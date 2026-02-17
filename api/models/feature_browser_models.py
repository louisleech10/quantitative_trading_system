"""Pydantic models for Feature Browser API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FeatureCatalogItem(BaseModel):
    name: str
    category: str = "unknown"
    source: str = "features"
    layer: str = "L1"
    family: str = "general"
    params: Dict[str, Any] = Field(default_factory=dict)
    coverage: float
    mean: Optional[float] = None
    std: Optional[float] = None
    nan_pct: float


class FeatureCatalogSummary(BaseModel):
    total_features: int
    total_categories: int
    avg_coverage: float
    stationary_ratio: float
    low_quality_count: int
    redundant_pairs: int


class FeatureCatalogResponse(BaseModel):
    items: List[FeatureCatalogItem]
    summary: FeatureCatalogSummary


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


class FeatureTimeSeriesPoint(BaseModel):
    timestamp: Optional[str] = None
    values: Dict[str, Optional[float]]


class FeatureACFItem(BaseModel):
    lag: int
    value: float


class FeatureFrequencyItem(BaseModel):
    frequency: float
    amplitude: float


class FeatureTimeSeriesResponse(BaseModel):
    features: List[str]
    sample_rate: int
    points: List[FeatureTimeSeriesPoint]
    acf: Dict[str, List[FeatureACFItem]]
    periodicity: Dict[str, List[FeatureFrequencyItem]]


class CorrelationMatrixResponse(BaseModel):
    method: str
    features: List[str]
    matrix: List[List[float]]
    mode: str


class FeatureQualityItem(BaseModel):
    feature: str
    adf_pvalue: Optional[float] = None
    is_stationary: bool
    coverage: float
    nan_pct: float


class FeatureQualityCheckRequest(BaseModel):
    features_path: str
    selected_features: Optional[List[str]] = None


class FeatureQualityCheckResponse(BaseModel):
    results: List[FeatureQualityItem]


class FeatureDataTableResponse(BaseModel):
    total_rows: int
    page: int
    page_size: int
    columns: List[str]
    rows: List[Dict[str, Any]]
