from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value_float = float(value)
        if np.isnan(value_float) or np.isinf(value_float):
            return default
        return value_float
    except (TypeError, ValueError):
        return default


class PerformanceMetrics:
    def __init__(self, equity_curve: Any, trades: Any, risk_free_rate: float = 0.02, periods_per_year: int = 730):
        if periods_per_year <= 0:
            raise ValueError(f"periods_per_year must be > 0, got {periods_per_year}")

        if equity_curve is None:
            equity_curve = []

        self.equity_curve = pd.Series(equity_curve, dtype=float).dropna()
        self.trades: List[Any] = list(trades or [])
        self.risk_free_rate = float(risk_free_rate)
        self.periods_per_year = int(periods_per_year)

    def _returns(self) -> pd.Series:
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return pd.Series(dtype=float)
        returns = self.equity_curve.pct_change().dropna()
        return returns.replace([np.inf, -np.inf], np.nan).dropna()

    def _trade_pnls(self) -> List[float]:
        results: List[float] = []
        for trade in self.trades:
            pnl = getattr(trade, "pnl", None)
            if pnl is None and isinstance(trade, dict):
                pnl = trade.get("pnl")
            results.append(_safe_float(pnl, 0.0))
        return results

    def _trade_pnl_pcts(self) -> List[float]:
        results: List[float] = []
        for trade in self.trades:
            pnl_pct = getattr(trade, "pnl_pct", None)
            if pnl_pct is None and isinstance(trade, dict):
                pnl_pct = trade.get("pnl_pct")
            results.append(_safe_float(pnl_pct, 0.0))
        return results

    def total_return(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        start = _safe_float(self.equity_curve.iloc[0], 0.0)
        end = _safe_float(self.equity_curve.iloc[-1], 0.0)
        if start <= 0:
            return 0.0
        return (end / start) - 1.0

    def cagr(self) -> float:
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return 0.0
        start = _safe_float(self.equity_curve.iloc[0], 0.0)
        end = _safe_float(self.equity_curve.iloc[-1], 0.0)
        if start <= 0 or end <= 0:
            return 0.0

        n_periods = len(self.equity_curve) - 1
        years = n_periods / self.periods_per_year
        return (end / start) ** (1.0 / years) - 1.0

    def sharpe_ratio(self) -> float:
        returns = self._returns()
        if returns.empty:
            return 0.0
        mean_ret = _safe_float(returns.mean(), 0.0)
        std_ret = _safe_float(returns.std(ddof=0), 0.0)
        if std_ret == 0:
            return 0.0
        excess = mean_ret - self.risk_free_rate / self.periods_per_year
        return excess / std_ret * np.sqrt(self.periods_per_year)

    def sortino_ratio(self) -> float:
        returns = self._returns()
        if returns.empty:
            return 0.0
        mean_ret = _safe_float(returns.mean(), 0.0)
        downside = returns[returns < 0]
        downside_std = _safe_float(downside.std(ddof=0), 0.0)
        if downside_std == 0:
            return 0.0
        excess = mean_ret - self.risk_free_rate / self.periods_per_year
        return excess / downside_std * np.sqrt(self.periods_per_year)

    def calmar_ratio(self) -> float:
        max_dd = abs(self.max_drawdown())
        if max_dd == 0:
            return 0.0
        return self.cagr() / max_dd

    def max_drawdown(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        running_max = self.equity_curve.cummax().replace(0, np.nan)
        drawdown = (self.equity_curve / running_max) - 1.0
        return _safe_float(drawdown.min(), 0.0)

    def max_drawdown_duration(self) -> int:
        if self.equity_curve.empty:
            return 0
        running_max = self.equity_curve.cummax().replace(0, np.nan)
        drawdown = (self.equity_curve / running_max) - 1.0
        in_drawdown = drawdown < 0
        if not in_drawdown.any():
            return 0

        max_duration = 0
        current = 0
        for is_dd in in_drawdown:
            if is_dd:
                current += 1
                max_duration = max(max_duration, current)
            else:
                current = 0
        return int(max_duration)

    def expectancy(self) -> float:
        pnls = self._trade_pnls()
        if not pnls:
            return 0.0
        wins = [x for x in pnls if x > 0]
        losses = [x for x in pnls if x < 0]
        total = len(pnls)
        win_rate = len(wins) / total
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss = float(np.mean(losses)) if losses else 0.0
        return win_rate * avg_win - (1.0 - win_rate) * abs(avg_loss)

    def system_quality_number(self) -> float:
        returns = np.asarray(self._trade_pnl_pcts(), dtype=float)
        if returns.size == 0:
            return 0.0
        mean_ret = _safe_float(np.nanmean(returns), 0.0)
        std_ret = _safe_float(np.nanstd(returns), 0.0)
        if std_ret == 0:
            return 0.0
        n = min(int(returns.size), 100)
        return mean_ret / std_ret * np.sqrt(n)

    def win_rate(self) -> float:
        pnls = self._trade_pnls()
        if not pnls:
            return 0.0
        wins = sum(1 for x in pnls if x > 0)
        return wins / len(pnls)

    def profit_factor(self) -> float:
        pnls = self._trade_pnls()
        if not pnls:
            return 0.0
        gross_profit = sum(x for x in pnls if x > 0)
        gross_loss = abs(sum(x for x in pnls if x < 0))
        if gross_loss == 0:
            return 0.0
        return gross_profit / gross_loss

    def avg_win(self) -> float:
        pnls = self._trade_pnls()
        wins = [x for x in pnls if x > 0]
        if not wins:
            return 0.0
        return float(np.mean(wins))

    def avg_loss(self) -> float:
        pnls = self._trade_pnls()
        losses = [x for x in pnls if x < 0]
        if not losses:
            return 0.0
        return float(np.mean(losses))

    def calculate_all(self) -> Dict[str, float]:
        return {
            "total_return": self.total_return(),
            "cagr": self.cagr(),
            "sharpe_ratio": self.sharpe_ratio(),
            "sortino_ratio": self.sortino_ratio(),
            "calmar_ratio": self.calmar_ratio(),
            "max_drawdown": self.max_drawdown(),
            "max_drawdown_duration": float(self.max_drawdown_duration()),
            "expectancy": self.expectancy(),
            "sqn": self.system_quality_number(),
            "win_rate": self.win_rate(),
            "profit_factor": self.profit_factor(),
            "avg_win": self.avg_win(),
            "avg_loss": self.avg_loss(),
            "total_trades": float(len(self.trades)),
        }
