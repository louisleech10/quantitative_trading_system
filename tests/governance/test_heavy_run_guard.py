"""NOCAP Task 0.3：重型命令須背景執行且經共用監看（scripts/heavy_run_guard.py）。秒級、不跑重型。"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("heavy_run_guard", REPO / "scripts" / "heavy_run_guard.py")
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)  # type: ignore[union-attr]


def _bash(command: str, background: bool) -> Dict[str, Any]:
    return {"tool_name": "Bash", "tool_input": {"command": command, "run_in_background": background}}


def _rc(payload: Any) -> int:
    return g.main(json.dumps(payload) if not isinstance(payload, str) else payload)


WRAP = "venv/bin/python scripts/run_watched.py --log /tmp/x.log -- "


@pytest.fixture(autouse=True)
def _empty_ledger(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """守衛之 TESTREG ledger 判定一律先指向空 ledger（隔離本機紀錄、結果不隨機器而變）；ledger 案（test_ledger_*）
    以 `_ledger` 改指受控內容。"""
    monkeypatch.setattr(g, "LEDGER_DIR", tmp_path_factory.mktemp("ledger_empty") / "ledger")


@pytest.mark.parametrize("cmd,background,expected", [
    # 自帶監看之量測：須背景
    ("venv/bin/python scripts/ffprod_measure.py run --cell C_BTCUSDT_1h", False, 2),
    # 背景、但無估時與成長曲線收據 ⇒ 擋（NOCAP Task 0.3b／0.3c）；committee_run 背景放行見下（estimate_exempt）
    ("venv/bin/python scripts/ffprod_measure.py run --cell C_BTCUSDT_1h", True, 2),
    ("venv/bin/python scripts/ffprod_measure.py plan --cell C_BTCUSDT_1h", False, 0),  # plan 非重型
    # 重型 pytest：須包裝且背景
    ("venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q", True, 2),
    (WRAP + "venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q", False, 2),
    # 經包裝且背景、但無估時收據 ⇒ 擋（NOCAP Task 0.3c；有相符收據之放行見 boundary 51）
    (WRAP + "venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q", True, 2),
    ("venv/bin/python -m pytest tests/feature_engineering/test_ffprod_measure.py -q", False, 0),  # 輕量
    ("venv/bin/python -m pytest -q", True, 2),  # 無參數全套
    ("venv/bin/python -m pytest tests -x -q", True, 2),  # 帶選項之全套（b1 審碼 r1 CODEX-R1-P1-05）
    ("venv/bin/python -m pytest -q -p no:cacheprovider tests/governance", True, 2),
    ("venv/bin/python -m pytest ./tests -q", True, 2),  # 路徑別名（b1 審碼 r2 CODEX-R2-P1-01）
    ("venv/bin/python -m pytest tests/. -q", True, 2),
    ("venv/bin/python -m pytest . -q", True, 2),
    ("venv/bin/python -m pytest -k watchdog tests/feature_engineering/test_numview_criteria.py -q", False, 0),
    # 委員派工：須背景
    ("bash scripts/committee_run.sh --session s brief out codex,composer", False, 2),
    ("bash scripts/committee_run.sh --session s brief out codex,composer", True, 0),
    ("git status --short", False, 0),
    # 只比對執行位置（2026-10-27 實測舊版逐字比對全文之誤擋）
    ("pgrep -fl 'pytest|ffprod_measure|generate_features'", False, 0),
    ("grep -n 'venv/bin/python -m pytest -q' docs/NOCAP_SPEC.md", False, 0),
    ("echo 'bash scripts/committee_run.sh --session s'", False, 0),
    ("bash scripts/list_active_mechanisms.sh --write", False, 0),  # 檔內只於名單／case 樣式提到 committee_run
    ("bash scripts/template_check.sh spec docs/NOCAP_SPEC.md", False, 0),  # 檔內只於正則／註解提到 pytest
    ("bash -c \"pgrep -fl 'pytest|x'\"", False, 0),
    # 仍須擋：分隔符、前置變數與前綴、bash -c、多行、子殼
    ("cd /tmp && venv/bin/python -m pytest -q", True, 2),
    ("git status; venv/bin/python scripts/ffprod_measure.py run --cell C_BTCUSDT_1h", False, 2),
    ("FOO=1 nohup venv/bin/python scripts/ffprod_measure.py run --cell C_BTCUSDT_1h", False, 2),
    ("bash -c 'venv/bin/python -m pytest -q'", True, 2),
    ("git status\nvenv/bin/python scripts/ffprod_measure.py ic --cell C_BTCUSDT_1h", False, 2),
    ("(venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q) > /tmp/o.log 2>&1", True, 2),
    ("ls | venv/bin/python -m pytest -q", True, 2),
    ("echo \"unterminated venv/bin/python -m pytest -q", False, 2),  # 引號不成對 ⇒ 全文比對（保守）
    # 包裝只認該命令本身：另一段落提到包裝不算
    ("echo scripts/run_watched.py; venv/bin/python -m pytest -q", True, 2),
])
def test_heavy_command_rules(cmd: str, background: bool, expected: int) -> None:
    assert _rc(_bash(cmd, background)) == expected


ICPERF_GATE = "venv/bin/python -m pytest -q -p no:cacheprovider tests/momentum/Analysis/test_icperf_gate.py"


@pytest.mark.parametrize("cmd,background,expected", [
    # 正例（命中 pytest_icperf_gate）：前景直跑、-k 篩到重型、背景未包裝、包裝背景但無估時收據 ⇒ 擋
    (ICPERF_GATE, False, 2),
    (ICPERF_GATE + " -k test_freeze_reproducible", False, 2),
    (ICPERF_GATE + " -m slow", True, 2),
    (WRAP + ICPERF_GATE, True, 2),
    # 末個 -m 生效：非重型篩選之後又帶 -m ⇒ 仍命中
    (ICPERF_GATE + " -m 'not slow and not requires_kline' -m slow", False, 2),
    # 豁免式後又延伸表示式（引號內 `or slow`／`or requires_kline`）⇒ 選到重型，仍命中；豁免式後接位置參數 ⇒ fail-closed 命中
    (ICPERF_GATE + " -m 'not slow and not requires_kline or slow'", False, 2),
    (ICPERF_GATE + " -m \"not slow and not requires_kline or requires_kline\"", False, 2),
    ("venv/bin/python -m pytest -q -m 'not slow and not requires_kline' tests/momentum/Analysis/test_icperf_gate.py",
     False, 2),
    # 反例：最後一個 -m 恰為排除全部重型與真實資料測試之篩選 ⇒ 非重型、前景放行
    (ICPERF_GATE + " -m 'not slow and not requires_kline'", False, 0),
    (ICPERF_GATE + " -m 'not slow and not requires_kline' -k boundary_06", False, 0),
    (ICPERF_GATE + " -m \"not slow and not requires_kline\" > /tmp/x.log 2>&1; echo rc=$?", False, 0),
    (ICPERF_GATE + " -m 'not slow and not requires_kline' 2> /tmp/x.err", False, 0),
    # `-m=EXPR` 與 `-m EXPR` 等價（r12 CODEX-R12-P2-04）
    (ICPERF_GATE + " -m='not slow and not requires_kline'", False, 0),
    (ICPERF_GATE + " -m='not slow and not requires_kline or slow'", False, 2),
])
def test_icperf_gate_pytest_is_heavy(cmd: str, background: bool, expected: int) -> None:
    """ICPERF 施工清單審查 r10 群集 A：test_icperf_gate 之 pytest 須經共用監看並背景（非重型篩選除外）。"""
    assert _rc(_bash(cmd, background)) == expected


ICPERF_CORRECTNESS = "venv/bin/python -m pytest -q -p no:cacheprovider tests/momentum/Analysis/test_icperf_correctness.py"


@pytest.mark.parametrize("cmd,background,expected", [
    # 正例（命中 pytest_icperf_correctness）：前景直跑、-k 篩到重型、背景未包裝、包裝背景但無估時收據 ⇒ 擋
    (ICPERF_CORRECTNESS, False, 2),
    (ICPERF_CORRECTNESS + " -k coverage_closed", False, 2),
    (ICPERF_CORRECTNESS + " -m requires_kline", True, 2),
    (WRAP + ICPERF_CORRECTNESS, True, 2),
    # 末個 -m 生效；豁免式後延伸表示式或接位置參數 ⇒ 命中（fail-closed）
    (ICPERF_CORRECTNESS + " -m 'not slow and not requires_kline' -m slow", False, 2),
    (ICPERF_CORRECTNESS + " -m 'not slow and not requires_kline or requires_kline'", False, 2),
    ("venv/bin/python -m pytest -q -m 'not slow and not requires_kline' tests/momentum/Analysis/test_icperf_correctness.py",
     False, 2),
    (ICPERF_CORRECTNESS + " -m='not slow and not requires_kline or slow'", False, 2),
    # 與 test_icperf_gate 同一命令：任一列命中即擋
    (ICPERF_CORRECTNESS + " tests/momentum/Analysis/test_icperf_gate.py -m 'not slow and not requires_kline' -m slow",
     False, 2),
    # 反例：最後一個 -m 恰為排除全部重型與真實資料測試之篩選 ⇒ 非重型、前景放行
    (ICPERF_CORRECTNESS + " -m 'not slow and not requires_kline'", False, 0),
    (ICPERF_CORRECTNESS + " -m 'not slow and not requires_kline' -k hac", False, 0),
    (ICPERF_CORRECTNESS + " -m \"not slow and not requires_kline\" > /tmp/x.log 2>&1; echo rc=$?", False, 0),
    (ICPERF_CORRECTNESS + " -m 'not slow and not requires_kline' 2> /tmp/x.err", False, 0),
    (ICPERF_CORRECTNESS + " -m='not slow and not requires_kline'", False, 0),
])
def test_icperf_correctness_pytest_is_heavy(cmd: str, background: bool, expected: int) -> None:
    """ICPERF Task 0.3：test_icperf_correctness 之 pytest 須經共用監看並背景（非重型篩選除外；豁免語意同
    pytest_icperf_gate）。"""
    assert _rc(_bash(cmd, background)) == expected


def test_executed_script_body_only_counts_command_position() -> None:
    """執行之 repo 內 .sh：檔內真的執行之重型命令擋；註解、字串、grep 樣式、`${x#y}` 後之下一行皆照實判定。"""
    helper = REPO / "handoffs" / "run_receipts" / ".nocap-guardtest-body.sh"
    helper.write_text("#!/usr/bin/env bash\n# bash scripts/committee_run.sh 只是註解\n"
                      "echo 'venv/bin/python -m pytest -q'\ngrep -q 'scripts/committee_run.sh' x\n"
                      'case "$1" in\n  scripts/gate.sh|scripts/committee_run.sh) : ;;\n  *) echo ok ;;\nesac\n'
                      'y="${HOME#/}"\n', encoding="utf-8")
    try:
        assert _rc(_bash(f"bash {helper}", False)) == 0  # case 樣式中之 committee_run 非命令
        assert _rc(_bash(f"ls {helper}", False)) == 0 and _rc(_bash(f"cat {helper}", False)) == 0
        base = helper.read_text(encoding="utf-8")
        helper.write_text(base + "bash scripts/committee_run.sh --session s b o c\n", encoding="utf-8")
        assert _rc(_bash(f"bash {helper}", False)) == 2  # `${HOME#/}` 後之下一行仍為獨立命令
        helper.write_text(base + 'case "$1" in\n  a|b) venv/bin/python -m pytest -q ;;\nesac\n', encoding="utf-8")
        assert _rc(_bash(f"bash {helper}", True)) == 2  # case 分支內真的執行之全套 pytest（未包裝）
        assert _rc(_bash(f"ls {helper}", False)) == 0  # 未執行
    finally:
        helper.unlink()


def test_indirect_helper_script_is_expanded_with_args(tmp_path: Path) -> None:
    """經 repo 內輔助 .sh（內含 "$@"）轉呼叫之重型命令亦被比對：以實際參數代入後判定。"""
    helper = REPO / "handoffs" / "run_receipts" / ".nocap-guardtest-helper.sh"
    helper.write_text('#!/usr/bin/env bash\nvenv/bin/python -m pytest "$@" -q\n', encoding="utf-8")
    try:
        cmd = f"bash {helper} tests/feature_engineering/test_ffprod_gate.py"
        assert _rc(_bash(cmd, True)) == 2  # 未經包裝
        cmd2 = f"bash {helper} tests/feature_engineering/test_ffprod_measure.py"
        assert _rc(_bash(cmd2, False)) == 0  # 輕量
    finally:
        helper.unlink()


def test_self_watched_sources_really_call_shared_watchdog() -> None:
    """清單之 self_watched 腳本皆確實呼叫共用監看 run_watched(（機械對證；移除即擋）。以守衛同一 AST 判定（呼叫節點），
    不以原始碼字串命中——docstring 或註解提到 run_watched( 不算（ICPERF 施工清單審查 r13 CODEX-R13-P1-02）。"""
    catalog = json.loads((REPO / "scripts" / "heavy_commands.json").read_text(encoding="utf-8"))
    for rule in catalog["self_watched"]:
        assert "run_watched(" in (REPO / rule["source"]).read_text(encoding="utf-8"), rule
        assert g.calls_run_watched(REPO / rule["source"]), rule
    fake = {"self_watched": [{"id": "x", "regex": "scripts/x_heavy\\.py", "source": "scripts/heavy_run_guard.py"}]}
    problems = g.check(_bash("venv/bin/python scripts/x_heavy.py", True), fake)
    assert problems and "未呼叫共用監看" in problems[0]
    doc_only = REPO / "handoffs" / "run_receipts" / ".nocap-guardtest-doconly.py"
    doc_only.write_text('"""只在說明提到 run_watched(，未呼叫。"""\n# run_watched(\nx = "run_watched("\n', encoding="utf-8")
    try:
        assert not g.calls_run_watched(doc_only)
    finally:
        doc_only.unlink()


def test_unreadable_payload_blocks_and_other_tools_pass() -> None:
    assert _rc("garbage") == 2
    assert _rc({"tool_name": "Edit", "tool_input": {}}) == 0


def test_hook_is_wired_and_fast() -> None:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for m in settings["hooks"]["PreToolUse"] if "Bash" in m["matcher"] for h in m["hooks"]]
    assert "bash scripts/heavy_run_guard.sh" in cmds
    start = time.perf_counter()
    rc = subprocess.run(["bash", str(REPO / "scripts" / "heavy_run_guard.sh")],
                        input=json.dumps(_bash("ls", False)), text=True, capture_output=True).returncode
    assert rc == 0 and time.perf_counter() - start < 1.0


def test_run_watched_wrapper_reports_stall_with_diagnosis(tmp_path: Path) -> None:
    """包裝器：正常命令回其 rc；不輸出亦不耗 CPU 之命令 ⇒ 判卡死、rc 4、留現場檔（門檻以判準檔為準，此處改注入小門檻）。"""
    spec = importlib.util.spec_from_file_location("run_watched_mod", REPO / "scripts" / "run_watched.py")
    rw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rw)  # type: ignore[union-attr]
    assert rw.main(["--log", str(tmp_path / "ok.log"), "--", "python3", "-c", "print('ok')"]) == 0
    wd = rw._watchdog()
    real_load = wd.load_config

    def fast(criteria: Any) -> Any:
        cfg = real_load(criteria)
        return wd.WatchdogConfig(check_interval_seconds=0.05, log_stall_seconds=0.4,
                                 swap_growth_fraction_of_ram=None, swap_consecutive_checks=2,
                                 wall_multiple_of_expected=cfg.wall_multiple_of_expected,
                                 wall_ceiling_seconds=cfg.wall_ceiling_seconds)

    wd.load_config = fast
    rw._watchdog = lambda: wd
    log = tmp_path / "hang.log"
    assert rw.main(["--log", str(log), "--", "python3", "-c", "import time; time.sleep(20)"]) == 4
    assert Path(str(log) + ".stall_diagnosis.json").is_file()


# ── NOCAP SPEC v2–v5 增修（Task 0.3／0.3b／0.3c）；施工前為紅 ─────────────────────────────────────────────

def _mod(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"{name}_hrg", REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.mark.parametrize("cmd", [
    "printf x | xargs -I{} venv/bin/python -m pytest -q",
    "find . -name x -exec venv/bin/python -m pytest -q \\;",
    "eval \"venv/bin/python -m pytest -q\"",
    "$PY -m pytest -q",
])
def test_boundary_26_dynamic_launch_inner_command_judged(cmd: str) -> None:
    """xargs／find -exec／eval 之內層命令遞迴判定；命令位置為未解析變數 ⇒ argv 全文比對（保守）。背景未包裝 ⇒ 擋。"""
    assert _rc(_bash(cmd, True)) == 2


def test_boundary_27_readonly_xargs_grep_allowed() -> None:
    """`ls | xargs grep pytest` 之內層為 grep（非啟動器）⇒ 放行（不一律 fail-closed）。"""
    assert _rc(_bash("ls | xargs grep pytest", False)) == 0


def _chain(depth: int, last: str) -> Path:
    """建 depth 層 .sh 鏈（第 i 層呼叫第 i+1 層，末層執行 `last`），回第一層路徑。"""
    paths = [REPO / "handoffs" / "run_receipts" / f".nocap-guardtest-l{i}.sh" for i in range(depth)]
    for i, p in enumerate(paths):
        body = f"bash {paths[i + 1]}\n" if i + 1 < depth else f"{last}\n"
        p.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    return paths[0]


def _unchain(depth: int) -> None:
    for i in range(depth):
        (REPO / "handoffs" / "run_receipts" / f".nocap-guardtest-l{i}.sh").unlink(missing_ok=True)


def test_boundary_28_two_level_sh_heavy_blocked() -> None:
    """兩層 .sh（outer → inner → 全套 pytest）前景 ⇒ 擋（遞迴至不再出現新 .sh）。"""
    try:
        assert _rc(_bash(f"bash {_chain(2, 'venv/bin/python -m pytest -q')}", False)) == 2
    finally:
        _unchain(2)


def test_boundary_29_beyond_depth_limit_fail_closed() -> None:
    """六層 .sh（逾深度上限 5）⇒ 擋（fail-closed），即使末層只 echo。"""
    try:
        assert _rc(_bash(f"bash {_chain(6, 'echo done')}", False)) == 2
    finally:
        _unchain(6)


def test_boundary_30_two_level_sh_inner_echo_allowed() -> None:
    """兩層而內層只 echo 重型字樣 ⇒ 放行。"""
    try:
        assert _rc(_bash(f"bash {_chain(2, 'echo venv/bin/python -m pytest -q')}", False)) == 0
    finally:
        _unchain(2)


@pytest.mark.parametrize("cmd", [
    "venv/bin/python scripts/ic1eb_b5_replay.py",
    "venv/bin/python scripts/capture_ic1eb_baseline.py",
    "venv/bin/python scripts/ic1c_freeze_baseline.py",
    "venv/bin/python tests/golden/ic_phase1_contract/freeze_baseline.py",
    "venv/bin/python tests/golden/ic_phase1_1a_cut1/freeze_baseline.py",
    "venv/bin/python tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py",
    "bash scripts/measure_ic_footprint.sh",
    "venv/bin/python scripts/verify_l1_warmup_requirements.py",
    "venv/bin/python scripts/framepath_affected_gate.py --plan",
    "bash scripts/cx_run.sh codex brief.md out.md",
    "venv/bin/python scripts/scale_probe.py --scale 500 --scale 1000 --scale 2000",
])
def test_boundary_31_listed_entrypoints_foreground_blocked(cmd: str) -> None:
    """SPEC Task 0.3「清單涵蓋」與 0.3b 起始例外：各 Phase 所列每個可執行入口前景直跑 ⇒ 擋。"""
    assert _rc(_bash(cmd, False)) == 2


def test_boundary_32_every_settings_hook_script_exists() -> None:
    """`.claude/settings.json` 每個 hook 指令所指之 repo 腳本皆存在（移除 block_busywait.sh 死掛載）。"""
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    missing = []
    for event in settings["hooks"].values():
        for m in event:
            for h in m["hooks"]:
                for tok in str(h.get("command", "")).split():
                    if tok.startswith("scripts/") and not (REPO / tok).is_file():
                        missing.append(tok)
    assert missing == []


def test_boundary_33_receipt_identity_rejects_uncommitted_change_and_byte_change(tmp_path: Path) -> None:
    """收據 match：code_paths 工作樹改一行未提交 ⇒ 失配；輸入檔改一位元組（size 不變）⇒ 失配。"""
    rid = _mod("run_receipt_identity")
    code, data = tmp_path / "entry.py", tmp_path / "in.bin"
    code.write_text("x = 1\n", encoding="utf-8")
    data.write_bytes(b"abcd")
    args = ("entry.py", ["entry.py", "--n", "5"], ["entry.py"], ["in.bin"], [])
    receipt = {"identity": {"match": rid.compute_match(*args, repo=tmp_path), "meta": {"producer": "p", "created_at": "t"}}}
    code.write_text("x = 2\n", encoding="utf-8")
    assert not rid.receipt_matches(receipt, rid.compute_match(*args, repo=tmp_path))
    code.write_text("x = 1\n", encoding="utf-8")
    data.write_bytes(b"abce")
    assert not rid.receipt_matches(receipt, rid.compute_match(*args, repo=tmp_path))


def test_boundary_34_receipt_meta_only_difference_reusable(tmp_path: Path) -> None:
    """只 meta（producer／created_at）不同 ⇒ 可沿用；換 target_argv 一個參數 ⇒ 失配。"""
    rid = _mod("run_receipt_identity")
    (tmp_path / "entry.py").write_text("x = 1\n", encoding="utf-8")
    match = rid.compute_match("entry.py", ["entry.py", "--n", "5"], ["entry.py"], [], [], repo=tmp_path)
    receipt = {"identity": {"match": match, "meta": {"producer": "other", "created_at": "2000-01-01"}}}
    assert rid.receipt_matches(receipt, match)
    other = rid.compute_match("entry.py", ["entry.py", "--n", "6"], ["entry.py"], [], [], repo=tmp_path)
    assert not rid.receipt_matches(receipt, other)


def _pts(seconds: List[float], rss: List[float]) -> List[Dict[str, Any]]:
    return [{"scale": s, "unit": "cols", "seconds": t, "peak_rss_bytes": r}
            for s, t, r in zip([500, 1000, 2000], seconds, rss)]


def test_boundary_35_scale_fit_low_r2_or_non_monotone_unreliable() -> None:
    """成長曲線：r2 < 0.9 或耗時／RSS 隨規模遞減 ⇒ extrapolation_unreliable。"""
    sp = _mod("scale_probe")
    assert sp.fit(_pts([10.0, 100.0, 12.0], [1e8, 2e8, 4e8]), 200_000)["extrapolation_unreliable"] is True
    assert sp.fit(_pts([10.0, 20.0, 40.0], [4e8, 2e8, 1e8]), 200_000)["extrapolation_unreliable"] is True
    assert sp.fit(_pts([10.0, 20.0, 40.0], [1e8, 2e8, 4e8]), 200_000)["extrapolation_unreliable"] is False


def test_boundary_36_projection_is_conservative_max() -> None:
    """推算取冪次擬合與末兩點線性外推之較大者（冪次偏低時取線性外推值）。"""
    sp = _mod("scale_probe")
    out = sp.fit(_pts([10.0, 14.0, 30.0], [1e8, 2e8, 4e8]), 4000)
    linear = 30.0 + (30.0 - 14.0) / (2000 - 1000) * (4000 - 2000)
    assert out["projection"]["seconds"] >= linear - 1e-9


def test_boundary_37_estimate_coverage_ids_must_exist_in_spec_budget_table() -> None:
    """估時收據之 coverage_path_ids 須為 SPEC §B 預算表之列 id。"""
    rid = _mod("run_receipt_identity")
    spec = (REPO / "docs" / "NOCAP_SPEC.md").read_text(encoding="utf-8")
    assert rid.coverage_ids_valid({"coverage_path_ids": ["NOCAP-BUDGET-1"]}, spec) is True
    assert rid.coverage_ids_valid({"coverage_path_ids": ["NOCAP-BUDGET-9"]}, spec) is False


def test_boundary_38_heavy_command_without_estimate_receipt_blocked() -> None:
    """Task 0.3c：重型命令（背景且經包裝）無估時收據 ⇒ 擋。"""
    assert _rc(_bash(WRAP + "venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q", True)) == 2


def test_boundary_49_scale_probe_background_without_receipt_allowed() -> None:
    """Task 0.3b 起始例外：scale_probe 背景執行且無任何收據 ⇒ 放行（不要求其自身收據）。"""
    assert _rc(_bash("venv/bin/python scripts/scale_probe.py --scale 500 --scale 1000 --scale 2000", True)) == 0


def test_boundary_50_scale_probe_writes_receipt_with_accurate_projection(tmp_path: Path,
                                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """scale_probe 以三規模點產出收據：points 3 點、projection 對注入之線性耗時（秒＝規模／1000）誤差 < 5%。"""
    sp = _mod("scale_probe")

    class _Res:
        def __init__(self, seconds: float) -> None:
            self.status, self.returncode, self.wall_seconds, self.peak_rss_bytes = "exited", 0, seconds, int(1e8 * seconds)

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        return _Res(float(kwargs["scale"]) / 1000.0)

    monkeypatch.setattr(sp, "run_watched", fake_run)
    out = tmp_path / "x-scale.json"
    rc = sp.main(["--out", str(out), "--full-scale", "8000", "--scale", "500", "--scale", "1000", "--scale", "2000",
                  "--", "python3", "-c", "pass"])
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0 and len(receipt["points"]) == 3
    assert [p["scale"] for p in receipt["points"]] == [500, 1000, 2000]
    assert all({"scale", "unit", "seconds", "peak_rss_bytes"} <= set(p) for p in receipt["points"])
    assert {"model", "exponent", "r2"} <= set(receipt["fit"]) and receipt["fit"]["r2"] >= 0.9
    assert {"scale", "seconds", "peak_rss_bytes"} <= set(receipt["projection"]) and receipt["projection"]["scale"] == 8000
    assert set(receipt["identity"]) == {"match", "meta"} and receipt["superlinear"] is False
    assert abs(receipt["projection"]["seconds"] - 8.0) / 8.0 < 0.05 and receipt["extrapolation_unreliable"] is False


def test_boundary_51_heavy_command_with_valid_estimate_receipt_allowed(tmp_path: Path) -> None:
    """Task 0.3c：重型命令背景且經包裝、且有 identity 相符與 coverage id 有效之估時收據 ⇒ 放行。"""
    rid = _mod("run_receipt_identity")
    inner = ["venv/bin/python", "-m", "pytest", "tests/feature_engineering/test_ffprod_gate.py", "-q"]
    match = rid.compute_match("tests/feature_engineering/test_ffprod_gate.py", inner,
                              ["tests/feature_engineering/test_ffprod_gate.py"], [], [])
    receipt = REPO / "handoffs" / "run_receipts" / "20261027-nocap-guardtest-estimate.json"
    receipt.write_text(json.dumps({"identity": {"match": match, "meta": {"producer": "test", "created_at": "t"}},
                                   "scale": "single", "estimate_seconds": 60, "basis": [], "spec_path": "docs/NOCAP_SPEC.md",
                                   "coverage_path_ids": ["NOCAP-BUDGET-3"]}), encoding="utf-8")
    try:
        assert _rc(_bash(WRAP + " ".join(inner), True)) == 0
    finally:
        receipt.unlink()


@pytest.mark.parametrize("break_field", ["target_argv", "code_sha256", "coverage"])
def test_boundary_56_heavy_command_with_mismatched_estimate_receipt_blocked(break_field: str) -> None:
    """Task 0.3c：估時收據 identity 之 target_argv 或 code_sha256 不符、或 coverage id 不在 §B 表 ⇒ 擋。"""
    rid = _mod("run_receipt_identity")
    inner = ["venv/bin/python", "-m", "pytest", "tests/feature_engineering/test_ffprod_gate.py", "-q"]
    match = rid.compute_match("tests/feature_engineering/test_ffprod_gate.py", inner,
                              ["tests/feature_engineering/test_ffprod_gate.py"], [], [])
    coverage = ["NOCAP-BUDGET-3"]
    if break_field == "coverage":
        coverage = ["NOCAP-BUDGET-9"]
    else:
        match = {**match, break_field: "0" * 64 if break_field == "code_sha256" else "venv/bin/python -m pytest -q"}
    receipt = REPO / "handoffs" / "run_receipts" / "20261027-nocap-guardtest-estimate.json"
    receipt.write_text(json.dumps({"identity": {"match": match, "meta": {"producer": "test", "created_at": "t"}},
                                   "scale": "single", "estimate_seconds": 60, "basis": [], "spec_path": "docs/NOCAP_SPEC.md",
                                   "coverage_path_ids": coverage}), encoding="utf-8")
    try:
        assert _rc(_bash(WRAP + " ".join(inner), True)) == 2
    finally:
        receipt.unlink()


@pytest.mark.parametrize("drop", ["scale", "estimate_seconds", "basis", "spec_path"])
def test_estimate_receipt_missing_required_field_blocked(drop: str) -> None:
    """Task 0.3c：估時收據缺必填欄（scale、estimate_seconds、basis、spec_path）⇒ 擋（b2 審碼 r1 CODEX-R1-P1-01）。"""
    rid = _mod("run_receipt_identity")
    inner = ["venv/bin/python", "-m", "pytest", "tests/feature_engineering/test_ffprod_gate.py", "-q"]
    match = rid.compute_match("tests/feature_engineering/test_ffprod_gate.py", inner,
                              ["tests/feature_engineering/test_ffprod_gate.py"], [], [])
    body = {"identity": {"match": match, "meta": {"producer": "test", "created_at": "t"}}, "scale": "single",
            "estimate_seconds": 60, "basis": [], "spec_path": "docs/NOCAP_SPEC.md", "coverage_path_ids": ["NOCAP-BUDGET-3"]}
    del body[drop]
    receipt = REPO / "handoffs" / "run_receipts" / "20261027-nocap-guardtest-estimate.json"
    receipt.write_text(json.dumps(body), encoding="utf-8")
    try:
        assert _rc(_bash(WRAP + " ".join(inner), True)) == 2
    finally:
        receipt.unlink()


@pytest.mark.parametrize("variant,expected", [("valid", 0), ("two_points", 2), ("code_mismatch", 2),
                                              ("unreliable", 2), ("missing", 2), ("hardware_mismatch", 2),
                                              ("empty_points", 2), ("no_fit", 2)])
def test_scale_receipt_gate_for_full_scale_command(variant: str, expected: int) -> None:
    """Task 0.3b：設 scale_receipt 之重型命令（ffprod_measure）背景執行且有效估時收據下——成長曲線收據有效 ⇒ 放行；
    只 2 點、程式碼態雜湊不符、標 extrapolation_unreliable、或無收據 ⇒ 擋。"""
    rid = _mod("run_receipt_identity")
    argv = ["venv/bin/python", "scripts/ffprod_measure.py", "run", "--cell", "C_BTCUSDT_1h"]
    match = rid.compute_match("scripts/ffprod_measure.py", argv, [], [], [])
    rr = REPO / "handoffs" / "run_receipts"
    est, scale = rr / "20261027-nocap-guardtest-estimate.json", rr / "20261027-nocap-guardtest-ffprod_measure-scale.json"
    est.write_text(json.dumps({"identity": {"match": match, "meta": {"producer": "test", "created_at": "t"}},
                               "scale": "single", "estimate_seconds": 60, "basis": [], "spec_path": "docs/NOCAP_SPEC.md",
                               "coverage_path_ids": ["NOCAP-BUDGET-3"]}), encoding="utf-8")
    pts = _pts([10.0, 20.0, 40.0], [1e8, 2e8, 4e8])
    receipt = {"identity": {"match": match, "meta": {"producer": "test", "created_at": "t"}}, "points": pts,
               "fit": {"model": "power", "exponent": 1.0, "r2": 1.0},
               "projection": {"scale": 8000, "seconds": 160.0, "peak_rss_bytes": 1.6e9},
               "extrapolation_unreliable": False}
    if variant == "two_points":
        receipt["points"] = pts[:2]
    elif variant == "code_mismatch":
        receipt["identity"]["match"] = {**match, "code_sha256": "0" * 64}
    elif variant == "unreliable":
        receipt["extrapolation_unreliable"] = True
    elif variant == "hardware_mismatch":  # b2 審碼 r1 COMPOSER-R1-P1-01：他機收據不得沿用
        receipt["identity"]["match"] = {**match, "hardware": {"cpu": "fake", "cores": 1, "ram_bytes": 1, "os": "Fake"}}
    elif variant == "empty_points":  # b2 審碼 r1 CODEX-R1-P1-01：點欄位不齊即無效
        receipt["points"] = [{}, {}, {}]
    elif variant == "no_fit":
        del receipt["fit"]
    if variant != "missing":
        scale.write_text(json.dumps(receipt), encoding="utf-8")
    try:
        assert _rc(_bash(" ".join(argv), True)) == expected
    finally:
        est.unlink(missing_ok=True)
        scale.unlink(missing_ok=True)


def test_mutation_depth_zero_misses_two_level_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：不展開被執行之 .sh（讀檔一律回 None）⇒ 一層 .sh 內之全套 pytest 漏擋（遞迴展開之鑑別力；逾深度上限
    之 fail-closed 不受此改壞影響，故改壞點選在讀檔）。"""
    monkeypatch.setattr(g, "_script_body", lambda *a, **k: None)
    try:
        assert _rc(_bash(f"bash {_chain(1, 'venv/bin/python -m pytest -q')}", False)) == 0
    finally:
        _unchain(1)


# ── 估時收據 × TESTREG ledger 交叉檢查（docs/TEST_SELECTION.md §4；2026-11-11 L1c 估時低估事故）────────────────

_GATE = "tests/feature_engineering/test_ffprod_gate.py"
_LEDGER_ROWS = [(f"{_GATE}::test_a", 300.0), (f"{_GATE}::test_b", 200.0), (f"{_GATE}::test_b", 150.0)]


def _ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """隔離 ledger：test_a 300 秒、test_b 兩筆取最大 200 秒 ⇒ 全檔加總 500 秒。"""
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "s.jsonl").write_text("".join(json.dumps({"nodeid": n, "duration_s": s, "outcome": "passed"}) + "\n"
                                       for n, s in _LEDGER_ROWS),
                               encoding="utf-8")
    monkeypatch.setattr(g, "LEDGER_DIR", d)


_CLOSE = {"tier": "close", "tier_reason": "測試：收案跑累積全受影響"}


def _ledger_rc(inner: List[str], estimate: float, extra: Dict[str, Any] = None) -> int:
    rid = _mod("run_receipt_identity")
    match = rid.compute_match(_GATE, inner, [_GATE], [], [])
    receipt = REPO / "handoffs" / "run_receipts" / "20261111-hrgledger-guardtest-estimate.json"
    receipt.write_text(json.dumps({"identity": {"match": match, "meta": {"producer": "test", "created_at": "t"}},
                                   "scale": "single", "estimate_seconds": estimate, "basis": [],
                                   "spec_path": "docs/NOCAP_SPEC.md", "coverage_path_ids": ["NOCAP-BUDGET-3"],
                                   **(extra or {})}), encoding="utf-8")
    try:
        return _rc(_bash(WRAP + " ".join(inner), True))
    finally:
        receipt.unlink()


def test_ledger_01_estimate_below_ledger_sum_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                     capsys: pytest.CaptureFixture) -> None:
    """tier＝close、收據 60 秒 < ledger 全檔保守估時 500 秒（整檔選取 ⇒ 無共用 fixture 轉移）⇒ 擋，訊息含估時秒數與
    重型條數。"""
    _ledger(tmp_path, monkeypatch)
    assert _ledger_rc(["venv/bin/python", "-m", "pytest", _GATE, "-q"], 60, _CLOSE) == 2
    err = capsys.readouterr().err
    assert "保守估時 500 秒" in err and "重型 2 條" in err


def test_ledger_02_estimate_at_or_above_sum_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """tier＝close、收據 ≥ ledger 加總（500）⇒ 放行（只擋低估）。"""
    _ledger(tmp_path, monkeypatch)
    assert _ledger_rc(["venv/bin/python", "-m", "pytest", _GATE, "-q"], 500, _CLOSE) == 0


@pytest.mark.parametrize("estimate,expected", [(199, 2), (200, 0)])
def test_ledger_03_trace_select_sums_listed_nodeids_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                         estimate: float, expected: int) -> None:
    """`--trace-select <檔>` ⇒ 只加總所列 nodeid（test_b 200 秒），不以全檔 500 秒誤擋（部分選取、無追蹤 ⇒ 共用 fixture
    成本未知，收據已明示 uncertain_ack）。"""
    _ledger(tmp_path, monkeypatch)
    sel = tmp_path / "sel.txt"
    sel.write_text(f"{_GATE}::test_b\n", encoding="utf-8")
    inner = ["venv/bin/python", "-m", "pytest", "-q", "-p", "scripts.readtrace_plugin", "--trace-select", str(sel), _GATE]
    assert _ledger_rc(inner, estimate, {**_CLOSE, **_ACK1}) == expected


@pytest.mark.parametrize("narrow", [["-k", "test_a"], ["-m", "slow"], ["--deselect", f"{_GATE}::test_a"]])
def test_ledger_04_narrowing_options_skip_cross_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                      narrow: List[str]) -> None:
    """含縮小選取選項 ⇒ 實際選取集不可知，不做估時交叉檢查（依檔加總只是上界）⇒ tier＝close 收據 60 秒放行。"""
    _ledger(tmp_path, monkeypatch)
    assert _ledger_rc(["venv/bin/python", "-m", "pytest", _GATE, "-q"] + narrow, 60, _CLOSE) == 0


@pytest.mark.parametrize("extra,narrow,expected", [
    ({}, [], 2),                                                    # 未宣告 ⇒ batch ⇒ 含重型擋
    ({"tier": "batch"}, [], 2),
    ({"tier": "batch"}, ["-k", "test_a"], 2),                       # 縮小前母集含重型 ⇒ 無從確認 ⇒ 擋
    ({"tier": "close"}, [], 2),                                     # 非 batch 無理由 ⇒ 擋
    ({"tier": "nightly", "tier_reason": "x"}, [], 2),               # 不在封閉集合
    ({"tier": "close", "tier_reason": "L1 收案"}, [], 0),
    ({"tier": "acceptance", "tier_reason": "SPEC 驗收 X"}, [], 0),
    ({"tier": "full", "tier_reason": "定期全量"}, [], 0),
    ({"tier": "fix", "tier_reason": "修復 test_a 後重跑"}, [], 0),
])
def test_ledger_07_tier_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: Dict[str, Any],
                              narrow: List[str], expected: int) -> None:
    """batch（含未宣告）只准快速層；close／acceptance／full／fix 准跑重型但須 tier_reason（TEST_SELECTION §3／§4）。"""
    _ledger(tmp_path, monkeypatch)
    assert _ledger_rc(["venv/bin/python", "-m", "pytest", _GATE, "-q"] + narrow, 10_000, extra) == expected


def test_ledger_08_batch_fast_only_selection_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """tier＝batch 之 --trace-select 只列快速層 nodeid ⇒ 放行（同檔另有重型不影響）。"""
    _ledger(tmp_path, monkeypatch)
    d = tmp_path / "ledger"
    with (d / "s.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"nodeid": f"{_GATE}::test_fast", "duration_s": 2.0, "outcome": "passed"}) + "\n")
    sel = tmp_path / "sel.txt"
    sel.write_text(f"{_GATE}::test_fast\n", encoding="utf-8")
    inner = ["venv/bin/python", "-m", "pytest", "-q", "--trace-select", str(sel), _GATE]
    assert _ledger_rc(inner, 10, {"tier": "batch", "uncertain_ack": {"unknown": 0, "fixture_cost_unknown": 1}}) == 0


_UNLISTED = "tests/zz_unlisted/test_slow_probe.py"


@pytest.mark.parametrize("dur,background,wrap,expected", [
    (120.0, False, False, 2),   # 清單外、ledger 判重型、前景 ⇒ 擋
    (120.0, True, False, 2),    # 背景但未經共用監看 ⇒ 擋
    (120.0, True, True, 2),     # 背景＋監看但無估時收據 ⇒ 擋
    (2.0, False, False, 0),     # 清單外快速層 ⇒ 不受影響
])
def test_ledger_09_unlisted_heavy_pytest_detected_by_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                            dur: float, background: bool, wrap: bool,
                                                            expected: int) -> None:
    """heavy_commands.json 未列之測試檔，ledger 紀錄耗時 ≥60 秒 ⇒ 視同重型（如 ffstat 系列）；快速層不擋。"""
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "s.jsonl").write_text(json.dumps({"nodeid": f"{_UNLISTED}::test_s", "duration_s": dur, "outcome": "passed"}) + "\n",
                               encoding="utf-8")
    monkeypatch.setattr(g, "LEDGER_DIR", d)
    cmd = ("venv/bin/python scripts/run_watched.py --log /tmp/x.log -- " if wrap else "") + \
        f"venv/bin/python -m pytest {_UNLISTED} -q"
    assert _rc(_bash(cmd, background)) == expected


def test_ledger_10_index_incremental_add_change_delete(tmp_path: Path) -> None:
    """增量索引：新增檔被讀入、變動檔重讀、刪除檔移除；索引壞 ⇒ 重建。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "a.jsonl").write_text(json.dumps({"nodeid": "tests/t.py::x", "duration_s": 1.0, "outcome": "passed"}) + "\n",
                               encoding="utf-8")
    assert ld.load_all(d) == {"tests/t.py::x": 1.0}
    (d / "b.jsonl").write_text(json.dumps({"nodeid": "tests/t.py::y", "duration_s": 2.0, "outcome": "passed"}) + "\n",
                               encoding="utf-8")
    assert ld.load_all(d) == {"tests/t.py::x": 1.0, "tests/t.py::y": 2.0}
    (d / "a.jsonl").write_text(json.dumps({"nodeid": "tests/t.py::x", "duration_s": 9.0, "outcome": "passed"}) + "\n" * 2,
                               encoding="utf-8")
    assert ld.load_all(d)["tests/t.py::x"] == 9.0
    (d / "b.jsonl").unlink()
    assert ld.load_all(d) == {"tests/t.py::x": 9.0}
    (tmp_path / "durations_index.json").write_text("{broken", encoding="utf-8")
    assert ld.load_all(d) == {"tests/t.py::x": 9.0}


@pytest.mark.parametrize("argv,expected", [
    (["venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/a.py::t", "tests/b"],
     ["tests/a.py::t", "tests/b"]),
    (["venv/bin/python", "-m", "pytest", "-q"], ["tests"]),
    (["venv/bin/python", "-m", "pytest", "tests/a.py", "-k", "x"], None),
    (["venv/bin/python", "-m", "pytest", "tests/a.py", "-mslow"], None),
    (["venv/bin/python", "scripts/x.py", "tests/a.py"], None),
])
def test_ledger_05_pytest_selector_parsing(argv: List[str], expected: Any) -> None:
    """pytest 之 `-m` 前之 python `-m` 不算縮小選取；帶值選項之值不當測試路徑；無位置參數 ⇒ testpaths。"""
    assert g._pytest_selectors(argv) == expected


def test_ledger_11_collect_only_and_argsfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """只收集／列資訊之 pytest 不執行測試 ⇒ 不做 ledger 檢查；`@參數檔`（pytest ≥8.2）展開為選取，讀不到 ⇒ None。"""
    assert not g._is_pytest(["venv/bin/python", "-m", "pytest", "--collect-only", "-q", "tests/a.py"])
    assert not g._is_pytest(["venv/bin/python", "-m", "pytest", "--co", "tests/a.py"])
    assert g._is_pytest(["venv/bin/python", "-m", "pytest", "-q", "tests/a.py"])
    args = tmp_path / "args.txt"
    args.write_text("tests/a.py::t one\n-q\n\ntests/b\n", encoding="utf-8")
    monkeypatch.setattr(g, "REPO", tmp_path)
    assert g._pytest_selectors(["venv/bin/python", "-m", "pytest", "@args.txt"]) == ["tests/a.py::t one", "tests/b"]
    assert g._pytest_selectors(["venv/bin/python", "-m", "pytest", "@missing.txt"]) is None


def test_ledger_13_latest_uninstrumented_record_wins(tmp_path: Path) -> None:
    """取每 nodeid 最近一次無量測負擔之 session 紀錄（同 pytest-split 存最近一次）；帶 --cov／readtrace 之 session
    只在無其他紀錄時採用。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()

    def write(name: str, argv: List[str], rows: Dict[str, float], mtime: int) -> None:
        p = d / name
        p.write_text(json.dumps({"kind": "session", "argv_raw": argv}) + "\n"
                     + "".join(json.dumps({"kind": "test", "nodeid": n, "duration_s": s, "outcome": "passed"}) + "\n"
                               for n, s in rows.items()),
                     encoding="utf-8")
        os.utime(p, ns=(mtime, mtime))

    write("old.jsonl", ["tests/t.py"], {"tests/t.py::a": 500.0, "tests/t.py::b": 9.0}, 1_000_000_000)
    write("new.jsonl", ["tests/t.py"], {"tests/t.py::a": 20.0}, 2_000_000_000)
    write("cov.jsonl", ["--cov", "tests/t.py"], {"tests/t.py::a": 900.0, "tests/t.py::c": 70.0}, 3_000_000_000)
    assert ld.load_all(d) == {"tests/t.py::a": 20.0, "tests/t.py::b": 9.0, "tests/t.py::c": 70.0}


@pytest.mark.parametrize("token", ["tests/x/test_a.py", "./tests/x/test_a.py", "tests/x/./test_a.py", "tests/x/",
                                   "{repo}/tests/x/test_a.py"])
def test_ledger_14_selector_paths_normalized(tmp_path: Path, token: str) -> None:
    """`./`、絕對路徑、`/.`、尾斜線之選取與 repo 相對拼字歸屬同一 nodeid 集（pytest 依實際路徑解析）。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "s.jsonl").write_text(json.dumps({"nodeid": "tests/x/test_a.py::t", "duration_s": 3.0, "outcome": "passed"}) + "\n",
                               encoding="utf-8")
    assert ld.load_durations([token.format(repo=REPO)], d) == {"tests/x/test_a.py::t": 3.0}


def test_ledger_15_cli_flags_unexpanded_file_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI 以檔案／目錄為輸入時，列入 `_unexpanded.txt`（ledger 外之新測試不會出現在 fast／heavy）；nodeid 輸入不列。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "s.jsonl").write_text(json.dumps({"nodeid": "tests/x/test_a.py::old", "duration_s": 1.0, "outcome": "passed"})
                               + "\n",
                               encoding="utf-8")
    monkeypatch.setattr(ld, "LEDGER_DIR", d)
    lst = tmp_path / "in.txt"
    lst.write_text("tests/x/test_a.py\ntests/x/test_a.py::old\n", encoding="utf-8")
    assert ld.main([str(lst), str(tmp_path / "o")]) == 0
    assert (tmp_path / "o_unexpanded.txt").read_text(encoding="utf-8") == "tests/x/test_a.py\n"
    assert (tmp_path / "o_fast.txt").read_text(encoding="utf-8") == "tests/x/test_a.py::old\n"


def test_ledger_24_cli_nodeid_tokens_not_expanded_to_stale_variants(tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """nodeid 輸入輸出原 token、不展開成 ledger 之參數化變體（ledger 留有已不存在之舊變體，展開後作選取 ⇒ pytest
    not found；2026-11-12 實踩）；無同名紀錄者（含聚合 token：參數化基名、類別）一律 unmatched——ledger 不知現有
    子項全集，取最大或加總皆可能低估（審碼 r9、r10），須以 --collect-only 展開成葉 nodeid 再估。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    _session(d, "s.jsonl", [("tests/x/test_a.py::t[inplace]", 2.0, "passed"), ("tests/x/test_a.py::t[sink]", 70.0, "passed"),
                            ("tests/x/test_a.py::u", 1.0, "passed")], 1_000_000_000)
    monkeypatch.setattr(ld, "LEDGER_DIR", d)
    lst = tmp_path / "in.txt"
    lst.write_text("tests/x/test_a.py::t\ntests/x/test_a.py::u\ntests/x/test_a.py::new\n", encoding="utf-8")
    assert ld.main([str(lst), str(tmp_path / "o")]) == 0
    assert (tmp_path / "o_fast.txt").read_text(encoding="utf-8") == "tests/x/test_a.py::u\n"
    assert (tmp_path / "o_heavy.txt").read_text(encoding="utf-8") == ""
    assert (tmp_path / "o_unmatched.txt").read_text(encoding="utf-8") == "tests/x/test_a.py::t\ntests/x/test_a.py::new\n"
    # 聚合 token：兩參數各 40 秒（最大值 40 會誤入快速層）、類別下只 m1 有紀錄而 m2 為未跑過之新方法（加總 40 會漏 m2）
    _session(d, "s2.jsonl", [("tests/y/test_b.py::p[a]", 40.0, "passed"), ("tests/y/test_b.py::p[b]", 40.0, "passed"),
                             ("tests/y/test_b.py::C::m1", 40.0, "passed")], 2_000_000_000)
    dur, unm = ld.token_durations(["tests/y/test_b.py::p", "tests/y/test_b.py::C", "tests/y/test_b.py::C::m1"],
                                  ld.load_all(d))
    assert dur == {"tests/y/test_b.py::C::m1": 40.0} and unm == ["tests/y/test_b.py::p", "tests/y/test_b.py::C"]


@pytest.mark.parametrize("narrow", ["-k test_s", "--lf", "--deselect tests/zz_unlisted/test_slow_probe.py::x"])
def test_ledger_16_unlisted_narrowed_heavy_still_needs_watch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                             narrow: str) -> None:
    """清單外 pytest 加縮小選取：實際選取不可知，但母集含重型 ⇒ 仍須背景執行（前景擋）。"""
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "s.jsonl").write_text(json.dumps({"nodeid": f"{_UNLISTED}::test_s", "duration_s": 300.0, "outcome": "passed"}) + "\n",
                               encoding="utf-8")
    monkeypatch.setattr(g, "LEDGER_DIR", d)
    assert _rc(_bash(f"venv/bin/python -m pytest {_UNLISTED} -q {narrow}", False)) == 2


def test_ledger_12_unlisted_collect_only_not_heavy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """清單外 pytest 之選取依 ledger 含重型，但只收集 ⇒ 不視同重型（前景可跑）；同命令執行測試 ⇒ 擋。"""
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "s.jsonl").write_text(json.dumps({"nodeid": f"{_UNLISTED}::test_s", "duration_s": 300.0, "outcome": "passed"}) + "\n",
                               encoding="utf-8")
    monkeypatch.setattr(g, "LEDGER_DIR", d)
    assert _rc(_bash(f"venv/bin/python -m pytest --collect-only -q {_UNLISTED}", False)) == 0
    assert _rc(_bash(f"venv/bin/python -m pytest -q {_UNLISTED}", False)) == 2


def test_ledger_06_durations_owner_matching(tmp_path: Path) -> None:
    """ledger_durations：目錄、檔案、nodeid、參數化變體皆歸屬；同 nodeid 取最大值；他檔不計。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    rows = [("tests/x/test_a.py::T::test_p[1]", 5.0), ("tests/x/test_a.py::T::test_p[1]", 7.0),
            ("tests/x/test_b.py::test_q", 3.0), ("tests/y/test_c.py::test_r", 11.0)]
    (d / "s.jsonl").write_text("".join(json.dumps({"nodeid": n, "duration_s": s, "outcome": "passed"}) + "\n"
                                       for n, s in rows) + "not json\n",
                               encoding="utf-8")
    assert ld.load_durations(["tests/x"], d) == {"tests/x/test_a.py::T::test_p[1]": 7.0, "tests/x/test_b.py::test_q": 3.0}
    assert set(ld.load_durations(["tests/x/test_a.py::T"], d)) == {"tests/x/test_a.py::T::test_p[1]"}
    assert set(ld.load_durations(["tests/x/test_a.py::T::test_p"], d)) == {"tests/x/test_a.py::T::test_p[1]"}
    assert ld.load_durations(["tests/x/test_a.py::T::test_p[2]"], d) == {}


def test_mutation_ledger_check_removed_misses_underestimate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：交叉檢查回空 ⇒ test_ledger_01 之低估收據放行（鑑別力）。"""
    _ledger(tmp_path, monkeypatch)
    monkeypatch.setattr(g, "ledger_problems", lambda *a, **k: [])
    assert _ledger_rc(["venv/bin/python", "-m", "pytest", _GATE, "-q"], 60, _CLOSE) == 0


def test_mutation_ledger_heavy_detection_removed_misses_unlisted(tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：清單外 ledger 判定回空 ⇒ test_ledger_09 之前景重型放行（鑑別力）。"""
    d = tmp_path / "ledger"
    d.mkdir()
    (d / "s.jsonl").write_text(json.dumps({"nodeid": f"{_UNLISTED}::test_s", "duration_s": 120.0, "outcome": "passed"}) + "\n",
                               encoding="utf-8")
    monkeypatch.setattr(g, "LEDGER_DIR", d)
    monkeypatch.setattr(g, "ledger_heavy_problems", lambda *a, **k: [])
    assert _rc(_bash(f"venv/bin/python -m pytest {_UNLISTED} -q", False)) == 0


def _session(d: Path, name: str, rows: List[Tuple[str, float, str]], mtime: int, argv: List[str] = None) -> None:
    p = d / name
    p.write_text(json.dumps({"kind": "session", "argv_raw": argv or ["tests"]}) + "\n"
                 + "".join(json.dumps({"kind": "test", "nodeid": n, "duration_s": s, "outcome": o}) + "\n"
                           for n, s, o in rows), encoding="utf-8")
    os.utime(p, ns=(mtime, mtime))


def test_ledger_17_failed_records_not_used_for_estimate(tmp_path: Path) -> None:
    """估時只採通過紀錄：較新之失敗（數秒即中止）不得取代較舊之通過耗時（2026-11-12 事故：dual_start[4h] 失敗 1.9
    秒、通過 2,068 秒）；從未通過者不入耗時表（失敗秒數不是耗時；r5 GROK-R5-P1-01），另列 never、估時列 unknown。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    _session(d, "old.jsonl", [("tests/t.py::slow", 2068.0, "passed"), ("tests/t.py::red", 5.0, "failed")], 1_000_000_000)
    _session(d, "new.jsonl", [("tests/t.py::slow", 1.9, "failed"), ("tests/t.py::red", 0.0, "error")], 2_000_000_000)
    dur, never, gaps = ld.load_all_detail(d)
    assert dur == {"tests/t.py::slow": 2068.0}
    assert never == {"tests/t.py::red"}
    est, det = ld.conservative_estimate(["tests/t.py::red"], dur, gaps)
    assert est == 0.0 and det["unknown"] == ["tests/t.py::red"]


def test_ledger_18_conservative_estimate_adds_fixture_gap(tmp_path: Path) -> None:
    """共用 fixture 建置成本隨選取轉移：b 歷史上當付費者時 200 秒、平時 0.1 秒（gap 199.9）⇒ 只選 b（同檔 a 未選）時
    保守估時 ≥ 200；整檔皆選 ⇒ 不加；追蹤顯示只用 session 範圍 fixture ⇒ 不加。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    _session(d, "s1.jsonl", [("tests/f.py::b", 200.0, "passed")], 1_000_000_000)
    _session(d, "s2.jsonl", [("tests/f.py::a", 180.0, "passed"), ("tests/f.py::b", 0.1, "passed")], 2_000_000_000)
    dur, _never, gaps = ld.load_all_detail(d)
    est, det = ld.conservative_estimate(["tests/f.py::b"], dur, gaps)
    assert det["selected_sum"] == pytest.approx(0.1) and est == pytest.approx(200.0)
    assert ld.conservative_estimate(["tests/f.py::a", "tests/f.py::b"], dur, gaps)[0] == pytest.approx(180.1)
    only_session = {"tests/f.py::b": ["session:::tmp_path_factory"]}
    assert ld.conservative_estimate(["tests/f.py::b"], dur, gaps, only_session)[0] == pytest.approx(0.1)
    module = {"tests/f.py::b": ["module:tests/f.py::m"]}
    est, det = ld.conservative_estimate(["tests/f.py::b"], dur, gaps, module)
    assert est == pytest.approx(200.0) and det["fixture_cost_unknown"] == ["tests/f.py"]  # 以差距代 ⇒ 標未知


def test_ledger_21_fixture_cost_measured_beats_gap(tmp_path: Path) -> None:
    """付費者固定（a 每次先跑 240 秒、b 每次 0.02 秒）⇒ 差距 0、不可觀測（r5 CODEX-R5-P1-03）：無實測成本時估 0.02 但標
    fixture_cost_unknown；有讀檔追蹤實測之 fixture 建置秒數 ⇒ 加實測成本、不標未知。專案 session fixture 亦同。"""
    ld = _mod("ledger_durations")
    d = tmp_path / "ledger"
    d.mkdir()
    for i, name in enumerate(("s1.jsonl", "s2.jsonl")):
        _session(d, name, [("tests/f.py::a", 240.0, "passed"), ("tests/f.py::b", 0.02, "passed")], 1_000_000_000 + i)
    dur, _never, gaps = ld.load_all_detail(d)
    fx = "module:tests/f.py::reference_after"
    shared = {"tests/f.py::b": [fx, "session:::tmp_path_factory"]}
    est, det = ld.conservative_estimate(["tests/f.py::b"], dur, gaps, shared)
    assert est == pytest.approx(0.02) and det["fixture_cost_unknown"] == ["tests/f.py"]
    trace = tmp_path / "t.jsonl"
    trace.write_text(json.dumps({"nodeid": "tests/f.py::a", "shared": [fx], "fixture_setup_s": {fx: 239.0}}) + "\n",
                     encoding="utf-8")
    costs = ld.load_fixture_costs([trace])
    est2, det2 = ld.conservative_estimate(["tests/f.py::b"], dur, gaps, shared, costs)
    assert est2 == pytest.approx(239.02) and det2["fixture_cost_unknown"] == []
    proj = {"tests/f.py::b": ["session:tests::tmp_feature_run_store"]}
    assert ld.conservative_estimate(["tests/f.py::b"], dur, gaps, proj)[1]["fixture_cost_unknown"] == [
        "session:tests::tmp_feature_run_store"]


def test_ledger_22_uncertain_selection_requires_ack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """選取含無通過紀錄之 nodeid（從未通過、失敗 1.9 秒）⇒ 收據須 `uncertain_ack` 寫明計數；寫明 ⇒ 放行
    （r5 GROK-R5-P1-01、COMPOSER-R5-P2-01）。"""
    d = tmp_path / "ledger"
    d.mkdir()
    _session(d, "s.jsonl", [(f"{_GATE}::test_b", 200.0, "passed"), (f"{_GATE}::test_new", 1.9, "failed")],
             1_000_000_000)
    monkeypatch.setattr(g, "LEDGER_DIR", d)
    sel = tmp_path / "sel.txt"
    sel.write_text(f"{_GATE}::test_b\n{_GATE}::test_new\n", encoding="utf-8")
    inner = ["venv/bin/python", "-m", "pytest", "-q", "-p", "scripts.readtrace_plugin", "--trace-select", str(sel), _GATE]
    ack = {"uncertain_ack": {"unknown": 1, "fixture_cost_unknown": 0}}
    assert _ledger_rc(inner, 300, {**_CLOSE, **ack}) == 0
    assert _ledger_rc(inner, 300, _CLOSE) == 2


def test_ledger_20_guard_uses_conservative_estimate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """守衛以保守估時（含共用 fixture 轉移）核收據：只選同檔之 b（被選加總 0.1 秒、耗時差距 199.9）⇒ 收據 100 秒擋、
    200 秒放行；簡單加總會放行 100 秒之低估。"""
    d = tmp_path / "ledger"
    d.mkdir()
    _session(d, "s1.jsonl", [(f"{_GATE}::test_b", 200.0, "passed")], 1_000_000_000)
    _session(d, "s2.jsonl", [(f"{_GATE}::test_a", 180.0, "passed"), (f"{_GATE}::test_b", 0.1, "passed")],
             2_000_000_000)
    monkeypatch.setattr(g, "LEDGER_DIR", d)
    sel = tmp_path / "sel.txt"
    sel.write_text(f"{_GATE}::test_b\n", encoding="utf-8")
    inner = ["venv/bin/python", "-m", "pytest", "-q", "-p", "scripts.readtrace_plugin", "--trace-select", str(sel), _GATE]
    assert _ledger_rc(inner, 200, {**_CLOSE, **_ACK1}) == 0  # 先證收據身分相符（放行），下一行之擋才確屬估時
    assert _ledger_rc(inner, 100, {**_CLOSE, **_ACK1}) == 2


_CHUNKED = "scripts/run_chunked.py"


def _chunked_rc(tmp_path: Path, select: List[str], estimate: Optional[float], extra: Dict[str, Any] = None,
                background: bool = True, plan_only: bool = False) -> int:
    sel = tmp_path / "select.txt"
    sel.write_text("".join(f"{n}\n" for n in select), encoding="utf-8")
    inner = ["venv/bin/python", _CHUNKED, "--select", str(sel), "--out", str(tmp_path / "out")] + (
        ["--plan-only"] if plan_only else [])
    receipt = REPO / "handoffs" / "run_receipts" / "20261112-hrgledger-chunkedtest-estimate.json"
    if estimate is not None:
        rid = _mod("run_receipt_identity")
        match = rid.compute_match(_CHUNKED, inner, [], [], [])
        receipt.write_text(json.dumps({"identity": {"match": match, "meta": {"producer": "test", "created_at": "t"}},
                                       "scale": "single", "estimate_seconds": estimate, "basis": [],
                                       "spec_path": "docs/NOCAP_SPEC.md", "coverage_path_ids": ["NOCAP-BUDGET-3"],
                                       **(extra or {})}), encoding="utf-8")
    try:
        return _rc(_bash(" ".join(inner), background))
    finally:
        receipt.unlink(missing_ok=True)


_ACK1 = {"uncertain_ack": {"unknown": 0, "fixture_cost_unknown": 1}}  # 只選 test_b、無追蹤 ⇒ 該檔共用成本未知


@pytest.mark.parametrize("estimate,extra,background,plan_only,expected", [
    (300, _ACK1, True, False, 2),                 # 未宣告 tier＝batch，選取含重型（test_b 200 秒）⇒ 擋
    (100, {**_CLOSE, **_ACK1}, True, False, 2),   # close 但估時 100 < 執行器 plan 208（200＋行程開銷 8）⇒ 擋
    (208, {**_CLOSE, **_ACK1}, True, False, 0),   # close、估時 ≥ plan、未知項已明示 ⇒ 放行
    (208, _CLOSE, True, False, 2),                # 未知項未明示（uncertain_ack 缺）⇒ 擋
    (208, {**_CLOSE, **_ACK1}, False, False, 2),  # 前景 ⇒ 擋（重型須背景）
    (None, None, False, True, 0),                 # --plan-only 只規劃 ⇒ 免
    (None, _CLOSE, True, False, 2),               # 無收據 ⇒ 擋
])
def test_ledger_19_chunked_runner_tier_and_estimate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, estimate: Any,
                                                    extra: Any, background: bool, plan_only: bool,
                                                    expected: int) -> None:
    """分批執行器之 --select 選取同 pytest 套用 tier 與 ledger 保守估時交叉檢查；只規劃者免。"""
    _ledger(tmp_path, monkeypatch)
    assert _chunked_rc(tmp_path, [f"{_GATE}::test_b"], estimate, extra, background, plan_only) == expected


def test_ledger_23_chunked_estimate_follows_runner_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """執行器拆批後各批重付共用 fixture 與行程開銷 ⇒ 守衛依其 plan 加總核（r5 CODEX-R5-P1-02）：同檔 a（重型 180）、
    b（0.1，檔內差距 199.9）整檔選取時整份估 180.1，但拆成 heavy[a]＋fast[b] 兩批、各為部分選取 ⇒
    (180＋199.9＋8)＋(0.1＋199.9＋8)＝595.9。"""
    d = tmp_path / "ledger"
    d.mkdir()
    _session(d, "s1.jsonl", [(f"{_GATE}::test_b", 200.0, "passed")], 1_000_000_000)
    _session(d, "s2.jsonl", [(f"{_GATE}::test_a", 180.0, "passed"), (f"{_GATE}::test_b", 0.1, "passed")],
             2_000_000_000)
    monkeypatch.setattr(g, "LEDGER_DIR", d)
    # 整份選取無未知項，但拆成兩批後各為部分選取 ⇒ 兩批各有一處共用成本未知（逐批實例數 2；審碼 r6）
    ack = {"uncertain_ack": {"unknown": 0, "fixture_cost_unknown": 2}}
    sel = [f"{_GATE}::test_a", f"{_GATE}::test_b"]
    assert _chunked_rc(tmp_path, sel, 596, {**_CLOSE, **ack}) == 0
    assert _chunked_rc(tmp_path, sel, 181, {**_CLOSE, **ack}) == 2
    assert _chunked_rc(tmp_path, sel, 596, _CLOSE) == 2  # 拆批產生之未知項未明示 ⇒ 擋


def test_mutation_chunked_selection_unparsed_misses_heavy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：執行器選取解析回 None ⇒ ledger_19 首案（batch 含重型）不再被擋（鑑別力）。"""
    _ledger(tmp_path, monkeypatch)
    monkeypatch.setattr(g, "_chunked_option", lambda argv, name: None)
    assert _chunked_rc(tmp_path, [f"{_GATE}::test_b"], 300) == 0
