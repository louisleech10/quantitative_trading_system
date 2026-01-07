"""
指標預計算快取 - 加速 Optuna 優化

透過在優化開始前一次性預計算所有可能的 EMA 週期，
將每個 Trial 的 EMA 計算從 O(n) 降為 O(1) 查表。

設計原則:
- 根據用戶 Optuna 設定的參數範圍動態預計算
- 以 (case_id, indicator_type, period) 為 key 存儲
- 支援未來擴展其他指標 (RSI, SMA 等)
- 記憶體上限約 2GB (適配 8GB 機器)

效能預估:
- 預計算時間: ~2-3 分鐘 (一次性)
- 每 Trial 加速: 11.4ms → <1ms (查表)
- 記憶體消耗: ~1.5 GB (10000 案例 × 96 週期)

Author: Claude (Optuna Optimization Phase)
Date: 2025-01-05
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from momentum.Analysis.kline_cache import KlineCache

logger = logging.getLogger(__name__)


# EMA 收斂所需的 warmup 倍數
WARMUP_MULTIPLIER = 4.5


@dataclass
class IndicatorCacheStats:
    """指標快取統計資訊"""
    total_cases: int = 0
    cached_cases: int = 0
    failed_cases: int = 0
    total_indicators: int = 0  # 總指標數量 (cases × periods)
    memory_mb: float = 0.0
    precompute_time_seconds: float = 0.0
    periods_cached: List[int] = field(default_factory=list)
    indicator_type: str = ""
    data_source: str = ""


class IndicatorCache:
    """
    指標預計算快取

    在 Optuna 優化開始前，一次性預計算所有案例的所有可能 EMA 週期，
    將 Trial 中的 EMA 計算從動態計算轉為 O(1) 查表。

    使用方式:
    ```python
    # 初始化快取 (需要 KlineCache)
    indicator_cache = IndicatorCache(kline_cache)

    # 預計算所有 EMA 週期
    indicator_cache.precompute(
        cases=all_cases,
        indicator_type="ema",
        data_source="close",
        periods=range(5, 101),  # 用戶 Optuna 設定的範圍
        far_lookback_bars=100
    )

    # 在 Trial 中查表獲取 EMA
    ema_short = indicator_cache.get(case_id, "ema", period=12)
    ema_mid = indicator_cache.get(case_id, "ema", period=26)
    ema_long = indicator_cache.get(case_id, "ema", period=50)

    # 直接計算信號
    signals = (ema_short > ema_mid) & (ema_mid > ema_long)
    ```
    """

    def __init__(
        self,
        kline_cache: KlineCache,
        n_workers: int = 4,
        memory_limit_mb: float = 2000.0
    ):
        """
        初始化指標快取

        Args:
            kline_cache: K 線資料快取 (必須已完成 preload)
            n_workers: 預計算時的並行工作線程數
            memory_limit_mb: 記憶體上限 (MB)，預設 2GB
        """
        self.kline_cache = kline_cache
        self.n_workers = n_workers
        self.memory_limit_mb = memory_limit_mb

        # 快取存儲: {(case_id, indicator_type, period): np.ndarray}
        self._cache: Dict[Tuple[str, str, int], np.ndarray] = {}

        # 快取的週期集合 (用於快速檢查)
        self._cached_periods: Set[int] = set()

        # Metadata
        self._indicator_type: str = ""
        self._data_source: str = ""
        self._far_lookback_bars: int = 0

        # 統計資訊
        self.stats = IndicatorCacheStats()

        # 是否已預計算
        self._is_precomputed = False

    def estimate_memory(
        self,
        n_cases: int,
        n_periods: int,
        n_bars: int = 200
    ) -> float:
        """
        估算記憶體使用量

        Args:
            n_cases: 案例數量
            n_periods: 週期種類數量
            n_bars: 每案例的 K 線數量

        Returns:
            float: 估算的記憶體使用量 (MB)
        """
        # float64 = 8 bytes
        bytes_needed = n_cases * n_periods * n_bars * 8
        return bytes_needed / (1024 * 1024)

    def precompute(
        self,
        cases: List[Any],
        indicator_type: str,
        data_source: str,
        periods: List[int],
        far_lookback_bars: int,
        progress_callback: Optional[callable] = None
    ) -> IndicatorCacheStats:
        """
        預計算所有案例的指標值

        Args:
            cases: 案例物件列表
            indicator_type: 指標類型 ("ema", "sma", "rsi" 等)
            data_source: 數據源 ("close", "open", "high", "low")
            periods: 要預計算的週期列表 (如 range(5, 101))
            far_lookback_bars: 遠期窗口回看 K 線數
            progress_callback: 進度回調 (current, total) -> None

        Returns:
            IndicatorCacheStats: 預計算統計資訊
        """
        start_time = time.time()

        # 檢查 KlineCache 是否已載入
        if not self.kline_cache.is_loaded():
            raise RuntimeError("KlineCache must be preloaded before IndicatorCache.precompute()")

        # 記錄配置
        self._indicator_type = indicator_type
        self._data_source = data_source
        self._far_lookback_bars = far_lookback_bars
        periods_list = sorted(list(periods))
        self._cached_periods = set(periods_list)

        n_cases = len(cases)
        n_periods = len(periods_list)

        # 記憶體檢查
        estimated_mb = self.estimate_memory(n_cases, n_periods, far_lookback_bars)
        logger.info(
            f"📊 指標快取記憶體估算: {estimated_mb:.1f} MB "
            f"({n_cases} 案例 × {n_periods} 週期)"
        )

        if estimated_mb > self.memory_limit_mb:
            logger.warning(
                f"⚠️ 估算記憶體 ({estimated_mb:.1f} MB) 超過上限 ({self.memory_limit_mb:.1f} MB)，"
                f"將繼續執行但可能影響系統效能"
            )

        logger.info(
            f"🚀 開始預計算指標快取: "
            f"{n_cases} 案例, "
            f"{indicator_type.upper()} 週期 {min(periods_list)}-{max(periods_list)} "
            f"({n_periods} 種), "
            f"data_source={data_source}"
        )

        self.stats.total_cases = n_cases
        self.stats.indicator_type = indicator_type
        self.stats.data_source = data_source
        self.stats.periods_cached = periods_list

        # 並行預計算
        failed_cases = []
        computed_count = 0
        total_tasks = n_cases

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            future_to_case = {
                executor.submit(
                    self._compute_case_indicators,
                    case,
                    indicator_type,
                    data_source,
                    periods_list,
                    far_lookback_bars
                ): case.case_id
                for case in cases
            }

            for future in as_completed(future_to_case):
                case_id = future_to_case[future]
                try:
                    indicators = future.result()
                    if indicators:
                        # 存入快取
                        for period, values in indicators.items():
                            cache_key = (case_id, indicator_type, period)
                            self._cache[cache_key] = values
                        computed_count += 1
                    else:
                        failed_cases.append(case_id)
                except Exception as e:
                    logger.warning(f"預計算案例 {case_id} 失敗: {e}")
                    failed_cases.append(case_id)

                # 進度回調
                if progress_callback:
                    progress_callback(
                        computed_count + len(failed_cases),
                        total_tasks
                    )

        # 更新統計
        self.stats.cached_cases = computed_count
        self.stats.failed_cases = len(failed_cases)
        self.stats.total_indicators = len(self._cache)
        self.stats.precompute_time_seconds = time.time() - start_time

        # 計算實際記憶體使用
        total_bytes = sum(
            arr.nbytes for arr in self._cache.values()
        )
        self.stats.memory_mb = total_bytes / (1024 * 1024)

        self._is_precomputed = True

        logger.info(
            f"✅ 指標快取預計算完成: "
            f"{computed_count}/{n_cases} 成功, "
            f"{len(failed_cases)} 失敗, "
            f"總指標數: {self.stats.total_indicators}, "
            f"記憶體: {self.stats.memory_mb:.1f} MB, "
            f"耗時: {self.stats.precompute_time_seconds:.1f}s"
        )

        if failed_cases:
            logger.warning(f"失敗案例 ID: {failed_cases[:10]}...")

        return self.stats

    def _compute_case_indicators(
        self,
        case: Any,
        indicator_type: str,
        data_source: str,
        periods: List[int],
        far_lookback_bars: int
    ) -> Optional[Dict[int, np.ndarray]]:
        """
        計算單個案例的所有週期指標

        Args:
            case: 案例物件
            indicator_type: 指標類型
            data_source: 數據源
            periods: 週期列表
            far_lookback_bars: 遠期窗口回看 K 線數

        Returns:
            Dict[int, np.ndarray]: {period: indicator_values} 或 None
        """
        try:
            case_id = case.case_id

            # 從 KlineCache 獲取 K 線資料
            # 獲取最大可能的 lookback (包含最大週期的 warmup)
            max_period = max(periods)
            max_warmup = int(max_period * WARMUP_MULTIPLIER)
            total_lookback = far_lookback_bars + max_warmup

            klines = self.kline_cache.get(case_id, actual_lookback=total_lookback)

            if klines is None or len(klines) == 0:
                return None

            # 獲取數據源
            if data_source not in klines.columns:
                logger.warning(f"案例 {case_id} 缺少 {data_source} 欄位")
                return None

            data = klines[data_source].astype(np.float64)

            # 計算所有週期的指標
            result = {}

            if indicator_type == "ema":
                for period in periods:
                    # 計算 EMA
                    ema = data.ewm(span=period, adjust=False).mean()
                    # 只保留 far_lookback_bars 範圍內的值
                    result[period] = ema.iloc[-far_lookback_bars:].values.astype(np.float64)

            elif indicator_type == "sma":
                for period in periods:
                    sma = data.rolling(window=period).mean()
                    result[period] = sma.iloc[-far_lookback_bars:].values.astype(np.float64)

            elif indicator_type == "rsi":
                for period in periods:
                    # RSI 計算
                    delta = data.diff()
                    gain = delta.where(delta > 0, 0.0)
                    loss = (-delta).where(delta < 0, 0.0)
                    avg_gain = gain.ewm(span=period, adjust=False).mean()
                    avg_loss = loss.ewm(span=period, adjust=False).mean()
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    result[period] = rsi.iloc[-far_lookback_bars:].values.astype(np.float64)

            else:
                logger.warning(f"不支援的指標類型: {indicator_type}")
                return None

            return result

        except Exception as e:
            logger.debug(f"計算案例 {case.case_id} 指標時發生錯誤: {e}")
            return None

    def get(
        self,
        case_id: str,
        indicator_type: str,
        period: int
    ) -> Optional[np.ndarray]:
        """
        從快取查表獲取指標值

        Args:
            case_id: 案例 ID
            indicator_type: 指標類型
            period: 週期

        Returns:
            np.ndarray 或 None (未快取時)
        """
        cache_key = (case_id, indicator_type, period)
        return self._cache.get(cache_key)

    def get_last_value(
        self,
        case_id: str,
        indicator_type: str,
        period: int
    ) -> Optional[float]:
        """
        獲取指標的最後一個值 (信號點的值)

        Args:
            case_id: 案例 ID
            indicator_type: 指標類型
            period: 週期

        Returns:
            float 或 None
        """
        values = self.get(case_id, indicator_type, period)
        if values is not None and len(values) > 0:
            return float(values[-1])
        return None

    def get_signals_for_case(
        self,
        case_id: str,
        indicator_type: str,
        short_period: int,
        mid_period: int,
        long_period: int
    ) -> Optional[np.ndarray]:
        """
        計算三線排列信號 (專用於 three_line_strategy)

        Args:
            case_id: 案例 ID
            indicator_type: 指標類型 (ema/sma)
            short_period: 短期週期
            mid_period: 中期週期
            long_period: 長期週期

        Returns:
            np.ndarray (boolean): 信號陣列，或 None
        """
        short_values = self.get(case_id, indicator_type, short_period)
        mid_values = self.get(case_id, indicator_type, mid_period)
        long_values = self.get(case_id, indicator_type, long_period)

        if short_values is None or mid_values is None or long_values is None:
            return None

        # 三線排列邏輯: short > mid > long
        signals = (short_values > mid_values) & (mid_values > long_values)
        return signals

    def has_case(self, case_id: str) -> bool:
        """檢查案例是否有快取"""
        # 只需檢查任一週期是否存在
        if not self._cached_periods:
            return False
        first_period = next(iter(self._cached_periods))
        cache_key = (case_id, self._indicator_type, first_period)
        return cache_key in self._cache

    def has_period(self, period: int) -> bool:
        """檢查週期是否已快取"""
        return period in self._cached_periods

    def is_precomputed(self) -> bool:
        """是否已完成預計算"""
        return self._is_precomputed

    def get_cached_periods(self) -> Set[int]:
        """獲取已快取的週期集合"""
        return self._cached_periods.copy()

    def get_indicator_type(self) -> str:
        """獲取已快取的指標類型"""
        return self._indicator_type

    def get_data_source(self) -> str:
        """獲取已快取的數據源"""
        return self._data_source

    def matches_config(self, indicator_type: str, data_source: str) -> bool:
        """
        檢查請求的配置是否與快取匹配

        Args:
            indicator_type: 請求的指標類型
            data_source: 請求的數據源

        Returns:
            bool: 是否匹配
        """
        return (
            self._indicator_type == indicator_type and
            self._data_source == data_source
        )

    def clear(self):
        """清空快取"""
        self._cache.clear()
        self._cached_periods.clear()
        self._is_precomputed = False
        self.stats = IndicatorCacheStats()
        logger.info("指標快取已清空")

    def __len__(self) -> int:
        """快取的指標數量"""
        return len(self._cache)

    def __contains__(self, key: Tuple[str, str, int]) -> bool:
        """支援 in 運算符"""
        return key in self._cache
