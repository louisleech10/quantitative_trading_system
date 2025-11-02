"""
OptunaOptimizer進階單元測試 - Day 3-4 特性測試

測試Day 3-4新增的容錯與監控功能:
1. CheckpointManager - 檢查點保存與恢復
2. ErrorHandler - 錯誤分類與重試機制
3. ProgressMonitor - 進度追蹤與里程碑通知
4. 多目標優化 - Pareto前沿分析

Author: Claude (Phase 3.5 Day 7-8)
Date: 2025-11-02
"""

import pytest
import optuna
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import tempfile
import os
import pickle
import time
from pathlib import Path
from typing import Dict, Any

from momentum.Optimization.optuna_optimizer import (
    OptunaOptimizer,
    ParameterRanges,
    OptimizationResult
)
from momentum.Optimization.checkpoint_manager import CheckpointManager
from momentum.Optimization.error_handler import OptimizationErrorHandler, ErrorType
from momentum.Optimization.progress_monitor import ProgressMonitor, ProgressStats
from api.models.training_window_config import TrainingWindowConfig


class TestCheckpointManager:
    """CheckpointManager測試套件"""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """臨時檢查點目錄"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def checkpoint_manager(self, temp_checkpoint_dir):
        """CheckpointManager實例"""
        return CheckpointManager(checkpoint_dir=temp_checkpoint_dir, interval_trials=10)

    def test_should_save_checkpoint_true(self, checkpoint_manager):
        """測試達到間隔時應保存檢查點"""
        assert checkpoint_manager.should_save_checkpoint(10) == True
        assert checkpoint_manager.should_save_checkpoint(20) == True
        assert checkpoint_manager.should_save_checkpoint(50) == True

    def test_should_save_checkpoint_false(self, checkpoint_manager):
        """測試未達到間隔時不應保存檢查點"""
        assert checkpoint_manager.should_save_checkpoint(5) == False
        assert checkpoint_manager.should_save_checkpoint(15) == False
        assert checkpoint_manager.should_save_checkpoint(23) == False

    def test_save_checkpoint_creates_file(self, checkpoint_manager, temp_checkpoint_dir):
        """測試保存檢查點創建文件"""
        study_name = "test_study"
        checkpoint_data = {
            'study_name': study_name,
            'n_trials': 10,
            'best_value': 0.456,
            'best_params': {'ema_short': 7}
        }

        checkpoint_path = checkpoint_manager.save_checkpoint(
            study_name=study_name,
            checkpoint_data=checkpoint_data
        )

        # 驗證文件存在
        assert os.path.exists(checkpoint_path)
        assert checkpoint_path.endswith('.pkl')

        # 驗證文件內容
        with open(checkpoint_path, 'rb') as f:
            loaded_data = pickle.load(f)
            assert loaded_data['study_name'] == study_name
            assert loaded_data['best_value'] == 0.456

    def test_load_checkpoint_existing(self, checkpoint_manager, temp_checkpoint_dir):
        """測試載入已存在的檢查點"""
        study_name = "test_study"
        checkpoint_data = {'best_value': 0.789}

        # 保存檢查點
        checkpoint_path = checkpoint_manager.save_checkpoint(study_name, checkpoint_data)

        # 載入檢查點
        loaded_data = checkpoint_manager.load_checkpoint(study_name)

        assert loaded_data is not None
        assert loaded_data['best_value'] == 0.789

    def test_load_checkpoint_nonexistent(self, checkpoint_manager):
        """測試載入不存在的檢查點返回None"""
        loaded_data = checkpoint_manager.load_checkpoint("nonexistent_study")
        assert loaded_data is None

    def test_list_checkpoints(self, checkpoint_manager, temp_checkpoint_dir):
        """測試列出所有檢查點"""
        # 保存3個檢查點
        checkpoint_manager.save_checkpoint("study1", {'value': 1})
        checkpoint_manager.save_checkpoint("study2", {'value': 2})
        checkpoint_manager.save_checkpoint("study3", {'value': 3})

        checkpoints = checkpoint_manager.list_checkpoints()

        assert len(checkpoints) >= 3  # >= 因為可能有舊檢查點


class TestErrorHandler:
    """ErrorHandler測試套件"""

    @pytest.fixture
    def error_handler(self):
        """ErrorHandler實例"""
        return OptimizationErrorHandler(max_retries=3, base_delay=0.1)

    def test_classify_error_retryable(self, error_handler):
        """測試分類可重試錯誤"""
        errors = [
            ConnectionError("Network timeout"),
            TimeoutError("Request timeout"),
            OSError("Resource temporarily unavailable")
        ]

        for error in errors:
            error_type = error_handler.classify_error(error)
            assert error_type == ErrorType.RETRYABLE

    def test_classify_error_non_retryable(self, error_handler):
        """測試分類不可重試錯誤"""
        errors = [
            ValueError("Invalid parameter"),
            TypeError("Wrong type"),
            KeyError("Missing key")
        ]

        for error in errors:
            error_type = error_handler.classify_error(error)
            assert error_type == ErrorType.NON_RETRYABLE

    def test_classify_error_fatal(self, error_handler):
        """測試分類致命錯誤"""
        error = MemoryError("Out of memory")
        error_type = error_handler.classify_error(error)
        assert error_type == ErrorType.FATAL

    def test_should_retry_within_limit(self, error_handler):
        """測試在重試次數限制內應重試"""
        assert error_handler.should_retry(0) == True
        assert error_handler.should_retry(1) == True
        assert error_handler.should_retry(2) == True

    def test_should_retry_exceed_limit(self, error_handler):
        """測試超過重試次數限制不應重試"""
        assert error_handler.should_retry(3) == False
        assert error_handler.should_retry(5) == False

    def test_calculate_delay_exponential_backoff(self, error_handler):
        """測試指數退避延遲計算"""
        delay0 = error_handler.calculate_delay(0)
        delay1 = error_handler.calculate_delay(1)
        delay2 = error_handler.calculate_delay(2)

        # 驗證指數增長（base_delay * 2^attempt）
        assert delay0 == pytest.approx(0.1, abs=0.05)  # 0.1 * 2^0 = 0.1
        assert delay1 == pytest.approx(0.2, abs=0.05)  # 0.1 * 2^1 = 0.2
        assert delay2 == pytest.approx(0.4, abs=0.05)  # 0.1 * 2^2 = 0.4


class TestProgressMonitor:
    """ProgressMonitor測試套件"""

    @pytest.fixture
    def progress_monitor(self):
        """ProgressMonitor實例"""
        callback = Mock()
        monitor = ProgressMonitor(
            total_trials=100,
            notification_callback=callback
        )
        return monitor

    def test_initialization(self, progress_monitor):
        """測試初始化狀態"""
        assert progress_monitor.total_trials == 100
        assert progress_monitor.completed_trials == 0
        assert progress_monitor.start_time is not None

    def test_on_trial_complete_updates_stats(self, progress_monitor):
        """測試試驗完成後更新統計"""
        stats = progress_monitor.on_trial_complete(
            trial_number=0,
            value=0.456,
            params={'ema_short': 7},
            state='COMPLETE'
        )

        assert stats.completed_trials == 1
        assert stats.completion_percentage == pytest.approx(1.0)
        assert stats.best_value == 0.456

    def test_milestone_notification(self, progress_monitor):
        """測試里程碑通知（25%/50%/75%）"""
        # 完成25次試驗（25%）
        for i in range(25):
            progress_monitor.on_trial_complete(i, 0.5, {}, 'COMPLETE')

        # 驗證回調被調用（milestone_reached事件）
        calls = progress_monitor.notification_callback.call_args_list
        milestone_calls = [c for c in calls if c[0][0] == 'milestone_reached']
        assert len(milestone_calls) >= 1

        # 驗證25%里程碑
        milestone_25 = next(c for c in milestone_calls if c[0][1]['milestone_percentage'] == 25)
        assert milestone_25 is not None

    def test_new_best_value_notification(self, progress_monitor):
        """測試新最佳值通知"""
        # 第一次試驗（best = 0.3）
        progress_monitor.on_trial_complete(0, 0.3, {'param': 1}, 'COMPLETE')

        # 第二次試驗（best = 0.5，更好）
        progress_monitor.on_trial_complete(1, 0.5, {'param': 2}, 'COMPLETE')

        # 驗證new_best_value事件被調用
        calls = progress_monitor.notification_callback.call_args_list
        new_best_calls = [c for c in calls if c[0][0] == 'new_best_value']
        assert len(new_best_calls) >= 2  # 至少2次（第一次和更新）

    def test_eta_calculation(self, progress_monitor):
        """測試ETA計算"""
        # 完成10次試驗
        for i in range(10):
            progress_monitor.on_trial_complete(i, 0.5, {}, 'COMPLETE')
            time.sleep(0.01)  # 模擬執行時間

        stats = progress_monitor.get_current_stats()

        # 驗證ETA存在且合理
        assert stats.estimated_remaining_time is not None
        assert stats.estimated_remaining_time > 0

    def test_trials_per_hour_calculation(self, progress_monitor):
        """測試每小時試驗數計算"""
        # 完成20次試驗
        for i in range(20):
            progress_monitor.on_trial_complete(i, 0.5, {}, 'COMPLETE')
            time.sleep(0.01)

        stats = progress_monitor.get_current_stats()

        # 驗證trials_per_hour存在且合理
        assert stats.trials_per_hour > 0


class TestOptunaOptimizerIntegration:
    """OptunaOptimizer整合測試（Day 3-4特性）"""

    @pytest.fixture
    def temp_storage(self):
        """臨時SQLite數據庫"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        storage = f"sqlite:///{db_path}"
        yield storage
        if os.path.exists(db_path):
            os.remove(db_path)

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """臨時檢查點目錄"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_optimizer_with_checkpoint_manager(self, temp_storage, temp_checkpoint_dir):
        """測試優化器整合CheckpointManager"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="checkpoint_test",
                    storage=temp_storage,
                    n_trials=5,
                    checkpoint_dir=temp_checkpoint_dir,
                    checkpoint_interval=2
                )

                # 驗證CheckpointManager已初始化
                assert optimizer.checkpoint_manager is not None
                assert optimizer.checkpoint_manager.interval_trials == 2

    def test_optimizer_with_error_handler(self, temp_storage):
        """測試優化器整合ErrorHandler"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="error_test",
                    storage=temp_storage,
                    n_trials=5,
                    max_retries=5,
                    retry_base_delay=0.5
                )

                # 驗證ErrorHandler已初始化
                assert optimizer.error_handler is not None
                assert optimizer.error_handler.max_retries == 5
                assert optimizer.error_handler.base_delay == 0.5

    def test_optimizer_with_progress_monitor(self, temp_storage):
        """測試優化器整合ProgressMonitor"""
        callback = Mock()

        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="progress_test",
                    storage=temp_storage,
                    n_trials=10,
                    enable_progress_monitor=True,
                    progress_notification_callback=callback
                )

                # 驗證ProgressMonitor配置已保存
                assert optimizer.enable_progress_monitor == True
                assert optimizer.progress_notification_callback == callback

    @pytest.mark.asyncio
    async def test_retry_wrapper_success_on_first_attempt(self, temp_storage):
        """測試重試包裝器：第一次嘗試成功"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="retry_test",
                    storage=temp_storage,
                    n_trials=5
                )

                # Mock目標函數成功返回
                mock_objective = AsyncMock(return_value=0.789)
                optimizer._objective_function = mock_objective

                # 創建trial
                study = optimizer.create_study()
                trial = study.ask()

                # 調用重試包裝器
                result = await optimizer._objective_function_with_retry(trial)

                # 驗證：第一次嘗試成功，只調用1次
                assert result == 0.789
                assert mock_objective.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_wrapper_retryable_error(self, temp_storage):
        """測試重試包裝器：可重試錯誤會重試"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="retry_test",
                    storage=temp_storage,
                    n_trials=5,
                    max_retries=3,
                    retry_base_delay=0.01
                )

                # Mock目標函數：前2次拋出ConnectionError，第3次成功
                mock_objective = AsyncMock(
                    side_effect=[
                        ConnectionError("Network error"),
                        ConnectionError("Network error"),
                        0.456
                    ]
                )
                optimizer._objective_function = mock_objective

                # 創建trial
                study = optimizer.create_study()
                trial = study.ask()

                # 調用重試包裝器
                result = await optimizer._objective_function_with_retry(trial)

                # 驗證：重試3次，最終成功
                assert result == 0.456
                assert mock_objective.call_count == 3

    def test_multi_objective_optimization(self, temp_storage):
        """測試多目標優化（separation + stability）"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                optimizer = OptunaOptimizer(
                    study_name="multi_obj_test",
                    storage=temp_storage,
                    sampler_type="NSGA-II",
                    use_multi_objective=True,
                    n_trials=5
                )

                # 驗證多目標配置
                assert optimizer.use_multi_objective == True
                assert optimizer.sampler_type == "NSGA-II"

                # 創建Study
                study = optimizer.create_study()

                # 驗證Study是多目標
                assert len(study.directions) == 2
                assert study.directions[0] == optuna.study.StudyDirection.MAXIMIZE
                assert study.directions[1] == optuna.study.StudyDirection.MAXIMIZE


class TestParetoAnalyzer:
    """ParetoAnalyzer測試套件"""

    @pytest.fixture
    def temp_storage(self):
        """臨時SQLite數據庫"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        storage = f"sqlite:///{db_path}"
        yield storage
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_pareto_analysis_requires_multi_objective(self, temp_storage):
        """測試Pareto分析需要多目標優化"""
        with patch('momentum.Optimization.optuna_optimizer.SignalAnalysisService'):
            with patch('momentum.Optimization.optuna_optimizer.CaseStorage'):
                # 單目標優化器
                optimizer = OptunaOptimizer(
                    study_name="single_obj",
                    storage=temp_storage,
                    use_multi_objective=False
                )

                # 嘗試獲取Pareto分析應拋出錯誤
                with pytest.raises(ValueError, match="multi-objective"):
                    optimizer.get_pareto_analysis()


# ==================== pytest配置 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
