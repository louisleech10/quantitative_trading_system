"""Feature factory pipeline skeleton for FeatureEngineering."""

from __future__ import annotations

import re
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Tuple

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
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
from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


logger = get_logger(__name__)

MAX_L2_ESTIMATED_COLS = 100_000

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
    compute_warnings: List[str] = None

    def __post_init__(self):
        if self.compute_warnings is None:
            self.compute_warnings = []


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
        self._registry = FeatureRegistry()
        self._validator = FeatureValidator()
        self._current_symbol: Optional[str] = None
        self._current_timeframe: Optional[str] = None
        self._current_raw_data: Optional[pd.DataFrame] = None
        self._reference_data_cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        self._cgsa_registry: Optional[ColumnGroupRegistry] = None

    def generate_features(
        self,
        symbol: str,
        timeframe: str,
        config_override: Optional[dict] = None,
        force_regenerate: bool = False,
        progress_callback: Optional[Callable] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        persist: bool = True,
    ) -> FeatureGenerationResult:
        """Run the seven-layer pipeline.

        force_regenerate=True skips cache and forces recalculation.
        Layer 0 failure stops the pipeline. Layer 1-6 failures return empty DataFrame.
        """
        config = self._resolve_config(config_override)
        self._progress_callback = progress_callback
        self._current_symbol = symbol
        self._current_timeframe = timeframe
        self._cgsa_registry = None
        start_time = time.time()

        config_hash = self._compute_config_hash(
            config,
            symbol,
            timeframe,
            start_date=start_date,
            end_date=end_date,
        )
        if not force_regenerate:
            cached = self._try_load_cache(symbol, timeframe, config_hash)
            if cached:
                return cached

        self._cgsa_registry = self._prepare_cgsa_registry(symbol, timeframe)

        training_tfs = list(dict.fromkeys(config.timeframes.training))
        if len(training_tfs) > 1:
            from momentum.FeatureEngineering.timeframe import MultiTFGenerator

            multi_generator = MultiTFGenerator(
                feature_factory=self,
                config=config,
                progress_callback=progress_callback,
            )
            return multi_generator.generate_multi_tf(
                symbol,
                start_date=start_date,
                end_date=end_date,
            )

        try:
            raw_data = self._layer0_data_ingestion(
                symbol,
                timeframe,
                config,
                start_date=start_date,
                end_date=end_date,
            )
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

        compute_warnings = self._collect_layer1_warnings(raw_data, config)
        layer1 = self._safe_execute("Layer 1", self._layer1_atomic_indicators, raw_data, config)
        layer2 = self._safe_execute("Layer 2", self._layer2_derived_features, layer1, raw_data, config)

        # Spill layer2 to disk-backed memmap BEFORE L3.
        # L3 only uses layer1, but layer2 stays alive (needed for L4/L5/L6).
        # On 8 GB M1: float64 layer2 (46K cols × 20K rows = 7.5 GB) + L3
        # memmap (12.9 GB on disk) causes OOM.  Converting layer2 to a
        # float32 memmap releases the 7.5 GB and uses ~0 RSS (only paged in
        # when accessed later by L4/L5/L6).
        layer2 = self._spill_to_memmap(layer2, "layer2")

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
            compute_warnings=compute_warnings,
            persist=persist,
        )
        return result

    @staticmethod
    def _spill_to_memmap(df: pd.DataFrame, label: str) -> pd.DataFrame:
        """Convert a large DataFrame to a float32 memmap-backed DataFrame.

        Releases the original float64 data and replaces it with a
        memory-mapped array on disk.  Pages are only loaded when accessed,
        so RSS drops to ~0 for inactive layers.
        """
        if df is None or df.empty:
            return df

        est_bytes = df.shape[0] * df.shape[1] * 8  # float64 estimate
        # Only spill if the DataFrame is large enough to warrant it (>500 MB).
        if est_bytes < 500_000_000:
            return df

        import gc
        from momentum.FeatureEngineering.memmap_utils import create_temp_memmap

        t0 = time.perf_counter()
        n_rows, n_cols = df.shape
        out = create_temp_memmap((n_rows, n_cols), prefix=f"spill_{label}_")

        # Row-block copy to avoid materialising full float32 array in memory.
        block_rows = 2048
        for row_start in range(0, n_rows, block_rows):
            row_end = min(row_start + block_rows, n_rows)
            out[row_start:row_end, :] = df.iloc[row_start:row_end].to_numpy(
                dtype=np.float32, na_value=np.nan
            )

        index = df.index
        columns = df.columns.tolist()
        del df
        gc.collect()

        result = pd.DataFrame(data=out, index=index, columns=columns, copy=False)
        elapsed = time.perf_counter() - t0
        logger.info(
            "[spill] %s: %d×%d → float32 memmap in %.1fs (freed ~%.1f GB float64)",
            label,
            n_rows,
            n_cols,
            elapsed,
            est_bytes / 1e9,
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
        self,
        symbol: str,
        timeframe: str,
        config: "FactoryConfig",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
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

        if start_date is not None or end_date is not None:
            index_as_datetime = self._coerce_index_to_datetime(data.index)

            if start_date is not None:
                start_ts = pd.Timestamp(start_date)
                start_mask = (index_as_datetime >= start_ts).to_numpy()
                data = data[start_mask]
                index_as_datetime = index_as_datetime[start_mask]
            if end_date is not None:
                end_ts = pd.Timestamp(end_date)
                end_mask = (index_as_datetime <= end_ts).to_numpy()
                data = data[end_mask]
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

        # --- 7 TA-Lib categories: filter enabled indicators (Strategy A) ---
        _CATEGORY_ENGINE_MAP: List[Tuple[str, bool, type]] = [
            ("trend", True, TrendIndicatorEngine),
            ("momentum", True, MomentumIndicatorEngine),
            ("volatility", True, VolatilityIndicatorEngine),
            ("volume", True, VolumeIndicatorEngine),
            ("cycle", True, CycleIndicatorEngine),
            ("pattern", True, PatternIndicatorEngine),
            ("statistics", True, StatisticsIndicatorEngine),
        ]
        for cat_name, required, engine_cls in _CATEGORY_ENGINE_MAP:
            cat_cfg = getattr(config.atomic_indicators, cat_name)
            if not cat_cfg.enabled:
                continue
            filtered = self._filter_category_config(cat_cfg)
            if filtered is None:
                continue
            tasks.append(
                (cat_name, required, lambda c=filtered, e=engine_cls: e(c, sources).compute_all(data))
            )

        # --- 3 Advanced categories: Microstructure / Entropy / TailRisk ---
        if config.atomic_indicators.microstructure.enabled:
            ms_cfg = self._filter_advanced_config(config.atomic_indicators.microstructure)
            tasks.append(
                ("microstructure", False, lambda c=ms_cfg: MicrostructureIndicatorEngine(c, sources).compute_all(data))
            )

        if config.atomic_indicators.entropy.enabled:
            ent_cfg = self._filter_advanced_config(config.atomic_indicators.entropy)
            tasks.append(
                ("entropy", False, lambda c=ent_cfg: EntropyIndicatorEngine(c, sources).compute_all(data))
            )

        if config.atomic_indicators.tail_risk.enabled:
            tr_cfg = self._filter_advanced_config(config.atomic_indicators.tail_risk)
            tasks.append(
                ("tail_risk", False, lambda c=tr_cfg: TailRiskIndicatorEngine(c, sources).compute_all(data))
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
                task_name, _, _ = tasks[idx]
                frame = ordered_results.get(idx, pd.DataFrame(index=data.index))
                frames.append(frame)
                self._persist_layer1_indicator_groups(frame, category_hint=task_name)
        else:
            for task_name, required, builder in tasks:
                try:
                    frame = builder()
                    frames.append(frame)
                    self._persist_layer1_indicator_groups(frame, category_hint=task_name)
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

    @staticmethod
    def _cgsa_enabled() -> bool:
        raw = os.getenv("FFACT_USE_CGSA", "1").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def _prepare_cgsa_registry(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[ColumnGroupRegistry]:
        if not self._cgsa_enabled():
            return None

        configured_work_dir = os.getenv("FFACT_CGSA_WORK_DIR", "").strip()
        if configured_work_dir:
            work_dir = Path(configured_work_dir)
        else:
            safe_symbol = re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol)
            safe_timeframe = re.sub(r"[^A-Za-z0-9_.-]+", "_", timeframe)
            work_dir = Path(tempfile.mkdtemp(prefix=f"ffact_cgsa_{safe_symbol}_{safe_timeframe}_"))

        logger.info("[CGSA] Initialized ColumnGroupRegistry at %s", work_dir)
        return ColumnGroupRegistry(work_dir=work_dir)

    @staticmethod
    def _is_numeric_token(token: str) -> bool:
        return re.fullmatch(r"-?\d+(?:\.\d+)?", token) is not None

    @classmethod
    def _parse_l1_column_identity(
        cls,
        column_name: str,
        category_hint: str,
    ) -> tuple[str, str, str]:
        parts = column_name.split("_")
        if len(parts) < 3:
            return "unknown", category_hint, column_name

        source = parts[0]
        category = parts[1] if parts[1] else category_hint
        indicator_tokens: List[str] = []
        for token in parts[2:]:
            if cls._is_numeric_token(token):
                break
            indicator_tokens.append(token)

        indicator = "_".join(indicator_tokens) if indicator_tokens else parts[2]
        return source, category, indicator

    def _next_available_group_id(self, base_group_id: str) -> str:
        if self._cgsa_registry is None:
            return base_group_id

        candidate = base_group_id
        suffix = 2
        while True:
            try:
                self._cgsa_registry.get(candidate)
            except KeyError:
                return candidate
            candidate = f"{base_group_id}_{suffix}"
            suffix += 1

    def _persist_layer1_indicator_groups(self, frame: pd.DataFrame, category_hint: str) -> None:
        if self._cgsa_registry is None or frame is None or frame.empty:
            return
        if not self._current_timeframe:
            return

        grouped_columns: Dict[tuple[str, str], List[str]] = {}
        grouped_sources: Dict[tuple[str, str], set[str]] = {}
        for column_name in frame.columns:
            source, category, indicator = self._parse_l1_column_identity(column_name, category_hint)
            key = (category, indicator)
            grouped_columns.setdefault(key, []).append(column_name)
            grouped_sources.setdefault(key, set()).add(source)

        for (category, indicator), columns in grouped_columns.items():
            if not columns:
                continue

            base_group_id = f"{self._current_timeframe}_L1_{category}_{indicator}"
            group_id = self._next_available_group_id(base_group_id)
            sources = grouped_sources.get((category, indicator), set())
            data_source = next(iter(sources)) if len(sources) == 1 else "mixed"
            data = frame.loc[:, columns].to_numpy(dtype=np.float32, copy=False)
            group = ColumnGroup(
                group_id=group_id,
                layer=LayerSource.L1,
                timeframe=self._current_timeframe,
                data_source=data_source,
                indicator=indicator,
                columns=tuple(columns),
                shape=(frame.shape[0], len(columns)),
                dtype="float32",
            )
            self._cgsa_registry.save_data(group, data)

    def _persist_layer2_category_group(self, category: str, frame: pd.DataFrame) -> None:
        if self._cgsa_registry is None or frame is None or frame.empty:
            return
        if not self._current_timeframe:
            return

        base_group_id = f"{self._current_timeframe}_L2_{category}"
        group_id = self._next_available_group_id(base_group_id)
        data = frame.to_numpy(dtype=np.float32, copy=False)
        group = ColumnGroup(
            group_id=group_id,
            layer=LayerSource.L2,
            timeframe=self._current_timeframe,
            data_source="derived",
            indicator=category,
            columns=tuple(frame.columns),
            shape=(frame.shape[0], frame.shape[1]),
            dtype="float32",
        )
        self._cgsa_registry.save_data(group, data)

    def _persist_layer_output_groups(
        self,
        frame: pd.DataFrame,
        layer: "LayerSource",
        label: str,
        chunk_cols: int = 5000,
    ) -> None:
        """Persist a layer output DataFrame into CGSA registry as chunked groups.

        Used for L3, L4, L5, L6 which don't have category-level grouping.
        Large outputs (e.g. L3 with 156K cols) are split into chunks.
        """
        if self._cgsa_registry is None or frame is None or frame.empty:
            return
        if not self._current_timeframe:
            return

        columns = list(frame.columns)
        n_cols = len(columns)
        chunk_idx = 0

        for start in range(0, n_cols, chunk_cols):
            chunk_cols_list = columns[start : start + chunk_cols]
            chunk_idx += 1
            suffix = f"_{chunk_idx}" if n_cols > chunk_cols else ""
            base_group_id = f"{self._current_timeframe}_{label}{suffix}"
            group_id = self._next_available_group_id(base_group_id)
            data = frame.iloc[:, start : start + chunk_cols].to_numpy(
                dtype=np.float32, copy=False,
            )
            group = ColumnGroup(
                group_id=group_id,
                layer=layer,
                timeframe=self._current_timeframe,
                data_source="derived",
                indicator=label,
                columns=tuple(chunk_cols_list),
                shape=(frame.shape[0], len(chunk_cols_list)),
                dtype="float32",
            )
            self._cgsa_registry.save_data(group, data)

        logger.info(
            "[CGSA] Persisted %s: %d cols → %d groups (tf=%s)",
            label, n_cols, chunk_idx, self._current_timeframe,
        )

    @staticmethod
    def _estimate_l2_output_cols(l1_col_count: int, operators_config: Dict[str, Any]) -> int:
        if l1_col_count <= 0:
            return 0

        estimated = 0
        pair_count = max(0, (l1_col_count * (l1_col_count - 1)) // 2)

        distance_cfg = operators_config.get("distance", {})
        if distance_cfg.get("enabled", False):
            estimated += l1_col_count

        cross_cfg = operators_config.get("cross", {})
        if cross_cfg.get("enabled", False):
            estimated += pair_count

        ratio_cfg = operators_config.get("ratio", {})
        if ratio_cfg.get("enabled", False):
            estimated += pair_count

        momentum_cfg = operators_config.get("momentum", {}) or operators_config.get("momentum_change", {})
        if momentum_cfg.get("enabled", False):
            lags = momentum_cfg.get("lags", [3, 5, 8])
            estimated += l1_col_count * max(1, len(lags))

        binary_cfg = operators_config.get("binary_signal", {})
        if binary_cfg.get("enabled", False):
            rules = binary_cfg.get("rules", [])
            estimated += l1_col_count * max(1, len(rules))

        signed_cfg = operators_config.get("signed_strength", {})
        if signed_cfg.get("enabled", False):
            estimated += l1_col_count

        worldquant_cfg = operators_config.get("worldquant", {})
        if worldquant_cfg.get("enabled", False):
            windows = worldquant_cfg.get("windows", [5, 13, 21])
            operators = worldquant_cfg.get("operators", ["ts_argmax", "ts_argmin", "ts_rank", "decay_linear"])
            transforms = worldquant_cfg.get("transforms", ["sign", "log1p", "abs", "clip"])
            total_ops = max(1, len(windows) * len(operators) + len(transforms))
            estimated += l1_col_count * total_ops

        return int(estimated)

    # ── Strategy A: Centralized filter helpers ─────────────────────────

    def _collect_layer1_warnings(self, data: pd.DataFrame, config: "FactoryConfig") -> List[str]:
        """在 Layer 1 執行前，預先檢查各進階引擎的必要欄位，回傳使用者可見的警告訊息清單。"""
        warnings: List[str] = []
        ai = config.atomic_indicators

        if ai.microstructure.enabled:
            ms_cfg = self._filter_advanced_config(ai.microstructure)
            engine = MicrostructureIndicatorEngine(ms_cfg, [])
            warnings.extend(engine.get_data_warnings(data))

        if ai.entropy.enabled:
            ent_cfg = self._filter_advanced_config(ai.entropy)
            engine = EntropyIndicatorEngine(ent_cfg, [])
            warnings.extend(engine.get_data_warnings(data))

        if ai.tail_risk.enabled:
            tr_cfg = self._filter_advanced_config(ai.tail_risk)
            engine = TailRiskIndicatorEngine(tr_cfg, [])
            warnings.extend(engine.get_data_warnings(data))

        return warnings

    @staticmethod
    def _filter_category_config(cat_cfg: Any) -> Optional[dict]:
        """Filter a CategoryConfig to only include enabled indicators.

        Returns a config dict with only enabled indicators, or None if none enabled.
        """
        enabled_indicators = [ind for ind in cat_cfg.indicators if ind.enabled]
        if not enabled_indicators:
            return None
        config_dict = cat_cfg.model_dump()
        config_dict["indicators"] = [ind.model_dump() for ind in enabled_indicators]
        return config_dict

    @staticmethod
    def _filter_advanced_config(config_model: Any) -> dict:
        """Filter Microstructure/Entropy/TailRisk config via features dict.

        Converts features dict {name: {enabled: bool}} → enabled_features list
        for backward compatibility with engines.
        """
        config_dict = config_model.model_dump()
        features = config_model.features  # Dict[str, AdvancedFeatureItemConfig]
        if features:
            enabled_names = [name for name, cfg in features.items() if cfg.enabled]
            config_dict["enabled_features"] = enabled_names
        return config_dict

    @staticmethod
    def _filter_operators_config(operators: Any) -> dict:
        """Filter OperatorConfig: remove disabled binary_signal rules and worldquant operators."""
        config_dict = operators.model_dump(by_alias=True)

        # Filter binary_signal rules
        bs = config_dict.get("binary_signal", {})
        if isinstance(bs.get("rules"), list):
            bs["rules"] = [r for r in bs["rules"] if r.get("enabled", True)]

        # Filter worldquant operators: dict → list of enabled names
        wq = config_dict.get("worldquant", {})
        wq_ops = wq.get("operators")
        if isinstance(wq_ops, dict):
            wq["operators"] = [
                name for name, cfg in wq_ops.items()
                if isinstance(cfg, dict) and cfg.get("enabled", True)
            ]
        elif wq_ops is None:
            wq.pop("operators", None)  # Let engine use its built-in defaults

        return config_dict

    @staticmethod
    def _filter_rolling_config(rolling_cfg: Any) -> dict:
        """Filter RollingAggConfig: convert dict aggregators to list of enabled names."""
        config_dict = rolling_cfg.model_dump()
        aggregators = config_dict.get("aggregators", {})
        if isinstance(aggregators, dict):
            config_dict["aggregators"] = [
                name for name, cfg in aggregators.items()
                if isinstance(cfg, dict) and cfg.get("enabled", True)
            ]
        return config_dict

    def _layer2_derived_features(
        self, layer1: pd.DataFrame, data: pd.DataFrame, config: "FactoryConfig"
    ) -> pd.DataFrame:
        t0 = time.perf_counter()
        logger.info("[L2] Starting derived features: %d L1 cols", layer1.shape[1])

        if layer1.empty:
            result = pd.DataFrame(index=layer1.index)
        elif not getattr(config.operators, 'enabled', True):
            result = pd.DataFrame(index=layer1.index)
        else:
            from momentum.FeatureEngineering.polars_adapter import polars_enabled

            use_polars = polars_enabled()
            if use_polars:
                result = self._layer2_derived_polars(layer1, data, config)
            else:
                result = self._layer2_derived_pandas(layer1, data, config)

        elapsed = time.perf_counter() - t0
        logger.info("[L2] Completed: %d cols in %.2fs", result.shape[1], elapsed)
        return result

    def _layer2_derived_pandas(
        self, layer1: pd.DataFrame, data: pd.DataFrame, config: "FactoryConfig"
    ) -> pd.DataFrame:
        """Legacy pandas path for L2 derived features."""
        filtered_ops = self._filter_operators_config(config.operators)
        engine = DerivedOperatorEngine(filtered_ops)
        indicator_specs = self._build_indicator_specs(layer1, config)

        if self._cgsa_registry is None:
            return engine.compute_all(layer1, data, indicator_specs)

        estimated_cols = self._estimate_l2_output_cols(layer1.shape[1], filtered_ops)
        if estimated_cols > MAX_L2_ESTIMATED_COLS:
            logger.warning(
                "[L2] Estimated output %d cols exceeds threshold %d, forcing per-category mode",
                estimated_cols,
                MAX_L2_ESTIMATED_COLS,
            )

        category_frames: List[pd.DataFrame] = []
        for category in DerivedOperatorEngine.OPERATOR_CATEGORIES:
            category_frame = engine.compute_category(layer1, data, indicator_specs, category)
            if category_frame is None or category_frame.empty:
                continue
            self._persist_layer2_category_group(category, category_frame)
            category_frames.append(category_frame)

        if category_frames:
            return pd.concat(category_frames, axis=1)
        return pd.DataFrame(index=layer1.index)

    def _layer2_derived_polars(
        self, layer1: pd.DataFrame, data: pd.DataFrame, config: "FactoryConfig"
    ) -> pd.DataFrame:
        """Polars-based path for L2 derived features (Task 4.1 + 4.2).

        Converts L1 to Polars for batch with_columns() operations,
        then converts back to pandas for downstream compatibility.
        """
        from momentum.FeatureEngineering.polars_adapter import (
            ensure_nan_semantics,
            pandas_to_polars,
            polars_to_pandas,
        )

        filtered_ops = self._filter_operators_config(config.operators)
        engine = DerivedOperatorEngine(filtered_ops)
        indicator_specs = self._build_indicator_specs(layer1, config)

        # Use Polars batch computation via engine's polars path
        result = engine.compute_all_polars(layer1, data, indicator_specs)

        if result is None or result.empty:
            return pd.DataFrame(index=layer1.index)

        # Persist to CGSA registry if enabled
        if self._cgsa_registry is not None:
            for category in DerivedOperatorEngine.OPERATOR_CATEGORIES:
                category_frame = engine.compute_category(layer1, data, indicator_specs, category)
                if category_frame is not None and not category_frame.empty:
                    self._persist_layer2_category_group(category, category_frame)

        return result

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
        filtered_config = self._filter_rolling_config(config.rolling_aggregation)
        aggregator = RollingAggregator(filtered_config)
        return aggregator.compute_all(base)

    def _layer4_lag_features(
        self,
        layer1: pd.DataFrame,
        layer2: pd.DataFrame,
        layer3: pd.DataFrame,
        data: pd.DataFrame,
        config: "FactoryConfig",
    ) -> pd.DataFrame:
        # LagProcessor.apply_to is typically "layer1_and_raw", which only
        # selects L1 and raw-data columns.  Passing the full
        # [data, layer1, layer2, layer3] creates a massive intermediate
        # DataFrame (213K cols) just for column selection to discard most of it.
        # Instead, pass only [data, layer1] — the layers that LagProcessor
        # actually uses — avoiding the 2-minute memmap copy entirely.
        apply_to = getattr(config.lag_features, "apply_to", "all")
        if self._cgsa_enabled() and apply_to != "layer1_and_raw":
            logger.warning(
                "[L4] CGSA mode requires lag_features.apply_to='layer1_and_raw'; forcing fast path from '%s'",
                apply_to,
            )
            apply_to = "layer1_and_raw"

        if apply_to == "layer1_and_raw":
            # Fast path: only the columns that will be selected
            base = self._combine_layers([data, layer1], context="layer4_input")
        else:
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
            if cache_key in self._reference_data_cache:
                ref_data = self._reference_data_cache[cache_key]
                # Cached negative lookup: reference data unavailable in this run.
                if ref_data is None:
                    return pd.DataFrame(index=layer1.index)
            else:
                ref_data = self._layer0_data_ingestion(reference_symbol, timeframe, config)
                self._reference_data_cache[cache_key] = ref_data
        except Exception as exc:
            # Cache negative result to avoid repeated failing fetch attempts.
            self._reference_data_cache[cache_key] = None
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
        if "relative_price" in features and features["relative_price"].enabled:
            frames.append(processor.compute_relative_price(symbol_close, btc_close).rename("cs_relative_price"))
        if "beta" in features and features["beta"].enabled:
            beta = processor.compute_beta(symbol_returns, btc_returns)
            frames.append(beta.rename("cs_beta"))
        if "idiosyncratic_momentum" in features and features["idiosyncratic_momentum"].enabled:
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
        """
        Layer 6 — Meta Features（元特徵層）

        本層為「二階特徵」：不從原始 K 線計算，而是整合 Layer 1 技術指標的輸出，
        提煉出更高維度的市場狀態訊號（趨勢共識、動量分歧、量價背離、波動率狀態等）。

        ┌────────────────────────────────────────────────────────────────┐
        │ 重要：Layer 6 與 IC/SHAP 篩選的關係                          │
        │                                                                │
        │  Layer 6 並非「要先跑 IC 篩選才能啟用」，而是與 L1~L5 同步   │
        │  計算後，再由 IC Analysis 和 SHAP 一起評估哪些 meta 特徵有用。│
        │                                                                │
        │  建議工作流程：                                               │
        │   1. 首次跑全套（L1~L6 全開）→ 取得完整 feature set          │
        │   2. IC Analysis / SHAP 篩選出高品質特徵                      │
        │   3. 若某 sub-engine 所有特徵 IC 皆低 → 可在 config 關閉       │
        │      以節省計算資源（如:對日線資料關閉 time_features）         │
        └────────────────────────────────────────────────────────────────┘

        Sub-engines（各自可在 scan_config.yaml 獨立開關）：
          - trend_consensus       : mean(sign(EMA8>EMA21), sign(MACD_Hist), ADX>25)
          - momentum_divergence   : std(rank(RSI), rank(CCI), rank(STOCH))  → 分歧度
          - volume_price_divergence: sign(ΔPrice) != sign(ΔVolume) → 量價背離
          - volatility_regime     : ATR_14 / ATR_55  → 短長期 ATR 比值
          - interaction           : EMA×RSI 交互、ATR×方向、成交量×價格變化
          - time_features         : HourOfDay / DayOfWeek / IsWeekend / MonthOfYear

        設計限制（已知）：
          - 每個 sub-engine 的指標欄位名稱均為 **hardcode**，透過 _find_column() 模糊
            比對 Layer 1 欄位。若 scan_config.yaml 未啟用對應指標，該 sub-engine
            會優雅地略過（回傳 NaN 或空欄位），不會報錯。
          - 目前 interaction 子引擎僅使用 EMA_8/21、RSI_14、ATR_14。
            其他 L1 指標（BBANDS、OBV、Keltner 等）尚未納入交互組合。

        未來待實作（Future Work）：
          TODO(layer6-redundancy): 加入特徵相關係數矩陣去冗餘
            → 對 L1~L6 全部特徵計算 Pearson 相關 > 0.85 的群，同群只留 IC 最高者
            → 工具: scipy.cluster.hierarchy / sklearn.AgglomerativeClustering

          TODO(layer6-mutual-info): 加入 Mutual Information 排序（非線性版 IC）
            → MI(feature, return) 能捕捉 Pearson 無法偵測的非線性關係
            → 工具: sklearn.feature_selection.mutual_info_regression

          TODO(layer6-multiple-testing): 加入多重比較校正（Bonferroni / BHY）
            → 測試 N 個特徵時，顯著性門檻需從 0.05 降為 0.05/N
            → 參考: Lopez de Prado《Advances in Financial ML》MinSharpe 公式

          TODO(layer6-dynamic-candidates): 讓 _find_column 候選列表可由 config 動態注入
            → 使用者可在 scan_config.yaml 指定 meta_features.consensus_indicators
            → 無需改 Python 程式碼即可擴展 sub-engine 使用的指標集
        """
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
            # data.index 在本專案中存儲的是 Unix 秒（int64）。
            # 必須先用 _coerce_index_to_datetime()（可自動偵測 s/ms/us/ns 單位）
            # 轉換為 datetime64 Series，再傳入 TimeFeatureEngine，
            # 否則 unit="ms" 會把秒當毫秒，將所有日期錯誤映射到 1970-01-21，
            # 導致 DayOfWeek/IsWeekend/MonthOfYear 全為常數並被 Layer 7 丟棄。
            #
            # 重要：_coerce_index_to_datetime 內部使用 pd.Series(index)，
            # 回傳的 Series 帶有預設 RangeIndex(0,1,2...)。
            # 必須將其 index 重設回 data.index，
            # 才能在 pd.concat(frames, axis=1) 時與其他 frames 正確對齊。
            dt_index = self._coerce_index_to_datetime(data.index)
            dt_index.index = data.index  # 恢復原始 index，避免 concat 時全行變 NaN
            frames.append(time_engine.compute_all(dt_index))

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=layer1.index)

        return pd.concat(frames, axis=1)

    def _layer6_5_preprocessing(self, all_features: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        """Layer 6.5: Feature preprocessing and normalization."""
        preprocessor = FeaturePreprocessor(config.preprocessing.model_dump())

        if self._cgsa_enabled() and self._cgsa_registry is not None:
            preprocessor.transform_registry_groups(self._cgsa_registry)
            return pd.DataFrame(index=all_features.index if all_features is not None else None)

        return preprocessor.transform(all_features)

    @staticmethod
    def _collect_cgsa_layer_counts(registry: ColumnGroupRegistry) -> Dict[str, int]:
        """Aggregate per-layer column counts directly from registry groups."""
        layer_mapping = {
            LayerSource.L1: "layer1",
            LayerSource.L2: "layer2",
            LayerSource.L3: "layer3",
            LayerSource.L4: "layer4",
            LayerSource.L5: "layer5",
            LayerSource.L6: "layer6",
            LayerSource.L65: "layer6_5",
        }

        counts: Dict[str, int] = {
            "layer1": 0,
            "layer2": 0,
            "layer3": 0,
            "layer4": 0,
            "layer5": 0,
            "layer6": 0,
            "layer6_5": 0,
        }

        for _, group in registry.iter_all():
            target_key = layer_mapping.get(group.layer)
            if target_key is None:
                continue
            counts[target_key] += int(group.n_cols)

        return counts

    def _scan_cgsa_registry_validation(self, registry: ColumnGroupRegistry) -> Dict[str, Any]:
        """Validate registry groups via per-group scan without materializing wide DataFrame."""
        has_nan = False
        has_inf = False
        warnings: List[str] = []
        total_values = 0
        non_nan_values = 0

        for group_id, group in registry.iter_all():
            group_data = np.asarray(registry.load_data(group_id), dtype=np.float32)
            if group_data.ndim != 2:
                warnings.append(f"Group {group_id} has invalid ndim={group_data.ndim}; expected 2D")
                logger.warning("[L7][CGSA] Invalid group shape for %s: ndim=%d", group_id, group_data.ndim)
                continue

            if group_data.shape[1] != group.n_cols:
                warnings.append(
                    f"Group {group_id} columns mismatch: expected {group.n_cols}, got {group_data.shape[1]}"
                )
                logger.warning(
                    "[L7][CGSA] Column mismatch for %s: expected=%d got=%d",
                    group_id,
                    group.n_cols,
                    group_data.shape[1],
                )

            value_count = int(group_data.size)
            if value_count == 0:
                continue

            inf_count = int(np.isinf(group_data).sum())
            nan_count = int(np.isnan(group_data).sum())
            nan_ratio = nan_count / value_count

            if inf_count > 0:
                has_inf = True
                message = f"Group {group_id} contains {inf_count} inf values"
                warnings.append(message)
                logger.warning("[L7][CGSA] %s", message)

            if nan_count > 0:
                has_nan = True

            if nan_ratio > 0.90:
                message = f"Group {group_id} NaN ratio={nan_ratio:.4f} exceeds 0.90"
                warnings.append(message)
                logger.warning("[L7][CGSA] %s", message)

            total_values += value_count
            non_nan_values += value_count - nan_count

        coverage = float(non_nan_values / total_values) if total_values > 0 else 0.0
        return {
            "has_nan": has_nan,
            "has_inf": has_inf,
            "coverage": coverage,
            "warnings": warnings,
        }

    def _layer7_validate_and_persist_cgsa(
        self,
        symbol: str,
        timeframe: str,
        raw_data: pd.DataFrame,
        config: "FactoryConfig",
        elapsed: float,
        config_hash: str,
        compute_warnings: Optional[List[str]] = None,
        persist: bool = True,
    ) -> FeatureGenerationResult:
        """CGSA Layer 7 path: per-group scan validation + per-group parquet persistence."""
        if self._cgsa_registry is None:
            raise ValueError("CGSA Layer 7 requested without initialized registry")

        labels_df = pd.DataFrame(index=raw_data.index)
        if "close" in raw_data.columns:
            label_generator = LabelGenerator(config.labels.model_dump())
            labels_df = label_generator.generate_all(raw_data["close"])

        validation_summary = self._scan_cgsa_registry_validation(self._cgsa_registry)
        layer_counts = self._collect_cgsa_layer_counts(self._cgsa_registry)
        feature_names = self._cgsa_registry.all_column_names()
        feature_count = int(self._cgsa_registry.total_columns())

        config_payload = config.model_dump(by_alias=True)
        training_tfs = config_payload.get("timeframes", {}).get("training", [])
        if not isinstance(training_tfs, list):
            training_tfs = [timeframe]

        persisted_group_paths: List[str] = []
        if persist:
            persisted_group_paths = self._storage.persist_registry_to_parquet(
                symbol=symbol,
                config_hash=config_hash,
                registry=self._cgsa_registry,
                cleanup_intermediate=False,
            )

        self._cgsa_registry.save_state(
            symbol=symbol,
            primary_tf=timeframe,
            training_tfs=training_tfs,
            config_hash=config_hash,
            config_snapshot=config_payload,
        )

        manifest_path = str(self._cgsa_registry.manifest_path)
        merged_warnings = (compute_warnings or []) + list(validation_summary["warnings"])

        metadata = {
            "feature_names": feature_names,
            "feature_count": feature_count,
            "layer_counts": layer_counts,
            "config_hash": config_hash,
            "generation_time": float(elapsed),
            "compute_warnings": merged_warnings,
            "symbol": symbol,
            "timeframe": timeframe,
            "data_range": self._data_range(raw_data),
            "config_used": config_payload,
            "manifest_path": manifest_path,
            "persisted_group_paths": persisted_group_paths,
            "validation": {
                "has_nan": bool(validation_summary["has_nan"]),
                "has_inf": bool(validation_summary["has_inf"]),
                "max_correlation": 0.0,
                "high_correlation_pairs": [],
                "warnings": list(validation_summary["warnings"]),
                "coverage": float(validation_summary["coverage"]),
                "constant_features_removed": [],
            },
        }

        result = FeatureGenerationResult(
            features_df=pd.DataFrame(index=raw_data.index),
            labels_df=labels_df,
            metadata=metadata,
            feature_count=feature_count,
            generation_time=float(elapsed),
            layer_counts=layer_counts,
            config_used=config_payload,
            compute_warnings=merged_warnings,
            hdf5_path=manifest_path if persist else "",
        )

        try:
            self._registry.add(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "config_hash": config_hash,
                    "feature_count": result.feature_count,
                    "row_count": len(raw_data.index),
                    "hdf5_relative_path": result.hdf5_path,
                }
            )
        except Exception as exc:
            logger.warning("Failed to update feature registry: %s", exc)

        return result

    def _layer7_validate_and_persist(
        self,
        symbol: str,
        timeframe: str,
        raw_data: pd.DataFrame,
        layers: List[pd.DataFrame],
        config: "FactoryConfig",
        elapsed: float,
        config_hash: str,
        compute_warnings: Optional[List[str]] = None,
        persist: bool = True,
    ) -> FeatureGenerationResult:
        if self._cgsa_enabled() and self._cgsa_registry is not None:
            return self._layer7_validate_and_persist_cgsa(
                symbol=symbol,
                timeframe=timeframe,
                raw_data=raw_data,
                config=config,
                elapsed=elapsed,
                config_hash=config_hash,
                compute_warnings=compute_warnings,
                persist=persist,
            )

        features_df = self._combine_layers(layers, context="layer7_final")
        features_df = features_df.reindex(raw_data.index)
        if not features_df.empty:
            # copy=False: if already float32 (memmap), avoids duplicating 11+ GB
            features_df = features_df.astype("float32", copy=False)
        # Add timeframe tag to all feature columns so single-TF and multi-TF outputs
        # share the same naming convention (e.g. ema_20 → ema_12h_20).
        if not features_df.empty:
            features_df = self._apply_timeframe_tag(features_df, timeframe)

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
            "compute_warnings": compute_warnings or [],
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
            compute_warnings=compute_warnings or [],
        )

        validation = self._validator.validate_factory_output(result)
        metadata["validation"] = validation.__dict__
        metadata["feature_names"] = list(result.features_df.columns)
        metadata["feature_count"] = int(result.features_df.shape[1])
        result.metadata = metadata
        result.feature_count = int(result.features_df.shape[1])

        if persist:
            result.hdf5_path = self._storage.save_factory_output(symbol, timeframe, result)
        else:
            result.hdf5_path = ""

        try:
            self._registry.add(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "config_hash": config_hash,
                    "feature_count": len(result.features_df.columns),
                    "row_count": len(result.features_df.index),
                    "hdf5_relative_path": result.hdf5_path,
                }
            )
        except Exception as exc:
            logger.warning("Failed to update feature registry: %s", exc)

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

    def _compute_config_hash(
        self,
        config: "FactoryConfig",
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        config_payload = config.model_dump(by_alias=True)
        timeframes = config_payload.get("timeframes")
        if isinstance(timeframes, dict) and isinstance(timeframes.get("training"), list):
            # Canonicalize list order so semantically identical training TF sets share cache key.
            timeframes["training"] = sorted(timeframes["training"])
        kline_last_ts = self._adapter_registry.get_last_timestamp(symbol, timeframe)
        config_payload["_kline_last_ts"] = kline_last_ts
        config_payload["_start_date"] = start_date
        config_payload["_end_date"] = end_date
        # Explicitly include timeframe kwarg in hash to ensure 12h/1h results never share cache.
        config_payload["_timeframe"] = timeframe
        payload = json.dumps(config_payload, sort_keys=True, default=str)
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
    def _apply_timeframe_tag(features_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Add timeframe tag to feature column names (e.g. ``ema_20`` → ``ema_12h_20``).

        Columns that already carry a timeframe tag or start with ``label_`` prefix
        are left unchanged.  ``meta_`` columns also get tagged to avoid duplicate
        names when merging multi-TF outputs.  The convention matches
        ``MultiTFGenerator._apply_timeframe_tag`` so single-TF and multi-TF outputs
        share the same naming scheme.
        """
        from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
        tf_keys = set(TimeframeAligner._timeframe_seconds_keys())

        def _rename(col: str) -> str:
            if col.startswith("label_"):
                return col  # Labels come from primary TF only, no TF tag needed
            # meta_ columns MUST be tagged with TF prefix (meta_1h_*, meta_12h_*)
            # to stay consistent with MultiTFGenerator._apply_timeframe_tag.
            parts = col.split("_")
            if len(parts) < 2:
                return col
            if parts[1] in tf_keys:
                return col  # already tagged
            return "_".join([parts[0], timeframe] + parts[1:])

        rename_map = {col: _rename(col) for col in features_df.columns}
        return features_df.rename(columns=rename_map)

    @staticmethod
    def _combine_layers(layers: List[pd.DataFrame], context: str = "unknown") -> pd.DataFrame:
        # In CGSA mode, skip the heavyweight multi-layer merge used for L7 and
        # multi-TF final merge.  Internal single-layer concats (layer3_input,
        # layer4_input, layer5_input) still need to materialize a DF because
        # the computation engines expect a pandas DataFrame as input.
        _cgsa_skip_contexts = {"layer6_5_input", "layer7_final", "multi_tf_merged"}
        if FeatureFactory._cgsa_enabled() and context in _cgsa_skip_contexts:
            logger.info("[CGSA] Skip _combine_layers in context=%s (registry-based path)", context)
            return pd.DataFrame()

        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()

        from momentum.FeatureEngineering.memmap_utils import concat_with_memmap

        combined = concat_with_memmap(valid_layers)

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
            # Memmap-safe dedup: .loc[:, ~mask] on a memmap-backed DF forces a
            # full in-memory copy (11+ GB → OOM).  Use contiguous-range copy
            # into a new memmap instead.
            keep_mask = ~combined.columns.duplicated(keep="first")
            est_bytes = combined.shape[0] * int(keep_mask.sum()) * 4
            if est_bytes >= 500_000_000:
                import numpy as _np
                from momentum.FeatureEngineering.memmap_utils import create_temp_memmap

                keep_idx = _np.where(keep_mask)[0]
                n_keep = len(keep_idx)
                n_rows = combined.shape[0]
                out = create_temp_memmap((n_rows, n_keep), prefix="dedup_")
                src = combined.values  # underlying memmap or array

                # Copy in contiguous ranges (typically ~12 ranges for 11 dups)
                dst = 0
                i = 0
                while i < n_keep:
                    s = int(keep_idx[i])
                    rlen = 1
                    while i + rlen < n_keep and int(keep_idx[i + rlen]) == s + rlen:
                        rlen += 1
                    out[:, dst : dst + rlen] = src[:, s : s + rlen]
                    dst += rlen
                    i += rlen

                combined = pd.DataFrame(
                    data=out,
                    index=combined.index,
                    columns=combined.columns[keep_idx].tolist(),
                    copy=False,
                )
            else:
                combined = combined.loc[:, keep_mask]
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
        dt_index = FeatureFactory._coerce_index_to_datetime(raw_data.index)
        valid = dt_index[dt_index.notna()]
        if valid.empty:
            return []
        start = valid.min()
        end = valid.max()
        if pd.isna(start) or pd.isna(end):
            return []
        return [start.isoformat(), end.isoformat()]

    @staticmethod
    def _coerce_index_to_datetime(index: pd.Index) -> pd.Series:
        """Convert an index to datetime with robust epoch unit inference.

        Kline timestamps in this project may be stored in seconds or milliseconds.
        Always forcing unit="ms" can silently shift second-based epochs to 1970,
        which then causes date-range filtering to drop all rows.
        """
        if index is None:
            return pd.Series(dtype="datetime64[ns]")

        index_series = pd.Series(index)

        if pd.api.types.is_numeric_dtype(index_series):
            numeric = pd.to_numeric(index_series, errors="coerce")
            max_abs = numeric.abs().max(skipna=True)
            if pd.notna(max_abs):
                if max_abs >= 1_000_000_000_000_000_000:
                    unit = "ns"
                elif max_abs >= 1_000_000_000_000_000:
                    unit = "us"
                elif max_abs >= 1_000_000_000_000:
                    unit = "ms"
                else:
                    unit = "s"

                parsed = pd.to_datetime(numeric, unit=unit, errors="coerce")
                fallback = pd.to_datetime(index_series, errors="coerce")
                return parsed.where(parsed.notna(), fallback)

        return pd.to_datetime(index_series, errors="coerce")

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
            raw_params = info.get("params") or {}
            # params from _build_metadata_entries is a dict e.g. {"timeperiod": 21}.
            # list(dict) iterates keys, not values — extract values explicitly.
            if isinstance(raw_params, dict):
                params_list = [v for v in raw_params.values() if isinstance(v, (int, float))]
            else:
                params_list = [v for v in raw_params if isinstance(v, (int, float))]
            indicator_specs[name] = {
                "source": info.get("source"),
                "category": info.get("category"),
                "indicator": info.get("indicator"),
                "params": params_list,
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

    # ------------------------------------------------------------------
    # Phase 5: Multi-symbol parallel execution
    # ------------------------------------------------------------------

    def run_multi_symbol(
        self,
        symbols: List[str],
        config_override: Optional[dict] = None,
        max_workers: int = 8,
        ref_symbol: str = "BTCUSDT",
        timeout_per_symbol: int = 600,
        cache_dir: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Run the feature pipeline for multiple symbols in parallel.

        Uses ProcessPoolExecutor with spawn context to avoid fork-related
        issues with TA-Lib C globals and Numba JIT.

        Returns:
            (results, errors) where results maps symbol → metadata dict,
            and errors maps symbol → error message string.
        """
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed

        # Step 1: Numba warm-up in main process (cache compiled functions)
        _warmup_numba_functions()

        # Step 2: Resolve config
        config = self._resolve_config(config_override)
        config_payload = config.model_dump(by_alias=True)

        # Step 3: Prepare reference data as Arrow IPC for zero-copy sharing
        ref_ipc_path: Optional[str] = None
        try:
            from momentum.FeatureEngineering.arrow_ipc_utils import write_reference_data_ipc
            ref_data = self._load_reference_if_available(ref_symbol, config)
            if ref_data is not None:
                import tempfile
                work_dir = Path(tempfile.mkdtemp(prefix="ffact_multi_"))
                ipc_path = write_reference_data_ipc(ref_data, work_dir, ref_symbol)
                ref_ipc_path = str(ipc_path)
        except Exception as exc:
            logger.warning("Reference data IPC preparation failed: %s", exc)

        # Step 4: spawn context (mandatory on macOS for TA-Lib safety)
        ctx = mp.get_context("spawn")
        effective_workers = min(max_workers, len(symbols))

        results: Dict[str, Any] = {}
        errors: Dict[str, str] = {}

        with ProcessPoolExecutor(max_workers=effective_workers, mp_context=ctx) as pool:
            futures = {
                pool.submit(
                    _worker_entry,
                    sym,
                    config_payload,
                    cache_dir,
                    ref_ipc_path,
                ): sym
                for sym in symbols
            }
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    results[sym] = future.result(timeout=timeout_per_symbol)
                except Exception as exc:
                    errors[sym] = str(exc)
                    logger.error("Symbol %s failed: %s", sym, exc)

        logger.info(
            "Multi-symbol run complete: %d succeeded, %d failed",
            len(results),
            len(errors),
        )
        return results, errors

    def _load_reference_if_available(
        self,
        ref_symbol: str,
        config: "FactoryConfig",
    ) -> Optional[pd.DataFrame]:
        """Try to load reference symbol data from cache."""
        try:
            training_tfs = list(dict.fromkeys(config.timeframes.training))
            tf = training_tfs[0] if training_tfs else "1h"
            cached = self._reference_data_cache.get((ref_symbol, tf))
            if cached is not None:
                return cached
            # Attempt adapter fetch
            raw = self._layer0_data_ingestion(ref_symbol, tf, config)
            return raw
        except Exception:
            return None


def _worker_entry(
    symbol: str,
    config_payload: dict,
    cache_dir: Optional[str],
    ref_ipc_path: Optional[str],
) -> dict:
    """Module-level worker function for ProcessPoolExecutor (must be picklable).

    Each worker creates its own FeatureFactory instance with an independent
    ColumnGroupRegistry — no shared mutable state across workers.
    """
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=cache_dir, validate_continuity=False)

    # Inject reference data from Arrow IPC if available
    if ref_ipc_path:
        try:
            from momentum.FeatureEngineering.arrow_ipc_utils import read_reference_data_ipc
            ref_df = read_reference_data_ipc(Path(ref_ipc_path))
            config_tfs = config_payload.get("timeframes", {}).get("training", ["1h"])
            tf = config_tfs[0] if config_tfs else "1h"
            factory._reference_data_cache[("BTCUSDT", tf)] = ref_df
        except Exception:
            pass  # Proceed without reference data

    result = factory.generate_features(
        symbol=symbol,
        timeframe=config_payload.get("timeframes", {}).get("training", ["1h"])[0] if config_payload.get("timeframes", {}).get("training") else "1h",
        config_override=config_payload,
        force_regenerate=True,
    )
    return result.metadata or {}


def _warmup_numba_functions() -> None:
    """Pre-compile all Numba @njit functions in the main process.

    Workers started via spawn inherit the Numba cache from __pycache__,
    avoiding redundant JIT compilation across 8 workers.
    """
    try:
        from momentum.FeatureEngineering.operators.numba_rolling import (
            fused_rolling_stats,
            rolling_rank,
            rolling_skew_kurt,
            rolling_slope,
        )
        dummy = np.random.randn(100).astype(np.float64)
        fused_rolling_stats(dummy, 5)
        rolling_rank(dummy, 5)
        rolling_slope(dummy, 5)
        rolling_skew_kurt(dummy, 5, 50)
        logger.info("[warmup] Numba JIT functions pre-compiled successfully")
    except Exception as exc:
        logger.warning("[warmup] Numba JIT warmup failed (non-fatal): %s", exc)
