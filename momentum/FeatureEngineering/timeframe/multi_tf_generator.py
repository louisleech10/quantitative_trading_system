"""Multi-timeframe feature generation."""

from __future__ import annotations

import gc
import os
import shutil
import time
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.timeframe.tf_aligner import CURRENT_MTF_ALIGN_VERSION, TimeframeAligner


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
        persist: bool = True,
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
                start_date=start_date, end_date=end_date, persist=persist,
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
        persist: bool = True,
    ) -> "FeatureGenerationResult":
        """CGSA multi-TF: compute layers per TF, align registry groups, then L6.5 + L7."""
        from momentum.FeatureEngineering.feature_config import AlignmentMode

        # Task 1.5: parallel mode dispatches non-primary TFs to spawned workers
        if self._multi_tf_parallel_enabled() and len(self._training_tfs) > 1:
            return self._generate_multi_tf_cgsa_parallel(
                symbol, primary_raw, primary_timestamps, start_time,
                start_date=start_date, end_date=end_date, persist=persist,
            )

        registry = self._factory._cgsa_registry
        skipped_tfs: List[str] = []
        tf_layer_counts: Dict[str, Dict[str, int]] = {}
        stage_seconds: Dict[str, float] = {
            "dual_tf_l1_l6": 0.0,
            "alignment": 0.0,
            "l65_l7": 0.0,
        }
        total_tfs = len(self._training_tfs)
        from momentum.FeatureEngineering.core.column_group import LayerSource as _LS
        _RESUME_LAYERS = (_LS.L1, _LS.L2, _LS.L3, _LS.L4, _LS.L5, _LS.L6)

        for index, timeframe in enumerate(self._training_tfs):
            self._report_progress(
                "multi_tf",
                ((index + 1) / max(total_tfs, 1)) * 0.7,
                f"[CGSA] Processing timeframe {timeframe} ({index + 1}/{total_tfs})",
            )

            if registry.has_layers_for_timeframe(timeframe, _RESUME_LAYERS):
                if timeframe != self._primary_tf and not self._tf_alignment_version_current(
                    registry, timeframe, _RESUME_LAYERS
                ):
                    logger.warning(
                        "[CGSA:resume] TF %s has stale/missing align_algo_version; rebuilding.",
                        timeframe,
                    )
                    self._drop_timeframe_groups_from_registry(registry, timeframe, _RESUME_LAYERS)
                else:
                    logger.info(
                        "[CGSA:resume] TF %s already has L1-L6 in manifest; skipping.",
                        timeframe,
                    )
                    tf_layer_counts[timeframe] = self._collect_layer_counts_from_registry(registry, timeframe)
                    continue

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

            # Set current timeframe so CGSA group IDs use the correct TF prefix.
            self._factory._current_timeframe = timeframe

            l1_l6_start = time.perf_counter()
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

            # Persist L3/L4/L5/L6 to CGSA registry (L1/L2 are persisted inside their layer methods).
            if layer3 is not None and not layer3.empty:
                self._factory._persist_layer_output_groups(layer3, _LS.L3, "L3_rolling")
            if layer4 is not None and not layer4.empty:
                self._factory._persist_layer_output_groups(layer4, _LS.L4, "L4_lag")
            if layer5 is not None and not layer5.empty:
                self._factory._persist_layer_output_groups(layer5, _LS.L5, "L5_cross")
            if layer6 is not None and not layer6.empty:
                self._factory._persist_layer_output_groups(layer6, _LS.L6, "L6_meta")

            stage_seconds["dual_tf_l1_l6"] += time.perf_counter() - l1_l6_start

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
                align_start = time.perf_counter()
                source_index, _ = TimeframeAligner._split_timestamp_index(raw_data)
                source_dt = TimeframeAligner._to_datetime_index(source_index)

                alignment_mode = self._config.timeframes.alignment_mode
                source_dur_ns, primary_dur_ns, mode = self._alignment_params_or_raise(timeframe)
                self._log_gap_source_if_any(timeframe, source_dt, source_dur_ns)

                source_s = TimeframeAligner._datetime_index_to_epoch_seconds(source_dt)
                primary_s = TimeframeAligner._datetime_index_to_epoch_seconds(primary_timestamps)
                idx_map = TimeframeAligner.build_asof_index_map(
                    primary_s,
                    source_s,
                    source_dur_ns=source_dur_ns,
                    primary_dur_ns=primary_dur_ns,
                    mode=mode,
                )

                n_primary = len(primary_timestamps)
                if self._compact_alignment_enabled():
                    idx_map_path = self._persist_alignment_idx_map(
                        registry.work_dir,
                        source_tf=timeframe,
                        primary_tf=self._primary_tf,
                        alignment_mode=str(getattr(alignment_mode, "value", alignment_mode)),
                        idx_map=idx_map,
                    )
                    compact_count = self._mark_existing_groups_compact_aligned(
                        registry=registry,
                        group_ids=new_group_ids,
                        source_tf=timeframe,
                        n_source=len(source_dt),
                        n_primary=n_primary,
                        idx_map_path=idx_map_path,
                        alignment_mode=str(getattr(alignment_mode, "value", alignment_mode)),
                        source_dur_ns=source_dur_ns,
                        primary_dur_ns=primary_dur_ns,
                        mode=mode,
                    )
                    logger.info(
                        "[CGSA][multi_tf] Compact-aligned %d groups from %s → %s "
                        "(source_rows=%d logical_rows=%d)",
                        compact_count,
                        timeframe,
                        self._primary_tf,
                        len(source_dt),
                        n_primary,
                    )
                else:
                    aligned_count = 0
                    for gid in new_group_ids:
                        src_data = np.asarray(registry.load_data(gid), dtype=np.float32)
                        aligned_arr = self._align_group_array(src_data, idx_map, n_primary)
                        registry.overwrite_data(gid, aligned_arr)
                        aligned_count += 1

                    logger.info(
                        "[CGSA][multi_tf] Aligned %d groups from %s → %s (idx_map built once)",
                        aligned_count, timeframe, self._primary_tf,
                    )
                stage_seconds["alignment"] += time.perf_counter() - align_start

        if self._primary_tf in skipped_tfs:
            raise ValueError(f"Primary timeframe data missing for {symbol}/{self._primary_tf}")

        # Restore current timeframe to primary for downstream L6.5/L7.
        self._factory._current_timeframe = self._primary_tf

        total_groups = len(list(registry.iter_all()))
        if total_groups == 0:
            raise ValueError(f"All training timeframes skipped for {symbol}")

        logger.info("[CGSA][multi_tf] All TFs done: %d total groups in registry", total_groups)

        # L6.5 + L7_raw via registry streaming. This avoids full .npy overwrite
        # before parquet persist and keeps IC Gatekeeper/post transforms downstream.
        self._report_progress("persist", 0.9, "[CGSA] Running Layer 6.5 → L7_raw streaming persist")
        config_hash = self._factory._compute_config_hash(
            self._config, symbol, self._primary_tf,
            start_date=start_date, end_date=end_date,
        )
        pre_l7_elapsed = time.time() - start_time
        l65_l7_start = time.perf_counter()
        result = self._factory._layer7_raw_from_cgsa_pipeline(
            symbol=symbol,
            timeframe=self._primary_tf,
            raw_data=primary_raw,
            config=self._config,
            elapsed=pre_l7_elapsed,
            config_hash=config_hash,
            persist=persist,
        )
        stage_seconds["l65_l7"] = time.perf_counter() - l65_l7_start
        total_elapsed = time.time() - start_time
        result.generation_time = total_elapsed
        result.metadata["generation_time"] = total_elapsed
        for key, value in stage_seconds.items():
            stage_seconds[key] = round(float(value), 3)
        result.metadata["multi_tf_stage_seconds"] = stage_seconds
        result.metadata["multi_tf_stage_timing_complete"] = True

        total_layer_counts = self._apply_total_layer_counts_to_result(result, tf_layer_counts)
        result.metadata["skipped_timeframes"] = skipped_tfs
        result.metadata["actual_timeframes"] = [
            tf for tf in self._training_tfs if tf not in skipped_tfs
        ]

        self._report_progress("complete", 1.0, f"[CGSA] MultiTF generation completed ({total_elapsed:.2f}s)")
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
    # CGSA parallel path (Task 1.5, SPEC §3.5)
    # ------------------------------------------------------------------
    def _generate_multi_tf_cgsa_parallel(
        self,
        symbol: str,
        primary_raw: pd.DataFrame,
        primary_timestamps: pd.DatetimeIndex,
        start_time: float,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        persist: bool = True,
    ) -> "FeatureGenerationResult":
        """CGSA multi-TF with ProcessPoolExecutor + spawn for non-primary TFs."""
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed

        from momentum.FeatureEngineering.feature_factory import _warmup_numba_functions
        from momentum.FeatureEngineering.core.column_group import LayerSource as _LS

        registry = self._factory._cgsa_registry
        skipped_tfs: List[str] = []
        tf_layer_counts: Dict[str, Dict[str, int]] = {}
        # dual_tf_l1_l6: worker L1-L6 runs in child processes; parent cannot
        # measure it (future.result() wait ≈ 0). Leave None — not 0.
        stage_seconds: Dict[str, Optional[float]] = {
            "dual_tf_l1_l6": None,
            "alignment": 0.0,
            "l65_l7": 0.0,
        }

        # ── Resume support ────────────────────────────────────────────────
        # When `_prepare_cgsa_registry` resumed an existing manifest, the
        # registry already contains some L1-L6 groups. Re-running the layer
        # methods would call `save_data` and raise "Duplicate group_id"
        # (or quietly create `_2`-suffixed siblings via `_next_available_group_id`).
        # Skip any TF whose L1-L6 set is already present.
        _RESUME_LAYERS = (_LS.L1, _LS.L2, _LS.L3, _LS.L4, _LS.L5, _LS.L6)
        primary_already_done = registry.has_layers_for_timeframe(
            self._primary_tf, _RESUME_LAYERS
        )

        # Step 1: Process primary TF in main process (needs registry + factory state)
        if primary_already_done:
            logger.info(
                "[CGSA-parallel:resume] Primary TF %s already has L1-L6 in manifest; skipping.",
                self._primary_tf,
            )
            self._report_progress(
                "multi_tf", 0.25,
                f"[CGSA-parallel:resume] Skipping primary TF {self._primary_tf} (already done)",
            )
            self._factory._current_timeframe = self._primary_tf
            tf_layer_counts[self._primary_tf] = self._collect_layer_counts_from_registry(
                registry, self._primary_tf
            )
        else:
            self._report_progress(
                "multi_tf", 0.1,
                f"[CGSA-parallel] Processing primary TF {self._primary_tf}",
            )
            self._factory._current_timeframe = self._primary_tf

            try:
                layer1 = self._factory._layer1_atomic_indicators(primary_raw, self._config)
                layer2 = self._factory._layer2_derived_features(layer1, primary_raw, self._config)
                layer3 = self._factory._layer3_rolling_aggregation(layer1, layer2, self._config)
                layer4 = self._factory._layer4_lag_features(layer1, layer2, layer3, primary_raw, self._config)
                layer5 = self._factory._layer5_cross_sectional(layer1, layer2, self._config)
                layer6 = self._factory._layer6_meta_features(layer1, layer2, primary_raw, self._config)
            except Exception as exc:
                logger.error("Primary TF pipeline failed: %s", exc, exc_info=True)
                raise

            for layer_df, layer_src, label in [
                (layer3, _LS.L3, "L3_rolling"), (layer4, _LS.L4, "L4_lag"),
                (layer5, _LS.L5, "L5_cross"), (layer6, _LS.L6, "L6_meta"),
            ]:
                if layer_df is not None and not layer_df.empty:
                    self._factory._persist_layer_output_groups(layer_df, layer_src, label)

            # CGSA can spill intermediate DataFrames after their groups are
            # persisted. The registry is the L7 source of truth, so primary
            # counts must come from the manifest-backed registry rather than
            # from possibly-empty in-memory frames.
            tf_layer_counts[self._primary_tf] = self._collect_layer_counts_from_registry(
                registry, self._primary_tf
            )
            del layer1, layer2, layer3, layer4, layer5, layer6
            gc.collect()

            # Persist primary TF progress immediately so a crash before workers
            # finish still leaves a resumable manifest.
            try:
                registry.write_manifest()
            except Exception as exc:
                logger.warning("[CGSA-parallel:resume] manifest flush after primary TF failed: %s", exc)

        logger.info("[CGSA-parallel] Primary TF %s done, %d groups", self._primary_tf, len(list(registry.iter_all())))

        # Step 2: Process non-primary TFs in parallel via ProcessPoolExecutor + spawn
        # Resume support: filter out TFs whose L1-L6 groups are already in the manifest.
        all_non_primary = [tf for tf in self._training_tfs if tf != self._primary_tf]
        non_primary_tfs: List[str] = []
        for _tf in all_non_primary:
            if registry.has_layers_for_timeframe(_tf, _RESUME_LAYERS):
                if not self._tf_alignment_version_current(registry, _tf, _RESUME_LAYERS):
                    logger.warning(
                        "[CGSA-parallel:resume] TF %s has stale/missing align_algo_version; rebuilding.",
                        _tf,
                    )
                    self._drop_timeframe_groups_from_registry(registry, _tf, _RESUME_LAYERS)
                    non_primary_tfs.append(_tf)
                    continue
                logger.info(
                    "[CGSA-parallel:resume] TF %s already has L1-L6 in manifest; skipping worker spawn.",
                    _tf,
                )
                tf_layer_counts[_tf] = self._collect_layer_counts_from_registry(registry, _tf)
            else:
                non_primary_tfs.append(_tf)

        if non_primary_tfs:
            _warmup_numba_functions()
            config_payload = self._config.model_dump(by_alias=True)
            ctx = mp.get_context("spawn")
            # FFACT_MULTI_TF_MAX_WORKERS caps worker count.
            # Set to a number to override; "auto" or unset → tier-based auto-detection.
            # Tier defaults: 8 GB=2, 16 GB=3, 24/32 GB=4.
            _env_raw = os.getenv("FFACT_MULTI_TF_MAX_WORKERS", "auto").strip().lower()
            if _env_raw in {"", "auto"}:
                from momentum.FeatureEngineering.utils.hardware_utils import (
                    get_memory_tier,
                    get_tier_config,
                )
                _env_max = get_tier_config(get_memory_tier())["multi_tf_max_workers"]
            else:
                try:
                    _env_max = max(1, int(_env_raw))
                except ValueError:
                    _env_max = 2
            max_workers = min(len(non_primary_tfs), _env_max)

            self._report_progress("multi_tf", 0.3, f"[CGSA-parallel] Spawning {len(non_primary_tfs)} TF workers (max_workers={max_workers})")

            # Bug #1 fix: extract cache_dir from the factory's storage adapter so
            # worker subprocesses use the same kline cache (not the default path).
            _worker_cache_dir: Optional[str] = None
            for _adapter in self._factory._adapter_registry._adapters.values():
                _storage = getattr(_adapter, "_storage", None)
                if _storage is not None and hasattr(_storage, "cache_dir"):
                    _worker_cache_dir = str(_storage.cache_dir)
                    break

            # OOM Fix: drop primary-TF in-memory buffers before spawning so
            # the parent process gives RAM headroom back to workers.
            gc.collect()

            with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as pool:
                futures = {
                    pool.submit(
                        _tf_worker_entry,
                        symbol,
                        tf,
                        config_payload,
                        start_date,
                        end_date,
                        _worker_cache_dir,
                    ): tf
                    for tf in non_primary_tfs
                }
                for future in as_completed(futures):
                    tf = futures[future]
                    try:
                        result = future.result(timeout=None)  # No timeout; worker may use Python fallback (slow)
                    except Exception as exc:
                        logger.error("TF worker %s failed: %s", tf, exc, exc_info=True)
                        skipped_tfs.append(tf)
                        continue

                    if "error" in result:
                        logger.warning("TF worker %s returned error: %s", tf, result["error"])
                        skipped_tfs.append(tf)
                        continue

                    # Register groups from worker into main registry.
                    # OOM Fix: result now carries only metadata + npy paths,
                    # so the pickle payload is KB rather than GB.
                    tf_layer_counts[tf] = result.get("layer_counts", {})
                    groups_data = result.get("groups", [])
                    source_ts_ms = result.get("source_timestamps_ms")
                    align_start = time.perf_counter()
                    self._register_worker_groups(
                        registry, groups_data, tf,
                        primary_timestamps, self._config.timeframes.alignment_mode,
                        source_timestamps_ms=source_ts_ms,
                    )
                    stage_seconds["alignment"] += time.perf_counter() - align_start
                    # Resume support: persist worker progress to manifest now,
                    # so a SIGKILL during the next worker / L6.5 leaves a
                    # resumable state. `register()` only updates in-memory
                    # registry; manifest must be flushed explicitly.
                    try:
                        registry.write_manifest()
                    except Exception as exc:
                        logger.warning(
                            "[CGSA-parallel:resume] manifest flush after TF %s failed: %s",
                            tf, exc,
                        )
                    # Drop the worker payload immediately so accumulated
                    # paths/columns lists do not grow unchecked.
                    del result, groups_data, source_ts_ms
                    gc.collect()

        self._report_progress("multi_tf", 0.7, "[CGSA-parallel] All TFs done")

        # Restore current timeframe to primary for downstream L6.5/L7.
        self._factory._current_timeframe = self._primary_tf

        total_groups = len(list(registry.iter_all()))
        if total_groups == 0:
            raise ValueError(f"All training timeframes skipped for {symbol}")

        logger.info("[CGSA-parallel] All TFs done: %d total groups in registry", total_groups)

        # L6.5 + L7_raw via registry streaming. IC Gatekeeper and selected
        # post-transforms remain downstream of generation.
        self._report_progress("persist", 0.9, "[CGSA-parallel] Running Layer 6.5 → L7_raw streaming persist")
        config_hash = self._factory._compute_config_hash(
            self._config, symbol, self._primary_tf,
            start_date=start_date, end_date=end_date,
        )
        pre_l7_elapsed = time.time() - start_time
        l65_l7_start = time.perf_counter()
        result = self._factory._layer7_raw_from_cgsa_pipeline(
            symbol=symbol,
            timeframe=self._primary_tf,
            raw_data=primary_raw,
            config=self._config,
            elapsed=pre_l7_elapsed,
            config_hash=config_hash,
            persist=persist,
        )
        stage_seconds["l65_l7"] = time.perf_counter() - l65_l7_start
        total_elapsed = time.time() - start_time
        result.generation_time = total_elapsed
        result.metadata["generation_time"] = total_elapsed
        for key, value in stage_seconds.items():
            if value is not None:
                stage_seconds[key] = round(float(value), 3)
        result.metadata["multi_tf_stage_seconds"] = stage_seconds
        result.metadata["multi_tf_stage_timing_complete"] = False

        total_layer_counts = self._apply_total_layer_counts_to_result(result, tf_layer_counts)
        result.metadata["skipped_timeframes"] = skipped_tfs
        result.metadata["actual_timeframes"] = [
            tf for tf in self._training_tfs if tf not in skipped_tfs
        ]

        self._report_progress("complete", 1.0, f"[CGSA-parallel] MultiTF completed ({total_elapsed:.2f}s)")
        return result

    def _register_worker_groups(
        self,
        registry: object,
        groups_data: List[Dict],
        source_tf: str,
        primary_timestamps: pd.DatetimeIndex,
        alignment_mode: object,
        source_timestamps_ms: Optional[np.ndarray] = None,
    ) -> None:
        """Register and align groups from a parallel TF worker into the main registry."""
        from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
        from momentum.FeatureEngineering.feature_config import AlignmentMode

        n_primary = len(primary_timestamps)
        primary_s = TimeframeAligner._datetime_index_to_epoch_seconds(primary_timestamps)

        # Build alignment index map from source → primary timestamps
        idx_map: Optional[np.ndarray] = None
        source_dur_ns = 0
        primary_dur_ns = 0
        mode = TimeframeAligner._normalize_decision_mode(alignment_mode)
        if source_timestamps_ms is not None:
            source_dur_ns, primary_dur_ns, mode = self._alignment_params_or_raise(source_tf, alignment_mode)
            source_s = self._coerce_worker_timestamps_to_epoch_seconds(source_timestamps_ms)
            idx_map = TimeframeAligner.build_asof_index_map(
                primary_s,
                source_s,
                source_dur_ns=source_dur_ns,
                primary_dur_ns=primary_dur_ns,
                mode=mode,
            )

        compact_alignment = self._compact_alignment_enabled() and idx_map is not None
        idx_map_path: Optional[Path] = None
        if compact_alignment:
            idx_map_path = self._persist_alignment_idx_map(
                registry.work_dir,
                source_tf=source_tf,
                primary_tf=self._primary_tf,
                alignment_mode=str(getattr(alignment_mode, "value", alignment_mode)),
                idx_map=idx_map,
            )

        aligned_count = 0
        worker_dirs_to_cleanup: set[Path] = set()
        freed_worker_bytes = 0
        # Debug knob: keep worker .npy + workdir intact for post-mortem inspection
        # or to resume from worker results. Default OFF so production runs reclaim
        # the multi-GiB scratch space promptly.
        keep_worker_npy = self._keep_worker_npy_enabled()
        for gd in groups_data:
            columns = tuple(gd["columns"])
            n_cols = len(columns)
            if compact_alignment and idx_map_path is not None:
                freed_bytes, moved_dirs = self._register_worker_group_compact(
                    registry=registry,
                    group_data=gd,
                    source_tf=source_tf,
                    n_primary=n_primary,
                    idx_map_path=idx_map_path,
                    alignment_mode=str(getattr(alignment_mode, "value", alignment_mode)),
                    source_dur_ns=source_dur_ns,
                    primary_dur_ns=primary_dur_ns,
                    mode=mode,
                    keep_worker_npy=keep_worker_npy,
                )
                freed_worker_bytes += freed_bytes
                worker_dirs_to_cleanup.update(moved_dirs)
                aligned_count += 1
                continue

            # OOM Fix: mmap-read the worker's .npy instead of receiving a
            # full ndarray over pickle. Backwards compatible: if a worker
            # returned the legacy "data" payload, fall back to it.
            src_data, source_paths = self._load_worker_group_source_array(gd)

            npy_path = registry.work_dir / f"{gd['group_id']}.npy"

            if idx_map is None and src_data.shape[0] != n_primary:
                logger.warning(
                    "No source timestamps for group %s; filling NaN", gd["group_id"],
                )
                source_for_save = None
            else:
                source_for_save = src_data

            try:
                self._persist_aligned_group_to_npy(
                    source_for_save,
                    npy_path,
                    n_primary=n_primary,
                    n_cols=n_cols,
                    idx_map=idx_map,
                    group_id=gd["group_id"],
                )
            finally:
                # Release mmap view before unlinking worker-side files.
                del src_data
                source_for_save = None

            group = ColumnGroup(
                group_id=gd["group_id"],
                layer=LayerSource(gd["layer"]),
                timeframe=gd["timeframe"],
                data_source=gd["data_source"],
                indicator=gd["indicator"],
                columns=columns,
                shape=(n_primary, n_cols),
                dtype="float32",
                disk_path=npy_path,
            )
            try:
                registry.register(group)
            except Exception:
                if npy_path.exists():
                    npy_path.unlink()
                raise

            if source_paths and not keep_worker_npy:
                # Skip cleanup when KEEP_WORKER_NPY is enabled so the worker
                # .npy + workdir remain intact for debugging / resume scenarios.
                for source_path in source_paths:
                    try:
                        source_resolved = source_path.resolve()
                        target_resolved = npy_path.resolve()
                        if source_resolved != target_resolved and source_path.exists():
                            file_size = source_path.stat().st_size
                            source_path.unlink()
                            freed_worker_bytes += file_size
                            worker_dirs_to_cleanup.add(source_path.parent)
                    except OSError as exc:
                        logger.warning(
                            "Failed to delete worker npy after registering %s: %s",
                            gd["group_id"],
                            exc,
                        )
            aligned_count += 1

        if not keep_worker_npy:
            self._cleanup_worker_dirs(worker_dirs_to_cleanup, registry.work_dir)
        elif worker_dirs_to_cleanup:
            logger.info(
                "[CGSA-parallel] FFACT_MULTI_TF_KEEP_WORKER_NPY=1 "
                "keeping %d worker workdirs for debug",
                len(worker_dirs_to_cleanup),
            )

        # Reclaim memory after processing a worker's full payload.
        gc.collect()
        logger.info(
            "[CGSA-parallel] Registered %d groups from worker TF %s (compact=%s, freed worker npy %.2f GiB)",
            aligned_count, source_tf, compact_alignment, freed_worker_bytes / (1024 ** 3),
        )

    def _mark_existing_groups_compact_aligned(
        self,
        *,
        registry: object,
        group_ids: List[str],
        source_tf: str,
        n_source: int,
        n_primary: int,
        idx_map_path: Path,
        alignment_mode: str,
        source_dur_ns: int,
        primary_dur_ns: int,
        mode: str,
    ) -> int:
        """Convert already-persisted non-primary groups to compact logical alignment."""
        from momentum.FeatureEngineering.core.column_group import AlignmentMeta

        compact_count = 0
        for group_id in group_ids:
            group = registry.get(group_id)
            alignment = AlignmentMeta(
                source_timeframe=source_tf,
                primary_timeframe=self._primary_tf,
                source_n_rows=int(n_source),
                primary_n_rows=int(n_primary),
                idx_map_path=idx_map_path,
                alignment_mode=str(alignment_mode),
                offset_ns=0,
                source_dur_ns=int(source_dur_ns),
                primary_dur_ns=int(primary_dur_ns),
                mode=str(mode),
                align_algo_version=CURRENT_MTF_ALIGN_VERSION,
            )
            registry._groups[group_id] = replace(
                group,
                shape=(int(n_primary), int(group.n_cols)),
                alignment=alignment,
            )
            compact_count += 1
        try:
            registry.write_manifest()
        except Exception as exc:
            logger.warning("[CGSA][multi_tf] manifest flush after compact alignment failed: %s", exc)
        return compact_count

    def _register_worker_group_compact(
        self,
        *,
        registry: object,
        group_data: Dict,
        source_tf: str,
        n_primary: int,
        idx_map_path: Path,
        alignment_mode: str,
        source_dur_ns: int,
        primary_dur_ns: int,
        mode: str,
        keep_worker_npy: bool,
    ) -> Tuple[int, set[Path]]:
        """Register a worker group using physical source rows + logical idx_map."""
        from momentum.FeatureEngineering.core.column_group import AlignmentMeta, ColumnGroup, LayerSource, ShardMeta

        columns = tuple(group_data["columns"])
        n_cols = len(columns)
        source_shape = group_data.get("shape") or [0, n_cols]
        n_source = int(source_shape[0])
        group_id = str(group_data["group_id"])
        moved_dirs: set[Path] = set()
        freed_worker_bytes = 0

        shard_payloads = sorted(
            group_data.get("shards") or [],
            key=lambda item: int(item.get("shard_idx", 0)),
        )
        shard_metas: List[ShardMeta] = []
        disk_path: Optional[Path] = None

        if shard_payloads:
            width = max(2, len(str(len(shard_payloads) - 1)))
            for shard_payload in shard_payloads:
                shard_idx = int(shard_payload.get("shard_idx", 0))
                source_path = Path(str(shard_payload.get("path") or shard_payload.get("file")))
                target_path = registry.work_dir / f"{group_id}.shard{shard_idx:0{width}d}.npy"
                moved_bytes = self._copy_or_move_worker_file(
                    source_path,
                    target_path,
                    keep_source=keep_worker_npy,
                )
                freed_worker_bytes += moved_bytes
                if moved_bytes > 0:
                    moved_dirs.add(source_path.parent)
                shard_metas.append(
                    ShardMeta(
                        shard_idx=shard_idx,
                        col_start=int(shard_payload.get("col_start", 0)),
                        col_end=int(shard_payload.get("col_end", 0)),
                        n_rows=int(shard_payload.get("n_rows", n_source)),
                        disk_path=target_path,
                        nbytes=int(shard_payload.get("nbytes", target_path.stat().st_size)),
                    )
                )
        elif "npy_path" in group_data:
            source_path = Path(str(group_data["npy_path"]))
            disk_path = registry.work_dir / f"{group_id}.npy"
            moved_bytes = self._copy_or_move_worker_file(
                source_path,
                disk_path,
                keep_source=keep_worker_npy,
            )
            freed_worker_bytes += moved_bytes
            if moved_bytes > 0:
                moved_dirs.add(source_path.parent)
        elif "data" in group_data:
            source_array = np.asarray(group_data["data"], dtype=np.float32)
            disk_path = registry.work_dir / f"{group_id}.npy"
            np.save(disk_path, source_array, allow_pickle=False)
            n_source = int(source_array.shape[0])
        else:
            raise ValueError(f"Worker group {group_id} has no npy_path/shards/data payload")

        alignment = AlignmentMeta(
            source_timeframe=source_tf,
            primary_timeframe=self._primary_tf,
            source_n_rows=int(n_source),
            primary_n_rows=int(n_primary),
            idx_map_path=idx_map_path,
            alignment_mode=str(alignment_mode),
            offset_ns=0,
            source_dur_ns=int(source_dur_ns),
            primary_dur_ns=int(primary_dur_ns),
            mode=str(mode),
            align_algo_version=CURRENT_MTF_ALIGN_VERSION,
        )
        group = ColumnGroup(
            group_id=group_id,
            layer=LayerSource(group_data["layer"]),
            timeframe=str(group_data["timeframe"]),
            data_source=str(group_data["data_source"]),
            indicator=str(group_data["indicator"]),
            columns=columns,
            shape=(int(n_primary), n_cols),
            dtype="float32",
            disk_path=disk_path,
            shards=tuple(shard_metas),
            alignment=alignment,
        )
        try:
            registry.register(group)
        except Exception:
            for shard in shard_metas:
                if shard.disk_path.exists():
                    shard.disk_path.unlink()
            if disk_path is not None and disk_path.exists():
                disk_path.unlink()
            raise
        return freed_worker_bytes, moved_dirs

    @staticmethod
    def _load_worker_group_source_array(group_data: Dict) -> Tuple[np.ndarray, List[Path]]:
        """Load worker group source data for dense fallback registration."""
        source_paths: List[Path] = []
        if "shards" in group_data and group_data.get("shards"):
            shape = group_data.get("shape") or [0, len(group_data.get("columns", []))]
            n_rows = int(shape[0])
            n_cols = int(shape[1])
            out = np.empty((n_rows, n_cols), dtype=np.float32)
            for shard_payload in sorted(group_data["shards"], key=lambda item: int(item.get("shard_idx", 0))):
                source_path = Path(str(shard_payload.get("path") or shard_payload.get("file")))
                source_paths.append(source_path)
                shard_arr = np.load(source_path, mmap_mode="r", allow_pickle=False)
                col_start = int(shard_payload.get("col_start", 0))
                col_end = int(shard_payload.get("col_end", col_start + shard_arr.shape[1]))
                out[:, col_start:col_end] = np.asarray(shard_arr, dtype=np.float32)
                del shard_arr
            return out, source_paths

        if "npy_path" in group_data:
            source_path = Path(group_data["npy_path"])
            source_paths.append(source_path)
            return np.load(source_path, mmap_mode="r", allow_pickle=False), source_paths

        return np.asarray(group_data["data"], dtype=np.float32), source_paths

    @staticmethod
    def _copy_or_move_worker_file(source_path: Path, target_path: Path, *, keep_source: bool) -> int:
        """Move worker source file into main work_dir, or copy when debug retention is on."""
        source_path = Path(source_path)
        target_path = Path(target_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Worker source file missing: {source_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if source_path.resolve() == target_path.resolve():
                return 0
        except OSError:
            pass
        if target_path.exists():
            target_path.unlink()
        source_size = int(source_path.stat().st_size)
        if keep_source:
            shutil.copy2(source_path, target_path)
            return 0
        shutil.move(str(source_path), str(target_path))
        return source_size

    @staticmethod
    def _persist_alignment_idx_map(
        work_dir: Path,
        *,
        source_tf: str,
        primary_tf: str,
        alignment_mode: str,
        idx_map: np.ndarray,
    ) -> Path:
        """Persist the shared source→primary idx_map used by compact groups."""
        safe_mode = str(alignment_mode).replace("/", "_").replace(" ", "_")
        idx_map_path = Path(work_dir) / f".align_{source_tf}_to_{primary_tf}_{safe_mode}.npy"
        temp_path = idx_map_path.with_suffix(idx_map_path.suffix + ".tmp")
        if temp_path.exists():
            temp_path.unlink()
        idx_map_arr = np.asarray(idx_map, dtype=np.int32)
        with temp_path.open("wb") as handle:
            np.save(handle, idx_map_arr, allow_pickle=False)
        os.replace(temp_path, idx_map_path)
        return idx_map_path

    @classmethod
    def _persist_aligned_group_to_npy(
        cls,
        src_data: Optional[np.ndarray],
        target_path: Path,
        n_primary: int,
        n_cols: int,
        idx_map: Optional[np.ndarray],
        group_id: str,
    ) -> None:
        """Persist an aligned worker group with bounded RAM and clearer disk errors."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_name(f".{target_path.name}.{os.getpid()}.tmp")
        if temp_path.exists():
            temp_path.unlink()

        expected_bytes = int(n_primary) * int(n_cols) * np.dtype(np.float32).itemsize
        free_before = cls._disk_free_bytes(target_path.parent)
        if free_before is not None and free_before < expected_bytes:
            raise OSError(
                f"Insufficient disk space while aligning worker group {group_id}: "
                f"need {cls._format_bytes(expected_bytes)}, available {cls._format_bytes(free_before)}, "
                f"target={target_path}"
            )

        block_rows = cls._align_block_rows()
        try:
            out = np.lib.format.open_memmap(
                temp_path,
                mode="w+",
                dtype=np.float32,
                shape=(int(n_primary), int(n_cols)),
            )
            for row_start in range(0, n_primary, block_rows):
                row_end = min(row_start + block_rows, n_primary)
                out_block = out[row_start:row_end]

                if src_data is None:
                    out_block[:] = np.nan
                    continue

                if idx_map is None:
                    out_block[:] = np.asarray(src_data[row_start:row_end], dtype=np.float32)
                    continue

                block_idx = idx_map[row_start:row_end]
                valid = block_idx >= 0
                out_block[:] = np.nan
                if np.any(valid):
                    out_block[valid] = np.asarray(src_data[block_idx[valid]], dtype=np.float32)

            out.flush()
            del out
            os.replace(temp_path, target_path)
        except Exception as exc:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            free_after = cls._disk_free_bytes(target_path.parent)
            raise OSError(
                f"Failed to persist aligned worker group {group_id}: {exc}; "
                f"shape=({n_primary}, {n_cols}), bytes={cls._format_bytes(expected_bytes)}, "
                f"free_before={cls._format_bytes(free_before)}, free_after={cls._format_bytes(free_after)}, "
                f"target={target_path}"
            ) from exc

    @staticmethod
    def _align_block_rows() -> int:
        raw = os.getenv("FFACT_MULTI_TF_ALIGN_BLOCK_ROWS", "1024").strip()
        try:
            return max(1, int(raw))
        except ValueError:
            return 1024

    @staticmethod
    def _disk_free_bytes(path: Path) -> Optional[int]:
        try:
            return int(shutil.disk_usage(path).free)
        except OSError:
            return None

    @staticmethod
    def _format_bytes(num_bytes: Optional[int]) -> str:
        if num_bytes is None:
            return "unknown"
        return f"{num_bytes / (1024 ** 3):.2f} GiB"

    @staticmethod
    def _cleanup_worker_dirs(worker_dirs: Iterable[Path], main_work_dir: Path) -> None:
        main_resolved = main_work_dir.resolve()
        for worker_dir in worker_dirs:
            try:
                worker_resolved = worker_dir.resolve()
                if worker_resolved == main_resolved:
                    continue
                if worker_resolved.name.endswith("_worker") and worker_resolved.exists():
                    shutil.rmtree(worker_resolved, ignore_errors=True)
            except OSError as exc:
                logger.warning("Failed to cleanup worker directory %s: %s", worker_dir, exc)

    @staticmethod
    def _keep_worker_npy_enabled() -> bool:
        """Honor FFACT_MULTI_TF_KEEP_WORKER_NPY for debug / resume scenarios."""
        raw = os.getenv("FFACT_MULTI_TF_KEEP_WORKER_NPY", "0").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    def _compact_alignment_enabled() -> bool:
        """Honor FFACT_MULTI_TF_COMPACT_ALIGNMENT for non-primary TF groups."""
        raw = os.getenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "1").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def _alignment_params_or_raise(
        self,
        source_tf: str,
        alignment_mode: Optional[object] = None,
    ) -> tuple[int, int, str]:
        """Return validated source/primary durations and decision mode."""
        source_sec = TimeframeAligner._timeframe_to_seconds(source_tf)
        primary_sec = TimeframeAligner._timeframe_to_seconds(self._primary_tf)
        if source_sec is None or primary_sec is None:
            raise ValueError(f"Unsupported timeframe for alignment: source={source_tf}, primary={self._primary_tf}")
        if int(source_sec) % int(primary_sec) != 0 and int(primary_sec) % int(source_sec) != 0:
            raise ValueError(
                f"Non-divisible timeframe alignment is unsupported: source={source_tf}({source_sec}s), "
                f"primary={self._primary_tf}({primary_sec}s)"
            )
        resolved_mode = alignment_mode
        if resolved_mode is None:
            resolved_mode = self._config.timeframes.alignment_mode
        mode = TimeframeAligner._normalize_decision_mode(resolved_mode)
        return (
            int(source_sec) * 1_000_000_000,
            int(primary_sec) * 1_000_000_000,
            mode,
        )

    @staticmethod
    def _coerce_worker_timestamps_to_epoch_seconds(timestamps: np.ndarray) -> np.ndarray:
        """Normalize worker timestamp payloads from legacy ms or new epoch seconds."""
        arr = np.asarray(timestamps, dtype=np.int64)
        if arr.size == 0:
            return arr
        max_abs = int(np.max(np.abs(arr)))
        if max_abs >= 100_000_000_000:
            return (arr // 1_000).astype(np.int64)
        return arr.astype(np.int64, copy=False)

    @staticmethod
    def _log_gap_source_if_any(source_tf: str, source_dt: pd.DatetimeIndex, source_dur_ns: int) -> None:
        """Log source bars with open gaps without changing alignment semantics."""
        if len(source_dt) < 2:
            return
        source_s = TimeframeAligner._datetime_index_to_epoch_seconds(source_dt)
        expected_s = int(source_dur_ns // 1_000_000_000)
        if expected_s <= 0:
            return
        gap_count = int(np.count_nonzero(np.diff(source_s) != expected_s))
        if gap_count:
            logger.warning(
                "[multi_tf] Source timeframe %s has %d non-contiguous open timestamp gaps",
                source_tf,
                gap_count,
            )

    @staticmethod
    def _tf_alignment_version_current(registry: object, timeframe: str, layers: Iterable[object]) -> bool:
        """Return True only when every existing non-primary layer group has current alignment metadata."""
        layer_values = {getattr(layer, "value", str(layer)) for layer in layers}
        matched = 0
        for _gid, group in registry.iter_all():
            if getattr(group, "timeframe", None) != timeframe:
                continue
            group_layer = getattr(getattr(group, "layer", ""), "value", str(getattr(group, "layer", "")))
            if group_layer not in layer_values:
                continue
            matched += 1
            alignment = getattr(group, "alignment", None)
            if alignment is None:
                return False
            if int(getattr(alignment, "align_algo_version", 1)) != CURRENT_MTF_ALIGN_VERSION:
                return False
        return matched > 0

    @staticmethod
    def _drop_timeframe_groups_from_registry(registry: object, timeframe: str, layers: Iterable[object]) -> None:
        """Remove stale groups for one timeframe so resume can rebuild without duplicate ids."""
        layer_values = {getattr(layer, "value", str(layer)) for layer in layers}
        stale_group_ids: List[str] = []
        for gid, group in registry.iter_all():
            if getattr(group, "timeframe", None) != timeframe:
                continue
            group_layer = getattr(getattr(group, "layer", ""), "value", str(getattr(group, "layer", "")))
            if group_layer in layer_values:
                stale_group_ids.append(gid)
        for gid in stale_group_ids:
            registry.unregister_group(gid)

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
                spill_to_memmap = getattr(self._factory, "_spill_to_memmap", None)
                if not callable(spill_to_memmap):
                    from momentum.FeatureEngineering.feature_factory import FeatureFactory

                    spill_to_memmap = FeatureFactory._spill_to_memmap
                layer2 = spill_to_memmap(layer2, "layer2")

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

            combined = self._factory._combine_layers(
                [layer1, layer2, layer3, layer4, layer5, layer6],
                context="multi_tf_layers",
            )
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

        merged_df = self._factory._combine_layers(
            aligned_outputs,
            context="multi_tf_legacy_merged",
        )
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

        total_layer_counts = self._apply_total_layer_counts_to_result(result, tf_layer_counts)
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

    @staticmethod
    def _collect_layer_counts_from_registry(registry: object, tf: str) -> Dict[str, int]:
        """Reconstruct per-layer column counts from registry contents.

        Used by Multi-TF resume path: when a TF is skipped because its
        L1-L6 groups are already persisted, we need to report the correct
        layer counts (instead of zeros) without re-running the layers.
        """
        from momentum.FeatureEngineering.core.column_group import LayerSource as _LS

        layer_map = {
            _LS.L1: "layer1",
            _LS.L2: "layer2",
            _LS.L3: "layer3",
            _LS.L4: "layer4",
            _LS.L5: "layer5",
            _LS.L6: "layer6",
        }
        counts: Dict[str, int] = {name: 0 for name in layer_map.values()}
        for _gid, group in registry.iter_all():
            if group.timeframe != tf:
                continue
            key = layer_map.get(group.layer)
            if key is not None:
                counts[key] += group.shape[1]
        return counts

    def _build_total_layer_counts(self, tf_layer_counts: Dict[str, Dict[str, int]]) -> Dict[str, int]:
        total_layer_counts: Dict[str, int] = {}
        for timeframe, counts in tf_layer_counts.items():
            for layer_name, count in counts.items():
                key = layer_name if timeframe == self._primary_tf else f"{layer_name}_{timeframe}"
                total_layer_counts[key] = count
        return total_layer_counts

    def _apply_total_layer_counts_to_result(
        self,
        result: Any,
        tf_layer_counts: Dict[str, Dict[str, int]],
    ) -> Dict[str, int]:
        """Write manifest-derived multi-TF counts back into the result object."""
        total_layer_counts = self._build_total_layer_counts(tf_layer_counts)
        counted_total = sum(int(value) for value in total_layer_counts.values())
        feature_count = int(getattr(result, "feature_count", 0) or 0)

        if counted_total != feature_count:
            result_counts = getattr(result, "layer_counts", {}) or {}
            l65_count = int(result_counts.get("layer6_5", 0) or 0)
            if l65_count and counted_total + l65_count == feature_count:
                total_layer_counts["layer6_5"] = l65_count
            else:
                logger.warning(
                    "[MultiTF] Layer count total mismatch: counted=%d feature_count=%d counts=%s",
                    counted_total,
                    feature_count,
                    total_layer_counts,
                )

        result.layer_counts = total_layer_counts
        result.metadata["layer_counts"] = total_layer_counts
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

    @staticmethod
    def _multi_tf_parallel_enabled() -> bool:
        """Check if Multi-TF parallel processing is enabled (Task 1.5, SPEC §3.5).

        Enabled by default because multi-TF is the primary research mode.
        Set FFACT_MULTI_TF_PARALLEL=0 to force serial execution.
        """
        raw = os.getenv("FFACT_MULTI_TF_PARALLEL", "1").strip().lower()
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


# ------------------------------------------------------------------
# Module-level worker for Multi-TF parallel (Task 1.5, SPEC §3.5)
# Must be at module level for ProcessPoolExecutor pickling.
# ------------------------------------------------------------------

def _tf_worker_entry(
    symbol: str,
    timeframe: str,
    config_payload: dict,
    start_date: Optional[str],
    end_date: Optional[str],
    cache_dir: Optional[str] = None,
) -> Dict:
    """Process a single timeframe in a spawned worker process.

    Each worker creates its own FeatureFactory with an independent
    ColumnGroupRegistry. Returns serialized group data + source timestamps
    for the main process to register and align.

    Returns dict with keys: timeframe, groups, source_timestamps_ms,
    layer_counts, or error.

    Note: NUMBA_NUM_THREADS=1 is set here to keep Numba in sequential mode
    inside the spawned subprocess. The workqueue threading layer is not
    safe for concurrent access across processes; forcing a single thread
    avoids SIGABRT while keeping full JIT compilation benefits.
    All hot paths (fused_rolling_stats_multi_window, _rolling_rank_numba)
    have already been changed from parallel=True/prange to sequential, so
    there is no performance regression vs. the parallel build.
    """
    import os as _os
    _os.environ["NUMBA_NUM_THREADS"] = "1"
    from momentum.factories import create_feature_factory

    try:
        # Bug #1 fix: pass cache_dir so the worker uses the same kline cache.
        factory = create_feature_factory(cache_dir=cache_dir, validate_continuity=False)
        config = factory._resolve_config(config_payload)

        # Bug #2 fix: explicitly initialize the CGSA registry so that L1/L2
        # layer methods can persist their groups, and so L3-L6 persist calls
        # below have a valid registry to write to.
        factory._cgsa_force_fresh = True
        factory._cgsa_registry = factory._prepare_cgsa_registry(symbol, timeframe, "worker")

        raw_data = factory._layer0_data_ingestion(
            symbol, timeframe, config,
            start_date=start_date, end_date=end_date,
        )
        if raw_data is None or raw_data.empty:
            return {"timeframe": timeframe, "error": f"Empty data for {symbol}/{timeframe}"}

        # Extract source timestamps for alignment by main process
        source_index, _ = TimeframeAligner._split_timestamp_index(raw_data)
        source_dt = TimeframeAligner._to_datetime_index(source_index)
        source_timestamps_ms = (
            source_dt.to_numpy(dtype="datetime64[ns]").astype(np.int64) // 1_000_000
        ).astype(np.int64)

        factory._current_timeframe = timeframe

        # OOM Fix: persist+del+gc per layer to avoid holding multiple large
        # layers in worker memory simultaneously. 1h L3 alone can be ~10 GB.
        from momentum.FeatureEngineering.core.column_group import LayerSource as _LS
        import gc as _gc

        layer1 = factory._layer1_atomic_indicators(raw_data, config)
        layer2 = factory._layer2_derived_features(layer1, raw_data, config)
        layer3 = factory._layer3_rolling_aggregation(layer1, layer2, config)
        # Plan A streaming: when L3 streaming-persist is active, layer3 is an
        # empty index-only DataFrame because survivors are already in registry.
        # Read true count from the registry instead of layer3.shape.
        if layer3 is not None and not layer3.empty:
            factory._persist_layer_output_groups(layer3, _LS.L3, "L3_rolling")
            layer_counts_l3 = layer3.shape[1]
        else:
            registry = getattr(factory, "_cgsa_registry", None)
            layer_counts_l3 = sum(
                g.shape[1] for _, g in registry.iter_all() if g.layer == _LS.L3
            ) if registry is not None else 0
        del layer3
        _gc.collect()

        layer4 = factory._layer4_lag_features(layer1, layer2, None, raw_data, config)
        layer_counts_l4 = layer4.shape[1] if layer4 is not None else 0
        if layer4 is not None and not layer4.empty:
            factory._persist_layer_output_groups(layer4, _LS.L4, "L4_lag")
        del layer4
        _gc.collect()

        layer5 = factory._layer5_cross_sectional(layer1, layer2, config)
        layer_counts_l5 = layer5.shape[1] if layer5 is not None else 0
        if layer5 is not None and not layer5.empty:
            factory._persist_layer_output_groups(layer5, _LS.L5, "L5_cross")
        del layer5
        _gc.collect()

        layer6 = factory._layer6_meta_features(layer1, layer2, raw_data, config)
        layer_counts_l6 = layer6.shape[1] if layer6 is not None else 0
        if layer6 is not None and not layer6.empty:
            factory._persist_layer_output_groups(layer6, _LS.L6, "L6_meta")
        del layer6

        # L1/L2 already persisted inside their layer methods; capture counts
        # then drop wide DataFrames before collecting group metadata.
        layer_counts = {
            "layer1": layer1.shape[1] if layer1 is not None else 0,
            "layer2": layer2.shape[1] if layer2 is not None else 0,
            "layer3": layer_counts_l3,
            "layer4": layer_counts_l4,
            "layer5": layer_counts_l5,
            "layer6": layer_counts_l6,
        }
        del layer1, layer2
        _gc.collect()

        # OOM Fix: collect ONLY metadata + .npy paths, never reload arrays.
        # Previously this materialised every group (np.asarray on mmap), pushing
        # 1h worker RSS past 10 GB and triggering BrokenProcessPool. The main
        # process now mmap-reads from these paths in _register_worker_groups.
        groups_data: List[Dict] = []
        registry = getattr(factory, "_cgsa_registry", None)
        if registry is not None:
            for group_id in sorted(registry._groups.keys()):
                group = registry.get(group_id)
                shards_payload = []
                if getattr(group, "shards", ()):
                    missing_shard = False
                    for shard in group.shards:
                        if not Path(shard.disk_path).exists():
                            missing_shard = True
                            break
                        shards_payload.append({
                            "shard_idx": shard.shard_idx,
                            "col_start": shard.col_start,
                            "col_end": shard.col_end,
                            "n_rows": shard.n_rows,
                            "nbytes": shard.nbytes,
                            "path": str(shard.disk_path),
                        })
                    if missing_shard:
                        continue
                    groups_data.append({
                        "group_id": group.group_id,
                        "layer": group.layer.value,
                        "timeframe": group.timeframe,
                        "data_source": group.data_source,
                        "indicator": group.indicator,
                        "columns": list(group.columns),
                        "shape": list(group.shape),
                        "dtype": group.dtype,
                        "shards": shards_payload,
                    })
                    continue

                npy_path = group.disk_path
                # If a group is still buffered in memory (no disk_path),
                # flush it explicitly so the main process can mmap-read it.
                if npy_path is None or not Path(npy_path).exists():
                    target_path = registry.work_dir / f"{group_id}.npy"
                    buffered = registry._memory_buffer.get(group_id) if hasattr(registry, "_memory_buffer") else None
                    if buffered is None:
                        # Defensive: skip groups with no recoverable data.
                        continue
                    np.save(target_path, np.asarray(buffered, dtype=np.float32), allow_pickle=False)
                    npy_path = target_path
                groups_data.append({
                    "group_id": group.group_id,
                    "layer": group.layer.value,
                    "timeframe": group.timeframe,
                    "data_source": group.data_source,
                    "indicator": group.indicator,
                    "columns": list(group.columns),
                    "shape": list(group.shape),
                    "dtype": group.dtype,
                    "npy_path": str(npy_path),
                })

        return {
            "timeframe": timeframe,
            "groups": groups_data,
            "source_timestamps_ms": source_timestamps_ms,
            "layer_counts": layer_counts,
        }
    except Exception as exc:
        return {"timeframe": timeframe, "error": str(exc)}
