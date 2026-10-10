"""TESTREG Task 3.2／4.2 驗收：子批閘 `scripts/testreg.py run`（docs/TESTREG_SPEC.md v17 C3）。

暫存倉以真實 pytest 子行程執行（`framepath_affected_gate.Runner`）；base＝子批前提交。驗：只跑 impact 選中之檔、子批造成
之紅擋下、base 既有紅（同失敗特徵）不擋、分段暫停後同命令接續沿用。實作前為紅。"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from tests.registry.testreg_helpers import TmpRepo, make_repo

testreg = importlib.import_module("scripts.testreg")
g = importlib.import_module("scripts.framepath_affected_gate")

FILES = {
    "momentum/__init__.py": "",
    "momentum/m.py": "def f():\n    return 1\n",
    "tests/test_rw.py": "from momentum.m import f\n\n\ndef test_r1():\n    assert f() == 1\n\n\ndef test_red():\n    assert f() == 2\n",
    "tests/test_other.py": "def test_o():\n    assert True\n",
}
MAN = "docs/manifests/T.json"


def _repo(tmp_path: Path) -> TmpRepo:
    r = make_repo(tmp_path, FILES)
    r.write_json(MAN, {"spec_path": "docs/T_SPEC.md", "batch_card": {"gate_cmd": "x", "risk_mitigation": [
        "affected_tests phase=3 tests/test_rw.py"]}})
    r.commit("manifest")
    return r


def _run(r: TmpRepo, base: str, tmp_path: Path, *extra: str):
    rel = "handoffs/run_receipts/testreg-run.json"
    proc = r.run("run", "--manifest", MAN, "--phase", "3", "--base", base, "--receipt", rel,
                 "--out", str(tmp_path / "out"), *extra)
    rcpt = json.loads(r.read(rel)) if r.p(rel).exists() else None
    return proc, rcpt


def test_run_selects_changed_file_only_and_passes(tmp_path):
    r = _repo(tmp_path)
    base = r.head()
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"].replace("assert f() == 1\n", "assert f() == 1\n    assert f() > 0\n"))
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    files = {x["path"] for x in rcpt["selection"]["selected"]}
    assert files == {"tests/test_rw.py"}
    assert rcpt["head_red"] == ["tests/test_rw.py::test_red"] and rcpt["caused"] == [] and rcpt["pass"] is True


def test_run_subbatch_caused_red_blocks(tmp_path):
    r = _repo(tmp_path)
    base = r.head()
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"].replace("assert f() == 1\n", "assert f() == 3\n"))
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 1 and rcpt["caused"] == ["tests/test_rw.py::test_r1"] and rcpt["pass"] is False


def test_mutation_no_base_comparison_counts_head_red_as_caused(tmp_path, monkeypatch, capsys):
    """mutant：歸屬不比 base（非綠一律本子批造成）⇒ base 既有紅之案被擋。"""
    r = _repo(tmp_path)
    base = r.head()
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"] + "\n\ndef test_more():\n    assert True\n")
    monkeypatch.setattr(g, "classify", lambda expected, batch, anchor: {
        "missing": [], "unexpected": [], "caused": [n for n in expected if batch[n]["outcome"] != "passed"],
        "head_red": [], "passed": [n for n in expected if batch[n]["outcome"] == "passed"]})
    rc = testreg.run_subbatch(r.root, MAN, 3, base, out=tmp_path / "out_m", receipt=r.p("handoffs/run_receipts/m.json"))
    assert rc == 1
    capsys.readouterr()


def test_boundary_02_pause_then_same_command_resumes_without_restart(tmp_path):
    r = _repo(tmp_path)
    base = r.head()
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"] + "\n\ndef test_more():\n    assert True\n")
    r.write("tests/test_other.py", "def test_o():\n    assert True\n\n\ndef test_o2():\n    assert True\n")
    proc, _ = _run(r, base, tmp_path, "--max-seconds", "0")
    assert proc.returncode == 3, proc.stdout + proc.stderr
    progress = json.loads((tmp_path / "out" / "progress.json").read_text(encoding="utf-8"))
    assert progress["state"] == "paused"
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 0 and rcpt["pass"] is True
    assert {x["path"] for x in rcpt["selection"]["selected"]} == {"tests/test_rw.py", "tests/test_other.py"}
