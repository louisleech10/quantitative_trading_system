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
    "07v_body_xfail_call_added": ("tests/test_autouse.py", "def test_b():\n", "def test_b():\n    pytest.xfail(\"r31\")\n",
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




def _full_oracle(r: TmpRepo, fileset: Dict[str, str] = FX_FILES) -> set:
    """完整反推之定義：暫存倉每一測試函式（依暫存倉 pytest.ini 之 python_classes／python_functions 以 fnmatch 收集，
    與真實樹同為 `Test*`／`test_*`；含 async 函式與類別方法；`testhelper` 不收）於 HEAD 與工作樹各自完整展開之
    斷言多重集合比較（不經呼叫者反推）。"""
    ini = configparser.ConfigParser()
    ini.read_string(r.read("pytest.ini"))
    cls_pat, fn_pat = ini["pytest"]["python_classes"], ini["pytest"]["python_functions"]
    files = {p: r.read(p) for p in fileset if is_test_path(p)}
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


PLUG2 = "import pytest\n\n\n@pytest.fixture\ndef plug_extra():\n    assert 1 > 0\n    yield\n"


@pytest.mark.parametrize("new_line,expect", [
    ('pytest_plugins = ["tests.plugins.plug", "tests.plugins.plug2"]\n', []),                  # 追加外掛
    ("pytest_plugins = []\n", ["pytest_plugins"]),                                            # 移除外掛
    ('pytest_plugins = ["tests.plugins.plug2", "tests.plugins.plug"]\n', ["pytest_plugins"]),  # 前插改序（保守判減）
])
def test_07w_conftest_pytest_plugins_profile_is_ordered_plugins(tmp_path, new_line, expect):
    """conftest 之 `pytest_plugins` 輪廓＝依序之外掛元素：外掛於 fixture 解析序最後（不遮蔽既有名稱）⇒ 追加不減、
    不反推呼叫者；移除或改序 ⇒ 減。實作期 b1 實測：追加一個外掛被當成常數減少而走完整呼叫者反推，真實
    tests/conftest.py 之 pre-commit `check --staged` 耗 175 秒。"""
    r = _repo(tmp_path, {**FX_FILES, "tests/plugins/plug2.py": PLUG2})
    _edit(r, "tests/conftest.py", 'pytest_plugins = ["tests.plugins.plug"]\n', new_line)
    assert testreg.decreased_defs(r.root, "tests/conftest.py") == expect
    proc = r.hook("tests/conftest.py")
    assert (proc.returncode != 0) == bool(_full_oracle(r)), proc.stderr
    if not expect:
        assert proc.returncode == 0 and _full_oracle(r) == set()
    if new_line == "pytest_plugins = []\n":  # 移除帶 autouse fixture 之外掛 ⇒ 全部測試之斷言減少
        assert _v19_subjects(proc.stderr) == _full_oracle(r) == ALL_FX_TESTS


# ── ⑦x usefixtures（SPEC v33；b1 審碼 r2 CODEX-R2-P1-01）：fixture 請求含 usefixtures 字面（函式裝飾器、類別裝飾器與
# 類別層 pytestmark〔含基底類別〕、模組層 pytestmark）——經此套用之 fixture 刪斷言或其外掛被移除 ⇒ 該等測試 V19 減少 ──
PLUGREQ = "import pytest\n\n\n@pytest.fixture\ndef plug_req():\n    assert 2 > 1\n    yield\n"
T_USEFX_FN = '''import pytest


@pytest.mark.usefixtures("checked_value")
def test_fn_marked():
    assert 1 == 1


def test_fn_plain():
    assert 2 == 2
'''
T_USEFX_CLS = '''import pytest


@pytest.mark.usefixtures("checked_value")
class TestDecorated:
    def test_cls_decorated(self):
        assert 1 == 1


class TestAttr:
    pytestmark = pytest.mark.usefixtures("checked_value")

    def test_cls_attr(self):
        assert 1 == 1


class TestChild(TestDecorated):
    def test_inherited(self):
        assert 1 == 1


class TestPlain:
    def test_cls_plain(self):
        assert 1 == 1
'''
T_USEFX_MOD = '''import pytest

pytestmark = [pytest.mark.usefixtures("plug_req")]


def test_mod_a():
    assert 1 == 1


def test_mod_b():
    assert 2 == 2
'''
T_USEFX_LOCAL = '''import pytest


@pytest.fixture
def local_ready():
    assert 3 > 2
    assert 4 > 3
    yield


@pytest.mark.usefixtures("local_ready")
def test_local_marked():
    assert 1 == 1


def test_local_plain():
    assert 1 == 1
'''
USEFX_CONFTEST = CONFTEST.replace('pytest_plugins = ["tests.plugins.plug"]',
                                  'pytest_plugins = ["tests.plugins.plug", "tests.plugins.plugreq"]')
USEFX_FILES = {**FX_FILES, "tests/conftest.py": USEFX_CONFTEST, "tests/plugins/plugreq.py": PLUGREQ,
               "tests/test_usefx_fn.py": T_USEFX_FN, "tests/test_usefx_cls.py": T_USEFX_CLS,
               "tests/test_usefx_mod.py": T_USEFX_MOD, "tests/test_usefx_local.py": T_USEFX_LOCAL}
USEFX_TESTS = {n for n in _collected(USEFX_FILES) if "/test_usefx_" in n}
USEFX_CHECKED = {"tests/test_usefx_fn.py::test_fn_marked", "tests/test_usefx_cls.py::TestDecorated::test_cls_decorated",
                 "tests/test_usefx_cls.py::TestAttr::test_cls_attr", "tests/test_usefx_cls.py::TestChild::test_inherited"}


def test_07x_usefixtures_premise():
    """反例前提：USEFX_CONFTEST 確實多列一個外掛；四種 usefixtures 來源之測試皆在 USEFX_TESTS。"""
    assert USEFX_CONFTEST != CONFTEST and "tests.plugins.plugreq" in USEFX_CONFTEST
    assert USEFX_CHECKED < USEFX_TESTS and {"tests/test_usefx_mod.py::test_mod_a",
                                            "tests/test_usefx_local.py::test_local_marked"} < USEFX_TESTS


def test_07x_usefixtures_conftest_fixture_assert_deleted(tmp_path):
    """conftest 之 fixture 刪一個斷言 ⇒ 經函式裝飾器、類別裝飾器、類別層 pytestmark、基底類別裝飾器以 usefixtures 套用
    該 fixture 之測試 hook 與 pre-commit 皆 V19（未套用者不列）。"""
    r = _repo(tmp_path, USEFX_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "")
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX_TESTS == USEFX_CHECKED, proc.stderr
    r.install_precommit()
    r.stage("tests/conftest.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) & USEFX_TESTS == USEFX_CHECKED, pc.stderr


def test_07x_usefixtures_plugin_removed(tmp_path):
    """模組層 pytestmark 以 usefixtures 請求外掛之 fixture，該外掛自 conftest 之 pytest_plugins 移除 ⇒ 該模組全部測試 V19。"""
    r = _repo(tmp_path, USEFX_FILES)
    _edit(r, "tests/conftest.py", 'pytest_plugins = ["tests.plugins.plug", "tests.plugins.plugreq"]',
          'pytest_plugins = ["tests.plugins.plug"]')
    assert testreg.decreased_defs(r.root, "tests/conftest.py") == ["pytest_plugins"]
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX_TESTS == {
        "tests/test_usefx_mod.py::test_mod_a", "tests/test_usefx_mod.py::test_mod_b"}, proc.stderr


def test_07x_usefixtures_module_fixture_assert_deleted(tmp_path):
    """測試模組內之 fixture 經函式裝飾器 usefixtures 請求，刪其一個斷言 ⇒ 寫該測試檔之 hook 只列請求者。"""
    r = _repo(tmp_path, USEFX_FILES)
    _edit(r, "tests/test_usefx_local.py", "    assert 4 > 3\n", "")
    proc = r.hook("tests/test_usefx_local.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) == {"tests/test_usefx_local.py::test_local_marked"}, \
        proc.stderr


def test_07x_usefixtures_no_decrease_rc0(tmp_path):
    """不減之改動（conftest 加註解、fixture 加一個斷言）⇒ rc 0。"""
    r = _repo(tmp_path, USEFX_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "    assert value < 10\n    assert value != 7\n")
    assert r.hook("tests/conftest.py").returncode == 0


# ── ⑦x（v34；審查 r33 CODEX-R33-P1-01／P2-02）：基底類別以模組屬性形式書寫且位於 helper 模組；usefixtures 只認直接標記
# 與 pytest.param(marks=…)（pytest 套用者），巢狀於他標記引數或作為參數值者不計 ──
USEFX_BASE = '''import pytest


@pytest.mark.usefixtures("checked_value")
class Base:
    pass


@pytest.mark.usefixtures("plug_req")
class PlugBase:
    pass
'''
T_USEFX_ATTR = '''import tests.helpers.usefx_base as ub


class TestAttrBase(ub.Base):
    def test_attr_base(self):
        assert 1 == 1


class TestAttrPlug(ub.PlugBase):
    def test_attr_plug(self):
        assert 1 == 1
'''
T_USEFX_NEST = '''import pytest


@pytest.mark.parametrize("x", [pytest.mark.usefixtures("checked_value")])
def test_marker_as_value(x):
    assert x is not None


@pytest.mark.custom_tag(pytest.mark.usefixtures("checked_value"))
def test_marker_as_argument():
    assert 1 == 1


@pytest.mark.parametrize("x", [pytest.param(1, marks=pytest.mark.usefixtures("checked_value")), 2])
def test_param_marks(x):
    assert x > 0
'''
USEFX2_FILES = {**USEFX_FILES, "tests/helpers/usefx_base.py": USEFX_BASE, "tests/test_usefx_attr.py": T_USEFX_ATTR,
                "tests/test_usefx_nest.py": T_USEFX_NEST}
USEFX2_NEW = {n for n in _collected(USEFX2_FILES) if "/test_usefx_attr.py" in n or "/test_usefx_nest.py" in n}


def test_07x_v34_attribute_base_conftest_fixture_assert_deleted(tmp_path):
    """helper 模組之基底類別（子類別以 `別名.類別` 繼承）以 usefixtures 套用 conftest fixture，刪其斷言 ⇒ 子類別測試 V19；
    巢狀標記不計；掛在 pytest.param(marks=…) 之 usefixtures 為 pytest 8.4 收集時拒收之非法寫法（ValueError），不計
    （SPEC v35，審查 r34 GROK-R34-P1-01）。hook 與 pre-commit 同判。"""
    r = _repo(tmp_path, USEFX2_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "")
    want = {"tests/test_usefx_attr.py::TestAttrBase::test_attr_base"}
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX2_NEW == want, proc.stderr
    r.install_precommit()
    r.stage("tests/conftest.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) & USEFX2_NEW == want, pc.stderr


def test_07x_v34_attribute_base_plugin_removed(tmp_path):
    """外掛之 fixture 只經他模組基底類別之 usefixtures 請求（測試檔原文不含該 fixture 名），外掛移除 ⇒ 子類別測試 V19。"""
    r = _repo(tmp_path, USEFX2_FILES)
    assert "plug_req" not in T_USEFX_ATTR
    _edit(r, "tests/conftest.py", 'pytest_plugins = ["tests.plugins.plug", "tests.plugins.plugreq"]',
          'pytest_plugins = ["tests.plugins.plug"]')
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX2_NEW == {
        "tests/test_usefx_attr.py::TestAttrPlug::test_attr_plug"}, proc.stderr


def test_07x_v34_helper_base_marker_removed(tmp_path):
    """helper 模組之基底類別拿掉 usefixtures 標記 ⇒ 寫該 helper 之 hook 列出經其請求 fixture 之子類別測試（hook 與 pre-commit）。"""
    r = _repo(tmp_path, USEFX2_FILES)
    _edit(r, "tests/helpers/usefx_base.py", '@pytest.mark.usefixtures("checked_value")\nclass Base:', "class Base:")
    proc = r.hook("tests/helpers/usefx_base.py")
    want = {"tests/test_usefx_attr.py::TestAttrBase::test_attr_base"}
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) == want, proc.stderr
    r.install_precommit()
    r.stage("tests/helpers/usefx_base.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) == want, pc.stderr


def test_07x_v34_test_class_marker_removed(tmp_path):
    """測試檔內類別拿掉 usefixtures 裝飾器 ⇒ 該類別與同檔子類別之測試 V19，他類別不列。"""
    r = _repo(tmp_path, USEFX2_FILES)
    _edit(r, "tests/test_usefx_cls.py", '@pytest.mark.usefixtures("checked_value")\nclass TestDecorated:',
          "class TestDecorated:")
    proc = r.hook("tests/test_usefx_cls.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) == {
        "tests/test_usefx_cls.py::TestDecorated::test_cls_decorated",
        "tests/test_usefx_cls.py::TestChild::test_inherited"}, proc.stderr


# ── ⑦x（v35；審查 r34 CODEX-R34-P1-01／P1-02）：基底類別以套件內相對匯入、或匯入後改名（別名）繼承 ──
T_USEFX_REL = '''from .helpers.usefx_base import Base, PlugBase


class TestRelBase(Base):
    def test_rel_base(self):
        assert 1 == 1


class TestRelPlug(PlugBase):
    def test_rel_plug(self):
        assert 1 == 1
'''
T_USEFX_ALIAS = '''from tests.helpers.usefx_base import Base as B, PlugBase as PB


class TestAliasBase(B):
    def test_alias_base(self):
        assert 1 == 1


class TestAliasPlug(PB):
    def test_alias_plug(self):
        assert 1 == 1
'''
USEFX3_FILES = {**USEFX2_FILES, "tests/test_usefx_rel.py": T_USEFX_REL, "tests/test_usefx_alias.py": T_USEFX_ALIAS}
USEFX3_NEW = {n for n in _collected(USEFX3_FILES) if "/test_usefx_rel.py" in n or "/test_usefx_alias.py" in n}


def test_07x_v35_premise():
    """反例前提：相對匯入與別名繼承之測試檔原文不含 fixture 名；兩檔各兩個測試。"""
    assert "checked_value" not in T_USEFX_REL + T_USEFX_ALIAS and "plug_req" not in T_USEFX_REL + T_USEFX_ALIAS
    assert len(USEFX3_NEW) == 4


def test_07x_v35_relative_and_alias_base_conftest_fixture_assert_deleted(tmp_path):
    """conftest fixture 刪斷言 ⇒ 經相對匯入或別名繼承之基底以 usefixtures 套用該 fixture 之測試 V19（hook 與 pre-commit）。"""
    r = _repo(tmp_path, USEFX3_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "")
    want = {"tests/test_usefx_rel.py::TestRelBase::test_rel_base", "tests/test_usefx_alias.py::TestAliasBase::test_alias_base"}
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX3_NEW == want, proc.stderr
    r.install_precommit()
    r.stage("tests/conftest.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) & USEFX3_NEW == want, pc.stderr


def test_07x_v35_relative_and_alias_base_plugin_removed(tmp_path):
    """外掛移除 ⇒ 經相對匯入或別名繼承之基底以 usefixtures 請求其 fixture 之測試 V19。"""
    r = _repo(tmp_path, USEFX3_FILES)
    _edit(r, "tests/conftest.py", 'pytest_plugins = ["tests.plugins.plug", "tests.plugins.plugreq"]',
          'pytest_plugins = ["tests.plugins.plug"]')
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX3_NEW == {
        "tests/test_usefx_rel.py::TestRelPlug::test_rel_plug",
        "tests/test_usefx_alias.py::TestAliasPlug::test_alias_plug"}, proc.stderr


def test_07x_v35_helper_base_marker_removed_relative_and_alias(tmp_path):
    """helper 基底類別拿掉 usefixtures ⇒ 經相對匯入或別名繼承之子類別測試亦列出（hook）。"""
    r = _repo(tmp_path, USEFX3_FILES)
    _edit(r, "tests/helpers/usefx_base.py", '@pytest.mark.usefixtures("checked_value")\nclass Base:', "class Base:")
    proc = r.hook("tests/helpers/usefx_base.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX3_NEW == {
        "tests/test_usefx_rel.py::TestRelBase::test_rel_base",
        "tests/test_usefx_alias.py::TestAliasBase::test_alias_base"}, proc.stderr


# ── ⑦x（v36；審查 r35 CODEX-R35-P1-02）：基底類別經星號匯入取得 ──
T_USEFX_STAR = '''from tests.helpers.usefx_base import *


class TestStarBase(Base):
    def test_star_base(self):
        assert 1 == 1


class TestStarPlug(PlugBase):
    def test_star_plug(self):
        assert 1 == 1
'''
USEFX4_FILES = {**USEFX2_FILES, "tests/test_usefx_star.py": T_USEFX_STAR}
USEFX4_NEW = {n for n in _collected(USEFX4_FILES) if "/test_usefx_star.py" in n}


def test_07x_v36_star_import_base_three_paths(tmp_path):
    """星號匯入之基底類別以 usefixtures 請求 fixture：conftest fixture 刪斷言、外掛移除、helper 基底拿掉標記三路徑
    皆列出對應子類別測試（hook；conftest 案另驗 pre-commit）。"""
    assert len(USEFX4_NEW) == 2 and "checked_value" not in T_USEFX_STAR
    r = _repo(tmp_path, USEFX4_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "")
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX4_NEW == {
        "tests/test_usefx_star.py::TestStarBase::test_star_base"}, proc.stderr
    r.install_precommit()
    r.stage("tests/conftest.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) & USEFX4_NEW == {
        "tests/test_usefx_star.py::TestStarBase::test_star_base"}, pc.stderr
    r2 = _repo(tmp_path / "plug", USEFX4_FILES)
    _edit(r2, "tests/conftest.py", 'pytest_plugins = ["tests.plugins.plug", "tests.plugins.plugreq"]',
          'pytest_plugins = ["tests.plugins.plug"]')
    p2 = r2.hook("tests/conftest.py")
    assert p2.returncode != 0 and _v19_subjects(p2.stderr) & USEFX4_NEW == {
        "tests/test_usefx_star.py::TestStarPlug::test_star_plug"}, p2.stderr
    r3 = _repo(tmp_path / "helper", USEFX4_FILES)
    _edit(r3, "tests/helpers/usefx_base.py", '@pytest.mark.usefixtures("checked_value")\nclass Base:', "class Base:")
    p3 = r3.hook("tests/helpers/usefx_base.py")
    assert p3.returncode != 0 and _v19_subjects(p3.stderr) & USEFX4_NEW == {
        "tests/test_usefx_star.py::TestStarBase::test_star_base"}, p3.stderr


# ── ⑦x（v37；審查 r36 CODEX-R36-P1-01）：兩星號來源匯出同名基底，Python 以後出現者為準 ──
USEFX_PLAIN = "class Base:\n    pass\n"
T_USEFX_ORDER = '''from tests.helpers.usefx_base import *
from tests.helpers.usefx_plain import *


class TestOverride(Base):
    def test_override(self):
        assert 1 == 1
'''
T_USEFX_ORDER2 = '''from tests.helpers.usefx_plain import *
from tests.helpers.usefx_base import *


class TestOverride2(Base):
    def test_override2(self):
        assert 1 == 1
'''
USEFX5_FILES = {**USEFX2_FILES, "tests/helpers/usefx_plain.py": USEFX_PLAIN, "tests/test_usefx_order.py": T_USEFX_ORDER,
                "tests/test_usefx_order2.py": T_USEFX_ORDER2}
USEFX5_NEW = {n for n in _collected(USEFX5_FILES) if "/test_usefx_order" in n}


def test_07x_v37_star_import_later_source_wins(tmp_path):
    """後出現之星號來源覆蓋同名基底：基底為無 usefixtures 者（TestOverride）不列、為有 usefixtures 者（TestOverride2）
    列出——conftest fixture 刪斷言時 hook 與 pre-commit 同判（取第一個來源之實作兩案皆錯）。"""
    assert len(USEFX5_NEW) == 2
    r = _repo(tmp_path, USEFX5_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "")
    want = {"tests/test_usefx_order2.py::TestOverride2::test_override2"}
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX5_NEW == want, proc.stderr
    r.install_precommit()
    r.stage("tests/conftest.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) & USEFX5_NEW == want, pc.stderr


# ── ⑦x（v38；審查 r37 CODEX-R37-P1-01）：同模組同名基底重定義，子類別取建立當時之基底 ──
T_USEFX_SHADOW = '''import pytest


@pytest.mark.usefixtures("checked_value")
class Base:
    pass


class TestBefore(Base):
    def test_before(self):
        assert 1 == 1


class Base:
    pass


class TestAfter(Base):
    def test_after(self):
        assert 1 == 1
'''
USEFX6_FILES = {**USEFX2_FILES, "tests/test_usefx_shadow.py": T_USEFX_SHADOW}
USEFX6_NEW = {n for n in _collected(USEFX6_FILES) if "/test_usefx_shadow.py" in n}


def test_07x_v38_shadowed_base_binding_time(tmp_path):
    """同名基底重定義：重定義前建立之子類別（TestBefore）經帶 usefixtures 之前者請求 fixture，之後者（TestAfter）不請求——
    conftest fixture 刪斷言時只列 TestBefore（hook 與 pre-commit 同判；依名取最後定義之實作漏列）。"""
    assert len(USEFX6_NEW) == 2
    r = _repo(tmp_path, USEFX6_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "")
    want = {"tests/test_usefx_shadow.py::TestBefore::test_before"}
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX6_NEW == want, proc.stderr
    r.install_precommit()
    r.stage("tests/conftest.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) & USEFX6_NEW == want, pc.stderr


# ── ⑦x（v39；審查 r38 CODEX-R38-P1-01／P1-02）：模組別名於類別建立後重綁；改前一個同名基底之標記 ──
T_USEFX_REALIAS = '''import tests.helpers.usefx_base as h


class TestAliasBefore(h.Base):
    def test_alias_before(self):
        assert 1 == 1


import tests.helpers.usefx_plain as h
'''
USEFX7_FILES = {**USEFX2_FILES, "tests/helpers/usefx_plain.py": USEFX_PLAIN, "tests/test_usefx_realias.py": T_USEFX_REALIAS,
                "tests/test_usefx_shadow.py": T_USEFX_SHADOW}
USEFX7_NEW = {n for n in _collected(USEFX7_FILES) if "/test_usefx_realias.py" in n or "/test_usefx_shadow.py" in n}


def test_07x_v39_module_alias_rebound_after_class(tmp_path):
    """模組別名於類別建立後重綁至他模組：子類別之基底為建立時別名所指者（帶 usefixtures）——conftest fixture 刪斷言時列出
    TestAliasBefore（hook 與 pre-commit；以模組最終別名解析之實作漏列）。"""
    r = _repo(tmp_path, USEFX7_FILES)
    _edit(r, "tests/conftest.py", "    assert value < 10\n", "")
    want = {"tests/test_usefx_realias.py::TestAliasBefore::test_alias_before",
            "tests/test_usefx_shadow.py::TestBefore::test_before"}
    proc = r.hook("tests/conftest.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) & USEFX7_NEW == want, proc.stderr
    r.install_precommit()
    r.stage("tests/conftest.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) & USEFX7_NEW == want, pc.stderr


def test_07x_v39_earlier_same_name_base_marker_removed(tmp_path):
    """同名基底重定義時，拿掉前一個 Base 之 usefixtures（後一個不變）⇒ 寫該測試檔之 hook 與 pre-commit 列出重定義前建立之
    子類別 TestBefore（差量輪廓只看最後一個定義之實作漏列）。"""
    r = _repo(tmp_path, USEFX7_FILES)
    _edit(r, "tests/test_usefx_shadow.py", '@pytest.mark.usefixtures("checked_value")\nclass Base:', "class Base:")
    want = {"tests/test_usefx_shadow.py::TestBefore::test_before"}
    proc = r.hook("tests/test_usefx_shadow.py")
    assert proc.returncode != 0 and _v19_subjects(proc.stderr) == want, proc.stderr
    r.install_precommit()
    r.stage("tests/test_usefx_shadow.py")
    pc = r.try_commit()
    assert pc.returncode != 0 and _v19_subjects(pc.stderr) == want, pc.stderr


# ── ⑦y（第 1 批審碼 r3 CODEX-R3-P1-01／COMPOSER-R3-P1-01）：`pytest_plugins` 外掛模組內 fixture 輪廓減少，依列它之 conftest
# 作用範圍之 fixture 請求關係判定（不做完整呼叫者反推：真實規模 157 秒）——須與完整反推 oracle 相等 ──
PLUGDEP = ("import pytest\n\n\n@pytest.fixture\ndef plug_req():\n    assert 2 > 1\n    yield\n\n\n"
           "@pytest.fixture\ndef plug_wrap(plug_req):\n    yield\n")
PLUGBASE = 'import pytest\n\n\n@pytest.mark.usefixtures("plug_wrap")\nclass PlugBase:\n    pass\n'
# 只經他模組別名基底類別請求者獨立一檔：該檔原文不含任何 fixture 名（文字預篩須納入遞移之類別名才不漏）
T_PLUG_VIABASE = '''from tests.helpers.plugbase import PlugBase as PB


class TestViaBase(PB):
    def test_via_base(self):
        assert 1 == 1
'''
T_PLUG_USERS = '''def test_param(plug_req):
    assert 1 == 1


def test_plain():
    assert 1 == 1
'''
T_PLUG_LOCALAUTO = '''import pytest


@pytest.fixture(autouse=True)
def local_guard(plug_req):
    yield


def test_la():
    assert 1 == 1
'''
PLUGDEP_FILES = {**USEFX_FILES, "tests/plugins/plugreq.py": PLUGDEP, "tests/helpers/plugbase.py": PLUGBASE,
                 "tests/test_plug_viabase.py": T_PLUG_VIABASE, "tests/test_plug_users.py": T_PLUG_USERS,
                 "tests/test_plug_localauto.py": T_PLUG_LOCALAUTO}
PLUGDEP_WANT = {"tests/test_usefx_mod.py::test_mod_a", "tests/test_usefx_mod.py::test_mod_b",
                "tests/test_plug_viabase.py::TestViaBase::test_via_base", "tests/test_plug_users.py::test_param",
                "tests/test_plug_localauto.py::test_la"}


@pytest.mark.parametrize("old,new,want", [
    ("    assert 2 > 1\n", "", PLUGDEP_WANT),                                 # 外掛 fixture 刪斷言
    ("    assert 2 > 1\n", "    assert 2 > 1\n    assert 3 > 2\n", set()),   # 加斷言：不減
    ("    yield\n\n\n@pytest", "    yield\n\n\n# 註解\n@pytest", set()),      # 加註解：不減
])
def test_07y_plugin_fixture_change_equals_full_oracle(tmp_path, old, new, want):
    """外掛模組內 fixture 刪一個斷言 ⇒ 經參數、模組層 pytestmark、他模組別名基底類別之 usefixtures（經外掛內遞移 fixture）、
    測試模組內 autouse fixture 請求者，hook 與 pre-commit 之 V19 主體皆等於完整反推 oracle；不減之改動 rc 0。"""
    r = _repo(tmp_path, PLUGDEP_FILES)
    _edit(r, "tests/plugins/plugreq.py", old, new)
    proc = r.hook("tests/plugins/plugreq.py")
    assert (proc.returncode != 0) == bool(want), proc.stderr
    assert _v19_subjects(proc.stderr) == _full_oracle(r, PLUGDEP_FILES) == want, proc.stderr
    r.install_precommit()
    r.stage("tests/plugins/plugreq.py")
    pc = r.try_commit()
    assert (pc.returncode != 0) == bool(want) and _v19_subjects(pc.stderr) == want, pc.stderr


# ── ⑦z（第 1 批審碼 r3 後主委實測：autouse fixture 刪斷言時候選為範圍內全部測試，逐一展開比較真實規模 120 秒）：fixture
# 改變之免展開判定（`_fixture_change_decide`）——前提成立者不逐一展開、不成立者逐一精確比較，兩者皆須與完整反推 oracle 相等 ──
PLUGAUTO = '''import pytest


@pytest.fixture
def auto_dep():
    yield 5


@pytest.fixture(autouse=True)
def auto_guard(auto_dep):
    value = auto_dep
    assert value > 0
    assert value < 10
    yield


@pytest.fixture(autouse=True)
def auto_quiet():
    yield


@pytest.fixture
def ord_r():
    r = list(range(2))
    assert len(r) > 0
    yield


@pytest.fixture
def ord_q():
    q = list(range(3))
    assert len(q) > 1
    yield


@pytest.fixture(autouse=True)
def aa_lost(ord_r):
    yield


@pytest.fixture(autouse=True)
def ab_keep(ord_q, ord_r):
    yield


@pytest.fixture
def sub_only():
    s = list(range(4))
    assert len(s) > 2
    yield
'''
T_AUTO_SUB = "def test_sub_only(sub_only):\n    assert True\n"
# 同名 fixture 遮蔽：以名稱入選候選，但閉包中 sub_only 解析至本模組（非外掛）
T_AUTO_SHADOW = ("import pytest\n\n\n@pytest.fixture\ndef sub_only():\n    yield\n\n\n"
                 "def test_shadowed(sub_only):\n    assert True\n")
AUTO_FILES = {**USEFX_FILES, "tests/plugins/plugauto.py": PLUGAUTO, "tests/test_auto_sub.py": T_AUTO_SUB,
              "tests/test_auto_shadow.py": T_AUTO_SHADOW,
              "tests/conftest.py": USEFX_CONFTEST.replace('"tests.plugins.plugreq"]',
                                                          '"tests.plugins.plugreq", "tests.plugins.plugauto"]')}
AUTO_ALL = set(_collected(AUTO_FILES))
ORDER_WANT = None  # 以完整反推 oracle 為準（局部名序號重排使部分測試舊鍵計數減少，視各測試其他局部名之並列而定）
AUTO_CASES = {
    # 名稱: ([(檔, 舊, 新)…], 預期 V19 主體, 是否走免展開判定〔不逐一展開〕)
    "assert_removed": ([("tests/plugins/plugauto.py", "    assert value < 10\n", "")], AUTO_ALL, True),
    "assert_weakened": ([("tests/plugins/plugauto.py", "    assert value < 10\n", "    assert value <= 10\n")],
                        AUTO_ALL, True),
    "assert_added": ([("tests/plugins/plugauto.py", "    assert value < 10\n",
                       "    assert value < 10\n    assert value != 7\n")], set(), True),
    "elementless_autouse_off": ([("tests/plugins/plugauto.py", "@pytest.fixture(autouse=True)\ndef auto_quiet",
                                  "@pytest.fixture\ndef auto_quiet")], set(), True),
    "asserting_autouse_off": ([("tests/plugins/plugauto.py", "@pytest.fixture(autouse=True)\ndef auto_guard",
                                "@pytest.fixture\ndef auto_guard")], AUTO_ALL, True),
    # 關閉無元素之 aa_lost 之 autouse：留下之 ord_r 改經 ab_keep 進入、展開順序與 ord_q 對調（同位置同序號之局部名改依出現序
    # 排序）⇒ 須交逐一精確比較（不得以「失去者皆無元素」逕判不減）
    "order_changed_elementless_off": ([("tests/plugins/plugauto.py", "@pytest.fixture(autouse=True)\ndef aa_lost",
                                        "@pytest.fixture\ndef aa_lost")], ORDER_WANT, False),
    # sub_only 刪斷言（減少）＋autouse 之 auto_guard 加斷言（增加）：test_sub_only 閉包含兩個改變者 ⇒ 精確比較、必減；
    # test_shadowed 之 sub_only 為本模組者、閉包中改變者只 auto_guard 且未減少 ⇒ 免展開判不減
    "mixed_shadowed": ([("tests/plugins/plugauto.py", "    assert len(s) > 2\n", ""),
                        ("tests/plugins/plugauto.py", "    assert value < 10\n",
                         "    assert value < 10\n    assert value != 7\n")],
                       {"tests/test_auto_sub.py::test_sub_only"}, False),
    "signature_changed": ([("tests/plugins/plugauto.py", "def auto_guard(auto_dep):",
                            "def auto_guard(auto_dep, request):"),
                           ("tests/plugins/plugauto.py", "    assert value < 10\n", "")], AUTO_ALL, False),
    "two_fixtures_changed": ([("tests/plugins/plugauto.py", "    assert value < 10\n", ""),
                              ("tests/plugins/plugauto.py", "    yield 5\n", "    assert 5 > 4\n    yield 5\n")],
                             AUTO_ALL, False),
    # 另一個 conftest 亦變更（conftest 不以模組名被引用，只能由「除 h 外變更之 tests/ 下 .py 皆為測試檔」閘擋下）
    "other_conftest_dirty": ([("tests/plugins/plugauto.py", "    assert value < 10\n", ""),
                              ("tests/sub/conftest.py", 'check_env("x")', 'check_env("xy")')], AUTO_ALL, False),
    "other_helper_dirty": ([("tests/plugins/plugauto.py", "    assert value < 10\n", ""),
                            ("tests/helpers/plughelp.py", "    assert v > 0\n", "    assert v > 0  # 註\n")],
                           AUTO_ALL, False),
}


@pytest.mark.parametrize("case", sorted(AUTO_CASES))
def test_07z_autouse_fixture_change_decision_equals_full_oracle(tmp_path, monkeypatch, case):
    """autouse 外掛 fixture 之改法：刪斷言、換弱斷言、加斷言、關閉無元素／有元素 fixture 之 autouse（前提成立 ⇒ 免展開判定）；
    改簽章、閉包內兩個 fixture 同改、另有 helper 檔變更（前提不成立 ⇒ 逐一精確比較）——hook 與 pre-commit 之 V19 主體皆等於
    完整反推 oracle 與預期；行程內以 `_Engine.elements` 呼叫數驗證走哪一條（免展開判定者為 0）。"""
    edits, want, fast = AUTO_CASES[case]
    r = _repo(tmp_path, AUTO_FILES)
    for rel, old, new in edits:
        _edit(r, rel, old, new)
    if want is None:
        want = _full_oracle(r, AUTO_FILES)
        assert want, "前提：序號重排須使至少一個測試減少（省略展開順序檢查而逕判不減之實作因此必紅）"
    calls = []
    orig = testreg._Engine.elements
    monkeypatch.setattr(testreg._Engine, "elements", lambda self, nid: calls.append(nid) or orig(self, nid))
    got = {f.subject for f in testreg.check(r.root, helpers=["tests/plugins/plugauto.py"]) if f.rule == "V19"}
    monkeypatch.undo()
    assert got == want and (not calls) == fast, (sorted(got ^ want)[:5], len(calls))
    proc = r.hook("tests/plugins/plugauto.py")
    assert (proc.returncode != 0) == bool(want), proc.stderr
    assert _v19_subjects(proc.stderr) == _full_oracle(r, AUTO_FILES) == want, proc.stderr
    r.install_precommit()
    for rel in sorted({e[0] for e in edits}):
        r.stage(rel)
    pc = r.try_commit()
    assert (pc.returncode != 0) == bool(want) and _v19_subjects(pc.stderr) == want, pc.stderr


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


@pytest.mark.parametrize("edit", ["plugin_removed", "plugins_reordered"])
def test_boundary_07c_conftest_pytest_plugins_change_wall_clock(head_worktree, edit):
    """真實規模（審碼 r1 CODEX-R1-P1-02）：tests/conftest.py 之 `pytest_plugins` 移除首個外掛／前後對調 ⇒ hook 與 pre-commit
    同一 rc 方向；不擋（rc 0）者 10 次中位 < 1 s，必擋者 3 次中位 < 5 s（§C 兩層）。實作不得對外掛做完整呼叫者反推
    （真實規模分鐘級）。每案起點斷言共用工作樹乾淨。"""
    _assert_clean(head_worktree)
    p = head_worktree / "tests/conftest.py"
    src = p.read_text(encoding="utf-8")
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in n.targets))
    plugins = [e.value for e in node.value.elts]
    assert len(plugins) >= 2, plugins
    new = plugins[1:] if edit == "plugin_removed" else [plugins[1], plugins[0], *plugins[2:]]
    lines = src.splitlines(keepends=True)
    lines[node.lineno - 1:node.end_lineno] = [f"pytest_plugins = {json.dumps(new)}\n"]
    p.write_text("".join(lines), encoding="utf-8")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(p)}})
    try:
        first = subprocess.run(["bash", str(head_worktree / "scripts/testreg_write_guard.sh")], input=payload,
                               capture_output=True, text=True, env=clean_env(), cwd=str(head_worktree))
        assert first.returncode in (0, 2), first.stderr
        blocking = first.returncode == 2
        runs = 3 if blocking else 10
        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            proc = subprocess.run(["bash", str(head_worktree / "scripts/testreg_write_guard.sh")], input=payload,
                                  capture_output=True, text=True, env=clean_env(), cwd=str(head_worktree))
            times.append(time.perf_counter() - t0)
            assert proc.returncode == first.returncode, proc.stderr
        staged = _staged_times_at(head_worktree, "tests/conftest.py", runs, blocking)
    finally:
        p.write_text(src, encoding="utf-8")
    limit = 5.0 if blocking else 1.0
    assert statistics.median(times) < limit, (edit, blocking, times)
    assert statistics.median(staged) < limit, (edit, blocking, staged)
    if edit == "plugin_removed":  # SPEC v33：經 usefixtures 套用被移除外掛之含斷言 fixture 之真實測試須全數被擋
        expected = _usefixtures_users(head_worktree, _asserting_fixtures(head_worktree, plugins[0]))
        assert expected, "前提：被移除之外掛須有經 usefixtures 套用之含斷言 fixture（真實樹 ic_persist_redirect）"
        assert blocking and expected <= _v19_subjects(first.stderr), sorted(expected - _v19_subjects(first.stderr))[:5]


def test_boundary_07d_test_file_class_base_change_wall_clock(head_worktree):
    """真實規模（v34）：測試檔內一個帶基底之非測試類別改以 object 為基底（類別輪廓減少 ⇒ 全檔比較＋子類別文字預篩，
    不做完整呼叫者反推——實測完整反推 41 秒）⇒ hook 與 pre-commit 同一 rc 方向；不擋者 10 次中位 < 1 s、必擋者 3 次中位
    < 5 s。標的由 AST 自 HEAD 測試檔導出（字典序第一個），不寫死。"""
    _assert_clean(head_worktree)
    rels = subprocess.run(["git", "-C", str(head_worktree), "ls-files", "tests/test_*.py", "tests/**/test_*.py"],
                          capture_output=True, text=True, check=True).stdout.split()
    pick = None
    for rel in sorted(rels):
        src = (head_worktree / rel).read_text(encoding="utf-8")
        for n in ast.parse(src).body:
            if isinstance(n, ast.ClassDef) and not n.name.startswith("Test") and len(n.bases) == 1 \
                    and isinstance(n.bases[0], ast.Name) and n.bases[0].id != "object":
                line = src.splitlines()[n.lineno - 1]
                if line.startswith(f"class {n.name}({n.bases[0].id}):"):
                    pick = (rel, line, f"class {n.name}(object):")
                    break
        if pick:
            break
    assert pick, "前提：HEAD 測試檔中有帶單一名稱基底之非測試類別"
    rel, old, new = pick
    p = head_worktree / rel
    src = p.read_text(encoding="utf-8")
    p.write_text(src.replace(old, new, 1), encoding="utf-8")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(p)}})
    try:
        first = subprocess.run(["bash", str(head_worktree / "scripts/testreg_write_guard.sh")], input=payload,
                               capture_output=True, text=True, env=clean_env(), cwd=str(head_worktree))
        assert first.returncode in (0, 2), first.stderr
        blocking = first.returncode == 2
        runs = 3 if blocking else 10
        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            proc = subprocess.run(["bash", str(head_worktree / "scripts/testreg_write_guard.sh")], input=payload,
                                  capture_output=True, text=True, env=clean_env(), cwd=str(head_worktree))
            times.append(time.perf_counter() - t0)
            assert proc.returncode == first.returncode, proc.stderr
        staged = _staged_times_at(head_worktree, rel, runs, blocking)
    finally:
        p.write_text(src, encoding="utf-8")
    limit = 5.0 if blocking else 1.0
    assert statistics.median(times) < limit, (rel, blocking, times)
    assert statistics.median(staged) < limit, (rel, blocking, staged)


def _plugin_assert_line(root: Path):
    """真實樹 tests/conftest.py 之 `pytest_plugins` 中，第一個含「本體直接含斷言之 fixture」之外掛 ⇒ (外掛路徑, fixture 名,
    該 fixture 本體內第一個單行斷言敘述〔assert 或 assert* 呼叫〕之行號)；標的由 AST 導出，不寫死。"""
    src = (root / "tests/conftest.py").read_text(encoding="utf-8")
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in n.targets))
    for dotted in (e.value for e in node.value.elts):
        names = _asserting_fixtures(root, dotted)
        rel = dotted.replace(".", "/") + ".py"
        for n in ast.parse((root / rel).read_text(encoding="utf-8")).body:
            if isinstance(n, ast.FunctionDef) and n.name in names:
                for s in ast.walk(n):
                    if (isinstance(s, ast.Assert) or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                                                      and getattr(s.value.func, "id", getattr(s.value.func, "attr", ""))
                                                      .startswith("assert"))) and s.lineno == s.end_lineno:
                        return rel, n.name, s.lineno
    return None


@pytest.mark.parametrize("edit", ["assert_removed", "comment_added"])
def test_boundary_07e_plugin_fixture_change_wall_clock(head_worktree, edit):
    """真實規模（第 1 批審碼 r3 CODEX-R3-P1-01／COMPOSER-R3-P1-01）：`pytest_plugins` 外掛內 fixture 刪一行斷言（必擋：經
    usefixtures 套用之真實測試全數 V19）⇒ hook rc 2、pre-commit rc≠0，各 3 次中位 < 5 s；同處加一行註解（不減）⇒ 皆 rc 0、
    各 10 次中位 < 1 s（§C 兩層）。實作不得對外掛做完整呼叫者反推（v39 實測 157–176 秒）。每案起點斷言共用工作樹乾淨。"""
    _assert_clean(head_worktree)
    pick = _plugin_assert_line(head_worktree)
    assert pick, "前提：tests/conftest.py 之外掛中有本體含斷言之 fixture（真實樹 ic_persist_redirect）"
    rel, name, line = pick
    p = head_worktree / rel
    src = p.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    if edit == "assert_removed":
        del lines[line - 1]
    else:
        lines.insert(line - 1, " " * (len(lines[line - 1]) - len(lines[line - 1].lstrip())) + "# 註解\n")
    p.write_text("".join(lines), encoding="utf-8")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(p)}})
    blocking = edit == "assert_removed"
    runs, limit = (3, 5.0) if blocking else (10, 1.0)
    times, first = [], None
    try:
        for _ in range(runs):
            t0 = time.perf_counter()
            proc = subprocess.run(["bash", str(head_worktree / "scripts/testreg_write_guard.sh")], input=payload,
                                  capture_output=True, text=True, env=clean_env(), cwd=str(head_worktree))
            times.append(time.perf_counter() - t0)
            assert proc.returncode == (2 if blocking else 0), proc.stderr[-2000:]
            first = first or proc
        staged = _staged_times_at(head_worktree, rel, runs, blocking)
    finally:
        p.write_text(src, encoding="utf-8")
    assert statistics.median(times) < limit, (edit, times)
    assert statistics.median(staged) < limit, (edit, staged)
    if blocking:  # 獨立字面 oracle：以 usefixtures 字面請求該 fixture 之真實測試須全數被擋
        expected = _usefixtures_users(head_worktree, {name})
        assert expected and expected <= _v19_subjects(first.stderr), sorted(expected - _v19_subjects(first.stderr))[:5]


AUTOUSE_PROBE = ("import pytest\n\n\n@pytest.fixture(autouse=True)\ndef zz_probe_guard():\n"
                 "    assert 1 + 1 == 2\n    assert 2 + 2 == 4\n    yield\n")
AUTOUSE_EDITS = {
    # 名稱: (舊, 新, 是否必擋)
    "assert_removed": ("    assert 2 + 2 == 4\n", "", True),
    "assert_weakened": ("    assert 2 + 2 == 4\n", "    assert 2 + 2 >= 4\n", True),
    "assert_added": ("    assert 2 + 2 == 4\n", "    assert 2 + 2 == 4\n    assert 3 + 3 == 6\n", False),
}


def _collected_real(root: Path) -> set:
    """獨立 oracle（不經 testreg）：依 pytest.ini 之 testpaths／python_files／python_classes／python_functions 以 fnmatch
    收集真實樹之函式層 nodeid（模組層函式含 async、類別內方法）。"""
    ini = configparser.ConfigParser()
    ini.read_string((root / "pytest.ini").read_text(encoding="utf-8"))
    sec = ini["pytest"]
    tps = sec.get("testpaths", "").split() or ["."]
    fpat, cpat = sec.get("python_functions", "test").split(), sec.get("python_classes", "Test").split()
    filepat = sec.get("python_files", "test_*.py").split()
    match = lambda name, pats: any(fnmatch.fnmatchcase(name, p) if any(c in p for c in "*?[") else name.startswith(p)
                                   for p in pats)
    rels = subprocess.run(["git", "-C", str(root), "ls-files", "--", *tps], capture_output=True, text=True,
                          check=True).stdout.split()
    files = {rel: (root / rel).read_text(encoding="utf-8") for rel in rels
             if rel.endswith(".py") and any(fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1], p) for p in filepat)}
    out = set()
    fn = (ast.FunctionDef, ast.AsyncFunctionDef)
    for rel, src in files.items():
        for n in ast.parse(src).body:
            if isinstance(n, fn) and match(n.name, fpat):
                out.add(f"{rel}::{n.name}")
            elif isinstance(n, ast.ClassDef) and match(n.name, cpat):
                out |= {f"{rel}::{n.name}::{m.name}" for m in n.body if isinstance(m, fn) and match(m.name, fpat)}
    return out


@pytest.fixture(scope="module")
def autouse_worktree(tmp_path_factory):
    """真實 repo HEAD 加一個合成提交（不入任何分支）之 detached 工作樹：新增外掛 tests/fixtures/zz_probe_autouse_plugin.py
    （帶兩行斷言之 autouse fixture）並列於 tests/conftest.py 之 `pytest_plugins` 末尾；用畢移除。"""
    wt = tmp_path_factory.mktemp("autowt") / "wt"
    env = clean_env()
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(wt), "HEAD"], check=True,
                   capture_output=True, env=env)
    (wt / "venv").symlink_to(REPO / "venv")
    conf = (wt / "tests/conftest.py").read_text(encoding="utf-8")
    node = next(n for n in ast.parse(conf).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in n.targets))
    lines = conf.splitlines(keepends=True)
    plugins = [e.value for e in node.value.elts] + ["tests.fixtures.zz_probe_autouse_plugin"]
    lines[node.lineno - 1:node.end_lineno] = [f"pytest_plugins = {json.dumps(plugins)}\n"]
    idx = tmp_path_factory.mktemp("autoidx") / "index"
    genv = {**env, "GIT_INDEX_FILE": str(idx)}
    git = lambda *a, e=genv, **k: subprocess.run(["git", "-C", str(wt), *a], check=True, capture_output=True, text=True,
                                                 env=e, **k).stdout.strip()
    git("read-tree", "HEAD")
    for rel, content in (("tests/conftest.py", "".join(lines)), ("tests/fixtures/zz_probe_autouse_plugin.py", AUTOUSE_PROBE)):
        blob = git("hash-object", "-w", "--stdin", input=content)
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}")
    sha = git("commit-tree", git("write-tree"), "-p", "HEAD", "-m", "TESTREG 07f autouse probe (temporary)")
    git("checkout", "-q", "--detach", sha, e=env)
    git("update-index", "-q", "--refresh", e=env)
    yield wt
    subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(wt)], capture_output=True, env=env)


@pytest.mark.parametrize("edit", sorted(AUTOUSE_EDITS))
def test_boundary_07f_autouse_plugin_fixture_change_wall_clock(autouse_worktree, edit):
    """真實規模（第 1 批審碼 r3 後主委實測：autouse fixture 刪斷言時逐一展開比較 120 秒）：合成提交上之 autouse 外掛 fixture
    刪一行斷言／換成較弱斷言（必擋：依 pytest.ini 收集之全部測試函式 V19，以獨立 oracle 比對相等）⇒ hook rc 2、pre-commit
    rc≠0、各 3 次中位 < 5 s；加一行斷言（不減）⇒ rc 0、各 10 次中位 < 1 s（§C 兩層）。每案起點斷言共用工作樹乾淨。"""
    wt = autouse_worktree
    st = subprocess.run(["git", "-C", str(wt), "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                        text=True, check=True, env=clean_env()).stdout
    parent = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD^"], capture_output=True, text=True, check=True,
                            env=clean_env()).stdout.strip()
    main = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                          env=clean_env()).stdout.strip()
    assert st == "" and parent == main, (st, parent, main)  # 起點：合成提交之上乾淨（量測不得受前案污染）
    old, new, blocking = AUTOUSE_EDITS[edit]
    rel = "tests/fixtures/zz_probe_autouse_plugin.py"
    p = wt / rel
    src = p.read_text(encoding="utf-8")
    assert src.count(old) == 1, src
    p.write_text(src.replace(old, new), encoding="utf-8")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(p)}})
    runs, limit = (3, 5.0) if blocking else (10, 1.0)
    times, first = [], None
    try:
        for _ in range(runs):
            t0 = time.perf_counter()
            proc = subprocess.run(["bash", str(wt / "scripts/testreg_write_guard.sh")], input=payload,
                                  capture_output=True, text=True, env=clean_env(), cwd=str(wt))
            times.append(time.perf_counter() - t0)
            assert proc.returncode == (2 if blocking else 0), proc.stderr[-2000:]
            first = first or proc
        staged = _staged_times_at(wt, rel, runs, blocking)
    finally:
        p.write_text(src, encoding="utf-8")
    assert statistics.median(times) < limit, (edit, times)
    assert statistics.median(staged) < limit, (edit, staged)
    if blocking:
        expected = _collected_real(wt)
        got = _v19_subjects(first.stderr)
        assert got == expected, (len(got), len(expected), sorted(got ^ expected)[:5])


def _asserting_fixtures(root: Path, dotted: str) -> set:
    """獨立 oracle（只看字面）：外掛模組中本體直接含 assert 敘述或呼叫 assert* 名稱之 fixture 名。"""
    tree = ast.parse((root / (dotted.replace(".", "/") + ".py")).read_text(encoding="utf-8"))
    out = set()
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and any("fixture" in ast.dump(d) for d in n.decorator_list):
            if any(isinstance(x, ast.Assert) or (isinstance(x, ast.Call) and getattr(x.func, "id", getattr(x.func, "attr", ""))
                                                 .startswith("assert")) for x in ast.walk(n)):
                out.add(n.name)
    return out


def _usefixtures_users(root: Path, names: set) -> set:
    """獨立 oracle（只看字面）：函式裝飾器、類別裝飾器或模組層 pytestmark 以 usefixtures 字面請求 names 之測試函式。"""
    def uses(nodes) -> bool:
        return any(isinstance(x, ast.Call) and getattr(x.func, "attr", "") == "usefixtures"
                   and any(isinstance(a, ast.Constant) and a.value in names for a in x.args)
                   for d in nodes for x in ast.walk(d))
    out = set()
    rels = subprocess.run(["git", "-C", str(root), "ls-files", "tests/test_*.py", "tests/**/test_*.py"],
                          capture_output=True, text=True, check=True).stdout.split()
    fn = (ast.FunctionDef, ast.AsyncFunctionDef)
    for rel in rels:
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        mod = uses([s.value for s in tree.body if isinstance(s, ast.Assign)
                    and any(getattr(t, "id", "") == "pytestmark" for t in s.targets)])
        for n in tree.body:
            if isinstance(n, fn) and n.name.startswith("test") and (mod or uses(n.decorator_list)):
                out.add(f"{rel}::{n.name}")
            elif isinstance(n, ast.ClassDef) and n.name.startswith("Test"):
                cls = mod or uses(n.decorator_list)
                out |= {f"{rel}::{n.name}::{m.name}" for m in n.body
                        if isinstance(m, fn) and m.name.startswith("test") and (cls or uses(m.decorator_list))}
    return out


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


def test_precommit_routing_reads_full_input_under_pipefail(tmp_path):
    """審碼 r1 CODEX-R1-P1-01：真實 pre-commit 之 TESTREG 路由條件於 `set -o pipefail` 下，對 10,000 筆命中之暫存路徑
    仍須命中（`grep -q` 命中即退出會使上游 `tr` 收 SIGPIPE、整條管線判為假而跳過 check）；不命中輸入須不命中。"""
    lines = (REPO / "scripts/git_hooks/pre-commit").read_text(encoding="utf-8").splitlines()
    i = next(j for j, l in enumerate(lines) if "scripts/testreg.py check --staged" in l)
    start = max(j for j in range(i) if lines[j].startswith("if git diff --cached"))
    cond = "\n".join(lines[start:i]).strip()
    assert cond.startswith("if ") and cond.endswith("; then"), cond
    cond = cond[len("if "):-len("; then")].replace("git diff --cached --name-only -z", "gen")
    for paths, want in ((["tests/test_%05d.py" % k for k in range(10000)], "matched"), (["docs/x.md"], "skipped")):
        src = tmp_path / "paths.bin"
        src.write_bytes(b"".join(p.encode() + b"\0" for p in paths))
        script = f"set -o pipefail\ngen() {{ cat '{src}'; }}\nif {cond}; then echo matched; else echo skipped; fi\n"
        out = subprocess.run(["bash", "-c", script], capture_output=True, text=True).stdout.strip()
        assert out == want, (cond, out)


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
