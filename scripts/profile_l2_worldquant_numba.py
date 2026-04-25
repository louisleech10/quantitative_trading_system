"""
Standalone benchmark + parity verification for WorldQuant L2 operators.

Compares pandas rolling.apply baselines vs Numba-accelerated kernels for:
- ts_argmax
- ts_argmin
- decay_linear

Goal: verify bit-exact parity (numerical equivalence within float tolerance)
before integrating into derived_operators.py.
"""
from __future__ import annotations

import time
import numpy as np
import pandas as pd
from numba import njit, prange


# ---------------------------------------------------------------------------
# Numba kernels (parallel over columns)
# ---------------------------------------------------------------------------

@njit(parallel=True, cache=True, fastmath=False)
def _ts_argmax_2d(arr: np.ndarray, window: int) -> np.ndarray:
    """pandas rolling.apply(np.argmax, raw=True) semantics with min_periods=window.

    If any value in the window is NaN, output is NaN.
    Otherwise returns index (0..window-1) of max value (first occurrence on ties).
    """
    n_rows, n_cols = arr.shape
    out = np.full((n_rows, n_cols), np.nan, dtype=np.float64)
    for c in prange(n_cols):
        for i in range(window - 1, n_rows):
            base = i - window + 1
            best_val = arr[base, c]
            best_idx = 0
            saw_nan = (best_val != best_val)
            for k in range(1, window):
                v = arr[base + k, c]
                if v != v:
                    saw_nan = True
                    break
                if v > best_val:
                    best_val = v
                    best_idx = k
            if not saw_nan:
                out[i, c] = best_idx
    return out


@njit(parallel=True, cache=True, fastmath=False)
def _ts_argmin_2d(arr: np.ndarray, window: int) -> np.ndarray:
    n_rows, n_cols = arr.shape
    out = np.full((n_rows, n_cols), np.nan, dtype=np.float64)
    for c in prange(n_cols):
        for i in range(window - 1, n_rows):
            base = i - window + 1
            best_val = arr[base, c]
            best_idx = 0
            saw_nan = (best_val != best_val)
            for k in range(1, window):
                v = arr[base + k, c]
                if v != v:
                    saw_nan = True
                    break
                if v < best_val:
                    best_val = v
                    best_idx = k
            if not saw_nan:
                out[i, c] = best_idx
    return out


@njit(parallel=True, cache=True, fastmath=False)
def _decay_linear_2d(arr: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Weighted dot product over rolling window.

    weights[k] is applied to arr[i - window + 1 + k, c].
    pandas rolling.apply(raw=True) propagates NaN: if any value in window is NaN,
    np.dot returns NaN.
    """
    n_rows, n_cols = arr.shape
    window = weights.shape[0]
    out = np.full((n_rows, n_cols), np.nan, dtype=np.float64)
    for c in prange(n_cols):
        for i in range(window - 1, n_rows):
            s = 0.0
            has_nan = False
            for k in range(window):
                v = arr[i - window + 1 + k, c]
                if v != v:  # NaN check
                    has_nan = True
                    break
                s += v * weights[k]
            if has_nan:
                out[i, c] = np.nan
            else:
                out[i, c] = s
    return out


# ---------------------------------------------------------------------------
# Wrappers that mimic the existing return shape (DataFrame with same index/cols)
# ---------------------------------------------------------------------------

def ts_argmax_numba(df: pd.DataFrame, window: int) -> pd.DataFrame:
    arr = df.to_numpy(dtype=np.float64, copy=False)
    out = _ts_argmax_2d(arr, window)
    return pd.DataFrame(out, index=df.index, columns=df.columns)


def ts_argmin_numba(df: pd.DataFrame, window: int) -> pd.DataFrame:
    arr = df.to_numpy(dtype=np.float64, copy=False)
    out = _ts_argmin_2d(arr, window)
    return pd.DataFrame(out, index=df.index, columns=df.columns)


def decay_linear_numba(df: pd.DataFrame, window: int) -> pd.DataFrame:
    weights = np.arange(1, window + 1, dtype=np.float64)
    weights /= weights.sum()
    arr = df.to_numpy(dtype=np.float64, copy=False)
    out = _decay_linear_2d(arr, weights)
    return pd.DataFrame(out, index=df.index, columns=df.columns)


# ---------------------------------------------------------------------------
# Parity + benchmark
# ---------------------------------------------------------------------------

def main() -> None:
    np.random.seed(0)
    # Use small data first for parity verification, then larger for bench
    rows, cols = 500, 20
    base = np.random.randn(rows, cols).astype(np.float64)
    # Inject some NaNs to exercise edge cases
    nan_mask = np.random.rand(rows, cols) < 0.02
    base[nan_mask] = np.nan
    df_small = pd.DataFrame(base, columns=[f"c{i}" for i in range(cols)])

    print("=" * 70)
    print("PARITY VERIFICATION (small data with NaNs)")
    print("=" * 70)

    for w in [5, 13, 21]:
        rolling = df_small.rolling(w)

        # ts_argmax
        baseline = rolling.apply(np.argmax, raw=True)
        candidate = ts_argmax_numba(df_small, w)
        # Compare ignoring NaN
        diff = (baseline.fillna(-999) - candidate.fillna(-999)).abs().max().max()
        print(f"  W={w:2d} ts_argmax    : max_abs_diff={diff:.6g}")
        assert diff < 1e-9, f"ts_argmax W={w} parity FAIL"

        # ts_argmin
        baseline = rolling.apply(np.argmin, raw=True)
        candidate = ts_argmin_numba(df_small, w)
        diff = (baseline.fillna(-999) - candidate.fillna(-999)).abs().max().max()
        print(f"  W={w:2d} ts_argmin    : max_abs_diff={diff:.6g}")
        assert diff < 1e-9, f"ts_argmin W={w} parity FAIL"

        # decay_linear
        weights = np.arange(1, w + 1, dtype=float)
        weights /= weights.sum()
        baseline = rolling.apply(lambda x, ww=weights: float(np.dot(x, ww)), raw=True)
        candidate = decay_linear_numba(df_small, w)
        diff = (baseline.fillna(-999) - candidate.fillna(-999)).abs().max().max()
        print(f"  W={w:2d} decay_linear : max_abs_diff={diff:.6g}")
        assert diff < 1e-9, f"decay_linear W={w} parity FAIL (diff={diff})"

    print("\nAll parity checks PASSED.\n")

    # ------------------------------------------------------------------
    # Benchmark on realistic scale
    # ------------------------------------------------------------------
    print("=" * 70)
    print("BENCHMARK (1h L2 scale: 17928 x 800 with 2% NaN)")
    print("=" * 70)
    np.random.seed(0)
    big = np.random.randn(17928, 800).astype(np.float32)
    nan_mask = np.random.rand(*big.shape) < 0.02
    big[nan_mask] = np.nan
    df_big = pd.DataFrame(big, columns=[f"c{i}" for i in range(800)])

    # Warm up Numba
    _ = ts_argmax_numba(df_big.iloc[:50, :5], 5)
    _ = ts_argmin_numba(df_big.iloc[:50, :5], 5)
    _ = decay_linear_numba(df_big.iloc[:50, :5], 5)

    for w in [5, 13, 21]:
        rolling = df_big.rolling(w)

        t0 = time.time()
        _ = rolling.apply(np.argmax, raw=True)
        t_pd_argmax = time.time() - t0

        t0 = time.time()
        _ = ts_argmax_numba(df_big, w)
        t_nb_argmax = time.time() - t0

        t0 = time.time()
        _ = rolling.apply(np.argmin, raw=True)
        t_pd_argmin = time.time() - t0

        t0 = time.time()
        _ = ts_argmin_numba(df_big, w)
        t_nb_argmin = time.time() - t0

        weights = np.arange(1, w + 1, dtype=float)
        weights /= weights.sum()

        t0 = time.time()
        _ = rolling.apply(lambda x, ww=weights: float(np.dot(x, ww)), raw=True)
        t_pd_decay = time.time() - t0

        t0 = time.time()
        _ = decay_linear_numba(df_big, w)
        t_nb_decay = time.time() - t0

        print(f"  W={w:2d}")
        print(f"    ts_argmax    : pandas={t_pd_argmax:6.2f}s  numba={t_nb_argmax:6.2f}s  speedup={t_pd_argmax/t_nb_argmax:5.1f}x")
        print(f"    ts_argmin    : pandas={t_pd_argmin:6.2f}s  numba={t_nb_argmin:6.2f}s  speedup={t_pd_argmin/t_nb_argmin:5.1f}x")
        print(f"    decay_linear : pandas={t_pd_decay:6.2f}s  numba={t_nb_decay:6.2f}s  speedup={t_pd_decay/t_nb_decay:5.1f}x")


if __name__ == "__main__":
    main()
