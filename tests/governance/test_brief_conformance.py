"""委員派工 brief 合規閘(P1-1):防「手搓 brief 漏引用範本 / 漏攤前提」。

病根(本 session 兩次事故,同一因):手搓 brief 未引用委員範本 →
1. 委員不用 canonical 格式 → completeness 抽不到 → Claude 手做 reconcile → 掉項(漏 grok T1-01)。
2. brief 未含 §0 挑戰前提 → Claude 錯誤前提被當 finding 帶回(偽 finding C2)。

治本(不重列範本條款,避免與範本漂移):cx_run.sh fail-closed 強制
- 收集 findings 類 brief(review/consult/closure)須**引用委員範本**(單一真相源承載 canonical 格式/§0-§3/Verdict)
- 且補**任務專屬前提宣告**(≥1 fact-verified + ≥1 assumed;範本給不了、每次須攤開)
- impl/stamp 不產 findings → 不強制(不誤擋)
範本↔工具相容性:COMMITTEE_FINDING_TEMPLATE 的 ID 正則與 completeness_check.sh CANONICAL_ID_RE 逐字一致(實測)。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CX_RUN = REPO / "scripts" / "cx_run.sh"

_REF = "照 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文"
_FACT = "fact-verified: gate.sh:453 實讀 → 只在 --reconcile 觸發"
_ASSUMED = "assumed: 送尚未驗完整的 reconcile 去審是合法情境"


def _run(brief: Path, family: str = "codex") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CX_RUN), family, str(brief), "handoffs/unit-test-out.md"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )


def _brief(tmp_path: Path, *lines: str) -> Path:
    b = tmp_path / "b.md"
    b.write_text("# t\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return b


# ---- brief-kind 宣告 ----
def test_missing_brief_kind_rejected(tmp_path: Path) -> None:
    p = _run(_brief(tmp_path, "隨便寫"))
    assert p.returncode != 0 and "brief-kind" in (p.stdout + p.stderr)


def test_unknown_kind_rejected(tmp_path: Path) -> None:
    p = _run(_brief(tmp_path, "brief-kind: whatever"))
    assert p.returncode != 0 and "未知 brief-kind" in (p.stdout + p.stderr)


# ---- ① 強制引用範本(事故 1:委員不照 canonical 格式) ----
def test_review_missing_template_reference_rejected(tmp_path: Path) -> None:
    """review brief 未引用任何委員範本 → 拒(委員不會照 canonical 格式 → completeness 抽不到)。"""
    p = _run(_brief(tmp_path, "brief-kind: review", _FACT, _ASSUMED))
    out = p.stdout + p.stderr
    assert p.returncode != 0 and "引用" in out and "範本" in out


# ---- ② 前提宣告:各 ≥1(事故 2:錯誤前提被當 finding 帶回) ----
def test_review_missing_assumed_rejected(tmp_path: Path) -> None:
    """引用範本但無 assumed → 拒(宣稱零假設可疑,逼攤開可疑前提)。"""
    p = _run(_brief(tmp_path, "brief-kind: review", _REF, _FACT))
    out = p.stdout + p.stderr
    assert p.returncode != 0 and "前提宣告" in out


def test_review_missing_fact_verified_rejected(tmp_path: Path) -> None:
    p = _run(_brief(tmp_path, "brief-kind: review", _REF, _ASSUMED))
    out = p.stdout + p.stderr
    assert p.returncode != 0 and "前提宣告" in out


# ---- 合規 → 過 brief 閘 ----
def test_compliant_review_brief_passes_brief_gate(tmp_path: Path) -> None:
    """引用範本 + 各 ≥1 前提 → 過 brief 閘(以未知 family 讓流程停在 family 檢查,證明已過 brief 檢查)。"""
    p = _run(_brief(tmp_path, "brief-kind: review", _REF, _FACT, _ASSUMED), family="notafamily")
    out = p.stdout + p.stderr
    assert "brief-kind" not in out and "引用" not in out and "前提宣告" not in out
    assert "family 須為" in out  # 停在 family 檢查 = brief 閘放行


def test_semantic_template_reference_accepted(tmp_path: Path) -> None:
    """引用語意審範本(另一合法範本)亦算合規。"""
    p = _run(
        _brief(tmp_path, "brief-kind: closure", "照 templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md",
               _FACT, _ASSUMED),
        family="notafamily",
    )
    out = p.stdout + p.stderr
    assert "family 須為" in out  # 過 brief 閘


# ---- impl/stamp 不誤擋 ----
def test_impl_kind_not_required_to_have_finding_clauses(tmp_path: Path) -> None:
    p = _run(_brief(tmp_path, "brief-kind: impl", "照 TODO 實作 B1"), family="notafamily")
    out = p.stdout + p.stderr
    assert "引用" not in out and "前提宣告" not in out
    assert "family 須為" in out


# ---- 範本↔工具相容性(實測 canonical ID 正則逐字一致) ----
def test_template_id_regex_matches_completeness_tool() -> None:
    """COMMITTEE_FINDING_TEMPLATE 的 ID 正則須與 completeness_check CANONICAL_ID_RE 一致(否則鏈斷)。"""
    tmpl = (REPO / "templates" / "COMMITTEE_FINDING_TEMPLATE.md").read_text(encoding="utf-8")
    tool = (REPO / "scripts" / "completeness_check.sh").read_text(encoding="utf-8")
    canon = r"^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$"
    assert canon in tmpl, "範本缺 canonical ID 正則"
    assert canon in tool, "工具缺 canonical ID 正則"
