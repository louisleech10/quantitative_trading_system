# 增強文件: api/services/task_manager.py

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading
import json
from pathlib import Path

from ..core.config import settings
from ..core.logging import get_logger
from ..models.responses import SearchResultData

class TaskStatusEnum(str, Enum):
    """任務狀態枚舉"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class TaskTypeEnum(str, Enum):
    """任務類型枚舉"""
    POSITIVE_SEARCH = "positive_search"
    NEGATIVE_SEARCH = "negative_search"
    COMBINED_SEARCH = "combined_search"
    DATA_EXPORT = "data_export"

@dataclass
class TaskProgress:
    """任務進度信息"""
    current_step: int = 0
    total_steps: int = 100
    step_description: str = "初始化中..."
    percentage: float = 0.0
    estimated_remaining_seconds: Optional[float] = None
    processed_symbols: List[str] = field(default_factory=list)
    current_symbol: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def update(self, current: int, total: int = None, description: str = None,
               symbol: str = None, error: str = None, warning: str = None):
        """更新進度信息"""
        self.current_step = current
        if total is not None:
            self.total_steps = total
        if description:
            self.step_description = description
        if symbol:
            self.current_symbol = symbol
            if symbol not in self.processed_symbols:
                self.processed_symbols.append(symbol)
        if error:
            self.errors.append(f"{datetime.now().isoformat()}: {error}")
        if warning:
            self.warnings.append(f"{datetime.now().isoformat()}: {warning}")
        
        # 計算百分比
        self.percentage = (self.current_step / self.total_steps * 100) if self.total_steps > 0 else 0.0

@dataclass
class TaskInfo:
    """完整的任務信息"""
    task_id: str
    task_type: TaskTypeEnum
    name: str
    status: TaskStatusEnum
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Optional[SearchResultData] = None
    error_message: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None  # 用於反例搜索關聯正例搜索
    child_task_ids: List[str] = field(default_factory=list)  # 子任務列表
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """計算任務執行時間"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    @property
    def is_active(self) -> bool:
        """檢查任務是否正在活躍執行"""
        return self.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING, TaskStatusEnum.PAUSED]

class EnhancedTaskManager:
    """增強版任務管理器"""
    
    def __init__(self):
        self.logger = get_logger("api.enhanced_task_manager")
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = threading.RLock()
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._cleanup_interval = 3600  # 1小時清理一次
        self._max_task_age = 86400  # 24小時後清理完成的任務
        
        # 啟動後台清理任務
        asyncio.create_task(self._periodic_cleanup())
        
        # 任務持久化設置
        self.persistence_enabled = True
        self.tasks_file = settings.logs_path / "tasks.json"
        
        # 載入持久化任務
        self._load_tasks_from_file()
    
    def create_task(self, name: str, task_type: TaskTypeEnum = TaskTypeEnum.POSITIVE_SEARCH,
                   config: Dict[str, Any] = None, parent_task_id: str = None) -> str:
        """創建新任務"""
        task_id = str(uuid.uuid4())
        
        with self._lock:
            task_info = TaskInfo(
                task_id=task_id,
                task_type=task_type,
                name=name,
                status=TaskStatusEnum.PENDING,
                created_at=datetime.now(),
                config=config or {},
                parent_task_id=parent_task_id
            )
            
            self._tasks[task_id] = task_info
            
            # 如果有父任務，更新父任務的子任務列表
            if parent_task_id and parent_task_id in self._tasks:
                self._tasks[parent_task_id].child_task_ids.append(task_id)
            
            self.logger.info(f"Created task {task_id}: {name} (type: {task_type.value})")
            
            # 持久化
            if self.persistence_enabled:
                self._save_tasks_to_file()
        
        return task_id
    
    def update_task_status(self, task_id: str, status: TaskStatusEnum,
                          error_message: str = None, result: SearchResultData = None):
        """更新任務狀態"""
        with self._lock:
            if task_id not in self._tasks:
                self.logger.warning(f"Task {task_id} not found for status update")
                return False
            
            task = self._tasks[task_id]
            old_status = task.status
            task.status = status
            
            # 更新時間戳
            if status == TaskStatusEnum.RUNNING and not task.started_at:
                task.started_at = datetime.now()
            elif status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]:
                task.completed_at = datetime.now()
            
            # 更新錯誤信息和結果
            if error_message:
                task.error_message = error_message
                task.progress.update(
                    current=task.progress.current_step,
                    description=f"錯誤: {error_message}",
                    error=error_message
                )
            
            if result:
                task.result = result
                task.progress.update(
                    current=task.progress.total_steps,
                    description="任務完成"
                )
            
            self.logger.info(f"Task {task_id} status: {old_status} -> {status}")
            
            # 觸發進度回調
            self._notify_progress_callbacks(task_id, task)
            
            # 持久化
            if self.persistence_enabled:
                self._save_tasks_to_file()
        
        return True
    
    def update_task_progress(self, task_id: str, current: int, total: int = None,
                           description: str = None, symbol: str = None,
                           error: str = None, warning: str = None,
                           estimated_remaining: float = None):
        """更新任務進度"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            task.progress.update(
                current=current,
                total=total,
                description=description,
                symbol=symbol,
                error=error,
                warning=warning
            )
            
            if estimated_remaining is not None:
                task.progress.estimated_remaining_seconds = estimated_remaining
            
            # 觸發進度回調
            self._notify_progress_callbacks(task_id, task)
        
        return True
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """獲取任務狀態"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[SearchResultData]:
        """獲取任務結果"""
        with self._lock:
            task = self._tasks.get(task_id)
            return task.result if task else None
    
    def list_tasks(self, status_filter: List[TaskStatusEnum] = None,
                  task_type_filter: List[TaskTypeEnum] = None,
                  limit: int = 50) -> List[TaskInfo]:
        """列出任務"""
        with self._lock:
            tasks = list(self._tasks.values())
            
            # 狀態過濾
            if status_filter:
                tasks = [t for t in tasks if t.status in status_filter]
            
            # 類型過濾
            if task_type_filter:
                tasks = [t for t in tasks if t.task_type in task_type_filter]
            
            # 按創建時間排序（最新的在前）
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            return tasks[:limit]
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING, TaskStatusEnum.PAUSED]:
                task.status = TaskStatusEnum.CANCELLED
                task.completed_at = datetime.now()
                task.progress.update(
                    current=task.progress.current_step,
                    description="任務已取消"
                )
                
                self.logger.info(f"Task {task_id} cancelled")
                
                # 觸發回調
                self._notify_progress_callbacks(task_id, task)
                
                # 持久化
                if self.persistence_enabled:
                    self._save_tasks_to_file()
                
                return True
        
        return False
    
    def pause_task(self, task_id: str) -> bool:
        """暫停任務"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            if task.status == TaskStatusEnum.RUNNING:
                task.status = TaskStatusEnum.PAUSED
                task.progress.update(
                    current=task.progress.current_step,
                    description="任務已暫停"
                )
                
                self.logger.info(f"Task {task_id} paused")
                return True
        
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢復任務"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            if task.status == TaskStatusEnum.PAUSED:
                task.status = TaskStatusEnum.RUNNING
                task.progress.update(
                    current=task.progress.current_step,
                    description="任務已恢復"
                )
                
                self.logger.info(f"Task {task_id} resumed")
                return True
        
        return False
    
    def register_progress_callback(self, task_id: str, callback: Callable):
        """註冊進度回調函數"""
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)
    
    def _notify_progress_callbacks(self, task_id: str, task_info: TaskInfo):
        """通知進度回調"""
        if task_id in self._progress_callbacks:
            for callback in self._progress_callbacks[task_id]:
                try:
                    callback(task_info)
                except Exception as e:
                    self.logger.error(f"Progress callback error: {str(e)}")
    
    async def _periodic_cleanup(self):
        """定期清理過期任務"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_old_tasks()
            except Exception as e:
                self.logger.error(f"Cleanup error: {str(e)}")
    
    async def cleanup_old_tasks(self):
        """清理舊任務"""
        cutoff_time = datetime.now() - timedelta(seconds=self._max_task_age)
        tasks_to_remove = []
        
        with self._lock:
            for task_id, task in self._tasks.items():
                # 只清理已完成/失敗/取消的任務，且超過保留期限
                if (task.status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED] 
                    and task.completed_at and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            # 移除任務
            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                # 清理回調
                if task_id in self._progress_callbacks:
                    del self._progress_callbacks[task_id]
            
            if tasks_to_remove:
                self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
                
                # 更新持久化文件
                if self.persistence_enabled:
                    self._save_tasks_to_file()
    
    def _save_tasks_to_file(self):
        """保存任務到文件"""
        try:
            tasks_data = {}
            for task_id, task in self._tasks.items():
                # 只保存關鍵信息，不保存結果數據（太大）
                tasks_data[task_id] = {
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "name": task.name,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat(),
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error_message": task.error_message,
                    "config": task.config,
                    "parent_task_id": task.parent_task_id,
                    "child_task_ids": task.child_task_ids,
                    "progress": {
                        "current_step": task.progress.current_step,
                        "total_steps": task.progress.total_steps,
                        "step_description": task.progress.step_description,
                        "percentage": task.progress.percentage,
                        "processed_symbols": task.progress.processed_symbols,
                        "current_symbol": task.progress.current_symbol,
                        "errors": task.progress.errors[-10:],  # 只保存最近10個錯誤
                        "warnings": task.progress.warnings[-10:]  # 只保存最近10個警告
                    }
                }
            
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Failed to save tasks to file: {str(e)}")
    
    def _load_tasks_from_file(self):
        """從文件載入任務"""
        try:
            if not self.tasks_file.exists():
                return
            
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
            
            for task_id, data in tasks_data.items():
                # 重建TaskInfo對象
                progress = TaskProgress(
                    current_step=data["progress"]["current_step"],
                    total_steps=data["progress"]["total_steps"],
                    step_description=data["progress"]["step_description"],
                    percentage=data["progress"]["percentage"],
                    processed_symbols=data["progress"]["processed_symbols"],
                    current_symbol=data["progress"]["current_symbol"],
                    errors=data["progress"]["errors"],
                    warnings=data["progress"]["warnings"]
                )
                
                task_info = TaskInfo(
                    task_id=data["task_id"],
                    task_type=TaskTypeEnum(data["task_type"]),
                    name=data["name"],
                    status=TaskStatusEnum(data["status"]),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
                    completed_at=datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None,
                    progress=progress,
                    error_message=data["error_message"],
                    config=data["config"],
                    parent_task_id=data["parent_task_id"],
                    child_task_ids=data["child_task_ids"]
                )
                
                self._tasks[task_id] = task_info
            
            self.logger.info(f"Loaded {len(tasks_data)} tasks from persistence file")
            
        except Exception as e:
            self.logger.error(f"Failed to load tasks from file: {str(e)}")

# 全局任務管理器實例
enhanced_task_manager = EnhancedTaskManager()

# 修改文件: api/services/case_search_integration_service.py
"""
案例搜索整合服務 - 整合現有搜索引擎到API服務
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.config import settings
from ..core.logging import get_logger
from ..models.requests import SearchConfigRequest
from ..models.responses import SearchResultData, CaseData
from ..utils.exceptions import SearchExecutionException
from .task_manager import enhanced_task_manager, TaskStatusEnum, TaskTypeEnum

# 動態導入momentum模組
project_root = Path(__file__).parent.parent.parent

class CaseSearchIntegrationService:
    """案例搜索整合服務"""
    
    def __init__(self):
        self.logger = get_logger("api.case_search_integration")
        self.momentum_available = False
        self.search_engine = None
        self.data_loader = None
        
        # 延遲載入momentum模組
        self._load_momentum_modules()
    
    def _load_momentum_modules(self):
        """載入momentum模組"""
        try:
            # 添加momentum路徑
            momentum_paths = [
                project_root / "momentum",
                project_root / "momentum" / "DataExtraction",
            ]
            
            for path in momentum_paths:
                if str(path) not in sys.path:
                    sys.path.insert(0, str(path))
            
            # 導入模組
            from momentum.factories import (
                create_case_search_engine,
                create_filter_condition,
                create_momentum_data_loader,
                create_search_configuration,
            )
            
            # 創建實例
            self.data_loader = create_momentum_data_loader()
            self.search_engine = create_case_search_engine(self.data_loader)
            self.momentum_available = True
            
            self.logger.info("✅ Momentum modules loaded successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load momentum modules: {str(e)}")
            self.momentum_available = False
    
    async def execute_search_with_progress(self, request: SearchConfigRequest,
                                         symbols: Optional[List[str]] = None) -> str:
        """執行搜索並提供詳細進度追蹤"""
        if not self.momentum_available:
            raise SearchExecutionException("Momentum search engine not available")
        
        # 創建任務
        task_id = enhanced_task_manager.create_task(
            name=request.name,
            task_type=TaskTypeEnum.POSITIVE_SEARCH,
            config=request.dict()
        )
        
        # 異步執行搜索
        asyncio.create_task(self._run_search_with_progress(task_id, request, symbols))
        
        return task_id
    
    async def _run_search_with_progress(self, task_id: str, request: SearchConfigRequest,
                                      symbols: Optional[List[str]] = None):
        """執行搜索並更新進度"""
        try:
            # 更新狀態為執行中
            enhanced_task_manager.update_task_status(task_id, TaskStatusEnum.RUNNING)
            
            # 步驟1: 準備搜索配置
            enhanced_task_manager.update_task_progress(
                task_id, current=1, total=10, description="準備搜索配置..."
            )
            
            search_config = await self._convert_request_to_config(request)
            
            # 步驟2: 獲取交易對列表
            enhanced_task_manager.update_task_progress(
                task_id, current=2, description="獲取交易對列表..."
            )
            
            if not symbols:
                symbols = await asyncio.to_thread(self.data_loader.get_symbols_list)
                symbols = [s for s in symbols[:50] if s.endswith('USDT')]  # 限制數量
            
            # 步驟3-8: 執行搜索（每個symbol一個進度更新）
            total_symbols = len(symbols)
            all_cases = []
            
            for i, symbol in enumerate(symbols):
                if enhanced_task_manager.get_task_status(task_id).status == TaskStatusEnum.CANCELLED:
                    return
                
                current_step = 3 + int((i / total_symbols) * 5)  # 步驟3-8
                enhanced_task_manager.update_task_progress(
                    task_id, 
                    current=current_step, 
                    description=f"搜索 {symbol}...",
                    symbol=symbol
                )
                
                try:
                    # 執行單個symbol的搜索
                    symbol_cases = await asyncio.to_thread(
                        self.search_engine.search_cases,
                        config=search_config,
                        symbols=[symbol],
                        batch_size=1,
                        save_results=False
                    )
                    
                    if symbol_cases:
                        processed_cases = await self._process_raw_cases(symbol_cases, symbol)
                        all_cases.extend(processed_cases)
                        
                        enhanced_task_manager.update_task_progress(
                            task_id,
                            current=current_step,
                            description=f"✅ {symbol}: 找到 {len(processed_cases)} 個案例"
                        )
                    else:
                        enhanced_task_manager.update_task_progress(
                            task_id,
                            current=current_step,
                            description=f"⚪ {symbol}: 無符合條件的案例"
                        )
                
                except Exception as e:
                    enhanced_task_manager.update_task_progress(
                        task_id,
                        current=current_step,
                        description=f"❌ {symbol}: 搜索失敗",
                        error=f"Symbol {symbol} search failed: {str(e)}"
                    )
            
            # 步驟9: 處理結果
            enhanced_task_manager.update_task_progress(
                task_id, current=9, description="處理搜索結果..."
            )
            
            if all_cases:
                result_data = SearchResultData(
                    cases=all_cases,
                    total_cases=len(all_cases),
                    search_config=request.dict(),
                    execution_time=enhanced_task_manager.get_task_status(task_id).duration_seconds or 0,
                    symbols_processed=symbols
                )
                
                # 步驟10: 完成
                enhanced_task_manager.update_task_progress(
                    task_id, current=10, description=f"搜索完成! 找到 {len(all_cases)} 個案例"
                )
                
                enhanced_task_manager.update_task_status(
                    task_id, TaskStatusEnum.COMPLETED, result=result_data
                )
                
                self.logger.info(f"Search {task_id} completed with {len(all_cases)} cases")
            else:
                enhanced_task_manager.update_task_status(
                    task_id, TaskStatusEnum.FAILED, 
                    error_message="No cases found matching the criteria"
                )
        
        except Exception as e:
            self.logger.error(f"Search {task_id} failed: {str(e)}")
            enhanced_task_manager.update_task_status(
                task_id, TaskStatusEnum.FAILED, error_message=str(e)
            )
    
    async def _convert_request_to_config(self, request: SearchConfigRequest):
        """轉換API請求為搜索配置"""
        # 導入SearchConfiguration和FilterCondition
        from momentum.factories import create_filter_condition, create_search_configuration
        
        config = create_search_configuration(
            name=request.name,
            description=request.description,
            timeframe=request.timeframe.value if hasattr(request.timeframe, 'value') else request.timeframe,
            lookback_periods=request.lookback_periods,
            forward_periods=request.forward_periods,
            time_range=request.time_range,
            sample_limit=request.sample_limit,
            min_volume=request.min_volume,
            exclude_new_listing_days=request.exclude_new_listing_days
        )
        
        # 添加初始條件
        for condition_req in request.initial_conditions:
            condition = create_filter_condition(
                condition_type=condition_req.condition_type.value if hasattr(condition_req.condition_type, 'value') else condition_req.condition_type,
                parameter=condition_req.parameter,
                operator=condition_req.operator.value if hasattr(condition_req.operator, 'value') else condition_req.operator,
                value=condition_req.value,
                description=condition_req.description
            )
            config.add_initial_condition(condition)
        
        # 添加高級條件
        for condition_req in request.advanced_conditions:
            condition = create_filter_condition(
                condition_type=condition_req.condition_type.value if hasattr(condition_req.condition_type, 'value') else condition_req.condition_type,
                parameter=condition_req.parameter,
                operator=condition_req.operator.value if hasattr(condition_req.operator, 'value') else condition_req.operator,
                value=condition_req.value,
                description=condition_req.description
            )
            config.add_advanced_condition(condition)
        
        # 手動添加 time_range 屬性以確保兼容性（參照測試腳本）
        if request.time_range:
            config.time_range = request.time_range
        
        # 確保有預設條件（如果沒有提供任何條件的話）
        if not request.initial_conditions and not request.advanced_conditions:
            # 添加預設的價格變化條件（參照測試腳本）
            default_condition = create_filter_condition(
                condition_type="price",
                parameter="price_change", 
                operator=">=",
                value=0.03,  # 3%漲幅（與測試腳本一致）
                description="預設價格漲幅條件"
            )
            config.add_initial_condition(default_condition)
        
        return config
    
    async def _process_raw_cases(self, raw_cases: List[Dict], symbol: str) -> List[CaseData]:
        """處理原始案例數據為CaseData對象"""
        processed_cases = []
        
        for case_dict in raw_cases:
            try:
                # 安全獲取數值
                def safe_float(value, default=0.0):
                    if value is None:
                        return default
                    if isinstance(value, str):
                        if value.lower() in ['n/a', 'null', 'none', '']:
                            return default
                        if value.endswith('%'):
                            return float(value[:-1]) / 100
                    return float(value)
                
                # 創建CaseData對象
                case_data = CaseData(
                    symbol=case_dict.get('symbol', symbol),
                    timestamp=case_dict.get('timestamp', datetime.now().isoformat()),
                    open=safe_float(case_dict.get('open')),
                    high=safe_float(case_dict.get('high')),
                    low=safe_float(case_dict.get('low')),
                    close=safe_float(case_dict.get('close')),
                    volume=safe_float(case_dict.get('volume')),
                    case_type=1,  # 正例
                    # 價格變化指標
                    price_change=safe_float(case_dict.get('price_change')),
                    price_change_pct=safe_float(case_dict.get('price_change_pct')),
                    # 成交量指標
                    volume_ratio=safe_float(case_dict.get('volume_ratio')),
                    taker_buy_ratio=safe_float(case_dict.get('taker_buy_ratio')),
                    # 技術指標
                    rsi=safe_float(case_dict.get('rsi')),
                    macd=safe_float(case_dict.get('macd')),
                    # 市場環境
                    market_phase=case_dict.get('market_phase', 'unknown'),
                    hour_of_day=case_dict.get('hour_of_day', 0),
                    day_of_week=case_dict.get('day_of_week', 0),
                    # 未來表現（如果有的話）
                    future_return_1h=safe_float(case_dict.get('future_return_1h')),
                    future_return_24h=safe_float(case_dict.get('future_return_24h')),
                    future_return_72h=safe_float(case_dict.get('future_return_72h'))
                )
                
                processed_cases.append(case_data)
                
            except Exception as e:
                self.logger.warning(f"Failed to process case data: {str(e)}")
                continue
        
        return processed_cases

# 創建全局服務實例
case_search_integration = CaseSearchIntegrationService()

# 修改 api/main.py 添加新路由

# 在 api/main.py 中添加以下導入和路由註冊
# from api.routes.two_stage_search import router as two_stage_router
# app.include_router(two_stage_router, prefix=settings.api_prefix)