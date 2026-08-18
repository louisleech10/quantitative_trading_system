"""小任務 3b — 白話說明 md→HTML 渲染器（scripts/plain_docs_render.{sh,py}）。

三件事（使用者 2026-08-18 定）：冪等／每個 .md 都有對應 .html／連結不死。
另驗：repo 內 docs/site/ 與現行 白話說明/*.md 一致（pre-commit 產出端強制之消費端備援）。
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SH = REPO / "scripts" / "plain_docs_render.sh"
PY = REPO / "scripts" / "plain_docs_render.py"


def _run(*args, cwd=REPO):
    return subprocess.run(["bash", str(SH), *args], cwd=str(cwd), capture_output=True, text=True, check=False)


def test_selftest_passes():
    """冪等／每 md 對應 html／連結改寫／過期偵測／死連結偵測（腳本自帶最小語料）。"""
    proc = _run("--selftest")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SELFTEST PASS" in proc.stdout


def test_committed_site_matches_sources():
    """repo 之 docs/site/ 必須與 白話說明/*.md 一致且 0 死連結（缺產出／過期即紅）。"""
    proc = _run("--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_every_md_has_html_and_index_lists_them(tmp_path):
    """對真實 白話說明/ 語料渲染到 tmp：每個 .md ⇒ 對應 .html；index 列出全部；同輸入二次渲染 byte 相同。"""
    src = REPO / "白話說明"
    out = tmp_path / "site"
    cmd = [sys.executable, str(PY), "--repo", str(REPO), "--src", str(src), "--out", str(out)]
    p1 = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert p1.returncode == 0, p1.stdout + p1.stderr
    mds = sorted(src.glob("*.md")) + sorted((src / "Archived").glob("*.md"))
    assert mds, "白話說明 無 .md？"
    index = (out / "index.html").read_text(encoding="utf-8")
    for md in mds:
        rel = md.relative_to(src).with_suffix(".html")
        assert (out / rel).is_file(), f"缺 {rel}"
        assert md.name in index, f"index 未列 {md.name}"
    snap = {p: p.read_bytes() for p in out.rglob("*.html")}
    p2 = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert p2.returncode == 0
    assert {p: p.read_bytes() for p in out.rglob("*.html")} == snap  # 冪等


def test_check_detects_missing_output(tmp_path):
    """--check 對缺產出必須 rc=1（缺產出即擋之根據）。"""
    src = tmp_path / "白話說明"
    src.mkdir()
    (src / "甲.md").write_text("# 甲\n\n內容\n", encoding="utf-8")
    out = tmp_path / "docs" / "site"
    proc = subprocess.run(
        [sys.executable, str(PY), "--repo", str(tmp_path), "--src", str(src), "--out", str(out), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "缺產出" in proc.stderr
