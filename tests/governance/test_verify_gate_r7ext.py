"""GOV_O3EXT_R7 B1 — task-id emitter + reconcile stamp provenance."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
from tests.governance._pyenv import PYTHON  # CI 無 venv → fallback sys.executable
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
RECONCILE_CHECK = REPO_ROOT / "scripts" / "reconcile_stamps_check.sh"
BODY_HASH = REPO_ROOT / "scripts" / "reconcile_body_hash.sh"


@pytest.fixture()
def isolated_gate(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """回傳隔離 gate dir 與 env，避免寫入真實 .claude/gate/。"""
    gate_dir = tmp_path / "gate"
    env = dict(os.environ, GATE_DIR_OVERRIDE=str(gate_dir))
    return gate_dir, env


def _run_gate(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(GATE_SH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _dispatch_low(
    env: dict[str, str],
    *,
    task_id: str | None = None,
    output: str | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [
        "dispatch",
        "--intent",
        "R7 extension unit test",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:R7 unit test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:R7 unit test",
    ]
    if task_id is not None:
        args.extend(["--task-id", task_id])
    if output is not None:
        args.extend(["--output", output])
    return _run_gate(env, *args)


def _json_events(audit_log: Path) -> list[dict]:
    events: list[dict] = []
    if not audit_log.is_file():
        return events
    for raw in audit_log.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("{"):
            events.append(json.loads(line))
    return events


def _write_repo_handoff(name: str, content: str) -> Path:
    path = REPO_ROOT / "handoffs" / name
    path.write_text(content, encoding="utf-8")
    return path


def _reconcile_body_hash(path: Path) -> str:
    proc = subprocess.run(
        ["bash", str(BODY_HASH), str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _append_approved_stamps(path: Path, *, task_id: str) -> None:
    digest = _reconcile_body_hash(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n"
            f"RECONCILE-STAMP: codex APPROVED 2099-01-01 sha256:{digest} task:{task_id}\n"
            f"RECONCILE-STAMP: composer APPROVED 2099-01-01 sha256:{digest} task:{task_id}\n"
        )


def _run_reconcile(path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    # fixture 由 _append_approved_stamps 造 codex+composer 兩家 → 顯式傳兩家 roster。
    # stamp 預設 2026-07-23 改 review_families(含 grok);本鏈測試驗機制非 roster,傳參宣告(非放寬 assert)。
    return subprocess.run(
        ["bash", str(RECONCILE_CHECK), str(path), "codex,composer"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_low_risk_task_id_emits_committee_dispatch_with_pending_output(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    gate_dir, env = isolated_gate
    proc = _dispatch_low(env, task_id="r7ext-low-01", output="handoffs/does-not-exist.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    events = _json_events(gate_dir / "audit.log")
    dispatch = [event for event in events if event.get("event") == "committee_dispatch"]
    assert len(dispatch) == 1
    assert dispatch[0]["task_id"] == "r7ext-low-01"
    assert dispatch[0]["output_path"] == "handoffs/does-not-exist.md"
    assert dispatch[0]["output_sha256"] == "pending"


def test_dispatch_without_task_id_does_not_emit_committee_event(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    gate_dir, env = isolated_gate
    proc = _dispatch_low(env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not [
        event
        for event in _json_events(gate_dir / "audit.log")
        if event.get("event") == "committee_dispatch"
    ]


def test_failed_dispatch_does_not_emit_committee_event(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    gate_dir, env = isolated_gate
    proc = _run_gate(
        env,
        "dispatch",
        "--intent",
        "missing required fields",
        "--task-id",
        "r7ext-failed-dispatch",
    )
    assert proc.returncode == 1
    assert not [
        event
        for event in _json_events(gate_dir / "audit.log")
        if event.get("event") == "committee_dispatch"
    ]


def test_register_output_requires_prior_dispatch_and_handoffs_path(
    isolated_gate: tuple[Path, dict[str, str]],
    tmp_path: Path,
) -> None:
    _, env = isolated_gate
    outside = tmp_path / "docs" / "x.md"
    outside.parent.mkdir(parents=True)
    outside.write_text("done\n", encoding="utf-8")

    no_dispatch = _run_gate(env, "register-output", "r7ext-no-dispatch", str(outside))
    assert no_dispatch.returncode == 1
    assert "handoffs" in (no_dispatch.stdout + no_dispatch.stderr) or "dispatch" in (
        no_dispatch.stdout + no_dispatch.stderr
    )

    rel = "handoffs/20990101-R7EXT-register.md"
    handoff = _write_repo_handoff("20990101-R7EXT-register.md", "registered\n")
    try:
        dispatch = _dispatch_low(env, task_id="r7ext-register", output=rel)
        assert dispatch.returncode == 0, dispatch.stdout + dispatch.stderr
        registered = _run_gate(env, "register-output", "r7ext-register", rel)
        assert registered.returncode == 0, registered.stdout + registered.stderr
    finally:
        handoff.unlink(missing_ok=True)


def test_register_output_rejects_legacy_task_id(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    _, env = isolated_gate
    rel = "handoffs/20990101-R7EXT-legacy.md"
    handoff = _write_repo_handoff("20990101-R7EXT-legacy.md", "legacy\n")
    try:
        dispatch = _dispatch_low(env, task_id="legacy-r7ext", output=rel)
        assert dispatch.returncode == 0, dispatch.stdout + dispatch.stderr
        proc = _run_gate(env, "register-output", "legacy-r7ext", rel)
        assert proc.returncode == 1
        assert "legacy" in (proc.stdout + proc.stderr)
    finally:
        handoff.unlink(missing_ok=True)


def test_task_id_json_fuzz_stays_single_valid_event(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    gate_dir, env = isolated_gate
    task_id = 'r7ext-"quoted"\n下一行'
    proc = _dispatch_low(env, task_id=task_id, output="handoffs/fuzz-missing.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    json_lines = [
        line
        for line in (gate_dir / "audit.log").read_text(encoding="utf-8").splitlines()
        if line.startswith("{")
    ]
    assert len(json_lines) == 1
    event = json.loads(json_lines[0])
    assert event["task_id"] == task_id


def test_reconcile_full_chain_dispatch_register_stamp_passes(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    gate_dir, env = isolated_gate
    rel = "handoffs/20990101-R7EXT-RECONCILE.md"
    reconcile = _write_repo_handoff(
        "20990101-R7EXT-RECONCILE.md",
        "# Reconcile\n\n委員審查內容。\n\n## 戳記\n",
    )
    try:
        dispatch = _dispatch_low(env, task_id="r7ext-chain", output=rel)
        assert dispatch.returncode == 0, dispatch.stdout + dispatch.stderr
        registered = _run_gate(env, "register-output", "r7ext-chain", rel)
        assert registered.returncode == 0, registered.stdout + registered.stderr
        _append_approved_stamps(reconcile, task_id="r7ext-chain")

        check_env = dict(env, VERIFY_GATE_COMMITTEE_AUDIT_LOG=str(gate_dir / "audit.log"))
        proc = _run_reconcile(reconcile, check_env)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "PASS" in proc.stdout
        assert "waived" not in proc.stdout.lower()
    finally:
        reconcile.unlink(missing_ok=True)


def test_reconcile_pending_dispatch_without_register_fails(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    gate_dir, env = isolated_gate
    rel = "handoffs/20990101-R7EXT-PENDING-RECONCILE.md"
    reconcile = REPO_ROOT / rel
    try:
        dispatch = _dispatch_low(env, task_id="r7ext-pending", output=rel)
        assert dispatch.returncode == 0, dispatch.stdout + dispatch.stderr
        reconcile = _write_repo_handoff(
            "20990101-R7EXT-PENDING-RECONCILE.md",
            "# Reconcile\n\n待補 register-output。\n\n## 戳記\n",
        )
        _append_approved_stamps(reconcile, task_id="r7ext-pending")

        check_env = dict(env, VERIFY_GATE_COMMITTEE_AUDIT_LOG=str(gate_dir / "audit.log"))
        proc = _run_reconcile(reconcile, check_env)
        assert proc.returncode == 1
        assert "pending" in (proc.stdout + proc.stderr) or "provenance" in (
            proc.stdout + proc.stderr
        )
    finally:
        reconcile.unlink(missing_ok=True)


def test_reconcile_fake_task_id_without_audit_fails(
    isolated_gate: tuple[Path, dict[str, str]],
) -> None:
    gate_dir, env = isolated_gate
    reconcile = _write_repo_handoff(
        "20990101-R7EXT-FAKE-RECONCILE.md",
        "# Reconcile\n\n無派工。\n\n## 戳記\n",
    )
    try:
        _append_approved_stamps(reconcile, task_id="r7ext-fake")
        check_env = dict(env, VERIFY_GATE_COMMITTEE_AUDIT_LOG=str(gate_dir / "audit.log"))
        proc = _run_reconcile(reconcile, check_env)
        assert proc.returncode == 1
        assert "committee_dispatch" in (proc.stdout + proc.stderr)
    finally:
        reconcile.unlink(missing_ok=True)
