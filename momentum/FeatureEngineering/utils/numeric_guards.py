"""數值守衛：除法近零分母 + 通用淨化。

Class A 數值垃圾的兩個來源之一：ratio 類算子（Momentum/Ratio/Distance）
`x / denom`，當 denom 接近零時爆炸。`denom.replace(0, np.nan)` 只擋「正好等於 0」，
但 TA-Lib 有界振盪器（STOCHRSI/STOCH/MFI…）在邊界回傳浮點噪音（如 -1.06e-14）
而非正好 0 → `(v − ε)/ε → 1e14`。

正確守衛是**尺度相對近零**：當 `|denom| < rel_eps × robust_scale(denom)` 時設 NaN，
其中 robust_scale = 該欄非零絕對值的中位數（不被離群值污染、尺度不變）。
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


def safe_denominator(denom: PandasObj, rel_eps: float = DEFAULT_DENOM_REL_EPS) -> PandasObj:
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

    # robust scale = 非零絕對值的中位數（Series→純量；DataFrame→per-column Series）
    nonzero = abs_d.where(abs_d > 0)
    scale = nonzero.median()
    threshold = scale * rel_eps

    if isinstance(denom, pd.DataFrame):
        # per-column 廣播；threshold 為 per-column Series（NaN 欄→門檻 NaN→lt 為 False）
        near_zero = abs_d.lt(threshold, axis=1).fillna(False)
        mask = near_zero | (abs_d == 0)
    else:
        thr = float(threshold) if np.isfinite(threshold) else 0.0
        mask = (abs_d < thr) | (abs_d == 0)
    return denom.where(~mask, np.nan)


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
