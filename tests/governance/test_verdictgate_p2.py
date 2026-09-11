"""VERDICTGATE B2（Task 2.1＋2.2）— SPEC ASSERT 各一 test；fail-closed 配對照組。

只跑本檔：venv/bin/python -m pytest tests/governance/test_verdictgate_p2.py -q
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = (
    "prev_review_resolve.sh", "verdictgate_check.sh", "verdictgate_baseline.sh", "audit_append.sh", "audit_events.json",
    "governance_families.sh", "governance_families.json", "debt_ledger.sh", "_debt_ledger_core.py", "debt_clear.sh",
    "completeness_check.sh", "reconcile_body_hash.sh", "review_quorum_check.sh",
)
FAMS = ["codex", "composer", "grok"]


def _h(tmp_path: Path) -> dict:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    gate_dir = root / ".claude" / "gate"; gate_dir.mkdir(parents=True)
    audit = gate_dir / "audit.log"; audit.write_text("", encoding="utf-8")
    for n in _SCRIPTS:
        src = REPO_ROOT / "scripts" / n
        if src.is_file():
            shutil.copy2(src, root / "scripts" / n)
            if n.endswith(".sh"):
                (root / "scripts" / n).chmod(0o755)
    env = {"GOVERNANCE_TEST_HARNESS": "1", "DEBT_AUDIT_OVERRIDE": str(audit), "GATE_DIR_OVERRIDE": str(gate_dir),
           "PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "LANG": "C.UTF-8"}
    return {"root": root, "audit": audit, "env": env}


def _run(h: dict, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", *args], cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False)


def _raw(h: dict, **rec) -> None:
    """直寫 JSON 列（模擬上線前 legacy 列或精確控制 append 序）。"""
    rec.setdefault("ts", "2026-09-01T00:00:00Z")
    with h["audit"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


_seq = [0]


def _open(h: dict, task: str, rid: str, fams=FAMS, brief_kind: str | None = "review") -> None:
    """用 audit_append 開輪（帶 sequence）；brief_kind=None 模擬上線前 round。"""
    _seq[0] += 1
    args = ["scripts/audit_append.sh", "--require-absent-session", f"s{rid}", "--event", "committee_round_open"]
    fields = [f"round_id={rid}", f"task_id={task}", "brief_path=handoffs/b.md", "brief_sha256=" + "a" * 64,
              "brief_sha256_norm=" + "a" * 64, "lock_mode=discovery", f"participants=@{json.dumps(fams)}",
              f"quorum_eligible=@{json.dumps(fams)}", f"expected_outputs=@{json.dumps({f: f'handoffs/o-{f}.md' for f in fams})}",
              f"session_name=s{rid}", "actor=t", "origin_script=committee_run.sh"]
    if brief_kind:
        fields.append(f"brief_kind={brief_kind}")
    for f in fields:
        args += ["--field", f]
    r = _run(h, *args); assert r.returncode == 0, r.stderr


def _out(h: dict, task: str, fam: str, verdict: str, blocked=(), closed=(), rid: str | None = None) -> None:
    args = ["scripts/audit_append.sh", "--event", "committee_output", "--field", f"task_id={task}", "--field", f"family={fam}",
            "--field", f"output_path=handoffs/o-{fam}.md", "--field", "output_sha256=x", "--field", f"verdict={verdict}",
            "--field", f"blocked_by=@{json.dumps(list(blocked))}", "--field", f"closed=@{json.dumps(list(closed))}",
            "--field", "actor=gate", "--field", "origin_script=gate.sh"]
    if rid:
        args += ["--field", f"round_id={rid}"]
    r = _run(h, *args); assert r.returncode == 0, r.stderr


def _family_result(h: dict, rid: str, fam: str, state: str = "success") -> None:
    r = _run(h, "scripts/audit_append.sh", "--event", "committee_family_result", "--field", f"round_id={rid}", "--field", f"family={fam}",
             "--field", "attempt_id=a", "--field", "cli_rc=0", "--field", f"output_path=handoffs/o-{fam}.md", "--field", "output_sha256=x",
             "--field", f"result_state={state}", "--field", "actor=cx_run", "--field", "origin_script=cx_run.sh")
    assert r.returncode == 0, r.stderr


def _check(h: dict, root: str, n: int, prev: str | None = None) -> subprocess.CompletedProcess[str]:
    if prev is None:
        prev = _run(h, "scripts/prev_review_resolve.sh", root, str(n)).stdout.strip()
    return _run(h, "scripts/verdictgate_check.sh", root, str(n), prev)


R1 = "ROOT-B1-REVIEW-R1"; R2 = "ROOT-B1-REVIEW-R2"


# ───────────── helper（prev_review_resolve） ─────────────

def test_helper_basic_prefix(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    assert _run(h, "scripts/prev_review_resolve.sh", "ROOT", "3").stdout.strip() == "ROOT-B1-REVIEW"


def test_helper_legacy_review_like_without_review_literal(tmp_path: Path) -> None:
    """`P16 6` 有 P16-B5-TASK31-REV（無 brief_kind、無 -review 字面）⇒ 視為 review。"""
    h = _h(tmp_path); _open(h, "P16-B5-TASK31-REV", "rid1", brief_kind=None)
    assert _run(h, "scripts/prev_review_resolve.sh", "P16", "6").stdout.strip() == "P16-B5-TASK31-REV"


def test_helper_excludes_stamp_suffix_form(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, "P16-B3-STAMP", "rid1", brief_kind=None)
    assert _run(h, "scripts/prev_review_resolve.sh", "P16", "4").stdout.strip() == ""


def test_helper_multi_round_same_prefix(tmp_path: Path) -> None:
    h = _h(tmp_path)
    for i, t in enumerate(("SPLITUNIFY-B1-REVIEW-R1", "SPLITUNIFY-B1-REVIEW-R2", "SPLITUNIFY-B1-REVIEW-R3")):
        _open(h, t, f"rid{i}")
    assert _run(h, "scripts/prev_review_resolve.sh", "SPLITUNIFY", "2").stdout.strip() == "SPLITUNIFY-B1-REVIEW"


def test_helper_descoped_backtracks(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    assert _run(h, "scripts/prev_review_resolve.sh", "ROOT", "3").stdout.strip() == "ROOT-B1-REVIEW"


def test_helper_x_layer_not_candidate(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, "ROOT-X-REVIEW-R1", "rid1")
    assert _run(h, "scripts/prev_review_resolve.sh", "ROOT", "2").stdout.strip() == ""


# ───────────── checker ─────────────

def test_check_usage_two_args(tmp_path: Path) -> None:
    h = _h(tmp_path)
    r = _run(h, "scripts/verdictgate_check.sh", "ROOT", "2")
    assert r.returncode == 2 and "用法" in r.stderr


def test_check_prev_absent_passes(tmp_path: Path) -> None:
    h = _h(tmp_path)
    assert _check(h, "ROOT", 2, "").returncode == 0


def test_check_blocked_without_closed_blocks(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, R1, "composer", "proceed", rid="rid1"); _out(h, R1, "grok", "proceed", rid="rid1")
    r = _check(h, "ROOT", 2)
    assert r.returncode == 1 and "CODEX-R1-P1-01" in r.stderr


def test_check_batch_already_entered_skips_prev_verdicts(tmp_path: Path) -> None:
    """C-4 只擋進入新批：b2 已有審查輪 ⇒ 對 b2 之閉合／補裁決／修補輪不重驗 b1（否則補裁決輪連鎖回溯）。"""
    h = _h(tmp_path)
    _open(h, "ROOT-B1-REVIEW-R1", "rid1")
    _out(h, "ROOT-B1-REVIEW-R1", "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    assert _check(h, "ROOT", 2, "ROOT-B1-REVIEW").returncode != 0          # 尚未進入 b2 ⇒ 擋
    _open(h, "ROOT-B2-REVIEW-R1", "rid2")
    r = _check(h, "ROOT", 2, "ROOT-B1-REVIEW")
    assert r.returncode == 0 and "非新進批次" in r.stdout
    assert _check(h, "ROOT", 3, "ROOT-B2-REVIEW").returncode != 0          # b3 仍是新批 ⇒ 依 b2 裁決（無 output）擋


def test_check_blocked_then_closed_passes(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, R1, "composer", "proceed", rid="rid1"); _out(h, R1, "grok", "proceed", rid="rid1")
    _open(h, R2, "rid2", fams=["codex"], brief_kind="closure")
    _out(h, R2, "codex", "proceed", closed=["CODEX-R1-P1-01"], rid="rid2")
    assert _check(h, "ROOT", 2).returncode == 0


def test_check_proceed_does_not_release(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, R1, "composer", "proceed", rid="rid1"); _out(h, R1, "grok", "proceed", rid="rid1")
    _open(h, R2, "rid2")
    for f in FAMS:
        _out(h, R2, f, "proceed", rid="rid2")   # codex R2 proceed 但無 CLOSED
    r = _check(h, "ROOT", 2)
    assert r.returncode == 1 and "proceed 不解除" in r.stderr


def test_check_closed_by_other_family_does_not_release(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, R1, "composer", "proceed", rid="rid1"); _out(h, R1, "grok", "proceed", rid="rid1")
    _open(h, R2, "rid2")
    _out(h, R2, "codex", "proceed", rid="rid2"); _out(h, R2, "grok", "proceed", rid="rid2")
    _out(h, R2, "composer", "proceed", closed=["CODEX-R1-P1-01"], rid="rid2")  # 他家寫 CLOSED（Phase 1 會拒收；本閘亦不認）
    assert _check(h, "ROOT", 2).returncode == 1


def test_check_no_output_family_blocks_and_names(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "proceed", rid="rid1"); _out(h, R1, "composer", "proceed", rid="rid1")
    r = _check(h, "ROOT", 2)
    assert r.returncode == 1 and "grok" in r.stderr and "補裁決輪" in r.stderr


def test_check_no_output_family_abandoned_round_passes(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "proceed", rid="rid1"); _out(h, R1, "composer", "proceed", rid="rid1")
    r = _run(h, "scripts/debt_clear.sh", "--abandon", "--round-id", "rid1", "--kind", "collection-failed",
             "--reason", "grok 真缺席：CLI 未啟動、無 family_result（測試）", "--approver", "test")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _check(h, "ROOT", 2).returncode == 0


def test_check_verdict_rejected_then_reregistered_passes(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "proceed", rid="rid1"); _out(h, R1, "composer", "proceed", rid="rid1")
    _family_result(h, "rid1", "grok", "verdict_rejected")
    assert _check(h, "ROOT", 2).returncode == 1
    _out(h, R1, "grok", "proceed", rid="rid1")          # 主委修檔後再 register-output ⇒ 解鎖①
    assert _check(h, "ROOT", 2).returncode == 0


def test_abandon_collection_failed_rejected_when_family_result_exists(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1"); _family_result(h, "rid1", "codex")
    r = _run(h, "scripts/debt_clear.sh", "--abandon", "--round-id", "rid1", "--kind", "collection-failed",
             "--reason", "測試：有 family_result 卻 abandon 應被拒（C-9 解鎖②收窄）", "--approver", "test")
    assert r.returncode != 0 and "committee_family_result" in r.stderr


def test_check_legacy_unknown_prev_blocks_with_hint(tmp_path: Path) -> None:
    """C-4 v4：前批有 round_open 但各家皆 unknown（舊 writer 無 verdict）⇒ 擋並指名補裁決輪。"""
    h = _h(tmp_path); _open(h, R1, "rid1", brief_kind=None)
    for f in FAMS:
        _raw(h, event="committee_output", task_id=R1, family="unknown", output_path=f"handoffs/o-{f}.md", output_sha256="x")
    r = _check(h, "ROOT", 2)
    assert r.returncode == 1 and "補裁決輪" in r.stderr


def test_check_descoped_prev_legacy_blocks(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1", brief_kind=None)   # B2 descoped；B1 legacy
    prev = _run(h, "scripts/prev_review_resolve.sh", "ROOT", "3").stdout.strip()
    assert prev == "ROOT-B1-REVIEW"
    assert _check(h, "ROOT", 3, prev).returncode == 1


def test_check_consult_prev_only_passes(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, "ROOT-B1-CONSULT-R1", "rid1", brief_kind="consult")
    assert _check(h, "ROOT", 2, "ROOT-B1-CONSULT").returncode == 0


def test_check_stamp_closed_does_not_release(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, R1, "composer", "proceed", rid="rid1"); _out(h, R1, "grok", "proceed", rid="rid1")
    _open(h, "ROOT-X-STAMP-R2", "rid2", fams=["codex"], brief_kind="stamp")
    _out(h, "ROOT-X-STAMP-R2", "codex", "null", closed=["CODEX-R1-P1-01"], rid="rid2")
    assert _check(h, "ROOT", 2).returncode == 1


def test_check_helper_and_checker_agree_on_descoped(tmp_path: Path) -> None:
    """caller 傳 helper 輸出（B1）而非字面 N-1（B2 不存在）——B1 未閉合時，經 helper 的呼叫必擋。
    （B2 審碼 GROK-R1-P2-02／CODEX-R1-P2-04：舊版第二斷言「字面 B2 ⇒ rc=0」是在證明洞存在，非擋洞，已刪。）"""
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, R1, "composer", "proceed", rid="rid1"); _out(h, R1, "grok", "proceed", rid="rid1")
    prev = _run(h, "scripts/prev_review_resolve.sh", "ROOT", "3").stdout.strip()
    assert prev == "ROOT-B1-REVIEW"
    assert _check(h, "ROOT", 3, prev).returncode == 1


def test_helper_returns_all_prefixes_of_same_batch_and_checker_checks_each(tmp_path: Path) -> None:
    """CODEX-R1-P1-02／GROK-R1-P1-02：同批兩個 review prefix，先開者 proceed、後開者 blocked 未閉 ⇒ 仍擋。"""
    h = _h(tmp_path)
    _open(h, "P16-B5-BOOTSTRAP-R1", "rid1", brief_kind=None)
    for f in FAMS:
        _out(h, "P16-B5-BOOTSTRAP-R1", f, "proceed", rid="rid1")
    _open(h, "P16-B5-TASK31-REV-R1", "rid2", brief_kind=None)
    _out(h, "P16-B5-TASK31-REV-R1", "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid2")
    _out(h, "P16-B5-TASK31-REV-R1", "composer", "proceed", rid="rid2"); _out(h, "P16-B5-TASK31-REV-R1", "grok", "proceed", rid="rid2")
    prev = _run(h, "scripts/prev_review_resolve.sh", "P16", "6").stdout.strip()
    assert prev == "P16-B5-BOOTSTRAP,P16-B5-TASK31-REV"
    r = _check(h, "P16", 6, prev)
    assert r.returncode == 1 and "P16-B5-TASK31-REV" in r.stderr


def test_quorum_counts_committee_output_families_case_insensitive(tmp_path: Path) -> None:
    """CODEX-R1-P1-01／GROK-R1-P1-01：committee_run 派出的輪 task_id 為 `<ROOT>-B1-REVIEW-R1`（無家族尾碼），
    quorum 須由 committee_output.family 計數（大小寫不敏感），否則 --impl-self 永遠拿不到 token。"""
    h = _h(tmp_path); _open(h, R1, "rid1")
    _out(h, R1, "codex", "proceed", rid="rid1"); _out(h, R1, "grok", "proceed", rid="rid1")
    r = _run(h, "scripts/review_quorum_check.sh", "ROOT-B1", "claude")
    assert r.returncode == 0 and "2 個" in r.stdout
    r2 = _run(h, "scripts/review_quorum_check.sh", "ROOT-B1", "grok")   # 實作者 grok 排除 ⇒ 1 家
    assert r2.returncode == 1


def test_report_cleared_root_not_live(tmp_path: Path) -> None:
    """CODEX-R1-P2-03／GROK-R1-P2-01：最新批 round 已 debt_clear ⇒ 不列 live_roots_unwatched。"""
    h = _h(tmp_path); _open(h, R1, "rid1", brief_kind=None)
    _raw(h, event="committee_debt_clear", round_id="rid1", session_id="s", lock_sha256="x", synth_sha256="y", roster="codex", completeness_rc="0", ts="2026-09-02T00:00:00Z")
    r = _run(h, "scripts/verdictgate_baseline.sh", "--report")
    assert "live_roots_unwatched=\n" in r.stdout and "legacy_open_by_root=root:b1" in r.stdout


# ───────────── committee_run 端到端（SPEC Task 2.2 兩條 committee_run ASSERT；B2 審碼 CODEX-R1-P2-04／GROK-R1-P2-03） ─────────────

_CR_SCRIPTS = ("committee_run.sh", "cx_run.sh", "gate.sh", "gate_check.sh", "_gate_lex.sh", "brief_conformance_check.sh",
               "_role_gate.sh", "governance_roles.json", "governance_verdicts.json", "verdict_parse.sh", "verdict_filled_check.sh",
               "stampable_artifacts.txt", "round_cost.sh")


def _cr_h(tmp_path: Path) -> dict:
    h = _h(tmp_path)
    (h["root"] / "handoffs").mkdir(exist_ok=True)
    for n in _CR_SCRIPTS:
        src = REPO_ROOT / "scripts" / n
        if src.is_file():
            shutil.copy2(src, h["root"] / "scripts" / n)
            if n.endswith(".sh"):
                (h["root"] / "scripts" / n).chmod(0o755)
    # committee_run 之 gate.sh dispatch 以 always-pass stub 取代（與 test_stamp_taskid_inject 同法）——
    # 本測試只驗 committee_run 自身之 verdictgate 前置與 round_open 欄位，不驗 gate 全套。
    gp = h["root"] / "scripts" / "gate_pass.sh"
    gp.write_text("#!/usr/bin/env bash\necho GATE PASS stub\nexit 0\n", encoding="utf-8"); gp.chmod(0o755)
    cr = h["root"] / "scripts" / "committee_run.sh"
    txt = cr.read_text(encoding="utf-8")
    old = 'bash "${SCRIPT_DIR}/gate.sh" dispatch "${gate_args[@]}"'
    assert old in txt
    cr.write_text(txt.replace(old, 'bash "${SCRIPT_DIR}/gate_pass.sh" dispatch "${gate_args[@]}"', 1), encoding="utf-8")
    brief = h["root"] / "handoffs" / "brief.md"
    brief.write_text("brief-kind: review\n\ntemplates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做\nfact-verified: unit-test → harness\nassumed: isolated env\n\nstub\n", encoding="utf-8")
    h["env"]["CX_STUB_MODE"] = "success"
    return h


def _run_cr(h: dict, task: str, session: str) -> subprocess.CompletedProcess[str]:
    return _run(h, "scripts/committee_run.sh", "--session", session, "handoffs/brief.md", "handoffs/out", "codex", "--",
                "--intent", "t", "--risk", "low", "--facts-asked", "none-needed:unit", "--review-role", "advisory",
                "--template", "n/a:stub", "--task-id", task)


def test_committee_run_round_open_records_brief_kind(tmp_path: Path) -> None:
    h = _cr_h(tmp_path); _open(h, R1, "rid1")
    for f in FAMS:
        _out(h, R1, f, "proceed", rid="rid1")
    r = _run_cr(h, "20260911-ROOT-B2-REVIEW-R1", "20260911-root-b2-review-r1")
    assert r.returncode == 0, r.stdout + r.stderr
    opens = [json.loads(l) for l in h["audit"].read_text(encoding="utf-8").splitlines() if l.startswith("{") and '"committee_round_open"' in l]
    assert opens[-1]["task_id"] == "20260911-ROOT-B2-REVIEW-R1" and opens[-1]["brief_kind"] == "review"


def test_committee_run_verdictgate_fail_rc_nonzero_zero_audit(tmp_path: Path) -> None:
    h = _cr_h(tmp_path); _open(h, "20260911-ROOT-B1-REVIEW-R1", "rid1")
    _out(h, "20260911-ROOT-B1-REVIEW-R1", "codex", "blocked", blocked=["CODEX-R1-P1-01"], rid="rid1")
    _out(h, "20260911-ROOT-B1-REVIEW-R1", "composer", "proceed", rid="rid1"); _out(h, "20260911-ROOT-B1-REVIEW-R1", "grok", "proceed", rid="rid1")
    before = h["audit"].read_text(encoding="utf-8")
    r = _run_cr(h, "20260911-ROOT-B2-REVIEW-R1", "20260911-root-b2-review-r1")
    assert r.returncode != 0 and "verdictgate" in (r.stdout + r.stderr)
    assert h["audit"].read_text(encoding="utf-8") == before      # 失敗零新增 audit


# ───────────── report ─────────────

def test_report_counts_and_live_roots(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1", brief_kind=None)
    for f in FAMS:
        _raw(h, event="committee_output", task_id=R1, family="unknown", output_path=f"handoffs/o-{f}.md", output_sha256="x")
    _open(h, "OTHER-B1-REVIEW-R1", "rid2")
    for f in FAMS:
        _out(h, "OTHER-B1-REVIEW-R1", f, "proceed", rid="rid2")
    r = _run(h, "scripts/verdictgate_baseline.sh", "--report")
    assert r.returncode == 0, r.stderr
    assert "unknown=3" in r.stdout and "live_roots_unwatched=root" in r.stdout
    assert "OTHER-B1-REVIEW rounds=1 codex=has_verdict" in r.stdout


def test_report_stamp_not_counted_unknown(tmp_path: Path) -> None:
    h = _h(tmp_path); _open(h, R1, "rid1", fams=["codex"])
    _out(h, R1, "codex", "null", rid="rid1")
    r = _run(h, "scripts/verdictgate_baseline.sh", "--report")
    assert "codex=stamp" in r.stdout and "unknown=0" in r.stdout


def test_report_unknown_equals_independent_count(tmp_path: Path) -> None:
    """unknown= 之值須等於獨立實算（v3 依 CODEX-R10-P1-02：不寫死 ≥621）。"""
    h = _h(tmp_path); _open(h, R1, "rid1", brief_kind=None)
    _raw(h, event="committee_output", task_id=R1, family="unknown", output_path="handoffs/o-codex.md", output_sha256="x")
    r = _run(h, "scripts/verdictgate_baseline.sh", "--report")
    # 獨立實算：roster 3 家，codex 有 legacy 輸出（unknown）、composer/grok 無輸出（no_output ⇒ 計 unknown）⇒ 3
    assert "unknown=3" in r.stdout
