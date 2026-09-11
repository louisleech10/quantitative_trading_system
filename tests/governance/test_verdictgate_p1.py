"""VERDICTGATE B1（Task 1.1＋1.2）— 每條 SPEC ASSERT 對應一個 test；fail-closed 各配對照組。

只跑本檔：venv/bin/python -m pytest tests/governance/test_verdictgate_p1.py -q
隔離：scripts 副本 + 空 audit（DEBT_AUDIT_OVERRIDE / GATE_DIR_OVERRIDE 同一檔）。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = (
    "gate.sh", "gate_check.sh", "_gate_lex.sh", "audit_append.sh", "audit_events.json",
    "governance_families.sh", "governance_families.json", "governance_roles.json", "governance_verdicts.json",
    "verdict_parse.sh", "verdict_filled_check.sh", "cx_run.sh", "brief_conformance_check.sh",
    "completeness_check.sh", "_role_gate.sh", "reconcile_body_hash.sh", "debt_ledger.sh",
    "_debt_ledger_core.py", "template_check.sh", "review_quorum_check.sh", "verify_task_provenance.py",
    "stampable_artifacts.txt",
)
TASK = "20260911-ROOT-X-REVIEW-R2"
ROUND = "11111111-1111-4111-8111-111111111111"


def _h(tmp_path: Path) -> dict:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "handoffs").mkdir()
    gate_dir = root / ".claude" / "gate"
    gate_dir.mkdir(parents=True)
    audit = gate_dir / "audit.log"
    audit.write_text("", encoding="utf-8")
    for n in _SCRIPTS:
        src = REPO_ROOT / "scripts" / n
        if src.is_file():
            shutil.copy2(src, root / "scripts" / n)
            if n.endswith(".sh"):
                (root / "scripts" / n).chmod(0o755)
    env = {
        "GOVERNANCE_TEST_HARNESS": "1", "DEBT_AUDIT_OVERRIDE": str(audit), "GATE_DIR_OVERRIDE": str(gate_dir),
        "PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "LANG": "C.UTF-8",
    }
    return {"root": root, "audit": audit, "env": env}


def _run(h: dict, *args: str, env_overlay: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(h["env"]); env.update(env_overlay or {})
    return subprocess.run(["bash", *args], cwd=h["root"], env=env, capture_output=True, text=True, check=False)


def _seed_dispatch(h: dict, task: str = TASK) -> None:
    """committee_dispatch 為 legacy 事件（gate.sh 原生以 raw JSON 寫入）。"""
    with h["audit"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "committee_dispatch", "task_id": task, "ts": "2026-09-11T00:00:00Z"}) + "\n")


def _open_round(h: dict, fams: list[str], *, task: str = TASK, session: str = "s1", brief_kind: str = "review",
                prefix: str = "handoffs/x") -> None:
    outs = {f: f"{prefix}-{f}.md" for f in fams}
    bp = h["root"] / "handoffs" / "brief.md"
    sha = hashlib.sha256(bp.read_bytes()).hexdigest() if bp.is_file() else "a" * 64   # cx_run 驗 brief_sha256 與開債記錄一致
    args = ["scripts/audit_append.sh", "--require-absent-session", session, "--event", "committee_round_open"]
    for f in (f"round_id={ROUND}", f"task_id={task}", "brief_path=handoffs/brief.md", f"brief_sha256={sha}",
              f"brief_sha256_norm={sha}", "lock_mode=discovery", f"participants=@{json.dumps(fams)}",
              f"quorum_eligible=@{json.dumps(fams)}", f"expected_outputs=@{json.dumps(outs)}",
              f"session_name={session}", f"brief_kind={brief_kind}", "actor=test", "origin_script=committee_run.sh"):
        args += ["--field", f]
    r = _run(h, *args)
    assert r.returncode == 0, r.stdout + r.stderr


def _write_out(h: dict, rel: str, fam_u: str, block: str, *, ids: tuple[str, ...] = ("P1-01",)) -> Path:
    body = "".join(f"## {fam_u}-R2-{i}\n\n**斷言**: x\n\n**碼證**: y\n\n**來源摘要**: a.md#aaaaaaaaaaaa\n\nbody\n\n" for i in ids)
    p = h["root"] / rel
    p.write_text(body + block + "\nSTATUS: DONE\n", encoding="utf-8")
    return p


def _reg(h: dict, rel: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return _run(h, "scripts/gate.sh", "register-output", TASK, rel, *extra)


def _events(h: dict, name: str) -> list[dict]:
    out = []
    for line in h["audit"].read_text(encoding="utf-8").splitlines():
        if line.startswith("{"):
            d = json.loads(line)
            if d.get("event") == name:
                out.append(d)
    return out


# ───────────────── Task 1.1 ─────────────────

def test_11_verdicts_json_loads_and_has_values() -> None:
    d = json.load(open(REPO_ROOT / "scripts" / "governance_verdicts.json", encoding="utf-8"))
    assert d["verdict_values"] == ["proceed", "blocked"]
    assert "延後→" in d["disposition_values"]


def test_11_templates_have_machine_block_and_no_prose_verdict() -> None:
    for t in ("SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md", "COMMITTEE_FINDING_TEMPLATE.md", "BRIEF_REVIEW_TEMPLATE.md"):
        p = REPO_ROOT / "templates" / t
        assert "VERDICT: " in p.read_text(encoding="utf-8")
        r = subprocess.run(["bash", "scripts/template_check.sh", "template", f"templates/{t}"], cwd=REPO_ROOT,
                           capture_output=True, text=True, check=False)
        assert r.returncode == 0, r.stdout
    adv = (REPO_ROOT / "templates" / "SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md").read_text(encoding="utf-8")
    assert "## Verdict：" not in adv


def test_11_template_check_rejects_dual_format(tmp_path: Path) -> None:
    """邊界②：範本同時含 `## Verdict：` 與機械塊 ⇒ 紅（兩份真相源）。"""
    p = tmp_path / "t.md"
    p.write_text("## Verdict：x\n\nVERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n", encoding="utf-8")
    r = subprocess.run(["bash", "scripts/template_check.sh", "template", str(p)], cwd=REPO_ROOT,
                       capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "廢止" in r.stdout


def test_11_registry_shape() -> None:
    reg = json.load(open(REPO_ROOT / "scripts" / "audit_events.json", encoding="utf-8"))
    assert reg["registry_version"] == 3
    assert "committee_output" not in reg["non_debt_legacy_events"]
    assert set(reg["required_fields_per_event"]["committee_output"]) >= {"verdict", "blocked_by", "closed", "family"}
    # TODO 寫 length==7 含 producer；producer 由 audit_append 強制填入、不列必填 ⇒ 6
    assert len(reg["required_fields_per_event"]["ticket_commit"]) == 6
    assert {"gate.sh", "git_hooks/post-commit", "git_hooks/pre-push"} <= set(reg["allowed_origin_scripts"])
    assert "brief_kind" in reg["debt_events"]["committee_round_open"]["fields"]
    assert "verdict_rejected" in reg["enums"]["result_state"]


# ───────────────── Task 1.2：register-output ─────────────────

def test_12_verdict_line_absent_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "VERDICT" in (r.stdout + r.stderr)
    assert _events(h, "committee_output") == []


def test_12_blocked_without_blocked_by_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: blocked\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "BLOCKED-BY" in (r.stdout + r.stderr)


def test_12_closed_id_of_other_family_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED: GROK-R1-P1-01\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "前綴家族" in (r.stdout + r.stderr)


def test_12_proceed_with_expected_path_registers(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode == 0, r.stdout + r.stderr
    ev = _events(h, "committee_output")
    assert len(ev) == 1 and ev[0]["family"] == "codex" and ev[0]["verdict"] == "proceed"
    assert ev[0]["blocked_by"] == [] and ev[0]["closed"] == []


def test_12_blocked_registers_blocked_by_list(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: blocked\nBLOCKED-BY: CODEX-R2-P1-01\nCLOSED:\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _events(h, "committee_output")[0]["blocked_by"] == ["CODEX-R2-P1-01"]


def test_12_blocked_by_id_not_in_file_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: blocked\nBLOCKED-BY: CODEX-R2-P1-09\nCLOSED:\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "不在本檔" in (r.stdout + r.stderr)


def test_12_path_not_expected_output_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/y-codex.md", "CODEX", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/y-codex.md")
    assert r.returncode != 0 and "expected_outputs" in (r.stdout + r.stderr)


def test_12_closed_id_found_only_in_other_root_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    # 另一票（OTHERROOT）之同家歷史產出含該 ID
    other = h["root"] / "handoffs" / "o-codex.md"
    other.write_text("## CODEX-R1-P1-01\n\n**斷言**: z\n", encoding="utf-8")
    with h["audit"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "committee_output", "task_id": "20260901-OTHERROOT-X-REVIEW-R1", "family": "codex",
                            "output_path": "handoffs/o-codex.md", "output_sha256": "x", "ts": "t"}) + "\n")
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED: CODEX-R1-P1-01\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "同 root" in (r.stdout + r.stderr)


def test_12_closed_id_in_same_root_history_accepted(tmp_path: Path) -> None:
    """對照組：同 root 之同家歷史產出（legacy family=unknown、尾碼 -codex.md）含該 ID ⇒ 放行。"""
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    prev = h["root"] / "handoffs" / "p-codex.md"
    prev.write_text("## CODEX-R1-P1-01\n\n**斷言**: z\n", encoding="utf-8")
    with h["audit"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "committee_output", "task_id": "20260911-ROOT-X-REVIEW-R1", "family": "unknown",
                            "output_path": "handoffs/p-codex.md", "output_sha256": "x", "ts": "t"}) + "\n")
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED: CODEX-R1-P1-01\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _events(h, "committee_output")[-1]["closed"] == ["CODEX-R1-P1-01"]


def test_12_family_from_suffix_grok(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex", "grok"])
    _write_out(h, "handoffs/x-grok.md", "GROK", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/x-grok.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _events(h, "committee_output")[0]["family"] == "grok"


def test_12_family_not_in_roster_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-agy.md", "AGY", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/x-agy.md")
    assert r.returncode != 0 and "quorum_eligible" in (r.stdout + r.stderr)


def test_12_no_round_open_for_task_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h)
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "committee_round_open" in (r.stdout + r.stderr)


def test_12_two_verdict_lines_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT: proceed\nVERDICT: blocked\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "歧義" in (r.stdout + r.stderr)


def test_12_fullwidth_colon_rejected_and_named(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    _write_out(h, "handoffs/x-codex.md", "CODEX", "VERDICT：proceed\nBLOCKED-BY:\nCLOSED:\n")
    r = _reg(h, "handoffs/x-codex.md")
    assert r.returncode != 0 and "全形" in (r.stdout + r.stderr)


def test_12_stamp_kind_registers_verdict_null(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    (h["root"] / "handoffs" / "reconcile").mkdir()
    synth = h["root"] / "handoffs" / "reconcile" / "synth.md"
    synth.write_text("# synth\n\n## 戳記\n\nRECONCILE-STAMP: codex APPROVED 2026-09-11 sha256:x task:t\n", encoding="utf-8")
    r = _reg(h, "handoffs/reconcile/synth.md", "--kind", "stamp", "--family", "codex")
    assert r.returncode == 0, r.stdout + r.stderr
    ev = _events(h, "committee_output")[0]
    assert ev["verdict"] == "null" and ev["family"] == "codex"


def test_12_stamp_kind_without_family_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h); _open_round(h, ["codex"])
    (h["root"] / "handoffs" / "s.md").write_text("x\n", encoding="utf-8")
    r = _reg(h, "handoffs/s.md", "--kind", "stamp")
    assert r.returncode != 0 and "--family" in (r.stdout + r.stderr)


# ───────────────── audit_append 契約 ─────────────────

def test_12_audit_append_committee_output_missing_verdict_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path)
    r = _run(h, "scripts/audit_append.sh", "--event", "committee_output", "--field", "task_id=T", "--field", "family=codex",
             "--field", "output_path=h.md", "--field", "output_sha256=x", "--field", "blocked_by=@[]", "--field", "closed=@[]",
             "--field", "actor=t", "--field", "origin_script=gate.sh")
    assert r.returncode != 0 and "verdict" in r.stderr


def test_12_audit_append_ticket_commit_origin_post_commit_ok(tmp_path: Path) -> None:
    h = _h(tmp_path)
    r = _run(h, "scripts/audit_append.sh", "--event", "ticket_commit", "--field", "sha=abc", "--field", "trailer=small",
             "--field", "root=small", "--field", "batch=0", "--field", 'prod_files=@["momentum/x.py"]',
             "--field", "token_fresh=null", "--field", "actor=t", "--field", "origin_script=git_hooks/post-commit")
    assert r.returncode == 0, r.stderr
    assert _events(h, "ticket_commit")[0]["prod_files"] == ["momentum/x.py"]


def test_12_audit_append_impl_token_issued_missing_root_rejected(tmp_path: Path) -> None:
    h = _h(tmp_path)
    r = _run(h, "scripts/audit_append.sh", "--event", "impl_token_issued", "--field", "task_id=T", "--field", "batch=2",
             "--field", "family=claude", "--field", "actor=t", "--field", "origin_script=gate.sh")
    assert r.returncode != 0 and "root" in r.stderr


# ───────────────── 舊列相容（sequence_since） ─────────────────

def test_12_ledger_grandfathers_pre_v3_committee_output_rows(tmp_path: Path) -> None:
    """B1 上線事故（2026-09-11）：舊 writer 直寫之 committee_output 無 sequence ⇒ 帳本判不可信、gate 拒發。
    registry `sequence_since` 前之無 sequence 列須被視為唯讀 legacy，帳本 rc≠2。"""
    h = _h(tmp_path)
    with h["audit"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "committee_output", "task_id": "OLD-X-REVIEW-R1", "family": "unknown",
                            "output_path": "handoffs/o-codex.md", "output_sha256": "x", "ts": "2026-09-01T00:00:00Z"}) + "\n")
    r = _run(h, "scripts/debt_ledger.sh", "--has-open")
    assert r.returncode in (0, 1), r.stdout + r.stderr


def test_12_ledger_rejects_post_v3_committee_output_without_sequence(tmp_path: Path) -> None:
    """對照組：sequence_since 之後仍無 sequence 的列＝壞寫入 ⇒ 帳本 fail-closed rc=2。"""
    h = _h(tmp_path)
    with h["audit"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "committee_output", "task_id": "NEW-X-REVIEW-R1", "family": "codex",
                            "output_path": "handoffs/n-codex.md", "output_sha256": "x", "ts": "2026-12-01T00:00:00Z"}) + "\n")
    r = _run(h, "scripts/debt_ledger.sh", "--has-open")
    assert r.returncode == 2 and "缺 sequence" in r.stderr


# ───────────────── cx_run 接線 ─────────────────

def _write_brief(h: dict, kind: str) -> str:
    lines = [f"brief-kind: {kind}", "", "templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做",
             "fact-verified: unit-test → harness", "assumed: isolated env", "", "stub\n"]
    (h["root"] / "handoffs" / "brief.md").write_text("\n".join(lines), encoding="utf-8")
    return "handoffs/brief.md"


def _run_cx(h: dict, fam: str, brief_rel: str, out_rel: str, tail: str) -> subprocess.CompletedProcess[str]:
    return _run(h, "scripts/cx_run.sh", fam, brief_rel, out_rel,
                env_overlay={"ROUND_ID": ROUND, "CX_STUB_MODE": "success", "CX_STUB_TAIL": tail})


def test_12_cx_run_review_done_with_verdict_auto_registers(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h)
    brief = _write_brief(h, "review")
    _open_round(h, ["codex"], prefix="handoffs/out")
    before = len(_events(h, "committee_output"))
    r = _run_cx(h, "codex", brief, "handoffs/out-codex.md", "verdict")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h, "committee_output")) == before + 1
    assert _events(h, "committee_output")[-1]["verdict"] == "proceed"


def test_12_cx_run_review_done_without_verdict_marks_rejected_rc_unchanged(tmp_path: Path) -> None:
    h = _h(tmp_path); _seed_dispatch(h)
    brief = _write_brief(h, "review")
    _open_round(h, ["codex"], prefix="handoffs/out")
    r = _run_cx(h, "codex", brief, "handoffs/out-codex.md", "done")
    assert r.returncode == 0, r.stdout + r.stderr          # cx_run rc 不變
    assert "verdict 拒收" in r.stderr
    states = [e["result_state"] for e in _events(h, "committee_family_result")]
    assert states[-1] == "verdict_rejected" and "success" in states
    assert _events(h, "committee_output") == []


def test_12_cx_run_review_without_status_done_does_not_register(tmp_path: Path) -> None:
    """對照組：既有 success stub（無 STATUS: DONE）⇒ 不嘗試註冊、不留 verdict_rejected。"""
    h = _h(tmp_path); _seed_dispatch(h)
    brief = _write_brief(h, "review")
    _open_round(h, ["codex"], prefix="handoffs/out")
    r = _run_cx(h, "codex", brief, "handoffs/out-codex.md", "")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _events(h, "committee_output") == []
    assert all(e["result_state"] != "verdict_rejected" for e in _events(h, "committee_family_result"))
