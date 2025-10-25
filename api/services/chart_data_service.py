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
from api.services.kline_data_service import (
    KlineDataService,
    get_kline_data_service
)
from momentum.DataExtraction.kline_storage import KlineStorageManager
from api.core.logging import get_logger

logger = get_logger("api.chart_data_service")


class ChartDataService:
    """
    圖表數據服務

    為前端圖表提供K線數據，支援以案例時間點T為中心的數據裁切
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        kline_data_service: Optional[KlineDataService] = None
    ):
        """
        初始化圖表數據服務

        Args:
            cache_dir: K線緩存目錄路徑
        """
        self.storage_service = KlineStorageService(cache_dir=cache_dir)
        self.kline_data_service = kline_data_service or get_kline_data_service(cache_dir=cache_dir)
        logger.info(f"ChartDataService initialized")


    def get_chart_data(self,
                      symbol: str,
                      case_timestamp: int,
                      timeframe: str,
                      max_bars: int = 200,
                      case_timeframe: Optional[str] = None) -> Dict:
        """
        獲取圖表數據

        **新邏輯（如果提供case_timeframe）**：
        - case_timestamp = TO (Target Open)
        - K線範圍：TO往前lookback + 案例區間 + TC往後forward
        - 返回 to_index, tc_index, case_bars

        **舊邏輯（不提供case_timeframe，向後兼容）**：
        - case_timestamp 為中心點
        - 返回 center_index

        Args:
            symbol: 交易對（如ETHUSDT）
            case_timestamp: 案例時間點T/TO（Unix秒）
            timeframe: 時間框架（查看用，如1h, 4h）
            max_bars: 最大返回根數（預設200）
            case_timeframe: 案例時間框架（如"12h"），如提供則使用新邏輯

        Returns:
            Dict: 符合API規範的響應格式
            {
                "success": bool,
                "data": {
                    "case_timestamp": int,
                    "klines": List[Dict],
                    "center_index": int (舊) 或
                    "to_index": int, "tc_index": int, "case_bars": int (新),
                    "metadata": {...}
                },
                "error": {...} (僅錯誤時)
            }
        """
        try:
            # 參數驗證
            validation_error = self._validate_parameters(
                symbol, case_timestamp, timeframe, max_bars
            )
            if validation_error:
                return validation_error

            # 計算前後根數
            if case_timeframe:
                # 新邏輯：預設往前100根，往後48根（可被max_bars覆蓋）
                bars_before = 100
                bars_after = 48
            else:
                # 舊邏輯：以T為中心，均分max_bars
                bars_before = max_bars // 2
                bars_after = max_bars - bars_before

            logger.info(
                f"Fetching chart data: {symbol}/{timeframe}, "
                f"TO={case_timestamp}, case_tf={case_timeframe}, max_bars={max_bars}"
            )

            # 確保緩存覆蓋需求區間
            self._ensure_data_coverage(
                symbol=symbol,
                case_timestamp=case_timestamp,
                timeframe=timeframe,
                lookback=bars_before,
                forward=bars_after,
                case_timeframe=case_timeframe
            )

            # 從storage讀取數據
            result = self.storage_service.read_klines_around_timestamp(
                symbol=symbol,
                timeframe=timeframe,
                center_timestamp=case_timestamp,
                lookback=bars_before,
                forward=bars_after,
                case_timeframe=case_timeframe
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

            # 獲取index信息（新/舊邏輯）
            if case_timeframe and "to_index" in result:
                # 新邏輯
                to_index = result.get("to_index", -1)
                tc_index = result.get("tc_index", -1)
                case_bars = result.get("case_bars", 1)
                resolved_case_timestamp = result.get("to_timestamp")
                resolved_tc_timestamp = result.get("tc_timestamp")

                expected_total = bars_before + case_bars + bars_after
                actual_total = len(klines_data)

                if actual_total < expected_total or to_index != bars_before:
                    logger.warning(
                        "Incomplete kline coverage for %s/%s: expected %d bars (lookback=%d, case=%d, forward=%d) "
                        "but got %d bars with TO index %d",
                        symbol,
                        timeframe,
                        expected_total,
                        bars_before,
                        case_bars,
                        bars_after,
                        actual_total,
                        to_index
                    )
                    return {
                        "success": False,
                        "error": {
                            "code": "DATA_INCOMPLETE",
                            "message": (
                                f"{symbol}/{timeframe} 的緩存不足，無法提供案例所需的K線範圍。"
                                "請先下載缺失的歷史資料後再重試。"
                            )
                        }
                    }

                # 格式化響應數據（新邏輯）
                response_data = self._format_response(
                    case_timestamp=case_timestamp,
                    klines=klines_data,
                    symbol=symbol,
                    timeframe=timeframe,
                    to_index=to_index,
                    tc_index=tc_index,
                    case_bars=case_bars,
                    case_timeframe=case_timeframe,
                    resolved_case_timestamp=resolved_case_timestamp,
                    resolved_tc_timestamp=resolved_tc_timestamp
                )

                logger.info(
                    f"Successfully fetched {len(klines_data)} klines for {symbol}/{timeframe} "
                    f"(case_tf={case_timeframe}), TO at {to_index}, TC at {tc_index}"
                )
            else:
                # 舊邏輯
                center_index = result.get("center_index", -1)

                # 格式化響應數據（舊邏輯）
                response_data = self._format_response(
                    case_timestamp=case_timestamp,
                    klines=klines_data,
                    symbol=symbol,
                    timeframe=timeframe,
                    center_index=center_index
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


    def _ensure_data_coverage(
        self,
        symbol: str,
        case_timestamp: int,
        timeframe: str,
        lookback: int,
        forward: int,
        case_timeframe: Optional[str]
    ) -> None:
        """確保指定案例時間點附近的K線數據已下載/緩存。"""
        if self.kline_data_service is None:
            return

        try:
            timeframe_seconds = KlineStorageManager.TIMEFRAME_SECONDS.get(timeframe)
            if timeframe_seconds is None:
                logger.debug(f"Timeframe {timeframe} not managed for automatic download")
                return

            case_bars = 1
            if case_timeframe:
                case_seconds = KlineStorageManager.TIMEFRAME_SECONDS.get(case_timeframe)
                if case_seconds:
                    case_bars = max(1, case_seconds // timeframe_seconds)

            start_ts = case_timestamp - lookback * timeframe_seconds
            # 包含案例區間與forward範圍
            end_ts = case_timestamp + ((case_bars - 1) + forward) * timeframe_seconds

            # 避免無效時間範圍
            if end_ts <= start_ts:
                end_ts = start_ts + timeframe_seconds

            start_dt = datetime.utcfromtimestamp(max(start_ts, 0))
            end_dt = datetime.utcfromtimestamp(max(end_ts, start_ts + timeframe_seconds))

            # 避免請求未來資料
            now_utc = datetime.utcnow()
            if end_dt > now_utc:
                end_dt = now_utc

            if end_dt <= start_dt:
                logger.debug(
                    f"Skip ensure coverage for {symbol}/{timeframe}: invalid time window {start_dt} - {end_dt}"
                )
                return

            self.kline_data_service.get_kline_data(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_dt,
                end_time=end_dt,
                validate_integrity=False
            )

        except Exception as e:
            logger.warning(
                f"Failed to ensure data coverage for {symbol}/{timeframe} at {case_timestamp}: {e}"
            )


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
                        symbol: str,
                        timeframe: str,
                        center_index: Optional[int] = None,
                        to_index: Optional[int] = None,
                        tc_index: Optional[int] = None,
                        case_bars: Optional[int] = None,
                        case_timeframe: Optional[str] = None,
                        resolved_case_timestamp: Optional[int] = None,
                        resolved_tc_timestamp: Optional[int] = None) -> Dict:
        """
        格式化響應數據（符合API規範）

        支持兩種模式：
        1. 舊邏輯：提供 center_index
        2. 新邏輯：提供 to_index, tc_index, case_bars, case_timeframe

        Args:
            case_timestamp: 案例時間戳
            klines: K線數據列表
            symbol: 交易對
            timeframe: 時間框架
            center_index: T在陣列中的位置（舊邏輯）
            to_index: TO在陣列中的位置（新邏輯）
            tc_index: TC在陣列中的位置（新邏輯）
            case_bars: 案例K線根數（新邏輯）
            case_timeframe: 案例時間框架（新邏輯）

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

        # 基礎響應
        response = {
            "case_timestamp": case_timestamp,
            "klines": formatted_klines,
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

        # 添加index信息（新/舊邏輯）
        if to_index is not None and tc_index is not None:
            # 新邏輯
            response["to_index"] = to_index
            response["tc_index"] = tc_index
            response["case_bars"] = case_bars
            response["metadata"]["case_timeframe"] = case_timeframe
            if resolved_case_timestamp is not None:
                response["aligned_case_timestamp"] = int(resolved_case_timestamp)
            if resolved_tc_timestamp is not None:
                response["aligned_tc_timestamp"] = int(resolved_tc_timestamp)
        else:
            # 舊邏輯
            response["center_index"] = center_index if center_index is not None else -1

        return response


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
