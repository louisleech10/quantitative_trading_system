#!/usr/bin/env python3
"""產生 L6.5 IC-First golden baseline（移除 legacy 前凍結用）。

read-only 腳本：從真實 kline 跑 IC-First 兩段式 L6.5，輸出 manifest + 指紋至
tests/golden/l65_hardening/。供 B2 移除 legacy 後 byte 級回歸對照。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.FeatureEngineering.preprocessing._d_star_cache import (  # noqa: E402
    PreprocessingContext,
    compute_data_fingerprint,
    compute_feature_schema_hash,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (  # noqa: E402
    FeaturePreprocessor,
)
from momentum.core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

DEFAULT_GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden" / "l65_hardening"
KLINE_CACHE_PATH = PROJECT_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
SYMBOLS: Tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "ADAUSDT")
TIMEFRAMES: Tuple[str, ...] = ("1h", "4h")
DEFAULT_MAX_ROWS = 2000
DEFAULT_MAX_COLS = 500
IC_FIRST_SELECTED_FEATURE_COUNT = 20
LAYER_RE = re.compile(r"^(L\d+)_")

# 固定 row-index 抽樣規則（相對於 tail(max_rows) 後的 DataFrame，不足則 clamp）
FIXED_SAMPLE_ROW_INDICES: Tuple[int, ...] = (
    0,
    1,
    10,
    50,
    100,
    250,
    500,
    750,
    1000,
    1250,
    1500,
    1750,
    1999,
)


class GoldenBaselineError(RuntimeError):
    """golden baseline 產生或校驗失敗。"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
    ).strip()


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _canonical_array_bytes(values: np.ndarray) -> bytes:
    """與 freeze_failopen_baseline 一致的 canonical float hash 位元組。"""
    array = np.asarray(values)
    canonical = np.array(array, copy=True, order="C")
    if canonical.dtype.kind == "f":
        nan_mask = np.isnan(canonical)
        negative_zero = (canonical == 0) & np.signbit(canonical)
        canonical[nan_mask] = np.nan
        canonical[negative_zero] = -0.0
    if canonical.dtype.itemsize > 1:
        canonical = canonical.astype(canonical.dtype.newbyteorder("<"), copy=False)
    return canonical.tobytes(order="C")


def _ic_first_config_payload() -> Dict[str, Any]:
    """IC-First 唯一路徑 baseline 用的 preprocessing config（移除 legacy 後應一致）。"""
    return {
        "enabled": True,
        "mode": "replace",
        "ic_first_pipeline": True,
        "causal_preprocessing": True,
        "calibration_bars": 500,
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.01, 0.99],
            "window": 252,
            "apply_to": "all",
        },
        "fractional_differencing": {
            "enabled": True,
            "d_range": [0.0, 1.0],
            "adf_threshold": 0.10,
            "weight_threshold": 1e-5,
            "precision": 0.01,
            "apply_to": "non_stationary",
            "cache_d_star": True,
        },
        "adf_differencing": {
            "enabled": True,
            "adf_threshold": 0.10,
            "max_diff": 1,
            "sample_size": 500,
            "apply_to": "non_stationary",
        },
        "rank_transform": {"enabled": True, "window": 252, "apply_to": "all"},
        "gaussian_normalize": {
            "enabled": True,
            "clip_range": [0.001, 0.999],
            "apply_to": "all",
        },
        "adaptive_zscore": {
            "enabled": True,
            "windows": [100, 252],
            "epsilon": 1e-8,
            "apply_to": "all",
        },
    }


def _pre_ic_config(full: Dict[str, Any]) -> Dict[str, Any]:
    """IC-First pre_ic：winsor + fracdiff/adf，關閉 rank/zscore/gaussian。"""
    config = json.loads(json.dumps(full))
    for step in ("rank_transform", "adaptive_zscore", "gaussian_normalize"):
        if isinstance(config.get(step), dict):
            config[step]["enabled"] = False
    return config


def _post_ic_config(full: Dict[str, Any]) -> Dict[str, Any]:
    """IC-First post_ic：rank/zscore/gaussian，關閉 winsor/fracdiff/adf。"""
    config = json.loads(json.dumps(full))
    for step in ("winsorization", "fractional_differencing", "adf_differencing"):
        if isinstance(config.get(step), dict):
            config[step]["enabled"] = False
    for step in ("rank_transform", "adaptive_zscore", "gaussian_normalize"):
        if isinstance(config.get(step), dict):
            config[step]["enabled"] = True
    return config


def _load_hdf5_kline_frame(symbol: str, tf: str, hdf5_path: Path) -> pd.DataFrame:
    if not hdf5_path.exists():
        raise GoldenBaselineError(
            f"缺少真實 kline：{hdf5_path.relative_to(PROJECT_ROOT)} 不存在，"
            "不得產假 baseline。"
        )

    import h5py

    dataset_key = f"{symbol}/{tf}/data"
    with h5py.File(hdf5_path, "r") as h5_file:
        if dataset_key not in h5_file:
            raise GoldenBaselineError(
                f"缺少 HDF5 dataset {dataset_key} in {hdf5_path.relative_to(PROJECT_ROOT)}"
            )
        records = h5_file[dataset_key][()]

    frame = pd.DataFrame.from_records(records)
    if "timestamp" in frame.columns:
        unit = "ms" if int(frame["timestamp"].max()) > 10**12 else "s"
        frame.index = pd.to_datetime(frame["timestamp"], unit=unit, utc=True)
    return frame


def _build_l1_l2_real_features(raw_frame: pd.DataFrame, max_cols: int) -> pd.DataFrame:
    """從真實 kline OHLCV 衍生 L1/L2 特徵（與 build_l65_golden 一致）。"""
    numeric = raw_frame.select_dtypes(include=[np.number]).copy()
    numeric = numeric.drop(columns=["timestamp"], errors="ignore")
    if numeric.empty:
        raise GoldenBaselineError("真實 kline 無可用數值欄位")

    frames: List[pd.DataFrame] = []
    base_columns = ["open", "high", "low", "close", "volume", "quote_volume", "taker_ratio"]
    for column in base_columns:
        if column in numeric.columns:
            frames.append(
                pd.DataFrame({f"L1_binance_{column}": numeric[column].astype(np.float32)})
            )

    close = (
        numeric["close"].astype(float)
        if "close" in numeric.columns
        else numeric.iloc[:, 0].astype(float)
    )
    volume = numeric["volume"].astype(float) if "volume" in numeric.columns else close.abs()
    derived: Dict[str, pd.Series] = {
        "L2_derived_close_return_1": close.pct_change(),
        "L2_derived_log_close": np.log(close.replace(0.0, np.nan).abs()),
        "L2_derived_volume_change_1": volume.pct_change(),
    }
    for window in (3, 5, 8, 13, 21, 34, 55, 89):
        derived[f"L2_derived_close_mean_{window}"] = close.rolling(window, min_periods=1).mean()
        derived[f"L2_derived_close_std_{window}"] = close.rolling(window, min_periods=2).std()
        derived[f"L2_derived_volume_mean_{window}"] = volume.rolling(window, min_periods=1).mean()

    frames.append(pd.DataFrame(derived, index=raw_frame.index))
    feature_frame = pd.concat(frames, axis=1).replace([np.inf, -np.inf], np.nan)
    feature_frame = feature_frame.iloc[:, :max_cols]
    return feature_frame.astype(np.float32, copy=False)


def _resolve_sample_row_indices(n_rows: int) -> List[int]:
    if n_rows <= 0:
        return []
    return sorted({min(idx, n_rows - 1) for idx in FIXED_SAMPLE_ROW_INDICES})


def _select_ic_first_features(columns: Sequence[str], count: int) -> List[str]:
    """固定 feature-id 集合：依欄名排序後取前 count 個。"""
    ordered = sorted(str(column) for column in columns)
    return ordered[: min(count, len(ordered))]


def _per_feature_stats(frame: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    stats: Dict[str, Dict[str, float]] = {}
    for column in frame.columns:
        series = frame[column].astype(np.float64)
        valid = series.dropna()
        stats[str(column)] = {
            "mean": float(valid.mean()) if not valid.empty else float("nan"),
            "std": float(valid.std()) if len(valid) > 1 else float("nan"),
            "nan_ratio": float(series.isna().mean()),
        }
    return stats


def _sampled_value_and_nan_hashes(
    frame: pd.DataFrame,
    row_indices: Sequence[int],
) -> Tuple[str, str]:
    """固定 row-index 抽樣的 value hash 與 NaN mask hash。"""
    value_digest = hashlib.sha256()
    mask_digest = hashlib.sha256()
    columns = list(frame.columns)
    for row_idx in row_indices:
        row = frame.iloc[row_idx]
        for column in columns:
            value = float(row[column]) if pd.notna(row[column]) else np.nan
            value_digest.update(_canonical_array_bytes(np.array([value], dtype=np.float64)))
            mask_digest.update(
                np.packbits(np.array([int(pd.isna(row[column]))], dtype=np.uint8), bitorder="little").tobytes()
            )
    return value_digest.hexdigest(), mask_digest.hexdigest()


def _fingerprint_frame(frame: pd.DataFrame) -> Dict[str, Any]:
    """單一 DataFrame 的 schema + 統計 + 抽樣 hash。"""
    columns = [str(column) for column in frame.columns]
    dtypes = {str(column): str(frame[column].dtype) for column in frame.columns}
    row_indices = _resolve_sample_row_indices(len(frame))
    value_hash, nan_mask_hash = _sampled_value_and_nan_hashes(frame, row_indices)
    return {
        "feature_count": len(columns),
        "feature_names_sha256": _sha256_payload(columns),
        "feature_ids": columns,
        "dtypes": dtypes,
        "per_feature_stats": _per_feature_stats(frame),
        "sample_row_indices": list(row_indices),
        "sampled_value_hash": value_hash,
        "nan_mask_hash": nan_mask_hash,
        "rows": int(len(frame)),
    }


def _run_ic_first_l65(
    source_frame: pd.DataFrame,
    symbol: str,
    tf: str,
    full_config: Dict[str, Any],
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """跑 IC-First 兩段式 L6.5，回傳 (pre_ic, post_ic, selected_features)。"""
    with tempfile.TemporaryDirectory(prefix="l65_hardening_dstar_") as temp_dir:
        original_cache_dir = FeaturePreprocessor.__dict__["_d_star_cache_dir"]
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: Path(temp_dir))
        try:
            data_fingerprint, _weak = compute_data_fingerprint(source_frame)
            context = PreprocessingContext(
                symbol=symbol,
                timeframe=tf,
                config_hash=_sha256_payload(full_config)[:16],
                data_fingerprint=data_fingerprint,
                feature_schema_hash=compute_feature_schema_hash(source_frame.columns),
                time_range=(
                    int(source_frame.index[0].value),
                    int(source_frame.index[-1].value),
                )
                if len(source_frame) > 0
                else None,
                row_count=len(source_frame),
                source_data_version="l65-hardening-v1",
            )
            pre_ic_pp = FeaturePreprocessor(_pre_ic_config(full_config), context=context)
            pre_ic_frame = pre_ic_pp.transform(source_frame)
            selected = _select_ic_first_features(
                list(pre_ic_frame.columns),
                IC_FIRST_SELECTED_FEATURE_COUNT,
            )
            post_ic_pp = FeaturePreprocessor(_post_ic_config(full_config), context=context)
            post_ic_frame = post_ic_pp.transform(pre_ic_frame.loc[:, selected])
        finally:
            FeaturePreprocessor._d_star_cache_dir = original_cache_dir

    return pre_ic_frame, post_ic_frame, selected


def _build_symbol_tf_record(
    symbol: str,
    tf: str,
    max_rows: int,
    max_cols: int,
    full_config: Dict[str, Any],
) -> Dict[str, Any]:
    raw_frame = _load_hdf5_kline_frame(symbol, tf, KLINE_CACHE_PATH)
    if len(raw_frame) < 100:
        raise GoldenBaselineError(
            f"{symbol}/{tf} 資料列數不足：{len(raw_frame)} < 100"
        )
    recent = raw_frame.tail(max_rows)
    source_frame = _build_l1_l2_real_features(recent, max_cols=max_cols)
    pre_ic_frame, post_ic_frame, selected = _run_ic_first_l65(
        source_frame,
        symbol,
        tf,
        full_config,
    )
    return {
        "symbol": symbol,
        "timeframe": tf,
        "source_rows": int(len(recent)),
        "source_cols": int(source_frame.shape[1]),
        "selected_feature_ids": selected,
        "selected_feature_count": len(selected),
        "pre_ic": _fingerprint_frame(pre_ic_frame),
        "post_ic": _fingerprint_frame(post_ic_frame),
    }


def build_baseline(
    out_dir: Path = DEFAULT_GOLDEN_DIR,
    *,
    max_rows: int = DEFAULT_MAX_ROWS,
    max_cols: int = DEFAULT_MAX_COLS,
) -> Dict[str, Any]:
    """產生 IC-First golden baseline + manifest。"""
    full_config = _ic_first_config_payload()
    config_hash = _sha256_payload(full_config)
    manifest: Dict[str, Any] = {
        "schema_version": 1,
        "mode": "ic_first_l65",
        "git_sha": _git_sha(),
        "generated_at_utc": _utc_now(),
        "kline_path": str(KLINE_CACHE_PATH.relative_to(PROJECT_ROOT)),
        "config_hash": config_hash,
        "config": full_config,
        "symbols": list(SYMBOLS),
        "timeframes": list(TIMEFRAMES),
        "sampling": {
            "max_rows": max_rows,
            "max_cols": max_cols,
            "fixed_row_indices_rule": list(FIXED_SAMPLE_ROW_INDICES),
            "ic_first_selected_feature_count": IC_FIRST_SELECTED_FEATURE_COUNT,
            "feature_selection": "sorted_column_names_take_first_n",
        },
        "records": {},
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    for symbol in SYMBOLS:
        manifest["records"][symbol] = {}
        for tf in TIMEFRAMES:
            logger.info("[L6.5 hardening] building %s/%s", symbol, tf)
            record = _build_symbol_tf_record(symbol, tf, max_rows, max_cols, full_config)
            manifest["records"][symbol][tf] = record
            record_path = out_dir / f"{symbol}_{tf}_baseline.json"
            _atomic_write_json(record_path, record)

    manifest_path = out_dir / "manifest.json"
    _atomic_write_json(manifest_path, manifest)
    logger.info("[L6.5 hardening] manifest written: %s", manifest_path)
    return manifest


def _compare_float(a: float, b: float, *, rel_tol: float = 1e-4, abs_tol: float = 1e-6) -> bool:
    if np.isnan(a) and np.isnan(b):
        return True
    if np.isnan(a) or np.isnan(b):
        return False
    return bool(np.isclose(a, b, rtol=rel_tol, atol=abs_tol))


def _compare_fingerprint(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    *,
    label: str,
) -> List[str]:
    """比對 fingerprint，回傳差異清單。"""
    errors: List[str] = []
    for key in (
        "feature_count",
        "feature_names_sha256",
        "feature_ids",
        "sample_row_indices",
        "sampled_value_hash",
        "nan_mask_hash",
        "rows",
    ):
        if expected.get(key) != actual.get(key):
            errors.append(f"{label}.{key}: expected={expected.get(key)!r} actual={actual.get(key)!r}")

    expected_stats = expected.get("per_feature_stats") or {}
    actual_stats = actual.get("per_feature_stats") or {}
    if set(expected_stats) != set(actual_stats):
        errors.append(
            f"{label}.per_feature_stats keys mismatch: "
            f"expected={len(expected_stats)} actual={len(actual_stats)}"
        )
    for feature_id, exp_stat in expected_stats.items():
        act_stat = actual_stats.get(feature_id)
        if act_stat is None:
            errors.append(f"{label}.{feature_id}: missing in actual")
            continue
        if not _compare_float(float(exp_stat["nan_ratio"]), float(act_stat["nan_ratio"])):
            errors.append(
                f"{label}.{feature_id}.nan_ratio: "
                f"expected={exp_stat['nan_ratio']} actual={act_stat['nan_ratio']}"
            )
        for stat_key in ("mean", "std"):
            if not _compare_float(float(exp_stat[stat_key]), float(act_stat[stat_key])):
                errors.append(
                    f"{label}.{feature_id}.{stat_key}: "
                    f"expected={exp_stat[stat_key]} actual={act_stat[stat_key]}"
                )
    return errors


def check_baseline(
    out_dir: Path = DEFAULT_GOLDEN_DIR,
    *,
    max_rows: int = DEFAULT_MAX_ROWS,
    max_cols: int = DEFAULT_MAX_COLS,
) -> bool:
    """自驗：重算指紋並與已存 manifest 比對。"""
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        raise GoldenBaselineError(f"缺少 manifest：{manifest_path}")

    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    full_config = stored.get("config") or _ic_first_config_payload()
    all_errors: List[str] = []

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            record_path = out_dir / f"{symbol}_{tf}_baseline.json"
            if not record_path.exists():
                all_errors.append(f"missing record file: {record_path}")
                continue
            expected_record = json.loads(record_path.read_text(encoding="utf-8"))
            actual_record = _build_symbol_tf_record(symbol, tf, max_rows, max_cols, full_config)
            for stage in ("pre_ic", "post_ic"):
                all_errors.extend(
                    _compare_fingerprint(
                        expected_record[stage],
                        actual_record[stage],
                        label=f"{symbol}/{tf}/{stage}",
                    )
                )
            if expected_record.get("selected_feature_ids") != actual_record.get(
                "selected_feature_ids"
            ):
                all_errors.append(
                    f"{symbol}/{tf}.selected_feature_ids mismatch"
                )

    if all_errors:
        for err in all_errors:
            logger.error("[L6.5 hardening] check FAIL: %s", err)
        return False

    logger.info("[L6.5 hardening] check PASS: %d symbol×tf records stable", len(SYMBOLS) * len(TIMEFRAMES))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify L6.5 IC-First golden baseline (l65_hardening)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="重算指紋並與 tests/golden/l65_hardening/ 已存 baseline 比對",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_GOLDEN_DIR))
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--max-cols", type=int, default=DEFAULT_MAX_COLS)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    try:
        if args.check:
            ok = check_baseline(out_dir, max_rows=args.max_rows, max_cols=args.max_cols)
            return 0 if ok else 1
        build_baseline(out_dir, max_rows=args.max_rows, max_cols=args.max_cols)
    except GoldenBaselineError as exc:
        logger.error("[L6.5 hardening] %s", exc)
        return 1
    except Exception as exc:
        logger.error("[L6.5 hardening] unexpected failure: %s", exc, exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
