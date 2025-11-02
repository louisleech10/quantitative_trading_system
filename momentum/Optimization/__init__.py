"""
Optimization模塊 - Optuna參數優化系統

本模塊提供策略參數的自動優化功能,使用Optuna框架搜索最佳參數組合。

核心組件:
- OptunaOptimizer: Optuna優化引擎核心類
- CheckpointManager: 斷點續跑管理器
- ErrorHandler: 錯誤處理與重試機制
- ProgressMonitor: 進度監控與通知系統

Author: Claude (Phase 3.5)
Date: 2025-11-02
"""

from .optuna_optimizer import OptunaOptimizer, ParameterRanges, OptimizationResult
from .checkpoint_manager import CheckpointManager
from .error_handler import OptimizationErrorHandler, ErrorType

__all__ = [
    'OptunaOptimizer',
    'ParameterRanges',
    'OptimizationResult',
    'CheckpointManager',
    'OptimizationErrorHandler',
    'ErrorType'
]
