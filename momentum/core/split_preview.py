"""Chronological holdout 之**列計畫**唯一實作（EVTLABEL Task 2.2／3.3；R3 `CODEX-R1-P1-04`）。

出生理由：`docs/EVTLABEL_SPEC.md` Task 3.3 之顯式模式 fast-fail 需要在**進 preprocessing 之前**
先估「驗證段有幾個正例／反例」，而 orchestrator 的 `_build_holdout_split_plan` 也要算同一件事。
若兩端各寫一份算術，兩份會漂——R3 三家一致要求抽成單一純函式，並拒絕「事後以
`preview_mismatch` 欄位容忍分歧」的方案（同函式同輸入卻不一致＝bug，不是可揭露的差異）。

🔴 純算術、無副作用、不 import `api`（解耦 R1）。
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import numpy as np
import pandas as pd


def holdout_test_row_index(
    n_rows: int,
    *,
    oos_test_size: float,
    purge_gap: int,
    embargo: int,
) -> np.ndarray:
    """回 test 段之**位置索引**（`index_kind="positional"`）。

    定義（與 `ic_filter_orchestrator._build_holdout_split_plan` 逐字相同）：
        split_point = floor((1 - oos_test_size) * n_rows)
        test_rows   = arange(split_point + purge_gap + embargo, n_rows)

    train 段（`arange(0, split_point)`）**不在本函式範圍**：它不需要被預檢共用，
    留在原處可避免把「切分計畫」整包搬家而動到 golden。

    參數皆為已解析之最終值——`purge_gap` 必須是呼叫端算好的
    `max(effective_horizon, label_window_rows)`，本函式**不猜、不查 config**。
    """
    n = int(n_rows)
    split_point = int(np.floor((1.0 - float(oos_test_size)) * n))
    start = split_point + int(purge_gap) + int(embargo)
    return np.arange(start, n, dtype=int)


def holdout_split_point(n_rows: int, *, oos_test_size: float) -> int:
    """train／test 的分界位置（供預檢與診斷；與上式同源）。"""
    return int(np.floor((1.0 - float(oos_test_size)) * int(n_rows)))


def _as_ms(index: Any, position: int) -> int:
    """取 `index[position]` 並正規化為 **epoch 毫秒 int**。

    🔴 SPLITUNIFY 之時鐘一律 epoch **毫秒**，與 `ic_filter_orchestrator._normalize_ic_time_index`
    （那支是**「秒」語意**，餵毫秒會 raise）**不同源，不得混用**——見 SPEC C-4（R2 之 D7）。
    """
    value = pd.Index(index)[position]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return int(pd.Timestamp(value).value // 10 ** 6)
    return int(value)


def holdout_boundary(
    feature_index: Any,
    *,
    oos_test_size: float,
    purge_gap: int,
    embargo: int,
) -> Dict[str, Any]:
    """canonical 邊界之**唯一**產生點（SPLITUNIFY Task 2.1／SPEC C-0）。

    回 `{"train_row_index", "test_row_index", "train_end_ms", "test_start_ms"}`。

    出生理由：事件路徑與 IC 路徑若各自算一次邊界，**即使公式相同也會分歧**——
    因為兩端的 universe 不同。實測（`handoffs/20260911-probe-splitunify-universe-gap.py`、
    receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`）：
    真實 ETHUSDT 1h 20352 列，未裁切時 features 與 bars 逐值相同；EVTALIGN 裁頭尾後
    邊界位移 5 根→2h、24 根→10h、168 根→67h。⇒ **必須共用同一個 universe 與同一支函式**。

    🔴 **本函式以既有兩支定義自身**（`holdout_split_point` ＋ `holdout_test_row_index`），
    不引入第二份切分算術；`M-SU-11` 之 mutation 即針對此。

    🔴 **ms 只供揭露與 `boundary_hash`，禁回流做成員（∈）判定**——成員判定一律走
    `feature_index[row_index]` 的**集合**語意（SPEC C-4）。ms 之導出寫死為
    `train_end_ms = as_ms(feature_index[train_rows[-1]])`、
    `test_start_ms = as_ms(feature_index[test_rows[0]])`（R2 之 D6：v2 只寫「回傳 ms」
    沒寫怎麼導出，實作端寫成 `feature_index[split_point]`（略過 purge／embargo）也能過
    原本的同源自證）。

    🔴 `purge_gap`／`embargo` 是 **row 單位且已包含在 `test_row_index[0]` 這個起點裡**
    （`holdout_test_row_index` ＝ `arange(split_point + purge_gap + embargo, n)`）
    ⇒ 下游做答案窗判定時**不得**再以毫秒相減（SPEC C-4 第一段；R4 之 F1）。

    參數皆為呼叫端算好的最終值——`purge_gap` 須是
    `max(effective_horizon, label_window_rows)`，本函式**不猜、不查 config**。
    """
    index = pd.Index(feature_index)
    n = int(len(index))
    if n == 0:
        # 無 universe 即無邊界；回空計畫會讓下游把「沒切」誤讀成「切了但都空」。
        raise ValueError("holdout_boundary: feature_index 為空——無 universe 即無 canonical 邊界")

    split_point = holdout_split_point(n, oos_test_size=oos_test_size)
    train_rows = np.arange(0, split_point, dtype=int)
    test_rows = holdout_test_row_index(
        n, oos_test_size=oos_test_size, purge_gap=purge_gap, embargo=embargo
    )
    return {
        "train_row_index": train_rows,
        "test_row_index": test_rows,
        # 空段回 None，**不得**回 -1 或 0——那會被下游當成「1970 年」或「有值」。
        "train_end_ms": _as_ms(index, int(train_rows[-1])) if train_rows.size else None,
        "test_start_ms": _as_ms(index, int(test_rows[0])) if test_rows.size else None,
    }


def count_binary_classes_in_rows(
    binary_labels: Optional[Mapping[int, int]],
    feature_index: Any,
    row_index: Any,
) -> Optional[Dict[str, int]]:
    """數「落在 `row_index` 這些列上的 0/1 標籤」各有幾個；`binary_labels` 為 None ⇒ 回 None。

    EVTLABEL Task 3.3（B3 review R1 修補）：本函式是**唯一**的計數實作。

    🔴 出生理由：原版把「測試段是哪幾列」在 service 端重算一次（自組 purge/embargo、
    自取 config），三家實測證明那份重建**必然**與 orchestrator 分歧。改為由呼叫端交出
    **已經算好的** `row_index`（orchestrator 的 `test_plan.row_index`），本函式只做計數 ——
    沒有第二份切分算術，就沒有可漂的東西。

    `binary_labels` 之鍵＝特徵列時間戳（feature_cutoff_ms），與 `feature_index` 同單位。
    不在 `feature_index` 上的鍵（期間對齊時已被剔除的事件）不計入，也不 raise。
    """
    if binary_labels is None:
        return None
    index = pd.Index(feature_index)
    rows = np.asarray(row_index, dtype=int)
    if len(rows) == 0:
        return {"n_pos": 0, "n_neg": 0}
    selected_index = index[rows]
    # 🔴 `binary_labels` 之鍵是 **epoch 毫秒整數**，而特徵索引通常是 `DatetimeIndex`
    #    （內部 ns）。不換算就永遠對不上 ⇒ 計數恆為 0 ⇒ 明示模式恆 raise、auto 恆退回報酬版，
    #    而且**不會拋任何例外**。本 bug 由 Task 3.4 的 selection-scope 測試抓出來。
    if isinstance(selected_index, pd.DatetimeIndex):
        selected = set((selected_index.asi8 // 10**6).astype("int64").tolist())
    else:
        selected = set(np.asarray(selected_index).tolist())
    n_pos = sum(1 for key, lab in binary_labels.items() if int(lab) == 1 and key in selected)
    n_neg = sum(1 for key, lab in binary_labels.items() if int(lab) == 0 and key in selected)
    return {"n_pos": int(n_pos), "n_neg": int(n_neg)}
