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
