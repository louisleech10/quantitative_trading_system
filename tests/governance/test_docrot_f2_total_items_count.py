"""DOCROT R2 之 F2（窄版計數字面閘）— 只收「共 N 條」語型。

病根（2026-09-12 DOCROT consult R1/R2 三家一致）：同一個數字寫在兩個地方，
改一處漏一處。碼證：`docs/SPLITUNIFY_SPEC.D-002.md:70`「register 共 29 條」
與 `:90` 表標題「共 29 條」並存；而 `scripts/spec_count_audit.py` 原第 51 行
逐字「刻意排除『條』」⇒ 對該形態**零命中**（改前實跑 `--list` 對 D-002 輸出為空）。

三家指定的是**窄版**：只數「共 N 條」，不是把所有「條」納入。本檔同時驗
「有抓到」與「沒擴大」——後者防的是把閘改成噪音製造機（收窄失敗即紅）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "scripts" / "spec_count_audit.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO),
    )


def _spec(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


def test_total_items_literal_is_captured(tmp_path: Path) -> None:
    """ASSERT 「共 29 條」被收入計數字面集合。"""
    p = _spec(tmp_path, "a.md", "## X\n\nregister 共 29 條，分四層敘述。\n")
    proc = _run(["--list", str(p)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "共 29 條" in proc.stdout, proc.stdout


def test_bare_items_literal_still_excluded(tmp_path: Path) -> None:
    """ASSERT 裸「條」仍不納入（證明是窄版，不是把「條」全開）。

    這條是收窄之可證偽斷言：若日後有人把 `_UNITS` 直接加上「條」，本條轉紅。
    """
    p = _spec(tmp_path, "b.md", "## X\n\nmutation 22 條；十三條意見；3 條 reason。\n")
    proc = _run(["--list", str(p)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "22 條" not in proc.stdout, "裸「條」不該命中：" + proc.stdout
    assert "十三條" not in proc.stdout, "裸「條」不該命中：" + proc.stdout


def test_drift_turns_red_against_baseline(tmp_path: Path) -> None:
    """ASSERT 數字改了而基準未更新 → rc=2（本閘的實際作用）。"""
    base_spec = _spec(tmp_path, "c1.md", "## X\n\nregister 共 29 條。\n")
    baseline = tmp_path / "baseline.txt"
    listed = _run(["--list", str(base_spec)])
    assert listed.returncode == 0, listed.stdout + listed.stderr
    baseline.write_text(listed.stdout, encoding="utf-8")

    # 未改 → 綠（mutation 自證：證明本閘非恆紅）
    same = _run(["--check", str(base_spec), "--baseline", str(baseline)])
    assert same.returncode == 0, same.stdout + same.stderr

    # 改成 30 條而基準仍是 29 → 紅
    drifted = _spec(tmp_path, "c1.md", "## X\n\nregister 共 30 條。\n")
    proc = _run(["--check", str(drifted), "--baseline", str(baseline)])
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "共 30 條" in proc.stderr, proc.stderr


def test_real_d002_form_is_no_longer_blind() -> None:
    """ASSERT 對真實的 `D-002` 不再零命中（改前實跑為空輸出）。

    端到端：防「規則寫了但對真實文件仍看不到」——此即本次發現的原始缺陷形態。
    """
    spec = REPO / "docs" / "SPLITUNIFY_SPEC.D-002.md"
    if not spec.exists():  # SPEC 移檔時不誤擋，但明確標示未驗
        import pytest

        pytest.skip(f"{spec} 不存在")
    proc = _run(["--list", str(spec)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "共 29 條" in proc.stdout, (
        "D-002 之 register 總數字面未被收入 ⇒ F2 對真實文件仍失明\n" + proc.stdout
    )
