"""IC analysis API models."""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ICAnalyzeRequest(BaseModel):
    features_path: str = Field(..., description="Path to features HDF5")
    labels_path: Optional[str] = Field(None, description="Path to labels HDF5")
    meta_path: Optional[str] = Field(None, description="Path to metadata JSON")
    config_override: Optional[Dict[str, Any]] = Field(None, description="Config override")
    event_query: Optional[str] = Field(None, description="Event filter query")
    event_timestamps: Optional[List[int]] = Field(
        None,
        description="Event timestamps for filtering",
    )


class ICAnalyzeResponse(BaseModel):
    task_id: str
    status: str


class ICTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    current_stage: Optional[str] = None
    error: Optional[str] = None


class ICTopFeaturesRequest(BaseModel):
    n: int = 30
    horizon: int = 5
    sort_by: str = "icir"


class ICRefilterRequest(BaseModel):
    thresholds: Dict[str, Any]
