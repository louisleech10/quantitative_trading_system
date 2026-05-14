"""
Feature Storage - 特徵儲存管理

使用 HDF5 格式儲存和讀取特徵數據

Author: AI Agent
Date: 2026-01-10
"""

import os
import queue
import threading
import time
import h5py
import pandas as pd
import numpy as np
import json
import hashlib
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = None
    pq = None

from momentum.FeatureEngineering.core.column_group_registry import FailureType
from momentum.core.config import get_l7_codec_upgrade_enabled
from momentum.core.logging import get_logger

if TYPE_CHECKING:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

logger = get_logger(__name__)

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


class AsyncParquetCompactor:
    """Background compactor that merges small parquet column partitions."""

    def __init__(
        self,
        staging_dir: Path,
        final_dir: Path,
        target_rows: int = 100_000,
        min_files_to_compact: int = 8,
    ) -> None:
        self._staging_dir = Path(staging_dir)
        self._final_dir = Path(final_dir)
        self._target_rows = max(1, int(target_rows))
        self._min_files_to_compact = max(2, int(min_files_to_compact))
        self._queue: "queue.Queue[Optional[Tuple[str, Path, List[str]]]]" = queue.Queue()
        self._pending: List[Tuple[str, Path, int, List[str]]] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._error: Optional[BaseException] = None
        self._merged_outputs: List[Path] = []
        self._merged_sources: Dict[str, List[str]] = {}
        self._part_to_final_path: Dict[str, str] = {}
        self._merge_index = 0

    @property
    def merged_sources(self) -> Dict[str, List[str]]:
        """Return merged parquet filename -> source part ids mapping."""
        with self._lock:
            return {key: list(value) for key, value in self._merged_sources.items()}

    @property
    def part_to_final_path(self) -> Dict[str, str]:
        """Return source part id -> final parquet path mapping."""
        with self._lock:
            return dict(self._part_to_final_path)

    def start(self) -> None:
        """Start the background compactor worker."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="l7-parquet-compactor", daemon=True)
        self._thread.start()

    def enqueue(self, item: Tuple[str, Path, List[str]]) -> None:
        """Queue one staging parquet file for background compaction."""
        if self._error is not None:
            raise RuntimeError("AsyncParquetCompactor already failed") from self._error
        part_id, staging_path, float32_cols = item
        self._queue.put((part_id, Path(staging_path), list(float32_cols)))

    def finalize(self) -> List[Path]:
        """Flush remaining files, stop the worker, and return final parquet paths."""
        if self._thread is None:
            return []
        self._queue.put(None)
        self._thread.join()
        if self._error is not None:
            raise RuntimeError("AsyncParquetCompactor failed during finalize") from self._error
        with self._lock:
            return list(self._merged_outputs)

    def _run(self) -> None:
        try:
            while True:
                item = self._queue.get()
                if item is None:
                    self._flush_pending(force=True)
                    return

                part_id, staging_path, float32_cols = item
                row_count = self._read_row_count(staging_path)

                if row_count >= self._target_rows:
                    self._compact_batch([(part_id, staging_path, row_count, float32_cols)])
                    continue

                self._pending.append((part_id, staging_path, row_count, float32_cols))
                if len(self._pending) >= self._min_files_to_compact:
                    self._flush_pending(force=False)
        except BaseException as exc:
            self._error = exc

    def _flush_pending(self, force: bool) -> None:
        if not self._pending:
            return
        if not force and len(self._pending) < self._min_files_to_compact:
            return
        batch = list(self._pending)
        self._pending.clear()
        self._compact_batch(batch)

    def _compact_batch(self, batch: List[Tuple[str, Path, int, List[str]]]) -> None:
        start_time = time.perf_counter()
        final_path, source_ids = self._merge_batch(batch)
        elapsed = time.perf_counter() - start_time
        with self._lock:
            self._merged_outputs.append(final_path)
            self._merged_sources[final_path.name] = list(source_ids)
            resolved_path = str(final_path.resolve())
            for part_id in source_ids:
                self._part_to_final_path[part_id] = resolved_path
        logger.info(
            "[L7] Compactor merged %d parts into %s in %.2fs",
            len(source_ids),
            final_path.name,
            elapsed,
        )

    def _merge_batch(self, batch: List[Tuple[str, Path, int, List[str]]]) -> Tuple[Path, List[str]]:
        final_path = self._next_output_path()
        temp_path = self._next_temp_path(final_path)
        source_ids = [part_id for part_id, _path, _rows, _float32_cols in batch]

        if len(batch) == 1:
            part_id, staging_path, _row_count, _float32_cols = batch[0]
            os.replace(staging_path, final_path)
            return final_path, [part_id]

        try:
            merged_table = self._merge_tables(batch)
            merged_float32_cols = sorted(
                {
                    column
                    for _part_id, _path, _rows, float32_cols in batch
                    for column in float32_cols
                }
            )
            _write_parquet_with_codec(
                merged_table,
                temp_path,
                float32_cols=merged_float32_cols,
            )
            os.replace(temp_path, final_path)
            for _part_id, staging_path, _row_count, _float32_cols in batch:
                if staging_path.exists():
                    staging_path.unlink()
            return final_path, source_ids
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _merge_tables(self, batch: List[Tuple[str, Path, int, List[str]]]):
        pa_module, pq_module = _require_pyarrow()
        expected_rows: Optional[int] = None
        arrays: List[Any] = []
        names: List[str] = []

        for _part_id, staging_path, row_count, _float32_cols in batch:
            table = pq_module.read_table(staging_path)
            if expected_rows is None:
                expected_rows = row_count
            elif row_count != expected_rows:
                raise ValueError(
                    f"Compactor row mismatch: expected {expected_rows}, got {row_count} for {staging_path.name}"
                )

            for column_name in table.column_names:
                if column_name in names:
                    raise ValueError(f"Compactor duplicate column detected: {column_name}")
                names.append(column_name)
                arrays.append(table[column_name])

        return pa_module.Table.from_arrays(arrays, names=names)

    def _read_row_count(self, staging_path: Path) -> int:
        _, pq_module = _require_pyarrow()
        parquet_file = pq_module.ParquetFile(str(staging_path))
        return int(parquet_file.metadata.num_rows)

    def _next_output_path(self) -> Path:
        self._merge_index += 1
        return self._final_dir / f"merged_{self._merge_index:04d}.parquet"

    @staticmethod
    def _next_temp_path(final_path: Path) -> Path:
        return final_path.parent / f".{final_path.stem}.tmp{final_path.suffix}"


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

    L7_RAW_SCHEMA_VERSION = "raw_v1"
    L7_PROCESSED_SCHEMA_VERSION = "processed_v1"
    L7_V2_MANIFEST_NAME = "feature_manifest.json"
    
    def __init__(self, base_path: str = "data_cache/features"):
        """
        Args:
            base_path: 特徵儲存根目錄
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._chunk_rows = self._resolve_positive_env("FFACT_HDF5_CHUNK_ROWS", 256)
        self._chunk_cols = self._resolve_positive_env("FFACT_HDF5_CHUNK_COLS", 512)
        self._gzip_level = self._resolve_bounded_env("FFACT_HDF5_GZIP_LEVEL", 4, 0, 9)

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
    ) -> Path:
        """Write IC-First raw L7 groups to the canonical V2 raw path."""
        return self._write_l7_v2_artifact(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            groups=groups,
            artifact_kind="raw",
            schema_version=self.L7_RAW_SCHEMA_VERSION,
            allow_empty=False,
            quality_status="complete",
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
    ) -> Tuple[Path, Dict[str, Any]]:
        """Stream CGSA registry groups into the canonical L7_raw artifact.

        When ``preprocessor`` is provided, each group is transformed and written
        directly to parquet without rewriting the registry ``.npy`` file. This
        is the disk-safe L6.5 → L7_raw path used by IC-First and legacy CGSA
        generation.
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

        def _write_group(
            group_id: str,
            columns: List[str],
            data: np.ndarray,
            source_group_id: str,
            source_disk_path: Optional[Path],
            cleanup_source: bool,
        ) -> None:
            nonlocal row_count, total_values, non_nan_values, total_inf, groups_with_inf
            nonlocal npy_freed, source_deleted

            safe_group_id = self._safe_path_segment(str(group_id), "group_id")
            columns_list = [str(column) for column in columns]

            # Multi-TF column tf-tagging.
            # CGSA mode skips _apply_timeframe_tag (multi_tf_generator.py) so 1h and
            # 12h groups both produce identical column names (e.g. "close_trend_EMA_20").
            # When IC engine calls ic_scores.update(group_ic) across groups the later
            # TF silently overwrites the earlier one — resulting in "only 1h" output and
            # no tf markers in feature names.  Fix: insert the group's tf as the 2nd
            # name segment (matching legacy _apply_timeframe_tag format):
            #   "close_trend_EMA_20"  →  "close_1h_trend_EMA_20"  (group 1h_L1_trend_EMA)
            #   "close_trend_EMA_20"  →  "close_12h_trend_EMA_20" (group 12h_L1_trend_EMA)
            _gid_tf = str(group_id).split("_", 1)[0]  # e.g. "1h", "12h", "4h"
            # Valid TF: digits + one of m/h/d  (e.g. "1m", "1h", "4h", "12h", "1d")
            if _gid_tf and _gid_tf[-1] in ("m", "h", "d") and _gid_tf[:-1].isdigit():
                _tf_guard = _gid_tf + "_"
                _tagged: List[str] = []
                for _c in columns_list:
                    _cp = _c.split("_", 1)
                    # Idempotent: skip if already tagged with this exact tf
                    if len(_cp) == 2 and not _cp[1].startswith(_tf_guard):
                        _tagged.append(f"{_cp[0]}_{_gid_tf}_{_cp[1]}")
                    else:
                        _tagged.append(_c)
                columns_list = _tagged

            array = np.asarray(data, dtype=np.float32)
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

            total_values += int(array.size)
            if array.size:
                nan_mask = np.isnan(array)
                non_nan_values += int(array.size - nan_mask.sum())
                inf_count = int(np.isinf(array).sum())
                total_inf += inf_count
                if inf_count > 0:
                    groups_with_inf += 1

            parts = self._split_large_group(safe_group_id, columns_list, array)
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
                _write_parquet_with_codec(
                    table,
                    staging_path,
                    float32_cols=float32_cols,
                    schema_metadata=parquet_metadata,
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

            ordered_group_manifest = {group_id: group_manifest[group_id] for group_id in sorted(group_manifest)}
            feature_schema_hash = self._build_schema_hash_from_columns(
                self.L7_RAW_SCHEMA_VERSION,
                ordered_group_manifest,
            )
            resolved_row_count = int(row_count or 0)
            resolved_time_range = time_range or {"start": None, "end": None}
            coverage = float(non_nan_values / total_values) if total_values else 0.0
            inf_ratio = float(total_inf / total_values) if total_values else 0.0
            validation_summary = {
                "has_nan": bool(non_nan_values < total_values),
                "has_inf": bool(total_inf > 0),
                "coverage": coverage,
                "inf_count": int(total_inf),
                "inf_ratio": inf_ratio,
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
                "dtype_summary": self._build_dtype_summary(
                    storage_dtype_counts,
                    float32_fallback_parts,
                    storage_dtype_column_counts,
                ),
            }
            if extra_metadata:
                stream_metadata.update(extra_metadata)

            manifest = self._build_feature_manifest_v2(
                run_dir=run_dir,
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                artifact_kind="raw",
                schema_version=self.L7_RAW_SCHEMA_VERSION,
                quality_status="complete",
                feature_schema_hash=feature_schema_hash,
                row_count=resolved_row_count,
                time_range=resolved_time_range,
                total_features=total_features,
                group_manifest=ordered_group_manifest,
                extra_metadata=stream_metadata,
            )

            if final_artifact_dir.exists():
                backup_dir = run_dir / f".previous-raw-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                os.replace(final_artifact_dir, backup_dir)

            os.replace(temp_artifact_dir, final_artifact_dir)
            artifact_installed = True
            self._write_feature_manifest_v2(run_dir, manifest)

            if backup_dir is not None and backup_dir.exists():
                shutil.rmtree(backup_dir)

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
    ) -> Path:
        """Write IC-First processed L7 groups to the canonical V2 processed path."""
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

        feature_schema_hash = self._build_l7_v2_schema_hash(
            schema_version=schema_version,
            group_items=group_items,
        )
        row_count = self._resolve_l7_v2_row_count(group_items)
        time_range = self._resolve_l7_v2_time_range(group_items)

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

            manifest = self._build_feature_manifest_v2(
                run_dir=run_dir,
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
            )

            if final_artifact_dir.exists():
                backup_dir = run_dir / f".previous-{artifact_kind}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                os.replace(final_artifact_dir, backup_dir)

            os.replace(temp_artifact_dir, final_artifact_dir)
            artifact_installed = True
            self._write_feature_manifest_v2(run_dir, manifest)

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

    def _build_feature_manifest_v2(
        self,
        run_dir: Path,
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
    ) -> Dict[str, Any]:
        existing_manifest = self._load_feature_manifest_v2_if_exists(run_dir)
        if existing_manifest:
            for key, expected in (("symbol", symbol), ("tf", tf), ("config_hash", config_hash)):
                actual = existing_manifest.get(key)
                if actual is not None and actual != expected:
                    raise ValueError(f"Manifest {key} mismatch: expected {expected}, got {actual}")

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
        if extra_metadata:
            artifact_manifest["metadata"] = dict(extra_metadata)
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
        manifest["quality_status"] = quality_status
        manifest["feature_schema_hash"] = feature_schema_hash
        manifest["row_count"] = row_count
        manifest["time_range"] = time_range
        manifest["total_features"] = total_features
        manifest["groups"] = group_manifest
        if extra_metadata:
            manifest["generation_metadata"] = dict(extra_metadata)
        manifest.setdefault("artifacts", {})[artifact_kind] = artifact_manifest
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
    def _write_feature_manifest_v2(cls, run_dir: Path, manifest: Dict[str, Any]) -> None:
        manifest_path = run_dir / cls.L7_V2_MANIFEST_NAME
        temp_path = run_dir / f"{cls.L7_V2_MANIFEST_NAME}.tmp"
        with temp_path.open("w", encoding="utf-8") as manifest_file:
            json.dump(manifest, manifest_file, ensure_ascii=False, indent=2, default=str)
        os.replace(temp_path, manifest_path)
    
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

    def save_factory_output(self, symbol: str, timeframe: str, result) -> str:
        """儲存工廠輸出：features.h5 + meta.json"""
        file_path = self.base_path / f"{symbol}_{timeframe}_factory.h5"
        self.save_metadata_json(symbol, timeframe, result.metadata or {})

        self.logger.info(f"開始儲存工廠輸出 - {symbol}/{timeframe}")

        features_df = result.features_df
        labels_df = result.labels_df

        feature_names = list(features_df.columns)
        label_names = list(labels_df.columns) if labels_df is not None else []

        if "timestamp" in features_df.columns:
            timestamps = features_df["timestamp"].to_numpy(dtype=np.int64)
        else:
            timestamps = features_df.index.to_numpy()
            if isinstance(features_df.index, pd.DatetimeIndex):
                timestamps = features_df.index.view("int64")

        try:
            with h5py.File(file_path, "w") as f:
                group = f.create_group(f"{symbol}/{timeframe}")

                # Use .values to get underlying array directly (memmap if
                # disk-backed) instead of .to_numpy() which may force a copy.
                features_arr = features_df.values
                if features_arr.dtype != np.float32:
                    features_arr = np.asarray(features_arr, dtype=np.float32)
                feature_chunks = self._build_2d_chunks(features_arr.shape)
                group.create_dataset(
                    "features",
                    data=features_arr,
                    compression="gzip",
                    compression_opts=self._gzip_level,
                    chunks=feature_chunks,
                )

                timestamp_chunks = self._build_1d_chunks(timestamps.shape)
                group.create_dataset(
                    "timestamps",
                    data=timestamps,
                    compression="gzip",
                    compression_opts=self._gzip_level,
                    chunks=timestamp_chunks,
                )

                if labels_df is not None and not labels_df.empty:
                    labels_arr = labels_df.to_numpy(dtype=np.float32)
                    label_chunks = self._build_2d_chunks(labels_arr.shape)
                    group.create_dataset(
                        "labels",
                        data=labels_arr,
                        compression="gzip",
                        compression_opts=self._gzip_level,
                        chunks=label_chunks,
                    )
                    group.attrs["label_names"] = label_names

                str_dtype = h5py.string_dtype(encoding="utf-8")
                group.create_dataset(
                    "feature_names",
                    data=np.array(feature_names, dtype=object),
                    dtype=str_dtype,
                )

                if label_names:
                    group.create_dataset(
                        "label_names",
                        data=np.array(label_names, dtype=object),
                        dtype=str_dtype,
                    )

                group.attrs["feature_count"] = len(feature_names)
                group.attrs["label_count"] = len(label_names)
                group.attrs["metadata_json"] = json.dumps(result.metadata or {})

            self.logger.info(
                f"工廠輸出儲存完成 - 特徵數: {len(feature_names)}, 標籤數: {len(label_names)}"
            )
            return str(file_path)
        except Exception as e:
            self.logger.error(f"工廠輸出儲存失敗: {str(e)}", exc_info=True)
            raise

    # V7 §12 P0: max columns before auto-splitting a group
    MAX_GROUP_COLUMNS = 5000
    FLOAT16_MAX_REL_ERROR = 1e-3
    FLOAT16_MAX_ABS_ERROR = 1e-12

    @staticmethod
    def _classify_persist_failure(error: BaseException) -> FailureType:
        """Classify parquet persistence failures for logging and diagnostics."""
        if isinstance(error, MemoryError):
            return FailureType.OOM
        if isinstance(error, (OSError, IOError)):
            return FailureType.IO_ERROR
        if isinstance(error, (ValueError, TypeError)):
            return FailureType.VALIDATION
        return FailureType.CONFIG

    def _persist_parts_parallel(
        self,
        parts_queue: List[Tuple[str, Any, Path, Path, List[str]]],
        n_workers: int,
        compactor: Optional[AsyncParquetCompactor] = None,
        compression_level: int = 1,
    ) -> List[str]:
        """Persist parquet parts with optional parallel writes and async compaction."""
        if not parts_queue:
            return []

        start_time = time.perf_counter()

        def _write_one(item: Tuple[str, Any, Path, Path, List[str]]) -> str:
            part_id, table, final_path, staging_path, float32_cols = item
            _write_parquet_with_codec(
                table,
                staging_path,
                float32_cols=float32_cols,
                compression_level=compression_level,
            )
            if compactor is not None:
                compactor.enqueue((part_id, staging_path, float32_cols))
            else:
                os.replace(staging_path, final_path)
            return str(final_path.resolve())

        try:
            if n_workers <= 1 or len(parts_queue) == 1:
                results = [_write_one(item) for item in parts_queue]
            else:
                with ThreadPoolExecutor(max_workers=n_workers) as pool:
                    results = list(pool.map(_write_one, parts_queue))
        except Exception as exc:
            failure_type = self._classify_persist_failure(exc)
            self.logger.error(
                "[L7] Parallel persist failed: failure_type=%s error=%s",
                failure_type.value,
                str(exc),
                exc_info=True,
            )
            raise

        elapsed = time.perf_counter() - start_time
        self.logger.info(
            "[L7] Parallel persist: %d parts in %.2fs, %d workers",
            len(results),
            elapsed,
            max(1, int(n_workers)),
        )
        return results

    def persist_registry_to_parquet(
        self,
        symbol: str,
        config_hash: str,
        registry: "ColumnGroupRegistry",
        cleanup_intermediate: bool = False,
    ) -> List[str]:
        """Persist CGSA registry groups to per-group parquet files.

        V7 enhancements:
        - float16 cast before writing when roundtrip-safe (halves storage)
        - float32 fallback for parts that would overflow, underflow, or lose too much precision
        - Auto-split groups with > MAX_GROUP_COLUMNS columns
        - Write manifest.json + columns.json.gz after all groups persisted

        Uses bounded batched staging: groups are converted to parquet-ready parts,
        flushed through the L7 writer, and their backing .npy files are deleted
        once the batch is durably accepted.
        """
        pa_module, _ = _require_pyarrow()
        from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config

        # Phase B Phase 1 Step 14: V7 path was designed for legacy single-file
        # `.npy` groups; sharded groups must go through the streaming raw-sink
        # (`write_raw_from_registry_stream`) which knows how to release shards
        # incrementally. Detect sharded sources and refuse with a clear error
        # rather than risking OOM during full registry concat.
        sharded_groups = [
            group_id
            for group_id, group in registry.iter_all()
            if getattr(group, "shards", ()) and len(group.shards) > 1
        ]
        if sharded_groups:
            preview = ", ".join(sharded_groups[:3])
            raise NotImplementedError(
                "persist_registry_to_parquet (V7 path) does not support sharded "
                f"CGSA groups; found {len(sharded_groups)} sharded groups (e.g. "
                f"{preview}). Use FeatureStorage.write_raw_from_registry_stream "
                "(L7_raw streaming path) instead. Set FFACT_CGSA_SHARD_BYTES to "
                "a value larger than your group sizes to disable sharding for "
                "legacy V7 testing."
            )

        output_dir = self.base_path / symbol / config_hash
        output_dir.mkdir(parents=True, exist_ok=True)

        staging_dir = output_dir / f".staging_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        staging_dir.mkdir(parents=True, exist_ok=False)

        persisted_paths: List[str] = []
        parquet_path_map: Dict[str, str] = {}
        # V7 manifest groups metadata
        manifest_groups: Dict[str, Dict] = {}
        all_columns: List[str] = []
        storage_dtypes: set[str] = set()
        # Per-dtype counters + per-part fallback list (Task 1: dtype_summary).
        # Future cross-symbol parity audits compare these counts to detect when
        # a previously-float16 group fell back to float32 on a different symbol
        # (which would silently change parquet bytes / overall_sha).
        storage_dtype_counts: Dict[str, int] = {}
        storage_dtype_column_counts: Dict[str, int] = {}
        float32_fallback_parts: List[str] = []
        total_rows: int = 0
        npy_freed = 0
        preserve_staging = False
        part_to_group_id: Dict[str, str] = {}
        first_part_by_group: Dict[str, str] = {}

        try:
            groups_list = list(registry.iter_all())
            total_groups = len(groups_list)
            max_group_columns = max((len(group.columns) for _group_id, group in groups_list), default=0)
            tier = get_memory_tier()
            tier_cfg = get_tier_config(tier)
            n_workers = self._resolve_positive_env(
                "FFACT_L7_WORKERS",
                int(tier_cfg["l7_workers"]),
            )
            # Tier-aware zstd compression level (Q2 optimisation).
            # Env var FFACT_L7_ZSTD_LEVEL overrides tier auto-detect.
            zstd_level: int = self._resolve_positive_env(
                "FFACT_L7_ZSTD_LEVEL",
                int(tier_cfg.get("l7_zstd_level", 1)),
            )
            compactor_enabled = os.getenv("FFACT_L7_COMPACTOR_ENABLED", "1").strip() != "0"
            target_rows = self._resolve_positive_env("FFACT_L7_COMPACTOR_TARGET_ROWS", 100_000)
            chunk_bars = tier_cfg.get("chunk_bars")
            use_compactor = (
                compactor_enabled
                and n_workers > 1
                and chunk_bars is not None
                and max_group_columns <= self.MAX_GROUP_COLUMNS
                and total_groups > 1
            )
            compactor: Optional[AsyncParquetCompactor] = None
            if use_compactor:
                compactor = AsyncParquetCompactor(
                    staging_dir=staging_dir,
                    final_dir=output_dir,
                    target_rows=target_rows,
                )
                compactor.start()

            pending_parts: List[Tuple[str, Any, Path, Path, List[str]]] = []
            pending_disk_paths: Dict[str, Path] = {}
            # P3.1 (2026-04-25): Tier-aware batch_limit. The previous
            # ``n_workers * 2`` over-pipelined the producer on small-RAM tiers
            # (8gb): up to 8 Arrow Tables (each ~group_size float16) lingered
            # in RAM before flush, contributing to the persist-phase plateau.
            # Cap at ``n_workers`` for tiers where the K-line buffer is tight;
            # 16gb+ keeps the 2x pipeline depth for max throughput.
            tier_label = str(tier).lower()
            batch_multiplier = 1 if "8" in tier_label and "gb" in tier_label else 2
            batch_limit = max(1, n_workers * batch_multiplier)

            self._precheck_l7_disk_space(
                output_dir,
                groups_list,
                batch_limit=batch_limit,
            )

            def _flush_pending_parts() -> None:
                nonlocal pending_parts, pending_disk_paths, npy_freed, persisted_paths
                if not pending_parts:
                    return
                batch_results = self._persist_parts_parallel(
                    pending_parts,
                    n_workers=n_workers,
                    compactor=compactor,
                    compression_level=zstd_level,
                )
                if compactor is None:
                    persisted_paths.extend(batch_results)

                for group_id, disk_path in pending_disk_paths.items():
                    if disk_path.exists():
                        disk_path.unlink()
                        npy_freed += 1
                pending_parts = []
                pending_disk_paths = {}

            for idx, (group_id, group) in enumerate(groups_list, 1):
                # P3.1 (2026-04-25): Skip the wasteful float32 materialization.
                # ``registry.load_data`` returns a memory-mapped read-only
                # array; the previous ``np.asarray(..., dtype=np.float32)``
                # forced a full RAM copy as float32 (4 bytes/cell) only for
                # the very next line to ``astype(np.float16)`` (2 bytes/cell)
                # and discard the float32. We retain the validation contract
                # by checking the mmap shape directly and let the f16 cast
                # do the one-and-only allocation in the part loop below.
                mmap_arr = registry.load_data(group_id)
                if mmap_arr.ndim != 2:
                    raise ValueError(f"Group {group_id} data must be 2D, got shape={mmap_arr.shape}")
                if mmap_arr.shape[1] != len(group.columns):
                    raise ValueError(
                        f"Group {group_id} columns mismatch: expected {len(group.columns)}, got {mmap_arr.shape[1]}"
                    )

                if total_rows == 0 and mmap_arr.shape[0] > 0:
                    total_rows = mmap_arr.shape[0]

                columns_list = list(group.columns)

                # Auto-split groups exceeding MAX_GROUP_COLUMNS (V7 §12 P0).
                # ``_split_large_group`` only slices columns (no copy); slices
                # of an mmap stay mmap-backed.
                parts = self._split_large_group(group_id, columns_list, mmap_arr)

                for part_id, part_cols, part_data in parts:
                    (
                        arrays,
                        storage_dtype,
                        float32_cols,
                        column_dtype_counts,
                        _part_estimate_bytes,
                    ) = self._select_parquet_storage_columns(part_data, part_cols, pa_module)
                    storage_dtypes.add(storage_dtype)
                    storage_dtype_counts[storage_dtype] = (
                        storage_dtype_counts.get(storage_dtype, 0) + 1
                    )
                    for dtype_name, dtype_count in column_dtype_counts.items():
                        storage_dtype_column_counts[dtype_name] = (
                            storage_dtype_column_counts.get(dtype_name, 0) + dtype_count
                        )
                    if float32_cols:
                        float32_fallback_parts.append(part_id)

                    staged_path = staging_dir / f"{part_id}.parquet"
                    final_path = output_dir / f"{part_id}.parquet"

                    table = pa_module.Table.from_arrays(arrays, names=list(part_cols))
                    pending_parts.append((part_id, table, final_path, staged_path, float32_cols))
                    part_to_group_id[part_id] = group_id
                    first_part_by_group.setdefault(group_id, part_id)

                    manifest_groups[part_id] = {
                        "file": f"{part_id}.parquet",
                        "column_count": len(part_cols),
                        "columns": list(part_cols),
                        "dtype": storage_dtype,
                    }
                    all_columns.extend(part_cols)
                    del arrays

                if group.disk_path and group.disk_path.exists():
                    pending_disk_paths[group_id] = group.disk_path

                del mmap_arr

                if len(pending_parts) >= batch_limit:
                    _flush_pending_parts()

                if idx % 100 == 0 or idx == total_groups:
                    self.logger.info(
                        "[L7] Persisted %d/%d groups (%d .npy freed)",
                        idx, total_groups, npy_freed,
                    )

            _flush_pending_parts()

            compaction_manifest: Dict[str, List[str]] = {}
            part_to_final_path: Dict[str, str]
            if compactor is not None:
                merged_paths = compactor.finalize()
                persisted_paths = [str(path.resolve()) for path in merged_paths]
                part_to_final_path = compactor.part_to_final_path
                compaction_manifest = compactor.merged_sources
            else:
                part_to_final_path = {
                    part_id: str((output_dir / f"{part_id}.parquet").resolve())
                    for part_id in manifest_groups
                }

            for part_id, group_metadata in manifest_groups.items():
                resolved_path = part_to_final_path.get(part_id)
                if resolved_path:
                    group_metadata["file"] = Path(resolved_path).name

            for group_id, first_part_id in first_part_by_group.items():
                resolved_path = part_to_final_path.get(first_part_id)
                if resolved_path:
                    parquet_path_map[group_id] = resolved_path

            if parquet_path_map:
                registry.set_group_parquet_paths(parquet_path_map)

            # Write V7 manifest.json + columns.json.gz
            self._write_v7_manifest(
                output_dir=output_dir,
                symbol=symbol,
                config_hash=config_hash,
                total_features=len(all_columns),
                total_rows=total_rows,
                groups=manifest_groups,
                compaction_sources=compaction_manifest,
                dtype=self._summarize_storage_dtype(storage_dtypes),
                dtype_summary=self._build_dtype_summary(
                    storage_dtype_counts,
                    float32_fallback_parts,
                    storage_dtype_column_counts,
                ),
            )
            self._write_columns_json_gz(output_dir, all_columns)

            self.logger.info(
                "CGSA per-group parquet persist completed: symbol=%s config_hash=%s "
                "groups=%d npy_freed=%d total_features=%d dtype=%s",
                symbol,
                config_hash,
                len(persisted_paths),
                npy_freed,
                len(all_columns),
                self._summarize_storage_dtype(storage_dtypes),
            )
            return persisted_paths
        except Exception as e:
            failure_type = self._classify_persist_failure(e)
            self.logger.error(
                "CGSA per-group parquet persist failed: symbol=%s config_hash=%s failure_type=%s error=%s",
                symbol,
                config_hash,
                failure_type.value,
                str(e),
                exc_info=True,
            )
            raise
        finally:
            if staging_dir.exists() and not preserve_staging:
                shutil.rmtree(staging_dir)

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
            return data.astype(np.float16), "float16"

        source = np.asarray(data, dtype=np.float32)
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
        source = np.asarray(data, dtype=np.float32)
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

    def _precheck_l7_disk_space(
        self,
        output_dir: Path,
        groups_list: List[Tuple[str, Any]],
        batch_limit: int = 1,
    ) -> None:
        """Fail fast using the extra disk budget needed by streaming L7 writes."""
        if not groups_list:
            return

        final_bytes_per_cell = np.dtype(np.float16).itemsize
        fallback_bytes_per_cell = np.dtype(np.float32).itemsize
        estimated_final_bytes = 0
        reclaimable_npy_bytes = 0
        largest_group_id = "<none>"
        largest_group_bytes = 0

        for group_id, group in groups_list:
            n_rows, n_cols = group.shape
            cell_count = int(n_rows) * int(n_cols)
            nominal_final_bytes = cell_count * final_bytes_per_cell
            fallback_group_bytes = cell_count * fallback_bytes_per_cell
            estimated_final_bytes += nominal_final_bytes
            if fallback_group_bytes > largest_group_bytes:
                largest_group_bytes = fallback_group_bytes
                largest_group_id = str(group_id)

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
        max_inflight_staging_bytes = largest_group_bytes * max(1, int(batch_limit))
        net_growth_bytes = max(0, estimated_final_bytes - reclaimable_npy_bytes)
        required_bytes = int((net_growth_bytes + max_inflight_staging_bytes) * safety_factor)

        free_bytes = self._safe_disk_free_bytes(output_dir)
        if free_bytes is None:
            return  # disk_usage unavailable; fall back to per-group guard

        if free_bytes < required_bytes:
            raise OSError(
                "Insufficient disk space for L7 persist: "
                f"need ~{required_bytes / (1024 ** 3):.2f} GiB "
                f"(safety_factor={safety_factor:.2f}, estimated_final="
                f"{estimated_final_bytes / (1024 ** 3):.2f} GiB, reclaimable_npy="
                f"{reclaimable_npy_bytes / (1024 ** 3):.2f} GiB, net_growth="
                f"{net_growth_bytes / (1024 ** 3):.2f} GiB, max_inflight_staging="
                f"{max_inflight_staging_bytes / (1024 ** 3):.2f} GiB, "
                f"largest_group={largest_group_id}:{largest_group_bytes / (1024 ** 3):.2f} GiB), "
                f"available {free_bytes / (1024 ** 3):.2f} GiB at {output_dir}; "
                f"groups={len(groups_list)}; clear data_cache/cgsa_work/* or lower "
                "FFACT_L7_DISK_SAFETY_FACTOR if you accept the risk."
            )

        self.logger.info(
            "[L7] Disk pre-check OK: required=%.2f GiB (safety x%.2f), "
            "estimated_final=%.2f GiB, reclaimable_npy=%.2f GiB, net_growth=%.2f GiB, "
            "max_inflight_staging=%.2f GiB, largest_group=%s:%.2f GiB, free=%.2f GiB, groups=%d",
            required_bytes / (1024 ** 3),
            safety_factor,
            estimated_final_bytes / (1024 ** 3),
            reclaimable_npy_bytes / (1024 ** 3),
            net_growth_bytes / (1024 ** 3),
            max_inflight_staging_bytes / (1024 ** 3),
            largest_group_id,
            largest_group_bytes / (1024 ** 3),
            free_bytes / (1024 ** 3),
            len(groups_list),
        )

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
    def _write_v7_manifest(
        output_dir: Path,
        symbol: str,
        config_hash: str,
        total_features: int,
        total_rows: int,
        groups: Dict[str, Dict],
        compaction_sources: Optional[Dict[str, List[str]]] = None,
        dtype: str = "float16",
        dtype_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write V7-format manifest.json (without full column names inline)."""
        manifest = {
            "version": "7.0",
            "symbol": symbol,
            "config_hash": config_hash,
            "created_at": datetime.utcnow().isoformat(),
            "total_features": total_features,
            "total_rows": total_rows,
            "dtype": dtype,
            "groups": groups,
        }
        if dtype_summary is not None:
            manifest["dtype_summary"] = dtype_summary
        if compaction_sources:
            manifest["compaction"] = {
                "merged_files": compaction_sources,
            }
        manifest_path = output_dir / "manifest.json"
        temp_path = output_dir / "manifest.json.tmp"
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, manifest_path)

    @staticmethod
    def _write_columns_json_gz(output_dir: Path, all_columns: List[str]) -> None:
        """Write compressed columns.json.gz containing all feature names."""
        import gzip as _gzip

        gz_path = output_dir / "columns.json.gz"
        temp_path = output_dir / "columns.json.gz.tmp"
        with _gzip.open(temp_path, "wt", encoding="utf-8") as f:
            json.dump(all_columns, f)
        os.replace(temp_path, gz_path)

    def _build_2d_chunks(self, shape: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        if len(shape) != 2:
            return None
        rows, cols = int(shape[0]), int(shape[1])
        if rows <= 0 or cols <= 0:
            return None
        return (min(rows, self._chunk_rows), min(cols, self._chunk_cols))

    def _build_1d_chunks(self, shape: Tuple[int, ...]) -> Optional[Tuple[int]]:
        if len(shape) != 1:
            return None
        rows = int(shape[0])
        if rows <= 0:
            return None
        return (min(rows, self._chunk_rows),)

    @staticmethod
    def _resolve_positive_env(env_name: str, default_value: int) -> int:
        raw = os.getenv(env_name, str(default_value)).strip()
        try:
            parsed = int(raw)
        except ValueError:
            parsed = default_value
        return max(1, parsed)

    @staticmethod
    def _resolve_bounded_env(env_name: str, default_value: int, lower: int, upper: int) -> int:
        raw = os.getenv(env_name, str(default_value)).strip()
        try:
            parsed = int(raw)
        except ValueError:
            parsed = default_value
        return max(lower, min(upper, parsed))

    def load_factory_output(self, symbol: str, timeframe: str):
        """載入工廠輸出"""
        file_path = self.base_path / f"{symbol}_{timeframe}_factory.h5"
        if not file_path.exists():
            return None

        try:
            with h5py.File(file_path, "r") as f:
                group_path = f"{symbol}/{timeframe}"
                if group_path not in f:
                    return None
                group = f[group_path]

                features = group["features"][:]
                timestamps = group["timestamps"][:]
                feature_names = []
                if "feature_names" in group:
                    raw_feature_names = list(group["feature_names"][:])
                    feature_names = [
                        n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                        for n in raw_feature_names
                    ]
                else:
                    raw_feature_names = list(group.attrs.get("feature_names", []))
                    feature_names = [
                        n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                        for n in raw_feature_names
                    ]

                features_df = pd.DataFrame(features, columns=feature_names)
                features_df.index = pd.Index(timestamps, name="timestamp")

                labels_df = pd.DataFrame(index=features_df.index)
                if "labels" in group:
                    labels = group["labels"][:]
                    label_names: List[str] = []
                    if "label_names" in group:
                        raw_label_names = list(group["label_names"][:])
                        label_names = [
                            n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                            for n in raw_label_names
                        ]
                    labels_df = pd.DataFrame(labels, columns=label_names, index=features_df.index)

                metadata = {}
                metadata_json = group.attrs.get("metadata_json")
                if metadata_json:
                    try:
                        metadata = json.loads(metadata_json)
                    except json.JSONDecodeError:
                        metadata = {}

            from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult

            result = FeatureGenerationResult(
                features_df=features_df,
                labels_df=labels_df,
                metadata=metadata,
                feature_count=features_df.shape[1],
                generation_time=metadata.get("generation_time", 0.0),
                layer_counts=metadata.get("layer_counts", {}),
                config_used=metadata.get("config_used", {}),
                hdf5_path=str(file_path),
            )

            numeric_cols = result.features_df.select_dtypes(include=["float64"]).columns
            if len(numeric_cols) > 0:
                result.features_df[numeric_cols] = result.features_df[numeric_cols].astype(np.float32)

            return result
        except Exception as e:
            self.logger.error(f"工廠輸出讀取失敗: {str(e)}", exc_info=True)
            raise

    def save_metadata_json(self, symbol: str, timeframe: str, metadata: Dict) -> str:
        """儲存 features_meta.json"""
        file_path = self.base_path / f"{symbol}_{timeframe}_factory_meta.json"
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=True, indent=2)
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Metadata 儲存失敗: {str(e)}", exc_info=True)
            raise
    
    def feature_file_exists(self, case_id: str) -> bool:
        """檢查特徵檔案是否存在"""
        file_path = self.base_path / f"{case_id}.h5"
        return file_path.exists()
    
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
    
    def delete_features(self, case_id: str) -> bool:
        """
        刪除特徵檔案
        
        Args:
            case_id: 案例 ID
            
        Returns:
            是否成功刪除
        """
        file_path = self.base_path / f"{case_id}.h5"
        
        if not file_path.exists():
            self.logger.warning(f"特徵檔案不存在，無法刪除: {file_path}")
            return False
        
        try:
            file_path.unlink()
            self.logger.info(f"特徵檔案已刪除: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"刪除特徵檔案失敗: {str(e)}", exc_info=True)
            return False
    
    def list_feature_files(self) -> List[Dict]:
        """
        列出所有特徵檔案
        
        Returns:
            特徵檔案列表，每個元素包含 case_id, file_path, file_size, modified_time
        """
        feature_files = []
        
        for file_path in self.base_path.glob("*.h5"):
            case_id = file_path.stem  # 檔名 (不含副檔名)
            
            feature_files.append({
                'case_id': case_id,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        # 按修改時間排序 (最新的在前)
        feature_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return feature_files
