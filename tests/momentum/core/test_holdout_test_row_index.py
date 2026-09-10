"""EVTLABEL Task 2.2／3.3（R3 `CODEX-R1-P1-04`）：holdout 列計畫之**單一實作**。

orchestrator 的切分與 service 的顯式模式預檢必須呼叫同一支純函式——兩份算術會漂，
而 R3 三家一致拒絕「事後以 preview_mismatch 容忍分歧」。
"""

from __future__ import annotations

import numpy as np
import pytest

from momentum.core.split_preview import holdout_split_point, holdout_test_row_index


def test_matches_legacy_arithmetic():
    """與 `_build_holdout_split_plan` 原式逐字相同（改寫前之算術是本測試的 oracle）。"""
    for n_rows in (100, 1000, 10_292, 18_937):
        for oos in (0.1, 0.2, 0.35):
            for purge in (0, 5, 12, 156):
                for embargo in (0, 144):
                    split_point = int(np.floor((1.0 - oos) * n_rows))
                    expected = np.arange(split_point + purge + embargo, n_rows, dtype=int)
                    got = holdout_test_row_index(
                        n_rows, oos_test_size=oos, purge_gap=purge, embargo=embargo,
                    )
                    assert np.array_equal(got, expected)
                    assert holdout_split_point(n_rows, oos_test_size=oos) == split_point


def test_receipt_run_shape():
    """受理 run（2026-09-09 報告：train 8,352＋隔離 149＋test 1,940 ⇒ n=10,441 列、oos 0.2）。

    改前 purge=5／embargo=144 ⇒ test 1,940 列；改後 purge=12 ⇒ 起點往後 7 列、總隔離 149→156。
    """
    n = 10_441
    before = holdout_test_row_index(n, oos_test_size=0.2, purge_gap=5, embargo=144)
    after = holdout_test_row_index(n, oos_test_size=0.2, purge_gap=12, embargo=144)
    assert len(before) == 1940
    assert len(after) == len(before) - 7
    assert after[0] == before[0] + 7


def test_purge_and_embargo_shift_start_only():
    n = 1000
    base = holdout_test_row_index(n, oos_test_size=0.2, purge_gap=0, embargo=0)
    shifted = holdout_test_row_index(n, oos_test_size=0.2, purge_gap=3, embargo=4)
    assert base[-1] == shifted[-1] == n - 1  # 尾端不動
    assert shifted[0] == base[0] + 7


def test_isolation_larger_than_tail_yields_empty_not_negative():
    """隔離區吃光尾段 ⇒ 空陣列（由呼叫端之 min_test_rows 判 INSUFFICIENT_DATA），不得回負索引。"""
    out = holdout_test_row_index(100, oos_test_size=0.2, purge_gap=50, embargo=50)
    assert out.size == 0
    assert out.dtype == np.dtype(int)


@pytest.mark.parametrize("n_rows", [0, 1])
def test_degenerate_sizes(n_rows: int):
    out = holdout_test_row_index(n_rows, oos_test_size=0.2, purge_gap=0, embargo=0)
    assert out.size <= n_rows


def test_orchestrator_uses_this_function():
    """防「有人把算術複製回去」：orchestrator 之 split 建構必須呼叫本函式。"""
    import inspect

    from momentum.Analysis import ic_filter_orchestrator as orch

    src = inspect.getsource(orch._build_holdout_split_plan)
    assert "holdout_test_row_index(" in src, "切分未使用共用純函式（第二份算術會漂）"
    assert "np.arange(split_point" not in src, "殘留舊的就地算術"
