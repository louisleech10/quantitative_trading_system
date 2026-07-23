"""B2 — canonical ID / digest / DEGRADE namespace / same-file dup（Task 2.1）。

nodeid:
  test_missing_digest_p0_fails
  test_source_digest_injection
  test_degrade_namespace_not_invalid
  test_same_file_dup_fails
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _run(synth: Path, *sources: Path) -> subprocess.CompletedProcess[str]:
    cmd = ["bash", str(COMPLETENESS_SH), str(synth), *[str(s) for s in sources]]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _full_finding(
    fid: str,
    *,
    digest: str | None = None,
    src: str = "sources/review-grok.md",
    assert_text: str = "assert body",
    code_text: str = "code proof",
) -> str:
    d = digest or _sha12(fid)
    return (
        f"## {fid}\n\n"
        f"**斷言**: {assert_text}\n\n"
        f"**碼證**: {code_text}\n\n"
        f"**來源摘要**: {src}#{d}\n"
    )


def test_missing_digest_p0_fails(tmp_path: Path) -> None:
    """P0 finding 有斷言+碼證但缺來源摘要/digest → exit 1。"""
    body_no_digest = (
        "## GROK-R1-P0-01\n\n"
        "**斷言**: missing digest should fail\n\n"
        "**碼證**: path:1\n"
    )
    src = _write(tmp_path / "review-grok.md", body_no_digest)
    synth = _write(tmp_path / "synth.md", body_no_digest)
    result = _run(synth, src)
    assert result.returncode != 0, (
        f"P0 缺 digest 應 FAIL; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "digest" in combined.lower() or "來源摘要" in combined


def test_source_digest_injection(tmp_path: Path) -> None:
    """harness 注入 source_digest: 可替代 **來源摘要** 欄（TC14）。"""
    d = _sha12("inject-ok")
    body = (
        "## GROK-R1-P0-01\n\n"
        "**斷言**: harness digest injection\n\n"
        "**碼證**: path:1\n\n"
        f"source_digest: {d}deadbeef\n"  # ≥12 hex
    )
    src = _write(tmp_path / "review-grok.md", body)
    synth = _write(tmp_path / "synth.md", body)
    result = _run(synth, src)
    assert result.returncode == 0, (
        f"source_digest: 注入應 PASS; stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_degrade_namespace_not_invalid(tmp_path: Path) -> None:
    """合法 ## DEGRADE-GROK-01 不進 union、不當 invalid（可與合法 finding 共存）。"""
    finding = _full_finding("CODEX-R1-P0-01", src="sources/review-codex.md")
    body = finding + "\n## DEGRADE-GROK-01\n\nabsent family GROK; reason=timeout\n"
    src = _write(tmp_path / "review-codex.md", body)
    synth = _write(tmp_path / "synth.md", finding)
    result = _run(synth, src)
    assert result.returncode == 0, (
        f"DEGRADE 命名空間不應觸發 invalid; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "DEGRADE-GROK-01" not in combined or "invalid" not in combined.lower()


def test_same_file_dup_fails(tmp_path: Path) -> None:
    """同檔兩個相同 ## ID → FAIL（COMPOSER-P2-02 / TC14）。"""
    one = _full_finding("GROK-R1-P0-01", assert_text="first")
    two = _full_finding("GROK-R1-P0-01", assert_text="second-dup")
    body = one + "\n" + two
    src = _write(tmp_path / "review-grok.md", body)
    synth = _write(tmp_path / "synth.md", one)
    result = _run(synth, src)
    assert result.returncode != 0, (
        f"同檔 dup 應 FAIL; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "duplicate" in combined.lower() or "dup" in combined.lower()


def test_trailing_text_heading_fails(tmp_path: Path) -> None:
    """heading 尾隨文字/尾標點 → invalid（CODEX-B2-P1-01；正則須整行 anchored ^…$）。"""
    for bad_head in ("## GROK-R1-P0-01 trailing-text", "## GROK-R1-P0-01:", "## GROK-R1-P0-01 — 標題"):
        body = (
            f"{bad_head}\n\n"
            "**斷言**: anchored regex should reject trailing\n\n"
            "**碼證**: path:1\n\n"
            f"**來源摘要**: sources/review-grok.md#{_sha12('x')}\n"
        )
        src = _write(tmp_path / "review-grok.md", body)
        synth = _write(tmp_path / "synth.md", body)
        result = _run(synth, src)
        assert result.returncode != 0, (
            f"尾隨文字 heading 應 invalid: {bad_head!r}; "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        combined = (result.stdout or "") + (result.stderr or "")
        assert "invalid" in combined.lower() or "trailing" in combined.lower()


def test_clean_id_heading_still_valid(tmp_path: Path) -> None:
    """對照:乾淨 ID-only heading 仍合法（確認 anchoring 沒誤殺正常 finding）。"""
    body = _full_finding("GROK-R1-P0-01")
    src = _write(tmp_path / "review-grok.md", body)
    synth = _write(tmp_path / "synth.md", body)
    result = _run(synth, src)
    assert result.returncode == 0, (
        f"乾淨 ID heading 應 PASS; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
