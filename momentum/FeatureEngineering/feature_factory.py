"""Feature factory pipeline skeleton for FeatureEngineering."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Tuple, Any

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.feature_validator import FeatureValidator
from momentum.FeatureEngineering.labels.label_generator import LabelGenerator
from momentum.FeatureEngineering.meta_features.consensus_features import ConsensusFeatureEngine
from momentum.FeatureEngineering.meta_features.interaction_features import InteractionFeatureEngine
from momentum.FeatureEngineering.meta_features.time_features import TimeFeatureEngine
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from momentum.FeatureEngineering.cross_sectional.relative_strength import RelativeStrengthProcessor
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.atomic.momentum_indicators import MomentumIndicatorEngine
from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine
from momentum.FeatureEngineering.atomic.cycle_indicators import CycleIndicatorEngine
from momentum.FeatureEngineering.atomic.pattern_indicators import PatternIndicatorEngine
from momentum.FeatureEngineering.atomic.statistics_indicators import StatisticsIndicatorEngine
from momentum.FeatureEngineering.atomic.custom_indicators import CustomIndicatorEngine
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


logger = get_logger(__name__)

if TYPE_CHECKING:
    from momentum.FeatureEngineering.feature_config import FactoryConfig


@dataclass
class FeatureGenerationResult:
    features_df: pd.DataFrame
    labels_df: pd.DataFrame
    metadata: Dict
    feature_count: int
    generation_time: float
    layer_counts: Dict[str, int]
    config_used: Dict
    hdf5_path: Optional[str] = None


class FeatureFactory:
    """Seven-layer feature pipeline orchestrator.

    Layer 0: Data ingestion -> Adapter fetch + synthetic fields
    Layer 1: Atomic indicators -> 7 indicator engines
    Layer 2: Derived features -> DerivedOperatorEngine
    Layer 3: Rolling aggregation -> RollingAggregator
    Layer 4: Lag features -> LagProcessor
    Layer 5: Cross-sectional -> RelativeStrengthProcessor
    Layer 6: Meta features -> Consensus/Time/Interaction
    Layer 7: Validation & persistence -> FeatureValidator + FeatureStorage
    """

    def __init__(self, config_manager: ConfigManager, adapter_registry: AdapterRegistry) -> None:
        self._config_manager = config_manager
        self._adapter_registry = adapter_registry
        self._progress_callback: Optional[Callable] = None
        self._storage = FeatureStorage()
        self._validator = FeatureValidator()
        self._current_symbol: Optional[str] = None
        self._current_timeframe: Optional[str] = None
        self._current_raw_data: Optional[pd.DataFrame] = None
        self._reference_data_cache: Dict[Tuple[str, str], pd.DataFrame] = {}

    def generate_features(
        self,
        symbol: str,
        timeframe: str,
        config_override: Optional[dict] = None,
        force_regenerate: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> FeatureGenerationResult:
        """Run the seven-layer pipeline.

        force_regenerate=True skips cache and forces recalculation.
        Layer 0 failure stops the pipeline. Layer 1-6 failures return empty DataFrame.
        """
        config = self._resolve_config(config_override)
        self._progress_callback = progress_callback
        self._current_symbol = symbol
        self._current_timeframe = timeframe
        start_time = time.time()

        config_hash = self._compute_config_hash(config)
        if not force_regenerate:
            cached = self._try_load_cache(symbol, timeframe, config_hash)
            if cached:
                return cached

        try:
            raw_data = self._layer0_data_ingestion(symbol, timeframe, config)
        except Exception as exc:
            logger.error(
                "Layer 0 failed for %s/%s: %s",
                symbol,
                timeframe,
                exc,
                exc_info=True,
            )
            raise

        self._current_raw_data = raw_data

        layer1 = self._safe_execute("Layer 1", self._layer1_atomic_indicators, raw_data, config)
        layer2 = self._safe_execute("Layer 2", self._layer2_derived_features, layer1, raw_data, config)
        layer3 = self._safe_execute("Layer 3", self._layer3_rolling_aggregation, layer1, layer2, config)
        layer4 = self._safe_execute("Layer 4", self._layer4_lag_features, layer1, layer2, layer3, raw_data, config)
        layer5 = self._safe_execute("Layer 5", self._layer5_cross_sectional, layer1, layer2, config)
        layer6 = self._safe_execute("Layer 6", self._layer6_meta_features, layer1, layer2, raw_data, config)

        layers = [layer1, layer2, layer3, layer4, layer5, layer6]
        if config.preprocessing.enabled:
            all_features = self._combine_layers(layers, context="layer6_5_input")
            preprocessed = self._safe_execute("Layer 6.5", self._layer6_5_preprocessing, all_features, config)
            if not preprocessed.empty:
                layers = [preprocessed]

        result = self._layer7_validate_and_persist(
            symbol,
            timeframe,
            raw_data,
            layers,
            config,
            time.time() - start_time,
            config_hash,
        )
        return result

    def _safe_execute(self, layer_name: str, func: Callable, *args) -> pd.DataFrame:
        """Execute a layer safely; return empty DataFrame on failure."""
        try:
            self._report_progress(layer_name, 0.0, f"Starting {layer_name}...")
            result = func(*args)
            if result is None:
                result = pd.DataFrame()
            if not result.empty:
                result = self._ensure_float32(result)
                if result.columns.has_duplicates:
                    duplicate_counts = result.columns[result.columns.duplicated(keep=False)].value_counts()
                    duplicate_total = int(result.columns.duplicated(keep="first").sum())
                    logger.warning(
                        "%s output contains duplicated columns (%d duplicates across %d names): %s",
                        layer_name,
                        duplicate_total,
                        len(duplicate_counts),
                        duplicate_counts.head(20).to_dict(),
                    )
            self._report_progress(
                layer_name,
                1.0,
                f"{layer_name} completed: {result.shape[1]} features",
            )
            return result
        except Exception as exc:
            logger.error("%s failed: %s", layer_name, exc, exc_info=True)
            return pd.DataFrame()

    _BASE_OHLCV = ["open", "high", "low", "close", "volume"]

    def _layer0_data_ingestion(
        self, symbol: str, timeframe: str, config: "FactoryConfig"
    ) -> pd.DataFrame:
        # Always include base OHLCV columns so non-single indicators (ADX, ATR, STOCH, CDL...)
        # can access high/low/close/open/volume even when user's enabled_sources omits them.
        # _select_single_series_sources still reads only config.data_sources.enabled_sources,
        # so OHLCV columns are never added to the single-series iteration scope.
        sources = list(dict.fromkeys(
            self._BASE_OHLCV
            + config.data_sources.enabled_sources
            + config.data_sources.synthetic_sources
        ))
        data = self._adapter_registry.fetch_aligned(symbol, timeframe, sources)
        data = data.sort_index()
        if not data.index.is_unique:
            duplicate_count = int(data.index.duplicated(keep="last").sum())
            logger.warning(
                "Layer 0 detected duplicated index for %s/%s, dropping %d rows and keeping last occurrence",
                symbol,
                timeframe,
                duplicate_count,
            )
            data = data[~data.index.duplicated(keep="last")]
        return data

    def _layer1_atomic_indicators(self, data: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        if data.empty:
            return pd.DataFrame(index=data.index)

        sources = self._select_single_series_sources(config)
        tasks: List[Tuple[str, bool, Callable[[], pd.DataFrame]]] = []

        if config.atomic_indicators.trend.enabled:
            tasks.append(
                (
                    "trend",
                    True,
                    lambda: TrendIndicatorEngine(
                        config.atomic_indicators.trend.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.momentum.enabled:
            tasks.append(
                (
                    "momentum",
                    True,
                    lambda: MomentumIndicatorEngine(
                        config.atomic_indicators.momentum.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.volatility.enabled:
            tasks.append(
                (
                    "volatility",
                    True,
                    lambda: VolatilityIndicatorEngine(
                        config.atomic_indicators.volatility.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.volume.enabled:
            tasks.append(
                (
                    "volume",
                    True,
                    lambda: VolumeIndicatorEngine(
                        config.atomic_indicators.volume.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.cycle.enabled:
            tasks.append(
                (
                    "cycle",
                    True,
                    lambda: CycleIndicatorEngine(
                        config.atomic_indicators.cycle.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.pattern.enabled:
            tasks.append(
                (
                    "pattern",
                    True,
                    lambda: PatternIndicatorEngine(
                        config.atomic_indicators.pattern.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.statistics.enabled:
            tasks.append(
                (
                    "statistics",
                    True,
                    lambda: StatisticsIndicatorEngine(
                        config.atomic_indicators.statistics.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.microstructure.enabled:
            tasks.append(
                (
                    "microstructure",
                    False,
                    lambda: MicrostructureIndicatorEngine(
                        config.atomic_indicators.microstructure.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.entropy.enabled:
            tasks.append(
                (
                    "entropy",
                    False,
                    lambda: EntropyIndicatorEngine(
                        config.atomic_indicators.entropy.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.atomic_indicators.tail_risk.enabled:
            tasks.append(
                (
                    "tail_risk",
                    False,
                    lambda: TailRiskIndicatorEngine(
                        config.atomic_indicators.tail_risk.model_dump(),
                        sources,
                    ).compute_all(data),
                )
            )

        if config.custom_indicators:
            custom_payload = [item.model_dump() for item in config.custom_indicators]
            tasks.append(
                (
                    "custom",
                    True,
                    lambda: CustomIndicatorEngine().compute_all(data, custom_payload),
                )
            )

        frames: List[pd.DataFrame] = []
        use_parallel = self._layer1_parallel_enabled() and len(tasks) > 1

        if use_parallel:
            max_workers = min(self._layer1_max_workers(), len(tasks))
            ordered_results: Dict[int, pd.DataFrame] = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map: Dict[Any, Tuple[int, str, bool]] = {}
                for idx, (task_name, required, builder) in enumerate(tasks):
                    future = executor.submit(builder)
                    future_map[future] = (idx, task_name, required)

                for future in as_completed(future_map):
                    idx, task_name, required = future_map[future]
                    try:
                        frame = future.result()
                    except Exception as exc:
                        if required:
                            raise
                        logger.warning("%s engine failed: %s", task_name.capitalize(), exc)
                        frame = pd.DataFrame(index=data.index)
                    ordered_results[idx] = frame

            for idx in range(len(tasks)):
                frames.append(ordered_results.get(idx, pd.DataFrame(index=data.index)))
        else:
            for task_name, required, builder in tasks:
                try:
                    frames.append(builder())
                except Exception as exc:
                    if required:
                        raise
                    logger.warning("%s engine failed: %s", task_name.capitalize(), exc)

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

    @staticmethod
    def _layer1_parallel_enabled() -> bool:
        # Default off to preserve strict deterministic behavior against golden baseline.
        # Can be enabled explicitly via FFACT_LAYER1_PARALLEL=1 for controlled experiments.
        raw = os.getenv("FFACT_LAYER1_PARALLEL", "0").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    @staticmethod
    def _layer1_max_workers() -> int:
        raw = os.getenv("FFACT_LAYER1_MAX_WORKERS", "4").strip()
        try:
            workers = int(raw)
        except ValueError:
            workers = 4
        return max(1, workers)

    def _layer2_derived_features(
        self, layer1: pd.DataFrame, data: pd.DataFrame, config: "FactoryConfig"
    ) -> pd.DataFrame:
        if layer1.empty:
            return pd.DataFrame(index=layer1.index)

        engine = DerivedOperatorEngine(config.operators)
        indicator_specs = self._build_indicator_specs(layer1, config)
        return engine.compute_all(layer1, data, indicator_specs)

    def _layer3_rolling_aggregation(
        self, layer1: pd.DataFrame, layer2: pd.DataFrame, config: "FactoryConfig"
    ) -> pd.DataFrame:
        # Only apply rolling aggregation to Layer 1 atomic indicators.
        # Layer 2 derived features (e.g. %change, log_return) must NOT be included here:
        # feeding them into rolling aggregation would create semantically redundant features
        # and inflate the feature space by ~20× unnecessarily.
        base = self._combine_layers([layer1], context="layer3_input")
        if base.empty:
            return pd.DataFrame(index=base.index)
        aggregator = RollingAggregator(config.rolling_aggregation)
        return aggregator.compute_all(base)

    def _layer4_lag_features(
        self,
        layer1: pd.DataFrame,
        layer2: pd.DataFrame,
        layer3: pd.DataFrame,
        data: pd.DataFrame,
        config: "FactoryConfig",
    ) -> pd.DataFrame:
        base = self._combine_layers([data, layer1, layer2, layer3], context="layer4_input")
        if base.empty:
            return pd.DataFrame(index=base.index)
        processor = LagProcessor(config)
        return processor.compute_all(base)

    def _layer5_cross_sectional(
        self, layer1: pd.DataFrame, layer2: pd.DataFrame, config: "FactoryConfig"
    ) -> pd.DataFrame:
        if not config.cross_sectional.enabled:
            return pd.DataFrame(index=layer1.index)

        symbol = self._current_symbol
        timeframe = self._current_timeframe
        if not symbol or not timeframe:
            return pd.DataFrame(index=layer1.index)

        reference_symbol = config.cross_sectional.reference_symbol
        if not reference_symbol or reference_symbol == symbol:
            return pd.DataFrame(index=layer1.index)

        try:
            cache_key = (reference_symbol, timeframe)
            ref_data = self._reference_data_cache.get(cache_key)
            if ref_data is None:
                ref_data = self._layer0_data_ingestion(reference_symbol, timeframe, config)
                self._reference_data_cache[cache_key] = ref_data
        except Exception as exc:
            logger.error("Cross-sectional reference fetch failed: %s", exc, exc_info=True)
            return pd.DataFrame(index=layer1.index)

        if ref_data.empty:
            return pd.DataFrame(index=layer1.index)

        if self._current_raw_data is None or "close" not in self._current_raw_data.columns:
            return pd.DataFrame(index=layer1.index)
        if "close" not in ref_data.columns:
            return pd.DataFrame(index=layer1.index)

        processor = RelativeStrengthProcessor()
        symbol_close = self._current_raw_data["close"]
        btc_close = ref_data["close"]
        aligned = pd.concat(
            [symbol_close.rename("symbol"), btc_close.rename("btc")],
            axis=1,
        ).dropna()
        if aligned.empty:
            return pd.DataFrame(index=layer1.index)
        symbol_close = aligned["symbol"]
        btc_close = aligned["btc"]
        symbol_returns = symbol_close.pct_change()
        btc_returns = btc_close.pct_change()

        frames: List[pd.Series] = []
        features = config.cross_sectional.features
        if "relative_price" in features:
            frames.append(processor.compute_relative_price(symbol_close, btc_close).rename("cs_relative_price"))
        if "beta" in features:
            beta = processor.compute_beta(symbol_returns, btc_returns)
            frames.append(beta.rename("cs_beta"))
        if "idiosyncratic_momentum" in features:
            beta = processor.compute_beta(symbol_returns, btc_returns)
            frames.append(
                processor.compute_idiosyncratic_momentum(symbol_returns, btc_returns, beta).rename(
                    "cs_idiosyncratic_momentum"
                )
            )

        if not frames:
            return pd.DataFrame(index=layer1.index)

        return pd.concat(frames, axis=1).reindex(layer1.index)

    def _layer6_meta_features(
        self,
        layer1: pd.DataFrame,
        layer2: pd.DataFrame,
        data: pd.DataFrame,
        config: "FactoryConfig",
    ) -> pd.DataFrame:
        if not config.meta_features.enabled:
            return pd.DataFrame(index=layer1.index)

        frames: List[pd.DataFrame] = []
        consensus_engine = ConsensusFeatureEngine()
        interaction_engine = InteractionFeatureEngine()
        time_engine = TimeFeatureEngine()

        if config.meta_features.trend_consensus:
            frames.append(consensus_engine.compute_trend_consensus(layer1).to_frame())
        if config.meta_features.momentum_divergence:
            frames.append(consensus_engine.compute_momentum_divergence(layer1).to_frame())
        if config.meta_features.volume_price_divergence:
            frames.append(consensus_engine.compute_volume_price_divergence(layer1, data).to_frame())
        if config.meta_features.volatility_regime:
            frames.append(consensus_engine.compute_volatility_regime(layer1).to_frame())

        if config.meta_features.interaction:
            frames.append(interaction_engine.compute_all(layer1, data))

        if config.meta_features.time_features:
            timestamps = pd.Series(data.index, index=data.index)
            frames.append(time_engine.compute_all(timestamps))

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=layer1.index)

        return pd.concat(frames, axis=1)

    def _layer6_5_preprocessing(self, all_features: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        """Layer 6.5: Feature preprocessing and normalization."""
        preprocessor = FeaturePreprocessor(config.preprocessing.model_dump())
        return preprocessor.transform(all_features)

    def _layer7_validate_and_persist(
        self,
        symbol: str,
        timeframe: str,
        raw_data: pd.DataFrame,
        layers: List[pd.DataFrame],
        config: "FactoryConfig",
        elapsed: float,
        config_hash: str,
    ) -> FeatureGenerationResult:
        features_df = self._combine_layers(layers, context="layer7_final")
        features_df = features_df.reindex(raw_data.index)
        if not features_df.empty:
            features_df = features_df.astype("float32")

        labels_df = pd.DataFrame(index=raw_data.index)
        if "close" in raw_data.columns:
            label_generator = LabelGenerator(config.labels.model_dump())
            labels_df = label_generator.generate_all(raw_data["close"])

        layer_counts = {
            "layer1": layers[0].shape[1] if len(layers) > 0 else 0,
            "layer2": layers[1].shape[1] if len(layers) > 1 else 0,
            "layer3": layers[2].shape[1] if len(layers) > 2 else 0,
            "layer4": layers[3].shape[1] if len(layers) > 3 else 0,
            "layer5": layers[4].shape[1] if len(layers) > 4 else 0,
            "layer6": layers[5].shape[1] if len(layers) > 5 else 0,
        }

        data_range = self._data_range(raw_data)
        metadata = {
            "feature_names": list(features_df.columns),
            "feature_count": int(features_df.shape[1]),
            "layer_counts": layer_counts,
            "config_hash": config_hash,
            "generation_time": float(elapsed),
            "symbol": symbol,
            "timeframe": timeframe,
            "data_range": data_range,
            "config_used": config.model_dump(by_alias=True),
        }

        result = FeatureGenerationResult(
            features_df=features_df,
            labels_df=labels_df,
            metadata=metadata,
            feature_count=int(features_df.shape[1]),
            generation_time=float(elapsed),
            layer_counts=layer_counts,
            config_used=config.model_dump(by_alias=True),
        )

        validation = self._validator.validate_factory_output(result)
        metadata["validation"] = validation.__dict__
        metadata["feature_names"] = list(result.features_df.columns)
        metadata["feature_count"] = int(result.features_df.shape[1])
        result.metadata = metadata
        result.feature_count = int(result.features_df.shape[1])

        result.hdf5_path = self._storage.save_factory_output(symbol, timeframe, result)
        return result

    def _report_progress(self, stage: str, progress: float, message: str) -> None:
        """Report progress for WebSocket or other observers."""
        if self._progress_callback:
            self._progress_callback({"stage": stage, "progress": progress, "message": message})
        logger.info("[%s] %0.0f%% - %s", stage, progress * 100, message)

    @property
    def config_manager(self) -> ConfigManager:
        """Expose ConfigManager for upper layers."""
        return self._config_manager

    def _resolve_config(self, config_override: Optional[dict]) -> "FactoryConfig":
        if isinstance(config_override, dict) and "preset" in config_override:
            preset_name = config_override.get("preset")
            preset_config = self._config_manager.apply_preset(preset_name)
            override_without_preset = {k: v for k, v in config_override.items() if k != "preset"}
            if not override_without_preset:
                return preset_config

            merged_payload = self._config_manager.deep_merge(
                preset_config.model_dump(by_alias=True),
                override_without_preset,
            )
            return preset_config.__class__.model_validate(merged_payload)
        return self._config_manager.get_merged_config(config_override)

    def _compute_config_hash(self, config: "FactoryConfig") -> str:
        payload = json.dumps(config.model_dump(by_alias=True), sort_keys=True, default=str)
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    def _try_load_cache(self, symbol: str, timeframe: str, config_hash: str) -> Optional[FeatureGenerationResult]:
        try:
            cached = self._storage.load_factory_output(symbol, timeframe)
        except Exception as exc:
            logger.warning("Cache load failed for %s/%s: %s", symbol, timeframe, exc)
            return None
        if not cached:
            return None
        cached_hash = cached.metadata.get("config_hash") if isinstance(cached.metadata, dict) else None
        if cached_hash != config_hash:
            return None
        logger.info("Cache hit for %s/%s [hash=%s]", symbol, timeframe, config_hash[:8])
        return cached

    @staticmethod
    def _combine_layers(layers: List[pd.DataFrame], context: str = "unknown") -> pd.DataFrame:
        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()
        combined = pd.concat(valid_layers, axis=1, copy=False)
        if combined.columns.has_duplicates:
            duplicate_count = int(combined.columns.duplicated(keep="first").sum())
            duplicate_series = combined.columns.to_series()
            duplicate_counts = duplicate_series[duplicate_series.duplicated(keep=False)].value_counts()
            logger.warning(
                "[%s] Combined feature layers contain duplicated columns, dropping %d duplicate columns across %d names. Top duplicates: %s",
                context,
                duplicate_count,
                len(duplicate_counts),
                duplicate_counts.head(30).to_dict(),
            )
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        return combined

    @staticmethod
    def _ensure_float32(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        numeric_columns = [
            column_name
            for column_name in df.columns
            if pd.api.types.is_numeric_dtype(df[column_name])
        ]
        if not numeric_columns:
            return df

        # Batched conversion avoids costly per-column block fragmentation on very wide DataFrames.
        dtype_map = {column_name: "float32" for column_name in numeric_columns}
        return df.astype(dtype_map, copy=False)

    @staticmethod
    def _data_range(raw_data: pd.DataFrame) -> List[str]:
        if raw_data is None or raw_data.empty:
            return []
        index = raw_data.index
        try:
            start = pd.to_datetime(index.min(), unit="ms")
            end = pd.to_datetime(index.max(), unit="ms")
        except Exception:
            start = pd.to_datetime(index.min(), errors="coerce")
            end = pd.to_datetime(index.max(), errors="coerce")
        if pd.isna(start) or pd.isna(end):
            return []
        return [start.isoformat(), end.isoformat()]

    def _build_indicator_specs(self, layer1: pd.DataFrame, config: "FactoryConfig") -> Dict[str, Dict]:
        sources = self._select_single_series_sources(config)
        metadata: Dict[str, Dict] = {}

        if config.atomic_indicators.trend.enabled:
            engine = TrendIndicatorEngine(config.atomic_indicators.trend.model_dump(), sources)
            metadata.update(engine.get_feature_metadata())
        if config.atomic_indicators.momentum.enabled:
            engine = MomentumIndicatorEngine(config.atomic_indicators.momentum.model_dump(), sources)
            metadata.update(engine.get_feature_metadata())
        if config.atomic_indicators.volatility.enabled:
            engine = VolatilityIndicatorEngine(config.atomic_indicators.volatility.model_dump(), sources)
            metadata.update(engine.get_feature_metadata())
        if config.atomic_indicators.volume.enabled:
            engine = VolumeIndicatorEngine(config.atomic_indicators.volume.model_dump(), sources)
            metadata.update(engine.get_feature_metadata())
        if config.atomic_indicators.cycle.enabled:
            engine = CycleIndicatorEngine(config.atomic_indicators.cycle.model_dump(), sources)
            metadata.update(engine.get_feature_metadata())
        if config.atomic_indicators.pattern.enabled:
            engine = PatternIndicatorEngine(config.atomic_indicators.pattern.model_dump(), sources)
            metadata.update(engine.get_feature_metadata())
        if config.atomic_indicators.statistics.enabled:
            engine = StatisticsIndicatorEngine(config.atomic_indicators.statistics.model_dump(), sources)
            metadata.update(engine.get_feature_metadata())
        if config.atomic_indicators.microstructure.enabled:
            try:
                engine = MicrostructureIndicatorEngine(config.atomic_indicators.microstructure.model_dump(), sources)
                metadata.update(engine.get_feature_metadata())
            except Exception as exc:
                logger.warning("Microstructure metadata build failed: %s", exc)
        if config.atomic_indicators.entropy.enabled:
            try:
                engine = EntropyIndicatorEngine(config.atomic_indicators.entropy.model_dump(), sources)
                metadata.update(engine.get_feature_metadata())
            except Exception as exc:
                logger.warning("Entropy metadata build failed: %s", exc)
        if config.atomic_indicators.tail_risk.enabled:
            try:
                engine = TailRiskIndicatorEngine(config.atomic_indicators.tail_risk.model_dump(), sources)
                metadata.update(engine.get_feature_metadata())
            except Exception as exc:
                logger.warning("Tail risk metadata build failed: %s", exc)

        indicator_specs: Dict[str, Dict] = {}
        for name in layer1.columns:
            info = metadata.get(name)
            if not info:
                continue
            indicator_specs[name] = {
                "source": info.get("source"),
                "category": info.get("category"),
                "indicator": info.get("indicator"),
                "params": list(info.get("params") or []),
            }
        return indicator_specs

    @staticmethod
    def _select_single_series_sources(config: "FactoryConfig") -> List[str]:
        enabled = list(dict.fromkeys(config.data_sources.enabled_sources))
        if not enabled:
            return []
        preferred = [source for source in ["close", "volume", "taker_ratio"] if source in enabled]
        ordered = preferred + [source for source in enabled if source not in preferred]
        return ordered
