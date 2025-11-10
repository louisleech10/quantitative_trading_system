"""
案例相關API路由

提供案例導入、批量下載等API端點
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from typing import Optional

from ..models.case_models import (
    CaseImportRequest,
    CaseImportResponse,
    BatchDownloadRequest,
    DownloadProgress,
    DownloadResult,
    CaseListResponse
)
from ..services.case_import_service import get_case_import_service
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
    default_timeframe: Optional[str] = "1h",
    validate_only: bool = False,
    force_clear: bool = False
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

    try:
        # 讀取文件內容
        file_content = await file.read()

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
