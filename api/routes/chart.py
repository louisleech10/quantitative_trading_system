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
    case_timestamp: int = Query(..., description="案例時間點T（Unix秒）"),
    timeframe: str = Query(..., description="時間框架（1h/4h/1d等）"),
    max_bars: int = Query(200, description="最大返回根數（預設200）", ge=1, le=1000)
):
    """
    獲取圖表數據（以T為中心的K線數據）

    用於前端圖表顯示，返回以案例時間點T為中心的K線數據。

    Args:
        symbol: 交易對（如ETHUSDT）
        case_timestamp: 案例時間點T（Unix秒）
        timeframe: 時間框架（1h, 4h, 1d等）
        max_bars: 最大返回根數（預設200，範圍1-1000）

    Returns:
        Dict: 圖表數據
        {
            "success": bool,
            "data": {
                "case_timestamp": int,
                "klines": List[Dict],
                "center_index": int,
                "metadata": {
                    "symbol": str,
                    "timeframe": str,
                    "total_bars": int,
                    "time_range": {
                        "start": int,
                        "end": int
                    }
                }
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
        f"timeframe={timeframe}, max_bars={max_bars}"
    )

    try:
        # 調用服務獲取數據
        result = chart_data_service.get_chart_data(
            symbol=symbol,
            case_timestamp=case_timestamp,
            timeframe=timeframe,
            max_bars=max_bars
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

        logger.info(
            f"Chart data fetched successfully: {len(result['data']['klines'])} klines, "
            f"center_index={result['data']['center_index']}"
        )

        return result

    except HTTPException:
        # 重新拋出HTTP異常
        raise
    except Exception as e:
        error_msg = f"Unexpected error in get_chart_data: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
