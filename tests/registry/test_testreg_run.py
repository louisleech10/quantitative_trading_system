"""TESTREG Task 3.2／4.2 驗收：子批閘 `scripts/testreg.py run`（docs/TESTREG_SPEC.md；契約 `subbatch_gate`、
`types.subbatch_receipt`）。

暫存倉以真實 pytest 子行程執行（`framepath_affected_gate.Runner`）；base＝子批前提交。驗：收據形狀與欄間關係、只跑
impact 選中之檔、子批造成之紅擋下、base 既有紅（同失敗特徵）不擋、分段暫停後同命令接續（未變之檔沿用、改變之檔重跑）。
實作前為紅。"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict

from tests.registry.testreg_helpers import TmpRepo, make_repo, schema

testreg = importlib.import_module("scripts.testreg")
g = importlib.import_module("scripts.framepath_affected_gate")

FILES = {
    "momentum/__init__.py": "",
    "momentum/m.py": "def f():\n    return 1\n",
    "tests/test_rw.py": "from momentum.m import f\n\n\ndef test_r1():\n    assert f() == 1\n\n\ndef test_red():\n    assert f() == 2\n",
    "tests/test_other.py": "def test_o():\n    assert True\n",
    "tests/test_untouched.py": "def test_u():\n    assert True\n",
}
SLOW_OTHER = "import time\n\n\ndef test_o():\n    time.sleep(1.2)\n    assert True\n"
MAN = "docs/manifests/T.json"
RCPT = "handoffs/run_receipts/testreg-run.json"


def _repo(tmp_path: Path, files: Dict[str, str] = None) -> TmpRepo:
    r = make_repo(tmp_path, files or FILES)
    r.write_json(MAN, {"spec_path": "docs/T_SPEC.md", "batch_card": {"gate_cmd": "x", "risk_mitigation": [
        "affected_tests phase=3 tests/test_rw.py"]}})
    r.commit("manifest")
    return r


def _run(r: TmpRepo, base: str, tmp_path: Path, *extra: str):
    proc = r.run("run", "--manifest", MAN, "--phase", "3", "--base", base, "--receipt", RCPT,
                 "--out", str(tmp_path / "out"), *extra)
    rcpt = json.loads(r.read(RCPT)) if r.p(RCPT).exists() else None
    return proc, rcpt


def _relations(rcpt: Dict[str, Any]) -> None:
    """契約 subbatch_gate 所列欄間關係（獨立重算）。"""
    sel = {x["path"] for x in rcpt["selection"]["selected"]}
    assert set(rcpt["files"]) == sel
    assert all(n.split("::")[0] in sel for n in rcpt["expected"])
    assert set(rcpt["results"]) <= set(rcpt["expected"])
    assert rcpt["missing"] == sorted(n for n in rcpt["expected"] if n not in rcpt["results"])
    bad = {n for n, o in rcpt["results"].items() if o != "passed"}
    assert not set(rcpt["caused"]) & set(rcpt["head_red"]) and set(rcpt["caused"]) | set(rcpt["head_red"]) == bad
    assert rcpt["pass"] == (not rcpt["caused"] and not rcpt["missing"] and not rcpt["incomplete_files"])


def test_run_receipt_shape_and_relations(tmp_path):
    r = _repo(tmp_path)
    base = r.head()
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"].replace("assert f() == 1\n", "assert f() == 1\n    assert f() > 0\n"))
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert testreg.validate_shape(rcpt, {"type": "types.subbatch_receipt"}, schema()) == []
    _relations(rcpt)
    assert rcpt["base"] == base and rcpt["head"] == r.head() and rcpt["phase"] == 3
    assert "tests/test_rw.py" in rcpt["changed_paths"]


def test_run_selects_changed_file_only_and_passes(tmp_path):
    r = _repo(tmp_path)
    base = r.head()
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"].replace("assert f() == 1\n", "assert f() == 1\n    assert f() > 0\n"))
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert set(rcpt["files"]) == {"tests/test_rw.py"}
    assert rcpt["head_red"] == ["tests/test_rw.py::test_red"] and rcpt["caused"] == [] and rcpt["pass"] is True


def test_run_subbatch_caused_red_blocks(tmp_path):
    r = _repo(tmp_path)
    base = r.head()
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"].replace("assert f() == 1\n", "assert f() == 3\n"))
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 1 and rcpt["caused"] == ["tests/test_rw.py::test_r1"] and rcpt["pass"] is False
    _relations(rcpt)


def test_run_inputs_digest_binds_base(tmp_path):
    r = _repo(tmp_path)
    first = r.head()
    r.write("tests/test_untouched.py", "def test_u():\n    assert 1 == 1\n")
    second = r.commit("advance")
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"] + "\n\ndef test_more():\n    assert True\n")
    _, a = _run(r, first, tmp_path / "a")
    _, b = _run(r, second, tmp_path / "b")
    assert a["inputs_digest"] != b["inputs_digest"]


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


def _two_file_change(r: TmpRepo) -> None:
    r.write("tests/test_rw.py", FILES["tests/test_rw.py"] + "\n\ndef test_more():\n    assert True\n")
    r.write("tests/test_other.py", SLOW_OTHER + "\n\ndef test_o2():\n    assert True\n")


def test_boundary_02_pause_then_same_command_resumes_without_restart(tmp_path):
    """--max-seconds 0.5：第一段跑完第一個檔（test_other 內含 1.2 秒）即於呼叫之間停下（rc 3、progress paused）；
    同命令接續 ⇒ 已完成之檔沿用（reused）、其餘執行，最終 rc 0。"""
    r = _repo(tmp_path, {**FILES, "tests/test_other.py": SLOW_OTHER})
    base = r.head()
    _two_file_change(r)
    proc, _ = _run(r, base, tmp_path, "--max-seconds", "0.5")
    assert proc.returncode == 3, proc.stdout + proc.stderr
    progress = json.loads((tmp_path / "out" / "progress.json").read_text(encoding="utf-8"))
    assert progress["state"] == "paused"
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 0 and rcpt["pass"] is True
    assert rcpt["files"]["tests/test_other.py"]["reused"] is True
    assert rcpt["files"]["tests/test_rw.py"]["reused"] is False


def test_resume_after_change_reruns_changed_file(tmp_path):
    r = _repo(tmp_path, {**FILES, "tests/test_other.py": SLOW_OTHER})
    base = r.head()
    _two_file_change(r)
    proc, _ = _run(r, base, tmp_path, "--max-seconds", "0.5")
    assert proc.returncode == 3
    r.write("tests/test_other.py", r.read("tests/test_other.py") + "\n\ndef test_o3():\n    assert True\n")
    proc, rcpt = _run(r, base, tmp_path)
    assert proc.returncode == 0
    assert rcpt["files"]["tests/test_other.py"]["reused"] is False
    assert "tests/test_other.py::test_o3" in rcpt["expected"] and rcpt["results"]["tests/test_other.py::test_o3"] == "passed"
