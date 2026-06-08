"""Feature factory pipeline skeleton for FeatureEngineering."""

from __future__ import annotations

import re
import os
import copy
import gc
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import time
import threading
import psutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Tuple

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.config import get_fracdiff_layers, get_ic_first_pipeline_enabled
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
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry, ColumnGroupRegistryError
from momentum.FeatureEngineering.timeframe.tf_aligner import CURRENT_MTF_ALIGN_VERSION
from momentum.FeatureEngineering.preprocessing._d_star_cache import (
    PreprocessingContext,
    WEAK_FINGERPRINT,
    compute_data_fingerprint,
    compute_feature_schema_hash,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


logger = get_logger(__name__)
_PROC = psutil.Process()  # Cached for low-overhead RSS sampling

# ── Pathological-input warnings: surface once, then stay quiet ──────────
# These two warnings come from real input pathologies (not bugs) and were
# previously flooding the log in tens of thousands of lines, hiding the
# real progress / error messages:
#   1. pandas overflow-on-cast: ratio features (e.g. ms_large_trade_ratio)
#      whose denominator approaches 0 produce 1e30+ values; float32 cast
#      yields ±inf. Final values get clipped by L6.5 winsorization.
#   2. statsmodels divide-by-zero in log: OLS on constant rolling windows
#      (zero residuals → log(0)=-inf in log-likelihood). Same downstream
#      handling.
# Using "once" preserves first-occurrence visibility (so we still see the
# location during debugging) while preventing log flooding. The L7
# validation scan tracks aggregate inf_count so we never *lose* visibility.
warnings.filterwarnings(
    "once",
    message="overflow encountered in cast",
    category=RuntimeWarning,
    module=r"pandas\.core\.nanops",
)
warnings.filterwarnings(
    "once",
    message="divide by zero encountered in log",
    category=RuntimeWarning,
    module=r"statsmodels\.regression\.linear_model",
)

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


@dataclass
class MemoryBudgetSnapshot:
    rss_before_gb: float
    rss_after_gb: float
    released_gb: float
    available_after_gb: float
    required_available_gb: float


class _PeakRssTracker:
    def __init__(self, label: str, interval_seconds: float = 0.02) -> None:
        self.label = label
        self.interval_seconds = interval_seconds
        self.peak_rss_gb = 0.0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __enter__(self) -> "_PeakRssTracker":
        self.peak_rss_gb = _current_rss_gb()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.peak_rss_gb = max(self.peak_rss_gb, _current_rss_gb())

    def _sample(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.peak_rss_gb = max(self.peak_rss_gb, _current_rss_gb())


class _MemoryProfiler:
    def track(self, label: str) -> _PeakRssTracker:
        return _PeakRssTracker(label)


def _current_rss_gb() -> float:
    import psutil

    return psutil.Process().memory_info().rss / float(1024**3)


def _available_ram_gb() -> float:
    import psutil

    return psutil.virtual_memory().available / float(1024**3)


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
        self._current_config_hash: Optional[str] = None
        self._current_raw_data: Optional[pd.DataFrame] = None
        self._reference_data_cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        self._cgsa_registry: Optional[ColumnGroupRegistry] = None
        self._cgsa_force_fresh: bool = False
        self._memory_profiler = _MemoryProfiler()
        self._ic_engine: Optional[Any] = None

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
        self._current_config_hash = None
        self._cgsa_registry = None
        start_time = time.time()

        config_hash = self._compute_config_hash(
            config,
            symbol,
            timeframe,
            start_date=start_date,
            end_date=end_date,
        )
        self._current_config_hash = config_hash
        if not force_regenerate:
            cached = self._try_load_cache(symbol, timeframe, config_hash)
            if cached:
                return cached

        self._cgsa_force_fresh = force_regenerate
        self._cgsa_registry = self._prepare_cgsa_registry(symbol, timeframe, config_hash or "")

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
        if self._cgsa_enabled() and self._cgsa_registry is not None:
            self._persist_single_tf_l3_l6_to_cgsa(layer3, layer4, layer5, layer6)
            return self._layer7_raw_from_cgsa_pipeline(
                symbol=symbol,
                timeframe=timeframe,
                raw_data=raw_data,
                config=config,
                elapsed=time.time() - start_time,
                config_hash=config_hash,
                compute_warnings=compute_warnings,
                persist=persist,
            )

        _ic_first_on = self._ic_first_enabled(config)
        if config.preprocessing.enabled:
            all_features = self._combine_layers(layers, context="layer6_5_input")
            if _ic_first_on:
                # IC-First: only run winsorization + fracdiff/ADF at generation time.
                # Rank / Z-Score / Gaussian are intentionally skipped here; they will be
                # optional downstream transforms after L7_raw is produced.
                logger.info(
                    "[IC-First] Generation mode: skipping rank/zscore/gaussian. "
                    "IC Gatekeeper and selected transforms are downstream actions after L7_raw."
                )
                preprocessed = self._safe_execute(
                    "Layer 6.5 (IC-First)", self._layer6_5_pre_ic, all_features, config
                )
            else:
                preprocessed = self._safe_execute(
                    "Layer 6.5", self._layer6_5_legacy, all_features, config
                )
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
            logger.info("%s starting, rss=%dMB", layer_name, _PROC.memory_info().rss >> 20)
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
            logger.info("%s done: %d cols, rss=%dMB", layer_name, result.shape[1], _PROC.memory_info().rss >> 20)
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
        config_hash: str = "",
    ) -> Optional[ColumnGroupRegistry]:
        if not self._cgsa_enabled():
            return None

        configured_work_dir = os.getenv("FFACT_CGSA_WORK_DIR", "").strip()
        if configured_work_dir:
            work_dir = Path(configured_work_dir).expanduser().resolve()
        else:
            safe_symbol = re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol)
            safe_timeframe = re.sub(r"[^A-Za-z0-9_.-]+", "_", timeframe)
            normalized_config_hash = config_hash or ""
            hash_prefix = normalized_config_hash[:8] if normalized_config_hash else "nohash"
            work_dir = (
                Path.cwd()
                / "data_cache"
                / "cgsa_work"
                / f"{safe_symbol}_{safe_timeframe}_{hash_prefix}"
            ).resolve()

        work_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = work_dir / "manifest.json"
        force_fresh = bool(getattr(self, "_cgsa_force_fresh", False))
        if manifest_path.exists() and not force_fresh:
            try:
                with manifest_path.open("r", encoding="utf-8") as handle:
                    manifest_payload = json.load(handle)
                if "groups" not in manifest_payload:
                    raise KeyError("groups")
                logger.info("[CGSA] Resuming from manifest at %s", work_dir)
                return ColumnGroupRegistry.resume_from_manifest(work_dir)
            except (json.JSONDecodeError, KeyError, OSError, ColumnGroupRegistryError) as exc:
                logger.warning(
                    "[CGSA] Corrupt manifest at %s: %s, starting fresh",
                    work_dir,
                    exc,
                )

        from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config

        tier = get_memory_tier()
        tier_cfg = get_tier_config(tier)
        buffer_groups = self._parse_positive_int_env(
            "FFACT_CGSA_MEMORY_BUFFER",
            int(tier_cfg["cgsa_memory_buffer"]),
        )

        logger.info(
            "[CGSA] Initialized ColumnGroupRegistry at %s (tier=%s, buffer_groups=%d)",
            work_dir,
            tier,
            buffer_groups,
        )
        return ColumnGroupRegistry(
            work_dir=work_dir,
            memory_buffer_groups=buffer_groups,
        )

    @staticmethod
    def _parse_positive_int_env(env_name: str, default: int) -> int:
        """Parse a non-negative integer env var with fallback to default."""

        raw_value = os.getenv(env_name, str(default)).strip()
        try:
            parsed_value = int(raw_value)
        except ValueError:
            parsed_value = default
        return max(0, parsed_value)

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
            self._log_persisted_group_shards(group_id, "L1")

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
        self._log_persisted_group_shards(group_id, "L2")

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
            self._log_persisted_group_shards(group_id, label)

        logger.info(
            "[CGSA] Persisted %s: %d cols → %d groups (tf=%s)",
            label, n_cols, chunk_idx, self._current_timeframe,
        )

    def _log_persisted_group_shards(self, group_id: str, label: str) -> None:
        """Emit one INFO line per persisted group showing shard layout.

        For single-shard small groups this is a no-op (only sharded groups
        with >1 shards or large total bytes are logged).
        """
        if self._cgsa_registry is None:
            return
        try:
            group = self._cgsa_registry.get(group_id)
        except Exception:
            return
        n_shards = len(getattr(group, "shards", ()) or ())
        total_bytes = int(getattr(group, "total_shard_bytes", 0) or 0)
        if n_shards <= 1 and total_bytes < (64 << 20):
            return
        logger.info(
            "[CGSA] %s persisted group=%s shards=%d total_bytes=%.1f MiB",
            label,
            group_id,
            max(n_shards, 1),
            total_bytes / (1024 * 1024),
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

        # Cascade blacklist：阻斷 CDL/HT_DCPHASE 進入 L2 衍生計算
        # L1 原始欄位保留於 feature store，此處只是不傳給 L2 operators
        layer1_for_l2 = self._apply_cascade_blacklist(layer1, "L2_input", config)

        if layer1_for_l2.empty:
            result = pd.DataFrame(index=layer1.index)
        elif not getattr(config.operators, 'enabled', True):
            result = pd.DataFrame(index=layer1.index)
        else:
            from momentum.FeatureEngineering.polars_adapter import polars_enabled

            use_polars = polars_enabled()
            if use_polars:
                result = self._layer2_derived_polars(layer1_for_l2, data, config)
            else:
                result = self._layer2_derived_pandas(layer1_for_l2, data, config)

        elapsed = time.perf_counter() - t0
        logger.info("[L2] Completed: %d cols in %.2fs", result.shape[1], elapsed)
        return result

    def _layer2_derived_pandas(
        self, layer1: pd.DataFrame, data: pd.DataFrame, config: "FactoryConfig"
    ) -> pd.DataFrame:
        """Legacy pandas path for L2 derived features.

        P1.3 — When per-category mode is in effect (registry persistence),
        the seven operator categories (Distance / Cross / Ratio / Momentum /
        BinarySignal / SignedStrength / WorldQuant) are dispatched to a
        ThreadPool. Many of the inner pandas / numpy ops release the GIL,
        delivering measurable parallelism on 4-8 core machines without the
        spawn overhead of a ProcessPool. Persistence to the registry remains
        serialised in the main thread to avoid concurrent-write races.
        """
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

        from momentum.FeatureEngineering.utils.hardware_utils import get_l2_category_workers

        category_workers = get_l2_category_workers()
        categories = list(DerivedOperatorEngine.OPERATOR_CATEGORIES)

        if category_workers <= 1 or len(categories) <= 1:
            # Serial fallback (or trivial single-category case).
            category_frames: List[pd.DataFrame] = []
            for category in categories:
                category_frame = engine.compute_category(layer1, data, indicator_specs, category)
                if category_frame is None or category_frame.empty:
                    continue
                self._persist_layer2_category_group(category, category_frame)
                category_frames.append(category_frame)
        else:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            t0 = time.perf_counter()
            computed_frames: Dict[str, pd.DataFrame] = {}
            with ThreadPoolExecutor(max_workers=category_workers) as pool:
                futures = {
                    pool.submit(
                        engine.compute_category, layer1, data, indicator_specs, category
                    ): category
                    for category in categories
                }
                for fut in as_completed(futures):
                    category = futures[fut]
                    try:
                        category_frame = fut.result()
                    except Exception as error:
                        logger.error(
                            "[L2] Category %s failed: %s", category, error, exc_info=True
                        )
                        continue
                    if category_frame is None or category_frame.empty:
                        continue
                    computed_frames[category] = category_frame

            # Serial persistence in the original category order keeps registry
            # writes single-threaded and downstream concat order deterministic.
            category_frames = []
            for category in categories:
                category_frame = computed_frames.get(category)
                if category_frame is None:
                    continue
                self._persist_layer2_category_group(category, category_frame)
                category_frames.append(category_frame)

            logger.info(
                "[L2] Parallel categories: %d/%d categories (%d workers) in %.2fs",
                len(category_frames),
                len(categories),
                category_workers,
                time.perf_counter() - t0,
            )

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
        # Cascade blacklist：阻斷 CDL/HT_DCPHASE 進入 L3 rolling
        base = self._apply_cascade_blacklist(base, "L3_input", config)
        if base.empty:
            return pd.DataFrame(index=base.index)
        filtered_config = self._filter_rolling_config(config.rolling_aggregation)
        aggregator = RollingAggregator(filtered_config)

        # Plan A: streaming persist when CGSA is enabled and tier prefers it.
        # The persister buffers small chunks per step and flushes to
        # ColumnGroupRegistry as soon as buffer reaches the tier-specific limit,
        # so the wide L3 DataFrame (~10 GB at 1h timeframe) is never materialised.
        from momentum.FeatureEngineering.utils.hardware_utils import (
            get_l3_persist_mode,
            get_l3_streaming_buffer_cols,
        )
        persist_mode = get_l3_persist_mode()
        if self._cgsa_enabled() and self._cgsa_registry is not None and persist_mode in {"streaming", "hybrid"}:
            persister = _StreamingL3Persister(
                factory=self,
                layer=LayerSource.L3,
                label_prefix="L3_rolling",
                buffer_cols=get_l3_streaming_buffer_cols(),
            )
            try:
                _ = aggregator.compute_all(base, persist_callback=persister)
            finally:
                persister.flush_all()
            logger.info(
                "[L3] streaming persist (mode=%s) complete: %d cols persisted in %d groups",
                persist_mode, persister.total_cols, persister.total_groups,
            )
            # Return an empty DataFrame keyed by the input index so downstream
            # layers (L4 fast path uses only L1+raw) compose correctly.
            return pd.DataFrame(index=base.index)

        # Classic in-memory path (tier_xlarge or CGSA disabled).
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
        # Cascade blacklist：阻斷 CDL/HT_DCPHASE 進入 L4 lag（含 non-CGSA fallback 路徑）
        base = self._apply_cascade_blacklist(base, f"L4_input[{apply_to}]", config)
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

    def run_ic_first_pipeline(
        self,
        symbol: str,
        tf: str,
        config: "FactoryConfig",
        *,
        raw_data: Optional[pd.DataFrame] = None,
        layers: Optional[List[pd.DataFrame]] = None,
        config_hash: Optional[str] = None,
        compute_warnings: Optional[List[str]] = None,
        start_time: Optional[float] = None,
        persist: bool = True,
        label: Optional[pd.Series] = None,
        ic_engine: Optional[Any] = None,
        feature_reader: Optional[Any] = None,
        storage: Optional[FeatureStorage] = None,
        ic_threshold: Optional[float] = None,
        allow_partial_ic: bool = False,
        label_horizon: str = "1_bar_forward_return",
        selection_window: Optional[Dict[str, Any]] = None,
        split_id: Optional[str] = None,
        cleanup_raw: bool = False,
    ) -> FeatureGenerationResult:
        """Run the IC-First pipeline with raw persist, GC gate, IC, and processed persist.

        Parameters
        ----------
        cleanup_raw:
            When *True* the ``raw/`` artifact directory is deleted immediately
            after ``processed/`` is successfully written.  Default is *False*
            because this is a research platform: re-running IC with a different
            method or window requires raw/ to be present, and regenerating 100+
            symbols takes hours.  Set *True* only in production ETL pipelines
            where disk space is the bottleneck and re-generation is acceptable.
        """
        start = start_time if start_time is not None else time.time()
        resolved_config_hash = config_hash or self._current_config_hash or self._compute_config_hash(
            config,
            symbol,
            tf,
        )
        self._current_symbol = symbol
        self._current_timeframe = tf
        self._current_config_hash = resolved_config_hash
        if not hasattr(self, "_progress_callback"):
            self._progress_callback = None
        if not hasattr(self, "_cgsa_registry"):
            self._cgsa_registry = None
        if not hasattr(self, "_reference_data_cache"):
            self._reference_data_cache = {}

        storage_manager = storage or getattr(self, "_storage", None) or FeatureStorage()
        resolved_reader = feature_reader or self._build_feature_reader_for_storage(storage_manager)
        resolved_ic_engine = ic_engine or getattr(self, "_ic_engine", None)
        if resolved_ic_engine is None:
            raise ValueError("run_ic_first_pipeline requires an injected ic_engine")

        if raw_data is None or layers is None:
            raw_data, layers = self._run_l1_l6_for_ic_first(symbol, tf, config)
        self._current_raw_data = raw_data

        if label is None:
            label = self._build_default_ic_label(raw_data)

        if selection_window is None and split_id is None:
            selection_window = {"start_pos": 0, "end_pos": int(len(label))}
            split_id = "ic_first_full_window"

        all_features = self._combine_layers(layers, context="ic_first_l65_pre_input")
        pre_ic_frame = self._safe_execute("Layer 6.5 pre_ic", self._layer6_5_pre_ic, all_features, config)
        pre_ic_groups = self._frame_to_l7_groups(pre_ic_frame, "pre_ic")
        raw_feature_count = sum(len(frame.columns) for frame in pre_ic_groups.values())
        raw_path = storage_manager.write_raw(
            symbol,
            tf,
            resolved_config_hash,
            pre_ic_groups,
            row_index=self._derive_row_index_for_artifact(raw_data),
        )

        rss_before_gc_gb = _current_rss_gb()
        del pre_ic_groups
        del pre_ic_frame
        del all_features
        del layers
        gc.collect()
        memory_snapshot = self._check_ic_memory_budget_after_raw_persist(
            rss_before_gc_gb,
            config,
        )

        peak_budget_gb = self._resolve_tier_peak_budget_gb(config)
        memory_profiler = getattr(self, "_memory_profiler", _MemoryProfiler())
        with memory_profiler.track("run_ic_gate") as ic_memory:
            ic_result = resolved_ic_engine.compute_ic_from_l7_raw(
                symbol,
                tf,
                resolved_config_hash,
                label,
                feature_reader=resolved_reader,
                ic_threshold=ic_threshold,
                allow_partial_ic=allow_partial_ic,
                method=None,
                label_horizon=label_horizon,
                selection_window=selection_window,
                split_id=split_id,
            )
        if float(ic_memory.peak_rss_gb) > peak_budget_gb:
            raise MemoryError(
                "IC-First: run_ic_gate peak RSS "
                f"{ic_memory.peak_rss_gb:.2f} GB > tier budget {peak_budget_gb:.2f} GB"
            )

        selected_features = self._extract_ic_selected_features(ic_result)
        if selected_features:
            selected_raw = resolved_reader.load_columns_v2(
                symbol,
                tf,
                resolved_config_hash,
                selected_features,
                artifact_kind="raw",
            )
            raw_selected_groups = self._frame_to_l7_groups(selected_raw, "selected")
        else:
            logger.warning("[IC-First] IC selection is empty; writing empty processed artifact")
            raw_selected_groups = {}

        preprocessor = FeaturePreprocessor(
            self._preprocessing_config_dict(config),
            context=self._build_preprocessing_context(raw_data, config),
        )
        processed_groups = preprocessor.transform_selected(
            selected_features,
            raw_selected_groups,
            config.preprocessing,
        )
        del raw_selected_groups
        gc.collect()

        processed_path = storage_manager.write_processed(
            symbol,
            tf,
            resolved_config_hash,
            processed_groups,
        )

        # IC-First raw/ cleanup: raw/ was needed only for the IC gate step.
        # After processed/ is safely on disk, reclaim that space immediately.
        # The IC metadata (selected features, scores) is preserved in the
        # returned FeatureGenerationResult so re-analysis does not need raw/.
        raw_freed_gb = 0.0
        if cleanup_raw and raw_path.exists():
            try:
                raw_size_bytes = sum(
                    f.stat().st_size for f in raw_path.rglob("*") if f.is_file()
                )
                import shutil as _ic_shutil
                _ic_shutil.rmtree(raw_path)
                raw_freed_gb = raw_size_bytes / 1_073_741_824
                logger.info(
                    "[IC-First] Cleaned up raw/ artifact (%.2f GB freed): %s",
                    raw_freed_gb,
                    raw_path,
                )
            except Exception as _cleanup_exc:
                logger.warning(
                    "[IC-First] raw/ cleanup failed (non-fatal, disk will not be reclaimed): %s",
                    _cleanup_exc,
                )
        processed_feature_count = sum(len(frame.columns) for frame in processed_groups.values())
        del processed_groups
        gc.collect()

        labels_df = label.to_frame(name=label.name or "label")
        metadata = {
            "symbol": symbol,
            "timeframe": tf,
            "config_hash": resolved_config_hash,
            "ic_first_pipeline": True,
            "raw_path": str(raw_path),
            "processed_path": str(processed_path),
            "selected_features": selected_features,
            "selected_count": len(selected_features),
            "raw_feature_count": raw_feature_count,
            "processed_feature_count": processed_feature_count,
            "memory_budget": memory_snapshot.__dict__,
            "run_ic_gate_peak_rss_gb": float(ic_memory.peak_rss_gb),
            "tier_peak_budget_gb": peak_budget_gb,
            "persist_requested": bool(persist),
            "raw_cleaned_up": cleanup_raw and not raw_path.exists(),
            "raw_freed_gb": raw_freed_gb,
        }
        logger.info(
            "[IC-First] post_ic done: symbol=%s tf=%s selected=%d processed_features=%d peak_rss_gb=%.2f",
            symbol,
            tf,
            len(selected_features),
            processed_feature_count,
            float(ic_memory.peak_rss_gb),
        )
        return FeatureGenerationResult(
            features_df=pd.DataFrame(index=raw_data.index if raw_data is not None else None),
            labels_df=labels_df,
            metadata=metadata,
            feature_count=processed_feature_count,
            generation_time=float(time.time() - start),
            layer_counts={
                "layer6_5_raw": int(raw_feature_count),
                "layer7_processed": int(processed_feature_count),
            },
            config_used=self._config_payload(config),
            hdf5_path=str(processed_path),
            compute_warnings=compute_warnings or [],
        )

    def _run_l1_l6_for_ic_first(
        self,
        symbol: str,
        tf: str,
        config: "FactoryConfig",
    ) -> Tuple[pd.DataFrame, List[pd.DataFrame]]:
        raw_data = self._layer0_data_ingestion(symbol, tf, config)
        self._current_raw_data = raw_data
        layer1 = self._safe_execute("Layer 1", self._layer1_atomic_indicators, raw_data, config)
        layer2 = self._safe_execute("Layer 2", self._layer2_derived_features, layer1, raw_data, config)
        layer2 = self._spill_to_memmap(layer2, "layer2")
        layer3 = self._safe_execute("Layer 3", self._layer3_rolling_aggregation, layer1, layer2, config)
        layer4 = self._safe_execute("Layer 4", self._layer4_lag_features, layer1, layer2, layer3, raw_data, config)
        layer5 = self._safe_execute("Layer 5", self._layer5_cross_sectional, layer1, layer2, config)
        layer6 = self._safe_execute("Layer 6", self._layer6_meta_features, layer1, layer2, raw_data, config)
        return raw_data, [layer1, layer2, layer3, layer4, layer5, layer6]

    @staticmethod
    def _frame_to_l7_groups(frame: pd.DataFrame, group_id: str) -> Dict[str, pd.DataFrame]:
        if frame is None or frame.empty:
            return {}
        return {group_id: frame}

    @staticmethod
    def _build_feature_reader_for_storage(storage: FeatureStorage) -> Any:
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        return FeatureReader(str(storage.base_path))

    @staticmethod
    def _build_default_ic_label(raw_data: pd.DataFrame) -> pd.Series:
        if raw_data is None or raw_data.empty or "close" not in raw_data.columns:
            raise ValueError("IC-First requires an explicit label or raw_data with close column")
        return raw_data["close"].astype(float).pct_change().shift(-1).rename("forward_return")

    @staticmethod
    def _extract_ic_selected_features(ic_result: Any) -> List[str]:
        if isinstance(ic_result, dict):
            selected = ic_result.get("selected", [])
        else:
            selected = getattr(ic_result, "selected", [])
        return [str(feature) for feature in selected]

    def _check_ic_memory_budget_after_raw_persist(
        self,
        rss_before_gc_gb: float,
        config: "FactoryConfig",
    ) -> MemoryBudgetSnapshot:
        rss_after_gc_gb = _current_rss_gb()
        available_after_gc_gb = _available_ram_gb()
        required_available_gb = self._resolve_required_available_gb(config)
        released_gb = rss_before_gc_gb - rss_after_gc_gb
        if available_after_gc_gb < required_available_gb:
            logger.error(
                "[IC-First] available RAM insufficient before run_ic_gate: %.2f GB < %.2f GB",
                available_after_gc_gb,
                required_available_gb,
            )
            raise MemoryError("IC-First: insufficient available RAM before run_ic_gate")
        logger.info(
            "[IC-First] gc diagnostic: released_gb=%.2f rss_after_gb=%.2f available_after_gb=%.2f required_available_gb=%.2f",
            released_gb,
            rss_after_gc_gb,
            available_after_gc_gb,
            required_available_gb,
        )
        return MemoryBudgetSnapshot(
            rss_before_gb=float(rss_before_gc_gb),
            rss_after_gb=float(rss_after_gc_gb),
            released_gb=float(released_gb),
            available_after_gb=float(available_after_gc_gb),
            required_available_gb=float(required_available_gb),
        )

    def _resolve_required_available_gb(self, config: "FactoryConfig") -> float:
        return self._resolve_config_float(config, "ic_gate_required_available_gb", 1.0)

    def _resolve_tier_peak_budget_gb(self, config: "FactoryConfig") -> float:
        try:
            from momentum.FeatureEngineering.utils.hardware_utils import get_current_tier_gb

            default_budget = max(float(get_current_tier_gb()) - 1.0, 1.0)
        except Exception:
            default_budget = 7.0
        return self._resolve_config_float(config, "tier_peak_budget_gb", default_budget)

    @staticmethod
    def _resolve_config_float(config: "FactoryConfig", field_name: str, default: float) -> float:
        candidates: List[Any] = [config, getattr(config, "preprocessing", None)]
        if isinstance(config, dict):
            candidates.extend([config.get("preprocessing"), config.get("memory")])
        model_extra = getattr(config, "model_extra", None)
        if isinstance(model_extra, dict):
            candidates.append(model_extra)

        for candidate in candidates:
            if candidate is None:
                continue
            value = None
            if isinstance(candidate, dict):
                value = candidate.get(field_name)
            else:
                value = getattr(candidate, field_name, None)
                extra = getattr(candidate, "model_extra", None)
                if value is None and isinstance(extra, dict):
                    value = extra.get(field_name)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                logger.warning("Invalid %s=%r; fallback to %.2f", field_name, value, default)
                return float(default)
        return float(default)

    @staticmethod
    def _config_payload(config: "FactoryConfig") -> Dict[str, Any]:
        if isinstance(config, dict):
            return copy.deepcopy(config)
        model_dump = getattr(config, "model_dump", None)
        if callable(model_dump):
            try:
                return model_dump(by_alias=True)
            except TypeError:
                return model_dump()
        return {}

    def _layer6_5_preprocessing(
        self,
        all_features: pd.DataFrame,
        config: "FactoryConfig",
        *,
        selected_features: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Layer 6.5: Feature preprocessing and normalization."""
        if self._ic_first_enabled(config):
            if selected_features is None:
                return self._layer6_5_pre_ic(all_features, config)
            return self._layer6_5_post_ic(all_features, config, selected_features)

        return self._layer6_5_legacy(all_features, config)

    @staticmethod
    def _ic_first_enabled(config: "FactoryConfig") -> bool:
        preprocessing = getattr(config, "preprocessing", None)
        config_enabled = bool(getattr(preprocessing, "ic_first_pipeline", False))
        return config_enabled or get_ic_first_pipeline_enabled()

    def _layer6_5_legacy(self, all_features: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        """Legacy Layer 6.5 path: apply preprocessing config to all features."""
        preprocessing_config = self._preprocessing_config_dict(config)
        return self._run_layer6_5_preprocessor(all_features, config, preprocessing_config)

    def _layer6_5_pre_ic(self, all_features: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        """Pre-IC path: winsorization plus FracDiff/ADF only."""
        preprocessing_config = self._preprocessing_config_dict(config)
        self._set_preprocessing_step_enabled(preprocessing_config, "rank_transform", False)
        self._set_preprocessing_step_enabled(preprocessing_config, "adaptive_zscore", False)
        self._set_preprocessing_step_enabled(preprocessing_config, "gaussian_normalize", False)
        logger.info("[IC-First] Layer 6.5 pre_ic enabled: winsorization/fracdiff/adf only")
        return self._run_layer6_5_preprocessor(all_features, config, preprocessing_config)

    def _build_l7_raw_preprocessing_config(self, config: "FactoryConfig") -> Dict[str, Any]:
        """Return the L6.5 config used by generation before writing L7_raw."""
        preprocessing_config = self._preprocessing_config_dict(config)
        if self._ic_first_enabled(config):
            self._set_preprocessing_step_enabled(preprocessing_config, "rank_transform", False)
            self._set_preprocessing_step_enabled(preprocessing_config, "adaptive_zscore", False)
            self._set_preprocessing_step_enabled(preprocessing_config, "gaussian_normalize", False)
        return preprocessing_config

    def _build_l7_raw_preprocessing_metadata(
        self,
        config: "FactoryConfig",
        raw_preprocessing_config: Optional[Dict[str, Any]],
        l65_mode: str,
    ) -> Dict[str, Any]:
        """Describe both requested preprocessing and what the raw artifact contains."""
        preprocessing = getattr(config, "preprocessing", None)
        config_enabled = bool(getattr(preprocessing, "enabled", False))
        raw_enabled = bool(raw_preprocessing_config) and config_enabled
        step_names = {
            "winsorization": "winsorization",
            "rank_transform": "rank_transform",
            "adaptive_zscore": "adaptive_zscore",
            "gaussian_normalize": "gaussian_normalize",
            "fractional_differencing": "fractional_differencing",
            "adf_differencing": "adf_differencing",
        }

        config_steps = {
            public_name: self._preprocessing_step_enabled(preprocessing, step_name)
            for public_name, step_name in step_names.items()
        }
        raw_steps = {
            public_name: self._preprocessing_step_enabled(raw_preprocessing_config, step_name)
            for public_name, step_name in step_names.items()
        }

        fracdiff_config = {}
        if isinstance(raw_preprocessing_config, dict):
            raw_fracdiff = raw_preprocessing_config.get("fractional_differencing")
            if isinstance(raw_fracdiff, dict):
                fracdiff_config = raw_fracdiff

        raw_artifact_applied = {
            "enabled": raw_enabled,
            "mode": l65_mode,
            "steps": raw_steps,
            "fracdiff_apply_to": fracdiff_config.get("apply_to"),
            "fracdiff_layers": sorted(get_fracdiff_layers()) if raw_steps["fractional_differencing"] else [],
        }

        return {
            "preprocessing_config_enabled": {
                "enabled": config_enabled,
                "ic_first_pipeline": self._ic_first_enabled(config),
                "steps": config_steps,
            },
            "raw_artifact_applied": raw_artifact_applied,
            # Backward-compatible flat fields. These now intentionally describe
            # the raw artifact, not merely the UI/config request.
            "preprocessing_enabled": raw_enabled,
            "rank_enabled": raw_steps["rank_transform"],
            "zscore_enabled": raw_steps["adaptive_zscore"],
            "gaussian_enabled": raw_steps["gaussian_normalize"],
            "fracdiff_enabled": raw_steps["fractional_differencing"],
            "adf_enabled": raw_steps["adf_differencing"],
        }

    def _resolve_l65_generation_mode(self, config: "FactoryConfig") -> str:
        # Phase B Phase 1 Step 36: strict three-way Mode A/B/C dispatch.
        # Modes:
        #   - "none"         (Mode C, L6.5 disabled passthrough)
        #   - "ic_first_pre" (Mode B, IC-First: Winsor + FracDiff/ADF only)
        #   - "legacy"       (Mode A, full L6.5 incl. Rank/ZScore/Gaussian)
        # Any combination that cannot be unambiguously resolved must raise
        # rather than silently default. Callers downstream rely on this exact
        # set of three values for cache invalidation and routing decisions.
        preprocessing = getattr(config, "preprocessing", None)
        if preprocessing is None:
            raise ValueError(
                "FactoryConfig.preprocessing is missing; cannot dispatch L6.5 mode "
                "(expected explicit Mode A/B/C selection)."
            )
        enabled_attr = getattr(preprocessing, "enabled", None)
        if enabled_attr is None:
            raise ValueError(
                "FactoryConfig.preprocessing.enabled is missing; cannot dispatch "
                "L6.5 mode (expected bool)."
            )
        if not bool(enabled_attr):
            return "none"
        if self._ic_first_enabled(config):
            return "ic_first_pre"
        return "legacy"

    def _layer6_5_post_ic(
        self,
        all_features: pd.DataFrame,
        config: "FactoryConfig",
        selected_features: List[str],
    ) -> pd.DataFrame:
        """Post-IC path: rank, zscore, and gaussian only for selected features."""
        selected_columns = [str(feature) for feature in selected_features]
        if not selected_columns:
            logger.warning("[IC-First] post_ic received no selected features; returning empty output")
            return pd.DataFrame(index=all_features.index if all_features is not None else None)

        if all_features is None and self._cgsa_registry is None:
            logger.warning("[IC-First] post_ic received no L6.5 input features")
            return pd.DataFrame()

        post_ic_features = all_features
        if all_features is not None:
            available_columns = [column for column in selected_columns if column in all_features.columns]
            missing_columns = [column for column in selected_columns if column not in all_features.columns]
            if missing_columns:
                logger.warning(
                    "[IC-First] post_ic skipped %d selected features missing from L6.5 input",
                    len(missing_columns),
                )
            if not available_columns:
                logger.warning("[IC-First] post_ic selected features are absent from L6.5 input")
                return pd.DataFrame(index=all_features.index)
            selected_columns = available_columns
            post_ic_features = all_features.loc[:, selected_columns].copy()

        preprocessing_config = self._preprocessing_config_dict(config)
        preprocessing_config["mode"] = "replace"
        self._set_preprocessing_step_enabled(preprocessing_config, "winsorization", False)
        self._set_preprocessing_step_enabled(preprocessing_config, "fractional_differencing", False)
        self._set_preprocessing_step_enabled(preprocessing_config, "adf_differencing", False)
        # 尊重使用者在 config 中的開關設定，而不是強制全開
        _rank_on = preprocessing_config.get("rank_transform", {}).get("enabled", True)
        _zscore_on = preprocessing_config.get("adaptive_zscore", {}).get("enabled", True)
        _gaussian_on = preprocessing_config.get("gaussian_normalize", {}).get("enabled", False)
        self._set_preprocessing_step_enabled(preprocessing_config, "rank_transform", _rank_on, selected_columns if _rank_on else None)
        self._set_preprocessing_step_enabled(preprocessing_config, "adaptive_zscore", _zscore_on, selected_columns if _zscore_on else None)
        self._set_preprocessing_step_enabled(preprocessing_config, "gaussian_normalize", _gaussian_on, selected_columns if _gaussian_on else None)
        logger.info(
            "[IC-First] Layer 6.5 post_ic enabled: transforming %d selected features",
            len(selected_columns),
        )
        return self._run_layer6_5_preprocessor(post_ic_features, config, preprocessing_config)

    def _run_layer6_5_preprocessor(
        self,
        all_features: pd.DataFrame,
        config: "FactoryConfig",
        preprocessing_config: Dict[str, Any],
    ) -> pd.DataFrame:
        # Cascade blacklist：阻斷 CDL/HT_DCPHASE 進入 L6.5 preprocessing
        # （legacy / ic_first_pre / post_ic 三 mode 都經由此函式 → 一處覆蓋全部）
        all_features = self._apply_cascade_blacklist(all_features, "L65_input", config)
        context = self._build_preprocessing_context(all_features, config)
        preprocessor = FeaturePreprocessor(preprocessing_config, context=context)

        if self._cgsa_enabled() and self._cgsa_registry is not None:
            from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config

            tier = get_memory_tier()
            tier_cfg = get_tier_config(tier)
            n_workers = self._parse_positive_int_env(
                "FFACT_L65_WORKERS",
                int(tier_cfg["l65_workers"]),
            )
            n_workers = max(1, n_workers)

            try:
                preprocessor.transform_registry_groups(
                    self._cgsa_registry,
                    n_workers=n_workers,
                )
            finally:
                self._cgsa_registry.finalize()
            # CGSA streaming path: L6.5 outputs live in CGSA registry, not in this
            # frame. L7 dead-feature drop on registry-side data is out of scope for
            # this step (see NAN_REDUCTION_STRATEGY.md §5.3 / PLAN §2.7).
            return pd.DataFrame(index=all_features.index if all_features is not None else None)

        # Classic in-memory path: apply L7 dead-feature drop on the transformed
        # frame (covers L1, L2, L4-fast/fallback, L5, L6 + L6.5 outputs).
        # See NAN_REDUCTION_STRATEGY.md §5.3 — drops ONLY constant/insufficient-
        # sample columns, NEVER drops by NaN ratio.
        result_frame = preprocessor.transform(all_features)
        return self._apply_l7_dead_feature_drop(result_frame, config)

    def _apply_cascade_blacklist(
        self,
        frame: pd.DataFrame,
        context: str,
        config: "FactoryConfig",
    ) -> pd.DataFrame:
        """Cascade categorical blacklist：阻斷 CDL_PATTERN_ALL / HT_DCPHASE 的下游 derivation。

        L1 原始欄位**保留**於最終 feature store；此處只剝離「進入下層 cascade 計算」的副本。

        詳見 docs/NAN_REDUCTION_STRATEGY.md §5.1 與 utils/cascade_blacklist.py。
        """
        from momentum.FeatureEngineering.utils.cascade_blacklist import (
            expand_blacklist_patterns,
            strip_blacklisted,
        )

        if frame is None or frame.empty or len(frame.columns) == 0:
            return frame
        nan_strategy = getattr(config, "nan_strategy", None)
        if nan_strategy is None:
            return frame
        patterns = getattr(nan_strategy, "categorical_blacklist", None) or []
        if not patterns:
            return frame
        blacklisted = expand_blacklist_patterns(patterns, frame.columns)
        if not blacklisted:
            return frame
        result = strip_blacklisted(frame, blacklisted)
        logger.info(
            "[NaN Blacklist][%s] stripped %d cols (e.g. %s)",
            context, len(blacklisted), list(blacklisted)[:3],
        )
        return result

    def _apply_l7_dead_feature_drop(
        self,
        frame: pd.DataFrame,
        config: "FactoryConfig",
    ) -> pd.DataFrame:
        """L7 死特徵清理（frame path）。

        Per-column drop only — never group-level（safety invariant I-1）。
        詳見 docs/NAN_REDUCTION_STRATEGY.md §5.3 與 utils/dead_feature_filter.py。
        """
        from momentum.FeatureEngineering.utils.dead_feature_filter import (
            drop_dead_columns,
            find_dead_columns,
        )

        if frame is None or frame.empty or len(frame.columns) == 0:
            return frame
        nan_strategy = getattr(config, "nan_strategy", None)
        if nan_strategy is None:
            return frame
        dead_cfg = getattr(nan_strategy, "l7_dead_feature_drop", None)
        if dead_cfg is None:
            return frame
        enabled = bool(getattr(dead_cfg, "enabled", True))
        min_valid = int(getattr(dead_cfg, "min_valid_samples", 100))

        dead, diag = find_dead_columns(frame, min_valid_samples=min_valid, enabled=enabled)
        if not dead:
            return frame
        result = drop_dead_columns(frame, dead)
        logger.info(
            "[L7 Dead Drop] dropped %d cols (constant=%d, sparse=%d); examples: %s",
            diag.total_dropped,
            len(diag.constant_cols),
            len(diag.sparse_cols),
            list(dead)[:5],
        )
        return result

    @staticmethod
    def _preprocessing_config_dict(config: "FactoryConfig") -> Dict[str, Any]:
        return copy.deepcopy(config.preprocessing.model_dump())

    @staticmethod
    def _set_preprocessing_step_enabled(
        preprocessing_config: Dict[str, Any],
        step_name: str,
        enabled: bool,
        apply_to: Optional[List[str]] = None,
    ) -> None:
        step_config = preprocessing_config.get(step_name)
        if not isinstance(step_config, dict):
            step_config = {}
            preprocessing_config[step_name] = step_config
        step_config["enabled"] = enabled
        if apply_to is not None:
            step_config["apply_to"] = list(apply_to)

    def _build_preprocessing_context(
        self,
        all_features: pd.DataFrame,
        config: "FactoryConfig",
    ) -> PreprocessingContext:
        symbol = self._current_symbol or "unknown"
        timeframe = self._current_timeframe or "unknown"
        config_hash = self._current_config_hash or ""
        raw_data = self._current_raw_data
        source_frame = raw_data if raw_data is not None and not raw_data.empty else all_features

        feature_columns: List[str]
        if self._cgsa_registry is not None:
            feature_columns = list(self._cgsa_registry.all_column_names())
        elif all_features is not None:
            feature_columns = [str(column) for column in all_features.columns]
        else:
            feature_columns = []

        feature_schema_hash = compute_feature_schema_hash(feature_columns)
        hdf5_meta = self._preprocessing_source_metadata(source_frame, symbol, timeframe)
        data_fingerprint, is_weak = compute_data_fingerprint(source_frame, hdf5_meta)
        source_attrs = getattr(source_frame, "attrs", {}) if source_frame is not None else {}
        source_data_version = str(source_attrs.get("source_data_version", ""))

        return PreprocessingContext(
            symbol=symbol,
            timeframe=timeframe,
            config_hash=config_hash,
            data_fingerprint=data_fingerprint,
            feature_schema_hash=feature_schema_hash,
            time_range=self._preprocessing_time_range(source_frame),
            row_count=0 if source_frame is None else int(len(source_frame.index)),
            source_data_version=source_data_version,
            data_fingerprint_status=WEAK_FINGERPRINT if is_weak else "strong",
        )

    @staticmethod
    def _preprocessing_source_metadata(
        frame: Optional[pd.DataFrame],
        symbol: str,
        timeframe: str,
    ) -> Dict[str, Any]:
        if frame is None or frame.empty:
            return {}
        schema_hash = compute_feature_schema_hash([str(column) for column in frame.columns])
        time_range = FeatureFactory._preprocessing_time_range(frame)
        attrs = getattr(frame, "attrs", {})
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_ts": None if time_range is None else time_range[0],
            "end_ts": None if time_range is None else time_range[1],
            "row_count": int(len(frame.index)),
            "source_data_version": str(attrs.get("source_data_version", "")),
            "schema_hash": schema_hash,
            "last_updated": attrs.get("last_updated"),
        }

    @staticmethod
    def _preprocessing_time_range(frame: Optional[pd.DataFrame]) -> Optional[Tuple[int, int]]:
        if frame is None or frame.empty:
            return None
        index = frame.index
        first = index[0]
        last = index[-1]
        try:
            return int(first), int(last)
        except (TypeError, ValueError):
            timestamps = pd.to_datetime(pd.Index([first, last]), errors="coerce")
            if timestamps.isna().any():
                return None
            return int(timestamps[0].value), int(timestamps[1].value)

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

        # Aggregate inf tracking — surfaces pathological-input quality signal.
        # Although L6.5 winsorization clips inf to finite, residual inf can
        # still appear in groups that bypass L6.5 (e.g. labels) or in early
        # validation runs without L6.5. We surface inf_ratio so the user can
        # quantify how much of the registry was tainted by overflow / div-zero.
        total_inf = 0
        groups_with_inf: List[Tuple[str, int, float]] = []  # (gid, count, ratio)

        for group_id, group in registry.iter_all():
            group_value_count = 0
            group_nan_count = 0
            group_inf_count = 0
            seen_cols = 0

            for shard_meta, shard_data, shard_columns in registry.iter_shards(group_id):
                group_data = np.asarray(shard_data, dtype=np.float32)
                if group_data.ndim != 2:
                    warnings.append(f"Group {group_id} has invalid ndim={group_data.ndim}; expected 2D")
                    logger.warning("[L7][CGSA] Invalid group shape for %s: ndim=%d", group_id, group_data.ndim)
                    continue

                if group_data.shape[0] != group.n_rows:
                    warnings.append(
                        f"Group {group_id} rows mismatch: expected {group.n_rows}, got {group_data.shape[0]}"
                    )
                    logger.warning(
                        "[L7][CGSA] Row mismatch for %s: expected=%d got=%d",
                        group_id,
                        group.n_rows,
                        group_data.shape[0],
                    )

                if group_data.shape[1] != len(shard_columns):
                    warnings.append(
                        f"Group {group_id} shard {shard_meta.shard_idx} columns mismatch: "
                        f"expected {len(shard_columns)}, got {group_data.shape[1]}"
                    )
                    logger.warning(
                        "[L7][CGSA] Shard column mismatch for %s shard=%d expected=%d got=%d",
                        group_id,
                        shard_meta.shard_idx,
                        len(shard_columns),
                        group_data.shape[1],
                    )

                value_count = int(group_data.size)
                if value_count == 0:
                    continue

                group_inf_count += int(np.isinf(group_data).sum())
                group_nan_count += int(np.isnan(group_data).sum())
                group_value_count += value_count
                seen_cols += int(group_data.shape[1])
                del shard_data, group_data

            if seen_cols != group.n_cols:
                warnings.append(
                    f"Group {group_id} columns mismatch: expected {group.n_cols}, got {seen_cols}"
                )
                logger.warning(
                    "[L7][CGSA] Column mismatch for %s: expected=%d got=%d",
                    group_id,
                    group.n_cols,
                    seen_cols,
                )

            if group_value_count == 0:
                continue

            nan_ratio = group_nan_count / group_value_count
            if group_inf_count > 0:
                has_inf = True
                total_inf += group_inf_count
                groups_with_inf.append((group_id, group_inf_count, group_inf_count / group_value_count))
                message = f"Group {group_id} contains {group_inf_count} inf values"
                warnings.append(message)
                logger.warning("[L7][CGSA] %s", message)

            if group_nan_count > 0:
                has_nan = True

            if nan_ratio > 0.90:
                message = f"Group {group_id} NaN ratio={nan_ratio:.4f} exceeds 0.90"
                warnings.append(message)
                logger.warning("[L7][CGSA] %s", message)

            total_values += group_value_count
            non_nan_values += group_value_count - group_nan_count

        coverage = float(non_nan_values / total_values) if total_values > 0 else 0.0
        inf_ratio = float(total_inf / total_values) if total_values > 0 else 0.0

        # Emit a one-shot quality summary so the inf metric is always visible
        # (instead of buried under per-group warnings). Top-5 offending groups
        # help users locate the upstream pathological feature family.
        if total_inf > 0:
            top_inf = sorted(groups_with_inf, key=lambda item: item[1], reverse=True)[:5]
            top_inf_str = ", ".join(
                f"{gid}({count} inf, {ratio:.2%})" for gid, count, ratio in top_inf
            )
            logger.warning(
                "[L7][CGSA] Quality summary: inf_count=%d, inf_ratio=%.6f, "
                "groups_with_inf=%d, coverage=%.4f, top_inf={%s}",
                total_inf,
                inf_ratio,
                len(groups_with_inf),
                coverage,
                top_inf_str,
            )
        else:
            logger.info(
                "[L7][CGSA] Quality summary: inf_count=0, coverage=%.4f, "
                "non_nan=%d/%d",
                coverage,
                non_nan_values,
                total_values,
            )

        return {
            "has_nan": has_nan,
            "has_inf": has_inf,
            "coverage": coverage,
            "inf_count": total_inf,
            "inf_ratio": inf_ratio,
            "groups_with_inf": len(groups_with_inf),
            "warnings": warnings,
        }

    def _persist_single_tf_l3_l6_to_cgsa(
        self,
        layer3: pd.DataFrame,
        layer4: pd.DataFrame,
        layer5: pd.DataFrame,
        layer6: pd.DataFrame,
    ) -> None:
        """Persist single-TF L3-L6 outputs before CGSA L6.5/L7_raw streaming."""
        if self._cgsa_registry is None:
            return
        if layer3 is not None and not layer3.empty:
            self._persist_layer_output_groups(layer3, LayerSource.L3, "L3_rolling")
        if layer4 is not None and not layer4.empty:
            self._persist_layer_output_groups(layer4, LayerSource.L4, "L4_lag")
        if layer5 is not None and not layer5.empty:
            self._persist_layer_output_groups(layer5, LayerSource.L5, "L5_cross")
        if layer6 is not None and not layer6.empty:
            self._persist_layer_output_groups(layer6, LayerSource.L6, "L6_meta")

    def _derive_row_index_for_artifact(self, raw_data: pd.DataFrame) -> Optional[pd.DatetimeIndex]:
        """萃取 primary 時間軸供 timestamps sidecar（V2 持久化）使用。

        **單位實測**：CGSA 路徑的 `raw_data.index` 為 **int64 epoch 秒**（如 1767225600；
        由 `_manifest_time_range_from_raw_data` 產出 '1767225600' 字串證實），亦可能是
        毫秒（Binance ~1.7e12）或已是 DatetimeIndex。**不可**沿用 `_to_datetime_index`
        （硬編 unit="ms"，會把秒當毫秒 → 1970-01-21 錯軸）。此處自行偵測單位（秒/毫秒）。

        timestamps sidecar 是**附加功能**：取不到對齊乾淨的軸 → 回 None（跳 sidecar，
        **不中斷生成**）。fail-closed 僅在於「不寫錯軸」，非「不生成」。
        """
        try:
            if "timestamp" in raw_data.columns:
                raw_ts = raw_data["timestamp"]
            else:
                raw_ts = pd.Series(raw_data.index)

            if pd.api.types.is_datetime64_any_dtype(raw_ts):
                ts = pd.DatetimeIndex(pd.to_datetime(raw_ts))
            else:
                vals = pd.to_numeric(raw_ts, errors="coerce")
                sample = vals.dropna()
                if sample.empty:
                    return None
                # 自動偵測 epoch 單位：秒 ~1.7e9、毫秒 ~1.7e12（與 _load_hdf5_features 同慣例）
                unit = "ms" if abs(float(sample.iloc[0])) >= 1e12 else "s"
                ts = pd.DatetimeIndex(pd.to_datetime(vals, unit=unit, errors="coerce"))

            if len(ts) != int(len(raw_data.index)) or ts.isna().any():
                logger.warning(
                    "[L7] timestamp 軸長度不符/含 NaT（len=%d vs rows=%d），跳過 sidecar（生成續行）",
                    len(ts), int(len(raw_data.index)),
                )
                return None
            return ts
        except Exception as exc:
            logger.warning("[L7] 萃取 timestamp 軸失敗，跳過 timestamps sidecar（生成續行）: %s", exc)
            return None

    def _layer7_raw_from_cgsa_pipeline(
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
        """CGSA generation path: L1-L6 → L6.5 mode → canonical L7_raw."""
        if self._cgsa_registry is None:
            raise ValueError("CGSA L7_raw requested without initialized registry")

        self._cgsa_registry.finalize()
        labels_df = pd.DataFrame(index=raw_data.index)
        if "close" in raw_data.columns:
            label_generator = LabelGenerator(config.labels.model_dump())
            labels_df = label_generator.generate_all(raw_data["close"])

        config_payload = config.model_dump(by_alias=True)
        training_tfs = config_payload.get("timeframes", {}).get("training", [])
        if not isinstance(training_tfs, list):
            training_tfs = [timeframe]

        l65_mode = self._resolve_l65_generation_mode(config)
        layer_counts_before = self._collect_cgsa_layer_counts(self._cgsa_registry)
        stream_summary: Dict[str, Any] = {
            "raw_path": "",
            "manifest_path": str(self._cgsa_registry.manifest_path),
            "feature_count": int(self._cgsa_registry.total_columns()),
            "row_count": int(len(raw_data.index)),
            "group_count": len(list(self._cgsa_registry.iter_all())),
            "validation": self._scan_cgsa_registry_validation(self._cgsa_registry),
            "l65_mode": l65_mode,
        }

        if persist:
            preprocessor = None
            preprocessing_config: Optional[Dict[str, Any]] = None
            if getattr(config.preprocessing, "enabled", False):
                preprocessing_config = self._build_l7_raw_preprocessing_config(config)
                context = self._build_preprocessing_context(raw_data, config)
                preprocessor = FeaturePreprocessor(preprocessing_config, context=context)

            from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config

            tier = get_memory_tier()
            tier_cfg = get_tier_config(tier)
            n_workers = self._parse_positive_int_env(
                "FFACT_L65_WORKERS",
                int(tier_cfg["l65_workers"]),
            )
            # L7 dead-drop（CGSA mode）：frame-path 不經此路徑，故在 registry stream
            # write 時 per-column 剔除常數/樣本不足/全 NaN 欄。enabled=False → None（no-op）。
            _nan_strat = getattr(config, "nan_strategy", None)
            _dead_cfg = getattr(_nan_strat, "l7_dead_feature_drop", None) if _nan_strat else None
            _dead_min_valid = (
                int(_dead_cfg.min_valid_samples)
                if _dead_cfg is not None and bool(getattr(_dead_cfg, "enabled", False))
                else None
            )
            # Layer B 通用淨化：inf / |v|>finite_cap → NaN，覆蓋所有 streamed 特徵（含 L3）。
            _san_cfg = getattr(_nan_strat, "numeric_sanitize", None) if _nan_strat else None
            _sanitize_cap = (
                float(_san_cfg.finite_cap)
                if _san_cfg is not None and bool(getattr(_san_cfg, "enabled", False))
                else None
            )
            raw_path, stream_summary = self._storage.write_raw_from_registry_stream(
                symbol=symbol,
                tf=timeframe,
                config_hash=config_hash,
                registry=self._cgsa_registry,
                preprocessor=preprocessor,
                n_workers=n_workers,
                cleanup_intermediate=True,
                l65_mode=l65_mode,
                dead_drop_min_valid=_dead_min_valid,
                sanitize_finite_cap=_sanitize_cap,
                row_index=self._derive_row_index_for_artifact(raw_data),
                time_range=self._manifest_time_range_from_raw_data(raw_data),
                extra_metadata={
                    **self._build_l7_raw_preprocessing_metadata(
                        config,
                        preprocessing_config,
                        l65_mode,
                    ),
                    "source_registry_manifest": str(self._cgsa_registry.manifest_path),
                },
            )
            stream_summary["raw_path"] = str(raw_path)

        self._cgsa_registry.save_state(
            symbol=symbol,
            primary_tf=timeframe,
            training_tfs=training_tfs,
            config_hash=config_hash,
            config_snapshot=config_payload,
        )

        validation_summary = stream_summary.get("validation", {})
        merged_warnings = (compute_warnings or []) + list(validation_summary.get("warnings", []))
        feature_count = int(stream_summary.get("feature_count", self._cgsa_registry.total_columns()))
        layer_counts = dict(layer_counts_before)
        layer_counts["layer6_5"] = max(0, feature_count - sum(
            int(layer_counts.get(key, 0))
            for key in ("layer1", "layer2", "layer3", "layer4", "layer5", "layer6")
        ))

        manifest_path = str(stream_summary.get("manifest_path") or self._cgsa_registry.manifest_path)
        raw_path_value = str(stream_summary.get("raw_path") or "")
        metadata = {
            "feature_names": [],
            "feature_count": feature_count,
            "layer_counts": layer_counts,
            "config_hash": config_hash,
            "generation_time": float(elapsed),
            "compute_warnings": merged_warnings,
            "symbol": symbol,
            "timeframe": timeframe,
            "data_range": self._data_range(raw_data),
            "config_used": config_payload,
            "artifact_kind": "raw",
            "schema_version": FeatureStorage.L7_RAW_SCHEMA_VERSION,
            "l65_mode": l65_mode,
            "manifest_path": manifest_path,
            "raw_path": raw_path_value,
            "npy_freed_bytes": int(stream_summary.get("npy_freed_bytes", 0)),
            "storage_dtype": stream_summary.get("storage_dtype"),
            "dtype_summary": stream_summary.get("dtype_summary"),
            "validation": {
                "has_nan": bool(validation_summary.get("has_nan", False)),
                "has_inf": bool(validation_summary.get("has_inf", False)),
                "max_correlation": 0.0,
                "high_correlation_pairs": [],
                "warnings": list(validation_summary.get("warnings", [])),
                "coverage": float(validation_summary.get("coverage", 0.0)),
                "inf_count": int(validation_summary.get("inf_count", 0)),
                "inf_ratio": float(validation_summary.get("inf_ratio", 0.0)),
                "groups_with_inf": int(validation_summary.get("groups_with_inf", 0)),
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

    @classmethod
    def _manifest_time_range_from_raw_data(cls, raw_data: pd.DataFrame) -> Dict[str, Optional[str]]:
        if raw_data is None or raw_data.empty:
            return {"start": None, "end": None}
        index = raw_data.index
        return {
            "start": cls._format_manifest_value(index[0]),
            "end": cls._format_manifest_value(index[-1]),
        }

    @staticmethod
    def _preprocessing_step_enabled(preprocessing: Any, step_name: str) -> bool:
        if isinstance(preprocessing, dict):
            step_config = preprocessing.get(step_name)
        else:
            step_config = getattr(preprocessing, step_name, None)
        if isinstance(step_config, dict):
            return bool(step_config.get("enabled", False))
        return bool(getattr(step_config, "enabled", False))

    @staticmethod
    def _format_manifest_value(value: Any) -> str:
        if hasattr(value, "isoformat"):
            return str(value.isoformat())
        if isinstance(value, np.generic):
            return str(value.item())
        return str(value)

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
                "inf_count": int(validation_summary.get("inf_count", 0)),
                "inf_ratio": float(validation_summary.get("inf_ratio", 0.0)),
                "groups_with_inf": int(validation_summary.get("groups_with_inf", 0)),
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
        config_payload["_mtf_align_version"] = CURRENT_MTF_ALIGN_VERSION
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


class _StreamingL3Persister:
    """Plan A: stream L3 chunks to ColumnGroupRegistry as they are produced.

    The RollingAggregator produces L3 features in (window, agg) × column-chunk
    order. Without streaming, every step's output across all column chunks must
    live in memory until the final pd.concat — at 1h timeframe this peaks at
    ~10 GB and triggers OOM in 8 GB workers.

    This persister is registered as a ``persist_callback`` on the aggregator.
    It buffers per-step columns up to ``buffer_cols`` (tier-aware) and flushes
    each buffer as a ColumnGroup .npy file via ``save_data``. After flush, the
    in-memory buffer is freed via ``del`` + ``gc.collect()``.

    Contract: caller (FeatureFactory) owns ``flush_all()`` invocation after
    the aggregator returns.
    """

    __slots__ = (
        "factory", "layer", "label_prefix", "buffer_cols",
        "_buffers", "_buffer_col_count", "_flushed_chunks",
        "total_cols", "total_groups",
    )

    def __init__(
        self,
        factory: "FeatureFactory",
        layer: LayerSource,
        label_prefix: str,
        buffer_cols: int = 5000,
    ) -> None:
        self.factory = factory
        self.layer = layer
        self.label_prefix = label_prefix
        self.buffer_cols = max(100, int(buffer_cols))
        self._buffers: Dict[str, List[pd.DataFrame]] = {}
        self._buffer_col_count: Dict[str, int] = {}
        self._flushed_chunks: Dict[str, int] = {}
        self.total_cols = 0
        self.total_groups = 0

    def __call__(self, step_label: str, chunk_frame: pd.DataFrame) -> None:
        if chunk_frame is None or chunk_frame.empty:
            return
        bufs = self._buffers.setdefault(step_label, [])
        bufs.append(chunk_frame)
        new_count = self._buffer_col_count.get(step_label, 0) + chunk_frame.shape[1]
        self._buffer_col_count[step_label] = new_count
        if new_count >= self.buffer_cols:
            self._flush(step_label)

    def _flush(self, step_label: str) -> None:
        bufs = self._buffers.pop(step_label, None)
        if not bufs:
            self._buffer_col_count.pop(step_label, None)
            return
        self._buffer_col_count.pop(step_label, None)

        chunk_idx = self._flushed_chunks.get(step_label, 0) + 1
        self._flushed_chunks[step_label] = chunk_idx

        if len(bufs) == 1:
            merged = bufs[0]
        else:
            merged = pd.concat(bufs, axis=1, copy=False)
        # Drop intermediate list reference before allocating numpy buffer.
        del bufs

        n_rows, n_cols = merged.shape
        if n_cols == 0:
            del merged
            return

        registry = self.factory._cgsa_registry
        timeframe = self.factory._current_timeframe or "unknown"
        base_id = f"{timeframe}_{self.label_prefix}_{step_label}_{chunk_idx}"
        group_id = self.factory._next_available_group_id(base_id)
        columns_tuple = tuple(merged.columns)
        data = merged.to_numpy(dtype=np.float32, copy=False)
        # ColumnGroup.save_data atomically writes .npy then registers metadata.
        group = ColumnGroup(
            group_id=group_id,
            layer=self.layer,
            timeframe=timeframe,
            data_source="derived",
            indicator=self.label_prefix,
            columns=columns_tuple,
            shape=(n_rows, n_cols),
            dtype="float32",
        )
        registry.save_data(group, data)

        self.total_cols += n_cols
        self.total_groups += 1
        del merged, data
        import gc as _gc
        _gc.collect()

    def flush_all(self) -> None:
        for sl in list(self._buffers.keys()):
            self._flush(sl)
        import gc as _gc
        _gc.collect()


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
