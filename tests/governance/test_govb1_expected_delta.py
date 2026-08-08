"""GOVB1 Task 1.3 — EXPECTED-DELTA: 宣告閘（票 B-29）。

階段 1 覆蓋：空區塊修正、--only、gate --brief+(c)、committee_run (e)、
lifecycle expected_delta 節＋embed、superset 超集（見 lifecycle_matrix）。
階段 2 (d) fail-closed 不在本檔（主委實測後另 commit）。
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
    # 錨定：剔除標題後再 grep 非空白的管道（整段換成 true ⇒ if ! true 永不進錯誤支）
    anchor = (
        "      | grep -vxF 'EXPECTED-DELTA:' \\\n"
        "      | grep -qE '[^[:space:]]'; then"
    )
    mut = src.replace(anchor, "      | true; then", 1)
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
    proc = _run(["jq", "-r", "keys[]", str(LIFECYCLE)])
    assert proc.returncode == 0, proc.stderr
    keys = sorted(ln.strip() for ln in proc.stdout.splitlines() if ln.strip())
    assert keys == ["_doc", "expected_delta", "kinds", "stages"], keys


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


def test_stage1_does_not_enable_d_fail_closed() -> None:
    """階段 1 禁啟 (d)：缺 --brief 的 impl(--spec) 不得因 brief 被 miss。"""
    src = GATE.read_text(encoding="utf-8")
    # (d) 特徵：spec 非空且 brief 空時 miss brief
    banned = re.search(
        r'\[ -n "\$\{spec\}" \].*\[ -z "\$\{brief\}" \].*miss brief',
        src,
        re.S,
    )
    assert banned is None, "階段 1 不應含 (d) miss brief 邏輯"
