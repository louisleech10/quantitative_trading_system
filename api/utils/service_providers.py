"""Cross-service composition utilities (Rule 4 zero-tolerance compliance).

Individual services must NOT import each other.  When cross-service interaction
is required, this module provides factory / provider functions that the
singleton getters in each service can use to wire dependencies at construction
time.

Dependency direction:
    api/services/  →  api/utils/  ←  (this module lazily imports api/services/)

All imports from api/services/ happen inside closures (call-time), never at
module import time, so there is zero circular-import risk.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


# ---------------------------------------------------------------------------
# Task payload providers
# ---------------------------------------------------------------------------

def create_task_payload_provider() -> Callable[[str], Optional[Dict[str, Any]]]:
    """Wire task payload lookup from ModelTaskService + ModelEnhancementService.

    Used by ``ExportService`` to resolve task payloads for export.
    """

    def provider(model_task_id: str) -> Optional[Dict[str, Any]]:
        # Source 1: ModelTaskService (pattern analysis tasks)
        try:
            from api.services.model_task_service import ModelTaskService

            svc = ModelTaskService()
            task = svc.get_task_status(model_task_id)
            if isinstance(task, dict):
                return task
        except Exception:
            pass

        # Source 2: ModelEnhancementService (calibration / walk-forward etc.)
        try:
            from api.services.model_enhancement_service import get_model_enhancement_service

            enhancement_task = get_model_enhancement_service().get_task_status(model_task_id)
            if enhancement_task is not None:
                payload = enhancement_task.model_dump()
                return {
                    "engine": "unknown",
                    "enhancement": {enhancement_task.module: enhancement_task.result},
                    "result": payload,
                }
        except Exception:
            pass

        return None

    return provider


def create_model_task_provider() -> Callable[[str], Optional[Dict[str, Any]]]:
    """Wire task payload lookup from ModelTaskService only.

    Used by ``ModelEnhancementService`` to pre-populate task data.
    """

    def provider(model_task_id: str) -> Optional[Dict[str, Any]]:
        try:
            from api.services.model_task_service import ModelTaskService

            svc = ModelTaskService()
            payload = svc.get_task_status(model_task_id)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return None

    return provider


# ---------------------------------------------------------------------------
# Report builder (FeatureExportService)
# ---------------------------------------------------------------------------

def get_report_builder_class() -> type:
    """Return the ``FeatureExportService`` class for report building.

    Used by ``FeatureFactoryService`` to build JSON / Markdown exports.
    """
    from api.services.feature_export_service import FeatureExportService

    return FeatureExportService


# ---------------------------------------------------------------------------
# Optimization output service
# ---------------------------------------------------------------------------

def get_optimization_output_service() -> Any:
    """Return the ``OptimizationOutputService`` singleton.

    Used by ``OptimizationTaskService`` to auto-generate outputs after
    a task completes.
    """
    from api.services.optimization_output_service import (
        get_optimization_output_service as _getter,
    )

    return _getter()
