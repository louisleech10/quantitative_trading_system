"""Numba-accelerated L6.5 transforms for CGSA per-group processing.

These operate on raw numpy float32 arrays and avoid pandas overhead entirely.
"""
from __future__ import annotations

import os
import numpy as np
from momentum.core.logging import get_logger

logger = get_logger(__name__)

_HAS_NUMBA = False
try:
    import numba
    from numba import njit, prange

    _HAS_NUMBA = True
except ImportError:
    logger.warning("numba not available; L6.5 fast transforms disabled, falling back to numpy")
    numba = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Rolling rank (percentile) — O(rows * cols * window), parallelized over cols
# ---------------------------------------------------------------------------

if _HAS_NUMBA:

    @njit(cache=True, parallel=True)
    def _rolling_rank_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Rolling percentile rank along axis-0, parallel across columns.

        Returns float32 array same shape as *arr*.
        Constant windows → 0.5. NaN → NaN.
        """
        n_rows, n_cols = arr.shape
        out = np.empty((n_rows, n_cols), dtype=np.float32)
        out[:] = np.nan

        for c in prange(n_cols):
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
    """Quantile winsorization on float32 array, column-wise."""
    lowers = np.nanquantile(arr, lower_q, axis=0).astype(np.float32)
    uppers = np.nanquantile(arr, upper_q, axis=0).astype(np.float32)
    out = np.clip(arr, lowers[np.newaxis, :], uppers[np.newaxis, :])
    return np.where(np.isnan(arr), np.nan, out).astype(np.float32)


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
    """
    data = arr.astype(np.float32, copy=True)

    if winsorize:
        data = winsorize_array(data, winsor_lower_q, winsor_upper_q)

    if rank:
        data = _rolling_rank_numba(data, rank_window)

    if zscore:
        mean, std = _rolling_mean_std(data, zscore_window)
        z = (data - mean) / (std + zscore_epsilon)
        z = np.where(std > 0, z, 0.0)
        z = np.where(np.isnan(data), np.nan, z)
        data = z.astype(np.float32)

    return data


def warmup_numba() -> None:
    """JIT-compile numba kernels with a tiny dummy array."""
    if not _HAS_NUMBA:
        return
    dummy = np.random.randn(10, 2).astype(np.float32)
    _ = _rolling_rank_numba(dummy, 5)
    logger.info("[L6.5] numba rolling_rank JIT warmup done")
