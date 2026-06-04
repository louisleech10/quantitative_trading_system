"""Feature browser API routes.

Phase 8 的特徵瀏覽器頁面已併入 Feature Factory，僅保留跨 Symbol
Coverage Matrix 端點（真實 NaN 覆蓋率計算）。原本骨架期的 IC / SHAP /
模型重要度 / quality-scorecard 等端點為未串接的占位實作，已隨頁面下架移除。
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from api.core.logging import get_logger
from api.models.feature_browser_models import (
    CoverageMatrixRequest,
    CoverageMatrixResponse,
    GroupCoverageRequest,
    GroupCoverageResponse,
    GroupFeatureCoverageRequest,
    GroupFeatureCoverageResponse,
)
from api.services.feature_browser_service import feature_browser_service


router = APIRouter(prefix="/api/v1", tags=["Feature Browser"])
logger = get_logger("api.routes.feature_browser")


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    logger.error("Feature browser route failed: %s", exc, exc_info=True)
    return HTTPException(status_code=500, detail=str(exc))


@router.post("/feature-browser/coverage-matrix", response_model=CoverageMatrixResponse)
async def post_coverage_matrix(request: CoverageMatrixRequest):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                feature_browser_service.get_coverage_matrix,
                symbols=request.symbols,
                timeframe=request.timeframe,
                feature_names=request.feature_names,
                feature_base_path=request.feature_base_path,
            ),
            timeout=request.timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Coverage Matrix 計算逾時，請縮小 Symbol 或 Feature 範圍") from exc
    except Exception as exc:
        raise _http_error(exc)


@router.post("/feature-browser/group-coverage", response_model=GroupCoverageResponse)
async def post_group_coverage(request: GroupCoverageRequest):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                feature_browser_service.get_group_coverage,
                symbols=request.symbols,
                timeframe=request.timeframe,
                feature_base_path=request.feature_base_path,
            ),
            timeout=request.timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Group Coverage 計算逾時，請縮小 Symbol 範圍") from exc
    except Exception as exc:
        raise _http_error(exc)


@router.post("/feature-browser/group-feature-coverage", response_model=GroupFeatureCoverageResponse)
async def post_group_feature_coverage(request: GroupFeatureCoverageRequest):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                feature_browser_service.get_group_feature_coverage,
                symbols=request.symbols,
                timeframe=request.timeframe,
                group_name=request.group_name,
                feature_base_path=request.feature_base_path,
                top_n=request.top_n,
            ),
            timeout=request.timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="Group Feature Coverage 計算逾時，請縮小 Symbol 或 top_n",
        ) from exc
    except Exception as exc:
        raise _http_error(exc)
