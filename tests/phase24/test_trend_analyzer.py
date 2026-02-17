import numpy as np
import pandas as pd
from types import SimpleNamespace

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


def test_constant_series_returns_flat():
    idx = pd.date_range("2024-01-01", periods=40, freq="12h")
    series = pd.Series(0.5, index=idx)
    analyzer = TrendAnalyzer({"min_samples": 20})
    result = analyzer.analyze_trend(series, "const")
    assert isinstance(result, dict)
    assert result["trend"] == "flat"


def test_interpret_trend_branches():
    analyzer = TrendAnalyzer({})
    assert "下降" in analyzer._interpret_trend("down")
    assert "上升" in analyzer._interpret_trend("up")
    assert "持平" in analyzer._interpret_trend("flat")
    assert "不確定" in analyzer._interpret_trend("other")


def test_combine_signal_branches():
    analyzer = TrendAnalyzer({})

    danger = analyzer._combine_signal({"trend": "down"}, {"trend": "up"}, None)
    assert danger["recommendation"] == "危險"

    warn = analyzer._combine_signal({"trend": "flat"}, {"trend": "up"}, 4.0)
    assert warn["recommendation"] in {"警告", "危險"}

    normal = analyzer._combine_signal({"trend": "up"}, {"trend": "down"}, None)
    assert normal["recommendation"] == "正常"


def test_analyze_trend_indeterminate_branch(monkeypatch):
    idx = pd.date_range("2024-01-01", periods=80, freq="12h")
    series = pd.Series(np.linspace(0.1, 0.2, 80), index=idx)
    analyzer = TrendAnalyzer({"min_samples": 20})

    monkeypatch.setattr(
        "momentum.Analysis.trend_analyzer.linregress",
        lambda x, y: SimpleNamespace(slope=np.nan, pvalue=0.01, rvalue=np.nan, intercept=0.0),
    )
    result = analyzer.analyze_trend(series, "nan")
    assert result["trend"] == "indeterminate"


def test_analyze_multi_dimension_includes_optional_dimensions():
    idx = pd.date_range("2024-01-01", periods=120, freq="12h")
    analyzer = TrendAnalyzer({"min_samples": 20})
    result = analyzer.analyze_multi_dimension(
        feature_name="f_opt",
        rolling_ic=pd.Series(np.linspace(0.0, 0.2, 120), index=idx),
        rolling_centrality=pd.Series(np.linspace(0.3, 0.1, 120), index=idx),
        factor_return_cumulative=pd.Series(np.linspace(0.0, 0.5, 120), index=idx),
        ls_spread_series=pd.Series(np.linspace(0.2, -0.1, 120), index=idx),
    )
    payload = result["f_opt"]
    assert "factor_return_trend" in payload
    assert "ls_spread_trend" in payload


def test_ensure_trend_dict_skip_result():
    skipped = SkippedResult(module_name="trend_analysis", reason="x", error_type="INSUFFICIENT_DATA")
    assert TrendAnalyzer._ensure_trend_dict(skipped) is None
