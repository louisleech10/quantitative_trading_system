"""
優化任務服務 - Optuna參數優化任務管理

功能:
1. 任務創建與管理（start/stop/cancel）
2. 進度追蹤與WebSocket通知
3. 結果持久化與查詢
4. 並發任務控制

Author: Claude (Phase 3.5 Day 5-6)
Date: 2025-11-02
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading
import json
from pathlib import Path

from api.core.config import settings
from api.core.logging import get_logger
from momentum.Optimization.optuna_optimizer import OptunaOptimizer, OptimizationResult, ParameterRanges
from api.models.training_window_config import TrainingWindowConfig


class OptimizationTaskStatus(str, Enum):
    """優化任務狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OptimizationTaskProgress:
    """優化任務進度"""
    completed_trials: int = 0
    total_trials: int = 100
    completion_percentage: float = 0.0
    best_value: Optional[float] = None
    best_params: Optional[Dict[str, Any]] = None
    elapsed_time: float = 0.0
    estimated_remaining_time: Optional[float] = None
    trials_per_hour: float = 0.0
    current_milestone: Optional[int] = None  # 當前達成的里程碑 (25/50/75)
    error_count: int = 0


@dataclass
class OptimizationTaskInfo:
    """優化任務完整信息"""
    task_id: str
    study_name: str
    status: OptimizationTaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: OptimizationTaskProgress = field(default_factory=OptimizationTaskProgress)
    result: Optional[OptimizationResult] = None
    error_message: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)  # 優化配置（sampler_type, n_trials等）

    @property
    def duration_seconds(self) -> Optional[float]:
        """計算任務執行時間"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    @property
    def is_active(self) -> bool:
        """檢查任務是否正在執行"""
        return self.status in [OptimizationTaskStatus.PENDING, OptimizationTaskStatus.RUNNING]

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於JSON序列化）"""
        return {
            'task_id': self.task_id,
            'study_name': self.study_name,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': {
                'completed_trials': self.progress.completed_trials,
                'total_trials': self.progress.total_trials,
                'completion_percentage': self.progress.completion_percentage,
                'best_value': self.progress.best_value,
                'best_params': self.progress.best_params,
                'elapsed_time': self.progress.elapsed_time,
                'estimated_remaining_time': self.progress.estimated_remaining_time,
                'trials_per_hour': self.progress.trials_per_hour,
                'current_milestone': self.progress.current_milestone,
                'error_count': self.progress.error_count
            },
            'result': self.result.__dict__ if self.result else None,
            'error_message': self.error_message,
            'config': self.config,
            'duration_seconds': self.duration_seconds
        }


class OptimizationTaskService:
    """
    優化任務服務

    負責管理Optuna優化任務的生命週期，包括任務創建、執行、進度追蹤和WebSocket通知。

    核心功能:
    1. 任務創建: 創建並初始化優化任務
    2. 任務執行: 在後台線程中運行OptunaOptimizer
    3. 進度追蹤: 通過ProgressMonitor callback接收進度更新
    4. WebSocket通知: 實時推送進度給前端（通過notification_callback）
    5. 結果持久化: 保存優化結果到文件

    設計理念:
    - 單例模式: 全局唯一任務管理器
    - 線程安全: 使用threading.Lock保護共享狀態
    - 回調解耦: 通過notification_callback與WebSocket層解耦
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """單例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化優化任務服務"""
        if hasattr(self, '_initialized'):
            return

        self.logger = get_logger("api.optimization_task_service")

        # 任務存儲（task_id -> TaskInfo）
        self.tasks: Dict[str, OptimizationTaskInfo] = {}

        # 運行中的任務（task_id -> asyncio.Task）
        self.running_tasks: Dict[str, asyncio.Task] = {}

        # OptunaOptimizer實例（task_id -> OptunaOptimizer）
        self.optimizers: Dict[str, OptunaOptimizer] = {}

        # WebSocket通知回調（task_id -> callback）
        self.notification_callbacks: Dict[str, Callable[[str, Dict[str, Any]], None]] = {}

        # 線程鎖（保護共享狀態）
        self.tasks_lock = threading.Lock()

        # 結果保存目錄
        self.results_dir = Path(settings.results_output_path) / "optimization_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = True
        self.logger.info("OptimizationTaskService initialized")

    def create_task(
        self,
        study_name: str,
        positive_cases: List[str],
        negative_cases: List[str],
        training_window: TrainingWindowConfig,
        sampler_type: str = "TPE",
        n_trials: int = 100,
        n_jobs: int = 1,
        parameter_ranges: Optional[ParameterRanges] = None,
        use_multi_objective: bool = False,
        notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> str:
        """
        創建優化任務

        Args:
            study_name: Optuna Study名稱
            positive_cases: 正例案例ID列表
            negative_cases: 反例案例ID列表
            training_window: 訓練窗口配置
            sampler_type: 優化器類型（TPE/CmaEs/Random/GP/NSGA-II）
            n_trials: 試驗次數
            n_jobs: 並行核心數
            parameter_ranges: 參數搜索範圍
            use_multi_objective: 是否使用多目標優化
            notification_callback: WebSocket通知回調函數

        Returns:
            task_id: 任務ID
        """
        task_id = str(uuid.uuid4())

        # 創建任務信息
        task_info = OptimizationTaskInfo(
            task_id=task_id,
            study_name=study_name,
            status=OptimizationTaskStatus.PENDING,
            created_at=datetime.now(),
            config={
                'positive_cases': positive_cases,
                'negative_cases': negative_cases,
                'training_window': training_window.__dict__ if hasattr(training_window, '__dict__') else training_window,
                'sampler_type': sampler_type,
                'n_trials': n_trials,
                'n_jobs': n_jobs,
                'use_multi_objective': use_multi_objective
            }
        )
        task_info.progress.total_trials = n_trials

        # 創建OptunaOptimizer實例（with ProgressMonitor callback）
        optimizer = OptunaOptimizer(
            study_name=study_name,
            storage=f"sqlite:///data/optuna_{study_name}.db",
            sampler_type=sampler_type,
            n_trials=n_trials,
            n_jobs=n_jobs,
            parameter_ranges=parameter_ranges,
            use_multi_objective=use_multi_objective,
            enable_progress_monitor=True,
            progress_notification_callback=self._create_progress_callback(task_id)
        )

        # 保存任務
        with self.tasks_lock:
            self.tasks[task_id] = task_info
            self.optimizers[task_id] = optimizer
            if notification_callback:
                self.notification_callbacks[task_id] = notification_callback

        self.logger.info(
            f"Task created: {task_id}, study={study_name}, "
            f"sampler={sampler_type}, n_trials={n_trials}"
        )

        return task_id

    def _create_progress_callback(self, task_id: str) -> Callable[[str, Dict[str, Any]], None]:
        """
        創建進度回調函數（ProgressMonitor會調用此函數）

        Args:
            task_id: 任務ID

        Returns:
            callback函數，接收(event_type, data)
        """
        def progress_callback(event_type: str, data: Dict[str, Any]):
            """
            ProgressMonitor進度回調

            事件類型:
            - optimization_started: 優化開始
            - new_best_value: 發現新最佳值
            - milestone_reached: 里程碑達成（25%/50%/75%）
            - progress_update: 實時進度更新
            - optimization_finished: 優化完成
            """
            try:
                # 更新任務進度
                with self.tasks_lock:
                    if task_id not in self.tasks:
                        return

                    task_info = self.tasks[task_id]

                    # 根據事件類型更新進度
                    if event_type == "optimization_started":
                        task_info.status = OptimizationTaskStatus.RUNNING
                        task_info.started_at = datetime.now()

                    elif event_type == "progress_update":
                        task_info.progress.completed_trials = data.get('completed_trials', 0)
                        task_info.progress.completion_percentage = data.get('completion_percentage', 0.0)
                        task_info.progress.best_value = data.get('best_value')
                        task_info.progress.elapsed_time = data.get('elapsed_time', 0.0)
                        task_info.progress.estimated_remaining_time = data.get('estimated_remaining_time')
                        task_info.progress.trials_per_hour = data.get('trials_per_hour', 0.0)

                    elif event_type == "new_best_value":
                        task_info.progress.best_value = data.get('best_value')
                        task_info.progress.best_params = data.get('best_params')

                    elif event_type == "milestone_reached":
                        task_info.progress.current_milestone = data.get('milestone_percentage')

                    elif event_type == "optimization_finished":
                        task_info.progress.completed_trials = data.get('completed_trials', 0)
                        task_info.progress.completion_percentage = 100.0

                # 轉發到WebSocket（如果有註冊callback）
                if task_id in self.notification_callbacks:
                    callback = self.notification_callbacks[task_id]
                    callback(event_type, {
                        'task_id': task_id,
                        **data
                    })

            except Exception as e:
                self.logger.error(f"Progress callback error for task {task_id}: {e}", exc_info=True)

        return progress_callback

    async def start_task(self, task_id: str) -> bool:
        """
        啟動優化任務（在後台運行）

        Args:
            task_id: 任務ID

        Returns:
            True if成功啟動，False otherwise
        """
        with self.tasks_lock:
            if task_id not in self.tasks:
                self.logger.error(f"Task not found: {task_id}")
                return False

            task_info = self.tasks[task_id]
            if task_info.status != OptimizationTaskStatus.PENDING:
                self.logger.warning(f"Task {task_id} is not in PENDING state: {task_info.status}")
                return False

            optimizer = self.optimizers.get(task_id)
            if not optimizer:
                self.logger.error(f"Optimizer not found for task: {task_id}")
                return False

        # 創建後台任務
        asyncio_task = asyncio.create_task(self._run_optimization(task_id))

        with self.tasks_lock:
            self.running_tasks[task_id] = asyncio_task

        self.logger.info(f"Task started: {task_id}")
        return True

    async def _run_optimization(self, task_id: str):
        """
        運行優化任務（後台協程）

        Args:
            task_id: 任務ID
        """
        try:
            with self.tasks_lock:
                task_info = self.tasks[task_id]
                optimizer = self.optimizers[task_id]
                config = task_info.config

            # 執行優化
            self.logger.info(f"Starting optimization for task: {task_id}")

            result = await optimizer.optimize(
                positive_cases=config['positive_cases'],
                negative_cases=config['negative_cases'],
                training_window=TrainingWindowConfig(**config['training_window'])
            )

            # 更新任務狀態
            with self.tasks_lock:
                task_info.status = OptimizationTaskStatus.COMPLETED
                task_info.completed_at = datetime.now()
                task_info.result = result

            # 保存結果到文件
            self._save_result(task_id, result)

            self.logger.info(f"Task completed: {task_id}, best_value={result.best_value}")

        except Exception as e:
            self.logger.error(f"Task failed: {task_id}, error={e}", exc_info=True)

            with self.tasks_lock:
                task_info = self.tasks[task_id]
                task_info.status = OptimizationTaskStatus.FAILED
                task_info.completed_at = datetime.now()
                task_info.error_message = str(e)

        finally:
            # 清理運行中的任務
            with self.tasks_lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

    def _save_result(self, task_id: str, result: OptimizationResult):
        """
        保存優化結果到文件

        Args:
            task_id: 任務ID
            result: 優化結果
        """
        try:
            result_file = self.results_dir / f"{task_id}_result.json"

            result_data = {
                'task_id': task_id,
                'best_value': result.best_value,
                'best_params': result.best_params,
                'best_trial_number': result.best_trial_number,
                'n_trials': result.n_trials,
                'optimization_time': result.optimization_time,
                'timestamp': datetime.now().isoformat()
            }

            with open(result_file, 'w') as f:
                json.dump(result_data, f, indent=2)

            self.logger.info(f"Result saved: {result_file}")

        except Exception as e:
            self.logger.error(f"Failed to save result for task {task_id}: {e}")

    def get_task(self, task_id: str) -> Optional[OptimizationTaskInfo]:
        """
        獲取任務信息

        Args:
            task_id: 任務ID

        Returns:
            TaskInfo或None
        """
        with self.tasks_lock:
            return self.tasks.get(task_id)

    def list_tasks(self, status: Optional[OptimizationTaskStatus] = None) -> List[OptimizationTaskInfo]:
        """
        列出所有任務

        Args:
            status: 過濾狀態（None=全部）

        Returns:
            任務列表
        """
        with self.tasks_lock:
            tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        # 按創建時間降序排序
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任務

        Args:
            task_id: 任務ID

        Returns:
            True if成功取消，False otherwise
        """
        with self.tasks_lock:
            if task_id not in self.tasks:
                return False

            task_info = self.tasks[task_id]

            if not task_info.is_active:
                self.logger.warning(f"Task {task_id} is not active: {task_info.status}")
                return False

            # 取消asyncio任務
            if task_id in self.running_tasks:
                asyncio_task = self.running_tasks[task_id]
                asyncio_task.cancel()

            # 更新狀態
            task_info.status = OptimizationTaskStatus.CANCELLED
            task_info.completed_at = datetime.now()

        self.logger.info(f"Task cancelled: {task_id}")
        return True

    def register_notification_callback(
        self,
        task_id: str,
        callback: Callable[[str, Dict[str, Any]], None]
    ):
        """
        註冊WebSocket通知回調

        Args:
            task_id: 任務ID
            callback: 回調函數，接收(event_type, data)
        """
        with self.tasks_lock:
            self.notification_callbacks[task_id] = callback

        self.logger.debug(f"Notification callback registered for task: {task_id}")

    def unregister_notification_callback(self, task_id: str):
        """
        取消註冊WebSocket通知回調

        Args:
            task_id: 任務ID
        """
        with self.tasks_lock:
            if task_id in self.notification_callbacks:
                del self.notification_callbacks[task_id]

        self.logger.debug(f"Notification callback unregistered for task: {task_id}")


# 全局單例
optimization_task_service = OptimizationTaskService()
