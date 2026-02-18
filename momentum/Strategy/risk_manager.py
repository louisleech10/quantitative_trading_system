from __future__ import annotations

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class RiskManager:
    @staticmethod
    def calculate_stop_loss(entry_price: float, atr: float, multiplier: float) -> float:
        if entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got {entry_price}")
        if atr < 0:
            raise ValueError(f"atr must be >= 0, got {atr}")
        if multiplier < 0:
            raise ValueError(f"multiplier must be >= 0, got {multiplier}")

        if atr == 0 or multiplier == 0:
            logger.warning("atr==0 or multiplier==0 in calculate_stop_loss, fallback to entry_price")
            return float(entry_price)

        return float(entry_price - atr * multiplier)

    @staticmethod
    def calculate_take_profit(entry_price: float, atr: float, sl_multiplier: float, tp_ratio: float) -> float:
        if entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got {entry_price}")
        if atr < 0:
            raise ValueError(f"atr must be >= 0, got {atr}")
        if sl_multiplier < 0:
            raise ValueError(f"sl_multiplier must be >= 0, got {sl_multiplier}")

        if atr == 0:
            logger.warning("atr==0 in calculate_take_profit, fallback to entry_price")
            return float(entry_price)

        take_profit = float(entry_price + atr * sl_multiplier * tp_ratio)
        if take_profit < entry_price:
            raise ValueError(f"take_profit must be >= entry_price, got {take_profit} < {entry_price}")
        return take_profit

    @staticmethod
    def calculate_trailing_stop(
        entry_price: float,
        current_high: float,
        atr: float,
        activation_multiplier: float,
    ) -> float | None:
        if entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got {entry_price}")
        if current_high <= 0:
            raise ValueError(f"current_high must be > 0, got {current_high}")
        if atr < 0:
            raise ValueError(f"atr must be >= 0, got {atr}")
        if activation_multiplier < 0:
            raise ValueError(
                f"activation_multiplier must be >= 0, got {activation_multiplier}"
            )

        if atr == 0:
            return None

        activation_price = entry_price + atr * activation_multiplier
        if current_high < activation_price:
            return None

        trailing_stop = current_high - atr * activation_multiplier
        return float(trailing_stop)
