"""session 命名守衛的接線測試。

為何存在（2026-08-06）：
    `committee_run.sh` 對 `session_name_check.sh` 採「檔案不存在則跳過」，
    理由是 governance 測試以精選腳本清單建隔離 repo 且刻意用合成 session 名
    （改 11 個測試檔的名稱屬溯及既往且零收益）。

    但「不存在則跳過」帶來一個新風險：**刪掉該檔，強制就靜默失效**。
    本測試即為該風險的機械擋門——斷言檔案存在、可執行、且確實被呼叫。

誠實邊界：本測試只驗「接線在」，不驗「判準對」；判準的可證偽性由
    `.claude/tmp/probe_name.sh` 的 11 案例（合規 5 放行／違規 6 擋下）涵蓋。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / "scripts" / "session_name_check.sh"
CALLER = REPO_ROOT / "scripts" / "committee_run.sh"


def test_guard_script_exists_and_executable() -> None:
    """守衛本體須存在且可執行——否則 committee_run 會靜默跳過強制。"""
    assert GUARD.is_file(), f"命名守衛不存在: {GUARD}"
    assert GUARD.stat().st_mode & 0o111, f"命名守衛不可執行: {GUARD}"


def test_committee_run_invokes_guard() -> None:
    """派工路徑須真的呼叫守衛（僅存在不夠）。"""
    src = CALLER.read_text(encoding="utf-8")
    assert "session_name_check.sh" in src, "committee_run.sh 未呼叫命名守衛"


def test_guard_rejects_legacy_name_and_accepts_conforming() -> None:
    """守衛須具鑑別力：舊式名擋下、合規名放行。

    以本 repo 實際用過的舊名為反例（非杜撰），確保不是恆真斷言。
    """
    bad = subprocess.run(
        ["bash", str(GUARD), "--session", "20260805-govb0-b3-fixreview"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert bad.returncode != 0, f"舊式名應被擋下: {bad.stdout}{bad.stderr}"

    good = subprocess.run(
        [
            "bash",
            str(GUARD),
            "--session",
            "20260806-govb0-b35-review-r1",
            "--task-id",
            "20260806-GOVB0-B35-REVIEW-R1",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert good.returncode == 0, f"合規名應放行: {good.stdout}{good.stderr}"
