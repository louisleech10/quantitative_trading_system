"""GOVB0 Task 1.1 — cx_run.sh prompt 依 brief-kind 分支（B-32）。

TEST-1.1-* 對應 docs/GOVB0_FRICTION_TODO.md Phase 1 / Task 1.1。
誠實邊界：只保證 harness 端不再誘導；不得以「委員這次沒寫」為斷言。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import tests.governance._debt_probe_helper as _dph

REPO_ROOT = Path(__file__).resolve().parents[2]
CX_RUN = REPO_ROOT / "scripts" / "cx_run.sh"

# 與 cx_run.sh RECONCILE-STAMP 正則同源的樣式（fam/hash/task 以字面代入後比對）
_STAMP_RE_TEMPLATE = (
    r"^RECONCILE-STAMP:[[:space:]]+{fam}[[:space:]]+APPROVED[[:space:]]+"
    r"[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}[[:space:]]+"
    r"(sha256:{hash}[[:space:]]+task:{task}|task:{task}[[:space:]]+sha256:{hash})"
    r"([[:space:]]|$)"
)

_SCRIPT_NAMES = (
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
    "brief_conformance_check.sh",
    "completeness_check.sh",
    "_role_gate.sh",
)


def _harness(tmp_path: Path) -> dict:
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


def _write_brief(
    h: dict,
    *,
    kind: str,
    name: str = "brief.md",
    stamp_target: str | None = None,
) -> Path:
    lines = [f"brief-kind: {kind}", ""]
    if kind == "stamp":
        st = stamp_target or "handoffs/target.md"
        lines.append(f"stamp-target: {st}")
        lines.append("")
    if kind in ("review", "consult", "closure"):
        lines.append("templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做")
        lines.append("fact-verified: unit-test → harness")
        lines.append("assumed: isolated env")
        lines.append("")
    lines.append(f"stub brief kind={kind}\n")
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
    task_id: str,
) -> None:
    brief_path = h["root"] / brief_rel
    brief_sha = hashlib.sha256(brief_path.read_bytes()).hexdigest()
    outputs = {f: f"{out_prefix}-{f}.md" for f in fams}
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


def _run_cx(
    h: dict,
    fam: str,
    brief_rel: str,
    out_rel: str,
    *,
    round_id: str,
    env_overlay: dict[str, str] | None = None,
    stub: str = "success",
) -> subprocess.CompletedProcess[str]:
    env = dict(h["env"])
    env["ROUND_ID"] = round_id
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


def _debt_has_open_rc(h: dict) -> int:
    r = _dph.run_cmd(
        h["scripts"] / "debt_ledger.sh",
        "--has-open",
        env=h["env"],
        cwd=h["root"],
    )
    return r.returncode


def _handoffs_snapshot(h: dict) -> set[str]:
    return {p.name for p in h["handoffs"].iterdir() if p.is_file()}


def _gate_token_mtimes(h: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    if not h["gate_dir"].is_dir():
        return out
    for p in h["gate_dir"].iterdir():
        if p.name.endswith(".token"):
            out[p.name] = p.stat().st_mtime
    return out


def _audit_line_count(h: dict) -> int:
    if not h["audit"].is_file():
        return 0
    return sum(1 for ln in h["audit"].read_text(encoding="utf-8").splitlines() if ln.strip())


def _extract_stamp_regex_from_cx(cx_text: str) -> str:
    """從 cx_run.sh 抽出 RECONCILE-STAMP 正則（SSOT）。"""
    m = re.search(
        r'grep -qE "(\^RECONCILE-STAMP:[^"]+)"',
        cx_text,
    )
    assert m, "cx_run.sh RECONCILE-STAMP 正則錨點漂移"
    return m.group(1)


# ---------------------------------------------------------------------------
# TEST-1.1-CONSULT / STAMP / UNKNOWN / NOSIDEEFFECT / FORMAT-SSOT
# ---------------------------------------------------------------------------


def test_11_consult_prompt_no_reconcile_stamp(tmp_path: Path) -> None:
    """TEST-1.1-CONSULT：brief_kind=consult → rc=0 且 prompt 中 RECONCILE-STAMP 出現 0 次。"""
    h = _harness(tmp_path)
    task_id = "GOVB0-T11-CONSULT"
    brief_rel = "handoffs/brief.md"
    _write_brief(h, kind="consult")
    rid = "c1111111-1111-4111-8111-111111111111"
    _open_round(
        h,
        round_id=rid,
        session="s-t11-consult",
        fams=["codex"],
        out_prefix="handoffs/t11c",
        brief_rel=brief_rel,
        task_id=task_id,
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/t11c-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    prompt = capture.read_text(encoding="utf-8")
    assert prompt.count("RECONCILE-STAMP") == 0, f"consult prompt 不得含 RECONCILE-STAMP:\n{prompt}"
    assert f"你的 task-id={task_id}" in prompt


def test_11_stamp_prompt_has_stamp_and_format(tmp_path: Path) -> None:
    """TEST-1.1-STAMP：brief_kind=stamp → rc=0 且 prompt 含 RECONCILE-STAMP 與格式說明。"""
    h = _harness(tmp_path)
    task_id = "GOVB0-T11-STAMP"
    (h["handoffs"] / "target.md").write_text("body\n\n## 戳記\n\n", encoding="utf-8")
    brief_rel = "handoffs/brief.md"
    _write_brief(h, kind="stamp", stamp_target="handoffs/target.md")
    rid = "c2222222-2222-4222-8222-222222222222"
    _open_round(
        h,
        round_id=rid,
        session="s-t11-stamp",
        fams=["codex"],
        out_prefix="handoffs/t11s",
        brief_rel=brief_rel,
        task_id=task_id,
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/t11s-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    prompt = capture.read_text(encoding="utf-8")
    assert "RECONCILE-STAMP" in prompt
    assert "RECONCILE-STAMP 的 task:" in prompt
    assert "非 ## 標題" in prompt or "非 ##" in prompt
    assert "sha256:" in prompt and "task:" in prompt
    assert f"你的 task-id={task_id}" in prompt


def test_11_unknown_rc_nonzero(tmp_path: Path) -> None:
    """TEST-1.1-UNKNOWN：brief_kind=unknown → rc!=0。"""
    h = _harness(tmp_path)
    brief = h["handoffs"] / "brief.md"
    brief.write_text("brief-kind: bogus\n\nstub unknown\n", encoding="utf-8")
    r = _run_cx(
        h,
        "codex",
        "handoffs/brief.md",
        "handoffs/out-codex.md",
        round_id="c3333333-3333-4333-8333-333333333333",
    )
    assert r.returncode != 0, r.stdout + r.stderr


def test_11_unknown_nosideeffect(tmp_path: Path) -> None:
    """TEST-1.1-UNKNOWN-NOSIDEEFFECT：拒派後四項無副作用。"""
    h = _harness(tmp_path)
    brief = h["handoffs"] / "brief.md"
    brief.write_text("brief-kind: bogus\n\nstub unknown\n", encoding="utf-8")

    before_tokens = _gate_token_mtimes(h)
    before_audit_n = _audit_line_count(h)
    before_debt_rc = _debt_has_open_rc(h)
    before_handoffs = _handoffs_snapshot(h)

    r = _run_cx(
        h,
        "codex",
        "handoffs/brief.md",
        "handoffs/out-codex.md",
        round_id="c4444444-4444-4444-8444-444444444444",
    )
    assert r.returncode != 0, r.stdout + r.stderr

    after_tokens = _gate_token_mtimes(h)
    # ① 無新 token 且既有 mtime 未更新
    assert after_tokens.keys() <= before_tokens.keys() or after_tokens == before_tokens
    for name, mt in after_tokens.items():
        assert name in before_tokens, f"新 token 檔: {name}"
        assert mt == before_tokens[name], f"token mtime 被更新: {name}"
    assert set(after_tokens) == set(before_tokens), "token 集合改變"

    # ② audit.log 行數前後相等
    assert _audit_line_count(h) == before_audit_n

    # ③ debt_ledger --has-open rc 與呼叫前相同
    assert _debt_has_open_rc(h) == before_debt_rc

    # ④ handoffs/ 未產生任何新檔
    assert _handoffs_snapshot(h) == before_handoffs


def test_11_unknown_cx_case_defense(tmp_path: Path) -> None:
    """defense-in-depth：brief_conformance 放行後，cx_run case * 仍拒 unknown。

    * 分支在 _prepare_and_run 內、前置條件之後，故須先開債。
    """
    h = _harness(tmp_path)
    # 放寬 brief_conformance 白名單，讓 bogus 通過
    bc = h["scripts"] / "brief_conformance_check.sh"
    text = bc.read_text(encoding="utf-8")
    m = re.search(
        r'  \*\) echo "ERROR: 未知 brief-kind:[^"]+"; exit 2 ;;',
        text,
    )
    assert m, "brief_conformance unknown case 錨點漂移"
    bc.write_text(
        text[: m.start()] + "  bogus) : ;;  # TEST harness allow\n" + text[m.start() :],
        encoding="utf-8",
    )

    # 需過 role gate：unknown kind 在 _role_gate 亦 fail-closed → 一併放寬
    rg = h["scripts"] / "_role_gate.sh"
    rg_text = rg.read_text(encoding="utf-8")
    rg_m = re.search(
        r"consult\|closure\|stamp\)\n\s+: # 不限制 implementer\n\s+;;\n",
        rg_text,
    )
    assert rg_m, "role_gate kind case 錨點漂移"
    insert = rg_m.group(0) + "    bogus) : ;;  # TEST harness allow\n"
    rg.write_text(rg_text[: rg_m.start()] + insert + rg_text[rg_m.end() :], encoding="utf-8")

    brief = h["handoffs"] / "brief.md"
    brief.write_text("brief-kind: bogus\n\nstub\n", encoding="utf-8")
    rid = "c5555555-5555-4555-8555-555555555555"
    _open_round(
        h,
        round_id=rid,
        session="s-t11-def",
        fams=["codex"],
        out_prefix="handoffs/t11d",
        brief_rel="handoffs/brief.md",
        task_id="GOVB0-T11-DEF",
    )
    r = _run_cx(
        h,
        "codex",
        "handoffs/brief.md",
        "handoffs/t11d-codex.md",
        round_id=rid,
    )
    assert r.returncode != 0, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert "unknown brief-kind" in out or "bogus" in out, out


def test_11_format_ssot(tmp_path: Path) -> None:
    """TEST-1.1-FORMAT-SSOT：合法戳記樣本同時通過 prompt 格式說明與 cx_run.sh 正則。"""
    h = _harness(tmp_path)
    task_id = "GOVB0-T11-FORMAT"
    body_hash = "a" * 64
    (h["handoffs"] / "target.md").write_text("body\n\n## 戳記\n\n", encoding="utf-8")
    brief_rel = "handoffs/brief.md"
    _write_brief(h, kind="stamp", stamp_target="handoffs/target.md")
    rid = "c6666666-6666-4666-8666-666666666666"
    _open_round(
        h,
        round_id=rid,
        session="s-t11-fmt",
        fams=["codex"],
        out_prefix="handoffs/t11f",
        brief_rel=brief_rel,
        task_id=task_id,
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/t11f-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    prompt = capture.read_text(encoding="utf-8")
    # prompt 格式說明要點
    assert "RECONCILE-STAMP:" in prompt
    assert "APPROVED" in prompt
    assert "sha256:" in prompt
    assert "task:" in prompt
    assert "非 ##" in prompt

    sample = (
        f"RECONCILE-STAMP: codex APPROVED 2026-08-05 "
        f"sha256:{body_hash} task:{task_id}"
    )
    # 與 prompt 說明機械一致：樣本含說明中的欄位序
    assert "RECONCILE-STAMP:" in sample and "APPROVED" in sample
    assert f"sha256:{body_hash}" in sample and f"task:{task_id}" in sample

    cx_text = (h["scripts"] / "cx_run.sh").read_text(encoding="utf-8")
    raw_re = _extract_stamp_regex_from_cx(cx_text)
    # 將 bash 變數占位換成字面（與 _maybe_register_stamp_output 執行時相同）
    fam_e = re.escape("codex")
    hash_e = re.escape(body_hash)
    task_e = re.escape(task_id)
    # 源碼正則含 ${fam_e} 等；抽出的是字面 ${fam_e}
    bash_re = raw_re
    for var, val in (
        ("${fam_e}", fam_e),
        ("${hash_e}", hash_e),
        ("${task_e}", task_e),
    ):
        bash_re = bash_re.replace(var, val)
    # bash ERE → python：[[:space:]] 保留（Python re 不認）；改寫
    py_re = bash_re.replace("[[:space:]]", r"\s")
    assert re.search(py_re, sample), f"樣本未通過 cx_run 正則:\n  re={py_re}\n  sample={sample}"


# ---------------------------------------------------------------------------
# TEST-1.1-MUT
# ---------------------------------------------------------------------------


def test_11_mut_unconditional_inject_turns_consult_red(tmp_path: Path) -> None:
    """TEST-1.1-MUT：還原無條件注入 → TEST-1.1-CONSULT 轉紅。"""
    h = _harness(tmp_path)
    cx = h["scripts"] / "cx_run.sh"
    text = cx.read_text(encoding="utf-8")
    # 移除 case 分支，使預設含 RECONCILE-STAMP 的 prompt 無條件生效
    m = re.search(
        r"  # Task 1\.1 / B-32：prompt 依既有.*?\n  case \"\$\{_bk\}\" in\n.*?\n  esac\n",
        text,
        flags=re.DOTALL,
    )
    assert m, "Task 1.1 case 錨點漂移"
    cx.write_text(text[: m.start()] + text[m.end() :], encoding="utf-8")

    task_id = "GOVB0-T11-MUT-CONSULT"
    brief_rel = "handoffs/brief.md"
    _write_brief(h, kind="consult")
    rid = "c7777777-7777-4777-8777-777777777777"
    _open_round(
        h,
        round_id=rid,
        session="s-t11-mut-c",
        fams=["codex"],
        out_prefix="handoffs/t11mc",
        brief_rel=brief_rel,
        task_id=task_id,
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/t11mc-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    prompt = capture.read_text(encoding="utf-8")
    # CONSULT 斷言轉紅：RECONCILE-STAMP 出現次數不再是 0
    consult_oracle_green = prompt.count("RECONCILE-STAMP") == 0
    assert not consult_oracle_green, (
        "MUTATION 未使 CONSULT 轉紅：無條件注入後 prompt 仍無 RECONCILE-STAMP"
    )


def test_11_mut_remove_unknown_branch_turns_red(tmp_path: Path) -> None:
    """TEST-1.1-MUT：移除 unknown 分支 → UNKNOWN／無副作用斷言轉紅。"""
    h = _harness(tmp_path)

    # 1) 放寬 brief_conformance + role_gate，使 bogus 抵達 _prepare_and_run
    bc = h["scripts"] / "brief_conformance_check.sh"
    text = bc.read_text(encoding="utf-8")
    m = re.search(
        r'  \*\) echo "ERROR: 未知 brief-kind:[^"]+"; exit 2 ;;',
        text,
    )
    assert m, "brief_conformance unknown case 錨點漂移"
    bc.write_text(
        text[: m.start()] + '  bogus) : ;;\n' + m.group(0) + text[m.end() :],
        encoding="utf-8",
    )
    rg = h["scripts"] / "_role_gate.sh"
    rg_text = rg.read_text(encoding="utf-8")
    # 在 unknown 分支前插入 bogus 放行
    rg_pat = re.search(
        r'(\s+\*\)\s*\n\s+printf \'未知 brief-kind=)',
        rg_text,
    )
    if rg_pat is None:
        rg_pat = re.search(
            r"(printf '未知 brief-kind=%s)",
            rg_text,
        )
    assert rg_pat, "role_gate unknown 錨點漂移"
    insert_at = rg_pat.start()
    rg.write_text(
        rg_text[:insert_at]
        + '    bogus) : ;;\n'
        + rg_text[insert_at:],
        encoding="utf-8",
    )

    # 2) 移除 cx_run 的 * fail-closed 分支（改為 no-op）
    cx = h["scripts"] / "cx_run.sh"
    cx_text = cx.read_text(encoding="utf-8")
    star = re.search(
        r'\n    \*\)\n      echo "ERROR: unknown brief-kind=\$\{_bk\}（fail-closed）" >&2\n      exit 1\n      ;;',
        cx_text,
    )
    assert star, "cx_run unknown 分支錨點漂移"
    cx.write_text(
        cx_text[: star.start()]
        + "\n    *) : ;;  # MUTATED: unknown no longer fail-closed"
        + cx_text[star.end() :],
        encoding="utf-8",
    )

    brief = h["handoffs"] / "brief.md"
    brief.write_text("brief-kind: bogus\n\nstub\n", encoding="utf-8")
    # 開債使 _prepare_and_run 能跑到 prompt 組裝
    task_id = "GOVB0-T11-MUT-UNK"
    rid = "c8888888-8888-4888-8888-888888888888"
    _open_round(
        h,
        round_id=rid,
        session="s-t11-mut-u",
        fams=["codex"],
        out_prefix="handoffs/t11mu",
        brief_rel="handoffs/brief.md",
        task_id=task_id,
    )
    before_audit_n = _audit_line_count(h)
    r = _run_cx(
        h,
        "codex",
        "handoffs/brief.md",
        "handoffs/t11mu-codex.md",
        round_id=rid,
    )
    # UNKNOWN 斷言轉紅：rc 應為 0（放行）而非 !=0
    unknown_oracle_green = r.returncode != 0
    assert not unknown_oracle_green, (
        f"MUTATION 未使 UNKNOWN 轉紅：移除 * 後仍 rc={r.returncode}\n"
        f"{r.stdout}\n{r.stderr}"
    )
    # 無副作用斷言轉紅：audit 行數增加（family_result 等）
    after_audit_n = _audit_line_count(h)
    noside_oracle_green = after_audit_n == before_audit_n
    assert not noside_oracle_green, (
        "MUTATION 未使 NOSIDEEFFECT 轉紅：audit 行數未增加"
    )
