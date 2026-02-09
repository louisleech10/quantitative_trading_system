"""Cross-sectional relative strength features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class RelativeStrengthProcessor:
    """Relative strength features (BTC reference)."""

    def compute_relative_price(self, symbol_close: pd.Series, btc_close: pd.Series) -> pd.Series:
        """symbol_price / btc_price"""
        return symbol_close / btc_close.replace(0, np.nan)

    def compute_beta(
        self,
        symbol_returns: pd.Series,
        btc_returns: pd.Series,
        window: int = 60,
    ) -> pd.Series:
        """Rolling Cov(R_i, R_btc) / Var(R_btc)"""
        cov = symbol_returns.rolling(window).cov(btc_returns)
        var = btc_returns.rolling(window).var()
        return cov / var.replace(0, np.nan)

    def compute_idiosyncratic_momentum(
        self,
        symbol_returns: pd.Series,
        btc_returns: pd.Series,
        beta: pd.Series,
    ) -> pd.Series:
        """Return - Beta x BTC_Return"""
        return symbol_returns - beta * btc_returns
