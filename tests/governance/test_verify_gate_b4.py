"""VERIFY_GATE Phase 4 (B4) — mutation receipt + W2/W3 provenance + audit_chain 測試。"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "venv" / "bin" / "python"
MUTATION_PROBE = REPO_ROOT / "scripts" / "mutation_probe_check.sh"
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
RECONCILE_CHECK = REPO_ROOT / "scripts" / "reconcile_stamps_check.sh"
VERIFY_AUDIT_CHAIN = REPO_ROOT / "scripts" / "verify_audit_chain.py"
VERIFY_TASK_PROVENANCE = REPO_ROOT / "scripts" / "verify_task_provenance.py"
DELIB_RECONCILE = REPO_ROOT / "handoffs" / "20260701-VERIFYGATE-DELIB-RECONCILE.md"

RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
COMMITTEE_AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"

_spec = importlib.util.spec_from_file_location("verify_audit_chain", VERIFY_AUDIT_CHAIN)
_audit_chain = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_audit_chain)

_prov_spec = importlib.util.spec_from_file_location("verify_task_provenance", VERIFY_TASK_PROVENANCE)
_task_prov = importlib.util.module_from_spec(_prov_spec)
assert _prov_spec.loader is not None
_prov_spec.loader.exec_module(_task_prov)


@pytest.fixture(autouse=True)
def isolated_b4_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """B4 測試用臨時 receipt/audit 路徑，避免污染真實目錄。"""
    receipts_dir = tmp_path / "run_receipts"
    verify_audit = tmp_path / "gate" / "verify_audit.log"
    committee_audit = tmp_path / "gate" / "committee_audit.log"
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(receipts_dir))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(verify_audit))
    monkeypatch.setenv(COMMITTEE_AUDIT_ENV, str(committee_audit))


def _write_green_mutation_fixture(path: Path) -> Path:
    """寫入會通過 mutation_probe_check 的最小測試檔。"""
    path.write_text(
        '''import pytest

def _add(a: int, b: int) -> int:
  return a + b

def test_example_passes() -> None:
    """底層正確性測試。"""
    assert _add(1, 1) == 2

def test_mutation_example_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """§B1.1：monkeypatch 注入錯誤算法 → 探針必紅。"""
    monkeypatch.setattr("test_green_probe._add", lambda a, b: a + b + 1)
    with pytest.raises(AssertionError):
        assert _add(1, 1) == 2
'''.replace("test_green_probe", path.stem),
        encoding="utf-8",
    )
    return path


def _write_red_mutation_fixture(path: Path) -> Path:
    """寫入 mutation 探針會 pytest 失敗的測試檔（探針無牙齒）。"""
    path.write_text(
        '''import pytest

def _add(a: int, b: int) -> int:
    return a + b

def test_example_passes() -> None:
    assert _add(2, 2) == 4

def test_mutation_example_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """探針應紅但 assert 通過 → mutation_probe_check 須 FAIL。"""
    monkeypatch.setattr("''' + path.stem + '''._add", lambda a, b: a + b)
    with pytest.raises(AssertionError):
        assert _add(2, 2) == 4
''',
        encoding="utf-8",
    )
    return path


def _run_mutation_probe(*paths: str | Path) -> subprocess.CompletedProcess[str]:
    """執行 mutation_probe_check.sh。"""
    argv = ["bash", str(MUTATION_PROBE), *[str(p) for p in paths]]
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _key_output_lines(text: str) -> list[str]:
    """抽取 PASS/FAIL 判定相關行（忽略 receipt 副作用行）。"""
    keys = (
        "MUTATION-PROBE PASS",
        "MUTATION-PROBE FAIL",
        "→ 跑 mutation 探針",
        "passed",
        "failed",
        "ERROR",
    )
    return [line for line in text.splitlines() if any(k in line for k in keys)]


def _append_committee_dispatch(
    audit_log: Path,
    *,
    task_id: str,
    output_path: Path,
    family: str = "composer",
) -> None:
    """append committee_dispatch 審計事件。"""
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    rel_output = str(output_path).replace("\\", "/")
    marker = "handoffs/"
    idx = rel_output.find(marker)
    if idx >= 0:
        rel_output = rel_output[idx:]
    event = {
        "event": "committee_dispatch",
        "task_id": task_id,
        "family": family,
        "output_path": rel_output,
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "ts": "2099-01-01T00:00:00Z",
    }
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _run_gate_adversarial(adversarial: str) -> subprocess.CompletedProcess[str]:
    """以高風險 dispatch + --adversarial 跑 gate.sh（template n/a 避開 spec 機檢）。

    GATE_DIR_OVERRIDE 指向 tmp:token/audit 落隔離目錄,不汙染真實 .claude/gate/audit.log。
    """
    gate_tmp = tempfile.mkdtemp(prefix="gate_b4_test_")
    env = dict(os.environ, GATE_DIR_OVERRIDE=gate_tmp)
    argv = [
        "bash",
        str(GATE_SH),
        "dispatch",
        "--intent",
        "B4 test adversarial provenance",
        "--risk",
        "high",
        "--facts-asked",
        "none-needed:B4 unit test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:B4 adversarial provenance test",
        "--adversarial",
        adversarial,
    ]
    return subprocess.run(
        argv, cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env
    )


def _write_reconcile_with_stamp(
    path: Path,
    *,
    body: str,
    stamp_line: str,
) -> Path:
    """寫入含戳記的 reconcile fixture。"""
    content = f"{body}\n\n## 戳記\n\n{stamp_line}\n"
    path.write_text(content, encoding="utf-8")
    return path


def test_mutation_probe_green_produces_receipt_and_same_verdict(tmp_path: Path) -> None:
    """Task 4.1：綠 fixture exit+關鍵訊息一致且產 receipt。"""
    fixture = _write_green_mutation_fixture(tmp_path / "test_green_probe.py")
    proc = _run_mutation_probe(fixture)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "MUTATION-PROBE PASS" in proc.stdout
    assert any("passed" in line for line in proc.stdout.splitlines())

    receipts_dir = Path(os.environ[RECEIPTS_DIR_ENV])
    matches = list(receipts_dir.glob("*-mutation-test_green_probe.json"))
    assert matches, "expected receipt json for mutation-test_green_probe"

    committee_audit = Path(os.environ[COMMITTEE_AUDIT_ENV])
    audit_text = committee_audit.read_text(encoding="utf-8")
    assert "mutation_receipt=" in audit_text


def test_mutation_probe_red_same_fail_verdict_and_receipt(tmp_path: Path) -> None:
    """Task 4.1：紅 fixture exit=1 且仍產 receipt。"""
    fixture = _write_red_mutation_fixture(tmp_path / "test_red_probe.py")
    proc = _run_mutation_probe(fixture)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "MUTATION-PROBE FAIL" in proc.stdout

    receipts_dir = Path(os.environ[RECEIPTS_DIR_ENV])
    matches = list(receipts_dir.glob("*-mutation-test_red_probe.json"))
    assert matches, "expected receipt even on failing mutation probe"


def test_mutation_probe_key_lines_stable_green_vs_red(tmp_path: Path) -> None:
    """Task 4.1：綠/紅 fixture 關鍵判定行結構一致（PASS vs FAIL 僅結論不同）。"""
    green = _write_green_mutation_fixture(tmp_path / "test_green_key.py")
    red = _write_red_mutation_fixture(tmp_path / "test_red_key.py")
    green_proc = _run_mutation_probe(green)
    red_proc = _run_mutation_probe(red)

    assert green_proc.returncode == 0
    assert red_proc.returncode == 1
    assert "→ 跑 mutation 探針" in green_proc.stdout
    assert "→ 跑 mutation 探針" in red_proc.stdout
    assert "MUTATION-PROBE PASS" in green_proc.stdout
    assert "MUTATION-PROBE FAIL" in red_proc.stdout


def test_gate_adversarial_rejects_non_adv_non_reconcile(tmp_path: Path) -> None:
    """Task 4.2：非 ADV 且非 reconcile 任意路徑 → gate 拒。"""
    fake = tmp_path / "not-adv.md"
    fake.write_text("# not an ADV\n", encoding="utf-8")
    proc = _run_gate_adversarial(str(fake))
    assert proc.returncode == 1
    combined = proc.stdout + proc.stderr
    assert "reconcile" in combined.lower() or "ADV" in combined


def test_gate_adversarial_rejects_without_dispatch(tmp_path: Path) -> None:
    """Task 4.2：fake ADV 無 task 審計 → gate 拒。"""
    fake_adv = REPO_ROOT / "handoffs" / "20990101-B4-FAKE-ADV-COMPOSER.md"
    fake_adv.write_text("# fake adversarial\n", encoding="utf-8")
    rel = "handoffs/20990101-B4-FAKE-ADV-COMPOSER.md"
    try:
        proc = _run_gate_adversarial(rel)
        assert proc.returncode == 1
        combined = proc.stdout + proc.stderr
        assert "provenance" in combined.lower() or "committee_dispatch" in combined
    finally:
        fake_adv.unlink(missing_ok=True)


def test_gate_adversarial_passes_with_dispatch(tmp_path: Path) -> None:
    """Task 4.2：有 committee_dispatch 審計 → gate 過。"""
    adv_path = REPO_ROOT / "handoffs" / "20990101-B4-TEST-ADV-COMPOSER.md"
    adv_path.write_text("# real adversarial review\nVERDICT: APPROVED\n", encoding="utf-8")

    committee_audit = Path(os.environ[COMMITTEE_AUDIT_ENV])
    rel = "handoffs/20990101-B4-TEST-ADV-COMPOSER.md"
    _append_committee_dispatch(
        committee_audit,
        task_id="testadv01",
        output_path=adv_path,
        family="composer",
    )

    try:
        proc = _run_gate_adversarial(rel)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "GATE PASS" in proc.stdout
    finally:
        adv_path.unlink(missing_ok=True)


def test_reconcile_rejects_stamp_without_dispatch(tmp_path: Path) -> None:
    """Task 4.3：手寫戳記無審計 → reconcile FAIL。"""
    body = "## 摘要\n\n測試 reconcile body。\n"
    stamp = (
        "RECONCILE-STAMP: composer APPROVED 2099-01-01 "
        "sha256:PLACEHOLDER task:fakestamp1"
    )
    fixture = _write_reconcile_with_stamp(tmp_path / "fake_reconcile.md", body=body, stamp_line=stamp)
    # 先算 body hash 並更新戳記
    body_hash_proc = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "reconcile_body_hash.sh"), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    body_hash = body_hash_proc.stdout.strip()
    content = fixture.read_text(encoding="utf-8").replace("PLACEHOLDER", body_hash)
    fixture.write_text(content, encoding="utf-8")

    proc = subprocess.run(
        ["bash", str(RECONCILE_CHECK), str(fixture), "composer"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "provenance" in (proc.stdout + proc.stderr).lower()


def test_reconcile_rejects_backdated_stamp_not_on_allowlist(tmp_path: Path) -> None:
    """Task 4.3：新檔回填舊日期戳記但不在 allowlist → reconcile FAIL。"""
    body = "## 摘要\n\n偽造 backdate reconcile。\n"
    stamp = (
        "RECONCILE-STAMP: composer APPROVED 2026-07-01 "
        "sha256:PLACEHOLDER task:fakestamp1"
    )
    fixture = _write_reconcile_with_stamp(tmp_path / "fake_backdate.md", body=body, stamp_line=stamp)
    body_hash_proc = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "reconcile_body_hash.sh"), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    body_hash = body_hash_proc.stdout.strip()
    content = fixture.read_text(encoding="utf-8").replace("PLACEHOLDER", body_hash)
    fixture.write_text(content, encoding="utf-8")

    proc = subprocess.run(
        ["bash", str(RECONCILE_CHECK), str(fixture), "composer"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "provenance" in (proc.stdout + proc.stderr).lower()


def test_reconcile_passes_with_dispatch_and_hash(tmp_path: Path) -> None:
    """Task 4.3：真派工事件 + 輸出 hash → reconcile PASS。"""
    output = tmp_path / "committee_output.md"
    output.write_text("# committee output\nAPPROVED\n", encoding="utf-8")

    body = "## 摘要\n\n真委員 reconcile。\n"
    fixture = tmp_path / "real_reconcile.md"
    fixture.write_text(f"{body}\n## 戳記\n\nPLACEHOLDER\n", encoding="utf-8")
    body_hash_proc = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "reconcile_body_hash.sh"), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    body_hash = body_hash_proc.stdout.strip()
    stamp = (
        f"RECONCILE-STAMP: composer APPROVED 2099-01-01 "
        f"sha256:{body_hash} task:realtask1"
    )
    fixture.write_text(f"{body}\n## 戳記\n\n{stamp}\n", encoding="utf-8")

    committee_audit = Path(os.environ[COMMITTEE_AUDIT_ENV])
    _append_committee_dispatch(
        committee_audit,
        task_id="realtask1",
        output_path=output,
        family="composer",
    )

    proc = subprocess.run(
        ["bash", str(RECONCILE_CHECK), str(fixture), "composer"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RECONCILE-STAMP PASS" in proc.stdout


def test_delib_reconcile_still_passes_allowlist() -> None:
    """Task 4.3：既有 DELIB reconcile（legacy allowlist）須仍 PASS。"""
    proc = subprocess.run(
        ["bash", str(RECONCILE_CHECK), str(DELIB_RECONCILE)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RECONCILE-STAMP PASS" in proc.stdout


def test_audit_chain_detects_tamper(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Task 4.4：竄改 receipt → TAMPER；正常 → OK。"""
    receipts_dir = tmp_path / "run_receipts"
    audit_log = tmp_path / "verify_audit.log"
    receipts_dir.mkdir(parents=True)

    ok_id = "20990101T000001Z-ok-chain"
    bad_id = "20990101T000002Z-bad-chain"
    log_ok = receipts_dir / f"{ok_id}.log"
    log_bad = receipts_dir / f"{bad_id}.log"
    json_ok = receipts_dir / f"{ok_id}.json"
    json_bad = receipts_dir / f"{bad_id}.json"
    log_ok.write_bytes(b"ok log\n")
    log_bad.write_bytes(b"bad log\n")

    ok_receipt = {
        "schema_version": "1.0",
        "receipt_id": ok_id,
        "claim_id": "ok-chain",
        "command": ["echo"],
        "command_sha256": "x",
        "cwd": str(REPO_ROOT),
        "git_head": "test",
        "tree_dirty": False,
        "started_at": "2099-01-01T00:00:00Z",
        "ended_at": "2099-01-01T00:00:01Z",
        "duration_seconds": 0.1,
        "exit_code": 0,
        "runtime_class": "static_only",
        "requested_class": None,
        "pytest_summary": None,
        "selected_node_ids": [],
        "markers": [],
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "stdout_sha256": "x",
        "stderr_sha256": "x",
        "log_sha256": hashlib.sha256(log_ok.read_bytes()).hexdigest(),
        "log_path": str(log_ok),
        "tail_excerpt": [],
    }
    bad_receipt = dict(ok_receipt)
    bad_receipt["receipt_id"] = bad_id
    bad_receipt["claim_id"] = "bad-chain"
    bad_receipt["log_sha256"] = hashlib.sha256(log_bad.read_bytes()).hexdigest()
    bad_receipt["log_path"] = str(log_bad)

    json_ok.write_text(json.dumps(ok_receipt, indent=2) + "\n", encoding="utf-8")
    json_bad.write_text(json.dumps(bad_receipt, indent=2) + "\n", encoding="utf-8")
    # 竄改 bad receipt（使 sha256 與審計事件不符）
    json_bad.write_text(json.dumps({**bad_receipt, "passed": 99}, indent=2) + "\n", encoding="utf-8")

    ok_receipt_sha = hashlib.sha256(json_ok.read_bytes()).hexdigest()
    bad_receipt_sha = hashlib.sha256(json_bad.read_bytes()).hexdigest()

    events = [
        {
            "event": "receipt",
            "receipt_id": ok_id,
            "receipt_sha256": ok_receipt_sha,
            "log_sha256": ok_receipt["log_sha256"],
        },
        {
            "event": "receipt",
            "receipt_id": bad_id,
            "receipt_sha256": "deadbeef" * 8,
            "log_sha256": bad_receipt["log_sha256"],
        },
    ]
    with audit_log.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")

    code = _audit_chain.run_report(audit_log, receipts_dir)
    captured = capsys.readouterr().out
    assert code == 0
    assert f"{ok_id}" in captured and "OK" in captured
    assert f"{bad_id}" in captured and "TAMPER" in captured
