"""Momentum internal DTO contracts.

This module re-exports pure data types (enums, dataclasses, Pydantic models)
from domain-internal modules so that ``api/`` can depend on
``momentum.core.contracts`` instead of reaching into domain internals (Rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Lazy re-exports from domain modules ─────────────────────────────────────
# Pure data types that api/ needs without coupling to domain internals.
# Uses lazy imports to avoid circular dependency via __init__.py files.

def _lazy_reexport(name: str):
    """Lazy re-export helper to avoid circular imports via __init__.py."""
    _MAP = {
        "FailureType": ("momentum.DataExtraction.parallel_search_engine", "FailureType"),
        "classify_error": ("momentum.DataExtraction.parallel_search_engine", "classify_error"),
        "FeatureGenerationResult": ("momentum.FeatureEngineering.feature_factory", "FeatureGenerationResult"),
        "DifficultyLevel": ("momentum.Analysis.feature_toggle_registry", "DifficultyLevel"),
        "IndicatorConfig": ("momentum.FeatureEngineering.feature_config", "IndicatorConfig"),
    }
    if name in _MAP:
        import importlib
        mod_path, attr = _MAP[name]
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Populated on first access via __getattr__ in the module
_LAZY_NAMES = {"FailureType", "classify_error", "FeatureGenerationResult", "DifficultyLevel", "IndicatorConfig"}

def __getattr__(name: str):
    if name in _LAZY_NAMES:
        val = _lazy_reexport(name)
        globals()[name] = val  # Cache to avoid repeated import
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

@dataclass(frozen=True)
class TrainingWindowConfig:
    """Training window configuration for momentum analysis."""

    reference_point: str = "TO"
    lookback_bars: Optional[int] = None
    lookforward_bars: int = 0
    far_lookback_bars: Optional[int] = None
    mode: str = "relative"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timeframe: Optional[str] = None
    custom_timestamp: Optional[int] = None


@dataclass(frozen=True)
class StrategyConfig:
    """Strategy configuration used by signal analyzers."""

    data_source: str
    indicator_type: str
    strategy_logic: str
    params: Dict[str, Any]


@dataclass(frozen=True)
class SignalDensityRequest:
    """Signal density analysis request contract."""

    strategy_config: StrategyConfig
    training_window: TrainingWindowConfig
    positive_cases: List[str]
    negative_cases: List[str]


@dataclass(frozen=True)
class SignalDensityResponse:
    """Signal density analysis response contract."""

    positive_avg_density: float
    negative_avg_density: float
    separation: float
    p_value: float
    cohens_d: float
    stability_cv: float
    positive_std: float
    negative_std: float
    positive_sample_size: int
    negative_sample_size: int
    case_level_densities: Dict[str, float] = field(default_factory=dict)
    positive_near_far_ratio: Optional[float] = None
    negative_near_far_ratio: Optional[float] = None
    positive_far_avg_density: Optional[float] = None
    negative_far_avg_density: Optional[float] = None
    positive_far_std: Optional[float] = None
    negative_far_std: Optional[float] = None
    positive_ratio_std: Optional[float] = None
    negative_ratio_std: Optional[float] = None
    ratio_separation: Optional[float] = None
    positive_near_zero_count: Optional[int] = None
    positive_near_zero_ratio: Optional[float] = None
    positive_far_zero_count: Optional[int] = None
    positive_far_zero_ratio: Optional[float] = None
    negative_near_zero_count: Optional[int] = None
    negative_near_zero_ratio: Optional[float] = None
    negative_far_zero_count: Optional[int] = None
    negative_far_zero_ratio: Optional[float] = None
    positive_ratio_cv: Optional[float] = None
    separation_cv: Optional[float] = None
    positive_total_weight: Optional[float] = None
    negative_total_weight: Optional[float] = None
    positive_weighted_mean_m: Optional[float] = None
    negative_weighted_mean_m: Optional[float] = None
    positive_m_std: Optional[float] = None
    negative_m_std: Optional[float] = None
    m_separation: Optional[float] = None
    positive_active_cases: Optional[int] = None
    negative_active_cases: Optional[int] = None
    positive_m_cv: Optional[float] = None
    m_separation_cv: Optional[float] = None
    optuna_golden_score: Optional[float] = None
    sample_warnings: Optional[List[str]] = None
    excluded_months_count: Optional[int] = None
    included_months_count: Optional[int] = None
    monthly_breakdown: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ParameterRange:
    """Parameter range definition for optimization."""

    min: float
    max: float
    step: Optional[float] = 1


class ParameterType(str, Enum):
    """Strategy parameter type."""

    INT = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"


class ConstraintType(str, Enum):
    """Parameter constraint type."""

    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    RANGE_NO_OVERLAP = "range_no_overlap"


class ParameterConstraint(BaseModel):
    """Parameter constraint definition."""

    type: ConstraintType = Field(..., description="Constraint type")
    target: str = Field(..., description="Target parameter name")
    message: str = Field(..., description="Error message when validation fails")


class ParameterDefinition(BaseModel):
    """Parameter definition used by strategy metadata."""

    name: str = Field(..., description="Parameter name")
    display_name: str = Field(..., description="UI display name")
    type: ParameterType = Field(..., description="Parameter type")
    default_value: Any = Field(..., description="Default value")

    min_value: Optional[float] = Field(None, description="Minimum value")
    max_value: Optional[float] = Field(None, description="Maximum value")
    step: Optional[float] = Field(None, description="Step size")
    choices: Optional[List[str]] = Field(None, description="Choices for categorical type")
    constraints: List[ParameterConstraint] = Field(
        default_factory=list,
        description="Parameter constraints",
    )
    description: Optional[str] = Field(None, description="Parameter description")
    unit: Optional[str] = Field(None, description="Unit label")

    @model_validator(mode="after")
    def validate_parameter_definition(self):
        """Validate required fields based on parameter type."""
        if self.type in [ParameterType.INT, ParameterType.FLOAT]:
            if self.min_value is None or self.max_value is None:
                raise ValueError(
                    f"min_value and max_value are required for {self.type} type"
                )

        if self.type == ParameterType.CATEGORICAL:
            if not self.choices:
                raise ValueError("choices is required for categorical type")

        return self


class StrategyMetadata(BaseModel):
    """Strategy metadata definition."""

    strategy_id: str = Field(..., description="Strategy id")
    display_name: str = Field(..., description="Display name")
    description: str = Field(..., description="Description")
    category: str = Field(..., description="Category")
    parameters: List[ParameterDefinition] = Field(..., description="Parameter definitions")
    supported_indicators: List[str] = Field(..., description="Supported indicators")
    supported_data_sources: List[str] = Field(..., description="Supported data sources")
    calculator_module: str = Field(..., description="Calculator module")
    calculator_function: str = Field(..., description="Calculator function")
    validator_module: Optional[str] = Field(None, description="Validator module")
    validator_function: Optional[str] = Field(None, description="Validator function")
    icon: Optional[str] = Field("", description="Icon")
    recommended_for: Optional[str] = Field(None, description="Recommended usage")
    complexity: Optional[str] = Field("medium", description="Complexity")
    tags: List[str] = Field(default_factory=list, description="Tags")

    @field_validator("parameters")
    @classmethod
    def validate_parameters_unique(cls, value):
        """Ensure parameter names are unique."""
        param_names = [param.name for param in value]
        if len(param_names) != len(set(param_names)):
            raise ValueError("Parameter names must be unique")
        return value

    def get_parameter(self, name: str) -> Optional[ParameterDefinition]:
        """Get a parameter definition by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def get_parameter_names(self) -> List[str]:
        """Return all parameter names."""
        return [param.name for param in self.parameters]

    def get_default_values(self) -> Dict[str, Any]:
        """Return default values for all parameters."""
        return {param.name: param.default_value for param in self.parameters}


class ValidationResult(BaseModel):
    """Parameter validation result."""

    is_valid: bool = Field(..., description="Whether the validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)

    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a success result."""
        return cls(is_valid=True, errors=[], warnings=[])

    @classmethod
    def failure(cls, errors: List[str]) -> "ValidationResult":
        """Create a failure result."""
        return cls(is_valid=False, errors=errors, warnings=[])


StrategyCalculator = callable
StrategyValidator = callable


@dataclass
class ICResult:
    """IC 分析單一特徵的結果 — momentum 內部 DTO."""

    feature_name: str
    ic_mean: float
    ic_std: float
    icir: float
    p_value: float
    ic_hit_rate: float
    monotonicity_score: Optional[float] = None
    long_short_spread: Optional[float] = None
    coverage: Optional[float] = None
    turnover_rate: Optional[float] = None
    ic_half_life: Optional[float] = None
    regime_robust: Optional[bool] = None


@dataclass
class FilteredFeatureSet:
    """精選特徵集 — momentum 內部 DTO."""

    feature_names: List[str]
    ic_results: List[ICResult]
    diversification_metrics: Dict[str, Any] = field(default_factory=dict)
    filter_log: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkippedResult:
    """模組執行跳過或失敗時的結構化結果（SPEC §1.5.3）"""

    module_name: str
    reason: str
    error_type: str  # INSUFFICIENT_DATA | SINGLE_CLASS | TIMEOUT | NUMERICAL_ERROR | ZERO_VARIANCE | UNEXPECTED
    details: Optional[Dict] = None
    retryable: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class FeatureLibraryEntry:
    """A single entry in the Feature Library registry."""

    symbol: str
    timeframe: str
    config_hash: str
    feature_count: int
    row_count: int
    created_at: float
    hdf5_relative_path: str


class FeatureNotFoundError(Exception):
    """Raised when requested features are not found in the library."""

    def __init__(self, symbol: str, timeframe: str, detail: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        msg = f"Features not found for {symbol}/{timeframe}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)
