"""P1-6 B5 Task 3.1：gate.sh 債務閘 + gate_check 重查。

驗收對齊 SPEC Task 3.1 驗證段 + 邊界。
hermetic：完整置換 env；探針變異用隔離副本，不直接改 repo 內 scripts/。
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from tests.governance import _debt_probe_helper as helper

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
GATE_CHECK_SH = REPO_ROOT / "scripts" / "gate_check.sh"
LEDGER_SH = REPO_ROOT / "scripts" / "debt_ledger.sh"
APPEND_SH = REPO_ROOT / "scripts" / "audit_append.sh"
SPEC = REPO_ROOT / "docs" / "CONVERGENCE_METHOD_SPEC.md"


def _base_env(audit: Path, gate_dir: Path, **extra: str) -> dict[str, str]:
    """完整置換 env（不繼承 parent ambient 鍵，含 ROUND_ID / DEBT_*）。"""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C"),
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
        "GATE_DIR_OVERRIDE": str(gate_dir),
    }
    env.update(extra)
    return env


def _setup_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """隔離 repo：scripts 副本 + 空 debt audit + 空 gate_dir。"""
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in (
        "gate.sh",
        "gate_check.sh",
        "debt_ledger.sh",
        "_debt_ledger_core.py",
        "audit_append.sh",
        "audit_events.json",
        "governance_families.sh",
        "governance_families.json",
        "template_check.sh",
        "coverage_check.sh",
        "completeness_check.sh",
        "reconcile_stamps_check.sh",
        "review_quorum_check.sh",
        "verify_task_provenance.py",
    ):
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
            if name.endswith(".sh"):
                (scripts / name).chmod(0o755)
    # gate.sh 啟動時 source families；路徑相對 SCRIPT_DIR
    audit = root / ".claude" / "gate" / "audit.log"
    audit.parent.mkdir(parents=True)
    audit.write_text("", encoding="utf-8")
    gate_dir = tmp_path / "gate_dir"
    gate_dir.mkdir()
    # 連結 python / 可選 venv 不強制；用系統 python3
    return root, audit, gate_dir


def _append(root: Path, audit: Path, *args: str) -> None:
    env = _base_env(audit, audit.parent)
    r = helper.run_cmd(
        root / "scripts" / "audit_append.sh",
        *args,
        env=env,
        cwd=root,
    )
    assert r.returncode == 0, f"append fail rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"


def _open_debt(
    root: Path,
    audit: Path,
    *,
    round_id: str,
    session: str,
    participants: list[str] | None = None,
) -> None:
    parts = participants or ["codex"]
    outs = {f: f"handoffs/out-{f}.md" for f in parts}
    _append(
        root,
        audit,
        "--require-absent-session",
        session,
        "--event",
        "committee_round_open",
        "--field",
        f"round_id={round_id}",
        "--field",
        "task_id=t-debt-gate",
        "--field",
        "brief_path=handoffs/brief.md",
        "--field",
        "brief_sha256=" + ("a" * 64),
        "--field",
        "brief_sha256_norm=" + ("b" * 64),
        "--field",
        "lock_mode=discovery",
        "--field",
        f"participants=@{json.dumps(parts, ensure_ascii=False)}",
        "--field",
        f"expected_outputs=@{json.dumps(outs, ensure_ascii=False)}",
        "--field",
        f"session_name={session}",
        "--field",
        "actor=test",
        "--field",
        "origin_script=committee_run.sh",
    )


def _clear_debt(root: Path, audit: Path, *, round_id: str, session: str) -> None:
    _append(
        root,
        audit,
        "--event",
        "committee_debt_clear",
        "--field",
        f"round_id={round_id}",
        "--field",
        f"session_id={session}",
        "--field",
        "lock_sha256=" + ("d" * 64),
        "--field",
        "synth_sha256=" + ("e" * 64),
        "--field",
        'roster=@["codex"]',
        "--field",
        "completeness_rc=0",
        "--field",
        "actor=test",
        "--field",
        "origin_script=debt_clear.sh",
    )


def _dispatch_low(
    root: Path,
    audit: Path,
    gate_dir: Path,
    *,
    extra_env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
    gate_script: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = _base_env(audit, gate_dir)
    if extra_env:
        env.update(extra_env)
    cmd = [
        "bash",
        str(gate_script or (root / "scripts" / "gate.sh")),
        "dispatch",
        "--intent",
        "debt-gate unit",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit-test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:debt-gate unit",
        "--task-id",
        f"debt-gate-{uuid.uuid4().hex[:8]}",
        "--output",
        "handoffs/debt-gate-unit.md",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _token_mtime(gate_dir: Path, kind: str = "dispatch") -> float | None:
    p = gate_dir / f"{kind}.token"
    if not p.is_file():
        return None
    return p.stat().st_mtime


# ── SPEC 驗證段 ──────────────────────────────────────────


def test_open_debt_blocks_new_round(tmp_path: Path) -> None:
    """有 OPEN 債時開新輪 → rc≠0 且 token mtime 未變。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    _open_debt(root, audit, round_id=rid, session="s-open-1")
    # 預置 token，確認 mtime 不變
    token = gate_dir / "dispatch.token"
    token.write_text("preexisting\n", encoding="utf-8")
    before = token.stat().st_mtime
    time.sleep(0.05)
    r = _dispatch_low(root, audit, gate_dir)
    assert r.returncode != 0, f"OPEN 債應拒發; out={r.stdout!r} err={r.stderr!r}"
    combined = (r.stdout or "") + (r.stderr or "")
    assert "OPEN" in combined or "未清" in combined or "債" in combined, combined
    after = token.stat().st_mtime
    assert after == before, "拒發時不得改寫 token mtime"
    assert token.read_text(encoding="utf-8") == "preexisting\n"


def test_open_debt_blocks_impl_dispatch(tmp_path: Path) -> None:
    """有 OPEN 債時實作派工（帶 --spec）→ 也 rc≠0（使用者裁決 3）。"""
    if not SPEC.is_file():
        pytest.skip("SPEC missing")
    root, audit, gate_dir = _setup_repo(tmp_path)
    # 真 SPEC 路徑：gate 以 cwd=root 跑，需能讀到 SPEC
    # 用絕對路徑 --spec
    rid = str(uuid.uuid4())
    _open_debt(root, audit, round_id=rid, session="s-impl")
    r = _dispatch_low(
        root,
        audit,
        gate_dir,
        extra_args=["--spec", str(SPEC)],
    )
    assert r.returncode != 0, f"OPEN+--spec 應拒; out={r.stdout!r} err={r.stderr!r}"
    combined = (r.stdout or "") + (r.stderr or "")
    # 須在 completeness/reconcile 之前被債務閘擋（不得只因缺 reconcile 拒）
    assert "債" in combined or "OPEN" in combined or "debt" in combined.lower(), combined


def test_clear_then_dispatch_passes(tmp_path: Path) -> None:
    """債清後 → rc=0。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    sess = "s-clear"
    _open_debt(root, audit, round_id=rid, session=sess)
    _clear_debt(root, audit, round_id=rid, session=sess)
    h = helper.run_cmd(
        root / "scripts" / "debt_ledger.sh",
        "--has-open",
        env=_base_env(audit, gate_dir),
        cwd=root,
    )
    assert h.returncode == 0, h.stderr
    r = _dispatch_low(root, audit, gate_dir)
    assert r.returncode == 0, f"債清應放行; out={r.stdout!r} err={r.stderr!r}"
    assert "GATE PASS" in (r.stdout or "")
    assert (gate_dir / "dispatch.token").is_file()


def test_gate_dir_override_cannot_hide_debt(tmp_path: Path) -> None:
    """GATE_DIR_OVERRIDE 指向空目錄但真 audit 有債 → 仍 rc≠0。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    rid = str(uuid.uuid4())
    _open_debt(root, audit, round_id=rid, session="s-hide")
    empty_gate = tmp_path / "empty_gate"
    empty_gate.mkdir()
    # 關鍵：DEBT_AUDIT_OVERRIDE 仍指向有債 audit；GATE_DIR 換空目錄不得藏債
    r = _dispatch_low(root, audit, empty_gate)
    assert r.returncode != 0, f"GATE_DIR 空不得藏債; out={r.stdout!r} err={r.stderr!r}"
    assert not (empty_gate / "dispatch.token").is_file() or (
        (empty_gate / "dispatch.token").read_text(encoding="utf-8").strip() == ""
    )


def test_debt_audit_override_requires_harness(tmp_path: Path) -> None:
    """DEBT_AUDIT_OVERRIDE 未帶 harness → rc≠0。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    # 無債 audit，但未綁 harness 的 override 本身須 fail-closed
    env = _base_env(audit, gate_dir)
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    # 保留 DEBT_AUDIT_OVERRIDE
    r = subprocess.run(
        [
            "bash",
            str(root / "scripts" / "gate.sh"),
            "dispatch",
            "--intent",
            "x",
            "--risk",
            "low",
            "--facts-asked",
            "none-needed:t",
            "--review-role",
            "single-executor:n/a",
            "--template",
            "n/a:t",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert r.returncode != 0, f"無 harness override 應拒; out={r.stdout!r} err={r.stderr!r}"
    combined = (r.stdout or "") + (r.stderr or "")
    assert (
        "GOVERNANCE_TEST_HARNESS" in combined
        or "DEBT_AUDIT_OVERRIDE" in combined
        or "fail-closed" in combined
        or "不可信" in combined
        or "債" in combined
    ), combined


def test_debt_ledger_missing_fail_closed(tmp_path: Path) -> None:
    """debt_ledger.sh 改名/缺失 → rc≠0（fail-closed）。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    ledger = root / "scripts" / "debt_ledger.sh"
    assert ledger.is_file()
    ledger.rename(root / "scripts" / "debt_ledger.sh.bak")
    r = _dispatch_low(root, audit, gate_dir)
    assert r.returncode != 0, f"缺 debt_ledger 應拒; out={r.stdout!r} err={r.stderr!r}"
    combined = (r.stdout or "") + (r.stderr or "")
    assert "debt_ledger" in combined or "缺失" in combined, combined


def test_multiple_open_debts_all_listed(tmp_path: Path) -> None:
    """多筆 open 債 → 全部列出，任一未清即拒。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    r1, r2 = str(uuid.uuid4()), str(uuid.uuid4())
    _open_debt(root, audit, round_id=r1, session="s-m1")
    _open_debt(root, audit, round_id=r2, session="s-m2")
    r = _dispatch_low(root, audit, gate_dir)
    assert r.returncode != 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert r1 in combined, f"須列出 round1: {combined!r}"
    assert r2 in combined, f"須列出 round2: {combined!r}"


def test_empty_audit_allows_dispatch(tmp_path: Path) -> None:
    """空 audit ＝無債，放行。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    assert audit.read_text(encoding="utf-8") == ""
    r = _dispatch_low(root, audit, gate_dir)
    assert r.returncode == 0, f"空 audit 應放行; out={r.stdout!r} err={r.stderr!r}"
    assert "GATE PASS" in (r.stdout or "")


def test_fresh_token_rechecks_ledger(tmp_path: Path) -> None:
    """gate_check：fresh token 時重查帳本；有 OPEN → exit 2。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    # 先無債發 token
    r = _dispatch_low(root, audit, gate_dir)
    assert r.returncode == 0, r.stderr
    assert (gate_dir / "dispatch.token").is_file()
    # 無債時 gate_check 放行
    env_ok = _base_env(audit, gate_dir)
    chk = subprocess.run(
        ["bash", str(root / "scripts" / "gate_check.sh")],
        input='{"tool_name":"Task","tool_input":{}}',
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env_ok,
    )
    assert chk.returncode == 0, f"無債 fresh 應放行; err={chk.stderr!r}"
    # 寫入 OPEN 債後，同 token 應被重查擋下（無 sidecar 快取；每次直查 ledger）
    _open_debt(root, audit, round_id=str(uuid.uuid4()), session="s-recheck")
    chk2 = subprocess.run(
        ["bash", str(root / "scripts" / "gate_check.sh")],
        input='{"tool_name":"Task","tool_input":{}}',
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env_ok,
    )
    assert chk2.returncode == 2, (
        f"OPEN 後 fresh token 重查應 exit 2; rc={chk2.returncode} err={chk2.stderr!r}"
    )
    assert "債" in (chk2.stderr or "") or "open_debt" in (chk2.stderr or "") or "OPEN" in (
        chk2.stderr or ""
    )


def test_gate_sh_enforces_debt_without_hook(tmp_path: Path) -> None:
    """只靠 gate.sh 本體（不經 gate_check）也擋 OPEN 債。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    _open_debt(root, audit, round_id=str(uuid.uuid4()), session="s-nohook")
    # 直接呼叫 gate.sh，不經 gate_check
    r = _dispatch_low(root, audit, gate_dir)
    assert r.returncode != 0
    assert not (gate_dir / "dispatch.token").is_file() or "GATE PASS" not in (r.stdout or "")


def test_gate_check_latency_under_100ms(tmp_path: Path) -> None:
    """單次 gate_check cold < 100ms（SPEC 字面；真實規模 audit 實測）。

    不得只量 warm／不得放寬 cold 門檻。無 sidecar 快取；cold＝每次直查 ledger。
    使用真實 audit 副本（若存在）以反映 prod 行數；否則以空 audit 仍 assert cold<100。
    """
    root, audit, gate_dir = _setup_repo(tmp_path)
    real_audit = REPO_ROOT / ".claude" / "gate" / "audit.log"
    real_lines = 0
    real_bytes = 0
    # 真實規模副本 + 未來 cutoff → 全檔仍掃描（序號/解析成本）但無 OPEN，
    # 避免 deny 追加 I/O 污染 latency；語意仍是 cold 全量 recheck。
    if real_audit.is_file():
        raw = real_audit.read_bytes()
        real_bytes = len(raw)
        real_lines = raw.count(b"\n") + (0 if raw.endswith(b"\n") or not raw else 1)
        audit.write_bytes(raw)
    (gate_dir / "dispatch.token").write_text("ts=test\nkind=dispatch\n", encoding="utf-8")
    env = _base_env(
        audit, gate_dir, DEBT_CUTOFF_OVERRIDE="2099-01-01T00:00:00Z"
    )

    def _once() -> tuple[int, float]:
        t0 = time.perf_counter()
        p = subprocess.run(
            ["bash", str(root / "scripts" / "gate_check.sh")],
            input='{"tool_name":"Task","tool_input":{}}',
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        dt = (time.perf_counter() - t0) * 1000.0
        return p.returncode, dt

    # 連續三次 cold（無快取；每次等價 cold）；取中位數抗抖
    samples: list[tuple[int, float]] = [_once() for _ in range(3)]
    ms_sorted = sorted(ms for _, ms in samples)
    ms_cold = ms_sorted[1]
    # 對應中位樣本的 rc（samples 與 ms_sorted 對齊取中位元素）
    mid_idx = sorted(range(3), key=lambda i: samples[i][1])[1]
    rc_cold = samples[mid_idx][0]
    rc2, ms2 = _once()

    receipt = (
        f"gate_check_latency receipt: cold_ms={ms_cold:.1f} second_ms={ms2:.1f} "
        f"samples_ms={[round(ms, 1) for _, ms in samples]} "
        f"real_audit_lines={real_lines} real_audit_bytes={real_bytes} "
        f"audit_bytes={audit.stat().st_size} cold_rc={rc_cold} second_rc={rc2} "
        f"cutoff_override=2099-01-01T00:00:00Z"
    )
    print(receipt)

    # SPEC：單次 gate_check < 100ms——以 cold（無快取）為準，不得放寬
    assert ms_cold < 100.0, f"cold gate_check 須 <100ms: {receipt}"
    assert ms2 < 100.0, f"second gate_check 須 <100ms: {receipt}"
    assert rc_cold == 0 and rc2 == 0, f"未來 cutoff 無債應放行: {receipt}"


def test_gate_check_cutoff_change_not_stale_allow(tmp_path: Path) -> None:
    """群集 B 回歸：改 cutoff 後不得沿用「無債」結論（原 cache key 不含 cutoff）。

    反例（修補前）：cutoff 2099 → rc=0 寫 cache；改 1970 → ledger rc=1 但 gate_check 仍 0。
    """
    root, audit, gate_dir = _setup_repo(tmp_path)
    # 寫入一筆 OPEN（ts=現在）；先用未來 cutoff 使帳本視其為 pre-cutoff → 無債
    _open_debt(root, audit, round_id=str(uuid.uuid4()), session="s-cutoff-stale")
    (gate_dir / "dispatch.token").write_text("ts=test\nkind=dispatch\n", encoding="utf-8")

    env_future = _base_env(
        audit, gate_dir, DEBT_CUTOFF_OVERRIDE="2099-01-01T00:00:00Z"
    )
    env_past = _base_env(
        audit, gate_dir, DEBT_CUTOFF_OVERRIDE="1970-01-01T00:00:00Z"
    )

    # 直接 ledger：未來 cutoff → 無債；過去 cutoff → 有債
    r_led_f = subprocess.run(
        ["bash", str(root / "scripts" / "debt_ledger.sh"), "--has-open"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env_future,
    )
    r_led_p = subprocess.run(
        ["bash", str(root / "scripts" / "debt_ledger.sh"), "--has-open"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env_past,
    )
    assert r_led_f.returncode == 0, f"未來 cutoff 應無債; rc={r_led_f.returncode} err={r_led_f.stderr!r}"
    assert r_led_p.returncode == 1, f"過去 cutoff 應有債; rc={r_led_p.returncode} err={r_led_p.stderr!r}"

    # 先以未來 cutoff 跑 gate_check（應放行）
    g1 = subprocess.run(
        ["bash", str(root / "scripts" / "gate_check.sh")],
        input='{"tool_name":"Task","tool_input":{}}',
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env_future,
    )
    assert g1.returncode == 0, f"未來 cutoff gate_check 應放行; rc={g1.returncode} err={g1.stderr!r}"

    # 只改 cutoff → 必須重算並擋下（修補前 stale allow rc=0）
    g2 = subprocess.run(
        ["bash", str(root / "scripts" / "gate_check.sh")],
        input='{"tool_name":"Task","tool_input":{}}',
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env_past,
    )
    assert g2.returncode == 2, (
        f"cutoff 變更後 gate_check 不得 stale allow; rc={g2.returncode} err={g2.stderr!r}"
    )


def test_gate_check_poisoned_sidecar_ignored(tmp_path: Path) -> None:
    """群集 C 回歸：預置 .has_open_idx 為 rc=0 不得 fail-open。

    反例（修補前）：poison `mtime size 0` → ledger rc=1 但 gate_check rc=0。
    修補後：不讀 sidecar；有 OPEN 時 gate_check 必須 exit 2。
    """
    root, audit, gate_dir = _setup_repo(tmp_path)
    _open_debt(root, audit, round_id=str(uuid.uuid4()), session="s-poison")
    (gate_dir / "dispatch.token").write_text("ts=test\nkind=dispatch\n", encoding="utf-8")
    env = _base_env(audit, gate_dir)

    # 直接 ledger 確認有債
    led = subprocess.run(
        ["bash", str(root / "scripts" / "debt_ledger.sh"), "--has-open"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert led.returncode == 1, f"應有 OPEN; rc={led.returncode} err={led.stderr!r}"

    # 預置毒化 sidecar（即使存在也必須被忽略）
    mtime = int(audit.stat().st_mtime)
    size = audit.stat().st_size
    poison = Path(str(audit) + ".has_open_idx")
    poison.write_text(f"{mtime} {size} 0\n", encoding="utf-8")

    g = subprocess.run(
        ["bash", str(root / "scripts" / "gate_check.sh")],
        input='{"tool_name":"Task","tool_input":{}}',
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert g.returncode == 2, (
        f"毒化 sidecar 不得 fail-open; rc={g.returncode} err={g.stderr!r} poison={poison.read_text()!r}"
    )


# ── mutation 自證（隔離副本 + monkeypatch helper.GATE_TARGET；禁直接改 repo scripts）──


def _dispatch_via_helper(
    root: Path,
    audit: Path,
    gate_dir: Path,
) -> subprocess.CompletedProcess[str]:
    """經 helper.GATE_TARGET 派工（探針 monkeypatch 此常數注入變異腳本）。"""
    env = _base_env(audit, gate_dir)
    return helper.run_cmd(
        helper.GATE_TARGET,
        "dispatch",
        "--intent",
        "debt-gate mutation",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit-test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:debt-gate mutation",
        "--task-id",
        f"debt-gate-mut-{uuid.uuid4().hex[:8]}",
        "--output",
        "handoffs/debt-gate-mut.md",
        env=env,
        cwd=root,
    )


def test_mutation_check_open_debt_always_zero_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M1：_check_open_debt 永遠回報無債 → OPEN 輸入從紅變綠（證偽後還原仍紅）。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    _open_debt(root, audit, round_id=str(uuid.uuid4()), session="s-mut1")
    gate = root / "scripts" / "gate.sh"
    monkeypatch.setattr(helper, "GATE_TARGET", gate)
    original = gate.read_text(encoding="utf-8")
    # baseline：OPEN 應拒
    base = _dispatch_via_helper(root, audit, gate_dir)
    assert base.returncode != 0, f"baseline 應拒; {base.stderr!r}"
    # 變異：函式開頭直接 return 0
    mutated = original.replace(
        "_check_open_debt() {\n  local debt_bin ledger_rc\n",
        "_check_open_debt() {\n  return 0\n  local debt_bin ledger_rc\n",
        1,
    )
    assert mutated != original, "mutation 未生效（搜尋字串未命中）"
    gate.write_text(mutated, encoding="utf-8")
    gate.chmod(0o755)
    r_mut = _dispatch_via_helper(root, audit, gate_dir)
    # 還原
    gate.write_text(original, encoding="utf-8")
    gate.chmod(0o755)
    r_fix = _dispatch_via_helper(root, audit, gate_dir)
    assert r_mut.returncode == 0, (
        f"mutation 後應假綠(放行); rc={r_mut.returncode} err={r_mut.stderr!r}"
    )
    assert r_fix.returncode != 0, (
        f"還原後應再拒; rc={r_fix.returncode} err={r_fix.stderr!r}"
    )


def test_mutation_skip_debt_call_site_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """註解掉唯一呼叫點 → OPEN 輸入假綠；還原轉紅。"""
    root, audit, gate_dir = _setup_repo(tmp_path)
    _open_debt(root, audit, round_id=str(uuid.uuid4()), session="s-mut2")
    gate = root / "scripts" / "gate.sh"
    monkeypatch.setattr(helper, "GATE_TARGET", gate)
    original = gate.read_text(encoding="utf-8")
    needle = "  _check_open_debt || exit 1\n"
    assert needle in original, "找不到唯一呼叫點"
    base = _dispatch_via_helper(root, audit, gate_dir)
    assert base.returncode != 0, f"baseline 應拒; {base.stderr!r}"
    gate.write_text(original.replace(needle, "  # mutated: skipped debt check\n", 1), encoding="utf-8")
    gate.chmod(0o755)
    r_mut = _dispatch_via_helper(root, audit, gate_dir)
    gate.write_text(original, encoding="utf-8")
    gate.chmod(0o755)
    r_fix = _dispatch_via_helper(root, audit, gate_dir)
    assert r_mut.returncode == 0, f"skip 呼叫點應假綠; {r_mut.stderr!r}"
    assert r_fix.returncode != 0, f"還原應拒; {r_fix.stderr!r}"
