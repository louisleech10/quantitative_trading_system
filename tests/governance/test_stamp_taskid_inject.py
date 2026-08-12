"""GOV-STAMP-TASKID-INJECT / D-001：task_id 注入＋stamp-target 驗證＋自動 register-output。

V1–V21 逐條 oracle；mutation 以隔離腳本副本閹割守衛後斷言轉紅。
測試一律 GOVERNANCE_TEST_HARNESS=1 + GATE_DIR_OVERRIDE / DEBT_AUDIT_OVERRIDE 隔離；
禁止寫入真實 .claude/gate/audit.log；禁止變異 repo 內 scripts/*.sh。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from tests.governance import _role_pin  # noqa: E402

import tests.governance._debt_probe_helper as _dph

REPO_ROOT = Path(__file__).resolve().parents[2]

# 與 D-001 §D2 逐字一致的注入句前綴
_TASK_ID_INJECT_PREFIX = "你的 task-id="
_TASK_ID_INJECT_SUFFIX = (
    "。RECONCILE-STAMP 的 task: 欄位須逐字使用此值；brief 內任何 task-id 範例一律不得採用。"
)

_SCRIPT_NAMES = (
    "committee_run.sh",
    "cx_run.sh",
    "audit_append.sh",
    "gate.sh",
    "audit_events.json",
    "governance_families.sh",
    "governance_families.json",
    "governance_roles.json",
    "reconcile_body_hash.sh",
    "debt_ledger.sh",
    "_debt_ledger_core.py",
    # GOV-DOC-CHECK-AT-WRITE（2026-08-02）：cx_run.sh 的 brief 合規閘 + stamp-target 驗證
    # 已抽成獨立腳本（一份實作、兩個呼叫點）。隔離 repo 少了它 → cx_run rc=127。
    "brief_conformance_check.sh",
    # GOV-FORMAT-SSOT 症狀 B（2026-08-02）：cx_run.sh 交件當下呼叫 --single 檢查產出格式。
    # 缺檔時 cx_run 會判「格式不合規」rc=3 —— 那是**檢查正確**（缺工具＝檢查沒跑），
    # 不是測試該放寬，故補進清單。
    # ⚠️ 本 session 第 5 次「新增依賴 → 某份 fixture 清單漏了它」＝票 GOV-TESTHARNESS-SCRIPTLIST-SSOT。
    "completeness_check.sh",
    "governance_families.sh",
    # GOVFLOW Task 3.1：角色閘 + task_id 白名單 SSOT（cx_run / committee_run 共用）
    "_role_gate.sh",
)


def _read_json_lines(audit: Path) -> list[dict]:
    if not audit.is_file():
        return []
    rows: list[dict] = []
    for line in audit.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            rows.append(rec)
    return rows


def _events(audit: Path, name: str | None = None) -> list[dict]:
    rows = _read_json_lines(audit)
    if name is None:
        return rows
    return [r for r in rows if r.get("event") == name]


def _audit_bytes(audit: Path) -> bytes:
    if not audit.is_file():
        return b""
    return audit.read_bytes()


def _body_hash(path: Path) -> str:
    """與 reconcile_body_hash.sh 同算法：## 戳記 前本體 sha256。"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    body_lines: list[str] = []
    for ln in lines:
        if re.match(r"^##\s*戳記", ln):
            break
        body_lines.append(ln)
    body = "".join(body_lines)
    # head -n N | shasum 會保留換行；與腳本一致用 bytes
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _write_stamp_target(
    path: Path,
    *,
    stamps: list[str] | None = None,
    body: str = "synth body for stamp inject tests\n",
) -> str:
    """寫入含 ## 戳記 區的目標檔；回傳 body_hash。"""
    content = body + "\n## 戳記\n\n"
    if stamps:
        content += "\n".join(stamps) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return _body_hash(path)


def _stamp_line(
    fam: str,
    task_id: str,
    body_hash: str,
    *,
    verdict: str = "APPROVED",
    day: str | None = None,
    field_order: str = "sha_then_task",
) -> str:
    d = day or date.today().isoformat()
    if field_order == "task_then_sha":
        return f"RECONCILE-STAMP: {fam} {verdict} {d} task:{task_id} sha256:{body_hash}"
    return f"RECONCILE-STAMP: {fam} {verdict} {d} sha256:{body_hash} task:{task_id}"


def _harness(tmp_path: Path) -> dict:
    """隔離 repo：scripts 副本 + 空 audit + handoffs + gate dir。"""
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    handoffs = root / "handoffs"
    handoffs.mkdir()
    gate_dir = root / ".claude" / "gate"
    gate_dir.mkdir(parents=True)
    audit = gate_dir / "audit.log"
    audit.write_text("", encoding="utf-8")

    for name in _SCRIPT_NAMES:
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
            if name.endswith(".sh"):
                (scripts / name).chmod(0o755)

    # committee_run 用 always-pass gate stub（不寫 committee_dispatch）
    (scripts / "gate_pass.sh").write_text(
        "#!/usr/bin/env bash\necho GATE PASS stub\nexit 0\n",
        encoding="utf-8",
    )
    (scripts / "gate_pass.sh").chmod(0o755)

    env = {
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
        "GATE_DIR_OVERRIDE": str(gate_dir),
        "CX_STUB_MODE": "success",
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
    }
    return {
        "root": root,
        "audit": audit,
        "gate_dir": gate_dir,
        "scripts": scripts,
        "env": env,
        "handoffs": handoffs,
    }


def _patch_committee_gate(scripts: Path) -> None:
    path = scripts / "committee_run.sh"
    text = path.read_text(encoding="utf-8")
    old = 'bash "${SCRIPT_DIR}/gate.sh" dispatch "${gate_args[@]}"'
    new = 'bash "${SCRIPT_DIR}/gate_pass.sh" dispatch "${gate_args[@]}"'
    assert old in text, "gate call anchor missing"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _write_brief(
    h: dict,
    *,
    kind: str = "stamp",
    stamp_target: str | None = "handoffs/target.md",
    extra_stamp_targets: list[str] | None = None,
    name: str = "brief.md",
    extra_body: str = "",
) -> Path:
    lines = [f"brief-kind: {kind}", ""]
    if kind == "stamp" and stamp_target is not None:
        lines.append(f"stamp-target: {stamp_target}")
        if extra_stamp_targets:
            for st in extra_stamp_targets:
                lines.append(f"stamp-target: {st}")
        lines.append("")
    if kind in ("review", "consult", "closure"):
        lines.append("templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做")
        lines.append("fact-verified: unit-test → harness")
        lines.append("assumed: isolated env")
        lines.append("")
    lines.append(extra_body or f"stub brief kind={kind}\n")
    path = h["handoffs"] / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _open_round(
    h: dict,
    *,
    round_id: str,
    session: str,
    fams: list[str],
    out_prefix: str,
    brief_rel: str,
    task_id: str = "P16-D001-T1",
    omit_task_id: bool = False,
    empty_task_id: bool = False,
) -> None:
    """開債。缺/空 task_id 無法走 audit_append（必填），改直接種 JSON 行。"""
    brief_path = h["root"] / brief_rel
    brief_sha = hashlib.sha256(brief_path.read_bytes()).hexdigest()
    outputs = {f: f"{out_prefix}-{f}.md" for f in fams}

    if omit_task_id or empty_task_id:
        # 偽造殘缺 open_ev（僅測試第⑦道前置）；audit_append 拒寫缺/空 task_id
        rec: dict = {
            "event": "committee_round_open",
            "round_id": round_id,
            "brief_path": brief_rel,
            "brief_sha256": brief_sha,
            "brief_sha256_norm": brief_sha,
            "lock_mode": "discovery",
            "participants": fams,
            "expected_outputs": outputs,
            "session_name": session,
            "actor": "test",
            "origin_script": "committee_run.sh",
            "schema_version": 1,
            "sequence": 1,
            "ts": "2026-08-02T00:00:00Z",
            "event_id": "00000000-0000-4000-8000-000000000099",
            "producer": "test",
        }
        if empty_task_id:
            rec["task_id"] = ""
        # omit_task_id：不放 task_id 鍵
        with h["audit"].open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return

    participants = json.dumps(fams)
    outputs_json = json.dumps(outputs)
    fields = [
        f"round_id={round_id}",
        f"task_id={task_id}",
        f"brief_path={brief_rel}",
        f"brief_sha256={brief_sha}",
        f"brief_sha256_norm={brief_sha}",
        "lock_mode=discovery",
        f"participants=@{participants}",
        f"expected_outputs=@{outputs_json}",
        f"session_name={session}",
        "actor=test",
        "origin_script=committee_run.sh",
    ]
    args: list[str] = [
        "--require-absent-session",
        session,
        "--event",
        "committee_round_open",
    ]
    for f in fields:
        args.extend(["--field", f])
    r = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        *args,
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode == 0, r.stdout + r.stderr


def _plant_dispatch(h: dict, task_id: str) -> None:
    """種入 committee_dispatch（register-output 前置）。"""
    rec = {
        "event": "committee_dispatch",
        "task_id": task_id,
        "family": "unknown",
        "output_path": "",
        "output_sha256": "pending",
        "ts": "2026-08-02T00:00:00Z",
    }
    with h["audit"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def _run_cx(
    h: dict,
    fam: str,
    brief_rel: str,
    out_rel: str,
    *,
    round_id: str,
    env_overlay: dict[str, str] | None = None,
    stub: str | None = "success",
) -> subprocess.CompletedProcess[str]:
    env = dict(h["env"])
    env["ROUND_ID"] = round_id
    if stub is None:
        env.pop("CX_STUB_MODE", None)
    else:
        env["CX_STUB_MODE"] = stub
    if env_overlay:
        env.update(env_overlay)
    return _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        fam,
        brief_rel,
        out_rel,
        env=env,
        cwd=h["root"],
    )


def _run_committee(
    h: dict,
    *,
    brief_rel: str,
    out_prefix: str = "handoffs/out",
    fams: str = "codex",
    session: str = "sess-d001",
    task_id: str = "P16-D001-T1",
) -> subprocess.CompletedProcess[str]:
    _patch_committee_gate(h["scripts"])
    return _dph.run_cmd(
        h["scripts"] / "committee_run.sh",
        "--session",
        session,
        brief_rel,
        out_prefix,
        fams,
        "--",
        "--intent",
        "d001-test",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit",
        "--review-role",
        "advisory",
        "--template",
        "n/a:stub",
        "--task-id",
        task_id,
        env=h["env"],
        cwd=h["root"],
    )


def _token_mtime(h: dict) -> float | None:
    tok = h["gate_dir"] / "dispatch.token"
    if not tok.is_file():
        return None
    return tok.stat().st_mtime


def _debt_has_open(h: dict) -> int:
    """debt_ledger --has-open；rc==0 表示無 OPEN 債。"""
    r = _dph.run_cmd(
        h["scripts"] / "debt_ledger.sh",
        "--has-open",
        env=h["env"],
        cwd=h["root"],
    )
    return r.returncode


# ── V1–V3：task_id 注入 ──────────────────────────────────────────


def test_v1_prompt_contains_task_id_via_cli_spy(tmp_path: Path) -> None:
    """V1：spy 捕獲的 prompt 字串含 你的 task-id=<open_ev.task_id> 逐字。"""
    h = _harness(tmp_path)
    task_id = "P16-D001-V1-TASK"
    target = h["handoffs"] / "target.md"
    _write_stamp_target(target)
    brief_rel = "handoffs/brief.md"
    _write_brief(h, stamp_target="handoffs/target.md", name="brief.md")
    rid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    _open_round(
        h,
        round_id=rid,
        session="s-v1",
        fams=["codex"],
        out_prefix="handoffs/v1",
        brief_rel=brief_rel,
        task_id=task_id,
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/v1-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert capture.is_file(), "CLI spy 未寫入 CX_PROMPT_CAPTURE"
    prompt = capture.read_text(encoding="utf-8")
    expected = f"{_TASK_ID_INJECT_PREFIX}{task_id}{_TASK_ID_INJECT_SUFFIX}"
    assert expected in prompt, f"prompt 缺逐字注入句:\n{prompt!r}"
    # 禁止以 static grep 充當通過：spy 檔必須非空且含 task_id
    assert task_id in prompt


def test_v2_missing_task_id_rejected_zero_audit(tmp_path: Path) -> None:
    """V2：open_ev 缺 task_id → rc≠0 且 audit 零新增。"""
    h = _harness(tmp_path)
    target = h["handoffs"] / "target.md"
    _write_stamp_target(target)
    brief_rel = "handoffs/brief.md"
    _write_brief(h, name="brief.md")
    rid = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    _open_round(
        h,
        round_id=rid,
        session="s-v2",
        fams=["codex"],
        out_prefix="handoffs/v2",
        brief_rel=brief_rel,
        omit_task_id=True,
    )
    before = _audit_bytes(h["audit"])
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/v2-codex.md", round_id=rid
    )
    assert r.returncode != 0
    assert "task_id" in (r.stdout + r.stderr)
    assert _audit_bytes(h["audit"]) == before
    assert _events(h["audit"], "committee_family_result") == []


def test_v3_empty_task_id_rejected_zero_audit(tmp_path: Path) -> None:
    """V3：open_ev.task_id 為空字串 → rc≠0 且 audit 零新增。"""
    h = _harness(tmp_path)
    target = h["handoffs"] / "target.md"
    _write_stamp_target(target)
    brief_rel = "handoffs/brief.md"
    _write_brief(h, name="brief.md")
    rid = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    _open_round(
        h,
        round_id=rid,
        session="s-v3",
        fams=["codex"],
        out_prefix="handoffs/v3",
        brief_rel=brief_rel,
        empty_task_id=True,
    )
    before = _audit_bytes(h["audit"])
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/v3-codex.md", round_id=rid
    )
    assert r.returncode != 0
    assert _audit_bytes(h["audit"]) == before


# ── V4–V6：committee_run stamp-target（gate 之前）────────────────


def _assert_v4_style_fail(h: dict, r: subprocess.CompletedProcess[str], before: bytes) -> None:
    assert r.returncode == 2, r.stdout + r.stderr
    assert _audit_bytes(h["audit"]) == before, "audit 必須逐位元組零新增"
    assert _events(h["audit"], "committee_dispatch") == []
    assert _events(h["audit"], "committee_round_open") == []
    # 未發 token：dispatch.token 不得存在（可證偽，禁止恆真 or True）
    assert not (h["gate_dir"] / "dispatch.token").is_file()
    assert _token_mtime(h) is None
    assert _debt_has_open(h) == 0


def test_v4_stamp_missing_target_rc2_zero_audit(tmp_path: Path) -> None:
    """V4：brief-kind=stamp 缺 stamp-target → rc=2，audit 零新增，未發 token。"""
    h = _harness(tmp_path)
    _write_brief(h, stamp_target=None, name="brief.md")  # 無 stamp-target 行
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, brief_rel="handoffs/brief.md")
    _assert_v4_style_fail(h, r, before)


def test_v5_stamp_two_inconsistent_targets_rc2(tmp_path: Path) -> None:
    """V5：兩個不一致 stamp-target → rc=2，audit 零新增。"""
    h = _harness(tmp_path)
    (h["handoffs"] / "a.md").write_text("a\n", encoding="utf-8")
    (h["handoffs"] / "b.md").write_text("b\n", encoding="utf-8")
    _write_brief(
        h,
        stamp_target="handoffs/a.md",
        extra_stamp_targets=["handoffs/b.md"],
        name="brief.md",
    )
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, brief_rel="handoffs/brief.md")
    _assert_v4_style_fail(h, r, before)


def test_v6_stamp_target_outside_handoffs(tmp_path: Path) -> None:
    """V6a：stamp-target 在 handoffs/ 外 → rc=2。"""
    h = _harness(tmp_path)
    outside = h["root"] / "outside.md"
    outside.write_text("x\n", encoding="utf-8")
    _write_brief(h, stamp_target="outside.md", name="brief.md")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, brief_rel="handoffs/brief.md")
    _assert_v4_style_fail(h, r, before)


def test_v6_stamp_target_has_dotdot(tmp_path: Path) -> None:
    """V6b：stamp-target 含 .. → rc=2。"""
    h = _harness(tmp_path)
    _write_brief(h, stamp_target="handoffs/../handoffs/x.md", name="brief.md")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, brief_rel="handoffs/brief.md")
    _assert_v4_style_fail(h, r, before)


def test_v6_stamp_target_file_missing(tmp_path: Path) -> None:
    """V6c：stamp-target 檔不存在 → rc=2。"""
    h = _harness(tmp_path)
    _write_brief(h, stamp_target="handoffs/no-such-file.md", name="brief.md")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, brief_rel="handoffs/brief.md")
    _assert_v4_style_fail(h, r, before)


def test_v6_direct_cx_run_missing_target_no_cli(tmp_path: Path) -> None:
    """V6 直呼：缺 stamp-target → rc==2 且 CLI 未啟動（spy 次數 0）、audit 零新增。"""
    h = _harness(tmp_path)
    _write_brief(h, stamp_target=None, name="brief.md")
    rid = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    # 即使 open_ev 存在，stamp-target 檢查在前置之前
    brief_rel = "handoffs/brief.md"
    _open_round(
        h,
        round_id=rid,
        session="s-v6d",
        fams=["codex"],
        out_prefix="handoffs/v6d",
        brief_rel=brief_rel,
    )
    before = _audit_bytes(h["audit"])
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/v6d-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert not capture.is_file(), "CLI/spy 不得啟動"
    assert _audit_bytes(h["audit"]) == before
    assert _events(h["audit"], "committee_family_result") == []


# ── V7–V11、V13–V15：auto register-output ──────────────────────


def _setup_stamp_success(
    h: dict,
    *,
    fam: str = "codex",
    task_id: str = "P16-D001-REG",
    plant_dispatch: bool = True,
    stamp_verdict: str = "APPROVED",
    stamp_task: str | None = None,
    wrong_hash: bool = False,
    cross_line: bool = False,
    no_stamp_section: bool = False,
    field_order: str = "sha_then_task",
    rid: str = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
) -> tuple[str, str, str]:
    """準備 stamp brief + target + open round；回傳 (rid, task_id, brief_rel)。"""
    target_rel = "handoffs/target.md"
    target = h["handoffs"] / "target.md"
    brief_rel = "handoffs/brief.md"
    if no_stamp_section:
        target.write_text("no stamp section at all\n", encoding="utf-8")
        bh = "0" * 64
    else:
        # 先寫 body 算 hash，再寫正確/錯誤戳記
        body = "register-output target body\n"
        # 預寫以算 hash
        target.write_text(body + "\n## 戳記\n\n", encoding="utf-8")
        bh = _body_hash(target)
        use_task = stamp_task if stamp_task is not None else task_id
        use_hash = ("f" * 64) if wrong_hash else bh
        if cross_line:
            # fam=codex：codex 行 APPROVED+錯 task；composer 行正確 task
            # naive 雙 grep 會把跨行組合成 true；單行匹配必須為 false
            stamps = [
                _stamp_line("codex", "WRONG-OTHER-TASK", bh, verdict="APPROVED"),
                _stamp_line("composer", task_id, bh, verdict="APPROVED"),
            ]
        else:
            stamps = [
                _stamp_line(
                    fam,
                    use_task,
                    use_hash,
                    verdict=stamp_verdict,
                    field_order=field_order,
                ),
            ]
        _write_stamp_target(target, stamps=stamps, body=body)

    _write_brief(h, stamp_target=target_rel, name="brief.md")
    out_prefix = "handoffs/reg"
    _open_round(
        h,
        round_id=rid,
        session=f"s-{rid[:8]}",
        fams=[fam],
        out_prefix=out_prefix,
        brief_rel=brief_rel,
        task_id=task_id,
    )
    if plant_dispatch:
        _plant_dispatch(h, task_id)
    return rid, task_id, brief_rel


def test_v7_success_registers_one_committee_output(tmp_path: Path) -> None:
    """V7：stub 成功且相符戳記 → 恰一筆 committee_output，path=stamp-target，sha≠pending。"""
    h = _harness(tmp_path)
    task_id = "P16-D001-V7"
    rid, _, brief_rel = _setup_stamp_success(
        h, fam="codex", task_id=task_id, plant_dispatch=True,
        rid="f1111111-1111-4111-8111-111111111111",
    )
    before_out = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    outs = _events(h["audit"], "committee_output")
    assert len(outs) - before_out == 1
    last = outs[-1]
    assert last.get("output_path") == "handoffs/target.md"
    sha = last.get("output_sha256") or ""
    assert len(sha) == 64
    assert sha != "pending"
    results = _events(h["audit"], "committee_family_result")
    assert results and results[-1].get("result_state") == "success"


def test_v8_no_family_stamp_zero_output(tmp_path: Path) -> None:
    """V8：目標無該家族戳記 → 零 committee_output。"""
    h = _harness(tmp_path)
    task_id = "P16-D001-V8"
    # 只寫 composer 戳記，派 codex
    target = h["handoffs"] / "target.md"
    body = "v8 body\n"
    target.write_text(body + "\n## 戳記\n\n", encoding="utf-8")
    bh = _body_hash(target)
    _write_stamp_target(
        target,
        stamps=[_stamp_line("composer", task_id, bh)],
        body=body,
    )
    _write_brief(h, stamp_target="handoffs/target.md")
    rid = "f2222222-2222-4222-8222-222222222222"
    _open_round(
        h,
        round_id=rid,
        session="s-v8",
        fams=["codex"],
        out_prefix="handoffs/reg",
        brief_rel="handoffs/brief.md",
        task_id=task_id,
    )
    _plant_dispatch(h, task_id)
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", "handoffs/brief.md", "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) == before


def test_v9_wrong_task_id_zero_output(tmp_path: Path) -> None:
    """V9：APPROVED 但 task: 是別的 id → 零 committee_output。"""
    h = _harness(tmp_path)
    rid, task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-V9",
        stamp_task="OTHER-TASK-ID",
        rid="f3333333-3333-4333-8333-333333333333",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) == before


def test_v10_rejected_stamp_zero_output(tmp_path: Path) -> None:
    """V10：該家族 REJECTED → 零 committee_output；rc 不變。"""
    h = _harness(tmp_path)
    rid, task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-V10",
        stamp_verdict="REJECTED",
        rid="f4444444-4444-4444-8444-444444444444",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) == before
    # 合法 no-op：stderr 不含 register-output 失敗字樣
    assert "register-output 失敗" not in (r.stdout + r.stderr)


def test_v11_cli_fail_zero_output_family_failed(tmp_path: Path) -> None:
    """V11：CLI rc≠0 → 零 committee_output；family_result result_state=failed。"""
    h = _harness(tmp_path)
    rid, task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-V11",
        rid="f5555555-5555-4555-8555-555555555555",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/reg-codex.md",
        round_id=rid,
        stub="fail_rc",
    )
    assert r.returncode != 0
    assert len(_events(h["audit"], "committee_output")) == before
    results = _events(h["audit"], "committee_family_result")
    assert results and results[-1].get("result_state") == "failed"


@pytest.mark.parametrize("kind", ("review", "consult", "closure", "impl"))
def test_v12_non_stamp_kinds_no_stamp_target_ok(tmp_path: Path, kind: str) -> None:
    """V12：review/consult/closure/impl 無 stamp-target → 不誤擋（與延伸前行為一致）。

    🔴 票 B-49 閉合條件 1／2（**兩處修正，缺一不可**）：
      ① 原為 `for kind in (...)` 單一測試 ⇒ **從 receipt 看不出跑了幾個 kind**，
         中途早退也只計一次。改參數化後每個 kind 各一格 ⇒ `passed == 4` 即 per-kind receipt。
      ② 原有「implementer 不在三家就靜默早退」的逃生口 ⇒ 使用者把 implementer 改成
         編排端（無 CLI 配方）時本測**假綠**。改為以 `_role_pin` 釘沙箱名冊：
         沙箱內一定是有 CLI 配方的家族，**不需要**也**不得有**任何早退分支。
         釘不成（名冊壞／家族清單漂移）⇒ `_role_pin` 自己 fail-closed 拋錯，不是早退。
    """
    h = _harness(tmp_path / kind)
    # impl 走實作端路徑：釘沙箱名冊，與生產 implementer 解耦（票 B-49）
    if kind == "impl":
        fam = _role_pin.pin_implementer(h["scripts"])
    else:
        # 🔴 review/consult/closure 一律取**非實作者**家族。原寫死 "codex"：
        #    只要 implementer 恰好是 codex，角色閘就以「實作者不自審」整批拒絕
        #    ⇒ 本測與名冊耦合，換人實作即回紅。硬編家族名是本票要根除的病。
        _impl = json.loads(
            (h["scripts"] / "governance_roles.json").read_text(encoding="utf-8")
        )["implementer"]
        _cands = [
            f for f in _role_pin.cli_dispatchable_families(h["scripts"]) if f != _impl
        ]
        assert _cands, f"沙箱內無非實作者之 CLI 家族（implementer={_impl}）⇒ fail-closed"
        fam = _cands[0]
    brief_rel = "handoffs/brief.md"
    _write_brief(h, kind=kind, stamp_target=None, name="brief.md")
    rid = {
        "review": "12111111-1111-4111-8111-111111111111",
        "consult": "12222222-2222-4222-8222-222222222222",
        "closure": "12333333-3333-4333-8333-333333333333",
        "impl": "12444444-4444-4444-8444-444444444444",
    }[kind]
    _open_round(
        h,
        round_id=rid,
        session=f"s-v12-{kind}",
        fams=[fam],
        out_prefix=f"handoffs/v12{kind}",
        brief_rel=brief_rel,
        task_id=f"P16-D001-V12-{kind}",
    )
    r = _run_cx(
        h,
        fam,
        brief_rel,
        f"handoffs/v12{kind}-{fam}.md",
        round_id=rid,
    )
    assert r.returncode == 0, f"kind={kind}: {r.stdout + r.stderr}"
    assert _events(h["audit"], "committee_output") == []


def test_v13_register_fail_distinguishable_from_noop(tmp_path: Path) -> None:
    """V13：三條件成立但無 committee_dispatch → 可辨識錯誤；family_result=success；零 output。"""
    h = _harness(tmp_path)
    rid, task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-V13",
        plant_dispatch=False,  # 刻意不種 → register-output rc≠0
        rid="f6666666-6666-4666-8666-666666666666",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert "register-output 失敗" in combined or "待人工補記" in combined, combined
    assert len(_events(h["audit"], "committee_output")) == before
    results = _events(h["audit"], "committee_family_result")
    assert results and results[-1].get("result_state") == "success"
    # 與 V8/V10 合法 no-op 機械可分：no-op 無此錯誤字串
    assert "待人工補記" in combined or "register-output 失敗" in combined


def test_v14_cross_line_stamp_zero_output(tmp_path: Path) -> None:
    """V14：跨行組合（A APPROVED+錯 task／B 正確 task）→ 零 committee_output。"""
    h = _harness(tmp_path)
    rid, task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-V14",
        cross_line=True,
        rid="f7777777-7777-4777-8777-777777777777",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) == before


def test_v15_wrong_sha256_zero_output(tmp_path: Path) -> None:
    """V15：sha256 非該檔 body hash → 零 committee_output。"""
    h = _harness(tmp_path)
    rid, task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-V15",
        wrong_hash=True,
        rid="f8888888-8888-4888-8888-888888888888",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) == before


def test_v_no_stamp_section_legal_noop(tmp_path: Path) -> None:
    """邊界：目標無 ## 戳記 → reconcile_body_hash rc≠0 → 合法 no-op。"""
    h = _harness(tmp_path)
    rid, task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-NOS",
        no_stamp_section=True,
        rid="f9999999-9999-4999-8999-999999999999",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) == before
    assert "register-output 失敗" not in (r.stdout + r.stderr)
    # body_hash stderr 不得逸出
    assert "缺『## 戳記』" not in (r.stdout + r.stderr)


# ── V16–V18：code review 修補 oracle ───────────────────────────


def test_v16_dot_task_id_no_false_match(tmp_path: Path) -> None:
    """V16：task_id 含 `.` 且目標僅有同位置換一字元的 task: 戳記 → 零 committee_output。

    例：open_ev.task_id=P16.D001-TASK，戳記 task:P16XD001-TASK（`.`→`X`）。
    未跳脫時 ERE 的 `.` 會誤配；跳脫後必須零註冊。
    """
    h = _harness(tmp_path)
    task_id = "P16.D001-TASK"
    wrong_task = "P16XD001-TASK"
    assert len(task_id) == len(wrong_task)
    assert task_id != wrong_task
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id=task_id,
        stamp_task=wrong_task,
        plant_dispatch=True,
        rid="a6666666-6666-4666-8666-666666666666",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) == before, (
        "含 `.` 的 task_id 不得誤配同位置換字元戳記（群 A fail-open）"
    )


def test_v17_reversed_field_order_registers(tmp_path: Path) -> None:
    """V17：戳記寫成 `task:<id> sha256:<hash>`（反序）→ 恰一筆 committee_output。

    跨行組合仍須零註冊（V14 不得退化）——本條只驗反序單行仍註冊。
    """
    h = _harness(tmp_path)
    task_id = "P16-D001-V17"
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id=task_id,
        plant_dispatch=True,
        field_order="task_then_sha",
        rid="a7777777-7777-4777-8777-777777777777",
    )
    before = len(_events(h["audit"], "committee_output"))
    r = _run_cx(
        h, "codex", brief_rel, "handoffs/reg-codex.md", round_id=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    outs = _events(h["audit"], "committee_output")
    assert len(outs) - before == 1, (
        f"反序戳記應自動註冊；got delta={len(outs) - before} stderr={r.stderr!r}"
    )
    assert outs[-1].get("output_path") == "handoffs/target.md"

    # V14 不退化：同一 harness 另建 cross_line 場景
    h2 = _harness(tmp_path / "v14-regression")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-V17-X",
        cross_line=True,
        plant_dispatch=True,
        rid="a7788888-8888-4888-8888-888888888888",
    )
    before2 = len(_events(h2["audit"], "committee_output"))
    r2 = _run_cx(
        h2, "codex", brief2, "handoffs/reg-codex.md", round_id=rid2
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert len(_events(h2["audit"], "committee_output")) == before2


def test_v18_missing_brief_kind_rc2_zero_audit(tmp_path: Path) -> None:
    """V18：brief 缺 brief-kind: → committee_run rc=2、audit 逐位元組零新增、未發 token、無 OPEN 債。"""
    h = _harness(tmp_path)
    # 刻意不寫 brief-kind:
    brief = h["handoffs"] / "brief.md"
    brief.write_text(
        "stamp-target: handoffs/target.md\n\nstub brief missing kind\n",
        encoding="utf-8",
    )
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, brief_rel="handoffs/brief.md")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "brief-kind" in (r.stdout + r.stderr)
    assert _audit_bytes(h["audit"]) == before
    assert not (h["gate_dir"] / "dispatch.token").is_file()
    assert _token_mtime(h) is None
    assert _debt_has_open(h) == 0
    assert _events(h["audit"], "committee_round_open") == []


def _assert_unknown_kind_rejected(
    h: dict, kind_line: str, *, expect_unknown_token: str | None = None
) -> None:
    """V19–V21 共用：未知 brief-kind → rc=2、audit 零新增、未發 token、無 OPEN 債。"""
    brief = h["handoffs"] / "brief.md"
    brief.write_text(
        f"{kind_line}\nstamp-target: handoffs/target.md\n\nstub unknown kind\n",
        encoding="utf-8",
    )
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, brief_rel="handoffs/brief.md")
    assert r.returncode == 2, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert "brief-kind" in out or "未知" in out
    if expect_unknown_token is not None:
        assert expect_unknown_token in out, (
            f"error should mention full value {expect_unknown_token!r}; got {out!r}"
        )
    assert _audit_bytes(h["audit"]) == before
    assert not (h["gate_dir"] / "dispatch.token").is_file()
    assert _token_mtime(h) is None
    assert _debt_has_open(h) == 0
    assert _events(h["audit"], "committee_round_open") == []


def test_v19_prefix_plus_suffix_kind_rejected(tmp_path: Path) -> None:
    """V19：brief-kind: stamp-evil（合法前綴＋後綴）→ rc=2、audit 零新增、未發 token、無 OPEN 債。

    前綴擷取 [a-z]+ 會把 stamp-evil 截成 stamp 而誤放行；整值比對必須拒絕。
    """
    _assert_unknown_kind_rejected(
        _harness(tmp_path),
        "brief-kind: stamp-evil",
        expect_unknown_token="stamp-evil",
    )


def test_v20_suffix_is_legal_kind_rejected(tmp_path: Path) -> None:
    """V20：brief-kind: evilstamp（後綴為合法值）→ rc=2、audit 零新增、未發 token、無 OPEN 債。"""
    _assert_unknown_kind_rejected(
        _harness(tmp_path),
        "brief-kind: evilstamp",
        expect_unknown_token="evilstamp",
    )


def test_v21_fully_unknown_kind_rejected(tmp_path: Path) -> None:
    """V21：brief-kind: bogus（完全未知）→ rc=2、audit 零新增、未發 token、無 OPEN 債。"""
    _assert_unknown_kind_rejected(
        _harness(tmp_path),
        "brief-kind: bogus",
        expect_unknown_token="bogus",
    )


# ── 群 H：E 類邊界永久回歸矩陣（CODEX-R3-P2-02）────────────────
#
# 9 列 × 2 入口（committee_run ＋ 直呼 cx_run）parity。
# 接受／拒絕判定必須一致；不一致即失敗。
# 拒：rc=2、audit 逐位元組零新增、未發 token、無 OPEN 債。
# 放行：rc=0（trim 尾空白／sort -u 同值去重為刻意行為，§D6#19）。

_GROUP_H_MATRIX: list[tuple[str, list[str], bool, str | None]] = [
    # (case_id, brief-kind 行（可多行）, expect_accept, expect_token_in_error)
    ("stamp-evil", ["brief-kind: stamp-evil"], False, "stamp-evil"),
    ("evilstamp", ["brief-kind: evilstamp"], False, "evilstamp"),
    ("stampx", ["brief-kind: stampx"], False, "stampx"),
    ("bogus", ["brief-kind: bogus"], False, "bogus"),
    ("STAMP", ["brief-kind: STAMP"], False, "STAMP"),
    ("empty", ["brief-kind:"], False, None),
    ("trailing-space", ["brief-kind: stamp "], True, None),
    ("dup-identical", ["brief-kind: stamp", "brief-kind: stamp"], True, None),
    (
        "dup-inconsistent",
        ["brief-kind: stamp", "brief-kind: review"],
        False,
        None,
    ),
]


def _group_h_write_brief(h: dict, kind_lines: list[str], *, name: str = "brief.md") -> Path:
    """寫入含 stamp-target 的 brief（放行列需要；拒列也附上以排除缺欄混淆）。"""
    lines = list(kind_lines) + [
        "stamp-target: handoffs/target.md",
        "",
        "stub group-H matrix\n",
    ]
    path = h["handoffs"] / name
    path.write_text("\n".join(lines), encoding="utf-8")
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    return path


def _group_h_assert_reject(
    h: dict,
    r: subprocess.CompletedProcess[str],
    before: bytes,
    *,
    expect_token: str | None,
    entry: str,
    case_id: str,
) -> None:
    assert r.returncode == 2, (
        f"群H {case_id}/{entry} 應拒 rc=2；got {r.returncode}\n"
        f"{r.stdout}{r.stderr}"
    )
    out = r.stdout + r.stderr
    assert "brief-kind" in out or "未知" in out or "不一致" in out or "缺" in out, (
        f"群H {case_id}/{entry} 錯誤訊息應涉及 brief-kind；got {out!r}"
    )
    if expect_token is not None:
        assert expect_token in out, (
            f"群H {case_id}/{entry} 錯誤應含完整值 {expect_token!r}；got {out!r}"
        )
    assert _audit_bytes(h["audit"]) == before, (
        f"群H {case_id}/{entry} audit 必須逐位元組零新增"
    )
    assert not (h["gate_dir"] / "dispatch.token").is_file()
    assert _token_mtime(h) is None
    assert _debt_has_open(h) == 0
    # 不得新開債（pre-plant 亦不得有 open，本矩陣拒列不預種 open）
    assert _events(h["audit"], "committee_round_open") == []


def _group_h_run_committee(
    h: dict, *, session: str = "sess-h"
) -> subprocess.CompletedProcess[str]:
    return _run_committee(
        h,
        brief_rel="handoffs/brief.md",
        out_prefix="handoffs/out-h",
        session=session,
        task_id="P16-D001-H1",
    )


def _group_h_run_cx_direct(
    h: dict, *, rid: str
) -> subprocess.CompletedProcess[str]:
    """直呼 cx_run（parity 入口）。拒列不需 open_ev；放行列由呼叫端先 _open_round。"""
    return _run_cx(
        h,
        "codex",
        "handoffs/brief.md",
        "handoffs/out-h-codex.md",
        round_id=rid,
    )


@pytest.mark.parametrize(
    "case_id,kind_lines,expect_accept,expect_token",
    _GROUP_H_MATRIX,
    ids=[c[0] for c in _GROUP_H_MATRIX],
)
def test_group_h_e_boundary_matrix_committee(
    tmp_path: Path,
    case_id: str,
    kind_lines: list[str],
    expect_accept: bool,
    expect_token: str | None,
) -> None:
    """群 H 入口 1：committee_run 對 E 邊界矩陣的接受／拒絕判定。"""
    h = _harness(tmp_path)
    _group_h_write_brief(h, kind_lines)
    before = _audit_bytes(h["audit"])
    r = _group_h_run_committee(h, session=f"sess-h-cr-{case_id}")
    if expect_accept:
        assert r.returncode == 0, (
            f"群H {case_id}/committee 應放行 rc=0；got {r.returncode}\n"
            f"{r.stdout}{r.stderr}"
        )
        assert _audit_bytes(h["audit"]) != before, "放行應寫入 audit（開債）"
        assert len(_events(h["audit"], "committee_round_open")) >= 1
    else:
        _group_h_assert_reject(
            h,
            r,
            before,
            expect_token=expect_token,
            entry="committee",
            case_id=case_id,
        )


@pytest.mark.parametrize(
    "case_id,kind_lines,expect_accept,expect_token",
    _GROUP_H_MATRIX,
    ids=[c[0] for c in _GROUP_H_MATRIX],
)
def test_group_h_e_boundary_matrix_cx_direct(
    tmp_path: Path,
    case_id: str,
    kind_lines: list[str],
    expect_accept: bool,
    expect_token: str | None,
) -> None:
    """群 H 入口 2：直呼 cx_run 對同一矩陣的接受／拒絕判定（parity）。"""
    h = _harness(tmp_path)
    _group_h_write_brief(h, kind_lines)
    rid = f"hhhhhhhh-hhhh-4hhh-8hhh-{case_id.encode().hex()[:12].ljust(12, '0')}"
    if expect_accept:
        # 放行路徑需合法 open_ev（brief-kind 通過後才走六道前置）
        _open_round(
            h,
            round_id=rid,
            session=f"s-h-cx-{case_id}",
            fams=["codex"],
            out_prefix="handoffs/out-h",
            brief_rel="handoffs/brief.md",
            task_id="P16-D001-H1",
        )
        before = _audit_bytes(h["audit"])
        r = _group_h_run_cx_direct(h, rid=rid)
        assert r.returncode == 0, (
            f"群H {case_id}/cx_direct 應放行 rc=0；got {r.returncode}\n"
            f"{r.stdout}{r.stderr}"
        )
        # family_result 應寫入（stub success）
        assert len(_events(h["audit"], "committee_family_result")) >= 1 or (
            _audit_bytes(h["audit"]) != before
        )
    else:
        before = _audit_bytes(h["audit"])
        r = _group_h_run_cx_direct(h, rid=rid)
        _group_h_assert_reject(
            h,
            r,
            before,
            expect_token=expect_token,
            entry="cx_direct",
            case_id=case_id,
        )


def test_group_h_committee_cx_parity_same_verdict(tmp_path: Path) -> None:
    """群 H parity：同一 brief 兩入口的接受／拒絕布林判定必須一致。"""
    mismatches: list[str] = []
    for case_id, kind_lines, expect_accept, _tok in _GROUP_H_MATRIX:
        h_cr = _harness(tmp_path / f"parity-cr-{case_id}")
        _group_h_write_brief(h_cr, kind_lines)
        r_cr = _group_h_run_committee(h_cr, session=f"parity-cr-{case_id}")
        cr_accept = r_cr.returncode == 0

        h_cx = _harness(tmp_path / f"parity-cx-{case_id}")
        _group_h_write_brief(h_cx, kind_lines)
        rid = f"hhhhhhhh-hhhh-4hhh-8hhh-{case_id.encode().hex()[:12].ljust(12, '0')}"
        if expect_accept:
            _open_round(
                h_cx,
                round_id=rid,
                session=f"parity-cx-{case_id}",
                fams=["codex"],
                out_prefix="handoffs/out-h",
                brief_rel="handoffs/brief.md",
                task_id="P16-D001-H1",
            )
        r_cx = _group_h_run_cx_direct(h_cx, rid=rid)
        cx_accept = r_cx.returncode == 0

        if cr_accept != cx_accept:
            mismatches.append(
                f"{case_id}: committee_accept={cr_accept}(rc={r_cr.returncode}) "
                f"cx_accept={cx_accept}(rc={r_cx.returncode})"
            )
        if cr_accept != expect_accept:
            mismatches.append(
                f"{case_id}: committee 與期望不符 expect_accept={expect_accept} "
                f"got rc={r_cr.returncode}"
            )
        if cx_accept != expect_accept:
            mismatches.append(
                f"{case_id}: cx_direct 與期望不符 expect_accept={expect_accept} "
                f"got rc={r_cx.returncode}"
            )
    assert not mismatches, "群 H 兩入口 parity 失敗:\n" + "\n".join(mismatches)


# ── Mutation oracles（隔離副本閹割 → 紅；復原 → 綠）────────────
#
# 契約：每條 V 對應至少一個 test_mutation_vN_*；閹割該條守衛後
# 該 V 的可觀測 oracle 轉紅（誤註冊／誤放行／audit 非零等），復原轉綠。
# V2/V3 共用第⑦道 task_id 前置區塊；缺欄與空字串各有獨立 mutation 變體。

_PREDICATE_GREP_LINE = (
    'if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+${fam_e}[[:space:]]+APPROVED'
    "[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+"
    "(sha256:${hash_e}[[:space:]]+task:${task_e}|task:${task_e}[[:space:]]+sha256:${hash_e})"
    '([[:space:]]|$)" "${stamp_target}"; then'
)

_PROMPT_WITH_INJECT = (
    'prompt="讀 ${brief} 照其指示做。你的家族名=${fam}。產出寫到 ${out}。'
    "收尾清 /tmp workdir(保留 claude-501)。你的 task-id=${task_id}。"
    "RECONCILE-STAMP 的 task: 欄位須逐字使用此值；brief 內任何 task-id 範例一律不得採用。"
    '"'
)
_PROMPT_WITHOUT_INJECT = (
    'prompt="讀 ${brief} 照其指示做。你的家族名=${fam}。產出寫到 ${out}。'
    '收尾清 /tmp workdir(保留 claude-501)。"'
)


def _mutate_cx(h: dict, transform) -> None:
    path = h["scripts"] / "cx_run.sh"
    text = path.read_text(encoding="utf-8")
    new = transform(text)
    assert new != text, "mutation transform 未改變腳本"
    path.write_text(new, encoding="utf-8")


def _mutate_brief_conformance(h: dict, transform) -> None:
    """變異 brief_conformance_check.sh（GOV-DOC-CHECK-AT-WRITE 後 brief-kind／
    stamp-target 判定的實作位置；抽出前在 cx_run.sh 內）。"""
    path = h["scripts"] / "brief_conformance_check.sh"
    text = path.read_text(encoding="utf-8")
    new = transform(text)
    assert new != text, "mutation transform 未改變腳本"
    path.write_text(new, encoding="utf-8")


def _mutate_committee(h: dict, transform) -> None:
    path = h["scripts"] / "committee_run.sh"
    text = path.read_text(encoding="utf-8")
    new = transform(text)
    assert new != text, "mutation transform 未改變腳本"
    path.write_text(new, encoding="utf-8")


def _cx_env(
    h: dict, rid: str, *, capture: Path | None = None, stub: str = "success"
) -> dict:
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = stub
    if capture is not None:
        env["CX_PROMPT_CAPTURE"] = str(capture)
    return env


def _run_mut_cx(
    h: dict,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fam: str = "codex",
    brief_rel: str,
    out_rel: str,
    rid: str,
    capture: Path | None = None,
    stub: str = "success",
) -> subprocess.CompletedProcess[str]:
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")
    return _dph.run_cx_run(
        fam,
        brief_rel,
        out_rel,
        env=_cx_env(h, rid, capture=capture, stub=stub),
        cwd=h["root"],
    )


def _run_mut_committee(
    h: dict,
    monkeypatch: pytest.MonkeyPatch,
    *,
    brief_rel: str = "handoffs/brief.md",
    task_id: str = "P16-D001-T1",
    session: str = "sess-d001",
) -> subprocess.CompletedProcess[str]:
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")
    _patch_committee_gate(h["scripts"])
    return _dph.run_committee_run(
        "--session",
        session,
        brief_rel,
        "handoffs/out",
        "codex",
        "--",
        "--intent",
        "d001-test",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit",
        "--review-role",
        "advisory",
        "--template",
        "n/a:stub",
        "--task-id",
        task_id,
        env=h["env"],
        cwd=h["root"],
    )


def test_mutation_v1_without_inject_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V1：閹割 task_id 注入句 → spy 斷言轉紅。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def strip_inject(text: str) -> str:
        assert _PROMPT_WITH_INJECT in text
        return text.replace(_PROMPT_WITH_INJECT, _PROMPT_WITHOUT_INJECT, 1)

    _mutate_cx(h, strip_inject)
    task_id = "P16-D001-MUT-V1"
    _write_stamp_target(h["handoffs"] / "target.md")
    _write_brief(h)
    rid = "a1111111-1111-4111-8111-111111111111"
    _open_round(
        h,
        round_id=rid,
        session="s-mut-v1",
        fams=["codex"],
        out_prefix="handoffs/mv1",
        brief_rel="handoffs/brief.md",
        task_id=task_id,
    )
    capture = h["root"] / "prompt.capture"
    r = _run_mut_cx(
        h,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/mv1-codex.md",
        rid=rid,
        capture=capture,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    expected = f"{_TASK_ID_INJECT_PREFIX}{task_id}{_TASK_ID_INJECT_SUFFIX}"
    assert expected not in capture.read_text(encoding="utf-8")

    h2 = _harness(tmp_path / "restore")
    _write_stamp_target(h2["handoffs"] / "target.md")
    _write_brief(h2)
    rid2 = "a2222222-2222-4222-8222-222222222222"
    _open_round(
        h2,
        round_id=rid2,
        session="s-mut-v1b",
        fams=["codex"],
        out_prefix="handoffs/mv1b",
        brief_rel="handoffs/brief.md",
        task_id=task_id,
    )
    cap2 = h2["root"] / "prompt.capture"
    r2 = _run_mut_cx(
        h2,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/mv1b-codex.md",
        rid=rid2,
        capture=cap2,
    )
    assert r2.returncode == 0
    assert expected in cap2.read_text(encoding="utf-8")


def _neuter_taskid_precheck(text: str) -> str:
    """V2/V3 共用：閹割第⑦道 task_id 缺/空前置。

    GOVFLOW-B3：字元白名單已抽到 ``_role_gate.sh``（SSOT）；本錨點只涵蓋
    Python 內缺/空/型別檢查。白名單另由 ``check-task-id`` 在捕獲後執行，
    合法 fallback 可通過白名單，故本 mutation 仍只證「缺/空被放行」。
    """
    old = (
        'task_id = open_ev.get("task_id")\n'
        'if task_id is None or (isinstance(task_id, str) and task_id == ""):\n'
        '    print("ERROR: open_ev 缺 task_id 或為空字串（第⑦道前置，拒派）", file=sys.stderr)\n'
        "    sys.exit(1)\n"
        "if not isinstance(task_id, str):\n"
        '    print(f"ERROR: open_ev.task_id 型別非法: {type(task_id).__name__}", file=sys.stderr)\n'
        "    sys.exit(1)\n"
        "print(task_id)\n"
    )
    new = (
        'task_id = open_ev.get("task_id")\n'
        'if task_id is None or not isinstance(task_id, str) or task_id == "":\n'
        '    task_id = "MUTATED-FALLBACK-TASK"\n'
        "print(task_id)\n"
    )
    assert old in text, "V2/V3 task_id precheck anchor missing"
    return text.replace(old, new, 1)


def test_mutation_v2_v3_shared_taskid_precheck_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V2/V3（共用）：閹割第⑦道 → 缺 task_id 仍放行；空字串變體各自可證偽。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    _mutate_cx(h, _neuter_taskid_precheck)
    _write_stamp_target(h["handoffs"] / "target.md")
    _write_brief(h)
    rid = "b0b0b0b0-b0b0-4b0b-8b0b-b0b0b0b0b0b0"
    _open_round(
        h,
        round_id=rid,
        session="s-mut-v2",
        fams=["codex"],
        out_prefix="handoffs/mv2",
        brief_rel="handoffs/brief.md",
        omit_task_id=True,
    )
    before = _audit_bytes(h["audit"])
    r = _run_mut_cx(
        h,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/mv2-codex.md",
        rid=rid,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert _audit_bytes(h["audit"]) != before
    assert _events(h["audit"], "committee_family_result")

    h2 = _harness(tmp_path / "restore-v2")
    _write_stamp_target(h2["handoffs"] / "target.md")
    _write_brief(h2)
    rid2 = "b1b1b1b1-b1b1-4b1b-8b1b-b1b1b1b1b1b1"
    _open_round(
        h2,
        round_id=rid2,
        session="s-mut-v2b",
        fams=["codex"],
        out_prefix="handoffs/mv2b",
        brief_rel="handoffs/brief.md",
        omit_task_id=True,
    )
    before2 = _audit_bytes(h2["audit"])
    r2 = _run_mut_cx(
        h2,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/mv2b-codex.md",
        rid=rid2,
    )
    assert r2.returncode != 0
    assert _audit_bytes(h2["audit"]) == before2

    # V3 空字串變體：只砍空字串分支、保留缺欄時，此段必須轉紅（否則 17 mutation 仍全綠）
    h3 = _harness(tmp_path / "mut-v3-empty")
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h3["scripts"] / "cx_run.sh")
    _mutate_cx(h3, _neuter_taskid_precheck)
    _write_stamp_target(h3["handoffs"] / "target.md")
    _write_brief(h3)
    rid3 = "b2b2b2b2-b2b2-4b2b-8b2b-b2b2b2b2b2b2"
    _open_round(
        h3,
        round_id=rid3,
        session="s-mut-v3",
        fams=["codex"],
        out_prefix="handoffs/mv3",
        brief_rel="handoffs/brief.md",
        empty_task_id=True,
    )
    before3 = _audit_bytes(h3["audit"])
    r3 = _run_mut_cx(
        h3,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/mv3-codex.md",
        rid=rid3,
    )
    assert r3.returncode == 0, r3.stdout + r3.stderr
    assert _audit_bytes(h3["audit"]) != before3
    assert _events(h3["audit"], "committee_family_result")

    h4 = _harness(tmp_path / "restore-v3-empty")
    _write_stamp_target(h4["handoffs"] / "target.md")
    _write_brief(h4)
    rid4 = "b3b3b3b3-b3b3-4b3b-8b3b-b3b3b3b3b3b3"
    _open_round(
        h4,
        round_id=rid4,
        session="s-mut-v3b",
        fams=["codex"],
        out_prefix="handoffs/mv3b",
        brief_rel="handoffs/brief.md",
        empty_task_id=True,
    )
    before4 = _audit_bytes(h4["audit"])
    r4 = _run_mut_cx(
        h4,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/mv3b-codex.md",
        rid=rid4,
    )
    assert r4.returncode != 0
    assert _audit_bytes(h4["audit"]) == before4


def test_incomplete_review_brief_rejected_before_debt_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX-R1-P1-01 迴歸：不完整的 review brief 必須在**開債前**被拒，audit 零成長。

    出生事故（實測，非推測）：本 repo audit sequence 367 —
      「閉合輪首次派工：brief 合規閘拒派（brief-kind=closure 須引用委員範本，主委漏寫）」。
    成因＝committee_run.sh 當時有**自己的**簡化 parser（只驗 kind 存不存在），
      而「範本引用 + fact-verified/assumed」只有 cx_run 驗，且 cx_run 在**開債之後**才跑
      ⇒ 債先開了才發現 brief 不合規，只能 --abandon。
    修法＝committee_run 改呼叫同一個 brief_conformance_check，且仍在 gate dispatch 之前。
    """
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")
    # 合法 kind、但缺範本引用與前提宣告 → 舊版會先開債，新版必須在開債前就擋掉
    (h["handoffs"] / "brief.md").write_text(
        "# 不完整 review brief\n\nbrief-kind: review\n\n沒有引用範本，也沒有前提宣告。\n",
        encoding="utf-8",
    )
    before = _audit_bytes(h["audit"])
    r = _run_mut_committee(h, monkeypatch)
    assert r.returncode == 2, f"不完整 brief 應被拒派；rc={r.returncode} {r.stderr}"
    assert _audit_bytes(h["audit"]) == before, "開債前被拒 ⇒ audit 必須逐位元組不變"
    assert _events(h["audit"], "committee_round_open") == [], "不得留下孤兒 OPEN 債"


def test_mutation_committee_partial_check_reopens_orphan_debt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """把 committee_run 的完整檢查換回「只驗 kind」→ 孤兒 OPEN 債重現。

    這條是上面那條迴歸測試的**可證偽性證明**：若不做這個變異就無法讓它轉紅，
    代表那條測試在測空氣。變異內容＝重現修法前的 committee_run 行為
    （自己 parse、只驗 brief-kind 存不存在，不驗範本引用／前提宣告）。
    """
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def partial_check(text: str) -> str:
        old = 'bash "${SCRIPT_DIR}/brief_conformance_check.sh" "${brief}" || exit $?'
        assert old in text, "committee_run 未呼叫 brief_conformance_check（錨點不存在）"
        # 修法前的等效行為：只驗有沒有 brief-kind 行
        t = text.replace(
            old,
            'grep -qE \'^brief-kind:\' "${brief}" || exit 2  # MUTATED: 只驗 kind',
            1,
        )
        # GOVFLOW-B3：_role_gate 會再跑完整 brief_conformance --emit，須一併跳過
        # 才能重現「只驗 kind → 孤兒 OPEN 債」的歷史病根。
        rg = (
            'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {\n'
            '  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2\n'
            "  exit 2\n"
            "}"
        )
        assert rg in t, "role gate preflight anchor missing（B3）"
        return t.replace(rg, "true  # MUTATED: skip role gate for partial-check proof", 1)

    _mutate_committee(h, partial_check)
    (h["handoffs"] / "brief.md").write_text(
        "# 不完整 review brief\n\nbrief-kind: review\n\n沒有引用範本，也沒有前提宣告。\n",
        encoding="utf-8",
    )
    _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, "變異後應重現孤兒 OPEN 債；若仍為 0 表示該測試無保護力"


def test_mutation_v4_move_after_gate_adds_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V4：刪除 gate 前 stamp-target／brief-kind 檢查 → 缺欄時 audit 非零。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def strip_pre_gate(text: str) -> str:
        start = text.find(
            "# GOV-STAMP-TASKID-INJECT / D-001 §D3：brief-kind 與 stamp-target 驗證"
        )
        end = text.find("# task_id 從透傳 gate argv 解析")
        assert start != -1 and end != -1 and start < end, "V4 committee anchor missing"
        t = text[:start] + text[end:]
        # GOVFLOW-B3：角色閘與 task_id 白名單亦在 gate 前；V4 語意＝刪光 gate 前檢查
        rg = (
            'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {\n'
            '  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2\n'
            "  exit 2\n"
            "}"
        )
        if rg in t:
            t = t.replace(rg, "true  # MUTATED V4: skip role gate", 1)
        tid = 'bash "${SCRIPT_DIR}/_role_gate.sh" check-task-id "${task_id}" || exit 2'
        if tid in t:
            t = t.replace(tid, "true  # MUTATED V4: skip task-id whitelist", 1)
        return t

    _mutate_committee(h, strip_pre_gate)
    _write_brief(h, stamp_target=None, name="brief.md")
    r = _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, f"刪除 gate 前檢查後應已開債；rc={r.returncode}"

    h2 = _harness(tmp_path / "restore4")
    _write_brief(h2, stamp_target=None, name="brief.md")
    before = _audit_bytes(h2["audit"])
    r2 = _run_mut_committee(h2, monkeypatch)
    assert r2.returncode == 2
    assert _audit_bytes(h2["audit"]) == before


def test_mutation_v5_skip_multi_target_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V5：刪除「多個不一致 stamp-target」檢查 → 不一致 brief 仍開債。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def neuter_multi(text: str) -> str:
        old = (
            '  if [ "${_st_n}" -gt 1 ]; then\n'
            '    echo "ERROR: stamp-target 有多個【不一致】宣告: $(printf \'%s\' "${_st_all}" | tr \'\\n\' \' \')" >&2\n'
            "    exit 2\n"
            "  fi\n"
        )
        assert old in text, "V5 multi-target anchor missing"
        return text.replace(old, "  # MUTATED: multi-target check removed\n", 1)

    _mutate_brief_conformance(h, neuter_multi)
    (h["handoffs"] / "a.md").write_text("a\n", encoding="utf-8")
    (h["handoffs"] / "b.md").write_text("b\n", encoding="utf-8")
    _write_brief(
        h,
        stamp_target="handoffs/a.md",
        extra_stamp_targets=["handoffs/b.md"],
        name="brief.md",
    )
    r = _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, f"V5 閹割後應開債；rc={r.returncode} {r.stderr}"

    h2 = _harness(tmp_path / "restore5")
    (h2["handoffs"] / "a.md").write_text("a\n", encoding="utf-8")
    (h2["handoffs"] / "b.md").write_text("b\n", encoding="utf-8")
    _write_brief(
        h2,
        stamp_target="handoffs/a.md",
        extra_stamp_targets=["handoffs/b.md"],
        name="brief.md",
    )
    before = _audit_bytes(h2["audit"])
    r2 = _run_mut_committee(h2, monkeypatch)
    assert r2.returncode == 2
    assert _audit_bytes(h2["audit"]) == before


def test_mutation_v6_skip_path_guard_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V6：刪除 handoffs/ 前綴檢查 → outside.md 目標仍開債。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def neuter_prefix(text: str) -> str:
        old = (
            '  case "${stamp_target}" in\n'
            "    handoffs/*) : ;;\n"
            '    *) echo "ERROR: stamp-target 須 handoffs/ 前綴: ${stamp_target}" >&2; exit 2 ;;\n'
            "  esac\n"
        )
        assert old in text, "V6 handoffs prefix anchor missing"
        return text.replace(old, "  # MUTATED: handoffs prefix check removed\n", 1)

    _mutate_brief_conformance(h, neuter_prefix)
    outside = h["root"] / "outside.md"
    outside.write_text("x\n", encoding="utf-8")
    _write_brief(h, stamp_target="outside.md", name="brief.md")
    r = _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, f"V6 閹割後應開債；rc={r.returncode} {r.stderr}"

    h2 = _harness(tmp_path / "restore6")
    (h2["root"] / "outside.md").write_text("x\n", encoding="utf-8")
    _write_brief(h2, stamp_target="outside.md", name="brief.md")
    before = _audit_bytes(h2["audit"])
    r2 = _run_mut_committee(h2, monkeypatch)
    assert r2.returncode == 2
    assert _audit_bytes(h2["audit"]) == before


def test_mutation_v7_skip_register_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V7：刪除 register-output 呼叫 → 相符戳記零註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def neuter_reg(text: str) -> str:
        old = (
            '  if ! bash "${SCRIPT_DIR}/gate.sh" register-output "${task_id}" "${stamp_target}"; then\n'
            "    # 註冊失敗（與合法 no-op 機械可分）：可辨識錯誤字串、rc 不變、不回捲 family_result\n"
            '    echo "ERROR: register-output 失敗（待人工補記）task=${task_id} path=${stamp_target}" >&2\n'
            "  fi\n"
        )
        assert old in text, "V7 register-output anchor missing"
        return text.replace(old, "  # MUTATED: register-output skipped\n", 1)

    _mutate_cx(h, neuter_reg)
    rid, _task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT7",
        plant_dispatch=True,
        rid="c1111111-1111-4111-8111-111111111111",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert _events(h["audit"], "committee_output") == []

    h2 = _harness(tmp_path / "restore7")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT7B",
        plant_dispatch=True,
        rid="c2222222-2222-4222-8222-222222222222",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    assert len(_events(h2["audit"], "committee_output")) == 1


def test_mutation_v8_ignore_fam_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V8：predicate 不錨定 fam → 他家族戳記被誤註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def ignore_fam(text: str) -> str:
        old = _PREDICATE_GREP_LINE
        new = (
            'if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+[A-Za-z0-9_-]+[[:space:]]+APPROVED'
            "[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+"
            "(sha256:${hash_e}[[:space:]]+task:${task_e}|task:${task_e}[[:space:]]+sha256:${hash_e})"
            '([[:space:]]|$)" "${stamp_target}"; then'
        )
        assert old in text, "V8 predicate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, ignore_fam)
    task_id = "P16-D001-MUT8"
    target = h["handoffs"] / "target.md"
    body = "v8mut body\n"
    target.write_text(body + "\n## 戳記\n\n", encoding="utf-8")
    bh = _body_hash(target)
    _write_stamp_target(
        target, stamps=[_stamp_line("composer", task_id, bh)], body=body
    )
    _write_brief(h, stamp_target="handoffs/target.md")
    rid = "c3333333-3333-4333-8333-333333333333"
    _open_round(
        h,
        round_id=rid,
        session="s-mut8",
        fams=["codex"],
        out_prefix="handoffs/reg",
        brief_rel="handoffs/brief.md",
        task_id=task_id,
    )
    _plant_dispatch(h, task_id)
    r = _run_mut_cx(
        h,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/reg-codex.md",
        rid=rid,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) >= 1

    h2 = _harness(tmp_path / "restore8")
    target2 = h2["handoffs"] / "target.md"
    target2.write_text(body + "\n## 戳記\n\n", encoding="utf-8")
    bh2 = _body_hash(target2)
    _write_stamp_target(
        target2, stamps=[_stamp_line("composer", task_id, bh2)], body=body
    )
    _write_brief(h2, stamp_target="handoffs/target.md")
    rid2 = "c4444444-4444-4444-8444-444444444444"
    _open_round(
        h2,
        round_id=rid2,
        session="s-mut8b",
        fams=["codex"],
        out_prefix="handoffs/reg",
        brief_rel="handoffs/brief.md",
        task_id=task_id,
    )
    _plant_dispatch(h2, task_id)
    r2 = _run_mut_cx(
        h2,
        monkeypatch,
        brief_rel="handoffs/brief.md",
        out_rel="handoffs/reg-codex.md",
        rid=rid2,
    )
    assert r2.returncode == 0
    assert _events(h2["audit"], "committee_output") == []


def test_mutation_v9_skip_task_anchor_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V9：predicate 不錨定 task: → 錯 task 戳記被誤註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def drop_task(text: str) -> str:
        old = _PREDICATE_GREP_LINE
        new = (
            'if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+${fam_e}[[:space:]]+APPROVED'
            "[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+.*"
            'sha256:${hash_e}" "${stamp_target}"; then'
        )
        assert old in text, "V9 predicate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, drop_task)
    rid, _task_id, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT9",
        stamp_task="OTHER-TASK-ID",
        plant_dispatch=True,
        rid="c5555555-5555-4555-8555-555555555555",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) >= 1

    h2 = _harness(tmp_path / "restore9")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT9B",
        stamp_task="OTHER-TASK-ID",
        plant_dispatch=True,
        rid="c6666666-6666-4666-8666-666666666666",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    assert _events(h2["audit"], "committee_output") == []


def test_mutation_v10_accept_rejected_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V10：predicate 接受 REJECTED → 應 no-op 的戳記被註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def accept_rejected(text: str) -> str:
        old = _PREDICATE_GREP_LINE
        new = (
            'if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+${fam_e}[[:space:]]+(APPROVED|REJECTED)'
            "[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+"
            "(sha256:${hash_e}[[:space:]]+task:${task_e}|task:${task_e}[[:space:]]+sha256:${hash_e})"
            '([[:space:]]|$)" "${stamp_target}"; then'
        )
        assert old in text, "V10 predicate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, accept_rejected)
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT10",
        stamp_verdict="REJECTED",
        plant_dispatch=True,
        rid="c7777777-7777-4777-8777-777777777777",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) >= 1

    h2 = _harness(tmp_path / "restore10")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT10B",
        stamp_verdict="REJECTED",
        plant_dispatch=True,
        rid="c8888888-8888-4888-8888-888888888888",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    assert _events(h2["audit"], "committee_output") == []


def test_mutation_v11_register_on_cli_fail_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V11：移除 cli_rc 短路 → CLI fail 且 out 非空時仍註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def invert_rc_gate(text: str) -> str:
        old = (
            "  # 條件①：result_state=success（cli_rc=0 且產出非空）\n"
            '  if [ "${cli_rc}" -ne 0 ] 2>/dev/null || [ ! -s "${out}" ]; then\n'
            "    return 0\n"
            "  fi\n"
        )
        new = (
            "  # MUTATED: cli_rc gate removed; keep non-empty out check only\n"
            '  if [ ! -s "${out}" ]; then\n'
            "    return 0\n"
            "  fi\n"
        )
        assert old in text, "V11 success-gate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, invert_rc_gate)
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT11",
        plant_dispatch=True,
        rid="d1111111-1111-4111-8111-111111111111",
    )
    out_rel = "handoffs/reg-codex.md"
    (h["root"] / "handoffs").mkdir(parents=True, exist_ok=True)
    (h["root"] / out_rel).write_text("non-empty for mut11\n", encoding="utf-8")
    r = _run_mut_cx(
        h,
        monkeypatch,
        brief_rel=brief_rel,
        out_rel=out_rel,
        rid=rid,
        stub="fail_rc",
    )
    assert r.returncode != 0
    results = _events(h["audit"], "committee_family_result")
    assert results and results[-1].get("result_state") == "failed"
    assert len(_events(h["audit"], "committee_output")) >= 1, (
        "拆 cli_rc 門後 fail 路徑仍應 register（out 非空）"
    )

    h2 = _harness(tmp_path / "restore11")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT11B",
        plant_dispatch=True,
        rid="d2222222-2222-4222-8222-222222222222",
    )
    r2 = _run_mut_cx(
        h2,
        monkeypatch,
        brief_rel=brief2,
        out_rel="handoffs/reg-codex.md",
        rid=rid2,
        stub="fail_rc",
    )
    assert r2.returncode != 0
    assert _events(h2["audit"], "committee_output") == []


def test_mutation_v12_force_stamp_target_all_kinds_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V12：非 stamp kind 也強制 stamp-target → impl 無 target 被誤擋。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def force_all(text: str) -> str:
        old = 'if [ "${_bk}" = "stamp" ]; then'
        assert old in text, "V12 stamp-kind gate anchor missing"
        return text.replace(
            old, 'if true; then  # MUTATED: all kinds need stamp-target', 1
        )

    # GOV-DOC-CHECK-AT-WRITE（2026-08-02）：此判定已從 cx_run.sh 抽到
    # brief_conformance_check.sh，探針隨之改指新位置。**變異語意未變**——
    # 仍是「非 stamp kind 也強制 stamp-target」，仍預期 impl brief 被誤擋。
    _mutate_brief_conformance(h, force_all)
    # 票 B-49：沙箱名冊釘成有 CLI 配方之家族；否則 implementer=claude 會讓本測
    # **因家族白名單被拒**而綠，而非因 V12 變異被誤擋 —— 那是假綠。
    fam = _role_pin.pin_implementer(h["scripts"])
    _write_brief(h, kind="impl", stamp_target=None, name="brief.md")
    rid = "d3333333-3333-4333-8333-333333333333"
    _open_round(
        h,
        round_id=rid,
        session="s-mut12",
        fams=[fam],
        out_prefix="handoffs/v12impl",
        brief_rel="handoffs/brief.md",
        task_id="P16-D001-MUT12",
    )
    r = _run_mut_cx(
        h,
        monkeypatch,
        fam=fam,
        brief_rel="handoffs/brief.md",
        out_rel=f"handoffs/v12impl-{fam}.md",
        rid=rid,
    )
    assert r.returncode == 2, "V12 閹割後無 stamp-target 的 impl 應被誤擋"

    h2 = _harness(tmp_path / "restore12")
    fam2 = _role_pin.pin_implementer(h2["scripts"])
    _write_brief(h2, kind="impl", stamp_target=None, name="brief.md")
    rid2 = "d4444444-4444-4444-8444-444444444444"
    _open_round(
        h2,
        round_id=rid2,
        session="s-mut12b",
        fams=[fam2],
        out_prefix="handoffs/v12impl",
        brief_rel="handoffs/brief.md",
        task_id="P16-D001-MUT12B",
    )
    r2 = _run_mut_cx(
        h2,
        monkeypatch,
        fam=fam2,
        brief_rel="handoffs/brief.md",
        out_rel=f"handoffs/v12impl-{fam2}.md",
        rid=rid2,
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_mutation_v13_silent_register_fail_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V13：register-output 失敗不印可辨識字串 → 與合法 no-op 不可分。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def silence_err(text: str) -> str:
        old = (
            '    echo "ERROR: register-output 失敗（待人工補記）task=${task_id} path=${stamp_target}" >&2\n'
        )
        assert old in text, "V13 error-string anchor missing"
        return text.replace(old, "    : # MUTATED: silent register failure\n", 1)

    _mutate_cx(h, silence_err)
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT13",
        plant_dispatch=False,
        rid="d5555555-5555-4555-8555-555555555555",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert "register-output 失敗" not in combined
    assert "待人工補記" not in combined
    results = _events(h["audit"], "committee_family_result")
    assert results and results[-1].get("result_state") == "success"

    h2 = _harness(tmp_path / "restore13")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT13B",
        plant_dispatch=False,
        rid="d6666666-6666-4666-8666-666666666666",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    c2 = r2.stdout + r2.stderr
    assert "register-output 失敗" in c2 or "待人工補記" in c2


def test_mutation_v14_dual_grep_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V14：predicate 改兩次獨立 grep 取交集 → cross_line 誤註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def dual_grep(text: str) -> str:
        old = f"{_PREDICATE_GREP_LINE}\n    return 0\n  fi"
        new = (
            'if ! grep -qE "RECONCILE-STAMP:[[:space:]]+${fam}[[:space:]]+APPROVED" "${stamp_target}"; then\n'
            "    return 0\n"
            "  fi\n"
            '  if ! grep -qE "task:${task_id}" "${stamp_target}"; then\n'
            "    return 0\n"
            "  fi"
        )
        assert old in text, "V14 predicate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, dual_grep)
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT14",
        cross_line=True,
        plant_dispatch=True,
        rid="b1111111-1111-4111-8111-111111111111",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) >= 1

    h2 = _harness(tmp_path / "restore14")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT14B",
        cross_line=True,
        plant_dispatch=True,
        rid="b2222222-2222-4222-8222-222222222222",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    assert _events(h2["audit"], "committee_output") == []


def test_mutation_v15_skip_sha_anchor_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V15：predicate 不錨定 sha256 → 錯 hash 被誤註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def drop_sha(text: str) -> str:
        old = _PREDICATE_GREP_LINE
        new = (
            'if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+${fam_e}[[:space:]]+APPROVED'
            "[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+.*"
            'task:${task_e}([[:space:]]|$)" "${stamp_target}"; then'
        )
        assert old in text, "V15 predicate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, drop_sha)
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT15",
        wrong_hash=True,
        plant_dispatch=True,
        rid="e1111111-1111-4111-8111-111111111111",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) >= 1

    h2 = _harness(tmp_path / "restore15")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT15B",
        wrong_hash=True,
        plant_dispatch=True,
        rid="e2222222-2222-4222-8222-222222222222",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    assert _events(h2["audit"], "committee_output") == []


def test_mutation_v16_unescaped_task_id_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V16：task_id 不跳脫即內插 → `.` 誤配並註冊。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def no_escape_task(text: str) -> str:
        old = _PREDICATE_GREP_LINE
        new = (
            'if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+${fam_e}[[:space:]]+APPROVED'
            "[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+"
            "(sha256:${hash_e}[[:space:]]+task:${task_id}|task:${task_id}[[:space:]]+sha256:${hash_e})"
            '([[:space:]]|$)" "${stamp_target}"; then'
        )
        assert old in text, "V16 predicate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, no_escape_task)
    task_id = "P16.D001-TASK"
    wrong = "P16XD001-TASK"
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id=task_id,
        stamp_task=wrong,
        plant_dispatch=True,
        rid="e3333333-3333-4333-8333-333333333333",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_events(h["audit"], "committee_output")) >= 1

    h2 = _harness(tmp_path / "restore16")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id=task_id,
        stamp_task=wrong,
        plant_dispatch=True,
        rid="e4444444-4444-4444-8444-444444444444",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    assert _events(h2["audit"], "committee_output") == []


def test_mutation_v17_order_sensitive_only_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V17：predicate 僅 sha-then-task → 反序戳記靜默 no-op。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h["scripts"] / "cx_run.sh")

    def order_sensitive(text: str) -> str:
        old = _PREDICATE_GREP_LINE
        new = (
            'if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+${fam_e}[[:space:]]+APPROVED'
            "[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+"
            "sha256:${hash_e}[[:space:]]+task:${task_e}"
            '([[:space:]]|$)" "${stamp_target}"; then'
        )
        assert old in text, "V17 predicate anchor missing"
        return text.replace(old, new, 1)

    _mutate_cx(h, order_sensitive)
    rid, _, brief_rel = _setup_stamp_success(
        h,
        fam="codex",
        task_id="P16-D001-MUT17",
        plant_dispatch=True,
        field_order="task_then_sha",
        rid="e5555555-5555-4555-8555-555555555555",
    )
    r = _run_mut_cx(
        h, monkeypatch, brief_rel=brief_rel, out_rel="handoffs/reg-codex.md", rid=rid
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert _events(h["audit"], "committee_output") == []

    h2 = _harness(tmp_path / "restore17")
    rid2, _, brief2 = _setup_stamp_success(
        h2,
        fam="codex",
        task_id="P16-D001-MUT17B",
        plant_dispatch=True,
        field_order="task_then_sha",
        rid="e6666666-6666-4666-8666-666666666666",
    )
    r2 = _run_mut_cx(
        h2, monkeypatch, brief_rel=brief2, out_rel="handoffs/reg-codex.md", rid=rid2
    )
    assert r2.returncode == 0
    assert len(_events(h2["audit"], "committee_output")) == 1


def test_mutation_v18_skip_missing_kind_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V18：刪除缺 brief-kind 與 unknown case → 畸形 brief 先開債。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def drop_kind_guards(text: str) -> str:
        old1 = (
            '[ -n "${_bk}" ] || {\n'
            "  echo \"ERROR: brief 缺 'brief-kind:' 宣告。請於 brief 加一行,值 ∈ review|consult|closure|impl|stamp\"\n"
            '  echo "  (收集 findings 類=review/consult/closure,會另檢範本引用+前提宣告)"\n'
            "  exit 2\n"
            "}\n"
        )
        old2 = _CR_BK_UNKNOWN_CASE
        assert old1 in text, "V18 missing brief-kind anchor missing"
        assert old2 in text, "V18 unknown-kind anchor missing"
        t = text.replace(old1, "  # MUTATED missing kind\n", 1)
        t = t.replace(old2, "  # MUTATED kind case\n", 1)
        return t

    _mutate_brief_conformance(h, drop_kind_guards)

    def skip_role_gate_for_v18(text: str) -> str:
        # B3：role gate 對空 kind fail-closed；本 MUT 只證 brief_conformance 缺欄守衛
        rg = (
            'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {\n'
            '  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2\n'
            "  exit 2\n"
            "}"
        )
        assert rg in text, "V18 role gate anchor missing"
        return text.replace(rg, "true  # MUTATED V18: skip role gate", 1)

    _mutate_committee(h, skip_role_gate_for_v18)
    (h["handoffs"] / "brief.md").write_text(
        "stamp-target: handoffs/target.md\n\nstub missing kind\n",
        encoding="utf-8",
    )
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    r = _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, f"V18 閹割後應開債；rc={r.returncode} {r.stderr}"

    h2 = _harness(tmp_path / "restore18")
    (h2["handoffs"] / "brief.md").write_text(
        "stamp-target: handoffs/target.md\n\nstub missing kind\n",
        encoding="utf-8",
    )
    (h2["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    before = _audit_bytes(h2["audit"])
    r2 = _run_mut_committee(h2, monkeypatch)
    assert r2.returncode == 2
    assert _audit_bytes(h2["audit"]) == before


# 完整擷取（修後）vs 前綴擷取（病根）錨點 — V19 mutation 用
# ⚠️ 錨點已從 committee_run.sh 移到 brief_conformance_check.sh（CODEX-R1-P1-01，2026-08-02）。
#   committee_run.sh 原本有**第二份** brief-kind／stamp-target parser，與 cx_run 那份各驗一半：
#   它只驗「kind 存不存在／值合不合法」，範本引用與前提宣告只有 cx_run 驗，而 cx_run 在**開債之後**跑
#   ⇒ 不完整 brief 會先留下 OPEN debt（本 repo audit sequence 367 即此例）。
#   修法＝committee_run 改呼叫同一個 checker，仍在 gate dispatch 之前。
#   **這些探針的變異語意完全不變**，只是守衛的實體位置換了檔，故改用 _mutate_brief_conformance。
#   常數名保留 `_CR_` 前綴以免大量無謂改名；其值已指向新檔內容。
_CR_BK_FULL_EXTRACT = (
    '_bk_all="$(grep -E \'^brief-kind:\' "${brief}" 2>/dev/null '
    "| sed 's/^brief-kind:[[:space:]]*//;s/[[:space:]]*$//' | sort -u)\""
)
_CR_BK_PREFIX_EXTRACT = (
    '_bk_all="$(grep -oE \'^brief-kind:[[:space:]]*[a-z]+\' "${brief}" 2>/dev/null '
    "| sed 's/.*:[[:space:]]*//' | sort -u)\""
)
_CR_BK_UNKNOWN_CASE = (
    '  *) echo "ERROR: 未知 brief-kind: ${_bk}'
    '(允許 review|consult|closure|impl|stamp)"; exit 2 ;;\n'
)


def test_mutation_v19_prefix_extract_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V19：把整值擷取改回 [a-z]+ 前綴擷取 → stamp-evil 被截成 stamp 並開債。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def reintroduce_prefix(text: str) -> str:
        assert _CR_BK_FULL_EXTRACT in text, "V19 full-extract anchor missing"
        return text.replace(_CR_BK_FULL_EXTRACT, _CR_BK_PREFIX_EXTRACT, 1)

    _mutate_brief_conformance(h, reintroduce_prefix)
    (h["handoffs"] / "brief.md").write_text(
        "brief-kind: stamp-evil\nstamp-target: handoffs/target.md\n\nstub\n",
        encoding="utf-8",
    )
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    r = _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, (
        f"V19 前綴擷取閹割後 stamp-evil 應開債；rc={r.returncode} {r.stderr}"
    )

    h2 = _harness(tmp_path / "restore19")
    (h2["handoffs"] / "brief.md").write_text(
        "brief-kind: stamp-evil\nstamp-target: handoffs/target.md\n\nstub\n",
        encoding="utf-8",
    )
    (h2["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    before = _audit_bytes(h2["audit"])
    r2 = _run_mut_committee(h2, monkeypatch)
    assert r2.returncode == 2, r2.stdout + r2.stderr
    assert _audit_bytes(h2["audit"]) == before
    assert _debt_has_open(h2) == 0


def test_mutation_v20_drop_unknown_case_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V20：刪除 unknown case → evilstamp 開債。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def drop_unknown(text: str) -> str:
        assert _CR_BK_UNKNOWN_CASE in text, "V20 unknown-case anchor missing"
        return text.replace(_CR_BK_UNKNOWN_CASE, "  # MUTATED unknown case\n", 1)

    _mutate_brief_conformance(h, drop_unknown)

    def skip_role_gate_for_v20(text: str) -> str:
        # B3：未知 kind 亦被 role gate fail-closed；本 MUT 只證 brief_conformance unknown case
        rg = (
            'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {\n'
            '  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2\n'
            "  exit 2\n"
            "}"
        )
        assert rg in text, "V20 role gate anchor missing"
        return text.replace(rg, "true  # MUTATED V20: skip role gate", 1)

    _mutate_committee(h, skip_role_gate_for_v20)
    (h["handoffs"] / "brief.md").write_text(
        "brief-kind: evilstamp\nstamp-target: handoffs/target.md\n\nstub\n",
        encoding="utf-8",
    )
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    r = _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, (
        f"V20 閹割後 evilstamp 應開債；rc={r.returncode} {r.stderr}"
    )

    h2 = _harness(tmp_path / "restore20")
    (h2["handoffs"] / "brief.md").write_text(
        "brief-kind: evilstamp\nstamp-target: handoffs/target.md\n\nstub\n",
        encoding="utf-8",
    )
    (h2["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    before = _audit_bytes(h2["audit"])
    r2 = _run_mut_committee(h2, monkeypatch)
    assert r2.returncode == 2, r2.stdout + r2.stderr
    assert _audit_bytes(h2["audit"]) == before
    assert _debt_has_open(h2) == 0


def test_mutation_v21_drop_unknown_case_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT V21：刪除 unknown case → bogus 開債。"""
    h = _harness(tmp_path)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    def drop_unknown(text: str) -> str:
        assert _CR_BK_UNKNOWN_CASE in text, "V21 unknown-case anchor missing"
        return text.replace(_CR_BK_UNKNOWN_CASE, "  # MUTATED unknown case\n", 1)

    _mutate_brief_conformance(h, drop_unknown)

    def skip_role_gate_for_v21(text: str) -> str:
        rg = (
            'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {\n'
            '  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2\n'
            "  exit 2\n"
            "}"
        )
        assert rg in text, "V21 role gate anchor missing"
        return text.replace(rg, "true  # MUTATED V21: skip role gate", 1)

    _mutate_committee(h, skip_role_gate_for_v21)
    (h["handoffs"] / "brief.md").write_text(
        "brief-kind: bogus\nstamp-target: handoffs/target.md\n\nstub\n",
        encoding="utf-8",
    )
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    r = _run_mut_committee(h, monkeypatch)
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) >= 1, (
        f"V21 閹割後 bogus 應開債；rc={r.returncode} {r.stderr}"
    )

    h2 = _harness(tmp_path / "restore21")
    (h2["handoffs"] / "brief.md").write_text(
        "brief-kind: bogus\nstamp-target: handoffs/target.md\n\nstub\n",
        encoding="utf-8",
    )
    (h2["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    before = _audit_bytes(h2["audit"])
    r2 = _run_mut_committee(h2, monkeypatch)
    assert r2.returncode == 2, r2.stdout + r2.stderr
    assert _audit_bytes(h2["audit"]) == before
    assert _debt_has_open(h2) == 0


# ── 群 H mutation：前綴擷取閹割 → 矩陣敏感列轉紅；復原綠 ────────


def _group_h_prefix_mutant_transform(text: str) -> str:
    """把 committee_run 整值擷取改回 [a-z]+ 前綴擷取（CR2 群 E 病根）。"""
    assert _CR_BK_FULL_EXTRACT in text, "群 H full-extract anchor missing"
    return text.replace(_CR_BK_FULL_EXTRACT, _CR_BK_PREFIX_EXTRACT, 1)


def _group_h_mut_reject_case(
    h: dict,
    monkeypatch: pytest.MonkeyPatch,
    kind_line: str,
    *,
    session: str,
) -> subprocess.CompletedProcess[str]:
    (h["handoffs"] / "brief.md").write_text(
        f"{kind_line}\nstamp-target: handoffs/target.md\n\nstub group-H mut\n",
        encoding="utf-8",
    )
    (h["handoffs"] / "target.md").write_text("t\n", encoding="utf-8")
    return _run_mut_committee(
        h, monkeypatch, brief_rel="handoffs/brief.md", session=session
    )


def test_mutation_group_h_prefix_extract_matrix_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT 群 H：整值→前綴擷取後，矩陣中 stamp-evil／stampx 類前綴敏感列 fail-open。

    前綴擷取 ``grep -oE '^brief-kind:[[:space:]]*[a-z]+'`` 會把：
    - ``stamp-evil`` 截成 ``stamp`` → 誤開債（必轉紅）
    - ``stampx`` 全為 [a-z] 不被截斷，仍整值 ``stampx`` → 白名單仍拒
      （此列靠永久矩陣＋ drop-unknown 類探針保護；前綴擷取 alone 不開洞）
    - ``evilstamp`` 同理整值仍為 evilstamp → 白名單仍拒

    契約：至少 stamp-evil 必須轉紅（開債）；復原後 stamp-evil／stampx／evilstamp 全綠拒。
    """
    # ── 閹割 ──
    h = _harness(tmp_path / "mut-h")
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")
    _mutate_brief_conformance(h, _group_h_prefix_mutant_transform)

    # stamp-evil → 必須 fail-open（截成 stamp 並開債）
    r_evil = _group_h_mut_reject_case(
        h, monkeypatch, "brief-kind: stamp-evil", session="mut-h-evil"
    )
    opens_evil = _events(h["audit"], "committee_round_open")
    assert len(opens_evil) >= 1, (
        f"群H 前綴擷取後 stamp-evil 應開債轉紅；rc={r_evil.returncode} "
        f"{r_evil.stderr}"
    )

    # stampx：前綴擷取不截斷 → 仍拒（記錄行為，非本 mutant 的 fail-open 面）
    h_sx = _harness(tmp_path / "mut-h-stampx")
    monkeypatch.setattr(
        _dph, "COMMITTEE_RUN_TARGET", h_sx["scripts"] / "committee_run.sh"
    )
    _mutate_brief_conformance(h_sx, _group_h_prefix_mutant_transform)
    before_sx = _audit_bytes(h_sx["audit"])
    r_sx = _group_h_mut_reject_case(
        h_sx, monkeypatch, "brief-kind: stampx", session="mut-h-sx"
    )
    # 若未來前綴邏輯改成可截 stampx，此列會開債 → 改斷言為轉紅即可
    assert r_sx.returncode == 2, (
        f"群H 前綴擷取下 stampx 現況應仍拒（全 [a-z] 不被截）；"
        f"rc={r_sx.returncode} {r_sx.stderr}"
    )
    assert _audit_bytes(h_sx["audit"]) == before_sx

    # evilstamp：同 stampx，前綴擷取 alone 不開洞
    h_es = _harness(tmp_path / "mut-h-evilstamp")
    monkeypatch.setattr(
        _dph, "COMMITTEE_RUN_TARGET", h_es["scripts"] / "committee_run.sh"
    )
    _mutate_brief_conformance(h_es, _group_h_prefix_mutant_transform)
    before_es = _audit_bytes(h_es["audit"])
    r_es = _group_h_mut_reject_case(
        h_es, monkeypatch, "brief-kind: evilstamp", session="mut-h-es"
    )
    assert r_es.returncode == 2, (
        f"群H 前綴擷取下 evilstamp 現況應仍拒；rc={r_es.returncode} {r_es.stderr}"
    )
    assert _audit_bytes(h_es["audit"]) == before_es

    # ── 復原 → 綠：stamp-evil／stampx／evilstamp 皆拒、零 audit ──
    for label, kind_line in (
        ("stamp-evil", "brief-kind: stamp-evil"),
        ("stampx", "brief-kind: stampx"),
        ("evilstamp", "brief-kind: evilstamp"),
    ):
        h2 = _harness(tmp_path / f"restore-h-{label}")
        monkeypatch.setattr(
            _dph, "COMMITTEE_RUN_TARGET", h2["scripts"] / "committee_run.sh"
        )
        # 不 mutate = 復原
        before = _audit_bytes(h2["audit"])
        r2 = _group_h_mut_reject_case(
            h2, monkeypatch, kind_line, session=f"restore-h-{label}"
        )
        assert r2.returncode == 2, (
            f"群H 復原後 {label} 應拒；rc={r2.returncode} {r2.stderr}"
        )
        assert _audit_bytes(h2["audit"]) == before
        assert _debt_has_open(h2) == 0
