"""
Feature Factory Service - Feature Factory 任務與配置管理
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import os
import threading
import time
import uuid
from bisect import bisect_right
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import h5py
import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.stattools import adfuller
    HAS_STATSMODELS = True
except Exception:
    HAS_STATSMODELS = False

from api.core.config import settings
from api.core.logging import get_logger
from api.utils.feature_name_parser import infer_category, infer_layer, infer_level
from momentum.core.contracts import FailureType, classify_error, FeatureGenerationResult
from momentum.factories import create_feature_factory, create_feature_factory_mcp


logger = get_logger("api.feature_factory_service")

# Feature Factory 使用獨立的 K 線儲存目錄（與案例 K 線分離）
# 對應 FeatureKlineDownloadPanel 的下載目標路徑
_FEATURE_KLINE_CACHE_DIR = str(settings.data_cache_path / "feature_klines")


class FeatureFactoryService:
    """Feature Factory service for task management and config operations."""

    _report_builder_cls = None  # Lazy-loaded via service_providers (Rule 4 compliant)
    _NAN_PATTERN_MAX_STEPS: int = 400  # max time columns returned in NaN pattern matrix

    @classmethod
    def _get_report_builder(cls):
        """Return a stateless FeatureExportService instance (Rule 4 compliant)."""
        if cls._report_builder_cls is None:
            from api.utils.service_providers import get_report_builder_class
            cls._report_builder_cls = get_report_builder_class()
        return cls._report_builder_cls()

    def __init__(self):
        self._factory = create_feature_factory(cache_dir=_FEATURE_KLINE_CACHE_DIR)
        self._config_manager = self._factory.config_manager
        self._mcp = create_feature_factory_mcp(factory=self._factory)
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._research_tasks: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()
        # Per-task DataFrame cache: task_id -> (DataFrame, export_meta)
        # Kept in memory to avoid re-reading HDF5 on every browse/export call.
        # Invalidated when the task is removed or a new generation starts.
        self._df_cache: Dict[str, tuple] = {}
        # Per-task pre-computed feature stats (for browse_features).
        # Shape: list of dicts with name/category/level/layer/nan_ratio/mean/std/…
        self._stats_cache: Dict[str, List[Dict[str, Any]]] = {}
        # Pre-sorted name-ascending view for default pagination fast-path.
        self._stats_name_sorted_cache: Dict[str, List[Dict[str, Any]]] = {}
        # Pre-built name keys aligned with _stats_name_sorted_cache for bisect cursor lookup.
        self._stats_name_keys_cache: Dict[str, List[str]] = {}
        # Task IDs currently warming stats in background to avoid duplicate warm threads.
        self._stats_warming_tasks: set[str] = set()
        # Per-task ADF cache: task_id -> feature_name -> pvalue (or None if unavailable).
        self._adf_cache: Dict[str, Dict[str, Optional[float]]] = {}
        # Task IDs currently warming ADF cache in background.
        self._adf_warming_tasks: set[str] = set()
        # Per-task inferred metadata cache: task_id -> feature_name -> {category, layer, level}
        self._feature_metadata_cache: Dict[str, Dict[str, Dict[str, str]]] = {}
        # Per-task CGSA catalog rows derived from parquet/manifest metadata.
        # This powers Feature Explorer table/options without materializing the
        # full 50k-200k column DataFrame.
        self._cgsa_catalog_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cgsa_column_path_cache: Dict[str, Dict[str, Path]] = {}
        # Per-task CGSA feature stats DataFrame indexed by feature name.
        # Backed by feature_stats_cache.parquet in the manifest directory so
        # computed stats survive API restarts and repeat searches are instant.
        self._cgsa_stats_mem_cache: Dict[str, pd.DataFrame] = {}
        # Task IDs currently running background CGSA stats warmup.
        self._cgsa_stats_warming_tasks: set[str] = set()
        self._cgsa_catalog_warming_tasks: set[str] = set()
        # Task IDs currently baking data_quality.json in background.
        self._data_quality_warming_tasks: set[str] = set()

        # ─── Browse request coalescing & warmup throttling (P0-A / P0-C) ───
        # Maps fingerprint -> in-flight threading.Event + result holder so that
        # multiple concurrent identical requests (StrictMode double-invoke, tab
        # remount, multi-tab fanout) reuse one underlying compute pass instead
        # of running the heavy parquet scan N times.  All browse_* methods are
        # synchronous (called via run_in_executor from FastAPI) so we use
        # threading primitives, not asyncio.
        self._browse_inflight: Dict[tuple, Dict[str, Any]] = {}
        self._browse_inflight_lock = threading.Lock()
        # Active foreground-request gauge; warmup workers yield while >0 so
        # they never compete with a user's tab load on 8GB hardware.
        self._active_browse_requests: int = 0
        self._active_browse_lock = threading.Lock()

        # Hardware-adaptive CGSA stats parameters (Q1 / Q2 optimisation).
        # Detected once at startup; overridden via FFACT_MEMORY_TIER env var.
        # Falls back to conservative 8GB defaults on detection failure.
        try:
            from momentum.FeatureEngineering.utils.hardware_utils import (
                get_memory_tier as _stats_gmt,
                get_tier_config as _stats_gtc,
            )
            _stats_tier = _stats_gmt()
            _stats_tcfg = _stats_gtc(_stats_tier)
            self._cgsa_stats_sync_cap: int = int(
                _stats_tcfg.get("cgsa_stats_sync_cap", self._CGSA_STATS_SYNC_CAP)
            )
            self._cgsa_stats_q_sample: int = int(
                _stats_tcfg.get("cgsa_stats_q_sample", 3_000)
            )
            self._cgsa_stats_warmup_workers: int = int(
                _stats_tcfg.get("cgsa_stats_warmup_workers", 4)
            )
            logger.info(
                "CGSA stats (tier=%s): sync_cap=%d q_sample=%d warmup_workers=%d",
                _stats_tier,
                self._cgsa_stats_sync_cap,
                self._cgsa_stats_q_sample,
                self._cgsa_stats_warmup_workers,
            )
        except Exception as _tier_exc:
            logger.warning(
                "CGSA stats tier detection failed, using conservative defaults: %s", _tier_exc
            )
            self._cgsa_stats_sync_cap = self._CGSA_STATS_SYNC_CAP
            self._cgsa_stats_q_sample = 3_000
            self._cgsa_stats_warmup_workers = 4

        # Restore any previously-completed tasks from disk so the Feature
        # Explorer stays functional across API restarts.
        self._restore_persisted_tasks()

    async def start_generation(self, request: Any) -> Dict[str, str]:
        """Start feature generation task."""
        task_id = str(uuid.uuid4())
        task_info = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "completed_stages": [],
            "error": None,
            "result": None,
            "created_at": datetime.now().isoformat(),
        }

        with self._lock:
            self._tasks[task_id] = task_info

        logger.info("Feature generation task started: %s", task_id)
        asyncio.create_task(self._run_task(task_id, request))

        return {"task_id": task_id, "status": "running"}

    async def _run_task(self, task_id: str, request: Any) -> None:
        """Run feature generation task in a thread pool to avoid blocking the event loop.

        generate_features() is CPU/IO-bound synchronous code.  Running it with
        run_in_executor keeps the event loop responsive so WebSocket heartbeats,
        progress notifications, and other HTTP requests are handled normally while
        the generation is in progress.
        """
        loop = asyncio.get_running_loop()

        def progress_callback(payload: Dict[str, Any]) -> None:
            """Called from the worker thread — must not touch asyncio directly."""
            stage = payload.get("stage")
            progress = payload.get("progress", 0.0)
            message = payload.get("message", "")

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["current_stage"] = stage
                task_info["progress"] = float(progress)
                if stage and progress >= 1.0:
                    if stage not in task_info["completed_stages"]:
                        task_info["completed_stages"].append(stage)

            notify_payload = {"stage": stage, "progress": float(progress), "message": message}
            # call_soon_threadsafe schedules _notify_callbacks back on the event loop
            # thread so asyncio.create_task() calls inside WS callbacks remain safe.
            loop.call_soon_threadsafe(self._notify_callbacks, task_id, notify_payload)

        try:
            config_override = getattr(request, "config_override", None)
            force_regenerate = bool(getattr(request, "force_regenerate", False))
            timeframe = getattr(request, "timeframe", "12h")
            symbol = getattr(request, "symbol", None)
            start_date = getattr(request, "start_date", None)
            end_date = getattr(request, "end_date", None)

            if not symbol:
                raise ValueError("symbol is required")

            resolved_override = self._resolve_config_override(config_override)

            # Offload the blocking call to a thread pool worker.
            result = await loop.run_in_executor(
                None,
                lambda: self._generate_features_with_phase_d(
                    task_id=task_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    config_override=resolved_override,
                    force_regenerate=force_regenerate,
                    progress_callback=progress_callback,
                    start_date=start_date,
                    end_date=end_date,
                ),
            )

            summary = self._summarize_result(result)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["result"] = summary

            # Persist task record to disk so the task can be restored after an
            # API restart without re-running feature generation.
            self._persist_task_record(task_id, summary)

            # Precompute Feature Table stats as soon as generation completes for
            # legacy HDF5 tasks. CGSA outputs can have 50k-200k columns; full
            # stats warmup materializes the whole matrix and blocks the UI for
            # minutes. CGSA Feature Explorer uses manifest/parquet metadata.
            if str(summary.get("hdf5_path", "")).lower().endswith(".json"):
                try:
                    context = self._load_task_context(task_id)
                    self._start_cgsa_catalog_warmup(task_id, context)
                    # Bake data_quality.json in background so the dashboard
                    # opens instantly after pipeline completes. Runs after the
                    # "completed" event is dispatched, so it does not delay the
                    # pipeline-finished signal users see.
                    self._start_data_quality_warmup(task_id, context)
                except Exception as exc:
                    logger.debug("CGSA catalog warmup start skipped for %s: %s", task_id, exc)
            else:
                self._start_stats_cache_warmup(task_id, reason="generation_completed")

            self._notify_callbacks(task_id, {
                "stage": "completed",
                "progress": 1.0,
                "message": "Feature generation completed",
                "result": summary,
            })

        except Exception as exc:
            error_type = classify_error(exc)
            logger.error(
                "Feature generation failed (%s): %s",
                error_type.value,
                exc,
                exc_info=True,
            )
            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "stage": "failed",
                "progress": 1.0,
                "message": str(exc),
            })

    def _generate_features_with_phase_d(
        self,
        task_id: str,
        symbol: str,
        timeframe: str,
        config_override: Optional[dict],
        force_regenerate: bool,
        progress_callback: Optional[Callable],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> FeatureGenerationResult:
        """Phase D governance: old/new compute path toggle, shadow compare, and rollback fallback."""
        new_path_enabled = self._is_new_compute_path_enabled()
        if not new_path_enabled:
            logger.info("Phase D: new_compute_path disabled, using old path for task %s", task_id)
            return self._run_with_env_overrides(
                self._factory,
                symbol=symbol,
                timeframe=timeframe,
                config_override=config_override,
                force_regenerate=force_regenerate,
                progress_callback=progress_callback,
                env_overrides=self._old_path_env_overrides(),
                start_date=start_date,
                end_date=end_date,
            )

        new_result = self._factory.generate_features(
            symbol=symbol,
            timeframe=timeframe,
            config_override=config_override,
            force_regenerate=force_regenerate,
            progress_callback=progress_callback,
            start_date=start_date,
            end_date=end_date,
        )

        if not self._should_run_dual_path_check(task_id):
            self._attach_phase_d_metadata(
                new_result,
                {
                    "new_compute_path": True,
                    "dual_run": False,
                    "fallback_triggered": False,
                    "reason": "sampling_skipped",
                },
            )
            return new_result

        logger.info("Phase D: running dual-path shadow compare for task %s", task_id)
        old_shadow_result = self._run_shadow_old_path(
            symbol=symbol,
            timeframe=timeframe,
            config_override=config_override,
            start_date=start_date,
            end_date=end_date,
        )
        equal, reason = self._compare_generation_results(old_shadow_result, new_result)

        if equal:
            self._attach_phase_d_metadata(
                new_result,
                {
                    "new_compute_path": True,
                    "dual_run": True,
                    "fallback_triggered": False,
                    "compare_passed": True,
                    "compare_reason": "ok",
                },
            )
            return new_result

        logger.error("Phase D gate failed for task %s, rollback to old path: %s", task_id, reason)
        fallback_result = self._run_with_env_overrides(
            self._factory,
            symbol=symbol,
            timeframe=timeframe,
            config_override=config_override,
            # Bypass cache to guarantee old path output is persisted after rollback.
            force_regenerate=True,
            progress_callback=progress_callback,
            env_overrides=self._old_path_env_overrides(),
            start_date=start_date,
            end_date=end_date,
        )
        self._attach_phase_d_metadata(
            fallback_result,
            {
                "new_compute_path": True,
                "dual_run": True,
                "fallback_triggered": True,
                "compare_passed": False,
                "compare_reason": reason,
            },
        )
        return fallback_result

    def _run_shadow_old_path(
        self,
        symbol: str,
        timeframe: str,
        config_override: Optional[dict],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> FeatureGenerationResult:
        shadow_factory = create_feature_factory()
        # Shadow path must not overwrite persisted output — use persist=False.
        return self._run_with_env_overrides(
            shadow_factory,
            symbol=symbol,
            timeframe=timeframe,
            config_override=config_override,
            force_regenerate=True,
            progress_callback=None,
            env_overrides=self._old_path_env_overrides(),
            start_date=start_date,
            end_date=end_date,
            persist=False,
        )

    def _run_with_env_overrides(
        self,
        factory,
        symbol: str,
        timeframe: str,
        config_override: Optional[dict],
        force_regenerate: bool,
        progress_callback: Optional[Callable],
        env_overrides: Dict[str, str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        persist: bool = True,
    ) -> FeatureGenerationResult:
        with self._temporary_environ(env_overrides):
            return factory.generate_features(
                symbol=symbol,
                timeframe=timeframe,
                config_override=config_override,
                force_regenerate=force_regenerate,
                progress_callback=progress_callback,
                start_date=start_date,
                end_date=end_date,
                persist=persist,
            )

    @staticmethod
    def _is_new_compute_path_enabled() -> bool:
        raw = os.getenv("FFACT_NEW_COMPUTE_PATH", "0").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _should_run_dual_path_check(self, task_id: str) -> bool:
        sample_rate = self._dual_run_sample_rate()
        if sample_rate <= 0:
            return False
        if sample_rate >= 1:
            return True

        # Deterministic sampling by task_id to keep behavior reproducible across retries.
        digest = hashlib.md5(task_id.encode("utf-8")).hexdigest()
        sample_value = int(digest[:8], 16) / float(0xFFFFFFFF)
        return sample_value < sample_rate

    @staticmethod
    def _dual_run_sample_rate() -> float:
        raw = os.getenv("FFACT_NEW_COMPUTE_DUALRUN_SAMPLE_RATE", "0").strip()
        try:
            parsed = float(raw)
        except ValueError:
            parsed = 0.0
        return max(0.0, min(1.0, parsed))

    @staticmethod
    def _old_path_env_overrides() -> Dict[str, str]:
        # Keep old behavior: no Layer1 parallel, no Layer3 column-chunking.
        # Layer4 chunk/batch use large values to approximate non-chunked flow.
        # FFACT_L3_STREAMING=1 activates Phase-2 streaming + variance filter to
        # prevent OOM on wide feature matrices (96K+ cols) on M1 8GB.
        return {
            "FFACT_LAYER1_PARALLEL": "0",
            "FFACT_LAYER3_CHUNK_SIZE": "0",
            "FFACT_LAYER4_CHUNK_SIZE": "1000000000",
            "FFACT_LAYER4_LAG_BATCH_SIZE": "1000000000",
            "FFACT_L3_STREAMING": "1",
        }

    @staticmethod
    def _compare_generation_results(old_result: FeatureGenerationResult, new_result: FeatureGenerationResult) -> tuple[bool, str]:
        old_features = old_result.features_df
        new_features = new_result.features_df
        if list(old_features.columns) != list(new_features.columns):
            return False, "feature_columns_mismatch"
        if not old_features.index.equals(new_features.index):
            return False, "feature_index_mismatch"
        if old_features.shape != new_features.shape:
            return False, "feature_shape_mismatch"
        if not np.array_equal(old_features.to_numpy(), new_features.to_numpy(), equal_nan=True):
            return False, "feature_values_mismatch"

        old_labels = old_result.labels_df
        new_labels = new_result.labels_df
        if list(old_labels.columns) != list(new_labels.columns):
            return False, "label_columns_mismatch"
        if not old_labels.index.equals(new_labels.index):
            return False, "label_index_mismatch"
        if old_labels.shape != new_labels.shape:
            return False, "label_shape_mismatch"
        if not np.array_equal(old_labels.to_numpy(), new_labels.to_numpy(), equal_nan=True):
            return False, "label_values_mismatch"

        metadata_ok, metadata_reason = FeatureFactoryService._compare_metadata_contract(
            old_result.metadata,
            new_result.metadata,
        )
        if not metadata_ok:
            return False, metadata_reason
        return True, "ok"

    @staticmethod
    def _compare_metadata_contract(old_metadata: Dict[str, Any], new_metadata: Dict[str, Any]) -> tuple[bool, str]:
        keys = [
            "feature_names",
            "feature_count",
            "layer_counts",
            "symbol",
            "timeframe",
            "data_range",
        ]
        for key in keys:
            if old_metadata.get(key) != new_metadata.get(key):
                return False, f"metadata_mismatch:{key}"
        return True, "ok"

    @staticmethod
    def _attach_phase_d_metadata(result: FeatureGenerationResult, payload: Dict[str, Any]) -> None:
        if not isinstance(result.metadata, dict):
            result.metadata = {}
        result.metadata["phase_d_governance"] = payload

    @staticmethod
    @contextlib.contextmanager
    def _temporary_environ(overrides: Dict[str, str]):
        previous: Dict[str, Optional[str]] = {}
        try:
            for key, value in overrides.items():
                previous[key] = os.environ.get(key)
                os.environ[key] = str(value)
            yield
        finally:
            for key, old in previous.items():
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by task id."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            return {
                "task_id": task_info["task_id"],
                "status": task_info["status"],
                "progress": task_info["progress"],
                "current_stage": task_info["current_stage"],
                "completed_stages": list(task_info["completed_stages"]),
                "error": task_info["error"],
            }

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task result if available."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            return task_info.get("result")

    def list_completed_tasks(self) -> List[Dict[str, Any]]:
        """Return a summary of all completed tasks (including restored ones).
        Used by the /browse/available endpoint so the frontend can recover after
        an API restart."""
        with self._lock:
            result = []
            for task_id, info in self._tasks.items():
                if info.get("status") != "completed":
                    continue
                task_result = info.get("result") or {}
                meta = task_result.get("metadata") or {}
                result.append({
                    "task_id": task_id,
                    "symbol": meta.get("symbol", ""),
                    "timeframe": meta.get("timeframe", ""),
                    "feature_count": task_result.get("feature_count"),
                    "created_at": info.get("created_at", ""),
                    "hdf5_path": task_result.get("hdf5_path", ""),
                })
            return sorted(result, key=lambda x: x["created_at"], reverse=True)

    def register_hdf5_for_browse(self, symbol: str, timeframe: str, hdf5_path: str) -> str:
        """將批次模式的 HDF5 檔案登錄為可瀏覽的虛擬任務，回傳可供 FeatureExplorer 使用的 task_id。

        批次任務結果以 {symbol: hdf5_path} 儲存，沒有單獨的 task_id，
        透過此方法建立虛擬任務記錄讓 browse endpoints 可以正常運作。
        """
        file_path = Path(hdf5_path)
        if not file_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

        # 使用固定格式的 task_id，相同 symbol+timeframe 重複呼叫回傳同一個 id（冪等）
        task_id = f"browse_{symbol}_{timeframe}"
        result = {
            "hdf5_path": str(hdf5_path),
            "metadata": {"symbol": symbol, "timeframe": timeframe},
            "feature_count": None,
            "generation_time": None,
            "layer_counts": {},
        }

        with self._lock:
            if task_id not in self._tasks:
                self._tasks[task_id] = {
                    "task_id": task_id,
                    "status": "completed",
                    "progress": 1.0,
                    "current_stage": None,
                    "completed_stages": [],
                    "error": None,
                    "result": result,
                    "created_at": datetime.now().isoformat(),
                }
            else:
                # 更新 hdf5_path 以反映最新批次結果
                self._tasks[task_id]["result"] = result

        logger.info(
            "Registered HDF5 for browse: task_id=%s symbol=%s timeframe=%s",
            task_id, symbol, timeframe,
        )
        return task_id

    def export_csv_stream(
        self,
        task_id: str,
        columns: Optional[List[str]] = None,
        max_rows: Optional[int] = None,
        include_metadata_header: bool = True,
        include_datasource: bool = False,
    ) -> Dict[str, Any]:
        """Build CSV export stream payload for API route."""
        from momentum.factories import create_kline_storage_manager

        context = self._load_task_context(task_id)
        schema = self._load_hdf5_schema(context)

        all_columns = schema["feature_names"]
        selected_columns = list(columns or [])
        if selected_columns:
            invalid = [column for column in selected_columns if column not in set(all_columns)]
            if invalid:
                raise ValueError(f"Invalid columns: {invalid}. Available columns count: {len(all_columns)}")
        else:
            selected_columns = all_columns

        row_count = int(schema["row_count"])
        if max_rows is not None and max_rows >= 0:
            row_count = min(row_count, max_rows)

        symbol = context["symbol"]
        timeframe = context["timeframe"]
        filename = f"{symbol}_{timeframe}_features_{task_id}.csv"

        # Load raw kline DataFrame indexed by datetime if requested
        raw_df: Optional[pd.DataFrame] = None
        raw_columns: List[str] = []
        if include_datasource:
            try:
                storage = create_kline_storage_manager(cache_dir=_FEATURE_KLINE_CACHE_DIR)
                kline_df = storage.read_klines(symbol, timeframe, validate_continuity=False)
                if kline_df is not None and not kline_df.empty and "timestamp" in kline_df.columns:
                    ts_val = kline_df["timestamp"].iloc[0]
                    kline_unit = "ms" if ts_val > 1e12 else "s"
                    kline_df = kline_df.set_index(
                        pd.to_datetime(kline_df["timestamp"], unit=kline_unit, errors="coerce")
                    )
                    kline_df.index.name = "timestamp"
                    # Keep only numeric raw OHLCV columns; drop the original timestamp column
                    raw_cols_candidates = [
                        "open", "high", "low", "close", "volume",
                        "taker_buy_volume", "taker_ratio", "quote_volume", "trades",
                    ]
                    raw_columns = [c for c in raw_cols_candidates if c in kline_df.columns]
                    raw_df = kline_df[raw_columns]
                    logger.info(f"Loaded {len(raw_df)} kline rows for datasource export ({raw_columns})")
                else:
                    logger.warning(f"No kline data found for {symbol}/{timeframe}; skipping datasource columns")
            except Exception as exc:
                logger.warning(f"Failed to load kline data for datasource export: {exc}")
                raw_df = None
                raw_columns = []

        export_meta = {
            "task_id": task_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "generated_at": context["generated_at"],
            "feature_count": len(selected_columns),
            "row_count": row_count,
            "datasource_columns": raw_columns,
        }

        generator = self._csv_chunk_generator_from_hdf5(
            context=context,
            selected_columns=selected_columns,
            max_rows=row_count,
            export_meta=export_meta,
            include_metadata_header=include_metadata_header,
            raw_df=raw_df,
            raw_columns=raw_columns,
        )

        return {
            "generator": generator,
            "filename": filename,
            "feature_count": int(len(selected_columns)),
            "row_count": int(row_count),
        }

    def export_json_report(
        self,
        task_id: str,
        include_sample_data: bool,
        sample_rows: int,
        include_statistics: bool,
        include_correlation_top_k: int,
    ) -> Dict[str, Any]:
        """Build structured JSON export payload."""
        df, export_meta = self._load_task_features(task_id)
        report_builder = self._get_report_builder()
        return report_builder.build_json_report(
            task_id=task_id,
            features_df=df,
            export_meta=export_meta,
            include_sample_data=include_sample_data,
            sample_rows=sample_rows,
            include_statistics=include_statistics,
            include_correlation_top_k=include_correlation_top_k,
        )

    def export_markdown_report(
        self,
        task_id: str,
        max_token_budget: int,
        sections: Optional[List[str]],
        language: str,
    ) -> str:
        """Build markdown report for LLM/human consumption."""
        df, export_meta = self._load_task_features(task_id)
        report_builder = self._get_report_builder()
        return report_builder.build_markdown_report(
            task_id=task_id,
            features_df=df,
            export_meta=export_meta,
            max_token_budget=max_token_budget,
            sections=sections,
            language=language,
        )

    def _build_stats_rows(self, task_id: str) -> List[Dict[str, Any]]:
        """Compute per-feature statistics using vectorized pandas operations and cache the result.

        Replacing the previous per-column loop (N_features × 6 individual series calls)
        with a single-pass approach reduces runtime from ~180 s to < 5 s for large DataFrames.
        """
        if task_id in self._stats_cache:
            return self._stats_cache[task_id]

        features_df, _ = self._load_task_features(task_id)

        # Guard: pandas.describe() raises on DataFrame without columns.
        if features_df.shape[1] == 0:
            rows: List[Dict[str, Any]] = []
            self._stats_cache[task_id] = rows
            self._stats_name_sorted_cache[task_id] = rows
            self._stats_name_keys_cache[task_id] = []
            logger.info("Stats cached for task %s (0 features)", task_id)
            return rows

        # --- One-pass vectorized stats ------------------------------------------
        # df.describe() computes count/mean/std/min/25%/50%/75%/max in one sweep.
        # df.skew() and df.kurt() each make a single pass over the data.
        # df.isna().mean() is also a single pass.
        # Suppress pandas overflow warnings for extreme-valued features.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            desc = features_df.describe(percentiles=[0.25, 0.75]).T  # (n_features, 8)
            skewness_s = features_df.skew()
            kurtosis_s = features_df.kurt()
        nan_ratio_s = features_df.isna().mean()

        feature_meta = self._get_feature_metadata_map(task_id, list(features_df.columns))

        rows: List[Dict[str, Any]] = []
        for column in features_df.columns:
            meta = feature_meta.get(column)
            inferred_category = (meta or {}).get("category", "other")
            inferred_layer = (meta or {}).get("layer", "layer1")
            inferred_level = (meta or {}).get("level", "L1")
            col_desc = desc.loc[column] if column in desc.index else {}
            rows.append(
                {
                    "name": column,
                    "category": inferred_category,
                    "level": inferred_level,
                    "layer": inferred_layer,
                    "nan_ratio": self._safe_float(nan_ratio_s.get(column, 0.0)),
                    "mean": self._safe_float(col_desc.get("mean")),
                    "std": self._safe_float(col_desc.get("std")),
                    "min": self._safe_float(col_desc.get("min")),
                    "q25": self._safe_float(col_desc.get("25%")),
                    "median": self._safe_float(col_desc.get("50%")),
                    "q75": self._safe_float(col_desc.get("75%")),
                    "max": self._safe_float(col_desc.get("max")),
                    "skewness": self._safe_float(skewness_s.get(column)),
                    "kurtosis": self._safe_float(kurtosis_s.get(column)),
                    "is_stationary": None,
                    "adf_pvalue": None,
                }
            )

        self._stats_cache[task_id] = rows
        name_sorted_rows = sorted(rows, key=lambda item: str(item.get("name", "")))
        self._stats_name_sorted_cache[task_id] = name_sorted_rows
        self._stats_name_keys_cache[task_id] = [str(item.get("name", "")) for item in name_sorted_rows]
        logger.info("Stats cached for task %s (%d features)", task_id, len(rows))
        return rows

    def browse_features(
        self,
        task_id: str,
        offset: int,
        limit: int,
        sort_by: Optional[str],
        sort_order: str,
        category: Optional[str],
        level: Optional[str],
        search: Optional[str],
        detail_level: str = "full",
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Browse feature list with pagination/filter/sorting."""
        fp = ("browse_features", task_id, offset, limit, sort_by, sort_order,
              category or "", level or "", search or "", detail_level, cursor or "")
        return self._coalesce_browse(fp, lambda: self._browse_features_impl(
            task_id, offset, limit, sort_by, sort_order, category, level, search,
            detail_level, cursor,
        ))

    def _browse_features_impl(
        self,
        task_id: str,
        offset: int,
        limit: int,
        sort_by: Optional[str],
        sort_order: str,
        category: Optional[str],
        level: Optional[str],
        search: Optional[str],
        detail_level: str = "full",
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        if sort_by and sort_by not in {"nan_ratio", "std", "skewness", "kurtosis", "name", "mean"}:
            raise ValueError(f"Invalid sort_by: {sort_by}")
        if sort_order not in {"asc", "desc"}:
            raise ValueError(f"Invalid sort_order: {sort_order}")
        if detail_level not in {"full", "table", "names"}:
            raise ValueError(f"Invalid detail_level: {detail_level}")

        normalized_category = (category or "").strip()
        normalized_level = (level or "").strip()
        normalized_search = (search or "").strip()
        normalized_cursor = (cursor or "").strip() or None

        context: Optional[Dict[str, Any]] = None
        try:
            context = self._load_task_context(task_id)
        except Exception:
            context = None

        if context and context.get("is_cgsa") and detail_level in {"table", "names"}:
            return self._browse_cgsa_catalog_features(
                task_id=task_id,
                context=context,
                offset=offset,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                category=normalized_category,
                level=normalized_level,
                search=normalized_search,
                cursor=normalized_cursor,
                detail_level=detail_level,
            )

        # Fast path for the most common first-load pattern:
        # no filters + name ascending pagination.  This avoids repeated O(N log N)
        # sorting on each chunk request and keeps full accuracy/data unchanged.
        if (
            (not normalized_category)
            and (not normalized_level)
            and (not normalized_search)
            and ((sort_by is None) or (sort_by == "name"))
            and (sort_order == "asc")
        ):
            if task_id not in self._stats_cache:
                self._build_stats_rows(task_id)

            base_rows = self._stats_name_sorted_cache.get(task_id)
            if base_rows is None:
                base_rows = sorted(self._stats_cache.get(task_id, []), key=lambda item: str(item.get("name", "")))
                self._stats_name_sorted_cache[task_id] = base_rows
            name_keys = self._stats_name_keys_cache.get(task_id)
            if name_keys is None:
                name_keys = [str(item.get("name", "")) for item in base_rows]
                self._stats_name_keys_cache[task_id] = name_keys

            start_index = offset
            if normalized_cursor is not None:
                start_index = bisect_right(name_keys, normalized_cursor) + offset

            total = len(base_rows)
            page_rows = base_rows[start_index: start_index + limit]

            ADF_PAGE_LIMIT = 100
            if detail_level == "full" and HAS_STATSMODELS and len(page_rows) <= ADF_PAGE_LIMIT:
                # Fast-path browse only uses already-warmed ADF cache.
                # Avoid loading the full DataFrame when compute_if_missing=False.
                if self._adf_cache.get(task_id):
                    page_rows = self._enrich_rows_with_adf(
                        task_id=task_id,
                        rows=page_rows,
                        features_df=None,
                        compute_if_missing=False,
                    )

            # Warm additional ADF results in background for follow-up pagination.
            if detail_level == "full":
                self._start_adf_cache_warmup(task_id, reason="browse_features_fast_path")

            page_rows = self._project_browse_rows(page_rows, detail_level)

            has_more = (start_index + len(page_rows)) < total
            next_cursor = str(page_rows[-1].get("name", "")) if (page_rows and has_more) else None

            return {
                "total": total,
                "offset": start_index,
                "limit": limit,
                "cursor": normalized_cursor,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "filters_applied": {
                    "category": category,
                    "level": level,
                    "search": search,
                },
                "features": page_rows,
            }

        if normalized_cursor is not None:
            raise ValueError("cursor is only supported for name-asc browse without filters")

        # Use cached vectorized stats (first call builds and caches, subsequent calls are instant)
        rows = list(self._build_stats_rows(task_id))  # shallow copy so filters don't mutate cache

        if category:
            category_lower = category.lower()
            rows = [row for row in rows if str(row["category"]).lower() == category_lower]

        if level:
            level_upper = level.upper()
            rows = [row for row in rows if str(row["level"]).upper() == level_upper]

        if search:
            needle = search.lower()
            rows = [row for row in rows if needle in str(row["name"]).lower()]

        total = len(rows)
        reverse = sort_order == "desc"
        order_key = sort_by or "name"
        rows.sort(key=lambda item: self._sortable_value(item.get(order_key)), reverse=reverse)

        page_rows = rows[offset: offset + limit]

        # ADF test is expensive (~50-100 ms/feature). Skip when the page is large to
        # avoid blocking the response for bulk requests (e.g. limit=5000 initial load).
        ADF_PAGE_LIMIT = 100
        if detail_level == "full" and HAS_STATSMODELS and len(page_rows) <= ADF_PAGE_LIMIT:
            if self._adf_cache.get(task_id):
                page_rows = self._enrich_rows_with_adf(
                    task_id=task_id,
                    rows=page_rows,
                    features_df=None,
                    compute_if_missing=False,
                )

        # Warm additional ADF results in background for follow-up pagination.
        if detail_level == "full":
            self._start_adf_cache_warmup(task_id, reason="browse_features")

        page_rows = self._project_browse_rows(page_rows, detail_level)

        has_more = (offset + len(page_rows)) < total
        next_cursor = str(page_rows[-1].get("name", "")) if (page_rows and has_more and order_key == "name" and not reverse) else None

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "cursor": normalized_cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "filters_applied": {
                "category": category,
                "level": level,
                "search": search,
            },
            "features": page_rows,
        }

    @staticmethod
    def _project_browse_rows(rows: List[Dict[str, Any]], detail_level: str) -> List[Dict[str, Any]]:
        if detail_level == "full":
            return rows

        if detail_level == "names":
            return [{"name": row.get("name")} for row in rows]

        # table: only return columns currently required by Feature Table.
        keys = {
            "name",
            "category",
            "level",
            "layer",
            "nan_ratio",
            "mean",
            "std",
            "min",
            "q25",
            "median",
            "q75",
            "max",
            "skewness",
            "kurtosis",
        }
        projected: List[Dict[str, Any]] = []
        for row in rows:
            projected.append({k: row.get(k) for k in keys})
        return projected

    def _browse_cgsa_catalog_features(
        self,
        task_id: str,
        context: Dict[str, Any],
        offset: int,
        limit: int,
        sort_by: Optional[str],
        sort_order: str,
        category: str,
        level: str,
        search: str,
        cursor: Optional[str],
        detail_level: str,
    ) -> Dict[str, Any]:
        """Browse CGSA features from manifest/parquet metadata only.

        This is intentionally lighter than ``_build_stats_rows``: wide CGSA
        outputs can contain 100k+ columns, so computing mean/std/skew/kurt for
        every feature blocks the UI for minutes. The table/detail selectors only
        need names and parsed metadata; nan_ratio is available from parquet
        column statistics.
        """
        rows = list(self._build_cgsa_catalog_rows(task_id, context))

        if category:
            category_lower = category.lower()
            rows = [row for row in rows if str(row["category"]).lower() == category_lower]

        if level:
            level_upper = level.upper()
            rows = [row for row in rows if str(row["level"]).upper() == level_upper]

        if search:
            needle = search.lower()
            rows = [row for row in rows if needle in str(row["name"]).lower()]

        reverse = sort_order == "desc"
        order_key = sort_by or "name"
        if order_key not in {"nan_ratio", "std", "skewness", "kurtosis", "name", "mean"}:
            raise ValueError(f"Invalid sort_by: {order_key}")

        if order_key != "name":
            # Catalog rows carry nan_ratio=0 (parquet null_count ≠ IEEE-754 NaN).
            # Load the computed stats cache — 100% warmup means instant lookup after
            # the first call; the first call loads ~2k parquet parts (~1-2s, then cached).
            all_stats = self._load_cgsa_stats_mem(task_id, context)
            if not all_stats.empty and order_key in all_stats.columns:
                def _stats_sort_key(item: Dict[str, Any]) -> Any:
                    name = item.get("name", "")
                    if name in all_stats.index:
                        return self._sortable_value(all_stats.at[name, order_key])
                    return self._sortable_value(item.get(order_key))
                rows.sort(key=_stats_sort_key, reverse=reverse)
            else:
                rows.sort(key=lambda item: self._sortable_value(item.get(order_key)), reverse=reverse)
        else:
            rows.sort(key=lambda item: self._sortable_value(item.get(order_key)), reverse=reverse)

        start_index = offset
        if cursor is not None:
            if order_key != "name" or reverse or category or level or search:
                raise ValueError("cursor is only supported for name-asc browse without filters")
            name_keys = [str(item.get("name", "")) for item in rows]
            start_index = bisect_right(name_keys, cursor) + offset

        total = len(rows)
        page_rows = rows[start_index: start_index + limit]
        if detail_level == "table":
            page_rows = self._enrich_cgsa_catalog_page_stats(context, page_rows)
        has_more = (start_index + len(page_rows)) < total
        next_cursor = str(page_rows[-1].get("name", "")) if (page_rows and has_more and order_key == "name" and not reverse) else None

        return {
            "total": total,
            "offset": start_index,
            "limit": limit,
            "cursor": cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "filters_applied": {
                "category": category or None,
                "level": level or None,
                "search": search or None,
            },
            "features": self._project_browse_rows(page_rows, detail_level),
        }

    @staticmethod
    def _compute_feature_stats_fast(
        numeric: pd.DataFrame, q_sample: int = 3_000
    ) -> pd.DataFrame:
        """Compute 10 column-wise statistics with optimised numpy ops.

        Key optimisations vs naive pandas:
        * Single ``np.nanpercentile`` call for all 3 quantiles instead of three
          separate ``.quantile()`` calls (each of which sorts the data
          independently → 3× the work).
        * Direct numpy reductions for mean/std/min/max/nan_ratio to avoid the
          per-column Python overhead of pandas aggregation methods.
        * Approximate quantiles via a systematic even-spaced sample when
          n_rows > q_sample.  Sorting q_sample instead of 52 000 rows per
          column is ~(52k/q_sample)× faster with <1 % error for typical
          financial time-series distributions.
        * Skewness and kurtosis still use pandas (they already delegate to
          numpy internally and handle edge-cases such as constant columns).

        Parameters
        ----------
        q_sample:
            Row count used for the approximate quantile sample.  Controlled
            per hardware tier via ``hardware_utils._CGSA_STATS_Q_SAMPLE_BY_TIER``.
        """
        arr = numeric.to_numpy(dtype=np.float64, na_value=np.nan)

        # Basic stats — each is a single vectorised numpy pass (full data).
        nan_ratio = np.isnan(arr).mean(axis=0)
        mean_vals = np.nanmean(arr, axis=0)
        std_vals  = np.nanstd(arr, axis=0, ddof=1)
        min_vals  = np.nanmin(arr, axis=0)
        max_vals  = np.nanmax(arr, axis=0)

        # Approximate quantiles from an evenly-spaced sample.
        # min/max are always exact (above); only q25/median/q75 use the sample.
        n_rows = arr.shape[0]
        if n_rows > q_sample:
            q_idx = np.round(np.linspace(0, n_rows - 1, q_sample)).astype(np.intp)
            arr_q = arr[q_idx, :]
        else:
            arr_q = arr
        qs = np.nanpercentile(arr_q, [25.0, 50.0, 75.0], axis=0)  # (3, n_cols)

        # Skew / kurt: delegate to pandas which handles constant-column NaN
        # and unbiased correction automatically.
        skew_vals = numeric.skew(skipna=True).to_numpy()
        kurt_vals = numeric.kurt(skipna=True).to_numpy()

        return pd.DataFrame(
            {
                "nan_ratio": nan_ratio,
                "mean":      mean_vals,
                "std":       std_vals,
                "min":       min_vals,
                "q25":       qs[0],
                "median":    qs[1],
                "q75":       qs[2],
                "max":       max_vals,
                "skewness":  skew_vals,
                "kurtosis":  kurt_vals,
            },
            index=numeric.columns,
        )

    def _enrich_cgsa_catalog_page_stats(
        self,
        context: Dict[str, Any],
        rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compute statistics for the current CGSA page using disk/memory cache.

        Already-computed feature stats are served instantly from the in-memory
        cache (backed by feature_stats_cache.parquet on disk). Only features that
        have never been computed trigger a parquet read, so repeat searches for
        the same features are nearly instant.
        """
        if not rows:
            return rows

        names = [str(row.get("name", "")) for row in rows if row.get("name")]
        if not names:
            return rows

        task_id = str(context.get("task_id", ""))
        all_stats = self._load_cgsa_stats_mem(task_id, context)

        # Only load parquet for features not yet in the cache.
        if not all_stats.empty:
            missing_names = [n for n in names if n not in all_stats.index]
        else:
            missing_names = names

        if missing_names:
            # Cap synchronous computation to keep the search response fast.
            # Features beyond the cap are returned with null stats ("-" in the
            # UI); the background warmup thread fills them in so the next search
            # for the same keyword is served entirely from cache.
            sync_batch = missing_names[: self._cgsa_stats_sync_cap]
            n_deferred = len(missing_names) - len(sync_batch)
            if n_deferred > 0:
                logger.debug(
                    "CGSA stats: %d features deferred to warmup for task %s (%d computed now)",
                    n_deferred, task_id, len(sync_batch),
                )
                # Ensure the warmup thread is running so deferred features are
                # computed as soon as possible.
                self._start_cgsa_stats_warmup(task_id, context)
            try:
                df, _total_rows = self._load_cgsa_selected_df(context, sync_batch)
                numeric = df.replace([np.inf, -np.inf], np.nan).astype("float64", copy=False)
                new_df = self._compute_feature_stats_fast(numeric, self._cgsa_stats_q_sample)
                new_df.index.name = "name"
                # Persist to disk and update in-memory cache.
                self._persist_cgsa_stats(task_id, context, new_df)
                with self._lock:
                    all_stats = self._cgsa_stats_mem_cache.get(task_id, new_df)
            except Exception as exc:
                logger.warning("CGSA page stats failed for task %s: %s", task_id, exc)

        enriched: List[Dict[str, Any]] = []
        stat_keys = ("nan_ratio", "mean", "std", "min", "q25", "median", "q75", "max", "skewness", "kurtosis")
        for row in rows:
            item = dict(row)
            name = str(item.get("name", ""))
            if not all_stats.empty and name in all_stats.index:
                row_stats = all_stats.loc[name]
                for key in stat_keys:
                    item[key] = self._safe_float(row_stats.get(key))
            enriched.append(item)
        return enriched

    def _build_cgsa_catalog_rows(self, task_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        cached = self._cgsa_catalog_cache.get(task_id)
        if cached is not None:
            return cached

        fast = self._load_cgsa_summary_fast(context)
        if fast is None:
            raise FileNotFoundError(f"CGSA metadata unavailable for task {task_id}")

        disk_cached = self._load_cgsa_catalog_disk_cache(task_id, context, fast)
        if disk_cached is not None:
            return disk_cached

        columns: List[str] = fast["columns"]
        nan_ratios: pd.Series = fast["nan_ratios"]
        metadata_map = self._get_feature_metadata_map(task_id, columns)

        rows: List[Dict[str, Any]] = []
        for name in columns:
            meta = metadata_map[name]
            rows.append({
                "name": name,
                "category": meta["category"],
                "level": meta["level"],
                "layer": meta["layer"],
                "nan_ratio": self._safe_float(nan_ratios.get(name, 0.0)) or 0.0,
                "mean": None,
                "std": None,
                "min": None,
                "q25": None,
                "median": None,
                "q75": None,
                "max": None,
                "skewness": None,
                "kurtosis": None,
                "is_stationary": None,
                "adf_pvalue": None,
            })

        self._cgsa_catalog_cache[task_id] = rows
        self._cgsa_column_path_cache[task_id] = fast["column_to_path"]
        self._persist_cgsa_catalog_cache(context, fast, rows)
        logger.info("CGSA catalog cached for task %s (%d features)", task_id, len(rows))
        return rows

    def _get_cgsa_catalog_cache_paths(self, context: Dict[str, Any]) -> tuple[Optional[Path], Optional[Path]]:
        manifest_dir = context.get("manifest_dir")
        if manifest_dir is None:
            return None, None
        base_dir = Path(manifest_dir)
        return base_dir / self._CGSA_CATALOG_CACHE_NAME, base_dir / self._CGSA_CATALOG_CACHE_META_NAME

    def _cgsa_catalog_cache_signature(self, context: Dict[str, Any], fast: Dict[str, Any]) -> Dict[str, Any]:
        manifest = context.get("manifest") or {}
        return {
            "version": 2,  # v2: nan_ratio populated from parquet null stats
            "feature_schema_hash": manifest.get("feature_schema_hash") or manifest.get("schema_hash") or "",
            "total_features": int(len(fast.get("columns") or [])),
            "total_rows": int(fast.get("total_rows") or 0),
            "manifest_path": str(context.get("file_path") or ""),
        }

    def _load_cgsa_catalog_disk_cache(
        self,
        task_id: str,
        context: Dict[str, Any],
        fast: Dict[str, Any],
    ) -> Optional[List[Dict[str, Any]]]:
        cache_path, meta_path = self._get_cgsa_catalog_cache_paths(context)
        if cache_path is None or meta_path is None or not cache_path.exists() or not meta_path.exists():
            return None
        try:
            expected = self._cgsa_catalog_cache_signature(context, fast)
            actual = json.loads(meta_path.read_text(encoding="utf-8"))
            if actual != expected:
                return None
            frame = pd.read_parquet(str(cache_path))
            frame = frame.where(pd.notna(frame), None)
            rows = frame.to_dict(orient="records")
            # Guard: if the cache predates nan_ratio, backfill from fast summary so
            # sort-by-nan_ratio works correctly without forcing a full rebuild.
            nan_ratios = fast.get("nan_ratios")
            if nan_ratios is not None and rows and rows[0].get("nan_ratio") is None:
                for row in rows:
                    name = row.get("name", "")
                    row["nan_ratio"] = self._safe_float(nan_ratios.get(name, 0.0)) or 0.0
            self._cgsa_catalog_cache[task_id] = rows
            self._cgsa_column_path_cache[task_id] = fast["column_to_path"]
            logger.info("CGSA catalog disk cache hit for task %s (%d features)", task_id, len(rows))
            return rows
        except Exception as exc:
            logger.warning("Failed to load CGSA catalog cache for task %s: %s", task_id, exc)
            return None

    def _persist_cgsa_catalog_cache(
        self,
        context: Dict[str, Any],
        fast: Dict[str, Any],
        rows: List[Dict[str, Any]],
    ) -> None:
        cache_path, meta_path = self._get_cgsa_catalog_cache_paths(context)
        if cache_path is None or meta_path is None:
            return
        tmp_cache: Optional[Path] = None
        tmp_meta: Optional[Path] = None
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_cache = cache_path.with_suffix(cache_path.suffix + f".{uuid.uuid4().hex}.tmp")
            tmp_meta = meta_path.with_suffix(meta_path.suffix + f".{uuid.uuid4().hex}.tmp")
            pd.DataFrame(rows).to_parquet(str(tmp_cache), index=False, compression="snappy")
            tmp_meta.write_text(
                json.dumps(self._cgsa_catalog_cache_signature(context, fast), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp_cache, cache_path)
            os.replace(tmp_meta, meta_path)
        except Exception as exc:
            logger.warning("Failed to persist CGSA catalog cache: %s", exc)
        finally:
            for tmp_path in (tmp_cache, tmp_meta):
                if tmp_path is not None and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass

    def _start_cgsa_catalog_warmup(self, task_id: str, context: Dict[str, Any]) -> None:
        with self._lock:
            if task_id in self._cgsa_catalog_cache or task_id in self._cgsa_catalog_warming_tasks:
                return
            self._cgsa_catalog_warming_tasks.add(task_id)

        def _worker() -> None:
            try:
                self._build_cgsa_catalog_rows(task_id, context)
            except Exception as exc:
                logger.debug("CGSA catalog warmup failed for task %s: %s", task_id, exc)
            finally:
                with self._lock:
                    self._cgsa_catalog_warming_tasks.discard(task_id)

        thread = threading.Thread(
            target=_worker,
            daemon=True,
            name=f"cgsa-catalog-warm-{task_id[:8]}",
        )
        thread.start()

    def _start_data_quality_warmup(self, task_id: str, context: Dict[str, Any]) -> None:
        """Background-bake data_quality.json so the dashboard opens instantly.

        No-op when the cache already exists or a warmup is already running.
        Runs in a daemon thread; pyarrow.compute kernels release the GIL so
        this does not throttle concurrent API calls meaningfully. If the user
        opens the Data Quality tab before the bake finishes, browse_data_quality
        falls back to the existing synchronous scan path.
        """
        if not context or not context.get("is_cgsa"):
            return
        cache_path = self._data_quality_cache_path(context)
        if cache_path is not None and cache_path.exists():
            return
        with self._lock:
            if task_id in self._data_quality_warming_tasks:
                return
            self._data_quality_warming_tasks.add(task_id)

        def _worker() -> None:
            try:
                fast = self._load_cgsa_summary_fast(context)
                if fast is None:
                    return
                report = self._build_data_quality_cgsa(context, fast)
                self._persist_data_quality_disk_cache(context, report)
                logger.info(
                    "data_quality background bake completed for task %s", task_id,
                )
            except Exception as exc:
                logger.debug(
                    "data_quality background bake failed for task %s: %s", task_id, exc,
                )
            finally:
                with self._lock:
                    self._data_quality_warming_tasks.discard(task_id)

        thread = threading.Thread(
            target=_worker,
            daemon=True,
            name=f"dq-warm-{task_id[:8]}",
        )
        thread.start()

    # ------------------------------------------------------------------
    # CGSA feature stats disk-cache helpers
    # ------------------------------------------------------------------

    def _get_cgsa_stats_cache_path(self, context: Dict[str, Any]) -> Optional[Path]:
        """Return path to the on-disk CGSA stats parquet, or None if unavailable."""
        manifest_dir = context.get("manifest_dir")
        if manifest_dir is None:
            return None
        return Path(manifest_dir) / self._CGSA_STATS_CACHE_NAME

    def _get_cgsa_stats_parts_dir(self, context: Dict[str, Any]) -> Optional[Path]:
        manifest_dir = context.get("manifest_dir")
        if manifest_dir is None:
            return None
        return Path(manifest_dir) / self._CGSA_STATS_PARTS_DIR_NAME

    def _load_cgsa_stats_mem(self, task_id: str, context: Dict[str, Any]) -> pd.DataFrame:
        """Return the in-memory CGSA stats DataFrame, loading from disk on first call.

        DataFrame is indexed by feature name with columns:
        nan_ratio / mean / std / min / q25 / median / q75 / max / skewness / kurtosis.
        Returns an empty DataFrame when no cache exists yet.
        """
        with self._lock:
            if task_id in self._cgsa_stats_mem_cache:
                return self._cgsa_stats_mem_cache[task_id]
            cache_path = self._get_cgsa_stats_cache_path(context)

        frames: List[pd.DataFrame] = []
        if cache_path is not None and cache_path.exists():
            try:
                frames.append(pd.read_parquet(str(cache_path)))
            except Exception as exc:
                logger.warning("Failed to load CGSA stats cache %s: %s", cache_path, exc)

        parts_dir = self._get_cgsa_stats_parts_dir(context)
        if parts_dir is not None and parts_dir.exists():
            for part_path in sorted(parts_dir.glob("*.parquet")):
                try:
                    frames.append(pd.read_parquet(str(part_path)))
                except Exception as exc:
                    logger.debug("Failed to load CGSA stats cache part %s: %s", part_path, exc)

        if frames:
            df = pd.concat(frames, axis=0, ignore_index=True)
            if "name" in df.columns:
                df = df.drop_duplicates(subset=["name"], keep="last").set_index("name")
            with self._lock:
                if task_id not in self._cgsa_stats_mem_cache:
                    self._cgsa_stats_mem_cache[task_id] = df
                return self._cgsa_stats_mem_cache[task_id]

        return pd.DataFrame()

    def _persist_cgsa_stats(
        self, task_id: str, context: Dict[str, Any], new_df: pd.DataFrame
    ) -> None:
        """Merge new_df into the in-memory cache and write to disk.

        Only features not already in the cache are added, so repeated calls are
        idempotent and the file does not grow with duplicate rows.

        The disk write is kept inside the lock so that concurrent warmup workers
        cannot write to the same file simultaneously and corrupt it.
        """
        with self._lock:
            existing = self._cgsa_stats_mem_cache.get(task_id, pd.DataFrame())
            if not existing.empty:
                new_only = new_df[~new_df.index.isin(existing.index)]
                if new_only.empty:
                    return  # Nothing new to persist
                merged = pd.concat([existing, new_only])
            else:
                merged = new_df.copy()
            self._cgsa_stats_mem_cache[task_id] = merged
            parts_dir = self._get_cgsa_stats_parts_dir(context)
            if parts_dir is not None:
                try:
                    parts_dir.mkdir(parents=True, exist_ok=True)
                    out = new_only.copy() if not existing.empty else new_df.copy()
                    out.index.name = "name"
                    part_path = parts_dir / f"stats_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:8]}.parquet"
                    out.reset_index().to_parquet(str(part_path), index=False, compression="snappy")
                    logger.debug(
                        "Persisted CGSA stats cache part for task %s (%d new, %d total)",
                        task_id, len(out), len(merged),
                    )
                except Exception as exc:
                    logger.warning("Failed to persist CGSA stats cache for task %s: %s", task_id, exc)

    def _start_cgsa_stats_warmup(self, task_id: str, context: Dict[str, Any]) -> None:
        """Start a background thread that progressively computes stats for all CGSA features.

        Groups are processed in parallel (up to cgsa_stats_warmup_workers workers) so the
        full cache is built in a fraction of the sequential time.  Results are
        persisted to disk after each group so the cache grows incrementally and
        survives API restarts.

        P0-C: Warmup yields to any in-flight foreground request and starts at
        a single worker on 8GB tier so a tab load is never slowed by the
        background thread.
        """
        # On 8GB tier (configured warmup_workers <= 2) cap at 1 worker; otherwise
        # use the configured value but never exceed 4 to avoid I/O contention.
        if self._cgsa_stats_warmup_workers <= 2:
            _WARMUP_WORKERS = 1
        else:
            _WARMUP_WORKERS = min(4, self._cgsa_stats_warmup_workers)
        # Delay launch so the first browse_summary response is not slowed by
        # the warmup thread spinning up at the same instant.
        _STARTUP_DELAY_SEC = 30.0

        with self._lock:
            if task_id in self._cgsa_stats_warming_tasks:
                return
            self._cgsa_stats_warming_tasks.add(task_id)

        def _process_group(group_meta: Any) -> int:
            """Read one parquet group, compute stats, persist; return # new features."""
            # P0-C: yield while a user-facing tab is actively waiting on a browse_*.
            while self._warmup_should_yield():
                time.sleep(0.5)
            import pyarrow.parquet as _pq_w
            if not isinstance(group_meta, dict):
                return 0
            manifest_dir: Optional[Path] = context.get("manifest_dir")
            relative = group_meta.get("path") or group_meta.get("file")
            if not relative or manifest_dir is None:
                return 0
            parquet_path = manifest_dir / relative
            cols: List[str] = list(group_meta.get("columns") or [])
            if not cols:
                return 0
            # Skip features already cached (checked under lock for thread safety).
            with self._lock:
                existing = self._cgsa_stats_mem_cache.get(task_id, pd.DataFrame())
            if not existing.empty:
                cols = [c for c in cols if c not in existing.index]
            if not cols:
                return 0
            try:
                table = _pq_w.read_table(str(parquet_path), columns=cols)
                df = table.to_pandas(self_destruct=True)
                numeric = df.replace([np.inf, -np.inf], np.nan).astype("float64", copy=False)
                new_df = self._compute_feature_stats_fast(numeric, self._cgsa_stats_q_sample)
                new_df.index.name = "name"
                self._persist_cgsa_stats(task_id, context, new_df)
                return len(cols)
            except Exception as exc:
                pname = parquet_path.name
                logger.debug("CGSA stats warmup: group %s skipped (%s)", pname, exc)
                return 0

        def _worker() -> None:
            from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed as _ac
            try:
                # P0-C: pause briefly before kicking off so the initial
                # browse_summary response is not contended by warmup I/O.
                time.sleep(_STARTUP_DELAY_SEC)
                manifest = context.get("manifest") or {}
                groups_raw = manifest.get("groups", {})
                if isinstance(groups_raw, dict):
                    groups_items: List[Any] = list(groups_raw.values())
                else:
                    groups_items = list(groups_raw) if groups_raw else []

                total_persisted = 0
                with _TPE(max_workers=_WARMUP_WORKERS, thread_name_prefix="cgsa-wm") as pool:
                    futures = {pool.submit(_process_group, gm): gm for gm in groups_items}
                    for future in _ac(futures):
                        try:
                            total_persisted += future.result()
                        except Exception as exc:
                            logger.debug("CGSA warmup future failed: %s", exc)

                logger.info(
                    "CGSA stats warmup completed for task %s — %d new features cached",
                    task_id, total_persisted,
                )
            except Exception as exc:
                logger.warning("CGSA stats warmup failed for task %s: %s", task_id, exc, exc_info=True)
            finally:
                with self._lock:
                    self._cgsa_stats_warming_tasks.discard(task_id)

        thread = threading.Thread(
            target=_worker,
            daemon=True,
            name=f"cgsa-stats-warm-{task_id[:8]}",
        )
        thread.start()
        logger.info(
            "CGSA stats warmup started for task %s (parallel_workers=%d)",
            task_id, _WARMUP_WORKERS,
        )

    def browse_feature_data(
        self,
        task_id: str,
        features: List[str],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Return time series data for selected features."""
        fp = ("browse_feature_data", task_id, tuple(features), offset, limit)
        return self._coalesce_browse(fp, lambda: self._browse_feature_data_impl(
            task_id, features, offset, limit,
        ))

    def _browse_feature_data_impl(
        self,
        task_id: str,
        features: List[str],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        if len(features) == 0:
            raise ValueError("features cannot be empty")
        if len(features) > 20:
            raise ValueError("features count exceeds limit 20")

        context = self._load_task_context(task_id)
        data = self._load_selected_feature_rows(
            context=context,
            selected_features=features,
            offset=offset,
            limit=limit,
        )
        return data

    def browse_correlation(
        self,
        task_id: str,
        features: List[str],
        method: str,
    ) -> Dict[str, Any]:
        """Return feature correlation matrix for selected features."""
        fp = ("browse_correlation", task_id, tuple(features), method)
        return self._coalesce_browse(fp, lambda: self._browse_correlation_impl(
            task_id, features, method,
        ))

    def _browse_correlation_impl(
        self,
        task_id: str,
        features: List[str],
        method: str,
    ) -> Dict[str, Any]:
        if len(features) == 0:
            raise ValueError("features cannot be empty")
        if len(features) > 50:
            raise ValueError("features count exceeds limit 50")
        if method not in {"pearson", "spearman", "kendall"}:
            raise ValueError(f"Invalid correlation method: {method}")

        context = self._load_task_context(task_id)
        if context.get("is_cgsa"):
            df, _total_rows = self._load_cgsa_selected_df(context, features)
        else:
            df, _ = self._load_task_features(task_id)
        missing = [name for name in features if name not in df.columns]
        if missing:
            raise ValueError(f"Invalid features: {missing}")

        selected = df[features].replace([np.inf, -np.inf], np.nan)
        corr_df = selected.corr(method=method).fillna(0.0)

        return {
            "features": list(corr_df.columns),
            "method": method,
            "matrix": corr_df.to_numpy().tolist(),
        }

    def browse_vif(self, task_id: str, features: List[str]) -> Dict[str, Any]:
        """Return VIF (Variance Inflation Factor) for selected features.

        VIF_i = diagonal element of inverse(correlation_matrix).
        VIF < 5: stable, 5-10: warning, >10: severe multicollinearity.
        """
        fp = ("browse_vif", task_id, tuple(features))
        return self._coalesce_browse(fp, lambda: self._browse_vif_impl(task_id, features))

    def _browse_vif_impl(self, task_id: str, features: List[str]) -> Dict[str, Any]:
        if len(features) < 2:
            raise ValueError("VIF requires at least 2 features")
        if len(features) > 50:
            raise ValueError("features count exceeds limit 50")

        context = self._load_task_context(task_id)
        if context.get("is_cgsa"):
            df, _total_rows = self._load_cgsa_selected_df(context, features)
        else:
            df, _ = self._load_task_features(task_id)
        missing = [name for name in features if name not in df.columns]
        if missing:
            raise ValueError(f"Invalid features: {missing}")

        selected_df = (
            df[features]
            .replace([np.inf, -np.inf], np.nan)
            .select_dtypes(include=[np.number])
            .dropna(axis=1, how="all")
        )
        if selected_df.shape[1] < 2:
            return {"items": []}

        corr_matrix = selected_df.corr(method="pearson").fillna(0.0).to_numpy(dtype=float)
        # 加微小正則化避免奇異矩陣
        corr_matrix = corr_matrix + np.eye(corr_matrix.shape[0]) * 1e-6
        inv_corr = np.linalg.pinv(corr_matrix)
        vif_values = np.diag(inv_corr)

        items = []
        for feature_name, vif_val in zip(list(selected_df.columns), vif_values):
            value = float(max(vif_val, 0.0))
            if value < 5.0:
                status = "stable"
            elif value < 10.0:
                status = "warning"
            else:
                status = "severe"
            items.append({"feature_name": feature_name, "vif": round(value, 3), "status": status})

        items.sort(key=lambda item: item["vif"], reverse=True)
        return {"items": items}

    def browse_distribution(
        self,
        task_id: str,
        feature: str,
        n_bins: int,
        compute_adf: bool = False,
    ) -> Dict[str, Any]:
        """Return histogram payload for one feature.

        ``compute_adf=False`` (default) skips the costly statsmodels ADF call;
        the front-end provides an explicit "Run ADF" button so cold-load
        latency is no longer dominated by stationarity tests.
        """
        fp = ("browse_distribution", task_id, feature, n_bins, bool(compute_adf))
        return self._coalesce_browse(fp, lambda: self._browse_distribution_impl(
            task_id, feature, n_bins, compute_adf,
        ))

    def _browse_distribution_impl(
        self,
        task_id: str,
        feature: str,
        n_bins: int,
        compute_adf: bool = False,
    ) -> Dict[str, Any]:
        context = self._load_task_context(task_id)
        if context.get("is_cgsa"):
            df, _total_rows = self._load_cgsa_selected_df(context, [feature])
        else:
            df, _ = self._load_task_features(task_id)
        if feature not in df.columns:
            raise ValueError(f"Invalid feature: {feature}")

        # 與 Feature Table (_enrich_cgsa_catalog_page_stats) 保持一致的清理流程：
        # 1. 強制轉 numeric（object 欄位轉 NaN）
        # 2. ±inf 替換為 NaN（float16 overflow、計算溢出等情況）
        # 3. 轉 float64（避免 float16 精度損失導致 mean/std 計算誤差）
        # nan_ratio 保留原始資料的 NaN 計算（不含 inf→NaN 的偽造缺失）
        raw_nan_ratio = float(df[feature].isna().mean())
        clean = pd.to_numeric(df[feature], errors="coerce").replace([np.inf, -np.inf], np.nan).astype("float64")
        series = clean.dropna()
        if series.empty:
            bins = np.array([])
            edges = np.array([])
        else:
            bins, edges = np.histogram(series.to_numpy(), bins=n_bins)

        adf_pvalue = (
            self._get_adf_pvalue(task_id=task_id, feature_name=feature, features_df=df)
            if (compute_adf and HAS_STATSMODELS)
            else None
        )

        return {
            "feature": feature,
            "n_bins": n_bins,
            "bins": bins.tolist(),
            "edges": edges.tolist(),
            "stats": {
                "count": int(series.shape[0]),
                "nan_ratio": raw_nan_ratio,
                "mean": self._safe_float(clean.mean()),
                "std": self._safe_float(clean.std()),
                "min": self._safe_float(clean.min()),
                "q25": self._safe_float(clean.quantile(0.25)),
                "median": self._safe_float(clean.median()),
                "q75": self._safe_float(clean.quantile(0.75)),
                "max": self._safe_float(clean.max()),
                "skewness": self._safe_float(clean.skew()),
                "kurtosis": self._safe_float(clean.kurt()),
                "adf_pvalue": adf_pvalue,
                "is_stationary": adf_pvalue is not None and adf_pvalue < 0.05,
            },
        }

    def browse_nan_pattern(self, task_id: str, sample_features: int) -> Dict[str, Any]:
        """Return missing-value matrix payload for sampled features.

        CGSA fast-path: reads NaN ratios from parquet metadata (no data load),
        then reads ONLY the top-N columns by NaN ratio to build the matrix.
        This avoids loading the full 453k-column DataFrame which causes OOM.
        """
        fp = ("browse_nan_pattern", task_id, sample_features)
        return self._coalesce_browse(fp, lambda: self._browse_nan_pattern_impl(
            task_id, sample_features,
        ))

    def _browse_nan_pattern_impl(self, task_id: str, sample_features: int) -> Dict[str, Any]:
        # --- CGSA fast-path -------------------------------------------------
        context: Optional[Dict[str, Any]] = None
        try:
            context = self._load_task_context(task_id)
        except Exception:
            context = None

        if context and context.get("is_cgsa"):
            try:
                fast = self._load_cgsa_summary_fast(context)
            except Exception as exc:
                logger.warning("browse_nan_pattern CGSA fast-path failed for %s: %s", task_id, exc)
                fast = None

            if fast is not None:
                nan_ratios_series: pd.Series = fast["nan_ratios"].sort_values(ascending=False)
                column_to_path: Dict[str, Any] = fast["column_to_path"]
                selected = list(nan_ratios_series.index[:sample_features])
                if not selected:
                    return {"features": [], "timestamps": [], "matrix": [], "nan_ratios": []}

                # Read only the selected columns — avoids full DataFrame load
                selected_df = self._load_cgsa_columns_subset(column_to_path, selected)
                if selected_df.empty:
                    return {"features": [], "timestamps": [], "matrix": [], "nan_ratios": []}

                timestamps_total = len(selected_df)
                if timestamps_total > self._NAN_PATTERN_MAX_STEPS:
                    step = max(1, timestamps_total // self._NAN_PATTERN_MAX_STEPS)
                    selected_df = selected_df.iloc[::step].head(self._NAN_PATTERN_MAX_STEPS)
                nan_arr = selected_df.isna().to_numpy()  # [T, N]
                matrix = nan_arr.T.tolist()              # [N, T] — one row per feature
                timestamps = [str(idx) for idx in selected_df.index.tolist()]
                return {
                    "features": selected,
                    "timestamps": timestamps,
                    "timestamps_total": timestamps_total,
                    "matrix": matrix,
                    "nan_ratios": [float(nan_ratios_series[name]) for name in selected],
                }

        # --- Fallback: full load (HDF5 / small tasks) -----------------------
        df, _ = self._load_task_features(task_id)
        if df.empty or df.shape[1] == 0:
            return {"features": [], "timestamps": [], "matrix": [], "nan_ratios": []}

        nan_ratio_series = df.isna().mean().sort_values(ascending=False)
        selected = list(nan_ratio_series.index[:sample_features])
        selected_df = df[selected]

        timestamps_total = len(selected_df)
        if timestamps_total > self._NAN_PATTERN_MAX_STEPS:
            step = max(1, timestamps_total // self._NAN_PATTERN_MAX_STEPS)
            selected_df = selected_df.iloc[::step].head(self._NAN_PATTERN_MAX_STEPS)
        nan_arr = selected_df.isna().to_numpy()  # [T, N]
        matrix = nan_arr.T.tolist()              # [N, T] — one row per feature
        timestamps = [str(index) for index in selected_df.index.tolist()]

        return {
            "features": selected,
            "timestamps": timestamps,
            "timestamps_total": timestamps_total,
            "matrix": matrix,
            "nan_ratios": [float(nan_ratio_series[name]) for name in selected],
        }

    # ------------------------------------------------------------------
    # Data Quality Diagnostics
    # ------------------------------------------------------------------
    _DATA_QUALITY_TIMELINE_POINTS: int = 200
    _DATA_QUALITY_SCATTERED_CAP: int = 5000   # 115k warmup features — cap to keep JSON sane
    _DATA_QUALITY_HIGH_NAN_THRESHOLD: float = 0.05
    _DATA_QUALITY_WARMUP_PCTILE: float = 0.95
    _DATA_QUALITY_CACHE_NAME: str = "data_quality.json"
    # Bump when the report schema changes so stale on-disk caches are invalidated.
    # dq_v2: coverage_timeline rebuilt from first/last_valid (was dead all-1.0);
    #        added counts.warmup_only_high_nan / counts.real_problem + group_breakdown.
    _DATA_QUALITY_SCHEMA_VERSION: str = "dq_v6"
    # Bucket bounds for warmup (lookback) length, in bars.
    _DATA_QUALITY_WARMUP_BUCKETS: List[tuple] = [
        ("0", 0, 0),
        ("1-50", 1, 50),
        ("51-200", 51, 200),
        ("201-1000", 201, 1000),
        (">1000", 1001, None),
    ]

    def browse_data_quality(self, task_id: str) -> Dict[str, Any]:
        """Comprehensive data-quality diagnostics report — coalesced wrapper."""
        fp = ("browse_data_quality", task_id)
        return self._coalesce_browse(fp, lambda: self._browse_data_quality_impl(task_id))

    def _browse_data_quality_impl(self, task_id: str) -> Dict[str, Any]:
        """Comprehensive data-quality diagnostics report.

        Industry-standard categories (per `missingno` / quant practice):
          1. Warmup NaN distribution — leading-NaN length per feature, driven by
             rolling-window lookbacks.
          2. Mid-series holes — NaN inside the valid range (data corruption /
             exchange downtime / index misalignment).
          3. Trailing NaN — NaN at the tail (live/streaming truncation).
          4. Scattered / high NaN — overall NaN ratio above threshold.
          5. Cross-sectional coverage — % features available per timestep,
             used to pick a sane training start.
        """
        context: Optional[Dict[str, Any]] = None
        try:
            context = self._load_task_context(task_id)
        except Exception:
            context = None

        if context and context.get("is_cgsa"):
            cached = self._load_data_quality_disk_cache(context)
            if cached is not None:
                return cached
            try:
                fast = self._load_cgsa_summary_fast(context)
            except Exception as exc:
                logger.warning("browse_data_quality CGSA fast-path failed for %s: %s", task_id, exc)
                fast = None
            if fast is not None:
                report = self._build_data_quality_cgsa(context, fast)
                self._persist_data_quality_disk_cache(context, report)
                return report

        df, _ = self._load_task_features(task_id)
        return self._build_data_quality_inmemory(df)

    def _data_quality_cache_path(self, context: Dict[str, Any]) -> Optional[Path]:
        manifest_dir = context.get("manifest_dir")
        if manifest_dir is None:
            return None
        return Path(manifest_dir) / self._DATA_QUALITY_CACHE_NAME

    def _load_data_quality_disk_cache(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        path = self._data_quality_cache_path(context)
        if path is None or not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                cached = json.load(f)
        except Exception as exc:
            logger.warning("data_quality cache load failed (%s): %s", path, exc)
            return None
        # Invalidate stale-schema caches (e.g. pre-dq_v2 with the dead all-1.0
        # coverage timeline). Returning None forces a recompute + overwrite.
        if cached.get("schema_version") != self._DATA_QUALITY_SCHEMA_VERSION:
            logger.info(
                "data_quality cache schema mismatch (%s != %s) → recompute: %s",
                cached.get("schema_version"), self._DATA_QUALITY_SCHEMA_VERSION, path,
            )
            return None
        return cached

    def _persist_data_quality_disk_cache(self, context: Dict[str, Any], report: Dict[str, Any]) -> None:
        path = self._data_quality_cache_path(context)
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False)
            tmp.replace(path)
        except Exception as exc:
            logger.warning("data_quality cache persist failed (%s): %s", path, exc)

    def _build_data_quality_cgsa(
        self,
        context: Dict[str, Any],
        fast: Dict[str, Any],
    ) -> Dict[str, Any]:
        """CGSA path: scan actual parquet data to detect IEEE-754 NaN values.

        Why we cannot trust ``fast['nan_ratios']`` here:
        parquet ``null_count`` only tracks the Arrow validity bitmap; it does
        NOT count IEEE-754 NaN bit patterns inside float columns.  CGSA writes
        NaN as a regular float value (no validity flag), so metadata reports
        zero nulls even when ``np.isnan`` finds many.  Feature Table catches
        this via ``np.isnan`` over loaded data; we must do the same.

        Memory strategy: stream each parquet file, then within each file read
        columns in batches to bound peak memory.  Per batch we go straight
        through Arrow's NumPy converter (skipping the pandas DataFrame copy)
        to roughly halve scan time on wide CGSA tasks.
        """
        import pyarrow.parquet as pq
        import pyarrow.compute as pc
        import time

        total_rows: int = int(fast["total_rows"])
        columns: List[str] = list(fast["columns"])
        column_to_path: Dict[str, Path] = fast["column_to_path"]
        n_features = len(columns)

        if total_rows == 0 or n_features == 0:
            return self._empty_data_quality_report()

        first_valid_map: Dict[str, int] = {c: 0 for c in columns}
        last_valid_map: Dict[str, int] = {c: total_rows - 1 for c in columns}
        real_nan_count: Dict[str, int] = {}
        row_nan_count = np.zeros(total_rows, dtype=np.int64)

        path_to_cols: Dict[Path, List[str]] = {}
        for col in columns:
            path = column_to_path.get(col)
            if path is None:
                continue
            path_to_cols.setdefault(path, []).append(col)

        # P1-D: Try the dq_v1 schema-metadata fast path first.  Files written
        # by the upgraded feature_storage carry per-column first_valid /
        # last_valid / nan_count packed into parquet schema metadata, so we
        # can skip the per-column NaN scan entirely.  Any file missing the
        # dq_v1 block (e.g. produced by an older writer) triggers fallback to
        # the parallel scan below — never wrong stats.
        dq_v1_hit, dq_v1_partials = self._try_load_dq_v1(
            list(path_to_cols.keys()), total_rows,
        )
        if dq_v1_hit:
            cols_seen: set = set()
            for partial in dq_v1_partials:
                local_row_nan = partial["row_nan"]
                if local_row_nan.shape[0] == total_rows:
                    row_nan_count += local_row_nan
                else:
                    aligned = min(local_row_nan.shape[0], total_rows)
                    row_nan_count[:aligned] += local_row_nan[:aligned]
                for col_name, nan_c, fv, lv in partial["col_stats"]:
                    if col_name in cols_seen:
                        continue
                    cols_seen.add(col_name)
                    real_nan_count[col_name] = nan_c
                    first_valid_map[col_name] = fv
                    last_valid_map[col_name] = lv
            real_nan_ratios = pd.Series(
                {c: (real_nan_count.get(c, 0) / total_rows) for c in columns},
                dtype=float,
            )
            timestamps = self._read_cgsa_timestamps(context, total_rows)
            group_map = self._build_group_map(column_to_path)
            logger.info(
                "browse_data_quality: dq_v1 fast-path hit (%d files, %d cols)",
                len(path_to_cols), len(columns),
            )
            # dq_v1 row_nan is a zeroed placeholder → rebuild from first/last_valid.
            return self._assemble_data_quality_report(
                total_rows=total_rows,
                columns=columns,
                nan_ratios=real_nan_ratios,
                first_valid_map=first_valid_map,
                last_valid_map=last_valid_map,
                row_nan_count=row_nan_count,
                timestamps=timestamps,
                rebuild_row_nan_from_valid=True,
                group_map=group_map,
            )

        # Cap per-batch memory.  T * batch_cols * 1 byte for the bool mask,
        # so 5000 cols * 20k rows ≈ 100 MB — safe for 8 GB tier.
        batch_cols = 5000
        n_paths = len(path_to_cols)
        scanned_cols = 0
        scanned_lock = threading.Lock()
        merge_lock = threading.Lock()
        t0 = time.monotonic()
        # P1-A: parallel scan with the same per-file batching budget so peak
        # RSS stays ≈ workers × 100 MB even on the 8 GB tier.
        max_workers = min(4, max(1, self._cgsa_stats_warmup_workers))
        if n_paths == 1:
            max_workers = 1
        logger.info(
            "browse_data_quality: scanning %d features across %d parquet files (rows=%d, workers=%d)",
            n_features, n_paths, total_rows, max_workers,
        )

        def _scan_one_file(args: tuple) -> None:
            nonlocal scanned_cols
            file_idx, path, cols_in_path = args
            local_row_nan = np.zeros(total_rows, dtype=np.int64)
            local_results: List[tuple] = []  # (col_name, nan_count, first_valid, last_valid)
            for start in range(0, len(cols_in_path), batch_cols):
                batch = cols_in_path[start:start + batch_cols]
                try:
                    table = pq.read_table(str(path), columns=batch)
                except Exception as exc:
                    logger.warning("browse_data_quality: failed to read %s: %s", path, exc)
                    continue
                if table.num_rows == 0 or table.num_columns == 0:
                    continue
                T_part = table.num_rows
                n_batch = table.num_columns
                nan_mask = np.empty((T_part, n_batch), dtype=bool)
                for j in range(n_batch):
                    arr = table.column(j)
                    try:
                        is_nan = pc.is_nan(arr)
                        combined = pc.or_kleene(pc.is_null(arr), is_nan)
                    except Exception:
                        combined = pc.is_null(arr)
                    nan_mask[:, j] = combined.to_numpy(zero_copy_only=False)
                del table

                if T_part == total_rows:
                    local_row_nan += nan_mask.sum(axis=1)
                else:
                    aligned = min(T_part, total_rows)
                    local_row_nan[:aligned] += nan_mask[:aligned].sum(axis=1)

                col_nan_counts = nan_mask.sum(axis=0)
                notna = ~nan_mask
                has_any = notna.any(axis=0)
                first_valid_arr = notna.argmax(axis=0)
                last_valid_arr = T_part - 1 - notna[::-1].argmax(axis=0)
                for i, col_name in enumerate(batch):
                    if has_any[i]:
                        fv = int(first_valid_arr[i])
                        lv = int(last_valid_arr[i])
                    else:
                        fv = total_rows
                        lv = -1
                    local_results.append((col_name, int(col_nan_counts[i]), fv, lv))
                del nan_mask, notna

            # Merge into shared state under a single lock per file.
            with merge_lock:
                row_nan_count[:] = row_nan_count + local_row_nan
                for col_name, nan_count, fv, lv in local_results:
                    real_nan_count[col_name] = nan_count
                    first_valid_map[col_name] = fv
                    last_valid_map[col_name] = lv
            with scanned_lock:
                scanned_cols += len(local_results)
                cur_scanned = scanned_cols
            if file_idx == 1 or file_idx == n_paths or file_idx % 10 == 0:
                elapsed = time.monotonic() - t0
                pct = cur_scanned / n_features * 100 if n_features else 100.0
                logger.info(
                    "browse_data_quality: file %d/%d scanned, %.1f%% cols (%.1fs)",
                    file_idx, n_paths, pct, elapsed,
                )
            # Periodic GC to release Arrow buffers on the 8 GB tier.
            if file_idx % 25 == 0:
                import gc as _gc
                _gc.collect()

        tasks = [
            (idx, path, cols_in_path)
            for idx, (path, cols_in_path) in enumerate(path_to_cols.items(), start=1)
        ]
        if max_workers <= 1 or len(tasks) <= 1:
            for task in tasks:
                _scan_one_file(task)
        else:
            from concurrent.futures import ThreadPoolExecutor as _TPE
            with _TPE(max_workers=max_workers, thread_name_prefix="dq-scan") as pool:
                list(pool.map(_scan_one_file, tasks))

        logger.info(
            "browse_data_quality: scan complete in %.1fs (%d cols, %d files)",
            time.monotonic() - t0, scanned_cols, n_paths,
        )

        real_nan_ratios = pd.Series(
            {c: (real_nan_count.get(c, 0) / total_rows) for c in columns},
            dtype=float,
        )

        timestamps = self._read_cgsa_timestamps(context, total_rows)
        group_map = self._build_group_map(column_to_path)
        # Parallel-scan row_nan_count is exact (includes mid-holes) → no rebuild.
        return self._assemble_data_quality_report(
            total_rows=total_rows,
            columns=columns,
            nan_ratios=real_nan_ratios,
            first_valid_map=first_valid_map,
            last_valid_map=last_valid_map,
            row_nan_count=row_nan_count,
            timestamps=timestamps,
            group_map=group_map,
        )

    @staticmethod
    def _build_group_map(
        column_to_path: Dict[str, Path],
    ) -> Dict[str, Tuple[str, str]]:
        """Map each column → (layer, tf) parsed from its parquet group_id (= file stem).

        Group ids follow ``{tf}_{layer}_{indicator}...`` e.g.
        ``1h_L3_rolling_W3_Skew_1_shard00`` → (``L3``, ``1h``);
        ``12h_L2_WorldQuant_part3`` → (``L2``, ``12h``).
        Unparseable stems map to (``?``, ``?``) so they still aggregate visibly.
        """
        stem_cache: Dict[Path, Tuple[str, str]] = {}
        group_map: Dict[str, Tuple[str, str]] = {}
        for col, path in column_to_path.items():
            if path is None:
                continue
            key = stem_cache.get(path)
            if key is None:
                parts = Path(path).stem.split("_")
                tf = parts[0] if parts else "?"
                layer = parts[1] if len(parts) > 1 else "?"
                # Validate tf looks like a timeframe (digits + m/h/d) and layer like L\d.
                if not (tf and tf[-1] in ("m", "h", "d") and tf[:-1].isdigit()):
                    tf = "?"
                if not (len(layer) >= 2 and layer[0] == "L" and layer[1:].isdigit()):
                    layer = "?"
                key = (layer, tf)
                stem_cache[path] = key
            group_map[col] = key
        return group_map

    def _try_load_dq_v1(
        self,
        paths: List[Path],
        total_rows: int,
    ) -> tuple:
        """Attempt to load packed per-column DQ stats from parquet schema metadata.

        Returns ``(True, partials)`` iff EVERY path supplies ``dq_v1`` metadata
        (any miss → ``(False, [])`` so the caller falls back to a live scan).
        Partials are dicts with ``row_nan`` (np.ndarray length total_rows or
        per-file len) and ``col_stats`` (list of (col, nan_count, fv, lv)).
        Reads run in parallel — each parquet footer is small (KB) so the
        wall-clock cost is dominated by FS round trips.
        """
        import pyarrow.parquet as pq
        import struct
        from concurrent.futures import ThreadPoolExecutor as _TPE

        def _one(path: Path) -> Optional[Dict[str, Any]]:
            try:
                meta = pq.read_metadata(str(path))
            except Exception:
                return None
            kv = meta.metadata or {}
            blob = kv.get(b"dq_v1")
            names_blob = kv.get(b"dq_v1_cols")
            rows_blob = kv.get(b"dq_v1_rows")
            if not blob or not names_blob or not rows_blob:
                return None
            try:
                file_rows = int(rows_blob.decode("ascii"))
            except Exception:
                return None
            try:
                (n_cols,) = struct.unpack_from("<I", blob, 0)
            except Exception:
                return None
            entry_size = struct.calcsize("<iiI")
            expected = 4 + n_cols * entry_size
            if len(blob) < expected:
                return None
            names_raw = names_blob.split(b"\x00")
            cols = [n.decode("utf-8") for n in names_raw if n]
            if len(cols) != n_cols:
                return None
            col_stats: List[tuple] = []
            row_nan_partial = np.zeros(file_rows, dtype=np.int64)
            # We do NOT have a per-row NaN histogram in dq_v1; we approximate
            # it from per-column stats: a column with k NaNs contributes k to
            # the total NaN count.  For the histogram-style stack we only need
            # the column sums.  Per-row counts are recomputed by summing across
            # files using a uniform distribution assumption ONLY for the
            # missing-by-time bucket; assemble_data_quality_report tolerates a
            # zeroed row_nan for the fast path.  (Conservative: this is the
            # one place dq_v1 trades exactness for speed; the report's column
            # tables are exact.)
            offset = 4
            for i in range(n_cols):
                fv, lv, nan_c = struct.unpack_from("<iiI", blob, offset)
                offset += entry_size
                col_stats.append((cols[i], int(nan_c), int(fv), int(lv)))
            return {
                "row_nan": row_nan_partial,
                "col_stats": col_stats,
                "file_rows": file_rows,
            }

        if not paths:
            return (False, [])
        max_workers = min(8, max(2, len(paths)))
        with _TPE(max_workers=max_workers, thread_name_prefix="dq-v1") as pool:
            results = list(pool.map(_one, paths))
        if any(r is None for r in results):
            return (False, [])
        # Verify row alignment.
        for r in results:
            if r["file_rows"] != total_rows:
                # Mismatch — caller should fall back to live scan to be safe.
                return (False, [])
        return (True, results)

    def _build_data_quality_inmemory(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback path: compute everything from a fully loaded DataFrame."""
        if df is None or df.empty or df.shape[1] == 0:
            return self._empty_data_quality_report()

        total_rows = int(df.shape[0])
        columns = list(df.columns)
        nan_ratios = df.isna().mean()

        nan_mask = df.isna().to_numpy()
        notna = ~nan_mask
        has_any = notna.any(axis=0)
        first_valid_arr = notna.argmax(axis=0)
        last_valid_arr = total_rows - 1 - notna[::-1].argmax(axis=0)

        first_valid_map: Dict[str, int] = {}
        last_valid_map: Dict[str, int] = {}
        for i, col in enumerate(columns):
            if has_any[i]:
                first_valid_map[col] = int(first_valid_arr[i])
                last_valid_map[col] = int(last_valid_arr[i])
            else:
                first_valid_map[col] = total_rows
                last_valid_map[col] = -1

        row_nan_count = nan_mask.sum(axis=1).astype(np.int64)
        timestamps = [str(idx) for idx in df.index.tolist()]
        return self._assemble_data_quality_report(
            total_rows=total_rows,
            columns=columns,
            nan_ratios=nan_ratios,
            first_valid_map=first_valid_map,
            last_valid_map=last_valid_map,
            row_nan_count=row_nan_count,
            timestamps=timestamps,
        )

    def _read_cgsa_timestamps(self, context: Dict[str, Any], total_rows: int) -> List[str]:
        """Best-effort timestamp recovery from the first CGSA parquet's index.

        Falls back to positional indices when no recognizable timestamp column
        is found. Reads at most one column to stay cheap on 450k-column tasks.
        """
        import pyarrow.parquet as pq

        manifest = context.get("manifest") or {}
        manifest_dir: Optional[Path] = context.get("manifest_dir")
        groups_raw = manifest.get("groups")
        first_path: Optional[Path] = None
        if isinstance(groups_raw, dict):
            for _gid, meta in groups_raw.items():
                if not isinstance(meta, dict):
                    continue
                relative = meta.get("path") or meta.get("file")
                if relative and manifest_dir is not None:
                    cand = manifest_dir / relative
                    if cand.exists():
                        first_path = cand
                        break
        elif isinstance(groups_raw, list):
            for meta in groups_raw:
                if isinstance(meta, dict) and meta.get("parquet_path"):
                    cand = Path(meta["parquet_path"])
                    if cand.exists():
                        first_path = cand
                        break

        if first_path is None:
            return [str(i) for i in range(total_rows)]

        try:
            pf = pq.ParquetFile(str(first_path))
            schema_names = pf.schema_arrow.names
        except Exception:
            return [str(i) for i in range(total_rows)]

        ts_candidates = [n for n in schema_names if n.lower() in ("timestamp", "open_time", "ts", "datetime", "index")]
        if not ts_candidates:
            return [str(i) for i in range(total_rows)]

        try:
            table = pq.read_table(str(first_path), columns=[ts_candidates[0]])
            series = table.column(0).to_pandas()
            if pd.api.types.is_datetime64_any_dtype(series):
                return [ts.isoformat() if hasattr(ts, "isoformat") else str(ts) for ts in series.tolist()]
            return [str(v) for v in series.tolist()]
        except Exception:
            return [str(i) for i in range(total_rows)]

    @staticmethod
    def _compute_nan_ratio_quantiles(nan_ratios: pd.Series) -> Dict[str, float]:
        """由 per-feature 真實 nan_ratio 序列計算五數摘要（與 np.percentile 對齊）。"""
        if len(nan_ratios) == 0:
            return {"min": 0.0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0.0}
        values = np.asarray(nan_ratios.astype(float).values, dtype=np.float64)
        percentiles = np.percentile(values, [0, 25, 50, 75, 100])
        return {
            "min": float(percentiles[0]),
            "q1": float(percentiles[1]),
            "median": float(percentiles[2]),
            "q3": float(percentiles[3]),
            "max": float(percentiles[4]),
        }

    def _resolve_true_nan_quality_metrics(
        self,
        context: Optional[Dict[str, Any]],
        fast: Optional[Dict[str, Any]],
        nan_ratios: pd.Series,
    ) -> Dict[str, Any]:
        """真實 per-feature NaN 均/峰/五數摘要；CGSA 快路徑須走 dq isna 掃描，不用 parquet null_count。"""
        dq: Optional[Dict[str, Any]] = None
        if context is not None and context.get("is_cgsa") and fast is not None:
            dq = self._load_data_quality_disk_cache(context)
            if dq is None or dq.get("nan_ratio_quantiles") is None:
                try:
                    dq = self._build_data_quality_cgsa(context, fast)
                    if int(dq.get("total_features") or 0) > 0:
                        self._persist_data_quality_disk_cache(context, dq)
                except Exception as exc:
                    logger.warning(
                        "browse_summary: dq nan metrics build failed for %s: %s",
                        context.get("task_id"),
                        exc,
                    )
                    dq = None
            if dq is not None and dq.get("nan_ratio_quantiles") is not None:
                return {
                    "nan_ratio_mean": float(dq.get("nan_ratio_mean") or 0.0),
                    "nan_ratio_max": float(dq.get("nan_ratio_max") or 0.0),
                    "nan_ratio_quantiles": dict(dq["nan_ratio_quantiles"]),
                }

        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            nan_ratio_mean = self._safe_float(nan_ratios.mean()) or 0.0
            nan_ratio_max = float(nan_ratios.max()) if len(nan_ratios) else 0.0
        return {
            "nan_ratio_mean": nan_ratio_mean,
            "nan_ratio_max": nan_ratio_max,
            "nan_ratio_quantiles": self._compute_nan_ratio_quantiles(nan_ratios),
        }

    def _assemble_data_quality_report(
        self,
        total_rows: int,
        columns: List[str],
        nan_ratios: pd.Series,
        first_valid_map: Dict[str, int],
        last_valid_map: Dict[str, int],
        row_nan_count: np.ndarray,
        timestamps: List[str],
        *,
        rebuild_row_nan_from_valid: bool = False,
        group_map: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Aggregate raw stats into the dashboard payload.

        ``rebuild_row_nan_from_valid``: when True, reconstruct the per-row NaN
        count from each column's first_valid / last_valid (leading warmup +
        trailing). Used by the dq_v1 metadata fast path, whose ``row_nan_count``
        is a zeroed placeholder (dq_v1 stores only per-column fv/lv/nan_count,
        not a per-row histogram). Known approximation: mid-hole NaNs inside the
        valid span are not reflected in coverage on this path (negligible — see
        plan §P0). The full-scan path passes an exact row_nan_count and leaves
        this False.

        ``group_map``: optional col → (layer, tf) for the group_breakdown block.
        """
        n_features = len(columns)
        if n_features == 0 or total_rows == 0:
            return self._empty_data_quality_report()

        # ---- P0: rebuild per-row NaN count from first/last valid -----------
        # A feature is missing at row r iff NOT (first_valid <= r <= last_valid).
        # For a feature with at least one valid value (fv <= lv) the leading
        # region [0, fv) and trailing region (lv, end] are disjoint, so:
        #   row_nan[r] = #(fv > r)  +  #(lv < r)   (over normal features)
        # All-NaN features (lv < 0) would be double-counted by that split, so
        # they are added once flatly. Vectorized O(total_rows + features).
        if rebuild_row_nan_from_valid:
            fv_list: List[int] = []
            lv_list: List[int] = []
            all_nan_features = 0
            for c in columns:
                fv = first_valid_map.get(c, 0)
                lv = last_valid_map.get(c, total_rows - 1)
                if lv < 0 or fv > lv:
                    all_nan_features += 1
                    continue
                fv_list.append(min(fv, total_rows))
                lv_list.append(lv)
            row_nan_count = np.full(total_rows, all_nan_features, dtype=np.int64)
            if fv_list:
                fv_arr = np.asarray(fv_list, dtype=np.int64)
                lv_arr = np.asarray(lv_list, dtype=np.int64)
                # leading_missing[r] = #(fv > r) = suffix sum of fv-histogram after r
                h_fv = np.bincount(np.clip(fv_arr, 0, total_rows), minlength=total_rows + 1)
                leading_missing = h_fv[::-1].cumsum()[::-1][1:]  # length total_rows
                # trailing_missing[r] = #(lv < r) = prefix sum of (lv+1)-histogram
                h_lv = np.bincount(np.clip(lv_arr + 1, 0, total_rows), minlength=total_rows + 1)
                trailing_missing = h_lv.cumsum()[:total_rows]
                row_nan_count = row_nan_count + leading_missing + trailing_missing
            row_nan_count = row_nan_count.astype(np.int64)

        # ---- Warmup distribution -----------------------------------------
        warmup_lengths = np.array(
            [first_valid_map.get(c, 0) for c in columns], dtype=np.int64
        )
        # Cap "all-NaN" sentinel (=total_rows) at total_rows for histogram safety.
        warmup_for_stats = np.clip(warmup_lengths, 0, total_rows)
        warmup_distribution = []
        for label, lo, hi in self._DATA_QUALITY_WARMUP_BUCKETS:
            if hi is None:
                count = int(((warmup_for_stats >= lo)).sum())
            else:
                count = int(((warmup_for_stats >= lo) & (warmup_for_stats <= hi)).sum())
            warmup_distribution.append({
                "bucket": label,
                "count": count,
                "ratio": float(count / n_features) if n_features else 0.0,
            })

        max_warmup = int(warmup_for_stats.max()) if n_features else 0
        p95_warmup = int(np.percentile(warmup_for_stats, self._DATA_QUALITY_WARMUP_PCTILE * 100)) if n_features else 0
        recommended_start_index = min(p95_warmup, max(total_rows - 1, 0))
        warmup_loss_ratio = float(recommended_start_index / total_rows) if total_rows else 0.0
        recommended_start_timestamp = (
            timestamps[recommended_start_index]
            if 0 <= recommended_start_index < len(timestamps)
            else str(recommended_start_index)
        )

        # ---- Per-feature derived stats -----------------------------------
        mid_holes: List[Dict[str, Any]] = []
        trailing_nans: List[Dict[str, Any]] = []
        scattered: List[Dict[str, Any]] = []
        real_problem_features: List[Dict[str, Any]] = []
        total_holes_features = 0
        total_trailing_features = 0
        total_high_nan_features = 0
        # P1: split the misleading "high NaN" bucket into benign vs real.
        #   warmup_only_high_nan: NaN is purely leading warmup (XGBoost handles;
        #     trim at training start) — NOT a data-quality problem.
        #   real_problem: mid-hole (NaN inside valid span) or all-NaN.
        warmup_only_high_nan = 0
        real_problem = 0
        # P3: per (layer, tf) group aggregation.
        group_stats: Dict[Tuple[str, str], Dict[str, float]] = {}

        def _bump_group(col_name: str, *, kind: str, ratio_v: float) -> None:
            # kind ∈ {"ok", "warmup", "real"}; called exactly once per feature so
            # feature_count / mean_nan_ratio cover ALL features in the group.
            if group_map is None:
                return
            key = group_map.get(col_name)
            if key is None:
                return
            g = group_stats.setdefault(
                key,
                {"feature_count": 0, "nan_ratio_sum": 0.0, "warmup_only": 0, "real_problem": 0},
            )
            g["feature_count"] += 1
            g["nan_ratio_sum"] += ratio_v
            if kind == "real":
                g["real_problem"] += 1
            elif kind == "warmup":
                g["warmup_only"] += 1

        for col in columns:
            ratio = float(nan_ratios.get(col, 0.0))
            nan_total = int(round(ratio * total_rows))
            first_v = first_valid_map.get(col, 0)
            last_v = last_valid_map.get(col, total_rows - 1)
            warmup_len = first_v if first_v < total_rows else total_rows
            trailing_len = (total_rows - 1 - last_v) if last_v >= 0 else total_rows
            # All-NaN: classify as scattered with ratio=1
            if last_v < 0:
                total_high_nan_features += 1
                real_problem += 1
                _bump_group(col, kind="real", ratio_v=1.0)
                scattered.append({"name": col, "nan_ratio": 1.0})
                real_problem_features.append({"name": col, "nan_ratio": 1.0, "hole_count": 0, "kind": "all_nan"})
                continue

            hole_count = max(0, nan_total - warmup_len - trailing_len)
            valid_span = max(1, last_v - first_v + 1)
            hole_ratio = float(hole_count / valid_span)
            if hole_count > 0:
                total_holes_features += 1
                mid_holes.append({
                    "name": col,
                    "hole_count": int(hole_count),
                    "hole_ratio": hole_ratio,
                })
            if trailing_len > 0:
                total_trailing_features += 1
                trailing_nans.append({
                    "name": col,
                    "trailing_length": int(trailing_len),
                })
            if ratio >= self._DATA_QUALITY_HIGH_NAN_THRESHOLD:
                total_high_nan_features += 1
                scattered.append({"name": col, "nan_ratio": ratio})
                # Benign iff all the NaN is leading warmup (no mid-hole).
                if hole_count > 0:
                    real_problem += 1
                    _bump_group(col, kind="real", ratio_v=ratio)
                    real_problem_features.append({"name": col, "nan_ratio": ratio, "hole_count": int(hole_count), "kind": "high_nan_hole"})
                else:
                    warmup_only_high_nan += 1
                    _bump_group(col, kind="warmup", ratio_v=ratio)
            else:
                # Not high-NaN: still count it in the group (kind="ok") so
                # feature_count / mean_nan_ratio reflect the whole group.
                _bump_group(col, kind="ok", ratio_v=ratio)

        mid_holes.sort(key=lambda x: x["hole_count"], reverse=True)
        trailing_nans.sort(key=lambda x: x["trailing_length"], reverse=True)
        scattered.sort(key=lambda x: x["nan_ratio"], reverse=True)
        real_problem_features.sort(key=lambda x: x["nan_ratio"], reverse=True)

        # ---- Cross-sectional coverage timeline ---------------------------
        coverage_arr = 1.0 - (row_nan_count.astype(np.float64) / float(n_features))
        coverage_arr = np.clip(coverage_arr, 0.0, 1.0)
        timeline = self._subsample_timeline(
            coverage_arr, timestamps, self._DATA_QUALITY_TIMELINE_POINTS
        )
        min_idx = int(np.argmin(coverage_arr))
        min_coverage = float(coverage_arr[min_idx])
        min_coverage_timestamp = (
            timestamps[min_idx] if 0 <= min_idx < len(timestamps) else str(min_idx)
        )

        timestamp_start = timestamps[0] if timestamps else ""
        timestamp_end = timestamps[-1] if timestamps else ""

        # "Real" problems exclude benign leading warmup. mid_holes already means
        # NaN inside the valid span; trailing means tail truncation; real_problem
        # counts mid-hole + all-NaN high-NaN features (computed in the loop).
        is_clean = (
            real_problem == 0
            and total_holes_features == 0
            and total_trailing_features == 0
            and max_warmup == 0
            and float(coverage_arr.min()) >= 1.0
        )

        # P3: finalize group_breakdown (sorted by feature_count desc).
        group_breakdown: List[Dict[str, Any]] = []
        for (layer, tf), g in group_stats.items():
            fc = int(g["feature_count"])
            group_breakdown.append({
                "layer": layer,
                "tf": tf,
                "feature_count": fc,
                "mean_nan_ratio": float(g["nan_ratio_sum"] / fc) if fc else 0.0,
                "warmup_only": int(g["warmup_only"]),
                "real_problem": int(g["real_problem"]),
            })
        group_breakdown.sort(key=lambda x: x["feature_count"], reverse=True)

        nan_ratio_mean = float(nan_ratios.mean()) if n_features else 0.0
        nan_ratio_max = float(nan_ratios.max()) if n_features else 0.0
        nan_ratio_quantiles = self._compute_nan_ratio_quantiles(nan_ratios)

        return {
            "schema_version": self._DATA_QUALITY_SCHEMA_VERSION,
            "nan_ratio_mean": nan_ratio_mean,
            "nan_ratio_max": nan_ratio_max,
            "nan_ratio_quantiles": nan_ratio_quantiles,
            "total_features": n_features,
            "total_timesteps": total_rows,
            "timestamp_start": timestamp_start,
            "timestamp_end": timestamp_end,
            "is_clean": bool(is_clean),
            "recommended_start_index": int(recommended_start_index),
            "recommended_start_timestamp": str(recommended_start_timestamp),
            "warmup_loss_ratio": warmup_loss_ratio,
            "max_warmup": int(max_warmup),
            "p95_warmup": int(p95_warmup),
            "warmup_distribution": warmup_distribution,
            "coverage_timeline": timeline,
            "min_coverage": min_coverage,
            "min_coverage_timestamp": str(min_coverage_timestamp),
            "mid_holes": mid_holes,
            "trailing_nans": trailing_nans,
            "scattered_nans": scattered[: self._DATA_QUALITY_SCATTERED_CAP],
            "real_problem_features": real_problem_features,
            "counts": {
                "mid_holes": int(total_holes_features),
                "trailing_nans": int(total_trailing_features),
                "high_nan": int(total_high_nan_features),
                "warmup_only_high_nan": int(warmup_only_high_nan),
                "real_problem": int(real_problem),
            },
            "group_breakdown": group_breakdown,
        }

    @staticmethod
    def _subsample_timeline(
        values: np.ndarray,
        timestamps: List[str],
        target_points: int,
    ) -> List[Dict[str, Any]]:
        n = int(values.shape[0])
        if n == 0:
            return []
        if n <= target_points:
            indices = range(n)
        else:
            step = max(1, n // target_points)
            indices = range(0, n, step)
        out: List[Dict[str, Any]] = []
        for idx in indices:
            ts = timestamps[idx] if 0 <= idx < len(timestamps) else str(idx)
            out.append({
                "index": int(idx),
                "timestamp": str(ts),
                "coverage": float(values[idx]),
            })
        return out

    @classmethod
    def _empty_data_quality_report(cls) -> Dict[str, Any]:
        return {
            "schema_version": cls._DATA_QUALITY_SCHEMA_VERSION,
            "total_features": 0,
            "total_timesteps": 0,
            "timestamp_start": "",
            "timestamp_end": "",
            "is_clean": True,
            "recommended_start_index": 0,
            "recommended_start_timestamp": "",
            "warmup_loss_ratio": 0.0,
            "max_warmup": 0,
            "p95_warmup": 0,
            "warmup_distribution": [],
            "coverage_timeline": [],
            "min_coverage": 1.0,
            "min_coverage_timestamp": "",
            "mid_holes": [],
            "trailing_nans": [],
            "scattered_nans": [],
            "real_problem_features": [],
            "counts": {
                "mid_holes": 0,
                "trailing_nans": 0,
                "high_nan": 0,
                "warmup_only_high_nan": 0,
                "real_problem": 0,
            },
            "group_breakdown": [],
            "nan_ratio_mean": 0.0,
            "nan_ratio_max": 0.0,
            "nan_ratio_quantiles": {
                "min": 0.0,
                "q1": 0.0,
                "median": 0.0,
                "q3": 0.0,
                "max": 0.0,
            },
        }

    def _get_stats_warmup_progress(
        self,
        task_id: str,
        *,
        total_features: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """回傳 stats 暖機進度，供 Feature Table 顯示排序暫定提示。

        沿用既有 cache 計數，不新增阻塞掃描。
        """
        total = int(total_features or 0)
        computed = 0
        ctx = context

        if ctx is None:
            try:
                ctx = self._load_task_context(task_id)
            except Exception:
                ctx = None

        if ctx and ctx.get("is_cgsa"):
            if total <= 0:
                try:
                    fast = self._load_cgsa_summary_fast(ctx)
                    if fast is not None:
                        total = len(fast.get("columns") or [])
                except Exception:
                    pass
            stats_df = self._load_cgsa_stats_mem(task_id, ctx)
            computed = int(len(stats_df.index)) if not stats_df.empty else 0
        else:
            with self._lock:
                cached_rows = self._stats_cache.get(task_id)
            if cached_rows is not None:
                computed = len(cached_rows)
            if total <= 0:
                try:
                    features_df, _meta = self._load_task_features(task_id)
                    total = int(features_df.shape[1])
                except Exception:
                    pass

        if total <= 0:
            return {
                "computed": 0,
                "total": 0,
                "pct": 100.0,
                "complete": True,
            }

        computed = min(computed, total)
        pct = round(float(computed) / float(total) * 100.0, 1)
        return {
            "computed": computed,
            "total": total,
            "pct": pct,
            "complete": computed >= total,
        }

    def browse_summary(self, task_id: str) -> Dict[str, Any]:
        """Return feature explorer summary dashboard payload — coalesced wrapper."""
        fp = ("browse_summary", task_id)
        return self._coalesce_browse(fp, lambda: self._browse_summary_impl(task_id))

    def _browse_summary_impl(self, task_id: str) -> Dict[str, Any]:
        """Return feature explorer summary dashboard payload.

        Performance strategy:
        * For CGSA tasks (parquet-backed) we first try ``_load_cgsa_summary_fast``
          which derives shape / nan_ratios / constants from parquet *metadata*
          without decoding any column data. This drops the cold-load path from
          ~30-60s (loading 200k columns into memory) to a few seconds.
        * Stationarity (ADF) only needs ~100 sample columns, so we read just
          those columns from parquet on demand.
        * The full DataFrame is still warmed asynchronously for FeatureTable /
          Distribution tabs via ``_start_stats_cache_warmup``; that no longer
          blocks the Overview response.
        * HDF5 tasks (or CGSA fast-path failures) fall through to the original
          full-load implementation.
        """
        import warnings

        # Probe context for CGSA fast-path. Wrap in try/except because some
        # unit tests monkeypatch only _load_task_features; in that case we
        # silently skip the fast path and fall through to the legacy load.
        context: Optional[Dict[str, Any]] = None
        try:
            context = self._load_task_context(task_id)
        except Exception as exc:
            logger.debug("browse_summary: _load_task_context failed (%s); using legacy path", exc)
            context = None

        if context and context.get("is_cgsa"):
            try:
                fast_summary = self._load_cgsa_summary_fast(context)
            except Exception as exc:
                logger.warning(
                    "CGSA fast summary failed for task %s, falling back to full load: %s",
                    task_id, exc, exc_info=True,
                )
                fast_summary = None
            if fast_summary is not None:
                return self._browse_summary_from_fast(task_id, context, fast_summary)

        # ----- Original full-load path (HDF5 / fast-path fallback) -----
        features_df, export_meta = self._load_task_features(task_id)

        # --- Category / layer / level breakdown (name parsing fast-path) ---
        by_category: Dict[str, int] = {}
        by_level: Dict[str, int] = {}
        by_layer_raw: Dict[str, int] = {}
        for col in features_df.columns:
            cat = infer_category(col)
            layer = infer_layer(col)
            level_raw = infer_level(cat)
            simple_level = self._to_simple_level(level_raw)
            by_category[cat] = by_category.get(cat, 0) + 1
            by_layer_raw[layer] = by_layer_raw.get(layer, 0) + 1
            by_level[simple_level] = by_level.get(simple_level, 0) + 1
        # Keys match _infer_layer() return values exactly.
        by_layer = {
            "Layer 1 (Atomic)": by_layer_raw.get("layer1", 0),
            "Layer 2 (Derived)": by_layer_raw.get("layer2", 0),
            "Layer 3 (Rolling)": by_layer_raw.get("layer3", 0),
            "Layer 4 (Lag)": by_layer_raw.get("layer4", 0),
            "Layer 5 (Cross-Sect)": by_layer_raw.get("layer5", 0),
            "Layer 6 (Meta)": by_layer_raw.get("layer6", 0),
            "Layer 6.5 (Preproc)": by_layer_raw.get("layer6_5", 0),
        }

        # --- Vectorized quality metrics ----------------------------------------
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            nan_ratios = features_df.isna().mean()
        nan_metrics = self._resolve_true_nan_quality_metrics(context, None, nan_ratios)

        # Constant features: nunique <= 1 (vectorized)
        numeric_df = features_df.select_dtypes(include=["number"])
        constant_features_list = list(
            numeric_df.columns[(numeric_df.nunique(dropna=True) <= 1).values]
        )

        # High-corr pair count: too slow on large feature sets — skip and mark as None.
        # We cap at 500 features to give a rough estimate without blocking for minutes.
        HIGH_CORR_SAMPLE_LIMIT = 500
        high_corr_pairs_count: Optional[int] = None
        if numeric_df.shape[1] <= HIGH_CORR_SAMPLE_LIMIT:
            corr_abs = numeric_df.corr().abs()
            upper = corr_abs.where(np.triu(np.ones(corr_abs.shape), k=1).astype(bool))
            high_corr_pairs_count = int((upper > 0.95).sum().sum())

        stationary_ratio = self._estimate_stationary_ratio(features_df)

        # Quality alerts: limit to a sample to avoid O(N) loop on 36k features
        quality_alerts = self._fast_quality_alerts(features_df, nan_ratios)

        # Warm the expensive per-feature stats cache asynchronously.  The summary
        # API is usually called before users open Feature Table, so this hides
        # first-load latency without reducing data completeness.
        self._start_stats_cache_warmup(task_id, reason="browse_summary")
        self._start_adf_cache_warmup(task_id, reason="browse_summary")

        stats_warmup = self._get_stats_warmup_progress(
            task_id,
            total_features=int(features_df.shape[1]),
        )

        return {
            "total_features": int(features_df.shape[1]),
            "total_rows": int(features_df.shape[0]),
            "by_category": by_category,
            "by_level": by_level,
            "by_layer": by_layer,
            "quality": {
                "nan_ratio_mean": nan_metrics["nan_ratio_mean"],
                "nan_ratio_max": nan_metrics["nan_ratio_max"],
                "nan_ratio_quantiles": nan_metrics["nan_ratio_quantiles"],
                "nan_ratio_distribution": self._nan_ratio_distribution(features_df, nan_ratios),
                "constant_features": constant_features_list,
                "high_corr_pairs_count": high_corr_pairs_count,
                "stationary_ratio": stationary_ratio,
                "quality_alerts": quality_alerts,
            },
            "stats_warmup": stats_warmup,
            "generation_info": {
                "task_id": task_id,
                "symbol": export_meta.get("symbol"),
                "timeframe": export_meta.get("timeframe"),
                "generated_at": export_meta.get("generated_at"),
                "generation_time": export_meta.get("generation_time"),
                "config_hash": (export_meta.get("metadata") or {}).get("config_hash"),
            },
        }

    def _start_stats_cache_warmup(self, task_id: str, reason: str) -> None:
        """Warm per-feature stats cache in background if not already available."""
        try:
            context = self._load_task_context(task_id)
            if context.get("is_cgsa"):
                # CGSA tasks use a group-by-group background warmup that
                # populates feature_stats_cache.parquet incrementally so
                # repeat searches are served from cache without parquet I/O.
                self._start_cgsa_stats_warmup(task_id, context)
                return
        except Exception:
            pass

        with self._lock:
            if task_id in self._stats_cache or task_id in self._stats_warming_tasks:
                return
            self._stats_warming_tasks.add(task_id)

        def _worker() -> None:
            try:
                self._build_stats_rows(task_id)
            except Exception as exc:
                logger.warning("Stats warmup failed for task %s: %s", task_id, exc, exc_info=True)
            finally:
                with self._lock:
                    self._stats_warming_tasks.discard(task_id)

        thread = threading.Thread(
            target=_worker,
            daemon=True,
            name=f"stats-warm-{task_id[:8]}",
        )
        thread.start()
        logger.info("Stats cache warming started for task %s (reason=%s)", task_id, reason)

    def _fast_quality_alerts(self, features_df: pd.DataFrame, nan_ratios: "pd.Series") -> List[Dict[str, Any]]:
        """Return quality alerts using the pre-computed nan_ratios series.

        Limits to first 50 alerts to avoid sending huge payloads for large datasets.
        """
        MAX_ALERTS = 50
        alerts: List[Dict[str, Any]] = []
        high_nan = nan_ratios[nan_ratios > 0.1].head(MAX_ALERTS)
        for feature, ratio in high_nan.items():
            alerts.append({
                "severity": "warning",
                "feature": feature,
                "message": f"NaN ratio {ratio:.2%} exceeds 10% threshold",
            })
            if len(alerts) >= MAX_ALERTS:
                break
        return alerts

    def register_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Register notification callback for task."""
        with self._lock:
            self._callbacks.setdefault(task_id, []).append(callback)

    def unregister_notification_callback(self, task_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unregister notification callback for task."""
        with self._lock:
            callbacks = self._callbacks.get(task_id, [])
            if callback in callbacks:
                callbacks.remove(callback)
            if not callbacks and task_id in self._callbacks:
                del self._callbacks[task_id]

    def get_presets(self) -> List[Dict[str, Any]]:
        """Get preset list."""
        return self._mcp.get_presets()

    def get_config(self, api_override: Optional[Dict] = None) -> Dict[str, Any]:
        """Get merged config for Feature Factory."""
        config = self._resolve_config(api_override)
        return config.model_dump(by_alias=True)

    def update_config(self, partial_config: Dict[str, Any]) -> Dict[str, Any]:
        """Return merged config for preview/update purposes."""
        config = self._resolve_config(partial_config)
        return config.model_dump(by_alias=True)

    def preview(self, config_override: Optional[Dict]) -> Dict[str, Any]:
        """Preview feature counts for config override."""
        config = self._resolve_config(config_override)
        preview = self._config_manager.preview_feature_count(config)
        return preview.model_dump()

    def nl2config(self, text: str) -> Dict[str, Any]:
        """Natural language to config conversion."""
        result = self._mcp.nl2config(text)
        preview = result.get("preview", {}) if isinstance(result, dict) else {}
        if isinstance(preview, dict) and "error" in preview:
            raise ValueError(preview.get("error"))
        return result

    def list_indicators(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List indicators by optional category."""
        return self._mcp.list_indicators(category)

    def list_data_sources(self) -> List[Dict[str, Any]]:
        """List data sources."""
        return self._mcp.list_data_sources()

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate config."""
        return self._mcp.validate_config(config)

    def get_feature_metadata(self, feature_name: str) -> Dict[str, Any]:
        """Get feature metadata."""
        return self._mcp.get_feature_metadata(feature_name)

    # ------ Phase B: Schema / Batch Toggle / Preset Apply ------

    def get_schema(self) -> Dict[str, Any]:
        """Build complete feature factory schema for frontend UI rendering.

        Returns a layered view of all available indicators, operators,
        aggregators, etc. with current enabled state and descriptions.
        """
        config = self._resolve_config(None)
        config_dict = config.model_dump(by_alias=True)
        return self._build_schema(config_dict)

    def batch_toggle(self, toggles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply batch toggle operations and return updated config + preview."""
        config = self._resolve_config(None)
        config_dict = config.model_dump(by_alias=True)

        results = []
        for toggle in toggles:
            path = toggle.get("path", "")
            value = toggle.get("value", True)
            success = self._apply_toggle_to_dict(config_dict, path, value)
            results.append({"path": path, "value": value, "success": success})

        updated_config = self._config_manager.get_merged_config(config_dict)
        preview = self._config_manager.preview_feature_count(updated_config)
        return {
            "results": results,
            "config": updated_config.model_dump(by_alias=True),
            "preview": preview.model_dump(),
        }

    def apply_preset_config(self, preset_name: str) -> Dict[str, Any]:
        """Apply a named preset and return the resulting config + preview."""
        config = self._config_manager.apply_preset(preset_name)
        preview = self._config_manager.preview_feature_count(config)
        return {
            "config": config.model_dump(by_alias=True),
            "preview": preview.model_dump(),
        }

    # ------ Schema Builder Internals ------

    _CATEGORY_DESCRIPTIONS: Dict[str, str] = {
        "trend": "趨勢指標",
        "momentum": "動量指標",
        "volatility": "波動率指標",
        "volume": "成交量指標",
        "cycle": "週期指標",
        "pattern": "K 線形態指標",
        "statistics": "統計指標",
        "microstructure": "微觀結構特徵",
        "entropy": "資訊熵特徵",
        "tail_risk": "尾部風險特徵",
    }

    _CATEGORY_LEVELS: Dict[str, str] = {
        "trend": "L1",
        "momentum": "L1",
        "volatility": "L1",
        "volume": "L1",
        "cycle": "L2",
        "pattern": "L2",
        "statistics": "L2",
        "microstructure": "L3",
        "entropy": "L3",
        "tail_risk": "L3",
    }

    _INDICATOR_DESCRIPTIONS: Dict[str, str] = {
        # Trend
        "EMA": "指數移動平均", "SMA": "簡單移動平均", "WMA": "加權移動平均",
        "DEMA": "雙指數移動平均", "TEMA": "三指數移動平均", "TRIMA": "三角移動平均",
        "KAMA": "Kaufman 自適應", "T3": "T3 移動平均", "MAMA": "Mesa 自適應",
        "HT_TRENDLINE": "Hilbert 趨勢線", "MIDPOINT": "中點", "MIDPRICE": "中價",
        "SAR": "Parabolic SAR", "SAREXT": "SAR 擴展", "BBANDS": "Bollinger Bands",
        "MAVP": "可變期間移動平均", "MA": "通用移動平均",
        # Momentum
        "RSI": "相對強弱指標", "MACD": "移動平均收斂散度", "MACDEXT": "MACD 擴展",
        "MACDFIX": "MACD 固定", "ADX": "平均趨勢方向指標", "ADXR": "ADX 評級",
        "DX": "方向運動指標", "PLUS_DI": "正向方向指標", "MINUS_DI": "負向方向指標",
        "PLUS_DM": "正向方向運動", "MINUS_DM": "負向方向運動", "CCI": "商品通道指標",
        "CMO": "Chande 動量振盪器", "MOM": "Momentum", "ROC": "變化率",
        "ROCP": "變化率百分比", "ROCR": "變化率比率", "ROCR100": "變化率比率 ×100",
        "APO": "絕對價格振盪器", "PPO": "百分比價格振盪器", "AROON": "Aroon 指標",
        "AROONOSC": "Aroon 振盪器", "BOP": "Balance of Power", "TRIX": "三重指數平均",
        "ULTOSC": "Ultimate Oscillator", "WILLR": "Williams %R", "MFI": "Money Flow Index",
        "STOCH": "隨機指標", "STOCHF": "快速隨機指標", "STOCHRSI": "RSI 隨機指標",
        # Volatility
        "ATR": "平均真實波幅", "NATR": "正規化 ATR", "TRANGE": "True Range",
        "Keltner": "Keltner 通道", "Donchian": "Donchian 通道",
        "Parkinson_Vol": "Parkinson 波動率", "GarmanKlass_Vol": "Garman-Klass 波動率",
        # Volume
        "OBV": "On-Balance Volume", "AD": "Accumulation/Distribution",
        "ADOSC": "AD 振盪器", "VWAP": "成交量加權平均價",
        "Volume_MA_Ratio": "量均比", "Force_Index": "力度指標",
        "Klinger_Volume_Osc": "Klinger 量振盪器", "Ease_of_Movement": "移動便捷度",
        # Cycle
        "HT_DCPERIOD": "主導期間", "HT_DCPHASE": "相位", "HT_PHASOR": "相位器",
        "HT_SINE": "正弦波", "HT_TRENDMODE": "趨勢模式",
        # Statistics
        "LINEARREG": "線性回歸", "LINEARREG_SLOPE": "回歸斜率",
        "LINEARREG_ANGLE": "回歸角度", "LINEARREG_INTERCEPT": "回歸截距",
        "STDDEV": "標準差", "VAR": "方差", "TSF": "時間序列預測",
        "BETA": "Beta 係數", "CORREL": "相關性",
        # Microstructure
        "amihud": "Amihud 非流動性", "kyle_lambda": "Kyle's Lambda",
        "roll_spread": "Roll 隱含價差", "cs_spread": "Corwin-Schultz 價差",
        "ofi": "訂單流失衡", "large_trade_ratio": "大單比率", "vpin": "VPIN",
        # Entropy
        "shannon": "Shannon 資訊熵", "approximate": "近似熵", "sample": "樣本熵",
        "hurst": "Hurst 指數", "fractal": "碎形維度", "permutation": "排列熵",
        # Tail Risk
        "cvar": "條件風險值", "realized_vol_up": "上行已實現波動率",
        "realized_vol_down": "下行已實現波動率", "rsj": "跳躍非對稱",
        "updown_vol_ratio": "上下波動比", "gain_pain_ratio": "盈虧比",
        "jarque_bera": "常態性檢定", "max_drawdown": "最大回撤",
    }

    _OPERATOR_DESCRIPTIONS: Dict[str, str] = {
        "distance": "距離運算元（指標間差距）",
        "cross": "交叉運算元（指標交叉信號）",
        "momentum": "動量變化運算元",
        "ratio": "比率運算元（指標間比率）",
        "binary_signal": "二元信號運算元（閾值觸發）",
        "worldquant": "WorldQuant Alpha 運算元",
    }

    _AGG_DESCRIPTIONS: Dict[str, str] = {
        "slope": "線性回歸斜率", "std": "標準差", "mean": "平均值",
        "rank": "百分位排名", "zscore": "Z 分數", "skew": "偏態",
        "kurt": "峰態", "min": "最小值", "max": "最大值", "range": "極差",
    }

    _META_DESCRIPTIONS: Dict[str, str] = {
        "consensus": "多指標共識信號",
        "interaction": "特徵交互作用",
        "time_features": "時間特徵（日期/小時等）",
        "trend_consensus": "趨勢共識信號",
        "momentum_divergence": "動量背離信號",
        "volume_price_divergence": "量價背離信號",
        "volatility_regime": "波動率區間狀態",
    }

    _PREPROCESSING_DESCRIPTIONS: Dict[str, str] = {
        "winsorization": "極值截斷（Winsorization）",
        "rank_transform": "百分位排名轉換",
        "adaptive_zscore": "自適應 Z-Score 標準化",
        "gaussian_normalize": "高斯正規化",
        "adf_differencing": "ADF 差分",
        "fractional_differencing": "分數階差分",
    }

    _SPECIAL_CATEGORY_DEFAULTS: Dict[str, List[str]] = {
        "microstructure": [
            "amihud",
            "kyle_lambda",
            "roll_spread",
            "cs_spread",
            "ofi",
            "large_trade_ratio",
            "vpin",
        ],
        "entropy": [
            "shannon",
            "approximate",
            "sample",
            "hurst",
            "fractal",
            "permutation",
        ],
        "tail_risk": [
            "cvar",
            "realized_vol_up",
            "realized_vol_down",
            "rsj",
            "updown_vol_ratio",
            "gain_pain_ratio",
            "jarque_bera",
            "max_drawdown",
        ],
    }

    def _build_schema(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build layered schema dict from a config dump."""
        layers: Dict[str, Any] = {}

        # --- Layer 1: Atomic Indicators ---
        atomic = config_dict.get("atomic_indicators", {})
        categories: Dict[str, Any] = {}
        for cat_key in ["trend", "momentum", "volatility", "volume",
                        "cycle", "pattern", "statistics"]:
            cat_cfg = atomic.get(cat_key, {})
            indicators = []
            for ind in cat_cfg.get("indicators", []):
                if not isinstance(ind, dict):
                    continue
                name = ind.get("name", "")
                params = {k: v for k, v in ind.items() if k not in ("name", "enabled")}
                desc = self._INDICATOR_DESCRIPTIONS.get(name, "")
                if not desc and name.startswith("CDL"):
                    desc = "K 線形態"
                indicators.append({
                    "name": name,
                    "enabled": ind.get("enabled", True),
                    "description": desc,
                    "params": params,
                })
            categories[cat_key] = {
                "enabled": cat_cfg.get("enabled", True),
                "level": self._CATEGORY_LEVELS.get(cat_key, "L1"),
                "description": self._CATEGORY_DESCRIPTIONS.get(cat_key, ""),
                "indicators": indicators,
            }

        for special_key in ["microstructure", "entropy", "tail_risk"]:
            special_cfg = atomic.get(special_key, {})
            features_list = []
            features_dict = special_cfg.get("features") or {}
            if not isinstance(features_dict, dict):
                features_dict = {}

            # Backward compatibility: if special category has no explicit features dict,
            # expose a complete default list so frontend can render toggles.
            if not features_dict:
                default_names = self._SPECIAL_CATEGORY_DEFAULTS.get(special_key, [])
                enabled_features = special_cfg.get("enabled_features")
                for name in default_names:
                    enabled = True
                    if isinstance(enabled_features, list):
                        enabled = name in enabled_features
                    features_dict[name] = {"enabled": enabled}

            for feat_name, feat_cfg in features_dict.items():
                features_list.append({
                    "name": feat_name,
                    "enabled": feat_cfg.get("enabled", True) if isinstance(feat_cfg, dict) else True,
                    "description": self._INDICATOR_DESCRIPTIONS.get(feat_name, ""),
                })
            # Build params excluding structural keys
            special_params = {
                k: v for k, v in special_cfg.items()
                if k not in ("enabled", "features", "enabled_features")
            }
            categories[special_key] = {
                "enabled": special_cfg.get("enabled", False),
                "level": self._CATEGORY_LEVELS.get(special_key, "L3"),
                "description": self._CATEGORY_DESCRIPTIONS.get(special_key, ""),
                "features": features_list,
                "params": special_params,
            }

        layers["layer1"] = {
            "name": "Atomic Indicators",
            "enabled": True,
            "categories": categories,
        }

        # --- Layer 2: Derived Operators ---
        operators_cfg = config_dict.get("operators", {})
        operators: Dict[str, Any] = {}
        for op_key in ["distance", "cross", "momentum", "ratio",
                        "binary_signal", "worldquant"]:
            op_cfg = operators_cfg.get(op_key, {})
            if not isinstance(op_cfg, dict):
                op_cfg = {}
            op_info: Dict[str, Any] = {
                "enabled": op_cfg.get("enabled", True),
                "description": self._OPERATOR_DESCRIPTIONS.get(op_key, ""),
            }
            if op_key == "binary_signal":
                op_info["rules"] = [
                    {
                        "indicator": r.get("indicator", ""),
                        "condition": r.get("condition", ""),
                        "name_suffix": r.get("name_suffix", ""),
                        "enabled": r.get("enabled", True),
                    }
                    for r in op_cfg.get("rules", [])
                    if isinstance(r, dict)
                ]
            elif op_key == "worldquant":
                wq_ops = op_cfg.get("operators") or {}
                op_info["operators"] = {
                    name: {"enabled": cfg.get("enabled", True) if isinstance(cfg, dict) else True}
                    for name, cfg in wq_ops.items()
                }
            operators[op_key] = op_info

        layers["layer2"] = {
            "name": "Derived Operators",
            "enabled": any(
                isinstance(v, dict) and v.get("enabled", True)
                for v in operators_cfg.values()
            ),
            "operators": operators,
        }

        # --- Layer 3: Rolling Aggregation ---
        rolling_cfg = config_dict.get("rolling_aggregation", {})
        aggregators: Dict[str, Any] = {}
        agg_dict = rolling_cfg.get("aggregators", {})
        if isinstance(agg_dict, dict):
            for agg_name, agg_cfg in agg_dict.items():
                aggregators[agg_name] = {
                    "enabled": agg_cfg.get("enabled", True) if isinstance(agg_cfg, dict) else True,
                    "description": self._AGG_DESCRIPTIONS.get(agg_name, ""),
                }

        layers["layer3"] = {
            "name": "Rolling Aggregation",
            "enabled": rolling_cfg.get("enabled", True),
            "windows": rolling_cfg.get("windows", []),
            "aggregators": aggregators,
            "apply_to": rolling_cfg.get("apply_to", "all"),
        }

        # --- Layer 4: Lag Features ---
        lag_cfg = config_dict.get("lag_features", {})
        layers["layer4"] = {
            "name": "Lag Features",
            "enabled": lag_cfg.get("enabled", True),
            "apply_to": lag_cfg.get("apply_to", "layer1_and_raw"),
            "exclude_patterns": lag_cfg.get("exclude_patterns", []),
        }

        # --- Layer 5: Cross-Sectional ---
        cross_cfg = config_dict.get("cross_sectional", {})
        cross_features: Dict[str, Any] = {}
        feat_dict = cross_cfg.get("features", {})
        if isinstance(feat_dict, dict):
            for feat_name, feat_cfg in feat_dict.items():
                cross_features[feat_name] = {
                    "enabled": feat_cfg.get("enabled", True) if isinstance(feat_cfg, dict) else True,
                    "description": "",
                }

        layers["layer5"] = {
            "name": "Cross-Sectional",
            "enabled": cross_cfg.get("enabled", False),
            "reference_symbol": cross_cfg.get("reference_symbol", "BTCUSDT"),
            "features": cross_features,
        }

        # --- Layer 6: Meta Features ---
        meta_cfg = config_dict.get("meta_features", {})
        sub_engines: Dict[str, Any] = {}
        for sub_key in ["consensus", "interaction", "time_features", "trend_consensus",
                        "momentum_divergence", "volume_price_divergence", "volatility_regime"]:
            sub_engines[sub_key] = {
                "enabled": meta_cfg.get(sub_key, True),
                "description": self._META_DESCRIPTIONS.get(sub_key, ""),
            }

        layers["layer6"] = {
            "name": "Meta Features",
            "enabled": meta_cfg.get("enabled", True),
            "sub_engines": sub_engines,
        }

        # --- Layer 6.5: Preprocessing ---
        prep_cfg = config_dict.get("preprocessing", {})
        methods: Dict[str, Any] = {}
        for method_key in ["winsorization", "rank_transform", "adaptive_zscore",
                           "gaussian_normalize", "adf_differencing", "fractional_differencing"]:
            method_cfg = prep_cfg.get(method_key, {})
            if not isinstance(method_cfg, dict):
                method_cfg = {}
            methods[method_key] = {
                "enabled": method_cfg.get("enabled", False),
                "description": self._PREPROCESSING_DESCRIPTIONS.get(method_key, ""),
                "params": {k: v for k, v in method_cfg.items() if k != "enabled"},
            }

        layers["layer6_5"] = {
            "name": "Preprocessing",
            "enabled": prep_cfg.get("enabled", False),
            "mode": prep_cfg.get("mode", "append"),
            "methods": methods,
        }

        return {"layers": layers}

    @staticmethod
    def _apply_toggle_to_dict(config: Dict[str, Any], path: str, value: Any) -> bool:
        """Apply a single toggle to a config dict using dot-path notation.

        Handles both dict navigation and list-by-name lookups:
        - ``atomic_indicators.trend.indicators.EMA.enabled`` → list lookup by name
        - ``rolling_aggregation.aggregators.zscore.enabled`` → dict key navigation
        """
        parts = path.split(".")
        if len(parts) < 2:
            return False

        current: Any = config
        i = 0
        while i < len(parts) - 1:
            part = parts[i]
            if not isinstance(current, dict) or part not in current:
                return False
            child = current[part]

            if isinstance(child, list):
                # Next part is a name to find in the list
                i += 1
                if i >= len(parts):
                    return False
                name_to_find = parts[i]
                found = None
                for item in child:
                    if isinstance(item, dict):
                        if item.get("name") == name_to_find or item.get("name_suffix") == name_to_find:
                            found = item
                            break
                if found is None:
                    return False
                current = found
            else:
                current = child
            i += 1

        if isinstance(current, dict):
            current[parts[-1]] = value
            return True
        return False

    def start_research(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start a lightweight AutoResearch task."""
        task_id = str(uuid.uuid4())
        task_info = {
            "task_id": task_id,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "payload": payload or {},
            "results": None,
        }
        with self._lock:
            self._research_tasks[task_id] = task_info
        logger.info("AutoResearch task started: %s", task_id)
        return {"task_id": task_id, "status": "running"}

    def get_research_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get AutoResearch task status."""
        with self._lock:
            task_info = self._research_tasks.get(task_id)
            if not task_info:
                return None
            return {
                "task_id": task_id,
                "status": task_info.get("status"),
            }

    def stop_research(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Stop AutoResearch task."""
        with self._lock:
            task_info = self._research_tasks.get(task_id)
            if not task_info:
                return None
            task_info["status"] = "stopped"
        return {"task_id": task_id, "status": "stopped"}

    def get_research_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get AutoResearch results."""
        with self._lock:
            task_info = self._research_tasks.get(task_id)
            if not task_info:
                return None
            return {
                "task_id": task_id,
                "results": task_info.get("results") or {},
            }

    def get_research_history(self) -> List[Dict[str, Any]]:
        """Get AutoResearch history list."""
        with self._lock:
            return [
                {
                    "task_id": task_id,
                    "status": info.get("status"),
                    "created_at": info.get("created_at"),
                }
                for task_id, info in self._research_tasks.items()
            ]

    def _resolve_config_override(self, config_override: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(config_override, dict):
            return config_override
        if "preset" in config_override:
            preset = config_override.get("preset")
            config = self._config_manager.apply_preset(preset)
            return config.model_dump(by_alias=True)
        return config_override

    def _resolve_config(self, config_override: Optional[Dict[str, Any]]):
        if isinstance(config_override, dict) and "preset" in config_override:
            preset = config_override.get("preset")
            return self._config_manager.apply_preset(preset)
        return self._config_manager.get_merged_config(config_override)

    def _notify_callbacks(self, task_id: str, payload: Dict[str, Any]) -> None:
        callbacks: List[Callable[[Dict[str, Any]], None]]
        with self._lock:
            callbacks = list(self._callbacks.get(task_id, []))
        for callback in callbacks:
            try:
                callback(payload)
            except Exception as exc:
                logger.error("Notification callback failed: %s", exc, exc_info=True)

    @staticmethod
    def _summarize_result(result: FeatureGenerationResult) -> Dict[str, Any]:
        return {
            "feature_count": result.feature_count,
            "generation_time": result.generation_time,
            "layer_counts": result.layer_counts,
            "metadata": result.metadata,
            "hdf5_path": result.hdf5_path,
        }

    # ------------------------------------------------------------------
    # Task persistence – allows the Feature Explorer to survive API restarts
    # ------------------------------------------------------------------

    _TASK_RECORD_NAME = "task_record.json"
    _CGSA_CATALOG_CACHE_NAME = "feature_catalog_cache.parquet"
    _CGSA_CATALOG_CACHE_META_NAME = "feature_catalog_cache.meta.json"
    _CGSA_STATS_CACHE_NAME = "feature_stats_cache.parquet"
    _CGSA_STATS_PARTS_DIR_NAME = "feature_stats_cache_parts"
    # Raised to 500: approximate quantiles (3 000-row sample) make 500 features
    # computable in ~600 ms, so the synchronous cap can be larger without
    # blocking the search response.  Features beyond the cap are returned with
    # null stats ("-") and filled in by the background warmup.
    _CGSA_STATS_SYNC_CAP = 500

    def _persist_task_record(self, task_id: str, summary: Dict[str, Any]) -> None:
        """Write a small JSON record next to the feature output so the task can
        be restored after an API restart."""
        hdf5_path = summary.get("hdf5_path")
        if not hdf5_path:
            return
        record_dir = Path(hdf5_path).parent
        record_path = record_dir / self._TASK_RECORD_NAME
        record = {
            "task_id": task_id,
            "hdf5_path": str(hdf5_path),
            "feature_count": summary.get("feature_count"),
            "generation_time": summary.get("generation_time"),
            "layer_counts": summary.get("layer_counts") or {},
            "metadata": summary.get("metadata") or {},
            "persisted_at": datetime.now().isoformat(),
        }
        try:
            record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug("Persisted task record: %s → %s", task_id, record_path)
        except OSError as exc:
            logger.warning("Failed to persist task record for %s: %s", task_id, exc)

    # ----------------------------------------------------------------------
    # P0-A: Browse-request coalescing helper.
    # ----------------------------------------------------------------------
    _BROWSE_COALESCE_TLS = threading.local()

    def _coalesce_browse(self, fingerprint: tuple, compute: Callable[[], Any]) -> Any:
        """Run ``compute`` exactly once per unique fingerprint at a time.

        Concurrent callers with the same fingerprint block on the in-flight
        event and reuse the original result/exception.  This eliminates the
        burst of duplicate parquet scans seen when tabs remount (StrictMode,
        navigation) while a heavy browse is still running.

        Mirrors successful/failed responses to every waiter so semantics are
        identical to a non-coalesced call.

        A thread-local re-entrancy guard prevents deadlock when a browse_*
        method calls another browse_* method on the same thread.
        """
        if getattr(self._BROWSE_COALESCE_TLS, "active", False):
            return compute()

        # Defensive lazy-init: legacy unit tests (and any caller that
        # constructs the service via ``__new__``) may not have run __init__.
        # The coalescing layer must never be the reason such a test fails, so
        # we materialize the required state on first use.
        if not hasattr(self, "_browse_inflight_lock"):
            self._browse_inflight_lock = threading.Lock()
        if not hasattr(self, "_browse_inflight"):
            self._browse_inflight = {}
        if not hasattr(self, "_active_browse_lock"):
            self._active_browse_lock = threading.Lock()
        if not hasattr(self, "_active_browse_requests"):
            self._active_browse_requests = 0

        with self._browse_inflight_lock:
            holder = self._browse_inflight.get(fingerprint)
            if holder is None:
                holder = {"event": threading.Event()}
                self._browse_inflight[fingerprint] = holder
                is_owner = True
            else:
                is_owner = False

        if not is_owner:
            holder["event"].wait()
            if "exception" in holder:
                raise holder["exception"]
            return holder["result"]

        # Owner branch: bump the foreground gauge so warmup yields.
        with self._active_browse_lock:
            self._active_browse_requests += 1
        self._BROWSE_COALESCE_TLS.active = True
        try:
            try:
                result = compute()
                holder["result"] = result
                return result
            except BaseException as exc:
                holder["exception"] = exc
                raise
        finally:
            self._BROWSE_COALESCE_TLS.active = False
            with self._active_browse_lock:
                self._active_browse_requests = max(0, self._active_browse_requests - 1)
            holder["event"].set()
            with self._browse_inflight_lock:
                self._browse_inflight.pop(fingerprint, None)

    def _warmup_should_yield(self) -> bool:
        """Return True when a foreground browse request is in flight.

        Warmup workers should pause briefly so user-facing tabs always win the
        I/O and CPU race on 8GB hardware.
        """
        with self._active_browse_lock:
            return self._active_browse_requests > 0

    def _restore_persisted_tasks(self) -> None:
        """Scan data_cache/features/ for feature outputs and restore them into
        the in-memory task store so the Feature Explorer survives API restarts.

        Two passes:
        1. task_record.json  — exact task_id written by a previous session.
        2. feature_manifest.json without a companion task_record — auto-register
           as a stable browse task (id: browse_{symbol}_{timeframe}).
        """
        features_root = settings.data_cache_path / "features"
        if not features_root.exists():
            return
        restored = 0

        # Pass 1 — restore exact task_ids from task_record.json
        for record_path in features_root.rglob(self._TASK_RECORD_NAME):
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.warning("Skipping unreadable task record %s: %s", record_path, exc)
                continue

            task_id = record.get("task_id")
            hdf5_path = record.get("hdf5_path")
            if not task_id or not hdf5_path:
                continue
            if not Path(hdf5_path).exists():
                logger.debug("Task record %s: output gone (%s), skipping", task_id, hdf5_path)
                continue
            with self._lock:
                if task_id in self._tasks:
                    continue
                self._tasks[task_id] = {
                    "task_id": task_id,
                    "status": "completed",
                    "progress": 1.0,
                    "current_stage": None,
                    "completed_stages": [],
                    "error": None,
                    "result": {
                        "feature_count": record.get("feature_count"),
                        "generation_time": record.get("generation_time"),
                        "layer_counts": record.get("layer_counts") or {},
                        "metadata": record.get("metadata") or {},
                        "hdf5_path": hdf5_path,
                    },
                    "created_at": record.get("persisted_at", ""),
                }
            restored += 1

        # Pass 2 — auto-register feature_manifest.json that have no task_record
        # Expected layout: features/{symbol}/{timeframe}/{config_hash}/feature_manifest.json
        for manifest_path in features_root.rglob("feature_manifest.json"):
            manifest_dir = manifest_path.parent
            if (manifest_dir / self._TASK_RECORD_NAME).exists():
                continue  # Already covered by Pass 1
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue

            # Derive symbol/timeframe from directory structure
            parts = manifest_dir.relative_to(features_root).parts
            if len(parts) < 3:
                continue  # Unexpected layout — skip
            symbol = parts[0]
            timeframe = parts[1]
            # Stable ID — latest-overwrite by symbol+timeframe. Older
            # browse_{symbol}_{timeframe}_{hash8} ids are ignored on restore.
            stable_id = f"browse_{symbol}_{timeframe}"
            with self._lock:
                if stable_id in self._tasks:
                    continue
                self._tasks[stable_id] = {
                    "task_id": stable_id,
                    "status": "completed",
                    "progress": 1.0,
                    "current_stage": None,
                    "completed_stages": [],
                    "error": None,
                    "result": {
                        "feature_count": manifest.get("total_features"),
                        "generation_time": None,
                        "layer_counts": {},
                        "metadata": {"symbol": symbol, "timeframe": timeframe},
                        "hdf5_path": str(manifest_path),
                    },
                    "created_at": manifest.get("created_at", ""),
                }
            restored += 1
            logger.debug(
                "Auto-registered manifest as browse task %s: %s", stable_id, manifest_path
            )

        if restored:
            logger.info("Restored %d persisted feature task(s) from disk", restored)

    def _load_task_features(self, task_id: str) -> tuple:
        """Load task features DataFrame, using an in-memory cache to avoid
        redundant HDF5/Parquet reads across multiple browse/export calls."""
        if task_id in self._df_cache:
            return self._df_cache[task_id]

        context = self._load_task_context(task_id)

        if context.get("is_cgsa"):
            df = self._load_cgsa_features_df(context)
        else:
            df = self._load_hdf5_features_df(context)

        export_meta = {
            "task_id": task_id,
            "symbol": context["symbol"],
            "timeframe": context["timeframe"],
            "generated_at": context["generated_at"],
            "feature_count": int(df.shape[1]),
            "row_count": int(df.shape[0]),
            "generation_time": context["task_result"].get("generation_time"),
            "layer_counts": context["task_result"].get("layer_counts") or {},
            "metadata": context["metadata"],
        }
        result = (df, export_meta)
        self._df_cache[task_id] = result
        logger.info("DataFrame cached for task %s (%d features, %d rows)", task_id, df.shape[1], df.shape[0])
        return result

    def _invalidate_task_cache(self, task_id: str) -> None:
        """Remove cached data for a task (called when task is deleted or regenerated)."""
        self._df_cache.pop(task_id, None)
        self._stats_cache.pop(task_id, None)
        self._stats_name_sorted_cache.pop(task_id, None)
        self._stats_name_keys_cache.pop(task_id, None)
        self._adf_cache.pop(task_id, None)
        self._feature_metadata_cache.pop(task_id, None)
        self._cgsa_catalog_cache.pop(task_id, None)
        self._cgsa_column_path_cache.pop(task_id, None)
        with self._lock:
            self._stats_warming_tasks.discard(task_id)
            self._adf_warming_tasks.discard(task_id)
            self._cgsa_stats_warming_tasks.discard(task_id)
            self._cgsa_catalog_warming_tasks.discard(task_id)

    def _get_feature_metadata_map(self, task_id: str, feature_names: List[str]) -> Dict[str, Dict[str, str]]:
        cache = self._feature_metadata_cache.setdefault(task_id, {})
        for name in feature_names:
            if name in cache:
                continue
            inferred_category = infer_category(name)
            inferred_layer = infer_layer(name)
            inferred_level = self._to_simple_level(infer_level(inferred_category))
            cache[name] = {
                "category": inferred_category,
                "layer": inferred_layer,
                "level": inferred_level,
            }
        return cache

    def _start_adf_cache_warmup(self, task_id: str, reason: str) -> None:
        """Warm per-feature ADF cache in batches to improve browse responsiveness."""
        if not HAS_STATSMODELS:
            return

        try:
            context = self._load_task_context(task_id)
            if context.get("is_cgsa"):
                logger.info("Skipping CGSA ADF warmup for task %s (reason=%s)", task_id, reason)
                return
        except Exception:
            pass

        with self._lock:
            if task_id in self._adf_warming_tasks:
                return
            self._adf_warming_tasks.add(task_id)

        def _worker() -> None:
            try:
                rows = self._build_stats_rows(task_id)
                if not rows:
                    return

                features_df, _ = self._load_task_features(task_id)
                feature_cache = self._adf_cache.setdefault(task_id, {})

                # Prioritize deterministic name-ascending order (same as default browse).
                ordered_names = [str(item.get("name", "")) for item in self._stats_name_sorted_cache.get(task_id, rows)]
                ordered_names = [name for name in ordered_names if name]

                WARM_TOP_K = 300
                BATCH_SIZE = 30
                pending_names = [name for name in ordered_names[:WARM_TOP_K] if name not in feature_cache]

                warmed = 0
                for idx in range(0, len(pending_names), BATCH_SIZE):
                    batch_names = pending_names[idx : idx + BATCH_SIZE]
                    for feature_name in batch_names:
                        if feature_name not in features_df.columns:
                            feature_cache[feature_name] = None
                            continue
                        feature_cache[feature_name] = self._compute_adf_pvalue(features_df[feature_name])
                        warmed += 1

                if warmed > 0:
                    logger.info(
                        "ADF cache warmed for task %s (%d features, reason=%s)",
                        task_id,
                        warmed,
                        reason,
                    )
            except Exception as exc:
                logger.warning("ADF warmup failed for task %s: %s", task_id, exc, exc_info=True)
            finally:
                with self._lock:
                    self._adf_warming_tasks.discard(task_id)

        thread = threading.Thread(
            target=_worker,
            daemon=True,
            name=f"adf-warm-{task_id[:8]}",
        )
        thread.start()

    def _enrich_rows_with_adf(
        self,
        task_id: str,
        rows: List[Dict[str, Any]],
        features_df: Optional[pd.DataFrame],
        compute_if_missing: bool = True,
    ) -> List[Dict[str, Any]]:
        enriched_rows: List[Dict[str, Any]] = []
        for item in rows:
            row = dict(item)
            feature_name = str(row.get("name", ""))
            adf_pvalue = self._get_adf_pvalue(
                task_id=task_id,
                feature_name=feature_name,
                features_df=features_df,
                compute_if_missing=compute_if_missing,
            )
            row["adf_pvalue"] = adf_pvalue
            row["is_stationary"] = adf_pvalue is not None and adf_pvalue < 0.05
            enriched_rows.append(row)
        return enriched_rows

    def _get_adf_pvalue(
        self,
        task_id: str,
        feature_name: str,
        features_df: Optional[pd.DataFrame],
        compute_if_missing: bool = True,
    ) -> Optional[float]:
        feature_cache = self._adf_cache.setdefault(task_id, {})
        if feature_name in feature_cache:
            return feature_cache[feature_name]

        if not compute_if_missing:
            return None

        if features_df is None:
            return None

        if feature_name not in features_df.columns:
            feature_cache[feature_name] = None
            return None

        pvalue = self._compute_adf_pvalue(features_df[feature_name])
        feature_cache[feature_name] = pvalue
        return pvalue

    def _load_task_context(self, task_id: str) -> Dict[str, Any]:
        task_result = self.get_result(task_id)
        if task_result is None:
            raise FileNotFoundError(f"Result not found: {task_id}")

        hdf5_path = task_result.get("hdf5_path")
        if not hdf5_path:
            raise FileNotFoundError(f"HDF5 path not found for task: {task_id}")

        file_path = Path(hdf5_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Feature output not found: {file_path}")

        metadata = task_result.get("metadata") or {}
        symbol = metadata.get("symbol")
        timeframe = metadata.get("timeframe")
        if not symbol or not timeframe:
            raise ValueError(f"Missing symbol/timeframe metadata for task: {task_id}")

        # Detect CGSA V7 manifest (manifest.json) vs legacy HDF5 (.h5).
        is_cgsa = file_path.suffix.lower() == ".json"
        manifest: Optional[Dict[str, Any]] = None
        manifest_dir: Optional[Path] = None

        if is_cgsa:
            try:
                raw_manifest = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise FileNotFoundError(
                    f"Failed to read CGSA manifest {file_path}: {exc}"
                ) from exc

            # V7 format: version=="7.0" and groups is a dict.
            # CGSA registry format: version==None and groups is a list.
            # When the latter, look for the companion V7 manifest under
            # data_cache/features/{symbol}/{config_hash}/manifest.json.
            if raw_manifest.get("version") != "7.0" and isinstance(
                raw_manifest.get("groups"), list
            ):
                config_hash = raw_manifest.get("config_hash")
                v7_path: Optional[Path] = None
                if config_hash:
                    candidate = (
                        settings.data_cache_path
                        / "features"
                        / symbol
                        / config_hash
                        / "manifest.json"
                    )
                    if candidate.exists():
                        v7_path = candidate
                if v7_path is not None:
                    try:
                        manifest = json.loads(v7_path.read_text(encoding="utf-8"))
                        file_path = v7_path
                        logger.debug(
                            "Redirected CGSA registry manifest to V7 manifest: %s",
                            v7_path,
                        )
                    except (OSError, ValueError) as exc:
                        logger.warning(
                            "Failed to read V7 manifest %s; falling back to registry manifest: %s",
                            v7_path, exc,
                        )
                        manifest = raw_manifest
                else:
                    # V7 manifest not yet written or lives elsewhere — keep the
                    # CGSA registry manifest; _load_cgsa_features_df handles
                    # the list format via each group's 'parquet_path' field.
                    manifest = raw_manifest
            else:
                manifest = raw_manifest

            manifest_dir = file_path.parent

        return {
            "task_id": task_id,
            "task_result": task_result,
            "metadata": metadata,
            "symbol": symbol,
            "timeframe": timeframe,
            "file_path": file_path,
            "group_path": f"{symbol}/{timeframe}",
            "generated_at": datetime.now().isoformat(),
            "is_cgsa": is_cgsa,
            "manifest": manifest,
            "manifest_dir": manifest_dir,
        }

    def _load_hdf5_features_df(self, context: Dict[str, Any]) -> pd.DataFrame:
        """Materialize a features DataFrame from a legacy single-TF HDF5 file."""
        file_path = context["file_path"]
        group_path = context["group_path"]
        with h5py.File(file_path, "r") as h5_file:
            if group_path not in h5_file:
                raise FileNotFoundError(f"Group not found in HDF5: {group_path}")
            group = h5_file[group_path]
            if "features" not in group:
                raise FileNotFoundError(f"features dataset missing: {group_path}/features")

            features = group["features"][:]
            raw_feature_names = list(group["feature_names"][:]) if "feature_names" in group else []
            feature_names = [
                name.decode("utf-8") if isinstance(name, (bytes, bytearray, np.bytes_)) else str(name)
                for name in raw_feature_names
            ]
            if len(feature_names) != features.shape[1]:
                feature_names = [f"feature_{idx}" for idx in range(features.shape[1])]

            df = pd.DataFrame(features, columns=feature_names)

            timestamps = group["timestamps"][:] if "timestamps" in group else None
            if timestamps is not None:
                timestamp_index = pd.to_datetime(timestamps, unit="s", errors="coerce")
                df.index = timestamp_index
                df.index.name = "timestamp"
        return df

    def _load_cgsa_features_df(self, context: Dict[str, Any]) -> pd.DataFrame:
        """Materialize a features DataFrame from a CGSA manifest.

        Supports three manifest formats:
        * V7 / raw_v1 (version=="7.0" or "l7_v2", groups is dict): each entry has
          ``path`` (relative path including subdirectory, e.g. ``raw/file.parquet``)
          and ``columns``. Created by feature_storage.py. ``path`` is preferred
          over ``file`` to correctly resolve artifacts inside ``raw/`` / ``processed/``.
        * CGSA registry (version==None, groups is list): each entry has
          ``parquet_path`` (absolute) and ``columns``. Created by
          cgsa_registry.save_state(). Used as fallback when V7 manifest is not
          yet available (e.g. persistence disabled or in-progress).
        """
        import pyarrow.parquet as pq  # local import keeps cold-start light

        manifest = context.get("manifest") or {}
        manifest_dir: Optional[Path] = context.get("manifest_dir")
        groups_raw = manifest.get("groups")
        if not groups_raw:
            return pd.DataFrame()

        frames: List[pd.DataFrame] = []

        if isinstance(groups_raw, dict):
            # V7 / raw_v1 format: {group_id: {"path": "subdir/file.parquet", "file": "file.parquet", "columns": [...]}}
            # Prefer "path" (relative to manifest_dir, includes subdirectory prefix) over
            # "file" (bare filename) so that artifacts inside raw/ or processed/ are
            # resolved correctly.
            for _group_id, group_meta in groups_raw.items():
                relative = group_meta.get("path") or group_meta.get("file")
                if not relative or manifest_dir is None:
                    continue
                parquet_path = manifest_dir / relative
                if not parquet_path.exists():
                    logger.warning(
                        "CGSA V7 parquet missing for task %s: %s",
                        context["task_id"], parquet_path,
                    )
                    continue
                table = pq.read_table(str(parquet_path))
                frames.append(table.to_pandas(self_destruct=True))
        else:
            # CGSA registry list format: [{"parquet_path": "...", "columns": [...]}]
            for group_meta in groups_raw:
                if not isinstance(group_meta, dict):
                    continue
                parquet_path_str = group_meta.get("parquet_path")
                if not parquet_path_str:
                    continue
                parquet_path = Path(parquet_path_str)
                if not parquet_path.exists():
                    logger.warning(
                        "CGSA registry parquet missing for task %s: %s",
                        context["task_id"], parquet_path,
                    )
                    continue
                cols = group_meta.get("columns")
                read_cols = list(cols) if cols else None
                table = pq.read_table(str(parquet_path), columns=read_cols)
                frames.append(table.to_pandas(self_destruct=True))

        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, axis=1, copy=False)

        # Defensive dedup: legacy cgsa_work manifests can contain duplicate
        # group entries (e.g. "_2" suffix groups produced by an aborted resume
        # before commit 37195bb). Concatenating those parquet files yields a
        # DataFrame with duplicated column names; downstream code that does
        # ``df[col]`` then receives a DataFrame instead of a Series and crashes
        # with "The truth value of a Series is ambiguous". Drop duplicates
        # (keep first) so subsequent endpoints see a clean column index.
        if df.columns.duplicated().any():
            duplicate_count = int(df.columns.duplicated().sum())
            logger.warning(
                "CGSA features for task %s contain %d duplicate column names; keeping first occurrence",
                context["task_id"], duplicate_count,
            )
            df = df.loc[:, ~df.columns.duplicated(keep="first")]
        return df

    def _load_cgsa_summary_fast(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Compute browse_summary inputs from parquet metadata WITHOUT decoding data.

        Returns ``None`` when statistics are unavailable, signaling the caller
        to fall back to the full DataFrame load path. Conservative: any single
        missing column-level statistic triggers fallback so we never report
        wrong nan_ratios.
        """
        import pyarrow.parquet as pq  # local import keeps cold-start light

        manifest = context.get("manifest") or {}
        manifest_dir: Optional[Path] = context.get("manifest_dir")
        groups_raw = manifest.get("groups")
        if not groups_raw:
            return None

        parquet_paths: List[Path] = []
        if isinstance(groups_raw, dict):
            for _gid, meta in groups_raw.items():
                if not isinstance(meta, dict):
                    continue
                relative = meta.get("path") or meta.get("file")
                if not relative or manifest_dir is None:
                    continue
                path = manifest_dir / relative
                if path.exists():
                    parquet_paths.append(path)
        else:
            for meta in groups_raw:
                if not isinstance(meta, dict):
                    continue
                ppath = meta.get("parquet_path")
                if not ppath:
                    continue
                path = Path(ppath)
                if path.exists():
                    parquet_paths.append(path)

        if not parquet_paths:
            return None

        columns_ordered: List[str] = []
        seen_cols: set = set()
        null_counts: Dict[str, int] = {}
        distinct_counts: Dict[str, Optional[int]] = {}
        min_max: Dict[str, tuple] = {}
        column_to_path: Dict[str, Path] = {}
        total_rows = 0

        # P2-B: read parquet footers in parallel.  Footers are small but the
        # 1,000+ files in a typical fresh-cold task dominate browse_summary
        # latency when read serially.
        from concurrent.futures import ThreadPoolExecutor as _TPE

        def _read_one_footer(path: Path) -> Optional[Dict[str, Any]]:
            try:
                pf = pq.ParquetFile(str(path))
            except Exception as exc:
                logger.warning("Failed to read parquet metadata %s: %s", path, exc)
                return None
            meta = pf.metadata
            if meta is None:
                return None
            file_columns = pf.schema_arrow.names
            n_rg = meta.num_row_groups
            per_col: Dict[str, Dict[str, Any]] = {}
            for col_idx, col in enumerate(file_columns):
                null_total = 0
                min_val = None
                max_val = None
                distinct_total: Optional[int] = 0
                bail = False
                for rg_i in range(n_rg):
                    rg_col = meta.row_group(rg_i).column(col_idx)
                    stats = rg_col.statistics
                    if stats is None or not getattr(stats, "has_null_count", False):
                        bail = True
                        break
                    null_total += stats.null_count
                    if distinct_total is not None:
                        if getattr(stats, "has_distinct_count", False):
                            distinct_total += stats.distinct_count
                        else:
                            distinct_total = None
                    if getattr(stats, "has_min_max", False):
                        s_min = stats.min
                        s_max = stats.max
                        if min_val is None:
                            min_val, max_val = s_min, s_max
                        else:
                            try:
                                if s_min < min_val:
                                    min_val = s_min
                                if s_max > max_val:
                                    max_val = s_max
                            except TypeError:
                                pass
                if bail:
                    # Signal hard fallback — caller drops to full-load path.
                    return None
                per_col[col] = {
                    "null": int(null_total),
                    "distinct": distinct_total,
                    "min": min_val,
                    "max": max_val,
                }
            return {
                "path": path,
                "num_rows": int(meta.num_rows),
                "file_columns": list(file_columns),
                "per_col": per_col,
            }

        max_workers = min(8, max(2, len(parquet_paths)))
        with _TPE(max_workers=max_workers, thread_name_prefix="cgsa-meta") as pool:
            footer_results = list(pool.map(_read_one_footer, parquet_paths))

        # Merge in original path order to preserve column ordering / first-seen wins.
        for result in footer_results:
            if result is None:
                # Statistics missing for at least one column — caller falls back.
                return None
            path = result["path"]
            file_rows = result["num_rows"]
            if total_rows == 0:
                total_rows = file_rows
            elif file_rows != total_rows:
                logger.warning(
                    "Parquet row count mismatch in CGSA task %s: %s has %d rows vs baseline %d",
                    context.get("task_id"), path, file_rows, total_rows,
                )
                total_rows = max(total_rows, file_rows)

            for col in result["file_columns"]:
                if col in seen_cols:
                    continue
                seen_cols.add(col)
                columns_ordered.append(col)
                column_to_path[col] = path
                stats = result["per_col"].get(col)
                if stats is None:
                    return None
                null_counts[col] = stats["null"]
                distinct_counts[col] = stats["distinct"]
                min_max[col] = (stats["min"], stats["max"])

        if total_rows == 0 or not columns_ordered:
            return None

        nan_ratios = pd.Series(
            {col: (null_counts[col] / total_rows) for col in columns_ordered},
            dtype=float,
        )

        constant_columns: List[str] = []
        for col in columns_ordered:
            dc = distinct_counts.get(col)
            if dc is not None and dc <= 1:
                constant_columns.append(col)
                continue
            mn, mx = min_max.get(col, (None, None))
            if mn is not None and mx is not None and mn == mx and null_counts[col] == 0:
                constant_columns.append(col)

        return {
            "total_rows": int(total_rows),
            "columns": columns_ordered,
            "nan_ratios": nan_ratios,
            "constant_columns": constant_columns,
            "column_to_path": column_to_path,
        }

    def _load_cgsa_columns_subset(
        self,
        column_to_path: Dict[str, Path],
        columns: List[str],
    ) -> pd.DataFrame:
        """Read just the requested columns from CGSA parquet files.

        Used by the fast browse_summary path for sample-based stationarity
        tests and capped correlation checks. Avoids materializing the full
        feature matrix.
        """
        import pyarrow.parquet as pq

        by_path: Dict[Path, List[str]] = {}
        for col in columns:
            path = column_to_path.get(col)
            if path is None:
                continue
            by_path.setdefault(path, []).append(col)

        frames: List[pd.DataFrame] = []
        for path, cols in by_path.items():
            try:
                table = pq.read_table(str(path), columns=cols)
                frames.append(table.to_pandas(self_destruct=True))
            except Exception as exc:
                logger.warning("Failed to load CGSA subset from %s: %s", path, exc)

        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, axis=1, copy=False)
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated(keep="first")]
        return df

    def _estimate_stationary_ratio_from_subset(self, df: pd.DataFrame) -> float:
        """Stationarity ratio over a precomputed sample DataFrame."""
        if df.empty or not HAS_STATSMODELS:
            return 0.0
        stationaries = 0
        evaluated = 0
        for column in df.columns:
            pvalue = self._compute_adf_pvalue(df[column])
            if pvalue is None:
                continue
            evaluated += 1
            if pvalue < 0.05:
                stationaries += 1
        if evaluated == 0:
            return 0.0
        return float(stationaries / evaluated)

    def _browse_summary_from_fast(
        self,
        task_id: str,
        context: Dict[str, Any],
        fast: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the browse_summary payload from CGSA parquet metadata."""
        import warnings

        columns: List[str] = fast["columns"]
        total_rows: int = fast["total_rows"]
        nan_ratios: pd.Series = fast["nan_ratios"]
        constant_features_list: List[str] = fast["constant_columns"]
        column_to_path: Dict[str, Path] = fast["column_to_path"]

        by_category: Dict[str, int] = {}
        by_level: Dict[str, int] = {}
        by_layer_raw: Dict[str, int] = {}
        for col in columns:
            cat = infer_category(col)
            layer = infer_layer(col)
            simple_level = self._to_simple_level(infer_level(cat))
            by_category[cat] = by_category.get(cat, 0) + 1
            by_layer_raw[layer] = by_layer_raw.get(layer, 0) + 1
            by_level[simple_level] = by_level.get(simple_level, 0) + 1
        by_layer = {
            "Layer 1 (Atomic)": by_layer_raw.get("layer1", 0),
            "Layer 2 (Derived)": by_layer_raw.get("layer2", 0),
            "Layer 3 (Rolling)": by_layer_raw.get("layer3", 0),
            "Layer 4 (Lag)": by_layer_raw.get("layer4", 0),
            "Layer 5 (Cross-Sect)": by_layer_raw.get("layer5", 0),
            "Layer 6 (Meta)": by_layer_raw.get("layer6", 0),
            "Layer 6.5 (Preproc)": by_layer_raw.get("layer6_5", 0),
        }

        nan_metrics = self._resolve_true_nan_quality_metrics(context, fast, nan_ratios)

        HIGH_CORR_SAMPLE_LIMIT = 500
        high_corr_pairs_count: Optional[int] = None
        if 0 < len(columns) <= HIGH_CORR_SAMPLE_LIMIT:
            try:
                subset_df = self._load_cgsa_columns_subset(column_to_path, columns)
                numeric_df = subset_df.select_dtypes(include=["number"])
                if numeric_df.shape[1]:
                    corr_abs = numeric_df.corr().abs()
                    upper = corr_abs.where(
                        np.triu(np.ones(corr_abs.shape), k=1).astype(bool)
                    )
                    high_corr_pairs_count = int((upper > 0.95).sum().sum())
            except Exception as exc:
                logger.warning("High-corr computation failed for task %s: %s", task_id, exc)

        sample_columns = columns[: min(100, len(columns))]
        try:
            adf_df = self._load_cgsa_columns_subset(column_to_path, sample_columns)
            stationary_ratio = self._estimate_stationary_ratio_from_subset(adf_df)
        except Exception as exc:
            logger.warning("Stationarity sample failed for task %s: %s", task_id, exc)
            stationary_ratio = 0.0

        quality_alerts = self._fast_quality_alerts(pd.DataFrame(), nan_ratios)

        # Background warmup so subsequent FeatureTable / Distribution tabs are
        # snappy. These are non-blocking.
        self._start_stats_cache_warmup(task_id, reason="browse_summary")
        self._start_adf_cache_warmup(task_id, reason="browse_summary")

        stats_warmup = self._get_stats_warmup_progress(
            task_id,
            total_features=len(columns),
            context=context,
        )

        task_result = context.get("task_result") or {}
        metadata = context.get("metadata") or {}

        return {
            "total_features": len(columns),
            "total_rows": int(total_rows),
            "by_category": by_category,
            "by_level": by_level,
            "by_layer": by_layer,
            "quality": {
                "nan_ratio_mean": nan_metrics["nan_ratio_mean"],
                "nan_ratio_max": nan_metrics["nan_ratio_max"],
                "nan_ratio_quantiles": nan_metrics["nan_ratio_quantiles"],
                "nan_ratio_distribution": self._nan_ratio_distribution(nan_ratios=nan_ratios),
                "constant_features": constant_features_list,
                "high_corr_pairs_count": high_corr_pairs_count,
                "stationary_ratio": stationary_ratio,
                "quality_alerts": quality_alerts,
            },
            "stats_warmup": stats_warmup,
            "generation_info": {
                "task_id": task_id,
                "symbol": context.get("symbol"),
                "timeframe": context.get("timeframe"),
                "generated_at": context.get("generated_at"),
                "generation_time": task_result.get("generation_time"),
                "config_hash": metadata.get("config_hash"),
            },
        }

    def _load_hdf5_schema(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if context.get("is_cgsa"):
            manifest = context.get("manifest") or {}
            groups_raw = manifest.get("groups")
            feature_names: List[str] = []
            if isinstance(groups_raw, dict):
                # l7_v2 format uses "row_count"; legacy V7 format uses "total_rows"
                for group_meta in groups_raw.values():
                    feature_names.extend(group_meta.get("columns") or [])
                return {
                    "feature_names": feature_names,
                    "row_count": int(manifest.get("row_count") or manifest.get("total_rows") or 0),
                }
            elif isinstance(groups_raw, list):
                # CGSA registry list format — read row count from first parquet
                import pyarrow.parquet as pq
                total_rows = 0
                for group_meta in groups_raw:
                    if not isinstance(group_meta, dict):
                        continue
                    feature_names.extend(group_meta.get("columns") or [])
                    if total_rows == 0:
                        pp = group_meta.get("parquet_path")
                        if pp and Path(pp).exists():
                            try:
                                pf = pq.ParquetFile(pp)
                                total_rows = pf.metadata.num_rows
                            except Exception:
                                pass
                return {
                    "feature_names": feature_names,
                    "row_count": total_rows,
                }
            return {"feature_names": [], "row_count": 0}
        file_path = context["file_path"]
        group_path = context["group_path"]
        with h5py.File(file_path, "r") as h5_file:
            if group_path not in h5_file:
                raise FileNotFoundError(f"Group not found in HDF5: {group_path}")
            group = h5_file[group_path]
            if "features" not in group:
                raise FileNotFoundError(f"features dataset missing: {group_path}/features")

            features_ds = group["features"]
            raw_feature_names = list(group["feature_names"][:]) if "feature_names" in group else []
            feature_names = [
                name.decode("utf-8") if isinstance(name, (bytes, bytearray, np.bytes_)) else str(name)
                for name in raw_feature_names
            ]
            if len(feature_names) != features_ds.shape[1]:
                feature_names = [f"feature_{idx}" for idx in range(features_ds.shape[1])]

            return {
                "feature_names": feature_names,
                "row_count": int(features_ds.shape[0]),
            }

    def _load_selected_feature_rows(
        self,
        context: Dict[str, Any],
        selected_features: List[str],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        if context.get("is_cgsa"):
            return self._load_cgsa_selected_rows(context, selected_features, offset, limit)

        file_path = context["file_path"]
        group_path = context["group_path"]

        with h5py.File(file_path, "r") as h5_file:
            if group_path not in h5_file:
                raise FileNotFoundError(f"Group not found in HDF5: {group_path}")

            group = h5_file[group_path]
            if "features" not in group:
                raise FileNotFoundError(f"features dataset missing: {group_path}/features")

            features_ds = group["features"]
            total_rows = int(features_ds.shape[0])

            raw_feature_names = list(group["feature_names"][:]) if "feature_names" in group else []
            all_columns = [
                name.decode("utf-8") if isinstance(name, (bytes, bytearray, np.bytes_)) else str(name)
                for name in raw_feature_names
            ]
            if len(all_columns) != features_ds.shape[1]:
                all_columns = [f"feature_{idx}" for idx in range(features_ds.shape[1])]

            missing = [name for name in selected_features if name not in set(all_columns)]
            if missing:
                raise ValueError(f"Invalid features: {missing}")

            start = min(offset, total_rows)
            end = min(offset + limit, total_rows)

            column_to_index = {name: idx for idx, name in enumerate(all_columns)}
            selected_indices = [column_to_index[name] for name in selected_features]

            sorted_pairs = sorted(enumerate(selected_indices), key=lambda item: item[1])
            sorted_positions = [item[0] for item in sorted_pairs]
            sorted_indices = [item[1] for item in sorted_pairs]

            chunk_sorted = features_ds[start:end, sorted_indices]
            reverse_order = np.argsort(sorted_positions)
            chunk_values = chunk_sorted[:, reverse_order]

            timestamps = []
            if "timestamps" in group:
                ts = pd.to_datetime(group["timestamps"][start:end], unit="s", errors="coerce")
                timestamps = [value.isoformat() if pd.notna(value) else None for value in ts]
            else:
                timestamps = [str(idx) for idx in range(start, end)]

            data_rows: List[Dict[str, Any]] = []
            for row_idx in range(chunk_values.shape[0]):
                row_payload: Dict[str, Any] = {"timestamp": timestamps[row_idx]}
                for col_idx, feature_name in enumerate(selected_features):
                    row_payload[feature_name] = self._safe_float(chunk_values[row_idx, col_idx])
                data_rows.append(row_payload)

            return {
                "total_rows": total_rows,
                "offset": offset,
                "limit": limit,
                "features": selected_features,
                "rows": data_rows,
            }

    def _load_cgsa_selected_rows(
        self,
        context: Dict[str, Any],
        selected_features: List[str],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """CGSA Parquet variant: read only the parquet groups that contain
        the requested columns, then slice rows. Falls back to the cached
        full DataFrame when it is already materialized."""
        task_id = context["task_id"]

        # Reuse cache if present (typical after stats warmup) — avoids re-reading parquet.
        cached = self._df_cache.get(task_id)
        if cached is not None:
            df_full = cached[0]
            missing = [name for name in selected_features if name not in df_full.columns]
            if missing:
                raise ValueError(f"Invalid features: {missing}")
            total_rows = int(df_full.shape[0])
            start = min(offset, total_rows)
            end = min(offset + limit, total_rows)
            slice_df = df_full.iloc[start:end][selected_features]
            chunk_values = slice_df.to_numpy()
            timestamps = self._format_cgsa_timestamps(df_full.index, start, end)
        else:
            selected_df, total_rows = self._load_cgsa_selected_df(
                context=context,
                selected_features=selected_features,
            )
            start = min(offset, total_rows)
            end = min(offset + limit, total_rows)
            slice_df = selected_df.iloc[start:end][selected_features]
            chunk_values = slice_df.to_numpy()
            timestamps = self._load_cgsa_kline_timestamps(context, start, end, total_rows)

        data_rows: List[Dict[str, Any]] = []
        for row_idx in range(chunk_values.shape[0]):
            row_payload: Dict[str, Any] = {"timestamp": timestamps[row_idx]}
            for col_idx, feature_name in enumerate(selected_features):
                row_payload[feature_name] = self._safe_float(chunk_values[row_idx, col_idx])
            data_rows.append(row_payload)

        return {
            "total_rows": total_rows,
            "offset": offset,
            "limit": limit,
            "features": selected_features,
            "rows": data_rows,
        }

    def _load_cgsa_selected_df(
        self,
        context: Dict[str, Any],
        selected_features: List[str],
    ) -> tuple[pd.DataFrame, int]:
        """Load only selected CGSA feature columns from parquet."""
        import pyarrow.parquet as pq

        task_id = context["task_id"]
        manifest = context.get("manifest") or {}
        manifest_dir: Optional[Path] = context.get("manifest_dir")
        groups_raw = manifest.get("groups")
        if not groups_raw:
            raise FileNotFoundError(f"Empty CGSA manifest for task {task_id}")

        selected_set = set(selected_features)
        column_to_file: Dict[str, Path] = {}
        total_rows = int(manifest.get("total_rows") or 0)

        if isinstance(groups_raw, dict):
            for group_meta in groups_raw.values():
                if not isinstance(group_meta, dict):
                    continue
                # Prefer "path" (relative with subdirectory prefix, e.g. "raw/file.parquet")
                # over "file" (bare filename).  Mirrors the logic in _load_cgsa_summary_fast.
                relative = group_meta.get("path") or group_meta.get("file")
                if not relative or manifest_dir is None:
                    continue
                parquet_path = manifest_dir / relative
                for col in group_meta.get("columns") or []:
                    if col in selected_set and col not in column_to_file:
                        column_to_file[col] = parquet_path
        else:
            for group_meta in groups_raw:
                if not isinstance(group_meta, dict):
                    continue
                pp = group_meta.get("parquet_path")
                if not pp:
                    continue
                parquet_path = Path(pp)
                for col in group_meta.get("columns") or []:
                    if col in selected_set and col not in column_to_file:
                        column_to_file[col] = parquet_path
                if total_rows == 0 and parquet_path.exists():
                    try:
                        total_rows = int(pq.ParquetFile(str(parquet_path)).metadata.num_rows)
                    except Exception:
                        pass

        missing = [name for name in selected_features if name not in column_to_file]
        if missing:
            raise ValueError(f"Invalid features: {missing}")

        file_to_cols: Dict[Path, List[str]] = {}
        for col in selected_features:
            file_to_cols.setdefault(column_to_file[col], []).append(col)

        partial_frames: List[pd.DataFrame] = []
        if len(file_to_cols) > 1:
            # Parallel I/O when features span multiple parquet files.
            from concurrent.futures import ThreadPoolExecutor

            def _read_one(args: tuple) -> pd.DataFrame:
                _path, _cols = args
                return pq.read_table(str(_path), columns=_cols).to_pandas(self_destruct=True)

            with ThreadPoolExecutor(max_workers=min(4, len(file_to_cols))) as _pool:
                partial_frames = list(_pool.map(_read_one, file_to_cols.items()))
        else:
            for parquet_path, cols in file_to_cols.items():
                table = pq.read_table(str(parquet_path), columns=cols)
                partial_frames.append(table.to_pandas(self_destruct=True))

        if not partial_frames:
            return pd.DataFrame(columns=selected_features), total_rows

        combined = pd.concat(partial_frames, axis=1, copy=False)
        if combined.columns.duplicated().any():
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        if total_rows == 0:
            total_rows = int(combined.shape[0])
        return combined[selected_features], total_rows

    def _load_cgsa_kline_timestamps(
        self,
        context: Dict[str, Any],
        start: int,
        end: int,
        expected_rows: int,
    ) -> List[str]:
        """Load exact timestamps for CGSA rows from the Feature K-line cache.

        CGSA parquet feature shards do not store a timestamp column. Returning
        row numbers here corrupts the time axis, so fail loudly if the canonical
        kline timestamp source is unavailable or length-mismatched.
        """
        symbol = context.get("symbol")
        timeframe = context.get("timeframe")
        if not symbol or not timeframe:
            raise ValueError("Missing symbol/timeframe for CGSA timestamp lookup")

        h5_path = settings.data_cache_path / "feature_klines" / "kline_cache.h5"
        dataset_path = f"{symbol}/{timeframe}/data"
        if not h5_path.exists():
            raise FileNotFoundError(f"Feature kline cache not found: {h5_path}")

        with h5py.File(h5_path, "r") as h5_file:
            if dataset_path not in h5_file:
                raise FileNotFoundError(f"Kline dataset not found: {dataset_path}")
            dataset = h5_file[dataset_path]
            if int(dataset.shape[0]) != int(expected_rows):
                raise ValueError(
                    f"Kline timestamp length mismatch for {dataset_path}: "
                    f"{dataset.shape[0]} != {expected_rows}"
                )
            if "timestamp" not in dataset.dtype.names:
                raise ValueError(f"Kline dataset has no timestamp field: {dataset_path}")
            ts_values = dataset["timestamp"][start:end]

        ts = pd.to_datetime(ts_values, unit="s", errors="coerce")
        if ts.isna().any():
            raise ValueError(f"Invalid timestamps in kline cache: {dataset_path}")
        return [value.isoformat() for value in ts]

    @staticmethod
    def _format_cgsa_timestamps(index: pd.Index, start: int, end: int) -> List[str]:
        """Best-effort timestamp formatter for CGSA preview rows."""
        if isinstance(index, pd.DatetimeIndex):
            return [
                value.isoformat() if pd.notna(value) else None
                for value in index[start:end]
            ]
        return [str(value) for value in index[start:end]]

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if np.isfinite(number):
            return number
        return None

    @staticmethod
    def _sortable_value(value: Any) -> Any:
        if value is None:
            return float("inf")
        if isinstance(value, (int, float, np.number)):
            return float(value)
        return str(value)

    @staticmethod
    def _to_simple_level(level: str) -> str:
        level_upper = level.upper()
        if level_upper.startswith("L1"):
            return "L1"
        if level_upper.startswith("L2"):
            return "L2"
        if level_upper.startswith("L3"):
            return "L3"
        return "L1"

    def _compute_adf_pvalue(self, series: pd.Series) -> Optional[float]:
        if not HAS_STATSMODELS:
            return None

        # Defensive: when caller selects a duplicated column name from a wide
        # DataFrame, ``df[name]`` returns a DataFrame. Pick the first column so
        # subsequent ``.replace()/.dropna()/.nunique()`` ops stay scalar-safe.
        if isinstance(series, pd.DataFrame):
            if series.shape[1] == 0:
                return None
            series = series.iloc[:, 0]

        clean = series.replace([np.inf, -np.inf], np.nan).dropna()
        if clean.shape[0] < 30:
            return None

        if clean.shape[0] > 500:
            clean = clean.iloc[-500:]

        if clean.nunique(dropna=True) <= 1:
            return None

        try:
            _, pvalue, *_ = adfuller(clean.to_numpy(), autolag="AIC")
            return self._safe_float(pvalue)
        except Exception:
            return None

    def _estimate_stationary_ratio(self, features_df: pd.DataFrame) -> float:
        if features_df.empty or not HAS_STATSMODELS:
            return 0.0

        sample_columns = list(features_df.columns[: min(100, features_df.shape[1])])
        if not sample_columns:
            return 0.0

        stationaries = 0
        evaluated = 0
        for column in sample_columns:
            pvalue = self._compute_adf_pvalue(features_df[column])
            if pvalue is None:
                continue
            evaluated += 1
            if pvalue < 0.05:
                stationaries += 1

        if evaluated == 0:
            return 0.0
        return float(stationaries / evaluated)

    @staticmethod
    def _find_constant_features(features_df: pd.DataFrame) -> List[str]:
        constants: List[str] = []
        for column in features_df.columns:
            series = features_df[column]
            if series.nunique(dropna=True) <= 1:
                constants.append(column)
        return constants

    @staticmethod
    def _nan_ratio_distribution(
        features_df: Optional[pd.DataFrame] = None,
        nan_ratios: Optional["pd.Series"] = None,
    ) -> List[float]:
        """Histogram of NaN ratios across feature columns.

        Accepts either a DataFrame (legacy callers) or a precomputed
        ``nan_ratios`` Series (fast-path callers) so we don't traverse a
        200k-column frame twice.
        """
        bins = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0]
        if nan_ratios is not None:
            nan_array = nan_ratios.to_numpy()
        elif features_df is not None and not features_df.empty:
            nan_array = features_df.isna().mean().to_numpy()
        else:
            return []
        counts, _ = np.histogram(nan_array, bins=bins)
        total = nan_array.shape[0]
        if total == 0:
            return [0.0 for _ in counts]
        return [float(value / total) for value in counts]

    def _csv_chunk_generator_from_hdf5(
        self,
        context: Dict[str, Any],
        selected_columns: List[str],
        max_rows: int,
        export_meta: Dict[str, Any],
        include_metadata_header: bool,
        raw_df: Optional[pd.DataFrame] = None,
        raw_columns: Optional[List[str]] = None,
    ) -> Generator[str, None, None]:
        task_id = context["task_id"]
        _raw_columns: List[str] = raw_columns or []

        if include_metadata_header:
            yield f"# task_id: {task_id}\n"
            yield f"# symbol: {export_meta.get('symbol', 'unknown')}\n"
            yield f"# timeframe: {export_meta.get('timeframe', 'unknown')}\n"
            yield f"# feature_count: {export_meta.get('feature_count', 0)}\n"
            yield f"# row_count: {export_meta.get('row_count', 0)}\n"
            yield f"# generated_at: {export_meta.get('generated_at', '')}\n"
            if _raw_columns:
                yield f"# datasource_columns: {','.join(_raw_columns)}\n"

        header = "timestamp," + (",".join(_raw_columns) + "," if _raw_columns else "") + ",".join(selected_columns) + "\n"
        yield header

        chunk_size = 10_000

        if context.get("is_cgsa"):
            # CGSA path: read parquet groups via the cached DataFrame loader
            # (faster on repeat calls; columns are already projected).
            df_full, _ = self._load_task_features(task_id)
            invalid = [c for c in selected_columns if c not in df_full.columns]
            if invalid:
                raise ValueError(
                    f"Invalid columns: {invalid}. Available columns count: {len(df_full.columns)}"
                )
            view = df_full[selected_columns].iloc[:max_rows]

            # CGSA parquet files have no timestamp column; attach datetime index
            # from the kline cache so the CSV timestamp column shows real dates.
            if not isinstance(view.index, pd.DatetimeIndex):
                try:
                    ts_list = self._load_cgsa_kline_timestamps(
                        context, 0, len(view), len(df_full)
                    )
                    view = view.copy()
                    view.index = pd.to_datetime(ts_list)
                    view.index.name = "timestamp"
                except Exception as _ts_exc:
                    logger.warning(
                        "[CGSA CSV] Cannot attach datetime index for task %s; "
                        "falling back to integer row index: %s",
                        task_id, _ts_exc,
                    )

            for start in range(0, len(view), chunk_size):
                chunk_df = view.iloc[start:start + chunk_size]
                if raw_df is not None and _raw_columns:
                    try:
                        raw_chunk = raw_df.reindex(chunk_df.index)[_raw_columns]
                    except Exception:
                        raw_chunk = pd.DataFrame(index=chunk_df.index, columns=_raw_columns)
                    chunk_df = pd.concat([raw_chunk, chunk_df], axis=1)
                buffer = io.StringIO()
                chunk_df.to_csv(buffer, header=False, index=True)
                yield buffer.getvalue()
            return

        file_path = context["file_path"]
        group_path = context["group_path"]

        with h5py.File(file_path, "r") as h5_file:
            group = h5_file[group_path]
            features_ds = group["features"]
            timestamps_ds = group["timestamps"] if "timestamps" in group else None

            all_columns = list(group["feature_names"][:]) if "feature_names" in group else []
            normalized_columns = [
                value.decode("utf-8") if isinstance(value, (bytes, bytearray, np.bytes_)) else str(value)
                for value in all_columns
            ]
            column_to_index = {name: idx for idx, name in enumerate(normalized_columns)}
            selected_indices = [column_to_index[name] for name in selected_columns]
            sorted_pairs = sorted(enumerate(selected_indices), key=lambda item: item[1])
            sorted_positions = [item[0] for item in sorted_pairs]
            sorted_indices = [item[1] for item in sorted_pairs]

            for start in range(0, max_rows, chunk_size):
                end = min(start + chunk_size, max_rows)
                chunk_sorted = features_ds[start:end, sorted_indices]
                reverse_order = np.argsort(sorted_positions)
                chunk_values = chunk_sorted[:, reverse_order]

                if timestamps_ds is not None:
                    ts_chunk = timestamps_ds[start:end]
                    # Auto-detect unit: feature factory stores Unix seconds (~1.7e9).
                    # Binance raw ms timestamps would be ~1.7e12.
                    unit = "ms" if len(ts_chunk) > 0 and ts_chunk[0] > 1e12 else "s"
                    ts = pd.to_datetime(ts_chunk, unit=unit, errors="coerce")
                    index = pd.Index(ts, name="timestamp")
                else:
                    index = pd.Index(range(start, end), name="timestamp")

                chunk_df = pd.DataFrame(chunk_values, columns=selected_columns, index=index)

                # Prepend raw datasource columns when requested
                if raw_df is not None and _raw_columns:
                    try:
                        raw_chunk = raw_df.reindex(chunk_df.index)[_raw_columns]
                    except Exception:
                        raw_chunk = pd.DataFrame(index=chunk_df.index, columns=_raw_columns)
                    chunk_df = pd.concat([raw_chunk, chunk_df], axis=1)

                buffer = io.StringIO()
                chunk_df.to_csv(buffer, header=False, index=True)
                yield buffer.getvalue()


feature_factory_service = FeatureFactoryService()
