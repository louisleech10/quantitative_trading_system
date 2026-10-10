"""TESTREG TODO 腳手架試跑：不經記錄器，驗 mutant 補丁可套與 junit 結果／行號符合測試之構造。"""
import sys, tempfile, xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, "/Users/louis/Desktop/quantitative_trading_system")
import tests.registry.test_testreg_validate as V
from tests.registry.testreg_helpers import make_repo, recorded_pytest, write_patch

def junit(r, patches, *ids):
    for p in patches: r.git("apply", p)
    try:
        proc, _ = recorded_pytest(r, "--junitxml=j.xml", "--tb=long", *ids, plugin=False)
    finally:
        for p in reversed(patches): r.git("apply", "-R", p)
    out = {}
    for c in ET.parse(r.p("j.xml")).iter("testcase"):
        st = "passed"
        for tag in ("failure", "error", "skipped"):
            el = c.find(tag)
            if el is not None:
                st = tag; txt = (el.text or "")
                locs = [l.split(":")[0:2] for l in txt.splitlines() if l.startswith("tests/") and ":" in l]
                st += " " + ",".join(":".join(x) for x in locs[-2:])
        out[c.get("name")] = st
    r.delete("j.xml")
    return out

tmp = Path(tempfile.mkdtemp())
r = make_repo(tmp, {"momentum/__init__.py": "", "momentum/calc.py": V.M_CALC, V.MF: V.M_TESTS, V.NF: V.N_TESTS})
pp = {}
for m in V.MUTANTS:
    V._patch_for(r, m); pp[m] = f"handoffs/run_receipts/testreg-mutants/{m}.patch"
r.commit("p")
rw = "rw.patch"; write_patch(r, V.MF, r.read(V.MF).replace(V.REWRITE_OLD, V.REWRITE_NEW), rw)
ren = "ren.patch"; write_patch(r, V.MF, r.read(V.MF).replace(V.RENAME_OLD, V.RENAME_NEW), ren)
r.commit("c")
for m in ("m_add", "m_scale", "m_guard", "m_noop", "m_legacy", "m_testfile"):
    print(m, junit(r, [pp[m]], *V.M_IDS))
for m in ("m_raise", "m_raise3"):
    print(m, junit(r, [pp[m]], V.NF))
print("rw+m_add", junit(r, [rw, pp["m_add"]], f"{V.MF}::test_old"))
print("ren+m_legacy", junit(r, [ren, pp["m_legacy"]], f"{V.MF}::test_dep_renamed"))
print("lines", V._old_lines(r))
e = make_repo(tmp, {"momentum/__init__.py": "", "momentum/calc.py": V.E0_CALC_A, "tests/__init__.py": "",
                    "tests/util_mod.py": V.E0_UTIL_A, "tests/helper_gone.py": V.E0_HELPER, V.E0_FILE: V.E0_TESTS}, name="e0")
e.write("momentum/calc.py", V.CALC); e.write("tests/util_mod.py", "def other():\n    return 0\n"); e.commit("rm")
print("e0", junit(e, [], V.E0_FILE))
