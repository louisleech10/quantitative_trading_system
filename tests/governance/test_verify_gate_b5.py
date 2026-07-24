"""VERIFY_GATE Phase 5 (B5) — RESULT 硬欄位、#6 衝突、W1 FACT-RECEIPT 測試。"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
TEMPLATE_CHECK = REPO_ROOT / "scripts" / "template_check.sh"
from tests.governance._pyenv import PYTHON  # CI 無 venv → fallback sys.executable
RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"

_claim_spec = importlib.util.spec_from_file_location("verification_claim_check", CLAIM_CHECK)
_claim_check = importlib.util.module_from_spec(_claim_spec)
assert _claim_spec.loader is not None
sys.modules[_claim_spec.name] = _claim_check
_claim_spec.loader.exec_module(_claim_check)


@pytest.fixture(autouse=True)
def isolated_verify_gate_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試隔離：臨時 receipt/audit/ledger 路徑。"""
    receipts_dir = tmp_path / "run_receipts"
    audit_log = tmp_path / "gate" / "verify_audit.log"
    pending_ledger = tmp_path / "pending_verifications.jsonl"
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(receipts_dir))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(audit_log))
    monkeypatch.setenv(PENDING_LEDGER_ENV, str(pending_ledger))


def _write_fixture(path: Path, content: str) -> Path:
    """寫入測試 fixture。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


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


def _run_template_check(kind: str, path: Path) -> subprocess.CompletedProcess[str]:
    """執行 template_check.sh。"""
    return subprocess.run(
        ["bash", str(TEMPLATE_CHECK), kind, str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _valid_result_body(
    *,
    runtime: str = "NOT_RUN",
    mutation: str = "NOT_RUN",
    receipts: str = "[]",
) -> str:
    return (
        "STATIC_CHECK=NOT_RUN\n"
        f"RUNTIME_CHECK={runtime}\n"
        f"MUTATION_CHECK={mutation}\n"
        f"RECEIPTS={receipts}\n"
        "OPEN_PENDING=[]\n"
    )


def test_b5_result_runtime_pass_without_receipts_fails(tmp_path: Path) -> None:
    """5.1：RUNTIME_CHECK=PASS 無 RECEIPTS → checker FAIL。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260701-B5-RESULT.md",
        _valid_result_body(runtime="PASS", receipts="[]"),
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "RUNTIME_CHECK=PASS" in proc.stderr
    assert "RECEIPTS" in proc.stderr


def test_b5_result_mutation_not_run_with_verified_claim_fails(tmp_path: Path) -> None:
    """5.1：MUTATION_CHECK=NOT_RUN + 同 task 已驗宣稱 → checker FAIL。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260701-P0-FF-3-RESULT.md",
        _valid_result_body(mutation="NOT_RUN")
        + "\n## 已完成\n\n- P0-FF-3 align mutation 已驗\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "MUTATION_CHECK=NOT_RUN" in proc.stderr


def test_b5_result_valid_structured_fields_pass(tmp_path: Path) -> None:
    """5.1：合法 RESULT 結構欄位 → checker 過（無 operational 極性宣稱）。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "20260701-B5-OK-RESULT.md",
        _valid_result_body(runtime="PASS", receipts='["20990101T000000Z-b5"]'),
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 0, proc.stderr


def test_b5_result_invalid_enum_fails_checker(tmp_path: Path) -> None:
    """5.1：RESULT 枚舉外值 → checker FAIL（非僅 template_check）。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "bad-enum-RESULT.md",
        _valid_result_body(runtime="ok", mutation="PASS", receipts='["r1"]'),
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "枚舉外值" in proc.stderr


def test_b5_template_check_result_invalid_enum_fails(tmp_path: Path) -> None:
    """5.1：RESULT 枚舉外值 → template_check FAIL。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "bad-RESULT.md",
        _valid_result_body(runtime="ok"),
    )
    proc = _run_template_check("result", fixture)
    assert proc.returncode == 1
    assert "枚舉外值" in proc.stdout


def test_b5_template_check_result_valid_pass(tmp_path: Path) -> None:
    """5.1：合法 RESULT → template_check 過。"""
    fixture = _write_fixture(
        tmp_path / "handoffs" / "good-RESULT.md",
        _valid_result_body(runtime="N/A:skipped", mutation="FAIL", receipts="[]"),
    )
    proc = _run_template_check("result", fixture)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_b5_fingerprint_conflict_real_markdown_green_then_red_fails(tmp_path: Path) -> None:
    """5.2：真實 markdown 先綠(VERIFY)後紅、舊綠未標 SUPERSEDED → checker FAIL。"""
    green = _write_fixture(
        tmp_path / "docs" / "green.md",
        "- tests/x.py::test_mutation_align mutation P0-FF-3 已驗 PASS VERIFY:good-receipt\n",
    )
    red = _write_fixture(
        tmp_path / "handoffs" / "red.md",
        "- tests/x.py::test_mutation_align mutation P0-FF-3 FAIL 紅燈\n",
    )
    proc = _run_checker("--files", str(green), str(red))
    assert proc.returncode == 1
    assert "SUPERSEDED" in proc.stderr


def test_b5_fingerprint_conflict_real_markdown_superseded_passes(tmp_path: Path) -> None:
    """5.2：真實 markdown 舊綠標 SUPERSEDED 後有紅紀錄 → 放行。"""
    green = _write_fixture(
        tmp_path / "docs" / "green-superseded.md",
        "- SUPERSEDED:old-green tests/x.py::test_mutation_align mutation P0-FF-3 "
        "VERIFY:good-receipt\n",
    )
    red = _write_fixture(
        tmp_path / "handoffs" / "red-superseded.md",
        "- tests/x.py::test_mutation_align mutation P0-FF-3 FAIL 紅燈\n",
    )
    proc = _run_checker("--files", str(green), str(red))
    assert proc.returncode == 0, proc.stderr


def test_b5_fingerprint_conflict_green_then_red_without_superseded_fails() -> None:
    """5.2：同 fingerprint 先綠(VERIFY)後紅、舊綠未標 SUPERSEDED → FAIL。"""
    shared_line = "tests/x.py::test_mutation_align mutation P0-FF-3"
    green_unit = _claim_check.Unit(
        text=f"- {shared_line} VERIFY:good-receipt",
        source_file="handoffs/green.md",
        source_line=1,
        section_operational=True,
    )
    green_claim = _claim_check.ClaimObject(
        polarity="success",
        scope=["tests/x.py::test_mutation_align"],
        runtime_expectation="mutation",
        source_context="operational_result",
        backing_ids=["good-receipt"],
        source_line_text=shared_line,
        task_id="P0-FF-3",
        is_operational=True,
        has_strong_polarity=True,
    )
    red_unit = _claim_check.Unit(
        text=f"- {shared_line} 紅燈",
        source_file="handoffs/red.md",
        source_line=1,
        section_operational=True,
    )
    red_claim = _claim_check.ClaimObject(
        polarity="failure",
        scope=["tests/x.py::test_mutation_align"],
        runtime_expectation="mutation",
        source_context="operational_result",
        source_line_text=shared_line,
        task_id="P0-FF-3",
        is_operational=True,
        has_strong_polarity=True,
    )
    violations = _claim_check.check_fingerprint_conflicts(
        [(green_unit, green_claim), (red_unit, red_claim)]
    )
    assert violations
    assert "SUPERSEDED" in violations[0].message


def test_b5_fingerprint_conflict_superseded_green_passes() -> None:
    """5.2：舊綠標 SUPERSEDED 後有紅紀錄 → 放行。"""
    shared_line = "tests/x.py::test_mutation_align mutation P0-FF-3"
    green_unit = _claim_check.Unit(
        text=f"- SUPERSEDED:old-green {shared_line} VERIFY:good-receipt",
        source_file="handoffs/green.md",
        source_line=1,
        section_operational=True,
    )
    green_claim = _claim_check.ClaimObject(
        polarity="supersede",
        scope=["tests/x.py::test_mutation_align"],
        runtime_expectation="mutation",
        source_context="operational_result",
        backing_ids=["good-receipt"],
        source_line_text=shared_line,
        task_id="P0-FF-3",
        is_operational=True,
        has_strong_polarity=True,
    )
    red_unit = _claim_check.Unit(
        text=f"- {shared_line} 紅燈",
        source_file="handoffs/red.md",
        source_line=1,
        section_operational=True,
    )
    red_claim = _claim_check.ClaimObject(
        polarity="failure",
        scope=["tests/x.py::test_mutation_align"],
        runtime_expectation="mutation",
        source_context="operational_result",
        source_line_text=shared_line,
        task_id="P0-FF-3",
        is_operational=True,
        has_strong_polarity=True,
    )
    violations = _claim_check.check_fingerprint_conflicts(
        [(green_unit, green_claim), (red_unit, red_claim)]
    )
    assert not violations


def test_b5_spec_command_output_fact_receipt_missing_fails(tmp_path: Path) -> None:
    """5.3：§A 已確認+指令輸出事實缺 FACT-RECEIPT → template_check FAIL。"""
    fixture = _write_fixture(
        tmp_path / "docs" / "CMD_OUTPUT_BAD_SPEC.md",
        "\n".join(
            [
                "## §RISK",
                "risk",
                "- RISK-HIT: none",
                "## §A",
                "- **已確認**：pytest tests/governance/test_verify_gate.py -q 輸出 49 passed",
                "- 待確認：無",
                "## §C",
                "c",
                "## §P",
                "p",
                "## §V",
                "v",
                "## §R",
                "r",
                "## §N",
                "§G：N/A — test",
                "## §G",
                "N/A",
            ]
        ),
    )
    proc = _run_template_check("spec", fixture)
    assert proc.returncode == 1
    assert "FACT-RECEIPT" in proc.stdout


def test_b5_spec_fact_receipt_missing_fails(tmp_path: Path) -> None:
    """5.3：§A 已確認+資料結構事實缺 FACT-RECEIPT → template_check FAIL。"""
    fixture = _write_fixture(
        tmp_path / "docs" / "BAD_SPEC.md",
        "\n".join(
            [
                "## §RISK",
                "risk",
                "- RISK-HIT: none",
                "## §A",
                "- **已確認**：raw_data.index 是 DatetimeIndex",
                "- 待確認：無",
                "## §C",
                "c",
                "## §P",
                "p",
                "## §V",
                "v",
                "## §R",
                "r",
                "## §N",
                "§G：N/A — test",
                "## §G",
                "N/A",
            ]
        ),
    )
    proc = _run_template_check("spec", fixture)
    assert proc.returncode == 1
    assert "FACT-RECEIPT" in proc.stdout


def test_b5_spec_fact_receipt_present_passes(tmp_path: Path) -> None:
    """5.3：§A 附 FACT-RECEIPT → template_check 過。"""
    fixture = _write_fixture(
        tmp_path / "docs" / "GOOD_SPEC.md",
        "\n".join(
            [
                "## §RISK",
                "risk",
                "- RISK-HIT: none",
                "## §A",
                "- **已確認**：raw_data.index 是 DatetimeIndex FACT-RECEIPT:receipt-abc",
                "- 待確認：無",
                "## §C",
                "c",
                "## §P",
                "**Task 1.1 — 範例任務**",
                "- 驗證：pytest x -q → PASS",
                "- 邊界：空輸入→暫無；全 NaN→暫無",
                "- 存活至：Phase 5 完工後保留",
                "- 覆蓋風險：無",
                "- 不可做：不改既有斷言",
                "p",
                "## §V",
                "v",
                "## §R",
                "r",
                "## §N",
                "§G：N/A — test",
                "## §G",
                "N/A",
            ]
        ),
    )
    proc = _run_template_check("spec", fixture)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_b5_spec_pending_confirmation_passes(tmp_path: Path) -> None:
    """5.3：§A 待確認（非已確認）→ 放行。"""
    fixture = _write_fixture(
        tmp_path / "docs" / "PENDING_SPEC.md",
        "\n".join(
            [
                "## §RISK",
                "risk",
                "- RISK-HIT: none",
                "## §A",
                "- 待確認:raw_data.index 是否 DatetimeIndex",
                "- 待確認：無",
                "## §C",
                "c",
                "## §P",
                "**Task 1.1 — 範例任務**",
                "- 驗證：pytest x -q → PASS",
                "- 邊界：空輸入→暫無；全 NaN→暫無",
                "- 存活至：Phase 5 完工後保留",
                "- 覆蓋風險：無",
                "- 不可做：不改既有斷言",
                "p",
                "## §V",
                "v",
                "## §R",
                "r",
                "## §N",
                "§G：N/A — test",
                "## §G",
                "N/A",
            ]
        ),
    )
    proc = _run_template_check("spec", fixture)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_b5_spec_missing_risk_hit_fails(tmp_path: Path) -> None:
    """5.3：canonical fact receipt 齊但缺 RISK-HIT → template_check FAIL。"""
    fixture = _write_fixture(
        tmp_path / "docs" / "MISSING_RISK_HIT_SPEC.md",
        "\n".join(
            [
                "## §RISK",
                "risk",
                "## §A",
                "- **已確認**：raw_data.index 是 DatetimeIndex FACT-RECEIPT:receipt-abc",
                "- 待確認：無",
                "## §C",
                "c",
                "## §P",
                "p",
                "## §V",
                "v",
                "## §R",
                "r",
                "## §N",
                "§G：N/A — test",
                "## §G",
                "N/A",
            ]
        ),
    )
    proc = _run_template_check("spec", fixture)
    assert proc.returncode == 1
    assert "RISK-HIT" in proc.stdout


def test_b5_existing_verify_gate_spec_still_passes() -> None:
    """回歸：現行 VERIFY_GATE_SPEC 不因 §A 新檢查被誤擋。"""
    proc = _run_template_check("spec", REPO_ROOT / "docs" / "VERIFY_GATE_SPEC.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_b5_existing_verify_gate_todo_still_passes() -> None:
    """回歸：現行 VERIFY_GATE_TODO 仍 PASS。"""
    proc = _run_template_check("todo", REPO_ROOT / "docs" / "VERIFY_GATE_TODO.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_b5_v7_zero_false_positive_regression() -> None:
    """回歸：既有檔 V7 誤報=0（exit 0）。"""
    proc = _run_checker(
        "--files",
        "docs/VERIFY_GATE_SPEC.md",
        "handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md",
        "docs/VERIFY_GATE_SPEC_PLAIN.md",
    )
    assert proc.returncode == 0, proc.stderr
