"""
批量K線下載服務

提供批量下載案例K線數據的異步功能
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.logging import get_logger
from api.core.config import settings
from api.models.case_models import (
    CaseRecord,
    BatchDownloadRequest,
    DownloadProgress,
    DownloadResult,
    TaskStatus
)
from api.utils.case_storage import CaseStorageManager, get_case_storage_manager
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.DataExtraction.kline_download_service import KlineDownloadService

logger = get_logger("api.batch_download_service")


class TimeRange:
    """時間範圍輔助類"""

    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

    def overlaps(self, other: 'TimeRange') -> bool:
        """檢查是否與另一個時間範圍重疊"""
        return self.start <= other.end and other.start <= self.end

    def merge(self, other: 'TimeRange') -> 'TimeRange':
        """合併兩個重疊的時間範圍"""
        return TimeRange(
            start=min(self.start, other.start),
            end=max(self.end, other.end)
        )

    def __repr__(self):
        return f"TimeRange({self.start} to {self.end})"


class BatchDownloadService:
    """
    批量K線下載服務

    功能：
    1. 創建下載任務
    2. 計算時間範圍（lookback + forward）
    3. 合併重疊時間段（優化）
    4. 異步批量下載
    5. 進度追蹤
    """

    # 時間框架秒數映射
    TIMEFRAME_SECONDS = {
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
    
    # Binance API 已知的歷史數據缺口（無法下載的時間段）
    # 這些是 Binance 平台級別的數據缺失，所有交易對都受影響
    KNOWN_DATA_GAPS = [
        {
            'start': datetime(2023, 3, 24, 13, 0, 0),  # 2023-03-24 13:00:00 UTC
            'end': datetime(2023, 3, 24, 14, 0, 0),    # 2023-03-24 14:00:00 UTC (不含)
            'reason': 'Binance 系統維護/數據缺口',
            'affects': 'all',  # 影響所有交易對
        },
        # 未來如發現其他缺口，可以在此添加
    ]

    def __init__(
        self,
        case_storage: Optional[CaseStorageManager] = None,
        kline_storage: Optional[KlineStorageManager] = None,
        download_service: Optional[KlineDownloadService] = None
    ):
        """
        初始化批量下載服務

        Args:
            case_storage: 案例存儲管理器
            kline_storage: K線存儲管理器
            download_service: K線下載服務
        """
        self.case_storage = case_storage or CaseStorageManager()
        # 使用配置的 data_cache 路徑，確保所有下載使用同一存儲位置
        self.kline_storage = kline_storage or KlineStorageManager(
            cache_dir=str(settings.data_cache_path)
        )

        if download_service:
            self.download_service = download_service
        else:
            # 創建下載服務並註冊BinanceProvider
            self.download_service = KlineDownloadService(
                storage_manager=self.kline_storage
            )

            # 註冊BinanceProvider
            try:
                from momentum.DataExtraction.providers.binance_provider import BinanceProvider
                binance_provider = BinanceProvider()
                self.download_service.registry.register('binance', binance_provider)
                logger.info("Registered BinanceProvider to KlineDownloadService")
            except Exception as e:
                logger.error(f"Failed to register BinanceProvider: {e}")
                raise

        # 任務進度追蹤：task_id → DownloadProgress
        self.tasks: Dict[str, DownloadProgress] = {}

        logger.info("BatchDownloadService initialized")


    def create_download_task(
        self,
        request: BatchDownloadRequest
    ) -> str:
        """
        創建下載任務

        Args:
            request: 批量下載請求

        Returns:
            str: 任務ID
        """
        # 生成任務ID
        task_id = f"batch_download_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 獲取要下載的案例
        if request.case_ids:
            cases = self.case_storage.get_cases(request.case_ids)
        else:
            cases = self.case_storage.get_cases()

        # 初始化進度
        progress = DownloadProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            total_cases=len(cases),
            completed_cases=0,
            failed_cases=0,
            progress_percent=0.0,
            start_time=datetime.utcnow()
        )

        self.tasks[task_id] = progress

        logger.info(
            f"Created download task {task_id} for {len(cases)} cases "
            f"(lookback={request.lookback_bars}, forward={request.forward_bars})"
        )

        return task_id


    async def execute_batch_download(
        self,
        task_id: str,
        request: BatchDownloadRequest
    ) -> DownloadResult:
        """
        執行批量下載（異步，支援並行）

        Args:
            task_id: 任務ID
            request: 批量下載請求

        Returns:
            DownloadResult: 下載結果
        """
        import asyncio

        logger.info(f"Starting batch download task: {task_id}")

        # 更新任務狀態
        progress = self.tasks[task_id]
        progress.status = TaskStatus.RUNNING

        # 獲取要下載的案例
        if request.case_ids:
            cases = self.case_storage.get_cases(request.case_ids)
        else:
            cases = self.case_storage.get_cases()

        # 按symbol分組（使用request.timeframe作為K線下載時間框架）
        grouped_cases = self._group_cases_by_symbol(cases)

        # 初始化結果統計
        downloaded_case_ids = []
        failed_case_ids = []
        error_details = {}
        skipped_cases = 0
        total_bars = 0

        # 用於線程安全的統計
        stats_lock = asyncio.Lock()

        start_time = datetime.utcnow()

        # 並行下載配置：最多5個並發下載任務
        max_concurrent_downloads = 5
        semaphore = asyncio.Semaphore(max_concurrent_downloads)

        async def download_group(symbol: str, group_cases: List[CaseRecord]):
            """下載單個分組（支援並行）"""
            nonlocal downloaded_case_ids, failed_case_ids, error_details, skipped_cases, total_bars

            # 使用request.timeframe作為K線下載時間框架（與案例的timeframe獨立）
            timeframe = request.timeframe

            async with semaphore:  # 限制並發數
                logger.info(
                    f"Processing {len(group_cases)} cases for {symbol}/{timeframe} "
                    f"(download timeframe={request.timeframe}, cases may have different timeframes)"
                )

                try:
                    # Step 1: 計算時間範圍
                    time_ranges = self._calculate_time_ranges(
                        group_cases,
                        timeframe,
                        request.lookback_bars,
                        request.forward_bars
                    )

                    # Step 2: 合併重疊時間範圍
                    merged_ranges = self._merge_overlapping_ranges(time_ranges)

                    logger.info(
                        f"Merged {len(time_ranges)} ranges into {len(merged_ranges)} "
                        f"for {symbol}/{timeframe}"
                    )

                    # Step 3: 下載合併後的時間範圍
                    for time_range in merged_ranges:
                        try:
                            # 檢查是否已存在（如果非force模式）
                            # **CRITICAL FIX**: 不只檢查metadata，還要驗證數據實際存在
                            if not request.force_redownload:
                                metadata = self.kline_storage.get_metadata(symbol, timeframe)
                                if metadata:
                                    # 驗證數據實際存在且非空
                                    total_bars = metadata.get('total_bars', 0)
                                    if total_bars > 0:
                                        # **CRITICAL FIX**: 檢查現有數據是否覆蓋請求的時間範圍
                                        meta_start = datetime.fromtimestamp(metadata.get('time_range_start', 0))
                                        meta_end = datetime.fromtimestamp(metadata.get('time_range_end', 0))

                                        # 將請求範圍轉為datetime便於比較
                                        requested_start = time_range.start
                                        requested_end = time_range.end

                                        # 檢查現有數據是否完全覆蓋請求範圍
                                        if meta_start <= requested_start and meta_end >= requested_end:
                                            # 時間範圍覆蓋，但還需要驗證數據連續性
                                            try:
                                                # 讀取數據並驗證連續性（避免有缺口的數據被誤判為完整）
                                                existing_df = await asyncio.to_thread(
                                                    self.kline_storage.read_klines,
                                                    symbol,
                                                    timeframe,
                                                    validate_continuity=True  # 啟用零容忍連續性驗證
                                                )
                                                # 如果沒有拋出異常，說明數據連續完整
                                                logger.warning(
                                                    f"⏭️  SKIPPING download for {symbol}/{timeframe} (force_redownload=False)\n"
                                                    f"   Existing data range: {meta_start} to {meta_end}\n"
                                                    f"   Requested range: {requested_start} to {requested_end}\n"
                                                    f"   ✅ Requested range is FULLY COVERED by existing data\n"
                                                    f"   ✅ Data continuity verified: {len(existing_df)} bars with no gaps\n"
                                                    f"   Affected cases: {len(group_cases)} cases will read from existing HDF5"
                                                )
                                                async with stats_lock:
                                                    skipped_cases += len(group_cases)
                                                continue
                                            except ValueError as e:
                                                # 連續性驗證失敗 - 數據有缺口，需要重新下載
                                                logger.warning(
                                                    f"⚠️  Existing data for {symbol}/{timeframe} has GAPS - forcing redownload\n"
                                                    f"   Existing range: {meta_start} to {meta_end}\n"
                                                    f"   Continuity error: {str(e)}\n"
                                                    f"   🔄 Will redownload to ensure data integrity"
                                                )
                                                # 不 continue，讓代碼繼續執行下載流程
                                        else:
                                            # ❌ 現有數據不覆蓋請求範圍 - 必須下載
                                            logger.warning(
                                                f"⚠️  Existing HDF5 data for {symbol}/{timeframe} is OUTDATED/INCOMPLETE\n"
                                                f"   Existing range: {meta_start} to {meta_end}\n"
                                                f"   Requested range: {requested_start} to {requested_end}\n"
                                                f"   📊 Gap analysis:\n"
                                                f"      - Request starts {'BEFORE' if requested_start < meta_start else 'AFTER'} existing data\n"
                                                f"      - Request ends {'BEFORE' if requested_end < meta_end else 'AFTER'} existing data\n"
                                                f"   🔄 Downloading new data to fill the gap..."
                                            )
                                            # 繼續往下執行下載流程
                                    else:
                                        # total_bars = 0，數據損壞 - 強制下載
                                        logger.warning(
                                            f"⚠️  Metadata exists for {symbol}/{timeframe} but total_bars=0\n"
                                            f"   Forcing download to fix corrupted state"
                                        )

                            # 診斷日誌：下載前
                            logger.info(
                                f"📥 DOWNLOADING from Binance API: {symbol}/{timeframe}\n"
                                f"   Time range: {time_range.start} to {time_range.end}\n"
                                f"   For {len(group_cases)} cases\n"
                                f"   Force redownload: {request.force_redownload}"
                            )

                            # 使用asyncio.to_thread()在線程池中執行同步下載
                            download_start_time = datetime.utcnow()
                            df = await asyncio.to_thread(
                                self.download_service.download_klines,
                                source='binance',
                                symbol=symbol,
                                start_time=time_range.start,
                                end_time=time_range.end,
                                timeframe=timeframe,
                                save_to_storage=True
                            )
                            download_elapsed = (datetime.utcnow() - download_start_time).total_seconds()

                            # 診斷日誌：下載後
                            if not df.empty:
                                async with stats_lock:
                                    total_bars += len(df)

                                # 獲取實際下載的時間範圍
                                actual_start = datetime.fromtimestamp(df['timestamp'].iloc[0])
                                actual_end = datetime.fromtimestamp(df['timestamp'].iloc[-1])

                                logger.info(
                                    f"✅ DOWNLOAD SUCCESS: {symbol}/{timeframe}\n"
                                    f"   Downloaded: {len(df)} K-lines in {download_elapsed:.2f}s\n"
                                    f"   Requested: {time_range.start} to {time_range.end}\n"
                                    f"   Actual data: {actual_start} to {actual_end}\n"
                                    f"   Saved to HDF5: data_cache/{symbol}_{timeframe}.h5"
                                )
                            else:
                                logger.warning(
                                    f"⚠️  DOWNLOAD RETURNED EMPTY: {symbol}/{timeframe}\n"
                                    f"   Time range: {time_range.start} to {time_range.end}\n"
                                    f"   Binance API returned 0 K-lines (data may not exist for this period)"
                                )

                        except Exception as e:
                            logger.error(
                                f"Failed to download {symbol}/{timeframe} "
                                f"({time_range.start} to {time_range.end}): {e}",
                                exc_info=True
                            )
                            # 記錄失敗案例
                            async with stats_lock:
                                for case in group_cases:
                                    if case.case_id not in failed_case_ids:
                                        failed_case_ids.append(case.case_id)
                                        error_details[case.case_id] = str(e)
                            continue

                    # Step 4: 為每個案例創建HDF5存儲（按案例組織）
                    for case in group_cases:
                        try:
                            # 計算案例所需的時間範圍
                            case_start, case_end = self._calculate_case_time_range(
                                case,
                                request.lookback_bars,
                                request.forward_bars
                            )
                            
                            # 檢查時間範圍是否包含已知的數據缺口
                            has_gaps, gaps = self._check_timerange_has_known_gaps(case_start, case_end)
                            
                            if has_gaps:
                                # 跳過包含已知缺口的案例
                                gap_info = gaps[0]  # 顯示第一個缺口
                                logger.warning(
                                    f"⚠️  SKIPPING case {case.case_id} due to known data gap\n"
                                    f"   Case time range: {case_start} to {case_end}\n"
                                    f"   Known gap: {gap_info['start']} to {gap_info['end']}\n"
                                    f"   Reason: {gap_info['reason']}\n"
                                    f"   這是 Binance API 級別的數據缺失，無法下載補齊"
                                )
                                async with stats_lock:
                                    skipped_cases += 1
                                continue

                            # 從已下載數據中讀取案例範圍的K線
                            # 注意：KlineStorageManager.read_klines() 期望整數時間戳，不是datetime對象
                            logger.debug(
                                f"Reading case data: {case.case_id}\n"
                                f"   Symbol/Timeframe: {symbol}/{timeframe}\n"
                                f"   Case time range: {case_start} to {case_end}\n"
                                f"   Case TO timestamp: {case.timestamp}"
                            )

                            case_df = self.kline_storage.read_klines(
                                symbol,
                                timeframe,
                                int(case_start.timestamp()),
                                int(case_end.timestamp())
                            )

                            if case_df is None or case_df.empty:
                                # 診斷日誌：讀取失敗的詳細信息
                                metadata = self.kline_storage.get_metadata(symbol, timeframe)
                                if metadata:
                                    meta_start = datetime.fromtimestamp(metadata.get('time_range_start', 0))
                                    meta_end = datetime.fromtimestamp(metadata.get('time_range_end', 0))
                                    meta_count = metadata.get('total_bars', 0)

                                    # 檢查案例時間範圍是否超出 HDF5 數據範圍
                                    case_to = datetime.fromtimestamp(case.timestamp)
                                    is_before_data = case_end < meta_start
                                    is_after_data = case_start > meta_end
                                    is_future = case_to > datetime.utcnow()

                                    logger.error(
                                        f"❌ READ FAILED for case {case.case_id} ({symbol}/{timeframe})\n"
                                        f"   Case ID: {case.case_id}\n"
                                        f"   Case TO (時間點): {case_to}\n"
                                        f"   Case range needed: {case_start} to {case_end}\n"
                                        f"   HDF5 data range: {meta_start} to {meta_end} ({meta_count} K-lines)\n"
                                        f"   Diagnosis:\n"
                                        f"     - Case is BEFORE HDF5 data: {is_before_data}\n"
                                        f"     - Case is AFTER HDF5 data: {is_after_data}\n"
                                        f"     - Case is in FUTURE: {is_future}\n"
                                        f"   Possible causes:\n"
                                        f"     {'- Case time is in the future (data not exist yet)' if is_future else ''}\n"
                                        f"     {'- HDF5 data is outdated (need to download newer data)' if is_after_data and not is_future else ''}\n"
                                        f"     {'- HDF5 data is too recent (need historical data)' if is_before_data else ''}"
                                    )
                                else:
                                    logger.error(
                                        f"❌ READ FAILED for case {case.case_id}\n"
                                        f"   HDF5 file does not exist or has no metadata: {symbol}_{timeframe}.h5"
                                    )

                                async with stats_lock:
                                    failed_case_ids.append(case.case_id)
                                    error_details[case.case_id] = "No klines data after download"
                                continue

                            # [優化] 不再保存案例切片，只驗證數據可讀取
                            # 案例數據應實時從共享K線庫讀取，避免數據重複和空間浪費
                            # 原邏輯：await asyncio.to_thread(self._save_case_klines, case, case_df, request)

                            logger.info(
                                f"Saved {len(case_df)} klines for case {case.case_id} "
                                f"(read from shared K-line library)"
                            )

                            async with stats_lock:
                                downloaded_case_ids.append(case.case_id)

                                # 更新進度
                                progress.completed_cases += 1
                                progress.progress_percent = (
                                    progress.completed_cases / progress.total_cases * 100
                                )
                                progress.current_symbol = symbol

                                # 計算預估剩餘時間
                                elapsed_time = (datetime.utcnow() - start_time).total_seconds()
                                if progress.completed_cases > 0:
                                    avg_time_per_case = elapsed_time / progress.completed_cases
                                    remaining_cases = progress.total_cases - progress.completed_cases
                                    progress.estimated_time_remaining = int(avg_time_per_case * remaining_cases)

                        except Exception as e:
                            logger.error(
                                f"Failed to process case {case.case_id}: {e}",
                                exc_info=True
                            )
                            async with stats_lock:
                                failed_case_ids.append(case.case_id)
                                error_details[case.case_id] = str(e)
                                progress.failed_cases += 1

                except Exception as e:
                    logger.error(
                        f"Failed to process group {symbol}/{timeframe}: {e}",
                        exc_info=True
                    )
                    # 標記整個組的案例為失敗
                    async with stats_lock:
                        for case in group_cases:
                            if case.case_id not in failed_case_ids:
                                failed_case_ids.append(case.case_id)
                                error_details[case.case_id] = f"Group error: {str(e)}"
                        progress.failed_cases += len(group_cases)

        # 創建所有下載任務並並行執行
        download_tasks = [
            download_group(symbol, group_cases)
            for symbol, group_cases in grouped_cases.items()
        ]

        # 並行執行所有下載任務
        await asyncio.gather(*download_tasks, return_exceptions=True)

        # 完成任務
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()

        progress.status = TaskStatus.COMPLETED if not failed_case_ids else TaskStatus.FAILED
        progress.end_time = end_time
        progress.failed_case_ids = failed_case_ids
        progress.progress_percent = 100.0

        result = DownloadResult(
            task_id=task_id,
            success=(len(failed_case_ids) == 0),
            total_cases=len(cases),
            successful_downloads=len(downloaded_case_ids),
            failed_downloads=len(failed_case_ids),
            skipped_cases=skipped_cases,
            downloaded_case_ids=downloaded_case_ids,
            failed_case_ids=failed_case_ids,
            error_details=error_details,
            total_bars_downloaded=total_bars,
            total_download_time=total_time
        )

        logger.info(
            f"Batch download task {task_id} completed: "
            f"{result.successful_downloads} success, "
            f"{result.failed_downloads} failed, "
            f"{result.skipped_cases} skipped, "
            f"{total_time:.2f}s"
        )

        return result


    def get_progress(self, task_id: str) -> Optional[DownloadProgress]:
        """
        獲取任務進度

        Args:
            task_id: 任務ID

        Returns:
            Optional[DownloadProgress]: 進度信息（不存在則返回None）
        """
        return self.tasks.get(task_id)


    def _group_cases_by_symbol(
        self,
        cases: List[CaseRecord]
    ) -> Dict[str, List[CaseRecord]]:
        """
        按symbol分組案例

        NOTE: 只按symbol分組，不按timeframe分組。
        K線下載的timeframe由BatchDownloadRequest指定，與案例的timeframe獨立。

        Args:
            cases: 案例列表

        Returns:
            Dict[str, List[CaseRecord]]: symbol → 案例列表
        """
        grouped = defaultdict(list)

        for case in cases:
            key = case.symbol
            grouped[key].append(case)

        logger.debug(f"Grouped {len(cases)} cases into {len(grouped)} groups by symbol")
        return dict(grouped)


    def _calculate_time_ranges(
        self,
        cases: List[CaseRecord],
        timeframe: str,
        lookback_bars: int,
        forward_bars: int
    ) -> List[TimeRange]:
        """
        計算時間範圍列表

        **新邏輯（使用TO/TC概念）**：
        - case.timestamp = TO (Target Open)
        - 計算案例在下載timeframe的K線數（case_bars）
        - start_time = TO - lookback_bars * timeframe_seconds
        - end_time = TO + (case_bars + forward_bars) * timeframe_seconds

        Args:
            cases: 案例列表
            timeframe: 時間框架（下載用，如1h）
            lookback_bars: 往前K線根數
            forward_bars: 往後K線根數

        Returns:
            List[TimeRange]: 時間範圍列表
        """
        download_tf_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 3600)
        ranges = []

        for case in cases:
            # 計算案例在下載timeframe的K線數
            case_tf_seconds = self.TIMEFRAME_SECONDS.get(case.timeframe, 43200)
            case_bars = max(1, case_tf_seconds // download_tf_seconds)

            # 計算開始和結束時間（以TO為起點）
            case_time = datetime.utcfromtimestamp(case.timestamp)  # TO
            start_time = case_time - timedelta(seconds=lookback_bars * download_tf_seconds)
            end_time = case_time + timedelta(seconds=(case_bars + forward_bars) * download_tf_seconds)

            ranges.append(TimeRange(start_time, end_time))

        logger.debug(
            f"Calculated {len(ranges)} time ranges for {len(cases)} cases "
            f"(download_tf={timeframe})"
        )
        return ranges


    def _merge_overlapping_ranges(self, ranges: List[TimeRange]) -> List[TimeRange]:
        """
        合併重疊的時間範圍

        Args:
            ranges: 原始時間範圍列表

        Returns:
            List[TimeRange]: 合併後的時間範圍列表
        """
        if not ranges:
            return []

        # 按開始時間排序
        sorted_ranges = sorted(ranges, key=lambda r: r.start)

        merged = [sorted_ranges[0]]

        for current in sorted_ranges[1:]:
            last_merged = merged[-1]

            if current.overlaps(last_merged):
                # 合併重疊範圍
                merged[-1] = last_merged.merge(current)
            else:
                # 不重疊，添加新範圍
                merged.append(current)

        logger.debug(
            f"Merged {len(ranges)} ranges into {len(merged)} ranges "
            f"(saved {len(ranges) - len(merged)} downloads)"
        )
        return merged


    def _calculate_case_time_range(
        self,
        case: CaseRecord,
        lookback_bars: int,
        forward_bars: int
    ) -> Tuple[datetime, datetime]:
        """
        計算單個案例的時間範圍

        Args:
            case: 案例記錄
            lookback_bars: 往前K線根數
            forward_bars: 往後K線根數

        Returns:
            Tuple[datetime, datetime]: (start_time, end_time)
        """
        timeframe_seconds = self.TIMEFRAME_SECONDS.get(case.timeframe, 3600)
        case_time = datetime.utcfromtimestamp(case.timestamp)

        start_time = case_time - timedelta(seconds=lookback_bars * timeframe_seconds)
        end_time = case_time + timedelta(seconds=forward_bars * timeframe_seconds)

        return start_time, end_time


    def _save_case_klines(
        self,
        case: CaseRecord,
        klines_df,
        request: BatchDownloadRequest
    ):
        """
        保存案例的K線數據到HDF5（按案例組織）

        Args:
            case: 案例記錄
            klines_df: K線DataFrame
            request: 批量下載請求
        """
        # HDF5路徑：/cases/{case_id}/
        # 存儲metadata和klines

        try:
            import h5py
            import numpy as np
            import time

            hdf5_path = self.kline_storage.hdf5_path

            # 確保HDF5文件存在
            if not hdf5_path.exists():
                self.kline_storage._create_hdf5_structure()

            # 重試機制：避免並發文件鎖定問題
            max_retries = 3
            retry_delay = 0.1  # 100ms
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    with h5py.File(hdf5_path, 'a') as f:
                        # 創建或獲取cases組
                        if 'cases' not in f:
                            cases_group = f.create_group('cases')
                        else:
                            cases_group = f['cases']

                        # 創建或獲取case_id組
                        case_id_str = str(case.case_id)
                        if case_id_str in cases_group:
                            case_group = cases_group[case_id_str]
                            # 如果data已存在，刪除舊的
                            if 'data' in case_group:
                                del case_group['data']
                        else:
                            case_group = cases_group.create_group(case_id_str)

                        # 將DataFrame轉為結構化數組並寫入
                        dtype_list = [(col, str(klines_df[col].dtype)) for col in klines_df.columns]
                        structured_array = np.array(
                            [tuple(row) for row in klines_df.values],
                            dtype=dtype_list
                        )

                        # 創建dataset with compression
                        dataset = case_group.create_dataset(
                            'data',
                            data=structured_array,
                            compression='gzip',
                            compression_opts=self.kline_storage.COMPRESSION_LEVEL
                        )

                        # 存儲metadata
                        case_group.attrs['case_id'] = case_id_str
                        case_group.attrs['symbol'] = case.symbol
                        case_group.attrs['timeframe'] = case.timeframe
                        case_group.attrs['case_timestamp'] = case.timestamp
                        case_group.attrs['positive_case'] = case.positive_case
                        case_group.attrs['lookback_bars'] = request.lookback_bars
                        case_group.attrs['forward_bars'] = request.forward_bars
                        case_group.attrs['total_bars'] = len(klines_df)
                        case_group.attrs['time_range_start'] = int(klines_df['timestamp'].min())
                        case_group.attrs['time_range_end'] = int(klines_df['timestamp'].max())
                        case_group.attrs['saved_at'] = datetime.utcnow().isoformat()
                    
                    # 成功，跳出重試循環
                    logger.info(
                        f"Saved {len(klines_df)} klines for case {case.case_id} to HDF5 at /cases/{case_id_str}/"
                    )
                    return
                    
                except OSError as e:
                    # HDF5 文件鎖定錯誤
                    if "Unable to synchronously open file" in str(e) or "file is already open" in str(e):
                        last_error = e
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"HDF5 file lock conflict for case {case.case_id}, "
                                f"retrying ({attempt + 1}/{max_retries})..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指數退避
                            continue
                        else:
                            # 最後一次重試也失敗
                            logger.error(
                                f"Failed to save case {case.case_id} after {max_retries} retries: {e}",
                                exc_info=True
                            )
                            raise
                    else:
                        # 其他 OSError，直接拋出
                        raise

        except Exception as e:
            logger.error(
                f"Failed to save case klines for {case.case_id}: {e}",
                exc_info=True
            )
            raise


    def _check_timerange_has_known_gaps(self, start: datetime, end: datetime) -> Tuple[bool, List[Dict]]:
        """
        檢查時間範圍是否包含已知的數據缺口
        
        Args:
            start: 開始時間
            end: 結束時間
            
        Returns:
            Tuple[bool, List[Dict]]: (是否有缺口, 缺口列表)
        """
        found_gaps = []
        
        for gap in self.KNOWN_DATA_GAPS:
            # 檢查時間範圍是否與已知缺口重疊
            if gap['start'] < end and gap['end'] > start:
                found_gaps.append(gap)
        
        return (len(found_gaps) > 0, found_gaps)


# 創建全局實例
_batch_download_service = None


def get_batch_download_service() -> BatchDownloadService:
    """
    獲取BatchDownloadService單例

    Returns:
        BatchDownloadService: 服務實例
    """
    global _batch_download_service

    if _batch_download_service is None:
        # 使用全局單例的 case_storage manager
        case_storage = get_case_storage_manager()
        _batch_download_service = BatchDownloadService(case_storage=case_storage)
        logger.info("Created global BatchDownloadService instance with shared storage")

    return _batch_download_service
