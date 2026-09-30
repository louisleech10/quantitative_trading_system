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
def _window_moments(data: np.ndarray, end: int, window: int) -> tuple[bool, float, float, float, float, float, float]:
    """`data[end-window+1 .. end]` 之逐窗精確統計（FFSTAT v50）：固定由左至右之順序、float64 二遍法。

    回傳 (全有效, mean, m2, m3, m4, min, max)；窗內任一 NaN ⇒ 全有效＝False。常數窗（max＝min）之 m2／m3／m4
    明定為 0（二遍法於相同值之和仍可能有末位誤差而使 x−mean≠0）。每列只讀該窗之值 ⇒ 與起算點無關。"""
    start = end - window + 1
    total = 0.0
    vmin = data[start]
    vmax = vmin
    for j in range(start, end + 1):
        v = data[j]
        if np.isnan(v):
            return False, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
        total += v
        if v < vmin:
            vmin = v
        if v > vmax:
            vmax = v
    mean = total / window
    if vmax == vmin:
        return True, mean, 0.0, 0.0, 0.0, vmin, vmax
    m2 = 0.0
    m3 = 0.0
    m4 = 0.0
    for j in range(start, end + 1):
        d = data[j] - mean
        d2 = d * d
        m2 += d2
        m3 += d2 * d
        m4 += d2 * d2
    return True, mean, m2, m3, m4, vmin, vmax


@numba.njit(cache=True)
def fused_rolling_stats(data: np.ndarray, window: int) -> np.ndarray:
    """Rolling mean／std／min／max／range／zscore with pandas-compatible min_periods=window semantics.

    FFSTAT v50：逐窗精確計算（`_window_moments`），取代 Welford 增量加入／移除——後者之捨入誤差依首個有限值之
    位置累積（值依起算點而異），且常數窗算出非零 std（真實 BTC 1h `MIDPOINT_21` W5 之 4,546 個常數窗全數非零）。
    常數窗 std＝0、zscore＝NaN；窗內任一 NaN ⇒ 該列全 NaN（同改前）。"""
    if window <= 0:
        raise ValueError("window must be positive")

    n_rows = len(data)
    output = np.full((n_rows, 6), np.nan, dtype=np.float64)
    if n_rows == 0:
        return output.astype(np.float32)

    for row_idx in range(window - 1, n_rows):
        valid, mean, m2, _m3, _m4, min_value, max_value = _window_moments(data, row_idx, window)
        if not valid:
            continue
        output[row_idx, 0] = mean
        std_value = np.sqrt(m2 / (window - 1)) if window > 1 else np.nan
        output[row_idx, 1] = std_value
        output[row_idx, 2] = min_value
        output[row_idx, 3] = max_value
        output[row_idx, 4] = max_value - min_value
        if np.isnan(std_value) or std_value <= 0.0:
            output[row_idx, 5] = np.nan
        else:
            output[row_idx, 5] = (data[row_idx] - mean) / std_value

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
    """Rolling OLS slope（窗內 x＝0..w−1）。

    FFSTAT v51（審查 r35 前主委實跑 §G⑦ 分解判準所得）：逐窗精確計算——窗內固定由左至右之 float64 二遍法
    Σ(j−x̄)(y_j−ȳ)／Σ(j−x̄)²，取代以「絕對列號」累加之 running sums（`sum_jy += row_idx*value`，其捨入誤差隨列號
    增長、值依起算點而異：真實 BTC 4h STOCHRSI-fastd 之 Slope 於刪前 2,049 列重算時末位不同）。窗內任一 NaN ⇒ NaN。"""
    if window <= 0:
        raise ValueError("window must be positive")

    n_rows = len(data)
    output = np.full(n_rows, np.nan, dtype=np.float64)
    if n_rows == 0 or window < 2:
        return output.astype(np.float32)

    w = float(window)
    x_mean = (w - 1.0) / 2.0
    sxx = w * (w * w - 1.0) / 12.0  # Σ(j−x̄)²

    for row_idx in range(window - 1, n_rows):
        start = row_idx - window + 1
        total = 0.0
        valid = True
        for j in range(start, row_idx + 1):
            value = data[j]
            if np.isnan(value):
                valid = False
                break
            total += value
        if not valid:
            continue
        y_mean = total / w
        sxy = 0.0
        for j in range(window):
            sxy += (float(j) - x_mean) * (data[start + j] - y_mean)
        output[row_idx] = sxy / sxx

    return output.astype(np.float32)


@numba.njit(cache=True)
def rolling_skew_kurt(data: np.ndarray, window: int, recalc_interval: int = 50) -> np.ndarray:
    """Rolling skew/kurt（樣本偏態／超額峰度，公式與退化防護同 `_compute_skew`／`_compute_kurt`）。

    FFSTAT v50：逐窗精確計算（`_window_moments`），取代 Pebay 增量＋依絕對列位每 `recalc_interval` 列重算——後者之值
    依起算點（首列位置與重算相位）而異。`recalc_interval` 保留為相容參數、不再使用。"""
    if window <= 0:
        raise ValueError("window must be positive")

    n_rows = len(data)
    output = np.full((n_rows, 2), np.nan, dtype=np.float64)
    if n_rows == 0:
        return output.astype(np.float32)

    for row_idx in range(window - 1, n_rows):
        valid, mean, m2, m3, m4, _vmin, _vmax = _window_moments(data, row_idx, window)
        if not valid:
            continue
        output[row_idx, 0] = _compute_skew(m2, m3, window, mean)
        output[row_idx, 1] = _compute_kurt(m2, m4, window, mean)

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