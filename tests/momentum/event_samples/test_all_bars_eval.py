"""Task B2.5 驗證：真實 kline 小段手算分母 exact；ASSERT mutation=ineligible_in_denominator ⇒ 紅（M4 seam）；
缺基率欄 ⇒ unavailable:missing_prevalence_disclosure（M7）；末端 n_tail_excluded 記帳；多 label_id 不覆蓋。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples import all_bars_eval as ab
from momentum.Analysis.event_samples.all_bars_eval import evaluate_all_bars
from tests.momentum.event_samples.helpers import load_bars


@pytest.fixture(scope="module")
def seg():
    b = load_bars("ETHUSDT", ("12h",))["ETHUSDT"]["12h"].iloc[1000:1100].reset_index(drop=True)
    return {"ETHUSDT": b}


def cfg(**over):
    base = {"horizon_bars": 2, "label_threshold": 0.01, "direction": "long", "decision_offset_bars": 0,
            "score_threshold": 0.5, "top_q": 0.1, "prevalence_learn": 0.5, "sample_design": "case_control",
            "seed": 1, "n_boot": 20, "entry_price_semantic": "trigger_open", "timeframe": "12h"}
    base.update(over)
    return base


def scores_for(seg, seed=3):
    rng = np.random.default_rng(seed)
    ot = seg["ETHUSDT"]["open_time_ms"].to_numpy()
    return pd.Series(rng.uniform(0, 1, len(ot)), index=pd.MultiIndex.from_product([["ETHUSDT"], ot]))


def test_denominator_hand_exact_real_kline(seg):
    """100 根、h=2、k=0 ⇒ eligible=98、tail=2；prevalence_full 逐根手算 exact。"""
    rep = evaluate_all_bars(scores_for(seg), seg, cfg())
    c = rep["counts"]
    assert (c["n_total"], c["n_eligible"], c["n_tail_excluded"], c["n_labeled"], c["n_missing"]) == (100, 98, 2, 98, 0)
    close = seg["ETHUSDT"]["close"].to_numpy(dtype=float)
    y = [(close[i + 2] / close[i] - 1.0) >= 0.01 for i in range(98)]
    assert rep["overall"]["prevalence_full"] == pytest.approx(float(np.mean(y)), abs=1e-12)
    assert rep["overall"]["prevalence_learn"] == 0.5 and rep["sample_design"] == "case_control"
    assert rep["overall"]["capability_status"] == "ok"


def test_decision_offset_shrinks_eligible(seg):
    rep = evaluate_all_bars(scores_for(seg), seg, cfg(decision_offset_bars=1))
    c = rep["counts"]
    assert (c["n_eligible"], c["n_unknown"], c["n_tail_excluded"]) == (97, 1, 2)
    assert rep["ineligible_reasons"]["warmup_insufficient"] == 1


def test_missing_scores_counted_not_dropped(seg):
    s = scores_for(seg)
    s.iloc[10:15] = np.nan
    rep = evaluate_all_bars(s, seg, cfg())
    assert rep["counts"]["n_missing"] == 5 and rep["counts"]["n_labeled"] == 93


def test_assert_mutation_ineligible_in_denominator_red(seg, monkeypatch):
    """ASSERT …WHEN mutation=ineligible_in_denominator THEN rc!=0（M4）：把 label_window_incomplete 計入 eligible ⇒ 分母手算斷言紅。"""
    orig = ab._is_eligible
    monkeypatch.setattr(ab, "_is_eligible", lambda i, n, h, k, o, c, *a: None if orig(i, n, h, k, o, c, *a) == "label_window_incomplete" and i + 1 < n else orig(i, n, h, k, o, c, *a))
    with pytest.raises((IndexError, AssertionError)):
        rep = evaluate_all_bars(scores_for(seg), seg, cfg())
        assert rep["counts"]["n_eligible"] == 98  # 分母手算 exact 斷言（mutation 態必不等 ⇒ 紅）


def test_missing_prevalence_disclosure_unavailable(seg):
    """M7：缺基率欄 ⇒ unavailable:missing_prevalence_disclosure。"""
    rep = evaluate_all_bars(scores_for(seg), seg, cfg(prevalence_learn=None))
    assert rep["capability_status"] == "unavailable" and rep["reason"] == "missing_prevalence_disclosure"
    rep2 = evaluate_all_bars(scores_for(seg), seg, cfg(sample_design="full"))
    assert rep2["reason"] == "missing_prevalence_disclosure"


def test_multiple_label_ids_not_overwritten(seg):
    a = evaluate_all_bars(scores_for(seg), seg, cfg(label_id="rule_A", label_threshold=0.01))
    b = evaluate_all_bars(scores_for(seg), seg, cfg(label_id="rule_B", label_threshold=0.05))
    assert a["label_id"] == "rule_A" and b["label_id"] == "rule_B"
    assert a["overall"]["prevalence_full"] >= b["overall"]["prevalence_full"]


def test_common_constraint_block_present(seg):
    """AR-3（三家 R1 同抓）：無 split plan ⇒ formal_pooled_inference_allowed=False＋reason；帶 plan ⇒ 同 tables 共同欄。"""
    from momentum.Analysis.event_samples.types import EventSplitPlan
    rep = evaluate_all_bars(scores_for(seg), seg, cfg())
    assert rep["common"]["formal_pooled_inference_allowed"] is False and rep["common"]["reason"] == "no_event_split_plan"
    plan = EventSplitPlan(assignments=pd.DataFrame(), purged=pd.DataFrame(), clusters=pd.DataFrame(),
                          summary={"degraded": ["single_symbol"], "loso_status": "not_evaluated", "n_symbols": 1,
                                   "stats_modes": {"primary": "macro", "sensitivity": "micro"}})
    rep2 = evaluate_all_bars(scores_for(seg), seg, cfg(), event_split_plan=plan)
    assert rep2["common"]["degraded"] == ["single_symbol"] and rep2["common"]["formal_pooled_inference_allowed"] is False
    assert rep2["common"]["cluster_adjusted"] is True


def test_grid_gap_counted_as_missing_bar(seg):
    """CODEX-R1-P1-02：決策→答案窗缺根 ⇒ missing_bar（不納分母）。刪掉第 50 根。"""
    b = seg["ETHUSDT"].drop(index=50).reset_index(drop=True)
    s2 = {"ETHUSDT": b}
    rep = evaluate_all_bars(scores_for(s2), s2, cfg())
    assert rep["ineligible_reasons"].get("missing_bar") == 2            # 窗跨缺口的兩根（i=48,49 之 h=2 窗）
    assert rep["counts"]["n_eligible"] == 99 - 2 - 2


def test_entry_semantic_next_open_hold_return_exact(seg):
    """D1-6 進場語意（CODEX-R1-P1-02）：next_open ⇒ entry=open[i+1]，持有報酬手算 exact。"""
    b = seg["ETHUSDT"]
    rule = lambda df: pd.Series(1.0, index=df["open_time_ms"])  # noqa: E731  # 全部發訊號
    rep = evaluate_all_bars(rule, seg, cfg(entry_price_semantic="next_open", n_boot=2))
    o, c = b["open"].to_numpy(dtype=float), b["close"].to_numpy(dtype=float)
    expected = np.mean([(c[i + 2] - o[i + 1]) / o[i + 1] for i in range(98)])
    assert rep["overall"]["signed_hold_return_signaled_mean"] == pytest.approx(expected, abs=1e-12)
    assert rep["manifest"]["entry_price_semantic"] == "next_open"


def test_required_entry_semantic_timeframe_and_duplicate_bar_fail_closed(seg):
    """CODEX-R2-P1-02：entry 語意／TF 必填無預設；duplicate bar 拒。"""
    c = cfg(); del c["entry_price_semantic"]
    with pytest.raises(ValueError, match="entry_price_semantic"):
        evaluate_all_bars(scores_for(seg), seg, c)
    c2 = cfg(); del c2["timeframe"]
    with pytest.raises(ValueError, match="timeframe"):
        evaluate_all_bars(scores_for(seg), seg, c2)
    dup = {"ETHUSDT": pd.concat([seg["ETHUSDT"], seg["ETHUSDT"].iloc[[50]]]).sort_values("open_time_ms").reset_index(drop=True)}
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_all_bars(scores_for(dup), dup, cfg())


def test_common_has_actual_macro_micro_cluster_ci(seg):
    """CODEX-R2-P1-01：共同欄含實際 macro／micro AUC 與 cluster-CI；cluster-aware 反例＝單一桶 ⇒ CI unavailable。"""
    rep = evaluate_all_bars(scores_for(seg), seg, cfg(n_boot=60))
    c = rep["common"]
    assert c["micro_auc"] == pytest.approx(rep["overall"]["auc"], abs=1e-12)
    assert c["macro_auc"] == pytest.approx(rep["overall"]["auc"], abs=1e-12)   # 單 symbol ⇒ macro==micro
    assert c["auc_cluster_ci"]["status"] == "ok" and c["auc_cluster_ci"]["ci_low"] <= c["micro_auc"] <= c["auc_cluster_ci"]["ci_high"]
    assert c["n_time_clusters"] == 98
    rep1 = evaluate_all_bars(scores_for(seg), seg, cfg(n_boot=60, bucket_ms=10**15))  # 全部落同一桶
    assert rep1["common"]["n_time_clusters"] == 1 and rep1["common"]["auc_cluster_ci"]["status"] == "unavailable"


def test_rule_callable_and_kind_strata(seg):
    from momentum.Analysis.event_samples.import_contract import load_event_import_contract
    cc = load_event_import_contract()["counterexample_classifier_config"]
    rule = lambda df: (df["close"] > df["open"]).astype(float)  # noqa: E731  # 簡單規則（決策列當根收漲）
    rep = evaluate_all_bars(rule, seg, cfg(classifier_config=cc))
    assert rep["overall"]["n"] == 98
    assert set(rep["strata"]["by_counterexample_kind"]) == {"a_trigger_no_follow", "b_range", "c_drop"}
    assert "n_unclassifiable" in rep["strata"]
