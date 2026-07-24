"""B4 Task 5.1 — DEGRADED_PENDING 狀態機（exit 3，非字串灰態）。

nodeid:
  test_absent_without_degrade_event_fails
  test_min_families_one_hardstop
  test_p0_waiver_rejected
  test_legal_degrade_exit3
  test_degraded_cannot_final_stamp
  test_degrade_with_extra_family_fails
  test_degrade_with_dup_family_fails
  test_illegal_expiry_fails
  test_expired_expiry_fails
  test_selfcheck_legal_degrade_not_rc0
  test_roster_duplicate_fails
  test_roster_unknown_family_fails
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
SPEC = REPO_ROOT / "docs" / "CONVERGENCE_METHOD_SPEC.md"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finding(fid: str) -> str:
    d = hashlib.sha256(fid.encode()).hexdigest()[:12]
    return (
        f"## {fid}\n\n"
        f"**斷言**: degrade assert\n\n"
        f"**碼證**: path:1\n\n"
        f"**來源摘要**: sources/review.md#{d}\n"
    )


def _write_lock(
    session: Path,
    *,
    roster: list[str],
    sources: list[dict],
) -> Path:
    lock = {
        "version": 1,
        "session_id": session.name,
        "expected_roster": roster,
        "sources": sorted(sources, key=lambda e: e["realpath"]),
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
    }
    path = session / "sources.lock"
    path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _write_degrade(
    session: Path,
    *,
    absent_family: str,
    reason: str = "timeout during review",
    round_n: int = 1,
    expiry: str = "2099-01-01T00:00:00Z",
    extra: dict | None = None,
) -> Path:
    body = {
        "absent_family": absent_family,
        "reason": reason,
        "approver": "committee-chair",
        "expiry": expiry,
        "remediation_owner": "ops",
        "round": round_n,
    }
    if extra:
        body.update(extra)
    path = session / "degrade.json"
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _two_present_one_absent(
    tmp_path: Path,
    *,
    name: str = "sess_deg",
    include_degrade_heading: bool = False,
    write_degrade_json: bool = False,
    degrade_reason: str = "timeout during review",
    round_n: int = 1,
    expiry: str = "2099-01-01T00:00:00Z",
) -> Path:
    """roster=codex,composer,grok；只放 codex+composer 來源；grok 缺席。"""
    session = tmp_path / name
    sources = session / "sources"
    sources.mkdir(parents=True)

    b_codex = _finding("CODEX-R1-P2-01")
    b_comp = _finding("COMPOSER-R1-P2-01")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")

    synth_parts = [b_codex, b_comp]
    if include_degrade_heading:
        synth_parts.append(
            "## DEGRADE-GROK-01\n\n"
            "absent family grok; remediation pending.\n"
        )
    (session / "synth.md").write_text("\n".join(synth_parts), encoding="utf-8")

    _write_lock(
        session,
        roster=["codex", "composer", "grok"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )
    if write_degrade_json:
        _write_degrade(
            session,
            absent_family="grok",
            reason=degrade_reason,
            round_n=round_n,
            expiry=expiry,
        )
    return session


def _run_completeness(
    session: Path,
    *extra: str,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COMPLETENESS_ADVISORY_ONLY", None)
    env.pop("COMPLETENESS_ALLOW_ARGV_SOURCES", None)
    if env_extra:
        env.update(env_extra)
    lock = session / "sources.lock"
    return subprocess.run(
        ["bash", str(COMPLETENESS_SH), "--lock", str(lock), *extra],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _stdout_nonempty_lines(stdout: str | None) -> list[str]:
    """行級：去掉空白行後的 stdout 行列表。"""
    return [ln.strip() for ln in (stdout or "").splitlines() if ln.strip()]


def test_absent_without_degrade_event_fails(tmp_path: Path) -> None:
    """grok 缺席 ∧ 無 ## DEGRADE-GROK-01 / degrade.json → exit 1。"""
    session = _two_present_one_absent(
        tmp_path,
        include_degrade_heading=False,
        write_degrade_json=False,
    )
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"無 degrade 事件應 FAIL; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "DEGRADED_PENDING" not in result.stdout
    assert "缺席" in combined or "DEGRADE" in combined or "FAIL" in combined


def test_min_families_one_hardstop(tmp_path: Path) -> None:
    """僅 1 家 present → 即使有 DEGRADE 事件仍硬停 exit 1。"""
    session = tmp_path / "sess_min1"
    sources = session / "sources"
    sources.mkdir(parents=True)
    body = _finding("CODEX-R1-P2-01")
    f = sources / "review-codex.md"
    f.write_text(body, encoding="utf-8")
    synth = body + "\n## DEGRADE-GROK-01\n\nabsent.\n"
    (session / "synth.md").write_text(synth, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex", "grok"],
        sources=[
            {
                "realpath": str(f.resolve()),
                "sha256": _sha256_bytes(body.encode()),
                "family": "codex",
            }
        ],
    )
    _write_degrade(session, absent_family="grok")
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"min_families=1 應硬停; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "min_families" in combined or "硬停" in combined
    assert result.returncode != 3
    assert "DEGRADED_PENDING" not in (result.stdout or "")


def test_p0_waiver_rejected(tmp_path: Path) -> None:
    """degrade.json 含 waived:/skip 或 P0 waiver 字樣 → 拒 exit 1。"""
    session = _two_present_one_absent(
        tmp_path,
        name="sess_p0waive",
        include_degrade_heading=True,
        write_degrade_json=True,
        degrade_reason="waived:P0-finding due to timeout",
    )
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"P0 waiver 應被拒; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert (
        "waiver" in combined.lower()
        or "waived" in combined.lower()
        or "P0" in combined
        or "禁" in combined
    ), f"須提示 waiver 拒絕: {combined!r}"
    assert "DEGRADED_PENDING" not in (result.stdout or "")

    # skip 字串同樣拒
    session2 = _two_present_one_absent(
        tmp_path,
        name="sess_skip",
        include_degrade_heading=True,
        write_degrade_json=True,
        degrade_reason="skip absent family for speed",
    )
    r2 = _run_completeness(session2)
    assert r2.returncode == 1, f"skip 字串應被拒; rc={r2.returncode} {r2.stderr!r}"


def test_legal_degrade_exit3(tmp_path: Path) -> None:
    """2 家 present + DEGRADE heading + 合法 degrade.json → exit 3 + stdout 唯一 DEGRADED_PENDING。

    BF3: 行級/exact 驗 — stdout 非空行必須恰好 ['DEGRADED_PENDING']，
    不得與 COMPLETENESS PASS 混。
    """
    session = _two_present_one_absent(
        tmp_path,
        name="sess_legal",
        include_degrade_heading=True,
        write_degrade_json=True,
        degrade_reason="reviewer timeout; remediation scheduled",
        round_n=1,
    )
    result = _run_completeness(session)
    assert result.returncode == 3, (
        f"合法降級應 exit 3; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    # BF3: 行級 exact — 唯一可辨 token
    lines = _stdout_nonempty_lines(result.stdout)
    assert lines == ["DEGRADED_PENDING"], (
        f"stdout 非空行須恰好 ['DEGRADED_PENDING']，得 {lines!r} full={result.stdout!r}"
    )
    assert "COMPLETENESS PASS" not in (result.stdout or ""), (
        f"stdout 不得混 COMPLETENESS PASS: {result.stdout!r}"
    )
    # 禁 RC=0 灰態
    assert result.returncode != 0

    # round>=2 → 仍 exit 3 但標記 ESCALATE（stderr）
    session_e = _two_present_one_absent(
        tmp_path,
        name="sess_escalate",
        include_degrade_heading=True,
        write_degrade_json=True,
        round_n=2,
    )
    r_e = _run_completeness(session_e)
    assert r_e.returncode == 3
    assert _stdout_nonempty_lines(r_e.stdout) == ["DEGRADED_PENDING"]
    combined_e = (r_e.stdout or "") + (r_e.stderr or "")
    assert "ESCALATE" in combined_e or "升級" in combined_e


def test_degrade_with_extra_family_fails(tmp_path: Path) -> None:
    """BF2: 缺 grok + roster 外 extra claude → exit1（非 rc3）。"""
    session = tmp_path / "sess_extra_fam"
    sources = session / "sources"
    sources.mkdir(parents=True)

    b_codex = _finding("CODEX-R1-P2-01")
    b_comp = _finding("COMPOSER-R1-P2-01")
    b_claude = _finding("CLAUDE-R1-P2-01")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_claude = sources / "review-claude.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")
    f_claude.write_text(b_claude, encoding="utf-8")

    synth = (
        b_codex
        + "\n"
        + b_comp
        + "\n"
        + b_claude
        + "\n## DEGRADE-GROK-01\n\nabsent grok.\n"
    )
    (session / "synth.md").write_text(synth, encoding="utf-8")
    # roster 無 claude，但 sources 含 claude（EXTRA_FAM）
    _write_lock(
        session,
        roster=["codex", "composer", "grok"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
            {
                "realpath": str(f_claude.resolve()),
                "sha256": _sha256_bytes(b_claude.encode()),
                "family": "claude",
            },
        ],
    )
    _write_degrade(session, absent_family="grok")
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"extra family 即使有 DEGRADE 仍 exit1; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 3
    combined = (result.stdout or "") + (result.stderr or "")
    assert "EXTRA" in combined or "roster 外" in combined or "unknown" in combined
    assert "DEGRADED_PENDING" not in (result.stdout or "")


def test_degrade_with_dup_family_fails(tmp_path: Path) -> None:
    """BF2: 缺 grok + 同家族 dup codex → exit1（非 rc3）。"""
    session = tmp_path / "sess_dup_fam"
    sources = session / "sources"
    sources.mkdir(parents=True)

    b_codex = _finding("CODEX-R1-P2-01")
    b_codex2 = _finding("CODEX-R1-P2-02")
    b_comp = _finding("COMPOSER-R1-P2-01")
    f_codex = sources / "review-codex.md"
    f_codex2 = sources / "review2-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_codex2.write_text(b_codex2, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")

    synth = (
        b_codex
        + "\n"
        + b_codex2
        + "\n"
        + b_comp
        + "\n## DEGRADE-GROK-01\n\nabsent grok.\n"
    )
    (session / "synth.md").write_text(synth, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex", "composer", "grok"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_codex2.resolve()),
                "sha256": _sha256_bytes(b_codex2.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )
    _write_degrade(session, absent_family="grok")
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"dup family 即使有 DEGRADE 仍 exit1; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 3
    combined = (result.stdout or "") + (result.stderr or "")
    assert "多來源" in combined or "MULTI" in combined or "混入" in combined
    assert "DEGRADED_PENDING" not in (result.stdout or "")


def test_illegal_expiry_fails(tmp_path: Path) -> None:
    """BF4: 非法 ISO8601 expiry → exit1（不可建 DEGRADED_PENDING）。"""
    session = _two_present_one_absent(
        tmp_path,
        name="sess_bad_exp",
        include_degrade_heading=True,
        write_degrade_json=True,
        expiry="2026-99-99T99:99:99Z",
    )
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"非法 expiry 應 exit1; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 3
    assert "DEGRADED_PENDING" not in (result.stdout or "")
    combined = (result.stdout or "") + (result.stderr or "")
    assert "expiry" in combined.lower() or "非法" in combined or "FAIL" in combined


def test_expired_expiry_fails(tmp_path: Path) -> None:
    """BF4: expiry < now → exit1（過期降級不可建 DEGRADED_PENDING）。"""
    session = _two_present_one_absent(
        tmp_path,
        name="sess_old_exp",
        include_degrade_heading=True,
        write_degrade_json=True,
        expiry="2000-01-01T00:00:00Z",
    )
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"過期 expiry 應 exit1; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 3
    assert "DEGRADED_PENDING" not in (result.stdout or "")
    combined = (result.stdout or "") + (result.stderr or "")
    assert (
        "EXPIRED" in combined
        or "expiry" in combined.lower()
        or "非法" in combined
        or "FAIL" in combined
    )


def test_selfcheck_legal_degrade_not_rc0(tmp_path: Path) -> None:
    """BF5: legal degrade fixture --self-check → 反映 DEGRADED_PENDING（非 rc0 無 token）。"""
    session = _two_present_one_absent(
        tmp_path,
        name="sess_sc_deg",
        include_degrade_heading=True,
        write_degrade_json=True,
        degrade_reason="reviewer timeout; self-check must surface",
    )
    result = _run_completeness(session, "--self-check")
    assert result.returncode == 3, (
        f"self-check 合法降級應 exit3; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 0
    lines = _stdout_nonempty_lines(result.stdout)
    assert "DEGRADED_PENDING" in lines, (
        f"self-check 須標 DEGRADED_PENDING: lines={lines!r} stdout={result.stdout!r}"
    )
    # 不得以 ADVISORY_MISSING / 無 token 的 rc0 掩蓋
    assert "ADVISORY_MISSING" not in (result.stdout or "")


def test_degraded_cannot_final_stamp(tmp_path: Path) -> None:
    """gate.sh 對真實 completeness rc=3 → 拒 final/實作 token（非 stub）。"""
    if not SPEC.is_file() or not GATE_SH.is_file():
        pytest.skip("gate/SPEC missing")

    # session 必須落在 handoffs/reconcile/<session>/ 結構（gate engagement）
    recon_root = tmp_path / "handoffs" / "reconcile" / "sess_rc3_real"
    sources = recon_root / "sources"
    sources.mkdir(parents=True)

    b_codex = _finding("CODEX-R1-P2-01")
    b_comp = _finding("COMPOSER-R1-P2-01")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")
    synth = (
        b_codex
        + "\n"
        + b_comp
        + "\n## DEGRADE-GROK-01\n\nabsent grok.\n"
    )
    (recon_root / "synth.md").write_text(synth, encoding="utf-8")
    _write_lock(
        recon_root,
        roster=["codex", "composer", "grok"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )
    _write_degrade(recon_root, absent_family="grok", reason="timeout; will re-run")

    # 先確認 completeness 真產 rc=3
    direct = _run_completeness(recon_root)
    assert direct.returncode == 3, (
        f"前置 completeness 應 rc=3; "
        f"rc={direct.returncode} stdout={direct.stdout!r} stderr={direct.stderr!r}"
    )

    # V-B：--reconcile 指既有 synth.md（禁建 reconcile.md 覆蓋 synth union）
    recon_file = recon_root / "synth.md"
    adv = tmp_path / "adv.md"
    adv.write_text("# ADV\n\nVerdict: APPROVED\n", encoding="utf-8")

    # stamps stub PASS（僅 harness）；completeness 走真腳本（不 override）
    stamp_stub = tmp_path / "stamps_pass.sh"
    stamp_stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    stamp_stub.chmod(0o755)

    gate_dir = tmp_path / "gate_tokens"
    gate_dir.mkdir()

    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env["GOVERNANCE_TEST_HARNESS"] = "1"
    env["RECONCILE_STAMPS_CHECK_OVERRIDE"] = str(stamp_stub)
    env.pop("COMPLETENESS_CHECK_OVERRIDE", None)
    env.pop("COMPLETENESS_ADVISORY_ONLY", None)

    result = subprocess.run(
        [
            "bash",
            str(GATE_SH),
            "dispatch",
            "--intent",
            "B4 degraded cannot final stamp",
            "--risk",
            "high",
            "--facts-asked",
            "none-needed:fixture",
            "--review-role",
            "single-executor:n/a",
            "--template",
            "n/a:impl-test",
            "--spec",
            str(SPEC),
            "--adversarial",
            str(adv),
            "--reconcile",
            str(recon_file),
            "--task-id",
            "conv-degrade-final-test",
            "--output",
            "handoffs/conv-degrade-final-test.md",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode != 0, (
        f"DEGRADED_PENDING 應拒 final; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "completeness" in combined.lower(), f"須到 completeness 層: {combined!r}"
    assert (
        "DEGRADED_PENDING" in combined or "rc=3" in combined
    ), f"須含 DEGRADED_PENDING/rc=3: {combined!r}"


def test_roster_duplicate_fails(tmp_path: Path) -> None:
    """New-07: expected_roster 含重複家族 → exit1（不可 normalize 後 silently 去重放行）。

    可證偽反例：若 _check_roster 只 lower+用 roster 迴圈、不去驗 Counter>1 → 本測 rc0 紅。
    """
    session = tmp_path / "sess_roster_dup"
    sources = session / "sources"
    sources.mkdir(parents=True)

    b_codex = _finding("CODEX-R1-P2-01")
    b_comp = _finding("COMPOSER-R1-P2-01")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")
    (session / "synth.md").write_text(b_codex + "\n" + b_comp, encoding="utf-8")

    # 完整 sources 匹配去重後 roster，但 expected_roster 故意 dup codex
    _write_lock(
        session,
        roster=["codex", "codex", "composer"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"expected_roster 重複家族應 exit1; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 3
    combined = (result.stdout or "") + (result.stderr or "")
    assert (
        "重複" in combined
        or "ROSTER_DUP" in combined
        or "dup" in combined.lower()
    ), f"須提示 roster 重複: {combined!r}"
    assert "DEGRADED_PENDING" not in (result.stdout or "")


def test_roster_unknown_family_fails(tmp_path: Path) -> None:
    """New-07: expected_roster 含 allowlist 外家族 → exit1；有 degrade 事件也不可 rc3。

    allowlist = {codex,composer,grok,claude,agy}
    可證偽反例：若只 normalize 不驗 allowlist、或 unknown 走 degrade→rc3 → 本測紅。
    """
    session = tmp_path / "sess_roster_unknown"
    sources = session / "sources"
    sources.mkdir(parents=True)

    b_codex = _finding("CODEX-R1-P2-01")
    b_comp = _finding("COMPOSER-R1-P2-01")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")

    # roster 含 unknown 'other'；sources 僅 codex+composer；給 other 配 degrade 事件
    # 若錯誤地走 degrade 放行 → 會 rc3，本測要求仍 exit1
    synth = (
        b_codex
        + "\n"
        + b_comp
        + "\n## DEGRADE-OTHER-01\n\nabsent unknown family other.\n"
    )
    (session / "synth.md").write_text(synth, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex", "composer", "other"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )
    _write_degrade(session, absent_family="other")
    result = _run_completeness(session)
    assert result.returncode == 1, (
        f"allowlist 外 roster 即使有 degrade 仍 exit1（不可 rc3）; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 3
    combined = (result.stdout or "") + (result.stderr or "")
    assert (
        "allowlist" in combined.lower()
        or "ROSTER_UNKNOWN" in combined
        or "外家族" in combined
        or "unknown" in combined.lower()
    ), f"須提示 allowlist 外 roster: {combined!r}"
    assert "DEGRADED_PENDING" not in (result.stdout or "")
