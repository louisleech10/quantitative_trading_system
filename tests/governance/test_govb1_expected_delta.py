"""GOVB1 Task 1.3 — EXPECTED-DELTA: 宣告閘（票 B-29）。

階段 1：空區塊修正、--only、gate --brief+(c)、committee_run (e)、
lifecycle expected_delta 節＋embed、superset 超集（見 lifecycle_matrix）。
階段 2：(d) fail-closed —— 一切 dispatch 皆須 --brief（同時關閉 R-11／R-12）。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BRIEF_CONF = REPO / "scripts" / "brief_conformance_check.sh"
GATE = REPO / "scripts" / "gate.sh"
COMMITTEE_RUN = REPO / "scripts" / "committee_run.sh"
LIFECYCLE = REPO / "scripts" / "govflow_lifecycle.json"
CX_RUN = REPO / "scripts" / "cx_run.sh"
FIXTURE = REPO / "tests" / "governance" / "fixtures" / "govb1"
RECONCILE = REPO / "handoffs" / "reconcile" / "20260807-govb1-x-stamp-r4" / "synth.md"


def _run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    kw.setdefault("cwd", str(REPO))
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        **kw,  # type: ignore[arg-type]
    )


def _out(proc: subprocess.CompletedProcess[str]) -> str:
    return (proc.stdout or "") + (proc.stderr or "")


# ── brief_conformance --only / full ──────────────────────────────────


def test_absent_only_rc_nonzero_mentions_expected_delta() -> None:
    """ASSERT --only expected-delta absent fixture → rc≠0 且 stderr/stdout 含 EXPECTED-DELTA。"""
    proc = _run(
        ["bash", str(BRIEF_CONF), "--only", "expected-delta", str(FIXTURE / "brief_impl_delta_absent.md")]
    )
    assert proc.returncode != 0, _out(proc)
    assert "EXPECTED-DELTA" in _out(proc)


def test_present_only_rc_zero() -> None:
    proc = _run(
        ["bash", str(BRIEF_CONF), "--only", "expected-delta", str(FIXTURE / "brief_impl_delta_present.md")]
    )
    assert proc.returncode == 0, _out(proc)


def test_empty_block_only_rc_nonzero() -> None:
    """空區塊（僅標題）⇒ rc≠0。"""
    proc = _run(
        ["bash", str(BRIEF_CONF), "--only", "expected-delta", str(FIXTURE / "brief_impl_delta_empty.md")]
    )
    assert proc.returncode != 0, _out(proc)
    assert "EXPECTED-DELTA" in _out(proc)
    assert "空" in _out(proc)


def test_consult_only_rc_zero_not_applicable() -> None:
    """非 impl ⇒ --only expected-delta 不適用 rc=0。"""
    proc = _run(
        ["bash", str(BRIEF_CONF), "--only", "expected-delta", str(FIXTURE / "brief_consult_ok.md")]
    )
    assert proc.returncode == 0, _out(proc)


def test_t_b4_2_unknown_only_name_fail_closed() -> None:
    """T-B4-2：--only <未知名> ⇒ rc≠0，stderr 具名。"""
    proc = _run(
        ["bash", str(BRIEF_CONF), "--only", "not-a-real-check", str(FIXTURE / "brief_impl_delta_present.md")]
    )
    assert proc.returncode != 0, _out(proc)
    assert "未知" in _out(proc) or "not-a-real-check" in _out(proc)


def test_full_path_does_not_yet_enforce_expected_delta() -> None:
    """階段 1：full path 暫不強制（B45 harness 死鎖）；--only／gate (c) 強制。

    主委擴大 scope 後應改回：absent full ⇒ rc≠0；present full ⇒ rc=0。
    """
    abs_p = _run(["bash", str(BRIEF_CONF), str(FIXTURE / "brief_impl_delta_absent.md")])
    assert abs_p.returncode == 0, (
        "階段 1 full path 不應因缺 EXPECTED-DELTA 擋 minimal impl（harness 共存）\n"
        + _out(abs_p)
    )
    pres = _run(["bash", str(BRIEF_CONF), str(FIXTURE / "brief_impl_delta_present.md")])
    assert pres.returncode == 0, _out(pres)


# ── T-B4-1 mutation：移除非空檢查 ⇒ 空區塊轉綠 ─────────────────────


def test_t_b4_1_mutation_remove_nonempty_check_empty_turns_green(tmp_path: Path) -> None:
    """mutation：把非空 body 檢查整段移除 ⇒ 空區塊 fixture 由紅轉綠。

    移除後仍紅 ⇒ 寫的仍是恆真檢查（不算完成）。
    """
    src = BRIEF_CONF.read_text(encoding="utf-8")
    # 錨定＝awk 判定器內「非空」那一條裁決〔B4-REVIEW-R2 群集 2 改寫後之新錨點〕。
    # 條件短路成 0 ⇒ 空區塊不再判 EMPTY ⇒ 落到 print "OK"。
    # 🔴 錨點失配時本測 **fail-closed 轉紅**（不得靜默通過）——實作改寫後須同步更新錨點。
    anchor = '      if (body == 0 && inline_body == 0) { print "EMPTY"; exit }'
    mut = src.replace(anchor, '      if (0) { print "EMPTY"; exit }', 1)
    assert mut != src, "mutation 未命中非空檢查錨點"
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "brief_conformance_check.sh").write_text(mut, encoding="utf-8")
    (scripts / "brief_conformance_check.sh").chmod(0o755)
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    empty = tmp_path / "empty.md"
    empty.write_text(
        (FIXTURE / "brief_impl_delta_empty.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # production 仍紅
    prod = _run(
        ["bash", str(BRIEF_CONF), "--only", "expected-delta", str(FIXTURE / "brief_impl_delta_empty.md")]
    )
    assert prod.returncode != 0, "production 空區塊應紅"
    # mutation 轉綠
    proc = _run(
        ["bash", str(scripts / "brief_conformance_check.sh"), "--only", "expected-delta", str(empty)],
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, (
        "移除非空檢查後空區塊應假綠（證明檢查非恆真）\n" + _out(proc)
    )


# ── lifecycle keys / embed ───────────────────────────────────────────


def test_lifecycle_keys_include_expected_delta() -> None:
    """頂層 keys 須 **⊇** 字面凍結集合（append-only 契約，**非** exact-equality）。

    〔20260809-GOVB1-B4-REVIEW-R2 群集 4／CODEX-R2-P1-04〕
    原版寫 `keys == [...]`：Task 4.2 新增 `zero_findings_contract` 節時**必然回歸**，
    與 JSON 的 single-writer／append-only 契約矛盾。
    """
    required = {"_doc", "expected_delta", "kinds", "stages"}
    proc = _run(["jq", "-r", "keys[]", str(LIFECYCLE)])
    assert proc.returncode == 0, proc.stderr
    keys = {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}
    assert required <= keys, f"lifecycle 頂層缺 keys: {sorted(required - keys)}"


def test_lifecycle_embed_gate_pass() -> None:
    """T-B4-6：lifecycle_embed 兩支 embed ≡ JSON。"""
    proc = _run(["bash", str(REPO / "scripts" / "govb1_final_gate.sh"), "--only", "lifecycle_embed"])
    assert proc.returncode == 0, _out(proc)


def test_cx_run_only_embed_line_covariant() -> None:
    """cx_run.sh 共變面：相對 HEAD 若有 diff，僅允許 _LIFECYCLE_EMBED_B64 行。"""
    proc = _run(["git", "diff", "HEAD", "--", str(CX_RUN.relative_to(REPO))])
    assert proc.returncode == 0
    diff = proc.stdout or ""
    if not diff.strip():
        return  # 已 commit 或無差
    content_lines = [
        ln
        for ln in diff.splitlines()
        if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))
    ]
    for ln in content_lines:
        assert "_LIFECYCLE_EMBED_B64" in ln, f"cx_run 非 embed 行被改: {ln[:120]}"


# ── gate --brief 掛點 ────────────────────────────────────────────────


def _gate_env(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    audit = tmp_path / "debt_audit.log"
    audit.write_text("", encoding="utf-8")
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env["DEBT_AUDIT_OVERRIDE"] = str(audit)
    env["GOVERNANCE_TEST_HARNESS"] = "1"
    return env


def _dispatch_brief_only(brief: Path) -> list[str]:
    """只測 (c) 掛點：不帶 --spec／--reconcile，避開 stamp provenance 與 completeness。"""
    return [
        "bash",
        str(GATE),
        "dispatch",
        "--task-id",
        "20260807-GOVB1-X-IMPL-R2",
        "--risk",
        "low",
        "--intent",
        "probe",
        "--facts-asked",
        "probe",
        "--review-role",
        "probe",
        "--template",
        "n/a:expected-delta-hook-probe",
        "--brief",
        str(brief),
    ]


def test_gate_brief_absent_rejects_with_expected_delta(tmp_path: Path) -> None:
    """gate + --brief absent ⇒ rc≠0 且輸出含 缺 EXPECTED-DELTA。"""
    env = _gate_env(tmp_path)
    proc = _run(
        _dispatch_brief_only(FIXTURE / "brief_impl_delta_absent.md"),
        env=env,
    )
    assert proc.returncode != 0, _out(proc)
    assert "缺 EXPECTED-DELTA" in _out(proc), _out(proc)


def test_gate_brief_present_accepts(tmp_path: Path) -> None:
    """gate + --brief present ⇒ rc=0（debt 隔離；無 --spec 以免 stamp 路徑干擾）。"""
    env = _gate_env(tmp_path)
    proc = _run(
        _dispatch_brief_only(FIXTURE / "brief_impl_delta_present.md"),
        env=env,
    )
    assert proc.returncode == 0, _out(proc)


def test_t_b4_3_attribution_comment_out_hook_turns_red(tmp_path: Path) -> None:
    """T-B4-3：把 (c) 掛點註解掉 ⇒『缺 EXPECTED-DELTA』歸因斷言轉紅（rc 可能仍≠0 因他因）。

    以突變 gate 腳本：移除 expected-delta 呼叫後，absent brief 不得再印 缺 EXPECTED-DELTA。
    """
    src = GATE.read_text(encoding="utf-8")
    assert "expected-delta" in src, "gate 未掛 expected-delta"
    mut = src.replace(
        'bash "${SCRIPT_DIR}/brief_conformance_check.sh" --only expected-delta "${brief}"',
        'true  # MUTATION: skip expected-delta hook',
    )
    assert mut != src
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    # gate 需同目錄工具；最小：只拷 gate + brief_conf + 依賴會從 REPO 找 SCRIPT_DIR
    # 故改寫 SCRIPT_DIR 指向 REPO/scripts，把突變 gate 放 tmp 並 patch SCRIPT_DIR
    gate_mut = scripts / "gate.sh"
    mut2 = mut.replace(
        'SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"',
        f'SCRIPT_DIR="{REPO / "scripts"}"',
        1,
    )
    gate_mut.write_text(mut2, encoding="utf-8")
    gate_mut.chmod(0o755)

    env = _gate_env(tmp_path)
    proc = _run(
        [
            "bash",
            str(gate_mut),
            "dispatch",
            "--task-id",
            "20260807-GOVB1-X-IMPL-R2",
            "--risk",
            "low",
            "--intent",
            "probe",
            "--facts-asked",
            "probe",
            "--review-role",
            "probe",
            "--template",
            "n/a:expected-delta-hook-probe",
            "--brief",
            str(FIXTURE / "brief_impl_delta_absent.md"),
        ],
        env=env,
        cwd=str(REPO),
    )
    # 掛點拿掉後不得再以 缺 EXPECTED-DELTA 歸因（可能 rc=0 放行，或因他因≠0）
    assert "缺 EXPECTED-DELTA" not in _out(proc), (
        "掛點註解後仍見 缺 EXPECTED-DELTA — 歸因錨點失效\n" + _out(proc)
    )


def test_t13_n2_committee_run_wires_brief() -> None:
    """T-1.3-N2：committee_run 須 append --brief。"""
    text = COMMITTEE_RUN.read_text(encoding="utf-8")
    assert "gate_args+=(--brief" in text or "gate_args+=(--brief " in text
    n = text.count("--brief")
    assert n >= 1


def test_gate_accepts_brief_flag_in_parser() -> None:
    """--brief 為已知旗標（未知參數路徑不再誤擋）。"""
    src = GATE.read_text(encoding="utf-8")
    assert re.search(r"--brief\)\s+brief=", src), "gate 缺 --brief case"


def test_d_must_not_use_spec_as_impl_proxy() -> None:
    """🔴 **永久規則**：(d) 之觸發條件禁以 `--spec` 為 impl 之代理。

    〔`CODEX-R1-P0-03`〕audit 實測：31 筆 impl round 中 `spec` 空值 **8 筆（25.8%）**
    ⇒ 以 `--spec` 圈定會讓那 8 筆**完全繞過**。

    本測原名 `test_stage1_does_not_enable_d_fail_closed`（階段 1 禁啟 (d)）；
    階段 2 落地後，其 regex 實際擋的是「`--spec` 代理版 (d)」——那是**永久禁令**，
    故正名。**不是**禁止 (d) 本身。
    """
    src = GATE.read_text(encoding="utf-8")
    banned = re.search(
        r'\[ -n "\$\{spec\}" \].*\[ -z "\$\{brief\}" \].*miss brief',
        src,
        re.S,
    )
    assert banned is None, "(d) 不得以 --spec 為 impl 判準之代理（25.8% 會繞過）"


# ── 階段 2：(d) fail-closed ──────────────────────────────────────────


def test_t13_n1_dispatch_without_brief_is_rejected() -> None:
    """`T-1.3-N1`：一切 dispatch 缺 `--brief` ⇒ 拒發 token，**且須歸因**。

    🔴 **歸因不可省**：未知參數／缺其他必填欄同樣是非零，只斷 `rc!=0`
    會讓「掛點根本沒跑」也算通過。故另斷輸出含 `--brief`。
    """
    proc = _run([
        "bash", str(GATE), "dispatch",
        "--task-id", "20260809-GOVB1-B4-PROBE-N1",
        "--risk", "low", "--intent", "probe",
        "--facts-asked", "probe", "--review-role", "probe",
        "--template", "n/a:probe",
    ])
    assert proc.returncode != 0, "缺 --brief 應拒發 token\n" + _out(proc)
    assert "--brief" in (proc.stdout + proc.stderr), (
        "拒發須歸因於 --brief（否則證明不了是 (d) 擋的）\n" + _out(proc)
    )


def test_d_block_present_and_unconditional() -> None:
    """(d) 之守衛須為**無條件**（所有 dispatch），非只在某類派工才檢查。

    mutation 契約：把 `if [ -z "${brief}" ]` 改成任何帶前提之條件 ⇒ 本測轉紅。
    """
    src = GATE.read_text(encoding="utf-8")
    assert re.search(r'\n  if \[ -z "\$\{brief\}" \]; then\n    miss brief ', src), (
        "(d) 守衛須為無條件 `if [ -z \"${brief}\" ]; then miss brief`"
    )


def test_committee_run_still_dispatchable_under_d() -> None:
    """🔴 **反向風險**：(d) 落地後主委仍須派得出工，否則無人能修 B4（`票 B-45` 同型）。

    `committee_run.sh` 必須無條件 append `--brief`；移除該行 ⇒ 所有派工被 (d) 擋死。
    """
    src = COMMITTEE_RUN.read_text(encoding="utf-8")
    assert 'gate_args+=(--brief "${brief}")' in src, (
        "committee_run 必須 append --brief，否則 (d) 落地後主委派不出任何工"
    )
