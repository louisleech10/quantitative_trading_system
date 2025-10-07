from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from enum import Enum

class TimeframeEnum(str, Enum):
    """支援的時間週期"""
    HOUR_1 = "1h"
    HOUR_4 = "4h" 
    HOUR_12 = "12h"
    DAY_1 = "1d"

class OperatorEnum(str, Enum):
    """支援的運算符"""
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    BETWEEN = "between"


class ConditionTypeEnum(str, Enum):
    """條件類型"""
    PRICE = "price"
    VOLUME = "volume"
    PATTERN = "pattern"

# 修復 FilterConditionRequest 驗證邏輯
class FilterConditionRequest(BaseModel):
    """篩選條件請求模型"""
    condition_type: ConditionTypeEnum = Field(..., description="條件類型")
    parameter: str = Field(..., description="參數名稱", min_length=1)
    operator: OperatorEnum = Field(..., description="運算符")
    value: Union[float, int, List[Union[float, int]]] = Field(..., description="閾值")
    description: Optional[str] = Field(None, description="條件描述")
    
    @validator('parameter')
    def validate_parameter_for_filtering(cls, v):
        """驗證參數是否可用於篩選"""
        # 只允許 price_change 用於篩選
        allowed_filtering_params = {'price_change'}
        
        if v not in allowed_filtering_params:
            raise ValueError(f"參數 '{v}' 不可用於篩選。僅支援篩選參數: {allowed_filtering_params}")
        
        return v
    
    @validator('value')
    def validate_value(cls, v, values):
        """驗證值的格式"""
        operator = values.get('operator')
        
        if operator == OperatorEnum.BETWEEN:
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("between運算符需要包含兩個數值的列表")
            if v[0] >= v[1]:
                raise ValueError("between運算符的第一個值必須小於第二個值")
        else:
            if isinstance(v, list):
                raise ValueError(f"運算符 {operator} 不支援列表值")
        
        return v

class SearchConfigRequest(BaseModel):
    """搜索配置請求模型"""
    name: str = Field(..., description="搜索配置名稱")
    description: Optional[str] = Field(None, description="搜索描述")
    timeframe: TimeframeEnum = Field(..., description="時間週期")

    symbols: Optional[List[str]] = Field(None, description="交易對列表")

    # 時間範圍 - 設為可選，有預設值，支持駝峰格式別名
    start_date: Optional[str] = Field(None, alias="startDate", description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, alias="endDate", description="結束日期 (YYYY-MM-DD)")
    time_range: Optional[List[str]] = Field(None, alias="timeRange", description="時間範圍 [start, end]")

    # K線參數
    lookback_periods: int = Field(default=100, ge=1, le=1000, description="回看週期數")
    forward_periods: int = Field(default=20, ge=1, le=100, description="前瞻週期數")

    # 採樣參數
    sample_limit: int = Field(default=500, ge=1, le=10000, description="樣本數量限制")
    min_volume: float = Field(default=0, ge=0, description="最小成交量")
    exclude_new_listing_days: int = Field(default=7, ge=0, le=365, description="排除新上市天數")

    # 搜索條件
    initial_conditions: List[FilterConditionRequest] = Field(default_factory=list, description="初始條件")
    advanced_conditions: List[FilterConditionRequest] = Field(default_factory=list, description="高級條件")
    
    def model_post_init(self, __context):
        """Pydantic V2 的 post-init 方法"""
        # DEBUG LOG - 需要debug時取消註釋
        # from api.core.logging import get_logger
        # logger = get_logger("api.models.requests")
        # logger.info(f"=== SearchConfigRequest model_post_init ===")
        # logger.info(f"Original start_date: {self.start_date}")
        # logger.info(f"Original end_date: {self.end_date}")
        # logger.info(f"Original time_range: {self.time_range}")

        # 只有在所有時間字段都為空時才設置預設值
        if not self.start_date and not self.end_date and not self.time_range:
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)  # 預設3個月
            self.start_date = start_date.strftime('%Y-%m-%d')
            self.end_date = end_date.strftime('%Y-%m-%d')
            # logger.info(f"設置了預設時間範圍: {self.start_date} 到 {self.end_date}")

        # 同步 time_range 和 start_date/end_date (但不覆蓋現有值)
        if self.start_date and self.end_date and not self.time_range:
            self.time_range = [self.start_date, self.end_date]
            # logger.info(f"從start_date/end_date同步到time_range: {self.time_range}")
        elif self.time_range and len(self.time_range) == 2 and not self.start_date:
            self.start_date = self.time_range[0]
            self.end_date = self.time_range[1]
            # logger.info(f"從time_range同步到start_date/end_date: {self.start_date} 到 {self.end_date}")

        # logger.info(f"Final start_date: {self.start_date}")
        # logger.info(f"Final end_date: {self.end_date}")
        # logger.info(f"Final time_range: {self.time_range}")
    
    model_config = {
        "populate_by_name": True,  # 允許使用字段名或別名
        "json_schema_extra": {
            "example": {
                "name": "動能突破搜索",
                "description": "尋找大漲前的動能訊號",
                "timeframe": "12h",
                "startDate": "2024-01-01",  # 使用駝峰格式
                "endDate": "2024-06-30",    # 使用駝峰格式
                "sample_limit": 100,
                "min_volume": 1000000,
                "initial_conditions": [
                    {
                        "condition_type": "price_change",
                        "parameter": "price_change_pct",
                        "operator": ">=",
                        "value": 0.05,
                        "description": "價格上漲5%以上"
                    }
                ]
            }
        }
    }

# 新增 NegativeCaseRequest 模型

class NegativeCaseRequest(BaseModel):
    """反例搜索請求模型"""
    search_config: SearchConfigRequest = Field(..., description="反例搜索配置")
    negative_ratio: float = Field(default=2.0, ge=1.0, le=5.0, description="反例與正例的比例")
    enable_time_separation: bool = Field(
        default=True,
        description="是否啟用時間分離（防止反例與正例時間過近，按Symbol獨立計算）"
    )
    time_separation_days: int = Field(
        default=3,
        ge=0,
        le=30,
        description="時間分離天數（0=關閉，按Symbol獨立過濾）"
    )
    sampling_strategy: str = Field(default="time_separated", description="採樣策略")

    class Config:
        json_schema_extra = {
            "example": {
                "search_config": {
                    "name": "negative_example_search",
                    "timeframe": "12h",
                    "initial_conditions": []
                },
                "negative_ratio": 2.0,
                "enable_time_separation": True,
                "time_separation_days": 3,
                "sampling_strategy": "time_separated"
            }
        }

class SearchPreviewRequest(BaseModel):
    """搜索預覽請求模型"""
    config: SearchConfigRequest = Field(..., description="搜索配置")
    symbols_limit: int = Field(10, description="預覽的交易對數量限制", ge=1, le=50)

class CaseSearchRequest(BaseModel):
    """案例搜索請求模型"""
    config: SearchConfigRequest = Field(..., description="搜索配置")
    symbols: Optional[List[str]] = Field(None, description="指定交易對列表（可選）")
    save_results: bool = Field(True, description="是否保存結果")
    export_format: Optional[str] = Field("csv", description="Export format", pattern="^(csv|json|h5)$")

class SearchTemplateRequest(BaseModel):
    """搜索模板請求模型"""
    template_name: str = Field(..., description="模板名稱", min_length=1)
    config: SearchConfigRequest = Field(..., description="搜索配置")
    is_default: bool = Field(False, description="是否為預設模板")

class BulkSearchRequest(BaseModel):
    """批量搜索請求模型"""
    configs: List[SearchConfigRequest] = Field(..., description="多個搜索配置", min_items=1, max_items=5)
    parallel_execution: bool = Field(False, description="是否並行執行")

# 配置更新相關模型
class ConfigUpdateRequest(BaseModel):
    """配置更新請求模型"""
    max_concurrent_searches: Optional[int] = Field(None, ge=1, le=10)
    search_timeout_seconds: Optional[int] = Field(None, ge=60, le=3600)
    enable_cache: Optional[bool] = Field(None)
    cache_ttl_seconds: Optional[int] = Field(None, ge=300, le=86400)

# 任務管理相關模型
class TaskCancelRequest(BaseModel):
    """任務取消請求模型"""
    task_id: str = Field(..., description="任務ID")
    reason: Optional[str] = Field(None, description="取消原因")

# 導出
__all__ = [
    "TimeframeEnum",
    "OperatorEnum", 
    "ConditionTypeEnum",
    "FilterConditionRequest",
    "SearchConfigRequest",
    "SearchPreviewRequest",
    "CaseSearchRequest",
    "SearchTemplateRequest",
    "BulkSearchRequest",
    "ConfigUpdateRequest",
    "TaskCancelRequest"
]