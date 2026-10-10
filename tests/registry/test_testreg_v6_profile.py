"""TESTREG Task 2.4 驗收：V-6 慢因收據 `handoffs/run_receipts/testreg-v6-profile.json`（docs/TESTREG_SPEC.md；契約
`v6_profile`、`types.v6_profile_receipt`）。收據由 D10 執行器（記錄器開）與 cProfile 實跑產生；`_v6_errors` 為獨立於
產生器之檢查（形狀、函式層名集合恰等於 AST 導出之 test_v6_*、slowest、改測試之收據條件），以合成收據之反例證其鑑別力。
實作前（收據不存在、validate_shape 為空殼）為紅。"""
from __future__ import annotations

import ast
import copy
import importlib
import json
import math
import sys
from typing import Any, Dict, List

import pytest

from tests.registry.testreg_helpers import REPO, schema

testreg = importlib.import_module("scripts.testreg")
RCPT = REPO / "handoffs/run_receipts/testreg-v6-profile.json"
TARGET = "tests/feature_engineering/test_failopen_correctness.py"


def _v6_functions() -> List[str]:
    tree = ast.parse((REPO / TARGET).read_text(encoding="utf-8"))
    return sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_v6_"))


def _v6_errors(r: Dict[str, Any]) -> List[str]:
    errs = list(testreg.validate_shape(r, {"type": "types.v6_profile_receipt"}, schema()))
    if errs:
        return errs
    names = {k.split("::")[-1].split("[")[0] for k in r["durations_s"]}
    if any(not k.startswith(TARGET + "::") for k in r["durations_s"]) or names != set(_v6_functions()):
        errs.append("durations_s 之函式層名集合 ≠ AST 導出之 test_v6_*")
    if r["slowest"] != max(r["durations_s"], key=r["durations_s"].get):
        errs.append("slowest ≠ 最慢項")
    if r["classification"] == schema()["enums"]["v6_classification"][0] and r["test_changed"]:
        if r["outcomes_sha256_before"] != r["outcomes_sha256_after"] or not r["mutation_receipt"] \
                or not (REPO / r["mutation_receipt"]).is_file():
            errs.append("改測試須 outcome 不變且附 mutation 收據")
    elif r["test_changed"]:
        errs.append("生產端歸類不得改測試")
    return errs


def _synthetic() -> Dict[str, Any]:
    fns = _v6_functions()
    durs = {f"{TARGET}::{n}": float(i + 1) for i, n in enumerate(fns)}
    return {"durations_s": durs, "slowest": max(durs, key=durs.get),
            "hotspots_top30": [{"function": f"m.py:{i}(f)", "cumtime_s": float(30 - i)} for i in range(30)],
            "classification": schema()["enums"]["v6_classification"][1], "evidence": ["momentum/x.py:10"],
            "window_and_symbols_unchanged": True, "test_changed": False, "outcomes_sha256_before": None,
            "outcomes_sha256_after": None, "mutation_receipt": None}


def test_v6_profile_receipt_complete():
    r = json.loads(RCPT.read_text(encoding="utf-8"))
    assert _v6_errors(r) == []
    assert r["window_and_symbols_unchanged"] is True


def test_synthetic_valid_receipt_passes():
    assert _v6_errors(_synthetic()) == []


SYNTH_NEGATIVES = {
    "extra_node": lambda r: (r["durations_s"].__setitem__(f"{TARGET}::test_v6_fake", 999.0),
                             r.__setitem__("slowest", f"{TARGET}::test_v6_fake")),
    "missing_node": lambda r: r["durations_s"].pop(sorted(r["durations_s"])[0]),
    "non_finite_hotspot": lambda r: r["hotspots_top30"][0].__setitem__("cumtime_s", math.inf),
    "string_hotspot": lambda r: r["hotspots_top30"][0].__setitem__("cumtime_s", "1.0"),
    "only_29_hotspots": lambda r: r["hotspots_top30"].pop(),
    "extra_top_level_key": lambda r: r.__setitem__("note", "x"),
    "slowest_wrong": lambda r: r.__setitem__("slowest", min(r["durations_s"], key=r["durations_s"].get)),
    "production_class_but_test_changed": lambda r: r.__setitem__("test_changed", True),
}


@pytest.mark.parametrize("case", sorted(SYNTH_NEGATIVES))
def test_synthetic_negative_receipts_rejected(case):
    r = copy.deepcopy(_synthetic())
    SYNTH_NEGATIVES[case](r)
    assert _v6_errors(r) != []


def test_mutation_unprofiled_v6_item_detected(monkeypatch):
    """mutant：檔中多一支未計時之 test_v6_* ⇒ 完整性檢查必報（收據漏項不得過）。"""
    r = _synthetic()
    assert _v6_errors(r) == []
    real = _v6_functions()
    monkeypatch.setattr(sys.modules[__name__], "_v6_functions", lambda: real + ["test_v6_unprofiled_extra"])
    assert _v6_errors(r) != []
