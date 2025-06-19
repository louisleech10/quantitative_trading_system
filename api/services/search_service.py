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

# Import existing momentum modules
try:
    from momentum.DataExtraction.data_loader_momentum import DataLoader
    from momentum.DataExtraction.case_search_engine import (
        CaseSearchEngine, SearchConfiguration, FilterCondition
    )
    from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig
except ImportError as e:
    raise ImportError(f"Failed to import momentum modules: {e}")

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
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        tasks_to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.updated_at < cutoff_time and task.status in [
                TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED
            ]
        ]
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            if task_id in self.task_results:
                del self.task_results[task_id]
        
        if tasks_to_remove:
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

class SearchService:
    """Main search service that wraps existing momentum search logic"""
    
    def __init__(self):
        self.logger = get_logger("api.search_service")
        self.task_manager = TaskManager()
        self.data_loader = None
        self.search_engine = None
        self._active_searches = 0
        
        # Initialize data loader and search engine
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize data loader and search engine"""
        try:
            # Initialize data loader with cache directory from settings
            self.data_loader = DataLoader(cache_dir=str(settings.data_cache_path))
            
            # Initialize search engine
            self.search_engine = CaseSearchEngine(self.data_loader)
            
            self.logger.info("Search service components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize search components: {str(e)}")
            raise SearchExecutionException(f"Service initialization failed: {str(e)}")
    
    def _convert_request_to_search_config(self, request: SearchConfigRequest) -> SearchConfiguration:
        """Convert API request to internal search configuration"""
        try:
            # Create base search configuration
            config = SearchConfiguration(
                name=request.name,
                description=request.description or f"{request.timeframe} timeframe search",
                timeframe=request.timeframe,
                lookback_periods=request.lookback_periods,
                forward_periods=request.forward_periods,
                time_range=(str(request.start_date), str(request.end_date)),
                sample_limit=request.sample_limit,
                min_volume=request.min_volume,
                exclude_new_listing_days=request.exclude_new_listing_days
            )
            
            # Add initial conditions
            for condition_req in request.initial_conditions:
                condition = FilterCondition(
                    condition_type=condition_req.condition_type,
                    parameter=condition_req.parameter,
                    operator=condition_req.operator,
                    value=condition_req.value,
                    description=condition_req.description
                )
                config.add_initial_condition(condition)
            
            # Add advanced conditions
            for condition_req in request.advanced_conditions:
                condition = FilterCondition(
                    condition_type=condition_req.condition_type,
                    parameter=condition_req.parameter,
                    operator=condition_req.operator,
                    value=condition_req.value,
                    description=condition_req.description
                )
                config.add_advanced_condition(condition)
            
            return config
            
        except Exception as e:
            raise SearchConfigException(f"Failed to convert request to search config: {str(e)}")
    
    def _convert_cases_to_response_data(self, cases: List[Dict], 
                                      execution_time: float,
                                      cache_used: bool = False) -> SearchResultData:
        """Convert search results to response data format"""
        try:
            # Convert cases to CaseData objects
            case_data_list = []
            for case in cases:
                case_data = CaseData(
                    symbol=case['symbol'],
                    timestamp=case['timestamp'],
                    trigger_idx=case.get('trigger_idx', 0),
                    close=case['close'],
                    volume=case['volume'],
                    price_change=case['price_change'],
                    market_phase=case.get('market_phase', 'UNKNOWN'),
                    future1_close_return=case.get('future1_close_return'),
                    future2_close_return=case.get('future2_close_return'),
                    future4_close_return=case.get('future4_close_return'),
                    future6_close_return=case.get('future6_close_return'),
                    future_max_return=case.get('future_max_return'),
                    future_max_drawdown=case.get('future_max_drawdown'),
                    prior_volatility=case.get('prior_volatility'),
                    prior_range=case.get('prior_range'),
                    prior_abs_change_sum=case.get('prior_abs_change_sum'),
                    time_range=case.get('time_range', {})
                )
                case_data_list.append(case_data)
            
            # Generate summary
            summary = self._generate_case_summary(cases)
            
            # Assess sampling quality
            sampling_quality = self._assess_sampling_quality(cases)
            
            return SearchResultData(
                cases=case_data_list,
                summary=summary,
                sampling_quality=sampling_quality,
                execution_time=execution_time,
                cache_used=cache_used
            )
            
        except Exception as e:
            raise SearchExecutionException(f"Failed to convert cases to response: {str(e)}")
    
    def _generate_case_summary(self, cases: List[Dict]) -> CaseSummary:
        """Generate summary statistics for cases"""
        if not cases:
            return CaseSummary(
                total_cases=0,
                positive_cases=0,
                negative_cases=0,
                unique_symbols=0,
                time_range={},
                market_phase_distribution={}
            )
        
        # Count positive/negative cases (assuming label field exists)
        positive_cases = sum(1 for case in cases if case.get('label', 1) == 1)
        negative_cases = len(cases) - positive_cases
        
        # Get unique symbols
        unique_symbols = len(set(case['symbol'] for case in cases))
        
        # Get time range
        timestamps = [case['timestamp'] for case in cases]
        time_range = {
            'start': min(timestamps).strftime('%Y-%m-%d %H:%M:%S'),
            'end': max(timestamps).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Market phase distribution
        market_phases = {}
        for case in cases:
            phase = case.get('market_phase', 'UNKNOWN')
            market_phases[phase] = market_phases.get(phase, 0) + 1
        
        return CaseSummary(
            total_cases=len(cases),
            positive_cases=positive_cases,
            negative_cases=negative_cases,
            unique_symbols=unique_symbols,
            time_range=time_range,
            market_phase_distribution=market_phases
        )
    
    def _assess_sampling_quality(self, cases: List[Dict]) -> SamplingQuality:
        """Assess the quality of sampling"""
        if not cases:
            return SamplingQuality(
                time_separation_score=0.0,
                symbol_diversity_score=0.0,
                market_phase_balance=0.0,
                overall_quality_score=0.0,
                warnings=["No cases found"]
            )
        
        warnings = []
        
        # Time separation score (placeholder implementation)
        time_separation_score = 0.8  # TODO: Implement actual logic
        
        # Symbol diversity score
        unique_symbols = len(set(case['symbol'] for case in cases))
        symbol_diversity_score = min(1.0, unique_symbols / 20)  # Assume 20+ symbols is good
        
        # Market phase balance
        phases = {}
        for case in cases:
            phase = case.get('market_phase', 'UNKNOWN')
            phases[phase] = phases.get(phase, 0) + 1
        
        if len(phases) < 2:
            warnings.append("Cases concentrated in single market phase")
            market_phase_balance = 0.3
        else:
            # Calculate balance based on distribution evenness
            total = len(cases)
            max_imbalance = max(phases.values()) / total
            market_phase_balance = 1.0 - max_imbalance
        
        # Overall quality score
        overall_quality_score = (
            time_separation_score * 0.4 +
            symbol_diversity_score * 0.3 +
            market_phase_balance * 0.3
        )
        
        if overall_quality_score < 0.5:
            warnings.append("Overall sampling quality is below recommended threshold")
        
        return SamplingQuality(
            time_separation_score=time_separation_score,
            symbol_diversity_score=symbol_diversity_score,
            market_phase_balance=market_phase_balance,
            overall_quality_score=overall_quality_score,
            warnings=warnings
        )
    
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
        """Run the actual search task"""
        start_time = datetime.now()
        self._active_searches += 1
        
        try:
            # Update task status to running
            self.task_manager.update_task_status(task_id, TaskStatusEnum.RUNNING)
            
            # Convert request to internal config
            config = self._convert_request_to_search_config(request)
            
            # Execute search using existing search engine
            cases = await self.search_engine.search_cases(
                config=config,
                symbols=symbols,
                batch_size=request.batch_size,
                save_results=True
            )
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Convert results to response format
            result_data = self._convert_cases_to_response_data(
                cases, execution_time, cache_used=False
            )
            
            # Store result and update task status
            self.task_manager.set_task_result(task_id, result_data)
            self.task_manager.update_task_status(task_id, TaskStatusEnum.COMPLETED)
            
            log_function_call(
                "search_execution",
                {"config_name": request.name, "cases_found": len(cases)},
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
            # Get limited symbol list for preview
            all_symbols = self.data_loader.get_symbols_list()
            valid_symbols = [s for s in all_symbols if s.endswith('USDT')][:symbols_limit]
            
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

# Global service instance
search_service = SearchService()

# Export
__all__ = ["SearchService", "search_service", "TaskManager"]