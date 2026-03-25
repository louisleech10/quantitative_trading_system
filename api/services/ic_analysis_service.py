"""IC analysis service for task management."""

from __future__ import annotations

import asyncio
import json
import math
import threading
import uuid
from io import BytesIO
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import h5py
import numpy as np
import pandas as pd

from api.core.logging import get_logger
from api.models.ic_models import DeepAnalysisRequest, ICAnalyzeRequest, ICFullAnalysisRequest
from momentum.factories import create_feature_library, create_ic_analyzer
from momentum.Analysis.ic_reporter import ICReporter


logger = get_logger("api.ic_analysis_service")


class ICAnalysisService:
    """IC analysis service for async task execution."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()
        self._last_task_id: Optional[str] = None
        self._feature_library = create_feature_library()

    async def start_analysis(self, request: ICAnalyzeRequest) -> Dict[str, str]:
        """Start IC analysis task."""
        task_id = str(uuid.uuid4())
        config_override = self._build_config_override(request)
        analyzer = create_ic_analyzer(config_override)

        task_info = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "current_step": None,
            "error": None,
            "result": None,
            "deep_analysis_result": None,
            "analyzer": analyzer,
            "applied_tier": (request.feature_tiers.active_preset if request.feature_tiers else "intermediate"),
            "created_at": datetime.now().isoformat(),
        }

        with self._lock:
            self._tasks[task_id] = task_info
            self._last_task_id = task_id

        logger.info("IC analysis task started: %s", task_id)
        asyncio.create_task(self._run_analysis(task_id, analyzer, request, config_override))

        return {"task_id": task_id, "status": "running"}

    async def _run_analysis(
        self,
        task_id: str,
        analyzer: Any,
        request: ICAnalyzeRequest,
        config_override: Optional[Dict[str, Any]],
    ) -> None:
        """Run IC analysis in background."""

        def progress_callback(payload: Dict[str, Any]) -> None:
            stage_name = payload.get("stage_name") or payload.get("stage")
            progress = float(payload.get("progress", 0.0))
            message = payload.get("message")
            current_step = payload.get("module_name") or payload.get("current_step") or stage_name

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["current_stage"] = stage_name
                task_info["current_step"] = current_step
                task_info["progress"] = progress
                task_info["status"] = "running"

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": stage_name,
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            })

        try:
            if request.mode == "cross_sectional":
                if not request.timeframe:
                    raise ValueError("timeframe is required for cross_sectional mode")
                if not request.symbols or len(request.symbols) < 2:
                    raise ValueError("cross_sectional mode requires at least 2 symbols")

                multi_features = self._feature_library.load_multi(request.symbols, request.timeframe)
                frames: List[pd.DataFrame] = []
                for symbol, frame in multi_features.items():
                    if frame is None or frame.empty:
                        raise ValueError(f"Feature data is empty for {symbol}/{request.timeframe}")
                    symbol_frame = frame.copy()
                    symbol_frame["_symbol"] = symbol
                    frames.append(symbol_frame)

                cross_df = pd.concat(frames, axis=0)
                cross_df = cross_df.set_index("_symbol", append=True)

                report = analyzer.analyze_cross_sectional(
                    features=cross_df,
                    labels_path=request.labels_path,
                    config_override=config_override,
                    progress_callback=progress_callback,
                )
            else:
                features_path = request.features_path
                if not features_path and request.symbol and request.timeframe:
                    try:
                        entry = self._feature_library._registry.find_latest(request.symbol, request.timeframe)
                    except Exception as exc:
                        logger.warning("FeatureLibrary lookup failed: %s", exc)
                        entry = None

                    if entry:
                        resolved_path = str(entry.get("hdf5_relative_path") or "")
                        if resolved_path and not Path(resolved_path).is_absolute():
                            resolved_path = str((Path.cwd() / resolved_path).resolve())
                        features_path = resolved_path

                if not features_path:
                    raise ValueError("features_path is required when FeatureLibrary symbol/timeframe is unavailable")

                report = analyzer.analyze(
                    features_path=features_path,
                    labels_path=request.labels_path,
                    meta_path=request.meta_path,
                    config_override=config_override,
                    progress_callback=progress_callback,
                    kline_reader=None,
                )

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["result"] = report

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "completed",
                "progress": 1.0,
                "message": "completed",
                "status": "completed",
            })

            logger.info("IC analysis task completed: %s", task_id)

        except Exception as exc:
            logger.error("IC analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["current_stage"] = "failed"
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            return {
                "task_id": task_info["task_id"],
                "status": task_info["status"],
                "progress": task_info.get("progress", 0.0),
                "current_stage": task_info.get("current_stage"),
                "current_step": task_info.get("current_step"),
                "applied_tier": task_info.get("applied_tier", "intermediate"),
                "error": task_info.get("error"),
            }

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task result."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            result = task_info.get("result")

        if result is None:
            return None

        normalized = self._to_json_compatible(result)
        if isinstance(normalized, dict):
            return normalized
        return {"raw": normalized}

    def export_analysis(self, task_id: str, format_type: str, module_name: Optional[str] = None) -> Dict[str, Any]:
        """Export IC analysis result into requested format."""

        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                raise ValueError(f"Task not found: {task_id}")
            report = task_info.get("result")
            deep_report = task_info.get("deep_analysis_result")

        if not isinstance(report, dict):
            raise ValueError(f"Result not found: {task_id}")

        normalized_format = (format_type or "").strip().lower()
        if normalized_format not in {"json", "ai_json", "csv_summary", "csv_detailed", "markdown", "hdf5"}:
            raise TypeError(f"Unsupported format: {format_type}")

        if normalized_format == "hdf5":
            metadata = report.get("metadata", {}) if isinstance(report, dict) else {}
            export_path = self._resolve_filtered_path(metadata)
            if not export_path.exists():
                raise FileNotFoundError("Filtered features not found")
            return {
                "type": "file",
                "path": export_path,
                "filename": export_path.name,
                "media_type": "application/x-hdf5",
            }

        reporter = ICReporter(config={})
        payload_for_export = dict(report)
        if isinstance(deep_report, dict):
            payload_for_export.setdefault("deep_analysis_report", deep_report)

        if normalized_format == "json":
            content = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "type": "bytes",
                "content": BytesIO(content),
                "filename": f"ic_report_{task_id}.json",
                "media_type": "application/json; charset=utf-8",
            }

        if normalized_format == "ai_json":
            payload = reporter.generate_ai_json(payload_for_export, deep_report=deep_report)
            content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "type": "bytes",
                "content": BytesIO(content),
                "filename": f"ic_ai_{task_id}.json",
                "media_type": "application/json; charset=utf-8",
            }

        if normalized_format == "csv_summary":
            csv_text = reporter.generate_summary_csv(payload_for_export, deep_report=deep_report)
            return {
                "type": "bytes",
                "content": BytesIO(csv_text.encode("utf-8")),
                "filename": f"ic_summary_{task_id}.csv",
                "media_type": "text/csv; charset=utf-8",
            }

        if normalized_format == "csv_detailed":
            if not module_name:
                raise ValueError("module query parameter is required for csv_detailed")
            csv_text = reporter.generate_detailed_csv(payload_for_export, module_name)
            return {
                "type": "bytes",
                "content": BytesIO(csv_text.encode("utf-8")),
                "filename": f"ic_{module_name}_{task_id}.csv",
                "media_type": "text/csv; charset=utf-8",
            }

        markdown = reporter.generate_enhanced_markdown(payload_for_export, deep_report=deep_report)
        return {
            "type": "bytes",
            "content": BytesIO(markdown.encode("utf-8")),
            "filename": f"ic_report_{task_id}.md",
            "media_type": "text/markdown; charset=utf-8",
        }

    def list_features(self, features_path: str, meta_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read available feature list from HDF5 (+ optional metadata JSON)."""
        path = Path(features_path)
        if not path.exists():
            raise FileNotFoundError(f"features_path not found: {features_path}")

        metadata = self._load_meta(meta_path)

        with h5py.File(path, "r") as h5_file:
            if "data" not in h5_file:
                raise ValueError("Invalid features HDF5: missing 'data' group")
            group = h5_file["data"]

            if "feature_names" in group:
                raw_names = group["feature_names"][:]
                names = [
                    item.decode("utf-8") if isinstance(item, bytes) else str(item)
                    for item in raw_names
                ]
            elif "features" in group and len(group["features"].shape) == 2:
                names = [f"feature_{i}" for i in range(group["features"].shape[1])]
            else:
                raise ValueError("Invalid features HDF5: missing feature_names/features")

        feature_items: List[Dict[str, Any]] = []
        for name in names:
            meta_item = metadata.get(name, {}) if isinstance(metadata.get(name, {}), dict) else {}
            feature_items.append({
                "feature_name": name,
                "category": meta_item.get("category"),
                "data_source": meta_item.get("data_source") or meta_item.get("source"),
                "family": meta_item.get("family"),
                "layer": meta_item.get("layer"),
            })

        return feature_items

    async def start_deep_analysis(self, task_id: str, request: DeepAnalysisRequest) -> Dict[str, str]:
        """Start deep analysis as a background task for an existing IC task."""
        analyzer = self.get_analyzer(task_id)
        if analyzer is None:
            raise ValueError(f"Task not found: {task_id}")

        status = self.get_task_status(task_id)
        if not status:
            raise ValueError(f"Task not found: {task_id}")
        if status.get("status") != "completed":
            raise ValueError(f"Task {task_id} is not ready for deep analysis")

        with self._lock:
            task_info = self._tasks.get(task_id)
            if task_info:
                task_info["status"] = "running"
                task_info["current_stage"] = "deep_analysis"
                task_info["current_step"] = None
                task_info["progress"] = 0.0
                task_info["error"] = None

        logger.info("Deep analysis started for task: %s", task_id)
        self._start_background_coroutine(
            lambda: self._run_deep_analysis(task_id, analyzer, request)
        )
        return {"task_id": task_id, "status": "running"}

    async def _run_deep_analysis(self, task_id: str, analyzer: Any, request: DeepAnalysisRequest) -> None:
        override = self._build_deep_module_override(request)

        def progress_callback(payload: Dict[str, Any]) -> None:
            progress = max(0.0, min(1.0, float(payload.get("progress", 0.0))))
            current_step = payload.get("module_name") or payload.get("current_step")
            message = payload.get("message")

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["status"] = "running"
                task_info["current_stage"] = "deep_analysis"
                task_info["current_step"] = current_step
                task_info["progress"] = progress

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            })

        try:
            selected_features = self._resolve_selected_features(
                analyzer=analyzer,
                selected_features=request.selected_features,
                top_n=request.top_n,
            )

            deep_report = await asyncio.to_thread(
                analyzer.run_deep_analysis,
                selected_features,
                override,
                progress_callback,
                None,
            )
            serialized = self._serialize_deep_report(deep_report)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["current_stage"] = "deep_analysis"
                    task_info["current_step"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["deep_analysis_result"] = serialized

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": "completed",
                "progress": 1.0,
                "message": "deep analysis completed",
                "status": "completed",
            })
        except Exception as exc:
            logger.error("Deep analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["current_stage"] = "deep_analysis"
                    task_info["current_step"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_deep_analysis_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get deep analysis result."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            deep_result = task_info.get("deep_analysis_result")

        if deep_result is None:
            return None

        normalized = self._to_json_compatible(deep_result)
        if isinstance(normalized, dict):
            return normalized
        return {"raw": normalized}

    async def start_full_analysis(self, request: ICFullAnalysisRequest) -> Dict[str, str]:
        """Start full analysis task (main + optional deep analysis)."""
        task_id = str(uuid.uuid4())
        config_override = self._build_config_override(request)
        analyzer = create_ic_analyzer(config_override)

        task_info = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "current_step": None,
            "error": None,
            "result": None,
            "deep_analysis_result": None,
            "analyzer": analyzer,
            "applied_tier": (request.feature_tiers.active_preset if request.feature_tiers else "intermediate"),
            "created_at": datetime.now().isoformat(),
        }

        with self._lock:
            self._tasks[task_id] = task_info
            self._last_task_id = task_id

        logger.info("IC full analysis task started: %s", task_id)
        self._start_background_coroutine(
            lambda: self._run_full_analysis(task_id, analyzer, request, config_override)
        )
        return {"task_id": task_id, "status": "running"}

    async def _run_full_analysis(
        self,
        task_id: str,
        analyzer: Any,
        request: ICFullAnalysisRequest,
        config_override: Optional[Dict[str, Any]],
    ) -> None:
        def progress_callback(payload: Dict[str, Any]) -> None:
            stage_name = payload.get("stage_name") or payload.get("stage")
            current_step = payload.get("module_name") or payload.get("current_step") or stage_name
            progress = max(0.0, min(1.0, float(payload.get("progress", 0.0))))
            message = payload.get("message")

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["status"] = "running"
                task_info["current_stage"] = stage_name
                task_info["current_step"] = current_step
                task_info["progress"] = progress

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": stage_name,
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            })

        try:
            report = await asyncio.to_thread(
                analyzer.analyze,
                request.features_path,
                request.labels_path,
                request.meta_path,
                config_override,
                progress_callback,
                None,
            )

            deep_result: Optional[Dict[str, Any]] = None
            if request.deep_analysis:
                deep_request = request.deep_analysis_config or DeepAnalysisRequest()
                selected_features = self._resolve_selected_features(
                    analyzer=analyzer,
                    selected_features=deep_request.selected_features,
                    top_n=deep_request.top_n,
                )
                deep_override = self._build_deep_module_override(deep_request)
                deep_report = await asyncio.to_thread(
                    analyzer.run_deep_analysis,
                    selected_features,
                    deep_override,
                    progress_callback,
                    None,
                )
                deep_result = self._serialize_deep_report(deep_report)
                if isinstance(report, dict):
                    report["deep_analysis_enabled"] = True
                    report["deep_analysis_report"] = deep_result

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["current_stage"] = "completed"
                    task_info["current_step"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["result"] = report
                    task_info["deep_analysis_result"] = deep_result

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "completed",
                "current_step": "completed",
                "progress": 1.0,
                "message": "full analysis completed",
                "status": "completed",
            })
        except Exception as exc:
            logger.error("IC full analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["current_stage"] = "failed"
                    task_info["current_step"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "failed",
                "current_step": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_analyzer(self, task_id: Optional[str]) -> Optional[Any]:
        """Get analyzer for task."""
        if not task_id:
            return None
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            return task_info.get("analyzer")

    def get_last_task_id(self) -> Optional[str]:
        """Get last task id."""
        with self._lock:
            return self._last_task_id

    async def refilter(self, task_id: str, thresholds: Dict[str, Any]) -> Dict[str, Any]:
        """Refilter using cached IC results."""
        analyzer = self.get_analyzer(task_id)
        if analyzer is None:
            raise ValueError(f"task not found: {task_id}")

        report = analyzer.refilter(thresholds)
        with self._lock:
            task_info = self._tasks.get(task_id)
            if task_info:
                task_info["result"] = report

        return report

    def register_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Register notification callback."""
        with self._lock:
            self._callbacks.setdefault(task_id, []).append(callback)

    def unregister_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Unregister notification callback."""
        with self._lock:
            callbacks = self._callbacks.get(task_id, [])
            if callback in callbacks:
                callbacks.remove(callback)
            if not callbacks and task_id in self._callbacks:
                del self._callbacks[task_id]

    def _notify_callbacks(self, task_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            callbacks = list(self._callbacks.get(task_id, []))
        for callback in callbacks:
            try:
                callback(payload)
            except Exception as exc:
                logger.error("IC notification callback failed: %s", exc, exc_info=True)

    def _build_config_override(self, request: ICAnalyzeRequest) -> Optional[Dict[str, Any]]:
        override = request.config_override or {}
        if not isinstance(override, dict):
            raise ValueError("config_override must be a dict")

        if request.event_query:
            override = self._deep_merge(override, {
                "event_filter": {
                    "enabled": True,
                    "query": request.event_query,
                }
            })

        if request.event_timestamps:
            logger.warning("event_timestamps provided but not supported in API yet")

        if request.feature_filter:
            override = self._deep_merge(override, {
                "feature_filter": request.feature_filter.model_dump(exclude_none=True)
            })

        if request.deep_analysis_config and request.deep_analysis_config.config_override:
            override = self._deep_merge(override, request.deep_analysis_config.config_override)

        if request.feature_tiers:
            override = self._deep_merge(
                override,
                {"feature_tiers": request.feature_tiers.model_dump(exclude_none=True)},
            )

        if request.deep_analysis_config:
            override = self._deep_merge(
                override,
                self._build_deep_module_override(request.deep_analysis_config),
            )

        return override or None

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _build_deep_module_override(self, request: DeepAnalysisRequest) -> Dict[str, Any]:
        modules = request.modules
        return {
            "factor_return": {"enabled": modules.factor_return},
            "factor_centrality": {"enabled": modules.factor_centrality},
            "trend_analysis": {"enabled": modules.trend_analysis},
            "parameter_sensitivity": {"enabled": modules.parameter_sensitivity},
            "rolling_oos": {"enabled": modules.rolling_oos},
            "factor_orthogonalization": {"enabled": modules.factor_orthogonalization},
            "factor_exposure": {"enabled": modules.factor_exposure},
            "long_short_analysis": {"enabled": modules.long_short_analysis},
            "feature_quality_diagnostics": {"enabled": modules.feature_quality_diagnostics},
            "net_ic_analysis": {"enabled": modules.net_ic_analysis},
            **(request.config_override or {}),
        }

    def _resolve_selected_features(
        self,
        analyzer: Any,
        selected_features: Optional[List[str]],
        top_n: int,
    ) -> Optional[List[str]]:
        if selected_features:
            return selected_features

        top_features = analyzer.get_top_features(n=top_n)
        if not top_features:
            return None

        return [
            item.get("feature_name")
            for item in top_features
            if isinstance(item, dict) and item.get("feature_name")
        ]

    def _serialize_deep_report(self, deep_report: Any) -> Dict[str, Any]:
        if is_dataclass(deep_report):
            raw = asdict(deep_report)
        elif hasattr(deep_report, "model_dump"):
            raw = deep_report.model_dump()
        elif isinstance(deep_report, dict):
            raw = deep_report
        else:
            raw = {"raw": str(deep_report)}

        normalized = self._to_json_compatible(raw)
        if isinstance(normalized, dict):
            return normalized
        return {"raw": normalized}

    def _to_json_compatible(self, value: Any) -> Any:
        """Recursively normalize nested values for FastAPI/Pydantic serialization."""

        if value is None:
            return value

        if isinstance(value, float):
            return value if math.isfinite(value) else None

        if isinstance(value, (str, int, bool)):
            return value

        if isinstance(value, np.generic):
            scalar = value.item()
            if isinstance(scalar, float):
                return scalar if math.isfinite(scalar) else None
            return scalar

        if isinstance(value, np.ndarray):
            return [self._to_json_compatible(item) for item in value.tolist()]

        if is_dataclass(value):
            return self._to_json_compatible(asdict(value))

        if hasattr(value, "model_dump"):
            return self._to_json_compatible(value.model_dump())

        if isinstance(value, dict):
            return {
                str(key): self._to_json_compatible(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [self._to_json_compatible(item) for item in value]

        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass

        return str(value)

    def _load_meta(self, meta_path: Optional[str]) -> Dict[str, Any]:
        if not meta_path:
            return {}

        path = Path(meta_path)
        if not path.exists():
            raise FileNotFoundError(f"meta_path not found: {meta_path}")

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid meta JSON: {meta_path}") from exc

    def _resolve_filtered_path(self, metadata: Dict[str, Any]) -> Path:
        symbol = metadata.get("symbol") if isinstance(metadata, dict) else None
        timeframe = metadata.get("timeframe") if isinstance(metadata, dict) else None
        if symbol and timeframe:
            name = f"{symbol}_{timeframe}_filtered.h5"
        else:
            name = "filtered_features.h5"
        return Path("data_cache/features") / name

    def _start_background_coroutine(self, coroutine_factory: Callable[[], Any]) -> None:
        """Run async workflow in a daemon thread to avoid request-loop cancellation."""

        def runner() -> None:
            try:
                asyncio.run(coroutine_factory())
            except Exception as exc:
                logger.error("Background coroutine crashed: %s", exc, exc_info=True)

        threading.Thread(target=runner, daemon=True).start()


ic_analysis_service = ICAnalysisService()
