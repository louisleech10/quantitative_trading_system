"""TODOFMT Task 2.2：`CLAUDE.md` 與 ORCH 之 TODO 定義同步，且審查強度不被放寬（docs/TODOFMT_SPEC.md Task 2.2）。

- 步驟 1：四項不變式之原文取自 L 之本 SPEC 行首為 `INV || ` 之行（非散文解析），片段須存於現行所屬檔、次數不少於 L。
- 步驟 1b：四份憲法檔相對 L 之新增行不得同時命中審查類與例外類關鍵詞（清單外）。
- 步驟 2–4：TODO 定義字面兩檔一致、`CLAUDE.md` 新增行不寫家數、`templates/`＋`scripts/` 無舊佔位符。
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.governance import _todofmt_anchor as anchor

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = {
    "CLAUDE.md": REPO_ROOT / "CLAUDE.md",
    "docs/MULTI_AGENT_ORCHESTRATION.md": REPO_ROOT / "docs" / "MULTI_AGENT_ORCHESTRATION.md",
    "AGENTS.md": REPO_ROOT / "AGENTS.md",
    ".cursorrules": REPO_ROOT / ".cursorrules",
}
ALLOWLIST = REPO_ROOT / "tests" / "governance" / "fixtures" / "constitution_exception_allowlist.txt"
TODO_DEFINITION = (
    "**TODO＝五類落點 manifest**（`docs/manifests/<EPIC>.json`：生產 stub／具名驗收測試與腳本／契約 JSON／機讀批次卡／實跑收據）"
)
ITEMS = {"i", "ii", "iii", "iv"}
_REVIEW_KW = re.compile(r"審查|對抗|自審|家數")
_EXCEPT_KW = re.compile(r"例外|不適用|可略|免")
_FAMILY_COUNT = re.compile(r"[0-9０-９一二兩三四五六七八九十]+\s*家")


def _current(rel: str) -> str:
    return CONSTITUTION[rel].read_text(encoding="utf-8")


def _added_lines_vs_l(rel: str) -> list[str]:
    """相對 L 之新增行（比較端＝現行工作樹）。"""
    out = subprocess.run(
        ["git", "diff", "--no-color", "-U0", anchor.design_freeze_commit(), "--", rel],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [ln[1:] for ln in out.splitlines() if ln.startswith("+") and not ln.startswith("+++")]


def _allowlisted() -> set[str]:
    if not ALLOWLIST.is_file():
        return set()
    return {ln.strip() for ln in ALLOWLIST.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}


def _invariant_problems() -> list[str]:
    problems: list[str] = []
    lo = anchor.design_freeze_commit()
    rows = anchor.invariant_lines()
    for item, rel, frag in rows:
        if "TODO" in frag:
            problems.append(f"片段含 TODO：{item}：{frag}")
        now = _current(rel).count(frag)
        at_l = (anchor.show(lo, rel) or "").count(frag)
        if now == 0:
            problems.append(f"片段不在現行檔：{item}：{rel}：{frag}")
        elif now < at_l:
            problems.append(f"片段次數減少（L={at_l}，現行={now}）：{item}：{rel}：{frag}")
    missing = ITEMS - {item for item, _, _ in rows}
    if missing:
        problems.append(f"四項中缺：{sorted(missing)}")
    return problems


def test_step1_invariants_hold() -> None:
    assert _invariant_problems() == []


def test_boundary_07_fragment_missing_from_current_file_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item, rel, frag = anchor.invariant_lines()[0]
    weakened = tmp_path / "weakened.md"
    weakened.write_text(_current(rel).replace(frag, ""), encoding="utf-8")
    monkeypatch.setitem(CONSTITUTION, rel, weakened)
    assert any("片段不在現行檔" in p for p in _invariant_problems())


def test_boundary_08_each_of_four_items_has_a_line() -> None:
    assert {item for item, _, _ in anchor.invariant_lines()} == ITEMS


def test_boundary_09_invariant_lines_are_four_columns() -> None:
    for item, rel, frag in anchor.invariant_lines():
        assert item and rel and frag


def test_boundary_10_fragments_do_not_contain_todo() -> None:
    assert not [f for _, _, f in anchor.invariant_lines() if "TODO" in f]


def test_boundary_11_fragment_count_must_not_decrease(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dup = [(i, r, f) for i, r, f in anchor.invariant_lines() if _current(r).count(f) >= 2]
    assert dup, "前提：至少一條片段於現行檔出現兩次以上（`；實作者不自審`）"
    item, rel, frag = dup[0]
    text = _current(rel)
    once_removed = text.replace(frag, "", 1)
    weakened = tmp_path / "weakened.md"
    weakened.write_text(once_removed, encoding="utf-8")
    monkeypatch.setitem(CONSTITUTION, rel, weakened)
    assert any("次數減少" in p for p in _invariant_problems())


def test_step1b_no_new_exception_clause_outside_allowlist() -> None:
    allow = _allowlisted()
    hits = []
    for rel in CONSTITUTION:
        for line in _added_lines_vs_l(rel):
            if _REVIEW_KW.search(line) and _EXCEPT_KW.search(line):
                if hashlib.sha256(line.encode("utf-8")).hexdigest() not in allow:
                    hits.append(f"{rel}: {line}")
    assert hits == [], hits


def _definition_lines(rel: str) -> list[str]:
    return [ln for ln in _current(rel).splitlines() if ln.startswith(TODO_DEFINITION)]


def test_step2_todo_definition_identical_in_claude_and_orch() -> None:
    """兩檔各恰一行以該定義開頭，且整行逐字相等（b2 審碼 grok：只比前綴時句尾分叉看不見）。"""
    claude, orch = _definition_lines("CLAUDE.md"), _definition_lines("docs/MULTI_AGENT_ORCHESTRATION.md")
    assert len(claude) == 1 and len(orch) == 1, (claude, orch)
    assert claude == orch


def test_step3_no_family_count_added_to_claude_md() -> None:
    assert not [ln for ln in _added_lines_vs_l("CLAUDE.md") if _FAMILY_COUNT.search(ln)]


def test_step4_no_old_placeholder_in_templates_or_scripts() -> None:
    hits = subprocess.run(
        ["grep", "-rlF", "docs/X_TODO.md", "templates", "scripts"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert hits == []


def test_boundary_04_spec_todo_flag_note_still_present() -> None:
    assert "`--spec/--todo`" in _current("CLAUDE.md")


def test_boundary_05_trigger_sentence_still_present() -> None:
    assert "SPEC/TODO 範本 → `templates/`" in _current("CLAUDE.md")


def test_mutation_weakening_one_invariant_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """把 `CLAUDE.md` 之「不得跳步」字句刪去 ⇒ 步驟 1 報錯（證快照比對有鑑別力）。"""
    rows = [(i, r, f) for i, r, f in anchor.invariant_lines() if i == "iv" and r == "CLAUDE.md"]
    assert rows
    text = _current("CLAUDE.md")
    for _, _, frag in rows:
        text = text.replace(frag, "")
    weakened = tmp_path / "CLAUDE.md"
    weakened.write_text(text, encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "CONSTITUTION", {**CONSTITUTION, "CLAUDE.md": weakened})
    assert _invariant_problems() != []
