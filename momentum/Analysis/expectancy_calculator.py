"""
Expectancy Calculator - 期望值估算

Author: AI Agent
Date: 2026-01-29
"""

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from api.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExpectancyResult:
    """期望值估算結果"""
    win_rate: float
    avg_win: float
    avg_loss: float
    expectancy: float
    total_trades: int
    threshold: float
    note: str

    def to_dict(self) -> Dict:
        return {
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "expectancy": self.expectancy,
            "total_trades": self.total_trades,
            "threshold": self.threshold,
            "note": self.note
        }


class ExpectancyCalculator:
    """期望值估算器"""

    def estimate_expectancy(
        self,
        price_changes: np.ndarray,
        predicted_proba: np.ndarray,
        threshold: float,
        min_trades: int = 30
    ) -> ExpectancyResult:
        """
        估算交易期望值

        Args:
            price_changes: 實際價格變化（百分比或報酬率）
            predicted_proba: 預測機率
            threshold: 進場機率閾值
            min_trades: 最少交易數（小於此數會警告）
        """
        if len(price_changes) == 0:
            raise ValueError("price_changes 為空")
        if len(price_changes) != len(predicted_proba):
            raise ValueError("price_changes 與 predicted_proba 長度不一致")

        trade_mask = predicted_proba >= threshold
        trade_returns = price_changes[trade_mask]

        total_trades = int(len(trade_returns))
        if total_trades == 0:
            logger.warning("無符合閾值的交易，無法估算期望值")
            return ExpectancyResult(
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                expectancy=0.0,
                total_trades=0,
                threshold=threshold,
                note="無符合閾值交易，期望值為 0"
            )

        wins = trade_returns[trade_returns > 0]
        losses = trade_returns[trade_returns <= 0]

        win_rate = float(len(wins) / total_trades)
        avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0

        expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss
        note = "此為粗估值，精確值需回測系統計算"

        logger.info(
            f"期望值估算完成 - 交易數: {total_trades}, "
            f"勝率: {win_rate:.2%}, 期望值: {expectancy:.6f}"
        )
        if total_trades < min_trades:
            logger.warning(
                f"交易數不足 ({total_trades} < {min_trades})，期望值可能不穩定"
            )

        return ExpectancyResult(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=float(expectancy),
            total_trades=total_trades,
            threshold=threshold,
            note=note
        )

    def calculate_sharpe_proxy(
        self,
        trade_returns: np.ndarray
    ) -> Optional[float]:
        """
        估算簡化 Sharpe Proxy
        """
        if len(trade_returns) == 0:
            return None

        mean_return = float(np.mean(trade_returns))
        std_return = float(np.std(trade_returns))
        if std_return == 0:
            return None

        return mean_return / std_return
