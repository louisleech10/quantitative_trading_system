"""Verify L6.5 in-place optimization: numerical parity + RAM peak.

Compares the OPTIMIZED `transform_array_fast` against a faithful
reproduction of the ORIGINAL implementation (kept here only for the
diff). The optimized version must produce bit-exact identical output
(allclose with rtol=0, atol=0 on non-NaN entries).
"""
from __future__ import annotations

import gc
import os
import sys
import tracemalloc

import numpy as np
import psutil


def rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


def transform_array_fast_OLD(
    arr: np.ndarray,
    *,
    winsor_lower_q: float = 0.01,
    winsor_upper_q: float = 0.99,
    rank_window: int = 252,
    zscore_window: int = 100,
    zscore_epsilon: float = 1e-8,
) -> np.ndarray:
    """Faithful reproduction of the pre-P2.5 implementation."""
    from momentum.FeatureEngineering.preprocessing._numba_transforms import (
        _rolling_rank_numba,
        _rolling_mean_std,
    )

    data = arr.astype(np.float32, copy=True)

    # OLD winsorize (4 copies)
    lowers = np.nanquantile(data, winsor_lower_q, axis=0).astype(np.float32)
    uppers = np.nanquantile(data, winsor_upper_q, axis=0).astype(np.float32)
    out = np.clip(data, lowers[np.newaxis, :], uppers[np.newaxis, :])
    data = np.where(np.isnan(data), np.nan, out).astype(np.float32)

    # rank
    data = _rolling_rank_numba(data, rank_window)

    # OLD zscore (7 copies)
    mean, std = _rolling_mean_std(data, zscore_window)
    z = (data - mean) / (std + zscore_epsilon)
    z = np.where(std > 0, z, 0.0)
    z = np.where(np.isnan(data), np.nan, z)
    data = z.astype(np.float32)

    return data


def main() -> int:
    from momentum.FeatureEngineering.preprocessing._numba_transforms import transform_array_fast

    # Warmup numba kernels
    rng_warmup = np.random.default_rng(0)
    _ = transform_array_fast(rng_warmup.standard_normal((300, 5), dtype=np.float32))
    _ = transform_array_fast_OLD(rng_warmup.standard_normal((300, 5), dtype=np.float32))
    gc.collect()

    cases = [
        ("medium  6k cols", 1494, 6000),
        ("large  16k cols", 1494, 16000),
    ]

    for label, rows, cols in cases:
        print(f"\n{'='*70}\n  CASE: {label}  ({rows} rows × {cols} cols)\n{'='*70}")
        rng = np.random.default_rng(42)
        arr = rng.standard_normal((rows, cols), dtype=np.float32)
        nan_idx = rng.random((rows, cols)) < 0.05
        arr[nan_idx] = np.nan

        # ---- OLD ----
        gc.collect()
        base = rss_mb()
        tracemalloc.start()
        out_old = transform_array_fast_OLD(arr)
        _, peak_old = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_old_mb = peak_old / 1024 / 1024
        print(f"  OLD: tracemalloc peak = {peak_old_mb:7.1f} MB  "
              f"(RSS_after={rss_mb():.1f} MB, baseline {base:.1f})")
        gc.collect()

        # ---- NEW ----
        base = rss_mb()
        tracemalloc.start()
        out_new = transform_array_fast(arr)
        _, peak_new = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_new_mb = peak_new / 1024 / 1024
        print(f"  NEW: tracemalloc peak = {peak_new_mb:7.1f} MB  "
              f"(RSS_after={rss_mb():.1f} MB, baseline {base:.1f})")
        savings = peak_old_mb - peak_new_mb
        ratio = peak_new_mb / peak_old_mb if peak_old_mb else 0
        print(f"  → savings: {savings:+.1f} MB  ({ratio*100:.1f}% of OLD)")

        # ---- parity ----
        old_nan = np.isnan(out_old)
        new_nan = np.isnan(out_new)
        nan_match = np.array_equal(old_nan, new_nan)
        # Compare non-NaN values bit-exactly
        if nan_match:
            valid = ~old_nan
            equal_bytes = (out_old[valid].tobytes() == out_new[valid].tobytes())
            allclose = np.allclose(out_old[valid], out_new[valid], rtol=0, atol=0, equal_nan=True)
            max_abs_diff = float(np.max(np.abs(out_old[valid] - out_new[valid]))) if valid.any() else 0.0
            print(f"  PARITY: nan_mask={nan_match}, bit_exact={equal_bytes}, "
                  f"allclose(rtol=0,atol=0)={allclose}, max|diff|={max_abs_diff:.2e}")
        else:
            n_diff = int(np.sum(old_nan != new_nan))
            print(f"  PARITY: nan_mask MISMATCH, {n_diff} positions differ")

        del out_old, out_new, arr
        gc.collect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
