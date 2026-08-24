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


def test_lookahead_rename_attack_01_uploaded_column_requires_declaration() -> None:
    """上傳 CSV 之欄名命中 registry，但無 producer provenance ⇒ 仍須強制宣告。"""
    res = lookahead_resolution(
        "future_4bar_return", "1h", provenance=PROVENANCE_EXTERNAL_UPLOAD
    )
    assert res["requires_declaration"] is True
    assert res["lookahead_bars"] is None
    assert res["reason"] == "external_upload_column_name_not_evidence"


def test_lookahead_rename_attack_02_system_generated_resolves_directly() -> None:
    """對照組：同一欄名但來自 /search 之系統產生批（有 provenance）⇒ 深度直接解析 == 4。"""
    res = lookahead_resolution(
        "future_4bar_return", "1h", provenance=PROVENANCE_SYSTEM_GENERATED
    )
    assert res["requires_declaration"] is False
    assert res["lookahead_bars"] == 4


def test_lookahead_rename_attack_03_system_generated_unknown_still_declares() -> None:
    """系統產生欄但深度不可由 registry 導出（legacy 無數字欄）⇒ 仍須宣告，不得給預設深度。"""
    res = lookahead_resolution(
        "future_max_return", "1h", provenance=PROVENANCE_SYSTEM_GENERATED
    )
    assert res["requires_declaration"] is True
    assert res["lookahead_bars"] is None
    assert res["reason"] == "depth_not_derivable_from_registry"


def test_lookahead_rename_attack_04_unknown_provenance_fail_closed() -> None:
    """provenance 為封閉集合；未知值即 raise，不得靜默當成可信。"""
    with pytest.raises(ValueError):
        lookahead_resolution("future_4bar_return", "1h", provenance="trust_me")
