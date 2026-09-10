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
    other_universe = SplitPlan(
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
    """
    index, train, test, keys, man, _ = _basic_case()
    shifted = pd.Index([int(v) + 50 * H1 for v in index], dtype="int64")
    with pytest.raises(ValueError, match="不同源"):
        derive_event_split_from_plans(train, test, keys, shifted, manifest=man, bucket_ms=H1)


def test_same_source_plans_from_shorter_grid_is_fail_closed() -> None:
    """🔴 B3 review R1（codex／composer 反例）：plan 建在**較短網格**、傳入長 `feature_index`。

    row_index 落在長 index 的長度內 ⇒ 既有的長度閘放行，但同一個 row number 指到不同時刻，
    投影**靜默成功**（composer 實跑 `RESULT: succeeded`；codex 實跑
    `RETURNED {'assignments': 2, 'purged': 2}`）。
    """
    index, _, _, keys, man, _ = _basic_case()
    short = pd.Index([int(index[0]) + i * H1 * 2 for i in range(len(index))], dtype="int64")
    short_train, short_test, _ = _plans(short)          # 同 symbol、同 hash 字面，網格不同
    with pytest.raises(ValueError, match="不同源"):
        derive_event_split_from_plans(short_train, short_test, keys, index, manifest=man, bucket_ms=H1)


def test_same_source_accepts_datetime_time_bounds() -> None:
    """🔴 IC orchestrator 產出的 `time_bounds` 是 `pd.Timestamp`（不是 int ms）。

    同源對證必須接受它——否則 B4 把 IC 的 plan 接上投影時會被自己的守衛擋死。
    單位分派是**型別驅動**：datetime-like 轉毫秒；整數必須本來就是毫秒（餵秒會被擋）。
    """
    index, train, test, keys, man, _ = _basic_case()
    ts_train = SplitPlan(
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
    seconds = SplitPlan(
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
    anon = SplitPlan(
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
    anon_test = SplitPlan(
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
    bad = SplitPlan(
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
    bad = SplitPlan(
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
    bad = SplitPlan(
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
    rev = SplitPlan(
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
