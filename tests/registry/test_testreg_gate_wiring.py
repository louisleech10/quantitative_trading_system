"""TESTREG Task 2.3 驗收：`scripts/framepath_affected_gate.py` 吃 impact 聯集、解析碑、判隔離失敗、修接續指紋
（docs/TESTREG_SPEC.md；schema `impact.gate_wiring`／`gate_feed`、`gate_report`、`manifest_status`）。

落點（SPEC v17 C1）：本檔取代 v16 所寫「test_framepath_disposition.py -k affected_gate 新增案例」——該檔為 FRAMEPATH
凍結之驗收測試（⓪ sha256 與 history_freeze_order），FRAMEPATH b1 生產提交後任何改動即紅；既有 affected_gate 案例
維持不動且須保持綠（回歸）。

閘之新增具名縫（呼叫端以模組屬性取用）：`resolve_tombstones`、`expanded_nodeids`、`must_missing`、`quarantine_active`、
`quarantine_match`、`split_quarantined`、`current_failures`、`out_exclusion`、`check_out_dir`、`changed_paths`、
`impact_universe_errors`、`validate_plan_receipt`；plan 經 `scripts.testreg.impact` 取 impact（模組屬性）。
`current_failures(ledger_dir, before_names, test_file)`＝契約 `gate_report.current_failure_source`：只取呼叫前不存在、且
`argv_raw` 有 token 等於該測試檔或以「該測試檔::」開頭之 session 之 failed／error test_record；`split_quarantined` 對
current 中無紀錄之 caused nodeid 一律不吸收。編排：`Runner(out, max_seconds, total, ledger_dir=…)` 於每次 pytest 呼叫前
記 ledger 檔名集合於 `runner.ledger_snapshots[test_file]`（沿用之結果另記於 meta）；`classify_quarantine(caused, runner,
catalog, ledger_dir, today)` 以之呼叫 `current_failures` 與 `split_quarantined`（皆模組屬性），verdict 前使用。
實作前為紅（AttributeError 或斷言）。
"""
from __future__ import annotations

import ast
import datetime as dt
import importlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.registry.testreg_helpers import REPO, TmpRepo, clean_env, entry, fact_keys_rows, make_repo, schema

g = importlib.import_module("scripts.framepath_affected_gate")
testreg = importlib.import_module("scripts.testreg")

REF = "handoffs/reconcile/20261010-testreg-x-review-r16/synth.md"
FUTURE, PAST = "2999-12-31", "2000-01-01"
TODAY = dt.date(2026, 10, 10)
GATE_FILES = {
    "momentum/__init__.py": "",
    "momentum/m.py": "def f():\n    return 1\n",
    "tests/test_keep.py": "from momentum.m import f\n\n\ndef test_k():\n    assert f() == 1\n",
    "tests/test_old.py": "def test_o():\n    assert 1 + 1 == 2\n",
    "tests/test_new.py": "def test_n():\n    assert 1 + 1 == 2\n",
    g.DISPOSITION_REL: json.dumps({"operations": [], "nodeids": []}),
}
ROWS = ["affected_tests phase=1 tests/test_old.py tests/test_keep.py", "affected_groups phase=1 C=tests/test_keep.py",
        "affected_must phase=1 tests/test_old.py::test_o"]


def _manifest(rows=ROWS) -> Dict[str, Any]:
    return {"spec_path": "docs/FRAMEPATH_SPEC.md", "batch_card": {"risk_mitigation": list(rows),
                                                                 "gate_cmd": "PYTHONPATH=. venv/bin/python "
                                                                             "scripts/framepath_affected_gate.py"}}


def _tomb(nodeid: str, replaced_by: List[str], level: str = "E1") -> Dict[str, Any]:
    return {"nodeid": nodeid, "evidence_level": level, "evidence_receipt": "handoffs/run_receipts/testreg-retire/x.json",
            "replaced_by": replaced_by, "disposition_ref": REF}


def _fake_collect(test_file: str, cwd, env) -> List[str]:
    p = Path(cwd) / test_file
    if not p.is_file():
        raise g.GateError(f"{test_file} 收集失敗或為空")
    tree = ast.parse(p.read_text(encoding="utf-8"))
    return [f"{test_file}::{n.name}" for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]


@pytest.fixture
def gate_repo(tmp_path, monkeypatch):
    """錨點＝初始提交；工作樹刪除 tests/test_old.py 並立跨檔 E1 碑（replaced_by tests/test_new.py::test_n）。"""
    r = make_repo(tmp_path, GATE_FILES)
    anchor = r.head()
    r.delete("tests/test_old.py")
    r.add_tombstone(_tomb("tests/test_old.py::test_o", ["tests/test_new.py::test_n"]))
    monkeypatch.setattr(g, "collect", _fake_collect)
    monkeypatch.setattr(g, "production_changes", lambda repo, anc: (set(), set(), [], []))
    return {"repo": r, "anchor": anchor, "env": clean_env(), "out": tmp_path / "gate_out"}


def _plan(fx, manifest=None) -> Dict[str, Any]:
    return g.plan(fx["repo"].root, fx["anchor"], 1, manifest or _manifest(), fx["env"], [], out=fx["out"])


# ── ①⑪ 碑解析於 collect 之前；已全數立碑而刪除之檔不致拒跑 ─────────────────────────────────────────────

def test_01_tombstoned_must_and_path_resolved_before_collect(gate_repo):
    sel = _plan(gate_repo)
    assert "tests/test_new.py" in sel["groups"]["B"] and "tests/test_old.py" not in sel["groups"]["B"]
    assert {"from": "tests/test_old.py::test_o", "to": ["tests/test_new.py::test_n"], "evidence_level": "E1"} in \
        sel["tombstone_resolutions"]
    assert "tests/test_new.py::test_n" in sel["selected"]
    assert sel["must_check"] == {"must": ["tests/test_new.py::test_n"], "missing": []}


def test_mutation_no_tombstone_resolution_refuses(gate_repo, monkeypatch):
    """mutant：碑解析不做（等同移到 collect 之後）⇒ 已刪原檔被 collect ⇒ 拒跑（①紅）。"""
    monkeypatch.setattr(g, "resolve_tombstones", lambda repo, items, catalog: (list(items), []))
    with pytest.raises(g.GateError):
        _plan(gate_repo)


def test_11_deleted_fully_tombstoned_file_absent_from_impact(gate_repo):
    imp = _plan(gate_repo)["testreg_impact"]
    universe = {x["path"] for x in imp["selected"]} | {x["path"] for x in imp["excluded"]}
    assert "tests/test_old.py" not in universe
    assert universe == {"tests/test_keep.py", "tests/test_new.py"}


# ── ⑦ plan 收據三欄、確定性 ─────────────────────────────────────────────────────────────────────────

def test_07_plan_receipt_fields_deterministic(gate_repo):
    a, b = _plan(gate_repo), _plan(gate_repo)
    fields = schema()["gate_report"]["plan_receipt_fields"]
    for k in fields:
        assert k in a and json.dumps(a[k], sort_keys=True) == json.dumps(b[k], sort_keys=True), k
    assert g.validate_plan_receipt({k: a[k] for k in fields}, gate_repo["repo"].root) == []


# ── ⑤ must 核對 ─────────────────────────────────────────────────────────────────────────────────────

def test_05_must_removed_without_tombstone_refuses(gate_repo):
    rows = ROWS[:2] + ["affected_must phase=1 tests/test_keep.py::test_gone"]
    with pytest.raises(g.GateError):
        _plan(gate_repo, _manifest(rows))
    assert g.must_missing(["tests/test_keep.py::test_gone"], {"tests/test_keep.py": ["tests/test_keep.py::test_k"]}) == [
        "tests/test_keep.py::test_gone"]


def test_mutation_skip_must_check_passes(gate_repo, monkeypatch):
    monkeypatch.setattr(g, "must_missing", lambda must, collected: [])
    rows = ROWS[:2] + ["affected_must phase=1 tests/test_keep.py::test_gone"]
    _plan(gate_repo, _manifest(rows))  # 不拋 ⇒ ⑤ 之紅來自 must 核對


# ── ⑥c／⑨ plan 收據與 impact_universe 驗證 ──────────────────────────────────────────────────────────

def test_06c_empty_or_missing_impact_refuses(gate_repo, monkeypatch):
    root = gate_repo["repo"].root
    good = {"testreg_impact": {"selected": [{"path": "tests/test_new.py", "reasons": ["must"]}],
                               "excluded": [{"path": "tests/test_keep.py", "excluded_reason": "outside_changed_dependency"}]},
            "catalog_sha256": "a" * 64, "previously_failed": []}
    assert g.validate_plan_receipt(good, root) == []
    assert g.validate_plan_receipt(dict(good, testreg_impact={}), root) != []
    assert g.validate_plan_receipt(dict(good, testreg_impact={"excluded": []}), root) != []
    monkeypatch.setattr(testreg, "impact", lambda *a, **k: {})
    with pytest.raises(g.GateError):
        _plan(gate_repo)


def test_09_impact_universe_violations(gate_repo, monkeypatch):
    tree = ["tests/test_keep.py", "tests/test_new.py"]
    ok = {"selected": [{"path": "tests/test_new.py", "reasons": ["must"]}],
          "excluded": [{"path": "tests/test_keep.py", "excluded_reason": "outside_changed_dependency"}]}
    assert g.impact_universe_errors(ok, tree) == []
    missing = {"selected": ok["selected"], "excluded": []}
    both = {"selected": ok["selected"], "excluded": ok["excluded"] + [{"path": "tests/test_new.py",
                                                                         "excluded_reason": "tombstoned"}]}
    assert g.impact_universe_errors(missing, tree) != [] and g.impact_universe_errors(both, tree) != []
    monkeypatch.setattr(testreg, "impact", lambda *a, **k: missing)
    with pytest.raises(g.GateError):
        _plan(gate_repo)


def test_09_changed_paths_include_production(gate_repo):
    r = gate_repo["repo"]
    r.write("momentum/m.py", "def f():\n    return 2\n")
    paths = g.changed_paths(r.root, gate_repo["anchor"])
    assert "momentum/m.py" in paths and "tests/test_old.py" in paths and paths == sorted(set(paths))
    assert not any(p.startswith("handoffs/") or "/__pycache__/" in f"/{p}" for p in paths)


# ── ③⑧ inputs_digest ────────────────────────────────────────────────────────────────────────────────

def _digest(r: TmpRepo, anchor: str, out: Path, manifest=None, prev=()) -> str:
    return g.plan_inputs_digest(r.root, anchor, 1, [out], clean_env(), out=out, manifest=manifest or _manifest(),
                                previously_failed=list(prev))


@pytest.fixture
def digest_repo(tmp_path):
    r = make_repo(tmp_path, GATE_FILES)
    out = r.p("gate_out")
    out.mkdir()
    return r, r.head(), out


def test_03_out_dir_excluded_but_other_untracked_counted(digest_repo):
    r, anchor, out = digest_repo
    d1 = _digest(r, anchor, out)
    (out / "junit").mkdir()
    (out / "junit" / "x.xml").write_text("<testsuite><testcase classname='a' name='b' time='1'/></testsuite>",
                                         encoding="utf-8")
    assert _digest(r, anchor, out) == d1
    r.write("momentum/new.py", "X = 1\n")
    assert _digest(r, anchor, out) != d1


def test_03_out_is_repo_root_refuses(digest_repo):
    r, _, _ = digest_repo
    with pytest.raises(g.GateError):
        g.check_out_dir(r.root, r.root)
    g.check_out_dir(r.p("gate_out"), r.root)


def test_mutation_out_exclusion_empty_breaks_03(digest_repo, monkeypatch):
    r, anchor, out = digest_repo
    monkeypatch.setattr(g, "out_exclusion", lambda repo, out_dir: None)
    d1 = _digest(r, anchor, out)
    (out / "y.xml").write_text("<testsuite/>", encoding="utf-8")
    assert _digest(r, anchor, out) != d1


@pytest.mark.parametrize("change", ["testreg_py", "schema", "catalog", "previously_failed", "manifest_object"])
def test_08_digest_binds_testreg_inputs(digest_repo, change):
    r, anchor, out = digest_repo
    d1 = _digest(r, anchor, out)
    man, prev = _manifest(), []
    if change == "testreg_py":
        r.write("scripts/testreg.py", r.read("scripts/testreg.py") + "\n# x\n")
    elif change == "schema":
        r.write("tests/registry/testreg_schema.json", r.read("tests/registry/testreg_schema.json") + "\n")
    elif change == "catalog":
        r.put_entry(entry("tests/test_keep.py", disposition_ref=REF))
    elif change == "previously_failed":
        prev = ["tests/test_keep.py::test_k"]
    else:
        man = _manifest(ROWS + ["affected_must phase=1 tests/test_keep.py::test_k"])
    assert _digest(r, anchor, out, man, prev) != d1


# ── ④ ENV_PREFIXES 單一來源；b1 計畫重放 ────────────────────────────────────────────────────────────

def test_04_env_prefixes_from_schema():
    assert tuple(g.ENV_PREFIXES) == tuple(schema()["ledger"]["env_prefixes"])
    tree = ast.parse((REPO / "scripts/framepath_affected_gate.py").read_text(encoding="utf-8"))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "ENV_PREFIXES" for t in n.targets)]
    assert len(assigns) == 1 and not isinstance(assigns[0].value, (ast.Tuple, ast.List))


def test_04_replay_b1_plan_superset_of_must():
    plan = json.loads((REPO / "handoffs/run_receipts/framepath-b1-affected-plan.json").read_text(encoding="utf-8"))
    man = json.loads((REPO / "docs/manifests/FRAMEPATH.json").read_text(encoding="utf-8"))
    must = g._row_nodeids(man["batch_card"]["risk_mitigation"], "affected_must phase=1 ")
    assert must
    some_file = sorted(plan["collected"])[0]
    new = g.expanded_nodeids(plan["selected"], plan["collected"], [some_file])
    assert set(must) <= new and set(plan["collected"][some_file]) <= new and set(plan["selected"]) <= new


# ── 碑解析之遞迴、循環、E0 ──────────────────────────────────────────────────────────────────────────

def test_boundary_01_recursive_resolution_and_cycle(tmp_path):
    r = make_repo(tmp_path, {"tests/test_c.py": "def test_c():\n    assert True\n"})
    cat = {"entries": {}, "tombstones": [_tomb("tests/test_a.py::test_a", ["tests/test_b.py::test_b"]),
                                         _tomb("tests/test_b.py::test_b", ["tests/test_c.py::test_c"], "E2")]}
    resolved, rows = g.resolve_tombstones(r.root, ["tests/test_a.py::test_a"], cat)
    assert resolved == ["tests/test_c.py::test_c"]
    assert any(x["from"] == "tests/test_a.py::test_a" for x in rows)
    cyc = {"entries": {}, "tombstones": [_tomb("tests/test_a.py::test_a", ["tests/test_b.py::test_b"]),
                                         _tomb("tests/test_b.py::test_b", ["tests/test_a.py::test_a"])]}
    with pytest.raises(g.GateError):
        g.resolve_tombstones(r.root, ["tests/test_a.py::test_a"], cyc)


def test_e0_tombstone_removed_and_recorded(tmp_path):
    r = make_repo(tmp_path, {"tests/test_c.py": "def test_c():\n    assert True\n"})
    cat = {"entries": {}, "tombstones": [_tomb("tests/test_z.py::test_z", [], "E0")]}
    resolved, rows = g.resolve_tombstones(r.root, ["tests/test_z.py::test_z", "tests/test_c.py"], cat)
    assert resolved == ["tests/test_c.py"]
    assert rows == [{"from": "tests/test_z.py::test_z", "to": [], "evidence_level": "E0"}]


# ── ②⑥ 隔離失敗 ────────────────────────────────────────────────────────────────────────────────────

FAIL = {"exception_type": "AssertionError", "exception_head": "assert 1 == 2", "exception_origin": "tests/t.py:5",
        "fail_line": 5}


def _write_ledger(d: Path, sid: str, outcome: str, rec: Dict[str, Any], nodeid: str = "tests/t.py::test_x[1]",
                  argv: List[str] = ()) -> None:
    sess = {"kind": "session", "session_id": sid, "started": "2026-10-01T00:00:00Z", "head": "a" * 40,
            "diff_digest": "clean", "kline_sha256": "absent", "python": "py", "packages_digest": "b" * 64, "env": {},
            "argv_norm": "{}", "argv_raw": list(argv), "fingerprint": "c" * 64, "duration_class": "d" * 64}
    test = {"kind": "test", "session_id": sid, "nodeid": nodeid, "order": 0, "outcome": outcome, "duration_s": 0.1,
            "phase_failed": "call" if outcome == "failed" else "none", "exception_type": rec.get("exception_type"),
            "exception_head": rec.get("exception_head"), "exception_origin": rec.get("exception_origin"),
            "fail_line": rec.get("fail_line"), "fail_frames": [], "teardown_failed": False, "markers": []}
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.jsonl").write_text(json.dumps(sess) + "\n" + json.dumps(test) + "\n", encoding="utf-8")


@pytest.fixture
def qfx(tmp_path):
    d = tmp_path / "ledger"
    sp, sf = str(uuid.uuid4()), str(uuid.uuid4())
    _write_ledger(d, sp, "passed", {})
    _write_ledger(d, sf, "failed", FAIL)

    def catalog(expires=FUTURE):
        q = {"nodeid": "tests/t.py::test_x", "reason": "flaky", "expires": expires, "disposition_ref": REF,
             "evidence": [{"session_id": sp, "nodeid": "tests/t.py::test_x[1]"},
                          {"session_id": sf, "nodeid": "tests/t.py::test_x[1]"}]}
        return {"entries": {"tests/t.py": entry("tests/t.py", quarantine=[q])}, "tombstones": []}
    return {"dir": d, "catalog": catalog}


def _verdict_after(caused: List[str]) -> bool:
    return g.verdict({"missing": [], "unexpected": [], "caused": caused, "head_red": [], "passed": []}, [], [])


def test_boundary_02_quarantine_parametrized_nodeid_matched_at_function_level(qfx):
    """quarantine 之 nodeid 為函式層；caused 為參數化 nodeid ⇒ 以函式層比對而吸收；他函式之參數化 nodeid 不吸收。"""
    still, qf = g.split_quarantined(["tests/t.py::test_x[1]", "tests/t.py::test_y[1]"],
                                    {"tests/t.py::test_x[1]": FAIL, "tests/t.py::test_y[1]": FAIL}, qfx["catalog"](),
                                    qfx["dir"], TODAY)
    assert still == ["tests/t.py::test_y[1]"] and [x["nodeid"] for x in qf] == ["tests/t.py::test_x[1]"]


def test_02_valid_quarantine_absorbs_matching_caused(qfx):
    still, qf = g.split_quarantined(["tests/t.py::test_x[1]"], {"tests/t.py::test_x[1]": FAIL}, qfx["catalog"](),
                                    qfx["dir"], TODAY)
    assert still == [] and _verdict_after(still)
    assert qf == [{"nodeid": "tests/t.py::test_x[1]", "quarantine_expires": FUTURE, "disposition_ref": REF}]
    assert all(testreg.validate_shape(x, {"type": "types.quarantined_failure"}, schema()) == [] for x in qf)


def test_02_expired_quarantine_still_blocks(qfx):
    still, qf = g.split_quarantined(["tests/t.py::test_x[1]"], {"tests/t.py::test_x[1]": FAIL}, qfx["catalog"](PAST),
                                    qfx["dir"], TODAY)
    assert still == ["tests/t.py::test_x[1]"] and qf == [] and not _verdict_after(still)


def test_mutation_no_expiry_check_absorbs_expired(qfx, monkeypatch):
    monkeypatch.setattr(g, "quarantine_active", lambda q, today: True)
    still, _ = g.split_quarantined(["tests/t.py::test_x[1]"], {"tests/t.py::test_x[1]": FAIL}, qfx["catalog"](PAST),
                                   qfx["dir"], TODAY)
    assert still == []


@pytest.mark.parametrize("field,value", [("exception_type", "ValueError"), ("exception_head", "other message"),
                                         ("exception_origin", "tests/t.py:9"), ("fail_line", 9)])
def test_06_quarantine_mismatch_blocks(qfx, field, value):
    cur = dict(FAIL, **{field: value})
    still, qf = g.split_quarantined(["tests/t.py::test_x[1]"], {"tests/t.py::test_x[1]": cur}, qfx["catalog"](),
                                    qfx["dir"], TODAY)
    assert still == ["tests/t.py::test_x[1]"] and qf == []


def _ledger_names(d: Path) -> set:
    return {p.name for p in d.glob("*.jsonl")}


def test_04c_current_failures_only_from_new_session_matching_argv(qfx):
    """C4：當前四欄只取「本次呼叫前後新增、且 argv_raw 含該測試檔」之 session；舊 session 與他檔之新 session 不採。"""
    d = qfx["dir"]
    before = _ledger_names(d)
    moved = dict(FAIL, exception_origin="tests/t.py:9", fail_line=9)
    s_other, s_this = str(uuid.uuid4()), str(uuid.uuid4())
    _write_ledger(d, s_other, "failed", FAIL, argv=["tests/other.py"])
    _write_ledger(d, s_this, "failed", moved, argv=["-q", "tests/t.py"])
    cur = g.current_failures(d, before, "tests/t.py")
    assert set(cur) == {"tests/t.py::test_x[1]"}
    assert cur["tests/t.py::test_x[1]"]["exception_origin"] == "tests/t.py:9" and cur["tests/t.py::test_x[1]"]["fail_line"] == 9
    still, qf = g.split_quarantined(["tests/t.py::test_x[1]"], cur, qfx["catalog"](), d, TODAY)
    assert still == ["tests/t.py::test_x[1]"] and qf == []  # 新失敗位置不同 ⇒ 照擋（不得以前史四欄冒充）


def test_04c_no_matching_new_session_never_quarantined(qfx):
    d = qfx["dir"]
    before = _ledger_names(d)
    _write_ledger(d, str(uuid.uuid4()), "failed", FAIL, argv=["tests/other.py"])
    cur = g.current_failures(d, before, "tests/t.py")
    assert cur == {}
    still, qf = g.split_quarantined(["tests/t.py::test_x[1]"], cur, qfx["catalog"](), d, TODAY)
    assert still == ["tests/t.py::test_x[1]"] and qf == []


def _fake_run_file(d: Path, rec: Dict[str, Any], argv_file: str = "tests/t.py"):
    """模擬一次 pytest 呼叫：寫 junit 結果與（記錄器所寫之）ledger session（argv_raw 含該測試檔）。"""

    def run_file(test_file, xml_path, cwd, env, nodeids, extra):
        _write_ledger(d, str(uuid.uuid4()), "failed", rec, argv=["-q", argv_file])
        Path(xml_path).parent.mkdir(parents=True, exist_ok=True)
        Path(xml_path).write_text('<testsuite><testcase classname="tests.t" name="test_x[1]"><failure type="AssertionError" '
                                  'message="assert 1 == 2"/></testcase></testsuite>', encoding="utf-8")
        return 1, {"tests/t.py::test_x[1]": {"outcome": "failed", "type": "AssertionError", "message": "assert 1 == 2"}}

    return run_file


def _orchestrate(qfx, tmp_path, monkeypatch, rec: Dict[str, Any]):
    """經實際編排路徑：Runner.run（呼叫前後快照 ledger 檔名於 runner.ledger_snapshots）→ classify_quarantine。"""
    monkeypatch.setattr(g, "run_file", _fake_run_file(qfx["dir"], rec))
    runner = g.Runner(tmp_path / "out", None, 1, ledger_dir=qfx["dir"])
    runner.run("tests/t.py", tmp_path / "out" / "junit" / "t.xml", tmp_path, {}, None, (), "k1", ["tests/t.py::test_x[1]"])
    assert "tests/t.py" in runner.ledger_snapshots
    return g.classify_quarantine(["tests/t.py::test_x[1]"], runner, qfx["catalog"](), qfx["dir"], TODAY)


def test_04d_orchestration_absorbs_only_matching_new_failure(qfx, tmp_path, monkeypatch):
    still, qf = _orchestrate(qfx, tmp_path, monkeypatch, FAIL)
    assert still == [] and [x["nodeid"] for x in qf] == ["tests/t.py::test_x[1]"]


def test_04d_orchestration_moved_failure_blocks(qfx, tmp_path, monkeypatch):
    still, qf = _orchestrate(qfx, tmp_path, monkeypatch, dict(FAIL, exception_origin="tests/t.py:9", fail_line=9))
    assert still == ["tests/t.py::test_x[1]"] and qf == []


def test_mutation_orchestration_ignores_snapshot_absorbs_moved_failure(qfx, tmp_path, monkeypatch):
    """mutant：編排不用呼叫前快照（current_failures 改取前史）⇒ 位置已變之新失敗被吸收。"""
    def from_history(ledger_dir, before_names, test_file):
        out = {}
        for p in sorted(Path(ledger_dir).glob("*.jsonl")):
            if p.name in before_names:
                for line in p.read_text(encoding="utf-8").splitlines():
                    r = json.loads(line)
                    if r.get("kind") == "test" and r["outcome"] in ("failed", "error"):
                        out[r["nodeid"]] = r
        return out

    monkeypatch.setattr(g, "current_failures", from_history)
    still, _ = _orchestrate(qfx, tmp_path, monkeypatch, dict(FAIL, exception_origin="tests/t.py:9", fail_line=9))
    assert still == []


def _result(caused: List[str]) -> Dict[str, Any]:
    return {"missing": [], "unexpected": [], "caused": list(caused), "head_red": [], "passed": []}


def _run_once(qfx, tmp_path, monkeypatch, rec: Dict[str, Any]):
    monkeypatch.setattr(g, "run_file", _fake_run_file(qfx["dir"], rec))
    runner = g.Runner(tmp_path / "out", None, 1, ledger_dir=qfx["dir"])
    runner.run("tests/t.py", tmp_path / "out" / "junit" / "t.xml", tmp_path, {}, None, (), "k1", ["tests/t.py::test_x[1]"])
    return runner


def test_04f_quarantined_verdict_is_the_verdict_path(qfx, tmp_path, monkeypatch):
    """verdict 之唯一組合：`quarantined_verdict(result, a_failures, incomplete, unexecuted, runner, catalog, ledger_dir,
    today) -> (pass, quarantined_failures)`：相符之新失敗 ⇒ pass 且列報；位置已變 ⇒ 不 pass。"""
    runner = _run_once(qfx, tmp_path, monkeypatch, FAIL)
    ok, qf = g.quarantined_verdict(_result(["tests/t.py::test_x[1]"]), [], [], [], runner, qfx["catalog"](), qfx["dir"],
                                   TODAY)
    assert ok is True and [x["nodeid"] for x in qf] == ["tests/t.py::test_x[1]"]
    runner = _run_once(qfx, tmp_path / "b", monkeypatch, dict(FAIL, exception_origin="tests/t.py:9", fail_line=9))
    ok, qf = g.quarantined_verdict(_result(["tests/t.py::test_x[1]"]), [], [], [], runner, qfx["catalog"](), qfx["dir"],
                                   TODAY)
    assert ok is False and qf == []


def test_mutation_quarantined_verdict_without_classify_blocks(qfx, tmp_path, monkeypatch):
    """mutant：組合不經 classify_quarantine（一律不吸收）⇒ 相符之新失敗亦不 pass（即 04f 之吸收來自該縫）。"""
    runner = _run_once(qfx, tmp_path, monkeypatch, FAIL)
    monkeypatch.setattr(g, "classify_quarantine", lambda caused, *a, **k: (list(caused), []))
    ok, _ = g.quarantined_verdict(_result(["tests/t.py::test_x[1]"]), [], [], [], runner, qfx["catalog"](), qfx["dir"],
                                  TODAY)
    assert ok is False


@pytest.mark.parametrize("other", ["a_failures", "incomplete", "unexecuted", "missing", "unexpected"])
def test_04f_other_failure_inputs_never_absorbed(qfx, tmp_path, monkeypatch, other):
    """caused 全被隔離吸收時，其餘任一失敗輸入（A 組失敗、未完成檔、殘差未執行、缺、多出）非空 ⇒ 仍不 pass。"""
    runner = _run_once(qfx, tmp_path, monkeypatch, FAIL)
    result = _result(["tests/t.py::test_x[1]"])
    a_f, inc, unexe = [], [], []
    if other == "a_failures":
        a_f = ["tests/a.py::test_a"]
    elif other == "incomplete":
        inc = ["tests/b.py"]
    elif other == "unexecuted":
        unexe = ["momentum/x.py:f"]
    else:
        result[other] = ["tests/c.py::test_c"]
    ok, qf = g.quarantined_verdict(result, a_f, inc, unexe, runner, qfx["catalog"](), qfx["dir"], TODAY)
    assert ok is False and [x["nodeid"] for x in qf] == ["tests/t.py::test_x[1]"]


def test_04g_gate_main_uses_quarantined_verdict_only():
    """結構：閘 main 之 verdict 只經 quarantined_verdict（不直接呼叫 verdict／split_quarantined／current_failures），
    且其回傳值確為最終裁決：解構之第一名同時用於收據之 "pass" 與 main 之 return，第二名用於收據之
    "quarantined_failures"。"""
    tree = ast.parse((REPO / "scripts/framepath_affected_gate.py").read_text(encoding="utf-8"))
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    called = {c.func.id for c in ast.walk(main) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert "quarantined_verdict" in called
    assert not called & {"verdict", "split_quarantined", "current_failures"}
    asg = [n for n in ast.walk(main) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
           and isinstance(n.value.func, ast.Name) and n.value.func.id == "quarantined_verdict"]
    assert len(asg) == 1 and isinstance(asg[0].targets[0], ast.Tuple)
    ok_name, qf_name = (e.id for e in asg[0].targets[0].elts)
    rets = [n for n in ast.walk(main) if isinstance(n, ast.Return) and n.value is not None]
    assert any(isinstance(x, ast.Name) and x.id == ok_name for r in rets for x in ast.walk(r.value))
    dicts = [d for d in ast.walk(main) if isinstance(d, ast.Dict)]
    pairs = {(k.value, v.id) for d in dicts for k, v in zip(d.keys, d.values)
             if isinstance(k, ast.Constant) and isinstance(v, ast.Name)}
    assert ("pass", ok_name) in pairs and ("quarantined_failures", qf_name) in pairs


def test_04h_gate_main_verdict_statement_form():
    """main 之裁決敘述形狀固定（自然接線錯誤即紅；刻意以別名／動態呼叫繞過屬 §N R6）：
    ① `quarantined_verdict` 之前五個引數依序為 `result, a_failures, incomplete, unexecuted, runner` 之名稱；
    ② `result` 為 `classify(...)` 之回傳、`a_failures`／`incomplete` 於 main 內有累加（`+=`／append／extend）、
       `unexecuted` 由非字面運算式指定（不得只綁空串列）；③ main 之結束碼敘述為 `return 0 if <裁決名> else 1`。"""
    tree = ast.parse((REPO / "scripts/framepath_affected_gate.py").read_text(encoding="utf-8"))
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    call = next(n.value for n in ast.walk(main) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Name) and n.value.func.id == "quarantined_verdict")
    names = [a.id if isinstance(a, ast.Name) else None for a in call.args[:5]]
    assert names == ["result", "a_failures", "incomplete", "unexecuted", "runner"], names
    binds: Dict[str, List[ast.AST]] = {}
    for n in ast.walk(main):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    binds.setdefault(t.id, []).append(n.value)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            binds.setdefault(n.target.id, []).append(n)
    assert any(isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "classify"
               for v in binds.get("result", []))
    grows = {n.func.value.id for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in ("append", "extend") and isinstance(n.func.value, ast.Name)}
    for nm in ("a_failures", "incomplete"):
        assert nm in grows or any(isinstance(v, ast.AugAssign) for v in binds.get(nm, [])), nm
    assert binds.get("unexecuted") and all(not isinstance(v, (ast.List, ast.Tuple, ast.Constant))
                                           for v in binds["unexecuted"])
    ok_name = next(n.targets[0].elts[0].id for n in ast.walk(main) if isinstance(n, ast.Assign)
                   and isinstance(n.value, ast.Call) and getattr(n.value.func, "id", "") == "quarantined_verdict")
    rets = [n.value for n in ast.walk(main) if isinstance(n, ast.Return) and isinstance(n.value, ast.IfExp)]
    assert any(isinstance(r.test, ast.Name) and r.test.id == ok_name and getattr(r.body, "value", None) == 0
               and getattr(r.orelse, "value", None) == 1 for r in rets)
    qv = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "quarantined_verdict")
    inner = {c.func.id for c in ast.walk(qv) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert {"classify_quarantine", "verdict"} <= inner


def test_mutation_current_failures_reusing_old_sessions_absorbs_new_failure(qfx, monkeypatch):
    """mutant：當前四欄改取前史（不看呼叫前後新增與 argv_raw）⇒ 位置已變之新失敗被吸收（即 04c 之紅來自 session 選擇）。"""
    d = qfx["dir"]
    before = _ledger_names(d)
    _write_ledger(d, str(uuid.uuid4()), "failed", dict(FAIL, exception_origin="tests/t.py:9", fail_line=9),
                  argv=["tests/t.py"])

    def from_history(ledger_dir, before_names, test_file):
        out = {}
        for p in sorted(Path(ledger_dir).glob("*.jsonl")):
            if p.name in before_names:
                for line in p.read_text(encoding="utf-8").splitlines():
                    r = json.loads(line)
                    if r.get("kind") == "test" and r["outcome"] in ("failed", "error"):
                        out[r["nodeid"]] = r
        return out

    monkeypatch.setattr(g, "current_failures", from_history)
    cur = g.current_failures(d, before, "tests/t.py")
    still, _ = g.split_quarantined(["tests/t.py::test_x[1]"], cur, qfx["catalog"](), d, TODAY)
    assert still == []


def test_06b_evidence_other_nodeid_v12_red(tmp_path):
    r = make_repo(tmp_path, {"tests/test_t.py": "def test_x():\n    assert True\n"})
    d = r.p(schema()["ledger"]["dir"])
    sp, sf = str(uuid.uuid4()), str(uuid.uuid4())
    _write_ledger(d, sp, "passed", {}, "tests/test_t.py::test_other")
    _write_ledger(d, sf, "failed", FAIL, "tests/test_t.py::test_other")
    q = {"nodeid": "tests/test_t.py::test_x", "reason": "flaky", "expires": FUTURE, "disposition_ref": REF,
         "evidence": [{"session_id": sp, "nodeid": "tests/test_t.py::test_other"},
                      {"session_id": sf, "nodeid": "tests/test_t.py::test_other"}]}
    r.put_entry(entry("tests/test_t.py", quarantine=[q]))
    proc = r.run("validate")
    assert proc.returncode != 0 and any(l.startswith("V12 ") for l in proc.stderr.splitlines()), proc.stderr


# ── ⑩ gate_cmd 判定、同碑多 manifest ────────────────────────────────────────────────────────────────

GATE = "venv/bin/python scripts/framepath_affected_gate.py"
GATE_CMDS = {
    "bare": (GATE, True),
    "pythonpath_env": ("PYTHONPATH=. " + GATE, True),
    "allowed_options": (GATE + " --out /tmp/x --max-seconds 3600 --timings a --timings b", True),
    "disallowed_env": ("FFACT_USE_CGSA=0 " + GATE, False),
    "help": (GATE + " --help", False),
    "plan": (GATE + " --plan", False),
    "out_missing_value": (GATE + " --out", False),
    "max_seconds_twice": (GATE + " --max-seconds 1 --max-seconds 2", False),
    "and_and": ("python scripts/framepath_affected_gate.py && pytest tests/x.py", False),
    "command_substitution": ("python scripts/framepath_affected_gate.py $(pytest tests/x.py)", False),
}


@pytest.mark.parametrize("case", sorted(GATE_CMDS))
def test_10_gate_cmd_tombstone_aware(case):
    cmd, ok = GATE_CMDS[case]
    assert testreg.manifest_tombstone_aware({"batch_card": {"gate_cmd": cmd}}, schema()) is ok


def test_10_same_tombstone_in_safe_and_unsafe_manifest_v14_red(tmp_path):
    r = make_repo(tmp_path, {"tests/test_t.py": "def test_x():\n    assert True\n\n\ndef test_y():\n    assert True\n",
                             "scripts/fact_keys.json": json.dumps(fact_keys_rows([
                                 ["001", "HP-OPEN", "進行中", "docs/OPEN_SPEC.md", "—"]]))})
    row = "affected_tests phase=1 tests/test_t.py"
    r.write_json("docs/manifests/SAFE.json", {"spec_path": "docs/OPEN_SPEC.md", "batch_card": {
        "gate_cmd": "PYTHONPATH=. " + GATE, "risk_mitigation": [row]}})
    r.write_json("docs/manifests/UNSAFE.json", {"spec_path": "docs/OPEN_SPEC.md", "batch_card": {
        "gate_cmd": "venv/bin/python -m pytest tests/test_t.py", "risk_mitigation": [row]}})
    r.commit("manifests")
    r.write("tests/test_t.py", "def test_x():\n    assert True\n")
    r.add_tombstone(_tomb("tests/test_t.py::test_y", [], "E0"))
    proc = r.run("validate")
    assert any(l.startswith("V14 ") and "UNSAFE" in l for l in proc.stderr.splitlines()), proc.stderr
