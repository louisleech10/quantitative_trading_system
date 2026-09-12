"""SPLITUNIFY B2b：投影純函式 `derive_event_split_from_plans` 之測試。

規格：`docs/SPLITUNIFY_SPEC.md`（v5）C-2／C-3／C-4／C-5；mutation `M-SU-1`..`M-SU-7`、
`M-SU-12`、`M-SU-13`。

🔴 本檔之核心是 **`-k answer_window`**：它釘住兩段式判定的**第一段**——
答案窗跨進測試段的 train 事件必進 `purged`。少了那一段就是把 `event_split.py:114`
那道事件側唯一擋標籤窗跨界洩漏的閘刪掉（`SPLITUNIFY` v3 犯過，`CODEX-R3-P1-02` 抓出）。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.core.split_preview import build_row_time_fingerprint

from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.split_projection import (
    EVENT_KEY_COLUMNS,
    build_event_keys,
    build_time_clusters,
    derive_event_split_from_plans,
)
from momentum.Analysis.event_samples.types import (
    AlignmentReceipts,
    EventManifest,
    EventSplitConfig,
)
from momentum.core.contracts import SplitPlan
from momentum.core.split_preview import holdout_boundary

H1 = 3_600_000
BASE = 1_700_000_000_000
N_BARS = 100
OOS, PURGE, EMBARGO = 0.3, 2, 2
SYM = "ETHUSDT"


def _feature_index(n: int = N_BARS) -> pd.Index:
    """epoch 毫秒 int64 index（每根 1h）。"""
    return pd.Index([BASE + i * H1 for i in range(n)], dtype="int64")


def _plans(index: pd.Index, *, symbol: str = SYM):
    b = holdout_boundary(index, oos_test_size=OOS, purge_gap=PURGE, embargo=EMBARGO)
    kw = dict(
        index_kind="positional",
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=symbol,
    )
    # 🔴 SPLITUNIFY D-001 (4.3)：fixture 之 index 即該 symbol 自己的 post-trim 索引，
    #    故 `row_index_local` 逐值等於 `row_index`；指紋由共用序列化器產生（與 producer 同一支）。
    ms = np.asarray(index, dtype="int64")

    def _fp(rows):
        return build_row_time_fingerprint(
            positions=np.asarray(rows, dtype=int),
            feature_ts_ms=ms[np.asarray(rows, dtype=int)],
            symbol=symbol,
            base_universe_hash="deadbeef",
        )

    train = SplitPlan(
        split_label="train",
        row_index=b["train_row_index"],
        time_bounds=(int(index[0]), int(index[b["train_row_index"][-1]])),
        row_index_local=np.asarray(b["train_row_index"], dtype=int),
        row_time_fingerprint=_fp(b["train_row_index"]),
        **kw,
    )
    test = SplitPlan(
        split_label="test",
        row_index=b["test_row_index"],
        time_bounds=(int(index[b["test_row_index"][0]]), int(index[-1])),
        row_index_local=np.asarray(b["test_row_index"], dtype=int),
        row_time_fingerprint=_fp(b["test_row_index"]),
        **kw,
    )
    return train, test, b


def _sp(**kw) -> SplitPlan:
    """測試用 `SplitPlan` 工廠：補上 D-001 (4.3) 之 `row_index_local` 與逐列指紋。

    🔴 投影端**只消費** `row_index_local`（D-001 (4.10)），故「壞形狀」測試一律把壞值
    **同時**放進兩欄，原本要驗的那道守衛才會照舊觸發（而不是被缺欄檢查搶先）。
    指紋算不出來時給非空佔位字串——形狀閘在指紋比對**之前**，不影響該類測試的斷言。
    """
    idx = kw.pop("_index", None)
    if idx is None:
        idx = _feature_index()
    kw.setdefault("row_index_local", np.asarray(kw["row_index"]))
    if "row_time_fingerprint" not in kw:
        try:
            loc = np.asarray(kw["row_index_local"], dtype=int)
            ms = np.asarray(idx, dtype="int64")
            kw["row_time_fingerprint"] = build_row_time_fingerprint(
                positions=loc,
                feature_ts_ms=ms[loc],
                symbol=str(kw.get("symbol") or ""),
                base_universe_hash=str(kw.get("base_universe_hash") or ""),
            )
        except Exception:
            kw["row_time_fingerprint"] = "0" * 64
    return SplitPlan(**kw)


def _event_keys(rows) -> pd.DataFrame:
    """rows: iterable of (event_id, cutoff_ms, label_end_ms[, symbol])。"""
    recs = []
    for r in rows:
        eid, cutoff, label_end = r[0], r[1], r[2]
        sym = r[3] if len(r) > 3 else SYM
        recs.append(
            {
                "event_id": eid,
                "feature_cutoff_ms": int(cutoff),
                "label_start_ms": int(cutoff),
                "label_end_ms": int(label_end),
                "symbol": sym,
                "timeframe": "1h",
            }
        )
    return pd.DataFrame(recs)


def _manifest(keys: pd.DataFrame) -> EventManifest:
    table = pd.DataFrame(
        {
            "event_id": keys["event_id"],
            "symbol": keys["symbol"],
            "timeframe": keys["timeframe"],
            "decision_at_ms": keys["feature_cutoff_ms"].astype("int64"),
            "label_start_ms": keys["label_start_ms"].astype("int64"),
            "label_end_ms": keys["label_end_ms"].astype("int64"),
        }
    )
    return EventManifest(
        table=table,
        summary={"n_events_raw": int(len(table)), "n_events_effective": int(len(table))},
        policy={},
    )


def _basic_case():
    """一批事件：train 段兩筆（一筆答案窗跨界）、test 段一筆、隔離區一筆。"""
    index = _feature_index()
    train, test, b = _plans(index)
    train_rows, test_rows = b["train_row_index"], b["test_row_index"]
    test_start = int(index[test_rows[0]])
    keys = _event_keys(
        [
            ("e_train_ok", index[train_rows[0]], int(index[train_rows[0]]) + H1),
            ("e_train_leak", index[train_rows[-1]], test_start),          # 答案窗恰好觸到 ⇒ purge
            ("e_test", index[test_rows[0]], int(index[test_rows[0]]) + H1),
            ("e_gap", index[train_rows[-1]] + H1, int(index[train_rows[-1]]) + 2 * H1),
        ]
    )
    return index, train, test, keys, _manifest(keys), test_start


# ── 🔴 2026-09-11 歸屬回溯稽核撈回的三條（當輪被我漏掉，兩道檢查都沒響）──────────
def test_answer_window_one_ms_before_test_start_stays_in_train() -> None:
    """`GROK-R1-P2-02`（B2b R1）：比較式差 1 毫秒的改壞（`>= test_start_ms - 1`）原本測不到。

    答案窗結束在測試段起點**前 1 毫秒** ⇒ 沒有跨界 ⇒ 必須留在 train。
    既有 fixture 只測「恰好觸到」（`== test_start` ⇒ purge），於是把比較式挪 1 毫秒的 mutant 全綠。
    """
    index = _feature_index()
    train, test, b = _plans(index)
    test_start = int(index[b["test_row_index"][0]])
    keys = _event_keys([
        ("e_one_ms_short", index[b["train_row_index"][-1]], test_start - 1),
        ("e_test", index[b["test_row_index"][0]], test_start + H1),
    ])
    plan = derive_event_split_from_plans(train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1)
    labels = dict(zip(plan.assignments["event_id"], plan.assignments["split_label"]))
    assert labels.get("e_one_ms_short") == "train", (
        "答案窗在測試段起點前 1 毫秒結束 ⇒ 沒跨界，卻被 purge（比較式被挪了）"
    )
    assert "e_one_ms_short" not in set(plan.purged["event_id"])


def test_manifest_summary_missing_key_is_named_not_bare_keyerror() -> None:
    """`CODEX-R3-P3-04`（B2b R3）：manifest 缺欄時原本丟出**沒有語意的裸 KeyError**。"""
    index, train, test, keys, man, _ = _basic_case()
    broken = EventManifest(table=man.table, summary={"n_events_effective": 4}, policy={})
    with pytest.raises(ValueError, match="manifest.summary 缺"):
        derive_event_split_from_plans(train, test, keys, index, manifest=broken, bucket_ms=H1)


def test_tier_min_test_events_is_honored_not_silently_one() -> None:
    """B2b R1 之 H6：投影路徑原本把使用者設定的測試段事件數下限**靜默換成 1**。

    `_basic_case` 的 test 段只有 1 筆事件：下限 1 ⇒ 不足清單為空；下限 5 ⇒ 必須列出。
    """
    index, train, test, keys, man, _ = _basic_case()
    default = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert default.summary["insufficient_events_in_test"] == []
    strict = derive_event_split_from_plans(
        train, test, keys, index, manifest=man, bucket_ms=H1, tier_min_test_events=5,
    )
    assert strict.summary["insufficient_events_in_test"] == [SYM], (
        "下限設 5、測試段只有 1 筆，卻沒有列為不足（設定被靜默忽略）"
    )


# ── 三態與容器形狀（M-SU-1／C-3）──────────────────────────────────────────
def test_three_state_two_containers_cover_all_events() -> None:
    index, train, test, keys, man, _ = _basic_case()
    plan = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assigned = set(plan.assignments["event_id"])
    purged = set(plan.purged["event_id"])
    assert assigned & purged == set(), "三態互斥"
    assert assigned | purged == set(keys["event_id"]), "三態涵蓋全集"
    assert len(plan.assignments) + len(plan.purged) == len(keys)
    assert set(plan.assignments["split_label"]) <= {"train", "test"}, (
        "🔴 `assignments.split_label` 只能有兩值——多出第三值時只認兩值的下游會靜默少算"
    )


def test_purge_reason_uses_existing_contract_literal() -> None:
    index, train, test, keys, man, _ = _basic_case()
    plan = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert set(plan.purged["reason"]) == {"interval_crosses_split_boundary"}


# ── 🔴 第一段：答案窗 purge（M-SU-13）─────────────────────────────────────
def test_answer_window_crossing_train_event_is_purged() -> None:
    """答案窗伸進測試段的 **train** 事件必進 `purged`——事件側唯一擋洩漏的閘。"""
    index, train, test, keys, man, _ = _basic_case()
    plan = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert "e_train_leak" in set(plan.purged["event_id"])
    assert "e_train_leak" not in set(plan.assignments["event_id"])


def test_answer_window_boundary_is_ge_not_gt() -> None:
    """`>=` 必須保留：`label_end_ms` **恰等於** `test_start_ms` 也算跨界。"""
    index, train, test, _, _, test_start = _basic_case()
    exact = _event_keys([("e_exact", index[0], test_start)])
    plan = derive_event_split_from_plans(
        train, test, exact, index, manifest=_manifest(exact), bucket_ms=H1
    )
    assert list(plan.purged["event_id"]) == ["e_exact"]


def test_answer_window_not_applied_to_test_side_events() -> None:
    """第一段只針對 **train 側**——test 段事件的答案窗當然在 test 段內，不該被誤 purge。"""
    index, train, test, _, _, _ = _basic_case()
    t_rows = np.asarray(test.row_index, dtype=int)
    keys = _event_keys([("e_t", index[t_rows[0]], int(index[t_rows[-1]]))])
    plan = derive_event_split_from_plans(
        train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
    )
    assert list(plan.assignments["split_label"]) == ["test"]
    assert plan.purged.empty


# ── 第二段：集合成員判定（M-SU-4／M-SU-5）────────────────────────────────
def test_membership_set_not_interval() -> None:
    """🔴 成員判定必須是**集合**，不是 `time_bounds` 閉區間（`M-SU-4`）。

    設計理由（第一版沒抓到 mutation 的教訓）：train rows 是**連續**的，所以在**無洞**的
    feature_index 上「區間」與「集合」等價，怎麼測都分不出來。真正能分辨的是
    **post-trim 之後 index 有洞**的情形——那正是本票的實際場景（EVTALIGN 會裁掉列）。
    這裡刻意做一個中間缺了一段的 index：事件時間戳落在**洞裡**（仍在 train 的
    `time_bounds` 之內）⇒ 集合語意判 purged、區間語意會誤判成 train。
    """
    full = _feature_index()
    hole = list(range(30, 40))  # 挖掉 train 段中間 10 根
    kept = [int(v) for i, v in enumerate(np.asarray(full, dtype="int64")) if i not in hole]
    index = pd.Index(kept, dtype="int64")
    train, test, _ = _plans(index)
    tr = np.asarray(train.row_index, dtype=int)
    hole_ms = int(np.asarray(full, dtype="int64")[35])  # 洞裡的時間戳
    assert int(index[tr[0]]) < hole_ms < int(index[tr[-1]]), "洞必須落在 train 的 time_bounds 之內"
    keys = _event_keys([("e_hole", hole_ms, hole_ms + H1)])
    plan = derive_event_split_from_plans(
        train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
    )
    assert list(plan.purged["event_id"]) == ["e_hole"], (
        "落在 post-trim 洞裡的事件必須 purged——判成 train 表示實作用了區間而非集合"
    )
    assert plan.assignments.empty


def test_dual_membership_raises_not_silent_pick() -> None:
    """🔴 同時落在 train 與 test ⇒ raise，不靜默取一（`M-SU-6`）。

    設計理由：正常 plan 的 train/test 列集互斥，那道 raise 在正常輸入下**永遠走不到**，
    所以第一版測不出來。本測試餵**刻意重疊**的 plan——那是防禦性分支存在的唯一理由。
    """
    index, train, _, _, _, _ = _basic_case()
    tr = np.asarray(train.row_index, dtype=int)
    overlapping_test = _sp(
        split_label="test",
        index_kind="positional",
        row_index=tr,  # 與 train 完全重疊
        time_bounds=(int(index[tr[0]]), int(index[tr[-1]])),
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    keys = _event_keys([("e_dual", index[tr[0]], int(index[tr[0]]) + H1)])
    with pytest.raises(ValueError, match="同時落在 train 與 test"):
        derive_event_split_from_plans(
            train, overlapping_test, keys, index, manifest=_manifest(keys), bucket_ms=H1
        )


def test_unmatched_timestamp_is_purged_not_train() -> None:
    """完全不在 `feature_index` 上的事件（被裁掉、或落在兩根 bar 之間）⇒ purged，禁 nearest。"""
    index, train, test, _, _, _ = _basic_case()
    off_grid = int(index[0]) + H1 // 3  # 兩根之間
    keys = _event_keys([("e_off", off_grid, off_grid + H1)])
    plan = derive_event_split_from_plans(
        train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
    )
    assert list(plan.purged["event_id"]) == ["e_off"]
    assert plan.assignments.empty


# ── fail-closed（M-SU-2／M-SU-3／M-SU-6）─────────────────────────────────
def test_multi_symbol_is_fail_closed() -> None:
    """事件批含兩個 symbol ⇒ 與單一 plan symbol 不相等 ⇒ 擋下（SPEC C-2）。"""
    index, train, test, _, _, _ = _basic_case()
    keys = _event_keys(
        [("e1", index[0], int(index[0]) + H1), ("e2", index[1], int(index[1]) + H1, "BTCUSDT")]
    )
    with pytest.raises(ValueError, match="multi_symbol_projection_unsupported"):
        derive_event_split_from_plans(
            train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
        )


def test_plan_symbols_differ_is_fail_closed() -> None:
    """train 與 test plan 的 symbol 不同 ⇒ 邊界本身就跨批，必須擋。"""
    index, train, _, keys, man, _ = _basic_case()
    _, btc_test, _ = _plans(index, symbol="BTCUSDT")
    with pytest.raises(ValueError, match="plan 之 symbol 不同"):
        derive_event_split_from_plans(train, btc_test, keys, index, manifest=man, bucket_ms=H1)


def test_plan_universes_differ_is_fail_closed() -> None:
    """🔴 symbol 相同**不代表** universe 相同（B3 自查）。

    同一個 ETHUSDT 可以有裁切前／裁切後兩份特徵索引（實測 EVTALIGN 裁頭尾後邊界位移 67 小時）。
    兩 plan 各自建在不同 universe 上時，`row_index` 的同一個數字指的是不同的時刻 ⇒ 靜默錯分。
    `base_universe_hash` 是 `SplitPlan` 已經帶著的身份欄，投影原本完全沒看它。
    """
    index, train, test, keys, man, _ = _basic_case()
    other_universe = _sp(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray(test.row_index, dtype=int),
        time_bounds=test.time_bounds,
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="a-different-universe",   # ← 唯一的差別
        symbol=SYM,
    )
    with pytest.raises(ValueError, match="base_universe_hash 不同"):
        derive_event_split_from_plans(train, other_universe, keys, index, manifest=man, bucket_ms=H1)


def test_same_source_shifted_feature_index_is_fail_closed() -> None:
    """🔴 B3 review R1（三家獨立實跑）：`feature_index` **同長度整體平移** ⇒ 必須擋。

    grok 的反例逐字：control `ev3=test`，把 index 整體 +50 根後 `ev3` 變 `train`、
    `labels_equal=False`，而全程 `NO_RAISE`。`base_universe_hash` 只是**字面**，
    plan 帶著相同字面卻建在另一份網格上時，同一個 row number 指到不同時刻。

    🔴 D-001 (4.13) 上線後，這個反例改由**更前面**的入口重驗（逐列時刻指紋）擋下：
       平移後 `index_ms[rows]` 逐值不同 ⇒ 重算指紋 ≠ plan 攜帶值。斷言字面跟著改到
       實際擋下它的那道閘，**不是**放寬成「有 raise 就算過」。原本那道 `time_bounds`
       同源閘仍有自己的覆蓋，見 `-k time_bounds_inconsistent`。
    """
    index, train, test, keys, man, _ = _basic_case()
    shifted = pd.Index([int(v) + 50 * H1 for v in index], dtype="int64")
    with pytest.raises(ValueError, match="指紋不符"):
        derive_event_split_from_plans(train, test, keys, shifted, manifest=man, bucket_ms=H1)


def test_same_source_plans_from_shorter_grid_is_fail_closed() -> None:
    """🔴 B3 review R1（codex／composer 反例）：plan 建在**較短網格**、傳入長 `feature_index`。

    row_index 落在長 index 的長度內 ⇒ 既有的長度閘放行，但同一個 row number 指到不同時刻，
    投影**靜默成功**（composer 實跑 `RESULT: succeeded`；codex 實跑
    `RETURNED {'assignments': 2, 'purged': 2}`）。

    🔴 同上：D-001 (4.13) 之入口重驗排在 `time_bounds` 同源閘**之前**，兩份網格之
       逐列時刻不同 ⇒ 指紋先不符。
    """
    index, _, _, keys, man, _ = _basic_case()
    short = pd.Index([int(index[0]) + i * H1 * 2 for i in range(len(index))], dtype="int64")
    short_train, short_test, _ = _plans(short)          # 同 symbol、同 hash 字面，網格不同
    with pytest.raises(ValueError, match="指紋不符"):
        derive_event_split_from_plans(short_train, short_test, keys, index, manifest=man, bucket_ms=H1)


def test_plan_time_bounds_inconsistent_with_own_rows_is_fail_closed() -> None:
    """🔴 `time_bounds` 同源閘之**專屬**覆蓋（`-k time_bounds_inconsistent`）。

    指紋閘上線後，上面兩條 B3 反例改由指紋擋下；若不另立本條，這道閘會變成
    **沒有任何測試會因它被刪掉而變紅**的死碼。本條讓指紋**成立**（同一份網格、同一批
    列）而只把 plan 自己攜帶的 `time_bounds` 寫錯 ⇒ 只剩這道閘能擋。
    """
    index, train, test, keys, man, _ = _basic_case()
    bad_bounds = _sp(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray(test.row_index, dtype=int),
        time_bounds=(int(index[0]), int(index[1])),      # ← 唯一的差別：與自己的列不一致
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    with pytest.raises(ValueError, match="不同源"):
        derive_event_split_from_plans(train, bad_bounds, keys, index, manifest=man, bucket_ms=H1)


def test_same_source_accepts_datetime_time_bounds() -> None:
    """🔴 IC orchestrator 產出的 `time_bounds` 是 `pd.Timestamp`（不是 int ms）。

    同源對證必須接受它——否則 B4 把 IC 的 plan 接上投影時會被自己的守衛擋死。
    單位分派是**型別驅動**：datetime-like 轉毫秒；整數必須本來就是毫秒（餵秒會被擋）。
    """
    index, train, test, keys, man, _ = _basic_case()
    ts_train = _sp(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray(train.row_index, dtype=int),
        time_bounds=(pd.Timestamp(int(train.time_bounds[0]), unit="ms"),
                     pd.Timestamp(int(train.time_bounds[1]), unit="ms")),
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    plan = derive_event_split_from_plans(ts_train, test, keys, index, manifest=man, bucket_ms=H1)
    assert not plan.assignments.empty


def test_same_source_rejects_second_unit_time_bounds() -> None:
    """整數 `time_bounds` 只接受**毫秒**：餵秒必須被指名擋下（不得靜默 ×1000）。"""
    index, train, test, keys, man, _ = _basic_case()
    seconds = _sp(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray(train.row_index, dtype=int),
        time_bounds=(int(train.time_bounds[0]) // 1000, int(train.time_bounds[1]) // 1000),
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    with pytest.raises(ValueError, match="epoch seconds"):
        derive_event_split_from_plans(seconds, test, keys, index, manifest=man, bucket_ms=H1)


def test_single_symbol_batch_unaffected() -> None:
    index, train, test, keys, man, _ = _basic_case()
    derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)


def test_non_positional_index_kind_is_fail_closed() -> None:
    index, train, test, keys, man, _ = _basic_case()
    bad = _sp(
        split_label="test",
        index_kind="row_id",
        row_index=np.asarray(test.row_index, dtype=int),
        time_bounds=(0, 1),
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    with pytest.raises(ValueError, match="只接受 'positional'"):
        derive_event_split_from_plans(train, bad, keys, index, manifest=man, bucket_ms=H1)


def test_empty_test_rows_is_fail_closed_not_none_compare() -> None:
    """test 段為空 ⇒ 先 fail-closed，禁與 `None` 比較（R4 之 F1）。"""
    index, train, _, keys, man, _ = _basic_case()
    empty_test = _sp(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([], dtype=int),
        time_bounds=(-1, -1),
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    with pytest.raises(ValueError, match="missing_test_plan"):
        derive_event_split_from_plans(train, empty_test, keys, index, manifest=man, bucket_ms=H1)


def test_missing_train_plan_is_fail_closed() -> None:
    index, _, test, keys, man, _ = _basic_case()
    with pytest.raises(ValueError, match="missing_train_plan"):
        derive_event_split_from_plans(None, test, keys, index, manifest=man, bucket_ms=H1)


# ── 單位（M-SU-12）───────────────────────────────────────────────────────
def test_unit_normalize_rejects_seconds_index() -> None:
    """epoch **秒** 的 index 必須 raise，不得靜默算出 1970 的邊界。"""
    index, train, test, keys, man, _ = _basic_case()
    seconds = pd.Index(np.asarray(index, dtype="int64") // 1000)
    with pytest.raises(ValueError, match="looks like epoch seconds"):
        derive_event_split_from_plans(train, test, keys, seconds, manifest=man, bucket_ms=H1)


def test_unit_normalize_accepts_datetime_index() -> None:
    """DatetimeIndex 與 int64 毫秒 index 給出**相同**的三態結果。"""
    index, train, test, keys, man, _ = _basic_case()
    dt_index = pd.to_datetime(np.asarray(index, dtype="int64"), unit="ms")
    a = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    b = derive_event_split_from_plans(train, test, keys, dt_index, manifest=man, bucket_ms=H1)
    assert set(a.purged["event_id"]) == set(b.purged["event_id"])
    assert a.assignments.equals(b.assignments)


# ── clusters 與 summary（M-SU-7／C-5）────────────────────────────────────
def test_clusters_match_independent_frozen_oracle() -> None:
    """🔴 clusters 對**獨立** oracle（凍結 JSON）逐值相等，**不拿 `split_events` 當 oracle**。

    出生理由（B2b review `CODEX-R1-P2-05`）：我把分簇抽成共用函式之後，
    `split_events` 自己就呼叫 `build_time_clusters` ⇒ 拿它當 oracle 是**同義反覆**，
    原本那條「逐值相等」測試在重構那一刻就變成空的（而且它還是綠的）。
    ⇒ oracle 改成依 `w = 1/n` 之定義**手推**並凍結的 JSON，與被測程式無因果關係。

    🔴 fixture 必須含**共桶**事件（`c2`／`c3` 權重 0.5）——每事件各自成簇時權重恆 1.0，
    把公式改寫死成 `1.0` 也測不出來。
    """
    oracle_path = (
        Path(__file__).resolve().parents[3] / "tests" / "golden" / "splitunify"
        / "clusters_oracle.json"
    )
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    keys = _event_keys(
        [(r["event_id"], r["decision_at_ms"], r["decision_at_ms"] + H1) for r in oracle["fixture"]]
    )
    got = build_time_clusters(_manifest(keys), int(oracle["bucket_ms"]))
    expected = pd.DataFrame(oracle["expected_clusters"])
    expected["time_cluster_id"] = expected["time_cluster_id"].astype("int64")
    pd.testing.assert_frame_equal(
        got.reset_index(drop=True), expected.reset_index(drop=True), check_like=False
    )
    assert set(got["cluster_weight"]) == {1.0, 0.5}, (
        "fixture 必須含共桶事件，否則權重恆 1.0、公式被改寫死也測不出來"
    )


def test_clusters_still_agree_with_split_events_shape() -> None:
    """輔助（**不是** oracle）：`split_events` 的 clusters 與共用實作同形。

    抽出後兩者本來就是同一支，本測試只擋「有人把 `split_events` 改回自己算」，
    不能當正確性 oracle——那是上一條的職責。
    """
    oracle = json.loads(
        (
            Path(__file__).resolve().parents[3] / "tests" / "golden" / "splitunify"
            / "clusters_oracle.json"
        ).read_text(encoding="utf-8")
    )
    keys = _event_keys(
        [(r["event_id"], r["decision_at_ms"], r["decision_at_ms"] + H1) for r in oracle["fixture"]]
    )
    man = _manifest(keys)
    legacy = split_events(
        man, EventSplitConfig(test_fraction=0.4, bucket_ms=H1, tier_min_test_events=0)
    )
    pd.testing.assert_frame_equal(build_time_clusters(man, H1), legacy.clusters)


def test_summary_has_all_twelve_keys() -> None:
    index, train, test, keys, man, _ = _basic_case()
    plan = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert set(plan.summary) == {
        "n_symbols",
        "per_symbol_n",
        "n_time_clusters",
        "avg_cluster_size",
        "degraded",
        "loso_status",
        "insufficient_events_in_test",
        "stats_modes",
        "n_events_raw",
        "n_events_effective",
        "n_purged",
        "bucket_ms",
    }
    assert plan.summary["n_purged"] == len(plan.purged)
    assert "single_symbol" in plan.summary["degraded"], (
        "多 symbol 已 fail-closed ⇒ 存活路徑恆單 symbol，本旗標恆亮是**預期的**；"
        "不得為了讓 formal_pooled_inference_allowed 變 True 而清空 degraded"
    )


# ── 邊界 ─────────────────────────────────────────────────────────────────
def test_empty_event_keys_gives_empty_three_states() -> None:
    """空批 ⇒ 三態皆空（不 raise）。manifest 也必須是**同一批**（即同樣為空）。"""
    index, train, test, _, _, _ = _basic_case()
    keys = pd.DataFrame(columns=list(_event_keys([("x", 0, 0)]).columns))
    man = _manifest(keys)
    plan = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert plan.assignments.empty and plan.purged.empty


# ── 身份對帳（H1／H2；B2b review 之 CODEX-R1-P1-01／P1-02）──────────────
def test_manifest_id_mismatch_is_fail_closed() -> None:
    """🔴 餵**另一批** manifest 必須 raise，不得產出「看起來成功」的 assignment。"""
    index, train, test, keys, _, _ = _basic_case()
    foreign = _manifest(_event_keys([("foreign", int(index[0]), int(index[0]) + H1)]))
    with pytest.raises(ValueError, match="event_id 集合不相等"):
        derive_event_split_from_plans(train, test, keys, index, manifest=foreign, bucket_ms=H1)


def test_manifest_superset_is_also_rejected() -> None:
    """**不接受 subset**——要子集就由呼叫端先裁好 manifest，別讓函式猜。"""
    index, train, test, keys, _, _ = _basic_case()
    extra = pd.concat(
        [keys, _event_keys([("extra", int(index[0]), int(index[0]) + H1)])], ignore_index=True
    )
    with pytest.raises(ValueError, match="不接受 subset"):
        derive_event_split_from_plans(
            train, test, keys, index, manifest=_manifest(extra), bucket_ms=H1
        )


def test_plan_symbol_mismatch_is_fail_closed() -> None:
    """🔴 單一 ETH 事件配單一 **BTC** plan 必須 raise——只看基數擋不住錯誤邊界歸屬。"""
    index, _, _, keys, man, _ = _basic_case()
    btc_train, btc_test, _ = _plans(index, symbol="BTCUSDT")
    with pytest.raises(ValueError, match="與 plan symbol"):
        derive_event_split_from_plans(
            btc_train, btc_test, keys, index, manifest=man, bucket_ms=H1
        )


def test_plan_without_symbol_is_fail_closed() -> None:
    """plan 沒有 symbol ⇒ 無法證明邊界屬於本批。"""
    index, train, test, keys, man, _ = _basic_case()
    anon = _sp(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray(train.row_index, dtype=int),
        time_bounds=train.time_bounds,
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=None,
    )
    anon_test = _sp(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray(test.row_index, dtype=int),
        time_bounds=test.time_bounds,
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=None,
    )
    with pytest.raises(ValueError, match="plan 未帶 symbol"):
        derive_event_split_from_plans(anon, anon_test, keys, index, manifest=man, bucket_ms=H1)


# ── malformed feature index（H3；CODEX-R1-P1-03）─────────────────────────
def test_mixed_unit_index_is_fail_closed() -> None:
    """🔴 **混合**單位（部分秒、部分毫秒）必須 raise——`np.all(...)` 會直接放行。"""
    index, train, test, keys, man, _ = _basic_case()
    mixed = np.asarray(index, dtype="int64").copy()
    mixed[5] = mixed[5] // 1000  # 只有一格是秒
    with pytest.raises(ValueError, match="混合"):
        derive_event_split_from_plans(
            train, test, keys, pd.Index(mixed), manifest=man, bucket_ms=H1
        )


def test_negative_row_index_is_fail_closed() -> None:
    """🔴 負 positional index 必須 raise——numpy 會回捲成尾端列，靜默給錯歸屬。"""
    index, train, test, keys, man, _ = _basic_case()
    bad = _sp(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray([-3, -2, -1], dtype=int),
        time_bounds=train.time_bounds,
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    with pytest.raises(ValueError, match="含負值"):
        derive_event_split_from_plans(bad, test, keys, index, manifest=man, bucket_ms=H1)


def test_row_index_out_of_range_is_fail_closed() -> None:
    index, train, test, keys, man, _ = _basic_case()
    bad = _sp(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray([0, 1, N_BARS + 5], dtype=int),
        time_bounds=train.time_bounds,
        purge_gap=PURGE,
        embargo=EMBARGO,
        purge_semantic="rows",
        base_universe_hash="deadbeef",
        symbol=SYM,
    )
    with pytest.raises(ValueError, match="超出 universe 長度"):
        derive_event_split_from_plans(bad, test, keys, index, manifest=man, bucket_ms=H1)


# ── 輸入不變式（B2b R2 之 I1–I6）─────────────────────────────────────────
def test_unsorted_feature_index_is_fail_closed() -> None:
    """🔴 `feature_index` 非嚴格遞增 ⇒ raise（I1；grok／codex／主委三方獨立收斂）。

    下游以 `test_rows[0]` 取「測試段最早時刻」；反序時那個值不是最早的
    ⇒ 答案窗比較用到錯的邊界，且**完全靜默**。
    """
    index, train, test, keys, man, _ = _basic_case()
    reversed_index = pd.Index(np.asarray(index, dtype="int64")[::-1])
    with pytest.raises(ValueError, match="非嚴格遞增"):
        derive_event_split_from_plans(
            train, test, keys, reversed_index, manifest=man, bucket_ms=H1
        )


def test_duplicate_feature_index_timestamps_is_fail_closed() -> None:
    """重複時間戳讓集合成員判定失去唯一性 ⇒ raise（I1 之另一半）。"""
    index, train, test, keys, man, _ = _basic_case()
    dup = np.asarray(index, dtype="int64").copy()
    dup[10] = dup[9]
    with pytest.raises(ValueError, match="重複"):
        derive_event_split_from_plans(train, test, keys, pd.Index(dup), manifest=man, bucket_ms=H1)


def test_nan_in_numeric_index_is_fail_closed() -> None:
    """🔴 數值型索引含 NaN ⇒ raise（I2）：`astype(int64)` 會把 NaN 變成 0 而不報錯。"""
    index, train, test, keys, man, _ = _basic_case()
    with_nan = np.asarray(index, dtype="float64").copy()
    with_nan[3] = np.nan
    with pytest.raises(ValueError, match="NaN／inf"):
        derive_event_split_from_plans(
            train, test, keys, pd.Index(with_nan), manifest=man, bucket_ms=H1
        )


def test_duplicate_event_id_is_fail_closed() -> None:
    """🔴 `event_keys.event_id` 重複 ⇒ raise（I3）：集合相等會**吃掉重複**。"""
    index, train, test, keys, _, _ = _basic_case()
    dup = pd.concat([keys, keys.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="event_id 重複"):
        derive_event_split_from_plans(
            train, test, dup, index, manifest=_manifest(dup.drop_duplicates("event_id")),
            bucket_ms=H1,
        )


def test_float_row_index_is_fail_closed() -> None:
    """🔴 非整數 `row_index` ⇒ raise（I4）：`dtype=int` 截斷（0.5→0）是**靜默改變歸屬**。"""
    index, train, test, keys, man, _ = _basic_case()
    bad = _sp(
        split_label="train", index_kind="positional",
        row_index=np.asarray([0.5, 1.5, 2.5, 3.5, 4.5]),
        time_bounds=train.time_bounds, purge_gap=PURGE, embargo=EMBARGO,
        purge_semantic="rows", base_universe_hash="deadbeef", symbol=SYM,
    )
    with pytest.raises(ValueError, match="非整數值"):
        derive_event_split_from_plans(bad, test, keys, index, manifest=man, bucket_ms=H1)


def test_inverted_answer_window_is_fail_closed() -> None:
    """🔴 `label_start_ms > label_end_ms` ⇒ raise（I5）：反轉的窗不是『比較短』，是壞掉。"""
    index, train, test, _, _, _ = _basic_case()
    inverted = _event_keys([("e_inv", index[0], int(index[0]) - H1)])
    with pytest.raises(ValueError, match="答案窗反轉"):
        derive_event_split_from_plans(
            train, test, inverted, index, manifest=_manifest(inverted), bucket_ms=H1
        )


def test_event_keys_may_share_timestamps() -> None:
    """🔴 反向保護：事件欄**可以**重複（兩事件同一根 bar 是正常的），不得被單調性誤擋。

    出生理由：我第一版把嚴格遞增套到事件欄上，當場誤擋合法輸入。
    """
    index, train, test, _, _, _ = _basic_case()
    same = _event_keys(
        [("e1", index[0], int(index[0]) + H1), ("e2", index[0], int(index[0]) + H1)]
    )
    plan = derive_event_split_from_plans(
        train, test, same, index, manifest=_manifest(same), bucket_ms=H1
    )
    assert len(plan.assignments) + len(plan.purged) == 2


def test_non_positive_bucket_ms_is_fail_closed() -> None:
    """🔴 `bucket_ms <= 0` ⇒ raise（I6）：`0` 原本只是靠 pandas 例外**巧合**擋住。"""
    index, _, _, keys, man, _ = _basic_case()
    for bad_bucket in (0, -1):
        with pytest.raises(ValueError, match="須為正整數"):
            build_time_clusters(man, bad_bucket)


def test_datetime_index_unsorted_is_fail_closed() -> None:
    """🔴 `DatetimeIndex` **也要**過遞增檢查（J1）——R2 只修了數值分支，這支繞過去了。"""
    index, train, test, keys, man, _ = _basic_case()
    dt_desc = pd.to_datetime(np.asarray(index, dtype="int64")[::-1], unit="ms")
    with pytest.raises(ValueError, match="非嚴格遞增"):
        derive_event_split_from_plans(train, test, keys, dt_desc, manifest=man, bucket_ms=H1)


def test_unsorted_row_index_is_fail_closed() -> None:
    """🔴 `row_index` **反序** ⇒ raise（J2）：範圍與唯一性都對，但 `row_index[0]` 不是最早的列。"""
    index, train, test, keys, man, _ = _basic_case()
    rev = _sp(
        split_label="test", index_kind="positional",
        row_index=np.asarray(test.row_index, dtype=int)[::-1],
        time_bounds=test.time_bounds, purge_gap=PURGE, embargo=EMBARGO,
        purge_semantic="rows", base_universe_hash="deadbeef", symbol=SYM,
    )
    with pytest.raises(ValueError, match="row_index 非嚴格遞增"):
        derive_event_split_from_plans(train, rev, keys, index, manifest=man, bucket_ms=H1)


def test_none_symbol_is_fail_closed() -> None:
    """🔴 `event_keys.symbol` 全為 `None` ⇒ raise（J3；三家獨立命中）。

    原本先 `if s is not None` 濾掉 ⇒ 空集合 ⇒ 後面的 `if symbols and ...` 整條被跳過
    ＝ **fail-open**，還會輸出 `symbol=None` 的 assignment。
    """
    index, train, test, _, _, _ = _basic_case()
    keys = _event_keys([("e", index[0], int(index[0]) + H1, None)])
    with pytest.raises(ValueError, match="含 None／空字串"):
        derive_event_split_from_plans(
            train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
        )


def test_blank_symbol_is_fail_closed() -> None:
    """空字串 symbol 同樣擋——`str(s)` 會把它變成合法值，但它不是身份。"""
    index, train, test, _, _, _ = _basic_case()
    keys = _event_keys([("e", index[0], int(index[0]) + H1, "  ")])
    with pytest.raises(ValueError, match="含 None／空字串"):
        derive_event_split_from_plans(
            train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
        )


def test_answer_window_one_ms_before_test_start_is_purged() -> None:
    """🔴 `label_end` 落在 canonical test start **前 1ms** 的 train 事件——不該 purge。

    出生理由（`CODEX-R1-P2-05`／`GROK-R1-P2-02`）：現有 fixture 用 `exact-equal`
    （`label_end == test_start`），所以「把條件改成 `>= test_start - 1`」或「誤減 embargo」
    這兩種 mutation 在 H1 對齊的 fixture 上**仍然全綠**＝假綠。
    本測試釘住**邊界的另一側**：差 1 毫秒就不該被 purge。
    """
    index, train, test, _, _, test_start = _basic_case()
    keys = _event_keys([("e_near", index[0], test_start - 1)])
    plan = derive_event_split_from_plans(
        train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
    )
    assert list(plan.assignments["split_label"]) == ["train"], (
        "差 1 毫秒就被 purge ⇒ 條件式比契約嚴（多減了緩衝）"
    )
    assert plan.purged.empty


def test_all_purged_is_legal_output() -> None:
    """全部落在隔離區 ⇒ `assignments` 空而 `purged` 為全集（`tables.py:201` 已明載不得誤擋）。"""
    index, train, test, _, _, _ = _basic_case()
    tr = np.asarray(train.row_index, dtype=int)
    gap = int(index[tr[-1]]) + H1
    keys = _event_keys([("g1", gap, gap + H1), ("g2", gap, gap + H1)])
    plan = derive_event_split_from_plans(
        train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
    )
    assert plan.assignments.empty
    assert len(plan.purged) == 2


# ── build_event_keys（R4 之 F2：producer 具名，禁 positional zip）────────
def _receipts(event_rows, per_tf_rows) -> AlignmentReceipts:
    return AlignmentReceipts(
        event_level=pd.DataFrame(event_rows),
        per_tf=pd.DataFrame(per_tf_rows),
    )


def test_build_event_keys_joins_by_event_id_not_position() -> None:
    """🔴 以 `event_id` 對位——`per_tf` 的**列序刻意與 `event_level` 相反**。

    若實作用 positional zip，兩筆的 `feature_cutoff_ms` 會對調 ⇒ 本測試紅。
    """
    ev = [
        {"event_id": "a", "symbol": SYM, "timeframe": "1h",
         "label_start_ms": 10, "label_end_ms": 20},
        {"event_id": "b", "symbol": SYM, "timeframe": "1h",
         "label_start_ms": 30, "label_end_ms": 40},
    ]
    per_tf = [  # 反序
        {"event_id": "b", "timeframe": "1h", "feature_cutoff_ms": 3000},
        {"event_id": "a", "timeframe": "1h", "feature_cutoff_ms": 1000},
    ]
    keys = build_event_keys(_receipts(ev, per_tf), selected_timeframe="1h")
    got = dict(zip(keys["event_id"], keys["feature_cutoff_ms"]))
    assert got == {"a": 1000, "b": 3000}
    assert list(keys.columns) == list(EVENT_KEY_COLUMNS)


def test_build_event_keys_picks_selected_timeframe_only() -> None:
    """`per_tf` 每個事件可有多個 TF——只取被選中的那一個，不得混用。"""
    ev = [{"event_id": "a", "symbol": SYM, "timeframe": "12h",
           "label_start_ms": 10, "label_end_ms": 20}]
    per_tf = [
        {"event_id": "a", "timeframe": "1h", "feature_cutoff_ms": 1000},
        {"event_id": "a", "timeframe": "12h", "feature_cutoff_ms": 9000},
    ]
    keys = build_event_keys(_receipts(ev, per_tf), selected_timeframe="12h")
    assert list(keys["feature_cutoff_ms"]) == [9000]


def test_build_event_keys_rejects_duplicate_per_tf_rows() -> None:
    """同一事件在被選 TF 下有多列 ⇒ raise（多 TF 複合鍵為殘留 `SU-RESID-2`）。"""
    ev = [{"event_id": "a", "symbol": SYM, "timeframe": "1h",
           "label_start_ms": 10, "label_end_ms": 20}]
    per_tf = [
        {"event_id": "a", "timeframe": "1h", "feature_cutoff_ms": 1000},
        {"event_id": "a", "timeframe": "1h", "feature_cutoff_ms": 2000},
    ]
    with pytest.raises(ValueError, match="多列 per_tf"):
        build_event_keys(_receipts(ev, per_tf), selected_timeframe="1h")


def test_build_event_keys_rejects_duplicate_event_level_rows() -> None:
    """🔴 `event_level` 本身有重複 `event_id` ⇒ merge 之 `validate="1:1"` 必須擋。

    出生理由（B2b review `CODEX-R1-P2-05` 之 `M-SU-15`）：我原本只擋 `per_tf` 的重複，
    `event_level` 的重複沒有任何測試——拿掉 `validate="1:1"` 也不會紅。
    """
    ev = [
        {"event_id": "a", "symbol": SYM, "timeframe": "1h",
         "label_start_ms": 10, "label_end_ms": 20},
        {"event_id": "a", "symbol": SYM, "timeframe": "1h",
         "label_start_ms": 11, "label_end_ms": 21},  # 重複 event_id
    ]
    per_tf = [{"event_id": "a", "timeframe": "1h", "feature_cutoff_ms": 1000}]
    with pytest.raises(Exception):  # pandas MergeError（validate="1:1"）
        build_event_keys(_receipts(ev, per_tf), selected_timeframe="1h")


def test_build_event_keys_rejects_missing_cutoff() -> None:
    """事件在被選 TF 下沒有 cutoff ⇒ raise，**不補預設**。"""
    ev = [
        {"event_id": "a", "symbol": SYM, "timeframe": "1h",
         "label_start_ms": 10, "label_end_ms": 20},
        {"event_id": "b", "symbol": SYM, "timeframe": "1h",
         "label_start_ms": 30, "label_end_ms": 40},
    ]
    per_tf = [{"event_id": "a", "timeframe": "1h", "feature_cutoff_ms": 1000}]
    with pytest.raises(ValueError, match="缺 cutoff"):
        build_event_keys(_receipts(ev, per_tf), selected_timeframe="1h")


def test_purity_does_not_mutate_inputs() -> None:
    index, train, test, keys, man, _ = _basic_case()
    keys_before = keys.copy()
    table_before = man.table.copy()
    derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    pd.testing.assert_frame_equal(keys, keys_before)
    pd.testing.assert_frame_equal(man.table, table_before)


# ══════════════════════════════════════════════════════════════════════════════
# D-001 Task 8.1／8.3：per-symbol 投影與逐標的門檻
#
# 🔴 本節測試名刻意含 `per_symbol`／`insufficient`：SPEC 的驗收命令是
#    `-k per_symbol`／`-k insufficient`。2026-09-12 實測本檔這兩個關鍵字
#    **各收到 0 條**（`56 deselected / 0 selected`）——驗收命令 rc=0 但零覆蓋。
#    命名對不上驗收命令，等於沒有驗收。
# ══════════════════════════════════════════════════════════════════════════════

SYM_B = "BTCUSDT"


def _plan_pair_for(symbol: str, short_index: pd.Index, positions: np.ndarray):
    """以該標的**自己的短索引**建 plan 對。

    `row_index`＝全框位置、`row_index_local`＝標的內序號、指紋以短索引之時刻計算——
    這正是 D-001 (4.3)／(4.4) 對 producer 的要求。
    """
    b = holdout_boundary(short_index, oos_test_size=OOS, purge_gap=PURGE, embargo=EMBARGO)
    ms = np.asarray(short_index, dtype="int64")
    kw = dict(index_kind="positional", purge_gap=PURGE, embargo=EMBARGO,
              purge_semantic="rows", base_universe_hash="deadbeef", symbol=symbol)

    def _mk(label: str, local) -> SplitPlan:
        loc = np.asarray(local, dtype=int)
        return SplitPlan(
            split_label=label,
            row_index=np.asarray(positions[loc], dtype=int),
            time_bounds=(int(ms[loc[0]]), int(ms[loc[-1]])),
            row_index_local=loc,
            row_time_fingerprint=build_row_time_fingerprint(
                positions=loc, feature_ts_ms=ms[loc],
                symbol=symbol, base_universe_hash="deadbeef",
            ),
            **kw,
        )

    return _mk("train", b["train_row_index"]), _mk("test", b["test_row_index"]), b


def _interleaved_case(*, n_test_events=(1, 3)):
    """兩標的於**全框交錯**：偶數列屬 A（ETHUSDT）、奇數列屬 B（BTCUSDT）。

    每個標的的短索引長 50，而其全框 `row_index` 最大值是 98／99 ⇒ 投影端若拿全框列號
    去索引該標的的短索引就必定越界。交錯正是 D-001 (4.18) 指定必測的形態，
    因為「等長且不交錯」的 fixture 會讓 `row_index` 與 `row_index_local` 剛好相等，
    把該擋的錯誤藏起來。
    """
    full = _feature_index()
    pos = {SYM: np.arange(0, N_BARS, 2, dtype=int), SYM_B: np.arange(1, N_BARS, 2, dtype=int)}
    idx = {s: pd.Index([int(full[p]) for p in pos[s]], dtype="int64") for s in pos}
    plans, bounds, rows = {}, {}, []
    for s, n_test in zip((SYM, SYM_B), n_test_events):
        tr, te, b = _plan_pair_for(s, idx[s], pos[s])
        plans[s], bounds[s] = (tr, te), b
        ms = np.asarray(idx[s], dtype="int64")
        t0 = int(ms[b["train_row_index"][0]])
        rows.append((f"{s}_train", t0, t0 + H1, s))
        for k in range(n_test):
            tk = int(ms[b["test_row_index"][k]])
            rows.append((f"{s}_test{k}", tk, tk + H1, s))
    keys = _event_keys(rows)
    return plans, idx, keys, _manifest(keys), bounds


def test_per_symbol_projection_assigns_both_symbols() -> None:
    """兩標的皆進 assignments（Task 8.1 斷言 1）。"""
    plans, idx, keys, man, _ = _interleaved_case()
    res = derive_event_split_from_plans(plans, keys, idx, manifest=man, bucket_ms=H1)
    assert set(res.assignments["symbol"]) == {SYM, SYM_B}
    assert res.summary["n_symbols"] == 2


def test_per_symbol_plans_mapping_without_index_mapping_is_fail_closed() -> None:
    """給了 plans Mapping 卻沒給對應的索引 Mapping ⇒ 擋（Task 8.1 斷言 2）。"""
    plans, idx, keys, man, _ = _interleaved_case()
    with pytest.raises(ValueError, match="multi_symbol_projection_unsupported"):
        derive_event_split_from_plans(plans, keys, idx[SYM], manifest=man, bucket_ms=H1)


def test_per_symbol_event_symbol_missing_from_plans_is_fail_closed() -> None:
    """事件有 B 而 plans 只有 A ⇒ 須**指名不一致**，且不得再用「不支援多標的」那個字面。

    🔴 Task 8.1 斷言 3 明文要求訊息**不得**含 `multi_symbol_projection_unsupported`：
    多標的現在已經支援了，再用那個字面會把「你漏給了一個標的」誤導成「本功能不支援」。
    """
    plans, idx, keys, man, _ = _interleaved_case()
    with pytest.raises(ValueError) as ei:
        derive_event_split_from_plans(
            {SYM: plans[SYM]}, keys, {SYM: idx[SYM]}, manifest=man, bucket_ms=H1
        )
    msg = str(ei.value)
    assert "不一致" in msg
    assert "multi_symbol_projection_unsupported" not in msg


def test_per_symbol_shared_universe_hash_is_allowed() -> None:
    """跨 symbol **共用**同一個 `base_universe_hash` 字面是合法的（整框 joint hash）。

    D-001 定案：禁把「跨 symbol 必互異」寫成閘——現行 IC 多標的計畫正是共用一份。
    """
    plans, idx, keys, man, _ = _interleaved_case()
    assert plans[SYM][0].base_universe_hash == plans[SYM_B][0].base_universe_hash
    res = derive_event_split_from_plans(plans, keys, idx, manifest=man, bucket_ms=H1)
    assert res.summary["n_symbols"] == 2


def test_per_symbol_crossed_feature_index_is_fail_closed() -> None:
    """以 A 的索引去解釋 B 的 `row_index_local` ⇒ 擋（Task 8.1 斷言 5）。"""
    plans, idx, keys, man, _ = _interleaved_case()
    crossed = {SYM: idx[SYM], SYM_B: idx[SYM]}
    with pytest.raises(ValueError):
        derive_event_split_from_plans(plans, keys, crossed, manifest=man, bucket_ms=H1)


def test_per_symbol_interleaved_never_indexes_full_frame() -> None:
    """B 的全框列號超出自己短索引長度 ⇒ 投影仍須成功且不得 IndexError（斷言 6）。"""
    plans, idx, keys, man, _ = _interleaved_case()
    assert int(np.asarray(plans[SYM_B][1].row_index).max()) >= len(idx[SYM_B])
    res = derive_event_split_from_plans(plans, keys, idx, manifest=man, bucket_ms=H1)
    assert not res.assignments.empty


def test_per_symbol_interleaved_matches_single_symbol_run() -> None:
    """B 的歸屬在「兩標的一起跑」與「只跑 B」之下必須逐筆相同（斷言 7）。"""
    plans, idx, keys, man, _ = _interleaved_case()
    both = derive_event_split_from_plans(plans, keys, idx, manifest=man, bucket_ms=H1)
    b_keys = keys[keys["symbol"] == SYM_B].reset_index(drop=True)
    solo = derive_event_split_from_plans(
        {SYM_B: plans[SYM_B]}, b_keys, {SYM_B: idx[SYM_B]},
        manifest=_manifest(b_keys), bucket_ms=H1,
    )
    got = dict(zip(both.assignments["event_id"], both.assignments["split_label"]))
    want = dict(zip(solo.assignments["event_id"], solo.assignments["split_label"]))
    assert want, "只跑 B 卻沒有任何歸屬 ⇒ 這條比較是空洞的"
    assert {k: v for k, v in got.items() if str(k).startswith(SYM_B)} == want


def test_per_symbol_degraded_clears_with_two_symbols() -> None:
    """`n_symbols == 2` ⇒ `single_symbol` 不得亮（斷言 8）。"""
    plans, idx, keys, man, _ = _interleaved_case()
    res = derive_event_split_from_plans(plans, keys, idx, manifest=man, bucket_ms=H1)
    assert "single_symbol" not in res.summary["degraded"]


def test_per_symbol_degraded_set_with_one_symbol() -> None:
    """`n_symbols == 1` ⇒ `single_symbol` 必須亮（斷言 9；解除條件不得放寬）。"""
    plans, idx, keys, man, _ = _interleaved_case()
    a_keys = keys[keys["symbol"] == SYM].reset_index(drop=True)
    res = derive_event_split_from_plans(
        {SYM: plans[SYM]}, a_keys, {SYM: idx[SYM]},
        manifest=_manifest(a_keys), bucket_ms=H1,
    )
    assert res.summary["n_symbols"] == 1
    assert "single_symbol" in res.summary["degraded"]


def test_insufficient_events_in_test_is_per_symbol_not_batch() -> None:
    """A 只有 1 筆 test、B 有 3 筆，門檻 2 ⇒ **只**標 A（Task 8.3 斷言 1）。

    退回整批 `n_test`（1+3=4 ≥ 2）就會變成一個都不標，這條即紅。
    """
    plans, idx, keys, man, _ = _interleaved_case(n_test_events=(1, 3))
    res = derive_event_split_from_plans(
        plans, keys, idx, manifest=man, bucket_ms=H1, tier_min_test_events=2,
    )
    assert sorted(res.summary["insufficient_events_in_test"]) == [SYM]


def test_insufficient_events_in_test_empty_when_all_above_threshold() -> None:
    """兩標的都達標 ⇒ 清單為空（Task 8.3 斷言 2）。"""
    plans, idx, keys, man, _ = _interleaved_case(n_test_events=(3, 3))
    res = derive_event_split_from_plans(
        plans, keys, idx, manifest=man, bucket_ms=H1, tier_min_test_events=2,
    )
    assert res.summary["insufficient_events_in_test"] == []


def test_per_symbol_mapping_key_not_matching_plan_symbol_is_fail_closed() -> None:
    """三角相等的**第三邊**：Mapping 的 key 與該 plan 自己的 `plan.symbol` 不一致 ⇒ 擋。

    分派器只比對「事件 symbol 集合 vs plans 之鍵」兩邊；第三邊靠逐 symbol 進入單標的
    路徑後的 `plan.symbol` 對證承擔。這條把它釘住——兩邊相等但 plan 裝錯不得放行。
    """
    plans, idx, keys, man, _ = _interleaved_case()
    swapped = {SYM: plans[SYM_B], SYM_B: plans[SYM]}   # 鍵與 plan.symbol 對調
    with pytest.raises(ValueError):
        derive_event_split_from_plans(swapped, keys, idx, manifest=man, bucket_ms=H1)


# ══════════════════════════════════════════════════════════════════════════════
# D-001 Task 8.2：逐列時刻同源對證（`-k fingerprint`）
#
# 🔴 同上：`-k fingerprint` 在 2026-09-12 實測亦為 0 selected。
# 🔴 指紋與遞增閘是**合取**：指紋先依序號排序再雜湊 ⇒ 對同集合重排**無感**，
#    擋重排的是遞增閘；兩者各有一條測試，缺一不可。
# ══════════════════════════════════════════════════════════════════════════════


def test_fingerprint_mid_row_shift_caught_though_endpoints_match() -> None:
    """首尾時刻相同、只有**中間一列**不同 ⇒ 必須擋（SU-RESID-3 的整條理由）。

    `time_bounds` 同源閘只看首尾，這個形態它看不出來；擋下它的是逐列指紋。
    """
    index, train, test, keys, man, _ = _basic_case()
    vals = [int(v) for v in index]
    mid = len(vals) // 2
    vals[mid] += 1                      # 仍嚴格遞增、首尾不變
    tampered = pd.Index(vals, dtype="int64")
    with pytest.raises(ValueError, match="指紋不符"):
        derive_event_split_from_plans(train, test, keys, tampered, manifest=man, bucket_ms=H1)


def test_fingerprint_passes_when_index_is_identical() -> None:
    """逐列相同 ⇒ 放行（避免上面那條是靠「什麼都擋」通過的）。"""
    index, train, test, keys, man, _ = _basic_case()
    res = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert not res.assignments.empty


def test_fingerprint_is_deterministic_across_recomputation() -> None:
    """同一組輸入重算兩次 ⇒ 值相同（否則入口重驗會隨機失敗）。"""
    index, _, _, _, _, _ = _basic_case()
    rows = np.arange(10, dtype=int)
    ms = np.asarray(index, dtype="int64")
    kw = dict(symbol=SYM, base_universe_hash="deadbeef")
    first = build_row_time_fingerprint(positions=rows, feature_ts_ms=ms[rows], **kw)
    second = build_row_time_fingerprint(positions=rows, feature_ts_ms=ms[rows], **kw)
    assert first == second


def test_fingerprint_of_empty_rows_is_sha256_of_empty_list() -> None:
    """空 `row_index` ⇒ 指紋 == `sha256("[]")`（釘住空集合的字面，不得改成空字串）。"""
    import hashlib

    got = build_row_time_fingerprint(
        positions=np.asarray([], dtype=int),
        feature_ts_ms=np.asarray([], dtype="int64"),
        symbol=SYM,
        base_universe_hash="deadbeef",
    )
    assert got == hashlib.sha256("[]".encode("utf-8")).hexdigest()


def test_fingerprint_missing_column_is_fail_closed() -> None:
    """缺 `row_time_fingerprint` ⇒ 擋，且訊息須指名缺的是哪一欄。"""
    index, train, test, keys, man, _ = _basic_case()
    object.__setattr__(train, "row_time_fingerprint", "")
    with pytest.raises(ValueError, match="row_time_fingerprint"):
        derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)


def test_fingerprint_missing_row_index_local_is_fail_closed() -> None:
    """缺 `row_index_local` ⇒ 擋，且**不得**以 `row_index` 回退（回退正是越界之來源）。"""
    index, train, test, keys, man, _ = _basic_case()
    object.__setattr__(train, "row_index_local", None)
    with pytest.raises(ValueError, match="row_index_local"):
        derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)


def test_fingerprint_independent_oracle_matches_producer_value() -> None:
    """由 fixture 重算之值 == producer 寫入 plan 的那一份（兩端同一支序列化器）。"""
    index, train, _, _, _, _ = _basic_case()
    ms = np.asarray(index, dtype="int64")
    loc = np.asarray(train.row_index_local, dtype=int)
    oracle = build_row_time_fingerprint(
        positions=loc, feature_ts_ms=ms[loc], symbol=SYM, base_universe_hash="deadbeef",
    )
    assert oracle == train.row_time_fingerprint


def test_fingerprint_reordered_rows_are_caught_by_monotonic_gate() -> None:
    """同集合**重排** ⇒ 指紋不變（排序後雜湊），必須由遞增閘擋下。

    這條若紅而 `-k fingerprint` 其餘皆綠，代表有人把遞增閘關掉了（`M-SU-D1-19`／`20`）。

    🔴 斷言**必須指名遞增閘**。原本只寫 `pytest.raises(ValueError)`，而重排會讓首列時刻
    跟著變、被 `time_bounds` 同源閘先擋下並丟出同一種例外 ⇒ 把遞增閘整個拿掉
    （`M-SU-D1-19`／`20`）這條照樣通過。那是廉價綠燈，2026-09-12 的 mutation 自證撈出來的。
    """
    index, train, test, keys, man, _ = _basic_case()
    loc = np.asarray(train.row_index_local, dtype=int).copy()
    loc[0], loc[1] = loc[1], loc[0]
    object.__setattr__(train, "row_index_local", loc)
    with pytest.raises(ValueError, match="非嚴格遞增"):
        derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)


def test_per_symbol_missing_feature_index_entry_is_fail_closed() -> None:
    """`plans` 有 B 但 `feature_index_by_symbol` 缺 B ⇒ 擋，**不得**丟棄該 symbol。

    🔴 這條是 `M-SU-D1-09` 自證時撈出來的缺口：把該處的 raise 改成 `continue`
    （映不到就丟棄），原本整批測試**一條都不會紅**——等於整個 symbol 的事件
    可以靜默消失。
    """
    plans, idx, keys, man, _ = _interleaved_case()
    partial = {SYM: idx[SYM]}                       # 故意缺 SYM_B
    with pytest.raises(ValueError, match="feature_index_by_symbol"):
        derive_event_split_from_plans(plans, keys, partial, manifest=man, bucket_ms=H1)


def test_fingerprint_tampered_rows_are_caught_at_entry() -> None:
    """建構後竄改序號（改變成員集合）⇒ 入口重驗擋下，訊息含兩個指紋的前 12 字元。"""
    import re

    index, train, test, keys, man, _ = _basic_case()
    loc = np.asarray(train.row_index_local, dtype=int).copy()
    loc[-1] = int(loc[-1]) + 1
    object.__setattr__(train, "row_index_local", loc)
    with pytest.raises(ValueError, match="指紋不符") as ei:
        derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert re.search(r"[0-9a-f]{12}", str(ei.value)), "訊息未帶可比對的指紋前綴"
