"""
K線數據整合服務 - 統一數據獲取接口
整合下載、存儲、讀取為統一服務，提供智能緩存管理

核心功能：
1. 統一數據獲取接口（get_kline_data）
2. 智能緩存檢查（HDF5已有 → 直接讀取）
3. 缺失數據自動下載（HDF5缺失 → 自動下載並存入）
4. 增量更新邏輯（部分命中 → 只下載缺失部分）
5. 數據完整性驗證（檢查timestamp連續性和gap）

設計原則：
- 單一職責：協調存儲和下載，不重複實作底層邏輯
- 智能緩存：優先使用HDF5，減少API調用
- 數據完整性：確保返回的數據連續、無gap
- 性能目標：讀取100根K線 < 100ms
- 錯誤透明：清晰LOG記錄決策過程

依賴關係：
- KlineStorageManager（任務1.1）：提供HDF5存儲能力
- KlineDownloadService（任務1.2）：提供API下載能力
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.config import settings
from api.core.logging import get_logger
from momentum.factories import (
    create_binance_provider,
    create_kline_download_service,
    create_kline_storage_manager,
)

logger = get_logger("api.kline_data_service")


class KlineDataService:
    """
    K線數據整合服務

    提供統一的K線數據獲取接口，自動處理緩存和下載邏輯

    使用場景：
    1. 圖表視覺化：獲取案例前後N根K線
    2. 指標計算：批量獲取多個symbol的K線
    3. ML訓練：大規模K線數據準備
    """

    def __init__(
        self,
        storage_manager: Optional[object] = None,
        download_service: Optional[object] = None,
        cache_dir: Optional[str] = None,
        default_source: str = "binance"
    ):
        """
        初始化K線數據整合服務

        Args:
            storage_manager: K線存儲管理器（任務1.1），若為None則自動創建
            download_service: K線下載服務（任務1.2），若為None則自動創建
            cache_dir: 緩存目錄路徑，若為None則使用設定檔
            default_source: 預設數據源（'binance', 'okx'等）
        """
        self.default_source = default_source

        # 初始化存儲管理器
        if storage_manager is None:
            if cache_dir is None:
                cache_dir = str(settings.kline_cache_dir)
            self.storage_manager = create_kline_storage_manager(cache_dir=cache_dir)
            logger.info(f"Created KlineStorageManager with cache_dir: {cache_dir}")
        else:
            self.storage_manager = storage_manager
            logger.info("Using provided KlineStorageManager")

        # 初始化下載服務
        if download_service is None:
            self.download_service = create_kline_download_service(
                storage_manager=self.storage_manager
            )

            # 註冊Binance Provider
            try:
                binance_provider = create_binance_provider()
                self.download_service.registry.register('binance', binance_provider)
                logger.info("Registered Binance provider")
            except Exception as e:
                logger.warning(f"Failed to register Binance provider: {e}")
        else:
            self.download_service = download_service
            logger.info("Using provided KlineDownloadService")

        logger.info(
            f"KlineDataService initialized (default_source={default_source})"
        )


    def get_kline_data(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        source: Optional[str] = None,
        validate_integrity: bool = True
    ) -> pd.DataFrame:
        """
        獲取K線數據（統一入口）

        智能決策邏輯：
        - 情況A：完全命中緩存 → 直接從HDF5讀取
        - 情況B：完全缺失 → 下載並存入HDF5
        - 情況C：部分命中 → 增量下載缺失部分

        Args:
            symbol: 交易對symbol（如'ETHUSDT'）
            timeframe: 時間框架（'1h', '4h', '1d'等）
            start_time: 開始時間（必須使用UTC時區，datetime對象）
            end_time: 結束時間（必須使用UTC時區，datetime對象）
            source: 數據源（若為None則使用default_source）
            validate_integrity: 是否驗證數據完整性

        Note:
            所有時間參數必須使用UTC時區。如果傳入本地時間可能導致數據錯誤。
            建議使用 datetime.utcnow() 或 datetime(2024, 1, 1) 等naive datetime。

        Returns:
            pd.DataFrame: K線數據，包含timestamp, OHLCV等欄位

        Raises:
            ValueError: 參數無效
            RuntimeError: 下載或存儲失敗
        """
        # 參數驗證
        if start_time >= end_time:
            raise ValueError(
                f"start_time ({start_time}) must be before end_time ({end_time})"
            )

        # P1-4 fix: 檢查是否請求未來時間
        now_utc = datetime.utcnow()
        if end_time > now_utc:
            logger.warning(
                f"end_time ({end_time}) is in the future (now: {now_utc}). "
                f"May return incomplete data or fail."
            )

        source = source or self.default_source

        # P2-1 fix: 記錄開始時間用於性能統計
        start_ts = time.time()

        logger.info(
            f"get_kline_data: {symbol}/{timeframe} "
            f"from {start_time.strftime('%Y-%m-%d %H:%M')} "
            f"to {end_time.strftime('%Y-%m-%d %H:%M')} "
            f"(source={source})"
        )

        try:
            # Step 1: 檢查HDF5緩存覆蓋情況（返回timestamp）
            has_cache, cache_start_ts, cache_end_ts = self._check_cache_coverage(
                symbol, timeframe
            )

            # 將請求時間轉為timestamp（使用calendar.timegm避免timezone問題）
            import calendar
            start_ts = calendar.timegm(start_time.timetuple())
            end_ts = calendar.timegm(end_time.timetuple())

            # Step 2: 決策邏輯（3種情況）
            if not has_cache:
                # 情況B：完全缺失 → 下載並存入
                logger.info(
                    f"Cache MISS (no data): downloading {symbol}/{timeframe}"
                )
                df = self._download_and_cache(
                    source, symbol, timeframe, start_time, end_time
                )

            elif cache_start_ts <= start_ts and end_ts <= cache_end_ts:
                # 情況A：完全命中 → 直接讀取
                logger.info(
                    f"Cache HIT (full): reading {symbol}/{timeframe} from storage"
                )
                df = self.storage_manager.read_klines(
                    symbol, timeframe, start_time, end_time
                )

                if df.empty:
                    logger.warning(
                        f"Cache metadata exists but read returned empty, "
                        f"falling back to download"
                    )
                    df = self._download_and_cache(
                        source, symbol, timeframe, start_time, end_time
                    )

            else:
                # 情況C：部分命中 → 增量下載
                logger.info(
                    f"Cache PARTIAL (cache: {cache_start_ts} to {cache_end_ts}, "
                    f"request: {start_ts} to {end_ts})"
                )
                df = self._handle_partial_cache(
                    source, symbol, timeframe, start_ts, end_ts,
                    cache_start_ts, cache_end_ts
                )

            # Step 3: 數據完整性驗證
            if validate_integrity and not df.empty:
                self._validate_data_integrity(
                    df, symbol, timeframe, start_time, end_time
                )

            # Step 4: 返回結果
            # P2-1 fix: 記錄總耗時
            elapsed_ms = (time.time() - start_ts) * 1000
            logger.info(
                f"Returned {len(df)} klines for {symbol}/{timeframe} "
                f"in {elapsed_ms:.2f}ms"
            )

            # 性能目標檢查（100ms內讀取100根K線）
            if len(df) >= 100 and elapsed_ms > 100:
                logger.warning(
                    f"Performance below target: {len(df)} klines took {elapsed_ms:.2f}ms "
                    f"(target: <100ms for 100 klines)"
                )

            return df

        except Exception as e:
            logger.error(
                f"Failed to get kline data for {symbol}/{timeframe}: {e}",
                exc_info=True
            )
            raise RuntimeError(
                f"Failed to get kline data for {symbol}/{timeframe}: {e}"
            ) from e


    def _check_cache_coverage(
        self,
        symbol: str,
        timeframe: str
    ) -> Tuple[bool, Optional[int], Optional[int]]:
        """
        檢查HDF5緩存覆蓋情況

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            Tuple[bool, Optional[int], Optional[int]]:
                - has_data: 是否有緩存數據
                - cache_start_ts: 緩存開始時間戳（Unix秒，若無則None）
                - cache_end_ts: 緩存結束時間戳（Unix秒，若無則None）
        """
        try:
            metadata = self.storage_manager.get_metadata(symbol, timeframe)

            if metadata is None:
                logger.debug(f"No metadata for {symbol}/{timeframe}")
                return False, None, None

            # 從metadata提取時間範圍（已經是Unix timestamp）
            time_range_start = metadata.get('time_range_start')
            time_range_end = metadata.get('time_range_end')

            if time_range_start is None or time_range_end is None:
                logger.warning(
                    f"Metadata exists but missing time_range for {symbol}/{timeframe}"
                )
                return False, None, None

            # 直接返回timestamp（不轉datetime，避免timezone問題）
            logger.debug(
                f"Cache coverage for {symbol}/{timeframe}: "
                f"{datetime.utcfromtimestamp(time_range_start).strftime('%Y-%m-%d %H:%M')} to "
                f"{datetime.utcfromtimestamp(time_range_end).strftime('%Y-%m-%d %H:%M')} "
                f"(timestamps: {time_range_start} - {time_range_end})"
            )

            return True, time_range_start, time_range_end

        except Exception as e:
            logger.warning(
                f"Error checking cache coverage for {symbol}/{timeframe}: {e}"
            )
            return False, None, None


    def _download_and_cache(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        *,
        save_to_storage: bool = True
    ) -> pd.DataFrame:
        """
        下載K線數據並存入緩存

        Args:
            source: 數據源
            symbol: 交易對symbol
            timeframe: 時間框架
            start_time: 開始時間（UTC）
            end_time: 結束時間（UTC）

        Returns:
            pd.DataFrame: 下載的K線數據

        Raises:
            RuntimeError: 下載或存儲失敗且無緩存可用
        """
        try:
            # 下載數據（save_to_storage=True會自動存入HDF5）
            df = self.download_service.download_klines(
                source=source,
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                timeframe=timeframe,
                save_to_storage=save_to_storage  # 保存與否由呼叫端決定
            )

            if df.empty:
                logger.warning(
                    f"Downloaded data is empty for {symbol}/{timeframe} "
                    f"from {start_time} to {end_time}"
                )
            else:
                logger.info(
                    f"Downloaded and cached {len(df)} klines for {symbol}/{timeframe}"
                )

            return df

        except Exception as e:
            logger.error(
                f"Failed to download and cache {symbol}/{timeframe}: {e}",
                exc_info=True
            )

            # P1-2 fix: 嘗試從HDF5讀取部分數據作為fallback
            logger.info(
                f"Attempting to read partial data from cache as fallback..."
            )
            try:
                df_fallback = self.storage_manager.read_klines(
                    symbol, timeframe, start_time, end_time
                )
                if not df_fallback.empty:
                    logger.warning(
                        f"Download failed, returning {len(df_fallback)} cached klines "
                        f"for {symbol}/{timeframe}"
                    )
                    return df_fallback
            except Exception as fallback_error:
                logger.debug(f"Cache fallback also failed: {fallback_error}")

            # 無法下載也無緩存，拋出異常
            raise RuntimeError(
                f"Failed to download and cache {symbol}/{timeframe}: {e}"
            ) from e


    def _handle_partial_cache(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        start_ts: int,
        end_ts: int,
        cache_start_ts: int,
        cache_end_ts: int
    ) -> pd.DataFrame:
        """
        處理部分命中緩存的情況（增量下載）

        邏輯：
        1. 計算缺失區間（gap_before 和 gap_after）
        2. 下載缺失部分
        3. 讀取緩存部分
        4. 合併並去重
        5. 更新HDF5緩存

        Args:
            source: 數據源
            symbol: 交易對symbol
            timeframe: 時間框架
            start_ts: 請求開始時間戳（Unix秒）
            end_ts: 請求結束時間戳（Unix秒）
            cache_start_ts: 緩存開始時間戳（Unix秒）
            cache_end_ts: 緩存結束時間戳（Unix秒）

        Returns:
            pd.DataFrame: 合併後的完整K線數據
        """
        dfs_to_merge = []

        # 1. 計算並下載前段缺失（gap_before）
        if start_ts < cache_start_ts:
            gap_before_start = datetime.utcfromtimestamp(start_ts)
            gap_before_end = datetime.utcfromtimestamp(cache_start_ts)
            logger.info(
                f"Downloading gap_before: {gap_before_start.strftime('%Y-%m-%d %H:%M')} "
                f"to {gap_before_end.strftime('%Y-%m-%d %H:%M')} "
                f"(timestamps: {start_ts} - {cache_start_ts})"
            )

            try:
                df_before = self._download_and_cache(
                    source,
                    symbol,
                    timeframe,
                    gap_before_start,
                    gap_before_end,
                    save_to_storage=False
                )
                if not df_before.empty:
                    dfs_to_merge.append(df_before)
                    logger.debug(f"Gap_before: added {len(df_before)} klines")
                    if self.storage_manager is not None:
                        try:
                            self.storage_manager.append_klines(symbol, timeframe, df_before)
                        except Exception as storage_error:
                            logger.warning(
                                f"Failed to append gap_before data for {symbol}/{timeframe}: {storage_error}"
                            )
            except Exception as e:
                logger.error(f"Failed to download gap_before: {e}", exc_info=True)
                # 繼續嘗試其他分段

        # 2. 讀取緩存部分（cache_overlap）
        cache_overlap_start_ts = max(start_ts, cache_start_ts)
        cache_overlap_end_ts = min(end_ts, cache_end_ts)

        if cache_overlap_start_ts < cache_overlap_end_ts:
            cache_overlap_start = datetime.utcfromtimestamp(cache_overlap_start_ts)
            cache_overlap_end = datetime.utcfromtimestamp(cache_overlap_end_ts)
            logger.info(
                f"Reading cached data: {cache_overlap_start.strftime('%Y-%m-%d %H:%M')} "
                f"to {cache_overlap_end.strftime('%Y-%m-%d %H:%M')} "
                f"(timestamps: {cache_overlap_start_ts} - {cache_overlap_end_ts})"
            )

            try:
                df_cached = self.storage_manager.read_klines(
                    symbol, timeframe, cache_overlap_start, cache_overlap_end
                )
                if df_cached is not None and not df_cached.empty:
                    dfs_to_merge.append(df_cached)
                    logger.debug(f"Cached data: added {len(df_cached)} klines")
                else:
                    logger.warning(
                        f"Cache read returned empty for {symbol}/{timeframe}"
                    )
            except Exception as e:
                logger.error(f"Failed to read cached data: {e}", exc_info=True)
                # 繼續嘗試其他分段

        # 3. 計算並下載後段缺失（gap_after）
        if end_ts > cache_end_ts:
            # CRITICAL FIX: gap_after應該從cache_end的**下一根K線**開始，避免重複下載
            # cache_end_ts 是最後一根K線的開盤時間戳，下一根應該是 cache_end_ts + timeframe_seconds
            timeframe_seconds = self._get_timeframe_seconds(timeframe)
            gap_after_start_ts = cache_end_ts + timeframe_seconds
            
            # 轉為datetime供download使用
            gap_after_start = datetime.utcfromtimestamp(gap_after_start_ts)
            gap_after_end = datetime.utcfromtimestamp(end_ts)
            
            logger.info(
                f"Downloading gap_after: {gap_after_start.strftime('%Y-%m-%d %H:%M')} "
                f"to {gap_after_end.strftime('%Y-%m-%d %H:%M')} "
                f"(timestamps: {gap_after_start_ts} - {end_ts}, +{timeframe_seconds}s from cache_end)"
            )

            try:
                df_after = self._download_and_cache(
                    source,
                    symbol,
                    timeframe,
                    gap_after_start,
                    gap_after_end,
                    save_to_storage=False
                )
                if not df_after.empty:
                    dfs_to_merge.append(df_after)
                    logger.debug(f"Gap_after: added {len(df_after)} klines")
                    if self.storage_manager is not None:
                        try:
                            self.storage_manager.append_klines(symbol, timeframe, df_after)
                        except Exception as storage_error:
                            logger.warning(
                                f"Failed to append gap_after data for {symbol}/{timeframe}: {storage_error}"
                            )
            except Exception as e:
                logger.error(f"Failed to download gap_after: {e}", exc_info=True)
                # 繼續嘗試其他分段

        # 4. 合併所有數據
        if not dfs_to_merge:
            # P0-3 fix: 記錄所有分段失敗的情況
            logger.error(
                f"No data segments available to merge for {symbol}/{timeframe}. "
                f"All download/read attempts failed."
            )
            return pd.DataFrame()

        merged_df = self._merge_kline_data(dfs_to_merge)

        logger.info(
            f"Merged {len(dfs_to_merge)} segments into {len(merged_df)} klines "
            f"for {symbol}/{timeframe}"
        )

        return merged_df


    def _merge_kline_data(self, dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """
        合併多段K線數據

        邏輯：
        1. 合併所有DataFrame
        2. 按timestamp排序
        3. 去除重複的timestamp（保留第一個）

        Args:
            dfs: 多個K線DataFrame列表

        Returns:
            pd.DataFrame: 合併後的K線數據
        """
        if not dfs:
            return pd.DataFrame()

        if len(dfs) == 1:
            return dfs[0].copy()

        # 合併所有DataFrame
        merged = pd.concat(dfs, ignore_index=True)

        # 按timestamp排序
        merged = merged.sort_values('timestamp').reset_index(drop=True)

        # 去重（保留第一個）
        original_count = len(merged)
        merged = merged.drop_duplicates(subset='timestamp', keep='first')
        duplicates_removed = original_count - len(merged)

        if duplicates_removed > 0:
            logger.debug(
                f"Removed {duplicates_removed} duplicate timestamps during merge"
            )

        return merged


    def _validate_data_integrity(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """
        驗證K線數據完整性

        檢查項目：
        1. timestamp連續性（是否有gap）
        2. 數據筆數是否合理
        3. OHLC數據是否有異常

        Args:
            df: K線數據
            symbol: 交易對symbol
            timeframe: 時間框架
            start_time: 請求開始時間
            end_time: 請求結束時間

        Note:
            此方法只記錄WARNING，不拋出異常（因為某些時段可能無交易）
        """
        if df.empty:
            logger.warning(
                f"Data integrity check: empty data for {symbol}/{timeframe}"
            )
            return

        # 1. 檢查timestamp連續性
        if len(df) > 1:
            timestamps = df['timestamp'].values

            # 計算時間間隔（應該固定）
            timeframe_seconds = self._get_timeframe_seconds(timeframe)

            # 抽樣檢查前10個間隔
            check_count = min(10, len(df) - 1)
            gaps = []

            for i in range(check_count):
                gap = timestamps[i + 1] - timestamps[i]
                gaps.append(gap)

                if gap != timeframe_seconds:
                    logger.warning(
                        f"Timestamp gap detected at index {i}: "
                        f"expected {timeframe_seconds}s, got {gap}s "
                        f"({symbol}/{timeframe})"
                    )

            # 檢查整體連續性
            if gaps:
                median_gap = sorted(gaps)[len(gaps) // 2]
                if median_gap != timeframe_seconds:
                    logger.warning(
                        f"Median gap ({median_gap}s) differs from expected "
                        f"({timeframe_seconds}s) for {symbol}/{timeframe}"
                    )

        # 2. 檢查數據筆數是否合理（P2-2: 僅在DEBUG級別執行，避免不必要計算）
        if logger.isEnabledFor(logging.DEBUG):
            expected_bars = int((end_time - start_time).total_seconds() /
                               self._get_timeframe_seconds(timeframe))
            actual_bars = len(df)

            # 允許±10%的誤差（考慮到某些時段可能無交易）
            if actual_bars < expected_bars * 0.9:
                logger.warning(
                    f"Data may be incomplete: expected ~{expected_bars} bars, "
                    f"got {actual_bars} bars ({symbol}/{timeframe})"
                )

        # 3. 檢查OHLC數據異常
        if 'high' in df.columns and 'low' in df.columns:
            invalid_ohlc = df[df['high'] < df['low']]
            if len(invalid_ohlc) > 0:
                logger.error(
                    f"Found {len(invalid_ohlc)} bars with high < low "
                    f"({symbol}/{timeframe})"
                )

        logger.debug(
            f"Data integrity check passed for {symbol}/{timeframe}: "
            f"{len(df)} bars"
        )


    def _get_timeframe_seconds(self, timeframe: str) -> int:
        """
        將timeframe字串轉換為秒數

        Args:
            timeframe: 時間框架（'1h', '4h', '1d'等）

        Returns:
            int: 對應的秒數

        Raises:
            ValueError: timeframe格式無效
        """
        timeframe_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '2h': 7200,
            '4h': 14400,
            '6h': 21600,
            '12h': 43200,
            '1d': 86400,
            '1w': 604800,
        }

        if timeframe not in timeframe_map:
            raise ValueError(
                f"Invalid timeframe: '{timeframe}'. "
                f"Supported: {list(timeframe_map.keys())}"
            )

        return timeframe_map[timeframe]


# ==================== 全局單例 ====================

_kline_data_service_instance: Optional[KlineDataService] = None


def get_kline_data_service(
    cache_dir: Optional[str] = None,
    default_source: str = "binance"
) -> KlineDataService:
    """
    獲取KlineDataService單例

    Args:
        cache_dir: 緩存目錄路徑（首次創建時使用）
        default_source: 預設數據源（首次創建時使用）

    Returns:
        KlineDataService: 全局單例
    """
    global _kline_data_service_instance

    if _kline_data_service_instance is None:
        _kline_data_service_instance = KlineDataService(
            cache_dir=cache_dir,
            default_source=default_source
        )
        logger.info("Created global KlineDataService instance")

    return _kline_data_service_instance
