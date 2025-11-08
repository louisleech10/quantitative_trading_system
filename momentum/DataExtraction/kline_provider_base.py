"""
K線數據提供者抽象基類
提供統一的數據源接口，支援多種交易所和數據源

設計原則：
- 定義統一的KlineData標準格式（8個必需欄位）
- 各數據源通過適配器模式轉換為標準格式
- 支援擴展：幣安 → OKX → 鏈上 → 台美股期
- 清晰的擴展路徑：繼承 → 實作 → 註冊 → 使用

標準數據格式（符合任務1.1 KlineStorageManager）:
- timestamp: int64 (Unix秒級時間戳)
- open, high, low, close: float32
- volume: float32
- taker_buy_volume: float32 (主動買入量)
- taker_ratio: float32 (主動買入比例，0-1)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class KlineData:
    """
    標準化K線數據模型

    必需欄位（8個）：
        timestamp: Unix秒級時間戳
        open: 開盤價
        high: 最高價
        low: 最低價
        close: 收盤價
        volume: 成交量
        taker_buy_volume: 主動買入量
        taker_ratio: 主動買入比例（0-1）

    可選欄位（擴展）：
        extra: 各數據源特有欄位（如quote_volume, number_of_trades等）
    """
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    taker_buy_volume: float
    taker_ratio: float
    extra: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式（用於DataFrame創建）

        Returns:
            Dict: 包含所有欄位的字典
        """
        base = {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'taker_buy_volume': self.taker_buy_volume,
            'taker_ratio': self.taker_ratio
        }

        # 合併擴展欄位
        if self.extra:
            base.update(self.extra)

        return base

    def validate(self) -> bool:
        """
        驗證數據合理性

        Returns:
            bool: 是否通過驗證

        Raises:
            ValueError: 數據不合理時
        """
        # 1. OHLC合理性檢查
        if not (self.low <= self.open <= self.high):
            raise ValueError(f"Invalid OHLC: open {self.open} not in [{self.low}, {self.high}]")

        if not (self.low <= self.close <= self.high):
            raise ValueError(f"Invalid OHLC: close {self.close} not in [{self.low}, {self.high}]")

        # 2. 價格必須為正
        if any(x <= 0 for x in [self.open, self.high, self.low, self.close]):
            raise ValueError("Prices must be positive")

        # 3. 成交量必須非負
        if self.volume < 0 or self.taker_buy_volume < 0:
            raise ValueError("Volumes must be non-negative")

        # 4. taker_buy_volume不能超過總volume
        if self.taker_buy_volume > self.volume:
            raise ValueError(f"taker_buy_volume {self.taker_buy_volume} > volume {self.volume}")

        # 5. taker_ratio範圍檢查
        if not (0 <= self.taker_ratio <= 1):
            raise ValueError(f"taker_ratio {self.taker_ratio} not in [0, 1]")

        return True


class KlineProviderBase(ABC):
    """
    K線數據提供者抽象基類

    所有數據源（幣安、OKX、鏈上、股票期貨等）都必須實作此接口

    核心方法（3個必須實作）：
    1. fetch_klines(): 獲取K線數據
    2. get_rate_limit(): 返回速率限制
    3. validate_symbol(): 驗證symbol格式

    可選方法（可覆寫）：
    4. get_supported_timeframes(): 返回支援的timeframe列表
    5. ping(): 健康檢查
    6. _calculate_next_batch_start(): 計算下一批次起始時間（用於多批次下載）
    
    批次下載規範：
    - 子類必須設置 batch_size 屬性（每批次最大K線數量）
    - 如需分批下載，應實現 _calculate_next_batch_start() 方法
    - 批次邊界計算必須使用計畫時間，不可依賴實際返回數據
    - 確保批次連續無縫，避免重疊或缺口
    """

    def __init__(self, name: str = "UnknownProvider", batch_size: int = 1000):
        """
        初始化Provider

        Args:
            name: Provider名稱（用於日誌和錯誤追蹤）
            batch_size: 單批次最大K線數量（默認1000，子類可覆寫）
        """
        self.name = name
        self.batch_size = batch_size
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def fetch_klines(self,
                     symbol: str,
                     start_time: datetime,
                     end_time: datetime,
                     timeframe: str) -> pd.DataFrame:
        """
        獲取K線數據（核心方法）

        Args:
            symbol: 交易對符號（各數據源格式可能不同）
            start_time: 開始時間
            end_time: 結束時間
            timeframe: 時間週期（如'1h', '4h', '1d'）

        Returns:
            pd.DataFrame: 包含標準8欄位的DataFrame
                - 必需欄位: timestamp, open, high, low, close, volume,
                           taker_buy_volume, taker_ratio
                - 可選欄位: 各數據源自行定義（如quote_volume等）

        Raises:
            ValueError: symbol或timeframe格式錯誤
            ConnectionError: 網絡連接失敗
            RuntimeError: API錯誤或其他運行時錯誤
        """
        pass

    @abstractmethod
    def get_rate_limit(self) -> int:
        """
        返回每分鐘請求限制

        Returns:
            int: 每分鐘最大請求數

        Examples:
            - 幣安: 1200 requests/min
            - OKX: 1200 requests/min (20 req/2s)
            - 鏈上: 可能無限制或依賴節點配置
        """
        pass

    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """
        驗證symbol格式是否符合此數據源

        Args:
            symbol: 交易對符號

        Returns:
            bool: 是否有效

        Examples:
            - 幣安: "BTCUSDT" (大寫，無分隔符)
            - OKX: "BTC-USDT" (大寫，使用'-')
            - 股票: "AAPL" (股票代碼)
        """
        pass

    def get_supported_timeframes(self) -> List[str]:
        """
        返回支援的timeframe列表（可選覆寫）

        Returns:
            List[str]: 支援的timeframe列表

        Note:
            默認返回常見的加密貨幣timeframes
            各數據源可以覆寫此方法提供自定義列表
        """
        return ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']

    def ping(self) -> bool:
        """
        健康檢查（可選覆寫）

        Returns:
            bool: API是否可用

        Note:
            默認實作返回True（假設可用）
            建議各數據源實作實際的ping檢查
        """
        try:
            self.logger.debug(f"Pinging {self.name}...")
            # 子類應該實作實際的API健康檢查
            # 例如：調用server_time端點
            return True
        except Exception as e:
            self.logger.warning(f"Ping failed for {self.name}: {e}")
            return False
    
    def _calculate_next_batch_start(self, 
                                    batch_end: datetime, 
                                    timeframe_seconds: int) -> datetime:
        """
        計算下一批次的起始時間（用於多批次下載）
        
        ⚠️ 關鍵設計原則：
        - 必須使用計畫的 batch_end，不可使用實際返回數據的最後時間戳
        - 確保批次連續：next_start = batch_end + 1*timeframe
        - 避免重疊或缺口
        
        Args:
            batch_end: 當前批次計畫結束時間
            timeframe_seconds: 時間框架秒數
            
        Returns:
            datetime: 下一批次起始時間
            
        Note:
            默認實現：batch_end + timeframe_seconds
            子類可根據API特性覆寫（如某些API的 startTime 為 exclusive）
        """
        return batch_end + timedelta(seconds=timeframe_seconds)

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        驗證返回的DataFrame格式是否符合標準（內部方法）

        Args:
            df: 要驗證的DataFrame

        Raises:
            ValueError: 格式不符合標準
        """
        if df.empty:
            return  # 空DataFrame是合法的（可能沒有數據）

        # 檢查必需欄位
        required_columns = [
            'timestamp', 'open', 'high', 'low', 'close',
            'volume', 'taker_buy_volume', 'taker_ratio'
        ]

        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # 檢查數據類型
        expected_dtypes = {
            'timestamp': ['int32', 'int64'],
            'open': ['float32', 'float64'],
            'high': ['float32', 'float64'],
            'low': ['float32', 'float64'],
            'close': ['float32', 'float64'],
            'volume': ['float32', 'float64'],
            'taker_buy_volume': ['float32', 'float64'],
            'taker_ratio': ['float32', 'float64']
        }

        for col, allowed_types in expected_dtypes.items():
            if df[col].dtype.name not in allowed_types:
                self.logger.warning(
                    f"Column '{col}' has type {df[col].dtype}, expected one of {allowed_types}"
                )

        # 檢查數據合理性（抽樣檢查前10行）
        sample_size = min(10, len(df))
        for idx in range(sample_size):
            row = df.iloc[idx]

            # OHLC合理性
            if not (row['low'] <= row['open'] <= row['high']):
                raise ValueError(
                    f"Row {idx}: Invalid OHLC - open {row['open']} not in [{row['low']}, {row['high']}]"
                )

            if not (row['low'] <= row['close'] <= row['high']):
                raise ValueError(
                    f"Row {idx}: Invalid OHLC - close {row['close']} not in [{row['low']}, {row['high']}]"
                )

            # 警告：無波動情況（可能是數據異常）
            if row['high'] == row['low']:
                self.logger.warning(
                    f"Row {idx}: No price movement detected (high={row['high']}, low={row['low']}). "
                    f"This may indicate data quality issues."
                )

            # taker_ratio範圍
            if not (0 <= row['taker_ratio'] <= 1):
                raise ValueError(
                    f"Row {idx}: taker_ratio {row['taker_ratio']} not in [0, 1]"
                )

            # taker_buy_volume不能超過volume
            if row['taker_buy_volume'] > row['volume']:
                raise ValueError(
                    f"Row {idx}: taker_buy_volume {row['taker_buy_volume']} > volume {row['volume']}"
                )

        # 檢查timestamp連續性（抽樣檢查）
        if len(df) > 1:
            timestamps = df['timestamp'].values
            gaps = []

            # 檢查前10個間隔（如果數據足夠）
            check_count = min(10, len(df) - 1)
            for i in range(check_count):
                gap = timestamps[i + 1] - timestamps[i]
                gaps.append(gap)

            # 檢測異常gap（與中位數差異過大）
            if gaps:
                median_gap = sorted(gaps)[len(gaps) // 2]
                for i, gap in enumerate(gaps):
                    if gap <= 0:
                        self.logger.warning(
                            f"Row {i}: Non-increasing timestamp detected (gap={gap}s)"
                        )
                    elif gap > median_gap * 2:
                        self.logger.warning(
                            f"Row {i}: Large timestamp gap detected (gap={gap}s, expected ~{median_gap}s)"
                        )

        self.logger.debug(f"DataFrame validation passed: {len(df)} rows, {len(df.columns)} columns")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__}(name='{self.name}')>"
