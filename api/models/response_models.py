from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class EnhancedCaseData(BaseModel):
    """擴充的案例數據模型 - 支援完整的20個參數"""
    
    # 基本識別資訊
    symbol: str
    timestamp: str
    trigger_idx: int
    timeframe: str
    
    # OHLCV 基礎數據
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # ===== 基礎觸發條件參數 (6個) =====
    price_change: float
    closing_strength: Optional[float] = None
    price_position: Optional[float] = None
    volume_multiplier: Optional[float] = None
    taker_buy_ratio: Optional[float] = None
    
    # ===== 未來表現驗證參數 - 收益率 (12個) =====
    future_1bar_return: Optional[float] = None
    future_2bar_return: Optional[float] = None
    future_3bar_return: Optional[float] = None
    future_4bar_return: Optional[float] = None
    future_5bar_return: Optional[float] = None
    future_6bar_return: Optional[float] = None
    future_7bar_return: Optional[float] = None
    future_8bar_return: Optional[float] = None
    future_9bar_return: Optional[float] = None
    future_10bar_return: Optional[float] = None
    future_11bar_return: Optional[float] = None
    future_12bar_return: Optional[float] = None
    
    # ===== 未來表現驗證參數 - 最大回撤 (12個) =====
    future_1bar_max_drawdown: Optional[float] = None
    future_2bar_max_drawdown: Optional[float] = None
    future_3bar_max_drawdown: Optional[float] = None
    future_4bar_max_drawdown: Optional[float] = None
    future_5bar_max_drawdown: Optional[float] = None
    future_6bar_max_drawdown: Optional[float] = None
    future_7bar_max_drawdown: Optional[float] = None
    future_8bar_max_drawdown: Optional[float] = None
    future_9bar_max_drawdown: Optional[float] = None
    future_10bar_max_drawdown: Optional[float] = None
    future_11bar_max_drawdown: Optional[float] = None
    future_12bar_max_drawdown: Optional[float] = None
    
    # ===== 時間相關描述參數 =====
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    market_phase: Optional[str] = None
    
    # ===== 反例專用參數 (2個) =====
    positive_negative_ratio: Optional[str] = None
    time_separation_days: Optional[int] = None
    case_type: Optional[str] = None  # 'positive' or 'negative'
    label: Optional[int] = None  # 1 for positive, 0 for negative
    
    # ===== 向後兼容的現有參數 =====
    future1_close_return: Optional[float] = None
    future2_close_return: Optional[float] = None
    future4_close_return: Optional[float] = None
    future6_close_return: Optional[float] = None
    future24_close_return: Optional[float] = None
    future48_close_return: Optional[float] = None
    future72_close_return: Optional[float] = None
    future_max_return: Optional[float] = None
    future_max_drawdown: Optional[float] = None
    future72_max_return: Optional[float] = None
    future72_max_drawdown: Optional[float] = None
    future24_close: Optional[float] = None
    future24_low: Optional[float] = None
    prior_volatility: Optional[float] = None
    prior_range: Optional[float] = None
    prior_abs_change_sum: Optional[float] = None
    
    # 時間範圍
    time_range: Optional[Dict[str, str]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class EnhancedSearchRequest(BaseModel):
    """擴充的搜索請求模型"""
    
    config: Dict[str, Any]
    symbols: Optional[List[str]] = None
    save_results: Optional[bool] = True
    export_format: Optional[str] = "csv"
    
    # ===== 新增：基礎觸發條件參數設定 =====
    price_change_min: Optional[float] = None
    price_change_max: Optional[float] = None
    closing_strength_min: Optional[float] = None
    closing_strength_max: Optional[float] = None
    price_position_min: Optional[float] = None
    price_position_max: Optional[float] = None
    volume_multiplier_min: Optional[float] = None
    taker_buy_ratio_min: Optional[float] = None
    taker_buy_ratio_max: Optional[float] = None
    
    # ===== 新增：未來表現要求參數設定 =====
    future_1bar_return_min: Optional[float] = None
    future_2bar_return_min: Optional[float] = None
    future_3bar_return_min: Optional[float] = None
    future_4bar_return_min: Optional[float] = None
    future_5bar_return_min: Optional[float] = None
    future_6bar_return_min: Optional[float] = None
    future_7bar_return_min: Optional[float] = None
    future_8bar_return_min: Optional[float] = None
    future_9bar_return_min: Optional[float] = None
    future_10bar_return_min: Optional[float] = None
    future_11bar_return_min: Optional[float] = None
    future_12bar_return_min: Optional[float] = None
    
    future_1bar_max_drawdown_max: Optional[float] = None
    future_2bar_max_drawdown_max: Optional[float] = None
    future_3bar_max_drawdown_max: Optional[float] = None
    future_4bar_max_drawdown_max: Optional[float] = None
    future_5bar_max_drawdown_max: Optional[float] = None
    future_6bar_max_drawdown_max: Optional[float] = None
    future_7bar_max_drawdown_max: Optional[float] = None
    future_8bar_max_drawdown_max: Optional[float] = None
    future_9bar_max_drawdown_max: Optional[float] = None
    future_10bar_max_drawdown_max: Optional[float] = None
    future_11bar_max_drawdown_max: Optional[float] = None
    future_12bar_max_drawdown_max: Optional[float] = None
    
    # ===== 新增：反例專用參數設定 =====
    positive_negative_ratio: Optional[str] = "1:2"
    time_separation_days: Optional[int] = 7


class ParameterValidationReport(BaseModel):
    """參數驗證報告模型"""
    
    total_rows: int
    parameters_status: Dict[str, Dict[str, Any]]
    data_quality: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    
    # 新增詳細統計
    basic_trigger_params_count: int = 6
    future_return_params_count: int = 12
    future_drawdown_params_count: int = 12
    descriptive_params_count: int = 3
    total_new_params_count: int = 33  # 6 + 12 + 12 + 3
    
    completion_rate: float
    quality_score: float


class EnhancedSearchResultData(BaseModel):
    """擴充的搜索結果數據模型"""
    
    cases: List[EnhancedCaseData]
    summary: Dict[str, Any]
    sampling_quality: Dict[str, Any]
    execution_time: float
    cache_used: bool
    
    # ===== 新增：參數統計摘要 =====
    parameter_statistics: Optional[Dict[str, Any]] = None
    validation_report: Optional[ParameterValidationReport] = None
    
    # 新增參數的統計摘要
    basic_trigger_stats: Optional[Dict[str, Any]] = None
    future_performance_stats: Optional[Dict[str, Any]] = None
    time_distribution_stats: Optional[Dict[str, Any]] = None


# ===== 數據轉換輔助函數 =====

def convert_case_to_enhanced_model(case_dict: Dict[str, Any]) -> EnhancedCaseData:
    """將字典格式的案例數據轉換為擴充模型"""
    
    # 安全獲取數值的輔助函數
    def safe_float(value, default=None):
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(value, default=None):
        if value is None or pd.isna(value):
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def safe_str(value, default=None):
        if value is None or pd.isna(value):
            return default
        return str(value)
    
    return EnhancedCaseData(
        # 基本識別資訊
        symbol=case_dict.get('symbol', ''),
        timestamp=str(case_dict.get('timestamp', '')),
        trigger_idx=safe_int(case_dict.get('trigger_idx'), 0),
        timeframe=safe_str(case_dict.get('timeframe'), '4h'),
        
        # OHLCV 基礎數據
        open=safe_float(case_dict.get('open'), 0.0),
        high=safe_float(case_dict.get('high'), 0.0),
        low=safe_float(case_dict.get('low'), 0.0),
        close=safe_float(case_dict.get('close'), 0.0),
        volume=safe_float(case_dict.get('volume'), 0.0),
        
        # 基礎觸發條件參數
        price_change=safe_float(case_dict.get('price_change'), 0.0),
        closing_strength=safe_float(case_dict.get('closing_strength')),
        price_position=safe_float(case_dict.get('price_position')),
        volume_multiplier=safe_float(case_dict.get('volume_multiplier')),
        taker_buy_ratio=safe_float(case_dict.get('taker_buy_ratio')),
        
        # 未來收益率參數 (1-12根K線)
        future_1bar_return=safe_float(case_dict.get('future_1bar_return')),
        future_2bar_return=safe_float(case_dict.get('future_2bar_return')),
        future_3bar_return=safe_float(case_dict.get('future_3bar_return')),
        future_4bar_return=safe_float(case_dict.get('future_4bar_return')),
        future_5bar_return=safe_float(case_dict.get('future_5bar_return')),
        future_6bar_return=safe_float(case_dict.get('future_6bar_return')),
        future_7bar_return=safe_float(case_dict.get('future_7bar_return')),
        future_8bar_return=safe_float(case_dict.get('future_8bar_return')),
        future_9bar_return=safe_float(case_dict.get('future_9bar_return')),
        future_10bar_return=safe_float(case_dict.get('future_10bar_return')),
        future_11bar_return=safe_float(case_dict.get('future_11bar_return')),
        future_12bar_return=safe_float(case_dict.get('future_12bar_return')),
        
        # 未來最大回撤參數 (1-12根K線)
        future_1bar_max_drawdown=safe_float(case_dict.get('future_1bar_max_drawdown')),
        future_2bar_max_drawdown=safe_float(case_dict.get('future_2bar_max_drawdown')),
        future_3bar_max_drawdown=safe_float(case_dict.get('future_3bar_max_drawdown')),
        future_4bar_max_drawdown=safe_float(case_dict.get('future_4bar_max_drawdown')),
        future_5bar_max_drawdown=safe_float(case_dict.get('future_5bar_max_drawdown')),
        future_6bar_max_drawdown=safe_float(case_dict.get('future_6bar_max_drawdown')),
        future_7bar_max_drawdown=safe_float(case_dict.get('future_7bar_max_drawdown')),
        future_8bar_max_drawdown=safe_float(case_dict.get('future_8bar_max_drawdown')),
        future_9bar_max_drawdown=safe_float(case_dict.get('future_9bar_max_drawdown')),
        future_10bar_max_drawdown=safe_float(case_dict.get('future_10bar_max_drawdown')),
        future_11bar_max_drawdown=safe_float(case_dict.get('future_11bar_max_drawdown')),
        future_12bar_max_drawdown=safe_float(case_dict.get('future_12bar_max_drawdown')),
        
        # 時間相關描述參數
        hour_of_day=safe_int(case_dict.get('hour_of_day')),
        day_of_week=safe_int(case_dict.get('day_of_week')),
        market_phase=safe_str(case_dict.get('market_phase')),
        
        # 反例專用參數
        positive_negative_ratio=safe_str(case_dict.get('positive_negative_ratio')),
        time_separation_days=safe_int(case_dict.get('time_separation_days')),
        case_type=safe_str(case_dict.get('case_type')),
        label=safe_int(case_dict.get('label')),
        
        # 向後兼容的現有參數
        future1_close_return=safe_float(case_dict.get('future1_close_return')),
        future2_close_return=safe_float(case_dict.get('future2_close_return')),
        future4_close_return=safe_float(case_dict.get('future4_close_return')),
        future6_close_return=safe_float(case_dict.get('future6_close_return')),
        future24_close_return=safe_float(case_dict.get('future24_close_return')),
        future48_close_return=safe_float(case_dict.get('future48_close_return')),
        future72_close_return=safe_float(case_dict.get('future72_close_return')),
        future_max_return=safe_float(case_dict.get('future_max_return')),
        future_max_drawdown=safe_float(case_dict.get('future_max_drawdown')),
        future72_max_return=safe_float(case_dict.get('future72_max_return')),
        future72_max_drawdown=safe_float(case_dict.get('future72_max_drawdown')),
        future24_close=safe_float(case_dict.get('future24_close')),
        future24_low=safe_float(case_dict.get('future24_low')),
        prior_volatility=safe_float(case_dict.get('prior_volatility')),
        prior_range=safe_float(case_dict.get('prior_range')),
        prior_abs_change_sum=safe_float(case_dict.get('prior_abs_change_sum')),
        
        # 時間範圍
        time_range=case_dict.get('time_range', {
            'start': '2023-01-01 00:00:00',
            'end': '2023-01-02 00:00:00'
        })
    )