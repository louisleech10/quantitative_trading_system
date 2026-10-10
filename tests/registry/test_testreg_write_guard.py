"""TESTREG Task 1.5 驗收：產出端登記檢查 `scripts/testreg_write_guard.sh`（PostToolUse Edit|Write）與 pre-commit
`testreg.py check --staged`（docs/TESTREG_SPEC.md）。

hook 案例以 PostToolUse payload 呼叫暫存倉內之 hook 複本（repo 根由 hook 位置推導）；pre-commit 案例於暫存倉安裝只跑
`testreg.py check --staged` 之 pre-commit 後以 `git commit` 驗；真實 repo 驗 hook 掛載、pre-commit 接線與牆鐘（⑧）。
實作前（hook 與 check 為空殼）為紅。
"""
from __future__ import annotations

import importlib
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Dict

import pytest

from tests.registry.testreg_helpers import (
    CATALOG_REL, PY, REPO, TmpRepo, bootstrap_entry, clean_env, entry, fact_keys_rows, make_repo, schema,
)

testreg = importlib.import_module("scripts.testreg")

T_KEEP = '''from momentum.calc import add


def test_one():
    result = add(1, 2)
    expected = 3
    assert result == expected
    assert result > 0


def test_two():
    assert add(2, 2) == 4
'''
CALC = "def add(a, b):\n    return a + b\n"
BASE = {"momentum/__init__.py": "", "momentum/calc.py": CALC, "tests/test_keep.py": T_KEEP}
REF = "handoffs/reconcile/20261010-testreg-x-review-r16/synth.md"


def _repo(tmp_path: Path, files: Dict[str, str] = None) -> TmpRepo:
    return make_repo(tmp_path, files or BASE)


def _edit(r: TmpRepo, rel: str, old: str, new: str) -> None:
    text = r.read(rel)
    assert old in text, (rel, old)
    r.write(rel, text.replace(old, new, 1))


def _hook_rc(r: TmpRepo, rel: str) -> int:
    return r.hook(rel).returncode


# ── ①② 新增測試檔與登記 ──────────────────────────────────────────────────────────────────────────────

def test_01_new_test_file_without_entry_hook_red(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_new.py", "def test_n():\n    assert True\n")
    proc = r.hook("tests/test_new.py", tool="Write")
    assert proc.returncode == 2 and "tests/test_new.py" in proc.stderr


def test_02_entry_unclassified_red_then_classified_green(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_new.py", "def test_n():\n    assert True\n")
    r.put_entry(bootstrap_entry("tests/test_new.py"))
    assert _hook_rc(r, CATALOG_REL) == 2 and _hook_rc(r, "tests/test_new.py") == 2
    r.put_entry(entry("tests/test_new.py"))
    assert _hook_rc(r, CATALOG_REL) == 0 and _hook_rc(r, "tests/test_new.py") == 0


class HookCopy:
    """暫存倉內之 hook 複本；`patch(body)` 以 body 置換其內容（mutant）。"""

    def __init__(self, r: TmpRepo) -> None:
        self.path = r.p("scripts/testreg_write_guard.sh")

    def patch(self, body: str) -> None:
        self.path.write_text(body, encoding="utf-8")


def test_02b_catalog_hook_checks_all_entries(tmp_path):
    """寫 catalog.json 時 entry 規則對全部 entry：HEAD 已有一筆壞 entry（未經本次改動），本次只改另一筆 ⇒ 仍 rc≠0
    且指名壞 entry；修正後 rc=0。"""
    r = _repo(tmp_path, {**BASE, "tests/test_other.py": "def test_o():\n    assert True\n"})
    cat = r.catalog()
    cat["entries"]["tests/test_other.py"]["owner"] = "x"
    r.set_catalog(cat)
    r.commit("bad entry (無 pre-commit)")
    r.put_entry(entry("tests/test_keep.py", disposition_ref=REF))
    proc = r.hook(CATALOG_REL)
    assert proc.returncode == 2 and any(l.startswith("V03 tests/test_other.py") for l in proc.stderr.splitlines()), \
        proc.stderr
    r.put_entry(entry("tests/test_other.py"))
    assert _hook_rc(r, CATALOG_REL) == 0


def test_mutation_hook_always_zero_misses_01(tmp_path):
    """mutant：hook 恆 rc=0 ⇒ ① 之案放行（即 ① 之紅來自 hook 判定）。"""
    r = _repo(tmp_path)
    r.write("tests/test_new.py", "def test_n():\n    assert True\n")
    assert _hook_rc(r, "tests/test_new.py") == 2
    HookCopy(r).patch("#!/usr/bin/env bash\ncat >/dev/null\nexit 0\n")
    assert _hook_rc(r, "tests/test_new.py") == 0


# ── ③ 刪檔無碑（pre-commit）─────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("drop_entry", [False, True])
def test_03_git_rm_without_tombstone_precommit_red(tmp_path, drop_entry):
    r = _repo(tmp_path)
    r.install_precommit()
    r.git("rm", "-q", "tests/test_keep.py")
    if drop_entry:
        cat = r.catalog()
        del cat["entries"]["tests/test_keep.py"]
        r.set_catalog(cat)
        r.stage(CATALOG_REL)
    proc = r.try_commit()
    assert proc.returncode != 0, proc.stderr


def test_mutation_precommit_ignores_deletions(tmp_path, monkeypatch, capsys):
    """mutant：pre-commit 不查刪除（暫存區變更清單去掉 D）⇒ ③（entry 一併刪除）之提交通過。"""
    r = _repo(tmp_path)
    r.git("rm", "-q", "tests/test_keep.py")
    cat = r.catalog()
    del cat["entries"]["tests/test_keep.py"]
    r.set_catalog(cat)
    r.stage(CATALOG_REL)
    assert testreg.main(["--repo", str(r.root), "check", "--staged"]) != 0
    orig = testreg.staged_changes
    monkeypatch.setattr(testreg, "staged_changes", lambda root: {p: s for p, s in orig(root).items() if s != "D"})
    assert testreg.main(["--repo", str(r.root), "check", "--staged"]) == 0
    capsys.readouterr()


# ── ④ quarantine 逾期（hook）─────────────────────────────────────────────────────────────────────────

def test_04_quarantine_expired_hook_red(tmp_path):
    r = _repo(tmp_path)
    sid = "12345678-1234-4123-8123-123456789abc"
    q = {"nodeid": "tests/test_keep.py::test_one", "reason": "r", "expires": "2000-01-01", "disposition_ref": REF,
         "evidence": [{"session_id": sid, "nodeid": "tests/test_keep.py::test_one"}] * 2}
    r.put_entry(entry("tests/test_keep.py", quarantine=[q]))
    proc = r.hook(CATALOG_REL)
    assert proc.returncode == 2 and any(l.startswith("V11 ") for l in proc.stderr.splitlines()), proc.stderr


# ── ⑤ 待改寫檔有暫存變更而無收據（pre-commit）────────────────────────────────────────────────────────

def test_05_rewrite_file_staged_change_without_receipt_precommit_red(tmp_path):
    r = _repo(tmp_path)
    r.put_entry(entry("tests/test_keep.py", disposition="rewrite", disposition_ref=REF,
                      rewrite_targets=["tests/test_keep.py::test_two"]))
    r.commit("classify")
    r.install_precommit()
    _edit(r, "tests/test_keep.py", "    assert add(2, 2) == 4\n", "    assert add(2, 2) == 4\n    assert add(0, 2) == 2\n")
    r.stage("tests/test_keep.py")
    proc = r.try_commit()
    assert proc.returncode != 0 and "V07" in proc.stderr, proc.stderr


# ── ⑥ 新碑指向未收案且閘不解析碑之 manifest（pre-commit）────────────────────────────────────────────

def test_06_new_tombstone_in_unsafe_manifest_precommit_red(tmp_path):
    r = _repo(tmp_path, {**BASE, "docs/manifests/M.json": json.dumps({
        "spec_path": "docs/OPEN_SPEC.md", "test_files": ["tests/test_keep.py"], "script_acceptance": [],
        "stub_modules": [], "contract_jsons": [], "run_receipts": [],
        "batch_card": {"gate_cmd": "venv/bin/python -m pytest tests/test_keep.py", "risk_mitigation": []}}),
        "scripts/fact_keys.json": json.dumps(fact_keys_rows([["001", "HP-OPEN", "進行中", "docs/OPEN_SPEC.md", "—"]]))})
    r.install_precommit()
    _edit(r, "tests/test_keep.py", "\n\ndef test_two():\n    assert add(2, 2) == 4\n", "\n")
    r.add_tombstone({"nodeid": "tests/test_keep.py::test_two", "evidence_level": "E0",
                     "evidence_receipt": "handoffs/run_receipts/testreg-retire/x.json", "replaced_by": [],
                     "disposition_ref": REF})
    r.stage(".")
    proc = r.try_commit()
    assert proc.returncode != 0 and "V14" in proc.stderr, proc.stderr


# ── ⑦ 斷言多重集合（hook）───────────────────────────────────────────────────────────────────────────

# check_pos 之名符合 assertion_nodes 第 4 類（^check_）且本身含斷言：依 SPEC v17，屬 assertion_helpers 之呼叫一律
# 以展開取代（不另計呼叫節點）——07c 以此釘住「刪 helper 內斷言必被偵測」。其餘 helper 刻意不用 check_／verify_ 等前綴。
HELPERS_FX = '''def check_pos(x):
    assert x > 0
    assert x < 100


def check(actual, limit):
    assert actual < limit


def close_enough(x, t):
    assert abs(x) < t


def all_positive(*args):
    assert all(a > 0 for a in args)
    assert len(args) > 0
'''
CONFTEST = '''import pytest


@pytest.fixture
def checked_value():
    value = 5
    assert value > 0
    assert value < 10
    return value
'''
T_FX = '''from momentum.calc import add
from tests.fixtures.fx_helpers import all_positive, check, check_pos, close_enough


def test_uses_helper():
    check_pos(add(1, 2))


def test_uses_fixture(checked_value):
    assert checked_value == 5


def test_threshold():
    actual = add(1, 1)
    check(actual, 3)


def test_tolerance():
    tol = 1e-9
    d = add(0.1, -0.1)
    assert abs(d) < tol


def test_swap():
    a = add(1, 1)
    b = add(2, 2)
    assert a < b


def test_identity():
    result = add(1, 2)
    expected = 3
    assert result == expected


def test_star():
    vals = [add(1, 1), add(2, 2)]
    all_positive(*vals)
'''
T_AUTOUSE = '''import pytest
from momentum.calc import add


@pytest.fixture
def base_value():
    v = add(1, 1)
    assert v == 2
    return v


@pytest.fixture(autouse=True)
def env_ready(base_value):
    assert add(0, 0) == 0
    assert base_value > 0
    yield


def test_a():
    assert add(1, 2) == 3


def test_b():
    assert add(2, 3) == 5
'''
TOL_MOD = "TOL = 1e-9\n"
CHECKS_MOD = "from tests.helpers.tolerances import TOL\n\n\ndef check_close(x, t=TOL):\n    assert abs(x) < t\n"
T_TOL = '''import tests.helpers.tolerances as tol
from tests.helpers import tolerances
from tests.helpers.checks import check_close
from tests.helpers.tolerances import TOL
from momentum.calc import add


def test_from_import():
    assert abs(add(0.1, -0.1)) < TOL


def test_module_alias():
    assert abs(add(0.1, -0.1)) < tol.TOL


def test_package_from_import():
    assert abs(add(0.1, -0.1)) < tolerances.TOL


def test_default_value():
    check_close(add(0.1, -0.1))


def test_function_level_import():
    from tests.helpers.tolerances import TOL
    assert abs(add(0.2, -0.2)) < TOL


def test_unrelated():
    assert add(1, 1) == 2
'''
T_LOCAL = '''from momentum.calc import add


def check_local(x):
    assert x > 0
    assert x < 9


def test_local():
    check_local(add(1, 2))
'''
FX_FILES = {**BASE, "tests/test_local.py": T_LOCAL, "tests/__init__.py": "", "tests/fixtures/__init__.py": "",
            "tests/fixtures/fx_helpers.py": HELPERS_FX,
            "tests/conftest.py": CONFTEST, "tests/test_fx.py": T_FX, "tests/test_autouse.py": T_AUTOUSE,
            "tests/helpers/__init__.py": "", "tests/helpers/tolerances.py": TOL_MOD, "tests/helpers/checks.py": CHECKS_MOD,
            "tests/test_tol.py": T_TOL}


def _v19_subjects(stderr: str) -> set:
    return {l.split(" ", 1)[1].split(": ", 1)[0] for l in stderr.splitlines() if l.startswith("V19 ")}


HOOK_CASES = {
    # 名稱: (檔, 舊, 新, 預期 V19 nodeid 集合〔空＝rc 0〕)
    "07_delete_assert_in_keep_file": ("tests/test_keep.py", "    assert result > 0\n", "",
                                      {"tests/test_keep.py::test_one"}),
    "07c_fixtures_helper_drops_assert": ("tests/fixtures/fx_helpers.py", "    assert x < 100\n", "",
                                         {"tests/test_fx.py::test_uses_helper"}),
    "07c_conftest_fixture_drops_assert": ("tests/conftest.py", "    assert value < 10\n", "",
                                          {"tests/test_fx.py::test_uses_fixture"}),
    "07c_helper_local_rename_ok": ("tests/conftest.py", "    value = 5\n    assert value > 0\n    assert value < 10\n"
                                   "    return value\n", "    v = 5\n    assert v > 0\n    assert v < 10\n    return v\n",
                                   set()),
    "07d_local_constant_changed": ("tests/test_fx.py", "    tol = 1e-9\n", "    tol = 1e-3\n",
                                   {"tests/test_fx.py::test_tolerance"}),
    "07e_helper_threshold_argument": ("tests/test_fx.py", "    check(actual, 3)\n", "    check(actual, 4)\n",
                                      {"tests/test_fx.py::test_threshold"}),
    "07f_compare_to_itself": ("tests/test_fx.py", "    assert result == expected\n", "    assert result == result\n",
                              {"tests/test_fx.py::test_identity"}),
    "07g_extract_to_helper_ok": ("tests/test_fx.py", "    assert abs(d) < tol\n", "    close_enough(d, tol)\n", set()),
    "07h_swap_operands": ("tests/test_fx.py", "    assert a < b\n", "    assert b < a\n", {"tests/test_fx.py::test_swap"}),
    "07i_autouse_fixture_drops_assert": ("tests/test_autouse.py", "    assert add(0, 0) == 0\n", "",
                                         {"tests/test_autouse.py::test_a", "tests/test_autouse.py::test_b"}),
    "07j_star_args_helper_drops_assert": ("tests/fixtures/fx_helpers.py", "    assert len(args) > 0\n", "",
                                          {"tests/test_fx.py::test_star"}),
    "07k_unrelated_assignment_ok": ("tests/test_fx.py", "    assert a < b\n", "    unused = 7\n    assert a < b\n", set()),
    "07l_fixture_dependency_of_autouse": ("tests/test_autouse.py", "    assert v == 2\n", "",
                                          {"tests/test_autouse.py::test_a", "tests/test_autouse.py::test_b"}),
    "07o_local_helper_in_test_module_drops_assert": ("tests/test_local.py", "    assert x < 9\n", "",
                                                     {"tests/test_local.py::test_local"}),
    "07o_local_helper_param_rename_ok": ("tests/test_local.py", "def check_local(x):\n    assert x > 0\n"
                                         "    assert x < 9\n", "def check_local(y):\n    assert y > 0\n    assert y < 9\n",
                                         set()),
    "07m_module_constant_import_forms": ("tests/helpers/tolerances.py", "TOL = 1e-9\n", "TOL = 1e-3\n",
                                         {f"tests/test_tol.py::{n}" for n in (
                                             "test_from_import", "test_module_alias", "test_package_from_import",
                                             "test_default_value", "test_function_level_import")}),
}


@pytest.mark.parametrize("case", sorted(HOOK_CASES))
def test_07_hook_assertion_multiset(tmp_path, case):
    rel, old, new, expect = HOOK_CASES[case]
    r = _repo(tmp_path, FX_FILES)
    _edit(r, rel, old, new)
    proc = r.hook(rel)
    assert proc.returncode == (2 if expect else 0), proc.stderr
    assert _v19_subjects(proc.stderr) == expect, proc.stderr


def test_07b_delete_whole_function_hook_red(tmp_path):
    r = _repo(tmp_path)
    _edit(r, "tests/test_keep.py", "\n\ndef test_two():\n    assert add(2, 2) == 4\n", "\n")
    proc = r.hook("tests/test_keep.py")
    assert proc.returncode == 2 and any(l.startswith("V20 tests/test_keep.py::test_two") for l in proc.stderr.splitlines())


def test_07c_helper_change_lists_callers(tmp_path):
    r = _repo(tmp_path, FX_FILES)
    _edit(r, "tests/fixtures/fx_helpers.py", "    assert x < 100\n", "")
    # helper_callers 為檔層候選集合：該檔任一 helper 之呼叫者（試作實證；被報 V19 者另由 07c 案例斷言只有 test_uses_helper）
    assert testreg.helper_callers(r.root, "tests/fixtures/fx_helpers.py") == [
        "tests/test_fx.py::test_star", "tests/test_fx.py::test_threshold", "tests/test_fx.py::test_uses_helper"]
    proc = r.hook("tests/fixtures/fx_helpers.py")
    assert "tests/test_fx.py::test_uses_helper" in proc.stderr


def test_mutation_hook_v19_count_only_misses_weaker(tmp_path, monkeypatch, capsys):
    """mutant：V19 只比斷言數 ⇒「換成較弱斷言」（數目不變）之 check 放行。"""
    r = _repo(tmp_path)
    _edit(r, "tests/test_keep.py", "    assert result == expected\n", "    assert result is not None\n")
    assert testreg.main(["--repo", str(r.root), "check", "--paths", "tests/test_keep.py"]) != 0
    monkeypatch.setattr(testreg, "multiset_decreased",
                        lambda o, n: ["<count>"] if sum(o.values()) > sum(n.values()) else [])
    assert testreg.main(["--repo", str(r.root), "check", "--paths", "tests/test_keep.py"]) == 0
    capsys.readouterr()


def test_mutation_helper_callers_empty_misses_07c(tmp_path, monkeypatch, capsys):
    """mutant：helper 反推呼叫者恆空 ⇒ 07c 之 helper 刪斷言放行。"""
    r = _repo(tmp_path, FX_FILES)
    _edit(r, "tests/fixtures/fx_helpers.py", "    assert x < 100\n", "")
    assert testreg.main(["--repo", str(r.root), "check", "--helpers", "tests/fixtures/fx_helpers.py"]) != 0
    monkeypatch.setattr(testreg, "helper_callers", lambda *a, **k: [])
    assert testreg.main(["--repo", str(r.root), "check", "--helpers", "tests/fixtures/fx_helpers.py"]) == 0
    capsys.readouterr()


# ── ⑦n manifest 變更致既有碑落入不安全之 manifest（hook 與 pre-commit）──────────────────────────────────

def test_07n_manifest_change_hook_and_precommit_red(tmp_path):
    man = {"spec_path": "docs/OPEN_SPEC.md", "test_files": [], "script_acceptance": [], "stub_modules": [],
           "contract_jsons": [], "run_receipts": [],
           "batch_card": {"gate_cmd": "venv/bin/python -m pytest tests/x.py", "risk_mitigation": []}}
    r = _repo(tmp_path, {**BASE, "docs/manifests/M.json": json.dumps(man),
                         "scripts/fact_keys.json": json.dumps(fact_keys_rows([["001", "HP-OPEN", "進行中",
                                                                                "docs/OPEN_SPEC.md", "—"]]))})
    _edit(r, "tests/test_keep.py", "\n\ndef test_two():\n    assert add(2, 2) == 4\n", "\n")
    r.add_tombstone({"nodeid": "tests/test_keep.py::test_two", "evidence_level": "E0",
                     "evidence_receipt": "handoffs/run_receipts/testreg-retire/x.json", "replaced_by": [],
                     "disposition_ref": REF})
    r.commit("tombstone (無 pre-commit)")
    r.install_precommit()
    man["batch_card"]["risk_mitigation"] = ["affected_must phase=1 tests/test_keep.py::test_two"]
    r.write("docs/manifests/M.json", json.dumps(man))
    proc = r.hook("docs/manifests/M.json")
    assert proc.returncode == 2 and "V22" in proc.stderr, proc.stderr
    r.stage("docs/manifests/M.json")
    proc = r.try_commit()
    assert proc.returncode != 0 and "V22" in proc.stderr, proc.stderr


# ── 邊界 ─────────────────────────────────────────────────────────────────────────────────────────────

def test_boundary_01_outside_tests_not_checked(tmp_path):
    r = _repo(tmp_path)
    r.write("momentum/calc.py", CALC + "\n# edit\n")
    r.write("tests/test_new.py", "def test_n():\n    assert True\n")  # 未登記，但本次寫入之檔不在 tests/
    assert _hook_rc(r, "momentum/calc.py") == 0


def test_boundary_03_edit_registered_file_and_helper_without_decrease_rc0(tmp_path):
    r = _repo(tmp_path, FX_FILES)
    _edit(r, "tests/test_keep.py", "def test_two():\n", "def test_two():\n    \"\"\"說明。\"\"\"\n")
    _edit(r, "tests/fixtures/fx_helpers.py", "def check(actual, limit):\n", "def check(actual, limit):\n    \"\"\"門檻。\"\"\"\n")
    for rel in ("tests/test_keep.py", "tests/fixtures/fx_helpers.py"):
        proc = r.hook(rel)
        assert proc.returncode == 0, (rel, proc.stderr)


def test_boundary_04_add_assertion_rc0(tmp_path):
    r = _repo(tmp_path)
    _edit(r, "tests/test_keep.py", "    assert add(2, 2) == 4\n", "    assert add(2, 2) == 4\n    assert add(3, 3) == 6\n")
    assert _hook_rc(r, "tests/test_keep.py") == 0


def test_boundary_05_helper_backprop_wall_clock_median_under_1s():
    """真實 repo：tests/conftest.py（全部 fixture 之呼叫者反推）未改動而觸發 hook，10 次牆鐘中位 < 1 s。"""
    times = _hook_times("tests/conftest.py")
    assert statistics.median(times) < 1.0, times


def test_boundary_02_registry_contract_runs_validate_only(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/registry/notes.json", "{}\n")
    assert _hook_rc(r, "tests/registry/notes.json") == 0
    cat = r.catalog()
    cat["entries"]["tests/test_keep.py"]["owner"] = "x"
    r.set_catalog(cat)
    proc = r.hook("tests/registry/notes.json")
    assert proc.returncode == 2 and any(l.startswith("V03 ") for l in proc.stderr.splitlines()), proc.stderr


# ── 真實 repo：掛載、接線、牆鐘（⑧／邊界 05）────────────────────────────────────────────────────────────

def test_hook_mounted_and_registered():
    settings = json.loads((REPO / ".claude/settings.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for g in settings["hooks"]["PostToolUse"] if g.get("matcher") == "Edit|Write"
            for h in g["hooks"]]
    assert "bash scripts/testreg_write_guard.sh" in cmds
    reg = (REPO / "docs/GOV_ENFORCEMENT_REGISTRY.md").read_text(encoding="utf-8")
    assert "testreg_write_guard.sh" in reg


def test_precommit_wired_with_direct_rc():
    text = (REPO / "scripts/git_hooks/pre-commit").read_text(encoding="utf-8")
    lines = text.splitlines()
    idx = [i for i, l in enumerate(lines) if "scripts/testreg.py check --staged" in l]
    assert len(idx) == 1
    i = idx[0]
    assert "|" not in lines[i].split("scripts/testreg.py check --staged", 1)[1]
    assert "$?" in lines[i + 1]
    final = max(j for j, l in enumerate(lines) if l.startswith("exec "))
    assert i < final


def _hook_times(rel: str) -> list:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(REPO / rel)}})
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        proc = subprocess.run(["bash", str(REPO / "scripts/testreg_write_guard.sh")], input=payload, capture_output=True,
                              text=True, env=clean_env(), cwd=str(REPO))
        times.append(time.perf_counter() - t0)
        assert proc.returncode == 0, proc.stderr
    assert len(json.loads((REPO / CATALOG_REL).read_text(encoding="utf-8"))["entries"]) >= 642
    return times


@pytest.mark.parametrize("rel", ["tests/registry/test_testreg_validate.py", "docs/manifests/TESTREG.json"])
def test_08_hook_wall_clock_median_under_1s(rel):
    """⑧：真實 repo（全量 entries）未改動之測試檔／manifest 觸發 hook，10 次牆鐘中位 < 1 s（helper 反推見邊界 05）。"""
    assert statistics.median(_hook_times(rel)) < 1.0
