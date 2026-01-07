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
from momentum.Analysis.strategy_registry import strategy_registry


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
    n_startup_trials: Optional[int] = Field(None, description="TPE 初始隨機試驗數（None 則自動設為 n_trials 的 15-25%）", ge=1, le=1000)
    n_jobs: int = Field(1, description="並行核心數（目前架構不支援真正多核）", ge=1, le=16)
    use_multi_objective: bool = Field(False, description="是否使用多目標優化（separation + stability）")
    enable_pruning: bool = Field(True, description="是否啟用 Pruner（MedianPruner）")
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
                "n_startup_trials": 15,
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
            n_startup_trials=request.n_startup_trials,
            n_jobs=request.n_jobs,
            parameter_ranges=request.parameter_ranges,
            use_multi_objective=request.use_multi_objective,
            enable_pruning=request.enable_pruning
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


# ==================== Strategy Management Endpoints ====================

class StrategyListResponse(BaseModel):
    """策略列表響應"""
    success: bool
    strategies: List[dict]
    total: int


class StrategyDetailResponse(BaseModel):
    """策略詳情響應"""
    success: bool
    strategy: dict


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies():
    """
    列出所有可用策略

    返回系統中註冊的所有策略及其基本信息。

    Returns:
        策略列表，每個策略包含：
        - strategy_id: 策略唯一標識符
        - display_name: 顯示名稱
        - description: 策略描述
        - category: 策略分類
        - complexity: 複雜度等級
        - icon: 策略圖標
        - tags: 標籤列表
        - parameter_count: 參數數量
    """
    try:
        strategy_list = strategy_registry.list_strategies()
        strategies = []

        for metadata in strategy_list:
            strategies.append({
                "strategy_id": metadata.strategy_id,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "category": metadata.category,
                "complexity": metadata.complexity,
                "icon": metadata.icon,
                "tags": metadata.tags,
                "parameter_count": len(metadata.parameters),
                "supported_indicators": metadata.supported_indicators,
                "supported_data_sources": metadata.supported_data_sources
            })

        logger.info(f"Listed {len(strategies)} strategies")

        return StrategyListResponse(
            success=True,
            strategies=strategies,
            total=len(strategies)
        )

    except Exception as e:
        logger.error(f"Failed to list strategies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy_detail(strategy_id: str):
    """
    獲取策略詳細信息

    返回指定策略的完整配置信息，包括所有參數定義、約束條件等。

    Args:
        strategy_id: 策略唯一標識符

    Returns:
        策略詳細信息，包含：
        - 基本信息（strategy_id, display_name, description等）
        - 參數定義列表（每個參數的類型、範圍、約束等）
        - 支援的指標和數據源
        - 計算函數位置
    """
    try:
        metadata = strategy_registry.get_strategy(strategy_id)

        # 構建參數定義
        parameters = []
        for param in metadata.parameters:
            param_dict = {
                "name": param.name,
                "display_name": param.display_name,
                "type": param.type,
                "default_value": param.default_value,
                "description": param.description,
                "unit": param.unit
            }

            # 根據類型添加額外字段
            if param.type in ["int", "float"]:
                param_dict["min_value"] = param.min_value
                param_dict["max_value"] = param.max_value
                param_dict["step"] = param.step
            elif param.type == "categorical":
                param_dict["choices"] = param.choices

            # 添加約束條件
            if param.constraints:
                param_dict["constraints"] = [
                    {
                        "type": c.type,
                        "target": c.target,
                        "message": c.message
                    }
                    for c in param.constraints
                ]

            parameters.append(param_dict)

        strategy_detail = {
            "strategy_id": metadata.strategy_id,
            "display_name": metadata.display_name,
            "description": metadata.description,
            "category": metadata.category,
            "complexity": metadata.complexity,
            "icon": metadata.icon,
            "tags": metadata.tags,
            "recommended_for": metadata.recommended_for,
            "parameters": parameters,
            "supported_indicators": metadata.supported_indicators,
            "supported_data_sources": metadata.supported_data_sources,
            "calculator_module": metadata.calculator_module,
            "calculator_function": metadata.calculator_function
        }

        logger.info(f"Retrieved strategy detail: {strategy_id}")

        return StrategyDetailResponse(
            success=True,
            strategy=strategy_detail
        )

    except ValueError as e:
        logger.warning(f"Strategy not found: {strategy_id}")
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")
    except Exception as e:
        logger.error(f"Failed to get strategy detail for {strategy_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
