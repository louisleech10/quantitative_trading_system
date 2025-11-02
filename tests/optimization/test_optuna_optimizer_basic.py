"""
OptunaOptimizer基礎單元測試

測試核心邏輯,不依賴真實案例數據（使用Mock）。

測試覆蓋:
1. Study創建/載入（驗證斷點續跑）
2. Sampler配置工廠（TPE/CmaEs/Random）
3. Pruner配置工廠（Median/Percentile/None）
4. 參數採樣範圍（驗證無硬編碼）
5. 參數約束驗證（short < mid < long剪枝）

Author: Claude (Phase 3.5)
Date: 2025-11-02
"""

import pytest
import optuna
from optuna.samplers import TPESampler, CmaEsSampler, RandomSampler
from optuna.pruners import MedianPruner, PercentilePruner, NopPruner
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
from typing import Tuple

from momentum.Optimization.optuna_optimizer import (
    OptunaOptimizer,
    ParameterRanges,
    OptimizationResult
)
from api.models.training_window_config import TrainingWindowConfig


class TestOptunaOptimizerBasic:
    """OptunaOptimizer基礎測試套件"""

    @pytest.fixture
    def temp_storage(self):
        """臨時SQLite數據庫路徑"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        storage = f"sqlite:///{db_path}"
        yield storage
        # 清理
        if os.path.exists(db_path):
            os.remove(db_path)

    @pytest.fixture
    def default_optimizer(self, temp_storage):
        """默認配置的優化器（用於大多數測試）"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="test_study",
                    storage=temp_storage,
                    sampler_type="TPE",
                    n_trials=5,
                    random_seed=42
                )
                return optimizer

    # ==================== 測試1: Study創建與載入 ====================

    def test_create_study_new(self, temp_storage):
        """測試創建新Study"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="new_study",
                    storage=temp_storage,
                    n_trials=10
                )

                study = optimizer.create_study()

                # 驗證
                assert study is not None
                assert study.study_name == "new_study"
                assert study.direction == optuna.study.StudyDirection.MAXIMIZE
                assert len(study.trials) == 0  # 新Study無試驗

    def test_create_study_load_existing(self, temp_storage):
        """測試載入已存在的Study（斷點續跑）"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                # 步驟1: 創建第一個optimizer並執行一些試驗
                optimizer1 = OptunaOptimizer(
                    study_name="resume_study",
                    storage=temp_storage,
                    n_trials=3
                )
                study1 = optimizer1.create_study()

                # 模擬執行試驗（直接添加試驗記錄）
                for i in range(3):
                    trial = study1.ask()
                    study1.tell(trial, i * 0.1)  # 模擬目標值

                assert len(study1.trials) == 3

                # 步驟2: 創建第二個optimizer載入同一Study
                optimizer2 = OptunaOptimizer(
                    study_name="resume_study",  # 相同名稱
                    storage=temp_storage,
                    n_trials=2
                )
                study2 = optimizer2.create_study()

                # 驗證: 應載入已有的3個試驗
                assert len(study2.trials) == 3
                assert study2.trials[0].value == 0.0
                assert study2.trials[1].value == 0.1
                assert study2.trials[2].value == 0.2

    # ==================== 測試2: Sampler配置工廠 ====================

    def test_create_sampler_tpe(self, default_optimizer):
        """測試創建TPESampler"""
        default_optimizer.sampler_type = "TPE"
        sampler = default_optimizer._create_sampler()

        assert isinstance(sampler, TPESampler)
        # 驗證隨機種子設置
        assert sampler._rng.bit_generator.state['state']['state'] is not None

    def test_create_sampler_cmaes(self, default_optimizer):
        """測試創建CmaEsSampler"""
        default_optimizer.sampler_type = "CmaEs"
        sampler = default_optimizer._create_sampler()

        assert isinstance(sampler, CmaEsSampler)

    def test_create_sampler_random(self, default_optimizer):
        """測試創建RandomSampler"""
        default_optimizer.sampler_type = "Random"
        sampler = default_optimizer._create_sampler()

        assert isinstance(sampler, RandomSampler)

    def test_create_sampler_invalid(self, default_optimizer):
        """測試無效Sampler類型拋出錯誤"""
        default_optimizer.sampler_type = "InvalidSampler"

        with pytest.raises(ValueError, match="Unknown sampler"):
            default_optimizer._create_sampler()

    # ==================== 測試3: Pruner配置工廠 ====================

    def test_create_pruner_median(self, default_optimizer):
        """測試創建MedianPruner"""
        default_optimizer.pruner_type = "Median"
        pruner = default_optimizer._create_pruner()

        assert isinstance(pruner, MedianPruner)

    def test_create_pruner_percentile(self, default_optimizer):
        """測試創建PercentilePruner"""
        default_optimizer.pruner_type = "Percentile"
        pruner = default_optimizer._create_pruner()

        assert isinstance(pruner, PercentilePruner)

    def test_create_pruner_none(self, default_optimizer):
        """測試創建NopPruner（無剪枝）"""
        default_optimizer.pruner_type = None
        pruner = default_optimizer._create_pruner()

        assert isinstance(pruner, NopPruner)

    def test_create_pruner_invalid(self, default_optimizer):
        """測試無效Pruner類型拋出錯誤"""
        default_optimizer.pruner_type = "InvalidPruner"

        with pytest.raises(ValueError, match="Unknown pruner"):
            default_optimizer._create_pruner()

    # ==================== 測試4: 參數範圍配置 ====================

    def test_parameter_ranges_default(self, default_optimizer):
        """測試默認參數範圍"""
        ranges = default_optimizer.parameter_ranges

        assert ranges.ema_short_range == (5, 200)
        assert ranges.ema_mid_range == (10, 200)
        assert ranges.ema_long_range == (20, 200)
        assert 'close' in ranges.data_sources
        assert 'three_line' in ranges.strategy_logics

    def test_parameter_ranges_custom(self, temp_storage):
        """測試自定義參數範圍（驗證無硬編碼）"""
        custom_ranges = ParameterRanges(
            ema_short_range=(3, 50),
            ema_mid_range=(15, 100),
            ema_long_range=(50, 150),
            data_sources=['close', 'volume'],
            strategy_logics=['three_line']
        )

        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="custom_ranges_test",
                    storage=temp_storage,
                    parameter_ranges=custom_ranges
                )

                # 驗證
                assert optimizer.parameter_ranges.ema_short_range == (3, 50)
                assert optimizer.parameter_ranges.data_sources == ['close', 'volume']

    # ==================== 測試5: 參數約束驗證 ====================

    @pytest.mark.asyncio
    async def test_parameter_constraint_three_line_valid(self, default_optimizer, temp_storage):
        """測試三線排列合法參數（short < mid < long）"""
        # Mock信號分析服務
        mock_response = Mock()
        mock_response.positive_avg_density = 0.6
        mock_response.negative_avg_density = 0.3

        default_optimizer.signal_service.analyze_signal_density = AsyncMock(return_value=mock_response)
        default_optimizer.positive_cases = ["case1"]
        default_optimizer.negative_cases = ["case2"]
        default_optimizer.training_window = Mock(spec=TrainingWindowConfig)

        # 創建Study
        study = default_optimizer.create_study()

        # 創建Trial並模擬合法參數
        trial = study.ask()
        trial.suggest_categorical('data_source', ['close'])
        trial.suggest_categorical('strategy_logic', ['three_line'])
        trial.suggest_int('ema_short', 5, 10)
        trial.suggest_int('ema_mid', 20, 30)
        trial.suggest_int('ema_long', 50, 60)

        # 手動設置參數（模擬Optuna採樣）
        trial._cached_frozen_trial.params = {
            'data_source': 'close',
            'strategy_logic': 'three_line',
            'ema_short': 7,
            'ema_mid': 25,
            'ema_long': 55
        }

        # 調用目標函數
        result = await default_optimizer._objective_function(trial)

        # 驗證: 合法參數應返回正常separation值
        assert result == pytest.approx(0.3, abs=0.01)  # 0.6 - 0.3 = 0.3
        assert default_optimizer.signal_service.analyze_signal_density.called

    @pytest.mark.asyncio
    async def test_parameter_constraint_three_line_invalid(self, default_optimizer):
        """測試三線排列非法參數（違反short < mid < long）應被剪枝"""
        default_optimizer.positive_cases = ["case1"]
        default_optimizer.negative_cases = ["case2"]
        default_optimizer.training_window = Mock(spec=TrainingWindowConfig)

        # 創建Study
        study = default_optimizer.create_study()
        trial = study.ask()

        # 手動設置非法參數（ema_short > ema_mid）
        trial._cached_frozen_trial.params = {
            'data_source': 'close',
            'strategy_logic': 'three_line',
            'ema_short': 30,   # 違反約束
            'ema_mid': 20,     # short > mid
            'ema_long': 50
        }

        # 調用目標函數,應拋出TrialPruned
        with pytest.raises(optuna.TrialPruned):
            await default_optimizer._objective_function(trial)

    # ==================== 測試6: 錯誤處理分類 ====================

    @pytest.mark.asyncio
    async def test_error_handling_retryable(self, default_optimizer):
        """測試可重試錯誤（網絡錯誤）返回較差值"""
        # Mock服務拋出ConnectionError
        default_optimizer.signal_service.analyze_signal_density = AsyncMock(
            side_effect=ConnectionError("Network timeout")
        )
        default_optimizer.positive_cases = ["case1"]
        default_optimizer.negative_cases = ["case2"]
        default_optimizer.training_window = Mock(spec=TrainingWindowConfig)

        study = default_optimizer.create_study()
        trial = study.ask()
        trial._cached_frozen_trial.params = {
            'data_source': 'close',
            'strategy_logic': 'short_long_cross',
            'ema_short': 7,
            'ema_long': 25
        }

        # 調用目標函數
        result = await default_optimizer._objective_function(trial)

        # 驗證: 可重試錯誤應返回-500.0
        assert result == -500.0

    @pytest.mark.asyncio
    async def test_error_handling_non_retryable(self, default_optimizer):
        """測試不可重試錯誤（參數錯誤）應被剪枝"""
        # Mock服務拋出ValueError
        default_optimizer.signal_service.analyze_signal_density = AsyncMock(
            side_effect=ValueError("Invalid parameter")
        )
        default_optimizer.positive_cases = ["case1"]
        default_optimizer.negative_cases = ["case2"]
        default_optimizer.training_window = Mock(spec=TrainingWindowConfig)

        study = default_optimizer.create_study()
        trial = study.ask()
        trial._cached_frozen_trial.params = {
            'data_source': 'close',
            'strategy_logic': 'short_long_cross',
            'ema_short': 7,
            'ema_long': 25
        }

        # 調用目標函數,應拋出TrialPruned
        with pytest.raises(optuna.TrialPruned):
            await default_optimizer._objective_function(trial)

    # ==================== 測試7: 輔助方法 ====================

    def test_get_best_trial_no_study(self, default_optimizer):
        """測試未創建Study時獲取最佳試驗拋出錯誤"""
        with pytest.raises(ValueError, match="Study not created"):
            default_optimizer.get_best_trial()

    def test_get_trials_dataframe_no_study(self, default_optimizer):
        """測試未創建Study時獲取試驗歷史拋出錯誤"""
        with pytest.raises(ValueError, match="Study not created"):
            default_optimizer.get_trials_dataframe()


# ==================== pytest配置 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
