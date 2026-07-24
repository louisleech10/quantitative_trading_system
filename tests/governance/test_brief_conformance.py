"""委員派工 brief 合規閘:防「手搓 brief 漏掉範本必填條款」。

兩次實證事故(同一病根,2026-07-23/24):
1. 手搓 brief 漏 canonical finding ID 格式 → 委員產出格式不一(codex `F-01`/grok `GROK-T1-01`/
   composer 無 ID)→ `completeness_check` 抽不到 → Claude 只能手做 reconcile → **掉項**(漏記 grok 立場)。
2. 手搓 brief 漏範本 §0「反幻覺/挑戰前提」→ Claude 把自己的錯誤前提寫進題目當範例,
   委員順著產出偽 finding(實例:把「送草稿 reconcile 去審」寫成合法情境)。ORCH L94 已記此傷疤
   (「開委員會時餵相同框架給多模型 → 相關性錯誤,前提錯到使用者才抓出」)。

範本 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 兩條都寫好好的——問題是手搓時漏掉。
故 `cx_run.sh`(所有委員派工統一入口)fail-closed 擋。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CX_RUN = REPO / "scripts" / "cx_run.sh"

_CANON = "輸出用 ## <FAMILY>-R<n>-P[0-3]-<NN>"
_PREMISE = "請先挑戰前提,勿只答我框好的題"


def _run(brief: Path, family: str = "codex") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CX_RUN), family, str(brief), "handoffs/unit-test-out.md"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )


def test_missing_brief_kind_rejected(tmp_path: Path) -> None:
    b = tmp_path / "b.md"
    b.write_text("# t\n隨便寫\n", encoding="utf-8")
    p = _run(b)
    assert p.returncode != 0 and "brief-kind" in (p.stdout + p.stderr)


def test_review_missing_canonical_id_rejected(tmp_path: Path) -> None:
    """事故 1:缺 canonical ID → 委員產出機器讀不到。"""
    b = tmp_path / "b.md"
    b.write_text(f"# t\nbrief-kind: review\n{_PREMISE}\n", encoding="utf-8")
    p = _run(b)
    out = p.stdout + p.stderr
    assert p.returncode != 0 and "canonical finding ID" in out


def test_review_missing_challenge_premise_rejected(tmp_path: Path) -> None:
    """事故 2:缺挑戰前提 → Claude 錯誤前提被當 finding 帶回。"""
    b = tmp_path / "b.md"
    b.write_text(f"# t\nbrief-kind: review\n{_CANON}\n", encoding="utf-8")
    p = _run(b)
    out = p.stdout + p.stderr
    assert p.returncode != 0 and "挑戰前提" in out


def test_unknown_kind_rejected(tmp_path: Path) -> None:
    b = tmp_path / "b.md"
    b.write_text("# t\nbrief-kind: whatever\n", encoding="utf-8")
    p = _run(b)
    assert p.returncode != 0 and "未知 brief-kind" in (p.stdout + p.stderr)


def test_compliant_review_brief_passes_brief_gate(tmp_path: Path) -> None:
    """合規 brief 應通過 brief 閘(以未知 family 讓流程停在 family 檢查,證明已過 brief 檢查)。"""
    b = tmp_path / "b.md"
    b.write_text(f"# t\nbrief-kind: review\n{_CANON}\n{_PREMISE}\n", encoding="utf-8")
    p = _run(b, family="notafamily")
    out = p.stdout + p.stderr
    assert "brief-kind" not in out and "canonical finding ID" not in out and "挑戰前提" not in out
    assert "family 須為" in out  # 停在 family 檢查 = brief 閘已放行


def test_impl_kind_not_required_to_have_finding_clauses(tmp_path: Path) -> None:
    """實作派工不產 findings → 不強制 canonical ID/挑戰前提(避免誤擋)。"""
    b = tmp_path / "b.md"
    b.write_text("# t\nbrief-kind: impl\n照 TODO 實作 B1\n", encoding="utf-8")
    p = _run(b, family="notafamily")
    out = p.stdout + p.stderr
    assert "canonical finding ID" not in out and "挑戰前提" not in out
    assert "family 須為" in out
