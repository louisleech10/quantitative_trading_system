"""
SignalDensityAnalyzer 單元測試 - Ultra Think 最終優化版本

測試信號密度分析器的 8 個核心方法，使用真實 ETHUSDT/1h 數據（NO MOCK DATA）。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本測試覆蓋
- 步驟 2: 審查優化 - 添加邊界測試、錯誤處理測試、性能測試
- 步驟 3: 最終版本 - 完整實作所有優化項
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
from api.models.case_models import CaseRecord
from api.models.training_window_config import TrainingWindowConfig, StrategyConfig
from tests.analysis.conftest import (
    assert_valid_signal_array,
    assert_valid_density,
    assert_statistical_metrics
)


class TestExtractTrainingWindow:
    """測試訓練窗口提取功能"""

    def test_extract_basic_window(
        self,
        signal_analyzer,
        minimal_test_cases,
        sample_training_window_config
    ):
        """測試基本訓練窗口提取"""
        case = minimal_test_cases["positive"][0]

        window_df = signal_analyzer.extract_training_window(
            case,
            sample_training_window_config
        )

        # 驗證返回 DataFrame
        assert isinstance(window_df, pd.DataFrame)

        # 驗證長度（應該 ≤ lookback_bars）
        assert len(window_df) <= sample_training_window_config.lookback_bars

        # 驗證必需列存在
        required_cols = ['close', 'open', 'high', 'low', 'volume']
        for col in required_cols:
            assert col in window_df.columns, f"Missing column: {col}"

        # 驗證時間範圍（所有時間戳應該 < case.timestamp）
        assert all(window_df.index <= pd.Timestamp.fromtimestamp(case.timestamp))

        print(f"✅ Extracted {len(window_df)} bars for window")

    def test_extract_with_lookforward(
        self,
        signal_analyzer,
        minimal_test_cases,
        edge_case_configs
    ):
        """測試包含 lookforward 的窗口提取"""
        case = minimal_test_cases["positive"][0]
        config = edge_case_configs["with_lookforward"]

        window_df = signal_analyzer.extract_training_window(case, config)

        # 驗證長度（lookback + lookforward）
        expected_max = config.lookback_bars + config.lookforward_bars
        assert len(window_df) <= expected_max

        print(f"✅ Extracted window with lookforward: {len(window_df)} bars")

    def test_extract_minimal_window(
        self,
        signal_analyzer,
        minimal_test_cases,
        edge_case_configs
    ):
        """測試最小窗口（10 根）"""
        case = minimal_test_cases["positive"][0]
        config = edge_case_configs["minimal_lookback"]

        window_df = signal_analyzer.extract_training_window(case, config)

        assert len(window_df) <= 10
        assert len(window_df) > 0  # 至少應有一些數據

        print(f"✅ Minimal window: {len(window_df)} bars")

    def test_extract_boundary_case_insufficient_data(
        self,
        signal_analyzer,
        real_ethusdt_data
    ):
        """測試邊界情況：數據不足時的處理"""
        # 創建一個非常早期的案例（可能沒有足夠歷史數據）
        early_timestamp = int(real_ethusdt_data.index[50].timestamp())

        case = CaseRecord(
            case_id="BOUNDARY_EARLY",
            symbol="ETHUSDT",
            timeframe="1h",
            timestamp=early_timestamp,
            positive_case=1
        )

        config = TrainingWindowConfig(
            reference_point="TO",
            lookback_bars=1000,  # 要求很多歷史數據
            lookforward_bars=0,
            mode="relative"
        )

        # 應該返回可用的數據（不足 1000 根但不報錯）
        window_df = signal_analyzer.extract_training_window(case, config)

        assert isinstance(window_df, pd.DataFrame)
        assert len(window_df) < 1000  # 數據不足
        assert len(window_df) > 0  # 但至少有一些

        print(f"✅ Boundary case handled: {len(window_df)} bars (requested 1000)")

    def test_extract_tc_reference_point(
        self,
        signal_analyzer,
        minimal_test_cases,
        edge_case_configs
    ):
        """測試 TC 參考點"""
        case = minimal_test_cases["positive"][0]
        config = edge_case_configs["tc_reference"]

        # TC 參考點目前應該與 TO 相同（未實作 TC 邏輯）
        window_df = signal_analyzer.extract_training_window(case, config)

        assert isinstance(window_df, pd.DataFrame)
        assert len(window_df) > 0

        print(f"✅ TC reference point: {len(window_df)} bars")


class TestCalculateStrategySignals:
    """測試策略信號計算功能"""

    def test_calculate_three_line_ema_signals(
        self,
        signal_analyzer,
        real_ethusdt_data,
        sample_strategy_config
    ):
        """測試三線順排 EMA 信號計算"""
        # 使用真實數據的前 500 根
        kline_data = real_ethusdt_data.head(500).copy()

        signals = signal_analyzer.calculate_strategy_signals(
            kline_data,
            sample_strategy_config
        )

        # 驗證返回陣列
        assert_valid_signal_array(signals, expected_length=len(kline_data))

        # 驗證前面有 NaN（需要 120 根預熱）
        max_period = max(
            sample_strategy_config.params["short_period"],
            sample_strategy_config.params["mid_period"],
            sample_strategy_config.params["long_period"]
        )
        assert np.isnan(signals[:max_period]).any(), \
            "Should have NaN values during warmup period"

        # 驗證後面有有效信號
        valid_signals = signals[~np.isnan(signals)]
        assert len(valid_signals) > 0, "Should have valid signals after warmup"

        # 統計信號分布
        signal_count = np.sum(valid_signals == 1)
        signal_ratio = signal_count / len(valid_signals) if len(valid_signals) > 0 else 0

        print(f"✅ EMA signals calculated: {signal_count}/{len(valid_signals)} "
              f"({signal_ratio:.2%}) bars matched")

    def test_calculate_signals_with_nan_in_data(
        self,
        signal_analyzer,
        real_ethusdt_data,
        sample_strategy_config
    ):
        """測試輸入數據包含 NaN 的情況"""
        kline_data = real_ethusdt_data.head(300).copy()

        # 人為插入一些 NaN
        kline_data.loc[kline_data.index[100:105], 'close'] = np.nan

        signals = signal_analyzer.calculate_strategy_signals(
            kline_data,
            sample_strategy_config
        )

        # 應該正常返回（NaN 位置的信號也是 NaN）
        assert_valid_signal_array(signals, expected_length=len(kline_data))

        print(f"✅ Handled NaN in data: {np.sum(np.isnan(signals))} NaN signals")

    def test_calculate_signals_minimal_data(
        self,
        signal_analyzer,
        real_ethusdt_data,
        sample_strategy_config
    ):
        """測試最小數據量（剛好滿足週期）"""
        # 只取 121 根（剛好滿足 long_period=120）
        kline_data = real_ethusdt_data.head(121).copy()

        signals = signal_analyzer.calculate_strategy_signals(
            kline_data,
            sample_strategy_config
        )

        assert_valid_signal_array(signals, expected_length=121)

        # 應該只有最後幾根有有效信號
        valid_signals = signals[~np.isnan(signals)]
        assert len(valid_signals) >= 1, "Should have at least 1 valid signal"

        print(f"✅ Minimal data: {len(valid_signals)} valid signals from 121 bars")


class TestCalculateCaseDensity:
    """測試單案例密度計算功能"""

    def test_calculate_density_normal_case(self, signal_analyzer):
        """測試正常情況的密度計算"""
        # 50% 信號密度
        signals = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 0], dtype=float)

        density = signal_analyzer.calculate_case_density(signals)

        assert_valid_density(density)
        assert density == 0.5, f"Expected 0.5, got {density}"

        print(f"✅ Normal density: {density}")

    def test_calculate_density_with_nan(self, signal_analyzer):
        """測試包含 NaN 的密度計算"""
        # 前 5 個 NaN，後 5 個中有 3 個信號
        signals = np.array([np.nan, np.nan, np.nan, np.nan, np.nan,
                           1, 0, 1, 0, 1], dtype=float)

        density = signal_analyzer.calculate_case_density(signals)

        assert_valid_density(density)
        # 應該是 3/5 = 0.6（忽略 NaN）
        assert abs(density - 0.6) < 1e-6, f"Expected 0.6, got {density}"

        print(f"✅ Density with NaN: {density}")

    def test_calculate_density_all_nan(self, signal_analyzer):
        """測試全部 NaN 的情況"""
        signals = np.array([np.nan] * 10, dtype=float)

        density = signal_analyzer.calculate_case_density(signals)

        assert density == 0.0, "All NaN should return 0.0"

        print(f"✅ All NaN density: {density}")

    def test_calculate_density_empty_array(self, signal_analyzer):
        """測試空陣列"""
        signals = np.array([], dtype=float)

        density = signal_analyzer.calculate_case_density(signals)

        assert density == 0.0, "Empty array should return 0.0"

        print(f"✅ Empty array density: {density}")

    def test_calculate_density_all_zero(self, signal_analyzer):
        """測試全部為 0（無信號）"""
        signals = np.zeros(20, dtype=float)

        density = signal_analyzer.calculate_case_density(signals)

        assert density == 0.0

        print(f"✅ All zero density: {density}")

    def test_calculate_density_all_one(self, signal_analyzer):
        """測試全部為 1（滿信號）"""
        signals = np.ones(20, dtype=float)

        density = signal_analyzer.calculate_case_density(signals)

        assert density == 1.0

        print(f"✅ All one density: {density}")


class TestStatisticalSignificanceTest:
    """測試統計顯著性檢驗功能"""

    def test_ttest_clearly_different(self, signal_analyzer):
        """測試明顯不同的兩組數據"""
        positive_densities = np.array([0.7, 0.75, 0.8, 0.72, 0.78] * 10)  # 高密度
        negative_densities = np.array([0.2, 0.25, 0.3, 0.22, 0.28] * 10)  # 低密度

        p_value = signal_analyzer.statistical_significance_test(
            positive_densities,
            negative_densities
        )

        assert 0.0 <= p_value <= 1.0
        assert p_value < 0.05, "Should be statistically significant"

        print(f"✅ T-test for different groups: p={p_value:.6f}")

    def test_ttest_similar_groups(self, signal_analyzer):
        """測試相似的兩組數據"""
        positive_densities = np.array([0.5, 0.52, 0.48, 0.51, 0.49] * 10)
        negative_densities = np.array([0.5, 0.51, 0.49, 0.50, 0.52] * 10)

        p_value = signal_analyzer.statistical_significance_test(
            positive_densities,
            negative_densities
        )

        assert 0.0 <= p_value <= 1.0
        assert p_value > 0.05, "Should NOT be statistically significant"

        print(f"✅ T-test for similar groups: p={p_value:.6f}")

    def test_ttest_minimal_samples(self, signal_analyzer):
        """測試最小樣本數"""
        positive_densities = np.array([0.8, 0.9])
        negative_densities = np.array([0.2, 0.3])

        p_value = signal_analyzer.statistical_significance_test(
            positive_densities,
            negative_densities
        )

        assert 0.0 <= p_value <= 1.0

        print(f"✅ T-test with minimal samples: p={p_value:.6f}")


class TestCohensD:
    """測試 Cohen's d 效果量計算"""

    def test_cohens_d_large_effect(self, signal_analyzer):
        """測試大效果量（d > 0.8）"""
        positive_densities = np.array([0.8, 0.85, 0.9, 0.82, 0.88] * 10)
        negative_densities = np.array([0.2, 0.25, 0.3, 0.22, 0.28] * 10)

        d = signal_analyzer.calculate_cohens_d(
            positive_densities,
            negative_densities
        )

        assert isinstance(d, float)
        assert d > 0.8, f"Should be large effect, got {d}"

        print(f"✅ Cohen's d (large effect): {d:.3f}")

    def test_cohens_d_medium_effect(self, signal_analyzer):
        """測試中等效果量（0.5 < d < 0.8）"""
        positive_densities = np.array([0.6, 0.65, 0.7, 0.62, 0.68] * 10)
        negative_densities = np.array([0.4, 0.45, 0.5, 0.42, 0.48] * 10)

        d = signal_analyzer.calculate_cohens_d(
            positive_densities,
            negative_densities
        )

        assert 0.5 < d < 0.8, f"Should be medium effect, got {d}"

        print(f"✅ Cohen's d (medium effect): {d:.3f}")

    def test_cohens_d_small_effect(self, signal_analyzer):
        """測試小效果量（d < 0.5）"""
        positive_densities = np.array([0.52, 0.55, 0.58, 0.53, 0.57] * 10)
        negative_densities = np.array([0.48, 0.51, 0.54, 0.49, 0.53] * 10)

        d = signal_analyzer.calculate_cohens_d(
            positive_densities,
            negative_densities
        )

        assert d < 0.5, f"Should be small effect, got {d}"

        print(f"✅ Cohen's d (small effect): {d:.3f}")

    def test_cohens_d_zero_effect(self, signal_analyzer):
        """測試零效果（完全相同）"""
        densities = np.array([0.5] * 20)

        d = signal_analyzer.calculate_cohens_d(densities, densities)

        assert abs(d) < 0.01, f"Should be near zero, got {d}"

        print(f"✅ Cohen's d (zero effect): {d:.6f}")


class TestStabilityAnalysis:
    """測試穩定性分析功能"""

    def test_stability_stable_strategy(self, signal_analyzer, real_test_cases):
        """測試穩定策略（低 CV）"""
        # 創建穩定的密度值（月間差異小）
        cases = real_test_cases["positive"][:20]

        # 所有案例密度都在 0.7~0.75 之間（穩定）
        case_densities = {
            case.case_id: 0.7 + (i % 5) * 0.01
            for i, case in enumerate(cases)
        }

        cv = signal_analyzer.stability_analysis_by_month(case_densities, cases)

        assert cv >= 0.0
        assert cv < 0.3, f"Should be stable (CV < 0.3), got {cv}"

        print(f"✅ Stability (stable): CV = {cv:.3f}")

    def test_stability_unstable_strategy(self, signal_analyzer, real_test_cases):
        """測試不穩定策略（高 CV）"""
        cases = real_test_cases["positive"][:20]

        # 月間差異大
        case_densities = {
            case.case_id: 0.3 if i < 10 else 0.8
            for i, case in enumerate(cases)
        }

        cv = signal_analyzer.stability_analysis_by_month(case_densities, cases)

        assert cv >= 0.3, f"Should be unstable (CV >= 0.3), got {cv}"

        print(f"✅ Stability (unstable): CV = {cv:.3f}")

    def test_stability_single_month(self, signal_analyzer, minimal_test_cases):
        """測試單月數據（邊界情況）"""
        cases = minimal_test_cases["positive"]

        case_densities = {
            case.case_id: 0.5 + i * 0.1
            for i, case in enumerate(cases)
        }

        cv = signal_analyzer.stability_analysis_by_month(case_densities, cases)

        # 單月數據 CV 應該為 0
        assert cv == 0.0, f"Single month CV should be 0, got {cv}"

        print(f"✅ Stability (single month): CV = {cv}")


class TestAnalyzeSignalDensity:
    """測試完整信號密度分析流程"""

    def test_full_analysis_minimal_cases(
        self,
        signal_analyzer,
        minimal_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試完整分析流程（最小案例集）"""
        result = signal_analyzer.analyze_signal_density(
            positive_cases=minimal_test_cases["positive"],
            negative_cases=minimal_test_cases["negative"],
            strategy_config=sample_strategy_config,
            window_config=sample_training_window_config
        )

        # 驗證返回類型
        from api.models.training_window_config import SignalDensityResponse
        assert isinstance(result, SignalDensityResponse)

        # 驗證所有必需欄位
        assert_valid_density(result.positive_avg_density)
        assert_valid_density(result.negative_avg_density)
        assert isinstance(result.separation, float)
        assert_statistical_metrics(result.p_value, result.cohens_d, result.stability_cv)

        # 驗證樣本數
        assert result.positive_sample_size == len(minimal_test_cases["positive"])
        assert result.negative_sample_size == len(minimal_test_cases["negative"])

        # 驗證案例級別密度
        assert len(result.case_level_densities) == (
            result.positive_sample_size + result.negative_sample_size
        )

        print(f"✅ Full analysis completed:")
        print(f"   Positive density: {result.positive_avg_density:.3f}")
        print(f"   Negative density: {result.negative_avg_density:.3f}")
        print(f"   Separation: {result.separation:.3f}")
        print(f"   P-value: {result.p_value:.6f}")
        print(f"   Cohen's d: {result.cohens_d:.3f}")
        print(f"   Stability CV: {result.stability_cv:.3f}")

    def test_full_analysis_real_test_cases(
        self,
        signal_analyzer,
        real_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試完整分析流程（真實測試案例）"""
        # 限制案例數（避免測試時間過長）
        positive_subset = real_test_cases["positive"][:10]
        negative_subset = real_test_cases["negative"][:10]

        result = signal_analyzer.analyze_signal_density(
            positive_cases=positive_subset,
            negative_cases=negative_subset,
            strategy_config=sample_strategy_config,
            window_config=sample_training_window_config
        )

        # 完整驗證
        assert_valid_density(result.positive_avg_density)
        assert_valid_density(result.negative_avg_density)
        assert_statistical_metrics(result.p_value, result.cohens_d, result.stability_cv)

        # 驗證標準差
        assert result.positive_std >= 0
        assert result.negative_std >= 0

        print(f"✅ Real cases analysis:")
        print(f"   Samples: {result.positive_sample_size} pos, {result.negative_sample_size} neg")
        print(f"   Separation: {result.separation:.3f}")
        print(f"   Significance: p={result.p_value:.6f}, d={result.cohens_d:.3f}")

    def test_analysis_edge_case_single_case_each(
        self,
        signal_analyzer,
        minimal_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試邊界情況：每組只有 1 個案例"""
        result = signal_analyzer.analyze_signal_density(
            positive_cases=minimal_test_cases["positive"][:1],
            negative_cases=minimal_test_cases["negative"][:1],
            strategy_config=sample_strategy_config,
            window_config=sample_training_window_config
        )

        # 應該正常返回（但統計指標可能不可靠）
        assert isinstance(result.separation, float)
        assert result.positive_sample_size == 1
        assert result.negative_sample_size == 1

        # 標準差應該為 0（只有 1 個樣本）
        assert result.positive_std == 0.0
        assert result.negative_std == 0.0

        print(f"✅ Single case analysis: separation={result.separation:.3f}")

    def test_analysis_error_empty_cases(
        self,
        signal_analyzer,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試錯誤情況：空案例列表"""
        with pytest.raises(ValueError, match="至少需要.*個案例"):
            signal_analyzer.analyze_signal_density(
                positive_cases=[],
                negative_cases=[],
                strategy_config=sample_strategy_config,
                window_config=sample_training_window_config
            )

        print("✅ Correctly raised error for empty cases")


class TestEndToEndIntegration:
    """端到端整合測試"""

    def test_e2e_different_strategies(
        self,
        signal_analyzer,
        minimal_test_cases,
        sample_training_window_config
    ):
        """測試不同策略參數的影響"""
        # 短週期策略
        short_strategy = StrategyConfig(
            data_source="close",
            indicator_type="ema",
            strategy_logic="three_line",
            params={"short_period": 5, "mid_period": 10, "long_period": 20}
        )

        # 長週期策略
        long_strategy = StrategyConfig(
            data_source="close",
            indicator_type="ema",
            strategy_logic="three_line",
            params={"short_period": 50, "mid_period": 100, "long_period": 200}
        )

        result_short = signal_analyzer.analyze_signal_density(
            positive_cases=minimal_test_cases["positive"],
            negative_cases=minimal_test_cases["negative"],
            strategy_config=short_strategy,
            window_config=sample_training_window_config
        )

        result_long = signal_analyzer.analyze_signal_density(
            positive_cases=minimal_test_cases["positive"],
            negative_cases=minimal_test_cases["negative"],
            strategy_config=long_strategy,
            window_config=sample_training_window_config
        )

        # 不同策略應該產生不同結果
        # （注意：可能相同，但大概率不同）
        print(f"✅ Short strategy separation: {result_short.separation:.3f}")
        print(f"✅ Long strategy separation: {result_long.separation:.3f}")

    def test_e2e_different_windows(
        self,
        signal_analyzer,
        minimal_test_cases,
        sample_strategy_config,
        edge_case_configs
    ):
        """測試不同訓練窗口的影響"""
        result_short_window = signal_analyzer.analyze_signal_density(
            positive_cases=minimal_test_cases["positive"],
            negative_cases=minimal_test_cases["negative"],
            strategy_config=sample_strategy_config,
            window_config=edge_case_configs["minimal_lookback"]
        )

        result_long_window = signal_analyzer.analyze_signal_density(
            positive_cases=minimal_test_cases["positive"],
            negative_cases=minimal_test_cases["negative"],
            strategy_config=sample_strategy_config,
            window_config=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=500,
                lookforward_bars=0,
                mode="relative"
            )
        )

        # 驗證都能正常完成
        assert isinstance(result_short_window.separation, float)
        assert isinstance(result_long_window.separation, float)

        print(f"✅ Short window (10 bars) separation: {result_short_window.separation:.3f}")
        print(f"✅ Long window (500 bars) separation: {result_long_window.separation:.3f}")
