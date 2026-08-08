"""GOVB1 Task 1.2 — finding ID 樣板驗證（_check_id_pattern）。

T-1.2-U* 正反 fixture、T-1.2-E1 三段錯誤訊息、T-1.2-M1 限縮 mutation。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BRIEF_CONF = REPO / "scripts" / "brief_conformance_check.sh"
COMPLETENESS = REPO / "scripts" / "completeness_check.sh"
FIXTURE = REPO / "tests" / "governance" / "fixtures" / "govb1"
LIFECYCLE = REPO / "scripts" / "govflow_lifecycle.json"


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


def _canon_re() -> str:
    m = re.search(
        r"^CANONICAL_ID_RE='([^']+)'",
        COMPLETENESS.read_text(encoding="utf-8"),
        re.M,
    )
    assert m, "completeness_check.sh 缺 CANONICAL_ID_RE"
    return m.group(1)


# ── U：正反 fixture ──────────────────────────────────────────────


def test_t12_u1_b0r_fixture_rc_nonzero() -> None:
    """ASSERT brief_id_b0r.md → rc!=0（敘事反引號內 B0R）。"""
    proc = _check(FIXTURE / "brief_id_b0r.md")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "CODEX-B0R-P1-01" in (proc.stdout + proc.stderr)


def test_t12_u2_discussion_fixture_rc_zero() -> None:
    """ASSERT brief_id_discussion.md → rc=0。"""
    proc = _check(FIXTURE / "brief_id_discussion.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t12_u3_impl_kind_skips_id_check(tmp_path: Path) -> None:
    """非 findings-kind（impl）即使含 B0R 亦不擋。"""
    p = tmp_path / "impl.md"
    p.write_text(
        "brief-kind: impl\n\n"
        "EXPECTED-DELTA:\n"
        "- tests: id pattern impl skip\n\n"
        "任務要求產出 `CODEX-B0R-P1-01`（不應擋）。\n",
        encoding="utf-8",
    )
    # 需 lifecycle JSON 可解析：把腳本與 JSON 一併放入 temp scripts/
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy2(BRIEF_CONF, scripts / "brief_conformance_check.sh")
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    shutil.copy2(COMPLETENESS, scripts / "completeness_check.sh")
    proc = _run(
        ["bash", str(scripts / "brief_conformance_check.sh"), str(p)],
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t12_u4_no_id_tokens_rc_zero(tmp_path: Path) -> None:
    """邊界①：完全無 ID 樣板 ⇒ rc=0。"""
    p = tmp_path / "empty_id.md"
    p.write_text(
        "brief-kind: review\n\n"
        "templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做\n\n"
        "fact-verified: `true` → ok\n"
        "assumed: 無 ID\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t12_u5_fence_id_ignored(tmp_path: Path) -> None:
    """邊界②：code fence 內 B0R ⇒ rc=0。"""
    p = tmp_path / "fence.md"
    p.write_text(
        "brief-kind: review\n\n"
        "templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做\n\n"
        "fact-verified: `true` → ok\n"
        "assumed: fence\n\n"
        "```\n"
        "CODEX-B0R-P1-01\n"
        "```\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_t12_u6_canonical_id_in_backtick_ok(tmp_path: Path) -> None:
    """合法 canonical token 在反引號內 ⇒ rc=0。"""
    p = tmp_path / "canon_ok.md"
    p.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做\n\n"
        "fact-verified: `true` → ok\n"
        "assumed: ok\n\n"
        "請產出 `CODEX-R1-P0-01` 形態 findings。\n",
        encoding="utf-8",
    )
    proc = _check(p)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── E1：三段錯誤訊息 ─────────────────────────────────────────────


def test_t12_e1_error_message_three_parts() -> None:
    """stderr/stdout 須含違規 token／期望樣式／修法。"""
    proc = _check(FIXTURE / "brief_id_b0r.md")
    assert proc.returncode != 0
    out = proc.stdout + proc.stderr
    assert "違規 token" in out
    assert "CODEX-B0R-P1-01" in out
    assert "期望樣式" in out
    re_lit = _canon_re()
    assert re_lit in out
    assert "修法" in out


# ── M1：限縮 mutation ────────────────────────────────────────────


def test_t12_m1_remove_findings_kind_gate_false_positive(tmp_path: Path) -> None:
    """mutation：拿掉 findings-kind 限縮 ⇒ impl+B0R 轉紅（對照：production 綠）。"""
    src = BRIEF_CONF.read_text(encoding="utf-8")
    # 把 _is_findings_kind 改為恆真
    mut = src.replace(
        "_is_findings_kind() {\n  # $1=brief-kind 值\n  case \"$1\" in\n"
        "    review|consult|closure) return 0 ;;\n"
        "    *) return 1 ;;\n"
        "  esac\n}",
        "_is_findings_kind() { return 0; }",
        1,
    )
    assert mut != src, "mutation 未命中 _is_findings_kind"
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "brief_conformance_check.sh").write_text(mut, encoding="utf-8")
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    shutil.copy2(COMPLETENESS, scripts / "completeness_check.sh")
    brief = tmp_path / "impl_b0r.md"
    brief.write_text(
        "brief-kind: impl\n\n"
        "EXPECTED-DELTA:\n"
        "- tests: id pattern mutation impl\n\n"
        "任務 `CODEX-B0R-P1-01`\n",
        encoding="utf-8",
    )
    # production：impl 不擋
    prod = _check(brief)
    assert prod.returncode == 0, "production 對 impl 應放行"
    # mutated：應擋
    bad = _run(
        ["bash", str(scripts / "brief_conformance_check.sh"), str(brief)],
        cwd=str(tmp_path),
    )
    assert bad.returncode != 0, "移除 findings-kind 限縮後 impl+B0R 應轉紅"


def test_t12_m1_remove_active_scan_false_negative(tmp_path: Path) -> None:
    """mutation：_active_id_tokens 改空 ⇒ b0r fixture 假綠。"""
    src = BRIEF_CONF.read_text(encoding="utf-8")
    mut = re.sub(
        r"_active_id_tokens\(\) \{.*?\n\}",
        "_active_id_tokens() { :; }",
        src,
        count=1,
        flags=re.S,
    )
    assert mut != src, "mutation 未命中 _active_id_tokens"
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "brief_conformance_check.sh").write_text(mut, encoding="utf-8")
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    shutil.copy2(COMPLETENESS, scripts / "completeness_check.sh")
    # copy fixture into tmp so path is simple
    brief = tmp_path / "b0r.md"
    brief.write_text(
        (FIXTURE / "brief_id_b0r.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # production 紅
    assert _check(FIXTURE / "brief_id_b0r.md").returncode != 0
    # mutated 假綠
    proc = _run(
        ["bash", str(scripts / "brief_conformance_check.sh"), str(brief)],
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, "拿掉 active 掃描後 b0r 應假綠（證限縮必要）"
