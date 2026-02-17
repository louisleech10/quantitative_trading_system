import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer


def _ic_matrix(rows=200, cols=8):
    rng = np.random.default_rng(42)
    return pd.DataFrame(rng.normal(scale=0.05, size=(rows, cols)), columns=[f"f{i}" for i in range(cols)])


def test_compute_centrality_success():
    analyzer = FactorCentralityAnalyzer({"n_components": 4, "min_samples_for_pca": 30})
    matrix = _ic_matrix()

    result = analyzer.compute_centrality(matrix)

    assert isinstance(result, dict)
    assert "pca_summary" in result
    assert len(result["features"]) > 0


def test_compute_centrality_too_few_features():
    analyzer = FactorCentralityAnalyzer({})
    matrix = _ic_matrix(cols=2)

    result = analyzer.compute_centrality(matrix)

    assert isinstance(result, SkippedResult)
    assert result.error_type == "INSUFFICIENT_DATA"


def test_compute_rolling_centrality():
    analyzer = FactorCentralityAnalyzer({"rolling_window": 30})
    matrix = _ic_matrix(rows=80, cols=6)

    rolling = analyzer.compute_rolling_centrality(matrix)

    assert isinstance(rolling, pd.DataFrame)
    assert not rolling.empty


def test_detect_crowding_regime():
    analyzer = FactorCentralityAnalyzer({"crowded_threshold": 0.3})
    index = pd.date_range("2024-01-01", periods=10, freq="12h")
    rolling = pd.DataFrame({"f0": np.linspace(0.1, 0.5, 10)}, index=index)

    result = analyzer.detect_crowding_regime(rolling, "f0")

    assert result["feature"] == "f0"
    assert result["trend"] in {"rising", "falling", "flat"}


def test_all_nan_ic_matrix_skip():
    analyzer = FactorCentralityAnalyzer({})
    matrix = pd.DataFrame({"f1": [np.nan] * 40, "f2": [np.nan] * 40, "f3": [np.nan] * 40})
    result = analyzer.compute_centrality(matrix)
    assert isinstance(result, SkippedResult)


def test_empty_matrix_skip():
    analyzer = FactorCentralityAnalyzer({})
    result = analyzer.compute_centrality(pd.DataFrame())
    assert isinstance(result, SkippedResult)


def test_compute_centrality_fallback_correlation(monkeypatch):
    analyzer = FactorCentralityAnalyzer({"min_samples_for_pca": 10})
    matrix = _ic_matrix(rows=60, cols=5)

    class _DummyPCA:
        def __init__(self, *args, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            raise ValueError("numerical explosion")

    monkeypatch.setattr("momentum.Analysis.factor_centrality_analyzer.PCA", _DummyPCA)
    result = analyzer.compute_centrality(matrix)

    assert isinstance(result, dict)
    assert result["pca_summary"].get("fallback") == "correlation_based"


def test_compute_rolling_centrality_too_short_window():
    analyzer = FactorCentralityAnalyzer({"rolling_window": 60})
    matrix = _ic_matrix(rows=4, cols=6)
    rolling = analyzer.compute_rolling_centrality(matrix)
    assert rolling.empty


def test_detect_crowding_regime_unknown_feature():
    analyzer = FactorCentralityAnalyzer({})
    rolling = pd.DataFrame({"f0": [0.1, 0.2, 0.3]})
    result = analyzer.detect_crowding_regime(rolling, "missing")
    assert result["regime"] == "unknown"


def test_compute_centrality_too_few_samples():
    analyzer = FactorCentralityAnalyzer({"min_samples_for_pca": 50})
    matrix = _ic_matrix(rows=20, cols=5)
    result = analyzer.compute_centrality(matrix)
    assert isinstance(result, SkippedResult)


def test_compute_centrality_all_constant_columns():
    analyzer = FactorCentralityAnalyzer({"min_samples_for_pca": 10})
    matrix = pd.DataFrame({"f1": [1.0] * 30, "f2": [1.0] * 30, "f3": [1.0] * 30})
    result = analyzer.compute_centrality(matrix)
    assert isinstance(result, SkippedResult)
    assert "constant" in result.reason


def test_fallback_corr_empty(monkeypatch):
    analyzer = FactorCentralityAnalyzer({"min_samples_for_pca": 10})
    matrix = _ic_matrix(rows=40, cols=4)

    class _FailPCA:
        def __init__(self, *args, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr("momentum.Analysis.factor_centrality_analyzer.PCA", _FailPCA)
    monkeypatch.setattr(pd.DataFrame, "corr", lambda self, method="spearman": pd.DataFrame())
    result = analyzer.compute_centrality(matrix)
    assert isinstance(result, SkippedResult)
    assert result.error_type == "NUMERICAL_ERROR"


def test_detect_crowding_regime_series_empty_and_falling():
    analyzer = FactorCentralityAnalyzer({"crowded_threshold": 0.5})
    empty_series_df = pd.DataFrame({"f0": [np.nan, np.nan, np.nan]})
    unknown = analyzer.detect_crowding_regime(empty_series_df, "f0")
    assert unknown["regime"] == "unknown"

    falling_df = pd.DataFrame({"f0": [0.8, 0.6, 0.4, 0.2]})
    falling = analyzer.detect_crowding_regime(falling_df, "f0")
    assert falling["trend"] in {"falling", "flat"}


def test_compute_rolling_centrality_empty_input():
    analyzer = FactorCentralityAnalyzer({})
    rolling = analyzer.compute_rolling_centrality(pd.DataFrame())
    assert rolling.empty
