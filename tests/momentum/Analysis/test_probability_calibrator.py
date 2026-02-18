import builtins

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from momentum.Analysis.probability_calibrator import ProbabilityCalibrator


def _train_model(X, y):
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    return model


def test_C1_single_class(probability_calibrator):
    y_true = np.ones(100, dtype=int)
    y_pred = np.random.uniform(0.2, 0.8, 100)
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred)
    assert result["probability_calibration"]["status"] == "skipped"
    assert result["probability_calibration"]["skipped"]["error_type"] == "SINGLE_CLASS"


def test_C2_zero_variance_proba(probability_calibrator):
    y_true = np.random.binomial(1, 0.5, 120)
    y_pred = np.full(120, 0.5)
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred)
    assert result["probability_calibration"]["status"] == "skipped"
    assert result["probability_calibration"]["skipped"]["error_type"] == "ZERO_VARIANCE"


def test_C3_small_sample_auto_fallback(probability_calibrator):
    y_true = np.random.binomial(1, 0.5, 40)
    y_pred = np.clip(np.random.normal(0.5, 0.2, 40), 0.01, 0.99)
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="auto")
    assert result["probability_calibration"]["method"] in {"platt", "original"}


def test_C4_isotonic_small_sample_fallback(probability_calibrator):
    y_true = np.random.binomial(1, 0.5, 200)
    y_pred = np.clip(np.random.normal(0.5, 0.2, 200), 0.01, 0.99)
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="isotonic")
    assert result["probability_calibration"]["method"] in {"platt", "original"}


def test_C5_venn_abers_downsampling(probability_calibrator):
    y_true = np.random.binomial(1, 0.5, 6000)
    y_pred = np.clip(np.random.normal(0.5, 0.2, 6000), 0.01, 0.99)
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="venn_abers")
    assert "probability_calibration" in result


def test_C6_cv_exceeds_half_samples(probability_calibrator):
    y_true = np.random.binomial(1, 0.5, 100)
    y_pred = np.clip(np.random.normal(0.5, 0.2, 100), 0.01, 0.99)
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, cv=80)
    assert result["probability_calibration"]["cv_folds"] <= 50


def test_C7_calibration_degradation_fallback(probability_calibrator, monkeypatch):
    y_true = np.random.binomial(1, 0.5, 200)
    y_pred = np.clip(np.random.normal(0.5, 0.2, 200), 0.01, 0.99)

    monkeypatch.setattr(
        probability_calibrator,
        "_apply_calibration_method",
        lambda method, y_true, y_pred, cv: np.clip(1 - y_pred, 0.01, 0.99),
    )

    def fake_metrics(y_true_in=None, y_pred_in=None, **kwargs):
        if y_pred_in is None:
            y_pred_in = kwargs.get("y_pred")
        if np.allclose(y_pred_in, y_pred):
            return {"ece": 0.05, "brier": 0.18}
        return {"ece": 0.2, "brier": 0.28}

    monkeypatch.setattr(probability_calibrator, "_compute_metrics", fake_metrics)
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="platt")
    assert result["probability_calibration"]["calibration_failed"] is True
    assert result["probability_calibration"]["method"] == "original"


def test_C8_predict_before_fit(probability_calibrator):
    X = np.random.randn(10, 3)
    with pytest.raises(ValueError):
        probability_calibrator.predict_calibrated(X)


def test_C9_nan_in_predictions(probability_calibrator):
    y_true = np.random.binomial(1, 0.5, 120)
    y_pred = np.clip(np.random.normal(0.5, 0.2, 120), 0.01, 0.99)
    y_pred[:10] = np.nan
    result = probability_calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred)
    assert "probability_calibration" in result


def test_C10_beta_package_missing_fallback(monkeypatch):
    calibrator = ProbabilityCalibrator()
    y_true = np.random.binomial(1, 0.5, 200)
    y_pred = np.clip(np.random.normal(0.5, 0.2, 200), 0.01, 0.99)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "betacal":
            raise ImportError("betacal unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="beta")
    assert result["probability_calibration"]["method"] in {"platt", "original"}


def test_C11_feature_mismatch(synthetic_binary_data):
    X, y = synthetic_binary_data
    model = _train_model(X, y)
    calibrator = ProbabilityCalibrator()
    calibrator.fit(model=model, X_cal=X, y_cal=y)

    X_bad = X.iloc[:, :5]
    with pytest.raises(ValueError):
        calibrator.predict_calibrated(X_bad)


def test_fit_from_predictions_improves_or_keeps_ece(synthetic_predictions):
    y_pred, y_true = synthetic_predictions
    calibrator = ProbabilityCalibrator()
    result = calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred)
    comp = result["probability_calibration"]["comparison"]
    method = result["probability_calibration"]["method"]
    assert comp[method]["ece"] <= comp["original"]["ece"] or result["probability_calibration"]["calibration_failed"]


def test_fit_and_predict_calibrated(synthetic_binary_data):
    X, y = synthetic_binary_data
    model = _train_model(X, y)
    calibrator = ProbabilityCalibrator()
    calibrator.fit(model=model, X_cal=X, y_cal=y)

    calibrated = calibrator.predict_calibrated(X.iloc[:20])
    assert calibrated.shape[0] == 20
    assert np.all((calibrated >= 0.0) & (calibrated <= 1.0))


def test_platt_scaling_schema(synthetic_predictions):
    y_pred, y_true = synthetic_predictions
    calibrator = ProbabilityCalibrator()
    result = calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="platt")
    payload = result["probability_calibration"]
    assert payload["method"] in {"platt", "original"}
    assert "comparison" in payload
    assert "reliability_curve" in payload


def test_auto_selects_best_method_exists(synthetic_predictions):
    y_pred, y_true = synthetic_predictions
    calibrator = ProbabilityCalibrator()
    result = calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="auto")
    payload = result["probability_calibration"]
    assert payload["best_method"] in payload["comparison"]


def test_transform_proba_after_fit_from_predictions(synthetic_predictions):
    y_pred, y_true = synthetic_predictions
    calibrator = ProbabilityCalibrator()
    calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="platt")
    transformed = calibrator.transform_proba(y_pred[:30])
    assert transformed.shape[0] == 30
    assert np.all((transformed >= 0.0) & (transformed <= 1.0))


def test_get_calibration_comparison_returns_selected_method(synthetic_predictions):
    y_pred, y_true = synthetic_predictions
    calibrator = ProbabilityCalibrator()
    calibrator.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, method="platt")
    comparison = calibrator.get_calibration_comparison()
    assert comparison["method"] in {"platt", "original"}
    assert "comparison" in comparison


def test_venn_abers_intervals_valid_bounds(synthetic_binary_data):
    X, y = synthetic_binary_data
    model = _train_model(X, y)
    calibrator = ProbabilityCalibrator()
    calibrator.fit(model=model, X_cal=X, y_cal=y, method="venn_abers")
    lower, center, upper = calibrator.get_venn_abers_intervals(X.iloc[:25])
    assert lower.shape == center.shape == upper.shape
    assert np.all(lower <= center)
    assert np.all(center <= upper)
    assert np.all((lower >= 0.0) & (upper <= 1.0))
