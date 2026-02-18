"""Phase 4.3 Execution Optimization routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.core.logging import get_logger
from api.models.optimization_models import (
    ExecutionOptimizationRequest,
    ExecutionOptimizationResponse,
    OptimizationResultResponse,
)
from api.services.optimization_task_service import optimization_task_service


router = APIRouter(prefix="/api/v1/optimization", tags=["Execution Optimization"])
logger = get_logger("api.routes.execution_optimization")


@router.post("/execution", response_model=ExecutionOptimizationResponse)
async def start_execution_optimization(
    request: ExecutionOptimizationRequest,
) -> ExecutionOptimizationResponse:
    """啟動策略執行優化任務。"""
    try:
        objective_config = {
            "model_predictions_path": request.model_predictions_path,
            "target_metric": request.target_metric,
            "constraints": request.constraints or {},
            "multi_objective": request.multi_objective,
            "search_space_override": request.search_space_override,
        }

        backtest_config = request.backtest_config or {}
        if "commission" in backtest_config:
            objective_config["commission"] = backtest_config["commission"]
        if "slippage" in backtest_config:
            objective_config["slippage"] = backtest_config["slippage"]

        task_id = optimization_task_service.create_task(
            study_name="execution_optimization",
            positive_cases=[],
            negative_cases=[],
            training_window=None,
            task_type="strategy_backtest",
            objective_config=objective_config,
            n_trials=request.n_trials,
            timeout_seconds=request.timeout_seconds,
            use_multi_objective=request.multi_objective,
        )

        started = await optimization_task_service.start_task(task_id)
        if not started:
            raise HTTPException(status_code=500, detail=f"Failed to start task: {task_id}")

        task_info = optimization_task_service.get_task(task_id)
        return ExecutionOptimizationResponse(
            task_id=task_id,
            status=(task_info.status.value if task_info else "pending"),
            created_at=(task_info.created_at.isoformat() if task_info else ""),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to start execution optimization: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{task_id}/result", response_model=OptimizationResultResponse)
async def get_optimization_result(task_id: str) -> OptimizationResultResponse:
    """取得優化任務結果。"""
    task_info = optimization_task_service.get_task(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    task_type = str(task_info.config.get("task_type", "unknown"))
    best_trial = None
    performance_metrics = None
    parameter_importance = None

    if task_info.result is not None:
        best_trial = {
            "trial_number": getattr(task_info.result, "best_trial_number", None),
            "value": getattr(task_info.result, "best_value", None),
            "params": getattr(task_info.result, "best_params", None),
        }
        performance_metrics = getattr(task_info.result, "metrics", None)
        parameter_importance = getattr(task_info.result, "parameter_importance", None)

    return OptimizationResultResponse(
        task_id=task_id,
        task_type=task_type,
        status=task_info.status.value,
        best_trial=best_trial,
        performance_metrics=performance_metrics,
        parameter_importance=parameter_importance,
    )
