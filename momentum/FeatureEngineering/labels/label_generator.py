"""Label generation utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class LabelGenerator:
    """Multi-horizon binary/regression label generation."""

    def __init__(self, config: dict):
        self._binary_horizons = config.get("binary", {}).get("horizons", [3, 5, 8, 13, 21])
        self._binary_threshold = config.get("binary", {}).get("threshold", 0.0)
        self._regression_horizons = config.get("regression", {}).get("horizons", [5, 13])

    def generate_all(self, close_prices: pd.Series) -> pd.DataFrame:
        """Generate all labels (binary + regression)."""
        labels = {}
        for horizon in self._binary_horizons:
            labels[f"label_binary_{horizon}d"] = self.generate_binary(
                close_prices, horizon, self._binary_threshold
            )
        for horizon in self._regression_horizons:
            labels[f"label_return_{horizon}d"] = self.generate_return(close_prices, horizon)
        return pd.DataFrame(labels, index=close_prices.index)

    def generate_binary(self, close: pd.Series, horizon: int, threshold: float) -> pd.Series:
        """label_binary_{horizon}d = 1 if return > threshold else 0"""
        ret = close.shift(-horizon) / close - 1
        binary = (ret > threshold).astype(float)
        binary[ret.isna()] = np.nan
        return binary

    def generate_return(self, close: pd.Series, horizon: int) -> pd.Series:
        """label_return_{horizon}d = (Close[t+N] / Close[t]) - 1"""
        return close.shift(-horizon) / close - 1
