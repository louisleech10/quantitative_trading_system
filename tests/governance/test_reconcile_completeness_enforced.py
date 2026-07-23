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
