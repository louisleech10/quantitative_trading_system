"""Model enhancement API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.models.model_enhancement import (
    AdversarialValidateRequest,
    CPCVRequest,
    CalibrateRequest,
    FullEnhancementRequest,
    FullEnhancementResponse,
    LearningCurveRequest,
    ModelEnhancementResponse,
    SampleWeightRequest,
    WalkForwardRequest,
)
from api.services.model_enhancement_service import get_model_enhancement_service


router = APIRouter(prefix="/api/v1/model-enhancement", tags=["Model Enhancement"])


@router.post("/calibrate", response_model=ModelEnhancementResponse)
async def calibrate(request: CalibrateRequest):
    return await get_model_enhancement_service().execute_calibration(request)


@router.post("/walk-forward", response_model=ModelEnhancementResponse)
async def walk_forward(request: WalkForwardRequest):
    return await get_model_enhancement_service().execute_walk_forward(request)


@router.post("/sample-weights", response_model=ModelEnhancementResponse)
async def sample_weights(request: SampleWeightRequest):
    return await get_model_enhancement_service().execute_sample_weights(request)


@router.post("/adversarial-validate", response_model=ModelEnhancementResponse)
async def adversarial_validate(request: AdversarialValidateRequest):
    return await get_model_enhancement_service().execute_adversarial(request)


@router.post("/cpcv", response_model=ModelEnhancementResponse)
async def cpcv(request: CPCVRequest):
    return await get_model_enhancement_service().execute_cpcv(request)


@router.post("/learning-curve", response_model=ModelEnhancementResponse)
async def learning_curve(request: LearningCurveRequest):
    return await get_model_enhancement_service().execute_learning_curve(request)


@router.get("/task/{task_id}", response_model=ModelEnhancementResponse)
async def task_status(task_id: str):
    result = get_model_enhancement_service().get_task_status(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return result


@router.post("/full-enhancement", response_model=FullEnhancementResponse)
async def full_enhancement(request: FullEnhancementRequest):
    return await get_model_enhancement_service().execute_full_enhancement(request)
