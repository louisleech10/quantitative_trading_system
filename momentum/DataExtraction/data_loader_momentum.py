import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from binance.client import Client
from typing import Optional, Dict, List, Union, Tuple
import h5py
import os
from functools import lru_cache
from pathlib import Path
import time
import threading
from functools import wraps
import asyncio
import sys


class IncompleteDownloadError(RuntimeError):
    """分批下載未能完整取得所指定區間（游標未前進／回應亂序或 stale）。

    **fail-closed**：寧可讓呼叫端看到錯誤，也不把不完整資料當成功返回並寫入快取
    （靜默截斷會污染後續所有分析；CODEX-R1-P1-03）。
    """
import json

# 確保可以導入抽象基類
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from momentum.DataExtraction.data_provider_base import DataProviderBase
except ImportError:
    from data_provider_base import DataProviderBase

try:
    from momentum.DataExtraction.kline_storage import KlineStorageManager
except ImportError:
    from kline_storage import KlineStorageManager

# 設置日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def rate_limited(max_per_second):
    """限制函數調用頻率的裝飾器"""
    min_interval = 1.0 / max_per_second
    last_called = {}

    def decorator(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            now = time.monotonic()
            key = str(args[0])
            
            if key in last_called:
                elapsed = now - last_called[key]
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                    
            last_called[key] = time.monotonic()
            return await func(*args, **kwargs)
        return wrapped
    return decorator

class DataLoader(DataProviderBase):
    """
    幣安市場數據加載器，實現了數據提供者抽象基類
    """
    def __init__(self, cache_dir: str = "data_cache", api_key: str = None, api_secret: str = None, enable_hdf5_cache: bool = True, enable_chart_downloader: bool = True):
        """
        初始化數據加載器

        Args:
            cache_dir: 緩存目錄路徑
            api_key: 幣安API密鑰，如果為None則使用環境變量
            api_secret: 幣安API密鑰，如果為None則使用環境變量
            enable_hdf5_cache: 是否啟用HDF5緩存（Phase 0），默認True
            enable_chart_downloader: 是否啟用圖表專用下載服務（任務1.2），默認True
        """
        super().__init__()
        self.client = Client(
            api_key or os.getenv('BINANCE_API_KEY'),
            api_secret or os.getenv('BINANCE_SECRET_KEY')
        )

        # 保存API credentials for chart downloader
        self._api_key = api_key
        self._api_secret = api_secret
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # V6 Legacy 清理：統一K線讀寫到 kline_cache.h5
        self.kline_storage_manager = None
        try:
            self.kline_storage_manager = KlineStorageManager(cache_dir=str(self.cache_dir))
            self.logger.info("KlineStorageManager 已啟用 (kline_cache.h5)")
        except Exception as e:
            self.logger.warning(f"無法初始化 KlineStorageManager: {e}")

        # Phase 0: HDF5緩存管理器（新增）
        self.enable_hdf5_cache = enable_hdf5_cache
        self.hdf5_cache_manager = None

        if self.enable_hdf5_cache:
            try:
                # 嘗試相對導入
                try:
                    from .data_cache_manager import DataCacheManager
                except ImportError:
                    # fallback到完整路徑導入
                    from momentum.DataExtraction.data_cache_manager import DataCacheManager

                hdf5_cache_dir = self.cache_dir / "hdf5_cache"
                self.hdf5_cache_manager = DataCacheManager(cache_dir=hdf5_cache_dir)
                self.logger.info("HDF5緩存管理器已啟用")
            except Exception as e:
                self.logger.warning(f"無法啟用HDF5緩存: {e}，將使用原有緩存")
                self.hdf5_cache_manager = None

        # 任務1.2: 圖表專用下載服務（新增）
        self.chart_downloader = None

        if enable_chart_downloader:
            try:
                # 導入下載服務（任務1.2）
                try:
                    from .kline_download_service import KlineDownloadService
                    from .providers.binance_provider import BinanceProvider
                except ImportError:
                    from momentum.DataExtraction.kline_download_service import KlineDownloadService
                    from momentum.DataExtraction.providers.binance_provider import BinanceProvider

                # 初始化KlineStorageManager
                kline_storage_dir = self.cache_dir / "kline_storage"
                kline_storage_manager = KlineStorageManager(cache_dir=str(kline_storage_dir))

                # 初始化下載服務
                self.chart_downloader = KlineDownloadService(
                    storage_manager=kline_storage_manager
                )

                # 註冊幣安Provider
                binance_provider = BinanceProvider(
                    api_key=self._api_key,
                    api_secret=self._api_secret
                )
                self.chart_downloader.registry.register('binance', binance_provider)

                self.logger.info(
                    "Chart downloader enabled with Binance provider "
                    "(rate_limit=1000 req/min)"
                )

            except Exception as e:
                self.logger.warning(
                    f"Failed to enable chart downloader: {e}，將使用原有下載方式"
                )
                self.chart_downloader = None

        # 內存緩存
        self._symbol_data_cache = {}
        self._memory_cache_size = 0
        self._max_memory_cache = 1024 * 1024 * 1024  # 1GB 內存緩存限制

        # 🔴 下載互斥鎖（CODEX-R2-P1-01／GROK-R2-P1-02／COMPOSER 必答 2①，三家全員）：
        #   `_search_single_symbol` 改 `asyncio.to_thread` 之後，同一個 loader 可被**多個並行搜尋
        #   任務**同時進入（`standalone_search_service` 是模組級 singleton，
        #   `MAX_CONCURRENT_SEARCHES` 預設 3）。改之前同步下載鎖住事件迴圈，等於**意外**把這條
        #   路徑序列化；改之後那個隱式保證消失，而 `_symbol_data_cache` 的 read-modify-write、
        #   `_memory_cache_size` 累加、`request_weight` 計數、以及 kline HDF5 的
        #   read→concat→write 全都沒有鎖。
        #   本鎖是**還原**那個被我拿掉的序列化保證，不是新增併發控制：仍在 worker 執行緒內持有，
        #   事件迴圈不受影響（liveness 測試涵蓋）。RLock 而非 Lock——同一執行緒內
        #   `get_historical_klines → _save_to_cache → _add_to_memory_cache` 會重入。
        self._loader_lock = threading.RLock()

        # API請求控制
        self.request_weight = 0
        self.last_request_time = time.time()
        self.max_requests_per_minute = 1200  # 幣安API限制

        # 交易對信息緩存
        self._symbols_info_cache = {}
        self._exchange_info_timestamp = 0
        self._exchange_info_cache = None

        # 時間間隔映射
        self.interval_map = {
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
    
    def get_historical_data(self, 
                           symbol: str,
                           start_time: Union[str, datetime],
                           end_time: Optional[Union[str, datetime]] = None,
                           interval: str = '1h') -> pd.DataFrame:
        """
        獲取歷史OHLCV數據的標準方法，實現抽象基類要求
        
        Args:
            symbol: 交易對符號
            start_time: 開始時間
            end_time: 結束時間，預設為當前時間
            interval: K線時間間隔
            
        Returns:
            pd.DataFrame: 包含OHLCV數據的DataFrame
        """
        # 🔴 整段下載（含快取讀、分頁抓取、快取寫）在 loader 鎖內完成，見 `_loader_lock` 之註解。
        #    鎖粒度刻意取「整趟下載」而非「單次 dict 突變」：真正會壞的是
        #    read-modify-write（記憶體快取的淘汰迴圈、HDF5 的 read→concat→write），
        #    只鎖單次突變擋不住那個交錯。
        with self._loader_lock:
            # 調用舊的方法並確保格式統一
            result = self.get_historical_klines(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                interval=interval
            )
        # 檢查原始獲取的數據中是否有NaN值
        if isinstance(result, pd.DataFrame) and not result.empty:
            nan_counts = result.isna().sum()
            if nan_counts.sum() > 0:
                self.logger.warning(f"幣安API原始數據中存在NaN值 ({symbol}, {interval}):")
                for col, count in nan_counts[nan_counts > 0].items():
                    self.logger.warning(f"  - {col}: {count}個NaN值")
                
                # 可選：輸出含有NaN的行
                nan_rows = result[result.isna().any(axis=1)]
                if not nan_rows.empty:
                    self.logger.warning(f"共有{len(nan_rows)}行含有NaN值")
                    if len(nan_rows) <= 5:  # 如果數量不多，可以全部輸出
                        for idx, row in nan_rows.iterrows():
                            self.logger.warning(f"NaN行 @{idx}:\n{row}")
                    else:
                        self.logger.warning(f"前3行含NaN值的數據:\n{nan_rows.head(3)}")
        
        formatted_result = self.format_output(result)
        
        # 檢查格式化後的數據
        if isinstance(formatted_result, pd.DataFrame) and not formatted_result.empty:
            nan_counts = formatted_result.isna().sum()
            if nan_counts.sum() > 0:
                self.logger.warning(f"格式化後的數據中存在NaN值 ({symbol}, {interval}):")
                for col, count in nan_counts[nan_counts > 0].items():
                    self.logger.warning(f"  - {col}: {count}個NaN值")
        
        return formatted_result
        
        #return self.format_output(result)
    
    def get_historical_klines(self, 
                             symbol: str,
                             start_time: Union[str, datetime],
                             end_time: Optional[Union[str, datetime]] = None,
                             interval: str = '1h') -> pd.DataFrame:
        """
        獲取歷史K線數據，兼容之前的接口
        
        Args:
            symbol: 交易對符號
            start_time: 開始時間
            end_time: 結束時間，預設為當前時間
            interval: K線時間間隔
            
        Returns:
            pd.DataFrame: 包含OHLCV數據的DataFrame
        """
        try:
            # 格式化交易對
            symbol = symbol.upper().strip()
            
            # 驗證時間間隔
            if interval not in self.interval_map:
                raise ValueError(f"無效的時間間隔。必須是以下之一: {list(self.interval_map.keys())}")
                
            binance_interval = self.interval_map[interval]
                
            # 轉換時間格式
            if isinstance(start_time, str):
                start_dt = pd.to_datetime(start_time)
            else:
                start_dt = start_time
                
            if end_time:
                if isinstance(end_time, str):
                    end_dt = pd.to_datetime(end_time)
                    # 若只提供日期（YYYY-MM-DD），視為當天結束而非 00:00:00
                    if len(end_time) == 10 and " " not in end_time and "T" not in end_time:
                        end_dt = end_dt + timedelta(days=1) - timedelta(milliseconds=1)
                else:
                    end_dt = end_time
            else:
                end_dt = datetime.now()
            
            self.logger.debug(f"獲取 {symbol} 的 {interval} 數據，從 {start_dt} 到 {end_dt}")

            # Phase 0: 優先嘗試從HDF5緩存獲取（極快）
            if self.hdf5_cache_manager:
                try:
                    hdf5_data = self.hdf5_cache_manager.get_cached_klines(
                        symbol, start_dt, end_dt, interval
                    )
                    if hdf5_data is not None and not hdf5_data.empty:
                        self.logger.debug(f"HDF5緩存命中: {symbol} {interval}")
                        return hdf5_data
                except Exception as e:
                    self.logger.warning(f"HDF5緩存讀取失敗: {e}，嘗試原有緩存")

            # 嘗試從原有緩存獲取（兼容性保留）
            cached_data = self._get_from_cache(symbol, start_dt, end_dt, interval)
            if cached_data is not None and not cached_data.empty:
                interval_seconds = self._interval_to_seconds(interval)
                stale_threshold = end_dt - timedelta(seconds=interval_seconds * 2)
                cached_last = cached_data.index.max()
                # 快取末端落後太多時，不直接返回，交給後續下載補齊
                if cached_last >= stale_threshold:
                    # 如果原有緩存命中，也更新到HDF5緩存
                    if self.hdf5_cache_manager:
                        try:
                            self.hdf5_cache_manager.save_to_cache(symbol, cached_data, interval)
                        except Exception as e:
                            self.logger.debug(f"更新HDF5緩存失敗: {e}")
                    return cached_data

                self.logger.info(
                    f"快取數據末端較舊，改為補下載: {symbol} {interval}, "
                    f"cached_last={cached_last}, expected_end={end_dt}"
                )



            # 計算時間範圍大小以決定是否分批獲取
            time_range = (end_dt - start_dt).total_seconds()
            max_single_request = 1000  # 幣安單次請求最大K線數
            
            # 估算時間間隔對應的秒數
            interval_seconds = self._interval_to_seconds(interval)
            estimated_candles = time_range / interval_seconds
            
            # 數據收集結果
            all_klines = []
            
            # 檢查API限制
            self._check_api_limits()
            
            if estimated_candles > max_single_request:
                # 分批獲取數據
                current_start = start_dt
                while current_start < end_dt:
                    # 計算批次結束時間
                    batch_end = min(
                        current_start + timedelta(seconds=interval_seconds * max_single_request),
                        end_dt
                    )
                    
                    # 獲取批次數據
                    batch_klines = self._fetch_klines_batch(
                        symbol, 
                        current_start,
                        batch_end,
                        binance_interval
                    )
                    
                    if batch_klines:
                        all_klines.extend(batch_klines)

                    # 更新下一批次的開始時間
                    previous_start = current_start
                    if not batch_klines:
                        # 該窗證實無資料 ⇒ 只跳過「已證實為空」的範圍，不多跳
                        # （原本固定 +1 天會吃掉窗末之後才恢復的 bar；CODEX-R1-P1-03 反例 B）
                        current_start = batch_end + timedelta(seconds=interval_seconds)
                    else:
                        # 自最後一根K線起「推進一整根」——**不可只加 1 毫秒**：
                        # 請求時間戳以「秒」為粒度送出（見 _fetch_klines_batch），毫秒會被截掉而回到同一根，
                        # 使同一窗永遠重抓 ⇒ 無窮迴圈＋同一根 K 線被重複 append（2026-08-22 UAT B1 實測）。
                        # 前提：回應依 open time 遞增且最後一筆為該頁最大值。**驗證而非假設**——
                        # 亂序／stale 回應會使「自最後一筆前進」跳過資料（CODEX-R1-P1-03 反例 A）。
                        opens = [int(k[0]) for k in batch_klines]
                        max_open = max(opens)
                        if opens != sorted(opens) or opens[-1] != max_open:
                            raise IncompleteDownloadError(
                                f"K 線回應非遞增或末筆非最大值（拒收，不得落快取）: {symbol} {interval} "
                                f"first={opens[0]} last={opens[-1]} max={max_open} n={len(opens)}"
                            )
                        current_start = (
                            pd.to_datetime(max_open, unit='ms')
                            + timedelta(seconds=interval_seconds)
                        )

                    # 機械防呆：未前進即 **fail-closed**（不可 break 後把 partial 當成功返回並落快取
                    # ——那是靜默截斷；CODEX-R1-P1-03）
                    if current_start <= previous_start:
                        raise IncompleteDownloadError(
                            f"分批下載未前進（拒收，不得落快取）: {symbol} {interval} "
                            f"current_start={previous_start} batch_end={batch_end} "
                            f"n_klines={len(batch_klines) if batch_klines else 0}"
                        )

                    # 避免API限制
                    time.sleep(0.1)
            else:
                # 一次性獲取所有數據
                all_klines = self._fetch_klines_batch(
                    symbol,
                    start_dt,
                    end_dt,
                    binance_interval
                )
            
            if not all_klines:
                self.logger.warning(f"未找到 {symbol} 的數據")
                return pd.DataFrame()
                
            # 創建DataFrame
            df = self._process_klines_to_dataframe(all_klines)
            # 僅在最後一根尚未收盤時才移除，避免固定少一根已完成K線
            df = self._drop_incomplete_last_candle(df, interval)

            # 緩存數據（更新到兩個緩存系統）
            if not df.empty:
                # 原有緩存
                self._save_to_cache(symbol, df, interval)

                # Phase 0: HDF5緩存
                if self.hdf5_cache_manager:
                    try:
                        self.hdf5_cache_manager.save_to_cache(symbol, df, interval)
                    except Exception as e:
                        self.logger.warning(f"保存到HDF5緩存失敗: {e}")

            return df
            
        except Exception as e:
            self.logger.error(f"獲取歷史K線時出錯: {str(e)}")
            raise
    
    def _fetch_klines_batch(self, symbol, start_dt, end_dt, binance_interval):
        """獲取一批K線數據"""
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # 以 epoch **毫秒**送出，不用 strftime（'%H:%M:%S' 只到秒，會把分頁推進的毫秒截掉，
                # 造成同一根 K 線被重複請求 ⇒ 無限迴圈；2026-08-22 UAT B1 實測病因）
                klines = self.client.get_historical_klines(
                    symbol=symbol,
                    interval=binance_interval,
                    start_str=str(int(pd.Timestamp(start_dt).value // 1_000_000)),
                    end_str=str(int(pd.Timestamp(end_dt).value // 1_000_000)),
                )
                
                # 更新API請求計數
                self.request_weight += 1
                self.last_request_time = time.time()
                
                return klines
                
            except Exception as e:
                retry_count += 1
                if self.handle_request_error(e, retry_count, max_retries):
                    time.sleep(2 ** retry_count)  # 指數退避
                else:
                    raise
        
        return []
    
    def _process_klines_to_dataframe(self, klines):
        """將K線數據轉換為DataFrame"""
        if not klines:
            return pd.DataFrame()
            
        # 創建DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # 處理數據
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        for col in ['open', 'high', 'low', 'close', 'volume', 
                   'quote_asset_volume', 'taker_buy_base_asset_volume', 
                   'taker_buy_quote_asset_volume']:
            df[col] = pd.to_numeric(df[col])
            
        df.set_index('timestamp', inplace=True)

        return df

    def _drop_incomplete_last_candle(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """只在最後一根K線尚未收盤時移除，避免不必要地丟失最新完整K線。"""
        if df is None or df.empty:
            return df

        try:
            interval_seconds = self._interval_to_seconds(interval)
            last_ts = df.index.max()
            now_utc = pd.Timestamp.utcnow().tz_localize(None)
            # 若最後一根的收盤時間仍在未來，代表尚未收盤
            if last_ts + timedelta(seconds=interval_seconds) > now_utc:
                return df.iloc[:-1]
            return df
        except Exception as e:
            self.logger.debug(f"檢查最後一根K線完整性失敗，保守移除最後一根: {e}")
            return df.iloc[:-1]
    
    def _interval_to_seconds(self, interval):
        """將時間間隔轉換為秒數"""
        interval_value = interval[:-1]
        interval_unit = interval[-1]
        
        try:
            value = int(interval_value)
        except ValueError:
            self.logger.error(f"無效的時間間隔格式: {interval}")
            return 3600  # 默認1小時
            
        if interval_unit == 'm':
            return value * 60
        elif interval_unit == 'h':
            return value * 3600
        elif interval_unit == 'd':
            return value * 86400
        elif interval_unit == 'w':
            return value * 604800
        elif interval_unit == 'M':
            return value * 2592000  # 假設一個月30天
        else:
            self.logger.error(f"無法識別的時間間隔單位: {interval_unit}")
            return 3600  # 默認1小時
    
    def _check_api_limits(self):
        """檢查並處理API請求限制"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # 如果在一分鐘內且接近限制，則等待
        if elapsed < 60 and self.request_weight >= (self.max_requests_per_minute * 0.95):
            wait_time = 60 - elapsed + 1  # 額外1秒緩衝
            self.logger.warning(f"接近API限制，等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
            self.request_weight = 0
            
        # 如果超過一分鐘，重置計數器
        elif elapsed >= 60:
            self.request_weight = 0
            self.last_request_time = current_time
    
    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """優化數據類型以減少內存使用"""
        # 數值列轉換為float64以確保計算更精準
        float_cols = ['open', 'high', 'low', 'close']
        if not df.empty:
            df[float_cols] = df[float_cols].astype('float64')
            
            # 成交量轉換為float64
            volume_cols = ['volume', 'quote_asset_volume', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            for col in volume_cols:
                if col in df.columns:
                    df[col] = df[col].astype('float64')
        
        return df
    
    def _get_cache_path(self, symbol: str, interval: str) -> Path:
        """獲取緩存文件路徑"""
        return self.cache_dir / f"{symbol}_{interval}.h5"
        
    def _get_from_cache(self, 
                       symbol: str,
                       start_dt: datetime,
                       end_dt: datetime,
                       interval: str) -> Optional[pd.DataFrame]:
        """從緩存中讀取數據"""
        # 檢查內存緩存
        cache_key = f"{symbol}_{interval}_{start_dt.date()}_{end_dt.date()}"
        if cache_key in self._symbol_data_cache:
            cached_data = self._symbol_data_cache[cache_key]
            # 確認時間範圍
            mask = (cached_data.index >= start_dt) & (cached_data.index <= end_dt)
            if mask.sum() > 0:  # 有數據
                return cached_data[mask]

        # 統一從 kline_cache.h5 讀取
        if self.kline_storage_manager is None:
            return None

        try:
            storage_df = self.kline_storage_manager.read_klines(
                symbol=symbol,
                timeframe=interval,
                start_time=start_dt,
                end_time=end_dt,
                validate_continuity=False,
            )
            if storage_df is None or storage_df.empty:
                return None

            result = self._from_storage_format(storage_df)
            if not result.empty:
                self._add_to_memory_cache(cache_key, result)
                return result
        except Exception as e:
            self.logger.warning(f"從 kline_cache.h5 讀取緩存失敗: {str(e)}")
                
        return None
        
    def _save_to_cache(self, symbol: str, data: pd.DataFrame, interval: str):
        """保存數據到緩存"""
        try:
            if data.empty:
                return

            if self.kline_storage_manager is None:
                self.logger.warning("KlineStorageManager 未啟用，略過緩存寫入")
                return

            # 優化數據類型
            data = self._optimize_dtypes(data)
            incoming_df = self._to_storage_format(data)

            existing_df = self.kline_storage_manager.read_klines(
                symbol=symbol,
                timeframe=interval,
                validate_continuity=False,
            )

            if existing_df is not None and not existing_df.empty:
                combined_df = pd.concat([existing_df, incoming_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
                combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            else:
                combined_df = incoming_df

            write_ok = self.kline_storage_manager.write_klines(
                symbol=symbol,
                timeframe=interval,
                df=combined_df,
                data_source="binance",
            )

            if write_ok:
                self.logger.info(f"數據已緩存到 kline_cache.h5: {symbol}/{interval}, {len(combined_df)} 行")
            else:
                self.logger.error(f"寫入 kline_cache.h5 失敗: {symbol}/{interval}")
            
        except Exception as e:
            self.logger.error(f"保存緩存失敗: {str(e)}")

    def _to_storage_format(self, data: pd.DataFrame) -> pd.DataFrame:
        """將 DataLoader 格式轉為 KlineStorageManager 所需格式。"""
        if data.empty:
            return pd.DataFrame(columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'taker_buy_volume', 'taker_ratio', 'quote_volume', 'number_of_trades'
            ])

        df = data.copy()

        if isinstance(df.index, pd.DatetimeIndex):
            timestamps = np.asarray(df.index.astype('int64') // 1_000_000_000, dtype='int64')
        elif 'timestamp' in df.columns:
            ts_series = pd.to_datetime(df['timestamp'])
            timestamps = np.asarray(ts_series.astype('int64') // 1_000_000_000, dtype='int64')
        else:
            raise ValueError("無法轉換為 storage 格式：缺少 timestamp")

        quote_col = 'quote_asset_volume' if 'quote_asset_volume' in df.columns else 'quote_volume'
        taker_base_col = (
            'taker_buy_base_asset_volume'
            if 'taker_buy_base_asset_volume' in df.columns
            else 'taker_buy_volume'
        )
        trades_col = 'number_of_trades' if 'number_of_trades' in df.columns else None

        def _as_numeric(col_name: str, default: float = 0.0) -> pd.Series:
            if col_name in df.columns:
                return pd.to_numeric(df[col_name], errors='coerce')
            return pd.Series(default, index=df.index, dtype='float64')

        out = pd.DataFrame({
            'timestamp': timestamps,
            'open': _as_numeric('open').to_numpy(),
            'high': _as_numeric('high').to_numpy(),
            'low': _as_numeric('low').to_numpy(),
            'close': _as_numeric('close').to_numpy(),
            'volume': _as_numeric('volume').to_numpy(),
            'taker_buy_volume': _as_numeric(taker_base_col, default=0.0).fillna(0.0).to_numpy(),
            'quote_volume': _as_numeric(quote_col, default=np.nan).to_numpy(),
            'number_of_trades': _as_numeric(trades_col, default=0.0).fillna(0).to_numpy(),
        })

        with np.errstate(divide='ignore', invalid='ignore'):
            out['taker_ratio'] = np.where(out['volume'] > 0, out['taker_buy_volume'] / out['volume'], 0.5)
        out['taker_ratio'] = out['taker_ratio'].clip(0, 1)

        out = out.dropna(subset=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        out = out.drop_duplicates(subset=['timestamp'], keep='last')
        out = out.sort_values('timestamp').reset_index(drop=True)
        out['timestamp'] = out['timestamp'].astype('int64')
        out['number_of_trades'] = out['number_of_trades'].astype('int64')

        return out

    def _from_storage_format(self, storage_df: pd.DataFrame) -> pd.DataFrame:
        """將 KlineStorageManager 讀取結果轉為 DataLoader 對外格式。"""
        if storage_df is None or storage_df.empty:
            return pd.DataFrame()

        df = storage_df.copy()
        if 'timestamp' not in df.columns:
            return pd.DataFrame()

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.set_index('timestamp').sort_index()

        if 'quote_volume' in df.columns and 'quote_asset_volume' not in df.columns:
            df['quote_asset_volume'] = df['quote_volume']
        if 'taker_buy_volume' in df.columns and 'taker_buy_base_asset_volume' not in df.columns:
            df['taker_buy_base_asset_volume'] = df['taker_buy_volume']
        if 'taker_buy_quote_asset_volume' not in df.columns:
            if 'quote_asset_volume' in df.columns and 'taker_ratio' in df.columns:
                df['taker_buy_quote_asset_volume'] = (
                    pd.to_numeric(df['quote_asset_volume'], errors='coerce').fillna(0.0)
                    * pd.to_numeric(df['taker_ratio'], errors='coerce').fillna(0.0)
                )
            else:
                df['taker_buy_quote_asset_volume'] = 0.0

        return df
            
    def _add_to_memory_cache(self, key: str, data: pd.DataFrame):
        """添加數據到內存緩存"""
        # 計算數據大小
        data_size = data.memory_usage(deep=True).sum()
        
        # 如果緩存即將超出限制，清理舊數據
        while self._memory_cache_size + data_size > self._max_memory_cache and self._symbol_data_cache:
            # 移除最舊的數據
            oldest_key = next(iter(self._symbol_data_cache))
            oldest_data = self._symbol_data_cache.pop(oldest_key)
            self._memory_cache_size -= oldest_data.memory_usage(deep=True).sum()
            
        # 添加新數據到緩存
        self._symbol_data_cache[key] = data
        self._memory_cache_size += data_size
        
    def clear_cache(self, older_than_days: int = 30):
        """清理舊的緩存數據"""
        try:
            # 清理文件緩存
            current_time = datetime.now()
            for cache_file in self.cache_dir.glob("*.h5"):
                # 檢查文件年齡
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if (current_time - file_time).days > older_than_days:
                    cache_file.unlink()
                    self.logger.info(f"已刪除舊緩存: {cache_file}")
                    
            # 清理內存緩存
            self._symbol_data_cache.clear()
            self._memory_cache_size = 0
            
            self.logger.info("緩存清理完成")
            
        except Exception as e:
            self.logger.error(f"清理緩存失敗: {str(e)}")
    
    def get_symbols_list(self) -> List[str]:
        """
        獲取市場中所有可用的交易對列表，實現抽象基類要求
        
        Returns:
            List[str]: 可用交易對的列表
        """
        try:
            # 檢查緩存是否需要更新
            current_time = time.time()
            if current_time - self._exchange_info_timestamp > 3600:  # 每小時更新一次
                exchange_info = self.client.get_exchange_info()
                self._exchange_info_cache = exchange_info
                self._exchange_info_timestamp = current_time
                self.logger.info("更新交易所信息緩存")
            else:
                exchange_info = self._exchange_info_cache
                
            # 提取交易對
            symbols = [
                s['symbol'] for s in exchange_info['symbols']
                if s['status'] == 'TRADING'
            ]
            
            return symbols
            
        except Exception as e:
            self.logger.error(f"獲取交易對列表失敗: {str(e)}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        獲取特定交易對的詳細信息，實現抽象基類要求
        
        Args:
            symbol: 交易對符號
            
        Returns:
            Dict: 包含交易對詳細信息的字典
        """
        try:
            # 檢查緩存
            if symbol in self._symbols_info_cache:
                return self._symbols_info_cache[symbol]
            
            # 獲取交易對信息
            symbol_info = None
            
            # 嘗試從交易所信息緩存中獲取
            if self._exchange_info_cache:
                for sym in self._exchange_info_cache['symbols']:
                    if sym['symbol'] == symbol:
                        symbol_info = sym
                        break
            
            # 如果緩存中沒有，直接獲取
            if not symbol_info:
                symbol_info = self.client.get_symbol_info(symbol)
                
            if not symbol_info:
                self.logger.warning(f"未找到交易對信息: {symbol}")
                return {}
            
            # 獲取第一筆交易時間
            try:
                # 獲取最早的一根K線
                earliest_klines = self.client.get_klines(
                    symbol=symbol,
                    interval='1d',
                    limit=1,
                    startTime=0  # 從最早的時間開始
                )
                
                if earliest_klines:
                    first_trade_time = earliest_klines[0][0]  # 第一個K線的開始時間
                else:
                    first_trade_time = None
                    
            except Exception as e:
                self.logger.error(f"獲取最早K線時出錯: {str(e)}")
                first_trade_time = None
            
            # 整理結果
            result = {
                'symbol': symbol_info['symbol'],
                'status': symbol_info['status'],
                'baseAsset': symbol_info['baseAsset'],
                'quoteAsset': symbol_info['quoteAsset'],
                'listingDate': first_trade_time,
                'permissions': symbol_info.get('permissions', [])
            }
            
            # 緩存結果
            self._symbols_info_cache[symbol] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"獲取交易對信息失敗: {str(e)}")
            return {}
    
    def get_ticker_data(self, symbol: str = None) -> Union[Dict, List[Dict]]:
        """
        獲取最新行情數據
        
        Args:
            symbol: 交易對符號，如果為None則獲取所有交易對
            
        Returns:
            Dict or List[Dict]: 行情數據
        """
        try:
            if symbol:
                return self.client.get_ticker(symbol=symbol)
            else:
                return self.client.get_all_tickers()
                
        except Exception as e:
            self.logger.error(f"獲取行情數據失敗: {str(e)}")
            return {} if symbol else []
    
    def get_exchange_time(self) -> datetime:
        """
        獲取交易所服務器時間
        
        Returns:
            datetime: 交易所服務器時間
        """
        try:
            server_time = self.client.get_server_time()
            return pd.to_datetime(server_time['serverTime'], unit='ms')
            
        except Exception as e:
            self.logger.error(f"獲取服務器時間失敗: {str(e)}")
            return datetime.now()  # 返回本地時間作為備用
    
    @lru_cache(maxsize=100)
    def get_market_depth(self, symbol: str, limit: int = 100) -> Dict:
        """
        獲取市場深度數據
        
        Args:
            symbol: 交易對符號
            limit: 獲取的深度等級數量
            
        Returns:
            Dict: 市場深度數據
        """
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)
            return depth
            
        except Exception as e:
            self.logger.error(f"獲取市場深度失敗: {str(e)}")
            return {}
    
    def get_cache_stats(self) -> dict:
        """
        獲取HDF5緩存統計信息（Phase 0）

        Returns:
            dict: 緩存統計數據，如果HDF5緩存未啟用則返回空字典
        """
        if self.hdf5_cache_manager:
            return self.hdf5_cache_manager.get_cache_stats()
        else:
            return {
                'hdf5_cache_enabled': False,
                'message': 'HDF5緩存未啟用'
            }

    def export_data_to_csv(self,
                         data: pd.DataFrame,
                         symbol: str,
                         interval: str,
                         output_dir: str = "exported_data") -> str:
        """
        將數據導出為CSV文件

        Args:
            data: 要導出的數據
            symbol: 交易對符號
            interval: 時間間隔
            output_dir: 輸出目錄

        Returns:
            str: CSV文件路徑
        """
        try:
            if data.empty:
                self.logger.warning("沒有數據可導出")
                return ""

            # 創建輸出目錄
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            # 生成文件名
            start_date = data.index.min().strftime('%Y%m%d')
            end_date = data.index.max().strftime('%Y%m%d')
            filename = f"{symbol}_{interval}_{start_date}_{end_date}.csv"
            file_path = output_path / filename

            # 將數據保存為CSV
            data.to_csv(file_path)
            self.logger.info(f"數據已導出到: {file_path}")

            return str(file_path)

        except Exception as e:
            self.logger.error(f"導出數據失敗: {str(e)}")
            return ""