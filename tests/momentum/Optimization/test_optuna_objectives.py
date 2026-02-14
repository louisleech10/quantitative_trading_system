"""Task 3.9/3.10 objective tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple, Union
import tempfile

import numpy as np
import optuna
import pandas as pd
import pytest

from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective
from momentum.Optimization.objectives.signal_density import SignalDensityObjective
from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective
from momentum.Optimization.optuna_optimizer import OptunaOptimizer


class DummyTrainer:
    def __init__(self):
        self.last_params: Dict[str, Any] = {}

    def train_model(self, features, labels, feature_names, **kwargs):
        params = kwargs.get("lightgbm_params") or kwargs.get("xgboost_params") or {}
        self.last_params = dict(params)
        score = 0.6 + min(float(params.get("learning_rate", 0.01)), 0.2) * 0.1
        return SimpleNamespace(cv_auc_mean=score)


class DummyObjective:
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def direction(self) -> str:
        return "maximize"

    @property
    def directions(self) -> Optional[list[str]]:
        return None

    def create_search_space(self, trial) -> Dict[str, Any]:
        return {"x": trial.suggest_float("x", 0.0, 1.0)}

    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, ...]]:
        x = float(params["x"])
        return 1.0 - (x - 0.4) ** 2

    def get_pruning_callback(self, trial):
        return None


@pytest.mark.asyncio
async def test_optuna_optimizer_pluggable_objective_runs_trials():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        optimizer = OptunaOptimizer(
            study_name="task39_pluggable",
            storage=f"sqlite:///{f.name}",
            objective=DummyObjective(),
            n_trials=5,
            n_jobs=1,
            enable_progress_monitor=False,
        )

        result = await optimizer.optimize()

    assert result.total_trials >= 5
    assert result.best_value > 0


def test_model_hyperparam_objective_search_space_and_evaluate():
    trainer = DummyTrainer()
    X = pd.DataFrame(np.random.randn(40, 6), columns=[f"f{i}" for i in range(6)])
    y = np.random.randint(0, 2, size=40)

    objective = ModelHyperparamObjective(
        trainer=trainer,
        features=X,
        labels=y,
        feature_names=X.columns.tolist(),
        engine="lightgbm",
        cv_folds=3,
    )

    trial = optuna.trial.FixedTrial(
        {
            "num_leaves": 31,
            "max_depth": -1,
            "learning_rate": 0.05,
            "n_estimators": 120,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_samples": 20,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "min_gain_to_split": 0.01,
        }
    )

    params = objective.create_search_space(trial)
    score = objective.evaluate(params)

    assert isinstance(score, float)
    assert score > 0
    assert "learning_rate" in trainer.last_params


def test_strategy_backtest_objective_single_and_multi():
    predictions = np.linspace(0.1, 0.9, 80)
    prices = 100 + np.cumsum(np.random.randn(80) * 0.3)

    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.65,
            "exit_threshold": 0.35,
            "stop_loss": 0.03,
            "take_profit": 0.06,
            "max_holding_bars": 10,
            "position_size": 0.6,
            "cooldown_bars": 1,
            "transaction_cost": 0.001,
            "min_signal_gap": 1,
        }
    )

    single = StrategyBacktestObjective(predictions, prices, multi_objective=False)
    params_single = single.create_search_space(trial)
    value_single = single.evaluate(params_single)
    assert isinstance(value_single, float)

    multi = StrategyBacktestObjective(predictions, prices, multi_objective=True)
    params_multi = multi.create_search_space(trial)
    value_multi = multi.evaluate(params_multi)
    assert isinstance(value_multi, tuple)
    assert len(value_multi) == 2


@pytest.mark.asyncio
async def test_multi_objective_auto_nsga2_sampler():
    predictions = np.linspace(0.1, 0.9, 60)
    prices = 100 + np.cumsum(np.random.randn(60) * 0.2)
    objective = StrategyBacktestObjective(predictions, prices, multi_objective=True)

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        optimizer = OptunaOptimizer(
            study_name="task310_multi",
            storage=f"sqlite:///{f.name}",
            objective=objective,
            sampler_type="TPE",
            n_trials=3,
            enable_progress_monitor=False,
        )
        study = optimizer.create_study()
        result = await optimizer.optimize()

    assert len(study.directions) == 2
    assert result.total_trials >= 3


def test_signal_density_objective_adapter_contract():
    objective = SignalDensityObjective(
        search_space_factory=lambda trial: {"x": trial.suggest_float("x", 0.0, 1.0)},
        evaluator=lambda params: float(params["x"]),
        pruning_callback_factory=lambda trial: None,
        multi_objective=False,
    )

    trial = optuna.trial.FixedTrial({"x": 0.3})
    params = objective.create_search_space(trial)
    score = objective.evaluate(params)

    assert objective.name == "signal_density"
    assert objective.direction == "maximize"
    assert objective.directions is None
    assert params["x"] == 0.3
    assert score == 0.3
