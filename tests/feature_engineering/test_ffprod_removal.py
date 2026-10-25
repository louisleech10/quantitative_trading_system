"""FFPROD Task 1.1：刪除無生產呼叫者之並存實作（SPEC `docs/FFPROD_SPEC.md` Task 0.1、Task 1.1）。

讀 Task 0.1 一次性盤點收據 `handoffs/run_receipts/<日期>-ffprod-inventory.json`（恰一份）。收據 `items[]` 每項至少含：
`path`、`function`、`disposition`（`keep`｜`remove`｜`measure`）、`scripts_callers`（只由 `scripts/` 呼叫之檔清單）、
`disabled_scripts`（[{`path`, `reason`}]，已停用而保留之腳本）、`string_lookup`（字串查表呼叫之字面清單）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pytest

REPO = Path(__file__).resolve().parents[2]
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
#: Task 1.1 驗證之零命中範圍（SPEC：`grep -rn` 於 `momentum api tests`）。
SEARCH_ROOTS = ("momentum", "api", "tests")


def _inventory() -> Dict[str, Any]:
    found = sorted(RECEIPTS_DIR.glob("*-ffprod-inventory.json"))
    assert len(found) == 1, f"盤點收據須恰一份，實得 {[p.name for p in found]}"
    return json.loads(found[0].read_text(encoding="utf-8"))


def _removed() -> List[Dict[str, Any]]:
    return [item for item in _inventory()["items"] if item["disposition"] == "remove"]


def _pattern(name: str) -> "re.Pattern[str]":
    return re.compile(rf"\b{re.escape(name)}\b")


def _references(name: str, roots: Iterable[str]) -> List[str]:
    """以字詞邊界搜尋 `name` 於 `roots`（目錄或單一 .py 檔）之 .py 檔，回傳命中之 `path:line`（排除本檔）。"""
    pattern = _pattern(name)
    hits: List[str] = []
    for root in roots:
        base = Path(root) if Path(root).is_absolute() else REPO / root
        files = [base] if base.is_file() else sorted(base.rglob("*.py"))
        for path in files:
            if path.resolve() == Path(__file__).resolve():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if pattern.search(line):
                    hits.append(f"{path}:{lineno}")
    return hits


# ---------------------------------------------------------------------------------------------- 驗證

def test_removed_functions_have_no_references() -> None:
    removed = _removed()
    assert removed, "盤點收據無 remove 項"
    leftovers = {item["function"]: _references(item["function"], SEARCH_ROOTS) for item in removed}
    assert {k: v for k, v in leftovers.items() if v} == {}


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_05_scripts_only_callers_rewritten_or_disabled() -> None:
    """邊界①：只由 `scripts/` 呼叫之實作被刪 ⇒ 該腳本已改寫（不再引用）或列於 `disabled_scripts` 並附理由。"""
    problems = []
    for item in _removed():
        disabled = {d["path"]: d["reason"] for d in item.get("disabled_scripts", [])}
        for script in item.get("scripts_callers", []):
            if script in disabled:
                assert str(disabled[script]).strip(), f"{script} 停用無理由"
                continue
            if _references(item["function"], [script]):
                problems.append(f"{item['function']} 仍被 {script} 引用且未列停用")
    assert problems == []


def test_boundary_06_string_lookup_callers_counted() -> None:
    """邊界②：只經字串查表呼叫者（如 `rolling_aggregator.AGGREGATORS`）以字串字面計為呼叫者——被刪者之查表字面亦須零命中。"""
    problems = []
    for item in _removed():
        for literal in item.get("string_lookup", []):
            hits = _references(literal, ["momentum", "api"])
            if hits:
                problems.append(f"{item['function']}：查表字面 {literal!r} 仍命中 {hits[:3]}")
    assert problems == []


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_reference_search_detects_planted_caller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：搜尋樣式換成永不命中 ⇒ 植入之呼叫漏抓（證零命中斷言確由字詞樣式承擔，而非恆空）。"""
    planted = tmp_path / "caller.py"
    planted.write_text("from x import _ffprod_dead_impl\n_ffprod_dead_impl()\n", encoding="utf-8")
    assert len(_references("_ffprod_dead_impl", [str(tmp_path)])) == 2
    monkeypatch.setattr(sys.modules[__name__], "_pattern", lambda _name: re.compile(r"(?!x)x"))
    assert _references("_ffprod_dead_impl", [str(tmp_path)]) == []
