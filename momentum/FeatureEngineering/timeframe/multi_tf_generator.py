"""Multi-timeframe feature generation."""

from __future__ import annotations

import gc
import os
import time
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional

import numpy as np
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

    def generate_multi_tf(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> "FeatureGenerationResult":
        """Generate features across training timeframes and align to primary."""
        start_time = time.time()

        try:
            primary_raw = self._factory._layer0_data_ingestion(
                symbol,
                self._primary_tf,
                self._config,
                start_date=start_date,
                end_date=end_date,
            )
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

        use_cgsa = self._cgsa_enabled() and getattr(self._factory, "_cgsa_registry", None) is not None
        if use_cgsa:
            return self._generate_multi_tf_cgsa(
                symbol, primary_raw, primary_timestamps, start_time,
                start_date=start_date, end_date=end_date,
            )

        return self._generate_multi_tf_legacy(
            symbol, primary_raw, primary_timestamps, start_time,
            start_date=start_date, end_date=end_date,
        )

    # ------------------------------------------------------------------
    # CGSA path: per-group registry, no global concat
    # ------------------------------------------------------------------
    def _generate_multi_tf_cgsa(
        self,
        symbol: str,
        primary_raw: pd.DataFrame,
        primary_timestamps: pd.DatetimeIndex,
        start_time: float,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> "FeatureGenerationResult":
        """CGSA multi-TF: compute layers per TF, align registry groups, then L6.5 + L7."""
        from momentum.FeatureEngineering.feature_config import AlignmentMode

        registry = self._factory._cgsa_registry
        skipped_tfs: List[str] = []
        tf_layer_counts: Dict[str, Dict[str, int]] = {}
        total_tfs = len(self._training_tfs)

        for index, timeframe in enumerate(self._training_tfs):
            self._report_progress(
                "multi_tf",
                ((index + 1) / max(total_tfs, 1)) * 0.7,
                f"[CGSA] Processing timeframe {timeframe} ({index + 1}/{total_tfs})",
            )

            try:
                raw_data = (
                    primary_raw
                    if timeframe == self._primary_tf
                    else self._factory._layer0_data_ingestion(
                        symbol, timeframe, self._config,
                        start_date=start_date, end_date=end_date,
                    )
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

            # Record groups before this TF runs so we know which were added.
            groups_before = set(registry._groups.keys())

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
            del layer1, layer2, layer3, layer4, layer5, layer6
            gc.collect()

            new_group_ids = sorted(set(registry._groups.keys()) - groups_before)

            if timeframe == self._primary_tf:
                logger.info(
                    "[CGSA][multi_tf] Primary TF %s: %d groups registered (no alignment needed)",
                    timeframe, len(new_group_ids),
                )
            else:
                # Align each new group from source TF rows to primary TF rows.
                source_index, _ = TimeframeAligner._split_timestamp_index(raw_data)
                source_dt = TimeframeAligner._to_datetime_index(source_index)

                alignment_mode = self._config.timeframes.alignment_mode
                offset_ns = -1 if alignment_mode == AlignmentMode.OPEN_MINUS else 0

                source_ms = (source_dt.to_numpy(dtype="datetime64[ns]").astype(np.int64) // 1_000_000).astype(np.int64)
                primary_ms = (primary_timestamps.to_numpy(dtype="datetime64[ns]").astype(np.int64) // 1_000_000).astype(np.int64)
                idx_map = TimeframeAligner.build_asof_index_map(primary_ms, source_ms, offset_ns=offset_ns)

                n_primary = len(primary_timestamps)
                aligned_count = 0
                for gid in new_group_ids:
                    group = registry.get(gid)
                    src_data = np.asarray(registry.load_data(gid), dtype=np.float32)
                    aligned_arr = self._align_group_array(src_data, idx_map, n_primary)
                    registry.overwrite_data(gid, aligned_arr)
                    aligned_count += 1

                logger.info(
                    "[CGSA][multi_tf] Aligned %d groups from %s → %s (idx_map built once)",
                    aligned_count, timeframe, self._primary_tf,
                )

        if self._primary_tf in skipped_tfs:
            raise ValueError(f"Primary timeframe data missing for {symbol}/{self._primary_tf}")

        total_groups = len(list(registry.iter_all()))
        if total_groups == 0:
            raise ValueError(f"All training timeframes skipped for {symbol}")

        logger.info("[CGSA][multi_tf] All TFs done: %d total groups in registry", total_groups)

        # L6.5 preprocessing via registry (per-group)
        if self._config.preprocessing.enabled:
            self._report_progress("preprocessing", 0.75, "[CGSA] Running Layer 6.5 per-group preprocessing")
            self._factory._layer6_5_preprocessing(pd.DataFrame(), self._config)

        # L7 validate + persist via registry
        self._report_progress("persist", 0.9, "[CGSA] Running Layer 7 per-group validate and persist")
        config_hash = self._factory._compute_config_hash(
            self._config, symbol, self._primary_tf,
            start_date=start_date, end_date=end_date,
        )
        elapsed = time.time() - start_time
        result = self._factory._layer7_validate_and_persist(
            symbol=symbol,
            timeframe=self._primary_tf,
            raw_data=primary_raw,
            layers=[pd.DataFrame()],
            config=self._config,
            elapsed=elapsed,
            config_hash=config_hash,
        )

        total_layer_counts = self._build_total_layer_counts(tf_layer_counts)
        result.layer_counts = total_layer_counts
        result.metadata["layer_counts"] = total_layer_counts
        result.metadata["skipped_timeframes"] = skipped_tfs
        result.metadata["actual_timeframes"] = [
            tf for tf in self._training_tfs if tf not in skipped_tfs
        ]

        self._report_progress("complete", 1.0, f"[CGSA] MultiTF generation completed ({elapsed:.2f}s)")
        return result

    @staticmethod
    def _align_group_array(
        src_data: np.ndarray,
        idx_map: np.ndarray,
        n_primary: int,
    ) -> np.ndarray:
        """Align a 2D group array from source rows to primary rows using precomputed idx_map."""
        n_cols = src_data.shape[1]
        out = np.full((n_primary, n_cols), np.nan, dtype=np.float32)
        valid = idx_map >= 0
        if np.any(valid):
            out[valid] = src_data[idx_map[valid]]
        return out

    # ------------------------------------------------------------------
    # Legacy path: wide DataFrame concat + alignment (non-CGSA)
    # ------------------------------------------------------------------
    def _generate_multi_tf_legacy(
        self,
        symbol: str,
        primary_raw: pd.DataFrame,
        primary_timestamps: pd.DatetimeIndex,
        start_time: float,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> "FeatureGenerationResult":
        """Legacy multi-TF: combine layers into wide DF, align, then L6.5 + L7."""
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
                    else self._factory._layer0_data_ingestion(
                        symbol, timeframe, self._config,
                        start_date=start_date, end_date=end_date,
                    )
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

                # Spill layer2 to memmap before L3 to avoid OOM on 8 GB M1.
                # In single-TF path this is done in feature_factory.py; multi-TF
                # calls layer methods directly so we must spill here too.
                layer2 = self._factory._spill_to_memmap(layer2, "layer2")

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
            del layer1, layer2, layer3, layer4, layer5, layer6
            gc.collect()
            if timeframe == self._primary_tf:
                if len(combined.index) != len(primary_timestamps):
                    raise ValueError(
                        f"Primary self-alignment length mismatch: combined={len(combined.index)} "
                        f"primary={len(primary_timestamps)}"
                    )
                logger.info(
                    "[multi_tf] Skipping self-alignment for primary TF %s (%d cols)",
                    timeframe, combined.shape[1],
                )
                aligned = combined.copy(deep=False)
                aligned.index = primary_timestamps
            else:
                aligned = TimeframeAligner.align_to_primary(
                    combined, timeframe, primary_timestamps,
                    self._primary_tf, self._config.timeframes.alignment_mode,
                )
            aligned.attrs = {}
            aligned = self._apply_timeframe_tag(
                aligned, timeframe,
                registry=getattr(self._factory, "_cgsa_registry", None),
            )
            aligned_outputs.append(aligned)

        if self._primary_tf in skipped_tfs:
            raise ValueError(f"Primary timeframe data missing for {symbol}/{self._primary_tf}")

        if not aligned_outputs:
            raise ValueError(f"All training timeframes skipped for {symbol}")

        merged_df = self._factory._combine_layers(aligned_outputs, context="multi_tf_merged")
        if merged_df.empty:
            raise ValueError(f"Merged MultiTF features empty for {symbol}")

        if len(merged_df.index) == len(primary_raw.index):
            merged_df.index = primary_raw.index

        if self._config.preprocessing.enabled:
            self._report_progress("preprocessing", 0.75, "Running Layer 6.5 preprocessing")
            merged_df = self._factory._layer6_5_preprocessing(merged_df, self._config)

        self._report_progress("persist", 0.9, "Running Layer 7 validate and persist")
        config_hash = self._factory._compute_config_hash(
            self._config, symbol, self._primary_tf,
            start_date=start_date, end_date=end_date,
        )
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
            tf for tf in self._training_tfs if tf not in skipped_tfs
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
        if MultiTFGenerator._cgsa_enabled():
            logger.info("[CGSA] Skip MultiTFGenerator._combine_layers (registry-based path)")
            return pd.DataFrame()

        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()

        from momentum.FeatureEngineering.memmap_utils import concat_with_memmap

        return concat_with_memmap(valid_layers)

    @staticmethod
    def _apply_timeframe_tag(
        features_df: pd.DataFrame,
        timeframe: str,
        registry: Optional[object] = None,
    ) -> pd.DataFrame:
        if features_df is None or features_df.empty:
            return features_df

        if registry is not None and MultiTFGenerator._cgsa_enabled():
            return features_df

        tf_keys = TimeframeAligner._timeframe_seconds_keys()

        def _rename(col: str) -> str:
            if col.startswith("label_"):
                return col  # Labels come from primary TF only, no TF tag needed
            # meta_ columns MUST be tagged with TF prefix (meta_1h_*, meta_12h_*)
            # to avoid duplicate column names when merging multi-TF outputs.
            parts = col.split("_")
            if len(parts) < 2:
                return col
            if parts[1] in tf_keys:
                return col
            return "_".join([parts[0], timeframe] + parts[1:])

        rename_map = {col: _rename(col) for col in features_df.columns}
        return features_df.rename(columns=rename_map)

    @staticmethod
    def _cgsa_enabled() -> bool:
        raw = os.getenv("FFACT_USE_CGSA", "1").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def _ensure_primary(self, training_tfs: List[str]) -> List[str]:
        deduped = list(dict.fromkeys(training_tfs))
        if self._primary_tf in deduped:
            return deduped
        return deduped + [self._primary_tf]

if TYPE_CHECKING:
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_config import FactoryConfig
    from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
