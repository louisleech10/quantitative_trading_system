"""TODOFMT Task 2.1：`templates/TODO_GENERATION_PROMPT.md` 改寫為五類落點（docs/TODOFMT_SPEC.md Task 2.1）。

每條邊界一個 grep 式機械斷言；判定集中於 `_violations()`，mutation 探針以 monkeypatch 換入改壞之範本後重跑同一判定。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = REPO_ROOT / "templates" / "TODO_GENERATION_PROMPT.md"

OLD_TODO_LITERAL = "docs/X_TODO.md"
CATEGORY_KEYS = ("stub_modules", "test_files", "script_acceptance", "contract_jsons", "batch_card", "run_receipts")
REASONS = ("blocked-by", "user-ruling", "needs-research")
_TASK_BLOCK = re.compile(r"^#{2,4}\s*Task\b", re.M)
_OLD_ANCHORS = re.compile(r"^## §0|^## §B", re.M)
_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")
_TABLE_VAR = re.compile(r"^\|\s*\{\{([A-Z_]+)\}\}\s*\|", re.M)


def _text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _violations(text: str) -> list[str]:
    out: list[str] = []
    if OLD_TODO_LITERAL in text:
        out.append("b1_old_todo_literal")
    if _TASK_BLOCK.search(text):
        out.append("b2_markdown_task_block")
    if any(k not in text for k in CATEGORY_KEYS):
        out.append("b3_category_missing")
    if any(r not in text for r in REASONS):
        out.append("b4_reason_missing")
    if _OLD_ANCHORS.search(text) or "{{TODO_FILE}}" in text:
        out.append("b5_old_and_new_coexist")
    if set(_PLACEHOLDER.findall(text)) != set(_TABLE_VAR.findall(text)):
        out.append("b6_placeholder_undeclared_or_unused")
    return out


def test_template_has_no_violation() -> None:
    assert _violations(_text()) == []


def test_boundary_01_old_todo_literal_absent() -> None:
    assert _text().count(OLD_TODO_LITERAL) == 0


def test_boundary_02_no_markdown_task_block() -> None:
    assert not _TASK_BLOCK.search(_text())


@pytest.mark.parametrize("key", CATEGORY_KEYS)
def test_boundary_03_each_category_described(key: str) -> None:
    assert key in _text()


@pytest.mark.parametrize("reason", REASONS)
def test_boundary_04_not_executable_three_reasons(reason: str) -> None:
    text = _text()
    assert "not_executable" in text and reason in text


def test_boundary_05_old_format_not_coexisting() -> None:
    text = _text()
    assert not _OLD_ANCHORS.search(text)
    assert "{{TODO_FILE}}" not in text


def test_boundary_06_placeholders_all_declared_and_used() -> None:
    text = _text()
    assert set(_PLACEHOLDER.findall(text)) == set(_TABLE_VAR.findall(text))


@pytest.mark.parametrize(
    "injected,expected",
    [
        (f"\n另見 {OLD_TODO_LITERAL}\n", "b1_old_todo_literal"),
        ("\n### Task 1.1 — 舊式區塊\n", "b2_markdown_task_block"),
        ("\n## §0 全域規則\n", "b5_old_and_new_coexist"),
        ("\n用 {{UNDECLARED_VAR}}\n", "b6_placeholder_undeclared_or_unused"),
    ],
)
def test_mutation_injecting_old_format_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, injected: str, expected: str
) -> None:
    """把舊格式片段注入範本複本 ⇒ 同一判定須報出對應邊界（證各邊界斷言有鑑別力）。"""
    mutant = tmp_path / "TODO_GENERATION_PROMPT.md"
    mutant.write_text(_text() + injected, encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "TEMPLATE", mutant)
    assert expected in _violations(_text())
