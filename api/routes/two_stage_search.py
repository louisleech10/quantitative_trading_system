from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime

from ..models.requests import SearchConfigRequest, NegativeCaseRequest
from ..models.responses import TaskStartResponse, SearchResponse
from ..core.logging import get_logger
from ..services.search_task_service import search_task_service

router = APIRouter(prefix="/two-stage", tags=["Two-Stage Search"])
logger = get_logger("api.routes.two_stage_search")

@router.post("/positive", response_model=TaskStartResponse)
async def start_positive_search(
    request: SearchConfigRequest,
    background_tasks: BackgroundTasks,
    symbols: Optional[List[str]] = None
):
    """
    開始正例搜索（第一階段）
    
    返回task_id，用於查詢進度和結果
    """
    try:
        task_id = await search_task_service.execute_positive_search(request, symbols)
        
        # 構造任務信息返回
        task_info = {
            "task_id": task_id,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "name": request.name
        }
        
        return TaskStartResponse(
            success=True,
            data=task_info
        )
        
    except Exception as e:
        logger.error(f"Error starting positive search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/negative/{positive_task_id}", response_model=TaskStartResponse)
async def start_negative_search(
    positive_task_id: str,
    request: NegativeCaseRequest,
    background_tasks: BackgroundTasks
):
    """
    開始反例搜索（第二階段）
    
    基於指定的正例搜索結果生成反例
    """
    try:
        negative_task_id = await search_task_service.execute_negative_search(
            positive_task_id, request
        )
        
        # 構造任務信息返回
        task_info = {
            "task_id": negative_task_id,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "positive_task_id": positive_task_id
        }
        
        return TaskStartResponse(
            success=True,
            data=task_info
        )
        
    except Exception as e:
        logger.error(f"Error starting negative search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/combined/{positive_task_id}/{negative_task_id}", response_model=SearchResponse)
async def get_combined_results(
    positive_task_id: str,
    negative_task_id: str
):
    """
    獲取正反例合併結果
    
    返回完整的正反例數據集
    """
    try:
        combined_results = search_task_service.get_combined_results(
            positive_task_id, negative_task_id
        )
        
        if not combined_results:
            raise HTTPException(
                status_code=404, 
                detail="No results found for the specified task IDs"
            )
        
        return SearchResponse(
            success=True,
            data=combined_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting combined results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))