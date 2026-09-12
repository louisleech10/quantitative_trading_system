"""DOCROT R2 之 F2（窄版計數字面閘）— 只收「共 N 條」語型。

病根（2026-09-12 DOCROT consult R1/R2 三家一致）：同一個數字寫在兩個地方，
改一處漏一處。碼證：`docs/SPLITUNIFY_SPEC.D-002.md:70`「register 共 29 條」
與 `:90` 表標題「共 29 條」並存；而 `scripts/spec_count_audit.py` 原第 51 行
逐字「刻意排除『條』」⇒ 對該形態**零命中**（改前實跑 `--list` 對 D-002 輸出為空）。

三家指定的是**窄版**：只數「共 N 條」，不是把所有「條」納入。本檔同時驗
「有抓到」與「沒擴大」——後者防的是把閘改成噪音製造機（收窄失敗即紅）。
"""

from __future__ import annotations

import os
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


# ── --dupes：同一計數字面出現在多行（R2 第 3 項掛載之 warn-only 形態）─────────


def test_dupes_flags_same_literal_on_two_lines(tmp_path: Path) -> None:
    """ASSERT 同一「共 N 條」寫在兩行 → 被指出，且逐行號列出。

    這正是 `--list`／`--check` 看不見的形態（集合比對會去重）。
    """
    p = _spec(
        tmp_path,
        "dup.md",
        "### 節標題（register 共 29 條）\n\n內文敘述。\n\n#### 表標題（共 29 條）\n",
    )
    proc = _run(["--dupes", str(p)])
    assert proc.returncode == 0, proc.stdout + proc.stderr  # warn-only，不擋
    assert "共 29 條" in proc.stderr, proc.stderr
    assert "1,5" in proc.stderr, "應逐行號列出兩處落點：" + proc.stderr


def test_dupes_silent_when_single_source(tmp_path: Path) -> None:
    """ASSERT 只寫一處 → 不出聲（mutation 自證：證明不是恆叫）。"""
    p = _spec(
        tmp_path,
        "single.md",
        "### 節標題（register 見 (5.6)）\n\n#### 表標題（共 29 條）\n",
    )
    proc = _run(["--dupes", str(p)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "共 29 條" not in proc.stderr, "單一真相源不該被指出：" + proc.stderr


def test_dupes_ignores_history_section(tmp_path: Path) -> None:
    """ASSERT 沿革段內的舊字面不算第二個真相源。

    F1 活文收縮的做法就是把考古逐字搬進 HISTORY；若沿革也計入，每搬一次就永久
    多一條誤報，閘會變成自己製造噪音的來源。實測 `D-002` 收斂後仍被指出
    「共 29 條 @ 行 90,365」，其中 365 正是我搬進沿革的引文——本條防的就是它。
    """
    p = _spec(
        tmp_path,
        "hist.md",
        "#### 表標題（共 29 條）\n\n"
        "## 沿革與追溯索引\n\n"
        "<!-- HISTORY-BEGIN -->\n"
        "- 原寫「共 29 條」，已改為指向 register。\n"
        "<!-- HISTORY-END -->\n",
    )
    proc = _run(["--dupes", str(p)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "共 29 條" not in proc.stderr, (
        "沿革引文被當成重複真相源 ⇒ 每次活文收縮都會留永久誤報\n" + proc.stderr
    )


def test_hook_emits_dupes_warning_without_blocking() -> None:
    """ASSERT 產出端 hook 會出重複計數的警告，且**不因此擋門**。

    R2 第 3 項要求掛三層，第 4 項要求第一期只 warn。本條同時釘住兩件事：
    警告真的出得來（不是掛了沒效），以及它不改 hook 的 rc（不是偷偷升成擋門）。
    走 hook 自帶的 GOVERNANCE_TEST_HARNESS 模式，不偽造 stdin。
    """
    hook = REPO / "scripts" / "spec_xref_hook.sh"
    # 檔名須落在 hook 的觸發集合（docs/*SPEC*.md）；HEAD 無此檔 ⇒ 殘留掃描跳過，
    # 亦無 synth 宣告它 ⇒ 兩道硬檢查都不跑，rc 只可能來自本次新增的警告層。
    probe = REPO / "docs" / ".tmp-docrot-dupes-probe_SPEC.md"
    probe.write_text(
        "### 節標題（register 共 41 條）\n\n#### 表標題（共 41 條）\n",
        encoding="utf-8",
    )
    try:
        proc = subprocess.run(
            ["bash", str(hook)],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO),
            env={
                **os.environ,
                "GOVERNANCE_TEST_HARNESS": "1",
                "SPEC_XREF_HOOK_TARGET": str(probe),
            },
        )
        assert "共 41 條" in proc.stderr, (
            "產出端警告層沒有出聲 ⇒ 掛了等於沒掛\n" + proc.stdout + proc.stderr
        )
        assert proc.returncode == 0, (
            "warn-only 層竟然改了 hook 的 rc ⇒ 第一期只 warn 的約定被破壞\n"
            + proc.stdout
            + proc.stderr
        )
    finally:
        if probe.exists():
            probe.unlink()


def test_dupes_is_warn_only_never_blocks(tmp_path: Path) -> None:
    """ASSERT 即使命中也 rc=0——第一期只 warn，不得擋門。

    若日後要升成擋門，本條會轉紅，逼迫改動者先處理「閾值與誤擋面未校準」那筆殘留。
    """
    p = _spec(tmp_path, "many.md", "共 3 條\n共 3 條\n共 3 條\n")
    proc = _run(["--dupes", str(p)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
