"""Task B1.3 驗證：跨界 purge 手造 exact、禁 positional index、macro/micro 標示、
同 time_cluster 權重和＝1（atol=1e-12）；單 symbol degraded、tier loud、極端同刻簇。"""

from __future__ import annotations

import pandas as pd
import pytest

from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.types import EventManifest, EventSplitConfig

B = 1704067200000
H12 = 43200000


def mk_manifest(rows) -> EventManifest:
    """rows: (event_id, symbol, decision_ms, start_ms, end_ms, tf)"""
    t = pd.DataFrame([
        {
            "event_id": e, "symbol": s, "decision_at_ms": d,
            "observation_interval_start_ms": a, "observation_interval_end_ms": b,
            "label_start_ms": a, "label_end_ms": b,
            "dedupe_cluster_id": "c0", "overlap_set_hash": "h", "uniqueness_weight": 1.0,
            "in_primary": True, "in_sensitivity": True, "timeframe": tf,
        }
        for e, s, d, a, b, tf in rows
    ])
    return EventManifest(table=t, summary={"n_events_raw": len(t), "n_events_effective": len(t)}, policy={})


def five_events(symbol="ETHUSDT"):
    return [(f"{symbol}-e{i}", symbol, B + i * H12, B + i * H12, B + (i + 1) * H12, "12h") for i in range(5)]


def test_boundary_purge_exact_hand_example():
    """驗證①：n=5、test_fraction=0.4 ⇒ 邊界＝第 3 顆；e2 答案窗跨界 ⇒ purge。"""
    plan = split_events(mk_manifest(five_events()), EventSplitConfig(test_fraction=0.4))
    a = plan.assignments.set_index("event_id")["split_label"]
    assert a.loc["ETHUSDT-e0"] == "train" and a.loc["ETHUSDT-e1"] == "train"
    assert a.loc["ETHUSDT-e3"] == "test" and a.loc["ETHUSDT-e4"] == "test"
    assert plan.purged.set_index("event_id").loc["ETHUSDT-e2", "reason"] == "interval_crosses_split_boundary"
    assert plan.summary["n_purged"] == 1


def test_no_positional_index_row_order_invariant():
    """驗證②：manifest 列序打亂 ⇒ 指派逐事件相同（切分依 ms 非列號）。"""
    m = mk_manifest(five_events())
    plan1 = split_events(m, EventSplitConfig(test_fraction=0.4))
    m2 = EventManifest(table=m.table.iloc[[3, 0, 4, 1, 2]].reset_index(drop=True), summary=m.summary, policy=m.policy)
    plan2 = split_events(m2, EventSplitConfig(test_fraction=0.4))
    key = lambda p: p.assignments.sort_values("event_id").reset_index(drop=True)  # noqa: E731
    pd.testing.assert_frame_equal(key(plan1), key(plan2))


def test_macro_micro_both_output_and_labeled():
    plan = split_events(mk_manifest(five_events()), EventSplitConfig(test_fraction=0.4))
    assert plan.summary["stats_modes"] == {"primary": "macro", "sensitivity": "micro"}


def test_time_cluster_weight_sums_to_one():
    """驗證④（M5 看住）：同 time_cluster 權重和＝1（atol=1e-12）。"""
    rows = five_events("ETHUSDT") + five_events("BTCUSDT")  # 兩標的同刻 ⇒ 每桶 2 事件
    plan = split_events(mk_manifest(rows), EventSplitConfig(test_fraction=0.4))
    sums = plan.clusters.groupby("time_cluster_id")["cluster_weight"].sum()
    assert (sums - 1.0).abs().max() <= 1e-12
    assert plan.summary["n_symbols"] == 2
    assert "single_symbol" not in plan.summary["degraded"]


def test_single_symbol_degraded():
    plan = split_events(mk_manifest(five_events()), EventSplitConfig(test_fraction=0.4))
    assert plan.summary["degraded"] == ["single_symbol"]
    assert plan.summary["loso_status"] == "not_evaluated"


def test_tier_insufficient_loud_no_fallback():
    """邊界②：test 段事件數 < tier 下限 ⇒ loud 記名，不回退全樣本（train 指派不變）。"""
    plan = split_events(mk_manifest(five_events()), EventSplitConfig(test_fraction=0.4, tier_min_test_events=3))
    assert plan.summary["insufficient_events_in_test"] == ["ETHUSDT"]
    a = plan.assignments["split_label"]
    assert (a == "train").sum() == 2 and (a == "test").sum() == 2


def test_extreme_all_symbols_same_instant_single_cluster():
    """邊界③：同刻全 symbol 觸發 ⇒ 該桶單一 cluster、權重 1/n。"""
    rows = [(f"s{i}", f"SYM{i}USDT", B, B, B + H12, "12h") for i in range(4)]
    plan = split_events(mk_manifest(rows), EventSplitConfig(test_fraction=0.5, tier_min_test_events=0))
    assert plan.summary["n_time_clusters"] == 1
    assert (plan.clusters["cluster_weight"] == 0.25).all()


def test_mixed_tf_requires_explicit_bucket():
    rows = five_events() + [("x1", "BTCUSDT", B, B, B + 3600000, "1h")]
    with pytest.raises(ValueError, match="bucket_ms"):
        split_events(mk_manifest(rows), EventSplitConfig(test_fraction=0.4))
    plan = split_events(mk_manifest(rows), EventSplitConfig(test_fraction=0.4, bucket_ms=H12, tier_min_test_events=0))
    assert plan.summary["bucket_ms"] == H12


def test_embargo_smaller_than_window_rejected():
    with pytest.raises(ValueError, match="緩衝"):
        split_events(mk_manifest(five_events()), EventSplitConfig(test_fraction=0.4, embargo_ms=1))
