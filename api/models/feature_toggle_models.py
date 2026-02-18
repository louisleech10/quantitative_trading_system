"""Feature toggle API models for Phase 6."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


DifficultyLiteral = Literal["L1", "L2", "L3"]


class FeatureToggleDTO(BaseModel):
    feature_id: str
    name: str
    description: str
    difficulty: DifficultyLiteral
    is_enabled: bool
    is_locked: bool
    engine_types: List[str]
    dependencies: List[str]
    phase: str
    module: Optional[str] = None
    estimated_time: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class FeatureToggleSummary(BaseModel):
    total: int
    enabled: int
    by_difficulty: Dict[str, Dict[str, int]]
    estimated_total_seconds: int


class FeatureToggleListResponse(BaseModel):
    toggles: List[FeatureToggleDTO]
    summary: FeatureToggleSummary
    presets: List[str]


class FeatureToggleUpdateRequest(BaseModel):
    enabled: bool


class FeatureToggleResponse(BaseModel):
    toggle: FeatureToggleDTO
    cascaded: List[str] = Field(default_factory=list)
    summary: FeatureToggleSummary


class BatchToggleUpdateRequest(BaseModel):
    updates: Dict[str, bool] = Field(default_factory=dict)


class BatchToggleResponse(BaseModel):
    updated: Dict[str, bool]
    cascaded: List[str] = Field(default_factory=list)
    summary: FeatureToggleSummary
