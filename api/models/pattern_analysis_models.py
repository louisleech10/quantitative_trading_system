"""
Pattern Analysis Models - 模式分析 Pydantic 模型

Author: AI Agent
Date: 2026-01-10
Updated: 2026-01-13 - 新增批量分析模型，支援指標配置
Updated: 2026-01-28 - 新增 OOT 驗證模型
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal


# ==================== OOT 驗證模型 ====================

class OOTValidationRequest(BaseModel):
    """OOT 驗證請求"""
    task_id: str = Field(..., description="XGBoost 分析任務 ID")
    oot_start_date: Optional[str] = Field(
        default=None,
        description="OOT 開始日期（ISO 格式，如 '2024-07-01'）。為 None 時使用自動切分"
    )
    oot_ratio: Optional[float] = Field(
        default=0.2,
        ge=0.05,
        le=0.5,
        description="OOT 資料比例（0.05-0.5），僅在 oot_start_date 為 None 時使用"
    )
    validation_ratio: Optional[float] = Field(
        default=0.1,
        ge=0.0,
        le=0.3,
        description="驗證集比例（從訓練集末端抽取）"
    )
    timestamp_column: Optional[str] = Field(
        default=None,
        description="時間欄位名稱（None 時自動偵測）"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_20260128_123456",
                "oot_start_date": "2024-07-01",
                "oot_ratio": 0.2,
                "validation_ratio": 0.1
            }
        }


class TimePeriodInfo(BaseModel):
    """時間區間資訊"""
    start: str = Field(..., description="開始時間")
    end: str = Field(..., description="結束時間")
    samples: int = Field(..., description="樣本數")
    positive_count: int = Field(default=0, description="正樣本數")
    positive_rate: float = Field(default=0.0, description="正樣本率")


class TimeSplitReport(BaseModel):
    """時間切分報告"""
    split_method: str = Field(..., description="切分方法：manual 或 auto")
    timestamp_column: str = Field(..., description="使用的時間欄位")
    random_seed: Optional[int] = Field(default=None, description="隨機種子")
    train_period: TimePeriodInfo = Field(..., description="訓練期間")
    validation_period: Optional[TimePeriodInfo] = Field(default=None, description="驗證期間")
    oot_period: TimePeriodInfo = Field(..., description="OOT 期間")
    total_samples: int = Field(..., description="總樣本數")


class OOTValidationResult(BaseModel):
    """OOT 驗證結果"""
    oot_auc: float = Field(..., description="OOT AUC")
    oot_precision: float = Field(..., description="OOT Precision")
    oot_recall: float = Field(..., description="OOT Recall")
    oot_f1: float = Field(..., description="OOT F1 Score")
    oot_samples: int = Field(..., description="OOT 樣本數")
    oot_positive_count: int = Field(..., description="OOT 正樣本數")
    oot_positive_rate: float = Field(..., description="OOT 正樣本率")
    cv_auc_mean: float = Field(..., description="CV AUC 平均值")
    cv_oot_gap: float = Field(..., description="CV-OOT Gap（CV AUC - OOT AUC）")
    gap_status: str = Field(
        ..., 
        description="Gap 狀態：good (< 0.05), acceptable (< 0.08), warning (>= 0.08)"
    )
    is_generalization_good: bool = Field(..., description="模型是否有良好泛化能力")
    oot_period_start: str = Field(..., description="OOT 期間開始")
    oot_period_end: str = Field(..., description="OOT 期間結束")


class OOTValidationResponse(BaseModel):
    """OOT 驗證回應"""
    task_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="狀態：success, failed")
    message: str = Field(..., description="狀態訊息")
    validation_result: Optional[OOTValidationResult] = Field(
        default=None, 
        description="OOT 驗證結果"
    )
    time_split_report: Optional[TimeSplitReport] = Field(
        default=None,
        description="時間切分報告"
    )
    error: Optional[str] = Field(default=None, description="錯誤訊息")


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
    symbols: List[str] = Field(..., description="交易對列表，如 ['ETHUSDT', 'BTCUSDT']")
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
    purge_gap: Optional[int] = Field(
        default=None,
        description="標籤用到未來幾根 K 線（Purged CV 用）"
    )
    embargo_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=0.1,
        description="Embargo 緩衝比例（0-0.1）"
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
                "symbols": ["ETHUSDT", "BTCUSDT"],
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


class CasePrediction(BaseModel):
    """單筆案例預測"""
    case_id: str
    y_true: Optional[int] = Field(default=None, description="真實標籤（可選）")
    predicted_proba: float


class ProbabilitySummary(BaseModel):
    """預測機率摘要"""
    mean: float
    std: float
    bins: Dict[str, int]
    min: float
    max: float


class XGBoostPredictionsResponse(BaseModel):
    """XGBoost 預測回應"""
    task_id: str
    total_cases: int
    summary: ProbabilitySummary
    predictions: Optional[List[CasePrediction]] = None


class FeatureImportanceTypesResponse(BaseModel):
    """多種特徵重要性回應"""
    task_id: str
    types: Dict[str, List[FeatureImportanceResponse]]


class ModelPerformanceResponse(BaseModel):
    """模型效能回應"""
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float
    brier_score: Optional[float] = None
    ece: Optional[float] = None
    calibration_quality: Optional[str] = None
    pr_auc: Optional[float] = None
    positive_rate: Optional[float] = None


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
