from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from ..models.requests import SearchConfigRequest, FilterConditionRequest
from ..models.responses import TaskStartResponse, SearchResponse
from ..core.logging import get_logger

# 定義 NegativeCaseRequest
class NegativeCaseRequest(BaseModel):
    """反例搜索請求模型"""
    negative_conditions: List[dict] = Field(..., description="反例搜索條件")
    negative_ratio: float = Field(default=2.0, ge=1.0, le=5.0, description="反例與正例的比例")
    enable_time_separation: bool = Field(
        default=True,
        description="是否啟用時間分離（防止反例與正例時間過近，按Symbol獨立計算）"
    )
    time_separation_days: int = Field(
        default=3,
        ge=0,
        le=30,
        description="時間分離天數（0=關閉，按Symbol獨立過濾）"
    )
    sampling_strategy: str = Field(default="time_separated", description="採樣策略")

    class Config:
        json_schema_extra = {
            "example": {
                "negative_conditions": [
                    {
                        "condition_type": "price",
                        "parameter": "price_change",
                        "operator": "<=",
                        "value": -0.03,
                        "description": "價格下跌3%以上"
                    }
                ],
                "negative_ratio": 2.0,
                "enable_time_separation": True,
                "time_separation_days": 3,
                "sampling_strategy": "time_separated"
            }
        }

# MockSearchTaskService 定義
class MockSearchTaskService:
    def __init__(self):
        self.logger = get_logger("api.mock_search_task_service")
    
    async def execute_positive_search(self, request, symbols=None):
        from ..services.standalone_search_service import standalone_search_service
        return await standalone_search_service.execute_search(request, symbols)
    
    async def execute_negative_search(self, positive_task_id, request):
        """執行用戶自定義的反例搜索"""
        from ..services.standalone_search_service import standalone_search_service
        
        # 1. 檢查正例任務狀態
        positive_task = standalone_search_service.get_task_status(positive_task_id)
        if not positive_task:
            raise HTTPException(status_code=404, detail=f"Positive task {positive_task_id} not found")
        
        # 修復：使用屬性訪問而不是 .get() 方法
        if hasattr(positive_task, 'status'):
            task_status = positive_task.status
        elif isinstance(positive_task, dict):
            task_status = positive_task.get('status')
        else:
            task_status = getattr(positive_task, 'status', None)
            
        if task_status != 'completed':
            raise HTTPException(status_code=400, detail=f"Positive task {positive_task_id} not completed yet (status: {task_status})")
        
        # 2. 獲取正例結果
        try:
            positive_result = standalone_search_service.get_task_result(positive_task_id)
            if not positive_result:
                raise HTTPException(status_code=404, detail=f"No positive result data found for task {positive_task_id}")
        except Exception as e:
            self.logger.error(f"Error getting positive result: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get positive result: {str(e)}")
        
        # 3. 獲取正例搜索的timeframe（使用與SearchTaskService相同的邏輯）
        positive_timeframe = "12h"  # 默認值

        # 嘗試從SearchTaskService中獲取存儲的配置
        from ..services.search_task_service import search_task_service
        if positive_task_id in search_task_service.positive_configs:
            positive_timeframe = search_task_service.positive_configs[positive_task_id].timeframe
            self.logger.info(f"從SearchTaskService存儲的配置中獲取timeframe: {positive_timeframe}")
        else:
            # 備用方案：從搜索結果中獲取
            try:
                positive_result = standalone_search_service.get_task_result(positive_task_id)
                if positive_result and hasattr(positive_result, 'search_config') and positive_result.search_config:
                    if isinstance(positive_result.search_config, dict) and 'timeframe' in positive_result.search_config:
                        positive_timeframe = positive_result.search_config['timeframe']
                        self.logger.info(f"從正例搜索結果中獲取timeframe: {positive_timeframe}")
                    else:
                        self.logger.warning(f"正例搜索結果中的search_config格式不正確，使用默認值: {positive_timeframe}")
                else:
                    self.logger.warning(f"無法從正例搜索結果中獲取search_config，使用默認值: {positive_timeframe}")
            except Exception as e:
                self.logger.warning(f"無法獲取正例timeframe，使用默認值: {str(e)}")

        self.logger.info(f"反例搜索將使用timeframe: {positive_timeframe}")

        # 3. 獲取正例搜索的時間範圍
        positive_start_date = "2024-02-01"  # 默認值
        positive_end_date = "2025-05-31"    # 默認值

        # 嘗試從存儲的配置中獲取時間範圍
        if positive_task_id in search_task_service.positive_configs:
            positive_config = search_task_service.positive_configs[positive_task_id]
            positive_start_date = positive_config.start_date
            positive_end_date = positive_config.end_date
            self.logger.info(f"從SearchTaskService獲取時間範圍: {positive_start_date} 到 {positive_end_date}")
        else:
            # 備用方案：從搜索結果中獲取
            try:
                positive_result = standalone_search_service.get_task_result(positive_task_id)
                if positive_result and hasattr(positive_result, 'search_config') and positive_result.search_config:
                    if isinstance(positive_result.search_config, dict):
                        positive_start_date = positive_result.search_config.get('start_date', positive_start_date)
                        positive_end_date = positive_result.search_config.get('end_date', positive_end_date)
                        self.logger.info(f"從搜索結果獲取時間範圍: {positive_start_date} 到 {positive_end_date}")
            except Exception as e:
                self.logger.warning(f"無法獲取正例時間範圍，使用默認值: {str(e)}")

        # 3. 創建反例搜索配置
        negative_config = SearchConfigRequest(
            name=f"negative_search_for_{positive_task_id}",
            description="用戶自定義反例搜索",
            timeframe=positive_timeframe,  # 使用正例搜索相同的timeframe
            initial_conditions=[],
            advanced_conditions=[],
            start_date=positive_start_date,  # 使用正例搜索相同的開始日期
            end_date=positive_end_date      # 使用正例搜索相同的結束日期
        )
        
        # 4. 添加用戶自定義的反例條件
        for condition_data in request.negative_conditions:
            condition = FilterConditionRequest(
                condition_type=condition_data["condition_type"],
                parameter=condition_data["parameter"],
                operator=condition_data["operator"],
                value=condition_data["value"],
                description=condition_data.get("description", "用戶自定義反例條件")
            )
            negative_config.initial_conditions.append(condition)
        
        # 5. 執行反例搜索
        negative_task_id = await standalone_search_service.execute_search(negative_config, None)
        
        return negative_task_id
    
    def get_combined_results(self, positive_task_id, negative_task_id):
        from ..services.standalone_search_service import standalone_search_service
        
        # 獲取正例結果
        positive_result = standalone_search_service.get_task_result(positive_task_id)
        negative_result = standalone_search_service.get_task_result(negative_task_id)
        
        if not positive_result and not negative_result:
            return None
        
        # 新增：收集實際使用的交易對
        actual_symbols = set()
        if positive_result and positive_result.cases:
            for case in positive_result.cases:
                case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
                if 'symbol' in case_dict:
                    actual_symbols.add(case_dict['symbol'])
        
        if negative_result and negative_result.cases:
            for case in negative_result.cases:
                case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
                if 'symbol' in case_dict:
                    actual_symbols.add(case_dict['symbol'])
        
        # 轉換為列表，如果為空則使用預設值
        symbols_list = list(actual_symbols) if actual_symbols else ["BTCUSDT"]
            
        # 暫時簡單合併，後續會實現完整的正反例標記邏輯
        all_cases = []
        positive_count = 0
        negative_count = 0

        if positive_result and positive_result.cases:
            for case in positive_result.cases:
                # 添加正例標記
                case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
                case_dict['positive_case'] = True
                all_cases.append(case_dict)
                positive_count += 1

        if negative_result and negative_result.cases:
            for case in negative_result.cases:
                # 添加反例標記
                case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
                case_dict['positive_case'] = False
                all_cases.append(case_dict)
                negative_count += 1
            
        if not all_cases:
            return None
            
        # 返回完整的合併結果，包含所有必需字段
        from ..models.responses import SearchResultData
        return SearchResultData(
            cases=all_cases,
            total_cases=len(all_cases),
            search_config={"positive_negative_ratio": f"{positive_count}:{negative_count}"},
            execution_time=0.0,
            symbols_processed=symbols_list,
            positive_cases_count=positive_count,
            negative_cases_count=negative_count,
            # 添加缺少的必需字段
            summary={
                "total_cases": len(all_cases),
                "positive_cases": positive_count,
                "negative_cases": negative_count,
                "unique_symbols": len(symbols_list),
                "time_range": {
                    "start": "2024-02-01",
                    "end": "2025-05-31"
                },
                "market_phase_distribution": {}
            },
            sampling_quality={
                "time_separation_score": 0.8,
                "symbol_diversity_score": 0.1,
                "market_phase_balance": 0.7,
                "overall_quality_score": 0.75,
                "warnings": []
            },
            cache_used=False
        )

# 創建全局服務實例
from ..services.search_task_service import search_task_service

# 創建路由器
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
        # 簡化的請求確認log（生產環境可移除）
        logger.info(f"Positive search request: {request.name}, timeframe: {request.timeframe}, dates: {request.start_date} to {request.end_date}")
        # DEBUG LOG - 需要debug時取消註釋
        # logger.info(f"=== 接收到正例搜索請求 ===")
        # logger.info(f"Request name: {request.name}")
        # logger.info(f"Request timeframe: {request.timeframe}")
        # logger.info(f"Request start_date: {request.start_date}")
        # logger.info(f"Request end_date: {request.end_date}")
        # logger.info(f"Request time_range: {request.time_range}")
        # logger.info(f"Request symbols: {request.symbols}")
        # logger.info(f"Function symbols param: {symbols}")

        task_id = await search_task_service.execute_positive_search(request, symbols)
        
        task_info = {
            "task_id": task_id,
            "status": "running", 
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "name": request.name,
            "config_name": request.name
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
        # ===== DEBUG: 記錄接收到的請求參數 =====
        logger.info(f"🔍 接收到反例搜索請求:")
        logger.info(f"  - positive_task_id: {positive_task_id}")
        logger.info(f"  - negative_ratio: {request.negative_ratio}")
        logger.info(f"  - enable_time_separation: {request.enable_time_separation}")
        logger.info(f"  - time_separation_days: {request.time_separation_days}")
        logger.info(f"  - enable_random_sampling: {request.enable_random_sampling}")
        logger.info(f"  - sampling_strategy: {request.sampling_strategy}")

        negative_task_id = await search_task_service.execute_negative_search(
            positive_task_id, request
        )
        
        task_info = {
            "task_id": negative_task_id,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config_name": f"negative_search_for_{positive_task_id}",
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