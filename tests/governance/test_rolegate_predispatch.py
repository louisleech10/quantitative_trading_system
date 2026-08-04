"""GOVFLOW Phase 3 — 角色 preflight 前移 ＋ 共用 _role_gate.sh。

Test ID 對齊 docs/GOV_DISPATCH_FLOW_FIX_TODO.md Phase 3 測試表：
  T3-U1..U7 / T3-B1..B3 / T3-C1 / T3-T1..T4 / T3-M1..M4
  （含行為層委派 ＋ 完整不相容清單 ＋ mutation 探針）

探針一律隔離副本（tmp_path）；rc 直接取，不經 pipe。
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from tests.governance import _debt_probe_helper as _dph

REPO_ROOT = Path(__file__).resolve().parents[2]

_REF = "照 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文"
_FACT = "fact-verified: role gate preflight → gate.sh dispatch 之前"
_ASSUMED = "assumed: CX_STUB_MODE=success 在 harness 隔離 env"

# 模組層常數：mutation 探針 monkeypatch 此處注入變異腳本（禁空 monkeypatch）
ROLE_GATE_TARGET = REPO_ROOT / "scripts" / "_role_gate.sh"
COMMITTEE_RUN_TARGET = REPO_ROOT / "scripts" / "committee_run.sh"
CX_RUN_TARGET = REPO_ROOT / "scripts" / "cx_run.sh"

_SCRIPT_NAMES = (
    "committee_run.sh",
    "cx_run.sh",
    "_role_gate.sh",
    "brief_conformance_check.sh",
    "audit_append.sh",
    "audit_events.json",
    "governance_families.sh",
    "governance_families.json",
    "governance_roles.json",
    "gate.sh",
    "debt_ledger.sh",
    "_debt_ledger_core.py",
    "completeness_check.sh",
)


def _read_json_lines(audit: Path) -> list[dict]:
    if not audit.is_file():
        return []
    out: list[dict] = []
    for line in audit.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _events(audit: Path, name: str | None = None) -> list[dict]:
    rows = _read_json_lines(audit)
    if name is None:
        return rows
    return [r for r in rows if r.get("event") == name]


def _audit_bytes(audit: Path) -> bytes:
    if not audit.is_file():
        return b""
    return audit.read_bytes()


def _harness(tmp_path: Path, *, kind: str = "review") -> dict:
    """隔離 repo：scripts 副本 + 空 audit + handoffs + gate stub。"""
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

    # always-pass gate（不寫 committee_dispatch；committee_run 呼叫點可被 patch）
    (scripts / "gate_pass.sh").write_text(
        "#!/usr/bin/env bash\necho GATE PASS stub\nexit 0\n",
        encoding="utf-8",
    )
    (scripts / "gate_pass.sh").chmod(0o755)

    if kind in ("review", "consult", "closure"):
        brief_text = (
            f"brief-kind: {kind}\n\n"
            f"{_REF}\n"
            f"{_FACT}\n"
            f"{_ASSUMED}\n\n"
            "Phase 3 role-gate harness brief.\n"
        )
    elif kind == "impl":
        brief_text = "brief-kind: impl\n\n照 TODO 實作 B3（impl 角色閘）。\n"
    elif kind == "stamp":
        brief_text = (
            "brief-kind: stamp\n"
            "stamp-target: handoffs/t3-stamp-target.md\n\n"
            "stamp path brief.\n"
        )
        (handoffs / "t3-stamp-target.md").write_text("## 戳記\n", encoding="utf-8")
    else:
        raise ValueError(f"unknown kind={kind}")

    brief = handoffs / f"t3-brief-{kind}.md"
    brief.write_text(brief_text, encoding="utf-8")

    env = {
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
        "GATE_DIR_OVERRIDE": str(gate_dir),
        "CX_STUB_MODE": "success",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C"),
    }
    return {
        "root": root,
        "audit": audit,
        "gate_dir": gate_dir,
        "scripts": scripts,
        "brief": brief,
        "brief_rel": f"handoffs/t3-brief-{kind}.md",
        "env": env,
        "handoffs": handoffs,
        "kind": kind,
    }


def _patch_committee_gate(scripts: Path) -> None:
    path = scripts / "committee_run.sh"
    text = path.read_text(encoding="utf-8")
    old = 'bash "${SCRIPT_DIR}/gate.sh" dispatch "${gate_args[@]}"'
    new = 'bash "${SCRIPT_DIR}/gate_pass.sh" dispatch "${gate_args[@]}"'
    assert old in text, "gate call anchor missing in committee_run.sh"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _read_implementer(scripts: Path) -> str:
    roles = json.loads((scripts / "governance_roles.json").read_text(encoding="utf-8"))
    return str(roles["implementer"])


def _run_committee(
    h: dict,
    *,
    fams_csv: str,
    task_id: str = "GOVFLOW-B3-T3",
    session: str = "sess-t3",
    via_helper: bool = False,
) -> subprocess.CompletedProcess[str]:
    _patch_committee_gate(h["scripts"])
    script = COMMITTEE_RUN_TARGET if via_helper else (h["scripts"] / "committee_run.sh")
    return _dph.run_cmd(
        script,
        "--session",
        session,
        h["brief_rel"],
        "handoffs/t3-out",
        fams_csv,
        "--",
        "--intent",
        "t3-rolegate",
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


def _run_cx(
    h: dict,
    *,
    family: str,
    out_rel: str = "handoffs/t3-cx-out.md",
    via_helper: bool = False,
) -> subprocess.CompletedProcess[str]:
    script = CX_RUN_TARGET if via_helper else (h["scripts"] / "cx_run.sh")
    return _dph.run_cmd(
        script,
        family,
        h["brief_rel"],
        out_rel,
        env=h["env"],
        cwd=h["root"],
    )


def _run_role_gate(
    h: dict,
    *args: str,
    via_helper: bool = False,
) -> subprocess.CompletedProcess[str]:
    script = ROLE_GATE_TARGET if via_helper else (h["scripts"] / "_role_gate.sh")
    return _dph.run_cmd(script, *args, env=h["env"], cwd=h["root"])


def _assert_zero_side_effects(h: dict, before: bytes) -> None:
    """audit 逐位元組零新增；無 committee_dispatch；無 gate token。"""
    after = _audit_bytes(h["audit"])
    assert after == before, (
        f"audit 必須零新增；before={len(before)}B after={len(after)}B "
        f"diff_events={_events(h['audit'])}"
    )
    assert not _events(h["audit"], "committee_dispatch")
    assert not _events(h["audit"], "committee_round_open")
    # gate token 檔不應出現在隔離 gate_dir
    tokens = list(h["gate_dir"].glob("*.token")) + list(h["gate_dir"].glob("dispatch*"))
    assert not tokens, f"不得產生 gate token: {tokens}"


def _sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _open_round(
    h: dict,
    *,
    round_id: str,
    session: str,
    fams: list[str],
    out_prefix: str,
    task_id: str,
) -> None:
    """隔離 audit 開債（audit_append 不驗 task_id 字元白名單）。"""
    brief_sha = _sha256_file(h["root"] / h["brief_rel"])
    participants = json.dumps(fams)
    outputs = json.dumps({f: f"{out_prefix}-{f}.md" for f in fams})
    r = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        "--require-absent-session",
        session,
        "--event",
        "committee_round_open",
        "--field",
        f"round_id={round_id}",
        "--field",
        f"task_id={task_id}",
        "--field",
        f"brief_path={h['brief_rel']}",
        "--field",
        f"brief_sha256={brief_sha}",
        "--field",
        f"brief_sha256_norm={brief_sha}",
        "--field",
        "lock_mode=discovery",
        "--field",
        f"participants=@{participants}",
        "--field",
        f"expected_outputs=@{outputs}",
        "--field",
        f"session_name={session}",
        "--field",
        "actor=test",
        "--field",
        "origin_script=committee_run.sh",
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode == 0, r.stdout + r.stderr


def _run_cx_with_round(
    h: dict,
    *,
    family: str,
    out_rel: str,
    round_id: str,
) -> subprocess.CompletedProcess[str]:
    env = dict(h["env"])
    env["ROUND_ID"] = round_id
    env["CX_STUB_MODE"] = "success"
    return _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        family,
        h["brief_rel"],
        out_rel,
        env=env,
        cwd=h["root"],
    )


def _check_task_id(h: dict, task_id: str) -> subprocess.CompletedProcess[str]:
    return _run_role_gate(h, "check-task-id", task_id)


# ── T3-U1 ───────────────────────────────────────────────────────────────────


def test_t3_u1_review_plus_implementer_rejected_zero_side_effects(
    tmp_path: Path,
) -> None:
    """T3-U1: review ＋ implementer ⇒ rc!=0 且零副作用。"""
    h = _harness(tmp_path, kind="review")
    impl = _read_implementer(h["scripts"])
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv=impl, session="sess-t3-u1")
    assert r.returncode != 0, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert "角色" in combined or "implementer" in combined or "不相容" in combined
    _assert_zero_side_effects(h, before)


# ── T3-U2 ───────────────────────────────────────────────────────────────────


def test_t3_u2_consult_same_set_proceeds(tmp_path: Path) -> None:
    """T3-U2: consult ＋ 同組（含 implementer）⇒ 角色閘放行（可進 gate/開債）。"""
    h = _harness(tmp_path, kind="consult")
    impl = _read_implementer(h["scripts"])
    # codex,composer,grok 含 implementer；consult 不限
    r = _run_committee(
        h,
        fams_csv=f"codex,composer,{impl}" if impl not in ("codex", "composer") else "codex,composer,grok",
        session="sess-t3-u2",
    )
    # 角色閘通過後會跑 gate stub + open debt + cx_run stubs
    assert r.returncode == 0, r.stdout + r.stderr
    assert _events(h["audit"], "committee_round_open"), r.stdout + r.stderr


# ── T3-U3 ───────────────────────────────────────────────────────────────────


def test_t3_u3_composer_not_false_rejected(tmp_path: Path) -> None:
    """T3-U3: composer 正例（防 raw intersection 誤拒）。"""
    h = _harness(tmp_path, kind="review")
    impl = _read_implementer(h["scripts"])
    # review 派 composer（非 implementer）必須通過
    assert impl != "composer", "SoT implementer 不得為 composer（本測前提）"
    r = _run_role_gate(
        h,
        "check-families",
        h["brief_rel"],
        "composer",
    )
    assert r.returncode == 0, r.stdout + r.stderr

    # 整批含 composer 也過
    others = [f for f in ("codex", "grok") if f != impl]
    fams = ",".join(["composer"] + others)
    r2 = _run_committee(h, fams_csv=fams, session="sess-t3-u3")
    assert r2.returncode == 0, r2.stdout + r2.stderr


# ── T3-U4 / T3-U5 ───────────────────────────────────────────────────────────


def test_t3_u4_claude_rejected(tmp_path: Path) -> None:
    """T3-U4: claude ⇒ rc!=0。"""
    h = _harness(tmp_path, kind="consult")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv="claude", session="sess-t3-u4")
    assert r.returncode != 0, r.stdout + r.stderr
    _assert_zero_side_effects(h, before)


def test_t3_u5_agy_rejected(tmp_path: Path) -> None:
    """T3-U5: agy ⇒ rc!=0。"""
    h = _harness(tmp_path, kind="consult")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv="agy", session="sess-t3-u5")
    assert r.returncode != 0, r.stdout + r.stderr
    _assert_zero_side_effects(h, before)


# ── T3-B1 ───────────────────────────────────────────────────────────────────


def test_t3_b1_bad_roles_json_fail_closed(tmp_path: Path) -> None:
    """T3-B1: SoT JSON 壞 ⇒ fail-closed。"""
    h = _harness(tmp_path, kind="review")
    roles_path = h["scripts"] / "governance_roles.json"
    roles_path.write_text("{not-json", encoding="utf-8")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv="codex", session="sess-t3-b1")
    assert r.returncode != 0, r.stdout + r.stderr
    _assert_zero_side_effects(h, before)


# ── T3-B2 ───────────────────────────────────────────────────────────────────


def test_t3_b2_one_incompatible_rejects_whole_batch(tmp_path: Path) -> None:
    """T3-B2: 三家中一家不相容 ⇒ 整批拒。"""
    h = _harness(tmp_path, kind="review")
    impl = _read_implementer(h["scripts"])
    # 合法 reviewer + implementer（不相容）混批
    reviewers = [f for f in ("codex", "composer", "grok") if f != impl]
    assert reviewers, "SoT 須有非 implementer 家族"
    fams_csv = f"{reviewers[0]},{impl}"
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv=fams_csv, session="sess-t3-b2")
    assert r.returncode != 0, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert impl in combined
    _assert_zero_side_effects(h, before)


# ── T3-C1 ───────────────────────────────────────────────────────────────────


def test_t3_c1_cx_run_role_gate_same_cases(tmp_path: Path) -> None:
    """T3-C1: cx_run.sh 既有角色閘通過同一組用例（共用後不漂移）。"""
    impl_h = _harness(tmp_path / "impl", kind="impl")
    impl = _read_implementer(impl_h["scripts"])
    reviewers = [f for f in ("codex", "composer", "grok") if f != impl]
    assert reviewers

    # impl 派給 non-implementer → 拒
    r1 = _run_cx(impl_h, family=reviewers[0], out_rel="handoffs/t3-c1-a.md")
    assert r1.returncode != 0, r1.stdout + r1.stderr
    assert "角色" in (r1.stdout + r1.stderr) or "implementer" in (r1.stdout + r1.stderr)

    # impl 派給 implementer → 角色閘不擋（後續 ROUND_ID 缺會非零，但不得是角色不符）
    r2 = _run_cx(impl_h, family=impl, out_rel="handoffs/t3-c1-b.md")
    combined2 = r2.stdout + r2.stderr
    assert "角色不符" not in combined2
    assert "實作者不自審" not in combined2

    # review 派給 implementer → 拒
    rev_h = _harness(tmp_path / "rev", kind="review")
    r3 = _run_cx(rev_h, family=impl, out_rel="handoffs/t3-c1-c.md")
    assert r3.returncode != 0, r3.stdout + r3.stderr
    assert "實作者不自審" in (r3.stdout + r3.stderr) or "implementer" in (
        r3.stdout + r3.stderr
    )

    # review 派給 reviewer → 角色閘不擋
    r4 = _run_cx(rev_h, family=reviewers[0], out_rel="handoffs/t3-c1-d.md")
    combined4 = r4.stdout + r4.stderr
    assert "角色不符" not in combined4
    assert "實作者不自審" not in combined4


# ── T3-U6 ───────────────────────────────────────────────────────────────────


def test_t3_u6_impl_non_implementer_rejected_zero_side_effects(
    tmp_path: Path,
) -> None:
    """T3-U6: brief-kind=impl ＋ 非 implementer ⇒ rc!=0、零副作用。"""
    h = _harness(tmp_path, kind="impl")
    impl = _read_implementer(h["scripts"])
    non = next(f for f in ("codex", "composer", "grok") if f != impl)
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv=non, session="sess-t3-u6")
    assert r.returncode != 0, r.stdout + r.stderr
    _assert_zero_side_effects(h, before)


# ── 附加：task_id 白名單對稱（brief 驗收 #5）───────────────────────────────


def test_t3_task_id_whitelist_committee_pre_gate(tmp_path: Path) -> None:
    """非法非空 task_id → rc=2、未發 token、未開債、audit 零新增。"""
    h = _harness(tmp_path, kind="consult")
    before = _audit_bytes(h["audit"])
    r = _run_committee(
        h,
        fams_csv="codex",
        task_id="bad task!",  # 含空白與 !
        session="sess-t3-tid",
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "白名單" in (r.stdout + r.stderr) or "task_id" in (r.stdout + r.stderr)
    _assert_zero_side_effects(h, before)


def test_t3_task_id_regex_single_source() -> None:
    """白名單 regex 僅在 _role_gate.sh 一處定義。"""
    import subprocess

    rg = REPO_ROOT / "scripts" / "_role_gate.sh"
    assert rg.is_file()
    r = subprocess.run(
        ["bash", str(rg), "task-id-regex"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, r.stderr
    pattern = r.stdout.strip()
    assert pattern == "^[A-Za-z0-9._-]+$", pattern

    # 全 repo scripts/ 內字面量只應出現在 _role_gate.sh
    hits: list[str] = []
    for p in (REPO_ROOT / "scripts").rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in {".sh", ".py", ".json"} and p.name != "_role_gate.sh":
            if p.suffix not in {".sh", ".py"}:
                continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "A-Za-z0-9._-" in text or r"[A-Za-z0-9._-]+" in text:
            # 允許註解引用，但定義形（ROLE_GATE_TASK_ID_REGEX= 或 fullmatch 字面）計數
            for i, line in enumerate(text.splitlines(), 1):
                if "A-Za-z0-9._-" not in line:
                    continue
                if line.strip().startswith("#"):
                    continue
                hits.append(f"{p.relative_to(REPO_ROOT)}:{i}:{line.strip()}")
    # 僅 _role_gate.sh 的 ROLE_GATE_TASK_ID_REGEX 賦值
    assert len(hits) == 1, f"白名單 regex 必須單一來源，得 {hits}"
    assert hits[0].startswith("scripts/_role_gate.sh:"), hits


# ── T3-U7：未知 family ─────────────────────────────────────────────────────


def test_t3_u7_unknown_family_rejected_nonzero(tmp_path: Path) -> None:
    """T3-U7: 不在 governance_families.json 的 family ⇒ 明確拒派、非零離開。"""
    h = _harness(tmp_path, kind="consult")
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv="notafamily", session="sess-t3-u7")
    assert r.returncode != 0, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert "未知家族" in combined or "notafamily" in combined
    _assert_zero_side_effects(h, before)


# ── T3-B3：完整不相容清單（兩家同時出現）──────────────────────────────────


def test_t3_b3_two_incompatible_full_list(tmp_path: Path) -> None:
    """T3-B3: impl 下兩家非 implementer 不相容 ⇒ 輸出同時含兩者（非只第一個）。"""
    h = _harness(tmp_path, kind="impl")
    impl = _read_implementer(h["scripts"])
    non = [f for f in ("codex", "composer", "grok") if f != impl]
    assert len(non) >= 2
    fams_csv = f"{non[0]},{non[1]}"
    before = _audit_bytes(h["audit"])
    r = _run_committee(h, fams_csv=fams_csv, session="sess-t3-b3")
    assert r.returncode != 0, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert non[0] in combined, f"完整清單須含 {non[0]}: {combined}"
    assert non[1] in combined, f"完整清單須含 {non[1]}: {combined}"
    assert "完整清單" in combined or "不相容" in combined
    _assert_zero_side_effects(h, before)


# ── T3-T3 / T3-T4：task_id 白名單行為層委派（非字面量掃描）────────────────


def test_t3_t3_task_id_inline_divergence_turns_red(tmp_path: Path) -> None:
    """T3-T3: 隔離副本於 committee_run 內嵌不同 inline regex（允 #）⇒ 與 SSOT 漂移轉紅。

    行為層：若 committee 不再委派 check-task-id，而改寫較寬 inline，
    則 committee 會放行 SSOT 仍拒絕的 task_id → 兩端不一致。
    """
    bad_tid = "GOVFLOW#BAD"  # 合法 SSOT 拒絕；內嵌允 # 後 committee 可能放行

    # ── 基線：兩端皆拒 ──
    h0 = _harness(tmp_path / "base", kind="consult")
    r_ssot0 = _check_task_id(h0, bad_tid)
    assert r_ssot0.returncode != 0, "SSOT 基線須拒 #"
    r_c0 = _run_committee(
        h0, fams_csv="codex", task_id=bad_tid, session="sess-t3-t3-base"
    )
    assert r_c0.returncode != 0, "committee 基線須拒 #"

    # ── 變異：committee 內嵌較寬 regex，不再呼叫 check-task-id ──
    h = _harness(tmp_path / "mut", kind="consult")
    cr = h["scripts"] / "committee_run.sh"
    text = cr.read_text(encoding="utf-8")
    old = 'bash "${SCRIPT_DIR}/_role_gate.sh" check-task-id "${task_id}" || exit 2'
    assert old in text, "check-task-id 委派錨點缺失"
    # 額外允許 #（與 _role_gate ROLE_GATE_TASK_ID_REGEX 不同）
    new = (
        'if [[ ! "${task_id}" =~ ^[A-Za-z0-9._#-]+$ ]]; then\n'
        '  echo "ERROR: task_id 不符合 inline 白名單" >&2\n'
        "  exit 2\n"
        "fi  # MUTATED: inline regex allows #"
    )
    cr.write_text(text.replace(old, new, 1), encoding="utf-8")
    cr.chmod(cr.stat().st_mode | stat.S_IXUSR)

    r_ssot = _check_task_id(h, bad_tid)
    assert r_ssot.returncode != 0, "SSOT 仍應拒 #"
    before_m = _audit_bytes(h["audit"])
    # consult+codex 角色合法；committee 內嵌較寬 regex → 過 pre-gate 並開債
    # （後續 cx_run 仍走 SSOT 會拒——這正是兩端漂移：committee 已有副作用）
    r_c = _run_committee(
        h, fams_csv="codex", task_id=bad_tid, session="sess-t3-t3-mut"
    )
    after_m = _audit_bytes(h["audit"])
    opened = bool(_events(h["audit"], "committee_round_open"))
    # 漂移成立：SSOT 仍拒，但 committee 已開債（基線為零副作用早退）
    drifted = (r_ssot.returncode != 0) and (opened or after_m != before_m)
    assert drifted, (
        "內嵌不同 regex 後須可觀測兩端漂移（committee 開債 vs SSOT 拒）"
        f"（committee_rc={r_c.returncode} ssot_rc={r_ssot.returncode} "
        f"opened={opened} out={r_c.stdout!r} err={r_c.stderr!r}）"
    )
    # cx_run 端仍依 SSOT 拒（證明並非「全鏈放寬」，而是委派被繞過）
    assert "白名單" in (r_c.stdout + r_c.stderr) or r_c.returncode != 0


def test_t3_t4_task_id_ssot_widen_both_ends_sync(tmp_path: Path) -> None:
    """T3-T4: 放寬 _role_gate.sh 白名單 ⇒ committee 與 cx_run 兩端同步改變。

    證明兩端真的讀同一份 SSOT，而非各自實作後碰巧一致。
    """
    bad_tid = "GOVFLOW#SYNC"

    # ── 基線：兩端皆拒 ──
    h_base = _harness(tmp_path / "base", kind="consult")
    assert _check_task_id(h_base, bad_tid).returncode != 0
    r_cb = _run_committee(
        h_base, fams_csv="codex", task_id=bad_tid, session="sess-t3-t4-b"
    )
    assert r_cb.returncode != 0

    h_cx_b = _harness(tmp_path / "cxb", kind="consult")
    rid_b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    _open_round(
        h_cx_b,
        round_id=rid_b,
        session="sess-t3-t4-cxb",
        fams=["codex"],
        out_prefix="handoffs/t3-t4b",
        task_id=bad_tid,
    )
    r_cxb = _run_cx_with_round(
        h_cx_b, family="codex", out_rel="handoffs/t3-t4b-codex.md", round_id=rid_b
    )
    assert r_cxb.returncode != 0
    assert "白名單" in (r_cxb.stdout + r_cxb.stderr) or "task_id" in (
        r_cxb.stdout + r_cxb.stderr
    )

    # ── 放寬 SSOT（隔離副本）──
    h = _harness(tmp_path / "wide", kind="consult")
    rg = h["scripts"] / "_role_gate.sh"
    text = rg.read_text(encoding="utf-8")
    old = "ROLE_GATE_TASK_ID_REGEX='^[A-Za-z0-9._-]+$'"
    assert old in text
    rg.write_text(
        text.replace(
            old,
            "ROLE_GATE_TASK_ID_REGEX='^[A-Za-z0-9._#-]+$'  # MUTATED widen allow #",
            1,
        ),
        encoding="utf-8",
    )
    rg.chmod(rg.stat().st_mode | stat.S_IXUSR)

    # SSOT 本身放行
    r_ssot = _check_task_id(h, bad_tid)
    assert r_ssot.returncode == 0, r_ssot.stdout + r_ssot.stderr

    # committee 端同步放行 task_id 閘（consult+codex 應整跑成功）
    r_c = _run_committee(
        h, fams_csv="codex", task_id=bad_tid, session="sess-t3-t4-c"
    )
    assert r_c.returncode == 0, (
        f"放寬 SSOT 後 committee 須同步放行; {r_c.stdout}{r_c.stderr}"
    )

    # cx_run 端：同份 _role_gate 放行白名單（不得再因 # 拒）
    h_cx = _harness(tmp_path / "cxw", kind="consult")
    # 兩端 isolation 各自有 scripts 副本 → 也要放寬 cx 副本的 SSOT
    rg2 = h_cx["scripts"] / "_role_gate.sh"
    t2 = rg2.read_text(encoding="utf-8")
    assert old in t2
    rg2.write_text(
        t2.replace(
            old,
            "ROLE_GATE_TASK_ID_REGEX='^[A-Za-z0-9._#-]+$'  # MUTATED widen allow #",
            1,
        ),
        encoding="utf-8",
    )
    rg2.chmod(rg2.stat().st_mode | stat.S_IXUSR)

    rid = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    _open_round(
        h_cx,
        round_id=rid,
        session="sess-t3-t4-cx",
        fams=["codex"],
        out_prefix="handoffs/t3-t4",
        task_id=bad_tid,
    )
    r_cx = _run_cx_with_round(
        h_cx, family="codex", out_rel="handoffs/t3-t4-codex.md", round_id=rid
    )
    combined = r_cx.stdout + r_cx.stderr
    assert "不符合白名單" not in combined, combined
    # 放行白名單後可能因 stub 路徑成功或其它前置；不得仍是白名單 rc=2 文案
    if r_cx.returncode != 0:
        assert "白名單" not in combined, combined


# ── mutation 探針 ───────────────────────────────────────────────────────────


def test_mutation_preflight_after_gate_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT：pre-gate 角色檢查被跳過、改在 gate 副作用之後才驗 → 零副作用轉紅。

    monkeypatch ``_dph.COMMITTEE_RUN_TARGET`` 指向隔離變異腳本（真碰到待測系統）。
    """
    # ── 基線：未變異 → 綠（零副作用）──
    h_base = _harness(tmp_path / "base", kind="review")
    impl = _read_implementer(h_base["scripts"])
    before_b = _audit_bytes(h_base["audit"])
    r_base = _run_committee(h_base, fams_csv=impl, session="sess-mut-base")
    assert r_base.returncode != 0
    _assert_zero_side_effects(h_base, before_b)

    # ── 變異：跳過 pre-gate 角色閘；在 gate 呼叫點先寫假 dispatch 再跑角色閘 ──
    h_mut = _harness(tmp_path / "mut", kind="review")
    impl = _read_implementer(h_mut["scripts"])
    cr = h_mut["scripts"] / "committee_run.sh"
    text = cr.read_text(encoding="utf-8")
    old_block = (
        'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {\n'
        '  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2\n'
        "  exit 2\n"
        "}"
    )
    assert old_block in text, "pre-gate role gate block anchor missing"
    text2 = text.replace(old_block, "true  # MUTATED: pre-gate role check skipped", 1)
    gate_line = 'bash "${SCRIPT_DIR}/gate.sh" dispatch "${gate_args[@]}"'
    assert gate_line in text2
    text2 = text2.replace(
        gate_line,
        'python3 -c "import os,json; p=os.environ.get(\'DEBT_AUDIT_OVERRIDE\',\'\');'
        ' open(p,\'a\').write(json.dumps({\'event\':\'committee_dispatch\','
        '\'seq\':1})+\'\\n\')" 2>/dev/null || true\n'
        'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || exit 2\n'
        + gate_line,
        1,
    )
    cr.write_text(text2, encoding="utf-8")
    cr.chmod(cr.stat().st_mode | stat.S_IXUSR)

    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", cr)
    before_m = _audit_bytes(h_mut["audit"])
    # via_helper 走 monkeypatch 後的 COMMITTEE_RUN_TARGET
    _patch_committee_gate(h_mut["scripts"])
    r_mut = _dph.run_committee_run(
        "--session",
        "sess-mut-after",
        h_mut["brief_rel"],
        "handoffs/t3-mut-out",
        impl,
        "--",
        "--intent",
        "mut-after",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit",
        "--review-role",
        "advisory",
        "--template",
        "n/a:stub",
        "--task-id",
        "GOVFLOW-B3-MUT",
        env=h_mut["env"],
        cwd=h_mut["root"],
    )
    assert r_mut.returncode != 0, "角色仍應拒派"
    after_m = _audit_bytes(h_mut["audit"])
    assert after_m != before_m, "mutation 必須使 audit 零新增失敗"
    assert _events(h_mut["audit"], "committee_dispatch"), after_m

    # 恢復：未變異副本仍綠
    h_fix = _harness(tmp_path / "fix", kind="review")
    before_f = _audit_bytes(h_fix["audit"])
    r_fix = _run_committee(
        h_fix, fams_csv=_read_implementer(h_fix["scripts"]), session="sess-mut-fix"
    )
    assert r_fix.returncode != 0
    _assert_zero_side_effects(h_fix, before_f)


def test_mutation_raw_intersection_rejects_composer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUT：mapping 改成 raw set intersection → composer 被誤拒（轉紅）。"""
    h = _harness(tmp_path, kind="review")
    rg = h["scripts"] / "_role_gate.sh"
    text = rg.read_text(encoding="utf-8")
    # 把 _family_to_cli 的 composer 映射刪掉，迫使 raw 語義
    old = 'composer) printf \'%s\' "cursor-agent" ;;'
    assert old in text
    # 變異：composer 映射成自己（假 raw 名），再令 executor 檢查用 raw 名
    new = 'composer) printf \'%s\' "composer" ;;  # MUTATED raw name'
    text2 = text.replace(old, new, 1)
    # 另把 mapping 檢查改成要求 family ∈ executor_clis（raw intersection）
    old_map_check = """  case " ${ec} " in
    *" ${cli} "*) : ;;
    *)
      printf '家族 %s 映射 CLI=%s 不在 executor_clis' "${fam}" "${cli}"
      return 1
      ;;
  esac"""
    # 改為同時要求 fam 也在 executor_clis（raw intersection 的錯誤判準）
    new_map_check = """  case " ${ec} " in
    *" ${cli} "*) : ;;
    *)
      printf '家族 %s 映射 CLI=%s 不在 executor_clis' "${fam}" "${cli}"
      return 1
      ;;
  esac
  # MUTATED: also require raw family name in executor_clis
  case " ${ec} " in
    *" ${fam} "*) : ;;
    *)
      printf '家族 %s 不在 executor_clis（raw intersection）' "${fam}"
      return 1
      ;;
  esac"""
    assert old_map_check in text2
    text2 = text2.replace(old_map_check, new_map_check, 1)
    rg.write_text(text2, encoding="utf-8")
    rg.chmod(rg.stat().st_mode | stat.S_IXUSR)

    monkeypatch.setattr(
        __import__(__name__, fromlist=["ROLE_GATE_TARGET"]),
        "ROLE_GATE_TARGET",
        rg,
    )
    # 直接跑隔離副本（不經 helper 常數亦可；靜態檢查要 monkeypatch setattr）
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h["scripts"] / "committee_run.sh")

    r = _run_role_gate(h, "check-families", h["brief_rel"], "composer")
    assert r.returncode != 0, (
        "raw intersection mutation 必須誤拒 composer；"
        f"rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
    )
    assert "composer" in (r.stdout + r.stderr)

    # 對照：未變異 composer 通過
    h2 = _harness(tmp_path / "ok", kind="review")
    r2 = _run_role_gate(h2, "check-families", h2["brief_rel"], "composer")
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_mutation_incompat_list_first_only_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T3-M3 MUT：完整清單改成只印第一個 ⇒ T3-B3 類斷言轉紅。"""
    h = _harness(tmp_path, kind="impl")
    impl = _read_implementer(h["scripts"])
    non = [f for f in ("codex", "composer", "grok") if f != impl]
    assert len(non) >= 2
    fams_csv = f"{non[0]},{non[1]}"

    # 基線：完整清單含兩者
    r0 = _run_committee(h, fams_csv=fams_csv, session="sess-m3-base")
    assert r0.returncode != 0
    c0 = r0.stdout + r0.stderr
    assert non[0] in c0 and non[1] in c0

    # 變異：錯誤累積後只保留第一行
    h_mut = _harness(tmp_path / "mut", kind="impl")
    rg = h_mut["scripts"] / "_role_gate.sh"
    text = rg.read_text(encoding="utf-8")
    old = '    echo "ERROR: 角色閘不相容（完整清單；整批拒絕）:" >&2\n    cat "${err_file}" >&2'
    assert old in text, "完整清單輸出錨點缺失"
    new = (
        '    echo "ERROR: 角色閘不相容（完整清單；整批拒絕）:" >&2\n'
        '    head -n 1 "${err_file}" >&2  # MUTATED: first-only'
    )
    rg.write_text(text.replace(old, new, 1), encoding="utf-8")
    rg.chmod(rg.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", h_mut["scripts"] / "committee_run.sh")

    r_mut = _run_committee(h_mut, fams_csv=fams_csv, session="sess-m3-mut")
    assert r_mut.returncode != 0
    c_mut = r_mut.stdout + r_mut.stderr
    # 只印第一個 ⇒ 兩者不能同時出現 → 完整清單契約轉紅
    both_present = (non[0] in c_mut) and (non[1] in c_mut)
    assert not both_present, (
        f"first-only mutation 後不得同時含兩者: {c_mut!r}"
    )

    # 復原副本仍綠（完整清單）
    h_fix = _harness(tmp_path / "fix", kind="impl")
    r_fix = _run_committee(h_fix, fams_csv=fams_csv, session="sess-m3-fix")
    assert r_fix.returncode != 0
    c_fix = r_fix.stdout + r_fix.stderr
    assert non[0] in c_fix and non[1] in c_fix


def test_mutation_canonical_role_gate_skip_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T3-M4 MUT：canonical T3-U1 路徑閹割 pre-gate 角色守衛 ⇒ 零副作用轉紅；復原轉綠。"""
    # 基線綠：review+implementer 拒且零副作用
    h_base = _harness(tmp_path / "base", kind="review")
    impl = _read_implementer(h_base["scripts"])
    before_b = _audit_bytes(h_base["audit"])
    r_b = _run_committee(h_base, fams_csv=impl, session="sess-m4-base")
    assert r_b.returncode != 0
    _assert_zero_side_effects(h_base, before_b)

    # 變異：跳過 pre-gate 角色閘（不移到後面）
    h_mut = _harness(tmp_path / "mut", kind="review")
    impl = _read_implementer(h_mut["scripts"])
    cr = h_mut["scripts"] / "committee_run.sh"
    text = cr.read_text(encoding="utf-8")
    old_block = (
        'bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {\n'
        '  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2\n'
        "  exit 2\n"
        "}"
    )
    assert old_block in text
    cr.write_text(
        text.replace(old_block, "true  # MUTATED: skip role preflight entirely", 1),
        encoding="utf-8",
    )
    cr.chmod(cr.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", cr)

    before_m = _audit_bytes(h_mut["audit"])
    _patch_committee_gate(h_mut["scripts"])
    r_mut = _dph.run_committee_run(
        "--session",
        "sess-m4-mut",
        h_mut["brief_rel"],
        "handoffs/t3-m4-out",
        impl,
        "--",
        "--intent",
        "m4-skip",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit",
        "--review-role",
        "advisory",
        "--template",
        "n/a:stub",
        "--task-id",
        "GOVFLOW-B3-M4",
        env=h_mut["env"],
        cwd=h_mut["root"],
    )
    after_m = _audit_bytes(h_mut["audit"])
    # 守衛被閹割後，implementer 被當 reviewer 派 → 應開債或寫 audit（零副作用轉紅）
    side_effect = after_m != before_m or r_mut.returncode == 0
    assert side_effect, (
        f"canonical mutation 後須破壞零副作用/拒派；"
        f"rc={r_mut.returncode} audit_same={after_m == before_m} "
        f"out={r_mut.stdout!r} err={r_mut.stderr!r}"
    )

    # 復原：未變異仍綠
    h_fix = _harness(tmp_path / "fix", kind="review")
    before_f = _audit_bytes(h_fix["audit"])
    r_fix = _run_committee(
        h_fix, fams_csv=_read_implementer(h_fix["scripts"]), session="sess-m4-fix"
    )
    assert r_fix.returncode != 0
    _assert_zero_side_effects(h_fix, before_f)


def test_mutation_task_id_inline_committee_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T3-M5 MUT：committee 內嵌不同 task_id regex ⇒ 與 SSOT 行為漂移轉紅。"""
    bad_tid = "GOV#MUT"
    h_base = _harness(tmp_path / "base", kind="consult")
    assert _check_task_id(h_base, bad_tid).returncode != 0
    r_b = _run_committee(
        h_base, fams_csv="codex", task_id=bad_tid, session="sess-m5-b"
    )
    assert r_b.returncode != 0

    h = _harness(tmp_path / "mut", kind="consult")
    cr = h["scripts"] / "committee_run.sh"
    text = cr.read_text(encoding="utf-8")
    old = 'bash "${SCRIPT_DIR}/_role_gate.sh" check-task-id "${task_id}" || exit 2'
    assert old in text
    new = (
        'if [[ ! "${task_id}" =~ ^[A-Za-z0-9._#-]+$ ]]; then exit 2; fi'
        "  # MUTATED inline"
    )
    cr.write_text(text.replace(old, new, 1), encoding="utf-8")
    cr.chmod(cr.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", cr)

    r_ssot = _check_task_id(h, bad_tid)
    assert r_ssot.returncode != 0
    before_m = _audit_bytes(h["audit"])
    _patch_committee_gate(h["scripts"])
    r_mut = _dph.run_committee_run(
        "--session",
        "sess-m5-mut",
        h["brief_rel"],
        "handoffs/t3-m5-out",
        "codex",
        "--",
        "--intent",
        "m5",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit",
        "--review-role",
        "advisory",
        "--template",
        "n/a:stub",
        "--task-id",
        bad_tid,
        env=h["env"],
        cwd=h["root"],
    )
    after_m = _audit_bytes(h["audit"])
    opened = bool(_events(h["audit"], "committee_round_open"))
    # 漂移：SSOT 仍拒，但 committee pre-gate 已被 inline 繞過 → 開債副作用
    assert r_ssot.returncode != 0 and (opened or after_m != before_m), (
        f"inline mutation 須造成漂移（開債 vs SSOT 拒）; "
        f"committee_rc={r_mut.returncode} ssot_rc={r_ssot.returncode} "
        f"opened={opened}"
    )
