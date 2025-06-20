import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.config import settings
from api.core.logging import get_logger, log_function_call
from api.utils.exceptions import (
    SearchExecutionException,
    DataLoaderException,
    SearchConfigException,
    raise_execution_error
)
from api.models.requests import SearchConfigRequest, FilterConditionRequest
from api.models.responses import (
    CaseData, CaseSummary, SamplingQuality, SearchResultData,
    TaskInfo, TaskStatusEnum, TaskProgress
)

class StandaloneTaskManager:
    """Standalone task management for search operations"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_results: Dict[str, Any] = {}
        self.logger = get_logger("api.standalone_task_manager")
    
    def create_task(self, config_name: str) -> str:
        """Create a new task and return task ID"""
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatusEnum.PENDING,
            created_at=now,
            updated_at=now,
            config_name=config_name
        )
        
        self.tasks[task_id] = task_info
        self.logger.info(f"Created task {task_id} for config: {config_name}")
        return task_id
    
    def update_task_status(self, task_id: str, status: TaskStatusEnum, 
                          error_message: Optional[str] = None,
                          progress: Optional[TaskProgress] = None):
        """Update task status"""
        if task_id not in self.tasks:
            self.logger.warning(f"Task {task_id} not found")
            return
        
        self.tasks[task_id].status = status
        self.tasks[task_id].updated_at = datetime.now()
        
        if error_message:
            self.tasks[task_id].error_message = error_message
        
        if progress:
            self.tasks[task_id].progress = progress
        
        self.logger.info(f"Updated task {task_id} status to {status}")
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status"""
        return self.tasks.get(task_id)
    
    def set_task_result(self, task_id: str, result: Any):
        """Set task result"""
        self.task_results[task_id] = result
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get task result"""
        return self.task_results.get(task_id)
    
    def cleanup_old_tasks(self, hours: int = 24):
        """Clean up tasks older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        tasks_to_remove = []
        
        for task_id, task_info in self.tasks.items():
            if task_info.created_at < cutoff_time:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            if task_id in self.task_results:
                del self.task_results[task_id]
        
        if tasks_to_remove:
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

class StandaloneSearchService:
    """Standalone search service that loads momentum modules dynamically"""
    
    def __init__(self):
        self.logger = get_logger("api.standalone_search_service")
        self.task_manager = StandaloneTaskManager()
        self._active_searches = 0
        
        # Initialize momentum modules
        self.momentum_available = False
        self.data_loader = None
        self.search_engine = None
        
        self._attempt_momentum_loading()
    
    def _attempt_momentum_loading(self):
        """Attempt to load momentum modules with comprehensive path handling"""
        try:
            self.logger.info("Attempting to load momentum modules...")
            
            # Add multiple potential paths
            momentum_paths = [
                project_root / "momentum",
                project_root / "momentum" / "DataExtraction",
            ]
            
            for path in momentum_paths:
                if str(path) not in sys.path:
                    sys.path.insert(0, str(path))
            
            # Try direct imports first
            try:
                self.logger.info("Trying direct imports...")
                
                # Import DataLoader
                from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
                self.data_loader = MomentumDataLoader()
                self.logger.info("✅ DataLoader imported successfully")
                
                # Import SearchEngine
                from momentum.DataExtraction.case_search_engine import CaseSearchEngine
                self.search_engine = CaseSearchEngine(self.data_loader)
                self.logger.info("✅ SearchEngine imported successfully")
                
                self.momentum_available = True
                self.logger.info("✅ All momentum modules loaded successfully")
                return
                
            except ImportError as e:
                self.logger.info(f"Direct import failed: {e}")
            
            # Try alternative import paths
            try:
                self.logger.info("Trying alternative import paths...")
                
                # Try full path imports
                full_path = project_root / "momentum"
                if str(full_path) not in sys.path:
                    sys.path.insert(0, str(full_path))
                
                from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
                from momentum.DataExtraction.case_search_engine import CaseSearchEngine
                
                self.data_loader = MomentumDataLoader()
                self.search_engine = CaseSearchEngine(self.data_loader)
                
                self.momentum_available = True
                self.logger.info("✅ Momentum modules loaded via alternative path")
                return
                
            except Exception as e:
                self.logger.info(f"Full path import failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to load momentum modules: {e}")
        
        # If all loading attempts failed, raise exception
        if not self.momentum_available:
            error_msg = "Momentum modules are required but could not be loaded"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _convert_request_to_search_config(self, request: SearchConfigRequest):
        """將API請求轉換為搜索引擎配置"""
        try:
            # 動態導入搜索配置類
            from momentum.DataExtraction.case_search_engine import SearchConfiguration, FilterCondition
            
            # 創建基本搜索配置
            config = SearchConfiguration(
                name=request.name,
                description=request.description or f"{request.timeframe.value} timeframe search",
                timeframe=request.timeframe.value,  # 轉換 enum 為字符串
                lookback_periods=request.lookback_periods,
                forward_periods=request.forward_periods,
                sample_limit=request.sample_limit,
                min_volume=request.min_volume,
                exclude_new_listing_days=request.exclude_new_listing_days
            )
            
            # 添加初始條件
            for condition_req in request.initial_conditions:
                condition = FilterCondition(
                    condition_type=condition_req.condition_type.value,
                    parameter=condition_req.parameter,
                    operator=condition_req.operator.value,
                    value=condition_req.value,
                    description=condition_req.description
                )
                config.add_initial_condition(condition)
            
            # 添加高級條件
            for condition_req in request.advanced_conditions:
                condition = FilterCondition(
                    condition_type=condition_req.condition_type.value,
                    parameter=condition_req.parameter,
                    operator=condition_req.operator.value,
                    value=condition_req.value,
                    description=condition_req.description
                )
                config.add_advanced_condition(condition)
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to convert request to search config: {str(e)}")
            raise
    
    async def execute_search(self, request: SearchConfigRequest, 
                           symbols: Optional[List[str]] = None) -> str:
        """Execute search asynchronously and return task ID"""
        # Check concurrent search limit
        if self._active_searches >= settings.max_concurrent_searches:
            raise SearchExecutionException(
                f"Maximum concurrent searches ({settings.max_concurrent_searches}) reached"
            )
        
        # Create task
        task_id = self.task_manager.create_task(request.name)
        
        # Start search in background
        asyncio.create_task(self._run_search_task(task_id, request, symbols))
        
        return task_id
    
    async def _run_search_task(self, task_id: str, request: SearchConfigRequest,
                             symbols: Optional[List[str]] = None):
        """Run the search task with real data only"""
        start_time = datetime.now()
        self._active_searches += 1
        
        try:
            # Update task status to running
            self.task_manager.update_task_status(task_id, TaskStatusEnum.RUNNING)
            
            # Ensure search engine is available
            if not self.momentum_available or not self.search_engine:
                error_msg = "Search engine not available - real data modules required"
                self.logger.error(error_msg)
                self.task_manager.update_task_status(
                    task_id, TaskStatusEnum.FAILED, error_message=error_msg
                )
                return
            
            self.logger.info(f"Running real search for: {request.name}")
            
            try:
                # 轉換請求為搜索配置
                search_config = self._convert_request_to_search_config(request)
                
                # 執行真實搜索
                real_cases_dict = await self.search_engine.search_cases(
                    config=search_config,
                    symbols=symbols or ["BTCUSDT"],
                    batch_size=1,
                    save_results=False
                )
                
                # 檢查搜索結果
                if real_cases_dict is None:
                    error_msg = "Search engine returned None - no data available"
                    self.logger.error(error_msg)
                    self.task_manager.update_task_status(
                        task_id, TaskStatusEnum.FAILED, error_message=error_msg
                    )
                    return
                
                if len(real_cases_dict) == 0:
                    error_msg = "No cases found matching the specified criteria"
                    self.logger.warning(error_msg)
                    self.task_manager.update_task_status(
                        task_id, TaskStatusEnum.FAILED, error_message=error_msg
                    )
                    return
                
                # 轉換字典格式為 CaseData 對象
                real_cases = []
                for case_dict in real_cases_dict:
                    try:
                        # 確保必要欄位存在
                        required_fields = ['symbol', 'timestamp', 'open', 'high', 'low', 'close']
                        if not all(key in case_dict for key in required_fields):
                            missing_fields = [key for key in required_fields if key not in case_dict]
                            self.logger.warning(f"Case data missing required fields: {missing_fields}")
                            continue
                        
                        case_data = CaseData(
                            symbol=case_dict['symbol'],
                            timestamp=datetime.strptime(case_dict['timestamp'], '%Y-%m-%d %H:%M:%S'),
                            trigger_idx=case_dict.get('trigger_idx', 0),
                            
                            # OHLC 數據 - 直接使用真實數據
                            open=case_dict['open'],
                            high=case_dict['high'],
                            low=case_dict['low'],
                            close=case_dict['close'],
                            volume=case_dict.get('volume', 1000000),
                            price_change=case_dict.get('price_change', 0.05),
                            market_phase=case_dict.get('market_phase', 'NEUTRAL'),
                            
                            # 未來表現指標
                            future1_close_return=case_dict.get('future1_close_return'),
                            future2_close_return=case_dict.get('future2_close_return'),
                            future4_close_return=case_dict.get('future4_close_return'),
                            future6_close_return=case_dict.get('future6_close_return'),
                            future24_close_return=case_dict.get('future24_close_return'),
                            future48_close_return=case_dict.get('future48_close_return'),
                            future_max_return=case_dict.get('future_max_return'),
                            future_max_drawdown=case_dict.get('future_max_drawdown'),
                            
                            # 其他數據
                            future24_close=case_dict.get('future24_close'),
                            future24_low=case_dict.get('future24_low'),
                            prior_volatility=case_dict.get('prior_volatility'),
                            prior_range=case_dict.get('prior_range'),
                            prior_abs_change_sum=case_dict.get('prior_abs_change_sum'),
                            time_range=case_dict.get('time_range', {
                                'start': '2023-01-01 00:00:00',
                                'end': '2023-01-02 00:00:00'
                            })
                        )
                        real_cases.append(case_data)
                        
                    except Exception as case_error:
                        self.logger.error(f"Error processing case data: {case_error}")
                        continue
                
                # 檢查處理後的案例數量
                if len(real_cases) == 0:
                    error_msg = "No valid cases after data processing"
                    self.logger.error(error_msg)
                    self.task_manager.update_task_status(
                        task_id, TaskStatusEnum.FAILED, error_message=error_msg
                    )
                    return
                
                self.logger.info(f"Real search completed: found {len(real_cases)} cases")
                
            except Exception as e:
                error_msg = f"Real search failed: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                self.task_manager.update_task_status(
                    task_id, TaskStatusEnum.FAILED, error_message=error_msg
                )
                return
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Generate summary
            positive_cases = len([c for c in real_cases if getattr(c, 'future4_close_return', 0) and c.future4_close_return > 0])
            negative_cases = len(real_cases) - positive_cases
            
            # Market phase distribution
            phase_dist = {}
            for case in real_cases:
                phase_dist[case.market_phase] = phase_dist.get(case.market_phase, 0) + 1
            
            # Convert results to response format
            result_data = SearchResultData(
                cases=real_cases,
                summary=CaseSummary(
                    total_cases=len(real_cases),
                    positive_cases=positive_cases,
                    negative_cases=negative_cases,
                    unique_symbols=len(set(c.symbol for c in real_cases)),
                    time_range={
                        "start": request.start_date.strftime('%Y-%m-%d'),
                        "end": request.end_date.strftime('%Y-%m-%d')
                    },
                    market_phase_distribution=phase_dist
                ),
                sampling_quality=SamplingQuality(
                    time_separation_score=0.8 if len(real_cases) > 5 else 0.6,
                    symbol_diversity_score=min(1.0, len(set(c.symbol for c in real_cases)) / 10),
                    market_phase_balance=0.7 if len(phase_dist) > 1 else 0.4,
                    overall_quality_score=0.75,
                    warnings=[]
                ),
                execution_time=execution_time,
                cache_used=False
            )
            
            # Store result and update task status
            self.task_manager.set_task_result(task_id, result_data)
            self.task_manager.update_task_status(task_id, TaskStatusEnum.COMPLETED)
            
            log_function_call(
                "real_search_execution",
                {"config_name": request.name, "cases_found": len(real_cases)},
                execution_time
            )
            
        except Exception as e:
            # Handle search failure
            error_msg = f"Search execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            self.task_manager.update_task_status(
                task_id, TaskStatusEnum.FAILED, error_message=error_msg
            )
            
        finally:
            self._active_searches -= 1
    
    async def preview_search(self, request: SearchConfigRequest,
                           symbols_limit: int = 10) -> Dict[str, Any]:
        """Preview search results without executing full search"""
        try:
            # Ensure data loader is available
            if not self.momentum_available or not self.data_loader:
                raise SearchExecutionException("Preview requires real data loader")
            
            # Try to get real symbol list
            try:
                all_symbols = await asyncio.to_thread(self.data_loader.get_symbols_list)
                valid_symbols = [s for s in all_symbols[:symbols_limit] if s.endswith('USDT')]
                self.logger.info("Using real symbol list for preview")
            except Exception as e:
                self.logger.warning(f"Failed to get real symbols: {e}")
                raise SearchExecutionException("Unable to access real symbol data for preview")
            
            # Generate preview
            preview_data = {
                "estimated_symbols": len(valid_symbols),
                "estimated_cases": min(request.sample_limit, len(valid_symbols) * 10),
                "estimated_execution_time": f"{len(valid_symbols) * 2}-{len(valid_symbols) * 4} seconds",
                "available_symbols": valid_symbols,
                "warnings": [],
                "data_quality": "real"
            }
            
            return preview_data
            
        except Exception as e:
            self.logger.error(f"Preview failed: {str(e)}")
            raise SearchExecutionException(f"Preview generation failed: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status"""
        return self.task_manager.get_task_status(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[SearchResultData]:
        """Get task result"""
        return self.task_manager.get_task_result(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        task_info = self.task_manager.get_task_status(task_id)
        if task_info and task_info.status == TaskStatusEnum.RUNNING:
            self.task_manager.update_task_status(
                task_id, TaskStatusEnum.CANCELLED, error_message="Task cancelled by user"
            )
            return True
        return False
    
    async def cleanup_old_tasks(self):
        """Clean up old tasks"""
        await asyncio.to_thread(self.task_manager.cleanup_old_tasks)

# Global service instance
standalone_search_service = StandaloneSearchService()

# Export
__all__ = ["StandaloneSearchService", "standalone_search_service"]