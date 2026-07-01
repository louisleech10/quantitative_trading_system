"""VERIFY_GATE Phase 1 (B1) + Phase 2 (B2) — receipt 產生器與 claim checker 測試。"""
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
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
PYTHON = REPO_ROOT / "venv" / "bin" / "python"
RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"

_spec = importlib.util.spec_from_file_location("run_with_receipt", RUN_WITH_RECEIPT)
_run_with_receipt = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_run_with_receipt)
validate_receipt_schema = _run_with_receipt.validate_receipt_schema

_claim_spec = importlib.util.spec_from_file_location("verification_claim_check", CLAIM_CHECK)
_claim_check = importlib.util.module_from_spec(_claim_spec)
assert _claim_spec.loader is not None
sys.modules[_claim_spec.name] = _claim_check
_claim_spec.loader.exec_module(_claim_check)


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
    """所有測試使用臨時 receipt/audit/ledger 路徑，避免污染受追蹤目錄。"""
    receipts_dir = tmp_path / "run_receipts"
    audit_log = tmp_path / "gate" / "verify_audit.log"
    pending_ledger = tmp_path / "pending_verifications.jsonl"
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(receipts_dir))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(audit_log))
    monkeypatch.setenv(PENDING_LEDGER_ENV, str(pending_ledger))


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


def _pending_ledger() -> Path:
    """從環境變數或預設路徑取得 pending ledger。"""
    override = os.environ.get(PENDING_LEDGER_ENV)
    if override:
        return Path(override)
    return REPO_ROOT / "handoffs" / "pending_verifications.jsonl"


def _check_files_inprocess(paths: list[Path]) -> tuple[int, str]:
    """進程內執行 checker（供 mutation 探針 monkeypatch 用）。"""
    violations = _claim_check.check_files(paths)
    if violations:
        lines = [f"{v.file}:{v.line}: {v.message}\n{v.unit_text}" for v in violations]
        return 1, "\n".join(lines)
    return 0, ""


def _run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    """執行 verification_claim_check.py。"""
    argv = [str(PYTHON), str(CLAIM_CHECK), *args]
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_fixture(path: Path, content: str) -> Path:
    """寫入測試用 markdown fixture。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _append_pending_event(event: dict) -> None:
    """append 一筆 pending ledger 事件。"""
    ledger = _pending_ledger()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _create_manual_receipt(
    claim_id: str,
    *,
    exit_code: int = 0,
    runtime_class: str = "helper_smoke",
    selected_node_ids: list[str] | None = None,
    failed: int = 0,
    with_audit: bool = True,
) -> str:
    """手動建立 receipt + 可選審計事件（測試用）。"""
    receipts_dir = _receipts_dir()
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
        "exit_code": exit_code,
        "runtime_class": runtime_class,
        "requested_class": None,
        "pytest_summary": "1 passed",
        "selected_node_ids": selected_node_ids or [],
        "markers": [],
        "passed": 1 if exit_code == 0 and failed == 0 else 0,
        "failed": failed,
        "skipped": 0,
        "stdout_sha256": "test",
        "stderr_sha256": "test",
        "log_sha256": log_sha256,
        "log_path": str(log_path),
        "tail_excerpt": ["ok"],
    }
    json_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if with_audit:
        audit_log = _audit_log()
        audit_log.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "event": "receipt",
            "receipt_id": receipt_id,
            "emitter": "run_with_receipt.py",
            "command_sha256": receipt["command_sha256"],
            "receipt_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
            "log_sha256": log_sha256,
            "git_head": "test",
            "exit_code": exit_code,
            "runtime_class": runtime_class,
            "started_at": receipt["started_at"],
            "ended_at": receipt["ended_at"],
            "ts": receipt["ended_at"],
        }
        with audit_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
    return receipt_id


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


def test_v2_fake_claim_blocked(tmp_path: Path) -> None:
    """V2：operational 假 claim 無 VERIFY → exit 1。"""
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\n- 已驗 ✅ align mutation 通過\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr


def test_v3_real_claim_with_verify_passes(tmp_path: Path) -> None:
    """V3：VERIFY 指向 exit0 且 class 匹配的 receipt → exit 0。"""
    claim_id = "v3-good-claim"
    node_id = f"{Path(__file__).as_posix()}::test_mutation_receipt_missing_field_fails"
    proc = _run_wrapper(claim_id, [str(PYTHON), "-m", "pytest", node_id, "-q"])
    assert proc.returncode == 0
    receipt_id, receipt = _latest_receipt_for_claim(claim_id)
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        (
            "## 現役任務\n\n"
            f"- 已驗 VERIFY:{receipt['receipt_id']} "
            f"{node_id} mutation runtime 通過\n"
        ),
    )
    check = _run_checker("--files", str(fixture))
    assert check.returncode == 0, check.stderr


def test_v4_helper_smoke_cannot_back_mutation_claim(tmp_path: Path) -> None:
    """V4：helper_smoke receipt 不得支撐 mutation 真紅 claim。"""
    receipt_id = _create_manual_receipt(
        "v4-helper-smoke",
        runtime_class="helper_smoke",
        selected_node_ids=[],
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"## 已完成\n\n- mutation runtime 真紅 VERIFY:{receipt_id}\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "runtime_class" in proc.stderr


def test_v5_polarity_mismatch_blocked(tmp_path: Path) -> None:
    """V5：claim 已驗通過但 receipt exit≠0 → exit 1。"""
    receipt_id = _create_manual_receipt(
        "v5-fail-exit",
        exit_code=1,
        failed=1,
        runtime_class="mutation_runtime",
        selected_node_ids=["tests/x.py::test_mutation_x"],
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        (
            f"- 已驗 VERIFY:{receipt_id} "
            "tests/x.py::test_mutation_x 通過\n"
        ),
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "極性" in proc.stderr


def test_v6_handwritten_receipt_without_audit_blocked(tmp_path: Path) -> None:
    """V6：手寫 receipt 無審計事件 → exit 1。"""
    receipt_id = _create_manual_receipt(
        "v6-no-audit",
        runtime_class="mutation_runtime",
        selected_node_ids=["tests/x.py::test_mutation_x"],
        with_audit=False,
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"- 已驗 VERIFY:{receipt_id} tests/x.py::test_mutation_x 通過\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "審計事件缺失" in proc.stderr


def test_v7_false_positive_zero_on_spec_files() -> None:
    """V7：本 repo SPEC/DELIB/PLAIN 合法引用不得誤擋。"""
    proc = _run_checker(
        "--files",
        "docs/VERIFY_GATE_SPEC.md",
        "handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md",
        "docs/VERIFY_GATE_SPEC_PLAIN.md",
    )
    assert proc.returncode == 0, proc.stderr


def test_v8_discussion_exemption_not_abused(tmp_path: Path) -> None:
    """V8：RESULT 檔 operational 新 claim 仍擋；HANDOFF VERIFY-EXEMPT 不生效。"""
    result_file = _write_fixture(
        tmp_path / "handoffs" / "20260701-TEST-RESULT.md",
        "## 已完成\n\nalign mutation 已驗真紅，無收據。\n",
    )
    proc_result = _run_checker("--files", str(result_file))
    assert proc_result.returncode == 1

    handoff = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\n- 已驗 ✅ VERIFY-EXEMPT:doc-example:test-1\n",
    )
    proc_handoff = _run_checker("--files", str(handoff))
    assert proc_handoff.returncode == 1


def test_v9_static_receipt_cannot_back_mutation_claim(tmp_path: Path) -> None:
    """V9：static_only receipt 不能支撐 mutation claim。"""
    receipt_id = _create_manual_receipt(
        "v9-static",
        runtime_class="static_only",
        selected_node_ids=[],
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"- 已驗 VERIFY:{receipt_id} mutation runtime 真紅\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "runtime_class" in proc.stderr


def test_v10_same_paragraph_partial_scope_blocked(tmp_path: Path) -> None:
    """V10：同段兩 claim，receipt 只覆蓋一個 scope → 另一仍擋。"""
    receipt_id = _create_manual_receipt(
        "v10-center",
        runtime_class="mutation_runtime",
        selected_node_ids=["tests/feature_engineering/test_x.py::test_mutation_center"],
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        (
            "- center mutation 真紅 VERIFY:"
            f"{receipt_id} tests/feature_engineering/test_x.py::test_mutation_center; "
            "align mutation 真紅\n"
        ),
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr


def test_v11_pending_open_blocks_done_claim(tmp_path: Path) -> None:
    """V11：未結 pending 擋同 task DONE/已驗；close 後放行。"""
    task_id = "P0-FF-3"
    pending_id = "pending-v11-001"
    _append_pending_event(
        {
            "event": "open",
            "pending_id": pending_id,
            "claim_fingerprint": "abc",
            "source_file": "handoffs/x-RESULT.md",
            "source_line": 1,
            "required_runtime_class": "mutation_runtime",
            "required_node_ids": [],
            "required_markers": [],
            "task_id": task_id,
            "ts": "2099-01-01T00:00:00Z",
        }
    )
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260701-P0-FF-3-RESULT.md",
        "\n".join(
            [
                "STATIC_CHECK=NOT_RUN",
                "RUNTIME_CHECK=NOT_RUN",
                "MUTATION_CHECK=NOT_RUN",
                "RECEIPTS=[]",
                "OPEN_PENDING=[]",
                "STATUS: DONE — P0-FF-3",
            ]
        )
        + "\n",
    )
    blocked = _run_checker("--files", str(fixture))
    assert blocked.returncode == 1
    assert pending_id in blocked.stderr

    list_open = _run_checker("list-open")
    assert pending_id in list_open.stdout

    _append_pending_event(
        {
            "event": "close",
            "pending_id": pending_id,
            "claim_fingerprint": "abc",
            "source_file": "handoffs/x-RESULT.md",
            "source_line": 1,
            "required_runtime_class": "mutation_runtime",
            "required_node_ids": [],
            "required_markers": [],
            "task_id": task_id,
            "ts": "2099-01-01T00:00:01Z",
            "receipt_id": _create_manual_receipt(
                "v11-close",
                runtime_class="mutation_runtime",
                selected_node_ids=[],
            ),
        }
    )
    allowed = _run_checker("--files", str(fixture))
    assert allowed.returncode == 0, allowed.stderr


def test_v17_incident_byte_fixtures_blocked(tmp_path: Path) -> None:
    """V17：事故原文 operational claim 無 VERIFY → 必擋。"""
    handoff_fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "- **已驗 ✅**:① align mutation 真紅(babu8o07p);\n",
    )
    commit_fixture = tmp_path / "COMMIT_MSG.txt"
    commit_fixture.write_text(
        "已驗(babu8o07p):對齊 mutation 真紅\n",
        encoding="utf-8",
    )
    metafix_fixture = _write_fixture(
        tmp_path / "handoffs" / "20260630-FF-P0FF3-METAFIX-PROMPT.md",
        "## 已完成\n\n也正確紅\n",
    )

    for target in (handoff_fixture, metafix_fixture):
        proc = _run_checker("--files", str(target))
        assert proc.returncode == 1, proc.stderr

    commit_proc = _run_checker("--commit-msg", str(commit_fixture))
    assert commit_proc.returncode == 1
    assert "babu8o07p" in commit_proc.stderr or "operational claim" in commit_proc.stderr


def test_mutation_drop_backing_check_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 探針：移除審計事件驗證 → V6 須轉綠（證明 check_backing 有牙齒）。"""
    receipt_id = _create_manual_receipt(
        "mutation-no-audit-probe",
        runtime_class="mutation_runtime",
        selected_node_ids=["tests/x.py::test_mutation_x"],
        with_audit=False,
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"- 已驗 VERIFY:{receipt_id} tests/x.py::test_mutation_x 通過\n",
    )

    real_check = _claim_check.check_backing

    def broken_check(claim: object, backing_id: str) -> tuple[bool, str]:
        if backing_id.startswith("SIGNOFF:"):
            return real_check(claim, backing_id)
        return True, ""

    monkeypatch.setattr(_claim_check, "check_backing", broken_check)
    code_broken, err_broken = _check_files_inprocess([fixture])
    assert code_broken == 0, err_broken

    monkeypatch.setattr(_claim_check, "check_backing", real_check)
    code_real, err_real = _check_files_inprocess([fixture])
    assert code_real == 1
    assert "審計事件缺失" in err_real


def test_mutation_allow_helper_smoke_for_mutation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mutation 探針：放寬 runtime_class 檢查 → V4 須 FAIL。"""
    receipt_id = _create_manual_receipt(
        "mutation-class-probe",
        runtime_class="helper_smoke",
        selected_node_ids=[],
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"- 已驗 VERIFY:{receipt_id} mutation runtime 通過\n",
    )

    real_sufficient = _claim_check._runtime_class_sufficient

    def broken_sufficient(claim: object, runtime_class: str) -> bool:
        return True

    monkeypatch.setattr(_claim_check, "_runtime_class_sufficient", broken_sufficient)
    code_broken, err_broken = _check_files_inprocess([fixture])
    assert code_broken == 0, err_broken

    monkeypatch.setattr(_claim_check, "_runtime_class_sufficient", real_sufficient)
    code_real, err_real = _check_files_inprocess([fixture])
    assert code_real == 1
    assert "runtime_class" in err_real


@pytest.mark.parametrize(
    "claim_line",
    [
        "- align 探針紅\n",
        "- align 正確紅\n",
        "- align 搞定\n",
    ],
)
def test_b2_incident_synonyms_blocked_without_verify(
    tmp_path: Path, claim_line: str
) -> None:
    """B2-1：事故同義詞 operational 無 VERIFY → exit 1。"""
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        f"## 現役任務\n\n{claim_line}",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr


def test_b2_inline_discussion_marker_does_not_suppress_operational(
    tmp_path: Path,
) -> None:
    """B2-2：inline claim-context 註解不得免責 operational bullet。"""
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\n- <!-- claim-context: discussion --> align mutation 已驗真紅\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr


def test_b2_forensics_filename_operational_still_blocked(tmp_path: Path) -> None:
    """B2-3：FORENSICS 檔名不得單獨免責 operational 新 claim。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260701-FF-FORENSICS-FAKE.md",
        "## 已完成\n\n- align mutation 已驗真紅\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr


def test_b2_reused_verify_wrong_node_id_blocked(tmp_path: Path) -> None:
    """B2-4：共用檔路徑不足以支撐不同 node-id claim。"""
    receipt_id = _create_manual_receipt(
        "b2-align-only",
        runtime_class="mutation_runtime",
        selected_node_ids=["tests/x.py::test_mutation_align"],
    )
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        (
            "- center mutation 真紅 VERIFY:"
            f"{receipt_id} tests/x.py::test_mutation_center; "
            f"align mutation 真紅 VERIFY:{receipt_id} tests/x.py::test_mutation_align\n"
        ),
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "scope" in proc.stderr


def test_b2_fake_pending_close_still_blocks_done(tmp_path: Path) -> None:
    """B2-5：偽 close（錯 fingerprint / 無真 receipt）不得關閉 pending。"""
    task_id = "P0-FF-3"
    pending_id = "pending-b2-fake-close"
    _append_pending_event(
        {
            "event": "open",
            "pending_id": pending_id,
            "claim_fingerprint": "abc",
            "source_file": "handoffs/x-RESULT.md",
            "source_line": 1,
            "required_runtime_class": "mutation_runtime",
            "required_node_ids": ["tests/x.py::test_mutation_align"],
            "required_markers": [],
            "task_id": task_id,
            "ts": "2099-01-01T00:00:00Z",
        }
    )
    _append_pending_event(
        {
            "event": "close",
            "pending_id": pending_id,
            "claim_fingerprint": "wrong",
            "source_file": "handoffs/x-RESULT.md",
            "source_line": 1,
            "required_runtime_class": "static_only",
            "required_node_ids": [],
            "required_markers": [],
            "task_id": task_id,
            "ts": "2099-01-01T00:00:01Z",
            "receipt_id": "20990101T000000Z-fake-no-receipt",
        }
    )
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260701-P0-FF-3-RESULT.md",
        "STATUS: DONE — P0-FF-3\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert pending_id in proc.stderr

