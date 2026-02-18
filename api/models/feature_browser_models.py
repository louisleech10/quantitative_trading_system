"""Pydantic models for Feature Browser API (Phase 8 / M9)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HistogramBin(BaseModel):
    left: float
    right: float
    count: int
    density: float


class FeatureDistributionStatistics(BaseModel):
    mean: Optional[float] = None
    std: Optional[float] = None
    skew: Optional[float] = None
    kurtosis: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    median: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    nan_pct: float
    unique_count: int
    zero_count: int
    jb_stat: Optional[float] = None
    jb_pvalue: Optional[float] = None


class FeatureDistributionResponse(BaseModel):
    feature_name: str
    bins: int
    histogram: List[HistogramBin]
    kde_x: List[float]
    kde_y: List[float]
    statistics: FeatureDistributionStatistics


class FeatureOverviewItem(BaseModel):
    feature_name: str
    data_type: str
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    nan_pct: float


class FeatureOverviewResponse(BaseModel):
    total_rows: int
    total_features: int
    numeric_features: int
    mean_nan_pct: float
    items: List[FeatureOverviewItem]


class ICDashboardEntry(BaseModel):
    feature_name: str
    ic_mean: float
    ic_std: float
    ir: float
    t_stat: float
    significance: str
    sparkline: List[float]


class ICDashboardResponse(BaseModel):
    available: bool
    message: Optional[str] = None
    entries: List[ICDashboardEntry] = Field(default_factory=list)


class RollingICPoint(BaseModel):
    timestamp: str
    ic: float
    ir: Optional[float] = None


class RollingICResponse(BaseModel):
    feature_name: str
    window: int
    points: List[RollingICPoint]


class FeatureQualityScore(BaseModel):
    feature_name: str
    stationarity_score: float
    coverage_score: float
    drift_score: float
    redundancy_score: float
    total_score: float
    grade: str


class QualityScorecardResponse(BaseModel):
    items: List[FeatureQualityScore]
    funnel: Dict[str, int]


class CorrelationMatrixResponse(BaseModel):
    method: str
    features: List[str]
    matrix: List[List[float]]
    truncated: bool = False
    original_feature_count: int = 0


class VIFEntry(BaseModel):
    feature_name: str
    vif: float
    status: str


class VIFResponse(BaseModel):
    items: List[VIFEntry]


class DriftMonitorEntry(BaseModel):
    feature_name: str
    psi: float
    ks_stat: float
    ks_pvalue: float
    status: str


class DriftMonitorResponse(BaseModel):
    items: List[DriftMonitorEntry]


class SHAPSummaryEntry(BaseModel):
    feature_name: str
    mean_abs_shap: float
    mean_shap: float


class SHAPSummaryResponse(BaseModel):
    available: bool
    message: Optional[str] = None
    items: List[SHAPSummaryEntry] = Field(default_factory=list)


class ImportanceComparisonEntry(BaseModel):
    feature_name: str
    lightgbm_importance: float
    xgboost_importance: float


class ImportanceComparisonResponse(BaseModel):
    items: List[ImportanceComparisonEntry]


class FeatureQualityCheckRequest(BaseModel):
    features_path: str
    selected_features: Optional[List[str]] = None


class FeatureQualityCheckResponse(BaseModel):
    results: List[Dict[str, Any]]


class FeatureDataTableResponse(BaseModel):
    total_rows: int
    page: int
    page_size: int
    columns: List[str]
    rows: List[Dict[str, Any]]
