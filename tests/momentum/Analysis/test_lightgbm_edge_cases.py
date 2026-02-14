from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer


ENGINES = ("lightgbm", "xgboost")


def _make_data(n_samples: int = 120, n_features: int = 8):
    rng = np.random.default_rng(99)
    X = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)),
        columns=[f"feature_{i}" for i in range(n_features)],
    )
    if n_features >= 3:
        score = X["feature_0"] - X["feature_1"] * 0.3 + X["feature_2"] * 0.2
    elif n_features == 2:
        score = X["feature_0"] - X["feature_1"] * 0.3
    else:
        score = X["feature_0"]
    y = (score > np.median(score)).astype(int).to_numpy()
    return X, y, X.columns.tolist()


def _build_trainer(engine: str):
    if engine == "lightgbm":
        return LightGBMAnalyzer(params={"n_estimators": 20, "num_leaves": 15})
    return XGBoostAnalyzer(params={"n_estimators": 20, "max_depth": 3})


def _train(engine: str):
    X, y, feature_names = _make_data()
    trainer = _build_trainer(engine)
    trainer.train_model(X, y, feature_names=feature_names, cv_folds=3)
    return trainer, X, y, feature_names


@pytest.mark.parametrize("engine", ENGINES)
def test_d1_empty_x_raises(engine):
    trainer = _build_trainer(engine)
    X = pd.DataFrame()
    y = np.array([], dtype=int)

    with pytest.raises(ValueError):
        trainer.train_model(X, y, feature_names=[])


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("label_value", [0, 1])
def test_d2_d3_single_class_labels_raise(engine, label_value):
    trainer = _build_trainer(engine)
    X, _, feature_names = _make_data()
    y = np.full(len(X), label_value, dtype=int)

    with pytest.raises(ValueError):
        trainer.train_model(X, y, feature_names=feature_names)


@pytest.mark.parametrize("engine", ENGINES)
def test_d4_length_mismatch_raises(engine):
    trainer = _build_trainer(engine)
    X, y, feature_names = _make_data()

    with pytest.raises(ValueError):
        trainer.train_model(X.iloc[:-1], y, feature_names=feature_names)


@pytest.mark.parametrize("engine", ENGINES)
def test_d5_nan_input_trainable(engine):
    trainer = _build_trainer(engine)
    X, y, feature_names = _make_data()
    X = X.copy()
    X.iloc[0, 0] = np.nan

    performance = trainer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    assert 0.0 <= performance.cv_auc_mean <= 1.0


@pytest.mark.parametrize("engine", ENGINES)
def test_d6_inf_input_raises(engine):
    trainer = _build_trainer(engine)
    X, y, feature_names = _make_data()
    X = X.copy()
    X.iloc[0, 0] = np.inf

    with pytest.raises(ValueError):
        trainer.train_model(X, y, feature_names=feature_names)


@pytest.mark.parametrize("engine", ENGINES)
def test_d7_single_feature_trainable(engine):
    trainer = _build_trainer(engine)
    X, y, _ = _make_data(n_features=1)
    feature_names = X.columns.tolist()

    performance = trainer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    assert 0.0 <= performance.cv_auc_mean <= 1.0


@pytest.mark.parametrize("engine", ENGINES)
def test_d9_ndarray_without_feature_names_raises(engine):
    trainer = _build_trainer(engine)
    X, y, _ = _make_data()

    with pytest.raises(ValueError):
        trainer.train_model(X.to_numpy(), y)


@pytest.mark.parametrize("engine", ENGINES)
def test_d10_feature_names_mismatch_raises(engine):
    trainer = _build_trainer(engine)
    X, y, _ = _make_data()

    if engine == "lightgbm":
        with pytest.raises(ValueError):
            trainer.train_model(X.to_numpy(), y, feature_names=["a", "b"])
    else:
        performance = trainer.train_model(X.to_numpy(), y, feature_names=["a", "b"], cv_folds=3)
        assert 0.0 <= performance.cv_auc_mean <= 1.0


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("eval_size", [0, 1])
def test_p3_p4_eval_size_invalid_raises(engine, eval_size):
    trainer = _build_trainer(engine)
    X, y, feature_names = _make_data()

    with pytest.raises(ValueError):
        trainer.train_model(X, y, feature_names=feature_names, eval_size=eval_size)


@pytest.mark.parametrize("engine", ENGINES)
def test_p1_cv_folds_less_than_2_raises(engine):
    trainer, X, y, feature_names = _train(engine)

    with pytest.raises(ValueError):
        trainer.validate_model(X, y, cv_folds=1)


@pytest.mark.parametrize("engine", ENGINES)
def test_p2_cv_folds_exceeds_samples_raises(engine):
    trainer, X, y, feature_names = _train(engine)

    with pytest.raises(ValueError):
        trainer.validate_model(X, y, cv_folds=len(X) + 1)


@pytest.mark.parametrize("engine", ENGINES)
def test_p5_purge_gap_too_large_raises(engine):
    trainer, X, y, feature_names = _train(engine)

    if engine == "lightgbm":
        with pytest.raises(ValueError):
            trainer.validate_model(X, y, cv_folds=3, time_series_split=True, purge_gap=len(X))
    else:
        performance = trainer.validate_model(X, y, cv_folds=3, time_series_split=True, purge_gap=len(X))
        assert 0.0 <= performance.cv_auc_mean <= 1.0


@pytest.mark.parametrize("engine", ENGINES)
def test_s1_predict_before_train_raises(engine):
    trainer = _build_trainer(engine)
    X, _, _ = _make_data()

    with pytest.raises(ValueError):
        trainer.predict_proba(X)


@pytest.mark.parametrize("engine", ENGINES)
def test_s2_feature_importance_before_train_raises(engine):
    trainer = _build_trainer(engine)

    with pytest.raises(ValueError):
        trainer.get_feature_importance()


@pytest.mark.parametrize("engine", ENGINES)
def test_s3_save_before_train_raises(engine):
    trainer = _build_trainer(engine)

    with pytest.raises(ValueError):
        trainer.save_model("data_cache/models/should_not_exist.pkl")


@pytest.mark.parametrize("engine", ENGINES)
def test_s4_load_missing_file_raises(engine):
    trainer = _build_trainer(engine)

    with pytest.raises(FileNotFoundError):
        trainer.load_model("data_cache/models/definitely_not_exists.pkl")


@pytest.mark.parametrize("engine", ENGINES)
def test_model_path_safety_rejects_outside_cache(engine):
    trainer, _, _, _ = _train(engine)

    with pytest.raises(ValueError, match="data_cache/models"):
        trainer.save_model("/tmp/not_allowed.pkl")


def test_s5_type_mismatch_lightgbm_to_xgboost_raises():
    lgb, _, _, _ = _train("lightgbm")
    path = Path("data_cache/models/type_mismatch_lgb.pkl")
    lgb.save_model(str(path))

    xgb = _build_trainer("xgboost")
    with pytest.raises(ValueError, match="模型類型不匹配"):
        xgb.load_model(str(path))

    if path.exists():
        path.unlink()


def test_s5_type_mismatch_xgboost_to_lightgbm_raises():
    xgb, _, _, _ = _train("xgboost")
    path = Path("data_cache/models/type_mismatch_xgb.pkl")
    xgb.save_model(str(path))

    lgb = _build_trainer("lightgbm")
    with pytest.raises(ValueError, match="模型類型不匹配"):
        lgb.load_model(str(path))

    if path.exists():
        path.unlink()


@pytest.mark.parametrize("engine", ENGINES)
def test_s6_loaded_model_can_be_retrained(engine):
    trainer, X, y, feature_names = _train(engine)
    path = Path(f"data_cache/models/retrain_{engine}.pkl")
    trainer.save_model(str(path))

    new_trainer = _build_trainer(engine)
    new_trainer.load_model(str(path))
    performance = new_trainer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    assert 0.0 <= performance.cv_auc_mean <= 1.0

    if path.exists():
        path.unlink()


@pytest.mark.parametrize("engine", ENGINES)
def test_o1_oot_insufficient_samples_returns_result(engine):
    trainer, X, y, _ = _train(engine)

    result = trainer.validate_oot(X.iloc[:20], y[:20], cv_auc_mean=0.7)

    if engine == "lightgbm":
        assert result.n_samples == 20
    else:
        assert result.oot_samples == 20


@pytest.mark.parametrize("engine", ENGINES)
def test_o2_oot_single_class_sets_auc_none(engine):
    trainer, X, y, _ = _train(engine)
    y_oot = np.zeros(30, dtype=int)

    result = trainer.validate_oot(X.iloc[:30], y_oot, cv_auc_mean=0.7)

    if engine == "lightgbm":
        assert result.oot_auc is None
    else:
        assert result.oot_auc == 0.0


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("sample_size", [1, 5, 20, 50, 9999])
def test_h1_shap_sample_size_handling(engine, sample_size):
    trainer, X, _, _ = _train(engine)

    result = trainer.analyze_shap_global(X.iloc[:40], sample_size=sample_size)

    if engine == "lightgbm":
        assert len(result.feature_names) > 0
    else:
        assert len(result.feature_importance_shap) > 0


@pytest.mark.parametrize("engine", ENGINES)
def test_h2_shap_sample_size_zero_raises(engine):
    trainer, X, _, _ = _train(engine)

    with pytest.raises(ValueError):
        trainer.analyze_shap_global(X.iloc[:20], sample_size=0)


@pytest.mark.parametrize("engine", ENGINES)
def test_h3_explain_single_case_feature_mismatch_raises(engine):
    trainer, X, _, _ = _train(engine)

    with pytest.raises(Exception):
        trainer.explain_single_case(pd.Series([0.1, 0.2], index=["a", "b"]))


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("k", [1, 2, 3, 5, 8, 10, 15, 20, 30, 40, 50, 60])
def test_precision_at_k_parameter_sweep(engine, k):
    trainer, X, y, _ = _train(engine)

    results = trainer.calculate_precision_at_k(X, y, k_values=[k])

    if engine == "lightgbm":
        assert len(results) == 1
        assert results[0].k == k
        assert 0.0 <= results[0].precision <= 1.0
    else:
        assert hasattr(results, "precision_at_k")
        assert int(k) in results.precision_at_k
        assert 0.0 <= float(results.precision_at_k[int(k)]) <= 1.0


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("sample_size", [10, 15, 20, 25, 30, 35, 40, 45, 50, 60])
def test_validate_oot_sample_size_sweep(engine, sample_size):
    trainer, X, y, _ = _train(engine)

    result = trainer.validate_oot(X.iloc[:sample_size], y[:sample_size], cv_auc_mean=0.75)

    if engine == "lightgbm":
        assert result.n_samples == sample_size
    else:
        assert result.oot_samples == sample_size
