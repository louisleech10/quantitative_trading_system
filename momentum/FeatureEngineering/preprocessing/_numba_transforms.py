"""Numba-accelerated L6.5 transforms for CGSA per-group processing.

These operate on raw numpy float32 arrays and avoid pandas overhead entirely.
"""
from __future__ import annotations

import numpy as np
from momentum.core.logging import get_logger

logger = get_logger(__name__)

_HAS_NUMBA = False
try:
    import numba
    from numba import njit

    _HAS_NUMBA = True
except ImportError:
    logger.warning("numba not available; L6.5 fast transforms disabled, falling back to numpy")
    numba = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Rolling rank (percentile) — O(rows * cols * window), parallelized over cols
# ---------------------------------------------------------------------------

if _HAS_NUMBA:

    @njit(cache=True)
    def _rolling_rank_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Rolling percentile rank along axis-0.

        Returns float32 array same shape as *arr*.
        Constant windows → 0.5. NaN → NaN.

        Note (P1.1 reverted 2026-04-25):
            We previously experimented with ``@njit(parallel=True) + prange``
            here. It is **incompatible** with the L6.5 outer ThreadPool
            (``feature_preprocessor._transform_registry_parallel``) under the
            default Numba ``workqueue`` threading layer, which is *not*
            threadsafe. Concurrent calls from multiple Python threads aborted
            the worker process. Switching layers (``omp``/``tbb``) requires
            extra binary deps that aren't pinned. Sequential ``range`` is the
            safe choice as long as parallelism is provided by the outer pool.
        """
        n_rows, n_cols = arr.shape
        out = np.empty((n_rows, n_cols), dtype=np.float32)
        out[:] = np.nan

        for c in range(n_cols):
            for r in range(n_rows):
                val = arr[r, c]
                if np.isnan(val):
                    continue
                start = max(0, r - window + 1)
                count = 0
                less = 0
                equal = 0
                for k in range(start, r + 1):
                    v = arr[k, c]
                    if not np.isnan(v):
                        count += 1
                        if v < val:
                            less += 1
                        elif v == val:
                            equal += 1
                if count == 0:
                    continue
                # Check constant window: all equal → 0.5
                if less == 0 and equal == count:
                    out[r, c] = 0.5
                else:
                    # average-method percentile rank
                    out[r, c] = np.float32((less + (equal + 1.0) / 2.0) / count)
        return out

else:

    def _rolling_rank_numba(arr: np.ndarray, window: int) -> np.ndarray:  # type: ignore[misc]
        """Fallback: pure numpy rolling rank (slower but correct)."""
        n_rows, n_cols = arr.shape
        out = np.full((n_rows, n_cols), np.nan, dtype=np.float32)
        for r in range(n_rows):
            start = max(0, r - window + 1)
            win = arr[start : r + 1, :]
            valid_mask = ~np.isnan(win)
            val_row = arr[r, :]
            for c in range(n_cols):
                if np.isnan(val_row[c]):
                    continue
                col_valid = win[:, c][valid_mask[:, c]]
                cnt = len(col_valid)
                if cnt == 0:
                    continue
                less = np.sum(col_valid < val_row[c])
                equal = np.sum(col_valid == val_row[c])
                if less == 0 and equal == cnt:
                    out[r, c] = 0.5
                else:
                    out[r, c] = np.float32((less + (equal + 1.0) / 2.0) / cnt)
        return out


# ---------------------------------------------------------------------------
# Rolling mean / std — uses bottleneck if available, else numpy stride tricks
# ---------------------------------------------------------------------------

try:
    import bottleneck as bn

    _HAS_BN = True
except ImportError:
    _HAS_BN = False
    bn = None  # type: ignore[assignment]


def _rolling_mean_std(arr: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Compute rolling mean and std along axis-0 for a 2-D float32 array.

    Returns (mean, std) both float32.
    """
    if _HAS_BN:
        mean = bn.move_mean(arr, window=window, min_count=1, axis=0).astype(np.float32)
        std = bn.move_std(arr, window=window, min_count=1, axis=0, ddof=1).astype(np.float32)
        return mean, std

    # Fallback: cumsum-based rolling mean/std (O(n) per column).
    n_rows, n_cols = arr.shape
    # Replace NaN with 0 for cumsum; track valid counts for min_periods=1.
    mask = ~np.isnan(arr)
    safe = np.where(mask, arr, 0.0)

    cumsum = np.cumsum(safe, axis=0)
    cumsum2 = np.cumsum(safe ** 2, axis=0)
    cumcnt = np.cumsum(mask.astype(np.float64), axis=0)

    # Shift by window
    cumsum_shifted = np.zeros_like(cumsum)
    cumsum_shifted[window:] = cumsum[:-window]
    cumsum2_shifted = np.zeros_like(cumsum2)
    cumsum2_shifted[window:] = cumsum2[:-window]
    cumcnt_shifted = np.zeros_like(cumcnt)
    cumcnt_shifted[window:] = cumcnt[:-window]

    win_sum = cumsum - cumsum_shifted
    win_sum2 = cumsum2 - cumsum2_shifted
    win_cnt = cumcnt - cumcnt_shifted

    # Avoid division by zero
    safe_cnt = np.where(win_cnt > 0, win_cnt, 1.0)
    mean = (win_sum / safe_cnt).astype(np.float32)

    # Bessel-corrected variance: var = (sum_sq - n*mean^2) / (n-1)
    variance = (win_sum2 - win_cnt * mean.astype(np.float64) ** 2)
    safe_cnt_m1 = np.where(win_cnt > 1, win_cnt - 1, 1.0)
    variance = np.maximum(variance / safe_cnt_m1, 0.0)
    std = np.sqrt(variance).astype(np.float32)

    # Mask where no valid values
    no_data = win_cnt == 0
    mean[no_data] = np.nan
    std[no_data] = np.nan

    return mean, std


# ---------------------------------------------------------------------------
# Winsorization (quantile clipping) — pure numpy
# ---------------------------------------------------------------------------

def winsorize_array(arr: np.ndarray, lower_q: float = 0.01, upper_q: float = 0.99) -> np.ndarray:
    """Quantile winsorization on float32 array, column-wise.

    Memory-conscious in-place variant (P2.5 — 2026-04-25):
        Profiler showed the previous implementation peaked at ~4× input
        because each of ``np.clip`` / ``np.where`` / ``.astype`` allocated
        a new full-size copy. We now:
        1. Clip in-place into ``arr`` (caller already passed a fresh copy
           via ``transform_array_fast``'s opening ``astype(copy=True)``).
        2. Compute the NaN mask once and write NaN back via boolean
           indexing instead of ``np.where`` (no copy).
        3. Skip the trailing ``.astype(np.float32)`` because clip preserves
           dtype when the bounds match.
        Peak drops from ~4× input to ~2× input (only the two quantile
        bound vectors are extra).

    Single-sort optimization (P4.3 — 2026-04-25):
        ``np.nanquantile`` sorts each column to compute the quantile.
        Calling it twice (lower then upper) doubles the sort cost. By
        passing both quantiles as an array, numpy sorts each column once
        and interpolates both quantiles from the same sorted view —
        bit-exact equivalent to two separate calls.
    """
    bounds = np.nanquantile(arr, [lower_q, upper_q], axis=0).astype(
        np.float32, copy=False
    )
    lowers = bounds[0]
    uppers = bounds[1]
    nan_mask = np.isnan(arr)
    np.clip(arr, lowers, uppers, out=arr)
    arr[nan_mask] = np.nan
    return arr


# ---------------------------------------------------------------------------
# Combined fast transform for CGSA per-group
# ---------------------------------------------------------------------------

def transform_array_fast(
    arr: np.ndarray,
    *,
    winsorize: bool = True,
    winsor_lower_q: float = 0.01,
    winsor_upper_q: float = 0.99,
    rank: bool = True,
    rank_window: int = 252,
    zscore: bool = True,
    zscore_window: int = 100,
    zscore_epsilon: float = 1e-8,
) -> np.ndarray:
    """Apply L6.5 transforms on a raw float32 array (rows × cols).

    Order: winsorize → rank_transform → adaptive_zscore (matches _transform_single).
    Returns float32 array of same shape (replace mode only).

    Memory-conscious in-place chain (P2.5 — 2026-04-25):
        Profiler revealed zscore was the largest RAM amplifier (peak ~7×
        input) because the formula ``(data-mean)/(std+eps)`` plus two
        ``np.where`` calls plus ``.astype`` allocated 5+ full-size temps.
        We now compute zscore in-place on the rolling-rank output,
        eliminating those copies. Combined with the winsorize in-place
        change, peak per-group drops from ~7× to ~3× input.
    """
    data = arr.astype(np.float32, copy=True)

    if winsorize:
        data = winsorize_array(data, winsor_lower_q, winsor_upper_q)

    if rank:
        # rank produces a fresh out array; safe to discard the prior `data`.
        data = _rolling_rank_numba(data, rank_window)

    if zscore:
        mean, std = _rolling_mean_std(data, zscore_window)
        # Cache masks BEFORE mutating any input — preserves bit-exact parity
        # with the original (data-mean)/(std+eps) + np.where(std>0,..) formula.
        # NB: ``~(std > 0)`` matches BOTH std==0 and std==NaN (mirrors the
        # original `np.where(std > 0, z, 0.0)` semantic where NaN std → 0.0).
        nan_mask = np.isnan(data)
        bad_std = ~(std > 0)
        # In-place: data <- data - mean   (saves one full-size temp)
        np.subtract(data, mean, out=data)
        # In-place: std <- std + epsilon  (std is a fresh array; safe to mutate)
        np.add(std, zscore_epsilon, out=std)
        # In-place: data <- data / (std+eps)
        np.divide(data, std, out=data)
        if bad_std.any():
            data[bad_std] = 0.0
        data[nan_mask] = np.nan
        # data is already float32 (rank output is float32); no astype needed.

    return data


def warmup_numba() -> None:
    """JIT-compile numba kernels with a tiny dummy array."""
    if not _HAS_NUMBA:
        return
    dummy = np.random.randn(10, 2).astype(np.float32)
    _ = _rolling_rank_numba(dummy, 5)
    logger.info("[L6.5] numba rolling_rank JIT warmup done")
