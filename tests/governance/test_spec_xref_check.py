"""spec_xref_check.sh — 「改一處漏一處」閘之可證偽測試。

每條對應腳本檔頭一個判準；含一條 mutation（把判準關掉 ⇒ 測試必紅）。
只跑本檔：pytest tests/governance/test_spec_xref_check.py -q
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "spec_xref_check.sh"


def _run(old: str, new: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    o = tmp_path / "old.md"
    n = tmp_path / "new.md"
    o.write_text(old, encoding="utf-8")
    n.write_text(new, encoding="utf-8")
    return subprocess.run(
        ["bash", str(SCRIPT), "--files", str(o), str(n)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


OLD = (
    "- 改法：視窗用 `origin/main..HEAD` 取聯集。\n"
    "- 邊界：首次 push 時 `origin/main..HEAD` 為空。\n"
    "- 其他：`unrelated_token_x` 不動。\n"
)


def test_dropped_token_with_untagged_residue_fails(tmp_path: Path) -> None:
    """改了改法那行、邊界那行漏改且沒標版本 ⇒ rc=1 並指名行號。"""
    new = OLD.replace("視窗用 `origin/main..HEAD` 取聯集", "視窗讀 audit 持續視窗取聯集")
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "`origin/main..HEAD` @L2" in r.stdout


def test_residue_tagged_with_version_passes(tmp_path: Path) -> None:
    """同一殘留行標了 v3 ⇒ 視為歷史敘述，rc=0（對照組）。"""
    new = OLD.replace("視窗用 `origin/main..HEAD` 取聯集", "視窗讀 audit 持續視窗取聯集")
    new = new.replace("首次 push 時 `origin/main..HEAD` 為空", "（v3 曾用 `origin/main..HEAD`，首次 push 為空）")
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_all_references_synced_passes(tmp_path: Path) -> None:
    """兩處都改掉 ⇒ rc=0。"""
    new = OLD.replace("`origin/main..HEAD`", "`audit 持續視窗`")
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_token_still_in_added_lines_is_not_dropped(tmp_path: Path) -> None:
    """token 只是被搬到另一行（added 行仍含它）⇒ 不算被拿掉，rc=0。"""
    new = OLD.replace(
        "- 改法：視窗用 `origin/main..HEAD` 取聯集。",
        "- 改法：取聯集，範圍＝`origin/main..HEAD`（維持）。",
    )
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_unchanged_file_passes(tmp_path: Path) -> None:
    r = _run(OLD, OLD, tmp_path)
    assert r.returncode == 0


def test_mutation_disabling_check_turns_red(tmp_path: Path) -> None:
    """mutation：把違規判準改成永不成立 ⇒ 第一條測試必須翻紅（證明測試不是廉價綠燈）。"""
    src = SCRIPT.read_text(encoding="utf-8")
    mutated = src.replace("if t in line and not ver_re.search(line):", "if False:")
    assert mutated != src
    m = tmp_path / "mutated.sh"
    m.write_text(mutated, encoding="utf-8")
    new = OLD.replace("視窗用 `origin/main..HEAD` 取聯集", "視窗讀 audit 持續視窗取聯集")
    o = tmp_path / "o.md"; n = tmp_path / "n.md"
    o.write_text(OLD, encoding="utf-8"); n.write_text(new, encoding="utf-8")
    r = subprocess.run(["bash", str(m), "--files", str(o), str(n)], cwd=ROOT,
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, "mutation 後仍擋 ⇒ 測試沒在測判準"


@pytest.mark.parametrize("args", [["--bogus"], ["--files", "only_one"]])
def test_usage_error_rc2(args: list[str]) -> None:
    r = subprocess.run(["bash", str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)
    assert r.returncode == 2
