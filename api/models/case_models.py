"""
案例相關數據模型

定義案例導入、批量下載的請求和響應模型
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class CaseRecord(BaseModel):
    """
    案例記錄模型

    代表單個交易案例的完整信息
    """
    case_id: str = Field(..., description="案例唯一ID")
    symbol: str = Field(..., description="交易對symbol（如BTCUSDT）")
    timeframe: str = Field(..., description="時間框架（1h/4h/12h/1d）")
    timestamp: int = Field(..., description="案例時間點（Unix timestamp）")
    positive_case: int = Field(..., description="案例標籤（1=正例，0=反例）", ge=0, le=1)

    # 可選欄位
    source_file: Optional[str] = Field(None, description="來源CSV文件名")
    import_time: Optional[datetime] = Field(None, description="導入時間")

    @validator('timeframe')
    def validate_timeframe(cls, v):
        """驗證timeframe格式"""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w']
        if v not in valid_timeframes:
            raise ValueError(f"Invalid timeframe: {v}. Must be one of {valid_timeframes}")
        return v

    @validator('symbol')
    def validate_symbol(cls, v):
        """驗證symbol格式"""
        if not v or not v.isupper():
            raise ValueError(f"Symbol must be uppercase: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "BTCUSDT_1736942400_1",
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "timestamp": 1736942400,
                "positive_case": 1,
                "source_file": "cases_2025_01.csv",
                "import_time": "2025-01-15T12:00:00"
            }
        }


class CaseImportRequest(BaseModel):
    """
    CSV導入請求模型
    """
    # CSV數據以base64編碼上傳，或直接使用File upload
    # 這裡定義可選參數
    default_timeframe: Optional[str] = Field("1h", description="預設時間框架（CSV缺少時使用）")
    validate_only: bool = Field(False, description="僅驗證不導入")

    class Config:
        json_schema_extra = {
            "example": {
                "default_timeframe": "1h",
                "validate_only": False
            }
        }


class CaseImportResponse(BaseModel):
    """
    CSV導入響應模型
    """
    success: bool = Field(..., description="是否成功")
    total_rows: int = Field(..., description="CSV總行數")
    valid_cases: int = Field(..., description="有效案例數")
    invalid_cases: int = Field(..., description="無效案例數")
    imported_cases: int = Field(..., description="實際導入案例數")
    errors: List[str] = Field(default_factory=list, description="錯誤列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    case_ids: List[str] = Field(default_factory=list, description="導入的案例ID列表")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_rows": 100,
                "valid_cases": 95,
                "invalid_cases": 5,
                "imported_cases": 95,
                "errors": ["Row 3: Missing 'symbol' column"],
                "warnings": ["Row 10: Future timestamp, skipped"],
                "case_ids": ["BTCUSDT_1736942400_1", "ETHUSDT_1736946000_1"]
            }
        }


class BatchDownloadRequest(BaseModel):
    """
    批量K線下載請求模型
    """
    case_ids: Optional[List[str]] = Field(None, description="要下載的案例ID列表（None=全部）")
    lookback_bars: int = Field(240, description="往前K線根數", ge=1, le=1000)
    forward_bars: int = Field(96, description="往後K線根數", ge=1, le=500)
    force_redownload: bool = Field(False, description="強制重新下載（覆蓋已有數據）")

    @validator('lookback_bars')
    def validate_lookback(cls, v):
        """驗證lookback_bars範圍"""
        if not 1 <= v <= 1000:
            raise ValueError("lookback_bars must be between 1 and 1000")
        return v

    @validator('forward_bars')
    def validate_forward(cls, v):
        """驗證forward_bars範圍"""
        if not 1 <= v <= 500:
            raise ValueError("forward_bars must be between 1 and 500")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "case_ids": None,
                "lookback_bars": 240,
                "forward_bars": 96,
                "force_redownload": False
            }
        }


class TaskStatus(str, Enum):
    """任務狀態枚舉"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadProgress(BaseModel):
    """
    下載進度模型
    """
    task_id: str = Field(..., description="任務ID")
    status: TaskStatus = Field(..., description="任務狀態")
    total_cases: int = Field(..., description="總案例數")
    completed_cases: int = Field(..., description="已完成案例數")
    failed_cases: int = Field(..., description="失敗案例數")
    progress_percent: float = Field(..., description="進度百分比（0-100）")

    # 詳細信息
    current_symbol: Optional[str] = Field(None, description="當前處理的symbol")
    estimated_time_remaining: Optional[int] = Field(None, description="預估剩餘時間（秒）")
    failed_case_ids: List[str] = Field(default_factory=list, description="失敗案例ID列表")
    error_messages: List[str] = Field(default_factory=list, description="錯誤消息列表")

    # 時間戳記
    start_time: datetime = Field(..., description="開始時間")
    end_time: Optional[datetime] = Field(None, description="結束時間")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "batch_download_20250115_120000",
                "status": "running",
                "total_cases": 100,
                "completed_cases": 45,
                "failed_cases": 2,
                "progress_percent": 45.0,
                "current_symbol": "BTCUSDT",
                "estimated_time_remaining": 120,
                "failed_case_ids": ["INVALID_1", "TIMEOUT_2"],
                "error_messages": ["Invalid symbol: XYZ", "Timeout downloading ABC"],
                "start_time": "2025-01-15T12:00:00",
                "end_time": None
            }
        }


class DownloadResult(BaseModel):
    """
    批量下載結果模型
    """
    task_id: str = Field(..., description="任務ID")
    success: bool = Field(..., description="整體是否成功")
    total_cases: int = Field(..., description="總案例數")
    successful_downloads: int = Field(..., description="成功下載數")
    failed_downloads: int = Field(..., description="失敗下載數")
    skipped_cases: int = Field(..., description="跳過案例數（已存在且非force）")

    # 詳細結果
    downloaded_case_ids: List[str] = Field(default_factory=list, description="成功下載案例ID")
    failed_case_ids: List[str] = Field(default_factory=list, description="失敗案例ID")
    error_details: Dict[str, str] = Field(default_factory=dict, description="錯誤詳情（case_id → error_msg）")

    # 統計信息
    total_bars_downloaded: int = Field(0, description="總下載K線根數")
    total_download_time: float = Field(0.0, description="總下載時間（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "batch_download_20250115_120000",
                "success": True,
                "total_cases": 100,
                "successful_downloads": 95,
                "failed_downloads": 3,
                "skipped_cases": 2,
                "downloaded_case_ids": ["BTCUSDT_1736942400_1"],
                "failed_case_ids": ["INVALID_1"],
                "error_details": {
                    "INVALID_1": "Invalid symbol format"
                },
                "total_bars_downloaded": 31920,
                "total_download_time": 125.5
            }
        }


class CaseListResponse(BaseModel):
    """
    案例列表響應模型
    """
    total: int = Field(..., description="總案例數")
    cases: List[CaseRecord] = Field(..., description="案例列表")

    # 統計信息
    positive_count: int = Field(..., description="正例數量")
    negative_count: int = Field(..., description="反例數量")
    symbols: List[str] = Field(..., description="涉及的symbol列表")
    timeframes: List[str] = Field(..., description="涉及的timeframe列表")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "cases": [],
                "positive_count": 30,
                "negative_count": 70,
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["1h", "4h"]
            }
        }
