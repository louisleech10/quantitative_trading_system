import time

import numpy as np
import pandas as pd

import momentum.Analysis.feature_quality_diagnostics as quality_module
from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics


def test_all_nan_feature_quality():
    analyzer = FeatureQualityDiagnostics(config={})
    df = pd.DataFrame({"f1": [np.nan] * 50})
    result = analyzer.run_full_diagnostics(df)
    assert result["coverage_stats"]["f1"]["coverage"] == 0.0
    assert result["adf_results"]["f1"]["skipped"] is True


def test_constant_feature_quality():
    analyzer = FeatureQualityDiagnostics(config={})
    df = pd.DataFrame({"f1": [1.0] * 100})
    result = analyzer.run_batch_adf_test(df)
    assert result["f1"]["skipped"] is True


def test_insufficient_adf_samples():
    analyzer = FeatureQualityDiagnostics(config={})
    df = pd.DataFrame({"f1": np.random.randn(10)})
    result = analyzer.run_batch_adf_test(df)
    assert result["f1"]["reason"] == "insufficient_samples"


def test_no_rolling_ic_for_drift():
    analyzer = FeatureQualityDiagnostics(config={})
    df = pd.DataFrame({"f1": np.random.randn(120), "f2": np.random.randn(120)})
    result = analyzer.run_full_diagnostics(df)
    assert result["drift_results"]["f1"]["skipped"] is True


def test_single_feature_quality():
    analyzer = FeatureQualityDiagnostics(config={})
    df = pd.DataFrame({"f1": np.random.randn(150)})
    scan = analyzer.redundancy_pre_scan(df)
    assert scan["skipped"] is True


def test_adf_timeout_single(monkeypatch):
    analyzer = FeatureQualityDiagnostics(config={"adf_timeout_sec": 0.01})

    def slow_adf(*args, **kwargs):
        time.sleep(0.2)
        return -3.0, 0.01, 0, 0, {}, 0.0

    monkeypatch.setattr(quality_module, "adfuller", slow_adf)
    df = pd.DataFrame({"f1": np.random.randn(200)})
    result = analyzer.run_batch_adf_test(df)
    assert result["f1"]["skipped"] is True
    assert result["f1"].get("timeout") is True


def test_adf_error_branch(monkeypatch):
    analyzer = FeatureQualityDiagnostics(config={"adf_timeout_sec": 1.0})

    def boom(*args, **kwargs):
        raise RuntimeError("adf boom")

    monkeypatch.setattr(quality_module, "adfuller", boom)
    df = pd.DataFrame({"f1": np.random.randn(200)})
    result = analyzer.run_batch_adf_test(df)
    assert result["f1"]["reason"] == "adf_error"


def test_autocorrelation_insufficient_and_error(monkeypatch):
    analyzer = FeatureQualityDiagnostics(config={"ljungbox_lags": 10})
    short_df = pd.DataFrame({"f1": np.random.randn(8)})
    short_result = analyzer.run_batch_autocorrelation_test(short_df)
    assert short_result["f1"]["reason"] == "insufficient_samples"

    def lb_boom(*args, **kwargs):
        raise RuntimeError("lb boom")

    monkeypatch.setattr(quality_module, "acorr_ljungbox", lb_boom)
    long_df = pd.DataFrame({"f1": np.random.randn(120)})
    err_result = analyzer.run_batch_autocorrelation_test(long_df)
    assert err_result["f1"]["reason"] == "ljungbox_error"


def test_detect_concept_drift_branches():
    analyzer = FeatureQualityDiagnostics(config={"drift_threshold": 0.1})

    short = analyzer.detect_concept_drift(pd.Series(np.random.randn(10)), "f1")
    assert short["skipped"] is True

    first = np.random.normal(0.0, 0.2, 120)
    second = np.random.normal(1.5, 0.2, 120)
    drift_series = pd.Series(np.concatenate([first, second]))
    drift = analyzer.detect_concept_drift(drift_series, "f2")
    assert drift["skipped"] is False
    assert isinstance(drift["drifted"], bool)


def test_compute_coverage_and_redundancy_pairs():
    analyzer = FeatureQualityDiagnostics(config={"redundancy_threshold": 0.6})
    x = np.linspace(0, 1, 200)
    df = pd.DataFrame({"f1": x, "f2": x * 0.9 + 0.01, "f3": np.random.randn(200)})

    coverage = analyzer.compute_coverage_stats(df)
    assert coverage["f1"]["coverage"] == 1.0

    scan = analyzer.redundancy_pre_scan(df)
    assert scan["skipped"] is False
    assert isinstance(scan["high_correlation_pairs"], list)


def test_run_full_diagnostics_with_rolling_dict():
    analyzer = FeatureQualityDiagnostics(config={})
    df = pd.DataFrame({"f1": np.random.randn(180), "f2": np.random.randn(180)})
    rolling_dict = {
        "f1": pd.Series(np.random.randn(180)),
        "f2": pd.Series(np.random.randn(180)),
    }
    result = analyzer.run_full_diagnostics(df, rolling_dict)
    assert result["summary"]["total_features"] == 2
    assert "quality_flags" in result


def test_effective_sample_ratio_and_psi_helpers(monkeypatch):
    ratio_short = FeatureQualityDiagnostics._effective_sample_ratio(pd.Series([1.0, 2.0]))
    assert ratio_short == 1.0

    monkeypatch.setattr(np, "corrcoef", lambda a, b: np.array([[1.0, np.nan], [np.nan, 1.0]]))
    ratio_nan = FeatureQualityDiagnostics._effective_sample_ratio(pd.Series(np.random.randn(20)))
    assert ratio_nan == 1.0

    psi_insufficient = FeatureQualityDiagnostics._psi(pd.Series([1.0, 2.0]), pd.Series([1.0, 2.0]))
    assert np.isnan(psi_insufficient)

    psi_low_var = FeatureQualityDiagnostics._psi(pd.Series([1.0] * 60), pd.Series([1.0] * 60))
    assert psi_low_var == 0.0
