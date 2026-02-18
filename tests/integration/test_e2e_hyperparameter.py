from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
import shutil

import numpy as np
import pandas as pd
import pytest

from api.services.optimization_output_service import OptimizationOutputService
from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective
from momentum.factories import create_optuna_optimizer


class DeterministicTrainer:
    def train_model(self, features, labels, feature_names, **kwargs):
        params = kwargs.get("lightgbm_params") or kwargs.get("xgboost_params") or {}
        lr = float(params.get("learning_rate", 0.05))
        depth = float(params.get("max_depth", 6))
        val_auc = min(0.90, 0.60 + lr * 1.5 + depth * 0.01)
        train_auc = min(0.95, val_auc + 0.03)
        return SimpleNamespace(train_auc_mean=train_auc, cv_auc_mean=val_auc)


def _make_dataset(n_rows: int = 220, n_features: int = 8):
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(n_rows, n_features)), columns=[f"f_{i}" for i in range(n_features)])
    y = (X["f_0"] + X["f_1"] * 0.5 > 0).astype(int).to_numpy()
    return X, y, X.columns.tolist()


def _make_optimizer(objective, tmp_path, n_trials: int = 8):
    return create_optuna_optimizer(
        objective=objective,
        study_name=f"phase46_hyper_{uuid4().hex}",
        storage=f"sqlite:///{tmp_path / 'hyper_optuna.db'}",
        sampler_type="Random",
        n_trials=n_trials,
        n_jobs=1,
        timeout=120,
        enable_progress=False,
    )


def _build_task_info(result) -> SimpleNamespace:
    return SimpleNamespace(
        status=SimpleNamespace(value="completed"),
        study_name="phase4_hyper_e2e",
        created_at=pd.Timestamp("2026-01-01T00:00:00Z"),
        started_at=pd.Timestamp("2026-01-01T00:00:01Z"),
        completed_at=pd.Timestamp("2026-01-01T00:00:02Z"),
        progress=SimpleNamespace(best_value=result.best_value),
        config={"objective_config": {"constraints": {"max_train_val_gap": 0.1}}},
        result=SimpleNamespace(
            best_trial_number=result.best_trial_number,
            best_value=result.best_value,
            best_params=result.best_params,
            metrics={"val_auc": result.best_value, "train_val_gap": 0.03},
            parameter_importance={"learning_rate": 0.3, "max_depth": 0.2},
        ),
    )


@pytest.mark.asyncio
async def test_hyperparameter_optimization_end_to_end_lightgbm(tmp_path):
    X, y, feature_names = _make_dataset()
    objective = ModelHyperparamObjective(
        trainer=DeterministicTrainer(),
        features=X,
        labels=y,
        feature_names=feature_names,
        engine="lightgbm",
        max_train_val_gap=0.2,
    )

    optimizer = _make_optimizer(objective, tmp_path, n_trials=8)
    result = await optimizer.optimize()

    assert result is not None
    assert result.best_value >= 0.6
    assert "learning_rate" in result.best_params


@pytest.mark.asyncio
async def test_hyperparameter_optimization_end_to_end_xgboost(tmp_path):
    X, y, feature_names = _make_dataset()
    objective = ModelHyperparamObjective(
        trainer=DeterministicTrainer(),
        features=X,
        labels=y,
        feature_names=feature_names,
        engine="xgboost",
        max_train_val_gap=0.2,
    )

    optimizer = _make_optimizer(objective, tmp_path, n_trials=6)
    result = await optimizer.optimize()

    assert result.best_value >= 0.6
    assert "max_depth" in result.best_params


@pytest.mark.asyncio
async def test_hyperparameter_output_generates_summary_and_trials(tmp_path):
    X, y, feature_names = _make_dataset()
    objective = ModelHyperparamObjective(
        trainer=DeterministicTrainer(),
        features=X,
        labels=y,
        feature_names=feature_names,
        engine="lightgbm",
        max_train_val_gap=0.2,
    )

    optimizer = _make_optimizer(objective, tmp_path, n_trials=5)
    result = await optimizer.optimize()

    service = OptimizationOutputService()
    task_id = f"hyper_{uuid4().hex}"
    artifacts = service.generate_outputs(
        task_type="hyperparameter",
        task_id=task_id,
        task_info=_build_task_info(result),
        optimizer=optimizer,
    )

    assert artifacts["summary_json"].exists()
    assert artifacts["trials_csv"].exists()
    assert artifacts["ai_report_md"].exists()
    shutil.rmtree(artifacts["output_dir"], ignore_errors=True)


@pytest.mark.asyncio
async def test_hyperparameter_summary_contains_best_trial(tmp_path):
    X, y, feature_names = _make_dataset()
    objective = ModelHyperparamObjective(
        trainer=DeterministicTrainer(),
        features=X,
        labels=y,
        feature_names=feature_names,
        engine="lightgbm",
        max_train_val_gap=0.2,
    )

    optimizer = _make_optimizer(objective, tmp_path, n_trials=5)
    result = await optimizer.optimize()

    service = OptimizationOutputService()
    task_id = f"hyper_{uuid4().hex}"
    service.generate_outputs(
        task_type="hyperparameter",
        task_id=task_id,
        task_info=_build_task_info(result),
        optimizer=optimizer,
    )

    summary = service.load_summary("hyperparameter", task_id)
    assert summary["best_trial"]["trial_number"] is not None
    assert isinstance(summary["best_trial"]["params"], dict)
    shutil.rmtree(service.base_output_dir / "hyperparameter" / task_id, ignore_errors=True)


@pytest.mark.asyncio
async def test_hyperparameter_trials_csv_has_completed_rows(tmp_path):
    X, y, feature_names = _make_dataset()
    objective = ModelHyperparamObjective(
        trainer=DeterministicTrainer(),
        features=X,
        labels=y,
        feature_names=feature_names,
        engine="lightgbm",
        max_train_val_gap=0.2,
    )

    optimizer = _make_optimizer(objective, tmp_path, n_trials=5)
    result = await optimizer.optimize()

    service = OptimizationOutputService()
    task_id = f"hyper_{uuid4().hex}"
    artifacts = service.generate_outputs(
        task_type="hyperparameter",
        task_id=task_id,
        task_info=_build_task_info(result),
        optimizer=optimizer,
    )

    trials_df = pd.read_csv(artifacts["trials_csv"])
    assert len(trials_df) >= 1
    assert "state" in trials_df.columns
    shutil.rmtree(artifacts["output_dir"], ignore_errors=True)
