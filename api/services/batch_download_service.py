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
        self.kline_storage = kline_storage or KlineStorageManager()

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

        # 按symbol和timeframe分組
        grouped_cases = self._group_cases_by_symbol_timeframe(cases)

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

        async def download_group(symbol: str, timeframe: str, group_cases: List[CaseRecord]):
            """下載單個分組（支援並行）"""
            nonlocal downloaded_case_ids, failed_case_ids, error_details, skipped_cases, total_bars

            async with semaphore:  # 限制並發數
                logger.info(
                    f"Processing {len(group_cases)} cases for {symbol}/{timeframe}"
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
                            if not request.force_redownload:
                                metadata = self.kline_storage.get_metadata(symbol, timeframe)
                                if metadata:
                                    logger.debug(
                                        f"Skipping {symbol}/{timeframe} (metadata exists, not force mode)"
                                    )
                                    async with stats_lock:
                                        skipped_cases += len(group_cases)
                                    continue

                            # 使用asyncio.to_thread()在線程池中執行同步下載
                            df = await asyncio.to_thread(
                                self.download_service.download_klines,
                                source='binance',
                                symbol=symbol,
                                start_time=time_range.start,
                                end_time=time_range.end,
                                timeframe=timeframe,
                                save_to_storage=True
                            )

                            if not df.empty:
                                async with stats_lock:
                                    total_bars += len(df)
                                logger.info(
                                    f"Downloaded {len(df)} bars for {symbol}/{timeframe} "
                                    f"({time_range.start} to {time_range.end})"
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
                            # 計算案例的具體時間範圍
                            case_start, case_end = self._calculate_case_time_range(
                                case,
                                request.lookback_bars,
                                request.forward_bars
                            )

                            # 從已下載數據中讀取案例範圍的K線
                            # 注意：KlineStorageManager.read_klines() 期望整數時間戳，不是datetime對象
                            case_df = self.kline_storage.read_klines(
                                symbol,
                                timeframe,
                                int(case_start.timestamp()),
                                int(case_end.timestamp())
                            )

                            if case_df is None or case_df.empty:
                                logger.warning(
                                    f"No klines found for case {case.case_id}"
                                )
                                async with stats_lock:
                                    failed_case_ids.append(case.case_id)
                                    error_details[case.case_id] = "No klines data after download"
                                continue

                            # 保存到cases路徑（按案例組織）
                            await asyncio.to_thread(
                                self._save_case_klines,
                                case,
                                case_df,
                                request
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
            download_group(symbol, timeframe, group_cases)
            for (symbol, timeframe), group_cases in grouped_cases.items()
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


    def _group_cases_by_symbol_timeframe(
        self,
        cases: List[CaseRecord]
    ) -> Dict[Tuple[str, str], List[CaseRecord]]:
        """
        按symbol和timeframe分組案例

        Args:
            cases: 案例列表

        Returns:
            Dict[Tuple[str, str], List[CaseRecord]]: (symbol, timeframe) → 案例列表
        """
        grouped = defaultdict(list)

        for case in cases:
            key = (case.symbol, case.timeframe)
            grouped[key].append(case)

        logger.debug(f"Grouped {len(cases)} cases into {len(grouped)} groups")
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

        Args:
            cases: 案例列表
            timeframe: 時間框架
            lookback_bars: 往前K線根數
            forward_bars: 往後K線根數

        Returns:
            List[TimeRange]: 時間範圍列表
        """
        timeframe_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 3600)
        ranges = []

        for case in cases:
            # 計算開始和結束時間
            case_time = datetime.utcfromtimestamp(case.timestamp)
            start_time = case_time - timedelta(seconds=lookback_bars * timeframe_seconds)
            end_time = case_time + timedelta(seconds=forward_bars * timeframe_seconds)

            ranges.append(TimeRange(start_time, end_time))

        logger.debug(
            f"Calculated {len(ranges)} time ranges for {len(cases)} cases"
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

            hdf5_path = self.kline_storage.hdf5_path

            # 確保HDF5文件存在
            if not hdf5_path.exists():
                self.kline_storage._create_hdf5_structure()

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

            logger.info(
                f"Saved {len(klines_df)} klines for case {case.case_id} to HDF5 at /cases/{case_id_str}/"
            )

        except Exception as e:
            logger.error(
                f"Failed to save case klines for {case.case_id}: {e}",
                exc_info=True
            )
            raise


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
