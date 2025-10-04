"""
數據緩存管理器 - Phase 0
使用HDF5格式實現高速K線數據緩存

核心功能：
1. 檢查緩存覆蓋率
2. 從HDF5快速讀取K線（< 0.05秒）
3. 增量更新（只下載缺失數據）
4. 元數據管理

設計原則：
- 只加速，不改邏輯
- 方法簽名與現有API保持一致
- 完整錯誤處理，單點故障不影響整體
- 向後兼容，可隨時禁用
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union
import logging
import json
import h5py
import time
from binance.client import Client
import os

logger = logging.getLogger(__name__)


class DataCacheManager:
    """
    HDF5緩存管理器

    特性：
    - 極速讀取：< 0.05秒/年數據
    - 增量更新：只下載缺失部分
    - 錯誤恢復：HDF5損壞自動重建
    - 統計追蹤：緩存命中率實時監控
    """

    # 類常量（避免硬編碼）
    API_RATE_LIMIT_DELAY = 0.1  # API調用間隔（秒）
    CACHE_READ_WARNING_THRESHOLD = 0.1  # 緩存讀取警告閾值（秒）
    MAX_RETRY_ATTEMPTS = 3  # 最大重試次數

    # Binance時間間隔映射
    INTERVAL_MAP = {
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

    def __init__(self, cache_dir: Path = None):
        """
        初始化緩存管理器

        Args:
            cache_dir: 緩存目錄路徑，默認為 data_cache/hdf5_cache
        """
        if cache_dir is None:
            cache_dir = Path("data_cache") / "hdf5_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 元數據文件路徑
        self.metadata_file = self.cache_dir / "metadata.json"

        # 加載或初始化元數據
        self.metadata = self._load_metadata()

        # Binance客戶端（用於下載缺失數據）
        self.client = Client(
            os.getenv('BINANCE_API_KEY'),
            os.getenv('BINANCE_SECRET_KEY')
        )

        # 統計信息
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_reads = 0

        logger.info(f"緩存管理器已初始化，緩存目錄: {self.cache_dir}")

    def get_cached_klines(
        self,
        symbol: str,
        start_time: Union[str, datetime, int],
        end_time: Union[str, datetime, int],
        interval: str
    ) -> Optional[pd.DataFrame]:
        """
        從緩存讀取K線數據（極快）

        Args:
            symbol: 交易對符號
            start_time: 開始時間
            end_time: 結束時間
            interval: 時間間隔

        Returns:
            pd.DataFrame: K線數據，如果緩存未命中返回None
        """
        self.total_reads += 1

        try:
            # 轉換時間格式
            start_dt = self._normalize_time(start_time)
            end_dt = self._normalize_time(end_time)

            # 獲取HDF5文件路徑
            cache_file = self._get_cache_path(symbol, interval)

            if not cache_file.exists():
                self.cache_misses += 1
                logger.debug(f"緩存未命中: {cache_file} 不存在")
                return None

            # 驗證HDF5文件完整性
            if not self._validate_hdf5_file(cache_file):
                logger.warning(f"HDF5文件損壞，自動刪除: {cache_file}")
                cache_file.unlink()
                self.cache_misses += 1
                return None

            # 檢查緩存覆蓋率
            cached_range, missing_ranges = self._check_cache_coverage(
                symbol, start_dt, end_dt, interval
            )

            if missing_ranges:
                # 有缺失數據，緩存未完全命中
                self.cache_misses += 1
                logger.debug(
                    f"緩存部分命中: {symbol} {interval}, "
                    f"缺失 {len(missing_ranges)} 個時間段"
                )
                return None

            # 從HDF5讀取數據
            start_read = time.time()

            with pd.HDFStore(cache_file, mode='r') as store:
                df = store.get('data')

                # 篩選時間範圍
                mask = (df.index >= start_dt) & (df.index <= end_dt)
                result = df[mask].copy()

            elapsed = time.time() - start_read
            self.cache_hits += 1

            # 只在讀取過慢時警告
            if elapsed > self.CACHE_READ_WARNING_THRESHOLD:
                logger.warning(
                    f"緩存讀取較慢: {symbol} {interval}, "
                    f"{len(result)}根K線, 耗時{elapsed:.3f}秒"
                )
            else:
                logger.debug(
                    f"緩存命中: {symbol} {interval}, "
                    f"{len(result)}根K線, 耗時{elapsed:.3f}秒"
                )

            return result

        except Exception as e:
            self.cache_misses += 1
            logger.error(f"讀取緩存失敗: {symbol} {interval}, 錯誤: {e}", exc_info=True)
            return None

    def ensure_data_cached(
        self,
        symbols: List[str],
        start_time: Union[str, datetime],
        end_time: Union[str, datetime],
        interval: str
    ) -> Dict[str, int]:
        """
        確保數據已緩存，缺失則下載（同步版本）

        Args:
            symbols: 交易對列表
            start_time: 開始時間
            end_time: 結束時間
            interval: 時間間隔

        Returns:
            Dict: 統計信息 {'cached': 已緩存數, 'downloaded': 下載數, 'failed': 失敗數}
        """
        try:
            start_dt = self._normalize_time(start_time)
            end_dt = self._normalize_time(end_time)

            total_symbols = len(symbols)
            cached_count = 0
            downloaded_count = 0
            failed_count = 0

            logger.info(f"開始檢查緩存: {total_symbols}個標的")

            for idx, symbol in enumerate(symbols, 1):
                try:
                    # 檢查緩存覆蓋率
                    cached_range, missing_ranges = self._check_cache_coverage(
                        symbol, start_dt, end_dt, interval
                    )

                    if missing_ranges:
                        logger.info(
                            f"[{idx}/{total_symbols}] {symbol}: "
                            f"需下載 {len(missing_ranges)} 個缺失時間段"
                        )

                        # 下載缺失數據（同步）
                        success = self._download_missing_data_sync(
                            symbol, missing_ranges, interval
                        )

                        if success:
                            downloaded_count += 1
                        else:
                            failed_count += 1
                    else:
                        cached_count += 1
                        logger.debug(f"[{idx}/{total_symbols}] {symbol}: 緩存完整")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"處理 {symbol} 時出錯: {e}", exc_info=True)
                    continue

            # 輸出統計信息
            logger.info(
                f"緩存檢查完成: "
                f"已緩存={cached_count}, 下載={downloaded_count}, 失敗={failed_count}"
            )

            return {
                'cached': cached_count,
                'downloaded': downloaded_count,
                'failed': failed_count
            }

        except Exception as e:
            logger.error(f"ensure_data_cached 失敗: {e}", exc_info=True)
            raise

    def save_to_cache(
        self,
        symbol: str,
        data: pd.DataFrame,
        interval: str
    ) -> None:
        """
        保存數據到緩存

        Args:
            symbol: 交易對符號
            data: K線數據
            interval: 時間間隔
        """
        try:
            if data.empty:
                logger.warning(f"數據為空，跳過保存: {symbol}")
                return

            cache_file = self._get_cache_path(symbol, interval)

            # 如果緩存文件已存在，合併數據
            if cache_file.exists():
                try:
                    with pd.HDFStore(cache_file, mode='r') as store:
                        existing_data = store.get('data')

                    # 合併並去重（保留最新數據）
                    combined = pd.concat([existing_data, data])
                    combined = combined[~combined.index.duplicated(keep='last')]
                    combined = combined.sort_index()

                    data_to_save = combined
                    logger.debug(f"合併緩存數據: {symbol}, 新增{len(data)}根K線")

                except Exception as e:
                    logger.warning(f"讀取現有緩存失敗，創建新緩存: {e}")
                    # 如果現有緩存損壞，刪除並重新創建
                    try:
                        cache_file.unlink()
                    except:
                        pass
                    data_to_save = data
            else:
                data_to_save = data

            # 保存到HDF5（使用壓縮）
            with pd.HDFStore(cache_file, mode='w', complevel=9, complib='blosc') as store:
                store.put('data', data_to_save, format='table')

            # 更新元數據
            self._update_metadata(symbol, interval, data_to_save)

            logger.info(
                f"數據已緩存: {symbol} {interval}, 共{len(data_to_save)}根K線"
            )

        except Exception as e:
            logger.error(f"保存緩存失敗: {symbol} {interval}, 錯誤: {e}", exc_info=True)
            # 不拋出異常，避免影響主流程

    def get_cache_stats(self) -> Dict:
        """
        獲取緩存統計信息

        Returns:
            Dict: 統計數據
        """
        hit_rate = (self.cache_hits / self.total_reads * 100) if self.total_reads > 0 else 0

        return {
            'total_reads': self.total_reads,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'cached_symbols': len(self.metadata)
        }

    def _check_cache_coverage(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> Tuple[Optional[Tuple[datetime, datetime]], List[Tuple[datetime, datetime]]]:
        """
        檢查緩存覆蓋率

        此方法計算請求的時間範圍與已緩存範圍的交集和差集

        Args:
            symbol: 交易對符號
            start_time: 請求開始時間
            end_time: 請求結束時間
            interval: 時間間隔

        Returns:
            (已緩存範圍, 缺失範圍列表)
            - 已緩存範圍: (cached_start, cached_end) 或 None
            - 缺失範圍列表: [(start1, end1), (start2, end2), ...]
        """
        try:
            # 從元數據獲取緩存信息
            cache_key = f"{symbol}_{interval}"

            if cache_key not in self.metadata:
                # 沒有任何緩存
                return None, [(start_time, end_time)]

            cache_info = self.metadata[cache_key]
            cached_start = datetime.fromisoformat(cache_info['start_time'])
            cached_end = datetime.fromisoformat(cache_info['end_time'])

            # 檢查請求範圍是否完全在緩存範圍內
            if cached_start <= start_time and cached_end >= end_time:
                # 完全覆蓋
                return (cached_start, cached_end), []

            # 計算缺失範圍
            missing_ranges = []

            if start_time < cached_start:
                # 前面缺失
                missing_ranges.append((start_time, min(cached_start, end_time)))

            if end_time > cached_end:
                # 後面缺失
                missing_ranges.append((max(cached_end, start_time), end_time))

            return (cached_start, cached_end), missing_ranges

        except Exception as e:
            logger.error(f"檢查緩存覆蓋率失敗: {e}", exc_info=True)
            # 保守處理：假設全部缺失
            return None, [(start_time, end_time)]

    def _download_missing_data_sync(
        self,
        symbol: str,
        missing_ranges: List[Tuple[datetime, datetime]],
        interval: str
    ) -> bool:
        """
        下載缺失數據（同步版本）

        Args:
            symbol: 交易對符號
            missing_ranges: 缺失時間範圍列表
            interval: 時間間隔

        Returns:
            bool: 是否全部下載成功
        """
        try:
            binance_interval = self.INTERVAL_MAP.get(interval)
            if not binance_interval:
                raise ValueError(f"不支持的時間間隔: {interval}")

            success_count = 0
            total_ranges = len(missing_ranges)

            # 逐個下載缺失範圍
            for idx, (start_dt, end_dt) in enumerate(missing_ranges, 1):
                try:
                    logger.info(
                        f"下載 {symbol} [{idx}/{total_ranges}]: "
                        f"{start_dt.strftime('%Y-%m-%d')} 到 {end_dt.strftime('%Y-%m-%d')}"
                    )

                    # 調用Binance API
                    klines = self.client.get_historical_klines(
                        symbol=symbol,
                        interval=binance_interval,
                        start_str=start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        end_str=end_dt.strftime('%Y-%m-%d %H:%M:%S')
                    )

                    if not klines:
                        logger.warning(f"未獲取到數據: {symbol} {start_dt}-{end_dt}")
                        continue

                    # 轉換為DataFrame
                    df = self._process_klines_to_dataframe(klines)

                    if not df.empty:
                        # 保存到緩存
                        self.save_to_cache(symbol, df, interval)
                        success_count += 1

                    # API限速（使用類常量）
                    time.sleep(self.API_RATE_LIMIT_DELAY)

                except Exception as e:
                    logger.error(
                        f"下載失敗: {symbol} {start_dt}-{end_dt}, 錯誤: {e}",
                        exc_info=True
                    )
                    # 單個範圍失敗不影響其他範圍
                    continue

            return success_count == total_ranges

        except Exception as e:
            logger.error(f"_download_missing_data_sync 失敗: {e}", exc_info=True)
            return False

    def _process_klines_to_dataframe(self, klines: List) -> pd.DataFrame:
        """
        將Binance K線數據轉換為DataFrame

        Args:
            klines: Binance API返回的K線數據

        Returns:
            pd.DataFrame: 標準化的K線數據
        """
        if not klines:
            return pd.DataFrame()

        # 創建DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        # 處理數據類型
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        for col in ['open', 'high', 'low', 'close', 'volume',
                   'quote_asset_volume', 'taker_buy_base_asset_volume',
                   'taker_buy_quote_asset_volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.set_index('timestamp', inplace=True)

        # 移除最後一根可能不完整的K線
        if not df.empty:
            df = df.iloc[:-1]

        return df

    def _validate_hdf5_file(self, file_path: Path) -> bool:
        """
        驗證HDF5文件完整性

        Args:
            file_path: HDF5文件路徑

        Returns:
            bool: 文件是否有效
        """
        try:
            with pd.HDFStore(file_path, mode='r') as store:
                # 嘗試讀取數據
                _ = store.get('data')
            return True
        except Exception:
            return False

    def _get_cache_path(self, symbol: str, interval: str) -> Path:
        """獲取緩存文件路徑"""
        filename = f"{symbol}_{interval}.h5"
        return self.cache_dir / filename

    def _normalize_time(self, time_input: Union[str, datetime, int]) -> datetime:
        """
        標準化時間格式

        Args:
            time_input: 字符串、datetime或時間戳

        Returns:
            datetime: 標準化後的datetime對象
        """
        if isinstance(time_input, datetime):
            return time_input
        elif isinstance(time_input, str):
            return pd.to_datetime(time_input)
        elif isinstance(time_input, int):
            # 假設是毫秒時間戳
            return pd.to_datetime(time_input, unit='ms')
        else:
            raise ValueError(f"不支持的時間格式: {type(time_input)}")

    def _load_metadata(self) -> Dict:
        """加載元數據"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            logger.warning(f"加載元數據失敗: {e}")
            return {}

    def _save_metadata(self) -> None:
        """保存元數據"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存元數據失敗: {e}")

    def _update_metadata(
        self,
        symbol: str,
        interval: str,
        data: pd.DataFrame
    ) -> None:
        """更新元數據"""
        try:
            cache_key = f"{symbol}_{interval}"

            self.metadata[cache_key] = {
                'symbol': symbol,
                'interval': interval,
                'start_time': data.index.min().isoformat(),
                'end_time': data.index.max().isoformat(),
                'total_bars': len(data),
                'last_update': datetime.now().isoformat()
            }

            self._save_metadata()

        except Exception as e:
            logger.error(f"更新元數據失敗: {e}")

    def clear_cache(self, symbol: str = None, interval: str = None) -> None:
        """
        清理緩存

        Args:
            symbol: 如果指定，只清理該交易對
            interval: 如果指定，只清理該時間間隔
        """
        try:
            if symbol and interval:
                # 清理特定緩存
                cache_file = self._get_cache_path(symbol, interval)
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info(f"已清理緩存: {symbol} {interval}")

                # 更新元數據
                cache_key = f"{symbol}_{interval}"
                if cache_key in self.metadata:
                    del self.metadata[cache_key]
                    self._save_metadata()
            else:
                # 清理所有緩存
                for cache_file in self.cache_dir.glob("*.h5"):
                    cache_file.unlink()

                self.metadata = {}
                self._save_metadata()

                logger.info("已清理所有緩存")

        except Exception as e:
            logger.error(f"清理緩存失敗: {e}")
