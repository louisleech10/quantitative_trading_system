"""
並行案例搜索引擎 - Phase 1 + 完整錯誤處理
使用 ProcessPoolExecutor 實現真正的多核並行處理

核心功能：
1. 自動偵測最佳 worker 數量
2. Symbol 批次分配
3. 並行處理與結果聚合
4. 完整錯誤處理與容錯
5. 智能重試機制
6. 詳細失敗報告

設計原則：
- 只加速，不改邏輯
- 方法簽名與原引擎一致
- 結果100%相同
- 向後兼容
- 失敗透明化（不靜默丟棄）
"""

import logging
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, asdict
from enum import Enum
import multiprocessing
import os
import psutil
import time
import json
from pathlib import Path

from momentum.DataExtraction.data_loader_momentum import IncompleteDownloadError

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """錯誤類型分類"""
    NETWORK_ERROR = "network_error"
    API_LIMIT = "api_limit"
    DATA_NOT_FOUND = "data_not_found"
    INVALID_CONFIG = "invalid_config"
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    """失敗記錄結構"""
    symbol: str
    error_type: str
    error_message: str
    error_trace: str = ""
    severity: str = "transient"  # transient, permanent, critical
    retry_count: int = 0
    first_failed_at: str = ""
    last_retry_at: str = ""
    worker_id: int = 0
    chunk_idx: int = 0
    is_recoverable: bool = True

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)


# 重試配置
RETRY_CONFIG = {
    FailureType.NETWORK_ERROR: {
        'max_retries': 3,
        'backoff_base': 1,  # 指數退避基數（秒）
        'description': '網絡問題，將重試'
    },
    FailureType.API_LIMIT: {
        'max_retries': 2,
        'backoff_base': 5,  # 固定延遲5秒
        'description': 'API限流，等待後重試'
    },
    FailureType.DATA_NOT_FOUND: {
        'max_retries': 0,
        'description': '數據不存在，跳過'
    },
    FailureType.INVALID_CONFIG: {
        'max_retries': 0,
        'description': '配置錯誤，應立即中斷'
    },
    FailureType.UNKNOWN: {
        'max_retries': 1,
        'backoff_base': 2,
        'description': '未知錯誤，嘗試重試一次'
    }
}


def classify_error(error: Exception) -> FailureType:
    """
    錯誤分類函數

    Args:
        error: 異常對象

    Returns:
        FailureType: 錯誤類型
    """
    # 🔴 型別優先於字串（CODEX-R2-P1-02／GROK-R2-P1-01 之衍生）：`IncompleteDownloadError`
    #   是**資料完整性拒收**，不是暫時性故障——重試它只會重複打同一個回亂序／stale 的端點。
    #   且其訊息含「拒收」「不得落快取」等中文字樣，不會命中下方任何英文關鍵字，
    #   落到 UNKNOWN 後仍會被重試。故在字串分類**之前**以型別攔截，歸為 INVALID_CONFIG
    #   （RETRY_CONFIG 中唯一 max_retries=0 且會立即中斷 worker 的類別）。
    if isinstance(error, IncompleteDownloadError):
        return FailureType.INVALID_CONFIG

    error_msg = str(error).lower()
    error_type_name = type(error).__name__.lower()

    # 網絡錯誤
    if any(keyword in error_msg for keyword in ['timeout', 'connection', 'network', 'unreachable']):
        return FailureType.NETWORK_ERROR

    if any(keyword in error_type_name for keyword in ['timeout', 'connection']):
        return FailureType.NETWORK_ERROR

    # API限流
    if any(keyword in error_msg for keyword in ['rate limit', 'too many requests', '429']):
        return FailureType.API_LIMIT

    # 數據不存在
    if any(keyword in error_msg for keyword in ['no data', 'not found', 'empty', 'missing']):
        return FailureType.DATA_NOT_FOUND

    # 配置錯誤
    if any(keyword in error_msg for keyword in ['invalid config', 'configuration error', 'config']):
        return FailureType.INVALID_CONFIG

    # 未知錯誤
    return FailureType.UNKNOWN


def calculate_backoff_delay(error_type: FailureType, attempt: int) -> float:
    """
    計算重試延遲時間

    Args:
        error_type: 錯誤類型
        attempt: 當前嘗試次數（0-based）

    Returns:
        float: 延遲秒數
    """
    config = RETRY_CONFIG[error_type]

    if 'backoff_base' not in config:
        return 0

    base = config['backoff_base']

    # API限流使用固定延遲
    if error_type == FailureType.API_LIMIT:
        return base

    # 其他使用指數退避: base * 2^attempt
    return base * (2 ** attempt)


def create_failure_record(
    symbol: str,
    error: Exception,
    error_type: FailureType,
    retry_count: int,
    worker_id: int,
    chunk_idx: int,
    first_failed_at: str
) -> FailureRecord:
    """
    創建失敗記錄

    Args:
        symbol: 交易對
        error: 異常對象
        error_type: 錯誤類型
        retry_count: 重試次數
        worker_id: Worker ID
        chunk_idx: 批次索引
        first_failed_at: 首次失敗時間

    Returns:
        FailureRecord: 失敗記錄
    """
    import traceback

    # 判斷嚴重性
    severity = "transient"
    is_recoverable = True

    if error_type == FailureType.INVALID_CONFIG:
        severity = "critical"
        is_recoverable = False
    elif error_type == FailureType.DATA_NOT_FOUND:
        severity = "permanent"
        is_recoverable = False
    elif error_type in [FailureType.NETWORK_ERROR, FailureType.API_LIMIT]:
        severity = "transient"
        is_recoverable = True

    return FailureRecord(
        symbol=symbol,
        error_type=error_type.value,
        error_message=str(error),
        error_trace=traceback.format_exc(),
        severity=severity,
        retry_count=retry_count,
        first_failed_at=first_failed_at,
        last_retry_at=datetime.now().isoformat(),
        worker_id=worker_id,
        chunk_idx=chunk_idx,
        is_recoverable=is_recoverable
    )


class ParallelSearchEngine:
    """
    並行搜索引擎

    特性：
    - 真正的多核並行（繞過GIL）
    - 自動優化 worker 數量
    - 智能負載平衡
    - 完整錯誤恢復
    """

    # 類常量
    DEFAULT_WORKER_COUNT = None  # None = 自動偵測
    MIN_WORKERS = 1
    MAX_WORKERS = None  # None = CPU核心數
    MEMORY_PER_WORKER_GB = 0.2  # 每個worker預估需要的內存（Phase 0+1+2優化後：從0.5改為0.2GB）

    def __init__(self,
                 case_search_engine,
                 num_workers: Optional[int] = None,
                 enable_parallel: bool = True):
        """
        初始化並行搜索引擎

        Args:
            case_search_engine: 原始案例搜索引擎實例
            num_workers: worker數量，None=自動偵測
            enable_parallel: 是否啟用並行（False時退回串行）
        """
        self.engine = case_search_engine
        self.enable_parallel = enable_parallel

        # 確定worker數量
        if num_workers is not None:
            self.num_workers = num_workers
        else:
            self.num_workers = self._get_optimal_workers()

        logger.info(
            f"並行搜索引擎已初始化: "
            f"workers={self.num_workers}, "
            f"parallel={self.enable_parallel}"
        )

    @staticmethod
    def _worker_log_path() -> Optional[str]:
        """worker 日誌路徑；取不到 ⇒ None（fail-open，只是沒有 worker 日誌，不影響搜尋）。

        優先用 `momentum/core/config.py` 解析之專案根（安裝／symlink 佈局下仍正確），
        `Path(__file__).parents[2]` 只作為最後退路（CODEX-R1-P2-06：硬推 root 非部署穩固契約）。
        呼叫端亦可自行傳 `log_path` 覆寫（`_process_chunk_worker(log_path=...)`）。
        """
        root = None
        try:
            from momentum.core.config import MomentumConfig

            root = Path(MomentumConfig.from_project_root().results_path).parent
        except Exception:                                # noqa: BLE001 —— 設定不可用時退路
            root = None
        try:
            if root is None:
                root = Path(__file__).resolve().parents[2]
            return str(Path(root) / "logs" / f"case_search_api_{datetime.now().strftime('%Y%m%d')}.log")
        except Exception:                                # noqa: BLE001
            return None

    def _get_optimal_workers(self) -> int:
        """
        動態計算最佳 worker 數量

        考慮因素：
        1. CPU核心數
        2. 可用內存
        3. 當前系統負載

        Returns:
            int: 最佳worker數量
        """
        try:
            # 1. 獲取CPU核心數
            cpu_count = multiprocessing.cpu_count()

            # 2. 檢查系統負載
            cpu_percent = psutil.cpu_percent(interval=0.5)
            if cpu_percent > 80:
                # 系統繁忙，減少worker避免競爭
                available_cores = max(2, cpu_count // 2)
                logger.info(f"系統CPU使用率{cpu_percent}%，減少worker至{available_cores}")
            else:
                available_cores = cpu_count

            # 3. 檢查可用內存
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            max_workers_by_memory = int(available_gb / self.MEMORY_PER_WORKER_GB)

            logger.debug(
                f"系統資源: CPU={cpu_count}核, "
                f"可用內存={available_gb:.1f}GB, "
                f"內存可支持{max_workers_by_memory}個worker"
            )

            # 4. 取最小值（最保守）
            optimal = min(available_cores, max_workers_by_memory, cpu_count)

            # 5. 至少保留1核給系統
            optimal = max(self.MIN_WORKERS, optimal - 1)

            # 6. 不超過最大限制
            if self.MAX_WORKERS is not None:
                optimal = min(optimal, self.MAX_WORKERS)

            logger.info(f"自動偵測最佳worker數: {optimal}")
            return optimal

        except Exception as e:
            logger.warning(f"無法自動偵測worker數，使用默認值2: {e}")
            return 2

    async def _serial_search_fallback(
        self,
        config,  # SearchConfiguration
        symbols: List[str],
        save_results: bool = False
    ) -> List[Dict]:
        """
        串行處理 fallback 邏輯（避免遞歸調用）

        當以下情況時使用：
        1. enable_parallel=False
        2. symbols 數量 < workers 數量

        直接調用 engine._search_batch() 進行逐個symbol處理，
        避免重新進入 search_cases() 的並行判斷邏輯。

        Args:
            config: 搜索配置
            symbols: symbol列表
            save_results: 是否保存結果

        Returns:
            搜索結果列表
        """
        logger.info(f"執行串行 fallback 處理: {len(symbols)} 個 symbols")
        all_results = []

        for i, symbol in enumerate(symbols, 1):
            try:
                logger.debug(f"處理 symbol {i}/{len(symbols)}: {symbol}")
                batch_results = await self.engine._search_batch(config, [symbol])
                if batch_results:
                    all_results.extend(batch_results)
                    logger.debug(f"{symbol}: 找到 {len(batch_results)} 個案例")
            except IncompleteDownloadError:
                # 見 `case_search_engine._search_single_symbol` 之註解：下載被拒收必須傳到任務層，
                # 不得在此記 log 後續跑成「其餘 symbol 的成功結果」——那份結果的完整性已無法宣稱。
                raise
            except Exception as e:
                logger.error(f"Symbol {symbol} 處理失敗: {e}", exc_info=True)

        # 保存結果（如果需要）
        if save_results and all_results:
            try:
                self.engine.matched_cases = all_results
                self.engine._save_results(config)
            except Exception as save_error:
                logger.error(f"保存結果失敗: {save_error}", exc_info=True)

        logger.info(f"串行 fallback 完成: {len(all_results)} 個案例")
        return all_results

    def _chunk_symbols(self, symbols: List[str], num_chunks: int) -> List[List[str]]:
        """
        將 symbols 分成 N 個批次（盡量平均）

        Args:
            symbols: 交易對列表
            num_chunks: 批次數量

        Returns:
            List[List[str]]: 分批後的symbol列表
        """
        if num_chunks <= 0:
            raise ValueError("num_chunks must be positive")

        # 計算每批的大小
        chunk_size = len(symbols) // num_chunks
        remainder = len(symbols) % num_chunks

        chunks = []
        start = 0

        for i in range(num_chunks):
            # 前 remainder 批多分配1個
            current_chunk_size = chunk_size + (1 if i < remainder else 0)
            end = start + current_chunk_size

            if start < len(symbols):
                chunks.append(symbols[start:end])

            start = end

        # 過濾空批次
        chunks = [chunk for chunk in chunks if chunk]

        logger.debug(
            f"將{len(symbols)}個symbols分成{len(chunks)}批: "
            f"{[len(c) for c in chunks]}"
        )

        return chunks

    def _save_failure_report(
        self,
        failed_records: List[Dict],
        retry_stats: Dict,
        config,
        total_symbols: int,
        execution_time: float
    ) -> str:
        """
        保存失敗報告到JSON文件

        Args:
            failed_records: 失敗記錄列表
            retry_stats: 重試統計
            config: 搜索配置
            total_symbols: 總symbol數量
            execution_time: 執行時間

        Returns:
            str: 保存的文件路徑
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 創建報告目錄
        report_dir = Path("search_results/failure_reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        # 創建報告文件名
        report_file = report_dir / f"failure_report_{timestamp}.json"

        # 生成推薦
        recommendations = []

        # 統計錯誤類型
        error_types = {}
        for failure in failed_records:
            error_type = failure['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # 根據錯誤類型生成建議
        if error_types.get(FailureType.NETWORK_ERROR.value, 0) > 0:
            count = error_types[FailureType.NETWORK_ERROR.value]
            recommendations.append(
                f"⚠️  {count}個symbols因網絡問題失敗，建議檢查網絡連接後重試"
            )

        if error_types.get(FailureType.DATA_NOT_FOUND.value, 0) > 0:
            count = error_types[FailureType.DATA_NOT_FOUND.value]
            recommendations.append(
                f"💡 {count}個symbols因數據缺失失敗，建議調整時間範圍或排除這些symbols"
            )

        # 創建報告數據
        report_data = {
            'metadata': {
                'timestamp': timestamp,
                'config_name': config.name if hasattr(config, 'name') else 'unknown',
                'total_symbols': total_symbols,
                'execution_time': execution_time
            },
            'summary': {
                'success_count': total_symbols - len(failed_records),
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
            ]
        }

        with open(failed_symbols_file, 'w', encoding='utf-8') as f:
            json.dump(failed_symbols_data, f, indent=2, ensure_ascii=False)

        logger.info(f"失敗symbols列表已保存到: {failed_symbols_file}")

        return str(report_file)

    async def search_cases_parallel(self,
                                   config,
                                   symbols: List[str],
                                   save_results: bool = True) -> List[Dict]:
        """
        並行搜索案例（主入口）

        Args:
            config: 搜索配置（必須可pickle，不能包含lambda函數或不可序列化對象）
            symbols: 交易對列表
            save_results: 是否保存結果

        Returns:
            List[Dict]: 搜索結果

        Raises:
            ValueError: 如果symbols列表為空
            Exception: 並行處理失敗時會fallback到串行模式

        Note:
            - 當symbols數量 < workers數量時，自動使用串行模式
            - 當enable_parallel=False時，直接使用串行模式
            - 單個symbol失敗不會影響整體處理
        """
        try:
            # 如果禁用並行，使用串行 fallback（避免遞歸）
            if not self.enable_parallel:
                logger.info("並行處理已禁用，使用串行模式（直接處理）")
                return await self._serial_search_fallback(config, symbols, save_results)

            # 如果symbol數量太少，使用串行 fallback（避免遞歸）
            if len(symbols) < self.num_workers:
                logger.info(
                    f"Symbol數量({len(symbols)})小於worker數({self.num_workers})，"
                    f"使用串行模式（直接處理，避免遞歸）"
                )
                return await self._serial_search_fallback(config, symbols, save_results)

            logger.info(
                f"開始並行搜索: {len(symbols)}個symbols, "
                f"{self.num_workers}個workers"
            )

            start_time = time.time()

            # 分批symbols
            symbol_chunks = self._chunk_symbols(symbols, self.num_workers)

            # 並行處理
            all_results = []
            all_failed_records = []  # 收集所有失敗記錄
            batch_times = []  # 記錄每批處理時間
            total_retry_stats = {
                'total_retries': 0,
                'successful_retries': 0,
                'failed_retries': 0
            }

            # 不用 `with`：其 __exit__ ⇒ shutdown(wait=True) ⇒ 在**事件迴圈執行緒**上 join worker
            # （取消或 worker 卡住時仍會鎖住整台服務；CODEX-R1-P1-05）。改由 finally 丟執行緒關閉。
            executor = ProcessPoolExecutor(max_workers=self.num_workers)
            try:
                # 提交任務
                futures = []
                for chunk_idx, chunk in enumerate(symbol_chunks):
                    future = executor.submit(
                        _process_chunk_worker,
                        chunk,
                        config,
                        chunk_idx,
                        len(symbol_chunks),
                        self._worker_log_path(),      # 子進程日誌落檔路徑（不落檔＝查不到任何 worker 紀錄）
                    )
                    futures.append(future)

                # 收集結果
                # 🔴 不得用 concurrent.futures.as_completed／future.result()：兩者都是**同步阻塞**，
                # 在 async 函式內會鎖住整個事件迴圈 ⇒ 搜尋期間後端對任何 HTTP 請求都不回應
                # （前端輪詢逾時報「請求超時」；2026-08-22 UAT B1 實測，sample 顯示主執行緒卡在 pthread_cond_wait）。
                # 改以 asyncio.wrap_future 包成 awaitable，逐個完成即處理，其餘時間讓出迴圈。
                completed = 0
                aio_futures = [asyncio.wrap_future(f) for f in futures]
                for aio_future in asyncio.as_completed(aio_futures):
                    batch_start = time.time()
                    try:
                        chunk_data = await aio_future
                        batch_elapsed = time.time() - batch_start

                        # 收集成功結果
                        if chunk_data['success_results']:
                            all_results.extend(chunk_data['success_results'])

                        # 收集失敗記錄
                        if chunk_data['failed_records']:
                            all_failed_records.extend(chunk_data['failed_records'])

                        # 聚合重試統計
                        retry_stats = chunk_data['retry_stats']
                        total_retry_stats['total_retries'] += retry_stats['total_retries']
                        total_retry_stats['successful_retries'] += retry_stats['successful_retries']
                        total_retry_stats['failed_retries'] += retry_stats['failed_retries']

                        batch_times.append(batch_elapsed)
                        completed += 1

                        logger.info(
                            f"批次完成 {completed}/{len(futures)}, "
                            f"成功: {len(all_results)}, "
                            f"失敗: {len(all_failed_records)}, "
                            f"批次耗時: {batch_elapsed:.2f}秒"
                        )

                    except Exception as e:
                        logger.error(f"批次處理失敗: {e}", exc_info=True)
                        # 單個批次失敗不影響其他批次
                        continue
            finally:
                # 關閉（含 join）丟到執行緒，事件迴圈期間仍可服務其他請求；取消時亦不阻塞
                await asyncio.to_thread(executor.shutdown, True)

            elapsed = time.time() - start_time

            # 計算性能統計
            if batch_times:
                avg_batch_time = sum(batch_times) / len(batch_times)
                max_batch_time = max(batch_times)
                min_batch_time = min(batch_times)
            else:
                avg_batch_time = max_batch_time = min_batch_time = 0

            # 輸出搜索總結
            logger.info("="*60)
            logger.info("搜索完成總結")
            logger.info("="*60)
            logger.info(
                f"✅ 成功: {len(all_results)}/{len(symbols)} 個案例"
            )
            logger.info(
                f"❌ 失敗: {len(all_failed_records)}/{len(symbols)} 個symbols"
            )
            logger.info(
                f"🔄 重試: {total_retry_stats['total_retries']}次 "
                f"(成功{total_retry_stats['successful_retries']}次, "
                f"失敗{total_retry_stats['failed_retries']}次)"
            )
            logger.info(
                f"⏱️  耗時: {elapsed:.2f}秒, "
                f"平均{elapsed/len(symbols):.3f}秒/symbol"
            )

            # 如果有失敗，輸出失敗詳情
            if all_failed_records:
                logger.warning("="*60)
                logger.warning("失敗詳情:")
                logger.warning("="*60)

                for i, failure in enumerate(all_failed_records[:5], 1):  # 只顯示前5個
                    logger.warning(
                        f"{i}. {failure['symbol']} [{failure['error_type']}]\n"
                        f"   錯誤: {failure['error_message']}\n"
                        f"   重試: {failure['retry_count']}次\n"
                        f"   嚴重性: {failure['severity']}"
                    )

                if len(all_failed_records) > 5:
                    logger.warning(f"... 還有 {len(all_failed_records)-5} 個失敗")

                # 保存失敗記錄到文件
                try:
                    failed_file = self._save_failure_report(
                        all_failed_records,
                        total_retry_stats,
                        config,
                        len(symbols),
                        elapsed
                    )
                    logger.warning(f"\n📄 完整失敗報告已保存到: {failed_file}")
                except Exception as e:
                    logger.error(f"保存失敗報告時出錯: {e}")

            # 保存結果（使用原引擎的保存方法）
            if save_results and all_results:
                try:
                    # 設置引擎的matched_cases，然後調用保存方法
                    self.engine.matched_cases = all_results
                    self.engine._save_results(config)
                except Exception as save_error:
                    logger.error(f"保存結果失敗: {save_error}", exc_info=True)

            return all_results

        except Exception as e:
            logger.error(f"並行搜索失敗: {e}", exc_info=True)

            # 如果並行失敗，嘗試退回串行
            # 注意：為避免死循環，臨時禁用並行後再調用
            logger.warning("並行處理失敗，退回串行模式")

            # 保存原始設置
            original_enable_parallel = self.enable_parallel

            try:
                # 臨時禁用並行
                self.enable_parallel = False

                # 調用原引擎（會使用串行模式）
                result = await self.engine.search_cases(
                    config=config,
                    symbols=symbols,
                    save_results=save_results
                )

                return result

            finally:
                # 恢復原始設置
                self.enable_parallel = original_enable_parallel


_WORKER_LOG_HANDLER_MARKER = "_search_worker_file_handler"


def _init_worker_file_logging(log_path: Optional[str]) -> None:
    """在 ProcessPool worker 子進程把 `momentum` namespace 的日誌落檔（fail-open、idempotent）。

    子進程不繼承父進程 handler；不掛的話 worker 內所有 INFO/ERROR（含每個 symbol 的失敗原因）
    只會噴到 console 而不進 `logs/`，使用者事後查不到任何紀錄。
    """
    if not log_path:
        return
    try:
        import logging as _logging
        from pathlib import Path as _Path

        # 掛在 **root**：下載器的 logger 名是頂層 `DataLoader`（`self.__class__.__name__`，parent=root），
        # 不在 `momentum` 命名空間下——只掛 momentum 會漏掉最需要的下載／retry／錯誤日誌
        # （CODEX-R1-P1-04 實測 `data_is_momentum_descendant=False`）。
        target = _logging.getLogger()
        for handler in target.handlers:
            if getattr(handler, _WORKER_LOG_HANDLER_MARKER, False):
                return                                   # 同進程重複呼叫不重複掛
        path = _Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = _logging.FileHandler(path, encoding="utf-8")
        setattr(file_handler, _WORKER_LOG_HANDLER_MARKER, True)
        file_handler.setLevel(_logging.INFO)             # handler 只收 INFO 以上（不放大既有 logger）
        file_handler.setFormatter(_logging.Formatter(
            fmt=f"%(asctime)s - %(name)s - [search-worker pid={os.getpid()}] %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        # 子進程 root 預設 WARNING ⇒ INFO 根本不會傳到 handler；只在「比 INFO 嚴」時放寬，
        # 且僅限本子進程（不回寫父進程狀態）。不動任何具名 logger 的 level（CODEX-R1-P1-04）。
        if target.level == _logging.NOTSET or target.level > _logging.INFO:
            target.setLevel(_logging.INFO)
        target.addHandler(file_handler)
    except Exception:                                    # noqa: BLE001 —— 日誌掛載失敗不得影響搜尋
        pass


def _process_chunk_worker(symbols_chunk: List[str],
                          config,
                          chunk_idx: int,
                          total_chunks: int,
                          log_path: Optional[str] = None) -> Dict:
    """
    Worker進程：處理一批symbols（含智能重試和失敗記錄）

    注意：此函數在獨立進程中運行，不能訪問主進程的對象

    Args:
        symbols_chunk: 要處理的symbols
        config: 搜索配置（必須可pickle）
        chunk_idx: 當前批次索引
        total_chunks: 總批次數

    Returns:
        Dict: {
            'success_results': [...],  # 成功的結果
            'failed_records': [...],   # 失敗記錄
            'retry_stats': {...}       # 重試統計
        }
    """
    try:
        # 在worker進程中重新初始化logger
        import logging
        import asyncio
        worker_logger = logging.getLogger(__name__)
        # 子進程的 logger 沒有父進程的 handler ⇒ 搜尋期間所有 worker 日誌（含失敗原因）都不會進 logs/，
        # 使用者只看得到 console 殘影（2026-08-22 UAT B1：log 停在「開始並行搜索」、errors_*.log 為 0 bytes）。
        # 於此掛檔案 handler（fail-open，掛不上不影響搜尋）。
        _init_worker_file_logging(log_path)

        # 在worker進程中重新創建引擎實例
        from momentum.DataExtraction.case_search_engine import CaseSearchEngine
        from momentum.DataExtraction.data_loader_momentum import DataLoader

        worker_logger.info(
            f"Worker {chunk_idx+1}/{total_chunks} 啟動, "
            f"處理 {len(symbols_chunk)} 個symbols"
        )

        # 創建數據加載器
        data_loader = DataLoader(enable_hdf5_cache=True)

        # 創建搜索引擎
        engine = CaseSearchEngine(data_loader=data_loader, enable_parallel=False)

        # 收集結果和失敗記錄
        chunk_results = []
        failed_records = []
        retry_stats = {
            'total_retries': 0,
            'successful_retries': 0,
            'failed_retries': 0
        }

        # 逐個處理symbol（在單個worker內部是串行的）
        for symbol_idx, symbol in enumerate(symbols_chunk, 1):
            first_failed_at = None
            symbol_success = False

            worker_logger.info(
                f"Worker {chunk_idx+1}/{total_chunks}: "
                f"處理 {symbol} ({symbol_idx}/{len(symbols_chunk)})"
            )

            # 智能重試邏輯
            for attempt in range(10):  # 最多10次（含初次）
                try:
                    # 調用原引擎的單symbol搜索方法
                    symbol_results = asyncio.run(
                        engine._search_single_symbol(symbol, config)
                    )

                    if symbol_results:
                        chunk_results.extend(symbol_results)
                        worker_logger.info(
                            f"Worker {chunk_idx+1}: "
                            f"{symbol} 找到 {len(symbol_results)} 個案例"
                        )

                    # 成功處理
                    symbol_success = True

                    # 如果之前失敗過，記錄重試成功
                    if attempt > 0:
                        retry_stats['successful_retries'] += 1
                        worker_logger.info(
                            f"{symbol} 第{attempt+1}次嘗試成功"
                        )

                    break  # 成功，跳出重試循環

                except Exception as e:
                    # 記錄首次失敗時間
                    if first_failed_at is None:
                        first_failed_at = datetime.now().isoformat()

                    # 錯誤分類
                    error_type = classify_error(e)
                    retry_config = RETRY_CONFIG[error_type]
                    max_retries = retry_config.get('max_retries', 0)

                    # 配置錯誤 → 立即中斷
                    if error_type == FailureType.INVALID_CONFIG:
                        worker_logger.error(
                            f"配置錯誤，worker {chunk_idx+1} 中斷: {e}"
                        )
                        raise

                    # 判斷是否應該重試
                    if attempt < max_retries:
                        # 計算延遲
                        delay = calculate_backoff_delay(error_type, attempt)

                        retry_stats['total_retries'] += 1

                        worker_logger.warning(
                            f"Worker {chunk_idx+1}: {symbol} 失敗 "
                            f"({error_type.value}), "
                            f"第{attempt+1}次嘗試失敗，"
                            f"{delay}秒後重試（最多{max_retries}次）"
                        )

                        time.sleep(delay)
                        continue  # 重試

                    else:
                        # 最終失敗，記錄失敗
                        retry_stats['failed_retries'] += 1

                        failure = create_failure_record(
                            symbol=symbol,
                            error=e,
                            error_type=error_type,
                            retry_count=attempt + 1,
                            worker_id=chunk_idx,
                            chunk_idx=chunk_idx,
                            first_failed_at=first_failed_at
                        )

                        failed_records.append(failure.to_dict())

                        worker_logger.error(
                            f"Worker {chunk_idx+1}: {symbol} "
                            f"重試{attempt+1}次後最終失敗 ({error_type.value}): {e}"
                        )

                        break  # 不再重試

        worker_logger.info(
            f"Worker {chunk_idx+1}/{total_chunks} 完成, "
            f"成功: {len(chunk_results)} 個案例, "
            f"失敗: {len(failed_records)} 個symbols, "
            f"重試: {retry_stats['total_retries']} 次"
        )

        return {
            'success_results': chunk_results,
            'failed_records': failed_records,
            'retry_stats': retry_stats
        }

    except Exception as e:
        worker_logger.error(f"Worker {chunk_idx+1} 整體失敗: {e}", exc_info=True)
        return {
            'success_results': [],
            'failed_records': [],
            'retry_stats': {'total_retries': 0, 'successful_retries': 0, 'failed_retries': 0}
        }
