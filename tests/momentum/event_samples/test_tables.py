"""Task B2.1／B2.2 驗證：手造小例 exact、CI 固定 seed 決定性、horizon 超界排除不灌 0、單事件 CI unavailable；
辨別表 OOS only、kind 分層、unclassifiable 不進分母、one-class unavailable、置亂 oracle 沿 B1.4。
事件序列用真實 kline 對齊（B2.1）；scores/labels 合成（B2.2，章程 §F）。"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.tables import binary_discrimination_table, event_forward_return_table
from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig, EventSplitConfig, EventSplitPlan
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def pipeline(bars, idxs, labels, **ev_over):
    events = [make_event(i, t0=BASE + n * H12, label=labels[i], **ev_over) for i, n in enumerate(idxs)]
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    man = build_event_manifest(rec, DedupePolicyConfig(scenario="C"), events=df)
    plan = split_events(man, EventSplitConfig(test_fraction=0.4, tier_min_test_events=0))
    return df, rec, man, plan


# ---------------- B2.1 forward_return ----------------

def test_forward_return_hand_example_exact(bars):
    """手造 exact：單事件 h=1,2 之 signed 報酬＝(close[entry+h]−open[entry])/open[entry]，標籤基準並排。"""
    df, rec, man, plan = pipeline(bars, [300, 600], [1, 0])
    rep = event_forward_return_table(man, rec, bars, plan, {"horizons": [1, 2], "seed": 1, "n_boot": 50})
    b = bars["ETHUSDT"]["12h"]
    for h in (1, 2):
        expected = []
        for n in (300, 600):
            entry = float(b["open"].iloc[n])
            expected.append((float(b["close"].iloc[n + h]) - entry) / entry)
        got = rep["sensitivity_micro"][str(h)]                             # micro＝event 等權（AR-3；GROK-R1-P2-02）
        assert got["n"] == 2
        assert got["mean"] == pytest.approx(np.mean(expected), abs=1e-12)
        assert "uniqueness_weighted" in rep and str(h) in rep["uniqueness_weighted"]
    assert rep["statistic_kind"] == "event_return"
    assert "label_anchor_mean" in rep["sensitivity_micro"]["1"]          # 兩數並排（D1-4）
    assert rep["common"]["degraded"] == ["single_symbol"]
    assert rep["common"]["formal_pooled_inference_allowed"] is False    # AR-3 機械可讀
    assert rep["common"]["n_events_raw"] == 2


def test_forward_return_ci_deterministic_and_horizon_excluded(bars):
    last = 1695
    df, rec, man, plan = pipeline(bars, [1000, 1100, 1200, last - 3], [1, 0, 1, 0])
    cfg = {"horizons": [1, 5], "seed": 7, "n_boot": 100}
    r1 = event_forward_return_table(man, rec, bars, plan, cfg)
    r2 = event_forward_return_table(man, rec, bars, plan, cfg)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    # last-3 事件：h=5 超出資料 ⇒ 該格 n=3（排除）不灌 0
    assert r1["sensitivity_micro"]["1"]["n"] == 4 and r1["sensitivity_micro"]["5"]["n"] == 3
    assert r1["sensitivity_micro"]["1"]["ci"]["status"] == "ok"


def test_forward_return_single_event_ci_unavailable(bars):
    df, rec, man, plan = pipeline(bars, [300, 900], [1, 0])
    rep = event_forward_return_table(man, rec, bars, plan, {"horizons": [1], "seed": 1, "n_boot": 20})
    sub = rep["strata"]["by_direction"]["long"]["1"]
    # 兩事件但 time_cluster 各自獨立 ⇒ ok；改用單事件子集檢 unavailable
    one = rep["strata"]["by_period"]
    assert any(v["1"]["ci"]["status"] == "unavailable" for v in one.values())


def test_forward_return_bad_horizons_rejected(bars):
    df, rec, man, plan = pipeline(bars, [300, 600], [1, 0])
    with pytest.raises(ValueError, match="horizons"):
        event_forward_return_table(man, rec, bars, plan, {"horizons": []})


# ---------------- B2.2 discrimination ----------------

def synth_plan(n=200, seed=3):
    rng = np.random.default_rng(seed)
    ids = [f"e{i}" for i in range(n)]
    y = pd.Series(rng.integers(0, 2, n), index=ids)
    s = pd.Series(y.to_numpy() * 1.0 + rng.normal(0, 0.7, n), index=ids)
    kinds = pd.Series(np.where(y == 0, rng.choice(["a_trigger_no_follow", "b_range", "c_drop", "unclassifiable"], n), None), index=ids)
    plan = EventSplitPlan(
        assignments=pd.DataFrame({"event_id": ids, "symbol": "S", "split_label": ["train"] * (n // 2) + ["test"] * (n - n // 2)}),
        purged=pd.DataFrame(), clusters=pd.DataFrame(),
        summary={"stats_modes": {"primary": "macro", "sensitivity": "micro"}, "degraded": ["single_symbol"], "loso_status": "not_evaluated"},
    )
    return s, y, pd.DataFrame({"counterexample_kind_effective": kinds}), plan


def test_discrimination_oos_only_and_kind_strata():
    s, y, strata, plan = synth_plan()
    rep = binary_discrimination_table(s, y, plan, strata, {"seed": 1, "n_perm": 200})
    assert rep["overall"]["n"] == 100                                   # 只 test 段
    assert rep["overall"]["auc"] > 0.7 and rep["overall"]["auc_in_band"] is False
    assert set(rep["by_counterexample_kind"]) == {"a_trigger_no_follow", "b_range", "c_drop"}
    assert rep["n_unclassifiable"] == int((strata.reindex(s.index[100:])["counterexample_kind_effective"] == "unclassifiable").sum())
    assert rep["receipts"]["oos_only"] is True
    # AR-3 共同欄全套（COMPOSER/GROK R1-P2-01）：無 manifest ⇒ raw/effective n null；degraded ⇒ 禁 formal pooled
    assert rep["common"]["formal_pooled_inference_allowed"] is False
    assert rep["common"]["degraded"] == ["single_symbol"] and rep["common"]["n_events_raw"] is None
    assert set(rep["common"]) >= {"stats_modes", "n_events_raw", "n_events_effective", "degraded", "loso_status", "cluster_adjusted"}


def test_discrimination_shuffled_in_band_and_one_class():
    s, y, strata, plan = synth_plan()
    rng = np.random.default_rng(20260820)
    y_sh = pd.Series(rng.permutation(y.to_numpy()), index=y.index)
    rep = binary_discrimination_table(s, y_sh, plan, strata, {"seed": 1, "n_perm": 200})
    assert rep["overall"]["auc_in_band"] is True
    rep1 = binary_discrimination_table(s, pd.Series(1, index=y.index), plan, strata, {"seed": 1, "n_perm": 50})
    assert rep1["overall"]["capability_status"] == "unavailable"


def test_discrimination_kind_layer_zero_unavailable_not_empty():
    s, y, strata, plan = synth_plan()
    strata2 = strata.copy()
    strata2.loc[strata2["counterexample_kind_effective"] == "c_drop", "counterexample_kind_effective"] = "b_range"
    rep = binary_discrimination_table(s, y, plan, strata2, {"seed": 1, "n_perm": 50})
    assert rep["by_counterexample_kind"]["c_drop"]["capability_status"] == "unavailable"
