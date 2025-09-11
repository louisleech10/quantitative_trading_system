"""
搜索任務服務 - 處理正反例兩階段搜索邏輯
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..core.config import settings
from ..core.logging import get_logger
from ..models.requests import SearchConfigRequest, NegativeCaseRequest
from ..models.responses import SearchResultData, CaseData
from ..utils.exceptions import SearchExecutionException
from .standalone_search_service import standalone_search_service

class SearchTaskService:
    """兩階段搜索任務服務：正例搜索 → 反例搜索"""
    
    def __init__(self):
        self.logger = get_logger("api.search_task_service")
        self.positive_results: Dict[str, List[CaseData]] = {}  # 儲存正例結果
        self.negative_results: Dict[str, List[CaseData]] = {}  # 儲存反例結果
        
    async def execute_positive_search(self, request: SearchConfigRequest, 
                                    symbols: Optional[List[str]] = None) -> str:
        """
        執行正例搜索（第一階段）
        返回 task_id，用於後續查詢結果和執行反例搜索
        """
        self.logger.info(f"Starting positive search: {request.name}")
        
        # 執行搜索
        task_id = await standalone_search_service.execute_search(request, symbols)
        
        # 監控搜索完成並儲存結果
        asyncio.create_task(self._monitor_positive_search(task_id))
        
        return task_id
    
    async def _monitor_positive_search(self, task_id: str):
        """監控正例搜索完成並儲存結果"""
        max_wait_time = 300  # 5分鐘超時
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < max_wait_time:
            task_info = standalone_search_service.get_task_status(task_id)
            
            if not task_info:
                self.logger.error(f"Task {task_id} not found")
                break
                
            if task_info.status.value == "completed":
                # 獲取結果並儲存
                result_data = standalone_search_service.get_task_result(task_id)
                if result_data and result_data.cases:
                    self.positive_results[task_id] = result_data.cases
                    self.logger.info(f"Positive search {task_id} completed with {len(result_data.cases)} cases")
                break
                
            elif task_info.status.value in ["failed", "cancelled"]:
                self.logger.warning(f"Positive search {task_id} ended with status: {task_info.status.value}")
                break
                
            await asyncio.sleep(2)  # 每2秒檢查一次
    
    async def execute_negative_search(self, positive_task_id: str, 
                                    negative_request: NegativeCaseRequest) -> str:
        """
        執行反例搜索（第二階段）
        基於正例搜索結果進行反例採樣
        """
        # 檢查正例結果是否存在
        if positive_task_id not in self.positive_results:
            raise SearchExecutionException(f"Positive search results not found for task {positive_task_id}")
        
        positive_cases = self.positive_results[positive_task_id]
        if not positive_cases:
            raise SearchExecutionException("No positive cases found to generate negative examples")
        
        self.logger.info(f"Starting negative search based on {len(positive_cases)} positive cases")
        
        # 生成新的task_id給反例搜索
        negative_task_id = str(uuid.uuid4())
        
        # 異步執行反例搜索
        asyncio.create_task(self._run_negative_search(
            negative_task_id, positive_cases, negative_request
        ))
        
        return negative_task_id
    
    async def _run_negative_search(self, task_id: str, positive_cases: List[CaseData],
                                 request: NegativeCaseRequest):
        """執行反例搜索邏輯"""
        try:
            # 更新任務狀態為執行中
            standalone_search_service.task_manager.create_task(f"negative_search_{task_id}")
            standalone_search_service.task_manager.update_task_status(
                task_id, "running"
            )
            
            # 提取正例的symbol列表
            positive_symbols = list(set(case.symbol for case in positive_cases))
            
            # 根據策略生成反例
            negative_cases = await self._generate_negative_cases(
                positive_cases, positive_symbols, request
            )
            
            if negative_cases:
                self.negative_results[task_id] = negative_cases
                
                # 更新任務為完成
                result_data = SearchResultData(
                    cases=negative_cases,
                    total_cases=len(negative_cases),
                    search_config=request.search_config.__dict__,
                    execution_time=5.0,  # 暫時固定值
                    symbols_processed=positive_symbols
                )
                
                standalone_search_service.task_manager.update_task_status(
                    task_id, "completed", result=result_data
                )
                
                self.logger.info(f"Negative search completed with {len(negative_cases)} cases")
            else:
                standalone_search_service.task_manager.update_task_status(
                    task_id, "failed", error_message="No negative cases generated"
                )
                
        except Exception as e:
            self.logger.error(f"Negative search failed: {str(e)}")
            standalone_search_service.task_manager.update_task_status(
                task_id, "failed", error_message=str(e)
            )
    
    async def _generate_negative_cases(self, positive_cases: List[CaseData],
                                     symbols: List[str],
                                     request: NegativeCaseRequest) -> List[CaseData]:
        """生成反例案例"""
        negative_cases = []
        target_count = int(len(positive_cases) * request.negative_ratio)
        
        # 提取正例的時間點
        positive_timestamps = [case.timestamp for case in positive_cases]
        
        # 按照時間分離策略選擇反例時間點
        negative_timestamps = self._select_negative_timestamps(
            positive_timestamps, symbols, request.time_separation_days, target_count
        )
        
        # 為每個反例時間點生成案例數據
        for timestamp in negative_timestamps:
            # 這裡需要調用數據加載器獲取該時間點的數據
            # 暫時生成示例數據
            negative_case = CaseData(
                symbol=symbols[len(negative_cases) % len(symbols)],
                timestamp=timestamp,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000000,
                case_type=0,  # 0 = negative case
                # 其他欄位...
            )
            negative_cases.append(negative_case)
            
            if len(negative_cases) >= target_count:
                break
        
        return negative_cases
    
    def _select_negative_timestamps(self, positive_timestamps: List[str],
                                   symbols: List[str], separation_days: int,
                                   target_count: int) -> List[str]:
        """選擇反例時間點，確保與正例時間充分分離"""
        negative_timestamps = []
        separation_delta = timedelta(days=separation_days)
        
        # 將正例時間轉換為datetime對象
        positive_times = [datetime.fromisoformat(ts.replace('Z', '+00:00')) 
                         if 'Z' in ts else datetime.fromisoformat(ts) 
                         for ts in positive_timestamps]
        
        # 生成候選時間點（在正例時間之前和之後，但保持分離）
        for pos_time in positive_times:
            # 在該正例時間之前和之後生成候選點
            candidate_before = pos_time - separation_delta
            candidate_after = pos_time + separation_delta
            
            # 檢查是否與其他正例時間衝突
            if not any(abs((candidate_before - pt).days) < separation_days 
                      for pt in positive_times):
                negative_timestamps.append(candidate_before.isoformat())
            
            if not any(abs((candidate_after - pt).days) < separation_days 
                      for pt in positive_times):
                negative_timestamps.append(candidate_after.isoformat())
            
            if len(negative_timestamps) >= target_count:
                break
        
        return negative_timestamps[:target_count]
    
    def get_combined_results(self, positive_task_id: str, 
                           negative_task_id: str) -> Optional[SearchResultData]:
        """獲取正反例合併結果"""
        positive_cases = self.positive_results.get(positive_task_id, [])
        negative_cases = self.negative_results.get(negative_task_id, [])
        
        if not positive_cases and not negative_cases:
            return None
        
        all_cases = positive_cases + negative_cases
        symbols_processed = list(set(case.symbol for case in all_cases))
        
        return SearchResultData(
            cases=all_cases,
            total_cases=len(all_cases),
            search_config={},  # 需要合併正反例配置
            execution_time=10.0,  # 需要計算實際時間
            symbols_processed=symbols_processed,
            positive_cases_count=len(positive_cases),
            negative_cases_count=len(negative_cases)
        )

# 創建全局服務實例
search_task_service = SearchTaskService()

# 新增文件: api/models/requests.py (添加反例搜索請求模型)

class NegativeCaseRequest(BaseModel):
    """反例搜索請求模型"""
    search_config: SearchConfigRequest = Field(..., description="反例搜索配置")
    negative_ratio: float = Field(default=2.0, ge=1.0, le=5.0, description="反例與正例的比例")
    time_separation_days: int = Field(default=7, ge=1, le=30, description="時間分離天數")
    sampling_strategy: str = Field(default="time_separated", description="採樣策略")
    
    class Config:
        json_schema_extra = {
            "example": {
                "search_config": {
                    "name": "negative_example_search",
                    "timeframe": "12h",
                    "initial_conditions": []
                },
                "negative_ratio": 2.0,
                "time_separation_days": 7,
                "sampling_strategy": "time_separated"
            }
        }

# 新增 API 路由: api/routes/two_stage_search.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from ..models.requests import SearchConfigRequest, NegativeCaseRequest
from ..models.responses import TaskStartResponse, SearchResponse
from ..services.search_task_service import search_task_service
from ..core.logging import get_logger

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
        
        # 獲取任務信息
        task_info = search_task_service.get_task_status(task_id)
        
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