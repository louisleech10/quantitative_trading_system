"""
Pattern Analysis Models - 模式分析 Pydantic 模型

Author: AI Agent
Date: 2026-01-10
Updated: 2026-01-13 - 新增批量分析模型，支援指標配置
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal


# ==================== 指標配置模型 ====================

class IndicatorParamsConfig(BaseModel):
    """單個指標參數配置"""
    indicator: str = Field(..., description="指標類型：ema_three_line, rsi, macd")
    data_source: str = Field(default="close", description="數據源：close, open, high, low, volume, taker_ratio")
    params: Dict[str, Any] = Field(..., description="指標參數")
    
    class Config:
        json_schema_extra = {
            "example": {
                "indicator": "ema_three_line",
                "data_source": "close",
                "params": {
                    "ema_short": 5,
                    "ema_mid": 20,
                    "ema_long": 60,
                    "volume_threshold": 0.6
                }
            }
        }


class XGBoostBatchAnalysisRequest(BaseModel):
    """XGBoost 批量分析請求（使用指標配置）"""
    symbol: str = Field(..., description="交易對，如 ETHUSDT")
    timeframe: str = Field(default="12h", description="時間週期：1h, 4h, 12h, 1d")
    indicators: List[IndicatorParamsConfig] = Field(..., description="指標配置列表")
    lookback_bars: int = Field(default=200, description="每個案例回看 K 線數量")
    sequence_length: Optional[int] = Field(
        default=None,
        description="序列特徵長度（TO 前 N 根，None 表示使用單根特徵）"
    )
    sequence_feature_mode: Literal["aggregate", "flatten"] = Field(
        default="aggregate",
        description="序列特徵模式：aggregate=彙總統計，flatten=展平序列"
    )
    sequence_stride: int = Field(default=1, description="序列抽樣步長（預設 1）")
    aggregation_methods: Optional[List[str]] = Field(
        default=None,
        description="序列彙總方法（如 mean, std, min, max, last, slope）"
    )
    multi_scale_windows: Optional[List[int]] = Field(
        default=None,
        description="多時間尺度窗口（如 [8, 16, 32]）"
    )
    time_series_split: bool = Field(
        default=True,
        description="是否使用時間序列切分避免洩漏"
    )
    xgboost_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="XGBoost 參數（可選，使用預設值）"
    )
    cv_folds: int = Field(default=5, description="交叉驗證折數")
    top_n_rules: int = Field(default=10, description="提取前 N 條規則")
    min_support: int = Field(default=10, description="最小支持度")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "ETHUSDT",
                "timeframe": "12h",
                "indicators": [
                    {
                        "indicator": "ema_three_line",
                        "data_source": "close",
                        "params": {"ema_short": 5, "ema_mid": 20, "ema_long": 60}
                    },
                    {
                        "indicator": "rsi",
                        "data_source": "close",
                        "params": {"period": 14, "overbought": 70, "oversold": 30}
                    }
                ],
                "lookback_bars": 200,
                "sequence_length": 64,
                "sequence_feature_mode": "aggregate",
                "sequence_stride": 1,
                "aggregation_methods": ["mean", "std", "min", "max", "last", "slope"],
                "multi_scale_windows": [16, 32],
                "time_series_split": True,
                "xgboost_params": {
                    "max_depth": 5,
                    "learning_rate": 0.05,
                    "n_estimators": 100
                },
                "cv_folds": 5
            }
        }


class XGBoostAnalysisRequest(BaseModel):
    """XGBoost 分析請求（保留向後相容）"""
    case_id: str = Field(..., description="案例 ID")
    xgboost_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="XGBoost 參數（可選）"
    )
    cv_folds: int = Field(default=5, description="交叉驗證折數")
    top_n_rules: int = Field(default=10, description="提取前 N 條規則")
    min_support: int = Field(default=10, description="最小支持度")
    
    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "case_20260110_123456",
                "xgboost_params": {
                    "max_depth": 5,
                    "learning_rate": 0.05,
                    "n_estimators": 100
                },
                "cv_folds": 5,
                "top_n_rules": 10,
                "min_support": 10
            }
        }


class FeatureCondition(BaseModel):
    """特徵條件"""
    feature: str
    operator: str
    threshold: float


class DecisionRuleResponse(BaseModel):
    """決策規則回應"""
    rule_id: int
    condition: str
    support: int
    confidence: float
    lift: float
    feature_conditions: List[FeatureCondition]


class FeatureImportanceResponse(BaseModel):
    """特徵重要性回應"""
    feature: str
    importance: float
    rank: int
    method: str


class ModelPerformanceResponse(BaseModel):
    """模型效能回應"""
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float


class XGBoostAnalysisResult(BaseModel):
    """XGBoost 分析結果"""
    case_id: str
    model_performance: ModelPerformanceResponse
    feature_importance: List[FeatureImportanceResponse]
    decision_rules: List[DecisionRuleResponse]
    model_saved: bool
    model_path: Optional[str] = None


class XGBoostBatchAnalysisResult(BaseModel):
    """XGBoost 批量分析結果"""
    symbol: str
    timeframe: str
    total_cases: int
    positive_cases: int
    negative_cases: int
    features_generated: int
    feature_names: List[str]
    model_performance: ModelPerformanceResponse
    feature_importance: List[FeatureImportanceResponse]
    decision_rules: List[DecisionRuleResponse]
    model_saved: bool
    model_path: Optional[str] = None


class XGBoostAnalysisResponse(BaseModel):
    """XGBoost 分析回應"""
    task_id: str
    message: str
    status: str  # "running", "completed", "failed"


class CaseSummaryResponse(BaseModel):
    """案例摘要回應"""
    total_cases: int
    positive_cases: int
    negative_cases: int
    symbols: List[str]
    timeframes: List[str]


class ModelInfoResponse(BaseModel):
    """模型資訊回應"""
    case_id: str
    feature_count: int
    feature_names: List[str]
    performance: ModelPerformanceResponse
    params: Dict[str, Any]
    saved_at: str
    metadata: Dict[str, Any]


class ModelListItem(BaseModel):
    """模型列表項目"""
    case_id: str
    file_path: str
    file_size: int
    modified_time: str
