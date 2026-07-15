#!/usr/bin/env python3
"""LA-0 B0: 可重現改前 golden baseline（真實 ICFilterOrchestrator stage1/4/5）。

SPEC: docs/IC_LA0_SPEC.md §G / §MS
TODO: docs/IC_LA0_TODO.md Task 0.1
B0FIX (codex review): #3 element-level early-prefix; #7 stratified
manifest with stage5 passed∩rejected; side-effect isolation (no data_cache writes).

輸入契約（T1, 已 grep 確認）:
  - ICFilterOrchestrator.analyze(features_path, labels_path, meta_path, kline_reader=...)
  - features HDF5: group ``{symbol}/{tf}/`` 下 datasets features / timestamps / feature_names
  - labels: 可空字串; 有 kline_reader + meta.symbol/timeframe 時 stage2 生成 return_{horizon}
  - meta JSON: symbol / timeframe / config_hash + per-feature {name, category, layer}
  - kline group key: data_cache/feature_klines/kline_cache.h5 → /{SYMBOL}/{tf}/data

特徵來源: data_cache/features registry（若缺則 BLOCKED；本腳本不重跑 Feature Factory）。
末 N bar: **timestamp 尾切**（sort_index 後尾段, 禁位置 index 切）。
"""

from __future__ import annotations

import atexit
import hashlib
import json
import resource
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

from momentum.Analysis.monotonicity_tester import MonotonicityTester  # noqa: E402
from momentum.factories import (  # noqa: E402
    create_feature_reader,
    create_ic_analyzer,
    create_kline_storage_manager,
)

# ---------------------------------------------------------------------------
# 凍結常數（B0 輸入契約 + B0FIX）
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).resolve().parent
INPUTS_DIR = OUTPUT_DIR / "inputs"
KLINE_CACHE_DIR = "data_cache/feature_klines"
KLINE_H5_GROUP_TEMPLATE = "/{symbol}/{timeframe}/data"
TAIL_BARS = 2000
PIT_STATS_VERSION = "pre_la0_baseline"  # B1 前尚無 pit_stats_version
SCHEMA_VERSION = "la0_b0_v2"

# §G L1 early-prefix：每序列截取前 N 個 emitted 元素（值 + 對齊 index）
EARLY_PREFIX_N = 64

# #7 分層取樣：hash-even universe 抽樣 → 小 batch 實跑 stage5 蒐集兩側 → final balance
# （大 probe 單次 analyze 在 FDR/ic_mean 下常 passed=0；小 batch 較能發現真 passers）
SCAN_SAMPLE_N = 2000
SCAN_BATCH_SIZE = 30
SCAN_MAX_BATCHES = 50
FINAL_PASSED_TARGET = 12
FINAL_REJECTED_TARGET = 12
STRATA_SEED = "la0_b0_stratified_v1"
SELECTION_METHOD = (
    "hash_even_sample_batch_stage5_scan_then_balance"
    ":sort_by_sha256(seed:name);even_stride_sample;"
    "analyze_batches(size=30);collect_passed∪rejected;"
    "final=sorted(passed)[:P]+sorted(rejected)[:R];re-analyze_final"
)

# 副作用隔離：reporter 寫入此 tmp，結束刪除；禁止 data_cache/reports|features
_SIDEFX_TMP: Optional[Path] = None

RUNS: list[dict[str, str]] = [
    {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "config_hash": "4a8a0b3726cc906ab3534994605e77f5",
        "baseline_name": "BTCUSDT_1h_baseline.json",
    },
    {
        "symbol": "ETHUSDT",
        "timeframe": "12h",
        "config_hash": "e53e22906c35363757f4cd49d27f973e",
        "baseline_name": "ETHUSDT_12h_baseline.json",
    },
]


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
    return _sha256_bytes("\n".join(sorted(items)).encode("utf-8"))


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


def _json_safe_float_list(values: Any) -> list[Optional[float]]:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    return [_json_safe_float(v) for v in arr.tolist()]


def _ts_str(ts: Any) -> str:
    if hasattr(ts, "isoformat"):
        return str(ts.isoformat())
    return str(ts)


def _early_prefix_payload(
    values: Any,
    timestamps: Optional[list[str]] = None,
    *,
    n: int = EARLY_PREFIX_N,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """§G L1 early-prefix：逐值 + 對齊 timestamp（可機械 atol 比對）。"""
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    take = min(int(n), int(arr.size))
    payload: dict[str, Any] = {
        "n_requested": int(n),
        "n_actual": take,
        "values": _json_safe_float_list(arr[:take]),
    }
    if timestamps is not None:
        payload["timestamps"] = [str(t) for t in timestamps[:take]]
    if extra:
        for key, val in extra.items():
            if isinstance(val, (list, tuple, np.ndarray)):
                seq = list(val)[:take]
                payload[key] = seq
            else:
                payload[key] = val
    return payload


# ---------------------------------------------------------------------------
# Side-effect isolation（禁寫 data_cache/reports|features）
# ---------------------------------------------------------------------------
def _ensure_sidefx_tmp() -> Path:
    global _SIDEFX_TMP
    if _SIDEFX_TMP is None:
        _SIDEFX_TMP = Path(tempfile.mkdtemp(prefix="la0_b0_sidefx_"))
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
    ) -> str:
        name = Path(output_path).name
        target = str(tmp / "features" / name)
        return orig_save_filtered(features_df, selected_features, target)

    reporter.save_report = _save_report  # type: ignore[method-assign]
    reporter.save_filter_log = _save_filter_log  # type: ignore[method-assign]
    reporter.save_filtered_features = _save_filtered_features  # type: ignore[method-assign]
    return tmp


# ---------------------------------------------------------------------------
# #7 deterministic 分層取樣
# ---------------------------------------------------------------------------
def _name_sort_key(name: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{STRATA_SEED}:{name}".encode("utf-8")).hexdigest()
    return (digest, name)


def _stratified_even_sample(all_names: list[str], n: int) -> list[str]:
    """對 sorted-by-hash 名冊做 even-stride 取樣（deterministic、跨 namespace 覆蓋）。"""
    ranked = sorted(all_names, key=_name_sort_key)
    if n <= 0:
        return []
    if n >= len(ranked):
        return ranked
    if n == 1:
        return [ranked[0]]
    # even indices across full ranked list
    indices = [int(round(i * (len(ranked) - 1) / (n - 1))) for i in range(n)]
    # de-dup while preserving order
    seen: set[int] = set()
    out: list[str] = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            out.append(ranked[idx])
    # fill if de-dup shortened
    if len(out) < n:
        for name in ranked:
            if name not in out:
                out.append(name)
            if len(out) >= n:
                break
    return out[:n]


def _stage5_passed_rejected(
    all_features: list[str], stage5_log: dict
) -> tuple[list[str], list[str], set[str]]:
    removed = stage5_log.get("removed_features") or {}
    removed_set: set[str] = set()
    if isinstance(removed, dict):
        for names in removed.values():
            if isinstance(names, list):
                removed_set.update(str(x) for x in names)
    passed = sorted(set(all_features) - removed_set)
    rejected = sorted(removed_set & set(all_features))
    return passed, rejected, removed_set


def _balance_final_selection(
    passed: list[str], rejected: list[str]
) -> tuple[list[str], dict[str, Any]]:
    """從 stage5 兩側 deterministic 取樣；保證 passed>0 且 rejected>0。"""
    if not passed or not rejected:
        raise RuntimeError(
            f"stage5 balance failed: n_passed={len(passed)} n_rejected={len(rejected)}"
        )
    n_p = min(FINAL_PASSED_TARGET, len(passed))
    n_r = min(FINAL_REJECTED_TARGET, len(rejected))
    # 若一側過少，用另一側補足總量但仍保留兩側至少 1
    sel_p = sorted(passed)[:n_p]
    sel_r = sorted(rejected)[:n_r]
    selected = sorted(set(sel_p) | set(sel_r))
    meta = {
        "selection_method": SELECTION_METHOD,
        "strata_seed": STRATA_SEED,
        "final_passed_target": FINAL_PASSED_TARGET,
        "final_rejected_target": FINAL_REJECTED_TARGET,
        "selected_passed": sel_p,
        "selected_rejected": sel_r,
        "n_selected_passed": len(sel_p),
        "n_selected_rejected": len(sel_r),
        "n_selected_total": len(selected),
    }
    return selected, meta


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def _write_features_h5(
    path: Path,
    symbol: str,
    timeframe: str,
    features_df: pd.DataFrame,
) -> None:
    """ICFilterOrchestrator._load_features_hdf5 契約。"""
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


def _build_meta(
    symbol: str,
    timeframe: str,
    config_hash: str,
    feature_names: list[str],
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
    return meta


def _timestamp_tail_cut(features_df: pd.DataFrame, n_bars: int) -> pd.DataFrame:
    """以 timestamp 尾切（sort_index 後取尾段），非位置 iloc 假設無序。"""
    if features_df.empty:
        raise RuntimeError("features_df empty before tail cut")
    ordered = features_df.sort_index()
    if not isinstance(ordered.index, pd.DatetimeIndex):
        try:
            ordered.index = pd.to_datetime(ordered.index, unit="s")
            ordered = ordered.sort_index()
        except (ValueError, TypeError, OverflowError):
            ordered = features_df.sort_index()
    if len(ordered) <= n_bars:
        return ordered
    return ordered.iloc[-n_bars:]


def _materialize_features(
    symbol: str,
    timeframe: str,
    config_hash: str,
    selected: list[str],
    tail_bars: int,
    *,
    stem_tag: str,
    selection_meta: dict[str, Any],
    source_feature_count: int,
) -> tuple[Path, Path, pd.DataFrame, dict[str, Any]]:
    reader = create_feature_reader()
    features_df = reader.load_columns_v2(symbol, timeframe, config_hash, selected)
    row_index = reader.load_row_index_v2(symbol, timeframe, config_hash)
    if row_index is not None:
        features_df = features_df.copy()
        features_df.index = row_index

    features_df = _timestamp_tail_cut(features_df, tail_bars)
    # 欄序穩定：依 selected 順序
    features_df = features_df.reindex(columns=list(selected))
    nan_ratio = {
        str(c): float(features_df[c].isna().mean()) for c in features_df.columns
    }

    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{symbol}_{timeframe}_{config_hash}_{stem_tag}_tail{tail_bars}"
    h5_path = INPUTS_DIR / f"{stem}.h5"
    meta_path = INPUTS_DIR / f"{stem}_meta.json"
    _write_features_h5(h5_path, symbol, timeframe, features_df)
    meta = _build_meta(symbol, timeframe, config_hash, list(features_df.columns))
    meta["baseline_subset"] = {
        **selection_meta,
        "source_feature_count": int(source_feature_count),
        "selected_features": list(features_df.columns),
        "tail_bars_requested": tail_bars,
        "tail_bars_actual": int(len(features_df)),
        "cut_method": "timestamp_tail_sort_index",
        "index_start": str(features_df.index[0]),
        "index_end": str(features_df.index[-1]),
        "nan_ratio": nan_ratio,
        "kline_h5_group": KLINE_H5_GROUP_TEMPLATE.format(
            symbol=symbol, timeframe=timeframe
        ),
    }
    meta_path.write_bytes(_canonical_json_bytes(meta))
    return h5_path, meta_path, features_df, meta


def _list_all_features(symbol: str, timeframe: str, config_hash: str) -> list[str]:
    reader = create_feature_reader()
    try:
        all_names = reader.list_features_v2(symbol, timeframe, config_hash)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"features artifact missing/unreadable for "
            f"{symbol}/{timeframe}/{config_hash}: {exc}"
        ) from exc
    if not all_names:
        raise RuntimeError(f"no features listed for {symbol}/{timeframe}/{config_hash}")
    return list(all_names)


# ---------------------------------------------------------------------------
# Rolling window-end / series capture
# ---------------------------------------------------------------------------
def _aligned_frame(
    features_df: pd.DataFrame, label_series: pd.Series
) -> pd.DataFrame:
    label_name = label_series.name or "label"
    return pd.concat([features_df, label_series.rename(label_name)], axis=1).dropna()


def _rolling_window_ends(
    features_df: pd.DataFrame,
    label_series: pd.Series,
    window: int,
    stride: int,
    test_mask: Optional[np.ndarray],
) -> tuple[list[str], list[int]]:
    """與 orchestrator._slice_rolling_ic_to_test 對齊的 emitted window-end timestamps。"""
    aligned = _aligned_frame(features_df, label_series)
    if aligned.empty or window <= 1 or len(aligned) < window:
        return [], []
    end_positions = np.arange(window, len(aligned) + 1, stride)
    end_index = aligned.index[end_positions - 1]
    if test_mask is not None:
        test_index = set(features_df.index[np.asarray(test_mask, dtype=bool)])
        keep = [i for i, ts in enumerate(end_index) if ts in test_index]
        end_index = end_index[keep]
        end_positions = end_positions[keep]
    timestamps = [_ts_str(ts) for ts in end_index.tolist()]
    # end_positions 為 aligned 上 1-based end（與 orchestrator 一致：end_positions-1）
    positions = [int(p) - 1 for p in end_positions.tolist()]
    return timestamps, positions


def _rolling_ic_payload(
    rolling_ic: dict,
    features_df: pd.DataFrame,
    label_series: pd.Series,
    windows: list[int],
    stride: int,
    test_mask: Optional[np.ndarray],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    empty_windows = 0
    ends_cache: dict[int, tuple[list[str], list[int]]] = {}
    for window in windows:
        ends_cache[int(window)] = _rolling_window_ends(
            features_df, label_series, int(window), stride, test_mask
        )

    for feature, win_map in sorted(rolling_ic.items(), key=lambda x: str(x[0])):
        feat_payload: dict[str, Any] = {}
        if not isinstance(win_map, dict):
            continue
        for window_key, series in sorted(win_map.items(), key=lambda x: str(x[0])):
            arr = np.asarray(series, dtype=np.float64).reshape(-1)
            if arr.size == 0:
                empty_windows += 1
            # parse window int from "window_21"
            w_int: Optional[int] = None
            if str(window_key).startswith("window_"):
                try:
                    w_int = int(str(window_key).split("_", 1)[1])
                except ValueError:
                    w_int = None
            ts_list: list[str] = []
            pos_list: list[int] = []
            if w_int is not None and w_int in ends_cache:
                ts_list, pos_list = ends_cache[w_int]
            # 長度對齊（slice 後 series 應與 kept ends 同長）
            if ts_list and len(ts_list) != arr.size:
                # 仍存 values；timestamp 以 min 長度對齊
                pass
            feat_payload[str(window_key)] = {
                "sha256": _hash_float_array(arr),
                "len": int(arr.size),
                "finite_count": int(np.isfinite(arr).sum()),
                "nan_count": int((~np.isfinite(arr)).sum()),
                "early_prefix": _early_prefix_payload(
                    arr,
                    ts_list if ts_list else None,
                    extra={
                        "emitted_window_end_positions": pos_list if pos_list else [],
                        "emitted_window_ends_note": (
                            "timestamps = aligned.dropna index at window-end "
                            "(orchestrator slice keep-in-test); "
                            "positions = 0-based index into aligned frame"
                        ),
                    },
                ),
            }
        payload[str(feature)] = feat_payload
    return {
        "per_feature_window": payload,
        "empty_window_series_count": empty_windows,
        "early_prefix_n": EARLY_PREFIX_N,
        "alignment_policy": (
            "emitted window-end on feature+label dropna aligned index; "
            "split ON → keep ends whose timestamp ∈ test_mask"
        ),
    }


def _icir_payload(icir: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for feature, stats in sorted(icir.items(), key=lambda x: str(x[0])):
        if not isinstance(stats, dict):
            continue
        out[str(feature)] = {
            "ic_mean": _json_safe_float(stats.get("ic_mean")),
            "ic_std": _json_safe_float(stats.get("ic_std")),
            "icir": _json_safe_float(stats.get("icir")),
            "ic_hit_rate": _json_safe_float(stats.get("ic_hit_rate")),
        }
    return out


def _mono_payload(mono_cache: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for feature, body in sorted(mono_cache.items(), key=lambda x: str(x[0])):
        if not isinstance(body, dict):
            continue
        qr = body.get("quantile_returns") or {}
        qmr = qr.get("quantile_mean_returns") if isinstance(qr, dict) else {}
        safe_qmr = {
            str(k): _json_safe_float(v)
            for k, v in sorted((qmr or {}).items(), key=lambda x: str(x[0]))
        }
        out[str(feature)] = {
            "monotonicity_score": _json_safe_float(body.get("monotonicity_score")),
            "quantile_mean_returns": safe_qmr,
            "quantile_mean_returns_sha256": _hash_float_array(
                [safe_qmr[k] if safe_qmr[k] is not None else np.nan for k in sorted(safe_qmr)]
            ),
        }
    return out


def _extract_bin_t_series(
    features_df: pd.DataFrame,
    label_series: pd.Series,
    test_mask: Optional[np.ndarray],
    num_quantiles: int = 5,
) -> dict[str, Any]:
    """現況全域 qcut bin 序列（legacy look-ahead baseline）+ early-prefix 逐值。"""
    mono = MonotonicityTester({})
    if test_mask is not None:
        mask = np.asarray(test_mask, dtype=bool)
        feat = features_df.loc[features_df.index[mask]]
        lab = label_series.loc[label_series.index[mask]]
    else:
        feat = features_df
        lab = label_series

    out: dict[str, Any] = {}
    for col in feat.columns:
        data = pd.DataFrame({"feature": feat[col], "label": lab}).dropna()
        if data.empty:
            out[str(col)] = {
                "bin_t_sha256": _sha256_bytes(b"empty"),
                "bin_t_len": 0,
                "n_unique": 0,
                "nan_ratio": 1.0,
                "early_prefix": _early_prefix_payload([], []),
            }
            continue
        n_q = mono._select_num_quantiles(len(data), num_quantiles)
        bins = mono._assign_quantiles(data, n_q)
        if bins is None:
            out[str(col)] = {
                "bin_t_sha256": _sha256_bytes(b"none"),
                "bin_t_len": 0,
                "n_unique": 0,
                "nan_ratio": 1.0,
                "early_prefix": _early_prefix_payload([], []),
            }
            continue
        arr = bins.to_numpy(dtype=np.float64)
        ts = [_ts_str(t) for t in data.index.tolist()]
        # index positions into feat (post test-mask) for alignment audits
        pos = list(range(len(arr)))
        out[str(col)] = {
            "bin_t_sha256": _hash_float_array(arr),
            "bin_t_len": int(arr.size),
            "n_unique": int(pd.Series(arr).nunique(dropna=True)),
            "nan_ratio": float(np.isnan(arr).mean()) if arr.size else 1.0,
            "early_prefix": _early_prefix_payload(
                arr,
                ts,
                extra={
                    "index_positions_in_dropna": pos,
                    "scope": "test_mask" if test_mask is not None else "full",
                },
            ),
        }
    return out


def _turnover_payload(turnover: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for feature, body in sorted(turnover.items(), key=lambda x: str(x[0])):
        if not isinstance(body, dict):
            continue
        ts = body.get("time_series") or {}
        q_to = list(ts.get("quantile_turnovers") or [])
        r_ch = list(ts.get("rank_change_rates") or [])
        stamps = list(ts.get("timestamps") or [])
        out[str(feature)] = {
            "quantile_turnover": _json_safe_float(body.get("quantile_turnover")),
            "rank_change_rate": _json_safe_float(body.get("rank_change_rate")),
            "autocorrelation": _json_safe_float(body.get("autocorrelation")),
            # legacy: diff().dropna() → 長度 n-1（S2 修後將變 n）
            "time_series": {
                "quantile_turnovers_len": int(len(q_to)),
                "rank_change_rates_len": int(len(r_ch)),
                "quantile_turnovers_sha256": _hash_float_array(q_to),
                "rank_change_rates_sha256": _hash_float_array(r_ch),
                "timestamps_len": int(len(stamps)),
                "legacy_length_policy": "n-1_after_dropna",
                "early_prefix": {
                    "n_requested": EARLY_PREFIX_N,
                    "n_actual": min(EARLY_PREFIX_N, len(q_to), len(r_ch)),
                    "quantile_turnovers": _json_safe_float_list(
                        q_to[:EARLY_PREFIX_N]
                    ),
                    "rank_change_rates": _json_safe_float_list(
                        r_ch[:EARLY_PREFIX_N]
                    ),
                    "timestamps": [str(t) for t in stamps[:EARLY_PREFIX_N]],
                },
            },
        }
    return out


def _pearson_control(
    orchestrator: Any,
    features_df: pd.DataFrame,
    label_series: pd.Series,
    split_context: Optional[dict],
    rolling_windows: list[int],
    rolling_stride: int,
) -> dict[str, Any]:
    """control: pearson rolling IC（P0-1 修後應 Δ≈0）。"""
    rolling_features = features_df
    rolling_label = label_series
    test_mask_for_ends: Optional[np.ndarray] = None
    if split_context is not None:
        train_mask = np.asarray(split_context.get("train_mask"), dtype=bool)
        test_mask = np.asarray(split_context.get("test_mask"), dtype=bool)
        allowed = train_mask | test_mask
        rolling_features = features_df.loc[features_df.index[allowed]]
        rolling_label = label_series.loc[label_series.index[allowed]]
        test_mask_for_ends = test_mask[allowed]

    rolling = orchestrator._ic_engine.compute_rolling_ic(
        rolling_features,
        rolling_label,
        rolling_windows,
        rolling_stride,
        method="pearson",
    )
    if split_context is not None:
        train_mask = np.asarray(split_context.get("train_mask"), dtype=bool)
        test_mask = np.asarray(split_context.get("test_mask"), dtype=bool)
        allowed = train_mask | test_mask
        rolling_test_mask = test_mask[allowed]
        rolling = orchestrator._slice_rolling_ic_to_test(
            rolling,
            rolling_features,
            rolling_label,
            rolling_windows,
            rolling_stride,
            rolling_test_mask,
        )
        test_mask_for_ends = rolling_test_mask
    return _rolling_ic_payload(
        rolling,
        rolling_features,
        rolling_label,
        rolling_windows,
        rolling_stride,
        test_mask_for_ends,
    )


def _train_mask_winsorize_control(
    orchestrator: Any,
    raw_features: pd.DataFrame,
    train_mask: np.ndarray,
) -> dict[str, Any]:
    """control: train_mask 段 winsorize（P0-3 修後 train 段應 Δ≈0）。"""
    preproc = orchestrator._preprocessor
    winsor_cfg = getattr(orchestrator._config.preprocessing, "winsorization", None)
    method = "percentile"
    lower = 1.0
    upper = 99.0
    if winsor_cfg is not None:
        method = getattr(winsor_cfg, "method", method)
        lower = float(getattr(winsor_cfg, "lower_percentile", lower))
        upper = float(getattr(winsor_cfg, "upper_percentile", upper))

    clipped, _log = preproc.winsorize(
        raw_features.copy(),
        method=method,
        lower=lower,
        upper=upper,
        metadata=None,
        fit_mask=train_mask,
    )
    train_vals = clipped.loc[clipped.index[train_mask]]
    # early-prefix: 前 EARLY_PREFIX_N 列 × 全欄 flatten 不實用；存 per-col early values 的 hash + 首列向量
    first_row = (
        train_vals.iloc[0].to_numpy(dtype=np.float64)
        if len(train_vals)
        else np.array([], dtype=np.float64)
    )
    return {
        "train_rows": int(train_mask.sum()),
        "value_sha256": _hash_float_array(train_vals.to_numpy(dtype=np.float64)),
        "nan_mask_sha256": _hash_bool_array(train_vals.isna().to_numpy()),
        "shape": [int(train_vals.shape[0]), int(train_vals.shape[1])],
        "early_prefix": {
            "n_rows": min(EARLY_PREFIX_N, int(len(train_vals))),
            "row_timestamps": [
                _ts_str(t) for t in train_vals.index[:EARLY_PREFIX_N].tolist()
            ],
            "first_row_values": _json_safe_float_list(first_row),
            "first_row_sha256": _hash_float_array(first_row),
        },
    }


def _rss_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _run_analyze(
    h5_path: Path, meta_path: Path
) -> tuple[Any, dict, float, int, int]:
    orchestrator = create_ic_analyzer()
    _isolate_orchestrator_persist(orchestrator)
    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    rss_before = _rss_kb()
    t0 = time.perf_counter()
    report = orchestrator.analyze(
        features_path=str(h5_path.resolve()),
        labels_path="",
        meta_path=str(meta_path.resolve()),
        kline_reader=kline_reader,
    )
    wall_s = float(time.perf_counter() - t0)
    rss_after = _rss_kb()
    return orchestrator, report, wall_s, rss_before, rss_after


def _unlink_quiet(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)  # type: ignore[call-arg]
    except TypeError:
        if path.exists():
            path.unlink()


def _select_balanced_features(
    symbol: str,
    timeframe: str,
    config_hash: str,
    all_names: list[str],
) -> tuple[list[str], dict[str, Any]]:
    """Deterministic 分層抽樣 + batch stage5 掃描，蒐集 passed 與 rejected 兩側。

    大 universe 單次 cap 易 passed=0（ic_mean/FDR）；改以 hash-even sample
    切小 batch 實跑真實 analyze，累積兩側後再 balance final set。
    """
    source_n = len(all_names)
    sample = _stratified_even_sample(all_names, SCAN_SAMPLE_N)
    passed_pool: set[str] = set()
    rejected_pool: set[str] = set()
    batches_ok = 0
    batches_fail = 0
    wall_total = 0.0

    print(
        f"[gen_baseline] {symbol}/{timeframe}: scan sample_n={len(sample)} "
        f"batch={SCAN_BATCH_SIZE} max_batches={SCAN_MAX_BATCHES} "
        f"(source_default_N={source_n})"
    )

    for batch_i, start in enumerate(range(0, len(sample), SCAN_BATCH_SIZE)):
        if batch_i >= SCAN_MAX_BATCHES:
            break
        # 已湊滿目標可早停
        if (
            len(passed_pool) >= FINAL_PASSED_TARGET
            and len(rejected_pool) >= FINAL_REJECTED_TARGET
        ):
            break
        chunk = sample[start : start + SCAN_BATCH_SIZE]
        if not chunk:
            continue
        h5_path, meta_path, _feat, _meta = _materialize_features(
            symbol,
            timeframe,
            config_hash,
            chunk,
            TAIL_BARS,
            stem_tag=f"scan_b{batch_i}",
            selection_meta={
                "phase": "scan_batch",
                "selection_method": SELECTION_METHOD,
                "strata_seed": STRATA_SEED,
                "batch_index": batch_i,
                "batch_size": len(chunk),
            },
            source_feature_count=source_n,
        )
        try:
            orchestrator, report, wall_s, _, _ = _run_analyze(h5_path, meta_path)
            wall_total += wall_s
            ic_cache = orchestrator._ic_cache or {}
            features_df = ic_cache.get("features_df")
            if features_df is None:
                batches_fail += 1
                continue
            filter_log = report.get("filter_log") or {}
            stage5_log = filter_log.get("stage5_thresholds") or {}
            all_features = [str(c) for c in features_df.columns]
            passed, rejected, _ = _stage5_passed_rejected(all_features, stage5_log)
            passed_pool.update(passed)
            rejected_pool.update(rejected)
            batches_ok += 1
            if passed:
                print(
                    f"[gen_baseline] {symbol}/{timeframe}: batch{batch_i} "
                    f"passed+={len(passed)} pool_p={len(passed_pool)} "
                    f"pool_r={len(rejected_pool)} wall={wall_s:.2f}s"
                )
        except Exception as exc:  # noqa: BLE001 — 掃描容錯（部分 chunk 有 engine 邊界錯）
            batches_fail += 1
            print(
                f"[gen_baseline] {symbol}/{timeframe}: batch{batch_i} "
                f"FAIL {type(exc).__name__}: {exc}"
            )
        finally:
            _unlink_quiet(h5_path)
            _unlink_quiet(meta_path)

    # scan_diag 進 baseline/meta 的鍵必須可重現（禁 wall）
    scan_diag = {
        "sample_n": len(sample),
        "batch_size": SCAN_BATCH_SIZE,
        "max_batches": SCAN_MAX_BATCHES,
        "batches_ok": batches_ok,
        "batches_fail": batches_fail,
        "n_passed_pool": len(passed_pool),
        "n_rejected_pool": len(rejected_pool),
    }
    print(
        f"[gen_baseline] {symbol}/{timeframe}: scan done "
        f"passed_pool={len(passed_pool)} rejected_pool={len(rejected_pool)} "
        f"batches_ok={batches_ok} fail={batches_fail} wall_total={wall_total:.2f}s"
    )

    if not passed_pool or not rejected_pool:
        raise RuntimeError(
            f"BLOCKED: stage5 both sides unavailable for {symbol}/{timeframe} "
            f"after batch scan; diag={scan_diag}"
        )

    selected, bal_meta = _balance_final_selection(
        sorted(passed_pool), sorted(rejected_pool)
    )
    bal_meta["scan"] = scan_diag
    bal_meta["source_feature_count"] = source_n
    bal_meta["actual_default_N"] = source_n
    bal_meta["config_hash"] = config_hash
    # live wall 僅回傳給 telemetry sidecar，不進 baseline/meta
    bal_meta["_live_scan_wall_total_s"] = float(wall_total)
    return selected, bal_meta


def run_one(run: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    symbol = run["symbol"]
    timeframe = run["timeframe"]
    config_hash = run["config_hash"]

    all_names = _list_all_features(symbol, timeframe, config_hash)
    actual_default_n = len(all_names)

    selected, selection_meta = _select_balanced_features(
        symbol, timeframe, config_hash, all_names
    )
    live_scan_wall = float(selection_meta.pop("_live_scan_wall_total_s", 0.0))

    # final re-analyze；若 FDR 合併後翻成單側，縮 rejected 再試一次
    final_attempts = [
        selected,
        sorted(
            set(selection_meta.get("selected_passed") or [])
            | set(
                (selection_meta.get("selected_rejected") or [])[
                    : max(3, FINAL_REJECTED_TARGET // 2)
                ]
            )
        ),
    ]
    orchestrator = None
    report: dict[str, Any] = {}
    wall_s = 0.0
    rss_before = 0
    rss_after = 0
    h5_path: Path = INPUTS_DIR / "placeholder.h5"
    meta_path: Path = INPUTS_DIR / "placeholder_meta.json"
    raw_features = pd.DataFrame()
    meta: dict[str, Any] = {}
    features_df = pd.DataFrame()
    label_series = pd.Series(dtype=float)
    split_context = None
    rolling_ic: dict = {}
    icir: dict = {}
    mono_cache: dict = {}
    turnover: dict = {}
    stage5_log: dict = {}
    passed_features: list[str] = []
    rejected_features: list[str] = []

    for attempt_i, attempt_cols in enumerate(final_attempts):
        if not attempt_cols:
            continue
        stem_tag = (
            f"strat_p{sum(1 for c in attempt_cols if c in set(selection_meta.get('selected_passed') or []))}"
            f"r{sum(1 for c in attempt_cols if c in set(selection_meta.get('selected_rejected') or []))}"
            f"_a{attempt_i}"
        )
        h5_path, meta_path, raw_features, meta = _materialize_features(
            symbol,
            timeframe,
            config_hash,
            attempt_cols,
            TAIL_BARS,
            stem_tag=stem_tag,
            selection_meta={
                **selection_meta,
                "phase": "final",
                "final_attempt": attempt_i,
                "final_selected": list(attempt_cols),
            },
            source_feature_count=actual_default_n,
        )
        orchestrator, report, wall_s, rss_before, rss_after = _run_analyze(
            h5_path, meta_path
        )
        ic_cache = orchestrator._ic_cache or {}
        features_df = ic_cache.get("features_df")
        if features_df is None or features_df.empty:
            raise RuntimeError(
                f"{symbol}/{timeframe}: features_df missing after analyze"
            )
        label_series = ic_cache.get("label_series")
        if label_series is None:
            raise RuntimeError(
                f"{symbol}/{timeframe}: label_series missing after analyze"
            )
        split_context = ic_cache.get("split_context")
        rolling_ic = ic_cache.get("rolling_ic") or {}
        icir = ic_cache.get("icir") or {}
        mono_cache = (
            orchestrator._monotonicity_cache or report.get("quantile_returns") or {}
        )
        turnover = report.get("turnover_analysis") or {}
        filter_log = report.get("filter_log") or {}
        stage5_log = filter_log.get("stage5_thresholds") or {}
        all_features = [str(c) for c in features_df.columns]
        passed_features, rejected_features, _ = _stage5_passed_rejected(
            all_features, stage5_log
        )
        print(
            f"[gen_baseline] {symbol}/{timeframe}: final attempt{attempt_i} "
            f"n={len(all_features)} passed={len(passed_features)} "
            f"rejected={len(rejected_features)}"
        )
        if passed_features and rejected_features:
            selection_meta["final_attempt_used"] = attempt_i
            break
    else:
        raise RuntimeError(
            f"{symbol}/{timeframe}: final baseline stage5 degenerate "
            f"passed={len(passed_features)} rejected={len(rejected_features)}"
        )

    windows = list(orchestrator._config.ic_calculation.rolling_windows)
    stride = int(orchestrator._config.ic_calculation.rolling_stride)

    test_mask = None
    train_mask = None
    if split_context is not None:
        test_mask = np.asarray(split_context.get("test_mask"), dtype=bool)
        train_mask = np.asarray(split_context.get("train_mask"), dtype=bool)

    # rolling ends 用 stage4 同 scope：train|test allowed 後 slice to test
    rolling_features = features_df
    rolling_label = label_series
    rolling_test_mask = test_mask
    if split_context is not None and test_mask is not None and train_mask is not None:
        allowed = train_mask | test_mask
        rolling_features = features_df.loc[features_df.index[allowed]]
        rolling_label = label_series.loc[label_series.index[allowed]]
        rolling_test_mask = test_mask[allowed]

    bin_t = _extract_bin_t_series(features_df, label_series, test_mask)
    pearson = _pearson_control(
        orchestrator,
        features_df,
        label_series,
        split_context,
        windows,
        stride,
    )
    train_winsor_control: Optional[dict[str, Any]] = None
    if train_mask is not None and train_mask.any():
        raw_from_orch, _ = orchestrator._load_features_hdf5(str(h5_path.resolve()))
        raw_from_orch = raw_from_orch.reindex(columns=list(features_df.columns))
        if len(raw_from_orch) == len(train_mask):
            train_winsor_control = _train_mask_winsorize_control(
                orchestrator, raw_from_orch, train_mask
            )

    stage1_value_sha = _hash_float_array(features_df.to_numpy(dtype=np.float64))
    stage1_nan_mask_sha = _hash_bool_array(features_df.isna().to_numpy())
    preproc_log = ic_cache.get("preproc_log") or {}

    schema = {
        "rolling_ic_keys": [
            "per_feature_window",
            "empty_window_series_count",
            "early_prefix_n",
            "alignment_policy",
        ],
        "rolling_window_fields": [
            "sha256",
            "len",
            "finite_count",
            "nan_count",
            "early_prefix",
        ],
        "early_prefix_fields": [
            "n_requested",
            "n_actual",
            "values",
            "timestamps",
            "emitted_window_end_positions",
        ],
        "icir_fields": ["ic_mean", "ic_std", "icir", "ic_hit_rate"],
        "mono_fields": [
            "monotonicity_score",
            "quantile_mean_returns",
            "quantile_mean_returns_sha256",
            "bin_t",
        ],
        "bin_t_fields": [
            "bin_t_sha256",
            "bin_t_len",
            "early_prefix",
        ],
        "turnover_fields": [
            "quantile_turnover",
            "rank_change_rate",
            "time_series",
        ],
        "turnover_ts_fields": [
            "quantile_turnovers_sha256",
            "rank_change_rates_sha256",
            "early_prefix",
        ],
        "stage1_fields": ["winsorize_value_sha256", "nan_mask_sha256"],
        "control_fields": ["pearson_rolling_ic", "train_mask_winsorize"],
    }

    n_rows = int(len(features_df))
    n_features = int(features_df.shape[1])

    baseline: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "pit_stats_version": PIT_STATS_VERSION,
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "kline_h5_group": KLINE_H5_GROUP_TEMPLATE.format(
            symbol=symbol, timeframe=timeframe
        ),
        "input_contract": {
            "features_path": str(h5_path.relative_to(REPO_ROOT)),
            "features_h5_sha256": _sha256_file(h5_path),
            "meta_path": str(meta_path.relative_to(REPO_ROOT)),
            "meta_sha256": _sha256_file(meta_path),
            "labels_path": "",
            "labels_source": "kline_reader.stage2_generate_returns",
            "label_definition": "return_5 (default_horizon=5, return_type=simple)",
            "kline_cache_dir": KLINE_CACHE_DIR,
            "tail_bars_requested": TAIL_BARS,
            "tail_bars_actual": n_rows,
            "cut_method": "timestamp_tail_sort_index",
            "index_start": str(features_df.index[0]),
            "index_end": str(features_df.index[-1]),
            "selection_method": SELECTION_METHOD,
            "strata_seed": STRATA_SEED,
            "config_hash": config_hash,
            "actual_default_N": actual_default_n,
            "source_feature_count": actual_default_n,
            "selected_features": list(features_df.columns),
            "selected_features_sha256": _hash_string_set(list(features_df.columns)),
            "selection_meta": selection_meta,
            "nan_ratio": (meta.get("baseline_subset") or {}).get("nan_ratio") or {},
            "early_prefix_n": EARLY_PREFIX_N,
        },
        "config_snapshot": {
            "default_method": orchestrator._config.global_settings.default_method,
            "rolling_windows": windows,
            "rolling_stride": stride,
            "monotonicity_score_min": float(
                orchestrator._config.thresholds.monotonicity_score_min
            ),
            "turnover_enabled": bool(orchestrator._config.turnover.enabled),
            "ic_train_test_split": bool(orchestrator._config.ic_train_test_split),
            "winsorization_enabled": bool(
                orchestrator._config.preprocessing.winsorization.enabled
            ),
            "winsorization_method": orchestrator._config.preprocessing.winsorization.method,
            "standardize": "none",
        },
        "counts": {
            "n_rows": n_rows,
            "n_features": n_features,
            "n_passed_features": int(len(passed_features)),
            "n_rejected_features": int(len(rejected_features)),
            "train_rows": int(train_mask.sum()) if train_mask is not None else None,
            "test_rows": int(test_mask.sum()) if test_mask is not None else None,
            "actual_default_N": actual_default_n,
        },
        "schema": schema,
        "rolling_ic": _rolling_ic_payload(
            rolling_ic,
            rolling_features,
            rolling_label,
            windows,
            stride,
            rolling_test_mask,
        ),
        "icir": _icir_payload(icir),
        "monotonicity": {
            "scores": _mono_payload(mono_cache),
            "bin_t": bin_t,
        },
        "turnover": _turnover_payload(turnover),
        "stage1": {
            "winsorize_value_sha256": stage1_value_sha,
            "nan_mask_sha256": stage1_nan_mask_sha,
            "preproc_log": {
                "winsorized_features": list(preproc_log.get("winsorized_features") or []),
                "skipped_winsorization": list(
                    preproc_log.get("skipped_winsorization") or []
                ),
                "removed_features": preproc_log.get("removed_features") or {},
            },
            "shape": [n_rows, n_features],
        },
        "passed_features": {
            "names": passed_features,
            "sha256": _hash_string_set(passed_features),
            "count": int(len(passed_features)),
            "rejected_names": rejected_features,
            "rejected_count": int(len(rejected_features)),
            "rejected_sha256": _hash_string_set(rejected_features),
            "stage5_threshold_log": {
                "input_features": stage5_log.get("input_features"),
                "output_features": stage5_log.get("output_features"),
                "alpha_effective": stage5_log.get("alpha_effective"),
                "n_tests": stage5_log.get("n_tests"),
                "removed_features": stage5_log.get("removed_features"),
            },
        },
        "control": {
            "pearson_rolling_ic": pearson,
            "train_mask_winsorize": train_winsor_control,
        },
        "before_perf_telemetry": {
            "n_features": n_features,
            "n_rows": n_rows,
            "actual_default_N": actual_default_n,
            "rolling_windows": windows,
            "method": "spearman",
            "rss_unit_note": "resource.ru_maxrss: bytes on macOS, KB on Linux",
            "note": (
                "non-blocking telemetry for perf epic; not a merge gate. "
                "Live wall/rss + actual_default_N recorded in "
                "before_perf_telemetry_receipt.json"
            ),
            "live_wall_rss_in_sidecar": True,
        },
        "report_metadata": {
            k: (report.get("metadata") or {}).get(k)
            for k in (
                "symbol",
                "timeframe",
                "feature_count_original",
                "feature_count_filtered",
                "truncation_mode",
                "ic_train_test_split",
            )
        },
    }
    live_telemetry = {
        "symbol": symbol,
        "timeframe": timeframe,
        "wall_seconds": wall_s,
        "scan_wall_total_s": live_scan_wall,
        "rss_max_raw": rss_after,
        "rss_before_raw": rss_before,
        "n_features": n_features,
        "n_rows": n_rows,
        "actual_default_N": actual_default_n,
        "n_passed": len(passed_features),
        "n_rejected": len(rejected_features),
        "selection_method": SELECTION_METHOD,
        "config_hash": config_hash,
        "rolling_windows": windows,
        "method": "spearman",
        "scan": selection_meta.get("scan"),
    }
    _ = raw_features
    return baseline, live_telemetry


def _assert_element_level(data: dict[str, Any], name: str) -> None:
    rolling = (data.get("rolling_ic") or {}).get("per_feature_window") or {}
    if not rolling:
        raise SystemExit(f"{name}: rolling_ic empty")
    sample_feat = next(iter(rolling.values()))
    sample_win = next(iter(sample_feat.values()))
    ep = sample_win.get("early_prefix") or {}
    if not ep.get("values"):
        raise SystemExit(f"{name}: rolling early_prefix.values missing")
    if "timestamps" not in ep:
        raise SystemExit(f"{name}: rolling early_prefix.timestamps missing")

    bin_t = (data.get("monotonicity") or {}).get("bin_t") or {}
    if not bin_t:
        raise SystemExit(f"{name}: bin_t empty")
    b0 = next(iter(bin_t.values()))
    if not (b0.get("early_prefix") or {}).get("values") and b0.get("bin_t_len", 0) > 0:
        raise SystemExit(f"{name}: bin_t early_prefix.values missing")

    turnover = data.get("turnover") or {}
    if not turnover:
        raise SystemExit(f"{name}: turnover empty")
    t0 = next(iter(turnover.values()))
    ts_ep = ((t0.get("time_series") or {}).get("early_prefix")) or {}
    if "quantile_turnovers" not in ts_ep or "rank_change_rates" not in ts_ep:
        raise SystemExit(f"{name}: turnover early_prefix incomplete")

    counts = data.get("counts") or {}
    if int(counts.get("n_passed_features") or 0) <= 0:
        raise SystemExit(f"{name}: n_passed_features must be > 0")
    if int(counts.get("n_rejected_features") or 0) <= 0:
        raise SystemExit(f"{name}: n_rejected_features must be > 0")
    if int(counts.get("actual_default_N") or 0) <= 0:
        raise SystemExit(f"{name}: actual_default_N missing")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # 清掉舊 lex top50 物化檔（避免殘留混淆）
    if INPUTS_DIR.exists():
        for stale in INPUTS_DIR.glob("*_top50_tail*"):
            stale.unlink()
        for stale in INPUTS_DIR.glob("*_probe*_tail*"):
            stale.unlink()

    written: list[Path] = []
    telemetry_receipt: list[dict[str, Any]] = []
    for run in RUNS:
        print(f"[gen_baseline] running {run['symbol']}/{run['timeframe']} ...")
        baseline, live_telem = run_one(run)
        out_path = OUTPUT_DIR / run["baseline_name"]
        raw = _canonical_json_bytes(baseline)
        out_path.write_bytes(raw)
        digest = _sha256_bytes(raw)
        print(
            f"[gen_baseline] wrote {out_path.relative_to(REPO_ROOT)} "
            f"sha256={digest} n_features={baseline['counts']['n_features']} "
            f"passed={baseline['counts']['n_passed_features']} "
            f"rejected={baseline['counts']['n_rejected_features']} "
            f"default_N={baseline['counts']['actual_default_N']} "
            f"n_rows={baseline['counts']['n_rows']} "
            f"wall={live_telem['wall_seconds']:.3f}s "
            f"rss_max_raw={live_telem['rss_max_raw']}"
        )
        written.append(out_path)
        telemetry_receipt.append(live_telem)

    receipt_path = OUTPUT_DIR / "before_perf_telemetry_receipt.json"
    receipt_path.write_bytes(
        _canonical_json_bytes(
            {
                "schema_version": "la0_b0_perf_receipt_v2",
                "note": (
                    "Live wall/rss + actual_default_N (source universe without cap); "
                    "not part of baseline sha256 gate"
                ),
                "selection_method": SELECTION_METHOD,
                "early_prefix_n": EARLY_PREFIX_N,
                "runs": telemetry_receipt,
            }
        )
    )
    print(f"[gen_baseline] telemetry receipt → {receipt_path.relative_to(REPO_ROOT)}")

    required_top = [
        "pit_stats_version",
        "rolling_ic",
        "icir",
        "monotonicity",
        "turnover",
        "stage1",
        "passed_features",
        "control",
        "before_perf_telemetry",
        "schema",
        "counts",
        "input_contract",
    ]
    for path in written:
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = [k for k in required_top if k not in data]
        if missing:
            raise SystemExit(f"{path.name} missing keys: {missing}")
        if not data.get("control", {}).get("pearson_rolling_ic"):
            raise SystemExit(f"{path.name} control.pearson_rolling_ic empty")
        if data.get("config_snapshot", {}).get("ic_train_test_split"):
            if not data.get("control", {}).get("train_mask_winsorize"):
                raise SystemExit(f"{path.name} control.train_mask_winsorize empty")
        mono = data.get("monotonicity") or {}
        if "bin_t" not in mono or "scores" not in mono:
            raise SystemExit(f"{path.name} monotonicity incomplete")
        stage1 = data.get("stage1") or {}
        if not stage1.get("winsorize_value_sha256") or not stage1.get("nan_mask_sha256"):
            raise SystemExit(f"{path.name} stage1 hashes missing")
        _assert_element_level(data, path.name)

    print("[gen_baseline] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
