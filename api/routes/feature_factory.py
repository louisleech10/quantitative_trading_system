"""
Feature Factory API Routes
"""

import asyncio
from functools import partial
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from api.core.logging import get_logger
from api.models.feature_factory_models import (
    BatchGenerateRequest,
    BatchQualityResponse,
    BatchTaskStatusResponse,
    BatchToggleRequest,
    FeatureGenerateRequest,
    FeaturePreviewRequest,
    FeaturePreviewResponse,
    FeatureTaskStatusResponse,
    NL2ConfigRequest,
    NL2ConfigResponse,
    RegisterPathRequest,
    RegisterPathResponse,
)
from api.services.feature_factory_batch_service import (
    FeatureFactoryBatchService,
    get_feature_factory_batch_service,
)
from api.services.feature_factory_service import feature_factory_service


router = APIRouter(prefix="/api/v1/features", tags=["Feature Factory"])
logger = get_logger("api.routes.feature_factory")


def get_batch_service() -> FeatureFactoryBatchService:
    """DI provider for FeatureFactoryBatchService singleton.

    Defined in route module to avoid importing api.main at module import time,
    which can cause circular imports during test collection.
    """
    return get_feature_factory_batch_service()


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


@router.get("/schema")
async def get_schema():
    """Get complete schema with all available indicators, descriptions, and current enabled state."""
    try:
        return feature_factory_service.get_schema()
    except Exception as exc:
        logger.error("Failed to get schema: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/config/batch-toggle")
async def batch_toggle(request: BatchToggleRequest):
    """Batch toggle indicator/aggregator/operator enabled states."""
    try:
        return feature_factory_service.batch_toggle(
            [t.model_dump() for t in request.toggles]
        )
    except Exception as exc:
        logger.error("Failed to batch toggle: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/config/presets/{preset_name}")
async def apply_preset(preset_name: str):
    """Apply a named preset and return the resulting config + preview."""
    try:
        return feature_factory_service.apply_preset_config(preset_name)
    except ValueError as exc:
        logger.error("Invalid preset name: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to apply preset: %s", exc, exc_info=True)
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


@router.post("/batch")
async def start_batch_generation(
    request: BatchGenerateRequest,
    service: FeatureFactoryBatchService = Depends(get_batch_service),
):
    """啟動批次特徵生成。"""
    try:
        task_id = await service.start_batch(request)
        return {
            "task_id": task_id,
            "status": "pending",
            "total": len(request.symbols),
        }
    except ValueError as exc:
        logger.error("Invalid batch request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start batch generation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/batch/{task_id}", response_model=BatchTaskStatusResponse)
async def get_batch_status(
    task_id: str,
    service: FeatureFactoryBatchService = Depends(get_batch_service),
):
    """查詢批次任務狀態。"""
    try:
        status = service.get_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get batch task status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/batch/{task_id}/quality", response_model=BatchQualityResponse)
async def get_batch_quality(
    task_id: str,
    service: FeatureFactoryBatchService = Depends(get_batch_service),
):
    """取得批次任務中所有成功標的的品質彙整摘要。"""
    try:
        result = await service.get_batch_quality_summary(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Batch task not found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get batch quality summary: %s", exc, exc_info=True)
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


@router.get("/export/{task_id}/csv")
async def export_features_csv(
    task_id: str,
    columns: Optional[str] = Query(None, description="逗號分隔的欄位名，空=全部"),
    max_rows: Optional[int] = Query(None, ge=0, description="最大行數，空=全部"),
    include_metadata_header: bool = Query(True, description="CSV 前方加入 #metadata 註解行"),
    include_datasource: bool = Query(False, description="在 CSV 前方加入原始數據源欄位（open/high/low/close/volume 等）"),
):
    """串流匯出特徵數據為 CSV。"""
    try:
        selected_columns = [column.strip() for column in columns.split(",") if column.strip()] if columns else None
        export_kwargs = {
            "task_id": task_id,
            "columns": selected_columns,
            "max_rows": max_rows,
            "include_metadata_header": include_metadata_header,
        }
        # Backward-compat: only pass include_datasource when explicitly requested.
        # Older tests/mocks may not accept this keyword argument.
        if include_datasource:
            export_kwargs["include_datasource"] = True
        loop = asyncio.get_running_loop()
        payload = await loop.run_in_executor(
            None,
            partial(
                feature_factory_service.export_csv_stream,
                **export_kwargs,
            ),
        )
        headers = {
            "Content-Disposition": f"attachment; filename={payload['filename']}",
            "X-Export-Task-Id": task_id,
            "X-Export-Feature-Count": str(payload["feature_count"]),
            "X-Export-Row-Count": str(payload["row_count"]),
        }
        return StreamingResponse(
            payload["generator"],
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to export CSV: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/{task_id}/json")
async def export_features_json(
    task_id: str,
    include_sample_data: bool = Query(True, description="包含前 N 行樣本數據"),
    sample_rows: int = Query(5, ge=1, le=100, description="樣本行數"),
    include_statistics: bool = Query(True, description="包含每欄統計摘要"),
    include_correlation_top_k: int = Query(10, ge=0, le=50, description="Top-K 高相關特徵對"),
):
    """匯出 AI Agent / LLM 可消費的結構化 JSON。"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                feature_factory_service.export_json_report,
                task_id=task_id,
                include_sample_data=include_sample_data,
                sample_rows=sample_rows,
                include_statistics=include_statistics,
                include_correlation_top_k=include_correlation_top_k,
            ),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to export JSON: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/{task_id}/markdown")
async def export_features_markdown(
    task_id: str,
    max_token_budget: int = Query(4000, ge=500, le=32000, description="Token 預算上限"),
    sections: Optional[str] = Query(None, description="逗號分隔的 section 名，空=全部"),
    language: str = Query("zh-TW", description="報告語言"),
):
    """匯出 LLM context window 友善的 Markdown 報告。"""
    try:
        selected_sections = [section.strip() for section in sections.split(",") if section.strip()] if sections else None
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(
            None,
            partial(
                feature_factory_service.export_markdown_report,
                task_id=task_id,
                max_token_budget=max_token_budget,
                sections=selected_sections,
                language=language,
            ),
        )
        headers = {
            "Content-Disposition": f"attachment; filename=feature_report_{task_id}.md",
        }
        return Response(content=content, media_type="text/markdown; charset=utf-8", headers=headers)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to export Markdown: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/browse/register", response_model=RegisterPathResponse)
async def register_hdf5_for_browse(
    request: RegisterPathRequest,
):
    """將批次任務的 HDF5 結果登錄為可瀏覽虛擬任務，回傳 FeatureExplorer 使用的 task_id。"""
    try:
        task_id = feature_factory_service.register_hdf5_for_browse(
            request.symbol, request.timeframe, request.hdf5_path
        )
        return RegisterPathResponse(task_id=task_id, symbol=request.symbol, timeframe=request.timeframe)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to register HDF5 for browse: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/browse/{task_id}/features")
async def browse_features(
    task_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100000),
    cursor: Optional[str] = Query(None, description="游標分頁：前一頁最後一筆 name"),
    sort_by: Optional[str] = Query(None, description="排序欄位：nan_ratio, std, skewness, kurtosis, mean, name"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    category: Optional[str] = Query(None, description="篩選類別"),
    level: Optional[str] = Query(None, pattern="^(L1|L2|L3)$"),
    search: Optional[str] = Query(None, description="特徵名模糊搜尋"),
    detail_level: str = Query("full", pattern="^(full|table)$", description="回傳欄位等級：full 或 table"),
):
    """分頁瀏覽特徵列表 + 統計摘要。"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                feature_factory_service.browse_features,
                task_id=task_id,
                offset=offset,
                limit=limit,
                cursor=cursor,
                sort_by=sort_by,
                sort_order=sort_order,
                category=category,
                level=level,
                search=search,
                detail_level=detail_level,
            ),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to browse features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/browse/{task_id}/data")
async def browse_feature_data(
    task_id: str,
    features: str = Query(..., description="逗號分隔的特徵名（最多 20）"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
):
    """取得指定特徵的原始數據（時間序列）。"""
    try:
        selected_features = [feature.strip() for feature in features.split(",") if feature.strip()]
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                feature_factory_service.browse_feature_data,
                task_id=task_id,
                features=selected_features,
                offset=offset,
                limit=limit,
            ),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to browse feature data: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/browse/{task_id}/correlation")
async def browse_correlation(
    task_id: str,
    features: str = Query(..., description="逗號分隔的特徵名（最多 50）"),
    method: str = Query("pearson", pattern="^(pearson|spearman|kendall)$"),
):
    """取得指定特徵集合的相關矩陣。"""
    try:
        selected_features = [feature.strip() for feature in features.split(",") if feature.strip()]
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                feature_factory_service.browse_correlation,
                task_id=task_id,
                features=selected_features,
                method=method,
            ),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to browse correlation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/browse/{task_id}/vif")
async def browse_vif(
    task_id: str,
    features: str = Query(..., description="逗號分隔的特徵名（最多 50）"),
):
    """取得指定特徵集合的 VIF（方差膨脹因子）——共線性診斷。"""
    try:
        selected_features = [feature.strip() for feature in features.split(",") if feature.strip()]
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                feature_factory_service.browse_vif,
                task_id=task_id,
                features=selected_features,
            ),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to browse VIF: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/browse/{task_id}/distribution")
async def browse_distribution(
    task_id: str,
    feature: str = Query(..., description="單一特徵名"),
    n_bins: int = Query(50, ge=10, le=200),
):
    """取得單一特徵的分佈直方圖數據。"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(feature_factory_service.browse_distribution, task_id=task_id, feature=feature, n_bins=n_bins),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to browse distribution: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/browse/{task_id}/nan-pattern")
async def browse_nan_pattern(
    task_id: str,
    sample_features: int = Query(50, ge=10, le=200, description="取樣特徵數"),
):
    """取得 NaN 分佈模式矩陣（missingno 風格）。"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(feature_factory_service.browse_nan_pattern, task_id=task_id, sample_features=sample_features),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to browse NaN pattern: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/browse/{task_id}/summary")
async def browse_summary(task_id: str):
    """取得整體摘要 Dashboard 數據。"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(feature_factory_service.browse_summary, task_id=task_id),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to browse summary: %s", exc, exc_info=True)
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
