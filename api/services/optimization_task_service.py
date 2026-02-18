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
import numpy as np
import pandas as pd

from api.core.config import settings
from api.core.logging import get_logger
from api.services.optimization_output_service import get_optimization_output_service
from momentum.factories import create_backtest_engine, create_model_trainer, create_optuna_optimizer
from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective
from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective
from api.models.training_window_config import TrainingWindowConfig
from api.utils.case_storage import get_case_storage_manager


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
    result: Optional[Any] = None
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

        # OptunaOptimizer實例（task_id -> optimizer）
        self.optimizers: Dict[str, Any] = {}

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
        training_window: Optional[TrainingWindowConfig],
        task_type: str = "signal_density",
        objective_config: Optional[Dict[str, Any]] = None,
        sampler_type: str = "TPE",
        n_trials: int = 100,
        timeout_seconds: Optional[int] = None,
        n_startup_trials: Optional[int] = None,
        n_jobs: int = 1,
        parameter_ranges: Optional[Any] = None,
        use_multi_objective: bool = False,
        enable_pruning: bool = True,
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
            n_startup_trials: TPE 初始隨機試驗數（None 則自動計算）
            n_jobs: 並行核心數
            parameter_ranges: 參數搜索範圍
            use_multi_objective: 是否使用多目標優化
            enable_pruning: 是否啟用 Pruner（MedianPruner）
            notification_callback: WebSocket通知回調函數

        Returns:
            task_id: 任務ID
        """
        task_id = str(uuid.uuid4())

        if task_type == "signal_density" and training_window is None:
            raise ValueError("signal_density 任務必須提供 training_window")

        # 決定 pruner 類型
        pruner_type = "Median" if enable_pruning else None

        # 創建任務信息
        task_info = OptimizationTaskInfo(
            task_id=task_id,
            study_name=study_name,
            status=OptimizationTaskStatus.PENDING,
            created_at=datetime.now(),
            config={
                'task_type': task_type,
                'objective_config': objective_config or {},
                'positive_cases': positive_cases,
                'negative_cases': negative_cases,
                'training_window': (
                    training_window.__dict__ if training_window is not None and hasattr(training_window, '__dict__') else training_window
                ),
                'sampler_type': sampler_type,
                'n_trials': n_trials,
                'timeout_seconds': timeout_seconds,
                'n_startup_trials': n_startup_trials,
                'n_jobs': n_jobs,
                'use_multi_objective': use_multi_objective,
                'enable_pruning': enable_pruning
            }
        )
        task_info.progress.total_trials = n_trials

        # 創建OptunaOptimizer實例（with ProgressMonitor callback）
        optimizer_kwargs = dict(
            study_name=study_name,
            storage=f"sqlite:///data/optuna_{study_name}.db",
            sampler_type=sampler_type,
            pruner_type=pruner_type,
            n_trials=n_trials,
            timeout=timeout_seconds,
            n_startup_trials=n_startup_trials,
            n_jobs=n_jobs,
            parameter_ranges=parameter_ranges,
            use_multi_objective=use_multi_objective,
            enable_progress_monitor=True,
            progress_notification_callback=self._create_progress_callback(task_id),
        )

        if task_type == "signal_density":
            optimizer_kwargs["case_storage_factory"] = get_case_storage_manager
            optimizer = create_optuna_optimizer(**optimizer_kwargs)
        elif task_type == "model_hyperparam":
            objective = self._build_model_hyperparam_objective(objective_config or {})
            optimizer = create_optuna_optimizer(objective=objective, **optimizer_kwargs)
        elif task_type == "strategy_backtest":
            objective = self._build_strategy_backtest_objective(objective_config or {}, use_multi_objective)
            optimizer = create_optuna_optimizer(objective=objective, **optimizer_kwargs)
        else:
            raise ValueError(f"不支援的 task_type: {task_type}")

        # 保存任務
        with self.tasks_lock:
            self.tasks[task_id] = task_info
            self.optimizers[task_id] = optimizer
            if notification_callback:
                self.notification_callbacks[task_id] = notification_callback

        self.logger.info(
            f"Task created: {task_id}, study={study_name}, "
            f"task_type={task_type}, sampler={sampler_type}, n_trials={n_trials}"
        )

        return task_id

    def _build_model_hyperparam_objective(self, objective_config: Dict[str, Any]) -> ModelHyperparamObjective:
        engine = str(objective_config.get("engine", "lightgbm"))
        features = objective_config.get("features")
        labels = objective_config.get("labels")
        feature_names = objective_config.get("feature_names")

        if features is None or labels is None:
            raise ValueError("model_hyperparam task_type 需要 objective_config.features 與 objective_config.labels")

        if isinstance(features, pd.DataFrame):
            X = features
            resolved_feature_names = feature_names or X.columns.tolist()
        elif isinstance(features, list) and len(features) > 0 and isinstance(features[0], dict):
            X = pd.DataFrame(features)
            resolved_feature_names = feature_names or X.columns.tolist()
        else:
            X = np.asarray(features)
            if X.ndim != 2:
                raise ValueError("features 必須是二維資料")
            if feature_names is None:
                resolved_feature_names = [f"feature_{idx}" for idx in range(X.shape[1])]
            else:
                resolved_feature_names = list(feature_names)
            X = pd.DataFrame(X, columns=resolved_feature_names)

        y = np.asarray(labels)
        if len(X) != len(y):
            raise ValueError("features 與 labels 長度不一致")

        trainer = create_model_trainer(engine, config=objective_config.get("base_model_params"))
        return ModelHyperparamObjective(
            trainer=trainer,
            features=X,
            labels=y,
            feature_names=resolved_feature_names,
            engine=engine,
            cv_folds=int(objective_config.get("cv_folds", 5)),
            max_train_val_gap=float(objective_config.get("max_train_val_gap", 0.1)),
            search_space_override=objective_config.get("search_space_override"),
            train_kwargs=objective_config.get("train_kwargs", {}),
        )

    def _build_strategy_backtest_objective(
        self,
        objective_config: Dict[str, Any],
        use_multi_objective: bool,
    ) -> StrategyBacktestObjective:
        csv_path = objective_config.get("model_predictions_path")
        prices = objective_config.get("prices")
        predicted_proba = objective_config.get("predicted_proba")
        atr_values = objective_config.get("atr_values")

        # Breaking Change migration compatibility:
        # legacy fields from pre-Phase 4.2 constructor
        legacy_predictions = objective_config.get("model_predictions")
        legacy_price_data = objective_config.get("price_data")

        if predicted_proba is None and legacy_predictions is not None:
            predicted_proba = legacy_predictions
        if prices is None and legacy_price_data is not None:
            legacy_close = pd.Series(legacy_price_data).astype(float)
            prices = pd.DataFrame(
                {
                    "open": legacy_close,
                    "high": legacy_close,
                    "low": legacy_close,
                    "close": legacy_close,
                }
            )
        if atr_values is None and prices is not None:
            close_series = pd.Series(prices["close"]).astype(float)
            atr_values = close_series.diff().abs().fillna(0.0)

        if csv_path:
            csv_file = Path(csv_path)
            if not csv_file.exists():
                raise ValueError(f"model_predictions_path not found: {csv_file}")

            data = pd.read_csv(csv_file)
            required_columns = {"open", "high", "low", "close", "atr"}
            if not required_columns.issubset(set(data.columns)):
                raise ValueError(
                    f"CSV missing required columns: {sorted(required_columns - set(data.columns))}"
                )

            proba_column = objective_config.get("predicted_proba_column", "predicted_proba_lgb")
            if proba_column not in data.columns:
                raise ValueError(f"CSV missing predicted proba column: {proba_column}")

            prices = data[["open", "high", "low", "close"]].copy()
            if "timestamp" in data.columns:
                prices["timestamp"] = data["timestamp"]

            predicted_proba = data[proba_column]
            atr_values = data["atr"]

        if prices is None or predicted_proba is None or atr_values is None:
            raise ValueError(
                "strategy_backtest task_type 需要 objective_config.model_predictions_path，"
                "或同時提供 prices/predicted_proba/atr_values"
            )

        if not isinstance(prices, pd.DataFrame):
            prices = pd.DataFrame(prices)

        backtest_engine = create_backtest_engine(
            commission=float(objective_config.get("commission", 0.001)),
            slippage=float(objective_config.get("slippage", 0.0005)),
        )

        return StrategyBacktestObjective(
            backtest_engine=backtest_engine,
            prices=prices,
            predicted_proba=pd.Series(predicted_proba),
            atr_values=pd.Series(atr_values),
            target_metric=str(objective_config.get("target_metric", "expectancy")),
            constraints=objective_config.get("constraints") or {},
            multi_objective=bool(objective_config.get("multi_objective", use_multi_objective)),
        )

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
                    task_type = str(task_info.config.get("task_type", ""))

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

                    # Phase 4.3 新事件: backtest_progress
                    if task_type == "strategy_backtest" and event_type in {"progress_update", "new_best_value"}:
                        callback("backtest_progress", {
                            "task_id": task_id,
                            "trial_number": data.get("completed_trials"),
                            "best_value": data.get("best_value"),
                            "completion_percentage": data.get("completion_percentage"),
                            "sharpe": data.get("sharpe_ratio"),
                            "max_dd": data.get("max_drawdown"),
                            "win_rate": data.get("win_rate"),
                            "expectancy": data.get("expectancy"),
                        })

                    # Phase 4.3 新事件: pareto_update（多目標）
                    use_multi_objective = bool(task_info.config.get("use_multi_objective", False))
                    if task_type == "strategy_backtest" and use_multi_objective and event_type in {"progress_update", "new_best_value", "optimization_finished"}:
                        callback("pareto_update", {
                            "task_id": task_id,
                            "pareto_front": self._get_pareto_front(task_id),
                        })

                    # Phase 4.3 新事件: overfitting_alert
                    if task_type == "model_hyperparam":
                        train_val_gap = data.get("train_val_gap")
                        threshold = float(task_info.config.get("objective_config", {}).get("max_train_val_gap", 0.1))
                        if isinstance(train_val_gap, (float, int)) and float(train_val_gap) > threshold:
                            callback("overfitting_alert", {
                                "task_id": task_id,
                                "trial_number": data.get("trial_number") or data.get("completed_trials"),
                                "train_val_gap": float(train_val_gap),
                                "threshold": threshold,
                            })

            except Exception as e:
                self.logger.error(f"Progress callback error for task {task_id}: {e}", exc_info=True)

        return progress_callback

    def _get_pareto_front(self, task_id: str) -> List[Dict[str, float]]:
        """取得多目標優化 Pareto front（若不可用則回傳空列表）。"""
        optimizer = self.optimizers.get(task_id)
        if optimizer is None:
            return []

        study = getattr(optimizer, "study", None)
        if study is None:
            return []

        best_trials = getattr(study, "best_trials", None)
        if not best_trials:
            return []

        pareto_front: List[Dict[str, float]] = []
        for trial in best_trials:
            values = getattr(trial, "values", None)
            if not values or len(values) < 2:
                continue
            pareto_front.append(
                {
                    "sharpe": float(values[0]),
                    "max_dd": float(values[1]),
                }
            )

        return pareto_front

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

                training_window_cfg = config.get('training_window')
                parsed_training_window = None
                if training_window_cfg is not None:
                    parsed_training_window = TrainingWindowConfig(**training_window_cfg)

            # 執行優化
            self.logger.info(f"Starting optimization for task: {task_id}")

            result = await optimizer.optimize(
                positive_cases=config['positive_cases'],
                negative_cases=config['negative_cases'],
                    training_window=parsed_training_window,
            )

            # 更新任務狀態
            with self.tasks_lock:
                task_info.status = OptimizationTaskStatus.COMPLETED
                task_info.completed_at = datetime.now()
                task_info.result = result

            # 保存結果到文件
            self._save_result(task_id, result)

            # Phase 4.5: 任務完成後自動生成輸出檔案
            try:
                output_service = get_optimization_output_service()
                output_service.generate_outputs(
                    task_type=str(config.get("task_type", "unknown")),
                    task_id=task_id,
                    task_info=task_info,
                    optimizer=optimizer,
                )
            except Exception as output_error:
                self.logger.error(
                    f"Failed to generate optimization outputs for task {task_id}: {output_error}",
                    exc_info=True,
                )

            # Ultra Think Step 3 優化: 任務完成後清理舊任務
            self._cleanup_old_tasks(keep_latest=100)

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

    def _save_result(self, task_id: str, result: Any):
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
                'n_trials': result.total_trials if hasattr(result, 'total_trials') else (result.n_trials if hasattr(result, 'n_trials') else None),
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

    def _get_storage_for_study(self, study_name: str) -> str:
        """
        獲取指定study的storage路徑

        Args:
            study_name: Study名稱

        Returns:
            SQLite storage路徑
        """
        # 查找對應的task_id
        with self.tasks_lock:
            for task_id, task_info in self.tasks.items():
                if task_info.study_name == study_name:
                    # 從optimizer獲取storage
                    if task_id in self.optimizers:
                        return self.optimizers[task_id].storage

        # 如果沒找到，使用預設storage路徑
        return "sqlite:///data/optuna_study.db"

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

    def _cleanup_old_tasks(self, keep_latest: int = 100):
        """
        Ultra Think Step 3 優化: 清理舊的已完成任務，防止內存洩漏

        保留最近 N 個已完成任務，刪除更舊的任務。
        注意: 只清理 COMPLETED 狀態的任務，FAILED/CANCELLED 任務會保留用於調試。

        Args:
            keep_latest: 保留最近N個已完成任務（默認100個）
        """
        with self.tasks_lock:
            # 收集所有已完成的任務（按完成時間排序）
            completed_tasks = [
                (task_id, task_info)
                for task_id, task_info in self.tasks.items()
                if task_info.status == OptimizationTaskStatus.COMPLETED
                and task_info.completed_at is not None
            ]

            # 如果已完成任務數量超過限制，清理最舊的
            if len(completed_tasks) > keep_latest:
                # 按完成時間排序（最舊的在前）
                sorted_tasks = sorted(completed_tasks, key=lambda x: x[1].completed_at)

                # 刪除最舊的任務（保留最新的 keep_latest 個）
                tasks_to_delete = sorted_tasks[:-keep_latest]

                for task_id, task_info in tasks_to_delete:
                    # 刪除任務信息
                    del self.tasks[task_id]

                    # 刪除 optimizer 實例（如果存在）
                    if task_id in self.optimizers:
                        del self.optimizers[task_id]

                    # 刪除通知回調（如果存在）
                    if task_id in self.notification_callbacks:
                        del self.notification_callbacks[task_id]

                    self.logger.info(
                        f"Cleaned up old completed task: {task_id} "
                        f"(completed at {task_info.completed_at})"
                    )

                self.logger.info(
                    f"Task cleanup completed: removed {len(tasks_to_delete)} old tasks, "
                    f"kept {keep_latest} recent tasks"
                )


# 全局單例
optimization_task_service = OptimizationTaskService()
