"""Export routes for Phase 7 (M8)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from api.models.export_models import ExportFormatEnum, ExportPreviewResponse, ExportScopeEnum
from api.services.export_service import get_export_service


router = APIRouter(prefix="/api/v1/export", tags=["Export"])


def _remove_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


@router.get("/{model_task_id}")
async def export_file(
    model_task_id: str,
    format: ExportFormatEnum = Query(...),
    scope: ExportScopeEnum = Query(default=ExportScopeEnum.full),
):
    try:
        content_bytes, file_name, media_type = get_export_service().export_file(
            model_task_id=model_task_id,
            format=format,
            scope=scope,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {error}")

    suffix = Path(file_name).suffix or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content_bytes)
        temp_path = tmp.name

    return FileResponse(
        path=temp_path,
        media_type=media_type,
        filename=file_name,
        background=BackgroundTask(_remove_temp_file, temp_path),
    )


@router.get("/{model_task_id}/preview", response_model=ExportPreviewResponse)
async def preview_export(
    model_task_id: str,
    format: ExportFormatEnum = Query(...),
    scope: ExportScopeEnum = Query(default=ExportScopeEnum.full),
):
    try:
        content, file_name = get_export_service().preview(
            model_task_id=model_task_id,
            format=format,
            scope=scope,
        )
        return ExportPreviewResponse(
            model_task_id=model_task_id,
            format=format,
            scope=scope,
            file_name=file_name,
            content=content,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"預覽失敗: {error}")
