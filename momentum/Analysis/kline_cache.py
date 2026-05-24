"""
K線資料預載入快取 - 加速 Optuna 優化

透過在優化開始前一次性載入所有案例的 K 線資料到記憶體，
避免每個 Trial 重複進行 HDF5 I/O 操作。

設計原則:
- 預計算最大可能的 lookback 範圍（基於 EMA 參數上限）
- 以 case_id 為 key 存儲預載入的 DataFrame
- 提供切片方法，根據實際 warmup 需求返回對應範圍的資料

效能預估:
- 記憶體消耗: ~2-4 GB (16,500 案例 × 500 根 K 線 × 8 欄位 × 8 bytes)
- 加速效果: 2-3x (消除 HDF5 讀取延遲)

Author: Claude (Optuna Optimization Phase)
Date: 2025-01-04
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from momentum.core.protocols import IKlineReader
from momentum.FeatureEngineering.atomic.warmup_lookup import get_warmup_bars


logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """快取統計資訊"""
    total_cases: int = 0
    cached_cases: int = 0
    failed_cases: int = 0
    memory_mb: float = 0.0
    load_time_seconds: float = 0.0


class KlineCache:
    """
    K 線資料預載入快取

    在 Optuna 優化開始前，一次性載入所有案例的 K 線資料，
    避免每個 Trial 重複讀取 HDF5。

    使用方式:
    ```python
    # 初始化快取
    cache = KlineCache(kline_storage)

    # 預載入所有案例（在優化前調用一次）
    cache.preload(
        cases=all_cases,
        far_lookback_bars=100,
        max_ema_period=100,
        timeframe="1h"
    )

    # 在 Trial 中獲取快取資料
    klines = cache.get(case_id, actual_lookback=262)
    ```
    """

    def __init__(
        self,
        kline_storage: IKlineReader,
        n_workers: int = 4
    ):
        """
        初始化快取

        Args:
            kline_storage: K 線讀取介面
            n_workers: 預載入時的並行工作線程數
        """
        self.storage = kline_storage
        self.n_workers = n_workers

        # 快取存儲: {case_id: DataFrame}
        self._cache: Dict[str, pd.DataFrame] = {}

        # 快取 metadata
        self._ref_timestamps: Dict[str, int] = {}  # {case_id: timestamp}
        self._max_lookback: int = 0  # 預載入時使用的最大 lookback

        # 統計資訊
        self.stats = CacheStats()

        # 是否已預載入
        self._is_loaded = False

    def preload(
        self,
        cases: List[Any],
        far_lookback_bars: int,
        max_ema_period: int,
        timeframe: str = "1h",
        reference_point: str = "TO",
        progress_callback: Optional[callable] = None
    ) -> CacheStats:
        """
        預載入所有案例的 K 線資料

        Args:
            cases: 案例物件列表（需包含 case_id, symbol, timeframe, timestamp）
            far_lookback_bars: 遠期窗口回看 K 線數
            max_ema_period: 最大 EMA 週期（用於計算 warmup）
            timeframe: 計算用時間框架
            reference_point: 參考點類型 ("TO" 或 "TC")
            progress_callback: 進度回調 (current, total) -> None

        Returns:
            CacheStats: 載入統計資訊
        """
        start_time = time.time()

        # Per-indicator warmup factor from warmup_table.yaml (EMA: 1.44×)
        max_warmup = get_warmup_bars("EMA", max_ema_period)
        self._max_lookback = far_lookback_bars + max_warmup

        logger.info(
            f"🚀 開始預載入 K 線快取: "
            f"{len(cases)} 案例, "
            f"far_lookback={far_lookback_bars}, "
            f"max_warmup={max_warmup}, "
            f"total_lookback={self._max_lookback}"
        )

        self.stats.total_cases = len(cases)

        # 收集所有需要載入的案例資訊
        load_tasks = []
        for case in cases:
            case_id = case.case_id
            symbol = case.symbol

            # 確定參考時間戳
            if reference_point == "TO":
                ref_timestamp = case.timestamp
            elif reference_point == "TC":
                ref_timestamp = getattr(case, 'tc_timestamp', case.timestamp)
            else:
                ref_timestamp = case.timestamp

            self._ref_timestamps[case_id] = ref_timestamp
            load_tasks.append((case_id, symbol, timeframe, ref_timestamp))

        # 並行載入
        failed_cases = []
        loaded_count = 0

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            future_to_case = {
                executor.submit(
                    self._load_single_case,
                    case_id, symbol, timeframe, ref_timestamp
                ): case_id
                for case_id, symbol, timeframe, ref_timestamp in load_tasks
            }

            for future in as_completed(future_to_case):
                case_id = future_to_case[future]
                try:
                    df = future.result()
                    if df is not None and len(df) > 0:
                        self._cache[case_id] = df
                        loaded_count += 1
                    else:
                        failed_cases.append(case_id)
                except Exception as e:
                    logger.warning(f"載入案例 {case_id} 失敗: {e}")
                    failed_cases.append(case_id)

                # 進度回調
                if progress_callback:
                    progress_callback(loaded_count + len(failed_cases), len(cases))

        # 更新統計
        self.stats.cached_cases = loaded_count
        self.stats.failed_cases = len(failed_cases)
        self.stats.load_time_seconds = time.time() - start_time

        # 估算記憶體使用
        total_bytes = sum(
            df.memory_usage(deep=True).sum()
            for df in self._cache.values()
        )
        self.stats.memory_mb = total_bytes / (1024 * 1024)

        self._is_loaded = True

        logger.info(
            f"✅ K 線快取預載入完成: "
            f"{loaded_count}/{len(cases)} 成功, "
            f"{len(failed_cases)} 失敗, "
            f"記憶體: {self.stats.memory_mb:.1f} MB, "
            f"耗時: {self.stats.load_time_seconds:.1f}s"
        )

        if failed_cases:
            logger.warning(f"失敗案例 ID: {failed_cases[:10]}...")

        return self.stats

    def _load_single_case(
        self,
        case_id: str,
        symbol: str,
        timeframe: str,
        ref_timestamp: int
    ) -> Optional[pd.DataFrame]:
        """
        載入單個案例的 K 線資料

        Args:
            case_id: 案例 ID
            symbol: 交易對
            timeframe: 時間框架
            ref_timestamp: 參考時間戳

        Returns:
            DataFrame 或 None（失敗時）
        """
        try:
            df = self.storage.read_klines_around_timestamp(
                symbol=symbol,
                timeframe=timeframe,
                center_timestamp=ref_timestamp,
                lookback=self._max_lookback,
                forward=0
            )

            if df is None or len(df) == 0:
                return None

            # 移除參考時間戳所在的 K 線（與原邏輯一致）
            df = df[df['timestamp'] < ref_timestamp].copy()

            return df

        except Exception as e:
            logger.debug(f"載入案例 {case_id} 時發生錯誤: {e}")
            return None

    def get(
        self,
        case_id: str,
        actual_lookback: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        從快取獲取案例的 K 線資料

        Args:
            case_id: 案例 ID
            actual_lookback: 實際需要的 lookback 數量（None 則返回全部快取）

        Returns:
            DataFrame 或 None（未快取時）
        """
        if case_id not in self._cache:
            return None

        df = self._cache[case_id]

        if actual_lookback is None or actual_lookback >= len(df):
            return df.copy()

        # 從末尾切片（最近的 actual_lookback 根）
        return df.iloc[-actual_lookback:].copy()

    def get_ref_timestamp(self, case_id: str) -> Optional[int]:
        """獲取案例的參考時間戳"""
        return self._ref_timestamps.get(case_id)

    def is_loaded(self) -> bool:
        """是否已完成預載入"""
        return self._is_loaded

    def has_case(self, case_id: str) -> bool:
        """檢查案例是否在快取中"""
        return case_id in self._cache

    def clear(self):
        """清空快取"""
        self._cache.clear()
        self._ref_timestamps.clear()
        self._is_loaded = False
        self.stats = CacheStats()
        logger.info("K 線快取已清空")

    def __len__(self) -> int:
        """快取的案例數量"""
        return len(self._cache)

    def __contains__(self, case_id: str) -> bool:
        """支援 in 運算符"""
        return case_id in self._cache
