"""Label generation utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)

# LA-2 DEC-1：winsorized 標籤禁用；三層 fail-closed 共用 reason-code literal
LOOKAHEAD_LABEL_UNSUPPORTED = "LOOKAHEAD_LABEL_UNSUPPORTED"
WINSORIZED_DISABLED_MSG = (
    f"{LOOKAHEAD_LABEL_UNSUPPORTED}: winsorized return_type is disabled (LA-2 DEC-1)"
)


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

    def generate_log_return(self, close: pd.Series, horizon: int) -> pd.Series:
        """ln(P_{t+N} / P_t) — log return"""
        shifted = close.shift(-horizon)
        base = close.replace(0, np.nan)
        return np.log(shifted / base)

    def generate_excess_return(
        self, close: pd.Series, benchmark_close: pd.Series | None, horizon: int
    ) -> pd.Series:
        """R_asset - R_benchmark — excess return"""
        if benchmark_close is None:
            logger.error("benchmark_close is required for excess return")
            raise ValueError("benchmark_close is required for excess return")
        asset_ret = close.shift(-horizon) / close - 1
        bench_ret = benchmark_close.shift(-horizon) / benchmark_close - 1
        return asset_ret - bench_ret

    def generate_risk_adjusted_return(
        self, close: pd.Series, horizon: int, vol_window: int = 21
    ) -> pd.Series:
        """R / rolling volatility — risk-adjusted return"""
        if vol_window <= 0:
            logger.error("vol_window must be positive")
            raise ValueError("vol_window must be positive")
        ret = close.shift(-horizon) / close - 1
        vol = close.pct_change().rolling(vol_window).std()
        return ret / vol.replace(0, np.nan)

    def generate_winsorized_return(
        self, close: pd.Series, horizon: int, lower: float = 0.01, upper: float = 0.99
    ) -> pd.Series:
        """Winsorized return — 已禁用（LA-2 DEC-1）。

        方法本體 fail-closed：直呼亦 raise，不保留可跑洩漏碼。
        """
        raise NotImplementedError(WINSORIZED_DISABLED_MSG)

    def generate_returns_by_type(
        self,
        close: pd.Series,
        horizon: int,
        return_type: str,
        benchmark_close: pd.Series | None = None,
    ) -> pd.Series:
        """Dispatch return generation by return_type.

        winsorized → NotImplementedError(LOOKAHEAD_LABEL_UNSUPPORTED)（LA-2 DEC-1）。
        """
        if return_type == "winsorized":
            raise NotImplementedError(WINSORIZED_DISABLED_MSG)
        dispatch = {
            "simple": lambda: self.generate_return(close, horizon),
            "log": lambda: self.generate_log_return(close, horizon),
            "excess": lambda: self.generate_excess_return(close, benchmark_close, horizon),
            "risk_adjusted": lambda: self.generate_risk_adjusted_return(close, horizon),
        }
        if return_type not in dispatch:
            logger.error("Unsupported return_type: %s", return_type)
            raise ValueError(f"Unsupported return_type: {return_type}")
        return dispatch[return_type]()

    def horizon_to_bars(self, time_duration: str, timeframe: str) -> int:
        """Convert time_duration to bar count for a given timeframe."""
        duration_hours = self._parse_duration_to_hours(time_duration)
        timeframe_hours = self._parse_duration_to_hours(timeframe)
        if duration_hours % timeframe_hours != 0:
            logger.error("time_duration %s is not aligned with timeframe %s", time_duration, timeframe)
            raise ValueError("time_duration is not aligned with timeframe")
        return int(duration_hours / timeframe_hours)

    @staticmethod
    def _parse_duration_to_hours(duration: str) -> int:
        """Parse duration string like 12h/1d/1w into hours."""
        value = duration.strip().lower()
        if not value:
            logger.error("Empty duration string")
            raise ValueError("duration is required")
        number = ""
        unit = ""
        for char in value:
            if char.isdigit():
                number += char
            else:
                unit += char
        if not number or unit not in {"h", "d", "w"}:
            logger.error("Invalid duration format: %s", duration)
            raise ValueError("Invalid duration format")
        count = int(number)
        if count <= 0:
            logger.error("Duration must be positive: %s", duration)
            raise ValueError("Duration must be positive")
        if unit == "h":
            return count
        if unit == "d":
            return count * 24
        return count * 7 * 24
