"""B3 Task 3.2 — gate.sh 高風險派實作掛 completeness（BC1–BC3 fix）。

nodeid:
  test_gate_rejects_incomplete_sources
  test_gate_rejects_degraded_final
  test_env_override_rejected_without_harness
  test_waived_adversarial_still_runs_completeness
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
SPEC = REPO_ROOT / "docs" / "CONVERGENCE_METHOD_SPEC.md"


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _finding(fid: str = "GROK-R1-P0-01") -> str:
    import hashlib

    d = hashlib.sha256(fid.encode()).hexdigest()[:12]
    return (
        f"## {fid}\n\n"
        f"**斷言**: gate completeness\n\n"
        f"**碼證**: path:1\n\n"
        f"**來源摘要**: sources/review-grok.md#{d}\n"
    )


def _conv_session(base: Path, name: str) -> Path:
    """合法 convergence 路徑：…/handoffs/reconcile/<session>/（觸發 _run_completeness_gate）。"""
    session = base / "handoffs" / "reconcile" / name
    (session / "sources").mkdir(parents=True)
    return session


def _write_session_incomplete(base: Path) -> Path:
    """roster 3 家、只放 2 檔 → completeness rc=1（roster 缺席）。

    路徑名刻意不含 degraded/fail/roster 等斷言關鍵字，避免假綠。
    """
    session = _conv_session(base, "sess_roster_gap")
    sources = session / "sources"
    bodies = {
        "review-codex.md": _finding("CODEX-R1-P0-01"),
        "review-composer.md": _finding("COMPOSER-R1-P0-01"),
    }
    entries = []
    synth_parts = []
    for name, body in bodies.items():
        p = sources / name
        p.write_text(body, encoding="utf-8")
        fam = name.rsplit("-", 1)[-1].removesuffix(".md")
        entries.append(
            {
                "realpath": str(p.resolve()),
                "sha256": _sha256_bytes(body.encode()),
                "family": fam,
            }
        )
        synth_parts.append(body)
    # synth 含 grok 假合併，但來源缺 grok
    synth_parts.append(_finding("GROK-R1-P0-01"))
    (session / "synth.md").write_text("\n".join(synth_parts), encoding="utf-8")
    lock = {
        "version": 1,
        "session_id": session.name,
        "expected_roster": ["codex", "composer", "grok"],
        "sources": sorted(entries, key=lambda e: e["realpath"]),
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
    }
    (session / "sources.lock").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # V-B：gate --reconcile 目標須為 synth.md（既有 synth 保留，不覆蓋）
    return session / "synth.md"


def _write_session_single_ok(base: Path, name: str = "session_ok") -> Path:
    """單家完整 lock（給 stub completeness 路徑用）。"""
    session = _conv_session(base, name)
    sources = session / "sources"
    body = _finding()
    src = sources / "review-grok.md"
    src.write_text(body, encoding="utf-8")
    (session / "synth.md").write_text(body, encoding="utf-8")
    lock = {
        "version": 1,
        "session_id": session.name,
        "expected_roster": ["grok"],
        "sources": [
            {
                "realpath": str(src.resolve()),
                "sha256": _sha256_bytes(body.encode()),
                "family": "grok",
            }
        ],
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
    }
    (session / "sources.lock").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # V-B：gate --reconcile 目標須為 synth.md（既有 synth 保留，不覆蓋）
    return session / "synth.md"


def _stub_pass(path: Path) -> Path:
    path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            echo "STUB PASS: $*"
            exit 0
            """
        ),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _stub_rc3(path: Path) -> Path:
    """B3：degrade 狀態機未實作；用 rc=3 stub 驗 gate 對 DEGRADED_PENDING 反應。"""
    path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            echo "DEGRADED_PENDING"
            exit 3
            """
        ),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _run_gate_high_risk(
    *,
    gate_dir: Path,
    reconcile: Path,
    adversarial: str | Path,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    # 清除可能從外部洩入的 harness/override
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    env.pop("RECONCILE_STAMPS_CHECK_OVERRIDE", None)
    env.pop("COMPLETENESS_CHECK_OVERRIDE", None)
    if env_extra:
        env.update(env_extra)
    # 避開 review-quorum（非 *-impl-bN-*）
    cmd = [
        "bash",
        str(GATE_SH),
        "dispatch",
        "--intent",
        "B3 completeness gate unit test",
        "--risk",
        "high",
        "--facts-asked",
        "none-needed:unit-test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:impl gate completeness unit test",
        "--spec",
        str(SPEC),
        "--adversarial",
        str(adversarial),
        "--reconcile",
        str(reconcile),
        "--task-id",
        "conv-gate-completeness-unit",
        "--output",
        "handoffs/conv-gate-completeness-unit.md",
    ]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_gate_rejects_incomplete_sources(tmp_path: Path) -> None:
    """真實 _run_completeness_gate：roster 缺席 → 拒發（禁路徑子字串/禁單獨 FAIL）。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")

    recon = _write_session_incomplete(tmp_path)
    adv = tmp_path / "adv.md"
    adv.write_text("# ADV\n\nVerdict: APPROVED\n\nno blocking findings\n", encoding="utf-8")

    stamp_stub = _stub_pass(tmp_path / "stamps_pass.sh")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()

    result = _run_gate_high_risk(
        gate_dir=gate_dir,
        reconcile=recon,
        adversarial=adv,
        env_extra={
            "GOVERNANCE_TEST_HARNESS": "1",
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(stamp_stub),
            # 不覆寫 completeness：真走 scripts/completeness_check.sh
        },
    )
    assert result.returncode != 0, (
        f"incomplete sources 應拒發 token; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    cl = combined.lower()
    # 須真到 completeness 層（禁僅 stamp FAIL / 路徑名假命中 / 禁單獨 FAIL）
    assert "completeness" in cl, f"須含 completeness 關鍵字: {combined!r}"
    assert (
        "roster" in cl or "缺席" in combined
    ), f"須含 roster/缺席（真 completeness 訊息）: {combined!r}"


def test_gate_rejects_degraded_final(tmp_path: Path) -> None:
    """rc=3 stub（DEGRADED_PENDING）→ gate 拒 final；須真走到 completeness gate。

    路徑名刻意不含 degraded（防路徑子字串假綠）。
    """
    if not SPEC.is_file():
        pytest.skip("SPEC missing")

    recon = _write_session_single_ok(tmp_path, "sess_rc3_stub")
    adv = tmp_path / "adv.md"
    adv.write_text("# ADV\n\nVerdict: APPROVED\n", encoding="utf-8")

    stamp_stub = _stub_pass(tmp_path / "stamps_pass.sh")
    deg_stub = _stub_rc3(tmp_path / "completeness_rc3.sh")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()

    result = _run_gate_high_risk(
        gate_dir=gate_dir,
        reconcile=recon,
        adversarial=adv,
        env_extra={
            "GOVERNANCE_TEST_HARNESS": "1",
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(stamp_stub),
            "COMPLETENESS_CHECK_OVERRIDE": str(deg_stub),
        },
    )
    assert result.returncode != 0, (
        f"DEGRADED_PENDING(rc=3) 應拒發; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    # 須為 gate 對 completeness rc=3 的明確拒發（禁路徑子字串 / 禁單獨 FAIL）
    assert "completeness" in combined.lower(), f"須含 completeness: {combined!r}"
    assert (
        "DEGRADED_PENDING" in combined or "rc=3" in combined
    ), f"須含 DEGRADED_PENDING 或 rc=3: {combined!r}"


def test_env_override_rejected_without_harness(tmp_path: Path) -> None:
    """BC1：未設 GOVERNANCE_TEST_HARNESS 而設 override → gate fail-closed exit1。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")

    recon = _write_session_single_ok(tmp_path, "session_bypass")
    adv = tmp_path / "adv.md"
    adv.write_text("# ADV\n\nVerdict: APPROVED\n", encoding="utf-8")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()

    # COMPLETENESS_CHECK_OVERRIDE=/bin/true 在無 harness 時必須拒
    result = _run_gate_high_risk(
        gate_dir=gate_dir,
        reconcile=recon,
        adversarial=adv,
        env_extra={
            # 刻意不設 GOVERNANCE_TEST_HARNESS
            "COMPLETENESS_CHECK_OVERRIDE": "/bin/true",
        },
    )
    assert result.returncode == 1, (
        f"無 harness 的 override 應 exit1; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "COMPLETENESS_CHECK_OVERRIDE" in combined or "GOVERNANCE_TEST_HARNESS" in combined

    # RECONCILE_STAMPS_CHECK_OVERRIDE 同理
    result2 = _run_gate_high_risk(
        gate_dir=gate_dir,
        reconcile=recon,
        adversarial=adv,
        env_extra={
            "RECONCILE_STAMPS_CHECK_OVERRIDE": "/bin/true",
        },
    )
    assert result2.returncode == 1
    combined2 = (result2.stdout or "") + (result2.stderr or "")
    assert (
        "RECONCILE_STAMPS_CHECK_OVERRIDE" in combined2
        or "GOVERNANCE_TEST_HARNESS" in combined2
    )

    # completeness_check.sh 的 COMPLETENESS_ALLOW_ARGV_SOURCES 無 harness → fail-closed
    env = os.environ.copy()
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    env["COMPLETENESS_ALLOW_ARGV_SOURCES"] = "1"
    cc = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "completeness_check.sh"), "a", "b"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert cc.returncode == 1
    cc_out = (cc.stdout or "") + (cc.stderr or "")
    assert "COMPLETENESS_ALLOW_ARGV_SOURCES" in cc_out or "GOVERNANCE_TEST_HARNESS" in cc_out


def test_waived_adversarial_still_runs_completeness(tmp_path: Path) -> None:
    """BC2：--adversarial waived: + convergence incomplete lock → 仍 exit1（completeness 未跳過）。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")

    recon = _write_session_incomplete(tmp_path)
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()

    result = _run_gate_high_risk(
        gate_dir=gate_dir,
        reconcile=recon,
        adversarial="waived:legacy-unit-test",
        env_extra={
            # waived 不需 stamp stub；completeness 真跑
        },
    )
    assert result.returncode != 0, (
        f"waived+incomplete 應仍被 completeness 擋; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    cl = combined.lower()
    assert "completeness" in cl, f"須走到 completeness: {combined!r}"
    assert (
        "roster" in cl or "缺席" in combined or "sources.lock" in cl
    ), f"須為 lock/roster 拒發: {combined!r}"
