"""IC analysis REST API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse

from api.core.logging import get_logger
from api.models.ic_models import (
    ICAnalyzeRequest,
    ICAnalyzeResponse,
    ICTaskStatusResponse,
    ICRefilterRequest,
)
from api.services.ic_analysis_service import ic_analysis_service
from momentum.Analysis.ic_config_schema import load_ic_config


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
async def get_result(task_id: str):
    """Get IC analysis result."""
    try:
        result = ic_analysis_service.get_result(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get result: %s", exc, exc_info=True)
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
