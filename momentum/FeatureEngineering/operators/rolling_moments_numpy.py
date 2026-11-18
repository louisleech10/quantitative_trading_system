"""L3 skew／kurt 之獨立 numpy 實作（TESTSEL I1b；docs/TESTSEL_I1_REDS_SPEC.md Task 2.4）。

用途：`rolling_aggregator` 中原以 pandas `rolling().skew()`／`.kurt()` 計算之四處（pandas 串流臂、numba 單窗路徑、
非串流向量化路徑、`_compute_skew`／`_compute_kurt`）一律改呼本模組——pandas 線上累積演算法於大均值欄數值錯
（真實 BTCUSDT/1h close 窗 5 kurt 20,348 窗中 19,035 窗超 1 float32 ulp，最大相對差 75.2）、常數窗輸出 skew 0／kurt −3。
實作：float64 逐窗兩遍法（先減窗均值再算二／三／四階中心矩），`numpy.lib.stride_tricks.sliding_window_view`；
**不呼叫任何 numba 函式**（numba 臂失敗而後備時仍可用）。退化約定與 numba 臂（`numba_rolling._window_moments`）一致：
樣本數不足、窗內任一非有限值、常數窗（max＝min）⇒ NaN。
"""
from __future__ import annotations

import numpy as np

# 與 numba_rolling._MOMENT_REL_EPS／_MOMENT_BOUND_TOL 同值（不 import numba 模組：後備須於 numba 不可用時仍可用）
_MOMENT_REL_EPS = 1e-12
_MOMENT_BOUND_TOL = 1e-9
#: 每塊實體暫存之元素數上界（float64 ⇒ 每份 8 MiB；同時存活約 5 份）——演算法內部分塊，不限制輸入規模
_SCRATCH_ELEMS = 1 << 20


def _kurt_lower(n: float) -> float:
    """樣本超額峰度之可達最小值（平衡兩點 k／k+1；TESTSEL I1e，SPEC Task 2.5）：偶數 n＝−2(n−1)/(n−3)，
    奇數 n＝−2n/(n−2)。與 `numba_rolling._compute_kurt` 同式。"""
    if int(n) % 2 == 1:
        return -2.0 * n / (n - 2.0)
    return -2.0 * (n - 1.0) / (n - 3.0)


def rolling_skew_kurt_numpy(values: np.ndarray, window: int) -> np.ndarray:
    """回 (len(values), 2) float64：[:, 0]＝樣本偏態（bias=False）、[:, 1]＝樣本超額峰度（Fisher、bias=False）。

    公式與退化／界守衛同 `numba_rolling._compute_skew`／`_compute_kurt`（m2／m3／m4 為窗內中心化之和）：
    skew＝n√(n−1)/(n−2)·m3/m2^1.5；kurt＝(n−1)/((n−2)(n−3))·((n+1)(n·m4/m2²−3)+6)；
    實質常數窗（m2 ≤ 1e-12·Σx²）或超出精確樣本界（|skew|≤√n、`_kurt_lower(n)`≤kurt≤n，容差 1e-9）⇒ NaN。"""
    x = np.asarray(values, dtype=np.float64)
    n_rows = x.shape[0]
    out = np.full((n_rows, 2), np.nan, dtype=np.float64)
    w = int(window)
    if w <= 0:
        raise ValueError("window must be positive")
    if n_rows < w:
        return out
    view = np.lib.stride_tricks.sliding_window_view(x, w)
    # 依輸出窗分塊：每塊之實體暫存（win／d／d2 與乘積）≤ _SCRATCH_ELEMS 個 float64，與列數、窗長無關；
    # 每個輸出只依其自身之窗（沿 axis=1 歸約），分塊不改任何窗之值（測試以不同塊大小逐位元比對）。
    step = max(1, _SCRATCH_ELEMS // w)
    for start in range(0, view.shape[0], step):
        _moments_block(view[start:start + step], w, start, out)
    return out


def _moments_block(view: np.ndarray, w: int, start: int, out: np.ndarray) -> None:
    """對 `view`（連續之輸出窗，第 0 窗之輸出列＝start＋w−1）算偏態／峰度並寫入 `out`。"""
    valid = np.isfinite(view).all(axis=1) & (view.max(axis=1) != view.min(axis=1))
    if not valid.any():
        return
    win = view[valid]
    mean = win.mean(axis=1, keepdims=True)
    d = win - mean
    d2 = d * d
    m2 = d2.sum(axis=1)
    m3 = (d2 * d).sum(axis=1)
    m4 = (d2 * d2).sum(axis=1)
    n = float(w)
    skew = np.full(win.shape[0], np.nan)
    kurt = np.full(win.shape[0], np.nan)
    sumsq = m2 + n * mean[:, 0] * mean[:, 0]
    usable = m2 > _MOMENT_REL_EPS * sumsq
    with np.errstate(divide="ignore", invalid="ignore"):
        if w >= 3:
            skew = (n * np.sqrt(n - 1.0) / (n - 2.0)) * (m3 / m2 ** 1.5)
            skew[~usable | ~np.isfinite(skew) | (np.abs(skew) > np.sqrt(n) * (1.0 + _MOMENT_BOUND_TOL))] = np.nan
        if w >= 4:
            excess = n * m4 / (m2 * m2) - 3.0
            kurt = ((n - 1.0) / ((n - 2.0) * (n - 3.0))) * ((n + 1.0) * excess + 6.0)
            lower = _kurt_lower(n)
            kurt[~usable | ~np.isfinite(kurt) | (kurt > n * (1.0 + _MOMENT_BOUND_TOL))
                 | (kurt < lower * (1.0 + _MOMENT_BOUND_TOL))] = np.nan
    rows = np.flatnonzero(valid) + (start + w - 1)
    out[rows, 0] = skew
    out[rows, 1] = kurt
