"""TESTREG Task 2.2 驗收：`scripts/testreg.py impact`（docs/TESTREG_SPEC.md；schema `impact`、`enums.select_reason`／
`exclude_reason`）。暫存倉之匯入圖已知，期望集合由構造直接寫出（獨立於實作之 oracle）。實作前（空殼）為紅。"""
from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set

import pytest

from tests.registry.testreg_helpers import TmpRepo, clean_env, entry, make_repo

testreg = importlib.import_module("scripts.testreg")

FILES = {
    "momentum/__init__.py": "",
    "momentum/a.py": "def fa():\n    return 1\n",
    "momentum/b.py": "from momentum.a import fa\n\n\ndef fb():\n    return fa()\n",
    "momentum/factories.py": "def make():\n    from momentum.core.c import cx\n    return cx()\n",
    "momentum/dyn.py": "import importlib\n\n\ndef load(name):\n    return importlib.import_module(name)\n",
    "momentum/core/__init__.py": "",
    "momentum/core/c.py": "def cx():\n    return 3\n",
    "momentum/core/d.py": "def dx():\n    return 4\n",
    "tests/__init__.py": "",
    "tests/conftest.py": "",
    "tests/helpers/__init__.py": "",
    "tests/helpers/h.py": "def helper():\n    return 0\n",
    "tests/test_a.py": "from momentum.a import fa\n\n\ndef test_a():\n    assert fa() == 1\n",
    "tests/test_b.py": "from momentum.b import fb\n\n\ndef test_b():\n    assert fb() == 1\n",
    "tests/test_fact.py": "from momentum.factories import make\n\n\ndef test_fact():\n    assert make() == 3\n",
    "tests/test_dyn.py": "from momentum.dyn import load\n\n\ndef test_dyn():\n    assert load('math')\n",
    "tests/test_d.py": "from momentum.core.d import dx\n\n\ndef test_d():\n    assert dx() == 4\n",
    "tests/test_none.py": "def test_none():\n    assert True\n",
    "tests/test_h.py": "from tests.helpers.h import helper\n\n\ndef test_h():\n    assert helper() == 0\n",
    "tests/feature_engineering/__init__.py": "",
    "tests/feature_engineering/conftest.py": "",
    "tests/feature_engineering/test_fe1.py": "def test_fe1():\n    assert True\n",
    "tests/feature_engineering/test_fe2.py": "def test_fe2():\n    assert True\n",
    "tests/registry/test_r.py": "def test_r():\n    assert True\n",
}
ALL_TESTS = sorted(p for p in FILES if p.split("/")[-1].startswith("test_"))


def _repo(tmp_path: Path, files: Dict[str, str] = None) -> TmpRepo:
    return make_repo(tmp_path, files or FILES)


def _sel(res: Dict[str, Any]) -> Dict[str, List[str]]:
    return {x["path"]: x["reasons"] for x in res["selected"]}


def _exc(res: Dict[str, Any]) -> Dict[str, str]:
    return {x["path"]: x["excluded_reason"] for x in res["excluded"]}


def _impact(r: TmpRepo, changed=(), must=(), prev=()) -> Dict[str, Any]:
    res = testreg.impact(r.root, list(changed), list(must), list(prev))
    sel, exc = set(_sel(res)), set(_exc(res))
    assert not sel & exc and sel | exc == set(ALL_TESTS_OF(r))
    return res


def ALL_TESTS_OF(r: TmpRepo) -> List[str]:
    return sorted(str(p.relative_to(r.root)) for p in (r.root / "tests").rglob("test_*.py"))


# ── ①② shared_test_infra ────────────────────────────────────────────────────────────────────────────

def test_01_root_conftest_selects_all(tmp_path):
    r = _repo(tmp_path)
    res = _impact(r, changed=["tests/conftest.py"])
    assert sorted(_sel(res)) == ALL_TESTS
    assert all("registry_unresolved" in v for v in _sel(res).values())


def test_02_subdir_conftest_selects_dir(tmp_path):
    r = _repo(tmp_path)
    sel = _sel(_impact(r, changed=["tests/feature_engineering/conftest.py"]))
    assert {"tests/feature_engineering/test_fe1.py", "tests/feature_engineering/test_fe2.py"} <= set(sel)


def test_mutation_shared_infra_removed_breaks_01(tmp_path, monkeypatch):
    r = _repo(tmp_path)
    assert sorted(_sel(_impact(r, changed=["tests/conftest.py"]))) == ALL_TESTS
    monkeypatch.setattr(testreg, "shared_infra_scope", lambda *a, **k: None)
    assert sorted(_sel_or_empty(r, ["tests/conftest.py"], [])) != ALL_TESTS


def _sel_or_empty(r: TmpRepo, changed, must) -> List[str]:
    """mutant 下 impact 可能因選集為空而具名拒跑（不輸出空集合）——視同未選入。"""
    try:
        return [x["path"] for x in testreg.impact(r.root, list(changed), list(must), [])["selected"]]
    except testreg.TestregError:
        return []


# ── ③④ 生產檔：taint 可解析／不可定 ─────────────────────────────────────────────────────────────────

def test_03_resolvable_production_change_no_unresolved(tmp_path):
    r = _repo(tmp_path)
    sel = _sel(_impact(r, changed=["momentum/a.py"]))
    assert {"tests/test_a.py", "tests/test_b.py"} <= set(sel)
    assert all("registry_unresolved" not in v for v in sel.values())


DYN_C = "import importlib\n\n\ndef cx():\n    return 3\n\n\ndef load(name):\n    return importlib.import_module(name)\n"
# domain(momentum/core/c.py)：prefix＝momentum/core（目錄層，不含檔名）⇒ 閉包含 momentum/core 下模組者
# （test_fact 經 factories 函式內 import、test_d）∪ 閉包含 dyn_modules（momentum/dyn.py、momentum/core/c.py）者（test_dyn）
DOMAIN_C = {"tests/test_fact.py", "tests/test_d.py", "tests/test_dyn.py"}


def _dyn_repo(tmp_path: Path) -> TmpRepo:
    r = _repo(tmp_path)
    r.write("momentum/core/c.py", DYN_C)
    return r


def test_04_unresolvable_production_change_selects_domain(tmp_path):
    r = _dyn_repo(tmp_path)
    sel = _sel(_impact(r, changed=["momentum/core/c.py"]))
    unresolved = {p for p, v in sel.items() if "registry_unresolved" in v}
    assert unresolved == DOMAIN_C
    assert set(sel) >= DOMAIN_C


def test_04b_function_level_import_reaches_domain(tmp_path):
    r = _dyn_repo(tmp_path)
    assert "tests/test_fact.py" in _sel(_impact(r, changed=["momentum/core/c.py"]))
    assert "momentum/core/c.py" in testreg.import_closure(r.root, "tests/test_fact.py")


def test_04c_dynamic_import_module_in_every_domain(tmp_path):
    r = _dyn_repo(tmp_path)
    r.write("momentum/core/d.py", "def dx():\n    return 4\n\n\ndef bad(n):\n    return __import__(n)\n")
    sel = _sel(_impact(r, changed=["momentum/core/d.py"]))
    assert "tests/test_dyn.py" in sel and "registry_unresolved" in sel["tests/test_dyn.py"]


def test_domain_prefix_directory_levels():
    """契約例：層＝目錄層、不含檔名。"""
    assert testreg.domain_prefix("momentum/core/c.py") == "momentum/core"
    assert testreg.domain_prefix("momentum/dyn.py") == "momentum"
    assert testreg.domain_prefix("momentum/FeatureEngineering/timeframe/x.py") == "momentum/FeatureEngineering"
    assert testreg.domain_prefix("run_api.py") == ""


def test_mutation_domain_prefix_counts_filename_breaks_shallow_path(tmp_path, monkeypatch):
    """mutant：prefix 取路徑前兩段（把檔名當一層）⇒ momentum/dyn.py 得 momentum/dyn.py，淺路徑之 domain 縮小。"""
    r = _repo(tmp_path)
    r.write("momentum/dyn.py", FILES["momentum/dyn.py"] + "\n\ndef again(n):\n    return __import__(n)\n")
    want = {"tests/test_a.py", "tests/test_b.py", "tests/test_fact.py", "tests/test_dyn.py", "tests/test_d.py"}
    sel = _sel(_impact(r, changed=["momentum/dyn.py"]))
    assert {p for p, v in sel.items() if "registry_unresolved" in v} == want
    monkeypatch.setattr(testreg, "domain_prefix", lambda p: "/".join(p.split("/")[:2]))
    sel = _sel(testreg.impact(r.root, ["momentum/dyn.py"], [], []))
    assert {p for p, v in sel.items() if "registry_unresolved" in v} != want


def test_mutation_domain_one_layer_breaks_04(tmp_path, monkeypatch):
    r = _dyn_repo(tmp_path)
    monkeypatch.setattr(testreg, "domain_prefix", lambda p: p.split("/")[0])
    sel = _sel(testreg.impact(r.root, ["momentum/core/c.py"], [], []))
    assert {p for p, v in sel.items() if "registry_unresolved" in v} != DOMAIN_C


def test_mutation_closure_direct_only_breaks_04b(tmp_path, monkeypatch):
    r = _dyn_repo(tmp_path)
    import ast

    def direct(repo_root, test_path):
        tree = ast.parse((repo_root / test_path).read_text(encoding="utf-8"))
        out = set()
        for n in tree.body:
            if isinstance(n, ast.ImportFrom) and n.module:
                p = n.module.replace(".", "/") + ".py"
                if (repo_root / p).exists():
                    out.add(p)
        return frozenset(out)

    monkeypatch.setattr(testreg, "import_closure", direct)
    sel = _sel(testreg.impact(r.root, ["momentum/core/c.py"], [], []))
    assert "registry_unresolved" not in sel.get("tests/test_fact.py", [])


# ── ⑤ 聯集、previously_failed、helper、碑、manifest 分組、錨點 worktree ─────────────────────────────────

MUST = ["tests/test_none.py::test_none"]


@pytest.mark.parametrize("changed", [[], ["momentum/a.py"], ["tests/conftest.py"], ["tests/helpers/h.py"]])
def test_05_selected_superset_of_must(tmp_path, changed):
    r = _repo(tmp_path)
    sel = _sel(_impact(r, changed=changed, must=MUST))
    assert "tests/test_none.py" in sel and "must" in sel["tests/test_none.py"]


def test_mutation_union_to_intersection_breaks_05(tmp_path, monkeypatch):
    r = _repo(tmp_path)

    def intersect(sources):
        sets = [set(v) for v in sources.values() if v]
        common = set.intersection(*sets) if sets else set()
        return {p: sorted(k for k, v in sources.items() if p in v) for p in common}

    monkeypatch.setattr(testreg, "combine_sources", intersect)
    assert "tests/test_none.py" not in _sel_or_empty(r, ["momentum/a.py"], MUST)


def test_05b_previously_failed_adds_file(tmp_path):
    r = _repo(tmp_path)
    base = _sel(_impact(r, changed=["momentum/a.py"], must=MUST))
    assert "tests/test_d.py" not in base
    sel = _sel(_impact(r, changed=["momentum/a.py"], must=MUST, prev=["tests/test_d.py::test_d"]))
    assert "previously_failed" in sel["tests/test_d.py"]


def test_05c_helper_module_change_selects_importers(tmp_path):
    r = _repo(tmp_path)
    sel = _sel(_impact(r, changed=["tests/helpers/h.py"]))
    assert "tests/test_h.py" in sel and "static_taint" in sel["tests/test_h.py"]
    assert "tests/test_a.py" not in sel


def _manifest(rows: List[str]) -> Dict[str, Any]:
    return {"spec_path": "docs/X_SPEC.md", "test_files": [], "script_acceptance": [], "stub_modules": [],
            "contract_jsons": [], "run_receipts": [], "batch_card": {"gate_cmd": "x", "risk_mitigation": rows}}


def _cli(r: TmpRepo, manifest: Dict[str, Any], phase: int = 1) -> subprocess.CompletedProcess:
    r.write_json("docs/manifests/X.json", manifest)
    return r.run("impact", "--changed-from", "worktree", "--manifest", "docs/manifests/X.json", "--phase", str(phase))


def test_05d_must_tombstoned_cross_file_e1_resolved(tmp_path):
    files = dict(FILES)
    files["tests/test_dup.py"] = "def test_dup():\n    assert True\n"
    r = _repo(tmp_path, files)
    r.delete("tests/test_none.py")
    cat = r.catalog()
    cat["tombstones"].append({"nodeid": "tests/test_none.py::test_none", "evidence_level": "E1",
                              "evidence_receipt": "handoffs/run_receipts/testreg-retire/x.json",
                              "replaced_by": ["tests/test_dup.py::test_dup"],
                              "disposition_ref": "handoffs/reconcile/x/synth.md"})
    r.set_catalog(cat)
    assert testreg.must_from_manifest(r.root, _manifest(["affected_tests phase=1 tests/test_none.py",
                                                         "affected_must phase=1 tests/test_none.py::test_none"]), 1) == [
        "tests/test_dup.py::test_dup"]
    res = testreg.impact(r.root, [], ["tests/test_dup.py::test_dup"], [])
    sel, exc = _sel(res), _exc(res)
    assert "must" in sel["tests/test_dup.py"]
    assert "tests/test_none.py" not in sel and "tests/test_none.py" not in exc


def test_05e_manifest_groups_not_must(tmp_path):
    r = _repo(tmp_path)
    proc = _cli(r, _manifest(["affected_tests phase=1 tests/test_d.py tests/test_none.py",
                              "affected_groups phase=1 C=tests/test_d.py",
                              "affected_must phase=1 tests/test_none.py::test_none"]))
    assert proc.returncode == 0, proc.stderr
    sel = _sel(json.loads(proc.stdout))
    assert "must" in sel["tests/test_none.py"]
    assert "must" not in sel.get("tests/test_d.py", [])


def test_05f_anchor_worktree_repo_root(tmp_path):
    r = _repo(tmp_path)
    anchor = r.head()
    r.write("tests/test_late.py", "def test_late():\n    assert True\n")
    r.put_entry(entry("tests/test_late.py"))
    r.commit("late test")
    wt = tmp_path / "anchor_wt"
    r.git("worktree", "add", "--detach", str(wt), anchor)
    res = testreg.impact(wt, ["momentum/a.py"], [], [])
    universe = {x["path"] for x in res["selected"]} | {x["path"] for x in res["excluded"]}
    assert "tests/test_late.py" not in universe and universe == set(ALL_TESTS)
    res_main = testreg.impact(r.root, ["momentum/a.py"], [], [])
    assert "tests/test_late.py" in {x["path"] for x in res_main["selected"]} | {x["path"] for x in res_main["excluded"]}


def test_06_all_sources_empty_never_empty_selection(tmp_path):
    r = _repo(tmp_path)
    try:
        res = testreg.impact(r.root, [], [], [])
    except testreg.TestregError:
        return
    assert res["selected"]


def test_07_catalog_invalid_refuses(tmp_path):
    """SPEC v17：impact 之前置驗證＝catalog 自身之形狀與枚舉（V03／V05／V13／V16／V17）；不合 ⇒ 拒跑。
    未登記之測試檔（V02）不拒跑，依 registry_unresolved 選入（見 test_changed_test_and_unregistered_test）。"""
    r = _repo(tmp_path)
    cat = r.catalog()
    cat["entries"]["tests/test_a.py"]["oracle"] = ["NOPE"]
    r.set_catalog(cat)
    with pytest.raises(testreg.TestregError):
        testreg.impact(r.root, ["momentum/a.py"], [], [])


def test_changed_test_and_unregistered_test(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_new.py", "def test_new():\n    assert True\n")
    sel = _sel(_impact(r, changed=["tests/test_new.py", "tests/test_d.py"]))
    assert "registry_unresolved" in sel["tests/test_new.py"]
    assert "changed_test" in sel["tests/test_d.py"]


def test_excluded_reasons_are_enum(tmp_path):
    r = _repo(tmp_path)
    res = _impact(r, changed=["momentum/a.py"])
    from tests.registry.testreg_helpers import enum
    assert set(_exc(res).values()) <= set(enum("exclude_reason"))
    assert all(set(v) <= set(enum("select_reason")) for v in _sel(res).values())


# ── 邊界 ─────────────────────────────────────────────────────────────────────────────────────────────

def test_boundary_01_manifest_without_affected_tests_refuses(tmp_path):
    r = _repo(tmp_path)
    proc = _cli(r, _manifest(["affected_must phase=1 tests/test_none.py::test_none"]))
    assert proc.returncode != 0 and "affected_tests" in proc.stderr


def test_boundary_02_changed_file_fully_tombstoned_excluded_tombstoned(tmp_path):
    """SPEC v17：變更之測試檔仍存在而其測試函式皆已立碑（檔內已無測試函式）⇒ excluded＝tombstoned；
    已刪除之測試檔不入 selected／excluded。"""
    r = _repo(tmp_path)
    r.write("tests/test_d.py", "from momentum.core.d import dx  # noqa: F401\n")
    cat = r.catalog()
    cat["tombstones"].append({"nodeid": "tests/test_d.py::test_d", "evidence_level": "E0",
                              "evidence_receipt": "handoffs/run_receipts/testreg-retire/x.json", "replaced_by": [],
                              "disposition_ref": "handoffs/reconcile/x/synth.md"})
    cat["tombstones"].append({"nodeid": "tests/test_none.py::test_none", "evidence_level": "E0",
                              "evidence_receipt": "handoffs/run_receipts/testreg-retire/y.json", "replaced_by": [],
                              "disposition_ref": "handoffs/reconcile/x/synth.md"})
    r.set_catalog(cat)
    r.delete("tests/test_none.py")
    res = _impact(r, changed=["tests/test_d.py", "tests/test_none.py"])
    assert _exc(res)["tests/test_d.py"] == "tombstoned"
    assert "tests/test_none.py" not in _sel(res) and "tests/test_none.py" not in _exc(res)
