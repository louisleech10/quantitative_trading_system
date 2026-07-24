"""INSTREV Phase B3 — pre-commit index-only 尾隨空白 auto-fix + backing 提示。"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from tests.governance._pyenv import link_python_env  # CI 無 venv 相容
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
from tests.governance._pyenv import PYTHON  # CI 無 venv → fallback sys.executable
PRE_COMMIT = REPO_ROOT / "scripts" / "git_hooks" / "pre-commit"
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
INSTALL_HOOKS = REPO_ROOT / "scripts" / "install_verify_hooks.sh"

RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"


@pytest.fixture(autouse=True)
def isolated_b3_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipts_dir = tmp_path / "run_receipts"
    audit_log = tmp_path / "gate" / "verify_audit.log"
    pending_ledger = tmp_path / "pending_verifications.jsonl"
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(receipts_dir))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(audit_log))
    monkeypatch.setenv(PENDING_LEDGER_ENV, str(pending_ledger))


def _setup_temp_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "mini_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "b3@test.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "B3 Test"], cwd=repo, check=True)

    scripts = repo / "scripts"
    scripts.mkdir()
    shutil.copytree(REPO_ROOT / "scripts" / "git_hooks", scripts / "git_hooks")
    for hook in (scripts / "git_hooks").iterdir():
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for name in ("verification_claim_check.py", "install_verify_hooks.sh"):
        (scripts / name).symlink_to(REPO_ROOT / "scripts" / name)
    link_python_env(repo)

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


def _run_precommit(repo: Path) -> subprocess.CompletedProcess[str]:
    hook = repo / "scripts" / "git_hooks" / "pre-commit"
    return subprocess.run(
        ["bash", str(hook)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )


def _staged_blob(repo: Path, rel: str) -> str:
    proc = subprocess.run(
        ["git", "show", f":{rel}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _staged_blob_bytes(repo: Path, rel: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f":{rel}"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    return proc.stdout


def _staged_mode(repo: Path, rel: str) -> str:
    proc = subprocess.run(
        ["git", "ls-files", "-s", "--", rel],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.split()[0]


def test_precommit_strips_trailing_ws_index_only(tmp_path: Path) -> None:
    """staged md 含行尾空白 → index blob 去尾空白、其餘位元組不變。"""
    repo = _setup_temp_git_repo(tmp_path)
    handoff = repo / "HANDOFF.md"
    content = "## 正在做\n\n- note with trailing   \n"
    expected = "## 正在做\n\n- note with trailing\n"
    handoff.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
    proc = _run_precommit(repo)
    assert proc.returncode == 0, proc.stderr
    staged = _staged_blob(repo, "HANDOFF.md")
    assert staged == expected
    assert not any(line.endswith(" ") or line.endswith("\t") for line in staged.splitlines())


def test_precommit_partial_stage_worktree_untouched(tmp_path: Path) -> None:
    """partial-stage：index 只反映 staged 版(去尾空白)，工作樹改動未納入。"""
    repo = _setup_temp_git_repo(tmp_path)
    handoff = repo / "HANDOFF.md"
    staged_text = "## 正在做\n\n- align 已驗真紅   \n"
    handoff.write_text(staged_text, encoding="utf-8")
    subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
    handoff.write_text("## 正在做\n\n- clean note\n", encoding="utf-8")
    proc = _run_precommit(repo)
    assert proc.returncode != 0
    staged = _staged_blob(repo, "HANDOFF.md")
    assert "已驗真紅" in staged
    assert staged.endswith("已驗真紅\n")
    assert handoff.read_text(encoding="utf-8") == "## 正在做\n\n- clean note\n"


def test_precommit_preserves_fenced_and_hard_break(tmp_path: Path) -> None:
    """fenced 內尾隨空白 + 兩空白 hard-break → 皆保留。"""
    repo = _setup_temp_git_repo(tmp_path)
    doc = repo / "docs" / "note.md"
    doc.parent.mkdir()
    content = (
        "prose line   \n"
        "hard break  \n"
        "next\n"
        "```py\n"
        "x = 1   \n"
        "```\n"
    )
    doc.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "docs/note.md"], cwd=repo, check=True, capture_output=True)
    proc = _run_precommit(repo)
    assert proc.returncode == 0, proc.stderr
    staged = _staged_blob(repo, "docs/note.md")
    assert "prose line\n" in staged
    assert "hard break  \n" in staged
    assert "x = 1   \n" in staged


def test_precommit_skips_non_utf8_staged_md_index_unchanged(tmp_path: Path) -> None:
    """非 UTF-8 staged md → auto-fix skip，index blob byte-for-byte 不變。"""
    repo = _setup_temp_git_repo(tmp_path)
    bad = repo / "docs" / "bad.md"
    bad.parent.mkdir()
    original = bytes.fromhex("616263ff2020200a")
    bad.write_bytes(original)
    subprocess.run(["git", "add", "docs/bad.md"], cwd=repo, check=True, capture_output=True)
    before = _staged_blob_bytes(repo, "docs/bad.md")
    proc = _run_precommit(repo)
    assert proc.returncode != 0
    after = _staged_blob_bytes(repo, "docs/bad.md")
    assert after == before == original


def test_precommit_preserves_executable_mode_on_autofix(tmp_path: Path) -> None:
    """executable staged md auto-fix 後 mode 仍為 100755。"""
    repo = _setup_temp_git_repo(tmp_path)
    doc = repo / "docs" / "run.md"
    doc.parent.mkdir()
    doc.write_text("## run\n\nline with trailing   \n", encoding="utf-8")
    doc.chmod(doc.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    subprocess.run(["git", "add", "docs/run.md"], cwd=repo, check=True, capture_output=True)
    assert _staged_mode(repo, "docs/run.md") == "100755"
    proc = _run_precommit(repo)
    assert proc.returncode == 0, proc.stderr
    assert _staged_mode(repo, "docs/run.md") == "100755"
    staged = _staged_blob(repo, "docs/run.md")
    assert staged.endswith("line with trailing\n")


def test_staged_non_utf8_md_checker_exit_2_graceful(tmp_path: Path) -> None:
    """非 UTF-8 staged md → checker --staged exit 2 + 清楚訊息，非 UnicodeDecodeError traceback。"""
    repo = _setup_temp_git_repo(tmp_path)
    bad = repo / "docs" / "bad.md"
    bad.parent.mkdir()
    original = bytes.fromhex("616263ff2020200a")
    bad.write_bytes(original)
    subprocess.run(["git", "add", "docs/bad.md"], cwd=repo, check=True, capture_output=True)
    proc = subprocess.run(
        [str(PYTHON), str(CLAIM_CHECK), "--staged"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    assert proc.returncode == 2, proc.stderr
    assert "cannot read docs/bad.md" in proc.stderr
    assert "not valid UTF-8 (staged blob)" in proc.stderr
    assert "UnicodeDecodeError" not in proc.stderr
    assert "Traceback" not in proc.stderr


def test_backing_violation_appends_verify_exempt_hint(tmp_path: Path) -> None:
    """缺 backing operational claim → exit 1、原訊息仍在、stderr 含 VERIFY-EXEMPT 提示。"""
    repo = _setup_temp_git_repo(tmp_path)
    handoff = repo / "HANDOFF.md"
    handoff.write_text("## 正在做\n\n- align 已驗真紅\n", encoding="utf-8")
    proc = subprocess.run(
        [str(PYTHON), str(CLAIM_CHECK), "--files", str(handoff)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    assert proc.returncode == 1
    assert "operational claim 缺少 VERIFY/REF/SIGNOFF backing" in proc.stderr
    assert "VERIFY-EXEMPT" in proc.stderr
    assert proc.stderr.count("operational claim 缺少") == 1
