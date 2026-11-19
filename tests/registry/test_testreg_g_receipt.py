"""TESTSEL I8 Task 1.2（docs/TESTSEL_I8_SPEC.md，規則 v2）：TESTREG V19 接受 §G 前後收據（`kind: g_before_after`）。

使用者 2026-11-19 裁定（AskUserQuestion 選「§G 前後收據代替（建議）」）：I8 改窄之測試以 §G mutant 前後收據為證，免做
V19 逐斷言 rewrite 收據。暫存 git 倉＋真實記錄器 pytest（`testreg_helpers.recorded_pytest`）：產品碼 `momentum/calc.py`；
測試檔兩函式——`test_wide`（x=1、x=3 兩斷言，改窄後只留 x=1 ⇒ 斷言多重集合減少 ⇒ V19）、`test_other`（x=5，不改）。
mutant 外掛（倉根、已提交；`-p mut_*` 載入，於 pytest_configure 改產品函式）：
- mut_all：scale 恆錯 ⇒ 改前、改後兩函式皆紅
- mut_x3：只 x=3 錯 ⇒ 改前 test_wide 紅、改後綠（偵測力下降）
- mut_x35：x=3、x=5 錯 ⇒ 改前兩函式皆紅、改後只 test_other 紅（「任一」判法會漏、逐 target 須擋）
- mut_same：改成等價實作 ⇒ 全綠（規則⑥）
- mut_fail：不碰產品碼、只 pytest.fail（規則②）
改前 session 於乾淨 HEAD（外掛與改窄補丁已提交）；改後 session 只多套改窄補丁（diff_digest＝`_digest_with(head, [patch])`）。
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Mapping

import pytest

from tests.registry.testreg_helpers import (TmpRepo, copy_repo, entry, make_repo, recorded_pytest, rule_lines,
                                            test_records, write_patch)

TF = "tests/test_g.py"
WIDE_ID, OTHER_ID = f"{TF}::test_wide", f"{TF}::test_other"
TARGETS = [OTHER_ID, WIDE_ID]
CALC = "def scale(x):\n    return 2.0 * x\n"
WIDE = ("from momentum.calc import scale\n\n\ndef test_wide():\n    assert scale(1.0) == 2.0\n"
        "    assert scale(3.0) == 6.0\n\n\ndef test_other():\n    assert scale(5.0) == 10.0\n")
NARROW = WIDE.replace("    assert scale(3.0) == 6.0\n", "")
_HDR = "def pytest_configure(config):\n    import momentum.calc as c\n    o = c.scale\n"
PLUGINS = {
    "mut_all": _HDR + "    c.scale = lambda x: 3.0 * x\n",
    "mut_x3": _HDR + "    c.scale = lambda x: 0.0 if x == 3.0 else o(x)\n",
    "mut_x35": _HDR + "    c.scale = lambda x: 0.0 if x in (3.0, 5.0) else o(x)\n",
    "mut_same": _HDR + "    c.scale = lambda x: x + x\n",
    "mut_fail": "import pytest\n\n\ndef pytest_runtest_setup(item):\n    pytest.fail('boom')\n",
    # r5 GROK-R5-P1-01：無害改產品碼過靜態掃描＋setup hook 恆失敗造假「前後皆紅」
    "mut_forge": (_HDR + "    c.scale = lambda x: x + x\n\n\nimport pytest\n\n\n"
                  "def pytest_runtest_setup(item):\n    pytest.fail('forged')\n"),
    # r6 GROK-R6-P1-01：模組層只 pytest_configure，於其內動態註冊 call 期 hook 造假失敗（phase＝call）
    "mut_forge_register": (_HDR + "    c.scale = lambda x: x + x\n\n    class _F:\n"
                           "        def pytest_runtest_call(self, item):\n"
                           "            raise AssertionError('forged-call')\n\n"
                           "    config.pluginmanager.register(_F(), 'forge')\n"),
}
PATCH = "handoffs/run_receipts/testsel-i8/test_g.narrow.patch"
RCPT = "handoffs/run_receipts/testsel-i8/test_g.json"
SPEC = "docs/TESTSEL_I8_SPEC.md"
RULING = "2026-11-19 使用者 AskUserQuestion：§G 前後收據代替（建議）"


def _sha(r: TmpRepo, rel: str) -> str:
    return hashlib.sha256(r.p(rel).read_bytes()).hexdigest()


def _run(r: TmpRepo, *args: str) -> str:
    _proc, ids = recorded_pytest(r, *args)
    assert len(ids) == 1, ids
    return ids[0]


@pytest.fixture(scope="module")
def base(tmp_path_factory) -> Dict[str, Any]:
    files = {"momentum/__init__.py": "", "momentum/calc.py": CALC, TF: WIDE}
    files.update({f"{m}.py": src for m, src in PLUGINS.items()})
    r = make_repo(tmp_path_factory.mktemp("g"), files)
    patch_sha = write_patch(r, TF, NARROW, PATCH)
    head = r.commit("narrow patch")  # 補丁檔提交 ⇒ 改前 session 之樹乾淨
    before = {m: _run(r, "-p", m, TF) for m in PLUGINS}
    before["k_filtered"] = _run(r, "-p", "mut_all", "-k", "test_wide", TF)
    r.write("junk.txt", "x")
    before["dirty"] = _run(r, "-p", "mut_all", TF)
    r.delete("junk.txt")
    r.write(TF, NARROW)
    after = {m: _run(r, "-p", m, TF) for m in PLUGINS}
    r.write("junk.txt", "x")
    after["dirty"] = _run(r, "-p", "mut_all", TF)
    r.delete("junk.txt")
    r.write(TF, WIDE)
    return {"repo": r, "head": head, "patch_sha": patch_sha, "before": before, "after": after}


def _outcomes(r: TmpRepo, sid: str) -> Dict[str, str]:
    recs = test_records(r, sid)
    return {t: recs[t]["outcome"] for t in TARGETS if t in recs}


def _mutant(fx: Mapping[str, Any], m: str, *, before_key: str = None, after_key: str = None) -> Dict[str, Any]:
    r = fx["repo"]
    b, a = fx["before"][before_key or m], fx["after"][after_key or m]
    return {"id": m, "plugin_path": f"{m}.py", "plugin_sha256": _sha(r, f"{m}.py"),
            "before_session_id": b, "after_session_id": a,
            "before_outcomes": _outcomes(r, b), "after_outcomes": _outcomes(r, a)}


def _receipt(fx: Mapping[str, Any], mutants: List[Dict[str, Any]], **over: Any) -> Dict[str, Any]:
    rc = {"kind": "g_before_after", "spec_ref": SPEC, "user_ruling": RULING, "head": fx["head"],
          "targets": list(TARGETS), "narrow_patch_path": PATCH, "narrow_patch_sha256": fx["patch_sha"],
          "mutants": mutants}
    rc.update(over)
    return rc


def _apply(r: TmpRepo, rcpt: Mapping[str, Any] = None, *, text: str = NARROW) -> None:
    r.write(TF, text)
    if rcpt is not None:
        r.write_json(RCPT, rcpt)
    r.put_entry(entry(TF, disposition="rewrite", rewrite_targets=list(TARGETS), disposition_ref=SPEC,
                      rewrite_receipt=RCPT if rcpt is not None else None))


def _check(r: TmpRepo):
    r.stage(".")
    return r.run("check", "--staged")


def _red(r: TmpRepo, why: str = "") -> bool:
    """V19／V07 擋下；給 why 時另須有含該字樣之 finding（確定是被預期之規則擋，非他條順帶）。"""
    proc = _check(r)
    lines = rule_lines(proc, "V19") + rule_lines(proc, "V07")
    return proc.returncode != 0 and bool(lines) and (not why or any(why in ln for ln in lines))


def _ok_mutants(fx) -> List[Dict[str, Any]]:
    return [_mutant(fx, "mut_all"), _mutant(fx, "mut_same")]


def test_fixture_premises(base):
    r = base["repo"]
    o = lambda side, m: _outcomes(r, base[side][m])  # noqa: E731
    assert o("before", "mut_all") == {WIDE_ID: "failed", OTHER_ID: "failed"}
    assert o("after", "mut_all") == {WIDE_ID: "failed", OTHER_ID: "failed"}
    assert o("before", "mut_x3") == {WIDE_ID: "failed", OTHER_ID: "passed"}
    assert o("after", "mut_x3") == {WIDE_ID: "passed", OTHER_ID: "passed"}
    assert o("before", "mut_x35") == {WIDE_ID: "failed", OTHER_ID: "failed"}
    assert o("after", "mut_x35") == {WIDE_ID: "passed", OTHER_ID: "failed"}
    assert o("before", "mut_same") == {WIDE_ID: "passed", OTHER_ID: "passed"}


def test_no_receipt_v19_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, None)
    proc = _check(r)
    assert proc.returncode != 0 and rule_lines(proc, "V19"), proc.stdout + proc.stderr


def test_valid_receipt_green(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, _ok_mutants(base)))
    proc = _check(r)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_targets_mismatch_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, _ok_mutants(base), targets=[WIDE_ID]))
    assert _red(r, "targets ≠ catalog")


def test_outcomes_missing_target_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_all")
    m["after_outcomes"].pop(OTHER_ID)
    _apply(r, _receipt(base, [m, _mutant(base, "mut_same")]))
    assert _red(r, "_outcomes 鍵 ≠ targets")


def test_plugin_sha_mismatch_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_all")
    m["plugin_sha256"] = "0" * 64
    _apply(r, _receipt(base, [m]))
    assert _red(r, "外掛不存在或 sha256 不符")


def test_plugin_not_touching_production_red(base, tmp_path):
    """規則②：外掛只 pytest.fail、不改產品碼 ⇒ 改前改後皆 error 亦不得放行。"""
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_fail")]))
    assert _red(r, "外掛未改 production_roots")


def test_plugin_forging_failures_via_extra_hook_red(base, tmp_path):
    """r5 GROK-R5-P1-01：外掛另定 pytest_runtest_setup 恆失敗（改前改後皆 error）⇒ 規則②擋（只准 pytest_configure）。"""
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_forge")]))
    assert _red(r, "外掛未改 production_roots")


def test_plugin_forging_via_dynamic_hook_registration_red(base, tmp_path):
    """r6 GROK-R6-P1-01：pytest_configure 內動態註冊 pytest_runtest_call 恆失敗（call 期、前後皆紅）⇒ 失敗 frame 不在
    target 函式本體 ⇒ 不計抓到 ⇒ 規則⑥擋。改壞對照：拿掉 frame 限制 ⇒ 本條轉綠（測試須紅）。"""
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_forge_register")]))
    assert _red(r, "偵測力證明為空")


def test_session_missing_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_all")
    m["after_session_id"] = "00000000-0000-4000-8000-000000000000"
    _apply(r, _receipt(base, [m]))
    assert _red(r, "session 相同或不在 ledger")


def test_same_session_as_before_and_after_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_all", after_key=None)
    m["after_session_id"] = m["before_session_id"]
    m["after_outcomes"] = dict(m["before_outcomes"])
    _apply(r, _receipt(base, [m]))
    assert _red(r, "session 相同或不在 ledger")


def test_after_earlier_than_before_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_all")
    m["before_session_id"], m["after_session_id"] = m["after_session_id"], m["before_session_id"]
    m["before_outcomes"], m["after_outcomes"] = m["after_outcomes"], m["before_outcomes"]
    _apply(r, _receipt(base, [m]))
    assert _red(r, "before session 未早於 after")


def test_before_not_clean_tree_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_all", before_key="dirty")]))
    assert _red(r, "before session 非乾淨樹")


def test_after_digest_not_from_narrow_patch_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_all", after_key="dirty")]))
    assert _red(r, "after session diff_digest")


def test_narrow_patch_differs_from_tree_red(base, tmp_path):
    """受驗之樹之測試檔與「head＋改窄補丁」不同（再改一字）⇒ 擋。"""
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, _ok_mutants(base)), text=NARROW.replace("== 10.0", "== 10.0 or True"))
    assert _red(r, "改窄補丁套於 head 後之測試檔")


def test_plugin_token_mismatch_red(base, tmp_path):
    """argv 之 `-p` 下一 token 非收據所列外掛（以 mut_all 之 session 冒充 mut_x35）⇒ 擋。"""
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_all")
    m["id"], m["plugin_path"], m["plugin_sha256"] = "mut_x35", "mut_x35.py", _sha(base["repo"], "mut_x35.py")
    _apply(r, _receipt(base, [m]))
    assert _red(r, "未以 -p mut_x35 載入外掛")


def test_session_filtered_with_k_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_all", before_key="k_filtered")
    _apply(r, _receipt(base, [m]))
    assert _red(r, "mut_all before：")


def test_outcome_mismatch_ledger_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    m = _mutant(base, "mut_x3")
    m["after_outcomes"][WIDE_ID] = "failed"  # ledger 實為 passed
    _apply(r, _receipt(base, [_mutant(base, "mut_all"), m]))
    assert _red(r, "與 ledger 不符")


def test_detection_drop_red(base, tmp_path):
    """規則⑤：mut_x3 之 test_wide 改前紅、改後綠 ⇒ 擋。改壞對照：刪除規則⑤之檢查 ⇒ 本條轉綠（測試須紅）。"""
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_all"), _mutant(base, "mut_x3")]))
    assert _red(r, "偵測力下降")


def test_detection_moves_to_other_target_red(base, tmp_path):
    """規則⑤逐 target：mut_x35 改前兩函式紅、改後只 test_other 紅（「任一」判法會放行）⇒ 擋。"""
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_all"), _mutant(base, "mut_x35")]))
    assert _red(r, "偵測力下降")


def test_all_mutants_green_before_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, [_mutant(base, "mut_same")]))
    assert _red(r, "偵測力證明為空")


def test_head_mismatch_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, _ok_mutants(base), head="f" * 40))
    assert _red(r, "收據 head")


def test_wrong_spec_ref_red(base, tmp_path):
    r = copy_repo(base["repo"], tmp_path, "r")
    _apply(r, _receipt(base, _ok_mutants(base), spec_ref="docs/OTHER_SPEC.md"))
    assert _red(r, "spec_ref 須為")
