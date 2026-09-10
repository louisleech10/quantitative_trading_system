"""EVTLABEL Task 3.5：0/1 標籤之分辨力統計（Mann-Whitney U／AUC／rank-biserial），向量化。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.5

## 這個模組在回答什麼問題

使用者在外面標好正反例匯入。對每一個特徵，我們問：**t₀ 之前的這個特徵值，能不能把正例
和反例分開？** 答案就是 AUC——隨機抓一個正例、一個反例，正例的特徵值比較大的機率。

- `auc = U / (n_pos · n_neg)`，其中 U 是 Mann-Whitney 的統計量。
- `rank_biserial = 2·auc − 1`（rank-biserial correlation），範圍 [−1, 1]，0 代表分不開。
  **負值代表反向但一樣能分**——所以下游門檻必須看**絕對值**（R1 推翻了共用 `ic_mean_min`）。
- p 值走雙尾 Mann-Whitney；多重比較之校正（BH-FDR）不在本模組，由 stage5 負責。

## 名稱一律用統計學標準名，不自創（使用者 2026-09-10）

`auc`（area under the ROC curve）、`rank_biserial`（rank-biserial correlation）、
`mw_u`（Mann-Whitney U）。

🔴 **純函式**：無 log、無 I/O、不讀 config、不改輸入。
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

__all__ = ["mann_whitney_table", "BINARY_STATUS_OK"]

BINARY_STATUS_OK = "ok"
_STATUS_CLASS_BELOW_MIN = "unavailable:class_below_min"
_STATUS_ALL_NAN = "unavailable:all_nan"
_STATUS_CONSTANT = "unavailable:constant"

COLUMNS = (
    "auc",
    "rank_biserial",
    "mw_u",
    "p_value",
    "n_pos",
    "n_neg",
    "n_used",
    "status",
)


def mann_whitney_table(
    features: pd.DataFrame,
    y: np.ndarray,
    *,
    min_class_n: int = 10,
    weights: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """逐特徵算 AUC／rank-biserial／U／雙尾 p；回 `index=特徵名` 之表。

    參數
    ----
    features : 每欄一個特徵、每列一個事件（列序須與 `y` 對齊）。
    y : `{0,1}` 之整數陣列，長度 == `len(features)`。
    min_class_n : 每一類至少幾個**有效值**才給 `status="ok"`。不足仍算出數值，
        但 status 標 `unavailable:class_below_min`——**算得出來不等於可信**，
        由下游決定要不要用（本模組不替下游做取捨）。
    weights : R-1（樣本唯一性加權）之預留欄位。本票**一律 None**；
        非 None ⇒ `NotImplementedError`。🔴 刻意不靜默忽略：靜默忽略等於
        「呼叫端以為加權了、其實沒有」，那是最難查的一種錯。

    NaN 處理
    --------
    逐欄 pairwise 去列：某欄的缺值只影響那一欄，不會讓整列被丟掉
    （`n_used` 記錄該欄實際用了幾筆）。`inf` 一律視為缺值——上游已有值域閘，
    此處只是防禦。

    不可用之三種情形（皆回值＋非 ok 之 status，不拋例外）
    ------------------------------------------------
    - `unavailable:all_nan`：該欄沒有任何有效值。
    - `unavailable:class_below_min`：某一類的有效值少於 `min_class_n`。
    - `unavailable:constant`：該欄在有效列上是常數。🔴 **不冒充 0.5／1.0**——
      scipy 對「全部並列」之 p 值定義依版本而異，給一個看似正常的數字比說不知道更糟。
    """
    if weights is not None:
        raise NotImplementedError(
            "mann_whitney_table 尚未支援樣本加權（R-1 預留）——"
            "禁靜默忽略：呼叫端會以為加權了、其實沒有"
        )

    y_arr = np.asarray(y)
    if y_arr.ndim != 1 or len(y_arr) != len(features):
        raise ValueError(f"y 長度 {len(y_arr)} 與 features 列數 {len(features)} 不符")
    uniq = set(np.unique(y_arr).tolist())
    if not uniq <= {0, 1}:
        raise ValueError(f"y 只接受 0/1，實得 {sorted(uniq)}")

    names = list(features.columns)
    x = features.to_numpy(dtype="float64", copy=True)
    # inf 併入缺值（上游已閘；此處防禦）
    x[~np.isfinite(x)] = np.nan

    pos_mask = y_arr == 1
    neg_mask = y_arr == 0
    xp, xn = x[pos_mask], x[neg_mask]

    n_pos = np.isfinite(xp).sum(axis=0).astype("int64")
    n_neg = np.isfinite(xn).sum(axis=0).astype("int64")
    n_used = n_pos + n_neg

    auc = np.full(len(names), np.nan)
    rank_biserial = np.full(len(names), np.nan)
    u_stat = np.full(len(names), np.nan)
    p_value = np.full(len(names), np.nan)

    # 🔴 **一次**呼叫（R3 codex P1-03：禁逐欄 python 迴圈）。
    #    [A-2] 實跑：39,373 欄 × 165 列，clean 0.49s、10% NaN 4.02s。
    computable = (n_pos > 0) & (n_neg > 0)
    if computable.any():
        with np.errstate(invalid="ignore"):
            res = stats.mannwhitneyu(
                xp[:, computable], xn[:, computable],
                alternative="two-sided", method="auto", axis=0, nan_policy="omit",
            )
        u_c = np.asarray(res.statistic, dtype="float64").reshape(-1)
        p_c = np.asarray(res.pvalue, dtype="float64").reshape(-1)
        denom = (n_pos[computable] * n_neg[computable]).astype("float64")
        u_stat[computable] = u_c
        p_value[computable] = p_c
        auc[computable] = u_c / denom
        rank_biserial[computable] = 2.0 * (u_c / denom) - 1.0

    # 常數欄：有效列上只有一個相異值（含「只有一筆有效值」）
    with np.errstate(invalid="ignore"):
        col_min = np.nanmin(np.where(np.isfinite(x), x, np.nan), axis=0)
        col_max = np.nanmax(np.where(np.isfinite(x), x, np.nan), axis=0)
    is_constant = np.isfinite(col_min) & np.isfinite(col_max) & (col_min == col_max)

    status = np.full(len(names), BINARY_STATUS_OK, dtype=object)
    status[np.asarray(n_used) == 0] = _STATUS_ALL_NAN
    below = (np.minimum(n_pos, n_neg) < int(min_class_n)) & (np.asarray(n_used) > 0)
    status[below] = _STATUS_CLASS_BELOW_MIN
    status[is_constant & (np.asarray(n_used) > 0)] = _STATUS_CONSTANT

    return pd.DataFrame(
        {
            "auc": auc,
            "rank_biserial": rank_biserial,
            "mw_u": u_stat,
            "p_value": p_value,
            "n_pos": n_pos,
            "n_neg": n_neg,
            "n_used": n_used,
            "status": status,
        },
        index=pd.Index(names, name="feature"),
    )[list(COLUMNS)]
