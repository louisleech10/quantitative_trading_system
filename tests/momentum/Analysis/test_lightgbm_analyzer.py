from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
from momentum.Analysis.model_types import (
    FoldImportanceStabilityResult,
    OOTValidationResult,
    PRMetrics,
    PrecisionAtKResult,
)


def test_train_model_returns_model_performance(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 30, "num_leaves": 15})

    performance = analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    assert performance.engine_type == "lightgbm"
    assert 0.0 <= performance.cv_auc_mean <= 1.0
    assert performance.training_time_seconds is not None


def test_train_with_purged_cv_smoke(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    timestamps = list(range(len(X)))
    analyzer = LightGBMAnalyzer(params={"n_estimators": 20, "num_leaves": 15})

    performance = analyzer.train_with_purged_cv(
        X,
        y,
        n_splits=3,
        purge_gap=2,
        timestamps=timestamps,
        feature_names=feature_names,
    )

    assert performance.engine_type == "lightgbm"


def test_validate_oot_returns_status(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 20, "num_leaves": 15})
    perf = analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    result = analyzer.validate_oot(X.iloc[-60:], y[-60:], cv_auc_mean=perf.cv_auc_mean)

    assert isinstance(result, OOTValidationResult)
    assert result.gap_status in {"good", "warning", "severe"}


def test_validate_oot_single_class_returns_none_auc(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 20, "num_leaves": 15})
    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    y_oot = np.zeros(40, dtype=int)
    result = analyzer.validate_oot(X.iloc[:40], y_oot, cv_auc_mean=0.7)

    assert result.oot_auc is None
    assert result.gap_status == "warning"


def test_predict_and_predictions_output(trained_lightgbm, synthetic_training_data):
    X, y, _ = synthetic_training_data

    proba = trained_lightgbm.predict_proba(X)
    output = trained_lightgbm.get_predictions(X, y_true=y)

    assert proba.shape == (len(X), 2)
    assert output.y_pred_proba.shape == (len(X), 2)
    assert output.y_pred_label.shape == (len(X),)


def test_feature_importance_methods(trained_lightgbm):
    gain = trained_lightgbm.get_feature_importance(method="gain", top_n=5)
    split = trained_lightgbm.get_feature_importance(method="split", top_n=5)
    all_types = trained_lightgbm.get_all_importance_types(trained_lightgbm.feature_names or [], top_n=3)

    assert len(gain) == 5
    assert len(split) == 5
    assert set(all_types.keys()) == {"gain", "split"}


def test_permutation_and_fold_stability(trained_lightgbm, synthetic_training_data):
    X, y, _ = synthetic_training_data

    perm = trained_lightgbm.calculate_permutation_importance(X, y, n_repeats=2)
    stability = trained_lightgbm.calculate_fold_importance_stability(X, y, cv_folds=3)

    assert len(perm) == X.shape[1]
    assert all(item.importance_std >= 0 for item in perm)
    assert all(isinstance(item, FoldImportanceStabilityResult) for item in stability)


def test_precision_at_k_and_pr_metrics(trained_lightgbm, synthetic_training_data):
    X, y, _ = synthetic_training_data

    p_at_k = trained_lightgbm.calculate_precision_at_k(X, y, k_values=[1, 5, 10])
    pr_metrics = trained_lightgbm.calculate_pr_metrics(X, y)

    assert all(isinstance(item, PrecisionAtKResult) for item in p_at_k)
    assert isinstance(pr_metrics, PRMetrics)
    assert 0.0 <= pr_metrics.pr_auc <= 1.0


def test_recommend_k_returns_dict(trained_lightgbm, synthetic_training_data):
    X, y, _ = synthetic_training_data
    proba = trained_lightgbm.predict_proba(X)[:, 1]

    result = trained_lightgbm.recommend_k(y, proba, target_precision=0.5, k_candidates=[1, 5, 10])

    assert set(result.keys()) == {"recommended_k", "precision"}


def test_shap_methods_smoke(trained_lightgbm, synthetic_training_data):
    X, _, _ = synthetic_training_data

    global_result = trained_lightgbm.analyze_shap_global(X, sample_size=20)
    single_result = trained_lightgbm.explain_single_case(X.iloc[0])

    assert len(global_result.feature_names) > 0
    assert global_result.shap_values.size > 0
    assert single_result.shap_values.size > 0


def test_save_and_load_roundtrip(trained_lightgbm, synthetic_training_data):
    X, _, _ = synthetic_training_data
    model_path = Path("data_cache/models/test_lightgbm_roundtrip.pkl")

    trained_lightgbm.save_model(str(model_path))

    loaded = LightGBMAnalyzer()
    loaded.load_model(str(model_path))
    pred = loaded.predict_proba(X)

    assert pred.shape == (len(X), 2)
    assert loaded.get_model_type() == "lightgbm"

    if model_path.exists():
        model_path.unlink()


def test_train_input_empty_y_and_invalid_eval_size():
    analyzer = LightGBMAnalyzer(params={"n_estimators": 10})
    X = np.zeros((10, 3))
    y = np.array([])

    with pytest.raises(ValueError):
        analyzer.train_model(X[:0], y, feature_names=["a", "b", "c"])

    y_valid = np.array([0, 1] * 5)
    with pytest.raises(ValueError):
        analyzer.train_model(X, y_valid, feature_names=["a", "b", "c"], eval_size=0)
    with pytest.raises(ValueError):
        analyzer.train_model(X, y_valid, feature_names=["a", "b", "c"], eval_size=1)


def test_train_numpy_feature_mismatch_and_missing_names():
    analyzer = LightGBMAnalyzer(params={"n_estimators": 10})
    X = np.random.randn(12, 4)
    y = np.array([0, 1] * 6)

    with pytest.raises(ValueError, match="必須提供 feature_names"):
        analyzer.train_model(X, y)

    with pytest.raises(ValueError, match="特徵數量不匹配"):
        analyzer.train_model(X, y, feature_names=["f0", "f1"])


def test_train_with_custom_params_and_categorical_branch(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 10})

    performance = analyzer.train_model(
        X,
        y,
        feature_names=feature_names,
        lightgbm_params={"n_estimators": 15, "num_leaves": 15},
        categorical_features=[],
        cv_folds=3,
    )

    assert performance.n_estimators_actual is not None
    assert analyzer.get_model_params()["n_estimators"] == 15
    assert analyzer.get_native_model() is not None


def test_time_series_split_invalid_branches():
    analyzer = LightGBMAnalyzer(params={"n_estimators": 5})
    X = np.random.randn(2, 2)
    y = np.array([0, 1])

    with pytest.raises(ValueError, match="eval_size 必須 > 0"):
        analyzer._time_series_split(X, y, eval_size=0, timestamps=None)
    with pytest.raises(ValueError, match="eval_size 必須 < 1"):
        analyzer._time_series_split(X, y, eval_size=1, timestamps=None)
    with pytest.raises(ValueError, match="時間序列切分比例不合理"):
        analyzer._time_series_split(X, y, eval_size=0.99, timestamps=None)


def test_validate_model_time_series_with_timestamps(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 10})
    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    result = analyzer.validate_model(
        X,
        y,
        cv_folds=3,
        time_series_split=True,
        timestamps=list(range(len(X))),
        purge_gap=1,
        embargo_pct=0.0,
    )
    assert 0 <= result.cv_auc_mean <= 1


def test_validate_oot_error_and_severe_branch(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 10})

    with pytest.raises(ValueError):
        analyzer.validate_oot(X, y)

    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    with pytest.raises(ValueError):
        analyzer.validate_oot(X.iloc[:0], y[:0], cv_auc_mean=0.8)
    with pytest.raises(ValueError):
        analyzer.validate_oot(X.iloc[:10], y[:9], cv_auc_mean=0.8)

    severe = analyzer.validate_oot(X.iloc[:60], y[:60], cv_auc_mean=0.99)
    assert severe.gap_status in {"warning", "severe", "good"}


def test_feature_importance_invalid_method_and_length_mismatch(trained_lightgbm):
    with pytest.raises(ValueError):
        trained_lightgbm.calculate_feature_importance(trained_lightgbm.feature_names or [], method="invalid")
    with pytest.raises(ValueError):
        trained_lightgbm.calculate_feature_importance(["f0"], method="gain")


def test_predict_related_error_branches(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 10})

    with pytest.raises(ValueError):
        analyzer.get_predictions(X)
    with pytest.raises(ValueError):
        analyzer.calculate_precision_at_k(X, y)
    with pytest.raises(ValueError):
        analyzer.calculate_pr_metrics(X, y)

    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    with pytest.raises(ValueError):
        analyzer.get_predictions(X.iloc[:0])
    with pytest.raises(ValueError):
        analyzer.calculate_precision_at_k(X.iloc[:0], y[:0])


def test_explain_single_case_without_feature_names_branch(synthetic_training_data):
    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 10})
    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    analyzer.feature_names = None
    with pytest.raises(ValueError, match="特徵名稱尚未設定"):
        analyzer.explain_single_case(X.iloc[0])


def test_save_load_format_error_branches(trained_lightgbm, tmp_path):
    wrong_suffix = tmp_path / "model.bin"
    with pytest.raises(ValueError, match=".pkl"):
        trained_lightgbm.save_model(str(wrong_suffix))

    payload_path = Path("data_cache/models/lightgbm_bad_payload.pkl")
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    loader = LightGBMAnalyzer()

    with open(payload_path, "wb") as file:
        import pickle

        pickle.dump(["not", "dict"], file)
    with pytest.raises(ValueError, match="模型檔案格式錯誤"):
        loader.load_model(str(payload_path))

    with open(payload_path, "wb") as file:
        import pickle

        pickle.dump({"model_type": "lightgbm", "model": None}, file)
    with pytest.raises(ValueError, match="模型檔案格式錯誤"):
        loader.load_model(str(payload_path))

    with open(payload_path, "wb") as file:
        pickle.dump({"model_type": "xgboost", "model": object()}, file)
    with pytest.raises(ValueError, match="模型類型不匹配"):
        loader.load_model(str(payload_path))

    if payload_path.exists():
        payload_path.unlink()
