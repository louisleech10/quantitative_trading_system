"""Pydantic models for export APIs (Phase 7 M8)."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExportFormatEnum(str, Enum):
    csv = "csv"
    json = "json"
    markdown = "markdown"


class ExportScopeEnum(str, Enum):
    performance = "performance"
    features = "features"
    calibration = "calibration"
    walk_forward = "walk_forward"
    adversarial = "adversarial"
    cpcv = "cpcv"
    learning_curve = "learning_curve"
    optimization = "optimization"
    comparison = "comparison"
    full = "full"


class ExportPreviewResponse(BaseModel):
    model_task_id: str
    format: ExportFormatEnum
    scope: ExportScopeEnum
    file_name: str
    content: str


class ExportQuery(BaseModel):
    format: ExportFormatEnum
    scope: ExportScopeEnum = Field(default=ExportScopeEnum.full)


class ExportErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
