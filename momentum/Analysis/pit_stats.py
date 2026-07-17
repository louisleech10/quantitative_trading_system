"""PIT (point-in-time) 統計原語家族 — LA-0 B1。

七原語 + per-bar validity mask。min_samples / first_valid 唯一權威 = SPEC §MS：
  effective_count(t) = series[0..t] 非 NaN 數
  valid(t) ⟺ effective_count(t) ≥ min_samples
  first_valid = min{t : effective_count(t) ≥ min_samples}  # dense → t=min_samples-1
  禁 hard-code index=min_samples

current-inclusive：每個 t 的統計含當前 bar。
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple, Union

import numpy as np
import pandas as pd

try:
    from numba import njit

    _HAS_NUMBA = True
except ImportError:  # pragma: no cover
    _HAS_NUMBA = False

    def njit(*args, **kwargs):  # type: ignore[misc]
        def _decorator(fn):
            return fn

        if args and callable(args[0]):
            return args[0]
        return _decorator


# ---------------------------------------------------------------------------
# 常數（簽名鎖）
# ---------------------------------------------------------------------------
PIT_STATS_VERSION: str = "la0_b1_v1"
MIN_SAMPLES: int = 100  # canonical §MS
DEFAULT_CHUNK_FEATURES: int = 256

ArrayLike = Union[pd.Series, np.ndarray]
MaskLike = Union[pd.Series, np.ndarray]


# ---------------------------------------------------------------------------
# §MS helpers
# ---------------------------------------------------------------------------
def effective_count(series: ArrayLike) -> np.ndarray:
    """回傳 per-t 累積非 NaN 計數，shape=(n,)。current-inclusive。"""
    values = _as_1d_float(series)
    return np.cumsum(~np.isnan(values), dtype=np.int64)


def first_valid_index(
    series: ArrayLike,
    min_samples: int = MIN_SAMPLES,
) -> Optional[int]:
    """依 §MS 計算 first_valid；無有效 bar 回 None。禁 hard-code index。"""
    if min_samples < 1:
        raise ValueError("min_samples must be >= 1")
    counts = effective_count(series)
    hits = np.flatnonzero(counts >= int(min_samples))
    if hits.size == 0:
        return None
    return int(hits[0])


def pit_valid_mask(
    series: ArrayLike,
    min_samples: int = MIN_SAMPLES,
) -> pd.Series:
    """per-bar validity：effective_count(t) ≥ min_samples。index 對齊輸入。"""
    index = _index_of(series)
    counts = effective_count(series)
    mask = counts >= int(min_samples)
    return pd.Series(mask, index=index, name="validity_mask", dtype=bool)


# ---------------------------------------------------------------------------
# 1. rolling_window_rank_corr
# ---------------------------------------------------------------------------
def rolling_window_rank_corr(
    x: np.ndarray,
    y: np.ndarray,
    window: int,
    stride: int,
    ties: str = "average",
    *,
    chunk_size: Optional[int] = DEFAULT_CHUNK_FEATURES,
    use_numba: bool = True,
) -> np.ndarray:
    """每窗內跨特徵向量化 rank + batch pearson corr（= spearman）。

    凍結位置參數語意：``(x, y, window, stride, ties='average')``。
    ``chunk_size`` / ``use_numba`` = RULING-1/T4 允許擴展（keyword-only），
    不改凍結位置參數語意。

    Parameters
    ----------
    x : (n_bars, n_features)
    y : (n_bars,)
    window, stride : 窗長與步幅
    ties : 僅支援 "average"（與 pandas rank 對齊）
    chunk_size : RULING-1/T4 允許擴展；特徵分批大小；None 或 >= n_features → 不分批
    use_numba : RULING-1/T4 允許擴展；True 走 Numba；False 走純 numpy（equivalence test）

    Returns
    -------
    np.ndarray, shape (n_emitted, n_features)
        emitted ends = window-1, window-1+stride, ... (< n)
    """
    if ties != "average":
        raise ValueError(f"only ties='average' supported, got {ties!r}")
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    if x_arr.ndim != 2:
        raise ValueError(f"x must be 2D (n_bars, n_features), got shape {x_arr.shape}")
    if y_arr.ndim != 1:
        raise ValueError(f"y must be 1D (n_bars,), got shape {y_arr.shape}")
    if x_arr.shape[0] != y_arr.shape[0]:
        raise ValueError("x and y must share the same length (axis 0)")
    if window <= 1:
        return np.empty((0, x_arr.shape[1]), dtype=np.float64)
    if stride < 1:
        raise ValueError("stride must be >= 1")

    n_bars, n_features = x_arr.shape
    if n_bars < window:
        return np.empty((0, n_features), dtype=np.float64)

    if chunk_size is None or chunk_size <= 0 or chunk_size >= n_features:
        return _rolling_window_rank_corr_impl(
            x_arr, y_arr, window, stride, use_numba=use_numba
        )

    parts: list[np.ndarray] = []
    for start in range(0, n_features, int(chunk_size)):
        end = min(start + int(chunk_size), n_features)
        parts.append(
            _rolling_window_rank_corr_impl(
                x_arr[:, start:end],
                y_arr,
                window,
                stride,
                use_numba=use_numba,
            )
        )
    return np.concatenate(parts, axis=1)


def _rolling_window_rank_corr_impl(
    x: np.ndarray,
    y: np.ndarray,
    window: int,
    stride: int,
    *,
    use_numba: bool,
) -> np.ndarray:
    if use_numba and _HAS_NUMBA:
        return _rolling_window_rank_corr_numba(x, y, int(window), int(stride))
    return _rolling_window_rank_corr_numpy(x, y, int(window), int(stride))


def _rolling_window_rank_corr_numpy(
    x: np.ndarray,
    y: np.ndarray,
    window: int,
    stride: int,
) -> np.ndarray:
    """純 numpy/pandas 參考路徑：每窗 DataFrame.rank + batch corr。"""
    n_bars, n_features = x.shape
    starts = np.arange(0, n_bars - window + 1, stride)
    n_out = len(starts)
    out = np.empty((n_out, n_features), dtype=np.float64)

    for oi, start in enumerate(starts):
        end = start + window
        x_win = x[start:end]
        y_win = y[start:end]
        if not np.isfinite(y_win).all():
            out[oi, :] = np.nan
            continue
        ry = pd.Series(y_win).rank(method="average").to_numpy(dtype=np.float64)
        y_std = float(np.std(ry, ddof=0))
        if y_std == 0.0 or not np.isfinite(y_std):
            out[oi, :] = np.nan
            continue
        rx = pd.DataFrame(x_win).rank(axis=0, method="average").to_numpy(dtype=np.float64)
        # 任欄有 NaN（源自 x NaN）→ 該 corr NaN
        nan_col = ~np.isfinite(x_win).all(axis=0)
        # batch pearson: corr = cov(rx, ry) / (std_rx * std_ry)
        rx_mean = rx.mean(axis=0)
        ry_mean = float(ry.mean())
        rx_c = rx - rx_mean
        ry_c = ry - ry_mean
        cov = (rx_c * ry_c[:, None]).sum(axis=0) / window
        std_x = np.sqrt((rx_c * rx_c).sum(axis=0) / window)
        std_y = float(np.sqrt((ry_c * ry_c).sum() / window))
        with np.errstate(divide="ignore", invalid="ignore"):
            corr = cov / (std_x * std_y)
        corr[~np.isfinite(corr)] = np.nan
        corr[nan_col] = np.nan
        # zero-variance x column
        corr[std_x == 0.0] = np.nan
        out[oi, :] = corr
    return out


@njit(cache=True)
def _rank_average_1d(arr: np.ndarray) -> np.ndarray:
    """1-based average ranks（對齊 pandas rank method='average'）。"""
    n = arr.shape[0]
    order = np.argsort(arr)
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and arr[order[j + 1]] == arr[order[i]]:
            j += 1
        # ranks (i+1)..(j+1) average
        avg = 0.5 * (float(i + 1) + float(j + 1))
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


@njit(cache=True)
def _pearson_1d(a: np.ndarray, b: np.ndarray) -> float:
    n = a.shape[0]
    if n < 2:
        return np.nan
    mean_a = 0.0
    mean_b = 0.0
    for i in range(n):
        mean_a += a[i]
        mean_b += b[i]
    mean_a /= n
    mean_b /= n
    cov = 0.0
    var_a = 0.0
    var_b = 0.0
    for i in range(n):
        da = a[i] - mean_a
        db = b[i] - mean_b
        cov += da * db
        var_a += da * da
        var_b += db * db
    if var_a <= 0.0 or var_b <= 0.0:
        return np.nan
    return cov / np.sqrt(var_a * var_b)


@njit(cache=True)
def _rolling_window_rank_corr_numba(
    x: np.ndarray,
    y: np.ndarray,
    window: int,
    stride: int,
) -> np.ndarray:
    n_bars, n_features = x.shape
    n_out = (n_bars - window) // stride + 1
    out = np.empty((n_out, n_features), dtype=np.float64)

    for oi in range(n_out):
        start = oi * stride
        end = start + window
        y_win = y[start:end]
        y_ok = True
        for i in range(window):
            if not np.isfinite(y_win[i]):
                y_ok = False
                break
        if not y_ok:
            for fi in range(n_features):
                out[oi, fi] = np.nan
            continue
        ry = _rank_average_1d(y_win)
        # y constant after rank?
        y_const = True
        for i in range(1, window):
            if ry[i] != ry[0]:
                y_const = False
                break
        if y_const:
            for fi in range(n_features):
                out[oi, fi] = np.nan
            continue

        for fi in range(n_features):
            x_ok = True
            x_win = np.empty(window, dtype=np.float64)
            for i in range(window):
                v = x[start + i, fi]
                if not np.isfinite(v):
                    x_ok = False
                    break
                x_win[i] = v
            if not x_ok:
                out[oi, fi] = np.nan
                continue
            rx = _rank_average_1d(x_win)
            out[oi, fi] = _pearson_1d(rx, ry)
    return out


# ---------------------------------------------------------------------------
# 2. pit_expanding_qcut_label
# ---------------------------------------------------------------------------
def pit_expanding_qcut_label(
    series: ArrayLike,
    q: int,
    min_samples: int = MIN_SAMPLES,
    duplicates: str = "drop",
    require_full_q: bool = False,
) -> pd.Series:
    """per-t expanding qcut → 當前 bar 分位 **label**（非分位值）。

    effective_count(t) < min_samples → NaN（§MS，非 t < min_samples）。

    Parameters
    ----------
    require_full_q:
        True 且該 t 實際 bin 數 ``nunique < q`` → 當根 NaN（Policy-Strict）。
        預設 False = 舊行為（duplicates='drop' 後可能 label 落在 reduced bins）。
    """
    index = _index_of(series)
    values = _as_1d_float(series)
    n = values.shape[0]
    out = np.full(n, np.nan, dtype=np.float64)
    if n == 0:
        return pd.Series(out, index=index, dtype=float)

    q = int(q)
    if q < 2:
        raise ValueError("q must be >= 2")

    counts = effective_count(values)
    for t in range(n):
        if counts[t] < min_samples:
            continue
        if not np.isfinite(values[t]):
            continue
        hist = values[: t + 1]
        finite = hist[np.isfinite(hist)]
        try:
            # labels=False → integer bin ids 0..
            bins = pd.qcut(finite, q=q, labels=False, duplicates=duplicates)
        except ValueError:
            continue
        bins_arr = bins.to_numpy() if isinstance(bins, pd.Series) else np.asarray(bins)
        if require_full_q:
            # 實際可分 bin 數不足 q → 當根 NaN（Policy-Strict，LA-1）
            n_unique = int(pd.Series(bins_arr).nunique(dropna=True))
            if n_unique < q:
                continue
        # map current value's position among finite → last finite is current if finite
        # current is at end of hist; its rank among finite is the last finite entry
        # because we included t and values[t] is finite.
        label = bins_arr[-1]
        if pd.isna(label):
            continue
        out[t] = float(label)
    return pd.Series(out, index=index, dtype=float)


# ---------------------------------------------------------------------------
# 3. pit_expanding_bounds
# ---------------------------------------------------------------------------
def pit_expanding_bounds(
    series: ArrayLike,
    lo_q: float,
    hi_q: float,
    min_samples: int = MIN_SAMPLES,
) -> Tuple[pd.Series, pd.Series]:
    """per-t expanding winsor 邊界 (lo, hi)。

    warmup（invalid）**唯一**回值 = (-inf, +inf)（no-clip）。
    lo_q / hi_q ∈ [0, 1]（分位數，如 0.01 / 0.99）。
    """
    index = _index_of(series)
    values = _as_1d_float(series)
    n = values.shape[0]
    lo_out = np.full(n, -np.inf, dtype=np.float64)
    hi_out = np.full(n, np.inf, dtype=np.float64)
    if n == 0:
        return (
            pd.Series(lo_out, index=index, dtype=float),
            pd.Series(hi_out, index=index, dtype=float),
        )

    if not (0.0 <= float(lo_q) < float(hi_q) <= 1.0):
        raise ValueError("require 0 <= lo_q < hi_q <= 1")

    counts = effective_count(values)
    for t in range(n):
        if counts[t] < min_samples:
            # warmup: keep (-inf, +inf)
            continue
        hist = values[: t + 1]
        finite = hist[np.isfinite(hist)]
        if finite.size == 0:
            continue
        lo_out[t] = float(np.quantile(finite, float(lo_q)))
        hi_out[t] = float(np.quantile(finite, float(hi_q)))
    return (
        pd.Series(lo_out, index=index, dtype=float),
        pd.Series(hi_out, index=index, dtype=float),
    )


# ---------------------------------------------------------------------------
# 3b. pit_expanding_quantile_thresholds（regime 契約薄 wrapper）
# ---------------------------------------------------------------------------
def pit_expanding_quantile_thresholds(
    series: ArrayLike,
    lo_q: float,
    hi_q: float,
    min_samples: int = MIN_SAMPLES,
) -> Tuple[pd.Series, pd.Series]:
    """regime 用 per-t expanding 分位門檻 (lo, hi)。

    內部零新演算法，直接委派 ``pit_expanding_bounds``。
    **regime 契約**：warmup（invalid）唯一回值 = ``(-inf, +inf)``，
    使 ``vol >= hi`` / ``vol <= lo`` 在 warmup 皆為 False（不進 high/low）。
    """
    return pit_expanding_bounds(
        series, lo_q=lo_q, hi_q=hi_q, min_samples=min_samples
    )


# ---------------------------------------------------------------------------
# 4. pit_expanding_rank
# ---------------------------------------------------------------------------
def pit_expanding_rank(
    series: ArrayLike,
    min_samples: int = MIN_SAMPLES,
    ties: str = "average",
) -> pd.Series:
    """per-t 當前 bar 在 [0..t] 內的 rank（1-based average ties）。invalid → NaN。"""
    if ties != "average":
        raise ValueError(f"only ties='average' supported, got {ties!r}")
    index = _index_of(series)
    values = _as_1d_float(series)
    n = values.shape[0]
    out = np.full(n, np.nan, dtype=np.float64)
    if n == 0:
        return pd.Series(out, index=index, dtype=float)

    counts = effective_count(values)
    for t in range(n):
        if counts[t] < min_samples:
            continue
        if not np.isfinite(values[t]):
            continue
        hist = values[: t + 1]
        # pandas rank skips NaN by default
        ranks = pd.Series(hist).rank(method="average")
        out[t] = float(ranks.iloc[-1])
    return pd.Series(out, index=index, dtype=float)


# ---------------------------------------------------------------------------
# 5. pit_expanding_mean_std
# ---------------------------------------------------------------------------
def pit_expanding_mean_std(
    series: ArrayLike,
    min_samples: int = MIN_SAMPLES,
) -> Tuple[pd.Series, pd.Series]:
    """per-t expanding mean / std，**ddof=1**。invalid → NaN。"""
    index = _index_of(series)
    values = _as_1d_float(series)
    n = values.shape[0]
    mean_out = np.full(n, np.nan, dtype=np.float64)
    std_out = np.full(n, np.nan, dtype=np.float64)
    if n == 0:
        return (
            pd.Series(mean_out, index=index, dtype=float),
            pd.Series(std_out, index=index, dtype=float),
        )

    # Welford online（只更新 finite）
    count = 0
    mean = 0.0
    m2 = 0.0
    for t in range(n):
        v = values[t]
        if np.isfinite(v):
            count += 1
            delta = v - mean
            mean += delta / count
            delta2 = v - mean
            m2 += delta * delta2
        if count >= min_samples:
            mean_out[t] = mean
            if count >= 2:
                std_out[t] = np.sqrt(m2 / (count - 1))  # ddof=1
            else:
                std_out[t] = np.nan
        # else leave NaN（invalid）
    return (
        pd.Series(mean_out, index=index, dtype=float),
        pd.Series(std_out, index=index, dtype=float),
    )


# ---------------------------------------------------------------------------
# 6. pit_expanding_mad
# ---------------------------------------------------------------------------
def pit_expanding_mad(
    series: ArrayLike,
    min_samples: int = MIN_SAMPLES,
) -> Tuple[pd.Series, pd.Series]:
    """per-t expanding (median, MAD)。回傳兩者。invalid → NaN。

    MAD = median(|x - median|)。
    """
    index = _index_of(series)
    values = _as_1d_float(series)
    n = values.shape[0]
    med_out = np.full(n, np.nan, dtype=np.float64)
    mad_out = np.full(n, np.nan, dtype=np.float64)
    if n == 0:
        return (
            pd.Series(med_out, index=index, dtype=float),
            pd.Series(mad_out, index=index, dtype=float),
        )

    counts = effective_count(values)
    for t in range(n):
        if counts[t] < min_samples:
            continue
        finite = values[: t + 1]
        finite = finite[np.isfinite(finite)]
        if finite.size == 0:
            continue
        med = float(np.median(finite))
        mad = float(np.median(np.abs(finite - med)))
        med_out[t] = med
        mad_out[t] = mad
    return (
        pd.Series(med_out, index=index, dtype=float),
        pd.Series(mad_out, index=index, dtype=float),
    )


# ---------------------------------------------------------------------------
# 7. pit_train_fit（orchestration policy，非 stats primitive）
# ---------------------------------------------------------------------------
def pit_train_fit(
    df: pd.DataFrame,
    fit_mask: MaskLike,
    transform_fn: Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame],
) -> pd.DataFrame:
    """mask 內 fit → 全段 transform。禁 fit 洩漏。

    transform_fn(fit_df, full_df) -> transformed full_df
    統計參數**只**得來自 fit_df；full_df 僅作 transform 目標。
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    mask = np.asarray(fit_mask, dtype=bool)
    if mask.shape[0] != len(df):
        raise ValueError(
            f"fit_mask length {mask.shape[0]} != df length {len(df)}"
        )
    if not bool(mask.any()):
        raise ValueError("fit_mask must select at least one row")

    fit_df = df.loc[mask]
    result = transform_fn(fit_df, df)
    if not isinstance(result, pd.DataFrame):
        raise TypeError("transform_fn must return a pandas DataFrame")
    if len(result) != len(df):
        raise ValueError("transform_fn result length must match full df")
    # 對齊 index（允許 transform 重建 index）
    if not result.index.equals(df.index):
        result = result.copy()
        result.index = df.index
    return result


# ---------------------------------------------------------------------------
# internal
# ---------------------------------------------------------------------------
def _as_1d_float(series: ArrayLike) -> np.ndarray:
    if isinstance(series, pd.Series):
        return series.to_numpy(dtype=np.float64, copy=False)
    arr = np.asarray(series, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"expected 1D series, got shape {arr.shape}")
    return arr


def _index_of(series: ArrayLike) -> pd.Index:
    if isinstance(series, pd.Series):
        return series.index
    return pd.RangeIndex(len(series))
