"""B3 Task 3.1 — sources.lock / roster / 拒收 / 拒 ADVISORY_ONLY（含 BC4 happy-path）。

nodeid:
  test_empty_dir_not_vacuous
  test_lock_version_mismatch_fails
  test_advisory_only_rejected
  test_symlink_outside_rejected
  test_valid_lock_passes
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"
WRITE_LOCK_SH = REPO_ROOT / "scripts" / "write_sources_lock.sh"


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _finding(fid: str = "GROK-R1-P0-01") -> str:
    import hashlib

    d = hashlib.sha256(fid.encode()).hexdigest()[:12]
    return (
        f"## {fid}\n\n"
        f"**斷言**: lock layer assert\n\n"
        f"**碼證**: path:1\n\n"
        f"**來源摘要**: sources/review-grok.md#{d}\n"
    )


def _write_lock(
    session: Path,
    *,
    roster: list[str],
    sources: list[dict],
    version: int = 1,
    closure_state: str = "FROZEN",
) -> Path:
    lock = {
        "version": version,
        "session_id": session.name,
        "expected_roster": roster,
        "sources": sorted(sources, key=lambda e: e["realpath"]),
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": closure_state,
    }
    path = session / "sources.lock"
    path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _run_lock(
    session: Path,
    *,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COMPLETENESS_ADVISORY_ONLY", None)
    env.pop("COMPLETENESS_ALLOW_ARGV_SOURCES", None)
    if env_extra:
        env.update(env_extra)
    lock = session / "sources.lock"
    return subprocess.run(
        ["bash", str(COMPLETENESS_SH), "--lock", str(lock)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_empty_dir_not_vacuous(tmp_path: Path) -> None:
    """空 sources/ + lock.sources=[] + roster 非空 → exit 1（非 vacuous PASS）。"""
    session = tmp_path / "session"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    (session / "synth.md").write_text(_finding(), encoding="utf-8")
    _write_lock(session, roster=["codex", "composer", "grok"], sources=[])
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"空目錄應 fail-closed; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "FAIL" in combined or "缺" in combined or "空" in combined


def test_lock_version_mismatch_fails(tmp_path: Path) -> None:
    """sources.lock version≠1 → 拒發 exit 1。"""
    session = tmp_path / "session"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding()
    src = sources_dir / "review-grok.md"
    src.write_text(body, encoding="utf-8")
    (session / "synth.md").write_text(body, encoding="utf-8")
    _write_lock(
        session,
        roster=["grok"],
        sources=[
            {
                "realpath": str(src.resolve()),
                "sha256": _sha256_bytes(body.encode()),
                "family": "grok",
            }
        ],
        version=99,
    )
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"version mismatch 應 FAIL; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "version" in combined.lower()


def test_advisory_only_rejected(tmp_path: Path) -> None:
    """正式路徑設 COMPLETENESS_ADVISORY_ONLY → 主動拒 exit 1。"""
    session = tmp_path / "session"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding()
    src = sources_dir / "review-grok.md"
    src.write_text(body, encoding="utf-8")
    (session / "synth.md").write_text(body, encoding="utf-8")
    _write_lock(
        session,
        roster=["grok"],
        sources=[
            {
                "realpath": str(src.resolve()),
                "sha256": _sha256_bytes(body.encode()),
                "family": "grok",
            }
        ],
    )
    result = _run_lock(session, env_extra={"COMPLETENESS_ADVISORY_ONLY": "1"})
    assert result.returncode == 1, (
        f"ADVISORY_ONLY 應被拒; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "advisory" in combined.lower()


def test_symlink_outside_rejected(tmp_path: Path) -> None:
    """outside-link.md symlink 指到 session sources/ 外 → 拒收 exit 1。"""
    session = tmp_path / "session"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    outside = tmp_path / "outside-payload.md"
    body = _finding("CODEX-R1-P0-01")
    outside.write_text(body, encoding="utf-8")

    link = sources_dir / "outside-link-codex.md"
    link.symlink_to(outside.resolve())

    (session / "synth.md").write_text(body, encoding="utf-8")
    # lock 記 symlink 路徑；realpath 解析後出 sources/
    _write_lock(
        session,
        roster=["codex"],
        sources=[
            {
                "realpath": str(link),  # 可為 link 路徑；腳本 realpath 後應出界
                "sha256": _sha256_bytes(body.encode()),
                "family": "codex",
            }
        ],
    )
    result = _run_lock(session)
    assert result.returncode != 0, (
        f"symlink 出目錄應拒收; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert (
        "symlink" in combined.lower()
        or "realpath" in combined.lower()
        or "出" in combined
        or "root" in combined.lower()
        or "FAIL" in combined
    )


def test_valid_lock_passes(tmp_path: Path) -> None:
    """BC4：write_sources_lock 產 lock → completeness --lock PASS（路徑 realpath 統一）。"""
    session = tmp_path / "session_ok"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding("GROK-R1-P0-01")
    (sources_dir / "review-grok.md").write_text(body, encoding="utf-8")
    (session / "synth.md").write_text(body, encoding="utf-8")

    env = os.environ.copy()
    env.pop("COMPLETENESS_ADVISORY_ONLY", None)
    env.pop("COMPLETENESS_ALLOW_ARGV_SOURCES", None)
    env.pop("GOVERNANCE_TEST_HARNESS", None)

    wr = subprocess.run(
        [
            "bash",
            str(WRITE_LOCK_SH),
            "--session",
            str(session),
            "--roster",
            "grok",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert wr.returncode == 0, (
        f"write_sources_lock 應成功; stdout={wr.stdout!r} stderr={wr.stderr!r}"
    )
    assert (session / "sources.lock").is_file()

    result = _run_lock(session)
    assert result.returncode == 0, (
        f"合法 lock 應 completeness PASS; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def _valid_session(tmp_path: Path) -> Path:
    """建一個 sources/ 內含單一合法 finding 檔 + FROZEN lock 的 session。"""
    session = tmp_path / "reconcile" / "sess1"
    sources = session / "sources"
    sources.mkdir(parents=True)
    body = _finding("GROK-R1-P0-01")
    f = sources / "review-grok.md"
    f.write_text(body, encoding="utf-8")
    # 綜合檔(synth)須含來源全部 ID → 完整 → PASS
    (session / "synth.md").write_text(body, encoding="utf-8")
    real = str(Path(os.path.realpath(str(f))))
    _write_lock(
        session,
        roster=["grok"],
        sources=[{"realpath": real, "sha256": _sha256_bytes(body.encode()), "family": "grok"}],
    )
    return session


def test_id_pattern_override_rejected_without_harness(tmp_path: Path) -> None:
    """CODEX-B3C-P0-03：ID_PATTERN/ALLOW_ID_PATTERN_OVERRIDE 無 GOVERNANCE_TEST_HARNESS → fail-closed。"""
    session = _valid_session(tmp_path)
    # 正常(無 override)應 PASS
    ok = _run_lock(session)
    assert ok.returncode == 0, f"baseline 合法 lock 應 PASS; {ok.stdout!r} {ok.stderr!r}"
    # 設 ID_PATTERN 過濾 finding 但不設 harness → 應 exit1
    bad = _run_lock(
        session,
        env_extra={"ID_PATTERN": "GROK-R1-P0-01", "ALLOW_ID_PATTERN_OVERRIDE": "1"},
    )
    assert bad.returncode != 0, (
        f"ID_PATTERN 覆寫無 harness 應 fail-closed; rc={bad.returncode} {bad.stdout!r} {bad.stderr!r}"
    )
    combined = (bad.stdout or "") + (bad.stderr or "")
    assert "GOVERNANCE_TEST_HARNESS" in combined or "ID_PATTERN" in combined


def test_force_frozen_lock_rejected_without_harness(tmp_path: Path) -> None:
    """CODEX-B3C-P2-01：write_sources_lock --force 覆寫 FROZEN lock 無 harness → fail-closed。"""
    session = _valid_session(tmp_path)
    env = os.environ.copy()
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    wr = subprocess.run(
        ["bash", str(WRITE_LOCK_SH), "--session", str(session), "--roster", "grok", "--force"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert wr.returncode != 0, (
        f"--force 覆寫 FROZEN 無 harness 應 fail-closed; rc={wr.returncode} {wr.stdout!r} {wr.stderr!r}"
    )
    combined = (wr.stdout or "") + (wr.stderr or "")
    assert "force" in combined.lower() or "GOVERNANCE_TEST_HARNESS" in combined
