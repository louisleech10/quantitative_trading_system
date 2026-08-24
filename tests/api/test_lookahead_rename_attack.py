"""GAP-3 UX Task 1.10 ⑤ — 改名攻擊（信任邊界）之驗收（SPEC L1673–1677）。

要防的失敗形態：使用者把「實際引用 20 根未來資料」的自訂欄**改名**為已登記之
`future_4bar_return`。若 registry 之接受條件只是欄名比對，L2 不會觸發、purge 被低估到 4 根。
⇒ 外部上傳欄之**欄名不具證據力**；判定依據是該批之 provenance。
"""

from __future__ import annotations

import pytest

from momentum.Analysis.event_samples.lookahead_registry import (
    PROVENANCE_EXTERNAL_UPLOAD,
    PROVENANCE_SYSTEM_GENERATED,
    lookahead_resolution,
)


# 🔴 CODEX-R4-P2-01：舊版兩條都只用 `future_4bar_return` ⇒ 把任一分支「特殊化成只認那一欄」
#    之壞法仍全綠（codex 實跑兩種突變皆 13 passed）。改為覆蓋 bar／hour／unknown 三類多欄。
_UPLOAD_CASES = [
    "future_4bar_return",        # bar 類，命中 registry
    "future_11bar_max_drawdown",  # bar 類，另一個 N
    "future72_max_return",        # hour 類
    "future24_close",             # hour 類，非 return 欄
    "future_max_return",          # unknown 類
    "my_custom_signal",           # 未登記
    "Future_7Bar_Return_%",       # CSV 標題形
]


@pytest.mark.parametrize("column", _UPLOAD_CASES)
def test_lookahead_rename_attack_01_uploaded_column_requires_declaration(column) -> None:
    """外部上傳一律須強制宣告——**無論欄名是否命中 registry、屬哪一類**。"""
    res = lookahead_resolution(column, "1h", provenance=PROVENANCE_EXTERNAL_UPLOAD)
    assert res["requires_declaration"] is True, column
    assert res["lookahead_bars"] is None, column
    assert res["reason"] == "external_upload_column_name_not_evidence", column


@pytest.mark.parametrize(
    "column,timeframe,expected_bars",
    [
        ("future_4bar_return", "1h", 4),
        ("future_11bar_max_drawdown", "1h", 11),
        ("future_4bar_return", "12h", 4),      # bar 類與 tf 無關
        ("future72_max_return", "1h", 72),
        ("future72_max_return", "12h", 6),      # hour 類逐 tf 不同
        ("future24_close", "12h", 2),
        ("Future_7Bar_Return_%", "1h", 7),      # CSV 標題形
    ],
)
def test_lookahead_rename_attack_02_system_generated_resolves_directly(
    column, timeframe, expected_bars
) -> None:
    """對照組：來自 /search 之系統產生批（有 provenance）⇒ 深度直接解析。"""
    res = lookahead_resolution(column, timeframe, provenance=PROVENANCE_SYSTEM_GENERATED)
    assert res["requires_declaration"] is False, column
    assert res["lookahead_bars"] == expected_bars, column


def test_lookahead_rename_attack_03_system_generated_unknown_still_declares() -> None:
    """系統產生欄但深度不可由 registry 導出（legacy 無數字欄）⇒ 仍須宣告，不得給預設深度。"""
    res = lookahead_resolution(
        "future_max_return", "1h", provenance=PROVENANCE_SYSTEM_GENERATED
    )
    assert res["requires_declaration"] is True
    assert res["lookahead_bars"] is None
    assert res["reason"] == "depth_not_derivable_from_registry"


# 🔴 CODEX-R3-P2-04：舊版只測 literal "trust_me" ⇒ 實作若寫成
#    `if provenance == "trust_me": raise`（只拒那一個字串、其餘一律放行）仍全綠。
#    改為多值參數化 ＋ 對「封閉集合」本身做斷言。
@pytest.mark.parametrize(
    "bogus",
    ["trust_me", "", "SYSTEM_GENERATED", "system-generated", "external", None, 0, "user", "internal"],
)
def test_lookahead_rename_attack_04_unknown_provenance_fail_closed(bogus) -> None:
    """provenance 為封閉集合；**任何**非集合內之值即 raise，不得靜默當成可信。"""
    with pytest.raises(ValueError):
        lookahead_resolution("future_4bar_return", "1h", provenance=bogus)


def test_lookahead_rename_attack_05_provenance_closed_set_is_exactly_two() -> None:
    """封閉集合之字面本身受測——多一個值進來就會紅（防悄悄放寬）。"""
    from momentum.Analysis.event_samples import lookahead_registry as lr

    assert set(lr._PROVENANCE_KINDS) == {PROVENANCE_SYSTEM_GENERATED, PROVENANCE_EXTERNAL_UPLOAD}
    # 集合內之兩值皆不得 raise（防「恆紅型假保證」）
    for ok in (PROVENANCE_SYSTEM_GENERATED, PROVENANCE_EXTERNAL_UPLOAD):
        lookahead_resolution("future_4bar_return", "1h", provenance=ok)
