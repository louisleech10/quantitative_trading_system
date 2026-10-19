"""
Feature Storage - 特徵儲存管理

使用 HDF5 格式儲存和讀取特徵數據

Author: AI Agent
Date: 2026-01-10
"""

import fcntl
import os
import threading
from contextlib import contextmanager
import h5py
import pandas as pd
import numpy as np
import json
import hashlib
import shutil
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple
from pathlib import Path
from datetime import datetime

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = None
    pq = None

from momentum.FeatureEngineering import feature_naming
from momentum.FeatureEngineering import run_provenance as _rp
from momentum.core.config import get_l7_codec_upgrade_enabled
from momentum.core.contracts import LayerExecutionResult, LayerStatus
from momentum.core.icfirstalign_errors import RowIndexLengthMismatchError
from momentum.core.logging import get_logger

if TYPE_CHECKING:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

logger = get_logger(__name__)


def _coerce_persistence_array(data: np.ndarray) -> np.ndarray:
    """Persistence 邊界：float64→float32 後再進 parquet/registry 編碼。"""
    # 只 cast dtype,不改記憶體序(ascontiguousarray 會改 npy/編碼 bytes 佈局)。
    return np.asarray(data, dtype=np.float32)


L7_ENCODING_REGISTRY_METADATA_KEY = "l7_encoding_registry"
RANK_UINT16_ENCODING = "rank_uint16"
ZSCORE_INT16_ENCODING = "zscore_int16"
GAUSSIAN_INT16_ENCODING = "gaussian_int16"
RANK_UINT16_NAN_SENTINEL = np.uint16(0)
ZSCORE_INT16_NAN_SENTINEL = np.int16(-32768)
ZSCORE_INT16_SCALE_FACTOR = 1000.0


class EncodeFallbackRequired(ValueError):
    """Raised when an integer codec would violate a lossless fallback gate."""


def encode_rank_as_uint16(rank_arr: np.ndarray, window: int) -> np.ndarray:
    """Encode rank percentiles to uint16, using 0 as the NaN sentinel."""

    window_int = int(window)
    if window_int <= 0:
        raise EncodeFallbackRequired("rank window must be positive")

    values = np.asarray(rank_arr, dtype=np.float32)
    encoded = np.zeros(values.shape, dtype=np.uint16)
    valid_mask = ~np.isnan(values)
    if not valid_mask.any():
        return encoded

    valid_values = values[valid_mask]
    if not bool(np.all(np.isfinite(valid_values))):
        raise EncodeFallbackRequired("rank values must be finite or NaN")
    if bool(np.any((valid_values <= 0.0) | (valid_values > 1.0))):
        raise EncodeFallbackRequired("rank values must be in (0, 1]")

    scaled = np.rint(valid_values * window_int * 2.0)
    if bool(np.any((scaled <= 0) | (scaled > np.iinfo(np.uint16).max))):
        raise EncodeFallbackRequired("rank scaled values exceed uint16 range")

    encoded[valid_mask] = scaled.astype(np.uint16)
    return encoded


def decode_rank_from_uint16(uint_arr: np.ndarray, window: int) -> np.ndarray:
    """Decode uint16 rank percentiles, restoring 0 sentinel values to NaN."""

    window_int = int(window)
    if window_int <= 0:
        raise ValueError("rank window must be positive")

    encoded = np.asarray(uint_arr, dtype=np.uint16)
    decoded = encoded.astype(np.float32) / float(window_int * 2.0)
    decoded[encoded == RANK_UINT16_NAN_SENTINEL] = np.nan
    return decoded


def encode_zscore_as_int16(zscore_arr: np.ndarray) -> np.ndarray:
    """Encode zscore-like values to int16, using INT16_MIN as NaN sentinel."""

    values = np.asarray(zscore_arr, dtype=np.float32)
    encoded = np.full(values.shape, ZSCORE_INT16_NAN_SENTINEL, dtype=np.int16)
    valid_mask = ~np.isnan(values)
    if not valid_mask.any():
        return encoded

    valid_values = values[valid_mask]
    if not bool(np.all(np.isfinite(valid_values))):
        raise EncodeFallbackRequired("zscore values must be finite or NaN")

    finite_abs_max = float(np.max(np.abs(valid_values)))
    if finite_abs_max > 32.767:
        raise EncodeFallbackRequired("zscore out of int16 range; fallback float32")

    scaled = np.rint(valid_values * ZSCORE_INT16_SCALE_FACTOR)
    if bool(np.any((scaled <= int(ZSCORE_INT16_NAN_SENTINEL)) | (scaled > np.iinfo(np.int16).max))):
        raise EncodeFallbackRequired("zscore scaled values exceed int16 range")

    encoded[valid_mask] = scaled.astype(np.int16)
    return encoded


def decode_zscore_from_int16(int_arr: np.ndarray) -> np.ndarray:
    """Decode int16 zscore-like values, restoring INT16_MIN to NaN."""

    encoded = np.asarray(int_arr, dtype=np.int16)
    decoded = encoded.astype(np.float32) / ZSCORE_INT16_SCALE_FACTOR
    decoded[encoded == ZSCORE_INT16_NAN_SENTINEL] = np.nan
    return decoded


def _write_parquet_zstd(
    table: Any,
    output_path: Path,
    compression_level: int = 1,
) -> None:
    _, pq_module = _require_pyarrow()
    pq_module.write_table(
        table,
        str(output_path),
        compression="zstd",
        compression_level=compression_level,
        use_dictionary=False,
    )


def _pack_dq_v1_metadata(part_data: Any, part_cols: List[str]) -> Optional[Dict[bytes, bytes]]:
    """Pack per-column data-quality stats so browse_data_quality can skip the scan.

    Format (little-endian):
        struct: <I (n_cols) + n_cols * (<iiI = first_valid_idx, last_valid_idx, nan_count)
        col_names: null-terminated UTF-8 strings concatenated.

    A column with no valid values stores first_valid=row_count, last_valid=-1.
    Returns None when ``part_data`` is not a 2D float array (we never want to
    add wrong stats — readers fall back to live parquet scan instead).
    """
    import struct

    try:
        arr = np.asarray(part_data)
    except Exception:
        return None
    if arr.ndim != 2 or arr.shape[1] != len(part_cols):
        return None
    if not np.issubdtype(arr.dtype, np.floating):
        return None

    nan_mask = np.isnan(arr)
    notna = ~nan_mask
    has_any = notna.any(axis=0)
    first_valid = notna.argmax(axis=0)
    last_valid = arr.shape[0] - 1 - notna[::-1].argmax(axis=0)
    nan_counts = nan_mask.sum(axis=0).astype(np.int64)
    row_count = int(arr.shape[0])

    buf = bytearray()
    buf += struct.pack("<I", len(part_cols))
    for i in range(len(part_cols)):
        if has_any[i]:
            fv = int(first_valid[i])
            lv = int(last_valid[i])
        else:
            fv = row_count
            lv = -1
        buf += struct.pack("<iiI", fv, lv, int(nan_counts[i]))

    names_blob = "\x00".join(str(c) for c in part_cols).encode("utf-8") + b"\x00"
    return {
        b"dq_v1": bytes(buf),
        b"dq_v1_cols": names_blob,
        b"dq_v1_rows": str(row_count).encode("ascii"),
    }


def _write_parquet_with_codec(
    table: Any,
    output_path: Path,
    *,
    float32_cols: List[str],
    schema_metadata: Optional[Dict[bytes, bytes]] = None,
    compression_level: int = 1,
) -> None:
    """Write parquet with optional BYTE_STREAM_SPLIT for float32 fallback columns."""

    if schema_metadata:
        merged_metadata = dict(table.schema.metadata or {})
        merged_metadata.update(schema_metadata)
        table = table.replace_schema_metadata(merged_metadata)

    table_columns = set(table.column_names)
    valid_float32_cols = [str(column) for column in float32_cols if str(column) in table_columns]
    if not get_l7_codec_upgrade_enabled() or not valid_float32_cols:
        _write_parquet_zstd(table, output_path, compression_level=compression_level)
        return

    _, pq_module = _require_pyarrow()
    column_encoding = {column: "BYTE_STREAM_SPLIT" for column in valid_float32_cols}
    try:
        pq_module.write_table(
            table,
            str(output_path),
            compression="zstd",
            compression_level=compression_level,
            use_dictionary=False,
            column_encoding=column_encoding,
            data_page_version="2.0",
        )
    except Exception as exc:
        if not _is_bss_unsupported_error(exc):
            raise
        if output_path.exists():
            output_path.unlink()
        logger.warning(
            "[L7-Codec] BYTE_STREAM_SPLIT unavailable for %d float32 cols; fallback zstd: %s",
            len(valid_float32_cols),
            str(exc),
        )
        _write_parquet_zstd(table, output_path, compression_level=compression_level)


def _is_bss_unsupported_error(error: Exception) -> bool:
    message = str(error).lower()
    markers = (
        "byte_stream_split",
        "byte stream split",
        "column_encoding",
        "column encoding",
        "unsupported",
        "not supported",
        "notimplemented",
    )
    return any(marker in message for marker in markers)


def build_phase2_skip_evidence(
    *,
    symbol: str,
    tf: str,
    config_hash: str,
    feature_schema_hash: str,
    l7_raw_size_bytes: int,
    l7_processed_size_bytes: int,
    fracdiff_enabled: bool,
    float32_fallback_group_count: int,
    reason: str,
) -> Dict[str, Any]:
    pa_module, _ = _require_pyarrow()
    return {
        "symbol": str(symbol),
        "tf": str(tf),
        "config_hash": str(config_hash),
        "feature_schema_hash": str(feature_schema_hash),
        "l7_raw_size_bytes": int(l7_raw_size_bytes),
        "l7_processed_size_bytes": int(l7_processed_size_bytes),
        "fracdiff_enabled": bool(fracdiff_enabled),
        "float32_fallback_group_count": int(float32_fallback_group_count),
        "pyarrow_version": str(getattr(pa_module, "__version__", "unknown")),
        "reason": str(reason),
        "created_at": datetime.utcnow().isoformat(),
    }


def write_phase2_skip_evidence(output_dir: Path, evidence: Dict[str, Any]) -> Path:
    required_fields = {
        "symbol",
        "tf",
        "config_hash",
        "feature_schema_hash",
        "l7_raw_size_bytes",
        "l7_processed_size_bytes",
        "fracdiff_enabled",
        "float32_fallback_group_count",
        "pyarrow_version",
        "reason",
        "created_at",
    }
    missing = sorted(required_fields.difference(evidence))
    if missing:
        raise ValueError(f"Phase 2 skip evidence missing fields: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "phase2_skip_evidence.json"
    temp_path = output_dir / "phase2_skip_evidence.json.tmp"
    with temp_path.open("w", encoding="utf-8") as evidence_file:
        json.dump(evidence, evidence_file, ensure_ascii=False, indent=2, default=str)
    os.replace(temp_path, output_path)
    return output_path


def _require_pyarrow() -> Tuple[Any, Any]:
    """Return pyarrow modules or raise a clear dependency error."""
    if pa is None or pq is None:
        raise ImportError("pyarrow is required for parquet persistence")
    return pa, pq


LAYER_NAME_TO_ID: Dict[str, str] = {
    "Layer 1": "L1",
    "Layer 2": "L2",
    "Layer 3": "L3",
    "Layer 4": "L4",
    "Layer 5": "L5",
    "Layer 6": "L6",
}

FAILOPEN_LAYER_FAILURE_STATUSES = frozenset(
    {
        LayerStatus.layer_failed,
        LayerStatus.all_engines_failed,
        LayerStatus.dependency_failed,
    }
)

V2_FAILOPEN_SCHEMA_VERSIONS = frozenset({"raw_v2", "processed_v2"})

QUALITY_STATUS_PRECEDENCE: Tuple[str, ...] = (
    "failed",
    "unknown",
    "partial",
    "empty_selection",
    "complete",
)

COMPLETENESS_FIELD_NAMES: Tuple[str, ...] = (
    "expected_layers",
    "present_layers",
    "failed_layers",
    "expected_timeframes",
    "present_timeframes",
    "failed_timeframes",
)


def default_completeness_meta(timeframe: str) -> Dict[str, Any]:
    """無 layer_results 證據時的 completeness 預設（quality_status=unknown）。"""
    return {
        "expected_layers": [],
        "present_layers": [],
        "failed_layers": [],
        "expected_timeframes": [timeframe],
        "present_timeframes": [],
        "failed_timeframes": [],
        "quality_status": "unknown",
        "failure_reasons": [],
    }


def build_completeness_meta_from_layer_results(
    layer_results: Dict[str, LayerExecutionResult],
    *,
    timeframe: str,
) -> Dict[str, Any]:
    """由 Batch2 layer_results 衍生 manifest completeness 欄（SPEC M-1~M-3）。"""
    if not layer_results:
        return default_completeness_meta(timeframe)

    expected_layers: List[str] = []
    present_layers: List[str] = []
    failed_layers: List[str] = []
    missing_layers: List[str] = []
    failure_reasons: List[str] = []

    for layer_name, layer_id in LAYER_NAME_TO_ID.items():
        result = layer_results.get(layer_name)
        if result is None:
            missing_layers.append(layer_id)
            continue
        if result.status == LayerStatus.empty_disabled:
            continue
        expected_layers.append(layer_id)
        if result.status in FAILOPEN_LAYER_FAILURE_STATUSES:
            failed_layers.append(layer_id)
            if result.reason:
                failure_reasons.append(f"{layer_id}:{result.reason}")
            continue
        present_layers.append(layer_id)

    if not expected_layers or missing_layers:
        quality_status = "unknown"
    elif failed_layers:
        quality_status = "partial"
    else:
        quality_status = "complete"

    return {
        "expected_layers": expected_layers,
        "present_layers": present_layers,
        "failed_layers": failed_layers,
        "expected_timeframes": [timeframe],
        "present_timeframes": [timeframe],
        "failed_timeframes": [],
        "quality_status": quality_status,
        "failure_reasons": failure_reasons,
    }


def build_timeframe_completeness(
    expected_tfs: Sequence[str],
    failed_tfs: Sequence[str],
) -> Dict[str, List[str]]:
    """週期三欄之 canonical 形成（docs/FFTFMETA_SPEC.md Task 1.1）。

    expected＝expected_tfs 首次出現序去重；failed 依 expected 序去重且須 ⊆ expected；present＝expected − failed（保序）。
    """
    expected: List[str] = list(dict.fromkeys(str(tf) for tf in expected_tfs))
    if not expected:
        raise ValueError("build_timeframe_completeness: expected_tfs 不得為空")
    failed_set = {str(tf) for tf in failed_tfs}
    unknown = sorted(failed_set.difference(expected))
    if unknown:
        raise ValueError(f"build_timeframe_completeness: failed_tfs 含不在 expected 之週期 {unknown}")
    return {
        "expected_timeframes": expected,
        "present_timeframes": [tf for tf in expected if tf not in failed_set],
        "failed_timeframes": [tf for tf in expected if tf in failed_set],
    }


def apply_quality_degradation(
    meta: Dict[str, Any],
    *,
    inf_ratio: float,
    nan_ratio: float,
    max_inf_ratio: float,
    max_nan_ratio: float,
    preprocessing_applied: Optional[bool],
    extra_failure_reasons: Sequence[str] = (),
) -> Dict[str, Any]:
    """NaN／inf 門檻與 L6.5 失敗之降級判定（docs/FFTFMETA_SPEC.md Task 2.3）。

    門檻為已解析之實值（`None` 由 factory 政策層先解析）；回傳併入降級後之新 completeness dict。
    健康（無任何降級原因）時回傳與輸入相等之副本；原因順序固定：既有（週期→層）→ L6.5 → inf → nan。
    `extra_failure_reasons`：d* 三出口之欄級事件（docs/FFSTAT_SPEC.md §C、Task 3.1），非空時併入並降為 partial。
    """
    out = dict(meta)
    reasons: List[str] = []
    # 降級只往更嚴重方向：unknown／failed 等優先序高於 partial 者不得被改寫為 partial（r1 codex P1-03）
    current = str(out.get("quality_status", "complete"))
    degraded_status = (
        current
        if current in QUALITY_STATUS_PRECEDENCE
        and QUALITY_STATUS_PRECEDENCE.index(current) < QUALITY_STATUS_PRECEDENCE.index("partial")
        else "partial"
    )
    if preprocessing_applied is False:
        out["preprocessing_applied"] = False
        reasons.append("L6.5:preprocessing_failed")
    # FFSTAT Task 3.1：d* 三出口欄級事件（`<事件>:<欄數>`）併入並降級；位置在 L6.5 之後、inf／nan 之前
    reasons.extend(str(reason) for reason in extra_failure_reasons)
    quality_reasons: List[str] = []
    if inf_ratio > max_inf_ratio:
        quality_reasons.append(f"inf_ratio={inf_ratio:.12g}>max_inf_ratio={max_inf_ratio:.12g}")
    if nan_ratio > max_nan_ratio:
        quality_reasons.append(f"nan_ratio={nan_ratio:.12g}>max_nan_ratio={max_nan_ratio:.12g}")
    if quality_reasons:
        out["quality_thresholds"] = {
            "max_inf_ratio": max_inf_ratio,
            "max_nan_ratio": max_nan_ratio,
            "observed_inf_ratio": float(inf_ratio),
            "observed_nan_ratio": float(nan_ratio),
        }
    reasons.extend(quality_reasons)
    if not reasons:
        return out
    out["quality_status"] = degraded_status
    out["run_status"] = degraded_status
    out["failure_reasons"] = list(out.get("failure_reasons", [])) + reasons
    return out


def _status_value(status: Any) -> str:
    return str(getattr(status, "value", status))


def _resolve_multi_tf_completeness(
    layer_results: Optional[Dict[str, LayerExecutionResult]],
    timeframe: str,
    *,
    timeframe_completeness: Optional[Dict[str, List[str]]],
    cross_tf_layer_failures: Sequence[str],
    layer_status_by_tf: Optional[Dict[str, Dict[str, Tuple[str, str]]]],
) -> Dict[str, Any]:
    """MultiTF canonical completeness（Task 1.2／1.3）。

    週期三欄取 `timeframe_completeness`；層失敗之唯一權威＝`cross_tf_layer_failures`（`L<n>:<tf>:<reason>`）；
    層之 expected 證據：有 `layer_status_by_tf` 時取各 present 週期非 empty_disabled 之 L<n> 聯集，否則取 `layer_results`。
    證據缺（無條目、條目缺 L1–L6 任一鍵、layer_results 缺層或為空）⇒ quality_status＝unknown。
    """
    from momentum.FeatureEngineering.utils.layer_ids import qualify_failed_layer_id

    tc = timeframe_completeness or build_timeframe_completeness([timeframe], [])
    layer_ids = list(LAYER_NAME_TO_ID.values())

    failed_layers: List[str] = []
    failed_ids: set = set()
    layer_reasons: List[str] = []
    for entry in cross_tf_layer_failures:
        qualified = qualify_failed_layer_id(str(entry), timeframe)
        parts = qualified.split(":", 2)
        prefix = ":".join(parts[:2])
        if prefix not in failed_layers:
            failed_layers.append(prefix)
        failed_ids.add(parts[0])
        layer_reasons.append(qualified)

    evidence_missing = False
    expected_layers: List[str] = []
    if layer_status_by_tf is not None:
        present_tfs = tc["present_timeframes"]
        for tf in present_tfs:
            statuses = layer_status_by_tf.get(tf)
            if not isinstance(statuses, dict) or not set(layer_ids) <= set(statuses):
                evidence_missing = True
        expected_layers = [
            layer_id
            for layer_id in layer_ids
            if any(
                _status_value(layer_status_by_tf[tf][layer_id][0]) != LayerStatus.empty_disabled.value
                for tf in present_tfs
                if isinstance(layer_status_by_tf.get(tf), dict) and layer_id in layer_status_by_tf[tf]
            )
        ]
    elif layer_results:
        for layer_name, layer_id in LAYER_NAME_TO_ID.items():
            result = layer_results.get(layer_name)
            if result is None:
                evidence_missing = True
                continue
            if result.status != LayerStatus.empty_disabled:
                expected_layers.append(layer_id)
    else:
        evidence_missing = True

    present_layers = [layer_id for layer_id in expected_layers if layer_id not in failed_ids]
    if evidence_missing or not expected_layers:
        quality_status = "unknown"
    elif tc["failed_timeframes"] or failed_layers:
        quality_status = "partial"
    else:
        quality_status = "complete"

    return {
        "expected_layers": expected_layers,
        "present_layers": present_layers,
        "failed_layers": failed_layers,
        "expected_timeframes": list(tc["expected_timeframes"]),
        "present_timeframes": list(tc["present_timeframes"]),
        "failed_timeframes": list(tc["failed_timeframes"]),
        "quality_status": quality_status,
        "failure_reasons": [f"timeframe:{tf}" for tf in tc["failed_timeframes"]] + layer_reasons,
    }


def resolve_completeness_meta(
    layer_results: Optional[Dict[str, LayerExecutionResult]],
    timeframe: str,
    *,
    override_quality_status: Optional[str] = None,
    timeframe_completeness: Optional[Dict[str, List[str]]] = None,
    cross_tf_layer_failures: Sequence[str] = (),
    layer_status_by_tf: Optional[Dict[str, Dict[str, Tuple[str, str]]]] = None,
) -> Dict[str, Any]:
    """組裝 artifact completeness；僅 consumer 政策（如 empty_selection）可覆寫 layer 衍生狀態。
    `timeframe_completeness`／`cross_tf_layer_failures`／`layer_status_by_tf`：MultiTF canonical 輸入
    （docs/FFTFMETA_SPEC.md Task 1.2／1.3；預設值時行為不變）。"""
    if timeframe_completeness is not None or cross_tf_layer_failures or layer_status_by_tf is not None:
        meta = _resolve_multi_tf_completeness(
            layer_results,
            timeframe,
            timeframe_completeness=timeframe_completeness,
            cross_tf_layer_failures=cross_tf_layer_failures,
            layer_status_by_tf=layer_status_by_tf,
        )
    elif layer_results:
        meta = build_completeness_meta_from_layer_results(layer_results, timeframe=timeframe)
    else:
        meta = default_completeness_meta(timeframe)
    if override_quality_status is not None:
        meta = dict(meta)
        meta["quality_status"] = override_quality_status
    return meta


def _is_default_completeness_input(
    timeframe_completeness: Optional[Dict[str, List[str]]],
    cross_tf_layer_failures: Sequence[str],
    layer_status_by_tf: Optional[Dict[str, Dict[str, Tuple[str, str]]]],
) -> bool:
    """writer 未收到任何 MultiTF canonical 輸入（IC-first 等後續寫入之形；Task 2.1）。"""
    return timeframe_completeness is None and not cross_tf_layer_failures and layer_status_by_tf is None


_ROOT_PRESERVED_COMPLETENESS_KEYS: Tuple[str, ...] = COMPLETENESS_FIELD_NAMES + (
    "failure_reasons",
    "quality_status",
    "run_status",
)


def _consumer_quality_override(quality_status: str) -> Optional[str]:
    """僅 empty_selection 等 consumer 政策覆寫 layer 衍生 quality_status。"""
    if quality_status == "empty_selection":
        return quality_status
    return None


def artifact_quality_status_for_merge(artifact: Dict[str, Any]) -> str:
    """單一 artifact 的有效 quality status（含遷移偵測 S-4）。"""
    schema_version = str(artifact.get("schema_version", ""))
    if schema_version not in V2_FAILOPEN_SCHEMA_VERSIONS:
        return "unknown"
    if not all(field in artifact for field in COMPLETENESS_FIELD_NAMES):
        return "unknown"
    return str(artifact.get("quality_status", "unknown"))


def merge_quality_status(artifacts: Dict[str, Any]) -> str:
    """跨 artifact 偏序聚合 run_status（failed>unknown>partial>empty_selection>complete）。"""
    if not isinstance(artifacts, dict) or not artifacts:
        return "unknown"
    statuses = [
        artifact_quality_status_for_merge(artifact)
        for artifact in artifacts.values()
        if isinstance(artifact, dict)
    ]
    if not statuses:
        return "unknown"
    for candidate in QUALITY_STATUS_PRECEDENCE:
        if candidate in statuses:
            return candidate
    return "unknown"


def resolve_run_status(manifest: Dict[str, Any]) -> str:
    """由 manifest artifacts 解析 run-level status。"""
    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return "unknown"
    return merge_quality_status(artifacts)


class FeatureStorage:
    """
    特徵儲存管理器
    
    使用 HDF5 格式儲存特徵，支持元數據管理
    
    Storage Format:
        data_cache/features/{case_id}.h5
        /{symbol}/{timeframe}/
            /features          # (n_samples, n_features) float32
            /feature_names     # Attribute: List[str]
            /labels            # (n_samples,) int32 (可選)
            /timestamps        # (n_samples,) int64
            /metadata          # Attributes
    """

    L7_RAW_SCHEMA_VERSION = "raw_v2"
    L7_PROCESSED_SCHEMA_VERSION = "processed_v2"
    L7_V2_MANIFEST_NAME = "feature_manifest.json"
    
    def __init__(self, base_path: str = "data_cache/features"):
        """
        Args:
            base_path: 特徵儲存根目錄
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger

    def feature_run_dir(self, symbol: str, tf: str, config_hash: str) -> Path:
        """Return the canonical V2 run directory for one symbol/timeframe/config."""
        safe_symbol = self._safe_path_segment(symbol, "symbol")
        safe_tf = self._safe_path_segment(tf, "tf")
        safe_config_hash = self._safe_path_segment(config_hash, "config_hash")
        return self.base_path / safe_symbol / safe_tf / safe_config_hash

    def write_raw(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        groups: Dict[str, pd.DataFrame],
        *,
        row_index: Optional[pd.DatetimeIndex] = None,
        layer_results: Optional[Dict[str, LayerExecutionResult]] = None,
        timeframe_completeness: Optional[Dict[str, List[str]]] = None,
        cross_tf_layer_failures: Sequence[str] = (),
        layer_status_by_tf: Optional[Dict[str, Dict[str, Tuple[str, str]]]] = None,
    ) -> Path:
        """Write IC-First raw L7 groups to the canonical V2 raw path.

        ``row_index`` is the primary timestamp axis.  When provided, its length
        must equal the raw row count; mismatch aborts the write.
        """
        return self._write_l7_v2_artifact(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            groups=groups,
            artifact_kind="raw",
            schema_version=self.L7_RAW_SCHEMA_VERSION,
            allow_empty=False,
            quality_status="complete",
            row_index=row_index,
            layer_results=layer_results,
            timeframe_completeness=timeframe_completeness,
            cross_tf_layer_failures=cross_tf_layer_failures,
            layer_status_by_tf=layer_status_by_tf,
        )

    def write_raw_from_registry_stream(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        registry: "ColumnGroupRegistry",
        *,
        preprocessor: Optional[Any] = None,
        n_workers: int = 1,
        cleanup_intermediate: bool = True,
        l65_mode: str = "legacy",
        time_range: Optional[Dict[str, Optional[str]]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        dead_drop_min_valid: Optional[int] = None,
        sanitize_finite_cap: Optional[float] = None,
        row_index: Optional[pd.DatetimeIndex] = None,
        row_slice: Optional[slice] = None,
        layer_results: Optional[Dict[str, LayerExecutionResult]] = None,
        timeframe_completeness: Optional[Dict[str, List[str]]] = None,
        cross_tf_layer_failures: Sequence[str] = (),
        layer_status_by_tf: Optional[Dict[str, Dict[str, Tuple[str, str]]]] = None,
        quality_gate: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Path, Dict[str, Any]]:
        """Stream CGSA registry groups into the canonical L7_raw artifact.

        When ``preprocessor`` is provided, each group is transformed and written
        directly to parquet without rewriting the registry ``.npy`` file. This
        is the disk-safe L6.5 → L7_raw path used by IC-First and legacy CGSA
        generation.

        ``dead_drop_min_valid``: 若不為 None，對每組 post-transform array 套用
        per-column dead-drop（常數欄 / valid_count < 此值 / 全 NaN）。這是 CGSA
        模式下 L7 dead feature drop 的實現（frame-path 不經過此路徑）。None = 停用，
        write 行為與現況 byte-identical。詳見 NAN_REDUCTION_STRATEGY.md §5.3。

        ``sanitize_finite_cap``: Layer B 通用淨化。若不為 None，對每組 post-transform
        array 將非有限值（±inf）與 |v| > cap 的絕對垃圾設為 NaN（在 dead-drop 之前），
        覆蓋所有 CGSA-streamed 特徵（含 L3）。攔截 Layer A 漏掉的 overflow stragglers；
        Class B 真實大值（如 volume VAR ~3e10）遠低於 cap → 保留。None = 停用。

        ``row_index``: primary timestamp axis for the run.  When provided, its
        length must match the streamed row_count; mismatch aborts the write.
        """
        pa_module, _ = _require_pyarrow()
        run_dir = self.feature_run_dir(symbol, tf, config_hash)
        run_dir.mkdir(parents=True, exist_ok=True)

        groups_list = list(registry.iter_all())
        if not groups_list:
            raise ValueError("write_raw_from_registry_stream requires non-empty registry groups")

        self._precheck_l7_raw_stream_disk_space(run_dir, groups_list)

        temp_root = run_dir / f".tmp-raw-{uuid.uuid4().hex}"
        temp_artifact_dir = temp_root / "raw"
        temp_artifact_dir.mkdir(parents=True, exist_ok=False)
        final_artifact_dir = run_dir / "raw"
        backup_dir: Optional[Path] = None
        artifact_installed = False
        preserve_temp = False
        # FFDSTAR Task 1.3 ⑤⑥：manifest 標記與回復、run 根檔（row index、紀錄檔）之安裝與備份
        manifest_marked = False
        manifest_before: Optional[bytes] = None
        install_backup_root: Optional[Path] = None
        installed_files: List[Tuple[str, bool]] = []

        group_manifest: Dict[str, Dict[str, Any]] = {}
        parquet_path_map: Dict[str, str] = {}
        first_part_by_source_group: Dict[str, str] = {}
        all_columns: List[str] = []
        storage_dtypes: set[str] = set()
        storage_dtype_counts: Dict[str, int] = {}
        storage_dtype_column_counts: Dict[str, int] = {}
        float32_fallback_parts: List[str] = []
        row_count: Optional[int] = None
        total_values = 0
        non_nan_values = 0
        total_inf = 0
        groups_with_inf = 0
        npy_freed = 0
        source_deleted = False
        dead_dropped_cols = 0
        dead_affected_groups = 0
        total_sanitized = 0

        parquet_metadata = self._build_l7_v2_parquet_metadata(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            schema_version=self.L7_RAW_SCHEMA_VERSION,
            feature_schema_hash="streaming_pending",
            artifact_kind="raw",
        )

        # Tier-aware zstd level for this streaming raw write.
        # Resolved once here so _write_group closure captures the scalar.
        # FFACT_L7_ZSTD_LEVEL env var overrides tier auto-detect.
        try:
            from momentum.FeatureEngineering.utils.hardware_utils import (
                get_memory_tier as _hw_gmt_stream,
                get_tier_config as _hw_gtc_stream,
            )
            _stream_tier_cfg = _hw_gtc_stream(_hw_gmt_stream())
            _stream_zstd_level: int = self._resolve_positive_env(
                "FFACT_L7_ZSTD_LEVEL",
                int(_stream_tier_cfg.get("l7_zstd_level", 1)),
            )
        except Exception:
            _stream_zstd_level = 1

        from momentum.FeatureEngineering.utils.nan_stats import ColumnNanAccumulator

        nan_accumulators: Dict[str, ColumnNanAccumulator] = {}
        dead_drop_reasons: Dict[str, str] = {}  # FFSTAT Task 2.3 ⑦：L7 串流剔除欄 → 原因
        # FFDSTAR Task 1.3：寫入端之逐欄紀錄素材（落盤名 → 終態／來源群組／dead-drop 事件）、群組檔內容身分項、
        # 前處理總開關關閉時之逐欄紀錄與群組表
        prov_terminals: Dict[str, str] = {}
        prov_column_group: Dict[str, str] = {}
        prov_column_keys: Dict[str, Tuple[str, str]] = {}
        prov_dropped: Dict[str, str] = {}
        prov_events: Dict[str, List[str]] = {}
        prov_master_off: Dict[Tuple[str, str], Dict[str, Any]] = {}
        prov_groups: Dict[str, Dict[str, Any]] = {}
        content_entries: List[_rp.ContentEntry] = []

        def _write_group(
            group_id: str,
            columns: List[str],
            data: np.ndarray,
            source_group_id: str,
            source_disk_path: Optional[Path],
            cleanup_source: bool,
        ) -> None:
            nonlocal row_count, total_values, non_nan_values, total_inf, groups_with_inf
            nonlocal npy_freed, source_deleted, dead_dropped_cols, dead_affected_groups
            nonlocal total_sanitized

            safe_group_id = self._safe_path_segment(str(group_id), "group_id")
            columns_list = [str(column) for column in columns]

            # Multi-TF column tf-tagging（FF-NAME Task 2.5）：registry 欄名為生成期間之未標記形，
            # 落盤時以群組週期插入第 2 段（唯一實作 feature_naming.tag_timeframe）：
            #   "close_trend_EMA_20"  →  "close_1h_trend_EMA_20"  (group 1h_L1_trend_EMA)
            #   "close_trend_EMA_20"  →  "close_12h_trend_EMA_20" (group 12h_L1_trend_EMA)
            _gid_tf = str(group_id).split("_", 1)[0]  # e.g. "1h", "12h", "4h", "1w"
            # RATIOUNSAFE Task 1.3：合法週期＝feature_naming.timeframe_keys()（含 1w；不寫死後綴規則）；
            # 標記規則單一真相源 feature_naming.tag_timeframe（群組週期身分、冪等、label_ 不標）
            _l65_names = list(columns_list)
            if _gid_tf in feature_naming.timeframe_keys():
                columns_list = [feature_naming.tag_timeframe(_c, _gid_tf) for _c in columns_list]
            # FFDSTAR Task 1.3：落盤名 → 來源群組、(來源群組, L6.5 所見欄名)（含其後被 dead-drop 者；紀錄對應之唯一權威）
            for _c, _l65 in zip(columns_list, _l65_names):
                prov_column_group[_c] = str(source_group_id)
                prov_column_keys[_c] = (str(source_group_id), _l65)

            array = _coerce_persistence_array(data)
            if row_slice is not None:
                array = array[row_slice]
            # registry 來源可能是 memmap / arrow 零拷貝（唯讀）；下方 Layer B 淨化與
            # dead-drop 需就地寫入 → 唯讀時複製成可寫副本（可寫來源維持零拷貝省記憶體）。
            if not array.flags.writeable:
                array = array.copy()
            if array.ndim != 2:
                raise ValueError(f"Raw stream group {safe_group_id} must be 2D, got {array.shape}")
            if array.shape[1] != len(columns_list):
                raise ValueError(
                    f"Raw stream group {safe_group_id} columns mismatch: "
                    f"expected {len(columns_list)}, got {array.shape[1]}"
                )
            if row_count is None:
                row_count = int(array.shape[0])
            elif row_count != int(array.shape[0]):
                raise ValueError(
                    f"L7_raw row_count mismatch: expected {row_count}, got {array.shape[0]} "
                    f"for {safe_group_id}"
                )

            # Layer B 通用淨化（CGSA mode）：在 dead-drop 之前，將 ±inf / 非有限值
            # 與 |v| > finite_cap 的絕對垃圾設為 NaN，覆蓋所有特徵（含 L3）。淨化後若
            # 整欄變 all-NaN，下方 dead-drop 順帶剔除。Class B 真實大值低於 cap → 保留。
            if sanitize_finite_cap is not None and array.size:
                from momentum.FeatureEngineering.utils.numeric_guards import sanitize_array_inplace

                _n_sanitized = sanitize_array_inplace(array, finite_cap=sanitize_finite_cap)
                if _n_sanitized:
                    total_sanitized += _n_sanitized

            # L7 dead-drop（CGSA mode）：per-column 剔除常數欄 / 樣本不足欄 / 全 NaN 欄。
            # 對實際 post-transform array 計算（不依賴快取統計）。整組全 dead 時 columns_list
            # 與 array 變空，下方 parts 為空 → 不寫 parquet，但源頭清理仍照常執行（I-6）。
            if dead_drop_min_valid is not None and array.shape[1] > 0:
                from momentum.FeatureEngineering.utils.dead_feature_filter import dead_column_mask

                _dmask = dead_column_mask(array, min_valid_samples=dead_drop_min_valid)
                if _dmask.any():
                    # FFSTAT Task 2.3 ⑦：剔除之欄與原因（同一死欄純函式；欄集合差異收據之原因來源）
                    from momentum.FeatureEngineering.preprocessing import stable_mask as _sm

                    _drop_idx = np.flatnonzero(_dmask)
                    _dec = _sm.dead_column_decision(
                        np.asarray(array[:, _drop_idx], dtype=np.float64), nan_rate_threshold=None,
                        min_valid=dead_drop_min_valid,
                    )
                    for _i, _reason in zip(_drop_idx, np.asarray(_dec.reason, dtype=object)):
                        dead_drop_reasons[str(columns_list[_i])] = str(_reason or "constant")
                        prov_dropped[str(columns_list[_i])] = str(source_group_id)
                        prov_events.setdefault(str(columns_list[_i]), []).append(str(_reason or "constant"))
                    # FFDSTAR Task 1.3：dead-drop 欄之終態（寫入端唯一離開點）
                    _rp.record_terminal(prov_terminals, [str(columns_list[_i]) for _i in _drop_idx], "dead_dropped")
                    _keep = ~_dmask
                    dead_dropped_cols += int(_dmask.sum())
                    dead_affected_groups += 1
                    columns_list = [c for c, k in zip(columns_list, _keep) if k]
                    array = array[:, _keep]

            total_values += int(array.size)
            if array.size:
                nan_mask = np.isnan(array)
                non_nan_values += int(array.size - nan_mask.sum())
                for column_index, column in enumerate(columns_list):
                    accumulator = nan_accumulators.setdefault(
                        column, ColumnNanAccumulator()
                    )
                    accumulator.update(nan_mask[:, column_index])
                inf_count = int(np.isinf(array).sum())
                total_inf += inf_count
                if inf_count > 0:
                    groups_with_inf += 1

            # 整組全 dead → parts 為空，不寫 parquet（下方源頭清理仍執行）
            parts = (
                self._split_large_group(safe_group_id, columns_list, array)
                if array.shape[1] > 0
                else []
            )
            # Compute source's pending-release shard bytes so the per-part disk
            # check mirrors the global pre-check's reclaimable accounting.
            # For chunked big-group splits, the source shards stay on disk until
            # the last chunk fires cleanup_source=True. Factoring them in here
            # prevents a false-fail when accumulated parquet parts temporarily
            # push the live free-disk reading below reserve_floor.
            _source_reclaimable: int = 0
            try:
                _sg = registry.get(str(source_group_id))
                _source_reclaimable = int(getattr(_sg, "total_shard_bytes", 0))
            except (KeyError, AttributeError):
                pass

            written_part_ids: List[str] = []
            for part_id, part_cols, part_data in parts:
                safe_part_id = self._safe_path_segment(str(part_id), "part_id")
                if safe_part_id in group_manifest:
                    # FFDSTAR Task 1.3 ①：part id 碰撞於寫入 group_manifest（及覆寫其 parquet）前拒收
                    raise _rp.ProvenanceConflictError(
                        f"L7_raw part id 碰撞：{safe_part_id}（來源群組 {source_group_id}；既有來源 "
                        f"{group_manifest[safe_part_id].get('source_group_id')}）"
                    )
                part_data = _coerce_persistence_array(part_data)
                (
                    arrays,
                    storage_dtype,
                    float32_cols,
                    column_dtype_counts,
                    part_estimate_bytes,
                ) = self._select_parquet_storage_columns(part_data, part_cols, pa_module)
                storage_dtypes.add(storage_dtype)
                storage_dtype_counts[storage_dtype] = storage_dtype_counts.get(storage_dtype, 0) + 1
                for dtype_name, dtype_count in column_dtype_counts.items():
                    storage_dtype_column_counts[dtype_name] = (
                        storage_dtype_column_counts.get(dtype_name, 0) + dtype_count
                    )
                if float32_cols:
                    float32_fallback_parts.append(safe_part_id)

                self._ensure_l7_raw_part_disk_space(
                    temp_artifact_dir,
                    part_id=safe_part_id,
                    source_group_id=str(source_group_id),
                    part_estimate_bytes=part_estimate_bytes,
                    source_reclaimable_bytes=_source_reclaimable,
                )

                table = pa_module.Table.from_arrays(arrays, names=list(part_cols))
                output_path = temp_artifact_dir / f"{safe_part_id}.parquet"
                staging_path = temp_artifact_dir / f".{safe_part_id}.tmp.parquet"
                # P1-D: precompute per-column data-quality stats so
                # browse_data_quality can skip the per-column NaN scan entirely
                # for fresh-cold reads.  Failure to pack returns None and we
                # fall back to base schema_metadata — no read-side regression.
                _dq_meta = _pack_dq_v1_metadata(part_data, list(part_cols))
                _merged_schema_metadata: Dict[bytes, bytes] = dict(parquet_metadata or {})
                if _dq_meta:
                    _merged_schema_metadata.update(_dq_meta)
                _write_parquet_with_codec(
                    table,
                    staging_path,
                    float32_cols=float32_cols,
                    schema_metadata=_merged_schema_metadata,
                    compression_level=_stream_zstd_level,
                )
                os.replace(staging_path, output_path)

                group_manifest[safe_part_id] = {
                    "path": str(Path("raw") / output_path.name),
                    "file": output_path.name,
                    "columns": list(part_cols),
                    "column_count": int(len(part_cols)),
                    "row_count": int(array.shape[0]),
                    "dtype": storage_dtype,
                    "nan_ratio": self._calculate_array_nan_ratio(part_data),
                    "file_size_bytes": int(output_path.stat().st_size),
                    "encoded_column_count": 0,
                    "source_group_id": str(source_group_id),
                    "dtype_counts": dict(column_dtype_counts),
                    "float32_columns": list(float32_cols),
                }
                # FFDSTAR Task 1.3 ③：群組檔寫畢當下計其內容身分項（檔案 sha256＋footer 之 Arrow 型別）
                content_entries.append(_rp.content_entry_for_file(
                    output_path, str(Path("raw") / output_path.name), list(part_cols), int(array.shape[0]),
                ))
                _rp.record_terminal(prov_terminals, [str(c) for c in part_cols], "written")
                all_columns.extend(part_cols)
                written_part_ids.append(safe_part_id)
                del arrays, table

            if written_part_ids:
                first_part_by_source_group.setdefault(str(source_group_id), written_part_ids[0])

            if cleanup_intermediate and cleanup_source:
                # Phase B Phase 1: sharded sources are tracked via the registry,
                # not a single .npy path. Use registry.release_storage() so
                # all shard files are released but the group entry stays so
                # the post-write set_group_parquet_paths() binding still works.
                source_group = None
                try:
                    source_group = registry.get(str(source_group_id))
                except KeyError:
                    source_group = None
                if source_group is not None and getattr(source_group, "shards", ()):
                    try:
                        freed = registry.release_storage(str(source_group_id))
                    except Exception as exc:
                        raise OSError(
                            f"Failed to release sharded source after raw write for {source_group_id}: {exc}"
                        ) from exc
                    npy_freed += freed
                    source_deleted = True
                elif source_disk_path is not None:
                    try:
                        source_path = Path(source_disk_path)
                        if source_path.exists():
                            file_size = source_path.stat().st_size
                            source_path.unlink()
                            npy_freed += file_size
                            source_deleted = True
                    except OSError as exc:
                        raise OSError(
                            f"Failed to cleanup source npy after raw write for {source_group_id}: {exc}"
                        ) from exc

            del array

        try:
            if preprocessor is not None:
                transformed_groups = preprocessor.transform_registry_groups_to_sink(
                    registry,
                    _write_group,
                    n_workers=n_workers,
                )
            else:
                # Mode C passthrough: no L6.5 transform. Stream sharded sources
                # shard-by-shard so peak in-flight bytes equal max_shard_bytes
                # rather than full group bytes.
                transformed_groups = 0
                for source_group_id, group in groups_list:
                    group_columns = list(group.columns)
                    source_disk = getattr(group, "disk_path", None)
                    shards = getattr(group, "shards", ()) or ()
                    # FFDSTAR Task 1.1 盤點①：總開關關閉（不建前處理器）⇒ 寫入端對全部欄全部步驟記總開關關閉之值；
                    # 鍵之週期＝群組之原生週期（同前處理器紀錄鍵；落盤名之對應由 `_write_group` 之對照決定）
                    _mode_c_tf = str(getattr(group, "timeframe", "") or str(source_group_id).split("_", 1)[0])
                    _mode_c_layer = getattr(getattr(group, "layer", None), "value", getattr(group, "layer", None))
                    _rp.record_all_steps(prov_master_off, [(_mode_c_tf, str(c)) for c in group_columns],
                                         "preprocessing_master_off",
                                         layer=None if _mode_c_layer is None else str(_mode_c_layer),
                                         group_id=str(source_group_id))
                    _rp.record_group(prov_groups, str(source_group_id), arm="no_preprocessing", status="ok")
                    if shards:
                        n_shards = len(shards)
                        for shard_pos, (shard_meta, shard_arr, shard_cols) in enumerate(
                            registry.iter_shards(str(source_group_id))
                        ):
                            is_last = shard_pos == n_shards - 1
                            shard_group_id = (
                                str(source_group_id)
                                if n_shards == 1
                                else f"{source_group_id}_shard{shard_meta.shard_idx:0{max(2, len(str(n_shards - 1)))}d}"
                            )
                            _write_group(
                                shard_group_id,
                                list(shard_cols),
                                np.asarray(shard_arr, dtype=np.float32),
                                str(source_group_id),
                                shard_meta.disk_path,
                                is_last,
                            )
                            del shard_arr
                    else:
                        data = registry.load_data(str(source_group_id))
                        _write_group(
                            str(source_group_id),
                            group_columns,
                            data,
                            str(source_group_id),
                            source_disk,
                            True,
                        )
                        del data
                    transformed_groups += 1

            total_features = int(len(all_columns))
            if total_features <= 0:
                raise ValueError("write_raw_from_registry_stream produced no features")

            if dead_drop_min_valid is not None and dead_dropped_cols > 0:
                logger.info(
                    "[L7 Dead Drop][CGSA] dropped %d cols across %d groups "
                    "(min_valid=%d); final features=%d",
                    dead_dropped_cols, dead_affected_groups, dead_drop_min_valid, total_features,
                )

            if sanitize_finite_cap is not None and total_sanitized > 0:
                logger.info(
                    "[Layer B Sanitize][CGSA] nulled %d non-finite/over-cap values "
                    "(finite_cap=%.0e) across all streamed features",
                    total_sanitized, sanitize_finite_cap,
                )

            ordered_group_manifest = {group_id: group_manifest[group_id] for group_id in sorted(group_manifest)}
            feature_schema_hash = self._build_schema_hash_from_columns(
                self.L7_RAW_SCHEMA_VERSION,
                ordered_group_manifest,
            )
            resolved_row_count = int(row_count or 0)

            # FFDSTAR Task 1.3 ②：前處理器紀錄（總開關關閉則寫入端紀錄）＋ dead-drop ＋群組 manifest 組逐欄紀錄表；
            # 窮盡性（落盤欄聯集 ∪ dead-drop 欄，逐名、無重複）不符即拋
            if preprocessor is not None:
                prov_records = preprocessor.execution_records()
                prov_group_table: Dict[str, Dict[str, Any]] = preprocessor.execution_groups()
            else:
                prov_records = prov_master_off
                prov_group_table = {}
            _rp.merge_groups(prov_group_table, prov_groups)
            written_sources = {str(info.get("source_group_id")) for info in ordered_group_manifest.values()}
            for _gid in sorted(set(prov_dropped.values()) - written_sources):
                _rp.record_group(prov_group_table, _gid, status="all_dead_dropped", override_status=True)
            provenance_table = _rp.build_provenance_table(
                prov_records,
                output_columns=list(all_columns),
                column_group=dict(prov_column_group),
                dropped_columns=dict(prov_dropped),
                terminals=dict(prov_terminals),
                events=dict(prov_events),
                column_keys=dict(prov_column_keys),
            )
            _rp.check_exhaustive(provenance_table, all_columns, prov_dropped)

            # FFDSTAR Task 1.3 ④：row index 檔（`timestamps.parquet`）改寫入暫存根（不再於安裝前直寫 run 根）
            row_index_manifest = self._write_row_index_artifact(
                run_dir=temp_root,
                row_index=row_index,
                row_count=resolved_row_count,
            )
            # FFDSTAR Task 1.3 ③：內容身分＝群組檔組成項（寫檔當下所計）＋ row index 檔 sha256
            row_index_sha256 = (
                _rp.file_sha256(temp_root / str(row_index_manifest["path"])) if row_index_manifest is not None else None
            )
            content_sha256 = _rp.compute_content_sha256(content_entries, row_index_sha256)
            # FFDSTAR Task 1.3 ④：紀錄檔以 zstd parquet 寫入暫存 `provenance/`（失敗上拋）
            provenance_pointer = _rp.write_provenance_table(provenance_table, temp_root, "raw", prov_group_table)
            resolved_time_range = time_range or {"start": None, "end": None}
            coverage = float(non_nan_values / total_values) if total_values else 0.0
            inf_ratio = float(total_inf / total_values) if total_values else 0.0
            abnormal_nan = sum(
                accumulator.abnormal() for accumulator in nan_accumulators.values()
            )
            nan_ratio = float(abnormal_nan / total_values) if total_values else 0.0
            # FFSTAT §C 紀錄：逐欄 stable_start（公開輸出首個有效值之時間）；有起始日而首個有效值晚於起始日之欄
            # ⇒ warmup_insufficient_history 事件（品質 partial）
            from momentum.FeatureEngineering.warmup_window import (
                WARMUP_INSUFFICIENT_EVENT,
                stable_start_from_first_rows,
                warmup_late_columns,
            )

            stable_start = (
                stable_start_from_first_rows(
                    {c: (acc.leading_nan if acc.seen_valid else None) for c, acc in nan_accumulators.items()},
                    row_index,
                )
                if row_index is not None
                else {}
            )
            warmup_late = warmup_late_columns(
                stable_start,
                (quality_gate or {}).get("warmup_output_start"),
                (quality_gate or {}).get("warmup_probe_late"),
            )
            validation_summary = {
                "has_nan": bool(non_nan_values < total_values),
                "has_inf": bool(total_inf > 0),
                "coverage": coverage,
                "inf_count": int(total_inf),
                "inf_ratio": inf_ratio,
                "nan_ratio": nan_ratio,
                "groups_with_inf": int(groups_with_inf),
                "warnings": [],
            }
            stream_metadata = {
                "artifact_kind": "raw",
                "schema_version": self.L7_RAW_SCHEMA_VERSION,
                "l65_mode": str(l65_mode),
                "cleanup_intermediate": bool(cleanup_intermediate),
                "npy_freed_bytes": int(npy_freed),
                "transformed_groups": int(transformed_groups),
                "dead_dropped_cols": int(dead_dropped_cols),
                "dead_affected_groups": int(dead_affected_groups),
                "stable_start": stable_start,
                "warmup_insufficient_columns": warmup_late,
                "dtype_summary": self._build_dtype_summary(
                    storage_dtype_counts,
                    float32_fallback_parts,
                    storage_dtype_column_counts,
                ),
            }
            if extra_metadata:
                stream_metadata.update(extra_metadata)

            completeness_meta = resolve_completeness_meta(
                layer_results,
                tf,
                timeframe_completeness=timeframe_completeness,
                cross_tf_layer_failures=cross_tf_layer_failures,
                layer_status_by_tf=layer_status_by_tf,
            )
            if quality_gate is not None:
                # Task 2.3：品質降級於 manifest 合併前定案（validation 比率於上方已算出）
                completeness_meta = apply_quality_degradation(
                    completeness_meta,
                    inf_ratio=inf_ratio,
                    nan_ratio=nan_ratio,
                    max_inf_ratio=float(quality_gate["max_inf_ratio"]),
                    max_nan_ratio=float(quality_gate["max_nan_ratio"]),
                    preprocessing_applied=quality_gate.get("preprocessing_applied"),
                    # FFSTAT Task 3.1：呼叫端已知之 d* 事件＋本串流 L6.5 前處理器所記事件（manifest 合併前）
                    extra_failure_reasons=tuple(quality_gate.get("extra_failure_reasons", ())) + tuple(
                        preprocessor.stationarity_failure_reasons()
                        if preprocessor is not None and hasattr(preprocessor, "stationarity_failure_reasons")
                        else ()
                    ) + ((f"{WARMUP_INSUFFICIENT_EVENT}:{len(warmup_late)}",) if warmup_late else ()),
                )
            # completeness 六欄＋quality_status＋failure_reasons；quality_thresholds／run_status 等降級細節只經 summary
            # 回給 factory。FFDSTAR Task 1.3 ⑦：raw 節點另新增 `content_sha256` 與 `provenance` 物件（合併時寫入）
            manifest_completeness = {
                key: completeness_meta[key]
                for key in COMPLETENESS_FIELD_NAMES + ("quality_status", "failure_reasons")
                if key in completeness_meta
            }

            # FFDSTAR Task 1.3 ⑤：對 run 根之任何寫入前，先將舊 manifest 之 raw 節點標為不完整（原子寫；回復用原位元組）
            manifest_before = self._mark_manifest_artifact_incomplete_v2(run_dir, "raw")
            manifest_marked = True

            # ⑥ 安裝 raw、row index 檔與紀錄檔（各自先將舊檔移為備份）
            if final_artifact_dir.exists():
                backup_dir = run_dir / f".previous-raw-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                os.replace(final_artifact_dir, backup_dir)

            os.replace(temp_artifact_dir, final_artifact_dir)
            artifact_installed = True
            install_backup_root = run_dir / f".previous-raw-files-{uuid.uuid4().hex}"
            self._install_staged_run_files(temp_root, run_dir, install_backup_root, installed_files)
            # ⑦ manifest 合併為唯一提交點
            self._atomic_merge_feature_manifest_v2(
                run_dir,
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                artifact_kind="raw",
                schema_version=self.L7_RAW_SCHEMA_VERSION,
                quality_status=str(completeness_meta["quality_status"]),
                feature_schema_hash=feature_schema_hash,
                row_count=resolved_row_count,
                time_range=resolved_time_range,
                total_features=total_features,
                group_manifest=ordered_group_manifest,
                extra_metadata=stream_metadata,
                row_index=row_index_manifest,
                completeness_meta=manifest_completeness,
                content_sha256=content_sha256,
                provenance=provenance_pointer.to_manifest(),
            )

            if backup_dir is not None and backup_dir.exists():
                shutil.rmtree(backup_dir)
            if install_backup_root is not None and install_backup_root.exists():
                shutil.rmtree(install_backup_root)

            for source_group_id, first_part_id in first_part_by_source_group.items():
                parquet_path_map[source_group_id] = str((final_artifact_dir / f"{first_part_id}.parquet").resolve())
            if parquet_path_map:
                registry.set_group_parquet_paths(parquet_path_map, write_manifest=False)

            summary = {
                "raw_path": str(final_artifact_dir),
                "manifest_path": str(run_dir / self.L7_V2_MANIFEST_NAME),
                "feature_count": total_features,
                "row_count": resolved_row_count,
                "group_count": len(ordered_group_manifest),
                "npy_freed_bytes": int(npy_freed),
                "storage_dtype": self._summarize_storage_dtype(storage_dtypes),
                "dtype_summary": stream_metadata["dtype_summary"],
                "validation": validation_summary,
                "l65_mode": str(l65_mode),
                "dead_dropped_cols": int(dead_dropped_cols),
                "dead_affected_groups": int(dead_affected_groups),
                "stable_start": stable_start,
                "warmup_insufficient_columns": warmup_late,
                "dead_drop_reasons": dict(dead_drop_reasons),
                # 最終 completeness（含 Task 2.3 降級）；factory 以之寫 result.metadata（Task 2.2 同源）
                "completeness": dict(completeness_meta),
            }
            self.logger.info(
                "[L7_raw] registry stream persist done: symbol=%s tf=%s groups=%d features=%d "
                "npy_freed=%.2f GiB dtype=%s",
                symbol,
                tf,
                len(ordered_group_manifest),
                total_features,
                npy_freed / (1024 ** 3),
                summary["storage_dtype"],
            )
            return final_artifact_dir, summary
        except Exception:
            preserve_temp = source_deleted
            if source_deleted:
                self.logger.warning(
                    "[L7_raw] late failure after source cleanup; preserving raw artifact/temp for recovery: %s",
                    final_artifact_dir if artifact_installed else temp_root,
                )
            if artifact_installed and final_artifact_dir.exists() and not source_deleted:
                shutil.rmtree(final_artifact_dir)
            if backup_dir is not None and backup_dir.exists() and not source_deleted:
                os.replace(backup_dir, final_artifact_dir)
            # FFDSTAR Task 1.3 ⑥：來源未刪 ⇒ row index 檔與紀錄檔自備份回復、manifest 回復為原位元組；來源已刪 ⇒
            # 不回復、manifest 維持不完整（fail-closed）
            if manifest_marked:
                if not source_deleted:
                    self._restore_staged_run_files(run_dir, install_backup_root, installed_files)
                    self._restore_manifest_v2_bytes(run_dir, manifest_before)
                else:
                    self._mark_manifest_artifact_incomplete_v2(run_dir, "raw")
            raise
        finally:
            if temp_root.exists() and not preserve_temp:
                shutil.rmtree(temp_root)
            elif temp_root.exists() and preserve_temp:
                self.logger.warning(
                    "[L7_raw] preserving incomplete temp artifact after source cleanup: %s",
                    temp_root,
                )

    def write_processed(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        groups: Dict[str, pd.DataFrame],
        *,
        row_index: pd.DatetimeIndex,
        layer_results: Optional[Dict[str, LayerExecutionResult]] = None,
        timeframe_completeness: Optional[Dict[str, List[str]]] = None,
        cross_tf_layer_failures: Sequence[str] = (),
        layer_status_by_tf: Optional[Dict[str, Dict[str, Tuple[str, str]]]] = None,
        post_ic_arm: Optional[str] = None,
    ) -> Path:
        """Write IC-First processed L7 groups to the canonical V2 processed path.

        ICFIRSTALIGN Task 1.3：`row_index` 必填；processed 寫自身 sidecar（`processed_timestamps.parquet`），
        位置與時間範圍、列數記於 processed artifact 節點；manifest 根之 time_range／row_count／row_index 只屬 raw。
        """
        quality_status = "empty_selection" if not groups else "complete"
        return self._write_l7_v2_artifact(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            groups=groups,
            artifact_kind="processed",
            schema_version=self.L7_PROCESSED_SCHEMA_VERSION,
            allow_empty=True,
            quality_status=quality_status,
            row_index=row_index,
            layer_results=layer_results,
            timeframe_completeness=timeframe_completeness,
            cross_tf_layer_failures=cross_tf_layer_failures,
            layer_status_by_tf=layer_status_by_tf,
            post_ic_arm=post_ic_arm,
        )

    def _write_l7_v2_artifact(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        groups: Dict[str, pd.DataFrame],
        artifact_kind: str,
        schema_version: str,
        allow_empty: bool,
        quality_status: str,
        row_index: Optional[pd.DatetimeIndex] = None,
        layer_results: Optional[Dict[str, LayerExecutionResult]] = None,
        timeframe_completeness: Optional[Dict[str, List[str]]] = None,
        cross_tf_layer_failures: Sequence[str] = (),
        layer_status_by_tf: Optional[Dict[str, Dict[str, Tuple[str, str]]]] = None,
        post_ic_arm: Optional[str] = None,
    ) -> Path:
        pa_module, pq_module = _require_pyarrow()
        run_dir = self.feature_run_dir(symbol, tf, config_hash)
        run_dir.mkdir(parents=True, exist_ok=True)

        group_items = self._normalize_l7_v2_groups(groups)
        total_features = sum(len(frame.columns) for _group_id, frame in group_items)
        if not allow_empty and total_features <= 0:
            raise ValueError("write_raw requires non-empty feature groups")
        if allow_empty and total_features <= 0:
            quality_status = "empty_selection"

        completeness_meta = resolve_completeness_meta(
            layer_results,
            tf,
            override_quality_status=_consumer_quality_override(quality_status),
            timeframe_completeness=timeframe_completeness,
            cross_tf_layer_failures=cross_tf_layer_failures,
            layer_status_by_tf=layer_status_by_tf,
        )
        resolved_quality_status = str(completeness_meta["quality_status"])
        preserve_root = _is_default_completeness_input(
            timeframe_completeness, cross_tf_layer_failures, layer_status_by_tf
        )

        feature_schema_hash = self._build_l7_v2_schema_hash(
            schema_version=schema_version,
            group_items=group_items,
        )
        row_count = self._resolve_l7_v2_row_count(group_items)
        if artifact_kind == "processed" and not group_items and row_index is not None:
            row_count = int(len(row_index))  # 空選擇：列數依 processed 軸（長度 0）
        row_index_manifest = self._write_row_index_artifact(
            run_dir=run_dir,
            row_index=row_index,
            row_count=row_count,
            filename="processed_timestamps.parquet" if artifact_kind == "processed" else "timestamps.parquet",
        )
        time_range = self._resolve_l7_v2_time_range(group_items)
        if artifact_kind == "processed" and row_index is not None:
            time_range = {
                "start": self._format_manifest_value(row_index[0]) if len(row_index) else None,
                "end": self._format_manifest_value(row_index[-1]) if len(row_index) else None,
            }

        temp_root = run_dir / f".tmp-{artifact_kind}-{uuid.uuid4().hex}"
        temp_artifact_dir = temp_root / artifact_kind
        temp_artifact_dir.mkdir(parents=True, exist_ok=False)

        final_artifact_dir = run_dir / artifact_kind
        backup_dir: Optional[Path] = None
        artifact_installed = False

        try:
            group_manifest: Dict[str, Dict[str, Any]] = {}
            parquet_metadata = self._build_l7_v2_parquet_metadata(
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                schema_version=schema_version,
                feature_schema_hash=feature_schema_hash,
                artifact_kind=artifact_kind,
            )

            for group_id, frame in group_items:
                group_manifest[group_id] = self._write_l7_v2_group_parquet(
                    pa_module=pa_module,
                    pq_module=pq_module,
                    artifact_dir=temp_artifact_dir,
                    group_id=group_id,
                    frame=frame,
                    schema_metadata=parquet_metadata,
                )

            if final_artifact_dir.exists():
                backup_dir = run_dir / f".previous-{artifact_kind}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                os.replace(final_artifact_dir, backup_dir)

            os.replace(temp_artifact_dir, final_artifact_dir)
            artifact_installed = True
            self._atomic_merge_feature_manifest_v2(
                run_dir,
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                artifact_kind=artifact_kind,
                schema_version=schema_version,
                quality_status=resolved_quality_status,
                feature_schema_hash=feature_schema_hash,
                row_count=row_count,
                time_range=time_range,
                total_features=total_features,
                group_manifest=group_manifest,
                row_index=row_index_manifest,
                completeness_meta=completeness_meta,
                preserve_root_completeness=preserve_root,
                post_ic_arm=post_ic_arm,
            )

            if backup_dir is not None and backup_dir.exists():
                shutil.rmtree(backup_dir)

            self.logger.info(
                "[IC-First] %s persist done: symbol=%s tf=%s groups=%d features=%d schema=%s",
                artifact_kind,
                symbol,
                tf,
                len(group_manifest),
                total_features,
                schema_version,
            )
            return final_artifact_dir
        except Exception:
            if artifact_installed and final_artifact_dir.exists():
                shutil.rmtree(final_artifact_dir)
            if backup_dir is not None and backup_dir.exists():
                os.replace(backup_dir, final_artifact_dir)
            raise
        finally:
            if temp_root.exists():
                shutil.rmtree(temp_root)

    @staticmethod
    def _safe_path_segment(value: str, field_name: str) -> str:
        segment = str(value).strip()
        if not segment or segment in {".", ".."} or "/" in segment or "\\" in segment:
            raise ValueError(f"Invalid {field_name}: {value!r}")
        return segment

    @classmethod
    def _normalize_l7_v2_groups(
        cls,
        groups: Dict[str, pd.DataFrame],
    ) -> List[Tuple[str, pd.DataFrame]]:
        if groups is None:
            raise ValueError("groups must be a dictionary")

        normalized: List[Tuple[str, pd.DataFrame]] = []
        seen_group_ids: set[str] = set()
        for raw_group_id, frame in groups.items():
            group_id = cls._safe_path_segment(str(raw_group_id), "group_id")
            if group_id in seen_group_ids:
                raise ValueError(f"Duplicate group_id after normalization: {group_id}")
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(f"Group {group_id} must be a pandas DataFrame")
            normalized.append((group_id, frame))
            seen_group_ids.add(group_id)
        return normalized

    @staticmethod
    def _build_l7_v2_schema_hash(
        schema_version: str,
        group_items: List[Tuple[str, pd.DataFrame]],
    ) -> str:
        schema_payload = {
            "schema_version": schema_version,
            "groups": {
                group_id: [str(column) for column in frame.columns]
                for group_id, frame in sorted(group_items, key=lambda item: item[0])
            },
        }
        encoded = json.dumps(schema_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _resolve_l7_v2_row_count(group_items: List[Tuple[str, pd.DataFrame]]) -> int:
        row_counts = {len(frame.index) for _group_id, frame in group_items}
        if not row_counts:
            return 0
        if len(row_counts) != 1:
            raise ValueError(f"L7 V2 group row_count mismatch: {sorted(row_counts)}")
        return int(next(iter(row_counts)))

    @classmethod
    def _resolve_l7_v2_time_range(
        cls,
        group_items: List[Tuple[str, pd.DataFrame]],
    ) -> Dict[str, Optional[str]]:
        if not group_items:
            return {"start": None, "end": None}

        non_empty_indexes = [frame.index for _group_id, frame in group_items if len(frame.index) > 0]
        if not non_empty_indexes:
            return {"start": None, "end": None}

        starts = [index[0] for index in non_empty_indexes]
        ends = [index[-1] for index in non_empty_indexes]
        return {
            "start": cls._format_manifest_value(min(starts)),
            "end": cls._format_manifest_value(max(ends)),
        }

    @staticmethod
    def _write_row_index_artifact(
        run_dir: Path,
        row_index: Optional[pd.DatetimeIndex],
        row_count: int,
        filename: str = "timestamps.parquet",
    ) -> Optional[Dict[str, Any]]:
        """Persist a timestamp axis as UTC epoch seconds（raw＝`timestamps.parquet`；processed 另檔，格式相同）。"""
        if row_index is None:
            return None
        if len(row_index) != row_count:
            raise RowIndexLengthMismatchError(f"row_index {len(row_index)} != row_count {row_count}")
        if not isinstance(row_index, pd.DatetimeIndex):
            raise TypeError("row_index must be a pandas DatetimeIndex")

        pa_module, pq_module = _require_pyarrow()
        epoch_s = (np.asarray(row_index.view("int64"), dtype=np.int64) // 1_000_000_000).astype("int64")
        table = pa_module.table({"timestamp": pa_module.array(epoch_s, type=pa_module.int64())})
        pq_module.write_table(table, run_dir / filename)
        return {
            "path": filename,
            "count": int(len(row_index)),
            "unit": "s",
            "tz": "UTC",
        }

    @staticmethod
    def _format_manifest_value(value: Any) -> str:
        if hasattr(value, "isoformat"):
            return str(value.isoformat())
        if isinstance(value, np.generic):
            return str(value.item())
        return str(value)

    @staticmethod
    def _build_l7_v2_parquet_metadata(
        symbol: str,
        tf: str,
        config_hash: str,
        schema_version: str,
        feature_schema_hash: str,
        artifact_kind: str,
    ) -> Dict[bytes, bytes]:
        return {
            b"schema_version": schema_version.encode("utf-8"),
            b"symbol": str(symbol).encode("utf-8"),
            b"tf": str(tf).encode("utf-8"),
            b"config_hash": str(config_hash).encode("utf-8"),
            b"feature_schema_hash": feature_schema_hash.encode("utf-8"),
            b"artifact_kind": artifact_kind.encode("utf-8"),
        }

    def _write_l7_v2_group_parquet(
        self,
        pa_module: Any,
        pq_module: Any,
        artifact_dir: Path,
        group_id: str,
        frame: pd.DataFrame,
        schema_metadata: Dict[bytes, bytes],
    ) -> Dict[str, Any]:
        file_name = f"{group_id}.parquet"
        output_path = artifact_dir / file_name
        artifact_kind = schema_metadata.get(b"artifact_kind", b"").decode("utf-8")
        table, float32_cols, encoding_registry = self._build_l7_v2_table(
            pa_module=pa_module,
            frame=frame,
            artifact_kind=artifact_kind,
        )
        merged_metadata = dict(table.schema.metadata or {})
        merged_metadata.update(schema_metadata)
        if encoding_registry:
            merged_metadata[L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8")] = json.dumps(
                encoding_registry,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        table = table.replace_schema_metadata(merged_metadata)
        _write_parquet_with_codec(
            table,
            output_path,
            float32_cols=float32_cols,
        )
        return {
            "path": str(Path(artifact_dir.name) / file_name),
            "file": file_name,
            "columns": [str(column) for column in frame.columns],
            "column_count": int(len(frame.columns)),
            "row_count": int(len(frame.index)),
            "dtype": self._summarize_frame_dtype(frame),
            "nan_ratio": self._calculate_nan_ratio(frame),
            "file_size_bytes": int(output_path.stat().st_size),
            "encoded_column_count": int(len(encoding_registry)),
        }

    def _build_l7_v2_table(
        self,
        pa_module: Any,
        frame: pd.DataFrame,
        artifact_kind: str,
    ) -> Tuple[Any, List[str], Dict[str, Dict[str, Any]]]:
        if artifact_kind != "processed" or not get_l7_codec_upgrade_enabled():
            return pa_module.Table.from_pandas(frame, preserve_index=False), [], {}

        arrays: List[Any] = []
        names: List[str] = []
        float32_cols: List[str] = []
        encoding_registry: Dict[str, Dict[str, Any]] = {}
        fallback_reasons: List[str] = []

        for column in frame.columns:
            column_name = str(column)
            series = frame[column]
            encoding_type, window = self._infer_l7_processed_encoding(column_name)
            original_dtype = str(series.dtype)

            if encoding_type == RANK_UINT16_ENCODING:
                if window is None or window <= 0:
                    fallback_reasons.append(f"{column_name}:invalid_rank_window")
                else:
                    values = series.to_numpy(dtype=np.float32, copy=False)
                    try:
                        encoded = encode_rank_as_uint16(values, window)
                        decoded = decode_rank_from_uint16(encoded, window)
                        self._assert_rank_roundtrip(values, decoded, window)
                        arrays.append(pa_module.array(encoded))
                        names.append(column_name)
                        encoding_registry[column_name] = {
                            "encoding_type": RANK_UINT16_ENCODING,
                            "scale_factor": str(window * 2),
                            "nan_sentinel": str(int(RANK_UINT16_NAN_SENTINEL)),
                            "window": str(window),
                            "original_dtype": original_dtype,
                        }
                        continue
                    except EncodeFallbackRequired as exc:
                        fallback_reasons.append(f"{column_name}:{exc}")

                fallback_values = series.to_numpy(dtype=np.float32, copy=False)
                arrays.append(pa_module.array(fallback_values))
                names.append(column_name)
                float32_cols.append(column_name)
                continue

            if encoding_type in {ZSCORE_INT16_ENCODING, GAUSSIAN_INT16_ENCODING}:
                values = series.to_numpy(dtype=np.float32, copy=False)
                try:
                    encoded = encode_zscore_as_int16(values)
                    decoded = decode_zscore_from_int16(encoded)
                    self._assert_zscore_roundtrip(values, decoded)
                    arrays.append(pa_module.array(encoded))
                    names.append(column_name)
                    encoding_registry[column_name] = {
                        "encoding_type": encoding_type,
                        "scale_factor": str(int(ZSCORE_INT16_SCALE_FACTOR)),
                        "nan_sentinel": str(int(ZSCORE_INT16_NAN_SENTINEL)),
                        "window": None,
                        "original_dtype": original_dtype,
                    }
                    continue
                except EncodeFallbackRequired as exc:
                    fallback_reasons.append(f"{column_name}:{exc}")
                    fallback_values = series.to_numpy(dtype=np.float32, copy=False)
                    arrays.append(pa_module.array(fallback_values))
                    names.append(column_name)
                    float32_cols.append(column_name)
                    continue

            arrays.append(pa_module.array(series.to_numpy(copy=False)))
            names.append(column_name)

        if fallback_reasons:
            self.logger.warning(
                "[L7-Codec] integer encoding fallback columns=%d sample=%s",
                len(fallback_reasons),
                fallback_reasons[:5],
            )

        return pa_module.Table.from_arrays(arrays, names=names), float32_cols, encoding_registry

    @classmethod
    def _infer_l7_processed_encoding(cls, column_name: str) -> Tuple[Optional[str], Optional[int]]:
        lowered = column_name.lower()
        if "zscore" in lowered:
            return ZSCORE_INT16_ENCODING, None
        if "gaussian" in lowered or "gauss" in lowered:
            return GAUSSIAN_INT16_ENCODING, None
        if "rank" in lowered:
            return RANK_UINT16_ENCODING, cls._infer_rank_window(column_name)
        return None, None

    @staticmethod
    def _infer_rank_window(column_name: str) -> Optional[int]:
        import re

        patterns = (
            r"(?i)(?:rank|tsrank)[_\-]?w?([0-9]+)",
            r"(?i)w([0-9]+)[_\-]?(?:rank|tsrank)",
        )
        for pattern in patterns:
            match = re.search(pattern, column_name)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
        return None

    @staticmethod
    def _assert_rank_roundtrip(original: np.ndarray, decoded: np.ndarray, window: int) -> None:
        if not np.array_equal(np.isnan(original), np.isnan(decoded)):
            raise EncodeFallbackRequired("rank NaN mask mismatch")
        valid_mask = ~np.isnan(original)
        if not valid_mask.any():
            return
        max_diff = float(np.max(np.abs(decoded[valid_mask] - original[valid_mask])))
        if max_diff > (1.0 / float(2 * window)):
            raise EncodeFallbackRequired(f"rank roundtrip diff {max_diff} exceeds tolerance")

    @staticmethod
    def _assert_zscore_roundtrip(original: np.ndarray, decoded: np.ndarray) -> None:
        if not np.array_equal(np.isnan(original), np.isnan(decoded)):
            raise EncodeFallbackRequired("zscore NaN mask mismatch")
        valid_mask = ~np.isnan(original)
        if not valid_mask.any():
            return
        max_diff = float(np.max(np.abs(decoded[valid_mask] - original[valid_mask])))
        if max_diff > 0.001:
            raise EncodeFallbackRequired(f"zscore roundtrip diff {max_diff} exceeds tolerance")

    @staticmethod
    def _summarize_frame_dtype(frame: pd.DataFrame) -> str:
        if frame.empty and len(frame.columns) == 0:
            return "none"
        dtypes = sorted({str(dtype) for dtype in frame.dtypes})
        if not dtypes:
            return "none"
        if len(dtypes) == 1:
            return dtypes[0]
        return "mixed"

    @staticmethod
    def _calculate_nan_ratio(frame: pd.DataFrame) -> float:
        if frame.size == 0:
            return 0.0
        missing = int(frame.isna().to_numpy().sum())
        return float(missing / frame.size)

    # 單一全域 Lock(非 per-run_dir dict):RMW 為毫秒級 json 讀寫、非熱路徑,
    # 跨 run_dir 串行化代價可忽略;換取長駐進程零無界增長(Codex r3 finding)。
    _manifest_v2_thread_lock = threading.Lock()

    @classmethod
    @contextmanager
    def _manifest_v2_lock(cls, run_dir: Path):
        """Serialize manifest read-modify-write (in-process thread lock + cross-process flock)."""
        run_dir.mkdir(parents=True, exist_ok=True)
        thread_lock = cls._manifest_v2_thread_lock
        thread_lock.acquire()
        try:
            lock_path = run_dir / f"{cls.L7_V2_MANIFEST_NAME}.lock"
            with lock_path.open("a+", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            thread_lock.release()

    def _mark_manifest_artifact_incomplete_v2(self, run_dir: Path, artifact_kind: str) -> Optional[bytes]:
        """FFDSTAR Task 1.3 ⑤（§C D4）：將既有 manifest 之 run 與該 artifact 節點標為不完整（鎖內原子寫）；回傳標記前
        之原位元組供回復（無 manifest ⇒ None、不建檔）。"""
        with self._manifest_v2_lock(run_dir):
            manifest_path = run_dir / self.L7_V2_MANIFEST_NAME
            if not manifest_path.exists():
                return None
            original = manifest_path.read_bytes()
            manifest = json.loads(original.decode("utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError(f"Invalid feature manifest: {manifest_path}")
            manifest["complete"] = False
            node = (manifest.get("artifacts") or {}).get(artifact_kind)
            if isinstance(node, dict):
                node["complete"] = False
            self._write_feature_manifest_v2_unlocked(run_dir, manifest)
            return original

    def _restore_manifest_v2_bytes(self, run_dir: Path, original: Optional[bytes]) -> None:
        """回復 manifest 為標記前之原位元組（鎖內原子替換）；標記前無 manifest 而現有者 ⇒ 標為不完整（fail-closed）。"""
        if original is None:
            self._mark_manifest_artifact_incomplete_v2(run_dir, "raw")
            return
        with self._manifest_v2_lock(run_dir):
            manifest_path = run_dir / self.L7_V2_MANIFEST_NAME
            temp_path = run_dir / f"{self.L7_V2_MANIFEST_NAME}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            temp_path.write_bytes(original)
            os.replace(temp_path, manifest_path)

    @staticmethod
    def _install_staged_run_files(
        staging_root: Path,
        run_dir: Path,
        backup_root: Path,
        installed: List[Tuple[str, bool]],
    ) -> None:
        """FFDSTAR Task 1.3 ⑥：暫存根中之 run 根檔（row index、`provenance/` 紀錄檔；artifact 目錄已先安裝）逐檔安裝：
        既有之同名檔先移至 `backup_root` 同相對路徑，再以 `os.replace` 換入。`installed` 依序記 (相對路徑, 是否有舊檔)，
        於移動之前登記，供失敗時回復。"""
        staged = sorted(path for path in Path(staging_root).rglob("*") if path.is_file())
        for source in staged:
            relative = source.relative_to(staging_root)
            target = Path(run_dir) / relative
            had_previous = target.exists()
            installed.append((str(relative), had_previous))
            if had_previous:
                backup = Path(backup_root) / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)

    @staticmethod
    def _restore_staged_run_files(
        run_dir: Path,
        backup_root: Optional[Path],
        installed: List[Tuple[str, bool]],
    ) -> None:
        """`_install_staged_run_files` 之回復：有舊檔者自備份換回，原無者刪除新裝之檔；最後刪備份根。"""
        for relative, had_previous in reversed(list(installed)):
            target = Path(run_dir) / relative
            backup = None if backup_root is None else Path(backup_root) / relative
            if had_previous:
                if backup is not None and backup.exists():
                    os.replace(backup, target)
            elif target.exists():
                target.unlink()
        if backup_root is not None and Path(backup_root).exists():
            shutil.rmtree(backup_root)

    def _atomic_merge_feature_manifest_v2(
        self,
        run_dir: Path,
        *,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str,
        schema_version: str,
        quality_status: str,
        feature_schema_hash: str,
        row_count: int,
        time_range: Dict[str, Optional[str]],
        total_features: int,
        group_manifest: Dict[str, Dict[str, Any]],
        extra_metadata: Optional[Dict[str, Any]] = None,
        row_index: Optional[Dict[str, Any]] = None,
        completeness_meta: Optional[Dict[str, Any]] = None,
        preserve_root_completeness: bool = False,
        post_ic_arm: Optional[str] = None,
        content_sha256: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Locked read-modify-write so raw/processed writers cannot clobber each other.

        FFDSTAR Task 1.3 ⑦：`content_sha256`／`provenance`（給定者）寫入該 artifact 節點；本合併為 run 之唯一提交點。"""
        with self._manifest_v2_lock(run_dir):
            existing_manifest = self._load_feature_manifest_v2_if_exists(run_dir)
            manifest = self._build_feature_manifest_v2(
                existing_manifest=existing_manifest or None,
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                artifact_kind=artifact_kind,
                schema_version=schema_version,
                quality_status=quality_status,
                feature_schema_hash=feature_schema_hash,
                row_count=row_count,
                time_range=time_range,
                total_features=total_features,
                group_manifest=group_manifest,
                extra_metadata=extra_metadata,
                row_index=row_index,
                completeness_meta=completeness_meta,
                preserve_root_completeness=preserve_root_completeness,
                post_ic_arm=post_ic_arm,
                content_sha256=content_sha256,
                provenance=provenance,
            )
            self._write_feature_manifest_v2_unlocked(run_dir, manifest)
            return manifest

    def _build_feature_manifest_v2(
        self,
        *,
        existing_manifest: Optional[Dict[str, Any]],
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str,
        schema_version: str,
        quality_status: str,
        feature_schema_hash: str,
        row_count: int,
        time_range: Dict[str, Optional[str]],
        total_features: int,
        group_manifest: Dict[str, Dict[str, Any]],
        extra_metadata: Optional[Dict[str, Any]] = None,
        row_index: Optional[Dict[str, Any]] = None,
        completeness_meta: Optional[Dict[str, Any]] = None,
        preserve_root_completeness: bool = False,
        post_ic_arm: Optional[str] = None,
        content_sha256: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if existing_manifest:
            for key, expected in (("symbol", symbol), ("tf", tf), ("config_hash", config_hash)):
                actual = existing_manifest.get(key)
                if actual is not None and actual != expected:
                    raise ValueError(f"Manifest {key} mismatch: expected {expected}, got {actual}")

        # Task 2.1：不帶週期資訊之後續寫入（IC-first）不得覆蓋既有根之 completeness／品質欄
        preserved_root: Dict[str, Any] = {}
        if (
            preserve_root_completeness
            and existing_manifest
            and all(key in existing_manifest for key in ("expected_timeframes", "present_timeframes", "failed_timeframes"))
        ):
            preserved_root = {
                key: json.loads(json.dumps(existing_manifest[key]))
                for key in _ROOT_PRESERVED_COMPLETENESS_KEYS
                if key in existing_manifest
            }

        artifact_manifest = {
            "complete": True,
            "schema_version": schema_version,
            "quality_status": quality_status,
            "path": artifact_kind,
            "feature_schema_hash": feature_schema_hash,
            "row_count": row_count,
            "time_range": time_range,
            "total_features": total_features,
            "group_count": len(group_manifest),
            "groups": group_manifest,
        }
        if completeness_meta:
            artifact_manifest.update(completeness_meta)
            artifact_manifest["quality_status"] = str(completeness_meta.get("quality_status", quality_status))
        if preserved_root:
            # 後續寫入之 artifact 承襲 run 之 canonical completeness，使 resolve_run_status 與根一致
            # （否則 IC-first 覆寫後 artifacts 皆 complete、resume 閘誤判可快取；r1 codex P1-02）
            for key in COMPLETENESS_FIELD_NAMES + ("failure_reasons",):
                if key in preserved_root:
                    artifact_manifest[key] = json.loads(json.dumps(preserved_root[key]))
            if quality_status != "empty_selection" and "quality_status" in preserved_root:
                artifact_manifest["quality_status"] = str(preserved_root["quality_status"])
        if extra_metadata:
            artifact_manifest["metadata"] = dict(extra_metadata)
        if post_ic_arm is not None:  # ICFIRSTALIGN Task 3.2：processed 節點記 post-IC 臂名
            artifact_manifest["post_ic_arm"] = str(post_ic_arm)
        if content_sha256 is not None:  # FFDSTAR Task 1.3 ⑦（§C D2）：run 內容身分
            artifact_manifest["content_sha256"] = str(content_sha256)
        if provenance is not None:  # FFDSTAR Task 1.3 ⑦：紀錄檔指標（鍵見契約 manifest_provenance_keys）
            artifact_manifest["provenance"] = dict(provenance)
        manifest = existing_manifest or {
            "version": "l7_v2",
            "symbol": symbol,
            "tf": tf,
            "config_hash": config_hash,
            "artifacts": {},
        }
        manifest["complete"] = True
        manifest["created_at"] = manifest.get("created_at") or datetime.utcnow().isoformat()
        manifest["updated_at"] = datetime.utcnow().isoformat()
        manifest["schema_version"] = schema_version
        manifest["feature_schema_hash"] = feature_schema_hash
        manifest["total_features"] = total_features
        # FF-NAME §G ⑦（Task 2.6 通過條件；世代閘讀取端為 Task 3.4）：本 run 欄名之命名世代
        manifest["feature_naming_version"] = feature_naming.CURRENT_FEATURE_NAMING_VERSION
        manifest["groups"] = group_manifest
        if artifact_kind == "processed":
            # ICFIRSTALIGN Task 1.3：processed 之時間軸、列數、時間範圍只寫入其 artifact 節點；
            # 根之 time_range／row_count／row_index 只屬 raw（既存者不覆寫；無 raw 時亦不寫根 row_index）
            if row_index is not None:
                artifact_manifest["row_index"] = dict(row_index)
            if not existing_manifest:
                manifest["row_count"] = row_count
                manifest["time_range"] = time_range
        else:
            manifest["row_count"] = row_count
            manifest["time_range"] = time_range
            if row_index is not None:
                manifest["row_index"] = dict(row_index)
            elif artifact_kind == "raw":
                manifest.pop("row_index", None)
        if extra_metadata:
            manifest["generation_metadata"] = dict(extra_metadata)
        manifest.setdefault("artifacts", {})[artifact_kind] = artifact_manifest

        run_status = resolve_run_status(manifest)
        manifest["run_status"] = run_status
        manifest["quality_status"] = run_status
        if completeness_meta:
            for field in COMPLETENESS_FIELD_NAMES:
                if field in completeness_meta:
                    manifest[field] = completeness_meta[field]
            if "failure_reasons" in completeness_meta:
                manifest["failure_reasons"] = list(completeness_meta["failure_reasons"])
        manifest.update(preserved_root)
        return manifest

    @staticmethod
    def _build_schema_hash_from_columns(
        schema_version: str,
        group_manifest: Dict[str, Dict[str, Any]],
    ) -> str:
        schema_payload = {
            "schema_version": schema_version,
            "groups": {
                group_id: [str(column) for column in metadata.get("columns", [])]
                for group_id, metadata in sorted(group_manifest.items())
            },
        }
        encoded = json.dumps(schema_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _calculate_array_nan_ratio(data: np.ndarray) -> float:
        if data.size == 0:
            return 0.0
        missing = int(np.isnan(data).sum())
        return float(missing / data.size)

    @classmethod
    def _load_feature_manifest_v2_if_exists(cls, run_dir: Path) -> Dict[str, Any]:
        manifest_path = run_dir / cls.L7_V2_MANIFEST_NAME
        if not manifest_path.exists():
            return {}
        with manifest_path.open("r", encoding="utf-8") as manifest_file:
            loaded = json.load(manifest_file)
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid feature manifest: {manifest_path}")
        return loaded

    @classmethod
    def _write_feature_manifest_v2_unlocked(cls, run_dir: Path, manifest: Dict[str, Any]) -> None:
        """Write manifest JSON atomically; caller must hold ``_manifest_v2_lock``."""
        manifest_path = run_dir / cls.L7_V2_MANIFEST_NAME
        temp_path = run_dir / f"{cls.L7_V2_MANIFEST_NAME}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        with temp_path.open("w", encoding="utf-8") as manifest_file:
            json.dump(manifest, manifest_file, ensure_ascii=False, indent=2, default=str)
        os.replace(temp_path, manifest_path)

    @classmethod
    def _write_feature_manifest_v2(cls, run_dir: Path, manifest: Dict[str, Any]) -> None:
        """Backward-compatible manifest write with exclusive lock."""
        with cls._manifest_v2_lock(run_dir):
            cls._write_feature_manifest_v2_unlocked(run_dir, manifest)
    
    def save_features_to_hdf5(
        self,
        case_id: str,
        symbol: str,
        timeframe: str,
        features_df: pd.DataFrame,
        feature_names: List[str],
        labels: Optional[np.ndarray] = None,
        strategy_params: Optional[Dict] = None
    ) -> str:
        """
        儲存特徵至 HDF5
        
        Args:
            case_id: 案例 ID (e.g., "ETHUSDT_1735905600_1")
            symbol: 交易標的 (e.g., "ETHUSDT")
            timeframe: 時間週期 (e.g., "1h", "12h")
            features_df: 特徵 DataFrame (必須包含 timestamp 和所有特徵)
            feature_names: 特徵名稱列表
            labels: 標籤數組 (可選, 1=盈利, 0=虧損)
            strategy_params: 策略參數 (用於記錄元數據)
            
        Returns:
            檔案路徑
        """
        file_path = self.base_path / f"{case_id}.h5"
        
        self.logger.info(f"開始儲存特徵 - 案例: {case_id}, 檔案: {file_path}")
        
        try:
            with h5py.File(file_path, 'w') as f:
                # 建立群組
                group_path = f"{symbol}/{timeframe}"
                group = f.create_group(group_path)
                
                # 儲存特徵矩陣
                feature_matrix = features_df[feature_names].values.astype(np.float32)
                group.create_dataset(
                    'features',
                    data=feature_matrix,
                    compression='gzip',
                    compression_opts=4
                )
                
                # 儲存特徵名稱 (作為屬性)
                group.attrs['feature_names'] = feature_names
                group.attrs['feature_count'] = len(feature_names)
                
                # 儲存時間戳
                timestamps = features_df['timestamp'].values.astype(np.int64)
                group.create_dataset(
                    'timestamps',
                    data=timestamps,
                    compression='gzip'
                )
                
                # 儲存標籤 (如果有)
                if labels is not None:
                    group.create_dataset(
                        'labels',
                        data=labels.astype(np.int32),
                        compression='gzip'
                    )
                
                # 儲存元數據
                group.attrs['extraction_time'] = datetime.now().isoformat()
                group.attrs['case_id'] = case_id
                group.attrs['symbol'] = symbol
                group.attrs['timeframe'] = timeframe
                group.attrs['n_samples'] = len(features_df)
                group.attrs['generation_method'] = 'dynamic'
                
                if strategy_params:
                    group.attrs['strategy_type'] = strategy_params.get('strategy_type', 'unknown')
                    # 將策略參數序列化為字串
                    import json
                    group.attrs['strategy_params'] = json.dumps(
                        strategy_params.get('params', {})
                    )
                
                self.logger.info(
                    f"特徵儲存完成 - 樣本數: {len(features_df)}, "
                    f"特徵數: {len(feature_names)}, 檔案大小: {file_path.stat().st_size / 1024:.2f} KB"
                )
                
                return str(file_path)
                
        except Exception as e:
            self.logger.error(f"特徵儲存失敗: {str(e)}", exc_info=True)
            raise
    
    def load_features_from_hdf5(
        self,
        case_id: str,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Tuple[pd.DataFrame, List[str], Dict]:
        """
        從 HDF5 讀取特徵
        
        Args:
            case_id: 案例 ID
            symbol: 交易標的（可選，未提供時自動偵測）
            timeframe: 時間週期（可選，未提供時自動偵測）
            
        Returns:
            (features_df, feature_names, metadata)
        """
        file_path = self.base_path / f"{case_id}.h5"
        
        if not file_path.exists():
            raise FileNotFoundError(f"特徵檔案不存在: {file_path}")
        
        self.logger.info(f"開始讀取特徵 - 案例: {case_id}, 檔案: {file_path}")
        
        try:
            with h5py.File(file_path, 'r') as f:
                if symbol is None or timeframe is None:
                    symbols = list(f.keys())
                    if not symbols:
                        raise KeyError("HDF5 檔案沒有任何群組")
                    symbol = symbols[0]
                    timeframes = list(f[symbol].keys())
                    if not timeframes:
                        raise KeyError(f"群組不存在: {symbol}")
                    timeframe = timeframes[0]
                    if len(symbols) > 1 or len(timeframes) > 1:
                        self.logger.warning(
                            f"未指定 symbol/timeframe，使用第一個群組: {symbol}/{timeframe}"
                        )

                group_path = f"{symbol}/{timeframe}"

                if group_path not in f:
                    raise KeyError(f"群組不存在: {group_path}")

                group = f[group_path]
                
                # 讀取特徵矩陣
                feature_matrix = group['features'][:]
                
                # 讀取特徵名稱
                raw_feature_names = list(group.attrs['feature_names'])
                feature_names = [
                    n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                    for n in raw_feature_names
                ]
                
                # 讀取時間戳
                timestamps = group['timestamps'][:]
                
                # 建立 DataFrame
                features_df = pd.DataFrame(
                    feature_matrix,
                    columns=feature_names
                )
                features_df['timestamp'] = timestamps
                
                # 讀取標籤 (如果有)
                if 'labels' in group:
                    labels = group['labels'][:]
                    features_df['label'] = labels
                
                # 讀取元數據
                metadata = {
                    'case_id': group.attrs.get('case_id'),
                    'symbol': group.attrs.get('symbol'),
                    'timeframe': group.attrs.get('timeframe'),
                    'extraction_time': group.attrs.get('extraction_time'),
                    'n_samples': group.attrs.get('n_samples'),
                    'feature_count': group.attrs.get('feature_count'),
                    'generation_method': group.attrs.get('generation_method'),
                    'strategy_type': group.attrs.get('strategy_type'),
                }
                
                # 解析策略參數
                if 'strategy_params' in group.attrs:
                    import json
                    metadata['strategy_params'] = json.loads(group.attrs['strategy_params'])
                
                self.logger.info(
                    f"特徵讀取完成 - 樣本數: {len(features_df)}, 特徵數: {len(feature_names)}"
                )
                
                return features_df, feature_names, metadata
                
        except Exception as e:
            self.logger.error(f"特徵讀取失敗: {str(e)}", exc_info=True)
            raise

    # V7 §12 P0: max columns before auto-splitting a group
    MAX_GROUP_COLUMNS = 5000
    FLOAT16_MAX_REL_ERROR = 1e-3
    FLOAT16_MAX_ABS_ERROR = 1e-12

    @classmethod
    def _split_large_group(
        cls,
        group_id: str,
        columns: List[str],
        data: np.ndarray,
    ) -> List[Tuple[str, List[str], np.ndarray]]:
        """Split a group into sub-parts when column count exceeds MAX_GROUP_COLUMNS.

        Returns list of (part_id, part_columns, part_data_slice).
        Groups with <= MAX_GROUP_COLUMNS columns are returned as-is.
        """
        max_cols = cls.MAX_GROUP_COLUMNS
        if len(columns) <= max_cols:
            return [(group_id, columns, data)]

        parts: List[Tuple[str, List[str], np.ndarray]] = []
        for i, chunk_start in enumerate(range(0, len(columns), max_cols)):
            chunk_end = min(chunk_start + max_cols, len(columns))
            part_cols = columns[chunk_start:chunk_end]
            part_data = data[:, chunk_start:chunk_end]
            part_id = f"{group_id}_part{i + 1}"
            parts.append((part_id, part_cols, part_data))
        return parts

    @classmethod
    def _select_parquet_storage_array(cls, data: np.ndarray) -> Tuple[np.ndarray, str]:
        """Return a parquet-ready array only using float16 when its roundtrip is safe.

        Feature scales vary widely across symbols and data sources: BTC price-scale
        indicators can overflow float16, while tiny quote prices can underflow to
        zero. A roundtrip gate catches both cases plus excessive quantization error.
        """
        if data.size == 0:
            return _coerce_persistence_array(data).astype(np.float16), "float16"

        source = _coerce_persistence_array(np.asarray(data))
        with np.errstate(all="ignore"):
            data_float16 = source.astype(np.float16)

        finite_mask = np.isfinite(source)
        if not finite_mask.any():
            return data_float16, "float16"

        roundtrip = data_float16.astype(np.float32)
        finite_roundtrip = np.isfinite(roundtrip)
        if not bool(np.all(finite_roundtrip[finite_mask])):
            return source, "float32"

        source_finite = source[finite_mask]
        roundtrip_finite = roundtrip[finite_mask]
        abs_error = np.abs(roundtrip_finite - source_finite)
        tolerance = np.maximum(
            cls.FLOAT16_MAX_ABS_ERROR,
            np.abs(source_finite) * cls.FLOAT16_MAX_REL_ERROR,
        )

        if bool(np.any(abs_error > tolerance)):
            return source, "float32"

        return data_float16, "float16"

    @classmethod
    def _select_parquet_storage_columns(
        cls,
        data: np.ndarray,
        columns: List[str],
        pa_module: Any,
    ) -> Tuple[List[Any], str, List[str], Dict[str, int], int]:
        """Build parquet arrays with per-column float16/float32 fallback."""
        source = _coerce_persistence_array(data)
        arrays: List[Any] = []
        float32_cols: List[str] = []
        dtype_counts: Dict[str, int] = {}
        total_bytes = 0

        for col_idx, column_name in enumerate(columns):
            column_array, storage_dtype = cls._select_parquet_storage_array(source[:, col_idx])
            dtype_counts[storage_dtype] = dtype_counts.get(storage_dtype, 0) + 1
            if storage_dtype == "float32":
                float32_cols.append(str(column_name))
            total_bytes += int(np.asarray(column_array).nbytes)
            arrays.append(pa_module.array(column_array))

        if not dtype_counts:
            part_dtype = "float16"
        elif len(dtype_counts) == 1:
            part_dtype = next(iter(dtype_counts))
        else:
            part_dtype = "mixed"
        return arrays, part_dtype, float32_cols, dtype_counts, total_bytes

    @staticmethod
    def _summarize_storage_dtype(storage_dtypes: set[str]) -> str:
        if not storage_dtypes:
            return "float16"
        if len(storage_dtypes) == 1:
            return next(iter(storage_dtypes))
        return "mixed"

    @staticmethod
    def _build_dtype_summary(
        counts: Dict[str, int],
        float32_fallback_parts: List[str],
        column_counts: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Return a structured dtype summary embedded in the V7 manifest.

        ``counts`` keeps per-dtype part counts (float16 / float32). The list of
        parts that fell back to float32 is bounded so that the manifest stays
        small even when many groups overflow on alternative symbols (e.g.
        BTC); the truncation is recorded explicitly for downstream auditors.
        """
        max_listed = 256
        sorted_parts = sorted(float32_fallback_parts)
        summary: Dict[str, Any] = {
            "counts": dict(sorted(counts.items())),
            "column_counts": dict(sorted((column_counts or {}).items())),
            "float32_fallback_count": len(sorted_parts),
            "float32_fallback_parts": sorted_parts[:max_listed],
        }
        if len(sorted_parts) > max_listed:
            summary["float32_fallback_truncated"] = True
            summary["float32_fallback_listed"] = max_listed
        return summary

    def _precheck_l7_raw_stream_disk_space(
        self,
        output_dir: Path,
        groups_list: List[Tuple[str, Any]],
    ) -> None:
        """Fail fast for the streaming L6.5 → L7_raw path.

        Unlike the legacy L7 precheck, this uses the largest parquet part size
        rather than the largest whole group because the raw writer splits each
        group before staging. This prevents false failures on 8GB-tier runs with
        giant WorldQuant/Momentum groups while still protecting disk headroom.
        """
        if not groups_list:
            return

        final_bytes_per_cell = np.dtype(np.float16).itemsize
        fallback_bytes_per_cell = np.dtype(np.float32).itemsize
        estimated_final_bytes = 0
        reclaimable_npy_bytes = 0
        largest_part_id = "<none>"
        largest_part_bytes = 0

        for group_id, group in groups_list:
            n_rows, n_cols = group.shape
            cell_count = int(n_rows) * int(n_cols)
            estimated_final_bytes += cell_count * final_bytes_per_cell

            part_cols = min(int(n_cols), int(self.MAX_GROUP_COLUMNS))
            part_bytes = int(n_rows) * part_cols * fallback_bytes_per_cell
            if part_bytes > largest_part_bytes:
                largest_part_bytes = part_bytes
                largest_part_id = str(group_id)

            disk_path = getattr(group, "disk_path", None)
            try:
                if disk_path is not None and disk_path.exists():
                    reclaimable_npy_bytes += int(disk_path.stat().st_size)
            except OSError:
                pass

            shards = getattr(group, "shards", ()) or ()
            if shards:
                reclaimable_npy_bytes += sum(int(getattr(s, "nbytes", 0)) for s in shards)

        safety_factor = self._resolve_l7_disk_safety_factor()
        min_free_bytes = self._resolve_l7_min_free_bytes()
        net_growth_bytes = max(0, estimated_final_bytes - reclaimable_npy_bytes)
        part_required_bytes = int((net_growth_bytes + largest_part_bytes) * safety_factor)
        required_bytes = max(part_required_bytes, min_free_bytes)
        free_bytes = self._safe_disk_free_bytes(output_dir)
        if free_bytes is None:
            return

        if free_bytes < required_bytes:
            raise OSError(
                "Insufficient disk space for L7_raw streaming persist: "
                f"need ~{required_bytes / (1024 ** 3):.2f} GiB "
                f"(safety_factor={safety_factor:.2f}, estimated_final="
                f"{estimated_final_bytes / (1024 ** 3):.2f} GiB, reclaimable_npy="
                f"{reclaimable_npy_bytes / (1024 ** 3):.2f} GiB, net_growth="
                f"{net_growth_bytes / (1024 ** 3):.2f} GiB, max_inflight_part="
                f"{largest_part_bytes / (1024 ** 3):.2f} GiB, largest_part_source="
                f"{largest_part_id}, reserve_floor={min_free_bytes / (1024 ** 3):.2f} GiB), "
                f"available {free_bytes / (1024 ** 3):.2f} GiB at {output_dir}; "
                "clear data_cache/cgsa_work/* or lower FFACT_L7_DISK_SAFETY_FACTOR if you accept the risk."
            )

        self.logger.info(
            "[L7_raw] Disk pre-check OK: required=%.2f GiB (safety x%.2f), "
            "estimated_final=%.2f GiB, reclaimable_npy=%.2f GiB, net_growth=%.2f GiB, "
            "max_inflight_part=%.2f GiB, largest_part_source=%s, reserve_floor=%.2f GiB, "
            "free=%.2f GiB, groups=%d",
            required_bytes / (1024 ** 3),
            safety_factor,
            estimated_final_bytes / (1024 ** 3),
            reclaimable_npy_bytes / (1024 ** 3),
            net_growth_bytes / (1024 ** 3),
            largest_part_bytes / (1024 ** 3),
            largest_part_id,
            min_free_bytes / (1024 ** 3),
            free_bytes / (1024 ** 3),
            len(groups_list),
        )

    def _ensure_l7_raw_part_disk_space(
        self,
        output_dir: Path,
        *,
        part_id: str,
        source_group_id: str,
        part_estimate_bytes: int,
        source_reclaimable_bytes: int = 0,
    ) -> None:
        safety_factor = self._resolve_l7_disk_safety_factor()
        min_free_bytes = self._resolve_l7_min_free_bytes()
        required_bytes = max(int(part_estimate_bytes * safety_factor), min_free_bytes)
        free_bytes = self._safe_disk_free_bytes(output_dir)
        if free_bytes is None:
            return
        # Account for source shards that are still on disk but will be freed
        # when cleanup_source fires on the final chunk of the current group.
        # This mirrors the global pre-check's reclaimable_npy accounting and
        # prevents false-fail for large chunked groups where parquet parts
        # accumulate faster than the source can be released.
        effective_free = free_bytes + source_reclaimable_bytes
        if effective_free >= required_bytes:
            return

        raise OSError(
            "Insufficient disk space for L7_raw parquet part: "
            f"need ~{required_bytes / (1024 ** 3):.2f} GiB "
            f"(safety_factor={safety_factor:.2f}, part_estimate="
            f"{part_estimate_bytes / (1024 ** 3):.2f} GiB, reserve_floor="
            f"{min_free_bytes / (1024 ** 3):.2f} GiB, part_id={part_id}, "
            f"source_group_id={source_group_id}), available "
            f"{free_bytes / (1024 ** 3):.2f} GiB (effective "
            f"{effective_free / (1024 ** 3):.2f} GiB with "
            f"{source_reclaimable_bytes / (1024 ** 3):.2f} GiB pending release) "
            f"at {output_dir}; "
            "clear data_cache/cgsa_work/* or set FFACT_L7_MIN_FREE_GIB to a lower value "
            "only if you accept the risk."
        )

    @staticmethod
    def _resolve_l7_disk_safety_factor() -> float:
        raw = os.getenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.5").strip()
        try:
            value = float(raw)
        except ValueError:
            return 1.5
        # Refuse non-positive values; treat as default rather than letting the
        # check trivially pass.
        if value <= 0:
            return 1.5
        return value

    @staticmethod
    def _resolve_l7_min_free_bytes() -> int:
        raw = os.getenv("FFACT_L7_MIN_FREE_GIB", "2.0").strip()
        try:
            value = float(raw)
        except ValueError:
            value = 2.0
        if value < 0:
            value = 2.0
        return int(value * (1024 ** 3))

    @staticmethod
    def _safe_disk_free_bytes(path: Path) -> Optional[int]:
        try:
            path.mkdir(parents=True, exist_ok=True)
            import shutil as _shutil
            return int(_shutil.disk_usage(path).free)
        except OSError:
            return None

    @staticmethod
    def _resolve_positive_env(env_name: str, default_value: int) -> int:
        raw = os.getenv(env_name, str(default_value)).strip()
        try:
            parsed = int(raw)
        except ValueError:
            parsed = default_value
        return max(1, parsed)

    def get_feature_summary(
        self,
        case_id: str,
        symbol: str,
        timeframe: str
    ) -> Dict:
        """
        獲取特徵摘要統計
        
        Args:
            case_id: 案例 ID
            symbol: 交易標的
            timeframe: 時間週期
            
        Returns:
            特徵統計摘要
        """
        features_df, feature_names, metadata = self.load_features_from_hdf5(
            case_id, symbol, timeframe
        )
        
        # 計算統計量
        feature_stats = {}
        for feature in feature_names:
            stats = features_df[feature].describe()
            feature_stats[feature] = {
                'mean': float(stats['mean']),
                'std': float(stats['std']),
                'min': float(stats['min']),
                'max': float(stats['max']),
                '25%': float(stats['25%']),
                '50%': float(stats['50%']),
                '75%': float(stats['75%'])
            }
        
        # 計算相關矩陣 (只保存對角線以上部分)
        corr_matrix = features_df[feature_names].corr()
        correlation_pairs = []
        for i in range(len(feature_names)):
            for j in range(i + 1, len(feature_names)):
                corr = abs(corr_matrix.iloc[i, j])
                if corr > 0.7:  # 只記錄中高相關性
                    correlation_pairs.append({
                        'feature1': feature_names[i],
                        'feature2': feature_names[j],
                        'correlation': float(corr)
                    })
        
        # 排序 (由高到低)
        correlation_pairs.sort(key=lambda x: x['correlation'], reverse=True)
        
        summary = {
            'case_id': case_id,
            'symbol': symbol,
            'timeframe': timeframe,
            'feature_count': len(feature_names),
            'sample_count': len(features_df),
            'feature_names': feature_names,
            'feature_stats': feature_stats,
            'high_correlation_pairs': correlation_pairs[:20],  # 只返回前 20 對
            'metadata': metadata
        }
        
        return summary
