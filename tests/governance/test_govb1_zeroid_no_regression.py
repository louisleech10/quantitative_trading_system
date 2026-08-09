"""GOVB1 Task 4.1 — `G-1` 三入口 × 三輸入交叉 oracle。

`G-1` 是**行為禁令而非路徑禁令**〔`CODEX-R2-P0-02`：路徑禁令擋不住等效改法〕：

> 禁止任何使 `C-2` 表中 8 列之 `rc` 由 `0` 變為非 `0` 的改動，**不論實作於哪一層**。

🔴 **本檔目前只閉合到兩欄，第三欄具名阻塞——不做假綠。**
第三欄（`cx_run` 交件路徑）在 Task 4.1 的檔案限制下**做不到**，成因與裁決請求見
`docs/GOV_B8_SCOPE_AMENDMENT.md` §4。本檔以 `test_cxrun_column_is_blocked_not_passing`
把該阻塞釘成**可見的斷言**：阻塞成因一旦消失（`cx_run.sh` 具備保留既有輸出的 stub 模式），
那條測試就會紅，逼下一手把第三欄補上，而不是讓它靜靜地不存在。
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS = REPO_ROOT / "scripts" / "completeness_check.sh"
CX_RUN = REPO_ROOT / "scripts" / "cx_run.sh"

# ---------------------------------------------------------------------------
# 三種輸入（與 SPEC §C-2／Task 4.1 驗證欄逐字對應）
# ---------------------------------------------------------------------------

INPUTS = {
    # ①0-ID 單行 heading probe：構造同 test_completeness_idlike_fp.py:102-105
    "single_heading_probe": "## OUT-OF-SCOPE\n",
    # ②prose-only 產出（完全沒有 canonical ID）
    "prose_only": "# 報告\n\n這一輪沒有可回報的項目，全部以散文敘述。\n",
    # ③hollow P3-00：sentinel 形態正確、標籤在、但標籤後**沒有內容**
    "hollow_p300": "## CODEX-R1-P3-00\n**斷言**:\n**碼證**:\n",
}


def _rc(args: list[str], *, env_extra: dict[str, str] | None = None) -> int:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    # 🔴 rc 直接取，禁經 pipe
    return subprocess.run(
        args, cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env
    ).returncode


# ---------------------------------------------------------------------------
# 欄 ①：completeness_check.sh --single（**已閉合**）
# ---------------------------------------------------------------------------

# 🔴 基準是**量到的**不是猜的（主委初版三格用猜的，其中一格就錯）。
#    Task 4.2 唯一許可的變更＝hollow_p300 由 0 → 非 0，屆時須同時改本表並附委員裁定。
SINGLE_BASELINE = {
    "single_heading_probe": 0,
    "prose_only": 0,
    "hollow_p300": 0,
}


@pytest.mark.parametrize("name", sorted(INPUTS))
def test_entry_single_rc_matches_baseline(name: str, tmp_path: Path) -> None:
    f = tmp_path / f"{name}.md"
    f.write_text(INPUTS[name], encoding="utf-8")
    got = _rc(["bash", str(COMPLETENESS), "--single", str(f), "--family", "codex"])
    assert got == SINGLE_BASELINE[name], (
        f"--single/{name} rc 由基準 {SINGLE_BASELINE[name]} 變成 {got}"
        "：若這是 Task 4.2 的許可變更，須同時改本檔基準並附委員裁定"
    )


def test_single_column_discriminates_between_inputs(tmp_path: Path) -> None:
    """🔴 反空轉：`--single` 這一欄若對任何輸入都給同一個 rc，它就沒有鑑別力。

    現況三格**確實都是 0**（這正是 Task 4.2 要改的病：hollow sentinel 現在過得去）。
    ⇒ 本測不要求 rc 相異，而是要求**至少一個非退化的對照**：
    一份**實質完整**的 finding 也必須是 0，而一份**結構壞掉**的必須非 0。
    這樣「三格全 0」才不是因為 `--single` 根本不看內容。
    """
    real = tmp_path / "real.md"
    real.write_text(
        "## CODEX-R1-P0-01\n**斷言**: 有實質內容的斷言。\n"
        "**碼證**: `bash x.sh` rc=2，可複驗。\n"
        # 🔴 `**來源摘要**` 須為 `<路徑>#<12 位雜湊>`；寫行號會 FAIL
        #    （出生事故：主委自己寫行號，4 個 P0/P1 全 FAIL）
        "**來源摘要**: scripts/x.sh#0123456789ab\n",
        encoding="utf-8",
    )
    assert _rc(["bash", str(COMPLETENESS), "--single", str(real), "--family", "codex"]) == 0

    broken = tmp_path / "broken.md"
    broken.write_text("## CODEX-RX-PZ-9\n**斷言**: x\n", encoding="utf-8")
    assert (
        _rc(["bash", str(COMPLETENESS), "--single", str(broken), "--family", "codex"]) != 0
    ), "畸形 canonical ID 竟然過關 ⇒ --single 這一欄沒有鑑別力，三格全 0 不具意義"


# ---------------------------------------------------------------------------
# 欄 ②：completeness_check.sh --lock（**具名阻塞**）
# ---------------------------------------------------------------------------


def test_lock_column_requires_real_reconcile_not_handcrafted() -> None:
    """🔴 `--lock` 欄具名阻塞：手搓 `sources.lock` 三格都是 rc=1，**與輸入無關**。

    主委初版手工組 lock JSON，三種輸入全部 rc=1——不是輸入造成的差異，
    而是 lock 本身缺 digest／body-hash 等欄位而**結構性失敗**。
    那樣的三格是**假的看守**：即使有人把判準改壞，三格照樣全 1，測試照樣綠。

    正確做法＝用 `scripts/reconcile_build.sh` 產生真實 lock 再灌三種輸入。
    該工具會在 `handoffs/reconcile/<session>/` 建立實體目錄，
    需要一個不汙染真實 session 空間的隔離方案 ⇒ 屬本欄未完成的具名工作。

    本測**刻意只斷言阻塞成因存在**（reconcile_build 是唯一合法造 lock 途徑），
    不假裝這一欄已經閉合。裁決請求見 docs/GOV_B8_SCOPE_AMENDMENT.md §4。
    """
    builder = REPO_ROOT / "scripts" / "reconcile_build.sh"
    assert builder.is_file(), "reconcile_build.sh 不存在 ⇒ 本欄的正確做法需重新評估"
    text = builder.read_text(encoding="utf-8", errors="replace")
    assert "sources.lock" in text, "reconcile_build 不再產 sources.lock ⇒ 本欄前提已變"


# ---------------------------------------------------------------------------
# 欄 ③：cx_run.sh 交件路徑（**具名阻塞**）
# ---------------------------------------------------------------------------


def test_cxrun_column_is_blocked_not_passing() -> None:
    """🔴 第三欄做不到的**成因**，釘成可見斷言。

    SPEC 要求對三種輸入各驗 `cx_run` 交件路徑的 `result_state`。
    但 `CX_STUB_MODE=success` 會呼叫 `_write_stub_success_output` **覆寫** `${out}`
    ⇒ 三種輸入根本傳不進交件路徑；而 `cx_run.sh` 在 Task 4.1 的檔案欄是
    **只讀（本 Task 不改）**，故無法新增「保留既有輸出」的 stub 模式。

    ⇒ 這一欄在本票的檔案限制下**不可達**，不是「忘了寫」。

    🔴 本測是**逼債條款**：一旦 `cx_run.sh` 具備保留既有輸出的 stub 模式
    （B10 的 `format-failed` 補救層很可能會加），本測即紅，
    逼下一手把第三欄真正補上，而不是讓缺口靜靜消失。
    """
    text = CX_RUN.read_text(encoding="utf-8", errors="replace")
    assert "_write_stub_success_output" in text, "stub 覆寫函式已改名 ⇒ 本阻塞成因須重新確認"
    preserving_modes = [m for m in ("preserve", "keep_output", "as_is") if m in text]
    assert not preserving_modes, (
        f"cx_run 已具備保留既有輸出的 stub 模式 {preserving_modes} ⇒ "
        "第三欄的阻塞成因消失，請立即補上三輸入 × result_state 矩陣"
    )


# ---------------------------------------------------------------------------
# G-1 的其餘機械驗收
# ---------------------------------------------------------------------------


def test_idlike_fp_test_file_is_untouched() -> None:
    """`git diff --stat tests/governance/test_completeness_idlike_fp.py` 須為空。

    改測試換綠即為違規（SPEC §C-2 機械驗收第 2 項）。
    """
    got = subprocess.run(
        ["git", "diff", "--stat", "tests/governance/test_completeness_idlike_fp.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert got.returncode == 0
    assert got.stdout.strip() == "", f"禁改該測試檔，卻有 diff:\n{got.stdout}"


def test_idlike_fp_suite_is_green() -> None:
    """`C-2` 機械驗收第 1 項：該測試檔全綠。"""
    got = subprocess.run(
        [
            "venv/bin/python",
            "-m",
            "pytest",
            "tests/governance/test_completeness_idlike_fp.py",
            "-q",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert got.returncode == 0, got.stdout[-2000:]


def test_task41_does_not_modify_readonly_files() -> None:
    """Task 4.1 的「只讀」欄：本批不得改動這些檔。"""
    readonly = [
        "scripts/completeness_check.sh",
        "scripts/cx_run.sh",
        "scripts/govflow_lifecycle.json",
        "tests/governance/test_completeness_idlike_fp.py",
    ]
    got = subprocess.run(
        ["git", "diff", "--stat", "--", *readonly],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert got.returncode == 0
    assert got.stdout.strip() == "", f"Task 4.1 只讀檔遭改動:\n{got.stdout}"
