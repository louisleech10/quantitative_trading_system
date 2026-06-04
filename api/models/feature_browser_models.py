"""Pydantic models for Feature Browser API.

僅保留跨 Symbol Coverage Matrix 所需模型；其餘骨架期占位端點
（IC / SHAP / 重要度 / quality-scorecard 等）已隨頁面併入 Feature
Factory 而移除。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CoverageMatrixRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1)
    timeframe: str
    feature_names: List[str] = Field(default_factory=list)
    feature_base_path: str = "data_cache/features"
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class CoverageMatrixSummary(BaseModel):
    avg_coverage: float
    worst_symbol: Optional[str] = None
    worst_feature: Optional[str] = None


class CoverageMatrixResponse(BaseModel):
    matrix: Dict[str, Dict[str, Optional[float]]]
    valid_counts: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    row_counts: Dict[str, int] = Field(default_factory=dict)
    symbols: List[str]
    features: List[str]
    summary: CoverageMatrixSummary


class GroupCoverageRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1)
    timeframe: str
    feature_base_path: str = "data_cache/features"
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class GroupCoverageSummary(BaseModel):
    avg_coverage: float
    worst_symbol: Optional[str] = None
    worst_group: Optional[str] = None
    missing_symbols: List[str] = Field(default_factory=list)


class GroupCoverageResponse(BaseModel):
    groups: List[str]
    symbols: List[str]
    matrix: Dict[str, Dict[str, Optional[float]]]
    divergence: Dict[str, float] = Field(default_factory=dict)
    summary: GroupCoverageSummary


class GroupFeatureCoverageRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1)
    timeframe: str
    group_name: str
    feature_base_path: str = "data_cache/features"
    top_n: int = Field(default=100, ge=1, le=500)
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class GroupFeatureCoverageResponse(BaseModel):
    group_name: str
    features: List[str]
    symbols: List[str]
    matrix: Dict[str, Dict[str, Optional[float]]]
    divergence: Dict[str, float] = Field(default_factory=dict)
    row_counts: Dict[str, int] = Field(default_factory=dict)
