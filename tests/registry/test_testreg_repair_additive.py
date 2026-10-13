"""TESTREG Task 3.0（SPEC v47；契約 version 46）驗收：準備步驟既有紅之修復收據（`receipts.infrastructure_repair`）、
純增改寫收據（`receipts.additive_rewrite`）與參數化全案例（`receipts.session_scope`）。

暫存 git 倉以真實記錄器產生 ledger 後驗：①G-a——共用 helper 於首個壞提交後因生產碼收緊而紅（失敗在 helper、不在斷言），
只改 helper、測試檔零差異；②G-b——舊目標吞例外而殺不死，舊函式一字不動、只新增可殺之函式；③G-c——檔內無測試函式，
模組層敘述依序搬入新增函式並以斷言取代結束碼；④參數化——字面、模組層名稱、類別乘積、fixture params。實作前為紅。
"""
from __future__ import annotations

import importlib
import json
import shutil
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pytest

from tests.registry.testreg_helpers import (
    TmpRepo, entry, lines_with, make_repo, recorded_pytest, session_of, test_records, write_patch,
)

testreg = importlib.import_module("scripts.testreg")

APPROVAL = "handoffs/reconcile/ra/synth.md"
CALC_GOOD = '''def add(a, b):
    return a + b


def scale(x):
    return x * 2


def safe_div(a, b):
    return a / b


def tag(name, tf):
    return f"{name}_{tf}"
'''
# 首個壞提交：tag 收緊為只收合法週期（仿 c6c93b84 之 tag_timeframe）⇒ helper 以 'unknown' 呼叫者於準備步驟失敗
CALC_BAD = CALC_GOOD.replace('def tag(name, tf):\n    return f"{name}_{tf}"\n',
                             'def tag(name, tf):\n    if tf not in ("1h", "4h"):\n        raise ValueError(f"bad tf {tf}")\n'
                             '    return f"{name}_{tf}"\n')
OTHER = "def g():\n    return 7\n"
HELPER = '''from momentum.calc import tag


def tagged(name, tf=None):
    tf = tf or "unknown"
    return tag(name, tf)
'''
HELPER_FIXED = HELPER.replace('tf = tf or "unknown"', 'tf = tf or "1h"')
T_GA = '''from helpers_tf import tagged
from momentum.calc import scale


def test_ga():
    name = tagged("x")
    assert name.startswith("x_")
    assert scale(2) == 4


def test_ga_inline():
    assert tagged("y").startswith("y_")
'''
# 首個壞提交時為「呼叫在斷言內」之形，之後一提交改為準備步驟形（bad 之失敗落在斷言敘述內之反例）
T_HIST_OLD = '''from helpers_tf import tagged


def test_hist():
    assert tagged("h").startswith("h_")
'''
T_HIST_NEW = '''from helpers_tf import tagged


def test_hist():
    name = tagged("h")
    assert name.startswith("h_")
'''
T_GB = '''from momentum.calc import add, safe_div


def test_quick():
    try:
        assert safe_div(6, 3) == 2
    except Exception:
        return False
    return True


def test_other_ok():
    assert add(1, 1) == 2
'''
GB_NEW_FN = "\n\ndef test_quick_strict():\n    assert safe_div(6, 3) == 2\n"
T_GC = '''from momentum.calc import add

a = add(1, 1)
b = add(2, 2)
print("sums", a, b)
if a + b != 6:
    raise SystemExit(1)
'''
GC_NEW = '''from momentum.calc import add


def test_gc_sums():
    a = add(1, 1)
    b = add(2, 2)
    print("sums", a, b)
    assert a + b == 6
'''
T_P = '''import pytest

VALS = [1, 2, 3]


@pytest.mark.parametrize("v", [1, 2, 3])
def test_p(v):
    assert v > 0


@pytest.mark.parametrize("v", VALS)
def test_p_name(v):
    assert v > 0


@pytest.mark.parametrize("a", [1, 2])
class TestK:
    @pytest.mark.parametrize("b", [3, 4, 5])
    def test_k(self, a, b):
        assert a < b


@pytest.fixture(params=[1, 2])
def fx(request):
    return request.param


def test_fx(fx):
    assert fx > 0


def test_plain():
    assert True
'''
GA, HIST, GB, GC, PF = "tests/test_ga.py", "tests/test_hist.py", "tests/test_gb.py", "tests/test_gc.py", "tests/test_p.py"
N_GA, N_GA_INLINE, N_HIST = f"{GA}::test_ga", f"{GA}::test_ga_inline", f"{HIST}::test_hist"
N_QUICK, N_STRICT, N_GC = f"{GB}::test_quick", f"{GB}::test_quick_strict", f"{GC}::test_gc_sums"
MUT_DIR = "handoffs/run_receipts/testreg-mutants"
MUTANTS = {  # 名稱: (檔, 舊片段, 新片段)〔首個壞提交後之生產碼〕
    "m_tag": ("momentum/calc.py", '    return f"{name}_{tf}"\n', '    return f"z_{tf}"\n'),
    "m_scale": ("momentum/calc.py", "    return x * 2\n", "    return x * 3\n"),
    "m_div": ("momentum/calc.py", "    return a / b\n", "    return a / b + 1\n"),
    "m_add": ("momentum/calc.py", "    return a + b\n", "    return a - b\n"),
    "m_g": ("momentum/other.py", "    return 7\n", "    return 8\n"),
}
GB_VARIANTS = {  # additive 補丁之變體（成立形＋反例）：名稱 → 改寫後之 tests/test_gb.py 全文
    "ok": T_GB + GB_NEW_FN,
    "modify_old": (T_GB + GB_NEW_FN).replace("    return True\n", "    return 1\n", 1),
    "delete_old": T_GB.replace("\n\ndef test_other_ok():\n    assert add(1, 1) == 2\n", "") + GB_NEW_FN,
    "fixture": T_GB.replace("from momentum.calc", "import pytest\nfrom momentum.calc", 1)
    + "\n\n@pytest.fixture\ndef six():\n    return 6\n" + GB_NEW_FN,
    "autouse": T_GB.replace("from momentum.calc", "import pytest\nfrom momentum.calc", 1)
    + "\n\n@pytest.fixture(autouse=True)\ndef _setup():\n    yield\n" + GB_NEW_FN,
    "module_stmt": T_GB + "\n\nX = safe_div(1, 1)\n" + GB_NEW_FN,
    "pytestmark": T_GB.replace("from momentum.calc", "import pytest\nfrom momentum.calc", 1)
    + "\n\npytestmark = pytest.mark.slow\n" + GB_NEW_FN,
    "unkillable": T_GB + "\n\ndef test_quick_strict():\n    assert safe_div(6, 3) == 2\n    assert True\n",
    "unbound": T_GB + "\n\ndef test_quick_strict():\n    assert add(3, 3) == 6\n",
    "wrong_file": T_GB.replace("from momentum.calc import add, safe_div", "from momentum.calc import add, safe_div\n"
                                                                         "from momentum.other import g", 1)
    + "\n\ndef test_quick_strict():\n    assert safe_div(6, 3) + g() == 9\n",
}
GC_VARIANTS = {
    "ok": GC_NEW,
    "residual": GC_NEW.replace("from momentum.calc import add\n", "from momentum.calc import add\n\na = add(1, 1)\n", 1),
    "exit_in_fn": GC_NEW.replace("    assert a + b == 6\n", "    if a + b != 6:\n        raise SystemExit(1)\n"
                                                           "    assert a + b == 6\n", 1),
    "order": GC_NEW.replace("    a = add(1, 1)\n    b = add(2, 2)\n", "    b = add(2, 2)\n    a = add(1, 1)\n", 1),
}

# ── v48（修訂審查 r46 處置；只增）──────────────────────────────────────────────────────────────────────────────
GK, GS = "tests/test_gk.py", "tests/test_gs.py"
N_K, N_K2, N_S, N_S2 = f"{GK}::test_k", f"{GK}::test_k2", f"{GS}::test_s", f"{GS}::test_s_strict"
T_GK = "from momentum.calc import add\n\n\ndef test_k():\n    assert add(1, 2) == 3\n"
T_GS = ("from momentum.calc import *\n\n\ndef test_s():\n    try:\n        assert safe_div(8, 4) == 2\n"
        "    except Exception:\n        return False\n    return True\n")
GK_VARIANTS = {"dup": T_GK + "\n\ndef test_k2():\n    assert add(2, 2) == 4\n"}
GS_VARIANTS = {"ok": T_GS + "\n\ndef test_s_strict():\n    assert safe_div(8, 4) == 2\n"}
GB_VARIANTS["import_shadow"] = T_GB + "\n\nfrom momentum.calc import add as safe_div\n" + GB_NEW_FN
GB_VARIANTS["star_import"] = T_GB + "\n\nfrom momentum.other import *\n" + GB_NEW_FN
GB_VARIANTS["decorator"] = (T_GB.replace("from momentum.calc", "import pytest\nfrom momentum.calc", 1)
                            + "\n\n@pytest.mark.skipif(False, reason=\"x\")\ndef test_quick_strict():\n"
                            "    assert safe_div(6, 3) == 2\n")
T_P_V48 = T_P + '''

@pytest.mark.usefixtures("fx")
def test_uf():
    assert True


@pytest.mark.parametrize("a", [1, 2])
class TestBase:
    pass


class TestChild(TestBase):
    def test_c(self, a):
        assert a > 0
'''


def infra_rel(nodeid: str) -> str:
    """獨立 oracle：依契約 receipts.infrastructure_repair.file_rule。"""
    return f"handoffs/run_receipts/testreg-infra-repair/{nodeid.replace('/', '__').replace('::', '--')}.json"


def additive_rel(path: str) -> str:
    """獨立 oracle：依契約 receipts.additive_rewrite.file_rule（檔級）。"""
    return f"handoffs/run_receipts/testreg-additive/{path.replace('/', '__')}.json"


def _mut_patch(r: TmpRepo, mid: str) -> tuple:
    rel = f"{MUT_DIR}/{mid}.patch"
    f, old, new = MUTANTS[mid]
    assert r.read(f).count(old) == 1, mid
    return rel, write_patch(r, f, r.read(f).replace(old, new, 1), rel)


def _run_with(r: TmpRepo, patches: List[str], *args: str) -> str:
    for p in patches:
        r.git("apply", p)
    try:
        proc, ids = recorded_pytest(r, *args)
    finally:
        for p in reversed(patches):
            r.git("apply", "-R", p)
    assert len(ids) == 1, proc.stdout + proc.stderr
    return ids[0]


def _at(r: TmpRepo, rev: str, branch: str, *args: str) -> str:
    r.git("checkout", "-q", "--detach", rev)
    try:
        return _run_with(r, [], *args)
    finally:
        r.git("checkout", "-q", branch)


@pytest.fixture(scope="module")
def ra(tmp_path_factory) -> Dict[str, Any]:
    root = tmp_path_factory.mktemp("ra")
    r = make_repo(root, {"momentum/__init__.py": "", "momentum/calc.py": CALC_GOOD, "momentum/other.py": OTHER,
                         "tests/helpers_tf.py": HELPER, GA: T_GA, HIST: T_HIST_OLD, GB: T_GB, GC: T_GC, PF: T_P})
    cat = r.catalog()
    cat["entries"][GA].update(entry(GA, disposition="rewrite", rewrite_targets=[N_GA], disposition_ref=APPROVAL))
    cat["entries"][GB].update(entry(GB, disposition="rewrite", rewrite_targets=[N_QUICK], disposition_ref=APPROVAL))
    cat["entries"][GC].update(entry(GC, disposition="rewrite", rewrite_targets=[], disposition_ref=APPROVAL))
    r.set_catalog(cat)
    # v48（只增）：可殺舊目標檔、星號匯入檔；參數化檔追加 usefixtures 與繼承類別
    r.write(GK, T_GK)
    r.write(GS, T_GS)
    r.write(PF, T_P_V48)
    cat2 = r.catalog()
    cat2["entries"][GK] = entry(GK, disposition="rewrite", rewrite_targets=[N_K], disposition_ref=APPROVAL)
    cat2["entries"][GS] = entry(GS, disposition="rewrite", rewrite_targets=[N_S], disposition_ref=APPROVAL)
    r.set_catalog(cat2)
    good = r.commit("catalog")
    r.write("momentum/calc.py", CALC_BAD)
    bad = r.commit("tag strict")
    r.write(HIST, T_HIST_NEW)
    r.commit("hist to setup form")
    r.write(APPROVAL, f"# approval\n{N_GA} {N_GA_INLINE} {N_HIST} {GB} {GC} first bad {bad[:8]}\n")
    r.write("handoffs/reconcile/ra/plain.md", "# approval without cross reference\n")
    r.write(APPROVAL, r.read(APPROVAL) + f"{GK} {GS}\n")
    rp = "handoffs/run_receipts/testreg-infra-repair/helpers_tf.repair.patch"
    rsha = write_patch(r, "tests/helpers_tf.py", HELPER_FIXED, rp)
    rp_bad = "handoffs/run_receipts/testreg-infra-repair/helpers_tf_and_test.repair.patch"
    rp_bad_text_helper = write_patch(r, "tests/helpers_tf.py", HELPER_FIXED, rp_bad)
    del rp_bad_text_helper
    # 修復補丁夾帶改測試檔（反例）：兩檔之合併補丁
    r.write("tests/helpers_tf.py", HELPER_FIXED)
    r.write(GA, T_GA.replace('    assert scale(2) == 4\n', '    assert scale(2) == 4\n    assert True\n', 1))
    combined = r.git("diff", "--binary", "--", "tests/helpers_tf.py", GA)
    r.git("checkout", "-q", "--", "tests/helpers_tf.py", GA)
    r.write(rp_bad, combined)
    import hashlib
    rbsha = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    msha = {m: _mut_patch(r, m) for m in MUTANTS}
    cp, csha = {}, {}
    for k, text in GB_VARIANTS.items():
        cp[f"gb_{k}"] = f"handoffs/run_receipts/testreg-additive/gb_{k}.compare.patch"
        csha[f"gb_{k}"] = write_patch(r, GB, text, cp[f"gb_{k}"])
    for k, text in GC_VARIANTS.items():
        cp[f"gc_{k}"] = f"handoffs/run_receipts/testreg-additive/gc_{k}.compare.patch"
        csha[f"gc_{k}"] = write_patch(r, GC, text, cp[f"gc_{k}"])
    for pre, path_, variants in (("gk", GK, GK_VARIANTS), ("gs", GS, GS_VARIANTS)):
        for k, text in variants.items():
            cp[f"{pre}_{k}"] = f"handoffs/run_receipts/testreg-additive/{pre}_{k}.compare.patch"
            csha[f"{pre}_{k}"] = write_patch(r, path_, text, cp[f"{pre}_{k}"])
    head = r.commit("patches")
    branch = r.git("rev-parse", "--abbrev-ref", "HEAD").strip()
    s: Dict[str, str] = {}
    # G-a
    s["ga@head"] = _run_with(r, [], N_GA, N_GA_INLINE, N_HIST)
    s["ga@repaired"] = _run_with(r, [rp], N_GA, N_GA_INLINE, N_HIST)
    for m in ("m_tag", "m_scale"):
        s[f"ga+{m}"] = _run_with(r, [rp, msha[m][0]], N_GA, N_GA_INLINE, N_HIST)
    s["ga@good"] = _at(r, good, branch, N_GA, N_GA_INLINE, N_HIST)
    s["ga@bad"] = _at(r, bad, branch, N_GA, N_GA_INLINE, N_HIST)
    # G-b（每變體：baseline〔全檔〕＋各 mutant〔全檔〕）
    for k in GB_VARIANTS:
        s[f"gb_{k}@base"] = _run_with(r, [cp[f"gb_{k}"]], GB)
        for m in ("m_div", "m_add", "m_g"):
            s[f"gb_{k}+{m}"] = _run_with(r, [cp[f"gb_{k}"], msha[m][0]], GB)
    # G-c
    for k in GC_VARIANTS:
        s[f"gc_{k}@base"] = _run_with(r, [cp[f"gc_{k}"]], GC)
        s[f"gc_{k}+m_add"] = _run_with(r, [cp[f"gc_{k}"], msha["m_add"][0]], GC)
    # 參數化（session_scope）
    s["p@fn"] = _run_with(r, [], f"{PF}::test_p")
    s["p@one"] = _run_with(r, [], f"{PF}::test_p[1]")
    s["p@k"] = _run_with(r, [], PF, "-k", "test_p")
    s["p@file"] = _run_with(r, [], PF)
    # v48（只增）
    s["gk_dup@base"] = _run_with(r, [cp["gk_dup"]], GK)
    s["gk_dup+m_add"] = _run_with(r, [cp["gk_dup"], msha["m_add"][0]], GK)
    s["gs_ok@base"] = _run_with(r, [cp["gs_ok"]], GS)
    s["gs_ok+m_div"] = _run_with(r, [cp["gs_ok"], msha["m_div"][0]], GS)
    s["p@dup"] = _run_with(r, [], "--keep-duplicates", f"{PF}::test_plain", f"{PF}::test_plain")
    return {"repo": r, "head": head, "good": good, "bad": bad, "branch": branch, "rp": rp, "rsha": rsha,
            "rp_bad": rp_bad, "rbsha": rbsha, "msha": msha, "cp": cp, "csha": csha, "s": s}


def _fail_loc(rec: Mapping[str, Any], path: str) -> Optional[str]:
    hits = [f for f in rec.get("fail_frames", []) if f.split(":")[0] == path]
    return hits[0] if hits else None


def _dc(fx, *sids: str) -> str:
    dcs = {session_of(fx["repo"], i)["duration_class"] for i in sids}
    assert len(dcs) == 1
    return dcs.pop()


def _infra_mutant(fx, mid: str, nodeid: str, sess: Optional[str] = None) -> Dict[str, Any]:
    sid = fx["s"][sess or f"ga+{mid}"]
    rec = test_records(fx["repo"], sid)[nodeid]
    return {"id": mid, "patch_path": fx["msha"][mid][0], "patch_sha256": fx["msha"][mid][1], "session_id": sid,
            "compare_session_id": sid, "target_outcome": rec["outcome"],
            "target_fail_loc": _fail_loc(rec, nodeid.split("::")[0]), "compare_outcomes": {nodeid: rec["outcome"]}}


def infra_receipt(fx, nodeid: str = N_GA, mids=("m_tag", "m_scale"), **over: Any) -> Dict[str, Any]:
    s = fx["s"]
    rc = {"target_nodeid": nodeid, "head": fx["head"], "approval_ref": APPROVAL, "fingerprint": "",
          "repair_patch_path": fx["rp"], "repair_patch_sha256": fx["rsha"], "first_bad_commit": fx["bad"],
          "good_commit": fx["good"], "target_session_id": s["ga@head"], "repaired_session_id": s["ga@repaired"],
          "good_session_id": s["ga@good"], "bad_session_id": s["ga@bad"],
          "mutants": [_infra_mutant(fx, m, nodeid) for m in mids]}
    rc.update(over)
    rc["fingerprint"] = _dc(fx, rc["target_session_id"], rc["repaired_session_id"], rc["good_session_id"],
                            rc["bad_session_id"], *[m["session_id"] for m in rc["mutants"]])
    return rc


def additive_receipt(fx, path: str, variant: str, mutants, added: List[str], **over: Any) -> Dict[str, Any]:
    pre = "gb" if path == GB else "gc"
    s = fx["s"]
    rc = {"path": path, "head": fx["head"], "approval_ref": APPROVAL, "fingerprint": "",
          "compare_patch_path": fx["cp"][f"{pre}_{variant}"], "compare_patch_sha256": fx["csha"][f"{pre}_{variant}"],
          "added_nodeids": added, "baseline_session_id": s[f"{pre}_{variant}@base"],
          "mutants": [{"id": m, "patch_path": fx["msha"][m][0], "patch_sha256": fx["msha"][m][1],
                       "session_id": s[f"{pre}_{variant}+{m}"]} for m in mutants]}
    rc.update(over)
    rc["fingerprint"] = _dc(fx, rc["baseline_session_id"], *[m["session_id"] for m in rc["mutants"]])
    return rc


def _work(fx, tmp_path: Path, name: str) -> TmpRepo:
    dst = tmp_path / name
    shutil.copytree(fx["repo"].root, dst, symlinks=True)
    return TmpRepo(dst)


def _ctx(r: TmpRepo, tree: str = "worktree"):
    return testreg.build_context(r.root, tree)


def _apply(r: TmpRepo, path: str, text: str) -> None:
    r.write(path, text)


# ── (i) infrastructure_repair ───────────────────────────────────────────────────────────────────────────────────

def test_i_precondition_target_red_at_head_in_helper_not_in_assertion(ra):
    """前提（獨立 oracle）：head 時 test_ga 失敗、失敗 frame 落在 helper，且不落在 test_ga 之任何斷言行；修復後全過。"""
    rec = test_records(ra["repo"], ra["s"]["ga@head"])[N_GA]
    assert rec["outcome"] in ("failed", "error")
    assert any(f.startswith("tests/helpers_tf.py:") for f in rec["fail_frames"]), rec
    assert_lines = set(lines_with(ra["repo"], GA, "assert "))
    assert not any(f.startswith(GA + ":") and int(f.rsplit(":", 1)[1]) in assert_lines for f in rec["fail_frames"])
    assert test_records(ra["repo"], ra["s"]["ga@repaired"])[N_GA]["outcome"] == "passed"


def test_i_valid_repair_receipt_counts_as_executed_v21(ra, tmp_path):
    """只改 helper（測試檔零差異）＋成立之修復收據 ⇒ 具名縫回 []、`validate --require-executed` 無 V21 列；無收據 ⇒ V21。"""
    r = _work(ra, tmp_path, "ok")
    _apply(r, "tests/helpers_tf.py", HELPER_FIXED)
    bad = r.run("validate", "--require-executed")
    assert any(l.startswith("V21 ") and GA in l for l in (bad.stdout + bad.stderr).splitlines()), bad.stderr
    r.write_json(infra_rel(N_GA), infra_receipt(ra))
    assert testreg.infrastructure_repair_errors(_ctx(r), N_GA) == []
    ok = r.run("validate", "--require-executed")
    assert not any(l.startswith("V21 ") and GA in l for l in (ok.stdout + ok.stderr).splitlines()), ok.stderr


INFRA_NEG = {
    "patch_touches_test_file": (lambda fx: {"repair_patch_path": fx["rp_bad"], "repair_patch_sha256": fx["rbsha"]},
                                "測試檔"),
    "repaired_not_passed": (lambda fx: {"repaired_session_id": fx["s"]["ga@head"]}, "修復後"),
    "approval_no_crossref": (lambda fx: {"approval_ref": "handoffs/reconcile/ra/plain.md"}, "approval_ref"),
    "missing_kill_for_assertion": (lambda fx: {"mutants": [_infra_mutant(fx, "m_tag", N_GA)]}, "無對應之殺 mutant"),
    "bad_not_failed": (lambda fx: {"bad_session_id": fx["s"]["ga@good"]}, "bad"),
}


@pytest.mark.parametrize("case", sorted(INFRA_NEG))
def test_i_repair_negatives_block_with_reason(ra, tmp_path, case):
    """各反例：具名縫回非空且含具體理由；`validate --require-executed` 仍有 V21 列。"""
    r = _work(ra, tmp_path, case)
    _apply(r, "tests/helpers_tf.py", HELPER_FIXED)
    over, reason = INFRA_NEG[case]
    r.write_json(infra_rel(N_GA), infra_receipt(ra, **over(ra)))
    errs = testreg.infrastructure_repair_errors(_ctx(r), N_GA)
    assert errs and any(reason in e for e in errs), errs
    proc = r.run("validate", "--require-executed")
    assert any(l.startswith("V21 ") and GA in l for l in (proc.stdout + proc.stderr).splitlines()), proc.stderr


def test_i_head_failure_inside_assertion_blocks(ra, tmp_path):
    """test_ga_inline：失敗之呼叫在斷言敘述內 ⇒ 不屬準備步驟既有紅，收據不成立（理由含「斷言」）。"""
    r = _work(ra, tmp_path, "inline")
    _apply(r, "tests/helpers_tf.py", HELPER_FIXED)
    r.write_json(infra_rel(N_GA_INLINE), infra_receipt(ra, N_GA_INLINE, mids=("m_tag",)))
    errs = testreg.infrastructure_repair_errors(_ctx(r), N_GA_INLINE)
    assert errs and any("斷言" in e for e in errs), errs


def test_i_bad_failure_inside_assertion_blocks(ra, tmp_path):
    """test_hist：首個壞提交時呼叫在斷言內（之後才改為準備步驟形）⇒ bad 之失敗落在斷言敘述內，收據不成立。"""
    r = _work(ra, tmp_path, "hist")
    _apply(r, "tests/helpers_tf.py", HELPER_FIXED)
    r.write_json(infra_rel(N_HIST), infra_receipt(ra, N_HIST, mids=("m_tag",)))
    errs = testreg.infrastructure_repair_errors(_ctx(r), N_HIST)
    assert errs and any("bad" in e for e in errs), errs


def test_i_named_seam_none_without_receipt(ra, tmp_path):
    r = _work(ra, tmp_path, "none")
    assert testreg.infrastructure_repair_errors(_ctx(r), N_GA) is None


def test_mutation_infra_errors_always_empty_lets_negative_through(ra, tmp_path, monkeypatch):
    """mutant：`infrastructure_repair_errors` 恆回 [] ⇒ 修後未全過之反例亦不再有 V21 列（證 V21 依賴該判定）。"""
    r = _work(ra, tmp_path, "mut")
    _apply(r, "tests/helpers_tf.py", HELPER_FIXED)
    cat = r.catalog()  # 只留 test_ga.py 一個 rewrite entry（他檔之未執行與本 mutant 無關）
    for other in (GB, GC, GK, GS):
        cat["entries"][other].update(entry(other))
    r.set_catalog(cat)
    r.write_json(infra_rel(N_GA), infra_receipt(ra, repaired_session_id=ra["s"]["ga@head"]))
    monkeypatch.setattr(testreg, "infrastructure_repair_errors", lambda ctx, nodeid: [])
    assert testreg.main(["--repo", str(r.root), "validate", "--require-executed"]) == 0


# ── (j) additive_rewrite（G-b）─────────────────────────────────────────────────────────────────────────────────

def _gb_commit_check(fx, tmp_path, variant: str, rc: Optional[Mapping[str, Any]]):
    r = _work(fx, tmp_path, f"gb_{variant}")
    _apply(r, GB, GB_VARIANTS[variant])
    rels = [GB]
    if rc is not None:
        r.write_json(additive_rel(GB), rc)
        rels.append(additive_rel(GB))
    r.install_precommit()
    r.stage(*rels)
    return r, r.try_commit()


def test_j_valid_additive_releases_v07_and_counts_executed(ra, tmp_path):
    """舊函式不動、新增 test_quick_strict（m_div 殺之、引用 safe_div）⇒ pre-commit rc 0；無收據 ⇒ V07 擋。"""
    _, no = _gb_commit_check(ra, tmp_path / "no", "ok", None)
    assert no.returncode != 0 and any(l.startswith("V07 ") for l in no.stderr.splitlines()), no.stderr
    rc = additive_receipt(ra, GB, "ok", ("m_div",), [N_STRICT])
    r, ok = _gb_commit_check(ra, tmp_path / "ok", "ok", rc)
    assert ok.returncode == 0, ok.stderr
    assert testreg.additive_rewrite_errors(_ctx(r), GB) == []
    proc = r.run("validate", "--require-executed")
    assert not any(l.startswith("V21 ") and GB in l for l in (proc.stdout + proc.stderr).splitlines()), proc.stderr


GB_NEG = {
    "modify_old": ([N_STRICT], ("m_div",), "舊"),
    "delete_old": ([N_STRICT], ("m_div",), "舊"),
    "fixture": ([N_STRICT], ("m_div",), "結構"),
    "autouse": ([N_STRICT], ("m_div",), "結構"),
    "module_stmt": ([N_STRICT], ("m_div",), "結構"),
    "pytestmark": ([N_STRICT], ("m_div",), "結構"),
    "unkillable": ([N_STRICT], ("m_div",), "無對應之殺 mutant"),
    "unbound": ([N_STRICT], ("m_add",), "情境"),
    "wrong_file": ([N_STRICT], ("m_g",), "情境"),
}


@pytest.mark.parametrize("variant", sorted(GB_NEG))
def test_j_additive_negatives_block_with_reason(ra, tmp_path, variant):
    added, mutants, reason = GB_NEG[variant]
    rc = additive_receipt(ra, GB, variant, mutants, added)
    r, proc = _gb_commit_check(ra, tmp_path, variant, rc)
    assert proc.returncode != 0, proc.stderr
    errs = testreg.additive_rewrite_errors(_ctx(r, "staged"), GB)
    assert errs and any(reason in e for e in errs), errs


def test_j_added_nodeids_must_be_exact(ra, tmp_path):
    """added_nodeids 少列或多列（列入舊函式）⇒ 不成立。"""
    for added in ([], [N_STRICT, N_QUICK]):
        rc = additive_receipt(ra, GB, "ok", ("m_div",), [N_STRICT])
        rc["added_nodeids"] = added
        r = _work(ra, tmp_path, f"exact{len(added)}")
        _apply(r, GB, GB_VARIANTS["ok"])
        r.write_json(additive_rel(GB), rc)
        assert testreg.additive_rewrite_errors(_ctx(r), GB), added


def test_j_named_seam_none_without_receipt(ra, tmp_path):
    r = _work(ra, tmp_path, "none")
    assert testreg.additive_rewrite_errors(_ctx(r), GB) is None


def test_mutation_additive_errors_always_empty_lets_negative_through(ra, tmp_path, monkeypatch):
    """mutant：`additive_rewrite_errors` 恆回 [] ⇒ 改舊函式之反例被 V07 放行（行程內 check --staged）。"""
    rc = additive_receipt(ra, GB, "modify_old", ("m_div",), [N_STRICT])
    r = _work(ra, tmp_path, "mut")
    _apply(r, GB, GB_VARIANTS["modify_old"])
    r.write_json(additive_rel(GB), rc)
    r.stage(GB, additive_rel(GB))
    monkeypatch.setattr(testreg, "additive_rewrite_errors", lambda ctx, path: [])
    assert testreg.main(["--repo", str(r.root), "check", "--staged"]) == 0


# ── (k) G-c ──────────────────────────────────────────────────────────────────────────────────────────────────────

def test_k_gc_relocation_valid(ra, tmp_path):
    r = _work(ra, tmp_path, "gc_ok")
    _apply(r, GC, GC_VARIANTS["ok"])
    r.write_json(additive_rel(GC), additive_receipt(ra, GC, "ok", ("m_add",), [N_GC]))
    assert testreg.additive_rewrite_errors(_ctx(r), GC) == []


@pytest.mark.parametrize("variant,reason", [("residual", "模組層"), ("exit_in_fn", "結束"), ("order", "依序")])
def test_k_gc_negatives_block(ra, tmp_path, variant, reason):
    r = _work(ra, tmp_path, f"gc_{variant}")
    _apply(r, GC, GC_VARIANTS[variant])
    r.write_json(additive_rel(GC), additive_receipt(ra, GC, variant, ("m_add",), [N_GC]))
    errs = testreg.additive_rewrite_errors(_ctx(r), GC)
    assert errs and any(reason in e for e in errs), errs


def test_k_gc_only_additive_applies(ra, tmp_path):
    """head 0 測試函式之 rewrite 檔：無收據 ⇒ V07 擋且訊息指名須走純增改寫收據。"""
    r = _work(ra, tmp_path, "gc_none")
    _apply(r, GC, GC_VARIANTS["ok"])
    r.install_precommit()
    r.stage(GC)
    proc = r.try_commit()
    assert proc.returncode != 0 and any(l.startswith("V07 ") and "純增" in l for l in proc.stderr.splitlines()), \
        proc.stderr


# ── (l) session_scope ────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sess,nodeid,ok", [
    ("p@fn", f"{PF}::test_p", True),
    ("p@file", f"{PF}::test_p", True),
    ("p@file", f"{PF}::test_p_name", True),
    ("p@file", f"{PF}::TestK::test_k", True),
    ("p@file", f"{PF}::test_plain", True),
    ("p@one", f"{PF}::test_p", False),
    ("p@k", f"{PF}::test_p", False),
    ("p@file", f"{PF}::test_fx", False),
])
def test_l_session_scope_cases(ra, tmp_path, sess, nodeid, ok):
    """全案例：函式層 nodeid／整檔且無篩選 ⇒ 成立（字面、模組層名稱、類別乘積 2×3、無參數）；只跑單一參數案例、帶 -k、
    以 fixture params 提供參數（不可靜態列舉）⇒ 不成立。"""
    errs = testreg.session_scope_errors(_ctx(ra["repo"]), ra["s"][sess], nodeid)
    assert (errs == []) is ok, errs


def test_l_precondition_counts(ra):
    """前提（獨立 oracle）：整檔 session 中 TestK::test_k 有 6 筆、test_p 有 3 筆；單案例 session 只 1 筆。"""
    recs = test_records(ra["repo"], ra["s"]["p@file"])
    assert sum(1 for n in recs if n.startswith(f"{PF}::TestK::test_k[")) == 6
    assert sum(1 for n in recs if n.startswith(f"{PF}::test_p[")) == 3
    assert len(test_records(ra["repo"], ra["s"]["p@one"])) == 1


def test_mutation_session_scope_wired_into_existing_red(ra, tmp_path, monkeypatch):
    """既有紅收據之 session 亦依 session_scope：具名縫改為恆回非空 ⇒ 成立之修復收據轉不成立（證各收據皆呼叫之）。"""
    r = _work(ra, tmp_path, "scope_wire")
    _apply(r, "tests/helpers_tf.py", HELPER_FIXED)
    r.write_json(infra_rel(N_GA), infra_receipt(ra))
    assert testreg.infrastructure_repair_errors(_ctx(r), N_GA) == []
    monkeypatch.setattr(testreg, "session_scope_errors", lambda ctx, sid, nodeid, tree=None: ["scope"])
    assert testreg.infrastructure_repair_errors(_ctx(r), N_GA)
    src = (Path(testreg.__file__)).read_text(encoding="utf-8")
    body = src.split("def defective_rewrite_errors", 1)[1].split("\ndef ", 1)[0]
    assert "session_scope_errors" in body  # 既有紅收據之判定本體呼叫具名縫


# ── (n) 秒級 ─────────────────────────────────────────────────────────────────────────────────────────────────────

def test_n_receipt_release_timing(ra, tmp_path):
    """附成立之純增收據之 pre-commit 放行判定（check --staged）3 次中位 < 5 s。"""
    rc = additive_receipt(ra, GB, "ok", ("m_div",), [N_STRICT])
    r = _work(ra, tmp_path, "t")
    _apply(r, GB, GB_VARIANTS["ok"])
    r.write_json(additive_rel(GB), rc)
    r.stage(GB, additive_rel(GB))
    secs = []
    for _ in range(3):
        t0 = time.perf_counter()
        proc = r.run("check", "--staged")
        secs.append(time.perf_counter() - t0)
        assert proc.returncode == 0, proc.stderr
    assert statistics.median(secs) < 5.0, secs


# ── v48（修訂審查 r46 處置；只增）────────────────────────────────────────────────────────────────────────────────

def _additive_receipt_v48(fx, path: str, pre: str, variant: str, mutants, added: List[str]) -> Dict[str, Any]:
    s = fx["s"]
    rc = {"path": path, "head": fx["head"], "approval_ref": APPROVAL, "fingerprint": "",
          "compare_patch_path": fx["cp"][f"{pre}_{variant}"], "compare_patch_sha256": fx["csha"][f"{pre}_{variant}"],
          "added_nodeids": added, "baseline_session_id": s[f"{pre}_{variant}@base"],
          "mutants": [{"id": m, "patch_path": fx["msha"][m][0], "patch_sha256": fx["msha"][m][1],
                       "session_id": s[f"{pre}_{variant}+{m}"]} for m in mutants]}
    rc["fingerprint"] = _dc(fx, rc["baseline_session_id"], *[m["session_id"] for m in rc["mutants"]])
    return rc


def test_o_killable_old_target_without_new_detection_blocks(ra, tmp_path):
    """(o) 舊目標 test_k 可殺且對殺新增函式之 m_add 亦失敗 ⇒ 純增不成立（理由含「偵測力」；應走 receipts.mutation）。"""
    rec = test_records(ra["repo"], ra["s"]["gk_dup+m_add"])
    assert rec[N_K]["outcome"] == "failed" and rec[N_K2]["outcome"] == "failed"  # 前提（獨立 oracle）
    r = _work(ra, tmp_path, "gk")
    _apply(r, GK, GK_VARIANTS["dup"])
    r.write_json(additive_rel(GK), _additive_receipt_v48(ra, GK, "gk", "dup", ("m_add",), [N_K2]))
    errs = testreg.additive_rewrite_errors(_ctx(r), GK)
    assert errs and any("偵測力" in e for e in errs), errs


GB_NEG_V48 = ["decorator", "import_shadow", "star_import"]


@pytest.mark.parametrize("variant", GB_NEG_V48)
def test_p_whitelist_v48_negatives_block(ra, tmp_path, variant):
    """(p) 新增 import 覆蓋 head 已用之名、星號匯入、新增函式帶非 parametrize 裝飾器 ⇒ 擋（理由含「結構」）。"""
    rc = additive_receipt(ra, GB, variant, ("m_div",), [N_STRICT])
    r = _work(ra, tmp_path, f"gb48_{variant}")
    _apply(r, GB, GB_VARIANTS[variant])
    r.write_json(additive_rel(GB), rc)
    errs = testreg.additive_rewrite_errors(_ctx(r), GB)
    assert errs and any("結構" in e for e in errs), errs


def test_q_precondition_inherited_and_duplicate_counts(ra):
    """前提（獨立 oracle）：繼承同模組基底之類別參數化使 TestChild::test_c 有 2 筆；--keep-duplicates 之 session 之
    argv_norm 確記 keepduplicates（記錄器以 nodeid 彙整、同 nodeid 只寫一筆，故以旗標擋下自然之重複執行）。"""
    recs = test_records(ra["repo"], ra["s"]["p@file"])
    assert sum(1 for n in recs if n.startswith(f"{PF}::TestChild::test_c[")) == 2
    an = json.loads(session_of(ra["repo"], ra["s"]["p@dup"])["argv_norm"])
    assert an["option"]["keepduplicates"] is True


def test_q_session_scope_usefixtures_inherited_duplicates(ra):
    """(q) usefixtures 請求 params fixture ⇒ 不可列舉；同模組基底類別之 parametrize 遞移納入 ⇒ 成立；重複執行同一 nodeid
    之 session ⇒ 不成立。"""
    ctx = _ctx(ra["repo"])
    errs_uf = testreg.session_scope_errors(ctx, ra["s"]["p@file"], f"{PF}::test_uf")
    assert any("不可靜態列舉" in e for e in errs_uf), errs_uf  # 須因列舉判定而擋，不只因筆數不符
    assert testreg.session_scope_errors(ctx, ra["s"]["p@file"], f"{PF}::TestChild::test_c") == []
    assert testreg.session_scope_errors(ctx, ra["s"]["p@dup"], f"{PF}::test_plain")


def test_r_star_import_old_target_additive_valid(ra, tmp_path):
    """(r) 舊目標經模組層星號匯入取得 safe_div ⇒ 情境綁定解析得之，純增成立。"""
    r = _work(ra, tmp_path, "gs")
    _apply(r, GS, GS_VARIANTS["ok"])
    r.write_json(additive_rel(GS), _additive_receipt_v48(ra, GS, "gs", "ok", ("m_div",), [N_S2]))
    assert testreg.additive_rewrite_errors(_ctx(r), GS) == []
