"""Feature browser API routes.

Phase 8 的特徵瀏覽器頁面已併入 Feature Factory，僅保留跨 Symbol
Coverage Matrix 端點（真實 NaN 覆蓋率計算）。原本骨架期的 IC / SHAP /
模型重要度 / quality-scorecard 等端點為未串接的占位實作，已隨頁面下架移除。

ICPERF Task 0.6 (h) ⑦／③（L1c）：三個計算端點改背景任務（無請求逾時、無時間上限）——POST 回 `{task_id}`；
`GET /feature-browser/tasks/{id}` 回狀態、進度與摘要；`POST .../cancel` 協作取消；`GET .../result` 讀結果
（Group Feature 以 offset／limit 自同一任務之完整結果快照分頁，limit ≥ 1 無上界，不帶 limit ⇒ 全量匯出）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from api.core.background_jobs import BackgroundJobStore, JobResultUnavailable
from api.core.logging import get_logger
from api.models.feature_browser_models import (
    CoverageMatrixRequest,
    CoverageTaskCancelResponse,
    CoverageTaskCreatedResponse,
    CoverageTaskStatusResponse,
    GroupCoverageRequest,
    GroupFeatureCoverageRequest,
)
from api.services.feature_browser_service import PAGED_KINDS, feature_browser_service, page_group_feature_result


router = APIRouter(prefix="/api/v1", tags=["Feature Browser"])
logger = get_logger("api.routes.feature_browser")


def _store() -> BackgroundJobStore:
    """請求當下取服務之任務紀錄庫（測試以 monkeypatch 換 tmp 目錄之實例）。"""
    return feature_browser_service.job_store


def _not_found(task_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Coverage 任務不存在：{task_id}")


def _submit(submit, **kwargs: Any) -> Dict[str, str]:
    try:
        return {"task_id": submit(**kwargs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/feature-browser/coverage-matrix", response_model=CoverageTaskCreatedResponse)
async def post_coverage_matrix(request: CoverageMatrixRequest):
    return _submit(feature_browser_service.submit_coverage_matrix, symbols=request.symbols,
                   timeframe=request.timeframe, feature_names=request.feature_names,
                   feature_base_path=request.feature_base_path)


@router.post("/feature-browser/group-coverage", response_model=CoverageTaskCreatedResponse)
async def post_group_coverage(request: GroupCoverageRequest):
    return _submit(feature_browser_service.submit_group_coverage, symbols=request.symbols,
                   timeframe=request.timeframe, feature_base_path=request.feature_base_path)


@router.post("/feature-browser/group-feature-coverage", response_model=CoverageTaskCreatedResponse)
async def post_group_feature_coverage(request: GroupFeatureCoverageRequest):
    return _submit(feature_browser_service.submit_group_feature_coverage, symbols=request.symbols,
                   timeframe=request.timeframe, group_name=request.group_name,
                   feature_base_path=request.feature_base_path)


@router.get("/feature-browser/tasks/{task_id}", response_model=CoverageTaskStatusResponse)
async def get_coverage_task(task_id: str):
    record = _store().get(task_id)
    if record is None:
        raise _not_found(task_id)
    return {key: record.get(key) for key in CoverageTaskStatusResponse.model_fields}


@router.post("/feature-browser/tasks/{task_id}/cancel", response_model=CoverageTaskCancelResponse)
async def cancel_coverage_task(task_id: str):
    try:
        outcome = _store().cancel(task_id)
    except KeyError as exc:
        raise _not_found(task_id) from exc
    return {"task_id": task_id, "cancel": outcome}


@router.get("/feature-browser/tasks/{task_id}/result")
async def get_coverage_task_result(
    task_id: str,
    offset: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1),
):
    store = _store()
    record = store.get(task_id)
    if record is None:
        raise _not_found(task_id)
    try:
        result = store.read_result(task_id)
    except JobResultUnavailable as exc:
        raise HTTPException(status_code=409, detail=f"Coverage 任務 {task_id} 狀態為 {record['state']}，尚無結果") from exc
    except KeyError as exc:
        raise _not_found(task_id) from exc
    if record.get("kind") in PAGED_KINDS:
        return page_group_feature_result(result, offset, limit)
    if offset != 0 or limit is not None:
        raise HTTPException(status_code=400, detail=f"任務種類 {record.get('kind')} 之結果不分頁")
    return result
