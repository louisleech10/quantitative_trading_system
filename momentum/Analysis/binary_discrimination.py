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

__all__ = [
    "mann_whitney_table",
    "BINARY_STATUS_OK",
    "block_ids_for_events",
    "block_permutation_oracle",
    "rank_biserial_stat",
]

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


# ══════════════════════════════════════════════════════════════════════════
# EVTLABEL Task 3.7：依賴感知之區塊置換（block permutation）
#
# 為什麼不能直接把標籤洗牌：事件之間**不是獨立的**。兩個相隔很近的事件，其 label 視窗
# 會重疊，等於在看同一段未來——把標籤逐筆洗開會破壞這個相依結構，讓「隨機也能篩出東西」
# 的機率被低估，於是置換檢定過度樂觀。做法是把時間上相鄰、視窗會互相重疊的事件綁成一個
# **區塊**，洗牌的單位是區塊而不是單筆（AFML 之 block bootstrap 同理）。
# ══════════════════════════════════════════════════════════════════════════


def block_ids_for_events(
    sel_idx_ms: np.ndarray,
    label_window_feature_bars: int,
    feature_bar_ms: int,
) -> tuple:
    """把事件依時間序切成區塊；回 `(block_ids, block_len, n_blocks)`。

    區塊長度 `L` 之取法（R2 D3）：
        L = max(1, ceil(W / min_gap), ceil(W / median_gap))

    `W` 是 label 視窗有幾根特徵 K 線，`gap` 是相鄰事件相隔幾根。
    直覺：視窗跨過幾個事件，那幾個就得綁在一起。

    🔴 **取 min 與 median 兩者之較大值**：只用 median 會低估局部密集段
    （前段每根都有事件、後段很稀疏時，median 看起來很大而密集段其實嚴重重疊）；
    只用 min 則會被單一個極近的一對綁死整批。取較大者＝偏保守。

    `len(gaps) == 0`（只有一個事件）⇒ `L = 1`。
    """
    arr = np.asarray(sorted(int(v) for v in np.asarray(sel_idx_ms).tolist()), dtype="int64")
    n = len(arr)
    if n == 0:
        return np.zeros(0, dtype=int), 1, 0
    bar = max(1, int(feature_bar_ms))
    w = max(0, int(label_window_feature_bars))
    gaps = np.diff(arr) / bar
    gaps = gaps[gaps > 0]
    if len(gaps) == 0 or w == 0:
        block_len = 1
    else:
        block_len = max(
            1,
            int(np.ceil(w / float(np.min(gaps)))),
            int(np.ceil(w / float(np.median(gaps)))),
        )
    block_ids = np.arange(n, dtype=int) // int(block_len)
    return block_ids, int(block_len), int(len(np.unique(block_ids)))


def _permute_blocks(rng: "np.random.Generator", y: np.ndarray, block_ids: np.ndarray) -> np.ndarray:
    """把 `y` 以**區塊**為單位重排；區塊內的順序與內容原樣保留。

    🔴 獨立小函式是刻意的：mutation `M-P3-4` 把它換成恆等，用來證明
    「置換真的有發生」這件事是被測到的，而不是靠註解宣稱。
    """
    order = np.unique(block_ids)
    shuffled = order.copy()
    rng.shuffle(shuffled)
    out = np.empty_like(y)
    cursor = 0
    for block in shuffled:
        chunk = y[block_ids == block]
        out[cursor: cursor + len(chunk)] = chunk
        cursor += len(chunk)
    return out


def block_permutation_oracle(
    values: np.ndarray,
    y: np.ndarray,
    block_ids: np.ndarray,
    stat_fn,
    *,
    seed: int,
    n_perm: int,
    q_low: float = 0.025,
    q_high: float = 0.975,
    min_blocks: int = 10,
) -> dict:
    """對單一特徵做區塊置換檢定；沿用既有 oracle 的三道硬檢與雙尾經驗 p。

    `n_blocks < min_blocks` ⇒ 回 `{"status": "unavailable:insufficient_blocks"}`。
    🔴 這是**預期中的限制**不是錯誤：答案窗很長時整批只切得出幾個區塊，
    此時置換分布的解析度不足以說任何話——誠實回「做不了」，不給一個沒有意義的 p。
    """
    import hashlib

    n_blocks = int(len(np.unique(block_ids)))
    if n_blocks < int(min_blocks):
        return {"status": f"unavailable:insufficient_blocks", "n_blocks": n_blocks}

    rng = np.random.default_rng(int(seed))
    observed = float(stat_fn(values, y))
    perm_stats = np.empty(int(n_perm), dtype=float)
    any_non_identity = False
    first_digest = None
    for i in range(int(n_perm)):
        yp = _permute_blocks(rng, y, block_ids)
        if first_digest is None:
            first_digest = hashlib.sha256(np.asarray(yp).tobytes()).hexdigest()
        if not np.array_equal(yp, y):
            any_non_identity = True
        perm_stats[i] = stat_fn(values, yp)

    # 硬檢 (i) 分布非退化；(ii) 非恆等——違反即 oracle 自身 FAIL（封死「觀測值∈觀測值」假綠）
    finite = perm_stats[~np.isnan(perm_stats)]
    if not (np.nanvar(perm_stats) > 0.0 and len(np.unique(finite)) > 1):
        raise ValueError("block permutation oracle degenerate: variance==0 or n_unique<=1（硬檢 i）")
    if not any_non_identity:
        raise ValueError("block permutation oracle identity-only permutations（硬檢 ii）")

    lo = float(np.nanquantile(perm_stats, q_low))     # 硬檢 (iii)：經驗分位
    hi = float(np.nanquantile(perm_stats, q_high))
    p = float(min(1.0, 2.0 * min(
        (1 + np.sum(perm_stats >= observed)) / (int(n_perm) + 1),
        (1 + np.sum(perm_stats <= observed)) / (int(n_perm) + 1),
    )))
    return {
        "status": BINARY_STATUS_OK,
        "observed": observed,
        "band_low": lo,
        "band_high": hi,
        "in_band": bool(lo <= observed <= hi),
        "p_value": p,
        "n_blocks": n_blocks,
        "receipt": {"seed": int(seed), "n_perm": int(n_perm),
                    "first_permutation_digest": first_digest},
    }


def rank_biserial_stat(values: np.ndarray, y: np.ndarray) -> float:
    """單一特徵之 rank-biserial（供置換 oracle 當 `stat_fn`）。"""
    v = np.asarray(values, dtype="float64")
    yy = np.asarray(y)
    pos, neg = v[yy == 1], v[yy == 0]
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    u = float(stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic)
    return 2.0 * (u / (len(pos) * len(neg))) - 1.0
