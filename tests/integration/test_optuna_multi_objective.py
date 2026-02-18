from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
import shutil

import pandas as pd
import pytest

from api.services.optimization_output_service import OptimizationOutputService
from momentum.Analysis.pareto_analyzer import ParetoAnalyzer
from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective
from momentum.factories import create_backtest_engine, create_optuna_optimizer


def _build_multi_objective(mock_prices, mock_predicted_proba, mock_atr) -> StrategyBacktestObjective:
    return StrategyBacktestObjective(
        backtest_engine=create_backtest_engine(),
        prices=mock_prices,
        predicted_proba=mock_predicted_proba,
        atr_values=mock_atr,
        target_metric="sharpe_ratio",
        constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 0},
        multi_objective=True,
    )


def _make_optimizer(objective, tmp_path, n_trials: int = 8):
    return create_optuna_optimizer(
        objective=objective,
        study_name=f"phase46_multi_{uuid4().hex}",
        storage=f"sqlite:///{tmp_path / 'multi_optuna.db'}",
        sampler_type="NSGA-II",
        n_trials=n_trials,
        n_jobs=1,
        timeout=120,
        enable_progress=False,
        use_multi_objective=True,
    )


def _build_task_info(result) -> SimpleNamespace:
    return SimpleNamespace(
        status=SimpleNamespace(value="completed"),
        study_name="phase4_multi_objective",
        created_at=pd.Timestamp("2026-01-01T00:00:00Z"),
        started_at=pd.Timestamp("2026-01-01T00:00:01Z"),
        completed_at=pd.Timestamp("2026-01-01T00:00:02Z"),
        progress=SimpleNamespace(best_value=result.best_value),
        config={"objective_config": {"constraints": {}}},
        result=SimpleNamespace(
            best_trial_number=result.best_trial_number,
            best_value=result.best_value,
            best_params=result.best_params,
            metrics={"sharpe_ratio": result.best_value},
            parameter_importance={"entry_threshold": 0.2},
        ),
    )


@pytest.mark.asyncio
async def test_multi_objective_optimization_end_to_end(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_multi_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_optimizer(objective, tmp_path, n_trials=8)
    result = await optimizer.optimize()

    assert result is not None
    assert result.study_direction == "MULTI_OBJECTIVE"
    assert "entry_threshold" in result.best_params


@pytest.mark.asyncio
async def test_multi_objective_has_pareto_trials(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_multi_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_optimizer(objective, tmp_path, n_trials=8)
    await optimizer.optimize()

    assert optimizer.study is not None
    assert len(optimizer.study.best_trials) >= 1
    assert all(len(trial.values) == 2 for trial in optimizer.study.best_trials)


@pytest.mark.asyncio
async def test_multi_objective_knee_point_recommendation(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_multi_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_optimizer(objective, tmp_path, n_trials=10)
    await optimizer.optimize()

    complete_trials = [trial for trial in optimizer.study.trials if trial.state.name == "COMPLETE"]
    trials_df = pd.DataFrame(
        [
            {
                "number": trial.number,
                "params": trial.params,
                "values": list(trial.values or []),
            }
            for trial in complete_trials
        ]
    )

    analysis = ParetoAnalyzer().analyze_pareto_front(trials_df, n_recommendations=3)
    recommendations = ParetoAnalyzer().get_recommended_params(analysis)

    assert len(analysis["pareto_solutions"]) >= 1
    assert len(recommendations) >= 1


@pytest.mark.asyncio
async def test_multi_objective_output_contains_trials(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_multi_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_optimizer(objective, tmp_path, n_trials=6)
    result = await optimizer.optimize()

    service = OptimizationOutputService()
    task_id = f"multi_{uuid4().hex}"
    artifacts = service.generate_outputs(
        task_type="execution",
        task_id=task_id,
        task_info=_build_task_info(result),
        optimizer=optimizer,
    )

    assert artifacts["summary_json"].exists()
    assert artifacts["trials_csv"].exists()
    shutil.rmtree(artifacts["output_dir"], ignore_errors=True)


@pytest.mark.asyncio
async def test_multi_objective_trials_have_two_values(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_multi_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_optimizer(objective, tmp_path, n_trials=7)
    await optimizer.optimize()

    complete_trials = [trial for trial in optimizer.study.trials if trial.state.name == "COMPLETE"]
    assert len(complete_trials) >= 1
    assert all(trial.values is not None and len(trial.values) == 2 for trial in complete_trials)
