"""數值守衛：除法近零分母 + 通用淨化。

Class A 數值垃圾的兩個來源之一：ratio 類算子（Momentum/Ratio/Distance）
`x / denom`，當 denom 接近零時爆炸。`denom.replace(0, np.nan)` 只擋「正好等於 0」，
但 TA-Lib 有界振盪器（STOCHRSI/STOCH/MFI…）在邊界回傳浮點噪音（如 -1.06e-14）
而非正好 0 → `(v − ε)/ε → 1e14`。

正確守衛是**尺度相對近零**：當 `|denom| < rel_eps × robust_scale(denom)` 時設 NaN，
其中 robust_scale = 第 t 列（含）之前固定回看窗（DEFAULT_DENOM_SCALE_WINDOW）內之非零絕對值中位數（不被離群值污染、尺度不變；
因果——FFSTAT v53 改前為全欄中位數＝未來洩漏；窗未滿之列 fail-closed 為 NaN）。
- STOCHRSI（median≈30）→ 門檻 3e-5 擋 1e-14 噪音、保留真實 0.5
- 真實微尺度特徵（median≈1e-8）→ 門檻隨之縮小、不誤殺

詳見 plans/kind-questing-newell.md Layer A2。
"""

from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd

PandasObj = Union[pd.Series, pd.DataFrame]

# 預設相對容差：分母小於「該欄 robust scale × 此值」即視為數值噪音 → NaN。
# 1e-6 遠高於 float64 噪音地板（~2.2e-16），足以擋 TA-Lib 振盪器邊界的 ~1e-14，
# 又遠小於任何有意義的振盪器值（如 STOCHRSI 0.5 / 30 ≈ 1.7e-2）。
DEFAULT_DENOM_REL_EPS: float = 1e-6

# FFSTAT v53（審查 r36 兩家一致：改前以「全欄」非零絕對值中位數為尺度，第 t 列是否遮為 NaN 取決於 t 之後之值
# ＝未來洩漏，且隨起算點而變）：尺度改為第 t 列（含）之前固定回看窗內之非零絕對值中位數；窗未滿之列 fail-closed。
DEFAULT_DENOM_SCALE_WINDOW: int = 252


def _numba():
    import numba

    return numba


def _build_rolling_nonzero_abs_median():
    numba = _numba()

    @numba.njit(cache=True)
    def kernel(values: np.ndarray, window: int) -> np.ndarray:
        n = values.shape[0]
        out = np.full(n, np.nan)
        first = -1
        for i in range(n):
            if np.isfinite(values[i]):
                first = i
                break
        if first < 0:
            return out
        # 滑動有序緩衝（插入／刪除為精確搬移，無累加捨入 ⇒ 中位數只依窗內值、與起算點無關）
        buf = np.empty(window + 1, dtype=np.float64)  # 先插後刪，瞬時可達 window+1
        size = 0
        for t in range(first, n):
            v = values[t]
            if np.isfinite(v) and v != 0.0:
                a = abs(v)
                k = size
                while k > 0 and buf[k - 1] > a:
                    buf[k] = buf[k - 1]
                    k -= 1
                buf[k] = a
                size += 1
            if t - window >= first:
                old = values[t - window]
                if np.isfinite(old) and old != 0.0:
                    a = abs(old)
                    k = 0
                    while k < size and buf[k] != a:
                        k += 1
                    for m in range(k, size - 1):
                        buf[m] = buf[m + 1]
                    size -= 1
            if t < first + window - 1:
                continue
            if size == 0:
                out[t] = 0.0
            elif size % 2 == 1:
                out[t] = buf[size // 2]
            else:
                out[t] = 0.5 * (buf[size // 2 - 1] + buf[size // 2])
        return out

    return kernel


_ROLLING_NONZERO_ABS_MEDIAN = None


def causal_denominator_scale(values: np.ndarray, window: int = DEFAULT_DENOM_SCALE_WINDOW) -> np.ndarray:
    """第 t 列（含）之前 ``window`` 列內之非零有限絕對值中位數；自首個有限值起未滿 ``window`` 列者為 NaN
    （fail-closed）；窗內全為 0 者為 0。只讀 t 之前之值 ⇒ 因果、且窗滿後與起算點無關。"""
    global _ROLLING_NONZERO_ABS_MEDIAN
    if _ROLLING_NONZERO_ABS_MEDIAN is None:
        _ROLLING_NONZERO_ABS_MEDIAN = _build_rolling_nonzero_abs_median()
    return _ROLLING_NONZERO_ABS_MEDIAN(np.ascontiguousarray(values, dtype=np.float64), int(window))


def causal_near_zero_mask(values: np.ndarray, rel_eps: float = DEFAULT_DENOM_REL_EPS,
                          window: int = DEFAULT_DENOM_SCALE_WINDOW) -> np.ndarray:
    """分母應遮為 NaN 之列：exact 0、非有限、|d| < rel_eps × 因果尺度、或因果尺度未定（窗未滿）。"""
    d = np.asarray(values, dtype=np.float64)
    abs_d = np.abs(d)
    if rel_eps <= 0:
        return ~np.isfinite(d) | (abs_d == 0)
    scale = causal_denominator_scale(d, window)
    with np.errstate(invalid="ignore"):
        return ~np.isfinite(d) | (abs_d == 0) | ~np.isfinite(scale) | (abs_d < rel_eps * scale)


def safe_denominator(denom: PandasObj, rel_eps: float = DEFAULT_DENOM_REL_EPS,
                     window: int = DEFAULT_DENOM_SCALE_WINDOW) -> PandasObj:
    """回傳 denom，將「正好為 0」與「相對近零（浮點噪音）」的元素設為 NaN。

    Args:
        denom: 分母 Series 或 DataFrame（DataFrame 為 per-column 判定）。
        rel_eps: 相對容差。<=0 時退化為僅擋 exact 0（向後相容）。

    Returns:
        同型別物件；近零元素 → NaN，使 `x / safe_denominator(denom)` 得 NaN 而非爆炸。
    """
    abs_d = denom.abs()
    if rel_eps <= 0:
        # 向後相容：僅擋 exact 0
        return denom.where(abs_d > 0, np.nan)

    # FFSTAT v53：尺度＝第 t 列（含）之前 DEFAULT_DENOM_SCALE_WINDOW 列之非零絕對值中位數（因果；窗未滿 fail-closed）
    if isinstance(denom, pd.DataFrame):
        mask = pd.DataFrame(
            {c: causal_near_zero_mask(denom[c].to_numpy(dtype=np.float64), rel_eps, window) for c in denom.columns},
            index=denom.index,
        )
        return denom.where(~mask, np.nan)
    mask = causal_near_zero_mask(denom.to_numpy(dtype=np.float64), rel_eps, window)
    return denom.where(~pd.Series(mask, index=denom.index), np.nan)


def sanitize_array_inplace(
    array: np.ndarray,
    finite_cap: float = 1e18,
) -> int:
    """Layer B 通用淨化：將非有限值與 |v|>finite_cap 的絕對垃圾設為 NaN（in-place）。

    這是最後防線，攔截 Layer A 漏掉的 overflow stragglers，覆蓋所有特徵（含
    CGSA-streamed L3）。Class B 真實大值（如 volume VAR ~3e10）遠低於 finite_cap
    → 保留。**不**做 quantile winsorization（Class A 爆炸比例 ~5% ≫ 1% 尾，clip 無效；
    根因已由 Layer A 在源頭 NaN）。

    Args:
        array: 2D float array（per-group post-transform），就地修改。
        finite_cap: 絕對值上限；超過視為數值垃圾。<=0 時停用 cap（僅 inf→NaN）。

    Returns:
        被設為 NaN 的元素數量（供日誌）。
    """
    if array.size == 0:
        return 0
    bad = ~np.isfinite(array)
    if finite_cap > 0:
        bad |= np.abs(array) > finite_cap
    n_bad = int(bad.sum())
    if n_bad:
        array[bad] = np.nan
    return n_bad
