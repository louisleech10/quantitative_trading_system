"""Multi-timeframe feature generation."""

from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


logger = get_logger(__name__)


class MultiTFGenerator:
    """Multi-timeframe feature generation orchestrator."""

    def __init__(
        self,
        feature_factory: "FeatureFactory",
        config: "FactoryConfig",
        progress_callback=None,
    ) -> None:
        self._factory = feature_factory
        self._config = config
        self._primary_tf = config.timeframes.primary
        self._training_tfs = self._ensure_primary(list(dict.fromkeys(config.timeframes.training)))
        self._progress_callback = progress_callback

    def generate_multi_tf(self, symbol: str) -> "FeatureGenerationResult":
        """Generate features across training timeframes and align to primary."""
        start_time = time.time()

        try:
            primary_raw = self._factory._layer0_data_ingestion(symbol, self._primary_tf, self._config)
        except FileNotFoundError as exc:
            logger.error(
                "Primary TF ingestion failed for %s/%s: %s",
                symbol,
                self._primary_tf,
                exc,
                exc_info=True,
            )
            raise ValueError(f"Primary timeframe data missing for {symbol}/{self._primary_tf}") from exc
        except Exception as exc:
            logger.error("Primary TF ingestion failed for %s/%s: %s", symbol, self._primary_tf, exc, exc_info=True)
            raise

        primary_timestamps = TimeframeAligner._to_datetime_index(
            TimeframeAligner._split_timestamp_index(primary_raw)[0]
        )
        if primary_timestamps.empty:
            raise ValueError(f"Primary timestamps empty for {symbol}/{self._primary_tf}")

        aligned_outputs: List[pd.DataFrame] = []
        skipped_tfs: List[str] = []
        tf_layer_counts: Dict[str, Dict[str, int]] = {}
        total_tfs = len(self._training_tfs)

        for index, timeframe in enumerate(self._training_tfs):
            self._report_progress(
                "multi_tf",
                ((index + 1) / max(total_tfs, 1)) * 0.7,
                f"Processing timeframe {timeframe} ({index + 1}/{total_tfs})",
            )

            try:
                raw_data = (
                    primary_raw
                    if timeframe == self._primary_tf
                    else self._factory._layer0_data_ingestion(symbol, timeframe, self._config)
                )
            except FileNotFoundError:
                logger.warning("MultiTF: missing data for %s/%s, skipping timeframe", symbol, timeframe)
                skipped_tfs.append(timeframe)
                continue
            except Exception as exc:
                logger.error("MultiTF: load failed for %s/%s: %s", symbol, timeframe, exc, exc_info=True)
                skipped_tfs.append(timeframe)
                continue

            if raw_data is None or raw_data.empty:
                logger.warning("MultiTF: empty data for %s/%s, skipping timeframe", symbol, timeframe)
                skipped_tfs.append(timeframe)
                continue

            try:
                layer1 = self._factory._layer1_atomic_indicators(raw_data, self._config)
                layer2 = self._factory._layer2_derived_features(layer1, raw_data, self._config)
                layer3 = self._factory._layer3_rolling_aggregation(layer1, layer2, self._config)
                layer4 = self._factory._layer4_lag_features(layer1, layer2, layer3, raw_data, self._config)
                layer5 = self._factory._layer5_cross_sectional(layer1, layer2, self._config)
                layer6 = self._factory._layer6_meta_features(layer1, layer2, raw_data, self._config)
            except Exception as exc:
                logger.error("Multi-TF pipeline failed for %s/%s: %s", symbol, timeframe, exc, exc_info=True)
                skipped_tfs.append(timeframe)
                continue

            tf_layer_counts[timeframe] = self._collect_layer_counts(
                [layer1, layer2, layer3, layer4, layer5, layer6]
            )

            combined = self._combine_layers([layer1, layer2, layer3, layer4, layer5, layer6])
            aligned = TimeframeAligner.align_to_primary(
                combined,
                timeframe,
                primary_timestamps,
                self._primary_tf,
                self._config.timeframes.alignment_mode,
            )
            aligned.attrs = {}
            if timeframe != self._primary_tf:
                aligned = self._apply_timeframe_tag(aligned, timeframe)
            aligned_outputs.append(aligned)

        if self._primary_tf in skipped_tfs:
            raise ValueError(f"Primary timeframe data missing for {symbol}/{self._primary_tf}")

        if not aligned_outputs:
            raise ValueError(f"All training timeframes skipped for {symbol}")

        merged_df = self._factory._combine_layers(aligned_outputs, context="multi_tf_merged")
        if merged_df.empty:
            raise ValueError(f"Merged MultiTF features empty for {symbol}")

        if len(merged_df.index) == len(primary_raw.index):
            # Layer 7 reindexes by raw_data.index; keep index space consistent with single-TF path.
            merged_df.index = primary_raw.index

        if self._config.preprocessing.enabled:
            self._report_progress("preprocessing", 0.75, "Running Layer 6.5 preprocessing")
            merged_df = self._factory._layer6_5_preprocessing(merged_df, self._config)

        self._report_progress("persist", 0.9, "Running Layer 7 validate and persist")
        config_hash = self._factory._compute_config_hash(self._config)
        elapsed = time.time() - start_time
        result = self._factory._layer7_validate_and_persist(
            symbol=symbol,
            timeframe=self._primary_tf,
            raw_data=primary_raw,
            layers=[merged_df],
            config=self._config,
            elapsed=elapsed,
            config_hash=config_hash,
        )

        total_layer_counts = self._build_total_layer_counts(tf_layer_counts)
        result.layer_counts = total_layer_counts
        result.metadata["layer_counts"] = total_layer_counts
        result.metadata["skipped_timeframes"] = skipped_tfs
        result.metadata["actual_timeframes"] = [
            timeframe for timeframe in self._training_tfs if timeframe not in skipped_tfs
        ]

        self._report_progress("complete", 1.0, f"MultiTF generation completed ({elapsed:.2f}s)")
        return result

    def _report_progress(self, stage: str, progress: float, message: str) -> None:
        if self._progress_callback:
            self._progress_callback({"stage": stage, "progress": progress, "message": message})
        logger.info("[multi_tf:%s] %0.0f%% - %s", stage, progress * 100, message)

    @staticmethod
    def _collect_layer_counts(layers: Iterable[pd.DataFrame]) -> Dict[str, int]:
        layer_list = list(layers)
        return {
            "layer1": layer_list[0].shape[1] if len(layer_list) > 0 and layer_list[0] is not None else 0,
            "layer2": layer_list[1].shape[1] if len(layer_list) > 1 and layer_list[1] is not None else 0,
            "layer3": layer_list[2].shape[1] if len(layer_list) > 2 and layer_list[2] is not None else 0,
            "layer4": layer_list[3].shape[1] if len(layer_list) > 3 and layer_list[3] is not None else 0,
            "layer5": layer_list[4].shape[1] if len(layer_list) > 4 and layer_list[4] is not None else 0,
            "layer6": layer_list[5].shape[1] if len(layer_list) > 5 and layer_list[5] is not None else 0,
        }

    def _build_total_layer_counts(self, tf_layer_counts: Dict[str, Dict[str, int]]) -> Dict[str, int]:
        total_layer_counts: Dict[str, int] = {}
        for timeframe, counts in tf_layer_counts.items():
            for layer_name, count in counts.items():
                key = layer_name if timeframe == self._primary_tf else f"{layer_name}_{timeframe}"
                total_layer_counts[key] = count
        return total_layer_counts

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

    def _ensure_primary(self, training_tfs: List[str]) -> List[str]:
        deduped = list(dict.fromkeys(training_tfs))
        if self._primary_tf in deduped:
            return deduped
        return deduped + [self._primary_tf]


# Type checking only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_config import FactoryConfig
    from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
