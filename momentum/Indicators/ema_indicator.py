"""
EMA 指標實作 - Ultra Think 最終優化版本

指數移動平均線（Exponential Moving Average）
使用 pandas_ta 庫計算，對近期價格賦予更高權重。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本的 EMA 計算
- 步驟 2: 審查優化 - 添加完整文檔、參數驗證、邊界處理
- 步驟 3: 最終版本 - 實作所有優化項

參考：Advanced_MA_Reference.py 的 EMA 實作方式
"""

import pandas as pd
from typing import Dict, Any
import logging

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas_ta not available, using pandas native ewm")

from .base_indicator import BaseIndicator
from .indicator_engine import register_indicator

logger = logging.getLogger(__name__)


@register_indicator("ema")
class EMAIndicator(BaseIndicator):
    """
    EMA（指數移動平均線）指標實作

    指數移動平均線是一種趨勢跟蹤指標，對近期價格賦予更高權重。
    相比簡單移動平均（SMA），EMA 對價格變化更敏感。

    計算公式：
        EMA[t] = price[t] × α + EMA[t-1] × (1-α)
        其中 α = 2 / (period + 1)

    特性：
    - 對近期價格變化反應更快
    - 滯後性較 SMA 小
    - 常用週期: 12, 20, 26, 50, 200

    Example:
        >>> from momentum.Indicators import EMAIndicator
        >>> from momentum.Indicators import DataSourceManager, DataSourceEnum
        >>>
        >>> # 初始化
        >>> indicator = EMAIndicator()
        >>> manager = DataSourceManager()
        >>>
        >>> # 獲取數據
        >>> close = manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)
        >>>
        >>> # 計算 EMA
        >>> ema_20 = indicator.calculate(close, period=20)
        >>> print(f"EMA 有效值從索引 {indicator._detect_valid_start(ema_20)} 開始")
        >>>
        >>> # 使用 safe_calculate（推薦）
        >>> result = indicator.safe_calculate(close, period=20)
        >>> if result:
        ...     print(f"計算時間: {result['metadata']['calc_time_ms']}ms")
        ...     print(f"有效起始: {result['valid_from']}")
    """

    @classmethod
    def get_indicator_name(cls) -> str:
        """
        獲取指標名稱

        Returns:
            str: "ema"
        """
        return "ema"

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """
        獲取默認參數

        Returns:
            Dict[str, Any]: {"period": 20}
        """
        return {"period": 20}

    def calculate(self, data: pd.Series, period: int = 20, **kwargs) -> pd.Series:
        """
        計算 EMA

        使用 pandas_ta 庫計算（如果可用），否則使用 pandas 原生 ewm。
        結果序列與輸入等長，前 (period-1) 個值為 NaN。

        Args:
            data: 輸入數據序列（如 close price, volume 等）
            period: 週期參數（默認 20）
                   - 短期: 12, 20, 26
                   - 中期: 50
                   - 長期: 100, 200
            **kwargs: 其他參數（忽略）

        Returns:
            pd.Series: EMA 計算結果（與輸入等長）

        Raises:
            ValueError: 參數無效時拋出

        Note:
            - 前 (period-1) 個值為 NaN
            - 使用 adjust=False 以保持與 TA-Lib 一致
            - 計算公式: α = 2/(period+1)

        Example:
            >>> data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            >>> ema = indicator.calculate(data, period=3)
            >>> print(ema)
            0    NaN
            1    NaN
            2    2.0
            3    3.0
            4    4.0
            ...
        """
        # 驗證參數
        if not self.validate_params(period=period):
            raise ValueError(f"Invalid period: {period}")

        # 檢查數據長度
        if len(data) < period:
            logger.warning(
                f"Data length ({len(data)}) < period ({period}), "
                f"all values will be NaN"
            )
            return pd.Series([float('nan')] * len(data), index=data.index)

        # 使用 pandas_ta（如果可用）
        if PANDAS_TA_AVAILABLE:
            try:
                result = ta.ema(data, length=period)
                logger.debug(f"Calculated EMA using pandas_ta: period={period}")
                return result
            except Exception as e:
                logger.warning(f"pandas_ta failed, falling back to pandas ewm: {e}")

        # 回退到 pandas 原生 ewm
        result = data.ewm(span=period, adjust=False).mean()
        logger.debug(f"Calculated EMA using pandas ewm: period={period}")

        return result

    def validate_params(self, period: int = 20, **kwargs) -> bool:
        """
        驗證參數有效性

        Args:
            period: 週期參數
            **kwargs: 其他參數（忽略）

        Returns:
            bool: 參數是否有效

        Raises:
            ValueError: 參數無效時拋出詳細錯誤信息

        參數約束：
        - period 必須是整數
        - period 範圍: [2, 200]
          - 最小 2: 技術上可計算的最小值
          - 最大 200: 常用的最長週期（200日均線）

        Example:
            >>> indicator = EMAIndicator()
            >>> indicator.validate_params(period=20)  # True
            >>> indicator.validate_params(period=1)   # ValueError
            >>> indicator.validate_params(period=300) # ValueError
        """
        # 檢查類型
        if not isinstance(period, int):
            raise ValueError(
                f"period must be int, got {type(period).__name__}"
            )

        # 檢查範圍
        if period < 2:
            raise ValueError(
                f"period must be >= 2 (got {period}). "
                f"Period too small for meaningful EMA calculation."
            )

        if period > 200:
            raise ValueError(
                f"period must be <= 200 (got {period}). "
                f"For very long periods, consider using SMA or custom implementation."
            )

        return True
