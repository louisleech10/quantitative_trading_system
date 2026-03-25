"""Cross-symbol training API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.services.cross_symbol_training_service import CrossSymbolTrainingService


router = APIRouter(prefix="/cross-symbol", tags=["cross-symbol"])
_service = CrossSymbolTrainingService()


class CrossSymbolValidationRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=2, description="至少 2 個 symbol")
    timeframe: str
    label_column: str = "label"
    feature_columns: Optional[List[str]] = None


@router.post("/validate")
async def run_validation(request: CrossSymbolValidationRequest):
    """Execute cross-symbol leave-one-out validation."""
    return await _service.run_cross_symbol_validation(
        symbols=request.symbols,
        timeframe=request.timeframe,
        label_column=request.label_column,
        feature_columns=request.feature_columns,
    )
