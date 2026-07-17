import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.long_short_analyzer import LongShortAnalyzer


def test_insufficient_ls_samples():
    """n<30 → SkippedResult(INSUFFICIENT_DATA)（模組進入門檻不變）。"""
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5})
    feature = pd.Series(np.random.randn(20))
    returns = pd.Series(np.random.randn(20) * 0.01)
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, SkippedResult)
    assert result.error_type == "INSUFFICIENT_DATA"


def test_quantile_exceeds_samples():
    """q=10,n=60 < bin min_samples=100 → bins 全 NaN → SkippedResult(cannot form quantiles)。"""
    analyzer = LongShortAnalyzer(config={"num_quantiles": 10})
    np.random.seed(42)
    feature = pd.Series(np.random.randn(60))
    returns = pd.Series(np.random.randn(60) * 0.01)
    result = analyzer.analyze(feature, returns, num_quantiles=10)
    assert isinstance(result, SkippedResult)
    assert "cannot form quantiles" in result.reason


def test_both_sides_negative_ic():
    """n≥200 過 bin min_samples；recommendation 落 enum。"""
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5})
    np.random.seed(10)
    n = 220
    feature = pd.Series(np.linspace(-1, 1, n))
    returns = pd.Series(-feature.values + 0.01 * np.random.randn(n))
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, dict)
    assert result["num_quantiles_used"] == 5
    assert result["recommendation"] in ["不建議", "只做空", "只做多", "雙向交易"]


def test_empty_side():
    """PIT 下單側空 → 該側 metrics NaN + recommendation==不建議；能算側照算。"""
    analyzer = LongShortAnalyzer(
        config={"num_quantiles": 5, "long_quantiles": [4, 5], "short_quantiles": [1, 2]}
    )
    np.random.seed(7)
    n = 220
    feature = pd.Series(np.linspace(-1, 1, n))
    returns = pd.Series(np.random.randn(n) * 0.01)
    # 高 feature 區 returns 全 NaN → long 側（高分位）空、short 仍有樣本
    high = feature >= feature.quantile(0.6)
    returns = returns.copy()
    returns.loc[high] = np.nan
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, dict)
    long_a = result["long_analysis"]
    short_a = result["short_analysis"]
    # 至少一側空（long 因 returns NaN 被排空）
    assert long_a["samples"] == 0 or short_a["samples"] == 0
    empty = long_a if long_a["samples"] == 0 else short_a
    nonempty = short_a if long_a["samples"] == 0 else long_a
    assert empty["samples"] == 0
    assert np.isnan(empty["ic"]) or empty["ic"] is None
    assert np.isnan(empty["mean_return"]) or empty["mean_return"] is None
    # 能算的側照算（非雙側皆 skip）
    assert nonempty["samples"] > 0
    assert result["recommendation"] == "不建議"


def test_asymmetric_quantile_def():
    """固定 q 語意：num_quantiles_used==5（禁依賴全域降 q）。"""
    analyzer = LongShortAnalyzer(
        config={"num_quantiles": 5, "long_quantiles": [5], "short_quantiles": [1, 2]}
    )
    np.random.seed(99)
    n = 220
    feature = pd.Series(np.random.randn(n))
    returns = pd.Series(np.random.randn(n) * 0.01)
    result = analyzer.analyze(feature, returns, num_quantiles=5)
    assert isinstance(result, dict)
    assert result["num_quantiles_used"] == 5
    assert result["asymmetry"]["type"] in ["long_dominant", "short_dominant", "symmetric"]
    assert result["recommendation"] in ["不建議", "只做空", "只做多", "雙向交易"]
