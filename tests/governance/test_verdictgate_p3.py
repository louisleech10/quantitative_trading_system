"""VERDICTGATE B3（Task 3.1／3.2／3.3）— 真 git 暫存 repo＋hook 實跑；每條 SPEC ASSERT 對應一個 test。

只跑本檔：venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = (
    "ticket_batch_check.sh", "audit_append.sh", "audit_events.json", "verification_claim_check.py",
    "governance_families.sh", "governance_families.json", "governance_roles.json", "governance_verdicts.json",
    "gate.sh", "gate_check.sh", "_gate_lex.sh", "debt_ledger.sh", "_debt_ledger_core.py", "template_check.sh",
    "completeness_check.sh", "reconcile_stamps_check.sh", "review_quorum_check.sh", "prev_review_resolve.sh",
    "verdictgate_check.sh", "verify_task_provenance.py", "stampable_artifacts.txt", "_role_gate.sh",
)
ZERO = "0" * 40


def _git(h: dict, *args: str, env_overlay: dict | None = None, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(h["env"]); env.update(env_overlay or {})
    return subprocess.run(["git", *args], cwd=h["root"], env=env, capture_output=True, text=True, check=False, input=stdin)


def _h(tmp_path: Path) -> dict:
    root = tmp_path / "repo"
    (root / "scripts" / "git_hooks").mkdir(parents=True)
    gate_dir = root / ".claude" / "gate"; gate_dir.mkdir(parents=True)
    audit = gate_dir / "audit.log"; audit.write_text("", encoding="utf-8")
    for n in _SCRIPTS:
        src = REPO_ROOT / "scripts" / n
        if src.is_file():
            shutil.copy2(src, root / "scripts" / n)
            if n.endswith(".sh"):
                (root / "scripts" / n).chmod(0o755)
    for hk in ("commit-msg", "post-commit", "pre-push"):
        shutil.copy2(REPO_ROOT / "scripts" / "git_hooks" / hk, root / "scripts" / "git_hooks" / hk)
        (root / "scripts" / "git_hooks" / hk).chmod(0o755)
    env = {"GOVERNANCE_TEST_HARNESS": "1", "DEBT_AUDIT_OVERRIDE": str(audit), "GATE_DIR_OVERRIDE": str(gate_dir),
           "PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "LANG": "C.UTF-8",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    h = {"root": root, "audit": audit, "gate_dir": gate_dir, "env": env}
    assert _git(h, "init", "-q", "-b", "main").returncode == 0
    assert _git(h, "config", "core.hooksPath", "scripts/git_hooks").returncode == 0
    (root / "README.md").write_text("base\n", encoding="utf-8")
    assert _git(h, "add", "-A").returncode == 0
    r = _git(h, "commit", "-q", "-m", "base")
    assert r.returncode == 0, r.stderr
    return h


def _stage(h: dict, *paths: str) -> None:
    for p in paths:
        f = h["root"] / p; f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {p} {time.time()}\n", encoding="utf-8")
    assert _git(h, "add", "-A").returncode == 0


def _commit(h: dict, msg: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return _git(h, "commit", "-q", *extra, "-m", msg)


def _token(h: dict, root: str, batch: int, age: int = 0) -> Path:
    t = h["gate_dir"] / f"impl.{root}-b{batch}.token"
    t.write_text(f"ts=x\nroot={root}\nbatch={batch}\n", encoding="utf-8")
    if age:
        os.utime(t, (time.time() - age, time.time() - age))
    return t


def _events(h: dict, name: str) -> list[dict]:
    return [json.loads(l) for l in h["audit"].read_text(encoding="utf-8").splitlines() if l.startswith("{") and json.loads(l).get("event") == name]


def _issue_token_event(h: dict, root: str, batch: int) -> None:
    r = subprocess.run(["bash", "scripts/audit_append.sh", "--event", "impl_token_issued", "--field", f"task_id={root}-impl-b{batch}-claude",
                        "--field", f"root={root}", "--field", f"batch={batch}", "--field", "family=claude", "--field", "actor=t",
                        "--field", "origin_script=gate.sh"], cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr


def _push_range(h: dict, rng: str) -> subprocess.CompletedProcess[str]:
    head = _git(h, "rev-parse", "HEAD").stdout.strip()
    return subprocess.run(["bash", "scripts/ticket_batch_check.sh", "--push-range", rng, "--local-sha", head],
                          cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False)


# ───────────── Task 3.2：commit-msg ─────────────

def test_32_prod_without_trailer_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/x.py")
    r = _commit(h, "feat: x")
    assert r.returncode != 0 and "Ticket-Batch" in r.stderr


def test_32_small_one_file_ok_and_post_commit_event(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/x.py")
    r = _commit(h, "feat: x\n\nTicket-Batch: small")
    assert r.returncode == 0, r.stderr
    ev = _events(h, "ticket_commit")
    assert len(ev) == 1 and ev[0]["trailer"] == "small" and ev[0]["prod_files"] == ["momentum/x.py"] and ev[0]["token_fresh"] == "null"


def test_32_small_five_files_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, *[f"momentum/f{i}.py" for i in range(5)])
    r = _commit(h, "feat: x\n\nTicket-Batch: small")
    assert r.returncode != 0 and "> 3" in r.stderr


def test_32_small_touching_factories_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/factories.py")
    r = _commit(h, "feat: x\n\nTicket-Batch: small")
    assert r.returncode != 0 and "factories" in r.stderr


def test_32_batch_trailer_token_absent_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/x.py")
    r = _commit(h, "feat: x\n\nTicket-Batch: ROOT/b2")
    assert r.returncode != 0 and "token" in r.stderr


def test_32_batch_trailer_token_fresh_ok_event_true(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/x.py"); _token(h, "ROOT", 2)
    r = _commit(h, "feat: x\n\nTicket-Batch: ROOT/b2")
    assert r.returncode == 0, r.stderr
    assert _events(h, "ticket_commit")[0]["token_fresh"] == "true"


def test_32_batch_trailer_token_expired_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/x.py"); _token(h, "ROOT", 2, age=1000)
    r = _commit(h, "feat: x\n\nTicket-Batch: ROOT/b2")
    assert r.returncode != 0 and "過期" in r.stderr


def test_32_docs_only_no_trailer_ok(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "docs/x.md")
    assert _commit(h, "docs: x").returncode == 0
    assert _events(h, "ticket_commit") == []


def test_32_skip_env_bypasses_but_leaves_audit(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/x.py")
    r = _commit(h, "feat: x", env_overlay=None) if False else _git(h, "commit", "-q", "-m", "feat: x", env_overlay={"GOVERNANCE_SKIP_COMMITMSG": "1"})
    assert r.returncode == 0, r.stderr
    assert any(e["hook"] == "commit-msg" for e in _events(h, "governance_bypass"))


def test_32_no_verify_skips_commit_msg_but_post_commit_still_emits_false(tmp_path: Path) -> None:
    """--no-verify 跳過 commit-msg 但不跳過 post-commit ⇒ 留 token_fresh=false 供 1c 擋。"""
    h = _h(tmp_path); _stage(h, "momentum/x.py")
    r = _commit(h, "feat: x\n\nTicket-Batch: ROOT/b2", "--no-verify")
    assert r.returncode == 0, r.stderr
    assert _events(h, "ticket_commit")[0]["token_fresh"] == "false"


def test_32_amend_retriggers_post_commit_new_sha(tmp_path: Path) -> None:
    h = _h(tmp_path); _stage(h, "momentum/x.py")
    assert _commit(h, "feat: x\n\nTicket-Batch: small").returncode == 0
    old = _git(h, "rev-parse", "HEAD").stdout.strip()
    _stage(h, "momentum/y.py")                                   # 有實質改動的 amend（同秒無改動之 amend 會得同 sha）
    assert _git(h, "commit", "-q", "--amend", "--no-edit").returncode == 0
    new = _git(h, "rev-parse", "HEAD").stdout.strip()
    shas = [e["sha"] for e in _events(h, "ticket_commit")]
    assert old in shas and new in shas and old != new


# ───────────── Task 3.3：push range ─────────────

def _small(h: dict, *files: str) -> None:
    _stage(h, *files)
    r = _commit(h, "feat: s\n\nTicket-Batch: small")
    assert r.returncode == 0, r.stderr


def test_33_three_small_union_five_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py", "momentum/b.py"); _small(h, "momentum/c.py", "momentum/d.py"); _small(h, "momentum/e.py")
    r = _push_range(h, f"{base}..HEAD")
    assert r.returncode != 0 and "累計生產檔 5" in r.stderr


def test_33_two_small_union_three_ok(tmp_path: Path) -> None:
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py", "momentum/b.py"); _small(h, "momentum/c.py")
    assert _push_range(h, f"{base}..HEAD").returncode == 0


def test_33_two_push_window_not_reset(tmp_path: Path) -> None:
    """GROK-R2-P0-01：push1 3 檔放行後，push2 再 3 檔（無 token）⇒ 累計 6 ⇒ 擋。"""
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py", "momentum/b.py", "momentum/c.py")
    mid = _git(h, "rev-parse", "HEAD").stdout.strip()
    assert _push_range(h, f"{base}..{mid}").returncode == 0
    _small(h, "momentum/d.py", "momentum/e.py", "momentum/f.py")
    r = _push_range(h, f"{mid}..HEAD")
    assert r.returncode != 0 and "累計生產檔 6" in r.stderr


def test_33_consumed_token_resets_window(tmp_path: Path) -> None:
    """對照組：領 token 且真的在該批 commit 生產檔（消費）⇒ 其後 small 自新窗計。"""
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py", "momentum/b.py", "momentum/c.py")
    _issue_token_event(h, "ROOT", 2); _token(h, "ROOT", 2); _stage(h, "momentum/impl.py")
    assert _commit(h, "feat: impl\n\nTicket-Batch: ROOT/b2").returncode == 0
    _small(h, "momentum/d.py", "momentum/e.py", "momentum/f.py")
    r = _push_range(h, f"{base}..HEAD")
    assert r.returncode == 0, r.stderr


def test_33_unconsumed_token_not_anchor(tmp_path: Path) -> None:
    """CODEX-R4-P1-04：只領 b1 token 不 commit ⇒ 不是錨 ⇒ 6 檔仍擋。"""
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py", "momentum/b.py", "momentum/c.py")
    _issue_token_event(h, "ROOT-Z", 1)
    _small(h, "momentum/d.py", "momentum/e.py", "momentum/f.py")
    assert _push_range(h, f"{base}..HEAD").returncode != 0


def test_33_docs_only_batch_commit_does_not_consume(tmp_path: Path) -> None:
    """CODEX-R5-P1-02：docs-only 帶 batch trailer 不消費 token ⇒ 仍累計 6。"""
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py", "momentum/b.py", "momentum/c.py")
    _issue_token_event(h, "ROOT", 2); _token(h, "ROOT", 2); _stage(h, "docs/x.md")
    assert _commit(h, "docs: x\n\nTicket-Batch: ROOT/b2").returncode == 0
    _small(h, "momentum/d.py", "momentum/e.py", "momentum/f.py")
    assert _push_range(h, f"{base}..HEAD").returncode != 0


def test_33_no_verify_then_token_not_ratified(tmp_path: Path) -> None:
    """CODEX-R4-P1-03：先 --no-verify commit 再領 token ⇒ token_fresh=false ⇒ push 擋。"""
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _stage(h, "momentum/x.py")
    assert _commit(h, "feat: x\n\nTicket-Batch: ROOT/b2", "--no-verify").returncode == 0
    _token(h, "ROOT", 2); _issue_token_event(h, "ROOT", 2)
    r = _push_range(h, f"{base}..HEAD")
    assert r.returncode != 0 and "token_fresh" in r.stderr


def test_33_prod_commit_without_trailer_in_range_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _stage(h, "momentum/x.py")
    assert _commit(h, "feat: x", "--no-verify").returncode == 0
    r = _push_range(h, f"{base}..HEAD")
    assert r.returncode != 0 and "無 Ticket-Batch" in r.stderr


def test_33_trailer_without_event_rejected(tmp_path: Path) -> None:
    """邊界④：有 trailer 卻無 ticket_commit 事件（post-commit 未跑）⇒ 擋。"""
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py")
    h["audit"].write_text("", encoding="utf-8")     # 模擬事件寫入失敗
    r = _push_range(h, f"{base}..HEAD")
    assert r.returncode != 0 and "無 audit ticket_commit" in r.stderr


def test_33_ghost_sha_filtered(tmp_path: Path) -> None:
    """GROK-R3-P2-01：amend 後舊 sha 不可達 ⇒ 不計入聯集。"""
    h = _h(tmp_path); base = _git(h, "rev-parse", "HEAD").stdout.strip()
    _small(h, "momentum/a.py", "momentum/b.py", "momentum/c.py")
    _stage(h, "momentum/d.py")                                   # amend 把 d 併入同一 commit（舊 sha 成幽靈）
    assert _git(h, "commit", "-q", "--amend", "--no-edit").returncode == 0
    r = _push_range(h, f"{base}..HEAD")
    assert r.returncode != 0 and "已濾 1" in r.stderr and "累計生產檔 4" in r.stderr   # 新 sha 4 檔 ⇒ 仍擋；舊 sha 為幽靈只濾不計


def test_33_pre_push_stdin_delete_line_skipped_and_ranges_exported(tmp_path: Path) -> None:
    """CODEX-R8-P1-02：local sha 全零（--delete）行跳過；其餘行組 range 傳給 gov_check。"""
    h = _h(tmp_path)
    stub = h["root"] / "scripts" / "gov_check.sh"
    stub.write_text("#!/usr/bin/env bash\necho \"RANGES=${VG_PUSH_RANGES:-} LOCALS=${VG_PUSH_LOCALS:-}\"\nexit 0\n", encoding="utf-8"); stub.chmod(0o755)
    head = _git(h, "rev-parse", "HEAD").stdout.strip()
    stdin = f"refs/heads/gone {ZERO} refs/heads/gone abc\nrefs/heads/main {head} refs/heads/main {ZERO}\n"
    r = subprocess.run(["bash", "scripts/git_hooks/pre-push", "origin", "x"], cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False, input=stdin)
    assert r.returncode == 0, r.stderr
    assert f"RANGES={head} LOCALS={head}" in r.stdout


def test_33_pre_push_all_delete_lines_ok(tmp_path: Path) -> None:
    h = _h(tmp_path)
    stub = h["root"] / "scripts" / "gov_check.sh"
    stub.write_text("#!/usr/bin/env bash\n[ -n \"${VG_PUSH_RANGES:-}\" ] && exit 9\nexit 0\n", encoding="utf-8"); stub.chmod(0o755)
    r = subprocess.run(["bash", "scripts/git_hooks/pre-push", "origin", "x"], cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False,
                       input=f"refs/heads/gone {ZERO} refs/heads/gone abc\n")
    assert r.returncode == 0


def test_33_pre_push_skip_env_leaves_audit(tmp_path: Path) -> None:
    h = _h(tmp_path)
    r = subprocess.run(["bash", "scripts/git_hooks/pre-push", "origin", "x"], cwd=h["root"], env={**h["env"], "GOVERNANCE_SKIP_PREPUSH": "1"},
                       capture_output=True, text=True, check=False, input="")
    assert r.returncode == 0 and any(e["hook"] == "pre-push" for e in _events(h, "governance_bypass"))


# ───────────── Task 3.1：gate.sh --impl-self ─────────────

def _dispatch(h: dict, task: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "scripts/gate.sh", "dispatch", "--impl-self", "--task-id", task, "--intent", "t", "--risk", "low",
                           "--facts-asked", "none-needed:unit", "--review-role", "single-executor:n/a", "--template", "n/a:unit", *extra],
                          cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False)


def _open_round(h: dict, task: str, rid: str, fams=("codex", "composer", "grok")) -> None:
    fams = list(fams)
    args = ["scripts/audit_append.sh", "--require-absent-session", f"s{rid}", "--event", "committee_round_open"]
    for f in (f"round_id={rid}", f"task_id={task}", "brief_path=handoffs/b.md", "brief_sha256=" + "a" * 64, "brief_sha256_norm=" + "a" * 64,
              "lock_mode=discovery", f"participants=@{json.dumps(fams)}", f"quorum_eligible=@{json.dumps(fams)}",
              f"expected_outputs=@{json.dumps({f: f'handoffs/o-{f}.md' for f in fams})}", f"session_name=s{rid}", "brief_kind=review",
              "actor=t", "origin_script=committee_run.sh"):
        args += ["--field", f]
    r = subprocess.run(["bash", *args], cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False); assert r.returncode == 0, r.stderr
    # 立即清債（避免 open debt 擋 dispatch）
    with h["audit"].open("a", encoding="utf-8") as fh:
        pass


def _out(h: dict, task: str, fam: str, verdict: str, blocked=(), rid: str = "") -> None:
    args = ["scripts/audit_append.sh", "--event", "committee_output", "--field", f"task_id={task}", "--field", f"family={fam}",
            "--field", f"output_path=handoffs/o-{fam}.md", "--field", "output_sha256=x", "--field", f"verdict={verdict}",
            "--field", f"blocked_by=@{json.dumps(list(blocked))}", "--field", "closed=@[]", "--field", "actor=gate", "--field", "origin_script=gate.sh"]
    if rid:
        args += ["--field", f"round_id={rid}"]
    r = subprocess.run(["bash", *args], cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False); assert r.returncode == 0, r.stderr


def _clear(h: dict, rid: str) -> None:
    r = subprocess.run(["bash", "scripts/audit_append.sh", "--event", "committee_debt_clear", "--field", f"round_id={rid}", "--field", "session_id=s",
                        "--field", "lock_sha256=x", "--field", "synth_sha256=y", "--field", "roster=codex", "--field", "completeness_rc=0",
                        "--field", "actor=t", "--field", "origin_script=debt_clear.sh"], cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr


def test_31_impl_self_b1_no_prev_issues_token_and_event(tmp_path: Path) -> None:
    h = _h(tmp_path)
    r = _dispatch(h, "ROOT-impl-b1-claude")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (h["gate_dir"] / "impl.ROOT-b1.token").is_file()
    ev = _events(h, "impl_token_issued"); assert len(ev) == 1 and ev[0]["root"] == "ROOT" and ev[0]["batch"] == "1"
    assert "跳過 quorum" in r.stdout


def test_31_impl_self_family_not_claude_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path)
    r = _dispatch(h, "ROOT-impl-b2-codex")
    assert r.returncode != 0 and "claude" in r.stdout


def test_31_impl_self_b2_prev_blocked_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _open_round(h, "ROOT-B1-REVIEW-R1", "rid1")
    _out(h, "ROOT-B1-REVIEW-R1", "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, "ROOT-B1-REVIEW-R1", "composer", "proceed", rid="rid1"); _out(h, "ROOT-B1-REVIEW-R1", "grok", "proceed", rid="rid1")
    _clear(h, "rid1")
    r = _dispatch(h, "ROOT-impl-b2-claude")
    assert r.returncode != 0 and "verdictgate" in (r.stdout + r.stderr)
    assert not (h["gate_dir"] / "impl.ROOT-b2.token").exists()


def test_31_impl_self_b2_prev_all_proceed_passes(tmp_path: Path) -> None:
    h = _h(tmp_path); _open_round(h, "ROOT-B1-REVIEW-R1", "rid1")
    for f in ("codex", "composer", "grok"):
        _out(h, "ROOT-B1-REVIEW-R1", f, "proceed", rid="rid1")
    _clear(h, "rid1")
    r = _dispatch(h, "ROOT-impl-b2-claude")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (h["gate_dir"] / "impl.ROOT-b2.token").is_file() and len(_events(h, "impl_token_issued")) == 1


def test_31_impl_self_b2_quorum_short_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _open_round(h, "ROOT-B1-REVIEW-R1", "rid1", fams=("codex",))
    _out(h, "ROOT-B1-REVIEW-R1", "codex", "proceed", rid="rid1"); _clear(h, "rid1")
    r = _dispatch(h, "ROOT-impl-b2-claude")
    assert r.returncode != 0 and "quorum" in (r.stdout + r.stderr).lower()
