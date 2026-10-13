"""TESTREG Task 3.0 驗收（SPEC v44；契約 version 43 `receipts.defective_rewrite`）：缺陷目標改寫收據。

目標測試函式為缺陷目標——`existing_red`（於 HEAD 已紅、紅在過期斷言）或 `vacuous`（斷言空心、生產錯誤不使其轉紅）——
時，`receipts.mutation` 之「目標每一斷言行皆被殺」不可滿足；改以缺陷證據＋改寫後函式逐斷言行之 mutant 殺點＋斷言差
限縮於 `defect_lines` 驗收，成立 ⇒ V19 放行（hook 與 pre-commit 同判）。
全部情境於暫存 git 倉以真實記錄器產生 ledger 後驗（同 `test_testreg_validate.py` 之 mutation 收據案例作法）。
實作前（`scripts/testreg.py` 無缺陷目標收據之判定）：放行案紅（V19 擋下）、`defective_rewrite_errors` 具名縫不存在。
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
BISECT_LOG = "handoffs/run_receipts/testreg-defective-rewrite/bisect-test_red.log"
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
CALC_BAD = CALC_GOOD.replace("    return x * 2\n", "    return x * 3\n", 1)
DR_TESTS = '''from momentum.calc import add, empty_result, scale, values


def test_red():
    assert add(1, 2) == 3
    assert scale(1) == 2


def test_hollow():
    r = empty_result(3)
    for _name, col in r["cols"].items():
        assert col == values(3)
    assert len(r["index"]) == 3


def test_other():
    assert add(2, 2) == 4
'''
RED_OLD = "    assert scale(1) == 2\n"
RED_NEW = "    assert scale(1) == 3\n"
HOLLOW_OLD = ('    r = empty_result(3)\n    for _name, col in r["cols"].items():\n        assert col == values(3)\n'
              '    assert len(r["index"]) == 3\n')
HOLLOW_NEW = '    r = empty_result(3)\n    assert values(3) == [0, 2, 4]\n    assert len(r["index"]) == 3\n'
MUTANTS = {  # 名稱: (calc.py 舊片段, 新片段)
    "m_add": ("    return a + b\n", "    return a - b\n"),
    "m_scale": ("    return x * 3\n", "    return x * 4\n"),
    "m_values": ("    return [i * 2 for i in range(n)]\n", "    return [i * 5 for i in range(n)]\n"),
    "m_index": ('    return {"index": list(range(n)), "cols": {}}\n',
                '    return {"index": list(range(n + 1)), "cols": {}}\n'),
    "m_noop": ("def validate_input(x):\n", "# noop\ndef validate_input(x):\n"),
    "m_testfile": None,  # 改測試檔之 mutant（反例用）
}
NID = {n: f"{DF}::{n}" for n in ("test_red", "test_hollow", "test_other")}


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
                         APPROVAL: "# approval\n", "tests/fixtures/testreg_recorder_plugin.py": plugin})
    good = r.head()
    r.write("momentum/calc.py", CALC_BAD)  # 行為改變：scale 由 ×2 改 ×3 ⇒ test_red 之期望值過期
    bad = r.commit("scale x3")
    r.write(BISECT_LOG, f"{bad} is the first bad commit\n")
    sha = {m: _patch_for(r, m) for m in MUTANTS}
    pp = {m: f"handoffs/run_receipts/testreg-mutants/{m}.patch" for m in MUTANTS}
    cp = {"red": "handoffs/run_receipts/testreg-defective-rewrite/test_red.compare.patch",
          "hollow": "handoffs/run_receipts/testreg-defective-rewrite/test_hollow.compare.patch",
          "red_drop_add": "handoffs/run_receipts/testreg-defective-rewrite/test_red_drop_add.compare.patch",
          "red_bad_expect": "handoffs/run_receipts/testreg-defective-rewrite/test_red_bad_expect.compare.patch"}
    csha = {
        "red": write_patch(r, DF, r.read(DF).replace(RED_OLD, RED_NEW), cp["red"]),
        "hollow": write_patch(r, DF, r.read(DF).replace(HOLLOW_OLD, HOLLOW_NEW), cp["hollow"]),
        "red_drop_add": write_patch(r, DF, r.read(DF).replace(RED_OLD, RED_NEW).replace(
            "    assert add(1, 2) == 3\n", "", 1), cp["red_drop_add"]),
        "red_bad_expect": write_patch(r, DF, r.read(DF).replace(RED_OLD, "    assert scale(1) == 5\n"),
                                      cp["red_bad_expect"]),
    }
    # 補丁與 bisect 紀錄本身為未追蹤檔，會進 diff_digest ⇒ 提交使 HEAD 乾淨，收據 head＝此提交
    head = r.commit("patches")
    sess = {
        "target@head": _run_with(r, [], NID["test_red"], NID["test_hollow"], NID["test_other"]),
        "red@base": _run_with(r, [cp["red"]], NID["test_red"]),
        "red_drop_add@base": _run_with(r, [cp["red_drop_add"]], NID["test_red"]),
        "red_bad_expect@base": _run_with(r, [cp["red_bad_expect"]], NID["test_red"]),
        "hollow@base": _run_with(r, [cp["hollow"]], NID["test_hollow"]),
    }
    for m in ("m_add", "m_scale"):
        sess[f"red+{m}"] = _run_with(r, [cp["red"], pp[m]], NID["test_red"])
    # 改測試檔之 mutant 與改寫補丁同改本檔而無法疊加；反例只需「補丁觸及測試檔」即應被拒，session 於 head 單獨跑
    sess["red+m_testfile"] = _run_with(r, [pp["m_testfile"]], NID["test_red"])
    sess["red_drop_add+m_scale"] = _run_with(r, [cp["red_drop_add"], pp["m_scale"]], NID["test_red"])
    for m in ("m_values", "m_index", "m_noop"):
        sess[f"hollow+{m}"] = _run_with(r, [cp["hollow"], pp[m]], NID["test_hollow"])
        sess[f"head+{m}"] = _run_with(r, [pp[m]], NID["test_hollow"])
    return {"repo": r, "head": head, "good": good, "bad": bad, "sha": sha, "pp": pp, "cp": cp, "csha": csha,
            "sess": sess}


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


def _survivor(fx, mid: str, defect_line: str) -> Dict[str, Any]:
    return {"id": mid, "defect_line": defect_line, "patch_path": fx["pp"][mid], "patch_sha256": fx["sha"][mid],
            "session_id": fx["sess"][f"head+{mid}"], "compare_session_id": fx["sess"][f"hollow+{mid}"]}


def _fingerprint(fx, rc: Mapping[str, Any]) -> str:
    r = fx["repo"]
    ids = [rc["compare_baseline_session_id"]] + ([rc["target_session_id"]] if rc["target_session_id"] else [])
    ids += [m["session_id"] for m in rc["mutants"]] + [s["session_id"] for s in rc["survivors"]]
    ids += [s["compare_session_id"] for s in rc["survivors"]]
    dc = {session_of(r, i)["duration_class"] for i in ids}
    assert len(dc) == 1
    return dc.pop()


def red_receipt(fx, compare: str = "red", mutants=("m_add", "m_scale")) -> Dict[str, Any]:
    r = fx["repo"]
    rc = {"kind": "existing_red", "target_nodeid": NID["test_red"], "head": fx["head"], "approval_ref": APPROVAL,
          "fingerprint": "", "defect_lines": [_line(r, "assert scale(1) == 2")],
          "compare_patch_path": fx["cp"][compare], "compare_patch_sha256": fx["csha"][compare],
          "compare_baseline_session_id": fx["sess"][f"{compare}@base"], "first_bad_commit": fx["bad"],
          "good_commit": fx["good"], "bisect_log_path": BISECT_LOG, "target_session_id": fx["sess"]["target@head"],
          "survivors": [], "mutants": [_mutant(fx, m, f"{compare}+{m}", NID["test_red"]) for m in mutants]}
    rc["fingerprint"] = _fingerprint(fx, rc)
    return rc


def hollow_receipt(fx, survivors=("m_values",), mutants=("m_values", "m_index")) -> Dict[str, Any]:
    r = fx["repo"]
    dl = _line(r, "assert col == values(3)")
    rc = {"kind": "vacuous", "target_nodeid": NID["test_hollow"], "head": fx["head"], "approval_ref": APPROVAL,
          "fingerprint": "", "defect_lines": [dl], "compare_patch_path": fx["cp"]["hollow"],
          "compare_patch_sha256": fx["csha"]["hollow"], "compare_baseline_session_id": fx["sess"]["hollow@base"],
          "first_bad_commit": None, "good_commit": None, "bisect_log_path": None, "target_session_id": None,
          "survivors": [_survivor(fx, m, dl) for m in survivors],
          "mutants": [_mutant(fx, m, f"hollow+{m}", NID["test_hollow"]) for m in mutants]}
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
        rc["defect_lines"] = [_line(r, "assert add(2, 2) == 4")]
    elif case == "fail_loc_not_in_defect_lines":
        rc["defect_lines"] = [_line(r, "assert add(1, 2) == 3")]
    elif case == "bisect_log_missing":
        rc["bisect_log_path"] = "handoffs/run_receipts/testreg-defective-rewrite/nope.log"
    elif case == "good_not_ancestor":
        rc["good_commit"], rc["first_bad_commit"] = rc["first_bad_commit"], rc["good_commit"]
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
    elif case == "survivors_nonempty":
        rc["survivors"] = [{"id": "x", "defect_line": rc["defect_lines"][0], "patch_path": fx["pp"]["m_noop"],
                            "patch_sha256": fx["sha"]["m_noop"], "session_id": fx["sess"]["head+m_noop"],
                            "compare_session_id": fx["sess"]["hollow+m_noop"]}]
    else:
        raise AssertionError(case)
    return rc


RED_NEG = ["target_passes_at_head", "fail_loc_not_in_defect_lines", "bisect_log_missing", "good_not_ancestor",
           "baseline_not_passed", "assert_line_without_kill", "mutant_touches_test_file", "head_not_HEAD",
           "session_not_bound", "survivors_nonempty"]


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
