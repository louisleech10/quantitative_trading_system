"""Task B2.3 驗證（`-k "gap3 and conditional_ic"`）：餵入層單元＋orchestrator 接線整合
（真實 la0 fixture；label 覆寫只在傳 event_label_values 時生效；A′ fallback 透傳；
缺 label_value ⇒ unavailable:missing_label_value、不重算；t₀−k 案例 label 錨不隨 decision 移動）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.ic_feed import build_event_ic_inputs
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig, EventSplitConfig
from tests.momentum.event_samples.helpers import load_bars, make_event
from tests.momentum.helpers.ichc_run import feature_index, run_analyze

BASE = 1704067200000
H12 = 43200000


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def feed(bars, idxs, labels, label_values, **over):
    events = []
    for i, n in enumerate(idxs):
        kw = dict(t0=BASE + n * H12, label=labels[i])
        if label_values[i] is not None:
            kw["label_value"] = label_values[i]
        kw.update(over)
        events.append(make_event(i, **kw))
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    man = build_event_manifest(rec, DedupePolicyConfig(scenario="C"), events=df)
    plan = split_events(man, EventSplitConfig(test_fraction=0.4, tier_min_test_events=0))
    return df, rec, build_event_ic_inputs(man, plan, df, rec, timeframe="12h")


def test_conditional_ic_feed_missing_label_value_unavailable(bars):
    _, _, out = feed(bars, [300, 600], [1, 0], [0.02, None])
    assert out["capability_status"] == "unavailable" and out["reason"] == "missing_label_value"
    assert out["event_timestamps"] == []


def test_conditional_ic_feed_timestamps_are_cutoff_bars_and_anchor_fixed(bars):
    """邊界③：k=1 事件之 feature 列＝決策前最後已收盤 bar（t₀−2 根 open），label 錨／值不隨 decision 移動。"""
    df, rec, out = feed(bars, [300, 600], [1, 0], [0.02, -0.01], decision_offset_bars=1)
    assert out["capability_status"] == "ok"
    r = rec.event_level.set_index("event_id")
    # decision_at = t0 − 1 bar open；cutoff = max{close ≤ decision_at} = t0 − 2 bar（close == decision_at）
    assert out["event_timestamps"] == sorted([BASE + 298 * H12, BASE + 598 * H12])
    assert out["event_label_values"][BASE + 298 * H12] == 0.02
    assert int(r.loc["ev0", "label_start_ms"]) == BASE + 301 * H12   # 錨仍＝t₀ close（D1-5）
    assert out["label_price_mismatch"] is False


def test_conditional_ic_feed_mismatch_flag_and_duplicate_loud(bars):
    ld = {"rule_id": "r", "canonical_digest": "c" * 64, "window": {"horizon_bars": 2}, "label_return_mode": "open_to_close"}
    _, _, out = feed(bars, [300, 600], [1, 0], [0.1, 0.2], label_definition=ld)
    assert out["label_price_mismatch"] is True
    with pytest.raises(ValueError, match="同一 feature 列"):
        # 兩事件 k 不同但 cutoff 同列（ev0 k=0 @300 → cutoff 299；ev1 @301 k=2 → decision 299 open → cutoff 298？）
        # 構造確定衝突：ev0 t0=300,k=0 ⇒ cutoff=299；ev1 t0=301,k=1 ⇒ decision=300 open ⇒ cutoff=299
        events = [make_event(0, t0=BASE + 300 * H12, label=1, label_value=0.1),
                  make_event(1, t0=BASE + 301 * H12, label=0, label_value=0.2, decision_offset_bars=1)]
        df = validate_event_import(events)
        rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
        man = build_event_manifest(rec, DedupePolicyConfig(scenario="A"), events=df)
        plan = split_events(man, EventSplitConfig(test_fraction=0.5, tier_min_test_events=0))
        build_event_ic_inputs(man, plan, df, rec, timeframe="12h")


# ---------------- orchestrator 整合（真實 la0 fixture） ----------------

def _labels_for(idx: pd.DatetimeIndex, seed: int = 20260820) -> dict:
    rng = np.random.default_rng(seed)
    return {int(t.value // 10**6): float(v) for t, v in zip(idx, rng.normal(0, 0.02, len(idx)))}


def _find_key(d, key):
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def test_conditional_ic_orchestrator_label_override_wiring():
    idx = feature_index(80)
    lv = _labels_for(idx)
    report = run_analyze({"event_filter": {"enabled": True, "min_events": 30}},
                         event_timestamps=list(lv.keys()), event_label_values=lv)
    assert _find_key(report.get("metadata"), "label_source") == "event_label_value"
    assert _find_key(report.get("metadata"), "statistic_kind") == "conditional_ic"


def test_conditional_ic_orchestrator_missing_label_loud():
    from momentum.Analysis.ic_filter_orchestrator import AlignmentViolationError
    idx = feature_index(80)
    lv = _labels_for(idx)
    lv_missing = dict(list(lv.items())[:-1])  # 少一個 timestamp 的 label
    with pytest.raises(AlignmentViolationError, match="event_label_values missing"):
        run_analyze({"event_filter": {"enabled": True, "min_events": 30}},
                    event_timestamps=list(lv.keys()), event_label_values=lv_missing)


def test_conditional_ic_orchestrator_aprime_fallback_passthrough():
    """A′：事件不足 ⇒ fallback；event_timestamps＋label 透傳不得炸、報告帶 fallback 標示。"""
    idx = feature_index(3)
    lv = _labels_for(idx)
    report = run_analyze({"event_filter": {"enabled": True, "min_events": 30}},
                         event_timestamps=list(lv.keys()), event_label_values=lv)
    assert _find_key(report.get("metadata"), "fallback") is True
