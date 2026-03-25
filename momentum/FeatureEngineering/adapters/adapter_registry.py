from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.adapters.base_adapter import DataSourceAdapter

logger = get_logger(__name__)


class AdapterRegistry:
    """Instance-level registry for data source adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, DataSourceAdapter] = {}

    def register(self, adapter: DataSourceAdapter) -> None:
        self._adapters[adapter.name] = adapter
        logger.info(f"Registered adapter: {adapter.name}")

    def get(self, name: str) -> DataSourceAdapter:
        if name not in self._adapters:
            raise KeyError(f"Adapter not found: {name}")
        return self._adapters[name]

    def list_all(self) -> List[str]:
        return sorted(self._adapters.keys())

    def get_all_fields(self) -> Dict[str, List[str]]:
        return {name: adapter.available_fields for name, adapter in self._adapters.items()}

    def get_all_single_series_fields(self) -> List[str]:
        fields = set()
        for adapter in self._adapters.values():
            fields.update(adapter.get_single_series_fields())
        return sorted(fields)

    def fetch_aligned(
        self,
        symbol: str,
        timeframe: str,
        enabled_sources: List[str],
    ) -> pd.DataFrame:
        if not self._adapters:
            raise ValueError("No adapters registered")

        frames = []
        for adapter in self._adapters.values():
            df = adapter.fetch(symbol, timeframe)
            columns = [col for col in enabled_sources if col in df.columns]
            if not columns:
                continue
            frames.append(df[columns])

        if not frames:
            raise ValueError("No data returned from adapters")

        aligned = pd.concat(frames, axis=1, join="inner")
        aligned = aligned.loc[:, ~aligned.columns.duplicated()]
        aligned = aligned.sort_index()

        logger.info(
            f"Aligned data for {symbol}/{timeframe}: {len(aligned)} rows, {len(aligned.columns)} columns"
        )
        return aligned

    def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
        """Return the latest timestamp across all registered adapters."""
        latest: Optional[int] = None
        for adapter in self._adapters.values():
            ts = adapter.get_last_timestamp(symbol, timeframe)
            if ts is not None and (latest is None or ts > latest):
                latest = ts
        return latest
