"""INSTREV Phase B4 — gate.sh 用法模板 + dispatch.sh wrapper。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from tests.governance._pyenv import link_python_env  # CI 無 venv 相容
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
DISPATCH_SH = REPO_ROOT / "scripts" / "dispatch.sh"


def test_gate_missing_required_prints_usage_template() -> None:
    """gate.sh dispatch 缺必填 → exit 1 且印完整用法模板。"""
    proc = subprocess.run(
        ["bash", str(GATE_SH), "dispatch"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "scripts/gate.sh dispatch --intent" in proc.stdout


def test_gate_bad_kind_prints_usage_template() -> None:
    """gate.sh badkind → exit 1 且印模板。"""
    proc = subprocess.run(
        ["bash", str(GATE_SH), "badkind"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "register-output" in proc.stdout


def _setup_dispatch_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "dispatch_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    scripts = repo / "scripts"
    scripts.mkdir()
    for name in (
        "gate.sh",
        "dispatch.sh",
        "template_check.sh",
        "coverage_check.sh",
        "reconcile_stamps_check.sh",
        "verify_task_provenance.py",
    ):
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
    (repo / "handoffs").mkdir()
    link_python_env(repo)
    return repo


def test_dispatch_auto_task_id_and_output(tmp_path: Path) -> None:
    """dispatch.sh 不給 task-id/output → 轉呼 gate 帶自動 task-id 與 handoffs/*-RESULT.md。"""
    repo = _setup_dispatch_repo(tmp_path)
    gate_dir = tmp_path / "gate"
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    proc = subprocess.run(
        [
            "bash",
            str(DISPATCH_SH),
            "--intent",
            "phase-b-test",
            "--risk",
            "low",
            "--facts-asked",
            "none-needed:test",
            "--review-role",
            "single-executor:n/a",
            "--template",
            "n/a:test",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE PASS" in proc.stdout
    audit = gate_dir / "audit.log"
    assert audit.is_file()
    import re

    assert re.search(r"[0-9]{8}-phase-b-test", audit.read_text(encoding="utf-8"))
    assert re.search(r"handoffs/[0-9]{8}-phase-b-test-RESULT\.md", audit.read_text(encoding="utf-8"))


def test_dispatch_explicit_task_id_not_overridden(tmp_path: Path) -> None:
    """給定 --task-id 時 wrapper 不覆蓋為自動 id。"""
    repo = _setup_dispatch_repo(tmp_path)
    gate_dir = tmp_path / "gate_explicit"
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    tid = "20990101-explicit-id"
    proc = subprocess.run(
        [
            "bash",
            str(DISPATCH_SH),
            "--intent",
            "x",
            "--task-id",
            tid,
            "--risk",
            "low",
            "--facts-asked",
            "none-needed:test",
            "--review-role",
            "single-executor:n/a",
            "--template",
            "n/a:test",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE PASS" in proc.stdout
    audit = gate_dir / "audit.log"
    assert audit.is_file()
    dispatch_task_ids: list[str] = []
    for line in audit.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("{"):
            continue
        event = json.loads(line)
        if event.get("event") == "committee_dispatch":
            dispatch_task_ids.append(event["task_id"])
    assert dispatch_task_ids, "audit 應含 committee_dispatch"
    assert tid in dispatch_task_ids
    import re

    auto_id = re.compile(r"^\d{8}-x$")
    leaked = [t for t in dispatch_task_ids if auto_id.match(t)]
    assert not leaked, f"wrapper 覆蓋 explicit task-id，出現自動 id: {leaked}"


def test_dispatch_collision_existing_output(tmp_path: Path) -> None:
    """預建同名 output → wrapper exit 1 不覆寫。"""
    repo = _setup_dispatch_repo(tmp_path)
    import datetime

    tid = f"{datetime.date.today().strftime('%Y%m%d')}-phase-b-collision"
    out = repo / "handoffs" / f"{tid}-RESULT.md"
    out.write_text("# existing\n", encoding="utf-8")
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(tmp_path / "gate3")
    proc = subprocess.run(
        [
            "bash",
            str(DISPATCH_SH),
            "--intent",
            "phase-b-collision",
            "--risk",
            "low",
            "--facts-asked",
            "none-needed:test",
            "--review-role",
            "single-executor:n/a",
            "--template",
            "n/a:test",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "已存在" in proc.stderr
    assert out.read_text(encoding="utf-8") == "# existing\n"


def test_dispatch_passthrough_bogus_to_gate(tmp_path: Path) -> None:
    """未知參數原樣透傳 → gate.sh 報未預期參數。"""
    repo = _setup_dispatch_repo(tmp_path)
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(tmp_path / "gate4")
    proc = subprocess.run(
        [
            "bash",
            str(DISPATCH_SH),
            "--intent",
            "x",
            "--risk",
            "low",
            "--bogus",
            "y",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 1
    assert "未預期參數" in proc.stderr or "未預期參數" in proc.stdout


def test_dispatch_collision_task_id_in_audit(tmp_path: Path) -> None:
    """task-id 已在 audit committee_dispatch → exit 1。"""
    repo = _setup_dispatch_repo(tmp_path)
    gate_dir = tmp_path / "gate5"
    gate_dir.mkdir()
    tid = f"{__import__('datetime').date.today().strftime('%Y%m%d')}-audit-collision"
    audit = gate_dir / "audit.log"
    event = {
        "event": "committee_dispatch",
        "task_id": tid,
        "family": "composer",
        "output_path": "handoffs/pending",
        "output_sha256": "pending",
        "ts": "2099-01-01T00:00:00Z",
    }
    audit.write_text(json.dumps(event) + "\n", encoding="utf-8")
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    proc = subprocess.run(
        [
            "bash",
            str(DISPATCH_SH),
            "--intent",
            "audit-collision",
            "--risk",
            "low",
            "--facts-asked",
            "none-needed:test",
            "--review-role",
            "single-executor:n/a",
            "--template",
            "n/a:test",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 1
    assert "task-id 已在 audit" in proc.stderr
