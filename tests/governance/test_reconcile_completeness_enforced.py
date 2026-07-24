"""強制:拿來當**實作依據**的 reconcile 必須走 session 流程(可機械驗 0 掉項)。

事故(2026-07-23 使用者抓包):Claude 手做 SPEC adversarial reconcile,漏記委員 finding
(grok T1-01)卻不自知;三家 review ID 格式不一,工具讀不到。
病灶=classic `handoffs/*-RECONCILE.md` 走 gate 時 `_run_completeness_gate` **靜默 return 0**
→ 沒閘門就手做掉項。修(2026-07-24):classic → **拒發 + 遷移指引**,不設 waiver 逃生口
(委員警示 waiver 會變新旁路;且「選配=Claude 會跳過」已實證)。
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "gate.sh"
SPEC = REPO / "docs" / "CONVERGENCE_METHOD_SPEC.md"


def _stub_pass(p: Path) -> Path:
    """stub 掉戳記檢查(exit 0),讓測試能到達 completeness 閘本身。"""
    p.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return p


def _dispatch(gate_dir: Path, reconcile: Path, stamps_stub: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env["GOVERNANCE_TEST_HARNESS"] = "1"  # 允許 stub override(B3 反 bypass 要求)
    env["RECONCILE_STAMPS_CHECK_OVERRIDE"] = str(stamps_stub)
    return subprocess.run(
        [
            "bash", str(GATE), "dispatch",
            "--intent", "reconcile completeness enforcement unit test",
            "--risk", "high",
            "--facts-asked", "none-needed:unit-test",
            "--review-role", "single-executor:n/a",
            "--template", "n/a:unit test",
            "--spec", str(SPEC),
            "--adversarial", "waived:unit-test",
            "--reconcile", str(reconcile),
            "--task-id", "reconcile-enforce-unit",
            "--output", "handoffs/reconcile-enforce-unit.md",
        ],
        cwd=str(REPO), capture_output=True, text=True, check=False, env=env,
    )


def test_classic_reconcile_rejected_for_impl_dispatch(tmp_path: Path) -> None:
    """classic(非 session)reconcile 當實作依據 → **拒發**(修前:靜默放行)。

    mutation:把 `_run_completeness_gate` 的 classic 分支改回 `return 0` → 本測試轉綠(=失去保護)。
    """
    classic = tmp_path / "20260724-SOMETHING-RECONCILE.md"
    classic.write_text("# classic reconcile\nbody\n## 戳記\n", encoding="utf-8")
    proc = _dispatch(tmp_path / "gate", classic, _stub_pass(tmp_path / "stamps.sh"))
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"classic reconcile 竟放行(應拒):\n{out}"
    assert "未走 session 流程" in out, f"缺遷移指引訊息:\n{out}"


def test_low_risk_and_no_spec_also_enforced(tmp_path: Path) -> None:
    """通則(2026-07-24 使用者定):引用委員綜合即須驗,**不看 risk、不看 --spec**。

    修前:completeness 巢狀在 risk=high + --spec 內 → 自標 low 或不帶 --spec 即可繞。
    mutation:把通則區塊搬回 risk=high 內 → 本測試轉綠(失去保護)。
    """
    classic = tmp_path / "20260724-LOW-RECONCILE.md"
    classic.write_text("body\nVerdict: APPROVED\n## 戳記\n", encoding="utf-8")
    gate_dir = tmp_path / "gl"
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    proc = subprocess.run(
        [
            "bash", str(GATE), "dispatch",
            "--task-id", "low-enforce-unit",
            "--intent", "low risk citing a reconcile",
            "--risk", "low",  # 低風險
            "--facts-asked", "none-needed:unit-test",
            "--review-role", "single-executor:n/a",
            "--template", "n/a:unit test",  # 無 --spec
            "--reconcile", str(classic),
        ],
        cwd=str(REPO), capture_output=True, text=True, check=False, env=env,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"low-risk 引用未驗 reconcile 竟放行:\n{out}"
    assert not (gate_dir / "dispatch.token").exists(), "竟發出 token"


def _dispatch_raw(gate_dir: Path, extra: list[str], env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env["GOVERNANCE_TEST_HARNESS"] = "1"
    env.update(env_extra)
    return subprocess.run(
        [
            "bash", str(GATE), "dispatch",
            "--intent", "enforcement unit test",
            "--risk", "high",
            "--facts-asked", "none-needed:unit-test",
            "--review-role", "single-executor:n/a",
            "--spec", str(SPEC),
            "--task-id", "reconcile-enforce-unit2",
            "--output", "handoffs/reconcile-enforce-unit2.md",
        ] + extra,
        cwd=str(REPO), capture_output=True, text=True, check=False, env=env,
    )


def test_double_waiver_rejected_for_impl_dispatch(tmp_path: Path) -> None:
    """委員 A(codex+composer P0):雙 waived → completeness 完全不跑卻發 token。應拒。

    V-C 後：impl 對 waived/空 reconcile 改走 miss reconcile（仍 fail-closed，訊息更直接）。
    """
    proc = _dispatch_raw(
        tmp_path / "g",
        ["--adversarial", "waived:t", "--reconcile", "waived:t", "--template", "impl:real"],
        {"RECONCILE_STAMPS_CHECK_OVERRIDE": str(_stub_pass(tmp_path / "s.sh"))},
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"雙 waived 竟發 token(應拒):\n{out}"
    assert (
        "無可機械驗" in out
        or "一律須顯式 session reconcile" in out
        or "--reconcile" in out
    ), out


def test_review_dispatch_na_template_not_falsely_blocked(tmp_path: Path) -> None:
    """誤擋防護:review/adversarial 派工本身(無 --spec、--template n/a:)本無 reconcile,不得被 V-C 擋。

    V-C 後判定依 -n spec；真 review 不得帶 --spec（舊 fixture 誤帶 --spec 會被當 impl）。
    """
    gate_dir = tmp_path / "g2"
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env["GOVERNANCE_TEST_HARNESS"] = "1"
    env["RECONCILE_STAMPS_CHECK_OVERRIDE"] = str(_stub_pass(tmp_path / "s2.sh"))
    proc = subprocess.run(
        [
            "bash",
            str(GATE),
            "dispatch",
            "--intent",
            "review dispatch no-spec",
            "--risk",
            "high",
            "--facts-asked",
            "none-needed:unit-test",
            "--review-role",
            "single-executor:n/a",
            # 無 --spec → 非 impl，不進 V-C
            "--adversarial",
            "waived:t",
            "--template",
            "n/a:review 派工",
            "--task-id",
            "reconcile-enforce-review",
            "--output",
            "handoffs/reconcile-enforce-review.md",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, f"review 派工被誤擋:\n{proc.stdout}{proc.stderr}"


def test_comma_adversarial_每檔都驗(tmp_path: Path) -> None:
    """impl 須顯式 --reconcile；completeness 對 reconcile 主路徑跑（V-C 淘汰 adversarial-only fallback）。

    舊：無 --reconcile 時對 comma adversarial 逐檔 completeness。
    新：impl 一律 --reconcile <synth>；此測驗 recon 主路徑 completeness 有跑 + multi-file adversarial 仍可附。
    """
    files = []
    for name in ("s1", "s2"):
        d = tmp_path / "handoffs" / "reconcile" / name
        (d / "sources").mkdir(parents=True)
        (d / "sources.lock").write_text("{}", encoding="utf-8")
        f = d / "synth.md"
        f.write_text("body\nVerdict: APPROVED\n## 戳記\n", encoding="utf-8")  # D-1 需 Verdict 行
        files.append(str(f))
    log = tmp_path / "cc_calls.log"
    cc = tmp_path / "cc.sh"
    cc.write_text(f'#!/usr/bin/env bash\necho "call" >> {log}\nexit 0\n', encoding="utf-8")
    cc.chmod(cc.stat().st_mode | stat.S_IXUSR)
    proc = _dispatch_raw(
        tmp_path / "g3",
        [
            "--adversarial",
            ",".join(files),
            "--reconcile",
            files[0],  # V-C：impl 須顯式 recon
            "--template",
            "impl:real",
        ],
        {
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(_stub_pass(tmp_path / "s3.sh")),
            "COMPLETENESS_CHECK_OVERRIDE": str(cc),
        },
    )
    calls = log.read_text(encoding="utf-8").count("call") if log.exists() else 0
    assert calls >= 1, (
        f"completeness 應至少對 --reconcile 跑 1 次; calls={calls} "
        f"rc={proc.returncode}\n{proc.stdout}{proc.stderr}"
    )
    # 另：無 --reconcile 的 impl+multi-adv 仍須被 V-C 拒（防回歸到 adversarial-only）
    proc2 = _dispatch_raw(
        tmp_path / "g3b",
        ["--adversarial", ",".join(files), "--template", "impl:real"],
        {
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(_stub_pass(tmp_path / "s3b.sh")),
            "COMPLETENESS_CHECK_OVERRIDE": str(cc),
        },
    )
    assert proc2.returncode != 0, "impl 無 --reconcile 竟放行"
    assert "reconcile" in (proc2.stdout + proc2.stderr).lower()


def test_reject_message_names_the_three_step_fix(tmp_path: Path) -> None:
    """拒發訊息須給可操作的三步修法(canonical ID / write_sources_lock / completeness_check)。"""
    classic = tmp_path / "20260724-X-RECONCILE.md"
    classic.write_text("body\n## 戳記\n", encoding="utf-8")
    out = "".join(
        [
            (p := _dispatch(tmp_path / "g2", classic, _stub_pass(tmp_path / "s2.sh"))).stdout,
            p.stderr,
        ]
    )
    for token in ("canonical", "write_sources_lock.sh", "completeness_check.sh"):
        assert token in out, f"拒發訊息缺 {token}:\n{out}"


def test_nonexistent_reconcile_target_rejected(tmp_path: Path) -> None:
    """委員 codex C4:原不驗宣告檔是否存在 → 可指向 session 內不存在的 target 仍過。"""
    sess = tmp_path / "handoffs" / "reconcile" / "sess"
    (sess / "sources").mkdir(parents=True)
    (sess / "sources.lock").write_text("{}", encoding="utf-8")
    gate_dir = tmp_path / "gx"
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    proc = subprocess.run(
        [
            "bash", str(GATE), "dispatch", "--task-id", "c4-unit",
            "--intent", "t", "--risk", "low", "--facts-asked", "none-needed:t",
            "--review-role", "r", "--template", "n/a:t",
            "--reconcile", str(sess / "NOPE.md"),
        ],
        cwd=str(REPO), capture_output=True, text=True, check=False, env=env,
    )
    assert proc.returncode != 0, "指向不存在的綜合檔竟放行"
    assert "不存在" in (proc.stdout + proc.stderr)
    assert not (gate_dir / "dispatch.token").exists()
