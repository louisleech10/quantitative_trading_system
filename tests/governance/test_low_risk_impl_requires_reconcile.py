"""V-C：impl(--spec) 不論 risk 一律須顯式 session reconcile。

nodeid:
  test_low_spec_no_reconcile_rejected
  test_low_spec_waived_reconcile_rejected
  test_low_spec_full_synth_passes
  test_make_impl_passing_session_rc0
"""
from __future__ import annotations

import hashlib
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
BODY_HASH_SH = REPO_ROOT / "scripts" / "reconcile_body_hash.sh"
WRITE_LOCK_SH = REPO_ROOT / "scripts" / "write_sources_lock.sh"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finding(fid: str) -> str:
    d = hashlib.sha256(fid.encode()).hexdigest()[:12]
    return (
        f"## {fid}\n\n"
        f"**斷言**: V-C impl requires reconcile\n\n"
        f"**碼證**: path:1\n\n"
        f"**來源摘要**: sources/review.md#{d}\n"
    )


def _stub_pass(path: Path) -> Path:
    path.write_text("#!/usr/bin/env bash\necho STUB_PASS\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def make_impl_passing_session(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """§V helper：完整 session + 3 家戳記 + audit 事件，使真實 stamp+completeness 可 PASS。

    回傳 (session_dir, synth_path, env_partial)。
    env_partial 僅含需寫入 gate_dir 前的設定提示（audit 預種路徑由 caller 接 GATE_DIR）。
    """
    # task id 僅 [a-z0-9-]（STAMP_TASK_RE 不含 underscore）
    uniq = f"vcpass{os.getpid()}{id(tmp_path) % 100000}"
    sess = tmp_path / "handoffs" / "reconcile" / uniq
    sources = sess / "sources"
    sources.mkdir(parents=True)

    bodies: dict[str, str] = {}
    for fam in ("codex", "composer", "grok"):
        fid = f"{fam.upper()}-R1-P0-01"
        body = _finding(fid)
        bodies[fam] = body
        (sources / f"review-{fam}.md").write_text(body, encoding="utf-8")

    synth_body = "\n".join(bodies[f] for f in ("codex", "composer", "grok"))
    synth = sess / "synth.md"
    # 先寫 body + 戳記區標題以算 body-hash
    synth.write_text(synth_body + "\n\n## 戳記\n\n", encoding="utf-8")

    # sources.lock via write_sources_lock.sh
    env_lock = os.environ.copy()
    env_lock["GOVERNANCE_TEST_HARNESS"] = "1"
    lock_proc = subprocess.run(
        [
            "bash",
            str(WRITE_LOCK_SH),
            "--session",
            str(sess),
            "--roster",
            "codex,composer,grok",
            "--mode",
            "discovery",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env_lock,
    )
    assert lock_proc.returncode == 0, lock_proc.stdout + lock_proc.stderr

    h_proc = subprocess.run(
        ["bash", str(BODY_HASH_SH), str(synth)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    h = h_proc.stdout.strip()

    tids = {
        "codex": f"vc-stamp-codex-{uniq}",
        "composer": f"vc-stamp-composer-{uniq}",
        "grok": f"vc-stamp-grok-{uniq}",
    }
    stamp_lines = [
        f"RECONCILE-STAMP: {fam} APPROVED 2099-01-01 sha256:{h} task:{tids[fam]}"
        for fam in ("codex", "composer", "grok")
    ]
    synth.write_text(synth_body + "\n\n## 戳記\n\n" + "\n".join(stamp_lines) + "\n", encoding="utf-8")

    # audit events payload（caller 寫入 GATE_DIR/audit.log）
    rel_out = f"handoffs/reconcile/{uniq}/synth.md"
    audit_events = []
    for fam in ("codex", "composer", "grok"):
        audit_events.append(
            {
                "event": "committee_dispatch",
                "task_id": tids[fam],
                "family": fam,
                "output_path": rel_out,
                "output_sha256": h,
                "ts": "2099-01-01T00:00:00Z",
            }
        )
    # stash on session for callers
    (sess / ".audit_seed.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in audit_events) + "\n",
        encoding="utf-8",
    )
    return sess, synth, {"body_hash": h, "tids": tids}


def _seed_audit(gate_dir: Path, session: Path) -> None:
    seed = session / ".audit_seed.jsonl"
    audit = gate_dir / "audit.log"
    gate_dir.mkdir(parents=True, exist_ok=True)
    audit.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8")


def _run_gate(
    *,
    gate_dir: Path,
    risk: str,
    reconcile: str | None,
    env_extra: dict[str, str] | None = None,
    with_spec: bool = True,
    adversarial: str | None = None,
    template: str = "n/a:V-C unit test",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    env.pop("RECONCILE_STAMPS_CHECK_OVERRIDE", None)
    env.pop("COMPLETENESS_CHECK_OVERRIDE", None)
    if env_extra:
        env.update(env_extra)
    cmd = [
        "bash",
        str(GATE_SH),
        "dispatch",
        "--intent",
        "V-C low-risk impl reconcile unit",
        "--risk",
        risk,
        "--facts-asked",
        "none-needed:unit-test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        template,
        "--task-id",
        "vc-low-impl-unit",
        "--output",
        "handoffs/vc-low-impl-unit.md",
    ]
    if with_spec:
        cmd.extend(["--spec", str(SPEC)])
    if reconcile is not None:
        cmd.extend(["--reconcile", reconcile])
    if adversarial is not None:
        cmd.extend(["--adversarial", adversarial])
    elif risk == "high":
        cmd.extend(["--adversarial", "waived:unit"])
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_low_spec_no_reconcile_rejected(tmp_path: Path) -> None:
    """--risk low --spec X 無 --reconcile → rc≠0。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    result = _run_gate(gate_dir=gate_dir, risk="low", reconcile=None, with_spec=True)
    assert result.returncode != 0, (
        f"low+spec 無 reconcile 應拒; rc={result.returncode} "
        f"out={(result.stdout or '') + (result.stderr or '')!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "reconcile" in combined.lower(), combined


def test_low_spec_waived_reconcile_rejected(tmp_path: Path) -> None:
    """--spec X --reconcile waived: → rc≠0。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    result = _run_gate(
        gate_dir=gate_dir,
        risk="low",
        reconcile="waived:test",
        with_spec=True,
    )
    assert result.returncode != 0, (
        f"waived reconcile 應拒; rc={result.returncode} "
        f"out={(result.stdout or '') + (result.stderr or '')!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "reconcile" in combined.lower(), combined


def test_low_spec_full_synth_passes(tmp_path: Path) -> None:
    """--risk low --spec + 完整 synth + 真 stamp/completeness → rc=0。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    sess, synth, _meta = make_impl_passing_session(tmp_path)
    gate_dir = tmp_path / "gate"
    _seed_audit(gate_dir, sess)

    result = _run_gate(
        gate_dir=gate_dir,
        risk="low",
        reconcile=str(synth),
        with_spec=True,
        # 無 override：真跑 stamp + completeness
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, (
        f"完整 synth 應 PASS; rc={result.returncode} out={combined!r}"
    )


def test_make_impl_passing_session_rc0(tmp_path: Path) -> None:
    """獨立驗 helper 契約：make_impl_passing_session → gate rc=0。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    sess, synth, _meta = make_impl_passing_session(tmp_path)
    gate_dir = tmp_path / "gate"
    _seed_audit(gate_dir, sess)
    result = _run_gate(
        gate_dir=gate_dir,
        risk="low",
        reconcile=str(synth),
        with_spec=True,
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")
