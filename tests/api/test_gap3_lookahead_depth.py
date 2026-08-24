"""GAP-3 UX Task 2.1b — 由篩選條件導出答案窗下界之驗收（SPEC L1846–1859 之 ①–④）。

⚠️ 驗收②**刻意不寫成**「lookahead_bars…＝72」之形態——那會暗示「根數恆為 72 而與 tf 無關」，
正是 SPEC 檔頭 SYNC-FORBID 所禁之字面。本檔要釘死的恰是**相反**：
**根數逐 tf 不同，時間長度才相同**。
"""

from __future__ import annotations

import pytest

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.Analysis.event_samples.lookahead_depth import (
    UnresolvableLookaheadDepth,
    depth_by_timeframe,
)


# ── ① bar 命名欄：鎖定為被引用欄之最大深度 ────────────────────────────────
def test_gap3_lookahead_depth_01_bar_named_locks_to_max() -> None:
    got = depth_by_timeframe(
        ["future_2bar_return", "future_7bar_return"],
        {"1h": 1},
        ["1h"],
    )
    assert got == {"1h": 7}
    # 「宣告 12 但條件只用 2／7」⇒ 取宣告值（左項不得被漏掉）
    assert depth_by_timeframe(["future_2bar_return"], {"1h": 12}, ["1h"]) == {"1h": 12}


# ── ② 小時命名欄之逐 tf 解析（根數逐 tf 不同） ─────────────────────────────
def test_gap3_lookahead_depth_02_hour_named_resolves_per_tf() -> None:
    got = depth_by_timeframe(
        ["future72_max_drawdown"],
        {"1h": 0, "12h": 0},
        ["1h", "12h"],
    )
    # receipt：72*3600//TIMEFRAME_SECONDS['1h'] , 72*3600//TIMEFRAME_SECONDS['12h'] → 72 6
    assert got["1h"] == 72 * 3600 // TIMEFRAME_SECONDS["1h"]
    assert got["12h"] == 72 * 3600 // TIMEFRAME_SECONDS["12h"]
    assert got["1h"] != got["12h"]  # 根數與 tf 相依，不是常數


# ── ③ 同批兩 tf 換算回 ms 相等（時間長度才是不變量）；對照組 bar 命名相差 12 倍 ─
def test_gap3_lookahead_depth_03_hour_named_equal_ms_across_tf() -> None:
    hour_named = depth_by_timeframe(
        ["future72_max_drawdown"], {"1h": 0, "12h": 0}, ["1h", "12h"]
    )
    ms_1h = hour_named["1h"] * TIMEFRAME_SECONDS["1h"] * 1000
    ms_12h = hour_named["12h"] * TIMEFRAME_SECONDS["12h"] * 1000
    assert ms_1h == ms_12h

    bar_named = depth_by_timeframe(
        ["future_4bar_return"], {"1h": 0, "12h": 0}, ["1h", "12h"]
    )
    assert bar_named["1h"] == bar_named["12h"] == 4
    b_ms_1h = bar_named["1h"] * TIMEFRAME_SECONDS["1h"] * 1000
    b_ms_12h = bar_named["12h"] * TIMEFRAME_SECONDS["12h"] * 1000
    assert b_ms_12h == b_ms_1h * 12


# ── ④ 批內僅單一 tf ⇒ map 退化為單鍵（回歸保護） ───────────────────────────
def test_gap3_lookahead_depth_04_single_tf_degenerates_to_one_key() -> None:
    got = depth_by_timeframe(["future_7bar_return"], {"1h": 3}, ["1h"])
    assert got == {"1h": 7}
    assert len(got) == 1


# ── 邊界②：附帶欄不得納入 max（過度 purge 亦屬錯誤） ───────────────────────
def test_gap3_lookahead_depth_05_attached_columns_not_in_max() -> None:
    # 條件只引用 future_2bar_return；Task 4.1 之附帶欄 [1,3,7] 不進 referenced_columns
    assert depth_by_timeframe(["future_2bar_return"], {"1h": 0}, ["1h"]) == {"1h": 2}


# ── 左項缺鍵 fail-closed（不得以 1 或別的 tf 之值默認替代） ────────────────
def test_gap3_lookahead_depth_06_missing_declared_key_fail_closed() -> None:
    with pytest.raises(KeyError):
        depth_by_timeframe(["future_4bar_return"], {"1h": 0}, ["1h", "12h"])


# ── 引用欄深度不可導出 ⇒ fail-closed，交 L2 宣告，不猜 ─────────────────────
def test_gap3_lookahead_depth_07_unresolvable_column_fail_closed() -> None:
    with pytest.raises(UnresolvableLookaheadDepth):
        depth_by_timeframe(["future_max_return"], {"1h": 0}, ["1h"])
    with pytest.raises(UnresolvableLookaheadDepth):
        depth_by_timeframe(["my_custom_signal"], {"1h": 0}, ["1h"])


# ── map 不得塌成 scalar：逐 tf 之宣告值不同 ⇒ 輸出必須逐 tf 不同 ────────────
def test_gap3_lookahead_depth_09_map_not_collapsed_to_scalar() -> None:
    """對「把 map 塌成單一 scalar」之定向探針。

    刻意用 **bar 命名欄**（根數與 tf 無關）＋**逐 tf 不同之宣告值**：
    此時兩 tf 之差異**只**來自左項，塌成 scalar 必紅，而小時換算之錯誤在此不影響
    ⇒ 本條把「塌 scalar」與「小時分支算錯」分開，兩種壞法不會共用同一條紅。
    """
    got = depth_by_timeframe(["future_4bar_return"], {"1h": 1, "12h": 9}, ["1h", "12h"])
    assert got == {"1h": 4, "12h": 9}


# ── 宣告值型別 fail-closed（bool ⊂ int） ──────────────────────────────────
def test_gap3_lookahead_depth_08_declared_type_fail_closed() -> None:
    with pytest.raises(ValueError):
        depth_by_timeframe(["future_4bar_return"], {"1h": True}, ["1h"])
    with pytest.raises(ValueError):
        depth_by_timeframe(["future_4bar_return"], {"1h": -1}, ["1h"])
