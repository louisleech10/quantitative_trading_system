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
# 🔴 D-002 `Task 9.2b`（(G-4d)③）：fixture 新增邊界事件 `bnd_shift`——它的
#    `feature_cutoff_ms` 在 **test 段**、`decision_at_ms` 在 **train 段**（兩值刻意不等）。
#    9.2b 前之 per-cutoff 判側會把它歸 **test**；9.2b 之事件級錨定歸 **train**。
#    ⇒ 本常數由 `train` 多出 `bnd_shift` **就是換錨的行為差異在手推錨點上的現形**；
#    沒有這一筆，(G-4d)②③ 在 golden 上一筆都測不到（R9 兩家撞題指出的空心通過）。
#    🔴 9B 前之錨點另存於不可變的 `tests/golden/splitunify/splitunify_golden.v8.json`
#    （`--write` 對它一律拒寫），兩份並存才能證明差異是刻意的而非寫壞的。
_HAND_TRAIN = ["bnd_shift", "tr0", "tr1", "tr2", "tr3"]
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


# ── 🔴 review-r27 之三道 golden 防護（`CODEX-R27-P1-01`／`P1-02`／`P1-03`）────────


def test_v8_baseline_has_external_anchor_in_code(golden: dict) -> None:
    """🔴 v8 不可變基準之驗證須有**外部錨**，不得只比「檔案 vs 旁檔」。

    出生理由：原本只驗檔案與其旁檔，**同步改寫兩者**即可悄悄換掉 9B 前的錨點
    （`CODEX-R27-P1-02` 實跑 `NORMAL_MODE_RC 0`）。
    🔴 **`CODEX-R28-P1-02` 再更正錨點的「位置」**：r27 把它寫成 helper 的 Python 常數，
    但 SPEC §V 早在 v13 之 O2 定死「錨在**已提交文件**、helper 只讀」——寫在 helper 裡
    就又是第二份真相。本測試據此改為驗 **SPEC §V 的逐字錨點行**（node id 保留供追溯）。
    """
    import hashlib
    from pathlib import Path

    m = _fz_module()
    anchor = m._read_v8_anchor_from_spec()
    assert anchor is not None and len(anchor) == 64, (
        "SPEC §V 缺（或有多於一個）逐字 `V8_BASELINE_SHA256=<64-hex>` 錨點行"
    )
    repo = Path(__file__).resolve().parents[3]
    v8 = repo / "tests" / "golden" / "splitunify" / "splitunify_golden.v8.json"
    sidecar = repo / "tests" / "golden" / "splitunify" / "splitunify_golden.v8.sha256"
    assert v8.exists() and sidecar.exists(), "v8 基準或旁檔缺席"
    assert hashlib.sha256(v8.read_bytes()).hexdigest() == anchor
    assert sidecar.read_text(encoding="utf-8").strip() == anchor


def test_golden_carries_hand_expected_side_third_judge(golden: dict) -> None:
    """🔴 (G-4e)：golden 須帶**人手** `expected_side` 攤平出來的第三份判準。

    出生理由：只比「投影 vs oracle」兩份時，同一次錯誤解讀寫進兩邊仍會通過 G-3b——
    該家實跑 `SAME_WRONG_PROJECTION_ORACLE_PASSES_G3B True`。
    🔴 本測試只驗**存在且三方相等**；三份人手同錯仍會一致，那是已具名的誠實邊界。
    """
    hand = golden["g4e_hand_expected_membership"]
    assert set(hand) == {"train", "test", "purged"}
    assert hand == golden["g1_membership"], "人手判準與投影不一致"
    assert hand == golden["g3b_oracle"], "人手判準與 oracle 不一致"
    total = sum(len(v) for v in hand.values())
    assert total == sum(len(golden["g1_membership"][k]) for k in hand), "三態筆數不守恆"
    assert "bnd_shift" in hand["train"], (
        "換錨邊界事件須由人手判在 train——它正是 (G-4d)③ 的存在理由"
    )


def test_versioned_v9_keys_present(golden: dict) -> None:
    """🔴 (G-4d)①：v9 版本化鍵須與主鍵並存，供日後與 v8 對照。"""
    for key in ("g1_membership_v9", "g3b_oracle_v9"):
        assert key in golden, f"缺版本化鍵 {key}"
        assert set(golden[key]) == {"train", "test", "purged"}


# ── 🔴 review-r28 之四道加強（`CODEX-R28-P1-01`..`P1-04`）────────────────────


def _fz_module():
    import importlib.util
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "_fz_r28", repo / "scripts" / "freeze_splitunify_golden.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_v8_anchor_lives_in_spec_not_in_helper() -> None:
    """🔴 v8 外部錨之**唯一權威**是 SPEC §V 的逐字行，helper 只讀（`CODEX-R28-P1-02`）。

    出生理由：r27 把 digest 寫成 helper 的 Python 常數，但 SPEC §V 早在 v13 之 O2 就定死
    「錨在已提交文件、**helper 只讀**」。寫在 helper 裡就又是第二份真相，而且
    「改碼與改 golden 是同一個人、同一個 commit」這個攻擊面完全沒縮小。
    """
    m = _fz_module()
    assert not hasattr(m, "V8_BASELINE_SHA256"), (
        "helper 不得自帶 digest 常數——那是第二份真相（SPEC §V 才是唯一權威）"
    )
    anchor = m._read_v8_anchor_from_spec()
    assert anchor is not None and len(anchor) == 64, "SPEC §V 缺唯一的 V8_BASELINE_SHA256 錨點行"
    import hashlib
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    v8 = repo / "tests" / "golden" / "splitunify" / "splitunify_golden.v8.json"
    assert hashlib.sha256(v8.read_bytes()).hexdigest() == anchor


def test_v8_baseline_creation_is_write_once() -> None:
    """🔴 v8 基準為 write-once：已存在時再次建立**須拒絕**（`CODEX-R28-P1-02`）。

    出生理由：只驗 digest 擋不住「刪掉重建一份新的 v8」。用 `O_CREAT|O_EXCL` 讓第二次
    建立在**作業系統層**失敗，才不是靠「記得不要覆寫」這種紀律。
    """
    m = _fz_module()
    assert m.create_v8_baseline_write_once(b"{}") == 1, (
        "v8 已存在卻允許再次建立 ⇒ write-once 沒生效"
    )


def test_golden_carries_hand_decision_timestamps(golden: dict) -> None:
    """🔴 (G-4e) 第二欄人手判準：`expected_decision_at_ms` 逐筆對帳（`CODEX-R28-P1-03`）。

    出生理由：r27 只人手填了**側別**，事件**時刻**仍與投影共用 `_plans`／`holdout_boundary`
    ⇒ 該家把每列 `decision_at_ms` **加 1 毫秒**、側別不變，golden 仍 `GOLDEN OK`。
    錨點時刻現改由 `BASE`／`H1` 兩個 fixture 常數手算，任何整批位移都會現形。
    """
    hand = golden["g4e_hand_decision_at_ms"]
    got = golden["g4e_actual_decision_at_ms"]
    assert hand and set(hand) == set(got), "兩份錨點時刻之事件集合須相同"
    assert hand == got, "人手錨點時刻與 fixture 實際值不符（整批位移）"
    assert len(set(hand.values())) > 1, "全部同值會讓本對帳失去鑑別力"


def test_write_refuses_silent_value_change_of_existing_keys() -> None:
    """🔴 `--write` 不得**靜默改掉**既有頂層鍵的值（`CODEX-R28-P1-01`）。

    出生理由：r27 的護欄只擋「丟鍵」，該家把 `g4_per_symbol_n` 改成 `{"ETHUSDT": 999}`
    後 `--write` 直接接受（`changed-existing-value RC 0`）。現改為**顯式具名**：
    要動哪個既有鍵就得在 `--accept-value-changes` 逐一列出——把「悄悄改」變成「必須寫下來」。
    """
    import inspect

    m = _fz_module()
    src = inspect.getsource(m.main)
    assert "--accept-value-changes" in src or "accept_value_changes" in src, (
        "缺既有鍵逐值閘之授權旗標 ⇒ 改值仍可靜默通過"
    )
    assert "_unauthorised" in src, "缺未授權改值之 fail-closed 分支"
