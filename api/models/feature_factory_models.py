"""
Feature Factory API Models

Pydantic models for Feature Factory endpoints.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class FeatureGenerateRequest(BaseModel):
    """Feature Factory generate request."""

    symbol: str = Field(..., description="交易標的")
    timeframe: str = Field("12h", description="時間週期")
    config_override: Optional[Dict] = Field(default=None, description="配置覆寫")
    force_regenerate: bool = Field(default=False, description="是否跳過快取")


class FeaturePreviewRequest(BaseModel):
    """Feature Factory preview request."""

    config_override: Optional[Dict] = Field(default=None, description="配置覆寫")


class FeaturePreviewResponse(BaseModel):
    """Feature Factory preview response."""

    total_features: int
    estimated_time_seconds: float
    memory_mb: float
    breakdown: Dict[str, int]


class FeatureTaskStatusResponse(BaseModel):
    """Feature Factory task status response."""

    task_id: str
    status: str
    progress: float
    current_stage: Optional[str] = None
    completed_stages: list[str]
    error: Optional[str] = None


class NL2ConfigRequest(BaseModel):
    """Natural language to config request."""

    text: str


class NL2ConfigResponse(BaseModel):
    """Natural language to config response."""

    config_patch: Dict
    description: str
    preview: FeaturePreviewResponse
