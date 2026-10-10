"""TESTREG Task 2.1 驗收：`scripts/testreg.py review` 逐檔逐訊號（docs/TESTREG_SPEC.md；schema `enums.review_signal`、
`derived.duration_regression_rule`）。每訊號一正例一反例＋反轉 mutation；summary／ledger 不存在之字面 unknown；
訊號不寫回 catalog。實作前（空殼）為紅。"""
from __future__ import annotations

import hashlib
import importlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.registry.testreg_helpers import CATALOG_REL, TmpRepo, entry, enum, fact_keys_rows, make_repo, schema

testreg = importlib.import_module("scripts.testreg")

CALC = "def add(a, b):\n    return a + b\n"
FILES = {"momentum/__init__.py": "", "momentum/calc.py": CALC,
         "tests/test_live.py": "from momentum.calc import add\n\n\ndef test_live():\n    assert add(1, 1) == 2\n",
         "tests/test_dead.py": "from momentum.calc import gone\n\n\ndef test_dead():\n    assert gone() == 1\n"}
LIVE, DEAD = "tests/test_live.py", "tests/test_dead.py"
REF = "handoffs/reconcile/20261010-testreg-x-review-r16/synth.md"
SIGNALS = enum("review_signal")


def _repo(tmp_path: Path) -> TmpRepo:
    return make_repo(tmp_path, FILES)


def _review(r: TmpRepo) -> Dict[str, Dict[str, Any]]:
    proc = r.run("review")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _rec(started: str, *, fp: str = "a" * 64, dc: str = "b" * 64, outcome: str = "passed",
         dur: float = 10.0) -> Dict[str, Any]:
    return {"session_id": str(uuid.uuid4()), "started": started, "fingerprint": fp, "duration_class": dc,
            "outcome": outcome, "duration_s": dur, "exception_type": None, "exception_head": None}


def _write_summary(r: TmpRepo, nodes: Dict[str, List[Dict[str, Any]]]) -> None:
    s = schema()
    r.write_json(s["summary"]["path"], {"schema_version": s["version"], "k": s["summary"]["k"], "nodes": nodes})


def _durations(prior: List[float], latest: float) -> List[Dict[str, Any]]:
    recs = [_rec(f"2026-10-0{i + 1}T00:00:00Z", dur=d) for i, d in enumerate(prior)]
    return recs + [_rec("2026-10-09T00:00:00Z", dur=latest)]


def _ledger(r: TmpRepo, sid: str, started: str, records: List[Dict[str, Any]]) -> None:
    sess = {"kind": "session", "session_id": sid, "started": started, "head": "a" * 40, "diff_digest": "clean",
            "kline_sha256": "absent", "python": "py", "packages_digest": "c" * 64, "env": {}, "argv_norm": "{}",
            "argv_raw": [], "fingerprint": "d" * 64, "duration_class": "e" * 64}
    lines = [sess] + [dict(x, session_id=sid) for x in records]
    r.write(f"{schema()['ledger']['dir']}/{sid}.jsonl", "\n".join(json.dumps(x) for x in lines) + "\n")


def _test_rec(nodeid: str) -> Dict[str, Any]:
    return {"kind": "test", "nodeid": nodeid, "order": 0, "outcome": "passed", "duration_s": 0.1, "phase_failed": "none",
            "exception_type": None, "exception_head": None, "exception_origin": None, "fail_line": None,
            "fail_frames": [], "teardown_failed": False, "markers": []}


def _coll_rec(path: str) -> Dict[str, Any]:
    return {"kind": "collect", "path": path, "exception_type": "ModuleNotFoundError", "exception_head": "No module"}


def _allowed_red(r: TmpRepo, owner: str) -> None:
    r.write_json("tests/_golden/prered/allowed_red.json", [{"node": f"{LIVE}::test_live", "owner_ticket": owner,
                                                            "reason": "r", "state": "red", "trigger": "t"}])


def _quarantine(r: TmpRepo, expires: str) -> None:
    sid = "12345678-1234-4123-8123-123456789abc"
    r.put_entry(entry(LIVE, quarantine=[{"nodeid": f"{LIVE}::test_live", "reason": "r", "expires": expires,
                                         "disposition_ref": REF,
                                         "evidence": [{"session_id": sid, "nodeid": f"{LIVE}::test_live"}] * 2}]))


# 每訊號：(正例構造, 反例構造)；正例使 LIVE（或 DEAD）之該訊號為 True，反例為 False
def _p_gone(r):
    return DEAD


def _n_gone(r):
    return LIVE


def _p_dur(r):
    _write_summary(r, {f"{LIVE}::test_live": _durations([10, 10, 10, 10, 10], 31.0)})
    return LIVE


def _n_dur(r):
    _write_summary(r, {f"{LIVE}::test_live": _durations([10, 10, 10, 10, 10], 29.0)})
    return LIVE


def _p_flip(r):
    _write_summary(r, {f"{LIVE}::test_live": [_rec("2026-10-01T00:00:00Z"),
                                              _rec("2026-10-02T00:00:00Z", outcome="failed")]})
    return LIVE


def _n_flip(r):
    _write_summary(r, {f"{LIVE}::test_live": [_rec("2026-10-01T00:00:00Z"),
                                              _rec("2026-10-02T00:00:00Z", outcome="failed", fp="f" * 64)]})
    return LIVE


def _p_coll(r):
    _ledger(r, str(uuid.uuid4()), "2026-10-01T00:00:00Z", [_test_rec(f"{LIVE}::test_live")])
    _ledger(r, str(uuid.uuid4()), "2026-10-02T00:00:00Z", [_coll_rec(LIVE)])
    return LIVE


def _n_coll(r):
    _ledger(r, str(uuid.uuid4()), "2026-10-01T00:00:00Z", [_coll_rec(LIVE)])
    _ledger(r, str(uuid.uuid4()), "2026-10-02T00:00:00Z", [_test_rec(f"{LIVE}::test_live")])
    return LIVE


def _p_owner_hp(r):
    _allowed_red(r, "FOO")
    r.write_json("scripts/fact_keys.json", fact_keys_rows([["001", "HP-FOO", "已完成", "docs/FOO_SPEC.md", "—"]]))
    return LIVE


def _n_owner(r):
    _allowed_red(r, "FOO")
    r.write_json("scripts/fact_keys.json", fact_keys_rows([["001", "HP-FOO", "進行中", "docs/FOO_SPEC.md", "—"]]))
    return LIVE


def _p_q(r):
    _quarantine(r, "2000-01-01")
    return LIVE


def _n_q(r):
    _quarantine(r, "2999-12-31")
    return LIVE


CASES = {
    "prod_symbol_gone": (_p_gone, _n_gone),
    "duration_regression": (_p_dur, _n_dur),
    "outcome_flip_same_fingerprint": (_p_flip, _n_flip),
    "collect_error": (_p_coll, _n_coll),
    "allowed_red_owner_closed": (_p_owner_hp, _n_owner),
    "quarantine_expired": (_p_q, _n_q),
}


def test_cases_cover_enum():
    assert sorted(CASES) == sorted(SIGNALS)


@pytest.mark.parametrize("signal", sorted(CASES))
def test_signal_positive(tmp_path, signal):
    r = _repo(tmp_path)
    path = CASES[signal][0](r)
    assert _review(r)[path][signal] is True


@pytest.mark.parametrize("signal", sorted(CASES))
def test_signal_negative(tmp_path, signal):
    r = _repo(tmp_path)
    path = CASES[signal][1](r)
    assert _review(r)[path][signal] is False


@pytest.mark.parametrize("signal", sorted(CASES))
def test_mutation_signal_inverted_breaks_positive(tmp_path, signal, monkeypatch):
    r = _repo(tmp_path)
    path = CASES[signal][0](r)
    assert testreg.review(r.root)[path][signal] is True
    orig = getattr(testreg, f"signal_{signal}")
    monkeypatch.setattr(testreg, f"signal_{signal}", lambda ctx, p: not orig(ctx, p))
    assert testreg.review(r.root)[path][signal] is False


def test_duration_regression_below_min_seconds_false(tmp_path):
    """中位 1 秒、本筆 9 秒（9 倍）但未達 min_seconds ⇒ False。"""
    r = _repo(tmp_path)
    _write_summary(r, {f"{LIVE}::test_live": _durations([1, 1, 1, 1, 1], 9.0)})
    assert _review(r)[LIVE]["duration_regression"] is False


def test_duration_regression_other_duration_class_not_compared(tmp_path):
    r = _repo(tmp_path)
    recs = _durations([10, 10, 10, 10, 10], 31.0)
    recs[-1]["duration_class"] = "9" * 64
    _write_summary(r, {f"{LIVE}::test_live": recs})
    assert _review(r)[LIVE]["duration_regression"] is False


def test_allowed_red_owner_via_roadmap_and_unknown(tmp_path):
    """查表規則（SPEC v17）：HP-<owner> 或 RM-<owner> 任一列狀態＝已完成 ⇒ True；兩區塊皆無對應列 ⇒ "unknown"。"""
    r = _repo(tmp_path)
    _allowed_red(r, "BAR")
    r.write_json("scripts/fact_keys.json", fact_keys_rows([["001", "RM-BAR", "線", "已完成", "docs/BAR_SPEC.md", "—"]]))
    assert _review(r)[LIVE]["allowed_red_owner_closed"] is True
    r.write_json("scripts/fact_keys.json", fact_keys_rows([]))
    assert _review(r)[LIVE]["allowed_red_owner_closed"] == "unknown"


def test_file_without_allowed_red_rows_false(tmp_path):
    r = _repo(tmp_path)
    _allowed_red(r, "FOO")
    assert _review(r)[DEAD]["allowed_red_owner_closed"] is False


def test_boundary_01_multiple_signals_all_listed(tmp_path):
    r = _repo(tmp_path)
    _p_q(r)
    r.write(LIVE, "from momentum.calc import gone\n\n\ndef test_live():\n    assert gone() == 2\n")
    out = _review(r)[LIVE]
    assert out["quarantine_expired"] is True and out["prod_symbol_gone"] is True
    assert set(out) == set(SIGNALS)


def test_boundary_02_no_ledger_only_ast_signals(tmp_path):
    r = _repo(tmp_path)
    assert not r.p(".testreg").exists()
    out = _review(r)
    for path in (LIVE, DEAD):
        for s in ("duration_regression", "outcome_flip_same_fingerprint", "collect_error"):
            assert out[path][s] == "unknown", (path, s)
    assert out[DEAD]["prod_symbol_gone"] is True and out[LIVE]["prod_symbol_gone"] is False


def test_review_does_not_write_catalog(tmp_path):
    r = _repo(tmp_path)
    before = hashlib.sha256(r.p(CATALOG_REL).read_bytes()).hexdigest()
    _p_dur(r)
    _review(r)
    assert hashlib.sha256(r.p(CATALOG_REL).read_bytes()).hexdigest() == before
