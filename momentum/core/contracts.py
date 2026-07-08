"""Momentum internal DTO contracts.

This module re-exports pure data types (enums, dataclasses, Pydantic models)
from domain-internal modules so that ``api/`` can depend on
``momentum.core.contracts`` instead of reaching into domain internals (Rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections.abc import Callable, Iterable
from typing import Any, Dict, List, Literal, Optional, Tuple

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
    split_label: Literal["train", "val", "test"]
    evaluated_features: List[str]
    n_tests: int
    method: str
    base_universe_hash: str

    def __post_init__(self) -> None:
        """驗證 evaluated_features 必須屬於 universe 且 n_tests 一致。"""
        if self.split_label not in {"train", "val", "test"}:
            raise ValueError("split_label must be one of train, val, test")
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


def validate_alignment(
    feature_data: Any,
    target_data: Any,
    spec: AlignmentSpec,
    *,
    close: Optional[pd.Series] = None,
    sample_size: int = 64,
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
            expected = float(np.log(future / current))
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
