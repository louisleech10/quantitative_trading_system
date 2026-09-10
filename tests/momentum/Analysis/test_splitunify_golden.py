"""SPLITUNIFY B2c：golden 五組之 pytest 入口（SPEC §G；nodeid 依 SPEC Task 2.3 命名）。

🔴 本檔**不重寫**比對邏輯——`scripts/freeze_splitunify_golden.py` 是唯一實作，
本檔只是把它接進 pytest，讓 golden 進回歸網。重寫一份就又是「兩份算術」。

nodeid 對照 SPEC §G：
  `-k row_fingerprint`   → G-5① 逐 row test fingerprint（sha256）
  `-k event_ids`         → G-5② 逐 event assignments／purged IDs（含 diff 輸出）
  `-k answer_window`     → G-5③ answer-window 完整性
  `-k leakage_negative`  → G-5④ 注入跨界事件必進 purged
  `-k independent_oracle`→ G-3b 新投影 vs 獨立 oracle
  `-k per_symbol`        → G-4 per-symbol counts
  `-k golden_compare`    → G-1 全組比對（失敗須**指名差在哪一筆**）
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "freeze_splitunify_golden.py"
GOLDEN = REPO / "tests" / "golden" / "splitunify" / "splitunify_golden.json"


@pytest.fixture(scope="module")
def golden() -> dict:
    assert GOLDEN.exists(), f"golden 不存在：{GOLDEN}——首次請跑 `--write`"
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def compare_run() -> subprocess.CompletedProcess:
    """跑一次比對模式；三個「每次都驗」的檢查（G-3b／G-5④）也在裡面。"""
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=REPO, capture_output=True, text=True
    )


def test_golden_compare_is_clean(compare_run) -> None:
    """G-1 全組比對 rc=0；失敗時輸出**必須指名差在哪一筆**（不是只回布林）。"""
    assert compare_run.returncode == 0, (
        f"golden 比對失敗（rc={compare_run.returncode}）：\n{compare_run.stdout[-2000:]}"
    )
    assert "GOLDEN OK" in compare_run.stdout


def test_independent_oracle_agrees(compare_run) -> None:
    """G-3b：投影 vs **獨立** oracle 集合相等（oracle 逐行重寫規則，不呼叫被測函式）。"""
    assert "✓ G-3b" in compare_run.stdout, compare_run.stdout[-2000:]


def test_leakage_negative_case_blocks(compare_run) -> None:
    """G-5④：把 train 事件的 `label_end_ms` 推進 test 區 ⇒ **必進 purged**。

    正向全對但負例不擋，等於沒有 containment 保證——這條是 golden 的另一半。
    """
    assert "✓ G-5④" in compare_run.stdout, compare_run.stdout[-2000:]


def test_row_fingerprint_recomputes_from_frozen_plaintext(golden: dict) -> None:
    """🔴 G-5①：由**凍結的明文** positions **獨立重算** sha256 並逐值比對。

    出生理由（B2c review `CODEX-R1-P1-02`）：只凍 hash、測試只驗「是 64 位 hex」
    ⇒ **錯的 fingerprint 也會被自凍結**，等於沒驗。現在明文與 hash 都凍，
    本測試從明文重算——兩者對不上表示 golden 內部自相矛盾。
    """
    positions = golden["g5_row_fingerprint_positions"]
    assert positions, "positions 不得為空"
    assert len(positions) == golden["g5_row_fingerprint_n"]
    assert positions == sorted(positions), "positions 必須遞增（row_index 之不變式）"
    assert len(set(positions)) == len(positions), "positions 不得重複"

    # 由明文重建 canonical payload 並重算——與 freeze 腳本同一條規則，但**資料來自 golden**。
    first_ms, last_ms = golden["g5_row_fingerprint_first_ms"], golden["g5_row_fingerprint_last_ms"]
    step = (last_ms - first_ms) // (len(positions) - 1) if len(positions) > 1 else 0
    rows = [[p, first_ms + i * step, "ETHUSDT", "splitunify-golden"]
            for i, p in enumerate(positions)]
    recomputed = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert recomputed == golden["g5_row_fingerprint_sha256"], (
        "由凍結明文重算之 sha256 與凍結的 hash 不符 ⇒ golden 內部自相矛盾"
    )


def test_answer_window_precondition_has_no_breach(golden: dict) -> None:
    """🔴 G-5③ 驗的是**前置條件**（兩端 endpoint 都在 bar 上），不是「投影有沒有 purge」。

    SPEC R4 之 F1 明訂 endpoint 檢查不進投影（投影沒有 bars）⇒ 由本 golden 驗上游。
    我第一版寫成「缺 endpoint 必 purge」，與該裁定矛盾（三家獨立命中 G-5③ 弱於 SPEC，
    但正確的修法不是把它加進投影，而是把驗的對象講清楚）。
    """
    aw = golden["g5_answer_window"]
    assert aw["precondition_breaches"] == [], (
        f"上游 alignment 應已擋下這些事件：{aw['precondition_breaches']}"
    )
    assert aw["missing_endpoint"] == aw["precondition_breaches"], "兩者是同一個集合的兩個名字"
    assert len(aw["both_endpoints_on_bar"]) == sum(
        len(golden["g1_membership"][k]) for k in ("train", "test", "purged")
    ), "fixture 之全部事件都應通過前置條件"


# ── 🔴 手推錨點：oracle 與 actual 共用 fixture／邊界，共同錯誤會一起綠 ──────
#    （B2c review `CODEX-R1-P1-03`）⇒ 這裡把**由 fixture 常數手算**出來的期望值寫死，
#    它不經過 `holdout_boundary` 也不經過投影。邊界算錯時這些數字會動，於是被抓到。
#
#    fixture 常數：N_BARS=200、OOS=0.3、PURGE=2、EMBARGO=2、每根 1h。
#    手算：split_point = floor((1-0.3) * 200) = 140
#          train rows  = 0..139
#          test rows   = 140+2+2 = 144 .. 199  ⇒ 共 200-144 = **56** 列
#    事件（12 筆）：tr0..tr3 取 train 前四列、tr_leak 取 train 末列（答案窗恰觸 test 起點）、
#          gap1/gap2 落在隔離區、te0..te4 取 test 前五列。
_HAND_TRAIN = ["tr0", "tr1", "tr2", "tr3"]
_HAND_TEST = ["te0", "te1", "te2", "te3", "te4"]
_HAND_PURGED = ["gap1", "gap2", "tr_leak"]
_HAND_TEST_ROW_FIRST = 144
_HAND_TEST_ROW_LAST = 199
_HAND_TEST_ROW_N = 56


def test_hand_derived_anchors_match_golden(golden: dict) -> None:
    """🔴 手推的期望值 vs 凍結值——不經 `holdout_boundary`、不經投影。

    出生理由：我的「獨立 oracle」與被測程式**共用同一組 fixture 與同一支邊界函式** ⇒
    邊界算錯時兩邊會**一起錯**而測試仍綠（`CODEX-R1-P1-03`）。
    這條是第三個獨立錨點：數字由 fixture 常數手算，任何一端動了都會對不上。
    """
    m = golden["g1_membership"]
    assert m["train"] == _HAND_TRAIN
    assert m["test"] == _HAND_TEST
    assert m["purged"] == _HAND_PURGED
    pos = golden["g5_row_fingerprint_positions"]
    assert pos[0] == _HAND_TEST_ROW_FIRST, (
        f"test 段起點應為 split_point(140)+purge(2)+embargo(2)=144，實得 {pos[0]}"
    )
    assert pos[-1] == _HAND_TEST_ROW_LAST
    assert len(pos) == _HAND_TEST_ROW_N == golden["g5_row_fingerprint_n"]


def test_event_ids_three_states_are_disjoint_and_total(golden: dict) -> None:
    """G-5②：三態互斥且涵蓋全集（金檔自身之不變式——防「凍了一份壞的」）。"""
    m = golden["g1_membership"]
    tr, te, pu = set(m["train"]), set(m["test"]), set(m["purged"])
    assert tr & te == set() and tr & pu == set() and te & pu == set(), "三態必須互斥"
    assert len(tr) + len(te) + len(pu) == len(tr | te | pu), "不得有重複 event_id"
    assert pu, "fixture 必須含被 purge 的事件，否則 G-5④ 的負例無從對照"


def test_per_symbol_counts_are_integers(golden: dict) -> None:
    """G-4：per-symbol counts 為**整數逐值**（非 atol 比較）。"""
    counts = golden["g4_per_symbol_n"]
    assert counts, "per_symbol_n 不得為空"
    assert all(isinstance(v, int) for v in counts.values())


def test_purge_reason_literal_is_contract_value(golden: dict) -> None:
    """purge reason 沿用既有契約字面，不得另造（SPEC C-3）。"""
    assert golden["purge_reasons"] == ["interval_crosses_split_boundary"]
