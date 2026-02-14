from __future__ import annotations

import numpy as np

from momentum.Analysis.calibration_analyzer import CalibrationAnalyzer
from momentum.Analysis.drift_analyzer import DriftAnalyzer


def test_lightgbm_shap_global_and_single_case(trained_lightgbm, synthetic_training_data):
    X, _, _ = synthetic_training_data

    global_result = trained_lightgbm.analyze_shap_global(X.iloc[:30], sample_size=20)
    single_result = trained_lightgbm.explain_single_case(X.iloc[0])

    assert len(global_result.feature_names) > 0
    assert global_result.shap_values.size > 0
    assert single_result.shap_values.size > 0


def test_calibration_analyzer_with_lightgbm_prediction(trained_lightgbm, synthetic_training_data):
    X, y, _ = synthetic_training_data
    y_pred = trained_lightgbm.predict_proba(X)[:, 1]

    calibration = CalibrationAnalyzer().calculate_metrics(y_true=y, y_pred_proba=y_pred)

    assert 0.0 <= calibration.brier_score <= 1.0
    assert 0.0 <= calibration.ece <= 1.0
    assert calibration.calibration_quality in {"good", "fair", "poor"}


def test_drift_analyzer_with_lightgbm_features(synthetic_training_data):
    X, _, _ = synthetic_training_data

    train_values = X.iloc[:100, 0].to_numpy()
    test_values = (X.iloc[100:200, 0] + 0.5).to_numpy()

    psi, bins, train_pct, test_pct = DriftAnalyzer().calculate_psi(train_values, test_values, bins=8)

    assert psi >= 0
    assert len(bins) >= 2
    assert len(train_pct) == len(test_pct)


def test_drift_report_and_feature_list(synthetic_training_data):
    X, _, feature_names = synthetic_training_data
    analyzer = DriftAnalyzer()

    X_train = X.iloc[:100].to_numpy()
    X_test = (X.iloc[100:200] + 0.2).to_numpy()
    psi_results = analyzer.calculate_all_features_psi(X_train, X_test, feature_names=feature_names)
    report = analyzer.generate_drift_report(psi_results)
    drifted = analyzer.get_drifted_features(psi_results, threshold=0.1)

    assert len(report.results) == len(feature_names)
    assert isinstance(drifted, list)


def test_lightgbm_predict_output_compatible_with_shared_analyzers(trained_lightgbm, synthetic_training_data):
    X, y, _ = synthetic_training_data
    output = trained_lightgbm.get_predictions(X, y_true=y)

    assert output.y_pred_proba.shape == (len(X), 2)
    assert set(np.unique(output.y_pred_label)).issubset({0, 1})
