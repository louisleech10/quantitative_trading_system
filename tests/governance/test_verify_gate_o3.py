"""VERIFY_GATE O3 — 治理過程 forensic 檔誤報修補（HANDOFF/commit/RESULT 零豁免）。"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "venv" / "bin" / "python"
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"


@pytest.fixture(autouse=True)
def isolated_verify_gate_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試使用臨時 receipt/audit/ledger 路徑。"""
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(tmp_path / "run_receipts"))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(tmp_path / "gate" / "verify_audit.log"))
    monkeypatch.setenv(PENDING_LEDGER_ENV, str(tmp_path / "pending_verifications.jsonl"))


def _run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    """執行 verification_claim_check.py。"""
    argv = [str(PYTHON), str(CLAIM_CHECK), *args]
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )


def _write_fixture(path: Path, content: str) -> Path:
    """寫入測試用 markdown fixture。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_o3_redteam_attack_examples_allowed(tmp_path: Path) -> None:
    """O3-①：fenced / inline-code / blockquote 攻擊範例字串放行。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "x-REDTEAM-CODEX.md",
        "\n".join(
            [
                "## 紅隊反例",
                "",
                "> Codex 寫道「已驗真紅」",
                "",
                "模糊 scope 測試 `VERIFY:fast-example-id`",
                "",
                "```",
                "錯誤訊息範例：receipt 不存在: wash",
                "align mutation 已驗真紅 VERIFY:no-such-receipt",
                "```",
            ]
        )
        + "\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 0, proc.stderr


def test_o3_review_real_verify_still_blocked(tmp_path: Path) -> None:
    """O3-Codex-①：REVIEW 檔散文含真 VERIFY 無 backing 仍 exit 1。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260702-REAL-REVIEW.md",
        "align mutation 已驗真紅 VERIFY:no-such-receipt\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "no-such-receipt" in proc.stderr or "backing" in proc.stderr or "receipt" in proc.stderr


def test_o3_review_operational_section_still_blocked(tmp_path: Path) -> None:
    """O3-Codex-②：REVIEW 檔 operational 段無 backing 仍 exit 1。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260702-REAL-REVIEW-OP.md",
        "## 已完成\n\nalign mutation 已驗真紅 VERIFY:no-such-receipt\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "no-such-receipt" in proc.stderr


def test_o3_review_bare_polarity_still_blocked(tmp_path: Path) -> None:
    """O3-Codex-③：REVIEW 檔裸極性宣稱仍 exit 1。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260702-REAL-REVIEW.md",
        "align mutation 已驗真紅\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_o3_handoff_same_operational_still_blocked(tmp_path: Path) -> None:
    """O3-②：HANDOFF 同款 operational 無 backing 仍 exit 1（零豁免）。"""
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\nCodex 寫道「align 已驗真紅」\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_o3_commit_msg_same_still_blocked(tmp_path: Path) -> None:
    """O3-③：commit-msg 同款 operational 仍 exit 1。"""
    commit_fixture = tmp_path / "COMMIT_MSG.txt"
    commit_fixture.write_text(
        "Codex 寫道「align 已驗真紅」\n",
        encoding="utf-8",
    )
    proc = _run_checker("--commit-msg", str(commit_fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_o3_v7_regression_spec_files_unblocked() -> None:
    """O3-④：V7 既有 SPEC/DELIB 合法引用誤報=0。"""
    proc = _run_checker(
        "--files",
        "docs/VERIFY_GATE_SPEC.md",
        "handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md",
        "docs/VERIFY_GATE_SPEC_PLAIN.md",
    )
    assert proc.returncode == 0, proc.stderr


def test_o3_r6_fake_attribution_handoff_still_blocked(tmp_path: Path) -> None:
    """O3-④：R6 假歸屬在 HANDOFF 仍擋（不回歸）。"""
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\nCodex 檔案寫道「align 已驗真紅」\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_o3_fix_prompt_operational_claim_still_blocked(tmp_path: Path) -> None:
    """O3 邊界：FIX-PROMPT operational 段作者裸宣稱（非範例）仍擋。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260630-FF-P0FF3-METAFIX-PROMPT.md",
        "## 已完成\n\n也正確紅\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr


def test_o3_repo_redteam_files_exit_zero() -> None:
    """O3 驗收：本 repo REDTEAM 治理檔全放行。"""
    proc = _run_checker(
        "--files",
        "handoffs/20260702-VERIFYGATE-REDTEAM-CLOSURE-CODEX.md",
        "handoffs/20260702-VERIFYGATE-REDTEAM-CODEX.md",
        "handoffs/20260702-VERIFYGATE-REDTEAM-COMPOSER.md",
        "handoffs/20260702-VERIFYGATE-REDTEAM-FIX-PROMPT.md",
        "handoffs/20260702-VERIFYGATE-REDTEAM-RECONCILE.md",
    )
    assert proc.returncode == 0, proc.stderr
