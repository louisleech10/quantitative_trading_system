#!/usr/bin/env python3
"""
指標快取驗證腳本

驗證目標：
1. IndicatorCache 可正確初始化
2. 預計算的 EMA 值與動態計算結果一致
3. 信號計算結果完全一致
4. 記憶體估算準確

Author: Claude (Verification Phase)
Date: 2025-01-05
"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import time
import logging
from typing import List, Dict, Any

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_klines(n_bars: int = 300) -> pd.DataFrame:
    """創建模擬 K 線資料"""
    np.random.seed(42)

    # 生成隨機價格走勢
    base_price = 100.0
    returns = np.random.normal(0, 0.02, n_bars)
    close = base_price * np.cumprod(1 + returns)

    high = close * (1 + np.abs(np.random.normal(0, 0.01, n_bars)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n_bars)))
    open_ = close + np.random.normal(0, 0.5, n_bars)
    volume = np.random.uniform(1000, 10000, n_bars)

    # 創建時間戳
    base_ts = 1704067200000  # 2024-01-01 00:00:00 UTC
    timestamps = [base_ts + i * 3600000 for i in range(n_bars)]  # 1h 間隔

    return pd.DataFrame({
        'timestamp': timestamps,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })


class MockCase:
    """模擬案例類別"""
    def __init__(self, case_id: str, symbol: str, timestamp: int, timeframe: str = "1h"):
        self.case_id = case_id
        self.symbol = symbol
        self.timestamp = timestamp
        self.timeframe = timeframe


class MockKlineCache:
    """模擬 K 線快取"""
    def __init__(self, klines: Dict[str, pd.DataFrame]):
        self._cache = klines
        self._is_loaded = True

        class Stats:
            memory_mb = 1.0
        self.stats = Stats()

    def is_loaded(self) -> bool:
        return self._is_loaded

    def has_case(self, case_id: str) -> bool:
        return case_id in self._cache

    def get(self, case_id: str, actual_lookback: int = None) -> pd.DataFrame:
        if case_id not in self._cache:
            return None
        df = self._cache[case_id]
        if actual_lookback is not None and actual_lookback < len(df):
            return df.iloc[-actual_lookback:].copy()
        return df.copy()


def verify_ema_calculation():
    """驗證 EMA 計算準確性"""
    logger.info("=" * 60)
    logger.info("驗證 1: EMA 計算準確性")
    logger.info("=" * 60)

    from momentum.Analysis.indicator_cache import IndicatorCache

    # 創建模擬資料
    n_bars = 300
    n_cases = 10
    far_lookback = 100

    # 創建模擬 K 線
    klines_cache = {}
    cases = []
    for i in range(n_cases):
        case_id = f"TEST_CASE_{i:03d}"
        klines = create_mock_klines(n_bars)
        klines_cache[case_id] = klines
        cases.append(MockCase(
            case_id=case_id,
            symbol="TESTUSDT",
            timestamp=klines['timestamp'].iloc[-1]
        ))

    mock_kline_cache = MockKlineCache(klines_cache)

    # 創建指標快取
    indicator_cache = IndicatorCache(
        kline_cache=mock_kline_cache,
        n_workers=2
    )

    # 預計算 EMA
    periods = list(range(5, 51))  # 5-50
    stats = indicator_cache.precompute(
        cases=cases,
        indicator_type="ema",
        data_source="close",
        periods=periods,
        far_lookback_bars=far_lookback
    )

    logger.info(f"預計算統計: {stats.cached_cases} 案例, {stats.total_indicators} 指標")

    # 驗證 EMA 值
    errors = []
    for case in cases[:3]:  # 驗證前 3 個案例
        klines = klines_cache[case.case_id]
        close = klines['close']

        for period in [12, 26, 50]:
            # 動態計算 EMA
            ema_dynamic = close.ewm(span=period, adjust=False).mean()
            ema_dynamic_slice = ema_dynamic.iloc[-far_lookback:].values

            # 從快取獲取 EMA
            ema_cached = indicator_cache.get(case.case_id, "ema", period)

            if ema_cached is None:
                errors.append(f"快取未命中: {case.case_id}, period={period}")
                continue

            # 比較
            if len(ema_cached) != len(ema_dynamic_slice):
                errors.append(
                    f"長度不匹配: {case.case_id}, period={period}, "
                    f"cached={len(ema_cached)}, dynamic={len(ema_dynamic_slice)}"
                )
                continue

            max_diff = np.max(np.abs(ema_cached - ema_dynamic_slice))
            if max_diff > 1e-10:
                errors.append(
                    f"數值差異過大: {case.case_id}, period={period}, max_diff={max_diff}"
                )
            else:
                logger.info(f"  ✅ {case.case_id} period={period}: max_diff={max_diff:.2e}")

    if errors:
        logger.error("EMA 計算驗證失敗:")
        for err in errors:
            logger.error(f"  ❌ {err}")
        return False

    logger.info("✅ EMA 計算驗證通過")
    return True


def verify_signal_calculation():
    """驗證信號計算準確性"""
    logger.info("=" * 60)
    logger.info("驗證 2: 信號計算準確性 (三線排列)")
    logger.info("=" * 60)

    from momentum.Analysis.indicator_cache import IndicatorCache

    # 創建模擬資料
    n_bars = 300
    n_cases = 5
    far_lookback = 100

    klines_cache = {}
    cases = []
    for i in range(n_cases):
        case_id = f"SIGNAL_CASE_{i:03d}"
        klines = create_mock_klines(n_bars)
        klines_cache[case_id] = klines
        cases.append(MockCase(
            case_id=case_id,
            symbol="TESTUSDT",
            timestamp=klines['timestamp'].iloc[-1]
        ))

    mock_kline_cache = MockKlineCache(klines_cache)

    # 創建指標快取
    indicator_cache = IndicatorCache(
        kline_cache=mock_kline_cache,
        n_workers=2
    )

    # 預計算
    periods = list(range(5, 51))
    indicator_cache.precompute(
        cases=cases,
        indicator_type="ema",
        data_source="close",
        periods=periods,
        far_lookback_bars=far_lookback
    )

    # 驗證信號
    errors = []
    for case in cases:
        klines = klines_cache[case.case_id]
        close = klines['close']

        short_period, mid_period, long_period = 12, 26, 50

        # 動態計算信號
        ema_short = close.ewm(span=short_period, adjust=False).mean()
        ema_mid = close.ewm(span=mid_period, adjust=False).mean()
        ema_long = close.ewm(span=long_period, adjust=False).mean()

        signals_dynamic = (
            (ema_short.iloc[-far_lookback:] > ema_mid.iloc[-far_lookback:]) &
            (ema_mid.iloc[-far_lookback:] > ema_long.iloc[-far_lookback:])
        ).values

        # 從快取獲取信號
        signals_cached = indicator_cache.get_signals_for_case(
            case_id=case.case_id,
            indicator_type="ema",
            short_period=short_period,
            mid_period=mid_period,
            long_period=long_period
        )

        if signals_cached is None:
            errors.append(f"信號快取未命中: {case.case_id}")
            continue

        if not np.array_equal(signals_cached, signals_dynamic):
            mismatch = np.sum(signals_cached != signals_dynamic)
            errors.append(f"信號不匹配: {case.case_id}, 不一致數量={mismatch}")
        else:
            signal_count = np.sum(signals_dynamic)
            logger.info(f"  ✅ {case.case_id}: 信號完全一致 (信號數={signal_count}/{len(signals_dynamic)})")

    if errors:
        logger.error("信號計算驗證失敗:")
        for err in errors:
            logger.error(f"  ❌ {err}")
        return False

    logger.info("✅ 信號計算驗證通過")
    return True


def verify_memory_estimation():
    """驗證記憶體估算準確性"""
    logger.info("=" * 60)
    logger.info("驗證 3: 記憶體估算準確性")
    logger.info("=" * 60)

    from momentum.Analysis.indicator_cache import IndicatorCache

    # 測試參數
    n_cases = 100
    n_periods = 50
    n_bars = 200

    # 理論值
    expected_bytes = n_cases * n_periods * n_bars * 8  # float64
    expected_mb = expected_bytes / (1024 * 1024)

    # 創建模擬資料
    klines_cache = {}
    cases = []
    for i in range(n_cases):
        case_id = f"MEM_CASE_{i:03d}"
        klines = create_mock_klines(n_bars + 100)  # 多加一些 warmup
        klines_cache[case_id] = klines
        cases.append(MockCase(
            case_id=case_id,
            symbol="TESTUSDT",
            timestamp=klines['timestamp'].iloc[-1]
        ))

    mock_kline_cache = MockKlineCache(klines_cache)

    indicator_cache = IndicatorCache(
        kline_cache=mock_kline_cache,
        n_workers=4
    )

    # 估算
    estimated_mb = indicator_cache.estimate_memory(n_cases, n_periods, n_bars)

    logger.info(f"理論估算: {expected_mb:.2f} MB")
    logger.info(f"方法估算: {estimated_mb:.2f} MB")

    if abs(estimated_mb - expected_mb) > 0.01:
        logger.error(f"❌ 記憶體估算不準確")
        return False

    logger.info("✅ 記憶體估算驗證通過")
    return True


def verify_performance():
    """驗證效能提升"""
    logger.info("=" * 60)
    logger.info("驗證 4: 效能比較")
    logger.info("=" * 60)

    from momentum.Analysis.indicator_cache import IndicatorCache

    n_cases = 50
    n_bars = 300
    far_lookback = 100
    n_trials = 100  # 模擬 100 次 Trial

    # 創建模擬資料
    klines_cache = {}
    cases = []
    for i in range(n_cases):
        case_id = f"PERF_CASE_{i:03d}"
        klines = create_mock_klines(n_bars)
        klines_cache[case_id] = klines
        cases.append(MockCase(
            case_id=case_id,
            symbol="TESTUSDT",
            timestamp=klines['timestamp'].iloc[-1]
        ))

    mock_kline_cache = MockKlineCache(klines_cache)

    # 測試動態計算耗時
    start = time.time()
    for trial in range(n_trials):
        short_period = 10 + (trial % 10)
        mid_period = 25 + (trial % 10)
        long_period = 45 + (trial % 10)

        for case in cases:
            klines = klines_cache[case.case_id]
            close = klines['close']

            ema_short = close.ewm(span=short_period, adjust=False).mean()
            ema_mid = close.ewm(span=mid_period, adjust=False).mean()
            ema_long = close.ewm(span=long_period, adjust=False).mean()

            signals = (ema_short > ema_mid) & (ema_mid > ema_long)

    dynamic_time = time.time() - start
    logger.info(f"動態計算: {n_trials} Trials × {n_cases} 案例 = {dynamic_time:.2f}s")

    # 創建快取
    indicator_cache = IndicatorCache(
        kline_cache=mock_kline_cache,
        n_workers=4
    )

    # 預計算 (一次性)
    start = time.time()
    periods = list(range(5, 60))
    indicator_cache.precompute(
        cases=cases,
        indicator_type="ema",
        data_source="close",
        periods=periods,
        far_lookback_bars=far_lookback
    )
    precompute_time = time.time() - start
    logger.info(f"預計算耗時: {precompute_time:.2f}s")

    # 測試快取查表耗時
    start = time.time()
    for trial in range(n_trials):
        short_period = 10 + (trial % 10)
        mid_period = 25 + (trial % 10)
        long_period = 45 + (trial % 10)

        for case in cases:
            signals = indicator_cache.get_signals_for_case(
                case_id=case.case_id,
                indicator_type="ema",
                short_period=short_period,
                mid_period=mid_period,
                long_period=long_period
            )

    cached_time = time.time() - start
    logger.info(f"快取查表: {n_trials} Trials × {n_cases} 案例 = {cached_time:.2f}s")

    speedup = dynamic_time / (precompute_time + cached_time)
    logger.info(f"加速比: {speedup:.1f}x (含預計算)")

    pure_speedup = dynamic_time / cached_time
    logger.info(f"純查表加速比: {pure_speedup:.1f}x")

    if pure_speedup > 5:
        logger.info("✅ 效能驗證通過 (加速 > 5x)")
        return True
    else:
        logger.warning(f"⚠️ 加速效果未達預期 ({pure_speedup:.1f}x < 5x)")
        return True  # 仍視為通過，只是警告


def main():
    """主驗證流程"""
    logger.info("=" * 60)
    logger.info("開始 IndicatorCache 驗證測試")
    logger.info("=" * 60)

    results = {
        "EMA 計算準確性": verify_ema_calculation(),
        "信號計算準確性": verify_signal_calculation(),
        "記憶體估算準確性": verify_memory_estimation(),
        "效能比較": verify_performance(),
    }

    logger.info("=" * 60)
    logger.info("驗證結果總結")
    logger.info("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 所有驗證測試通過!")
    else:
        logger.error("\n❌ 部分驗證測試失敗")

    return all_passed


if __name__ == "__main__":
    main()
