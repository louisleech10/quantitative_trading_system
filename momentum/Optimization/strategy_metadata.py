"""
策略元數據系統 - 動態參數配置核心模組

此模組定義了策略元數據的數據結構，用於支援任意指標和策略的動態配置。
通過元數據系統，可以完全消除硬編碼，實現配置驅動的參數優化。

Author: Claude (Phase 1 - Dynamic Parameters Refactoring)
Date: 2025-12-03
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class ParameterType(str, Enum):
    """參數類型枚舉"""
    INT = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"


class ConstraintType(str, Enum):
    """約束類型枚舉"""
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    RANGE_NO_OVERLAP = "range_no_overlap"


class ParameterConstraint(BaseModel):
    """
    參數約束定義

    用於定義參數之間的關係約束，例如：
    - short_period < mid_period < long_period
    - overbought_threshold > oversold_threshold
    """
    type: ConstraintType = Field(..., description="約束類型")
    target: str = Field(..., description="目標參數名稱")
    message: str = Field(..., description="驗證失敗時的錯誤訊息")

    class Config:
        schema_extra = {
            "example": {
                "type": "less_than",
                "target": "mid_period",
                "message": "短期週期必須小於中期週期"
            }
        }


class ParameterDefinition(BaseModel):
    """
    參數定義

    定義單個優化參數的所有元數據，包括類型、範圍、約束等。
    """
    name: str = Field(..., description="參數名稱（內部使用）")
    display_name: str = Field(..., description="UI 顯示名稱")
    type: ParameterType = Field(..., description="參數類型")
    default_value: Any = Field(..., description="默認值")

    # For int/float types
    min_value: Optional[float] = Field(None, description="最小值（int/float）")
    max_value: Optional[float] = Field(None, description="最大值（int/float）")
    step: Optional[float] = Field(None, description="步長（int/float）")

    # For categorical type
    choices: Optional[List[str]] = Field(None, description="可選值列表（categorical）")

    # Validation
    constraints: List[ParameterConstraint] = Field(
        default_factory=list,
        description="參數約束列表"
    )

    # UI hints
    description: Optional[str] = Field(None, description="參數描述")
    unit: Optional[str] = Field(None, description="單位（如：秒、%）")

    @model_validator(mode='after')
    def validate_parameter_definition(self):
        """驗證參數定義的完整性（Pydantic V2）"""
        # 數值類型需要 min_value, max_value
        if self.type in [ParameterType.INT, ParameterType.FLOAT]:
            if self.min_value is None or self.max_value is None:
                raise ValueError(
                    f"min_value and max_value are required for {self.type} type"
                )

        # 分類類型需要 choices
        if self.type == ParameterType.CATEGORICAL:
            if not self.choices or len(self.choices) == 0:
                raise ValueError("choices is required for categorical type")

        return self

    class Config:
        schema_extra = {
            "example": {
                "name": "short_period",
                "display_name": "短期週期",
                "type": "int",
                "default_value": 7,
                "min_value": 5,
                "max_value": 15,
                "step": 1,
                "description": "短期移動平均週期",
                "constraints": [
                    {
                        "type": "less_than",
                        "target": "mid_period",
                        "message": "短期週期必須小於中期週期"
                    }
                ]
            }
        }


class StrategyMetadata(BaseModel):
    """
    策略元數據

    定義一個完整策略的所有元數據，包括參數定義、計算函數、驗證規則等。
    這是整個動態參數系統的核心數據結構。
    """
    strategy_id: str = Field(..., description="策略唯一標識符（如：three_line）")
    display_name: str = Field(..., description="策略顯示名稱")
    description: str = Field(..., description="策略描述")
    category: str = Field(..., description="策略分類（trend/momentum/volatility）")

    # 參數定義
    parameters: List[ParameterDefinition] = Field(
        ...,
        description="策略參數定義列表"
    )

    # 支援的指標和數據源
    supported_indicators: List[str] = Field(
        ...,
        description="支援的指標類型列表（如：['ema', 'sma']）"
    )
    supported_data_sources: List[str] = Field(
        ...,
        description="支援的數據源列表（如：['close', 'volume']）"
    )

    # 計算函數位置（動態導入）
    calculator_module: str = Field(
        ...,
        description="計算函數所在模組路徑"
    )
    calculator_function: str = Field(
        ...,
        description="計算函數名稱"
    )

    # 驗證函數位置（可選）
    validator_module: Optional[str] = Field(
        None,
        description="驗證函數所在模組路徑"
    )
    validator_function: Optional[str] = Field(
        None,
        description="驗證函數名稱"
    )

    # UI 相關
    icon: Optional[str] = Field("📈", description="策略圖標")
    recommended_for: Optional[str] = Field(
        None,
        description="推薦使用場景"
    )
    complexity: Optional[str] = Field(
        "medium",
        description="複雜度等級（simple/medium/advanced）"
    )

    # 額外元數據
    tags: List[str] = Field(
        default_factory=list,
        description="標籤列表（用於搜索和分類）"
    )

    @field_validator('parameters')
    @classmethod
    def validate_parameters_unique(cls, v):
        """確保參數名稱唯一（Pydantic V2）"""
        param_names = [p.name for p in v]
        if len(param_names) != len(set(param_names)):
            raise ValueError("Parameter names must be unique")
        return v

    def get_parameter(self, name: str) -> Optional[ParameterDefinition]:
        """根據名稱獲取參數定義"""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def get_parameter_names(self) -> List[str]:
        """獲取所有參數名稱列表"""
        return [p.name for p in self.parameters]

    def get_default_values(self) -> Dict[str, Any]:
        """獲取所有參數的默認值字典"""
        return {p.name: p.default_value for p in self.parameters}

    class Config:
        schema_extra = {
            "example": {
                "strategy_id": "three_line",
                "display_name": "三線排列",
                "description": "短期EMA > 中期EMA > 長期EMA，順勢交易",
                "category": "trend",
                "parameters": [
                    {
                        "name": "short_period",
                        "display_name": "短期週期",
                        "type": "int",
                        "default_value": 7,
                        "min_value": 5,
                        "max_value": 15,
                        "step": 1
                    }
                ],
                "supported_indicators": ["ema", "sma"],
                "supported_data_sources": ["close", "open", "high", "low"],
                "calculator_module": "momentum.Analysis.strategies.three_line_strategy",
                "calculator_function": "calculate_signals",
                "icon": "📈",
                "complexity": "simple",
                "tags": ["trend", "moving_average"]
            }
        }


class ValidationResult(BaseModel):
    """
    參數驗證結果

    用於返回參數驗證的結果，包括是否通過和錯誤訊息列表。
    """
    is_valid: bool = Field(..., description="是否驗證通過")
    errors: List[str] = Field(
        default_factory=list,
        description="錯誤訊息列表"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="警告訊息列表（不影響驗證通過）"
    )

    def add_error(self, message: str):
        """添加錯誤訊息"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """添加警告訊息"""
        self.warnings.append(message)

    @classmethod
    def success(cls) -> 'ValidationResult':
        """創建成功的驗證結果"""
        return cls(is_valid=True, errors=[], warnings=[])

    @classmethod
    def failure(cls, errors: List[str]) -> 'ValidationResult':
        """創建失敗的驗證結果"""
        return cls(is_valid=False, errors=errors, warnings=[])


# 類型別名，用於策略計算和驗證函數的類型提示
StrategyCalculator = callable  # (kline_data, indicators, params) -> signals
StrategyValidator = callable   # (params) -> List[str]
