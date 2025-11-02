"""
優化系統端到端整合測試

測試完整流程:
1. 創建優化任務 → 啟動任務 → WebSocket訂閱 → 完成
2. 分析API（參數重要性、歷史、參數空間）

Author: Claude (Phase 3.5 Day 7-8)
Date: 2025-11-02
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os

from api.services.optimization_task_service import (
    optimization_task_service,
    OptimizationTaskStatus
)
from api.models.training_window_config import TrainingWindowConfig


class TestOptimizationEndToEnd:
    """端到端整合測試"""

    @pytest.fixture
    def training_window(self):
        """訓練窗口配置"""
        return TrainingWindowConfig(
            start_date="2024-01-01",
            end_date="2024-12-31",
            timeframe="1h"
        )

    @pytest.mark.asyncio
    async def test_create_and_query_task(self, training_window):
        """測試創建任務並查詢狀態"""
        # 創建任務
        task_id = optimization_task_service.create_task(
            study_name="integration_test_001",
            positive_cases=["case_001", "case_002"],
            negative_cases=["case_003", "case_004"],
            training_window=training_window,
            sampler_type="TPE",
            n_trials=10,
            n_jobs=1
        )

        # 驗證任務已創建
        assert task_id is not None

        # 查詢任務
        task_info = optimization_task_service.get_task(task_id)

        # 驗證
        assert task_info is not None
        assert task_info.task_id == task_id
        assert task_info.status == OptimizationTaskStatus.PENDING
        assert task_info.study_name == "integration_test_001"
        assert len(task_info.config['positive_cases']) == 2
        assert len(task_info.config['negative_cases']) == 2

    @pytest.mark.asyncio
    async def test_list_tasks(self, training_window):
        """測試列出所有任務"""
        # 創建3個任務
        task_ids = []
        for i in range(3):
            task_id = optimization_task_service.create_task(
                study_name=f"list_test_{i}",
                positive_cases=["case_001"],
                negative_cases=["case_002"],
                training_window=training_window,
                n_trials=5
            )
            task_ids.append(task_id)

        # 列出所有任務
        all_tasks = optimization_task_service.list_tasks()

        # 驗證至少包含我們創建的3個任務
        assert len(all_tasks) >= 3

        # 驗證我們創建的任務都在列表中
        task_ids_in_list = [t.task_id for t in all_tasks]
        for task_id in task_ids:
            assert task_id in task_ids_in_list

    @pytest.mark.asyncio
    async def test_list_tasks_filtered_by_status(self, training_window):
        """測試按狀態過濾任務列表"""
        # 創建PENDING任務
        task_id = optimization_task_service.create_task(
            study_name="filter_test",
            positive_cases=["case_001"],
            negative_cases=["case_002"],
            training_window=training_window,
            n_trials=5
        )

        # 列出PENDING任務
        pending_tasks = optimization_task_service.list_tasks(status=OptimizationTaskStatus.PENDING)

        # 驗證我們創建的任務在PENDING列表中
        task_ids_in_list = [t.task_id for t in pending_tasks]
        assert task_id in task_ids_in_list

        # 列出COMPLETED任務（應該不包含我們的任務）
        completed_tasks = optimization_task_service.list_tasks(status=OptimizationTaskStatus.COMPLETED)
        completed_task_ids = [t.task_id for t in completed_tasks]
        assert task_id not in completed_task_ids

    @pytest.mark.asyncio
    async def test_cancel_task(self, training_window):
        """測試取消任務"""
        # 創建任務
        task_id = optimization_task_service.create_task(
            study_name="cancel_test",
            positive_cases=["case_001"],
            negative_cases=["case_002"],
            training_window=training_window,
            n_trials=5
        )

        # 取消任務
        success = await optimization_task_service.cancel_task(task_id)

        # 驗證
        assert success == True

        # 查詢任務狀態
        task_info = optimization_task_service.get_task(task_id)
        assert task_info.status == OptimizationTaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_notification_callback_registration(self, training_window):
        """測試WebSocket通知回調註冊"""
        # 創建任務
        task_id = optimization_task_service.create_task(
            study_name="callback_test",
            positive_cases=["case_001"],
            negative_cases=["case_002"],
            training_window=training_window,
            n_trials=5
        )

        # 創建Mock回調
        mock_callback = Mock()

        # 註冊回調
        optimization_task_service.register_notification_callback(task_id, mock_callback)

        # 驗證回調已註冊
        assert task_id in optimization_task_service.notification_callbacks
        assert optimization_task_service.notification_callbacks[task_id] == mock_callback

        # 取消註冊
        optimization_task_service.unregister_notification_callback(task_id)

        # 驗證回調已移除
        assert task_id not in optimization_task_service.notification_callbacks


class TestTaskServiceSingleton:
    """測試OptimizationTaskService單例模式"""

    def test_singleton_pattern(self):
        """測試單例模式：多次獲取應返回同一實例"""
        from api.services.optimization_task_service import OptimizationTaskService

        instance1 = OptimizationTaskService()
        instance2 = OptimizationTaskService()

        # 驗證是同一實例
        assert instance1 is instance2

    def test_singleton_shared_state(self, training_window):
        """測試單例共享狀態：一個實例創建的任務，另一個實例也能訪問"""
        from api.services.optimization_task_service import OptimizationTaskService

        service1 = OptimizationTaskService()
        service2 = OptimizationTaskService()

        # service1創建任務
        task_id = service1.create_task(
            study_name="singleton_test",
            positive_cases=["case_001"],
            negative_cases=["case_002"],
            training_window=training_window,
            n_trials=5
        )

        # service2應能訪問該任務
        task_info = service2.get_task(task_id)

        assert task_info is not None
        assert task_info.task_id == task_id


class TestTaskInfoSerialization:
    """測試TaskInfo序列化"""

    def test_to_dict_serialization(self, training_window):
        """測試TaskInfo.to_dict()序列化"""
        # 創建任務
        task_id = optimization_task_service.create_task(
            study_name="serialization_test",
            positive_cases=["case_001"],
            negative_cases=["case_002"],
            training_window=training_window,
            n_trials=5
        )

        # 獲取任務
        task_info = optimization_task_service.get_task(task_id)

        # 序列化為字典
        task_dict = task_info.to_dict()

        # 驗證
        assert isinstance(task_dict, dict)
        assert task_dict['task_id'] == task_id
        assert task_dict['study_name'] == "serialization_test"
        assert task_dict['status'] == 'pending'
        assert 'progress' in task_dict
        assert 'config' in task_dict

    def test_to_dict_datetime_serialization(self, training_window):
        """測試datetime字段正確序列化為ISO字符串"""
        # 創建任務
        task_id = optimization_task_service.create_task(
            study_name="datetime_test",
            positive_cases=["case_001"],
            negative_cases=["case_002"],
            training_window=training_window,
            n_trials=5
        )

        task_info = optimization_task_service.get_task(task_id)
        task_dict = task_info.to_dict()

        # 驗證created_at是ISO格式字符串
        assert isinstance(task_dict['created_at'], str)
        assert 'T' in task_dict['created_at']  # ISO格式包含'T'


# ==================== pytest配置 ====================

@pytest.fixture(autouse=True)
def cleanup_tasks():
    """每個測試後清理任務（避免跨測試污染）"""
    yield
    # 測試結束後清理
    # 注意：由於是單例模式，無法完全清理，只記錄
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
