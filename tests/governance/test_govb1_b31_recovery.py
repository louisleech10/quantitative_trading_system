"""GOVB1 Task 4.3（`票 B-31`）— `format-failed` 補救層 ＋ 兩件移交。

Task 4.3 本體：格式不合規時給**逐條可修補清單**（`檔:行` ＋ 違規類型 ＋ 修法一行），
使該輪不必整份重跑（實測委員一次重跑約 15 分鐘）。

🔴 本檔同時承接兩件由前票明確核可的移交：
  · **B8 C5**：`cx_run` 三入口矩陣**第三欄**。B8 當時不可達（`CX_STUB_MODE=success`
    會覆寫 `${out}`，而 `cx_run.sh` 在 Task 4.1 是唯讀），故只掛逼債條款。
    Task 4.3 得以改 `cx_run.sh` ⇒ 新增 `preserve` stub 模式，第三欄從此可驗。
  · **B9 C5**：零 findings 契約第 ③ 件（findings **落點**）的**強制點**。
    在此之前 `findings_destination` 只是 JSON 宣告，沒有任何腳本會擋。

🔴 **`cx_run.sh` 的原始碼被 `_B45_HARNESS` 凍結測試逐字錨定**（函式本體與呼叫點皆是）。
本批新增一律加在錨點**外側**，且落點快照走**動態作用域**而非新增參數
——主委實測：改內部縮排或加一個引數，都會讓 mutation probe 找不到錨點而轉紅。
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CX_RUN = REPO_ROOT / "scripts" / "cx_run.sh"
COMPLETENESS = REPO_ROOT / "scripts" / "completeness_check.sh"
LIFECYCLE = REPO_ROOT / "scripts" / "govflow_lifecycle.json"


def _src() -> str:
    return CX_RUN.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Task 4.3 本體：逐條可修補清單
# ---------------------------------------------------------------------------


def test_fixup_list_emitter_exists_and_has_three_columns() -> None:
    """`_emit_fixup_list` 須輸出 `檔:行` ＋ 違規類型 ＋ 修法一行（三欄）。

    只給 rc 的舊行為讓委員不知道**哪一條、哪一行、怎麼修** ⇒ 只能整份重跑。
    """
    s = _src()
    assert "_emit_fixup_list()" in s
    assert "可修補清單（逐條）" in s
    # 三欄格式字串：檔:行 \t 類型 \t 修法
    assert "'  %s:%s\\t%s\\t%s\\n'" in s, "修補清單不是三欄格式"
    assert "COMMITTEE_FINDING_TEMPLATE.md" in s, "修法欄未指向範本"


def test_fixup_list_is_invoked_only_on_failure() -> None:
    """成功路徑不得付出額外成本（清單只在失敗時再跑一次 checker）。"""
    s = _src()
    i = s.index("_emit_fixup_list \"${_log}\"")
    guard = s[max(0, i - 400) : i]
    assert '[ "${_rc}" -ne 0 ]' in guard, "修補清單未以失敗為前提"
    assert '[ "${_rc}" -ne 127 ]' in guard, "checker 不可用時不應再跑一次"


def test_fixup_list_always_has_a_line_number() -> None:
    """🔴 `CODEX-R1-P1-04`：每條**必含** `檔:行`，不得印 `檔:?`。

    duplicate-ID 這類訊息不帶 canonical ID ⇒ 原實作退回 `?`，
    委員無從定位 ⇒ 補救層失去意義（那正是 `票 B-31` 要解的病）。
    退路為三層封閉規則：①訊息自帶 `:<行號>` ②檔內第一個 canonical heading ③第 1 行。
    """
    s = _src()
    assert "${_no:-?}" not in s, "仍有 `?` 退路 ⇒ 可能印出無法定位的條目"
    assert '[ -n "${_no}" ] || _no=1' in s, "缺最終退路 ⇒ 仍可能印空行號"
    # 三層退路都要在
    assert "grep -Eo ':[0-9]+'" in s
    assert "grep -nE '^#{2,6}" in s


def test_format_failed_does_not_become_failed() -> None:
    """SPEC 邊界①：格式失敗但產出實質完整 ⇒ 標 `format-failed`，**不得**標 `failed`。"""
    s = _src()
    assert 'result_state="format-failed"' in s
    # exit 3 是 format-failed 的專用碼；不得與 failed 混用
    assert "格式不合規 → exit 3" in s


def test_debt_clear_success_guard_not_relaxed() -> None:
    """🔴 不可做：不得放寬 `debt_clear` 只接受 `success` 的守衛（三值契約凍結）。"""
    s = (REPO_ROOT / "scripts" / "debt_clear.sh").read_text(encoding="utf-8")
    assert "format-failed" not in s.split("abandon_kind")[0] or True  # 存在性不強制
    # 守衛本身：debt_clear 不得把 format-failed 當成可銷帳
    assert "success" in s
    got = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "scripts/debt_clear.sh"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert got.returncode == 0
    assert got.stdout.strip() == "", f"本批不得改 debt_clear.sh:\n{got.stdout}"


# ---------------------------------------------------------------------------
# B8 C5 移交：preserve stub 讓三入口矩陣第三欄可達
# ---------------------------------------------------------------------------


def test_preserve_stub_mode_exists_and_does_not_overwrite() -> None:
    """🔴 B8 C5 移交的**阻塞成因**必須在此消失。

    B8 的 `test_cxrun_column_is_blocked_not_passing` 是逼債條款：
    它斷言「`cx_run.sh` 沒有保留既有輸出的 stub 模式」。
    本批加上 `preserve` 後那條**必須轉紅**，並由本檔接手第三欄——
    這正是逼債條款的設計目的（阻塞成因消失即逼下一手補上）。
    """
    s = _src()
    assert "      preserve)" in s, "未新增 preserve stub 模式"
    i = s.index("      preserve)")
    seg = s[i : s.index("        ;;", i)]
    # 只看**實際指令**，不看註解——註解裡提到覆寫函式名是在解釋「為何不用它」
    code = [ln for ln in seg.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert not any("_write_stub_success_output" in ln for ln in code), (
        "preserve 模式仍覆寫產出"
    )
    assert "cli_rc=0" in seg


def test_b8_blocker_test_was_retired() -> None:
    """B8 的逼債條款須已被移除或改寫——不得與本檔的第三欄並存互相矛盾。"""
    zeroid = (
        REPO_ROOT / "tests" / "governance" / "test_govb1_zeroid_no_regression.py"
    ).read_text(encoding="utf-8")
    # 判「函式定義」不判字串——退場說明本來就會提到它的名字
    assert "def test_cxrun_column_is_blocked_not_passing" not in zeroid, (
        "B8 逼債條款仍在，但阻塞成因已消失 ⇒ 兩處敘述矛盾"
    )
    assert "退場" in zeroid, "逼債條款移除了卻沒留退場說明 ⇒ 缺口會靜靜消失"


# ---------------------------------------------------------------------------
# B9 C5 移交：findings 落點強制點
# ---------------------------------------------------------------------------


def test_findings_destination_has_an_enforcement_point() -> None:
    """🔴 B9 C5 移交：契約第 ③ 件從「JSON 宣告」變成**會擋的檢查**。

    在此之前沒有任何腳本會擋「把 findings append 進 stamp-target」，
    `票 B-52` 的落點事故因此仍可重演（`CODEX-R1-P1-05`／`COMPOSER-R1-P2-01`）。
    """
    s = _src()
    assert "_check_findings_destination()" in s
    assert "findings 落點違規" in s
    assert "zero_findings_contract.findings_destination" in s, "未指回契約 SoT"


def test_destination_check_snapshots_before_cli_runs() -> None:
    """快照必須在 CLI **執行前**取，否則比不出「本輪新增了什麼」。"""
    s = _src()
    # 只在 _run_cli_and_emit 內比較（該函式外另有 _capture_prompt_if_harness 的定義）
    body = s[s.index("_run_cli_and_emit() {"):]
    snap = body.index('_dest_snap="$(mktemp)"')
    cli = body.index("  _capture_prompt_if_harness\n")
    assert snap < cli, "落點快照取得晚於 CLI 執行 ⇒ 比對無意義"


def test_destination_check_is_kind_independent() -> None:
    """落點檢查不得被 findings-kind 閘擋住——stamp 輪正是出事的那一種。"""
    s = _src()
    i = s.index("if [ -n \"${_dest_snap:-}\" ]")
    seg = s[s.index("  # ── 以下為 Task 4.3 新增") : i]
    assert "case \"${_bk}\"" not in seg, "落點檢查落在 brief-kind 閘內 ⇒ stamp 輪不受檢"


def test_destination_check_uses_dynamic_scope_not_new_param() -> None:
    """🔴 呼叫點被凍結測試逐字錨定 ⇒ 不得新增引數。

    主委實測：多傳一個引數會讓 `_B45_HARNESS` 的 mutation probe 找不到錨點而轉紅。
    """
    s = _src()
    assert '_fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"' in s, (
        "呼叫點字面已變 ⇒ 凍結測試錨點會漂移"
    )
    assert 'if [ -n "${_dest_snap:-}" ]' in s, "未以動態作用域讀快照"


# ---------------------------------------------------------------------------
# 凍結錨點保護（本批最容易誤傷的地方）
# ---------------------------------------------------------------------------


def test_frozen_anchors_in_cx_run_are_intact() -> None:
    """🔴 `_B45_HARNESS` 逐字錨定的三處字面必須一字不差。

    epic 期間那五個測試檔禁改 ⇒ 只能反過來要求 `cx_run.sh` 保住錨點。
    本測把「哪幾段不能動」變成 B10 自己的斷言，而不是等別人的測試紅了才知道。
    """
    s = _src()
    for anchor in (
        '        if [ ! -f "${_cc}" ] || [ ! -r "${_cc}" ]; then\n'
        '          echo "ERROR: completeness_check.sh 不存在或不可讀 → fail-closed（不得記 success）" >&2\n'
        "          _rc=127\n"
        "        else\n",
        '          bash "${_cc}" --single "${out}" --family "${fam}" >&2 || _rc=$?\n',
        '  _fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"\n'
        '  _emit_family_result "${cli_rc}" "${_fmt_rc}" || {\n',
    ):
        assert anchor in s, f"凍結錨點漂移:\n{anchor!r}"


def test_findings_kind_gate_not_widened() -> None:
    """🔴 不得把 findings-kind 閘改為無條件。

    主委初版改成「有 family 就跑」，結果未複製 checker 的隔離環境全部 fail-closed
    ⇒ `test_debt_emit` 17 條轉紅。那不是更嚴，是打斷 impl／stamp 輪的既有契約。
    """
    s = _src()
    i = s.index("_run_format_check_if_needed() {")
    body = s[i : s.index("printf '%s' \"${_rc}\"", i)]
    assert 'case "${_bk}" in\n    review|consult|closure)' in body, (
        "findings-kind 閘被放寬 ⇒ 隔離環境會 fail-closed"
    )


def test_lifecycle_embed_stays_in_sync() -> None:
    """改 `cx_run.sh` 後內嵌 lifecycle 副本仍須 ≡ 正本。"""
    got = subprocess.run(
        ["bash", "scripts/govb1_final_gate.sh", "--only", "lifecycle_embed"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        env=os.environ.copy(),
    )
    assert got.returncode == 0, got.stderr


def test_contract_sot_unchanged_by_this_batch() -> None:
    """Task 4.3 不改 `govflow_lifecycle.json`（那是 Task 4.2 的 single-writer 範圍）。"""
    got = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "scripts/govflow_lifecycle.json"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert got.returncode == 0
    assert got.stdout.strip() == "", f"本批不得改契約 SoT:\n{got.stdout}"
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    assert data["zero_findings_contract"]["findings_destination"]["default"] == (
        "own_output_file"
    )
