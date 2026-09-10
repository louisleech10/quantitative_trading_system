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
    selected = set(np.asarray(index[rows]).tolist())
    n_pos = sum(1 for key, lab in binary_labels.items() if int(lab) == 1 and key in selected)
    n_neg = sum(1 for key, lab in binary_labels.items() if int(lab) == 0 and key in selected)
    return {"n_pos": int(n_pos), "n_neg": int(n_neg)}
