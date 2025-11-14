"""
指標計算引擎 - Ultra Think 最終優化版本

統一的指標調用入口，支援指標註冊、配置驅動的批量計算、整合 HDF5。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本的註冊和計算功能
- 步驟 2: 審查優化 - 添加裝飾器、錯誤處理、性能監控、元信息
- 步驟 3: 最終版本 - 實作所有優化項

設計原則：
- 統一入口：所有指標通過引擎調用
- 靈活註冊：支援類方法和裝飾器兩種方式
- 配置驅動：從配置列表批量計算
- 完整錯誤處理：單個指標失敗不影響其他指標
- 性能監控：記錄計算時間
"""

from typing import Dict, List, Type, Optional, Any, Callable
import pandas as pd
import logging
import time
from functools import wraps

from .base_indicator import BaseIndicator
from .data_source_manager import DataSourceManager
from .types import DataSourceEnum, IndicatorConfig

logger = logging.getLogger(__name__)


def register_indicator(name: str) -> Callable:
    """
    裝飾器：註冊指標

    Example:
        >>> @register_indicator("ema")
        >>> class EMAIndicator(BaseIndicator):
        ...     pass
    """
    def decorator(indicator_class: Type[BaseIndicator]) -> Type[BaseIndicator]:
        IndicatorEngine.register(name, indicator_class)
        return indicator_class
    return decorator


class IndicatorEngine:
    """
    指標計算引擎

    統一管理所有指標，提供註冊機制和批量計算功能。
    整合 DataSourceManager 和 KlineStorageManager，實現端到端計算。

    主要功能：
    - 指標註冊（類方法或裝飾器）
    - 單指標計算
    - 批量計算（配置驅動）
    - 從 symbol/timeframe 端到端計算
    - 錯誤處理和降級策略
    - 性能監控

    Example:
        >>> from momentum.Indicators import IndicatorEngine, EMAIndicator
        >>>
        >>> # 註冊指標
        >>> IndicatorEngine.register("ema", EMAIndicator)
        >>>
        >>> # 初始化引擎
        >>> engine = IndicatorEngine()
        >>>
        >>> # 單指標計算
        >>> result = engine.calculate_indicator(
        ...     "ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=20
        ... )
        >>>
        >>> # 批量計算
        >>> configs = [
        ...     {"indicator": "ema", "data_source": "close", "params": {"period": 20}},
        ...     {"indicator": "ema", "data_source": "volume", "params": {"period": 10}},
        ... ]
        >>> results = engine.calculate_indicators("ETHUSDT", "1h", configs)
    """

    # 類變量：註冊的指標
    _indicators: Dict[str, Type[BaseIndicator]] = {}

    def __init__(self, data_manager: Optional[DataSourceManager] = None):
        """
        初始化指標引擎

        Args:
            data_manager: 數據源管理器（可選，默認創建新實例）
        """
        self.data_manager = data_manager or DataSourceManager()
        logger.info("IndicatorEngine initialized")

    # ==================== 指標註冊 ====================

    @classmethod
    def register(cls, name: str, indicator_class: Type[BaseIndicator]):
        """
        註冊指標（類方法）

        Args:
            name: 指標名稱（如 "ema", "sma", "rsi"）
            indicator_class: 指標類（必須繼承 BaseIndicator）

        Raises:
            ValueError: 如果指標類不是 BaseIndicator 的子類

        Example:
            >>> IndicatorEngine.register("ema", EMAIndicator)
            >>> print(IndicatorEngine.list_indicators())
            ['ema']
        """
        # 驗證指標類
        if not issubclass(indicator_class, BaseIndicator):
            raise ValueError(
                f"Indicator class must inherit from BaseIndicator, "
                f"got {indicator_class.__name__}"
            )

        # 檢查重複註冊
        if name in cls._indicators:
            logger.warning(f"Indicator '{name}' already registered, overwriting")

        cls._indicators[name] = indicator_class
        logger.info(f"Registered indicator: {name} -> {indicator_class.__name__}")

    @classmethod
    def unregister(cls, name: str):
        """
        取消註冊指標

        Args:
            name: 指標名稱
        """
        if name in cls._indicators:
            del cls._indicators[name]
            logger.info(f"Unregistered indicator: {name}")

    @classmethod
    def list_indicators(cls) -> List[str]:
        """
        列出所有已註冊的指標

        Returns:
            List[str]: 指標名稱列表

        Example:
            >>> indicators = IndicatorEngine.list_indicators()
            >>> print(f"Available indicators: {indicators}")
        """
        return list(cls._indicators.keys())

    @classmethod
    def get_indicator_info(cls, name: str) -> Dict[str, Any]:
        """
        獲取指標元信息

        Args:
            name: 指標名稱

        Returns:
            Dict[str, Any]: 指標信息（類名、默認參數等）

        Example:
            >>> info = IndicatorEngine.get_indicator_info("ema")
            >>> print(info['default_params'])
            {'period': 20}
        """
        if name not in cls._indicators:
            raise ValueError(f"Indicator '{name}' not registered")

        indicator_class = cls._indicators[name]
        return {
            "name": name,
            "class_name": indicator_class.__name__,
            "default_params": indicator_class.get_default_params(),
            "description": indicator_class.__doc__ or "No description"
        }

    # ==================== 單指標計算 ====================

    def calculate_indicator(
        self,
        indicator_name: str,
        data_source: DataSourceEnum,
        symbol: str,
        timeframe: str,
        **params
    ) -> pd.Series:
        """
        計算單個指標

        從 HDF5 讀取數據並計算指標。

        Args:
            indicator_name: 指標名稱（必須已註冊）
            data_source: 數據源（如 CLOSE, VOLUME）
            symbol: 交易對（如 "ETHUSDT"）
            timeframe: 時間框架（如 "1h"）
            **params: 指標參數

        Returns:
            pd.Series: 計算結果

        Raises:
            ValueError: 指標未註冊或計算失敗

        Example:
            >>> engine = IndicatorEngine()
            >>> ema = engine.calculate_indicator(
            ...     "ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=20
            ... )
            >>> print(f"EMA values: {len(ema)}")
        """
        # 獲取指標類
        if indicator_name not in self._indicators:
            available = ", ".join(self.list_indicators())
            raise ValueError(
                f"Indicator '{indicator_name}' not registered. "
                f"Available: {available}"
            )

        indicator_class = self._indicators[indicator_name]
        indicator = indicator_class()

        # 獲取數據
        logger.debug(
            f"Loading data: {symbol}/{timeframe}/{data_source.value}"
        )
        data = self.data_manager.get_data_source(symbol, timeframe, data_source)

        # 計算
        logger.debug(f"Calculating {indicator_name} with params: {params}")
        start_time = time.time()
        result = indicator.calculate(data, **params)
        calc_time = (time.time() - start_time) * 1000

        logger.info(
            f"Calculated {indicator_name}({params}) on {symbol}/{timeframe}/{data_source.value}: "
            f"{calc_time:.2f}ms"
        )

        return result

    # ==================== 批量計算 ====================

    def calculate_indicators(
        self,
        symbol: str,
        timeframe: str,
        configs: List[IndicatorConfig]
    ) -> pd.DataFrame:
        """
        批量計算多個指標（配置驅動）

        根據配置列表批量計算，單個指標失敗不影響其他指標。

        Args:
            symbol: 交易對
            timeframe: 時間框架
            configs: 指標配置列表，每個配置包含：
                    - indicator: 指標名稱
                    - data_source: 數據源名稱（字符串）
                    - params: 參數字典
                    - output_name: 可選的輸出列名

        Returns:
            pd.DataFrame: 所有成功計算的指標結果

        Example:
            >>> configs = [
            ...     {
            ...         "indicator": "ema",
            ...         "data_source": "close",
            ...         "params": {"period": 20},
            ...         "output_name": "ema_20"
            ...     },
            ...     {
            ...         "indicator": "ema",
            ...         "data_source": "volume",
            ...         "params": {"period": 10}
            ...     }
            ... ]
            >>> results = engine.calculate_indicators("ETHUSDT", "1h", configs)
            >>> print(results.columns)
            ['ema_20', 'ema_volume_period10']
        """
        logger.info(
            f"Starting batch calculation: {len(configs)} indicators "
            f"for {symbol}/{timeframe}"
        )
        start_time = time.time()

        results = {}
        success_count = 0
        fail_count = 0

        for i, config in enumerate(configs, 1):
            try:
                indicator_name = config['indicator']
                data_source_str = config['data_source']
                params = config.get('params', {})
                output_name = self._generate_output_name(
                    indicator_name,
                    data_source_str,
                    params,
                    config.get('output_name')
                )

                # 轉換數據源
                try:
                    data_source = DataSourceEnum(data_source_str)
                except ValueError:
                    logger.error(
                        f"Invalid data_source '{data_source_str}' in config #{i}"
                    )
                    fail_count += 1
                    continue

                # 計算指標
                logger.debug(f"Calculating #{i}: {output_name}")
                result = self.calculate_indicator(
                    indicator_name, data_source, symbol, timeframe, **params
                )

                results[output_name] = result
                success_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to calculate config #{i}: {e}",
                    exc_info=True
                )
                fail_count += 1
                # 繼續處理其他指標（降級策略）

        # 計算總時間
        total_time = (time.time() - start_time) * 1000

        logger.info(
            f"Batch calculation completed: {success_count} succeeded, "
            f"{fail_count} failed, {total_time:.2f}ms total"
        )

        # 返回 DataFrame（如果有成功的結果）
        if results:
            return pd.DataFrame(results)
        else:
            logger.warning("No indicators calculated successfully")
            return pd.DataFrame()

    def calculate_indicators_from_dataframe(
        self,
        kline_df: pd.DataFrame,
        configs: List[IndicatorConfig]
    ) -> pd.DataFrame:
        """從現有 K 線 DataFrame 計算指標"""
        if kline_df is None or kline_df.empty:
            raise ValueError("kline_df is empty; cannot calculate indicators")

        logger.info(
            f"Starting in-memory calculation: {len(configs)} indicators on {len(kline_df)} bars"
        )
        start_time = time.time()

        results: Dict[str, pd.Series] = {}
        success_count = 0
        fail_count = 0

        for i, config in enumerate(configs, 1):
            try:
                indicator_name = config['indicator']
                data_source_str = config['data_source']
                params = config.get('params', {})
            except KeyError as e:
                logger.error(f"Config #{i} missing required field: {e}")
                fail_count += 1
                continue

            output_name = self._generate_output_name(
                indicator_name,
                data_source_str,
                params,
                config.get('output_name')
            )

            # 轉換枚舉
            try:
                data_source = DataSourceEnum(data_source_str)
            except ValueError:
                logger.error(
                    f"Invalid data_source '{data_source_str}' in config #{i}"
                )
                fail_count += 1
                continue

            if indicator_name not in self._indicators:
                available = ", ".join(self.list_indicators()) or "<none>"
                logger.error(
                    f"Indicator '{indicator_name}' not registered. Available: {available}"
                )
                fail_count += 1
                continue

            # 取得資料欄位
            try:
                data_series = self.data_manager.get_data_source_from_df(
                    kline_df,
                    data_source
                )
            except Exception as e:
                logger.error(
                    f"Failed to extract data_source '{data_source.value}' for config #{i}: {e}"
                )
                raise ValueError(
                    f"DataFrame 缺少所需欄位 '{data_source.value}' 或包含無效數據"
                ) from e

            indicator_class = self._indicators[indicator_name]
            indicator = indicator_class()

            indicator_result = indicator.safe_calculate(data_series, **params)
            if indicator_result is None:
                last_error = indicator.get_last_error() or "Unknown indicator error"
                logger.error(
                    f"Indicator '{indicator_name}' failed on config #{i}: {last_error}"
                )
                fail_count += 1
                continue

            result_series = indicator_result['data']
            if not result_series.index.equals(kline_df.index):
                result_series = result_series.reindex(kline_df.index)

            results[output_name] = result_series
            success_count += 1

        total_time = (time.time() - start_time) * 1000
        logger.info(
            f"In-memory calculation completed: {success_count} succeeded, "
            f"{fail_count} failed, {total_time:.2f}ms total"
        )

        if not results:
            raise ValueError(
                "No indicators calculated successfully from dataframe; see logs for details"
            )

        return pd.DataFrame(results, index=kline_df.index)

    @staticmethod
    def _generate_output_name(
        indicator_name: str,
        data_source_str: str,
        params: Dict[str, Any],
        custom_name: Optional[str]
    ) -> str:
        """建立一致且可控的輸出欄位名稱"""
        if custom_name:
            return custom_name

        if params:
            param_str = "_".join(
                f"{key}{value}" for key, value in sorted(params.items())
            )
        else:
            param_str = "default"

        return f"{indicator_name}_{data_source_str}_{param_str}"

    # ==================== 輔助方法 ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取引擎統計信息

        Returns:
            Dict[str, Any]: 統計信息
        """
        return {
            "registered_indicators": len(self._indicators),
            "indicator_names": self.list_indicators(),
            "cache_size": len(self.data_manager._cache)
        }
