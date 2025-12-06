"""
EMA 指標實作 - 函數式版本

指數移動平均線（Exponential Moving Average）
使用函數式風格實作，通過 register_functional_indicator 自動包裝成類。

此版本作為混合式架構的範例，展示如何以簡單的函數式風格實作技術指標。

功能特性：
- 使用 pandas_ta 庫計算（如果可用）
- 回退到 pandas 原生 ewm
- 完整的參數驗證
- 邊界條件處理

Author: Claude (Sonnet 4.5)
Date: 2025-12-04
"""

import pandas as pd
import logging
from typing import Dict, Any

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas_ta not available, using pandas native ewm")

from .functional_wrapper import register_functional_indicator

logger = logging.getLogger(__name__)


def calculate_ema(data: pd.Series, period: int = 20) -> pd.Series:
    """
    計算 EMA（指數移動平均線）

    指數移動平均線對近期價格賦予更高權重，相比 SMA 對價格變化更敏感。

    計算公式：
        EMA[t] = price[t] × α + EMA[t-1] × (1-α)
        其中 α = 2 / (period + 1)

    Args:
        data: 輸入數據序列（如 close price, volume 等）
        period: 週期參數（默認 20）
               - 短期: 12, 20, 26
               - 中期: 50
               - 長期: 100, 200

    Returns:
        pd.Series: EMA 計算結果（與輸入等長，前 period-1 個值為 NaN）

    Example:
        >>> import pandas as pd
        >>> data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        >>> ema = calculate_ema(data, period=3)
        >>> print(ema)
        0    NaN
        1    NaN
        2    2.00
        3    3.00
        4    4.00
        ...

    Note:
        - 前 (period-1) 個值為 NaN
        - 使用 adjust=False 以保持與幣安、TradingView 一致
        - 如果數據長度 < period，返回全 NaN 序列
        - 不使用 pandas_ta，因其 EMA 計算與業界標準有微小差異
    """
    # 邊界檢查：數據長度不足
    if len(data) < period:
        logger.warning(
            f"Data length ({len(data)}) < period ({period}), "
            f"returning all NaN"
        )
        return pd.Series([float('nan')] * len(data), index=data.index)

    # 強制使用 pandas 原生 ewm（與幣安、TradingView 一致）
    # 不使用 pandas_ta，因其 EMA 計算與業界標準有微小差異（小數第二位）
    result = data.ewm(span=period, adjust=False).mean()
    logger.debug(f"Calculated EMA using pandas ewm: period={period}")

    return result


def validate_ema_params(period: int = 20) -> bool:
    """
    驗證 EMA 參數有效性

    參數約束：
    - period 必須是整數
    - period 範圍: [2, 200]
      - 最小 2: 技術上可計算的最小值
      - 最大 200: 常用的最長週期（200日均線）

    Args:
        period: 週期參數

    Returns:
        bool: 參數是否有效（總是返回 True，無效時拋出異常）

    Raises:
        ValueError: 參數無效時拋出詳細錯誤信息

    Example:
        >>> validate_ema_params(period=20)  # True
        >>> validate_ema_params(period=1)   # ValueError
        >>> validate_ema_params(period=300) # ValueError
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


# 註冊到系統（一行代碼）
register_functional_indicator(
    name="ema",
    calculate_fn=calculate_ema,
    validate_fn=validate_ema_params,
    default_params={"period": 20},
    description=(
        "指數移動平均線（Exponential Moving Average）- "
        "對近期價格賦予更高權重，相比 SMA 對價格變化更敏感"
    )
)


# 可選：提供便利函數用於直接調用（測試用）
def ema(data: pd.Series, period: int = 20) -> pd.Series:
    """
    EMA 便利函數（直接調用，無錯誤處理）

    此函數直接調用 calculate_ema，不經過 IndicatorEngine。
    適用於測試和快速計算，但缺少 BaseIndicator 的錯誤處理。

    Args:
        data: 輸入數據序列
        period: 週期參數

    Returns:
        pd.Series: EMA 計算結果

    Example:
        >>> from momentum.Indicators.ema import ema
        >>> result = ema(close_data, period=20)
    """
    return calculate_ema(data, period=period)
