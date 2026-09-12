"""DOCROT R2 之 E3（審查輸入隔離）產出端硬擋 — 骨架佔位未填即拒派。

病根（2026-09-12 DOCROT consult R1/R2 三家一致）：審查輸入若是「整份檔」，
審查者會重新審已作廢的主張、把上一輪的修法再審一次（`D-002` 之 R11 十二條、
R12 十三條**全部**針對前版修法）。修法逐字依 `CODEX-R1-P1-02`：
「review command 只餵 current block＋本輪 diff」。

`brief_conformance_check.sh` 原有的 ② 前提閘只**數** `assumed:` 行數 ⇒
`new_brief.sh` 吐出的未填骨架行照樣過閘。本檔驗新增之佔位偵測：
骨架原樣派出即 rc!=0，逐條填完即 rc=0（後者為 mutation 自證，證明本閘非恆紅）。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BRIEF_CONF = REPO / "scripts" / "brief_conformance_check.sh"
NEW_BRIEF = REPO / "scripts" / "new_brief.sh"

# new_brief.sh 逐字吐出的骨架佔位（封閉集合，與腳本內 PLACEHOLDERS 對應）
PLACEHOLDER_TARGET = "（檔:起訖行 或 節名"
PLACEHOLDER_ASSUMED = "（我的假設，可能是錯的）"


def _check(brief: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(BRIEF_CONF), str(brief)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO),
    )


def _brief(tmp: Path, name: str, *, body: str) -> Path:
    p = tmp / name
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return p


def test_filled_brief_passes(tmp_path: Path) -> None:
    """ASSERT 逐條填完之 brief → rc=0（證明本閘非恆紅）。"""
    brief = _brief(
        tmp_path,
        "filled.md",
        body=(
            "## 審查標的\n"
            "- current block：docs/X_SPEC.md:70-90（(5.6) register 段）\n"
            "- 本輪 diff：git diff abc1234..HEAD -- docs/X_SPEC.md\n\n"
            "fact-verified: register 現為 29 條 → 實跑 grep -c\n"
            "assumed: 條數只存在於表標題一處\n"
        ),
    )
    proc = _check(brief)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_unfilled_assumed_placeholder_rejected(tmp_path: Path) -> None:
    """ASSERT 未填之 assumed 骨架行 → rc!=0（補既有 ② 閘只數行數之洞）。"""
    brief = _brief(
        tmp_path,
        "unfilled_assumed.md",
        body=(
            "fact-verified: 真的查過了 → 實跑 grep\n"
            f"assumed: {PLACEHOLDER_ASSUMED}\n"
        ),
    )
    proc = _check(brief)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "未填骨架佔位" in proc.stdout + proc.stderr


def test_unfilled_review_target_rejected(tmp_path: Path) -> None:
    """ASSERT 審查標的原樣派出 → rc!=0（E3 之產出端硬擋）。"""
    brief = _brief(
        tmp_path,
        "unfilled_target.md",
        body=(
            "## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）\n"
            f"- **current block**：{PLACEHOLDER_TARGET}——只列本輪要審的現行段落）\n\n"
            "fact-verified: 真的查過了 → 實跑 grep\n"
            "assumed: 這條有填\n"
        ),
    )
    proc = _check(brief)
    assert proc.returncode != 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("kind", ["consult", "review", "impl"])
def test_real_new_brief_skeleton_is_rejected(kind: str) -> None:
    """ASSERT `new_brief.sh` 之真實產出未填即 rc!=0（端到端，非手搓字串）。

    防的是「骨架改了、閘的字面沒跟著改」——兩邊漂移時本條轉紅。
    `impl` 一併驗：佔位檢查置於 case 之前，對所有 kind 生效。

    new_brief.sh 強制輸出落在 `handoffs/` 且拒覆寫 ⇒ 用唯一檔名並於結束刪除。
    """
    out_rel = f"handoffs/.tmp-e3-probe-{kind}.md"
    out_abs = REPO / out_rel
    if out_abs.exists():
        out_abs.unlink()
    try:
        gen = subprocess.run(
            ["bash", str(NEW_BRIEF), kind, out_rel, "E3 佔位探針"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO),
        )
        assert gen.returncode == 0 and out_abs.exists(), (
            f"new_brief.sh 產骨架失敗 rc={gen.returncode}\n"
            f"stdout={gen.stdout}\nstderr={gen.stderr}"
        )
        proc = _check(out_abs)
        assert proc.returncode != 0, (
            "new_brief.sh 的未填骨架竟然過閘 ⇒ 佔位字面已漂移，"
            "請同步 brief_conformance_check.sh 之 PLACEHOLDERS\n"
            + proc.stdout
            + proc.stderr
        )
    finally:
        if out_abs.exists():
            out_abs.unlink()
