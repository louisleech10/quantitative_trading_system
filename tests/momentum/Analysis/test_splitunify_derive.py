"""SPLITUNIFY B2b：投影純函式 `derive_event_split_from_plans` 之測試。

規格：`docs/SPLITUNIFY_SPEC.md`（v5）C-2／C-3／C-4／C-5；mutation `M-SU-1`..`M-SU-7`、
`M-SU-12`、`M-SU-13`。

🔴 本檔之核心是 **`-k answer_window`**：它釘住兩段式判定的**第一段**——
答案窗跨進測試段的 train 事件必進 `purged`。少了那一段就是把 `event_split.py:114`
那道事件側唯一擋標籤窗跨界洩漏的閘刪掉（`SPLITUNIFY` v3 犯過，`CODEX-R3-P1-02` 抓出）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

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
    train = SplitPlan(
        split_label="train",
        row_index=b["train_row_index"],
        time_bounds=(int(index[0]), int(index[b["train_row_index"][-1]])),
        **kw,
    )
    test = SplitPlan(
        split_label="test",
        row_index=b["test_row_index"],
        time_bounds=(int(index[b["test_row_index"][0]]), int(index[-1])),
        **kw,
    )
    return train, test, b


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
    overlapping_test = SplitPlan(
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
    index, train, test, _, _, _ = _basic_case()
    keys = _event_keys(
        [("e1", index[0], int(index[0]) + H1), ("e2", index[1], int(index[1]) + H1, "BTCUSDT")]
    )
    with pytest.raises(ValueError, match="multi_symbol_projection_unsupported"):
        derive_event_split_from_plans(
            train, test, keys, index, manifest=_manifest(keys), bucket_ms=H1
        )


def test_single_symbol_batch_unaffected() -> None:
    index, train, test, keys, man, _ = _basic_case()
    derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)


def test_non_positional_index_kind_is_fail_closed() -> None:
    index, train, test, keys, man, _ = _basic_case()
    bad = SplitPlan(
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
    empty_test = SplitPlan(
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
def test_clusters_byte_identical_to_legacy_split_events() -> None:
    """`build_time_clusters` 是自 `split_events` **原樣抽出**——同一 manifest 須逐值相同。

    🔴 fixture 必須讓**至少兩個事件落在同一個桶**（`M-SU-4`／`M-SU-7` 的教訓）：
    每個事件各自成簇時 `cluster_weight` 恆為 `1/1 == 1.0`，把權重公式改成寫死 `1.0`
    也測不出來。這裡刻意讓 `c2`／`c3` 共用同一桶 ⇒ 權重應為 **0.5**。
    """
    index, _, _, _, _, _ = _basic_case()
    t0 = int(index[0])
    keys = _event_keys(
        [
            ("c1", t0, t0 + H1),
            ("c2", t0 + H1, t0 + 2 * H1),
            ("c3", t0 + H1, t0 + 2 * H1),  # 與 c2 同桶 ⇒ 權重 0.5
        ]
    )
    man = _manifest(keys)
    mine = build_time_clusters(man, H1)
    legacy = split_events(
        man, EventSplitConfig(test_fraction=0.4, bucket_ms=H1, tier_min_test_events=0)
    )
    assert set(mine["cluster_weight"]) == {1.0, 0.5}, (
        "fixture 必須含共桶事件，否則權重恆 1.0、公式被改寫死也測不出來"
    )
    pd.testing.assert_frame_equal(mine, legacy.clusters)


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
    index, train, test, _, _, _ = _basic_case()
    keys = _event_keys([])
    keys = pd.DataFrame(columns=list(_event_keys([("x", 0, 0)]).columns))
    man = _manifest(_event_keys([("x", int(index[0]), int(index[0]))]))
    plan = derive_event_split_from_plans(train, test, keys, index, manifest=man, bucket_ms=H1)
    assert plan.assignments.empty and plan.purged.empty


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
