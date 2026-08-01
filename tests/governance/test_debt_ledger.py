"""P1-6 B4 Task 2.1：debt_ledger.sh 只讀帳本。

驗收對齊 SPEC Task 2.1 驗證段 + 邊界 + mutation 三態。
hermetic：一律走 _debt_probe_helper.run_cmd（傳 env 即完整置換）。
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from tests.governance import _debt_probe_helper as helper

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "scripts" / "audit_events.json"
LEDGER_SH = REPO_ROOT / "scripts" / "debt_ledger.sh"
APPEND_SH = REPO_ROOT / "scripts" / "audit_append.sh"


def _hermetic_env(audit: Path, **extra: str) -> dict[str, str]:
    """完整置換 env；不繼承 parent（含 ROUND_ID）。"""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C"),
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
    }
    env.update(extra)
    return env


def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
    """隔離 repo 副本：scripts + 空 audit。"""
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in ("debt_ledger.sh", "_debt_ledger_core.py", "audit_append.sh", "audit_events.json"):
        src = REPO_ROOT / "scripts" / name
        shutil.copy2(src, scripts / name)
        if name.endswith(".sh"):
            (scripts / name).chmod(0o755)
    audit = root / ".claude" / "gate" / "audit.log"
    audit.parent.mkdir(parents=True)
    audit.write_text("", encoding="utf-8")
    return root, audit


def _append(root: Path, audit: Path, *args: str) -> None:
    env = _hermetic_env(audit)
    r = helper.run_cmd(
        root / "scripts" / "audit_append.sh",
        *args,
        env=env,
        cwd=root,
    )
    assert r.returncode == 0, f"append fail rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"


def _ledger(root: Path, audit: Path, *args: str, **extra_env: str):
    env = _hermetic_env(audit, **extra_env)
    return helper.run_cmd(
        root / "scripts" / "debt_ledger.sh",
        *args,
        env=env,
        cwd=root,
    )


def _open(
    root: Path,
    audit: Path,
    *,
    round_id: str,
    session: str,
    participants: list[str],
    actor: str = "test",
) -> None:
    parts = json.dumps(participants, ensure_ascii=False)
    outs = {f: f"handoffs/out-{f}.md" for f in participants}
    _append(
        root,
        audit,
        "--require-absent-session",
        session,
        "--event",
        "committee_round_open",
        "--field",
        f"round_id={round_id}",
        "--field",
        "task_id=t1",
        "--field",
        "brief_path=handoffs/brief.md",
        "--field",
        "brief_sha256=" + ("a" * 64),
        "--field",
        "brief_sha256_norm=" + ("b" * 64),
        "--field",
        "lock_mode=discovery",
        "--field",
        f"participants=@{parts}",
        "--field",
        f"expected_outputs=@{json.dumps(outs, ensure_ascii=False)}",
        "--field",
        f"session_name={session}",
        "--field",
        f"actor={actor}",
        "--field",
        "origin_script=committee_run.sh",
    )


def _result(
    root: Path,
    audit: Path,
    *,
    round_id: str,
    family: str,
    state: str = "success",
    sha: str | None = None,
    path: str | None = None,
) -> None:
    out = path or f"handoffs/out-{family}.md"
    out_sha = sha if sha is not None else ("c" * 64 if state == "success" else "")
    args = [
        "--event",
        "committee_family_result",
        "--field",
        f"round_id={round_id}",
        "--field",
        f"family={family}",
        "--field",
        "attempt_id=att-1",
        "--field",
        "cli_rc=0" if state == "success" else "cli_rc=1",
        "--field",
        f"output_path={out}",
        "--field",
        f"output_sha256={out_sha}",
        "--field",
        f"result_state={state}",
        "--field",
        "actor=test",
        "--field",
        "origin_script=cx_run.sh",
    ]
    _append(root, audit, *args)


def _clear_event(root: Path, audit: Path, *, round_id: str, session: str) -> None:
    _append(
        root,
        audit,
        "--event",
        "committee_debt_clear",
        "--field",
        f"round_id={round_id}",
        "--field",
        f"session_id={session}",
        "--field",
        "lock_sha256=" + ("d" * 64),
        "--field",
        "synth_sha256=" + ("e" * 64),
        "--field",
        'roster=@["codex"]',
        "--field",
        "completeness_rc=0",
        "--field",
        "actor=test",
        "--field",
        "origin_script=debt_clear.sh",
    )


def _write_raw(audit: Path, lines: list[str]) -> None:
    audit.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


# ── SPEC 驗證段 ──────────────────────────────────────────


def test_list_one_open_with_three_families(tmp_path: Path) -> None:
    """派 3 家 → --list 1 筆 OPEN。"""
    root, audit = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    _open(root, audit, round_id=rid, session="s3", participants=["codex", "composer", "grok"])
    for fam in ("codex", "composer", "grok"):
        _result(root, audit, round_id=rid, family=fam)
    r = _ledger(root, audit, "--list")
    assert r.returncode == 0, r.stderr
    opens = [ln for ln in r.stdout.splitlines() if "state=OPEN" in ln]
    assert len(opens) == 1
    assert rid in opens[0]


def test_list_one_open_with_one_family(tmp_path: Path) -> None:
    """派 1 家 → 也 1 筆 OPEN。"""
    root, audit = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    _open(root, audit, round_id=rid, session="s1", participants=["codex"])
    _result(root, audit, round_id=rid, family="codex")
    r = _ledger(root, audit, "--list")
    assert r.returncode == 0, r.stderr
    opens = [ln for ln in r.stdout.splitlines() if "state=OPEN" in ln]
    assert len(opens) == 1


def test_clear_then_zero_open(tmp_path: Path) -> None:
    """銷帳後 → 0 筆 OPEN。"""
    root, audit = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    _open(root, audit, round_id=rid, session="sc", participants=["codex"])
    _clear_event(root, audit, round_id=rid, session="sc")
    r = _ledger(root, audit, "--list")
    assert r.returncode == 0, r.stderr
    opens = [ln for ln in r.stdout.splitlines() if "state=OPEN" in ln]
    assert opens == []
    h = _ledger(root, audit, "--has-open")
    assert h.returncode == 0  # 無債


def test_cutoff_before_records_zero(tmp_path: Path) -> None:
    """cutoff 前紀錄 → 0 筆。"""
    root, audit = _setup_repo(tmp_path)
    # 手寫 pre-cutoff 事件（append 會寫當下 ts）
    rec = {
        "event": "committee_round_open",
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "sequence": 1,
        "producer": "audit_append.sh",
        "origin_script": "committee_run.sh",
        "actor": "test",
        "ts": "2020-01-01T00:00:00Z",
        "round_id": "old-round",
        "task_id": "t",
        "brief_path": "handoffs/b.md",
        "brief_sha256": "a" * 64,
        "brief_sha256_norm": "b" * 64,
        "lock_mode": "discovery",
        "participants": ["codex"],
        "expected_outputs": {"codex": "handoffs/x.md"},
        "session_name": "old-sess",
    }
    _write_raw(audit, [json.dumps(rec, ensure_ascii=False, sort_keys=True)])
    r = _ledger(root, audit, "--list")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""
    h = _ledger(root, audit, "--has-open")
    assert h.returncode == 0


def test_empty_audit_zero_debt(tmp_path: Path) -> None:
    """audit 存在但零 JSON 行 → 無債 rc=0。"""
    root, audit = _setup_repo(tmp_path)
    audit.write_text("# comment only\n\n", encoding="utf-8")
    h = _ledger(root, audit, "--has-open")
    assert h.returncode == 0, h.stderr
    r = _ledger(root, audit, "--list")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_missing_audit_fail_closed(tmp_path: Path) -> None:
    """audit 檔缺失 → rc=2。"""
    root, audit = _setup_repo(tmp_path)
    missing = root / "no-such-audit.log"
    env = _hermetic_env(missing)
    r = helper.run_cmd(root / "scripts" / "debt_ledger.sh", "--has-open", env=env, cwd=root)
    assert r.returncode == 2
    assert "缺失" in (r.stderr or "") or "ERROR" in (r.stderr or "")


def test_duplicate_open_same_round_fail_closed(tmp_path: Path) -> None:
    """同一 round_id 兩筆 committee_round_open → fail-closed。"""
    root, audit = _setup_repo(tmp_path)
    rid = "dup-round"
    # 兩筆不同 session 同 round_id（手寫，繞 require-absent）
    lines = []
    for i, sess in enumerate(("s-a", "s-b"), start=1):
        rec = {
            "event": "committee_round_open",
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "sequence": i,
            "producer": "audit_append.sh",
            "origin_script": "committee_run.sh",
            "actor": "test",
            "ts": "2026-07-29T00:00:00Z",
            "round_id": rid,
            "task_id": "t",
            "brief_path": "handoffs/b.md",
            "brief_sha256": "a" * 64,
            "brief_sha256_norm": "b" * 64,
            "lock_mode": "discovery",
            "participants": ["codex"],
            "expected_outputs": {"codex": "handoffs/x.md"},
            "session_name": sess,
        }
        lines.append(json.dumps(rec, ensure_ascii=False, sort_keys=True))
    _write_raw(audit, lines)
    r = _ledger(root, audit, "--has-open")
    assert r.returncode == 2
    assert "兩筆" in (r.stderr or "") or "round_id" in (r.stderr or "")


def test_malformed_json_line_fail_closed(tmp_path: Path) -> None:
    """以 { 開頭但 JSON 壞 → rc=2（不得靜默略過）。"""
    root, audit = _setup_repo(tmp_path)
    audit.write_text('{not-json\n', encoding="utf-8")
    r = _ledger(root, audit, "--has-open")
    assert r.returncode == 2
    assert "JSON" in (r.stderr or "") or "解析" in (r.stderr or "")


def test_malformed_json_no_debt_marker_fail_closed(tmp_path: Path) -> None:
    """無 debt-marker 的壞 JSON（以 { 開頭且以 } 結尾）→ rc=2。

    迴歸 CODEX-R2-P1-01：marker prefilter 曾把 `{not-json}` 當「不像帳目」跳過，
    導致 --has-open 假報「無債」(rc=0) 並讓 gate dispatch fail-open。
    壞行本身不含任何 debt 事件關鍵字——這正是 prefilter 會漏的形態。
    """
    root, audit = _setup_repo(tmp_path)
    # 關鍵：以 } 結尾 + 無 debt-marker（舊 prefilter 會 continue）
    audit.write_text("{not-json}\n", encoding="utf-8")
    r = _ledger(root, audit, "--has-open")
    assert r.returncode == 2, (
        f"無 marker 壞 JSON 須 fail-closed rc=2, got {r.returncode}; "
        f"err={r.stderr!r} out={r.stdout!r}"
    )
    assert "JSON" in (r.stderr or "") or "解析" in (r.stderr or ""), r.stderr


def test_sequence_gap_fail_closed(tmp_path: Path) -> None:
    """序號缺號 → fail-closed。"""
    root, audit = _setup_repo(tmp_path)
    rec = {
        "event": "committee_round_open",
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "sequence": 2,  # gap: missing 1
        "producer": "audit_append.sh",
        "origin_script": "committee_run.sh",
        "actor": "test",
        "ts": "2026-07-29T00:00:00Z",
        "round_id": "gap-r",
        "task_id": "t",
        "brief_path": "handoffs/b.md",
        "brief_sha256": "a" * 64,
        "brief_sha256_norm": "b" * 64,
        "lock_mode": "discovery",
        "participants": ["codex"],
        "expected_outputs": {"codex": "handoffs/x.md"},
        "session_name": "gap-s",
    }
    _write_raw(audit, [json.dumps(rec, ensure_ascii=False, sort_keys=True)])
    r = _ledger(root, audit, "--has-open")
    assert r.returncode == 2
    assert "缺號" in (r.stderr or "") or "序號" in (r.stderr or "")


def test_sequence_dup_fail_closed(tmp_path: Path) -> None:
    """序號重號 → fail-closed。"""
    root, audit = _setup_repo(tmp_path)
    lines = []
    for sess in ("s1", "s2"):
        rec = {
            "event": "committee_round_open",
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "sequence": 1,  # 重號
            "producer": "audit_append.sh",
            "origin_script": "committee_run.sh",
            "actor": "test",
            "ts": "2026-07-29T00:00:00Z",
            "round_id": f"r-{sess}",
            "task_id": "t",
            "brief_path": "handoffs/b.md",
            "brief_sha256": "a" * 64,
            "brief_sha256_norm": "b" * 64,
            "lock_mode": "discovery",
            "participants": ["codex"],
            "expected_outputs": {"codex": "handoffs/x.md"},
            "session_name": sess,
        }
        lines.append(json.dumps(rec, ensure_ascii=False, sort_keys=True))
    _write_raw(audit, lines)
    r = _ledger(root, audit, "--has-open")
    assert r.returncode == 2
    assert "重號" in (r.stderr or "") or "序號" in (r.stderr or "")


def test_latest_result_wins_by_sequence(tmp_path: Path) -> None:
    """同一 (round, family) 多筆 → 取序號最大。"""
    root, audit = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    _open(root, audit, round_id=rid, session="lr", participants=["codex"])
    _result(root, audit, round_id=rid, family="codex", state="failed", sha="")
    _result(root, audit, round_id=rid, family="codex", state="success", sha="f" * 64)
    r = _ledger(root, audit, "--dump-json")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    latest = data["rounds"][rid]["latest_results"]["codex"]
    assert latest["result_state"] == "success"
    assert latest["output_sha256"] == "f" * 64


def test_round_exists_single_skips_seq_continuity(tmp_path: Path) -> None:
    """序號缺號時 --has-open rc=2 但 --round-exists-single 仍 rc=0。"""
    root, audit = _setup_repo(tmp_path)
    rec = {
        "event": "committee_round_open",
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "sequence": 3,  # gap
        "producer": "audit_append.sh",
        "origin_script": "committee_run.sh",
        "actor": "test",
        "ts": "2026-07-29T00:00:00Z",
        "round_id": "exists-gap",
        "task_id": "t",
        "brief_path": "handoffs/b.md",
        "brief_sha256": "a" * 64,
        "brief_sha256_norm": "b" * 64,
        "lock_mode": "discovery",
        "participants": ["codex"],
        "expected_outputs": {"codex": "handoffs/x.md"},
        "session_name": "eg",
    }
    _write_raw(audit, [json.dumps(rec, ensure_ascii=False, sort_keys=True)])
    h = _ledger(root, audit, "--has-open")
    assert h.returncode == 2
    e = _ledger(root, audit, "--round-exists-single", "exists-gap")
    assert e.returncode == 0, e.stderr


def test_abandoned_count_split_by_kind(tmp_path: Path) -> None:
    """--abandoned-count 依 abandon_kind 分開兩個數字。"""
    root, audit = _setup_repo(tmp_path)
    # open + abandon x2 different kinds
    for i, (sess, kind) in enumerate(
        (
            ("ab1", "no-findings-expected"),
            ("ab2", "collection-failed"),
            ("ab3", "no-findings-expected"),
        ),
        start=1,
    ):
        rid = f"r-ab-{i}"
        _open(root, audit, round_id=rid, session=sess, participants=["codex"])
        _append(
            root,
            audit,
            "--event",
            "debt_abandon",
            "--field",
            f"round_id={rid}",
            "--field",
            f"abandon_kind={kind}",
            "--field",
            "reason=" + ("x" * 25),
            "--field",
            "approver=alice",
            "--field",
            "actor=test",
            "--field",
            "origin_script=debt_clear.sh",
        )
    r = _ledger(root, audit, "--abandoned-count")
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "no-findings-expected 2 筆" in out
    assert "collection-failed 1 筆" in out


def test_cutoff_override_requires_harness(tmp_path: Path) -> None:
    """DEBT_CUTOFF_OVERRIDE 未綁 harness → fail-closed。"""
    root, audit = _setup_repo(tmp_path)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "DEBT_AUDIT_OVERRIDE": str(audit),
        # 故意不設 GOVERNANCE_TEST_HARNESS
        "DEBT_CUTOFF_OVERRIDE": "2099-01-01T00:00:00Z",
    }
    # 也會因 DEBT_AUDIT_OVERRIDE 無 harness 先擋
    r = helper.run_cmd(root / "scripts" / "debt_ledger.sh", "--has-open", env=env, cwd=root)
    assert r.returncode != 0


def test_debt_ledger_sourced_env_ignored_missing_audit(tmp_path: Path) -> None:
    """ASSERT debt_ledger WHEN env=DEBT_LEDGER_SOURCED=1 audit=missing THEN rc=2

    外部可設的 env 不得繞過 CLI；行為須與未設時完全相同。
    """
    root, audit = _setup_repo(tmp_path)
    missing = root / "no-such-audit.log"
    env_with = _hermetic_env(missing, DEBT_LEDGER_SOURCED="1")
    env_without = _hermetic_env(missing)
    r1 = helper.run_cmd(root / "scripts" / "debt_ledger.sh", "--has-open", env=env_with, cwd=root)
    r2 = helper.run_cmd(root / "scripts" / "debt_ledger.sh", "--has-open", env=env_without, cwd=root)
    assert r1.returncode == 2, r1.stderr
    assert r2.returncode == 2, r2.stderr


def test_debt_ledger_sourced_env_ignored_has_open(tmp_path: Path) -> None:
    """ASSERT debt_ledger WHEN env=DEBT_LEDGER_SOURCED=1 audit=has_open THEN rc=1"""
    root, audit = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    _open(root, audit, round_id=rid, session="src-open", participants=["codex"])
    env_with = _hermetic_env(audit, DEBT_LEDGER_SOURCED="1")
    env_without = _hermetic_env(audit)
    r1 = helper.run_cmd(root / "scripts" / "debt_ledger.sh", "--has-open", env=env_with, cwd=root)
    r2 = helper.run_cmd(root / "scripts" / "debt_ledger.sh", "--has-open", env=env_without, cwd=root)
    assert r1.returncode == 1, r1.stderr + r1.stdout
    assert r2.returncode == 1, r2.stderr + r2.stdout


def test_abandoned_count_empty_enum_fail_closed(tmp_path: Path) -> None:
    """registry enums.abandon_kind 空／缺失 → --abandoned-count rc≠0（無硬編 fallback）。"""
    root, audit = _setup_repo(tmp_path)
    reg_path = root / "scripts" / "audit_events.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["enums"]["abandon_kind"] = []
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = _ledger(root, audit, "--abandoned-count")
    assert r.returncode == 2
    assert "abandon_kind" in (r.stderr or "") or "恰兩值" in (r.stderr or "")


def test_round_exists_single_rejects_duplicate_open(tmp_path: Path) -> None:
    """同一 round 兩筆 open → --round-exists-single rc=2（非恰一筆）。"""
    root, audit = _setup_repo(tmp_path)
    rid = "dup-exists"
    lines = []
    for i, sess in enumerate(("s-a", "s-b"), start=1):
        rec = {
            "event": "committee_round_open",
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "sequence": i,
            "producer": "audit_append.sh",
            "origin_script": "committee_run.sh",
            "actor": "test",
            "ts": "2026-07-29T00:00:00Z",
            "round_id": rid,
            "task_id": "t",
            "brief_path": "handoffs/b.md",
            "brief_sha256": "a" * 64,
            "brief_sha256_norm": "b" * 64,
            "lock_mode": "discovery",
            "participants": ["codex"],
            "expected_outputs": {"codex": "handoffs/x.md"},
            "session_name": sess,
        }
        lines.append(json.dumps(rec, ensure_ascii=False, sort_keys=True))
    _write_raw(audit, lines)
    e = _ledger(root, audit, "--round-exists-single", rid)
    assert e.returncode == 2
    assert "恰一筆" in (e.stderr or "") or "兩筆" in (e.stderr or "") or "非恰" in (e.stderr or "")


def test_mutation_malformed_json_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 三態：略過壞 JSON → 假綠；restore 後再紅。

    探針經 monkeypatch 把 helper.DEBT_LEDGER_TARGET 指到隔離副本（真碰到待測系統）。
    同時覆蓋「無 debt-marker 的 `{not-json}`」（P1-01 形態）。
    """
    root, audit = _setup_repo(tmp_path)
    # 核心已抽至 _debt_ledger_core.py；探針變異隔離副本的核心（debt_ledger.sh 只轉調）
    core = root / "scripts" / "_debt_ledger_core.py"
    script = root / "scripts" / "debt_ledger.sh"
    monkeypatch.setattr(helper, "DEBT_LEDGER_TARGET", script)
    original = core.read_text(encoding="utf-8")
    # anchor：json.loads 失敗 → sys.exit(2)（所有 { 行共用）
    old = (
        '                print(\n'
        '                    f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}",\n'
        '                    file=sys.stderr,\n'
        '                )\n'
        '                sys.exit(2)'
    )
    new = (
        '                print(\n'
        '                    f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}",\n'
        '                    file=sys.stderr,\n'
        '                )\n'
        '                continue  # MUTANT: swallow malformed'
    )
    assert old in original, "mutation anchor missing"
    # P1-01 形態：無 debt-marker + 以 } 結尾的壞 JSON
    audit.write_text("{not-json}\n", encoding="utf-8")

    def _run_ledger() -> int:
        r = helper.run_debt_ledger(
            "--has-open",
            env=_hermetic_env(audit),
            cwd=root,
        )
        return r.returncode

    assert _run_ledger() == 2
    core.write_text(original.replace(old, new, 1), encoding="utf-8")
    assert _run_ledger() == 0, "mutant 應靜默略過壞 JSON 變假綠"
    core.write_text(original, encoding="utf-8")
    assert _run_ledger() == 2
