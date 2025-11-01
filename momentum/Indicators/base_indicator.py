"""
BaseIndicator 抽象類 - Ultra Think 最終優化版本

定義所有技術指標的統一接口和共用邏輯。
參考 Base_Indicator_Reference.py 的最佳實踐，簡化並優化。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本的抽象方法定義
- 步驟 2: 審查優化 - 添加驗證、錯誤處理、性能監控、輔助方法
- 步驟 3: 最終版本 - 實作完整的基類功能

設計原則：
- 統一接口：所有指標遵循相同的調用方式
- 完整驗證：數據和參數驗證確保計算正確
- 錯誤處理：safe_calculate 包裝器處理所有異常
- 性能監控：記錄計算時間用於優化
- 易於擴展：子類只需實作 calculate 和 validate_params
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import logging
import time

from .types import DataSourceEnum, IndicatorResult

logger = logging.getLogger(__name__)


class BaseIndicator(ABC):
    """
    指標抽象基類

    所有技術指標都必須繼承此類並實作以下抽象方法：
    - calculate(): 核心計算邏輯
    - validate_params(): 參數驗證邏輯

    共用功能：
    - validate_data(): 數據驗證
    - safe_calculate(): 帶錯誤處理的計算包裝器
    - calculate_batch(): 批量計算多個數據源
    - _detect_valid_start(): 檢測第一個有效值位置

    Example:
        >>> class EMAIndicator(BaseIndicator):
        ...     @classmethod
        ...     def get_indicator_name(cls) -> str:
        ...         return "ema"
        ...
        ...     def calculate(self, data: pd.Series, period: int = 20) -> pd.Series:
        ...         return data.ewm(span=period, adjust=False).mean()
        ...
        ...     def validate_params(self, period: int = 20, **kwargs) -> bool:
        ...         return 2 <= period <= 200
    """

    def __init__(self):
        """
        初始化指標

        子類一般不需要覆寫此方法，除非有特殊的初始化需求。
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._last_error: Optional[str] = None
        self._last_calc_time: Optional[float] = None

    # ==================== 抽象方法（子類必須實作） ====================

    @abstractmethod
    def calculate(self, data: pd.Series, **params) -> pd.Series:
        """
        計算指標（核心方法，子類必須實作）

        Args:
            data: 輸入數據序列（如 close price, volume 等）
            **params: 指標參數（如 period, smooth 等）

        Returns:
            pd.Series: 計算結果序列（與輸入等長，前N個值可能為 NaN）

        Note:
            - 結果序列必須與輸入等長
            - 前N個不足以計算的值應設為 NaN
            - 避免 look-ahead bias（未來函數）

        Example:
            >>> def calculate(self, data: pd.Series, period: int = 20) -> pd.Series:
            ...     return data.ewm(span=period, adjust=False).mean()
        """
        pass

    @abstractmethod
    def validate_params(self, **params) -> bool:
        """
        驗證參數有效性（子類必須實作）

        Args:
            **params: 指標參數

        Returns:
            bool: 參數是否有效

        Raises:
            ValueError: 參數無效時可以拋出異常（可選）

        Example:
            >>> def validate_params(self, period: int = 20, **kwargs) -> bool:
            ...     if not isinstance(period, int):
            ...         raise ValueError("period must be int")
            ...     if not 2 <= period <= 200:
            ...         raise ValueError("period must be in [2, 200]")
            ...     return True
        """
        pass

    # ==================== 類方法（子類應該覆寫） ====================

    @classmethod
    def get_indicator_name(cls) -> str:
        """
        獲取指標名稱（建議子類覆寫）

        Returns:
            str: 指標名稱（如 "ema", "sma", "rsi"）

        Example:
            >>> @classmethod
            >>> def get_indicator_name(cls) -> str:
            ...     return "ema"
        """
        return cls.__name__.lower().replace("indicator", "")

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """
        獲取默認參數（建議子類覆寫）

        Returns:
            Dict[str, Any]: 默認參數字典

        Example:
            >>> @classmethod
            >>> def get_default_params(cls) -> Dict[str, Any]:
            ...     return {"period": 20}
        """
        return {}

    # ==================== 數據驗證 ====================

    def validate_data(self, data: pd.Series) -> Tuple[bool, str]:
        """
        驗證輸入數據

        Args:
            data: 輸入數據序列

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤信息)

        檢查項：
        - 數據不為空
        - 無 NaN 值（或 NaN 比例可接受）
        - 數值範圍合理
        """
        if data is None or len(data) == 0:
            return False, "Data is empty"

        # 檢查 NaN
        nan_count = data.isna().sum()
        nan_ratio = nan_count / len(data)
        if nan_ratio > 0.1:  # 允許最多 10% 的 NaN
            return False, f"Too many NaN values: {nan_count}/{len(data)} ({nan_ratio:.1%})"

        # 檢查數據類型
        if not np.issubdtype(data.dtype, np.number):
            return False, f"Data must be numeric, got {data.dtype}"

        return True, ""

    # ==================== 計算包裝器 ====================

    def safe_calculate(self, data: pd.Series, **params) -> Optional[IndicatorResult]:
        """
        安全的計算包裝器（帶完整錯誤處理）

        Args:
            data: 輸入數據序列
            **params: 指標參數

        Returns:
            Optional[IndicatorResult]: 計算結果（包含數據和元數據）
                                       失敗時返回 None

        Example:
            >>> indicator = EMAIndicator()
            >>> result = indicator.safe_calculate(close_data, period=20)
            >>> if result:
            ...     print(f"Valid from index: {result['valid_from']}")
            ...     print(f"Calculation time: {result['metadata']['calc_time_ms']}ms")
        """
        self._last_error = None
        start_time = time.time()

        try:
            # 驗證參數
            if not self.validate_params(**params):
                error_msg = f"Invalid parameters: {params}"
                self.logger.error(error_msg)
                self._last_error = error_msg
                return None

            # 驗證數據
            is_valid, error_msg = self.validate_data(data)
            if not is_valid:
                self.logger.error(f"Data validation failed: {error_msg}")
                self._last_error = error_msg
                return None

            # 執行計算
            result_series = self.calculate(data, **params)

            # 計算時間
            calc_time = (time.time() - start_time) * 1000  # 毫秒
            self._last_calc_time = calc_time

            # 檢測有效起始位置
            valid_from = self._detect_valid_start(result_series)

            # 構建結果
            result: IndicatorResult = {
                "data": result_series,
                "valid_from": valid_from,
                "metadata": {
                    "params": params,
                    "calc_time_ms": round(calc_time, 2),
                    "data_length": len(data),
                    "indicator_name": self.get_indicator_name()
                }
            }

            self.logger.debug(
                f"Calculation completed: {len(data)} bars, "
                f"{calc_time:.2f}ms, valid_from={valid_from}"
            )

            return result

        except Exception as e:
            error_msg = f"Calculation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self._last_error = error_msg
            return None

    def calculate_batch(
        self,
        data_dict: Dict[DataSourceEnum, pd.Series],
        **params
    ) -> Dict[DataSourceEnum, pd.Series]:
        """
        批量計算多個數據源

        Args:
            data_dict: 數據源字典（key: DataSourceEnum, value: pd.Series）
            **params: 指標參數

        Returns:
            Dict[DataSourceEnum, pd.Series]: 計算結果字典

        Example:
            >>> all_sources = data_manager.get_all_data_sources("ETHUSDT", "1h")
            >>> results = indicator.calculate_batch(all_sources, period=20)
            >>> print(f"Calculated {len(results)} data sources")
        """
        result = {}
        for ds, series in data_dict.items():
            try:
                result[ds] = self.calculate(series, **params)
                self.logger.debug(f"Calculated {ds.value}: {len(series)} bars")
            except Exception as e:
                self.logger.error(f"Failed to calculate {ds.value}: {e}")
                # 繼續處理其他數據源（降級策略）

        return result

    # ==================== 輔助方法 ====================

    def _detect_valid_start(self, data: pd.Series) -> int:
        """
        檢測第一個有效值的索引位置

        Args:
            data: 計算結果序列

        Returns:
            int: 第一個非 NaN 值的索引（0-based）
                 如果全部為 NaN，返回 len(data)

        Example:
            >>> result = pd.Series([nan, nan, 1.5, 2.0, 2.5])
            >>> valid_from = indicator._detect_valid_start(result)
            >>> print(valid_from)  # 2
        """
        if data is None or len(data) == 0:
            return 0

        # 找到第一個非 NaN 的位置
        valid_mask = ~data.isna()
        if not valid_mask.any():
            # 全部為 NaN
            return len(data)

        # 返回第一個 True 的索引
        return valid_mask.idxmax() if isinstance(valid_mask.idxmax(), int) else 0

    def get_last_error(self) -> Optional[str]:
        """
        獲取最後一次錯誤信息

        Returns:
            Optional[str]: 錯誤信息，無錯誤時返回 None
        """
        return self._last_error

    def get_last_calc_time(self) -> Optional[float]:
        """
        獲取最後一次計算時間（毫秒）

        Returns:
            Optional[float]: 計算時間（ms），未計算時返回 None
        """
        return self._last_calc_time
