"""P1-6 B4 Task 2.2：debt_clear.sh 銷帳六項 + --abandon 逃生口。

驗收對齊 SPEC Task 2.2 驗證段（含死鎖修法 oracle、mode=discovery、sha 不符）。
hermetic：一律走 _debt_probe_helper（傳 env 即完整置換）。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.governance import _debt_probe_helper as helper

REPO_ROOT = Path(__file__).resolve().parents[2]


def _hermetic_env(audit: Path, **extra: str) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C"),
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
    }
    env.update(extra)
    return env


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _finding(fid: str = "CODEX-R1-P0-01") -> str:
    d = hashlib.sha256(fid.encode()).hexdigest()[:12]
    return (
        f"## {fid}\n\n"
        f"**斷言**: clear test assert\n\n"
        f"**碼證**: path:1\n\n"
        f"**來源摘要**: sources/review-codex.md#{d}\n"
    )


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in (
        "debt_clear.sh",
        "debt_ledger.sh",
        "_debt_ledger_core.py",
        "audit_append.sh",
        "audit_events.json",
        "completeness_check.sh",
        "governance_families.json",
    ):
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
            if name.endswith(".sh"):
                (scripts / name).chmod(0o755)
    # completeness 可能依賴其他腳本片段；複製 helpers if present
    for extra in ("load_governance_families.sh",):
        src = REPO_ROOT / "scripts" / extra
        if src.is_file():
            shutil.copy2(src, scripts / extra)
    audit = root / ".claude" / "gate" / "audit.log"
    audit.parent.mkdir(parents=True)
    audit.write_text("", encoding="utf-8")
    (root / "handoffs").mkdir(parents=True, exist_ok=True)
    return root, audit


def _append(root: Path, audit: Path, *args: str) -> None:
    r = helper.run_cmd(
        root / "scripts" / "audit_append.sh",
        *args,
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert r.returncode == 0, f"append fail rc={r.returncode} err={r.stderr!r}"


def _open_round(
    root: Path,
    audit: Path,
    *,
    round_id: str,
    session: str,
    participants: list[str],
) -> None:
    parts = json.dumps(participants, ensure_ascii=False)
    outs = {f: f"handoffs/{session}-{f}.md" for f in participants}
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
        "task_id=t-clear",
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
        "actor=test",
        "--field",
        "origin_script=committee_run.sh",
    )


def _write_output(root: Path, session: str, family: str, body: str) -> tuple[Path, str]:
    p = root / "handoffs" / f"{session}-{family}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p, _sha256_file(p)


def _result(
    root: Path,
    audit: Path,
    *,
    round_id: str,
    family: str,
    out_path: str,
    out_sha: str,
    state: str = "success",
) -> None:
    _append(
        root,
        audit,
        "--event",
        "committee_family_result",
        "--field",
        f"round_id={round_id}",
        "--field",
        f"family={family}",
        "--field",
        "attempt_id=att-1",
        "--field",
        "cli_rc=0",
        "--field",
        f"output_path={out_path}",
        "--field",
        f"output_sha256={out_sha}",
        "--field",
        f"result_state={state}",
        "--field",
        "actor=test",
        "--field",
        "origin_script=cx_run.sh",
    )


def _build_session(
    root: Path,
    *,
    session: str,
    round_id: str,
    families: list[str],
    mode: str = "review",
    bodies: dict[str, str] | None = None,
    roster: list[str] | None = None,
) -> Path:
    """建立 handoffs/reconcile/<session> 含 sources + synth + lock。"""
    sess = root / "handoffs" / "reconcile" / session
    sources = sess / "sources"
    sources.mkdir(parents=True)
    entries = []
    fams = roster if roster is not None else list(families)
    for fam in families:
        body = (bodies or {}).get(fam) or _finding(f"{fam.upper()}-R1-P0-01")
        # basename 須 *-<family>.md
        fname = f"review-{fam}.md"
        p = sources / fname
        p.write_text(body, encoding="utf-8")
        entries.append(
            {
                "realpath": str(p.resolve()),
                "sha256": _sha256_file(p),
                "family": fam,
            }
        )
    # synth 含全部 finding
    synth_parts = []
    for fam in families:
        synth_parts.append((bodies or {}).get(fam) or _finding(f"{fam.upper()}-R1-P0-01"))
    (sess / "synth.md").write_text("\n".join(synth_parts), encoding="utf-8")
    lock = {
        "version": 1,
        "session_id": session,
        "round_id": round_id,
        "expected_roster": fams,
        "sources": sorted(entries, key=lambda e: e["realpath"]),
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
        "mode": mode,
    }
    lock_path = sess / "sources.lock"
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return lock_path


def _clear(root: Path, audit: Path, *args: str):
    return helper.run_cmd(
        root / "scripts" / "debt_clear.sh",
        *args,
        env=_hermetic_env(audit),
        cwd=root,
    )


def _ledger(root: Path, audit: Path, *args: str):
    return helper.run_cmd(
        root / "scripts" / "debt_ledger.sh",
        *args,
        env=_hermetic_env(audit),
        cwd=root,
    )


def _happy_path_prep(
    root: Path,
    audit: Path,
    *,
    session: str = "sess-ok",
    families: list[str] | None = None,
    mode: str = "review",
    roster: list[str] | None = None,
) -> tuple[str, Path]:
    families = families or ["codex", "composer"]
    rid = str(uuid.uuid4())
    _open_round(root, audit, round_id=rid, session=session, participants=families)
    for fam in families:
        body = _finding(f"{fam.upper()}-R1-P0-01")
        p, sha = _write_output(root, session, fam, body)
        rel = str(p.relative_to(root))
        _result(root, audit, round_id=rid, family=fam, out_path=rel, out_sha=sha)
    lock = _build_session(
        root,
        session=session,
        round_id=rid,
        families=families,
        mode=mode,
        roster=roster,
    )
    return rid, lock


# ── 銷帳 happy / 負例 ───────────────────────────────────


def test_clear_happy_path(tmp_path: Path) -> None:
    root, audit = _setup(tmp_path)
    rid, lock = _happy_path_prep(root, audit, session="happy")
    r = _clear(
        root,
        audit,
        "--round-id",
        rid,
        "--session",
        "happy",
        "--lock",
        str(lock),
    )
    assert r.returncode == 0, r.stderr + r.stdout
    h = _ledger(root, audit, "--has-open")
    assert h.returncode == 0
    # 事件含 lock_sha256
    lines = [
        json.loads(ln)
        for ln in audit.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("{")
    ]
    clears = [x for x in lines if x.get("event") == "committee_debt_clear"]
    assert len(clears) == 1
    assert clears[0].get("lock_sha256")
    assert clears[0]["round_id"] == rid


def test_clear_wrong_round_id_binding(tmp_path: Path) -> None:
    """拿 A 輪 lock 銷 B 輪 → rc≠0。"""
    root, audit = _setup(tmp_path)
    rid_a, lock_a = _happy_path_prep(root, audit, session="sess-a")
    rid_b, _ = _happy_path_prep(root, audit, session="sess-b")
    r = _clear(
        root,
        audit,
        "--round-id",
        rid_b,
        "--session",
        "sess-a",
        "--lock",
        str(lock_a),
    )
    assert r.returncode != 0
    assert "identity" in (r.stderr or "").lower() or "binding" in (r.stderr or "").lower() or "round_id" in (
        r.stderr or ""
    )


def test_clear_discovery_mode_rejected(tmp_path: Path) -> None:
    """ASSERT debt_clear WHEN lock.mode=discovery THEN rc!=0"""
    root, audit = _setup(tmp_path)
    rid, lock = _happy_path_prep(root, audit, session="disc", mode="discovery")
    r = _clear(
        root,
        audit,
        "--round-id",
        rid,
        "--session",
        "disc",
        "--lock",
        str(lock),
    )
    assert r.returncode != 0
    assert "review" in (r.stderr or "")


def test_clear_roster_mismatch(tmp_path: Path) -> None:
    """lock roster 與 open.participants 集合不相等 → rc≠0，且訊號屬 _assert_roster_equals。

    構造：open 兩家、lock roster 僅一家、synth/sources 僅該家 → completeness 綠，
    擋在 roster 集合不相等（非 completeness「roster 缺席」假綠）。
    """
    root, audit = _setup(tmp_path)
    session = "roster-mis"
    families_open = ["codex", "composer"]
    families_lock = ["codex"]
    rid = str(uuid.uuid4())
    _open_round(root, audit, round_id=rid, session=session, participants=families_open)
    for fam in families_open:
        body = _finding(f"{fam.upper()}-R1-P0-01")
        p, sha = _write_output(root, session, fam, body)
        rel = str(p.relative_to(root))
        _result(root, audit, round_id=rid, family=fam, out_path=rel, out_sha=sha)
    # lock / sources / synth 僅 roster 一家，讓 completeness 通過
    lock = _build_session(
        root,
        session=session,
        round_id=rid,
        families=families_lock,
        mode="review",
        roster=families_lock,
    )
    r = _clear(
        root,
        audit,
        "--round-id",
        rid,
        "--session",
        session,
        "--lock",
        str(lock),
    )
    assert r.returncode != 0
    err = r.stderr or ""
    assert "集合不相等" in err or "roster 集合" in err
    assert "缺席" not in err  # 不得被 completeness 先擋


def test_clear_completeness_fail(tmp_path: Path) -> None:
    """completeness rc≠0 → 拒銷。"""
    root, audit = _setup(tmp_path)
    rid, lock = _happy_path_prep(root, audit, session="comp-fail", families=["codex"])
    # 破壞 synth：漏 finding
    sess = root / "handoffs" / "reconcile" / "comp-fail"
    (sess / "synth.md").write_text("# empty synth no findings\n", encoding="utf-8")
    r = _clear(
        root,
        audit,
        "--round-id",
        rid,
        "--session",
        "comp-fail",
        "--lock",
        str(lock),
    )
    assert r.returncode != 0
    assert "completeness" in (r.stderr or "").lower() or "COMPLETENESS" in (r.stderr or "")


def test_clear_output_tampered_sha(tmp_path: Path) -> None:
    """某家產出檔交件後被改動 → rc≠0。"""
    root, audit = _setup(tmp_path)
    rid, lock = _happy_path_prep(root, audit, session="tamp", families=["codex"])
    # 改產出檔
    out = root / "handoffs" / "tamp-codex.md"
    out.write_text(out.read_text(encoding="utf-8") + "\nTAMPER\n", encoding="utf-8")
    r = _clear(
        root,
        audit,
        "--round-id",
        rid,
        "--session",
        "tamp",
        "--lock",
        str(lock),
    )
    assert r.returncode != 0
    assert "sha" in (r.stderr or "").lower() or "改動" in (r.stderr or "")


def test_clear_idempotent_noop(tmp_path: Path) -> None:
    """重複銷帳 → 冪等 no-op。"""
    root, audit = _setup(tmp_path)
    rid, lock = _happy_path_prep(root, audit, session="idem")
    r1 = _clear(root, audit, "--round-id", rid, "--session", "idem", "--lock", str(lock))
    assert r1.returncode == 0, r1.stderr
    r2 = _clear(root, audit, "--round-id", rid, "--session", "idem", "--lock", str(lock))
    assert r2.returncode == 0, r2.stderr
    assert "no-op" in (r2.stdout or "") or "CLOSED" in (r2.stdout or "")
    lines = [
        json.loads(ln)
        for ln in audit.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("{")
    ]
    clears = [x for x in lines if x.get("event") == "committee_debt_clear"]
    assert len(clears) == 1  # 未再寫


# ── abandon ─────────────────────────────────────────────


def test_abandon_missing_fields(tmp_path: Path) -> None:
    """--abandon 缺 reason/approver/kind → rc≠0。"""
    root, audit = _setup(tmp_path)
    rid, _ = _happy_path_prep(root, audit, session="ab-miss", families=["codex"])
    base = ["--abandon", "--round-id", rid]
    for args in (
        base + ["--kind", "collection-failed", "--reason", "x" * 25],  # 缺 approver
        base + ["--kind", "collection-failed", "--approver", "alice"],  # 缺 reason
        base + ["--reason", "x" * 25, "--approver", "alice"],  # 缺 kind
        base
        + [
            "--kind",
            "collection-failed",
            "--reason",
            "short",
            "--approver",
            "alice",
        ],  # reason 過短
    ):
        r = _clear(root, audit, *args)
        assert r.returncode != 0, f"should reject: {args}"


def test_abandon_open_no_deadline(tmp_path: Path) -> None:
    """--abandon 在 OPEN 未逾任何期限 → rc=0。"""
    root, audit = _setup(tmp_path)
    rid, _ = _happy_path_prep(root, audit, session="ab-ok", families=["codex"])
    r = _clear(
        root,
        audit,
        "--abandon",
        "--round-id",
        rid,
        "--kind",
        "no-findings-expected",
        "--reason",
        "x" * 25,
        "--approver",
        "alice",
    )
    assert r.returncode == 0, r.stderr
    st = _ledger(root, audit, "--round-state", rid)
    assert st.returncode == 0
    assert st.stdout.strip() == "ABANDONED"


def test_abandon_survives_sequence_gap(tmp_path: Path) -> None:
    """ASSERT debt_clear WHEN cmd=abandon audit=seq_gap round=single_open THEN rc=0"""
    root, audit = _setup(tmp_path)
    rid = "gap-abandon-round"
    rec = {
        "event": "committee_round_open",
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "sequence": 5,  # gap
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
        "session_name": "gap-ab",
    }
    audit.write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    h = _ledger(root, audit, "--has-open")
    assert h.returncode == 2
    r = _clear(
        root,
        audit,
        "--abandon",
        "--round-id",
        rid,
        "--kind",
        "collection-failed",
        "--reason",
        "y" * 25,
        "--approver",
        "bob",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    # abandon 事件寫入
    lines = [
        json.loads(ln)
        for ln in audit.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("{")
    ]
    abs_ = [x for x in lines if x.get("event") == "debt_abandon"]
    assert len(abs_) == 1
    assert abs_[0]["abandon_kind"] == "collection-failed"


def test_abandon_rejects_duplicate_open(tmp_path: Path) -> None:
    """ASSERT debt_clear WHEN cmd=abandon round=duplicate_open THEN rc!=0

    --abandon 只豁免序號連續性，不得吞掉 duplicate-open 語意 fail-closed。
    """
    root, audit = _setup(tmp_path)
    rid = "dup-abandon-round"
    lines = []
    for i, sess in enumerate(("dup-a", "dup-b"), start=1):
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
    audit.write_text("\n".join(lines) + "\n", encoding="utf-8")
    h = _ledger(root, audit, "--has-open")
    assert h.returncode == 2
    r = _clear(
        root,
        audit,
        "--abandon",
        "--round-id",
        rid,
        "--kind",
        "collection-failed",
        "--reason",
        "y" * 25,
        "--approver",
        "bob",
    )
    assert r.returncode != 0
    # 不得寫入 debt_abandon
    written = [
        json.loads(ln)
        for ln in audit.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("{")
    ]
    assert not any(x.get("event") == "debt_abandon" for x in written)


def test_clear_lock_session_mismatch(tmp_path: Path) -> None:
    """顯式 --lock 配錯 --session → rc≠0（session_id 綁定）。"""
    root, audit = _setup(tmp_path)
    rid, lock = _happy_path_prep(root, audit, session="sess-lock-a", families=["codex"])
    # 另建一個 session 名的 empty dir 暗示錯配
    r = _clear(
        root,
        audit,
        "--round-id",
        rid,
        "--session",
        "sess-lock-WRONG",
        "--lock",
        str(lock),
    )
    assert r.returncode != 0
    err = (r.stderr or "") + (r.stdout or "")
    assert "session" in err.lower() or "不一致" in err


def test_abandoned_then_clear_rejected(tmp_path: Path) -> None:
    """ABANDONED 後再銷 → rc≠0。"""
    root, audit = _setup(tmp_path)
    rid, lock = _happy_path_prep(root, audit, session="ab-then-clear", families=["codex"])
    r1 = _clear(
        root,
        audit,
        "--abandon",
        "--round-id",
        rid,
        "--kind",
        "collection-failed",
        "--reason",
        "z" * 25,
        "--approver",
        "carol",
    )
    assert r1.returncode == 0, r1.stderr
    r2 = _clear(
        root,
        audit,
        "--round-id",
        rid,
        "--session",
        "ab-then-clear",
        "--lock",
        str(lock),
    )
    assert r2.returncode != 0
    assert "ABANDONED" in (r2.stderr or "")


def test_mutation_mode_review_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 三態 ③：拔掉 mode=review 守衛 → discovery 假綠。"""
    root, audit = _setup(tmp_path)
    script = root / "scripts" / "debt_clear.sh"
    monkeypatch.setattr(helper, "DEBT_CLEAR_TARGET", script)
    original = script.read_text(encoding="utf-8")
    old = '_assert_lock_mode_is_review() {\n  local lock="$1"'
    new = '_assert_lock_mode_is_review() {\n  return 0\n  local lock="$1"'
    assert old in original

    rid, lock = _happy_path_prep(
        root, audit, session="mut-mode", mode="discovery", families=["codex"]
    )
    base = helper.run_debt_clear(
        "--round-id",
        rid,
        "--session",
        "mut-mode",
        "--lock",
        str(lock),
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert base.returncode != 0
    assert "review" in (base.stderr or "")

    script.write_text(original.replace(old, new, 1), encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid2, lock2 = _happy_path_prep(
        root, audit, session="mut-mode2", mode="discovery", families=["codex"]
    )
    mut = helper.run_debt_clear(
        "--round-id",
        rid2,
        "--session",
        "mut-mode2",
        "--lock",
        str(lock2),
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert mut.returncode == 0, f"mutant should pass discovery: {mut.stderr}"

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid3, lock3 = _happy_path_prep(
        root, audit, session="mut-mode3", mode="discovery", families=["codex"]
    )
    rest = helper.run_debt_clear(
        "--round-id",
        rid3,
        "--session",
        "mut-mode3",
        "--lock",
        str(lock3),
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert rest.returncode != 0


def test_mutation_open_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 三態 ①：拔掉 OPEN 守衛 → ABANDONED 輪可假銷。"""
    root, audit = _setup(tmp_path)
    script = root / "scripts" / "debt_clear.sh"
    monkeypatch.setattr(helper, "DEBT_CLEAR_TARGET", script)
    original = script.read_text(encoding="utf-8")
    old = '_assert_round_is_OPEN() {\n  local rid="$1"'
    new = '_assert_round_is_OPEN() {\n  return 0\n  local rid="$1"'
    assert old in original

    # baseline: abandon first then clear → 紅 + ABANDONED
    rid, lock = _happy_path_prep(root, audit, session="mut-open", families=["codex"])
    ab = helper.run_debt_clear(
        "--abandon",
        "--round-id",
        rid,
        "--kind",
        "collection-failed",
        "--reason",
        "z" * 25,
        "--approver",
        "carol",
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert ab.returncode == 0, ab.stderr
    base = helper.run_debt_clear(
        "--round-id",
        rid,
        "--session",
        "mut-open",
        "--lock",
        str(lock),
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert base.returncode != 0
    assert "ABANDONED" in (base.stderr or "")

    script.write_text(original.replace(old, new, 1), encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid2, lock2 = _happy_path_prep(root, audit, session="mut-open2", families=["codex"])
    ab2 = helper.run_debt_clear(
        "--abandon",
        "--round-id",
        rid2,
        "--kind",
        "collection-failed",
        "--reason",
        "z" * 25,
        "--approver",
        "carol",
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert ab2.returncode == 0, ab2.stderr
    mut = helper.run_debt_clear(
        "--round-id",
        rid2,
        "--session",
        "mut-open2",
        "--lock",
        str(lock2),
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert mut.returncode == 0, f"mutant 應讓 ABANDONED 假銷: {mut.stderr}"

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid3, lock3 = _happy_path_prep(root, audit, session="mut-open3", families=["codex"])
    ab3 = helper.run_debt_clear(
        "--abandon",
        "--round-id",
        rid3,
        "--kind",
        "collection-failed",
        "--reason",
        "z" * 25,
        "--approver",
        "carol",
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert ab3.returncode == 0
    rest = helper.run_debt_clear(
        "--round-id",
        rid3,
        "--session",
        "mut-open3",
        "--lock",
        str(lock3),
        env=_hermetic_env(audit),
        cwd=root,
    )
    assert rest.returncode != 0
    assert "ABANDONED" in (rest.stderr or "")


def test_mutation_completeness_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 三態 ②：拔掉 completeness 守衛 → 空 synth 假銷。"""
    root, audit = _setup(tmp_path)
    script = root / "scripts" / "debt_clear.sh"
    monkeypatch.setattr(helper, "DEBT_CLEAR_TARGET", script)
    original = script.read_text(encoding="utf-8")
    old = '_run_completeness() {\n  local lock="$1"'
    new = '_run_completeness() {\n  return 0\n  local lock="$1"'
    assert old in original

    def _prep_broken(sess: str):
        rid, lock = _happy_path_prep(root, audit, session=sess, families=["codex"])
        (root / "handoffs" / "reconcile" / sess / "synth.md").write_text(
            "# empty synth no findings\n", encoding="utf-8"
        )
        return rid, lock

    audit.write_text("", encoding="utf-8")
    rid, lock = _prep_broken("mut-comp")
    base = helper.run_debt_clear(
        "--round-id", rid, "--session", "mut-comp", "--lock", str(lock),
        env=_hermetic_env(audit), cwd=root,
    )
    assert base.returncode != 0
    assert "completeness" in (base.stderr or "").lower() or "COMPLETENESS" in (base.stderr or "")

    script.write_text(original.replace(old, new, 1), encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid2, lock2 = _prep_broken("mut-comp2")
    mut = helper.run_debt_clear(
        "--round-id", rid2, "--session", "mut-comp2", "--lock", str(lock2),
        env=_hermetic_env(audit), cwd=root,
    )
    assert mut.returncode == 0, f"mutant 應假綠: {mut.stderr}"

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid3, lock3 = _prep_broken("mut-comp3")
    rest = helper.run_debt_clear(
        "--round-id", rid3, "--session", "mut-comp3", "--lock", str(lock3),
        env=_hermetic_env(audit), cwd=root,
    )
    assert rest.returncode != 0


def test_mutation_identity_binding_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 三態 ④：拔掉 identity binding → 錯 round 假銷。"""
    root, audit = _setup(tmp_path)
    script = root / "scripts" / "debt_clear.sh"
    monkeypatch.setattr(helper, "DEBT_CLEAR_TARGET", script)
    original = script.read_text(encoding="utf-8")
    old = '_assert_identity_binding() {\n  local lock="$1"\n  local rid="$2"'
    new = '_assert_identity_binding() {\n  return 0\n  local lock="$1"\n  local rid="$2"'
    assert old in original

    rid_a, lock_a = _happy_path_prep(root, audit, session="mut-id-a", families=["codex"])
    rid_b, _ = _happy_path_prep(root, audit, session="mut-id-b", families=["codex"])
    base = helper.run_debt_clear(
        "--round-id", rid_b, "--session", "mut-id-a", "--lock", str(lock_a),
        env=_hermetic_env(audit), cwd=root,
    )
    assert base.returncode != 0
    assert "identity" in (base.stderr or "").lower() or "binding" in (base.stderr or "").lower() or "round_id" in (
        base.stderr or ""
    )

    script.write_text(original.replace(old, new, 1), encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid_a2, lock_a2 = _happy_path_prep(root, audit, session="mut-id-a2", families=["codex"])
    rid_b2, _ = _happy_path_prep(root, audit, session="mut-id-b2", families=["codex"])
    mut = helper.run_debt_clear(
        "--round-id", rid_b2, "--session", "mut-id-a2", "--lock", str(lock_a2),
        env=_hermetic_env(audit), cwd=root,
    )
    assert mut.returncode == 0, f"mutant 應假綠: {mut.stderr}"

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid_a3, lock_a3 = _happy_path_prep(root, audit, session="mut-id-a3", families=["codex"])
    rid_b3, _ = _happy_path_prep(root, audit, session="mut-id-b3", families=["codex"])
    rest = helper.run_debt_clear(
        "--round-id", rid_b3, "--session", "mut-id-a3", "--lock", str(lock_a3),
        env=_hermetic_env(audit), cwd=root,
    )
    assert rest.returncode != 0


def test_mutation_roster_equals_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 三態 ④附加：拔掉 roster 集合相等 → 假銷。"""
    root, audit = _setup(tmp_path)
    script = root / "scripts" / "debt_clear.sh"
    monkeypatch.setattr(helper, "DEBT_CLEAR_TARGET", script)
    original = script.read_text(encoding="utf-8")
    old = '_assert_roster_equals() {\n  local lock="$1"\n  local rid="$2"'
    new = '_assert_roster_equals() {\n  return 0\n  local lock="$1"\n  local rid="$2"'
    assert old in original

    def _prep_mismatch(sess: str):
        families_open = ["codex", "composer"]
        families_lock = ["codex"]
        rid = str(uuid.uuid4())
        _open_round(root, audit, round_id=rid, session=sess, participants=families_open)
        for fam in families_open:
            body = _finding(f"{fam.upper()}-R1-P0-01")
            p, sha = _write_output(root, sess, fam, body)
            _result(root, audit, round_id=rid, family=fam, out_path=str(p.relative_to(root)), out_sha=sha)
        lock = _build_session(
            root, session=sess, round_id=rid, families=families_lock, mode="review", roster=families_lock
        )
        return rid, lock

    audit.write_text("", encoding="utf-8")
    rid, lock = _prep_mismatch("mut-rost")
    base = helper.run_debt_clear(
        "--round-id", rid, "--session", "mut-rost", "--lock", str(lock),
        env=_hermetic_env(audit), cwd=root,
    )
    assert base.returncode != 0
    assert "集合不相等" in (base.stderr or "") or "roster" in (base.stderr or "").lower()

    script.write_text(original.replace(old, new, 1), encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid2, lock2 = _prep_mismatch("mut-rost2")
    mut = helper.run_debt_clear(
        "--round-id", rid2, "--session", "mut-rost2", "--lock", str(lock2),
        env=_hermetic_env(audit), cwd=root,
    )
    assert mut.returncode == 0, f"mutant 應假綠: {mut.stderr}"

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid3, lock3 = _prep_mismatch("mut-rost3")
    rest = helper.run_debt_clear(
        "--round-id", rid3, "--session", "mut-rost3", "--lock", str(lock3),
        env=_hermetic_env(audit), cwd=root,
    )
    assert rest.returncode != 0


def test_mutation_family_sha_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation 三態 ⑤：拔掉 family success+sha 守衛 → 被改動產出假銷。"""
    root, audit = _setup(tmp_path)
    script = root / "scripts" / "debt_clear.sh"
    monkeypatch.setattr(helper, "DEBT_CLEAR_TARGET", script)
    original = script.read_text(encoding="utf-8")
    old = '_assert_all_families_success_and_sha_match() {\n  local rid="$1"'
    new = '_assert_all_families_success_and_sha_match() {\n  return 0\n  local rid="$1"'
    assert old in original

    def _prep_tampered(sess: str):
        rid, lock = _happy_path_prep(root, audit, session=sess, families=["codex"])
        out = root / "handoffs" / f"{sess}-codex.md"
        out.write_text(out.read_text(encoding="utf-8") + "\nTAMPER\n", encoding="utf-8")
        return rid, lock

    audit.write_text("", encoding="utf-8")
    rid, lock = _prep_tampered("mut-sha")
    base = helper.run_debt_clear(
        "--round-id", rid, "--session", "mut-sha", "--lock", str(lock),
        env=_hermetic_env(audit), cwd=root,
    )
    assert base.returncode != 0
    assert "sha" in (base.stderr or "").lower() or "改動" in (base.stderr or "")

    script.write_text(original.replace(old, new, 1), encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid2, lock2 = _prep_tampered("mut-sha2")
    mut = helper.run_debt_clear(
        "--round-id", rid2, "--session", "mut-sha2", "--lock", str(lock2),
        env=_hermetic_env(audit), cwd=root,
    )
    assert mut.returncode == 0, f"mutant 應假綠: {mut.stderr}"

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    audit.write_text("", encoding="utf-8")
    rid3, lock3 = _prep_tampered("mut-sha3")
    rest = helper.run_debt_clear(
        "--round-id", rid3, "--session", "mut-sha3", "--lock", str(lock3),
        env=_hermetic_env(audit), cwd=root,
    )
    assert rest.returncode != 0


# ── 1b --rebuild 實跑（隔離 repo；harness=unset 為關鍵）──────────


def _rebuild_harness(tmp_path: Path) -> tuple[Path, Path, Path]:
    """隔離 repo：reconcile_build + write_sources_lock + registry + 空 audit。

    故意不設 GOVERNANCE_TEST_HARNESS（證偽「正式路徑不可達」）。
    """
    root = tmp_path / "rebuild-repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in (
        "reconcile_build.sh",
        "write_sources_lock.sh",
        "completeness_check.sh",
        "audit_events.json",
        "governance_families.json",
        "load_governance_families.sh",
    ):
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
            if name.endswith(".sh"):
                (scripts / name).chmod(0o755)
    audit = root / ".claude" / "gate" / "audit.log"
    audit.parent.mkdir(parents=True)
    audit.write_text("", encoding="utf-8")
    return root, scripts / "reconcile_build.sh", audit


def _rebuild_finding(family: str) -> str:
    upper = family.upper()
    return (
        f"## {upper}-R1-P0-01\n\n"
        "**斷言**: rebuild identity must preserve sources and hashes.\n\n"
        "**碼證**: scripts/reconcile_build.sh:1\n\n"
        f"**來源摘要**: sources/review-{family}.md#aaaaaaaaaaaa\n"
    )


def _rebuild_audit_open(
    audit: Path,
    session_name: str,
    round_id: str,
    *,
    extra_opens: list[tuple[str, str]] | None = None,
    closed: bool = False,
) -> None:
    records = [
        {
            "event": "committee_round_open",
            "sequence": 1,
            "round_id": round_id,
            "session_name": session_name,
        }
    ]
    seq = 1
    for sess, rid in extra_opens or []:
        seq += 1
        records.append(
            {
                "event": "committee_round_open",
                "sequence": seq,
                "round_id": rid,
                "session_name": sess,
            }
        )
    if closed:
        seq += 1
        records.append(
            {
                "event": "committee_debt_clear",
                "sequence": seq,
                "round_id": round_id,
            }
        )
    audit.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


def _rebuild_run(script: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    """harness=unset：完整 env 不含 GOVERNANCE_TEST_HARNESS。"""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C"),
    }
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=str(script.parents[1]),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _seed_discovery_session(root: Path, reconcile: Path, session: str, families: list[str]) -> Path:
    """fresh discovery 建 session；回傳 lock path。"""
    src_files = []
    for fam in families:
        p = root / f"review-{fam}.md"
        p.write_text(_rebuild_finding(fam), encoding="utf-8")
        src_files.append(str(p))
    r = _rebuild_run(reconcile, session, "--mode", "discovery", *src_files)
    assert r.returncode == 0, r.stdout + r.stderr
    lock = root / "handoffs" / "reconcile" / session / "sources.lock"
    assert lock.is_file()
    return lock


def test_rebuild_1b_happy_path_harness_unset(tmp_path: Path) -> None:
    """ASSERT reconcile_build WHEN from=discovery to=review round=open audit=one
    rebuild=yes harness=unset THEN rc=0 AND lock.mode=review AND lock.round_id=nonempty
    AND lock.sources/hashes/roster unchanged.
    """
    root, reconcile, audit = _rebuild_harness(tmp_path)
    session = "b4-rebuild-happy"
    lock_path = _seed_discovery_session(root, reconcile, session, ["codex", "grok"])
    before = json.loads(lock_path.read_text(encoding="utf-8"))
    assert before["mode"] == "discovery"
    rid = "round-b4-rebuild-happy"
    _rebuild_audit_open(audit, session, rid)

    r = _rebuild_run(reconcile, session, "--mode", "review", "--rebuild")
    assert r.returncode == 0, r.stdout + r.stderr
    after = json.loads(lock_path.read_text(encoding="utf-8"))
    assert after["mode"] == "review"
    assert after.get("round_id") == rid and after["round_id"]
    assert after["sources"] == before["sources"]
    assert after["expected_roster"] == before["expected_roster"]
    assert [s["sha256"] for s in after["sources"]] == [s["sha256"] for s in before["sources"]]


def test_rebuild_1b_without_flag_rejected(tmp_path: Path) -> None:
    """ASSERT reconcile_build WHEN from=discovery to=review round=open audit=one rebuild=no THEN rc!=0"""
    root, reconcile, audit = _rebuild_harness(tmp_path)
    session = "b4-rebuild-noflag"
    _seed_discovery_session(root, reconcile, session, ["codex"])
    _rebuild_audit_open(audit, session, "round-noflag")
    # session 已存在且未帶 --rebuild → 拒覆寫
    src = root / "review-codex.md"
    r = _rebuild_run(reconcile, session, "--mode", "review", str(src))
    assert r.returncode != 0


def test_rebuild_1b_review_to_discovery_rejected(tmp_path: Path) -> None:
    """ASSERT reconcile_build WHEN from=review to=discovery rebuild=yes THEN rc!=0"""
    root, reconcile, audit = _rebuild_harness(tmp_path)
    session = "b4-rebuild-reverse"
    lock_path = _seed_discovery_session(root, reconcile, session, ["codex"])
    _rebuild_audit_open(audit, session, "round-rev")
    # 先升到 review
    up = _rebuild_run(reconcile, session, "--mode", "review", "--rebuild")
    assert up.returncode == 0, up.stdout + up.stderr
    assert json.loads(lock_path.read_text(encoding="utf-8"))["mode"] == "review"
    # 反向降級
    r = _rebuild_run(reconcile, session, "--mode", "discovery", "--rebuild")
    assert r.returncode != 0
    assert "review" in (r.stderr or r.stdout or "") or "discovery" in (r.stderr or r.stdout or "")


def test_rebuild_1b_closed_round_rejected(tmp_path: Path) -> None:
    """ASSERT reconcile_build WHEN from=discovery to=review round=closed rebuild=yes THEN rc!=0"""
    root, reconcile, audit = _rebuild_harness(tmp_path)
    session = "b4-rebuild-closed"
    _seed_discovery_session(root, reconcile, session, ["codex"])
    _rebuild_audit_open(audit, session, "round-closed", closed=True)
    r = _rebuild_run(reconcile, session, "--mode", "review", "--rebuild")
    assert r.returncode != 0


def test_rebuild_1b_audit_zero_rejected(tmp_path: Path) -> None:
    """ASSERT reconcile_build WHEN from=discovery to=review audit=zero rebuild=yes THEN rc!=0"""
    root, reconcile, audit = _rebuild_harness(tmp_path)
    session = "b4-rebuild-zero"
    _seed_discovery_session(root, reconcile, session, ["codex"])
    # audit 空
    audit.write_text("", encoding="utf-8")
    r = _rebuild_run(reconcile, session, "--mode", "review", "--rebuild")
    assert r.returncode != 0


def test_rebuild_1b_audit_many_rejected(tmp_path: Path) -> None:
    """ASSERT reconcile_build WHEN from=discovery to=review audit=many rebuild=yes THEN rc!=0"""
    root, reconcile, audit = _rebuild_harness(tmp_path)
    session = "b4-rebuild-many"
    _seed_discovery_session(root, reconcile, session, ["codex"])
    # 同 session_name 兩筆 open（不同 round）
    _rebuild_audit_open(
        audit,
        session,
        "round-many-1",
        extra_opens=[(session, "round-many-2")],
    )
    r = _rebuild_run(reconcile, session, "--mode", "review", "--rebuild")
    assert r.returncode != 0
