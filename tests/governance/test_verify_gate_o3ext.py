"""GOV_O3EXT_R7 B2 — committee process file-class exemption."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
from tests.governance._pyenv import PYTHON  # CI 無 venv → fallback sys.executable
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
LEGACY_REGISTER = REPO_ROOT / "scripts" / "register_legacy_committee_files.sh"

RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
COMMITTEE_AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"


@pytest.fixture(autouse=True)
def isolated_verify_gate_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """隔離 receipt/audit/ledger，避免污染真實 .claude/gate/。"""
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(tmp_path / "run_receipts"))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(tmp_path / "gate" / "verify_audit.log"))
    monkeypatch.setenv(COMMITTEE_AUDIT_ENV, str(tmp_path / "gate" / "audit.log"))
    monkeypatch.setenv(PENDING_LEDGER_ENV, str(tmp_path / "pending_verifications.jsonl"))


def _write_fixture(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _append_committee_output(audit_log: Path, *, output_path: str, sha256: str) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event": "committee_output",
        "task_id": "o3ext-test",
        "family": "composer",
        "output_path": output_path,
        "output_sha256": sha256,
        "ts": "2099-01-01T00:00:00Z",
    }
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _run_checker(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PYTHON), str(CLAIM_CHECK), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env or os.environ.copy(),
    )


def test_registered_handoff_process_file_with_matching_raw_sha_is_exempt(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20990101-O3EXT-REVIEW-composer.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    rel = "handoffs/20990101-O3EXT-REVIEW-composer.md"
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=rel,
        sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    )

    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 0, proc.stderr


def test_registered_handoff_process_file_hash_mismatch_fails(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20990101-O3EXT-TAMPER-codex.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    rel = "handoffs/20990101-O3EXT-TAMPER-codex.md"
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=rel,
        sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    )
    fixture.write_text("## 已完成\n\nalign mutation 已驗真紅，事後改字\n", encoding="utf-8")

    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_handoff_root_same_prose_is_not_fileclass_exempt(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path="HANDOFF.md",
        sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    )

    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_docs_same_prose_is_not_fileclass_exempt(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "docs" / "20990101-O3EXT-smuggle.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path="docs/20990101-O3EXT-smuggle.md",
        sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    )

    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_committee_event_in_verify_audit_log_does_not_exempt(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20990101-O3EXT-WRONGLOG-composer.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    _append_committee_output(
        Path(os.environ[AUDIT_LOG_ENV]),
        output_path="handoffs/20990101-O3EXT-WRONGLOG-composer.md",
        sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    )

    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_o3_fileclass_can_be_disabled_by_env(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20990101-O3EXT-DISABLED-composer.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path="handoffs/20990101-O3EXT-DISABLED-composer.md",
        sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    )
    env = dict(os.environ, VERIFY_GATE_O3_FILECLASS="0")

    proc = _run_checker("--files", str(fixture), env=env)
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_bad_committee_json_line_is_ignored_fail_closed(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20990101-O3EXT-BADJSON-composer.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    audit = Path(os.environ[COMMITTEE_AUDIT_ENV])
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text('{"event":"committee_output", bad json\n', encoding="utf-8")

    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_legacy_register_rejects_non_whitelisted_file(tmp_path: Path) -> None:
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20990101-O3EXT-NOT-WHITELISTED.md",
        "## 已完成\n\nalign mutation 已驗真紅\n",
    )
    proc = subprocess.run(
        ["bash", str(LEGACY_REGISTER), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ, GATE_DIR_OVERRIDE=str(tmp_path / "gate")),
    )
    assert proc.returncode == 1
    assert "whitelist" in (proc.stdout + proc.stderr) or "白名單" in (
        proc.stdout + proc.stderr
    )


def test_legacy_register_rejects_missing_whitelisted_file(tmp_path: Path) -> None:
    missing = REPO_ROOT / "handoffs" / "20260702-FF-ALIGN-ORACLE-FACTS.md"
    proc = subprocess.run(
        ["bash", str(LEGACY_REGISTER), str(missing.with_name("20260702-FF-ALIGN-ORACLE-FACTS.md.missing"))],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ, GATE_DIR_OVERRIDE=str(tmp_path / "gate")),
    )
    assert proc.returncode == 1
