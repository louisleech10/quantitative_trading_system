"""
類型定義和枚舉 - Ultra Think 最終優化版本

定義指標計算系統中使用的核心類型和枚舉。
本模塊經過 Ultra Think 三步驟優化，確保類型定義完整且易於使用。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本的枚舉和類型定義
- 步驟 2: 審查優化 - 添加輔助方法、完善文檔、增強類型定義
- 步驟 3: 最終版本 - 實作所有優化項
"""

from enum import Enum
from typing import TypedDict, Dict, Any, List, Optional
import pandas as pd


class DataSourceEnum(str, Enum):
    """
    數據源枚舉 - 定義可用於指標計算的8種數據來源

    所有枚舉值嚴格對應 HDF5 K線數據中的實際欄位名稱，
    由 KlineStorageManager 管理和驗證。

    數據來源分類：
    - 價格數據: OPEN, HIGH, LOW, CLOSE
    - 成交量數據: VOLUME, TAKER_VOLUME, QUOTE_VOLUME
    - 市場力量數據: TAKER_RATIO

    Attributes:
        CLOSE: 收盤價（最常用於指標計算）
        OPEN: 開盤價
        HIGH: 最高價
        LOW: 最低價
        VOLUME: 成交量（基礎貨幣單位，如 BTC/ETH）
        TAKER_VOLUME: 主動買入成交量（市場力量指標）
        TAKER_RATIO: 主動買入比例（0.0~1.0，已在 HDF5 存儲時計算）
        QUOTE_VOLUME: 成交額（計價貨幣單位，如 USDT，可選）
    """
    CLOSE = "close"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    VOLUME = "volume"
    TAKER_VOLUME = "taker_buy_volume"
    TAKER_RATIO = "taker_ratio"
    QUOTE_VOLUME = "quote_volume"

    @classmethod
    def get_price_sources(cls) -> List['DataSourceEnum']:
        """
        獲取所有價格相關數據源（OHLC）

        Returns:
            包含 OPEN, HIGH, LOW, CLOSE 的列表

        Example:
            >>> DataSourceEnum.get_price_sources()
            [<DataSourceEnum.OPEN: 'open'>, <DataSourceEnum.HIGH: 'high'>, ...]
        """
        return [cls.OPEN, cls.HIGH, cls.LOW, cls.CLOSE]

    @classmethod
    def get_volume_sources(cls) -> List['DataSourceEnum']:
        """
        獲取所有成交量相關數據源

        Returns:
            包含 VOLUME, TAKER_VOLUME, QUOTE_VOLUME 的列表

        Example:
            >>> DataSourceEnum.get_volume_sources()
            [<DataSourceEnum.VOLUME: 'volume'>, ...]
        """
        return [cls.VOLUME, cls.TAKER_VOLUME, cls.QUOTE_VOLUME]

    @classmethod
    def get_required_sources(cls) -> List['DataSourceEnum']:
        """
        獲取必需的數據源（不包含可選的 QUOTE_VOLUME）

        Returns:
            包含 7 個必需數據源的列表
        """
        return [
            cls.CLOSE, cls.OPEN, cls.HIGH, cls.LOW,
            cls.VOLUME, cls.TAKER_VOLUME, cls.TAKER_RATIO
        ]

    @classmethod
    def get_all_sources(cls) -> List['DataSourceEnum']:
        """
        獲取所有數據源（包含可選的）

        Returns:
            包含所有 8 個數據源的列表
        """
        return list(cls)


class IndicatorParams(TypedDict, total=False):
    """
    指標參數基礎類型

    這是一個通用的參數字典，支援任意鍵值對。
    具體指標可以定義自己的參數類型（繼承此類）。

    使用 total=False 允許所有字段都是可選的，
    具體的參數驗證由各指標的 validate_params() 方法負責。

    常見參數：
        period: 週期參數（如 EMA 的週期）
        其他任意參數根據指標需求定義

    Example:
        >>> params: IndicatorParams = {"period": 20, "smooth": 3}
    """
    pass  # 允許任意鍵值對


class IndicatorResult(TypedDict):
    """
    指標計算結果類型

    包含計算結果數據和元數據，用於完整描述一個指標的計算輸出。

    Attributes:
        data: 計算結果序列（與輸入數據等長，前N個可能為NaN）
        valid_from: 第一個有效值的索引位置（0-based）
        metadata: 可選的額外元數據（如計算參數、時間等）

    Example:
        >>> result: IndicatorResult = {
        ...     "data": pd.Series([nan, nan, 1.5, 2.0, 2.5]),
        ...     "valid_from": 2,
        ...     "metadata": {"period": 20, "calc_time_ms": 5.2}
        ... }
    """
    data: pd.Series
    valid_from: int
    metadata: Optional[Dict[str, Any]]


class IndicatorConfig(TypedDict, total=False):
    """
    指標配置類型 - 用於配置驅動的批量計算

    定義如何計算一個指標的完整配置，包括指標名稱、
    數據源、參數和輸出名稱。

    Attributes:
        indicator: 指標名稱（如 "ema"）
        data_source: 數據源（如 "close"）
        params: 指標參數字典
        output_name: 可選的自訂輸出名稱（默認自動生成）

    Example:
        >>> config: IndicatorConfig = {
        ...     "indicator": "ema",
        ...     "data_source": "close",
        ...     "params": {"period": 20},
        ...     "output_name": "ema_20"
        ... }
    """
    indicator: str
    data_source: str
    params: Dict[str, Any]
    output_name: Optional[str]


class ParamRange(TypedDict):
    """
    參數範圍類型 - 用於 Optuna 參數優化

    定義指標參數的取值範圍，用於後續的參數優化任務。

    Attributes:
        min: 最小值
        max: 最大值
        step: 步長（可選）
        type: 參數類型（"int", "float", "categorical"）
        choices: 分類參數的可選值列表（僅當 type="categorical" 時）

    Example:
        >>> period_range: ParamRange = {
        ...     "min": 2,
        ...     "max": 200,
        ...     "step": 1,
        ...     "type": "int"
        ... }
    """
    min: Optional[float]
    max: Optional[float]
    step: Optional[float]
    type: str
    choices: Optional[List[Any]]
