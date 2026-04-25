"""Profile L6.5 RAM peak per sub-step on a representative group size.

Goal: identify which intermediate copy in transform_array_fast dominates
the 2270 MB peak observed during preprocessing. Uses tracemalloc and
process RSS sampling.
"""
from __future__ import annotations

import gc
import os
import sys
import time
import tracemalloc

import numpy as np
import psutil


def rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


def banner(title: str, baseline_mb: float, peak_tm_mb: float) -> None:
    delta = rss_mb() - baseline_mb
    print(
        f"  {title:<40s}  RSS_now={rss_mb():7.1f} MB  "
        f"delta_from_start={delta:+7.1f} MB  tm_peak={peak_tm_mb:7.1f} MB"
    )


def profile_winsorize(arr: np.ndarray) -> None:
    print(f"\n[winsorize_array]  input shape={arr.shape}, dtype={arr.dtype}, "
          f"size={arr.nbytes/1024/1024:.1f} MB")
    base = rss_mb()
    tracemalloc.start()

    t0 = time.time()
    lowers = np.nanquantile(arr, 0.01, axis=0).astype(np.float32)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"nanquantile(0.01)  ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()

    t0 = time.time()
    uppers = np.nanquantile(arr, 0.99, axis=0).astype(np.float32)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"nanquantile(0.99)  ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()

    t0 = time.time()
    out = np.clip(arr, lowers[np.newaxis, :], uppers[np.newaxis, :])
    _, peak = tracemalloc.get_traced_memory()
    banner(f"np.clip            ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()

    t0 = time.time()
    nan_mask = np.isnan(arr)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"np.isnan (mask)    ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()

    t0 = time.time()
    out2 = np.where(nan_mask, np.nan, out)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"np.where(nan,out)  ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()

    t0 = time.time()
    final = out2.astype(np.float32)
    _, peak = tracemalloc.get_traced_memory()
    banner(f".astype(float32)   ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.stop()
    del lowers, uppers, out, nan_mask, out2, final
    gc.collect()


def profile_full_chain(arr: np.ndarray) -> None:
    """Mimic transform_array_fast end-to-end with intermediate snapshots."""
    print(f"\n[full chain]  input shape={arr.shape}, dtype={arr.dtype}")
    base = rss_mb()
    tracemalloc.start()

    t0 = time.time()
    data = arr.astype(np.float32, copy=True)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"astype copy        ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()

    # ---- winsorize inline (current implementation)
    t0 = time.time()
    lowers = np.nanquantile(data, 0.01, axis=0).astype(np.float32)
    uppers = np.nanquantile(data, 0.99, axis=0).astype(np.float32)
    out = np.clip(data, lowers[np.newaxis, :], uppers[np.newaxis, :])
    data_w = np.where(np.isnan(data), np.nan, out).astype(np.float32)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"winsorize(curr)    ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()
    del lowers, uppers, out
    gc.collect()

    # ---- rolling rank
    from momentum.FeatureEngineering.preprocessing._numba_transforms import _rolling_rank_numba

    t0 = time.time()
    data_r = _rolling_rank_numba(data_w, 252)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"rolling_rank       ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.reset_peak()

    # ---- zscore
    from momentum.FeatureEngineering.preprocessing._numba_transforms import _rolling_mean_std

    t0 = time.time()
    mean, std = _rolling_mean_std(data_r, 100)
    z = (data_r - mean) / (std + 1e-8)
    z = np.where(std > 0, z, 0.0)
    z = np.where(np.isnan(data_r), np.nan, z)
    data_z = z.astype(np.float32)
    _, peak = tracemalloc.get_traced_memory()
    banner(f"zscore (curr)      ({time.time()-t0:.2f}s)", base, peak / 1024 / 1024)
    tracemalloc.stop()


def main() -> int:
    # Representative L6.5 group sizes. Largest known group ~16k cols × 1494 rows.
    sizes = [
        ("medium  6k cols", 1494, 6000),
        ("large  16k cols", 1494, 16000),
    ]

    rng = np.random.default_rng(42)
    for label, rows, cols in sizes:
        print(f"\n{'='*70}\n  CASE: {label}  ({rows} rows × {cols} cols)\n{'='*70}")
        arr = rng.standard_normal((rows, cols), dtype=np.float32)
        # Inject some NaNs (~5%)
        nan_mask = rng.random((rows, cols)) < 0.05
        arr[nan_mask] = np.nan
        print(f"  raw size: {arr.nbytes/1024/1024:.1f} MB, RSS_baseline={rss_mb():.1f} MB")

        profile_winsorize(arr)
        gc.collect()
        profile_full_chain(arr)
        del arr, nan_mask
        gc.collect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
