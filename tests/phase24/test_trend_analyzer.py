import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.trend_analyzer import TrendAnalyzer


def test_analyze_trend_down():
    idx = pd.date_range("2024-01-01", periods=80, freq="12h")
    series = pd.Series(np.linspace(1.0, 0.2, 80), index=idx)
    analyzer = TrendAnalyzer({"min_samples": 20})

    result = analyzer.analyze_trend(series, "ic")

    assert isinstance(result, dict)
    assert result["trend"] in {"down", "flat"}


def test_short_time_series_skip():
    idx = pd.date_range("2024-01-01", periods=10, freq="12h")
    series = pd.Series(np.linspace(1.0, 0.2, 10), index=idx)
    analyzer = TrendAnalyzer({"min_samples": 20})

    result = analyzer.analyze_trend(series, "ic")

    assert isinstance(result, SkippedResult)


def test_analyze_multi_dimension_combined_signal():
    idx = pd.date_range("2024-01-01", periods=80, freq="12h")
    ic = pd.Series(np.linspace(1.0, 0.2, 80), index=idx)
    centrality = pd.Series(np.linspace(0.1, 0.5, 80), index=idx)
    analyzer = TrendAnalyzer({"min_samples": 20})

    result = analyzer.analyze_multi_dimension(
        feature_name="f1",
        rolling_ic=ic,
        rolling_centrality=centrality,
        ic_decay_half_life=3.0,
    )

    signal = result["f1"]["combined_signal"]
    assert signal["recommendation"] in {"正常", "警告", "危險"}


def test_batch_analyze():
    idx = pd.date_range("2024-01-01", periods=100, freq="12h")
    matrix = pd.DataFrame(
        {
            "f1": np.linspace(0.1, 0.5, 100),
            "f2": np.linspace(0.5, 0.1, 100),
        },
        index=idx,
    )
    analyzer = TrendAnalyzer({"min_samples": 20})

    result = analyzer.batch_analyze(matrix, top_n=2)

    assert set(result.keys()) == {"f1", "f2"}
