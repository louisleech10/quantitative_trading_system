"""VERIFY_GATE 過嚴回歸修補 (O1–O2) — staged 增量掃描與 REF 檔案路徑。"""
from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "venv" / "bin" / "python"
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
INSTALL_HOOKS = REPO_ROOT / "scripts" / "install_verify_hooks.sh"


def _run_checker(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    argv = [str(PYTHON), str(CLAIM_CHECK), *args]
    return subprocess.run(
        argv,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_fixture(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _setup_temp_git_repo(tmp_path: Path) -> Path:
    """建立含 symlink scripts 的臨時 git repo。"""
    repo = tmp_path / "mini_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "o@test.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "O Test"], cwd=repo, check=True)

    scripts = repo / "scripts"
    scripts.mkdir()
    shutil.copytree(REPO_ROOT / "scripts" / "git_hooks", scripts / "git_hooks")
    for hook in (scripts / "git_hooks").iterdir():
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for name in (
        "verification_claim_check.py",
        "install_verify_hooks.sh",
        "verify_hooks_health.sh",
        "verify_pretooluse.sh",
    ):
        (scripts / name).symlink_to(REPO_ROOT / "scripts" / name)
    (repo / "venv").symlink_to(REPO_ROOT / "venv", target_is_directory=True)

    (repo / "README.md").write_text("# temp\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: init"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


# --- O1: staged 只掃新增行 ---


def test_o1_staged_unchanged_history_line_not_rescanned(tmp_path: Path) -> None:
    """O1-①：既有未改無 backing 行 + 本次改他處 → commit 過。"""
    repo = _setup_temp_git_repo(tmp_path)
    handoff = repo / "HANDOFF.md"
    handoff.write_text("## 正在做\n\n- align 已驗真紅\n", encoding="utf-8")
    subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: seed handoff"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)

    handoff.write_text("## 正在做\n\n- align 已驗真紅\n\n- innocuous note\n", encoding="utf-8")
    subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
    proc = subprocess.run(
        ["git", "commit", "-m", "docs: add note"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_o1_staged_new_unbacked_operational_blocked(tmp_path: Path) -> None:
    """O1-②：本次新增無 backing operational 行 → 仍擋。"""
    repo = _setup_temp_git_repo(tmp_path)
    subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
    handoff = repo / "HANDOFF.md"
    handoff.write_text("## 正在做\n\n- clean note\n", encoding="utf-8")
    subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: init handoff"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    handoff.write_text("## 正在做\n\n- clean note\n\n- align 已驗真紅\n", encoding="utf-8")
    subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
    proc = subprocess.run(
        ["git", "commit", "-m", "docs: bad claim"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_o1_staged_partial_stage_fake_claim_still_blocked(tmp_path: Path) -> None:
    """O1-② partial-stage：staged 假 claim + working tree 改回 → 仍擋（B3-1 不回歸）。"""
    repo = _setup_temp_git_repo(tmp_path)
    subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
    handoff = repo / "HANDOFF.md"
    handoff.write_text("## 正在做\n\n- align 已驗真紅\n", encoding="utf-8")
    subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
    handoff.write_text("## 正在做\n\n- clean note\n", encoding="utf-8")
    proc = subprocess.run(
        ["git", "commit", "-m", "docs: partial stage"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


# --- O2: REF 檔案路徑 ---


def test_o2_ref_existing_closure_file_allowed(tmp_path: Path) -> None:
    """O2-①：REF:handoffs/<存在且含 CLOSED 的檔> → 放行。"""
    _write_fixture(
        tmp_path / "handoffs" / "20990101-O2-CLOSURE.md",
        "# closure\n\nVERDICT: R1-R7 CLOSED\n",
    )
    _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\nCodex 閉合 R1-R7 CLOSED REF:handoffs/20990101-O2-CLOSURE.md\n",
    )
    proc = _run_checker(
        "--files",
        "HANDOFF.md",
        "handoffs/20990101-O2-CLOSURE.md",
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr


def test_o2_ref_missing_file_blocked(tmp_path: Path) -> None:
    """O2-②：REF:handoffs/<不存在> → 擋。"""
    _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\nCodex 閉合 REF:handoffs/20990101-NO-SUCH-FILE.md\n",
    )
    proc = _run_checker("--files", "HANDOFF.md", cwd=tmp_path)
    assert proc.returncode == 1
    assert "不存在" in proc.stderr or "backing" in proc.stderr


def test_o2_ref_empty_file_no_backing_blocked(tmp_path: Path) -> None:
    """O2-③：REF:<存在但無 backing> → 擋。"""
    _write_fixture(tmp_path / "handoffs" / "20990101-O2-EMPTY.md", "# empty\n\n")
    _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\n進度見 REF:handoffs/20990101-O2-EMPTY.md\n",
    )
    proc = _run_checker(
        "--files",
        "HANDOFF.md",
        "handoffs/20990101-O2-EMPTY.md",
        cwd=tmp_path,
    )
    assert proc.returncode == 1
    assert "backing" in proc.stderr or "不存在" in proc.stderr


def test_o2_r6_fake_attribution_without_ref_still_blocked(tmp_path: Path) -> None:
    """O2-④：R6 假歸屬（無 REF）仍擋。"""
    fixture = _write_fixture(
        tmp_path / "HANDOFF.md",
        "## 現役任務\n\nCodex 檔案寫道「align 已驗真紅」\n",
    )
    proc = _run_checker("--files", str(fixture))
    assert proc.returncode == 1
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr
