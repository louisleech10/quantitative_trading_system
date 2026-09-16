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

# new_brief.sh 逐字吐出的骨架佔位**完整行**（封閉集合，與腳本內 awk `ph[]` 對應）。
# 🔴 DOCROT consult-r4 Task 1.8（codex 機械版）：由全文 substring 改為 exact-line，
#   故測試字面必須是 generator 的整行，手寫近似字串不再算命中（那正是誤擋的來源）。
PLACEHOLDER_TARGET = (
    "- **current block**：（檔:起訖行 或 節名——**只列本輪要審的現行段落**，不得寫「整份檔」）"
)
PLACEHOLDER_ASSUMED = "assumed: （我的假設，可能是錯的） ← 請直接攻這條"
COMPLETENESS = REPO / "scripts" / "completeness_check.sh"


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
            f"{PLACEHOLDER_ASSUMED}\n"
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
            f"{PLACEHOLDER_TARGET}\n\n"
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


# ── DOCROT consult-r4 Task 1.8：合法引用不誤擋（exact-line＋fence／blockquote scope）──


def test_quoted_and_fenced_placeholder_literals_pass(tmp_path: Path) -> None:
    """Task 1.8 ASSERT 骨架字面只出現在 blockquote／成對 fence 內 ⇒ rc=0（不誤擋）。

    前版全文 `grep -qF` 對此 rc=2，誤拒後靠人改寫引用＝紀律；使用者裁定不接受。
    mutation：把 scanner 改回全檔 substring ⇒ 本條紅。
    """
    brief = _brief(
        tmp_path,
        "quoted.md",
        body=(
            "## 審查標的\n"
            "- current block：docs/X_SPEC.md:70-90\n"
            "- 本輪 diff：git diff a..b -- docs/X_SPEC.md\n\n"
            f"> 範例：{PLACEHOLDER_ASSUMED}\n\n"
            "```\n"
            f"{PLACEHOLDER_TARGET}\n"
            "1. （問題一）\n"
            "```\n\n"
            "fact-verified: 真的查過了 → 實跑 grep\n"
            "assumed: 條數只在一處\n"
        ),
    )
    proc = _check(brief)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_unclosed_fence_is_fail_closed(tmp_path: Path) -> None:
    """Task 1.8 ASSERT fence 未閉合 ⇒ rc≠0（無法判定佔位是否在 fence 內，fail-closed）。"""
    brief = _brief(
        tmp_path,
        "unclosed.md",
        body=(
            "fact-verified: 真的查過了 → 實跑 grep\n"
            "assumed: 條數只在一處\n\n"
            "```\n"
            f"{PLACEHOLDER_TARGET}\n"
        ),
    )
    proc = _check(brief)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    # 既有 kind 解析已對未閉合 fence fail-closed（訊息「未閉合的 code fence」）；
    # 佔位 scanner 的 `<UNCLOSED-FENCE>` 是第二道，兩者任一擋下皆合約。
    assert "未閉合" in proc.stdout + proc.stderr


def test_active_exact_placeholder_line_still_rejected(tmp_path: Path) -> None:
    """Task 1.8 ASSERT 佔位整行原樣出現在 active 行（非 fence／非 blockquote）⇒ 仍拒。"""
    brief = _brief(
        tmp_path,
        "active.md",
        body=(
            "fact-verified: 真的查過了 → 實跑 grep\n"
            "assumed: 條數只在一處\n"
            f"   {PLACEHOLDER_TARGET}   \n"
        ),
    )
    proc = _check(brief)
    assert proc.returncode != 0, proc.stdout + proc.stderr


# ── DOCROT consult-r3 Task 1.4 ＋ consult-r4 Task 1.6：completeness --single 之機械牙 ──


def _single(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(COMPLETENESS), "--single", str(path), "--family", "grok"],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )


def _finding(tmp: Path, name: str, *, sev: str, evidence: str) -> Path:
    p = tmp / name
    p.write_text(
        f"## GROK-R9-{sev}-01\n\n"
        "**斷言**: 一句可證偽主張。\n\n"
        f"**碼證**: {evidence}\n\n"
        # DOCROT2 Task 3.1：未給 round id 之 --single 須類別；補上使拒收只能來自本檔各條之原判準
        "**類別**: code-contract\n\n"
        "**來源摘要**: docs/X.md#abcdef123456\n\n"
        "[BLOCKING] 信心度=High。修法：x。\n",
        encoding="utf-8",
    )
    return p


def _target_with_history(tmp: Path) -> Path:
    t = tmp / "TARGET_SPEC.md"
    t.write_text(
        "## 本文\n活文第 2 行\n\n<!-- HISTORY-BEGIN -->\n舊主張（第 5 行）\n<!-- HISTORY-END -->\n"
        "## 沿革與追溯索引\n沿革內第 8 行\n## 附錄\n附錄第 10 行\n",
        encoding="utf-8",
    )
    return t


def test_p0_without_code_anchor_or_mutation_rejected(tmp_path: Path) -> None:
    """Task 1.6 ASSERT P0 碼證只有散文 ⇒ `--single` rc≠0。

    碼證：grok R4 實跑——純散文 P0 在前版 `--single` rc=0（無碼錨牙）。
    mutation：刪 `_validate_anchors` 之 token 檢查 ⇒ 本條紅。
    """
    p = _finding(tmp_path, "prose.md", sev="P0", evidence="見某章節用詞差異。")
    proc = _single(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "缺 CODE-ANCHOR:/MUTATION:" in proc.stderr, proc.stderr


def test_p1_missing_only_mutation_rejected(tmp_path: Path) -> None:
    """Task 1.6 ASSERT 有 CODE-ANCHOR 但缺 MUTATION ⇒ 仍拒（兩行皆必填）。"""
    t = _target_with_history(tmp_path)
    p = _finding(tmp_path, "nomut.md", sev="P1", evidence=f"CODE-ANCHOR: {t}:2")
    proc = _single(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "has_anchor=1 has_mutation=0" in proc.stderr, proc.stderr


def test_p0_with_active_anchor_and_mutation_passes(tmp_path: Path) -> None:
    """Task 1.6 ASSERT 兩 token 齊、anchor 在活文 ⇒ rc=0（證明非恆紅）。"""
    t = _target_with_history(tmp_path)
    p = _finding(
        tmp_path, "ok.md", sev="P0",
        evidence=f"CODE-ANCHOR: {t}:2\nMUTATION: 刪掉判定會紅。",
    )
    proc = _single(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_anchor_in_history_markers_rejected(tmp_path: Path) -> None:
    """Task 1.4 ASSERT CODE-ANCHOR 落在 HISTORY-BEGIN..END ⇒ rc≠0。

    碼證：D-002 之 R11 十二條、R12 十三條全部針對前版修法（審查者把作廢主張當現行）。
    mutation：刪區間判定 ⇒ 本條紅。
    """
    t = _target_with_history(tmp_path)
    p = _finding(
        tmp_path, "hist.md", sev="P0",
        evidence=f"CODE-ANCHOR: {t}:5\nMUTATION: 刪掉判定會紅。",
    )
    proc = _single(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "anchor 落在歷史段" in proc.stderr, proc.stderr


def test_anchor_in_history_section_rejected(tmp_path: Path) -> None:
    """Task 1.4 ASSERT anchor 落在 `## 沿革…` 節 ⇒ rc≠0；落在其後 `## 附錄` ⇒ rc=0。"""
    t = _target_with_history(tmp_path)
    bad = _finding(
        tmp_path, "sect.md", sev="P0",
        evidence=f"CODE-ANCHOR: {t}:8\nMUTATION: 刪掉判定會紅。",
    )
    assert _single(bad).returncode != 0
    ok = _finding(
        tmp_path, "appx.md", sev="P0",
        evidence=f"CODE-ANCHOR: {t}:10\nMUTATION: 刪掉判定會紅。",
    )
    proc = _single(ok)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_code_file_comment_marker_is_not_history(tmp_path: Path) -> None:
    """〔CODEX-R2-P1-01〕ASSERT 程式檔註解含 `HISTORY-BEGIN` 字面 ⇒ 不算歷史區；anchor 指其後程式行 rc=0。

    碼證：codex 構造 anchor 指 `scripts/completeness_check.sh:413`（scanner 程式行，其上方註解含該字面）
    ⇒ 前版 rc=1 誤拒。歷史區只存在於 .md 且 marker 為 `<!-- HISTORY-BEGIN -->` 註解形態。
    mutation：把 `case "${path}" in *.md)` 拿掉或 marker 正則放回裸字面 ⇒ 本條紅。
    """
    sh = tmp_path / "scanner.sh"
    sh.write_text(
        "#!/usr/bin/env bash\n# 遇 HISTORY-BEGIN 設狀態\n# 遇 HISTORY-END 清零\nawk 'NR==1' \"$1\"\n",
        encoding="utf-8",
    )
    p = _finding(
        tmp_path, "code_anchor.md", sev="P0",
        evidence=f"CODE-ANCHOR: {sh}:4\nMUTATION: 刪掉判定會紅。",
    )
    proc = _single(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_bare_marker_literal_in_md_prose_is_not_history(tmp_path: Path) -> None:
    """〔CODEX-R2-P1-01〕ASSERT .md 正文提到 `HISTORY-BEGIN` 字面（非 `<!-- -->` 註解）⇒ 不算歷史區。"""
    t = tmp_path / "PROSE_SPEC.md"
    t.write_text("## 本文\n本節說明 HISTORY-BEGIN 標記的用法。\n活文第 3 行\n", encoding="utf-8")
    p = _finding(
        tmp_path, "prose_anchor.md", sev="P0",
        evidence=f"CODE-ANCHOR: {t}:3\nMUTATION: 刪掉判定會紅。",
    )
    proc = _single(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_range_anchor_spanning_history_rejected(tmp_path: Path) -> None:
    """〔CODEX-R2-P1-02〕ASSERT `path:A-B` 範圍任一行落歷史 ⇒ rc≠0（不得截成起點偽裝現行）。

    碼證：codex 構造 `hist_sandwich.md:1-3`（第 1 行活文、第 3 行 HISTORY）⇒ 前版 rc=0。
    mutation：把 `(-[0-9]+)?` 拿掉或 `NR >= want && NR <= want_end` 改回 `NR == want` ⇒ 本條紅。
    """
    t = tmp_path / "SANDWICH_SPEC.md"
    t.write_text("活文 1\n<!-- HISTORY-BEGIN -->\n舊 3\n<!-- HISTORY-END -->\n活文 5\n", encoding="utf-8")
    bad = _finding(
        tmp_path, "range_bad.md", sev="P0",
        evidence=f"CODE-ANCHOR: {t}:1-3\nMUTATION: 刪掉判定會紅。",
    )
    proc = _single(bad)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "anchor 落在歷史段" in proc.stderr and ":1-3" in proc.stderr, proc.stderr
    ok = _finding(
        tmp_path, "range_ok.md", sev="P0",
        evidence=f"CODE-ANCHOR: {t}:5-5\nMUTATION: 刪掉判定會紅。",
    )
    proc = _single(ok)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_p3_sentinel_not_subject_to_token_rule(tmp_path: Path) -> None:
    """Task 1.6 ASSERT P2／P3（含零 findings sentinel）不套 token 必填。"""
    p = _finding(tmp_path, "p3.md", sev="P3", evidence="本輪無 finding。")
    proc = _single(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_templates_and_new_brief_carry_code_anchor_rule() -> None:
    """Task 1.6 ASSERT 範本與 new_brief 骨架含封閉字面（grok R3 驗收：grep 命中）。

    mutation：刪該句 ⇒ 本條紅。
    """
    prompt = (REPO / "templates" / "SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md").read_text(encoding="utf-8")
    finding = (REPO / "templates" / "COMMITTEE_FINDING_TEMPLATE.md").read_text(encoding="utf-8")
    newbrief = NEW_BRIEF.read_text(encoding="utf-8")
    for text, name in ((prompt, "SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md"), (finding, "COMMITTEE_FINDING_TEMPLATE.md")):
        assert "CODE-ANCHOR:" in text and "MUTATION:" in text, name
        assert "doc-literal-only" in text, name
    assert "CODE-ANCHOR:" in newbrief and "MUTATION:" in newbrief, "new_brief.sh 必答骨架缺 pointer 句"
