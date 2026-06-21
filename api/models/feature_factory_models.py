"""Feature Factory API Models.

Pydantic models for Feature Factory endpoints.
"""

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from api.core.logging import get_logger
from momentum.FeatureEngineering.feature_config import SUPPORTED_TIMEFRAMES


logger = get_logger("api.models.feature_factory")


class FailOpenGateFlags(BaseModel):
    """Fail-open consumer/producer gate flags（對應 FactoryConfig §C-1）。"""

    allow_partial_layers: bool = False
    allow_partial_timeframes: bool = False
    allow_partial_ic: bool = False
    allow_partial_training: bool = False
    max_inf_ratio: float = 0.0
    max_nan_ratio: Optional[float] = None


class FeatureGenerateRequest(BaseModel):
    """Feature Factory generate request."""

    symbol: str = Field(..., description="交易標的")
    timeframe: str = Field("12h", description="時間週期")
    config_override: Optional[Dict] = Field(default=None, description="配置覆寫")
    fail_open: Optional[FailOpenGateFlags] = Field(
        default=None,
        description="可選 fail-open gate 旗標（亦可在 config_override 內傳）",
    )
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
    result: Optional[Dict] = None
    retention_prompt: Optional[bool] = None
    run_identity: Optional[Dict[str, str]] = None
    process_rss_mb: Optional[int] = Field(
        default=None,
        description=(
            "單 symbol 路徑：API 行程整體 RSS（MB），含 API/browse 等同進程噪音；"
            "純觀測值，非該 symbol 獨佔記憶體。"
        ),
    )
    worker_rss_mb: Optional[int] = None
    current_rss_mb: Optional[int] = Field(
        default=None,
        description="Legacy RSS 欄（與 process_rss_mb 或 worker_rss_mb 雙寫同值）。",
    )
    schema_version: int = 1


class RunInfo(BaseModel):
    symbol: str
    timeframe: str
    config_hash: str
    alias: Optional[str] = None
    batch_id: Optional[str] = None
    batch_alias: Optional[str] = None
    created_at: Optional[str] = None
    last_generated_at: Optional[str] = None
    size_bytes: Optional[int] = None
    active: bool
    browse_task_id: str
    browse_ready: bool
    browse_path: Optional[str] = None
    feature_count: Optional[int] = None
    row_count: Optional[int] = None
    quality_status: Optional[str] = None


class EnsureBrowseResponse(BaseModel):
    """Registry run 對應的 browse 虛擬任務確保結果。"""

    browse_task_id: str
    browse_ready: bool
    symbol: str
    timeframe: str
    config_hash: str


class AliasRequest(BaseModel):
    alias: Optional[str] = None


class BatchAliasRequest(BaseModel):
    batch_alias: Optional[str] = None


class BatchAliasResponse(BaseModel):
    affected: int


class DeleteRunResponse(BaseModel):
    symbol: str
    timeframe: str
    config_hash: str
    features_deleted: bool
    cgsa_deleted: bool
    registry_removed: bool
    skipped: list[str]
    errors: list[str]
    total_bytes: int


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
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    config_override: Optional[Dict[str, Any]] = None
    force_regenerate: bool = False
    max_workers: int = Field(default=4, ge=1, le=8)

    @field_validator("symbols")
    @classmethod
    def deduplicate_symbols(cls, value: List[str]) -> List[str]:
        """自動去重且保留順序。"""
        duplicated = []
        seen = set()
        for symbol in value:
            if symbol in seen and symbol not in duplicated:
                duplicated.append(symbol)
            seen.add(symbol)
        if duplicated:
            logger.warning("Feature Factory batch duplicate symbols ignored: %s", duplicated)
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
    current_symbol: Optional[str] = None
    current_timeframe: Optional[str] = None
    current_stage: Optional[str] = None
    stage_progress: Optional[float] = None
    process_rss_mb: Optional[int] = Field(
        default=None,
        description=(
            "單 symbol 路徑：API 行程整體 RSS（MB），含 API/browse 等同進程噪音；"
            "純觀測值，非該 symbol 獨佔記憶體。"
        ),
    )
    worker_rss_mb: Optional[int] = Field(
        default=None,
        description="批次路徑：子進程 worker RSS（MB）。",
    )
    current_rss_mb: Optional[int] = Field(
        default=None,
        description="Legacy RSS 欄（與 process_rss_mb 或 worker_rss_mb 雙寫同值）。",
    )
    schema_version: int = 1
    queued: Optional[int] = None
    concurrent_symbols: Optional[int] = None
    memory_sanity_failed: Optional[bool] = None
    last_item_metrics: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, str]] = None
    browse_task_ids: Optional[Dict[str, str]] = None
    errors: Optional[Dict[str, str]] = None
    retention_pending: Optional[List["BatchRetentionItem"]] = None


class BatchRetentionItem(BaseModel):
    """單一 batch run 的 retention 狀態（post-hoc mark）。"""

    symbol: str
    timeframe: str
    config_hash: str
    state: str
    hdf5_path: Optional[str] = None
    error: Optional[str] = None


class BatchRetentionDecisionRequest(BaseModel):
    """批次 retention retain/discard 決策請求。"""

    decision: Literal["retain", "discard"]


class BatchRetentionDecisionResponse(BaseModel):
    """批次 retention 決策結果。"""

    batch_id: str
    symbol: str
    timeframe: str
    config_hash: str
    state: str
    hdf5_path: Optional[str] = None
    error: Optional[str] = None


class BatchRetentionPendingResponse(BaseModel):
    """批次待決 retention 列表。"""

    batch_id: str
    pending: List[BatchRetentionItem]


class BatchResumeResponse(BaseModel):
    """批次 resume 回應。"""

    batch_id: str
    resumed_from: str
    skipped_items: int
    queued_items: int
    status: str


class NanQuantiles(BaseModel):
    """各特徵真實缺值率（np.isnan）的 5 數摘要。"""

    min: float = 0.0
    q1: float = 0.0
    median: float = 0.0
    q3: float = 0.0
    max: float = 0.0


class SymbolQualitySummary(BaseModel):
    """單一標的特徵品質摘要（批次彙整用）。"""

    symbol: str
    bar_count: int
    feature_count: int
    nan_ratio_mean: float
    nan_ratio_max: float
    nan_quantiles: NanQuantiles = NanQuantiles()  # 5 數摘要;未宣告會被 response_model 濾掉→前端顯示 0
    constant_feature_count: int
    alert_count: int
    warmup_only_count: int = 0
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
