"""TESTREG Task 3.0 驗收（SPEC v45；契約 version 44 `receipts.defective_rewrite`）：既有紅改寫收據。

目標測試函式於 HEAD 已紅、紅在期望值已過期之斷言（kind=existing_red）時，`receipts.mutation` 之「目標每一斷言行皆被殺」
不可滿足；改以好壞兩提交與 HEAD 之記錄器 session 證據＋改寫只改該斷言內之字面常數（AST 同構）＋改寫後函式逐斷言行之
mutant 殺點驗收，成立 ⇒ V19 放行（hook 與 pre-commit 同判）。全部情境於暫存 git 倉以真實記錄器產生 ledger 後驗。

v45 沿革（修訂審查 r43）：v44 之 `vacuous` 型刪除。本檔 v44 之函式本體逐字保留（V19／V20：已提交之測試函式不得減少斷言
或刪改名），其語意經模組常數與無斷言之輔助函式改為 v45：暫存倉之 `test_hollow` 改為第二個既有紅目標（`values` 之期望值
過期），`hollow_receipt` 產該目標之 existing_red 收據，其 `survivors` 參數改作反例選擇（見該函式說明）；v45 新反例以新增
函式補（`test_v45_*`）。
"""
from __future__ import annotations

import copy
import importlib
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pytest

from tests.registry.testreg_helpers import (
    REPO, TmpRepo, entry, lines_with, make_repo, recorded_pytest, schema, session_of, test_records, write_patch,
)

testreg = importlib.import_module("scripts.testreg")

DF = "tests/test_dr.py"
APPROVAL = "handoffs/reconcile/dr/synth.md"
APPROVAL_PLAIN = "handoffs/reconcile/dr/plain.md"  # 無交叉引用之裁定檔（反例）
CALC_GOOD = '''def add(a, b):
    return a + b


def scale(x):
    return x * 2


def values(n):
    return [i * 2 for i in range(n)]


def empty_result(n):
    """仿生成回傳表：只帶索引、不帶欄。"""
    return {"index": list(range(n)), "cols": {}}


def validate_input(x):
    return x
'''
# 首個壞提交同時改 scale（×2→×3）與 values（i*2→i*3）⇒ test_red、test_hollow 之期望值皆過期（兩個既有紅目標）
CALC_BAD = CALC_GOOD.replace("    return x * 2\n", "    return x * 3\n", 1).replace(
    "    return [i * 2 for i in range(n)]\n", "    return [i * 3 for i in range(n)]\n", 1)
DR_TESTS = '''from momentum.calc import add, empty_result, scale, values


def test_red():
    x = 1
    assert add(1, 2) == 3
    assert scale(x) == 2
    assert add(2, 2) == 4


def test_hollow():
    r = empty_result(3)
    assert values(3) == [0, 2, 4]
    assert len(r["index"]) == 3


def test_vac():
    r = empty_result(3)
    for _name, col in r["cols"].items():
        assert col == values(3)
    assert len(r["index"]) == 3


def test_dup():
    assert add(1, 1) == 2
    assert scale(1) == 2
    assert add(1, 1) == 2


def test_helper_red():
    _check_scale()


def test_other():
    assert add(2, 2) == 4


def _check_scale():
    assert scale(1) == 2
'''
RED_OLD = "    assert scale(x) == 2\n"
RED_NEW = "    assert scale(x) == 3\n"
HOLLOW_OLD = "    assert values(3) == [0, 2, 4]\n"
HOLLOW_NEW = "    assert values(3) == [0, 3, 6]\n"
SETUP_OLD, SETUP_NEW = "    x = 1\n", "    x = abs(1)\n"  # 改 setup（非字面）
DUP_OLD = "    assert scale(1) == 2\n    assert add(1, 1) == 2\n"
DUP_NEW = "    assert scale(1) == 3\n"  # 修過期字面並刪重複斷言
HELPER_OLD = "def _check_scale():\n    assert scale(1) == 2\n"
HELPER_NEW = "def _check_scale():\n    assert scale(1) == 3\n"
VAC_OLD = '    r = empty_result(3)\n    for _name, col in r["cols"].items():'
VAC_NEW = '    r = {"index": [0, 1, 2], "cols": {"v": values(3)}}\n    for _name, col in r["cols"].items():'
MUTANTS = {  # 名稱: (calc.py〔首個壞提交後〕舊片段, 新片段)
    "m_add": ("    return a + b\n", "    return a - b\n"),
    "m_add22": ("    return a + b\n", "    return a + b + (1 if (a, b) == (2, 2) else 0)\n"),
    "m_scale": ("    return x * 3\n", "    return x * 4\n"),
    "m_values": ("    return [i * 3 for i in range(n)]\n", "    return [i * 5 for i in range(n)]\n"),
    "m_index": ('    return {"index": list(range(n)), "cols": {}}\n',
                '    return {"index": list(range(n + 1)), "cols": {}}\n'),
    "m_noop": ("def validate_input(x):\n", "# noop\ndef validate_input(x):\n"),
    "m_testfile": None,  # 改測試檔之 mutant（反例用）
}
NID = {n: f"{DF}::{n}" for n in ("test_red", "test_hollow", "test_vac", "test_dup", "test_helper_red", "test_other")}


def receipt_rel(nodeid: str) -> str:
    """獨立 oracle：依契約 receipts.defective_rewrite.file_rule（`/`→`__`、`::`→`--`）。"""
    d = schema()["receipts"]["defective_rewrite"]["dir"]
    return f"{d}/{nodeid.replace('/', '__').replace('::', '--')}.json"


def _patch_for(r: TmpRepo, mid: str) -> str:
    rel = f"handoffs/run_receipts/testreg-mutants/{mid}.patch"
    if mid == "m_testfile":
        return write_patch(r, DF, r.read(DF).replace("assert add(1, 2) == 3", "assert add(1, 2) == 4", 1), rel)
    old, new = MUTANTS[mid]
    assert old in r.read("momentum/calc.py"), mid
    return write_patch(r, "momentum/calc.py", r.read("momentum/calc.py").replace(old, new, 1), rel)


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
def dr_base(tmp_path_factory) -> Dict[str, Any]:
    root = tmp_path_factory.mktemp("dr")
    plugin = (REPO / "tests/fixtures/testreg_recorder_plugin.py").read_text(encoding="utf-8")
    r = make_repo(root, {"momentum/__init__.py": "", "momentum/calc.py": CALC_GOOD, DF: DR_TESTS,
                         "tests/fixtures/testreg_recorder_plugin.py": plugin})
    good = r.head()
    r.write("momentum/calc.py", CALC_BAD)  # 行為改變 ⇒ test_red、test_hollow、test_dup、test_helper_red 之期望值過期
    bad = r.commit("scale x3, values i*3")
    # 裁定檔須交叉引用目標 nodeid 與首個壞提交前 8 碼（契約 rule）；另一份不含交叉引用者供反例
    r.write(APPROVAL, f"# approval\n{NID['test_red']} {NID['test_hollow']} {NID['test_dup']} "
                      f"{NID['test_helper_red']} first bad {bad[:8]}\n")
    r.write(APPROVAL_PLAIN, "# approval without cross reference\n")
    sha = {m: _patch_for(r, m) for m in MUTANTS}
    pp = {m: f"handoffs/run_receipts/testreg-mutants/{m}.patch" for m in MUTANTS}
    d = "handoffs/run_receipts/testreg-defective-rewrite"
    cp = {k: f"{d}/{k}.compare.patch" for k in
          ("red", "hollow", "red_drop_add", "red_bad_expect", "red_setup", "dup", "helper")}
    src = r.read(DF)
    csha = {
        "red": write_patch(r, DF, src.replace(RED_OLD, RED_NEW), cp["red"]),
        "hollow": write_patch(r, DF, src.replace(HOLLOW_OLD, HOLLOW_NEW), cp["hollow"]),
        "red_drop_add": write_patch(r, DF, src.replace(RED_OLD, RED_NEW).replace(
            "    assert add(1, 2) == 3\n", "", 1), cp["red_drop_add"]),
        "red_bad_expect": write_patch(r, DF, src.replace(RED_OLD, "    assert scale(x) == 5\n"), cp["red_bad_expect"]),
        "red_setup": write_patch(r, DF, src.replace(RED_OLD, RED_NEW).replace(SETUP_OLD, SETUP_NEW, 1), cp["red_setup"]),
        "dup": write_patch(r, DF, src.replace(DUP_OLD, DUP_NEW, 1), cp["dup"]),
        "helper": write_patch(r, DF, src.replace(HELPER_OLD, HELPER_NEW, 1), cp["helper"]),
    }
    # 補丁與裁定檔本身為未追蹤檔，會進 diff_digest ⇒ 提交使 HEAD 乾淨，收據 head＝此提交
    head = r.commit("patches")
    branch = r.git("rev-parse", "--abbrev-ref", "HEAD").strip()
    sess = {
        "v44@head": _run_with(r, [], NID["test_red"], NID["test_hollow"], NID["test_other"]),  # v44 呼叫逐字保留（V19）
        "red@base": _run_with(r, [cp["red"]], NID["test_red"]),
        "red_drop_add@base": _run_with(r, [cp["red_drop_add"]], NID["test_red"]),
        "red_bad_expect@base": _run_with(r, [cp["red_bad_expect"]], NID["test_red"]),
        "hollow@base": _run_with(r, [cp["hollow"]], NID["test_hollow"]),
    }
    for m in ("m_add", "m_scale", "m_add22"):
        sess[f"red+{m}"] = _run_with(r, [cp["red"], pp[m]], NID["test_red"])
    # 改測試檔之 mutant 與改寫補丁同改本檔而無法疊加；反例只需「補丁觸及測試檔」即應被拒，session 於 head 單獨跑
    sess["red+m_testfile"] = _run_with(r, [pp["m_testfile"]], NID["test_red"])
    sess["red_drop_add+m_scale"] = _run_with(r, [cp["red_drop_add"], pp["m_scale"]], NID["test_red"])
    for m in ("m_values", "m_index", "m_noop"):
        sess[f"hollow+{m}"] = _run_with(r, [cp["hollow"], pp[m]], NID["test_hollow"])
        sess[f"head+{m}"] = _run_with(r, [pp[m]], NID["test_hollow"])
    # v45 新增；target@head 刻意不含 test_hollow（hollow 之 target session 另跑；反例「以他 session 冒充」據此成立）
    sess["target@head"] = _run_with(r, [], NID["test_red"], NID["test_dup"], NID["test_helper_red"], NID["test_other"])
    sess["hollow@head"] = _run_with(r, [], NID["test_hollow"], NID["test_vac"])
    for k in ("red_setup", "dup", "helper"):
        sess[f"{k}@base"] = _run_with(r, [cp[k]], NID["test_red"], NID["test_dup"], NID["test_helper_red"])
    # 好壞兩提交之乾淨樹 session（記錄器以 -p 注入；兩提交樹中皆已有該外掛檔）
    for name, rev in (("good", good), ("bad", bad)):
        r.git("checkout", "-q", "--detach", rev)
        try:
            sess[name] = _run_with(r, [], NID["test_red"], NID["test_hollow"])
        finally:
            r.git("checkout", "-q", branch)
    # 非 head 祖先之「首個壞提交」：自 good 分出之另一分支提交（第一親代＝good）
    r.git("checkout", "-q", "-b", "fbside", good)
    r.write("README", "side\n")
    side = r.commit("side")
    r.git("checkout", "-q", branch)
    return {"repo": r, "head": head, "good": good, "bad": bad, "side": side, "sha": sha, "pp": pp, "cp": cp,
            "csha": csha, "sess": sess}


def _fail_loc(rec: Mapping[str, Any]) -> Optional[str]:
    hits = [f for f in rec.get("fail_frames", []) if f.split(":")[0] == DF]
    return hits[0] if hits else None


def _line(r: TmpRepo, needle: str, nth: int = 0) -> str:
    return f"{DF}:{lines_with(r, DF, needle)[nth]}"


def _mutant(fx, mid: str, sess_key: str, nodeid: str) -> Dict[str, Any]:
    rec = test_records(fx["repo"], fx["sess"][sess_key])[nodeid]
    return {"id": mid, "patch_path": fx["pp"][mid], "patch_sha256": fx["sha"][mid],
            "session_id": fx["sess"][sess_key], "compare_session_id": fx["sess"][sess_key],
            "target_outcome": rec["outcome"], "target_fail_loc": _fail_loc(rec),
            "compare_outcomes": {nodeid: rec["outcome"]}}


def _fingerprint(fx, rc: Mapping[str, Any]) -> str:
    r = fx["repo"]
    ids = [rc[k] for k in ("compare_baseline_session_id", "target_session_id", "good_session_id", "bad_session_id")
           if rc.get(k)]
    ids += [m["session_id"] for m in rc["mutants"]]
    dc = {session_of(r, i)["duration_class"] for i in ids}
    assert len(dc) == 1
    return dc.pop()


def _receipt(fx, target: str, defect_needle: str, compare: str, mutants, target_sess: str, nth: int = 0,
             mut_sess: str = None) -> Dict[str, Any]:
    """v45 existing_red 收據（成立形）：目標、單一缺陷斷言、改寫補丁、好壞兩提交與 head 之 session、殺 mutant。
    mut_sess 給定時，各 mutant 之紀錄一律取自該 session（只供反例：收據本即不成立，mutant 內容不影響結論）。"""
    r = fx["repo"]
    return {"kind": "existing_red", "target_nodeid": NID[target], "head": fx["head"], "approval_ref": APPROVAL,
            "fingerprint": "", "defect_lines": [_line(r, defect_needle, nth)],
            "compare_patch_path": fx["cp"][compare], "compare_patch_sha256": fx["csha"][compare],
            "compare_baseline_session_id": fx["sess"][f"{compare}@base"], "first_bad_commit": fx["bad"],
            "good_commit": fx["good"], "target_session_id": fx["sess"][target_sess],
            "good_session_id": fx["sess"]["good"], "bad_session_id": fx["sess"]["bad"],
            "mutants": [_mutant(fx, m, mut_sess or f"{compare}+{m}", NID[target]) for m in mutants]}


def red_receipt(fx, compare: str = "red", mutants=("m_add", "m_scale", "m_add22")) -> Dict[str, Any]:
    rc = _receipt(fx, "test_red", "assert scale(x) == 2", compare, mutants, "target@head")
    rc["fingerprint"] = _fingerprint(fx, rc)
    return rc


def hollow_receipt(fx, survivors=None, mutants=("m_values", "m_index")) -> Dict[str, Any]:
    """v45：第二個既有紅目標 test_hollow（`values` 期望值過期）之 existing_red 收據。

    參數 `survivors` 沿 v44 名稱（v44 函式本體逐字保留之故），v45 改作反例選擇：
    ("m_index",) ⇒ defect_lines 改指未失敗之 `len(r["index"])` 斷言（缺陷須為 head 失敗所在）；
    ("m_noop",) ⇒ good_session_id 改用 first_bad 之 session（不綁定 good 提交）；None ⇒ 成立形。"""
    rc = _receipt(fx, "test_hollow", "assert values(3) == [0, 2, 4]", "hollow", mutants, "hollow@head")
    if survivors == ("m_index",):
        rc["defect_lines"] = [_line(fx["repo"], 'assert len(r["index"]) == 3')]
    elif survivors == ("m_noop",):
        rc["good_session_id"] = fx["sess"]["bad"]
    rc["fingerprint"] = _fingerprint(fx, rc)
    return rc


def _work(fx, tmp_path: Path, name: str) -> TmpRepo:
    """每案於基底倉之複本操作（不污染 module 級 fixture）；ledger 隨複本。"""
    import shutil
    dst = tmp_path / name
    shutil.copytree(fx["repo"].root, dst, symlinks=True)
    return TmpRepo(dst)


def _apply_rewrite(r: TmpRepo, which: str) -> None:
    src = r.read(DF)
    if which == "red":
        r.write(DF, src.replace(RED_OLD, RED_NEW))
    elif which == "red_drop_add":
        r.write(DF, src.replace(RED_OLD, RED_NEW).replace("    assert add(1, 2) == 3\n", "", 1))
    elif which == "hollow":
        r.write(DF, src.replace(HOLLOW_OLD, HOLLOW_NEW))
    elif which == "red_setup":
        r.write(DF, src.replace(RED_OLD, RED_NEW).replace(SETUP_OLD, SETUP_NEW, 1))
    elif which == "dup":
        r.write(DF, src.replace(DUP_OLD, DUP_NEW, 1))
    elif which == "helper":
        r.write(DF, src.replace(HELPER_OLD, HELPER_NEW, 1))
    elif which == "vac":
        r.write(DF, src.replace(VAC_OLD, VAC_NEW, 1))
    else:
        raise AssertionError(which)


def _v19(stderr: str) -> set:
    return {l.split(" ", 1)[1].split(": ", 1)[0] for l in stderr.splitlines() if l.startswith("V19 ")}


def _hook_and_commit(r: TmpRepo, rels: List[str]) -> tuple:
    r.install_precommit()
    hook = r.hook(DF)
    r.stage(DF, *rels)
    return hook, r.try_commit()


# ── (a) existing_red ────────────────────────────────────────────────────────────────────────────────────────────

def test_a_existing_red_valid_receipt_releases_v19(dr_base, tmp_path):
    """目標於 HEAD 因過期期望值紅 → 改期望值、附成立之收據 ⇒ hook 與 pre-commit 皆 rc 0；無收據 ⇒ V19 擋下該 nodeid。"""
    r = _work(dr_base, tmp_path, "ok")
    _apply_rewrite(r, "red")
    blocked = r.hook(DF)
    assert blocked.returncode == 2 and _v19(blocked.stderr) == {NID["test_red"]}, blocked.stderr
    r.write_json(receipt_rel(NID["test_red"]), red_receipt(dr_base))
    hook, proc = _hook_and_commit(r, [receipt_rel(NID["test_red"])])
    assert hook.returncode == 0, hook.stderr
    assert proc.returncode == 0, proc.stderr


def _red_neg(fx, case: str) -> Dict[str, Any]:
    rc = red_receipt(fx)
    r = fx["repo"]
    if case == "target_passes_at_head":
        rc["target_nodeid"] = NID["test_other"]
        rc["defect_lines"] = [_line(r, "assert add(2, 2) == 4", 1)]
    elif case == "fail_loc_not_in_defect_lines":
        rc["defect_lines"] = [_line(r, "assert add(1, 2) == 3")]
    elif case == "first_bad_not_head_ancestor":
        rc["first_bad_commit"] = fx["side"]  # 第一親代仍為 good，但不在 head 之歷史上
    elif case == "good_not_first_parent":
        rc["good_commit"] = fx["head"]
    elif case == "good_session_unbound":
        rc["good_session_id"] = fx["sess"]["bad"]
    elif case == "bad_session_unbound":
        rc["bad_session_id"] = fx["sess"]["good"]
    elif case == "target_session_unbound":
        rc["target_session_id"] = fx["sess"]["red@base"]
    elif case == "approval_no_crossref":
        rc["approval_ref"] = APPROVAL_PLAIN
    elif case == "kind_vacuous":
        rc["kind"] = "vacuous"
    elif case == "baseline_not_passed":
        rc = red_receipt(fx, compare="red_bad_expect", mutants=())  # 改寫後期望值仍錯
        rc["mutants"] = red_receipt(fx)["mutants"]
    elif case == "assert_line_without_kill":
        rc = red_receipt(fx, mutants=("m_scale",))
    elif case == "mutant_touches_test_file":
        rc["mutants"].append(_mutant(fx, "m_testfile", "red+m_testfile", NID["test_red"]))
    elif case == "head_not_HEAD":
        rc["head"] = fx["good"]
    elif case == "session_not_bound":
        rc["compare_baseline_session_id"] = fx["sess"]["target@head"]
    else:
        raise AssertionError(case)
    return rc


# v45 反例集（v44 之 bisect_log_missing／good_not_ancestor／survivors_nonempty 隨契約刪欄而改為下列可機驗條件）
RED_NEG = ["target_passes_at_head", "fail_loc_not_in_defect_lines", "first_bad_not_head_ancestor",
           "good_not_first_parent", "good_session_unbound", "bad_session_unbound", "target_session_unbound",
           "approval_no_crossref", "kind_vacuous", "baseline_not_passed", "assert_line_without_kill",
           "mutant_touches_test_file", "head_not_HEAD", "session_not_bound"]


@pytest.mark.parametrize("case", RED_NEG)
def test_a_existing_red_negatives_block(dr_base, tmp_path, case):
    """收據任一條件不成立 ⇒ hook 與 pre-commit 皆以 V19 擋下 test_red，訊息含「缺陷目標改寫收據不成立」。"""
    r = _work(dr_base, tmp_path, case)
    _apply_rewrite(r, "red")
    rc = _red_neg(dr_base, case)
    rel = receipt_rel(rc["target_nodeid"]) if case != "target_passes_at_head" else receipt_rel(NID["test_red"])
    r.write_json(rel, rc)
    hook, proc = _hook_and_commit(r, [rel])
    assert hook.returncode == 2 and NID["test_red"] in _v19(hook.stderr), hook.stderr
    assert "缺陷目標改寫收據不成立" in hook.stderr or case == "target_passes_at_head", hook.stderr
    assert proc.returncode != 0 and _v19(proc.stderr) == _v19(hook.stderr), proc.stderr


def test_a_assert_diff_outside_defect_lines_blocks(dr_base, tmp_path):
    """斷言差限縮：改寫另刪一個非缺陷斷言（`add(1, 2) == 3`）⇒ 即使該改寫後函式可證偽，仍擋下。"""
    r = _work(dr_base, tmp_path, "drop")
    _apply_rewrite(r, "red_drop_add")
    rc = red_receipt(dr_base, compare="red_drop_add", mutants=("m_scale",))
    r.write_json(receipt_rel(NID["test_red"]), rc)
    hook, proc = _hook_and_commit(r, [receipt_rel(NID["test_red"])])
    assert hook.returncode == 2 and "缺陷目標改寫收據不成立" in hook.stderr, hook.stderr
    assert proc.returncode != 0


def test_a_compare_patch_touching_other_file_blocks(dr_base, tmp_path):
    """compare_patch 所及之檔須恰為目標所在測試檔：以一個改 calc.py 之補丁冒充 ⇒ 擋下。"""
    r = _work(dr_base, tmp_path, "cpother")
    _apply_rewrite(r, "red")
    rc = red_receipt(dr_base)
    rc["compare_patch_path"], rc["compare_patch_sha256"] = dr_base["pp"]["m_noop"], dr_base["sha"]["m_noop"]
    r.write_json(receipt_rel(NID["test_red"]), rc)
    hook = r.hook(DF)
    assert hook.returncode == 2 and "缺陷目標改寫收據不成立" in hook.stderr, hook.stderr


# ── (b) vacuous ─────────────────────────────────────────────────────────────────────────────────────────────────

def test_b_vacuous_valid_receipt_releases_v19(dr_base, tmp_path):
    """目標以空表比對恆綠（survivor m_values 下仍 passed）→ 改讀實值、附成立之收據 ⇒ hook 與 pre-commit 皆 rc 0。"""
    r = _work(dr_base, tmp_path, "vok")
    _apply_rewrite(r, "hollow")
    blocked = r.hook(DF)
    assert blocked.returncode == 2 and _v19(blocked.stderr) == {NID["test_hollow"]}, blocked.stderr
    r.write_json(receipt_rel(NID["test_hollow"]), hollow_receipt(dr_base))
    hook, proc = _hook_and_commit(r, [receipt_rel(NID["test_hollow"])])
    assert hook.returncode == 0, hook.stderr
    assert proc.returncode == 0, proc.stderr


VAC_NEG = {
    "survivor_kills_target": dict(survivors=("m_index",)),  # 索引改變 ⇒ 舊函式之 len 斷言紅 ⇒ 非空心證據
    "survivor_compare_still_passes": dict(survivors=("m_noop",)),
    "assert_line_without_kill": dict(mutants=("m_values",)),
}


@pytest.mark.parametrize("case", sorted(VAC_NEG) + ["defect_line_without_survivor", "red_fields_present"])
def test_b_vacuous_negatives_block(dr_base, tmp_path, case):
    r = _work(dr_base, tmp_path, case)
    _apply_rewrite(r, "hollow")
    if case in VAC_NEG:
        rc = hollow_receipt(dr_base, **VAC_NEG[case])
    else:
        rc = hollow_receipt(dr_base)
        if case == "defect_line_without_survivor":
            rc["defect_lines"].append(_line(dr_base["repo"], 'assert len(r["index"]) == 3'))
        else:
            rc["target_session_id"] = dr_base["sess"]["target@head"]
    r.write_json(receipt_rel(NID["test_hollow"]), rc)
    hook, proc = _hook_and_commit(r, [receipt_rel(NID["test_hollow"])])
    assert hook.returncode == 2 and "缺陷目標改寫收據不成立" in hook.stderr, hook.stderr
    assert proc.returncode != 0


# ── (d) V21 與具名縫 ─────────────────────────────────────────────────────────────────────────────────────────────

def test_d_v21_accepts_defective_receipts(dr_base, tmp_path):
    """disposition=rewrite、rewrite_receipt=null，而 rewrite_targets 每一 nodeid 皆有成立之缺陷目標改寫收據
    ⇒ `validate --require-executed` rc 0；刪去其一 ⇒ rc≠0 且有 V21 列。"""
    r = _work(dr_base, tmp_path, "v21")
    _apply_rewrite(r, "red")
    src = r.read(DF).replace(HOLLOW_OLD, HOLLOW_NEW)
    r.write(DF, src)
    r.write_json(receipt_rel(NID["test_red"]), red_receipt(dr_base))
    r.write_json(receipt_rel(NID["test_hollow"]), hollow_receipt(dr_base))
    r.put_entry(entry(DF, disposition="rewrite", rewrite_targets=[NID["test_red"], NID["test_hollow"]],
                      disposition_ref=APPROVAL, rewrite_receipt=None))
    ok = r.run("validate", "--require-executed")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    r.delete(receipt_rel(NID["test_hollow"]))
    bad = r.run("validate", "--require-executed")
    assert bad.returncode != 0 and any(l.startswith("V21") for l in (bad.stdout + bad.stderr).splitlines())


def test_d_v21_existing_receipt_after_head_advances(dr_base, tmp_path):
    """head 判定同 receipts.mutation：改寫與收據提交後 HEAD 再前進一個無關提交，既有收據之 head 為 HEAD 之祖先
    ⇒ `validate --require-executed` 仍 rc 0；把收據之 head 改為非祖先（另一分支提交）⇒ rc≠0。"""
    r = _work(dr_base, tmp_path, "v21adv")
    _apply_rewrite(r, "red")
    r.write_json(receipt_rel(NID["test_red"]), red_receipt(dr_base))
    r.put_entry(entry(DF, disposition="rewrite", rewrite_targets=[NID["test_red"]], disposition_ref=APPROVAL,
                      rewrite_receipt=None))
    r.commit("rewrite with defective receipt")
    r.write("README", "x\n")
    r.commit("unrelated")
    ok = r.run("validate", "--require-executed")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    r.git("checkout", "-q", "-b", "side", dr_base["good"])
    side = r.commit("side")
    r.git("checkout", "-q", "-")
    rc = json.loads(r.read(receipt_rel(NID["test_red"])))
    rc["head"] = side
    r.write_json(receipt_rel(NID["test_red"]), rc)
    r.commit("receipt head not ancestor")
    bad = r.run("validate", "--require-executed")
    assert bad.returncode != 0, bad.stdout + bad.stderr


def test_d_named_seam_exists_and_returns_none_without_receipt(dr_base, tmp_path):
    """具名縫 `defective_rewrite_errors(ctx, nodeid)`：無收據 ⇒ None（同 `literal_fix_errors` 之約定）。"""
    assert callable(getattr(testreg, "defective_rewrite_errors", None))


def test_mutation_receipt_condition_always_true_lets_negative_through(dr_base, tmp_path, monkeypatch):
    """mutant：`defective_rewrite_errors` 恆回 []（任一條件恆真）⇒ 原應擋下之反例（斷言差含非缺陷斷言）被放行——
    證 (a) 之反例依賴該判定。以行程內 `testreg.main` 執行 check，monkeypatch 置換具名縫。"""
    r = _work(dr_base, tmp_path, "mut")
    _apply_rewrite(r, "red_drop_add")
    r.write_json(receipt_rel(NID["test_red"]), red_receipt(dr_base, compare="red_drop_add", mutants=("m_scale",)))
    monkeypatch.setattr(testreg, "defective_rewrite_errors", lambda ctx, nodeid: [])
    rc = testreg.main(["--repo", str(r.root), "check", "--paths", DF])
    assert rc == 0


# ── (e) 秒級 ────────────────────────────────────────────────────────────────────────────────────────────────────

def test_e_receipt_release_timing(dr_base, tmp_path):
    """附成立收據之放行判定（hook）3 次中位 < 5 s（§C 必擋層門檻；收據驗證含 session 重算）。"""
    r = _work(dr_base, tmp_path, "t")
    _apply_rewrite(r, "red")
    r.write_json(receipt_rel(NID["test_red"]), red_receipt(dr_base))
    secs = []
    for _ in range(3):
        t0 = time.perf_counter()
        proc = r.hook(DF)
        secs.append(time.perf_counter() - t0)
        assert proc.returncode == 0, proc.stderr
    assert statistics.median(secs) < 5.0, secs


# ── v45 新增（修訂審查 r43 處置）──────────────────────────────────────────────────────────────────────────────────

def _blocked_with(fx, tmp_path, name: str, which: str, target: str, rc: Mapping[str, Any], reason: str) -> None:
    """套改寫 which、寫目標之收據 rc ⇒ hook 與 pre-commit 皆以 V19 擋下目標，且 hook 訊息含收據不成立與具體理由。"""
    r = _work(fx, tmp_path, name)
    _apply_rewrite(r, which)
    rel = receipt_rel(NID[target])
    r.write_json(rel, rc)
    hook, proc = _hook_and_commit(r, [rel])
    assert hook.returncode == 2 and NID[target] in _v19(hook.stderr), hook.stderr
    assert "缺陷目標改寫收據不成立" in hook.stderr and reason in hook.stderr, hook.stderr
    assert proc.returncode != 0 and _v19(proc.stderr) == _v19(hook.stderr), proc.stderr


def test_v45_two_defect_lines_piggyback_blocks(dr_base, tmp_path):
    """夾帶：把未失敗之 `add(1, 2) == 3` 一併登入 defect_lines 並同提交刪除 ⇒ 擋下（defect_lines 須恰一項）。"""
    rc = red_receipt(dr_base, compare="red_drop_add", mutants=("m_scale",))
    rc["defect_lines"] = [_line(dr_base["repo"], "assert add(1, 2) == 3"), rc["defect_lines"][0]]
    _blocked_with(dr_base, tmp_path, "piggy", "red_drop_add", "test_red", rc, "恰一項")


def test_v45_setup_change_blocks(dr_base, tmp_path):
    """改 setup（`x = 1` → `x = abs(1)`）並修過期字面 ⇒ 擋下（只准改缺陷斷言內之字面常數）。"""
    rc = _receipt(dr_base, "test_red", "assert scale(x) == 2", "red_setup", ("m_scale",), "target@head",
                  mut_sess="red_setup@base")
    rc["fingerprint"] = _fingerprint(dr_base, rc)
    _blocked_with(dr_base, tmp_path, "setup", "red_setup", "test_red", rc, "字面常數")


def test_v45_duplicate_assertion_deletion_blocks(dr_base, tmp_path):
    """修過期字面並刪除一個重複之 `add(1, 1) == 2` ⇒ 擋下（AST 須同構）。"""
    rc = _receipt(dr_base, "test_dup", "assert scale(1) == 2", "dup", ("m_add", "m_scale"), "target@head", 0,
                  mut_sess="target@head")
    rc["fingerprint"] = _fingerprint(dr_base, rc)
    _blocked_with(dr_base, tmp_path, "dup", "dup", "test_dup", rc, "字面常數")


def test_v45_defect_in_helper_blocks(dr_base, tmp_path):
    """過期斷言位於測試模組內 helper（`_check_scale`）⇒ 不適用本收據、擋下（缺陷須位於目標函式本體）。"""
    rc = _receipt(dr_base, "test_helper_red", "assert scale(1) == 2", "helper", ("m_scale",), "target@head", 1,
                  mut_sess="target@head")
    rc["fingerprint"] = _fingerprint(dr_base, rc)
    _blocked_with(dr_base, tmp_path, "helper", "helper", "test_helper_red", rc, "本體")


@pytest.mark.parametrize("case,reason", [
    ("fail_loc_not_in_defect_lines", "失敗位置"), ("first_bad_not_head_ancestor", "祖先"),
    ("good_not_first_parent", "第一親代"), ("good_session_unbound", "good 之 session"),
    ("bad_session_unbound", "bad 之 session"), ("target_session_unbound", "target 之 session"),
    ("approval_no_crossref", "approval_ref"), ("kind_vacuous", "kind"),
])
def test_v45_negatives_name_specific_reason(dr_base, tmp_path, case, reason):
    """各反例之 hook 訊息含其具體理由（不只「不成立」）。"""
    _blocked_with(dr_base, tmp_path, case, "red", "test_red", _red_neg(dr_base, case), reason)


def test_v45_hollow_source_change_without_receipt_passes(dr_base, tmp_path):
    """空心測試（迴圈迭代空集合）改上游比較對象之資料來源、原斷言保留 ⇒ 斷言多重集合不減，無收據亦 hook 與
    pre-commit 皆 rc 0（v45：空心測試不適用本收據）。"""
    r = _work(dr_base, tmp_path, "vac")
    _apply_rewrite(r, "vac")
    hook, proc = _hook_and_commit(r, [])
    assert hook.returncode == 0, hook.stderr
    assert proc.returncode == 0, proc.stderr


def test_v45_rewrite_ok_precedence_inprocess(dr_base, tmp_path, monkeypatch):
    """`_rewrite_ok` 為真（既有 rewrite 收據成立）時不呼叫 `defective_rewrite_errors` 即放行（行程內 monkeypatch）。"""
    r = _work(dr_base, tmp_path, "prec")
    _apply_rewrite(r, "red")
    calls = []
    monkeypatch.setattr(testreg, "_rewrite_ok", lambda ctx, nodeid: True)
    monkeypatch.setattr(testreg, "defective_rewrite_errors", lambda ctx, nodeid: calls.append(nodeid) or ["x"])
    assert testreg.main(["--repo", str(r.root), "check", "--paths", DF]) == 0
    assert calls == []


def test_v45_named_seam_none_without_receipt_and_empty_when_valid(dr_base, tmp_path):
    """具名縫（真實 Context）：無收據 ⇒ None；成立之收據 ⇒ []；不成立 ⇒ 非空清單。"""
    r = _work(dr_base, tmp_path, "seam")
    _apply_rewrite(r, "red")
    assert testreg.defective_rewrite_errors(testreg.build_context(r.root), NID["test_red"]) is None
    r.write_json(receipt_rel(NID["test_red"]), red_receipt(dr_base))
    assert testreg.defective_rewrite_errors(testreg.build_context(r.root), NID["test_red"]) == []
    r.write_json(receipt_rel(NID["test_red"]), _red_neg(dr_base, "approval_no_crossref"))
    assert testreg.defective_rewrite_errors(testreg.build_context(r.root), NID["test_red"])
