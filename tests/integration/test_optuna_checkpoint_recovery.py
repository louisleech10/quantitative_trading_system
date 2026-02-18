from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import time

import pandas as pd
import pytest

from momentum.Optimization.checkpoint_manager import CheckpointManager
from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective
from momentum.factories import create_backtest_engine, create_optuna_optimizer


def _build_objective(mock_prices, mock_predicted_proba, mock_atr) -> StrategyBacktestObjective:
    return StrategyBacktestObjective(
        backtest_engine=create_backtest_engine(),
        prices=mock_prices,
        predicted_proba=mock_predicted_proba,
        atr_values=mock_atr,
        target_metric="expectancy",
        constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 0},
    )


def _make_optimizer(objective, storage_path: Path, study_name: str, n_trials: int):
    return create_optuna_optimizer(
        objective=objective,
        study_name=study_name,
        storage=f"sqlite:///{storage_path}",
        sampler_type="Random",
        n_trials=n_trials,
        n_jobs=1,
        timeout=120,
        enable_progress=False,
    )


@pytest.mark.asyncio
async def test_checkpoint_recovery_resume_trials(mock_prices, mock_predicted_proba, mock_atr, tmp_path):
    objective = _build_objective(mock_prices, mock_predicted_proba, mock_atr)
    storage_path = tmp_path / "resume_optuna.db"
    study_name = f"phase46_resume_{uuid4().hex}"

    first = _make_optimizer(objective, storage_path, study_name, n_trials=4)
    first_result = await first.optimize()
    assert first_result.total_trials >= 4

    second = _make_optimizer(objective, storage_path, study_name, n_trials=3)
    second_result = await second.optimize()
    assert second_result.total_trials >= first_result.total_trials + 3


@pytest.mark.asyncio
async def test_checkpoint_manager_save_and_load(mock_prices, mock_predicted_proba, mock_atr, tmp_path):
    objective = _build_objective(mock_prices, mock_predicted_proba, mock_atr)
    storage_path = tmp_path / "checkpoint_optuna.db"
    study_name = f"phase46_ckpt_{uuid4().hex}"

    optimizer = _make_optimizer(objective, storage_path, study_name, n_trials=3)
    await optimizer.optimize()

    manager = CheckpointManager(checkpoint_dir=str(tmp_path / "checkpoints"), save_interval=1)
    checkpoint_path = manager.save_checkpoint(
        study=optimizer.study,
        trial_number=len(optimizer.study.trials),
        additional_data={"phase": "4.6.1"},
    )

    loaded = manager.load_checkpoint(checkpoint_path)
    assert loaded is not None
    assert loaded["study_name"] == study_name
    assert loaded["n_trials"] >= 3


def test_checkpoint_manager_latest_checkpoint(tmp_path):
    manager = CheckpointManager(checkpoint_dir=str(tmp_path / "checkpoints"), save_interval=1)
    study_name = f"phase46_latest_{uuid4().hex}"

    manager.save_checkpoint(study_name=study_name, trial_number=1, checkpoint_data={"best_value": 0.1})
    time.sleep(1.1)
    manager.save_checkpoint(study_name=study_name, trial_number=2, checkpoint_data={"best_value": 0.2})

    latest_path = manager.get_latest_checkpoint(study_name)
    assert latest_path is not None

    latest = manager.load_checkpoint(latest_path)
    assert latest["trial_number"] == 2


def test_checkpoint_validate_and_export_csv(tmp_path):
    manager = CheckpointManager(checkpoint_dir=str(tmp_path / "checkpoints"), save_interval=1)
    study_name = f"phase46_validate_{uuid4().hex}"

    df = pd.DataFrame(
        {
            "number": [0, 1],
            "value": [0.12, 0.15],
            "state": ["COMPLETE", "COMPLETE"],
        }
    )

    checkpoint_path = manager.save_checkpoint(
        study_name=study_name,
        trial_number=2,
        checkpoint_data={"trials_dataframe": df},
    )

    assert manager.validate_checkpoint(checkpoint_path)

    csv_path = manager.export_checkpoint_summary(checkpoint_path)
    assert Path(csv_path).exists()


@pytest.mark.asyncio
async def test_checkpoint_load_then_continue_optimization(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_objective(mock_prices, mock_predicted_proba, mock_atr)
    storage_path = tmp_path / "continue_optuna.db"
    study_name = f"phase46_continue_{uuid4().hex}"

    first = _make_optimizer(objective, storage_path, study_name, n_trials=3)
    await first.optimize()

    manager = CheckpointManager(checkpoint_dir=str(tmp_path / "checkpoints"), save_interval=1)
    checkpoint_path = manager.save_checkpoint(
        study=first.study,
        trial_number=len(first.study.trials),
        additional_data={"status": "interrupted"},
    )
    loaded = manager.load_checkpoint(checkpoint_path)
    assert loaded["trial_number"] >= 3

    resumed = _make_optimizer(objective, storage_path, study_name, n_trials=2)
    resumed_result = await resumed.optimize()
    assert resumed_result.total_trials >= loaded["trial_number"] + 2
