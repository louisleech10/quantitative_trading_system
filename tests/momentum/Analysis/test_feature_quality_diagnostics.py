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
    # ICPERF Task 0.4 ㉒ QN-5：舊＝設 adf_timeout_sec 0.01 且 ADF 耗時 0.2 秒 ⇒ skipped＝True、timeout＝True（丟棄已算值）；
    # 新＝移除牆鐘逾時（使用者 2026-10-27「全專案禁時間上限停運算」）⇒ 設極小 adf_timeout_sec 時之值與不設時相同、
    # 無 skipped／timeout
    analyzer = FeatureQualityDiagnostics(config={"adf_timeout_sec": 0.01})
    baseline_analyzer = FeatureQualityDiagnostics(config={})

    def slow_adf(*args, **kwargs):
        time.sleep(0.2)
        return -3.0, 0.01, 0, 0, {}, 0.0

    monkeypatch.setattr(quality_module, "adfuller", slow_adf)
    df = pd.DataFrame({"f1": np.random.randn(200)})
    result = analyzer.run_batch_adf_test(df)
    baseline = baseline_analyzer.run_batch_adf_test(df)
    assert result["f1"]["skipped"] is False
    assert "timeout" not in result["f1"]
    assert result["f1"] == baseline["f1"]
    assert result["f1"]["adf_statistic"] == -3.0 and result["f1"]["p_value"] == 0.01
    assert result["f1"]["is_stationary"] is True
