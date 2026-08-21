"""
案例相關API路由

提供案例導入、批量下載等API端點
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Query
from typing import Optional

from ..models.case_models import (
    CaseImportRequest,
    CaseImportResponse,
    BatchDownloadRequest,
    DownloadProgress,
    DownloadResult,
    CaseListResponse
)
from ..services.case_import_service import (
    EventImportRejectedError,
    get_case_import_service,
    get_event_import_service,
)
from ..models.event_import_models import (
    EventAnalyzeRequest,
    EventAnalyzeResponse,
    EventImportDetailResponse,
    EventImportJsonRequest,
    EventImportListResponse,
    EventImportRejected,
    EventImportResponse,
)
from ..services.batch_download_service import get_batch_download_service
from ..utils.case_storage import get_case_storage_manager
from ..core.logging import get_logger

logger = get_logger("api.routes.case")

router = APIRouter(prefix="/api/v1", tags=["Case Management"])

# 獲取服務實例
case_import_service = get_case_import_service()
batch_download_service = get_batch_download_service()
case_storage = get_case_storage_manager()


@router.post("/case/import", response_model=CaseImportResponse)
async def import_cases_from_csv(
    file: UploadFile = File(...),
    default_timeframe: Optional[str] = Query("1h"),
    validate_only: bool = Query(False),
    force_clear: bool = Query(False)
):
    """
    上傳CSV/Excel文件並導入案例

    Args:
        file: CSV或Excel文件
        default_timeframe: 預設時間框架（CSV缺少時使用）
        validate_only: 僅驗證不導入
        force_clear: 導入前強制清空所有舊案例（需用戶確認）

    Returns:
        CaseImportResponse: 導入結果
            - 如果有現有案例且force_clear=False，返回need_confirmation=True
            - 如果force_clear=True，清空舊案例後導入

    Raises:
        HTTPException: 導入失敗
    """
    logger.info(
        f"Receiving case import request: {file.filename} "
        f"(default_timeframe={default_timeframe}, validate_only={validate_only}, force_clear={force_clear})"
    )

    # 檢查文件格式
    filename = file.filename
    if not filename.endswith(('.csv', '.xlsx', '.xls', '.txt')):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {filename}. "
                   f"Supported formats: .csv, .xlsx, .xls, .txt"
        )

    # 讀取文件內容
    file_content = await file.read()

    # GAP-3 B5.1 legacy adapter：新 schema 檔誤投舊端點 ⇒ 顯式 400（禁 silent coerce）；放在 try 外免被泛捕成 500
    _header = _csv_header(file_content, filename)
    if _header is not None and get_event_import_service().looks_new_schema(_header):
        raise HTTPException(status_code=400, detail=EventImportRejected(
            kind="new_schema_on_legacy_endpoint",
            message="偵測到 GAP-3 新 schema（event_id/t0/label…）；請改投 /api/v1/case/import-events，本端點只收舊三欄格式",
        ).model_dump())

    try:
        # 導入案例（支持force_clear參數）
        result = case_import_service.import_from_file(
            file_content=file_content,
            filename=filename,
            default_timeframe=default_timeframe,
            validate_only=validate_only,
            force_clear=force_clear
        )

        logger.info(
            f"Case import completed: {result.imported_cases}/{result.total_rows} imported, "
            f"{len(result.errors)} errors"
        )

        return result

    except ValueError as e:
        logger.error(f"Validation error during case import: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error during case import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


def _csv_header(content: bytes, filename: str) -> Optional[list]:
    """只讀 CSV 首列鍵名供 schema 偵測（不做任何契約檢查）。"""
    if not filename or not filename.lower().endswith((".csv", ".txt")):
        return None
    try:
        first = content.split(b"\n", 1)[0].decode("utf-8-sig", errors="replace")
    except Exception:  # noqa: BLE001
        return None
    return [c.strip().strip('"') for c in first.split(",")]


def _rejected(exc: EventImportRejectedError) -> HTTPException:
    return HTTPException(status_code=422 if exc.payload.kind == "contract_violation" else 400, detail=exc.payload.model_dump())


# ---------------------------------------------------------------------------
# GAP-3 Task B5.1 — 新 schema 事件匯入（驗證唯一實作在 momentum/；本層透傳）
# ---------------------------------------------------------------------------
@router.post("/case/import-events", response_model=EventImportResponse)
async def import_events_file(
    file: UploadFile = File(...),
    validate_only: bool = Query(False),
    verify_source_digest: bool = Query(False, description="以上傳內容 sha256 對證各列 source_file_digest"),
):
    """上傳 CSV/JSON（GAP-3 事件契約新 schema）。拒收 ⇒ 400（legacy／parse）或 422（契約違規，逐列 reason）。"""
    svc = get_event_import_service()
    content = await file.read()
    try:
        records = svc.parse_upload(content, file.filename or "")
        return svc.import_records(records, source_name=file.filename, upload_bytes=content, validate_only=validate_only,
                                  verify_source_digest=verify_source_digest)
    except EventImportRejectedError as exc:
        raise _rejected(exc)


@router.post("/case/import-events/json", response_model=EventImportResponse)
async def import_events_json(request: EventImportJsonRequest):
    """JSON 記錄列表匯入（同一 validator；`source_file_digest`＝canonical JSON sha256）。"""
    import json as _json

    svc = get_event_import_service()
    body = _json.dumps(request.records, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    try:
        return svc.import_records(request.records, source_name=request.source_name, upload_bytes=body,
                                  validate_only=request.validate_only, verify_source_digest=request.verify_source_digest)
    except EventImportRejectedError as exc:
        raise _rejected(exc)


@router.get("/case/events", response_model=EventImportListResponse)
async def list_event_imports():
    return get_event_import_service().list_imports()


@router.get("/case/events/{import_id}", response_model=EventImportDetailResponse)
async def get_event_import(import_id: str):
    out = get_event_import_service().get_import(import_id)
    if out is None:
        raise HTTPException(status_code=404, detail=f"event import {import_id!r} not found")
    return out


@router.post("/case/events/{import_id}/analyze", response_model=EventAnalyzeResponse)
async def analyze_event_import(import_id: str, request: EventAnalyzeRequest):
    """對一筆匯入跑對齊→去重→切分＋兩張表（真實 kline；統計全在 momentum）。缺 kline／契約違規 ⇒ 4xx 顯式。"""
    svc = get_event_import_service()
    try:
        out = svc.analyze(import_id, request)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail={"kind": "bars_unavailable", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"kind": "pipeline_rejected", "message": str(exc)})
    if out is None:
        raise HTTPException(status_code=404, detail=f"event import {import_id!r} not found")
    return out


@router.get("/case/list", response_model=CaseListResponse)
async def get_case_list():
    """
    獲取所有已導入案例列表

    Returns:
        CaseListResponse: 案例列表和統計信息
    """
    logger.info("Retrieving case list")

    try:
        result = case_storage.get_statistics()

        logger.info(f"Retrieved {result.total} cases")

        return result

    except Exception as e:
        logger.error(f"Failed to retrieve case list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cases: {str(e)}")


@router.get("/case/count")
async def get_case_count():
    """
    獲取當前案例數量

    Returns:
        dict: {"count": int} - 當前案例總數
    """
    logger.info("Retrieving case count")

    try:
        cases = case_storage.get_cases()
        count = len(cases)

        logger.info(f"Current case count: {count}")

        return {"count": count}

    except Exception as e:
        logger.error(f"Failed to retrieve case count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve case count: {str(e)}")


@router.post("/kline/batch-download")
async def start_batch_download(
    request: BatchDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    開始批量K線下載任務

    Args:
        request: 批量下載請求
        background_tasks: FastAPI背景任務

    Returns:
        dict: {"task_id": str, "message": str}
    """
    logger.info(
        f"Starting batch download: case_ids={request.case_ids}, "
        f"lookback={request.lookback_bars}, forward={request.forward_bars}"
    )

    try:
        # 創建下載任務
        task_id = batch_download_service.create_download_task(request)

        # 添加到背景任務
        background_tasks.add_task(
            batch_download_service.execute_batch_download,
            task_id,
            request
        )

        logger.info(f"Batch download task {task_id} created and queued")

        return {
            "task_id": task_id,
            "message": f"Batch download task created successfully"
        }

    except Exception as e:
        logger.error(f"Failed to start batch download: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start download: {str(e)}"
        )


@router.get("/kline/download-status/{task_id}", response_model=DownloadProgress)
async def get_download_status(task_id: str):
    """
    查詢批量下載任務進度

    Args:
        task_id: 任務ID

    Returns:
        DownloadProgress: 下載進度

    Raises:
        HTTPException: 任務不存在
    """
    logger.debug(f"Querying download status for task: {task_id}")

    progress = batch_download_service.get_progress(task_id)

    if not progress:
        logger.warning(f"Download task not found: {task_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Download task not found: {task_id}"
        )

    return progress


@router.delete("/case/clear-all")
async def clear_all_cases():
    """
    清空所有案例（謹慎使用）

    Returns:
        dict: {"success": bool, "cleared_count": int, "message": str}
    """
    logger.warning("Clearing all cases from storage")

    try:
        cleared_count = case_storage.clear_all()

        logger.info(f"All cases cleared successfully: {cleared_count} cases")

        return {
            "success": True,
            "cleared_count": cleared_count,
            "message": f"Successfully cleared {cleared_count} cases"
        }

    except Exception as e:
        logger.error(f"Failed to clear cases: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cases: {str(e)}"
        )
