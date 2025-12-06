"""
圖表相關API路由

提供K線數據獲取、圖表數據等API端點
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json

from ..services.chart_data_service import get_chart_data_service
from ..core.logging import get_logger

logger = get_logger("api.routes.chart")

router = APIRouter(prefix="/api/v1/chart", tags=["Chart Data"])

# 獲取服務實例
chart_data_service = get_chart_data_service()


@router.get("/data")
async def get_chart_data(
    symbol: str = Query(..., description="交易對（如ETHUSDT）"),
    case_timestamp: int = Query(..., description="案例時間點T/TO（Unix秒）"),
    timeframe: str = Query(..., description="時間框架（查看用，1h/4h/1d等）"),
    max_bars: int = Query(200, description="最大返回根數（預設200）", ge=1, le=1000),
    case_timeframe: Optional[str] = Query(None, description="案例時間框架（如12h），提供則使用TO/TC邏輯"),
    lookback_bars: Optional[int] = Query(None, description="往前K線根數（預設100）", ge=1, le=1000),
    forward_bars: Optional[int] = Query(None, description="往後K線根數（預設48，可為0表示不看未來）", ge=0, le=1000),
    # 新增：指標計算參數
    indicator_type: Optional[str] = Query(None, description="指標類型（如ema）"),
    data_source: Optional[str] = Query(None, description="數據源（close/open/high/low/volume/taker_buy_volume/taker_ratio）"),
    strategy_logic: Optional[str] = Query(None, description="策略邏輯（three_line/short_long_cross/mid_long_cross）"),
    short_period: Optional[int] = Query(None, description="短週期EMA（如5）", ge=1, le=500),
    mid_period: Optional[int] = Query(None, description="中週期EMA（如20）", ge=1, le=500),
    long_period: Optional[int] = Query(None, description="長週期EMA（如60）", ge=1, le=500)
):
    """
    獲取圖表數據（可含指標計算）

    **新邏輯（如果提供case_timeframe）**：
    - case_timestamp = TO (Target Open)
    - 返回 to_index, tc_index, case_bars
    - K線範圍：TO往前100根 + 案例區間 + TC往後48根

    **舊邏輯（不提供case_timeframe，向後兼容）**：
    - case_timestamp 為中心點
    - 返回 center_index
    - K線範圍：中心點±max_bars/2

    **指標計算（可選）**：
    - 如果提供 indicator_type + strategy_logic + 對應週期，將返回 indicators 欄位
    - 使用後端 IndicatorEngine 計算，確保與策略測試結果一致

    Args:
        symbol: 交易對（如ETHUSDT）
        case_timestamp: 案例時間點T/TO（Unix秒）
        timeframe: 時間框架（查看用，1h, 4h, 1d等）
        max_bars: 最大返回根數（預設200，範圍1-1000）
        case_timeframe: 案例時間框架（如"12h"），如提供則使用新邏輯
        indicator_type: 指標類型（如 "ema"）
        data_source: 數據源（如 "close"）
        strategy_logic: 策略邏輯（three_line/short_long_cross/mid_long_cross）
        short_period: 短週期（如 5）
        mid_period: 中週期（如 20）
        long_period: 長週期（如 60）

    Returns:
        Dict: 圖表數據
        {
            "success": bool,
            "data": {
                "case_timestamp": int,
                "klines": List[Dict],
                "center_index": int (舊) 或
                "to_index": int, "tc_index": int, "case_bars": int (新),
                "indicators": {...} (可選),
                "metadata": {...}
            }
        }

    Raises:
        HTTPException:
            - 400: 參數驗證失敗
            - 404: 數據不存在
            - 500: 系統錯誤
    """
    # 構建指標配置（如果提供了相關參數）
    indicator_config = None
    if indicator_type and strategy_logic:
        params = {}
        if short_period is not None:
            params["short_period"] = short_period
        if mid_period is not None:
            params["mid_period"] = mid_period
        if long_period is not None:
            params["long_period"] = long_period
        
        if params:  # 至少有一個週期參數
            indicator_config = {
                "indicator_type": indicator_type,
                "data_source": data_source or "close",
                "strategy_logic": strategy_logic,
                "params": params
            }
            logger.info(f"Indicator config: {indicator_config}")

    logger.info(
        f"GET /api/v1/chart/data: symbol={symbol}, case_timestamp={case_timestamp}, "
        f"timeframe={timeframe}, case_timeframe={case_timeframe}, max_bars={max_bars}, "
        f"lookback_bars={lookback_bars}, forward_bars={forward_bars}, "
        f"has_indicator_config={indicator_config is not None}"
    )

    try:
        # 調用服務獲取數據
        result = chart_data_service.get_chart_data(
            symbol=symbol,
            case_timestamp=case_timestamp,
            timeframe=timeframe,
            max_bars=max_bars,
            case_timeframe=case_timeframe,
            lookback_bars=lookback_bars,
            forward_bars=forward_bars,
            indicator_config=indicator_config
        )

        # 檢查結果
        if not result.get("success", False):
            error = result.get("error", {})
            error_code = error.get("code", "UNKNOWN_ERROR")
            error_message = error.get("message", "Unknown error")

            # 根據錯誤代碼返回適當的HTTP狀態碼
            if error_code == "DATA_NOT_FOUND":
                logger.warning(f"Data not found: {error_message}")
                raise HTTPException(status_code=404, detail=error_message)
            elif error_code.startswith("VALIDATION_"):
                logger.warning(f"Validation error: {error_message}")
                raise HTTPException(status_code=400, detail=error_message)
            else:
                logger.error(f"System error: {error_message}")
                raise HTTPException(status_code=500, detail=error_message)

        # 日誌輸出（新/舊邏輯）
        data = result['data']
        if 'to_index' in data:
            logger.info(
                f"Chart data fetched successfully: {len(data['klines'])} klines, "
                f"TO at {data['to_index']}, TC at {data['tc_index']}"
            )
        else:
            logger.info(
                f"Chart data fetched successfully: {len(data['klines'])} klines, "
                f"center_index={data.get('center_index', -1)}"
            )

        return result

    except HTTPException:
        # 重新拋出HTTP異常
        raise
    except Exception as e:
        error_msg = f"Unexpected error in get_chart_data: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
