"""V-B：gate --reconcile 目標須 realpath == session/synth.md。

nodeid:
  test_dropped_target_rejected
  test_synth_target_passes
  test_symlink_to_synth_passes
  test_no_reconcile_dispatch_not_rejected_by_realpath
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
        f"**斷言**: V-B target bind\n\n"
        f"**碼證**: path:1\n\n"
        f"**來源摘要**: sources/review-grok.md#{d}\n"
    )


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


def _write_complete_session(base: Path, name: str = "vb_sess") -> Path:
    """單家完整 session（sources+lock+synth）；回傳 session 目錄。"""
    session = base / "handoffs" / "reconcile" / name
    sources = session / "sources"
    sources.mkdir(parents=True)
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
        "mode": "discovery",
    }
    (session / "sources.lock").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return session


def _run_dispatch(
    *,
    gate_dir: Path,
    reconcile: str | Path | None,
    env_extra: dict[str, str] | None = None,
    risk: str = "low",
    with_spec: bool = False,
    template: str = "n/a:V-B unit test",
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
        "V-B target-synth bind unit test",
        "--risk",
        risk,
        "--facts-asked",
        "none-needed:unit-test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        template,
        "--task-id",
        "vb-target-bind-unit",
        "--output",
        "handoffs/vb-target-bind-unit.md",
    ]
    if with_spec:
        cmd.extend(["--spec", str(SPEC)])
    if reconcile is not None:
        cmd.extend(["--reconcile", str(reconcile)])
    if risk == "high":
        cmd.extend(["--adversarial", "waived:unit-test"])
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_dropped_target_rejected(tmp_path: Path) -> None:
    """session synth 完整、--reconcile 指缺項 dropped.md → realpath 綁定拒發。"""
    session = _write_complete_session(tmp_path, "vb_dropped")
    dropped = session / "dropped.md"
    dropped.write_text("# dropped incomplete union\n\n## 戳記\n", encoding="utf-8")

    stamp_stub = _stub_pass(tmp_path / "stamps.sh")
    # completeness stub PASS：若無 realpath 綁定，會被放行（mutation 轉紅依據）
    cc_stub = _stub_pass(tmp_path / "cc.sh")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()

    result = _run_dispatch(
        gate_dir=gate_dir,
        reconcile=dropped,
        env_extra={
            "GOVERNANCE_TEST_HARNESS": "1",
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(stamp_stub),
            "COMPLETENESS_CHECK_OVERRIDE": str(cc_stub),
        },
    )
    assert result.returncode != 0, (
        f"dropped target 應拒; rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "synth.md" in combined or "未綁定" in combined or "目標須為" in combined, (
        f"須指明 target/synth 綁定: {combined!r}"
    )


def test_synth_target_passes(tmp_path: Path) -> None:
    """--reconcile 指 synth.md → 通過 realpath 閘（可停在下游；本測用 stub 使整體 PASS）。"""
    session = _write_complete_session(tmp_path, "vb_synth_ok")
    synth = session / "synth.md"
    stamp_stub = _stub_pass(tmp_path / "stamps.sh")
    cc_stub = _stub_pass(tmp_path / "cc.sh")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()

    result = _run_dispatch(
        gate_dir=gate_dir,
        reconcile=synth,
        env_extra={
            "GOVERNANCE_TEST_HARNESS": "1",
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(stamp_stub),
            "COMPLETENESS_CHECK_OVERRIDE": str(cc_stub),
        },
    )
    combined = (result.stdout or "") + (result.stderr or "")
    # 不得被 realpath 綁定拒
    assert "目標須為 session synth.md" not in combined, combined
    assert "未綁定" not in combined, combined
    assert result.returncode == 0, (
        f"synth target + stub 應 PASS; rc={result.returncode} out={combined!r}"
    )


def test_symlink_to_synth_passes(tmp_path: Path) -> None:
    """symlink → synth.md（realpath 展開後相等）→ 放行。"""
    session = _write_complete_session(tmp_path, "vb_symlink")
    synth = session / "synth.md"
    link = session / "alias_recon.md"
    try:
        link.symlink_to(synth.name)  # relative symlink
    except OSError as exc:
        pytest.skip(f"symlink unsupported: {exc}")

    stamp_stub = _stub_pass(tmp_path / "stamps.sh")
    cc_stub = _stub_pass(tmp_path / "cc.sh")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()

    result = _run_dispatch(
        gate_dir=gate_dir,
        reconcile=link,
        env_extra={
            "GOVERNANCE_TEST_HARNESS": "1",
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(stamp_stub),
            "COMPLETENESS_CHECK_OVERRIDE": str(cc_stub),
        },
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "目標須為 session synth.md" not in combined, combined
    assert result.returncode == 0, (
        f"symlink→synth 應 PASS; rc={result.returncode} out={combined!r}"
    )


def test_no_reconcile_dispatch_not_rejected_by_realpath(tmp_path: Path) -> None:
    """無 --reconcile 的派工（review template n/a）→ 不被 realpath 綁定拒發。"""
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    result = _run_dispatch(
        gate_dir=gate_dir,
        reconcile=None,
        risk="low",
        with_spec=False,
        template="n/a:review no reconcile",
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "目標須為 session synth.md" not in combined, combined
    assert "未綁定" not in combined, combined
    # 可能因其他 miss 失敗，但不得是 realpath 綁定
    # low + n/a + 無 reconcile 應可 PASS
    assert result.returncode == 0, (
        f"無 reconcile 不應被 realpath 擋; rc={result.returncode} out={combined!r}"
    )
