"""
Feature Factory Service - Feature Factory 任務與配置管理
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from api.core.logging import get_logger
from momentum.DataExtraction.parallel_search_engine import FailureType, classify_error
from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
from momentum.FeatureEngineering.mcp.feature_factory_mcp import FeatureFactoryMCP


logger = get_logger("api.feature_factory_service")


class FeatureFactoryService:
    """Feature Factory service for task management and config operations."""

    def __init__(self):
        self._factory = create_feature_factory()
        self._config_manager = self._factory.config_manager
        self._mcp = FeatureFactoryMCP(self._factory, self._config_manager)
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._research_tasks: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()

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
        """Run feature generation task in background."""
        def progress_callback(payload: Dict[str, Any]) -> None:
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

            self._notify_callbacks(task_id, {
                "stage": stage,
                "progress": float(progress),
                "message": message,
            })

        try:
            config_override = getattr(request, "config_override", None)
            force_regenerate = bool(getattr(request, "force_regenerate", False))
            timeframe = getattr(request, "timeframe", "12h")
            symbol = getattr(request, "symbol", None)

            if not symbol:
                raise ValueError("symbol is required")

            resolved_override = self._resolve_config_override(config_override)
            result = self._factory.generate_features(
                symbol=symbol,
                timeframe=timeframe,
                config_override=resolved_override,
                force_regenerate=force_regenerate,
                progress_callback=progress_callback,
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


feature_factory_service = FeatureFactoryService()
