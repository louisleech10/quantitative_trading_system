"""
優化分析 REST API - Optuna優化結果分析

功能:
1. 參數重要性分析（GET /optimization/tasks/{task_id}/analysis/importance）
2. 優化歷史曲線數據（GET /optimization/tasks/{task_id}/analysis/history）
3. 參數空間數據（GET /optimization/tasks/{task_id}/analysis/param-space）

Author: Claude (Phase 3.5 Day 7-8)
Date: 2025-11-02
"""

from typing import Optional, Dict, List, Any, TYPE_CHECKING
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# 延遲導入 optuna 以避免 sklearn 在模塊加載時初始化
if TYPE_CHECKING:
    import optuna

from api.core.logging import get_logger
from api.services.optimization_task_service import (
    optimization_task_service,
    OptimizationTaskStatus
)
# from momentum.Optimization.result_analyzer import ResultAnalyzer  # 延遲導入以避免 optuna 在模塊加載時初始化


router = APIRouter(prefix="/api/v1/optimization")
logger = get_logger("api.routes.optimization_analysis")


# ==================== Response Models ====================

class ParameterImportance(BaseModel):
    """參數重要性"""
    parameter_name: str
    importance: float
    rank: int  # 1 = 最重要


class ImportanceAnalysisResponse(BaseModel):
    """參數重要性分析響應"""
    success: bool
    task_id: str
    study_name: str
    n_trials: int
    importances: List[ParameterImportance]
    evaluator: str  # fanova, mean_decrease_impurity
    message: Optional[str] = None


class OptimizationHistoryPoint(BaseModel):
    """優化歷史點"""
    trial_number: int
    value: float
    best_value_so_far: float
    datetime: str
    params: Dict[str, Any]
    state: str  # COMPLETE, PRUNED, FAIL


class OptimizationHistoryResponse(BaseModel):
    """優化歷史響應"""
    success: bool
    task_id: str
    study_name: str
    history: List[OptimizationHistoryPoint]
    total_trials: int


class ParamSpacePoint(BaseModel):
    """參數空間點"""
    trial_number: int
    value: float
    params: Dict[str, Any]
    state: str


class ParamSpaceResponse(BaseModel):
    """參數空間響應"""
    success: bool
    task_id: str
    study_name: str
    points: List[ParamSpacePoint]
    param_names: List[str]
    total_trials: int


# ==================== Helper Functions ====================

def _get_study_from_task(task_id: str) -> "optuna.Study":
    """
    從任務ID獲取Optuna Study

    Args:
        task_id: 任務ID

    Returns:
        Optuna Study對象

    Raises:
        HTTPException: 任務不存在或未完成
    """
    import optuna  # 延遲導入

    task_info = optimization_task_service.get_task(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task_info.status not in [OptimizationTaskStatus.COMPLETED, OptimizationTaskStatus.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Task must be RUNNING or COMPLETED for analysis. Current status: {task_info.status.value}"
        )

    # 從TaskService獲取Study（通過study_name）
    try:
        # 使用Optuna的load_study（假設使用SQLite storage）
        study_name = task_info.study_name
        storage = optimization_task_service._get_storage_for_study(study_name)
        study = optuna.load_study(study_name=study_name, storage=storage)
        return study
    except Exception as e:
        logger.error(f"Failed to load study for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load study: {str(e)}")


# ==================== API Endpoints ====================

@router.get("/tasks/{task_id}/analysis/importance", response_model=ImportanceAnalysisResponse)
async def get_parameter_importance(
    task_id: str,
    evaluator: str = Query("fanova", description="重要性評估器（fanova/mean_decrease_impurity）"),
    n_trials: Optional[int] = Query(None, description="使用最近N次試驗（None=全部）")
):
    """
    計算參數重要性

    使用Optuna內建的參數重要性分析，計算每個參數對目標函數的影響程度。

    支援兩種評估器:
    - **fanova**: Functional ANOVA（適用於連續/類別參數，推薦）
    - **mean_decrease_impurity**: 基於決策樹的特徵重要性（適用於大量試驗）

    Args:
        task_id: 任務ID
        evaluator: 評估器類型
        n_trials: 使用最近N次試驗（None表示使用全部試驗）

    Returns:
        參數重要性列表（降序排序）

    Example:
        GET /api/v1/optimization/tasks/xxx/analysis/importance?evaluator=fanova

        Response:
        {
            "success": true,
            "task_id": "xxx",
            "study_name": "momentum_opt_001",
            "n_trials": 100,
            "importances": [
                {"parameter_name": "threshold", "importance": 0.456, "rank": 1},
                {"parameter_name": "min_candles", "importance": 0.234, "rank": 2},
                ...
            ],
            "evaluator": "fanova"
        }
    """
    try:
        # 獲取Study
        study = _get_study_from_task(task_id)

        # 獲取試驗數量
        trials = study.trials
        if n_trials is not None:
            trials = trials[-n_trials:]  # 取最近N次

        if len(trials) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 completed trials for importance analysis"
            )

        # 計算參數重要性
        import optuna  # 延遲導入

        if evaluator == "fanova":
            # 使用FANOVA（推薦）
            try:
                importance_dict = optuna.importance.get_param_importances(
                    study,
                    evaluator=optuna.importance.FanovaImportanceEvaluator(),
                    params=None  # None = 計算所有參數
                )
            except Exception as e:
                logger.warning(f"FANOVA failed, falling back to mean_decrease_impurity: {e}")
                # FANOVA可能失敗（例如參數太少），回退到MDI
                importance_dict = optuna.importance.get_param_importances(
                    study,
                    evaluator=optuna.importance.MeanDecreaseImpurityImportanceEvaluator(),
                    params=None
                )
                evaluator = "mean_decrease_impurity"

        elif evaluator == "mean_decrease_impurity":
            # 使用Mean Decrease Impurity
            importance_dict = optuna.importance.get_param_importances(
                study,
                evaluator=optuna.importance.MeanDecreaseImpurityImportanceEvaluator(),
                params=None
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported evaluator: {evaluator}. Use 'fanova' or 'mean_decrease_impurity'"
            )

        # 轉換為響應格式（降序排序）
        importances = [
            ParameterImportance(
                parameter_name=param_name,
                importance=importance,
                rank=rank + 1
            )
            for rank, (param_name, importance) in enumerate(
                sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
            )
        ]

        logger.info(f"Parameter importance calculated for task {task_id}: {len(importances)} parameters")

        return ImportanceAnalysisResponse(
            success=True,
            task_id=task_id,
            study_name=study.study_name,
            n_trials=len(trials),
            importances=importances,
            evaluator=evaluator
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate parameter importance for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/analysis/history", response_model=OptimizationHistoryResponse)
async def get_optimization_history(
    task_id: str,
    n_trials: Optional[int] = Query(None, description="返回最近N次試驗（None=全部）")
):
    """
    獲取優化歷史曲線數據

    返回每次試驗的值、累計最佳值、參數等信息，用於繪製優化曲線。

    Args:
        task_id: 任務ID
        n_trials: 返回最近N次試驗（None表示返回全部）

    Returns:
        優化歷史列表

    Example:
        GET /api/v1/optimization/tasks/xxx/analysis/history?n_trials=50

        Response:
        {
            "success": true,
            "task_id": "xxx",
            "study_name": "momentum_opt_001",
            "history": [
                {
                    "trial_number": 0,
                    "value": 0.234,
                    "best_value_so_far": 0.234,
                    "datetime": "2025-11-02T10:00:00",
                    "params": {"threshold": 0.5, ...},
                    "state": "COMPLETE"
                },
                ...
            ],
            "total_trials": 100
        }
    """
    import optuna  # 延遲導入

    try:
        # 獲取Study
        study = _get_study_from_task(task_id)

        # 獲取試驗
        trials = study.trials
        if n_trials is not None:
            trials = trials[-n_trials:]

        # 構建歷史數據
        history = []
        best_value = float('inf') if study.direction == optuna.study.StudyDirection.MINIMIZE else float('-inf')

        for trial in trials:
            # 更新累計最佳值
            if trial.state == optuna.trial.TrialState.COMPLETE:
                if study.direction == optuna.study.StudyDirection.MINIMIZE:
                    best_value = min(best_value, trial.value)
                else:
                    best_value = max(best_value, trial.value)

            history.append(
                OptimizationHistoryPoint(
                    trial_number=trial.number,
                    value=trial.value if trial.value is not None else 0.0,
                    best_value_so_far=best_value,
                    datetime=trial.datetime_complete.isoformat() if trial.datetime_complete else "",
                    params=trial.params,
                    state=trial.state.name
                )
            )

        logger.info(f"Optimization history retrieved for task {task_id}: {len(history)} trials")

        return OptimizationHistoryResponse(
            success=True,
            task_id=task_id,
            study_name=study.study_name,
            history=history,
            total_trials=len(study.trials)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization history for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/analysis/param-space", response_model=ParamSpaceResponse)
async def get_parameter_space(
    task_id: str,
    n_trials: Optional[int] = Query(None, description="返回最近N次試驗（None=全部）")
):
    """
    獲取參數空間數據

    返回每次試驗的參數組合和對應的目標值，用於繪製參數空間散點圖。

    Args:
        task_id: 任務ID
        n_trials: 返回最近N次試驗（None表示返回全部）

    Returns:
        參數空間數據點列表

    Example:
        GET /api/v1/optimization/tasks/xxx/analysis/param-space

        Response:
        {
            "success": true,
            "task_id": "xxx",
            "study_name": "momentum_opt_001",
            "points": [
                {
                    "trial_number": 0,
                    "value": 0.234,
                    "params": {"threshold": 0.5, "min_candles": 10},
                    "state": "COMPLETE"
                },
                ...
            ],
            "param_names": ["threshold", "min_candles", ...],
            "total_trials": 100
        }
    """
    import optuna  # 延遲導入

    try:
        # 獲取Study
        study = _get_study_from_task(task_id)

        # 獲取試驗
        trials = study.trials
        if n_trials is not None:
            trials = trials[-n_trials:]

        # 構建參數空間數據
        points = []
        for trial in trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                points.append(
                    ParamSpacePoint(
                        trial_number=trial.number,
                        value=trial.value,
                        params=trial.params,
                        state=trial.state.name
                    )
                )

        # 獲取參數名稱列表
        param_names = list(study.best_params.keys()) if study.best_trial else []

        logger.info(f"Parameter space data retrieved for task {task_id}: {len(points)} points")

        return ParamSpaceResponse(
            success=True,
            task_id=task_id,
            study_name=study.study_name,
            points=points,
            param_names=param_names,
            total_trials=len(study.trials)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get parameter space for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Ultra Think Step 3 優化: 新增端點 ====================

# 延遲初始化 ResultAnalyzer（避免在模塊加載時導入 optuna）
_result_analyzer = None

def get_result_analyzer():
    """延遲初始化 ResultAnalyzer"""
    global _result_analyzer
    if _result_analyzer is None:
        from momentum.Optimization.result_analyzer import ResultAnalyzer
        _result_analyzer = ResultAnalyzer()
    return _result_analyzer


@router.get("/tasks/{task_id}/analysis/heatmap")
async def get_parameter_heatmap(
    task_id: str,
    param_x: str = Query(..., description="X 軸參數名"),
    param_y: str = Query(..., description="Y 軸參數名"),
    max_trials: int = Query(1000, description="最大 trials 數量")
):
    """
    獲取參數空間熱力圖數據

    返回 2D 參數組合與目標值映射，用於繪製熱力圖。

    Args:
        task_id: 任務 ID
        param_x: X 軸參數名（如 "ema_short"）
        param_y: Y 軸參數名（如 "ema_mid"）
        max_trials: 最大 trials 數量（默認 1000）

    Returns:
        熱力圖數據點列表

    Example:
        GET /api/v1/optimization/tasks/xxx/analysis/heatmap?param_x=ema_short&param_y=ema_mid
    """
    try:
        study = _get_study_from_task(task_id)
        heatmap_data = get_result_analyzer().generate_heatmap_data(
            study=study,
            param_x=param_x,
            param_y=param_y,
            max_trials=max_trials
        )

        logger.info(
            f"Generated heatmap for task {task_id}: "
            f"{len(heatmap_data.data_points)} points"
        )

        return {
            "success": True,
            "task_id": task_id,
            "data": heatmap_data.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate heatmap for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/analysis/convergence")
async def get_convergence_analysis(
    task_id: str,
    convergence_threshold: float = Query(0.05, description="收斂閾值（默認 5%）"),
    window_ratio: float = Query(0.2, description="檢測窗口比例（默認 20%）")
):
    """
    獲取收斂分析數據

    檢測優化是否已收斂，返回收斂點和 best value 歷史。

    Args:
        task_id: 任務 ID
        convergence_threshold: 收斂閾值（默認 0.05 = 5%）
        window_ratio: 檢測窗口比例（默認 0.2 = 20%）

    Returns:
        收斂分析結果

    Example:
        GET /api/v1/optimization/tasks/xxx/analysis/convergence
    """
    try:
        study = _get_study_from_task(task_id)
        convergence_analysis = get_result_analyzer().analyze_convergence(
            study=study,
            convergence_threshold=convergence_threshold,
            window_ratio=window_ratio
        )

        logger.info(
            f"Convergence analysis for task {task_id}: "
            f"converged={convergence_analysis.converged}"
        )

        return {
            "success": True,
            "task_id": task_id,
            "data": convergence_analysis.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze convergence for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/analysis/stability")
async def get_stability_analysis(
    task_id: str,
    time_attr: str = Query("datetime_start", description="Trial 時間屬性名")
):
    """
    獲取穩定性分析數據

    按月份分組計算平均值和標準差，識別最差和最佳月份。

    Args:
        task_id: 任務 ID
        time_attr: Trial 時間屬性名（默認 "datetime_start"）

    Returns:
        穩定性分析結果

    Example:
        GET /api/v1/optimization/tasks/xxx/analysis/stability
    """
    try:
        study = _get_study_from_task(task_id)
        stability_analysis = get_result_analyzer().analyze_stability(
            study=study,
            time_attr=time_attr
        )

        logger.info(
            f"Stability analysis for task {task_id}: "
            f"overall_cv={stability_analysis.overall_cv:.4f}"
        )

        return {
            "success": True,
            "task_id": task_id,
            "data": stability_analysis.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze stability for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/trials")
async def get_top_trials(
    task_id: str,
    top_n: int = Query(20, description="返回前 N 個最佳 trials，-1 表示返回所有"),
    sort_by: str = Query("value", description="排序依據（value）"),
    include_params: bool = Query(True, description="是否包含參數詳情"),
    include_all_states: bool = Query(False, description="是否包含所有狀態（PRUNED, FAILED）")
):
    """
    獲取 Top N trials

    返回排序後的最佳 trials 列表。

    Args:
        task_id: 任務 ID
        top_n: 返回前 N 個最佳 trials（默認 20），-1 表示返回所有
        sort_by: 排序依據（目前僅支援 "value"）
        include_params: 是否包含參數詳情（默認 True）
        include_all_states: 是否包含所有狀態（PRUNED, FAILED），默認只返回 COMPLETE

    Returns:
        Trial 排名列表

    Example:
        GET /api/v1/optimization/tasks/xxx/trials?top_n=-1&include_all_states=true
    """
    try:
        study = _get_study_from_task(task_id)
        top_trials = get_result_analyzer().get_top_trials(
            study=study,
            top_n=top_n,
            include_params=include_params,
            include_all_states=include_all_states
        )

        logger.info(f"Retrieved top {len(top_trials)} trials for task {task_id} (include_all_states={include_all_states})")

        return {
            "success": True,
            "task_id": task_id,
            "trials": top_trials,
            "total_count": len(top_trials)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get top trials for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/result")
async def get_optimization_result(task_id: str):
    """
    獲取完整優化結果

    返回最佳參數、最佳值、trial 數量等完整信息。

    Args:
        task_id: 任務 ID

    Returns:
        完整優化結果

    Example:
        GET /api/v1/optimization/tasks/xxx/result
    """
    try:
        task_info = optimization_task_service.get_task(task_id)

        if not task_info:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        if task_info.status != OptimizationTaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Task must be COMPLETED. Current status: {task_info.status.value}"
            )

        if not task_info.result:
            raise HTTPException(
                status_code=404,
                detail=f"No result found for task {task_id}"
            )

        result = task_info.result

        # 計算 trial 統計
        trial_stats = None
        try:
            import optuna
            study = _get_study_from_task(task_id)
            all_trials = study.get_trials(deepcopy=False)

            # 統計各狀態的 trial 數量
            complete_count = sum(1 for t in all_trials if t.state == optuna.trial.TrialState.COMPLETE)
            pruned_count = sum(1 for t in all_trials if t.state == optuna.trial.TrialState.PRUNED)
            failed_count = sum(1 for t in all_trials if t.state == optuna.trial.TrialState.FAIL)

            trial_stats = {
                "total": len(all_trials),
                "complete": complete_count,
                "pruned": pruned_count,
                "failed": failed_count
            }
        except Exception as e:
            logger.warning(f"Failed to calculate trial stats for task {task_id}: {e}")

        logger.info(f"Retrieved optimization result for task {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "study_name": task_info.study_name,
            "result": {
                "best_value": result.best_value,
                "best_params": result.best_params,
                "best_trial_number": result.best_trial_number,
                "n_trials": result.total_trials if hasattr(result, 'total_trials') else result.n_trials if hasattr(result, 'n_trials') else None,
                "optimization_time": result.optimization_time if hasattr(result, 'optimization_time') else result.optimization_time_seconds if hasattr(result, 'optimization_time_seconds') else None,
                "study_direction": result.study_direction if hasattr(result, 'study_direction') else "maximize",
                "convergence_info": result.convergence_info if hasattr(result, 'convergence_info') else None
            },
            "trial_stats": trial_stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get result for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
