"""FKPERF：GOVB1 g2／g3 對新核心之同等檢查（docs/FKPERF_SPEC.md Task 4.3、C-9）。

g2（consumer 字面分母）與 g3（停用開關）按路徑掃描 `gen_fact_key_blocks.sh`，其掃描清單屬硬保護集不得改；
核心移入 `scripts/_gen_fact_key_blocks.py` 後由本檔施加同等判定。量詞集合與樣式一律讀
`scripts/govb1_final_gate.sh` 之定義行（單一來源，不另抄）。存活至 GOVB1 復工、manifest 納入核心為止。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, List

import pytest

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "govb1_final_gate.sh"
CORE = REPO / "scripts" / "_gen_fact_key_blocks.py"


def _gate_text() -> str:
    return GATE.read_text(encoding="utf-8")


def g2_units(read: Callable[[], str] = _gate_text) -> str:
    """`_G2_UNITS='…'` 定義行之量詞集合；找不到定義即 fail-closed（不得靜默回空）。"""
    m = re.search(r"^_G2_UNITS='([^']+)'", read(), re.M)
    assert m, "govb1_final_gate.sh 之 _G2_UNITS 定義行找不到 ⇒ fail-closed"
    return m.group(1)


def g3_pattern(read: Callable[[], str] = _gate_text) -> str:
    """`_g3()` 內 `grep -rnqE '…'` 之停用開關樣式；找不到即 fail-closed。"""
    m = re.search(r"^_g3\(\) \{ ! grep -rnqE '([^']+)'", read(), re.M)
    assert m, "govb1_final_gate.sh 之 _g3 樣式找不到 ⇒ fail-closed"
    return m.group(1)


def g2_hits(text: str, units: str) -> List[str]:
    """同 `_frozen_hits`：`[0-9]+[[:space:]]*(units)`，含註解行（照 g2 現行語意）。"""
    rx = re.compile(r"[0-9]+\s*(?:" + units + r")")
    return [ln for ln in text.splitlines() if rx.search(ln)]


def g3_hits(text: str, pattern: str) -> List[str]:
    rx = re.compile(pattern.replace("[[:space:]]", r"\s"))
    return [ln for ln in text.splitlines() if rx.search(ln)]


# ---------------------------------------------------------------- Task 4.3 驗證

def test_core_has_no_g2_literal_denominators() -> None:
    """Task 4.3 驗證：核心檔無 g2 所禁之字面分母。"""
    assert g2_hits(CORE.read_text(encoding="utf-8"), g2_units()) == []


def test_core_has_no_g3_disable_switch() -> None:
    """Task 4.3 驗證：核心檔無 g3 所禁之停用開關樣式。"""
    assert g3_hits(CORE.read_text(encoding="utf-8"), g3_pattern()) == []


def test_injected_literal_and_switch_are_detected(tmp_path: Path) -> None:
    """Task 4.3 驗證：核心注入 `18 份` ⇒ g2 命中；注入 `WARN_ONLY` ⇒ g3 命中；原文 ⇒ 皆不命中。"""
    src = CORE.read_text(encoding="utf-8")
    assert g2_hits(src + "\nx = 1  # 共 18 份\n", g2_units())
    assert g3_hits(src + "\nWARN_ONLY = True\n", g3_pattern())
    assert not g2_hits(src, g2_units()) and not g3_hits(src, g3_pattern())


# ---------------------------------------------------------------- 邊界（Task 4.3）

def test_boundary_31_units_definition_missing_fails_closed() -> None:
    """Task 4.3 邊界①：`_G2_UNITS` 定義行格式改變 ⇒ fail-closed（找不到定義），不得靜默回空而綠。"""
    mangled = _gate_text().replace("_G2_UNITS='", "_G2_UNIT_SET='", 1)
    with pytest.raises(AssertionError, match="找不到"):
        g2_units(lambda: mangled)


def test_boundary_32_literal_inside_comment_counts() -> None:
    """Task 4.3 邊界②：註解中的字面照 g2 現行語意計入。"""
    assert g2_hits("# 這裡寫了 18 份\n", g2_units()) == ["# 這裡寫了 18 份"]


def test_mutation_units_reader_swapped_to_empty_set_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """鑑別力：把定義來源換成不含 `_G2_UNITS` 之文字 ⇒ 判定 fail-closed，不會空集合而綠。"""
    import tests.governance.test_fkperf_govb1_equiv as me
    monkeypatch.setattr(me, "_gate_text", lambda: "# no definition\n")
    with pytest.raises(AssertionError):
        me.g2_units(me._gate_text)
