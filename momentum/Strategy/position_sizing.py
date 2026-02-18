from __future__ import annotations

import math
from typing import Any, Dict

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class KellyPositionSizer:
    def __init__(self, kelly_fraction: float = 0.5, max_position: float = 0.25):
        if not 0.0 <= kelly_fraction <= 1.0:
            raise ValueError(f"kelly_fraction must be in [0, 1], got {kelly_fraction}")
        if max_position <= 0:
            raise ValueError(f"max_position must be > 0, got {max_position}")
        self.kelly_fraction = kelly_fraction
        self.max_position = max_position

    def calculate_position_size(
        self,
        predicted_proba: float,
        equity: float,
        risk_params: Dict[str, Any],
    ) -> float:
        if equity <= 0:
            logger.warning("equity <= 0, fallback to position size 0.0")
            return 0.0

        if math.isnan(predicted_proba):
            return 0.0

        proba = min(max(float(predicted_proba), 0.0), 1.0)
        win_loss_ratio = float(risk_params.get("win_loss_ratio", 1.5))
        if win_loss_ratio <= 0:
            raise ValueError(f"win_loss_ratio must be > 0, got {win_loss_ratio}")

        p = proba
        q = 1.0 - p
        b = win_loss_ratio
        kelly_fraction_raw = (p * b - q) / b
        actual_fraction = kelly_fraction_raw * self.kelly_fraction
        clipped = min(max(actual_fraction, 0.0), self.max_position)
        return float(clipped)


class FixedPositionSizer:
    def __init__(self, fixed_size: float = 0.1):
        if fixed_size < 0:
            raise ValueError(f"fixed_size must be >= 0, got {fixed_size}")
        self.fixed_size = fixed_size

    def calculate_position_size(
        self,
        predicted_proba: float,
        equity: float,
        risk_params: Dict[str, Any],
    ) -> float:
        return float(self.fixed_size)


class ProbabilityScaledSizer:
    def __init__(self, max_position: float = 0.25, threshold: float = 0.5):
        if max_position <= 0:
            raise ValueError(f"max_position must be > 0, got {max_position}")
        if not 0 <= threshold < 1:
            raise ValueError(f"threshold must be in [0, 1), got {threshold}")
        self.max_position = max_position
        self.threshold = threshold

    def calculate_position_size(
        self,
        predicted_proba: float,
        equity: float,
        risk_params: Dict[str, Any],
    ) -> float:
        if equity <= 0:
            logger.warning("equity <= 0, fallback to position size 0.0")
            return 0.0

        if math.isnan(predicted_proba):
            return 0.0

        proba = min(max(float(predicted_proba), 0.0), 1.0)
        if proba <= self.threshold:
            return 0.0

        size = (proba - self.threshold) / (1.0 - self.threshold) * self.max_position
        return float(min(max(size, 0.0), self.max_position))
