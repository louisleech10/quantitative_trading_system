"""
數據緩存管理器 - Phase 0 + 錯誤處理增強
使用HDF5格式實現高速K線數據緩存

核心功能：
1. 檢查緩存覆蓋率
2. 從HDF5快速讀取K線（< 0.05秒）
3. 增量更新（只下載缺失數據）
4. 元數據管理
5. 智能錯誤處理和重試（新增）
6. 詳細失敗報告（新增）

設計原則：
- 只加速，不改邏輯
- 方法簽名與現有API保持一致
- 完整錯誤處理，單點故障不影響整體
- 向後兼容，可隨時禁用
- 失敗透明化（不靜默丟棄）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import json
import h5py
import time
from binance.client import Client
import os

logger = logging.getLogger(__name__)


class CacheFailureType(Enum):
    """緩存錯誤類型分類"""
    NETWORK_ERROR = "network_error"
    API_LIMIT = "api_limit"
    DATA_NOT_FOUND = "data_not_found"
    HDF5_ERROR = "hdf5_error"
    INVALID_SYMBOL = "invalid_symbol"
    UNKNOWN = "unknown"


@dataclass
class CacheFailureRecord:
    """緩存失敗記錄結構"""
    symbol: str
    error_type: str
    error_message: str
    error_trace: str = ""
    severity: str = "transient"  # transient, permanent, critical
    retry_count: int = 0
    first_failed_at: str = ""
    last_retry_at: str = ""
    operation: str = ""  # 'download', 'save', 'read'
    is_recoverable: bool = True

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)


# 緩存操作重試配置
CACHE_RETRY_CONFIG = {
    CacheFailureType.NETWORK_ERROR: {
        'max_retries': 3,
        'backoff_base': 1,
        'description': '網絡問題，將重試'
    },
    CacheFailureType.API_LIMIT: {
        'max_retries': 2,
        'backoff_base': 5,
        'description': 'API限流，等待後重試'
    },
    CacheFailureType.DATA_NOT_FOUND: {
        'max_retries': 0,
        'description': '數據不存在，跳過'
    },
    CacheFailureType.HDF5_ERROR: {
        'max_retries': 1,
        'backoff_base': 0.5,
        'description': 'HDF5錯誤，嘗試重建'
    },
    CacheFailureType.INVALID_SYMBOL: {
        'max_retries': 0,
        'description': '無效symbol，跳過'
    },
    CacheFailureType.UNKNOWN: {
        'max_retries': 1,
        'backoff_base': 2,
        'description': '未知錯誤，嘗試重試一次'
    }
}


def classify_cache_error(error: Exception) -> CacheFailureType:
    """
    錯誤分類函數

    Args:
        error: 異常對象

    Returns:
        CacheFailureType: 錯誤類型
    """
    error_msg = str(error).lower()
    error_type_name = type(error).__name__.lower()

    # 網絡錯誤
    if any(keyword in error_msg for keyword in ['timeout', 'connection', 'network', 'unreachable']):
        return CacheFailureType.NETWORK_ERROR

    if any(keyword in error_type_name for keyword in ['timeout', 'connection']):
        return CacheFailureType.NETWORK_ERROR

    # API限流
    if any(keyword in error_msg for keyword in ['rate limit', 'too many requests', '429', '418']):
        return CacheFailureType.API_LIMIT

    # 無效symbol（優先於數據不存在，因為關鍵字更具體）
    if any(keyword in error_msg for keyword in ['invalid symbol', 'symbol not found', 'unknown symbol']):
        return CacheFailureType.INVALID_SYMBOL

    # 數據不存在
    if any(keyword in error_msg for keyword in ['no data', 'not found', 'empty', 'missing']):
        return CacheFailureType.DATA_NOT_FOUND

    # HDF5錯誤
    if any(keyword in error_msg for keyword in ['hdf5', 'h5py', 'corrupt', 'invalid hdf5']):
        return CacheFailureType.HDF5_ERROR

    # 未知錯誤
    return CacheFailureType.UNKNOWN


def calculate_cache_backoff_delay(error_type: CacheFailureType, attempt: int) -> float:
    """
    計算重試延遲時間

    Args:
        error_type: 錯誤類型
        attempt: 當前嘗試次數（0-based）

    Returns:
        float: 延遲秒數
    """
    config = CACHE_RETRY_CONFIG[error_type]

    if 'backoff_base' not in config:
        return 0

    base = config['backoff_base']

    # API限流使用固定延遲
    if error_type == CacheFailureType.API_LIMIT:
        return base

    # 其他使用指數退避: base * 2^attempt
    return base * (2 ** attempt)


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
        確保數據已緩存，缺失則下載（同步版本，含智能重試和失敗追蹤）

        Args:
            symbols: 交易對列表
            start_time: 開始時間
            end_time: 結束時間
            interval: 時間間隔

        Returns:
            Dict: 統計信息 {
                'cached': 已緩存數,
                'downloaded': 下載數,
                'failed': 失敗數,
                'failed_records': 失敗記錄列表,
                'retry_stats': 重試統計
            }
        """
        try:
            start_dt = self._normalize_time(start_time)
            end_dt = self._normalize_time(end_time)

            total_symbols = len(symbols)
            cached_count = 0
            downloaded_count = 0

            # 失敗追蹤
            failed_records = []
            retry_stats = {
                'total_retries': 0,
                'successful_retries': 0,
                'failed_retries': 0
            }

            logger.info(f"開始檢查緩存: {total_symbols}個標的")

            for idx, symbol in enumerate(symbols, 1):
                first_failed_at = None
                symbol_success = False

                # 智能重試循環（最多10次總嘗試）
                for attempt in range(10):
                    try:
                        # 檢查緩存覆蓋率
                        cached_range, missing_ranges = self._check_cache_coverage(
                            symbol, start_dt, end_dt, interval
                        )

                        if missing_ranges:
                            if attempt == 0:
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
                                symbol_success = True

                                # 如果之前失敗過，記錄重試成功
                                if attempt > 0:
                                    retry_stats['successful_retries'] += 1
                                    logger.info(f"{symbol} 第{attempt+1}次嘗試成功")

                                break  # 成功，跳出重試循環
                            else:
                                # 下載失敗，拋出異常進入重試邏輯
                                raise Exception("下載失敗")
                        else:
                            # 緩存完整
                            cached_count += 1
                            symbol_success = True
                            logger.debug(f"[{idx}/{total_symbols}] {symbol}: 緩存完整")
                            break

                    except Exception as e:
                        # 記錄首次失敗時間
                        if first_failed_at is None:
                            first_failed_at = datetime.now().isoformat()

                        # 錯誤分類
                        error_type = classify_cache_error(e)
                        retry_config = CACHE_RETRY_CONFIG[error_type]
                        max_retries = retry_config.get('max_retries', 0)

                        # 判斷是否應該重試
                        if attempt < max_retries:
                            # 計算延遲
                            delay = calculate_cache_backoff_delay(error_type, attempt)
                            retry_stats['total_retries'] += 1

                            logger.warning(
                                f"[{idx}/{total_symbols}] {symbol} 失敗 "
                                f"({error_type.value}), "
                                f"第{attempt+1}次嘗試失敗，"
                                f"{delay}秒後重試（最多{max_retries}次）: {e}"
                            )

                            time.sleep(delay)
                            continue  # 重試

                        else:
                            # 最終失敗，記錄失敗
                            retry_stats['failed_retries'] += 1

                            failure = self._create_cache_failure_record(
                                symbol=symbol,
                                error=e,
                                error_type=error_type,
                                retry_count=attempt + 1,
                                first_failed_at=first_failed_at,
                                operation='download'
                            )

                            failed_records.append(failure.to_dict())

                            logger.error(
                                f"[{idx}/{total_symbols}] {symbol} "
                                f"重試{attempt+1}次後最終失敗 ({error_type.value}): {e}",
                                exc_info=True
                            )

                            break  # 不再重試

            # 輸出終端總結
            logger.info("="*60)
            logger.info("緩存下載完成總結")
            logger.info("="*60)
            logger.info(
                f"✅ 成功: {cached_count + downloaded_count}/{total_symbols} "
                f"(已緩存{cached_count}, 新下載{downloaded_count})"
            )
            logger.info(f"❌ 失敗: {len(failed_records)}/{total_symbols}")
            logger.info(
                f"🔄 重試: {retry_stats['total_retries']}次 "
                f"(成功{retry_stats['successful_retries']}次, "
                f"失敗{retry_stats['failed_retries']}次)"
            )

            # 如果有失敗，輸出失敗詳情
            if failed_records:
                logger.warning("="*60)
                logger.warning("失敗詳情 (前5個):")
                logger.warning("="*60)

                for i, failure in enumerate(failed_records[:5], 1):
                    logger.warning(
                        f"{i}. {failure['symbol']} [{failure['error_type']}]\n"
                        f"   錯誤: {failure['error_message']}\n"
                        f"   重試: {failure['retry_count']}次\n"
                        f"   嚴重性: {failure['severity']}"
                    )

                if len(failed_records) > 5:
                    logger.warning(f"... 還有 {len(failed_records)-5} 個失敗")

                # 保存失敗報告
                try:
                    report_path = self._save_cache_failure_report(
                        failed_records,
                        retry_stats,
                        symbols
                    )
                    logger.warning(f"\n📄 完整失敗報告已保存: {report_path}")
                except Exception as report_error:
                    logger.error(f"保存失敗報告時出錯: {report_error}", exc_info=True)

            return {
                'cached': cached_count,
                'downloaded': downloaded_count,
                'failed': len(failed_records),
                'failed_records': failed_records,
                'retry_stats': retry_stats
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

    def _create_cache_failure_record(
        self,
        symbol: str,
        error: Exception,
        error_type: CacheFailureType,
        retry_count: int,
        first_failed_at: str,
        operation: str
    ) -> CacheFailureRecord:
        """
        創建緩存失敗記錄

        Args:
            symbol: 交易對符號
            error: 異常對象
            error_type: 錯誤類型
            retry_count: 重試次數
            first_failed_at: 首次失敗時間
            operation: 操作類型 ('download', 'save', 'read')

        Returns:
            CacheFailureRecord: 失敗記錄
        """
        import traceback

        # 判斷嚴重性和可恢復性
        severity = "transient"
        is_recoverable = True

        if error_type == CacheFailureType.INVALID_SYMBOL:
            severity = "permanent"
            is_recoverable = False
        elif error_type == CacheFailureType.DATA_NOT_FOUND:
            severity = "permanent"
            is_recoverable = False
        elif error_type in [CacheFailureType.NETWORK_ERROR, CacheFailureType.API_LIMIT]:
            severity = "transient"
            is_recoverable = True
        elif error_type == CacheFailureType.HDF5_ERROR:
            severity = "transient"
            is_recoverable = True

        return CacheFailureRecord(
            symbol=symbol,
            error_type=error_type.value,
            error_message=str(error),
            error_trace=traceback.format_exc(),
            severity=severity,
            retry_count=retry_count,
            first_failed_at=first_failed_at,
            last_retry_at=datetime.now().isoformat(),
            operation=operation,
            is_recoverable=is_recoverable
        )

    def _save_cache_failure_report(
        self,
        failed_records: List[Dict],
        retry_stats: Dict,
        total_symbols: List[str]
    ) -> str:
        """
        保存失敗報告到JSON文件

        Args:
            failed_records: 失敗記錄列表
            retry_stats: 重試統計
            total_symbols: 總symbol列表

        Returns:
            str: 保存的文件路徑
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 創建報告目錄
        report_dir = Path("data_cache") / "failure_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        # 報告文件路徑
        report_file = report_dir / f"cache_failure_{timestamp}.json"

        # 統計錯誤類型
        error_types = {}
        for failure in failed_records:
            error_type = failure['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # 生成建議
        recommendations = []

        if error_types.get(CacheFailureType.NETWORK_ERROR.value, 0) > 0:
            count = error_types[CacheFailureType.NETWORK_ERROR.value]
            recommendations.append(
                f"⚠️  {count}個symbols因網絡問題失敗，建議檢查網絡後重試"
            )

        if error_types.get(CacheFailureType.API_LIMIT.value, 0) > 0:
            count = error_types[CacheFailureType.API_LIMIT.value]
            recommendations.append(
                f"⏱️  {count}個symbols因API限流失敗，建議稍後重試或降低並發"
            )

        if error_types.get(CacheFailureType.DATA_NOT_FOUND.value, 0) > 0:
            count = error_types[CacheFailureType.DATA_NOT_FOUND.value]
            recommendations.append(
                f"💡 {count}個symbols數據不存在，建議調整時間範圍或排除這些symbols"
            )

        if error_types.get(CacheFailureType.HDF5_ERROR.value, 0) > 0:
            count = error_types[CacheFailureType.HDF5_ERROR.value]
            recommendations.append(
                f"🔧 {count}個symbols因HDF5錯誤失敗，建議清理緩存後重試"
            )

        if error_types.get(CacheFailureType.INVALID_SYMBOL.value, 0) > 0:
            count = error_types[CacheFailureType.INVALID_SYMBOL.value]
            recommendations.append(
                f"❌ {count}個symbols無效，建議從列表中排除"
            )

        # 創建報告數據
        report_data = {
            'metadata': {
                'timestamp': timestamp,
                'total_symbols': len(total_symbols),
                'operation': 'cache_download'
            },
            'summary': {
                'success_count': len(total_symbols) - len(failed_records),
                'failed_count': len(failed_records),
                'retry_total': retry_stats['total_retries'],
                'retry_successful': retry_stats['successful_retries'],
                'retry_failed': retry_stats['failed_retries']
            },
            'failure_breakdown': error_types,
            'failed_symbols': failed_records,
            'recommendations': recommendations
        }

        # 保存到文件
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        # 同時保存失敗symbols列表（方便重試）
        failed_symbols_file = report_dir / f"failed_symbols_{timestamp}.json"
        failed_symbols_data = {
            'failed_symbols': [f['symbol'] for f in failed_records],
            'recoverable_symbols': [
                f['symbol'] for f in failed_records if f['is_recoverable']
            ],
            'permanent_failed_symbols': [
                f['symbol'] for f in failed_records if not f['is_recoverable']
            ]
        }

        with open(failed_symbols_file, 'w', encoding='utf-8') as f:
            json.dump(failed_symbols_data, f, indent=2, ensure_ascii=False)

        logger.info(f"失敗symbols列表已保存: {failed_symbols_file}")

        return str(report_file)
