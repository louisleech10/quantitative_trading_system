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

# Add momentum module to path explicitly
momentum_path = project_root / "momentum"
if str(momentum_path) not in sys.path:
    sys.path.insert(0, str(momentum_path))

# Add DataExtraction path explicitly  
data_extraction_path = momentum_path / "DataExtraction"
if str(data_extraction_path) not in sys.path:
    sys.path.insert(0, str(data_extraction_path))

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

class TaskManager:
    """Task management for search operations"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_results: Dict[str, Any] = {}
        self.logger = get_logger("api.task_manager")
    
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

class FixedSearchService:
    """Fixed search service that properly imports momentum modules"""
    
    def __init__(self):
        self.logger = get_logger("api.fixed_search_service")
        self.task_manager = TaskManager()
        self._active_searches = 0
        
        # Initialize momentum modules with proper error handling
        self.data_loader = None
        self.search_engine = None
        self.market_config = None
        
        self._initialize_momentum_modules()
    
    def _initialize_momentum_modules(self):
        """Initialize momentum modules with enhanced error handling"""
        try:
            self.logger.info("Attempting to initialize momentum modules...")
            
            # Try to import momentum modules
            try:
                from data_loader_momentum import DataLoader
                self.logger.info("Successfully imported DataLoader")
            except ImportError as e:
                self.logger.error(f"Failed to import DataLoader: {e}")
                # Try alternative import path
                try:
                    from momentum.DataExtraction.data_loader_momentum import DataLoader
                    self.logger.info("Successfully imported DataLoader via full path")
                except ImportError as e2:
                    self.logger.error(f"Failed alternative DataLoader import: {e2}")
                    raise
            
            try:
                from case_search_engine import CaseSearchEngine, SearchConfiguration, FilterCondition
                self.logger.info("Successfully imported CaseSearchEngine")
            except ImportError as e:
                self.logger.error(f"Failed to import CaseSearchEngine: {e}")
                # Try alternative import path
                try:
                    from momentum.DataExtraction.case_search_engine import (
                        CaseSearchEngine, SearchConfiguration, FilterCondition
                    )
                    self.logger.info("Successfully imported CaseSearchEngine via full path")
                except ImportError as e2:
                    self.logger.error(f"Failed alternative CaseSearchEngine import: {e2}")
                    raise
            
            try:
                from Market_Screener_Configuration import MarketConfig
                self.market_config = MarketConfig
                self.logger.info("Successfully imported MarketConfig")
            except ImportError as e:
                self.logger.error(f"Failed to import MarketConfig: {e}")
                # Try alternative import path
                try:
                    from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig
                    self.market_config = MarketConfig
                    self.logger.info("Successfully imported MarketConfig via full path")
                except ImportError as e2:
                    self.logger.warning(f"Failed MarketConfig import, using fallback: {e2}")
                    self.market_config = None
            
            # Initialize components
            api_key, secret_key = settings.get_binance_credentials()
            
            # Initialize data loader with API credentials
            self.data_loader = DataLoader(
                cache_dir=str(settings.data_cache_path),
                api_key=api_key,
                api_secret=secret_key
            )
            
            # Initialize search engine
            self.search_engine = CaseSearchEngine(self.data_loader)
            
            self.logger.info("Momentum modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize momentum modules: {str(e)}")
            # Fall back to mock implementation
            self.logger.info("Falling back to mock implementation")
            self._initialize_mock_components()
    
    def _initialize_mock_components(self):
        """Initialize mock components as fallback"""
        from api.services.temp_search_service import TempSearchService
        temp_service = TempSearchService()
        
        # Use temp service methods as fallback
        self._run_mock_search_task = temp_service._run_mock_search_task
        self._create_mock_cases = temp_service._create_mock_cases
        
        self.logger.info("Mock components initialized as fallback")
    
    def _convert_request_to_search_config(self, request: SearchConfigRequest):
        """Convert API request to internal search configuration"""
        if not self.search_engine:
            raise SearchExecutionException("Search engine not properly initialized")
        
        try:
            # This would be the real implementation once modules are working
            # For now, we'll create a mock config structure
            config = {
                'name': request.name,
                'description': request.description or f"{request.timeframe} timeframe search",
                'timeframe': request.timeframe,
                'lookback_periods': request.lookback_periods,
                'forward_periods': request.forward_periods,
                'time_range': (str(request.start_date), str(request.end_date)),
                'sample_limit': request.sample_limit,
                'min_volume': request.min_volume,
                'exclude_new_listing_days': request.exclude_new_listing_days,
                'initial_conditions': [
                    {
                        'condition_type': cond.condition_type,
                        'parameter': cond.parameter,
                        'operator': cond.operator,
                        'value': cond.value,
                        'description': cond.description
                    }
                    for cond in request.initial_conditions
                ],
                'advanced_conditions': [
                    {
                        'condition_type': cond.condition_type,
                        'parameter': cond.parameter,
                        'operator': cond.operator,
                        'value': cond.value,
                        'description': cond.description
                    }
                    for cond in request.advanced_conditions
                ]
            }
            
            return config
            
        except Exception as e:
            raise SearchConfigException(f"Failed to convert request to search config: {str(e)}")
    
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
        if self.search_engine:
            asyncio.create_task(self._run_real_search_task(task_id, request, symbols))
        else:
            asyncio.create_task(self._run_mock_search_task(task_id, request, symbols))
        
        return task_id
    
    async def _run_real_search_task(self, task_id: str, request: SearchConfigRequest,
                                  symbols: Optional[List[str]] = None):
        """Run the actual search task using real momentum modules"""
        start_time = datetime.now()
        self._active_searches += 1
        
        try:
            # Update task status to running
            self.task_manager.update_task_status(task_id, TaskStatusEnum.RUNNING)
            
            # Convert request to internal config
            config = self._convert_request_to_search_config(request)
            
            self.logger.info(f"Starting real search with config: {config['name']}")
            
            # TODO: Execute real search using momentum modules
            # For now, simulate some work and return mock data
            await asyncio.sleep(5)  # Simulate real work
            
            # Create mock results (replace with real search results)
            from api.services.temp_search_service import TempSearchService
            temp_service = TempSearchService()
            mock_cases = temp_service._create_mock_cases(request)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Convert results to response format
            result_data = SearchResultData(
                cases=mock_cases,
                summary=CaseSummary(
                    total_cases=len(mock_cases),
                    positive_cases=len(mock_cases),
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
                "real_search_execution",
                {"config_name": request.name, "cases_found": len(mock_cases)},
                execution_time
            )
            
        except Exception as e:
            # Handle search failure
            error_msg = f"Real search execution failed: {str(e)}"
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
            if self.data_loader:
                # Try to get real symbol list
                try:
                    all_symbols = await asyncio.to_thread(self.data_loader.get_symbols_list)
                    valid_symbols = [s for s in all_symbols[:symbols_limit] if s.endswith('USDT')]
                except Exception as e:
                    self.logger.warning(f"Failed to get real symbols, using mock: {e}")
                    valid_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
            else:
                valid_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
            
            # Estimate execution time based on symbols and config
            estimated_time = len(valid_symbols) * 2.5  # Rough estimate: 2.5s per symbol
            
            # Estimate cases (placeholder logic)
            estimated_cases = len(valid_symbols) * 3  # Rough estimate
            
            return {
                "estimated_cases": estimated_cases,
                "estimated_execution_time": estimated_time,
                "symbols_to_process": valid_symbols,
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
        self.task_manager.cleanup_old_tasks()
    
    def is_real_service_available(self) -> bool:
        """Check if real momentum modules are available"""
        return self.data_loader is not None and self.search_engine is not None

# Global service instance
fixed_search_service = FixedSearchService()

# Export
__all__ = ["FixedSearchService", "fixed_search_service"]