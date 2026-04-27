from __future__ import annotations

import gc
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Dict, FrozenSet, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.preprocessing._d_star_cache import (
    DStarCache,
    PreprocessingContext,
)
from momentum.FeatureEngineering.preprocessing._non_stationary_cache import NonStationaryCache
from momentum.core.config import MomentumConfig, get_fracdiff_layers, get_fracdiff_precision
from momentum.core.logging import get_logger


if TYPE_CHECKING:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


logger = get_logger(__name__)
_FRACDIFF_LAYER_RE = re.compile(r"^(L\d+)_")


def _is_fracdiff_target_layer(column: str, allowed_layers: FrozenSet[str]) -> bool:
    if "ALL" in allowed_layers:
        return True

    match = _FRACDIFF_LAYER_RE.match(str(column))
    if not match:
        logger.warning(
            "[L6.5] Layer parse failed col=%s, treat as non-target",
            column,
        )
        return False
    return match.group(1) in allowed_layers

try:
    from scipy.special import erfinv

    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False
    erfinv = None
    logger.warning("scipy not available, gaussian normalization disabled")

try:
    from statsmodels.tsa.stattools import adfuller

    HAS_STATSMODELS = True
except Exception:
    HAS_STATSMODELS = False
    adfuller = None
    logger.warning("statsmodels not available, ADF/Fractional Differencing disabled")


class FeaturePreprocessor:
    """Layer 6.5: 特徵前處理與正規化。"""

    def __init__(self, config: Dict, context: Optional[PreprocessingContext] = None) -> None:
        self._config = config or {}
        self._preprocessing_context = context or PreprocessingContext()
        self.rank_config = self._config.get("rank_transform", {})
        self.gaussian_config = self._config.get("gaussian_normalize", {})
        self.adf_config = self._config.get("adf_differencing", {})
        self.zscore_config = self._config.get("adaptive_zscore", {})
        self.winsor_config = self._config.get("winsorization", {})
        self.fracdiff_config = self._config.get("fractional_differencing", {})
        # 預設 replace：確保跨標的欄位名稱一致
        self.mode = self._config.get("mode", "replace")

        self._fracdiff_processed_columns: set[str] = set()
        self._fracdiff_apply_to_layers = get_fracdiff_layers()
        self._non_stationary_cache = NonStationaryCache()
        self._column_chunk_size = self._resolve_column_chunk_size()
        self._d_star_cache: Optional[DStarCache] = None
        self._d_star_cache_shared = False
        self._numba_warmed_up = False

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

        if worker_count <= 1:
            return self._transform_registry_serial(registry, groups, transform_context)

        return self._transform_registry_parallel(
            registry,
            groups,
            transform_context,
            worker_count,
        )

    def _build_registry_transform_context(self) -> Dict[str, object]:
        """Resolve immutable per-run settings for registry-based L6.5 transforms."""

        do_winsorize = self.winsor_config.get("enabled", True)
        do_rank = self.rank_config.get("enabled", False)
        do_zscore = self.zscore_config.get("enabled", False)
        do_fracdiff = self.fracdiff_config.get("enabled", False)
        do_adf = self.adf_config.get("enabled", False)
        do_gaussian = self.gaussian_config.get("enabled", False)

        use_fast = (
            not do_fracdiff
            and not do_adf
            and not do_gaussian
            and self.mode == "replace"
        )

        transform_context: Dict[str, object] = {
            "use_fast": use_fast,
        }

        if use_fast:
            self._warmup_numba_if_needed()

            from momentum.FeatureEngineering.preprocessing._numba_transforms import transform_array_fast

            winsor_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
            zscore_windows = self.zscore_config.get("windows", [100, 252])

            transform_context.update(
                {
                    "transform_array_fast": transform_array_fast,
                    "do_winsorize": do_winsorize,
                    "winsor_lower_q": float(winsor_range[0]),
                    "winsor_upper_q": float(winsor_range[1]),
                    "do_rank": do_rank,
                    "rank_window": int(self.rank_config.get("window", 252)),
                    "do_zscore": do_zscore,
                    "zscore_window": int(zscore_windows[0]) if zscore_windows else 100,
                    "zscore_epsilon": float(self.zscore_config.get("epsilon", 1e-8)),
                }
            )

        return transform_context

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

        logger.info("[L6.5] Serial start: %d groups", total)

        for group in groups:
            gid = getattr(group, "group_id", "<unknown>")
            n_cols = self._group_n_columns(group)
            try:
                # Route oversized slow-path groups through chunked processing
                # to cap peak memory (avoids 3-4× full_array copies for 1.8 GB groups).
                if not use_fast and split_threshold > 0 and n_cols > split_threshold:
                    self._transform_single_group_chunked(registry, group, chunk_size=split_threshold)
                    last_group_label = f"{gid} (slow-chunked)"
                else:
                    self._transform_single_group(registry, group, transform_context)
                    last_group_label = gid
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
                    "rate=%.2f/s, ETA=%.0fs, last=%s",
                    done,
                    total,
                    100.0 * done / max(total, 1),
                    elapsed_so_far,
                    rate,
                    eta if eta != float("inf") else -1,
                    last_group_label,
                )
                last_heartbeat_at = now
                last_heartbeat_done = done

        elapsed = time.perf_counter() - started_at
        logger.info(
            "[L6.5] Serial complete: %d/%d in %.2fs (%d failed)",
            completed,
            len(groups),
            elapsed,
            failed,
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
        use_fast = bool(transform_context.get("use_fast", False))
        can_split = use_fast and split_threshold > 0

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

        for group in ordered_groups:
            n_cols = self._group_n_columns(group)
            if can_split and n_cols > split_threshold:
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
            elif not use_fast and split_threshold > 0 and n_cols > split_threshold:
                # Slow path (FracDiff/ADF/Gaussian) with a large group: process in
                # column chunks sequentially to cap peak memory at ~full_array + chunk_copies
                # instead of full_array × 3–4 copies (which OOM-kills on 8 GB systems).
                slow_chunked_groups.append(group)
            else:
                full_groups.append(group)

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
            "[L6.5] Parallel start: %d full groups + %d big-group splits → %d sub-tasks "
            "(workers=%d, split_threshold=%d, slow_chunked=%d)",
            len(full_groups),
            len(split_meta),
            total_tasks,
            n_workers,
            split_threshold,
            len(slow_chunked_groups),
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
                        "elapsed=%.1fs, rate=%.2f/s, ETA=%.0fs, last=%s",
                        tasks_done,
                        total_tasks,
                        100.0 * tasks_done / max(total_tasks, 1),
                        completed,
                        len(groups),
                        elapsed,
                        rate,
                        eta if eta != float("inf") else -1,
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
                self._transform_single_group_chunked(registry, group, chunk_size=split_threshold)
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
                    "elapsed=%.1fs, rate=%.2f/s, ETA=%.0fs, last=%s",
                    tasks_done,
                    total_tasks,
                    100.0 * tasks_done / max(total_tasks, 1),
                    completed,
                    len(groups),
                    elapsed_so_far,
                    rate,
                    eta if eta != float("inf") else -1,
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
                "(%d failed, %d big-group splits → %d sub-tasks, %d slow-chunked)",
                completed,
                len(groups),
                elapsed,
                n_workers,
                failed,
                split_count,
                total_slices,
                len(slow_chunked_groups),
            )
        else:
            logger.info(
                "[L6.5] Parallel complete: %d/%d groups in %.2fs, %d workers "
                "(%d failed, %d slow-chunked)",
                completed,
                len(groups),
                elapsed,
                n_workers,
                failed,
                len(slow_chunked_groups),
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

                processed_df = self._transform_single(chunk_df)

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
            winsor_lower_q=float(transform_context.get("winsor_lower_q", 0.01)),
            winsor_upper_q=float(transform_context.get("winsor_upper_q", 0.99)),
            rank=bool(transform_context.get("do_rank", False)),
            rank_window=int(transform_context.get("rank_window", 252)),
            zscore=bool(transform_context.get("do_zscore", False)),
            zscore_window=int(transform_context.get("zscore_window", 100)),
            zscore_epsilon=float(transform_context.get("zscore_epsilon", 1e-8)),
        )

    def _transform_single_group(
        self,
        registry: "ColumnGroupRegistry",
        group: object,
        transform_context: Dict[str, object],
    ) -> None:
        """Transform a single registry group in-place."""

        from momentum.FeatureEngineering.core.column_group import ColumnGroup as _CG, LayerSource as _LS

        group_id = getattr(group, "group_id")
        group_array = np.asarray(registry.load_data(group_id), dtype=np.float32)
        use_fast = bool(transform_context.get("use_fast", False))

        if use_fast:
            transform_array_fast = transform_context["transform_array_fast"]
            processed_array = transform_array_fast(
                group_array,
                winsorize=bool(transform_context.get("do_winsorize", True)),
                winsor_lower_q=float(transform_context.get("winsor_lower_q", 0.01)),
                winsor_upper_q=float(transform_context.get("winsor_upper_q", 0.99)),
                rank=bool(transform_context.get("do_rank", False)),
                rank_window=int(transform_context.get("rank_window", 252)),
                zscore=bool(transform_context.get("do_zscore", False)),
                zscore_window=int(transform_context.get("zscore_window", 100)),
                zscore_epsilon=float(transform_context.get("zscore_epsilon", 1e-8)),
            )
            registry.overwrite_data(group_id, processed_array)
            return

        is_append = self.mode == "append"
        group_df = pd.DataFrame(group_array, columns=list(getattr(group, "columns")), copy=False)
        processed_df = self._transform_single(group_df)

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

    def _transform_single(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Original transform logic applied to a full DataFrame."""
        transformed = features_df.copy()
        self._fracdiff_processed_columns = set()

        transformed = self._apply_winsorization(transformed)

        if self.fracdiff_config.get("enabled", False):
            transformed = self._apply_fractional_differencing(transformed)

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
            lowers = selected.quantile(lower_q)
            uppers = selected.quantile(upper_q)
            clipped = selected.clip(lower=lowers, upper=uppers, axis=1)
            clipped = clipped.astype(np.float32, copy=False)
            result.loc[:, columns] = clipped.loc[:, columns]
        else:
            raise ValueError(f"Unsupported winsorization method: {method}")

        return result

    def _resolve_fracdiff_precision(self) -> float:
        return get_fracdiff_precision(self.fracdiff_config.get("precision", 0.02))

    def _filter_fracdiff_target_columns(self, columns: List[str]) -> List[str]:
        return [
            column
            for column in columns
            if _is_fracdiff_target_layer(column, self._fracdiff_apply_to_layers)
        ]

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
        )

    def _apply_fractional_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        if not HAS_STATSMODELS:
            logger.warning("Fractional differencing skipped: statsmodels unavailable")
            return df

        apply_to = self.fracdiff_config.get("apply_to", "non_stationary")
        selection_df = df
        if apply_to == "non_stationary":
            numeric_columns = [
                column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])
            ]
            target_columns = self._filter_fracdiff_target_columns(numeric_columns)
            if not target_columns:
                return df
            selection_df = df.loc[:, target_columns]

        columns = self._select_columns(selection_df, apply_to)
        if apply_to != "non_stationary" and columns:
            columns = self._filter_fracdiff_target_columns(columns)
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

        for column in eligible_columns:
            series = result[column].astype(float)

            try:
                cached_d_star = cache.get(column) if cache is not None else None
                if cached_d_star is not None:
                    d_star = cached_d_star
                else:
                    d_star = self._find_min_d(
                        series,
                        adf_threshold=adf_threshold,
                        d_range=(float(d_range[0]), float(d_range[1])),
                        precision=precision,
                        max_lag=max_lag,
                    )
                    if cache is not None:
                        cache.set(column, d_star)
            except Exception as exc:
                logger.warning("FracDiff d* search failed for %s: %s; fallback to d=1.0", column, exc)
                d_star = 1.0

            frac = self._frac_diff_ffd(series, d_star, threshold=weight_threshold, max_width=max_lag)

            if self.mode == "replace":
                result[column] = frac
            else:
                result[f"{column}_fracdiff"] = frac

            self._fracdiff_processed_columns.add(column)

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

            working = series.copy()
            chosen_diff = 0
            for diff_order in range(max_diff + 1):
                clean = working.dropna()
                if len(clean) < 20:
                    break
                sample = clean.tail(sample_size)
                try:
                    pvalue = adfuller(sample, autolag="AIC")[1]
                except Exception:
                    pvalue = 1.0

                if pvalue <= threshold:
                    chosen_diff = diff_order
                    break

                if diff_order < max_diff:
                    working = working.diff()

            if chosen_diff == 0:
                continue

            if self.mode == "replace":
                result[column] = working
            else:
                result[f"{column}_diff{chosen_diff}"] = working

        if skipped_high_nan:
            logger.warning(
                "ADF differencing skipped for %d columns due to too many NaN. Sample: %s",
                len(skipped_high_nan),
                skipped_high_nan[:10],
            )

        return result

    def _apply_rank_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.rank_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        window = int(self.rank_config.get("window", 252))

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)

        # Use pandas' vectorized rolling.rank fast path and patch constant windows
        # to keep legacy behavior exactly (constant window -> 0.5).
        rolling = selected.rolling(window, min_periods=1)
        ranked_df = rolling.rank(
            method="average",
            pct=True,
        )
        rolling_max = rolling.max()
        rolling_min = rolling.min()
        # all-NaN windows naturally produce False here (NaN == NaN is False).
        constant_mask = rolling_max == rolling_min
        ranked_df = ranked_df.mask(constant_mask, 0.5)
        ranked_df = ranked_df.where(~selected.isna(), np.nan)
        ranked_df = ranked_df.astype(np.float32, copy=False)

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
        new_columns: Dict[str, pd.Series] = {}
        for column in columns:
            series = result[column].astype(float)
            if series.nunique(dropna=True) <= 1:
                ranked = pd.Series(0.5, index=series.index)
            else:
                ranked = series.rank(pct=True)
            clipped = ranked.clip(lower=lower, upper=upper)
            gaussian = np.sqrt(2.0) * erfinv(2.0 * clipped - 1.0)
            gaussian_series = pd.Series(gaussian, index=series.index)
            if self.mode == "replace":
                result[column] = gaussian_series.astype(np.float32, copy=False)
            else:
                new_columns[f"{column}_gaussian"] = gaussian_series

        if self.mode != "replace" and new_columns:
            result = pd.concat([result, pd.DataFrame(new_columns, index=result.index)], axis=1)

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
        primary_window = int(windows[0]) if windows else 100

        if self.mode == "replace":
            mean = selected.rolling(primary_window, min_periods=1).mean()
            std = selected.rolling(primary_window, min_periods=1).std()
            zscore = (selected - mean) / (std + epsilon)
            zscore = zscore.where(std > 0.0, 0.0)
            zscore = zscore.where(~selected.isna(), np.nan)
            zscore = zscore.astype(np.float32, copy=False)
            result.loc[:, columns] = zscore
        else:
            append_frames: List[pd.DataFrame] = []
            for window in windows:
                window_int = int(window)
                mean = selected.rolling(window_int, min_periods=1).mean()
                std = selected.rolling(window_int, min_periods=1).std()
                zscore = (selected - mean) / (std + epsilon)
                zscore = zscore.where(std > 0.0, 0.0)
                zscore = zscore.where(~selected.isna(), np.nan)
                zscore = zscore.astype(np.float32, copy=False)
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
            cache_key = self._non_stationary_cache.make_key(
                str(column),
                threshold,
                sample_size,
                nan_policy,
                raw_series,
            )
            cached = self._non_stationary_cache.get(cache_key)
            if cached is not None:
                if cached:
                    non_stationary.append(column)
                continue

            if float(raw_series.isna().mean()) > 0.5:
                self._non_stationary_cache.set(cache_key, False)
                continue

            series = raw_series.dropna()
            if len(series) < 20:
                is_non_stationary = True
                self._non_stationary_cache.set(cache_key, is_non_stationary)
                non_stationary.append(column)
                continue

            try:
                pvalue = adfuller(series.tail(sample_size), autolag="AIC")[1]
            except Exception:
                pvalue = 1.0

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

        conv = np.convolve(valid_slice, weights, mode="valid")
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

        clean = series.dropna()
        if len(clean) < 20:
            return 1.0

        left, right = float(d_range[0]), float(d_range[1])
        best = right
        effective_precision = (
            self._resolve_fracdiff_precision() if precision is None else float(precision)
        )
        if effective_precision <= 0.0:
            effective_precision = self._resolve_fracdiff_precision()

        def _is_stationary(d_value: float) -> bool:
            frac = self._frac_diff_ffd(
                clean,
                d_value,
                threshold=float(self.fracdiff_config.get("weight_threshold", 1e-5)),
                max_width=max_lag,
            )
            frac_clean = frac.dropna()
            if len(frac_clean) < 20:
                return False
            pvalue = adfuller(frac_clean.tail(500), autolag="AIC")[1]
            return bool(pvalue <= adf_threshold)

        while right - left > effective_precision:
            mid = (left + right) / 2.0
            try:
                stationary = _is_stationary(mid)
            except Exception:
                stationary = False

            if stationary:
                best = mid
                right = mid
            else:
                left = mid

        return round(best, 4)
