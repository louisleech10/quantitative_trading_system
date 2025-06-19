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
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="
    BETWEEN = "between"

class ConditionTypeEnum(str, Enum):
    """條件類型"""
    PRICE = "price"
    VOLUME = "volume"
    PATTERN = "pattern"

class FilterConditionRequest(BaseModel):
    """篩選條件請求模型"""
    condition_type: ConditionTypeEnum = Field(..., description="條件類型")
    parameter: str = Field(..., description="參數名稱", min_length=1)
    operator: OperatorEnum = Field(..., description="運算符")
    value: Union[float, int, List[Union[float, int]]] = Field(..., description="閾值")
    description: Optional[str] = Field(None, description="條件描述")
    
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
    name: str = Field(..., description="配置名稱", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="配置描述", max_length=500)
    
    # 基本搜索參數
    timeframe: TimeframeEnum = Field(TimeframeEnum.HOUR_12, description="時間週期")
    start_date: Union[str, date] = Field(..., description="開始日期 (YYYY-MM-DD)")
    end_date: Union[str, date] = Field(..., description="結束日期 (YYYY-MM-DD)")
    
    # K線參數
    lookback_periods: int = Field(100, description="回溯K線數量", ge=1, le=500)
    forward_periods: int = Field(6, description="向前看K線數量", ge=1, le=50)
    
    # 採樣參數
    sample_limit: int = Field(500, description="樣本數量限制", ge=1, le=5000)
    min_volume: float = Field(0, description="最小成交量要求", ge=0)
    exclude_new_listing_days: int = Field(7, description="排除新上市後天數", ge=0, le=365)
    
    # 篩選條件
    initial_conditions: List[FilterConditionRequest] = Field(
        default_factory=list, 
        description="初始篩選條件"
    )
    advanced_conditions: List[FilterConditionRequest] = Field(
        default_factory=list,
        description="高級篩選條件"
    )
    
    # 正反例採樣配置
    negative_sampling: bool = Field(True, description="是否生成負例")
    positive_negative_ratio: float = Field(1.0, description="正負例比例", gt=0, le=10)
    
    # 批次處理參數
    batch_size: int = Field(20, description="批次處理大小", ge=1, le=100)
    
    @validator('start_date', 'end_date', pre=True)
    def parse_date(cls, v):
        """解析日期字串"""
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("日期格式必須為 YYYY-MM-DD")
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """驗證日期範圍"""
        start_date = values.get('start_date')
        if start_date and v <= start_date:
            raise ValueError("結束日期必須晚於開始日期")
        return v
    
    @validator('initial_conditions', 'advanced_conditions')
    def validate_conditions(cls, v):
        """驗證條件列表"""
        if len(v) > 20:  # 限制條件數量
            raise ValueError("條件數量不能超過20個")
        return v

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