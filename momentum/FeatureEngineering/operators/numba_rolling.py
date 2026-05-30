from __future__ import annotations

import numba
import numpy as np


@numba.njit(cache=True)
def _welford_update(count: int, mean: float, m2: float, new_value: float) -> tuple[int, float, float]:
    """Update Welford state with a new value."""
    count += 1
    delta = new_value - mean
    mean += delta / count
    delta2 = new_value - mean
    m2 += delta * delta2
    return count, mean, m2


@numba.njit(cache=True)
def _welford_remove(count: int, mean: float, m2: float, old_value: float) -> tuple[int, float, float]:
    """Remove one value from Welford state (inverse update)."""
    count -= 1
    if count <= 0:
        return 0, 0.0, 0.0
    delta = old_value - mean
    mean -= delta / count
    delta2 = old_value - mean
    m2 -= delta * delta2
    if m2 < 0.0 and m2 > -1e-12:
        m2 = 0.0
    return count, mean, m2


@numba.njit(cache=True)
def _pebay_update(
    count: int,
    mean: float,
    m2: float,
    m3: float,
    m4: float,
    new_value: float,
) -> tuple[int, float, float, float, float]:
    """Update central moments (M2/M3/M4) using Pebay online equations."""
    prev_count = count
    count = prev_count + 1
    delta = new_value - mean
    delta_n = delta / count
    delta_n2 = delta_n * delta_n
    term1 = delta * delta_n * prev_count

    m4 = (
        m4
        + term1 * delta_n2 * (count * count - 3.0 * count + 3.0)
        + 6.0 * delta_n2 * m2
        - 4.0 * delta_n * m3
    )
    m3 = m3 + term1 * delta_n * (count - 2.0) - 3.0 * delta_n * m2
    m2 = m2 + term1
    mean = mean + delta_n

    if m2 < 0.0 and m2 > -1e-12:
        m2 = 0.0
    if m4 < 0.0 and m4 > -1e-10:
        m4 = 0.0

    return count, mean, m2, m3, m4


@numba.njit(cache=True)
def _pebay_remove(
    count: int,
    mean: float,
    m2: float,
    m3: float,
    m4: float,
    old_value: float,
) -> tuple[int, float, float, float, float]:
    """Remove one value from Pebay central moments for sliding windows."""
    if count <= 1:
        return 0, 0.0, 0.0, 0.0, 0.0

    n = float(count)
    next_count = count - 1
    next_n = float(next_count)

    next_mean = (n * mean - old_value) / next_n
    delta = old_value - next_mean

    next_m2 = m2 - (delta * delta) * (next_n / n)
    if next_m2 < 0.0 and next_m2 > -1e-12:
        next_m2 = 0.0

    next_m3 = (
        m3
        - (delta * delta * delta) * (next_n * (n - 2.0) / (n * n))
        + 3.0 * delta * next_m2 / n
    )

    next_m4 = (
        m4
        - (delta ** 4) * next_n * (n * n - 3.0 * n + 3.0) / (n * n * n)
        - 6.0 * (delta * delta) * next_m2 / (n * n)
        + 4.0 * delta * next_m3 / n
    )

    if next_m2 < 0.0 and next_m2 > -1e-12:
        next_m2 = 0.0
    if next_m4 < 0.0 and next_m4 > -1e-10:
        next_m4 = 0.0

    return next_count, next_mean, next_m2, next_m3, next_m4


@numba.njit(cache=True)
def _batch_recompute_moments(
    ring_values: np.ndarray,
    ring_valid: np.ndarray,
) -> tuple[int, float, float, float, float]:
    """Recompute moments from ring-buffer values to correct numeric drift."""
    count = 0
    mean = 0.0
    m2 = 0.0
    m3 = 0.0
    m4 = 0.0

    for idx in range(ring_values.shape[0]):
        if ring_valid[idx] == 1:
            count, mean, m2, m3, m4 = _pebay_update(count, mean, m2, m3, m4, ring_values[idx])

    return count, mean, m2, m3, m4


# Two complementary guards make higher moments numerically safe across ALL data:
#
# (1) Relative degeneracy guard — a window is "effectively constant" (skew/kurt
#     undefined → NaN) when its summed 2nd central moment m2 is negligible
#     relative to Σx² = m2 + count·mean². Scale-invariant; catches constant runs
#     whose incremental m2 drifts to float-noise (e.g. EMA/HT-TRENDMODE all-equal
#     → m2≈1e-30 → leaks a spurious ~1e-15 skew without this).
#
# (2) Exact mathematical sample bound — for n real observations the bias-corrected
#     sample moments satisfy |skewness| ≤ √n and -2 ≤ excess_kurtosis ≤ n (attained
#     by the "n-1 equal + 1 outlier" extremal window). Any value beyond is
#     mathematically impossible for n real points → pure floating-point garbage.
#     This is centring-INDEPENDENT, so it catches the explosion on zero-centred
#     data (microstructure spread) where guard (1) degenerates (Σx²≈m2).
#
# Together they cover both failure modes; the genuine max |skew|=√55=7.4162 on a
# 54:1 window is preserved.
_MOMENT_REL_EPS: float = 1e-12
_MOMENT_BOUND_TOL: float = 1e-9


@numba.njit(cache=True)
def _compute_skew(m2: float, m3: float, count: int, mean: float) -> float:
    """Sample skewness with degeneracy guard + exact |skew| ≤ √n bound."""
    if count < 3 or m2 <= 0.0:
        return np.nan
    sumsq = m2 + count * mean * mean  # Σx², scale anchor
    if m2 <= _MOMENT_REL_EPS * sumsq:
        return np.nan  # effectively-constant window → undefined

    n = float(count)
    result = (n * np.sqrt(n - 1.0) / (n - 2.0)) * (m3 / (m2 ** 1.5))
    bound = np.sqrt(n)
    if not np.isfinite(result) or abs(result) > bound * (1.0 + _MOMENT_BOUND_TOL):
        return np.nan  # beyond the exact sample bound → numerical garbage
    return result


@numba.njit(cache=True)
def _compute_kurt(m2: float, m4: float, count: int, mean: float) -> float:
    """Sample excess kurtosis with degeneracy guard + exact -2 ≤ k ≤ n bound."""
    if count < 4 or m2 <= 0.0:
        return np.nan
    sumsq = m2 + count * mean * mean
    if m2 <= _MOMENT_REL_EPS * sumsq:
        return np.nan  # effectively-constant window → undefined

    n = float(count)
    excess = n * m4 / (m2 * m2) - 3.0
    result = ((n - 1.0) / ((n - 2.0) * (n - 3.0))) * ((n + 1.0) * excess + 6.0)
    # Exact bounds for the bias-corrected sample excess kurtosis:
    #   upper = n  (n-1 equal + 1 outlier);  lower = -2(n-1)/(n-3)  (perfect bimodal,
    #   = -4 at n=5, → -2 as n→∞). Beyond these is numerically impossible.
    upper = n
    lower = -2.0 * (n - 1.0) / (n - 3.0)
    if (
        not np.isfinite(result)
        or result > upper * (1.0 + _MOMENT_BOUND_TOL)
        or result < lower * (1.0 + _MOMENT_BOUND_TOL)
    ):
        return np.nan  # outside the exact sample bound → numerical garbage
    return result


@numba.njit(cache=True)
def _bisect_left(values: np.ndarray, size: int, target: float) -> int:
    low = 0
    high = size
    while low < high:
        mid = (low + high) // 2
        if values[mid] < target:
            low = mid + 1
        else:
            high = mid
    return low


@numba.njit(cache=True)
def _bisect_right(values: np.ndarray, size: int, target: float) -> int:
    low = 0
    high = size
    while low < high:
        mid = (low + high) // 2
        if target < values[mid]:
            high = mid
        else:
            low = mid + 1
    return low


@numba.njit(cache=True)
def _insert_sorted(sorted_buf: np.ndarray, buf_len: int, value: float) -> int:
    insert_pos = _bisect_left(sorted_buf, buf_len, value)
    for idx in range(buf_len, insert_pos, -1):
        sorted_buf[idx] = sorted_buf[idx - 1]
    sorted_buf[insert_pos] = value
    return buf_len + 1


@numba.njit(cache=True)
def _remove_sorted(sorted_buf: np.ndarray, buf_len: int, value: float) -> int:
    remove_pos = _bisect_left(sorted_buf, buf_len, value)
    while remove_pos < buf_len and sorted_buf[remove_pos] != value:
        remove_pos += 1
    if remove_pos >= buf_len:
        for idx in range(buf_len):
            if sorted_buf[idx] == value:
                remove_pos = idx
                break
    if remove_pos >= buf_len:
        return buf_len

    for idx in range(remove_pos, buf_len - 1):
        sorted_buf[idx] = sorted_buf[idx + 1]
    return buf_len - 1


@numba.njit(cache=True)
def fused_rolling_stats(data: np.ndarray, window: int) -> np.ndarray:
    """Single-pass rolling stats with pandas-compatible min_periods=window semantics."""
    if window <= 0:
        raise ValueError("window must be positive")

    n_rows = len(data)
    output = np.full((n_rows, 6), np.nan, dtype=np.float64)
    if n_rows == 0:
        return output.astype(np.float32)

    ring_values = np.empty(window, dtype=np.float64)
    ring_valid = np.zeros(window, dtype=np.uint8)

    min_deque = np.empty(n_rows, dtype=np.int64)
    max_deque = np.empty(n_rows, dtype=np.int64)
    min_head = 0
    min_tail = 0
    max_head = 0
    max_tail = 0

    count = 0
    mean = 0.0
    m2 = 0.0

    for row_idx in range(n_rows):
        slot = row_idx % window

        if row_idx >= window:
            old_idx = row_idx - window
            if ring_valid[slot] == 1:
                old_value = ring_values[slot]
                count, mean, m2 = _welford_remove(count, mean, m2, old_value)

            while min_head < min_tail and min_deque[min_head] <= old_idx:
                min_head += 1
            while max_head < max_tail and max_deque[max_head] <= old_idx:
                max_head += 1

        value = data[row_idx]
        if np.isnan(value):
            ring_valid[slot] = 0
            ring_values[slot] = np.nan
        else:
            ring_valid[slot] = 1
            ring_values[slot] = value
            count, mean, m2 = _welford_update(count, mean, m2, value)

            while min_head < min_tail and data[min_deque[min_tail - 1]] >= value:
                min_tail -= 1
            min_deque[min_tail] = row_idx
            min_tail += 1

            while max_head < max_tail and data[max_deque[max_tail - 1]] <= value:
                max_tail -= 1
            max_deque[max_tail] = row_idx
            max_tail += 1

        if row_idx >= window - 1 and count >= window:
            min_value = data[min_deque[min_head]]
            max_value = data[max_deque[max_head]]

            output[row_idx, 0] = mean

            if count > 1:
                variance = m2 / (count - 1)
                if variance < 0.0 and variance > -1e-12:
                    variance = 0.0
                std_value = np.sqrt(variance) if variance >= 0.0 else np.nan
            else:
                std_value = np.nan

            output[row_idx, 1] = std_value
            output[row_idx, 2] = min_value
            output[row_idx, 3] = max_value
            output[row_idx, 4] = max_value - min_value

            if np.isnan(std_value) or std_value <= 0.0:
                output[row_idx, 5] = np.nan
            else:
                output[row_idx, 5] = (value - mean) / std_value

    return output.astype(np.float32)


@numba.njit(cache=True)
def rolling_rank(data: np.ndarray, window: int) -> np.ndarray:
    """Rolling percentile rank for the latest value with average-tie semantics."""
    if window <= 0:
        raise ValueError("window must be positive")

    n_rows = len(data)
    output = np.full(n_rows, np.nan, dtype=np.float64)
    if n_rows == 0:
        return output.astype(np.float32)

    sorted_buf = np.empty(window, dtype=np.float64)
    ring_values = np.empty(window, dtype=np.float64)
    ring_valid = np.zeros(window, dtype=np.uint8)
    buf_len = 0

    for row_idx in range(n_rows):
        slot = row_idx % window

        if row_idx >= window and ring_valid[slot] == 1:
            buf_len = _remove_sorted(sorted_buf, buf_len, ring_values[slot])

        value = data[row_idx]
        if np.isnan(value):
            ring_valid[slot] = 0
            ring_values[slot] = np.nan
        else:
            ring_valid[slot] = 1
            ring_values[slot] = value
            buf_len = _insert_sorted(sorted_buf, buf_len, value)

        if row_idx >= window - 1 and buf_len >= window and not np.isnan(value):
            left = _bisect_left(sorted_buf, buf_len, value)
            right = _bisect_right(sorted_buf, buf_len, value)
            average_rank = (left + right - 1.0) / 2.0 + 1.0
            output[row_idx] = average_rank / float(buf_len)

    return output.astype(np.float32)


@numba.njit(cache=True)
def rolling_slope(data: np.ndarray, window: int) -> np.ndarray:
    """Rolling OLS slope using running sums and 0-based x positions."""
    if window <= 0:
        raise ValueError("window must be positive")

    n_rows = len(data)
    output = np.full(n_rows, np.nan, dtype=np.float64)
    if n_rows == 0:
        return output.astype(np.float32)

    w = float(window)
    sum_x = w * (w - 1.0) / 2.0
    sum_x2 = w * (w - 1.0) * (2.0 * w - 1.0) / 6.0
    denominator = w * sum_x2 - sum_x * sum_x
    if denominator == 0.0:
        return output.astype(np.float32)

    ring_values = np.empty(window, dtype=np.float64)
    ring_valid = np.zeros(window, dtype=np.uint8)

    sum_y = 0.0
    sum_jy = 0.0
    valid_count = 0

    for row_idx in range(n_rows):
        slot = row_idx % window

        if row_idx >= window and ring_valid[slot] == 1:
            old_value = ring_values[slot]
            old_index = row_idx - window
            sum_y -= old_value
            sum_jy -= float(old_index) * old_value
            valid_count -= 1

        value = data[row_idx]
        if np.isnan(value):
            ring_valid[slot] = 0
            ring_values[slot] = np.nan
        else:
            ring_valid[slot] = 1
            ring_values[slot] = value
            sum_y += value
            sum_jy += float(row_idx) * value
            valid_count += 1

        if row_idx >= window - 1 and valid_count >= window and not np.isnan(value):
            start_idx = row_idx - window + 1
            sum_xy = sum_jy - float(start_idx) * sum_y
            output[row_idx] = (w * sum_xy - sum_x * sum_y) / denominator

    return output.astype(np.float32)


@numba.njit(cache=True)
def rolling_skew_kurt(data: np.ndarray, window: int, recalc_interval: int = 50) -> np.ndarray:
    """Rolling skew/kurt with Pebay updates and periodic exact recalibration."""
    if window <= 0:
        raise ValueError("window must be positive")

    n_rows = len(data)
    output = np.full((n_rows, 2), np.nan, dtype=np.float64)
    if n_rows == 0:
        return output.astype(np.float32)

    ring_values = np.empty(window, dtype=np.float64)
    ring_valid = np.zeros(window, dtype=np.uint8)

    if recalc_interval <= 0:
        effective_recalc = window
    elif recalc_interval < window:
        effective_recalc = recalc_interval
    else:
        effective_recalc = window

    count = 0
    mean = 0.0
    m2 = 0.0
    m3 = 0.0
    m4 = 0.0

    for row_idx in range(n_rows):
        slot = row_idx % window

        if row_idx >= window and ring_valid[slot] == 1:
            count, mean, m2, m3, m4 = _pebay_remove(count, mean, m2, m3, m4, ring_values[slot])

        value = data[row_idx]
        if np.isnan(value):
            ring_valid[slot] = 0
            ring_values[slot] = np.nan
        else:
            ring_valid[slot] = 1
            ring_values[slot] = value
            count, mean, m2, m3, m4 = _pebay_update(count, mean, m2, m3, m4, value)

        if (row_idx + 1) % effective_recalc == 0:
            count, mean, m2, m3, m4 = _batch_recompute_moments(ring_values, ring_valid)

        if row_idx >= window - 1 and count >= window:
            output[row_idx, 0] = _compute_skew(m2, m3, count, mean)
            output[row_idx, 1] = _compute_kurt(m2, m4, count, mean)

    return output.astype(np.float32)


@numba.njit(cache=True)
def fused_rolling_stats_multi_window(values: np.ndarray, windows: np.ndarray) -> np.ndarray:
    """Compute rolling stats for multiple windows with a single Python/Numpy call.

    Output layout on the last axis:
    mean, std, min, max, range, zscore, skew, kurt, rank, slope.
    """
    n_rows = len(values)
    n_windows = windows.shape[0]
    output = np.full((n_rows, n_windows, 10), np.nan, dtype=np.float64)

    if n_windows == 0:
        return output

    for window_idx in range(n_windows):
        window = int(windows[window_idx])
        if window <= 0:
            continue

        fused = fused_rolling_stats(values, window).astype(np.float64)
        skew_kurt = rolling_skew_kurt(values, window).astype(np.float64)
        rank = rolling_rank(values, window).astype(np.float64)
        slope = rolling_slope(values, window).astype(np.float64)

        output[:, window_idx, 0:6] = fused
        output[:, window_idx, 6] = skew_kurt[:, 0]
        output[:, window_idx, 7] = skew_kurt[:, 1]
        output[:, window_idx, 8] = rank
        output[:, window_idx, 9] = slope

    return output


__all__ = [
    "fused_rolling_stats",
    "fused_rolling_stats_multi_window",
    "rolling_rank",
    "rolling_slope",
    "rolling_skew_kurt",
    "warmup_numba",
]


def warmup_numba() -> None:
    """Warm up cached rolling kernels in the main process."""

    dummy = np.random.randn(64).astype(np.float64)
    fused_rolling_stats(dummy, 5)
    fused_rolling_stats_multi_window(dummy, np.array([5, 13, 21], dtype=np.int32))
    rolling_rank(dummy, 5)
    rolling_slope(dummy, 5)
    rolling_skew_kurt(dummy, 5, 10)