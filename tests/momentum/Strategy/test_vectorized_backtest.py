import numpy as np
import pandas as pd
import pytest

from momentum.Strategy.vectorized_backtest import Trade, VectorizedBacktest


def _build_prices(close_values):
    close = np.array(close_values, dtype=float)
    open_prices = close.copy()
    high = close + 1.0
    low = close - 1.0
    ts = pd.date_range("2025-01-01", periods=len(close), freq="12h")
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
        }
    )


def _default_params(**overrides):
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
    params.update(overrides)
    return params


def test_normal_backtest_with_trades(mock_prices, mock_predicted_proba, mock_atr, mock_strategy_params):
    vb = VectorizedBacktest()
    result = vb.run_backtest(mock_prices, mock_predicted_proba, mock_atr, mock_strategy_params)
    assert result is not None
    assert isinstance(result.trades, list)


def test_normal_backtest_metrics_calculated(mock_prices, mock_predicted_proba, mock_atr, mock_strategy_params):
    vb = VectorizedBacktest()
    result = vb.run_backtest(mock_prices, mock_predicted_proba, mock_atr, mock_strategy_params)
    assert "sharpe_ratio" in result.metrics


def test_empty_prices():
    vb = VectorizedBacktest()
    result = vb.run_backtest(pd.DataFrame(columns=["open", "high", "low", "close"]), pd.Series(dtype=float), pd.Series(dtype=float), _default_params())
    assert len(result.trades) == 0


def test_single_bar_prices():
    vb = VectorizedBacktest()
    prices = _build_prices([100.0])
    result = vb.run_backtest(prices, pd.Series([0.8]), pd.Series([2.0]), _default_params())
    assert len(result.trades) == 0


def test_zero_proba_no_signals():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103, 104])
    proba = pd.Series([0, 0, 0, 0, 0], dtype=float)
    atr = pd.Series([2, 2, 2, 2, 2], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params())
    assert len(result.trades) == 0


def test_all_proba_one_with_cooldown():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103, 104, 105, 106])
    proba = pd.Series([1, 1, 1, 1, 1, 1, 1], dtype=float)
    atr = pd.Series([2, 2, 2, 2, 2, 2, 2], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(cooldown_bars=3))
    assert len(result.trades) >= 1
    entry_times = [t.entry_time for t in result.trades]
    if len(entry_times) > 1:
        entry_indices = [
            int(prices.index[prices["timestamp"] == ts][0])
            for ts in entry_times
        ]
        assert min(np.diff(entry_indices)) > 3


def test_threshold_above_one_no_trades():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103])
    proba = pd.Series([0.6, 0.7, 0.8, 0.9], dtype=float)
    atr = pd.Series([2, 2, 2, 2], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(entry_threshold=1.1))
    assert len(result.trades) == 0


def test_entry_le_exit_threshold_error():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102])
    proba = pd.Series([0.8, 0.8, 0.8], dtype=float)
    atr = pd.Series([2, 2, 2], dtype=float)
    with pytest.raises(ValueError):
        vb.run_backtest(prices, proba, atr, _default_params(entry_threshold=0.4, exit_threshold=0.4))


def test_atr_contains_nan_fallback():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103])
    proba = pd.Series([0.8, 0.8, 0.3, 0.3], dtype=float)
    atr = pd.Series([2.0, np.nan, 2.0, 2.0], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params())
    assert len(result.trades) >= 1


def test_atr_all_zero_signal_exit_only():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103, 104])
    proba = pd.Series([0.8, 0.8, 0.3, 0.3, 0.3], dtype=float)
    atr = pd.Series([0, 0, 0, 0, 0], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params())
    assert len(result.trades) >= 1
    assert result.trades[0].exit_reason == "signal_exit"


def test_high_commission_warning(caplog):
    VectorizedBacktest(commission=0.08, slippage=0.03)
    assert "High cost" in caplog.text


def test_unclosed_position_at_data_end():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103, 104])
    proba = pd.Series([0.8, 0.8, 0.8, 0.8, 0.8], dtype=float)
    atr = pd.Series([2, 2, 2, 2, 2], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(exit_threshold=0.0))
    assert result.trades[-1].exit_reason == "data_end"


def test_cooldown_exceeds_data_length():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103, 104])
    proba = pd.Series([1, 1, 1, 1, 1], dtype=float)
    atr = pd.Series([2, 2, 2, 2, 2], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(cooldown_bars=100))
    assert len(result.trades) == 1


def test_consecutive_stop_losses():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 95, 90, 85, 80, 75, 70])
    proba = pd.Series([0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9], dtype=float)
    atr = pd.Series([1, 1, 1, 1, 1, 1, 1], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(stop_loss_atr=0.5, cooldown_bars=0))
    assert any(t.exit_reason == "stop_loss" for t in result.trades)


def test_zero_price_error():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 0, 102])
    proba = pd.Series([0.8, 0.8, 0.8], dtype=float)
    atr = pd.Series([2, 2, 2], dtype=float)
    with pytest.raises(ValueError):
        vb.run_backtest(prices, proba, atr, _default_params())


def test_mismatched_lengths_error():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102])
    proba = pd.Series([0.8, 0.8], dtype=float)
    atr = pd.Series([2, 2, 2], dtype=float)
    with pytest.raises(ValueError):
        vb.run_backtest(prices, proba, atr, _default_params())


@pytest.mark.parametrize("method", ["kelly", "fixed", "probability_scaled"])
def test_position_sizing_integration(method):
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103, 104, 105])
    proba = pd.Series([0.8, 0.9, 0.3, 0.3, 0.8, 0.3], dtype=float)
    atr = pd.Series([2, 2, 2, 2, 2, 2], dtype=float)
    params = _default_params(position_sizing_method=method)
    result = vb.run_backtest(prices, proba, atr, params)
    assert result is not None


def test_take_profit_triggered():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 110, 112, 114])
    prices.loc[1, "high"] = 120
    proba = pd.Series([0.9, 0.9, 0.9, 0.9], dtype=float)
    atr = pd.Series([2, 2, 2, 2], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(stop_loss_atr=1.0, take_profit_ratio=2.0))
    assert any(t.exit_reason == "take_profit" for t in result.trades)


def test_stop_loss_triggered():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 98, 96, 94])
    prices.loc[1, "low"] = 90
    proba = pd.Series([0.9, 0.9, 0.9, 0.9], dtype=float)
    atr = pd.Series([2, 2, 2, 2], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(stop_loss_atr=1.0))
    assert any(t.exit_reason == "stop_loss" for t in result.trades)


def test_trailing_stop_triggered():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 102, 104, 103, 101])
    prices.loc[2, "high"] = 108
    prices.loc[3, "low"] = 100
    proba = pd.Series([0.9, 0.9, 0.9, 0.9, 0.9], dtype=float)
    atr = pd.Series([1, 1, 1, 1, 1], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params(stop_loss_atr=2.0, trailing_stop_activation=1.0))
    assert any(t.exit_reason in {"trailing_stop", "take_profit", "stop_loss"} for t in result.trades)


def test_signal_exit_triggered():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102, 103, 104])
    proba = pd.Series([0.9, 0.9, 0.2, 0.2, 0.2], dtype=float)
    atr = pd.Series([0, 0, 0, 0, 0], dtype=float)
    result = vb.run_backtest(prices, proba, atr, _default_params())
    assert any(t.exit_reason == "signal_exit" for t in result.trades)


def test_commission_slippage_deduction():
    prices = _build_prices([100, 105, 110])
    proba = pd.Series([0.9, 0.2, 0.2], dtype=float)
    atr = pd.Series([2, 2, 2], dtype=float)
    no_cost = VectorizedBacktest(commission=0.0, slippage=0.0).run_backtest(prices, proba, atr, _default_params())
    with_cost = VectorizedBacktest(commission=0.01, slippage=0.01).run_backtest(prices, proba, atr, _default_params())

    assert no_cost.trades and with_cost.trades
    assert with_cost.trades[0].pnl < no_cost.trades[0].pnl


def test_backtest_performance_benchmark():
    vb = VectorizedBacktest()
    n = 1000
    close = np.linspace(100, 120, n)
    prices = _build_prices(close)
    proba = pd.Series(np.linspace(0.2, 0.95, n))
    atr = pd.Series(np.full(n, 2.0))
    result = vb.run_backtest(prices, proba, atr, _default_params())
    assert len(result.equity_curve) == n


def test_negative_commission_or_slippage_error():
    with pytest.raises(ValueError):
        VectorizedBacktest(commission=-0.001, slippage=0.0)
    with pytest.raises(ValueError):
        VectorizedBacktest(commission=0.001, slippage=-0.001)


def test_apply_cooldown_single_signal_branch():
    vb = VectorizedBacktest()
    signals = pd.Series([0, 0, 1, 0, 0])
    result = vb._apply_cooldown(signals, cooldown_bars=5)
    assert result.sum() == 1


def test_validate_inputs_missing_columns_error():
    vb = VectorizedBacktest()
    prices = pd.DataFrame({"open": [1], "close": [1]})
    with pytest.raises(ValueError):
        vb.run_backtest(prices, pd.Series([0.5]), pd.Series([1.0]), _default_params())


def test_validate_inputs_atr_length_mismatch_error():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102])
    proba = pd.Series([0.8, 0.8, 0.8], dtype=float)
    atr = pd.Series([2, 2], dtype=float)
    with pytest.raises(ValueError):
        vb.run_backtest(prices, proba, atr, _default_params())


def test_calculate_equity_curve_without_timestamp_column():
    vb = VectorizedBacktest()
    prices = pd.DataFrame(
        {
            "open": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
            "close": [100, 101, 102],
        },
        index=pd.Index([0, 1, 2]),
    )
    trades = [
        Trade(
            entry_time=0,
            entry_price=100,
            exit_time=1,
            exit_price=101,
            position_size=0.1,
            direction="long",
            pnl=0.001,
            pnl_pct=0.01,
            exit_reason="signal_exit",
            mae=-0.01,
            mfe=0.02,
        )
    ]
    curve = vb._calculate_equity_curve(trades, prices)
    assert len(curve) == 3


def test_calculate_equity_curve_skip_unknown_timestamp_exit():
    vb = VectorizedBacktest()
    prices = _build_prices([100, 101, 102])
    unknown_time = pd.Timestamp("2030-01-01")
    trades = [
        Trade(
            entry_time=prices.loc[0, "timestamp"],
            entry_price=100,
            exit_time=unknown_time,
            exit_price=101,
            position_size=0.1,
            direction="long",
            pnl=0.001,
            pnl_pct=0.01,
            exit_reason="signal_exit",
            mae=-0.01,
            mfe=0.02,
        )
    ]
    curve = vb._calculate_equity_curve(trades, prices)
    assert (curve == 1.0).all()
