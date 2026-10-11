"""TESTREG Task 1.5 驗收：產出端登記檢查 `scripts/testreg_write_guard.sh`（PostToolUse Edit|Write）與 pre-commit
`testreg.py check --staged`（docs/TESTREG_SPEC.md）。

hook 案例以 PostToolUse payload 呼叫暫存倉內之 hook 複本（repo 根由 hook 位置推導）；pre-commit 案例於暫存倉安裝只跑
`testreg.py check --staged` 之 pre-commit 後以 `git commit` 驗；真實 repo 驗 hook 掛載、pre-commit 接線與牆鐘（⑧）。
實作前（hook 與 check 為空殼）為紅。
"""
from __future__ import annotations

import ast
import configparser
import fnmatch
import importlib
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Dict, List

import pytest

from tests.registry.testreg_helpers import (
    CATALOG_REL, PY, REPO, TmpRepo, bootstrap_entry, clean_env, entry, fact_keys_rows, is_test_path, make_repo, schema,
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

pytest_plugins = ["tests.plugins.plug"]


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
    from tests.fixtures.fx_helpers import check_pos
    check_pos(base_value)
    assert add(0, 0) == 0
    assert base_value > 0
    yield


def test_a():
    assert add(1, 2) == 3


def test_b():
    assert add(2, 3) == 5
'''
TOL_MOD = "TOL = 1e-9\n"
CHECKS_MOD = ("from tests.helpers.tolerances import TOL\nimport tests.helpers.tolerances as tolmod\n"
              "from tests.helpers import tolerances as tolpkg\n\n\ndef check_close(x, t=TOL):\n    assert abs(x) < t\n\n\n"
              "def check_alias(x):\n    assert abs(x) < tolmod.TOL\n\n\ndef check_pkg(x):\n    assert abs(x) < tolpkg.TOL\n")
T_TOL = '''import tests.helpers.tolerances as tol
from tests.helpers import tolerances
from tests.helpers.checks import check_alias, check_close, check_pkg
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


def test_alias_helper():
    check_alias(add(0.1, -0.1))


def test_pkg_helper():
    check_pkg(add(0.1, -0.1))
'''
T_SHAPES = '''from momentum.calc import add
from tests.fixtures.fx_helpers import check_pos
from tests.helpers.checks import check_close


class TestK:
    def test_k(self):
        check_pos(add(1, 2))


async def test_async():
    check_close(add(0.1, -0.1))


def testhelper():
    check_close(add(0.1, -0.1))
'''
# autouse fixture 在子目錄 conftest、斷言在外部 helper：測試檔本身不 import 該 helper（審查 r24）
SUB_CONFTEST = '''import pytest


@pytest.fixture(autouse=True)
def env_checked():
    from tests.helpers.envcheck import check_env
    check_env("x")
    yield
'''
ENVCHECK = "def check_env(v):\n    assert v is not None\n    assert v != ''\n"
# pytest_plugins 所列外掛之 autouse fixture 呼叫外部 helper（審查 r25）：作用於全部測試，測試檔皆不 import 該 helper
PLUG = '''import pytest


@pytest.fixture(autouse=True)
def plug_ready():
    from tests.helpers.plughelp import check_plug
    check_plug(3)
    yield
'''
PLUGHELP = "def check_plug(v):\n    assert v > 0\n    assert v < 5\n"
T_SUB = "def test_s1():\n    assert 1 + 1 == 2\n\n\ndef test_s2():\n    assert 2 + 2 == 4\n"
T_LOCAL ='''from momentum.calc import add


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
            "tests/helpers/loose.py": "TOL = 1e-3\n", "tests/test_tol.py": T_TOL, "tests/test_shapes.py": T_SHAPES,
            "tests/helpers/envcheck.py": ENVCHECK, "tests/sub/__init__.py": "", "tests/sub/conftest.py": SUB_CONFTEST,
            "tests/sub/test_sub.py": T_SUB, "tests/plugins/__init__.py": "", "tests/plugins/plug.py": PLUG,
            "tests/helpers/plughelp.py": PLUGHELP}


def _collected(files: Dict[str, str], fn_pat: str = "test_*", cls_pat: str = "Test*") -> List[str]:
    """函式層 nodeid（fnmatch：模組層函式含 async、類別內方法；與真實樹 pytest.ini 同規則）。"""
    fn = (ast.FunctionDef, ast.AsyncFunctionDef)
    out = []
    for rel in sorted(p for p in files if is_test_path(p)):
        for n in ast.parse(files[rel]).body:
            if isinstance(n, fn) and fnmatch.fnmatchcase(n.name, fn_pat):
                out.append(f"{rel}::{n.name}")
            elif isinstance(n, ast.ClassDef) and fnmatch.fnmatchcase(n.name, cls_pat):
                out += [f"{rel}::{n.name}::{m.name}" for m in n.body
                        if isinstance(m, fn) and fnmatch.fnmatchcase(m.name, fn_pat)]
    return out


ALL_FX_TESTS = set(_collected(FX_FILES))


def _v19_subjects(stderr: str) -> set:
    return {l.split(" ", 1)[1].split(": ", 1)[0] for l in stderr.splitlines() if l.startswith("V19 ")}


HOOK_CASES = {
    # 名稱: (檔, 舊, 新, 預期 V19 nodeid 集合〔空＝rc 0〕)
    "07_delete_assert_in_keep_file": ("tests/test_keep.py", "    assert result > 0\n", "",
                                      {"tests/test_keep.py::test_one"}),
    "07c_fixtures_helper_drops_assert": ("tests/fixtures/fx_helpers.py", "    assert x < 100\n", "",
                                         {"tests/test_fx.py::test_uses_helper", "tests/test_shapes.py::TestK::test_k",
                                          "tests/test_autouse.py::test_a", "tests/test_autouse.py::test_b"}),
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
                                             "test_default_value", "test_function_level_import", "test_alias_helper",
                                             "test_pkg_helper")} | {"tests/test_shapes.py::test_async"}),
    # 07p（審查 r22／r23）：helper 模組層 import 改變——差量判定須回 None、退回完整反推
    "07p_helper_import_source_changed": ("tests/helpers/checks.py", "from tests.helpers.tolerances import TOL\n",
                                         "from tests.helpers.loose import TOL\n",
                                         {"tests/test_tol.py::test_default_value", "tests/test_shapes.py::test_async"}),
    "07p_helper_import_replaced_by_rebinding": ("tests/helpers/checks.py", "from tests.helpers.tolerances import TOL\n",
                                                "TOL = 1e-3\n", {"tests/test_tol.py::test_default_value",
                                                                 "tests/test_shapes.py::test_async"}),
    "07p_helper_alias_import_source_changed": ("tests/helpers/checks.py", "import tests.helpers.tolerances as tolmod\n",
                                               "import tests.helpers.loose as tolmod\n",
                                               {"tests/test_tol.py::test_alias_helper"}),
    "07p_helper_package_import_source_changed": ("tests/helpers/checks.py",
                                                 "from tests.helpers import tolerances as tolpkg\n",
                                                 "from tests.helpers import loose as tolpkg\n",
                                                 {"tests/test_tol.py::test_pkg_helper"}),
    "07p_conftest_unrelated_import_ok": ("tests/conftest.py", "import pytest\n", "import os\nimport pytest\n", set()),
    # 07q（審查 r24）：子目錄 conftest 之 autouse fixture 呼叫外部 helper，測試檔不 import 該 helper
    "07q_conftest_autouse_external_helper_drops_assert": ("tests/helpers/envcheck.py", "    assert v != ''\n", "",
                                                          {"tests/sub/test_sub.py::test_s1",
                                                           "tests/sub/test_sub.py::test_s2"}),
    # 07r（審查 r25）：fixture 由 autouse 改為普通（本體不變）——受其保護之測試失去其斷言
    "07r_conftest_autouse_turned_off": ("tests/sub/conftest.py", "@pytest.fixture(autouse=True)\n", "@pytest.fixture\n",
                                        {"tests/sub/test_sub.py::test_s1", "tests/sub/test_sub.py::test_s2"}),
    "07r_module_autouse_turned_off": ("tests/test_autouse.py", "@pytest.fixture(autouse=True)\n", "@pytest.fixture\n",
                                      {"tests/test_autouse.py::test_a", "tests/test_autouse.py::test_b"}),
    # 07v（審查 r30）：對既有測試新增 skip／skipif／xfail（斷言不變但不再執行）⇒ 視同斷言歸零（schema skip_rule）
    "07v_function_xfail_added": ("tests/test_autouse.py", "def test_a():\n", "@pytest.mark.xfail(reason=\"r30\")\ndef test_a():\n",
                                 {"tests/test_autouse.py::test_a"}),
    "07v_body_skip_call_added": ("tests/test_autouse.py", "def test_b():\n", "def test_b():\n    pytest.skip(\"r30\")\n",
                                 {"tests/test_autouse.py::test_b"}),
    "07v_module_pytestmark_skipif_added": ("tests/test_autouse.py", "from momentum.calc import add\n",
                                           "from momentum.calc import add\n\npytestmark = pytest.mark.skipif(True, reason=\"r30\")\n",
                                           {"tests/test_autouse.py::test_a", "tests/test_autouse.py::test_b"}),
    "07v_class_skip_added": ("tests/test_shapes.py", "\n\nclass TestK:\n", "\nimport pytest\n\n\n@pytest.mark.skip(reason=\"r30\")\nclass TestK:\n",
                             {"tests/test_shapes.py::TestK::test_k"}),
    # 07t（審查 r25）：pytest_plugins 所列外掛之 autouse fixture（作用於全部測試）
    "07t_plugin_autouse_external_helper_drops_assert": ("tests/helpers/plughelp.py", "    assert v < 5\n", "",
                                                        ALL_FX_TESTS),
    "07t_plugin_autouse_turned_off": ("tests/plugins/plug.py", "@pytest.fixture(autouse=True)\n", "@pytest.fixture\n",
                                      ALL_FX_TESTS),
}
IMPORT_CASES = sorted(c for c in HOOK_CASES if c.startswith("07p_"))
# 各 import 改變案之 decreased_defs：須含（⊇）之使用者定義、不得含之無關定義
IMPORT_DEFS = {
    "07p_helper_import_source_changed": ({"check_close"}, {"check_alias", "check_pkg"}),
    "07p_helper_import_replaced_by_rebinding": ({"check_close"}, {"check_alias", "check_pkg"}),
    "07p_helper_alias_import_source_changed": ({"check_alias"}, {"check_close", "check_pkg"}),
    "07p_helper_package_import_source_changed": ({"check_pkg"}, {"check_close", "check_alias"}),
    "07p_conftest_unrelated_import_ok": (set(), {"checked_value"}),
}


@pytest.mark.parametrize("case", sorted(HOOK_CASES))
def test_07_hook_assertion_multiset(tmp_path, case):
    rel, old, new, expect = HOOK_CASES[case]
    r = _repo(tmp_path, FX_FILES)
    _edit(r, rel, old, new)
    proc = r.hook(rel)
    assert proc.returncode == (2 if expect else 0), proc.stderr
    assert _v19_subjects(proc.stderr) == expect, proc.stderr


@pytest.mark.parametrize("case", sorted(HOOK_CASES))
def test_07u_precommit_matches_hook(tmp_path, case):
    """pre-commit 路徑與 hook 同判：每一 hook 案例只暫存被改之檔後提交 ⇒ 預期非空則 rc≠0、空則 rc=0，且 V19 主體
    逐案等於預期（測試檔、helper、conftest、外掛、autouse、import 改變各路由皆經 `check --staged`，審查 r26）。"""
    rel, old, new, expect = HOOK_CASES[case]
    r = _repo(tmp_path, FX_FILES)
    r.install_precommit()
    _edit(r, rel, old, new)
    r.stage(rel)
    proc = r.try_commit()
    assert (proc.returncode != 0) == bool(expect), proc.stderr
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
        "tests/test_autouse.py::test_a", "tests/test_autouse.py::test_b", "tests/test_fx.py::test_star",
        "tests/test_fx.py::test_threshold", "tests/test_fx.py::test_uses_helper", "tests/test_shapes.py::TestK::test_k"]
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




def _full_oracle(r: TmpRepo) -> set:
    """完整反推之定義：暫存倉每一測試函式（依暫存倉 pytest.ini 之 python_classes／python_functions 以 fnmatch 收集，
    與真實樹同為 `Test*`／`test_*`；含 async 函式與類別方法；`testhelper` 不收）於 HEAD 與工作樹各自完整展開之
    斷言多重集合比較（不經呼叫者反推）。"""
    ini = configparser.ConfigParser()
    ini.read_string(r.read("pytest.ini"))
    cls_pat, fn_pat = ini["pytest"]["python_classes"], ini["pytest"]["python_functions"]
    files = {p: r.read(p) for p in FX_FILES if is_test_path(p)}
    return {nid for nid in _collected(files, fn_pat, cls_pat)
            if testreg.multiset_decreased(testreg.assertion_multiset(r.root, nid, "HEAD"),
                                          testreg.assertion_multiset(r.root, nid, "worktree"))}


@pytest.mark.parametrize("case", sorted(HOOK_CASES))
def test_07p_delta_equals_full_reverse_oracle(tmp_path, case):
    """差量判定（helper 檔：只對完整展開輪廓減少之模組層名稱反推呼叫者；測試檔：模組層共用定義減少才全檔，否則只算
    本體改了之測試函式——審查 r29）之 V19 主體，逐案（helper 檔與測試檔全部 hook 案例）等於完整反推 oracle（暫存倉
    全量逐函式比較）；oracle 只在本測試算，不進產出端。"""
    rel, old, new, expect = HOOK_CASES[case]
    r = _repo(tmp_path, FX_FILES)
    _edit(r, rel, old, new)
    assert _v19_subjects(r.hook(rel).stderr) == _full_oracle(r) == expect


@pytest.mark.parametrize("case", IMPORT_CASES)
def test_07p_import_change_decreased_defs_by_expanded_profile(tmp_path, case):
    """import 改變之差量以名稱之完整展開輪廓判定（不以字面形態挑選、不一律退回完整反推）：引用改變之綁定之定義必在、
    無關定義不在；無關 import ⇒ 空串列（不反推，產出端維持秒級）。"""
    rel, old, new, _ = HOOK_CASES[case]
    must, must_not = IMPORT_DEFS[case]
    r = _repo(tmp_path, FX_FILES)
    _edit(r, rel, old, new)
    got = testreg.decreased_defs(r.root, rel)
    assert got is not None and must <= set(got) and not (must_not & set(got)), got
    if not must:
        assert got == []


@pytest.mark.parametrize("case,name", [("07r_conftest_autouse_turned_off", "env_checked"),
                                       ("07t_plugin_autouse_turned_off", "plug_ready")])
def test_07r_fixture_autouse_flag_in_profile(tmp_path, case, name):
    """fixture 之完整展開輪廓含 decorator 之 autouse 狀態：本體不變而 autouse 關閉 ⇒ 該 fixture 在 decreased_defs 內
    （conftest 與 pytest_plugins 外掛皆然）。"""
    rel, old, new, _ = HOOK_CASES[case]
    r = _repo(tmp_path, FX_FILES)
    _edit(r, rel, old, new)
    assert name in (testreg.decreased_defs(r.root, rel) or [])


def test_07c_helper_change_precommit_red(tmp_path):
    """pre-commit 路徑：helper 刪一個斷言後只暫存該 helper 檔 ⇒ `check --staged` rc≠0 且列出受影響呼叫者（V19）。"""
    r = _repo(tmp_path, FX_FILES)
    r.install_precommit()
    _edit(r, "tests/fixtures/fx_helpers.py", "    assert x < 100\n", "")
    r.stage("tests/fixtures/fx_helpers.py")
    proc = r.try_commit()
    assert proc.returncode != 0 and "tests/test_fx.py::test_uses_helper" in _v19_subjects(proc.stderr), proc.stderr


INI_CASES = {
    # 名稱: (舊行, 新行〔None＝於檔尾加一行標記註冊〕, HEAD 收集而受驗樹不再收集之代表 nodeid〔None＝不得有 V20〕)
    "python_functions_narrowed": ("python_functions = test_*", "python_functions = check_*", "tests/test_keep.py::test_one"),
    "python_classes_narrowed": ("python_classes = Test*", "python_classes = Check*", "tests/test_shapes.py::TestK::test_k"),
    "testpaths_narrowed": ("testpaths = tests", "testpaths = tests/sub", "tests/test_keep.py::test_one"),
    "python_files_narrowed": ("python_files = test_*.py", "python_files = check_*.py", "tests/test_keep.py::test_one"),
    "python_functions_superset_ok": ("python_functions = test_*", "python_functions = test_* check_*", None),
    "marker_added_ok": (None, None, None),
}


@pytest.mark.parametrize("case", sorted(INI_CASES))
def test_07s_pytest_ini_collection_change_hook_and_precommit(tmp_path, case):
    """pytest.ini 之收集設定（testpaths、python_files、python_classes、python_functions 四者任一）縮減致 HEAD 收集之
    測試函式於受驗樹不再被收集 ⇒ hook 與 pre-commit 皆 rc≠0（V20）；模式只增（超集）或非收集設定之改動 ⇒ rc=0。"""
    old, new, gone = INI_CASES[case]
    r = _repo(tmp_path, FX_FILES)
    r.install_precommit()
    ini = r.read("pytest.ini")
    if old is None:
        r.write("pytest.ini", ini + "    extra_marker: e\n")
    else:
        assert ini.count(old + "\n") == 1, ini
        r.write("pytest.ini", ini.replace(old + "\n", new + "\n"))
    proc = r.hook("pytest.ini")
    v20 = [l for l in proc.stderr.splitlines() if l.startswith("V20 ")]
    if gone is None:
        assert proc.returncode == 0 and not v20, proc.stderr
        r.stage("pytest.ini")
        proc = r.try_commit()
        assert proc.returncode == 0 and not any(l.startswith("V20 ") for l in proc.stderr.splitlines()), proc.stderr
        return
    assert proc.returncode == 2 and any(l.startswith(f"V20 {gone}") for l in v20), proc.stderr
    r.stage("pytest.ini")
    proc = r.try_commit()
    assert proc.returncode != 0 and any(l.startswith(f"V20 {gone}") for l in proc.stderr.splitlines()), proc.stderr


def test_mutation_delta_ignores_binding_change_misses_07p(tmp_path, monkeypatch, capsys):
    """mutant：差量只比本體字面、不展開綁定（import 來源改變時回空）⇒ 07p 之 import 來源改變放行。"""
    rel, old, new, _ = HOOK_CASES["07p_helper_import_source_changed"]
    r = _repo(tmp_path, FX_FILES)
    _edit(r, rel, old, new)
    assert testreg.main(["--repo", str(r.root), "check", "--helpers", rel]) != 0
    monkeypatch.setattr(testreg, "decreased_defs", lambda *a, **k: [])
    assert testreg.main(["--repo", str(r.root), "check", "--helpers", rel]) == 0
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


@pytest.fixture(scope="module")
def head_worktree(tmp_path_factory):
    """真實 repo HEAD 之 detached 工作樹（含 catalog；venv 以 symlink 共用），供改動共用 helper 之量測；用畢移除。"""
    wt = tmp_path_factory.mktemp("headwt") / "wt"
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(wt), "HEAD"], check=True,
                   capture_output=True, env=clean_env())
    (wt / "venv").symlink_to(REPO / "venv")
    yield wt
    subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(wt)], capture_output=True,
                   env=clean_env())


def _hook_times_at(root: Path, rel: str) -> list:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(root / rel)}})
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        proc = subprocess.run(["bash", str(root / "scripts/testreg_write_guard.sh")], input=payload, capture_output=True,
                              text=True, env=clean_env(), cwd=str(root))
        times.append(time.perf_counter() - t0)
        assert proc.returncode == 0, proc.stderr
    return times


def _assert_clean(root: Path) -> None:
    """共用之 HEAD 工作樹每案起點：已追蹤檔無改動、暫存區為空、HEAD 未變（量測不得受前案污染；審查 r28）。"""
    st = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                        text=True, check=True, env=clean_env()).stdout
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                          env=clean_env()).stdout.strip()
    main = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                          env=clean_env()).stdout.strip()
    assert st == "" and head == main, (st, head, main)


def _staged_times_at(root: Path, rel: str, runs: int, want_red: bool) -> list:
    """pre-commit 路徑之真實規模計時：暫存 rel 後直接呼叫 pre-commit 所跑之 `testreg.py check --staged`（不提交），
    rc 依 want_red；跑完撤回暫存。"""
    subprocess.run(["git", "-C", str(root), "add", "--", rel], check=True, capture_output=True, env=clean_env())
    times = []
    try:
        for _ in range(runs):
            t0 = time.perf_counter()
            proc = subprocess.run([PY, str(root / "scripts/testreg.py"), "check", "--staged"], capture_output=True,
                                  text=True, env=clean_env(), cwd=str(root))
            times.append(time.perf_counter() - t0)
            assert (proc.returncode != 0) == want_red, proc.stderr[-2000:]
    finally:
        subprocess.run(["git", "-C", str(root), "reset", "-q", "--", rel], check=True, capture_output=True,
                       env=clean_env())
    return times


@pytest.mark.parametrize("edit", ["unchanged", "comment_appended", "fixture_docstring_added", "import_added"])
def test_boundary_05_helper_backprop_wall_clock_median_under_1s(head_worktree, edit):
    """真實規模（HEAD 全部測試檔）：tests/conftest.py 未改／加註解／為一個 fixture 加說明／於最後一個模組層 import
    之後加一行無關 import（皆不減斷言）後觸發 hook，10 次牆鐘中位 < 1 s（實作須以差量判定：只對完整展開輪廓減少之
    名稱反推呼叫者——完整反推實測 245 秒；import 改變不得一律退回完整反推）；同一改動暫存後之 pre-commit
    （`check --staged`）亦 rc 0 且 10 次中位 < 1 s。每案起點斷言共用工作樹乾淨。"""
    _assert_clean(head_worktree)
    p = head_worktree / "tests/conftest.py"
    src = p.read_text(encoding="utf-8")
    if edit == "comment_appended":
        p.write_text(src + "\n# 註解\n", encoding="utf-8")
    elif edit == "import_added":
        tree = ast.parse(src)
        assert "colorsys" not in src
        last = max(n.end_lineno for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)))
        lines = src.splitlines(keepends=True)
        lines.insert(last, "import colorsys  # noqa: F401\n")
        p.write_text("".join(lines), encoding="utf-8")
    elif edit == "fixture_docstring_added":
        tree = ast.parse(src)
        fx = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and any("fixture" in ast.dump(d) for d in n.decorator_list))
        lines = src.splitlines(keepends=True)
        lines.insert(fx.body[0].lineno - 1, ' ' * fx.body[0].col_offset + '"""說明。"""\n')
        p.write_text("".join(lines), encoding="utf-8")
    try:
        times = _hook_times_at(head_worktree, "tests/conftest.py")
        staged = _staged_times_at(head_worktree, "tests/conftest.py", 10, False)
    finally:
        p.write_text(src, encoding="utf-8")
    assert statistics.median(times) < 1.0, times
    assert statistics.median(staged) < 1.0, staged


INI_TIMING = {
    # 名稱: (舊行, 新行〔None＝於檔尾加一行標記註冊〕, 是否必擋)
    "marker_added": (None, None, False),
    "functions_superset": ("python_functions = test_*", "python_functions = test_* check_*", False),
    "functions_narrowed": ("python_functions = test_*", "python_functions = check_*", True),
    "classes_narrowed": ("python_classes = Test*", "python_classes = Check*", True),
    "files_narrowed": ("python_files = test_*.py", "python_files = check_*.py", True),
    "testpaths_narrowed": ("testpaths = tests", "testpaths = tests/registry", True),
}


@pytest.mark.parametrize("edit", sorted(INI_TIMING))
def test_boundary_06_pytest_ini_wall_clock(head_worktree, edit):
    """真實規模 pytest.ini：加標記註冊、python_functions 只增模式（超集，不檢）⇒ rc 0 且 10 次中位 < 1 s；四項收集設定
    任一縮減（必擋：全部測試檔 V20，兩樹以單一批次讀取）⇒ rc 2 且 3 次中位 < 5 s（§C 之必擋例外；試作逐檔讀 HEAD 約 20 秒、
    批次讀取後四項分別約 1.5–2.6 秒——成本為解析全部測試檔以列出消失之 nodeid）；同一改動暫存後之 pre-commit
    （`check --staged`）同一 rc 方向與同一門檻。每案起點斷言共用工作樹乾淨。"""
    _assert_clean(head_worktree)
    old, new, blocking = INI_TIMING[edit]
    p = head_worktree / "pytest.ini"
    src = p.read_text(encoding="utf-8")
    if old is None:
        p.write_text(src + "    extra_marker: e\n", encoding="utf-8")
    else:
        assert src.count(old + "\n") == 1, src
        p.write_text(src.replace(old + "\n", new + "\n"), encoding="utf-8")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(p)}})
    want_rc, runs, limit = (2, 3, 5.0) if blocking else (0, 10, 1.0)
    times = []
    try:
        for _ in range(runs):
            t0 = time.perf_counter()
            proc = subprocess.run(["bash", str(head_worktree / "scripts/testreg_write_guard.sh")], input=payload,
                                  capture_output=True, text=True, env=clean_env(), cwd=str(head_worktree))
            times.append(time.perf_counter() - t0)
            assert proc.returncode == want_rc, proc.stderr[-2000:]
        staged = _staged_times_at(head_worktree, "pytest.ini", runs, blocking)
    finally:
        p.write_text(src, encoding="utf-8")
    assert statistics.median(times) < limit, times
    assert statistics.median(staged) < limit, staged


ROUTE_TIMING = {
    # 名稱: (改動之檔, 附加之尾字串)——皆不減斷言、語意不變；分別走測試檔、catalog（全部 entry 規則）、manifest（V22）路由
    "test_file_comment": ("tests/registry/test_testreg_validate.py", "\n# 註解\n"),
    "catalog_trailing_newline": (CATALOG_REL, "\n"),
    "manifest_trailing_newline": ("docs/manifests/TESTREG.json", "\n"),
}


@pytest.mark.parametrize("edit", sorted(ROUTE_TIMING))
def test_boundary_07_route_wall_clock_hook_and_precommit(head_worktree, edit):
    """真實規模之其餘產出端路由（審查 r29）：測試檔、catalog、manifest 各做一個不減檢查之改動 ⇒ hook 與 pre-commit
    （暫存後直接跑 `check --staged`）皆 rc 0 且各 10 次中位 < 1 s（§C 各自計時）。每案起點斷言共用工作樹乾淨。"""
    _assert_clean(head_worktree)
    rel, tail = ROUTE_TIMING[edit]
    p = head_worktree / rel
    src = p.read_text(encoding="utf-8")
    p.write_text(src + tail, encoding="utf-8")
    try:
        times = _hook_times_at(head_worktree, rel)
        staged = _staged_times_at(head_worktree, rel, 10, False)
    finally:
        p.write_text(src, encoding="utf-8")
    assert statistics.median(times) < 1.0, times
    assert statistics.median(staged) < 1.0, staged


def _pick_helper_decrease(root: Path):
    """真實樹中「模組層非測試、非 fixture 函式含單行 assert，且被本檔測試函式呼叫」之測試檔，取測試函式最多者
    ⇒ (路徑, assert 行號)；最壞規模之測試檔路由差量（模組內共用定義減少）。"""
    files = subprocess.run(["git", "-C", str(root), "ls-files", "tests/test_*.py", "tests/**/test_*.py"],
                           capture_output=True, text=True, check=True).stdout.split()
    best = None
    for rel in files:
        mod = ast.parse((root / rel).read_text(encoding="utf-8"))
        tests = [n for n in mod.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and fnmatch.fnmatchcase(n.name, "test_*")]
        for cls in (n for n in mod.body if isinstance(n, ast.ClassDef) and fnmatch.fnmatchcase(n.name, "Test*")):
            tests += [m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and fnmatch.fnmatchcase(m.name, "test_*")]
        called = {c.func.id for t in tests for c in ast.walk(t) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        for h in mod.body:
            if isinstance(h, ast.FunctionDef) and not h.name.startswith("test") and h.name in called \
                    and not any("fixture" in ast.dump(d) for d in h.decorator_list):
                asserts = [s for s in h.body if isinstance(s, ast.Assert) and s.lineno == s.end_lineno]
                if asserts and (best is None or len(tests) > best[0]):
                    best = (len(tests), rel, asserts[0].lineno)
    assert best is not None
    return best[1], best[2]


def test_boundary_07b_test_file_helper_decrease_wall_clock(head_worktree):
    """真實規模最壞之測試檔路由（審查 r30）：最大之「模組內 helper 有斷言」測試檔刪該 helper 一行斷言（必擋：其呼叫者 V19）
    ⇒ hook rc 2、pre-commit rc≠0，且各 3 次中位 < 5 s（§C 必擋層；試作整檔重算 hook 約 2.7 秒，改只算受影響函式後
    hook 約 0.77 秒、pre-commit 約 0.95 秒）。每案起點斷言共用工作樹乾淨。"""
    _assert_clean(head_worktree)
    rel, line = _pick_helper_decrease(head_worktree)
    p = head_worktree / rel
    src = p.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    del lines[line - 1]
    p.write_text("".join(lines), encoding="utf-8")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(p)}})
    times = []
    try:
        for _ in range(3):
            t0 = time.perf_counter()
            proc = subprocess.run(["bash", str(head_worktree / "scripts/testreg_write_guard.sh")], input=payload,
                                  capture_output=True, text=True, env=clean_env(), cwd=str(head_worktree))
            times.append(time.perf_counter() - t0)
            assert proc.returncode == 2 and "V19 " in proc.stderr, proc.stderr[-2000:]
        staged = _staged_times_at(head_worktree, rel, 3, True)
    finally:
        p.write_text(src, encoding="utf-8")
    assert statistics.median(times) < 5.0, times
    assert statistics.median(staged) < 5.0, staged


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


def _tracked_tests() -> set:
    """全量規模＝真實 repo 現行 tracked 測試檔（不寫死檔數）。"""
    return set(subprocess.run(["git", "-C", str(REPO), "ls-files", "tests/test_*.py", "tests/**/test_*.py"],
                              capture_output=True, text=True, check=True).stdout.split())


def _hook_times(rel: str) -> list:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(REPO / rel)}})
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        proc = subprocess.run(["bash", str(REPO / "scripts/testreg_write_guard.sh")], input=payload, capture_output=True,
                              text=True, env=clean_env(), cwd=str(REPO))
        times.append(time.perf_counter() - t0)
        assert proc.returncode == 0, proc.stderr
    assert _tracked_tests() <= set(json.loads((REPO / CATALOG_REL).read_text(encoding="utf-8"))["entries"])
    return times


@pytest.mark.parametrize("rel", ["tests/registry/test_testreg_validate.py", "docs/manifests/TESTREG.json"])
def test_08_hook_wall_clock_median_under_1s(rel):
    """⑧：真實 repo（全量 entries）未改動之測試檔／manifest 觸發 hook，10 次牆鐘中位 < 1 s（helper 反推見邊界 05）。"""
    assert statistics.median(_hook_times(rel)) < 1.0
