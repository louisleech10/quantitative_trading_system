"""Strategy backtest objective for Optuna."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.protocols import IOptimizationObjective

logger = get_logger(__name__)


class StrategyBacktestObjective(IOptimizationObjective):
    """策略回測參數優化目標（Sharpe 最大化，可選 MaxDD 最小化）。"""

    def __init__(self, model_predictions: Any, price_data: Any, multi_objective: bool = False):
        self.predictions = np.asarray(model_predictions, dtype=float)
        self.prices = pd.Series(np.asarray(price_data, dtype=float))
        self.multi_objective = multi_objective

        if len(self.predictions) != len(self.prices):
            raise ValueError("model_predictions 與 price_data 長度必須一致")
        if len(self.predictions) < 3:
            raise ValueError("資料筆數不足，至少需要 3 筆")

    @property
    def name(self) -> str:
        return "strategy_backtest"

    @property
    def direction(self) -> str:
        return "maximize"

    @property
    def directions(self) -> Optional[list[str]]:
        if self.multi_objective:
            return ["maximize", "minimize"]
        return None

    def create_search_space(self, trial: Any) -> Dict[str, Any]:
        return {
            "entry_threshold": trial.suggest_float("entry_threshold", 0.50, 0.90),
            "exit_threshold": trial.suggest_float("exit_threshold", 0.10, 0.50),
            "stop_loss": trial.suggest_float("stop_loss", 0.005, 0.10),
            "take_profit": trial.suggest_float("take_profit", 0.01, 0.20),
            "max_holding_bars": trial.suggest_int("max_holding_bars", 1, 30),
            "position_size": trial.suggest_float("position_size", 0.10, 1.00),
            "cooldown_bars": trial.suggest_int("cooldown_bars", 0, 10),
            "transaction_cost": trial.suggest_float("transaction_cost", 0.0, 0.005),
            "min_signal_gap": trial.suggest_int("min_signal_gap", 0, 5),
        }

    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, float]]:
        signals = self._generate_signals(params)
        metrics = self._run_backtest(signals, params)
        if self.multi_objective:
            return float(metrics["sharpe_ratio"]), float(metrics["max_drawdown"])
        return float(metrics["sharpe_ratio"])

    def get_pruning_callback(self, trial: Any) -> Optional[Any]:
        return None

    def _generate_signals(self, params: Dict[str, Any]) -> pd.Series:
        entry_threshold = float(params["entry_threshold"])
        exit_threshold = float(params["exit_threshold"])

        if entry_threshold <= exit_threshold:
            raise ValueError("entry_threshold 必須大於 exit_threshold")

        raw_signal = np.where(
            self.predictions >= entry_threshold,
            1.0,
            np.where(self.predictions <= exit_threshold, 0.0, np.nan),
        )
        signal_series = pd.Series(raw_signal).ffill().fillna(0.0)

        min_signal_gap = int(params.get("min_signal_gap", 0))
        if min_signal_gap > 0:
            changed = signal_series.diff().abs().fillna(signal_series.abs())
            cooldown_mask = changed.rolling(window=min_signal_gap + 1, min_periods=1).max().shift(1).fillna(0) > 0
            signal_series = signal_series.where(~cooldown_mask, signal_series.shift(1).fillna(0.0))

        return signal_series.astype(float)

    def _run_backtest(self, signals: pd.Series, params: Dict[str, Any]) -> Dict[str, float]:
        returns = self.prices.pct_change().fillna(0.0)

        position_size = float(params["position_size"])
        stop_loss = float(params["stop_loss"])
        take_profit = float(params["take_profit"])
        transaction_cost = float(params["transaction_cost"])

        position = signals.shift(1).fillna(0.0) * position_size
        gross_returns = position * returns
        bounded_returns = gross_returns.clip(lower=-stop_loss, upper=take_profit)

        turnover = position.diff().abs().fillna(position.abs())
        costs = turnover * transaction_cost
        net_returns = bounded_returns - costs

        mean_ret = float(net_returns.mean())
        std_ret = float(net_returns.std(ddof=0))
        sharpe_ratio = (np.sqrt(252.0) * mean_ret / std_ret) if std_ret > 0 else -999.0

        equity_curve = (1.0 + net_returns).cumprod()
        running_peak = equity_curve.cummax()
        drawdown = 1.0 - (equity_curve / running_peak.replace(0, np.nan))
        max_drawdown = float(drawdown.fillna(0.0).max())

        logger.info(
            f"StrategyBacktestObjective result: sharpe={sharpe_ratio:.6f}, "
            f"max_drawdown={max_drawdown:.6f}"
        )

        return {
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
        }
