"""Multi-timeframe feature generation."""

from __future__ import annotations

import gc
import os
import shutil
import time
from pathlib import Path
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

        # Task 1.5: parallel mode dispatches non-primary TFs to spawned workers
        if self._multi_tf_parallel_enabled() and len(self._training_tfs) > 1:
            return self._generate_multi_tf_cgsa_parallel(
                symbol, primary_raw, primary_timestamps, start_time,
                start_date=start_date, end_date=end_date,
            )

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

            # Set current timeframe so CGSA group IDs use the correct TF prefix.
            self._factory._current_timeframe = timeframe

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
            from momentum.FeatureEngineering.core.column_group import LayerSource as _LS
            if layer3 is not None and not layer3.empty:
                self._factory._persist_layer_output_groups(layer3, _LS.L3, "L3_rolling")
            if layer4 is not None and not layer4.empty:
                self._factory._persist_layer_output_groups(layer4, _LS.L4, "L4_lag")
            if layer5 is not None and not layer5.empty:
                self._factory._persist_layer_output_groups(layer5, _LS.L5, "L5_cross")
            if layer6 is not None and not layer6.empty:
                self._factory._persist_layer_output_groups(layer6, _LS.L6, "L6_meta")

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

        # Restore current timeframe to primary for downstream L6.5/L7.
        self._factory._current_timeframe = self._primary_tf

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
    ) -> "FeatureGenerationResult":
        """CGSA multi-TF with ProcessPoolExecutor + spawn for non-primary TFs."""
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed

        from momentum.FeatureEngineering.feature_factory import _warmup_numba_functions
        from momentum.FeatureEngineering.core.column_group import LayerSource as _LS

        registry = self._factory._cgsa_registry
        skipped_tfs: List[str] = []
        tf_layer_counts: Dict[str, Dict[str, int]] = {}

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

            tf_layer_counts[self._primary_tf] = self._collect_layer_counts(
                [layer1, layer2, layer3, layer4, layer5, layer6]
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
                    self._register_worker_groups(
                        registry, groups_data, tf,
                        primary_timestamps, self._config.timeframes.alignment_mode,
                        source_timestamps_ms=source_ts_ms,
                    )
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

        # L6.5 preprocessing via registry (per-group)
        if self._config.preprocessing.enabled:
            self._report_progress("preprocessing", 0.75, "[CGSA-parallel] Running Layer 6.5")
            self._factory._layer6_5_preprocessing(pd.DataFrame(), self._config)

        # L7 validate + persist
        self._report_progress("persist", 0.9, "[CGSA-parallel] Running Layer 7")
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

        self._report_progress("complete", 1.0, f"[CGSA-parallel] MultiTF completed ({elapsed:.2f}s)")
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
        primary_ms = (
            primary_timestamps.to_numpy(dtype="datetime64[ns]").astype(np.int64) // 1_000_000
        ).astype(np.int64)

        # Build alignment index map from source → primary timestamps
        idx_map: Optional[np.ndarray] = None
        if source_timestamps_ms is not None:
            offset_ns = -1 if alignment_mode == AlignmentMode.OPEN_MINUS else 0
            idx_map = TimeframeAligner.build_asof_index_map(
                primary_ms, source_timestamps_ms, offset_ns=offset_ns,
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
            source_npy_path: Optional[Path] = None

            # OOM Fix: mmap-read the worker's .npy instead of receiving a
            # full ndarray over pickle. Backwards compatible: if a worker
            # returned the legacy "data" payload, fall back to it.
            if "npy_path" in gd:
                source_npy_path = Path(gd["npy_path"])
                src_data = np.load(source_npy_path, mmap_mode="r", allow_pickle=False)
            else:
                src_data = gd["data"]

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

            if source_npy_path is not None and not keep_worker_npy:
                # Skip cleanup when KEEP_WORKER_NPY is enabled so the worker
                # .npy + workdir remain intact for debugging / resume scenarios.
                try:
                    source_resolved = source_npy_path.resolve()
                    target_resolved = npy_path.resolve()
                    if source_resolved != target_resolved and source_npy_path.exists():
                        file_size = source_npy_path.stat().st_size
                        source_npy_path.unlink()
                        freed_worker_bytes += file_size
                        worker_dirs_to_cleanup.add(source_npy_path.parent)
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
            "[CGSA-parallel] Registered %d groups from worker TF %s (freed worker npy %.2f GiB)",
            aligned_count, source_tf, freed_worker_bytes / (1024 ** 3),
        )

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
