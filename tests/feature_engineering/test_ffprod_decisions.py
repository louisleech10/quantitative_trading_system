"""FFPROD Task 2.2：機讀決定紀錄對量測收據（SPEC `docs/FFPROD_SPEC.md` Task 2.1 驗證、Task 2.2）。

`tests/_golden/ffprod/decisions.json`：{"candidates": [{`candidate_id`, `choice`（選項或 `retain`）, `canonical_source`（L2 才有：
`polars_public`｜`pandas_category`）, `changed_targets`（欄名清單）, `user_ruling_ref`（SPEC §A 對應行）, `implemented_commit`（Phase 3
施工後填）}]}。量測收據 `handoffs/run_receipts/<日期>-ffprod-candidates.json`（恰一份）：{"candidates": [{`candidate_id`,
`options`: [{`option`, `run_dir`, `changed_columns`, ...}]}]}。秒級、只讀檔。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest

REPO = Path(__file__).resolve().parents[2]
DECISIONS_PATH = REPO / "tests" / "_golden" / "ffprod" / "decisions.json"
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
L2_SOURCES = ("polars_public", "pandas_category")


def _receipt() -> Dict[str, Any]:
    found = sorted(RECEIPTS_DIR.glob("*-ffprod-candidates.json"))
    assert len(found) == 1, f"量測收據須恰一份，實得 {[p.name for p in found]}"
    return json.loads(found[0].read_text(encoding="utf-8"))


def _decisions() -> List[Dict[str, Any]]:
    assert DECISIONS_PATH.exists(), f"決定紀錄未建立：{DECISIONS_PATH}"
    return list(json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))["candidates"])


def decision_errors(decision: Mapping[str, Any], measured: Mapping[str, Any]) -> List[str]:
    """單一候選之決定紀錄對收據：`retain` ⇒ `changed_targets` 為空；否則 `choice` 須為收據選項之一，`changed_targets`
    （集合）須等於該選項之 `changed_columns`；L2 候選之 `canonical_source` 須屬 `L2_SOURCES` 且等於 `choice`。"""
    errors: List[str] = []
    cid = decision["candidate_id"]
    targets = set(decision["changed_targets"])
    if decision["choice"] == "retain":
        if targets:
            errors.append(f"{cid}：retain 而 changed_targets 非空")
        return errors
    options = {o["option"]: o for o in measured["options"]}
    if decision["choice"] not in options:
        return [f"{cid}：choice {decision['choice']!r} 不屬收據選項 {sorted(options)}"]
    expected = set(options[decision["choice"]]["changed_columns"])
    if targets != expected:
        errors.append(f"{cid}：changed_targets 多 {sorted(targets - expected)[:5]} 少 {sorted(expected - targets)[:5]}")
    if set(options) == set(L2_SOURCES) and decision.get("canonical_source") != decision["choice"]:
        errors.append(f"{cid}：L2 候選之 canonical_source {decision.get('canonical_source')!r} 須等於 choice")
    elif set(options) != set(L2_SOURCES) and "canonical_source" in decision:
        errors.append(f"{cid}：非 L2 候選不得記 canonical_source")
    return errors


def ruling_ref_errors(ref: str, spec_lines: List[str]) -> List[str]:
    """`user_ruling_ref` 須為 `docs/FFPROD_SPEC.md:<行>`，該行位於 §A 段內（`## §A` 至下一個 `## ` 之間）且含使用者逐字「」。"""
    prefix = "docs/FFPROD_SPEC.md:"
    if not ref.startswith(prefix) or not ref[len(prefix):].isdigit():
        return [f"格式不符：{ref!r}"]
    line_no = int(ref[len(prefix):])
    start = next((i for i, s in enumerate(spec_lines, 1) if s.startswith("## §A")), None)
    end = next((i for i, s in enumerate(spec_lines, 1) if start and i > start and s.startswith("## ")), None)
    if start is None or end is None or not (start < line_no < end):
        return [f"{ref} 不在 §A 段內"]
    if "「" not in spec_lines[line_no - 1]:
        return [f"{ref} 該行無使用者逐字引文"]
    return []


# ---------------------------------------------------------------------------------------------- 驗證

def test_decisions_cover_every_measured_candidate() -> None:
    measured = {c["candidate_id"] for c in _receipt()["candidates"]}
    decided = [d["candidate_id"] for d in _decisions()]
    assert len(decided) == len(set(decided))
    assert set(decided) == measured


def test_decisions_match_measured_options() -> None:
    measured = {c["candidate_id"]: c for c in _receipt()["candidates"]}
    errors = [e for d in _decisions() for e in decision_errors(d, measured[d["candidate_id"]])]
    assert errors == []


def test_every_decision_cites_user_ruling() -> None:
    spec_lines = (REPO / "docs" / "FFPROD_SPEC.md").read_text(encoding="utf-8").splitlines()
    errors = [e for d in _decisions() for e in ruling_ref_errors(str(d.get("user_ruling_ref", "")), spec_lines)]
    assert errors == []


# ---------------------------------------------------------------------------------------------- 邊界（Task 2.2）

def test_boundary_07_retain_choice_has_empty_changed_targets() -> None:
    """邊界①：使用者選保留現狀 ⇒ 該候選不施工（`changed_targets` 為空、無 `implemented_commit`）。"""
    for decision in _decisions():
        if decision["choice"] == "retain":
            assert decision["changed_targets"] == []
            assert not decision.get("implemented_commit")


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_extra_or_missing_target_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：決定紀錄之 `changed_targets` 多一欄或少一欄、`canonical_source` 與 choice 不一 ⇒ 對照案轉紅。"""
    measured = {"candidates": [{"candidate_id": "l2",
                                "options": [{"option": "pandas_category", "changed_columns": ["a", "b"]},
                                            {"option": "polars_public", "changed_columns": ["c"]}]}]}
    good = {"candidate_id": "l2", "choice": "pandas_category", "canonical_source": "pandas_category",
            "changed_targets": ["a", "b"], "user_ruling_ref": "§A"}
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_receipt", lambda: measured)
    monkeypatch.setattr(module, "_decisions", lambda: [good])
    test_decisions_match_measured_options()
    missing_source = {k: v for k, v in good.items() if k != "canonical_source"}
    for broken in ({**good, "changed_targets": ["a", "b", "x"]}, {**good, "changed_targets": ["a"]},
                   {**good, "canonical_source": "polars_public"}, {**good, "choice": "retain"}, missing_source):
        monkeypatch.setattr(module, "_decisions", lambda b=broken: [b])
        with pytest.raises(AssertionError):
            test_decisions_match_measured_options()


def test_mutation_ruling_ref_outside_section_a_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：決定紀錄之裁定引用改為任意字串或指到現行 SPEC §A 外之行 ⇒ 引用案轉紅。"""
    spec_lines = (REPO / "docs" / "FFPROD_SPEC.md").read_text(encoding="utf-8").splitlines()
    outside = next(i for i, s in enumerate(spec_lines, 1) if s.startswith("## §C"))
    module = sys.modules[__name__]
    for bad in ("garbage", f"docs/FFPROD_SPEC.md:{outside}", "docs/FFPROD_SPEC.md:1"):
        monkeypatch.setattr(module, "_decisions", lambda b=bad: [{"candidate_id": "x", "user_ruling_ref": b}])
        with pytest.raises(AssertionError):
            test_every_decision_cites_user_ruling()
