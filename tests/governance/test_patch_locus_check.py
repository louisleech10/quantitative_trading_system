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


def _write_patch(tmp_path, loci_lines, *, authority=True, verify=True, before_after="（略）"):
    """🔴 R11：`before_after` 是**弱證據之意圖來源**。

    弱證據（anchor 只在刪除行／未追蹤檔之全檔 fallback）須額外要求 anchor 出現在
    **SYNC-LOCI 以外**之補丁包正文；`_write_patch` 預設之「（略）」不含任何 anchor，
    因此弱證據案例必須顯式傳入 `before_after`，否則應為紅——這正是新規則的用意。
    """
    body = ["# PATCH cluster test"]
    if authority:
        body.append("AUTHORITY: 測試用")
    body.append("SYNC-LOCI:")
    body.extend(loci_lines)
    body.append("BEFORE/AFTER: " + before_after)
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


def test_anchor_quoting_deleted_text_is_green(tmp_path):  # R11：已加意圖佐證，見 _write_patch
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
        "BEFORE/AFTER: 刪除 OLD_CLAUSE_TO_BE_DELETED，改為 NEW_CLAUSE\n"
        "VERIFY:\n- true\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(GATE), str(patch), "--diff-base", "HEAD~1"],
        capture_output=True, text=True, cwd=str(repo),
    )
    log = out.stdout + out.stderr
    assert out.returncode == 0, "引用被刪除文字之 anchor 應為綠；輸出：%s" % log


def test_anchor_present_is_green(tmp_path):
    """anchor 確實出現在該檔內容中 ⇒ rc=0（正例，防「恆紅」型假保證）。

    🔴 R11：此 fixture 為**未追蹤檔**，走 `weak_full` 全檔 fallback（弱證據）
    ⇒ 須在 BEFORE/AFTER 附上該 anchor 之意圖佐證。對照組見
    `test_untracked_full_fallback_without_intent_is_red`。
    """
    fixture = REPO / "tests" / "governance" / "_tmp_locus_fixture.txt"
    fixture.write_text("內容含 ANCHOR_PRESENT_MARKER 這個字串。\n", encoding="utf-8")
    try:
        patch = _write_patch(
            tmp_path,
            ["- tests/governance/_tmp_locus_fixture.txt#ANCHOR_PRESENT_MARKER"],
            before_after="把 ANCHOR_PRESENT_MARKER 這一段改寫成新內容",
        )
        rc, log = _run(patch)
        assert rc == 0, "anchor 在內容中卻回 rc=%d；輸出：%s" % (rc, log)
        assert "全部被改到" in log, log
    finally:
        fixture.unlink(missing_ok=True)


def test_empty_sync_loci_is_red(tmp_path):  # R11：與 malformed-line 反測同屬格式 fail-closed 家族
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


def test_bracket_stage_suffix_is_parsed_not_part_of_anchor(tmp_path):
    """`[@impl]`（方括號形、無前置空白）須與 `@impl` 同解析。

    出處（R17）：brief 之格式行寫作 `- <檔>#<錨點>[@spec|@doc|@harness|@impl]`，
    方括號在該行是「可選」之標記；三家委員合理地照字面寫成 `#錨點[@spec]`。
    舊 regex 只吃 `\\s*@stage$` ⇒ `[@spec]` 被併入 anchor ⇒ 該 anchor 永遠 grep 不到
    ＝**假紅**（22 個 locus 一次全中）。

    可證偽性：若解析回退（把 `[@impl]` 當 anchor 的一部分），本條之 rc 會變成 2
    ——因為缺省 stage 是最嚴的 `@spec`，未達即紅。
    """
    patch = _write_patch(
        tmp_path,
        ["- api/models/ic_models.py#ICAnalyzeRequest[@impl]"],
    )
    rc, log = _run(patch)
    assert rc == 0, "`[@impl]` 應被解析為 stage 而非 anchor 之一部分；輸出：%s" % log
    assert "DEFERRED" in log, log
    assert "[@impl]" not in log.split("←")[0], "anchor 不應仍夾帶 `[@impl]`：%s" % log


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




def test_cjk_path_with_diff_base_is_recognised(tmp_path):  # R11：本檔另有弱證據系列反測
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


# ────────────────────────────────────────────────────────────────────
# R11：SYNC-LOCI 格式截斷／弱證據須有委員意圖佐證
# 出處＝CODEX-R11-P1-09（malformed 行截斷解析）
#      ＋COMPOSER-R11-P1-03（無關刪除行假綠）
#      ＋GROK-R11-P1-06（未追蹤檔全檔 fallback，零改動亦綠）
# ────────────────────────────────────────────────────────────────────


def test_malformed_loci_line_is_red_and_does_not_truncate(tmp_path):
    """`- 合法` / `MALFORMED` / `- 缺失` ⇒ rc=2，且**後續 locus 不得被靜默丟棄**。

    🔴 mutation guard：把非法行改回靜默 `in_loci = False`（首版行為）⇒
    本條會變成「只解析到第一條、rc=0」而轉綠。
    """
    fixture = REPO / "tests" / "governance" / "_tmp_locus_fixture.txt"
    fixture.write_text("內容含 FIRST_VALID_ANCHOR 這個字串。\n", encoding="utf-8")
    try:
        patch = _write_patch(
            tmp_path,
            [
                "- tests/governance/_tmp_locus_fixture.txt#FIRST_VALID_ANCHOR",
                "MALFORMED_LOCUS_LINE",
                "- tests/governance/__no_such_file__.md#MISSING_REQUIRED_LOCUS",
            ],
            before_after="改寫 FIRST_VALID_ANCHOR 與 MISSING_REQUIRED_LOCUS",
        )
        rc, log = _run(patch)
        assert rc == 2, "malformed 行未 fail-closed；輸出：%s" % log
        assert "SYNC-LOCI 內有非法行" in log, log
    finally:
        fixture.unlink(missing_ok=True)


def test_unrelated_deleted_line_without_intent_is_red(tmp_path):
    """anchor 只出現在**無關**之刪除行、且補丁包正文未提及 ⇒ rc=2。

    情境：同檔改 A 段、刪掉恰含該 anchor 字面的 B 段。R10 版「OR diff hunk」會綠。
    🔴 mutation guard：拿掉「弱證據須有意圖佐證」⇒ 本條轉綠。
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
    target.write_text("A_SECTION old\nUNRELATED_ANCHOR_TEXT\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "init")
    # 改 A 段、順手刪掉含 anchor 字面的無關那行
    target.write_text("A_SECTION new\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "edit")
    head_ts = int(git("log", "-1", "--format=%ct").stdout.strip())
    os.utime(str(target), (head_ts - 3600, head_ts - 3600))

    patch = tmp_path / "patch.md"
    patch.write_text(
        "# PATCH cluster test\nAUTHORITY: 測試用\nSYNC-LOCI:\n"
        "- doc.md#UNRELATED_ANCHOR_TEXT\n"
        "BEFORE/AFTER: 只改 A_SECTION，完全沒提要動那一行\n"
        "VERIFY:\n- true\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(GATE), str(patch), "--diff-base", "HEAD~1"],
        capture_output=True, text=True, cwd=str(repo),
    )
    log = out.stdout + out.stderr
    assert out.returncode == 2, "無關刪除行仍被當成改到；輸出：%s" % log
    assert "弱證據" in log, log


def test_untracked_full_fallback_without_intent_is_red(tmp_path):
    """未追蹤檔之全檔 fallback（零內容改動）且補丁包正文未提及 ⇒ rc=2。

    🔴 GROK-R11-P1-06 之回歸樁：該檔只要 mtime 比 HEAD 新就被判 touched，
    再把全檔當新增 ⇒ 檔內既有字面在**沒有任何改動**下也會通過。
    對照組＝`test_anchor_present_is_green`（有意圖佐證 ⇒ 綠）。
    """
    fixture = REPO / "tests" / "governance" / "_tmp_locus_fixture.txt"
    fixture.write_text("內容含 ANCHOR_PRESENT_MARKER 這個字串。\n", encoding="utf-8")
    try:
        patch = _write_patch(
            tmp_path,
            ["- tests/governance/_tmp_locus_fixture.txt#ANCHOR_PRESENT_MARKER"],
        )  # before_after 預設「（略）」＝無意圖佐證
        rc, log = _run(patch)
        assert rc == 2, "全檔 fallback 在無意圖佐證下仍綠；輸出：%s" % log
        assert "弱證據" in log, log
    finally:
        fixture.unlink(missing_ok=True)


def test_sync_loci_section_is_not_its_own_intent_evidence(tmp_path):
    """意圖佐證**不得**取自 SYNC-LOCI 區段本身（否則恆真、補強變假綠）。

    本條與上一條的差別只有「anchor 是否出現在 BEFORE/AFTER」；
    若實作把整份 patch 當意圖來源，兩條會同時綠 ⇒ 補強機制失效。
    """
    fixture = REPO / "tests" / "governance" / "_tmp_locus_fixture.txt"
    fixture.write_text("內容含 ONLY_IN_LOCI_LINE 這個字串。\n", encoding="utf-8")
    try:
        patch = _write_patch(
            tmp_path,
            ["- tests/governance/_tmp_locus_fixture.txt#ONLY_IN_LOCI_LINE"],
            before_after="這段完全沒有提到那個錨點字面",
        )
        rc, log = _run(patch)
        assert rc == 2, "SYNC-LOCI 自身被當成意圖佐證（恆真假綠）；輸出：%s" % log
    finally:
        fixture.unlink(missing_ok=True)
