"""B3 Task 3.1 — sources.lock / roster / 拒收 / 拒 ADVISORY_ONLY（含 BC4 happy-path）。

nodeid:
  test_empty_dir_not_vacuous
  test_lock_version_mismatch_fails
  test_advisory_only_rejected
  test_symlink_outside_rejected
  test_valid_lock_passes
  test_lock_discovery_p0_without_digest_passes
  test_lock_review_missing_digest_fails
  test_lock_missing_mode_defaults_review_strict
  test_lock_unknown_mode_fails
  test_family_prefix_mismatch_fails
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


def _finding_no_digest(fid: str = "GROK-R1-P0-01") -> str:
    """合法斷言+碼證但無來源摘要（discovery 可過、review 應 FAIL）。"""
    return (
        f"## {fid}\n\n"
        f"**斷言**: lock layer assert no digest\n\n"
        f"**碼證**: path:1\n"
    )


def _write_lock(
    session: Path,
    *,
    roster: list[str],
    sources: list[dict],
    version: int = 1,
    closure_state: str = "FROZEN",
    mode: str | None = "review",
) -> Path:
    lock: dict = {
        "version": version,
        "session_id": session.name,
        "expected_roster": roster,
        "sources": sorted(sources, key=lambda e: e["realpath"]),
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": closure_state,
    }
    # mode=None → 故意省略欄位（測缺欄 fail-closed 預設 review）
    if mode is not None:
        lock["mode"] = mode
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


# ---------------------------------------------------------------------------
# digest 適用邊界（A+C+family-binding）
# ---------------------------------------------------------------------------


def test_lock_discovery_p0_without_digest_passes(tmp_path: Path) -> None:
    """FROZEN discovery lock + 合法 P0 無來源摘要 + synth 完整 → exit 0。"""
    session = tmp_path / "session_discovery"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding_no_digest("GROK-R1-P0-01")
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
        mode="discovery",
    )
    result = _run_lock(session)
    assert result.returncode == 0, (
        f"discovery 免 digest 應 PASS; rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_lock_review_missing_digest_fails(tmp_path: Path) -> None:
    """review lock 缺 digest → exit 1（維持強制）。"""
    session = tmp_path / "session_review_digest"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding_no_digest("GROK-R1-P0-01")
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
        mode="review",
    )
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"review 缺 digest 應 FAIL; rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "digest" in combined.lower() or "來源摘要" in combined


def test_lock_missing_mode_defaults_review_strict(tmp_path: Path) -> None:
    """缺 mode 欄 → 當 review 強制 digest（fail-closed，不放寬）。"""
    session = tmp_path / "session_no_mode"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding_no_digest("GROK-R1-P0-01")
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
        mode=None,  # 故意省略
    )
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"缺 mode 應當 review 嚴格; rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "digest" in combined.lower() or "來源摘要" in combined


def test_lock_unknown_mode_fails(tmp_path: Path) -> None:
    """mode=foo → exit 1。"""
    session = tmp_path / "session_bad_mode"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding("GROK-R1-P0-01")
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
        mode="foo",
    )
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"未知 mode 應 FAIL; rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "mode" in combined.lower() or "foo" in combined


def test_lock_empty_mode_fails(tmp_path: Path) -> None:
    """CODEX-R1-P2-01：mode 存在但為空字串 → 未知值 exit 1（非默認 review）。"""
    session = tmp_path / "session_empty_mode"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding("GROK-R1-P0-01")
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
        mode="",  # present-but-empty → 未知值,非缺欄
    )
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"空 mode 應 FAIL(未知值,非默認 review); rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "mode" in combined.lower()


def test_family_prefix_mismatch_fails(tmp_path: Path) -> None:
    """codex 檔含 ## GROK-R1-... → family-binding FAIL exit1（堵冒充）。"""
    session = tmp_path / "session_fam_bind"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    # 冒充：檔名/lock.family=codex，heading 卻用 GROK-
    body = _finding("GROK-R1-P0-01")
    src = sources_dir / "review-codex.md"
    src.write_text(body, encoding="utf-8")
    (session / "synth.md").write_text(body, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex"],
        sources=[
            {
                "realpath": str(src.resolve()),
                "sha256": _sha256_bytes(body.encode()),
                "family": "codex",
            }
        ],
        mode="review",
    )
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"family mismatch 應 FAIL; rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert (
        "family-binding" in combined.lower()
        or "family" in combined.lower()
        or "mismatch" in combined.lower()
    )


def test_write_sources_lock_invalid_mode_exits_nonzero(tmp_path: Path) -> None:
    """write_sources_lock --mode 非法值 → exit≠0。"""
    session = tmp_path / "session_wmode"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding("GROK-R1-P0-01")
    (sources_dir / "review-grok.md").write_text(body, encoding="utf-8")
    env = os.environ.copy()
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    wr = subprocess.run(
        [
            "bash",
            str(WRITE_LOCK_SH),
            "--session",
            str(session),
            "--roster",
            "grok",
            "--mode",
            "staging",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert wr.returncode != 0, (
        f"非法 --mode 應 exit≠0; rc={wr.returncode} {wr.stdout!r} {wr.stderr!r}"
    )


def test_lock_discovery_dropped_id_still_fails(tmp_path: Path) -> None:
    """discovery 下 dropped-ID 仍 FAIL（不弱化 ID-completeness 核心）。"""
    session = tmp_path / "session_disc_drop"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    body = _finding_no_digest("GROK-R1-P0-01")
    src = sources_dir / "review-grok.md"
    src.write_text(body, encoding="utf-8")
    # synth 故意掉 ID
    (session / "synth.md").write_text(
        "## GROK-R1-P2-99\n\n**斷言**: other\n\n**碼證**: x\n",
        encoding="utf-8",
    )
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
        mode="discovery",
    )
    result = _run_lock(session)
    assert result.returncode == 1, (
        f"discovery 掉項仍應 FAIL; rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
