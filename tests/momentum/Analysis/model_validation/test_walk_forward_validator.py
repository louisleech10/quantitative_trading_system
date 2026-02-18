import numpy as np
import pytest

from momentum.Analysis.model_validation.walk_forward_validator import (
    WalkForwardReport,
)


def test_W1_data_too_short(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X.iloc[:100],
        y=y[:100],
        feature_names=X.columns.tolist(),
        train_size=80,
        test_size=30,
    )
    assert result.error_type == "INSUFFICIENT_DATA"


def test_W2_small_train_window(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=45,
        test_size=80,
    )
    assert isinstance(report, WalkForwardReport)


def test_W3_minimal_periods(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X.iloc[:750],
        y=y[:750],
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert report.n_periods <= 2


def test_W4_single_class_test_period(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    y_mod = y.copy()
    y_mod[505:605] = 1
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y_mod,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
        step_size=100,
    )
    assert any(period.test_auc is None for period in report.period_results)


def test_W5_step_larger_than_test(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
        step_size=150,
    )
    assert report.n_periods >= 1


def test_W6_purge_exceeds_test(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"purge_gap": 50})
    with pytest.raises(ValueError):
        validator.validate_rolling(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist(), train_size=500, test_size=50)


def test_W7_training_failure_single_period(walk_forward_validator, synthetic_binary_data):
    X, y = synthetic_binary_data

    def bad_factory():
        class BadModel:
            def fit(self, X, y):
                raise RuntimeError("boom")

        return BadModel()

    report = walk_forward_validator.validate_rolling(
        model_factory=bad_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert isinstance(report, WalkForwardReport)
    assert report.n_periods == 0


def test_W8_both_modes(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"mode": "both", "train_size": 500, "test_size": 100})
    result = validator.validate(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist())
    assert "rolling" in result and "expanding" in result


def test_W9_all_periods_below_random(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    y_inverse = 1 - y
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y_inverse,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert report.assessment in {"unstable", "moderate", "robust"}


def test_W10_expanding_memory_warning(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_expanding(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        initial_train_size=500,
        test_size=100,
        step_size=200,
    )
    assert isinstance(report, WalkForwardReport)


def test_rolling_basic_metrics(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert report.n_periods >= 3
    assert report.mean_oos_auc >= 0.0
    assert report.assessment in {"robust", "moderate", "unstable"}


def test_validate_default_returns_rolling_key(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"mode": "rolling", "train_size": 500, "test_size": 100})
    result = validator.validate(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist())
    assert "rolling" in result
    assert isinstance(result["rolling"], WalkForwardReport)


def test_validate_expanding_returns_expanding_key(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"mode": "expanding", "train_size": 500, "test_size": 100})
    result = validator.validate(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist())
    assert "expanding" in result
    assert isinstance(result["expanding"], WalkForwardReport)


def test_rolling_report_contains_period_ranges(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
        step_size=100,
    )
    assert isinstance(report, WalkForwardReport)
    assert report.period_results
    first = report.period_results[0]
    assert first.train_end_idx > first.train_start_idx
    assert first.test_end_idx > first.test_start_idx


def test_rolling_feature_stability_has_reasonable_ratio(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert isinstance(report, WalkForwardReport)
    assert report.feature_stability
    assert all(0.0 <= value <= 1.0 for value in report.feature_stability.values())
