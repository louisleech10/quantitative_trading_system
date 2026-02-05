"""Momentum cross-domain protocols."""

from __future__ import annotations

from typing import Protocol, Iterable, Any, Dict, Optional, runtime_checkable


@runtime_checkable
class IKlineReader(Protocol):
    """Read kline data by symbol/timeframe and optional time range."""

    def read_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        validate_continuity: bool = False,
    ) -> Any:
        ...

    def read_klines_around_timestamp(
        self,
        symbol: str,
        timeframe: str,
        center_timestamp: int,
        lookback: int,
        forward: int,
    ) -> Any:
        ...

    def get_metadata(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        ...


@runtime_checkable
class IIndicatorEngine(Protocol):
    """Indicator calculation engine interface."""

    def calculate_indicators_from_dataframe(
        self,
        kline_df: Any,
        configs: Iterable[Dict[str, Any]],
    ) -> Any:
        ...


@runtime_checkable
class IModelTrainer(Protocol):
    """Model training interface for analysis/optimization."""

    def train_model(
        self,
        features: Any,
        labels: Any,
        feature_names: Iterable[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        ...
