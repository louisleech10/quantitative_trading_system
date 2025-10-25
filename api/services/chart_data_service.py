"""
圖表數據服務 - 為前端圖表提供K線數據

功能：
1. 獲取以T點為中心的K線數據（用於圖表顯示）
2. 數據格式轉換（HDF5 → JSON）
3. center_index計算（T在陣列中的位置）
4. 錯誤處理和日誌記錄

設計原則：
- 基於kline_storage_service構建
- 符合API_SPECIFICATION_CHART.md規範
- 完整錯誤處理
- 適當日誌記錄
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.services.kline_storage_service import KlineStorageService
from api.core.logging import get_logger

logger = get_logger("api.chart_data_service")


class ChartDataService:
    """
    圖表數據服務

    為前端圖表提供K線數據，支援以案例時間點T為中心的數據裁切
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        初始化圖表數據服務

        Args:
            cache_dir: K線緩存目錄路徑
        """
        self.storage_service = KlineStorageService(cache_dir=cache_dir)
        logger.info(f"ChartDataService initialized")


    def get_chart_data(self,
                      symbol: str,
                      case_timestamp: int,
                      timeframe: str,
                      max_bars: int = 200) -> Dict:
        """
        獲取圖表數據（以T為中心）

        Args:
            symbol: 交易對（如ETHUSDT）
            case_timestamp: 案例時間點T（Unix秒）
            timeframe: 時間框架（如1h, 4h）
            max_bars: 最大返回根數（預設200）

        Returns:
            Dict: 符合API規範的響應格式
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
                },
                "error": {
                    "code": str,
                    "message": str
                } (僅錯誤時)
            }
        """
        try:
            # 參數驗證
            validation_error = self._validate_parameters(
                symbol, case_timestamp, timeframe, max_bars
            )
            if validation_error:
                return validation_error

            # 計算前後根數（以T為中心，均分max_bars）
            bars_before = max_bars // 2
            bars_after = max_bars - bars_before

            logger.info(
                f"Fetching chart data: {symbol}/{timeframe}, "
                f"T={case_timestamp}, max_bars={max_bars}"
            )

            # 從storage讀取數據
            result = self.storage_service.read_klines_around_timestamp(
                symbol=symbol,
                timeframe=timeframe,
                center_timestamp=case_timestamp,
                lookback=bars_before,
                forward=bars_after
            )

            # 檢查讀取是否成功
            if not result.get("success", False):
                error_message = result.get("message", "Failed to read klines")
                logger.error(f"Failed to read klines: {error_message}")
                return {
                    "success": False,
                    "error": {
                        "code": "DATA_NOT_FOUND",
                        "message": f"K線數據不存在或讀取失敗: {error_message}"
                    }
                }

            # 檢查是否有數據
            klines_data = result.get("data", [])
            if len(klines_data) == 0:
                logger.warning(f"No klines data found for {symbol}/{timeframe} at T={case_timestamp}")
                return {
                    "success": False,
                    "error": {
                        "code": "DATA_NOT_FOUND",
                        "message": f"未找到 {symbol}/{timeframe} 在時間點 {case_timestamp} 附近的K線數據"
                    }
                }

            center_index = result.get("center_index", -1)

            # 格式化響應數據
            response_data = self._format_response(
                case_timestamp=case_timestamp,
                klines=klines_data,
                center_index=center_index,
                symbol=symbol,
                timeframe=timeframe
            )

            logger.info(
                f"Successfully fetched {len(klines_data)} klines for {symbol}/{timeframe}, "
                f"center_index={center_index}"
            )

            return {
                "success": True,
                "data": response_data
            }

        except Exception as e:
            error_msg = f"Exception in get_chart_data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": {
                    "code": "SYSTEM_ERROR",
                    "message": f"系統錯誤: {str(e)}"
                }
            }


    def _validate_parameters(self,
                            symbol: str,
                            case_timestamp: int,
                            timeframe: str,
                            max_bars: int) -> Optional[Dict]:
        """
        驗證請求參數

        Args:
            symbol: 交易對
            case_timestamp: 案例時間戳
            timeframe: 時間框架
            max_bars: 最大根數

        Returns:
            Dict: 錯誤響應（如果驗證失敗），否則None
        """
        # 驗證symbol
        if not symbol or not isinstance(symbol, str):
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_INVALID_SYMBOL",
                    "message": "Symbol必須是非空字符串"
                }
            }

        # 驗證timestamp
        if not isinstance(case_timestamp, int) or case_timestamp <= 0:
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_INVALID_TIMESTAMP",
                    "message": "case_timestamp必須是正整數（Unix秒）"
                }
            }

        # 驗證timeframe
        valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '12h', '1d']
        if timeframe not in valid_timeframes:
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_INVALID_TIMEFRAME",
                    "message": f"不支援的timeframe: {timeframe}。支援: {', '.join(valid_timeframes)}"
                }
            }

        # 驗證max_bars
        if not isinstance(max_bars, int) or max_bars <= 0:
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_INVALID_MAX_BARS",
                    "message": "max_bars必須是正整數"
                }
            }

        if max_bars > 1000:
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_TIME_RANGE_TOO_LARGE",
                    "message": "max_bars不能超過1000"
                }
            }

        return None


    def _format_response(self,
                        case_timestamp: int,
                        klines: List[Dict],
                        center_index: int,
                        symbol: str,
                        timeframe: str) -> Dict:
        """
        格式化響應數據（符合API規範）

        Args:
            case_timestamp: 案例時間戳
            klines: K線數據列表
            center_index: T在陣列中的位置
            symbol: 交易對
            timeframe: 時間框架

        Returns:
            Dict: 格式化的響應數據
        """
        # 確保klines中的數據類型正確（float32 -> float，避免JSON序列化問題）
        formatted_klines = []
        for kline in klines:
            formatted_kline = {
                "timestamp": int(kline["timestamp"]),
                "open": float(kline["open"]),
                "high": float(kline["high"]),
                "low": float(kline["low"]),
                "close": float(kline["close"]),
                "volume": float(kline["volume"]),
                "taker_buy_volume": float(kline["taker_buy_volume"]),
                "taker_ratio": float(kline["taker_ratio"])
            }

            # 可選欄位
            if "quote_volume" in kline and kline["quote_volume"] is not None:
                formatted_kline["quote_volume"] = float(kline["quote_volume"])

            if "number_of_trades" in kline and kline["number_of_trades"] is not None:
                formatted_kline["number_of_trades"] = int(kline["number_of_trades"])

            formatted_klines.append(formatted_kline)

        # 計算時間範圍
        time_range_start = formatted_klines[0]["timestamp"] if len(formatted_klines) > 0 else case_timestamp
        time_range_end = formatted_klines[-1]["timestamp"] if len(formatted_klines) > 0 else case_timestamp

        return {
            "case_timestamp": case_timestamp,
            "klines": formatted_klines,
            "center_index": center_index,
            "metadata": {
                "symbol": symbol,
                "timeframe": timeframe,
                "total_bars": len(formatted_klines),
                "time_range": {
                    "start": time_range_start,
                    "end": time_range_end
                }
            }
        }


# 全局實例（單例模式）
_chart_data_service_instance = None


def get_chart_data_service() -> ChartDataService:
    """
    獲取ChartDataService全局實例（單例模式）

    Returns:
        ChartDataService: 服務實例
    """
    global _chart_data_service_instance

    if _chart_data_service_instance is None:
        _chart_data_service_instance = ChartDataService()

    return _chart_data_service_instance
