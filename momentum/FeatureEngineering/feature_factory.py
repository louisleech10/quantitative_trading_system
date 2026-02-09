"""Feature factory pipeline skeleton for FeatureEngineering."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

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

        result = self._layer7_validate_and_persist(
            symbol,
            timeframe,
            raw_data,
            [layer1, layer2, layer3, layer4, layer5, layer6],
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
            self._report_progress(
                layer_name,
                1.0,
                f"{layer_name} completed: {result.shape[1]} features",
            )
            return result
        except Exception as exc:
            logger.error("%s failed: %s", layer_name, exc, exc_info=True)
            return pd.DataFrame()

    def _layer0_data_ingestion(
        self, symbol: str, timeframe: str, config: "FactoryConfig"
    ) -> pd.DataFrame:
        sources = list(dict.fromkeys(config.data_sources.enabled_sources + config.data_sources.synthetic_sources))
        data = self._adapter_registry.fetch_aligned(symbol, timeframe, sources)
        data = data.sort_index()
        return data

    def _layer1_atomic_indicators(self, data: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        if data.empty:
            return pd.DataFrame(index=data.index)

        sources = self._select_single_series_sources(config)
        frames: List[pd.DataFrame] = []

        if config.atomic_indicators.trend.enabled:
            engine = TrendIndicatorEngine(config.atomic_indicators.trend.model_dump(), sources)
            frames.append(engine.compute_all(data))

        if config.atomic_indicators.momentum.enabled:
            engine = MomentumIndicatorEngine(config.atomic_indicators.momentum.model_dump(), sources)
            frames.append(engine.compute_all(data))

        if config.atomic_indicators.volatility.enabled:
            engine = VolatilityIndicatorEngine(config.atomic_indicators.volatility.model_dump(), sources)
            frames.append(engine.compute_all(data))

        if config.atomic_indicators.volume.enabled:
            engine = VolumeIndicatorEngine(config.atomic_indicators.volume.model_dump(), sources)
            frames.append(engine.compute_all(data))

        if config.atomic_indicators.cycle.enabled:
            engine = CycleIndicatorEngine(config.atomic_indicators.cycle.model_dump(), sources)
            frames.append(engine.compute_all(data))

        if config.atomic_indicators.pattern.enabled:
            engine = PatternIndicatorEngine(config.atomic_indicators.pattern.model_dump(), sources)
            frames.append(engine.compute_all(data))

        if config.atomic_indicators.statistics.enabled:
            engine = StatisticsIndicatorEngine(config.atomic_indicators.statistics.model_dump(), sources)
            frames.append(engine.compute_all(data))

        if config.custom_indicators:
            engine = CustomIndicatorEngine()
            frames.append(engine.compute_all(data, [item.model_dump() for item in config.custom_indicators]))

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

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
        base = self._combine_layers([layer1, layer2])
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
        base = self._combine_layers([data, layer1, layer2, layer3])
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
            ref_data = self._layer0_data_ingestion(reference_symbol, timeframe, config)
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
        features_df = self._combine_layers(layers)
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
            return self._config_manager.apply_preset(preset_name)
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
    def _combine_layers(layers: List[pd.DataFrame]) -> pd.DataFrame:
        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()
        return pd.concat(valid_layers, axis=1, copy=False)

    @staticmethod
    def _ensure_float32(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        for idx in range(df.shape[1]):
            series = df.iloc[:, idx]
            if pd.api.types.is_numeric_dtype(series):
                df.iloc[:, idx] = series.astype("float32")
        return df

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
        return ordered[:2] if len(ordered) > 2 else ordered
