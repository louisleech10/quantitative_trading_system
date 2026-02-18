import numpy as np
import pytest


def test_L1_invalid_fraction(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    with pytest.raises(ValueError):
        learning_curve_analyzer.analyze_data_curve(model_factory, X, y, X.columns.tolist(), train_fractions=[0.0, 0.2])


def test_L2_fraction_too_small(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = learning_curve_analyzer.analyze_data_curve(model_factory, X.iloc[:100], y[:100], X.columns.tolist(), train_fractions=[0.05, 0.4, 1.0])
    assert all(frac >= 0.4 for frac in result["fractions"])


def test_L3_feature_count_exceeds(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = learning_curve_analyzer.analyze_feature_curve(model_factory, X, y, X.columns.tolist(), feature_counts=[5, 999])
    assert max(result["feature_counts"]) <= X.shape[1]


def test_L4_no_predictive_power(learning_curve_analyzer):
    diagnosis = learning_curve_analyzer.diagnose_bias_variance(
        train_scores=[0.55, 0.54, 0.53],
        cv_scores=[0.5, 0.51, 0.5],
        fractions=[0.2, 0.6, 1.0],
    )
    assert diagnosis["type"] == "no_predictive_power"


def test_L5_nan_fold(learning_curve_analyzer, synthetic_binary_data, model_factory, monkeypatch):
    X, y = synthetic_binary_data

    def fake_cv(*args, **kwargs):
        return [np.nan, None, 0.62]

    monkeypatch.setattr(learning_curve_analyzer, "_time_series_cv_auc", fake_cv)
    result = learning_curve_analyzer.analyze_data_curve(model_factory, X, y, X.columns.tolist(), train_fractions=[0.2])
    assert result["cv_scores"] == [0.62]


def test_L6_shap_unavailable(learning_curve_analyzer, synthetic_binary_data, model_factory, monkeypatch):
    X, y = synthetic_binary_data

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "shap":
            raise ImportError("no shap")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    result = learning_curve_analyzer.analyze_feature_curve(model_factory, X, y, X.columns.tolist(), ranking_method="shap")
    assert "feature_ranking" in result


def test_L7_single_feature(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    X_single = X[[X.columns[0]]]
    result = learning_curve_analyzer.analyze_feature_curve(model_factory, X_single, y, X_single.columns.tolist())
    assert result["feature_counts"] == [1]


def test_L8_small_dataset(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = learning_curve_analyzer.full_analysis(model_factory, X.iloc[:150], y[:150], X.columns.tolist())
    assert "learning_curve" in result


def test_high_variance_diagnosis(learning_curve_analyzer):
    diagnosis = learning_curve_analyzer.diagnose_bias_variance(
        train_scores=[0.9, 0.85, 0.82],
        cv_scores=[0.6, 0.62, 0.65],
        fractions=[0.2, 0.6, 1.0],
    )
    assert diagnosis["type"] == "high_variance"


def test_full_analysis_schema(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = learning_curve_analyzer.full_analysis(model_factory, X, y, X.columns.tolist())
    assert "learning_curve" in result
    assert "data_curve" in result["learning_curve"]
    assert "feature_curve" in result["learning_curve"]
    assert "diagnosis" in result["learning_curve"]


def test_data_curve_scores_are_bounded(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = learning_curve_analyzer.analyze_data_curve(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_fractions=[0.2, 0.4, 0.8, 1.0],
    )
    assert result["fractions"]
    assert all(0.0 <= score <= 1.0 for score in result["train_scores"])
    assert all(0.0 <= score <= 1.0 for score in result["cv_scores"])


def test_feature_curve_optimal_in_used_counts(learning_curve_analyzer, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = learning_curve_analyzer.analyze_feature_curve(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        feature_counts=[3, 5, 10, 15],
    )
    assert result["feature_counts"]
    assert result["optimal_n_features"] in result["feature_counts"]


def test_good_fit_diagnosis(learning_curve_analyzer):
    diagnosis = learning_curve_analyzer.diagnose_bias_variance(
        train_scores=[0.66, 0.67, 0.68],
        cv_scores=[0.63, 0.64, 0.65],
        fractions=[0.2, 0.6, 1.0],
    )
    assert diagnosis["type"] == "good_fit"


def test_high_bias_diagnosis(learning_curve_analyzer):
    diagnosis = learning_curve_analyzer.diagnose_bias_variance(
        train_scores=[0.55, 0.56, 0.57],
        cv_scores=[0.53, 0.54, 0.55],
        fractions=[0.2, 0.6, 1.0],
    )
    assert diagnosis["type"] == "high_bias"
