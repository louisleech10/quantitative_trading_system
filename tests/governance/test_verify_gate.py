"""VERIFY_GATE Phase 1 (B1) — receipt 產生器與 gitignore 可追蹤測試。"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_WITH_RECEIPT = REPO_ROOT / "scripts" / "run_with_receipt.py"
PYTHON = REPO_ROOT / "venv" / "bin" / "python"
RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"

_spec = importlib.util.spec_from_file_location("run_with_receipt", RUN_WITH_RECEIPT)
_run_with_receipt = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_run_with_receipt)
validate_receipt_schema = _run_with_receipt.validate_receipt_schema


def _receipts_dir() -> Path:
    """從環境變數或預設路徑取得 receipt 目錄。"""
    override = os.environ.get(RECEIPTS_DIR_ENV)
    if override:
        return Path(override)
    return REPO_ROOT / "handoffs" / "run_receipts"


def _audit_log() -> Path:
    """從環境變數或預設路徑取得審計 log。"""
    override = os.environ.get(AUDIT_LOG_ENV)
    if override:
        return Path(override)
    return REPO_ROOT / ".claude" / "gate" / "verify_audit.log"


@pytest.fixture(autouse=True)
def isolated_verify_gate_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """所有測試使用臨時 receipt/audit 路徑，避免污染受追蹤目錄。"""
    receipts_dir = tmp_path / "run_receipts"
    audit_log = tmp_path / "gate" / "verify_audit.log"
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(receipts_dir))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(audit_log))

_spec = importlib.util.spec_from_file_location("run_with_receipt", RUN_WITH_RECEIPT)
_run_with_receipt = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_run_with_receipt)
validate_receipt_schema = _run_with_receipt.validate_receipt_schema

RECEIPT_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "receipt_id",
    "claim_id",
    "command",
    "command_sha256",
    "cwd",
    "git_head",
    "tree_dirty",
    "started_at",
    "ended_at",
    "duration_seconds",
    "exit_code",
    "runtime_class",
    "requested_class",
    "pytest_summary",
    "selected_node_ids",
    "markers",
    "passed",
    "failed",
    "skipped",
    "stdout_sha256",
    "stderr_sha256",
    "log_sha256",
    "log_path",
    "tail_excerpt",
)


def _assert_receipt_schema(receipt: dict) -> None:
    """斷言 receipt 含 SPEC 定義的全必填欄位。"""
    missing = [field for field in RECEIPT_REQUIRED_FIELDS if field not in receipt]
    assert not missing, f"receipt missing required fields: {missing}"


def _run_wrapper(
    claim_id: str,
    cmd: list[str],
    *,
    requested_class: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """以 venv python 執行 run_with_receipt.py。"""
    argv = [str(PYTHON), str(RUN_WITH_RECEIPT), "--claim-id", claim_id]
    if requested_class is not None:
        argv.extend(["--requested-class", requested_class])
    argv.append("--")
    argv.extend(cmd)
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _latest_receipt_for_claim(claim_id: str) -> tuple[Path, dict]:
    """找指定 claim_id 最新 receipt JSON。"""
    receipts_dir = _receipts_dir()
    matches = sorted(receipts_dir.glob(f"*-{claim_id}.json"))
    assert matches, f"no receipt found for claim_id={claim_id}"
    path = matches[-1]
    return path, json.loads(path.read_text(encoding="utf-8"))


def _read_last_audit_event() -> dict:
    """讀 verify_audit.log 最後一行 JSON。"""
    audit_log = _audit_log()
    assert audit_log.is_file(), "verify_audit.log missing"
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, "verify_audit.log is empty"
    return json.loads(lines[-1])


def test_receipt_schema() -> None:
    """V1：全欄位、log_sha256 一致、審計事件寫入、exit 透傳。"""
    claim_id = "test-receipt-schema-v1"
    proc = _run_wrapper(
        claim_id,
        [str(PYTHON), "-c", "print('2 passed')"],
    )
    assert proc.returncode == 0

    receipt_path, receipt = _latest_receipt_for_claim(claim_id)
    _assert_receipt_schema(receipt)

    log_path = Path(receipt["log_path"])
    assert log_path.is_file()
    log_digest = hashlib.sha256(log_path.read_bytes()).hexdigest()
    assert receipt["log_sha256"] == log_digest

    receipt_digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

    audit_event = _read_last_audit_event()
    assert audit_event["event"] == "receipt"
    assert audit_event["receipt_id"] == receipt["receipt_id"]
    assert audit_event["receipt_id"] == receipt_path.stem
    assert audit_event["log_sha256"] == log_digest
    assert audit_event["emitter"] == "run_with_receipt.py"
    assert audit_event["command_sha256"] == receipt["command_sha256"]
    assert audit_event["receipt_sha256"] == receipt_digest
    assert audit_event["exit_code"] == receipt["exit_code"]
    assert audit_event["runtime_class"] == receipt["runtime_class"]


def test_receipt_exit_passthrough() -> None:
    """子命令 exit code 須透傳給 wrapper。"""
    claim_id = "test-receipt-exit-passthrough"
    proc = _run_wrapper(
        claim_id,
        [str(PYTHON), "-c", "import sys; sys.exit(3)"],
    )
    assert proc.returncode == 3

    _, receipt = _latest_receipt_for_claim(claim_id)
    assert receipt["exit_code"] == 3


def test_gitignore_receipt_trackable() -> None:
    """W12 前置：receipt/audit log 不被 *.log 泛忽略，其他 log 仍忽略。"""
    receipt_log = REPO_ROOT / "handoffs" / "run_receipts" / "test.log"
    scripts_log = REPO_ROOT / "scripts" / "foo.log"

    receipt_check = subprocess.run(
        ["git", "check-ignore", str(receipt_log)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert receipt_check.returncode == 1, (
        f"expected handoffs/run_receipts/*.log to be trackable, got: {receipt_check.stdout}"
    )

    scripts_check = subprocess.run(
        ["git", "check-ignore", "-v", str(scripts_log)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert scripts_check.returncode == 0, "expected scripts/foo.log to remain ignored by *.log"
    assert "*.log" in scripts_check.stdout


def test_mutation_receipt_missing_field_fails() -> None:
    """mutation 探針：移除任一必填欄位 → production schema 驗證須 FAIL。"""
    claim_id = "test-mutation-receipt-missing-field"
    proc = _run_wrapper(
        claim_id,
        [str(PYTHON), "-c", "print('1 passed')"],
    )
    assert proc.returncode == 0

    _, receipt = _latest_receipt_for_claim(claim_id)
    validate_receipt_schema(receipt)

    field = RECEIPT_REQUIRED_FIELDS[0]
    mutated = copy.deepcopy(receipt)
    del mutated[field]
    with pytest.raises(AssertionError, match="missing required fields"):
        validate_receipt_schema(mutated)


def test_requested_class_does_not_override_runtime_class() -> None:
    """requested_class 僅稽核存檔，不得覆蓋 derive_runtime_class 推導結果。"""
    claim_id = "test-requested-class-no-override"
    proc = _run_wrapper(
        claim_id,
        [str(PYTHON), "-c", "pass"],
        requested_class="mutation_runtime",
    )
    assert proc.returncode == 0

    _, receipt = _latest_receipt_for_claim(claim_id)
    assert receipt["requested_class"] == "mutation_runtime"
    assert receipt["runtime_class"] == "static_only"


def test_command_not_found_still_produces_receipt() -> None:
    """不存在的子命令仍須產 receipt，exit_code=127。"""
    claim_id = "test-command-not-found"
    proc = _run_wrapper(
        claim_id,
        ["definitely-not-a-real-command-verifygate"],
    )
    assert proc.returncode == 127

    _, receipt = _latest_receipt_for_claim(claim_id)
    assert receipt["exit_code"] == 127
    validate_receipt_schema(receipt)


def test_mutation_node_id_runtime_class_and_selected_nodes() -> None:
    """node-id 式 mutation 測試須歸類 mutation_runtime 且 selected_node_ids 非空。"""
    claim_id = "test-mutation-node-id"
    node_id = f"{Path(__file__).as_posix()}::test_mutation_receipt_missing_field_fails"
    proc = _run_wrapper(
        claim_id,
        [str(PYTHON), "-m", "pytest", node_id, "-q"],
    )
    assert proc.returncode == 0

    _, receipt = _latest_receipt_for_claim(claim_id)
    assert receipt["runtime_class"] == "mutation_runtime"
    assert receipt["selected_node_ids"]
    assert any("::test_mutation_" in node for node in receipt["selected_node_ids"])
