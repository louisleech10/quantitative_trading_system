"""TESTREG Task 1.1 驗收：`scripts/testreg.py validate` 依 schema `validation_rules` V01–V22（docs/TESTREG_SPEC.md）。

結構：
- A 節：V01–V22 各一正例、一反例（反例斷言 stderr 有以該規則 id 開頭之列），與「該規則函式改為恆真 ⇒ 其反例
  之規則列消失」之 mutation（逐規則；呼叫 `testreg.main` 於行程內，以 monkeypatch 置換 `rule_vNN`）。
- B 節：收據情境（E0 ①–⑦、E1、mutation 收據與 binding、改寫收據〔SPEC v17 compare_patch〕、V14／V16／V18／V19／
  V20／V21／V22 之具名反例與正例），皆於暫存 git 倉以真實記錄器產生 ledger 後驗。
- C 節：`validate_shape`（V17 共用實作）對收據、impact_result、summary、ledger 紀錄之形狀反例。
- D 節：邊界（catalog 不存在；ledger 不在本機而 catalog 有 quarantine）與無枚舉副本之字面計數。
實作前（`scripts/testreg.py` 為空殼）全部為紅。
"""
from __future__ import annotations

import collections
import hashlib
import importlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping

import pytest

from tests.registry.testreg_helpers import (
    CATALOG_REL, REPO, TESTREG, TmpRepo, bootstrap_entry, classified, copy_repo, entry, enum, fact_keys_rows,
    lines_with, make_repo, recorded_pytest, rule_lines, schema, session_of, test_records, write_patch,
)

testreg = importlib.import_module("scripts.testreg")

# ── 共用檔案內容 ─────────────────────────────────────────────────────────────────────────────────────

CALC = "def add(a, b):\n    return a + b\n"
T_CALC = (
    "from momentum.calc import add\n\n\n"
    "def test_add():\n    total = add(1, 2)\n    assert total == 3\n\n\n"
    "def test_add_twice():\n    assert add(2, 2) == 4\n"
)
BASE = {"momentum/__init__.py": "", "momentum/calc.py": CALC, "tests/test_calc.py": T_CALC}
FUTURE = "2999-12-31"
PAST = "2000-01-01"
RETIRE_DIR = "handoffs/run_receipts/testreg-retire"
REF = "handoffs/reconcile/20261010-testreg-x-review-r16/synth.md"


def _validate(r: TmpRepo, *extra: str):
    return r.run("validate", *extra)


def _inproc(r: TmpRepo, capsys, *extra: str):
    rc = testreg.main(["--repo", str(r.root), "validate", *extra])
    err = capsys.readouterr().err
    return rc, err


def _has_rule(err: str, rule: str) -> bool:
    return any(l.startswith(rule + " ") for l in err.splitlines())


# ── E0 情境（真實 ledger）─────────────────────────────────────────────────────────────────────────────

E0_CALC_A = "def add(a, b):\n    return a + b\n\n\ndef gone(x):\n    return x\n"
E0_UTIL_A = "def gone2():\n    return 2\n"
E0_HELPER = "def use_gone():\n    from momentum.calc import gone\n    return gone(1)\n"
E0_TESTS = '''import pytest
import momentum.calc as calc
from tests.helper_gone import use_gone


def make():
    class O:
        pass
    return O()


def test_import_gone():
    from momentum.calc import gone
    assert gone(1) == 1


def test_attr_gone():
    assert calc.gone(2) == 2


def test_guard_passes():
    with pytest.raises(ImportError):
        from momentum.calc import gone  # noqa: F401


def test_helper_gone():
    assert use_gone() == 1


def test_never():
    from momentum.calc import never
    assert never() == 0


def test_tests_symbol():
    from tests.util_mod import gone2
    assert gone2() == 2


def test_obj_attr():
    obj = make()
    assert obj.gone() == 1


def test_name_error():
    assert gone(1) == 1  # noqa: F821


def test_patched_then_deleted(monkeypatch):
    monkeypatch.setattr(calc, "gone", lambda x: x, raising=False)
    monkeypatch.delattr(calc, "gone")
    assert calc.gone(3) == 3
'''
E0_FILE = "tests/test_e0.py"


@pytest.fixture(scope="module")
def e0_base(tmp_path_factory) -> Dict[str, Any]:
    """HEAD＝刪除 `gone`／`gone2` 之提交；於乾淨 HEAD 以真實記錄器跑 test_e0.py 一次。"""
    root = tmp_path_factory.mktemp("e0")
    r = make_repo(root, {"momentum/__init__.py": "", "momentum/calc.py": E0_CALC_A,
                         "tests/__init__.py": "", "tests/util_mod.py": E0_UTIL_A,
                         "tests/helper_gone.py": E0_HELPER, E0_FILE: E0_TESTS})
    r.write("momentum/calc.py", CALC)
    r.write("tests/util_mod.py", "def other():\n    return 0\n")
    deleting = r.commit("remove gone")
    proc, ids = recorded_pytest(r, E0_FILE)
    assert len(ids) == 1, proc.stdout + proc.stderr
    recs = test_records(r, ids[0])
    return {"repo": r, "session": ids[0], "records": recs, "deleting": deleting}


def _e0_receipt(fx: Mapping[str, Any], fn: str, *, module: str = "momentum.calc", symbol: str = "gone",
                exc: str = None, origin_needle: str = None) -> Dict[str, Any]:
    """收據欄一律取自真實紀錄；exc／origin_needle 只用於構造「宣稱與紀錄不符」之反例。"""
    nodeid = f"{E0_FILE}::{fn}"
    rec = fx["records"][nodeid]
    origin = rec["exception_origin"]
    if origin_needle is not None:
        origin = f"{E0_FILE}:{lines_with(fx['repo'], E0_FILE, origin_needle)[0]}"
    return {"nodeid": nodeid, "head": fx["deleting"], "ledger_ref": {"session_id": fx["session"], "nodeid": nodeid},
            "exception_type": exc or rec["exception_type"], "exception_origin": origin, "deleted_module": module,
            "deleted_symbol": symbol, "deleting_commit": fx["deleting"]}


def _retire_e0(r: TmpRepo, fx: Mapping[str, Any], fn: str, receipt: Mapping[str, Any], *, delete_fn: bool = True):
    rel = f"{RETIRE_DIR}/{fn}.json"
    r.write_json(rel, receipt)
    r.add_tombstone({"nodeid": f"{E0_FILE}::{fn}", "evidence_level": "E0", "evidence_receipt": rel,
                     "replaced_by": [], "disposition_ref": REF})
    if delete_fn:
        _delete_function(r, E0_FILE, fn)


def _delete_function(r: TmpRepo, rel: str, fn: str) -> None:
    """自檔中刪除頂層函式 fn（含其前置 decorator 與其後空行）。"""
    import ast
    src = r.read(rel)
    tree = ast.parse(src)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
    start = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
    lines = src.splitlines(keepends=True)
    end = node.end_lineno
    while end < len(lines) and not lines[end].strip():
        end += 1
    r.write(rel, "".join(lines[:start] + lines[end:]))


def test_e0_records_shape(e0_base):
    """情境前提（記錄器產出）：兩個 E0 正例目標於乾淨 HEAD 失敗且失敗行位於目標測試檔。"""
    recs = e0_base["records"]
    imp = recs[f"{E0_FILE}::test_import_gone"]
    att = recs[f"{E0_FILE}::test_attr_gone"]
    assert imp["outcome"] == "failed" and imp["exception_type"] == "ImportError"
    assert imp["exception_origin"] == f"{E0_FILE}:{lines_with(e0_base['repo'], E0_FILE, 'from momentum.calc import gone')[0]}"
    assert att["outcome"] == "failed" and att["exception_type"] == "AttributeError"
    assert att["exception_origin"] == f"{E0_FILE}:{lines_with(e0_base['repo'], E0_FILE, 'calc.gone(2)')[0]}"
    assert session_of(e0_base["repo"], e0_base["session"])["diff_digest"] == "clean"


@pytest.mark.parametrize("fn", ["test_import_gone", "test_attr_gone"])
def test_e0_valid_receipt_green(e0_base, tmp_path, fn):
    r = copy_repo(e0_base["repo"], tmp_path, "r")
    _retire_e0(r, e0_base, fn, _e0_receipt(e0_base, fn))
    proc = _validate(r)
    assert proc.returncode == 0, proc.stderr


E0_NEGATIVES = {
    # ① 目標於 HEAD 通過（負向守衛）；收據之型別與失敗行照 E0 形狀填寫，唯紀錄 outcome＝passed
    "e0_1_target_passes_at_head": ("test_guard_passes", {"exc": "ImportError",
                                                         "origin_needle": "from momentum.calc import gone  # noqa"}),
    # ② 失敗行位於 helper 而非目標測試檔
    "e0_2_fail_line_in_helper": ("test_helper_gone", {}),
    # ③ 缺失符號從未存在於 production_roots
    "e0_3_symbol_never_existed": ("test_never", {"symbol": "never"}),
    # ④ 符號定義於 tests/ 內
    "e0_4_symbol_defined_in_tests": ("test_tests_symbol", {"module": "tests.util_mod", "symbol": "gone2"}),
    # ⑤ 失敗行為 obj.sym（obj 為 setup 回傳值），同名 sym 已自生產碼刪除
    "e0_5_setup_object_attribute": ("test_obj_attr", {}),
    # ⑥ 局部名 NameError
    "e0_6_local_name_error": ("test_name_error", {"exc": "AttributeError"}),
    # ⑦ 測試先 monkeypatch.setattr 後 delattr 製造 AttributeError
    "e0_7_monkeypatch_setattr_then_delattr": ("test_patched_then_deleted", {}),
}


@pytest.mark.parametrize("case", sorted(E0_NEGATIVES))
def test_e0_negative_receipts_red(e0_base, tmp_path, case):
    fn, kw = E0_NEGATIVES[case]
    r = copy_repo(e0_base["repo"], tmp_path, "r")
    _retire_e0(r, e0_base, fn, _e0_receipt(e0_base, fn, **kw))
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


# ── E1 情境 ──────────────────────────────────────────────────────────────────────────────────────────

E1_TESTS = '''import pytest
from momentum.calc import add

K = 3


@pytest.fixture
def two():
    return 2


def test_a(two):
    assert add(1, two) == K


def test_b(two):
    assert add(1, two) == K
'''
# 函式本文與 test_dup.py::test_b 逐字相同，只差同名 fixture 之定義
E1_FIXDIFF = E1_TESTS.replace("def two():\n    return 2\n", "def two():\n    return 1 + 1\n").replace(
    "\n\ndef test_a(two):\n    assert add(1, two) == K\n", "")
# 函式本文相同，只差所引用之模組層常數之定義
E1_CONSTDIFF = E1_TESTS.replace("K = 3\n", "K = 1 + 2\n").replace("\n\ndef test_a(two):\n    assert add(1, two) == K\n", "")
E1_AUTOUSE = '''import pytest
from momentum.calc import add

K = 3


@pytest.fixture(autouse=True)
def setup_env():
    yield


@pytest.fixture
def two():
    return 2


def test_b(two):
    assert add(1, two) == K
'''
E1_MARKED = '''import pytest
from momentum.calc import add

pytestmark = pytest.mark.slow
K = 3


@pytest.fixture
def two():
    return 2


def test_b(two):
    assert add(1, two) == K
'''
E1_CLASSES = '''from momentum.calc import add


class Base:
    def setup_method(self):
        self.k = 3


class BaseAlt:
    def setup_method(self):
        self.k = 4


class TestA(Base):
    def test_x(self):
        assert add(1, 2) == self.k


class TestB(BaseAlt):
    def test_x(self):
        assert add(1, 2) == self.k
'''


def _e1_repo(tmp_path: Path, files: Mapping[str, str]) -> TmpRepo:
    return make_repo(tmp_path, {"momentum/__init__.py": "", "momentum/calc.py": CALC, **files})


def _e1_retire(r: TmpRepo, target: str, replacement: str, *, delete: bool = True, tree: str = "worktree") -> None:
    """以實作之 `e1_hashes`（validate 同一正規化）誠實記錄雜湊；之後刪除目標函式並立 E1 碑。"""
    tgt = testreg.e1_hashes(r.root, target, "HEAD")
    rep = testreg.e1_hashes(r.root, replacement, tree)
    rel = f"{RETIRE_DIR}/{target.split('::')[-1]}.json"
    r.write_json(rel, {"nodeid": target, "head": r.head(), "replacement_nodeid": replacement,
                       "target_ast_sha256": tgt["ast"], "replacement_ast_sha256": rep["ast"],
                       "fixture_closure_sha256": tgt["fixture_closure"], "module_context_sha256": tgt["module_context"]})
    r.add_tombstone({"nodeid": target, "evidence_level": "E1", "evidence_receipt": rel,
                     "replaced_by": [replacement], "disposition_ref": REF})
    if delete:
        path, fn = target.split("::", 1)
        if "::" in fn:
            raise AssertionError("類別方法用專用刪法")
        _delete_function(r, path, fn)


def test_e1_exact_duplicate_green(tmp_path):
    r = _e1_repo(tmp_path, {"tests/test_dup.py": E1_TESTS})
    _e1_retire(r, "tests/test_dup.py::test_b", "tests/test_dup.py::test_a")
    proc = _validate(r)
    assert proc.returncode == 0, proc.stderr


E1_VARIANTS = {"fixture_definition": E1_FIXDIFF, "module_constant": E1_CONSTDIFF, "autouse_fixture": E1_AUTOUSE,
               "pytestmark": E1_MARKED}


def test_e1_variants_have_identical_function_text():
    """反例前提：各變體之 test_b 本文與 test_dup.py::test_b 逐字相同（差異只在 fixture／模組層／autouse／pytestmark）。"""
    body = "def test_b(two):\n    assert add(1, two) == K\n"
    assert all(body in v for v in E1_VARIANTS.values()) and body in E1_TESTS


E1_DIFF_KEY = {"fixture_definition": "fixture_closure", "module_constant": "module_context",
               "autouse_fixture": "fixture_closure", "pytestmark": "module_context"}


@pytest.mark.parametrize("variant", sorted(E1_VARIANTS))
def test_e1_context_differs_red(tmp_path, variant):
    """fixture 定義不同而函式相同／所引用之模組層常數不同／autouse fixture 不同／pytestmark 不同 ⇒ 非完全重複 ⇒ V08。
    獨立斷言（不依收據）：兩者 ast 雜湊相同而該變體對應之情境雜湊不同——恆回相同雜湊之 e1_hashes 於此即紅。"""
    r = _e1_repo(tmp_path, {"tests/test_dup.py": E1_TESTS, "tests/test_other.py": E1_VARIANTS[variant]})
    tgt = testreg.e1_hashes(r.root, "tests/test_other.py::test_b", "HEAD")
    rep = testreg.e1_hashes(r.root, "tests/test_dup.py::test_a", "HEAD")
    assert tgt["ast"] == rep["ast"] and tgt[E1_DIFF_KEY[variant]] != rep[E1_DIFF_KEY[variant]]
    _e1_retire(r, "tests/test_other.py::test_b", "tests/test_dup.py::test_a")
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


E1_BODYDIFF = E1_TESTS.replace("\n\ndef test_a(two):\n    assert add(1, two) == K\n", "").replace(
    "def test_b(two):\n    assert add(1, two) == K\n", "def test_b(two):\n    assert add(two, 1) == K\n")


def test_e1_function_body_differs_red(tmp_path):
    """函式本文不同（情境相同）⇒ ast 雜湊須不同（恆回常數之 ast 雜湊於此即紅）⇒ 誠實收據 V08 紅。"""
    r = _e1_repo(tmp_path, {"tests/test_dup.py": E1_TESTS, "tests/test_other.py": E1_BODYDIFF})
    tgt = testreg.e1_hashes(r.root, "tests/test_other.py::test_b", "HEAD")
    rep = testreg.e1_hashes(r.root, "tests/test_dup.py::test_a", "HEAD")
    assert tgt["ast"] != rep["ast"]
    assert tgt["fixture_closure"] == rep["fixture_closure"] and tgt["module_context"] == rep["module_context"]
    _e1_retire(r, "tests/test_other.py::test_b", "tests/test_dup.py::test_a")
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


@pytest.mark.parametrize("variant", sorted(E1_VARIANTS) + ["function_body"])
def test_e1_forged_equal_hashes_recomputed_red(tmp_path, variant):
    """偽造收據：把 target 之三雜湊照抄（宣稱完全重複）而兩者情境或本文實際不同 ⇒ validate 重算不等 ⇒ V08。"""
    other = E1_BODYDIFF if variant == "function_body" else E1_VARIANTS[variant]
    r = _e1_repo(tmp_path, {"tests/test_dup.py": E1_TESTS, "tests/test_other.py": other})
    tgt = testreg.e1_hashes(r.root, "tests/test_other.py::test_b", "HEAD")
    rel = f"{RETIRE_DIR}/forged.json"
    r.write_json(rel, {"nodeid": "tests/test_other.py::test_b", "head": r.head(),
                       "replacement_nodeid": "tests/test_dup.py::test_a", "target_ast_sha256": tgt["ast"],
                       "replacement_ast_sha256": tgt["ast"], "fixture_closure_sha256": tgt["fixture_closure"],
                       "module_context_sha256": tgt["module_context"]})
    r.add_tombstone({"nodeid": "tests/test_other.py::test_b", "evidence_level": "E1", "evidence_receipt": rel,
                     "replaced_by": ["tests/test_dup.py::test_a"], "disposition_ref": REF})
    _delete_function(r, "tests/test_other.py", "test_b")
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_e1_base_class_setup_method_differs_red(tmp_path):
    r = _e1_repo(tmp_path, {"tests/test_cls.py": E1_CLASSES})
    tgt = testreg.e1_hashes(r.root, "tests/test_cls.py::TestB::test_x", "HEAD")
    rep = testreg.e1_hashes(r.root, "tests/test_cls.py::TestA::test_x", "worktree")
    rel = f"{RETIRE_DIR}/clsb.json"
    r.write_json(rel, {"nodeid": "tests/test_cls.py::TestB::test_x", "head": r.head(),
                       "replacement_nodeid": "tests/test_cls.py::TestA::test_x", "target_ast_sha256": tgt["ast"],
                       "replacement_ast_sha256": rep["ast"], "fixture_closure_sha256": tgt["fixture_closure"],
                       "module_context_sha256": tgt["module_context"]})
    r.add_tombstone({"nodeid": "tests/test_cls.py::TestB::test_x", "evidence_level": "E1", "evidence_receipt": rel,
                     "replaced_by": ["tests/test_cls.py::TestA::test_x"], "disposition_ref": REF})
    r.write("tests/test_cls.py", E1_CLASSES.replace(
        "\n\nclass TestB(BaseAlt):\n    def test_x(self):\n        assert add(1, 2) == self.k\n", "\n"))
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_v09_e1_replacement_only_in_staged_tree_green(tmp_path):
    """同提交改名之 E1 碑：replacement 只存在於暫存區之樹 ⇒ pre-commit（check --staged）綠。"""
    r = _e1_repo(tmp_path, {"tests/test_dup.py": E1_TESTS})
    r.write("tests/test_dup.py", E1_TESTS.replace("def test_b(two):", "def test_b_renamed(two):"))
    r.stage("tests/test_dup.py")
    _e1_retire(r, "tests/test_dup.py::test_b", "tests/test_dup.py::test_b_renamed", delete=False, tree="staged")
    r.stage(CATALOG_REL, RETIRE_DIR)
    proc = r.run("check", "--staged")
    assert proc.returncode == 0, proc.stderr


# ── mutation 收據情境（E2、改寫；SPEC v17 compare_patch／compare_session_id）──────────────────────────────

M_CALC = '''import warnings


def add(a, b):
    return a + b


def scale(x):
    return x * 2


def legacy():
    warnings.warn("old", DeprecationWarning)
    return 1


def validate_input(x):
    return x
'''
M_TESTS = '''import numpy as np
import pytest
from momentum.calc import add, legacy, scale


@pytest.fixture(autouse=True)
def guard():
    assert add(0, 0) == 0
    yield


def test_old():
    assert add(1, 2) == 3
    np.testing.assert_allclose(scale(1.0), 2.0)


def test_new():
    assert add(1, 2) == 3
    np.testing.assert_allclose(scale(1.0), 2.0)


def test_dep():
    with pytest.deprecated_call():
        legacy()
    assert add(2, 2) == 4


def test_dep_twin():
    with pytest.deprecated_call():
        legacy()
    assert add(2, 2) == 4
'''
N_TESTS = '''import pytest
from momentum.calc import scale


@pytest.fixture
def val():
    return scale(1)


def test_noassert(val):
    scale(3)


def test_noassert_twin(val):
    scale(3)
'''
MF = "tests/test_m.py"
NF = "tests/test_n.py"
MUTANTS = {
    "m_add": ("    return a + b\n", "    return a - b\n"),
    "m_scale": ("    return x * 2\n", "    return x * 3\n"),
    "m_guard": ("    return a + b\n", "    return a + b + (1 if (a, b) == (0, 0) else 0)\n"),
    "m_noop": ("def validate_input(x):\n", "# noop\ndef validate_input(x):\n"),
    "m_legacy": ('    warnings.warn("old", DeprecationWarning)\n', ""),
    "m_raise": ("    return x * 2\n", "    raise ValueError('m')\n"),
    "m_raise3": ("    return x * 2\n", "    if x == 3:\n        raise ValueError('m3')\n    return x * 2\n"),
    "m_testfile": None,  # 改測試檔之 mutant（反例用）
}
M_IDS = [f"{MF}::{n}" for n in ("test_old", "test_new", "test_dep", "test_dep_twin")]
REWRITE_OLD = ("    assert add(1, 2) == 3\n    np.testing.assert_allclose(scale(1.0), 2.0)\n\n\ndef test_new():")
REWRITE_NEW = ("    assert add(1, 2) == 3\n    assert scale(1.0) == 2.0\n\n\ndef test_new():")
RENAME_OLD = ('def test_dep_twin():\n    with pytest.deprecated_call():\n        legacy()\n    assert add(2, 2) == 4\n')
RENAME_NEW = ('def test_dep_renamed():\n    with pytest.deprecated_call():\n        legacy()\n'
              '    assert add(2, 2) == 4\n    assert add(1, 1) == 2\n')


def _patch_for(r: TmpRepo, mid: str) -> str:
    rel = f"handoffs/run_receipts/testreg-mutants/{mid}.patch"
    if mid == "m_testfile":
        sha = write_patch(r, MF, r.read(MF).replace("assert add(1, 2) == 3\n    np.testing",
                                                  "assert add(1, 2) == 4\n    np.testing", 1), rel)
    else:
        old, new = MUTANTS[mid]
        assert old in r.read("momentum/calc.py")
        sha = write_patch(r, "momentum/calc.py", r.read("momentum/calc.py").replace(old, new, 1), rel)
    return sha


def _run_with(r: TmpRepo, patches: List[str], *nodeids: str) -> str:
    for p in patches:
        r.git("apply", p)
    try:
        proc, ids = recorded_pytest(r, *nodeids)
    finally:
        for p in reversed(patches):
            r.git("apply", "-R", p)
    assert len(ids) == 1, proc.stdout + proc.stderr
    return ids[0]


@pytest.fixture(scope="module")
def mut_base(tmp_path_factory) -> Dict[str, Any]:
    root = tmp_path_factory.mktemp("mut")
    r = make_repo(root, {"momentum/__init__.py": "", "momentum/calc.py": M_CALC, MF: M_TESTS, NF: N_TESTS})
    head = r.head()
    sha = {m: _patch_for(r, m) for m in MUTANTS}
    pp = {m: f"handoffs/run_receipts/testreg-mutants/{m}.patch" for m in MUTANTS}
    # 補丁檔本身為未追蹤檔，會進 diff_digest ⇒ 提交補丁使 HEAD 乾淨，收據 head＝此提交
    head = r.commit("mutant patches")
    rw_patch = "handoffs/run_receipts/testreg-rewrite/test_old.compare.patch"
    rw_sha = write_patch(r, MF, r.read(MF).replace(REWRITE_OLD, REWRITE_NEW), rw_patch)
    ren_patch = "handoffs/run_receipts/testreg-retire/test_dep_twin.compare.patch"
    ren_sha = write_patch(r, MF, r.read(MF).replace(RENAME_OLD, RENAME_NEW), ren_patch)
    head = r.commit("compare patches")
    sess = {}
    for m in ("m_add", "m_scale", "m_guard", "m_noop", "m_legacy"):
        sess[m] = _run_with(r, [pp[m]], *M_IDS)
    for m in ("m_raise", "m_raise3", "m_noop"):
        sess[m + "@n"] = _run_with(r, [pp[m]], NF)
    sess["m_add@target_only"] = _run_with(r, [pp["m_add"]], f"{MF}::test_old")
    sess["m_testfile"] = _run_with(r, [pp["m_testfile"]], *M_IDS)
    for m in ("m_add", "m_scale", "m_guard"):
        sess[m + "@rw"] = _run_with(r, [rw_patch, pp[m]], f"{MF}::test_old")
    for m in ("m_add", "m_guard", "m_legacy"):
        sess[m + "@ren"] = _run_with(r, [ren_patch, pp[m]], f"{MF}::test_dep_renamed")
    sess["clean"] = _run_with(r, [], *M_IDS)
    return {"repo": r, "head": head, "sha": sha, "pp": pp, "sess": sess, "rw_patch": rw_patch, "rw_sha": rw_sha,
            "ren_patch": ren_patch, "ren_sha": ren_sha}


def _line(r: TmpRepo, rel: str, needle: str, nth: int = 0) -> str:
    return f"{rel}:{lines_with(r, rel, needle)[nth]}"


def _fail_loc(rec: Mapping[str, Any], files: List[str]) -> Any:
    hits = [f for f in rec["fail_frames"] if f.split(":")[0] in files]
    return hits[0] if hits else None  # fail_frames 由內而外 ⇒ 第一個＝最後一個落在該檔之 frame


def _mutant(fx, mid: str, sess_key: str, target: str, compare: List[str], compare_sess_key: str = None):
    r = fx["repo"]
    trec = test_records(r, fx["sess"][sess_key])[target]
    csess = fx["sess"][compare_sess_key or sess_key]
    crec = test_records(r, csess)
    return {"id": mid, "patch_path": fx["pp"][mid], "patch_sha256": fx["sha"][mid],
            "session_id": fx["sess"][sess_key], "compare_session_id": csess,
            "target_outcome": trec["outcome"], "target_fail_loc": _fail_loc(trec, [target.split("::")[0]]),
            "compare_outcomes": {c: crec[c]["outcome"] for c in compare}}


def _receipt(fx, target: str, compare: List[str], lines: List[str], mutants: List[Dict[str, Any]],
             compare_patch: str = None, compare_sha: str = None) -> Dict[str, Any]:
    r = fx["repo"]
    dc = {session_of(r, m["session_id"])["duration_class"] for m in mutants} | {
        session_of(r, m["compare_session_id"])["duration_class"] for m in mutants}
    assert len(dc) == 1
    return {"target_nodeid": target, "compare_nodeids": compare, "head": fx["head"], "fingerprint": dc.pop(),
            "target_assertion_lines": lines, "mutants": mutants, "compare_patch_path": compare_patch,
            "compare_patch_sha256": compare_sha}


def _old_lines(r: TmpRepo) -> List[str]:
    return [_line(r, MF, "assert add(0, 0) == 0"), _line(r, MF, "assert add(1, 2) == 3", 0),
            _line(r, MF, "np.testing.assert_allclose(scale(1.0), 2.0)", 0)]


def _e2_old_receipt(fx) -> Dict[str, Any]:
    t, c = f"{MF}::test_old", [f"{MF}::test_new"]
    return _receipt(fx, t, c, _old_lines(fx["repo"]),
                    [_mutant(fx, "m_add", "m_add", t, c), _mutant(fx, "m_scale", "m_scale", t, c),
                     _mutant(fx, "m_guard", "m_guard", t, c)])


def _retire_e2(r: TmpRepo, target: str, replaced_by: List[str], receipt: Mapping[str, Any], *, delete: bool = True,
               rel: str = None):
    rel = rel or f"{RETIRE_DIR}/{target.split('::')[-1]}.json"
    r.write_json(rel, receipt)
    r.add_tombstone({"nodeid": target, "evidence_level": "E2", "evidence_receipt": rel, "replaced_by": replaced_by,
                     "disposition_ref": REF})
    if delete:
        _delete_function(r, target.split("::")[0], target.split("::")[-1])


def test_mreceipt_scenario_records(mut_base):
    """情境前提（記錄器產出）：各 mutant 於目標之結果與失敗位置符合構造。"""
    r = mut_base["repo"]
    old = f"{MF}::test_old"
    add = test_records(r, mut_base["sess"]["m_add"])[old]
    assert add["outcome"] == "failed" and add["phase_failed"] == "call"
    assert _fail_loc(add, [MF]) == _line(r, MF, "assert add(1, 2) == 3", 0)
    guard = test_records(r, mut_base["sess"]["m_guard"])[old]
    assert guard["outcome"] == "error" and guard["phase_failed"] == "setup"
    assert _fail_loc(guard, [MF]) == _line(r, MF, "assert add(0, 0) == 0")
    assert all(v["outcome"] == "passed" for v in test_records(r, mut_base["sess"]["m_noop"]).values())


def test_e2_valid_receipt_green(mut_base, tmp_path):
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    _retire_e2(r, f"{MF}::test_old", [f"{MF}::test_new"], _e2_old_receipt(mut_base))
    proc = _validate(r)
    assert proc.returncode == 0, proc.stderr


def test_mreceipt_fixture_assertion_setup_kill_counts(mut_base, tmp_path):
    """target 之斷言位於 autouse fixture，殺 mutant 於 setup 期失敗且 frame 落在該 fixture ⇒ 計入（綠）；
    去掉該 mutant ⇒ fixture 斷言行無對應 mutant ⇒ 紅。"""
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    rcpt = _e2_old_receipt(mut_base)
    assert any(m["id"] == "m_guard" and m["target_outcome"] == "error" for m in rcpt["mutants"])
    _retire_e2(r, f"{MF}::test_old", [f"{MF}::test_new"], rcpt)
    assert _validate(r).returncode == 0
    rcpt["mutants"] = [m for m in rcpt["mutants"] if m["id"] != "m_guard"]
    r.write_json(f"{RETIRE_DIR}/test_old.json", rcpt)
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def _bad_e2(fx, mutate: Callable[[Dict[str, Any]], Dict[str, Any]], replaced_by: List[str] = None):
    rcpt = mutate(_e2_old_receipt(fx))
    return rcpt, replaced_by or [f"{MF}::test_new"]


def _drop_mutant(rc, mid):
    rc["mutants"] = [m for m in rc["mutants"] if m["id"] != mid]
    return rc


def _extra_compare_key(rc):
    rc["mutants"][0]["compare_outcomes"][f"{MF}::test_dep"] = "passed"
    return rc


def _swap_sessions(rc):
    a, b = rc["mutants"][0], rc["mutants"][1]
    a["session_id"], b["session_id"] = b["session_id"], a["session_id"]
    a["compare_session_id"], b["compare_session_id"] = b["compare_session_id"], a["compare_session_id"]
    return rc


def _omit_allclose(rc):
    rc["target_assertion_lines"] = [l for l in rc["target_assertion_lines"]
                                    if l != rc["target_assertion_lines"][2]]
    rc["mutants"] = [m for m in rc["mutants"] if m["id"] != "m_scale"]
    return rc


def _wrong_fingerprint(rc):
    """合法 64-hex 但不等於各 session 之 duration_class（binding_rule ④）。"""
    rc["fingerprint"] = "0" * 64 if rc["fingerprint"] != "0" * 64 else "1" * 64
    return rc


MUTATION_NEGATIVES = {
    "compare_nodeids_proper_subset_of_replaced_by": (lambda rc: rc, [f"{MF}::test_new", f"{MF}::test_dep"]),
    "fingerprint_valid_hex_wrong_value": (_wrong_fingerprint, None),
    "compare_outcomes_unlisted_key": (_extra_compare_key, None),
    "assertion_line_without_killing_mutant": (lambda rc: _drop_mutant(rc, "m_scale"), None),
    "assert_allclose_line_not_listed": (_omit_allclose, None),
    "session_diff_digest_mismatch_patch": (_swap_sessions, None),
}


@pytest.mark.parametrize("case", sorted(MUTATION_NEGATIVES))
def test_mreceipt_negatives_red(mut_base, tmp_path, case):
    mutate, replaced = MUTATION_NEGATIVES[case]
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    rcpt, rb = _bad_e2(mut_base, mutate, replaced)
    _retire_e2(r, f"{MF}::test_old", rb, rcpt)
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_mreceipt_binding_claimed_failed_but_session_passed_red(mut_base, tmp_path):
    """compare_outcomes 填 failed 而所指 session 之紀錄為 passed ⇒ 紅。"""
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    rcpt = _e2_old_receipt(mut_base)
    t, c = f"{MF}::test_old", [f"{MF}::test_new"]
    noop = _mutant(mut_base, "m_noop", "m_noop", t, c)
    assert noop["target_outcome"] == "passed"
    noop["compare_outcomes"] = {c[0]: "failed"}
    rcpt["mutants"].append(noop)
    _retire_e2(r, t, c, rcpt)
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_mreceipt_binding_session_lacks_compare_nodeid_red(mut_base, tmp_path):
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    rcpt = _e2_old_receipt(mut_base)
    rcpt["mutants"][0]["session_id"] = rcpt["mutants"][0]["compare_session_id"] = mut_base["sess"]["m_add@target_only"]
    _retire_e2(r, f"{MF}::test_old", [f"{MF}::test_new"], rcpt)
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_mreceipt_no_assertion_target_setup_kill_red_and_call_kill_green(mut_base, tmp_path):
    """無斷言 target：殺 mutant 之 target 失敗於 setup（以 fixture 破壞冒充）⇒ 紅；於 call 期在 target 函式內失敗 ⇒ 綠；
    mutants 為空 ⇒ 紅。"""
    t, c = f"{NF}::test_noassert", [f"{NF}::test_noassert_twin"]
    for key, mid, ok in (("m_raise@n", "m_raise", False), ("m_raise3@n", "m_raise3", True)):
        r = copy_repo(mut_base["repo"], tmp_path, f"r_{mid}")
        rcpt = _receipt(mut_base, t, c, [], [_mutant(mut_base, mid, key, t, c)])
        _retire_e2(r, t, c, rcpt)
        proc = _validate(r)
        assert (proc.returncode == 0) is ok, (mid, proc.stderr)
    r = copy_repo(mut_base["repo"], tmp_path, "r_empty")
    rcpt = _receipt(mut_base, t, c, [], [_mutant(mut_base, "m_raise3", "m_raise3@n", t, c)])
    rcpt["mutants"] = []
    _retire_e2(r, t, c, rcpt)
    proc = _validate(r)
    assert proc.returncode != 0, proc.stderr


def test_mreceipt_deprecated_call_line_must_be_listed(mut_base, tmp_path):
    """`pytest.deprecated_call` 行屬斷言節點：收據漏列 ⇒ 紅；列入並有殺於該行之 mutant ⇒ 綠。"""
    t, c = f"{MF}::test_dep", [f"{MF}::test_dep_twin"]
    r0 = mut_base["repo"]
    full = [_line(r0, MF, "assert add(0, 0) == 0"), _line(r0, MF, "with pytest.deprecated_call():", 0),
            _line(r0, MF, "assert add(2, 2) == 4", 0)]
    muts = [_mutant(mut_base, "m_guard", "m_guard", t, c), _mutant(mut_base, "m_legacy", "m_legacy", t, c),
            _mutant(mut_base, "m_add", "m_add", t, c)]
    r = copy_repo(r0, tmp_path, "ok")
    _retire_e2(r, t, c, _receipt(mut_base, t, c, full, muts))
    assert _validate(r).returncode == 0, _validate(r).stderr
    r = copy_repo(r0, tmp_path, "bad")
    _retire_e2(r, t, c, _receipt(mut_base, t, c, [full[0], full[2]],
                                 [m for m in muts if m["id"] != "m_legacy"]))
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_mreceipt_patch_touching_test_file_red(mut_base, tmp_path):
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    rcpt = _e2_old_receipt(mut_base)
    rcpt["mutants"].append(_mutant(mut_base, "m_testfile", "m_testfile", f"{MF}::test_old", [f"{MF}::test_new"]))
    _retire_e2(r, f"{MF}::test_old", [f"{MF}::test_new"], rcpt)
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_e2_receipt_target_nodeid_must_equal_tombstone(mut_base, tmp_path):
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    rcpt = _e2_old_receipt(mut_base)
    rcpt["target_nodeid"] = f"{MF}::test_dep"
    _retire_e2(r, f"{MF}::test_old", [f"{MF}::test_new"], rcpt)
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_new_receipt_head_must_equal_head(mut_base, tmp_path):
    """本提交新增之收據 head 不等於 HEAD ⇒ V08（以一空提交使 HEAD 前進）。"""
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    r.commit("advance")
    _retire_e2(r, f"{MF}::test_old", [f"{MF}::test_new"], _e2_old_receipt(mut_base))
    r.stage(".")
    proc = r.run("check", "--staged")
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr


def test_precommit_binding_missing_session_or_outcome_mismatch_red(mut_base, tmp_path):
    """E2 收據之 session 於 ledger 不存在 ⇒ 一般 pre-commit 即紅（V08）；改寫收據之 outcome 不符 ⇒ 一般 pre-commit 即紅（V07）。"""
    r = copy_repo(mut_base["repo"], tmp_path, "e2")
    rcpt = _e2_old_receipt(mut_base)
    rcpt["mutants"][0]["session_id"] = "00000000-0000-4000-8000-000000000000"
    _retire_e2(r, f"{MF}::test_old", [f"{MF}::test_new"], rcpt)
    r.stage(".")
    proc = r.run("check", "--staged")
    assert proc.returncode != 0 and rule_lines(proc, "V08"), proc.stderr
    r = copy_repo(mut_base["repo"], tmp_path, "rw")
    rc = _rewrite_receipt(mut_base)
    rc["mutants"][0]["compare_outcomes"][f"{MF}::test_old"] = "passed"
    _apply_rewrite(r, mut_base, rc)
    r.stage(".")
    proc = r.run("check", "--staged")
    assert proc.returncode != 0 and rule_lines(proc, "V07"), proc.stderr


# 改寫收據（SPEC v17：compare_patch 套在 head 上產生改寫後之 compare 函式；compare_session 於該樹＋mutant 補丁執行）

def _rewrite_receipt(fx) -> Dict[str, Any]:
    t = f"{MF}::test_old"
    muts = [_mutant(fx, m, m, t, [t], m + "@rw") for m in ("m_add", "m_scale", "m_guard")]
    return _receipt(fx, t, [t], _old_lines(fx["repo"]), muts, fx["rw_patch"], fx["rw_sha"])


def _apply_rewrite(r: TmpRepo, fx, rcpt: Mapping[str, Any], *, receipt: bool = True) -> None:
    r.write(MF, r.read(MF).replace(REWRITE_OLD, REWRITE_NEW))
    rel = "handoffs/run_receipts/testreg-rewrite/test_old.json"
    if receipt:
        r.write_json(rel, rcpt)
    r.put_entry(entry(MF, disposition="rewrite", rewrite_targets=[f"{MF}::test_old"], disposition_ref=REF,
                      rewrite_receipt=rel if receipt else None))


def test_rewrite_in_place_with_compare_patch_green(mut_base, tmp_path):
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    _apply_rewrite(r, mut_base, _rewrite_receipt(mut_base))
    proc = _validate(r)
    assert proc.returncode == 0, proc.stderr
    r.stage(".")
    proc = r.run("check", "--staged")
    assert proc.returncode == 0, proc.stderr


def test_rewrite_compare_patch_must_reproduce_tree_red(mut_base, tmp_path):
    """compare_patch 套在 head 後之 compare 函式須與受驗之樹相同：工作樹再改一字 ⇒ V07。"""
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    _apply_rewrite(r, mut_base, _rewrite_receipt(mut_base))
    r.write(MF, r.read(MF).replace("assert scale(1.0) == 2.0", "assert scale(1.0) == 2.0 or True"))
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V07"), proc.stderr


def test_v21_rewrite_unexecuted_require_executed_red_plain_green(mut_base, tmp_path):
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    r.put_entry(entry(MF, disposition="rewrite", rewrite_targets=[f"{MF}::test_old"], disposition_ref=REF))
    assert _validate(r).returncode == 0, _validate(r).stderr
    proc = _validate(r, "--require-executed")
    assert proc.returncode != 0 and rule_lines(proc, "V21"), proc.stderr


def test_v20_rename_with_content_change_e2_green(mut_base, tmp_path):
    """改名兼改內容而附 E2 碑（target＝舊函式於 head；compare＝新函式經 compare_patch）⇒ 綠。"""
    r = copy_repo(mut_base["repo"], tmp_path, "r")
    t, c = f"{MF}::test_dep_twin", [f"{MF}::test_dep_renamed"]
    lines = [_line(r, MF, "assert add(0, 0) == 0"), _line(r, MF, "with pytest.deprecated_call():", 1),
             _line(r, MF, "assert add(2, 2) == 4", 1)]
    muts = [_mutant(mut_base, m, m, t, c, m + "@ren") for m in ("m_guard", "m_legacy", "m_add")]
    rcpt = _receipt(mut_base, t, c, lines, muts, mut_base["ren_patch"], mut_base["ren_sha"])
    r.write(MF, r.read(MF).replace(RENAME_OLD, RENAME_NEW))
    _retire_e2(r, t, c, rcpt, delete=False)
    proc = _validate(r)
    assert proc.returncode == 0, proc.stderr


# ── V14／V22：manifest 選測位置 ─────────────────────────────────────────────────────────────────────

AWARE_GATE = "PYTHONPATH=. venv/bin/python scripts/framepath_affected_gate.py"


def _manifest(spec: str, *, test_files=(), gate_cmd="venv/bin/python -m pytest tests/x.py", rows=(),
              contract_jsons=()) -> Dict[str, Any]:
    return {"spec_path": spec, "test_files": list(test_files), "script_acceptance": [], "stub_modules": [],
            "contract_jsons": list(contract_jsons), "run_receipts": [],
            "batch_card": {"gate_cmd": gate_cmd, "risk_mitigation": list(rows), "touches": []}}


def _calc_tombstone_repo(tmp_path: Path, name: str = "r") -> TmpRepo:
    """test_add_twice 已不存在且立 E0 形狀之碑（收據內容不在本組驗證範圍；V08 之列另行排除）。"""
    r = make_repo(tmp_path, BASE, name=name)
    return r


def _new_tombstone(r: TmpRepo, nodeid: str = "tests/test_calc.py::test_add_twice", replaced_by=None) -> None:
    _delete_function(r, "tests/test_calc.py", nodeid.split("::")[-1])
    r.add_tombstone({"nodeid": nodeid, "evidence_level": "E2" if replaced_by else "E0",
                     "evidence_receipt": f"{RETIRE_DIR}/x.json", "replaced_by": list(replaced_by or []),
                     "disposition_ref": REF})


V14_CASES = {
    # (manifest, 預期 V14 列是否出現)
    "unsafe_test_files_path": (_manifest("docs/OPEN_SPEC.md", test_files=["tests/test_calc.py"]), True),
    "gate_cmd_and_and_pytest": (_manifest("docs/OPEN_SPEC.md", test_files=["tests/test_calc.py"],
                                          gate_cmd="python scripts/framepath_affected_gate.py && pytest tests/x.py"), True),
    "gate_cmd_command_substitution": (_manifest("docs/OPEN_SPEC.md", test_files=["tests/test_calc.py"],
                                                gate_cmd="python scripts/framepath_affected_gate.py $(pytest tests/x.py)"),
                                      True),
    "spec_not_in_handoff_pending": (_manifest("docs/NOWHERE_SPEC.md", test_files=["tests/test_calc.py"]), True),
    "affected_must_row_counts": (_manifest("docs/OPEN_SPEC.md", rows=[
        "affected_must phase=1 tests/test_calc.py::test_add_twice"]), True),
    "contract_jsons_only_not_counted": (_manifest("docs/OPEN_SPEC.md", contract_jsons=["tests/test_calc.py"]), False),
    "description_string_not_counted": (_manifest("docs/OPEN_SPEC.md", rows=[
        "說明：tests/test_calc.py::test_add_twice 曾為重複"]), False),
    "closed_manifest": (_manifest("docs/DONE_SPEC.md", test_files=["tests/test_calc.py"]), False),
    "aware_gate_cmd_allows_v14": (_manifest("docs/OPEN_SPEC.md", gate_cmd=AWARE_GATE, rows=[
        "affected_tests phase=1 tests/test_calc.py"]), False),
}


@pytest.mark.parametrize("case", sorted(V14_CASES))
def test_v14_manifest_selection_positions(tmp_path, case):
    man, expect = V14_CASES[case]
    r = make_repo(tmp_path, BASE)
    r.write_json("scripts/fact_keys.json", fact_keys_rows([
        ["001", "HP-OPEN", "進行中", "docs/OPEN_SPEC.md", "—"], ["002", "HP-DONE", "已完成", "docs/DONE_SPEC.md", "—"]]))
    r.write_json("docs/manifests/M.json", man)
    r.commit("manifest")
    _new_tombstone(r)
    proc = _validate(r)
    assert bool(rule_lines(proc, "V14")) is expect, proc.stderr


def test_v14_existing_tombstone_replaced_by_change_rechecked(tmp_path):
    """既有碑改換 replaced_by 而該碑 nodeid 在不安全之 manifest ⇒ V14。"""
    r = make_repo(tmp_path, {**BASE, "tests/test_other.py": "def test_o():\n    assert 1 == 1\n\n\ndef test_p():\n    assert 2 == 2\n"})
    _new_tombstone(r, replaced_by=["tests/test_other.py::test_o"])
    r.commit("tombstone")
    r.write_json("docs/manifests/M.json", _manifest("docs/OPEN_SPEC.md", test_files=["tests/test_calc.py"]))
    r.write_json("scripts/fact_keys.json", fact_keys_rows([["001", "HP-OPEN", "進行中", "docs/OPEN_SPEC.md", "—"]]))
    r.commit("manifest")
    cat = r.catalog()
    cat["tombstones"][0]["replaced_by"] = ["tests/test_other.py::test_p"]
    r.set_catalog(cat)
    proc = _validate(r)
    assert rule_lines(proc, "V14"), proc.stderr


@pytest.mark.parametrize("aware", [False, True])
def test_v22_changed_manifest_rechecks_existing_tombstones(tmp_path, aware):
    r = make_repo(tmp_path, BASE)
    _new_tombstone(r)
    r.write_json("scripts/fact_keys.json", fact_keys_rows([["001", "HP-OPEN", "進行中", "docs/OPEN_SPEC.md", "—"]]))
    r.write_json("docs/manifests/M.json", _manifest("docs/OPEN_SPEC.md"))
    r.commit("tombstone + manifest")
    row = "affected_tests phase=1 tests/test_calc.py"
    r.write_json("docs/manifests/M.json", _manifest("docs/OPEN_SPEC.md", rows=[row],
                                                    gate_cmd=AWARE_GATE if aware else "pytest tests/x.py"))
    proc = _validate(r)
    assert bool(rule_lines(proc, "V22")) is (not aware), proc.stderr
    r.stage("docs/manifests/M.json")
    proc = r.run("check", "--manifest", "docs/manifests/M.json")
    assert (proc.returncode == 0) is aware, proc.stderr


# ── V16／V18 ────────────────────────────────────────────────────────────────────────────────────────

def _bootstrapped(tmp_path: Path) -> TmpRepo:
    r = make_repo(tmp_path, BASE, catalog=False, commit=False)
    r.set_catalog({"entries": {"tests/test_calc.py": bootstrap_entry("tests/test_calc.py")}, "tombstones": []})
    r.write(schema()["bootstrap"]["paths_file"], "tests/test_calc.py\n")
    r.commit("bootstrap")
    return r


def test_v16_bootstrapped_unclassified_green(tmp_path):
    assert _validate(_bootstrapped(tmp_path)).returncode == 0


def test_v16_new_entry_unclassified_red(tmp_path):
    r = _bootstrapped(tmp_path)
    r.write("tests/test_new.py", "def test_n():\n    assert True\n")
    r.put_entry(bootstrap_entry("tests/test_new.py"))
    assert rule_lines(_validate(r), "V16")


def test_v16_classified_back_to_unclassified_red(tmp_path):
    r = _bootstrapped(tmp_path)
    r.put_entry(entry("tests/test_calc.py"))
    r.commit("classify")
    r.put_entry(bootstrap_entry("tests/test_calc.py"))
    assert rule_lines(_validate(r), "V16")


def test_v16_mixed_unclassified_red(tmp_path):
    r = _bootstrapped(tmp_path)
    e = bootstrap_entry("tests/test_calc.py")
    e["guarantee"] = [classified()["guarantee"][0], "unclassified"]
    r.put_entry(e)
    assert rule_lines(_validate(r), "V16")


def test_v18_bootstrap_paths_file_immutable(tmp_path):
    r = _bootstrapped(tmp_path)
    r.write(schema()["bootstrap"]["paths_file"], "tests/test_calc.py\ntests/test_x.py\n")
    assert rule_lines(_validate(r), "V18")


# ── V19／V20（工作樹相對 HEAD）──────────────────────────────────────────────────────────────────────

V19_HELPERS = '''def check_sum(x):
    assert x == 3


def check_four(x):
    assert x == 4
    assert x > 0
'''
V19_TESTS = '''import numpy as np
from momentum.calc import add, validate_input
from tests.helpers_v19 import check_four, check_sum


def test_plain():
    assert add(1, 2) == 3
    assert add(0, 0) == 0


def test_close():
    np.testing.assert_allclose(add(0.1, 0.2), 0.3)


def test_helper():
    check_sum(add(1, 2))
    assert add(1, 1) == 2


def test_validate():
    validate_input(add(1, 2))
    assert add(1, 2) == 3


def test_shared():
    check_four(add(2, 2))


def test_three():
    value = add(1, 2)
    assert value == 3
    assert value > 0
    assert value < 10


def check_local(x):
    assert x > 0
    assert x < 9


def test_local_helper():
    check_local(add(1, 2))
'''
V19_OTHER = "from tests.helpers_v19 import check_four\nfrom momentum.calc import add\n\n\ndef test_shared_too():\n    check_four(add(3, 1))\n"
V19_BASE = {"momentum/__init__.py": "", "momentum/calc.py": M_CALC.replace("import warnings\n\n\n", ""),
            "tests/__init__.py": "", "tests/helpers_v19.py": V19_HELPERS, "tests/test_v19.py": V19_TESTS,
            "tests/test_v19b.py": V19_OTHER}

V19_EDITS = {
    # (檔, 舊, 新, 預期 V19 之 nodeid 集合)
    "delete_assert": ("tests/test_v19.py", "    assert add(0, 0) == 0\n", "",
                      {"tests/test_v19.py::test_plain"}),
    "allclose_to_weaker": ("tests/test_v19.py", "np.testing.assert_allclose(add(0.1, 0.2), 0.3)",
                           "assert add(0.1, 0.2) is not None", {"tests/test_v19.py::test_close"}),
    "delete_helper_call": ("tests/test_v19.py", "    check_sum(add(1, 2))\n", "", {"tests/test_v19.py::test_helper"}),
    "delete_validate_call": ("tests/test_v19.py", "    validate_input(add(1, 2))\n", "",
                             {"tests/test_v19.py::test_validate"}),
    "shared_helper_drops_assert": ("tests/helpers_v19.py", "    assert x > 0\n", "",
                                   {"tests/test_v19.py::test_shared", "tests/test_v19b.py::test_shared_too"}),
    "local_helper_in_test_module_drops_assert": ("tests/test_v19.py", "    assert x < 9\n", "",
                                                 {"tests/test_v19.py::test_local_helper"}),
    "local_helper_param_rename_ok": ("tests/test_v19.py", "def check_local(x):\n    assert x > 0\n    assert x < 9\n",
                                     "def check_local(y):\n    assert y > 0\n    assert y < 9\n", set()),
    "rename_local_variable": ("tests/test_v19.py", "    value = add(1, 2)\n    assert value == 3\n    assert value > 0\n"
                              "    assert value < 10\n", "    v = add(1, 2)\n    assert v == 3\n    assert v > 0\n"
                              "    assert v < 10\n", set()),
    "extract_three_asserts_to_helper": ("tests/test_v19.py", "    value = add(1, 2)\n    assert value == 3\n"
                                        "    assert value > 0\n    assert value < 10\n",
                                        "    value = add(1, 2)\n    _three(value)\n\n\ndef _three(value):\n"
                                        "    assert value == 3\n    assert value > 0\n    assert value < 10\n", set()),
}


def _v19_nodeids(proc) -> set:
    """V19 列之主體（函式層 nodeid；列格式 `V19 <nodeid>: <訊息>`）。"""
    return {l.split(" ", 1)[1].split(": ", 1)[0].strip() for l in rule_lines(proc, "V19")}


@pytest.mark.parametrize("case", sorted(V19_EDITS))
def test_v19_assertion_multiset_cases(tmp_path, case):
    rel, old, new, expect = V19_EDITS[case]
    r = make_repo(tmp_path, V19_BASE)
    assert old in r.read(rel)
    r.write(rel, r.read(rel).replace(old, new, 1))
    proc = _validate(r)
    got = _v19_nodeids(proc)
    assert got == expect, proc.stderr
    assert (proc.returncode == 0) is (not expect), proc.stderr


@pytest.mark.parametrize("edit", ["delete", "rename"])
def test_v20_delete_or_rename_without_tombstone_red(tmp_path, edit):
    r = make_repo(tmp_path, BASE)
    if edit == "delete":
        _delete_function(r, "tests/test_calc.py", "test_add_twice")
    else:
        r.write("tests/test_calc.py", r.read("tests/test_calc.py").replace("def test_add_twice", "def test_add_two"))
    proc = _validate(r)
    assert proc.returncode != 0 and rule_lines(proc, "V20"), proc.stderr


def test_mutation_v19_count_only_comparison_misses_weaker_assertion(tmp_path, monkeypatch, capsys):
    """mutant：V19 只比斷言數不比多重集合 ⇒「換成較弱斷言」案綠（即該案之紅來自多重集合比較）。"""
    rel, old, new, _ = V19_EDITS["allclose_to_weaker"]
    r = make_repo(tmp_path, V19_BASE)
    r.write(rel, r.read(rel).replace(old, new, 1))
    rc, err = _inproc(r, capsys)
    assert _has_rule(err, "V19")
    monkeypatch.setattr(testreg, "multiset_decreased",
                        lambda o, n: ["<count>"] if sum(o.values()) > sum(n.values()) else [])
    rc, err = _inproc(r, capsys)
    assert not _has_rule(err, "V19"), err


# ── A 節：V01–V22 逐規則正反例與 mutation ──────────────────────────────────────────────────────────────

def _flaky_files() -> Dict[str, str]:
    return {**BASE, "tests/test_flaky.py": "import os\n\n\ndef test_flip():\n    assert os.environ.get('FLIP') != '1'\n"}


@pytest.fixture(scope="module")
def flaky_base(tmp_path_factory) -> Dict[str, Any]:
    """同 fingerprint 下 passed 與 failed 各一筆之 ledger（FLIP 不屬 env_prefixes，故不改 fingerprint）。"""
    r = make_repo(tmp_path_factory.mktemp("flaky"), _flaky_files())
    _, a = recorded_pytest(r, "tests/test_flaky.py")
    _, b = recorded_pytest(r, "tests/test_flaky.py", env_extra={"FLIP": "1"})
    nid = "tests/test_flaky.py::test_flip"
    assert test_records(r, a[0])[nid]["outcome"] == "passed" and test_records(r, b[0])[nid]["outcome"] == "failed"
    assert session_of(r, a[0])["fingerprint"] == session_of(r, b[0])["fingerprint"]
    return {"repo": r, "pass": a[0], "fail": b[0], "nodeid": nid}


def _quarantine(fx, expires: str = FUTURE, evidence=None) -> Dict[str, Any]:
    nid = fx["nodeid"]
    ev = evidence if evidence is not None else [{"session_id": fx["pass"], "nodeid": nid},
                                                {"session_id": fx["fail"], "nodeid": nid}]
    return {"nodeid": nid, "reason": "flaky", "evidence": ev, "expires": expires, "disposition_ref": REF}


def _with_quarantine(fx, tmp_path, q) -> TmpRepo:
    r = copy_repo(fx["repo"], tmp_path, "r")
    r.put_entry(entry("tests/test_flaky.py", quarantine=[q], disposition_ref=REF))
    return r


def _base(tmp_path, **kw) -> TmpRepo:
    return make_repo(tmp_path, BASE, **kw)


def _cat_edit(r: TmpRepo, fn: Callable[[Dict[str, Any]], None]) -> TmpRepo:
    cat = r.catalog()
    fn(cat)
    r.set_catalog(cat)
    return r


def _ent(cat, path="tests/test_calc.py"):
    return cat["entries"][path]


G_FILE = "tests/test_g.py"
G_TESTS = ("import momentum.calc as calc\n\n\ndef test_g_import():\n    from momentum.calc import gone\n"
           "    assert gone(1) == 1\n\n\ndef test_g_attr():\n    assert calc.gone(2) == 2\n")


def _e0_small(tmp_path: Path, extra: Mapping[str, str] = None, name: str = "small") -> Dict[str, Any]:
    """兩函式皆可持 E0 之小倉：init（含 extra，如 manifest／fact_keys）→ 刪 gone 提交 → 乾淨 HEAD 跑一次。"""
    r = make_repo(tmp_path, {"momentum/__init__.py": "", "momentum/calc.py": E0_CALC_A, G_FILE: G_TESTS,
                             **(extra or {})}, name=name)
    r.write("momentum/calc.py", CALC)
    deleting = r.commit("remove gone")
    proc, ids = recorded_pytest(r, G_FILE)
    assert len(ids) == 1, proc.stdout + proc.stderr
    return {"repo": r, "session": ids[0], "records": test_records(r, ids[0]), "deleting": deleting}


def _retire_small(info: Mapping[str, Any], fn: str, *, delete_fn: bool = True) -> None:
    r, nid = info["repo"], f"{G_FILE}::{fn}"
    rec = info["records"][nid]
    rel = f"{RETIRE_DIR}/{fn}.json"
    r.write_json(rel, {"nodeid": nid, "head": info["deleting"], "ledger_ref": {"session_id": info["session"],
                                                                               "nodeid": nid},
                       "exception_type": rec["exception_type"], "exception_origin": rec["exception_origin"],
                       "deleted_module": "momentum.calc", "deleted_symbol": "gone", "deleting_commit": info["deleting"]})
    r.add_tombstone({"nodeid": nid, "evidence_level": "E0", "evidence_receipt": rel, "replaced_by": [],
                     "disposition_ref": REF})
    if delete_fn:
        _delete_function(r, G_FILE, fn)


def _pos_v01(tmp_path, fx):
    """整檔淘汰：檔已刪而 entry 仍在，其全部函式皆有碑 ⇒ V01 綠。"""
    info = _e0_small(tmp_path)
    for fn in ("test_g_import", "test_g_attr"):
        _retire_small(info, fn, delete_fn=False)
    info["repo"].delete(G_FILE)
    return info["repo"]


def _neg_v01(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: c["entries"].__setitem__("tests/test_ghost.py",
                                                                         entry("tests/test_ghost.py")))


def _neg_v02(tmp_path, fx):
    r = _base(tmp_path)
    r.write("tests/test_new.py", "def test_n():\n    assert 1 == 1\n")
    return r


def _neg_v03(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: _ent(c).__setitem__("owner", "x"))


def _pos_v04(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: _ent(c).__setitem__("disposition_ref", REF))


def _neg_v04(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: _ent(c).__setitem__("ticket", "OTHER"))


def _pos_v05(tmp_path, fx):
    vals = [v for v in enum("charter_category") if v != "unclassified"][:2]
    return _cat_edit(_base(tmp_path), lambda c: _ent(c).__setitem__("guarantee", vals))


def _neg_v05(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: _ent(c).__setitem__("oracle", ["NOPE"]))


def _rewrite_entry(c, ref=REF, targets=("tests/test_calc.py::test_add",)):
    _ent(c).update({"disposition": "rewrite", "disposition_ref": ref, "rewrite_targets": list(targets)})


def _pos_v06(tmp_path, fx):
    return _cat_edit(_base(tmp_path), _rewrite_entry)


def _neg_v06(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: _rewrite_entry(c, ref=None))


def _pos_v07(tmp_path, fx):
    r = copy_repo(fx["mut"]["repo"], tmp_path, "r")
    _apply_rewrite(r, fx["mut"], _rewrite_receipt(fx["mut"]))
    return r


def _neg_v07(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: (_rewrite_entry(c), _ent(c).__setitem__(
        "rewrite_receipt", "handoffs/run_receipts/testreg-rewrite/missing.json")))


def _pos_v08(tmp_path, fx):
    r = copy_repo(fx["e0"]["repo"], tmp_path, "r")
    _retire_e0(r, fx["e0"], "test_import_gone", _e0_receipt(fx["e0"], "test_import_gone"))
    return r


def _neg_v08(tmp_path, fx):
    r = _base(tmp_path)
    r.add_tombstone({"nodeid": "tests/test_calc.py::test_removed", "evidence_level": "E0",
                     "evidence_receipt": f"{RETIRE_DIR}/nope.json", "replaced_by": [], "disposition_ref": REF})
    return r


def _pos_v09(tmp_path, fx):
    r = _e1_repo(tmp_path, {"tests/test_dup.py": E1_TESTS})
    _e1_retire(r, "tests/test_dup.py::test_b", "tests/test_dup.py::test_a")
    return r


def _neg_v09(tmp_path, fx):
    r = _pos_v09(tmp_path, fx)
    return _cat_edit(r, lambda c: c["tombstones"][0].__setitem__("replaced_by", []))


def _neg_v10(tmp_path, fx):
    r = copy_repo(fx["e0"]["repo"], tmp_path, "r")
    _retire_e0(r, fx["e0"], "test_import_gone", _e0_receipt(fx["e0"], "test_import_gone"), delete_fn=False)
    return r


def _pos_v11(tmp_path, fx):
    return _with_quarantine(fx["flaky"], tmp_path, _quarantine(fx["flaky"]))


def _neg_v11(tmp_path, fx):
    return _with_quarantine(fx["flaky"], tmp_path, _quarantine(fx["flaky"], expires=PAST))


def _neg_v12(tmp_path, fx):
    f = fx["flaky"]
    return _with_quarantine(f, tmp_path, _quarantine(f, evidence=[{"session_id": f["pass"], "nodeid": f["nodeid"]},
                                                                  {"session_id": f["pass"], "nodeid": f["nodeid"]}]))


def _neg_v13(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: c.__setitem__("extra", {}))


def _manifest_files(spec: str, row_state: str, **man_kw: Any) -> Dict[str, str]:
    return {"scripts/fact_keys.json": json.dumps(fact_keys_rows([["001", "HP-X", row_state, spec, "—"]])),
            "docs/manifests/M.json": json.dumps(_manifest(spec, **man_kw))}


def _pos_v14(tmp_path, fx):
    """新碑所指檔出現在已收案 manifest 之 test_files ⇒ V14 綠（manifest 於刪除提交前即存在，收據 head＝HEAD）。"""
    info = _e0_small(tmp_path, _manifest_files("docs/DONE_SPEC.md", "已完成", test_files=[G_FILE]))
    _retire_small(info, "test_g_attr")
    return info["repo"]


def _neg_v14(tmp_path, fx):
    r = _base(tmp_path)
    r.write_json("scripts/fact_keys.json", fact_keys_rows([["001", "HP-OPEN", "進行中", "docs/OPEN_SPEC.md", "—"]]))
    r.write_json("docs/manifests/M.json", _manifest("docs/OPEN_SPEC.md", test_files=["tests/test_calc.py"]))
    r.commit("manifest")
    _new_tombstone(r)
    return r


def _neg_v15(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: _rewrite_entry(c, targets=("tests/test_calc.py::test_nope",)))


def _neg_v16(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: c["entries"].__setitem__(
        "tests/test_calc.py", bootstrap_entry("tests/test_calc.py")))


def _neg_v17(tmp_path, fx):
    return _cat_edit(_base(tmp_path), lambda c: _ent(c).__setitem__("ticket", 5))


def _neg_v18(tmp_path, fx):
    r = _bootstrapped(tmp_path)
    r.write(schema()["bootstrap"]["paths_file"], "tests/test_other.py\n")
    return r


def _pos_v19(tmp_path, fx):
    r = _base(tmp_path)
    r.write("tests/test_calc.py", r.read("tests/test_calc.py") + "    assert add(2, 3) == 5\n")
    return r


def _neg_v19(tmp_path, fx):
    r = _base(tmp_path)
    r.write("tests/test_calc.py", r.read("tests/test_calc.py").replace("    assert total == 3\n", "    total\n"))
    return r


def _pos_v20(tmp_path, fx):
    r = _e1_repo(tmp_path, {"tests/test_dup.py": E1_TESTS})
    r.write("tests/test_dup.py", E1_TESTS.replace("def test_b(two):", "def test_b_renamed(two):"))
    _e1_retire(r, "tests/test_dup.py::test_b", "tests/test_dup.py::test_b_renamed", delete=False)
    return r


def _neg_v20(tmp_path, fx):
    r = _base(tmp_path)
    _delete_function(r, "tests/test_calc.py", "test_add_twice")
    return r


def _neg_v21(tmp_path, fx):
    return _cat_edit(_base(tmp_path), _rewrite_entry)


def _pos_v22(tmp_path, fx):
    """既有碑（收據 head 為 HEAD 之祖先）之檔被加入一個閘會解析碑之 manifest ⇒ V22 綠。"""
    info = _e0_small(tmp_path, _manifest_files("docs/OPEN_SPEC.md", "進行中"))
    _retire_small(info, "test_g_attr")
    r = info["repo"]
    r.commit("tombstone")
    r.write_json("docs/manifests/M.json", _manifest("docs/OPEN_SPEC.md", gate_cmd=AWARE_GATE,
                                                    rows=[f"affected_tests phase=1 {G_FILE}"]))
    return r


def _neg_v22(tmp_path, fx):
    r = _base(tmp_path)
    _new_tombstone(r)
    r.write_json("scripts/fact_keys.json", fact_keys_rows([["001", "HP-OPEN", "進行中", "docs/OPEN_SPEC.md", "—"]]))
    r.write_json("docs/manifests/M.json", _manifest("docs/OPEN_SPEC.md"))
    r.commit("tombstone")
    r.write_json("docs/manifests/M.json", _manifest("docs/OPEN_SPEC.md", rows=["affected_tests phase=1 tests/test_calc.py"]))
    return r


_plain = lambda tmp_path, fx: _base(tmp_path)  # noqa: E731
RULE_CASES: Dict[str, Dict[str, Any]] = {
    "V01": {"pos": _pos_v01, "neg": _neg_v01},
    "V02": {"pos": _plain, "neg": _neg_v02},
    "V03": {"pos": _plain, "neg": _neg_v03},
    "V04": {"pos": _pos_v04, "neg": _neg_v04},
    "V05": {"pos": _pos_v05, "neg": _neg_v05},
    "V06": {"pos": _pos_v06, "neg": _neg_v06},
    "V07": {"pos": _pos_v07, "neg": _neg_v07},
    "V08": {"pos": _pos_v08, "neg": _neg_v08},
    "V09": {"pos": _pos_v09, "neg": _neg_v09},
    "V10": {"pos": _pos_v08, "neg": _neg_v10},
    "V11": {"pos": _pos_v11, "neg": _neg_v11},
    "V12": {"pos": _pos_v11, "neg": _neg_v12},
    "V13": {"pos": _plain, "neg": _neg_v13},
    "V14": {"pos": _pos_v14, "neg": _neg_v14},
    "V15": {"pos": _pos_v06, "neg": _neg_v15},
    "V16": {"pos": lambda tp, fx: _bootstrapped(tp), "neg": _neg_v16},
    "V17": {"pos": _plain, "neg": _neg_v17},
    "V18": {"pos": lambda tp, fx: _bootstrapped(tp), "neg": _neg_v18},
    "V19": {"pos": _pos_v19, "neg": _neg_v19},
    "V20": {"pos": _pos_v20, "neg": _neg_v20},
    "V21": {"pos": _pos_v07, "neg": _neg_v21, "args": ("--require-executed",)},
    "V22": {"pos": _pos_v22, "neg": _neg_v22},
}


@pytest.fixture
def fx(e0_base, mut_base, flaky_base):
    return {"e0": e0_base, "mut": mut_base, "flaky": flaky_base}


def test_rule_cases_cover_all_schema_rules():
    assert sorted(RULE_CASES) == [r["id"] for r in schema()["validation_rules"]] == list(testreg.RULE_IDS)


@pytest.mark.parametrize("rule", sorted(RULE_CASES))
def test_rule_positive(tmp_path, fx, rule):
    case = RULE_CASES[rule]
    proc = _validate(case["pos"](tmp_path, fx), *case.get("args", ()))
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("rule", sorted(RULE_CASES))
def test_rule_negative(tmp_path, fx, rule):
    case = RULE_CASES[rule]
    proc = _validate(case["neg"](tmp_path, fx), *case.get("args", ()))
    assert proc.returncode != 0 and rule_lines(proc, rule), proc.stderr


@pytest.mark.parametrize("rule", sorted(RULE_CASES))
def test_mutation_rule_always_true_turns_negative_green(tmp_path, fx, rule, monkeypatch, capsys):
    """mutant：規則函式改為恆真 ⇒ 其反例之該規則列消失（反例測試即紅）。"""
    case = RULE_CASES[rule]
    r = case["neg"](tmp_path, fx)
    rc, err = _inproc(r, capsys, *case.get("args", ()))
    assert rc != 0 and _has_rule(err, rule), err
    monkeypatch.setattr(testreg, f"rule_{rule.lower()}", lambda ctx: [])
    rc, err = _inproc(r, capsys, *case.get("args", ()))
    assert not _has_rule(err, rule), err


def test_mutation_v07_change_requires_receipt_half(tmp_path, monkeypatch, capsys):
    """mutant：V07 只查「rewrite_receipt 非 null ⇒ 驗過」方向 ⇒ 待改寫檔有暫存變更而無收據之提交通過。"""
    r = _base(tmp_path)
    _cat_edit(r, _rewrite_entry)
    r.commit("classify rewrite")
    r.write("tests/test_calc.py", r.read("tests/test_calc.py") + "    assert add(0, 1) == 1\n")
    r.stage(".")
    rc = testreg.main(["--repo", str(r.root), "check", "--staged"])
    err = capsys.readouterr().err
    assert rc != 0 and _has_rule(err, "V07"), err
    monkeypatch.setattr(testreg, "rule_v07_change_requires_receipt", lambda ctx: [])
    rc = testreg.main(["--repo", str(r.root), "check", "--staged"])
    err = capsys.readouterr().err
    assert not _has_rule(err, "V07"), err


# ── C 節：validate_shape（V17 共用實作）───────────────────────────────────────────────────────────────

def _types():
    return schema()["types"]


def _good_e0() -> Dict[str, Any]:
    return {"nodeid": "tests/test_a.py::test_x", "head": "a" * 40,
            "ledger_ref": {"session_id": "12345678-1234-4123-8123-123456789abc", "nodeid": "tests/test_a.py::test_x"},
            "exception_type": enum("e0_exception_types")[0], "exception_origin": "tests/test_a.py:3",
            "deleted_module": "momentum.calc", "deleted_symbol": "gone", "deleting_commit": "b" * 40}


def _summary(n: int) -> Dict[str, Any]:
    rec = {"session_id": "12345678-1234-4123-8123-123456789abc", "started": "2026-10-10T00:00:00Z",
           "fingerprint": "c" * 64, "duration_class": "d" * 64, "outcome": enum("outcome")[0], "duration_s": 1.0,
           "exception_type": None, "exception_head": None}
    k = schema()["summary"]["k"]
    return {"schema_version": schema()["version"], "k": k, "nodes": {"tests/test_a.py::test_x": [rec] * n}}


def _summary_with_unknown_key() -> Dict[str, Any]:
    s = json.loads(json.dumps(_summary(1)))
    s["nodes"]["tests/test_a.py::test_x"][0]["x"] = 1
    return s


def _test_record(duration: float) -> Dict[str, Any]:
    return {"kind": "test", "session_id": "12345678-1234-4123-8123-123456789abc", "nodeid": "tests/test_a.py::test_x",
            "order": 0, "outcome": enum("outcome")[0], "duration_s": duration, "phase_failed": "none",
            "exception_type": None, "exception_head": None, "exception_origin": None, "fail_line": None,
            "fail_frames": [], "teardown_failed": False, "markers": []}


def test_shape_good_examples_pass():
    s = schema()
    assert testreg.validate_shape(_good_e0(), {"type": "types.receipt_E0"}, s) == []
    assert testreg.validate_shape(_summary(1), s["summary"]["shape"], s) == []
    assert testreg.validate_shape(_test_record(0.5), {"type": "types.test_record"}, s) == []
    imp = {"selected": [{"path": "tests/test_a.py", "reasons": [enum("select_reason")[0]]}], "excluded": []}
    assert testreg.validate_shape(imp, {"type": "types.impact_result"}, s) == []


SHAPE_NEGATIVES = {
    "receipt_unknown_field": ("types.receipt_E0", lambda: dict(_good_e0(), extra=1)),
    "receipt_head_not_40_hex": ("types.receipt_E0", lambda: dict(_good_e0(), head="abc")),
    "impact_selected_empty": ("types.impact_result", lambda: {"selected": [], "excluded": []}),
    "summary_records_exceed_k": ("summary.shape", lambda: _summary(schema()["summary"]["k"] + 1)),
    "summary_record_unknown_key": ("summary.shape", lambda: _summary_with_unknown_key()),
    "ledger_duration_negative": ("types.test_record", lambda: _test_record(-1.0)),
    "ledger_duration_nan": ("types.test_record", lambda: _test_record(math.nan)),
}


@pytest.mark.parametrize("case", sorted(SHAPE_NEGATIVES))
def test_shape_negatives(case):
    key, build = SHAPE_NEGATIVES[case]
    s = schema()
    spec = s["summary"]["shape"] if key == "summary.shape" else {"type": key}
    assert testreg.validate_shape(build(), spec, s) != []


CATALOG_SHAPE_NEGATIVES = {
    "nodeid_format": lambda c: c["tombstones"].append({"nodeid": "tests/test_calc.py:test_x", "evidence_level": "E0",
                                                      "evidence_receipt": f"{RETIRE_DIR}/x.json", "replaced_by": [],
                                                      "disposition_ref": REF}),
    "expires_not_date": lambda c: _ent(c)["quarantine"].append(
        {"nodeid": "tests/test_calc.py::test_add", "reason": "r", "expires": "2026/12/31", "disposition_ref": REF,
         "evidence": [{"session_id": "12345678-1234-4123-8123-123456789abc", "nodeid": "tests/test_calc.py::test_add"}] * 2}),
    "path_dotdot": lambda c: _ent(c).__setitem__("disposition_ref", "docs/../x.md"),
    "path_leading_slash": lambda c: _ent(c).__setitem__("disposition_ref", "/abs/x.md"),
    "evidence_missing_session_id": lambda c: _ent(c)["quarantine"].append(
        {"nodeid": "tests/test_calc.py::test_add", "reason": "r", "expires": FUTURE, "disposition_ref": REF,
         "evidence": [{"nodeid": "tests/test_calc.py::test_add"}] * 2}),
    "evidence_session_id_bad_format": lambda c: _ent(c)["quarantine"].append(
        {"nodeid": "tests/test_calc.py::test_add", "reason": "r", "expires": FUTURE, "disposition_ref": REF,
         "evidence": [{"session_id": "not-a-uuid", "nodeid": "tests/test_calc.py::test_add"}] * 2}),
    "map_key_differs_from_path": lambda c: c["entries"].__setitem__("tests/test_calc.py",
                                                                    dict(_ent(c), path="tests/test_other.py")),
}


@pytest.mark.parametrize("case", sorted(CATALOG_SHAPE_NEGATIVES))
def test_catalog_shape_negatives(tmp_path, case):
    r = _base(tmp_path)
    _cat_edit(r, CATALOG_SHAPE_NEGATIVES[case])
    proc = _validate(r)
    want = "V03" if case == "map_key_differs_from_path" else "V17"
    assert proc.returncode != 0 and rule_lines(proc, want), proc.stderr


# ── D 節：邊界與無枚舉副本 ───────────────────────────────────────────────────────────────────────────

def test_boundary_01_catalog_missing_named_nonzero(tmp_path):
    r = make_repo(tmp_path, BASE, catalog=False)
    proc = _validate(r)
    assert proc.returncode != 0
    assert CATALOG_REL in proc.stderr


def test_boundary_02_ledger_missing_with_quarantine_unverifiable(flaky_base, tmp_path):
    r = _with_quarantine(flaky_base, tmp_path, _quarantine(flaky_base))
    import shutil
    shutil.move(str(r.p(".testreg")), str(tmp_path / "moved_ledger"))
    proc = _validate(r)
    assert proc.returncode != 0
    assert any("unverifiable" in l for l in rule_lines(proc, "V12")), proc.stderr


def test_no_enum_copies_in_testreg_source():
    """`grep -c "A22\\|EXACT\\|correctness" scripts/testreg.py` == 0（枚舉一律讀 schema）。"""
    text = TESTREG.read_text(encoding="utf-8")
    assert sum(text.count(w) for w in ("A22", "EXACT", "correctness")) == 0
