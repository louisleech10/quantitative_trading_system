#!/usr/bin/env python3
"""Read-only B7 L6.5 ThreadPool microbench.

Loads real 1h kline series via h5py and writes no data_cache artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

import h5py
import numpy as np
import pandas as pd
import psutil
from numba import njit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from momentum.FeatureEngineering.preprocessing._numba_transforms import rolling_quantile_2d
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


@njit(cache=False)
def rolling_quantile_sliding_gil(
    arr: np.ndarray,
    lower_q: float,
    upper_q: float,
    window: int,
    min_periods: int,
) -> Tuple[np.ndarray, np.ndarray]:
    n_rows, n_cols = arr.shape
    lower = np.empty((n_rows, n_cols), dtype=np.float32)
    upper = np.empty((n_rows, n_cols), dtype=np.float32)
    lower[:] = np.nan
    upper[:] = np.nan
    for c in range(n_cols):
        sorted_vals = np.empty(window + 1, dtype=np.float64)
        count = 0
        for r in range(n_rows):
            value = arr[r, c]
            if not np.isnan(value) and np.isfinite(value):
                left = 0
                right = count
                while left < right:
                    mid = (left + right) // 2
                    if value < sorted_vals[mid]:
                        right = mid
                    else:
                        left = mid + 1
                for k in range(count, left, -1):
                    sorted_vals[k] = sorted_vals[k - 1]
                sorted_vals[left] = value
                count += 1
            if r >= window:
                outgoing = arr[r - window, c]
                if not np.isnan(outgoing) and np.isfinite(outgoing):
                    left = 0
                    right = count
                    while left < right:
                        mid = (left + right) // 2
                        if sorted_vals[mid] < outgoing:
                            left = mid + 1
                        else:
                            right = mid
                    for k in range(left, count - 1):
                        sorted_vals[k] = sorted_vals[k + 1]
                    count -= 1
            if count < min_periods:
                continue
            for q_idx in range(2):
                q = lower_q if q_idx == 0 else upper_q
                pos = q * (count - 1)
                lo = int(np.floor(pos))
                hi = min(lo + 1, count - 1)
                frac = pos - lo
                quantile = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])
                if q_idx == 0:
                    lower[r, c] = np.float32(quantile)
                else:
                    upper[r, c] = np.float32(quantile)
    return lower, upper


@njit(cache=False, nogil=True)
def rolling_quantile_sliding_nogil(
    arr: np.ndarray,
    lower_q: float,
    upper_q: float,
    window: int,
    min_periods: int,
) -> Tuple[np.ndarray, np.ndarray]:
    n_rows, n_cols = arr.shape
    lower = np.empty((n_rows, n_cols), dtype=np.float32)
    upper = np.empty((n_rows, n_cols), dtype=np.float32)
    lower[:] = np.nan
    upper[:] = np.nan
    for c in range(n_cols):
        sorted_vals = np.empty(window + 1, dtype=np.float64)
        count = 0
        for r in range(n_rows):
            value = arr[r, c]
            if not np.isnan(value) and np.isfinite(value):
                left = 0
                right = count
                while left < right:
                    mid = (left + right) // 2
                    if value < sorted_vals[mid]:
                        right = mid
                    else:
                        left = mid + 1
                for k in range(count, left, -1):
                    sorted_vals[k] = sorted_vals[k - 1]
                sorted_vals[left] = value
                count += 1
            if r >= window:
                outgoing = arr[r - window, c]
                if not np.isnan(outgoing) and np.isfinite(outgoing):
                    left = 0
                    right = count
                    while left < right:
                        mid = (left + right) // 2
                        if sorted_vals[mid] < outgoing:
                            left = mid + 1
                        else:
                            right = mid
                    for k in range(left, count - 1):
                        sorted_vals[k] = sorted_vals[k + 1]
                    count -= 1
            if count < min_periods:
                continue
            for q_idx in range(2):
                q = lower_q if q_idx == 0 else upper_q
                pos = q * (count - 1)
                lo = int(np.floor(pos))
                hi = min(lo + 1, count - 1)
                frac = pos - lo
                quantile = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])
                if q_idx == 0:
                    lower[r, c] = np.float32(quantile)
                else:
                    upper[r, c] = np.float32(quantile)
    return lower, upper


@dataclass
class BenchResult:
    name: str
    workers: int
    wall_s: float
    speedup: float
    rss_start_mb: float
    rss_peak_mb: float
    rss_delta_mb: float
    checksum: float


class RssSampler:
    def __init__(self, interval_s: float = 0.01) -> None:
        self._proc = psutil.Process()
        self._interval_s = interval_s
        self._stop = threading.Event()
        self.start_mb = self._rss_mb()
        self.peak_mb = self.start_mb
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _rss_mb(self) -> float:
        return self._proc.memory_info().rss / (1024 * 1024)

    def __enter__(self) -> "RssSampler":
        self.start_mb = self._rss_mb()
        self.peak_mb = self.start_mb
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        self.peak_mb = max(self.peak_mb, self._rss_mb())

    def _run(self) -> None:
        while not self._stop.is_set():
            self.peak_mb = max(self.peak_mb, self._rss_mb())
            time.sleep(self._interval_s)


def load_real_groups(path: Path, groups: int, rows: int) -> List[pd.DataFrame]:
    fields = ("close", "volume", "taker_ratio")
    frames: List[pd.DataFrame] = []
    with h5py.File(path, "r") as h5:
        symbols = sorted(k for k in h5.keys() if not k.startswith("_"))
        for symbol in symbols:
            data = h5[f"{symbol}/1h/data"][:rows]
            for field in fields:
                values = np.asarray(data[field], dtype=np.float32)
                col = f"L3_{symbol}_{field}_narrow"
                frames.append(pd.DataFrame({col: values}))
                if len(frames) >= groups:
                    return frames
    raise RuntimeError(f"not enough groups: requested={groups} got={len(frames)}")


def l65_config(window: int) -> Dict[str, object]:
    return {
        "enabled": True,
        "causal_preprocessing": True,
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.01, 0.99],
            "window": window,
            "apply_to": "all",
        },
        "rank_transform": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
    }


def run_threaded(
    name: str,
    workers: int,
    tasks: Sequence[Callable[[], float]],
    serial_wall: float | None = None,
) -> BenchResult:
    with RssSampler() as rss:
        t0 = time.perf_counter()
        if workers == 1:
            checks = [task() for task in tasks]
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                checks = list(pool.map(lambda fn: fn(), tasks))
        wall = time.perf_counter() - t0
    base = wall if serial_wall is None else serial_wall
    return BenchResult(
        name=name,
        workers=workers,
        wall_s=wall,
        speedup=base / wall if wall > 0 else float("nan"),
        rss_start_mb=rss.start_mb,
        rss_peak_mb=rss.peak_mb,
        rss_delta_mb=rss.peak_mb - rss.start_mb,
        checksum=float(np.sum(checks)),
    )


def bench_l65(frames: Sequence[pd.DataFrame], window: int, workers_set: Sequence[int]) -> List[BenchResult]:
    config = l65_config(window)

    def make_task(frame: pd.DataFrame) -> Callable[[], float]:
        def task() -> float:
            pp = FeaturePreprocessor(config)
            out = pp._transform_single(frame)
            return float(np.nanmean(out.to_numpy(dtype=np.float32)))
        return task

    tasks = [make_task(frame) for frame in frames]
    results: List[BenchResult] = []
    serial_wall = None
    for workers in workers_set:
        result = run_threaded("native_l65_winsor", workers, tasks, serial_wall)
        if workers == 1:
            serial_wall = result.wall_s
            result.speedup = 1.0
        results.append(result)
    return results


def bench_kernel(
    name: str,
    kernel: Callable[[np.ndarray, float, float, int, int], Tuple[np.ndarray, np.ndarray]],
    arrays: Sequence[np.ndarray],
    window: int,
    min_periods: int,
    workers_set: Sequence[int],
) -> List[BenchResult]:
    def make_task(arr: np.ndarray) -> Callable[[], float]:
        def task() -> float:
            lower, upper = kernel(arr, 0.01, 0.99, window, min_periods)
            return float(np.nanmean(lower) + np.nanmean(upper))
        return task

    tasks = [make_task(arr) for arr in arrays]
    results: List[BenchResult] = []
    serial_wall = None
    for workers in workers_set:
        result = run_threaded(name, workers, tasks, serial_wall)
        if workers == 1:
            serial_wall = result.wall_s
            result.speedup = 1.0
        results.append(result)
    return results


def warmup(arrays: Sequence[np.ndarray], window: int, min_periods: int) -> None:
    sample = arrays[0][:512].copy()
    sample_window = min(window, 128)
    sample_min = min(min_periods, sample_window)
    rolling_quantile_2d(sample, 0.01, 0.99, sample_window, sample_min)
    rolling_quantile_sliding_gil(sample, 0.01, 0.99, sample_window, sample_min)
    rolling_quantile_sliding_nogil(sample, 0.01, 0.99, sample_window, sample_min)
    FeaturePreprocessor(l65_config(sample_window))._transform_single(pd.DataFrame({"warmup": sample[:, 0]}))


def format_table(results: Sequence[BenchResult]) -> str:
    lines = [
        "| bench | workers | wall_s | speedup_vs_1 | rss_peak_mb | rss_delta_mb | checksum |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        lines.append(
            f"| {r.name} | {r.workers} | {r.wall_s:.3f} | {r.speedup:.2f}x | "
            f"{r.rss_peak_mb:.1f} | {r.rss_delta_mb:.1f} | {r.checksum:.6g} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h5", type=Path, default=Path("data_cache/feature_klines/kline_cache.h5"))
    parser.add_argument("--groups", type=int, default=24)
    parser.add_argument("--rows", type=int, default=20352)
    parser.add_argument("--window", type=int, default=3024)
    parser.add_argument("--workers", default="1,2,4,6")
    parser.add_argument("--json-out", type=Path, default=Path("scripts/tmp/b7_l65_threadpool_microbench_results.json"))
    args = parser.parse_args()

    os.environ.setdefault("NUMBA_NUM_THREADS", "1")
    workers_set = [int(x) for x in args.workers.split(",") if x]
    min_periods = min(args.window, max(20, args.window // 4))
    frames = load_real_groups(args.h5, args.groups, args.rows)
    arrays = [frame.to_numpy(dtype=np.float64, copy=True) for frame in frames]
    warmup(arrays, args.window, min_periods)

    all_results: List[BenchResult] = []
    all_results.extend(bench_l65(frames, args.window, workers_set))
    all_results.extend(bench_kernel("product_kernel_current", rolling_quantile_2d, arrays, args.window, min_periods, workers_set))
    all_results.extend(bench_kernel("copied_kernel_njit", rolling_quantile_sliding_gil, arrays, args.window, min_periods, workers_set))
    all_results.extend(bench_kernel("copied_kernel_nogil", rolling_quantile_sliding_nogil, arrays, args.window, min_periods, workers_set))

    metadata = {
        "h5": str(args.h5),
        "groups": args.groups,
        "rows": args.rows,
        "window": args.window,
        "min_periods": min_periods,
        "workers": workers_set,
        "l65_optimization_profile": os.getenv("FFACT_L65_OPTIMIZATION_PROFILE", "optimized(default)"),
        "numba_num_threads": os.getenv("NUMBA_NUM_THREADS"),
        "rss_idle_mb": psutil.Process().memory_info().rss / (1024 * 1024),
        "wall_median_by_bench": {
            name: statistics.median(r.wall_s for r in all_results if r.name == name)
            for name in sorted({r.name for r in all_results})
        },
    }
    payload = {"metadata": metadata, "results": [r.__dict__ for r in all_results]}
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    print(format_table(all_results))
    print(f"RESULT_JSON={args.json_out}")


if __name__ == "__main__":
    main()
