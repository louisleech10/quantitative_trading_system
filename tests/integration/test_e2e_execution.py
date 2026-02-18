from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
import shutil

import pandas as pd
import pytest

from api.services.optimization_output_service import OptimizationOutputService
from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective
from momentum.factories import create_backtest_engine, create_optuna_optimizer


def _make_execution_optimizer(objective: StrategyBacktestObjective, tmp_path, n_trials: int = 8):
    return create_optuna_optimizer(
        objective=objective,
        study_name=f"phase46_exec_{uuid4().hex}",
        storage=f"sqlite:///{tmp_path / 'execution_optuna.db'}",
        sampler_type="Random",
        n_trials=n_trials,
        n_jobs=1,
        timeout=120,
        enable_progress=False,
    )


def _build_execution_objective(mock_prices, mock_predicted_proba, mock_atr) -> StrategyBacktestObjective:
    return StrategyBacktestObjective(
        backtest_engine=create_backtest_engine(commission=0.001, slippage=0.0005),
        prices=mock_prices,
        predicted_proba=mock_predicted_proba,
        atr_values=mock_atr,
        target_metric="expectancy",
        constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 0},
        multi_objective=False,
    )


def _build_task_info(result, backtest_result) -> SimpleNamespace:
    return SimpleNamespace(
        status=SimpleNamespace(value="completed"),
        study_name="phase4_execution_e2e",
        created_at=pd.Timestamp("2026-01-01T00:00:00Z"),
        started_at=pd.Timestamp("2026-01-01T00:00:01Z"),
        completed_at=pd.Timestamp("2026-01-01T00:00:02Z"),
        progress=SimpleNamespace(best_value=result.best_value),
        config={
            "objective_config": {
                "constraints": {
                    "max_drawdown": -0.30,
                    "min_win_rate": 0.40,
                    "min_trades": 5,
                }
            }
        },
        result=SimpleNamespace(
            best_trial_number=result.best_trial_number,
            best_value=result.best_value,
            best_params=result.best_params,
            metrics=backtest_result.metrics,
            parameter_importance={"entry_threshold": 0.25, "stop_loss_atr": 0.20},
            backtest_result=backtest_result,
        ),
    )


@pytest.mark.asyncio
async def test_execution_optimization_end_to_end(mock_prices, mock_predicted_proba, mock_atr, tmp_path):
    objective = _build_execution_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_execution_optimizer(objective, tmp_path, n_trials=8)

    result = await optimizer.optimize()

    assert result is not None
    assert 0.5 <= result.best_params["entry_threshold"] <= 0.95
    assert 0.3 <= result.best_params["exit_threshold"] <= 0.6
    assert result.total_trials >= 8


@pytest.mark.asyncio
async def test_execution_output_generates_json_and_csv(mock_prices, mock_predicted_proba, mock_atr, tmp_path):
    objective = _build_execution_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_execution_optimizer(objective, tmp_path, n_trials=6)
    result = await optimizer.optimize()

    engine = create_backtest_engine(commission=0.001, slippage=0.0005)
    backtest_result = engine.run_backtest(
        prices=mock_prices,
        predicted_proba=mock_predicted_proba,
        atr_values=mock_atr,
        strategy_params=result.best_params,
    )

    service = OptimizationOutputService()
    task_id = f"exec_{uuid4().hex}"
    artifacts = service.generate_outputs(
        task_type="execution",
        task_id=task_id,
        task_info=_build_task_info(result, backtest_result),
        optimizer=optimizer,
    )

    assert artifacts["summary_json"].exists()
    assert artifacts["trades_csv"].exists()
    assert artifacts["equity_curve_csv"].exists()
    assert artifacts["trials_csv"].exists()
    shutil.rmtree(artifacts["output_dir"], ignore_errors=True)


@pytest.mark.asyncio
async def test_execution_summary_contains_constraint_satisfaction(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_execution_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_execution_optimizer(objective, tmp_path, n_trials=5)
    result = await optimizer.optimize()

    engine = create_backtest_engine()
    backtest_result = engine.run_backtest(mock_prices, mock_predicted_proba, mock_atr, result.best_params)

    service = OptimizationOutputService()
    task_id = f"exec_{uuid4().hex}"
    service.generate_outputs(
        task_type="execution",
        task_id=task_id,
        task_info=_build_task_info(result, backtest_result),
        optimizer=optimizer,
    )

    summary = service.load_summary("execution", task_id)
    constraints = summary.get("constraint_satisfaction", {})
    assert "max_drawdown" in constraints
    assert "min_win_rate" in constraints
    assert "min_trades" in constraints
    shutil.rmtree(service.base_output_dir / "execution" / task_id, ignore_errors=True)


@pytest.mark.asyncio
async def test_execution_result_contains_backtest_metrics(mock_prices, mock_predicted_proba, mock_atr, tmp_path):
    objective = _build_execution_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_execution_optimizer(objective, tmp_path, n_trials=4)
    result = await optimizer.optimize()

    engine = create_backtest_engine()
    backtest_result = engine.run_backtest(mock_prices, mock_predicted_proba, mock_atr, result.best_params)

    assert len(backtest_result.equity_curve) == len(mock_prices)
    assert "sharpe_ratio" in backtest_result.metrics


@pytest.mark.asyncio
async def test_execution_trials_csv_contains_completed_trials(
    mock_prices,
    mock_predicted_proba,
    mock_atr,
    tmp_path,
):
    objective = _build_execution_objective(mock_prices, mock_predicted_proba, mock_atr)
    optimizer = _make_execution_optimizer(objective, tmp_path, n_trials=5)
    result = await optimizer.optimize()

    engine = create_backtest_engine()
    backtest_result = engine.run_backtest(mock_prices, mock_predicted_proba, mock_atr, result.best_params)

    service = OptimizationOutputService()
    task_id = f"exec_{uuid4().hex}"
    artifacts = service.generate_outputs(
        task_type="execution",
        task_id=task_id,
        task_info=_build_task_info(result, backtest_result),
        optimizer=optimizer,
    )

    trials_df = pd.read_csv(artifacts["trials_csv"])
    assert len(trials_df) >= 1
    assert "trial_number" in trials_df.columns
    shutil.rmtree(artifacts["output_dir"], ignore_errors=True)
