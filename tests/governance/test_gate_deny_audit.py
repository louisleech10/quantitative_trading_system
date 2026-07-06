"""INSTREV Phase B2 — gate_check.sh DENY 事件 append audit.log。"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.sh"


def _run_gate_check(
    payload: str,
    *,
    gate_dir: Path,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    return subprocess.run(
        ["bash", str(GATE_CHECK)],
        input=payload,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _last_audit_event(audit_log: Path) -> dict:
    lines = [ln for ln in audit_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "audit.log 為空"
    return json.loads(lines[-1])


def test_gate_deny_no_token_appends_audit(tmp_path: Path) -> None:
    """無 token 的 Task → exit 2 且 audit 尾行 gate_deny/no_fresh_token。"""
    gate_dir = tmp_path / "gate"
    proc = _run_gate_check('{"tool_name":"Task"}', gate_dir=gate_dir)
    assert proc.returncode == 2
    audit = gate_dir / "audit.log"
    assert audit.is_file()
    event = _last_audit_event(audit)
    assert event["event"] == "gate_deny"
    assert event["tool"] == "Task"
    assert event["reason"] == "no_fresh_token"
    assert event["kind"] == "dispatch"


def test_gate_deny_expired_token_appends_audit(tmp_path: Path) -> None:
    """過期 dispatch.token → exit 2 且 reason=token_expired。"""
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    token = gate_dir / "dispatch.token"
    token.write_text("stale", encoding="utf-8")
    old = time.time() - 1200
    os.utime(token, (old, old))
    proc = _run_gate_check('{"tool_name":"Task"}', gate_dir=gate_dir)
    assert proc.returncode == 2
    event = _last_audit_event(gate_dir / "audit.log")
    assert event["reason"] == "token_expired"


def test_gate_fresh_token_no_deny_audit(tmp_path: Path) -> None:
    """fresh token → exit 0 且不新增 gate_deny。"""
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    token = gate_dir / "dispatch.token"
    token.write_text("fresh", encoding="utf-8")
    proc = _run_gate_check('{"tool_name":"Task"}', gate_dir=gate_dir)
    assert proc.returncode == 0
    audit = gate_dir / "audit.log"
    if audit.is_file():
        assert "gate_deny" not in audit.read_text(encoding="utf-8")


def test_gate_deny_unwritable_gate_dir_still_exit2(tmp_path: Path) -> None:
    """GATE_DIR 不可寫 → 仍 exit 2 不崩。"""
    gate_dir = tmp_path / "readonly_gate"
    gate_dir.mkdir()
    gate_dir.chmod(0o444)
    try:
        proc = _run_gate_check('{"tool_name":"Task"}', gate_dir=gate_dir)
        assert proc.returncode == 2
    finally:
        gate_dir.chmod(0o755)


def test_gate_non_gated_action_no_audit(tmp_path: Path) -> None:
    """非 gated 工具 → exit 0 且不寫 gate_deny。"""
    gate_dir = tmp_path / "gate"
    proc = _run_gate_check('{"tool_name":"Read"}', gate_dir=gate_dir)
    assert proc.returncode == 0
    assert not (gate_dir / "audit.log").exists()
