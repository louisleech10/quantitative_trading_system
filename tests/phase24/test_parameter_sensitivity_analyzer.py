import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer


def _make_dataset():
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=240, freq="12h")
    base = rng.normal(size=240)
    labels = pd.Series(base * 0.02 + rng.normal(scale=0.01, size=240), index=idx)
    df = pd.DataFrame(
        {
            "close_RSI_10": base + rng.normal(scale=0.1, size=240),
            "close_RSI_14": base + rng.normal(scale=0.1, size=240),
            "close_RSI_21": base + rng.normal(scale=0.1, size=240),
            "other": rng.normal(size=240),
        },
        index=idx,
    )
    return df, labels


def test_detect_feature_families():
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    families = analyzer.detect_feature_families(["close_RSI_10", "close_RSI_14", "x"])
    assert "close_RSI" in families


def test_analyze_from_variants_success():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="close_RSI",
        variant_params={"variants": ["close_RSI_10", "close_RSI_14", "close_RSI_21"]},
    )
    assert isinstance(result, dict)
    assert "stability_metrics" in result


def test_small_family_skip():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="small",
        variant_params={"variants": ["close_RSI_10", "close_RSI_14"]},
    )
    assert isinstance(result, SkippedResult)


def test_batch_analyze():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.batch_analyze(df, labels)
    assert "families" in result
    assert "summary" in result
