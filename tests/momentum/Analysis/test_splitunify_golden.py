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
import os
import re
import shutil
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


# ── 🔴 review-r29 之五條加強（`CODEX-R29-P1-01`..`P1-05`）────────────────────


def test_value_change_authorisation_requires_old_new_digest() -> None:
    """🔴 `--accept-value-changes` 須帶 `old8:new8`，只列鍵名不算授權（`CODEX-R29-P1-01`）。

    出生理由：r28 只驗鍵名 ⇒ 一旦具名，該鍵**任意**新值都能寫進去（該家實跑把 13 改成 999
    且 rc=0）。也就是說「習慣性把所有鍵都列上去」等於沒有閘。
    🔴 這是主委**第三次**宣稱「偏離委員修法但等效」，三次都被實跑否證 ⇒ 本測試釘住格式。
    """
    import inspect

    m = _fz_module()
    src = inspect.getsource(m.main)
    assert "<old8>:<new8>" in src or "_digest_bad" in src, (
        "授權未綁 old→new digest ⇒ 具名即可任意改值"
    )
    assert "_digest_bad" in src, "缺 digest 不符之 fail-closed 分支"


def test_v8_anchor_must_live_in_spec_section_v_not_history() -> None:
    """🔴 錨點只認 **§V 區段內**，`HISTORY` 區塞一行不算（`CODEX-R29-P1-02`）。

    出生理由：r28 的 regex 接受 SPEC **任意位置** ⇒ 在 `HISTORY` 塞新錨點、再同步換掉
    v8 與旁檔即可繞過（該家實跑 `N2_SAME_COMMIT_REPLACED_SPEC_RC 0`）。
    🔴 **誠實邊界**：本測試只證明「塞在哪裡」被收窄；**擋不住**「同一 commit 同時改
    §V 錨、v8、旁檔與 helper」——那需要受保護簽章或不可變 ancestor attestation，
    屬新建治理工具，已登記為具名殘留 `SU-RESID-V8-ATTEST`，**不得讀作已關閉**。
    """
    import inspect

    m = _fz_module()
    src = inspect.getsource(m._read_v8_anchor_from_spec)
    assert "HISTORY-BEGIN" in src and "沿革" in src, (
        "錨點掃描未排除 HISTORY／沿革區 ⇒ 塞在那裡也會被採信"
    )
    assert m._read_v8_anchor_from_spec() is not None


def test_hand_decision_timestamps_are_immutable_literals() -> None:
    """🔴 人手錨點時刻須為**不可變字面**，不得由 `BASE`／`H1` 推導（`CODEX-R29-P1-03`）。

    出生理由：r28 寫成 `BASE + n * H1`，而 fixture 的實際時刻用的是**同兩個常數** ⇒
    該家把 `BASE` 平移 17 毫秒，人手值與實際值**一起移動**、對帳照樣相等
    （實跑 `N3_BASE_SHIFT_AFTER_EQUAL True`）。
    """
    import inspect

    m = _fz_module()
    src = inspect.getsource(m._event_keys)
    seg = src[src.index("_hand_decision"):src.index("return pd.DataFrame")]
    assert "BASE" not in seg and "H1" not in seg, (
        "人手錨點時刻仍由 BASE／H1 推導 ⇒ 與 fixture 實際值共因，整批位移測不到"
    )


def test_v8_first_create_path_exists_and_is_transactional() -> None:
    """🔴 首次建立須**接進 `main()`** 且兩檔為交易式（`CODEX-R29-P1-04`）。

    出生理由：r28 只提供 helper，`main()` 在 v8 缺席時一律 rc=1 ⇒「首建成功」那一半
    **從來沒有可執行路徑**（該家實跑 `V8_CREATED False`）；且逐一 `O_EXCL` 在旁檔先存在時
    會留下**半套狀態**。
    """
    import inspect

    m = _fz_module()
    main_src = inspect.getsource(m.main)
    assert "--init-v8" in main_src or "init_v8" in main_src, "首次建立未接進 main()"
    create_src = inspect.getsource(m.create_v8_baseline_write_once)
    assert "existing" in create_src and "unlink" in create_src, (
        "首次建立非交易式 ⇒ 中途失敗會留半套狀態"
    )


# 🔴 **R30 `CODEX-R30-P1-01`：第三份獨立副本（本檔）**。
#    r29 把人手時刻改成不可變字面，切斷了**事後**平移 `BASE` 的共因；
#    但該家實跑證明：把 `BASE` **與** fixture 裡的字面**同步**平移 17 毫秒，兩欄仍相等
#    （`BASE_SHIFT_AND_HAND_SHIFT_G4E_EQUAL True`）——因為那些字面當初是主委**用同一組常數算出來再貼上去的**。
#    ⇒ 在**另一個檔**（本測試檔）再放一份字面，並與 golden 凍結值逐筆對帳；
#    要繞過就得**同時**改 fixture、golden 與本檔三處。這不是絕對防護（同 commit 改三處仍可），
#    但把「改一個常數就靠到」拉升到「必須審過三個檔」，且與 `SU-RESID-V8-ATTEST` 同一誠實邊界。
_INDEP_DECISION_MS = {
    "tr0": 1700000000000,
    "tr1": 1700003600000,
    "tr2": 1700007200000,
    "tr3": 1700010800000,
    "tr_leak": 1700500400000,
    "gap1": 1700504000000,
    "gap2": 1700507600000,
    "te0": 1700518400000,
    "te1": 1700522000000,
    "te2": 1700525600000,
    "te3": 1700529200000,
    "te4": 1700532800000,
    "bnd_shift": 1700000000000,
}


def test_hand_decision_timestamps_have_independent_third_copy(golden: dict) -> None:
    """🔴 錨點時刻須有**第三份獨立副本**（`CODEX-R30-P1-01`）。

    出生理由：r29 的「不可變字面」只切斷了**事後**平移；該家把 `BASE` 與字面同步
    平移後兩欄仍相等，因為字面當初是由同一組常數算出來的。本測試把第三份
    放在**另一個檔**，三者任一不同即紅。
    """
    hand = golden["g4e_hand_decision_at_ms"]
    got = golden["g4e_actual_decision_at_ms"]
    assert set(_INDEP_DECISION_MS) == set(hand) == set(got), "三份之事件集合須相同"
    assert _INDEP_DECISION_MS == hand, "本檔獨立副本 ≠ fixture 人手字面"
    assert _INDEP_DECISION_MS == got, "本檔獨立副本 ≠ fixture 實際值"


# ── 🔴 D-002 `Task 9.5`（批次 B9F）：§V 第 6 條與 §G (G-2) 之指名測試（**行為測試**，非原始碼字串比對）──
#
# 既有同主題測試多以 `inspect.getsource` 檢查字串存在；本節改為**真的執行**寫檔／建立／比對路徑，
# 並把副作用導到 `tmp_path`（`monkeypatch` 模組層 `GOLDEN_DIR`／`RECEIPT_DIR`），不動 repo 內檔案。

SPEC = REPO / "docs" / "SPLITUNIFY_SPEC.md"
V8 = REPO / "tests" / "golden" / "splitunify" / "splitunify_golden.v8.json"
V8_SIDECAR = REPO / "tests" / "golden" / "splitunify" / "splitunify_golden.v8.sha256"
_V8_TOP_KEYS = (
    "_doc", "g1_membership", "g3b_oracle", "g4_per_symbol_n", "g5_answer_window",
    "g5_row_fingerprint_first_ms", "g5_row_fingerprint_last_ms", "g5_row_fingerprint_n",
    "g5_row_fingerprint_positions", "g5_row_fingerprint_sha256", "purge_reasons",
)
_PARALLEL_PREFIX = "g2_interleaved_"
#: 平行組之**人手**事件級成員集（事件命名即其設計側別；不經投影、不經 oracle）。
_HAND_INTERLEAVED_MEMBERSHIP = {
    "train": ["BTCUSDT_tr0", "ETHUSDT_tr0"],
    "test": ["BTCUSDT_te0", "BTCUSDT_te1", "ETHUSDT_te0", "ETHUSDT_te1"],
    "purged": ["BTCUSDT_leak", "ETHUSDT_leak"],
}


def _spec_anchor_hits_outside_history() -> list:
    """**不經 helper**：直接讀 SPEC、截掉 HISTORY／沿革區後，收集所有 `V8_BASELINE_SHA256=` 行之值。

    值刻意寬鬆擷取（非 64-hex 也收），好讓「格式壞掉」被判為格式錯而不是「找不到」。
    """
    text = SPEC.read_text(encoding="utf-8")
    for marker in ("<!-- HISTORY-BEGIN -->", "## 沿革與追溯索引"):
        pos = text.find(marker)
        if pos >= 0:
            text = text[:pos]
    return re.findall(r"^\s*`?V8_BASELINE_SHA256=([^\s`]*)`?\s*$", text, re.M)


def _tmp_golden_dir(tmp_path: Path) -> Path:
    gd = tmp_path / "golden"
    gd.mkdir()
    for p in (GOLDEN, V8, V8_SIDECAR):
        shutil.copy2(p, gd / p.name)
    return gd


def _run_main(m, monkeypatch, tmp_path: Path, golden_dir: Path, *argv: str) -> int:
    monkeypatch.setattr(m, "GOLDEN_DIR", golden_dir)
    # `main()` 只以 `REPO` 印相對路徑（`_SPEC_PATH` 為匯入時已算好之常數，不受影響）；
    # 寫檔目錄在 tmp 時須一併導過去，否則 `relative_to(REPO)` 拋 ValueError。
    if tmp_path in golden_dir.parents:
        monkeypatch.setattr(m, "REPO", tmp_path)
    receipts = tmp_path / "receipts"
    receipts.mkdir(exist_ok=True)
    monkeypatch.setattr(m, "RECEIPT_DIR", receipts)
    monkeypatch.setattr(sys, "argv", ["freeze_splitunify_golden.py", *argv])
    return m.main()


def test_spec_anchor_line_exists_and_is_64hex() -> None:
    """§V 第 6 條（`M-SU-D2-34`）：SPEC §V 內**恰一行** `V8_BASELINE_SHA256=<64-hex>`（HISTORY 區不算）。"""
    hits = _spec_anchor_hits_outside_history()
    assert len(hits) == 1, f"SPEC §V 之 V8 錨點行須恰一行，實得 {len(hits)}：{hits}"
    assert re.fullmatch(r"[0-9a-f]{64}", hits[0]), f"錨點值非 64 位小寫 hex：{hits[0]!r}"


def test_v8_sha256_matches_spec_anchor_line() -> None:
    """§V 第 6 條（外部錨，`M-SU-D2-33`）：v8 檔實際 sha256 ＝ SPEC 錨點行 ＝ 旁檔。

    🔴 只比旁檔會綠（同步改寫兩檔即可換掉回歸錨）——故以**不經 helper** 讀出之 SPEC 字面為準。
    """
    hits = _spec_anchor_hits_outside_history()
    assert len(hits) == 1
    anchor = hits[0]
    assert hashlib.sha256(V8.read_bytes()).hexdigest() == anchor, "v8 基準內容與 SPEC 外部錨不符"
    assert V8_SIDECAR.read_text(encoding="utf-8").strip() == anchor, "旁檔與 SPEC 外部錨不符"


def test_v8_baseline_is_write_once(tmp_path: Path, monkeypatch) -> None:
    """§V 第 6 條（`M-SU-D2-33`）：首次建立成功；其後任何一次再建即拒、且不改寫已存在之內容；半套狀態不建。"""
    m = _fz_module()
    monkeypatch.setattr(m, "GOLDEN_DIR", tmp_path)
    first = b'{"baseline": 1}\n'
    assert m.create_v8_baseline_write_once(first) == 0
    v8, sidecar = tmp_path / "splitunify_golden.v8.json", tmp_path / "splitunify_golden.v8.sha256"
    assert v8.read_bytes() == first
    assert sidecar.read_text(encoding="utf-8") == hashlib.sha256(first).hexdigest() + "\n"
    assert m.create_v8_baseline_write_once(b'{"baseline": 2}\n') == 1, "v8 已存在卻允許再建"
    assert v8.read_bytes() == first, "再建被拒後內容不得被改寫"
    half = tmp_path / "half"
    half.mkdir()
    monkeypatch.setattr(m, "GOLDEN_DIR", half)
    (half / "splitunify_golden.v8.sha256").write_text("stale\n", encoding="utf-8")
    assert m.create_v8_baseline_write_once(first) == 1, "只有旁檔存在時仍允許建立 ⇒ 半套狀態"
    assert not (half / "splitunify_golden.v8.json").exists()


def test_freeze_write_flag_refuses_v8_target(tmp_path: Path, monkeypatch, capsys) -> None:
    """§V 第 6 條（`M-SU-D2-29`）：`--write` 之寫入目標解析為 v8 基準時**必拒**，且以該專屬理由拒（非被其他閘順帶擋下）。"""
    m = _fz_module()
    gd = tmp_path / "golden"
    gd.mkdir()
    shutil.copy2(V8, gd / V8.name)
    shutil.copy2(V8_SIDECAR, gd / V8_SIDECAR.name)
    (gd / "splitunify_golden.json").symlink_to(gd / V8.name)
    before = (gd / V8.name).read_bytes()
    rc = _run_main(m, monkeypatch, tmp_path, gd, "--write")
    out = capsys.readouterr().out
    assert rc == 1
    assert "為不可變基準，禁止 --write 覆寫" in out, out[-1500:]
    assert (gd / V8.name).read_bytes() == before, "v8 基準被 --write 改寫"


def test_freeze_script_does_not_write_spec_anchor(tmp_path: Path, monkeypatch) -> None:
    """§V 第 6 條（`M-SU-D2-34`）：凍結腳本比對與重凍兩種模式皆**不寫** SPEC（錨點行只由人在 SPEC 維護、helper 只讀）。"""
    m = _fz_module()
    before = (SPEC.read_bytes(), os.stat(SPEC).st_mtime_ns)
    assert _run_main(m, monkeypatch, tmp_path, GOLDEN.parent) == 0, "比對模式 rc≠0"
    gd = _tmp_golden_dir(tmp_path)
    assert _run_main(m, monkeypatch, tmp_path, gd, "--write") == 0, "tmp 重凍 rc≠0"
    assert (SPEC.read_bytes(), os.stat(SPEC).st_mtime_ns) == before, "凍結腳本改寫（或重寫）了 SPEC"


def test_main_json_eleven_top_keys_unchanged(tmp_path: Path, monkeypatch, capsys) -> None:
    """§V 第 6 條（`M-SU-D2-29`）：主檔既有 11 個頂層鍵（＝v8 鍵集）於重凍後逐值不變；改其值而無 digest 授權即拒寫。"""
    m = _fz_module()
    v8_keys = set(json.loads(V8.read_text(encoding="utf-8")))
    assert v8_keys == set(_V8_TOP_KEYS), "fixture 前提變了：v8 鍵集不是原始 11 鍵"
    original = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert v8_keys <= set(original), "主檔丟了 v8 時代之頂層鍵"

    gd = _tmp_golden_dir(tmp_path)
    assert _run_main(m, monkeypatch, tmp_path, gd, "--write") == 0
    rewritten = json.loads((gd / GOLDEN.name).read_text(encoding="utf-8"))
    for k in _V8_TOP_KEYS:
        if k.startswith("_"):
            continue
        assert rewritten[k] == original[k], f"重凍改動了既有頂層鍵 {k}"

    real_build = m._build_actual

    def _tampered():
        out = real_build()
        out["g4_per_symbol_n"] = {k: v + 1 for k, v in out["g4_per_symbol_n"].items()}
        return out

    monkeypatch.setattr(m, "_build_actual", _tampered)
    snapshot = (gd / GOLDEN.name).read_bytes()
    capsys.readouterr()
    assert _run_main(m, monkeypatch, tmp_path, gd, "--write") == 1
    assert "GOLDEN REFUSE" in capsys.readouterr().out
    assert (gd / GOLDEN.name).read_bytes() == snapshot, "被拒之重凍仍改寫了主檔"


def test_single_tf_golden_values_unchanged(golden: dict) -> None:
    """§G／`Task 9.5`（`M-SU-D2-17`）：新增平行組後，單標的組**每個既有鍵**之現算值與 golden 逐值相同。"""
    m = _fz_module()
    actual = m._build_actual()
    single_keys = [k for k in golden if not k.startswith("_") and not k.startswith(_PARALLEL_PREFIX)]
    assert set(_V8_TOP_KEYS) - {"_doc"} <= set(single_keys)
    diffs = [k for k in single_keys if actual.get(k) != golden[k]]
    assert diffs == [], f"單標的回歸錨被改動：{diffs}"


def test_interleaved_parallel_group_g5_differs_and_is_stable(golden: dict) -> None:
    """§G (G-2)（`M-SU-D2-16`／`M-SU-D2-17`）：交錯平行組兩次建構逐值相同、與 golden 相符、g5 與單標的組不同。

    成員集須**事件級**（不擴成 event×TF）且等於人手成員集；稽核列數＝事件數×2（兩個 feature TF 皆在）。
    """
    m = _fz_module()
    first, second = m._build_interleaved_actual(), m._build_interleaved_actual()
    assert first == second, "平行組不穩定（兩次建構不同）"
    assert set(first) == {k for k in golden if k.startswith(_PARALLEL_PREFIX)}, "golden 缺平行組鍵或多出鍵"
    for k, v in first.items():
        assert golden[k] == v, f"平行組 {k} 與 golden 不符"

    membership = first["g2_interleaved_membership"]
    assert membership == _HAND_INTERLEAVED_MEMBERSHIP, "平行組成員集與人手判準不符（或被擴成 event×TF）"
    flat = [e for side in membership.values() for e in side]
    assert len(flat) == len(set(flat)) == first["g2_interleaved_n_events"]
    assert first["g2_interleaved_n_event_tf_rows"] == 2 * first["g2_interleaved_n_events"]

    fps = first["g2_interleaved_g5_row_fingerprint_sha256"]
    assert set(fps) == {"ETHUSDT", "BTCUSDT"} and fps["ETHUSDT"] != fps["BTCUSDT"]
    assert golden["g5_row_fingerprint_sha256"] not in fps.values(), "平行組 g5 與單標的組相同 ⇒ 疑似覆蓋"

    # 🔴 review-r50 `CODEX-R50-P2-01`：由**凍結明文**（標的內序號＋逐列 feature_ts_ms）獨立重算 SHA，須等於凍結值——
    #    明文與雜湊須為同一份 payload。算法同 `test_row_fingerprint_recomputes_from_frozen_plaintext`，資料只取自 golden。
    local = golden["g2_interleaved_g5_row_fingerprint_positions"]
    ts = golden["g2_interleaved_g5_row_fingerprint_feature_ts_ms"]
    glob = golden["g2_interleaved_global_row_index_positions"]
    for s in ("ETHUSDT", "BTCUSDT"):
        assert local[s] == sorted(set(local[s])) and len(local[s]) == len(ts[s]) == len(glob[s]) > 0
        rows = [[p, t, s, "splitunify-golden-interleaved"] for p, t in zip(local[s], ts[s])]
        recomputed = hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert recomputed == golden["g2_interleaved_g5_row_fingerprint_sha256"][s], (
            f"{s}：由凍結明文重算之指紋與凍結 SHA 不符 ⇒ positions 與 SHA 不是同一份 payload"
        )
    # 全框列號只作「確實交錯」之證據：ETH 偶數、BTC 奇數，且不得冒充 payload（與標的內序號不同）
    assert all(p % 2 == 0 for p in glob["ETHUSDT"]) and all(p % 2 == 1 for p in glob["BTCUSDT"]), "非交錯全框位置"
    assert glob["BTCUSDT"] != local["BTCUSDT"], "全框列號與標的內序號相同 ⇒ fixture 未交錯或兩鍵被混用"
