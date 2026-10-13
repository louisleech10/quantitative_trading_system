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

# ── v49（修訂審查 r47 處置；只增）：根 conftest 以 pytest_plugins 載入之外掛模組中帶 params 之 fixture ─────────
CONFTEST_V49 = 'pytest_plugins = ["tests.plug_fx"]\n'
PLUG_V49 = "import pytest\n\n\n@pytest.fixture(params=[1, 2])\ndef plug_fx(request):\n    return request.param\n"
T_P_V49_ADD = "\n\ndef test_plug(plug_fx):\n    assert plug_fx > 0\n"


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
    # v49（只增）
    r.write("tests/conftest.py", CONFTEST_V49)
    r.write("tests/plug_fx.py", PLUG_V49)
    r.write(PF, T_P_V48 + T_P_V49_ADD)
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


# ── v49（修訂審查 r47 處置；只增）────────────────────────────────────────────────────────────────────────────────

def test_s_session_scope_plugin_param_fixture_not_enumerable(ra):
    """(s) test_plug 請求根 conftest 以 pytest_plugins 載入之外掛模組中以 params 定義之 fixture（前提：整檔 session 中
    有 2 筆）⇒ session_scope 以「不可靜態列舉」為理由不成立（只掃測試檔與目錄鏈 conftest 之實作會少算為 1）。"""
    recs = test_records(ra["repo"], ra["s"]["p@file"])
    assert sum(1 for n in recs if n.startswith(f"{PF}::test_plug[")) == 2
    errs = testreg.session_scope_errors(_ctx(ra["repo"]), ra["s"]["p@file"], f"{PF}::test_plug")
    assert any("不可靜態列舉" in e for e in errs), errs


# ── v50（修訂審查 r48 處置；只增）：外掛模組中 autouse＋params 之 fixture，測試函式不請求 ────────────────────────────
CONFTEST_V50 = 'pytest_plugins = ["tests.plug_auto"]\n'
PLUG_V50 = "import pytest\n\n\n@pytest.fixture(autouse=True, params=[1, 2])\ndef plug_auto(request):\n    return request.param\n"
PA = "tests/test_pa.py"
T_PA_V50 = "def test_pa():\n    assert True\n"


@pytest.fixture(scope="module")
def ra_auto(tmp_path_factory) -> Dict[str, Any]:
    """(t) 專用暫存 repo：autouse 外掛 fixture 會參數化同一 session 之全部測試，故不併入 ra。"""
    r = make_repo(tmp_path_factory.mktemp("ra_auto"), {"momentum/__init__.py": "", "momentum/other.py": OTHER,
                                                       "tests/conftest.py": CONFTEST_V50,
                                                       "tests/plug_auto.py": PLUG_V50, PA: T_PA_V50})
    return {"repo": r, "sid": _run_with(r, [], PA)}


def test_t_session_scope_plugin_autouse_param_fixture_not_enumerable(ra_auto):
    """(t) test_pa 不請求任何 fixture，但根 conftest 以 pytest_plugins 載入之外掛模組中有 autouse＋params 之 fixture
    （前提：整檔 session 中有 2 筆）⇒ session_scope 以「不可靜態列舉」為理由不成立（不遍歷外掛 autouse 之實作會少算為 1）。"""
    recs = test_records(ra_auto["repo"], ra_auto["sid"])
    assert sum(1 for n in recs if n.startswith(f"{PA}::test_pa[")) == 2
    errs = testreg.session_scope_errors(_ctx(ra_auto["repo"]), ra_auto["sid"], f"{PA}::test_pa")
    assert any("不可靜態列舉" in e for e in errs), errs


# ── v51（修訂審查 r49 處置；只增）：autouse 遞移依賴外掛 params fixture；類別裝飾器／類別 pytestmark／模組 pytestmark 之
#    usefixtures 請求外掛 params fixture ──────────────────────────────────────────────────────────────────────────
CONFTEST_V51T = 'pytest_plugins = ["tests.plug_trans"]\n'
PLUG_V51T = ("import pytest\n\n\n@pytest.fixture(params=[1, 2])\ndef inner(request):\n    return request.param\n\n\n"
             "@pytest.fixture(autouse=True)\ndef outer(inner):\n    return inner\n")
PT = "tests/test_tr.py"
T_PT_V51 = "def test_tr():\n    assert True\n"
CONFTEST_V51U = 'pytest_plugins = ["tests.plug_uf"]\n'
PLUG_V51U = "import pytest\n\n\n@pytest.fixture(params=[1, 2])\ndef ufx(request):\n    return request.param\n"
UCD, UCM, UMOD = "tests/test_ucd.py", "tests/test_ucm.py", "tests/test_umod.py"
T_UCD = ('import pytest\n\n\n@pytest.mark.usefixtures("ufx")\nclass TestUcd:\n    def test_c(self):\n'
         '        assert True\n')
T_UCM = ('import pytest\n\n\nclass TestUcm:\n    pytestmark = pytest.mark.usefixtures("ufx")\n\n'
         '    def test_c(self):\n        assert True\n')
T_UMOD = 'import pytest\n\npytestmark = pytest.mark.usefixtures("ufx")\n\n\ndef test_m():\n    assert True\n'


@pytest.fixture(scope="module")
def ra_trans(tmp_path_factory) -> Dict[str, Any]:
    """(u) 專用暫存 repo：autouse 外掛 fixture 會參數化同一 session 之全部測試，故不併入 ra／ra_auto。"""
    r = make_repo(tmp_path_factory.mktemp("ra_trans"), {"momentum/__init__.py": "", "momentum/other.py": OTHER,
                                                        "tests/conftest.py": CONFTEST_V51T,
                                                        "tests/plug_trans.py": PLUG_V51T, PT: T_PT_V51})
    return {"repo": r, "sid": _run_with(r, [], PT)}


@pytest.fixture(scope="module")
def ra_uf(tmp_path_factory) -> Dict[str, Any]:
    """(v)(w)(x) 共用暫存 repo：外掛 ufx 帶 params、非 autouse；三檔各以一種 usefixtures 宣告請求它，各跑一 session。"""
    r = make_repo(tmp_path_factory.mktemp("ra_uf"), {"momentum/__init__.py": "", "momentum/other.py": OTHER,
                                                     "tests/conftest.py": CONFTEST_V51U, "tests/plug_uf.py": PLUG_V51U,
                                                     UCD: T_UCD, UCM: T_UCM, UMOD: T_UMOD})
    return {"repo": r, "sid": {p: _run_with(r, [], p) for p in (UCD, UCM, UMOD)}}


def test_u_session_scope_autouse_transitive_plugin_param_fixture_not_enumerable(ra_trans):
    """(u) test_tr 不請求任何 fixture；外掛中 autouse 之 outer 依賴帶 params 之 inner（前提：整檔 session 中 2 筆）⇒
    session_scope 以「不可靜態列舉」為理由不成立（不展開 autouse 遞移依賴之實作會少算為 1）。"""
    recs = test_records(ra_trans["repo"], ra_trans["sid"])
    assert sum(1 for n in recs if n.startswith(f"{PT}::test_tr[")) == 2
    errs = testreg.session_scope_errors(_ctx(ra_trans["repo"]), ra_trans["sid"], f"{PT}::test_tr")
    assert any("不可靜態列舉" in e for e in errs), errs


def test_v_session_scope_class_decorator_usefixtures_plugin_param_not_enumerable(ra_uf):
    """(v) 類別裝飾器 @pytest.mark.usefixtures("ufx")（前提：2 筆）⇒「不可靜態列舉」（不讀類別裝飾器層會少算為 1）。"""
    sid = ra_uf["sid"][UCD]
    assert sum(1 for n in test_records(ra_uf["repo"], sid) if n.startswith(f"{UCD}::TestUcd::test_c[")) == 2
    errs = testreg.session_scope_errors(_ctx(ra_uf["repo"]), sid, f"{UCD}::TestUcd::test_c")
    assert any("不可靜態列舉" in e for e in errs), errs


def test_w_session_scope_class_pytestmark_usefixtures_plugin_param_not_enumerable(ra_uf):
    """(w) 類別本體 pytestmark = pytest.mark.usefixtures("ufx")（前提：2 筆）⇒「不可靜態列舉」（不讀類別 pytestmark 層會少算
    為 1）。"""
    sid = ra_uf["sid"][UCM]
    assert sum(1 for n in test_records(ra_uf["repo"], sid) if n.startswith(f"{UCM}::TestUcm::test_c[")) == 2
    errs = testreg.session_scope_errors(_ctx(ra_uf["repo"]), sid, f"{UCM}::TestUcm::test_c")
    assert any("不可靜態列舉" in e for e in errs), errs


def test_x_session_scope_module_pytestmark_usefixtures_plugin_param_not_enumerable(ra_uf):
    """(x) 模組層 pytestmark = pytest.mark.usefixtures("ufx")（前提：2 筆）⇒「不可靜態列舉」（不讀模組 pytestmark 層會少算
    為 1）。"""
    sid = ra_uf["sid"][UMOD]
    assert sum(1 for n in test_records(ra_uf["repo"], sid) if n.startswith(f"{UMOD}::test_m[")) == 2
    errs = testreg.session_scope_errors(_ctx(ra_uf["repo"]), sid, f"{UMOD}::test_m")
    assert any("不可靜態列舉" in e for e in errs), errs


# ── v52（修訂審查 r50 處置；只增）──────────────────────────────────────────────────────────────────────────────────
# (z)(z2)(z3)：session_scope ② 之模組層 pytestmark 參數化（pytest.param 元素）、他模組基底、類別本體 params fixture
MP, XB, CB = "tests/test_mp.py", "tests/test_xb.py", "tests/test_cb.py"
T_MP = ('import pytest\n\npytestmark = pytest.mark.parametrize("x", [pytest.param(1, id="one"), pytest.param(2, id="two")])'
        '\n\n\ndef test_m(x):\n    assert x > 0\n')
HELPER_BASE = "class Base:\n    pass\n"
T_XB = "from tests.helper_base import Base\n\n\nclass TestC(Base):\n    def test_a(self):\n        assert True\n"
T_CB = ("import pytest\n\n\nclass TestCb:\n    @pytest.fixture(params=[1, 2])\n    def cfx(self, request):\n"
        "        return request.param\n\n    def test_c(self, cfx):\n        assert cfx > 0\n")


@pytest.fixture(scope="module")
def ra_v52s(tmp_path_factory) -> Dict[str, Any]:
    """(z)(z2)(z3) 共用暫存 repo（無 autouse，各檔互不影響）；各檔各跑一 session（整檔）。"""
    r = make_repo(tmp_path_factory.mktemp("ra_v52s"), {"momentum/__init__.py": "", "momentum/other.py": OTHER,
                                                       "tests/helper_base.py": HELPER_BASE, MP: T_MP, XB: T_XB, CB: T_CB})
    return {"repo": r, "sid": {p: _run_with(r, [], p) for p in (MP, XB, CB)}}


def test_z_session_scope_module_pytestmark_parametrize_pytest_param_enumerable(ra_v52s):
    """(z) 模組層 pytestmark = pytest.mark.parametrize("x", [pytest.param(…), pytest.param(…)])（前提：2 筆）⇒ 靜態列舉
    為 2、與紀錄數相符，session_scope 成立（不讀模組 pytestmark 之參數化層、或不把 pytest.param 計為一案之實作會不符）。"""
    sid = ra_v52s["sid"][MP]
    recs = test_records(ra_v52s["repo"], sid)
    assert sorted(n for n in recs if n.startswith(f"{MP}::test_m[")) == [f"{MP}::test_m[one]", f"{MP}::test_m[two]"]
    assert testreg.session_scope_errors(_ctx(ra_v52s["repo"]), sid, f"{MP}::test_m") == []


def test_z2_session_scope_base_class_from_other_module_not_enumerable(ra_v52s):
    """(z2) 測試類別之基底自他模組匯入（同模組解析不到、非 object；前提：1 筆）⇒ 以「不可靜態列舉」為理由不成立
    （把「基底解析不到」當作略過之實作會列舉為 1 而放行）。"""
    sid = ra_v52s["sid"][XB]
    assert [n for n in test_records(ra_v52s["repo"], sid) if n.startswith(f"{XB}::TestC::test_a")] == \
        [f"{XB}::TestC::test_a"]
    errs = testreg.session_scope_errors(_ctx(ra_v52s["repo"]), sid, f"{XB}::TestC::test_a")
    assert any("不可靜態列舉" in e for e in errs), errs


def test_z3_session_scope_class_body_param_fixture_not_enumerable(ra_v52s):
    """(z3) 測試類別本體內 @pytest.fixture(params=[1, 2]) 被方法請求（前提：2 筆）⇒「不可靜態列舉」（只掃模組頂層 fixture
    之實作會少算為 1）。"""
    sid = ra_v52s["sid"][CB]
    assert sum(1 for n in test_records(ra_v52s["repo"], sid) if n.startswith(f"{CB}::TestCb::test_c[")) == 2
    errs = testreg.session_scope_errors(_ctx(ra_v52s["repo"]), sid, f"{CB}::TestCb::test_c")
    assert any("不可靜態列舉" in e for e in errs), errs


# (aa1)–(aa4)：情境綁定之 R(t) 納入實際套用之 fixture 閉包（K4-1）；只看 R 相關錯誤，故不需真實 session（虛 session 用合法格式之
#    uuid 與 hex，使收據通過形狀檢查而進入後段；各案先斷言已到達後段〔unverifiable 出現〕以防空心）
ABSENT_BASE, ABSENT_MUT, ABSENT_FP = ("00000000-0000-4000-8000-0000000000b1", "00000000-0000-4000-8000-0000000000b2",
                                     "0" * 64)
K4 = "tests/test_k4.py"
K4_CONFTEST = ('import pytest\n\n\n@pytest.fixture\ndef adder():\n    from momentum.calc import add\n    return add\n\n\n'
               '@pytest.fixture\ndef unused_fx():\n    from momentum.calc import safe_div\n    return safe_div\n\n\n'
               '@pytest.fixture(autouse=True)\ndef _env_tag():\n    from momentum.calc import tag\n    return tag\n')
T_K4 = ('import pytest\n\n\ndef test_fx_arg(adder):\n    try:\n        assert adder(1, 1) == 2\n    except Exception:\n'
        '        return False\n\n\nclass TestAuto:\n    @pytest.fixture(autouse=True)\n    def _imp(self):\n'
        '        from momentum.calc import scale\n        self.scale = scale\n\n    def test_cls_auto(self):\n'
        '        try:\n            assert self.scale(2) == 4\n        except Exception:\n            return False\n\n\n'
        'def test_doc_only():\n    assert "x" in "xyz"\n')
K4_NEW = T_K4.replace("import pytest\n", "import pytest\nfrom momentum.calc import add, scale\n", 1) + \
    "\n\ndef test_add_and_scale_direct():\n    assert add(1, 1) == 2\n    assert scale(2) == 4\n"
K4_TARGETS = [f"{K4}::test_fx_arg", f"{K4}::TestAuto::test_cls_auto", f"{K4}::test_doc_only"]


@pytest.fixture(scope="module")
def ra_k4(tmp_path_factory) -> Dict[str, Any]:
    """(aa) 暫存 repo：conftest 有被請求之 adder、未被請求之 unused_fx、目錄層 autouse 之 _env_tag；測試類別有類別內
    autouse（函式內匯入 scale 掛到 self）。改寫只新增 test_add_and_scale_direct；收據之 session 為虛（只驗 R 相關錯誤）。"""
    r = make_repo(tmp_path_factory.mktemp("ra_k4"), {"momentum/__init__.py": "", "momentum/calc.py": CALC_GOOD,
                                                     "tests/conftest.py": K4_CONFTEST, K4: T_K4})
    cat = r.catalog()
    cat["entries"][K4].update(entry(K4, disposition="rewrite", rewrite_targets=K4_TARGETS, disposition_ref=APPROVAL))
    r.set_catalog(cat)
    r.write(APPROVAL, f"# approval\n{K4}\n")
    mp = f"{MUT_DIR}/k4_m_add.patch"
    msha = write_patch(r, "momentum/calc.py", CALC_GOOD.replace("    return a + b\n", "    return a - b\n", 1), mp)
    cp = "handoffs/run_receipts/testreg-additive/k4.compare.patch"
    csha = write_patch(r, K4, K4_NEW, cp)
    head = r.commit("k4")
    r.write(K4, K4_NEW)
    r.write_json(additive_rel(K4), {
        "path": K4, "head": head, "approval_ref": APPROVAL, "fingerprint": ABSENT_FP, "compare_patch_path": cp,
        "compare_patch_sha256": csha, "added_nodeids": [f"{K4}::test_add_and_scale_direct"],
        "baseline_session_id": ABSENT_BASE, "mutants": [{"id": "m_add", "patch_path": mp, "patch_sha256": msha,
                                                         "session_id": ABSENT_MUT}]})
    return {"repo": r, "errs": testreg.additive_rewrite_errors(_ctx(r), K4) or []}


def test_aa1_fixture_argument_symbols_enter_scenario(ra_k4):
    """(aa1) test_fx_arg 經 fixture 參數 adder（函式內匯入 add）使用生產碼 ⇒ R 非空、且新增函式引用 add 即滿足 ⊆（不遍歷
    fixture 之實作判為「未引用任何生產符號」）。前提：已到達後段（unverifiable）。"""
    assert any("unverifiable" in e for e in ra_k4["errs"]), ra_k4["errs"]
    assert not [e for e in ra_k4["errs"] if "test_fx_arg" in e and "情境綁定" in e and "定義" not in e], ra_k4["errs"]


def test_aa2_class_autouse_local_import_enters_scenario(ra_k4):
    """(aa2) TestAuto::test_cls_auto 經類別內 autouse fixture 之函式內匯入取得 scale ⇒ R 含 scale、新增函式引用 scale 即
    滿足（不遍歷類別內 autouse 之實作判為「未引用任何生產符號」）。前提：已到達後段（unverifiable）。"""
    assert any("unverifiable" in e for e in ra_k4["errs"]), ra_k4["errs"]
    assert not [e for e in ra_k4["errs"] if "test_cls_auto" in e and "情境綁定" in e and "定義" not in e], ra_k4["errs"]


def test_aa3_directory_autouse_is_environment_not_scenario(ra_k4):
    """(aa3) test_doc_only 不經生產碼；conftest 之目錄層 autouse _env_tag 雖匯入 tag，屬環境不入 R ⇒ 仍「未引用任何生產符號」
    （本收據不適用）（把目錄層 autouse 納入之實作使 R＝{tag} 而不報）。"""
    assert any("test_doc_only" in e and "未引用任何生產符號" in e for e in ra_k4["errs"]), ra_k4["errs"]


def test_aa4_visible_but_unrequested_fixture_not_in_scenario(ra_k4):
    """(aa4) conftest 之 unused_fx（匯入 safe_div）可見但未被 test_fx_arg 請求 ⇒ 不入 R；新增函式未引用 safe_div 不報
    （把「可見」當「套用」之實作會要求引用 safe_div）。前提：已到達後段（unverifiable）。"""
    assert any("unverifiable" in e for e in ra_k4["errs"]), ra_k4["errs"]
    assert not [e for e in ra_k4["errs"] if "safe_div" in e], ra_k4["errs"]


# (ab)：情境綁定之殺 mutant 須改動 R(t) 中之符號定義（非僅同檔）
N_SCALED = f"{GB}::test_quick_scaled"
GB_V52 = {"other_symbol": T_GB.replace("from momentum.calc import add, safe_div\n",
                                       "from momentum.calc import add, safe_div\nfrom momentum.calc import scale\n", 1)
          + "\n\ndef test_quick_scaled():\n    assert safe_div(scale(3), 3) == 2\n"}


@pytest.fixture(scope="module")
def ra_ab(tmp_path_factory) -> Dict[str, Any]:
    """(ab) 暫存 repo：舊目標 test_quick 只引用 safe_div；新增 test_quick_scaled 由 m_scale（改同檔之 scale）殺。"""
    r = make_repo(tmp_path_factory.mktemp("ra_ab"), {"momentum/__init__.py": "", "momentum/calc.py": CALC_GOOD,
                                                     "momentum/other.py": OTHER, GB: T_GB})
    cat = r.catalog()
    cat["entries"][GB].update(entry(GB, disposition="rewrite", rewrite_targets=[N_QUICK], disposition_ref=APPROVAL))
    r.set_catalog(cat)
    r.write(APPROVAL, f"# approval\n{GB}\n")
    f, old, new = MUTANTS["m_scale"]
    mp = f"{MUT_DIR}/ab_m_scale.patch"
    msha = write_patch(r, f, r.read(f).replace(old, new, 1), mp)
    cp = "handoffs/run_receipts/testreg-additive/ab.compare.patch"
    csha = write_patch(r, GB, GB_V52["other_symbol"], cp)
    head = r.commit("ab")
    base = _run_with(r, [cp], GB)
    kill = _run_with(r, [cp, mp], GB)
    return {"repo": r, "head": head, "cp": cp, "csha": csha, "mp": mp, "msha": msha, "base": base, "kill": kill}


def test_ab_binding_requires_killer_to_modify_referenced_symbol(ra_ab, tmp_path):
    """(ab) 前提：m_scale 殺 test_quick_scaled、test_quick 對之盲。只附 m_scale（改同檔之 scale，非舊目標所引用之
    safe_div）⇒ 情境綁定不成立（以補丁所改之頂層定義判定；只看所改之檔之實作會放行）。"""
    fx = ra_ab
    recs = test_records(fx["repo"], fx["kill"])
    assert recs[N_SCALED]["outcome"] == "failed" and recs[N_QUICK]["outcome"] == "passed"
    r = _work(fx, tmp_path, "ab")
    _apply(r, GB, GB_V52["other_symbol"])
    r.write_json(additive_rel(GB), {
        "path": GB, "head": fx["head"], "approval_ref": APPROVAL, "fingerprint": _dc(fx, fx["base"], fx["kill"]),
        "compare_patch_path": fx["cp"], "compare_patch_sha256": fx["csha"], "added_nodeids": [N_SCALED],
        "baseline_session_id": fx["base"],
        "mutants": [{"id": "m_scale", "patch_path": fx["mp"], "patch_sha256": fx["msha"], "session_id": fx["kill"]}]})
    errs = testreg.additive_rewrite_errors(_ctx(r), GB)
    assert any("情境綁定" in e and "定義" in e for e in errs), errs


# (y1)–(y7)：G-c 之混合分支 if（K5）
YM, YN, YC, YB = "tests/test_ym.py", "tests/test_yn.py", "tests/test_yc.py", "tests/test_yb.py"
T_YM = 'from momentum.calc import add\n\na = add(1, 2)\nif a == 3:\n    print("ok")\nelse:\n    print("bad")\n    exit(1)\n'
T_YN = ('from momentum.calc import add\n\na = add(1, 2)\nif a == 3:\n    print("ok")\nelse:\n    for _ in range(1):\n'
        '        exit(2)\n    exit(1)\n')  # else 有直接子敘述之 exit(1)，另有迴圈內之 exit(2)
T_YC = 'from momentum.calc import add\n\nif add(1, 2) == 3:\n    print("ok")\nelse:\n    exit(1)\n'
T_YB = 'from momentum.calc import add\n\na = add(1, 2)\nif a == 3:\n    print("ok")\n    exit(0)\nelse:\n    exit(1)\n'
_YM_FN = ('from momentum.calc import add\n\n\ndef test_ym():\n    a = add(1, 2)\n    if a == 3:\n        print("ok")\n'
          '    else:\n        print("bad")\n')
Y_VARIANTS = {  # 名稱：(檔, 改寫後全文, 期望理由子字串〔None＝G-c 無錯〕)
    "ok": (YM, _YM_FN + "    assert a == 3\n", None),
    "no_assert": (YM, _YM_FN, "緊接"),
    "wrong_cond": (YM, _YM_FN + "    assert a >= 3\n", "緊接"),
    "not_adjacent": (YM, _YM_FN + '    print("done")\n    assert a == 3\n', "緊接"),
    "nested": (YN, 'from momentum.calc import add\n\n\ndef test_yn():\n    a = add(1, 2)\n    if a == 3:\n'
                   '        print("ok")\n    else:\n        for _ in range(1):\n            pass\n    assert a == 3\n', "不適用"),
    "call_cond": (YC, 'from momentum.calc import add\n\n\ndef test_yc():\n    if add(1, 2) == 3:\n        print("ok")\n'
                      '    assert add(1, 2) == 3\n', "不適用"),
    "both_sides": (YB, 'from momentum.calc import add\n\n\ndef test_yb():\n    a = add(1, 2)\n    if a == 3:\n'
                       '        print("ok")\n    assert a == 3\n', "不適用"),
}


@pytest.fixture(scope="module")
def ra_y(tmp_path_factory) -> Dict[str, Any]:
    """(y) 暫存 repo：四個 G-c 原檔為 head（rewrite、rewrite_targets 空）；各變體之 compare patch；session 為虛（只驗 G-c
    結構錯誤）。"""
    r = make_repo(tmp_path_factory.mktemp("ra_y"), {"momentum/__init__.py": "", "momentum/calc.py": CALC_GOOD,
                                                    YM: T_YM, YN: T_YN, YC: T_YC, YB: T_YB})
    cat = r.catalog()
    for p in (YM, YN, YC, YB):
        cat["entries"][p].update(entry(p, disposition="rewrite", rewrite_targets=[], disposition_ref=APPROVAL))
    r.set_catalog(cat)
    r.write(APPROVAL, f"# approval\n{YM} {YN} {YC} {YB}\n")
    mp = f"{MUT_DIR}/y_m_add.patch"
    msha = write_patch(r, "momentum/calc.py", CALC_GOOD.replace("    return a + b\n", "    return a - b\n", 1), mp)
    cps = {}
    for k, (p, text, _why) in Y_VARIANTS.items():
        rel = f"handoffs/run_receipts/testreg-additive/y_{k}.compare.patch"
        cps[k] = (rel, write_patch(r, p, text, rel))
    head = r.commit("y")
    return {"repo": r, "head": head, "mp": mp, "msha": msha, "cps": cps}


def _y_errs(fx, tmp_path, variant: str) -> List[str]:
    p, text, _why = Y_VARIANTS[variant]
    r = _work(fx, tmp_path, f"y_{variant}")
    _apply(r, p, text)
    fn = text.split("def ", 1)[1].split("(", 1)[0]
    r.write_json(additive_rel(p), {
        "path": p, "head": fx["head"], "approval_ref": APPROVAL, "fingerprint": ABSENT_FP,
        "compare_patch_path": fx["cps"][variant][0], "compare_patch_sha256": fx["cps"][variant][1],
        "added_nodeids": [f"{p}::{fn}"], "baseline_session_id": ABSENT_BASE,
        "mutants": [{"id": "m_add", "patch_path": fx["mp"], "patch_sha256": fx["msha"], "session_id": ABSENT_MUT}]})
    errs = testreg.additive_rewrite_errors(_ctx(r), p) or []
    assert any("unverifiable" in e for e in errs), errs  # 前提：已過形狀檢查、到達後段
    return [e for e in errs if e.startswith("G-c")]


def test_y1_gc_mixed_if_stripped_with_adjacent_assert_valid(ra_y, tmp_path):
    """(y1) 檔尾 if 之 else 含印出與 exit(1)：搬入時剝除 exit、緊接 assert a == 3 ⇒ G-c 結構無錯。"""
    assert _y_errs(ra_y, tmp_path, "ok") == []


@pytest.mark.parametrize("variant", ["no_assert", "wrong_cond", "not_adjacent"])
def test_y2_gc_mixed_if_requires_adjacent_same_condition_assert(ra_y, tmp_path, variant):
    """(y2–y4) 缺 assert、assert 條件與原 if 不同（AST）、assert 不緊接 ⇒ 以「緊接 assert 其條件」為理由不成立。"""
    errs = _y_errs(ra_y, tmp_path, variant)
    assert any(Y_VARIANTS[variant][2] in e for e in errs), errs


@pytest.mark.parametrize("variant", ["nested", "call_cond", "both_sides"])
def test_y5_gc_exit_outside_rule_not_applicable(ra_y, tmp_path, variant):
    """(y5–y7) else 除直接之 exit(1) 外另有迴圈內之 exit(2)（非 if 本體／else 之直接子敘述）、條件含呼叫（再求值有副作用之虞）、兩側皆有結束類
    ⇒ 以「本收據不適用」為理由不成立。"""
    errs = _y_errs(ra_y, tmp_path, variant)
    assert any(Y_VARIANTS[variant][2] in e for e in errs), errs
