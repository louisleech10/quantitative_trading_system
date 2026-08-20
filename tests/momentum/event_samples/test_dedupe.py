"""Task B1.2 驗證：簇首代表＝interval 最早（scenario=C primary）、權重/簇計數手算 exact、
單事件/極端簇/缺 interval 邊界。合成的是事件 interval 序列非價格（章程 §F 合法）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.types import AlignmentReceipts, DedupePolicyConfig

B = 1704067200000


def mk_receipts(rows):
    """rows: list[(event_id, start_ms, end_ms)] → 最小事件級收據。"""
    ev = pd.DataFrame([
        {
            "event_id": e, "t0_ms": s, "decision_offset_bars": 0, "decision_at_ms": s,
            "entry_at_ms": s, "entry_price_source_bar_open_ms": s, "entry_price_source_field": "open",
            "label_start_ms": s, "label_end_ms": t, "entry_after_label_start": False,
        }
        for e, s, t in rows
    ])
    return AlignmentReceipts(event_level=ev, per_tf=pd.DataFrame())


def test_scenario_c_policy_primary_cluster_first_representative():
    """ASSERT …WHEN scenario=C policy=primary THEN rc=0：簇首代表＝interval 最早。"""
    m = build_event_manifest(
        mk_receipts([("e1", B, B + 100), ("e2", B + 50, B + 150), ("e3", B + 500000, B + 500100)]),
        DedupePolicyConfig(scenario="C"),
    )
    t = m.table.set_index("event_id")
    assert m.policy["primary"] == "cluster_first"
    assert t.loc["e1", "dedupe_cluster_id"] == t.loc["e2", "dedupe_cluster_id"]
    assert t.loc["e3", "dedupe_cluster_id"] != t.loc["e1", "dedupe_cluster_id"]
    assert bool(t.loc["e1", "in_primary"]) is True   # interval 最早＝代表
    assert bool(t.loc["e2", "in_primary"]) is False
    assert bool(t.loc["e3", "in_primary"]) is True
    assert m.summary["n_clusters"] == 2
    assert m.summary["n_events_effective"] == 2


def test_uniqueness_weights_exact_hand_example():
    m = build_event_manifest(
        mk_receipts([("e1", B, B + 100), ("e2", B + 50, B + 150), ("e3", B + 500000, B + 500100)]),
        DedupePolicyConfig(scenario="A"),
    )
    t = m.table.set_index("event_id")
    assert t.loc["e1", "uniqueness_weight"] == 0.5
    assert t.loc["e2", "uniqueness_weight"] == 0.5
    assert t.loc["e3", "uniqueness_weight"] == 1.0
    assert m.policy["primary"] == "all_with_uniqueness"
    assert m.policy["requires_cluster_robust"] is True   # 無修正 raw-all 禁出
    assert m.summary["n_events_effective"] == pytest.approx(2.0, abs=1e-12)
    assert m.summary["overlap_fraction"] == pytest.approx(2 / 3, abs=1e-12)


def test_single_event_weight_one_own_cluster():
    m = build_event_manifest(mk_receipts([("e1", B, B + 100)]), DedupePolicyConfig(scenario="C"))
    t = m.table.iloc[0]
    assert t["uniqueness_weight"] == 1.0
    assert m.summary["n_clusters"] == 1
    assert m.summary["sensitivity_flip"] is False


def test_extreme_all_same_interval_effective_one():
    m = build_event_manifest(
        mk_receipts([(f"e{i}", B, B + 100) for i in range(5)]), DedupePolicyConfig(scenario="C")
    )
    assert m.summary["n_clusters"] == 1
    assert m.summary["n_events_effective"] == 1
    assert m.summary["sensitivity_flip"] is True


def test_missing_interval_fail_closed():
    r = mk_receipts([("e1", B, B + 100)])
    r.event_level.loc[0, "label_end_ms"] = np.nan
    with pytest.raises(ValueError, match="fail-closed"):
        build_event_manifest(r, DedupePolicyConfig(scenario="C"))


def test_transitive_overlap_union_find_composer_counterexample():
    """COMPOSER-R1-P1-01：A[0,100]⊃C[30,35]、B[40,50]⊂A 但不與 C 相交 ⇒ 三者須同簇（鏈式掃描會拆開 B）。"""
    m = build_event_manifest(
        mk_receipts([("A", B, B + 100), ("C", B + 30, B + 35), ("B", B + 40, B + 50)]),
        DedupePolicyConfig(scenario="A", cluster_gap_ms=0),
    )
    t = m.table.set_index("event_id")
    assert t.loc["A", "dedupe_cluster_id"] == t.loc["B", "dedupe_cluster_id"] == t.loc["C", "dedupe_cluster_id"]
    assert m.summary["n_clusters"] == 1
    # 權重與簇一致：A 與兩者皆交 ⇒ 1/3；C、B 各只與 A 交 ⇒ 1/2
    assert t.loc["A", "uniqueness_weight"] == pytest.approx(1 / 3, abs=1e-12)
    assert t.loc["C", "uniqueness_weight"] == 0.5 and t.loc["B", "uniqueness_weight"] == 0.5


def test_transitive_overlap_union_find_codex_counterexample():
    """CODEX-R1-P1-02：a[0,100]、b[50,60]、c[90,120]（gap=0）⇒ 區間聯集連通，三者同簇且 C 簇首＝a。"""
    m = build_event_manifest(
        mk_receipts([("a", B, B + 100), ("b", B + 50, B + 60), ("c", B + 90, B + 120)]),
        DedupePolicyConfig(scenario="C", cluster_gap_ms=0),
    )
    t = m.table.set_index("event_id")
    assert t["dedupe_cluster_id"].nunique() == 1
    assert bool(t.loc["a", "in_primary"]) is True and not bool(t.loc["b", "in_primary"]) and not bool(t.loc["c", "in_primary"])
    assert m.summary["n_events_effective"] == 1


def test_events_context_join():
    ev = pd.DataFrame({"event_id": ["e1"], "symbol": ["ETHUSDT"], "timeframe": ["12h"], "label": [1],
                       "scenario": ["C"], "direction": ["long"]})
    m = build_event_manifest(mk_receipts([("e1", B, B + 100)]), DedupePolicyConfig(scenario="C"), events=ev)
    assert m.table.loc[0, "symbol"] == "ETHUSDT"
    assert m.table.loc[0, "timeframe"] == "12h"
