"""FeatureLibrary - unified read-only interface for consuming generated features."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from momentum.core.contracts import FeatureLibraryEntry, FeatureNotFoundError
from momentum.core.logging import get_logger
from momentum.FeatureEngineering.consumer_gate import (
    TrainingReadError,
    assert_consumer_run_status,
    assert_required_columns_present,
)
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage

logger = get_logger(__name__)


class FeatureLibrary:
    """Read-only facade for accessing generated features.

    V7: delegates loading to FeatureReader (Parquet-only) when per-group
    Parquet output is available.  Falls back to legacy HDF5 via
    FeatureStorage only when no manifest.json exists.
    """

    def __init__(
        self,
        registry: FeatureRegistry,
        storage: FeatureStorage,
        feature_reader: Optional[FeatureReader] = None,
    ) -> None:
        self._registry = registry
        self._storage = storage
        self._reader = feature_reader or FeatureReader(str(storage.base_path))

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

    def load(
        self,
        symbol: str,
        timeframe: str,
        *,
        config_hash: Optional[str] = None,
        for_training: bool = False,
        allow_partial_training: bool = False,
    ) -> pd.DataFrame:
        """Load latest features for a symbol/timeframe pair.

        V7: tries FeatureReader (Parquet) first; falls back to legacy HDF5.
        """
        return self._load_internal(
            symbol,
            timeframe,
            config_hash=config_hash,
            for_training=for_training,
            allow_partial_training=allow_partial_training,
        )

    def load_for_training(
        self,
        symbol: str,
        timeframe: str,
        *,
        allow_partial_training: bool = False,
    ) -> pd.DataFrame:
        """Strict consumer load for ML/training paths."""
        return self._load_internal(
            symbol,
            timeframe,
            for_training=True,
            allow_partial_training=allow_partial_training,
        )

    def _load_internal(
        self,
        symbol: str,
        timeframe: str,
        *,
        config_hash: Optional[str] = None,
        for_training: bool,
        allow_partial_training: bool,
    ) -> pd.DataFrame:
        if config_hash:
            entry = self._registry.get(symbol, timeframe, config_hash)
            if entry is None:
                raise FeatureNotFoundError(
                    symbol,
                    timeframe,
                    f"config_hash not found: {config_hash}",
                )
        else:
            entry = self._registry.find_latest_materialized(symbol, timeframe)
            if entry is None:
                raise FeatureNotFoundError(
                    symbol,
                    timeframe,
                    "No materialized registry entry",
                )

        resolved_hash = entry.get("config_hash", "")
        explicit_hash = bool(config_hash)

        if resolved_hash:
            try:
                manifest = self._reader.load_manifest_v2(
                    symbol,
                    timeframe,
                    resolved_hash,
                    artifact_kind="raw",
                    consumer="strict" if for_training else "browse",
                    allow_partial=allow_partial_training,
                )
                columns = self._reader.list_features_v2(
                    symbol,
                    timeframe,
                    resolved_hash,
                    artifact_kind="raw",
                    consumer="strict" if for_training else "browse",
                    allow_partial=allow_partial_training,
                )
                if columns:
                    features_df = self._reader.load_columns_v2(
                        symbol,
                        timeframe,
                        resolved_hash,
                        columns,
                        artifact_kind="raw",
                        consumer="strict" if for_training else "browse",
                        allow_partial=allow_partial_training,
                    )
                    if not features_df.empty:
                        if for_training:
                            assert_consumer_run_status(
                                manifest,
                                consumer="strict",
                                allow_partial=allow_partial_training,
                                error_type=TrainingReadError,
                            )
                        logger.info(
                            "Loaded features via FeatureReader for %s/%s: %d rows x %d cols "
                            "(run_status=%s)",
                            symbol,
                            timeframe,
                            len(features_df),
                            len(features_df.columns),
                            manifest.get("run_status", manifest.get("quality_status")),
                        )
                        return features_df
            except FileNotFoundError:
                if explicit_hash:
                    raise FeatureNotFoundError(
                        symbol,
                        timeframe,
                        f"V2 artifacts missing for config_hash: {resolved_hash}",
                    ) from None

        if explicit_hash:
            raise FeatureNotFoundError(
                symbol,
                timeframe,
                f"artifacts missing for config_hash: {resolved_hash}",
            )

        result = self._storage.load_factory_output(symbol, timeframe)
        features_df = getattr(result, "features_df", None) if result is not None else None
        if features_df is None or features_df.empty:
            raise FeatureNotFoundError(symbol, timeframe, "HDF5 file missing or empty")

        metadata = getattr(result, "metadata", None) or {}
        if for_training:
            from momentum.FeatureEngineering.consumer_gate import effective_run_status_from_metadata

            run_status = effective_run_status_from_metadata(metadata)
            if run_status != "complete" and not (allow_partial_training and run_status == "partial"):
                raise TrainingReadError(
                    f"run_status={run_status!r} is not consumable for training "
                    f"(allow_partial_training={allow_partial_training})"
                )

        logger.info(
            "Loaded features for %s/%s: %d rows x %d cols",
            symbol,
            timeframe,
            len(features_df),
            len(features_df.columns),
        )
        return features_df

    def load_multi(
        self,
        symbols: List[str],
        timeframe: str,
        *,
        config_hashes: Optional[Dict[str, str]] = None,
        for_training: bool = False,
        allow_partial_training: bool = False,
        feature_columns: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Load features for multiple symbols. Raises if any symbol is missing."""
        loaded: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            symbol_hash = (config_hashes or {}).get(symbol)
            if config_hashes is not None and symbol not in config_hashes:
                logger.warning(
                    "config_hashes missing symbol %s/%s; falling back to find_latest",
                    symbol,
                    timeframe,
                )
            loaded[symbol] = self.load(
                symbol,
                timeframe,
                config_hash=symbol_hash,
                for_training=for_training,
                allow_partial_training=allow_partial_training,
            )
        if feature_columns:
            assert_required_columns_present(loaded, feature_columns, error_type=TrainingReadError)
        return loaded

    def ensure_fresh(self, symbol: str, timeframe: str, current_config_hash: str) -> bool:
        """Return whether latest cached entry matches given config hash."""
        entry = self._registry.find_latest_materialized(symbol, timeframe)
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
