"""
圖表信號計算服務層 - Ultra Think 初版

提供圖表信號箭頭系統的服務層封裝 (Task 3.4)。
根據策略配置計算每根K線的信號狀態,用於在圖表上渲染藍色箭頭標記。

Ultra Think 記錄:
- 步驟 1: 初版代碼 - 基本服務層架構和核心邏輯
- 步驟 2: 審查優化 - (待執行)
- 步驟 3: 最終優化 - (待執行)

設計原則:
1. 複用 Task 3.1 的 IndicatorEngine 計算指標
2. 向量化策略評估,避免 Python 循環
3. 智能採樣限制標記數量 (最多500個)
4. 統一錯誤處理和日誌記錄

Author: Claude (Phase 3.3+3.4)
Date: 2025-11-01
"""

import logging
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators import IndicatorEngine
from api.core.config import settings
from api.models.strategy_test_models import (
    ChartSignalCalculationRequest,
    ChartSignalCalculationResponse,
    SignalPoint
)


class ChartSignalService:
    """
    圖表信號計算服務 (全局單例)

    提供圖表信號箭頭的服務層接口,整合:
    - KlineStorageManager (讀取K線數據)
    - IndicatorEngine (計算指標)
    - 向量化策略評估邏輯

    核心方法:
    - calculate_chart_signals: 計算圖表信號點
    - _evaluate_strategy_logic: 評估策略邏輯(向量化)
    - _sample_signals: 智能採樣限制標記數量
    """

    _instance = None

    def __new__(cls):
        """單例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化服務(僅執行一次)"""
        if self._initialized:
            return

        # 依賴注入
        self.kline_storage = KlineStorageManager(cache_dir=str(settings.kline_cache_dir))
        self.indicator_engine = IndicatorEngine()

        self.logger = logging.getLogger(__name__)
        self.logger.info("ChartSignalService initialized")

        # 配置常量
        self.MAX_SIGNAL_POINTS = None  # 無上限，返回完整信號列表

        self._initialized = True

    async def calculate_chart_signals(
        self,
        request: ChartSignalCalculationRequest
    ) -> ChartSignalCalculationResponse:
        """
        計算圖表信號點

        主服務方法,執行完整的圖表信號計算流程。

        流程:
        1. 從 HDF5 讀取 K線數據
        2. 調用 IndicatorEngine 計算指標
        3. 向量化評估每根K線是否符合策略
        4. 生成 SignalPoint 列表
        5. 若超過500個,進行智能採樣

        Args:
            request: 圖表信號計算請求

        Returns:
            ChartSignalCalculationResponse

        Raises:
            HTTPException:
                - 400: 參數驗證失敗
                - 404: K線數據不存在
                - 500: 內部服務錯誤

        Example:
            >>> service = ChartSignalService()
            >>> request = ChartSignalCalculationRequest(
            ...     symbol="BTCUSDT",
            ...     timeframe="1h",
            ...     start_time=1704067200000,
            ...     end_time=1704153600000,
            ...     strategy_config=StrategyConfig(...)
            ... )
            >>> result = await service.calculate_chart_signals(request)
            >>> print(len(result.signal_points))
            45
        """
        start_time_calc = time.time()

        try:
            # 1. 驗證請求
            self._validate_request(request)

            # 2. 計算暖機期需求並擴展時間範圍
            strategy_logic = request.strategy_config.strategy_logic
            params = request.strategy_config.params
            
            # 計算最大 EMA 週期
            max_period = 0
            if strategy_logic == "three_line":
                max_period = max(
                    params.get("short_period", 0),
                    params.get("mid_period", 0),
                    params.get("long_period", 0)
                )
            elif strategy_logic == "short_long_cross":
                max_period = max(
                    params.get("short_period", 0),
                    params.get("long_period", 0)
                )
            elif strategy_logic == "mid_long_cross":
                max_period = max(
                    params.get("mid_period", 0),
                    params.get("long_period", 0)
                )
            
            # 計算暖機期（4.5× 最大週期，確保 99.5% 精度）
            WARMUP_MULTIPLIER = 4.5
            warmup_bars = int(max_period * WARMUP_MULTIPLIER)

            # 獲取 timeframe 的秒數
            from momentum.DataExtraction.kline_storage import KlineStorageManager
            timeframe_seconds = KlineStorageManager.TIMEFRAME_SECONDS.get(request.timeframe)
            if timeframe_seconds is None:
                raise ValueError(f"不支援的 timeframe: {request.timeframe}")
            
            # 擴展時間範圍（往前擴展暖機期）
            warmup_ms = warmup_bars * timeframe_seconds * 1000
            extended_start_time = request.start_time - warmup_ms
            
            self.logger.info(
                f"開始計算圖表信號: {request.symbol} {request.timeframe}, "
                f"用戶請求範圍: {request.start_time} ~ {request.end_time}, "
                f"最大EMA週期: {max_period}, 暖機需求: {warmup_bars} 根K線, "
                f"擴展後範圍: {extended_start_time} ~ {request.end_time}"
            )

            # 3. 讀取 K線數據（包含暖機期）
            klines = self._load_klines(
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_time=extended_start_time,
                end_time=request.end_time
            )

            if len(klines) == 0:
                raise ValueError(
                    f"指定時間範圍內無K線數據: {request.symbol} {request.timeframe}"
                )

            total_bars = len(klines)
            self.logger.info(f"成功讀取 {total_bars} 根K線（包含 {warmup_bars} 根暖機數據）")

            # 4. 計算指標（會自動檢查暖機充足性）
            indicator_results = self._calculate_indicators(
                klines=klines,
                strategy_config=request.strategy_config
            )

            # 5. 評估策略邏輯 (向量化)
            signal_mask = self._evaluate_strategy_logic(
                indicator_results=indicator_results,
                strategy_config=request.strategy_config
            )

            # 6. 生成信號點列表（過濾掉暖機期的信號點）
            signal_points = self._generate_signal_points(
                klines=klines,
                indicator_results=indicator_results,
                signal_mask=signal_mask,
                user_start_time=request.start_time  # 只返回用戶請求範圍內的信號
            )

            signal_count = len(signal_points)
            # 計算密度時使用用戶請求範圍內的有效 K 線數量
            valid_range_mask = (klines["timestamp"].to_numpy() * 1000) >= request.start_time
            signal_range_bars = int(valid_range_mask.sum())
            if signal_range_bars <= 0:
                signal_range_bars = max(total_bars - warmup_bars, 1)

            signal_density = signal_count / signal_range_bars
            if signal_density > 1:
                self.logger.warning(
                    "信號密度超過 100%%，已限制於 1.0，signal_count=%d, bars=%d",
                    signal_count,
                    signal_range_bars,
                )
                signal_density = 1.0

            # 7. 智能採樣 (若超過限制)
            is_sampled = False
            if self.MAX_SIGNAL_POINTS is not None and len(signal_points) > self.MAX_SIGNAL_POINTS:
                self.logger.warning(
                    f"信號點數量({len(signal_points)})超過限制({self.MAX_SIGNAL_POINTS}),進行採樣"
                )
                signal_points = self._sample_signals(signal_points, self.MAX_SIGNAL_POINTS)
                is_sampled = True

            # 8. 生成策略名稱
            strategy_name = self._generate_strategy_name(request.strategy_config)

            # 記錄性能
            elapsed_time = time.time() - start_time_calc
            self.logger.info(
                f"圖表信號計算完成: "
                f"total_bars={total_bars} (包含暖機 {warmup_bars}), "
                f"signal_count={signal_count}, "
                f"density={signal_density:.2%}, "
                f"sampled={is_sampled}, "
                f"耗時={elapsed_time:.3f}秒"
            )

            return ChartSignalCalculationResponse(
                signal_points=signal_points,
                total_bars=total_bars,
                signal_count=signal_count,
                signal_density=signal_density,
                is_sampled=is_sampled,
                strategy_name=strategy_name
            )

        except ValueError as e:
            # 參數驗證失敗(400 Bad Request)
            self.logger.error(f"參數驗證失敗: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        except FileNotFoundError as e:
            # 數據不存在(404 Not Found)
            self.logger.error(f"K線數據不存在: {e}")
            raise HTTPException(status_code=404, detail=str(e))

        except Exception as e:
            # 內部錯誤(500 Internal Server Error)
            elapsed_time = time.time() - start_time_calc
            self.logger.error(
                f"圖表信號計算失敗: {e}, 耗時={elapsed_time:.3f}秒",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail=f"內部服務錯誤: {str(e)}"
            )

    def _validate_request(self, request: ChartSignalCalculationRequest):
        """
        驗證請求參數

        Args:
            request: 圖表信號計算請求

        Raises:
            ValueError: 當參數驗證失敗時
        """
        # 檢查時間範圍
        if request.end_time <= request.start_time:
            raise ValueError("end_time 必須大於 start_time")

        # 檢查指標是否已註冊
        available_indicators = self.indicator_engine.list_indicators()
        if request.strategy_config.indicator_type not in available_indicators:
            raise ValueError(
                f"未知的指標類型: {request.strategy_config.indicator_type}. "
                f"可用指標: {', '.join(available_indicators)}"
            )

        # 檢查策略邏輯類型
        supported_logics = ["three_line", "short_long_cross", "mid_long_cross"]
        if request.strategy_config.strategy_logic not in supported_logics:
            raise ValueError(
                f"不支持的策略邏輯: {request.strategy_config.strategy_logic}. "
                f"支持的邏輯: {', '.join(supported_logics)}"
            )

        self.logger.debug("請求驗證通過")

    def _load_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: int,
        end_time: int
    ) -> pd.DataFrame:
        """
        從 HDF5 讀取 K線數據
        
        注意：start_time 和 end_time 應該已經包含暖機期的擴展

        Args:
            symbol: 交易對
            timeframe: 時間週期
            start_time: 開始時間戳(毫秒)
            end_time: 結束時間戳(毫秒)

        Returns:
            K線數據 DataFrame

        Raises:
            FileNotFoundError: K線數據不存在
            ValueError: 數據不連續
        """
        try:
            # 將毫秒轉換為秒
            start_ts_sec = start_time // 1000
            end_ts_sec = end_time // 1000
            
            # 讀取K線數據（允許中間有缺口，避免整體任務被阻擋）
            klines = self.kline_storage.read_klines(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_ts_sec,
                end_time=end_ts_sec,
                validate_continuity=False  # 前端策略測試允許分段資料
            )

            if klines is None or len(klines) == 0:
                raise FileNotFoundError(
                    f"K線數據不存在或為空: {symbol} {timeframe}"
                )

            # 評估實際覆蓋率，若少於預期則記錄警告方便排查
            timeframe_seconds = KlineStorageManager.TIMEFRAME_SECONDS.get(timeframe)
            if timeframe_seconds:
                expected_bars = int((end_ts_sec - start_ts_sec) / timeframe_seconds) + 1
                missing_bars = max(expected_bars - len(klines), 0)
                if missing_bars > 0:
                    coverage = len(klines) / expected_bars
                    self.logger.warning(
                        "讀取的 K 線存在缺口: %s/%s, 預期 %d 根、實際 %d 根、缺少 %d 根、覆蓋率 %.2f%%",
                        symbol,
                        timeframe,
                        expected_bars,
                        len(klines),
                        missing_bars,
                        coverage * 100,
                    )

            return klines

        except ValueError as e:
            # 連續性檢查失敗，向上傳播
            self.logger.error(f"數據連續性檢查失敗: {e}")
            raise
        except Exception as e:
            self.logger.error(f"讀取K線數據失敗: {e}", exc_info=True)
            raise

    def _calculate_indicators(
        self,
        klines: pd.DataFrame,
        strategy_config: Any
    ) -> Dict[str, np.ndarray]:
        """
        計算指標

        調用 Task 3.1 的 IndicatorEngine 計算指標值。

        Args:
            klines: K線數據
            strategy_config: 策略配置

        Returns:
            指標結果字典 (indicator_name → np.ndarray)

        Raises:
            ValueError: 指標計算失敗或暖機數據不足

        Note:
            對於 EMA 三線策略,返回:
            {
                "ema_short": np.array([...]),
                "ema_mid": np.array([...]),
                "ema_long": np.array([...])
            }
        """
        try:
            # 根據策略邏輯確定需要計算的指標
            strategy_logic = strategy_config.strategy_logic
            params = strategy_config.params
            data_source = strategy_config.data_source
            indicator_type = strategy_config.indicator_type

            # 計算最大 EMA 週期（用於暖機檢查）
            max_period = 0
            if strategy_logic == "three_line":
                max_period = max(
                    params.get("short_period", 0),
                    params.get("mid_period", 0),
                    params.get("long_period", 0)
                )
            elif strategy_logic == "short_long_cross":
                max_period = max(
                    params.get("short_period", 0),
                    params.get("long_period", 0)
                )
            elif strategy_logic == "mid_long_cross":
                max_period = max(
                    params.get("mid_period", 0),
                    params.get("long_period", 0)
                )
            
            # 暖機充足性檢查（4.5× 最大週期）
            WARMUP_MULTIPLIER = 4.5
            required_warmup_bars = int(max_period * WARMUP_MULTIPLIER)
            available_bars = len(klines)

            if available_bars < required_warmup_bars:
                first_ts = int(klines.iloc[0]['timestamp']) if len(klines) > 0 else 0
                last_ts = int(klines.iloc[-1]['timestamp']) if len(klines) > 0 else 0

                error_detail = {
                    "code": "INSUFFICIENT_WARMUP",
                    "message": f"暖機數據不足: 最大 EMA 週期為 {max_period}，需要 {required_warmup_bars} 根K線（4.5× 週期），實際只有 {available_bars} 根",
                    "max_ema_period": max_period,
                    "required_bars": required_warmup_bars,
                    "available_bars": available_bars,
                    "missing_bars": required_warmup_bars - available_bars,
                    "available_start_timestamp": first_ts,
                    "available_end_timestamp": last_ts,
                    "suggested_action": f"請擴大時間範圍或重新批量下載數據，建議 warmup_bars >= {required_warmup_bars}（最長EMA週期 × 4.5）才能準確計算 EMA{max_period}"
                }

                self.logger.error(f"暖機數據不足: {error_detail}")
                raise ValueError(error_detail["message"])

            # 定義參數名稱到輸出列名的映射
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
                raise ValueError(f"不支持的策略邏輯: {strategy_logic}")

            indicator_configs = []
            for param_name, output_name in param_to_output.items():
                if param_name not in params:
                    raise ValueError(f"策略參數缺少 {param_name}")

                period = params[param_name]
                indicator_configs.append(
                    {
                        "indicator": indicator_type,
                        "data_source": data_source,
                        "params": {"period": period},
                        "output_name": output_name,
                    }
                )

            indicator_df = self.indicator_engine.calculate_indicators_from_dataframe(
                kline_df=klines,
                configs=indicator_configs,
            )

            # 獲取輸出列名列表
            output_names = list(param_to_output.values())
            missing_columns = [name for name in output_names if name not in indicator_df.columns]
            if missing_columns:
                raise ValueError(
                    f"指標計算缺少欄位: {', '.join(missing_columns)}"
                )

            results = {
                output_name: indicator_df[output_name].to_numpy()
                for output_name in output_names
            }

            return results

        except Exception as e:
            self.logger.error(f"指標計算失敗: {e}", exc_info=True)
            raise ValueError(f"指標計算失敗: {e}")

    def _evaluate_strategy_logic(
        self,
        indicator_results: Dict[str, np.ndarray],
        strategy_config: Any
    ) -> np.ndarray:
        """
        評估策略邏輯 (向量化)

        使用向量化運算判斷每根K線是否符合策略條件。

        Args:
            indicator_results: 指標結果字典
            strategy_config: 策略配置

        Returns:
            布林數組 (True表示符合策略)

        Note:
            策略邏輯:
            - three_line: ema_short > ema_mid > ema_long
            - short_long_cross: ema_short > ema_long
            - mid_long_cross: ema_mid > ema_long
        """
        strategy_logic = strategy_config.strategy_logic

        if strategy_logic == "three_line":
            # EMA 三線排列: short > mid > long
            ema_short = indicator_results["ema_short"]
            ema_mid = indicator_results["ema_mid"]
            ema_long = indicator_results["ema_long"]

            # 向量化布林運算
            mask = (ema_short > ema_mid) & (ema_mid > ema_long)

        elif strategy_logic == "short_long_cross":
            # 短長交叉: short > long
            ema_short = indicator_results["ema_short"]
            ema_long = indicator_results["ema_long"]

            mask = ema_short > ema_long

        elif strategy_logic == "mid_long_cross":
            # 中長交叉: mid > long
            ema_mid = indicator_results["ema_mid"]
            ema_long = indicator_results["ema_long"]

            mask = ema_mid > ema_long

        else:
            raise ValueError(f"不支持的策略邏輯: {strategy_logic}")

        # 處理 NaN 值 (指標計算初期可能為 NaN)
        mask = np.nan_to_num(mask, nan=False)

        return mask

    def _generate_signal_points(
        self,
        klines: pd.DataFrame,
        indicator_results: Dict[str, np.ndarray],
        signal_mask: np.ndarray,
        user_start_time: Optional[int] = None
    ) -> List[SignalPoint]:
        """
        生成信號點列表

        根據信號掩碼生成 SignalPoint 對象列表。

        Args:
            klines: K線數據
            indicator_results: 指標結果字典
            signal_mask: 信號布林掩碼
            user_start_time: 用戶請求的起始時間戳（毫秒），如提供則過濾掉暖機期的信號點

        Returns:
            SignalPoint 列表
        """
        signal_points = []

        # 找出所有符合策略的索引
        signal_indices = np.where(signal_mask)[0]

        for idx in signal_indices:
            # 提取時間戳（秒）
            timestamp_sec = int(klines.iloc[idx]["timestamp"])
            timestamp_ms = timestamp_sec * 1000
            
            # 如果指定了用戶起始時間，過濾掉暖機期的信號點
            if user_start_time is not None and timestamp_ms < user_start_time:
                continue

            # 提取指標值
            indicator_values = {}
            for indicator_name, values in indicator_results.items():
                indicator_values[indicator_name] = float(values[idx])

            # 創建 SignalPoint（timestamp 使用秒）
            signal_point = SignalPoint(
                timestamp=timestamp_ms,  # API 模型期望毫秒
                indicator_values=indicator_values,
                signal_density=None  # 暫時不計算單點密度
            )

            signal_points.append(signal_point)

        return signal_points

    def _sample_signals(
        self,
        signal_points: List[SignalPoint],
        max_points: int
    ) -> List[SignalPoint]:
        """
        智能採樣信號點

        當信號點數量超過限制時,進行均勻採樣。

        Args:
            signal_points: 原始信號點列表
            max_points: 最大點數

        Returns:
            採樣後的信號點列表

        Note:
            採樣策略:
            - 使用均勻採樣 (等間隔選取)
            - 保證首尾信號點一定被選中
            - 未來可改進為保留高密度區域
        """
        if len(signal_points) <= max_points:
            return signal_points

        # 計算採樣間隔
        step = len(signal_points) / max_points

        # 均勻採樣
        sampled_indices = [int(i * step) for i in range(max_points)]

        # 確保最後一個點被包含
        if sampled_indices[-1] != len(signal_points) - 1:
            sampled_indices[-1] = len(signal_points) - 1

        sampled_points = [signal_points[i] for i in sampled_indices]

        self.logger.info(
            f"採樣完成: {len(signal_points)} → {len(sampled_points)}"
        )

        return sampled_points

    def _generate_strategy_name(self, strategy_config: Any) -> str:
        """
        生成策略名稱

        根據策略配置自動生成易讀的策略名稱。

        Args:
            strategy_config: 策略配置

        Returns:
            策略名稱字符串

        Example:
            >>> config = StrategyConfig(
            ...     data_source="close",
            ...     indicator_type="ema",
            ...     strategy_logic="three_line",
            ...     params={"ema_short": 7, "ema_mid": 18, "ema_long": 35}
            ... )
            >>> name = self._generate_strategy_name(config)
            >>> print(name)
            "EMA(7,18,35)三線排列 - 收盤價"
        """
        indicator_type = strategy_config.indicator_type.upper()
        strategy_logic = strategy_config.strategy_logic
        params = strategy_config.params
        data_source = strategy_config.data_source

        # 策略邏輯中文名稱
        logic_names = {
            "three_line": "三線排列",
            "short_long_cross": "短長交叉",
            "mid_long_cross": "中長交叉"
        }
        logic_name = logic_names.get(strategy_logic, strategy_logic)

        # 數據源中文名稱
        source_names = {
            "close": "收盤價",
            "open": "開盤價",
            "high": "最高價",
            "low": "最低價",
            "volume": "成交量",
            "taker_buy_volume": "主動買入量",
            "taker_ratio": "主動買入比例",
            "quote_volume": "成交額"
        }
        source_name = source_names.get(data_source, data_source)

        # 提取參數
        if strategy_logic == "three_line":
            param_str = f"({params.get('short_period')},{params.get('mid_period')},{params.get('long_period')})"
        elif strategy_logic == "short_long_cross":
            param_str = f"({params.get('short_period')},{params.get('long_period')})"
        elif strategy_logic == "mid_long_cross":
            param_str = f"({params.get('mid_period')},{params.get('long_period')})"
        else:
            param_str = ""

        return f"{indicator_type}{param_str}{logic_name} - {source_name}"
