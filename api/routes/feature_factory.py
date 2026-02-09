"""
Feature Factory API Routes
"""

from typing import Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from api.core.logging import get_logger
from api.models.feature_factory_models import (
    FeatureGenerateRequest,
    FeaturePreviewRequest,
    FeaturePreviewResponse,
    FeatureTaskStatusResponse,
    NL2ConfigRequest,
    NL2ConfigResponse,
)
from api.services.feature_factory_service import feature_factory_service


router = APIRouter(prefix="/api/v1/features", tags=["Feature Factory"])
logger = get_logger("api.routes.feature_factory")


@router.get("/presets")
async def get_presets():
    """Get feature presets."""
    try:
        return feature_factory_service.get_presets()
    except Exception as exc:
        logger.error("Failed to get presets: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/config")
async def get_config():
    """Get merged config."""
    try:
        return feature_factory_service.get_config()
    except Exception as exc:
        logger.error("Failed to get config: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/config")
async def update_config(config_override: Dict = Body(...)):
    """Update config (merged output only)."""
    try:
        return feature_factory_service.update_config(config_override)
    except Exception as exc:
        logger.error("Failed to update config: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/config/validate")
async def validate_config(config: Dict = Body(...)):
    """Validate config."""
    try:
        return feature_factory_service.validate_config(config)
    except Exception as exc:
        logger.error("Failed to validate config: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/preview", response_model=FeaturePreviewResponse)
async def preview_features(request: FeaturePreviewRequest):
    """Preview feature counts."""
    try:
        return feature_factory_service.preview(request.config_override)
    except Exception as exc:
        logger.error("Failed to preview features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/generate")
async def generate_features(request: FeatureGenerateRequest):
    """Start feature generation task."""
    try:
        return await feature_factory_service.start_generation(request)
    except ValueError as exc:
        logger.error("Invalid request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start generation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/task/{task_id}", response_model=FeatureTaskStatusResponse)
async def get_task_status(task_id: str):
    """Get task status."""
    try:
        status = feature_factory_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get task status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/result/{task_id}")
async def get_task_result(task_id: str):
    """Get task result if available."""
    try:
        result = feature_factory_service.get_result(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get task result: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/nl2config", response_model=NL2ConfigResponse)
async def nl2config(request: NL2ConfigRequest):
    """Convert natural language to config patch."""
    try:
        return feature_factory_service.nl2config(request.text)
    except ValueError as exc:
        logger.error("Invalid NL2Config request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to convert NL to config: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/indicators")
async def list_indicators(category: Optional[str] = Query(None, description="指標分類")):
    """List all indicators."""
    try:
        return feature_factory_service.list_indicators(category)
    except Exception as exc:
        logger.error("Failed to list indicators: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/data-sources")
async def list_data_sources():
    """List all data sources."""
    try:
        return feature_factory_service.list_data_sources()
    except Exception as exc:
        logger.error("Failed to list data sources: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metadata/{feature_name}")
async def get_feature_metadata(feature_name: str):
    """Get feature metadata."""
    try:
        return feature_factory_service.get_feature_metadata(feature_name)
    except Exception as exc:
        logger.error("Failed to get feature metadata: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/research/start")
async def start_research(payload: Optional[Dict] = Body(None)):
    """Start AutoResearch task."""
    try:
        return feature_factory_service.start_research(payload)
    except Exception as exc:
        logger.error("Failed to start research: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/research/{task_id}/status")
async def get_research_status(task_id: str):
    """Get AutoResearch task status."""
    try:
        status = feature_factory_service.get_research_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get research status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/research/{task_id}/stop")
async def stop_research(task_id: str):
    """Stop AutoResearch task."""
    try:
        status = feature_factory_service.stop_research(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to stop research: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/research/{task_id}/results")
async def get_research_results(task_id: str):
    """Get AutoResearch results."""
    try:
        results = feature_factory_service.get_research_results(task_id)
        if results is None:
            raise HTTPException(status_code=404, detail=f"Results not found: {task_id}")
        return results
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get research results: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/research/history")
async def get_research_history():
    """Get AutoResearch history."""
    try:
        return feature_factory_service.get_research_history()
    except Exception as exc:
        logger.error("Failed to get research history: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
