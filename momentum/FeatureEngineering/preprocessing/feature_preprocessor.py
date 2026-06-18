from __future__ import annotations

import copy
import gc
import os
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import psutil
from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, List, Mapping, Optional, Tuple, Union

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.preprocessing._d_star_cache import (
    ADF_ENGINE_VERSION,
    DStarCache,
    PreprocessingContext,
    _col_value_fingerprint,
    _strong_col_value_fingerprint,
)
from momentum.FeatureEngineering.preprocessing._fast_adf_numba import (
    FAST_ADF_ENGINE_VERSION,
    adf_pvalue_fast,
)
from momentum.FeatureEngineering.preprocessing._hurst_prior import (
    find_min_d_full_bisection,
    find_min_d_with_prior,
)
from momentum.FeatureEngineering.preprocessing._non_stationary_cache import NonStationaryCache
from momentum.FeatureEngineering.preprocessing._slow_path_parallel import (
    ParallelSlowPath,
    process_fracdiff_column_values,
)
from momentum.FeatureEngineering.preprocessing._numba_transforms import (
    _rolling_mean_std,
    _rolling_rank_numba,
    rolling_quantile_2d,
)
from momentum.FeatureEngineering.utils.adf_safe_skip import filter_safe_skip
from momentum.FeatureEngineering.utils.hardware_utils import get_current_tier_gb
from momentum.FeatureEngineering.utils.winsor_params import resolve_winsor_min_periods
from momentum.FeatureEngineering.operators.derived_operators import (
    RATIO_UNSAFE_CATEGORIES,
)
from momentum.core.config import (
    MomentumConfig,
    get_fast_adf_enabled,
    get_fracdiff_layers,
    get_fracdiff_precision,
    get_l65_optimization_profile,
    get_batch_symbol_concurrency,
    get_slowpath_n_jobs,
)
from momentum.core.logging import get_logger


if TYPE_CHECKING:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


logger = get_logger(__name__)
_PROC = psutil.Process()  # Cached for low-overhead RSS sampling
_FRACDIFF_LAYER_RE = re.compile(r"^(L\d+)_")
_WARNED_CAUSAL_OVERRIDE = False


def _is_ratio_unsafe_column(col: str) -> bool:
    """Belt-and-suspenders pattern guard for L6.5 entry.

    L1 atomic naming convention: `<source>_<category>_<rest>` (e.g.
    `ohlc_pattern_CDLDOJI`). Ratio-unsafe categories propagate to derived names
    (`ohlc_pattern_CDLDOJI_Momentum_L5`) so the same positional check works for
    L1 / L2 / L3 outputs alike. See docs/NAN_POISONING_INVESTIGATION.md § 7B / Q11.2.
    """
    parts = str(col).split("_", 2)
    return len(parts) >= 2 and parts[1] in RATIO_UNSAFE_CATEGORIES


def _is_fracdiff_target_layer(column: str, allowed_layers: FrozenSet[str]) -> bool:
    if "ALL" in allowed_layers:
        return True

    match = _FRACDIFF_LAYER_RE.match(str(column))
    if not match:
        return False
    return match.group(1) in allowed_layers

try:
    from scipy.special import ndtri
    from scipy.signal import fftconvolve as _scipy_fftconvolve_pp

    HAS_SCIPY = True
    _HAS_FFTCONV_PP = True
except Exception:
    HAS_SCIPY = False
    _HAS_FFTCONV_PP = False
    ndtri = None
    logger.warning("scipy not available, gaussian normalization disabled")

# FFT crossover: use FFT when n_signal * n_weights exceeds this threshold.
# For fracdiff at 20k rows with w≈252: n×w≈5.1M >> 4096, always uses FFT.
_FRACDIFF_FFT_OPS_THRESHOLD = 4096


def _frac_diff_convolve(signal: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """1-D convolution (mode='valid') with automatic FFT dispatch for fracdiff.

    Uses ``scipy.signal.fftconvolve`` when available and operation count
    exceeds the crossover threshold; falls back to ``np.convolve`` otherwise.
    """
    if _HAS_FFTCONV_PP and signal.size * weights.size > _FRACDIFF_FFT_OPS_THRESHOLD:
        return np.asarray(_scipy_fftconvolve_pp(signal, weights, mode="valid"), dtype=np.float64)
    return np.convolve(signal, weights, mode="valid")

try:
    from statsmodels.tsa.stattools import adfuller

    HAS_STATSMODELS = True
except Exception:
    HAS_STATSMODELS = False
    adfuller = None
    logger.warning("statsmodels not available, ADF/Fractional Differencing disabled")

class FeaturePreprocessor:
    """Layer 6.5: 特徵前處理與正規化。"""

    def __init__(
        self,
        config: Dict,
        context: Optional[PreprocessingContext] = None,
        column_layer_map: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._config = config or {}
        self._preprocessing_context = context or PreprocessingContext()
        self._column_layer_map = dict(column_layer_map) if column_layer_map is not None else None
        self.rank_config = self._config.get("rank_transform", {})
        self.gaussian_config = self._config.get("gaussian_normalize", {})
        self.adf_config = self._config.get("adf_differencing", {})
        self.zscore_config = self._config.get("adaptive_zscore", {})
        self.winsor_config = self._config.get("winsorization", {})
        self.fracdiff_config = self._config.get("fractional_differencing", {})
        self.adf_safe_skip_config = self._config.get("adf_safe_skip", {}) or {}
        # 預設 replace：確保跨標的欄位名稱一致
        self.mode = self._config.get("mode", "replace")
        # ⚠️必須 True,False=look-ahead 洩漏,禁關,變更需委員會
        raw_causal = bool(self._config.get("causal_preprocessing", True))
        if not raw_causal:
            global _WARNED_CAUSAL_OVERRIDE
            if not _WARNED_CAUSAL_OVERRIDE:
                logger.warning(
                    "⚠️ causal_preprocessing=False 被忽略,強制 True(防 look-ahead 洩漏,變更需委員會)"
                )
                _WARNED_CAUSAL_OVERRIDE = True
        self.causal_preprocessing = True

        self._fracdiff_processed_columns: set[str] = set()
        self._fracdiff_apply_to_layers = get_fracdiff_layers()
        self._non_stationary_cache = NonStationaryCache()
        self._column_chunk_size = self._resolve_column_chunk_size()
        self._d_star_cache: Optional[DStarCache] = None
        self._d_star_cache_shared = False
        self._numba_warmed_up = False

    def _rolling_window(self) -> int:
        window = int(self.winsor_config.get("window", self.rank_config.get("window", 252)))
        return max(window, 1)

    @staticmethod
    def _rolling_min_periods(window: int) -> int:
        return resolve_winsor_min_periods(int(window))

    def _calibration_bars(self) -> int:
        adf_sample = int(self.adf_config.get("sample_size", self.fracdiff_config.get("sample_size", 500)))
        configured = int(self._config.get("calibration_bars", 500))
        return max(adf_sample, configured, 500)

    def _calibration_series(self, series: pd.Series) -> pd.Series:
        bars = min(len(series), self._calibration_bars())
        return series.iloc[:bars]

    def _calibration_values(self, values: np.ndarray) -> np.ndarray:
        arr = np.asarray(values)
        bars = min(len(arr), self._calibration_bars())
        return arr[:bars]

    @staticmethod
    def _resolve_column_chunk_size() -> int:
        """Resolve L6.5 column chunk size from env var (0 = disabled)."""
        raw = os.getenv("FFACT_L65_CHUNK_SIZE", "2000").strip()
        try:
            size = int(raw)
        except ValueError:
            size = 2000
        return max(size, 0)

    def transform(self, features_df: pd.DataFrame) -> pd.DataFrame:
        if features_df is None or features_df.empty:
            return pd.DataFrame(index=features_df.index if features_df is not None else None)

        # Belt-and-suspenders: drop ratio-unsafe (pattern) columns at L6.5 entry.
        # In normal pipelines L3 already filters these out, but L6.5 may receive
        # registry-loaded historical data, post-IC selections, or other paths
        # that bypass L3. See docs/NAN_POISONING_INVESTIGATION.md § 7B / Q11.2.
        unsafe = [c for c in features_df.columns if _is_ratio_unsafe_column(str(c))]
        if unsafe:
            logger.info(
                "[L6.5] dropping %d ratio-unsafe columns (categories=%s) at preprocessor entry",
                len(unsafe), sorted(RATIO_UNSAFE_CATEGORIES),
            )
            features_df = features_df.drop(columns=unsafe)
            if features_df.empty:
                return pd.DataFrame(index=features_df.index)

        from momentum.FeatureEngineering.polars_adapter import polars_enabled

        use_polars = polars_enabled()

        num_cols = len(features_df.columns)
        chunk_size = self._column_chunk_size

        if use_polars and not self.fracdiff_config.get("enabled", False):
            # Polars path: fracdiff not supported in Polars (requires scipy/statsmodels)
            return self._transform_single_polars(features_df)

        if chunk_size > 0 and num_cols > chunk_size:
            return self._transform_chunked(features_df, chunk_size)

        return self._transform_single(features_df)

    def transform_selected(
        self,
        selected: List[str],
        groups: Dict[str, pd.DataFrame],
        config: Optional[Any] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Post-IC transform for selected features only."""
        selected_columns = [str(feature) for feature in selected]
        if not selected_columns:
            logger.warning("[IC-First] post_ic received empty IC selection")
            return {}

        if groups is None:
            raise ValueError("groups must be a dictionary")

        post_ic_config = self._build_post_ic_transform_config(
            selected_columns=selected_columns,
            config=config,
        )
        post_ic_preprocessor = FeaturePreprocessor(
            post_ic_config,
            context=self._preprocessing_context,
            column_layer_map=self._column_layer_map,
        )

        processed_groups: Dict[str, pd.DataFrame] = {}
        missing_columns = set(selected_columns)
        for group_id, group_df in groups.items():
            if not isinstance(group_df, pd.DataFrame):
                raise TypeError(f"Group {group_id} must be a pandas DataFrame")

            available_columns = [column for column in selected_columns if column in group_df.columns]
            if not available_columns:
                continue

            missing_columns.difference_update(available_columns)
            selected_frame = group_df.loc[:, available_columns].copy()
            transformed = post_ic_preprocessor.transform(selected_frame)
            if not transformed.empty:
                processed_groups[str(group_id)] = transformed

        if missing_columns:
            logger.warning(
                "[IC-First] post_ic skipped %d selected features missing from L7_raw",
                len(missing_columns),
            )
        if not processed_groups:
            logger.warning("[IC-First] post_ic produced no processed groups")

        return processed_groups

    def _build_post_ic_transform_config(
        self,
        selected_columns: List[str],
        config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        preprocessing_config = self._coerce_preprocessing_config(config, self._config)
        preprocessing_config["mode"] = "replace"
        preprocessing_config["enabled"] = True
        self._set_config_step_enabled(preprocessing_config, "winsorization", False)
        self._set_config_step_enabled(preprocessing_config, "fractional_differencing", False)
        self._set_config_step_enabled(preprocessing_config, "adf_differencing", False)
        # 尊重使用者在 config 中的開關設定
        _rank_on = preprocessing_config.get("rank_transform", {}).get("enabled", True)
        _zscore_on = preprocessing_config.get("adaptive_zscore", {}).get("enabled", True)
        _gaussian_on = preprocessing_config.get("gaussian_normalize", {}).get("enabled", False)
        self._set_config_step_enabled(preprocessing_config, "rank_transform", _rank_on, selected_columns if _rank_on else None)
        self._set_config_step_enabled(preprocessing_config, "adaptive_zscore", _zscore_on, selected_columns if _zscore_on else None)
        self._set_config_step_enabled(preprocessing_config, "gaussian_normalize", _gaussian_on, selected_columns if _gaussian_on else None)
        return preprocessing_config

    @staticmethod
    def _coerce_preprocessing_config(
        config: Optional[Any],
        default_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        if config is None:
            return copy.deepcopy(default_config)

        raw_config = getattr(config, "preprocessing", config)
        if isinstance(raw_config, dict):
            if "preprocessing" in raw_config and "rank_transform" not in raw_config:
                raw_config = raw_config["preprocessing"]
            return copy.deepcopy(raw_config)

        model_dump = getattr(raw_config, "model_dump", None)
        if callable(model_dump):
            return copy.deepcopy(model_dump())

        raise TypeError("config must be a preprocessing config, FactoryConfig, dict, or None")

    @staticmethod
    def _set_config_step_enabled(
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

    def transform_registry_groups(
        self,
        registry: "ColumnGroupRegistry",
        n_workers: int = 1,
    ) -> int:
        """Apply L6.5 transforms per group from registry and overwrite each group in place."""
        if registry is None:
            return 0

        groups = [group for _, group in registry.iter_all() if group.n_cols > 0]
        if not groups:
            return 0

        worker_count = max(1, int(n_workers))
        transform_context = self._build_registry_transform_context()
        logger.info(
            "[L6.5] Registry transform config: groups=%d workers=%d mode=%s "
            "use_fast=%s can_use_numba_fast=%s winsor=%s rank=%s zscore=%s "
            "fracdiff=%s fracdiff_apply_to=%s fracdiff_layers=%s adf=%s gaussian=%s",
            len(groups),
            worker_count,
            self.mode,
            bool(transform_context.get("use_fast", False)),
            bool(transform_context.get("can_use_numba_fast", False)),
            bool(transform_context.get("do_winsorize", False)),
            bool(transform_context.get("do_rank", False)),
            bool(transform_context.get("do_zscore", False)),
            bool(transform_context.get("do_fracdiff", False)),
            self.fracdiff_config.get("apply_to", "non_stationary"),
            sorted(self._fracdiff_apply_to_layers),
            bool(transform_context.get("do_adf", False)),
            bool(transform_context.get("do_gaussian", False)),
        )

        io_stats_before = self._registry_io_stats(registry)

        def _execute() -> int:
            if worker_count <= 1:
                return self._transform_registry_serial(registry, groups, transform_context)

            return self._transform_registry_parallel(
                registry,
                groups,
                transform_context,
                worker_count,
            )

        defer_manifest = getattr(registry, "defer_manifest_writes", None)
        if callable(defer_manifest):
            with defer_manifest("l65_transform"):
                completed = _execute()
        else:
            completed = _execute()

        self._log_registry_io_summary(registry, io_stats_before)
        return completed

    def transform_registry_groups_to_sink(
        self,
        registry: "ColumnGroupRegistry",
        sink: Callable[[str, List[str], np.ndarray, str, Optional[Path], bool], None],
        n_workers: int = 1,
    ) -> int:
        """Apply L6.5 per group and stream transformed arrays to ``sink``.

        This path is used by the L7_raw writer. It intentionally avoids
        ``registry.overwrite_data()`` so large groups do not require source
        ``.npy`` plus full-size ``.npy.tmp`` headroom before parquet persist.
        """
        if registry is None:
            return 0

        raw_sink = sink

        def persistence_sink(
            group_id: str,
            columns: List[str],
            data: np.ndarray,
            source_group_id: str,
            source_disk_path: Optional[Path],
            cleanup_source: bool,
        ) -> None:
            # 只 cast dtype,不改記憶體序(ascontiguousarray 會變 npy header/bytes)。
            data_fp32 = np.asarray(data, dtype=np.float32)
            raw_sink(
                group_id,
                columns,
                data_fp32,
                source_group_id,
                source_disk_path,
                cleanup_source,
            )

        sink = persistence_sink

        groups = [group for _, group in registry.iter_all() if group.n_cols > 0]
        if not groups:
            return 0

        worker_count = max(1, int(n_workers))
        if worker_count > 1:
            logger.info(
                "[L6.5] raw-sink path uses serial group streaming for disk safety "
                "(requested_workers=%d)",
                worker_count,
            )

        transform_context = self._build_registry_transform_context()
        logger.info(
            "[L6.5] Registry raw-sink config: groups=%d requested_workers=%d "
            "effective_workers=1 mode=%s use_fast=%s can_use_numba_fast=%s "
            "winsor=%s rank=%s zscore=%s fracdiff=%s fracdiff_apply_to=%s "
            "fracdiff_layers=%s adf=%s gaussian=%s",
            len(groups),
            worker_count,
            self.mode,
            bool(transform_context.get("use_fast", False)),
            bool(transform_context.get("can_use_numba_fast", False)),
            bool(transform_context.get("do_winsorize", False)),
            bool(transform_context.get("do_rank", False)),
            bool(transform_context.get("do_zscore", False)),
            bool(transform_context.get("do_fracdiff", False)),
            self.fracdiff_config.get("apply_to", "non_stationary"),
            sorted(self._fracdiff_apply_to_layers),
            bool(transform_context.get("do_adf", False)),
            bool(transform_context.get("do_gaussian", False)),
        )

        from momentum.FeatureEngineering.utils.hardware_utils import get_l65_split_threshold

        split_threshold = get_l65_split_threshold()
        group_plan: List[Tuple[object, str, bool, int]] = []
        fast_full_count = 0
        slow_full_count = 0
        slow_chunked_count = 0
        max_group_cols = 0
        total_tasks = 0
        for group in groups:
            group_id = str(getattr(group, "group_id"))
            n_cols = self._group_n_columns(group)
            shards = getattr(group, "shards", ()) or ()
            requires_slow = self._group_requires_slow_transform(group, transform_context)
            is_chunked = requires_slow and split_threshold > 0 and n_cols > split_threshold
            if is_chunked:
                estimated_tasks = max(1, (n_cols + split_threshold - 1) // split_threshold)
            elif shards and self.mode == "replace" and not requires_slow and bool(transform_context.get("can_use_numba_fast", False)):
                estimated_tasks = max(1, len(shards))
            else:
                estimated_tasks = 1
            if is_chunked:
                slow_chunked_count += 1
            elif requires_slow:
                slow_full_count += 1
            else:
                fast_full_count += 1
            max_group_cols = max(max_group_cols, n_cols)
            total_tasks += estimated_tasks
            group_plan.append((group, group_id, is_chunked, estimated_tasks))

        schedule_mode = "registry_order"
        if self._raw_sink_largest_first_enabled():
            group_plan.sort(key=lambda item: (-self._group_disk_size_bytes(item[0]), item[1]))
            schedule_mode = "largest_first"

        completed = 0
        started_at = time.perf_counter()
        heartbeat_step = max(1, total_tasks // 20)
        heartbeat_interval_sec = 30.0
        last_heartbeat_at = started_at
        last_heartbeat_done = 0
        tasks_done = 0

        logger.info(
            "[L6.5] Raw-sink start: %d full groups (fast=%d, slow=%d) + "
            "%d big-group splits → %d sub-tasks "
            "(requested_workers=%d, effective_workers=1, split_threshold=%d, "
            "slow_chunked=%d, max_group_cols=%d, schedule=%s, rss=%dMB)",
            len(groups) - slow_chunked_count,
            fast_full_count,
            slow_full_count,
            slow_chunked_count,
            total_tasks,
            worker_count,
            split_threshold,
            slow_chunked_count,
            max_group_cols,
            schedule_mode,
            _PROC.memory_info().rss >> 20,
        )

        for index, (group, group_id, is_chunked, estimated_tasks) in enumerate(
            group_plan,
            1,
        ):
            shards = getattr(group, "shards", ()) or ()
            can_shard_stream = (
                bool(shards)
                and not is_chunked
                and self.mode == "replace"
                and not self._group_requires_slow_transform(group, transform_context)
                and bool(transform_context.get("can_use_numba_fast", False))
            )

            # Native-resolution L6.5 path for compact-aligned groups: compute
            # transforms on source rows then forward-fill to primary rows.
            # Avoids step-function bias in fracdiff/distribution stats.
            native_outputs = self._maybe_run_native_l65_to_sink(
                registry,
                group,
                sink,
            )
            if native_outputs is not None:
                outputs_written = native_outputs
                completed += 1
                tasks_done += max(estimated_tasks, outputs_written, 1)
                last_group_label = f"{group_id} (native-tf, parts={outputs_written})"

                now = time.perf_counter()
                if (
                    tasks_done - last_heartbeat_done >= heartbeat_step
                    or (now - last_heartbeat_at) >= heartbeat_interval_sec
                    or index == len(group_plan)
                ):
                    elapsed = now - started_at
                    rate = tasks_done / elapsed if elapsed > 0 else 0.0
                    eta = (total_tasks - tasks_done) / rate if rate > 0 else float("inf")
                    logger.info(
                        "[L6.5] raw-sink heartbeat: tasks %d/%d (%.1f%%), groups %d/%d, "
                        "elapsed=%.1fs, rate=%.2f/s, ETA=%.0fs, rss=%dMB, last=%s",
                        tasks_done,
                        total_tasks,
                        100.0 * tasks_done / max(total_tasks, 1),
                        completed,
                        len(group_plan),
                        elapsed,
                        rate,
                        eta if eta != float("inf") else -1,
                        _PROC.memory_info().rss >> 20,
                        last_group_label,
                    )
                    last_heartbeat_at = now
                    last_heartbeat_done = tasks_done
                gc.collect()
                continue

            if is_chunked:
                source_disk_path = getattr(group, "disk_path", None)
                outputs_written = self._stream_single_group_chunked_to_sink(
                    registry,
                    group,
                    split_threshold,
                    sink,
                    source_disk_path,
                )
            elif can_shard_stream:
                # Phase B Phase 1 Step 11: per-shard streaming.
                # Each shard is a column slice with the FULL row axis, so
                # column-independent fast-path kernels (winsor/rank/zscore)
                # produce identical results per shard as on the concat.
                # We delete the source shard `.npy` immediately after sink
                # acknowledges the parquet part is durable.
                outputs_written = self._stream_sharded_group_to_sink(
                    registry,
                    group,
                    transform_context,
                    sink,
                )
            else:
                outputs = self._transform_single_group_to_arrays(
                    registry,
                    group,
                    transform_context,
                )
                source_disk_path = getattr(group, "disk_path", None)
                for output_index, (output_group_id, columns, data) in enumerate(outputs):
                    sink(
                        output_group_id,
                        columns,
                        data,
                        group_id,
                        source_disk_path,
                        output_index == len(outputs) - 1,
                    )
                outputs_written = len(outputs)
                del outputs
            completed += 1
            tasks_done += max(estimated_tasks, outputs_written, 1)
            if is_chunked:
                last_group_label = f"{group_id} (slow-chunked, parts={outputs_written})"
            else:
                last_group_label = f"{group_id} (full)"

            now = time.perf_counter()
            if (
                tasks_done - last_heartbeat_done >= heartbeat_step
                or (now - last_heartbeat_at) >= heartbeat_interval_sec
                or index == len(group_plan)
            ):
                elapsed = now - started_at
                rate = tasks_done / elapsed if elapsed > 0 else 0.0
                eta = (total_tasks - tasks_done) / rate if rate > 0 else float("inf")
                logger.info(
                    "[L6.5] raw-sink heartbeat: tasks %d/%d (%.1f%%), groups %d/%d, "
                    "elapsed=%.1fs, rate=%.2f/s, ETA=%.0fs, rss=%dMB, last=%s",
                    tasks_done,
                    total_tasks,
                    100.0 * tasks_done / max(total_tasks, 1),
                    completed,
                    len(group_plan),
                    elapsed,
                    rate,
                    eta if eta != float("inf") else -1,
                    _PROC.memory_info().rss >> 20,
                    last_group_label,
                )
                last_heartbeat_at = now
                last_heartbeat_done = tasks_done

            gc.collect()

        logger.info(
            "[L6.5] raw-sink complete: %d/%d groups in %.2fs rss=%dMB",
            completed,
            len(groups),
            time.perf_counter() - started_at,
            _PROC.memory_info().rss >> 20,
        )
        return completed

    def _build_registry_transform_context(self) -> Dict[str, object]:
        """Resolve immutable per-run settings for registry-based L6.5 transforms."""

        do_winsorize = self.winsor_config.get("enabled", True)
        do_rank = self.rank_config.get("enabled", False)
        do_zscore = self.zscore_config.get("enabled", False)
        do_fracdiff = self.fracdiff_config.get("enabled", False)
        do_adf = self.adf_config.get("enabled", False)
        do_gaussian = self.gaussian_config.get("enabled", False)

        can_use_numba_fast = self.mode == "replace"
        # Gaussian with apply_to="all" can be applied as a post-step after numba fast path,
        # so it no longer forces use_fast=False globally.
        gaussian_apply_to = self.gaussian_config.get("apply_to", "all")
        gaussian_needs_slow = do_gaussian and gaussian_apply_to != "all"
        use_fast = can_use_numba_fast and not do_fracdiff and not do_adf and not gaussian_needs_slow

        transform_context: Dict[str, object] = {
            "use_fast": use_fast,
            "can_use_numba_fast": can_use_numba_fast,
            "do_winsorize": do_winsorize,
            "do_rank": do_rank,
            "do_zscore": do_zscore,
            "do_fracdiff": do_fracdiff,
            "do_adf": do_adf,
            "do_gaussian": do_gaussian,
            "gaussian_apply_to": gaussian_apply_to,
            "causal_preprocessing": self.causal_preprocessing,
            "winsor_window": self._rolling_window(),
            "winsor_min_periods": self._rolling_min_periods(self._rolling_window()),
        }

        if can_use_numba_fast:
            self._warmup_numba_if_needed()

            from momentum.FeatureEngineering.preprocessing._numba_transforms import transform_array_fast

            winsor_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
            winsor_method = str(self.winsor_config.get("method", "quantile"))
            winsor_sigma_k = float(self.winsor_config.get("sigma_k", 3.0))
            zscore_windows = self.zscore_config.get("windows", [100, 252])
            gaussian_clip = self.gaussian_config.get("clip_range", [0.001, 0.999])

            transform_context.update(
                {
                    "transform_array_fast": transform_array_fast,
                    "do_winsorize": do_winsorize,
                    "winsor_method": winsor_method,
                    "winsor_sigma_k": winsor_sigma_k,
                    "winsor_lower_q": float(winsor_range[0]),
                    "winsor_upper_q": float(winsor_range[1]),
                    "do_rank": do_rank,
                    "rank_window": int(self.rank_config.get("window", 252)),
                    "do_zscore": do_zscore,
                    "zscore_window": int(zscore_windows[0]) if zscore_windows else 100,
                    "zscore_epsilon": float(self.zscore_config.get("epsilon", 1e-8)),
                    "gaussian_clip_lower": float(gaussian_clip[0]),
                    "gaussian_clip_upper": float(gaussian_clip[1]),
                    "causal_preprocessing": self.causal_preprocessing,
                    "winsor_window": self._rolling_window(),
                    "winsor_min_periods": self._rolling_min_periods(self._rolling_window()),
                }
            )

        return transform_context

    # ------------------------------------------------------------------
    # Native-resolution L6.5 path for compact-aligned groups
    # ------------------------------------------------------------------
    def _maybe_run_native_l65_to_sink(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        sink: Callable[[str, List[str], np.ndarray, str, Optional[Path], bool], None],
    ) -> Optional[int]:
        """Try the native-resolution L6.5 path for one compact-aligned group.

        Returns the number of sink outputs written, or ``None`` if the group
        is not eligible (caller falls back to the legacy expand-then-transform
        sub-paths).
        """
        from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
            apply_idx_map_to_array,
            scale_preprocessing_config_for_native,
            should_use_native_path,
        )
        from dataclasses import replace as _dc_replace

        alignment = getattr(group, "alignment", None)
        if alignment is None:
            return None

        group_id = str(getattr(group, "group_id"))
        columns = list(getattr(group, "columns"))
        if not columns:
            return None

        source_tf = str(getattr(alignment, "source_timeframe", "") or "")
        primary_tf = str(getattr(alignment, "primary_timeframe", "") or "")
        source_n_rows = int(getattr(alignment, "source_n_rows", 0))
        primary_n_rows = int(getattr(alignment, "primary_n_rows", 0))

        scaled_config = scale_preprocessing_config_for_native(
            self._config,
            source_tf,
            primary_tf,
        )

        use_native, reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe=source_tf,
            primary_timeframe=primary_tf,
            source_n_rows=source_n_rows,
            scaled_config=scaled_config,
        )
        if not use_native:
            logger.info(
                "[L6.5] native-tf path skipped: group=%s reason=%s "
                "src_tf=%s primary_tf=%s native_rows=%d",
                group_id,
                reason,
                source_tf,
                primary_tf,
                source_n_rows,
            )
            return None

        # Load native (source-resolution) data and idx_map.
        native_arr = np.asarray(registry.load_data_native(group_id), dtype=np.float32)
        if native_arr.shape[0] != source_n_rows:
            logger.warning(
                "[L6.5] native-tf row mismatch: group=%s expected=%d got=%d, falling back",
                group_id,
                source_n_rows,
                native_arr.shape[0],
            )
            return None
        idx_map = registry.get_alignment_idx_map(group_id)
        if idx_map is None:
            return None

        # Build per-group context with source-tf cache key isolation.
        # row_count and time_range use native rows so d_star cache fingerprint
        # naturally invalidates when the source-tf row count changes and won't
        # collide with the primary-tf cache key for the same column.
        native_ctx = _dc_replace(
            self._preprocessing_context,
            timeframe=source_tf or self._preprocessing_context.timeframe,
            row_count=int(source_n_rows),
            time_range=None,  # Per-group native time range not currently tracked.
        )

        # Run L6.5 on native rows using a sibling preprocessor that owns its
        # own d_star_cache scoped to the source timeframe.
        native_pp = FeaturePreprocessor(scaled_config, context=native_ctx)
        native_pp._fracdiff_apply_to_layers = self._fracdiff_apply_to_layers

        native_df = pd.DataFrame(native_arr, columns=columns, copy=False)
        try:
            processed_df = native_pp._transform_single(
                native_df,
                source_layer=self._group_layer_name(group),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[L6.5] native-tf transform failed: group=%s err=%s, falling back",
                group_id,
                exc,
            )
            return None
        finally:
            del native_df, native_arr

        is_append = self.mode == "append"
        original_cols_present = [c for c in columns if c in processed_df.columns]
        if not original_cols_present:
            logger.warning(
                "[L6.5] native-tf transform produced no original columns for group=%s, falling back",
                group_id,
            )
            return None

        source_disk_path = getattr(group, "disk_path", None)

        # Expand original-column block back to primary rows via idx_map.
        orig_native = processed_df[original_cols_present].to_numpy(
            dtype=np.float32, copy=False
        )
        orig_aligned = apply_idx_map_to_array(orig_native, idx_map, primary_n_rows)
        del orig_native

        outputs: List[Tuple[str, List[str], np.ndarray]] = [
            (group_id, list(original_cols_present), orig_aligned),
        ]

        if is_append:
            new_cols = [c for c in processed_df.columns if c not in columns]
            if new_cols:
                new_native = processed_df[new_cols].to_numpy(dtype=np.float32, copy=False)
                new_aligned = apply_idx_map_to_array(new_native, idx_map, primary_n_rows)
                del new_native
                new_group_id = f"{group_id}_L65"
                suffix = 1
                while new_group_id in registry._groups:
                    new_group_id = f"{group_id}_L65_{suffix}"
                    suffix += 1
                outputs.append((new_group_id, list(new_cols), new_aligned))

        del processed_df

        for output_index, (out_group_id, out_columns, out_data) in enumerate(outputs):
            sink(
                out_group_id,
                out_columns,
                out_data,
                group_id,
                source_disk_path,
                output_index == len(outputs) - 1,
            )

        logger.info(
            "[L6.5] native-tf path completed: group=%s src_tf=%s primary_tf=%s "
            "native_rows=%d primary_rows=%d outputs=%d",
            group_id,
            source_tf,
            primary_tf,
            source_n_rows,
            primary_n_rows,
            len(outputs),
        )
        return len(outputs)

    def _maybe_run_native_l65_inplace(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
    ) -> bool:
        """Native-resolution L6.5 in-place variant.

        Loads native rows, runs L6.5, expands to primary rows via idx_map,
        and overwrites the registry entry with the primary-shaped result.
        Returns ``True`` when the native path was taken, ``False`` otherwise.

        Note: After ``overwrite_data`` the alignment metadata is stripped (the
        on-disk array now stores fully expanded primary rows). Downstream
        consumers using ``load_data`` see primary-shaped output, identical to
        the legacy expand-then-transform path — only the L6.5 statistics are
        computed correctly on native rows.
        """
        from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
            apply_idx_map_to_array,
            scale_preprocessing_config_for_native,
            should_use_native_path,
        )
        from momentum.FeatureEngineering.core.column_group import (
            ColumnGroup as _CG,
            LayerSource as _LS,
        )
        from dataclasses import replace as _dc_replace

        alignment = getattr(group, "alignment", None)
        if alignment is None:
            return False

        group_id = str(getattr(group, "group_id"))
        columns = list(getattr(group, "columns"))
        if not columns:
            return False

        source_tf = str(getattr(alignment, "source_timeframe", "") or "")
        primary_tf = str(getattr(alignment, "primary_timeframe", "") or "")
        source_n_rows = int(getattr(alignment, "source_n_rows", 0))
        primary_n_rows = int(getattr(alignment, "primary_n_rows", 0))

        scaled_config = scale_preprocessing_config_for_native(
            self._config,
            source_tf,
            primary_tf,
        )

        use_native, reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe=source_tf,
            primary_timeframe=primary_tf,
            source_n_rows=source_n_rows,
            scaled_config=scaled_config,
        )
        if not use_native:
            logger.info(
                "[L6.5] native-tf in-place skipped: group=%s reason=%s "
                "src_tf=%s primary_tf=%s native_rows=%d",
                group_id,
                reason,
                source_tf,
                primary_tf,
                source_n_rows,
            )
            return False

        native_arr = np.asarray(registry.load_data_native(group_id), dtype=np.float32)
        if native_arr.shape[0] != source_n_rows:
            logger.warning(
                "[L6.5] native-tf in-place row mismatch: group=%s expected=%d got=%d, "
                "falling back",
                group_id,
                source_n_rows,
                native_arr.shape[0],
            )
            return False
        idx_map = registry.get_alignment_idx_map(group_id)
        if idx_map is None:
            return False

        native_ctx = _dc_replace(
            self._preprocessing_context,
            timeframe=source_tf or self._preprocessing_context.timeframe,
            row_count=int(source_n_rows),
            time_range=None,
        )

        native_pp = FeaturePreprocessor(scaled_config, context=native_ctx)
        native_pp._fracdiff_apply_to_layers = self._fracdiff_apply_to_layers

        native_df = pd.DataFrame(native_arr, columns=columns, copy=False)
        try:
            processed_df = native_pp._transform_single(
                native_df,
                source_layer=self._group_layer_name(group),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[L6.5] native-tf in-place transform failed: group=%s err=%s, "
                "falling back",
                group_id,
                exc,
            )
            return False
        finally:
            del native_df, native_arr

        is_append = self.mode == "append"
        original_cols_present = [c for c in columns if c in processed_df.columns]
        if not original_cols_present:
            logger.warning(
                "[L6.5] native-tf in-place produced no original columns: group=%s, "
                "falling back",
                group_id,
            )
            return False

        orig_native = processed_df[original_cols_present].to_numpy(
            dtype=np.float32, copy=False
        )
        orig_aligned = apply_idx_map_to_array(orig_native, idx_map, primary_n_rows)
        del orig_native

        # If replace mode but column subset, fill gaps with original values.
        if len(original_cols_present) != len(columns):
            full_aligned = np.empty((primary_n_rows, len(columns)), dtype=np.float32)
            existing_primary = np.asarray(registry.load_data(group_id), dtype=np.float32)
            full_aligned[:] = existing_primary
            del existing_primary
            present_idx = [columns.index(c) for c in original_cols_present]
            full_aligned[:, present_idx] = orig_aligned
            del orig_aligned
            registry.overwrite_data(group_id, full_aligned)
            del full_aligned
        else:
            registry.overwrite_data(group_id, orig_aligned)
            del orig_aligned

        if is_append:
            new_cols = [c for c in processed_df.columns if c not in columns]
            if new_cols:
                new_native = processed_df[new_cols].to_numpy(
                    dtype=np.float32, copy=False
                )
                new_aligned = apply_idx_map_to_array(new_native, idx_map, primary_n_rows)
                del new_native
                new_gid = f"{group_id}_L65"
                suffix = 1
                while new_gid in registry._groups:
                    new_gid = f"{group_id}_L65_{suffix}"
                    suffix += 1
                new_group = _CG(
                    group_id=new_gid,
                    layer=_LS.L65,
                    timeframe=getattr(group, "timeframe"),
                    data_source="preprocessed",
                    indicator=getattr(group, "indicator"),
                    columns=tuple(new_cols),
                    shape=(new_aligned.shape[0], new_aligned.shape[1]),
                    dtype="float32",
                )
                registry.save_data(new_group, new_aligned)
                del new_aligned

        del processed_df

        logger.info(
            "[L6.5] native-tf in-place completed: group=%s src_tf=%s primary_tf=%s "
            "native_rows=%d primary_rows=%d",
            group_id,
            source_tf,
            primary_tf,
            source_n_rows,
            primary_n_rows,
        )
        return True

    def _warmup_numba_if_needed(self) -> None:
        """Compile relevant Numba kernels once before any fan-out begins."""

        if self._numba_warmed_up:
            return

        try:
            from momentum.FeatureEngineering.operators.numba_rolling import warmup_numba as warmup_rolling_numba

            warmup_rolling_numba()
        except ImportError:
            pass

        try:
            from momentum.FeatureEngineering.preprocessing._numba_transforms import warmup_numba as warmup_l65_numba

            warmup_l65_numba()
        except ImportError:
            pass

        self._numba_warmed_up = True

    @staticmethod
    def _group_n_columns(group: object) -> int:
        """Best-effort group width lookup for greedy scheduling."""

        n_columns = getattr(group, "n_columns", None)
        if isinstance(n_columns, int):
            return n_columns

        n_cols = getattr(group, "n_cols", None)
        if isinstance(n_cols, int):
            return n_cols

        return 0

    @staticmethod
    def _group_disk_size_bytes(group: object) -> int:
        """Total persisted bytes for a group (sum of shards or single file).

        Used by the largest-first raw-sink scheduler so sharded groups are
        ordered by their full footprint (not just the first shard).
        """
        # Prefer explicit shard total if present (Phase B Phase 1).
        shards = getattr(group, "shards", None) or ()
        if shards:
            return sum(int(getattr(shard, "nbytes", 0)) for shard in shards)
        disk_path = getattr(group, "disk_path", None)
        if disk_path is None:
            return 0
        try:
            path = Path(disk_path)
            if path.exists():
                return int(path.stat().st_size)
        except OSError:
            return 0
        return 0
        return 0

    @staticmethod
    def _raw_sink_largest_first_enabled() -> bool:
        raw = os.getenv("FFACT_L65_RAW_SINK_LARGEST_FIRST", "1").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    @staticmethod
    def _registry_io_stats(registry: "ColumnGroupRegistry") -> Dict[str, float]:
        stats = getattr(registry, "io_stats", None)
        if callable(stats):
            return stats()
        return {}

    @staticmethod
    def _log_registry_io_summary(
        registry: "ColumnGroupRegistry",
        before: Dict[str, float],
    ) -> None:
        stats = getattr(registry, "io_stats", None)
        if not callable(stats):
            return
        after = stats()

        def delta(key: str) -> float:
            return float(after.get(key, 0.0)) - float(before.get(key, 0.0))

        overwrite_count = delta("overwrite_count")
        persist_count = delta("persist_count")
        manifest_writes = delta("manifest_write_count")
        manifest_deferred = delta("manifest_deferred_count")
        if overwrite_count <= 0 and persist_count <= 0 and manifest_writes <= 0:
            return

        logger.info(
            "[L6.5] Registry I/O summary: overwrites=%.0f overwrite_mb=%.2f overwrite_sec=%.2f "
            "persists=%.0f persist_mb=%.2f persist_sec=%.2f manifest_writes=%.0f "
            "manifest_deferred=%.0f manifest_sec=%.2f",
            overwrite_count,
            delta("overwrite_bytes") / (1024 ** 2),
            delta("overwrite_seconds"),
            persist_count,
            delta("persist_bytes") / (1024 ** 2),
            delta("persist_seconds"),
            manifest_writes,
            manifest_deferred,
            delta("manifest_write_seconds"),
        )

    def _group_requires_slow_transform(
        self,
        group: object,
        transform_context: Dict[str, object],
    ) -> bool:
        if self.mode != "replace":
            return True
        # P1.1 fix: ADF per-layer routing — mirrors fracdiff logic (V1 SPEC intent).
        # ADF is the prerequisite step for FracDiff and only meaningful for layers that
        # undergo FracDiff (default: L1/L2 only). L3+ rolling groups do not need ADF and
        # should reach the fast path. The former global check (if do_adf: return True)
        # forced ALL 122 groups slow regardless of layer, which is a design defect.
        if bool(transform_context.get("do_adf", False)):
            if "ALL" in self._fracdiff_apply_to_layers:
                return True
            source_layer = self._group_layer_name(group)
            if source_layer and source_layer in self._fracdiff_apply_to_layers:
                return True
            # source_layer known and NOT in ADF/FracDiff target set → this group
            # does not need ADF; continue to per-layer fracdiff check below.
            # source_layer None (unknown origin) → also falls through; the fracdiff
            # column-based filter at the end handles unknown-layer groups correctly.
        # Gaussian with apply_to="all" is handled as a vectorised post-step after the
        # numba fast path (see _transform_single_group), so it does NOT force slow path.
        # Only non-"all" apply_to needs column names and therefore requires slow path.
        if bool(transform_context.get("do_gaussian", False)):
            if transform_context.get("gaussian_apply_to", "all") != "all":
                return True
        if not bool(transform_context.get("do_fracdiff", False)):
            return False

        if "ALL" in self._fracdiff_apply_to_layers:
            return True

        source_layer = self._group_layer_name(group)
        if source_layer:
            return source_layer in self._fracdiff_apply_to_layers

        columns = list(getattr(group, "columns", []))
        return bool(self._filter_fracdiff_target_columns(columns))

    def _transform_registry_serial(
        self,
        registry: "ColumnGroupRegistry",
        groups: List[object],
        transform_context: Dict[str, object],
    ) -> int:
        """Serial fallback path for deterministic L6.5 registry transforms."""
        from momentum.FeatureEngineering.utils.hardware_utils import get_l65_split_threshold

        completed = 0
        failed = 0
        started_at = time.perf_counter()

        use_fast = bool(transform_context.get("use_fast", False))
        can_use_numba_fast = bool(transform_context.get("can_use_numba_fast", use_fast))
        split_threshold = get_l65_split_threshold()

        # ── Sub-step progress logging ────────────────────────────────────
        # Mirrors the parallel path heartbeat so SIGKILL leaves the last
        # attempted group visible in the log.
        total = len(groups)
        heartbeat_step = max(1, total // 20)
        heartbeat_interval_sec = 30.0
        last_heartbeat_at = started_at
        last_heartbeat_done = 0
        last_group_label = "<none>"

        logger.info("[L6.5] Serial start: %d groups, rss=%dMB", total, _PROC.memory_info().rss >> 20)

        for group in groups:
            gid = getattr(group, "group_id", "<unknown>")
            n_cols = self._group_n_columns(group)
            try:
                # Route oversized slow-path groups through chunked processing
                # to cap peak memory (avoids 3-4× full_array copies for 1.8 GB groups).
                requires_slow = self._group_requires_slow_transform(group, transform_context)
                slow_route_candidate = requires_slow or not can_use_numba_fast
                if slow_route_candidate and split_threshold > 0 and n_cols > split_threshold:
                    self._transform_single_group_chunked(registry, group, chunk_size=split_threshold)
                    last_group_label = f"{gid} (slow-chunked)"
                else:
                    self._transform_single_group(registry, group, transform_context)
                    last_group_label = f"{gid} ({'slow' if slow_route_candidate else 'fast'})"
                completed += 1
            except Exception as error:
                failed += 1
                logger.error(
                    "[L6.5] Failed group %s: %s",
                    gid,
                    error,
                    exc_info=True,
                )

            gc.collect()
            now = time.perf_counter()
            done = completed + failed
            if (
                done - last_heartbeat_done >= heartbeat_step
                or (now - last_heartbeat_at) >= heartbeat_interval_sec
            ):
                elapsed_so_far = now - started_at
                rate = done / elapsed_so_far if elapsed_so_far > 0 else 0.0
                eta = (total - done) / rate if rate > 0 else float("inf")
                logger.info(
                    "[L6.5] heartbeat (serial): %d/%d (%.1f%%), elapsed=%.1fs, "
                    "rate=%.2f/s, ETA=%.0fs, rss=%dMB, last=%s",
                    done,
                    total,
                    100.0 * done / max(total, 1),
                    elapsed_so_far,
                    rate,
                    eta if eta != float("inf") else -1,
                    _PROC.memory_info().rss >> 20,
                    last_group_label,
                )
                last_heartbeat_at = now
                last_heartbeat_done = done

        elapsed = time.perf_counter() - started_at
        logger.info(
            "[L6.5] Serial complete: %d/%d in %.2fs (%d failed), rss=%dMB",
            completed,
            len(groups),
            elapsed,
            failed,
            _PROC.memory_info().rss >> 20,
        )
        return completed

    def _transform_registry_parallel(
        self,
        registry: "ColumnGroupRegistry",
        groups: List[object],
        transform_context: Dict[str, object],
        n_workers: int,
    ) -> int:
        """ThreadPool-based L6.5 registry transform with greedy scheduling.

        P1.2 — Large-group splitting:
            When a group's column count exceeds ``FFACT_L65_SPLIT_THRESHOLD``
            (tier-aware), it is partitioned into balanced column slices that
            run as independent sub-tasks in the same ThreadPool. This reduces
            tail latency caused by giant groups (e.g. ``L2_Momentum`` with
            ~16k cols) blocking otherwise idle workers. Splitting only applies
            on the fast (Numba) path because column-wise transforms (winsor /
            rank / zscore) are independent and safely concatenable; the slow
            pandas path is left intact for correctness.
        """

        if not groups:
            return 0

        from momentum.FeatureEngineering.utils.hardware_utils import get_l65_split_threshold

        split_threshold = get_l65_split_threshold()
        can_use_numba_fast = bool(
            transform_context.get(
                "can_use_numba_fast",
                bool(transform_context.get("use_fast", False)),
            )
        )
        can_split = can_use_numba_fast and split_threshold > 0

        ordered_groups = sorted(
            groups,
            key=self._group_n_columns,
            reverse=True,
        )

        # Partition groups into three categories:
        #   "full"         – normal ThreadPool task (fast or slow path, n_cols ≤ threshold)
        #   "split"        – fast-path Numba column-slice sub-tasks (n_cols > threshold)
        #   "slow_chunked" – slow-path (FracDiff/ADF) large-group sequential chunking
        full_groups: List[object] = []
        split_meta: Dict[str, Dict[str, object]] = {}
        slow_chunked_groups: List[object] = []
        slow_full_count = 0
        fast_full_count = 0
        max_group_cols = 0

        for group in ordered_groups:
            n_cols = self._group_n_columns(group)
            max_group_cols = max(max_group_cols, n_cols)
            requires_slow = self._group_requires_slow_transform(group, transform_context)
            slow_route_candidate = requires_slow or not can_use_numba_fast
            if (not requires_slow) and can_split and n_cols > split_threshold:
                # Balance slice widths: ceil(n_cols / n_splits) ensures a final
                # slice no larger than the others (avoids straggler).
                n_splits = (n_cols + split_threshold - 1) // split_threshold
                slice_width = (n_cols + n_splits - 1) // n_splits
                slices = [
                    (i * slice_width, min((i + 1) * slice_width, n_cols))
                    for i in range(n_splits)
                ]
                # Load array once; sub-tasks share read-only views.
                group_array = np.asarray(registry.load_data(group.group_id), dtype=np.float32)
                split_meta[group.group_id] = {
                    "group": group,
                    "array": group_array,
                    "slices": slices,
                    "results": {},
                    "completed_slices": 0,
                }
            elif slow_route_candidate and split_threshold > 0 and n_cols > split_threshold:
                # Slow path (FracDiff/ADF/Gaussian) with a large group: process in
                # column chunks sequentially to cap peak memory at ~full_array + chunk_copies
                # instead of full_array × 3–4 copies (which OOM-kills on 8 GB systems).
                # Task 1.1 keeps statsmodels ADF out of ThreadPool; optional loky
                # parallelism happens inside the FracDiff slow path only.
                slow_chunked_groups.append(group)
            else:
                full_groups.append(group)
                if slow_route_candidate:
                    slow_full_count += 1
                else:
                    fast_full_count += 1

        completed = 0
        failed = 0
        started_at = time.perf_counter()

        # ── Sub-step progress logging ────────────────────────────────────
        # Goal: when L6.5 OOM-kills mid-pipeline, the last log line tells
        # us which group/slice was running. Without this, we only see the
        # "Parallel complete" line at the very end (which never prints on
        # crash). Heartbeat every max(1, total//20) completions OR every
        # 30s, whichever comes first.
        total_tasks = (
            len(full_groups)
            + sum(len(info["slices"]) for info in split_meta.values())
            + len(slow_chunked_groups)
        )
        heartbeat_step = max(1, total_tasks // 20)
        heartbeat_interval_sec = 30.0
        last_heartbeat_at = started_at
        last_heartbeat_done = 0
        tasks_done = 0  # full task or single slice (fan-out granularity)
        last_group_label = "<none>"

        logger.info(
            "[L6.5] Parallel start: %d full groups (fast=%d, slow=%d) + "
            "%d big-group splits → %d sub-tasks "
            "(workers=%d, split_threshold=%d, slow_chunked=%d, max_group_cols=%d, rss=%dMB)",
            len(full_groups),
            fast_full_count,
            slow_full_count,
            len(split_meta),
            total_tasks,
            n_workers,
            split_threshold,
            len(slow_chunked_groups),
            max_group_cols,
            _PROC.memory_info().rss >> 20,
        )

        # Submit task type tagging: ("full", group, None) or ("slice", group, (s, e)).
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures: Dict[object, Tuple[str, object, Optional[Tuple[int, int]]]] = {}

            for group in full_groups:
                fut = pool.submit(self._transform_single_group, registry, group, transform_context)
                futures[fut] = ("full", group, None)

            for gid, info in split_meta.items():
                group_array = info["array"]
                for (start, end) in info["slices"]:
                    slice_view = group_array[:, start:end]
                    fut = pool.submit(self._transform_array_slice, slice_view, transform_context)
                    futures[fut] = ("slice", info["group"], (start, end))

            split_completed_groups: set[str] = set()

            for fut in as_completed(futures):
                kind, group, slice_range = futures[fut]
                gid = getattr(group, "group_id", "<unknown>")
                try:
                    result = fut.result()
                    if kind == "full":
                        completed += 1
                        last_group_label = f"{gid} (full)"
                    else:
                        meta = split_meta[gid]
                        meta["results"][slice_range] = result
                        meta["completed_slices"] += 1
                        last_group_label = (
                            f"{gid} slice[{slice_range[0]}:{slice_range[1]}] "
                            f"({meta['completed_slices']}/{len(meta['slices'])})"
                        )
                        if meta["completed_slices"] == len(meta["slices"]):
                            # Concatenate slices in column order and persist.
                            ordered = sorted(meta["results"].items(), key=lambda kv: kv[0][0])
                            merged = np.concatenate([r for _, r in ordered], axis=1)
                            registry.overwrite_data(gid, merged)
                            # Free intermediate buffers asap.
                            del meta["results"]
                            del meta["array"]
                            split_completed_groups.add(gid)
                            completed += 1
                            last_group_label = f"{gid} (split→merged)"
                except Exception as error:
                    failed += 1
                    logger.error(
                        "[L6.5] Failed group %s (%s): %s",
                        gid,
                        kind,
                        error,
                        exc_info=True,
                    )

                # Heartbeat: emit periodic progress so a SIGKILL leaves
                # the last-attempted group visible in the log.
                tasks_done += 1
                now = time.perf_counter()
                if (
                    tasks_done - last_heartbeat_done >= heartbeat_step
                    or (now - last_heartbeat_at) >= heartbeat_interval_sec
                ):
                    elapsed = now - started_at
                    rate = tasks_done / elapsed if elapsed > 0 else 0.0
                    eta = (total_tasks - tasks_done) / rate if rate > 0 else float("inf")
                    logger.info(
                        "[L6.5] heartbeat: tasks %d/%d (%.1f%%), groups %d/%d, "
                        "elapsed=%.1fs, rate=%.2f/s, ETA=%.0fs, rss=%dMB, last=%s",
                        tasks_done,
                        total_tasks,
                        100.0 * tasks_done / max(total_tasks, 1),
                        completed,
                        len(groups),
                        elapsed,
                        rate,
                        eta if eta != float("inf") else -1,
                        _PROC.memory_info().rss >> 20,
                        last_group_label,
                    )
                    last_heartbeat_at = now
                    last_heartbeat_done = tasks_done

        # ── Slow-path chunked groups (sequential, after ThreadPool) ──────
        # These are large groups (n_cols > split_threshold) on the slow path
        # (FracDiff/ADF/Gaussian). Processing them sequentially with column
        # chunking caps peak memory at ~full_array + chunk_copies instead of
        # full_array × 3–4 copies (which OOM-kills on 8 GB systems).
        for group in slow_chunked_groups:
            gid = getattr(group, "group_id", "<unknown>")
            try:
                safe_chunk_size = split_threshold if split_threshold > 0 else self._group_n_columns(group)
                self._transform_single_group_chunked(registry, group, chunk_size=safe_chunk_size)
                completed += 1
                last_group_label = f"{gid} (slow-chunked)"
            except Exception as error:
                failed += 1
                logger.error(
                    "[L6.5] Failed slow-chunked group %s: %s",
                    gid,
                    error,
                    exc_info=True,
                )
            gc.collect()

            tasks_done += 1
            now = time.perf_counter()
            if (
                tasks_done - last_heartbeat_done >= heartbeat_step
                or (now - last_heartbeat_at) >= heartbeat_interval_sec
            ):
                elapsed_so_far = now - started_at
                rate = tasks_done / elapsed_so_far if elapsed_so_far > 0 else 0.0
                eta = (total_tasks - tasks_done) / rate if rate > 0 else float("inf")
                logger.info(
                    "[L6.5] heartbeat: tasks %d/%d (%.1f%%), groups %d/%d, "
                    "elapsed=%.1fs, rate=%.2f/s, ETA=%.0fs, rss=%dMB, last=%s",
                    tasks_done,
                    total_tasks,
                    100.0 * tasks_done / max(total_tasks, 1),
                    completed,
                    len(groups),
                    elapsed_so_far,
                    rate,
                    eta if eta != float("inf") else -1,
                    _PROC.memory_info().rss >> 20,
                    last_group_label,
                )
                last_heartbeat_at = now
                last_heartbeat_done = tasks_done

        elapsed = time.perf_counter() - started_at
        split_count = len(split_meta)
        if split_count:
            total_slices = sum(len(info["slices"]) for info in split_meta.values())
            logger.info(
                "[L6.5] Parallel complete: %d/%d groups in %.2fs, %d workers "
                "(%d failed, %d big-group splits → %d sub-tasks, %d slow-chunked, rss=%dMB)",
                completed,
                len(groups),
                elapsed,
                n_workers,
                failed,
                split_count,
                total_slices,
                len(slow_chunked_groups),
                _PROC.memory_info().rss >> 20,
            )
        else:
            logger.info(
                "[L6.5] Parallel complete: %d/%d groups in %.2fs, %d workers "
                "(%d failed, %d slow-chunked, rss=%dMB)",
                completed,
                len(groups),
                elapsed,
                n_workers,
                failed,
                len(slow_chunked_groups),
                _PROC.memory_info().rss >> 20,
            )
        return completed

    def _transform_single_group_chunked(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        chunk_size: int,
    ) -> None:
        """Process a large CGSA group in column chunks on the slow (pandas/FracDiff) path.

        This is the memory-safe alternative to _transform_single_group for groups whose
        column count exceeds split_threshold when use_fast=False (i.e. FracDiff/ADF/Gaussian
        is enabled).

        Memory comparison for a 1.8 GB group (L2_WorldQuant):
          - Without chunking: full_array(1.8) + copy_A(1.8) + copy_B(3.6 append) = 7.2 GB
          - With chunk_size=2000: full_array(1.8) + chunk_copies(~0.14) = ~1.94 GB peak

        Correctness: All L6.5 transforms (winsor / rank / zscore / fracdiff / ADF /
        gaussian) are column-wise independent → chunking by columns is mathematically
        equivalent to processing all columns at once.

        Performance: d_star cache is loaded once per group (shared across chunks) to
        avoid 50× file-I/O storm. The full source array is freed before assembling
        the output to avoid compounding allocations.

        Handles both "replace" mode (same column count) and "append" mode (adds _fracdiff etc).
        """
        from momentum.FeatureEngineering.core.column_group import (
            ColumnGroup as _CG,
            LayerSource as _LS,
        )

        # Native-resolution L6.5 path for compact-aligned groups bypasses
        # column chunking entirely (native rows are already small).
        if self._maybe_run_native_l65_inplace(registry, group):
            return

        group_id = getattr(group, "group_id")
        col_names = list(getattr(group, "columns"))
        n_cols = len(col_names)

        # Load the full group array ONCE. Slice views below are zero-copy
        # when the underlying array is F-order (typical for CGSA .npy files).
        full_array = np.asarray(registry.load_data(group_id), dtype=np.float32)

        is_append = self.mode == "append"

        # ── Shared d_star cache (avoids per-chunk file I/O storm) ───────
        # Without this, every chunk re-loads/saves the cache file, turning
        # a 50-chunk group into 50 disk roundtrips during FracDiff search.
        use_shared_dstar_cache = bool(
            self.fracdiff_config.get("enabled", False)
            and self.fracdiff_config.get("cache_d_star", True)
        )
        previous_shared_cache = self._d_star_cache_shared
        if use_shared_dstar_cache:
            self._d_star_cache_shared = True
            self._d_star_cache = None

        orig_chunks: List[np.ndarray] = []
        new_chunks: List[np.ndarray] = []
        new_col_names_all: List[str] = []

        try:
            for chunk_start in range(0, n_cols, chunk_size):
                chunk_end = min(chunk_start + chunk_size, n_cols)
                chunk_cols = col_names[chunk_start:chunk_end]

                # F-order column slice is contiguous → pandas accepts copy=False
                # without an internal copy. C-order falls back to a chunk-sized
                # copy inside pandas (still much smaller than the full array).
                chunk_view = full_array[:, chunk_start:chunk_end]
                chunk_df = pd.DataFrame(chunk_view, columns=chunk_cols, copy=False)

                processed_df = self._transform_single(
                    chunk_df,
                    source_layer=self._group_layer_name(group),
                )

                orig_chunks.append(
                    processed_df[chunk_cols].to_numpy(dtype=np.float32, copy=False)
                )

                if is_append:
                    new_col_names = [c for c in processed_df.columns if c not in chunk_cols]
                    if new_col_names:
                        new_chunks.append(
                            processed_df[new_col_names].to_numpy(dtype=np.float32, copy=False)
                        )
                        new_col_names_all.extend(new_col_names)

                # Free chunk temporaries immediately to prevent RSS accumulation.
                del chunk_df, processed_df

        finally:
            # Persist d_star cache once after all chunks complete.
            if use_shared_dstar_cache and self._d_star_cache is not None:
                self._d_star_cache.flush_atomic()
                self._d_star_cache = None
            self._d_star_cache_shared = previous_shared_cache

            # Free the large source array before assembling results so the
            # concatenation allocations don't compound with it.
            del full_array
            gc.collect()

        # Reassemble original columns and write back to registry.
        orig_merged = np.concatenate(orig_chunks, axis=1)
        del orig_chunks
        registry.overwrite_data(group_id, orig_merged)
        del orig_merged
        gc.collect()

        # Create L65 group for appended columns (e.g. _fracdiff, _diff1).
        if is_append and new_chunks:
            new_merged = np.concatenate(new_chunks, axis=1)
            del new_chunks

            timeframe = getattr(group, "timeframe", "unknown")
            indicator = getattr(group, "indicator", "preprocessed")

            new_gid = f"{group_id}_L65"
            suffix = 1
            while new_gid in registry._groups:
                new_gid = f"{group_id}_L65_{suffix}"
                suffix += 1

            new_group = _CG(
                group_id=new_gid,
                layer=_LS.L65,
                timeframe=timeframe,
                data_source="preprocessed",
                indicator=indicator,
                columns=tuple(new_col_names_all),
                shape=(new_merged.shape[0], new_merged.shape[1]),
                dtype="float32",
            )
            registry.save_data(new_group, new_merged)
            del new_merged
            gc.collect()

    def _transform_array_slice(
        self,
        array_slice: np.ndarray,
        transform_context: Dict[str, object],
    ) -> np.ndarray:
        """Run the fast Numba transform pipeline on a column slice.

        Used by ``_transform_registry_parallel`` for big-group sub-tasks (P1.2).
        Inputs/outputs are decoupled from the registry; the caller concatenates
        slice results and writes back. Operations are column-wise so slicing is
        safe (winsor / rolling rank / rolling zscore each operate per column).
        """
        transform_array_fast = transform_context["transform_array_fast"]
        # Ensure contiguous float32 to satisfy numba layout assumptions.
        if not array_slice.flags["C_CONTIGUOUS"] or array_slice.dtype != np.float32:
            array_slice = np.ascontiguousarray(array_slice, dtype=np.float32)
        return transform_array_fast(
            array_slice,
            winsorize=bool(transform_context.get("do_winsorize", True)),
            winsor_method=str(transform_context.get("winsor_method", "quantile")),
            winsor_lower_q=float(transform_context.get("winsor_lower_q", 0.01)),
            winsor_upper_q=float(transform_context.get("winsor_upper_q", 0.99)),
            winsor_sigma_k=float(transform_context.get("winsor_sigma_k", 3.0)),
            rank=bool(transform_context.get("do_rank", False)),
            rank_window=int(transform_context.get("rank_window", 252)),
            zscore=bool(transform_context.get("do_zscore", False)),
            zscore_window=int(transform_context.get("zscore_window", 100)),
            zscore_epsilon=float(transform_context.get("zscore_epsilon", 1e-8)),
            causal_preprocessing=bool(transform_context.get("causal_preprocessing", True)),
            winsor_window=int(transform_context.get("winsor_window", 252)),
            winsor_min_periods=int(transform_context.get("winsor_min_periods", 63)),
        )

    def _transform_single_group(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        transform_context: Dict[str, object],
    ) -> None:
        """Transform a single registry group in-place."""

        from momentum.FeatureEngineering.core.column_group import ColumnGroup as _CG, LayerSource as _LS

        # Native-resolution L6.5 path for compact-aligned groups: compute on
        # source rows then expand to primary rows. Avoids step-function bias
        # in fracdiff and distribution-based statistics.
        if self._maybe_run_native_l65_inplace(registry, group):
            return

        group_id = getattr(group, "group_id")
        group_array = np.asarray(registry.load_data(group_id), dtype=np.float32)
        use_fast = bool(transform_context.get("can_use_numba_fast", transform_context.get("use_fast", False)))
        requires_slow = self._group_requires_slow_transform(group, transform_context)

        if use_fast and not requires_slow:
            transform_array_fast = transform_context["transform_array_fast"]
            processed_array = transform_array_fast(
                group_array,
                winsorize=bool(transform_context.get("do_winsorize", True)),
                winsor_method=str(transform_context.get("winsor_method", "quantile")),
                winsor_lower_q=float(transform_context.get("winsor_lower_q", 0.01)),
                winsor_upper_q=float(transform_context.get("winsor_upper_q", 0.99)),
                winsor_sigma_k=float(transform_context.get("winsor_sigma_k", 3.0)),
                rank=bool(transform_context.get("do_rank", False)),
                rank_window=int(transform_context.get("rank_window", 252)),
                zscore=bool(transform_context.get("do_zscore", False)),
                zscore_window=int(transform_context.get("zscore_window", 100)),
                zscore_epsilon=float(transform_context.get("zscore_epsilon", 1e-8)),
                causal_preprocessing=bool(transform_context.get("causal_preprocessing", True)),
                winsor_window=int(transform_context.get("winsor_window", 252)),
                winsor_min_periods=int(transform_context.get("winsor_min_periods", 63)),
            )
            # Gaussian post-step: apply_to="all" can be vectorised directly on the
            # numpy array without needing column names, so we handle it here instead
            # of forcing the entire group through pandas slow path.
            if bool(transform_context.get("do_gaussian", False)) and HAS_SCIPY:
                processed_array = self._gaussian_2d(
                    processed_array.astype(np.float64, copy=False),
                    lower=float(transform_context.get("gaussian_clip_lower", 0.001)),
                    upper=float(transform_context.get("gaussian_clip_upper", 0.999)),
                    causal=bool(transform_context.get("causal_preprocessing", True)),
                    window=int(transform_context.get("winsor_window", 252)),
                    min_periods=int(transform_context.get("winsor_min_periods", 63)),
                )
            registry.overwrite_data(group_id, processed_array)
            return

        if self._can_use_optimized_dataframe_path():
            self._transform_single_group_optimized(registry, group, group_array)
            return

        is_append = self.mode == "append"
        group_df = pd.DataFrame(group_array, columns=list(getattr(group, "columns")), copy=False)
        processed_df = self._transform_single(
            group_df,
            source_layer=self._group_layer_name(group),
        )

        if is_append and len(processed_df.columns) > getattr(group, "n_cols"):
            orig_cols = list(getattr(group, "columns"))
            orig_array = processed_df[orig_cols].to_numpy(dtype=np.float32, copy=False)
            registry.overwrite_data(group_id, orig_array)

            new_cols = [column for column in processed_df.columns if column not in orig_cols]
            if new_cols:
                new_array = processed_df[new_cols].to_numpy(dtype=np.float32, copy=False)
                new_gid = f"{group_id}_L65"
                suffix = 1
                while new_gid in registry._groups:
                    new_gid = f"{group_id}_L65_{suffix}"
                    suffix += 1
                new_group = _CG(
                    group_id=new_gid,
                    layer=_LS.L65,
                    timeframe=getattr(group, "timeframe"),
                    data_source="preprocessed",
                    indicator=getattr(group, "indicator"),
                    columns=tuple(new_cols),
                    shape=(new_array.shape[0], new_array.shape[1]),
                    dtype="float32",
                )
                registry.save_data(new_group, new_array)
            return

        processed_array = processed_df.to_numpy(dtype=np.float32, copy=False)
        registry.overwrite_data(group_id, processed_array)

    def _transform_single_group_to_arrays(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        transform_context: Dict[str, object],
    ) -> List[Tuple[str, List[str], np.ndarray]]:
        """Transform one registry group and return arrays instead of overwriting .npy."""
        group_id = str(getattr(group, "group_id"))
        columns = list(getattr(group, "columns"))
        group_array = np.asarray(registry.load_data(group_id), dtype=np.float32)
        use_fast = bool(transform_context.get("can_use_numba_fast", transform_context.get("use_fast", False)))
        requires_slow = self._group_requires_slow_transform(group, transform_context)

        if use_fast and not requires_slow:
            transform_array_fast = transform_context["transform_array_fast"]
            processed_array = transform_array_fast(
                group_array,
                winsorize=bool(transform_context.get("do_winsorize", True)),
                winsor_method=str(transform_context.get("winsor_method", "quantile")),
                winsor_lower_q=float(transform_context.get("winsor_lower_q", 0.01)),
                winsor_upper_q=float(transform_context.get("winsor_upper_q", 0.99)),
                winsor_sigma_k=float(transform_context.get("winsor_sigma_k", 3.0)),
                rank=bool(transform_context.get("do_rank", False)),
                rank_window=int(transform_context.get("rank_window", 252)),
                zscore=bool(transform_context.get("do_zscore", False)),
                zscore_window=int(transform_context.get("zscore_window", 100)),
                zscore_epsilon=float(transform_context.get("zscore_epsilon", 1e-8)),
                causal_preprocessing=bool(transform_context.get("causal_preprocessing", True)),
                winsor_window=int(transform_context.get("winsor_window", 252)),
                winsor_min_periods=int(transform_context.get("winsor_min_periods", 63)),
            )
            if bool(transform_context.get("do_gaussian", False)) and HAS_SCIPY:
                processed_array = self._gaussian_2d(
                    processed_array.astype(np.float64, copy=False),
                    lower=float(transform_context.get("gaussian_clip_lower", 0.001)),
                    upper=float(transform_context.get("gaussian_clip_upper", 0.999)),
                    causal=bool(transform_context.get("causal_preprocessing", True)),
                    window=int(transform_context.get("winsor_window", 252)),
                    min_periods=int(transform_context.get("winsor_min_periods", 63)),
                )
            return [(group_id, columns, np.asarray(processed_array, dtype=np.float32))]

        if self._can_use_optimized_dataframe_path():
            group_df = pd.DataFrame(group_array, columns=columns, copy=False)
            processed_df = self._transform_single_optimized_df(group_df)
            return [(group_id, list(processed_df.columns), processed_df.to_numpy(dtype=np.float32, copy=False))]

        is_append = self.mode == "append"
        group_df = pd.DataFrame(group_array, columns=columns, copy=False)
        processed_df = self._transform_single(
            group_df,
            source_layer=self._group_layer_name(group),
        )

        if is_append and len(processed_df.columns) > len(columns):
            outputs: List[Tuple[str, List[str], np.ndarray]] = []
            orig_array = processed_df[columns].to_numpy(dtype=np.float32, copy=False)
            outputs.append((group_id, columns, orig_array))

            new_columns = [column for column in processed_df.columns if column not in columns]
            if new_columns:
                new_group_id = f"{group_id}_L65"
                suffix = 1
                while new_group_id in registry._groups:
                    new_group_id = f"{group_id}_L65_{suffix}"
                    suffix += 1
                new_array = processed_df[new_columns].to_numpy(dtype=np.float32, copy=False)
                outputs.append((new_group_id, list(new_columns), new_array))
            return outputs

        processed_array = processed_df.to_numpy(dtype=np.float32, copy=False)
        return [(group_id, list(processed_df.columns), processed_array)]

    def _transform_single_group_chunked_to_arrays(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        chunk_size: int,
    ) -> List[Tuple[str, List[str], np.ndarray]]:
        """Chunked slow-path transform that streams arrays to the L7_raw writer."""
        group_id = str(getattr(group, "group_id"))
        col_names = list(getattr(group, "columns"))
        n_cols = len(col_names)
        full_array = np.asarray(registry.load_data(group_id), dtype=np.float32)
        is_append = self.mode == "append"

        use_shared_dstar_cache = bool(
            self.fracdiff_config.get("enabled", False)
            and self.fracdiff_config.get("cache_d_star", True)
        )
        previous_shared_cache = self._d_star_cache_shared
        if use_shared_dstar_cache:
            self._d_star_cache_shared = True
            self._d_star_cache = None

        orig_chunks: List[np.ndarray] = []
        new_chunks: List[np.ndarray] = []
        new_col_names_all: List[str] = []

        try:
            for chunk_start in range(0, n_cols, chunk_size):
                chunk_end = min(chunk_start + chunk_size, n_cols)
                chunk_cols = col_names[chunk_start:chunk_end]
                chunk_view = full_array[:, chunk_start:chunk_end]
                chunk_df = pd.DataFrame(chunk_view, columns=chunk_cols, copy=False)
                processed_df = self._transform_single(
                    chunk_df,
                    source_layer=self._group_layer_name(group),
                )
                orig_chunks.append(processed_df[chunk_cols].to_numpy(dtype=np.float32, copy=False))
                if is_append:
                    new_col_names = [column for column in processed_df.columns if column not in chunk_cols]
                    if new_col_names:
                        new_chunks.append(processed_df[new_col_names].to_numpy(dtype=np.float32, copy=False))
                        new_col_names_all.extend(new_col_names)
                del chunk_df, processed_df
        finally:
            if use_shared_dstar_cache and self._d_star_cache is not None:
                self._d_star_cache.flush_atomic()
                self._d_star_cache = None
            self._d_star_cache_shared = previous_shared_cache
            del full_array
            gc.collect()

        outputs: List[Tuple[str, List[str], np.ndarray]] = []
        orig_merged = np.concatenate(orig_chunks, axis=1)
        del orig_chunks
        outputs.append((group_id, col_names, orig_merged))

        if is_append and new_chunks:
            new_merged = np.concatenate(new_chunks, axis=1)
            del new_chunks
            new_group_id = f"{group_id}_L65"
            suffix = 1
            while new_group_id in registry._groups:
                new_group_id = f"{group_id}_L65_{suffix}"
                suffix += 1
            outputs.append((new_group_id, new_col_names_all, new_merged))

        return outputs

    def _stream_sharded_group_to_sink(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        transform_context: Dict[str, object],
        sink: Callable[[str, List[str], np.ndarray, str, Optional[Path], bool], None],
    ) -> int:
        """Transform a sharded group shard-by-shard and free shards as we go.

        Pre-conditions (enforced by caller): mode == 'replace', fast-path
        applicable (numba), no slow ops requiring per-column-cross-shard
        scope. Each shard is a column slice; column-independent kernels
        (winsor/rank/zscore) yield bit-equivalent output per shard vs the
        concatenated path. After the sink confirms parquet durability we
        unlink the source `.npy` shard so peak cgsa_work bytes shrink
        monotonically while the group is being written.
        """
        group_id = str(getattr(group, "group_id"))
        shards = tuple(getattr(group, "shards", ()) or ())
        n_shards = len(shards)
        if n_shards == 0:
            return 0

        transform_array_fast = transform_context["transform_array_fast"]
        do_gaussian = bool(transform_context.get("do_gaussian", False))
        gaussian_apply_to = transform_context.get("gaussian_apply_to", "all")
        gaussian_clip_lower = float(transform_context.get("gaussian_clip_lower", 0.001))
        gaussian_clip_upper = float(transform_context.get("gaussian_clip_upper", 0.999))

        outputs_written = 0
        width = max(2, len(str(n_shards - 1)))

        for shard_pos, (shard_meta, shard_arr, shard_cols) in enumerate(
            registry.iter_shards(group_id)
        ):
            is_last = shard_pos == n_shards - 1
            arr_in = np.asarray(shard_arr, dtype=np.float32)
            processed = transform_array_fast(
                arr_in,
                winsorize=bool(transform_context.get("do_winsorize", True)),
                winsor_method=str(transform_context.get("winsor_method", "quantile")),
                winsor_lower_q=float(transform_context.get("winsor_lower_q", 0.01)),
                winsor_upper_q=float(transform_context.get("winsor_upper_q", 0.99)),
                winsor_sigma_k=float(transform_context.get("winsor_sigma_k", 3.0)),
                rank=bool(transform_context.get("do_rank", False)),
                rank_window=int(transform_context.get("rank_window", 252)),
                zscore=bool(transform_context.get("do_zscore", False)),
                zscore_window=int(transform_context.get("zscore_window", 100)),
                zscore_epsilon=float(transform_context.get("zscore_epsilon", 1e-8)),
                causal_preprocessing=bool(transform_context.get("causal_preprocessing", True)),
                winsor_window=int(transform_context.get("winsor_window", 252)),
                winsor_min_periods=int(transform_context.get("winsor_min_periods", 63)),
            )
            if do_gaussian and HAS_SCIPY and gaussian_apply_to == "all":
                processed = self._gaussian_2d(
                    processed.astype(np.float64, copy=False),
                    lower=gaussian_clip_lower,
                    upper=gaussian_clip_upper,
                    causal=bool(transform_context.get("causal_preprocessing", True)),
                    window=int(transform_context.get("winsor_window", 252)),
                    min_periods=int(transform_context.get("winsor_min_periods", 63)),
                )
            processed = np.asarray(processed, dtype=np.float32)

            output_group_id = (
                group_id if n_shards == 1 else f"{group_id}_shard{shard_meta.shard_idx:0{width}d}"
            )

            sink(
                output_group_id,
                list(shard_cols),
                processed,
                group_id,
                shard_meta.disk_path,
                is_last,
            )
            outputs_written += 1

            del shard_arr, arr_in, processed

            if not is_last:
                try:
                    registry.unlink_shard(group_id, shard_meta.shard_idx)
                except Exception as exc:
                    logger.warning(
                        "[L6.5] shard cleanup skipped: group=%s shard=%d err=%s",
                        group_id,
                        shard_meta.shard_idx,
                        exc,
                    )
            gc.collect()

        return outputs_written

    def _stream_single_group_chunked_to_sink(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        chunk_size: int,
        sink: Callable[[str, List[str], np.ndarray, str, Optional[Path], bool], None],
        source_disk_path: Optional[Path],
    ) -> int:
        """Transform a wide slow-path group one column chunk at a time.

        The legacy chunked helper rebuilt the full transformed matrix with
        ``np.concatenate`` before L7_raw wrote parquet. For 20k x 25k+ groups
        that creates an avoidable multi-GB RSS spike. The raw-sink path can
        safely persist each transformed chunk as its own parquet group and
        delete the source ``.npy`` after the final chunk has landed.
        """
        group_id = str(getattr(group, "group_id"))
        col_names = list(getattr(group, "columns"))
        n_cols = len(col_names)
        if n_cols <= 0:
            return 0

        full_array = np.asarray(registry.load_data(group_id), dtype=np.float32)
        is_append = self.mode == "append"
        chunk_ranges = list(range(0, n_cols, chunk_size))
        total_chunks = len(chunk_ranges)

        use_shared_dstar_cache = bool(
            self.fracdiff_config.get("enabled", False)
            and self.fracdiff_config.get("cache_d_star", True)
        )
        previous_shared_cache = self._d_star_cache_shared
        if use_shared_dstar_cache:
            self._d_star_cache_shared = True
            self._d_star_cache = None

        outputs_written = 0
        logger.info(
            "[L6.5] raw-sink chunk stream start: group=%s cols=%d chunks=%d chunk_size=%d rss=%dMB",
            group_id,
            n_cols,
            total_chunks,
            chunk_size,
            _PROC.memory_info().rss >> 20,
        )

        try:
            for chunk_index, chunk_start in enumerate(chunk_ranges, 1):
                chunk_end = min(chunk_start + chunk_size, n_cols)
                chunk_cols = col_names[chunk_start:chunk_end]
                chunk_view = full_array[:, chunk_start:chunk_end]
                chunk_df = pd.DataFrame(chunk_view, columns=chunk_cols, copy=False)
                processed_df = self._transform_single(
                    chunk_df,
                    source_layer=self._group_layer_name(group),
                )

                chunk_outputs: List[Tuple[str, List[str], np.ndarray]] = []
                output_group_id = f"{group_id}_chunk{chunk_index}"
                chunk_outputs.append(
                    (
                        output_group_id,
                        chunk_cols,
                        processed_df[chunk_cols].to_numpy(dtype=np.float32, copy=False),
                    )
                )
                if is_append:
                    new_col_names = [column for column in processed_df.columns if column not in chunk_cols]
                    if new_col_names:
                        chunk_outputs.append(
                            (
                                f"{group_id}_L65_chunk{chunk_index}",
                                list(new_col_names),
                                processed_df[new_col_names].to_numpy(dtype=np.float32, copy=False),
                            )
                        )

                for output_index, (output_group_id, columns, data) in enumerate(chunk_outputs):
                    is_last_output = chunk_index == total_chunks and output_index == len(chunk_outputs) - 1
                    sink(
                        output_group_id,
                        columns,
                        data,
                        group_id,
                        source_disk_path,
                        is_last_output,
                    )
                    outputs_written += 1

                del chunk_outputs, chunk_df, processed_df, chunk_view
                gc.collect()
        finally:
            if use_shared_dstar_cache and self._d_star_cache is not None:
                self._d_star_cache.flush_atomic()
                self._d_star_cache = None
            self._d_star_cache_shared = previous_shared_cache
            del full_array
            gc.collect()

        logger.info(
            "[L6.5] raw-sink chunk stream complete: group=%s chunks=%d outputs=%d rss=%dMB",
            group_id,
            total_chunks,
            outputs_written,
            _PROC.memory_info().rss >> 20,
        )
        return outputs_written

    def _transform_single_group_optimized(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        group_array: Optional[np.ndarray] = None,
    ) -> None:
        """Transform a registry group via the optimized single-copy DataFrame path."""

        group_id = getattr(group, "group_id")
        source_array = group_array
        if source_array is None:
            source_array = np.asarray(registry.load_data(group_id), dtype=np.float32)

        group_df = pd.DataFrame(
            source_array,
            columns=list(getattr(group, "columns")),
            copy=False,
        )
        processed_df = self._transform_single_optimized_df(group_df)
        processed_array = processed_df.to_numpy(dtype=np.float32, copy=False)
        registry.overwrite_data(group_id, processed_array)

    @staticmethod
    def _group_layer_name(group: object) -> Optional[str]:
        layer = getattr(group, "layer", None)
        value = getattr(layer, "value", layer)
        if value is None:
            return None
        return str(value)

    def _can_use_optimized_dataframe_path(self) -> bool:
        if get_l65_optimization_profile() != "optimized":
            return False
        if self.mode != "replace":
            return False
        if self.fracdiff_config.get("enabled", False):
            return False
        if self.adf_config.get("enabled", False):
            return False
        return True

    def _optimized_replace_columns(self, features_df: pd.DataFrame) -> List[str]:
        selected_columns: List[str] = []
        seen_columns = set()

        def add_columns(columns: List[str]) -> None:
            for column in columns:
                if column not in seen_columns:
                    selected_columns.append(column)
                    seen_columns.add(column)

        add_columns(
            self._select_columns(
                features_df,
                self.winsor_config.get("apply_to", "all"),
            )
        )

        if self.rank_config.get("enabled", False):
            add_columns(
                self._select_columns(
                    features_df,
                    self.rank_config.get("apply_to", "all"),
                )
            )

        if self.gaussian_config.get("enabled", False):
            add_columns(
                self._select_columns(
                    features_df,
                    self.gaussian_config.get("apply_to", "all"),
                )
            )

        if self.zscore_config.get("enabled", False):
            add_columns(
                self._select_columns(
                    features_df,
                    self.zscore_config.get("apply_to", "all"),
                )
            )

        return selected_columns

    @staticmethod
    def _column_positions(
        all_columns: List[str],
        selected_columns: List[str],
    ) -> List[int]:
        position_by_column = {
            column: position for position, column in enumerate(all_columns)
        }
        return [
            position_by_column[column]
            for column in selected_columns
            if column in position_by_column
        ]

    def _winsorize_2d_legacy_equivalent(self, arr: np.ndarray) -> np.ndarray:
        # np.ascontiguousarray: zero-copy when arr is already C-contiguous float64.
        # Caller passes a fancy-indexed slice that NumPy has already materialised
        # as a separate float64 array, so .copy() here is always redundant.
        result_array = np.ascontiguousarray(arr, dtype=np.float64)
        selected = pd.DataFrame(result_array)
        method = self.winsor_config.get("method", "sigma")

        if method == "sigma":
            sigma_k = float(self.winsor_config.get("sigma_k", 3.0))
            if self.causal_preprocessing:
                window = self._rolling_window()
                min_periods = self._rolling_min_periods(window)
                means, stds = _rolling_mean_std(result_array, window, min_periods=min_periods)
                lowers = means.astype(np.float64) - sigma_k * stds.astype(np.float64)
                uppers = means.astype(np.float64) + sigma_k * stds.astype(np.float64)
                nan_mask = np.isnan(result_array)
                valid_bounds = np.isfinite(lowers) & np.isfinite(uppers)
                clipped = np.clip(result_array, lowers, uppers)
                result_array[valid_bounds] = clipped[valid_bounds]
                result_array[nan_mask] = np.nan
            else:
                means = selected.mean(skipna=True)
                stds = selected.std(skipna=True)
                valid_std = (~stds.isna()) & (stds != 0.0)
                if not valid_std.any():
                    return result_array

                valid_positions = valid_std[valid_std].index.tolist()
                lowers = means.loc[valid_positions] - sigma_k * stds.loc[valid_positions]
                uppers = means.loc[valid_positions] + sigma_k * stds.loc[valid_positions]
                clipped = selected.loc[:, valid_positions].clip(
                    lower=lowers,
                    upper=uppers,
                    axis=1,
                )
                result_array[:, valid_positions] = clipped.to_numpy(dtype=np.float32, copy=False)
            return result_array

        if method == "quantile":
            quantile_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
            lower_q = float(quantile_range[0])
            upper_q = float(quantile_range[1])
            if self.causal_preprocessing:
                window = self._rolling_window()
                min_periods = self._rolling_min_periods(window)
                lowers, uppers = rolling_quantile_2d(
                    result_array,
                    lower_q,
                    upper_q,
                    window,
                    min_periods,
                )
                nan_mask = np.isnan(result_array)
                # 暖機期 quantile bounds 無效 → pass-through 原值（非輸出 NaN）。
                valid_bounds = np.isfinite(lowers) & np.isfinite(uppers)
                clipped = np.clip(result_array, lowers, uppers)
                result_array[valid_bounds] = clipped[valid_bounds]
                result_array[nan_mask] = np.nan
                return result_array.astype(np.float32, copy=False)
            return self._winsorize_2d_inplace(
                result_array,
                lower_q,
                upper_q,
            ).astype(np.float32, copy=False)

        raise ValueError(f"Unsupported winsorization method: {method}")

    @staticmethod
    def _rolling_zscore_2d(
        arr: np.ndarray,
        windows: List[int],
        epsilon: float,
        mode: str = "replace",
    ) -> Union[np.ndarray, Dict[int, np.ndarray]]:
        if mode not in {"replace", "append"}:
            raise ValueError(f"Unsupported zscore mode: {mode}")

        selected = pd.DataFrame(np.asarray(arr, dtype=np.float64))
        normalized_windows = [int(window) for window in windows]

        if not normalized_windows:
            if mode == "append":
                return {}
            return selected.to_numpy(dtype=np.float32, copy=True)

        zscore_by_window: Dict[int, np.ndarray] = {}
        for window_int in normalized_windows:
            if window_int <= 0:
                raise ValueError("zscore window must be positive")

            rolling = selected.rolling(window_int, min_periods=1)
            mean = rolling.mean()
            std = rolling.std()
            zscore = (selected - mean) / (std + epsilon)
            zscore = zscore.where(std > 0.0, 0.0)
            zscore = zscore.where(~selected.isna(), np.nan)
            zscore_by_window[window_int] = zscore.to_numpy(dtype=np.float32, copy=False)

        if mode == "append":
            return zscore_by_window

        primary_window = normalized_windows[0]
        return zscore_by_window[primary_window]

    def _transform_single_optimized_df(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Single-copy replace-mode transform path for non-FracDiff/ADF L6.5 work."""

        working_columns = self._optimized_replace_columns(features_df)
        if not working_columns:
            return features_df.copy()

        working_values = features_df.loc[:, working_columns].to_numpy(
            dtype=np.float64,
            copy=True,
        )

        winsor_positions = self._column_positions(
            working_columns,
            self._select_columns(
                features_df,
                self.winsor_config.get("apply_to", "all"),
            ),
        )
        if winsor_positions:
            working_values[:, winsor_positions] = self._winsorize_2d_legacy_equivalent(
                working_values[:, winsor_positions]
            )

        if self.rank_config.get("enabled", False):
            rank_positions = self._column_positions(
                working_columns,
                self._select_columns(
                    features_df,
                    self.rank_config.get("apply_to", "all"),
                ),
            )
            if rank_positions:
                rank_window = int(self.rank_config.get("window", 252))
                working_values[:, rank_positions] = self._rolling_rank_2d_v2(
                    working_values[:, rank_positions],
                    rank_window,
                )

        if self.gaussian_config.get("enabled", False):
            if HAS_SCIPY:
                gaussian_positions = self._column_positions(
                    working_columns,
                    self._select_columns(
                        features_df,
                        self.gaussian_config.get("apply_to", "all"),
                    ),
                )
                if gaussian_positions:
                    clip_range = self.gaussian_config.get("clip_range", [0.001, 0.999])
                    working_values[:, gaussian_positions] = self._gaussian_2d(
                        working_values[:, gaussian_positions],
                        lower=float(clip_range[0]),
                        upper=float(clip_range[1]),
                        causal=self.causal_preprocessing,
                        window=self._rolling_window(),
                        min_periods=self._rolling_min_periods(self._rolling_window()),
                    )
            else:
                logger.warning("Gaussian normalization skipped: scipy unavailable")

        if self.zscore_config.get("enabled", False):
            zscore_positions = self._column_positions(
                working_columns,
                self._select_columns(
                    features_df,
                    self.zscore_config.get("apply_to", "all"),
                ),
            )
            if zscore_positions:
                windows = [int(window) for window in self.zscore_config.get("windows", [100, 252])]
                epsilon = float(self.zscore_config.get("epsilon", 1e-8))
                zscore_values = self._rolling_zscore_2d(
                    working_values[:, zscore_positions],
                    windows,
                    epsilon,
                    mode="replace",
                )
                working_values[:, zscore_positions] = zscore_values

        result = features_df.copy()
        result.loc[:, working_columns] = working_values
        return result

    def _transform_single(
        self,
        features_df: pd.DataFrame,
        source_layer: Optional[str] = None,
    ) -> pd.DataFrame:
        """Original transform logic applied to a full DataFrame."""
        self._fracdiff_processed_columns = set()
        if self._can_use_optimized_dataframe_path():
            return self._transform_single_optimized_df(features_df)

        return self._transform_single_legacy(features_df, source_layer=source_layer)

    def _transform_single_legacy(
        self,
        features_df: pd.DataFrame,
        source_layer: Optional[str] = None,
    ) -> pd.DataFrame:
        """Legacy per-transform DataFrame-copy pipeline."""
        transformed = features_df.copy()
        self._fracdiff_processed_columns = set()

        transformed = self._apply_winsorization(transformed)

        if self.fracdiff_config.get("enabled", False):
            transformed = self._apply_fractional_differencing(
                transformed,
                source_layer=source_layer,
            )

        if self.adf_config.get("enabled", False):
            transformed = self._apply_adf_differencing(transformed)

        if self.rank_config.get("enabled", False):
            transformed = self._apply_rank_transform(transformed)

        if self.gaussian_config.get("enabled", False):
            transformed = self._apply_gaussian_normalize(transformed)

        if self.zscore_config.get("enabled", False):
            transformed = self._apply_adaptive_zscore(transformed)

        return transformed

    def _transform_single_polars(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Polars-based L6.5 transform (Task 4.3).

        Handles winsorization, rank, zscore using Polars expressions.
        fracdiff and ADF are not supported (require scipy/statsmodels)
        and must use the pandas path.
        """
        from momentum.FeatureEngineering.polars_adapter import (
            pandas_to_polars,
            polars_l65_adaptive_zscore,
            polars_l65_rank_transform,
            polars_l65_winsorization,
            polars_to_pandas,
        )

        pl_df = pandas_to_polars(features_df)

        # Winsorization
        winsor_apply_to = self.winsor_config.get("apply_to", "all")
        winsor_columns = self._select_columns(features_df, winsor_apply_to)
        if winsor_columns:
            method = self.winsor_config.get("method", "sigma")
            sigma_k = float(self.winsor_config.get("sigma_k", 3.0))
            quantile_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
            pl_df = polars_l65_winsorization(
                pl_df,
                columns=winsor_columns,
                method=method,
                sigma_k=sigma_k,
                quantile_range=(float(quantile_range[0]), float(quantile_range[1])),
                causal_preprocessing=self.causal_preprocessing,
                window=self._rolling_window(),
                min_periods=self._rolling_min_periods(self._rolling_window()),
            )

        # ADF differencing (pandas fallback — not supported in Polars)
        if self.adf_config.get("enabled", False):
            # Convert back to pandas, apply ADF, then convert back
            pd_temp = polars_to_pandas(pl_df, index=features_df.index)
            pd_temp = self._apply_adf_differencing(pd_temp)
            pl_df = pandas_to_polars(pd_temp)

        # Rank transform (polars 1.x: map_batches + scipy, numerically equiv. to pandas)
        if self.rank_config.get("enabled", False):
            rank_apply_to = self.rank_config.get("apply_to", "all")
            rank_columns = self._select_columns(features_df, rank_apply_to)
            rank_window = int(self.rank_config.get("window", 252))
            if rank_columns and self.mode == "replace":
                pl_df = polars_l65_rank_transform(
                    pl_df, columns=rank_columns, window=rank_window
                )
            else:
                # append mode or empty column list: fall back to pandas
                pd_temp = polars_to_pandas(pl_df, index=features_df.index)
                pd_temp = self._apply_rank_transform(pd_temp)
                pl_df = pandas_to_polars(pd_temp)

        # Gaussian normalize (pandas fallback — requires scipy erfinv)
        if self.gaussian_config.get("enabled", False):
            pd_temp = polars_to_pandas(pl_df, index=features_df.index)
            pd_temp = self._apply_gaussian_normalize(pd_temp)
            pl_df = pandas_to_polars(pd_temp)

        # Adaptive z-score
        if self.zscore_config.get("enabled", False):
            zscore_apply_to = self.zscore_config.get("apply_to", "all")
            zscore_columns = self._select_columns(features_df, zscore_apply_to)
            windows = self.zscore_config.get("windows", [100, 252])
            epsilon = float(self.zscore_config.get("epsilon", 1e-8))
            primary_window = int(windows[0]) if windows else 100
            if zscore_columns and self.mode == "replace":
                pl_df = polars_l65_adaptive_zscore(
                    pl_df, columns=zscore_columns, window=primary_window, epsilon=epsilon
                )
            elif zscore_columns:
                # append mode: fall back to pandas
                pd_temp = polars_to_pandas(pl_df, index=features_df.index)
                pd_temp = self._apply_adaptive_zscore(pd_temp)
                pl_df = pandas_to_polars(pd_temp)

        result = polars_to_pandas(pl_df, index=features_df.index)
        return result

    def _transform_chunked(self, features_df: pd.DataFrame, chunk_size: int) -> pd.DataFrame:
        """Process columns in chunks to limit peak memory on wide DataFrames.

        All L6.5 operations (winsorization, rank_transform, adaptive_zscore, etc.)
        are column-independent, so chunking does not affect correctness.
        """
        all_columns = list(features_df.columns)
        n_chunks = (len(all_columns) + chunk_size - 1) // chunk_size
        logger.info(
            "[L6.5] Column chunking activated: %d cols → %d chunks of ≤%d",
            len(all_columns),
            n_chunks,
            chunk_size,
        )

        result_chunks: List[pd.DataFrame] = []
        use_memmap = (len(features_df.index) * len(all_columns) * 4) >= 500_000_000

        use_shared_dstar_cache = bool(
            self.fracdiff_config.get("enabled", False)
            and self.fracdiff_config.get("cache_d_star", True)
        )
        previous_shared_cache = self._d_star_cache_shared
        if use_shared_dstar_cache:
            # Load once for the whole run (instead of once per chunk).
            self._d_star_cache_shared = True
            self._d_star_cache = None

        if use_memmap:
            from momentum.FeatureEngineering.memmap_utils import create_temp_memmap
            import numpy as _np

            out_arr = create_temp_memmap(
                (len(features_df.index), len(all_columns)), prefix="l65_"
            )
            col_offset = 0

        try:
            for i in range(0, len(all_columns), chunk_size):
                chunk_cols = all_columns[i : i + chunk_size]
                chunk_idx = i // chunk_size + 1
                logger.info("[L6.5] Processing chunk %d/%d (%d cols)", chunk_idx, n_chunks, len(chunk_cols))

                chunk_df = features_df[chunk_cols]
                processed_chunk = self._transform_single(chunk_df)

                if use_memmap:
                    n = processed_chunk.shape[1]
                    out_arr[:, col_offset : col_offset + n] = _np.asarray(
                        processed_chunk.values, dtype=_np.float32
                    )
                    col_offset += n
                    del processed_chunk
                else:
                    result_chunks.append(processed_chunk)

                # Release references to reduce peak memory
                del chunk_df
        finally:
            if use_shared_dstar_cache and self._d_star_cache is not None:
                # Save once after all chunks complete.
                self._d_star_cache.flush_atomic()
                self._d_star_cache = None
            self._d_star_cache_shared = previous_shared_cache

        if use_memmap:
            return pd.DataFrame(
                data=out_arr, index=features_df.index, columns=all_columns, copy=False,
            )

        if not result_chunks:
            return pd.DataFrame(index=features_df.index)

        return pd.concat(result_chunks, axis=1, copy=False)

    def _apply_winsorization(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.winsor_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        method = self.winsor_config.get("method", "sigma")

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)

        if method == "sigma":
            sigma_k = float(self.winsor_config.get("sigma_k", 3.0))
            if self.causal_preprocessing:
                window = self._rolling_window()
                min_periods = self._rolling_min_periods(window)
                arr = selected.to_numpy(dtype=np.float64, copy=True)
                means, stds = _rolling_mean_std(arr, window, min_periods=min_periods)
                lowers = means.astype(np.float64) - sigma_k * stds.astype(np.float64)
                uppers = means.astype(np.float64) + sigma_k * stds.astype(np.float64)
                nan_mask = np.isnan(arr)
                valid_bounds = np.isfinite(lowers) & np.isfinite(uppers)
                clipped = np.clip(arr, lowers, uppers)
                arr[valid_bounds] = clipped[valid_bounds]
                arr[nan_mask] = np.nan
                result.loc[:, columns] = pd.DataFrame(
                    arr.astype(np.float32, copy=False),
                    index=selected.index,
                    columns=columns,
                )
            else:
                means = selected.mean(skipna=True)
                stds = selected.std(skipna=True)
                valid_std = (~stds.isna()) & (stds != 0.0)
                if not valid_std.any():
                    return result

                valid_columns = valid_std[valid_std].index.tolist()
                lowers = means.loc[valid_columns] - sigma_k * stds.loc[valid_columns]
                uppers = means.loc[valid_columns] + sigma_k * stds.loc[valid_columns]
                clipped = selected.loc[:, valid_columns].clip(lower=lowers, upper=uppers, axis=1)
                clipped = clipped.astype(np.float32, copy=False)
                result.loc[:, valid_columns] = clipped
        elif method == "quantile":
            quantile_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
            lower_q = float(quantile_range[0])
            upper_q = float(quantile_range[1])
            selected_array = selected.to_numpy(dtype=np.float64, copy=True)
            if self.causal_preprocessing:
                window = self._rolling_window()
                min_periods = self._rolling_min_periods(window)
                lowers, uppers = rolling_quantile_2d(
                    selected_array,
                    lower_q,
                    upper_q,
                    window,
                    min_periods,
                )
                nan_mask = np.isnan(selected_array)
                valid_bounds = np.isfinite(lowers) & np.isfinite(uppers)
                clipped = np.clip(selected_array, lowers, uppers)
                selected_array[valid_bounds] = clipped[valid_bounds]
                selected_array[nan_mask] = np.nan
                clipped_array = selected_array
            else:
                clipped_array = self._winsorize_2d_inplace(
                    selected_array,
                    lower_q,
                    upper_q,
                )
            clipped = pd.DataFrame(
                clipped_array.astype(np.float32, copy=False),
                index=selected.index,
                columns=columns,
            )
            result.loc[:, columns] = clipped
        else:
            raise ValueError(f"Unsupported winsorization method: {method}")

        return result

    @staticmethod
    def _partition_nanquantile_2d(
        arr: np.ndarray,
        quantiles: List[float],
    ) -> np.ndarray:
        """O(n) partial-sort replacement for np.nanquantile(arr, q, axis=0).

        Fast path (all columns have the same finite-element count):
            Replaces NaN/inf with +inf to push them after all finite values,
            then calls ``np.partition`` once for all required k-th positions.
            Complexity: O(n × |kths|) where |kths| ≤ 2 × len(quantiles).

        Slow path (heterogeneous finite-element counts across columns):
            Falls back to ``_nanquantile_linear`` (np.nanquantile).  Triggered
            only when columns differ in NaN count — uncommon for L6.5 rolling
            groups where every column shares the same rolling-window warmup
            NaN prefix.

        Numerical equivalence:
            Produces bit-identical output to
            ``np.nanquantile(..., method='linear')`` for all inputs where the
            fast path applies.
        """
        n_rows, n_cols = arr.shape
        if n_cols == 0:
            return np.empty((len(quantiles), 0), dtype=np.float64)
        finite_counts = np.sum(np.isfinite(arr), axis=0)  # shape: (n_cols,)

        # Fast path: uniform finite-element count across all columns.
        # L6.5 rolling groups satisfy this because each group's rolling-window
        # warmup NaN prefix is identical for every column in the group.
        if int(finite_counts.min()) == int(finite_counts.max()):
            n_valid = int(finite_counts[0])
            if n_valid == 0:
                # Every value in every column is NaN → return NaN bounds.
                return np.full((len(quantiles), n_cols), np.nan, dtype=np.float64)

            # Push NaN / ±inf to the end of each column so np.partition
            # sees only finite values in the first n_valid positions.
            tmp = arr.copy()
            tmp[~np.isfinite(tmp)] = np.inf

            # Pre-compute k-th positions and linear-interpolation fractions.
            k_lo_list: List[int] = []
            k_hi_list: List[int] = []
            frac_list: List[float] = []
            kths_seen: set = set()
            kths_sorted: List[int] = []
            for q in quantiles:
                k_f = float(q) * (n_valid - 1)
                k_lo = int(np.floor(k_f))
                k_hi = min(k_lo + 1, n_valid - 1)
                frac = k_f - k_lo
                k_lo_list.append(k_lo)
                k_hi_list.append(k_hi)
                frac_list.append(frac)
                for k in (k_lo, k_hi):
                    if k not in kths_seen:
                        kths_seen.add(k)
                        kths_sorted.append(k)

            # Single np.partition call covers all needed positions.
            partitioned = np.partition(tmp, sorted(kths_sorted), axis=0)

            results = np.empty((len(quantiles), n_cols), dtype=np.float64)
            for q_idx in range(len(quantiles)):
                lo = partitioned[k_lo_list[q_idx]]   # shape: (n_cols,)
                hi = partitioned[k_hi_list[q_idx]]   # shape: (n_cols,)
                results[q_idx] = lo + frac_list[q_idx] * (hi - lo)
            return results

        # Slow path: heterogeneous NaN counts → fall back to nanquantile.
        return FeaturePreprocessor._nanquantile_linear(arr, quantiles)

    @staticmethod
    def _nanquantile_linear(
        arr: np.ndarray,
        quantiles: List[float],
    ) -> np.ndarray:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="All-NaN slice encountered",
                category=RuntimeWarning,
            )
            try:
                return np.nanquantile(
                    arr,
                    quantiles,
                    axis=0,
                    method="linear",
                )
            except TypeError:
                return np.nanquantile(
                    arr,
                    quantiles,
                    axis=0,
                    interpolation="linear",
                )

    @classmethod
    def _winsorize_2d_inplace(
        cls,
        arr: np.ndarray,
        lower_q: float,
        upper_q: float,
        method: str = "linear",
    ) -> np.ndarray:
        if method != "linear":
            raise ValueError(f"Unsupported winsorize quantile method: {method}")

        if arr.ndim != 2:
            raise ValueError("winsorize input must be a 2D array")
        if arr.shape[0] == 0 or arr.shape[1] == 0:
            return arr

        bounds = cls._partition_nanquantile_2d(arr, [lower_q, upper_q])
        np.clip(arr, bounds[0], bounds[1], out=arr)
        return arr

    def _resolve_fracdiff_precision(self) -> float:
        return get_fracdiff_precision(self.fracdiff_config.get("precision", 0.02))

    def _filter_fracdiff_target_columns(
        self,
        columns: List[str],
        source_layer: Optional[str] = None,
    ) -> List[str]:
        if "ALL" in self._fracdiff_apply_to_layers:
            return self._apply_adf_safe_skip(list(columns), context="fracdiff")

        if source_layer:
            if source_layer in self._fracdiff_apply_to_layers:
                return self._apply_adf_safe_skip(list(columns), context=f"fracdiff/{source_layer}")
            logger.info(
                "[L6.5] FracDiff skipped by registry layer: layer=%s allowed=%s columns=%d",
                source_layer,
                sorted(self._fracdiff_apply_to_layers),
                len(columns),
            )
            return []

        if self._column_layer_map is not None:
            target_columns = [
                column
                for column in columns
                if column in self._column_layer_map
                and self._column_layer_map[column] in self._fracdiff_apply_to_layers
            ]
            unknown_columns = [column for column in columns if column not in self._column_layer_map]
            if unknown_columns:
                logger.warning(
                    "[L6.5] FracDiff layer map missing %d/%d columns; "
                    "treating unknown columns as non-target. examples=%s",
                    len(unknown_columns),
                    len(columns),
                    [str(column) for column in unknown_columns[:5]],
                )
            return self._apply_adf_safe_skip(target_columns, context="fracdiff/layer_map")

        target_columns: List[str] = []
        parse_failed = 0
        parse_failed_examples: List[str] = []
        for column in columns:
            column_text = str(column)
            match = _FRACDIFF_LAYER_RE.match(column_text)
            if match is None:
                parse_failed += 1
                if len(parse_failed_examples) < 5:
                    parse_failed_examples.append(column_text)
                continue
            if match.group(1) in self._fracdiff_apply_to_layers:
                target_columns.append(column)

        if parse_failed:
            logger.warning(
                "[L6.5] Layer parse failed for FracDiff filter: unparsed_columns=%d/%d "
                "allowed=%s examples=%s; treating unparsed columns as non-target",
                parse_failed,
                len(columns),
                sorted(self._fracdiff_apply_to_layers),
                parse_failed_examples,
            )

        return self._apply_adf_safe_skip(target_columns, context="fracdiff")

    def _apply_adf_safe_skip(self, columns: List[str], *, context: str) -> List[str]:
        """對 columns 套用 ADF safe-skip whitelist。

        對「數學上嚴格 I(0)」的欄位（嚴格有界 / 數學差分 / 共整合差）
        bypass ADF 測試直接視為 I(0) → 不進入 fracdiff / adf_differencing。

        詳見 docs/NAN_REDUCTION_STRATEGY.md §4.5。
        """
        if not columns:
            return columns
        cfg = self.adf_safe_skip_config
        enabled = bool(cfg.get("enabled", True))
        additional = tuple(cfg.get("additional_patterns") or ())
        exclusions = tuple(cfg.get("exclusion_patterns") or ())
        needs_adf, skipped = filter_safe_skip(
            columns,
            enabled=enabled,
            additional_patterns=additional,
            exclusion_patterns=exclusions,
        )
        if skipped:
            pct = len(skipped) / max(len(columns), 1) * 100.0
            logger.info(
                "[ADF Safe-Skip][%s] bypassed %d/%d cols (%.1f%%); examples: %s",
                context, len(skipped), len(columns), pct, skipped[:3],
            )
        return needs_adf

    @staticmethod
    def _d_star_cache_dir() -> Path:
        return MomentumConfig.from_project_root().data_cache_path / "feature_preprocessing"

    def _create_d_star_cache(
        self,
        *,
        adf_threshold: float,
        precision: float,
        max_lag: int,
        weight_threshold: float,
    ) -> DStarCache:
        sample_size = int(
            self.fracdiff_config.get(
                "sample_size",
                self.adf_config.get("sample_size", 500),
            )
        )
        return DStarCache(
            self._preprocessing_context,
            self._d_star_cache_dir(),
            adf_threshold=adf_threshold,
            precision=precision,
            max_lag=max_lag,
            weight_threshold=weight_threshold,
            sample_size=sample_size,
            nan_policy="dropna",
            adf_engine_version=self._adf_engine_version(),
            causal_preprocessing=self.causal_preprocessing,
            calibration_bars=self._calibration_bars(),
        )

    @staticmethod
    def _adf_engine_version() -> str:
        if get_fast_adf_enabled():
            return FAST_ADF_ENGINE_VERSION
        return ADF_ENGINE_VERSION

    @staticmethod
    def _adf_pvalue_for_values(values: np.ndarray, sample_size: int = 500) -> float:
        clean_values = np.asarray(values, dtype=np.float64)
        clean_values = clean_values[np.isfinite(clean_values)]
        if clean_values.size < 20:
            return 1.0
        if get_fast_adf_enabled():
            return float(adf_pvalue_fast(clean_values, sample_size=sample_size)[0])
        try:
            return float(adfuller(pd.Series(clean_values).head(sample_size), autolag="AIC")[1])
        except Exception:
            return 1.0

    @staticmethod
    def _assign_fracdiff_result(
        result: pd.DataFrame,
        column: str,
        fracdiff_series: pd.Series,
        mode: str,
    ) -> None:
        if mode == "replace":
            result[column] = fracdiff_series
        else:
            result[f"{column}_fracdiff"] = fracdiff_series

    def _resolve_slowpath_n_jobs(self) -> int:
        try:
            tier_gb = get_current_tier_gb()
        except Exception:
            tier_gb = 8
        concurrent_symbols = get_batch_symbol_concurrency()
        return get_slowpath_n_jobs(tier_gb, concurrent_symbols=concurrent_symbols)

    def _apply_fractional_differencing_serial(
        self,
        result: pd.DataFrame,
        eligible_columns: List[str],
        *,
        cache: Optional[DStarCache],
        adf_threshold: float,
        d_range: Tuple[float, float],
        precision: float,
        max_lag: int,
        weight_threshold: float,
    ) -> pd.DataFrame:
        for column in eligible_columns:
            series = result[column].astype(float)
            col_arr = series.to_numpy(dtype=np.float64, copy=False)
            cache_arr = self._calibration_values(col_arr)

            try:
                cached_d_star = cache.get(column, cache_arr) if cache is not None else None
                if cached_d_star is not None:
                    d_star = cached_d_star
                else:
                    d_star = self._find_min_d(
                        series,
                        adf_threshold=adf_threshold,
                        d_range=d_range,
                        precision=precision,
                        max_lag=max_lag,
                    )
                    if cache is not None:
                        cache.set(column, d_star, cache_arr)
            except Exception as exc:
                logger.warning("FracDiff d* search failed for %s: %s; fallback to d=1.0", column, exc)
                d_star = 1.0

            fracdiff_series = self._frac_diff_ffd(
                series,
                d_star,
                threshold=weight_threshold,
                max_width=max_lag,
            )
            self._assign_fracdiff_result(result, column, fracdiff_series, self.mode)
            self._fracdiff_processed_columns.add(column)

        return result

    def _apply_fractional_differencing_parallel(
        self,
        result: pd.DataFrame,
        eligible_columns: List[str],
        *,
        cache: Optional[DStarCache],
        adf_threshold: float,
        d_range: Tuple[float, float],
        precision: float,
        max_lag: int,
        weight_threshold: float,
        n_jobs: int,
    ) -> pd.DataFrame:
        sample_size = int(
            self.fracdiff_config.get(
                "sample_size",
                self.adf_config.get("sample_size", 500),
            )
        )
        col_input_arrays: Dict[str, np.ndarray] = {}
        duplicate_columns_by_rep: Dict[str, List[str]] = {}
        item_rep_by_value: Dict[str, str] = {}
        items: List[Tuple[np.ndarray, Dict[str, object]]] = []
        for column in eligible_columns:
            series = result[column].astype(float)
            col_arr = series.to_numpy(dtype=np.float64, copy=False)
            cache_arr = self._calibration_values(col_arr)
            col_input_arrays[column] = col_arr
            value_key = _strong_col_value_fingerprint(col_arr)
            cached_d_star = (
                cache.get_by_value_fingerprint(
                    column,
                    weak_fp=_col_value_fingerprint(cache_arr),
                    strong_fp=_strong_col_value_fingerprint(cache_arr),
                )
                if cache is not None
                else None
            )
            dedupe_key = f"{value_key}:{cached_d_star if cached_d_star is not None else 'miss'}"
            representative = item_rep_by_value.get(dedupe_key)
            if representative is not None:
                duplicate_columns_by_rep[representative].append(column)
                continue
            item_rep_by_value[dedupe_key] = column
            duplicate_columns_by_rep[column] = [column]
            metadata: Dict[str, object] = {
                "column": column,
                "cached_d_star": cached_d_star,
                "adf_threshold": adf_threshold,
                "d_range": d_range,
                "precision": precision,
                "max_lag": max_lag,
                "weight_threshold": weight_threshold,
                "sample_size": sample_size,
                "calibration_bars": self._calibration_bars(),
            }
            items.append((col_arr, metadata))

        outputs = ParallelSlowPath(n_jobs).map(items, process_fracdiff_column_values)
        failed_columns: List[str] = []
        for output in outputs:
            column = str(output["column"])
            d_star = float(output["d_star"])
            fracdiff_values = np.asarray(output["fracdiff_values"], dtype=np.float64)
            fracdiff_series = pd.Series(fracdiff_values, index=result.index)
            duplicate_columns = duplicate_columns_by_rep.get(column, [column])
            for target_column in duplicate_columns:
                self._assign_fracdiff_result(result, target_column, fracdiff_series, self.mode)
                self._fracdiff_processed_columns.add(target_column)

                if cache is not None and (
                    not bool(output.get("cache_hit", False)) or target_column != column
                ):
                    target_values = col_input_arrays.get(target_column)
                    if target_values is not None:
                        target_values = self._calibration_values(target_values)
                    cache.set(target_column, d_star, target_values)
            if output.get("status") != "ok":
                failed_columns.extend(duplicate_columns)

        if failed_columns:
            logger.warning(
                "[L6.5] FracDiff joblib fallback d=1.0 for %d columns. Sample: %s",
                len(failed_columns),
                failed_columns[:10],
            )

        logger.info(
            "[L6.5] FracDiff joblib slow path complete: columns=%d n_jobs=%d",
            len(eligible_columns),
            n_jobs,
        )
        return result

    def _apply_fractional_differencing(
        self,
        df: pd.DataFrame,
        source_layer: Optional[str] = None,
    ) -> pd.DataFrame:
        if not HAS_STATSMODELS:
            logger.warning("Fractional differencing skipped: statsmodels unavailable")
            return df

        apply_to = self.fracdiff_config.get("apply_to", "non_stationary")
        selection_df = df
        if apply_to == "non_stationary":
            numeric_columns = [
                column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])
            ]
            target_columns = self._filter_fracdiff_target_columns(
                numeric_columns,
                source_layer=source_layer,
            )
            if not target_columns:
                return df
            selection_df = df.loc[:, target_columns]

        columns = self._select_columns(selection_df, apply_to)
        if apply_to != "non_stationary" and columns:
            columns = self._filter_fracdiff_target_columns(
                columns,
                source_layer=source_layer,
            )
        if not columns:
            return df

        result = df.copy()
        d_range = self.fracdiff_config.get("d_range", [0.0, 1.0])
        adf_threshold = float(self.fracdiff_config.get("adf_threshold", 0.05))
        weight_threshold = float(self.fracdiff_config.get("weight_threshold", 1e-5))
        precision = self._resolve_fracdiff_precision()
        # 限制 weight 寬度：最多序列長度的 10%（上限 252），避免 d≈0.5 時產生大量 NaN
        max_lag = int(self.fracdiff_config.get("max_lag", 0))
        if max_lag <= 0:
            max_lag = min(max(2, len(df) // 10), 252)

        cache_enabled = bool(self.fracdiff_config.get("cache_d_star", True))
        cache: Optional[DStarCache] = None
        shared_cache = False
        if cache_enabled and self._d_star_cache_shared:
            if self._d_star_cache is None:
                self._d_star_cache = self._create_d_star_cache(
                    adf_threshold=adf_threshold,
                    precision=precision,
                    max_lag=max_lag,
                    weight_threshold=weight_threshold,
                )
            cache = self._d_star_cache
            shared_cache = True
        elif cache_enabled:
            cache = self._create_d_star_cache(
                adf_threshold=adf_threshold,
                precision=precision,
                max_lag=max_lag,
                weight_threshold=weight_threshold,
            )

        # Precompute NaN rates once per chunk to avoid per-column scans.
        nan_rates = result.loc[:, columns].isna().mean()
        eligible_columns = [column for column in columns if float(nan_rates.get(column, 1.0)) <= 0.5]
        skipped_high_nan: List[str] = [column for column in columns if column not in eligible_columns]

        if eligible_columns:
            slowpath_n_jobs = self._resolve_slowpath_n_jobs()
            if slowpath_n_jobs > 1 and len(eligible_columns) > 1:
                try:
                    result = self._apply_fractional_differencing_parallel(
                        result,
                        eligible_columns,
                        cache=cache,
                        adf_threshold=adf_threshold,
                        d_range=(float(d_range[0]), float(d_range[1])),
                        precision=precision,
                        max_lag=max_lag,
                        weight_threshold=weight_threshold,
                        n_jobs=slowpath_n_jobs,
                    )
                except MemoryError:
                    logger.error(
                        "[L6.5] joblib slow-path OOM, raise for batch downscale",
                        exc_info=True,
                    )
                    raise
                except Exception as exc:
                    logger.error(
                        "[L6.5] joblib slow path failed, fallback to serial chunked slow path: %s",
                        exc,
                        exc_info=True,
                    )
                    result = self._apply_fractional_differencing_serial(
                        result,
                        eligible_columns,
                        cache=cache,
                        adf_threshold=adf_threshold,
                        d_range=(float(d_range[0]), float(d_range[1])),
                        precision=precision,
                        max_lag=max_lag,
                        weight_threshold=weight_threshold,
                    )
            else:
                result = self._apply_fractional_differencing_serial(
                    result,
                    eligible_columns,
                    cache=cache,
                    adf_threshold=adf_threshold,
                    d_range=(float(d_range[0]), float(d_range[1])),
                    precision=precision,
                    max_lag=max_lag,
                    weight_threshold=weight_threshold,
                )

        if skipped_high_nan:
            logger.warning(
                "FracDiff skipped for %d columns due to too many NaN. Sample: %s",
                len(skipped_high_nan),
                skipped_high_nan[:10],
            )

        if cache_enabled and cache is not None:
            if not shared_cache:
                cache.flush_atomic()
            cache_hits, cache_misses = cache.stats()
            total_lookups = cache_hits + cache_misses
            if total_lookups > 0:
                logger.info(
                    "[L6.5] symbol=%s tf=%s d_star_cache_hit=%d/%d path=%s",
                    self._preprocessing_context.symbol,
                    self._preprocessing_context.timeframe,
                    cache_hits,
                    total_lookups,
                    cache.path,
                )

        return result

    def _apply_adf_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        if not HAS_STATSMODELS:
            logger.warning("ADF differencing skipped: statsmodels unavailable")
            return df

        apply_to = self.adf_config.get("apply_to", "non_stationary")
        columns = self._select_columns(df, apply_to)
        if not columns:
            return df

        result = df.copy()
        threshold = float(self.adf_config.get("adf_threshold", 0.05))
        max_diff = int(self.adf_config.get("max_diff", 2))
        sample_size = int(self.adf_config.get("sample_size", 500))
        candidate_columns = [
            column for column in columns if column not in self._fracdiff_processed_columns
        ]
        # ADF safe-skip：對數學嚴格 I(0) 欄位 bypass ADF（詳見 utils/adf_safe_skip.py）
        candidate_columns = self._apply_adf_safe_skip(candidate_columns, context="adf_diff")
        if not candidate_columns:
            return result

        nan_rates = result.loc[:, candidate_columns].isna().mean()
        eligible_columns = [
            column for column in candidate_columns if float(nan_rates.get(column, 1.0)) <= 0.5
        ]
        skipped_high_nan: List[str] = [
            column for column in candidate_columns if column not in eligible_columns
        ]

        for column in eligible_columns:
            series = result[column].astype(float)

            decision_source = self._calibration_series(series)
            decision_working = decision_source.copy()
            full_working = series.copy()
            chosen_diff = 0
            for diff_order in range(max_diff + 1):
                clean = decision_working.dropna()
                if len(clean) < 20:
                    break
                sample = clean.head(sample_size)
                pvalue = self._adf_pvalue_for_values(sample.to_numpy(dtype=np.float64), sample_size=sample_size)

                if pvalue <= threshold:
                    chosen_diff = diff_order
                    break

                if diff_order < max_diff:
                    decision_working = decision_working.diff()
                    full_working = full_working.diff()

            if chosen_diff == 0:
                continue

            if self.mode == "replace":
                result[column] = full_working
            else:
                result[f"{column}_diff{chosen_diff}"] = full_working

        if skipped_high_nan:
            logger.warning(
                "ADF differencing skipped for %d columns due to too many NaN. Sample: %s",
                len(skipped_high_nan),
                skipped_high_nan[:10],
            )

        return result

    @staticmethod
    def _rolling_rank_2d_v2(arr: np.ndarray, window: int) -> np.ndarray:
        if window <= 0:
            raise ValueError("rank window must be positive")

        selected = pd.DataFrame(np.asarray(arr, dtype=np.float64))
        min_periods = FeaturePreprocessor._rolling_min_periods(window)
        rolling = selected.rolling(window, min_periods=min_periods)
        ranked_df = rolling.rank(method="average", pct=True)
        constant_mask = rolling.std(ddof=0) == 0.0
        ranked_df = ranked_df.mask(constant_mask, 0.5)
        ranked_df = ranked_df.where(~selected.isna(), np.nan)
        return ranked_df.to_numpy(dtype=np.float32, copy=False)

    def _apply_rank_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.rank_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        window = int(self.rank_config.get("window", 252))

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)

        ranked_df = pd.DataFrame(
            self._rolling_rank_2d_v2(
                selected.to_numpy(dtype=np.float64, copy=False),
                window,
            ),
            index=selected.index,
            columns=columns,
        )

        if self.mode == "replace":
            result.loc[:, columns] = ranked_df
        else:
            ranked_df = ranked_df.rename(columns={column: f"{column}_rank" for column in columns})
            result = pd.concat([result, ranked_df], axis=1)

        return result

    def _rolling_last_rank_pct_for_preprocess(self, values: np.ndarray) -> float:
        """Rolling percentile rank for the last value, preserving legacy constant-window behavior."""
        last = values[-1]
        if np.isnan(last):
            return np.nan

        valid_mask = ~np.isnan(values)
        valid_count = int(valid_mask.sum())
        if valid_count == 0:
            return np.nan

        valid_values = values[valid_mask]
        # Keep legacy behavior: constant windows map to 0.5 exactly.
        if np.nanmax(valid_values) == np.nanmin(valid_values):
            return 0.5

        less_count = int(np.sum(valid_values < last))
        equal_count = int(np.sum(valid_values == last))
        average_rank = less_count + (equal_count + 1) / 2.0
        return average_rank / float(valid_count)

    @staticmethod
    def _gaussian_2d(
        arr: np.ndarray,
        lower: float = 0.001,
        upper: float = 0.999,
        *,
        causal: bool = True,
        window: int = 252,
        min_periods: int = 63,
    ) -> np.ndarray:
        if not HAS_SCIPY or ndtri is None:
            raise RuntimeError("scipy is required for gaussian normalization")

        selected = pd.DataFrame(np.asarray(arr, dtype=np.float64))
        if causal:
            ranked_arr = _rolling_rank_numba(
                selected.to_numpy(dtype=np.float64, copy=False),
                int(window),
                int(min_periods),
            )
            ranked_df = pd.DataFrame(ranked_arr, index=selected.index, columns=selected.columns)
        else:
            ranked_df = selected.rank(pct=True)
            nunique = selected.nunique(dropna=True)
            constant_columns = nunique[nunique <= 1].index.tolist()
            if constant_columns:
                constant_values = ranked_df.loc[:, constant_columns].where(
                    selected.loc[:, constant_columns].isna(),
                    0.5,
                )
                ranked_df.loc[:, constant_columns] = constant_values

        clipped = ranked_df.clip(lower=lower, upper=upper)
        gaussian_arr = ndtri(clipped.to_numpy(dtype=np.float64, copy=False))
        gaussian_arr[selected.isna().to_numpy()] = np.nan
        return gaussian_arr.astype(np.float32, copy=False)

    def _apply_gaussian_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        if not HAS_SCIPY:
            logger.warning("Gaussian normalization skipped: scipy unavailable")
            return df

        apply_to = self.gaussian_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        clip_range = self.gaussian_config.get("clip_range", [0.001, 0.999])
        lower = float(clip_range[0])
        upper = float(clip_range[1])

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)
        gaussian_df = pd.DataFrame(
            self._gaussian_2d(
                selected.to_numpy(dtype=np.float64, copy=False),
                lower=lower,
                upper=upper,
                causal=self.causal_preprocessing,
                window=self._rolling_window(),
                min_periods=self._rolling_min_periods(self._rolling_window()),
            ),
            index=selected.index,
            columns=columns,
        )

        if self.mode == "replace":
            result.loc[:, columns] = gaussian_df
        else:
            gaussian_df = gaussian_df.rename(columns={column: f"{column}_gaussian" for column in columns})
            result = pd.concat([result, gaussian_df], axis=1)

        return result

    def _apply_adaptive_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.zscore_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        windows = self.zscore_config.get("windows", [100, 252])
        epsilon = float(self.zscore_config.get("epsilon", 1e-8))

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)

        if self.mode == "replace":
            zscore_values = self._rolling_zscore_2d(
                selected.to_numpy(dtype=np.float64, copy=False),
                [int(window) for window in windows],
                epsilon,
                mode="replace",
            )
            zscore = pd.DataFrame(
                zscore_values,
                index=selected.index,
                columns=columns,
            )
            result.loc[:, columns] = zscore
        else:
            append_frames: List[pd.DataFrame] = []
            zscore_by_window = self._rolling_zscore_2d(
                selected.to_numpy(dtype=np.float64, copy=False),
                [int(window) for window in windows],
                epsilon,
                mode="append",
            )
            for window in windows:
                window_int = int(window)
                if window_int not in zscore_by_window:
                    continue
                zscore = pd.DataFrame(
                    zscore_by_window[window_int],
                    index=selected.index,
                    columns=columns,
                )
                zscore = zscore.rename(columns={column: f"{column}_zscore_{window_int}" for column in columns})
                append_frames.append(zscore)

            if append_frames:
                result = pd.concat([result] + append_frames, axis=1)

        return result

    def _select_columns(self, df: pd.DataFrame, apply_to: Union[str, List[str]]) -> List[str]:
        numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if not numeric_columns:
            return []

        if isinstance(apply_to, list):
            return [col for col in apply_to if col in numeric_columns]

        if apply_to == "all":
            return numeric_columns

        if apply_to == "layer1_only":
            prefixes = ("close_", "open_", "high_", "low_", "volume_", "quote_volume_", "taker_", "ms_", "ent_", "tr_")
            return [col for col in numeric_columns if col.startswith(prefixes)]

        if apply_to == "non_stationary":
            return self._get_non_stationary_columns(df[numeric_columns])

        try:
            pattern = re.compile(str(apply_to))
            return [col for col in numeric_columns if pattern.search(col)]
        except re.error:
            logger.warning("Invalid regex apply_to=%s, fallback to all numeric columns", apply_to)
            return numeric_columns

    def _get_non_stationary_columns(self, df: pd.DataFrame) -> List[str]:
        if not HAS_STATSMODELS:
            return []

        threshold = float(self.adf_config.get("adf_threshold", self.fracdiff_config.get("adf_threshold", 0.05)))
        sample_size = int(self.adf_config.get("sample_size", self.fracdiff_config.get("sample_size", 500)))
        sample_size = max(sample_size, 1)
        nan_policy = "dropna"
        non_stationary: List[str] = []

        for column in df.columns:
            raw_series = df[column]
            decision_series = self._calibration_series(raw_series)
            cache_key = self._non_stationary_cache.make_key(
                str(column),
                threshold,
                sample_size,
                nan_policy,
                decision_series,
                causal_preprocessing=self.causal_preprocessing,
                calibration_bars=self._calibration_bars(),
            )
            cached = self._non_stationary_cache.get(cache_key)
            if cached is not None:
                if cached:
                    non_stationary.append(column)
                continue

            if float(decision_series.isna().mean()) > 0.5:
                self._non_stationary_cache.set(cache_key, False)
                continue

            series = decision_series.dropna()
            if len(series) < 20:
                is_non_stationary = True
                self._non_stationary_cache.set(cache_key, is_non_stationary)
                non_stationary.append(column)
                continue

            pvalue = self._adf_pvalue_for_values(
                series.head(sample_size).to_numpy(dtype=np.float64),
                sample_size=sample_size,
            )

            is_non_stationary = bool(pvalue > threshold)
            self._non_stationary_cache.set(cache_key, is_non_stationary)
            if is_non_stationary:
                non_stationary.append(column)

        return non_stationary

    @staticmethod
    def _get_weights_ffd(d: float, threshold: float = 1e-5, max_width: int = 0) -> np.ndarray:
        """計算 FFD 權重序列。

        max_width > 0 時強制截斷，防止 d ≈ 0.5 時產生幾百個權重（導致同等數量的 NaN）。
        """
        weights = [1.0]
        k = 1
        while True:
            w = -weights[-1] * (d - k + 1) / k
            if abs(w) < threshold:
                break
            if max_width > 0 and len(weights) >= max_width:
                break
            weights.append(w)
            k += 1
        return np.array(weights[::-1], dtype=np.float64)

    @staticmethod
    def _frac_diff_ffd(
        series: pd.Series,
        d: float,
        threshold: float = 1e-5,
        max_width: int = 0,
    ) -> pd.Series:
        """Fixed-Width Window Fractional Differencing。

        只對第一個有效值之後的區間做卷積，初始 NaN 區間（如 EMA warmup）
        保持 NaN，不做 bfill，避免常數區差分後出現假 0 值。
        """
        values = series.astype(float)
        weights = FeaturePreprocessor._get_weights_ffd(d, threshold, max_width=max_width)
        width = len(weights)

        out = np.full(len(values), np.nan, dtype=np.float64)

        # 找第一個有效位置，避免 bfill 把 EMA warmup NaN 填成常數
        arr = values.to_numpy(dtype=np.float64)
        valid_mask = ~np.isnan(arr)
        if valid_mask.sum() < width:
            return pd.Series(out, index=series.index)

        first_valid = int(np.argmax(valid_mask))
        # 只在有效區間內做 ffill（處理中途偶發 NaN）
        valid_slice = pd.Series(arr[first_valid:], dtype=float).ffill().to_numpy(dtype=np.float64)

        if len(valid_slice) < width:
            return pd.Series(out, index=series.index)

        conv = _frac_diff_convolve(valid_slice, weights)
        # 結果起始位置：first_valid + width - 1
        out[first_valid + width - 1 : first_valid + len(valid_slice)] = conv
        return pd.Series(out, index=series.index)

    def _find_min_d(
        self,
        series: pd.Series,
        *,
        adf_threshold: float = 0.05,
        d_range: Tuple[float, float] = (0.0, 1.0),
        precision: Optional[float] = None,
        max_lag: int = 0,
    ) -> float:
        if not HAS_STATSMODELS:
            return 1.0

        decision_series = self._calibration_series(series)
        clean = decision_series.dropna()
        if len(clean) < 20:
            return 1.0

        left, right = float(d_range[0]), float(d_range[1])
        effective_precision = (
            self._resolve_fracdiff_precision() if precision is None else float(precision)
        )
        if effective_precision <= 0.0:
            effective_precision = self._resolve_fracdiff_precision()
        weight_threshold = float(self.fracdiff_config.get("weight_threshold", 1e-5))
        values = clean.to_numpy(dtype=np.float64, copy=False)

        # ── Precompute filled_slice once ─────────────────────────────────────
        # clean = series.dropna() guarantees no NaN in values, so:
        #   - finite_mask is all-True, first_valid = 0
        #   - ffill() is a no-op (nothing to forward-fill)
        # We still handle the rare edge case where inf exists in clean.
        _finite_mask = np.isfinite(values)
        _first_valid = int(np.argmax(_finite_mask)) if _finite_mask.any() else len(values)
        _raw_slice = values[_first_valid:]
        # ffill inf/nan within the slice (no-op when values is all-finite)
        _filled_slice: np.ndarray = (
            pd.Series(_raw_slice, dtype=float).ffill().to_numpy(dtype=np.float64)
            if not np.all(_finite_mask[_first_valid:])
            else _raw_slice
        )
        _n_total = len(values)

        def _fracdiff_values(raw_values: np.ndarray, d_value: float) -> np.ndarray:
            # Use precomputed _filled_slice — avoids repeating dropna/ffill/isnan
            # across bisection iterations (6 calls per column at precision=0.02).
            del raw_values
            weights_arr = FeaturePreprocessor._get_weights_ffd(
                d_value, weight_threshold, max_width=max_lag
            )
            w = len(weights_arr)
            out = np.full(_n_total, np.nan, dtype=np.float64)
            if _filled_slice.size < w:
                return out
            conv = _frac_diff_convolve(_filled_slice, weights_arr)
            out[_first_valid + w - 1 : _first_valid + _filled_slice.size] = conv
            return out

        def _adf_pvalue(fracdiff_values: np.ndarray) -> float:
            clean_values = np.asarray(fracdiff_values, dtype=np.float64)
            clean_values = clean_values[np.isfinite(clean_values)]
            if clean_values.size < 20:
                return 1.0
            return self._adf_pvalue_for_values(clean_values, sample_size=500)

        def _full_search() -> float:
            return find_min_d_full_bisection(
                values,
                precision=effective_precision,
                adf_threshold=adf_threshold,
                adf_fn=_adf_pvalue,
                fracdiff_fn=_fracdiff_values,
                d_range=(left, right),
            )

        return round(
            find_min_d_with_prior(
                values,
                precision=effective_precision,
                adf_threshold=adf_threshold,
                adf_fn=_adf_pvalue,
                fracdiff_fn=_fracdiff_values,
                full_search_fn=_full_search,
                d_range=(left, right),
            ),
            4,
        )
