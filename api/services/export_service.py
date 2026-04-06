"""Export service for Phase 7 (M8)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from api.core.logging import get_logger
from api.models.export_models import ExportFormatEnum, ExportScopeEnum
from momentum.factories import create_analysis_exporter


class ExportService:
    """Generate downloadable export content for model task outputs."""

    def __init__(
        self,
        exporter_factory: Callable = create_analysis_exporter,
        task_payload_provider: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
    ):
        self.logger = get_logger(__name__)
        self.exporter = exporter_factory()
        self.task_payload_provider = task_payload_provider or self._default_task_payload_provider

    def export_file(
        self,
        model_task_id: str,
        format: ExportFormatEnum,
        scope: ExportScopeEnum,
    ) -> Tuple[bytes, str, str]:
        payload = self._load_payload(model_task_id)
        if not payload or not self._has_exportable_content(payload):
            raise ValueError(f"任務不存在或無可匯出資料: {model_task_id}")

        rendered = self.exporter.export_by_scope(
            data=payload,
            scope=scope.value,
            format=format,
            model_id=model_task_id,
        )

        if format == ExportFormatEnum.json:
            import json

            text = json.dumps(rendered, ensure_ascii=False, indent=2)
            media_type = "application/json"
            extension = "json"
        elif format == ExportFormatEnum.csv:
            text = rendered if isinstance(rendered, str) else ""
            media_type = "text/csv"
            extension = "csv"
        else:
            text = rendered if isinstance(rendered, str) else ""
            media_type = "text/markdown"
            extension = "md"

        file_name = f"{model_task_id}_{scope.value}.{extension}"
        return text.encode("utf-8"), file_name, media_type

    def preview(
        self,
        model_task_id: str,
        format: ExportFormatEnum,
        scope: ExportScopeEnum,
    ) -> Tuple[str, str]:
        content_bytes, file_name, _ = self.export_file(
            model_task_id=model_task_id,
            format=format,
            scope=scope,
        )
        content = content_bytes.decode("utf-8")
        return content, file_name

    def _load_payload(self, model_task_id: str) -> Dict[str, Any]:
        payload = self.task_payload_provider(model_task_id)
        if not isinstance(payload, dict):
            return {}

        result = payload.get("result")
        merged: Dict[str, Any] = {
            "engine": payload.get("engine"),
            "performance": payload.get("performance"),
            "feature_importance": payload.get("feature_importance"),
            "comparison": payload.get("comparison"),
            "optimization": {
                "best_value": payload.get("best_value"),
                "best_params": payload.get("best_params"),
                "trials_summary": payload.get("trials_summary"),
            },
            "enhancement": payload.get("enhancement"),
        }

        if isinstance(result, dict):
            merged["engine"] = merged.get("engine") or result.get("engine")
            merged["performance"] = merged.get("performance") or result.get("performance")
            merged["feature_importance"] = merged.get("feature_importance") or result.get("feature_importance")
            merged["comparison"] = merged.get("comparison") or result.get("comparison")
            merged["optimization"] = {
                "best_value": result.get("best_value") or merged["optimization"].get("best_value"),
                "best_params": result.get("best_params") or merged["optimization"].get("best_params"),
                "trials_summary": result.get("trials_summary") or merged["optimization"].get("trials_summary"),
            }
            if isinstance(result.get("enhancement"), dict):
                merged["enhancement"] = result.get("enhancement")

        return merged

    @staticmethod
    def _has_exportable_content(payload: Dict[str, Any]) -> bool:
        candidates = [
            payload.get("performance"),
            payload.get("feature_importance"),
            payload.get("comparison"),
            payload.get("enhancement"),
            payload.get("optimization"),
        ]
        for item in candidates:
            if isinstance(item, dict) and any(value not in (None, [], {}, "") for value in item.values()):
                return True
            if isinstance(item, list) and len(item) > 0:
                return True
            if item not in (None, {}, [], ""):
                return True
        return False

_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Return the ExportService singleton, wired with cross-service provider."""
    global _export_service
    if _export_service is None:
        from api.utils.service_providers import create_task_payload_provider

        _export_service = ExportService(
            task_payload_provider=create_task_payload_provider(),
        )
    return _export_service
