"""V-A：戳記缺 task:<id> 一律 FAIL（無 grandfather）。

nodeid:
  test_no_task_stamp_rejected
  test_with_task_allowlist_still_passes
  test_mutation_allow_missing_task_breaks_guard
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RECONCILE_CHECK = REPO_ROOT / "scripts" / "reconcile_stamps_check.sh"
BODY_HASH_SH = REPO_ROOT / "scripts" / "reconcile_body_hash.sh"
PROVENANCE_PY = REPO_ROOT / "scripts" / "verify_task_provenance.py"
DELIB_RECONCILE = REPO_ROOT / "handoffs" / "20260701-VERIFYGATE-DELIB-RECONCILE.md"
COMMITTEE_AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"


@pytest.fixture(autouse=True)
def _isolated_committee_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """隔離 committee audit，避免外洩真實 log。"""
    audit = tmp_path / "committee_audit.log"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text("", encoding="utf-8")
    monkeypatch.setenv(COMMITTEE_AUDIT_ENV, str(audit))


def _body_hash(path: Path) -> str:
    proc = subprocess.run(
        ["bash", str(BODY_HASH_SH), str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def test_no_task_stamp_rejected(tmp_path: Path) -> None:
    """三家 APPROVED 但戳記無 task:<id> → reconcile_stamps_check rc≠0。"""
    body = "## 摘要\n\nV-A no-task stamp fixture。\n"
    fixture = tmp_path / "no_task_reconcile.md"
    # 先寫入佔位戳記以算 body-hash（## 戳記 前內容）
    fixture.write_text(f"{body}\n## 戳記\n\nPLACEHOLDER\n", encoding="utf-8")
    h = _body_hash(fixture)
    stamps = "\n".join(
        [
            f"RECONCILE-STAMP: codex APPROVED 2099-01-01 sha256:{h}",
            f"RECONCILE-STAMP: composer APPROVED 2099-01-01 sha256:{h}",
            f"RECONCILE-STAMP: grok APPROVED 2099-01-01 sha256:{h}",
        ]
    )
    fixture.write_text(f"{body}\n## 戳記\n\n{stamps}\n", encoding="utf-8")

    proc = subprocess.run(
        ["bash", str(RECONCILE_CHECK), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    assert proc.returncode != 0, (
        f"無 task 戳記應 FAIL; rc={proc.returncode} "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    cl = combined.lower()
    assert (
        "provenance" in cl or "task" in cl or "缺 task" in combined
    ), f"訊息須指明 task/provenance 問題: {combined!r}"


def test_with_task_allowlist_still_passes() -> None:
    """既有 allowlist 戳記（帶 task）→ rc=0（防過度收緊）。"""
    # legacy 兩家 roster（同 test_verify_gate_b4.test_delib_reconcile_still_passes_allowlist）
    proc = subprocess.run(
        ["bash", str(RECONCILE_CHECK), str(DELIB_RECONCILE), "codex,composer"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RECONCILE-STAMP PASS" in proc.stdout


def _load_provenance():
    spec = importlib.util.spec_from_file_location(
        "verify_task_provenance_va_mut", PROVENANCE_PY
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mutation_allow_missing_task_breaks_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mutation：缺 task 改回 return 0 → 防護斷言 rc!=0 轉紅（證 test_no_task 有牙齒）。"""
    mod = _load_provenance()
    original = mod.check_stamp_provenance

    def _buggy_allow_missing(stamp_line: str, reconcile_file: str = "") -> tuple[int, str]:
        # 舊洞：無 task 直接放行
        task_match = mod.STAMP_TASK_RE.search(stamp_line)
        if not task_match:
            return 0, ""
        return original(stamp_line, reconcile_file)

    monkeypatch.setattr(mod, "check_stamp_provenance", _buggy_allow_missing)
    rc, _msg = mod.check_stamp_provenance(
        "RECONCILE-STAMP: codex APPROVED 2099-01-01 "
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    with pytest.raises(AssertionError):
        assert rc != 0, "缺 task 應 FAIL"
