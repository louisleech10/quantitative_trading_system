"""NOCAP Task 0.3：重型命令須背景執行且經共用監看（scripts/heavy_run_guard.py）。秒級、不跑重型。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

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


@pytest.mark.parametrize("cmd,background,expected", [
    # 自帶監看之量測：須背景
    ("venv/bin/python scripts/ffprod_measure.py run --cell C_BTCUSDT_1h", False, 2),
    ("venv/bin/python scripts/ffprod_measure.py run --cell C_BTCUSDT_1h", True, 0),
    ("venv/bin/python scripts/ffprod_measure.py plan --cell C_BTCUSDT_1h", False, 0),  # plan 非重型
    # 重型 pytest：須包裝且背景
    ("venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q", True, 2),
    (WRAP + "venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q", False, 2),
    (WRAP + "venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q", True, 0),
    ("venv/bin/python -m pytest tests/feature_engineering/test_ffprod_measure.py -q", False, 0),  # 輕量
    ("venv/bin/python -m pytest -q", True, 2),  # 無參數全套
    ("venv/bin/python -m pytest tests -x -q", True, 2),  # 帶選項之全套（b1 審碼 r1 CODEX-R1-P1-05）
    ("venv/bin/python -m pytest -q -p no:cacheprovider tests/governance", True, 2),
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
    """清單之 self_watched 腳本皆確實呼叫共用監看 run_watched(（機械對證；移除即擋）。"""
    catalog = json.loads((REPO / "scripts" / "heavy_commands.json").read_text(encoding="utf-8"))
    for rule in catalog["self_watched"]:
        assert "run_watched(" in (REPO / rule["source"]).read_text(encoding="utf-8"), rule
    fake = {"self_watched": [{"id": "x", "regex": "scripts/x_heavy\\.py", "source": "scripts/heavy_run_guard.py"}]}
    problems = g.check(_bash("venv/bin/python scripts/x_heavy.py", True), fake)
    assert problems and "未呼叫共用監看" in problems[0]


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


def test_mutation_depth_zero_misses_two_level_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：不展開被執行之 .sh（讀檔一律回 None）⇒ 一層 .sh 內之全套 pytest 漏擋（遞迴展開之鑑別力；逾深度上限
    之 fail-closed 不受此改壞影響，故改壞點選在讀檔）。"""
    monkeypatch.setattr(g, "_script_body", lambda *a, **k: None)
    try:
        assert _rc(_bash(f"bash {_chain(1, 'venv/bin/python -m pytest -q')}", False)) == 0
    finally:
        _unchain(1)
