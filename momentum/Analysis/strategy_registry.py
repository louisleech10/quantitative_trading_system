"""
策略註冊中心 - 動態策略管理系統

此模組提供策略註冊、查詢、驗證和動態載入功能。
通過策略註冊系統，可以從 YAML 配置文件載入策略元數據，
並動態導入策略計算函數，實現完全配置驅動的架構。

Author: Claude (Phase 1 - Dynamic Parameters Refactoring)
Date: 2025-12-03
"""

import importlib
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from functools import lru_cache

from momentum.Optimization.strategy_metadata import (
    StrategyMetadata,
    ParameterDefinition,
    ParameterType,
    ConstraintType,
    ValidationResult,
    StrategyCalculator,
    StrategyValidator
)
from api.core.logging import get_logger

logger = get_logger("strategy_registry")


class StrategyRegistry:
    """
    策略註冊中心（單例模式）

    負責：
    1. 從 YAML 配置文件載入策略元數據
    2. 動態導入策略計算函數和驗證函數
    3. 提供策略查詢和參數驗證服務
    4. 緩存策略元數據和函數引用，提高性能
    """

    _instance: Optional['StrategyRegistry'] = None
    _initialized: bool = False

    # 策略元數據緩存
    _strategies: Dict[str, StrategyMetadata] = {}

    # 函數緩存
    _calculators: Dict[str, StrategyCalculator] = {}
    _validators: Dict[str, Optional[StrategyValidator]] = {}

    def __new__(cls) -> 'StrategyRegistry':
        """單例模式：確保只有一個實例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化註冊中心（只執行一次）"""
        if not self._initialized:
            self._load_strategies_from_yaml()
            StrategyRegistry._initialized = True

    def _load_strategies_from_yaml(self):
        """從 YAML 配置文件載入所有策略定義"""
        try:
            # 查找配置文件
            config_path = self._find_config_file()

            logger.info(f"Loading strategies from {config_path}")

            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'strategies' not in data:
                logger.warning("No strategies found in config file")
                return

            # 載入每個策略
            for strategy_id, config in data['strategies'].items():
                try:
                    # 創建 StrategyMetadata 實例
                    metadata = StrategyMetadata(
                        strategy_id=strategy_id,
                        **config
                    )

                    # 緩存元數據
                    self._strategies[strategy_id] = metadata

                    # 動態載入計算函數
                    calculator = self._import_function(
                        metadata.calculator_module,
                        metadata.calculator_function
                    )
                    self._calculators[strategy_id] = calculator

                    # 動態載入驗證函數（如果有）
                    if metadata.validator_module and metadata.validator_function:
                        validator = self._import_function(
                            metadata.validator_module,
                            metadata.validator_function
                        )
                        self._validators[strategy_id] = validator
                    else:
                        self._validators[strategy_id] = None

                    logger.info(
                        f"Loaded strategy: {strategy_id} "
                        f"({metadata.display_name})"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to load strategy '{strategy_id}': {e}",
                        exc_info=True
                    )

            logger.info(
                f"Strategy registry initialized with "
                f"{len(self._strategies)} strategies"
            )

        except Exception as e:
            logger.error(
                f"Failed to load strategies from YAML: {e}",
                exc_info=True
            )
            raise

    def _find_config_file(self) -> Path:
        """查找策略配置文件"""
        # 嘗試多個可能的位置
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "strategies.yaml",
            Path(__file__).parent.parent / "config" / "strategies.yaml",
            Path.cwd() / "config" / "strategies.yaml",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        raise FileNotFoundError(
            f"Could not find strategies.yaml in any of: "
            f"{[str(p) for p in possible_paths]}"
        )

    def _import_function(
        self,
        module_path: str,
        function_name: str
    ) -> Callable:
        """
        動態導入函數

        Args:
            module_path: 模組路徑（如 'momentum.Analysis.strategies.three_line_strategy'）
            function_name: 函數名稱（如 'calculate_signals'）

        Returns:
            函數對象

        Raises:
            ImportError: 如果模組或函數不存在
        """
        try:
            module = importlib.import_module(module_path)
            function = getattr(module, function_name)
            return function
        except ImportError as e:
            raise ImportError(
                f"Failed to import module '{module_path}': {e}"
            )
        except AttributeError as e:
            raise AttributeError(
                f"Function '{function_name}' not found in module "
                f"'{module_path}': {e}"
            )

    # ==================== 查詢 API ====================

    def get_strategy(self, strategy_id: str) -> StrategyMetadata:
        """
        獲取策略元數據

        Args:
            strategy_id: 策略ID

        Returns:
            策略元數據

        Raises:
            ValueError: 如果策略不存在
        """
        if strategy_id not in self._strategies:
            available = list(self._strategies.keys())
            raise ValueError(
                f"Strategy '{strategy_id}' not found. "
                f"Available strategies: {available}"
            )
        return self._strategies[strategy_id]

    def list_strategies(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[StrategyMetadata]:
        """
        列出所有策略（支援過濾）

        Args:
            category: 按分類過濾（trend/momentum/volatility）
            tags: 按標籤過濾

        Returns:
            策略元數據列表
        """
        strategies = list(self._strategies.values())

        # 按分類過濾
        if category:
            strategies = [s for s in strategies if s.category == category]

        # 按標籤過濾
        if tags:
            strategies = [
                s for s in strategies
                if any(tag in s.tags for tag in tags)
            ]

        return strategies

    def list_strategy_ids(self) -> List[str]:
        """列出所有策略 ID"""
        return list(self._strategies.keys())

    def strategy_exists(self, strategy_id: str) -> bool:
        """檢查策略是否存在"""
        return strategy_id in self._strategies

    # ==================== 函數獲取 API ====================

    def get_calculator(self, strategy_id: str) -> StrategyCalculator:
        """
        獲取策略計算函數

        Args:
            strategy_id: 策略ID

        Returns:
            計算函數（簽名：(kline_data, indicators, params) -> signals）

        Raises:
            ValueError: 如果策略不存在
        """
        if strategy_id not in self._calculators:
            raise ValueError(f"Calculator for '{strategy_id}' not found")
        return self._calculators[strategy_id]

    def get_validator(
        self,
        strategy_id: str
    ) -> Optional[StrategyValidator]:
        """
        獲取策略驗證函數（如果存在）

        Args:
            strategy_id: 策略ID

        Returns:
            驗證函數（簽名：(params) -> List[str]）或 None

        Raises:
            ValueError: 如果策略不存在
        """
        if strategy_id not in self._validators:
            raise ValueError(f"Strategy '{strategy_id}' not found")
        return self._validators[strategy_id]

    # ==================== 參數驗證 API ====================

    def validate_parameters(
        self,
        strategy_id: str,
        params: Dict[str, Any]
    ) -> ValidationResult:
        """
        驗證策略參數

        執行三層驗證：
        1. 基礎驗證：類型、範圍
        2. 約束驗證：參數間關係
        3. 自定義驗證：業務邏輯

        Args:
            strategy_id: 策略ID
            params: 參數字典

        Returns:
            ValidationResult 包含驗證結果和錯誤訊息
        """
        result = ValidationResult.success()

        try:
            metadata = self.get_strategy(strategy_id)

            # 1. 基礎驗證（類型、範圍）
            self._validate_basic(metadata, params, result)

            # 2. 約束驗證（參數間關係）
            if result.is_valid:
                self._validate_constraints(metadata, params, result)

            # 3. 自定義驗證（業務邏輯）
            if result.is_valid:
                validator = self.get_validator(strategy_id)
                if validator:
                    custom_errors = validator(params)
                    if custom_errors:
                        for error in custom_errors:
                            result.add_error(error)

        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            logger.error(
                f"Error validating parameters for {strategy_id}: {e}",
                exc_info=True
            )

        return result

    def _validate_basic(
        self,
        metadata: StrategyMetadata,
        params: Dict[str, Any],
        result: ValidationResult
    ):
        """基礎驗證：類型和範圍"""
        for param_def in metadata.parameters:
            param_name = param_def.name

            # 檢查參數是否存在
            if param_name not in params:
                result.add_error(
                    f"缺少必要參數: {param_def.display_name} ({param_name})"
                )
                continue

            value = params[param_name]

            # 類型驗證
            if param_def.type == ParameterType.INT:
                if not isinstance(value, int):
                    result.add_error(
                        f"{param_def.display_name} 必須是整數，當前值: {value}"
                    )
                    continue
            elif param_def.type == ParameterType.FLOAT:
                if not isinstance(value, (int, float)):
                    result.add_error(
                        f"{param_def.display_name} 必須是數字，當前值: {value}"
                    )
                    continue
            elif param_def.type == ParameterType.CATEGORICAL:
                if value not in param_def.choices:
                    result.add_error(
                        f"{param_def.display_name} 必須是以下值之一: "
                        f"{param_def.choices}，當前值: {value}"
                    )
                    continue

            # 範圍驗證（數值類型）
            if param_def.type in [ParameterType.INT, ParameterType.FLOAT]:
                if param_def.min_value is not None and value < param_def.min_value:
                    result.add_error(
                        f"{param_def.display_name} 不能小於 "
                        f"{param_def.min_value}，當前值: {value}"
                    )
                if param_def.max_value is not None and value > param_def.max_value:
                    result.add_error(
                        f"{param_def.display_name} 不能大於 "
                        f"{param_def.max_value}，當前值: {value}"
                    )

    def _validate_constraints(
        self,
        metadata: StrategyMetadata,
        params: Dict[str, Any],
        result: ValidationResult
    ):
        """約束驗證：參數間關係"""
        for param_def in metadata.parameters:
            param_name = param_def.name

            if param_name not in params:
                continue

            for constraint in param_def.constraints:
                target_name = constraint.target

                # 檢查目標參數是否存在
                if target_name not in params:
                    result.add_warning(
                        f"約束目標參數 '{target_name}' 不存在，跳過約束檢查"
                    )
                    continue

                # 檢查約束
                is_valid = self._check_constraint(
                    params[param_name],
                    params[target_name],
                    constraint.type
                )

                if not is_valid:
                    result.add_error(constraint.message)

    def _check_constraint(
        self,
        value: Any,
        target_value: Any,
        constraint_type: ConstraintType
    ) -> bool:
        """檢查單個約束是否滿足"""
        try:
            if constraint_type == ConstraintType.LESS_THAN:
                return value < target_value
            elif constraint_type == ConstraintType.LESS_THAN_OR_EQUAL:
                return value <= target_value
            elif constraint_type == ConstraintType.GREATER_THAN:
                return value > target_value
            elif constraint_type == ConstraintType.GREATER_THAN_OR_EQUAL:
                return value >= target_value
            elif constraint_type == ConstraintType.EQUAL:
                return value == target_value
            elif constraint_type == ConstraintType.NOT_EQUAL:
                return value != target_value
            else:
                logger.warning(f"Unknown constraint type: {constraint_type}")
                return True
        except Exception as e:
            logger.error(f"Error checking constraint: {e}")
            return False

    # ==================== 工具方法 ====================

    def get_parameter_ranges(
        self,
        strategy_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        獲取策略的參數範圍（用於 Optuna 採樣）

        Returns:
            {
                'param_name': {
                    'type': 'int',
                    'min': 5,
                    'max': 15,
                    'step': 1
                }
            }
        """
        metadata = self.get_strategy(strategy_id)
        ranges = {}

        for param_def in metadata.parameters:
            range_info = {'type': param_def.type.value}

            if param_def.type in [ParameterType.INT, ParameterType.FLOAT]:
                range_info['min'] = param_def.min_value
                range_info['max'] = param_def.max_value
                if param_def.step:
                    range_info['step'] = param_def.step
            elif param_def.type == ParameterType.CATEGORICAL:
                range_info['choices'] = param_def.choices

            ranges[param_def.name] = range_info

        return ranges

    def reload(self):
        """重新載入策略配置（用於開發環境熱重載）"""
        logger.info("Reloading strategy registry...")
        self._strategies.clear()
        self._calculators.clear()
        self._validators.clear()
        self._load_strategies_from_yaml()


# ==================== 單例實例 ====================

# 創建全局單例實例
strategy_registry = StrategyRegistry()


# ==================== 便捷函數 ====================

def get_strategy_registry() -> StrategyRegistry:
    """獲取策略註冊中心實例"""
    return strategy_registry
