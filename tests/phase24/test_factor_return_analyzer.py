import numpy as np
import pandas as pd

from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer
from momentum.Analysis.deep_analysis_types import SkippedResult


def _make_data(n: int = 400):
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="12h")
    feature = pd.Series(rng.normal(size=n), index=idx, name="f1")
    label = pd.Series(feature.values * 0.02 + rng.normal(scale=0.01, size=n), index=idx, name="ret")
    return feature, label


def test_compute_factor_returns_success():
    feature, label = _make_data()
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5})

    result = analyzer.compute_factor_returns(feature, label)

    assert isinstance(result, dict)
    assert "quantile_returns_summary" in result
    assert "risk_metrics" in result
    assert result["num_quantiles_used"] >= 2


def test_insufficient_samples():
    feature, label = _make_data(20)
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_factor_returns(feature, label)
    assert isinstance(result, SkippedResult)
    assert result.error_type == "INSUFFICIENT_DATA"


def test_constant_feature_skip():
    _, label = _make_data(100)
    idx = label.index
    feature = pd.Series(1.0, index=idx)
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_factor_returns(feature, label)
    assert isinstance(result, SkippedResult)


def test_empty_quantile_fallback():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2024-01-01", periods=120, freq="12h")
    feature = pd.Series(np.where(np.arange(120) % 2 == 0, 1, 2), index=idx)
    label = pd.Series(rng.normal(size=120) * 0.01, index=idx)
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5})

    result = analyzer.compute_factor_returns(feature, label)

    assert isinstance(result, dict)
    assert result["num_quantiles_used"] in {2, 3}


def test_compute_batch():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2024-01-01", periods=300, freq="12h")
    features = pd.DataFrame(
        {
            "f1": rng.normal(size=300),
            "f2": rng.normal(size=300),
            "f3": rng.normal(size=300),
        },
        index=idx,
    )
    labels = pd.Series(features["f1"] * 0.01 + rng.normal(scale=0.01, size=300), index=idx)
    analyzer = FactorReturnAnalyzer({})

    result = analyzer.compute_batch(features, labels, top_n=2)

    assert len(result) == 2
    assert set(result.keys()) == {"f1", "f2"}
