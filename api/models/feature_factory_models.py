"""Feature Factory API Models.

Pydantic models for Feature Factory endpoints.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from momentum.FeatureEngineering.feature_config import SUPPORTED_TIMEFRAMES


class FeatureGenerateRequest(BaseModel):
    """Feature Factory generate request."""

    symbol: str = Field(..., description="交易標的")
    timeframe: str = Field("12h", description="時間週期")
    config_override: Optional[Dict] = Field(default=None, description="配置覆寫")
    start_date: Optional[str] = Field(default=None, description="起始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="結束日期 (YYYY-MM-DD)")
    force_regenerate: bool = Field(default=False, description="是否跳過快取")

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        """驗證時間週期。"""
        if value not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {value}, available: {SUPPORTED_TIMEFRAMES}"
            )
        return value


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


class BatchToggleItem(BaseModel):
    """Single toggle operation."""

    path: str = Field(..., description="點分路徑，例如 atomic_indicators.trend.indicators.EMA.enabled")
    value: bool = Field(..., description="啟用或關閉")


class BatchToggleRequest(BaseModel):
    """Batch toggle request."""

    toggles: List[BatchToggleItem] = Field(..., description="批量切換操作列表")


class BatchGenerateRequest(BaseModel):
    """批次特徵生成請求。"""

    symbols: List[str] = Field(..., min_length=1, max_length=200)
    timeframe: str = Field(default="12h", description="primary TF")
    config_override: Optional[Dict[str, Any]] = None
    force_regenerate: bool = False
    max_workers: int = Field(default=4, ge=1, le=8)


class FeatureGenerationRequest(BaseModel):
    """Feature generation request with optional date range."""

    config: Optional[Dict[str, Any]] = None
    symbols: List[str]
    timeframe: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    force_regenerate: bool = False

    @field_validator("symbols")
    @classmethod
    def deduplicate_symbols(cls, value: List[str]) -> List[str]:
        """自動去重且保留順序。"""
        return list(dict.fromkeys(value))

    @field_validator("symbols")
    @classmethod
    def validate_symbol_format(cls, value: List[str]) -> List[str]:
        """驗證標的名稱格式（英數與底線）。"""
        for symbol in value:
            if not re.match(r"^[A-Za-z0-9_]+$", symbol):
                raise ValueError(f"無效標的名稱: {symbol}")
        return value

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        """驗證主時間週期。"""
        if value not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {value}, available: {SUPPORTED_TIMEFRAMES}"
            )
        return value


class BatchTaskStatusResponse(BaseModel):
    """批次任務狀態。"""

    task_id: str
    status: str
    total: int
    completed: int
    failed: int
    progress: float
    results: Optional[Dict[str, str]] = None
    errors: Optional[Dict[str, str]] = None


class SymbolQualitySummary(BaseModel):
    """單一標的特徵品質摘要（批次彙整用）。"""

    symbol: str
    bar_count: int
    feature_count: int
    nan_ratio_mean: float
    nan_ratio_max: float
    constant_feature_count: int
    alert_count: int
    grade: str  # 'pass' | 'watch' | 'reject'


class BatchQualityResponse(BaseModel):
    """批次品質彙整回應。"""

    batch_task_id: str
    summaries: List[SymbolQualitySummary]
    total_symbols: int
    pass_count: int
    watch_count: int
    reject_count: int
    computed_at: str


class RegisterPathRequest(BaseModel):
    """將批次結果的 HDF5 路徑登錄為可瀏覽的虛擬任務。"""

    symbol: str
    timeframe: str
    hdf5_path: str


class RegisterPathResponse(BaseModel):
    """登錄成功後回傳的 browse task_id。"""

    task_id: str
    symbol: str
    timeframe: str
