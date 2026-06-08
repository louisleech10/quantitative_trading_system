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
    def _rolling_rank_numba(arr: np.ndarray, window: int, min_periods: int = 1) -> np.ndarray:
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
                if count < min_periods:
                    continue
                # Check constant window: all equal → 0.5
                if less == 0 and equal == count:
                    out[r, c] = 0.5
                else:
                    # average-method percentile rank
                    out[r, c] = np.float32((less + (equal + 1.0) / 2.0) / count)
        return out

else:

    def _rolling_rank_numba(arr: np.ndarray, window: int, min_periods: int = 1) -> np.ndarray:  # type: ignore[misc]
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
                if cnt < min_periods:
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


def _rolling_min_periods(window: int) -> int:
    """因果 rolling 暖機門檻，與 slow/legacy winsor 路徑一致。"""
    w = max(1, int(window))
    return min(w, max(20, w // 4))


def _rolling_mean_std(arr: np.ndarray, window: int, min_periods: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Compute rolling mean and std along axis-0 for a 2-D float32 array.

    Returns (mean, std) both float32.
    """
    if _HAS_BN and window <= arr.shape[0] and min_periods <= window:
        mean = bn.move_mean(arr, window=window, min_count=min_periods, axis=0).astype(np.float32)
        std = bn.move_std(arr, window=window, min_count=min_periods, axis=0, ddof=1).astype(np.float32)
        return mean, std

    # Fallback: cumsum-based rolling mean/std (O(n) per column).
    n_rows, n_cols = arr.shape
    # Replace NaN with 0 for cumsum; track valid counts for min_periods.
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
    no_data = win_cnt < min_periods
    mean[no_data] = np.nan
    std[no_data] = np.nan

    return mean, std


if _HAS_NUMBA:

    @njit(cache=True)
    def _rolling_quantile_numba(
        arr: np.ndarray,
        lower_q: float,
        upper_q: float,
        window: int,
        min_periods: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        n_rows, n_cols = arr.shape
        lower = np.empty((n_rows, n_cols), dtype=np.float32)
        upper = np.empty((n_rows, n_cols), dtype=np.float32)
        lower[:] = np.nan
        upper[:] = np.nan

        for c in range(n_cols):
            scratch = np.empty(window, dtype=np.float64)
            for r in range(n_rows):
                start = max(0, r - window + 1)
                count = 0
                for k in range(start, r + 1):
                    v = arr[k, c]
                    if not np.isnan(v) and np.isfinite(v):
                        scratch[count] = v
                        count += 1
                if count < min_periods:
                    continue
                sorted_vals = np.sort(scratch[:count])
                for q_idx in range(2):
                    q = lower_q if q_idx == 0 else upper_q
                    pos = q * (count - 1)
                    lo = int(np.floor(pos))
                    hi = min(lo + 1, count - 1)
                    frac = pos - lo
                    value = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])
                    if q_idx == 0:
                        lower[r, c] = np.float32(value)
                    else:
                        upper[r, c] = np.float32(value)
        return lower, upper

else:

    def _rolling_quantile_numba(
        arr: np.ndarray,
        lower_q: float,
        upper_q: float,
        window: int,
        min_periods: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        n_rows, n_cols = arr.shape
        lower = np.full((n_rows, n_cols), np.nan, dtype=np.float32)
        upper = np.full((n_rows, n_cols), np.nan, dtype=np.float32)
        for c in range(n_cols):
            for r in range(n_rows):
                start = max(0, r - window + 1)
                values = arr[start : r + 1, c]
                values = values[np.isfinite(values)]
                if len(values) < min_periods:
                    continue
                bounds = np.nanquantile(values, [lower_q, upper_q]).astype(np.float32)
                lower[r, c] = bounds[0]
                upper[r, c] = bounds[1]
        return lower, upper


def rolling_quantile_2d(
    arr: np.ndarray,
    lower_q: float,
    upper_q: float,
    window: int,
    min_periods: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return row-wise causal quantile bounds for each column."""
    if window <= 0:
        raise ValueError("rolling quantile window must be positive")
    if min_periods <= 0:
        raise ValueError("rolling quantile min_periods must be positive")
    data = np.asarray(arr, dtype=np.float64)
    if data.ndim != 2:
        raise ValueError("rolling quantile input must be 2D")
    return _rolling_quantile_numba(data, float(lower_q), float(upper_q), int(window), int(min_periods))


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


def rolling_winsorize_array(
    arr: np.ndarray,
    lower_q: float = 0.01,
    upper_q: float = 0.99,
    *,
    window: int = 252,
    min_periods: int = 63,
) -> np.ndarray:
    """Causal quantile winsorization on float32 array, column-wise."""
    lowers, uppers = rolling_quantile_2d(arr, lower_q, upper_q, window, min_periods)
    nan_mask = np.isnan(arr)
    valid_bounds = np.isfinite(lowers) & np.isfinite(uppers)
    clipped = np.clip(arr, lowers, uppers)
    arr[valid_bounds] = clipped[valid_bounds]
    arr[nan_mask] = np.nan
    return arr


# ---------------------------------------------------------------------------
# Combined fast transform for CGSA per-group
# ---------------------------------------------------------------------------

def transform_array_fast(
    arr: np.ndarray,
    *,
    winsorize: bool = True,
    winsor_method: str = "quantile",
    winsor_lower_q: float = 0.01,
    winsor_upper_q: float = 0.99,
    winsor_sigma_k: float = 3.0,
    rank: bool = True,
    rank_window: int = 252,
    zscore: bool = True,
    zscore_window: int = 100,
    zscore_epsilon: float = 1e-8,
    causal_preprocessing: bool = True,
    winsor_window: int = 252,
    winsor_min_periods: int = 63,
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
        if winsor_method == "sigma":
            if causal_preprocessing:
                mean, std = _rolling_mean_std(data, winsor_window, min_periods=winsor_min_periods)
            else:
                mean = np.nanmean(data, axis=0, keepdims=True).astype(np.float32)
                std = np.nanstd(data, axis=0, ddof=1, keepdims=True).astype(np.float32)
            lower = mean.astype(np.float64) - float(winsor_sigma_k) * std.astype(np.float64)
            upper = mean.astype(np.float64) + float(winsor_sigma_k) * std.astype(np.float64)
            nan_mask = np.isnan(data)
            # 暖機期 bounds 無效 → pass-through 原值（非輸出 NaN）；僅 valid_bounds 列 clip。
            valid_bounds = np.isfinite(lower) & np.isfinite(upper)
            clipped = np.clip(data, lower, upper)
            data[valid_bounds] = clipped[valid_bounds]
            data[nan_mask] = np.nan
        elif causal_preprocessing:
            data = rolling_winsorize_array(
                data,
                winsor_lower_q,
                winsor_upper_q,
                window=winsor_window,
                min_periods=winsor_min_periods,
            )
        else:
            data = winsorize_array(data, winsor_lower_q, winsor_upper_q)

    if rank:
        # rank produces a fresh out array; safe to discard the prior `data`.
        data = _rolling_rank_numba(data, rank_window, _rolling_min_periods(rank_window))

    if zscore:
        mean, std = _rolling_mean_std(
            data,
            zscore_window,
            min_periods=_rolling_min_periods(zscore_window),
        )
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
