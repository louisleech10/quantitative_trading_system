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
    """cx_run.sh 共變面：**Task 1.3 的**改動僅允許 `_LIFECYCLE_EMBED_B64` 行。

    🔴 斷言範圍已由「相對 HEAD 的全部 diff」收窄為「非 Task 4.3 授權範圍的 diff」
    〔`20260810-GOVB1-B10-REVIEW-R1` 必答 1，codex＋composer 兩家裁 **(A)** 核准〕。

    原因：`docs/GOVB1_INPUT_QUALITY_TODO.md` 的 **Task 4.3 修改檔案欄明文授權改
    `scripts/cx_run.sh`**（改寫 `_run_format_check_if_needed()`、新增 `_emit_fixup_list()`），
    與本測原本的「只准動 embed 行」**字面互斥**：不改測試 ⇒ 全套永紅；
    不改 `cx_run.sh` ⇒ Task 4.3 無交付。

    🔴 **收窄不等於放行**：本測仍擋住「非授權」的改動——
    判準＝改動必須落在 Task 4.3 具名交付的函式內，或是 embed 行。
    〔委員原話：「不得為綠而刪 Task 4.3 交付」〕
    """
    proc = _run(["git", "diff", "HEAD", "--", str(CX_RUN.relative_to(REPO))])
    assert proc.returncode == 0
    diff = proc.stdout or ""
    if not diff.strip():
        return  # 已 commit 或無差
    # Task 4.3 具名授權的識別字（出自 TODO 修改檔案欄與其實作要點）
    task43_markers = (
        "_emit_fixup_list",
        "_check_findings_destination",
        "_run_format_check_if_needed",
        "_dest_snap",
        "preserve)",
        "Task 4.3",
        "B8 C5",
        "B9 C5",
    )
    # 🔴 以 **hunk** 為判斷單位，不以「行」。授權函式**內部**的行本來就不帶識別字，
    #   逐行判會把合法交付判成違規（主委實測撞到）。
    hunks: list[list[str]] = []
    for ln in diff.splitlines():
        if ln.startswith("@@"):
            hunks.append([])
        elif hunks:
            hunks[-1].append(ln)
    for hunk in hunks:
        changed = [
            ln for ln in hunk
            if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))
        ]
        if not changed:
            continue
        blob = "\n".join(hunk)  # 含 context 行，故授權函式名找得到
        if "_LIFECYCLE_EMBED_B64" in blob:
            continue
        if any(m in blob for m in task43_markers):
            continue
        raise AssertionError(
            "cx_run 有**非 Task 4.3 授權**的 hunk 被改:\n" + "\n".join(changed[:6])
        )


# ── gate --brief 掛點 ────────────────────────────────────────────────


def _gate_env(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir(parents=True, exist_ok=True)
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


def test_stage2_enables_d_fail_closed() -> None:
    """階段 2 已啟 (d)：impl(--spec) 缺 --brief 時 gate 須 miss brief。

    🔴 本測**取代**原 `test_stage1_does_not_enable_d_fail_closed`（反斷言封條）。
    出處＝`handoffs/reconcile/20260810-govb1-b4-consult-r1/synth.md` 群集 5：
    codex 指出「階段 1 封條達成後若保留原反斷言，等於把已完成的目標寫成禁止」。
    """
    src = GATE.read_text(encoding="utf-8")
    hit = re.search(
        r'\[ -n "\$\{spec\}" \].*\[ -z "\$\{brief\}" \].*miss brief',
        src,
        re.S,
    )
    assert hit is not None, "階段 2 應含 (d) miss brief 邏輯"


# ── Task 1.3 (d) 階段 2：impl 派工之 brief 綁定 ─────────────────────
#
# 裁決＝handoffs/reconcile/20260810-govb1-b4-consult-r1/synth.md（codex+composer APPROVED）。
# 兩層各有正／負用例 ＋ mutation；`--only impl-kind` 為單一 kind parser 之下游。

_D_SPEC = REPO / "docs" / "GOVB1_INPUT_QUALITY_SPEC.md"
_D_RECONCILE = REPO / "handoffs" / "reconcile" / "20260807-govb1-x-stamp-r4" / "synth.md"


def _dispatch_impl(brief: Path | None) -> list[str]:
    """T-1.3-N1 之逐字形態：帶 --spec / --reconcile；brief 可缺。"""
    cmd = [
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
        "n/a:d-hook-probe",
        "--spec",
        str(_D_SPEC),
        "--reconcile",
        str(_D_RECONCILE),
    ]
    if brief is not None:
        cmd.extend(["--brief", str(brief)])
    return cmd


def _d_env(tmp_path: Path) -> dict[str, str]:
    """(d) 之單元隔離環境。

    🔴 以 harness override 把 completeness／stamp 兩閘換成 no-op：
    本組測的是 **(d) 自身**，不該因某份 reconcile 的戳記健康度而綠或紅
    ——那正是本次把 (d) 移到 completeness 之前所要杜絕的耦合。
    兩個 override 於 `gate.sh:43-50` 對非 harness 路徑 fail-closed，非旁路。
    """
    env = _gate_env(tmp_path)
    stub = tmp_path / "true_stub.sh"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    env["COMPLETENESS_CHECK_OVERRIDE"] = str(stub)
    env["RECONCILE_STAMPS_CHECK_OVERRIDE"] = str(stub)
    return env


def test_t13_n1_impl_without_brief_rejected(tmp_path: Path) -> None:
    """T-1.3-N1（負向＋歸因）：`--spec` 缺 `--brief` ⇒ rc≠0 且輸出具名 `--brief`。

    🔴 歸因不可只斷 rc≠0——未知參數／缺必填欄同樣非零，會讓掛點沒跑也算通過。
    """
    proc = _run(_dispatch_impl(None), env=_d_env(tmp_path))
    assert proc.returncode != 0, _out(proc)
    assert "--brief" in _out(proc), _out(proc)
    assert "T-1.3-N1" in _out(proc), _out(proc)


def test_t13_n1_impl_without_brief_mints_no_token(tmp_path: Path) -> None:
    """行為層：缺 brief 不得留下 dispatch.token。"""
    env = _d_env(tmp_path)
    _run(_dispatch_impl(None), env=env)
    assert not (Path(env["GATE_DIR_OVERRIDE"]) / "dispatch.token").exists()


def test_t13_d_impl_with_valid_impl_brief_accepted(tmp_path: Path) -> None:
    """正向：`--spec` ＋ 合規 impl brief ⇒ rc=0 且發 token（證明 (d) 不是恆拒）。"""
    env = _d_env(tmp_path)
    proc = _run(
        _dispatch_impl(FIXTURE / "brief_impl_delta_present.md"), env=env
    )
    assert proc.returncode == 0, _out(proc)
    assert (Path(env["GATE_DIR_OVERRIDE"]) / "dispatch.token").is_file(), _out(proc)


def test_t13_d_impl_with_non_impl_brief_rejected(tmp_path: Path) -> None:
    """`CODEX-R1-P0-01` 之反例：`--spec` ＋ 合法 consult brief ⇒ 須拒（原本 rc=0 且發 token）。"""
    proc = _run(
        _dispatch_impl(FIXTURE / "brief_consult_ok.md"), env=_d_env(tmp_path)
    )
    assert proc.returncode != 0, _out(proc)
    assert "brief-kind" in _out(proc), _out(proc)


def test_t13_d_impl_with_non_impl_brief_mints_no_token(tmp_path: Path) -> None:
    """行為層：上述反例不得留下 dispatch.token（rc≠0 但仍發 token＝假閉合）。"""
    env = _d_env(tmp_path)
    _run(_dispatch_impl(FIXTURE / "brief_consult_ok.md"), env=env)
    gate_dir = Path(env["GATE_DIR_OVERRIDE"])
    assert not (gate_dir / "dispatch.token").exists(), (
        f"kind 錯配仍發 token：{list(gate_dir.iterdir())}"
    )


def test_only_impl_kind_rejects_each_non_impl_kind(tmp_path: Path) -> None:
    """封閉集合負向：**每一種**非 impl kind 皆須被 `--only impl-kind` 拒。

    kind 集合非手抄——由 `scripts/govflow_lifecycle.json` 之 `kinds` 導出，
    減去 `impl`。新增 kind 而未覆蓋時本測自動涵蓋。
    """
    kinds = set(json.loads(LIFECYCLE.read_text(encoding="utf-8"))["kinds"]) - {"impl"}
    assert kinds, "lifecycle kinds 解析為空"
    for kind in sorted(kinds):
        brief = tmp_path / f"brief_{kind}.md"
        body = f"brief-kind: {kind}\n"
        if kind == "stamp":
            body += "\nstamp-target: handoffs/x.md\n"
        brief.write_text(body + "\nstub\n", encoding="utf-8")
        proc = _run(["bash", str(BRIEF_CONF), "--only", "impl-kind", str(brief)])
        assert proc.returncode != 0, f"kind={kind} 應被拒: {_out(proc)}"
        assert kind in _out(proc), f"kind={kind} 訊息未具名: {_out(proc)}"


def test_only_impl_kind_accepts_impl() -> None:
    proc = _run(
        [
            "bash",
            str(BRIEF_CONF),
            "--only",
            "impl-kind",
            str(FIXTURE / "brief_impl_delta_present.md"),
        ]
    )
    assert proc.returncode == 0, _out(proc)


def _mutated_gate(tmp_path: Path, anchor: str, repl: str) -> Path:
    """複製 gate.sh 並就地替換 anchor；錨點失配即 fail-closed 轉紅。"""
    src = GATE.read_text(encoding="utf-8")
    assert anchor in src, f"mutation 錨點失配（實作改寫後須同步）: {anchor[:60]!r}"
    mut = src.replace(anchor, repl, 1)
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    gate_mut = scripts / "gate.sh"
    gate_mut.write_text(
        mut.replace(
            'SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"',
            f'SCRIPT_DIR="{REPO / "scripts"}"',
            1,
        ),
        encoding="utf-8",
    )
    gate_mut.chmod(0o755)
    return gate_mut


def _run_with_gate(
    gate_path: Path, brief: Path | None, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    cmd = _dispatch_impl(brief)
    cmd[1] = str(gate_path)
    return _run(cmd, env=env, cwd=str(REPO))


def test_mutation_d_remove_miss_brief_turns_green(tmp_path: Path) -> None:
    """mutation：移除 (d) 第①層 ⇒ 缺 brief 的 impl 派工由紅轉綠。

    移除後仍紅 ⇒ 寫的是恆真檢查（不算完成）。
    """
    mut_gate = _mutated_gate(
        tmp_path,
        '      miss brief "impl 派工(--spec)一律須顯式 --brief（T-1.3-N1：掛點不得空轉）"',
        "      :  # MUTATION: drop (d) layer 1",
    )
    proc = _run_with_gate(mut_gate, None, _d_env(tmp_path / "env1"))
    assert proc.returncode == 0, (
        "移除 miss brief 後應轉綠（否則錨點失準或檢查恆真）\n" + _out(proc)
    )


def test_mutation_d_remove_kind_binding_turns_green(tmp_path: Path) -> None:
    """mutation：移除 (d) 第②層 ⇒ `--spec` ＋ consult brief 由紅轉綠（＝`CODEX-R1-P0-01` 復發）。"""
    mut_gate = _mutated_gate(
        tmp_path,
        '      bash "${SCRIPT_DIR}/brief_conformance_check.sh" --only impl-kind "${brief}" \\\n',
        "      true \\\n",
    )
    proc = _run_with_gate(
        mut_gate, FIXTURE / "brief_consult_ok.md", _d_env(tmp_path / "env2")
    )
    assert proc.returncode == 0, (
        "移除 kind binding 後應轉綠（否則錨點失準）\n" + _out(proc)
    )


# ── review-r1 findings 之修法驗收 ────────────────────────────────────
#
# 出處：handoffs/reconcile/20260810-govb1-b4-review-r1/synth.md（三條全 ACCEPT）
#   群集 1 `CODEX-R1-P1-01`：`--spec ""` 顯式空值 fail-open（P1，BLOCKING）
#   群集 2 `CODEX-R1-P2-02`：fence 內 `brief-kind:` 被採信


def _dispatch_specless(extra: list[str]) -> list[str]:
    """不含 `--spec` 之最小 dispatch；`extra` 供各測附加旗標。"""
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
        "n/a:spec-value-probe",
        *extra,
    ]


def _no_token(env: dict[str, str]) -> bool:
    return not (Path(env["GATE_DIR_OVERRIDE"]) / "dispatch.token").exists()


def test_p1_01_empty_spec_rejected_and_mints_no_token(tmp_path: Path) -> None:
    """`CODEX-R1-P1-01` 反例：`--spec ""` ⇒ rc≠0、具名 `--spec`、且**不得**留下 token。"""
    env = _d_env(tmp_path)
    proc = _run(_dispatch_specless(["--spec", ""]), env=env)
    assert proc.returncode != 0, _out(proc)
    assert "--spec" in _out(proc), _out(proc)
    assert _no_token(env), "空 --spec 仍發 token"


def test_p1_01_whitespace_spec_rejected_and_mints_no_token(tmp_path: Path) -> None:
    """全空白值同樣拒（不得只擋純空字串）。"""
    env = _d_env(tmp_path)
    proc = _run(_dispatch_specless(["--spec", "   "]), env=env)
    assert proc.returncode != 0, _out(proc)
    assert _no_token(env), "全空白 --spec 仍發 token"


def test_p1_01_duplicate_spec_rejected(tmp_path: Path) -> None:
    """`--spec <有效> --spec ""` 之 last-wins 抹除 ⇒ 拒（重複給值本身即拒）。"""
    env = _d_env(tmp_path)
    proc = _run(
        _dispatch_specless(["--spec", str(_D_SPEC), "--spec", ""]), env=env
    )
    assert proc.returncode != 0, _out(proc)
    assert "重複" in _out(proc), _out(proc)
    assert _no_token(env), "重複 --spec 仍發 token"


def test_p1_01_no_spec_flag_unchanged(tmp_path: Path) -> None:
    """回歸護欄：**完全不給** `--spec`（非 impl 派工）行為逐字不變 ⇒ rc=0 且發 token。

    缺這條的話，上面三條可以用「一律拒 --spec」這種過寬修法騙過去。
    """
    env = _d_env(tmp_path)
    proc = _run(_dispatch_specless([]), env=env)
    assert proc.returncode == 0, _out(proc)
    assert not _no_token(env), _out(proc)


def test_p2_02_fenced_only_kind_not_trusted() -> None:
    """`CODEX-R1-P2-02` 反例：只有 fence 內寫 `brief-kind: impl` ⇒ 判為缺宣告而拒。"""
    proc = _run(
        [
            "bash",
            str(BRIEF_CONF),
            "--only",
            "impl-kind",
            str(FIXTURE / "brief_fenced_kind_only.md"),
        ]
    )
    assert proc.returncode != 0, _out(proc)
    assert "缺 'brief-kind:' 宣告" in _out(proc), _out(proc)


def test_p2_02_fenced_impl_does_not_shadow_real_consult() -> None:
    """真實宣告 consult ＋ fence 內 impl ⇒ 解析為 consult 而被 impl-kind 拒。

    🔴 同時證明**未**因排除 fence 而誤觸「多個不一致宣告」之歧義 fail-closed
    （訊息須是 kind 不符，不是「多個宣告」）。
    """
    proc = _run(
        [
            "bash",
            str(BRIEF_CONF),
            "--only",
            "impl-kind",
            str(FIXTURE / "brief_consult_with_fenced_impl.md"),
        ]
    )
    assert proc.returncode != 0, _out(proc)
    assert "consult" in _out(proc), _out(proc)
    assert "多個" not in _out(proc), "誤判為多宣告歧義：\n" + _out(proc)


def test_p2_02_fenced_brief_still_passes_full_path() -> None:
    """回歸護欄：帶 fence 之合法 consult brief 走 full path 仍 rc=0（未因修法誤擋）。"""
    proc = _run(
        ["bash", str(BRIEF_CONF), str(FIXTURE / "brief_consult_with_fenced_impl.md")]
    )
    assert proc.returncode == 0, _out(proc)


def test_mutation_p1_01_remove_empty_spec_guard_turns_green(tmp_path: Path) -> None:
    """mutation：移除空值守衛 ⇒ `--spec ""` 由紅轉綠且**發出 token**（＝原缺陷復發）。"""
    mut_gate = _mutated_gate(
        tmp_path,
        "      *[![:space:]]*) : ;;",
        "      *) : ;;  # MUTATION: accept any spec value",
    )
    env = _d_env(tmp_path / "envm1")
    cmd = _dispatch_specless(["--spec", ""])
    cmd[1] = str(mut_gate)
    proc = _run(cmd, env=env, cwd=str(REPO))
    assert proc.returncode == 0, "移除空值守衛後應轉綠\n" + _out(proc)
    assert not _no_token(env), "缺陷復發時應發出 token（否則本 mutation 沒測到東西）"


def test_p1_01_empty_spec_with_consult_brief_rejected(tmp_path: Path) -> None:
    """`CODEX-R1-P1-01` 探針 2：`--spec "" --brief <consult>` ⇒ 拒且無 token。

    composer 於 r2 以碼證推理「與探針 1 同路徑」；本測把該推理變成機械保證。
    """
    env = _d_env(tmp_path)
    proc = _run(
        _dispatch_specless(
            ["--spec", "", "--brief", str(FIXTURE / "brief_consult_ok.md")]
        ),
        env=env,
    )
    assert proc.returncode != 0, _out(proc)
    assert _no_token(env), "空 --spec ＋ consult brief 仍發 token"


# ── `CODEX-R2-P1-01`：fence 修法自身引入之回歸 ─────────────────────


def test_r2_p1_01_unclosed_fence_rejected() -> None:
    """未閉合 fence ⇒ 宣告範圍無法判定 ⇒ fail-closed（不得只剩 fence 前的宣告）。"""
    proc = _run(
        [
            "bash",
            str(BRIEF_CONF),
            "--only",
            "impl-kind",
            str(FIXTURE / "brief_unclosed_fence_conflict.md"),
        ]
    )
    assert proc.returncode != 0, _out(proc)
    assert "未閉合" in _out(proc), _out(proc)


def test_r2_p1_01_unclosed_fence_mints_no_token(tmp_path: Path) -> None:
    """行為層：該 malformed brief 走完整 gate 不得發 token（codex 原反例即此）。"""
    env = _d_env(tmp_path)
    _run(
        _dispatch_impl(FIXTURE / "brief_unclosed_fence_conflict.md"), env=env
    )
    assert _no_token(env), "未閉合 fence 之 malformed brief 仍發 token"


def test_r2_p1_01_matches_pre_fence_behaviour() -> None:
    """回歸方向確認：本 fixture 在 fence 修法**之前**即為 rc≠0（多宣告歧義）。

    🔴 意義：證明修法沒有把一條原本 fail-closed 的路徑放行——那才是 `CODEX-R2-P1-01`
    的本質（新引入的回歸），不是「本來就沒擋」。
    """
    old = subprocess.run(
        ["git", "show", "ba5489ba:scripts/brief_conformance_check.sh"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if old.returncode != 0:
        pytest.skip("ba5489ba 不可達（淺 clone？）")
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        scripts = Path(td) / "scripts"
        scripts.mkdir()
        old_bc = scripts / "brief_conformance_check.sh"
        old_bc.write_text(old.stdout, encoding="utf-8")
        old_bc.chmod(0o755)
        shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
        proc = _run(
            [
                "bash",
                str(old_bc),
                "--only",
                "impl-kind",
                str(FIXTURE / "brief_unclosed_fence_conflict.md"),
            ],
            cwd=td,
        )
    assert proc.returncode != 0, (
        "舊版對本 fixture 應已 fail-closed；若舊版就放行，本 finding 就不是回歸\n"
        + _out(proc)
    )


def test_mutation_r2_p1_01_remove_eof_guard_turns_green(tmp_path: Path) -> None:
    """mutation：拿掉 EOF `infence` 守衛 ⇒ 未閉合 fence fixture 由紅轉綠（回歸復發）。"""
    src = BRIEF_CONF.read_text(encoding="utf-8")
    anchor = "    END { if (infence) exit 3 }"
    assert anchor in src, "mutation 錨點失配（EOF 守衛改寫後須同步）"
    mut = src.replace(anchor, "    END { }", 1)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    bc_mut = scripts / "brief_conformance_check.sh"
    bc_mut.write_text(mut, encoding="utf-8")
    bc_mut.chmod(0o755)
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    proc = _run(
        [
            "bash",
            str(bc_mut),
            "--only",
            "impl-kind",
            str(FIXTURE / "brief_unclosed_fence_conflict.md"),
        ],
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, (
        "移除 EOF 守衛後應假綠（證明守衛非恆真）\n" + _out(proc)
    )


def test_mutation_p2_02_remove_fence_exclusion_turns_green(tmp_path: Path) -> None:
    """mutation：拿掉 kind 解析的 fence 排除 ⇒ fence-only fixture 由紅轉綠。"""
    src = BRIEF_CONF.read_text(encoding="utf-8")
    anchor = '  brief="${_bk_fence_tmp}"'
    assert anchor in src, "mutation 錨點失配（fence 排除實作改寫後須同步）"
    mut = src.replace(anchor, '  :  # MUTATION: do not swap in fence-stripped file', 1)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    bc_mut = scripts / "brief_conformance_check.sh"
    bc_mut.write_text(mut, encoding="utf-8")
    bc_mut.chmod(0o755)
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    proc = _run(
        [
            "bash",
            str(bc_mut),
            "--only",
            "impl-kind",
            str(FIXTURE / "brief_fenced_kind_only.md"),
        ],
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, (
        "移除 fence 排除後 fence-only 應假綠（證明排除非恆真）\n" + _out(proc)
    )
