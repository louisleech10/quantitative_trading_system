from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.factories import create_position_sizer
from momentum.Strategy.performance_metrics import PerformanceMetrics
from momentum.Strategy.risk_manager import RiskManager

logger = get_logger(__name__)


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    position_size: float
    direction: str
    pnl: float
    pnl_pct: float
    exit_reason: str
    mae: float
    mfe: float


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: List[Trade]
    metrics: Dict[str, float]
    config: Dict[str, Any]


class VectorizedBacktest:
    def __init__(self, commission: float = 0.001, slippage: float = 0.0005):
        if commission < 0 or slippage < 0:
            raise ValueError("commission and slippage must be >= 0")
        if commission + slippage > 0.10:
            logger.warning(f"High cost: commission={commission}, slippage={slippage}")
        self.commission = commission
        self.slippage = slippage

    def run_backtest(
        self,
        prices: pd.DataFrame,
        predicted_proba: pd.Series,
        atr_values: pd.Series,
        strategy_params: dict,
    ) -> BacktestResult:
        early_result = self._validate_inputs(prices, predicted_proba, atr_values, strategy_params)
        if early_result is not None:
            return early_result

        entry_threshold = float(strategy_params.get("entry_threshold", 0.7))
        exit_threshold = float(strategy_params.get("exit_threshold", 0.4))
        cooldown_bars = int(strategy_params.get("cooldown_bars", 0))

        entry_signals = self._generate_entry_signals(predicted_proba, entry_threshold)
        entry_signals = self._apply_cooldown(entry_signals, cooldown_bars)
        exit_signals = self._generate_exit_signals(predicted_proba, exit_threshold)

        position_sizes = self._calculate_position_sizes(
            predicted_proba,
            entry_signals,
            strategy_params,
        )

        trades = self._execute_trades(
            prices=prices,
            atr=atr_values,
            entry_signals=entry_signals,
            exit_signals=exit_signals,
            position_sizes=position_sizes,
            strategy_params=strategy_params,
        )

        equity_curve = self._calculate_equity_curve(trades, prices)
        metrics = PerformanceMetrics(equity_curve, trades).calculate_all()

        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            config=strategy_params,
        )

    def _generate_entry_signals(self, proba: pd.Series, threshold: float) -> pd.Series:
        return (proba > threshold).astype(int)

    def _generate_exit_signals(self, proba: pd.Series, threshold: float) -> pd.Series:
        return (proba < threshold).astype(int)

    def _apply_cooldown(self, signals: pd.Series, cooldown_bars: int) -> pd.Series:
        if cooldown_bars <= 0:
            return signals.astype(int)

        signal_values = signals.astype(int).to_numpy(copy=True)
        active_indices = np.flatnonzero(signal_values == 1)
        if len(active_indices) <= 1:
            return pd.Series(signal_values, index=signals.index, dtype=int)

        keep_mask = np.zeros(len(signal_values), dtype=int)
        last_kept = -10**9
        for idx in active_indices:
            if idx - last_kept > cooldown_bars:
                keep_mask[idx] = 1
                last_kept = int(idx)

        return pd.Series(keep_mask, index=signals.index, dtype=int)

    def _extract_sizer_kwargs(self, strategy_params: dict, method: str) -> dict:
        if method == "kelly":
            return {
                "kelly_fraction": float(strategy_params.get("kelly_fraction", 0.5)),
                "max_position": float(strategy_params.get("max_position_size", 0.25)),
            }
        if method == "fixed":
            return {
                "fixed_size": float(
                    strategy_params.get("fixed_size", strategy_params.get("position_size", 0.1))
                )
            }
        return {
            "max_position": float(strategy_params.get("max_position_size", 0.25)),
            "threshold": float(strategy_params.get("position_size_threshold", 0.5)),
        }

    def _calculate_position_sizes(
        self,
        proba: pd.Series,
        signals: pd.Series,
        strategy_params: dict,
    ) -> pd.Series:
        method = str(strategy_params.get("position_sizing_method", "fixed")).strip().lower()
        sizer = create_position_sizer(method, **self._extract_sizer_kwargs(strategy_params, method))
        risk_params = {
            "win_loss_ratio": float(strategy_params.get("win_loss_ratio", 1.5))
        }

        sizes = pd.Series(np.zeros(len(signals), dtype=float), index=signals.index)
        signal_indices = np.flatnonzero(signals.to_numpy() == 1)
        for idx in signal_indices:
            p = float(proba.iloc[idx])
            sizes.iloc[idx] = sizer.calculate_position_size(
                predicted_proba=p,
                equity=1.0,
                risk_params=risk_params,
            )
        return sizes

    def _execute_trades(
        self,
        prices: pd.DataFrame,
        atr: pd.Series,
        entry_signals: pd.Series,
        exit_signals: pd.Series,
        position_sizes: pd.Series,
        strategy_params: dict,
    ) -> List[Trade]:
        trades: List[Trade] = []

        stop_loss_atr = float(strategy_params.get("stop_loss_atr", 2.0))
        take_profit_ratio = float(strategy_params.get("take_profit_ratio", 3.0))
        trailing_activation = float(strategy_params.get("trailing_stop_activation", 0.05))

        in_position = False
        entry_idx = -1
        entry_price = 0.0
        entry_time: pd.Timestamp | Any = None
        position_size = 0.0
        stop_loss = None
        take_profit = None
        trailing_stop = None

        for i in range(len(prices)):
            row = prices.iloc[i]
            close = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])
            timestamp = row["timestamp"] if "timestamp" in prices.columns else prices.index[i]
            atr_value = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) else np.nan

            if not in_position and int(entry_signals.iloc[i]) == 1:
                in_position = True
                entry_idx = i
                entry_price = close
                entry_time = timestamp
                position_size = float(position_sizes.iloc[i])

                if pd.isna(atr_value) or atr_value <= 0:
                    stop_loss = None
                    take_profit = None
                    trailing_stop = None
                else:
                    stop_loss = RiskManager.calculate_stop_loss(entry_price, atr_value, stop_loss_atr)
                    take_profit = RiskManager.calculate_take_profit(
                        entry_price,
                        atr_value,
                        stop_loss_atr,
                        take_profit_ratio,
                    )
                    trailing_stop = None
                continue

            if not in_position:
                continue

            exit_reason = None
            exit_price = close

            if stop_loss is not None and low <= stop_loss:
                exit_reason = "stop_loss"
                exit_price = float(stop_loss)
            elif take_profit is not None and high >= take_profit:
                exit_reason = "take_profit"
                exit_price = float(take_profit)
            else:
                if stop_loss is not None:
                    maybe_trailing = RiskManager.calculate_trailing_stop(
                        entry_price=entry_price,
                        current_high=high,
                        atr=max(atr_value, 0.0) if not pd.isna(atr_value) else 0.0,
                        activation_multiplier=trailing_activation,
                    )
                    if maybe_trailing is not None:
                        trailing_stop = (
                            maybe_trailing if trailing_stop is None else max(trailing_stop, maybe_trailing)
                        )

                if trailing_stop is not None and low <= trailing_stop:
                    exit_reason = "trailing_stop"
                    exit_price = float(trailing_stop)
                elif int(exit_signals.iloc[i]) == 1:
                    exit_reason = "signal_exit"
                    exit_price = close

            if exit_reason is None:
                continue

            trade_pnl_pct_raw = (exit_price - entry_price) / entry_price
            total_cost = (self.commission + self.slippage) * 2
            trade_pnl_pct = trade_pnl_pct_raw - total_cost
            trade_pnl = position_size * trade_pnl_pct

            segment = prices.iloc[entry_idx : i + 1]
            min_low = float(segment["low"].min())
            max_high = float(segment["high"].max())
            mae = (min_low - entry_price) / entry_price
            mfe = (max_high - entry_price) / entry_price

            trades.append(
                Trade(
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=timestamp,
                    exit_price=exit_price,
                    position_size=position_size,
                    direction="long",
                    pnl=trade_pnl,
                    pnl_pct=trade_pnl_pct,
                    exit_reason=exit_reason,
                    mae=mae,
                    mfe=mfe,
                )
            )

            in_position = False
            entry_idx = -1
            stop_loss = None
            take_profit = None
            trailing_stop = None

        if in_position:
            last_idx = len(prices) - 1
            last_row = prices.iloc[last_idx]
            last_close = float(last_row["close"])
            last_time = last_row["timestamp"] if "timestamp" in prices.columns else prices.index[last_idx]

            trade_pnl_pct_raw = (last_close - entry_price) / entry_price
            total_cost = (self.commission + self.slippage) * 2
            trade_pnl_pct = trade_pnl_pct_raw - total_cost
            trade_pnl = position_size * trade_pnl_pct

            segment = prices.iloc[entry_idx : last_idx + 1]
            min_low = float(segment["low"].min())
            max_high = float(segment["high"].max())
            mae = (min_low - entry_price) / entry_price
            mfe = (max_high - entry_price) / entry_price

            trades.append(
                Trade(
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=last_time,
                    exit_price=last_close,
                    position_size=position_size,
                    direction="long",
                    pnl=trade_pnl,
                    pnl_pct=trade_pnl_pct,
                    exit_reason="data_end",
                    mae=mae,
                    mfe=mfe,
                )
            )

        return trades

    def _calculate_equity_curve(self, trades: List[Trade], prices: pd.DataFrame) -> pd.Series:
        equity = np.ones(len(prices), dtype=float)
        if not trades:
            return pd.Series(equity, index=prices.index)

        pnl_map: Dict[int, float] = {}
        timestamp_to_index: Dict[Any, int] = {}
        if "timestamp" in prices.columns:
            for idx, ts_value in enumerate(prices["timestamp"].tolist()):
                timestamp_to_index[ts_value] = idx

        for trade in trades:
            if "timestamp" in prices.columns:
                if trade.exit_time not in timestamp_to_index:
                    continue
                idx = int(timestamp_to_index[trade.exit_time])
            else:
                idx = int(prices.index.get_loc(trade.exit_time))
            pnl_map[idx] = pnl_map.get(idx, 0.0) + float(trade.pnl_pct)

        returns = np.zeros(len(prices), dtype=float)
        for idx, pnl in pnl_map.items():
            returns[idx] += pnl

        equity = np.cumprod(1.0 + returns)
        return pd.Series(equity, index=prices.index)

    def _validate_inputs(
        self,
        prices: pd.DataFrame,
        predicted_proba: pd.Series,
        atr_values: pd.Series,
        strategy_params: dict,
    ) -> BacktestResult | None:
        required_cols = {"open", "high", "low", "close"}
        missing = required_cols - set(prices.columns)
        if missing:
            raise ValueError(f"prices missing required columns: {sorted(missing)}")

        if prices.empty:
            return BacktestResult(
                equity_curve=pd.Series([1.0]),
                trades=[],
                metrics={},
                config=strategy_params,
            )
        if len(prices) == 1:
            return BacktestResult(
                equity_curve=pd.Series([1.0]),
                trades=[],
                metrics={},
                config=strategy_params,
            )
        if len(prices) != len(predicted_proba):
            raise ValueError(
                f"prices length {len(prices)} != predicted_proba length {len(predicted_proba)}"
            )
        if len(prices) != len(atr_values):
            raise ValueError(f"prices length {len(prices)} != atr_values length {len(atr_values)}")
        if (prices[["open", "high", "low", "close"]] <= 0).any().any():
            raise ValueError("prices contain zero or negative values")

        entry_threshold = strategy_params.get("entry_threshold", 0.7)
        exit_threshold = strategy_params.get("exit_threshold", 0.4)
        if entry_threshold <= exit_threshold:
            raise ValueError(
                f"entry_threshold ({entry_threshold}) must > exit_threshold ({exit_threshold})"
            )

        return None
