"""B-64 同輪同家重派之機械路徑（SPEC v12 Task 1.1–1.8）。

全部測試於隔離 repo 執行：GOVERNANCE_TEST_HARNESS=1、DEBT_AUDIT_OVERRIDE、GATE_DIR_OVERRIDE，
不讀寫真實 .claude/gate/。gate_check 判定只餵 JSON payload，絕不真的派工。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# 隔離 repo 之固定複製清單（同 test_govb1_b31_recovery.py::_COPY_SCRIPTS 再加本票所需）
_COPY_SCRIPTS = [
    "audit_append.sh", "audit_events.json", "governance_families.sh", "governance_families.json",
    "governance_roles.json", "governance_verdicts.json", "completeness_check.sh", "debt_clear.sh",
    "debt_ledger.sh", "_debt_ledger_core.py", "_role_gate.sh", "govflow_lifecycle.json",
    "doc_format_precheck.sh", "verdict_filled_check.sh", "template_check.sh", "verdict_parse.sh",
    "gate.sh", "gate_check.sh", "_gate_lex.sh", "reconcile_body_hash.sh",
    "_redispatch_check.py", "_synth_attr.py", "reconcile_stamps_check.sh", "session_name_check.sh",
    "brief_conformance_check.sh", "quant_standard_check.sh", "ticket_batch_check.sh",
]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Repo:
    """隔離 repo：scripts 副本＋自建 audit．gate 目錄。"""

    def __init__(self, root: Path):
        self.root = root
        self.scripts = root / "scripts"
        self.gate = root / "gate"
        self.audit = root / "audit.log"
        self.seq = 0

    @property
    def env(self) -> dict:
        e = dict(os.environ)
        e.update(
            GOVERNANCE_TEST_HARNESS="1",
            DEBT_AUDIT_OVERRIDE=str(self.audit),
            GATE_DIR_OVERRIDE=str(self.gate),
        )
        return e

    def run(self, args, stdin: str | None = None, env_extra: dict | None = None,
            cwd: Path | None = None) -> subprocess.CompletedProcess:
        env = self.env
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            args, capture_output=True, text=True, input=stdin,
            cwd=str(cwd or self.root), env=env,
        )

    def redispatch(self, rid: str, fam: str, reason: str = "redispatch-test-reason-000000001"):
        return self.run(["bash", str(self.scripts / "gate.sh"), "redispatch",
                         "--round-id", rid, "--family", fam, "--reason", reason])

    def append(self, event: str, **fields) -> None:
        args = ["bash", str(self.scripts / "audit_append.sh"), "--event", event]
        for k, v in fields.items():
            args += ["--field", f"{k}={v}"]
        proc = self.run(args)
        assert proc.returncode == 0, proc.stderr

    def write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def events(self, event: str) -> list[dict]:
        if not self.audit.is_file():
            return []
        out = []
        for line in self.audit.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s.startswith("{"):
                continue
            rec = json.loads(s)
            if rec.get("event") == event:
                out.append(rec)
        return out


@pytest.fixture()
def repo(tmp_path: Path) -> Repo:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for name in _COPY_SCRIPTS:
        src = REPO / "scripts" / name
        if src.is_file():
            shutil.copy2(src, root / "scripts" / name)
    (root / "handoffs").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    r = Repo(root)
    r.gate.mkdir(parents=True, exist_ok=True)
    r.audit.touch()
    return r


def open_round(r: Repo, rid: str, fams=("codex", "composer"), brief="handoffs/b.md",
               out_prefix="handoffs/o") -> dict:
    """開一輪：寫 brief、committee_round_open 事件。回傳 expected_outputs。"""
    r.write(brief, "brief body\n")
    expected = {f: f"{out_prefix}-{f}.md" for f in fams}
    r.append(
        "committee_round_open",
        round_id=rid, session_name=f"s-{rid[:8]}", brief_path=brief,
        task_id="20260916-REDISPATCH-T-REVIEW-R1", lock_mode="review",
        brief_sha256=sha256_text("brief body\n"),
        brief_sha256_norm=sha256_text("brief body\n"), brief_kind="review",
        participants="@" + json.dumps(list(fams)), quorum_eligible="@" + json.dumps(list(fams)),
        expected_outputs="@" + json.dumps(expected),
        actor="committee_run", origin_script="committee_run.sh",
    )
    return expected


def family_result(r: Repo, rid: str, fam: str, state: str, out_path: str,
                  sha: str = "", partial: str | None = None) -> None:
    fields = dict(
        round_id=rid, family=fam, attempt_id=str(uuid.uuid4()), cli_rc="1" if state == "failed" else "0",
        output_path=out_path, output_sha256=sha, result_state=state,
        actor="cx_run", origin_script="cx_run.sh",
    )
    if partial:
        fields["partial_output_sha256"] = partial
    r.append("committee_family_result", **fields)


# ── Task 1.4：路徑 token 文法 ──────────────────────────────────────────
@pytest.mark.parametrize("path,rc", [
    ("b.md", 0), ("/abs/handoffs/x.md", 0), ("handoffs/白話.md", 0),
    ("handoffs/it's.md", 2), ("-x.md", 2), ("", 2),
])
def test_path_check_grammar(repo: Repo, path: str, rc: int) -> None:
    proc = repo.run(["python3", str(repo.scripts / "_redispatch_check.py"), "path-check", path])
    assert proc.returncode == rc, proc.stderr


def test_committee_run_path_rule_matches_python(repo: Repo) -> None:
    """committee_run.sh 之內嵌 bash 版與 path_token_ok 逐例一致（語意對照，不得漂移）。"""
    src = (REPO / "scripts" / "committee_run.sh").read_text(encoding="utf-8")
    start = src.index("_cr_path_bad() {")
    end = src.index("}", start) + 1
    fn = src[start:end]
    assert fn.strip(), "擷取 _cr_path_bad 失敗"
    cases = ["b.md", "/abs/handoffs/x.md", "handoffs/白話.md", "handoffs/it's.md", "-x.md", "",
             "a\nb.md", "a\rb.md"]
    for case in cases:
        bash_rc = subprocess.run(
            ["bash", "-c", fn + '\nif _cr_path_bad "$1"; then exit 1; else exit 0; fi', "_", case],
            capture_output=True, text=True,
        ).returncode
        py_rc = repo.run(["python3", str(repo.scripts / "_redispatch_check.py"), "path-check", case]).returncode
        assert (bash_rc != 0) == (py_rc != 0), f"路徑判定漂移: {case!r} bash={bash_rc} py={py_rc}"


# ── Task 1.1：發放條件 ────────────────────────────────────────────────
def _failed_no_output_round(r: Repo) -> tuple[str, dict]:
    rid = str(uuid.uuid4())
    expected = open_round(r, rid)
    family_result(r, rid, "codex", "failed", expected["codex"])
    return rid, expected


def test_issue_failed_no_output_only_open_rc0(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith(f"ROUND_ID={rid} bash scripts/cx_run.sh codex handoffs/b.md handoffs/o-codex.md")
    issued = repo.events("redispatch_token_issued")
    assert len(issued) == 1 and issued[0]["prev_output_sha256"] == "none"
    assert (repo.gate / f"redispatch.{rid}.codex.token").is_file()


def test_issue_round_id_traversal_gate_dir_absent_rc2(repo: Repo) -> None:
    shutil.rmtree(repo.gate)
    proc = repo.redispatch("../../escape", "codex")
    assert proc.returncode == 2
    assert not repo.gate.exists(), "輸入驗證前不得建立閘目錄"


def test_issue_family_uppercase_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    assert repo.redispatch(rid, "Codex").returncode == 2


def test_issue_reason_too_short_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    assert repo.redispatch(rid, "codex", reason="short").returncode == 2


def test_issue_latest_success_rc1(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    repo.write(expected["codex"], "out\n")
    family_result(repo, rid, "codex", "success", expected["codex"], sha=sha256_text("out\n"))
    assert repo.redispatch(rid, "codex").returncode == 1


def test_issue_format_failed_archives_rc0(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "## CODEX-R1-P1-01\n**斷言**: 測試用斷言內容夠長以供逐字引用比對\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "format-failed", expected["codex"], sha=sha256_text(body))
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 0, proc.stderr
    ev = repo.events("redispatch_token_issued")[0]
    arc = repo.root / ev["prev_output_archive"]
    assert arc.is_file() and sha256_text(arc.read_text(encoding="utf-8")) == sha256_text(body)
    assert ev["prev_output_sha256"] == sha256_text(body)


def test_issue_failed_partial_output_archives_rc0(repo: Repo) -> None:
    """failed 之 output_sha256 依契約為空 ⇒ 以 partial_output_sha256 為準仍須保存。"""
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "partial output\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "failed", expected["codex"], partial=sha256_text(body))
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 0, proc.stderr
    ev = repo.events("redispatch_token_issued")[0]
    assert ev["prev_output_sha256"] == sha256_text(body)
    assert (repo.root / ev["prev_output_archive"]).is_file()


def test_issue_output_deleted_before_archive_rc1(repo: Repo) -> None:
    """條件判定通過後、保存前產出檔被刪 ⇒ 不得誤判為「無前次產出」而照發（b1 r1 CODEX-R1-P1-02）。"""
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "## CODEX-R1-P1-01\n**斷言**: 測試用斷言內容夠長以供逐字引用比對\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "format-failed", expected["codex"], sha=sha256_text(body))
    hook = f"rm -f {repo.root / expected['codex']}"
    proc = repo.run(["bash", str(repo.scripts / "gate.sh"), "redispatch", "--round-id", rid,
                     "--family", "codex", "--reason", "redispatch-test-reason-000000001"],
                    env_extra={"REDISPATCH_TEST_BEFORE_ARCHIVE_CMD": hook})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert repo.events("redispatch_token_issued") == []
    assert not (repo.root / "handoffs" / "redispatch_archive").exists()


def test_exhausted_check_holds_permit_lock(repo: Repo) -> None:
    """耗盡查核期間須持有（輪、家族）鎖（b1 r1 CODEX-R1-P1-03）。"""
    rid = _exhausted_round(repo)
    marker = repo.root / "lockstate.txt"
    probe = repo.root / "probe_lock.py"
    probe.write_text(
        "import fcntl, os, sys\n"
        f"p = {str(repo.gate / f'redispatch.{rid}.codex.lock')!r}\n"
        "fd = os.open(p, os.O_CREAT | os.O_RDWR, 0o600)\n"
        "try:\n"
        "    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
        "    state = 'free'\n"
        "    fcntl.flock(fd, fcntl.LOCK_UN)\n"
        "except BlockingIOError:\n"
        "    state = 'held'\n"
        f"open({str(marker)!r}, 'w').write(state)\n",
        encoding="utf-8",
    )
    repo.run(["python3", str(repo.scripts / "_redispatch_check.py"), "exhausted-check",
              "--round-id", rid],
             env_extra={"REDISPATCH_TEST_IN_EXHAUSTED_LOCK_CMD": f"python3 {probe}"})
    assert marker.is_file(), "掛鉤未執行"
    assert marker.read_text(encoding="utf-8").strip() == "held"


def test_issue_partial_output_missing_rc1(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "partial output\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "failed", expected["codex"], partial=sha256_text(body))
    (repo.root / expected["codex"]).unlink()
    assert repo.redispatch(rid, "codex").returncode == 1


def test_issue_partial_output_zeroed_rc1(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "partial output\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "failed", expected["codex"], partial=sha256_text(body))
    repo.write(expected["codex"], "")
    assert repo.redispatch(rid, "codex").returncode == 1


def test_issue_output_sha_mismatch_rc1(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    repo.write(expected["codex"], "orig\n")
    family_result(repo, rid, "codex", "format-failed", expected["codex"], sha=sha256_text("orig\n"))
    repo.write(expected["codex"], "tampered\n")
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 1
    assert not (repo.root / "handoffs" / "redispatch_archive").exists()


def test_issue_second_round_open_rc1(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    open_round(repo, str(uuid.uuid4()), brief="handoffs/b2.md", out_prefix="handoffs/o2")
    assert repo.redispatch(rid, "codex").returncode == 1


def test_issue_family_not_active_rc1(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid, fams=("codex", "grok"))
    family_result(repo, rid, "grok", "failed", expected["grok"])
    fams_path = repo.scripts / "governance_families.json"
    d = json.loads(fams_path.read_text(encoding="utf-8"))
    d["active_stampers"] = ["codex", "composer"]
    fams_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    assert repo.redispatch(rid, "grok").returncode == 1


def test_issue_pending_attempt_rc1(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    assert repo.redispatch(rid, "codex").returncode == 0
    assert repo.redispatch(rid, "codex").returncode == 1        # 已有待用許可（⑨）


def test_issue_symlink_output_rc1(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    target = repo.write("handoffs/real.md", "x\n")
    link = repo.root / expected["codex"]
    link.symlink_to(target)
    family_result(repo, rid, "codex", "failed", expected["codex"])
    assert repo.redispatch(rid, "codex").returncode == 1


def test_issue_round_brief_single_quote_rc1(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid, brief="handoffs/it's.md")
    family_result(repo, rid, "codex", "failed", expected["codex"])
    assert repo.redispatch(rid, "codex").returncode == 1        # ⑫ 文法


def test_issue_round_brief_unicode_quoted_rc0(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid, brief="handoffs/白話.md")
    family_result(repo, rid, "codex", "failed", expected["codex"])
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 0, proc.stderr
    assert "'handoffs/白話.md'" in proc.stdout


def test_fault_point_without_harness_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    env = {"REDISPATCH_FAULT_POINT": "after_token_write", "GOVERNANCE_TEST_HARNESS": "0"}
    proc = repo.run(["python3", str(repo.scripts / "_redispatch_check.py"), "issue",
                     "--round-id", rid, "--family", "codex",
                     "--reason", "redispatch-test-reason-000000001"], env_extra=env)
    assert proc.returncode == 2


def test_issue_killed_after_token_write_then_retry_rc0(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    proc = repo.run(["python3", str(repo.scripts / "_redispatch_check.py"), "issue",
                     "--round-id", rid, "--family", "codex",
                     "--reason", "redispatch-test-reason-000000001"],
                    env_extra={"REDISPATCH_FAULT_POINT": "after_token_write"})
    assert proc.returncode != 0
    assert (repo.gate / f"redispatch.{rid}.codex.token").is_file()
    assert repo.events("redispatch_token_issued") == []
    assert repo.redispatch(rid, "codex").returncode == 0
    assert len(repo.events("redispatch_token_issued")) == 1


# ── Task 1.2：消費與放行 ──────────────────────────────────────────────
def _payload(cmd: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})


def _issued_cmd(r: Repo, rid: str, fam: str = "codex") -> str:
    proc = r.redispatch(rid, fam)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_consume_exact_rc0(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = _issued_cmd(repo, rid)
    proc = repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd))
    assert proc.returncode == 0, proc.stderr
    assert len(repo.events("redispatch_token_consumed")) == 1
    assert (repo.gate / f"redispatch.{rid}.codex.token.consumed").is_file()


def test_consume_twice_second_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = _issued_cmd(repo, rid)
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 0
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 2


@pytest.mark.parametrize("mutate", [
    lambda c: c.replace("handoffs/b.md", "handoffs/other.md"),      # brief 不符
    lambda c: c.replace("handoffs/o-codex.md", "handoffs/x.md"),    # 產出不符
    lambda c: c.replace(" codex ", " composer "),                   # 家族不符
    lambda c: c + " ; ls",                                          # 額外字元
    lambda c: c + " > /tmp/x",                                      # 重導
    lambda c: "FOO=1 " + c,                                         # 額外 env
    lambda c: c + " ",                                              # 尾端空白
])
def test_consume_mutated_command_rc2(repo: Repo, mutate) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = _issued_cmd(repo, rid)
    proc = repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(mutate(cmd)))
    assert proc.returncode == 2
    assert repo.events("redispatch_token_consumed") == []


def test_consume_brief_modified_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = _issued_cmd(repo, rid)
    repo.write("handoffs/b.md", "tampered\n")
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 2


def test_consume_secret_mismatch_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = _issued_cmd(repo, rid)
    tok = repo.gate / f"redispatch.{rid}.codex.token"
    tok.write_text(tok.read_text(encoding="utf-8").replace("secret=", "secret=x"), encoding="utf-8")
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 2


def test_forged_token_without_audit_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = f"ROUND_ID={rid} bash scripts/cx_run.sh codex handoffs/b.md handoffs/o-codex.md"
    (repo.gate / f"redispatch.{rid}.codex.token").write_text(
        "\n".join([
            "nonce=deadbeef", "secret=zzz", f"round_id={rid}", "family=codex",
            "brief_path=handoffs/b.md", "brief_sha256=" + sha256_text("brief body\n"),
            "output_path=handoffs/o-codex.md", "attempt_no=1", "issued_epoch=0",
            "prev_output_sha256=none", "prev_output_archive=none", "",
        ]), encoding="utf-8")
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 2


def test_consume_archive_modified_rc2(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "## CODEX-R1-P1-01\n**斷言**: 測試用斷言內容夠長以供逐字引用比對\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "format-failed", expected["codex"], sha=sha256_text(body))
    cmd = _issued_cmd(repo, rid)
    arc = repo.root / repo.events("redispatch_token_issued")[0]["prev_output_archive"]
    arc.write_text("tampered\n", encoding="utf-8")
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 2


def test_consume_token_tampered_prev_fields_rc2(repo: Repo) -> None:
    """竄改許可檔之保存檔綁定欄 ⇒ 與發放事件不符，不得放行（b1 r1 CODEX-R1-P1-01）。"""
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "## CODEX-R1-P1-01\n**斷言**: 測試用斷言內容夠長以供逐字引用比對\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "format-failed", expected["codex"], sha=sha256_text(body))
    cmd = _issued_cmd(repo, rid)
    tok = repo.gate / f"redispatch.{rid}.codex.token"
    text = tok.read_text(encoding="utf-8")
    text = re.sub(r"prev_output_archive=.*", "prev_output_archive=none", text)
    text = re.sub(r"prev_output_sha256=.*", "prev_output_sha256=none", text)
    tok.write_text(text, encoding="utf-8")
    proc = repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd))
    assert proc.returncode == 2
    assert repo.events("redispatch_token_consumed") == []


def test_non_dispatch_command_skips_redispatch_helper(repo: Repo) -> None:
    """kind 非 dispatch 之指令不得呼叫 helper（效能：以替身記錄呼叫）。"""
    helper = repo.scripts / "_redispatch_check.py"
    marker = repo.root / "helper_called.txt"
    helper.write_text(f"#!/usr/bin/env python3\nopen({str(marker)!r}, 'a').close()\n", encoding="utf-8")
    proc = repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload("ls -la"))
    assert proc.returncode == 0
    assert not marker.exists()


def test_missing_helper_same_as_current(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = f"ROUND_ID={rid} bash scripts/cx_run.sh codex handoffs/b.md handoffs/o-codex.md"
    (repo.scripts / "_redispatch_check.py").unlink()
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 2


# ── Task 1.8 與 registry ──────────────────────────────────────────────
def test_registry_committee_family_result_has_partial_field() -> None:
    reg = json.loads((REPO / "scripts" / "audit_events.json").read_text(encoding="utf-8"))
    fields = reg["debt_events"]["committee_family_result"]["fields"]
    assert "partial_output_sha256" in fields
    assert "partial_output_sha256" not in reg["required_fields_per_event"]["committee_family_result"]


def test_redispatch_events_registry_round_scoped_false() -> None:
    reg = json.loads((REPO / "scripts" / "audit_events.json").read_text(encoding="utf-8"))
    for name, origin in (("redispatch_token_issued", "gate.sh"),
                         ("redispatch_token_consumed", "gate_check.sh"),
                         ("redispatch_token_claimed", "cx_run.sh")):
        ev = reg["debt_events"][name]
        assert ev["round_scoped"] is False and ev["origin_script"] == origin
        assert ev["opens_debt"] is False and ev["closes_debt"] is False
    assert "gate_check.sh" in reg["allowed_origin_scripts"]
    for key in ("redispatch_max_attempts", "redispatch_min_interval_seconds",
                "redispatch_token_ttl_seconds", "redispatch_launch_grace_seconds"):
        assert key in reg["constants"]


def test_redispatch_audit_calls_accept_real_registry(repo: Repo) -> None:
    """三事件以真實 audit_append 逐一寫入：rc=0、序號連續；移除 actor 即 rc≠0。"""
    rid = str(uuid.uuid4())
    common = dict(round_id=rid, family="codex", origin_script="gate.sh", actor="gate")
    repo.append("redispatch_token_issued", attempt_no="1", brief_path="handoffs/b.md",
                brief_sha256=sha256_text("x"), output_path="handoffs/o-codex.md",
                reason="redispatch-test-reason-000000001", issue_nonce="n1",
                permit_secret_sha256=sha256_text("s"), prev_output_sha256="none",
                prev_output_archive="none", **common)
    repo.append("redispatch_token_consumed", issue_nonce="n1", command_sha256=sha256_text("c"),
                round_id=rid, family="codex", actor="gate_check", origin_script="gate_check.sh")
    repo.append("redispatch_token_claimed", issue_nonce="n1", round_id=rid, family="codex",
                actor="cx_run", origin_script="cx_run.sh")
    seqs = [e["sequence"] for e in repo.events("redispatch_token_issued")
            + repo.events("redispatch_token_consumed") + repo.events("redispatch_token_claimed")]
    assert seqs == sorted(seqs) and len(set(seqs)) == 3
    proc = repo.run(["bash", str(repo.scripts / "audit_append.sh"), "--event", "redispatch_token_claimed",
                     "--field", f"round_id={rid}", "--field", "family=codex",
                     "--field", "issue_nonce=n2", "--field", "origin_script=cx_run.sh"])
    assert proc.returncode != 0 and "actor" in proc.stderr


# ── Task 1.1：已交件判準（completeness 以替身固定回值，測本票之接線） ──────
def _stub_completeness(r: Repo, body: str) -> None:
    (r.scripts / "completeness_check.sh").write_text(body, encoding="utf-8")


def _delivered_round(r: Repo) -> tuple[str, dict]:
    rid = str(uuid.uuid4())
    expected = open_round(r, rid)
    out = expected["codex"]
    r.write(out, "delivered body\n")
    family_result(r, rid, "codex", "format-failed", out, sha=sha256_text("delivered body\n"))
    r.append("committee_output", round_id=rid, family="codex", output_path=out,
             output_sha256=sha256_text("delivered body\n"), verdict="proceed",
             blocked_by="@[]", closed="@[]",
             task_id="20260916-REDISPATCH-T-REVIEW-R1", actor="gate", origin_script="gate.sh")
    return rid, expected


def test_issue_output_registered_completeness_pass_rc1(repo: Repo) -> None:
    rid, _ = _delivered_round(repo)
    _stub_completeness(repo, "#!/usr/bin/env bash\nexit 0\n")
    assert repo.redispatch(rid, "codex").returncode == 1        # 已交件 ⇒ ④違規


def test_issue_output_registered_completeness_fail_rc0(repo: Repo) -> None:
    rid, _ = _delivered_round(repo)
    _stub_completeness(repo, "#!/usr/bin/env bash\nexit 1\n")
    assert repo.redispatch(rid, "codex").returncode == 0        # 自動登記殘痕 ⇒ 未交件


def test_issue_output_registered_sha_mismatch_rc0(repo: Repo) -> None:
    rid, expected = _delivered_round(repo)
    _stub_completeness(repo, "#!/usr/bin/env bash\nexit 0\n")
    repo.write(expected["codex"], "tampered-after-register\n")  # 登記 sha 與現檔不符 ⇒ 未交件
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 1                                  # ⑤產出於結果列後被改動亦擋
    assert "④" not in proc.stderr


def test_issue_output_registered_outside_repo_rc0(repo: Repo) -> None:
    """登記路徑不等於該輪 expected ⇒ 視為未交件（gate.sh 對 repo 外絕對路徑會截斷前綴）。"""
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    repo.write(expected["codex"], "body\n")
    family_result(repo, rid, "codex", "format-failed", expected["codex"], sha=sha256_text("body\n"))
    repo.append("committee_output", round_id=rid, family="codex",
                output_path="handoffs/elsewhere-codex.md", output_sha256=sha256_text("body\n"),
                verdict="proceed", blocked_by="@[]", closed="@[]",
                task_id="20260916-REDISPATCH-T-REVIEW-R1",
                actor="gate", origin_script="gate.sh")
    _stub_completeness(repo, "#!/usr/bin/env bash\nexit 0\n")
    assert repo.redispatch(rid, "codex").returncode == 0


def test_env_flag_does_not_flip_delivered(repo: Repo) -> None:
    """呼叫端之逃生口旗標不得翻轉已交件判準（濾除 COMPLETENESS_*／ID_PATTERN）。"""
    rid, _ = _delivered_round(repo)
    _stub_completeness(
        repo,
        '#!/usr/bin/env bash\nif [ -n "${COMPLETENESS_ADVISORY_ONLY:-}" ]; then exit 1; fi\nexit 0\n',
    )
    proc = repo.run(["bash", str(repo.scripts / "gate.sh"), "redispatch", "--round-id", rid,
                     "--family", "codex", "--reason", "redispatch-test-reason-000000001"],
                    env_extra={"COMPLETENESS_ADVISORY_ONLY": "1"})
    assert proc.returncode == 1, proc.stdout + proc.stderr     # 仍判為已交件


def test_delivered_uses_repo_cwd(repo: Repo) -> None:
    """已交件判準固定以 repo 為工作目錄呼叫（錨點檔以 cwd 解析，SPEC §A）。"""
    rid, _ = _delivered_round(repo)
    marker = repo.root / "cwd.txt"
    _stub_completeness(repo, f'#!/usr/bin/env bash\npwd > {marker}\nexit 0\n')
    repo.run(["bash", str(repo.scripts / "gate.sh"), "redispatch", "--round-id", rid,
              "--family", "codex", "--reason", "redispatch-test-reason-000000001"],
             cwd=repo.root.parent)
    assert marker.is_file()
    assert Path(marker.read_text(encoding="utf-8").strip()).resolve() == repo.root.resolve()


def test_issue_partial_sha_read_from_audit_not_ledger(repo: Repo) -> None:
    """帳本投影不含 partial_output_sha256 ⇒ 結果列須自 audit 事件讀取。"""
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    body = "partial\n"
    repo.write(expected["codex"], body)
    family_result(repo, rid, "codex", "failed", expected["codex"], partial=sha256_text(body))
    dump = repo.run(["python3", "-S", str(repo.scripts / "_debt_ledger_core.py")], env_extra={
        "DEBT_LEDGER_MODE": "dump_json", "DEBT_LEDGER_ROUND_ID": "",
        "DEBT_LEDGER_REGISTRY": str(repo.scripts / "audit_events.json"),
        "DEBT_LEDGER_REPO": str(repo.root),
    })
    latest = json.loads(dump.stdout)["rounds"][rid]["latest_results"]["codex"]
    assert "partial_output_sha256" not in latest                # 投影確實丟欄
    assert repo.redispatch(rid, "codex").returncode == 0        # 仍讀得到 ⇒ 保存成立
    assert repo.events("redispatch_token_issued")[0]["prev_output_sha256"] == sha256_text(body)


# ── Task 1.1 ⑦⑧：上限與間隔 ────────────────────────────────────────────
def _issue_event(r: Repo, rid: str, fam: str, nonce: str) -> None:
    r.append("redispatch_token_issued", round_id=rid, family=fam, attempt_no="1",
             brief_path="handoffs/b.md", brief_sha256=sha256_text("brief body\n"),
             output_path=f"handoffs/o-{fam}.md", reason="redispatch-test-reason-000000001",
             issue_nonce=nonce, permit_secret_sha256=sha256_text("s"),
             prev_output_sha256="none", prev_output_archive="none",
             actor="gate", origin_script="gate.sh")


def test_issue_attempts_exhausted_rc1(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    for i in range(6):                                          # 六次發放皆已完成（done）
        nonce = f"n{i}"
        _issue_event(repo, rid, "codex", nonce)
        repo.append("redispatch_token_consumed", round_id=rid, family="codex", issue_nonce=nonce,
                    command_sha256=sha256_text("c"), actor="gate_check", origin_script="gate_check.sh")
        repo.append("redispatch_token_claimed", round_id=rid, family="codex", issue_nonce=nonce,
                    actor="cx_run", origin_script="cx_run.sh")
        family_result(repo, rid, "codex", "failed", "handoffs/o-codex.md")
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 1
    assert "⑦" in proc.stderr and "--abandon" in proc.stderr    # 耗盡時另印棄置指令


def test_issue_interval_not_elapsed_rc1(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    _issue_event(repo, rid, "codex", "n0")
    repo.append("redispatch_token_consumed", round_id=rid, family="codex", issue_nonce="n0",
                command_sha256=sha256_text("c"), actor="gate_check", origin_script="gate_check.sh")
    repo.append("redispatch_token_claimed", round_id=rid, family="codex", issue_nonce="n0",
                actor="cx_run", origin_script="cx_run.sh")
    family_result(repo, rid, "codex", "failed", "handoffs/o-codex.md")   # done ⇒ ⑨不擋
    proc = repo.redispatch(rid, "codex")
    assert proc.returncode == 1 and "⑧" in proc.stderr


# ── Task 1.3：audit_append 之鎖內條件寫入 ──────────────────────────────
def _exhausted_round(repo: Repo) -> str:
    """造一輪：codex 六次重派皆已結束且最新結果為 failed 無產出 ⇒ 符合棄置例外。"""
    rid, _ = _failed_no_output_round(repo)
    for i in range(6):
        nonce = f"x{i}"
        _issue_event(repo, rid, "codex", nonce)
        repo.append("redispatch_token_consumed", round_id=rid, family="codex", issue_nonce=nonce,
                    command_sha256=sha256_text("c"), actor="gate_check", origin_script="gate_check.sh")
        repo.append("redispatch_token_claimed", round_id=rid, family="codex", issue_nonce=nonce,
                    actor="cx_run", origin_script="cx_run.sh")
        family_result(repo, rid, "codex", "failed", "handoffs/o-codex.md")
    return rid


def _abandon(repo: Repo, rid: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    return repo.run(["bash", str(repo.scripts / "debt_clear.sh"), "--abandon", "--round-id", rid,
                     "--kind", "collection-failed",
                     "--reason", "redispatch-test-reason-000000001",
                     "--approver", "redispatch-test-approver"], env_extra=env_extra)


def test_abandon_exhausted_all_ended_rc0(repo: Repo) -> None:
    rid = _exhausted_round(repo)
    proc = _abandon(repo, rid)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(repo.events("debt_abandon")) == 1


def test_abandon_below_max_attempts_rc1(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    assert _abandon(repo, rid).returncode != 0            # 未達上限 ⇒ 既有 C-9 拒絕不變
    assert repo.events("debt_abandon") == []


def test_abandon_result_appended_after_check_rc1(repo: Repo) -> None:
    """查核通過後插入遲到結果 ⇒ 鎖內條件寫入須拒（b1 r1 CODEX-R1-P1-03／GROK-R1-P1-01）。"""
    rid = _exhausted_round(repo)
    hook = (f'bash {repo.scripts / "audit_append.sh"} --event committee_family_result '
            f'--field round_id={rid} --field family=codex --field attempt_id=late-1 '
            f'--field cli_rc=0 --field output_path=handoffs/o-codex.md '
            f'--field output_sha256={sha256_text("late")} --field result_state=success '
            f'--field actor=cx_run --field origin_script=cx_run.sh')
    proc = _abandon(repo, rid, env_extra={"REDISPATCH_TEST_AFTER_EXHAUSTED_CHECK_CMD": hook})
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert repo.events("debt_abandon") == []


def test_abandon_concurrent_single_event(repo: Repo) -> None:
    rid = _exhausted_round(repo)
    args = ["bash", str(repo.scripts / "debt_clear.sh"), "--abandon", "--round-id", rid,
            "--kind", "collection-failed", "--reason", "redispatch-test-reason-000000001",
            "--approver", "redispatch-test-approver"]
    procs = [subprocess.Popen(args, cwd=str(repo.root), env=repo.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
    rcs = [p.wait() for p in procs]
    assert len(repo.events("debt_abandon")) == 1, f"rcs={rcs}"


def test_audit_append_round_unchanged_rejects_after_snapshot(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    snapshot = repo.events("committee_family_result")[-1]["sequence"]
    family_result(repo, rid, "codex", "failed", "handoffs/o-codex.md")   # 快照後新增事件
    proc = repo.run(["bash", str(repo.scripts / "audit_append.sh"),
                     "--require-round-unchanged", f"{rid}@{snapshot}",
                     "--event", "debt_abandon", "--field", f"round_id={rid}",
                     "--field", "abandon_kind=collection-failed",
                     "--field", "reason=redispatch-test-reason-000000001",
                     "--field", "approver=redispatch-test-approver",
                     "--field", "actor=debt_clear", "--field", "origin_script=debt_clear.sh"])
    assert proc.returncode == 1 and repo.events("debt_abandon") == []


def test_audit_append_round_unchanged_ignores_other_round(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    snapshot = repo.events("committee_family_result")[-1]["sequence"]
    other = str(uuid.uuid4())
    open_round(repo, other, brief="handoffs/b2.md", out_prefix="handoffs/o2")   # 他輪事件不影響
    proc = repo.run(["bash", str(repo.scripts / "audit_append.sh"),
                     "--require-round-unchanged", f"{rid}@{snapshot}",
                     "--event", "debt_abandon", "--field", f"round_id={rid}",
                     "--field", "abandon_kind=collection-failed",
                     "--field", "reason=redispatch-test-reason-000000001",
                     "--field", "approver=redispatch-test-approver",
                     "--field", "actor=debt_clear", "--field", "origin_script=debt_clear.sh"])
    assert proc.returncode == 0, proc.stderr
    assert len(repo.events("debt_abandon")) == 1


def test_audit_append_round_unchanged_with_absent_session_rc2(repo: Repo) -> None:
    proc = repo.run(["bash", str(repo.scripts / "audit_append.sh"),
                     "--require-round-unchanged", "r@1",
                     "--require-absent-session", "s1",
                     "--event", "committee_round_open"])
    assert proc.returncode == 2


# ── Task 1.7：保存檔處置查核（archive-check 單元） ─────────────────────
_ARCHIVE_BODY = "## CODEX-R1-P1-01\n**斷言**: 保存檔之斷言內容需夠長以供逐字引用比對之用\n"


def _archive_round(r: Repo, body: str = _ARCHIVE_BODY) -> tuple[str, Path]:
    rid = str(uuid.uuid4())
    expected = open_round(r, rid)
    r.write(expected["codex"], body)
    family_result(r, rid, "codex", "format-failed", expected["codex"],
                  sha=hashlib.sha256(body.encode("utf-8")).hexdigest())
    assert r.redispatch(rid, "codex").returncode == 0
    arc = r.root / r.events("redispatch_token_issued")[0]["prev_output_archive"]
    return rid, arc


def _synth(r: Repo, rows: str, arc_rel: str = "") -> Path:
    text = ("# Reconcile — t\n\n## 群集 / 處置\n\n**修訂標的**：docs/REDISPATCH_SPEC.md\n\n"
            "| 群集 | 嚴重度 | 來源 ID | 處置 |\n|---|---|---|---|\n" + rows +
            (f"\n保存檔：{arc_rel}\n" if arc_rel else "") +
            "\n**Verdict**: 可合併\n\n---\n\n## 附錄：findings 逐字保留\n")
    return r.write("handoffs/reconcile/t/synth.md", text)


def _archive_check(r: Repo, rid: str, synth: Path) -> subprocess.CompletedProcess:
    return r.run(["python3", str(r.scripts / "_redispatch_check.py"), "archive-check",
                  "--round-id", rid, "--synth", str(synth)])


def test_clear_archive_findings_all_dispositioned_rc0(repo: Repo) -> None:
    rid, arc = _archive_round(repo)
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 保存檔之斷言內容需夠長以供逐字引用比對之用 | P1 | CODEX-R1-P1-01 | 採納 |\n", rel)
    assert _archive_check(repo, rid, synth).returncode == 0


def test_clear_archive_finding_missing_row_rc1(repo: Repo) -> None:
    rid, arc = _archive_round(repo)
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 別的意見 | P1 | CODEX-R1-P9-99 | 採納 |\n", rel)
    assert _archive_check(repo, rid, synth).returncode == 1


def test_clear_archive_finding_quote_mismatch_rc1(repo: Repo) -> None:
    rid, arc = _archive_round(repo)
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 引用不逐字 | P1 | CODEX-R1-P1-01 | 採納 |\n", rel)
    assert _archive_check(repo, rid, synth).returncode == 1


def test_clear_archive_finding_no_disposition_rc1(repo: Repo) -> None:
    rid, arc = _archive_round(repo)
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 保存檔之斷言內容需夠長以供逐字引用比對之用 | P1 | CODEX-R1-P1-01 | 待議 |\n", rel)
    assert _archive_check(repo, rid, synth).returncode == 1


def test_clear_archive_path_not_in_synth_rc1(repo: Repo) -> None:
    rid, arc = _archive_round(repo)
    synth = _synth(repo, "| 保存檔之斷言內容需夠長以供逐字引用比對之用 | P1 | CODEX-R1-P1-01 | 採納 |\n")
    assert _archive_check(repo, rid, synth).returncode == 1


def test_clear_archive_modified_rc1(repo: Repo) -> None:
    rid, arc = _archive_round(repo)
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 保存檔之斷言內容需夠長以供逐字引用比對之用 | P1 | CODEX-R1-P1-01 | 採納 |\n", rel)
    arc.write_text("tampered\n", encoding="utf-8")
    assert _archive_check(repo, rid, synth).returncode == 1


def test_clear_archive_finding_without_assertion_id_dispositioned_rc0(repo: Repo) -> None:
    rid, arc = _archive_round(repo, body="## CODEX-R1-P1-01\n（無斷言行）\n")
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 無斷言之保存檔意見 | P1 | CODEX-R1-P1-01 | 採納 |\n", rel)
    assert _archive_check(repo, rid, synth).returncode == 0


def test_clear_archive_finding_without_assertion_no_row_rc1(repo: Repo) -> None:
    rid, arc = _archive_round(repo, body="## CODEX-R1-P1-01\n（無斷言行）\n")
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 不相關 | P3 | CODEX-R1-P9-99 | 採納 |\n", rel)
    assert _archive_check(repo, rid, synth).returncode == 1


def test_clear_archive_non_utf8_id_dispositioned_rc0(repo: Repo) -> None:
    """解碼有損但仍取得標號 ⇒ 只要求含處置 token 之同 ID 列，略過引用比對。"""
    rid = str(uuid.uuid4())
    expected = open_round(repo, rid)
    raw = ("## CODEX-R1-P1-01\n**斷言**: 原始斷言".encode("utf-8") + b"\xff\xfe"
           + "內容需夠長以供逐字引用比對\n".encode("utf-8"))
    p = repo.root / expected["codex"]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(raw)
    family_result(repo, rid, "codex", "format-failed", expected["codex"],
                  sha=hashlib.sha256(raw).hexdigest())
    assert repo.redispatch(rid, "codex").returncode == 0
    arc = repo.root / repo.events("redispatch_token_issued")[0]["prev_output_archive"]
    synth = _synth(repo, "| 解碼有損之保存檔意見 | P1 | CODEX-R1-P1-01 | 採納 |\n",
                   str(arc.relative_to(repo.root)))
    assert _archive_check(repo, rid, synth).returncode == 0


def test_clear_archive_zero_findings_path_cited_rc0(repo: Repo) -> None:
    rid, arc = _archive_round(repo, body="（本檔無 canonical 標號）\n")
    rel = str(arc.relative_to(repo.root))
    synth = _synth(repo, "| 無標號之保存檔 | P3 | CODEX-R1-P9-99 | 採納 |\n", rel)
    assert _archive_check(repo, rid, synth).returncode == 0


def test_clear_archive_no_redispatch_event_rc0(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    open_round(repo, rid)
    synth = _synth(repo, "| 無保存檔之輪 | P3 | CODEX-R1-P9-99 | 採納 |\n")
    assert _archive_check(repo, rid, synth).returncode == 0


def test_clear_helper_absent_with_archive_event_rc1(repo: Repo) -> None:
    """helper 缺失而該輪有帶保存檔之發放事件 ⇒ debt_clear 內嵌分支 fail-closed。"""
    rid, arc = _archive_round(repo)
    (repo.scripts / "_redispatch_check.py").unlink()
    src = (REPO / "scripts" / "debt_clear.sh").read_text(encoding="utf-8")
    start = src.index("_assert_redispatch_archives_dispositioned() {")
    end = src.index("\n_cmd_clear() {", start)
    fn = src[start:end]
    script = repo.root / "probe.sh"
    script.write_text(
        "SCRIPT_DIR=" + str(repo.scripts) + "\n"
        "_resolve_audit_path() { printf '%s' \"" + str(repo.audit) + "\"; }\n"
        + fn + "\n_assert_redispatch_archives_dispositioned \"$1\" \"$2\"\n",
        encoding="utf-8",
    )
    synth = _synth(repo, "| 保存檔之斷言內容需夠長以供逐字引用比對之用 | P1 | CODEX-R1-P1-01 | 採納 |\n",
                   str(arc.relative_to(repo.root)))
    lock = synth.parent / "sources.lock"
    lock.write_text("{}", encoding="utf-8")
    proc = repo.run(["bash", str(script), rid, str(lock)])
    assert proc.returncode == 1 and "fail-closed" in proc.stderr


# ── Task 1.6：行程租約與認領 ──────────────────────────────────────────
def _lease(r: Repo, rid: str, fam: str, cmd: list[str]) -> subprocess.CompletedProcess:
    return r.run(["python3", str(r.scripts / "_redispatch_check.py"), "lease",
                  "--round-id", rid, "--family", fam, "--"] + cmd)


def _lease_bg(r: Repo, rid: str, fam: str, cmd: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        ["python3", str(r.scripts / "_redispatch_check.py"), "lease",
         "--round-id", rid, "--family", fam, "--"] + cmd,
        cwd=str(r.root), env=r.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _wait_for(path: Path, timeout: float = 5.0) -> bool:
    import time as _t
    end = _t.time() + timeout
    while _t.time() < end:
        if path.exists():
            return True
        _t.sleep(0.05)
    return False


def test_lease_second_process_same_round_family_rc2(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    marker = repo.root / "held.txt"
    proc = _lease_bg(repo, rid, "codex", ["bash", "-c", f"touch {marker}; sleep 3"])
    try:
        assert _wait_for(marker), "第一個租約行程未啟動"
        assert _lease(repo, rid, "codex", ["true"]).returncode == 2
    finally:
        proc.kill()
        proc.wait()


def test_lease_released_on_process_exit(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    assert _lease(repo, rid, "codex", ["true"]).returncode == 0
    assert _lease(repo, rid, "codex", ["true"]).returncode == 0     # 前一行程已結束 ⇒ 可再取得


def test_lease_inherited_by_child_process(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    marker = repo.root / "child.txt"
    proc = _lease_bg(repo, rid, "codex", ["bash", "-c", f"(touch {marker}; sleep 3) & exit 0"])
    try:
        assert _wait_for(marker), "子行程未啟動"
        proc.wait(timeout=5)
        assert _lease(repo, rid, "codex", ["true"]).returncode == 2  # 子行程仍持有繼承之描述子
    finally:
        subprocess.run(["pkill", "-f", f"sleep 3"], capture_output=True)


def test_lease_non_uuid_round_id_ok(repo: Repo) -> None:
    assert _lease(repo, "r-ab-1", "codex", ["true"]).returncode == 0
    assert list(repo.audit.parent.glob("redispatch.lease.*"))


def test_normal_run_without_consumed_file_proceeds(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    assert _lease(repo, rid, "codex", ["true"]).returncode == 0
    assert repo.events("redispatch_token_claimed") == []


def test_claim_within_grace_proceeds(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = _issued_cmd(repo, rid)
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 0
    assert _lease(repo, rid, "codex", ["true"]).returncode == 0
    assert len(repo.events("redispatch_token_claimed")) == 1
    assert (repo.gate / f"redispatch.{rid}.codex.token.claimed").is_file()


def test_claim_past_grace_refuses_rc2(repo: Repo) -> None:
    rid, _ = _failed_no_output_round(repo)
    cmd = _issued_cmd(repo, rid)
    assert repo.run(["bash", str(repo.scripts / "gate_check.sh")], stdin=_payload(cmd)).returncode == 0
    # 把消費事件之 ts 改為逾啟動寬限之過去時間（隔離 audit，測試夾具操作）
    lines = repo.audit.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if '"redispatch_token_consumed"' in line:
            rec = json.loads(line)
            rec["ts"] = "2020-01-01T00:00:00Z"
            lines[i] = json.dumps(rec, ensure_ascii=False)
    repo.audit.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = _lease(repo, rid, "codex", ["true"])
    assert proc.returncode == 2 and "啟動寬限" in proc.stderr
    assert (repo.gate / f"redispatch.{rid}.codex.token.expired").is_file()
    assert repo.events("redispatch_token_claimed") == []


def test_consumed_file_without_event_deleted_and_proceeds(repo: Repo) -> None:
    rid = str(uuid.uuid4())
    open_round(repo, rid)
    stale = repo.gate / f"redispatch.{rid}.codex.token.consumed"
    stale.write_text("nonce=ghost\n", encoding="utf-8")
    assert _lease(repo, rid, "codex", ["true"]).returncode == 0
    assert not stale.exists()
    assert repo.events("redispatch_token_claimed") == []


def test_lease_skipped_when_helper_absent(repo: Repo) -> None:
    """helper 缺失 ⇒ cx_run.sh 不 re-exec、不建立租約檔（行為與現行相同）。"""
    shutil.copy2(REPO / "scripts" / "cx_run.sh", repo.scripts / "cx_run.sh")
    (repo.scripts / "_redispatch_check.py").unlink()
    repo.write("handoffs/b.md", "brief body\n")
    proc = repo.run(["bash", str(repo.scripts / "cx_run.sh"), "codex", "handoffs/b.md",
                     "handoffs/o-codex.md"], env_extra={"ROUND_ID": str(uuid.uuid4())})
    assert proc.returncode != 0                                   # 後續閘擋下，但不得因 helper 缺失而爆
    assert not list(repo.audit.parent.glob("redispatch.lease.*"))
