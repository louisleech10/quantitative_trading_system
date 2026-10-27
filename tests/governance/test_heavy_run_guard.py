"""NOCAP Task 0.3：重型命令須背景執行且經共用監看（scripts/heavy_run_guard.py）。秒級、不跑重型。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

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
    # 委員派工：須背景
    ("bash scripts/committee_run.sh --session s brief out codex,composer", False, 2),
    ("bash scripts/committee_run.sh --session s brief out codex,composer", True, 0),
    ("git status --short", False, 0),
])
def test_heavy_command_rules(cmd: str, background: bool, expected: int) -> None:
    assert _rc(_bash(cmd, background)) == expected


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
