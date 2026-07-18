"""Momentum internal DTO contracts.

This module re-exports pure data types (enums, dataclasses, Pydantic models)
from domain-internal modules so that ``api/`` can depend on
``momentum.core.contracts`` instead of reaching into domain internals (Rule 3).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum
from collections.abc import Callable, Iterable
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
import hashlib
import json

import numpy as np
import pandas as pd
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


class EvaluationStatus(str, Enum):
    """IC 特徵評估狀態，避免 legacy/未評估特徵混入排序或 FDR。"""

    EVALUATED = "evaluated"
    NOT_EVALUATED = "not_evaluated"
    SKIPPED = "skipped"
    UNKNOWN_LEGACY = "unknown_legacy"


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
    eval_status: EvaluationStatus = EvaluationStatus.UNKNOWN_LEGACY


def filter_evaluated(results: List[ICResult]) -> List[ICResult]:
    """只回傳明確完成評估的 ICResult，legacy/跳過/未評估皆不列入。"""
    return [
        result
        for result in results
        if result.eval_status == EvaluationStatus.EVALUATED
    ]


@dataclass(frozen=True)
class ICArtifactSchema:
    """IC artifact long-layout 單列契約。"""

    feature_name: str
    horizon: int
    ic_mean: float
    ic_std: float
    icir: float
    p_value: float
    ic_hit_rate: float
    eval_status: str
    selection_scope_id: str
    schema_version: int


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
class SplitPlan:
    """IC 切分列歸屬契約，記錄單一 split 的 canonical row identity。"""

    split_label: Literal["train", "val", "test"]
    index_kind: Literal["timestamp", "positional", "row_id"]
    row_index: np.ndarray
    time_bounds: tuple
    purge_gap: int
    embargo: int
    purge_semantic: Literal["rows", "timedelta"] = "rows"
    expected_freq: Optional[str] = None
    base_universe_hash: str = ""
    symbol: Optional[str] = None

    def __post_init__(self) -> None:
        """驗證切分契約的必要 discriminator 與 purge 邊界。"""
        if self.split_label not in {"train", "val", "test"}:
            raise ValueError("split_label must be one of train, val, test")
        if self.index_kind not in {"timestamp", "positional", "row_id"}:
            raise ValueError("index_kind must be one of timestamp, positional, row_id")
        if self.purge_semantic not in {"rows", "timedelta"}:
            raise ValueError("purge_semantic must be one of rows, timedelta")
        if not self.base_universe_hash:
            raise ValueError("base_universe_hash is required")
        if len(self.row_index) > 0 and self.purge_gap >= len(self.row_index):
            raise ValueError("purge_gap must be smaller than non-empty row_index length")


class CrossSymbolLeakageError(ValueError):
    """切分列跨越 symbol 邊界時使用的 fail-closed 例外。"""


class TimestampDiscontinuityError(ValueError):
    """單一 symbol 內 timestamp 非嚴格連續時使用的 fail-closed 例外。"""


class SplitPairLeakageError(ValueError):
    """train/test pair 的 purge 或 embargo 禁止區間被 train row 踩入。"""


def _coerce_timestamp_array(values: Any) -> np.ndarray:
    """將 timestamp array 正規化成 pandas datetime64[ns] 陣列。"""
    arr = np.asarray(values)
    if arr.size == 0:
        return pd.to_datetime(arr).to_numpy()
    if np.issubdtype(arr.dtype, np.datetime64):
        return pd.to_datetime(arr).to_numpy()
    if np.issubdtype(arr.dtype, np.number):
        return pd.to_datetime(arr, unit="s").to_numpy()
    return pd.to_datetime(arr).to_numpy()


def _normalize_symbol_value(value: Any) -> str:
    """將 symbol 正規化為非空 str；缺值或不可解碼值 fail-closed。

    missing_sentinels 是 best-effort heuristic；權威防線是
    validate_* / split_per_symbol 的 allowed_symbols allowlist，接線端應傳入真實 universe。
    """
    missing_sentinels = {"", "nan", "null", "none", "na", "n/a", "<na>"}
    if value is None:
        raise CrossSymbolLeakageError("symbol contains missing value")
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CrossSymbolLeakageError("symbol bytes must decode as utf-8") from exc
    try:
        if pd.isna(value):
            raise CrossSymbolLeakageError("symbol contains missing value")
    except TypeError:
        pass
    if not isinstance(value, str):
        raise CrossSymbolLeakageError("symbol must normalize to non-empty str")
    normalized = value.strip()
    if normalized.lower() in missing_sentinels:
        raise CrossSymbolLeakageError("symbol contains missing sentinel")
    return normalized


def _normalize_symbol_array(values: Any) -> np.ndarray:
    """正規化整條 symbol array，避免 bytes/NaN 靜默通過或被 groupby 丟棄。"""
    arr = np.asarray(values, dtype=object)
    return np.asarray([_normalize_symbol_value(value) for value in arr], dtype=object)


def _normalize_allowed_symbols(allowed_symbols: Optional[set[str]]) -> Optional[set[str]]:
    """正規化 allowed symbol universe，供 contract 層做權威 allowlist 檢查。"""
    if allowed_symbols is None:
        return None
    return {_normalize_symbol_value(symbol) for symbol in allowed_symbols}


def _validate_allowed_symbols(
    plan_symbol: str,
    symbol_arr: np.ndarray,
    allowed_symbols: Optional[set[str]],
) -> None:
    """確認 plan 與資料 symbol 都屬於指定 universe。"""
    normalized_allowed = _normalize_allowed_symbols(allowed_symbols)
    if normalized_allowed is None:
        return
    if plan_symbol not in normalized_allowed:
        raise CrossSymbolLeakageError("SplitPlan.symbol is outside allowed_symbols")
    unknown_symbols = set(np.unique(symbol_arr)) - normalized_allowed
    if unknown_symbols:
        raise CrossSymbolLeakageError("symbols contain values outside allowed_symbols")


def _contiguous_index_ranges(indices: np.ndarray) -> List[Tuple[int, int]]:
    """將 sorted row positions 壓成半開區間 [start, end)。"""
    if indices.size == 0:
        return []
    sorted_idx = np.sort(indices.astype(int))
    ranges: List[Tuple[int, int]] = []
    start = int(sorted_idx[0])
    prev = start
    for value in sorted_idx[1:]:
        current = int(value)
        if current != prev + 1:
            ranges.append((start, prev + 1))
            start = current
        prev = current
    ranges.append((start, prev + 1))
    return ranges


def _local_ordinals_for_symbol(
    row_index: np.ndarray,
    symbol_arr: np.ndarray,
    symbol: str,
) -> np.ndarray:
    """將全域 row position 映射成同 symbol 內的 local ordinal。"""
    symbol_positions = np.flatnonzero(symbol_arr == symbol)
    if symbol_positions.size == 0:
        raise CrossSymbolLeakageError("symbol has no rows in base universe")
    local_ordinals = np.searchsorted(symbol_positions, row_index.astype(int))
    if (
        np.any(local_ordinals >= symbol_positions.size)
        or not np.array_equal(symbol_positions[local_ordinals], row_index.astype(int))
    ):
        raise CrossSymbolLeakageError("row_index contains rows outside declared symbol")
    return local_ordinals.astype(int)


def validate_split_integrity(
    plan: SplitPlan,
    ts: Any,
    symbols: Any,
    allowed_symbols: Optional[set[str]] = None,
) -> None:
    """驗證 SplitPlan 未跨 symbol 且單一 symbol 時間軸可安全套用 rows purge。"""
    row_index = np.asarray(plan.row_index, dtype=int)

    if plan.symbol is None:
        raise CrossSymbolLeakageError("SplitPlan.symbol is required for split integrity")
    plan_symbol = _normalize_symbol_value(plan.symbol)
    if plan.purge_semantic == "rows" and plan.expected_freq is None:
        raise TimestampDiscontinuityError(
            "rows purge requires expected_freq; use timedelta purge to allow gaps"
        )

    symbol_arr = _normalize_symbol_array(symbols)
    _validate_allowed_symbols(plan_symbol, symbol_arr, allowed_symbols)
    ts_arr = _coerce_timestamp_array(ts)
    if symbol_arr.shape[0] != ts_arr.shape[0]:
        raise ValueError("symbols and ts must have the same length")
    if row_index.size == 0:
        return
    if np.any(row_index < 0) or np.any(row_index >= symbol_arr.shape[0]):
        raise IndexError("plan.row_index contains positions outside base universe")

    selected_symbols = np.unique(symbol_arr[row_index])
    if selected_symbols.size != 1 or selected_symbols[0] != plan_symbol:
        raise CrossSymbolLeakageError(
            "SplitPlan row_index must contain exactly its declared symbol"
        )

    selected_ts = ts_arr[row_index]
    if selected_ts.size > 1:
        diffs = np.diff(selected_ts)
        if np.any(diffs <= np.timedelta64(0, "ns")):
            raise TimestampDiscontinuityError(
                "SplitPlan timestamps must be strictly increasing without duplicates"
            )
        if plan.purge_semantic == "rows":
            base_ts = ts_arr[symbol_arr == plan_symbol]
            base_diffs = np.diff(base_ts)
            if np.any(base_diffs <= np.timedelta64(0, "ns")):
                raise TimestampDiscontinuityError(
                    "base symbol timestamps must be strictly increasing without duplicates"
                )
            expected_delta = pd.Timedelta(plan.expected_freq)
            max_gap = pd.Timedelta(np.max(base_diffs))
            if max_gap > expected_delta * 1.05:
                raise TimestampDiscontinuityError(
                    "rows purge requires continuous timestamps at expected_freq"
                )


def validate_split_pair_integrity(
    train_plan: SplitPlan,
    test_plan: SplitPlan,
    ts: Any,
    symbols: Any,
    allowed_symbols: Optional[set[str]] = None,
) -> None:
    """驗證 train rows 沒踩進 test 的 purge/embargo 禁止區間。"""
    validate_split_integrity(train_plan, ts, symbols, allowed_symbols)
    validate_split_integrity(test_plan, ts, symbols, allowed_symbols)

    train_rows = np.asarray(train_plan.row_index, dtype=int)
    test_rows = np.asarray(test_plan.row_index, dtype=int)
    if train_rows.size == 0 or test_rows.size == 0:
        raise SplitPairLeakageError("train/test row_index must be non-empty")
    train_symbol = _normalize_symbol_value(train_plan.symbol)
    test_symbol = _normalize_symbol_value(test_plan.symbol)
    if train_symbol != test_symbol:
        raise CrossSymbolLeakageError("train/test SplitPlan symbols must match")
    if train_plan.base_universe_hash != test_plan.base_universe_hash:
        raise ValueError("train/test SplitPlan base_universe_hash must match")

    symbol_arr = _normalize_symbol_array(symbols)
    train_local = _local_ordinals_for_symbol(train_rows, symbol_arr, train_symbol)
    test_local = _local_ordinals_for_symbol(test_rows, symbol_arr, test_symbol)
    purge_gap = max(int(test_plan.purge_gap), int(train_plan.purge_gap), 0)
    embargo = max(int(test_plan.embargo), 0)
    for start, end in _contiguous_index_ranges(test_local):
        forbidden_start = max(0, start - purge_gap)
        forbidden_end = end + purge_gap + embargo
        leaking = train_rows[
            (train_local >= forbidden_start) & (train_local < forbidden_end)
        ]
        if leaking.size > 0:
            raise SplitPairLeakageError(
                "train rows overlap test purge/embargo forbidden interval"
            )


def _time_bounds_for_indices(ts: Any, row_index: np.ndarray) -> tuple:
    """依 row_index 建立 SplitPlan time_bounds。"""
    if row_index.size == 0:
        return (None, None)
    ts_arr = _coerce_timestamp_array(ts)
    selected = ts_arr[row_index]
    return (pd.Timestamp(selected[0]), pd.Timestamp(selected[-1]))


def split_per_symbol(
    data: pd.DataFrame,
    splitter: Callable[[pd.DataFrame], Iterable[Tuple[np.ndarray, np.ndarray]]],
    symbol_col: str,
    ts_col: str,
    *,
    purge_gap: int = 0,
    embargo: int = 0,
    purge_semantic: Literal["rows", "timedelta"] = "rows",
    expected_freq: Optional[str] = None,
    base_universe_hash: str = "",
    allowed_symbols: Optional[set[str]] = None,
) -> List[Tuple[SplitPlan, SplitPlan]]:
    """逐 symbol 呼叫 splitter，將 local index 轉回全 frame row position。"""
    if symbol_col not in data.columns or ts_col not in data.columns:
        raise ValueError("data must contain symbol_col and ts_col")
    if not base_universe_hash:
        raise ValueError("base_universe_hash is required")

    frame = data.copy()
    frame["_split_row_pos"] = np.arange(len(frame), dtype=int)
    frame[symbol_col] = _normalize_symbol_array(frame[symbol_col].to_numpy())
    ts = frame[ts_col].to_numpy()
    symbols = frame[symbol_col].to_numpy()
    normalized_allowed = _normalize_allowed_symbols(allowed_symbols)
    plans: List[Tuple[SplitPlan, SplitPlan]] = []

    for symbol, group in frame.groupby(symbol_col, sort=False, dropna=False):
        symbol = _normalize_symbol_value(symbol)
        if normalized_allowed is not None and symbol not in normalized_allowed:
            raise CrossSymbolLeakageError("symbols contain values outside allowed_symbols")
        group_sorted = group.sort_values(ts_col, kind="mergesort")
        positions = group_sorted["_split_row_pos"].to_numpy(dtype=int)
        group_for_splitter = group_sorted.drop(columns=["_split_row_pos"])
        for train_local, test_local in splitter(group_for_splitter):
            train_rows = positions[np.asarray(train_local, dtype=int)]
            test_rows = positions[np.asarray(test_local, dtype=int)]
            train_plan = SplitPlan(
                split_label="train",
                index_kind="positional",
                row_index=train_rows,
                time_bounds=_time_bounds_for_indices(ts, train_rows),
                purge_gap=purge_gap,
                embargo=embargo,
                purge_semantic=purge_semantic,
                expected_freq=expected_freq,
                base_universe_hash=base_universe_hash,
                symbol=symbol,
            )
            test_plan = SplitPlan(
                split_label="test",
                index_kind="positional",
                row_index=test_rows,
                time_bounds=_time_bounds_for_indices(ts, test_rows),
                purge_gap=purge_gap,
                embargo=embargo,
                purge_semantic=purge_semantic,
                expected_freq=expected_freq,
                base_universe_hash=base_universe_hash,
                symbol=symbol,
            )
            validate_split_pair_integrity(
                train_plan,
                test_plan,
                ts,
                symbols,
                allowed_symbols=normalized_allowed,
            )
            plans.append((train_plan, test_plan))
    return plans


@dataclass(frozen=True)
class RowMaskPlan:
    """IC 列遮罩契約，使用 canonical row identity 表達入選列。"""

    row_index: np.ndarray
    index_kind: Literal["timestamp", "positional", "row_id"]
    source: Literal["split", "event", "feature_filter", "full"]
    base_universe_hash: str
    length: int
    symbol: Optional[str] = None

    def __post_init__(self) -> None:
        """驗證遮罩契約 discriminator 與 universe identity。"""
        if self.index_kind not in {"timestamp", "positional", "row_id"}:
            raise ValueError("index_kind must be one of timestamp, positional, row_id")
        if self.source not in {"split", "event", "feature_filter", "full"}:
            raise ValueError("source must be one of split, event, feature_filter, full")
        if not self.base_universe_hash:
            raise ValueError("base_universe_hash is required")
        if self.length < 0:
            raise ValueError("length must be non-negative")

    @property
    def n_selected(self) -> int:
        """回傳遮罩選中的列數。"""
        return int(len(self.row_index))

    def to_mask(self, base_len: int) -> np.ndarray:
        """依 base universe 長度轉回 boolean mask。"""
        if self.length != base_len:
            raise ValueError("length must match base_len")
        mask = np.zeros(base_len, dtype=bool)
        mask[self.row_index] = True
        return mask

    @classmethod
    def from_mask(cls, mask: np.ndarray, **meta: Any) -> "RowMaskPlan":
        """由 boolean mask 建立 RowMaskPlan，metadata 必須帶 discriminator。"""
        if "index_kind" not in meta:
            raise ValueError("index_kind is required")
        row_index = np.flatnonzero(mask)
        return cls(row_index=row_index, length=len(mask), **meta)


@dataclass(frozen=True)
class SelectionScope:
    """IC FDR/顯著性範圍契約，鎖定 universe、split 與 evaluated 集合。"""

    scope_id: str
    universe_features: List[str]
    # "full" = 無 train/test split 的明示全樣本標籤（Task 2.3 契約擴充，非放寬）
    split_label: Literal["train", "val", "test", "full"]
    evaluated_features: List[str]
    n_tests: int
    method: str
    base_universe_hash: str

    def __post_init__(self) -> None:
        """驗證 evaluated_features 必須屬於 universe 且 n_tests 一致。"""
        if self.split_label not in {"train", "val", "test", "full"}:
            raise ValueError("split_label must be one of train, val, test, full")
        if not set(self.evaluated_features).issubset(set(self.universe_features)):
            raise ValueError("evaluated_features must be a subset of universe_features")
        if self.n_tests != len(self.evaluated_features):
            raise ValueError("n_tests must match len(evaluated_features)")


@dataclass(frozen=True)
class AlignmentSpec:
    """IC Feature_t 與 Target_t+lag 的對齊契約簽名。"""

    feature_ts_col: str
    target_ts_col: str
    lag: int
    freq: str

    def __post_init__(self) -> None:
        """驗證 lag 與 pandas frequency 字串。"""
        if self.lag < 0:
            raise ValueError("lag must be non-negative")
        try:
            pd.tseries.frequencies.to_offset(self.freq)
        except (TypeError, ValueError) as exc:
            raise ValueError("freq must be a valid pandas frequency") from exc


class AlignmentViolationError(ValueError):
    """Feature/target 時間軸或 label 值不符合對齊契約。"""


@dataclass(frozen=True)
class AlignmentReport:
    """Feature_t 與 Target_t+lag 對齊檢查摘要。"""

    gap_count: int
    gap_rate: float
    checked_samples: int


_ALIGNMENT_COVERAGE_TOLERANCE = 0.01


def _extract_alignment_index(data: Any, ts_col: str, role: str) -> pd.Index:
    """取出對齊檢查使用的時間軸。"""
    if isinstance(data, (pd.Series, pd.DataFrame)):
        if ts_col in data:
            return pd.Index(data[ts_col], name=ts_col)
        return data.index
    raise AlignmentViolationError(f"{role} must be a pandas Series or DataFrame")


def _normalize_alignment_index(index: pd.Index, role: str) -> pd.DatetimeIndex:
    """依 D-1 將 DatetimeIndex 或 int64 epoch 秒正規化為 DatetimeIndex。"""
    if isinstance(index, pd.MultiIndex):
        raise AlignmentViolationError(f"{role} index must not be MultiIndex")
    if isinstance(index, pd.RangeIndex):
        raise AlignmentViolationError(f"{role} index must carry timestamps, not RangeIndex")

    if isinstance(index, pd.DatetimeIndex):
        ts = pd.DatetimeIndex(index)
    elif pd.api.types.is_integer_dtype(index.dtype):
        values = index.to_numpy(dtype=np.int64)
        if values.size and (np.any(np.abs(values) > 1_000_000_000_000)):
            raise AlignmentViolationError(f"{role} index looks like milliseconds, expected epoch seconds")
        ts = pd.to_datetime(values, unit="s")
    else:
        try:
            ts = pd.DatetimeIndex(pd.to_datetime(index, errors="raise"))
        except (TypeError, ValueError) as exc:
            raise AlignmentViolationError(f"{role} index must be datetime-like or int64 epoch seconds") from exc

    if ts.hasnans:
        raise AlignmentViolationError(f"{role} index contains NaT")
    if not ts.is_monotonic_increasing:
        raise AlignmentViolationError(f"{role} index must be monotonic increasing")
    if not ts.is_unique:
        raise AlignmentViolationError(f"{role} index must be unique")
    return ts


def _alignment_values(data: Any) -> pd.Series:
    """取出 target label 數值序列。"""
    if isinstance(data, pd.Series):
        return data
    if isinstance(data, pd.DataFrame):
        numeric_cols = list(data.select_dtypes(include=[np.number]).columns)
        if not numeric_cols:
            raise AlignmentViolationError("target_data must contain a numeric label column")
        return data[numeric_cols[0]]
    raise AlignmentViolationError("target_data must be a pandas Series or DataFrame")


def _count_structural_tail_nans(values: pd.Series) -> int:
    """計算尾端連續 NaN 數。"""
    mask = values.isna().to_numpy()
    count = 0
    for is_nan in mask[::-1]:
        if not is_nan:
            break
        count += 1
    return count


def _cadence_report(ts: pd.DatetimeIndex, expected_freq: str) -> tuple[int, float]:
    """依 D-3 檢查非 gap cadence，並回傳 gap 摘要。"""
    if len(ts) <= 1:
        return 0, 0.0
    diff_ns = np.diff(ts.asi8)
    if np.any(diff_ns <= 0):
        raise AlignmentViolationError("timestamps must be strictly increasing")
    median_ns = float(np.median(diff_ns))
    gap_mask = diff_ns > (1.5 * median_ns)
    non_gap = diff_ns[~gap_mask]
    if non_gap.size == 0:
        raise AlignmentViolationError("cannot infer cadence from non-gap timestamps")
    values, counts = np.unique(non_gap, return_counts=True)
    cadence_ns = int(values[int(np.argmax(counts))])
    expected_ns = pd.tseries.frequencies.to_offset(expected_freq).nanos
    tolerance = max(expected_ns * 0.05, 1.0)
    if abs(cadence_ns - expected_ns) > tolerance:
        raise AlignmentViolationError(
            f"cadence mismatch: expected {expected_freq}, got {pd.Timedelta(cadence_ns, unit='ns')}"
        )
    gap_count = int(gap_mask.sum())
    gap_rate = gap_count / max(int(diff_ns.size), 1)
    return gap_count, float(gap_rate)


def _sensitive_alignment_rows(values: pd.Series, ts: pd.DatetimeIndex) -> np.ndarray:
    """找出 label 變異突變點與 gap 邊界，供 Tier-2 oracle 強制抽樣。"""
    sensitive: set[int] = set()
    if len(values) >= 2:
        arr = values.to_numpy(dtype="float64", copy=False)
        diffs = np.abs(np.diff(arr))
        finite = np.flatnonzero(np.isfinite(diffs))
        if finite.size:
            positive = finite[diffs[finite] > 0.0]
            ranked = positive if positive.size else finite
            ranked = ranked[np.argsort(diffs[ranked], kind="mergesort")[::-1]]
            for left_row in ranked[:16]:
                sensitive.add(int(left_row))
                sensitive.add(int(left_row + 1))

    if len(ts) >= 2:
        diff_ns = np.diff(ts.asi8)
        median_ns = float(np.median(diff_ns))
        gap_left_rows = np.flatnonzero(diff_ns > (1.5 * median_ns))
        for left_row in gap_left_rows:
            sensitive.add(int(left_row))
            sensitive.add(int(left_row + 1))

    return np.array(sorted(sensitive), dtype=int)


def _sample_alignment_positions(
    candidate_positions: np.ndarray,
    sample_size: int,
    *,
    sensitive_positions: Optional[np.ndarray] = None,
) -> np.ndarray:
    """以確定性分層抽樣檢查頭尾、等距位置與變異敏感區。"""
    if candidate_positions.size <= sample_size:
        return candidate_positions
    head = candidate_positions[:2]
    tail = candidate_positions[-2:]
    candidate_set = set(candidate_positions.tolist())
    used = set(np.concatenate([head, tail]).tolist())
    if sensitive_positions is not None and sensitive_positions.size:
        used.update(int(pos) for pos in sensitive_positions.tolist() if int(pos) in candidate_set)

    remaining = max(sample_size - len(used), 0)
    if remaining:
        grid_idx = np.linspace(0, candidate_positions.size - 1, num=min(remaining, candidate_positions.size))
        grid = candidate_positions[np.unique(np.rint(grid_idx).astype(int))]
    else:
        grid = np.array([], dtype=int)
    return np.array(sorted(used.union(grid.tolist())), dtype=int)


# Tier-2 逐點 oracle 支援的報酬型別;excess/risk_adjusted/winsorized 屬視窗/基準轉換
# 無逐點封閉式,只走 Tier-1(caller 不得對其傳 close)。
_ORACLE_RETURN_KINDS = {
    "log": lambda current, future: float(np.log(future / current)),
    "simple": lambda current, future: float(future / current - 1.0),
}

# 公開常數:caller 判斷「此 return_type 是否可傳 close 啟用 Tier-2」的單一真相源。
ORACLE_RETURN_KINDS = frozenset(_ORACLE_RETURN_KINDS)


def validate_alignment(
    feature_data: Any,
    target_data: Any,
    spec: AlignmentSpec,
    *,
    close: Optional[pd.Series] = None,
    sample_size: int = 64,
    return_kind: str = "log",
) -> AlignmentReport:
    """驗證 Feature_t 與 Target_t+lag 的時間軸與 bar-ordinal label 值。"""
    feature_index = _normalize_alignment_index(
        _extract_alignment_index(feature_data, spec.feature_ts_col, "feature_data"),
        "feature_data",
    )
    target_index = _normalize_alignment_index(
        _extract_alignment_index(target_data, spec.target_ts_col, "target_data"),
        "target_data",
    )
    if len(feature_index) == 0 or len(target_index) == 0:
        raise AlignmentViolationError("feature_data and target_data must be non-empty")
    if not feature_index.equals(target_index):
        raise AlignmentViolationError("feature and target timestamps must match exactly")

    gap_count, gap_rate = _cadence_report(feature_index, spec.freq)
    target_values = _alignment_values(target_data)
    if target_values.isna().all():
        raise AlignmentViolationError("target_data cannot be all NaN")
    tail_nans = _count_structural_tail_nans(target_values)
    if tail_nans != spec.lag:
        raise AlignmentViolationError(
            f"target trailing NaN count must equal lag: expected {spec.lag}, got {tail_nans}"
        )
    valid_ratio = float(target_values.notna().sum()) / float(len(target_values))
    expected_valid_ratio = (max(len(target_values) - spec.lag, 0) / float(len(target_values))) * (
        1.0 - _ALIGNMENT_COVERAGE_TOLERANCE
    )
    if valid_ratio < expected_valid_ratio:
        raise AlignmentViolationError(
            f"target coverage too low: actual={valid_ratio:.4f}, required>={expected_valid_ratio:.4f}"
        )

    checked_samples = 0
    if close is not None:
        oracle = _ORACLE_RETURN_KINDS.get(return_kind)
        if oracle is None:
            raise AlignmentViolationError(
                f"unsupported oracle return_kind: {return_kind}; Tier-2 supports {sorted(_ORACLE_RETURN_KINDS)}"
            )
        close_index = _normalize_alignment_index(close.index, "close")
        close_series = pd.Series(close.to_numpy(dtype="float64", copy=False), index=close_index)
        positioner = pd.Series(np.arange(len(close_series), dtype=int), index=close_index)
        positions = positioner.reindex(feature_index).to_numpy()
        known_positions = ~pd.isna(positions)
        safe_positions = np.full(len(positions), -1, dtype=int)
        safe_positions[known_positions] = positions[known_positions].astype(int)
        in_bounds = known_positions & (safe_positions + spec.lag < len(close_series))
        value_mask = target_values.notna().to_numpy()
        candidate_rows = np.flatnonzero(in_bounds & value_mask)
        if candidate_rows.size < 8:
            raise AlignmentViolationError("insufficient valid samples for alignment oracle")
        sensitive_rows = _sensitive_alignment_rows(target_values, feature_index)
        sampled_rows = _sample_alignment_positions(
            candidate_rows,
            int(sample_size),
            sensitive_positions=sensitive_rows,
        )
        for row in sampled_rows:
            close_pos = int(safe_positions[row])
            current = close_series.iloc[close_pos]
            future = close_series.iloc[close_pos + spec.lag]
            got = float(target_values.iloc[row])
            if pd.isna(current) or pd.isna(future) or pd.isna(got):
                continue
            expected = oracle(current, future)
            if not np.isclose(got, expected, atol=1e-6, rtol=1e-5, equal_nan=False):
                raise AlignmentViolationError(
                    f"label mismatch at {feature_index[row]}: expected {expected}, got {got}"
                )
            checked_samples += 1
        if checked_samples < 8:
            raise AlignmentViolationError("insufficient checked samples for alignment oracle")

    return AlignmentReport(
        gap_count=gap_count,
        gap_rate=gap_rate,
        checked_samples=checked_samples,
    )


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


class LayerStatus(str, Enum):
    """Feature Factory 單層執行狀態（SPEC §P-4 九類互斥 enum）。"""

    ok = "ok"
    engine_partial = "engine_partial"
    all_engines_failed = "all_engines_failed"
    empty_disabled = "empty_disabled"
    empty_short_data = "empty_short_data"
    empty_not_applicable = "empty_not_applicable"
    offloaded_to_registry = "offloaded_to_registry"
    dependency_failed = "dependency_failed"
    layer_failed = "layer_failed"


@dataclass(frozen=True)
class LayerExecutionResult:
    """Feature Factory 單層執行結果 contract（Batch1 / SPEC §P-1）。"""

    data: pd.DataFrame
    status: LayerStatus
    failed_engines: Tuple[str, ...]
    reason: Optional[str]
    configured_engines: int
    present_engines: int
    required_engines: int
    dependency_error: bool

    def __post_init__(self) -> None:
        """強制 failed_engines 為 tuple，確保 frozen dataclass 真不可變。"""
        if not isinstance(self.failed_engines, tuple):
            object.__setattr__(self, "failed_engines", tuple(self.failed_engines))


def derive_status(
    *,
    configured_engines: int,
    present_engines: int,
    required_engines: int,
    failed_engines: Tuple[str, ...] = (),
    layer_enabled: bool = True,
    short_data: bool = False,
    offloaded: bool = False,
    dependency_error: bool = False,
    layer_exception: bool = False,
) -> LayerStatus:
    """依 SPEC §P-4 真值表優先級由上而下判定 layer status（每組唯一映射）。"""
    if not layer_enabled or configured_engines == 0:
        return LayerStatus.empty_disabled
    if layer_exception:
        return LayerStatus.layer_failed
    if dependency_error:
        return LayerStatus.dependency_failed
    if (
        configured_engines > 0
        and present_engines == 0
        and (required_engines > 0 or bool(failed_engines))
    ):
        return LayerStatus.all_engines_failed
    if short_data:
        return LayerStatus.empty_short_data
    if offloaded:
        return LayerStatus.offloaded_to_registry
    if configured_engines > 0 and present_engines == 0:
        return LayerStatus.empty_not_applicable
    if failed_engines and present_engines > 0:
        return LayerStatus.engine_partial
    return LayerStatus.ok


# ── LA-2 B2: OOF/OOT/Calibrator receipts + horizon OOT check (§0.6-APPENDIX) ──

EvalScope = Literal["oot", "cv_oof", "in_sample_research_only"]

# 後端 issuer allowlist（tamper-evident 誠實邊界，非密碼學防偽）
TRUSTED_RECEIPT_ISSUERS: frozenset[str] = frozenset(
    {
        "xgboost_task_service",
        "xgboost_batch_service",
        "model_task_service",
        "probability_calibrator",
        "lightgbm_analyzer",
        "xgboost_analyzer",
        "test_issuer",
    }
)

RECEIPT_ENVELOPE_VERSION = 1

# §0.6-C 28-path eval_scope 閉集（service/analyzer 共用）
MODEL_PERFORMANCE_EVAL_SCOPE: Dict[str, EvalScope] = {
    "in_sample_train_auc": "in_sample_research_only",
    "fit_pool_auc": "in_sample_research_only",
    "overfitting_score": "in_sample_research_only",
    "precision": "cv_oof",
    "recall": "cv_oof",
    "f1_score": "cv_oof",
    "cv_auc_mean": "cv_oof",
    "cv_auc_std": "cv_oof",
    "oot_auc": "oot",
    "calibration_curve": "cv_oof",
    "brier_score": "cv_oof",
    "ece": "cv_oof",
    "pr_curve": "cv_oof",
    "pr_auc": "cv_oof",
    "precision_at_k": "oot",
    "recommend_k": "oot",
    "expectancy": "oot",
    "sharpe_proxy": "oot",
    "bootstrap_ci": "oot",
    "predictions/train": "in_sample_research_only",
    "predictions/oot": "oot",
    "feature_importance": "in_sample_research_only",
    "feature_importance_all": "in_sample_research_only",
    "permutation_importance": "in_sample_research_only",
    "fold_importance_stability": "cv_oof",
    "shap_sample": "in_sample_research_only",
    "regime_analysis": "in_sample_research_only",
    "cross_symbol_validation": "in_sample_research_only",
}

# consumer deny for in_sample_research_only fields（promotion/signal 禁）
EVAL_SCOPE_CONSUMER_DENY: frozenset[str] = frozenset(
    {
        "in_sample_train_auc",
        "fit_pool_auc",
        "overfitting_score",
        "predictions/train",
        "feature_importance",
        "feature_importance_all",
        "permutation_importance",
        "shap_sample",
        "regime_analysis",
        "cross_symbol_validation",
    }
)

OMITTED_METRIC = "OMITTED"


class ReceiptVerificationError(ValueError):
    """OOF/OOT/Calibrator receipt 驗證失敗（fail-closed）。"""


class MetricsOmittedError(ValueError):
    """缺 held-out 時 OOT 指標 OMITTED + deny（非 silent 全樣本）。"""


def _require_1d_row_index(row_index: Any, *, where: str = "row_index") -> np.ndarray:
    """row_index 必須 1-D（2-D 不可先 reshape 繞過 hash 身份）。"""
    arr = np.asarray(row_index)
    if arr.ndim != 1:
        raise ValueError(
            f"{where} must be 1-D (got ndim={arr.ndim}); "
            "2-D input is rejected at factory and hash (no reshape(-1) bypass)"
        )
    return np.ascontiguousarray(arr, dtype="<i8")


def _canonical_row_index_bytes(row_index: Any) -> bytes:
    """canonical hash 用 row_index bytes：dtype '<i8'、1-D contiguous。"""
    return _require_1d_row_index(row_index).tobytes()


def _field_sha256(payload: bytes) -> bytes:
    """單欄獨立 sha256 digest（32 bytes）。"""
    return hashlib.sha256(payload).digest()


def canonical_idx_hash(
    row_index: Any,
    *,
    split_label: str = "",
    symbol: str = "",
    base_universe_hash: str = "",
) -> str:
    """idx/plan canonical sha256（禁 Python hash()；禁可撞 ``|`` 串接）。

    逐欄獨立 sha256 再串接後外層 sha256，使 ``a|b,c`` ≠ ``a,b|c``。
    """
    # 逐欄獨立 digest 再串 — 不可用 b"|".join（delimiter 可撞）
    concatenated = b"".join(
        [
            _field_sha256(_canonical_row_index_bytes(row_index)),
            _field_sha256(str(split_label).encode()),
            _field_sha256(str(symbol).encode()),
            _field_sha256(str(base_universe_hash).encode()),
        ]
    )
    return hashlib.sha256(concatenated).hexdigest()


def canonical_split_plan_hash(plan: "SplitPlan") -> str:
    """SplitPlan → split_plan_hash（含 label/symbol/universe 防撞）。"""
    return canonical_idx_hash(
        plan.row_index,
        split_label=str(plan.split_label),
        symbol=str(plan.symbol or ""),
        base_universe_hash=str(plan.base_universe_hash),
    )


def model_artifact_digest(model_artifact: bytes) -> str:
    """model_artifact_digest = sha256(artifact bytes)。"""
    if not isinstance(model_artifact, (bytes, bytearray)):
        raise TypeError("model_artifact must be bytes")
    return hashlib.sha256(bytes(model_artifact)).hexdigest()


def _canonical_json_bytes(obj: Any) -> bytes:
    """canonical JSON bytes：sort_keys + compact separators。"""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def envelope_digest_for(
    receipt_kind: Literal["oof", "oot", "calibrator"],
    fields_dict: Dict[str, Any],
    *,
    version: int = RECEIPT_ENVELOPE_VERSION,
) -> str:
    """envelope_digest = sha256(canonical-JSON({kind,version,fields}))。"""
    payload = {
        "receipt_kind": receipt_kind,
        "version": int(version),
        "fields": fields_dict,
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def build_receipt_envelope(
    receipt_kind: Literal["oof", "oot", "calibrator"],
    receipt: Any,
    *,
    version: int = RECEIPT_ENVELOPE_VERSION,
) -> Dict[str, Any]:
    """serialization envelope（API/service 一律用此結構）。"""
    fields_dict = asdict(receipt)
    digest = envelope_digest_for(receipt_kind, fields_dict, version=version)
    return {
        "receipt_kind": receipt_kind,
        "version": int(version),
        "fields": fields_dict,
        "envelope_digest": digest,
    }


@dataclass(frozen=True)
class OofReceipt:
    """OOF fold receipt（§0.6-A）。"""

    split_plan_hash: str
    fold_id: int
    fit_idx_hash: str
    eval_idx_hash: str
    model_artifact_digest: str
    trusted_issuer: str


@dataclass(frozen=True)
class OotReceipt:
    """OOT receipt（§0.6-A；PatternOotReceipt 別名）。"""

    split_plan_hash: str
    fit_label_end: int
    eval_start: int
    horizon: int
    embargo: int
    model_artifact_digest: str
    trusted_issuer: str


# Task 3.2 晉升用同一結構
PatternOotReceipt = OotReceipt


@dataclass(frozen=True)
class CalibratorReceipt:
    """Calibrator receipt（無 fold/eval_idx；calib∩train=∅）。"""

    split_plan_hash: str
    calib_idx_hash: str
    train_idx_hash: str
    model_artifact_digest: str
    trusted_issuer: str


def _assert_trusted_issuer(issuer: str) -> None:
    if issuer not in TRUSTED_RECEIPT_ISSUERS:
        raise ReceiptVerificationError(
            f"trusted_issuer {issuer!r} not in server allowlist"
        )


def _verify_envelope_step(
    *,
    receipt: Any,
    receipt_kind: Literal["oof", "oot", "calibrator"],
    envelope: Optional[Dict[str, Any]],
) -> None:
    """第④步：envelope 必填；比對 receipt_kind + version + fields（digest 涵蓋三者）。"""
    if envelope is None:
        raise ReceiptVerificationError(
            f"{receipt_kind} envelope is required (None not allowed; step ④ fail-closed)"
        )
    if not isinstance(envelope, dict):
        raise ReceiptVerificationError(f"{receipt_kind} envelope must be a dict")

    if envelope.get("receipt_kind") != receipt_kind:
        raise ReceiptVerificationError(
            f"{receipt_kind} envelope receipt_kind mismatch: "
            f"got {envelope.get('receipt_kind')!r}"
        )
    if int(envelope.get("version", -1)) != int(RECEIPT_ENVELOPE_VERSION):
        raise ReceiptVerificationError(
            f"{receipt_kind} envelope version mismatch: "
            f"got {envelope.get('version')!r}, expected {RECEIPT_ENVELOPE_VERSION}"
        )

    fields_dict = asdict(receipt)
    env_fields = envelope.get("fields")
    if env_fields is None:
        raise ReceiptVerificationError(f"{receipt_kind} envelope.fields is required")
    if env_fields != fields_dict:
        raise ReceiptVerificationError(
            f"{receipt_kind} envelope.fields does not match receipt asdict"
        )

    expected = envelope_digest_for(
        receipt_kind, fields_dict, version=int(envelope.get("version"))
    )
    if envelope.get("envelope_digest") != expected:
        raise ReceiptVerificationError(f"{receipt_kind} envelope_digest mismatch")


def verify_oof_receipt(
    receipt: OofReceipt,
    plan: "SplitPlan",
    fit_idx: Any,
    eval_idx: Any,
    model_artifact: bytes,
    *,
    envelope: Optional[Dict[str, Any]] = None,
) -> None:
    """四步重算：artifact digest + idx/plan hash + fit∩eval=∅ + envelope（必填）。"""
    _assert_trusted_issuer(receipt.trusted_issuer)

    # ① artifact digest
    expected_art = model_artifact_digest(model_artifact)
    if receipt.model_artifact_digest != expected_art:
        raise ReceiptVerificationError("OofReceipt model_artifact_digest mismatch")

    # ② plan / idx hash 重算
    plan_hash = canonical_split_plan_hash(plan)
    if receipt.split_plan_hash != plan_hash:
        raise ReceiptVerificationError("OofReceipt split_plan_hash mismatch")

    fit_hash = canonical_idx_hash(
        fit_idx,
        split_label=str(plan.split_label),
        symbol=str(plan.symbol or ""),
        base_universe_hash=str(plan.base_universe_hash),
    )
    eval_hash = canonical_idx_hash(
        eval_idx,
        split_label=str(plan.split_label),
        symbol=str(plan.symbol or ""),
        base_universe_hash=str(plan.base_universe_hash),
    )
    if receipt.fit_idx_hash != fit_hash:
        raise ReceiptVerificationError("OofReceipt fit_idx_hash mismatch")
    if receipt.eval_idx_hash != eval_hash:
        raise ReceiptVerificationError("OofReceipt eval_idx_hash mismatch")

    # ③ disjointness
    fit_set = set(_require_1d_row_index(fit_idx, where="fit_idx").astype(int).tolist())
    eval_set = set(_require_1d_row_index(eval_idx, where="eval_idx").astype(int).tolist())
    if fit_set & eval_set:
        raise ReceiptVerificationError("OofReceipt fit_idx ∩ eval_idx must be empty")

    # ④ envelope 必填：kind + version + fields + digest
    _verify_envelope_step(receipt=receipt, receipt_kind="oof", envelope=envelope)


def verify_oot_receipt(
    receipt: OotReceipt,
    train_plan: "SplitPlan",
    eval_plan: "SplitPlan",
    horizon: int,
    model_artifact: bytes,
    *,
    envelope: Optional[Dict[str, Any]] = None,
    bar_duration: Optional[Any] = None,
    ts: Optional[np.ndarray] = None,
) -> None:
    """四步重算：artifact + plan hash + horizon 嚴格 < + envelope（必填）。

    另經 ``validate_oot_label_horizon``：跨 symbol→CrossSymbolLeakageError；
    train→eval time_bounds gap→TimestampDiscontinuityError（B2-05）。
    """
    _assert_trusted_issuer(receipt.trusted_issuer)

    # ① artifact
    expected_art = model_artifact_digest(model_artifact)
    if receipt.model_artifact_digest != expected_art:
        raise ReceiptVerificationError("OotReceipt model_artifact_digest mismatch")

    # ② plan hash（train plan）
    plan_hash = canonical_split_plan_hash(train_plan)
    if receipt.split_plan_hash != plan_hash:
        raise ReceiptVerificationError("OotReceipt split_plan_hash mismatch")

    if int(receipt.horizon) != int(horizon):
        raise ReceiptVerificationError("OotReceipt horizon mismatch")

    train_rows = _require_1d_row_index(train_plan.row_index, where="train_plan.row_index")
    eval_rows = _require_1d_row_index(eval_plan.row_index, where="eval_plan.row_index")
    if train_rows.size == 0 or eval_rows.size == 0:
        raise ReceiptVerificationError("OotReceipt train/eval row_index must be non-empty")

    fit_label_end = int(train_rows.max()) + int(horizon)
    eval_start = int(eval_rows.min())
    embargo = int(receipt.embargo)
    if receipt.fit_label_end != fit_label_end:
        raise ReceiptVerificationError("OotReceipt fit_label_end mismatch")
    if receipt.eval_start != eval_start:
        raise ReceiptVerificationError("OotReceipt eval_start mismatch")

    # ③ horizon 嚴格 <（+ disjointness of row sets as safety）
    if not (fit_label_end + embargo < eval_start):
        raise ReceiptVerificationError(
            f"OotReceipt horizon boundary failed: "
            f"fit_label_end({fit_label_end})+embargo({embargo}) < eval_start({eval_start}) is False"
        )
    if set(train_rows.astype(int).tolist()) & set(eval_rows.astype(int).tolist()):
        raise ReceiptVerificationError("OotReceipt train∩eval row_index must be empty")

    # also re-run public horizon validator for timestamp branch consistency
    validate_oot_label_horizon(
        train_plan,
        eval_plan,
        horizon,
        bar_duration=bar_duration,
        ts=ts,
        embargo=embargo,
    )

    # ④ envelope 必填
    _verify_envelope_step(receipt=receipt, receipt_kind="oot", envelope=envelope)


def verify_calibrator_receipt(
    receipt: CalibratorReceipt,
    train_plan: "SplitPlan",
    calib_idx: Any,
    model_artifact: bytes,
    *,
    envelope: Optional[Dict[str, Any]] = None,
) -> None:
    """四步重算：artifact + hashes + calib∩train=∅ + envelope（必填）。"""
    _assert_trusted_issuer(receipt.trusted_issuer)

    # ① artifact
    expected_art = model_artifact_digest(model_artifact)
    if receipt.model_artifact_digest != expected_art:
        raise ReceiptVerificationError("CalibratorReceipt model_artifact_digest mismatch")

    # ② plan / idx hashes
    plan_hash = canonical_split_plan_hash(train_plan)
    if receipt.split_plan_hash != plan_hash:
        raise ReceiptVerificationError("CalibratorReceipt split_plan_hash mismatch")

    train_hash = canonical_idx_hash(
        train_plan.row_index,
        split_label=str(train_plan.split_label),
        symbol=str(train_plan.symbol or ""),
        base_universe_hash=str(train_plan.base_universe_hash),
    )
    calib_hash = canonical_idx_hash(
        calib_idx,
        split_label="calib",
        symbol=str(train_plan.symbol or ""),
        base_universe_hash=str(train_plan.base_universe_hash),
    )
    if receipt.train_idx_hash != train_hash:
        raise ReceiptVerificationError("CalibratorReceipt train_idx_hash mismatch")
    if receipt.calib_idx_hash != calib_hash:
        raise ReceiptVerificationError("CalibratorReceipt calib_idx_hash mismatch")

    # ③ disjointness
    train_set = set(
        _require_1d_row_index(train_plan.row_index, where="train_plan.row_index")
        .astype(int)
        .tolist()
    )
    calib_set = set(_require_1d_row_index(calib_idx, where="calib_idx").astype(int).tolist())
    if train_set & calib_set:
        raise ReceiptVerificationError(
            "CalibratorReceipt calib_idx ∩ train_plan.row_index must be empty"
        )

    # ④ envelope 必填
    _verify_envelope_step(receipt=receipt, receipt_kind="calibrator", envelope=envelope)


def _assert_oot_train_eval_same_symbol(
    train_plan: "SplitPlan",
    eval_plan: "SplitPlan",
) -> None:
    """OOT train/eval 必須同 symbol；跨 symbol → CrossSymbolLeakageError。"""
    t_sym = train_plan.symbol
    e_sym = eval_plan.symbol
    if t_sym is None and e_sym is None:
        return
    if t_sym is None or e_sym is None:
        raise CrossSymbolLeakageError(
            "train/eval SplitPlan symbols must both be set or both None"
        )
    if _normalize_symbol_value(t_sym) != _normalize_symbol_value(e_sym):
        raise CrossSymbolLeakageError(
            "train/eval SplitPlan symbols must match (cross-symbol OOT blocked)"
        )


def _is_datetime_time_bound(value: Any) -> bool:
    """time_bounds 元素是否為可解析的 datetime（非純數值 ordinal）。"""
    if value is None:
        return False
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return True
    if isinstance(value, datetime):
        return True
    if isinstance(value, str):
        try:
            return not pd.isna(pd.Timestamp(value))
        except (TypeError, ValueError, pd.errors.OutOfBoundsDatetime):
            return False
    return False


def _assert_oot_train_eval_time_bounds_continuity(
    train_plan: "SplitPlan",
    eval_plan: "SplitPlan",
    train_rows: np.ndarray,
    eval_rows: np.ndarray,
) -> None:
    """即使 row 空間 strict < 成立，train 尾→eval 首 time_bounds 不連續/跨界仍 raise。

    使用 SplitPlan.time_bounds + expected_freq 對照 row_gap：
    - datetime bounds：actual Δt 必須 ≈ row_gap * expected_freq
    - 數值 ordinal bounds：bound_gap 必須 == row_gap
    time_bounds 缺端點則跳過（相容舊 synthetic plan）。
    """
    tb_t = train_plan.time_bounds
    tb_e = eval_plan.time_bounds
    if tb_t is None or tb_e is None:
        return
    if len(tb_t) < 2 or len(tb_e) < 2:
        return
    train_end, eval_start = tb_t[1], tb_e[0]
    if train_end is None or eval_start is None:
        return

    row_gap = int(eval_rows.min()) - int(train_rows.max())

    if _is_datetime_time_bound(train_end) or _is_datetime_time_bound(eval_start):
        try:
            te = pd.Timestamp(train_end)
            es = pd.Timestamp(eval_start)
        except (TypeError, ValueError, pd.errors.OutOfBoundsDatetime) as exc:
            raise TimestampDiscontinuityError(
                "OOT time_bounds train_end/eval_start not parseable as timestamps"
            ) from exc
        if pd.isna(te) or pd.isna(es):
            raise TimestampDiscontinuityError("OOT time_bounds contain NaT")
        if es <= te:
            raise TimestampDiscontinuityError(
                "OOT time_bounds: eval_start must be after train_end"
            )
        freq = train_plan.expected_freq or eval_plan.expected_freq
        if freq is None:
            raise TimestampDiscontinuityError(
                "OOT time_bounds datetime gap check requires expected_freq"
            )
        if row_gap <= 0:
            raise TimestampDiscontinuityError(
                "OOT time_bounds/row_index inconsistent (non-positive row gap)"
            )
        expected_delta = row_gap * pd.Timedelta(freq)
        actual_delta = es - te
        tol = max(pd.Timedelta(freq) * 0.05, pd.Timedelta(nanoseconds=1))
        if abs(actual_delta - expected_delta) > tol:
            raise TimestampDiscontinuityError(
                "train→eval timestamp gap discontinuous/cross-boundary: "
                f"actual={actual_delta}, expected_from_rows≈{expected_delta} "
                f"(row_gap={row_gap}, freq={freq})"
            )
        return

    # 數值 ordinal bounds（build_train_oot_split_plans 等）
    try:
        te_n = float(train_end)
        es_n = float(eval_start)
    except (TypeError, ValueError):
        return
    bound_gap = es_n - te_n
    if abs(bound_gap - float(row_gap)) > 1e-9:
        raise TimestampDiscontinuityError(
            f"train→eval time_bounds gap ({bound_gap}) != row gap ({row_gap})"
        )


def validate_oot_label_horizon(
    train_plan: "SplitPlan",
    eval_plan: "SplitPlan",
    horizon: int,
    bar_duration: Optional[Any] = None,
    ts: Optional[np.ndarray] = None,
    *,
    embargo: Optional[int] = None,
) -> None:
    """horizon-aware OOT 邊界（嚴格 <）。

    row 空間：fit_label_end(=max(train.row_index)+horizon)+embargo < min(eval.row_index)
    timestamp 分支：max(fit_ts)+(horizon+embargo)*bar_duration < min(eval_ts)；
    缺 bar_duration / expected_freq / gap(discontinuity) → raise（禁 fallback row）。

    另（B2-05）：
    - train_plan.symbol != eval_plan.symbol → CrossSymbolLeakageError
    - train 尾→eval 首 time_bounds 不連續/跨界（即使 strict <）→ TimestampDiscontinuityError
    """
    if int(horizon) < 0:
        raise SplitPairLeakageError("horizon must be non-negative")

    train_rows = np.asarray(train_plan.row_index, dtype=int)
    eval_rows = np.asarray(eval_plan.row_index, dtype=int)
    if train_rows.size == 0 or eval_rows.size == 0:
        raise SplitPairLeakageError("train/eval row_index must be non-empty for OOT horizon")

    # B2-05：跨 symbol 一律擋（先於 horizon，fail-closed）
    _assert_oot_train_eval_same_symbol(train_plan, eval_plan)

    emb = int(embargo if embargo is not None else max(int(eval_plan.embargo), 0))
    fit_label_end = int(train_rows.max()) + int(horizon)
    eval_start = int(eval_rows.min())

    index_kind = str(train_plan.index_kind)
    if index_kind == "timestamp":
        # hard-fail (U8): 缺 bar_duration / expected_freq / ts → raise
        if bar_duration is None:
            raise SplitPairLeakageError(
                "timestamp OOT requires bar_duration (no fallback to row check)"
            )
        if train_plan.expected_freq is None and eval_plan.expected_freq is None:
            raise SplitPairLeakageError(
                "timestamp OOT requires expected_freq on train or eval plan"
            )
        if ts is None:
            raise SplitPairLeakageError(
                "timestamp OOT requires ts array for discontinuity check"
            )
        ts_arr = _coerce_timestamp_array(ts)
        if np.any(train_rows < 0) or np.any(train_rows >= len(ts_arr)):
            raise IndexError("train_plan.row_index outside ts")
        if np.any(eval_rows < 0) or np.any(eval_rows >= len(ts_arr)):
            raise IndexError("eval_plan.row_index outside ts")
        fit_ts = ts_arr[train_rows]
        eval_ts = ts_arr[eval_rows]
        if fit_ts.size > 1:
            diffs = np.diff(fit_ts)
            if np.any(diffs <= np.timedelta64(0, "ns")):
                raise TimestampDiscontinuityError(
                    "timestamp OOT: fit timestamps not strictly increasing"
                )
            expected_delta = pd.Timedelta(
                train_plan.expected_freq or eval_plan.expected_freq
            )
            max_gap = pd.Timedelta(np.max(diffs))
            if max_gap > expected_delta * 1.05:
                raise TimestampDiscontinuityError(
                    "timestamp OOT: discontinuity/gap exceeds expected_freq"
                )
        # bar_duration: accept Timedelta / str / numeric seconds
        if isinstance(bar_duration, (int, float, np.integer, np.floating)):
            bd = pd.Timedelta(seconds=float(bar_duration))
        else:
            bd = pd.Timedelta(bar_duration)
        fit_end_ts = pd.Timestamp(fit_ts.max()) + (int(horizon) + emb) * bd
        eval_start_ts = pd.Timestamp(eval_ts.min())
        if not (fit_end_ts < eval_start_ts):
            raise SplitPairLeakageError(
                f"timestamp OOT boundary failed: "
                f"max(fit_ts)+(horizon+embargo)*bar_duration={fit_end_ts} "
                f"< min(eval_ts)={eval_start_ts} is False"
            )
        # B2-05：time_bounds 跨界/gap（即使 ts[rows] strict < 已過）
        _assert_oot_train_eval_time_bounds_continuity(
            train_plan, eval_plan, train_rows, eval_rows
        )
        return

    # row / positional / row_id 空間：嚴格 <
    if not (fit_label_end + emb < eval_start):
        raise SplitPairLeakageError(
            f"OOT label-horizon boundary failed: "
            f"fit_label_end({fit_label_end})+embargo({emb}) < eval_start({eval_start}) "
            f"is False (strict <; equality is leakage)"
        )
    # B2-05：time_bounds gap（即使 strict < 成立）
    _assert_oot_train_eval_time_bounds_continuity(
        train_plan, eval_plan, train_rows, eval_rows
    )


def make_oot_receipt(
    train_plan: "SplitPlan",
    eval_plan: "SplitPlan",
    horizon: int,
    model_artifact: bytes,
    *,
    trusted_issuer: str,
    embargo: Optional[int] = None,
) -> OotReceipt:
    """產 OotReceipt（先 validate_oot_label_horizon；row_index 必須 1-D）。"""
    _require_1d_row_index(train_plan.row_index, where="train_plan.row_index")
    _require_1d_row_index(eval_plan.row_index, where="eval_plan.row_index")
    emb = int(embargo if embargo is not None else max(int(eval_plan.embargo), 0))
    validate_oot_label_horizon(train_plan, eval_plan, horizon, embargo=emb)
    train_rows = np.asarray(train_plan.row_index, dtype=int)
    eval_rows = np.asarray(eval_plan.row_index, dtype=int)
    return OotReceipt(
        split_plan_hash=canonical_split_plan_hash(train_plan),
        fit_label_end=int(train_rows.max()) + int(horizon),
        eval_start=int(eval_rows.min()),
        horizon=int(horizon),
        embargo=emb,
        model_artifact_digest=model_artifact_digest(model_artifact),
        trusted_issuer=trusted_issuer,
    )


def make_oof_receipt(
    plan: "SplitPlan",
    fold_id: int,
    fit_idx: Any,
    eval_idx: Any,
    model_artifact: bytes,
    *,
    trusted_issuer: str,
) -> OofReceipt:
    """產 OofReceipt（fit∩eval 必須空；2-D idx → raise，禁 reshape 繞過）。"""
    fit_arr = _require_1d_row_index(fit_idx, where="fit_idx").astype(int)
    eval_arr = _require_1d_row_index(eval_idx, where="eval_idx").astype(int)
    if set(fit_arr.tolist()) & set(eval_arr.tolist()):
        raise ReceiptVerificationError("cannot make OofReceipt with overlapping fit/eval")
    return OofReceipt(
        split_plan_hash=canonical_split_plan_hash(plan),
        fold_id=int(fold_id),
        fit_idx_hash=canonical_idx_hash(
            fit_arr,
            split_label=str(plan.split_label),
            symbol=str(plan.symbol or ""),
            base_universe_hash=str(plan.base_universe_hash),
        ),
        eval_idx_hash=canonical_idx_hash(
            eval_arr,
            split_label=str(plan.split_label),
            symbol=str(plan.symbol or ""),
            base_universe_hash=str(plan.base_universe_hash),
        ),
        model_artifact_digest=model_artifact_digest(model_artifact),
        trusted_issuer=trusted_issuer,
    )


def make_calibrator_receipt(
    train_plan: "SplitPlan",
    calib_idx: Any,
    model_artifact: bytes,
    *,
    trusted_issuer: str,
) -> CalibratorReceipt:
    """產 CalibratorReceipt（calib∩train 必須空；2-D idx → raise）。"""
    train_arr = _require_1d_row_index(train_plan.row_index, where="train_plan.row_index")
    train_set = set(train_arr.astype(int).tolist())
    calib_arr = _require_1d_row_index(calib_idx, where="calib_idx").astype(int)
    if train_set & set(calib_arr.tolist()):
        raise ReceiptVerificationError(
            "cannot make CalibratorReceipt with calib∩train overlap"
        )
    return CalibratorReceipt(
        split_plan_hash=canonical_split_plan_hash(train_plan),
        calib_idx_hash=canonical_idx_hash(
            calib_arr,
            split_label="calib",
            symbol=str(train_plan.symbol or ""),
            base_universe_hash=str(train_plan.base_universe_hash),
        ),
        train_idx_hash=canonical_idx_hash(
            train_plan.row_index,
            split_label=str(train_plan.split_label),
            symbol=str(train_plan.symbol or ""),
            base_universe_hash=str(train_plan.base_universe_hash),
        ),
        model_artifact_digest=model_artifact_digest(model_artifact),
        trusted_issuer=trusted_issuer,
    )


def build_train_oot_split_plans(
    n_samples: int,
    *,
    oot_ratio: float = 0.2,
    horizon: int = 1,
    embargo: int = 0,
    purge_gap: int = 0,
    symbol: Optional[str] = None,
    base_universe_hash: str = "service_run",
    index_kind: Literal["timestamp", "positional", "row_id"] = "positional",
    expected_freq: Optional[str] = None,
    min_oot_samples: int = 10,
    min_train_samples: int = 20,
) -> Optional[Tuple["SplitPlan", "SplitPlan"]]:
    """依時間序切 train/OOT SplitPlan（嚴格 horizon 邊界）。

    有足夠 held-out 時回傳 (train_plan, oot_plan)；不足則 None（caller OMIT）。
    eval 起點 = train_end + horizon + embargo + 1（保證 fit_label_end+embargo < eval_start）。
    """
    if n_samples <= 0 or oot_ratio <= 0.0 or oot_ratio >= 1.0:
        return None
    n_oot_target = max(int(np.floor(n_samples * float(oot_ratio))), int(min_oot_samples))
    if n_oot_target >= n_samples:
        return None
    # 預留 horizon+embargo gap 於 train 與 oot 之間
    gap = int(horizon) + int(embargo) + 1
    # oot 起於 n_samples - n_oot；train 終於 oot_start - gap
    oot_start = n_samples - n_oot_target
    train_end_exclusive = oot_start - gap + 1  # train rows [0, train_end_exclusive)
    # max(train)=train_end_exclusive-1; fit_label_end=(train_end-1)+horizon
    # 需 fit_label_end + embargo < oot_start
    # → train_end_exclusive - 1 + horizon + embargo < oot_start
    # → train_end_exclusive <= oot_start - horizon - embargo
    # with gap = h+e+1: train_end = oot_start - gap + 1 = oot_start - h - e
    # max train = oot_start - h - e - 1; fit_end+emb = oot_start - 1 < oot_start ✓
    if train_end_exclusive < int(min_train_samples):
        return None
    if oot_start >= n_samples or train_end_exclusive <= 0:
        return None

    train_rows = np.arange(0, train_end_exclusive, dtype=int)
    oot_rows = np.arange(oot_start, n_samples, dtype=int)
    if train_rows.size < int(min_train_samples) or oot_rows.size < int(min_oot_samples):
        return None

    universe = base_universe_hash or "service_run"
    train_plan = SplitPlan(
        split_label="train",
        index_kind=index_kind,
        row_index=train_rows,
        time_bounds=(int(train_rows.min()), int(train_rows.max())),
        purge_gap=int(purge_gap),
        embargo=int(embargo),
        purge_semantic="rows",
        expected_freq=expected_freq,
        base_universe_hash=universe,
        symbol=symbol,
    )
    oot_plan = SplitPlan(
        split_label="test",
        index_kind=index_kind,
        row_index=oot_rows,
        time_bounds=(int(oot_rows.min()), int(oot_rows.max())),
        purge_gap=int(purge_gap),
        embargo=int(embargo),
        purge_semantic="rows",
        expected_freq=expected_freq,
        base_universe_hash=universe,
        symbol=symbol,
    )
    # 預先驗證；失敗則視為無可用 OOT
    try:
        validate_oot_label_horizon(train_plan, oot_plan, horizon, embargo=embargo)
    except (
        SplitPairLeakageError,
        CrossSymbolLeakageError,
        TimestampDiscontinuityError,
        ValueError,
        IndexError,
    ):
        return None
    return train_plan, oot_plan


# ── Factor discriminated union（B2 建型別；B3 接線）──────────────────────────


@dataclass(frozen=True)
class OrthogonalizationPayload:
    method: str
    orthogonalized_hash: str
    summary: Dict[str, Any]


@dataclass(frozen=True)
class ExposurePayload:
    proxy_kind: Literal["trailing_close_ret"]
    exposure_hash: str
    summary: Dict[str, Any]


@dataclass(frozen=True)
class FactorModuleResult:
    """C-3 loud factor result（discriminated union）。"""

    module: Literal["orthogonalization", "exposure"]
    oos_guarantees: Literal[False]
    fit_scope: Literal["full_sample"]
    payload: Union[OrthogonalizationPayload, ExposurePayload]

    def __post_init__(self) -> None:
        if self.oos_guarantees is not False:
            raise ValueError("FactorModuleResult.oos_guarantees must be False")
        if self.fit_scope != "full_sample":
            raise ValueError("FactorModuleResult.fit_scope must be 'full_sample'")
        if self.module == "orthogonalization" and not isinstance(
            self.payload, OrthogonalizationPayload
        ):
            raise ValueError("module=orthogonalization requires OrthogonalizationPayload")
        if self.module == "exposure" and not isinstance(self.payload, ExposurePayload):
            raise ValueError("module=exposure requires ExposurePayload")


def deny_factor_in_ok_oos(report: Dict[str, Any]) -> None:
    """root analysis_status==ok_oos 且 factor/diagnostic loud 存在 → raise。

    B3 consumer/export/persist 出口呼叫；B2 只建型別與 verifier。
    亦掃 nested ``diagnostic_only`` / ``signal_use_denied``（U18 adversarial）。
    """
    if not isinstance(report, dict):
        return
    root_status = report.get("analysis_status")
    if root_status != "ok_oos":
        return

    def _walk(node: Any, *, is_root: bool = False) -> None:
        if isinstance(node, FactorModuleResult):
            raise ValueError(
                "deny_factor_in_ok_oos: FactorModuleResult present under ok_oos"
            )
        if isinstance(node, dict):
            # nested diagnostic_only / signal_use_denied under ok_oos → deny signal
            if not is_root and (
                node.get("signal_use_denied") is True
                or node.get("diagnostic_only") is True
                or node.get("analysis_status") == "diagnostic_only"
            ):
                raise ValueError(
                    "deny_factor_in_ok_oos: diagnostic_only/signal_use_denied under ok_oos"
                )
            # raw dict 亦 deny（掃 oos_guarantees 鍵 / module factor）
            if (
                "oos_guarantees" in node
                and node.get("oos_guarantees") is False
                and node.get("fit_scope") == "full_sample"
                and node.get("module") in {"orthogonalization", "exposure"}
            ):
                raise ValueError(
                    "deny_factor_in_ok_oos: factor loud dict present under ok_oos"
                )
            for value in node.values():
                _walk(value, is_root=False)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _walk(item, is_root=False)

    _walk(report, is_root=True)


def build_eval_scope_map(keys: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """回傳欄位→eval_scope 對照（供 model_performance 掛 eval_scope）。

    B2-06：keys 中任一不在 §0.6-C 28-path 閉集 → fail-closed raise（禁靜默省略）。
    """
    if keys is None:
        return dict(MODEL_PERFORMANCE_EVAL_SCOPE)
    out: Dict[str, str] = {}
    unknown: List[str] = []
    for k in keys:
        key = str(k)
        if key not in MODEL_PERFORMANCE_EVAL_SCOPE:
            unknown.append(key)
            continue
        out[key] = MODEL_PERFORMANCE_EVAL_SCOPE[key]
    if unknown:
        raise ValueError(
            "unknown eval_scope metric(s) not in 28-path canonical set: "
            + ", ".join(unknown)
        )
    return out


def tag_model_performance_scopes(performance: Dict[str, Any]) -> Dict[str, Any]:
    """為 model_performance dict 掛 eval_scope 子表 + consumer_deny 清單。

    eval_scope 只含 28-path 閉集；若呼叫端把 unlisted metric 塞進既有
    ``eval_scope`` 子表 → fail-closed（B2-06 service 不得保留 unlisted field）。
    """
    out = dict(performance)
    # B2-06：既有 eval_scope 若含非 canonical field → raise（禁靜默保留）
    prior_scope = out.get("eval_scope")
    if isinstance(prior_scope, dict):
        unknown_prior = [
            str(k) for k in prior_scope.keys() if str(k) not in MODEL_PERFORMANCE_EVAL_SCOPE
        ]
        if unknown_prior:
            raise ValueError(
                "unknown eval_scope metric(s) not in 28-path canonical set: "
                + ", ".join(unknown_prior)
            )
    present = [k for k in out.keys() if k in MODEL_PERFORMANCE_EVAL_SCOPE]
    # nested predictions
    preds = out.get("predictions")
    if isinstance(preds, dict):
        for sub in ("train", "oot"):
            path = f"predictions/{sub}"
            if sub in preds and path in MODEL_PERFORMANCE_EVAL_SCOPE:
                present.append(path)
    out["eval_scope"] = {k: MODEL_PERFORMANCE_EVAL_SCOPE[k] for k in present}
    out["consumer_deny"] = sorted(
        k for k in present if k in EVAL_SCOPE_CONSUMER_DENY or (
            k in MODEL_PERFORMANCE_EVAL_SCOPE
            and MODEL_PERFORMANCE_EVAL_SCOPE[k] == "in_sample_research_only"
        )
    )
    return out
