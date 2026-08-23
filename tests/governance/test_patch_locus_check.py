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

import os
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
        # 🔴 R10：判準細分後，「當前內容與 diff hunk 皆找不到」歸類為**非字面**（委員責任）；
        #    「在內容中但不在 diff」才是「未改到」（主委責任）——見下一條測試。
        assert "anchor 非字面" in log, log
    finally:
        fixture.unlink(missing_ok=True)


def test_anchor_in_content_but_not_in_diff_is_red(tmp_path):
    """anchor **在當前內容中**但**不在本次 diff hunk** ⇒ rc=2，且訊息為「未改到」而非「非字面」。

    🔴 這是 R10 修正判準後的關鍵對照組：
    首版把兩種情形混為一談，導致「委員 anchor 引用被刪除之舊文字」被誤判成非字面。
    本條用獨立 tmp git repo：檔內兩段字面，只改其中一段，anchor 指未改的那段。
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*a):
        return subprocess.run(["git"] + list(a), cwd=str(repo),
                              capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    target = repo / "doc.md"
    target.write_text("SECTION_UNTOUCHED\nSECTION_EDITED old\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "init")
    target.write_text("SECTION_UNTOUCHED\nSECTION_EDITED new\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "edit")
    head_ts = int(git("log", "-1", "--format=%ct").stdout.strip())
    os.utime(str(target), (head_ts - 3600, head_ts - 3600))

    patch = tmp_path / "patch.md"
    patch.write_text(
        "# PATCH cluster test\nAUTHORITY: 測試用\nSYNC-LOCI:\n"
        "- doc.md#SECTION_UNTOUCHED\n"
        "BEFORE/AFTER: （略）\nVERIFY:\n- true\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(GATE), str(patch), "--diff-base", "HEAD~1"],
        capture_output=True, text=True, cwd=str(repo),
    )
    log = out.stdout + out.stderr
    assert out.returncode == 2, log
    assert "anchor 未出現在該檔之 diff hunk 內" in log, log
    assert "anchor 非字面" not in log, log


def test_anchor_quoting_deleted_text_is_green(tmp_path):
    """anchor 引用**被刪除**之舊文字 ⇒ 應為綠（它出現在 diff 之 `-` 行）。

    🔴 **主委首版此判準錯誤**：只查「當前內容」⇒ 委員在 BEFORE 段引用將被刪除之字面，
    套用後必然找不到，會被誤判「非字面」並誤歸委員責任。R10 十二份補丁包有十餘個
    anchor 因此假紅。本條為該修正之回歸樁；把判準退回「只查當前內容」⇒ 本條轉紅。
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*a):
        return subprocess.run(["git"] + list(a), cwd=str(repo),
                              capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    target = repo / "doc.md"
    target.write_text("OLD_CLAUSE_TO_BE_DELETED\nkeep\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "init")
    target.write_text("NEW_CLAUSE\nkeep\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "edit")
    head_ts = int(git("log", "-1", "--format=%ct").stdout.strip())
    os.utime(str(target), (head_ts - 3600, head_ts - 3600))

    patch = tmp_path / "patch.md"
    patch.write_text(
        "# PATCH cluster test\nAUTHORITY: 測試用\nSYNC-LOCI:\n"
        "- doc.md#OLD_CLAUSE_TO_BE_DELETED\n"
        "BEFORE/AFTER: （略）\nVERIFY:\n- true\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(GATE), str(patch), "--diff-base", "HEAD~1"],
        capture_output=True, text=True, cwd=str(repo),
    )
    log = out.stdout + out.stderr
    assert out.returncode == 0, "引用被刪除文字之 anchor 應為綠；輸出：%s" % log


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


# ────────────────────────────────────────────────────────────────────
# R9 新增：stage 維度／anchor 字面閘／CJK 路徑（quotepath）
# 出處＝CODEX-R9-P1-06（stage 由補丁包宣告）＋ GROK-R9-P1-04（quotepath 假紅）。
# ────────────────────────────────────────────────────────────────────


def _run_args(patch_path, *extra):
    out = subprocess.run(
        [sys.executable, str(GATE), str(patch_path)] + list(extra),
        capture_output=True, text=True, cwd=str(REPO),
    )
    return out.returncode, out.stdout + out.stderr


def test_descriptive_anchor_is_red_at_parse_time(tmp_path):
    """anchor 非字面（該檔內容找不到）⇒ 提交當下即 rc=2，屬委員責任。

    🔴 mutation guard：拿掉 parse 期之字面閘，本條會退化成
    「anchor 未出現在 diff hunk 內」而訊息不同 ⇒ 斷言訊息字面即可偵測。
    """
    fixture = REPO / "tests" / "governance" / "_tmp_locus_fixture.txt"
    fixture.write_text("內容含 ANCHOR_PRESENT_MARKER 這個字串。\n", encoding="utf-8")
    try:
        patch = _write_patch(
            tmp_path,
            ["- tests/governance/_tmp_locus_fixture.txt#檔頭之某段敘述性描述"],
        )
        rc, log = _run(patch)
        assert rc == 2, log
        assert "anchor 非字面" in log, log
    finally:
        fixture.unlink(missing_ok=True)


def test_impl_stage_locus_is_deferred_not_red(tmp_path):
    """未達之 `@impl` locus ⇒ DEFERRED、不計 rc（stage 由補丁包宣告）。

    對照組（下一條）：同一 locus 不標 stage（缺省 @spec）⇒ 必紅。
    兩條並存才能證明 DEFERRED 不是「全部放行」。
    """
    patch = _write_patch(
        tmp_path,
        ["- api/models/ic_models.py#ICAnalyzeRequest@impl"],
    )
    rc, log = _run(patch)
    assert rc == 0, "標 @impl 之未達 locus 不應計 rc；輸出：%s" % log
    assert "DEFERRED" in log, log


def test_unstaged_locus_defaults_to_spec_and_is_red(tmp_path):
    """未標 stage ⇒ 缺省 `@spec` ⇒ 未達即紅（證明預設值是最嚴的那個）。"""
    patch = _write_patch(
        tmp_path,
        ["- api/models/ic_models.py#ICAnalyzeRequest"],
    )
    rc, log = _run(patch)
    assert rc == 2, "缺省 stage 應為 spec 而必紅；輸出：%s" % log
    assert "[@spec]" in log, log


def test_also_impl_widens_and_turns_impl_red(tmp_path):
    """`--also-impl` 只**加寬**：同一 @impl locus 加旗標後轉紅。"""
    patch = _write_patch(
        tmp_path,
        ["- api/models/ic_models.py#ICAnalyzeRequest@impl"],
    )
    rc, log = _run_args(patch, "--also-impl")
    assert rc == 2, "--also-impl 應使 @impl 計入 rc；輸出：%s" % log
    assert "[@impl]" in log, log




def test_cjk_path_with_diff_base_is_recognised(tmp_path):
    """**tracked** 之 CJK 路徑在 `--diff-base` 路徑下不得被 quotepath 咬成假紅。

    🔴 GROK-R9-P1-04 之回歸樁。**首版此測試是假綠**（主委自查發現）：
    首版用 repo 內**未追蹤**之 CJK fixture，而未追蹤檔走的是
    `git status --porcelain -z`——`-z` 本來就不做 quoting ⇒ 拿掉
    `core.quotepath=false` 也不會轉紅。**真正會被咬的是 `git diff --name-only <base>`**。
    ⇒ 改為在 tmp_path 建**獨立 git repo**：commit 一個 CJK 路徑檔、改它、再以
    `--diff-base HEAD` 對證。自帶 fixture、不依賴本 repo 之歷史或髒污狀態。

    mutation：把 `_git` 之 `-c core.quotepath=false` 拿掉 ⇒ 本條必紅。
    """
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    def git(*a):
        return subprocess.run(["git"] + list(a), cwd=str(repo),
                              capture_output=True, text=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    target = repo / "白話說明" / "中文檔.md"
    target.parent.mkdir(parents=True)
    target.write_text("第一版\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "init")
    target.write_text("第一版\nANCHOR_AFTER_EDIT\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "edit")
    # 🔴 **必須把 mtime 壓到 HEAD commit 時間之前**，否則 `is_touched()` 的
    #    mtime 回退（給 gitignore 檔用的）會讓本測試在 quotepath 壞掉時仍然綠——
    #    主委首兩版此測試都因此假綠，第三版才真的能被 mutation 打紅。
    head_ts = int(git("log", "-1", "--format=%ct").stdout.strip())
    os.utime(str(target), (head_ts - 3600, head_ts - 3600))

    patch = tmp_path / "patch.md"
    patch.write_text(
        "# PATCH cluster test\nAUTHORITY: 測試用\nSYNC-LOCI:\n"
        "- 白話說明/中文檔.md#ANCHOR_AFTER_EDIT\n"
        "BEFORE/AFTER: （略）\nVERIFY:\n- true\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(GATE), str(patch), "--diff-base", "HEAD~1"],
        capture_output=True, text=True, cwd=str(repo),
    )
    log = out.stdout + out.stderr
    assert "檔案未被本次改動" not in log, "CJK 路徑被 quotepath 咬成假紅：%s" % log
    assert out.returncode == 0, log
