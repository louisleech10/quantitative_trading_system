"""TESTREG Task 3.3／4.3 驗收：`scripts/testreg.py effect`（docs/TESTREG_SPEC.md；欄位定義 SPEC v17 C9）。
`--out` 寫報告、`--recompute` 由 catalog 碑與 summary 重算逐數字比對；無紀錄 ⇒ 字面 unknown（不寫 0）。實作前為紅。"""
from __future__ import annotations

import importlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.registry.testreg_helpers import TmpRepo, entry, make_repo, schema

testreg = importlib.import_module("scripts.testreg")

REF = "handoffs/reconcile/20261010-testreg-x-review-r16/synth.md"
RCPT = "handoffs/run_receipts/testreg-retire/x.json"


def _rec(dur: float, outcome: str = "passed") -> Dict[str, Any]:
    return {"session_id": str(uuid.uuid4()), "started": "2026-10-01T00:00:00Z", "fingerprint": "a" * 64,
            "duration_class": "b" * 64, "outcome": outcome, "duration_s": dur, "exception_type": None,
            "exception_head": None}


def _repo(tmp_path: Path, summary_nodes: Dict[str, List[Dict[str, Any]]] = None) -> TmpRepo:
    r = make_repo(tmp_path, {"tests/test_keep.py": "def test_k():\n    assert True\n",
                             "tests/feature_engineering/test_gone.py": "def test_g1():\n    assert True\n"
                                                                       "\n\ndef test_g2():\n    assert True\n",
                             "tests/api/test_part.py": "def test_p1():\n    assert True\n\n\ndef test_p2():\n    assert True\n"})
    r.delete("tests/feature_engineering/test_gone.py")
    r.write("tests/api/test_part.py", "def test_p1():\n    assert True\n")
    cat = r.catalog()
    cat["tombstones"] = [
        {"nodeid": "tests/feature_engineering/test_gone.py::test_g1", "evidence_level": "E0", "evidence_receipt": RCPT,
         "replaced_by": [], "disposition_ref": REF},
        {"nodeid": "tests/feature_engineering/test_gone.py::test_g2", "evidence_level": "E1", "evidence_receipt": RCPT,
         "replaced_by": ["tests/test_keep.py::test_k"], "disposition_ref": REF},
        {"nodeid": "tests/api/test_part.py::test_p2", "evidence_level": "E2", "evidence_receipt": RCPT,
         "replaced_by": ["tests/api/test_part.py::test_p1"], "disposition_ref": REF}]
    r.set_catalog(cat)
    s = schema()
    nodes = summary_nodes if summary_nodes is not None else {
        "tests/feature_engineering/test_gone.py::test_g1[a]": [_rec(1.0), _rec(3.0), _rec(2.0)],
        "tests/feature_engineering/test_gone.py::test_g1[b]": [_rec(10.0)],
        "tests/feature_engineering/test_gone.py::test_g2": [_rec(4.0), _rec(100.0, "failed"), _rec(6.0)],
        "tests/api/test_part.py::test_p2": [_rec(0.5)],
        "tests/test_keep.py::test_k": [_rec(9.0)]}
    r.write_json(s["summary"]["path"], {"schema_version": s["version"], "k": s["summary"]["k"], "nodes": nodes})
    return r


def test_effect_report_values(tmp_path):
    r = _repo(tmp_path)
    rep = testreg.effect_report(r.root)
    assert rep["retired_functions"] == 3
    assert rep["retired_files"] == 1  # test_gone.py 已刪且全部函式有碑；test_part.py 仍存在
    assert rep["evidence_levels"] == {"E0": 1, "E1": 1, "E2": 1}
    # test_g1：[a] 中位 2.0＋[b] 10.0；test_g2：passed 之 4.0、6.0 中位 5.0；test_p2：0.5
    assert rep["saved_seconds_per_full_run"] == pytest.approx(2.0 + 10.0 + 5.0 + 0.5)


def test_effect_report_shape(tmp_path):
    r = _repo(tmp_path)
    for rep in (testreg.effect_report(r.root), testreg.effect_report(_repo(tmp_path / "u", {}).root)):
        assert testreg.validate_shape(rep, {"type": "types.effect_report"}, schema()) == []
        assert set(rep["evidence_levels"]) == set(schema()["enums"]["retire_evidence_level"])


BAD_REPORTS = {
    "extra_key": lambda rep: dict(rep, extra=1),
    "wrong_type": lambda rep: dict(rep, retired_functions=str(rep["retired_functions"])),
    "non_finite": lambda rep: dict(rep, saved_seconds_per_full_run=float("nan")),
    "missing_level_key": lambda rep: dict(rep, evidence_levels={k: v for k, v in rep["evidence_levels"].items()
                                                                if k != "E0"}),
}


@pytest.mark.parametrize("case", sorted(BAD_REPORTS))
def test_effect_recompute_rejects_malformed_report(tmp_path, case):
    """手寫報告之未知鍵／錯型／非有限值／缺等級鍵 ⇒ --recompute rc≠0（先驗形再逐欄比對）。"""
    r = _repo(tmp_path)
    rel = "handoffs/run_receipts/testreg-phase3-effect.json"
    assert r.run("effect", "--out", rel).returncode == 0
    rep = json.loads(r.read(rel))
    r.write(rel, json.dumps(BAD_REPORTS[case](rep)))
    proc = r.run("effect", "--recompute", rel)
    assert proc.returncode != 0 and any(l.startswith("EFFECT ") for l in proc.stderr.splitlines()), proc.stderr


def test_effect_scope_prefix(tmp_path):
    r = _repo(tmp_path)
    rep = testreg.effect_report(r.root, ["tests/feature_engineering/"])
    assert rep["scope"] == ["tests/feature_engineering/"] and rep["retired_functions"] == 2
    assert rep["evidence_levels"] == {"E0": 1, "E1": 1, "E2": 0}


def test_effect_out_then_recompute_rc0_and_tamper_red(tmp_path):
    r = _repo(tmp_path)
    rel = "handoffs/run_receipts/testreg-phase3-effect.json"
    assert r.run("effect", "--out", rel, "--scope", "tests/feature_engineering/").returncode == 0
    proc = r.run("effect", "--recompute", rel)
    assert proc.returncode == 0, proc.stderr
    rep = json.loads(r.read(rel))
    rep["retired_functions"] += 1
    r.write_json(rel, rep)
    proc = r.run("effect", "--recompute", rel)
    assert proc.returncode != 0 and any(l.startswith("EFFECT ") for l in proc.stderr.splitlines())


def test_boundary_01_missing_summary_record_unknown_not_zero(tmp_path):
    r = _repo(tmp_path, {"tests/feature_engineering/test_gone.py::test_g1": [_rec(1.0)]})
    rep = testreg.effect_report(r.root)
    assert rep["saved_seconds_per_full_run"] == "unknown"


def test_effect_failed_only_records_unknown(tmp_path):
    """被淘汰 nodeid 只有 failed 紀錄 ⇒ 無 passed 中位可用 ⇒ unknown（不外插）。"""
    nodes = {"tests/feature_engineering/test_gone.py::test_g1": [_rec(1.0)],
             "tests/feature_engineering/test_gone.py::test_g2": [_rec(5.0, "failed")],
             "tests/api/test_part.py::test_p2": [_rec(0.5)]}
    assert testreg.effect_report(_repo(tmp_path, nodes).root)["saved_seconds_per_full_run"] == "unknown"


def test_mutation_report_zero_instead_of_unknown_caught_by_recompute(tmp_path, monkeypatch, capsys):
    """mutant：產報告時把 unknown 寫成 0 ⇒ 以真實實作 --recompute 必 rc≠0（報告不得掩蓋 unknown）。"""
    r = _repo(tmp_path, {"tests/feature_engineering/test_gone.py::test_g1": [_rec(1.0)]})
    rel = "handoffs/run_receipts/testreg-final-effect.json"
    orig = testreg.effect_report

    def zeroing(root, scope=()):
        rep = orig(root, scope)
        if rep["saved_seconds_per_full_run"] == "unknown":
            rep["saved_seconds_per_full_run"] = 0.0
        return rep

    monkeypatch.setattr(testreg, "effect_report", zeroing)
    assert testreg.main(["--repo", str(r.root), "effect", "--out", rel]) == 0
    assert json.loads(r.read(rel))["saved_seconds_per_full_run"] == 0.0
    monkeypatch.undo()
    assert testreg.main(["--repo", str(r.root), "effect", "--recompute", rel]) != 0
    capsys.readouterr()
