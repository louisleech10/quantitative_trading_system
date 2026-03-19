"""
Feature Factory Service - Feature Factory 任務與配置管理
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import os
import threading
import uuid
from bisect import bisect_right
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

import h5py
import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.stattools import adfuller
    HAS_STATSMODELS = True
except Exception:
    HAS_STATSMODELS = False

from api.core.logging import get_logger
from momentum.DataExtraction.parallel_search_engine import FailureType, classify_error
from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
from momentum.FeatureEngineering.mcp.feature_factory_mcp import FeatureFactoryMCP
from api.services.feature_export_service import FeatureExportService


logger = get_logger("api.feature_factory_service")


class FeatureFactoryService:
    """Feature Factory service for task management and config operations."""

    def __init__(self):
        self._factory = create_feature_factory()
        self._config_manager = self._factory.config_manager
        self._mcp = FeatureFactoryMCP(self._factory, self._config_manager)
        self._export_service = FeatureExportService()
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
                ),
            )

            summary = self._summarize_result(result)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["result"] = summary

            # Precompute Feature Table stats as soon as generation completes.
            # This keeps first table open responsive without changing any metrics.
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
            )

        new_result = self._factory.generate_features(
            symbol=symbol,
            timeframe=timeframe,
            config_override=config_override,
            force_regenerate=force_regenerate,
            progress_callback=progress_callback,
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
    ) -> FeatureGenerationResult:
        shadow_factory = create_feature_factory()
        # Shadow path must not overwrite persisted output.
        shadow_factory._storage.save_factory_output = lambda *_args, **_kwargs: ""
        return self._run_with_env_overrides(
            shadow_factory,
            symbol=symbol,
            timeframe=timeframe,
            config_override=config_override,
            force_regenerate=True,
            progress_callback=None,
            env_overrides=self._old_path_env_overrides(),
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
    ) -> FeatureGenerationResult:
        with self._temporary_environ(env_overrides):
            return factory.generate_features(
                symbol=symbol,
                timeframe=timeframe,
                config_override=config_override,
                force_regenerate=force_regenerate,
                progress_callback=progress_callback,
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
        # Keep old behavior: no Layer1 parallel, no Layer3 chunking.
        # Layer4 chunk/batch use large values to approximate non-chunked flow.
        return {
            "FFACT_LAYER1_PARALLEL": "0",
            "FFACT_LAYER3_CHUNK_SIZE": "0",
            "FFACT_LAYER4_CHUNK_SIZE": "1000000000",
            "FFACT_LAYER4_LAG_BATCH_SIZE": "1000000000",
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
    ) -> Dict[str, Any]:
        """Build CSV export stream payload for API route."""
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

        export_meta = {
            "task_id": task_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "generated_at": context["generated_at"],
            "feature_count": len(selected_columns),
            "row_count": row_count,
        }

        generator = self._csv_chunk_generator_from_hdf5(
            context=context,
            selected_columns=selected_columns,
            max_rows=row_count,
            export_meta=export_meta,
            include_metadata_header=include_metadata_header,
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
        return self._export_service.build_json_report(
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
        return self._export_service.build_markdown_report(
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
        if sort_by and sort_by not in {"nan_ratio", "std", "skewness", "kurtosis", "name", "mean"}:
            raise ValueError(f"Invalid sort_by: {sort_by}")
        if sort_order not in {"asc", "desc"}:
            raise ValueError(f"Invalid sort_order: {sort_order}")
        if detail_level not in {"full", "table"}:
            raise ValueError(f"Invalid detail_level: {detail_level}")

        normalized_category = (category or "").strip()
        normalized_level = (level or "").strip()
        normalized_search = (search or "").strip()
        normalized_cursor = (cursor or "").strip() or None

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

        # table: only return columns currently required by Feature Table.
        keys = {
            "name",
            "category",
            "level",
            "layer",
            "nan_ratio",
            "std",
            "skewness",
            "kurtosis",
        }
        projected: List[Dict[str, Any]] = []
        for row in rows:
            projected.append({k: row.get(k) for k in keys})
        return projected

    def browse_feature_data(
        self,
        task_id: str,
        features: List[str],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Return time series data for selected features."""
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
        if len(features) == 0:
            raise ValueError("features cannot be empty")
        if len(features) > 50:
            raise ValueError("features count exceeds limit 50")
        if method not in {"pearson", "spearman", "kendall"}:
            raise ValueError(f"Invalid correlation method: {method}")

        df, _ = self._load_task_features(task_id)
        missing = [name for name in features if name not in df.columns]
        if missing:
            raise ValueError(f"Invalid features: {missing}")

        selected = df[features]
        corr_df = selected.corr(method=method).fillna(0.0)

        return {
            "features": list(corr_df.columns),
            "method": method,
            "matrix": corr_df.to_numpy().tolist(),
        }

    def browse_distribution(self, task_id: str, feature: str, n_bins: int) -> Dict[str, Any]:
        """Return histogram payload for one feature."""
        df, _ = self._load_task_features(task_id)
        if feature not in df.columns:
            raise ValueError(f"Invalid feature: {feature}")

        series = df[feature].dropna()
        if series.empty:
            bins = np.array([])
            edges = np.array([])
        else:
            bins, edges = np.histogram(series.to_numpy(), bins=n_bins)

        adf_pvalue = self._get_adf_pvalue(task_id=task_id, feature_name=feature, features_df=df) if HAS_STATSMODELS else None

        return {
            "feature": feature,
            "n_bins": n_bins,
            "bins": bins.tolist(),
            "edges": edges.tolist(),
            "stats": {
                "count": int(series.shape[0]),
                "nan_ratio": float(df[feature].isna().mean()),
                "mean": self._safe_float(df[feature].mean()),
                "std": self._safe_float(df[feature].std()),
                "min": self._safe_float(df[feature].min()),
                "q25": self._safe_float(df[feature].quantile(0.25)),
                "median": self._safe_float(df[feature].median()),
                "q75": self._safe_float(df[feature].quantile(0.75)),
                "max": self._safe_float(df[feature].max()),
                "skewness": self._safe_float(df[feature].skew()),
                "kurtosis": self._safe_float(df[feature].kurt()),
                "adf_pvalue": adf_pvalue,
                "is_stationary": adf_pvalue is not None and adf_pvalue < 0.05,
            },
        }

    def browse_nan_pattern(self, task_id: str, sample_features: int) -> Dict[str, Any]:
        """Return missing-value matrix payload for sampled features."""
        df, _ = self._load_task_features(task_id)
        if df.empty or df.shape[1] == 0:
            return {"features": [], "timestamps": [], "matrix": [], "nan_ratios": []}

        nan_ratio_series = df.isna().mean().sort_values(ascending=False)
        selected = list(nan_ratio_series.index[:sample_features])
        selected_df = df[selected]

        matrix = selected_df.isna().to_numpy().tolist()
        timestamps = [str(index) for index in selected_df.index.tolist()]

        return {
            "features": selected,
            "timestamps": timestamps,
            "matrix": matrix,
            "nan_ratios": [float(nan_ratio_series[name]) for name in selected],
        }

    def browse_summary(self, task_id: str) -> Dict[str, Any]:
        """Return feature explorer summary dashboard payload.

        Rewritten to avoid calling build_json_report() which is prohibitively slow
        for large feature sets (36k+ features).  All computation here is O(N) or
        uses vectorized pandas/numpy — no full correlation matrix.
        """
        import warnings
        features_df, export_meta = self._load_task_features(task_id)

        # --- Category / layer / level breakdown (name parsing fast-path) ---
        by_category: Dict[str, int] = {}
        by_level: Dict[str, int] = {}
        by_layer_raw: Dict[str, int] = {}
        for col in features_df.columns:
            cat = self._export_service._infer_category(col)
            layer = self._export_service._infer_layer(col)
            level_raw = self._export_service._infer_level(cat)
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
            nan_ratio_mean = float(nan_ratios.mean())
            nan_ratio_max = float(nan_ratios.max()) if len(nan_ratios) else 0.0

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

        return {
            "total_features": int(features_df.shape[1]),
            "total_rows": int(features_df.shape[0]),
            "by_category": by_category,
            "by_level": by_level,
            "by_layer": by_layer,
            "quality": {
                "nan_ratio_mean": nan_ratio_mean,
                "nan_ratio_max": nan_ratio_max,
                "nan_ratio_distribution": self._nan_ratio_distribution(features_df),
                "constant_features": constant_features_list,
                "high_corr_pairs_count": high_corr_pairs_count,
                "stationary_ratio": stationary_ratio,
                "quality_alerts": quality_alerts,
            },
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

    def _load_task_features(self, task_id: str) -> tuple:
        """Load task features DataFrame, using an in-memory cache to avoid
        redundant HDF5 reads across multiple browse/export calls."""
        if task_id in self._df_cache:
            return self._df_cache[task_id]

        context = self._load_task_context(task_id)
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
        with self._lock:
            self._stats_warming_tasks.discard(task_id)
            self._adf_warming_tasks.discard(task_id)

    def _get_feature_metadata_map(self, task_id: str, feature_names: List[str]) -> Dict[str, Dict[str, str]]:
        cache = self._feature_metadata_cache.setdefault(task_id, {})
        for name in feature_names:
            if name in cache:
                continue
            inferred_category = self._export_service._infer_category(name)
            inferred_layer = self._export_service._infer_layer(name)
            inferred_level = self._to_simple_level(self._export_service._infer_level(inferred_category))
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
            raise FileNotFoundError(f"HDF5 file not found: {file_path}")

        metadata = task_result.get("metadata") or {}
        symbol = metadata.get("symbol")
        timeframe = metadata.get("timeframe")
        if not symbol or not timeframe:
            raise ValueError(f"Missing symbol/timeframe metadata for task: {task_id}")

        return {
            "task_id": task_id,
            "task_result": task_result,
            "metadata": metadata,
            "symbol": symbol,
            "timeframe": timeframe,
            "file_path": file_path,
            "group_path": f"{symbol}/{timeframe}",
            "generated_at": datetime.now().isoformat(),
        }

    def _load_hdf5_schema(self, context: Dict[str, Any]) -> Dict[str, Any]:
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
    def _nan_ratio_distribution(features_df: pd.DataFrame) -> List[float]:
        if features_df.empty:
            return []
        bins = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0]
        nan_ratios = features_df.isna().mean().to_numpy()
        counts, _ = np.histogram(nan_ratios, bins=bins)
        total = nan_ratios.shape[0]
        if total == 0:
            return [0.0 for _ in counts]
        return [float(value / total) for value in counts]

    @staticmethod
    def _csv_chunk_generator_from_hdf5(
        context: Dict[str, Any],
        selected_columns: List[str],
        max_rows: int,
        export_meta: Dict[str, Any],
        include_metadata_header: bool,
    ) -> Generator[str, None, None]:
        task_id = context["task_id"]
        if include_metadata_header:
            yield f"# task_id: {task_id}\n"
            yield f"# symbol: {export_meta.get('symbol', 'unknown')}\n"
            yield f"# timeframe: {export_meta.get('timeframe', 'unknown')}\n"
            yield f"# feature_count: {export_meta.get('feature_count', 0)}\n"
            yield f"# row_count: {export_meta.get('row_count', 0)}\n"
            yield f"# generated_at: {export_meta.get('generated_at', '')}\n"

        header = "timestamp," + ",".join(selected_columns) + "\n"
        yield header

        file_path = context["file_path"]
        group_path = context["group_path"]
        chunk_size = 10_000

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
                buffer = io.StringIO()
                chunk_df.to_csv(buffer, header=False, index=True)
                yield buffer.getvalue()


feature_factory_service = FeatureFactoryService()
