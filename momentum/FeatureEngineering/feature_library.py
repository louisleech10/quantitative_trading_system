"""FeatureLibrary - unified read-only interface for consuming generated features."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from momentum.core.contracts import FeatureLibraryEntry, FeatureNotFoundError
from momentum.core.logging import get_logger
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage

logger = get_logger(__name__)


class FeatureLibrary:
    """Read-only facade for accessing generated features."""

    def __init__(
        self,
        registry: FeatureRegistry,
        storage: FeatureStorage,
    ) -> None:
        self._registry = registry
        self._storage = storage

    def list_available(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> List[FeatureLibraryEntry]:
        """List all available feature sets, optionally filtered."""
        entries = self._registry.list_all()
        if symbol:
            entries = [entry for entry in entries if entry.get("symbol") == symbol]
        if timeframe:
            entries = [entry for entry in entries if entry.get("timeframe") == timeframe]
        return [self._to_entry(entry) for entry in entries]

    def load(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load latest features for a symbol/timeframe pair."""
        entry = self._registry.find_latest(symbol, timeframe)
        if entry is None:
            raise FeatureNotFoundError(symbol, timeframe, "No registry entry")

        result = self._storage.load_factory_output(symbol, timeframe)
        features_df = getattr(result, "features_df", None) if result is not None else None
        if features_df is None or features_df.empty:
            raise FeatureNotFoundError(symbol, timeframe, "HDF5 file missing or empty")

        logger.info(
            "Loaded features for %s/%s: %d rows x %d cols",
            symbol,
            timeframe,
            len(features_df),
            len(features_df.columns),
        )
        return features_df

    def load_multi(self, symbols: List[str], timeframe: str) -> Dict[str, pd.DataFrame]:
        """Load features for multiple symbols. Raises if any symbol is missing."""
        loaded: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            loaded[symbol] = self.load(symbol, timeframe)
        return loaded

    def ensure_fresh(self, symbol: str, timeframe: str, current_config_hash: str) -> bool:
        """Return whether latest cached entry matches given config hash."""
        entry = self._registry.find_latest(symbol, timeframe)
        if entry is None:
            return False
        return entry.get("config_hash") == current_config_hash

    @staticmethod
    def _to_entry(raw: Dict) -> FeatureLibraryEntry:
        return FeatureLibraryEntry(
            symbol=raw.get("symbol", ""),
            timeframe=raw.get("timeframe", ""),
            config_hash=raw.get("config_hash", ""),
            feature_count=raw.get("feature_count", 0),
            row_count=raw.get("row_count", 0),
            created_at=raw.get("created_at", 0.0),
            hdf5_relative_path=raw.get("hdf5_relative_path", ""),
        )
