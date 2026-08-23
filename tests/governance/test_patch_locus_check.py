# -*- coding: utf-8 -*-
"""patch_locus_check 之回歸測試（CODEX-R8-P1-06 指定之 new-regression-fixtures）。

病根：該閘首版只以「dirty worktree 之**檔名**集合」判定 locus
⇒ 同檔之無關修改、或該檔本來就 dirty，即可被誤算為「補丁已套用」。
主委當時在 HANDOFF／角色卡以「diff 觸及集合 ⊇ SYNC-LOCI」描述其強度，
**該描述高於實際能力**（codex 命中）。

本檔釘住三件事：
  1. anchor 未出現在 diff hunk 內 ⇒ 必紅（同檔無關行變更不得滿足 anchor）
  2. SYNC-LOCI 為空 ⇒ 必紅（空對空恆綠是假綠）
  3. 缺 AUTHORITY／VERIFY 欄 ⇒ 必紅（補丁包格式不合）

以及一條正例：anchor 確實出現在 diff 內 ⇒ rc=0。

🔴 測試設計說明（防假綠）：三條反測皆為「改壞就紅」形態——
若把 anchor 比對拿掉（退回首版之檔名比對），第 1 條必轉綠 ⇒ 該測試即失去意義。
故第 1 條同時是本次強度升級之 mutation guard。
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "patch_locus_check.py"


def _run(patch_path, cwd=None):
    out = subprocess.run(
        [sys.executable, str(GATE), str(patch_path)],
        capture_output=True, text=True, cwd=str(cwd or REPO),
    )
    return out.returncode, out.stdout + out.stderr


def _write_patch(tmp_path, loci_lines, *, authority=True, verify=True):
    body = ["# PATCH cluster test"]
    if authority:
        body.append("AUTHORITY: 測試用")
    body.append("SYNC-LOCI:")
    body.extend(loci_lines)
    body.append("BEFORE/AFTER: （略）")
    if verify:
        body.append("VERIFY:")
        body.append("- true")
    p = tmp_path / "patch.md"
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    return p


def test_anchor_not_in_diff_is_red(tmp_path):
    """anchor 未出現在該檔 diff hunk 內 ⇒ rc=2。

    🔴 本條同時是「檔名比對 → anchor 比對」升級之 mutation guard：
    若退回首版（只比檔名），本條會轉綠。

    🔴 **測試須自帶 fixture、不得依賴 repo 之髒污狀態**：
    首版用 `scripts/patch_locus_check.py` 當 locus，前提是「該檔此刻是 dirty」——
    commit 之後該前提消失、測試轉紅。這是測試設計缺陷（依賴外部狀態），
    已改為在 repo 內建一個**未追蹤**之 fixture 檔（未追蹤即視為本次改動），
    再給一個不存在於其內容中的 anchor。
    """
    fixture = REPO / "tests" / "governance" / "_tmp_locus_fixture.txt"
    fixture.write_text("這是 fixture 內容，不含目標錨點。\n", encoding="utf-8")
    try:
        patch = _write_patch(
            tmp_path,
            ["- tests/governance/_tmp_locus_fixture.txt#__ANCHOR_THAT_DOES_NOT_EXIST__"],
        )
        rc, log = _run(patch)
        assert rc == 2, "anchor 不在內容中卻回 rc=%d；輸出：%s" % (rc, log)
        assert "anchor 未出現在該檔之 diff hunk 內" in log, log
    finally:
        fixture.unlink(missing_ok=True)


def test_anchor_present_is_green(tmp_path):
    """anchor 確實出現在該檔內容中 ⇒ rc=0（正例，防「恆紅」型假保證）。"""
    fixture = REPO / "tests" / "governance" / "_tmp_locus_fixture.txt"
    fixture.write_text("內容含 ANCHOR_PRESENT_MARKER 這個字串。\n", encoding="utf-8")
    try:
        patch = _write_patch(
            tmp_path,
            ["- tests/governance/_tmp_locus_fixture.txt#ANCHOR_PRESENT_MARKER"],
        )
        rc, log = _run(patch)
        assert rc == 0, "anchor 在內容中卻回 rc=%d；輸出：%s" % (rc, log)
        assert "全部被改到" in log, log
    finally:
        fixture.unlink(missing_ok=True)


def test_empty_sync_loci_is_red(tmp_path):
    """SYNC-LOCI 為空 ⇒ rc=2（空對空恆綠是假綠）。"""
    patch = _write_patch(tmp_path, [])
    rc, log = _run(patch)
    assert rc == 2
    assert "SYNC-LOCI 欄為空" in log


def test_missing_authority_field_is_red(tmp_path):
    """缺 AUTHORITY 欄 ⇒ rc=2（補丁包格式不合）。"""
    patch = _write_patch(
        tmp_path, ["- scripts/patch_locus_check.py#changed_files"], authority=False
    )
    rc, log = _run(patch)
    assert rc == 2
    assert "缺 AUTHORITY 欄" in log


def test_missing_verify_field_is_red(tmp_path):
    """缺 VERIFY 欄 ⇒ rc=2。"""
    patch = _write_patch(
        tmp_path, ["- scripts/patch_locus_check.py#changed_files"], verify=False
    )
    rc, log = _run(patch)
    assert rc == 2
    assert "缺 VERIFY 欄" in log


def test_nonexistent_patch_file_is_red(tmp_path):
    """補丁包不存在 ⇒ rc=2（fail-closed，不得靜默通過）。"""
    rc, log = _run(tmp_path / "no_such_patch.md")
    assert rc == 2
    assert "補丁包不存在" in log
