"""INSTREV Phase B1 — check_agent_contract_sync.sh 兩層 token + 反向檢查。"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC_SCRIPT = REPO_ROOT / "scripts" / "check_agent_contract_sync.sh"

SOURCE_FILES = (
    "AGENTS.md",
    ".cursorrules",
    "CLAUDE.md",
    "docs/MULTI_AGENT_ORCHESTRATION.md",
)


def _setup_sync_repo(tmp_path: Path) -> Path:
    """複製四源檔到臨時 git repo，供隔離測試。"""
    repo = tmp_path / "sync_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "docs").mkdir()
    scripts = repo / "scripts"
    scripts.mkdir()
    shutil.copy2(SYNC_SCRIPT, scripts / "check_agent_contract_sync.sh")
    for rel in SOURCE_FILES:
        src = REPO_ROOT / rel
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return repo


def _run_sync(repo: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    return subprocess.run(
        ["bash", "scripts/check_agent_contract_sync.sh"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def test_sync_check_passes_on_unmodified_copies(tmp_path: Path) -> None:
    """未動四源副本 → exit 0 且 stdout 含 ✅。"""
    repo = _setup_sync_repo(tmp_path)
    proc = _run_sync(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "✅" in proc.stdout


def test_sync_fails_when_reconcile_stamp_missing_from_agents(tmp_path: Path) -> None:
    """刪 AGENTS.md 的 RECONCILE-STAMP → exit 1 且訊息含該 token。"""
    repo = _setup_sync_repo(tmp_path)
    agents = repo / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8").replace("RECONCILE-STAMP", "REMOVED-STAMP"),
        encoding="utf-8",
    )
    proc = _run_sync(repo)
    assert proc.returncode == 1
    assert "RECONCILE-STAMP" in proc.stdout


def test_sync_fails_when_executor_hardcoded_in_claude(tmp_path: Path) -> None:
    """CLAUDE.md 植入 Composer 實作 → 反向檢查 exit 1。"""
    repo = _setup_sync_repo(tmp_path)
    claude = repo / "CLAUDE.md"
    claude.write_text(claude.read_text(encoding="utf-8") + "\nComposer 實作\n", encoding="utf-8")
    proc = _run_sync(repo)
    assert proc.returncode == 1
    assert "寫死執行端" in proc.stdout


def test_sync_fails_when_duplicate_orch_anchor(tmp_path: Path) -> None:
    """ORCH 複製第二條錨點行 → 反向檢查 exit 1。"""
    repo = _setup_sync_repo(tmp_path)
    orch = repo / "docs/MULTI_AGENT_ORCHESTRATION.md"
    anchor = '**現行分工(duplicate):測試。**'
    orch.write_text(orch.read_text(encoding="utf-8") + f"\n{anchor}\n", encoding="utf-8")
    proc = _run_sync(repo)
    assert proc.returncode == 1
    assert "錨點行計數" in proc.stdout


def test_sync_fullwidth_paren_anchor_counts_as_one(tmp_path: Path) -> None:
    """全形括號錨點變體仍計數 == 1（替換半形為全形）。"""
    repo = _setup_sync_repo(tmp_path)
    orch = repo / "docs/MULTI_AGENT_ORCHESTRATION.md"
    text = orch.read_text(encoding="utf-8")
    text = text.replace("現行分工(2026", "現行分工（2026", 1)
    orch.write_text(text, encoding="utf-8")
    proc = _run_sync(repo)
    assert proc.returncode == 0, proc.stdout


def test_sync_fails_when_verify_only_in_planner_layer(tmp_path: Path) -> None:
    """VERIFY 只在 CLAUDE 不在合約 → CONTRACT_REQUIRED FAIL。"""
    repo = _setup_sync_repo(tmp_path)
    for f in ("AGENTS.md", ".cursorrules"):
        p = repo / f
        p.write_text(p.read_text(encoding="utf-8").replace("VERIFY", "CHECK"), encoding="utf-8")
    proc = _run_sync(repo)
    assert proc.returncode == 1
    assert "VERIFY" in proc.stdout
