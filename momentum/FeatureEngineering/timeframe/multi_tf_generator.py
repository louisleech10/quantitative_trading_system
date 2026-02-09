"""Multi-timeframe feature generation."""

from __future__ import annotations

from typing import Iterable, List

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


logger = get_logger(__name__)


class MultiTFGenerator:
    """Multi-timeframe feature generation orchestrator."""

    def __init__(self, feature_factory: "FeatureFactory", config: "FactoryConfig") -> None:
        self._factory = feature_factory
        self._config = config
        self._primary_tf = config.timeframes.primary
        self._training_tfs = list(dict.fromkeys(config.timeframes.training))

    def generate_multi_tf(self, symbol: str) -> pd.DataFrame:
        """Generate features across training timeframes and align to primary."""
        training_tfs = self._ensure_primary(self._training_tfs, self._primary_tf)

        try:
            primary_raw = self._factory._layer0_data_ingestion(symbol, self._primary_tf, self._config)
        except Exception as exc:
            logger.error("Primary TF ingestion failed for %s/%s: %s", symbol, self._primary_tf, exc, exc_info=True)
            return pd.DataFrame()

        primary_timestamps = TimeframeAligner._to_datetime_index(
            TimeframeAligner._split_timestamp_index(primary_raw)[0]
        )
        if primary_timestamps.empty:
            logger.error("Primary timestamps empty for %s/%s", symbol, self._primary_tf)
            return pd.DataFrame()

        aligned_outputs: List[pd.DataFrame] = []

        for timeframe in training_tfs:
            try:
                raw_data = (
                    primary_raw
                    if timeframe == self._primary_tf
                    else self._factory._layer0_data_ingestion(symbol, timeframe, self._config)
                )
                layer1 = self._factory._layer1_atomic_indicators(raw_data, self._config)
                layer2 = self._factory._layer2_derived_features(layer1, raw_data, self._config)
                layer3 = self._factory._layer3_rolling_aggregation(layer1, layer2, self._config)
                layer4 = self._factory._layer4_lag_features(layer1, layer2, layer3, raw_data, self._config)
                layer5 = self._factory._layer5_cross_sectional(layer1, layer2, self._config)
                layer6 = self._factory._layer6_meta_features(layer1, layer2, raw_data, self._config)
            except Exception as exc:
                logger.error("Multi-TF pipeline failed for %s/%s: %s", symbol, timeframe, exc, exc_info=True)
                continue

            combined = self._combine_layers([layer1, layer2, layer3, layer4, layer5, layer6])
            aligned = TimeframeAligner.align_to_primary(
                combined,
                timeframe,
                primary_timestamps,
                self._primary_tf,
            )
            aligned.attrs = {}
            if timeframe != self._primary_tf:
                aligned = self._apply_timeframe_tag(aligned, timeframe)
            aligned_outputs.append(aligned)

        if not aligned_outputs:
            return pd.DataFrame(index=primary_timestamps)

        return pd.concat(aligned_outputs, axis=1)

    @staticmethod
    def _combine_layers(layers: Iterable[pd.DataFrame]) -> pd.DataFrame:
        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()
        return pd.concat(valid_layers, axis=1)

    @staticmethod
    def _apply_timeframe_tag(features_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if features_df is None or features_df.empty:
            return features_df

        tf_keys = TimeframeAligner._timeframe_seconds_keys()

        def _rename(col: str) -> str:
            if col.startswith("meta_") or col.startswith("label_"):
                return col
            parts = col.split("_")
            if len(parts) < 2:
                return col
            if parts[1] in tf_keys:
                return col
            return "_".join([parts[0], timeframe] + parts[1:])

        rename_map = {col: _rename(col) for col in features_df.columns}
        return features_df.rename(columns=rename_map)

    @staticmethod
    def _ensure_primary(training_tfs: List[str], primary_tf: str) -> List[str]:
        if primary_tf in training_tfs:
            return training_tfs
        return [primary_tf] + training_tfs


# Type checking only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_config import FactoryConfig
