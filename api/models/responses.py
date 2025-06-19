from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# 基礎回應模型
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

# 任務狀態相關
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

# 案例相關模型
class CaseData(BaseModel):
    """案例數據模型"""
    symbol: str = Field(..., description="交易對")
    timestamp: datetime = Field(..., description="觸發時間")
    trigger_idx: int = Field(..., description="觸發K線索引")
    close: float = Field(..., description="收盤價")
    volume: float = Field(..., description="成交量")
    price_change: float = Field(..., description="價格變化百分比")
    market_phase: str = Field(..., description="市場階段")
    
    # 未來表現指標
    future1_close_return: Optional[float] = Field(None, description="未來1根K線回報")
    future2_close_return: Optional[float] = Field(None, description="未來2根K線回報")
    future4_close_return: Optional[float] = Field(None, description="未來4根K線回報")
    future6_close_return: Optional[float] = Field(None, description="未來6根K線回報")
    future_max_return: Optional[float] = Field(None, description="未來最大回報")
    future_max_drawdown: Optional[float] = Field(None, description="未來最大回撤")
    
    # 前期特徵
    prior_volatility: Optional[float] = Field(None, description="前期波動率")
    prior_range: Optional[float] = Field(None, description="前期價格範圍")
    prior_abs_change_sum: Optional[float] = Field(None, description="前期絕對變化總和")
    
    # 時間範圍信息
    time_range: Dict[str, str] = Field(..., description="時間範圍")

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

# 搜索結果相關
class SearchResultData(BaseModel):
    """搜索結果數據模型"""
    cases: List[CaseData] = Field(..., description="案例列表")
    summary: CaseSummary = Field(..., description="案例摘要")
    sampling_quality: SamplingQuality = Field(..., description="採樣品質")
    execution_time: float = Field(..., description="執行時間（秒）")
    cache_used: bool = Field(..., description="是否使用了緩存")

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

# 任務相關回應
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

# 配置相關回應
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

# 導出相關回應
class ExportData(BaseModel):
    """導出數據模型"""
    file_path: str = Field(..., description="文件路徑")
    file_size: int = Field(..., description="文件大小（字節）")
    format: str = Field(..., description="文件格式")
    download_url: Optional[str] = Field(None, description="下載URL")

class ExportResponse(BaseResponse):
    """導出回應模型"""
    data: ExportData = Field(..., description="導出數據")

# 統計相關回應
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

# 導出
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
    "SuccessResponse"
]