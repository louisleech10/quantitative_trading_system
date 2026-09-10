"""Chronological holdout 之**列計畫**唯一實作（EVTLABEL Task 2.2／3.3；R3 `CODEX-R1-P1-04`）。

出生理由：`docs/EVTLABEL_SPEC.md` Task 3.3 之顯式模式 fast-fail 需要在**進 preprocessing 之前**
先估「驗證段有幾個正例／反例」，而 orchestrator 的 `_build_holdout_split_plan` 也要算同一件事。
若兩端各寫一份算術，兩份會漂——R3 三家一致要求抽成單一純函式，並拒絕「事後以
`preview_mismatch` 欄位容忍分歧」的方案（同函式同輸入卻不一致＝bug，不是可揭露的差異）。

🔴 純算術、無副作用、不 import `api`（解耦 R1）。
"""

from __future__ import annotations

import numpy as np


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
