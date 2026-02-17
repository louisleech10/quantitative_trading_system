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


def test_detect_feature_families_with_metadata():
    analyzer = ParameterSensitivityAnalyzer({})
    features = ["a_10", "a_20", "b_10"]
    metadata = {
        "a_10": {"indicator": "rsi", "data_source": "close"},
        "a_20": {"indicator": "rsi", "data_source": "close"},
        "b_10": {"indicator": "ema", "data_source": "close"},
    }
    families = analyzer.detect_feature_families(features, metadata)
    assert "close_rsi" in families
    assert len(families["close_rsi"]) == 2


def test_analyze_from_variants_insufficient_valid_variants():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="close_RSI",
        variant_params={"variants": ["close_RSI_10", "missing_1", "missing_2"]},
    )
    assert isinstance(result, SkippedResult)


def test_analyze_from_variants_all_nan_ic():
    idx = pd.date_range("2024-01-01", periods=240, freq="12h")
    labels = pd.Series(0.1, index=idx)
    df = pd.DataFrame(
        {
            "f_10": np.arange(240, dtype=float),
            "f_20": np.arange(240, dtype=float) + 1,
            "f_30": np.arange(240, dtype=float) + 2,
        },
        index=idx,
    )
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="f",
        variant_params={"variants": ["f_10", "f_20", "f_30"]},
    )
    assert isinstance(result, SkippedResult)


def test_classify_overfitting_risk_levels():
    analyzer = ParameterSensitivityAnalyzer({"ic_std_threshold_low": 0.02, "ic_std_threshold_high": 0.05})
    assert analyzer.classify_overfitting_risk(0.01, 0.1) == "low"
    assert analyzer.classify_overfitting_risk(0.03, 0.2) == "medium"
    assert analyzer.classify_overfitting_risk(0.08, 0.4) == "high"


def test_batch_analyze_collects_high_and_low_risk():
    idx = pd.date_range("2024-01-01", periods=240, freq="12h")
    rng = np.random.default_rng(11)
    base = rng.normal(size=240)
    labels = pd.Series(base + rng.normal(scale=0.1, size=240), index=idx)

    df = pd.DataFrame(
        {
            "stable_10": base + rng.normal(scale=0.01, size=240),
            "stable_20": base + rng.normal(scale=0.01, size=240),
            "stable_30": base + rng.normal(scale=0.01, size=240),
            "noisy_10": rng.normal(size=240),
            "noisy_20": rng.normal(size=240),
            "noisy_30": rng.normal(size=240),
        },
        index=idx,
    )
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.batch_analyze(df, labels)

    assert "high_risk_families" in result
    assert "robust_families" in result


def test_compute_ic_and_icir_proxy_edge_cases():
    x = pd.Series([1, 2, 3, 4])
    y = pd.Series([1, 2, 3, 4])
    assert np.isnan(ParameterSensitivityAnalyzer._compute_ic(x, y))

    x2 = pd.Series([1, 1, 1, 1, 1, 1])
    y2 = pd.Series([1, 2, 3, 4, 5, 6])
    assert np.isnan(ParameterSensitivityAnalyzer._compute_ic(x2, y2))

    zeros = pd.Series([0, 0, 0, 0, 0, 0])
    assert np.isnan(ParameterSensitivityAnalyzer._compute_icir_proxy(zeros, y2))


def test_extract_param_value_without_suffix():
    value = ParameterSensitivityAnalyzer._extract_param_value("feature_alpha")
    assert value == "feature_alpha"
