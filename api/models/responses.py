# api/models/responses.py - 安全擴充版本
# 在現有 CaseData 模型基礎上新增20個參數，保持向後兼容

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# 基礎回應模型 (保持不變)
class BaseResponse(BaseModel):
    """基礎回應模型"""
    success: bool = Field(..., description="請求是否成功")
    timestamp: datetime = Field(default_factory=datetime.now, description="回應時間戳")

class ErrorDetail(BaseModel):
    """錯誤詳情模型"""
    code: str = Field(..., description="錯誤代碼")
    message: str = Field(..., description="錯誤訊息")
    details: Dict[str, Any] = Field(default_factory=dict, description="錯誤詳細信息")

class ErrorResponse(BaseResponse):
    """錯誤回應模型"""
    success: bool = Field(False, description="請求失敗")
    error: ErrorDetail = Field(..., description="錯誤信息")

# 任務狀態相關 (保持不變)
class TaskStatusEnum(str, Enum):
    """任務狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskProgress(BaseModel):
    """任務進度模型"""
    current: int = Field(..., description="當前進度", ge=0)
    total: int = Field(..., description="總數", ge=0)
    percentage: float = Field(..., description="完成百分比", ge=0, le=100)
    current_symbol: Optional[str] = Field(None, description="當前處理的交易對")
    estimated_remaining_seconds: Optional[int] = Field(None, description="預計剩餘秒數")

class TaskInfo(BaseModel):
    """任務信息模型"""
    task_id: str = Field(..., description="任務ID")
    status: TaskStatusEnum = Field(..., description="任務狀態")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")
    config_name: str = Field(..., description="配置名稱")
    progress: Optional[TaskProgress] = Field(None, description="任務進度")
    error_message: Optional[str] = Field(None, description="錯誤訊息")

# ===== 擴充的案例數據模型 =====
class CaseData(BaseModel):
    """案例數據模型 - 擴充版本，支援完整的新參數"""
    symbol: str = Field(..., description="交易對")
    timestamp: datetime = Field(..., description="觸發時間")
    trigger_idx: int = Field(..., description="觸發K線索引")
    
    # 完整的 OHLCV 基礎數據 (保持現有欄位)
    open: float = Field(..., description="開盤價")
    high: float = Field(..., description="最高價")
    low: float = Field(..., description="最低價")
    close: float = Field(..., description="收盤價")
    volume: float = Field(..., description="成交量")
    price_change: float = Field(..., description="價格變化百分比")
    market_phase: str = Field(..., description="市場階段")

    # 新增：正反例標記字段
    positive_case: Optional[bool] = Field(None, description="是否為正例（True=正例，False=反例，None=未標記）")
    
    # ===== 新增：基礎觸發條件參數 (5個新增) =====
    timeframe: Optional[str] = Field(None, description="時間框架")
    closing_strength: Optional[float] = Field(None, description="收盤強度")
    price_position: Optional[float] = Field(None, description="價格位置")
    volume_multiplier: Optional[float] = Field(None, description="成交量倍數")
    taker_buy_ratio: Optional[float] = Field(None, description="主動買入比例")
    
    # ===== 新增：未來收益參數 (1-12根K線) =====
    future_1bar_return: Optional[float] = Field(None, description="未來1根K線收益率")
    future_2bar_return: Optional[float] = Field(None, description="未來2根K線收益率")
    future_3bar_return: Optional[float] = Field(None, description="未來3根K線收益率")
    future_4bar_return: Optional[float] = Field(None, description="未來4根K線收益率")
    future_5bar_return: Optional[float] = Field(None, description="未來5根K線收益率")
    future_6bar_return: Optional[float] = Field(None, description="未來6根K線收益率")
    future_7bar_return: Optional[float] = Field(None, description="未來7根K線收益率")
    future_8bar_return: Optional[float] = Field(None, description="未來8根K線收益率")
    future_9bar_return: Optional[float] = Field(None, description="未來9根K線收益率")
    future_10bar_return: Optional[float] = Field(None, description="未來10根K線收益率")
    future_11bar_return: Optional[float] = Field(None, description="未來11根K線收益率")
    future_12bar_return: Optional[float] = Field(None, description="未來12根K線收益率")
    
    # ===== 新增：未來回撤參數 (1-12根K線) =====
    future_1bar_max_drawdown: Optional[float] = Field(None, description="未來1根K線最大回撤")
    future_2bar_max_drawdown: Optional[float] = Field(None, description="未來2根K線最大回撤")
    future_3bar_max_drawdown: Optional[float] = Field(None, description="未來3根K線最大回撤")
    future_4bar_max_drawdown: Optional[float] = Field(None, description="未來4根K線最大回撤")
    future_5bar_max_drawdown: Optional[float] = Field(None, description="未來5根K線最大回撤")
    future_6bar_max_drawdown: Optional[float] = Field(None, description="未來6根K線最大回撤")
    future_7bar_max_drawdown: Optional[float] = Field(None, description="未來7根K線最大回撤")
    future_8bar_max_drawdown: Optional[float] = Field(None, description="未來8根K線最大回撤")
    future_9bar_max_drawdown: Optional[float] = Field(None, description="未來9根K線最大回撤")
    future_10bar_max_drawdown: Optional[float] = Field(None, description="未來10根K線最大回撤")
    future_11bar_max_drawdown: Optional[float] = Field(None, description="未來11根K線最大回撤")
    future_12bar_max_drawdown: Optional[float] = Field(None, description="未來12根K線最大回撤")
    
    # ===== 新增：時間描述參數 =====
    hour_of_day: Optional[int] = Field(None, description="觸發時的小時 (0-23)")
    day_of_week: Optional[int] = Field(None, description="觸發時的星期 (1-7)")

    # ===== 改寫：分類特徵參數 (9個) =====
    # 數值參數（3個）
    past_3day_max_volatility: Optional[float] = Field(None, description="過去3天最大波動度(%)")
    past_3day_direction: Optional[float] = Field(None, description="過去3天方向性(%)")
    past_3day_volume_cv: Optional[float] = Field(None, description="過去3天量能變異係數")

    # 分類參數（6個）
    volatility_class: Optional[str] = Field(None, description="波動度分類 L/M/H/X")
    direction_class: Optional[str] = Field(None, description="方向性分類 D/S/U/V")
    volume_class: Optional[str] = Field(None, description="量能分類 A/B/C")
    market_class: Optional[str] = Field(None, description="市場分類 C1-C12")
    market_class_name: Optional[str] = Field(None, description="市場分類名稱")
    difficulty_level: Optional[str] = Field(None, description="難度等級")

    # ===== 向後兼容的現有參數 (保持不變) =====
    future1_close_return: Optional[float] = Field(None, description="未來1根K線收盤價收益率")
    future2_close_return: Optional[float] = Field(None, description="未來2根K線收盤價收益率")
    future4_close_return: Optional[float] = Field(None, description="未來4根K線收盤價收益率")
    future6_close_return: Optional[float] = Field(None, description="未來6根K線收盤價收益率")
    future24_close_return: Optional[float] = Field(None, description="未來24小時收盤價收益率")
    future48_close_return: Optional[float] = Field(None, description="未來48小時收盤價收益率")
    future72_close_return: Optional[float] = Field(None, description="未來72小時收盤價收益率")
    future_max_return: Optional[float] = Field(None, description="未來最大收益率")
    future_max_drawdown: Optional[float] = Field(None, description="未來最大回撤")
    future72_max_return: Optional[float] = Field(None, description="未來72小時最大收益率")
    future72_max_drawdown: Optional[float] = Field(None, description="未來72小時最大回撤")
    future24_close: Optional[float] = Field(None, description="未來24小時收盤價")
    future24_low: Optional[float] = Field(None, description="未來24小時最低價")
    prior_volatility: Optional[float] = Field(None, description="過去波動率")
    prior_range: Optional[float] = Field(None, description="過去價格範圍")
    prior_abs_change_sum: Optional[float] = Field(None, description="過去絕對變化總和")
    time_range: Optional[Dict[str, str]] = Field(None, description="時間範圍")
    

# ===== 新增：參數統計和驗證報告模型 =====

class ParameterStat(BaseModel):
    """參數統計模型"""
    min: float = Field(..., description="最小值")
    max: float = Field(..., description="最大值")
    avg: float = Field(..., description="平均值")
    count: int = Field(..., description="有效數據數量")
    valid_percentage: float = Field(..., description="有效數據百分比")

class ParameterStatistics(BaseModel):
    """參數統計摘要模型"""
    basic_trigger_params: Dict[str, ParameterStat] = Field(..., description="基礎觸發參數統計")
    future_return_params: Dict[str, ParameterStat] = Field(..., description="未來收益參數統計")
    future_drawdown_params: Dict[str, ParameterStat] = Field(..., description="未來回撤參數統計")
    time_distribution: Dict[str, Dict[str, int]] = Field(..., description="時間分布統計")

class ParameterStatus(BaseModel):
    """參數狀態模型"""
    exists: bool = Field(..., description="參數是否存在")
    nan_count: Optional[int] = Field(None, description="NaN數量")
    nan_percentage: Optional[float] = Field(None, description="NaN百分比")
    data_type: Optional[str] = Field(None, description="數據類型")
    sample_values: Optional[List[Any]] = Field(None, description="樣本值")

class ParameterValidationReport(BaseModel):
    """參數驗證報告模型"""
    total_rows: int = Field(..., description="總行數")
    parameters_status: Dict[str, Dict[str, ParameterStatus]] = Field(..., description="參數狀態")
    data_quality: Dict[str, Any] = Field(..., description="數據質量指標")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    errors: List[str] = Field(default_factory=list, description="錯誤信息")
    basic_trigger_params_count: int = Field(..., description="基礎觸發參數數量")
    future_return_params_count: int = Field(..., description="未來收益參數數量")
    future_drawdown_params_count: int = Field(..., description="未來回撤參數數量")
    descriptive_params_count: int = Field(..., description="描述性參數數量")
    total_new_params_count: int = Field(..., description="新參數總數")
    completion_rate: float = Field(..., description="完成率")
    quality_score: float = Field(..., description="質量評分")

# ===== 保持現有的其他模型不變 =====

class CaseSummary(BaseModel):
    """案例摘要模型"""
    total_cases: int = Field(..., description="總案例數")
    positive_cases: int = Field(..., description="正例數量")
    negative_cases: int = Field(..., description="負例數量")
    unique_symbols: int = Field(..., description="涉及的交易對數量")
    time_range: Dict[str, str] = Field(..., description="時間範圍")
    market_phase_distribution: Dict[str, int] = Field(..., description="市場階段分布")

class SamplingQuality(BaseModel):
    """採樣品質評估模型"""
    time_separation_score: float = Field(..., description="時間分離度評分", ge=0, le=1)
    symbol_diversity_score: float = Field(..., description="標的多樣性評分", ge=0, le=1)
    market_phase_balance: float = Field(..., description="市場階段平衡度", ge=0, le=1)
    overall_quality_score: float = Field(..., description="整體品質評分", ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, description="品質警告")

# ===== 擴充的搜索結果模型 =====
class SearchResultData(BaseModel):
    """搜索結果數據模型 - 擴充版本"""
    cases: List[CaseData] = Field(..., description="案例列表")
    summary: CaseSummary = Field(..., description="案例摘要")
    sampling_quality: SamplingQuality = Field(..., description="採樣品質")
    execution_time: float = Field(..., description="執行時間（秒）")
    cache_used: bool = Field(..., description="是否使用了緩存")

    # ===== 新增：搜索配置信息 =====
    search_config: Optional[Dict[str, Any]] = Field(None, description="搜索配置信息，包含timeframe等參數")
    symbols_processed: Optional[List[str]] = Field(None, description="處理的交易對列表")
    total_cases: Optional[int] = Field(None, description="總案例數")
    positive_cases_count: Optional[int] = Field(None, description="正例數量")
    negative_cases_count: Optional[int] = Field(None, description="反例數量")

    # ===== 新增：參數統計摘要 =====
    parameter_statistics: Optional[ParameterStatistics] = Field(None, description="參數統計摘要")
    validation_report: Optional[ParameterValidationReport] = Field(None, description="參數驗證報告")
    basic_trigger_stats: Optional[Dict[str, Any]] = Field(None, description="基礎觸發參數統計")
    future_performance_stats: Optional[Dict[str, Any]] = Field(None, description="未來表現參數統計")
    time_distribution_stats: Optional[Dict[str, Any]] = Field(None, description="時間分布統計")

# ===== 保持現有的回應模型不變 =====

class SearchResponse(BaseResponse):
    """搜索回應模型"""
    data: SearchResultData = Field(..., description="搜索結果")

class SearchPreviewData(BaseModel):
    """搜索預覽數據模型"""
    estimated_cases: int = Field(..., description="預計案例數量")
    estimated_execution_time: float = Field(..., description="預計執行時間（秒）")
    symbols_to_process: List[str] = Field(..., description="將要處理的交易對")
    potential_issues: List[str] = Field(default_factory=list, description="潛在問題")

class SearchPreviewResponse(BaseResponse):
    """搜索預覽回應模型"""
    data: SearchPreviewData = Field(..., description="預覽數據")

# 任務相關回應 (保持不變)
class TaskStartResponse(BaseResponse):
    """任務啟動回應模型"""
    data: TaskInfo = Field(..., description="任務信息")

class TaskStatusResponse(BaseResponse):
    """任務狀態回應模型"""
    data: TaskInfo = Field(..., description="任務信息")

class TaskListData(BaseModel):
    """任務列表數據模型"""
    tasks: List[TaskInfo] = Field(..., description="任務列表")
    total: int = Field(..., description="總任務數")

class TaskListResponse(BaseResponse):
    """任務列表回應模型"""
    data: TaskListData = Field(..., description="任務列表數據")

# 配置相關回應 (保持不變)
class SearchTemplate(BaseModel):
    """搜索模板模型"""
    name: str = Field(..., description="模板名稱")
    description: str = Field(..., description="模板描述")
    config: Dict[str, Any] = Field(..., description="配置內容")
    is_default: bool = Field(..., description="是否為預設模板")
    created_at: datetime = Field(..., description="創建時間")

class TemplateListData(BaseModel):
    """模板列表數據模型"""
    templates: List[SearchTemplate] = Field(..., description="模板列表")
    total: int = Field(..., description="總模板數")

class TemplateListResponse(BaseResponse):
    """模板列表回應模型"""
    data: TemplateListData = Field(..., description="模板列表數據")

class ConfigData(BaseModel):
    """配置數據模型"""
    max_concurrent_searches: int = Field(..., description="最大並發搜索數")
    search_timeout_seconds: int = Field(..., description="搜索超時時間")
    enable_cache: bool = Field(..., description="是否啟用緩存")
    cache_ttl_seconds: int = Field(..., description="緩存TTL")
    supported_timeframes: List[str] = Field(..., description="支援的時間週期")
    max_lookback_periods: int = Field(..., description="最大回溯週期")
    max_sample_limit: int = Field(..., description="最大樣本限制")

class ConfigResponse(BaseResponse):
    """配置回應模型"""
    data: ConfigData = Field(..., description="配置數據")

# 導出相關回應 (保持不變)
class ExportData(BaseModel):
    """導出數據模型"""
    file_path: str = Field(..., description="文件路徑")
    file_size: int = Field(..., description="文件大小（字節）")
    format: str = Field(..., description="文件格式")
    download_url: Optional[str] = Field(None, description="下載URL")

class ExportResponse(BaseResponse):
    """導出回應模型"""
    data: ExportData = Field(..., description="導出數據")

# 統計相關回應 (保持不變)
class SystemStats(BaseModel):
    """系統統計模型"""
    total_searches: int = Field(..., description="總搜索次數")
    total_cases_found: int = Field(..., description="總發現案例數")
    average_execution_time: float = Field(..., description="平均執行時間")
    cache_hit_rate: float = Field(..., description="緩存命中率")
    active_tasks: int = Field(..., description="活躍任務數")

class StatsResponse(BaseResponse):
    """統計回應模型"""
    data: SystemStats = Field(..., description="系統統計")

# 成功回應的便利類型
SuccessResponse = BaseResponse

# ===== 新增：數據轉換輔助函數 =====

def convert_case_dict_to_model(case_dict: Dict[str, Any]) -> CaseData:
    """將字典格式的案例數據轉換為 Pydantic 模型"""
    
    def safe_float(value, default=None):
        """安全轉換為 float"""
        if value is None or (isinstance(value, float) and (value != value)):  # Check for NaN
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(value, default=None):
        """安全轉換為 int"""
        if value is None or (isinstance(value, float) and (value != value)):
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def safe_str(value, default=None):
        """安全轉換為 str"""
        if value is None:
            return default
        return str(value)
    
    # 處理時間戳
    timestamp = case_dict.get('timestamp')
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            timestamp = datetime.now()
    elif not isinstance(timestamp, datetime):
        timestamp = datetime.now()
    
    return CaseData(
        # 基本識別資訊
        symbol=case_dict.get('symbol', ''),
        timestamp=timestamp,
        trigger_idx=safe_int(case_dict.get('trigger_idx'), 0),
        
        # OHLCV 基礎數據
        open=safe_float(case_dict.get('open'), 0.0),
        high=safe_float(case_dict.get('high'), 0.0),
        low=safe_float(case_dict.get('low'), 0.0),
        close=safe_float(case_dict.get('close'), 0.0),
        volume=safe_float(case_dict.get('volume'), 0.0),
        price_change=safe_float(case_dict.get('price_change'), 0.0),
        market_phase=safe_str(case_dict.get('market_phase'), 'UNKNOWN'),
        
        # 基礎觸發條件參數
        timeframe=safe_str(case_dict.get('timeframe')),
        closing_strength=safe_float(case_dict.get('closing_strength')),
        price_position=safe_float(case_dict.get('price_position')),
        volume_multiplier=safe_float(case_dict.get('volume_multiplier')),
        taker_buy_ratio=safe_float(case_dict.get('taker_buy_ratio')),
        
        # 未來收益參數 (1-12根K線)
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
        
        # 未來回撤參數 (1-12根K線)
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
        
        # 時間描述參數
        hour_of_day=safe_int(case_dict.get('hour_of_day')),
        day_of_week=safe_int(case_dict.get('day_of_week')),

        # ===== 改寫：分類特徵參數 (9個) =====
        # 數值參數（3個）
        past_3day_max_volatility=safe_float(case_dict.get('past_3day_max_volatility')),
        past_3day_direction=safe_float(case_dict.get('past_3day_direction')),
        past_3day_volume_cv=safe_float(case_dict.get('past_3day_volume_cv')),

        # 分類參數（6個）
        volatility_class=safe_str(case_dict.get('volatility_class')),
        direction_class=safe_str(case_dict.get('direction_class')),
        volume_class=safe_str(case_dict.get('volume_class')),
        market_class=safe_str(case_dict.get('market_class')),
        market_class_name=safe_str(case_dict.get('market_class_name')),
        difficulty_level=safe_str(case_dict.get('difficulty_level')),

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

# 導出 (更新導出清單)
__all__ = [
    "BaseResponse",
    "ErrorResponse", 
    "ErrorDetail",
    "TaskStatusEnum",
    "TaskProgress",
    "TaskInfo",
    "CaseData",
    "CaseSummary",
    "SamplingQuality",
    "SearchResultData",
    "SearchResponse",
    "SearchPreviewData", 
    "SearchPreviewResponse",
    "TaskStartResponse",
    "TaskStatusResponse",
    "TaskListResponse",
    "SearchTemplate",
    "TemplateListResponse",
    "ConfigResponse",
    "ExportResponse",
    "StatsResponse",
    "SuccessResponse",
    # 新增的模型
    "ParameterStat",
    "ParameterStatistics",
    "ParameterStatus", 
    "ParameterValidationReport",
    "convert_case_dict_to_model"
]