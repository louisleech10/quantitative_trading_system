"""GOVB1 Task 1.4 — fact-verified 兩機械規則。

規則① count: 禁截斷；規則② 派工可變 rc 須標「派工後預期值」。
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BRIEF_CONF = REPO / "scripts" / "brief_conformance_check.sh"
COMPLETENESS = REPO / "scripts" / "completeness_check.sh"
LIFECYCLE = REPO / "scripts" / "govflow_lifecycle.json"
FIXTURE = REPO / "tests" / "governance" / "fixtures" / "govb1"


def _run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    kw.setdefault("cwd", str(REPO))
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        **kw,  # type: ignore[arg-type]
    )


def _check(brief: Path) -> subprocess.CompletedProcess[str]:
    return _run(["bash", str(BRIEF_CONF), str(brief)])


def _write_consult(tmp: Path, name: str, fact_line: str) -> Path:
    p = tmp / name
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        f"{fact_line}\n"
        "assumed: test\n",
        encoding="utf-8",
    )
    return p


# ── 正反 fixture ─────────────────────────────────────────────────


def test_t14_u1_head_count_rc_nonzero() -> None:
    """ASSERT brief_factverified_head.md → rc!=0。"""
    proc = _check(FIXTURE / "brief_factverified_head.md")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "截斷" in out or "head" in out


def test_t14_u2_ok_fixture_rc_zero() -> None:
    """ASSERT brief_factverified_ok.md → rc=0。"""
    proc = _check(FIXTURE / "brief_factverified_ok.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_multi_backtick_early_trunc_rc_nonzero() -> None:
    """雙反引號：首組 head 截斷、末組無害 ⇒ 須擋（CODEX-R1-P1-03）。

    舊 _extract_cmd 只取末組 ⇒ 修前假綠；修後須 rc≠0。
    """
    proc = _check(FIXTURE / "brief_factverified_multi_trunc.md")
    assert proc.returncode != 0, (
        "multi-trunc fixture 須轉紅（首組 head 不得被末組 echo 掩蓋）\n"
        + proc.stdout
        + proc.stderr
    )
    out = proc.stdout + proc.stderr
    assert "截斷" in out or "head" in out


def test_t14_multi_backtick_both_clean_rc_zero(tmp_path: Path) -> None:
    """雙反引號：兩組皆無截斷 ⇒ 綠（防 over-block）。"""
    p = _write_consult(
        tmp_path,
        "multi_ok.md",
        "fact-verified: count: 2 — `wc -l some.log`；`echo stable`",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_neg_python_m_pytest_not_blocked(tmp_path: Path) -> None:
    """負向：python -m pytest 不得誤擋（即使在 count: 內）。"""
    p = _write_consult(
        tmp_path,
        "py.md",
        "fact-verified: count: `python -m pytest tests/governance -q` → 100",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_neg_pytest_m_marker_not_blocked(tmp_path: Path) -> None:
    """負向：pytest -m not_slow 不得誤擋。"""
    p = _write_consult(
        tmp_path,
        "mark.md",
        "fact-verified: count: `pytest -m not_slow` → 3",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_neg_natural_language_head_of_not_blocked(tmp_path: Path) -> None:
    """負向：自然語句 head of 不得誤擋（無 count: 指令）。"""
    p = _write_consult(
        tmp_path,
        "nat.md",
        "fact-verified: the head of the branch is main → git symbolic-ref",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_pos_grep_m1_blocked(tmp_path: Path) -> None:
    """正向：grep -m1 必須擋（count: 內）。"""
    p = _write_consult(
        tmp_path,
        "m1.md",
        "fact-verified: count: `grep -m1 ^foo bar.txt | wc -l` → 1",
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr


def test_t14_boundary_head_without_count_ok(tmp_path: Path) -> None:
    """邊界①：指令含 head 但無 count: ⇒ rc=0。"""
    p = _write_consult(
        tmp_path,
        "nocount.md",
        "fact-verified: `head -5 some.log` → 印出前 5 行（非計數）",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_rule2_debt_ledger_needs_post_dispatch(tmp_path: Path) -> None:
    """規則②：debt_ledger --has-open 缺「派工後預期值」⇒ 紅。"""
    p = _write_consult(
        tmp_path,
        "debt.md",
        "fact-verified: `bash scripts/debt_ledger.sh --has-open` → rc=0",
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "派工後預期值" in (proc.stdout + proc.stderr)


def test_t14_rule2_with_annotation_ok(tmp_path: Path) -> None:
    """規則②：標了派工後預期值 ⇒ 綠。"""
    p = _write_consult(
        tmp_path,
        "debt_ok.md",
        "fact-verified: `bash scripts/debt_ledger.sh --has-open` → rc=0；派工後預期值: rc=1",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── CODEX-R2-P1-04：反引號封閉類別（未成對／巢狀／跨行／零抽取）──


def test_t14_count_zero_backtick_rc_nonzero(tmp_path: Path) -> None:
    """零反引號 count: ⇒ 明確拒絕（STAMP-R4 補正之退化情形）。"""
    p = _write_consult(
        tmp_path,
        "zero_bt.md",
        "fact-verified: count: 1 — no command segment",
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "成對反引號" in out or "不得為空" in out, out


def test_t14_count_unpaired_backtick_rc_nonzero(tmp_path: Path) -> None:
    """未成對反引號 ⇒ rc≠0。"""
    p = _write_consult(
        tmp_path,
        "unpaired.md",
        "fact-verified: count: `head -5 x",  # 無閉合
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "成對反引號" in out or "不得為空" in out or "截斷" in out, out


def test_t14_count_cross_line_rc_nonzero(tmp_path: Path) -> None:
    """跨行分片：count: 列無閉合反引號 ⇒ 該列拒絕。"""
    p = tmp_path / "cross.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "fact-verified: count: `head -5 some.log\n"
        "x`\n"
        "assumed: test\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr


def test_t14_count_nested_backtick_rc_nonzero(tmp_path: Path) -> None:
    """巢狀反引號 ⇒ 非良構（奇數或配對數不符）⇒ rc≠0。"""
    # 3 backticks：open outer, open inner, close inner — unpaired outer
    p = _write_consult(
        tmp_path,
        "nested.md",
        "fact-verified: count: `printf `head -5` more",
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr


def test_t14_count_nested_even_backtick_rc_nonzero() -> None:
    """偶數巢狀反引號（NEW-CLASS）⇒ 段間含詞元 ⇒ rc=2。

    codex 活體：`` `echo outer `date` more` `` 修前 rc=0 假綠。
    """
    proc = _check(FIXTURE / "brief_factverified_nested_even.md")
    assert proc.returncode == 2, (
        "偶數巢狀反引號須明確拒絕（段間 date 非分隔符）\n"
        + proc.stdout
        + proc.stderr
    )
    out = proc.stdout + proc.stderr
    assert "成對反引號" in out or "不得為空" in out, out


def test_t14_count_blank_segment_rc_nonzero() -> None:
    """純空白指令段 `` `   ` `` ⇒ 視同零抽取 ⇒ rc≠0（COMPOSER-R3-P3-00）。"""
    proc = _check(FIXTURE / "brief_factverified_blank_seg.md")
    assert proc.returncode != 0, (
        "純空白指令段須明確拒絕\n" + proc.stdout + proc.stderr
    )
    out = proc.stdout + proc.stderr
    assert "成對反引號" in out or "不得為空" in out, out


def test_t14_count_blank_segment_inline_rc_nonzero(tmp_path: Path) -> None:
    """inline 純空白段（與 fixture 等價）⇒ rc≠0。"""
    p = _write_consult(
        tmp_path,
        "blank_inline.md",
        "fact-verified: count: 1 — `   `",
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr


def test_t14_count_nested_even_inline_rc_2(tmp_path: Path) -> None:
    """inline 偶數巢狀（與 fixture 等價）⇒ rc=2。"""
    p = _write_consult(
        tmp_path,
        "nested_even_inline.md",
        "fact-verified: count: 2 — `echo outer `date` more`",
    )
    proc = _check(p)
    assert proc.returncode == 2, proc.stdout + proc.stderr


# ── review-r4 NEW-CLASS：選列判準（錨定／fence／count token）────────


def test_t14_discuss_context_not_selected_rc_zero() -> None:
    """討論語境同時提及 fact-verified:＋count:（反引號內）⇒ 不進解析器 ⇒ rc=0。

    主委事故重現：修前 rc=2 誤擋；修後須綠。
    """
    proc = _check(FIXTURE / "brief_factverified_discuss_context.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_discuss_context_inline_rc_zero(tmp_path: Path) -> None:
    """inline 討論列（非行首宣告）⇒ rc=0。"""
    p = tmp_path / "discuss.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "fact-verified: smoke → ok\n"
        "assumed: test\n\n"
        "討論語境：規則以 `fact-verified:` 與 `count:` 標記掃描整行。\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_fence_declaration_not_selected_rc_zero(tmp_path: Path) -> None:
    """fence 內之 fact-verified 宣告樣式 ⇒ 不進解析器（含 head 截斷）⇒ rc=0。"""
    p = tmp_path / "fence.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "fact-verified: smoke → ok\n"
        "assumed: test\n\n"
        "```\n"
        "fact-verified: count: 1 — `head -5 some.log` → 5\n"
        "```\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_list_style_decl_still_checked(tmp_path: Path) -> None:
    """行首 list 標記 `- fact-verified:` 仍為有效宣告；含 head ⇒ rc=2。"""
    p = tmp_path / "list.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "- fact-verified: count: 1 — `head -5 some.log` → 5\n"
        "assumed: test\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "截斷" in out or "head" in out


def test_t14_count_token_not_max_count_field(tmp_path: Path) -> None:
    """max_count: 欄位名（含 head 指令）⇒ 非子字串 count: ⇒ 不進規則① ⇒ rc=0。"""
    p = _write_consult(
        tmp_path,
        "max_count.md",
        "fact-verified: max_count: 42 — `head -5 some.log` → preview only",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_count_token_not_counter_field(tmp_path: Path) -> None:
    """counter: 欄位名（非計數語境）⇒ 不進規則① ⇒ rc=0。"""
    p = _write_consult(
        tmp_path,
        "counter.md",
        "fact-verified: counter: 7 — `head -5 some.log` → preview only",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_midline_factverified_not_selected(tmp_path: Path) -> None:
    """行內任意位置 fact-verified:（非行首）⇒ 不選列；即使含 count:+head。"""
    p = tmp_path / "mid.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "fact-verified: smoke → ok\n"
        "assumed: test\n\n"
        "note: fact-verified: count: 1 — `head -5 x` → 5\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t14_decl_good_count_still_green(tmp_path: Path) -> None:
    """行首正常宣告 ＋ 良構指令無截斷 ⇒ rc=0（選列收窄後不退化）。"""
    p = _write_consult(
        tmp_path,
        "good.md",
        "fact-verified: count: 1 — `wc -l some.log` → 3",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── review-r5 REGRESSION：有界前綴擴充 ＋ fence fail-closed ────────


def _prefix_decl_line(prefix: str) -> str:
    """prefix 接到 fact-verified 計數＋head 截斷列。"""
    if prefix == "**":
        return "**fact-verified:** count: 1 — `head -5 some.log` → 5"
    return f"{prefix}fact-verified: count: 1 — `head -5 some.log` → 5"


@pytest.mark.parametrize(
    "prefix,label",
    [
        ("1. ", "ordered_dot"),
        ("2) ", "ordered_paren"),
        ("> ", "blockquote"),
        ("**", "bold"),
        ("+ ", "plus"),
        ("- ", "dash_control"),
        ("* ", "star_control"),
        ("> - ", "stacked_bq_dash"),
    ],
)
def test_t14_prefix_styles_head_blocked(
    tmp_path: Path, prefix: str, label: str
) -> None:
    """有界前綴集合：1./N)/>/**/+/−/* 及可堆疊 ⇒ 含 head 須 rc=2。

    review-r5 REGRESSION：父版僅 [-*]? 漏接 1./ >/ **/ +（修前 rc=0 假綠）。
    """
    p = tmp_path / f"prefix_{label}.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        f"{_prefix_decl_line(prefix)}\n"
        "assumed: test\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 2, (
        f"prefix={label!r} 須擋截斷（期望 rc=2）\n"
        + proc.stdout
        + proc.stderr
    )
    out = proc.stdout + proc.stderr
    assert "截斷" in out or "head" in out


def test_t14_unclosed_fence_fail_closed() -> None:
    """未閉合 fence ⇒ fail-closed rc≠0（禁吞至 EOF 靜默放行）。"""
    proc = _check(FIXTURE / "brief_factverified_unclosed_fence.md")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "unclosed" in out.lower() or "fail-closed" in out.lower() or "fence" in out.lower()


def test_t14_unclosed_fence_inline_fail_closed(tmp_path: Path) -> None:
    """inline 未閉合 fence 後仍有 active head 宣告 ⇒ rc≠0。"""
    p = tmp_path / "unclosed.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "```\n"
        "orphan fence body\n"
        "fact-verified: count: 1 — `head -5 some.log` → 5\n"
        "assumed: test\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode != 0, proc.stdout + proc.stderr


def test_t14_indent_fence_close_then_head_blocked() -> None:
    """縮排閉合 ``` 後之 active 宣告含 head ⇒ rc=2。"""
    proc = _check(FIXTURE / "brief_factverified_indent_fence_close.md")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "截斷" in out or "head" in out


def test_t14_indent_fence_close_inline(tmp_path: Path) -> None:
    """inline：兩個空白＋``` 閉合後 head 宣告 ⇒ rc=2。"""
    p = tmp_path / "indent_close.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "```\n"
        "code\n"
        "  ```\n"
        "fact-verified: count: 1 — `head -5 some.log` → 5\n"
        "assumed: test\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_t14_open_prefix_not_accepted(tmp_path: Path) -> None:
    """開放式前綴（@ 等非有界集合）不得被選列；含 count+head 仍 rc=0。"""
    p = tmp_path / "open_prefix.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "fact-verified: smoke → ok\n"
        "assumed: test\n\n"
        "@ fact-verified: count: 1 — `head -5 some.log` → 5\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── M1 mutation ──────────────────────────────────────────────────


def test_t14_m1_remove_rule1_false_green(tmp_path: Path) -> None:
    """mutation：_has_trunc 恆 false ⇒ head fixture 假綠。"""
    src = BRIEF_CONF.read_text(encoding="utf-8")
    mut = re.sub(
        r"_has_trunc\(\) \{.*?\n\}",
        "_has_trunc() { return 1; }",  # return 1 = no trunc detected
        src,
        count=1,
        flags=re.S,
    )
    assert mut != src
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "brief_conformance_check.sh").write_text(mut, encoding="utf-8")
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    shutil.copy2(COMPLETENESS, scripts / "completeness_check.sh")
    brief = tmp_path / "head.md"
    brief.write_text(
        (FIXTURE / "brief_factverified_head.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert _check(FIXTURE / "brief_factverified_head.md").returncode != 0
    proc = _run(
        ["bash", str(scripts / "brief_conformance_check.sh"), str(brief)],
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, "移除規則①後 head fixture 應假綠"
