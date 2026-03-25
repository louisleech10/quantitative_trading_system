"""
Feature Factory 專屬資料 API

提供獨立於案例系統的 K 線下載與查詢路由。
"""

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.core.logging import get_logger
from api.services.feature_kline_service import get_feature_kline_service

logger = get_logger("api.routes.feature_data")

router = APIRouter(prefix="/api/v1/feature-data", tags=["Feature Data"])


# ── Request / Response Models ──────────────────────────────────────────────

SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]


class FeatureKlineDownloadRequest(BaseModel):
    """Feature Factory K 線下載請求。"""

    symbols: List[str] = Field(
        ...,
        min_length=1,
        description=(
            "標的清單，支援任意 symbol 如 BTCUSDT、AAPL、NQH25。"
            "特殊值 ALL_USDT 會展開為 Binance 全部 USDT 交易對。"
        ),
    )
    timeframes: List[str] = Field(
        default=["12h"],
        description="時間框架清單，支援 1m/5m/15m/30m/1h/4h/12h/1d/1w",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="起始日期 YYYY-MM-DD，None 表示從歷史最早",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="結束日期 YYYY-MM-DD，None 表示到今天",
    )
    force_redownload: bool = Field(
        default=False,
        description="是否強制重新下載（覆蓋已有資料）",
    )

    @field_validator("symbols")
    @classmethod
    def deduplicate_symbols(cls, v: List[str]) -> List[str]:
        seen: set = set()
        return [s.upper() for s in v if not (s.upper() in seen or seen.add(s.upper()))]  # type: ignore[func-returns-value]

    @field_validator("timeframes")
    @classmethod
    def validate_timeframes(cls, v: List[str]) -> List[str]:
        invalid = [tf for tf in v if tf not in SUPPORTED_TIMEFRAMES]
        if invalid:
            raise ValueError(
                f"不支援的時間框架：{invalid}，可用值：{SUPPORTED_TIMEFRAMES}"
            )
        if not v:
            raise ValueError("timeframes 不可為空")
        return v


class FeatureKlineDownloadResponse(BaseModel):
    task_id: str
    message: str
    total_jobs: int
    symbols_count: int
    timeframes: List[str]


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/kline/download", response_model=FeatureKlineDownloadResponse)
async def start_feature_kline_download(
    request: FeatureKlineDownloadRequest,
    background_tasks: BackgroundTasks,
) -> FeatureKlineDownloadResponse:
    """
    啟動 Feature Factory 專屬 K 線下載任務。

    - 完全獨立於案例 K 線（data-preparation 頁）
    - 資料儲存於 data_cache/feature_klines/
    - 支援 ALL_USDT 展開
    """
    svc = get_feature_kline_service()

    # 展開 ALL_USDT
    expanded_symbols = svc.expand_symbols(request.symbols)
    if not expanded_symbols:
        raise HTTPException(status_code=400, detail="展開後的標的清單為空，請確認輸入或 ALL_USDT 展開結果")

    task_id = svc.create_download_task(
        symbols=expanded_symbols,
        timeframes=request.timeframes,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    background_tasks.add_task(
        svc.execute_download,
        task_id,
        expanded_symbols,
        request.timeframes,
        request.start_date,
        request.end_date,
        request.force_redownload,
    )

    total_jobs = len(expanded_symbols) * len(request.timeframes)
    logger.info(
        f"Feature K 線下載任務 {task_id} 已建立：{len(expanded_symbols)} 個標的，"
        f"{len(request.timeframes)} 個時間框架"
    )

    return FeatureKlineDownloadResponse(
        task_id=task_id,
        message="下載任務已啟動",
        total_jobs=total_jobs,
        symbols_count=len(expanded_symbols),
        timeframes=request.timeframes,
    )


@router.get("/kline/download-status/{task_id}")
async def get_feature_kline_download_status(task_id: str):
    """查詢 Feature K 線下載任務進度。"""
    svc = get_feature_kline_service()
    status = svc.get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"任務不存在：{task_id}")
    return status


@router.get("/kline/list")
async def list_downloaded_feature_klines():
    """列出 Feature Factory 已下載的所有 (symbol, timeframe) 組合。"""
    svc = get_feature_kline_service()
    entries = svc.list_downloaded()
    return {"entries": entries, "total": len(entries)}


@router.get("/exchange/usdt-symbols")
async def get_usdt_symbols():
    """
    從 Binance 取得所有 USDT 交易對清單（供前端 ALL_USDT 預覽使用）。
    不依賴 API key，直接呼叫公開端點。
    """
    svc = get_feature_kline_service()
    pairs = svc._get_all_usdt_pairs()  # noqa: SLF001
    return {"symbols": pairs, "total": len(pairs)}


@router.get("/kline/quality/{symbol}/{timeframe}")
async def get_feature_kline_quality(symbol: str, timeframe: str):
    """
    取得指定 symbol/timeframe 的數據品質報告。

    包含：
    - metadata（bar 數、時間範圍、資料來源）
    - integrity 完整性檢查（時間連續性、重複 timestamp、OHLC 合理性、taker_ratio 範圍）
    """
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的時間框架：{timeframe}，可用值：{SUPPORTED_TIMEFRAMES}",
        )
    svc = get_feature_kline_service()
    report = svc.get_quality_report(symbol.upper(), timeframe)
    return report

