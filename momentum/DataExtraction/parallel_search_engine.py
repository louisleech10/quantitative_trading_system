"""
並行案例搜索引擎 - Phase 1
使用 ProcessPoolExecutor 實現真正的多核並行處理

核心功能：
1. 自動偵測最佳 worker 數量
2. Symbol 批次分配
3. 並行處理與結果聚合
4. 完整錯誤處理與容錯

設計原則：
- 只加速，不改邏輯
- 方法簽名與原引擎一致
- 結果100%相同
- 向後兼容
"""

import logging
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import psutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)


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
    MEMORY_PER_WORKER_GB = 2.0  # 每個worker預估需要的內存

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
            # 如果禁用並行，退回原引擎
            if not self.enable_parallel:
                logger.info("並行處理已禁用，使用串行模式")
                return await self.engine.search_cases(
                    config=config,
                    symbols=symbols,
                    save_results=save_results
                )

            # 如果symbol數量太少，不值得並行
            if len(symbols) < self.num_workers:
                logger.info(
                    f"Symbol數量({len(symbols)})小於worker數({self.num_workers})，"
                    f"使用串行模式"
                )
                return await self.engine.search_cases(
                    config=config,
                    symbols=symbols,
                    save_results=save_results
                )

            logger.info(
                f"開始並行搜索: {len(symbols)}個symbols, "
                f"{self.num_workers}個workers"
            )

            start_time = time.time()

            # 分批symbols
            symbol_chunks = self._chunk_symbols(symbols, self.num_workers)

            # 並行處理
            all_results = []
            batch_times = []  # 記錄每批處理時間

            with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
                # 提交任務
                futures = []
                for chunk_idx, chunk in enumerate(symbol_chunks):
                    future = executor.submit(
                        _process_chunk_worker,
                        chunk,
                        config,
                        chunk_idx,
                        len(symbol_chunks)
                    )
                    futures.append(future)

                # 收集結果
                completed = 0
                for future in as_completed(futures):
                    batch_start = time.time()
                    try:
                        chunk_results = future.result()
                        batch_elapsed = time.time() - batch_start

                        if chunk_results:
                            all_results.extend(chunk_results)

                        batch_times.append(batch_elapsed)
                        completed += 1

                        logger.info(
                            f"批次完成 {completed}/{len(futures)}, "
                            f"當前總結果: {len(all_results)}, "
                            f"批次耗時: {batch_elapsed:.2f}秒"
                        )

                    except Exception as e:
                        logger.error(f"批次處理失敗: {e}", exc_info=True)
                        # 單個批次失敗不影響其他批次
                        continue

            elapsed = time.time() - start_time

            # 計算性能統計
            if batch_times:
                avg_batch_time = sum(batch_times) / len(batch_times)
                max_batch_time = max(batch_times)
                min_batch_time = min(batch_times)
            else:
                avg_batch_time = max_batch_time = min_batch_time = 0

            logger.info(
                f"並行搜索完成: 找到{len(all_results)}個案例, "
                f"耗時{elapsed:.2f}秒, "
                f"平均{elapsed/len(symbols):.3f}秒/symbol"
            )

            logger.info(
                f"批次統計: "
                f"平均{avg_batch_time:.2f}秒, "
                f"最快{min_batch_time:.2f}秒, "
                f"最慢{max_batch_time:.2f}秒"
            )

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


def _process_chunk_worker(symbols_chunk: List[str],
                          config,
                          chunk_idx: int,
                          total_chunks: int) -> List[Dict]:
    """
    Worker進程：處理一批symbols

    注意：此函數在獨立進程中運行，不能訪問主進程的對象

    Args:
        symbols_chunk: 要處理的symbols
        config: 搜索配置（必須可pickle）
        chunk_idx: 當前批次索引
        total_chunks: 總批次數

    Returns:
        List[Dict]: 搜索結果
    """
    try:
        # 在worker進程中重新初始化logger
        import logging
        worker_logger = logging.getLogger(__name__)

        # 在worker進程中重新創建引擎實例
        # 這是必須的，因為不能跨進程共享對象
        from momentum.DataExtraction.case_search_engine import CaseSearchEngine
        from momentum.DataExtraction.data_loader_momentum import DataLoader

        worker_logger.info(
            f"Worker {chunk_idx+1}/{total_chunks} 啟動, "
            f"處理 {len(symbols_chunk)} 個symbols"
        )

        # 創建數據加載器
        data_loader = DataLoader(enable_hdf5_cache=True)

        # 創建搜索引擎
        engine = CaseSearchEngine(data_loader=data_loader)

        # 收集結果
        chunk_results = []

        # 逐個處理symbol（在單個worker內部是串行的）
        for symbol_idx, symbol in enumerate(symbols_chunk, 1):
            try:
                worker_logger.info(
                    f"Worker {chunk_idx+1}/{total_chunks}: "
                    f"處理 {symbol} ({symbol_idx}/{len(symbols_chunk)})"
                )

                # 調用原引擎的單symbol搜索方法
                # 使用 asyncio.run() 安全地運行async函數
                import asyncio

                symbol_results = asyncio.run(
                    engine._search_single_symbol(symbol, config)
                )

                if symbol_results:
                    chunk_results.extend(symbol_results)
                    worker_logger.info(
                        f"Worker {chunk_idx+1}: "
                        f"{symbol} 找到 {len(symbol_results)} 個案例"
                    )

            except Exception as e:
                worker_logger.error(
                    f"Worker {chunk_idx+1}: "
                    f"處理 {symbol} 失敗: {e}",
                    exc_info=True
                )
                # 單個symbol失敗不影響其他symbol
                continue

        worker_logger.info(
            f"Worker {chunk_idx+1}/{total_chunks} 完成, "
            f"共找到 {len(chunk_results)} 個案例"
        )

        return chunk_results

    except Exception as e:
        worker_logger.error(f"Worker {chunk_idx+1} 整體失敗: {e}", exc_info=True)
        return []
