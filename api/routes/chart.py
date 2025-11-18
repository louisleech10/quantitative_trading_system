"""
圖表相關API路由

提供K線數據獲取、圖表數據等API端點
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

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
    forward_bars: Optional[int] = Query(None, description="往後K線根數（預設48，可為0表示不看未來）", ge=0, le=1000)
):
    """
    獲取圖表數據

    **新邏輯（如果提供case_timeframe）**：
    - case_timestamp = TO (Target Open)
    - 返回 to_index, tc_index, case_bars
    - K線範圍：TO往前100根 + 案例區間 + TC往後48根

    **舊邏輯（不提供case_timeframe，向後兼容）**：
    - case_timestamp 為中心點
    - 返回 center_index
    - K線範圍：中心點±max_bars/2

    Args:
        symbol: 交易對（如ETHUSDT）
        case_timestamp: 案例時間點T/TO（Unix秒）
        timeframe: 時間框架（查看用，1h, 4h, 1d等）
        max_bars: 最大返回根數（預設200，範圍1-1000）
        case_timeframe: 案例時間框架（如"12h"），如提供則使用新邏輯

    Returns:
        Dict: 圖表數據
        {
            "success": bool,
            "data": {
                "case_timestamp": int,
                "klines": List[Dict],
                "center_index": int (舊) 或
                "to_index": int, "tc_index": int, "case_bars": int (新),
                "metadata": {...}
            }
        }

    Raises:
        HTTPException:
            - 400: 參數驗證失敗
            - 404: 數據不存在
            - 500: 系統錯誤
    """
    logger.info(
        f"GET /api/v1/chart/data: symbol={symbol}, case_timestamp={case_timestamp}, "
        f"timeframe={timeframe}, case_timeframe={case_timeframe}, max_bars={max_bars}, "
        f"lookback_bars={lookback_bars}, forward_bars={forward_bars}"
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
            forward_bars=forward_bars
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
