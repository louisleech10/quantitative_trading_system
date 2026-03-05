"""
Feature Factory Service - Feature Factory 任務與配置管理
"""

from __future__ import annotations

import asyncio
import io
import threading
import uuid
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
                lambda: self._factory.generate_features(
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

        rows: List[Dict[str, Any]] = []
        for column in features_df.columns:
            inferred_category = self._export_service._infer_category(column)
            inferred_layer = self._export_service._infer_layer(column)
            inferred_level = self._to_simple_level(self._export_service._infer_level(inferred_category))
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
    ) -> Dict[str, Any]:
        """Browse feature list with pagination/filter/sorting."""
        if sort_by and sort_by not in {"nan_ratio", "std", "skewness", "kurtosis", "name", "mean"}:
            raise ValueError(f"Invalid sort_by: {sort_by}")
        if sort_order not in {"asc", "desc"}:
            raise ValueError(f"Invalid sort_order: {sort_order}")

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

        if HAS_STATSMODELS:
            features_df, _ = self._load_task_features(task_id)
            for item in page_rows:
                adf_pvalue = self._compute_adf_pvalue(features_df[item["name"]])
                item["adf_pvalue"] = adf_pvalue
                item["is_stationary"] = adf_pvalue is not None and adf_pvalue < 0.05

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "filters_applied": {
                "category": category,
                "level": level,
                "search": search,
            },
            "features": page_rows,
        }

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

        adf_pvalue = self._compute_adf_pvalue(df[feature]) if HAS_STATSMODELS else None

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

        # --- Category / layer / level breakdown (fast string parsing) ----------
        by_category: Dict[str, int] = {}
        by_level_raw: Dict[str, int] = {}
        by_layer_raw: Dict[str, int] = {}
        for col in features_df.columns:
            cat = self._export_service._infer_category(col)
            layer = self._export_service._infer_layer(col)
            level_raw = self._export_service._infer_level(cat)
            by_category[cat] = by_category.get(cat, 0) + 1
            by_layer_raw[layer] = by_layer_raw.get(layer, 0) + 1
            by_level_raw[level_raw] = by_level_raw.get(level_raw, 0) + 1

        by_level = {self._to_simple_level(k): v for k, v in by_level_raw.items()}
        by_layer = {
            "layer1": by_layer_raw.get("layer1_atomic", 0),
            "layer2": by_layer_raw.get("layer2_derived", 0),
            "layer3": by_layer_raw.get("layer3_rolling", 0),
            "layer4": by_layer_raw.get("layer4_lag", 0),
            "layer5": by_layer_raw.get("layer5_cross_sectional", 0),
            "layer6": by_layer_raw.get("layer6_meta", 0),
            "layer6_5": by_layer_raw.get("layer6_5_preprocessing", 0),
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
