"""Verification script for the NaN poisoning fix (Step 5 of NAN_POISONING_INVESTIGATION.md).

Runs an isolated L1-pattern + L1-trend → L2 derived → L3 rolling → L6.5 preprocess
pipeline on real BTCUSDT 1h kline data and asserts that:

  * No `ohlc_pattern_*` columns leak into L2 derived outputs (Momentum / Distance /
    SignedStrength / WorldQuant).
  * No `ohlc_pattern_*` columns leak into L3 rolling-aggregation outputs.
  * L6.5 entry-level guard drops manually-injected pattern columns
    (belt-and-suspenders verification).
  * Non-pattern columns (trend SMA) are NOT collateral-damaged by the guards.
  * `_variance_filter` drops effective_n < 30 even when nan_rate <= 0.9.
  * `RATIO_UNSAFE_CATEGORIES` is the same frozenset across all three modules.

Run with: PYTHONPATH="$PWD" venv/bin/python scripts/verify_nan_poisoning_fix.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from momentum.FeatureEngineering.atomic.pattern_indicators import PatternIndicatorEngine
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.operators.derived_operators import (
    RATIO_UNSAFE_CATEGORIES,
    DerivedOperatorEngine,
)
from momentum.FeatureEngineering.operators.rolling_aggregator import (
    RATIO_UNSAFE_CATEGORIES as RAG_UNSAFE,
    RollingAggregator,
    _is_ratio_unsafe_column,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
    RATIO_UNSAFE_CATEGORIES as PP_UNSAFE,
    FeaturePreprocessor,
    _is_ratio_unsafe_column as pp_is_unsafe,
)

KLINE_PATH = Path("data_cache/feature_klines/kline_cache.h5")
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
ROWS = 4000  # ~5.5 months of 1h bars; enough for L3 window=720 to produce real stats.


def _load_raw() -> pd.DataFrame:
    with h5py.File(KLINE_PATH, "r") as f:
        ds = f[f"{SYMBOL}/{TIMEFRAME}/data"][:]
    df = pd.DataFrame(ds)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df = df.set_index("timestamp").tail(ROWS).astype({c: "float64" for c in df.columns if c != "timestamp"})
    return df


def _check(label: str, cond: bool, detail: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    line = f"  [{mark}] {label}" + (f" — {detail}" if detail else "")
    print(line)
    if not cond:
        raise SystemExit(1)


def main() -> int:
    print("=" * 80)
    print("NaN Poisoning Fix — Verification (Step 5)")
    print("=" * 80)

    # ------------------------------------------------------------------ B1-B5
    print("\n[1/6] Unit-level: _is_ratio_unsafe_column boundary cases")
    _check("B1 pattern L1", _is_ratio_unsafe_column("ohlc_pattern_CDLDOJI"))
    _check("B2 trend L1 (no false positive)", not _is_ratio_unsafe_column("close_trend_SMA_20"))
    _check("B3 pattern L2 derived", _is_ratio_unsafe_column("ohlc_pattern_CDLDOJI_Momentum_L5"))
    _check("B4 single-word col", not _is_ratio_unsafe_column("singleword"))
    _check("B5 L3-prefixed trend", not _is_ratio_unsafe_column("L3_close_trend_SMA_20_mean_w20"))
    _check("B5b preprocessor guard parity",
           pp_is_unsafe("ohlc_pattern_CDLDOJI") and not pp_is_unsafe("close_trend_SMA_20"))

    # --------------------------------------------------------------------- B8
    print("\n[2/6] Constant parity across modules")
    _check("RATIO_UNSAFE_CATEGORIES identical",
           RATIO_UNSAFE_CATEGORIES == RAG_UNSAFE == PP_UNSAFE,
           f"all three == {sorted(RATIO_UNSAFE_CATEGORIES)}")

    # ----------------------------------------------------------------- B6, B7
    print("\n[3/6] _variance_filter effective_n condition")
    n = 200
    df = pd.DataFrame({
        "all_good": np.random.randn(n),                            # keep
        "low_n": [np.nan] * 180 + list(np.random.randn(20)),       # drop: eff_n=20
        "borderline_nan": [np.nan] * 100 + list(np.random.randn(100)),  # keep: eff_n=100
        "constant": [1.0] * n,                                     # drop
        "with_inf": [np.inf] + list(np.random.randn(n - 1)),       # drop
    })
    filtered = RollingAggregator._variance_filter(df, nan_threshold=0.9)
    _check("B6 low effective_n dropped", "low_n" not in filtered.columns)
    _check("B7 borderline kept", "borderline_nan" in filtered.columns)
    _check("constant dropped", "constant" not in filtered.columns)
    _check("inf dropped", "with_inf" not in filtered.columns)
    _check("good kept", "all_good" in filtered.columns)

    # ------------------------------------------------------------------ Real
    print(f"\n[4/6] Real pipeline on {SYMBOL} {TIMEFRAME} ({ROWS} bars)")
    raw = _load_raw()
    print(f"  loaded raw: {raw.shape}, cols={list(raw.columns)}")

    # Build a mixed L1: real patterns (60+ CDL cols) + a couple of trend SMAs.
    pattern_engine = PatternIndicatorEngine(config={}, data_sources=["ohlc"])
    layer1_pattern = pattern_engine.compute_all(raw)

    sma_frames = []
    for tp in (10, 20):
        sma_frames.append(TALibWrapper.compute_batch("SMA", raw, [{"timeperiod": tp}], ["close"]))
    layer1_trend = pd.concat(sma_frames, axis=1)

    layer1 = pd.concat([layer1_pattern, layer1_trend], axis=1)
    pattern_cols = [c for c in layer1.columns if "_pattern_" in c]
    trend_cols = [c for c in layer1.columns if "_trend_" in c]
    print(f"  L1 built: {layer1.shape[1]} cols ({len(pattern_cols)} pattern + {len(trend_cols)} trend)")
    _check("L1 contains pattern cols (sanity)", len(pattern_cols) >= 30)
    _check("L1 contains trend cols (sanity)", len(trend_cols) >= 2)

    # ------------------------------------------------------------------ L2
    op_engine = DerivedOperatorEngine(config={
        "momentum": {"enabled": True, "apply_to": "all", "lags": [1, 5, 10]},
        "distance": {"enabled": True, "apply_to": "all"},
        "signed_strength": {"enabled": True, "apply_to": "all"},
        "worldquant": {"enabled": True, "apply_to": "all", "windows": [5, 10]},
    })
    layer2 = op_engine.compute_all(layer1, raw)
    print(f"  L2 derived: {layer2.shape[1]} cols")
    l2_pattern_leaks = [c for c in layer2.columns if "_pattern_" in c]
    _check("L2 has NO pattern-derived leakage",
           not l2_pattern_leaks,
           f"found {len(l2_pattern_leaks)} leaks" if l2_pattern_leaks else "")
    l2_trend_derived = [c for c in layer2.columns if "_trend_" in c]
    _check("L2 still derives trend cols (no collateral damage)",
           len(l2_trend_derived) >= 4,
           f"got {len(l2_trend_derived)}")

    # ------------------------------------------------------------------ L3
    rolling = RollingAggregator(config={
        "windows": [20, 60],
        "aggregators": ["mean", "std", "rank"],
        "apply_to": "all",
        "min_periods_ratio": 0.5,
    })
    layer3 = rolling.compute_all(layer1)
    print(f"  L3 rolling: {layer3.shape[1]} cols")
    l3_pattern_leaks = [c for c in layer3.columns if "_pattern_" in c]
    _check("L3 has NO pattern rolling outputs",
           not l3_pattern_leaks,
           f"found {len(l3_pattern_leaks)} leaks" if l3_pattern_leaks else "")
    l3_trend = [c for c in layer3.columns if "_trend_" in c]
    _check("L3 still aggregates trend cols", len(l3_trend) >= 6, f"got {len(l3_trend)}")

    # ----------------------------------------------------------------- L6.5
    # Inject a fake pattern column to verify L6.5 belt-and-suspenders guard.
    print(f"\n[5/6] L6.5 belt-and-suspenders")
    injection = pd.DataFrame({
        "ohlc_pattern_CDLDOJI_Momentum_L5": np.random.randn(len(layer3)),
        "ohlc_pattern_BullishCount_W5_mean_w20": np.random.randn(len(layer3)),
    }, index=layer3.index)
    l65_input = pd.concat([layer3.iloc[:, :50], injection], axis=1)
    pre_cols = set(l65_input.columns)
    _check("injection visible at L6.5 input",
           "ohlc_pattern_CDLDOJI_Momentum_L5" in pre_cols)

    pp = FeaturePreprocessor(config={
        "rank_transform": {"enabled": True, "apply_to": "all"},
    })
    l65_out = pp.transform(l65_input)
    l65_leaks = [c for c in l65_out.columns if "_pattern_" in c]
    _check("L6.5 dropped injected pattern cols",
           not l65_leaks,
           f"leaks={l65_leaks}" if l65_leaks else "")

    # ------------------------------------------------------- Summary metrics
    print("\n[6/6] Quantitative summary")
    high_nan_l3 = (layer3.isna().mean() > 0.9).sum()
    print(f"  L3 cols with NaN rate > 0.9: {int(high_nan_l3)} / {layer3.shape[1]}")
    print(f"  L2 expected pattern derivatives if unguarded:")
    print(f"     {len(pattern_cols)} patterns × ~13 ops ≈ {len(pattern_cols) * 13} cols (now 0)")
    print(f"  L3 expected pattern aggregations if unguarded:")
    print(f"     {len(pattern_cols)} patterns × 2 windows × 3 aggs = {len(pattern_cols) * 6} cols (now 0)")

    print("\n" + "=" * 80)
    print("ALL CHECKS PASSED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
