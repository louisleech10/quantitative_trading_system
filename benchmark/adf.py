"""Micro benchmark for the L6.5 Fast ADF implementation."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from statsmodels.tsa.adfvalues import mackinnonp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.FeatureEngineering.preprocessing._fast_adf_numba import (  # noqa: E402
    adf_pvalue_fast,
    warmup_numba,
)

FAST_ADF_MEAN_LIMIT_MS = 5.0
FAST_ADF_P99_LIMIT_MS = 15.0
MACKINNON_MEAN_LIMIT_MS = 1.0
MACKINNON_P99_LIMIT_MS = 2.0


def _stationary_sample(row_count: int = 500) -> np.ndarray:
    rng = np.random.default_rng(20260428)
    noise = rng.normal(0.0, 1.0, size=row_count)
    values = np.empty(row_count, dtype=np.float64)
    values[0] = noise[0]
    for row_index in range(1, row_count):
        values[row_index] = 0.25 * values[row_index - 1] + noise[row_index]
    return values


def _duration_summary(durations_ms: List[float]) -> Dict[str, float]:
    values = np.asarray(durations_ms, dtype=np.float64)
    return {
        "mean_ms": float(np.mean(values)),
        "p50_ms": float(np.percentile(values, 50)),
        "p95_ms": float(np.percentile(values, 95)),
        "p99_ms": float(np.percentile(values, 99)),
        "max_ms": float(np.max(values)),
    }


def _time_fast_adf(calls: int) -> Dict[str, float]:
    sample = _stationary_sample()
    durations_ms: List[float] = []
    fallback_count = 0
    for _ in range(calls):
        started = time.perf_counter()
        _, used_fallback = adf_pvalue_fast(sample, lag=0)
        durations_ms.append((time.perf_counter() - started) * 1000.0)
        fallback_count += int(used_fallback)
    summary = _duration_summary(durations_ms)
    summary["fallback_count"] = float(fallback_count)
    return summary


def _time_mackinnon(calls: int) -> Dict[str, float]:
    durations_ms: List[float] = []
    t_statistic = -4.0
    for _ in range(calls):
        started = time.perf_counter()
        mackinnonp(t_statistic, regression="c", N=1)
        durations_ms.append((time.perf_counter() - started) * 1000.0)
    return _duration_summary(durations_ms)


def run_benchmark(calls: int) -> Dict[str, object]:
    warmup_numba()
    fast_adf = _time_fast_adf(calls)
    mackinnon = _time_mackinnon(calls)
    passed = bool(
        fast_adf["mean_ms"] <= FAST_ADF_MEAN_LIMIT_MS
        and fast_adf["p99_ms"] <= FAST_ADF_P99_LIMIT_MS
        and mackinnon["mean_ms"] <= MACKINNON_MEAN_LIMIT_MS
        and mackinnon["p99_ms"] <= MACKINNON_P99_LIMIT_MS
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "calls": calls,
        "fast_adf": fast_adf,
        "mackinnonp": mackinnon,
        "thresholds": {
            "fast_adf_mean_ms_max": FAST_ADF_MEAN_LIMIT_MS,
            "fast_adf_p99_ms_max": FAST_ADF_P99_LIMIT_MS,
            "mackinnonp_mean_ms_max": MACKINNON_MEAN_LIMIT_MS,
            "mackinnonp_p99_ms_max": MACKINNON_P99_LIMIT_MS,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark L6.5 Fast ADF")
    parser.add_argument("--calls", type=int, default=10000)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if int(args.calls) <= 0:
        raise SystemExit("--calls must be positive")
    payload = run_benchmark(int(args.calls))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
