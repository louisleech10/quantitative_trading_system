"""TESTREG Task 1.3 驗收：記錄器 `tests/fixtures/testreg_recorder_plugin.py`（docs/TESTREG_SPEC.md；契約 schema `ledger`／`summary`）。

全部於暫存 git 倉以真實 pytest 子行程執行（`-p testreg_recorder_plugin`）；注入與 mutation 一律寫在暫存倉之根層
conftest.py（於 sessionstart 前載入，置換記錄器之具名縫），生產碼不含任何測試開關。§G 不變性基準之比對讀
`handoffs/run_receipts/testreg-recorder-{baseline,verify}.json`（由 `handoffs/run_receipts/testreg_probes/recorder_invariance.py`
於第 1 批產出）。實作前（記錄器為空殼）全部為紅。
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pytest

from tests.registry.testreg_helpers import (
    PLUGIN_DIR, PLUGIN_MOD, PY, REPO, TmpRepo, clean_env, lines_with, make_repo, recorded_pytest, schema, session_of,
    test_records,
)

OUTCOMES = '''import pytest


@pytest.fixture
def broken_setup():
    raise RuntimeError("setup boom")


@pytest.fixture
def broken_teardown():
    yield
    raise RuntimeError("teardown boom")


def test_pass():
    assert 1 == 1


def test_fail():
    x = 1
    assert x == 2


def test_skip():
    pytest.skip("s")


@pytest.mark.xfail(reason="x")
def test_xfail():
    assert 1 == 2


@pytest.mark.xfail(reason="x")
def test_xpass():
    assert 1 == 1


@pytest.mark.xfail(reason="x", strict=True)
def test_xpass_strict():
    assert 1 == 1


def test_setup_error(broken_setup):
    assert True


def test_teardown_fail_call_pass(broken_teardown):
    assert True


def test_call_and_teardown_fail(broken_teardown):
    assert 1 == 2


def test_call_skip_teardown_fail(broken_teardown):
    pytest.skip("s")


@pytest.mark.xfail(reason="x")
def test_call_xfail_teardown_fail(broken_teardown):
    assert 1 == 2
'''
OF = "tests/test_outcomes.py"
EXPECT = {  # nodeid 尾 → (outcome, phase_failed, teardown_failed)，依 schema ledger.outcome_aggregation
    "test_pass": ("passed", "none", False),
    "test_fail": ("failed", "call", False),
    "test_skip": ("skipped", "none", False),
    "test_xfail": ("xfailed", "none", False),
    "test_xpass": ("xpassed", "none", False),
    "test_xpass_strict": ("failed", "call", False),
    "test_setup_error": ("error", "setup", False),
    "test_teardown_fail_call_pass": ("error", "teardown", True),
    "test_call_and_teardown_fail": ("failed", "call", True),
    "test_call_skip_teardown_fail": ("error", "teardown", True),
    # pytest 對帶 xfail 標記之測試，teardown 例外亦由 skipping 外掛改報為 skipped＋wasxfail（非 failed）⇒ 依彙整規則為 xfailed
    "test_call_xfail_teardown_fail": ("xfailed", "none", False),
}
SIMPLE = {"tests/test_a.py": "def test_a1():\n    assert True\n\n\ndef test_a2():\n    assert 1 == 1\n",
          "tests/test_b.py": "def test_b1():\n    assert True\n"}
KLINE = "data_cache/feature_klines/kline_cache.h5"


def _proj(tmp_path: Path, files: Mapping[str, str] = None, conftest: Optional[str] = None,
          name: str = "proj") -> TmpRepo:
    r = make_repo(tmp_path, dict(files or SIMPLE), catalog=False, name=name)
    if conftest is not None:
        r.write("conftest.py", conftest)
        r.commit("conftest")
    return r


def _conftest(body: str) -> str:
    return f"import {PLUGIN_MOD} as rec\n\n{body}\n"


class Inject:
    """子行程內之置換：`setattr(name, expr)` 產生暫存倉根層 conftest 之 `setattr(rec, name, <expr>)`（於 sessionstart 前
    載入，置換記錄器具名縫）；`prelude` 放置換所需之輔助定義。"""

    def __init__(self) -> None:
        self.lines: List[str] = []

    def prelude(self, code: str) -> "Inject":
        self.lines.append(code)
        return self

    def setattr(self, name: str, expr: str) -> "Inject":
        self.lines.append(f"setattr(rec, {name!r}, {expr})")
        return self

    def conftest(self) -> str:
        return _conftest("\n".join(self.lines))


def _only(ids: List[str]) -> str:
    assert len(ids) == 1, ids
    return ids[0]


def _summary(r: TmpRepo) -> Dict[str, Any]:
    return json.loads(r.read(schema()["summary"]["path"]))


# ── ① outcome 彙整與失敗欄位 ────────────────────────────────────────────────────────────────────────

def test_outcome_aggregation_each_case(tmp_path):
    r = _proj(tmp_path, {OF: OUTCOMES})
    proc, ids = recorded_pytest(r, OF)
    recs = test_records(r, _only(ids))
    got = {n.split("::")[-1]: (v["outcome"], v["phase_failed"], v["teardown_failed"]) for n, v in recs.items()}
    assert got == EXPECT, proc.stdout


def test_failure_fields_exception_origin_fail_line(tmp_path):
    r = _proj(tmp_path, {OF: OUTCOMES})
    _, ids = recorded_pytest(r, OF)
    rec = test_records(r, _only(ids))[f"{OF}::test_fail"]
    line = lines_with(r, OF, "assert x == 2")[0]
    assert rec["exception_type"] == "AssertionError"
    assert rec["fail_line"] == line
    assert rec["exception_origin"] == f"{OF}:{line}"
    assert f"{OF}:{line}" in rec["fail_frames"]
    assert rec["exception_head"] and len(rec["exception_head"]) <= 300
    ok = test_records(r, ids[0])[f"{OF}::test_pass"]
    assert ok["exception_type"] is None and ok["fail_line"] is None and ok["fail_frames"] == []


def test_order_and_markers(tmp_path):
    r = _proj(tmp_path, {OF: OUTCOMES})
    _, ids = recorded_pytest(r, OF)
    recs = test_records(r, _only(ids))
    orders = sorted(v["order"] for v in recs.values())
    assert orders == list(range(orders[0], orders[0] + len(recs)))
    assert "xfail" in recs[f"{OF}::test_xfail"]["markers"]


def test_session_record_fields(tmp_path):
    r = _proj(tmp_path)
    _, ids = recorded_pytest(r, "tests/test_a.py")
    s = session_of(r, _only(ids))
    assert set(s) == set(schema()["types"]["session_record"]["fields"])
    assert s["head"] == r.head() and s["diff_digest"] == "clean" and s["kline_sha256"] == "absent"
    assert s["session_id"] == ids[0] and uuid.UUID(ids[0]).version == 4


# ── summary 重建條件（①／④；Task 1.1 所列 schema_version 舊檔與未知鍵同法）─────────────────────────────────

def _seed_ledger(r: TmpRepo, n: int) -> List[str]:
    """以一次真實 session 之 jsonl 為樣本，合成 n 份不同 session_id 與遞增 started 之 ledger 檔（形狀合法）。"""
    _, ids = recorded_pytest(r, "tests/test_a.py")
    src = r.ledger(_only(ids))
    made = []
    for i in range(n):
        sid = str(uuid.uuid4())
        started = f"2026-01-01T00:00:{i:02d}Z"
        lines = []
        for rec in src:
            rec = dict(rec, session_id=sid)
            if rec["kind"] == "session":
                rec["started"] = started
            lines.append(json.dumps(rec, ensure_ascii=False))
        r.write(f".testreg/ledger/{sid}.jsonl", "\n".join(lines) + "\n")
        made.append(sid)
    return made


def _ledger_count(r: TmpRepo, nodeid: str) -> int:
    return sum(1 for sid in r.ledger_ids() for rec in r.ledger(sid) if rec.get("nodeid") == nodeid)


GHOST = "tests/test_ghost.py::test_x"


def _bogus_summary(kind: str) -> Dict[str, Any]:
    s = schema()
    rec = {"session_id": str(uuid.uuid4()), "started": "2026-01-01T00:00:00Z", "fingerprint": "a" * 64,
           "duration_class": "b" * 64, "outcome": "passed", "duration_s": 1.0, "exception_type": None,
           "exception_head": None}
    out = {"schema_version": s["version"], "k": s["summary"]["k"], "nodes": {GHOST: [rec]}}
    if kind == "over_k":
        out["nodes"][GHOST] = [rec] * (s["summary"]["k"] + 1)
    elif kind == "started_not_iso":
        out["nodes"][GHOST] = [dict(rec, started="2026-01-01 00:00")]
    elif kind == "old_schema_version":
        out["schema_version"] = s["version"] - 1
    elif kind == "unknown_key":
        out["nodes"][GHOST] = [dict(rec, extra=1)]
    return out


@pytest.mark.parametrize("kind", ["garbage", "over_k", "started_not_iso", "old_schema_version", "unknown_key"])
def test_summary_rebuilt_from_ledger(tmp_path, kind):
    """毀損／超過 k 筆／started 非 ISO-UTC／schema_version 不符／未知鍵 ⇒ 視同不存在，由 ledger 全量重建：
    假紀錄（GHOST）消失、逐 nodeid 筆數 == min(k, ledger 筆數)、保留者為 started 最近之 k 筆。"""
    r = _proj(tmp_path)
    k = schema()["summary"]["k"]
    _seed_ledger(r, k + 5)
    path = r.p(schema()["summary"]["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json" if kind == "garbage" else json.dumps(_bogus_summary(kind)), encoding="utf-8")
    recorded_pytest(r, "tests/test_a.py")
    s = _summary(r)
    assert GHOST not in s["nodes"]
    nid = "tests/test_a.py::test_a1"
    assert len(s["nodes"][nid]) == min(k, _ledger_count(r, nid)) == k
    kept = sorted(x["started"] for x in s["nodes"][nid])
    all_started = sorted(session_of(r, sid)["started"] for sid in r.ledger_ids())
    assert kept == all_started[-k:]


def test_summary_incremental_merge_keeps_valid_existing(tmp_path):
    r = _proj(tmp_path)
    recorded_pytest(r, "tests/test_a.py")
    before = _summary(r)
    recorded_pytest(r, "tests/test_b.py")
    after = _summary(r)
    assert set(before["nodes"]) <= set(after["nodes"])
    assert "tests/test_b.py::test_b1" in after["nodes"]


# ── ② 巢狀 ───────────────────────────────────────────────────────────────────────────────────────────

NESTED = f'''import os
import subprocess
import sys


def test_spawn():
    proc = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "-p", "{PLUGIN_MOD}",
                           "tests/test_inner.py"], env=dict(os.environ), cwd=os.getcwd())
    assert proc.returncode == 0
'''
INNER = "def test_inner():\n    assert True\n"


def _nested_proj(tmp_path, conftest=None):
    return _proj(tmp_path, {"tests/test_nested.py": NESTED, "tests/test_inner.py": INNER}, conftest)


def test_nested_session_writes_nothing(tmp_path):
    r = _nested_proj(tmp_path)
    proc, ids = recorded_pytest(r, "tests/test_nested.py")
    assert proc.returncode == 0, proc.stdout
    assert len(ids) == 1 and len(r.ledger_ids()) == 1


def test_mutation_nested_check_removed_writes_inner(tmp_path):
    r = _nested_proj(tmp_path, Inject().setattr("is_nested", "lambda environ=None: False").conftest())
    proc, ids = recorded_pytest(r, "tests/test_nested.py")
    assert proc.returncode == 0, proc.stdout
    assert len(ids) == 2


# ── ③ 記錄器例外不影響被測 session ────────────────────────────────────────────────────────────────────

FAILING = {"tests/test_mix.py": "def test_ok():\n    assert True\n\n\ndef test_bad():\n    assert False\n"}
RAISE_WRITE = "def _boom(*a, **k):\n    raise OSError('disk full')\n\n\nrec.write_ledger = _boom"


def test_recorder_exception_does_not_change_rc(tmp_path):
    base = _proj(tmp_path, FAILING, name="base")
    ref, _ = recorded_pytest(base, "tests/test_mix.py", plugin=False)
    r = _proj(tmp_path, FAILING, _conftest(RAISE_WRITE), name="boom")
    proc, ids = recorded_pytest(r, "tests/test_mix.py")
    assert proc.returncode == ref.returncode == 1
    notes = [l for l in proc.stderr.splitlines() if l.startswith("testreg-recorder:")]
    assert len(notes) == 1, proc.stderr
    assert ids == []


def test_mutation_recorder_raises_changes_rc(tmp_path):
    base = _proj(tmp_path, FAILING, name="base")
    ref, _ = recorded_pytest(base, "tests/test_mix.py", plugin=False)
    inj = Inject().prelude(RAISE_WRITE).setattr("safe", "lambda fn, *a, **k: fn(*a, **k)")
    r = _proj(tmp_path, FAILING, inj.conftest(), name="mut")
    proc, _ = recorded_pytest(r, "tests/test_mix.py")
    notes = [l for l in proc.stderr.splitlines() if l.startswith("testreg-recorder:")]
    # ③ 之通過條件＝rc 同未裝記錄器 且 恰一列單行告知；mutant 下（例外上拋）此條件必不成立
    assert not (proc.returncode == ref.returncode and len(notes) == 1), proc.stderr


# ── ⑤ fingerprint／duration_class ────────────────────────────────────────────────────────────────────

def _fp(r: TmpRepo, *args: str, env: Mapping[str, str] = None) -> Dict[str, Any]:
    _, ids = recorded_pytest(r, *args, env_extra=env)
    return session_of(r, _only(ids))


def test_fingerprint_same_params_equal(tmp_path):
    r = _proj(tmp_path)
    assert _fp(r, "tests/test_a.py")["fingerprint"] == _fp(r, "tests/test_a.py")["fingerprint"]


VARIANTS_DIFFER = {
    "plugin_flag": (("-p", "no:doctest", "tests/test_a.py", "tests/test_b.py"), None),
    "keyword": (("-k", "a1", "tests/test_a.py", "tests/test_b.py"), None),
    "positional_order": (("tests/test_b.py", "tests/test_a.py"), None),
    "pytest_addopts": (("tests/test_a.py", "tests/test_b.py"), {"PYTEST_ADDOPTS": "-x"}),
    "numba_disable_jit": (("tests/test_a.py", "tests/test_b.py"), {"NUMBA_DISABLE_JIT": "1"}),
    "openblas_threads": (("tests/test_a.py", "tests/test_b.py"), {"OPENBLAS_NUM_THREADS": "1"}),
}
VARIANTS_EQUAL = {
    "extra_quiet": ("-q", "tests/test_a.py", "tests/test_b.py"),
    "tb_space_form": ("--tb", "short", "tests/test_a.py", "tests/test_b.py"),
    "reportchars_space_form": ("-r", "A", "tests/test_a.py", "tests/test_b.py"),
}
EQUAL_BASE = {"extra_quiet": ("tests/test_a.py", "tests/test_b.py"),
              "tb_space_form": ("--tb=short", "tests/test_a.py", "tests/test_b.py"),
              "reportchars_space_form": ("-rA", "tests/test_a.py", "tests/test_b.py")}


@pytest.mark.parametrize("case", sorted(VARIANTS_DIFFER))
def test_fingerprint_changes_with_params(tmp_path, case):
    r = _proj(tmp_path)
    base = _fp(r, "tests/test_a.py", "tests/test_b.py")
    args, env = VARIANTS_DIFFER[case]
    assert _fp(r, *args, env=env)["fingerprint"] != base["fingerprint"]


@pytest.mark.parametrize("case", sorted(VARIANTS_EQUAL))
def test_fingerprint_ignores_display_params(tmp_path, case):
    r = _proj(tmp_path)
    assert _fp(r, *VARIANTS_EQUAL[case])["fingerprint"] == _fp(r, *EQUAL_BASE[case])["fingerprint"]


def test_mutation_argv_norm_keeps_quiet(tmp_path):
    """mutant：argv_norm 不去 -q（verbose／quiet 計入）⇒「只改 -q 相等」之案改為不等。"""
    inj = Inject().prelude("_orig = rec.argv_norm\n\n\ndef _keep(config):\n"
                           "    return _orig(config) + '|verbose=' + str(config.option.verbose)\n").setattr("argv_norm", "_keep")
    r = _proj(tmp_path, conftest=inj.conftest())
    a = _fp(r, *VARIANTS_EQUAL["extra_quiet"])["fingerprint"]
    b = _fp(r, *EQUAL_BASE["extra_quiet"])["fingerprint"]
    assert a != b


UNSTABLE = ("_orig = rec.sha256_file\n\n\ndef _touching(path):\n    out = _orig(path)\n"
            "    with open(path, 'ab') as fh:\n        fh.write(b'x')\n    return out\n\n\nrec.sha256_file = _touching")


def _with_kline(r: TmpRepo, content: bytes = b"0123456789" * 100) -> Path:
    p = r.p(KLINE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p


def test_kline_changing_during_hash_is_unstable_and_unique(tmp_path):
    """雜湊期間 kline 檔兩度變動 ⇒ kline_sha256＝unstable，fingerprint／duration_class 皆不與任何 session 相同
    （兩個 unstable session 其餘欄位全同亦然：公式之 U＝session_id）；不寫快取。"""
    r = _proj(tmp_path, conftest=_conftest(UNSTABLE))
    _with_kline(r)
    a, b = _fp(r, "tests/test_a.py"), _fp(r, "tests/test_a.py")
    assert a["kline_sha256"] == b["kline_sha256"] == "unstable"
    assert a["fingerprint"] != b["fingerprint"] and a["duration_class"] != b["duration_class"]
    cache = r.p(".testreg/kline_sha_cache.json")
    assert not cache.exists()


# ── ⑥ 並行合併 summary ──────────────────────────────────────────────────────────────────────────────

SLOW_READ = ("import time\n_orig_read = rec.read_summary\n\n\ndef _slow(path, schema):\n    out = _orig_read(path, schema)\n"
             "    time.sleep(1.5)\n    return out\n\n\nrec.read_summary = _slow")


def _parallel(r: TmpRepo, files: List[str]) -> None:
    env = clean_env(PYTHONPATH=os.pathsep.join([str(PLUGIN_DIR), str(r.root)]))
    procs = [subprocess.Popen([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "-p", PLUGIN_MOD, f],
                              cwd=str(r.root), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for f in files]
    for p in procs:
        p.communicate(timeout=120)


def test_parallel_sessions_merge_all_records(tmp_path):
    r = _proj(tmp_path, conftest=_conftest(SLOW_READ))
    recorded_pytest(r, "tests/test_a.py")  # 先有合法 summary ⇒ 之後為增量合併（非重建）
    _parallel(r, ["tests/test_a.py", "tests/test_b.py"])
    s = _summary(r)
    assert len(s["nodes"]["tests/test_a.py::test_a1"]) == 2
    assert len(s["nodes"]["tests/test_b.py::test_b1"]) == 1


def test_mutation_no_lock_loses_records(tmp_path):
    inj = Inject().prelude(SLOW_READ + "\nimport contextlib").setattr("summary_lock",
                                                                     "lambda lock_path: contextlib.nullcontext()")
    r = _proj(tmp_path, conftest=inj.conftest())
    recorded_pytest(r, "tests/test_a.py")
    _parallel(r, ["tests/test_a.py", "tests/test_b.py"])
    s = _summary(r)
    got = len(s["nodes"].get("tests/test_a.py::test_a1", [])) + len(s["nodes"].get("tests/test_b.py::test_b1", []))
    assert got < 3


# ── ⑦／⑧ kline 雜湊快取 ─────────────────────────────────────────────────────────────────────────────

def test_kline_same_size_content_with_mtime_reset_changes_sha(tmp_path):
    r = _proj(tmp_path)
    p = _with_kline(r, b"A" * 1000)
    st = p.stat()
    first = _fp(r, "tests/test_a.py")["kline_sha256"]
    p.write_bytes(b"B" * 1000)
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    second = _fp(r, "tests/test_a.py")["kline_sha256"]
    assert first != second and second == __import__("hashlib").sha256(b"B" * 1000).hexdigest()


def test_mutation_cache_key_without_ctime_returns_stale(tmp_path):
    inj = Inject().setattr("kline_cache_key", "lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, 0)")
    r = _proj(tmp_path, conftest=inj.conftest())
    p = _with_kline(r, b"A" * 1000)
    st = p.stat()
    first = _fp(r, "tests/test_a.py")["kline_sha256"]
    p.write_bytes(b"B" * 1000)
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert _fp(r, "tests/test_a.py")["kline_sha256"] == first


def test_kline_cache_written_and_valid_under_parallel(tmp_path):
    r = _proj(tmp_path)
    p = _with_kline(r, b"C" * 4096)
    _parallel(r, ["tests/test_a.py", "tests/test_b.py"])
    cache = json.loads(r.read(".testreg/kline_sha_cache.json"))
    st = p.stat()
    assert cache == {"key": [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns],
                     "sha256": __import__("hashlib").sha256(b"C" * 4096).hexdigest()}


def test_kline_cache_corrupt_treated_as_absent(tmp_path):
    r = _proj(tmp_path)
    _with_kline(r, b"D" * 100)
    r.write(".testreg/kline_sha_cache.json", "{broken")
    assert _fp(r, "tests/test_a.py")["kline_sha256"] == __import__("hashlib").sha256(b"D" * 100).hexdigest()


# ── ⑨ 收集錯誤 ──────────────────────────────────────────────────────────────────────────────────────

def test_collect_error_recorded(tmp_path):
    r = _proj(tmp_path, {**SIMPLE, "tests/test_broken.py": "import no_such_module_testreg_xyz\n"})
    _, ids = recorded_pytest(r, "tests")
    colls = [x for x in r.ledger(_only(ids)) if x.get("kind") == "collect"]
    assert [c["path"] for c in colls] == ["tests/test_broken.py"]
    assert isinstance(colls[0]["exception_type"], str) and colls[0]["exception_type"]
    assert colls[0]["exception_head"] and len(colls[0]["exception_head"]) <= 300
    assert session_of(r, ids[0])["session_id"] == ids[0]  # 收集錯誤中止之 session 仍寫 ledger（pytest 預設不跑其餘測試）


# ── 邊界 ─────────────────────────────────────────────────────────────────────────────────────────────

def test_boundary_01_kline_absent_recorded(tmp_path):
    r = _proj(tmp_path)
    assert not r.p(KLINE).exists()
    s = _fp(r, "tests/test_a.py")
    assert s["kline_sha256"] == "absent"


KILL = "import os\nimport signal\n\n\ndef test_kill():\n    os.kill(os.getpid(), signal.SIGKILL)\n"


def test_boundary_02_sigkill_leaves_no_partial_and_stale_tmp_cleaned(tmp_path):
    r = _proj(tmp_path, {**SIMPLE, "tests/test_kill.py": KILL})
    proc, ids = recorded_pytest(r, "tests/test_kill.py")
    assert proc.returncode == -signal.SIGKILL and ids == []
    ledger = r.p(".testreg/ledger")
    assert not ledger.exists() or all(p.name.endswith(".jsonl") for p in ledger.iterdir())
    ledger.mkdir(parents=True, exist_ok=True)
    dead = subprocess.Popen(["true"])
    dead.wait()
    stale = ledger / f"{uuid.uuid4()}.jsonl.tmp-{dead.pid}"
    alive = ledger / f"{uuid.uuid4()}.jsonl.tmp-{os.getpid()}"
    stale.write_text("partial", encoding="utf-8")
    alive.write_text("in progress", encoding="utf-8")
    recorded_pytest(r, "tests/test_a.py")
    assert not stale.exists() and alive.exists()


# ── §G 不變性基準（收據比對）─────────────────────────────────────────────────────────────────────────

BASELINE = REPO / "handoffs/run_receipts/testreg-recorder-baseline.json"
VERIFY = REPO / "handoffs/run_receipts/testreg-recorder-verify.json"


def test_g_recorder_invariance_receipts():
    """§G：裝記錄器後同命令之 ①outcome sha256 ②順序 sha256 ③rc 逐項 == 基準；④porcelain 去 `.testreg/` 列後 == 基準；
    樣本清單＝凍結時寫死者（兩收據相同），且基準於記錄器掛載前之提交產生。"""
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    ver = json.loads(VERIFY.read_text(encoding="utf-8"))
    assert base["sample"] == ver["sample"] and base["command"] == ver["command"]
    assert base["sample"][:2] == ["tests/feature_engineering/test_framepath_disposition.py",
                                  "tests/governance/test_mutation_scope_extension.py"]
    api = base["sample"][2:]
    assert len(api) == 10 and all(s.startswith("tests/api/test_") for s in api) and api == sorted(api)
    assert base["sample_rule"] == "tests/api 依路徑字典序前 10 檔（凍結時之 git ls-files）"
    for key in ("outcomes_sha256", "order_sha256", "rc", "porcelain_sha256_without_testreg"):
        assert ver[key] == base[key], key
    assert base["recorder_loaded"] is False and ver["recorder_loaded"] is True
    assert ver["ledger_sessions_written"] >= 1
