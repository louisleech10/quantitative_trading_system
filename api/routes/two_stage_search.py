from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from ..models.requests import SearchConfigRequest
from ..models.responses import TaskStartResponse, SearchResponse
from ..core.logging import get_logger

# 暫時定義 NegativeCaseRequest
class NegativeCaseRequest(BaseModel):
    """反例搜索請求模型"""
    search_config: SearchConfigRequest = Field(..., description="反例搜索配置")
    negative_ratio: float = Field(default=2.0, ge=1.0, le=5.0, description="反例與正例的比例")
    time_separation_days: int = Field(default=7, ge=1, le=30, description="時間分離天數")
    sampling_strategy: str = Field(default="time_separated", description="採樣策略")

# 暫時的 search_task_service 模擬實現
class MockSearchTaskService:
    def __init__(self):
        self.logger = get_logger("api.mock_search_task_service")
    
    async def execute_positive_search(self, request, symbols=None):
        from ..services.standalone_search_service import standalone_search_service
        return await standalone_search_service.execute_search(request, symbols)
    
    async def execute_negative_search(self, positive_task_id, request):
        import uuid
        return str(uuid.uuid4())
    
    def get_combined_results(self, positive_task_id, negative_task_id):
        return None

search_task_service = MockSearchTaskService()

router = APIRouter(prefix="/two-stage", tags=["Two-Stage Search"])
logger = get_logger("api.routes.two_stage_search")

@router.post("/positive", response_model=TaskStartResponse)
async def start_positive_search(
    request: SearchConfigRequest,
    background_tasks: BackgroundTasks,
    symbols: Optional[List[str]] = None
):
    """開始正例搜索（第一階段）"""
    try:
        task_id = await search_task_service.execute_positive_search(request, symbols)
        
        task_info = {
            "task_id": task_id,
            "status": "running", 
            "created_at": datetime.now().isoformat(),
            "name": request.name
        }
        
        return TaskStartResponse(success=True, data=task_info)
        
    except Exception as e:
        logger.error(f"Error starting positive search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/negative/{positive_task_id}", response_model=TaskStartResponse)
async def start_negative_search(
    positive_task_id: str,
    request: NegativeCaseRequest,
    background_tasks: BackgroundTasks
):
    """開始反例搜索（第二階段）"""
    try:
        negative_task_id = await search_task_service.execute_negative_search(
            positive_task_id, request
        )
        
        task_info = {
            "task_id": negative_task_id,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "positive_task_id": positive_task_id
        }
        
        return TaskStartResponse(success=True, data=task_info)
        
    except Exception as e:
        logger.error(f"Error starting negative search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/combined/{positive_task_id}/{negative_task_id}", response_model=SearchResponse)
async def get_combined_results(positive_task_id: str, negative_task_id: str):
    """獲取正反例合併結果"""
    try:
        combined_results = search_task_service.get_combined_results(
            positive_task_id, negative_task_id
        )
        
        if not combined_results:
            raise HTTPException(status_code=404, detail="No results found")
        
        return SearchResponse(success=True, data=combined_results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting combined results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))