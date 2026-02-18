"""Phase 4.2.4 tests for enhanced ModelHyperparamObjective."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import optuna
import pandas as pd
import pytest

from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective


class StubTrainer:
    def __init__(self, perf=None, error: Exception | None = None):
        self.perf = perf
        self.error = error
        self.last_kwargs = None

    def train_model(self, features, labels, feature_names, **kwargs):
        self.last_kwargs = kwargs
        if self.error:
            raise self.error
        if self.perf is not None:
            return self.perf
        return SimpleNamespace(train_auc_mean=0.78, cv_auc_mean=0.72)


def make_objective(**kwargs):
    X = pd.DataFrame(np.random.randn(200, 6), columns=[f"f{i}" for i in range(6)])
    y = np.random.randint(0, 2, size=200)
    base = dict(
        trainer=StubTrainer(),
        features=X,
        labels=y,
        feature_names=X.columns.tolist(),
        engine="lightgbm",
        cv_folds=5,
        max_train_val_gap=0.2,
    )
    base.update(kwargs)
    return ModelHyperparamObjective(**base)


def make_lightgbm_trial() -> optuna.trial.FixedTrial:
    return optuna.trial.FixedTrial(
        {
            "num_leaves": 31,
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_samples": 20,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "min_gain_to_split": 0.01,
        }
    )


def test_evaluate_returns_auc():
    objective = make_objective()
    trial = make_lightgbm_trial()
    params = objective.create_search_space(trial)
    score = objective.evaluate(params)
    assert isinstance(score, float)
    assert score > 0


def test_overfitting_detection_pruned():
    trainer = StubTrainer(perf=SimpleNamespace(train_auc_mean=0.95, cv_auc_mean=0.70))
    objective = make_objective(trainer=trainer, max_train_val_gap=0.1)
    trial = make_lightgbm_trial()
    params = objective.create_search_space(trial)
    with pytest.raises(optuna.TrialPruned):
        objective.evaluate(params)


def test_search_space_min_gt_max_error():
    objective = make_objective(
        search_space_override={
            "learning_rate": {"type": "float", "low": 0.2, "high": 0.1},
        }
    )
    with pytest.raises(ValueError):
        objective.create_search_space(optuna.trial.FixedTrial({"learning_rate": 0.1}))


def test_model_training_failure_fatal():
    trainer = StubTrainer(error=RuntimeError("train failed"))
    objective = make_objective(trainer=trainer)
    trial = make_lightgbm_trial()
    params = objective.create_search_space(trial)
    with pytest.raises(RuntimeError, match="FATAL"):
        objective.evaluate(params)


def test_auc_below_random():
    trainer = StubTrainer(perf=SimpleNamespace(train_auc_mean=0.52, cv_auc_mean=0.49))
    objective = make_objective(trainer=trainer, max_train_val_gap=0.2)
    trial = make_lightgbm_trial()
    params = objective.create_search_space(trial)
    score = objective.evaluate(params)
    assert score < 0.5


def test_zero_features_error():
    X = pd.DataFrame(index=range(120))
    y = np.random.randint(0, 2, size=120)
    with pytest.raises(ValueError):
        ModelHyperparamObjective(
            trainer=StubTrainer(),
            features=X,
            labels=y,
            feature_names=[],
            engine="lightgbm",
        )


def test_small_training_set_warning(caplog):
    X = pd.DataFrame(np.random.randn(50, 3), columns=["a", "b", "c"])
    y = np.random.randint(0, 2, size=50)
    ModelHyperparamObjective(
        trainer=StubTrainer(),
        features=X,
        labels=y,
        feature_names=X.columns.tolist(),
        engine="lightgbm",
    )
    assert any("訓練樣本數過少" in rec.message for rec in caplog.records)


def test_invalid_model_type():
    X = pd.DataFrame(np.random.randn(120, 3), columns=["a", "b", "c"])
    y = np.random.randint(0, 2, size=120)
    with pytest.raises(ValueError):
        ModelHyperparamObjective(
            trainer=StubTrainer(),
            features=X,
            labels=y,
            feature_names=X.columns.tolist(),
            engine="invalid",
        )


def test_lightgbm_search_space_ranges():
    objective = make_objective(engine="lightgbm")
    params = objective.create_search_space(make_lightgbm_trial())
    assert 0.005 <= params["learning_rate"] <= 0.2


def test_xgboost_search_space_ranges():
    X = pd.DataFrame(np.random.randn(200, 6), columns=[f"f{i}" for i in range(6)])
    y = np.random.randint(0, 2, size=200)
    objective = ModelHyperparamObjective(
        trainer=StubTrainer(),
        features=X,
        labels=y,
        feature_names=X.columns.tolist(),
        engine="xgboost",
        max_train_val_gap=0.2,
    )
    trial = optuna.trial.FixedTrial(
        {
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5.0,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "max_delta_step": 1,
        }
    )
    params = objective.create_search_space(trial)
    assert 1 <= params["max_depth"] <= 12


def test_trial_user_attrs_recorded():
    objective = make_objective()
    trial = make_lightgbm_trial()
    params = objective.create_search_space(trial)
    objective.evaluate(params)
    assert "train_auc" in trial.user_attrs
    assert "val_auc" in trial.user_attrs
    assert "train_val_gap" in trial.user_attrs


def test_cv_folds_parameter():
    trainer = StubTrainer()
    objective = make_objective(trainer=trainer, cv_folds=7)
    params = objective.create_search_space(make_lightgbm_trial())
    objective.evaluate(params)
    assert trainer.last_kwargs["cv_folds"] == 7


def test_custom_train_kwargs():
    trainer = StubTrainer()
    objective = make_objective(trainer=trainer, train_kwargs={"early_stopping_rounds": 20})
    params = objective.create_search_space(make_lightgbm_trial())
    objective.evaluate(params)
    assert trainer.last_kwargs["early_stopping_rounds"] == 20


def test_name_property():
    objective = make_objective()
    assert objective.name == "model_hyperparam"


def test_direction_property():
    objective = make_objective()
    assert objective.direction == "maximize"


def test_directions_property_none_and_pruning_callback():
    objective = make_objective()
    assert objective.directions is None
    assert objective.get_pruning_callback(None) is None


def test_numpy_features_path_and_small_sample_warning(caplog):
    X = np.random.randn(80, 4)
    y = np.random.randint(0, 2, size=80)
    objective = ModelHyperparamObjective(
        trainer=StubTrainer(),
        features=X,
        labels=y,
        feature_names=["a", "b", "c", "d"],
        engine="lightgbm",
    )
    assert objective is not None
    assert any("訓練樣本數過少" in rec.message for rec in caplog.records)


def test_numpy_features_zero_columns_error():
    X = np.random.randn(100)
    y = np.random.randint(0, 2, size=100)
    with pytest.raises(ValueError, match="features"):
        ModelHyperparamObjective(
            trainer=StubTrainer(),
            features=X,
            labels=y,
            feature_names=["a"],
            engine="lightgbm",
        )


def test_empty_labels_error():
    X = pd.DataFrame(np.random.randn(120, 3), columns=["a", "b", "c"])
    with pytest.raises(ValueError, match="labels"):
        ModelHyperparamObjective(
            trainer=StubTrainer(),
            features=X,
            labels=np.array([]),
            feature_names=X.columns.tolist(),
            engine="lightgbm",
        )


def test_create_search_space_unsupported_type_error():
    objective = make_objective(
        search_space_override={
            "weird_param": {"type": "unknown", "low": 1, "high": 2},
        }
    )
    with pytest.raises(ValueError, match="不支援的參數型別"):
        objective.create_search_space(optuna.trial.FixedTrial({"weird_param": 1}))


def test_create_search_space_missing_low_high_error():
    objective = make_objective(
        search_space_override={
            "learning_rate": {"type": "float", "low": 0.1},
        }
    )
    with pytest.raises(ValueError, match="缺少 low/high"):
        objective.create_search_space(optuna.trial.FixedTrial({"learning_rate": 0.1}))


def test_create_search_space_empty_categorical_choices_error():
    objective = make_objective(
        search_space_override={
            "boosting_type": {"type": "categorical", "choices": []},
        }
    )
    with pytest.raises(ValueError, match="choices"):
        objective.create_search_space(optuna.trial.FixedTrial({"boosting_type": "gbdt"}))


def test_create_search_space_categorical_branch_success():
    objective = make_objective(
        search_space_override={
            "boosting_type": {"type": "categorical", "choices": ["gbdt", "dart"]},
        }
    )
    trial = optuna.trial.FixedTrial({"boosting_type": "dart"})
    params = objective.create_search_space(trial)
    assert params["boosting_type"] == "dart"


def test_lightgbm_learning_rate_lower_bound_error():
    objective = make_objective(
        search_space_override={
            "learning_rate": {"type": "float", "low": 0.001, "high": 0.2},
        }
    )
    with pytest.raises(ValueError, match="learning_rate"):
        objective.create_search_space(optuna.trial.FixedTrial({"learning_rate": 0.01}))


def test_lightgbm_num_leaves_upper_bound_error():
    objective = make_objective(
        search_space_override={
            "num_leaves": {"type": "int", "low": 10, "high": 200},
        }
    )
    with pytest.raises(ValueError, match="num_leaves"):
        objective.create_search_space(optuna.trial.FixedTrial({"num_leaves": 31}))


def test_xgboost_max_depth_upper_bound_error():
    X = pd.DataFrame(np.random.randn(200, 3), columns=["a", "b", "c"])
    y = np.random.randint(0, 2, size=200)
    objective = ModelHyperparamObjective(
        trainer=StubTrainer(),
        features=X,
        labels=y,
        feature_names=X.columns.tolist(),
        engine="xgboost",
        search_space_override={
            "max_depth": {"type": "int", "low": 1, "high": 20},
        },
    )
    with pytest.raises(ValueError, match="max_depth"):
        objective.create_search_space(optuna.trial.FixedTrial({"max_depth": 6}))


def test_evaluate_xgboost_path():
    X = pd.DataFrame(np.random.randn(200, 3), columns=["a", "b", "c"])
    y = np.random.randint(0, 2, size=200)
    trainer = StubTrainer(perf=SimpleNamespace(train_auc_mean=0.77, cv_auc_mean=0.74))
    objective = ModelHyperparamObjective(
        trainer=trainer,
        features=X,
        labels=y,
        feature_names=X.columns.tolist(),
        engine="xgboost",
        max_train_val_gap=0.2,
    )
    trial = optuna.trial.FixedTrial(
        {
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3.0,
            "gamma": 0.2,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "max_delta_step": 1,
        }
    )
    params = objective.create_search_space(trial)
    score = objective.evaluate(params)
    assert score == pytest.approx(0.74)
    assert "xgboost_params" in trainer.last_kwargs


def test_extract_metric_default_and_raise():
    objective = make_objective()
    perf = SimpleNamespace()
    assert objective._extract_metric(perf, ["nope"], default=0.66) == pytest.approx(0.66)
    with pytest.raises(ValueError):
        objective._extract_metric(perf, ["still_missing"])


def test_set_trial_user_attrs_without_trial_no_error():
    objective = make_objective()
    objective._current_trial = None
    objective._set_trial_user_attrs(0.7, 0.6, 0.1)


def test_validate_search_space_non_dict_rule_is_ignored():
    objective = make_objective()
    objective._validate_search_space({"foo": "bar"})


def test_evaluate_engine_else_branch_raises_value_error():
    objective = make_objective()
    objective.engine = "invalid"
    with pytest.raises(ValueError, match="不支援的引擎"):
        objective.evaluate({})


def test_get_search_space_schema_for_frontend():
    objective = make_objective()
    schema = objective.get_search_space_schema()
    assert isinstance(schema, dict)
    assert "learning_rate" in schema
