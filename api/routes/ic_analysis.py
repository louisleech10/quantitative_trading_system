"""IC analysis REST API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse

from api.core.logging import get_logger
from api.models.ic_models import (
    DeepAnalysisRequest,
    DeepAnalysisResponse,
    FeatureListItem,
    FeatureListResponse,
    ICAnalyzeRequest,
    ApplyTransformsRequest,
    ApplyTransformsResponse,
    ICAnalyzeResponse,
    ICFullAnalysisRequest,
    ICTaskStatusResponse,
    ICRefilterRequest,
)
from api.services.ic_analysis_service import ic_analysis_service
from momentum.factories import load_ic_config


router = APIRouter(prefix="/api/v1/ic")
logger = get_logger("api.routes.ic_analysis")


@router.post("/analyze", response_model=ICAnalyzeResponse)
async def start_ic_analysis(request: ICAnalyzeRequest):
    """Start IC analysis task."""
    try:
        return await ic_analysis_service.start_analysis(request)
    except ValueError as exc:
        logger.error("Invalid IC analysis request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start IC analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/task/{task_id}", response_model=ICTaskStatusResponse)
async def get_task_status(task_id: str):
    """Get IC analysis task status."""
    try:
        status = ic_analysis_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get task status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/result/{task_id}")
async def get_result(task_id: str, schema_version: Optional[int] = Query(None)):
    """Get IC analysis result."""
    try:
        result = ic_analysis_service.get_result(task_id, schema_version)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get result: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/features/list", response_model=FeatureListResponse)
async def list_available_features(
    features_path: Optional[str] = Query(None, description="Legacy features path or parquet key"),
    meta_path: Optional[str] = None,
    symbol: Optional[str] = Query(None, description="Feature Library symbol"),
    timeframe: Optional[str] = Query(None, description="Feature Library timeframe"),
    config_hash: Optional[str] = Query(None, description="Feature Library config_hash"),
):
    """List available features from HDF5 + optional metadata."""
    try:
        features = ic_analysis_service.list_features(
            features_path=features_path,
            meta_path=meta_path,
            symbol=symbol,
            timeframe=timeframe,
            config_hash=config_hash,
        )
        return {
            "total": len(features),
            "features": [FeatureListItem(**item) for item in features],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to list features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/deep-analysis/{task_id}", response_model=ICAnalyzeResponse)
async def start_deep_analysis(task_id: str, request: DeepAnalysisRequest):
    """Start deep analysis for an existing IC task."""
    try:
        return await ic_analysis_service.start_deep_analysis(task_id, request)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "Task not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message)
    except Exception as exc:
        logger.error("Failed to start deep analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/deep-analysis/{task_id}/result", response_model=DeepAnalysisResponse)
async def get_deep_analysis_result(task_id: str):
    """Get deep analysis result for task."""
    try:
        status = ic_analysis_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        result = ic_analysis_service.get_deep_analysis_result(task_id)
        summary = None
        module_status = None
        if isinstance(result, dict):
            summary = {
                "total_modules": int(result.get("total_modules", 10)),
                "completed_count": int(result.get("completed_count", 0)),
                "skipped_count": int(result.get("skipped_count", 0)),
                "failed_count": int(result.get("failed_count", 0)),
                "total_execution_time_s": float(result.get("total_execution_time_s", 0.0)),
            }
            module_status = [
                {
                    "module_name": module_name,
                    "status": module_state,
                }
                for module_name, module_state in (result.get("module_summary") or {}).items()
            ]

        return {
            "task_id": task_id,
            "status": status.get("status", "running"),
            "progress": float(status.get("progress", 0.0)),
            "current_step": status.get("current_step"),
            "summary": summary,
            "module_status": module_status,
            "results": result,
            "applied_tier": status.get("applied_tier", "intermediate"),
            "error": status.get("error"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get deep analysis result: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/full-analysis", response_model=ICAnalyzeResponse)
async def start_full_analysis(request: ICFullAnalysisRequest):
    """Start one-shot full analysis workflow."""
    try:
        return await ic_analysis_service.start_full_analysis(request)
    except ValueError as exc:
        logger.error("Invalid full analysis request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start full analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summary/{task_id}")
async def get_summary(task_id: str):
    """Get AI summary for IC analysis."""
    try:
        result = ic_analysis_service.get_result(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
        summary = _build_summary(result)
        return {"task_id": task_id, "summary": summary}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get summary: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/top-features")
async def get_top_features(
    n: int = Query(30, ge=1, le=500),
    sort_by: str = Query("icir"),
    task_id: Optional[str] = Query(None),
):
    """Get top features for the latest task."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        analyzer = ic_analysis_service.get_analyzer(resolved_task_id)
        if analyzer is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return analyzer.get_top_features(n=n, sort_by=sort_by)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get top features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/decay/{feature_name}")
async def get_decay(feature_name: str, task_id: Optional[str] = Query(None)):
    """Get IC decay for a feature."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        decay = (result.get("ic_decay") or {}).get(feature_name)
        if decay is None:
            raise HTTPException(status_code=404, detail=f"Feature not found: {feature_name}")
        return decay
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get decay: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/quantile/{feature_name}")
async def get_quantile(feature_name: str, task_id: Optional[str] = Query(None)):
    """Get quantile returns for a feature."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        quantile = (result.get("quantile_returns") or {}).get(feature_name)
        if quantile is None:
            raise HTTPException(status_code=404, detail=f"Feature not found: {feature_name}")
        return quantile
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get quantile returns: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/correlation")
async def get_correlation(task_id: Optional[str] = Query(None)):
    """Get correlation matrix."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        return result.get("correlation_matrix", {})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get correlation matrix: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/grouped")
async def get_grouped(task_id: Optional[str] = Query(None)):
    """Get grouped IC results."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        return result.get("grouped_ic", {})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get grouped IC: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/config")
async def update_config(config_override: Dict[str, Any] = Body(...)):
    """Update IC config by returning merged config."""
    try:
        config = load_ic_config(api_override=config_override)
        return config.model_dump(by_alias=True)
    except Exception as exc:
        logger.error("Failed to update IC config: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/refilter")
async def refilter(
    request: ICRefilterRequest,
    task_id: Optional[str] = Query(None),
):
    """Refilter IC results with new thresholds."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        if not resolved_task_id:
            raise HTTPException(status_code=404, detail="Task not found")
        return await ic_analysis_service.refilter(resolved_task_id, request.thresholds)
    except ValueError as exc:
        logger.error("Invalid refilter request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to refilter: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/{task_id}")
async def export_filtered_features(task_id: str):
    """Export filtered features HDF5."""
    try:
        result = ic_analysis_service.get_result(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")

        metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
        export_path = _resolve_filtered_path(metadata)
        if not export_path.exists():
            raise HTTPException(status_code=404, detail="Filtered features not found")

        return FileResponse(export_path)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to export filtered features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/{task_id}/{format}")
async def export_analysis(
    task_id: str,
    format: str,
    module: Optional[str] = Query(default=None),
):
    """Export analysis report in multi-format outputs."""
    try:
        export_result = ic_analysis_service.export_analysis(
            task_id=task_id,
            format_type=format,
            module_name=module,
        )
        logger.info("Export success: task_id=%s, format=%s, module=%s", task_id, format, module)

        if export_result["type"] == "file":
            return FileResponse(
                path=export_result["path"],
                media_type=export_result["media_type"],
                filename=export_result["filename"],
            )

        headers = {
            "Content-Disposition": f"attachment; filename=\"{export_result['filename']}\"",
        }
        if export_result["type"] == "bytes":
            content = export_result["content"]
            if hasattr(content, "getvalue"):
                content = content.getvalue()
            return Response(
                content=content,
                media_type=export_result["media_type"],
                headers=headers,
            )
        return StreamingResponse(
            export_result["content"],
            media_type=export_result["media_type"],
            headers=headers,
        )
    except ValueError as exc:
        message = str(exc)
        if "Task not found" in message or "Result not found" in message:
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=422, detail=message)
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to export analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export-csv/{task_id}")
async def export_filtered_csv(task_id: str):
    """Export filtered features as CSV."""
    try:
        analyzer = ic_analysis_service.get_analyzer(task_id)
        if analyzer is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        filtered_df = analyzer.get_filtered_features()
        if filtered_df is None or filtered_df.empty:
            raise HTTPException(status_code=404, detail="Filtered features not found")

        output_dir = Path("data_cache/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"ic_filtered_{task_id}.csv"
        filtered_df.to_csv(output_path, index=True)
        return FileResponse(output_path)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to export CSV: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/apply-transforms/{task_id}", response_model=ApplyTransformsResponse)
async def apply_transforms(task_id: str, request: ApplyTransformsRequest):
    """Apply L6.5 post-processing (rank/zscore/gaussian) to IC-selected features.

    Designed for the IC-First workflow:
      1. Feature Factory (IC-First mode) generates L1-L7 with winsor+fracdiff only.
      2. IC Gatekeeper filters to the best features.
      3. Call this endpoint to apply rank/zscore/gaussian to those features.

    Transform order is always: rank → zscore → gaussian.
    """
    try:
        result = await ic_analysis_service.apply_transforms(
            task_id=task_id,
            selected_features=request.selected_features,
            rank=request.rank,
            zscore=request.zscore,
            gaussian=request.gaussian,
            rank_window=request.rank_window,
            zscore_windows=request.zscore_windows,
        )
        return ApplyTransformsResponse(**result)
    except (FileNotFoundError, ValueError) as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception as exc:
        logger.error("apply-transforms failed for task %s: %s", task_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


def _resolve_filtered_path(metadata: Dict[str, Any]) -> Path:
    symbol = metadata.get("symbol") if isinstance(metadata, dict) else None
    timeframe = metadata.get("timeframe") if isinstance(metadata, dict) else None
    if symbol and timeframe:
        name = f"{symbol}_{timeframe}_filtered.h5"
    else:
        name = "filtered_features.h5"
    return Path("data_cache/features") / name


def _build_summary(report: Dict[str, Any]) -> str:
    summary_table = report.get("summary_table", []) if isinstance(report, dict) else []
    top_features = sorted(
        summary_table,
        key=lambda item: item.get("icir", float("-inf")),
        reverse=True,
    )[:5]

    lines = [
        "# IC Gatekeeper Summary",
        "",
        "## Key Findings",
    ]

    if top_features:
        for item in top_features:
            lines.append(
                f"- {item.get('feature_name')}: ICIR={item.get('icir')}, IC Mean={item.get('ic_mean')}"
            )
    else:
        lines.append("- No features passed the filter.")

    lines.extend(
        [
            "",
            "## Regime Analysis",
            "- Regime statistics available in grouped_ic section.",
            "",
            "## Recommendations",
            "- Review thresholds if too few features passed.",
            "",
            "## Risk Warnings",
            "- Event sample size may reduce statistical confidence.",
        ]
    )

    return "\n".join(lines)
