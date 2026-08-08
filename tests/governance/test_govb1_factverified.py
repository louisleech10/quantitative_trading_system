"""GOVB1 Task 1.4 — fact-verified 兩機械規則。

規則① count: 禁截斷；規則② 派工可變 rc 須標「派工後預期值」。
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

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
