"""Feature browser API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.core.logging import get_logger
from api.models.feature_browser_models import (
    CorrelationMatrixResponse,
    FeatureCatalogResponse,
    FeatureDataTableResponse,
    FeatureDistributionResponse,
    FeatureQualityCheckRequest,
    FeatureQualityCheckResponse,
    FeatureTimeSeriesResponse,
)
from api.services.feature_browser_service import feature_browser_service


router = APIRouter(prefix="/api/v1/features", tags=["Feature Browser"])
logger = get_logger("api.routes.feature_browser")


@router.get("/catalog", response_model=FeatureCatalogResponse)
async def get_feature_catalog(features_path: str = Query(..., description="特徵檔案路徑")):
    try:
        return feature_browser_service.get_catalog(features_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to get feature catalog: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{feature_name}/distribution", response_model=FeatureDistributionResponse)
async def get_feature_distribution(
    feature_name: str,
    features_path: str = Query(..., description="特徵檔案路徑"),
    bins: int = Query(50, ge=10, le=200),
):
    try:
        return feature_browser_service.get_distribution(features_path, feature_name, bins)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to get feature distribution: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/time-series", response_model=FeatureTimeSeriesResponse)
async def get_feature_time_series(
    features_path: str = Query(..., description="特徵檔案路徑"),
    features: Optional[str] = Query(None, description="逗號分隔特徵名"),
    sample_rate: int = Query(1, ge=1, le=50),
):
    try:
        selected = [item.strip() for item in (features or "").split(",") if item.strip()]
        return feature_browser_service.get_time_series(features_path, selected, sample_rate)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to get feature time series: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/correlation", response_model=CorrelationMatrixResponse)
async def get_feature_correlation(
    features_path: str = Query(..., description="特徵檔案路徑"),
    features: Optional[str] = Query(None, description="逗號分隔特徵名"),
    method: str = Query("spearman", pattern="^(pearson|spearman|kendall)$"),
    max_features: int = Query(100, ge=2, le=500),
):
    try:
        selected = [item.strip() for item in (features or "").split(",") if item.strip()]
        return feature_browser_service.get_correlation(features_path, selected, method, max_features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to get feature correlation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/quality-check", response_model=FeatureQualityCheckResponse)
async def quality_check_features(request: FeatureQualityCheckRequest):
    try:
        return feature_browser_service.run_quality_check(request.features_path, request.selected_features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to run feature quality check: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/data-table", response_model=FeatureDataTableResponse)
async def get_feature_data_table(
    features_path: str = Query(..., description="特徵檔案路徑"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    columns: Optional[str] = Query(None, description="逗號分隔欄位"),
):
    try:
        selected_columns = [item.strip() for item in (columns or "").split(",") if item.strip()]
        return feature_browser_service.get_data_table(features_path, page, page_size, selected_columns)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to get feature data table: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
