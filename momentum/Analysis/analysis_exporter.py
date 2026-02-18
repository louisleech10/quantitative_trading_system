"""Multi-format analysis exporter for Phase 7 (M8)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from momentum.core.logging import get_logger


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"


class AnalysisExporter:
    """Export model analysis payload to CSV/JSON/Markdown."""

    SCHEMA_VERSION = "1.0"

    def __init__(self):
        self.logger = get_logger(__name__)

    def export_model_performance(
        self,
        data: Dict[str, Any],
        format: ExportFormat | str,
        model_id: str,
    ) -> str | Dict[str, Any]:
        records = self._to_records(data.get("performance"))
        payload = {
            "scope": "performance",
            "records": records,
            "engine": data.get("engine", "unknown"),
        }
        return self._render(payload=payload, format=format, model_id=model_id)

    def export_feature_importance(
        self,
        data: Dict[str, Any],
        format: ExportFormat | str,
        model_id: str,
    ) -> str | Dict[str, Any]:
        feature_data = data.get("feature_importance")
        records = self._to_records(feature_data)
        payload = {
            "scope": "features",
            "records": records,
            "engine": data.get("engine", "unknown"),
        }
        return self._render(payload=payload, format=format, model_id=model_id)

    def export_enhancement_results(
        self,
        data: Dict[str, Any],
        format: ExportFormat | str,
        model_id: str,
    ) -> str | Dict[str, Any]:
        enhancement = data.get("enhancement")
        records = self._to_records(enhancement)
        payload = {
            "scope": "enhancement",
            "records": records,
            "engine": data.get("engine", "unknown"),
        }
        return self._render(payload=payload, format=format, model_id=model_id)

    def export_full_research_report(
        self,
        data: Dict[str, Any],
        format: ExportFormat | str,
        model_id: str,
    ) -> str | Dict[str, Any]:
        payload = {
            "scope": "full",
            "engine": data.get("engine", "unknown"),
            "performance": self._to_records(data.get("performance")),
            "feature_importance": self._to_records(data.get("feature_importance")),
            "enhancement": self._to_records(data.get("enhancement")),
            "comparison": self._to_records(data.get("comparison")),
            "optimization": self._to_records(data.get("optimization")),
        }
        return self._render(payload=payload, format=format, model_id=model_id)

    def export_by_scope(
        self,
        data: Dict[str, Any],
        scope: str,
        format: ExportFormat | str,
        model_id: str,
    ) -> str | Dict[str, Any]:
        normalized_format = self._normalize_format(format)
        if scope == "performance":
            return self.export_model_performance(data, normalized_format, model_id)
        if scope == "features":
            return self.export_feature_importance(data, normalized_format, model_id)
        if scope in {
            "calibration",
            "walk_forward",
            "adversarial",
            "cpcv",
            "learning_curve",
            "optimization",
            "comparison",
        }:
            return self._export_single_scope(data, scope, normalized_format, model_id)
        if scope == "full":
            return self.export_full_research_report(data, normalized_format, model_id)
        return self.export_enhancement_results(data, normalized_format, model_id)

    def _export_single_scope(
        self,
        data: Dict[str, Any],
        scope: str,
        format: ExportFormat | str,
        model_id: str,
    ) -> str | Dict[str, Any]:
        if scope == "comparison":
            source = data.get("comparison")
        elif scope == "optimization":
            source = data.get("optimization")
        else:
            enhancement = data.get("enhancement")
            source = enhancement.get(scope) if isinstance(enhancement, dict) else None

        payload = {
            "scope": scope,
            "engine": data.get("engine", "unknown"),
            "records": self._to_records(source),
        }
        return self._render(payload=payload, format=format, model_id=model_id)

    def _render(
        self,
        payload: Dict[str, Any],
        format: ExportFormat | str,
        model_id: str,
    ) -> str | Dict[str, Any]:
        normalized_format = self._normalize_format(format)
        envelope = self._create_json_envelope(payload, model_id)
        if normalized_format == ExportFormat.JSON:
            return envelope
        if normalized_format == ExportFormat.CSV:
            return self._to_csv(envelope)
        return self._to_markdown(envelope)

    @staticmethod
    def _normalize_format(format: ExportFormat | str) -> ExportFormat:
        if isinstance(format, ExportFormat):
            return format
        return ExportFormat(str(format).lower())

    def _create_json_envelope(self, data: Dict[str, Any], model_id: str) -> Dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "model_id": model_id,
            "engine": data.get("engine", "unknown"),
            "data_source": data.get("data_source", {}),
            **self._sanitize(data),
        }

    def _to_csv(self, envelope: Dict[str, Any]) -> str:
        flat_rows = self._flatten_for_csv(envelope)
        if not flat_rows:
            return "key,value\n"
        headers = sorted({key for row in flat_rows for key in row.keys()})
        lines = [",".join(headers)]
        for row in flat_rows:
            values = [self._csv_escape(row.get(header)) for header in headers]
            lines.append(",".join(values))
        return "\n".join(lines) + "\n"

    def _to_markdown(self, envelope: Dict[str, Any]) -> str:
        lines: List[str] = [
            f"# Export Report ({envelope.get('scope', 'unknown')})",
            "",
            f"- model_id: {envelope.get('model_id', '')}",
            f"- engine: {envelope.get('engine', '')}",
            f"- export_timestamp: {envelope.get('export_timestamp', '')}",
            "",
        ]

        scope = envelope.get("scope")
        if scope == "full":
            for section in ["performance", "feature_importance", "enhancement", "comparison", "optimization"]:
                lines.extend(self._markdown_section(section, envelope.get(section)))
        else:
            lines.extend(self._markdown_section("records", envelope.get("records")))

        return "\n".join(lines).strip() + "\n"

    def _markdown_section(self, title: str, value: Any) -> List[str]:
        lines = [f"## {title}"]
        records = self._to_records(value)
        if not records:
            lines.append("- N/A")
            lines.append("")
            return lines

        for record in records[:50]:
            if isinstance(record, dict):
                text = ", ".join(f"{key}={record[key]}" for key in sorted(record.keys()))
            else:
                text = str(record)
            lines.append(f"- {text}")
        lines.append("")
        return lines

    def _flatten_for_csv(self, value: Any) -> List[Dict[str, Any]]:
        records = self._to_records(value)
        normalized: List[Dict[str, Any]] = []
        for item in records:
            if isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({"value": item})
        return normalized

    def _to_records(self, data: Any) -> List[Any]:
        if data is None:
            return []
        if isinstance(data, list):
            return [self._sanitize(item) for item in data]
        if isinstance(data, dict):
            return [self._sanitize(data)]
        return [self._sanitize(data)]

    def _sanitize(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, float):
            if np.isnan(value) or np.isinf(value):
                return None
            return value
        if isinstance(value, np.generic):
            return self._sanitize(value.item())
        if isinstance(value, np.ndarray):
            return [self._sanitize(item) for item in value.tolist()]
        if isinstance(value, dict):
            return {str(key): self._sanitize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize(item) for item in value]
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return self._sanitize(value.model_dump())
        if hasattr(value, "__dict__"):
            return self._sanitize({k: v for k, v in vars(value).items() if not k.startswith("_")})
        return str(value)

    @staticmethod
    def _csv_escape(value: Any) -> str:
        text = "" if value is None else str(value)
        if any(ch in text for ch in [",", "\n", '"']):
            return '"' + text.replace('"', '""') + '"'
        return text
