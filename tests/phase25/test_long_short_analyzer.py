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


def test_both_sides_negative_ic_concrete_outcome():
    """遞增 linspace（120 根）：PIT 標籤自第 100 根起每根皆為歷史新高 ⇒ 全落最高箱（label 4）。

    手算：long（預設分位 4、5）樣本＝120−100+1＝21、short（分位 1、2）樣本 0；
    returns＝−feature 嚴格遞減 ⇒ long 側 spearman IC＝−1；單側空 ⇒ 不建議。
    """
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5})
    feature = pd.Series(np.linspace(-1, 1, 120))
    returns = pd.Series(-feature.values)
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, dict) and result["long_analysis"]["samples"] == 21 \
        and result["short_analysis"]["samples"] == 0 and np.isclose(result["long_analysis"]["ic"], -1.0) \
        and result["recommendation"] == "不建議", result


def test_asymmetric_quantile_def_counts_follow_configured_sets():
    """非對稱分位設定（long＝{5}、short＝{1,2}）：樣本數須對應所設分位集合（手算 PIT 標籤）。

    序列：前 100 根為 1..100；其後依序 新低(-999)、75.5、新高(1100)、30.5、新低(-1999)、新高(2100)。
    手算各根於其歷史中之五分位 label：t99＝4（當下最大）、新低＝0、75.5＝3（介於 60%／80% 分位）、
    新高＝4、30.5＝1（介於 20%／40% 分位）。⇒ long（僅 label 4）＝t99＋兩個新高＝3；
    short（label 0、1）＝兩個新低＋30.5＝3；75.5（label 3）兩側皆不計。
    returns：label 4 處 +0.03、label 0／1 處 −0.01（做空報酬 +0.01）、其餘 0
    ⇒ long 均值 0.03、short 均值 0.01、比值 3 > 1.5 ⇒ long_dominant。
    """
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5, "long_quantiles": [5], "short_quantiles": [1, 2]})
    tail_vals = [-999.0, 75.5, 1100.0, 30.5, -1999.0, 2100.0]
    tail_side = ["S", "-", "L", "S", "S", "L"]
    feature = pd.Series(list(np.arange(1, 101, dtype=float)) + tail_vals)
    ret = np.zeros(len(feature))
    ret[99] = 0.03
    for i, side in enumerate(tail_side):
        ret[100 + i] = 0.03 if side == "L" else (-0.01 if side == "S" else 0.0)
    result = analyzer.analyze(feature, pd.Series(ret), num_quantiles=5)
    assert isinstance(result, dict) and result["long_analysis"]["samples"] == 3 \
        and result["short_analysis"]["samples"] == 3 and np.isclose(result["long_analysis"]["mean_return"], 0.03) \
        and np.isclose(result["short_analysis"]["mean_return"], 0.01) \
        and result["asymmetry"]["type"] == "long_dominant", result
