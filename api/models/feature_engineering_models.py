"""
Feature Engineering API Models

Pydantic models for Phase 4 feature engineering endpoints

Author: AI Agent
Date: 2026-01-10
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


# Request Models

class FeatureExtractionRequest(BaseModel):
    """特徵提取請求"""
    case_id: str = Field(..., description="案例 ID (格式：symbol_timestamp_index)")
    symbol: str = Field(..., description="交易標的")
    timeframe: str = Field(..., description="時間週期 (1h, 4h, 12h, 1d)")
    strategy_type: str = Field(..., description="策略類型 (目前僅支持 ema_three_line)")
    strategy_params: Dict = Field(..., description="策略參數 (Optuna 優化後的參數)")
    include_basic_features: bool = Field(
        default=True,
        description="是否包含通用價格/成交量特徵"
    )
    validate_input: bool = Field(
        default=True,
        description="是否執行驗證",
        alias="validate"
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "case_id": "ETHUSDT_1735905600_1",
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "strategy_type": "ema_three_line",
                "strategy_params": {
                    "ema_short": 5,
                    "ema_mid": 20,
                    "ema_long": 60,
                    "volume_threshold": 0.6
                },
                "include_basic_features": True,
                "validate": True
            }
        }


# Response Models

class FeatureExtractionStartResponse(BaseModel):
    """特徵提取啟動響應"""
    task_id: str
    status: str
    estimated_time: int = Field(..., description="預估完成時間 (秒)")


class ValidationResult(BaseModel):
    """驗證結果"""
    has_nan: bool
    has_inf: bool
    max_correlation: float
    warnings: List[str]


class FeatureExtractionResult(BaseModel):
    """特徵提取結果"""
    case_id: str
    symbol: str
    timeframe: str
    strategy_type: str
    n_samples: int = Field(..., description="K線樣本數")
    n_features: int = Field(..., description="特徵數量")
    feature_names: List[str]
    storage_path: str
    validation: Optional[ValidationResult] = None


class FeatureTaskStatusResponse(BaseModel):
    """特徵提取任務狀態響應"""
    task_id: str
    status: str = Field(..., description="running | completed | failed")
    progress: int = Field(..., description="進度 (0-100)")
    result: Optional[FeatureExtractionResult] = None
    error: Optional[str] = None


class FeatureStats(BaseModel):
    """特徵統計"""
    mean: float
    std: float
    min: float
    max: float
    percentile_25: float = Field(..., alias='25%')
    percentile_50: float = Field(..., alias='50%')
    percentile_75: float = Field(..., alias='75%')
    
    class Config:
        populate_by_name = True


class CorrelationPair(BaseModel):
    """相關性對"""
    feature1: str
    feature2: str
    correlation: float


class FeatureSummaryResponse(BaseModel):
    """特徵摘要響應"""
    case_id: str
    symbol: str
    timeframe: str
    feature_count: int
    sample_count: int
    feature_names: List[str]
    feature_stats: Dict[str, Dict] = Field(..., description="特徵統計字典")
    high_correlation_pairs: List[CorrelationPair] = Field(
        ...,
        description="高相關性特徵對 (相關性 > 0.7)"
    )
    metadata: Dict
