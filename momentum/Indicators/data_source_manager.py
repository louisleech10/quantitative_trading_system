"""
數據源管理器 - Ultra Think 最終優化版本

統一管理從 HDF5 讀取K線數據的各種數據源。
整合 KlineStorageManager，提供標準化的數據訪問接口。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本的讀取和驗證功能
- 步驟 2: 審查優化 - 添加完整錯誤處理、日誌、緩存、更強驗證
- 步驟 3: 最終版本 - 實作所有優化項，支援 DataFrame 直接輸入

設計原則：
- 復用 KlineStorageManager，避免重複造輪子
- 支援兩種輸入：symbol/timeframe 或直接 DataFrame
- 完整的錯誤處理和日誌記錄
- 簡單的緩存機制避免重複讀取
- 數據驗證確保下游指標計算正確
"""

import pandas as pd
from typing import Dict, Union, Optional, Tuple
import logging
from pathlib import Path

from momentum.DataExtraction.kline_storage import KlineStorageManager
from .types import DataSourceEnum

logger = logging.getLogger(__name__)


class DataSourceManager:
    """
    數據源管理器

    統一管理從 HDF5 讀取K線數據的各種數據源。
    支援從 symbol/timeframe 讀取或直接傳入 DataFrame。

    Attributes:
        storage: KlineStorageManager 實例
        _cache: 簡單的數據緩存（symbol_timeframe -> DataFrame）

    Example:
        >>> manager = DataSourceManager()
        >>> # 方式1: 從 HDF5 讀取
        >>> close_data = manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)
        >>> # 方式2: 直接傳入 DataFrame
        >>> df = pd.DataFrame(...)
        >>> close_data = manager.get_data_source_from_df(df, DataSourceEnum.CLOSE)
    """

    def __init__(self, storage_manager: Optional[KlineStorageManager] = None):
        """
        初始化數據源管理器

        Args:
            storage_manager: KlineStorageManager 實例（可選，默認創建新實例）
        """
        self.storage = storage_manager or KlineStorageManager()
        self._cache: Dict[str, pd.DataFrame] = {}  # 簡單緩存

    def get_dataframe(
        self,
        symbol: str,
        timeframe: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        獲取完整的 K線 DataFrame

        Args:
            symbol: 交易對（如 "ETHUSDT"）
            timeframe: 時間框架（如 "1h"）
            use_cache: 是否使用緩存（默認 True）

        Returns:
            pd.DataFrame: K線數據

        Raises:
            ValueError: 讀取失敗時拋出
        """
        cache_key = f"{symbol}_{timeframe}"

        # 檢查緩存
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            return self._cache[cache_key]

        # 從 HDF5 讀取
        logger.info(f"Reading klines from HDF5: {symbol}/{timeframe}")
        df = self.storage.read_klines(symbol, timeframe)

        if df is None:
            error_msg = f"Failed to read klines for {symbol}/{timeframe}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 驗證數據完整性
        is_valid, error_msg = self.validate_dataframe(df)
        if not is_valid:
            logger.error(f"DataFrame validation failed: {error_msg}")
            raise ValueError(f"Invalid DataFrame: {error_msg}")

        # 更新緩存
        if use_cache:
            self._cache[cache_key] = df
            logger.debug(f"Cached data for {cache_key}")

        logger.info(f"Successfully loaded {len(df)} bars for {symbol}/{timeframe}")
        return df

    def get_data_source(
        self,
        symbol: str,
        timeframe: str,
        data_source: DataSourceEnum,
        use_cache: bool = True
    ) -> pd.Series:
        """
        獲取指定的數據源

        Args:
            symbol: 交易對（如 "ETHUSDT"）
            timeframe: 時間框架（如 "1h"）
            data_source: 數據源類型
            use_cache: 是否使用緩存

        Returns:
            pd.Series: 數據序列

        Raises:
            ValueError: 讀取失敗或列不存在時拋出

        Example:
            >>> manager = DataSourceManager()
            >>> close = manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)
            >>> print(f"Got {len(close)} data points")
        """
        df = self.get_dataframe(symbol, timeframe, use_cache)
        return self.get_data_source_from_df(df, data_source)

    def get_data_source_from_df(
        self,
        df: pd.DataFrame,
        data_source: DataSourceEnum
    ) -> pd.Series:
        """
        從 DataFrame 中提取指定數據源

        Args:
            df: K線 DataFrame
            data_source: 數據源類型

        Returns:
            pd.Series: 數據序列

        Raises:
            ValueError: 列不存在時拋出

        Example:
            >>> df = pd.read_csv("klines.csv")
            >>> close = manager.get_data_source_from_df(df, DataSourceEnum.CLOSE)
        """
        col_name = data_source.value

        if col_name not in df.columns:
            available_cols = ", ".join(df.columns)
            error_msg = f"Column '{col_name}' not found. Available: {available_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        series = df[col_name].copy()

        # 驗證數據
        is_valid, error_msg = self.validate_series(series, data_source)
        if not is_valid:
            logger.warning(f"Series validation warning for {col_name}: {error_msg}")

        return series

    def get_all_data_sources(
        self,
        symbol: str,
        timeframe: str,
        use_cache: bool = True,
        required_only: bool = False
    ) -> Dict[DataSourceEnum, pd.Series]:
        """
        獲取所有數據源

        Args:
            symbol: 交易對
            timeframe: 時間框架
            use_cache: 是否使用緩存
            required_only: 是否只返回必需的數據源（不包含可選的 quote_volume）

        Returns:
            Dict[DataSourceEnum, pd.Series]: 所有數據源的字典

        Example:
            >>> all_sources = manager.get_all_data_sources("ETHUSDT", "1h")
            >>> for ds, series in all_sources.items():
            ...     print(f"{ds.value}: {len(series)} bars")
        """
        df = self.get_dataframe(symbol, timeframe, use_cache)

        sources_to_fetch = (
            DataSourceEnum.get_required_sources() if required_only
            else DataSourceEnum.get_all_sources()
        )

        result = {}
        for ds in sources_to_fetch:
            col_name = ds.value
            if col_name in df.columns:
                result[ds] = df[col_name].copy()
            else:
                if ds != DataSourceEnum.QUOTE_VOLUME:  # quote_volume 是可選的
                    logger.warning(f"Required column {col_name} not found")

        logger.info(f"Loaded {len(result)} data sources for {symbol}/{timeframe}")
        return result

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        驗證 DataFrame 完整性

        Args:
            df: K線 DataFrame

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤信息)

        檢查項：
        - 必需列是否存在
        - 是否有空數據
        - timestamp 是否單調遞增
        - 數據類型是否正確
        """
        if df is None or len(df) == 0:
            return False, "DataFrame is empty"

        # 檢查必需列
        required_cols = [ds.value for ds in DataSourceEnum.get_required_sources()]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {missing_cols}"

        # 檢查 timestamp 單調遞增
        if 'timestamp' in df.columns:
            if not df['timestamp'].is_monotonic_increasing:
                return False, "Timestamp is not monotonic increasing"

        # 檢查價格數據完整性
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                if df[col].isna().any():
                    return False, f"Column {col} contains NaN"
                if (df[col] <= 0).any():
                    return False, f"Column {col} contains non-positive values"

        # 檢查 OHLC 邏輯
        if all(col in df.columns for col in price_cols):
            if (df['high'] < df['low']).any():
                return False, "High < Low detected"
            if (df['high'] < df['close']).any() or (df['high'] < df['open']).any():
                return False, "High is not the maximum"
            if (df['low'] > df['close']).any() or (df['low'] > df['open']).any():
                return False, "Low is not the minimum"

        # 檢查 taker_ratio 範圍
        if 'taker_ratio' in df.columns:
            if (df['taker_ratio'] < 0).any() or (df['taker_ratio'] > 1).any():
                return False, "taker_ratio out of range [0, 1]"

        return True, ""

    def validate_series(
        self,
        data: pd.Series,
        data_source: DataSourceEnum
    ) -> Tuple[bool, str]:
        """
        驗證單個數據序列

        Args:
            data: 數據序列
            data_source: 數據源類型

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤信息)
        """
        if data is None or len(data) == 0:
            return False, "Series is empty"

        # 檢查 NaN
        nan_count = data.isna().sum()
        if nan_count > 0:
            return False, f"Series contains {nan_count} NaN values"

        # 根據數據源類型做特定檢查
        if data_source in [DataSourceEnum.CLOSE, DataSourceEnum.OPEN,
                           DataSourceEnum.HIGH, DataSourceEnum.LOW]:
            # 價格數據應為正數
            if (data <= 0).any():
                return False, "Price data contains non-positive values"

        elif data_source in [DataSourceEnum.VOLUME, DataSourceEnum.TAKER_VOLUME,
                             DataSourceEnum.QUOTE_VOLUME]:
            # 成交量數據應為非負數
            if (data < 0).any():
                return False, "Volume data contains negative values"

        elif data_source == DataSourceEnum.TAKER_RATIO:
            # taker_ratio 應在 [0, 1] 範圍
            if (data < 0).any() or (data > 1).any():
                return False, "taker_ratio out of range [0, 1]"

        return True, ""

    def clear_cache(self):
        """清空緩存"""
        self._cache.clear()
        logger.info("Data cache cleared")
