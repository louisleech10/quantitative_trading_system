#!/usr/bin/env python3
"""LA-1 B0: 可重現改前 golden baseline（五路徑 legacy 輸出）。

SPEC: docs/IC_LA1_SPEC.md §G / B0.1
TODO: docs/IC_LA1_TODO.md Task 0.1

入口契約（LA-0 級）:
  - ICFilterOrchestrator.analyze(features_path, labels_path, meta_path, kline_reader=…)
  - features HDF5 + meta JSON（symbol/timeframe/config_hash + per-feature 條目）
  - kline group key: data_cache/feature_klines/kline_cache.h5 → /{SYMBOL}/{tf}/data
  - helpers 沿用 LA-0；persist 導 tmp（禁污染 data_cache）

五路徑:
  ① regime rule grouped IC
  ② kmeans grouped IC
  ③ RegimeDetector.detect_phases_for_index（XGBoost 路徑）
  ④ long_short
  ⑤ fallback（短樣本 insufficient_data）

B4 control 三路徑（完整 raw report 樹 + volatile sentinel scrub）:
  ① regime OFF
  ② long_short OFF
  ③ 非觸發 fallback（全量輸入 + 預設 min_test_rows）
  契約: *_control_*_full.json = 全樹（禁投影）；volatile 以 RFC6901 denylist scrub

--check assert:
  ① §0.1 兩 input kline sha 重驗
  ② early-flip manifest 兩側 len>0
  ③ baseline JSON 五路徑鍵齊全
  ④ 三 control full artifact + rules + receipt 三者 sha 自洽
"""

from __future__ import annotations

import argparse
import atexit
import copy
import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import h5py
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from momentum.Analysis.long_short_analyzer import LongShortAnalyzer  # noqa: E402
from momentum.factories import (  # noqa: E402
    create_ic_analyzer,
    create_kline_storage_manager,
    create_regime_detector,
)

# ---------------------------------------------------------------------------
# 凍結常數（SPEC §G canonical mutation + 輸入 receipt）
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).resolve().parent
INPUTS_DIR = OUTPUT_DIR / "inputs"
KLINE_CACHE_DIR = "data_cache/feature_klines"
KLINE_H5_PATH = REPO_ROOT / KLINE_CACHE_DIR / "kline_cache.h5"
KLINE_H5_GROUP_TEMPLATE = "/{symbol}/{timeframe}/data"
SCHEMA_VERSION = "la1_b0_v1"

# SPEC §G FACT-RECEIPT（Claude h5py 2026-07-16）
EXPECTED_KLINE: dict[tuple[str, str], dict[str, Any]] = {
    ("BTCUSDT", "1h"): {
        "rows": 20352,
        "sha16": "1c93c37938a4917a",
    },
    ("ETHUSDT", "12h"): {
        "rows": 1696,
        "sha16": "00d1ee985ad3f09f",
    },
}

# Canonical mutation 常數（SPEC §G；內嵌禁口頭改）
M_TRUNC_RATIO = 0.75  # n_keep = int(0.75 * n)
EARLY_WINDOW_RATIO = 2.0 / 3.0  # early = [0, int(2/3 * n_keep))
REFIT_INTERVAL_CONST = 50  # mid-segment trunc = prev_end + REFIT_INTERVAL//2

# 五路徑鍵（--check assert ③）
PATH_KEYS = (
    "regime_rule",
    "regime_kmeans",
    "xgboost_phases",
    "long_short",
    "fallback",
)

# B4 control 三路徑（各自獨立完整 artifact；禁測試內現建 expected）
CONTROL_SCHEMA_VERSION = "la1_b0_control_v2"
CONTROL_KINDS = (
    "regime_off",
    "ls_off",
    "non_trigger_fallback",
)
# control artifact 必含頂層鍵（--check / deep-equal 契約）
CONTROL_REQUIRED_KEYS = (
    "schema_version",
    "control_kind",
    "symbol",
    "timeframe",
    "config_hash",
    "input_contract",
    "control_config",
    "report",
    "mask_membership_control",
    "volatile_rules_sha256",
    "content_sha256",
)

# volatile denylist / receipt（SYNTHESIS B4-CODEX-1）
CONTROL_VOLATILE_RULES_NAME = "control_volatile_rules.json"
CONTROL_VOLATILE_RECEIPT_NAME = "control_volatile_receipt.json"
VOLATILE_SENTINEL_KEY = "__volatile__"
NONFINITE_MARKER_KEY = "__nonfinite__"
CONTROL_ATOL = 1e-12

_ISO8601_TS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$"
)
_ISOLATED_TMP_PATH_RE = re.compile(
    r"(?:^|/)(?:var/folders|tmp|private/var/folders).*"
    r"(?:la1_b0_sidefx_|/T/).+\.h5$",
    re.IGNORECASE,
)
_VALIDATOR_REGEX: dict[str, "re.Pattern[str]"] = {
    "iso8601_timestamp": _ISO8601_TS_RE,
    "isolated_tmp_path": _ISOLATED_TMP_PATH_RE,
}
_KNOWN_VOLATILE_PRODUCERS: dict[str, dict[str, str]] = {
    "/generated_at": {
        "expected_type": "str",
        "validator": "iso8601_timestamp",
        "reason": "per-run wall-clock from ICReporter.build_report",
        "producer_ref": "momentum/Analysis/ic_reporter.py:329",
    },
    "/metadata/filtered_generated_at": {
        "expected_type": "str",
        "validator": "iso8601_timestamp",
        "reason": "mirrors report generated_at after filtered features write",
        "producer_ref": "momentum/Analysis/ic_filter_orchestrator.py:3490",
    },
    "/metadata/filtered_features_path": {
        "expected_type": "str",
        "validator": "isolated_tmp_path",
        "reason": "absolute path under process-local sidefx tmp for filtered HDF5",
        "producer_ref": "momentum/Analysis/ic_filter_orchestrator.py:3488",
    },
}

# 特徵輸入：沿用 LA-0 已物化真實 features（非合成）
LA0_INPUTS_DIR = REPO_ROOT / "tests" / "golden" / "la0" / "inputs"

RUNS: list[dict[str, str]] = [
    {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "config_hash": "4a8a0b3726cc906ab3534994605e77f5",
        "baseline_name": "BTCUSDT_1h_baseline.json",
        "la0_h5_glob": "BTCUSDT_1h_*_a0_tail2000.h5",
    },
    {
        "symbol": "ETHUSDT",
        "timeframe": "12h",
        "config_hash": "e53e22906c35363757f4cd49d27f973e",
        "baseline_name": "ETHUSDT_12h_baseline.json",
        "la0_h5_glob": "ETHUSDT_12h_*_a0_tail2000.h5",
    },
]

# fallback 短樣本：len>=100 過 ingestion，但 train=floor(0.8*n)<min_test_rows=131
# → insufficient_data full-sample fallback（n=100 → train=80）
FALLBACK_TAIL_BARS = 100

_SIDEFX_TMP: Optional[Path] = None


# ---------------------------------------------------------------------------
# Hash / JSON helpers（LA-0 契約）
# ---------------------------------------------------------------------------
def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_float_array(values: Any) -> str:
    """穩定 hash float 陣列（NaN→sentinel 後 tobytes）。"""
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    out = arr.copy()
    nan_mask = ~np.isfinite(out)
    out[nan_mask] = -9.87654321e30
    payload = out.tobytes(order="C") + f"|nan_count={int(nan_mask.sum())}".encode()
    return _sha256_bytes(payload)


def _hash_bool_array(values: Any) -> str:
    arr = np.asarray(values, dtype=np.bool_).reshape(-1)
    return _sha256_bytes(arr.tobytes(order="C") + f"|n={arr.size}".encode())


def _hash_string_set(items: list[str]) -> str:
    return _sha256_bytes("\n".join(sorted(str(x) for x in items)).encode("utf-8"))


def _hash_string_array(values: Any) -> str:
    arr = np.asarray(values, dtype=object).reshape(-1)
    joined = "\n".join(str(x) for x in arr.tolist())
    return _sha256_bytes(joined.encode("utf-8") + f"|n={arr.size}".encode())


def _json_safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(f):
        return None
    return float(f)


def _ts_str(ts: Any) -> str:
    if hasattr(ts, "isoformat"):
        return str(ts.isoformat())
    return str(ts)


# ---------------------------------------------------------------------------
# Canonical mutation helpers（SPEC §G）
# ---------------------------------------------------------------------------
def m_trunc_n_keep(n: int) -> int:
    """M-trunc：截尾保留前 75%。"""
    return int(M_TRUNC_RATIO * int(n))


def early_window_end(n_keep: int) -> int:
    """early window = [0, int(2/3 * n_keep))。"""
    return int(EARLY_WINDOW_RATIO * int(n_keep))


def mid_segment_trunc_point(prev_end: int, refit_interval: int = REFIT_INTERVAL_CONST) -> int:
    """mid-segment trunc 點落 refit 段中：prev_end + REFIT_INTERVAL//2。"""
    return int(prev_end) + int(refit_interval) // 2


# ---------------------------------------------------------------------------
# Side-effect isolation
# ---------------------------------------------------------------------------
def _ensure_sidefx_tmp() -> Path:
    global _SIDEFX_TMP
    if _SIDEFX_TMP is None:
        _SIDEFX_TMP = Path(tempfile.mkdtemp(prefix="la1_b0_sidefx_"))
        (_SIDEFX_TMP / "reports").mkdir(parents=True, exist_ok=True)
        (_SIDEFX_TMP / "features").mkdir(parents=True, exist_ok=True)

        def _cleanup() -> None:
            if _SIDEFX_TMP is not None and _SIDEFX_TMP.exists():
                shutil.rmtree(_SIDEFX_TMP, ignore_errors=True)

        atexit.register(_cleanup)
    return _SIDEFX_TMP


def _isolate_orchestrator_persist(orchestrator: Any) -> Path:
    """將 reporter 持久化導向 tmp；不寫 data_cache/reports/* 或 data_cache/features/*。"""
    tmp = _ensure_sidefx_tmp()
    reporter = orchestrator._reporter
    orig_save_report = reporter.save_report
    orig_save_filter_log = reporter.save_filter_log
    orig_save_filtered = reporter.save_filtered_features

    def _save_report(report: dict, output_dir: str, case_id: str) -> dict[str, str]:
        return orig_save_report(report, str(tmp / "reports"), case_id)

    def _save_filter_log(filter_log: dict, output_dir: str, case_id: str) -> str:
        return orig_save_filter_log(filter_log, str(tmp / "reports"), case_id)

    def _save_filtered_features(
        features_df: pd.DataFrame,
        selected_features: list,
        output_path: str,
        **kwargs: Any,
    ) -> str:
        name = Path(output_path).name
        target = str(tmp / "features" / name)
        return orig_save_filtered(features_df, selected_features, target, **kwargs)

    reporter.save_report = _save_report  # type: ignore[method-assign]
    reporter.save_filter_log = _save_filter_log  # type: ignore[method-assign]
    reporter.save_filtered_features = _save_filtered_features  # type: ignore[method-assign]
    return tmp


# ---------------------------------------------------------------------------
# Kline receipt / features I/O
# ---------------------------------------------------------------------------
def _kline_group_dataset_sha16(symbol: str, timeframe: str) -> tuple[int, str]:
    """回傳 (rows, sha256 前 16 hex) — 對 structured dataset 全欄位 bytes。"""
    group_key = KLINE_H5_GROUP_TEMPLATE.format(symbol=symbol, timeframe=timeframe)
    # h5py key 不含 leading slash 時用相對
    key = group_key.lstrip("/")
    with h5py.File(KLINE_H5_PATH, "r") as handle:
        if key not in handle:
            raise RuntimeError(f"kline group missing: {group_key} in {KLINE_H5_PATH}")
        data = handle[key][()]
    rows = int(data.shape[0]) if hasattr(data, "shape") else 0
    sha16 = hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest()[:16]
    return rows, sha16


def verify_kline_receipts() -> None:
    """§0.1 / --check assert ①：兩 input sha 重驗。"""
    if not KLINE_H5_PATH.is_file():
        raise SystemExit(f"kline cache missing (read-only required): {KLINE_H5_PATH}")
    for (symbol, timeframe), expected in EXPECTED_KLINE.items():
        rows, sha16 = _kline_group_dataset_sha16(symbol, timeframe)
        if rows != int(expected["rows"]):
            raise SystemExit(
                f"kline rows mismatch {symbol}/{timeframe}: "
                f"got {rows} expected {expected['rows']}"
            )
        if sha16 != expected["sha16"]:
            raise SystemExit(
                f"kline sha16 mismatch {symbol}/{timeframe}: "
                f"got {sha16} expected {expected['sha16']}"
            )
        print(
            f"[gen_baseline] kline OK {symbol}/{timeframe} "
            f"rows={rows} sha16={sha16}"
        )


def _write_features_h5(
    path: Path,
    symbol: str,
    timeframe: str,
    features_df: pd.DataFrame,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    group_key = f"{symbol}/{timeframe}"
    index_values = features_df.index
    if isinstance(index_values, pd.DatetimeIndex):
        timestamps = index_values.view("int64") // 10**9
    else:
        timestamps = np.arange(len(features_df), dtype=np.int64)

    with h5py.File(path, "w") as file:
        group = file.create_group(group_key)
        group.create_dataset(
            "features",
            data=features_df.to_numpy(dtype=np.float32),
            compression="gzip",
        )
        group.create_dataset("timestamps", data=np.asarray(timestamps, dtype=np.int64))
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(
            "feature_names",
            data=np.array(list(features_df.columns), dtype=object),
            dtype=str_dtype,
        )


def _read_features_h5(path: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    group_key = f"{symbol}/{timeframe}"
    with h5py.File(path, "r") as file:
        group = file[group_key]
        feats = group["features"][()]
        names = [
            n.decode("utf-8") if isinstance(n, (bytes, bytearray)) else str(n)
            for n in group["feature_names"][()]
        ]
        timestamps = group["timestamps"][()]
    index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None)
    return pd.DataFrame(feats, columns=names, index=index)


def _build_meta(
    symbol: str,
    timeframe: str,
    config_hash: str,
    feature_names: list[str],
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
    }
    for name in feature_names:
        meta[name] = {
            "name": name,
            "category": "unknown",
            "layer": 1,
        }
    if extra:
        meta["baseline_subset"] = extra
    return meta


def _resolve_la0_feature_inputs(run: dict[str, str]) -> tuple[Path, Path]:
    """解析 LA-0 已物化真實 features（唯讀來源）→ 複製到 la1/inputs。"""
    matches = sorted(LA0_INPUTS_DIR.glob(run["la0_h5_glob"]))
    if not matches:
        raise RuntimeError(
            f"LA-0 feature input missing for {run['symbol']}/{run['timeframe']}: "
            f"{LA0_INPUTS_DIR}/{run['la0_h5_glob']}"
        )
    src_h5 = matches[0]
    src_meta = Path(str(src_h5).replace(".h5", "_meta.json"))
    if not src_meta.is_file():
        raise RuntimeError(f"LA-0 meta missing: {src_meta}")

    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    dst_h5 = INPUTS_DIR / src_h5.name
    dst_meta = INPUTS_DIR / src_meta.name
    if not dst_h5.exists() or dst_h5.stat().st_size != src_h5.stat().st_size:
        shutil.copy2(src_h5, dst_h5)
    if not dst_meta.exists() or dst_meta.stat().st_mtime < src_meta.stat().st_mtime:
        shutil.copy2(src_meta, dst_meta)
    return dst_h5, dst_meta


def _materialize_short_features(
    full_h5: Path,
    symbol: str,
    timeframe: str,
    config_hash: str,
    n_bars: int = FALLBACK_TAIL_BARS,
) -> tuple[Path, Path]:
    """短樣本 features（觸發 insufficient_data fallback）。"""
    features_df = _read_features_h5(full_h5, symbol, timeframe)
    ordered = features_df.sort_index()
    # 取尾段：label lag 尾端 NaN 契約與 full 序列一致；n 仍 < 可過 min_test_rows
    short = ordered.iloc[-n_bars:].copy()
    stem = f"{symbol}_{timeframe}_{config_hash}_fallback_tail{n_bars}"
    h5_path = INPUTS_DIR / f"{stem}.h5"
    meta_path = INPUTS_DIR / f"{stem}_meta.json"
    _write_features_h5(h5_path, symbol, timeframe, short)
    meta = _build_meta(
        symbol,
        timeframe,
        config_hash,
        list(short.columns),
        extra={
            "purpose": "fallback_insufficient_data",
            "n_bars": int(len(short)),
            "cut_method": "timestamp_tail_sort_index",
            "source_h5": full_h5.name,
        },
    )
    meta_path.write_bytes(_canonical_json_bytes(meta))
    return h5_path, meta_path


# ---------------------------------------------------------------------------
# Regime mask / early-flip（legacy 全期 nanpercentile）
# ---------------------------------------------------------------------------
def _legacy_regime_masks(close: pd.Series) -> dict[str, pd.Series]:
    """與 ic_engine._compute_regime_groups_rule 一致的 legacy 全期門檻。"""
    ema_55 = close.ewm(span=55, adjust=False).mean()
    vol = close.pct_change(fill_method=None).rolling(55).std()
    vol_values = vol.dropna()
    if vol_values.empty:
        empty = pd.Series(False, index=close.index)
        return {
            "bull": empty,
            "bear": empty,
            "high_vol": empty,
            "low_vol": empty,
        }
    high_thresh = float(np.nanpercentile(vol_values, 80))
    low_thresh = float(np.nanpercentile(vol_values, 20))
    return {
        "bull": (close > ema_55).fillna(False),
        "bear": (close < ema_55).fillna(False),
        "high_vol": (vol >= high_thresh).fillna(False),
        "low_vol": (vol <= low_thresh).fillna(False),
    }


def _build_early_flip_manifest(close: pd.Series) -> dict[str, Any]:
    """分層 manifest：M-trunc 後 early window 可測翻轉集合（high/low 兩側）。"""
    n = int(len(close))
    n_keep = m_trunc_n_keep(n)
    early_end = early_window_end(n_keep)
    full_masks = _legacy_regime_masks(close)
    trunc_masks = _legacy_regime_masks(close.iloc[:n_keep])

    high_flip: list[int] = []
    low_flip: list[int] = []
    for i in range(early_end):
        if bool(full_masks["high_vol"].iloc[i]) != bool(trunc_masks["high_vol"].iloc[i]):
            high_flip.append(i)
        if bool(full_masks["low_vol"].iloc[i]) != bool(trunc_masks["low_vol"].iloc[i]):
            low_flip.append(i)

    # long_short early bin flip probe（全域 qcut vs trunc 全域 qcut）
    # 使用 close 本身作 feature proxy（真實序列，非合成隨機）
    feature = close.astype(float)
    label = close.pct_change(-1)
    bin_flip = _early_bin_flip_indices(feature, label, n_keep, early_end)

    return {
        "mutation": {
            "m_trunc_ratio": M_TRUNC_RATIO,
            "n": n,
            "n_keep": n_keep,
            "early_window": [0, early_end],
            "early_window_ratio": EARLY_WINDOW_RATIO,
            "refit_interval_const": REFIT_INTERVAL_CONST,
            "mid_segment_trunc_example": mid_segment_trunc_point(100, REFIT_INTERVAL_CONST),
        },
        "regime_rule": {
            "high_vol_flip_indices": high_flip,
            "low_vol_flip_indices": low_flip,
            "n_high_vol_flip": len(high_flip),
            "n_low_vol_flip": len(low_flip),
        },
        "long_short": {
            "bin_flip_indices": bin_flip,
            "n_bin_flip": len(bin_flip),
        },
    }


def _early_bin_flip_indices(
    feature: pd.Series,
    label: pd.Series,
    n_keep: int,
    early_end: int,
    q: int = 5,
) -> list[int]:
    """legacy 全域 qcut：full vs M-trunc 在 early window 的 bin 翻轉 index。"""

    def _bins(feat: pd.Series, lab: pd.Series) -> pd.Series:
        data = pd.concat([feat.rename("f"), lab.rename("l")], axis=1).dropna()
        if len(data) < q:
            return pd.Series(dtype=float)
        try:
            return pd.qcut(data["f"], q=q, labels=False, duplicates="drop")
        except ValueError:
            return pd.Series(dtype=float)

    full_bins = _bins(feature, label)
    trunc_bins = _bins(feature.iloc[:n_keep], label.iloc[:n_keep])
    if full_bins.empty or trunc_bins.empty:
        return []
    # align on shared index positions within early window of original feature index
    flips: list[int] = []
    feat_index = list(feature.index)
    for i in range(min(early_end, len(feat_index))):
        ts = feat_index[i]
        if ts not in full_bins.index or ts not in trunc_bins.index:
            continue
        a = full_bins.loc[ts]
        b = trunc_bins.loc[ts]
        if pd.isna(a) and pd.isna(b):
            continue
        if pd.isna(a) or pd.isna(b) or int(a) != int(b):
            flips.append(i)
    return flips


def _mask_payload(masks: dict[str, pd.Series]) -> dict[str, Any]:
    names = sorted(masks.keys())
    out: dict[str, Any] = {
        "name_set_sha256": _hash_string_set(names),
        "regimes": {},
    }
    for name in names:
        arr = masks[name].astype(bool).to_numpy()
        out["regimes"][name] = {
            "membership_sha256": _hash_bool_array(arr),
            "true_count": int(arr.sum()),
            "len": int(arr.size),
            "true_rate": float(arr.mean()) if arr.size else 0.0,
        }
    return out


# ---------------------------------------------------------------------------
# Analyze runners
# ---------------------------------------------------------------------------
def _base_config_override(regime_method: str) -> dict[str, Any]:
    return {
        "report": {
            "include_regime_analysis": True,
            "include_decay_analysis": False,
            "include_turnover_analysis": False,
            "include_quantile_curves": False,
            "include_correlation_heatmap": False,
            "include_layer_analysis": False,
            "ai_summary": False,
        },
        "turnover": {"enabled": False},
        "ic_calculation": {
            "grouped_analysis": {
                "by_regime": True,
                "by_year": False,
                "by_quarter": False,
                "by_category": False,
                "by_data_source": False,
                "by_layer": False,
                "by_volatility": False,
                "regime_method": regime_method,
            }
        },
        "long_short_analysis": {
            "enabled": True,
            "num_quantiles": 5,
        },
    }


# ---------------------------------------------------------------------------
# B4 control configs / artifacts（regime OFF · LS OFF · non-trigger fallback）
# ---------------------------------------------------------------------------
def control_regime_off_config() -> dict[str, Any]:
    """control-1：regime OFF；LS 維持 ON（獨立變因）。"""
    return {
        "report": {
            "include_regime_analysis": False,
            "include_decay_analysis": False,
            "include_turnover_analysis": False,
            "include_quantile_curves": False,
            "include_correlation_heatmap": False,
            "include_layer_analysis": False,
            "ai_summary": False,
        },
        "turnover": {"enabled": False},
        "ic_calculation": {
            "grouped_analysis": {
                "by_regime": False,
                "by_year": False,
                "by_quarter": False,
                "by_category": False,
                "by_data_source": False,
                "by_layer": False,
                "by_volatility": False,
            }
        },
        "long_short_analysis": {
            "enabled": True,
            "num_quantiles": 5,
        },
    }


def control_ls_off_config() -> dict[str, Any]:
    """control-2：LS OFF；regime rule 維持 ON（獨立變因）。"""
    return {
        "report": {
            "include_regime_analysis": True,
            "include_decay_analysis": False,
            "include_turnover_analysis": False,
            "include_quantile_curves": False,
            "include_correlation_heatmap": False,
            "include_layer_analysis": False,
            "ai_summary": False,
        },
        "turnover": {"enabled": False},
        "ic_calculation": {
            "grouped_analysis": {
                "by_regime": True,
                "by_year": False,
                "by_quarter": False,
                "by_category": False,
                "by_data_source": False,
                "by_layer": False,
                "by_volatility": False,
                "regime_method": "rule",
            }
        },
        "long_short_analysis": {
            "enabled": False,
            "num_quantiles": 5,
        },
    }


def control_non_trigger_fallback_config() -> dict[str, Any]:
    """control-3：非觸發 fallback（正常全量輸入 + 預設 min_test_rows）。"""
    return _base_config_override("rule")


def control_config_for_kind(kind: str) -> dict[str, Any]:
    if kind == "regime_off":
        return control_regime_off_config()
    if kind == "ls_off":
        return control_ls_off_config()
    if kind == "non_trigger_fallback":
        return control_non_trigger_fallback_config()
    raise ValueError(f"unknown control kind: {kind!r}")


def control_artifact_name(symbol: str, timeframe: str, kind: str) -> str:
    """``{SYMBOL}_{tf}_control_{kind}_full.json``（SYNTHESIS 全樹 artifact）。"""
    if kind not in CONTROL_KINDS:
        raise ValueError(f"unknown control kind: {kind!r}")
    return f"{symbol}_{timeframe}_control_{kind}_full.json"


def control_volatile_rules_path() -> Path:
    return OUTPUT_DIR / CONTROL_VOLATILE_RULES_NAME


def control_volatile_receipt_path() -> Path:
    return OUTPUT_DIR / CONTROL_VOLATILE_RECEIPT_NAME


def _control_mask_sides(masks: dict[str, pd.Series]) -> dict[str, Any]:
    """bull/bear 四欄摘要（control 側；high/low 為修改路徑不入）。"""
    payload = _mask_payload(masks)
    regimes = payload.get("regimes") or {}
    out: dict[str, Any] = {}
    for side in ("bull", "bear"):
        if side not in regimes:
            raise RuntimeError(f"control mask missing regime {side!r}")
        body = regimes[side]
        out[side] = {
            "membership_sha256": body["membership_sha256"],
            "true_count": body["true_count"],
            "len": body["len"],
            "true_rate": body["true_rate"],
        }
    return out


def _fallback_triggered_flag(report: dict[str, Any]) -> bool:
    """從 report 推不足資料 fallback 是否觸發（ok_oos → 強制 False）。"""
    if report.get("analysis_status") == "ok_oos":
        return False
    meta = report.get("metadata") or {}
    split = meta.get("ic_train_test_split") or {}
    if not isinstance(split, dict):
        return False
    return bool(
        split.get("reason") == "insufficient_data"
        or split.get("fallback") is True
        or "insufficient" in str(split.get("reason", "")).lower()
    )


def _control_config_fingerprint(kind: str) -> dict[str, Any]:
    """凍結 control 開關（與 config_override 對齊的可讀摘要）。"""
    if kind == "regime_off":
        return {
            "include_regime_analysis": False,
            "by_regime": False,
            "long_short_enabled": True,
            "regime_method": None,
        }
    if kind == "ls_off":
        return {
            "include_regime_analysis": True,
            "by_regime": True,
            "long_short_enabled": False,
            "regime_method": "rule",
        }
    return {
        "include_regime_analysis": True,
        "by_regime": True,
        "long_short_enabled": True,
        "regime_method": "rule",
        "min_test_rows_override": None,
    }


# ---------------------------------------------------------------------------
# RFC6901 + volatile scrub（SYNTHESIS B4-CODEX-1）
# ---------------------------------------------------------------------------
def _rfc6901_decode_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _rfc6901_encode_token(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _assert_exact_rfc6901_pointer(pointer: str) -> None:
    """禁 glob / key-name；只准 exact RFC6901。"""
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError(
            f"pointer must be exact RFC6901 starting with /: {pointer!r}"
        )
    if "*" in pointer or "?" in pointer:
        raise ValueError(f"glob pointer forbidden: {pointer!r}")
    if "//" in pointer:
        raise ValueError(f"empty path segment forbidden: {pointer!r}")
    if pointer != "/" and pointer.endswith("/"):
        raise ValueError(f"trailing slash forbidden: {pointer!r}")


def rfc6901_get(doc: Any, pointer: str) -> Any:
    """依 exact RFC6901 pointer 取值；不存在 → KeyError。"""
    _assert_exact_rfc6901_pointer(pointer)
    if pointer == "/":
        raise KeyError("root-only pointer '/' not supported for leaf scrub")
    cur: Any = doc
    for raw in pointer[1:].split("/"):
        token = _rfc6901_decode_token(raw)
        if isinstance(cur, list):
            try:
                idx = int(token)
            except ValueError as exc:
                raise KeyError(pointer) from exc
            cur = cur[idx]
        elif isinstance(cur, dict):
            if token not in cur:
                raise KeyError(pointer)
            cur = cur[token]
        else:
            raise KeyError(pointer)
    return cur


def rfc6901_set(doc: Any, pointer: str, value: Any) -> None:
    """就地設定 exact RFC6901 leaf。"""
    _assert_exact_rfc6901_pointer(pointer)
    parts = [_rfc6901_decode_token(p) for p in pointer[1:].split("/")]
    cur: Any = doc
    for token in parts[:-1]:
        if isinstance(cur, list):
            cur = cur[int(token)]
        else:
            cur = cur[token]
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    elif isinstance(cur, dict):
        if last not in cur:
            raise KeyError(pointer)
        cur[last] = value
    else:
        raise KeyError(pointer)


def rfc6901_exists(doc: Any, pointer: str) -> bool:
    try:
        rfc6901_get(doc, pointer)
        return True
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def _python_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, (np.floating,)):
        return "float"
    if isinstance(value, (np.integer,)):
        return "int"
    return type(value).__name__


def _coerce_json_scalar(value: Any) -> Any:
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def validate_volatile_value(value: Any, rule: dict[str, Any]) -> None:
    """驗原值型別 + validator 格式；失敗 raise ValueError。"""
    expected = str(rule.get("expected_type") or "")
    got = _python_type_name(value)
    if expected and got != expected:
        raise ValueError(
            f"volatile type mismatch at {rule.get('pointer')}: "
            f"expected {expected} got {got}"
        )
    validator = str(rule.get("validator") or "")
    if validator not in _VALIDATOR_REGEX:
        raise ValueError(
            f"unknown validator {validator!r} at {rule.get('pointer')}"
        )
    if not isinstance(value, str) or not _VALIDATOR_REGEX[validator].search(value):
        raise ValueError(
            f"volatile format fail at {rule.get('pointer')}: "
            f"validator={validator} value={value!r}"
        )


def load_volatile_rules(path: Optional[Path] = None) -> list[dict[str, Any]]:
    """載入 denylist rules；schema=[{pointer,expected_type,validator,reason,producer_ref}]。"""
    p = path or control_volatile_rules_path()
    if not p.is_file():
        raise FileNotFoundError(f"volatile rules missing: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("control_volatile_rules.json must be a list")
    rules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"rules[{i}] must be object")
        for req in (
            "pointer",
            "expected_type",
            "validator",
            "reason",
            "producer_ref",
        ):
            if req not in item:
                raise ValueError(f"rules[{i}] missing {req}")
        pointer = str(item["pointer"])
        _assert_exact_rfc6901_pointer(pointer)
        if pointer in seen:
            raise ValueError(f"duplicate pointer in rules: {pointer}")
        seen.add(pointer)
        rules.append(
            {
                "pointer": pointer,
                "expected_type": str(item["expected_type"]),
                "validator": str(item["validator"]),
                "reason": str(item["reason"]),
                "producer_ref": str(item["producer_ref"]),
            }
        )
    rules.sort(key=lambda r: r["pointer"])
    return rules


def rules_sha256(rules: list[dict[str, Any]]) -> str:
    return _sha256_bytes(_canonical_json_bytes(rules))


def load_volatile_receipt(path: Optional[Path] = None) -> dict[str, Any]:
    p = path or control_volatile_receipt_path()
    if not p.is_file():
        raise FileNotFoundError(f"volatile receipt missing: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("receipt must be object")
    return data


def receipt_sha256(receipt: dict[str, Any]) -> str:
    body = {k: v for k, v in receipt.items() if k != "content_sha256"}
    return _sha256_bytes(_canonical_json_bytes(body))


def _apply_nonfinite_markers(obj: Any) -> Any:
    """NaN/±inf → typed marker；其餘遞迴。"""
    obj = _coerce_json_scalar(obj)
    if isinstance(obj, float):
        if math.isnan(obj):
            return {NONFINITE_MARKER_KEY: "NaN"}
        if math.isinf(obj):
            return {NONFINITE_MARKER_KEY: "+Inf" if obj > 0 else "-Inf"}
        return obj
    if isinstance(obj, dict):
        if VOLATILE_SENTINEL_KEY in obj or NONFINITE_MARKER_KEY in obj:
            return dict(obj)
        return {str(k): _apply_nonfinite_markers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_apply_nonfinite_markers(v) for v in obj]
    if isinstance(obj, tuple):
        return [_apply_nonfinite_markers(v) for v in obj]
    return obj


def canonical_full_report(
    report: dict[str, Any],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """deep-copy 全樹 → 逐 pointer 驗型別/格式後換 sentinel → NaN/±inf marker。

    sentinel：``{"__volatile__": <pointer>, "original_type": "<type>"}``
    不刪鍵；驗不過 / unused pointer → raise。
    """
    if not isinstance(report, dict):
        raise TypeError("report must be dict")
    tree: Any = copy.deepcopy(report)
    used: set[str] = set()
    for rule in rules:
        pointer = rule["pointer"]
        _assert_exact_rfc6901_pointer(pointer)
        if not rfc6901_exists(tree, pointer):
            raise ValueError(
                f"unused volatile pointer (missing in report): {pointer}"
            )
        original = rfc6901_get(tree, pointer)
        validate_volatile_value(original, rule)
        orig_type = _python_type_name(original)
        rfc6901_set(
            tree,
            pointer,
            {
                VOLATILE_SENTINEL_KEY: pointer,
                "original_type": orig_type,
            },
        )
        used.add(pointer)
    rule_ptrs = {r["pointer"] for r in rules}
    if used != rule_ptrs:
        raise ValueError(
            f"rules/used pointer set mismatch used={used} rules={rule_ptrs}"
        )
    marked = _apply_nonfinite_markers(tree)
    if not isinstance(marked, dict):
        raise TypeError("canonical report must remain dict")
    return marked


def _values_equal_discovery(
    a: Any, b: Any, *, atol: float = CONTROL_ATOL
) -> bool:
    a = _coerce_json_scalar(a)
    b = _coerce_json_scalar(b)
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        if math.isinf(a) or math.isinf(b):
            return a == b
        return abs(a - b) <= atol
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, bool) or isinstance(b, bool):
            return a == b
        return abs(float(a) - float(b)) <= atol
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(
            _values_equal_discovery(a[k], b[k], atol=atol) for k in a
        )
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(
            _values_equal_discovery(x, y, atol=atol) for x, y in zip(a, b)
        )
    return a == b


def _discovery_leaf_diffs(
    a: Any,
    b: Any,
    *,
    pointer: str = "",
    atol: float = CONTROL_ATOL,
) -> list[tuple[str, Any, Any]]:
    a = _coerce_json_scalar(a)
    b = _coerce_json_scalar(b)
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = set(a.keys()), set(b.keys())
        if ka != kb:
            return [(pointer or "/", a, b)]
        out: list[tuple[str, Any, Any]] = []
        for k in sorted(ka, key=str):
            child = f"{pointer}/{_rfc6901_encode_token(str(k))}"
            out.extend(
                _discovery_leaf_diffs(a[k], b[k], pointer=child, atol=atol)
            )
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [(pointer or "/", a, b)]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            child = f"{pointer}/{i}"
            out.extend(_discovery_leaf_diffs(x, y, pointer=child, atol=atol))
        return out
    if _values_equal_discovery(a, b, atol=atol):
        return []
    return [(pointer or "/", a, b)]


def _is_admissible_volatile_candidate(
    pointer: str, left: Any, right: Any
) -> bool:
    meta = _KNOWN_VOLATILE_PRODUCERS.get(pointer)
    if meta is None:
        return False
    rule = {
        "pointer": pointer,
        "expected_type": meta["expected_type"],
        "validator": meta["validator"],
    }
    try:
        validate_volatile_value(left, rule)
        validate_volatile_value(right, rule)
    except ValueError:
        return False
    return left != right


def _reset_sidefx_tmp() -> None:
    """強制下一輪 _isolate 使用全新 tmp root。"""
    global _SIDEFX_TMP
    if _SIDEFX_TMP is not None and _SIDEFX_TMP.exists():
        shutil.rmtree(_SIDEFX_TMP, ignore_errors=True)
    _SIDEFX_TMP = None


def _run_analyze_isolated(
    h5_path: Path,
    meta_path: Path,
    config_override: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """fresh sidefx tmp 後跑 analyze，回傳 raw report。"""
    _reset_sidefx_tmp()
    _orch, report = _run_analyze(h5_path, meta_path, config_override)
    if not isinstance(report, dict):
        raise TypeError("analyze must return dict report")
    return report


def discover_volatile_pointers(
    *,
    runs: Optional[list[dict[str, str]]] = None,
    kinds: Optional[tuple[str, ...]] = None,
) -> dict[str, Any]:
    """同 config 兩次 isolated 跑 → leaf diff 候選；只准入 producer-clear volatile。"""
    use_runs = runs if runs is not None else RUNS
    use_kinds = kinds if kinds is not None else CONTROL_KINDS
    matrix: list[dict[str, Any]] = []
    union: set[str] = set()
    for run in use_runs:
        h5_path, meta_path = _resolve_la0_feature_inputs(run)
        for kind in use_kinds:
            cfg = control_config_for_kind(kind)
            t0 = time.perf_counter()
            r1 = _run_analyze_isolated(h5_path, meta_path, cfg)
            r2 = _run_analyze_isolated(h5_path, meta_path, cfg)
            diffs = _discovery_leaf_diffs(r1, r2)
            observed: list[str] = []
            bad: list[str] = []
            for pointer, left, right in diffs:
                if pointer in ("", "/"):
                    bad.append(f"structural root diff kind={kind}")
                    continue
                if _is_admissible_volatile_candidate(pointer, left, right):
                    observed.append(pointer)
                    continue
                bad.append(
                    f"{pointer}: nondeterminism or non-admissible "
                    f"left_type={_python_type_name(left)} "
                    f"right_type={_python_type_name(right)}"
                )
            if bad:
                raise RuntimeError(
                    "discover_volatile_pointers FAIL nondeterminism: "
                    + "; ".join(bad[:8])
                    + (f" (+{len(bad)-8} more)" if len(bad) > 8 else "")
                )
            observed_u = sorted(set(observed))
            union.update(observed_u)
            matrix.append(
                {
                    "symbol": run["symbol"],
                    "timeframe": run["timeframe"],
                    "control_kind": kind,
                    "volatile_paths": observed_u,
                    "run_wall_s": round(time.perf_counter() - t0, 3),
                }
            )
            print(
                f"[gen_baseline] discover {run['symbol']}/{run['timeframe']} "
                f"{kind}: paths={observed_u}"
            )
    observed_sorted = sorted(union)
    print(f"VOLATILE_CANDIDATES={observed_sorted}")
    return {
        "schema_version": "la1_control_volatile_receipt_v1",
        "observed_pointers": observed_sorted,
        "discover_matrix": matrix,
        "receipt_note": (
            "paths = union of exact RFC6901 leaf diffs across CONTROL_KINDS×RUNS "
            "with isolated tmp; only producer-clear timestamp/tmp-path admitted; "
            "numeric/set/order diffs fail closed"
        ),
    }


def build_volatile_rules_from_observed(
    observed_pointers: list[str],
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for pointer in sorted(set(observed_pointers)):
        meta = _KNOWN_VOLATILE_PRODUCERS.get(pointer)
        if meta is None:
            raise RuntimeError(
                f"observed pointer not in known producers "
                f"(refuse denylist): {pointer}"
            )
        rules.append(
            {
                "pointer": pointer,
                "expected_type": meta["expected_type"],
                "validator": meta["validator"],
                "reason": meta["reason"],
                "producer_ref": meta["producer_ref"],
            }
        )
    return rules


def assert_receipt_matches_rules(
    receipt: dict[str, Any],
    rules: list[dict[str, Any]],
) -> None:
    observed = receipt.get("observed_pointers")
    if not isinstance(observed, list):
        raise ValueError("receipt.observed_pointers must be list")
    obs_set = set(str(x) for x in observed)
    rule_set = {r["pointer"] for r in rules}
    if obs_set != rule_set:
        raise ValueError(
            f"receipt observed ≠ rules: "
            f"only_obs={sorted(obs_set - rule_set)} "
            f"only_rules={sorted(rule_set - obs_set)}"
        )
    rsha = rules_sha256(rules)
    if receipt.get("rules_sha256") and receipt.get("rules_sha256") != rsha:
        raise ValueError(
            f"receipt.rules_sha256 mismatch: "
            f"got {receipt.get('rules_sha256')} expected {rsha}"
        )
    osha = _sha256_bytes(
        _canonical_json_bytes(sorted(str(x) for x in observed))
    )
    if receipt.get("observed_pointers_sha256") and receipt.get(
        "observed_pointers_sha256"
    ) != osha:
        raise ValueError(
            f"receipt.observed_pointers_sha256 mismatch: "
            f"got {receipt.get('observed_pointers_sha256')} expected {osha}"
        )


def write_volatile_rules_and_receipt(
    *,
    discover: bool = True,
) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if discover:
        disc = discover_volatile_pointers()
        observed = list(disc["observed_pointers"])
        matrix = disc["discover_matrix"]
        note = disc["receipt_note"]
    else:
        rules_existing = load_volatile_rules()
        observed = [r["pointer"] for r in rules_existing]
        matrix = []
        note = "reused existing rules without rediscover"
    rules = build_volatile_rules_from_observed(observed)
    rsha = rules_sha256(rules)
    osha = _sha256_bytes(_canonical_json_bytes(sorted(observed)))
    rules_path = control_volatile_rules_path()
    rules_path.write_bytes(_canonical_json_bytes(rules))
    receipt: dict[str, Any] = {
        "schema_version": "la1_control_volatile_receipt_v1",
        "observed_pointers": sorted(observed),
        "observed_pointers_sha256": osha,
        "rules_sha256": rsha,
        "discover_matrix": matrix,
        "receipt_note": note,
    }
    receipt["content_sha256"] = receipt_sha256(receipt)
    receipt_path = control_volatile_receipt_path()
    receipt_path.write_bytes(_canonical_json_bytes(receipt))
    print(
        f"[gen_baseline] wrote {rules_path.name} sha={rsha[:16]} "
        f"n_rules={len(rules)}"
    )
    print(
        f"[gen_baseline] wrote {receipt_path.name} "
        f"content_sha={receipt['content_sha256'][:16]}"
    )
    assert_receipt_matches_rules(receipt, rules)
    return rules_path, receipt_path


def assemble_control_artifact(
    *,
    kind: str,
    symbol: str,
    timeframe: str,
    config_hash: str,
    h5_path: Path,
    meta_path: Path,
    report: dict[str, Any],
    masks: dict[str, pd.Series],
    rules: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """組裝 control **全樹** canonical 輸出（report=canonical_full_report；禁投影）。"""
    if kind not in CONTROL_KINDS:
        raise ValueError(f"unknown control kind: {kind!r}")
    use_rules = rules if rules is not None else load_volatile_rules()
    rows, sha16 = _kline_group_dataset_sha16(symbol, timeframe)
    full_report = canonical_full_report(report, use_rules)
    if "summary_table" not in full_report:
        raise RuntimeError(
            "canonical report missing summary_table (projection leak?)"
        )
    body: dict[str, Any] = {
        "schema_version": CONTROL_SCHEMA_VERSION,
        "spec_ref": "docs/IC_LA1_SPEC.md §G control deep-equal",
        "todo_ref": "docs/IC_LA1_TODO.md Task 4.1 / B4-CODEX-1 SYNTHESIS",
        "control_kind": kind,
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "input_contract": {
            "features_h5": str(h5_path.relative_to(REPO_ROOT)),
            "meta_json": str(meta_path.relative_to(REPO_ROOT)),
            "kline_cache": str(KLINE_H5_PATH.relative_to(REPO_ROOT)),
            "kline_rows": rows,
            "kline_sha16": sha16,
        },
        "control_config": _control_config_fingerprint(kind),
        "report": full_report,
        "mask_membership_control": _control_mask_sides(masks),
        "volatile_rules_sha256": rules_sha256(use_rules),
    }
    body["content_sha256"] = _sha256_bytes(
        _canonical_json_bytes(
            {k: v for k, v in body.items() if k != "content_sha256"}
        )
    )
    return body


def run_control_one(
    run: dict[str, str],
    kind: str,
    *,
    rules: Optional[list[dict[str, Any]]] = None,
    isolate: bool = True,
) -> dict[str, Any]:
    """跑單一 symbol×control_kind → 完整 control full-tree artifact。"""
    if kind not in CONTROL_KINDS:
        raise ValueError(f"unknown control kind: {kind!r}")
    symbol = run["symbol"]
    timeframe = run["timeframe"]
    config_hash = run["config_hash"]
    h5_path, meta_path = _resolve_la0_feature_inputs(run)
    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    raw = kline_reader.read_klines(symbol, timeframe)
    if raw is None or raw.empty:
        raise RuntimeError(f"empty kline for {symbol}/{timeframe}")
    close = raw["close"].astype(float)

    cfg = control_config_for_kind(kind)
    if isolate:
        report = _run_analyze_isolated(h5_path, meta_path, cfg)
    else:
        _orch, report = _run_analyze(h5_path, meta_path, cfg)
    masks = _legacy_regime_masks(close)
    return assemble_control_artifact(
        kind=kind,
        symbol=symbol,
        timeframe=timeframe,
        config_hash=config_hash,
        h5_path=h5_path,
        meta_path=meta_path,
        report=report,
        masks=masks,
        rules=rules,
    )


def generate_control_artifacts(
    *,
    rules: Optional[list[dict[str, Any]]] = None,
) -> list[Path]:
    """凍結三 control × 每 RUN 的 **full-tree** canonical 輸出。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if rules is None:
        if not control_volatile_rules_path().is_file():
            write_volatile_rules_and_receipt(discover=True)
        use_rules = load_volatile_rules()
    else:
        use_rules = rules
    written: list[Path] = []
    for run in RUNS:
        for kind in CONTROL_KINDS:
            print(
                f"[gen_baseline] control-full {kind} "
                f"{run['symbol']}/{run['timeframe']} ..."
            )
            t0 = time.perf_counter()
            artifact = run_control_one(
                run, kind, rules=use_rules, isolate=True
            )
            out_path = OUTPUT_DIR / control_artifact_name(
                run["symbol"], run["timeframe"], kind
            )
            raw = _canonical_json_bytes(artifact)
            out_path.write_bytes(raw)
            digest = _sha256_bytes(raw)
            print(
                f"[gen_baseline] wrote {out_path.relative_to(REPO_ROOT)} "
                f"sha256={digest} bytes={len(raw)} "
                f"wall={time.perf_counter()-t0:.2f}s"
            )
            written.append(out_path)
    return written


def _assert_control_artifact(data: dict[str, Any], name: str) -> None:
    """--check：control full artifact 結構 + content_sha256 + 全樹鍵 + rules sha。"""
    missing = [k for k in CONTROL_REQUIRED_KEYS if k not in data]
    if missing:
        raise SystemExit(f"{name}: missing control keys: {missing}")
    kind = data.get("control_kind")
    if kind not in CONTROL_KINDS:
        raise SystemExit(f"{name}: invalid control_kind={kind!r}")
    if data.get("schema_version") != CONTROL_SCHEMA_VERSION:
        raise SystemExit(
            f"{name}: schema_version={data.get('schema_version')!r} "
            f"expected {CONTROL_SCHEMA_VERSION!r}"
        )
    body_wo = {k: v for k, v in data.items() if k != "content_sha256"}
    recomputed = _sha256_bytes(_canonical_json_bytes(body_wo))
    if recomputed != data.get("content_sha256"):
        raise SystemExit(
            f"{name}: content_sha256 mismatch "
            f"(got {data.get('content_sha256')}, recomputed {recomputed})"
        )
    symbol = data.get("symbol")
    timeframe = data.get("timeframe")
    if (symbol, timeframe) not in EXPECTED_KLINE:
        raise SystemExit(f"{name}: unknown symbol/tf {symbol}/{timeframe}")
    expected = EXPECTED_KLINE[(str(symbol), str(timeframe))]
    ic = data.get("input_contract") or {}
    if ic.get("kline_sha16") != expected["sha16"] or int(
        ic.get("kline_rows") or 0
    ) != int(expected["rows"]):
        raise SystemExit(
            f"{name}: embedded kline receipt mismatch "
            f"sha={ic.get('kline_sha16')} rows={ic.get('kline_rows')}"
        )
    mm = data.get("mask_membership_control") or {}
    for side in ("bull", "bear"):
        if side not in mm:
            raise SystemExit(f"{name}: mask_membership_control missing {side}")
        for fld in ("membership_sha256", "true_count", "len", "true_rate"):
            if fld not in mm[side]:
                raise SystemExit(f"{name}: {side} missing {fld}")
    report = data.get("report") or {}
    if not isinstance(report, dict):
        raise SystemExit(f"{name}: report must be dict")
    if "summary_table" not in report:
        raise SystemExit(
            f"CONTROL_FULL_TREE_CHECK=FAIL reason=projection_keys "
            f"report_keys={len(report)} missing=summary_table"
        )
    projection_only = {
        "by_regime_empty",
        "by_regime_name_set",
        "kind_contract",
        "triggered_insufficient_data",
    }
    if set(report.keys()) <= projection_only | {
        "analysis_status",
        "oos_guarantees",
        "by_regime",
        "long_short",
        "fallback",
    }:
        raise SystemExit(
            f"CONTROL_FULL_TREE_CHECK=FAIL reason=projection_keys "
            f"report_keys={sorted(report.keys())}"
        )
    rules = load_volatile_rules()
    rsha = rules_sha256(rules)
    if data.get("volatile_rules_sha256") != rsha:
        raise SystemExit(
            f"{name}: volatile_rules_sha256 mismatch "
            f"got={data.get('volatile_rules_sha256')} expected={rsha}"
        )
    for rule in rules:
        pointer = rule["pointer"]
        try:
            val = rfc6901_get(report, pointer)
        except KeyError:
            raise SystemExit(
                f"{name}: scrubbed report missing pointer {pointer}"
            )
        if not isinstance(val, dict) or val.get(VOLATILE_SENTINEL_KEY) != pointer:
            raise SystemExit(
                f"{name}: expected volatile sentinel at {pointer}, got {val!r}"
            )
    if report.get("analysis_status") != "ok_oos":
        raise SystemExit(f"{name}: analysis_status must be ok_oos")
    if kind == "regime_off":
        by_regime = (report.get("grouped_ic") or {}).get("by_regime") or {}
        if by_regime:
            raise SystemExit(f"{name}: regime_off by_regime not empty")
    if kind == "ls_off":
        ls = report.get("long_short") or report.get("long_short_analysis")
        if isinstance(ls, dict):
            feats = ls.get("features") or ls.get("results") or {}
            if feats:
                raise SystemExit(
                    f"{name}: ls_off long_short features not empty"
                )
    if kind == "non_trigger_fallback":
        if report.get("oos_guarantees") is not True:
            raise SystemExit(f"{name}: non_trigger oos_guarantees must be true")
        if _fallback_triggered_flag(report):
            raise SystemExit(f"{name}: non_trigger must not trigger fallback")


def check_control_artifacts() -> None:
    """--check assert ④：rules + receipt + 六 full artifact 三者 sha。"""
    rules_path = control_volatile_rules_path()
    receipt_path = control_volatile_receipt_path()
    if not rules_path.is_file() or not receipt_path.is_file():
        print(
            "[gen_baseline] --check: volatile rules/receipt missing → discover+write"
        )
        write_volatile_rules_and_receipt(discover=True)
    rules = load_volatile_rules()
    receipt = load_volatile_receipt()
    assert_receipt_matches_rules(receipt, rules)
    body_wo = {k: v for k, v in receipt.items() if k != "content_sha256"}
    rec_recomputed = _sha256_bytes(_canonical_json_bytes(body_wo))
    if receipt.get("content_sha256") != rec_recomputed:
        raise SystemExit(
            f"receipt content_sha256 mismatch got={receipt.get('content_sha256')} "
            f"recomputed={rec_recomputed}"
        )
    rules_digest = rules_sha256(rules)
    receipt_digest = receipt.get("content_sha256")
    print(
        f"[gen_baseline] check rules_sha256={rules_digest} "
        f"receipt_sha256={receipt_digest}"
    )

    missing: list[str] = []
    for run in RUNS:
        for kind in CONTROL_KINDS:
            name = control_artifact_name(run["symbol"], run["timeframe"], kind)
            path = OUTPUT_DIR / name
            if not path.is_file():
                missing.append(name)
    if missing:
        print(
            f"[gen_baseline] --check: control full artifacts missing "
            f"({len(missing)}) → generate"
        )
        generate_control_artifacts(rules=rules)
    for run in RUNS:
        for kind in CONTROL_KINDS:
            name = control_artifact_name(run["symbol"], run["timeframe"], kind)
            path = OUTPUT_DIR / name
            if not path.is_file():
                raise SystemExit(f"control artifact still missing: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            _assert_control_artifact(data, name)
            file_sha = _sha256_file(path)
            print(
                f"[gen_baseline] check OK control {name} "
                f"content_sha256={data.get('content_sha256')} "
                f"file_sha256={file_sha}"
            )
    n_art = len(CONTROL_KINDS) * len(RUNS)
    print(
        f"CONTROL_FULL_TREE_CHECK=PASS artifacts={n_art} "
        f"denylist_sha={rules_digest[:16]}"
    )
    print(
        f"[gen_baseline] --check control OK "
        f"({len(CONTROL_KINDS)} kinds × {len(RUNS)} symbols + rules + receipt)"
    )


def _run_analyze(
    h5_path: Path,
    meta_path: Path,
    config_override: Optional[dict[str, Any]] = None,
) -> tuple[Any, dict]:
    orchestrator = create_ic_analyzer()
    _isolate_orchestrator_persist(orchestrator)
    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    report = orchestrator.analyze(
        features_path=str(h5_path.resolve()),
        labels_path="",
        meta_path=str(meta_path.resolve()),
        config_override=config_override,
        kline_reader=kline_reader,
    )
    return orchestrator, report


def _summarize_by_regime(by_regime: dict) -> dict[str, Any]:
    """per-regime grouped IC：名稱集合 sha + 每量 value/NaN mask hash。"""
    if not isinstance(by_regime, dict):
        return {"empty": True, "name_set_sha256": _hash_string_set([])}
    regime_names = sorted(str(k) for k in by_regime.keys())
    payload: dict[str, Any] = {
        "name_set_sha256": _hash_string_set(regime_names),
        "regime_names": regime_names,
        "per_regime": {},
    }
    for rname in regime_names:
        body = by_regime.get(rname) or {}
        if not isinstance(body, dict):
            payload["per_regime"][rname] = {"empty": True}
            continue
        feature_names = sorted(str(f) for f in body.keys())
        values: list[float] = []
        nan_flags: list[bool] = []
        per_feature: dict[str, Any] = {}
        for fname in feature_names:
            stats = body.get(fname) or {}
            if isinstance(stats, dict):
                ic_val = stats.get("ic_mean", stats.get("ic", stats.get("spearman")))
            else:
                ic_val = stats
            f = _json_safe_float(ic_val)
            values.append(f if f is not None else float("nan"))
            nan_flags.append(f is None)
            per_feature[fname] = {"ic": f}
        payload["per_regime"][rname] = {
            "feature_name_set_sha256": _hash_string_set(feature_names),
            "value_sha256": _hash_float_array(values),
            "nan_mask_sha256": _hash_bool_array(nan_flags),
            "n_features": len(feature_names),
            "per_feature": per_feature,
        }
    return payload


def _summarize_long_short(ls_results: dict) -> dict[str, Any]:
    feature_names = sorted(str(k) for k in ls_results.keys())
    out: dict[str, Any] = {
        "name_set_sha256": _hash_string_set(feature_names),
        "features": {},
    }
    ics: list[float] = []
    nan_flags: list[bool] = []
    for fname in feature_names:
        body = ls_results.get(fname) or {}
        if body.get("skipped"):
            out["features"][fname] = {
                "skipped": True,
                "reason": body.get("reason"),
                "error_type": body.get("error_type"),
            }
            continue
        long_a = body.get("long_analysis") or {}
        short_a = body.get("short_analysis") or {}
        rec = body.get("recommendation")
        n_q = body.get("num_quantiles_used")
        row = {
            "long_ic": _json_safe_float(long_a.get("ic")),
            "long_mean_return": _json_safe_float(long_a.get("mean_return")),
            "short_ic": _json_safe_float(short_a.get("ic")),
            "short_mean_return": _json_safe_float(short_a.get("mean_return")),
            "recommendation": rec,
            "num_quantiles_used": int(n_q) if n_q is not None else None,
        }
        out["features"][fname] = row
        for key in ("long_ic", "short_ic", "long_mean_return", "short_mean_return"):
            v = row[key]
            ics.append(v if v is not None else float("nan"))
            nan_flags.append(v is None)
    out["value_sha256"] = _hash_float_array(ics)
    out["nan_mask_sha256"] = _hash_bool_array(nan_flags)
    return out


def _to_unix_seconds_list(timestamps: Any) -> list[int]:
    """將 timestamp 欄位 / DatetimeIndex / Series 轉為 per-position unix 秒（int）。

    kline_storage 回傳 RangeIndex + `timestamp` 欄位（已是 unix 秒）；
    不可把 RangeIndex 0..n-1 誤當時間戳。
    """
    if isinstance(timestamps, pd.DatetimeIndex):
        return [int(x) for x in (timestamps.asi8 // 10**9).tolist()]
    if isinstance(timestamps, pd.Series):
        if pd.api.types.is_datetime64_any_dtype(timestamps):
            return [int(x) for x in (timestamps.astype("int64") // 10**9).tolist()]
        return [int(x) for x in timestamps.astype("int64").tolist()]
    if isinstance(timestamps, pd.Index) and not isinstance(
        timestamps, pd.RangeIndex
    ):
        if isinstance(timestamps, pd.DatetimeIndex):
            return [int(x) for x in (timestamps.asi8 // 10**9).tolist()]
        try:
            return [int(x) for x in np.asarray(timestamps, dtype=np.int64).tolist()]
        except (TypeError, ValueError):
            pass
    # ndarray / list / 純量序列
    arr = np.asarray(timestamps)
    if np.issubdtype(arr.dtype, np.datetime64):
        # datetime64[ns] → unix s
        return [int(x) for x in (arr.astype("datetime64[s]").astype(np.int64)).tolist()]
    if np.issubdtype(arr.dtype, np.number):
        vals = [int(x) for x in arr.astype(np.int64).tolist()]
        # 防護：RangeIndex 被當成 timestamps（0..n-1）— 這不是真實時間
        if len(vals) >= 2 and vals[0] == 0 and vals[1] == 1 and vals[-1] == len(vals) - 1:
            raise RuntimeError(
                "timestamps look like RangeIndex positions (0..n-1); "
                "pass kline `timestamp` column (unix seconds), not close.index"
            )
        return vals
    out: list[int] = []
    for ts in timestamps:
        if hasattr(ts, "timestamp"):
            out.append(int(ts.timestamp()))
        else:
            out.append(int(pd.Timestamp(ts).timestamp()))
    return out


def _summarize_phases(labels: list[str], timestamps: Any) -> dict[str, Any]:
    """凍結 XGBoost 路徑 per-index phase label 序列（element 級，禁 aggregate-only）。

    必含：
      - labels: list[str] 與 bar 順序對齊
      - timestamps: list[int] unix 秒，與 labels 同序同長（真實 kline timestamp）
      - labels_sha256 / name_set* / value_counts / len（完整性摘要）
    """
    arr = [str(x) for x in labels]
    ts_list = _to_unix_seconds_list(timestamps)
    if len(ts_list) != len(arr):
        raise RuntimeError(
            f"xgboost_phases label/timestamp length mismatch: "
            f"labels={len(arr)} timestamps={len(ts_list)}"
        )
    name_set = sorted(set(arr))
    return {
        "len": len(arr),
        "name_set_sha256": _hash_string_set(name_set),
        "name_set": name_set,
        "labels_sha256": _hash_string_array(arr),
        "timestamps_sha256": _hash_string_array([str(t) for t in ts_list]),
        "value_counts": {
            k: int(sum(1 for x in arr if x == k)) for k in name_set
        },
        # element payload（SPEC §G / B0.1：禁 aggregate-only）
        "labels": arr,
        "timestamps": ts_list,
    }


def _summarize_fallback(report: dict) -> dict[str, Any]:
    meta = report.get("metadata") or {}
    split = meta.get("ic_train_test_split") or {}
    return {
        "fit_mode": meta.get("fit_mode"),
        "oos_guarantees": meta.get("oos_guarantees"),
        "split_meta": {
            "reason": split.get("reason") if isinstance(split, dict) else None,
            "fallback": split.get("fallback") if isinstance(split, dict) else None,
            "applied": split.get("applied") if isinstance(split, dict) else None,
            "raw_keys": sorted(split.keys()) if isinstance(split, dict) else [],
        },
        "triggered_insufficient_data": (
            isinstance(split, dict)
            and (
                split.get("reason") == "insufficient_data"
                or "insufficient" in str(split.get("reason", "")).lower()
                or split.get("fallback") is True
                or meta.get("fit_mode") == "full_sample"
            )
        ),
        "metadata_sha256": _sha256_bytes(
            _canonical_json_bytes(
                {
                    "fit_mode": meta.get("fit_mode"),
                    "oos_guarantees": meta.get("oos_guarantees"),
                    "ic_train_test_split": split,
                }
            )
        ),
    }


def run_one(run: dict[str, str]) -> dict[str, Any]:
    symbol = run["symbol"]
    timeframe = run["timeframe"]
    config_hash = run["config_hash"]

    h5_path, meta_path = _resolve_la0_feature_inputs(run)
    print(f"[gen_baseline] {symbol}/{timeframe}: features={h5_path.name}")

    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    raw = kline_reader.read_klines(symbol, timeframe)
    if raw is None or raw.empty:
        raise RuntimeError(f"empty kline for {symbol}/{timeframe}")
    close = raw["close"].astype(float)
    volume = raw["volume"].astype(float) if "volume" in raw.columns else None
    # kline 時間在欄位 `timestamp`（unix 秒），index 常為 RangeIndex — 勿混用
    if "timestamp" not in raw.columns:
        raise RuntimeError(
            f"{symbol}/{timeframe}: kline missing `timestamp` column "
            "(required for xgboost_phases element payload)"
        )
    kline_timestamps = raw["timestamp"]

    # ---- ① regime rule ----
    t0 = time.perf_counter()
    orch_rule, report_rule = _run_analyze(
        h5_path, meta_path, _base_config_override("rule")
    )
    by_regime_rule = (report_rule.get("grouped_ic") or {}).get("by_regime") or {}
    regime_rule_payload = _summarize_by_regime(by_regime_rule)
    masks_rule = _legacy_regime_masks(close)
    regime_rule_payload["mask_membership"] = _mask_payload(masks_rule)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: regime_rule "
        f"regimes={list(by_regime_rule.keys())} wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- ② kmeans ----
    t0 = time.perf_counter()
    _orch_km, report_km = _run_analyze(
        h5_path, meta_path, _base_config_override("kmeans")
    )
    by_regime_km = (report_km.get("grouped_ic") or {}).get("by_regime") or {}
    regime_km_payload = _summarize_by_regime(by_regime_km)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: regime_kmeans "
        f"regimes={list(by_regime_km.keys())} wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- ③ XGBoost detect_phases_for_index ----
    t0 = time.perf_counter()
    detector = create_regime_detector(n_clusters=4, lookback=55)
    phase_labels = detector.detect_phases_for_index(close, volume, index=close.index)
    phases_payload = _summarize_phases(list(phase_labels), kline_timestamps)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: xgboost_phases "
        f"n={phases_payload['len']} names={phases_payload['name_set']} "
        f"wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- ④ long_short（經 analyze 後 cache + LongShortAnalyzer）----
    t0 = time.perf_counter()
    ic_cache = orch_rule._ic_cache or {}
    features_df = ic_cache.get("features_df")
    label_series = ic_cache.get("label_series")
    if features_df is None or label_series is None:
        raise RuntimeError(f"{symbol}/{timeframe}: ic_cache missing after analyze")
    ls_analyzer = LongShortAnalyzer(
        {"enabled": True, "num_quantiles": 5, "long_quantiles": [4, 5], "short_quantiles": [1, 2]}
    )
    ls_results = ls_analyzer.batch_analyze(
        features_df, label_series, top_n=len(features_df.columns)
    )
    long_short_payload = _summarize_long_short(ls_results)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: long_short "
        f"n_features={len(ls_results)} wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- ⑤ fallback：短樣本（len 剛好 ≥100 但 train/test < min_test_rows）----
    # 另用 min_test_rows 抬高作雙保險（同一 short 輸入）
    t0 = time.perf_counter()
    short_h5, short_meta = _materialize_short_features(
        h5_path, symbol, timeframe, config_hash, FALLBACK_TAIL_BARS
    )
    fb_override = _base_config_override("rule")
    # 雙保險：即使 short 切法變動，抬高 min_test_rows 必觸發 insufficient_data
    fb_override["min_test_rows"] = 10_000
    _orch_fb, report_fb = _run_analyze(short_h5, short_meta, fb_override)
    fallback_payload = _summarize_fallback(report_fb)
    fallback_payload["trigger_config"] = {
        "n_bars": FALLBACK_TAIL_BARS,
        "min_test_rows_override": 10_000,
    }
    print(
        f"[gen_baseline] {symbol}/{timeframe}: fallback "
        f"triggered={fallback_payload['triggered_insufficient_data']} "
        f"fit_mode={fallback_payload['fit_mode']} "
        f"reason={(fallback_payload.get('split_meta') or {}).get('reason')} "
        f"wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- early-flip manifest ----
    early_flip = _build_early_flip_manifest(close)

    rows, sha16 = _kline_group_dataset_sha16(symbol, timeframe)
    baseline: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "spec_ref": "docs/IC_LA1_SPEC.md §G / B0.1",
        "todo_ref": "docs/IC_LA1_TODO.md Task 0.1",
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "kline_h5_group": KLINE_H5_GROUP_TEMPLATE.format(
            symbol=symbol, timeframe=timeframe
        ),
        "input_contract": {
            "features_h5": str(h5_path.relative_to(REPO_ROOT)),
            "meta_json": str(meta_path.relative_to(REPO_ROOT)),
            "kline_cache": str(KLINE_H5_PATH.relative_to(REPO_ROOT)),
            "kline_rows": rows,
            "kline_sha16": sha16,
            "analyze_signature": (
                "ICFilterOrchestrator.analyze(features_path, labels_path, "
                "meta_path, kline_reader=…)"
            ),
        },
        "canonical_mutation": {
            "m_trunc": "n_keep=int(0.75*n)",
            "m_trunc_ratio": M_TRUNC_RATIO,
            "early_window": "[0, int(2/3*n_keep))",
            "early_window_ratio": EARLY_WINDOW_RATIO,
            "mid_segment_trunc": "prev_end+REFIT_INTERVAL//2",
            "refit_interval_const": REFIT_INTERVAL_CONST,
        },
        # 五路徑
        "regime_rule": regime_rule_payload,
        "regime_kmeans": regime_km_payload,
        "xgboost_phases": phases_payload,
        "long_short": long_short_payload,
        "fallback": fallback_payload,
        "early_flip_manifest": early_flip,
    }
    return baseline


def _assert_early_flip_sides(manifest: dict[str, Any], name: str) -> None:
    """--check assert ②：early-flip 集合兩側 len>0。"""
    regime = manifest.get("regime_rule") or {}
    n_high = int(regime.get("n_high_vol_flip") or 0)
    n_low = int(regime.get("n_low_vol_flip") or 0)
    if n_high <= 0 or n_low <= 0:
        raise SystemExit(
            f"{name}: early-flip sides empty "
            f"(n_high_vol_flip={n_high}, n_low_vol_flip={n_low}); "
            "expected both > 0"
        )
    # 亦檢查 index 列表長度一致
    if len(regime.get("high_vol_flip_indices") or []) != n_high:
        raise SystemExit(f"{name}: high_vol_flip_indices length mismatch")
    if len(regime.get("low_vol_flip_indices") or []) != n_low:
        raise SystemExit(f"{name}: low_vol_flip_indices length mismatch")


def _assert_xgboost_element_payload(xg: dict[str, Any], name: str) -> None:
    """--check：xgboost_phases 必須有 per-index element payload（禁 aggregate-only）。"""
    if not xg.get("labels_sha256"):
        raise SystemExit(f"{name}: xgboost_phases.labels_sha256 missing")
    labels = xg.get("labels")
    timestamps = xg.get("timestamps")
    if not isinstance(labels, list) or len(labels) == 0:
        raise SystemExit(
            f"{name}: xgboost_phases.labels element payload missing or empty"
        )
    if not isinstance(timestamps, list) or len(timestamps) == 0:
        raise SystemExit(
            f"{name}: xgboost_phases.timestamps element payload missing or empty"
        )
    n = int(xg.get("len") or 0)
    if len(labels) != n:
        raise SystemExit(
            f"{name}: xgboost_phases.labels len={len(labels)} != len field={n}"
        )
    if len(timestamps) != n:
        raise SystemExit(
            f"{name}: xgboost_phases.timestamps len={len(timestamps)} != len field={n}"
        )
    # 真實 unix 秒（拒 RangeIndex 0..n-1 假時間）
    if n >= 2 and timestamps[0] == 0 and timestamps[1] == 1 and timestamps[-1] == n - 1:
        raise SystemExit(
            f"{name}: xgboost_phases.timestamps look like positional RangeIndex "
            "(0..n-1); expected kline unix seconds"
        )
    if n >= 1 and int(timestamps[0]) < 1_000_000_000:
        # 2001-09-09 之前的 unix 秒視為不合理（kline 應為 2017+）
        raise SystemExit(
            f"{name}: xgboost_phases.timestamps[0]={timestamps[0]} "
            "not plausible unix seconds"
        )
    # hash 與 element 序列一致（防只塞空 list 或錯序）
    recomputed = _hash_string_array([str(x) for x in labels])
    if recomputed != xg.get("labels_sha256"):
        raise SystemExit(
            f"{name}: xgboost_phases.labels_sha256 mismatch vs element labels"
        )
    ts_recomputed = _hash_string_array([str(t) for t in timestamps])
    if xg.get("timestamps_sha256") and ts_recomputed != xg.get("timestamps_sha256"):
        raise SystemExit(
            f"{name}: xgboost_phases.timestamps_sha256 mismatch vs element timestamps"
        )


def _assert_five_path_keys(data: dict[str, Any], name: str) -> None:
    """--check assert ③：baseline JSON 五路徑鍵齊全 + element payload。"""
    missing = [k for k in PATH_KEYS if k not in data]
    if missing:
        raise SystemExit(f"{name}: missing five-path keys: {missing}")
    # 基本非空
    if not (data.get("regime_rule") or {}).get("regime_names") and not (
        data.get("regime_rule") or {}
    ).get("per_regime"):
        # allow empty only if explicitly empty dict with name_set
        if "name_set_sha256" not in (data.get("regime_rule") or {}):
            raise SystemExit(f"{name}: regime_rule incomplete")
    _assert_xgboost_element_payload(data.get("xgboost_phases") or {}, name)
    if not (data.get("long_short") or {}).get("name_set_sha256"):
        raise SystemExit(f"{name}: long_short.name_set_sha256 missing")
    if "triggered_insufficient_data" not in (data.get("fallback") or {}):
        raise SystemExit(f"{name}: fallback.triggered_insufficient_data missing")


def generate_all() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for run in RUNS:
        print(f"[gen_baseline] running {run['symbol']}/{run['timeframe']} ...")
        baseline = run_one(run)
        out_path = OUTPUT_DIR / run["baseline_name"]
        raw = _canonical_json_bytes(baseline)
        out_path.write_bytes(raw)
        digest = _sha256_bytes(raw)
        print(
            f"[gen_baseline] wrote {out_path.relative_to(REPO_ROOT)} "
            f"sha256={digest}"
        )
        written.append(out_path)
    # B4：三 control 完整 artifact
    written.extend(generate_control_artifacts())
    return written


def check_all() -> int:
    """--check：四類 assert；任一不符 exit 1。"""
    # ① kline sha
    verify_kline_receipts()

    # 若 baseline 不存在則先生成（可重現）
    missing_baselines = [
        run for run in RUNS if not (OUTPUT_DIR / run["baseline_name"]).is_file()
    ]
    if missing_baselines:
        print("[gen_baseline] --check: baselines missing → generate first")
        generate_all()
    else:
        # baseline 在但 control 可能缺：只補 control
        missing_ctrl = [
            control_artifact_name(run["symbol"], run["timeframe"], kind)
            for run in RUNS
            for kind in CONTROL_KINDS
            if not (
                OUTPUT_DIR
                / control_artifact_name(run["symbol"], run["timeframe"], kind)
            ).is_file()
        ]
        if missing_ctrl:
            print(
                f"[gen_baseline] --check: control artifacts missing "
                f"({len(missing_ctrl)}) → generate_control_artifacts"
            )
            generate_control_artifacts()

    for run in RUNS:
        path = OUTPUT_DIR / run["baseline_name"]
        if not path.is_file():
            raise SystemExit(f"baseline missing after generate: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        # ③ five path keys
        _assert_five_path_keys(data, path.name)
        # ② early-flip both sides
        manifest = data.get("early_flip_manifest") or {}
        _assert_early_flip_sides(manifest, path.name)
        # 交叉驗證 baseline 內嵌 kline sha
        expected = EXPECTED_KLINE[(run["symbol"], run["timeframe"])]
        got_sha = (data.get("input_contract") or {}).get("kline_sha16")
        got_rows = (data.get("input_contract") or {}).get("kline_rows")
        if got_sha != expected["sha16"] or int(got_rows or 0) != int(expected["rows"]):
            raise SystemExit(
                f"{path.name}: embedded kline receipt mismatch "
                f"sha={got_sha} rows={got_rows}"
            )
        print(
            f"[gen_baseline] check OK {path.name} "
            f"high_flip={manifest['regime_rule']['n_high_vol_flip']} "
            f"low_flip={manifest['regime_rule']['n_low_vol_flip']}"
        )

    # ④ 三 control artifact 存在 + content/file sha
    check_control_artifacts()

    print(
        "[gen_baseline] --check OK "
        "(sha + early-flip sides + five paths + control full + rules + receipt)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "驗證 kline sha + early-flip 兩側 + 五路徑鍵 + "
            "control full artifact + rules + receipt sha（不符 exit 1）"
        ),
    )
    parser.add_argument(
        "--controls-only",
        action="store_true",
        help="只生成三 control × symbols full-tree artifact（不重跑五路徑 baseline）",
    )
    parser.add_argument(
        "--discover-volatiles",
        action="store_true",
        help="兩次 isolated 跑 discover volatile pointers 並寫 rules+receipt",
    )
    args = parser.parse_args()
    if args.check:
        return check_all()
    if args.discover_volatiles:
        write_volatile_rules_and_receipt(discover=True)
        print("[gen_baseline] discover-volatiles OK")
        return 0
    if args.controls_only:
        if not control_volatile_rules_path().is_file():
            write_volatile_rules_and_receipt(discover=True)
        generate_control_artifacts()
        check_control_artifacts()
        print("[gen_baseline] controls-only OK")
        return 0
    write_volatile_rules_and_receipt(discover=True)
    generate_all()
    for run in RUNS:
        path = OUTPUT_DIR / run["baseline_name"]
        data = json.loads(path.read_text(encoding="utf-8"))
        _assert_five_path_keys(data, path.name)
        _assert_early_flip_sides(data.get("early_flip_manifest") or {}, path.name)
    check_control_artifacts()
    print("[gen_baseline] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
