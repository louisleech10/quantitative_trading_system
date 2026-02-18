from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from api.services.optimization_task_service import (
    OptimizationTaskInfo,
    OptimizationTaskProgress,
    OptimizationTaskService,
    OptimizationTaskStatus,
)


def test_emit_backtest_progress_and_pareto_update():
    service = OptimizationTaskService()
    task_id = "phase43-strategy-task"
    received = []

    def _callback(event_type, data):
        received.append((event_type, data))

    with service.tasks_lock:
        service.tasks[task_id] = OptimizationTaskInfo(
            task_id=task_id,
            study_name="phase43",
            status=OptimizationTaskStatus.RUNNING,
            created_at=datetime.now(),
            progress=OptimizationTaskProgress(total_trials=10),
            config={"task_type": "strategy_backtest", "use_multi_objective": True},
        )
        service.notification_callbacks[task_id] = _callback
        service.optimizers[task_id] = SimpleNamespace(
            study=SimpleNamespace(
                best_trials=[
                    SimpleNamespace(values=(1.2, 0.15)),
                    SimpleNamespace(values=(1.0, 0.10)),
                ]
            )
        )

    progress_callback = service._create_progress_callback(task_id)
    progress_callback("progress_update", {"completed_trials": 3, "completion_percentage": 30.0, "best_value": 1.2})

    event_types = [event for event, _ in received]
    assert "progress_update" in event_types
    assert "backtest_progress" in event_types
    assert "pareto_update" in event_types

    with service.tasks_lock:
        service.tasks.pop(task_id, None)
        service.notification_callbacks.pop(task_id, None)
        service.optimizers.pop(task_id, None)


def test_emit_overfitting_alert():
    service = OptimizationTaskService()
    task_id = "phase43-hyper-task"
    received = []

    def _callback(event_type, data):
        received.append((event_type, data))

    with service.tasks_lock:
        service.tasks[task_id] = OptimizationTaskInfo(
            task_id=task_id,
            study_name="phase43-hyper",
            status=OptimizationTaskStatus.RUNNING,
            created_at=datetime.now(),
            progress=OptimizationTaskProgress(total_trials=10),
            config={
                "task_type": "model_hyperparam",
                "objective_config": {"max_train_val_gap": 0.1},
            },
        )
        service.notification_callbacks[task_id] = _callback

    progress_callback = service._create_progress_callback(task_id)
    progress_callback("new_best_value", {"trial_number": 5, "train_val_gap": 0.25})

    event_types = [event for event, _ in received]
    assert "new_best_value" in event_types
    assert "overfitting_alert" in event_types

    with service.tasks_lock:
        service.tasks.pop(task_id, None)
        service.notification_callbacks.pop(task_id, None)
