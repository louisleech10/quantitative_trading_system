"""Numba-accelerated L6.5 transforms for CGSA per-group processing.

These operate on raw numpy float32 arrays and avoid pandas overhead entirely.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
from momentum.core.logging import get_logger
from momentum.FeatureEngineering.preprocessing import stable_mask as _stable_mask

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
            here. It is **incompatible** with an L6.5 outer ThreadPool
            (registry 群組平行轉換；該入口已於 FFPROD Task 1.1 刪除) under the
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

    @njit(cache=True)
    def _rolling_quantile_sliding_numba(
        arr: np.ndarray,
        lower_q: float,
        upper_q: float,
        window: int,
        min_periods: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """以滑動有序視窗計算逐欄因果分位數。"""
        n_rows, n_cols = arr.shape
        lower = np.empty((n_rows, n_cols), dtype=np.float32)
        upper = np.empty((n_rows, n_cols), dtype=np.float32)
        lower[:] = np.nan
        upper[:] = np.nan

        for c in range(n_cols):
            # 容量 window+1:r>=window 時先 insert(count 瞬達 window+1)後 remove,
            # 多留一格避免 numba 無邊界檢查的瞬態越界寫(Composer review MAJOR)。
            sorted_vals = np.empty(window + 1, dtype=np.float64)
            count = 0
            for r in range(n_rows):
                value = arr[r, c]
                if not np.isnan(value) and np.isfinite(value):
                    # Upper-bound insertion preserves input order among equal values,
                    # including the byte-distinct +0.0 and -0.0 values.
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
                        # Equal values are chronological because insertion uses upper bound;
                        # the outgoing observation is therefore the first equal element.
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
    # 預設 sliding(byte-identical 已三方簽核 + e2e 雙路徑 19-20x 驗證);
    # FFACT_ROLLING_QUANTILE_KERNEL=legacy 一鍵回退舊 full-sort kernel。
    if _HAS_NUMBA and os.getenv("FFACT_ROLLING_QUANTILE_KERNEL", "sliding") != "legacy":
        return _rolling_quantile_sliding_numba(
            data, float(lower_q), float(upper_q), int(window), int(min_periods)
        )
    return _rolling_quantile_numba(data, float(lower_q), float(upper_q), int(window), int(min_periods))


# ---------------------------------------------------------------------------
# Winsorization (quantile clipping) — pure numpy
# ---------------------------------------------------------------------------

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
    # FFSTAT Task 2.3 第①類（R6 甲）：窗未湊滿之列（自首個有限值起 window−1 列）遮為 NaN；計算本身不變
    _stable_mask.mask_incomplete_window_inplace(arr, window)
    return arr


# ---------------------------------------------------------------------------
# Combined fast transform for CGSA per-group
# ---------------------------------------------------------------------------

def transform_array_fast(
    arr: np.ndarray,
    *,
    winsorize: bool = True,
    winsor_method: Optional[str] = None,
    winsor_lower_q: float = 0.01,
    winsor_upper_q: float = 0.99,
    winsor_sigma_k: float = 3.0,
    causal_preprocessing: bool = True,
    winsor_window: int = 252,
    winsor_min_periods: int = 63,
) -> np.ndarray:
    """Apply the L6.5 winsorize step on a raw float32 array (rows × cols); returns float32 of same shape.

    FFPROD Task 1.1：快速核心只服務 raw 生成（registry 路徑），raw 之 L6.5 一律關 rank／zscore／gaussian
    （`feature_factory._build_l7_raw_preprocessing_config`），故核心只保留縮尾步；rank／zscore 之生產實作在 pandas 核心。
    """
    if not causal_preprocessing:
        # FFSTAT v53（審查 r36 codex P1-02）：全欄 nanmean／nanstd／nanquantile 分支＝未來洩漏（且 sigma 分支之廣播
        # 於實跑拋 IndexError）；生成路徑早已釘死因果，直接呼叫亦 fail-closed
        raise ValueError("非因果前處理（causal_preprocessing=False）已移除：全欄統計量含未來資料")
    # NUMVIEW Task 2.1（審碼 b3 r1）：核心不再以預設 method 補值——啟用之步驟須明給
    if winsorize and winsor_method is None:
        from momentum.FeatureEngineering.numeric_view import NumericPolicyError

        raise NumericPolicyError("快速核心：縮尾啟用須明給 winsor_method（不以預設補值）")
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
            if causal_preprocessing:
                # FFSTAT Task 2.3 第①類（R6 甲）：窗未湊滿之列遮為 NaN（quantile 分支於 rolling_winsorize_array 內）
                _stable_mask.mask_incomplete_window_inplace(data, winsor_window)
        elif winsor_method == "quantile":
            # NUMVIEW Task 2.1：明列 quantile 分支（改前 `elif causal_preprocessing` ＝ 非 sigma 之任何值一律走 quantile）；
            # 非因果已於函式開頭拒收
            data = rolling_winsorize_array(
                data,
                winsor_lower_q,
                winsor_upper_q,
                window=winsor_window,
                min_periods=winsor_min_periods,
            )
        else:
            from momentum.FeatureEngineering.numeric_view import NumericPolicyError

            raise NumericPolicyError(f"縮尾 method={winsor_method!r} 不屬契約 winsor_method_values（快速核心）")

    return data


def warmup_numba() -> None:
    """JIT-compile numba kernels with a tiny dummy array."""
    if not _HAS_NUMBA:
        return
    dummy = np.random.randn(10, 2).astype(np.float32)
    _ = _rolling_rank_numba(dummy, 5)
    logger.info("[L6.5] numba rolling_rank JIT warmup done")
