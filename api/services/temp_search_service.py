import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from api.core.config import settings
from api.core.logging import get_logger, log_function_call
from api.utils.exceptions import SearchExecutionException
from api.models.requests import SearchConfigRequest
from api.models.responses import (
    CaseData, CaseSummary, SamplingQuality, SearchResultData,
    TaskInfo, TaskStatusEnum, TaskProgress
)

class TempTaskManager:
    """Temporary task manager for testing"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_results: Dict[str, Any] = {}
        self.logger = get_logger("api.temp_task_manager")
    
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
                          progress: Optional[TaskProgress] = None,
                          error_message: Optional[str] = None):
        """Update task status and progress"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].updated_at = datetime.now()
            
            if progress:
                self.tasks[task_id].progress = progress
            if error_message:
                self.tasks[task_id].error_message = error_message
                
            self.logger.info(f"Updated task {task_id} status to {status}")
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information"""
        return self.tasks.get(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get task result"""
        return self.task_results.get(task_id)
    
    def set_task_result(self, task_id: str, result: Any):
        """Set task result"""
        self.task_results[task_id] = result

class TempSearchService:
    """Temporary search service for testing API functionality"""
    
    def __init__(self):
        self.logger = get_logger("api.temp_search_service")
        self.task_manager = TempTaskManager()
        self._active_searches = 0
    
    async def execute_search(self, request: SearchConfigRequest, 
                           symbols: Optional[List[str]] = None) -> str:
        """Execute search asynchronously and return task ID"""
        # Create task
        task_id = self.task_manager.create_task(request.name)
        
        # Start search in background
        asyncio.create_task(self._run_mock_search_task(task_id, request, symbols))
        
        return task_id
    
    async def _run_mock_search_task(self, task_id: str, request: SearchConfigRequest,
                                  symbols: Optional[List[str]] = None):
        """Run a mock search task for testing"""
        start_time = datetime.now()
        self._active_searches += 1
        
        try:
            # Update task status to running
            self.task_manager.update_task_status(task_id, TaskStatusEnum.RUNNING)
            
            # Simulate search work
            await asyncio.sleep(3)  # Simulate 3 seconds of work
            
            # Create mock results
            mock_cases = self._create_mock_cases(request)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Convert results to response format
            result_data = SearchResultData(
                cases=mock_cases,
                summary=CaseSummary(
                    total_cases=len(mock_cases),
                    positive_cases=len([c for c in mock_cases if not hasattr(c, 'label') or c.label != 0]),
                    negative_cases=0,
                    unique_symbols=len(set(c.symbol for c in mock_cases)),
                    time_range={
                        "start": request.start_date.strftime('%Y-%m-%d'),
                        "end": request.end_date.strftime('%Y-%m-%d')
                    },
                    market_phase_distribution={"GREED": 2, "NEUTRAL": 1}
                ),
                sampling_quality=SamplingQuality(
                    time_separation_score=0.8,
                    symbol_diversity_score=0.7,
                    market_phase_balance=0.6,
                    overall_quality_score=0.7,
                    warnings=[]
                ),
                execution_time=execution_time,
                cache_used=False
            )
            
            # Store result and update task status
            self.task_manager.set_task_result(task_id, result_data)
            self.task_manager.update_task_status(task_id, TaskStatusEnum.COMPLETED)
            
            log_function_call(
                "mock_search_execution",
                {"config_name": request.name, "cases_found": len(mock_cases)},
                execution_time
            )
            
        except Exception as e:
            # Handle search failure
            error_msg = f"Mock search execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            self.task_manager.update_task_status(
                task_id, TaskStatusEnum.FAILED, error_message=error_msg
            )
            
        finally:
            self._active_searches -= 1
    
    def _create_mock_cases(self, request: SearchConfigRequest) -> List[CaseData]:
        """Create mock case data for testing"""
        mock_cases = []
        
        base_time = datetime.combine(request.start_date, datetime.min.time())
        
        for i in range(3):  # Create 3 mock cases
            case = CaseData(
                symbol=f"BTC{'USDT' if i == 0 else 'ETH' if i == 1 else 'ADA'}USDT",
                timestamp=base_time + timedelta(days=i*10),
                trigger_idx=95 + i,
                close=45000.0 + i * 1000,
                volume=1500000.0 + i * 100000,
                price_change=0.12 + i * 0.02,
                market_phase=["GREED", "NEUTRAL", "GREED"][i],
                future1_close_return=0.05 + i * 0.01,
                future2_close_return=0.08 + i * 0.01,
                future4_close_return=0.12 + i * 0.02,
                future6_close_return=0.15 + i * 0.02,
                future_max_return=0.20 + i * 0.03,
                future_max_drawdown=-0.03 - i * 0.01,
                prior_volatility=0.02 + i * 0.005,
                prior_range=0.05 + i * 0.01,
                prior_abs_change_sum=0.08 + i * 0.01,
                time_range={
                    "start": (base_time + timedelta(days=i*10-4)).strftime('%Y-%m-%d %H:%M:%S'),
                    "end": (base_time + timedelta(days=i*10+1)).strftime('%Y-%m-%d %H:%M:%S')
                }
            )
            mock_cases.append(case)
        
        return mock_cases
    
    async def preview_search(self, request: SearchConfigRequest,
                           symbols_limit: int = 10) -> Dict[str, Any]:
        """Preview search results without executing full search"""
        try:
            return {
                "estimated_cases": 15,
                "estimated_execution_time": 25.0,
                "symbols_to_process": ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"],
                "potential_issues": []
            }
            
        except Exception as e:
            raise SearchExecutionException(f"Preview generation failed: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status information"""
        return self.task_manager.get_task(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[SearchResultData]:
        """Get task result if completed"""
        task = self.task_manager.get_task(task_id)
        if task and task.status == TaskStatusEnum.COMPLETED:
            return self.task_manager.get_task_result(task_id)
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        task = self.task_manager.get_task(task_id)
        if task and task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            self.task_manager.update_task_status(task_id, TaskStatusEnum.CANCELLED)
            return True
        return False
    
    def cleanup_old_tasks(self):
        """Clean up old completed tasks"""
        pass  # Mock implementation

# Global service instance
temp_search_service = TempSearchService()

# Export
__all__ = ["TempSearchService", "temp_search_service"]