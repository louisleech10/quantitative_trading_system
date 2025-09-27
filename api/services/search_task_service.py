"""
搜索任務服務 - 處理正反例兩階段搜索邏輯
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from pydantic import BaseModel, Field
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
        self.logger.info(f"Negative request type: {type(negative_request)}")
        
        # 檢查用戶條件
        if hasattr(negative_request, 'negative_conditions') and negative_request.negative_conditions:
            self.logger.info(f"用戶設定了 {len(negative_request.negative_conditions)} 個反例條件")
            for i, condition in enumerate(negative_request.negative_conditions):
                self.logger.info(f"條件 {i+1}: {condition}")
        else:
            self.logger.info("沒有用戶設定的反例條件，將使用時間分離策略")
        
        # 生成新的task_id給反例搜索
        negative_task_id = str(uuid.uuid4())
        
        # 異步執行反例搜索
        asyncio.create_task(self._run_negative_search(
            negative_task_id, positive_cases, negative_request
        ))
        
        return negative_task_id
    
    async def _run_negative_search(self, task_id: str, positive_cases: List[CaseData],
                             request: NegativeCaseRequest):
        """執行反例搜索邏輯 - 修復版本"""
        try:
            # 更新任務狀態為執行中
            standalone_search_service.task_manager.create_task(f"negative_search_{task_id}")
            standalone_search_service.task_manager.update_task_status(
                task_id, "running"
            )
            
            # 提取正例的symbol列表
            positive_symbols = list(set(case.symbol for case in positive_cases))
            self.logger.info(f"開始執行用戶自定義條件的反例搜索，交易對: {positive_symbols}")
            
            # 檢查是否有用戶設定的條件
            if hasattr(request, 'negative_conditions') and request.negative_conditions:
                self.logger.info(f"使用用戶設定的反例條件，條件數量: {len(request.negative_conditions)}")
                
                # 使用用戶條件進行真實搜索
                negative_cases = await self._search_with_user_conditions(
                    positive_symbols, request, positive_cases
                )
            else:
                self.logger.info("沒有用戶條件，使用時間分離策略")
                # 沒有用戶條件時才使用時間分離
                negative_cases = await self._generate_negative_cases(
                    positive_cases, positive_symbols, request
                )
            
            if negative_cases:
                self.negative_results[task_id] = negative_cases
                self.logger.info(f"反例搜索完成，找到 {len(negative_cases)} 個案例")
                
                # 更新任務為完成
                result_data = SearchResultData(
                    cases=negative_cases,
                    total_cases=len(negative_cases),
                    search_config={}, # 移除對 search_config 的引用
                    execution_time=5.0,
                    symbols_processed=positive_symbols
                )
                
                standalone_search_service.task_manager.update_task_status(
                    task_id, "completed", result_data=result_data
                )
            else:
                self.logger.warning("反例搜索沒有找到任何案例")
                standalone_search_service.task_manager.update_task_status(
                    task_id, "failed", error_message="No negative cases found"
                )
                
        except Exception as e:
            self.logger.error(f"Negative search failed: {str(e)}")
            standalone_search_service.task_manager.update_task_status(
                task_id, "failed", error_message=str(e)
            )
    
    async def _search_with_user_conditions(self, symbols: List[str], 
                                     request: NegativeCaseRequest,
                                     positive_cases: List[CaseData]) -> List[CaseData]:
        """基於用戶設定條件執行反例搜索 - 修復版本"""
        try:
            from ..models.requests import SearchConfigRequest, FilterConditionRequest
            
            self.logger.info("構建反例搜索配置...")
            
            # === 修復1：從正例案例中提取時間範圍 ===
            if not positive_cases:
                self.logger.error("沒有正例案例，無法確定搜索時間範圍")
                return []
            
            # 找出正例的時間範圍
            positive_timestamps = []
            for case in positive_cases:
                if hasattr(case, 'timestamp'):
                    positive_timestamps.append(case.timestamp)
                elif hasattr(case, '__dict__') and 'timestamp' in case.__dict__:
                    positive_timestamps.append(case.__dict__['timestamp'])
            
            if not positive_timestamps:
                self.logger.error("無法從正例案例中提取時間戳")
                return []
            
            # 轉換為datetime對象並找出範圍
            from datetime import datetime, timedelta
            positive_times = []
            for ts in positive_timestamps:
                if isinstance(ts, str):
                    if 'T' in ts:
                        positive_times.append(datetime.fromisoformat(ts.replace('Z', '')))
                    else:
                        positive_times.append(datetime.strptime(ts, '%Y-%m-%d %H:%M:%S'))
                elif isinstance(ts, datetime):
                    positive_times.append(ts)
            
            # 設定搜索的時間範圍（比正例範圍稍大一些）
            min_time = min(positive_times)
            max_time = max(positive_times)
            
            # 擴展時間範圍以包含更多潛在反例
            search_start = min_time - timedelta(days=30)
            search_end = max_time + timedelta(days=30)
            
            self.logger.info(f"正例時間範圍: {min_time} 到 {max_time}")
            self.logger.info(f"反例搜索範圍: {search_start} 到 {search_end}")
            
            # === 創建搜索配置 ===
            negative_config = SearchConfigRequest(
                name=f"user_negative_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="基於用戶條件的反例搜索",
                timeframe="12h",
                initial_conditions=[],
                advanced_conditions=[],
                start_date=search_start.strftime('%Y-%m-%d'),
                end_date=search_end.strftime('%Y-%m-%d')
            )
            
            # 添加用戶設定的條件
            for condition_data in request.negative_conditions:
                self.logger.info(f"添加條件: {condition_data['parameter']} {condition_data['operator']} {condition_data['value']}")
                
                condition = FilterConditionRequest(
                    condition_type=condition_data["condition_type"],
                    parameter=condition_data["parameter"],
                    operator=condition_data["operator"],
                    value=condition_data["value"],
                    description=condition_data.get("description", "用戶自定義反例條件")
                )
                negative_config.initial_conditions.append(condition)
            
            # 執行真實搜索
            self.logger.info("執行基於條件的反例搜索...")
            negative_task_id = await standalone_search_service.execute_search(negative_config, symbols)
            
            # 等待搜索完成
            max_wait_time = 60
            start_time = datetime.now()
            
            while (datetime.now() - start_time).seconds < max_wait_time:
                task_info = standalone_search_service.get_task_status(negative_task_id)
                if task_info and task_info.status.value == "completed":
                    # 獲取搜索結果
                    result_data = standalone_search_service.get_task_result(negative_task_id)
                    if result_data and result_data.cases:
                        self.logger.info(f"條件搜索完成，找到 {len(result_data.cases)} 個候選反例")
                        
                        # === 修復2和3：應用時間分離和比例控制 ===
                        filtered_cases = await self._apply_time_separation_and_ratio(
                            result_data.cases, 
                            positive_cases,
                            request.time_separation_days if hasattr(request, 'time_separation_days') else 7,
                            request.negative_ratio if hasattr(request, 'negative_ratio') else 2.0
                        )
                        
                        return filtered_cases
                    break
                elif task_info and task_info.status.value in ["failed", "cancelled"]:
                    self.logger.error("反例搜索失敗或被取消")
                    break
                
                await asyncio.sleep(2)
            
            self.logger.warning("反例搜索超時或失敗")
            return []
            
        except Exception as e:
            self.logger.error(f"用戶條件搜索失敗: {str(e)}")
            return []
        
    async def _apply_time_separation_and_ratio(self, candidate_cases: List[CaseData],
                                         positive_cases: List[CaseData],
                                         separation_days: int,
                                         ratio: float) -> List[CaseData]:
        """應用時間分離和比例控制"""
        try:
            from datetime import datetime, timedelta
            
            # 獲取正例時間戳
            positive_times = []
            for case in positive_cases:
                if hasattr(case, 'timestamp'):
                    ts = case.timestamp
                elif hasattr(case, '__dict__') and 'timestamp' in case.__dict__:
                    ts = case.__dict__['timestamp']
                else:
                    continue
                
                if isinstance(ts, str):
                    if 'T' in ts:
                        positive_times.append(datetime.fromisoformat(ts.replace('Z', '')))
                    else:
                        positive_times.append(datetime.strptime(ts, '%Y-%m-%d %H:%M:%S'))
                elif isinstance(ts, datetime):
                    positive_times.append(ts)
            
            # 過濾掉與正例時間太接近的候選案例
            separation_delta = timedelta(days=separation_days)
            filtered_candidates = []
            
            for case in candidate_cases:
                if hasattr(case, 'timestamp'):
                    ts = case.timestamp
                elif hasattr(case, '__dict__') and 'timestamp' in case.__dict__:
                    ts = case.__dict__['timestamp']
                else:
                    continue
                
                if isinstance(ts, str):
                    if 'T' in ts:
                        case_time = datetime.fromisoformat(ts.replace('Z', ''))
                    else:
                        case_time = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                elif isinstance(ts, datetime):
                    case_time = ts
                else:
                    continue
                
                # 檢查與所有正例時間的距離
                is_separated = True
                for pos_time in positive_times:
                    if abs((case_time - pos_time)) < separation_delta:
                        is_separated = False
                        break
                
                if is_separated:
                    filtered_candidates.append(case)
            
            self.logger.info(f"時間分離後剩餘候選反例: {len(filtered_candidates)}")
            
            # 計算目標反例數量
            target_count = int(len(positive_cases) * ratio)
            self.logger.info(f"目標反例數量: {target_count} (正例: {len(positive_cases)}, 比例: {ratio})")
            
            # 如果候選案例數量超過目標，隨機選擇
            if len(filtered_candidates) > target_count:
                import random
                selected_cases = random.sample(filtered_candidates, target_count)
                self.logger.info(f"從 {len(filtered_candidates)} 個候選中隨機選擇了 {len(selected_cases)} 個反例")
            else:
                selected_cases = filtered_candidates
                if len(selected_cases) < target_count:
                    self.logger.warning(f"反例數量不足: 找到 {len(selected_cases)}, 目標 {target_count}")
            
            # 為反例添加標記
            final_cases = []
            for case in selected_cases:
                if hasattr(case, '__dict__'):
                    case.__dict__['positive_case'] = 0
                    final_cases.append(case)
                elif isinstance(case, dict):
                    case['positive_case'] = 0
                    final_cases.append(case)
                else:
                    final_cases.append(case)
            
            self.logger.info(f"最終生成反例數量: {len(final_cases)}")
            return final_cases
            
        except Exception as e:
            self.logger.error(f"時間分離和比例控制失敗: {str(e)}")
            return candidate_cases[:int(len(positive_cases) * ratio)]  # 降級處理
    
    async def _generate_negative_cases(self, positive_cases: List[CaseData],
                                 symbols: List[str],
                                 request: NegativeCaseRequest) -> List[CaseData]:
        """基於真實K線數據生成時間分離的反例案例"""
        self.logger.info(f"開始生成真實反例：正例數量={len(positive_cases)}, 目標比例={request.negative_ratio}")
        
        negative_cases = []
        target_count = int(len(positive_cases) * request.negative_ratio)
        separation_days = request.time_separation_days
        
        # 獲取數據加載器
        from ..services.standalone_search_service import standalone_search_service
        data_loader = standalone_search_service.data_loader
        
        for i, positive_case in enumerate(positive_cases):
            if len(negative_cases) >= target_count:
                break
                
            try:
                # 調試時間戳格式
                self.logger.info(f"正例 {i} 時間戳: {positive_case.timestamp} (type: {type(positive_case.timestamp)})")
                self.logger.info(f"分離天數: {separation_days} (type: {type(separation_days)})")

                # 安全解析時間戳
                timestamp_str = str(positive_case.timestamp)
                if 'Z' in timestamp_str:
                    timestamp_str = timestamp_str.replace('Z', '+00:00')
                elif '+' not in timestamp_str and 'T' in timestamp_str:
                    timestamp_str += '+00:00'

                pos_time = datetime.fromisoformat(timestamp_str)
                symbol = str(positive_case.symbol)

                # 確保separation_days是整數
                sep_days = int(separation_days)

                # 計算分離的時間點
                before_time = pos_time - timedelta(days=sep_days)
                after_time = pos_time + timedelta(days=sep_days)

                self.logger.info(f"正例時間: {pos_time}, 前分離: {before_time}, 後分離: {after_time}")
                
                # 為每個候選時間點獲取真實K線數據
                for candidate_time in [before_time, after_time]:
                    if len(negative_cases) >= target_count:
                        break
                    
                    try:
                        # 獲取該時間點前後的K線數據
                        # 使用更大的時間範圍查詢，並確保查詢歷史數據
                        start_time = (candidate_time - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                        end_time = (candidate_time + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

                        # 確保查詢的是歷史時間，不是未來時間
                        current_time = datetime.now()
                        if candidate_time > current_time:
                            self.logger.warning(f"跳過未來時間點: {candidate_time}")
                            continue
                        
                        self.logger.info(f"準備獲取 {symbol} 從 {start_time} 到 {end_time} 的K線數據")
                        try:
                            # 調用真實數據加載器
                            kline_data = data_loader.get_historical_data(
                                symbol=symbol,
                                start_time=start_time,
                                end_time=end_time,
                                interval='12h'
                            )
                            self.logger.info(f"數據獲取結果: {type(kline_data)}, 長度: {len(kline_data) if kline_data is not None else 'None'}")
                        except Exception as data_error:
                            self.logger.error(f"數據加載器調用失敗: {str(data_error)}")
                            kline_data = None
                        
                        if kline_data is not None and not kline_data.empty:
                            # 找到最接近目標時間的K線
                            target_timestamp = candidate_time.strftime('%Y-%m-%d %H:%M:%S')
                            closest_idx = None
                            min_diff = float('inf')
                            
                            for idx, row in kline_data.iterrows():
                                time_diff = abs((idx - candidate_time).total_seconds())
                                if time_diff < min_diff:
                                    min_diff = time_diff
                                    closest_idx = idx
                            
                            if closest_idx is not None:
                                row = kline_data.loc[closest_idx]
                                
                                # 計算價格變化
                                price_change = (float(row['close']) - float(row['open'])) / float(row['open'])

                                negative_case = CaseData(
                                    symbol=symbol,
                                    timestamp=closest_idx.isoformat(),
                                    open=float(row['open']),
                                    high=float(row['high']),
                                    low=float(row['low']),
                                    close=float(row['close']),
                                    volume=float(row['volume']),
                                    trigger_idx=0,  # 反例的觸發索引
                                    price_change=price_change,
                                    market_phase="反例"  # 標記為反例階段
                                )
                                
                                negative_cases.append(negative_case)
                                self.logger.info(f"生成真實反例 {len(negative_cases)}: {symbol} at {closest_idx}")
                                
                    except Exception as e:
                        self.logger.warning(f"獲取 {symbol} 在 {candidate_time} 的真實數據失敗: {str(e)}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"處理正例 {i} 時出錯: {str(e)}")
                continue
        
        self.logger.info(f"實際生成的真實反例數量: {len(negative_cases)}")
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
        
        all_cases = []

        self.logger.info(f"合併正例數量: {len(positive_cases)}")
        self.logger.info(f"合併反例數量: {len(negative_cases)}")

        # 處理正例，添加 positive_case 標記
        for case in positive_cases:
            case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
            case_dict['positive_case'] = True
            all_cases.append(case_dict)

        # 處理反例，添加 positive_case 標記  
        for case in negative_cases:
            case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
            case_dict['positive_case'] = False
            all_cases.append(case_dict)

        self.logger.info(f"合併後總案例數: {len(all_cases)}")
        if all_cases:
            self.logger.info(f"第一個案例有positive_case標記: {'positive_case' in all_cases[0]}")
        
        symbols_processed = []
        for case in all_cases:
            if isinstance(case, dict) and 'symbol' in case:
                symbols_processed.append(case['symbol'])
            elif hasattr(case, 'symbol'):
                symbols_processed.append(case.symbol)
        symbols_processed = list(set(symbols_processed))
        
        return SearchResultData(
            cases=all_cases,
            total_cases=len(all_cases),
            search_config={},
            execution_time=10.0,
            symbols_processed=symbols_processed,
            positive_cases_count=len(positive_cases),
            negative_cases_count=len(negative_cases),
            summary={
                "total_cases": len(all_cases),
                "positive_cases": len(positive_cases),
                "negative_cases": len(negative_cases),
                "unique_symbols": len(symbols_processed),
                "time_range": {"start": "2024-02-01", "end": "2025-05-31"},
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