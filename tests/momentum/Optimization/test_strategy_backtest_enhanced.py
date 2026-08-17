"""Phase 4.2.4 tests for enhanced StrategyBacktestObjective."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import optuna
import pandas as pd
import pytest

from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective


class StubBacktestEngine:
    def __init__(self, result=None):
        self.result = result

    def run_backtest(self, prices, predicted_proba, atr_values, strategy_params):
        if self.result is not None:
            return self.result
        equity_curve = pd.Series([1.0, 1.05, 1.02, 1.08])
        trades = [
            {"pnl": 0.03, "pnl_pct": 0.03},
            {"pnl": -0.01, "pnl_pct": -0.01},
            {"pnl": 0.02, "pnl_pct": 0.02},
        ]
        return SimpleNamespace(equity_curve=equity_curve, trades=trades, metrics={}, config=strategy_params)


def make_inputs(n: int = 30):
    close = 100 + np.cumsum(np.random.randn(n) * 0.1)
    prices = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=n, freq="12h"),
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
        }
    )
    predicted_proba = pd.Series(np.linspace(0.2, 0.95, n))
    atr_values = pd.Series(np.full(n, 1.0))
    return prices, predicted_proba, atr_values


def make_objective(**kwargs):
    prices, predicted_proba, atr_values = make_inputs()
    base = dict(
        backtest_engine=StubBacktestEngine(),
        prices=prices,
        predicted_proba=predicted_proba,
        atr_values=atr_values,
        constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 0},
        target_metric="expectancy",
        multi_objective=False,
    )
    base.update(kwargs)
    return StrategyBacktestObjective(**base)


def test_evaluate_returns_target_metric():
    objective = make_objective(target_metric="expectancy")
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    value = objective.evaluate(params)
    assert isinstance(value, float)


def test_evaluate_with_constraints_pass():
    objective = make_objective(constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 1})
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    assert isinstance(objective.evaluate(params), float)


def test_evaluate_maxdd_constraint_pruned():
    objective = make_objective(constraints={"max_drawdown": -0.01, "min_win_rate": 0.0, "min_trades": 0})
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    with pytest.raises(optuna.TrialPruned):
        objective.evaluate(params)


def test_evaluate_winrate_constraint_pruned():
    objective = make_objective(constraints={"max_drawdown": -1.0, "min_win_rate": 0.9, "min_trades": 0})
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    with pytest.raises(optuna.TrialPruned):
        objective.evaluate(params)


def test_evaluate_min_trades_pruned():
    objective = make_objective(constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 999})
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    with pytest.raises(optuna.TrialPruned):
        objective.evaluate(params)


def test_all_trials_pruned_handling():
    objective = make_objective(constraints={"max_drawdown": 0.0, "min_win_rate": 1.0, "min_trades": 999})
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    with pytest.raises(optuna.TrialPruned):
        objective.evaluate(params)


def test_invalid_target_metric():
    prices, predicted_proba, atr_values = make_inputs()
    with pytest.raises(ValueError):
        StrategyBacktestObjective(
            backtest_engine=StubBacktestEngine(),
            prices=prices,
            predicted_proba=predicted_proba,
            atr_values=atr_values,
            target_metric="invalid_metric",
        )


def test_nan_proba_input():
    prices, predicted_proba, atr_values = make_inputs()
    predicted_proba.iloc[0] = np.nan
    objective = StrategyBacktestObjective(
        backtest_engine=StubBacktestEngine(),
        prices=prices,
        predicted_proba=predicted_proba,
        atr_values=atr_values,
        constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 0},
    )
    assert objective.predicted_proba.isna().sum() == 0


def test_non_continuous_timestamps():
    prices, predicted_proba, atr_values = make_inputs()
    prices.loc[3, "timestamp"] = prices.loc[0, "timestamp"]
    objective = StrategyBacktestObjective(
        backtest_engine=StubBacktestEngine(),
        prices=prices,
        predicted_proba=predicted_proba,
        atr_values=atr_values,
    )
    assert objective is not None


def test_multi_objective_mode():
    objective = make_objective(multi_objective=True)
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    result = objective.evaluate(params)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_create_search_space_params():
    objective = make_objective()
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    assert len(params) == 9


def test_backtest_engine_protocol_injection():
    objective = make_objective(backtest_engine=StubBacktestEngine())
    assert hasattr(objective.backtest_engine, "run_backtest")


@pytest.mark.parametrize("metric", ["expectancy", "sortino_ratio", "calmar_ratio", "sqn"])
def test_target_metric_variants(metric: str):
    objective = make_objective(target_metric=metric)
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    assert isinstance(objective.evaluate(params), float)


def test_evaluate_stores_trial_user_attrs():
    objective = make_objective()
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    objective.evaluate(params)
    assert "expectancy" in trial.user_attrs


def test_evaluate_with_empty_backtest_result():
    empty_result = SimpleNamespace(equity_curve=pd.Series([1.0]), trades=[], metrics={}, config={})
    objective = make_objective(backtest_engine=StubBacktestEngine(result=empty_result))
    trial = optuna.trial.FixedTrial(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "kelly_fraction": 0.5,
            "max_position_size": 0.2,
            "cooldown_bars": 5,
            "trailing_stop_activation": 0.03,
        }
    )
    params = objective.create_search_space(trial)
    assert isinstance(objective.evaluate(params), float)


def test_directions_property_multi_objective():
    objective = make_objective(multi_objective=True)
    assert objective.directions == ["maximize", "minimize"]


def test_name_property():
    objective = make_objective()
    assert objective.name == "strategy_backtest"


def test_length_mismatch_predicted_proba_error():
    prices, predicted_proba, atr_values = make_inputs()
    with pytest.raises(ValueError, match="predicted_proba"):
        StrategyBacktestObjective(
            backtest_engine=StubBacktestEngine(),
            prices=prices,
            predicted_proba=predicted_proba.iloc[:-1],
            atr_values=atr_values,
        )


def test_length_mismatch_atr_error():
    prices, predicted_proba, atr_values = make_inputs()
    with pytest.raises(ValueError, match="atr_values"):
        StrategyBacktestObjective(
            backtest_engine=StubBacktestEngine(),
            prices=prices,
            predicted_proba=predicted_proba,
            atr_values=atr_values.iloc[:-1],
        )


def test_direction_and_directions_defaults():
    objective = make_objective(multi_objective=False)
    assert objective.direction == "maximize"
    assert objective.directions is None


def test_get_pruning_callback_none():
    objective = make_objective()
    assert objective.get_pruning_callback(None) is None


def test_evaluate_without_create_search_space():
    objective = make_objective()
    params = {
        "entry_threshold": 0.7,
        "exit_threshold": 0.4,
        "stop_loss_atr": 2.0,
        "take_profit_ratio": 3.0,
        "position_sizing_method": "fixed",
        "kelly_fraction": 0.5,
        "max_position_size": 0.2,
        "cooldown_bars": 5,
        "trailing_stop_activation": 0.03,
    }
    assert isinstance(objective.evaluate(params), float)


def test_record_trial_metrics_non_float_value_fallback():
    objective = make_objective()

    class TrialSpy:
        def __init__(self):
            self.calls = {}

        def set_user_attr(self, key, value):
            self.calls[key] = value

    spy = TrialSpy()
    objective._current_trial = spy
    objective._record_trial_metrics({"meta": "not-a-float"})
    assert spy.calls["meta"] == "not-a-float"


# ============================================================================
# GAP-1 Task 1.3 — objective 端傳遞鏈斷言（只加，不改既有）
# 驗收②b：timeframe 須真的傳到 engine 並改變數值，而非「只存在參數」。
# ============================================================================


class _RecordingEngine:
    """記錄 run_backtest 收到的 kwargs，並回真實引擎之結果形狀。"""

    def __init__(self):
        self.calls = []

    def run_backtest(self, prices, predicted_proba, atr_values, strategy_params, **kwargs):
        from momentum.Strategy.vectorized_backtest import VectorizedBacktest

        self.calls.append(kwargs)
        return VectorizedBacktest().run_backtest(
            prices, predicted_proba, atr_values, strategy_params, **kwargs
        )


def test_objective_forwards_timeframe_to_engine():
    """②b 前半：timeframe 給定時，engine 真的收到（傳遞鏈存在）。"""
    engine = _RecordingEngine()
    objective = make_objective(backtest_engine=engine, timeframe="1h", risk_free_rate=0.0)
    objective.evaluate(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "position_size": 0.1,
            "kelly_fraction": 0.5,
            "max_position_size": 0.25,
            "cooldown_bars": 0,
            "trailing_stop_activation": 0.05,
        }
    )
    assert engine.calls, "engine 未被呼叫"
    assert engine.calls[0]["timeframe"] == "1h"
    assert engine.calls[0]["risk_free_rate"] == 0.0


def test_objective_omits_new_kwargs_when_timeframe_absent():
    """既有路徑（未指定 timeframe）之呼叫形狀逐字不變 ⇒ 舊 engine 實作不破。"""
    engine = _RecordingEngine()
    objective = make_objective(backtest_engine=engine, target_metric="sharpe_ratio")
    objective.evaluate(
        {
            "entry_threshold": 0.7,
            "exit_threshold": 0.4,
            "stop_loss_atr": 2.0,
            "take_profit_ratio": 3.0,
            "position_sizing_method": "fixed",
            "position_size": 0.1,
            "kelly_fraction": 0.5,
            "max_position_size": 0.25,
            "cooldown_bars": 0,
            "trailing_stop_activation": 0.05,
        }
    )
    assert engine.calls[0] == {}


def test_objective_sharpe_matches_direct_engine_and_differs_from_default():
    """②b 後半：objective 之 sharpe 與 engine 直呼同值，且與 timeframe=None 不等。"""
    from momentum.Strategy.performance_metrics import PerformanceMetrics
    from momentum.Strategy.vectorized_backtest import VectorizedBacktest

    params = {
        "entry_threshold": 0.7,
        "exit_threshold": 0.4,
        "stop_loss_atr": 2.0,
        "take_profit_ratio": 3.0,
        "position_sizing_method": "fixed",
        "position_size": 0.1,
        "kelly_fraction": 0.5,
        "max_position_size": 0.25,
        "cooldown_bars": 0,
        "trailing_stop_activation": 0.05,
    }
    prices, proba, atr = make_inputs(60)

    engine = _RecordingEngine()
    objective = StrategyBacktestObjective(
        backtest_engine=engine,
        prices=prices,
        predicted_proba=proba,
        atr_values=atr,
        target_metric="sharpe_ratio",
        constraints={"max_drawdown": -1.0, "min_win_rate": 0.0, "min_trades": 0},
        timeframe="1h",
        risk_free_rate=0.0,
    )
    objective_value = objective.evaluate(params)

    direct = VectorizedBacktest().run_backtest(
        prices, proba, atr, params, timeframe="1h", risk_free_rate=0.0
    )
    assert direct.annualization["periods_per_year"] == 8760
    assert objective_value == pytest.approx(direct.metrics["sharpe_ratio"], abs=1e-12)

    default = VectorizedBacktest().run_backtest(prices, proba, atr, params, risk_free_rate=0.0)
    default_sharpe = PerformanceMetrics(
        default.equity_curve, default.trades, risk_free_rate=0.0, periods_per_year=730
    ).calculate_all()["sharpe_ratio"]
    if default_sharpe != 0.0:
        assert objective_value != pytest.approx(default_sharpe, abs=1e-12)
