"""
幣安K線數據提供者

功能：
1. 從幣安API下載K線數據
2. Token Bucket速率限制（1000 requests/min）
3. 智能錯誤處理和重試（指數退避）
4. 分批下載支援（單次最多1000根K線）
5. taker_ratio計算（處理volume=0情況）
6. 數據格式轉換（幣安12欄位 → 標準8欄位）

幣安API格式：
[Open time, Open, High, Low, Close, Volume, Close time,
 Quote volume, Trades, Taker buy base, Taker buy quote, Ignore]

標準格式：
timestamp, open, high, low, close, volume, taker_buy_volume, taker_ratio
[可選: quote_volume, number_of_trades]
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import deque
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import pandas as pd
import numpy as np
import time
import calendar
import threading
import os
import logging

import sys
from pathlib import Path

# 確保可以導入父模組
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 嘗試相對導入，fallback到絕對導入
try:
    from ..kline_provider_base import KlineProviderBase
except ImportError:
    from momentum.DataExtraction.kline_provider_base import KlineProviderBase

logger = logging.getLogger(__name__)


class BinanceRateLimiter:
    """
    幣安專用速率限制器（Token Bucket算法）

    特性：
    - Token Bucket算法（平滑速率控制）
    - 線程安全（支援多線程並發）
    - 自動補充令牌
    - 阻塞式獲取（等待令牌可用）

    幣安限制：
    - 1200 requests/min（官方限制）
    - 實際設置1000 requests/min（留buffer）
    """

    def __init__(self, max_requests_per_minute: int = 1000):
        """
        初始化速率限制器

        Args:
            max_requests_per_minute: 每分鐘最大請求數
        """
        self.capacity = max_requests_per_minute
        self.tokens = float(max_requests_per_minute)
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.refill_rate = max_requests_per_minute / 60.0  # tokens per second

        self.logger = logging.getLogger(f"{__name__}.RateLimiter")
        self.logger.info(f"Rate limiter initialized: {max_requests_per_minute} req/min")

    def acquire(self, tokens: int = 1) -> bool:
        """
        獲取令牌（阻塞直到可用）- 線程安全版本

        Args:
            tokens: 需要的令牌數

        Returns:
            bool: 總是返回True（阻塞直到成功）
        """
        while True:
            with self.lock:
                # 補充令牌
                self._refill_tokens()

                # 如果令牌足夠，立即消耗並返回
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    self.logger.debug(f"Acquired {tokens} tokens, remaining: {self.tokens:.2f}")
                    return True

                # 令牌不足，計算需要等待的時間
                wait_time = (tokens - self.tokens) / self.refill_rate

            # 在鎖外等待（避免阻塞其他線程）
            self.logger.debug(
                f"Rate limit: not enough tokens, waiting {wait_time:.2f}s"
            )
            time.sleep(wait_time)
            # 循環重試（重新獲取鎖並檢查）

    def _refill_tokens(self) -> None:
        """
        補充令牌（內部方法）

        根據時間流逝自動補充令牌
        """
        now = time.time()
        elapsed = now - self.last_update

        # 計算應補充的令牌數
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)

        self.last_update = now

    def get_available_tokens(self) -> float:
        """
        獲取當前可用令牌數（不改變狀態）

        Returns:
            float: 可用令牌數
        """
        with self.lock:
            self._refill_tokens()
            return self.tokens


class BinanceProvider(KlineProviderBase):
    """
    幣安K線數據提供者

    特性：
    - 速率限制（1000 req/min）
    - 智能重試（根據錯誤類型）
    - 分批下載（單次最多1000根）
    - 錯誤分類（5種）
    - 進度追蹤
    """

    # 錯誤類型分類
    ERROR_NETWORK = "network_error"
    ERROR_API_LIMIT = "api_rate_limit"
    ERROR_INVALID_SYMBOL = "invalid_symbol"
    ERROR_DATA = "data_error"
    ERROR_UNKNOWN = "unknown"

    # 重試配置
    RETRY_CONFIG = {
        ERROR_NETWORK: {'max_retries': 3, 'backoff': 2},
        ERROR_API_LIMIT: {'max_retries': 5, 'backoff': 10},
        ERROR_INVALID_SYMBOL: {'max_retries': 0},  # 不重試
        ERROR_DATA: {'max_retries': 1, 'backoff': 1},
        ERROR_UNKNOWN: {'max_retries': 2, 'backoff': 3}
    }

    # 幣安錯誤碼映射（補充官方錯誤碼）
    BINANCE_ERROR_CODES = {
        -1003: ERROR_API_LIMIT,      # Too many requests (WAF limit)
        -1015: ERROR_API_LIMIT,      # Too many new orders
        -1021: ERROR_NETWORK,        # Timestamp outside recvWindow
        -1100: ERROR_INVALID_SYMBOL, # Illegal characters in parameter
        -1121: ERROR_INVALID_SYMBOL, # Invalid symbol
        -1125: ERROR_NETWORK,        # API key not found
        -2010: ERROR_DATA,           # New order rejected
        -2011: ERROR_DATA,           # Cancel order rejected
    }

    # timeframe映射
    TIMEFRAME_MAP = {
        '1m': Client.KLINE_INTERVAL_1MINUTE,
        '3m': Client.KLINE_INTERVAL_3MINUTE,
        '5m': Client.KLINE_INTERVAL_5MINUTE,
        '15m': Client.KLINE_INTERVAL_15MINUTE,
        '30m': Client.KLINE_INTERVAL_30MINUTE,
        '1h': Client.KLINE_INTERVAL_1HOUR,
        '2h': Client.KLINE_INTERVAL_2HOUR,
        '4h': Client.KLINE_INTERVAL_4HOUR,
        '6h': Client.KLINE_INTERVAL_6HOUR,
        '8h': Client.KLINE_INTERVAL_8HOUR,
        '12h': Client.KLINE_INTERVAL_12HOUR,
        '1d': Client.KLINE_INTERVAL_1DAY,
        '3d': Client.KLINE_INTERVAL_3DAY,
        '1w': Client.KLINE_INTERVAL_1WEEK,
        '1M': Client.KLINE_INTERVAL_1MONTH
    }

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        初始化幣安Provider

        Args:
            api_key: API密鑰（可選，讀取公開數據不需要）
            api_secret: API密鑰（可選）
        """
        super().__init__(name="Binance")

        # 初始化Binance客戶端
        self.client = Client(
            api_key or os.getenv('BINANCE_API_KEY', ''),
            api_secret or os.getenv('BINANCE_SECRET_KEY', '')
        )

        # 初始化速率限制器
        self.rate_limiter = BinanceRateLimiter(max_requests_per_minute=1000)

        self.logger.info("BinanceProvider initialized")

    def fetch_klines(self,
                     symbol: str,
                     start_time: datetime,
                     end_time: datetime,
                     timeframe: str) -> pd.DataFrame:
        """
        獲取幣安K線數據

        實作策略：
        1. 驗證參數
        2. 分批下載（單次最多1000根）
        3. 速率限制控制
        4. 錯誤處理與重試
        5. 數據格式轉換

        Args:
            symbol: 交易對（如BTCUSDT）
            start_time: 開始時間
            end_time: 結束時間
            timeframe: 時間週期（如'1h'）

        Returns:
            pd.DataFrame: 標準化K線數據

        Raises:
            ValueError: 參數錯誤
            RuntimeError: 下載失敗
        """
        # 1. 驗證timeframe
        if timeframe not in self.TIMEFRAME_MAP:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}. "
                f"Supported: {list(self.TIMEFRAME_MAP.keys())}"
            )

        binance_interval = self.TIMEFRAME_MAP[timeframe]

        # 2. 估算總批次數（用於進度顯示）
        timeframe_seconds = self._get_timeframe_seconds(timeframe)
        total_seconds = (end_time - start_time).total_seconds()
        estimated_klines = int(total_seconds / timeframe_seconds)
        estimated_batches = max(1, (estimated_klines + 999) // 1000)  # 向上取整

        all_klines = []
        current_start = start_time
        batch_count = 0

        self.logger.info(
            f"Starting download: {symbol} {timeframe} "
            f"from {start_time} to {end_time} "
            f"(estimated ~{estimated_klines} klines in ~{estimated_batches} batches)"
        )

        # 3. 分批下載
        while current_start < end_time:
            batch_count += 1

            # 計算批次結束時間（最多1000根）
            batch_end = min(
                current_start + timedelta(seconds=timeframe_seconds * 1000),
                end_time
            )

            # 計算進度百分比
            progress_pct = min(100, int((batch_count / estimated_batches) * 100))

            self.logger.info(
                f"[{progress_pct}%] Batch {batch_count}/{estimated_batches}: "
                f"{current_start.strftime('%Y-%m-%d %H:%M')} to {batch_end.strftime('%Y-%m-%d %H:%M')}"
            )

            # 速率限制
            self.rate_limiter.acquire()

            # 下載批次（帶重試）
            batch_klines = self._fetch_with_retry(
                symbol, current_start, batch_end, binance_interval
            )

            if batch_klines:
                all_klines.extend(batch_klines)
                self.logger.info(
                    f"[{progress_pct}%] Batch {batch_count}: downloaded {len(batch_klines)} klines, "
                    f"total: {len(all_klines)}"
                )

                # 更新下一批次開始時間（使用最後一根K線的時間+1）
                last_open_time = batch_klines[-1][0]
                current_start = datetime.fromtimestamp(last_open_time / 1000) + timedelta(
                    seconds=timeframe_seconds
                )
            else:
                # 沒有更多數據
                self.logger.info(f"Batch {batch_count}: no more data available")
                break

        # 4. 轉換為DataFrame
        if not all_klines:
            self.logger.warning(f"No klines found for {symbol} {timeframe}")
            return pd.DataFrame()

        df = self._convert_to_dataframe(all_klines)

        self.logger.info(
            f"Download completed: {len(df)} klines in {batch_count} batches"
        )

        return df

    def _fetch_with_retry(self,
                         symbol: str,
                         start: datetime,
                         end: datetime,
                         interval: str,
                         max_retries: Optional[int] = None) -> List:
        """
        帶重試的單批次獲取

        Args:
            symbol: 交易對
            start: 開始時間
            end: 結束時間
            interval: 幣安interval常量
            max_retries: 最大重試次數（None則根據錯誤類型決定）

        Returns:
            List: K線數據（幣安原始格式）

        Raises:
            RuntimeError: 超過最大重試次數
        """
        attempt = 0
        last_error = None

        while True:
            try:
                # 調用幣安API
                # FIX: start/end 是 naive UTC datetime，不能用.timestamp()（會用local timezone）
                # 使用calendar.timegm轉UTC timestamp
                start_ms = int(calendar.timegm(start.timetuple()) * 1000)
                end_ms = int(calendar.timegm(end.timetuple()) * 1000)
                
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=start_ms,
                    endTime=end_ms,
                    limit=1000
                )

                self.logger.debug(f"Fetched {len(klines)} klines from Binance API")
                return klines

            except BinanceAPIException as e:
                # 幣安API錯誤（含錯誤碼）
                error_type = self._classify_binance_error(e)
                config = self.RETRY_CONFIG[error_type]

                if max_retries is not None:
                    current_max = max_retries
                else:
                    current_max = config.get('max_retries', 0)

                if attempt >= current_max:
                    self.logger.error(
                        f"Max retries ({current_max}) exceeded for {symbol}: {e}"
                    )
                    raise RuntimeError(f"Failed to fetch klines after {attempt} retries") from e

                # 計算退避延遲
                delay = config.get('backoff', 1) * (2 ** attempt)
                self.logger.warning(
                    f"BinanceAPIException ({error_type}), "
                    f"retry {attempt + 1}/{current_max} in {delay}s: {e}"
                )

                time.sleep(delay)
                attempt += 1
                last_error = e

            except (BinanceRequestException, ConnectionError, TimeoutError) as e:
                # 網絡錯誤
                error_type = self.ERROR_NETWORK
                config = self.RETRY_CONFIG[error_type]

                if max_retries is not None:
                    current_max = max_retries
                else:
                    current_max = config.get('max_retries', 0)

                if attempt >= current_max:
                    self.logger.error(
                        f"Max retries ({current_max}) exceeded for {symbol}: {e}"
                    )
                    raise RuntimeError(f"Network error after {attempt} retries") from e

                delay = config.get('backoff', 2) * (2 ** attempt)
                self.logger.warning(
                    f"Network error, retry {attempt + 1}/{current_max} in {delay}s: {e}"
                )

                time.sleep(delay)
                attempt += 1
                last_error = e

            except Exception as e:
                # 未知錯誤
                self.logger.error(f"Unexpected error fetching klines: {e}", exc_info=True)
                raise RuntimeError(f"Unexpected error: {e}") from e

    def _convert_to_dataframe(self, klines: List) -> pd.DataFrame:
        """
        轉換幣安原始格式為標準DataFrame

        幣安格式（12欄位）：
        [Open time, Open, High, Low, Close, Volume, Close time,
         Quote volume, Trades, Taker buy base, Taker buy quote, Ignore]

        標準格式（8+2欄位）：
        timestamp, open, high, low, close, volume,
        taker_buy_volume, taker_ratio [, quote_volume, number_of_trades]

        Args:
            klines: 幣安K線數據

        Returns:
            pd.DataFrame: 標準化DataFrame
        """
        if not klines:
            return pd.DataFrame()

        # 創建DataFrame（幣安格式）
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades',
            'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'
        ])

        # 類型轉換
        df['timestamp'] = (df['open_time'] / 1000).astype('int64')  # 毫秒轉秒

        for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_volume', 'quote_volume']:
            df[col] = df[col].astype('float32')

        df['trades'] = df['trades'].astype('int32')

        # 計算taker_ratio（向量化，處理volume=0）
        df['taker_ratio'] = np.where(
            df['volume'] > 0,
            df['taker_buy_volume'] / df['volume'],
            0.5  # volume=0時默認0.5（中性）
        ).astype('float32')

        # 確保taker_ratio在0-1範圍
        df['taker_ratio'] = df['taker_ratio'].clip(0, 1)

        # 選擇標準欄位 + 可選欄位
        result = df[[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'taker_buy_volume', 'taker_ratio',
            'quote_volume', 'trades'  # 可選欄位
        ]].rename(columns={'trades': 'number_of_trades'})

        return result

    def _classify_binance_error(self, error: BinanceAPIException) -> str:
        """
        分類幣安API錯誤

        Args:
            error: BinanceAPIException

        Returns:
            str: 錯誤類型
        """
        error_code = error.code

        # 檢查錯誤碼映射
        if error_code in self.BINANCE_ERROR_CODES:
            return self.BINANCE_ERROR_CODES[error_code]

        # 根據錯誤訊息分類
        error_msg = str(error).lower()

        if 'rate limit' in error_msg or '429' in error_msg:
            return self.ERROR_API_LIMIT
        elif 'invalid symbol' in error_msg or '400' in error_msg:
            return self.ERROR_INVALID_SYMBOL
        elif 'timeout' in error_msg or 'connection' in error_msg:
            return self.ERROR_NETWORK
        else:
            return self.ERROR_UNKNOWN

    def _get_timeframe_seconds(self, timeframe: str) -> int:
        """
        獲取timeframe對應的秒數

        Args:
            timeframe: 時間週期（如'1h', '4h'）

        Returns:
            int: 秒數
        """
        timeframe_seconds = {
            '1m': 60,
            '3m': 180,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '2h': 7200,
            '4h': 14400,
            '6h': 21600,
            '8h': 28800,
            '12h': 43200,
            '1d': 86400,
            '3d': 259200,
            '1w': 604800,
            '1M': 2592000  # 約30天
        }

        return timeframe_seconds.get(timeframe, 3600)

    def get_rate_limit(self) -> int:
        """
        返回每分鐘請求限制

        Returns:
            int: 1000 requests/min
        """
        return 1000

    def validate_symbol(self, symbol: str) -> bool:
        """
        驗證幣安symbol格式

        幣安格式：
        - 大寫字母
        - 無分隔符
        - 長度至少6個字符（如BTCUSDT）

        Args:
            symbol: 交易對符號

        Returns:
            bool: 是否有效
        """
        if not symbol:
            return False

        # 檢查是否全大寫
        if not symbol.isupper():
            return False

        # 檢查長度
        if len(symbol) < 6:
            return False

        # 檢查只包含字母
        if not symbol.isalpha():
            return False

        return True

    def get_supported_timeframes(self) -> List[str]:
        """
        返回幣安支援的timeframe列表

        Returns:
            List[str]: 支援的timeframe
        """
        return list(self.TIMEFRAME_MAP.keys())

    def ping(self) -> bool:
        """
        檢查幣安API健康狀態

        Returns:
            bool: API是否可用
        """
        try:
            self.client.ping()
            self.logger.info("Binance API ping successful")
            return True
        except Exception as e:
            self.logger.error(f"Binance API ping failed: {e}")
            return False
