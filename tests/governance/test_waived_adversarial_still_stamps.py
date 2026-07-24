"""V-M：stamp 脫鉤 adversarial-waived；call-count oracle。

nodeid:
  test_low_impl_nonwaived_adv_calls_stamp_once
  test_high_impl_nonwaived_adv_calls_stamp_once
  test_impl_waived_adv_still_calls_stamp
  test_review_no_spec_skips_stamp
  test_impl_full_stamp_passes
  test_mutation_waived_adv_skips_stamp_breaks_guard
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests.governance.test_low_risk_impl_requires_reconcile import (
    SPEC,
    _seed_audit,
    make_impl_passing_session,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"


def _stamp_count_stub(path: Path, log: Path, *, exit_code: int = 1) -> Path:
    """stub：把每次呼叫的第一參數 append 到 log；預設 exit 1（無戳記拒）。"""
    path.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            echo "$1" >> "{log}"
            exit {exit_code}
            """
        ),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _cc_pass(path: Path) -> Path:
    path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _minimal_session(tmp_path: Path, name: str) -> Path:
    """最小 session：sources+lock+synth（無戳記；completeness stub 時用）。"""
    import hashlib
    from datetime import datetime, timezone

    sess = tmp_path / "handoffs" / "reconcile" / name
    sources = sess / "sources"
    sources.mkdir(parents=True)
    body = (
        "## GROK-R1-P0-01\n\n**斷言**: x\n\n**碼證**: p:1\n\n"
        "**來源摘要**: sources/review-grok.md#abc\n"
    )
    src = sources / "review-grok.md"
    src.write_text(body, encoding="utf-8")
    synth = sess / "synth.md"
    synth.write_text(body + "\n## 戳記\n", encoding="utf-8")
    lock = {
        "version": 1,
        "session_id": name,
        "expected_roster": ["grok"],
        "sources": [
            {
                "realpath": str(src.resolve()),
                "sha256": hashlib.sha256(body.encode()).hexdigest(),
                "family": "grok",
            }
        ],
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
        "mode": "discovery",
    }
    (sess / "sources.lock").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return synth


def _count_synth_calls(log: Path, synth: Path) -> int:
    if not log.is_file():
        return 0
    target = str(synth.resolve())
    n = 0
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            if Path(line).resolve() == Path(target).resolve():
                n += 1
        except OSError:
            if line == str(synth) or line == target:
                n += 1
    return n


def _run(
    *,
    gate_dir: Path,
    risk: str,
    reconcile: str | None,
    adversarial: str,
    with_spec: bool,
    stamp_log: Path,
    env_more: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    stamp_stub = _stamp_count_stub(gate_dir / "stamp_stub.sh", stamp_log, exit_code=1)
    cc_stub = _cc_pass(gate_dir / "cc_stub.sh")
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env["GOVERNANCE_TEST_HARNESS"] = "1"
    env["RECONCILE_STAMPS_CHECK_OVERRIDE"] = str(stamp_stub)
    env["COMPLETENESS_CHECK_OVERRIDE"] = str(cc_stub)
    if env_more:
        env.update(env_more)
    cmd = [
        "bash",
        str(GATE_SH),
        "dispatch",
        "--intent",
        "V-M stamp call-count unit",
        "--risk",
        risk,
        "--facts-asked",
        "none-needed:unit-test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:V-M unit" if not with_spec else "n/a:impl V-M unit",
        "--adversarial",
        adversarial,
        "--task-id",
        "vm-stamp-count-unit",
        "--output",
        "handoffs/vm-stamp-count-unit.md",
    ]
    if with_spec:
        cmd.extend(["--spec", str(SPEC)])
    if reconcile is not None:
        cmd.extend(["--reconcile", reconcile])
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_low_impl_nonwaived_adv_calls_stamp_once(tmp_path: Path) -> None:
    """low + --spec + reconcile + 真實 adversarial → stamp call-count==1 且 rc≠0。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    synth = _minimal_session(tmp_path, "vm_low_once")
    # 合規 ADV 命名，避免 adversarial-processing 額外 stamp
    adv = tmp_path / "handoffs" / "20260725-VM-ADV-codex.md"
    adv.parent.mkdir(parents=True, exist_ok=True)
    adv.write_text("# ADV\n\nVerdict: APPROVED\n\nno blocking findings\n", encoding="utf-8")

    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    log = gate_dir / "stamp_calls.log"
    result = _run(
        gate_dir=gate_dir,
        risk="low",
        reconcile=str(synth),
        adversarial=str(adv),
        with_spec=True,
        stamp_log=log,
    )
    assert result.returncode != 0, "無真戳記應 rc≠0"
    assert _count_synth_calls(log, synth) == 1, (
        f"stamp 應恰 1 次(arg==synth); log={log.read_text() if log.is_file() else ''!r}"
    )


def test_high_impl_nonwaived_adv_calls_stamp_once(tmp_path: Path) -> None:
    """high + --spec + 非 waived adversarial → call-count==1（防雙跑/未刪舊塊）。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    synth = _minimal_session(tmp_path, "vm_high_once")
    adv = tmp_path / "handoffs" / "20260725-VMH-ADV-composer.md"
    adv.parent.mkdir(parents=True, exist_ok=True)
    adv.write_text("# ADV\n\nVerdict: APPROVED\n", encoding="utf-8")

    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    log = gate_dir / "stamp_calls.log"
    result = _run(
        gate_dir=gate_dir,
        risk="high",
        reconcile=str(synth),
        adversarial=str(adv),
        with_spec=True,
        stamp_log=log,
    )
    assert result.returncode != 0
    n = _count_synth_calls(log, synth)
    assert n == 1, (
        f"high 應 stamp 恰 1 次(未刪舊塊會==2); n={n} "
        f"log={log.read_text() if log.is_file() else ''!r}"
    )


def test_impl_waived_adv_still_calls_stamp(tmp_path: Path) -> None:
    """--spec + reconcile + --adversarial waived: → stamp 仍==1（V-M）。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    synth = _minimal_session(tmp_path, "vm_waived_adv")
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    log = gate_dir / "stamp_calls.log"
    result = _run(
        gate_dir=gate_dir,
        risk="low",
        reconcile=str(synth),
        adversarial="waived:unit-test",
        with_spec=True,
        stamp_log=log,
    )
    assert result.returncode != 0
    assert _count_synth_calls(log, synth) == 1, (
        f"waived adversarial 仍須 stamp; "
        f"log={log.read_text() if log.is_file() else ''!r}"
    )


def test_review_no_spec_skips_stamp(tmp_path: Path) -> None:
    """無 --spec + --adversarial waived: → stamp call-count==0。"""
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    log = gate_dir / "stamp_calls.log"
    # 仍掛 stub 以便計數（若被呼叫）
    result = _run(
        gate_dir=gate_dir,
        risk="low",
        reconcile=None,
        adversarial="waived:review",
        with_spec=False,
        stamp_log=log,
    )
    # review 可 PASS
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")
    calls = log.read_text(encoding="utf-8") if log.is_file() else ""
    assert calls.strip() == "", f"review 不應呼叫 stamp: {calls!r}"


def test_impl_full_stamp_passes(tmp_path: Path) -> None:
    """3 家 APPROVED 帶 task（真 stamp，無 override）→ rc=0。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    sess, synth, _meta = make_impl_passing_session(tmp_path)
    gate_dir = tmp_path / "gate"
    _seed_audit(gate_dir, sess)

    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    env.pop("RECONCILE_STAMPS_CHECK_OVERRIDE", None)
    env.pop("COMPLETENESS_CHECK_OVERRIDE", None)
    cmd = [
        "bash",
        str(GATE_SH),
        "dispatch",
        "--intent",
        "V-M full stamp pass",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:impl full stamp",
        "--spec",
        str(SPEC),
        "--reconcile",
        str(synth),
        "--task-id",
        "vm-full-stamp-unit",
        "--output",
        "handoffs/vm-full-stamp-unit.md",
    ]
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")


def test_mutation_waived_adv_skips_stamp_breaks_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：stamp 改回「adversarial waived → skip」→ waived adv 時 call-count==0。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")

    src = GATE_SH.read_text(encoding="utf-8")
    # 舊 V-M 洞：stamp 包在 adversarial 非 waived 條件內
    pat = re.compile(
        r'(\s*)bash "\$\{_stamp_bin\}" "\$\{reconcile\}" \\\n'
        r'\s*\|\| \{ echo "ERROR: impl reconcile 未獲委員核可。委員須 append RECONCILE-STAMP APPROVED。"; exit 1; \}',
        re.MULTILINE,
    )
    m = pat.search(src)
    assert m, "expected hoisted stamp call site"
    ind = m.group(1)
    replacement = (
        f'{ind}case "${{adversarial}}" in\n'
        f"{ind}  waived:*|stamped-waived:*) : ;;  # MUTATED skip stamp\n"
        f"{ind}  *)\n"
        f'{ind}    bash "${{_stamp_bin}}" "${{reconcile}}" \\\n'
        f'{ind}      || {{ echo "ERROR: impl reconcile 未獲委員核可。委員須 append RECONCILE-STAMP APPROVED。"; exit 1; }}\n'
        f"{ind}    ;;\n"
        f"{ind}esac"
    )
    bad, n = pat.subn(replacement, src, count=1)
    assert n == 1

    mut_gate = REPO_ROOT / "scripts" / f".gate_mut_vm_{os.getpid()}.sh"
    try:
        mut_gate.write_text(bad, encoding="utf-8")
        mut_gate.chmod(mut_gate.stat().st_mode | stat.S_IXUSR)
        monkeypatch.setattr(
            "tests.governance.test_waived_adversarial_still_stamps.GATE_SH",
            mut_gate,
        )

        synth = _minimal_session(tmp_path, "vm_mut_waived")
        gate_dir = tmp_path / "gate"
        gate_dir.mkdir()
        log = gate_dir / "stamp_calls.log"
        stamp_stub = _stamp_count_stub(gate_dir / "stamp_stub.sh", log, exit_code=1)
        cc_stub = _cc_pass(gate_dir / "cc_stub.sh")
        env = os.environ.copy()
        env["GATE_DIR_OVERRIDE"] = str(gate_dir)
        env["GOVERNANCE_TEST_HARNESS"] = "1"
        env["RECONCILE_STAMPS_CHECK_OVERRIDE"] = str(stamp_stub)
        env["COMPLETENESS_CHECK_OVERRIDE"] = str(cc_stub)
        cmd = [
            "bash",
            str(mut_gate),
            "dispatch",
            "--intent",
            "V-M mutation waived skip stamp",
            "--risk",
            "low",
            "--facts-asked",
            "none-needed:unit",
            "--review-role",
            "single-executor:n/a",
            "--template",
            "n/a:impl V-M mut",
            "--spec",
            str(SPEC),
            "--reconcile",
            str(synth),
            "--adversarial",
            "waived:unit-test",
            "--task-id",
            "vm-mut-waived",
            "--output",
            "handoffs/vm-mut-waived.md",
        ]
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        n_calls = _count_synth_calls(log, synth)
        # 變異後 waived adv 跳 stamp → call-count==0；防護斷言 call-count==1 會失敗
        with pytest.raises(AssertionError):
            assert n_calls == 1, (
                f"waived adversarial 仍須 stamp; n={n_calls} "
                f"rc={result.returncode} log={log.read_text() if log.is_file() else ''!r}"
            )
    finally:
        mut_gate.unlink(missing_ok=True)
