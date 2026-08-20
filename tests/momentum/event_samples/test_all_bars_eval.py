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
            "seed": 1, "n_boot": 20}
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
    monkeypatch.setattr(ab, "_is_eligible", lambda i, n, h, k, o, c: None if orig(i, n, h, k, o, c) == "label_window_incomplete" and i + 1 < n else orig(i, n, h, k, o, c))
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


def test_rule_callable_and_kind_strata(seg):
    from momentum.Analysis.event_samples.import_contract import load_event_import_contract
    cc = load_event_import_contract()["counterexample_classifier_config"]
    rule = lambda df: (df["close"] > df["open"]).astype(float)  # noqa: E731  # 簡單規則（決策列當根收漲）
    rep = evaluate_all_bars(rule, seg, cfg(classifier_config=cc))
    assert rep["overall"]["n"] == 98
    assert set(rep["strata"]["by_counterexample_kind"]) == {"a_trigger_no_follow", "b_range", "c_drop"}
    assert "n_unclassifiable" in rep["strata"]
