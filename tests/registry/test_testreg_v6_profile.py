"""TESTREG Task 2.4 驗收：V-6 慢因收據 `handoffs/run_receipts/testreg-v6-profile.json`（docs/TESTREG_SPEC.md）。
收據由 D10 執行器（記錄器開）與 cProfile 實跑產生；本檔驗其完整性與可證偽欄位。實作前（收據不存在）為紅。"""
from __future__ import annotations

import ast
import json
import re

from tests.registry.testreg_helpers import REPO

RCPT = REPO / "handoffs/run_receipts/testreg-v6-profile.json"
TARGET = "tests/feature_engineering/test_failopen_correctness.py"
CLASSES = {"測試端重複計算", "生產端本身耗時"}


def _v6_functions():
    tree = ast.parse((REPO / TARGET).read_text(encoding="utf-8"))
    return sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_v6_"))


def _missing_items(r) -> list:
    names = {k.split("::")[-1].split("[")[0] for k in r["durations_s"]}
    return sorted(set(_v6_functions()) - names)


def test_v6_profile_receipt_complete():
    r = json.loads(RCPT.read_text(encoding="utf-8"))
    assert _missing_items(r) == []
    assert all(isinstance(v, (int, float)) and v >= 0 for v in r["durations_s"].values())
    slowest = max(r["durations_s"], key=r["durations_s"].get)
    assert r["slowest"] == slowest
    assert len(r["hotspots_top30"]) == 30 and all({"function", "cumtime_s"} <= set(h) for h in r["hotspots_top30"])
    assert r["classification"] in CLASSES
    assert r["evidence"] and all(re.fullmatch(r"[A-Za-z0-9_./-]+\.py:[1-9][0-9]*", e) for e in r["evidence"])
    assert r["window_and_symbols_unchanged"] is True


def test_mutation_unprofiled_v6_item_detected(monkeypatch):
    """mutant：檔中多一支未計時之 test_v6_* ⇒ 完整性檢查必報缺（收據漏項不得過）。"""
    import sys
    r = json.loads(RCPT.read_text(encoding="utf-8"))
    assert _missing_items(r) == []
    mod = sys.modules[__name__]
    real = _v6_functions()
    monkeypatch.setattr(mod, "_v6_functions", lambda: real + ["test_v6_unprofiled_extra"])
    assert _missing_items(r) == ["test_v6_unprofiled_extra"]


def test_v6_test_side_change_requires_mutation_receipt():
    r = json.loads(RCPT.read_text(encoding="utf-8"))
    if r["classification"] == "測試端重複計算" and r.get("test_changed"):
        assert r["outcomes_sha256_before"] == r["outcomes_sha256_after"]
        assert (REPO / r["mutation_receipt"]).is_file()
    else:
        assert not r.get("test_changed")
