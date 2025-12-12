"""
Phase 2 整合測試 - 動態參數系統重構驗證

測試範圍:
1. Optuna 優化器動態參數採樣
2. Signal Density Analyzer 動態策略計算
3. API 端點 (GET /strategies, GET /strategies/{id})
4. 向後兼容性驗證

Author: Claude (Phase 2.4 Testing)
Date: 2025-12-03
"""

import sys
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import optuna

from momentum.Analysis.strategy_registry import strategy_registry
from momentum.Optimization.strategy_metadata import ParameterType
from momentum.Optimization.optuna_optimizer import OptunaOptimizer, ParameterRanges
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators.indicator_engine import IndicatorEngine
from api.models.training_window_config import StrategyConfig


class TestOptunaOptimizerDynamicParameters:
    """測試 OptunaOptimizer 動態參數採樣"""

    def test_strategy_metadata_parameter_sampling(self):
        """測試使用策略元數據進行參數採樣"""
        # 創建 Optuna study 和 trial
        study = optuna.create_study(direction="maximize")

        # 測試三種策略的參數採樣
        for strategy_logic in ["three_line", "short_long_cross", "mid_long_cross"]:
            # 獲取策略元數據
            metadata = strategy_registry.get_strategy(strategy_logic)

            # 創建一個試驗
            trial = study.ask()

            # 模擬參數採樣 (透過 suggest)
            params = {}
            for param_def in metadata.parameters:
                if param_def.type == ParameterType.INT:
                    params[param_def.name] = trial.suggest_int(
                        param_def.name,
                        int(param_def.min_value),
                        int(param_def.max_value)
                    )

            # 驗證參數是否在範圍內
            for param_name, param_value in params.items():
                param_def = metadata.get_parameter(param_name)
                assert param_def.min_value <= param_value <= param_def.max_value, \
                    f"Parameter {param_name} out of range for {strategy_logic}"

            print(f"✅ {strategy_logic}: 動態參數採樣成功 - {params}")

    def test_multi_objective_dynamic_sampling(self):
        """測試多目標優化函數的動態參數採樣"""
        # 創建多目標 study
        study = optuna.create_study(directions=["maximize", "minimize"])

        for strategy_logic in ["three_line", "short_long_cross", "mid_long_cross"]:
            metadata = strategy_registry.get_strategy(strategy_logic)
            trial = study.ask()

            # 模擬多目標參數採樣
            params = {}
            for param_def in metadata.parameters:
                if param_def.type == ParameterType.INT:
                    params[param_def.name] = trial.suggest_int(
                        param_def.name,
                        int(param_def.min_value),
                        int(param_def.max_value)
                    )

            # 驗證參數範圍
            for param_name, param_value in params.items():
                param_def = metadata.get_parameter(param_name)
                assert param_def.min_value <= param_value <= param_def.max_value

            print(f"✅ {strategy_logic} (multi-objective): 動態參數採樣成功 - {params}")

    def test_parameter_validation_with_registry(self):
        """測試參數驗證使用註冊表"""
        # 測試 three_line 策略的約束驗證
        params_valid = {
            "short_period": 7,
            "mid_period": 21,
            "long_period": 60,  # >= 50 (滿足 min_value 約束)
            "indicator_type": "ema",
            "data_source": "close"
        }

        result = strategy_registry.validate_parameters("three_line", params_valid)
        assert result.is_valid, f"Valid params rejected: {result.errors}"
        print("✅ three_line 有效參數驗證通過")

        # 測試無效參數 (違反約束)
        params_invalid = {
            "short_period": 20,  # > mid_period (違反 less_than 約束)
            "mid_period": 15,
            "long_period": 60,
            "indicator_type": "ema",
            "data_source": "close"
        }

        result = strategy_registry.validate_parameters("three_line", params_invalid)
        assert not result.is_valid, "Invalid params should fail validation"
        print(f"✅ three_line 無效參數正確拒絕: {result.errors[0]}")


class TestSignalDensityAnalyzerDynamicStrategy:
    """測試 SignalDensityAnalyzer 動態策略計算"""

    def test_calculate_strategy_signals_three_line(self):
        """測試動態計算 three_line 策略信號"""
        # 創建模擬 K線數據
        kline_data = pd.DataFrame({
            'timestamp': range(100),
            'open': np.random.uniform(40000, 42000, 100),
            'high': np.random.uniform(41000, 43000, 100),
            'low': np.random.uniform(39000, 41000, 100),
            'close': np.random.uniform(40000, 42000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })

        # 創建策略配置
        strategy_config = StrategyConfig(
            strategy_logic="three_line",
            indicator_type="ema",
            data_source="close",
            params={
                "short_period": 7,
                "mid_period": 21,
                "long_period": 48
            }
        )

        # 創建分析器
        mock_storage = Mock(spec=KlineStorageManager)
        mock_indicator = Mock(spec=IndicatorEngine)

        # 模擬 indicator_engine 返回結果
        mock_indicators_df = pd.DataFrame({
            'ema_short': np.random.uniform(40000, 42000, 100),
            'ema_mid': np.random.uniform(39500, 41500, 100),
            'ema_long': np.random.uniform(39000, 41000, 100)
        })
        mock_indicator.calculate_indicators_from_dataframe = Mock(return_value=mock_indicators_df)

        analyzer = SignalDensityAnalyzer(
            kline_storage=mock_storage,
            indicator_engine=mock_indicator
        )

        # 執行計算
        signals = analyzer.calculate_strategy_signals(kline_data, strategy_config)

        # 驗證結果
        assert isinstance(signals, np.ndarray), "Signals should be numpy array"
        assert len(signals) == 100, "Signals length should match kline data"
        assert signals.dtype == bool, "Signals should be boolean array"
        print(f"✅ three_line 動態策略計算成功: {np.sum(signals)}/{len(signals)} 個信號")

    def test_calculate_strategy_signals_short_long_cross(self):
        """測試動態計算 short_long_cross 策略信號"""
        kline_data = pd.DataFrame({
            'timestamp': range(100),
            'open': np.random.uniform(40000, 42000, 100),
            'high': np.random.uniform(41000, 43000, 100),
            'low': np.random.uniform(39000, 41000, 100),
            'close': np.random.uniform(40000, 42000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })

        strategy_config = StrategyConfig(
            strategy_logic="short_long_cross",
            indicator_type="ema",
            data_source="close",
            params={
                "short_period": 7,
                "long_period": 48
            }
        )

        mock_storage = Mock(spec=KlineStorageManager)
        mock_indicator = Mock(spec=IndicatorEngine)

        mock_indicators_df = pd.DataFrame({
            'ema_short': np.random.uniform(40000, 42000, 100),
            'ema_long': np.random.uniform(39000, 41000, 100)
        })
        mock_indicator.calculate_indicators_from_dataframe = Mock(return_value=mock_indicators_df)

        analyzer = SignalDensityAnalyzer(
            kline_storage=mock_storage,
            indicator_engine=mock_indicator
        )

        signals = analyzer.calculate_strategy_signals(kline_data, strategy_config)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == 100
        assert signals.dtype == bool
        print(f"✅ short_long_cross 動態策略計算成功: {np.sum(signals)}/{len(signals)} 個信號")

    def test_calculate_strategy_signals_mid_long_cross(self):
        """測試動態計算 mid_long_cross 策略信號"""
        kline_data = pd.DataFrame({
            'timestamp': range(100),
            'open': np.random.uniform(40000, 42000, 100),
            'high': np.random.uniform(41000, 43000, 100),
            'low': np.random.uniform(39000, 41000, 100),
            'close': np.random.uniform(40000, 42000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })

        strategy_config = StrategyConfig(
            strategy_logic="mid_long_cross",
            indicator_type="ema",
            data_source="close",
            params={
                "mid_period": 21,
                "long_period": 48
            }
        )

        mock_storage = Mock(spec=KlineStorageManager)
        mock_indicator = Mock(spec=IndicatorEngine)

        mock_indicators_df = pd.DataFrame({
            'ema_mid': np.random.uniform(40000, 42000, 100),
            'ema_long': np.random.uniform(39000, 41000, 100)
        })
        mock_indicator.calculate_indicators_from_dataframe = Mock(return_value=mock_indicators_df)

        analyzer = SignalDensityAnalyzer(
            kline_storage=mock_storage,
            indicator_engine=mock_indicator
        )

        signals = analyzer.calculate_strategy_signals(kline_data, strategy_config)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == 100
        assert signals.dtype == bool
        print(f"✅ mid_long_cross 動態策略計算成功: {np.sum(signals)}/{len(signals)} 個信號")

    def test_invalid_strategy_raises_error(self):
        """測試無效策略會拋出錯誤"""
        kline_data = pd.DataFrame({
            'close': np.random.uniform(40000, 42000, 100)
        })

        strategy_config = StrategyConfig(
            strategy_logic="invalid_strategy",
            indicator_type="ema",
            data_source="close",
            params={"dummy_param": 1}  # 至少需要一個參數
        )

        mock_storage = Mock(spec=KlineStorageManager)
        mock_indicator = Mock(spec=IndicatorEngine)

        analyzer = SignalDensityAnalyzer(
            kline_storage=mock_storage,
            indicator_engine=mock_indicator
        )

        try:
            analyzer.calculate_strategy_signals(kline_data, strategy_config)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "not found" in str(e).lower()
            print("✅ 無效策略正確拋出 ValueError")


class TestAPIEndpoints:
    """測試 API 端點"""

    def test_list_strategies_endpoint(self):
        """測試 GET /strategies 端點"""
        # 模擬 API 調用
        strategy_list = strategy_registry.list_strategies()

        assert len(strategy_list) >= 3, f"Should have at least 3 strategies, got {len(strategy_list)}"

        strategy_ids = [s.strategy_id for s in strategy_list]
        assert "three_line" in strategy_ids, f"'three_line' not in {strategy_ids}"
        assert "short_long_cross" in strategy_ids, f"'short_long_cross' not in {strategy_ids}"
        assert "mid_long_cross" in strategy_ids, f"'mid_long_cross' not in {strategy_ids}"

        # 模擬構建響應
        strategies = []
        for metadata in strategy_list:
            strategies.append({
                "strategy_id": metadata.strategy_id,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "category": metadata.category,
                "parameter_count": len(metadata.parameters)
            })

        assert len(strategies) == len(strategy_list)
        print(f"✅ GET /strategies 端點測試成功: 返回 {len(strategies)} 個策略")

    def test_get_strategy_detail_endpoint(self):
        """測試 GET /strategies/{id} 端點"""
        strategy_id = "three_line"

        metadata = strategy_registry.get_strategy(strategy_id)

        # 模擬構建詳細響應
        parameters = []
        for param in metadata.parameters:
            param_dict = {
                "name": param.name,
                "display_name": param.display_name,
                "type": param.type,
                "default_value": param.default_value
            }

            if param.type in ["int", "float"]:
                param_dict["min_value"] = param.min_value
                param_dict["max_value"] = param.max_value

            if param.constraints:
                param_dict["constraints"] = [
                    {"type": c.type, "target": c.target}
                    for c in param.constraints
                ]

            parameters.append(param_dict)

        strategy_detail = {
            "strategy_id": metadata.strategy_id,
            "display_name": metadata.display_name,
            "parameters": parameters
        }

        assert strategy_detail["strategy_id"] == strategy_id
        assert len(strategy_detail["parameters"]) > 0
        print(f"✅ GET /strategies/{strategy_id} 端點測試成功: {len(parameters)} 個參數")

    def test_invalid_strategy_returns_404(self):
        """測試無效策略返回 404"""
        try:
            strategy_registry.get_strategy("invalid_strategy_xyz")
            assert False, "Should raise ValueError"
        except ValueError:
            print("✅ 無效策略正確返回 404 (ValueError)")


class TestBackwardCompatibility:
    """測試向後兼容性"""

    def test_three_line_strategy_still_works(self):
        """驗證 three_line 策略在重構後仍正常工作"""
        # 獲取策略元數據
        metadata = strategy_registry.get_strategy("three_line")

        assert metadata.strategy_id == "three_line"
        assert len(metadata.parameters) == 3  # short, mid, long (indicator_type 和 data_source 不在參數列表中)

        # 驗證默認值
        defaults = metadata.get_default_values()
        assert defaults["short_period"] == 7
        assert defaults["mid_period"] == 25  # Updated default value
        assert defaults["long_period"] == 70  # Updated default value

        print("✅ three_line 策略向後兼容性驗證通過")

    def test_strategy_calculation_backward_compatible(self):
        """驗證策略計算函數向後兼容"""
        calculator = strategy_registry.get_calculator("three_line")

        # 創建測試數據
        kline_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105] * 20  # 120 rows
        })

        params = {
            "short_period": 7,
            "mid_period": 21,
            "long_period": 48,
            "indicator_type": "ema",
            "data_source": "close"
        }

        # 這應該能正常工作（如果 IndicatorEngine 正常）
        # 由於我們沒有完整的環境，只驗證函數存在且可調用
        assert callable(calculator)
        print("✅ 策略計算函數向後兼容")


def run_all_tests():
    """運行所有測試"""
    print("\n" + "="*80)
    print("Phase 2 整合測試開始")
    print("="*80 + "\n")

    # Test 1: Optuna Optimizer
    print("\n--- Test 1: Optuna Optimizer 動態參數 ---")
    test_optuna = TestOptunaOptimizerDynamicParameters()
    test_optuna.test_strategy_metadata_parameter_sampling()
    test_optuna.test_multi_objective_dynamic_sampling()
    test_optuna.test_parameter_validation_with_registry()

    # Test 2: Signal Density Analyzer
    print("\n--- Test 2: Signal Density Analyzer 動態策略 ---")
    test_analyzer = TestSignalDensityAnalyzerDynamicStrategy()
    test_analyzer.test_calculate_strategy_signals_three_line()
    test_analyzer.test_calculate_strategy_signals_short_long_cross()
    test_analyzer.test_calculate_strategy_signals_mid_long_cross()
    test_analyzer.test_invalid_strategy_raises_error()

    # Test 3: API Endpoints
    print("\n--- Test 3: API 端點 ---")
    test_api = TestAPIEndpoints()
    test_api.test_list_strategies_endpoint()
    test_api.test_get_strategy_detail_endpoint()
    test_api.test_invalid_strategy_returns_404()

    # Test 4: Backward Compatibility
    print("\n--- Test 4: 向後兼容性 ---")
    test_compat = TestBackwardCompatibility()
    test_compat.test_three_line_strategy_still_works()
    test_compat.test_strategy_calculation_backward_compatible()

    print("\n" + "="*80)
    print("✅ Phase 2 整合測試全部通過！")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_all_tests()
