"""Phase 4.3 Hyperparameter Optimization routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from api.core.logging import get_logger
from api.models.optimization_models import (
    HyperparamOptimizationRequest,
    HyperparamOptimizationResponse,
    OptimizationConfigResponse,
    OptimizationExportRequest,
)
from api.services.optimization_output_service import get_optimization_output_service
from api.services.optimization_task_service import optimization_task_service
from momentum.factories import get_momentum_config_class

MomentumConfig = get_momentum_config_class()


router = APIRouter(prefix="/api/v1/optimization", tags=["Hyperparameter Optimization"])
logger = get_logger("api.routes.hyperparameter_optimization")


def _remove_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


@router.post("/hyperparameter", response_model=HyperparamOptimizationResponse)
async def start_hyperparameter_optimization(
    request: HyperparamOptimizationRequest,
) -> HyperparamOptimizationResponse:
    """啟動超參數優化任務。"""
    try:
        features_path = Path(request.features_path)
        labels_path = Path(request.labels_path)

        if not features_path.exists():
            raise HTTPException(status_code=422, detail=f"features_path not found: {features_path}")
        if not labels_path.exists():
            raise HTTPException(status_code=422, detail=f"labels_path not found: {labels_path}")

        features_df = pd.read_csv(features_path)
        labels_df = pd.read_csv(labels_path)
        if labels_df.shape[1] == 0:
            raise HTTPException(status_code=422, detail="labels_path has no columns")

        labels = labels_df.iloc[:, 0]
        if len(features_df) != len(labels):
            raise HTTPException(status_code=422, detail="features and labels row count mismatch")

        objective_config: Dict[str, Any] = {
            "engine": request.model_type,
            "features": features_df.to_dict(orient="records"),
            "labels": labels.tolist(),
            "feature_names": features_df.columns.tolist(),
            "cv_folds": request.cv_folds,
            "max_train_val_gap": request.max_train_val_gap,
            "search_space_override": request.search_space_override,
        }

        task_id = optimization_task_service.create_task(
            study_name=f"hyperparam_{request.model_type}_{features_path.stem}",
            positive_cases=[],
            negative_cases=[],
            training_window=None,
            task_type="model_hyperparam",
            objective_config=objective_config,
            n_trials=request.n_trials,
            timeout_seconds=request.timeout_seconds,
        )

        started = await optimization_task_service.start_task(task_id)
        if not started:
            raise HTTPException(status_code=500, detail=f"Failed to start task: {task_id}")

        task_info = optimization_task_service.get_task(task_id)
        return HyperparamOptimizationResponse(
            task_id=task_id,
            status=(task_info.status.value if task_info else "pending"),
            created_at=(task_info.created_at.isoformat() if task_info else ""),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to start hyperparameter optimization: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/config", response_model=OptimizationConfigResponse)
async def get_optimization_config() -> OptimizationConfigResponse:
    """取得優化配置。"""
    try:
        config = MomentumConfig.load_optimization_config()
        return OptimizationConfigResponse(
            execution=config.get("execution", {}),
            hyperparameter=config.get("hyperparameter", {}),
        )
    except Exception as exc:
        logger.error(f"Failed to load optimization config: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{task_type}/{task_id}/export")
async def export_optimization_result(
    task_type: str,
    task_id: str,
    request: OptimizationExportRequest,
):
    """匯出優化結果（Phase 4.5: json/csv/html/charts/full）。"""
    if task_type not in {"execution", "hyperparameter"}:
        raise HTTPException(status_code=400, detail="task_type must be execution or hyperparameter")

    task_info = optimization_task_service.get_task(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    output_service = get_optimization_output_service()
    optimizers = getattr(optimization_task_service, "optimizers", {})
    optimizer = optimizers.get(task_id) if isinstance(optimizers, dict) else None
    artifacts = output_service.ensure_outputs(
        task_type=task_type,
        task_id=task_id,
        task_info=task_info,
        optimizer=optimizer,
    )

    if request.format == "json":
        return JSONResponse(output_service.load_summary(task_type=task_type, task_id=task_id))

    if request.format == "csv":
        file_path = artifacts["trials_csv"] if artifacts["trials_csv"].exists() else artifacts["summary_csv"]
        return FileResponse(
            path=str(file_path),
            media_type="text/csv",
            filename=file_path.name,
        )

    if request.format == "html":
        file_path = artifacts["html_report"]
        return FileResponse(
            path=str(file_path),
            media_type="text/html",
            filename=file_path.name,
        )

    if request.format == "charts":
        chart_files = [
            artifacts["equity_curve_csv"],
            artifacts["trials_csv"],
            artifacts["summary_json"],
        ]
        content = output_service.build_zip_bytes(chart_files)
        temp_path = output_service.save_temp_bytes(content, suffix=".zip")
        file_name = f"optimization_charts_{task_type}_{task_id}.zip"
        return FileResponse(
            path=temp_path,
            media_type="application/zip",
            filename=file_name,
            background=BackgroundTask(_remove_temp_file, temp_path),
        )

    if request.format == "full":
        full_files = [
            artifacts["summary_json"],
            artifacts["summary_csv"],
            artifacts["trades_csv"],
            artifacts["equity_curve_csv"],
            artifacts["trials_csv"],
            artifacts["ai_report_md"],
            artifacts["html_report"],
        ]
        content = output_service.build_zip_bytes(full_files)
        temp_path = output_service.save_temp_bytes(content, suffix=".zip")
        file_name = f"optimization_full_{task_type}_{task_id}.zip"
        return FileResponse(
            path=temp_path,
            media_type="application/zip",
            filename=file_name,
            background=BackgroundTask(_remove_temp_file, temp_path),
        )

    raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")
