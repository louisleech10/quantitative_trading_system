"""
verify_l1_warmup_requirements.py

Empirically determine the MINIMUM warmup bars required for each L1 atomic
indicator (TA-Lib) to converge to its "infinite history" value within a
configurable relative-error threshold (default 0.5%).

Method
------
1. Load ETHUSDT 1h klines (20,352 bars) from data_cache as approximate
   "infinite history" ground truth.
2. For each (indicator, period) under test:
     - Ground truth: indicator(full_series)[eval_start : eval_end]
     - Test(K)    : indicator(full_series[eval_start - K : eval_end])
                    aligned to the same absolute bars
   Find the smallest K such that
     max |test(K) - gt| / max(|gt|, eps)  <  THRESHOLD   over eval window.
3. Group results by indicator family; report per-indicator K and ratio K/period;
   write warmup_table.yaml consumed downstream by
   `_compute_warmup_buffer_bars()`.

Purpose
-------
The output is the SOURCE OF TRUTH for how many extra bars L0 needs to prepend
before the user-specified target window starts. It replaces the previous
blanket "3 x max_period x max_tf_ratio" heuristic.

Run
---
PYTHONPATH=. ./venv/bin/python scripts/verify_l1_warmup_requirements.py \
    [--threshold 0.005] [--eval-window 1000] [--output warmup_table.yaml]
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import h5py
import numpy as np
import pandas as pd
import talib
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KLINE_PATH = PROJECT_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
DEFAULT_SYMBOL = "ETHUSDT"
DEFAULT_TF = "1h"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "momentum" / "FeatureEngineering" / "atomic" / "warmup_table.yaml"
)

# Periods chosen to span small / medium / large segments of the fibonacci set
# used in scan_config.yaml ([5, 8, 13, 21, 34, 55, 89, 144, 233]).
TEST_PERIODS = [13, 55, 233]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_klines(symbol: str = DEFAULT_SYMBOL, tf: str = DEFAULT_TF) -> Dict[str, np.ndarray]:
    """Load klines as a dict of float64 arrays."""
    if not KLINE_PATH.exists():
        raise FileNotFoundError(f"Kline cache not found: {KLINE_PATH}")
    with h5py.File(KLINE_PATH, "r") as f:
        rec = f[f"{symbol}/{tf}/data"][:]
    return {
        "open": rec["open"].astype(np.float64),
        "high": rec["high"].astype(np.float64),
        "low": rec["low"].astype(np.float64),
        "close": rec["close"].astype(np.float64),
        "volume": rec["volume"].astype(np.float64),
    }


# ---------------------------------------------------------------------------
# Convergence search
# ---------------------------------------------------------------------------
@dataclass
class IndicatorTest:
    name: str
    family: str
    # fn(data_dict, period) -> ndarray  OR  tuple of ndarrays
    fn: Callable[[Dict[str, np.ndarray], int], object]
    # which output index to compare (for multi-output: 0=line, 1=signal, 2=hist)
    output_indices: Tuple[int, ...] = (0,)
    # override test periods (e.g. MACD uses single timeperiod = slow period)
    periods: Optional[List[int]] = None
    # if True, indicator output is boolean/integer (CDL_*); use absolute diff
    integer_output: bool = False
    note: str = ""


def scale_normalized_error(test: np.ndarray, gt: np.ndarray, integer: bool) -> float:
    """Max absolute deviation normalized by the indicator's *robust scale* over
    the evaluation window.

    Why not pointwise relative error: indicators that oscillate through zero
    (CMO, MACD, AROONOSC, TRIX, etc.) produce meaningless relative errors when
    the instantaneous value is near zero, even though the deviation is
    insignificant for ML purposes. Normalizing by the 75th-percentile of
    |gt| over the eval window measures error against the indicator's
    *typical magnitude*, which is what actually matters downstream.

      err = max|test - gt|  /  max( P75(|gt|),  std(gt),  floor )

    For price-magnitude indicators (EMA/SMA/MACD): P75(|gt|) ~ avg price level.
    For oscillators (RSI/ADX/CMO/...):  P75(|gt|) ~ typical oscillation amplitude.
    """
    mask = ~(np.isnan(gt) | np.isnan(test))
    if mask.sum() == 0:
        return np.inf
    if integer:
        # boolean / signed integer output - any mismatch counts
        return float((test[mask] != gt[mask]).any())
    gt_v = gt[mask]
    diff = np.abs(test[mask] - gt_v)
    max_abs_diff = float(diff.max())
    p75 = float(np.percentile(np.abs(gt_v), 75))
    std = float(np.std(gt_v))
    scale = max(p75, std, 1e-8)
    return max_abs_diff / scale


def find_min_warmup(
    test_spec: IndicatorTest,
    full_data: Dict[str, np.ndarray],
    period: int,
    eval_start: int,
    eval_end: int,
    threshold: float,
    max_K_cap: int,
) -> Tuple[int, float]:
    """Search smallest K such that result(data[eval_start-K : eval_end])
    matches result(full_data)[eval_start:eval_end] within threshold.

    Returns (K, achieved_max_rel_err). K = -1 if not converged within cap.
    """
    # Ground truth from full history
    gt_full = test_spec.fn(full_data, period)
    if isinstance(gt_full, tuple):
        gt_outputs = [gt_full[i] for i in test_spec.output_indices]
    else:
        gt_outputs = [gt_full]
    gt_slices = [g[eval_start:eval_end] for g in gt_outputs]

    # Search K values: dense near period, sparser further out
    K_values: List[int] = []
    K = max(period, 1)
    while K <= max_K_cap:
        K_values.append(K)
        # +1 step near small K, exponential growth further out
        next_K = max(K + 1, int(K * 1.10))
        K = next_K
    # Always include period * {1,2,3,5,8,12,16} explicitly for clean reporting
    for mult in (1, 2, 3, 5, 8, 12, 16, 20):
        K_values.append(period * mult)
    K_values = sorted(set(k for k in K_values if 1 <= k <= max_K_cap))

    best_err = np.inf
    for K in K_values:
        sub = {k: v[eval_start - K:eval_end] for k, v in full_data.items()}
        try:
            res = test_spec.fn(sub, period)
        except Exception as exc:  # noqa: BLE001
            # Some indicators (e.g. HT_*) reject short input; skip
            continue
        if isinstance(res, tuple):
            res_outputs = [res[i] for i in test_spec.output_indices]
        else:
            res_outputs = [res]
        # Align tail to evaluation window
        eval_len = eval_end - eval_start
        max_err_this_K = 0.0
        for out, gt_slice in zip(res_outputs, gt_slices):
            tail = out[-eval_len:]
            err = scale_normalized_error(tail, gt_slice, test_spec.integer_output)
            if err > max_err_this_K:
                max_err_this_K = err
        if max_err_this_K < best_err:
            best_err = max_err_this_K
        if max_err_this_K < threshold:
            return K, max_err_this_K

    return -1, best_err


# ---------------------------------------------------------------------------
# Indicator catalog
# ---------------------------------------------------------------------------
def build_indicator_tests() -> List[IndicatorTest]:
    """Return list of indicator tests, organized by family."""
    tests: List[IndicatorTest] = []

    # ----- Family: ema_seeded (TA-Lib uses SMA seed for first EMA value) -----
    tests += [
        IndicatorTest("EMA", "ema_seeded",
            lambda d, p: talib.EMA(d["close"], timeperiod=p)),
        IndicatorTest("SMA", "window_only",
            lambda d, p: talib.SMA(d["close"], timeperiod=p)),
        IndicatorTest("WMA", "window_only",
            lambda d, p: talib.WMA(d["close"], timeperiod=p)),
        IndicatorTest("DEMA", "compound_ema",
            lambda d, p: talib.DEMA(d["close"], timeperiod=p)),
        IndicatorTest("TEMA", "compound_ema",
            lambda d, p: talib.TEMA(d["close"], timeperiod=p)),
        IndicatorTest("TRIMA", "window_only",
            lambda d, p: talib.TRIMA(d["close"], timeperiod=p)),
        IndicatorTest("KAMA", "adaptive_ema",
            lambda d, p: talib.KAMA(d["close"], timeperiod=p)),
        IndicatorTest("T3", "compound_ema",
            lambda d, p: talib.T3(d["close"], timeperiod=p)),
        IndicatorTest("MIDPOINT", "window_only",
            lambda d, p: talib.MIDPOINT(d["close"], timeperiod=p)),
        IndicatorTest("MIDPRICE", "window_only",
            lambda d, p: talib.MIDPRICE(d["high"], d["low"], timeperiod=p)),
    ]

    # ----- Momentum -----
    tests += [
        IndicatorTest("RSI", "wilder",
            lambda d, p: talib.RSI(d["close"], timeperiod=p)),
        IndicatorTest("ADX", "wilder",
            lambda d, p: talib.ADX(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("ADXR", "wilder",
            lambda d, p: talib.ADXR(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("DX", "wilder",
            lambda d, p: talib.DX(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("PLUS_DI", "wilder",
            lambda d, p: talib.PLUS_DI(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("MINUS_DI", "wilder",
            lambda d, p: talib.MINUS_DI(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("PLUS_DM", "wilder",
            lambda d, p: talib.PLUS_DM(d["high"], d["low"], timeperiod=p)),
        IndicatorTest("MINUS_DM", "wilder",
            lambda d, p: talib.MINUS_DM(d["high"], d["low"], timeperiod=p)),
        IndicatorTest("CCI", "window_only",
            lambda d, p: talib.CCI(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("CMO", "wilder",
            lambda d, p: talib.CMO(d["close"], timeperiod=p)),
        IndicatorTest("MOM", "window_only",
            lambda d, p: talib.MOM(d["close"], timeperiod=p)),
        IndicatorTest("ROC", "window_only",
            lambda d, p: talib.ROC(d["close"], timeperiod=p)),
        IndicatorTest("AROON", "window_only",
            lambda d, p: talib.AROON(d["high"], d["low"], timeperiod=p),
            output_indices=(0, 1)),
        IndicatorTest("AROONOSC", "window_only",
            lambda d, p: talib.AROONOSC(d["high"], d["low"], timeperiod=p)),
        IndicatorTest("TRIX", "compound_ema",
            lambda d, p: talib.TRIX(d["close"], timeperiod=p)),
        IndicatorTest("WILLR", "window_only",
            lambda d, p: talib.WILLR(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("MFI", "wilder",
            lambda d, p: talib.MFI(d["high"], d["low"], d["close"], d["volume"], timeperiod=p)),
    ]

    # ----- Volatility -----
    tests += [
        IndicatorTest("ATR", "wilder",
            lambda d, p: talib.ATR(d["high"], d["low"], d["close"], timeperiod=p)),
        IndicatorTest("NATR", "wilder",
            lambda d, p: talib.NATR(d["high"], d["low"], d["close"], timeperiod=p)),
    ]

    # ----- MACD family (compound EMA: fast=12, slow=26, signal=9 default) -----
    # We parameterize as period = slow (the longest EMA inside), and compare line.
    tests += [
        IndicatorTest("MACD_line", "compound_ema",
            lambda d, p: talib.MACD(d["close"], fastperiod=max(1, p//2),
                                    slowperiod=p, signalperiod=max(1, p//3))[0]),
        IndicatorTest("MACD_signal", "compound_ema",
            lambda d, p: talib.MACD(d["close"], fastperiod=max(1, p//2),
                                    slowperiod=p, signalperiod=max(1, p//3))[1]),
        IndicatorTest("APO", "compound_ema",
            lambda d, p: talib.APO(d["close"], fastperiod=max(1, p//2),
                                   slowperiod=p)),
        IndicatorTest("PPO", "compound_ema",
            lambda d, p: talib.PPO(d["close"], fastperiod=max(1, p//2),
                                   slowperiod=p)),
    ]

    # ----- HT_* / cycle (TA-Lib enforces internal ~63 bar lookback) -----
    # period parameter not used (forced 63), but we still parameterize by p
    # to record min K. Use a single representative period.
    tests += [
        IndicatorTest("HT_TRENDLINE", "hilbert",
            lambda d, p: talib.HT_TRENDLINE(d["close"]),
            periods=[63]),
        IndicatorTest("HT_DCPERIOD", "hilbert",
            lambda d, p: talib.HT_DCPERIOD(d["close"]),
            periods=[63]),
        IndicatorTest("HT_DCPHASE", "hilbert",
            lambda d, p: talib.HT_DCPHASE(d["close"]),
            periods=[63]),
        IndicatorTest("HT_TRENDMODE", "hilbert",
            lambda d, p: talib.HT_TRENDMODE(d["close"]),
            periods=[63], integer_output=True),
    ]

    # ----- SAR / SAREXT (stateful from initial trend guess) -----
    tests += [
        IndicatorTest("SAR", "stateful_pivot",
            lambda d, p: talib.SAR(d["high"], d["low"], acceleration=0.02, maximum=0.2),
            periods=[1]),
    ]

    # ----- ULTOSC (uses multiple periods: short=7, medium=14, long=28 default) -----
    tests += [
        IndicatorTest("ULTOSC", "wilder",
            lambda d, p: talib.ULTOSC(d["high"], d["low"], d["close"],
                                      timeperiod1=max(1, p//4),
                                      timeperiod2=max(1, p//2),
                                      timeperiod3=p)),
    ]

    # ----- Cumulative (no convergence; included for completeness logging) -----
    # OBV / AD / ADOSC behavior:
    #   OBV, AD: pure cumulative sums -- can never match across different start
    #            points (constant offset). We mark them family=cumulative,
    #            no warmup measurement.
    #   ADOSC: EMA of AD -> converges in differences but base level is offset.
    #          We measure first-difference convergence below.
    # Skipped from numeric search; written into YAML as special-case.

    return tests


# Indicators marked cumulative (handled specially in YAML output)
CUMULATIVE_INDICATORS = {
    "OBV": {
        "family": "cumulative",
        "strategy": "burn_in_from_dataset_start",
        "note": "Cumulative sum; only relative changes are meaningful; "
                "differs from Binance by a constant offset unless started at listing.",
    },
    "AD": {
        "family": "cumulative",
        "strategy": "burn_in_from_dataset_start",
        "note": "Same as OBV: pure accumulator; absolute level not comparable.",
    },
    "ADOSC": {
        "family": "cumulative_diff_ema",
        "strategy": "burn_in_from_dataset_start_plus_5x_slow",
        "note": "EMA(fast) - EMA(slow) of AD; level differs but oscillator "
                "converges once both EMAs settle (~5x slow period).",
    },
    "VWAP": {
        "family": "cumulative",
        "strategy": "session_reset_or_burn_in_from_dataset_start",
        "note": "Binance UI uses session resets (daily/weekly); for ML use "
                "consistent reset rule across train/test/live.",
    },
}

# Pattern indicators (CDL_*): all use 1-5 bar lookback, integer output.
# Listed for completeness; warmup = 5 bars (max CDL lookback).
PATTERN_INDICATORS_DEFAULT_WARMUP = 5


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.005,
                    help="Scale-normalized error tolerance "
                         "(default 0.005 = max|err| < 0.5%% of robust scale)")
    ap.add_argument("--eval-window", type=int, default=1000,
                    help="# of bars used for ground-truth vs test comparison")
    ap.add_argument("--max-K-cap", type=int, default=4000,
                    help="Upper bound on warmup K to search")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                    help="Output YAML path")
    ap.add_argument("--periods", type=int, nargs="+", default=TEST_PERIODS,
                    help="Periods to test per indicator (default 13 55 233)")
    ap.add_argument("--symbol", type=str, default=DEFAULT_SYMBOL,
                    help="Symbol to verify (default ETHUSDT)")
    ap.add_argument("--symbols", type=str, nargs="+", default=None,
                    help="Multiple symbols to consolidate (takes max ratio across symbols). "
                         "Overrides --symbol when set.")
    ap.add_argument("--tf", type=str, default=DEFAULT_TF,
                    help="Timeframe (default 1h)")
    ap.add_argument("--no-write", action="store_true",
                    help="Do not write YAML; print summary only (for cross-symbol verification)")
    ap.add_argument("--eval-start-offset", type=int, default=0,
                    help="Shift eval window earlier by N bars (for window-position sensitivity check)")
    args = ap.parse_args()

    symbols_to_run = args.symbols if args.symbols else [args.symbol]
    consolidated_indicator_data: Dict[str, Dict] = {}
    last_N = 0
    last_results: List[Dict] = []

    for sym_idx, sym in enumerate(symbols_to_run, 1):
        print(f"\n========== Symbol {sym_idx}/{len(symbols_to_run)}: {sym} ==========")
        sym_indicator_data = _run_single_symbol(sym, args)
        # Merge max ratio per indicator across symbols
        for ind, entry in sym_indicator_data.items():
            if ind not in consolidated_indicator_data:
                consolidated_indicator_data[ind] = {
                    "family": entry["family"],
                    "max_ratio": 0.0,
                    "max_K": 0,
                    "per_symbol_ratio": {},
                    "all_converged": True,
                }
            cur = consolidated_indicator_data[ind]
            cur["per_symbol_ratio"][sym] = entry["max_ratio"]
            if entry["max_ratio"] > cur["max_ratio"]:
                cur["max_ratio"] = entry["max_ratio"]
            if entry["max_K"] > cur["max_K"]:
                cur["max_K"] = entry["max_K"]
            if not entry["all_converged"]:
                cur["all_converged"] = False

    # Build YAML structure (consolidated max across symbols)
    out = {
        "_meta": {
            "generated_by": "scripts/verify_l1_warmup_requirements.py",
            "data_source": f"symbols={symbols_to_run} tf={args.tf}",
            "scale_normalized_error_threshold": args.threshold,
            "eval_window_bars": args.eval_window,
            "test_periods": args.periods,
            "consolidation": "max ratio across symbols (worst case)",
            "principle": (
                "Minimum warmup K (in bars at the indicator's native TF) such "
                "that max|test - infinite_history_gt| over the eval window is "
                "less than THRESHOLD * robust_scale(gt), where "
                "robust_scale = max(P75(|gt|), std(gt))."
            ),
            "usage": (
                "warmup_bars(indicator, period) = ceil(period * recommended_factor); "
                "see momentum/Analysis/warmup_lookup.py"
            ),
        },
        "indicators": {},
        "cumulative_special_cases": CUMULATIVE_INDICATORS,
        "pattern_default_warmup_bars": PATTERN_INDICATORS_DEFAULT_WARMUP,
    }
    for ind, entry in sorted(consolidated_indicator_data.items()):
        out["indicators"][ind] = {
            "family": entry["family"],
            # Round UP to 2 decimals to be conservative
            "recommended_factor": float(np.ceil(max(1.0, entry["max_ratio"]) * 100) / 100),
            "max_K_observed": entry["max_K"],
            "all_periods_converged": entry["all_converged"],
            "per_symbol_max_ratio": {
                s: round(r, 3) for s, r in entry["per_symbol_ratio"].items()
            },
        }

    if not args.no_write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            yaml.safe_dump(out, f, sort_keys=False, default_flow_style=False)
        print(f"\n[FINAL] Wrote consolidated warmup table -> {args.output}")
    else:
        print(f"\n[FINAL] --no-write set; YAML not written.")

    # Final summary
    print("\n=== CONSOLIDATED SUMMARY (max factor across symbols) ===")
    print(f"{'INDICATOR':<14s} {'FAMILY':<18s} {'FACTOR':>7s} {'MAX_K':>7s} {'PER_SYMBOL':>40s}")
    for ind, entry in sorted(consolidated_indicator_data.items(),
                             key=lambda kv: (kv[1]["family"], -kv[1]["max_ratio"])):
        per_sym = ",".join(f"{s}={r:.2f}" for s, r in entry["per_symbol_ratio"].items())
        factor = float(np.ceil(max(1.0, entry["max_ratio"]) * 100) / 100)
        print(f"{ind:<14s} {entry['family']:<18s} "
              f"{factor:>7.2f} {entry['max_K']:>7d} {per_sym:>40s}")
    return 0


def _run_single_symbol(sym: str, args) -> Dict[str, Dict]:
    """Run the warmup search for one symbol and return by_indicator dict."""
    print(f"[1/3] Loading klines: {sym} {args.tf}")
    data = load_klines(sym, args.tf)
    N = len(data["close"])
    print(f"      Loaded {N} bars.")
    if N < 10000:
        print(f"      WARNING: only {N} bars available; large periods may not "
              f"have enough ground-truth burn-in.")

    # Evaluation window: last EVAL_WINDOW bars (optionally shifted earlier);
    # ground truth = indicator(full_series)[eval_start:eval_end]
    eval_end = N - args.eval_start_offset
    eval_start = eval_end - args.eval_window
    print(f"      Eval window: bars [{eval_start} : {eval_end}]  "
          f"(threshold = {args.threshold*100:.2f}% scale-normalized error)")

    tests = build_indicator_tests()
    print(f"[2/4] Indicators to test: {len(tests)}; "
          f"periods per indicator: {args.periods}")

    results: List[Dict] = []
    t0 = time.time()
    for i, spec in enumerate(tests, 1):
        periods = spec.periods if spec.periods else args.periods
        for period in periods:
            # Need eval_start - K >= 0; ensure max_K_cap respects this
            max_K = min(args.max_K_cap, eval_start - 1)
            K, err = find_min_warmup(
                spec, data, period,
                eval_start=eval_start, eval_end=eval_end,
                threshold=args.threshold, max_K_cap=max_K,
            )
            ratio = (K / period) if (K > 0 and period > 0) else None
            status = "OK" if K > 0 else "NOT_CONVERGED"
            results.append({
                "indicator": spec.name,
                "family": spec.family,
                "period": period,
                "min_warmup_bars": int(K) if K > 0 else None,
                "ratio_K_over_period": round(ratio, 3) if ratio else None,
                "achieved_max_rel_err": float(err) if np.isfinite(err) else None,
                "status": status,
            })
            print(f"      [{i:3d}/{len(tests)}] {spec.name:<14s} "
                  f"period={period:>4d}  K={K if K > 0 else 'X':>5}  "
                  f"ratio={ratio if ratio else '-':<6}  "
                  f"err={err:.4e}  {status}")

    elapsed = time.time() - t0
    print(f"[3/3] Search finished in {elapsed:.1f}s for {sym}")

    # Per-indicator: take max ratio across tested periods (worst case within this symbol)
    by_indicator: Dict[str, Dict] = {}
    for r in results:
        ind = r["indicator"]
        if ind not in by_indicator:
            by_indicator[ind] = {
                "family": r["family"],
                "max_ratio": 0.0,
                "max_K": 0,
                "all_converged": True,
            }
        entry = by_indicator[ind]
        if r["status"] != "OK":
            entry["all_converged"] = False
        if r["ratio_K_over_period"] is not None:
            if r["ratio_K_over_period"] > entry["max_ratio"]:
                entry["max_ratio"] = r["ratio_K_over_period"]
            if r["min_warmup_bars"] and r["min_warmup_bars"] > entry["max_K"]:
                entry["max_K"] = r["min_warmup_bars"]

    # Per-symbol summary
    print(f"\n--- {sym} summary ---")
    print(f"{'INDICATOR':<14s} {'FAMILY':<18s} {'FACTOR':>7s} {'MAX_K':>7s} {'CONVERGED':>10s}")
    for ind, entry in sorted(by_indicator.items(),
                             key=lambda kv: (kv[1]["family"], -kv[1]["max_ratio"])):
        print(f"{ind:<14s} {entry['family']:<18s} "
              f"{entry['max_ratio']:>7.2f} {entry['max_K']:>7d} "
              f"{'YES' if entry['all_converged'] else 'NO':>10s}")
    return by_indicator


if __name__ == "__main__":
    sys.exit(main())
