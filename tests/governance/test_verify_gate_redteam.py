"""VERIFY_GATE 紅隊修補 (R1–R7) — reconcile 20260702 真漏洞回歸。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "venv" / "bin" / "python"
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.sh"
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
PRETOOLUSE = REPO_ROOT / "scripts" / "verify_pretooluse.sh"
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
RECONCILE_CHECK = REPO_ROOT / "scripts" / "reconcile_stamps_check.sh"

RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
COMMITTEE_AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"


@pytest.fixture(autouse=True)
def isolated_redteam_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """隔離 receipt/audit 路徑，零觸碰真實 .claude/gate/*。"""
    receipts_dir = tmp_path / "run_receipts"
    verify_audit = tmp_path / "gate" / "verify_audit.log"
    committee_audit = tmp_path / "gate" / "committee_audit.log"
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(receipts_dir))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(verify_audit))
    monkeypatch.setenv(COMMITTEE_AUDIT_ENV, str(committee_audit))


def _run_gate_check(tool_name: str, *, command: str = "", file_path: str = "") -> int:
    """執行 gate_check.sh，回傳 exit code。"""
    payload: dict = {"tool_name": tool_name, "tool_input": {}}
    if command:
        payload["tool_input"]["command"] = command
    if file_path:
        payload["tool_input"]["file_path"] = file_path
    proc = subprocess.run(
        ["bash", str(GATE_CHECK)],
        input=json.dumps(payload),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode


def _run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    argv = [str(PYTHON), str(CLAIM_CHECK), *args]
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_fixture(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _create_manual_receipt(
    claim_id: str,
    *,
    runtime_class: str = "helper_smoke",
    selected_node_ids: list[str] | None = None,
) -> str:
    """建立 receipt + 審計事件（隔離路徑）。"""
    receipts_dir = Path(os.environ[RECEIPTS_DIR_ENV])
    audit_log = Path(os.environ[AUDIT_LOG_ENV])
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt_id = f"20990101T000000Z-{claim_id}"
    json_path = receipts_dir / f"{receipt_id}.json"
    log_path = receipts_dir / f"{receipt_id}.log"
    log_path.write_bytes(b"ok\n")
    log_sha256 = hashlib.sha256(log_path.read_bytes()).hexdigest()
    receipt = {
        "schema_version": "1.0",
        "receipt_id": receipt_id,
        "claim_id": claim_id,
        "command": [str(PYTHON), "-c", "print('1 passed')"],
        "command_sha256": "test",
        "cwd": str(REPO_ROOT),
        "git_head": "test",
        "tree_dirty": False,
        "started_at": "2099-01-01T00:00:00Z",
        "ended_at": "2099-01-01T00:00:01Z",
        "duration_seconds": 0.1,
        "exit_code": 0,
        "runtime_class": runtime_class,
        "requested_class": None,
        "pytest_summary": "1 passed",
        "selected_node_ids": selected_node_ids or [],
        "markers": [],
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "stdout_sha256": "test",
        "stderr_sha256": "test",
        "log_sha256": log_sha256,
        "log_path": str(log_path),
        "tail_excerpt": ["ok"],
    }
    json_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event": "receipt",
        "receipt_id": receipt_id,
        "receipt_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
        "log_sha256": log_sha256,
        "exit_code": 0,
        "runtime_class": runtime_class,
    }
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")
    return receipt_id


def _run_pretooluse(payload: dict) -> int:
    proc = subprocess.run(
        ["bash", str(PRETOOLUSE)],
        input=json.dumps(payload),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode


def _run_gate_check_isolated(
    gate_dir: Path,
    tool_name: str,
    *,
    command: str = "",
) -> int:
    """在隔離 GATE_DIR 下執行 gate_check（不觸碰真實 .claude/gate）。"""
    script = GATE_CHECK.read_text(encoding="utf-8")
    script = script.replace('GATE_DIR=".claude/gate"', f'GATE_DIR="{gate_dir}"', 1)
    isolated = gate_dir.parent / "gate_check_isolated.sh"
    isolated.write_text(script, encoding="utf-8")
    isolated.chmod(0o755)
    payload: dict = {"tool_name": tool_name, "tool_input": {}}
    if command:
        payload["tool_input"]["command"] = command
    proc = subprocess.run(
        ["bash", str(isolated)],
        input=json.dumps(payload),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode


# --- R1: env-prefix dispatch gate ---


def test_r1_gate_check_env_prefix_matches_bare_verdict() -> None:
    """R1：env-prefix 版與裸版判定一致（不可因前綴放行）。"""
    bare = _run_gate_check("Bash", command="codex exec hello")
    prefixed = _run_gate_check("Bash", command="GATE_DIR_OVERRIDE=/tmp codex exec hello")
    assert bare == prefixed


def test_r1_gate_check_blocks_without_token_isolated(tmp_path: Path) -> None:
    """R1：無 token 時裸版與 env-prefix 皆 exit 2。"""
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    bare = _run_gate_check_isolated(gate_dir, "Bash", command="codex exec hello")
    prefixed = _run_gate_check_isolated(
        gate_dir,
        "Bash",
        command="GATE_DIR_OVERRIDE=/tmp codex exec hello",
    )
    assert bare == 2
    assert prefixed == 2


def test_r1_gate_check_blocks_multiple_env_prefixes_isolated(tmp_path: Path) -> None:
    """R1：多個 env 前綴仍擋 codex exec（隔離 GATE_DIR）。"""
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    rc = _run_gate_check_isolated(
        gate_dir,
        "Bash",
        command="FOO=1 BAR=baz codex exec --skip-git-repo-check x",
    )
    assert rc == 2


# --- R2: docs operational smuggling ---


def test_r2_docs_operational_without_backing_blocked(tmp_path: Path) -> None:
    """R2：docs operational 段無 backing → exit 1。"""
    fixture = _write_fixture(
        tmp_path / "docs" / "reviews" / "smuggle.md",
        "## 已完成\n\nFF align mutation 已驗全綠 STATUS:DONE\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_r2_docs_discussion_prose_allowed(tmp_path: Path) -> None:
    """R2：docs 純設計散文（非 operational 段）放行。"""
    fixture = _write_fixture(
        tmp_path / "docs" / "design" / "notes.md",
        "## 設計筆記\n\n歷史上曾討論「已驗真紅」字樣的風險（規格示例）。\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 0, proc.stderr


# --- R3: vague scope receipt wash ---


def test_r3_vague_scope_receipt_wash_blocked(tmp_path: Path) -> None:
    """R3：模糊 P0-FF-3 綠燈 + 無關快測 receipt → exit 1。"""
    receipt_id = _create_manual_receipt("r3-fast-unrelated", runtime_class="helper_smoke")
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"## 現役任務\n\nP0-FF-3 已驗綠燈 VERIFY:{receipt_id}\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "模糊 scope" in proc.stderr


def test_r3_specific_scope_receipt_allowed(tmp_path: Path) -> None:
    """R3：具體 node-id + mutation receipt 仍放行。"""
    node = "tests/feature_engineering/test_x.py::test_mutation_align"
    receipt_id = _create_manual_receipt(
        "r3-mutation-align",
        runtime_class="mutation_runtime",
        selected_node_ids=[node],
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"## 已完成\n\n{node} mutation 已驗全綠 VERIFY:{receipt_id}\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 0, proc.stderr


# --- R4: PreToolUse path normalization ---


def test_r4_pretooluse_tmp_private_tmp_same_verdict() -> None:
    """R4：/tmp 與 realpath 一致時對 HANDOFF 假 claim 同擋（exit 2）。"""
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    real_root = os.path.realpath(root)
    handoff = Path(real_root) / "HANDOFF.md"
    payload_base = {
        "tool_name": "Edit",
        "tool_input": {"new_string": "## 正在做\n\n- align 已驗真紅\n"},
    }
    rc_direct = _run_pretooluse({**payload_base, "tool_input": {**payload_base["tool_input"], "file_path": str(handoff)}})
    # 模擬 Cursor 可能送的不一致前綴（若 realpath 已一致則兩者相同）
    alt = str(handoff).replace("/private", "", 1) if "/private" in str(handoff) else str(handoff)
    rc_alt = _run_pretooluse({**payload_base, "tool_input": {**payload_base["tool_input"], "file_path": alt}})
    assert rc_direct == 2
    assert rc_alt == 2


def test_r4_pretooluse_fail_closed_on_unresolvable_handoff_path() -> None:
    """R4：看似 HANDOFF 但無法對齊 repo → fail-closed exit 2。"""
    payload = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/tmp/definitely-not-repo/HANDOFF.md",
            "new_string": "## 正在做\n\n- note\n",
        },
    }
    assert _run_pretooluse(payload) == 2


# --- R6: fake attribution self-cert ---


def test_r6_fake_attribution_quoted_polarity_blocked_staged(tmp_path: Path) -> None:
    """R6：假歸屬「Codex 檔案寫道『…已驗真紅』」無 VERIFY → exit 1。"""
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\nCodex 檔案寫道「align 已驗真紅」\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_r6_true_attribution_with_verify_allowed(tmp_path: Path) -> None:
    """R6：帶 VERIFY 的真引用放行。"""
    receipt_id = _create_manual_receipt("r6-verify-cite")
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"## 現役任務\n\n委員報告寫道「進度全綠 VERIFY:{receipt_id}」\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 0, proc.stderr


def test_r6_v7_regression_spec_files_unblocked() -> None:
    """R6/V7：既有 SPEC/DELIB 合法引用誤報=0。"""
    proc = _run_checker(
        "--files",
        "docs/VERIFY_GATE_SPEC.md",
        "handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md",
        "docs/VERIFY_GATE_SPEC_PLAIN.md",
    )
    assert proc.returncode == 0, proc.stderr


# --- R7: committee_dispatch emitter ---


def test_r7_gate_task_id_appends_committee_dispatch(tmp_path: Path) -> None:
    """R7：gate dispatch --task-id + adversarial → audit 有 committee_dispatch 且 hash 符。"""
    gate_tmp = tempfile.mkdtemp(prefix="gate_r7_test_")
    adv_path = REPO_ROOT / "handoffs" / "20990101-R7-ADV-COMPOSER.md"
    adv_path.write_text("# R7 adversarial review\nVERDICT: APPROVED\n", encoding="utf-8")
    rel = "handoffs/20990101-R7-ADV-COMPOSER.md"

    env = dict(os.environ, GATE_DIR_OVERRIDE=gate_tmp)
    try:
        proc = subprocess.run(
            [
                "bash",
                str(GATE_SH),
                "dispatch",
                "--intent",
                "R7 committee dispatch emitter test",
                "--risk",
                "high",
                "--facts-asked",
                "none-needed:R7 unit test",
                "--review-role",
                "composer adversarial",
                "--template",
                "n/a:R7 provenance test",
                "--adversarial",
                rel,
                "--task-id",
                "r7task01",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

        audit_log = Path(gate_tmp) / "audit.log"
        assert audit_log.is_file()
        dispatch_lines = [
            line
            for line in audit_log.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("{") and "committee_dispatch" in line
        ]
        assert dispatch_lines, audit_log.read_text()
        event = json.loads(dispatch_lines[-1])
        assert event["event"] == "committee_dispatch"
        assert event["task_id"] == "r7task01"
        assert event["output_path"] == rel
        assert event["output_sha256"] == hashlib.sha256(adv_path.read_bytes()).hexdigest()

        env_prov = dict(os.environ, VERIFY_GATE_COMMITTEE_AUDIT_LOG=str(audit_log))
        adv_proc = subprocess.run(
            [
                str(PYTHON),
                str(REPO_ROOT / "scripts" / "verify_task_provenance.py"),
                "check-adversarial",
                rel,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env_prov,
        )
        assert adv_proc.returncode == 0, adv_proc.stderr
    finally:
        adv_path.unlink(missing_ok=True)
