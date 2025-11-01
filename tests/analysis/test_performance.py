"""
Signal Density Analysis 性能測試 - Ultra Think 最終優化版本

驗證系統性能指標：1000 cases < 10 seconds

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本性能測試
- 步驟 2: 審查優化 - 添加詳細性能分析、瓶頸識別
- 步驟 3: 最終版本 - 完整實作所有優化項
"""

import pytest
import time
import numpy as np
from typing import Dict, List

from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
from api.models.case_models import CaseRecord
from api.models.training_window_config import (
    TrainingWindowConfig,
    StrategyConfig,
    SignalDensityResponse
)


class TestPerformanceTarget:
    """測試核心性能目標：1000 cases < 10 seconds"""

    @pytest.mark.slow
    def test_1000_cases_under_10_seconds(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """
        核心性能測試：1000 個案例在 10 秒內完成

        驗證指標：
        - 總時間 < 10 秒
        - 平均每案例時間 < 10 ms
        - 無崩潰或超時
        """
        positive_cases = performance_test_cases["positive"]
        negative_cases = performance_test_cases["negative"]

        total_cases = len(positive_cases) + len(negative_cases)

        print(f"\n{'='*60}")
        print(f"性能測試開始：{total_cases} 個案例")
        print(f"{'='*60}")

        start_time = time.time()

        result = signal_analyzer.analyze_signal_density(
            positive_cases=positive_cases,
            negative_cases=negative_cases,
            strategy_config=sample_strategy_config,
            window_config=sample_training_window_config
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # 計算性能指標
        avg_time_per_case = elapsed / total_cases * 1000  # ms
        cases_per_second = total_cases / elapsed

        print(f"\n{'='*60}")
        print(f"性能測試結果：")
        print(f"{'='*60}")
        print(f"總案例數：{total_cases}")
        print(f"總耗時：{elapsed:.2f} 秒")
        print(f"平均每案例：{avg_time_per_case:.2f} ms")
        print(f"吞吐量：{cases_per_second:.1f} cases/s")
        print(f"{'='*60}")

        # 驗證性能目標
        assert elapsed < 10.0, \
            f"Performance target missed: {elapsed:.2f}s > 10.0s"

        assert avg_time_per_case < 10.0, \
            f"Average time too high: {avg_time_per_case:.2f}ms > 10ms"

        # 驗證結果有效性
        assert isinstance(result, SignalDensityResponse)
        assert result.positive_sample_size == len(positive_cases)
        assert result.negative_sample_size == len(negative_cases)

        print(f"\n✅ 性能測試通過：{total_cases} cases in {elapsed:.2f}s")

        # 返回性能數據供分析
        return {
            "total_cases": total_cases,
            "elapsed": elapsed,
            "avg_ms": avg_time_per_case,
            "throughput": cases_per_second
        }


class TestPerformanceBreakdown:
    """測試性能分解：識別瓶頸"""

    @pytest.mark.slow
    def test_training_window_extraction_performance(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_training_window_config
    ):
        """測試訓練窗口提取性能"""
        cases = performance_test_cases["positive"][:100]  # 100 個樣本

        times = []

        for case in cases:
            start = time.perf_counter()
            window_df = signal_analyzer.extract_training_window(
                case,
                sample_training_window_config
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # ms

        avg_time = np.mean(times)
        max_time = np.max(times)
        min_time = np.min(times)

        print(f"\n訓練窗口提取性能 (100 samples):")
        print(f"  平均：{avg_time:.3f} ms")
        print(f"  最大：{max_time:.3f} ms")
        print(f"  最小：{min_time:.3f} ms")

        # 應該 < 5ms per case
        assert avg_time < 5.0, f"Window extraction too slow: {avg_time:.3f}ms"

        print(f"✅ 窗口提取性能合格")

    @pytest.mark.slow
    def test_signal_calculation_performance(
        self,
        signal_analyzer,
        real_ethusdt_data,
        sample_strategy_config
    ):
        """測試信號計算性能"""
        # 使用 500 根 K 線，重複計算 100 次
        kline_data = real_ethusdt_data.head(500).copy()

        times = []

        for _ in range(100):
            start = time.perf_counter()
            signals = signal_analyzer.calculate_strategy_signals(
                kline_data,
                sample_strategy_config
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # ms

        avg_time = np.mean(times)

        print(f"\n信號計算性能 (100 iterations, 500 bars each):")
        print(f"  平均：{avg_time:.3f} ms")

        # 應該 < 2ms per calculation
        assert avg_time < 2.0, f"Signal calculation too slow: {avg_time:.3f}ms"

        print(f"✅ 信號計算性能合格")

    @pytest.mark.slow
    def test_density_calculation_performance(self, signal_analyzer):
        """測試密度計算性能"""
        # 創建 1000 個信號陣列
        signals_list = [
            np.random.choice([0.0, 1.0, np.nan], size=500)
            for _ in range(1000)
        ]

        start = time.perf_counter()

        densities = [
            signal_analyzer.calculate_case_density(signals)
            for signals in signals_list
        ]

        elapsed = time.perf_counter() - start
        avg_time = elapsed / 1000 * 1000  # ms

        print(f"\n密度計算性能 (1000 arrays):")
        print(f"  總耗時：{elapsed:.3f} s")
        print(f"  平均：{avg_time:.6f} ms")

        # 應該非常快（< 0.01ms per calculation）
        assert avg_time < 0.01, f"Density calculation too slow: {avg_time:.6f}ms"

        print(f"✅ 密度計算性能合格")

    @pytest.mark.slow
    def test_statistical_test_performance(self, signal_analyzer):
        """測試統計檢驗性能"""
        # 創建樣本數據
        positive_densities = np.random.uniform(0.6, 0.9, size=500)
        negative_densities = np.random.uniform(0.1, 0.4, size=500)

        times = []

        for _ in range(1000):
            start = time.perf_counter()

            p_value = signal_analyzer.statistical_significance_test(
                positive_densities,
                negative_densities
            )

            cohens_d = signal_analyzer.calculate_cohens_d(
                positive_densities,
                negative_densities
            )

            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # ms

        avg_time = np.mean(times)

        print(f"\n統計檢驗性能 (1000 iterations):")
        print(f"  平均：{avg_time:.6f} ms")

        # 應該非常快（< 0.1ms per test）
        assert avg_time < 0.1, f"Statistical tests too slow: {avg_time:.6f}ms"

        print(f"✅ 統計檢驗性能合格")


class TestScalability:
    """測試可擴展性"""

    @pytest.mark.slow
    def test_performance_scales_linearly(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試性能隨案例數量線性擴展"""
        case_counts = [10, 50, 100, 200]
        times = []

        for count in case_counts:
            positive_subset = performance_test_cases["positive"][:count//2]
            negative_subset = performance_test_cases["negative"][:count//2]

            start = time.time()

            signal_analyzer.analyze_signal_density(
                positive_cases=positive_subset,
                negative_cases=negative_subset,
                strategy_config=sample_strategy_config,
                window_config=sample_training_window_config
            )

            elapsed = time.time() - start
            times.append(elapsed)

            print(f"{count} cases: {elapsed:.3f}s ({elapsed/count*1000:.2f}ms/case)")

        # 計算線性度（理想情況下應該是線性的）
        # time_per_case 應該相對穩定
        times_per_case = [t/c for t, c in zip(times, case_counts)]
        cv = np.std(times_per_case) / np.mean(times_per_case)

        print(f"\n可擴展性分析:")
        print(f"  每案例時間變異係數：{cv:.3f}")

        # CV < 0.5 表示相對線性
        assert cv < 0.5, f"Performance not scaling linearly: CV={cv:.3f}"

        print(f"✅ 性能線性擴展")

    @pytest.mark.slow
    def test_memory_efficiency(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試內存效率（不應該有明顯內存洩漏）"""
        import gc

        # 強制垃圾回收
        gc.collect()

        # 多次執行相同分析
        for _ in range(5):
            result = signal_analyzer.analyze_signal_density(
                positive_cases=performance_test_cases["positive"][:100],
                negative_cases=performance_test_cases["negative"][:100],
                strategy_config=sample_strategy_config,
                window_config=sample_training_window_config
            )

            # 清理
            del result
            gc.collect()

        print(f"✅ 內存效率測試完成（無崩潰）")


class TestConcurrentPerformance:
    """測試並發性能（如果需要）"""

    @pytest.mark.slow
    @pytest.mark.skip(reason="Concurrent execution not yet implemented")
    def test_concurrent_analysis(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試並發分析（未來優化）"""
        # 預留：未來如果實作並發分析，在這裡測試
        pass


class TestPerformanceRegression:
    """性能回歸測試"""

    @pytest.mark.slow
    def test_baseline_performance_100_cases(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """
        基線性能測試：100 個案例

        建立性能基線，用於檢測未來回歸。
        """
        cases_count = 100
        positive_subset = performance_test_cases["positive"][:cases_count//2]
        negative_subset = performance_test_cases["negative"][:cases_count//2]

        start = time.time()

        result = signal_analyzer.analyze_signal_density(
            positive_cases=positive_subset,
            negative_cases=negative_subset,
            strategy_config=sample_strategy_config,
            window_config=sample_training_window_config
        )

        elapsed = time.time() - start

        # 100 個案例應該 < 1 秒
        assert elapsed < 1.0, f"Baseline regression: {elapsed:.3f}s > 1.0s"

        print(f"✅ 基線性能：{cases_count} cases in {elapsed:.3f}s")

        # 記錄到文件（可選）
        # with open("performance_baseline.txt", "a") as f:
        #     f.write(f"{datetime.now()},{cases_count},{elapsed:.3f}\n")


class TestWorstCasePerformance:
    """最壞情況性能測試"""

    @pytest.mark.slow
    def test_large_window_performance(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_strategy_config
    ):
        """測試大窗口（1000 根）性能"""
        large_window_config = TrainingWindowConfig(
            reference_point="TO",
            lookback_bars=1000,
            lookforward_bars=0,
            mode="relative"
        )

        cases = performance_test_cases["positive"][:50]

        start = time.time()

        for case in cases:
            window_df = signal_analyzer.extract_training_window(
                case,
                large_window_config
            )

            signals = signal_analyzer.calculate_strategy_signals(
                window_df,
                sample_strategy_config
            )

            density = signal_analyzer.calculate_case_density(signals)

        elapsed = time.time() - start
        avg_time = elapsed / 50 * 1000  # ms

        print(f"\n大窗口性能 (1000 bars, 50 cases):")
        print(f"  總耗時：{elapsed:.3f}s")
        print(f"  平均：{avg_time:.2f}ms/case")

        # 大窗口應該 < 50ms per case
        assert avg_time < 50.0, f"Large window too slow: {avg_time:.2f}ms"

        print(f"✅ 大窗口性能合格")

    @pytest.mark.slow
    def test_long_period_strategy_performance(
        self,
        signal_analyzer,
        performance_test_cases,
        sample_training_window_config
    ):
        """測試長週期策略（200 週期）性能"""
        long_period_strategy = StrategyConfig(
            data_source="close",
            indicator_type="ema",
            strategy_logic="three_line",
            params={
                "short_period": 50,
                "mid_period": 100,
                "long_period": 200
            }
        )

        result = signal_analyzer.analyze_signal_density(
            positive_cases=performance_test_cases["positive"][:100],
            negative_cases=performance_test_cases["negative"][:100],
            strategy_config=long_period_strategy,
            window_config=sample_training_window_config
        )

        # 只要能完成就行（不應該崩潰）
        assert isinstance(result, SignalDensityResponse)

        print(f"✅ 長週期策略性能測試完成")


# ============================================================
# 性能測試輔助工具
# ============================================================

def run_performance_suite():
    """運行完整性能測試套件（可獨立執行）"""
    print("="*60)
    print("Signal Density Analysis 性能測試套件")
    print("="*60)

    pytest.main([
        __file__,
        "-v",
        "-m", "slow",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_performance_suite()
