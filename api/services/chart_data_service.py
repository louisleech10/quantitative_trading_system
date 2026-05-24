"""
圖表數據服務 - 為前端圖表提供K線數據

功能：
1. 獲取以T點為中心的K線數據（用於圖表顯示）
2. 數據格式轉換（HDF5 → JSON）
3. center_index計算（T在陣列中的位置）
4. **指標計算**（可選，使用 IndicatorEngine 確保與策略計算一致）
5. 錯誤處理和日誌記錄

設計原則：
- 基於kline_storage_service構建
- 符合API_SPECIFICATION_CHART.md規範
- 完整錯誤處理
- 適當日誌記錄
- 前端不計算指標，全部由後端負責（架構一致性）
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
import numpy as np
import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Any

from momentum.factories import (
    create_binance_provider,
    create_indicator_engine,
    create_kline_download_service,
    create_kline_storage_manager,
)
from momentum.FeatureEngineering.atomic.warmup_lookup import (
    get_warmup_bars,
    get_warmup_factor,
)
from api.core.logging import get_logger

logger = get_logger("api.chart_data_service")


class ChartDataService:
    """
    圖表數據服務

    為前端圖表提供K線數據，支援以案例時間點T為中心的數據裁切。
    支援可選的指標計算（使用 IndicatorEngine 確保與策略計算一致）。
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        kline_data_service: Optional[Any] = None
    ):
        """
        初始化圖表數據服務

        Args:
            cache_dir: K線緩存目錄路徑
        """
        self.storage_manager = create_kline_storage_manager(cache_dir=cache_dir)
        self.download_service = create_kline_download_service(
            storage_manager=self.storage_manager
        )
        try:
            self.download_service.registry.register(
                "binance",
                create_binance_provider(),
            )
        except Exception:
            logger.debug("Binance provider already registered", exc_info=True)

        self.kline_data_service = kline_data_service
        self.indicator_engine = create_indicator_engine()  # 新增：用於指標計算
        logger.info(f"ChartDataService initialized with IndicatorEngine")


    def get_chart_data(self,
                      symbol: str,
                      case_timestamp: int,
                      timeframe: str,
                      max_bars: int = 200,
                      case_timeframe: Optional[str] = None,
                      lookback_bars: Optional[int] = None,
                      forward_bars: Optional[int] = None,
                      indicator_config: Optional[Dict[str, Any]] = None) -> Dict:
        """
        獲取圖表數據（可含指標數據）

        **新邏輯（如果提供case_timeframe）**：
        - case_timestamp = TO (Target Open)
        - K線範圍：TO往前lookback + 案例區間 + TC往後forward
        - 返回 to_index, tc_index, case_bars

        **舊邏輯（不提供case_timeframe，向後兼容）**：
        - case_timestamp 為中心點
        - 返回 center_index
        
        **指標計算（可選）**：
        - 如提供 indicator_config，則使用 IndicatorEngine 計算指標
        - 確保與策略計算使用相同的 warmup 和算法

        Args:
            symbol: 交易對（如ETHUSDT）
            case_timestamp: 案例時間點T/TO（Unix秒）
            timeframe: 時間框架（查看用，如1h, 4h）
            max_bars: 最大返回根數（預設200）
            case_timeframe: 案例時間框架（如"12h"），如提供則使用新邏輯
            lookback_bars: 往前K線根數（預設100，僅當case_timeframe提供時使用）
            forward_bars: 往後K線根數（預設48，僅當case_timeframe提供時使用）
            indicator_config: 指標配置（可選）
                {
                    "indicator_type": "ema",           # 指標類型
                    "data_source": "close",            # 數據源
                    "strategy_logic": "three_line",   # 策略邏輯
                    "params": {                        # 指標參數
                        "short_period": 5,
                        "mid_period": 20,
                        "long_period": 60
                    }
                }

        Returns:
            Dict: 符合API規範的響應格式
            {
                "success": bool,
                "data": {
                    "case_timestamp": int,
                    "klines": List[Dict],
                    "center_index": int (舊) 或
                    "to_index": int, "tc_index": int, "case_bars": int (新),
                    "indicators": {...} (可選，當提供 indicator_config 時),
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
                # 新邏輯：使用提供的lookback_bars和forward_bars，或使用預設值
                bars_before = lookback_bars if lookback_bars is not None else 100
                bars_after = forward_bars if forward_bars is not None else 48
            else:
                # 舊邏輯：以T為中心，均分max_bars
                bars_before = max_bars // 2
                bars_after = max_bars - bars_before

            logger.info(
                f"Fetching chart data: {symbol}/{timeframe}, "
                f"TO={case_timestamp}, case_tf={case_timeframe}, max_bars={max_bars}, "
                f"lookback={bars_before}, forward={bars_after}"
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
            result = self._read_klines_around_timestamp(
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

                # 檢查 lookback 是否足夠（這是必要的）
                if to_index < bars_before:
                    logger.warning(
                        "Insufficient lookback for %s/%s: expected %d lookback bars but TO is at index %d",
                        symbol,
                        timeframe,
                        bars_before,
                        to_index
                    )
                    return {
                        "success": False,
                        "error": {
                            "code": "DATA_INCOMPLETE",
                            "message": (
                                f"{symbol}/{timeframe} 的緩存不足，lookback 資料不完整。"
                                "請先下載缺失的歷史資料後再重試。"
                            )
                        }
                    }
                
                # Forward 資料不足時只記錄警告，不阻止顯示
                if actual_total < expected_total:
                    logger.info(
                        "Partial forward data for %s/%s: expected %d bars (lookback=%d, case=%d, forward=%d) "
                        "but got %d bars with TO index %d (forward available: %d)",
                        symbol,
                        timeframe,
                        expected_total,
                        bars_before,
                        case_bars,
                        bars_after,
                        actual_total,
                        to_index,
                        actual_total - to_index - case_bars
                    )

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

            # === 可選：計算指標（含 warmup 數據獲取）===
            if indicator_config:
                try:
                    # 計算需要的 warmup 數據量 (EMA factor from warmup_table.yaml)
                    params = indicator_config.get("params", {})
                    max_period = max(
                        params.get("short_period", 0),
                        params.get("mid_period", 0),
                        params.get("long_period", 0)
                    )
                    required_warmup = get_warmup_bars("EMA", max_period)
                    
                    # 獲取包含 warmup 的完整數據進行計算
                    indicators_result = self._calculate_indicators_with_warmup(
                        symbol=symbol,
                        timeframe=timeframe,
                        display_klines=klines_data,
                        indicator_config=indicator_config,
                        required_warmup=required_warmup
                    )
                    if indicators_result:
                        response_data["indicators"] = indicators_result
                        logger.info(
                            f"Calculated indicators with warmup: {list(indicators_result.keys())}"
                        )
                except Exception as ind_err:
                    # 指標計算失敗不應阻止返回 K 線數據
                    logger.warning(
                        f"Failed to calculate indicators: {ind_err}", 
                        exc_info=True
                    )
                    response_data["indicator_error"] = str(ind_err)

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
        """
        確保指定案例時間點附近的K線數據已下載/緩存。
        
        智能下載：只下載缺失的部分，避開已有數據以防止無效的重複下載。
        """
        try:
            timeframe_seconds = self.storage_manager.TIMEFRAME_SECONDS.get(timeframe)
            if timeframe_seconds is None:
                logger.debug(f"Timeframe {timeframe} not managed for automatic download")
                return

            case_bars = 1
            if case_timeframe:
                case_seconds = self.storage_manager.TIMEFRAME_SECONDS.get(case_timeframe)
                if case_seconds:
                    case_bars = max(1, case_seconds // timeframe_seconds)

            # 計算需要的完整時間範圍
            required_start_ts = case_timestamp - lookback * timeframe_seconds
            # 包含案例區間與forward範圍
            required_end_ts = case_timestamp + ((case_bars - 1) + forward) * timeframe_seconds

            # 避免請求未來資料
            now_utc = datetime.utcnow()
            required_end_dt = datetime.utcfromtimestamp(max(required_end_ts, required_start_ts + timeframe_seconds))
            if required_end_dt > now_utc:
                required_end_dt = now_utc
                required_end_ts = int(required_end_dt.timestamp())

            # 檢查現有數據範圍
            try:
                # 直接從底層 storage manager 讀取 metadata
                metadata = self.storage_manager.get_metadata(symbol, timeframe)
                existing_start = metadata.get('time_range_start') if metadata else None
                existing_end = metadata.get('time_range_end') if metadata else None
                
                logger.info(
                    f"DEBUG metadata: existing_start={existing_start}, existing_end={existing_end}, "
                    f"required_start={required_start_ts}, required_end={required_end_ts}"
                )
            except Exception as meta_err:
                logger.warning(f"Failed to get metadata for {symbol}/{timeframe}: {meta_err}", exc_info=True)
                existing_start = None
                existing_end = None
            
            if existing_start and existing_end:
                logger.debug(
                    f"Existing data: {datetime.utcfromtimestamp(existing_start)} to {datetime.utcfromtimestamp(existing_end)}, "
                    f"Required: {datetime.utcfromtimestamp(required_start_ts)} to {datetime.utcfromtimestamp(required_end_ts)}"
                )
                
                # 計算需要下載的缺口
                gaps = []
                
                # 缺口1: 需要的開始時間 < 現有開始時間（往前補）
                if required_start_ts < existing_start:
                    gap_start = datetime.utcfromtimestamp(max(required_start_ts, 0))
                    gap_end = datetime.utcfromtimestamp(existing_start)
                    gaps.append(("gap_before", gap_start, gap_end))
                
                # 缺口2: 需要的結束時間 > 現有結束時間（往後補）
                if required_end_ts > existing_end:
                    # CRITICAL: 從現有數據的下一根K線開始，避免重複下載
                    next_timestamp = existing_end + timeframe_seconds
                    gap_start = datetime.utcfromtimestamp(next_timestamp)
                    gap_end = datetime.utcfromtimestamp(required_end_ts)
                    
                    logger.info(
                        f"DEBUG gap_after: existing_end={existing_end} ({datetime.utcfromtimestamp(existing_end)}), "
                        f"next_timestamp={next_timestamp} ({gap_start}), "
                        f"gap_start={gap_start}, gap_end={gap_end}"
                    )
                    
                    # 確保 gap_start 不超過 now_utc
                    if gap_start <= now_utc:
                        gaps.append(("gap_after", gap_start, min(gap_end, now_utc)))
                
                # 下載所有缺口
                for gap_type, start_dt, end_dt in gaps:
                    if end_dt <= start_dt:
                        continue
                        
                    logger.info(f"Downloading {gap_type}: {start_dt} to {end_dt}")
                    self._download_klines_range(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_dt=start_dt,
                        end_dt=end_dt,
                    )
            else:
                # 沒有現有數據，下載完整範圍
                start_dt = datetime.utcfromtimestamp(max(required_start_ts, 0))
                end_dt = datetime.utcfromtimestamp(required_end_ts)
                
                if end_dt > now_utc:
                    end_dt = now_utc
                
                if end_dt > start_dt:
                    logger.info(f"Downloading full range: {start_dt} to {end_dt}")
                    self._download_klines_range(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_dt=start_dt,
                        end_dt=end_dt,
                    )

        except Exception as e:
            logger.warning(
                f"Failed to ensure data coverage for {symbol}/{timeframe} at {case_timestamp}: {e}"
            )

    def _download_klines_range(
        self,
        symbol: str,
        timeframe: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> None:
        """Download missing klines via injected service or direct download."""
        if self.kline_data_service is not None:
            self.kline_data_service.get_kline_data(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_dt,
                end_time=end_dt,
                validate_integrity=False,
            )
            return

        try:
            self.download_service.download_klines(
                source="binance",
                symbol=symbol,
                start_time=start_dt,
                end_time=end_dt,
                timeframe=timeframe,
                save_to_storage=True,
            )
        except Exception as e:
            logger.warning(
                f"Failed to download klines for {symbol}/{timeframe}: {e}",
                exc_info=True,
            )

    def _read_klines_around_timestamp(
        self,
        symbol: str,
        timeframe: str,
        center_timestamp: int,
        lookback: int,
        forward: int,
        case_timeframe: Optional[str],
    ) -> Dict[str, Any]:
        """Read klines around timestamp and return chart_data style payload."""
        try:
            df = self.storage_manager.read_klines_around_timestamp(
                symbol=symbol,
                timeframe=timeframe,
                center_timestamp=center_timestamp,
                lookback=lookback,
                forward=forward,
                case_timeframe=case_timeframe,
            )
            if df is None or len(df) == 0:
                return {
                    "success": False,
                    "data": [],
                    "message": "No klines data found",
                }

            result = {
                "success": True,
                "data": df.to_dict("records"),
            }
            if case_timeframe:
                result["to_index"] = df.attrs.get("to_index")
                result["tc_index"] = df.attrs.get("tc_index")
                result["case_bars"] = df.attrs.get("case_bars")
                result["to_timestamp"] = df.attrs.get("to_timestamp")
                result["tc_timestamp"] = df.attrs.get("tc_timestamp")
            else:
                result["center_index"] = df.attrs.get("center_index")
            return result
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": str(e),
            }

    def _read_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: int,
        end_time: int,
    ) -> Dict[str, Any]:
        """Read klines in range and return chart_data style payload."""
        try:
            df = self.storage_manager.read_klines(
                symbol,
                timeframe,
                start_time=start_time,
                end_time=end_time,
                validate_continuity=False,
            )
            if df is None or len(df) == 0:
                return {
                    "success": False,
                    "data": [],
                    "message": "No klines data found",
                }
            return {
                "success": True,
                "data": df.to_dict("records"),
            }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": str(e),
            }


    def _calculate_indicators_with_warmup(
        self,
        symbol: str,
        timeframe: str,
        display_klines: List[Dict],
        indicator_config: Dict[str, Any],
        required_warmup: int
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        計算指標（含 warmup 數據獲取）
        
        為確保 EMA 計算精度，先獲取額外的 warmup 數據進行計算，
        然後只返回 display_klines 範圍內的 EMA 值。
        
        Args:
            symbol: 交易對
            timeframe: 時間框架
            display_klines: 需要顯示的 K 線數據（API 返回給前端的）
            indicator_config: 指標配置
            required_warmup: 需要的 warmup 數據量（4.5 × max_period）
            
        Returns:
            Dict: 指標結果，只包含 display_klines 範圍內的數據
        """
        if not display_klines:
            return None
            
        try:
            # 獲取 display_klines 的時間範圍
            first_display_ts = display_klines[0]['timestamp']
            last_display_ts = display_klines[-1]['timestamp']
            display_timestamps = set(kline['timestamp'] for kline in display_klines)
            
            # 計算 timeframe 對應的秒數
            timeframe_seconds = self.storage_manager.TIMEFRAME_SECONDS.get(timeframe)
            if not timeframe_seconds:
                logger.warning(f"Unknown timeframe: {timeframe}, falling back to simple calculation")
                return self._calculate_indicators_for_chart(display_klines, indicator_config)
            
            # 計算需要獲取的更早的開始時間（含 warmup）
            warmup_start_ts = first_display_ts - (required_warmup * timeframe_seconds)
            
            logger.info(
                f"Fetching warmup data: need {required_warmup} extra bars before {first_display_ts}, "
                f"warmup_start={warmup_start_ts}"
            )
            
            # 從 storage 讀取包含 warmup 的完整數據
            warmup_result = self._read_klines(
                symbol=symbol,
                timeframe=timeframe,
                start_time=warmup_start_ts,
                end_time=last_display_ts
            )
            
            if not warmup_result.get("success"):
                logger.warning(
                    f"Failed to read warmup data: {warmup_result.get('message')}, "
                    f"falling back to simple calculation"
                )
                return self._calculate_indicators_for_chart(display_klines, indicator_config)
            
            warmup_klines = warmup_result.get("data", [])
            
            if len(warmup_klines) < len(display_klines):
                logger.warning(
                    f"Warmup data shorter than display data: {len(warmup_klines)} < {len(display_klines)}, "
                    f"falling back to simple calculation"
                )
                return self._calculate_indicators_for_chart(display_klines, indicator_config)
            
            logger.info(
                f"Got {len(warmup_klines)} klines with warmup (display: {len(display_klines)}), "
                f"extra warmup bars: {len(warmup_klines) - len(display_klines)}"
            )
            
            # 使用完整數據（含 warmup）計算指標
            full_indicators = self._calculate_indicators_for_chart(warmup_klines, indicator_config)
            
            if not full_indicators:
                return None
            
            # 只保留 display_klines 範圍內的指標值
            trimmed_indicators = {}
            for indicator_name, indicator_data in full_indicators.items():
                trimmed_data = [
                    point for point in indicator_data 
                    if point['time'] in display_timestamps
                ]
                trimmed_indicators[indicator_name] = trimmed_data
                
            logger.info(
                f"Trimmed indicators to display range: "
                f"{len(list(full_indicators.values())[0])} -> {len(list(trimmed_indicators.values())[0])} points"
            )
            
            return trimmed_indicators
            
        except Exception as e:
            logger.error(f"Failed to calculate indicators with warmup: {e}", exc_info=True)
            # 回退到簡單計算
            return self._calculate_indicators_for_chart(display_klines, indicator_config)


    def _calculate_indicators_for_chart(
        self,
        klines: List[Dict],
        indicator_config: Dict[str, Any]
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        為圖表計算指標數據

        使用 IndicatorEngine 計算指標，確保與策略計算使用相同算法和 warmup。
        
        Args:
            klines: K線數據列表（已格式化的 Dict 列表）
            indicator_config: 指標配置
                {
                    "indicator_type": "ema",
                    "data_source": "close",
                    "strategy_logic": "three_line",
                    "params": {"short_period": 5, "mid_period": 20, "long_period": 60}
                }

        Returns:
            Dict: 指標結果，格式為
            {
                "ema_short": [{"time": 1704067200, "value": 50000.0}, ...],
                "ema_mid": [{"time": 1704067200, "value": 49500.0}, ...],
                "ema_long": [{"time": 1704067200, "value": 49000.0}, ...]
            }
            如果計算失敗則返回 None
        """
        if not klines or not indicator_config:
            return None

        try:
            # 提取配置
            indicator_type = indicator_config.get("indicator_type", "ema")
            data_source = indicator_config.get("data_source", "close")
            strategy_logic = indicator_config.get("strategy_logic", "three_line")
            params = indicator_config.get("params", {})

            # 根據策略邏輯確定需要計算的指標
            if strategy_logic == "three_line":
                param_to_output = {
                    "short_period": "ema_short",
                    "mid_period": "ema_mid",
                    "long_period": "ema_long"
                }
            elif strategy_logic == "short_long_cross":
                param_to_output = {
                    "short_period": "ema_short",
                    "long_period": "ema_long"
                }
            elif strategy_logic == "mid_long_cross":
                param_to_output = {
                    "mid_period": "ema_mid",
                    "long_period": "ema_long"
                }
            else:
                logger.warning(f"Unsupported strategy_logic: {strategy_logic}")
                return None

            # 將 klines 轉換為 DataFrame
            kline_df = pd.DataFrame(klines)
            
            # 確保必要的欄位存在
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_columns if col not in kline_df.columns]
            if missing_cols:
                logger.error(f"Missing columns in klines: {missing_cols}")
                return None

            # 計算最大週期（用於 warmup 檢查和日誌）
            max_period = 0
            for param_name in param_to_output.keys():
                period = params.get(param_name, 0)
                max_period = max(max_period, period)

            required_warmup = get_warmup_bars("EMA", max_period)
            if len(kline_df) < required_warmup:
                logger.warning(
                    f"Insufficient data for indicator calculation: "
                    f"need {required_warmup} bars (max_period={max_period} × {get_warmup_factor('EMA'):.2f}), "
                    f"have {len(kline_df)} bars. Indicators may be less accurate."
                )
                # 注意：不返回 None，仍計算（IndicatorEngine 會處理）

            # 構建指標配置
            indicator_configs = []
            for param_name, output_name in param_to_output.items():
                period = params.get(param_name)
                if period is None or period <= 0:
                    logger.warning(f"Invalid or missing {param_name}: {period}")
                    continue

                indicator_configs.append({
                    "indicator": indicator_type,
                    "data_source": data_source,
                    "params": {"period": period},
                    "output_name": output_name,
                })

            if not indicator_configs:
                logger.warning("No valid indicator configs to calculate")
                return None

            # 使用 IndicatorEngine 計算
            indicator_df = self.indicator_engine.calculate_indicators_from_dataframe(
                kline_df=kline_df,
                configs=indicator_configs,
            )

            # 將結果轉換為前端需要的格式
            # 格式：{"ema_short": [{"time": ts, "value": val}, ...], ...}
            results = {}
            timestamps = kline_df['timestamp'].tolist()

            for output_name in param_to_output.values():
                if output_name not in indicator_df.columns:
                    continue

                values = indicator_df[output_name].tolist()
                results[output_name] = [
                    {"time": int(ts), "value": float(val) if not np.isnan(val) else None}
                    for ts, val in zip(timestamps, values)
                ]

            logger.info(
                f"Calculated {len(results)} indicators using IndicatorEngine "
                f"(data_source={data_source}, max_period={max_period})"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to calculate indicators: {e}", exc_info=True)
            return None


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
