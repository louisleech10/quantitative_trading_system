import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.long_short_analyzer import LongShortAnalyzer


def test_insufficient_ls_samples():
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5})
    feature = pd.Series(np.random.randn(20))
    returns = pd.Series(np.random.randn(20) * 0.01)
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, SkippedResult)


def test_quantile_exceeds_samples():
    analyzer = LongShortAnalyzer(config={"num_quantiles": 10})
    np.random.seed(42)
    feature = pd.Series(np.random.randn(60))
    returns = pd.Series(np.random.randn(60) * 0.01)
    result = analyzer.analyze(feature, returns, num_quantiles=10)
    assert isinstance(result, dict)
    assert result["num_quantiles_used"] >= 2


def test_both_sides_negative_ic():
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5})
    np.random.seed(10)
    feature = pd.Series(np.linspace(-1, 1, 120))
    returns = pd.Series(-feature.values + 0.01 * np.random.randn(120))
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, dict)
    assert result["recommendation"] in ["不建議", "只做空", "只做多", "雙向交易"]


def test_empty_side():
    analyzer = LongShortAnalyzer(config={"num_quantiles": 2, "long_quantiles": [2], "short_quantiles": [1]})
    feature = pd.Series(np.concatenate([np.zeros(40), np.ones(40)]))
    returns = pd.Series(np.random.randn(80) * 0.01)
    result = analyzer.analyze(feature, returns, num_quantiles=2)
    assert isinstance(result, dict) or isinstance(result, SkippedResult)


def test_asymmetric_quantile_def():
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5, "long_quantiles": [5], "short_quantiles": [1, 2]})
    np.random.seed(99)
    feature = pd.Series(np.random.randn(120))
    returns = pd.Series(np.random.randn(120) * 0.01)
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, dict)
    assert result["asymmetry"]["type"] in ["long_dominant", "short_dominant", "symmetric"]


def test_compute_side_metrics_empty_branch():
    metrics = LongShortAnalyzer._compute_side_metrics(pd.Series([], dtype=float), pd.Series([], dtype=float), "long")
    assert metrics["samples"] == 0
    assert np.isnan(metrics["ic"])


def test_recommendation_all_branches():
    assert LongShortAnalyzer._recommendation(0.1, 0.1) == "雙向交易"
    assert LongShortAnalyzer._recommendation(0.1, -0.1) == "只做多"
    assert LongShortAnalyzer._recommendation(-0.1, 0.1) == "只做空"
    assert LongShortAnalyzer._recommendation(-0.1, -0.1) == "不建議"


def test_classify_asymmetry_total_zero_and_short_dominant():
    zero = LongShortAnalyzer._classify_asymmetry(np.nan, np.nan)
    assert zero["type"] == "symmetric"

    short_dom = LongShortAnalyzer._classify_asymmetry(0.01, 0.2)
    assert short_dom["type"] == "short_dominant"


def test_assign_quantiles_none_for_constant_feature():
    bins, used = LongShortAnalyzer._assign_quantiles_with_fallback(pd.Series([1.0] * 60), requested=5)
    assert bins is None
    assert used == 0
