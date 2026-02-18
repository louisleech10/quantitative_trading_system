"""Feature browser API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.core.logging import get_logger
from api.models.feature_browser_models import (
    CorrelationMatrixResponse,
    FeatureDataTableResponse,
    FeatureDistributionResponse,
    FeatureOverviewResponse,
    FeatureQualityCheckRequest,
    FeatureQualityCheckResponse,
    ICDashboardResponse,
    ImportanceComparisonResponse,
    QualityScorecardResponse,
    RollingICResponse,
    SHAPSummaryResponse,
    VIFResponse,
    DriftMonitorResponse,
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


# ===== Phase 8 API =====
@router.get("/feature-browser/overview", response_model=FeatureOverviewResponse)
async def get_feature_overview(features_path: str = Query(..., description="特徵檔案路徑")):
    try:
        return feature_browser_service.get_overview(features_path)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/distribution/{feature_name}", response_model=FeatureDistributionResponse)
async def get_feature_distribution(
    feature_name: str,
    features_path: str = Query(..., description="特徵檔案路徑"),
    bins: int = Query(50, ge=10, le=200),
):
    try:
        return feature_browser_service.get_distribution(features_path, feature_name, bins)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/ic-dashboard", response_model=ICDashboardResponse)
async def get_ic_dashboard(
    features_path: str = Query(..., description="特徵檔案路徑"),
    top_k: int = Query(50, ge=1, le=300),
):
    try:
        return feature_browser_service.get_ic_dashboard(features_path, top_k=top_k)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/rolling-ic/{feature_name}", response_model=RollingICResponse)
async def get_rolling_ic(
    feature_name: str,
    features_path: str = Query(..., description="特徵檔案路徑"),
    window: int = Query(63, ge=10, le=500),
):
    try:
        return feature_browser_service.get_rolling_ic(features_path, feature_name, window=window)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/quality-scorecard", response_model=QualityScorecardResponse)
async def get_quality_scorecard(
    features_path: str = Query(..., description="特徵檔案路徑"),
    top_k: int = Query(200, ge=10, le=1000),
):
    try:
        return feature_browser_service.get_quality_scorecard(features_path, top_k=top_k)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/correlation-matrix", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix(
    features_path: str = Query(..., description="特徵檔案路徑"),
    method: str = Query("spearman", pattern="^(pearson|spearman|kendall)$"),
    max_features: int = Query(200, ge=2, le=500),
):
    try:
        return feature_browser_service.get_correlation_matrix(features_path, method=method, max_features=max_features)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/vif", response_model=VIFResponse)
async def get_vif(
    features_path: str = Query(..., description="特徵檔案路徑"),
    max_features: int = Query(200, ge=2, le=500),
):
    try:
        return feature_browser_service.get_vif(features_path, max_features=max_features)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/drift-monitor", response_model=DriftMonitorResponse)
async def get_drift_monitor(
    features_path: str = Query(..., description="特徵檔案路徑"),
    max_features: int = Query(200, ge=2, le=500),
):
    try:
        return feature_browser_service.get_drift_monitor(features_path, max_features=max_features)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/shap-summary", response_model=SHAPSummaryResponse)
async def get_shap_summary(
    features_path: str = Query(..., description="特徵檔案路徑"),
    top_k: int = Query(30, ge=1, le=300),
):
    try:
        return feature_browser_service.get_shap_summary(features_path, top_k=top_k)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/feature-browser/importance-comparison", response_model=ImportanceComparisonResponse)
async def get_importance_comparison(
    features_path: str = Query(..., description="特徵檔案路徑"),
    top_k: int = Query(30, ge=1, le=300),
):
    try:
        return feature_browser_service.get_importance_comparison(features_path, top_k=top_k)
    except Exception as exc:
        raise _http_error(exc)


# ===== Legacy API compatibility =====
@router.get("/features/catalog")
async def legacy_get_feature_catalog(features_path: str = Query(..., description="特徵檔案路徑")):
    try:
        return feature_browser_service.get_catalog(features_path)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/features/{feature_name}/distribution", response_model=FeatureDistributionResponse)
async def legacy_get_feature_distribution(
    feature_name: str,
    features_path: str = Query(..., description="特徵檔案路徑"),
    bins: int = Query(50, ge=10, le=200),
):
    try:
        return feature_browser_service.get_distribution(features_path, feature_name, bins)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/features/time-series")
async def legacy_get_feature_time_series(
    features_path: str = Query(..., description="特徵檔案路徑"),
    features: Optional[str] = Query(None, description="逗號分隔特徵名"),
    sample_rate: int = Query(1, ge=1, le=50),
):
    try:
        selected = [item.strip() for item in (features or "").split(",") if item.strip()]
        return feature_browser_service.get_time_series(features_path, selected, sample_rate)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/features/correlation")
async def legacy_get_feature_correlation(
    features_path: str = Query(..., description="特徵檔案路徑"),
    features: Optional[str] = Query(None, description="逗號分隔特徵名"),
    method: str = Query("spearman", pattern="^(pearson|spearman|kendall)$"),
    max_features: int = Query(100, ge=2, le=500),
):
    try:
        selected = [item.strip() for item in (features or "").split(",") if item.strip()]
        return feature_browser_service.get_correlation(features_path, selected, method, max_features)
    except Exception as exc:
        raise _http_error(exc)


@router.post("/features/quality-check", response_model=FeatureQualityCheckResponse)
async def legacy_quality_check_features(request: FeatureQualityCheckRequest):
    try:
        return feature_browser_service.run_quality_check(request.features_path, request.selected_features)
    except Exception as exc:
        raise _http_error(exc)


@router.get("/features/data-table", response_model=FeatureDataTableResponse)
async def legacy_get_feature_data_table(
    features_path: str = Query(..., description="特徵檔案路徑"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    columns: Optional[str] = Query(None, description="逗號分隔欄位"),
):
    try:
        selected_columns = [item.strip() for item in (columns or "").split(",") if item.strip()]
        return feature_browser_service.get_data_table(features_path, page, page_size, selected_columns)
    except Exception as exc:
        raise _http_error(exc)
