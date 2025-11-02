"""
優化任務 REST API - Optuna參數優化任務管理

功能:
1. 創建優化任務（POST /optimization/tasks）
2. 啟動任務（POST /optimization/tasks/{task_id}/start）
3. 查詢任務狀態（GET /optimization/tasks/{task_id}）
4. 列出所有任務（GET /optimization/tasks）
5. 取消任務（POST /optimization/tasks/{task_id}/cancel）

Author: Claude (Phase 3.5 Day 5-6)
Date: 2025-11-02
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.core.logging import get_logger
from api.services.optimization_task_service import (
    optimization_task_service,
    OptimizationTaskStatus
)
from api.models.training_window_config import TrainingWindowConfig
from momentum.Optimization.optuna_optimizer import ParameterRanges


router = APIRouter(prefix="/api/v1/optimization")
logger = get_logger("api.routes.optimization")


# ==================== Request Models ====================

class CreateOptimizationTaskRequest(BaseModel):
    """創建優化任務請求"""
    study_name: str = Field(..., description="Optuna Study名稱")
    positive_cases: List[str] = Field(..., description="正例案例ID列表", min_items=1)
    negative_cases: List[str] = Field(..., description="反例案例ID列表", min_items=1)
    training_window: TrainingWindowConfig = Field(..., description="訓練窗口配置")
    sampler_type: str = Field("TPE", description="優化器類型（TPE/CmaEs/Random/GP/NSGA-II）")
    n_trials: int = Field(100, description="試驗次數", ge=1, le=10000)
    n_jobs: int = Field(1, description="並行核心數", ge=1, le=16)
    use_multi_objective: bool = Field(False, description="是否使用多目標優化（separation + stability）")
    parameter_ranges: Optional[ParameterRanges] = Field(None, description="參數搜索範圍（None使用預設）")

    class Config:
        schema_extra = {
            "example": {
                "study_name": "momentum_optimization_001",
                "positive_cases": ["case_001", "case_002"],
                "negative_cases": ["case_003", "case_004"],
                "training_window": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "timeframe": "1h"
                },
                "sampler_type": "TPE",
                "n_trials": 100,
                "n_jobs": 6,
                "use_multi_objective": False
            }
        }


class CreateOptimizationTaskResponse(BaseModel):
    """創建優化任務響應"""
    success: bool
    task_id: str
    message: str


class TaskStatusResponse(BaseModel):
    """任務狀態響應"""
    success: bool
    data: dict


class TaskListResponse(BaseModel):
    """任務列表響應"""
    success: bool
    data: List[dict]
    total: int


# ==================== API Endpoints ====================

@router.post("/tasks", response_model=CreateOptimizationTaskResponse)
async def create_optimization_task(request: CreateOptimizationTaskRequest):
    """
    創建優化任務

    創建一個Optuna參數優化任務，但不立即啟動。
    任務創建後處於PENDING狀態，需要調用/start端點才會開始執行。

    Returns:
        task_id: 任務ID，用於後續查詢和控制
    """
    try:
        # 創建任務
        task_id = optimization_task_service.create_task(
            study_name=request.study_name,
            positive_cases=request.positive_cases,
            negative_cases=request.negative_cases,
            training_window=request.training_window,
            sampler_type=request.sampler_type,
            n_trials=request.n_trials,
            n_jobs=request.n_jobs,
            parameter_ranges=request.parameter_ranges,
            use_multi_objective=request.use_multi_objective
        )

        logger.info(f"Optimization task created: {task_id}")

        return CreateOptimizationTaskResponse(
            success=True,
            task_id=task_id,
            message=f"Optimization task created successfully. Use /tasks/{task_id}/start to begin."
        )

    except Exception as e:
        logger.error(f"Failed to create optimization task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/start")
async def start_optimization_task(task_id: str):
    """
    啟動優化任務

    啟動已創建的優化任務，任務將在後台執行。
    可以通過WebSocket訂閱實時進度，或通過GET /tasks/{task_id}查詢狀態。

    Args:
        task_id: 任務ID

    Returns:
        成功消息
    """
    try:
        success = await optimization_task_service.start_task(task_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to start task. Task may not exist or not in PENDING state.")

        logger.info(f"Optimization task started: {task_id}")

        return {
            "success": True,
            "message": f"Optimization task {task_id} started successfully. Connect to ws://localhost:8000/ws/optimization/{task_id} for real-time updates."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start optimization task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_optimization_task(task_id: str):
    """
    獲取任務狀態

    查詢優化任務的詳細狀態，包括進度、最佳參數、錯誤信息等。

    Args:
        task_id: 任務ID

    Returns:
        任務詳細信息
    """
    try:
        task_info = optimization_task_service.get_task(task_id)

        if not task_info:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return TaskStatusResponse(
            success=True,
            data=task_info.to_dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=TaskListResponse)
async def list_optimization_tasks(
    status: Optional[OptimizationTaskStatus] = Query(None, description="過濾狀態（PENDING/RUNNING/COMPLETED/FAILED/CANCELLED）")
):
    """
    列出所有優化任務

    獲取所有優化任務列表，支援按狀態過濾。
    任務按創建時間降序排序。

    Args:
        status: 過濾狀態（可選）

    Returns:
        任務列表
    """
    try:
        tasks = optimization_task_service.list_tasks(status=status)

        return TaskListResponse(
            success=True,
            data=[task.to_dict() for task in tasks],
            total=len(tasks)
        )

    except Exception as e:
        logger.error(f"Failed to list optimization tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/cancel")
async def cancel_optimization_task(task_id: str):
    """
    取消任務

    取消正在運行或待執行的優化任務。
    已完成的任務無法取消。

    Args:
        task_id: 任務ID

    Returns:
        成功消息
    """
    try:
        success = await optimization_task_service.cancel_task(task_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel task. Task may not exist or not in active state.")

        logger.info(f"Optimization task cancelled: {task_id}")

        return {
            "success": True,
            "message": f"Optimization task {task_id} cancelled successfully."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel optimization task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
