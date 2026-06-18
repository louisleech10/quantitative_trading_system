#!/usr/bin/env python3
"""Codex 獨立 L6.5 B3b 資料正確性簽核。

驗證焦點：
1. 真實 kline 生成特徵後，外部 causal=False 被強制成 causal=True。
2. 竄改未來 bar 不改變過去 L6.5 輸出。
3. 多 TF 先在 native TF 計算 L6.5，再 merge 到 1h，merge 後值等於 native PIT 值。
4. train/test split 邊界後資料被竄改時，train split 輸出不變。
5. 10 symbol × 3 TF schema/NaN/Inf gate 一致，且 shared instance 不污染後續 symbol。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import h5py
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (  # noqa: E402
    FeaturePreprocessor,
)

KLINE_CACHE = PROJECT_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
TIMEFRAMES: Tuple[str, ...] = ("1h", "4h", "12h")
MAX_ROWS = 720
PIT_TAMPER_BARS = 48
PIT_GUARD_BARS = 96

L65_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "mode": "replace",
    "causal_preprocessing": True,
    "winsorization": {
        "enabled": True,
        "method": "quantile",
        "quantile_range": [0.02, 0.98],
        "window": 96,
        "apply_to": "all",
    },
    "rank_transform": {"enabled": True, "window": 96, "apply_to": "all"},
    "gaussian_normalize": {"enabled": False},
    "adaptive_zscore": {
        "enabled": True,
        "windows": [48, 96],
        "epsilon": 1e-8,
        "apply_to": "all",
    },
    "fractional_differencing": {"enabled": False},
    "adf_differencing": {"enabled": False},
}


def _load_kline(symbol: str, timeframe: str, *, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    """從真實 HDF5 cache 讀單一 symbol/timeframe。"""
    key = f"{symbol}/{timeframe}/data"
    with h5py.File(KLINE_CACHE, "r") as h5_file:
        if key not in h5_file:
            raise KeyError(f"missing dataset: {key}")
        records = h5_file[key][()]

    frame = pd.DataFrame.from_records(records).tail(max_rows).copy()
    unit = "ms" if int(frame["timestamp"].max()) > 10**12 else "s"
    frame.index = pd.to_datetime(frame["timestamp"], unit=unit, utc=True)
    frame = frame.drop(columns=["timestamp"])
    if not frame.index.is_monotonic_increasing:
        raise AssertionError(f"{symbol}/{timeframe} timestamp not monotonic")
    return frame


def _available_symbols() -> List[str]:
    """列出同時具備 1h/4h/12h 的真實 symbol。"""
    with h5py.File(KLINE_CACHE, "r") as h5_file:
        symbols = sorted(h5_file.keys())
        return [
            symbol
            for symbol in symbols
            if all(f"{symbol}/{timeframe}/data" in h5_file for timeframe in TIMEFRAMES)
        ]


def _feature_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """由真實 OHLCV 生成固定 schema 的 L1/L2 檢查特徵。"""
    close = raw["close"].astype(float)
    high = raw["high"].astype(float)
    low = raw["low"].astype(float)
    volume = raw["volume"].astype(float)
    quote_volume = raw["quote_volume"].astype(float)
    taker = raw["taker_buy_volume"].astype(float)
    trades = raw["number_of_trades"].astype(float)

    features = pd.DataFrame(
        {
            "L1_open": raw["open"].astype(float),
            "L1_high": high,
            "L1_low": low,
            "L1_close": close,
            "L1_volume": volume,
            "L1_quote_volume": quote_volume,
            "L1_taker_ratio": raw["taker_ratio"].astype(float),
            "L1_trades": trades,
            "L2_close_ret_1": close.pct_change(),
            "L2_log_close": np.log(close.replace(0.0, np.nan).abs()),
            "L2_hl_spread": (high - low) / close.replace(0.0, np.nan),
            "L2_volume_ret_1": volume.pct_change(),
            "L2_taker_share": taker / volume.replace(0.0, np.nan),
            "L2_quote_per_trade": quote_volume / trades.replace(0.0, np.nan),
        },
        index=raw.index,
    )
    return features.replace([np.inf, -np.inf], np.nan).astype(np.float32)


def _preprocess(features: pd.DataFrame, *, causal: bool = True) -> pd.DataFrame:
    """執行 L6.5，呼叫端可傳 False 驗證釘死。"""
    config = json.loads(json.dumps(L65_CONFIG))
    config["causal_preprocessing"] = causal
    return FeaturePreprocessor(config).transform(features)


def _arrays_equal(left: pd.DataFrame, right: pd.DataFrame, *, atol: float = 1e-9) -> bool:
    if list(left.columns) != list(right.columns) or len(left) != len(right):
        return False
    return bool(
        np.allclose(
            left.to_numpy(dtype=np.float64),
            right.to_numpy(dtype=np.float64),
            atol=atol,
            rtol=0.0,
            equal_nan=True,
        )
    )


def _finite_summary(frame: pd.DataFrame) -> Dict[str, int]:
    values = frame.to_numpy(dtype=np.float64)
    return {
        "cells": int(values.size),
        "nan": int(np.isnan(values).sum()),
        "pos_inf": int(np.isposinf(values).sum()),
        "neg_inf": int(np.isneginf(values).sum()),
    }


def _tail_tamper(raw: pd.DataFrame) -> pd.DataFrame:
    """只竄改尾端未來 bar，保留 index/schema。"""
    tampered = raw.copy()
    numeric_columns = [column for column in tampered.columns if column != "number_of_trades"]
    tampered.loc[tampered.index[-PIT_TAMPER_BARS:], numeric_columns] = (
        tampered.loc[tampered.index[-PIT_TAMPER_BARS:], numeric_columns] * 7.0 + 1_000_000.0
    )
    tampered.loc[tampered.index[-PIT_TAMPER_BARS:], "number_of_trades"] = (
        tampered.loc[tampered.index[-PIT_TAMPER_BARS:], "number_of_trades"] + 100_000
    )
    return tampered


def _check_causal_for_dataset(raw: pd.DataFrame) -> Dict[str, Any]:
    """檢查 False 強制 True 與未來竄改不影響過去。"""
    features = _feature_frame(raw)
    forced = _preprocess(features, causal=False)
    causal = _preprocess(features, causal=True)
    forced_eq_true = _arrays_equal(forced, causal)

    tampered_features = _feature_frame(_tail_tamper(raw))
    tampered = _preprocess(tampered_features, causal=True)
    cutoff = max(0, len(causal) - PIT_GUARD_BARS)
    pit_ok = _arrays_equal(causal.iloc[:cutoff], tampered.iloc[:cutoff])
    max_abs_diff = 0.0
    if cutoff:
        diff = np.nan_to_num(
            causal.iloc[:cutoff].to_numpy(np.float64)
            - tampered.iloc[:cutoff].to_numpy(np.float64),
            nan=0.0,
        )
        max_abs_diff = float(np.max(np.abs(diff))) if diff.size else 0.0
    return {
        "rows": int(len(raw)),
        "cols": int(features.shape[1]),
        "forced_false_equals_true": bool(forced_eq_true),
        "future_tamper_past_unchanged": bool(pit_ok),
        "past_rows_checked": int(cutoff),
        "past_max_abs_diff": max_abs_diff,
    }


def _native_processed_by_tf(symbol: str) -> Dict[str, pd.DataFrame]:
    return {
        timeframe: _preprocess(_feature_frame(_load_kline(symbol, timeframe)), causal=True)
        for timeframe in TIMEFRAMES
    }


def _merge_to_primary(native: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """將 native TF L6.5 輸出 PIT ffill 到 1h primary index。"""
    primary_index = native["1h"].index
    parts = [native["1h"].add_prefix("tf1h__")]
    for timeframe in ("4h", "12h"):
        aligned = native[timeframe].reindex(primary_index, method="ffill")
        parts.append(aligned.add_prefix(f"tf{timeframe}__"))
    return pd.concat(parts, axis=1)


def _check_merge_value_conservation(native: Mapping[str, pd.DataFrame]) -> Dict[str, Any]:
    """merge 後每個 lower-TF 值必須等於當下可見的最後一筆 native 值。"""
    merged = _merge_to_primary(native)
    primary_index = native["1h"].index
    checked = 0
    mismatches = 0
    for timeframe in ("4h", "12h"):
        source = native[timeframe]
        columns = list(source.columns[:5])
        for ts in primary_index[::37]:
            visible = source.loc[source.index <= ts]
            if visible.empty:
                continue
            expected = visible.iloc[-1]
            for column in columns:
                actual = merged.loc[ts, f"tf{timeframe}__{column}"]
                exp_value = expected[column]
                both_nan = pd.isna(actual) and pd.isna(exp_value)
                equal = both_nan or math.isclose(
                    float(actual), float(exp_value), rel_tol=0.0, abs_tol=1e-9
                )
                checked += 1
                if not equal:
                    mismatches += 1
    return {
        "comparisons": checked,
        "mismatches": mismatches,
        "passed": bool(checked > 0 and mismatches == 0),
    }


def _check_split_no_leakage(symbol: str) -> Dict[str, Any]:
    """竄改 split 邊界後資料時，train 區間 merged output 不得變。"""
    raw_by_tf = {timeframe: _load_kline(symbol, timeframe) for timeframe in TIMEFRAMES}
    native = {
        timeframe: _preprocess(_feature_frame(raw), causal=True)
        for timeframe, raw in raw_by_tf.items()
    }
    merged = _merge_to_primary(native)
    boundary = int(len(merged) * 0.8)
    boundary_ts = merged.index[boundary]

    tampered_raw_by_tf: Dict[str, pd.DataFrame] = {}
    for timeframe, raw in raw_by_tf.items():
        tampered = raw.copy()
        future_mask = tampered.index >= boundary_ts
        numeric_columns = [column for column in tampered.columns if column != "number_of_trades"]
        tampered.loc[future_mask, numeric_columns] = (
            tampered.loc[future_mask, numeric_columns] * 5.0 + 500_000.0
        )
        tampered.loc[future_mask, "number_of_trades"] = (
            tampered.loc[future_mask, "number_of_trades"] + 50_000
        )
        tampered_raw_by_tf[timeframe] = tampered

    tampered_native = {
        timeframe: _preprocess(_feature_frame(raw), causal=True)
        for timeframe, raw in tampered_raw_by_tf.items()
    }
    tampered_merged = _merge_to_primary(tampered_native)
    train_original = merged.iloc[:boundary]
    train_tampered = tampered_merged.iloc[:boundary]
    passed = _arrays_equal(train_original, train_tampered)
    return {
        "symbol": symbol,
        "train_rows_checked": int(len(train_original)),
        "columns_checked": int(train_original.shape[1]),
        "passed": bool(passed),
    }


def _check_nan_inf_gate(symbol: str) -> Dict[str, Any]:
    """用真實資料的污染副本確認 NaN 保留且 Inf 不穿透。"""
    features = _feature_frame(_load_kline(symbol, "1h"))
    probe = features.copy()
    nan_locs = [(probe.index[i], probe.columns[0]) for i in range(10, 15)]
    pos_inf_locs = [(probe.index[i], probe.columns[1]) for i in range(20, 25)]
    neg_inf_locs = [(probe.index[i], probe.columns[2]) for i in range(30, 35)]
    for row, column in nan_locs:
        probe.loc[row, column] = np.nan
    for row, column in pos_inf_locs:
        probe.loc[row, column] = np.inf
    for row, column in neg_inf_locs:
        probe.loc[row, column] = -np.inf

    output = _preprocess(probe, causal=True)
    summary = _finite_summary(output)
    injected_nan_preserved = all(pd.isna(output.loc[row, column]) for row, column in nan_locs)
    injected_inf_values = [
        output.loc[row, column] for row, column in [*pos_inf_locs, *neg_inf_locs]
    ]
    injected_inf_not_infinite = all(
        not np.isinf(float(value)) if pd.notna(value) else True
        for value in injected_inf_values
    )
    injected_inf_output_nan = sum(1 for value in injected_inf_values if pd.isna(value))
    injected_inf_output_finite = sum(
        1 for value in injected_inf_values if pd.notna(value) and np.isfinite(float(value))
    )
    return {
        "symbol": symbol,
        "output": summary,
        "injected_nan_preserved": bool(injected_nan_preserved),
        "injected_inf_not_infinite": bool(injected_inf_not_infinite),
        "injected_inf_output_nan": int(injected_inf_output_nan),
        "injected_inf_output_finite": int(injected_inf_output_finite),
        "passed": bool(
            summary["pos_inf"] == 0
            and summary["neg_inf"] == 0
            and injected_nan_preserved
            and injected_inf_not_infinite
        ),
    }


def _check_shared_instance_isolation(symbols: Iterable[str]) -> Dict[str, Any]:
    """同一 FeaturePreprocessor 連續處理不同 symbol 不得污染結果。"""
    symbol_list = list(symbols)
    first, second = symbol_list[0], symbol_list[1]
    first_frame = _feature_frame(_load_kline(first, "1h"))
    second_frame = _feature_frame(_load_kline(second, "1h"))

    shared = FeaturePreprocessor(json.loads(json.dumps(L65_CONFIG)))
    _ = shared.transform(first_frame)
    second_after_first = shared.transform(second_frame)
    second_clean = _preprocess(second_frame, causal=True)
    return {
        "sequence": [first, second],
        "passed": bool(_arrays_equal(second_after_first, second_clean)),
        "rows_checked": int(len(second_clean)),
        "columns_checked": int(second_clean.shape[1]),
    }


def run_signoff() -> Dict[str, Any]:
    if not KLINE_CACHE.exists():
        raise FileNotFoundError(KLINE_CACHE)

    symbols = _available_symbols()
    if len(symbols) != 10:
        raise AssertionError(f"expected 10 complete symbols, got {len(symbols)}: {symbols}")

    causal_results: Dict[str, Dict[str, Dict[str, Any]]] = {}
    schema_by_dataset: Dict[str, List[str]] = {}
    dtype_by_dataset: Dict[str, Dict[str, str]] = {}
    finite_by_dataset: Dict[str, Dict[str, int]] = {}
    for symbol in symbols:
        causal_results[symbol] = {}
        for timeframe in TIMEFRAMES:
            raw = _load_kline(symbol, timeframe)
            causal_results[symbol][timeframe] = _check_causal_for_dataset(raw)
            output = _preprocess(_feature_frame(raw), causal=True)
            dataset = f"{symbol}/{timeframe}"
            schema_by_dataset[dataset] = [str(column) for column in output.columns]
            dtype_by_dataset[dataset] = {
                str(column): str(output[column].dtype) for column in output.columns
            }
            finite_by_dataset[dataset] = _finite_summary(output)

    reference_schema = next(iter(schema_by_dataset.values()))
    schema_consistent = all(columns == reference_schema for columns in schema_by_dataset.values())
    reference_dtypes = next(iter(dtype_by_dataset.values()))
    dtype_consistent = all(dtypes == reference_dtypes for dtypes in dtype_by_dataset.values())
    no_output_inf = all(
        summary["pos_inf"] == 0 and summary["neg_inf"] == 0
        for summary in finite_by_dataset.values()
    )

    native_by_symbol = {symbol: _native_processed_by_tf(symbol) for symbol in symbols}
    merge_checks = {
        symbol: _check_merge_value_conservation(native)
        for symbol, native in native_by_symbol.items()
    }
    merged_schemas = {
        symbol: [str(column) for column in _merge_to_primary(native).columns]
        for symbol, native in native_by_symbol.items()
    }
    merged_schema_reference = next(iter(merged_schemas.values()))
    merged_schema_consistent = all(
        columns == merged_schema_reference for columns in merged_schemas.values()
    )
    split_checks = {symbol: _check_split_no_leakage(symbol) for symbol in symbols}
    gate_check = _check_nan_inf_gate(symbols[0])
    shared_check = _check_shared_instance_isolation(symbols)

    causal_pass = all(
        result["forced_false_equals_true"] and result["future_tamper_past_unchanged"]
        for by_tf in causal_results.values()
        for result in by_tf.values()
    )
    merge_pass = all(result["passed"] for result in merge_checks.values())
    split_pass = all(result["passed"] for result in split_checks.values())
    overall = all(
        (
            causal_pass,
            schema_consistent,
            dtype_consistent,
            no_output_inf,
            merged_schema_consistent,
            merge_pass,
            split_pass,
            gate_check["passed"],
            shared_check["passed"],
        )
    )

    return {
        "kline_cache": str(KLINE_CACHE.relative_to(PROJECT_ROOT)),
        "symbols": symbols,
        "timeframes": list(TIMEFRAMES),
        "datasets_checked": len(symbols) * len(TIMEFRAMES),
        "rows_per_dataset": {
            f"{symbol}/{timeframe}": causal_results[symbol][timeframe]["rows"]
            for symbol in symbols
            for timeframe in TIMEFRAMES
        },
        "feature_columns_per_dataset": len(reference_schema),
        "causal_pit": {
            "passed": causal_pass,
            "datasets_checked": len(symbols) * len(TIMEFRAMES),
            "tamper_tail_bars": PIT_TAMPER_BARS,
            "guard_bars": PIT_GUARD_BARS,
            "details": causal_results,
        },
        "schema_isolation": {
            "schema_consistent": schema_consistent,
            "dtype_consistent": dtype_consistent,
            "no_output_inf": no_output_inf,
            "datasets_checked": len(schema_by_dataset),
            "output_finite_summary": finite_by_dataset,
        },
        "multi_tf_merge": {
            "passed": merge_pass and merged_schema_consistent,
            "merged_schema_consistent": merged_schema_consistent,
            "checks": merge_checks,
        },
        "split_no_leakage": {
            "passed": split_pass,
            "checks": split_checks,
        },
        "nan_inf_gate": gate_check,
        "cross_symbol_state_isolation": shared_check,
        "overall_passed": overall,
        "signoff": "資料正確" if overall else "有疑慮",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Codex L6.5 B3b data correctness signoff")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=PROJECT_ROOT / "results" / "l65_b3b_codex_signoff.json",
    )
    args = parser.parse_args()

    result = run_signoff()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if not result["overall_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
