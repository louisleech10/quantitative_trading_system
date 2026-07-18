import numpy as np
import pandas as pd
import pytest


def test_A1_feature_name_mismatch(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    X_train = X.iloc[:800].copy()
    X_test = X.iloc[800:1000].copy()
    X_test = X_test.rename(columns={X_test.columns[0]: "mismatch"})

    with pytest.raises(ValueError):
        adversarial_validator.validate_distribution(X_train, X_test)


def test_A2_tiny_test_set(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    X_train = X.iloc[:800].copy()
    X_test = X.iloc[800:815].copy()
    result = adversarial_validator.validate_distribution(X_train, X_test)
    assert "distribution_test" in result


def test_A3_identical_distributions(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    X_train = X.iloc[:500].copy()
    X_test = X_train.copy()
    result = adversarial_validator.validate_distribution(X_train, X_test)
    auc = result["distribution_test"]["auc"]
    assert abs(auc - 0.5) <= 0.15


def test_A4_no_timestamps_skip_leakage(adversarial_validator, synthetic_binary_data):
    X, y = synthetic_binary_data
    result = adversarial_validator.full_validation(
        X_train=X.iloc[:800],
        X_test=X.iloc[800:1000],
        y_train=y[:800],
        timestamps=None,
    )
    assert result["adversarial_validation"]["leakage_detection"]["status"] == "skipped"


def test_A5_extreme_future_window(adversarial_validator, synthetic_binary_data, synthetic_timestamps):
    X, y = synthetic_binary_data
    with pytest.raises(ValueError):
        adversarial_validator.detect_leakage(X.iloc[:100], y[:100], synthetic_timestamps[:100], future_window=60)


def test_A6_all_features_drifted(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    X_train = X.iloc[:800].copy()
    X_test = X.iloc[800:1200].copy() + 3.0
    result = adversarial_validator.feature_level_tests(X_train, X_test)
    assert result
    feature_rows = [v for v in result.values() if isinstance(v, dict) and "status" in v]
    assert feature_rows
    assert all(v["status"] in {"warning", "severe"} for v in feature_rows)
    assert result.get("diagnostic_only") is True


def test_A7_all_nan_feature(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    X_train = X.iloc[:800].copy()
    X_test = X.iloc[800:1000].copy()
    X_train["nan_feature"] = np.nan
    X_test["nan_feature"] = np.nan
    result = adversarial_validator.feature_level_tests(X_train, X_test)
    assert "nan_feature" not in result


def test_A8_empty_dataset(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    result = adversarial_validator.validate_distribution(X.iloc[:0], X.iloc[:10])
    assert result["distribution_test"]["status"] == "skipped"


def test_distribution_drift_detected(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    X_train = X.iloc[:800].copy()
    X_test = X.iloc[800:1200].copy() + 2.0
    result = adversarial_validator.validate_distribution(X_train, X_test)
    assert result["distribution_test"]["auc"] > 0.7
    assert result["distribution_test"]["status"] == "severe"


def test_full_validation_schema(adversarial_validator, synthetic_binary_data, synthetic_timestamps):
    X, y = synthetic_binary_data
    result = adversarial_validator.full_validation(
        X_train=X.iloc[:800],
        X_test=X.iloc[800:1200],
        y_train=y[:800],
        timestamps=synthetic_timestamps[:800],
    )
    assert "adversarial_validation" in result
    assert "distribution_test" in result["adversarial_validation"]
    assert "feature_level_tests" in result["adversarial_validation"]


def test_feature_level_tests_returns_expected_schema(adversarial_validator, synthetic_binary_data):
    X, _ = synthetic_binary_data
    result = adversarial_validator.feature_level_tests(X.iloc[:600], X.iloc[600:1200])
    assert result
    first_value = next(v for v in result.values() if isinstance(v, dict) and "ks_statistic" in v)
    assert "ks_statistic" in first_value
    assert "ks_pvalue" in first_value
    assert "psi" in first_value
    assert "status" in first_value
    assert result.get("diagnostic_only") is True
    assert result.get("signal_use_denied") is True


def test_detect_leakage_schema(adversarial_validator, synthetic_binary_data, synthetic_timestamps):
    X, y = synthetic_binary_data
    leakage = adversarial_validator.detect_leakage(
        X=X.iloc[:800],
        y=y[:800],
        timestamps=synthetic_timestamps[:800],
        future_window=5,
    )
    assert "suspicious_features" in leakage
    assert "autocorrelation_flags" in leakage
    assert leakage["status"] in {"ok", "skipped"}
    assert leakage.get("diagnostic_only") is True
    assert leakage.get("signal_use_denied") is True


def test_full_validation_recommendations_type(adversarial_validator, synthetic_binary_data, synthetic_timestamps):
    X, y = synthetic_binary_data
    result = adversarial_validator.full_validation(
        X_train=X.iloc[:800],
        X_test=X.iloc[800:1200] + 2.5,
        y_train=y[:800],
        timestamps=synthetic_timestamps[:800],
    )
    recommendations = result["adversarial_validation"]["recommendations"]
    assert isinstance(recommendations, list)
