"""Feature toggle routes for Phase 6 (M7)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models.feature_toggle_models import (
    BatchToggleResponse,
    BatchToggleUpdateRequest,
    FeatureToggleListResponse,
    FeatureToggleResponse,
    FeatureToggleUpdateRequest,
)
from api.services.feature_toggle_service import get_feature_toggle_service


router = APIRouter(prefix="/api/v1/feature-toggles", tags=["Feature Toggles"])


@router.get("", response_model=FeatureToggleListResponse)
async def get_feature_toggles(
    difficulty: Optional[str] = Query(default=None, pattern="^(L1|L2|L3)?$"),
):
    try:
        return get_feature_toggle_service().list_toggles(difficulty=difficulty)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.put("/batch", response_model=BatchToggleResponse)
async def batch_update_toggles(request: BatchToggleUpdateRequest):
    try:
        return get_feature_toggle_service().batch_update(request.updates)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.put("/{feature_id}", response_model=FeatureToggleResponse)
async def update_feature_toggle(feature_id: str, request: FeatureToggleUpdateRequest):
    try:
        return get_feature_toggle_service().update_toggle(feature_id, request.enabled)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/presets/{preset_name}", response_model=FeatureToggleListResponse)
async def apply_preset(preset_name: str):
    try:
        return get_feature_toggle_service().apply_preset(preset_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
