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
    
    
    
    def create_task(self, config_name: str, task_id: Optional[str] = None) -> str:
        """Create a new task and return task ID"""
        if task_id is None:
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
        # ✅ 添加日誌確認結果存儲
        if result and hasattr(result, 'cases'):
            self.logger.debug(f"Stored task result: task_id={task_id}, cases={len(result.cases) if result.cases else 0}")
        else:
            self.logger.debug(f"Stored task result: task_id={task_id}, result_type={type(result).__name__}")
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get task result"""
        result = self.task_results.get(task_id)
        # ✅ 添加日誌確認結果讀取
        if result and hasattr(result, 'cases'):
            self.logger.debug(f"Retrieved task result: task_id={task_id}, cases={len(result.cases) if result.cases else 0}")
        else:
            self.logger.debug(f"Retrieved task result: task_id={task_id}, exists={result is not None}")
        return result
    
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

class MomentumDataLoaderWrapper:
    """Wrapper class to provide the expected interface for the search engine"""
    
    def __init__(self, momentum_data_loader):
        self.momentum_data_loader = momentum_data_loader
        self.data_loader = momentum_data_loader.data_loader  # 內部的 DataLoader 實例
        self.logger = get_logger("api.momentum_wrapper")
    
    def get_historical_data(self, symbol: str, start_time, end_time, interval: str = "4h"):
        """Delegate to the internal DataLoader's get_historical_data method"""
        try:
            # 處理時間參數 - 修復 tuple 錯誤
            if isinstance(start_time, tuple):
                if len(start_time) >= 3:
                    start_time = f"{start_time[0]:04d}-{start_time[1]:02d}-{start_time[2]:02d}"
                else:
                    start_time = "2022-01-01"  # 默認值
            elif isinstance(start_time, datetime):
                start_time = start_time.strftime('%Y-%m-%d')
            
            if isinstance(end_time, tuple):
                if len(end_time) >= 3:
                    end_time = f"{end_time[0]:04d}-{end_time[1]:02d}-{end_time[2]:02d}"
                else:
                    end_time = "2022-12-31"  # 默認值
            elif isinstance(end_time, datetime):
                end_time = end_time.strftime('%Y-%m-%d')
            
            self.logger.info(f"Getting data for {symbol}: {start_time} to {end_time}")
            
            return self.data_loader.get_historical_data(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                interval=interval
            )
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            raise
    
    def get_symbols_list(self):
        """Delegate to the internal DataLoader's get_symbols_list method"""
        return self.data_loader.get_symbols_list()
    
    def get_symbol_info(self, symbol: str):
        """Delegate to the internal DataLoader's get_symbol_info method"""
        return self.data_loader.get_symbol_info(symbol)

class StandaloneSearchService:
    """Standalone search service that loads momentum modules dynamically"""
    
    def __init__(self):
        self.logger = get_logger("api.standalone_search_service")
        self.task_manager = StandaloneTaskManager()  # 這裡現在是正確的
        self._active_searches = 0
        
        # Initialize momentum modules status
        self.momentum_available = False
        self.data_loader = None
        self.search_engine = None
        
        # 延遲加載：不在初始化時強制加載模塊
        # 只在實際需要時才加載
        self.logger.info("StandaloneSearchService initialized - momentum modules will be loaded on demand")
    
    def _ensure_momentum_loaded(self):
        """Ensure momentum modules are loaded, load them if not already loaded"""
        if self.momentum_available:
            return True
            
        try:
            self.logger.info("Loading momentum modules on demand...")
            
            # Add project root to path
            momentum_paths = [
                project_root / "momentum",
                project_root / "momentum" / "DataExtraction",
            ]
            
            for path in momentum_paths:
                if str(path) not in sys.path:
                    sys.path.insert(0, str(path))
            
            # Try to import momentum modules
            from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
            from momentum.DataExtraction.case_search_engine import CaseSearchEngine
            
            # Create instances
            momentum_loader = MomentumDataLoader()
            self.data_loader = MomentumDataLoaderWrapper(momentum_loader)
            self.search_engine = CaseSearchEngine(
                self.data_loader,
                enable_parallel=True,
                num_workers=None  # 使用自動偵測（根據CPU核心數和可用內存）
            )
            
            self.momentum_available = True
            self.logger.info("✅ Momentum modules loaded successfully on demand")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load momentum modules: {str(e)}")
            self.momentum_available = False
            return False
    
    def is_real_service_available(self) -> bool:
        """Check if real momentum service is available"""
        # Try to load modules if not already loaded
        if not self.momentum_available:
            self._ensure_momentum_loaded()
        
        return self.momentum_available and self.data_loader is not None and self.search_engine is not None

    
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
                
                # Import the correct class name: MomentumDataLoader (not MomentumStrategyDataLoader)
                from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
                momentum_loader = MomentumDataLoader()
                
                # Create a wrapper that provides the expected interface
                self.data_loader = MomentumDataLoaderWrapper(momentum_loader)
                self.logger.info("✅ DataLoader imported and wrapped successfully")

                # Import SearchEngine
                from momentum.DataExtraction.case_search_engine import CaseSearchEngine
                self.search_engine = CaseSearchEngine(
                    self.data_loader,
                    enable_parallel=True,
                    num_workers=None  # 使用自動偵測（根據CPU核心數和可用內存）
                )
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

                momentum_loader = MomentumDataLoader()
                self.data_loader = MomentumDataLoaderWrapper(momentum_loader)
                self.search_engine = CaseSearchEngine(
                    self.data_loader,
                    enable_parallel=True,
                    num_workers=None  # 使用自動偵測（根據CPU核心數和可用內存）
                )
                
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
            
            # 準備時間範圍
            time_range = (
                request.start_date,
                request.end_date
            )
            
            # 創建基本搜索配置
            config = SearchConfiguration(
                name=request.name,
                description=request.description or f"{request.timeframe.value} timeframe search",
                timeframe=request.timeframe.value,  # 轉換 enum 為字符串
                lookback_periods=request.lookback_periods,
                forward_periods=request.forward_periods,
                sample_limit=request.sample_limit,
                min_volume=request.min_volume,
                exclude_new_listing_days=request.exclude_new_listing_days,
                time_range=time_range  # 添加時間範圍參數
            )
            
            # 手動添加 time_range 屬性以確保兼容性
            config.time_range = time_range
            
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
        # Ensure momentum modules are loaded before executing search
        if not self._ensure_momentum_loaded():
            raise SearchExecutionException("Momentum modules could not be loaded")
        
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

                # 添加調試LOG
                self.logger.debug(f"Symbols parameter: {symbols}")
                self.logger.debug(f"Request symbols: {getattr(request, 'symbols', 'NOT_FOUND')}")

                def process_special_keywords(symbol_list):
                    if not symbol_list:
                        return ["BTCUSDT"]
                    
                    result = []
                    for symbol in symbol_list:
                        if symbol == "ALL_USDT":
                            # 獲取所有USDT交易對
                            try:
                                all_symbols = self.data_loader.get_symbols_list()
                                usdt_symbols = [s for s in all_symbols if s.endswith('USDT')]
                                # 排除特殊代幣
                                filtered = [s for s in usdt_symbols if not any(
                                    bad in s for bad in ['UP', 'DOWN', 'BULL', 'BEAR', 'USDC', 'BUSD']
                                )]
                                result.extend(filtered)
                            except:
                                result.append("BTCUSDT")
                        else:
                            result.append(symbol)
                    return result

                final_symbols = process_special_keywords(symbols or request.symbols or ["BTCUSDT"])
                self.logger.debug(f"Final symbols: {final_symbols}")
                
                # 執行真實搜索
                real_cases_dict = await self.search_engine.search_cases(
                    config=search_config,
                    symbols=final_symbols,
                    batch_size=1,
                    save_results=False
                )
                
                # 檢查搜索結果
                if real_cases_dict is None:
                    error_msg = "[DATA_UNAVAILABLE] Search engine returned no data - check symbol validity and date range"
                    self.logger.error(error_msg)
                    self.task_manager.update_task_status(
                        task_id, TaskStatusEnum.FAILED, error_message=error_msg
                    )
                    return
                
                if len(real_cases_dict) == 0:
                    info_msg = f"Search completed: No cases found for {len(final_symbols)} symbols with given criteria"
                    self.logger.info(info_msg)
                    # 沒有結果不是失敗，而是成功完成但結果為空
                    empty_summary = CaseSummary(
                        total_cases=0,
                        positive_cases=0,
                        negative_cases=0,
                        unique_symbols=len(final_symbols),
                        time_range={"start": "N/A", "end": "N/A"},
                        market_phase_distribution={}
                    )

                    empty_quality = SamplingQuality(
                        time_separation_score=0.0,
                        symbol_diversity_score=0.0,
                        market_phase_balance=0.0,
                        overall_quality_score=0.0,
                        warnings=["No cases found"]
                    )

                    result_data = SearchResultData(
                        cases=[],
                        summary=empty_summary,
                        sampling_quality=empty_quality,
                        execution_time=0.0,
                        cache_used=False,
                        search_config=None
                    )
                    self.task_manager.set_task_result(task_id, result_data)
                    self.task_manager.update_task_status(task_id, TaskStatusEnum.COMPLETED)
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
                        
                        # 安全獲取數值的輔助函數
                        def safe_float(value, default=None):
                            if value is None or (isinstance(value, str) and value.lower() in ['n/a', 'null', 'none']):
                                return default
                            try:
                                if isinstance(value, str) and value.endswith('%'):
                                    return float(value[:-1]) / 100  # 轉換百分比字符串
                                return float(value) if value is not None else default
                            except (ValueError, TypeError):
                                return default
                        
                        def safe_int(value, default=None):
                            if value is None:
                                return default
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return default
                        
                        def safe_str(value, default=None):
                            if value is None:
                                return default
                            return str(value)
                        
                        # 創建完整的 CaseData 對象，包含所有新參數
                        case_data = CaseData(
                            symbol=case_dict['symbol'],
                            timestamp=datetime.strptime(case_dict['timestamp'], '%Y-%m-%d %H:%M:%S'),
                            trigger_idx=case_dict.get('trigger_idx', 0),
                            # 單一正例搜索：明確標記為正例
                            positive_case=True,
                            
                            # OHLC 數據
                            open=case_dict['open'],
                            high=case_dict['high'],
                            low=case_dict['low'],
                            close=case_dict['close'],
                            volume=case_dict.get('volume', 1000000),
                            price_change=safe_float(case_dict.get('price_change'), 0.05),
                            market_phase=case_dict.get('market_phase', 'NEUTRAL'),
                            
                            # ===== 新增：基礎觸發條件參數 =====
                            timeframe=safe_str(case_dict.get('timeframe')),
                            closing_strength=safe_float(case_dict.get('closing_strength')),
                            price_position=safe_float(case_dict.get('price_position')),
                            volume_multiplier=safe_float(case_dict.get('volume_multiplier')),
                            taker_buy_ratio=safe_float(case_dict.get('taker_buy_ratio')),
                            
                            # ===== 新增：未來收益參數 (1-12根K線) =====
                            future_1bar_return=safe_float(case_dict.get('future_1bar_return')),
                            future_2bar_return=safe_float(case_dict.get('future_2bar_return')),
                            future_3bar_return=safe_float(case_dict.get('future_3bar_return')),
                            future_4bar_return=safe_float(case_dict.get('future_4bar_return')),
                            future_5bar_return=safe_float(case_dict.get('future_5bar_return')),
                            future_6bar_return=safe_float(case_dict.get('future_6bar_return')),
                            future_7bar_return=safe_float(case_dict.get('future_7bar_return')),
                            future_8bar_return=safe_float(case_dict.get('future_8bar_return')),
                            future_9bar_return=safe_float(case_dict.get('future_9bar_return')),
                            future_10bar_return=safe_float(case_dict.get('future_10bar_return')),
                            future_11bar_return=safe_float(case_dict.get('future_11bar_return')),
                            future_12bar_return=safe_float(case_dict.get('future_12bar_return')),
                            
                            # ===== 新增：未來回撤參數 (1-12根K線) =====
                            future_1bar_max_drawdown=safe_float(case_dict.get('future_1bar_max_drawdown')),
                            future_2bar_max_drawdown=safe_float(case_dict.get('future_2bar_max_drawdown')),
                            future_3bar_max_drawdown=safe_float(case_dict.get('future_3bar_max_drawdown')),
                            future_4bar_max_drawdown=safe_float(case_dict.get('future_4bar_max_drawdown')),
                            future_5bar_max_drawdown=safe_float(case_dict.get('future_5bar_max_drawdown')),
                            future_6bar_max_drawdown=safe_float(case_dict.get('future_6bar_max_drawdown')),
                            future_7bar_max_drawdown=safe_float(case_dict.get('future_7bar_max_drawdown')),
                            future_8bar_max_drawdown=safe_float(case_dict.get('future_8bar_max_drawdown')),
                            future_9bar_max_drawdown=safe_float(case_dict.get('future_9bar_max_drawdown')),
                            future_10bar_max_drawdown=safe_float(case_dict.get('future_10bar_max_drawdown')),
                            future_11bar_max_drawdown=safe_float(case_dict.get('future_11bar_max_drawdown')),
                            future_12bar_max_drawdown=safe_float(case_dict.get('future_12bar_max_drawdown')),
                            
                            # ===== 新增：時間描述參數 =====
                            hour_of_day=safe_int(case_dict.get('hour_of_day')),
                            day_of_week=safe_int(case_dict.get('day_of_week')),

                            # ===== 改寫：分類特徵參數 (9個) =====
                            # 數值參數（3個）
                            past_3day_max_volatility=safe_float(case_dict.get('past_3day_max_volatility')),
                            past_3day_direction=safe_float(case_dict.get('past_3day_direction')),
                            past_3day_volume_cv=safe_float(case_dict.get('past_3day_volume_cv')),

                            # 分類參數（6個）
                            volatility_class=safe_str(case_dict.get('volatility_class')),
                            direction_class=safe_str(case_dict.get('direction_class')),
                            volume_class=safe_str(case_dict.get('volume_class')),
                            market_class=safe_str(case_dict.get('market_class')),
                            market_class_name=safe_str(case_dict.get('market_class_name')),
                            difficulty_level=safe_str(case_dict.get('difficulty_level')),

                            # ===== 向後兼容的現有參數 =====
                            future1_close_return=safe_float(case_dict.get('future1_close_return')),
                            future2_close_return=safe_float(case_dict.get('future2_close_return')),
                            future4_close_return=safe_float(case_dict.get('future4_close_return')),
                            future6_close_return=safe_float(case_dict.get('future6_close_return')),
                            future24_close_return=safe_float(case_dict.get('future24_close_return')),
                            future48_close_return=safe_float(case_dict.get('future48_close_return')),
                            future72_close_return=safe_float(case_dict.get('future72_close_return')),
                            future_max_return=safe_float(case_dict.get('future_max_return')),
                            future_max_drawdown=safe_float(case_dict.get('future_max_drawdown')),
                            future72_max_return=safe_float(case_dict.get('future72_max_return')),
                            future72_max_drawdown=safe_float(case_dict.get('future72_max_drawdown')),
                            future24_close=safe_float(case_dict.get('future24_close')),
                            future24_low=safe_float(case_dict.get('future24_low')),
                            prior_volatility=safe_float(case_dict.get('prior_volatility')),
                            prior_range=safe_float(case_dict.get('prior_range')),
                            prior_abs_change_sum=safe_float(case_dict.get('prior_abs_change_sum')),
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
                    info_msg = "Search completed: All cases filtered out during data validation"
                    self.logger.info(info_msg)
                    # 所有案例被過濾也不是失敗，而是成功完成但結果為空
                    empty_summary = CaseSummary(
                        total_cases=0,
                        positive_cases=0,
                        negative_cases=0,
                        unique_symbols=len(final_symbols),
                        time_range={"start": "N/A", "end": "N/A"},
                        market_phase_distribution={}
                    )

                    empty_quality = SamplingQuality(
                        time_separation_score=0.0,
                        symbol_diversity_score=0.0,
                        market_phase_balance=0.0,
                        overall_quality_score=0.0,
                        warnings=["All cases filtered out"]
                    )

                    result_data = SearchResultData(
                        cases=[],
                        summary=empty_summary,
                        sampling_quality=empty_quality,
                        execution_time=0.0,
                        cache_used=False,
                        search_config=None
                    )
                    self.task_manager.set_task_result(task_id, result_data)
                    self.task_manager.update_task_status(task_id, TaskStatusEnum.COMPLETED)
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
            
            # Generate summary - 使用 positive_case 標記而不是 future4_close_return
            positive_cases = len([c for c in real_cases if getattr(c, 'positive_case', False) is True])
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
                        "start": request.start_date,
                        "end": request.end_date
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
                cache_used=False,
                # 添加搜索配置信息，包含timeframe
                search_config={
                    "timeframe": request.timeframe,
                    "name": request.name,
                    "description": request.description,
                    "start_date": request.start_date,
                    "end_date": request.end_date
                },
                symbols_processed=symbols,
                total_cases=len(real_cases),
                positive_cases_count=positive_cases,
                negative_cases_count=negative_cases
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
        # Ensure momentum modules are loaded before preview
        if not self._ensure_momentum_loaded():
            raise SearchExecutionException("Momentum modules could not be loaded")
            
        try:
            # Try to get real symbol list
            all_symbols = await asyncio.to_thread(self.data_loader.get_symbols_list)
            valid_symbols = [s for s in all_symbols[:symbols_limit] if s.endswith('USDT')]
            self.logger.info("Using real symbol list for preview")
            
            # Calculate estimates more accurately
            estimated_cases = min(request.sample_limit, len(valid_symbols) * 5)
            estimated_time = max(2.0, len(valid_symbols) * 1.5)  # 至少2秒，每個symbol大約1.5秒
            
            # Generate preview data with correct format
            preview_data = {
                "estimated_cases": estimated_cases,
                "estimated_execution_time": round(estimated_time, 1),  # 確保是數字
                "symbols_to_process": valid_symbols[:10],  # 限制返回的symbol數量
                "potential_issues": self._check_potential_issues(request, valid_symbols)
            }
            
            return preview_data
        except Exception as e:
            self.logger.error(f"Preview failed: {str(e)}")
            # 如果無法獲取真實數據，返回預設值
            return {
                "estimated_cases": min(request.sample_limit, 50),
                "estimated_execution_time": 10.0,  # 數字而不是字符串
                "symbols_to_process": ["BTCUSDT", "ETHUSDT"],  # 預設值
                "potential_issues": ["Unable to fetch real symbol list"]
            }
    def _check_potential_issues(self, request: SearchConfigRequest, 
                           symbols: List[str]) -> List[str]:
        """檢查潛在問題"""
        issues = []
        
        # 檢查條件數量
        if not request.initial_conditions:
            issues.append("No initial conditions specified")
        
        if len(request.initial_conditions) > 5:
            issues.append("Too many conditions may result in very few matches")
        
        # 檢查時間範圍
        if request.time_range:
            start_date = datetime.fromisoformat(request.time_range[0])
            end_date = datetime.fromisoformat(request.time_range[1])
            days_diff = (end_date - start_date).days
            
            if days_diff < 30:
                issues.append("Short time range may limit results")
            elif days_diff > 365:
                issues.append("Long time range may slow down search")
        
        # 檢查symbol數量
        if len(symbols) < 5:
            issues.append("Few symbols available for search")
        
        # 檢查sample_limit
        if request.sample_limit > 1000:
            issues.append("Large sample limit may increase processing time")
        
        return issues
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status"""
        return self.task_manager.get_task_status(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[SearchResultData]:
        """Get task result"""
        result_data = self.task_manager.get_task_result(task_id)
        
        # 為正例搜索結果自動添加 positive_case 標記
        if result_data and result_data.cases:
            for case in result_data.cases:
                # 處理不同的案例數據格式
                if hasattr(case, '__dict__'):
                    case.__dict__['positive_case'] = True
                elif isinstance(case, dict):
                    case['positive_case'] = True
        
        return result_data
    
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