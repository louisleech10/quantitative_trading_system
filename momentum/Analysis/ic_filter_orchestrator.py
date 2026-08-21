"""IC filter orchestrator for Gatekeeper pipeline."""

from __future__ import annotations

import json
import hashlib
import math
import re
import time
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from momentum.Analysis.factor_return_analyzer import FactorTimingReturnSeries

import h5py
import numpy as np
import pandas as pd

from momentum.Analysis.coverage_analyzer import CoverageAnalyzer
from momentum.Analysis.data_preprocessor import DataPreprocessor
from momentum.Analysis.event_filter import EventFilter
from momentum.Analysis.factor_combiner import combine_factors
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_reporter import ICReporter
from momentum.Analysis.marginal_ic import MarginalICParams, compute_marginal_ic
from momentum.Analysis.monotonicity_tester import MonotonicityTester
from momentum.Analysis.pit_stats import PIT_STATS_VERSION
from momentum.Analysis.redundancy_filter import RedundancyFilter
from scipy import stats as scipy_stats

from momentum.Analysis.survivor_contract import (
    build_survivor_output,
    compute_event_identity,
    load_survivor_contract,
    validate_survivor_output,
)
from momentum.Analysis.statistical_validator import (
    StatisticalValidator,
    _hac_nan_result,
    _newey_west_bartlett_se,
    apply_fdr,
    compute_hac_ic_statistics,
)
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer
from momentum.Analysis.ic_config_schema import FeatureFilterSchema, ICConfig
from momentum.Analysis.deep_analysis_types import DeepAnalysisReport, SkippedResult
from momentum.core.exceptions import (
    InsufficientDataError,
    InvalidInputError,
    ModuleUnavailableError,
)
from momentum.core.logging import get_logger
from momentum.core.contracts import (
    ORACLE_RETURN_KINDS,
    AlignmentSpec,
    AlignmentViolationError,
    ExposurePayload,
    FactorModuleResult,
    OrthogonalizationPayload,
    SelectionScope,
    SplitPlan,
    TimestampDiscontinuityError,
    deny_factor_in_ok_oos,
    _coerce_timestamp_array,
    _normalize_symbol_value,
    split_per_symbol,
    validate_alignment,
    validate_split_pair_integrity,
)
from momentum.core.protocols import IKlineReader
from momentum.factories import create_label_generator
from momentum.Analysis.ic_split_adapter import ICSplitAdapter


logger = get_logger(__name__)


MODULE_ENABLED_PATHS: dict[str, tuple[str, str]] = {
    "factor_return": ("factor_return", "enabled"),
    "factor_centrality": ("factor_centrality", "enabled"),
    "trend_analysis": ("trend_analysis", "enabled"),
    "parameter_sensitivity": ("parameter_sensitivity", "enabled"),
    "rolling_oos": ("rolling_oos", "enabled"),
    "factor_orthogonalization": ("factor_orthogonalization", "enabled"),
    "factor_exposure": ("factor_exposure", "enabled"),
    "long_short_analysis": ("long_short_analysis", "enabled"),
    "feature_quality_diagnostics": ("feature_quality_diagnostics", "enabled"),
    "net_ic_analysis": ("net_ic_analysis", "enabled"),
}

LOCKED_STAGE_KEYS: set[str] = {
    "ic_calculation",
    "preprocessing",
    "statistical_validation",
    "redundancy_filter",
    "report_generation",
    "ai_summary",
}

# path 可為二層或更深嵌套；fdr_correction 為 UI 邊界唯一轉名點 → significance.fdr.enabled
STAGE_OVERRIDE_PATHS: dict[str, tuple[str, ...]] = {
    "event_filtering": ("event_filter", "enabled"),
    "ic_decay": ("report", "include_decay_analysis"),
    "grouped_ic": ("report", "include_regime_analysis"),
    "turnover_analysis": ("turnover", "enabled"),
    "ai_summary": ("report", "ai_summary"),
    "fdr_correction": ("significance", "fdr", "enabled"),
    "marginal_ic": ("marginal_ic", "enabled"),  # GAP-2 Task 4.1（B5 toggle／wiring R1b）
}


def _set_nested_bool(data: dict, path: tuple[str, ...], value: bool) -> None:
    """沿 path 設定巢狀 bool；中途缺節或非 dict 則靜默跳過（保既有未知 key 行為）。"""
    if not path:
        return
    cursor: Any = data
    for part in path[:-1]:
        if not isinstance(cursor, dict):
            return
        child = cursor.get(part)
        if not isinstance(child, dict):
            return
        cursor = child
    if isinstance(cursor, dict):
        cursor[path[-1]] = bool(value)


def _config_significance_maxlags(config: ICConfig) -> Optional[int]:
    """自 schema 讀 significance.maxlags（None=自動頻寬）。"""
    sig = getattr(config, "significance", None)
    if sig is None:
        return None
    raw = sig.get("maxlags") if isinstance(sig, dict) else getattr(sig, "maxlags", None)
    if raw is None:
        return None
    return int(raw)

EXPECTED_FREQ_BY_TIMEFRAME: dict[str, pd.Timedelta] = {
    "1h": pd.Timedelta("1h"),
    "4h": pd.Timedelta("4h"),
    "12h": pd.Timedelta("12h"),
}

# D-F / Composer v2.2：固定一行 PRDS 披露（report metadata significance.fdr_assumption_note）
FDR_ASSUMPTION_NOTE = (
    "BH assumes PRDS; correlated features may yield slight FDR optimism"
)
TESTED_ESTIMATOR_BAR_LEVEL = "bar_level_spearman"
TESTED_ESTIMATOR_XSEC_PERIOD_IC = "cross_sectional_period_ic"


def _resolve_expected_freq(metadata: Optional[dict]) -> pd.Timedelta:
    """由 metadata 的 timeframe 推導 rows purge 需要的固定頻率。"""
    timeframe = (metadata or {}).get("timeframe")
    if timeframe not in EXPECTED_FREQ_BY_TIMEFRAME:
        raise ValueError(f"Unsupported or missing timeframe for IC split: {timeframe!r}")
    return EXPECTED_FREQ_BY_TIMEFRAME[timeframe]


def _alignment_freq_from_metadata(metadata: Optional[dict]) -> str:
    """由 metadata 取得 alignment gate 使用的 pandas freq 字串。"""
    timeframe = (metadata or {}).get("timeframe")
    if timeframe not in EXPECTED_FREQ_BY_TIMEFRAME:
        raise ValueError(f"Unsupported or missing timeframe for alignment: {timeframe!r}")
    return str(timeframe)


def _normalize_ic_time_index(index: pd.Index, role: str) -> pd.DatetimeIndex:
    """D-1/D-4: DatetimeIndex 或 int64 epoch 秒正規化為 DatetimeIndex。"""
    if isinstance(index, pd.MultiIndex):
        raise AlignmentViolationError(f"{role} index must not be MultiIndex")
    if isinstance(index, pd.RangeIndex):
        raise AlignmentViolationError(f"{role} index must carry timestamps, not RangeIndex")

    if isinstance(index, pd.DatetimeIndex):
        ts = pd.DatetimeIndex(index)
    elif pd.api.types.is_integer_dtype(index.dtype):
        values = index.to_numpy(dtype=np.int64)
        if values.size and bool(np.any(np.abs(values) > 1_000_000_000_000)):
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
    return pd.DatetimeIndex(ts, name=index.name)


def _normalize_frame_time_index(frame: pd.DataFrame, role: str) -> pd.DatetimeIndex:
    """取 DataFrame timestamp 欄或 index 作 D-1 時間軸。"""
    if "timestamp" in frame.columns:
        return _normalize_ic_time_index(pd.Index(frame["timestamp"], name="timestamp"), role)
    return _normalize_ic_time_index(frame.index, role)


def _numeric_payload_sha256(data: pd.Series | pd.DataFrame) -> str:
    """值守恆 receipt: index rewrite 前後數值 payload 必須相同。"""
    values = data.to_numpy(copy=False)
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def _assign_datetime_index_preserving_values(
    data: pd.Series | pd.DataFrame,
    index: pd.DatetimeIndex,
    role: str,
) -> pd.Series | pd.DataFrame:
    """D-4 寫回 DatetimeIndex，且驗證只改 index、不改值。"""
    before = _numeric_payload_sha256(data)
    updated = data.copy(deep=False)
    updated.index = pd.DatetimeIndex(index, name=data.index.name)
    after = _numeric_payload_sha256(updated)
    if before != after:
        raise AlignmentViolationError(f"{role} index normalization changed values")
    return updated


def _alignment_spec(metadata: Optional[dict], horizon: int) -> AlignmentSpec:
    return AlignmentSpec(
        feature_ts_col="timestamp",
        target_ts_col="timestamp",
        lag=int(horizon),
        freq=_alignment_freq_from_metadata(metadata),
    )


def _resolve_metadata_symbol_allowlist(
    metadata: Optional[dict],
    allowed_symbols: Optional[set[str]] = None,
) -> set[str]:
    """由單幣 metadata 建立並驗證 split symbol allowlist。"""
    if metadata is None or "symbol" not in metadata:
        raise ValueError("metadata.symbol is required for IC train/test split")
    symbol = _normalize_symbol_value(metadata["symbol"])
    normalized_allowed = (
        {_normalize_symbol_value(value) for value in allowed_symbols}
        if allowed_symbols is not None
        else {symbol}
    )
    if symbol not in normalized_allowed:
        raise ValueError("metadata.symbol is outside allowed_symbols")
    return {symbol}


def _resolve_effective_label_horizon(
    config: ICConfig,
    labels_df: Optional[pd.DataFrame],
) -> int:
    """解析實際 label horizon；labels 欄名優先，無 labels 時才 fallback。"""
    if labels_df is not None:
        parsed: list[tuple[str, int]] = []
        for column in labels_df.columns:
            try:
                parsed.append((str(column), _resolve_label_horizon_from_column(str(column), config)))
            except InvalidInputError:
                continue
        if not parsed:
            raise InvalidInputError("label horizon cannot be resolved from labels_df columns")
        default_horizon = int(config.global_settings.default_horizon)
        selected_column, resolved = parsed[0]
        for column, horizon in parsed:
            if horizon == default_horizon:
                selected_column = column
                resolved = horizon
                break
        logger.info(
            "Resolved label horizon from labels_df column",
            extra={
                "horizon_source": "column_parse",
                "effective_horizon": int(resolved),
                "selected_label_column": selected_column,
                "parsed_label_horizons": {column: horizon for column, horizon in parsed},
            },
        )
        if default_horizon == resolved:
            return default_horizon
        return int(resolved)

    horizons = list(config.labels.horizons or [])
    if not horizons:
        raise ValueError("labels.horizons must contain at least one horizon")
    default_horizon = int(config.global_settings.default_horizon)
    resolved = default_horizon if default_horizon in horizons else int(horizons[0])
    logger.warning(
        "Falling back to configured label horizon because labels_df is unavailable",
        extra={"horizon_source": "default_fallback", "effective_horizon": resolved},
    )
    return resolved


def _resolve_label_horizon_from_column(name: str, config: ICConfig) -> int:
    """由 label 欄名解析 bar 數 horizon；無法證明單位換算時 fail-closed。"""
    del config
    match = re.fullmatch(r"return_(\d+)", name)
    if match:
        return int(match.group(1))
    unit_match = re.fullmatch(r"(?:label_)?return_(\d+)([a-zA-Z]+)", name)
    if unit_match:
        raise InvalidInputError(f"label horizon has unsupported unit: {name}")
    raise InvalidInputError(f"label horizon cannot be resolved from column: {name}")


def _base_universe_hash(index: pd.Index, symbol: str) -> str:
    """用 symbol/timestamp/row_pos 建立 split base universe hash。"""
    ts_arr = _coerce_timestamp_array(index.to_numpy())
    identity = pd.util.hash_pandas_object(
        pd.DataFrame(
            {
                "symbol": [_normalize_symbol_value(symbol)] * len(index),
                "timestamp": ts_arr,
                "_split_row_pos": np.arange(len(index), dtype=int),
            }
        ),
        index=True,
    ).values
    return hashlib.sha256(identity.tobytes()).hexdigest()


def _validate_expected_frequency(index: pd.Index, expected_freq: pd.Timedelta) -> None:
    """確認 rows purge 的 base universe 是固定頻率時間軸。"""
    ts_arr = _coerce_timestamp_array(index.to_numpy())
    if ts_arr.size <= 1:
        return
    diffs = np.diff(ts_arr)
    if np.any(diffs <= np.timedelta64(0, "ns")):
        raise TimestampDiscontinuityError(
            "base timestamps must be strictly increasing without duplicates"
        )
    expected_delta = expected_freq.to_timedelta64()
    tolerance = max(
        pd.Timedelta(expected_freq).value * 0.05,
        pd.Timedelta("1ns").value,
    )
    diff_ns = diffs.astype("timedelta64[ns]").astype(np.int64)
    expected_ns = np.timedelta64(expected_delta, "ns").astype(np.int64)
    if np.any(np.abs(diff_ns - expected_ns) > tolerance):
        raise TimestampDiscontinuityError(
            "rows purge requires continuous timestamps at expected_freq"
        )


def _time_bounds_for_rows(index: pd.Index, row_index: np.ndarray) -> tuple:
    if row_index.size == 0:
        return (None, None)
    ts_arr = _coerce_timestamp_array(index.to_numpy())
    selected = ts_arr[row_index]
    return (pd.Timestamp(selected[0]), pd.Timestamp(selected[-1]))


def _build_holdout_split_plan(
    features_df: pd.DataFrame,
    config: ICConfig,
    symbol: str,
    expected_freq: pd.Timedelta,
    purge_gap: int,
    labels_df: Optional[pd.DataFrame] = None,
) -> tuple[SplitPlan, SplitPlan] | SkippedResult:
    """建立單幣 chronological holdout train/test SplitPlan。"""
    effective_horizon = _resolve_effective_label_horizon(config, labels_df)
    if int(purge_gap) < effective_horizon:
        raise ValueError("purge_gap must be >= effective label horizon")
    n_rows = len(features_df)
    _validate_expected_frequency(features_df.index, expected_freq)
    split_point = int(np.floor((1.0 - float(config.oos_test_size)) * n_rows))
    effective_purge = max(int(purge_gap), effective_horizon, 0)
    effective_embargo = int(config.embargo)
    train_rows = np.arange(0, split_point, dtype=int)
    test_rows = np.arange(split_point + effective_purge + effective_embargo, n_rows, dtype=int)
    min_rows = int(config.min_test_rows)
    if train_rows.size < min_rows or test_rows.size < min_rows:
        return SkippedResult(
            "ic_train_test_split",
            "train/test rows below min_test_rows",
            "INSUFFICIENT_DATA",
            {
                "train_rows": int(train_rows.size),
                "test_rows": int(test_rows.size),
                "min_test_rows": min_rows,
            },
        )

    normalized_symbol = _normalize_symbol_value(symbol)
    universe_hash = _base_universe_hash(features_df.index, normalized_symbol)
    plan_kwargs = {
        "index_kind": "positional",
        "purge_gap": effective_purge,
        "embargo": effective_embargo,
        "purge_semantic": "rows",
        "expected_freq": str(expected_freq),
        "base_universe_hash": universe_hash,
        "symbol": normalized_symbol,
    }
    train_plan = SplitPlan(
        split_label="train",
        row_index=train_rows,
        time_bounds=_time_bounds_for_rows(features_df.index, train_rows),
        **plan_kwargs,
    )
    test_plan = SplitPlan(
        split_label="test",
        row_index=test_rows,
        time_bounds=_time_bounds_for_rows(features_df.index, test_rows),
        **plan_kwargs,
    )
    symbols = np.asarray([normalized_symbol] * n_rows, dtype=object)
    validate_split_pair_integrity(
        train_plan,
        test_plan,
        features_df.index.to_numpy(),
        symbols,
        allowed_symbols={normalized_symbol},
    )
    return train_plan, test_plan


def _resolve_cross_sectional_label_horizon(label_col: str) -> Optional[int]:
    """xsec label bar-horizon；不可解析→None（禁 fallback h=1 假 horizon）。

    必須在 `_label` 改名前對**原始欄名**呼叫（CODEX-3 / D-H）。
    與 `_resolve_label_horizon_from_column` 單一真相源收斂，禁兩套。
    """
    try:
        return _resolve_label_horizon_from_column(str(label_col), None)  # type: ignore[arg-type]
    except InvalidInputError:
        return None


def _select_inframe_return_n_column(columns: Any) -> Optional[str]:
    """in-frame 候選：自欄名挑 `return_N`（regex return_(\\d+)）。

    多欄確定性規則（明文凍結）：取 **N 最小**；N 相同時取欄名字典序第一。
    優先序位置等同舊硬編 `return_1`（label > return_N > future_return > target > y）。
    """
    matches: list[tuple[int, str]] = []
    for col in columns:
        name = str(col)
        match = re.fullmatch(r"return_(\d+)", name)
        if match:
            matches.append((int(match.group(1)), name))
    if not matches:
        return None
    matches.sort(key=lambda item: (item[0], item[1]))
    return matches[0][1]


def _compute_hac_on_ic_series(
    values: np.ndarray,
    horizon: int,
    *,
    maxlags: Optional[int] = None,
) -> dict:
    """對 xsec 逐期 IC 序列做 NW HAC（z=IC 本身；L/cap/p 同 D-A）。

    Returns:
        t_stat / p_value / se / n_obs / maxlags（fail-closed 時統計量 NaN）
    """
    if horizon is None or int(horizon) < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    horizon = int(horizon)
    z = np.asarray(values, dtype=float)
    z = z[np.isfinite(z)]
    n_valid = int(z.size)
    if n_valid < 2:
        return _hac_nan_result(n_obs=n_valid, maxlags=np.nan)

    min_lag_floor = horizon - 1
    if maxlags is not None:
        maxlags_int = int(maxlags)
        if maxlags_int < min_lag_floor:
            raise ValueError(
                f"maxlags={maxlags_int} < horizon-1={min_lag_floor}; "
                "explicit maxlags must be >= horizon-1"
            )
        L = maxlags_int
    else:
        auto_bw = int(4 * (n_valid / 100.0) ** (2.0 / 9.0))
        L = max(auto_bw, min_lag_floor)
    if L >= n_valid - 1 or n_valid < max(8, 2 * L):
        return _hac_nan_result(n_obs=n_valid, maxlags=L)

    se = _newey_west_bartlett_se(z, L)
    mean_z = float(np.mean(z))
    if not np.isfinite(se) or se == 0.0:
        return _hac_nan_result(n_obs=n_valid, maxlags=L)

    t_stat = float(mean_z / se)
    p_value = float(2.0 * scipy_stats.t.sf(abs(t_stat), df=n_valid - 1))
    return {
        "t_stat": t_stat,
        "p_value": p_value,
        "se": float(se),
        "n_obs": n_valid,
        "maxlags": int(L),
    }


def _labels_df_has_symbol_dimension(labels_df: pd.DataFrame) -> bool:
    """labels_path 是否含 per-symbol 維度（MultiIndex symbol level）。"""
    if not isinstance(labels_df.index, pd.MultiIndex):
        return False
    names = {str(name).lower() for name in labels_df.index.names if name is not None}
    return bool(names.intersection({"symbol", "_symbol"}))


def _normalize_cross_sectional_labels_index(
    labels_df: pd.DataFrame,
    *,
    symbol_level_idx: int,
) -> pd.DataFrame:
    """D-1: cross-sectional labels_path 的 timestamp level 必須可驗證且單調。"""
    if not isinstance(labels_df.index, pd.MultiIndex):
        raise InvalidInputError("cross_sectional labels_path must use MultiIndex")
    if not labels_df.index.is_monotonic_increasing:
        raise InvalidInputError("cross_sectional labels_path index must be monotonic increasing")
    if not labels_df.index.is_unique:
        raise InvalidInputError("cross_sectional labels_path index must be unique")

    time_level_idx = next(
        (idx for idx in range(labels_df.index.nlevels) if idx != symbol_level_idx),
        None,
    )
    if time_level_idx is None:
        raise InvalidInputError("cross_sectional labels_path timestamp level missing")

    time_values = pd.Index(labels_df.index.get_level_values(time_level_idx))
    if isinstance(time_values, pd.DatetimeIndex):
        normalized_time = pd.DatetimeIndex(time_values)
    elif pd.api.types.is_integer_dtype(time_values.dtype):
        values = time_values.to_numpy(dtype=np.int64)
        if values.size and bool(np.any(np.abs(values) > 1_000_000_000_000)):
            raise InvalidInputError(
                "cross_sectional labels_path timestamp index looks like milliseconds, "
                "expected epoch seconds"
            )
        normalized_time = pd.DatetimeIndex(pd.to_datetime(values, unit="s"))
    else:
        try:
            normalized_time = pd.DatetimeIndex(pd.to_datetime(time_values, errors="raise"))
        except (TypeError, ValueError) as exc:
            raise InvalidInputError(
                "cross_sectional labels_path timestamp index must be datetime-like "
                "or int64 epoch seconds"
            ) from exc
    if normalized_time.hasnans:
        raise InvalidInputError("cross_sectional labels_path timestamp index contains NaT")

    arrays = [
        normalized_time
        if idx == time_level_idx
        else labels_df.index.get_level_values(idx)
        for idx in range(labels_df.index.nlevels)
    ]
    normalized = labels_df.copy()
    normalized.index = pd.MultiIndex.from_arrays(arrays, names=labels_df.index.names)
    if not normalized.index.is_monotonic_increasing:
        raise InvalidInputError("cross_sectional labels_path index must be monotonic increasing")
    if not normalized.index.is_unique:
        raise InvalidInputError("cross_sectional labels_path index must be unique")
    return normalized


def _enforce_cross_sectional_label_coverage(
    numeric_df: pd.DataFrame,
    label_col: str,
    symbol_level_idx: int,
    effective_horizon: int,
    tol: float,
) -> dict[str, float]:
    """per-symbol 標籤覆蓋率守衛（D-3：結構性下界，非全域平均）。"""
    per_symbol_coverage: dict[str, float] = {}
    for symbol, group in numeric_df.groupby(level=symbol_level_idx, sort=True):
        labels = group[label_col]
        len_s = int(len(labels))
        if len_s == 0:
            raise InvalidInputError(f"symbol {symbol} has no rows for label coverage check")
        if int(labels.notna().sum()) == 0:
            raise InvalidInputError(
                f"symbol {symbol} has all-NaN labels (fail-closed)"
            )
        if len_s <= effective_horizon:
            raise InvalidInputError(
                f"symbol {symbol} has {len_s} rows, insufficient for "
                f"forward horizon {effective_horizon}"
            )
        coverage_s = float(labels.notna().sum()) / len_s
        floor_s = (len_s - effective_horizon) / len_s
        threshold = floor_s * (1.0 - tol)
        if coverage_s < threshold:
            raise InvalidInputError(
                f"label coverage too low for {symbol}: "
                f"actual={coverage_s:.4f}, required>={threshold:.4f} "
                f"(floor={floor_s:.4f}, horizon={effective_horizon})"
            )
        per_symbol_coverage[str(symbol)] = coverage_s
    return per_symbol_coverage


def _cross_sectional_to_split_frame(
    numeric_df: pd.DataFrame,
    symbol_level_idx: int,
    time_level_idx: int,
) -> pd.DataFrame:
    """將 MultiIndex cross-sectional frame 轉成 split_per_symbol 契約用的 flat frame。"""
    ts = numeric_df.index.get_level_values(time_level_idx)
    symbols = numeric_df.index.get_level_values(symbol_level_idx)
    return pd.DataFrame(
        {
            "symbol": symbols,
            "timestamp": pd.to_datetime(_coerce_timestamp_array(ts)),
        }
    )


def _build_cross_sectional_global_split(
    numeric_df: pd.DataFrame,
    symbol_level_idx: int,
    time_level_idx: int,
    config: ICConfig,
    expected_freq: pd.Timedelta,
    effective_horizon: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """全域同步時間邊界 holdout（D-1）：所有 symbol 共用同一日曆切點。"""
    split_frame = _cross_sectional_to_split_frame(
        numeric_df, symbol_level_idx, time_level_idx
    )
    ts_values = split_frame["timestamp"].to_numpy()
    unique_ts = pd.DatetimeIndex(pd.unique(ts_values)).sort_values()
    n_ts = int(len(unique_ts))
    if n_ts < 2:
        raise InvalidInputError("cross_sectional split requires at least 2 unique timestamps")

    split_point = int(np.floor((1.0 - float(config.oos_test_size)) * n_ts))
    if split_point < 1 or split_point >= n_ts:
        raise InvalidInputError(
            "cross_sectional oos_test_size leaves no train or test timestamps"
        )

    t_train_end = pd.Timestamp(unique_ts[split_point - 1])
    purge_td = effective_horizon * expected_freq
    embargo_td = int(config.embargo) * expected_freq
    test_start = t_train_end + purge_td + embargo_td

    ts_series = pd.Series(pd.to_datetime(ts_values))
    train_mask = (ts_series <= t_train_end).to_numpy(dtype=bool)
    test_mask = (ts_series >= test_start).to_numpy(dtype=bool)

    min_rows = int(config.min_test_rows)
    train_rows = int(train_mask.sum())
    test_rows = int(test_mask.sum())
    if train_rows < min_rows or test_rows < min_rows:
        raise InvalidInputError(
            "cross_sectional train/test rows below min_test_rows",
        )

    per_symbol_test_rows: dict[str, int] = {}
    symbols_arr = split_frame["symbol"].to_numpy()
    for symbol in pd.unique(symbols_arr):
        symbol_mask = symbols_arr == symbol
        symbol_test = int((test_mask & symbol_mask).sum())
        if symbol_test < min_rows:
            raise InvalidInputError(
                f"cross_sectional test rows below min_test_rows for {symbol}: "
                f"{symbol_test} < {min_rows}"
            )
        per_symbol_test_rows[str(symbol)] = symbol_test

    adapter = ICSplitAdapter(expected_freq=str(expected_freq))
    audit_frame = adapter._with_row_positions(split_frame, "symbol", "timestamp")
    base_hash = adapter._base_universe_hash(audit_frame, "symbol", "timestamp")
    allowed_symbols = {
        _normalize_symbol_value(value) for value in pd.unique(symbols_arr)
    }

    def splitter(group: pd.DataFrame) -> Any:
        group_ts = pd.to_datetime(group["timestamp"])
        train_local = np.flatnonzero(group_ts <= t_train_end)
        test_local = np.flatnonzero(group_ts >= test_start)
        if train_local.size == 0 or test_local.size == 0:
            raise InvalidInputError(
                f"cross_sectional split produced empty train/test for "
                f"{group['symbol'].iloc[0]}"
            )
        yield train_local, test_local

    plan_pairs = split_per_symbol(
        split_frame,
        splitter,
        "symbol",
        "timestamp",
        purge_gap=0,
        embargo=int(config.embargo),
        purge_semantic="timedelta",
        expected_freq=str(expected_freq),
        base_universe_hash=base_hash,
        allowed_symbols=allowed_symbols,
    )
    for train_plan, test_plan in plan_pairs:
        validate_split_pair_integrity(
            train_plan,
            test_plan,
            audit_frame["timestamp"].to_numpy(),
            audit_frame["symbol"].to_numpy(),
            allowed_symbols=allowed_symbols,
        )

    train_max_time = pd.Timestamp(ts_series[train_mask].max())
    test_min_time = pd.Timestamp(ts_series[test_mask].min())
    required_gap = purge_td + embargo_td
    actual_gap = test_min_time - train_max_time
    if actual_gap < required_gap:
        raise InvalidInputError(
            "cross_sectional split gap smaller than purge+embargo: "
            f"actual={actual_gap}, required>={required_gap}"
        )

    split_meta = {
        "requested": True,
        "applied": True,
        "scope": "cross_sectional_global_time_holdout",
        "oos_guarantees": True,
        "effective_horizon": effective_horizon,
        "purge_td": str(purge_td),
        "embargo_td": str(embargo_td),
        "train_max_time": str(train_max_time),
        "test_min_time": str(test_min_time),
        "train_rows": train_rows,
        "test_rows": test_rows,
        "per_symbol_test_rows": per_symbol_test_rows,
        "expected_freq": str(expected_freq),
        "base_universe_hash": base_hash,
        "n_split_plans": len(plan_pairs),
    }
    return train_mask, test_mask, split_meta


def _derive_stage_masks(
    train_plan: SplitPlan,
    test_plan: SplitPlan,
    current_index: pd.Index,
) -> tuple[np.ndarray, np.ndarray]:
    """用 split time_bounds 在目前 stage index 上重導 train/test 布林遮罩。"""
    current_ts = pd.to_datetime(_coerce_timestamp_array(current_index.to_numpy()))
    train_lo, train_hi = train_plan.time_bounds
    test_lo, test_hi = test_plan.time_bounds
    train_mask = (current_ts >= train_lo) & (current_ts <= train_hi)
    test_mask = (current_ts >= test_lo) & (current_ts <= test_hi)
    if bool(np.any(train_mask & test_mask)):
        raise ValueError("train/test stage masks overlap")
    return np.asarray(train_mask, dtype=bool), np.asarray(test_mask, dtype=bool)


def _slice_by_mask(
    features_df: pd.DataFrame,
    label_series: pd.Series,
    mask: Optional[np.ndarray],
) -> tuple[pd.DataFrame, pd.Series]:
    if mask is None:
        return features_df, label_series
    mask_arr = np.asarray(mask, dtype=bool)
    if mask_arr.shape[0] != len(features_df):
        raise ValueError("split mask length must match features length")
    if not bool(mask_arr.any()):
        raise ValueError("split mask must select at least one row")
    selected_positions = np.flatnonzero(mask_arr)
    sliced_features = features_df.iloc[selected_positions]
    if len(label_series) == len(features_df):
        feature_index = _normalize_ic_time_index(features_df.index, "features_df")
        label_index = _normalize_ic_time_index(label_series.index, "label_series")
        if not feature_index.equals(label_index):
            raise AlignmentViolationError("label_series index must match features_df before positional slicing")
        sliced_label = label_series.iloc[selected_positions]
    else:
        label_index = _normalize_ic_time_index(label_series.index, "label_series")
        sliced_index = _normalize_ic_time_index(sliced_features.index, "sliced_features")
        normalized_label = label_series.copy(deep=False)
        normalized_label.index = label_index
        sliced_label = normalized_label.reindex(sliced_index)
        sliced_label.index = sliced_features.index
    return sliced_features, sliced_label


def _slice_raw_data_by_mask(
    raw_data: pd.DataFrame,
    features_df: pd.DataFrame,
    sliced_features: pd.DataFrame,
    mask: Optional[np.ndarray],
) -> pd.DataFrame:
    """用 feature row 位置切 raw kline，避免 RangeIndex 與 timestamp index 錯配。"""
    if mask is None:
        return raw_data
    mask_arr = np.asarray(mask, dtype=bool)
    if mask_arr.shape[0] != len(features_df):
        raise ValueError("split mask length must match features length")
    selected_positions = np.flatnonzero(mask_arr)
    if len(raw_data) == len(features_df):
        raw_index = _normalize_frame_time_index(raw_data, "raw_data")
        feature_index = _normalize_ic_time_index(features_df.index, "features_df")
        if not raw_index.equals(feature_index):
            raise AlignmentViolationError("raw_data index must match features_df before positional slicing")
        sliced_raw = raw_data.iloc[selected_positions].copy()
        sliced_raw.index = sliced_features.index
        return sliced_raw
    raw_index = _normalize_frame_time_index(raw_data, "raw_data")
    sliced_index = _normalize_ic_time_index(sliced_features.index, "sliced_features")
    normalized_raw = raw_data.copy(deep=False)
    normalized_raw.index = raw_index
    sliced_raw = normalized_raw.reindex(sliced_index)
    sliced_raw.index = sliced_features.index
    return sliced_raw


def _split_fallback_metadata(reason: str, details: dict[str, Any]) -> dict[str, Any]:
    """建立 default-ON 回退 metadata，避免 legacy 結果被誤標為 OOS。"""
    return {
        "requested": True,
        "applied": False,
        "scope": "full_sample_legacy",
        "oos_guarantees": False,
        "reason": reason,
        "details": {
            "train_rows": int(details.get("train_rows", 0)),
            "test_rows": int(details.get("test_rows", 0)),
            "min_test_rows": int(details.get("min_test_rows", 0)),
        },
    }


class ICFilterOrchestrator:
    """IC 篩選協調器 — 八階段流水線 + 快取策略 + 篩選日誌。"""

    def __init__(self, config: ICConfig):
        self._config = config
        self._preprocessor = DataPreprocessor(config.preprocessing.model_dump())
        self._ic_engine = ICEngine(config.ic_calculation.model_dump())
        self._stat_validator = StatisticalValidator(config.thresholds.model_dump())
        self._event_filter = EventFilter(config.event_filter.model_dump())
        self._monotonicity = MonotonicityTester(config.thresholds.model_dump())
        self._redundancy = RedundancyFilter(config.redundancy.model_dump())
        self._turnover = TurnoverAnalyzer(config.turnover.model_dump())
        self._coverage = CoverageAnalyzer()
        self._reporter = ICReporter(config.report.model_dump())

        self._ic_cache: Optional[dict] = None
        self._monotonicity_cache: Optional[dict] = None
        self._corr_cache: Optional[pd.DataFrame] = None
        self._config_hash: Optional[str] = None
        self._report: Optional[dict] = None
        self._filtered_features_df: Optional[pd.DataFrame] = None
        self._deep_analysis_cache: "OrderedDict[str, DeepAnalysisReport]" = OrderedDict()
        # LA-0 B4：當次 analyze 注入的 fit_mode（deep key / refilter revalidate）
        self._active_fit_mode: Optional[str] = None
        # LA-1 B3：fallback 內層 analyze 禁 persist（G-C）；唯一寫出在 wrapper 加 root 後
        self._suppress_persist: bool = False
        # GAP-2 Task 4.1：fallback 遞迴 analyze 之唯一判定旗標（_stage6b fit_scope=full_sample）；
        # 事件身分（stage3 pop timestamps 前計算）；本 request 之 features/labels 路徑（refilter 沿用）；當次 run config hash
        self._in_fallback_rerun: bool = False
        self._event_identity: Optional[dict] = None
        self._event_context: Optional[dict] = None  # GAP-3 B2.4：survivor v2 六鍵（餵入層提供；None ⇒ 全 null）
        self._features_path: Optional[str] = None
        self._labels_path: Optional[str] = None
        self._current_config_hash: Optional[str] = None
        self._current_config: Optional[ICConfig] = None
        # 1c-FR-FULL F1.1：PIT 因子擇時序列 in-memory owner（F1 寫、F4 讀）
        # cache hit 無 series → 依賴 owner 的 net_ic 走 unavailable，不得崩
        self._factor_return_series: dict[str, FactorTimingReturnSeries] = {}

        self._progress_callback: Optional[Callable] = None

    def analyze(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        kline_reader: Optional[IKlineReader] = None,
        *,
        event_timestamps: Optional[list] = None,
        event_label_values: Optional[dict] = None,
        event_context: Optional[dict] = None,
    ) -> dict:
        """主入口：執行完整八階段流水線。

        event_label_values（GAP-3 Task B2.3）：{epoch_ms: label_value} 事件連續 label；
        提供時條件 IC 只吃此 label（D1-3，禁以 decision 列 join 主線 return_N），
        沿 `event_timestamps` 入口、stage3/4/5＋A′ fallback 原樣；不傳 ⇒ 行為逐位元組不變（§G-1 golden）。

        event_timestamps（ICHC Task 4.2）：per-request 事件時間戳，keyword-only；
        與 features index 同 epoch 語意（秒/毫秒判別沿用 ic_engine 自動偵測原語）；
        空 list ≡ 未帶。不入 config schema（宣告性設定不承載 per-request 資料）。
        """
        if not event_timestamps:
            event_timestamps = None

        config = self._apply_tier_config(self._apply_config_override(config_override))
        self._progress_callback = progress_callback
        self._clear_deep_analysis_cache()
        # GAP-2 Task 4.1：入口存路徑（供 refilter／persist provenance）＋當次 config hash
        self._features_path = str(features_path) if features_path else None
        self._labels_path = str(labels_path) if labels_path else None
        self._current_config_hash = self._hash_config(config)
        self._current_config = config  # 本次 effective config（provenance ic_method／label_return_type 取此，非建構時 config）
        self._event_context = dict(event_context) if event_context else None  # GAP-3 B2.4：survivor v2 六鍵來源

        self._report_progress(0, "ingestion", 0.02, "loading inputs")
        features_df, labels_df, metadata, stage0_log = self._stage0_ingestion(
            features_path, labels_path, meta_path, config=config, kline_reader=kline_reader
        )

        split_context: Optional[dict] = None
        if config.ic_train_test_split:
            expected_freq = _resolve_expected_freq(metadata)
            allowed_symbols = _resolve_metadata_symbol_allowlist(metadata)
            symbol = next(iter(allowed_symbols))
            effective_horizon = _resolve_effective_label_horizon(config, labels_df)
            split_result = _build_holdout_split_plan(
                features_df,
                config,
                symbol,
                expected_freq,
                purge_gap=effective_horizon,
                labels_df=labels_df,
            )
            if isinstance(split_result, SkippedResult):
                # ICHC R6 修補（三家同判 P1）：R5 A′ 兩呼叫點皆須透傳事件語意
                return self._run_full_sample_fallback(
                    features_path,
                    labels_path,
                    meta_path,
                    config_override,
                    progress_callback,
                    kline_reader,
                    reason="insufficient_data",
                    details=split_result.details or {},
                    event_timestamps=event_timestamps,
                    event_label_values=event_label_values,
                    event_context=event_context,
                )
            train_plan, test_plan = split_result
            train_mask, test_mask = _derive_stage_masks(
                train_plan, test_plan, features_df.index
            )
            split_context = {
                "train_plan": train_plan,
                "test_plan": test_plan,
                "train_mask": train_mask,
                "test_mask": test_mask,
                "effective_horizon": effective_horizon,
                "expected_freq": str(expected_freq),
                "allowed_symbols": sorted(allowed_symbols),
            }
            metadata = dict(metadata)
            metadata["ic_train_test_split"] = {
                "requested": True,
                "applied": True,
                "scope": "train_test_holdout",
                "oos_guarantees": True,
                "effective_horizon": effective_horizon,
                "purge_gap": train_plan.purge_gap,
                "embargo": train_plan.embargo,
                "expected_freq": str(expected_freq),
                "train_rows": int(len(train_plan.row_index)),
                "test_rows": int(len(test_plan.row_index)),
                "train_time_bounds": [str(value) for value in train_plan.time_bounds],
                "test_time_bounds": [str(value) for value in test_plan.time_bounds],
                "index_kind": train_plan.index_kind,
            }

        self._report_progress(1, "preprocessing", 0.12, "preprocessing features")
        fit_mode, fit_mask = self._resolve_stage1_fit(
            config, split_context=split_context
        )
        features_df, preproc_log = self._stage1_preprocessing(
            features_df,
            metadata,
            fit_mask=fit_mask,
            fit_mode=fit_mode,
        )
        # 傳播到 metadata（refilter revalidate + report 紅標）
        metadata = dict(metadata) if metadata else {}
        metadata["fit_mode"] = fit_mode
        metadata["pit_stats_version"] = PIT_STATS_VERSION
        if fit_mode == "full_sample":
            metadata["oos_guarantees"] = False
        elif "oos_guarantees" not in metadata and (
            not isinstance(metadata.get("ic_train_test_split"), dict)
        ):
            # split 路徑已在 ic_train_test_split 寫 oos_guarantees=True
            metadata["oos_guarantees"] = bool(preproc_log.get("oos_guarantees", True))

        self._report_progress(2, "label_generation", 0.25, "aligning labels")
        label_series, labels_df = self._stage2_label_generation(
            labels_df, metadata, config, kline_reader, features_df=features_df
        )

        self._report_progress(3, "event_filter", 0.35, "applying event filter")
        features_df, label_series, event_info = self._stage3_event_filter(
            features_df, label_series, metadata, config, kline_reader,
            event_timestamps=event_timestamps,
            event_label_values=event_label_values,
        )
        if split_context is not None:
            train_mask, test_mask = _derive_stage_masks(
                split_context["train_plan"],
                split_context["test_plan"],
                features_df.index,
            )
            split_context["train_mask"] = train_mask
            split_context["test_mask"] = test_mask
            event_info = dict(event_info)
            event_info["split_mask"] = {
                "train_rows": int(train_mask.sum()),
                "test_rows": int(test_mask.sum()),
            }

        features_df, metadata, feature_filter_info = self._apply_feature_filter(
            features_df, metadata, config.feature_filter
        )

        self._report_progress(4, "ic_calculation", 0.55, "computing IC metrics")
        ic_results = self._stage4_ic_calculation(
            features_df,
            label_series,
            metadata,
            config,
            kline_reader,
            split_context=split_context,
        )
        if ic_results.get("status") == "skipped":
            # ICHC R5 one-shot guard：fallback 重跑內再觸發＝設計不變式被破壞
            # （holdout off 後 stage4 不應再 skip）——fail-closed 禁遞迴。
            if self._suppress_persist:
                raise RuntimeError(
                    "one-shot fallback guard: rolling_warmup_insufficient hit again "
                    "inside fallback rerun (invariant: holdout-off skips no warmup)"
                )
            return self._run_full_sample_fallback(
                features_path,
                labels_path,
                meta_path,
                config_override,
                progress_callback,
                kline_reader,
                reason="rolling_warmup_insufficient",
                details=ic_results.get("details") or {},
                event_timestamps=event_timestamps,
                event_label_values=event_label_values,
                event_context=event_context,
            )

        self._report_progress(
            5, "stat_validation", 0.70, "validating statistics"
        )
        stage5_results = self._stage5_statistical_validation(
            features_df,
            label_series,
            ic_results,
            config,
            event_info,
            split_context=split_context,
            metadata=metadata,
        )

        self._report_progress(6, "redundancy", 0.82, "removing redundancy")
        stage6_results = self._stage6_redundancy(
            features_df,
            stage5_results["passed_features"],
            ic_results["icir"],
            metadata,
            split_context=split_context,
        )

        # GAP-2 Task 4.1：stage 6b 邊際 IC／多因子組合（插入點①：analyze stage6 後、stage7 前）
        stage6b_results = self._stage6b_marginal_ic(
            features_df,
            ic_results.get("label_series"),
            stage5_results,
            stage6_results,
            split_context,
            config,
            fit_scope=self._resolve_stage6b_fit_scope(split_context),
        )

        self._report_progress(7, "report", 0.95, "generating report")
        report = self._stage7_report(
            features_df,
            metadata,
            ic_results,
            stage5_results,
            stage6_results,
            stage0_log,
            preproc_log,
            event_info,
            feature_filter_info,
            split_context=split_context,
            stage6b_results=stage6b_results,
        )

        self._report_progress(7, "report", 1.0, "completed")
        self._report = report
        return report

    def _run_full_sample_fallback(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str],
        config_override: Optional[dict],
        progress_callback: Optional[Callable],
        kline_reader: Optional[IKlineReader],
        reason: str,
        details: dict[str, Any],
        *,
        event_timestamps: Optional[list] = None,
        event_label_values: Optional[dict] = None,
        event_context: Optional[dict] = None,
    ) -> dict:
        """以 flag-off 重跑 full-sample，並只追加 fallback metadata。

        LA-0 RULING-3：呼叫前鎖 fit_mode=full_sample + oos_guarantees=False 紅標。
        LA-1 B3：logger.warning + 禁內層 persist + root 紅標後唯一寫出。
        """
        details = details or {}
        train_rows = int(details.get("train_rows", 0))
        test_rows = int(details.get("test_rows", 0))
        min_test_rows = int(details.get("min_test_rows", 0))
        logger.warning(
            "IC full-sample fallback triggered: reason=%s train_rows=%s "
            "test_rows=%s min_test_rows=%s fit_mode=full_sample",
            reason,
            train_rows,
            test_rows,
            min_test_rows,
        )

        fallback_override = deepcopy(config_override) if config_override else {}
        fallback_override["ic_train_test_split"] = False
        # 注入 full_sample（禁落入 pit_expanding / unset）
        prep_override = dict(fallback_override.get("preprocessing") or {})
        prep_override["fit_mode"] = "full_sample"
        fallback_override["preprocessing"] = prep_override

        prev_suppress = self._suppress_persist
        self._suppress_persist = True
        self._in_fallback_rerun = True  # GAP-2 Task 4.1：唯一 fallback 判定機制（_stage6b fit_scope=full_sample）
        try:
            # ICHC R5 裁決（三家 CONVERGED=方案 A′）：fallback 重跑保留 event_timestamps
            # ——事件語意不得靜默丟失；holdout off 後 stage4 不再進 warmup skip，
            # one-shot guard 見 analyze() 內 _in_fallback_rerun。
            report = self.analyze(
                features_path,
                labels_path,
                meta_path,
                config_override=fallback_override,
                progress_callback=progress_callback,
                kline_reader=kline_reader,
                event_timestamps=event_timestamps,
                event_label_values=event_label_values,  # GAP-3 B2.3：A′ 透傳亦保留事件 label（禁靜默丟）
                event_context=event_context,
            )
        finally:
            self._suppress_persist = prev_suppress
            self._in_fallback_rerun = False

        report_meta = dict(report.get("metadata") or {})
        report_meta.pop("scope", None)
        report_meta["ic_train_test_split"] = _split_fallback_metadata(reason, details)
        report_meta["fit_mode"] = "full_sample"
        report_meta["oos_guarantees"] = False
        report_meta["pit_stats_version"] = PIT_STATS_VERSION
        report["metadata"] = report_meta

        # root 紅標 + pass_class（權威在 wrapper 加註之後）
        self._annotate_root_status_and_pass_class(
            report,
            analysis_status="degraded_full_sample",
            oos_guarantees=False,
        )
        # GAP-2 A1-3／TODO 4.2(c)：邊際 IC 節之 OOS 兩欄同點重注入（root 單一來源）
        self._inject_root_oos(report.get("marginal_ic"), "degraded_full_sample", False)

        # G-C：唯一寫出點 = root 欄位加註之後（外層未 suppress 時）
        if not self._suppress_persist:
            features_df = None
            if isinstance(self._ic_cache, dict):
                features_df = self._ic_cache.get("features_df")
            if features_df is not None:
                self._persist_outputs(
                    features_df,
                    self._filtered_features_df,
                    report,
                    report_meta,
                    report.get("filter_log") or {},
                    stage6b_results=report.get("marginal_ic"),
                    event_identity=self._event_identity,
                    features_path=self._features_path,
                    label_series=self._ic_cache.get("label_series") if isinstance(self._ic_cache, dict) else None,
                    split_context=self._ic_cache.get("split_context") if isinstance(self._ic_cache, dict) else None,
                )

        self._report = report
        return report

    @staticmethod
    def _resolve_root_status(report_meta: dict) -> tuple[str, bool]:
        """由 metadata 推 root analysis_status / oos_guarantees。

        OOS 宣稱 iff analysis_status=="ok_oos"（G-A2）。
        """
        meta = report_meta or {}
        if meta.get("oos_guarantees") is False:
            return "degraded_full_sample", False
        if meta.get("fit_mode") == "full_sample":
            return "degraded_full_sample", False
        # ICHC Task 4.1：事件樣本不足回退全樣本 → 即使 holdout 已 applied 仍判 degraded
        event_meta = meta.get("event_filter")
        if isinstance(event_meta, dict) and event_meta.get("fallback") is True:
            return "degraded_full_sample", False
        split = meta.get("ic_train_test_split")
        if isinstance(split, dict):
            if split.get("oos_guarantees") is False or split.get("applied") is False:
                return "degraded_full_sample", False
            if split.get("applied") is True and split.get("oos_guarantees") is not False:
                return "ok_oos", True
        if meta.get("oos_guarantees") is True:
            return "ok_oos", True
        return "degraded_full_sample", False

    @staticmethod
    def _annotate_root_status_and_pass_class(
        report: dict,
        *,
        analysis_status: str,
        oos_guarantees: bool,
    ) -> None:
        """寫 root 紅標 + summary_table/filter_log pass_class（G-A2）。"""
        report["analysis_status"] = analysis_status
        report["oos_guarantees"] = bool(oos_guarantees)
        pass_class = (
            "oos" if analysis_status == "ok_oos" else "full_sample_research_only"
        )
        summary = report.get("summary_table")
        if isinstance(summary, list):
            for row in summary:
                if isinstance(row, dict):
                    row["pass_class"] = pass_class
        filter_log = report.get("filter_log")
        if isinstance(filter_log, dict):
            stage5 = filter_log.get("stage5_thresholds")
            if isinstance(stage5, dict):
                of = stage5.get("output_features")
                if isinstance(of, dict):
                    of["pass_class"] = pass_class
                    of.setdefault(
                        "count",
                        of.get("count", stage5.get("input_features")),
                    )
                else:
                    # 保留 count 語意，附 pass_class（oracle ② 路徑）
                    stage5["output_features"] = {
                        "count": of if isinstance(of, int) else 0,
                        "pass_class": pass_class,
                    }
                stage5["pass_class"] = pass_class

    def analyze_cross_sectional(
        self,
        features: pd.DataFrame,
        labels_path: Optional[str] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        timeframe: Optional[str] = None,
    ) -> dict:
        """Cross-sectional IC: rank corr(feature_{i,t}, return_{i,t+1}) across symbols at each timestamp."""

        config = self._apply_tier_config(self._apply_config_override(config_override))
        self._progress_callback = progress_callback
        self._clear_deep_analysis_cache()

        if features is None or features.empty:
            raise InvalidInputError("features is empty")
        if not isinstance(features.index, pd.MultiIndex) or features.index.nlevels < 2:
            raise InvalidInputError("cross-sectional features must use MultiIndex (timestamp, symbol)")

        index_names = list(features.index.names)
        symbol_level_idx = features.index.nlevels - 1
        if "_symbol" in index_names:
            symbol_level_idx = index_names.index("_symbol")
        elif "symbol" in index_names:
            symbol_level_idx = index_names.index("symbol")

        label_col: Optional[str] = None
        # D-H / CODEX-3：horizon 必須在 `_label` 改名前對原始欄名解析
        horizon_source_name: Optional[str] = None
        sig_horizon: Optional[int] = None
        labels_df = self._load_labels_hdf5(labels_path) if labels_path else None

        if labels_df is not None and not labels_df.empty:
            if not _labels_df_has_symbol_dimension(labels_df):
                raise InvalidInputError(
                    "cross_sectional labels_path 單軸不支援;用 kline 衍生標籤或另立 per-symbol labels epic"
                )
            labels_index_names = list(labels_df.index.names)
            labels_symbol_level_idx = labels_df.index.nlevels - 1
            if "_symbol" in labels_index_names:
                labels_symbol_level_idx = labels_index_names.index("_symbol")
            elif "symbol" in labels_index_names:
                labels_symbol_level_idx = labels_index_names.index("symbol")
            labels_df = _normalize_cross_sectional_labels_index(
                labels_df,
                symbol_level_idx=labels_symbol_level_idx,
            )
            label_series = self._select_label_series(labels_df, config)
            # 原始欄名（改名前）；Series.name 在 _select_label_series 取自 labels_df 欄
            if label_series.name is not None:
                horizon_source_name = str(label_series.name)
            else:
                horizon_source_name = str(labels_df.columns[0])
            sig_horizon = _resolve_cross_sectional_label_horizon(horizon_source_name)
            working_df = features.copy()
            working_df["_label"] = label_series.reindex(features.index).to_numpy()
            label_col = "_label"
        else:
            # in-frame 候選優先序（維持既有；return_1 泛化為 return_N / CODEX-3）：
            # label > return_N(多欄→N 最小, 同 N 字典序第一) > future_return > target > y
            working_df = features.copy()
            for candidate in ["label", "return_N", "future_return", "target", "y"]:
                if candidate == "return_N":
                    chosen = _select_inframe_return_n_column(working_df.columns)
                    if chosen is None:
                        continue
                    label_col = chosen
                    horizon_source_name = chosen
                    sig_horizon = _resolve_cross_sectional_label_horizon(chosen)
                    break
                if candidate in working_df.columns:
                    label_col = candidate
                    horizon_source_name = candidate
                    sig_horizon = _resolve_cross_sectional_label_horizon(candidate)
                    break

        if label_col is None:
            raise InvalidInputError("cross_sectional mode requires a label column or labels_path")

        numeric_df = working_df.select_dtypes(include=[np.number]).copy()
        if label_col not in numeric_df.columns:
            if label_col not in working_df.columns:
                raise InvalidInputError(f"label column missing: {label_col}")
            numeric_df[label_col] = pd.to_numeric(working_df[label_col], errors="coerce")

        feature_cols = [column for column in numeric_df.columns if column != label_col]
        if not feature_cols:
            raise InvalidInputError("no numeric feature columns found for cross-sectional analysis")

        # 覆蓋率/split purge 需要整數 horizon；不可解析時僅結構下界 1（**不**用於顯著性）
        structural_horizon = int(sig_horizon) if sig_horizon is not None else 1
        effective_horizon = structural_horizon
        per_symbol_coverage = _enforce_cross_sectional_label_coverage(
            numeric_df,
            label_col,
            symbol_level_idx,
            effective_horizon,
            config.min_label_coverage_tol,
        )
        mean_coverage = float(np.mean(list(per_symbol_coverage.values())))

        split_meta: Optional[dict[str, Any]] = None
        analysis_df = numeric_df
        if config.ic_train_test_split:
            if not timeframe:
                raise InvalidInputError(
                    "timeframe is required for cross_sectional ic_train_test_split"
                )
            if timeframe not in EXPECTED_FREQ_BY_TIMEFRAME:
                raise InvalidInputError(
                    f"Unsupported timeframe for cross_sectional split: {timeframe!r}"
                )
            expected_freq = EXPECTED_FREQ_BY_TIMEFRAME[timeframe]
            time_levels = [
                idx for idx in range(numeric_df.index.nlevels) if idx != symbol_level_idx
            ]
            if not time_levels:
                raise InvalidInputError("cannot infer timestamp level for cross-sectional analysis")
            time_level_idx = time_levels[0] if len(time_levels) == 1 else time_levels[0]
            try:
                train_mask, test_mask, split_meta = _build_cross_sectional_global_split(
                    numeric_df,
                    symbol_level_idx,
                    time_level_idx,
                    config,
                    expected_freq,
                    effective_horizon,
                )
            except InvalidInputError as exc:
                raise InvalidInputError(
                    f"cross_sectional ic_train_test_split failed: {exc}"
                ) from exc
            analysis_df = numeric_df.iloc[np.flatnonzero(test_mask)]

        self._report_progress(0, "cross_sectional", 0.2, "preparing grouped slices")

        time_levels = [
            idx for idx in range(analysis_df.index.nlevels) if idx != symbol_level_idx
        ]
        if not time_levels:
            raise InvalidInputError("cannot infer timestamp level for cross-sectional analysis")

        grouped_level: Any = time_levels[0] if len(time_levels) == 1 else time_levels
        grouped = analysis_df.groupby(level=grouped_level, sort=True)
        ic_series: dict[str, list[float]] = {column: [] for column in feature_cols}
        n_slices = 0

        for _, group in grouped:
            if len(group) < 2:
                continue
            n_slices += 1
            y = group[label_col]
            for feature_name in feature_cols:
                pair = pd.concat([group[feature_name], y], axis=1).dropna()
                if len(pair) < 2:
                    continue
                ranked_x = pair.iloc[:, 0].rank(method="average")
                ranked_y = pair.iloc[:, 1].rank(method="average")
                corr = ranked_x.corr(ranked_y, method="pearson")
                if pd.notna(corr):
                    ic_series[feature_name].append(float(corr))

        self._report_progress(1, "cross_sectional", 0.8, "building cross-sectional report")

        summary_table: list[dict[str, Any]] = []
        maxlags_by_feature: dict[str, Any] = {}
        for feature_name in feature_cols:
            values = np.array(ic_series.get(feature_name, []), dtype=float)
            if values.size == 0:
                ic_mean = np.nan
                ic_std = np.nan
                icir = np.nan
                ic_hit_rate = np.nan
            else:
                ic_mean = float(np.nanmean(values))
                ic_std = float(np.nanstd(values))
                icir = float(ic_mean / ic_std) if ic_std > 0 else np.nan
                ic_hit_rate = float(np.mean(values > 0))

            # D-H：h 可解析→HAC t/p；h=None→p 族全 NaN（禁假 horizon 反保守 p）
            if sig_horizon is None:
                t_stat = float("nan")
                p_value = float("nan")
                maxlags_by_feature[feature_name] = np.nan
            else:
                hac = _compute_hac_on_ic_series(
                    values,
                    sig_horizon,
                    maxlags=_config_significance_maxlags(config),
                )
                t_stat = float(hac["t_stat"]) if hac.get("t_stat") is not None else float("nan")
                p_value = float(hac["p_value"]) if hac.get("p_value") is not None else float("nan")
                maxlags_by_feature[feature_name] = hac.get("maxlags", np.nan)

            summary_table.append(
                {
                    "feature_name": feature_name,
                    "ic_mean": ic_mean,
                    "ic_std": ic_std,
                    "icir": icir,
                    "t_stat": t_stat,
                    "p_value": p_value,
                    "p_value_adj": float("nan"),
                    "ic_hit_rate": ic_hit_rate,
                    "monotonicity_score": None,
                    "long_short_spread": None,
                    "coverage": None,
                    "turnover_rate": None,
                    "ic_half_life": None,
                    "regime_robust": None,
                }
            )

        # FDR 對該路徑全 feature（n_tests=finite p）；排序仍按 ICIR、不加門檻
        p_values_map: dict[str, float] = {}
        for item in summary_table:
            name = str(item["feature_name"])
            try:
                p_values_map[name] = float(item["p_value"])
            except (TypeError, ValueError):
                p_values_map[name] = float("nan")
        # 同 stage5：一律算 BH q 填 p_value_adj；enabled 旗標僅披露（xsec 無 p 閘）
        fdr_enabled = self._resolve_fdr_enabled(config)
        fdr_method = self._resolve_fdr_method(config)
        alpha_for_fdr = float(config.thresholds.p_value_max)
        q_values, n_tests = apply_fdr(
            p_values_map, alpha_for_fdr, method=fdr_method
        )
        for item in summary_table:
            name = str(item["feature_name"])
            q = q_values.get(name, float("nan"))
            try:
                item["p_value_adj"] = float(q)
            except (TypeError, ValueError):
                item["p_value_adj"] = float("nan")

        summary_table = sorted(
            summary_table,
            key=lambda item: (
                item.get("icir")
                if isinstance(item.get("icir"), (int, float)) and np.isfinite(item.get("icir"))
                else float("-inf")
            ),
            reverse=True,
        )

        ranked_features = [
            item.get("feature_name")
            for item in summary_table
            if isinstance(item.get("feature_name"), str)
        ]

        symbol_ic_matrix = self._build_cross_sectional_symbol_matrix(
            numeric_df=analysis_df,
            feature_cols=ranked_features,
            label_col=label_col,
            symbol_level_idx=symbol_level_idx,
        )
        cross_symbol_validation = self._build_cross_symbol_validation(symbol_ic_matrix)

        finite_maxlags = [
            int(v)
            for v in maxlags_by_feature.values()
            if v is not None and np.isfinite(float(v))
        ]
        maxlags_meta: Optional[int] = max(finite_maxlags) if finite_maxlags else None

        metadata: dict[str, Any] = {
            "mode": "cross_sectional",
            "n_symbols": int(features.index.get_level_values(symbol_level_idx).nunique()),
            "symbols": symbol_ic_matrix.get("symbols", []),
            "n_timestamps": int(n_slices),
            "total_features_input": len(feature_cols),
            "total_features_output": len(feature_cols),
            "per_symbol_coverage": per_symbol_coverage,
            "mean_label_coverage": mean_coverage,
            "horizon_unresolved": bool(sig_horizon is None),
            "label_horizon": sig_horizon,
            "horizon_source_name": horizon_source_name,
            "significance": {
                "fdr": {
                    # D-G：method 恆 canonical；OFF 唯一表述=enabled=false
                    "enabled": bool(fdr_enabled),
                    "method": fdr_method,
                    "alpha_effective": float(alpha_for_fdr),
                },
                "maxlags": maxlags_meta,
                "n_tests": int(n_tests),
                "tested_estimator": TESTED_ESTIMATOR_XSEC_PERIOD_IC,
                "fdr_assumption_note": FDR_ASSUMPTION_NOTE,
            },
        }
        if split_meta is not None:
            metadata["ic_train_test_split"] = split_meta

        # ICHC Task 3.1：五節由裸空 dict 改契約 status（區分「模式不適用」與「壞了」）
        from momentum.Analysis.ic_config_schema import contract_enum

        _na_status = "not_applicable"
        assert _na_status in contract_enum("capability_status")
        _xsec_na = {"status": _na_status, "reason": "cross_sectional_mode"}

        analysis_results = {
            "filter_log": {
                "mode": "cross_sectional",
                "n_timestamps": n_slices,
            },
            "summary_table": summary_table,
            "ic_decay": dict(_xsec_na),
            "quantile_returns": dict(_xsec_na),
            "grouped_ic": dict(_xsec_na),
            "correlation_matrix": {"features": [], "matrix": []},
            "diversification_metrics": {},
            "rolling_ic_series": {
                name: {"window_cross_sectional": values}
                for name, values in ic_series.items()
            },
            "turnover_analysis": dict(_xsec_na),
            "coverage_analysis": dict(_xsec_na),
            "marginal_ic": dict(_xsec_na),  # GAP-2 Task 4.1：xsec 路徑 not_applicable:cross_sectional_mode（禁呼叫計算）
            "cross_sectional_symbol_ic": symbol_ic_matrix,
            "cross_symbol_validation": cross_symbol_validation,
        }

        report = self._reporter.generate_json_report(analysis_results, metadata)
        # LA-1 B3-CX-01：xsec 無 full_sample fallback，但仍必須有 root 紅標/pass_class。
        # OOS 宣稱 iff analysis_status=="ok_oos"（有 split 且 oos_guarantees）；否則 degraded。
        status, oos = self._resolve_root_status(metadata)
        self._annotate_root_status_and_pass_class(
            report,
            analysis_status=status,
            oos_guarantees=oos,
        )
        self._report = report
        self._report_progress(2, "cross_sectional", 1.0, "completed")
        return report

    @staticmethod
    def _safe_rank_corr(x: pd.Series, y: pd.Series) -> Optional[float]:
        pair = pd.concat([x, y], axis=1).dropna()
        if len(pair) < 2:
            return None
        ranked_x = pair.iloc[:, 0].rank(method="average")
        ranked_y = pair.iloc[:, 1].rank(method="average")
        corr = ranked_x.corr(ranked_y, method="pearson")
        if pd.isna(corr):
            return None
        return float(corr)

    def _build_cross_sectional_symbol_matrix(
        self,
        numeric_df: pd.DataFrame,
        feature_cols: list[str],
        label_col: str,
        symbol_level_idx: int,
    ) -> dict[str, Any]:
        symbols: list[str] = []
        matrix: dict[str, dict[str, Optional[float]]] = {
            feature_name: {} for feature_name in feature_cols
        }

        for symbol, group in numeric_df.groupby(level=symbol_level_idx, sort=True):
            symbol_name = str(symbol)
            symbols.append(symbol_name)
            y = group[label_col]

            for feature_name in feature_cols:
                matrix[feature_name][symbol_name] = self._safe_rank_corr(group[feature_name], y)

        return {
            "symbols": symbols,
            "features": feature_cols,
            "matrix": matrix,
        }

    def _build_cross_symbol_validation(self, symbol_ic_matrix: dict[str, Any]) -> dict[str, Any]:
        symbols = [str(item) for item in symbol_ic_matrix.get("symbols", [])]
        features = [str(item) for item in symbol_ic_matrix.get("features", [])]
        matrix = symbol_ic_matrix.get("matrix", {})

        if len(symbols) < 2 or len(features) == 0:
            return {
                "status": "skipped",
                "reason": "insufficient_symbols_or_features",
                "consistency_score": None,
                "best_symbol": None,
                "worst_symbol": None,
                "symbol_scores": {},
                "suggestions": ["Symbol 或特徵數不足，無法進行跨 Symbol 一致性驗證"],
            }

        symbol_scores: dict[str, float] = {}
        for symbol in symbols:
            abs_values: list[float] = []
            for feature in features:
                value = (matrix.get(feature) or {}).get(symbol)
                if isinstance(value, (int, float)) and np.isfinite(value):
                    abs_values.append(abs(float(value)))
            if abs_values:
                symbol_scores[symbol] = float(np.mean(abs_values))

        feature_scores: list[float] = []
        sign_conflict_features: list[str] = []
        symbol_specific_features: list[str] = []
        universal_features: list[str] = []

        for feature in features:
            per_symbol = (matrix.get(feature) or {})
            values = [
                float(value)
                for value in (per_symbol.get(symbol) for symbol in symbols)
                if isinstance(value, (int, float)) and np.isfinite(value)
            ]
            if len(values) < 2:
                continue

            sign_array = np.sign(np.array(values, dtype=float))
            positive_count = int(np.sum(sign_array > 0))
            negative_count = int(np.sum(sign_array < 0))
            if positive_count > 0 and negative_count > 0:
                sign_conflict_features.append(feature)

            sign_agreement = abs(float(np.sum(sign_array))) / len(sign_array)
            dispersion = float(np.std(values))
            dispersion_score = max(0.0, 1.0 - min(dispersion / 0.1, 1.0))
            feature_scores.append(0.7 * sign_agreement + 0.3 * dispersion_score)

            abs_values = [abs(item) for item in values]
            sorted_abs_values = sorted(abs_values, reverse=True)
            if len(sorted_abs_values) >= 2 and sorted_abs_values[0] >= 0.02 and (sorted_abs_values[0] - sorted_abs_values[1]) >= 0.02:
                symbol_specific_features.append(feature)

            same_direction = positive_count == len(sign_array) or negative_count == len(sign_array)
            strong_ratio = float(np.mean(np.array(abs_values) >= 0.015))
            if same_direction and strong_ratio >= 0.7:
                universal_features.append(feature)

        consistency_score = float(np.mean(feature_scores)) if feature_scores else 0.0

        best_symbol = None
        worst_symbol = None
        if symbol_scores:
            best_symbol = max(symbol_scores, key=symbol_scores.get)
            worst_symbol = min(symbol_scores, key=symbol_scores.get)

        suggestions: list[str] = []
        if consistency_score >= 0.7:
            suggestions.append("跨 Symbol 一致性高，可優先納入聯合訓練候選")
        elif consistency_score >= 0.4:
            suggestions.append("跨 Symbol 一致性中等，建議搭配 regime 條件做分組驗證")
        else:
            suggestions.append("跨 Symbol 一致性偏弱，建議僅在特定 Symbol 場景使用")

        if sign_conflict_features:
            suggestions.append("部分因子在不同 Symbol 呈現方向衝突，需檢查市場結構差異")

        return {
            "status": "completed",
            "reason": None,
            "consistency_score": consistency_score,
            "best_symbol": best_symbol,
            "worst_symbol": worst_symbol,
            "symbol_scores": symbol_scores,
            "feature_summary": {
                "total_features": len(features),
                "universal_features": len(universal_features),
                "symbol_specific_features": len(symbol_specific_features),
                "sign_conflict_features": len(sign_conflict_features),
            },
            "samples": {
                "universal_features": universal_features[:10],
                "symbol_specific_features": symbol_specific_features[:10],
                "sign_conflict_features": sign_conflict_features[:10],
            },
            "suggestions": suggestions,
        }

    def refilter(self, thresholds: dict) -> dict:
        """使用新門檻重新篩選（不重算 IC）。

        LA-0 M4：refilter 無獨立 cache key → 前檢 metadata
        pit_stats_version / fit_mode；不符則 invalidate 並 raise（禁重用舊污染 cache）。
        """

        if self._ic_cache is None or self._monotonicity_cache is None:
            raise ValueError("IC cache is empty, run analyze() first")

        # revalidate version/mode（無獨立 refilter key）
        cached_meta = self._ic_cache.get("metadata") or {}
        preproc_log = self._ic_cache.get("preproc_log") or {}
        cached_version = cached_meta.get("pit_stats_version") or preproc_log.get(
            "pit_stats_version"
        )
        cached_mode = cached_meta.get("fit_mode") or preproc_log.get("fit_mode")
        current_mode = self._active_fit_mode or cached_mode
        if (
            cached_version != PIT_STATS_VERSION
            or cached_mode is None
            or (current_mode is not None and cached_mode != current_mode)
        ):
            # invalidate 重算：清 cache，呼叫端須 re-run analyze()
            self._ic_cache = None
            self._monotonicity_cache = None
            self._corr_cache = None
            self._clear_deep_analysis_cache()
            raise ValueError(
                "IC cache invalidated: pit_stats_version/fit_mode mismatch "
                f"(cached_version={cached_version!r} current={PIT_STATS_VERSION!r}, "
                f"cached_mode={cached_mode!r} current_mode={current_mode!r}); "
                "re-run analyze() before refilter()"
            )

        self._clear_deep_analysis_cache()

        config_data = self._config.model_dump()
        merged = self._deep_merge(config_data, {"thresholds": thresholds or {}})
        config = ICConfig.model_validate(merged)
        self._current_config_hash = self._hash_config(config)
        self._current_config = config

        # 與首跑同 scope：從 cache 重建 split_context（OOS→test，full→None）
        split_context = self._ic_cache.get("split_context")
        metadata = self._ic_cache.get("metadata", {})

        stage5_results = self._stage5_statistical_validation(
            self._ic_cache["features_df"],
            self._ic_cache["label_series"],
            self._ic_cache,
            config,
            self._ic_cache.get("event_info", {}),
            split_context=split_context,
            metadata=metadata,
        )

        stage6_results = self._stage6_redundancy(
            self._ic_cache["features_df"],
            stage5_results["passed_features"],
            self._ic_cache["icir"],
            metadata,
            split_context=split_context,
        )

        # GAP-2 Task 4.1：stage 6b（插入點②：refilter stage6 後、stage7 前；同 request 之 event_identity 沿用）
        stage6b_results = self._stage6b_marginal_ic(
            self._ic_cache["features_df"],
            self._ic_cache.get("label_series"),
            stage5_results,
            stage6_results,
            split_context,
            config,
            fit_scope=self._resolve_stage6b_fit_scope(split_context),
        )

        report = self._stage7_report(
            self._ic_cache["features_df"],
            metadata,
            self._ic_cache,
            stage5_results,
            stage6_results,
            self._ic_cache.get("stage0_log", {}),
            self._ic_cache.get("preproc_log", {}),
            self._ic_cache.get("event_info", {}),
            self._ic_cache.get("feature_filter_info", {}),
            split_context=split_context,
            stage6b_results=stage6b_results,
        )

        self._report = report
        return report

    def analyze_full(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        deep_analysis: bool = False,
    ) -> dict:
        """一站式分析：先跑主流程，再依需求追加深度分析。"""

        report = self.analyze(
            features_path=features_path,
            labels_path=labels_path,
            meta_path=meta_path,
            config_override=config_override,
            progress_callback=progress_callback,
        )

        if not deep_analysis:
            return report

        effective_config = self._apply_tier_config(self._apply_config_override(config_override))
        if not self._is_deep_analysis_enabled(effective_config):
            logger.info("Deep analysis skipped by tier preset: %s", effective_config.feature_tiers.active_preset)
            return report

        deep_report = self.run_deep_analysis(
            config_override=config_override,
            progress_callback=progress_callback,
        )

        report_with_deep = self._reporter.inject_deep_analysis(report, deep_report)
        self._report = report_with_deep
        return report_with_deep

    def run_deep_analysis(
        self,
        selected_features: Optional[list[str]] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        force_modules: Optional[list[str]] = None,
    ) -> DeepAnalysisReport:
        """執行 Phase 2.4/2.5 十個深度分析模組並彙總結果。"""

        if self._ic_cache is None:
            raise InvalidInputError("IC cache is empty, run analyze() first")

        config = self._apply_tier_config(self._apply_config_override(config_override))

        # F1.1：每次 deep run 先 invalidate series owner（cache hit 路徑亦不殘留 stale）
        self._factor_return_series = {}

        if not self._is_deep_analysis_enabled(config):
            report = DeepAnalysisReport()
            report.module_summary = {
                "factor_returns": "not_run",
                "factor_centrality": "not_run",
                "trend_analysis": "not_run",
                "parameter_sensitivity": "not_run",
                "rolling_oos": "not_run",
                "factor_orthogonalization": "not_run",
                "factor_exposure": "not_run",
                "long_short_analysis": "not_run",
                "feature_quality_diagnostics": "not_run",
                "net_ic_analysis": "not_run",
            }
            logger.info("Deep analysis disabled by tier preset: %s", config.feature_tiers.active_preset)
            return report

        candidate_features = selected_features or []
        if not candidate_features:
            if self._filtered_features_df is not None and not self._filtered_features_df.empty:
                candidate_features = list(self._filtered_features_df.columns)
            else:
                candidate_features = list(self._ic_cache["features_df"].columns)
        selected = [f for f in candidate_features if f in self._ic_cache["features_df"].columns]

        cache_key = self._compute_deep_cache_key(selected, config)
        force_set = set(force_modules or [])
        cache_hit_only = (not force_set) and (cache_key in self._deep_analysis_cache)

        if cache_hit_only:
            base_report = deepcopy(self._deep_analysis_cache[cache_key])
            # cache hit：series owner 已於上方清空；F4 讀不到 → net_ic unavailable（契約）
            logger.info("Deep analysis cache hit: key=%s", cache_key)
        else:
            base_report = DeepAnalysisReport()
            if cache_key in self._deep_analysis_cache:
                # force-merge:以 cache 為 base 再重跑 force_modules(legacy FR 可能殘留)
                base_report = deepcopy(self._deep_analysis_cache[cache_key])

            module_runners: list[tuple[str, Callable[..., dict]]] = [
                ("factor_returns", self._run_factor_return),
                ("factor_centrality", self._run_factor_centrality),
                ("trend_analysis", self._run_trend_analysis),
                ("parameter_sensitivity", self._run_parameter_sensitivity),
                ("rolling_oos", self._run_rolling_oos),
                ("factor_orthogonalization", self._run_factor_orthogonalization),
                ("factor_exposure", self._run_factor_exposure),
                ("long_short_analysis", self._run_long_short),
                ("feature_quality_diagnostics", self._run_feature_quality_diagnostics),
                ("net_ic_analysis", self._run_net_ic),
            ]

            run_targets: list[tuple[str, Callable[..., dict]]] = []
            for module_name, runner in module_runners:
                if force_set and module_name not in force_set:
                    continue
                if (not force_set) and (not self._is_module_enabled(module_name, config)):
                    continue
                run_targets.append((module_name, runner))

            total_targets = max(1, len(run_targets))
            started = time.perf_counter()

            for idx, (module_name, runner) in enumerate(run_targets, start=1):
                module_started = time.perf_counter()
                try:
                    result = runner(selected, config)
                    base_report.results[module_name] = result
                    # D-4：factor_exposure 巢狀 factor_attribution.status==unavailable
                    # → completed_partial（非 completed）；他模組不變
                    if (
                        module_name == "factor_exposure"
                        and isinstance(result, dict)
                        and isinstance(result.get("factor_attribution"), dict)
                        and result["factor_attribution"].get("status") == "unavailable"
                    ):
                        base_report.module_summary[module_name] = "completed_partial"
                    else:
                        base_report.module_summary[module_name] = "completed"
                    logger.info(
                        "Deep module completed: %s in %.2fs",
                        module_name,
                        time.perf_counter() - module_started,
                    )
                except ModuleUnavailableError as exc:
                    # 刻意下架:§U union + summary unavailable;不入 deep_analysis_errors
                    base_report.results[module_name] = {
                        "status": "unavailable",
                        "value": None,
                        "reason": str(exc),
                    }
                    base_report.module_summary[module_name] = "unavailable"
                    logger.info(
                        "Deep module unavailable: %s, reason=%s (%.2fs)",
                        module_name,
                        str(exc),
                        time.perf_counter() - module_started,
                    )
                except Exception as exc:  # noqa: BLE001
                    skipped = self._classify_and_skip(module_name, exc)
                    base_report.deep_analysis_errors.append(skipped)
                    base_report.results[module_name] = {
                        "skipped": True,
                        "reason": skipped.reason,
                        "error_type": skipped.error_type,
                    }
                    base_report.module_summary[module_name] = "skipped"
                    logger.warning(
                        "Deep module skipped: %s, reason=%s", module_name, skipped.reason
                    )

                payload = {
                    "stage": "deep_analysis",
                    "module_name": module_name,
                    "progress": float(idx / total_targets),
                    "message": f"{module_name} completed ({idx}/{total_targets})",
                }
                self._emit_deep_progress(
                    progress_callback or self._progress_callback, payload
                )

            base_report.total_execution_time_s = float(time.perf_counter() - started)

            all_module_names = [name for name, _ in module_runners]
            for module_name in all_module_names:
                base_report.module_summary.setdefault(module_name, "not_run")

            # D-12：completed_partial 計入 completed（exposure 本體有效，僅子項不可用）
            base_report.completed_count = sum(
                1
                for status in base_report.module_summary.values()
                if status in ("completed", "completed_partial")
            )
            base_report.skipped_count = sum(
                1 for status in base_report.module_summary.values() if status == "skipped"
            )
            base_report.failed_count = 0

            # 寫入 cache 前先 sanitize,避免 dirty legacy 再被 force-merge 讀出
            base_report = self._sanitize_deep_report_factor_returns(base_report)
            self._cache_deep_analysis_result(cache_key, base_report)
            base_report = deepcopy(base_report)

        # 單一收斂點:cache-hit / force-merge / 全量重算 最終 return 前必過 sanitizer
        # (冪等;cache-hit 路徑此為唯一 sanitize,force 路徑為雙重保險)
        # F1 雙審:owner 空時不得服務依賴 series 的 stale net_ic ok
        sanitized = self._sanitize_deep_report_factor_returns(base_report)
        return self._ensure_net_ic_owner_consistency(sanitized)

    def _compute_deep_cache_key(self, selected_features: list[str], config: ICConfig) -> str:
        deep_cfg = {
            "factor_return": config.factor_return.model_dump(),
            "factor_centrality": config.factor_centrality.model_dump(),
            "trend_analysis": config.trend_analysis.model_dump(),
            "parameter_sensitivity": config.parameter_sensitivity.model_dump(),
            "rolling_oos": config.rolling_oos.model_dump(),
            "factor_orthogonalization": config.factor_orthogonalization.model_dump(),
            "factor_exposure": config.factor_exposure.model_dump(),
            "long_short_analysis": config.long_short_analysis.model_dump(),
            "feature_quality_diagnostics": config.feature_quality_diagnostics.model_dump(),
            "net_ic_analysis": config.net_ic_analysis.model_dump(),
            "deep_analysis_global": config.deep_analysis_global.model_dump(),
        }
        # LA-0 M4：key 必含 pit_stats_version + fit_mode
        fit_mode = self._active_fit_mode
        if fit_mode is None and self._ic_cache is not None:
            meta = self._ic_cache.get("metadata") or {}
            preproc = self._ic_cache.get("preproc_log") or {}
            fit_mode = meta.get("fit_mode") or preproc.get("fit_mode")
        if fit_mode is None:
            fit_mode = getattr(config.preprocessing, "fit_mode", "unset")
        # F2 ⑩: schema_version 入 cache key,防命中 stopgap 舊 unavailable 快取
        from momentum.Analysis.factor_return_sanitizer import FR_SCHEMA_VERSION

        payload = {
            "features": sorted(selected_features),
            "deep_config": deep_cfg,
            "pit_stats_version": PIT_STATS_VERSION,
            "fit_mode": fit_mode,
            "schema_version": FR_SCHEMA_VERSION,
            # GAP-2 Task 4.1：事件身分入 key（換 request 不沿用舊 cache）
            "event_identity": self._event_identity,
        }
        dump = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(dump.encode("utf-8")).hexdigest()

    def _is_module_enabled(self, module_name: str, config: ICConfig) -> bool:
        if module_name == "factor_returns":
            return bool(config.factor_return.enabled)
        if module_name == "factor_centrality":
            return bool(config.factor_centrality.enabled)
        if module_name == "trend_analysis":
            return bool(config.trend_analysis.enabled)
        if module_name == "parameter_sensitivity":
            return bool(config.parameter_sensitivity.enabled)
        if module_name == "rolling_oos":
            return bool(config.rolling_oos.enabled)
        if module_name == "factor_orthogonalization":
            return bool(config.factor_orthogonalization.enabled)
        if module_name == "factor_exposure":
            return bool(config.factor_exposure.enabled)
        if module_name == "long_short_analysis":
            return bool(config.long_short_analysis.enabled)
        if module_name == "feature_quality_diagnostics":
            return bool(config.feature_quality_diagnostics.enabled)
        if module_name == "net_ic_analysis":
            return bool(config.net_ic_analysis.enabled)
        return False

    def _classify_and_skip(self, name: str, e: Exception) -> SkippedResult:
        text = str(e).lower()
        if isinstance(e, InsufficientDataError):
            error_type = "INSUFFICIENT_DATA"
            retryable = False
        elif isinstance(e, TimeoutError) or "timeout" in text:
            error_type = "COMPUTATION_TIMEOUT"
            retryable = True
        elif isinstance(e, (ValueError, np.linalg.LinAlgError)):
            if "nan" in text or "singular" in text or "numerical" in text:
                error_type = "NUMERICAL_ERROR"
            else:
                error_type = "INTERNAL_ERROR"
            retryable = False
        else:
            error_type = "INTERNAL_ERROR"
            retryable = False

        logger.error("Deep module failed: %s", name, exc_info=True)
        return SkippedResult(
            module_name=name,
            reason=str(e),
            error_type=error_type,
            retryable=retryable,
        )

    def _run_factor_return(self, selected_features: list[str], config: ICConfig) -> dict:
        """1c-FR-FULL F1.1：factory + compute_batch → §U ok union + series owner。

        F2 sanitizer 放行 ok union;module_summary 同步 completed。
        """
        from momentum.factories import create_factor_return_analyzer

        if self._ic_cache is None:
            raise InvalidInputError("IC cache is empty, run analyze() first")

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        analyzer = create_factor_return_analyzer(config.factor_return.model_dump())
        result = analyzer.compute_batch(
            features_df, labels, top_n=len(selected_features) if selected_features else 1
        )
        # series owner：唯一 API = analyzer.get_series_map()（F0 鎖）
        self._factor_return_series = analyzer.get_series_map()
        return result

    @staticmethod
    def _sanitize_deep_report_factor_returns(report: DeepAnalysisReport) -> DeepAnalysisReport:
        """對 DeepAnalysisReport 套 §U discriminator(ok 放行 / legacy 擋;codex R2-3)。"""
        from momentum.Analysis.factor_return_sanitizer import sanitize_factor_returns

        envelope = {
            "results": report.results if isinstance(report.results, dict) else {},
            "module_summary": (
                report.module_summary if isinstance(report.module_summary, dict) else {}
            ),
            "completed_count": int(report.completed_count),
            "skipped_count": int(report.skipped_count),
            "failed_count": int(report.failed_count),
        }
        cleaned = sanitize_factor_returns(envelope)
        if isinstance(cleaned, dict):
            results = cleaned.get("results")
            if isinstance(results, dict):
                report.results = results
            summary = cleaned.get("module_summary")
            if isinstance(summary, dict):
                report.module_summary = summary
            if "completed_count" in cleaned:
                report.completed_count = int(cleaned["completed_count"])
            if "skipped_count" in cleaned:
                report.skipped_count = int(cleaned["skipped_count"])
            if "failed_count" in cleaned:
                report.failed_count = int(cleaned["failed_count"])
        return report

    def _run_factor_centrality(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer

        rolling_ic = self._ic_cache.get("rolling_ic") or {}
        matrix = pd.DataFrame({
            name: self._extract_rolling_ic_series(value)
            for name, value in rolling_ic.items()
            if name in selected_features and isinstance(value, dict)
        })
        if matrix.empty:
            raise InsufficientDataError("rolling_ic matrix unavailable")

        analyzer = FactorCentralityAnalyzer(config.factor_centrality.model_dump())
        centrality = analyzer.compute_centrality(matrix)
        if isinstance(centrality, SkippedResult):
            raise InsufficientDataError(centrality.reason)
        rolling = analyzer.compute_rolling_centrality(matrix)
        regimes = {
            name: analyzer.detect_crowding_regime(rolling, name)
            for name in list(matrix.columns)
        }
        return {
            **centrality,
            "rolling_centrality": rolling.to_dict(orient="list"),
            "regimes": regimes,
        }

    def _run_trend_analysis(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.trend_analyzer import TrendAnalyzer

        rolling_ic = self._ic_cache.get("rolling_ic") or {}
        matrix = pd.DataFrame({
            name: self._extract_rolling_ic_series(value)
            for name, value in rolling_ic.items()
            if name in selected_features and isinstance(value, dict)
        })
        if matrix.empty:
            raise InsufficientDataError("rolling_ic matrix unavailable")

        analyzer = TrendAnalyzer(config.trend_analysis.model_dump())
        return analyzer.batch_analyze(matrix, top_n=len(selected_features))

    def _run_parameter_sensitivity(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        metadata = self._ic_cache.get("metadata") or {}
        analyzer = ParameterSensitivityAnalyzer(config.parameter_sensitivity.model_dump())
        return analyzer.batch_analyze(features_df, labels, metadata=metadata)

    def _run_rolling_oos(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.rolling_oos_validator import RollingOOSValidator

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        analyzer = RollingOOSValidator(config.rolling_oos.model_dump())
        return analyzer.validate_batch(features_df, labels, top_n=len(selected_features))

    def _run_factor_orthogonalization(self, selected_features: list[str], config: ICConfig) -> dict:
        """C-3 loud：GS/PCA 算法不變；結果包 FactorModuleResult（oos_guarantees=False）。"""
        import hashlib

        from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer

        factors = self._ic_cache["features_df"][selected_features]
        analyzer = FactorOrthogonalizer(
            {
                **config.factor_orthogonalization.model_dump(),
                "icir_scores": self._ic_cache.get("icir", {}),
            }
        )
        method = str(config.factor_orthogonalization.method)
        if method == "pca":
            transformed, summary = analyzer.pca_orthogonalize(factors)
        else:
            transformed, summary = analyzer.gram_schmidt(factors)

        orth_hash = hashlib.sha256(
            np.ascontiguousarray(
                transformed.to_numpy(dtype=np.float64) if not transformed.empty else np.array([])
            ).tobytes()
        ).hexdigest()
        payload = OrthogonalizationPayload(
            method=str(summary.get("method", method)),
            orthogonalized_hash=orth_hash,
            summary={**summary, "transformed_shape": list(transformed.shape)},
        )
        typed = FactorModuleResult(
            module="orthogonalization",
            oos_guarantees=False,
            fit_scope="full_sample",
            payload=payload,
        )
        # B3-F9：保留 typed（envelope），禁純 asdict 丟型別
        out: dict[str, Any] = {
            "typed_result": typed,
            "module": typed.module,
            "oos_guarantees": typed.oos_guarantees,
            "fit_scope": typed.fit_scope,
            "payload": typed.payload,
            "transformed_shape": list(transformed.shape),
            "export_scope": "in_sample_research_only",
            "consumer_deny": True,
        }
        out.update(summary)
        return out

    def _run_factor_exposure(self, selected_features: list[str], config: ICConfig) -> dict:
        """C-3 loud + DEC-3：market_proxy = trailing close-ret（lag≥1），非 forward label。"""
        import hashlib

        from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer

        analyzer = FactorExposureAnalyzer(config.factor_exposure.model_dump())
        factor_values = self._ic_cache["features_df"][selected_features]

        # DEC-3：trailing close return，decision-ts=前一 bar close（不見當根 close）
        close_series = self._ic_cache.get("close_series")
        if close_series is None:
            # 無 close carrier → fail-closed（禁 silent fallback 到 label_series）
            raise InvalidInputError(
                "factor_exposure requires _ic_cache['close_series'] "
                "(trailing close-ret proxy; label_series forward proxy forbidden)"
            )
        close_aligned = pd.to_numeric(close_series, errors="coerce").reindex(
            factor_values.index
        )
        # lag≥1：pct_change().shift(1) → bar t 只用 close[t-1]/close[t-2]
        market_proxy = close_aligned.pct_change().shift(1)
        # 時間軸等權（len=列數非標的數），非交易持倉
        equal_time_weights = pd.Series(
            1.0 / max(1, len(factor_values)), index=factor_values.index
        )

        neutralization_mode = str(config.factor_exposure.neutralization_mode)
        neutralized_values = analyzer.neutralize_factor_matrix(
            factor_values=factor_values,
            market_proxy=market_proxy,
            mode=neutralization_mode,
            lookback=config.factor_exposure.neutralization_lookback,
        )

        exposure = analyzer.calculate_portfolio_exposure(equal_time_weights, factor_values)
        neutralized_exposure = analyzer.calculate_portfolio_exposure(
            equal_time_weights, neutralized_values
        )
        concentration = analyzer.monitor_exposure_concentration(
            exposure,
            max_single_exposure=config.factor_exposure.max_single_exposure,
        )
        neutralized_concentration = analyzer.monitor_exposure_concentration(
            neutralized_exposure,
            max_single_exposure=config.factor_exposure.max_single_exposure,
        )

        original_hhi = concentration.get("hhi")
        neutralized_hhi = neutralized_concentration.get("hhi")
        delta_hhi = None
        if isinstance(original_hhi, (int, float)) and isinstance(neutralized_hhi, (int, float)):
            delta_hhi = float(original_hhi) - float(neutralized_hhi)

        # B3 幽靈契約隔離：巢狀 factor_attribution 顯式 unavailable（恰三鍵）；
        # 移除頂層鏡像 alpha/r_squared/attribution/unexplained/factor_betas。
        # 禁接真迴歸；reason 禁寫「系統沒有 PnL」。
        _ATTR_NOT_WIRED_REASON = (
            "attribution_not_wired_to_canonical_contract"
            "（單標的 canonical FR 下迴歸 ill-posed；"
            "接真需另定 portfolio_returns 與 RHS 契約，見 ROADMAP 票A/票B）"
        )
        summary = {
            "portfolio_exposure": exposure.to_dict(),
            "factor_attribution": {
                "status": "unavailable",
                "value": None,
                "reason": _ATTR_NOT_WIRED_REASON,
            },
            "concentration": concentration,
            "neutralization_mode": neutralization_mode,
            "neutralization_lookback": int(config.factor_exposure.neutralization_lookback),
            "neutralized_portfolio_exposure": neutralized_exposure.to_dict(),
            "neutralized_concentration": neutralized_concentration,
            "neutralization_delta_hhi": delta_hhi,
            "proxy_kind": "trailing_close_ret",
            "proxy_lag": 1,
        }
        exp_hash = hashlib.sha256(
            json.dumps(
                {k: v for k, v in summary["portfolio_exposure"].items()},
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        payload = ExposurePayload(
            proxy_kind="trailing_close_ret",
            exposure_hash=exp_hash,
            summary=summary,
        )
        typed = FactorModuleResult(
            module="exposure",
            oos_guarantees=False,
            fit_scope="full_sample",
            payload=payload,
        )
        # B3-F9：保留 typed（envelope），禁純 asdict 丟型別
        out: dict[str, Any] = {
            "typed_result": typed,
            "module": typed.module,
            "oos_guarantees": typed.oos_guarantees,
            "fit_scope": typed.fit_scope,
            "payload": typed.payload,
            "export_scope": "in_sample_research_only",
            "consumer_deny": True,
        }
        out.update(summary)
        return out

    def _run_long_short(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.long_short_analyzer import LongShortAnalyzer

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        analyzer = LongShortAnalyzer(config.long_short_analysis.model_dump())
        return analyzer.batch_analyze(features_df, labels, top_n=len(selected_features))

    def _run_feature_quality_diagnostics(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics

        analyzer = FeatureQualityDiagnostics(config.feature_quality_diagnostics.model_dump())
        features_df = self._ic_cache["features_df"][selected_features]
        rolling_ic = self._ic_cache.get("rolling_ic") or {}
        rolling_ic_dict = {
            name: self._extract_rolling_ic_series(value)
            for name, value in rolling_ic.items()
            if name in selected_features and isinstance(value, dict)
        }
        return analyzer.run_full_diagnostics(features_df, rolling_ic_dict=rolling_ic_dict)

    def _run_net_ic(self, selected_features: list[str], config: ICConfig) -> dict:
        """Net IC runner(B-strict):交接 PIT series owner → breakeven/profitable。

        F4:從 ``self._factor_return_series[name]`` 取 gross=ls_return、position;
        turnover series 於 analyzer 內 ``position.diff().abs().fillna(0)``(D6 首 bar=0)。
        cache-hit 無 owner → 不得回傳 series-dependent ok/evaluable(F1 護欄)。
        """
        from momentum.Analysis.net_ic_analyzer import NetICAnalyzer

        # ICHC Task 5.3（R1 三家同判 C1）：turnover 停用 → NetIC 顯式 typed
        # unavailable（reason 入契約枚舉），禁靜默 skip、禁偷算 turnover（方案 B 否決）
        turnover_section = (self._report or {}).get("turnover_analysis", {})
        if (
            isinstance(turnover_section, dict)
            and turnover_section.get("status") == "disabled"
        ):
            return {"status": "unavailable", "reason": "turnover_disabled"}

        analyzer = NetICAnalyzer(config.net_ic_analysis.model_dump())
        summary = {
            row["feature_name"]: {"ic_mean": row.get("ic_mean")}
            for row in (self._report or {}).get("summary_table", [])
            if row.get("feature_name") in selected_features
        }
        turnover_data = {
            name: float(data.get("quantile_turnover", 0.0))
            for name, data in (self._report or {}).get("turnover_analysis", {}).items()
            if name in selected_features
        }
        # F4.1: 只傳 owner 內已有 series 的 selected features(缺→analyzer unavailable)
        series_for_batch = {
            name: self._factor_return_series[name]
            for name in selected_features
            if name in self._factor_return_series
        }
        result = analyzer.batch_analyze(
            summary,
            turnover_data,
            factor_return_series=series_for_batch,
        )
        if (
            not self._factor_return_series
            and self._net_ic_payload_depends_on_series_owner(result)
        ):
            return {
                "status": "unavailable",
                "value": None,
                "reason": "factor_return_series_unavailable_on_cache_hit",
            }
        return result

    @staticmethod
    def _net_ic_payload_depends_on_series_owner(payload: Any) -> bool:
        """True 若 net_ic payload 宣稱 series-derived 可評估（ok / evaluable>0）。

        現行 gross-only 路徑（evaluable_count=0、nested unavailable）回 False，
        不誤傷 cache-hit 的合法 gross net_ic。
        """
        if not isinstance(payload, dict):
            return False
        if payload.get("status") == "ok":
            return True
        summary = payload.get("summary")
        if isinstance(summary, dict):
            try:
                if int(summary.get("evaluable_count") or 0) > 0:
                    return True
            except (TypeError, ValueError):
                pass
        features = payload.get("features")
        if not isinstance(features, dict):
            value = payload.get("value")
            if isinstance(value, dict):
                return ICFilterOrchestrator._net_ic_payload_depends_on_series_owner(value)
            return False
        for feat in features.values():
            if not isinstance(feat, dict):
                continue
            if feat.get("status") == "ok":
                return True
            for key in ("net_factor_return", "breakeven_cost_bps", "profitable_after_cost"):
                sub = feat.get(key)
                if isinstance(sub, dict) and sub.get("status") == "ok":
                    return True
                if key == "breakeven_cost_bps" and isinstance(sub, (int, float)):
                    if np.isfinite(float(sub)):
                        return True
                if key == "profitable_after_cost" and isinstance(sub, bool):
                    return True
        return False

    def _ensure_net_ic_owner_consistency(
        self, report: DeepAnalysisReport
    ) -> DeepAnalysisReport:
        """cache-hit/force-merge 缺 owner 時,降級依賴 series 的 stale net_ic ok。

        不得服務 owner=[] 卻 net_ic status:ok 依賴 series 的不一致狀態。
        """
        if self._factor_return_series:
            return report
        results = report.results if isinstance(report.results, dict) else None
        if results is None:
            return report
        net = results.get("net_ic_analysis")
        if not self._net_ic_payload_depends_on_series_owner(net):
            return report
        results["net_ic_analysis"] = {
            "status": "unavailable",
            "value": None,
            "reason": "factor_return_series_unavailable_on_cache_hit",
        }
        summary = report.module_summary
        if isinstance(summary, dict) and summary.get("net_ic_analysis") == "completed":
            summary["net_ic_analysis"] = "unavailable"
            # D-12：completed_partial 計入 completed
            report.completed_count = sum(
                1
                for status in summary.values()
                if status in ("completed", "completed_partial")
            )
        return report

    def _emit_deep_progress(self, callback: Optional[Callable], payload: dict) -> None:
        if callback is None:
            return
        try:
            callback(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Deep progress callback failed: %s", exc)

    def _cache_deep_analysis_result(self, key: str, report: DeepAnalysisReport) -> None:
        if key in self._deep_analysis_cache:
            self._deep_analysis_cache.pop(key)
        self._deep_analysis_cache[key] = deepcopy(report)
        while len(self._deep_analysis_cache) > 5:
            self._deep_analysis_cache.popitem(last=False)

    def _clear_deep_analysis_cache(self) -> None:
        self._deep_analysis_cache.clear()

    @staticmethod
    def _extract_rolling_ic_series(window_dict: dict) -> pd.Series:
        if not isinstance(window_dict, dict) or not window_dict:
            return pd.Series(dtype=float)

        best_key = max(
            window_dict.keys(),
            key=lambda k: len(window_dict.get(k, [])) if isinstance(window_dict.get(k, []), list) else 0,
        )
        values = window_dict.get(best_key, [])
        return pd.Series(values, dtype=float)

    def get_top_features(self, n: int = 30, sort_by: str = "icir") -> list[dict]:
        """取得 Top N 特徵。"""

        if not self._report:
            return []
        table = self._report.get("summary_table", [])
        if not table:
            return []
        ordered = sorted(
            table,
            key=lambda item: item.get(sort_by, float("-inf")),
            reverse=True,
        )
        return ordered[:n]

    def get_filtered_features(self) -> pd.DataFrame:
        """取得精選特徵矩陣。"""

        if self._filtered_features_df is None:
            return pd.DataFrame()
        return self._filtered_features_df.copy()

    def get_report(self) -> dict:
        """取得完整報告。"""

        return self._report or {}

    def _stage0_ingestion(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str],
        config: Optional[ICConfig] = None,
        kline_reader: Optional[IKlineReader] = None,
    ) -> tuple[pd.DataFrame, Optional[pd.DataFrame], dict, dict]:
        features_df, features_meta = self._load_features_hdf5(features_path)
        labels_df = self._load_labels_hdf5(labels_path)
        meta = self._load_meta_json(meta_path)
        if features_meta and not meta:
            meta = features_meta

        if labels_df is not None and not labels_df.empty:
            active_config = config or self._config
            feature_index = _normalize_ic_time_index(features_df.index, "features_df")
            label_index = _normalize_ic_time_index(labels_df.index, "labels_df")
            normalized_features = features_df.copy(deep=False)
            normalized_features.index = feature_index
            normalized_labels = labels_df.copy(deep=False)
            normalized_labels.index = label_index
            if not label_index.equals(feature_index):
                normalized_labels = normalized_labels.reindex(feature_index)
            label_series = self._select_label_series(normalized_labels, active_config)
            if label_series.isna().all():
                raise AlignmentViolationError("selected label is all NaN after feature reindex")
            horizon = _resolve_label_horizon_from_column(str(label_series.name), active_config)
            close = None
            if kline_reader is not None and meta:
                symbol = meta.get("symbol")
                timeframe = meta.get("timeframe")
                if symbol and timeframe:
                    raw_data = kline_reader.read_klines(symbol, timeframe)
                    if raw_data is not None and not raw_data.empty and "close" in raw_data.columns:
                        close_index = _normalize_frame_time_index(raw_data, "raw_data")
                        close = pd.Series(
                            raw_data["close"].to_numpy(copy=False),
                            index=close_index,
                        )
            _rk = active_config.labels.return_type
            report = validate_alignment(
                normalized_features,
                label_series,
                _alignment_spec(meta, horizon),
                close=close if _rk in ORACLE_RETURN_KINDS else None,
                return_kind=_rk,
            )
            features_df = _assign_datetime_index_preserving_values(
                features_df, feature_index, "features_df"
            )
            labels_df = _assign_datetime_index_preserving_values(
                normalized_labels, feature_index, "labels_df"
            )

        removed_nan = self._validate_input(features_df, labels_df, meta)
        stage0_log = {
            "input_features": int(features_df.shape[1]),
            "removed_nan_features": removed_nan,
        }
        if labels_df is not None and not labels_df.empty:
            stage0_log["alignment_report"] = {
                "gap_count": int(report.gap_count),
                "gap_rate": float(report.gap_rate),
                "checked_samples": int(report.checked_samples),
            }

        if removed_nan:
            features_df = features_df.drop(columns=removed_nan)
            if meta:
                for name in removed_nan:
                    meta.pop(name, None)

        return features_df, labels_df, meta, stage0_log

    def _resolve_stage1_fit(
        self,
        config: ICConfig,
        split_context: Optional[dict],
    ) -> tuple[str, Optional[np.ndarray]]:
        """RULING-3 caller→fit_mode 映射（orchestrator 強制注入，禁 unset 進 preprocess）。

        - config.preprocessing.fit_mode == full_sample → full_sample（fallback/研究）
        - split ON → train_mask + train_mask
        - split OFF → pit_expanding
        """
        cfg_mode = str(getattr(config.preprocessing, "fit_mode", "unset") or "unset")
        if cfg_mode == "full_sample":
            self._active_fit_mode = "full_sample"
            return "full_sample", None
        if split_context is not None:
            self._active_fit_mode = "train_mask"
            return "train_mask", split_context.get("train_mask")
        # split off：生產分析路徑 → PIT（非 silent full-sample）
        self._active_fit_mode = "pit_expanding"
        return "pit_expanding", None

    def _stage1_preprocessing(
        self,
        features_df: pd.DataFrame,
        metadata: dict,
        fit_mask: Optional[np.ndarray] = None,
        fit_mode: Optional[str] = None,
    ) -> tuple[pd.DataFrame, dict]:
        if fit_mode is None or fit_mode == "unset":
            raise ValueError(
                "orchestrator _stage1_preprocessing requires explicit fit_mode "
                "!= unset (RULING-3 fail-closed invariant)"
            )
        self._active_fit_mode = fit_mode
        return self._preprocessor.preprocess(
            features_df,
            metadata,
            fit_mask=fit_mask,
            fit_mode=fit_mode,
        )

    def _stage2_label_generation(
        self,
        labels_df: Optional[pd.DataFrame],
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
        features_df: Optional[pd.DataFrame] = None,
    ) -> tuple[pd.Series, pd.DataFrame]:
        # LA-2 DEC-1：winsorized fail-closed — 必須在 preloaded early return 之前，
        # 使 preloaded labels 與 generate 路徑皆擋（與 LabelGenerator / schema 同 reason）。
        if config.labels.return_type == "winsorized":
            from momentum.FeatureEngineering.labels.label_generator import (
                WINSORIZED_DISABLED_MSG,
            )

            raise NotImplementedError(WINSORIZED_DISABLED_MSG)

        if labels_df is not None and not labels_df.empty:
            label_series = self._select_label_series(labels_df, config)
            return label_series, labels_df

        symbol = metadata.get("symbol") if metadata else None
        timeframe = metadata.get("timeframe") if metadata else None
        if kline_reader is None or not symbol or not timeframe:
            raise InvalidInputError("labels_path is required when kline_reader is missing")

        raw_data = kline_reader.read_klines(symbol, timeframe)
        if raw_data is None or raw_data.empty or "close" not in raw_data.columns:
            raise InvalidInputError("raw close data is required for label generation")

        close_index = _normalize_frame_time_index(raw_data, "raw_data")
        close = pd.Series(
            raw_data["close"].to_numpy(copy=False),
            index=close_index,
        )
        labels_cfg = config.labels
        horizon = _resolve_effective_label_horizon(config, None)

        label_generator = create_label_generator()
        label_series = label_generator.generate_returns_by_type(
            close,
            horizon,
            labels_cfg.return_type,
        )
        labels_df = pd.DataFrame(
            {f"return_{horizon}": label_series}, index=close_index
        )
        if features_df is None:
            feature_index = close_index
            features_for_gate = pd.DataFrame(index=feature_index)
        else:
            feature_index = _normalize_ic_time_index(features_df.index, "features_df")
            features_for_gate = features_df.copy(deep=False)
            features_for_gate.index = feature_index

        labels_for_gate = labels_df.reindex(feature_index)
        label_series = labels_for_gate[f"return_{horizon}"]
        validate_alignment(
            features_for_gate,
            label_series,
            _alignment_spec(metadata, horizon),
            close=close if labels_cfg.return_type in ORACLE_RETURN_KINDS else None,
            return_kind=labels_cfg.return_type,
        )
        if features_df is not None:
            normalized_features = _assign_datetime_index_preserving_values(
                features_df, feature_index, "features_df"
            )
            features_df.index = normalized_features.index
        labels_df = _assign_datetime_index_preserving_values(
            labels_for_gate, feature_index, "labels_df"
        )
        label_series = labels_df[f"return_{horizon}"]
        return label_series, labels_df

    def _stage3_event_filter(
        self,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
        *,
        event_timestamps: Optional[list] = None,
        event_label_values: Optional[dict] = None,
    ) -> tuple[pd.DataFrame, pd.Series, dict]:
        event_cfg = config.event_filter
        # GAP-2 Task 4.1：事件身分於 pop timestamps **之前**以 request 原始輸入計算（不可變；refilter 沿用）
        self._event_identity = compute_event_identity(
            getattr(event_cfg, "query", None) if event_cfg.enabled else None,
            list(event_timestamps) if (event_cfg.enabled and event_timestamps is not None) else None,
        )
        if not event_cfg.enabled:
            return features_df, label_series, {"mode": "none"}

        query = event_cfg.query
        # ICHC Task 4.2：per-request timestamps 由 analyze() 參數下鑽（原寫死 None）。
        # 正規化為 DatetimeIndex（epoch 語意契約）：數值輸入沿用 ms/s 量級判別
        # （同 ic_engine._get_time_index 原語：>=1e12 判 ms，否則 s）。
        timestamps = event_timestamps
        if timestamps is not None:
            ts_arr = np.asarray(list(timestamps))
            if np.issubdtype(ts_arr.dtype, np.number):
                max_abs = float(np.nanmax(np.abs(ts_arr.astype(float)))) if len(ts_arr) else 0.0
                unit = "ms" if max_abs >= 1e12 else "s"
                timestamps = list(pd.to_datetime(ts_arr, unit=unit, errors="raise"))
            else:
                timestamps = list(pd.to_datetime(ts_arr, errors="raise"))

        feature_index = _normalize_ic_time_index(features_df.index, "features_df")
        label_index = _normalize_ic_time_index(label_series.index, "label_series")
        if not feature_index.equals(label_index):
            raise AlignmentViolationError("label_series index must match features_df before event filtering")

        normalized_features = features_df.copy(deep=False)
        normalized_features.index = feature_index
        normalized_label = label_series.copy(deep=False)
        normalized_label.index = feature_index

        filter_base = normalized_features
        if kline_reader is not None and metadata:
            symbol = metadata.get("symbol")
            timeframe = metadata.get("timeframe")
            if symbol and timeframe:
                raw_data = kline_reader.read_klines(symbol, timeframe)
                if raw_data is not None and not raw_data.empty:
                    raw_index = _normalize_frame_time_index(raw_data, "raw_data")
                    filter_base = raw_data.copy(deep=False)
                    filter_base.index = raw_index

        # ICHC Task 4.2：timestamps 模式一律走「正規化後 index」比對——
        # raw kline 的 `timestamp` 欄是 epoch int，會被 apply_filter 優先取用而恒 0 命中；
        # 僅 timestamps 模式在本地淺 copy 上移除該欄（query 模式不動，query 可引用該欄）。
        if timestamps is not None and "timestamp" in getattr(filter_base, "columns", []):
            filter_base = filter_base.drop(columns=["timestamp"])

        filtered_df, info = self._event_filter.apply_filter(
            filter_base, query=query, timestamps=timestamps
        )
        # ICHC Task 4.2：raw timestamps 清單不進 report metadata（不可序列化且可能巨大）
        # ——只留計數；EventFilter 本體 filter_info 契約不動（其他 caller 不受影響）
        info.pop("timestamps", None)
        info["n_timestamps_requested"] = len(timestamps) if timestamps else 0

        if info.get("tier") == "insufficient":
            # ICHC Task 4.1：loud fallback——reason 入契約枚舉；root 紅標由
            # _resolve_root_status 讀 metadata.event_filter.fallback 觸發（禁 silent）
            info["fallback"] = True
            info["reason"] = "insufficient_events"
            if event_label_values is not None:
                # GROK-R1-P1-01：事件不足時 conditional IC 不可算——全樣本續算用的是主線 return_N，
                # 必須 loud 揭露（禁靜默退回）；下游讀 conditional_ic_abandoned 判 unavailable。
                info["label_source"] = "mainline_return_N"
                info["conditional_ic_abandoned"] = True
                info["statistic_kind"] = "conditional_ic_unavailable"
            return features_df, label_series, info

        filtered_index = _normalize_ic_time_index(filtered_df.index, "filtered_events")
        selected_index = feature_index.intersection(filtered_index)
        if selected_index.empty:
            raise AlignmentViolationError("event filter produced no timestamps overlapping features")
        filtered_features = normalized_features.loc[selected_index]
        filtered_label = normalized_label.loc[selected_index]
        if event_label_values is not None:
            # GAP-3 Task B2.3：條件 IC 只吃事件連續 label_value（SPEC D1-3）；選中之每一 timestamp
            # 必須有 label_value（缺 ⇒ loud，不回退主線 return_N——D1-5 禁以 decision 列 join）。
            # 不傳 ⇒ 本分支不執行，既有 stage 語意與報告鍵逐位元組不變（§G-1 golden 看住）。
            idx_ms = (selected_index.asi8 // 10**6).astype("int64")
            missing = [int(t) for t in idx_ms if int(t) not in event_label_values]
            if missing:
                raise AlignmentViolationError(
                    f"event_label_values missing for {len(missing)} selected timestamps (first={missing[:3]})"
                )
            vals = np.asarray([float(event_label_values[int(t)]) for t in idx_ms], dtype=float)
            if not np.isfinite(vals).all():  # CODEX-R1-P2-05：label 覆寫須有限值閘（inf/NaN loud）
                raise AlignmentViolationError("event_label_values contain non-finite values")
            filtered_label = pd.Series(vals, index=filtered_label.index, name=filtered_label.name)
            info = dict(info)
            info["label_source"] = "event_label_value"
            info["statistic_kind"] = "conditional_ic"
            info["sample_scope_kind"] = "event"
        return filtered_features, filtered_label, info

    def _apply_feature_filter(
        self,
        features_df: pd.DataFrame,
        metadata: dict,
        feature_filter: Optional[FeatureFilterSchema],
    ) -> tuple[pd.DataFrame, dict, dict]:
        original_columns = list(features_df.columns)
        selected = set(original_columns)
        info = {
            "feature_count_original": int(len(original_columns)),
            "feature_count_filtered": int(len(original_columns)),
            "feature_filter_applied": False,
            "truncation_mode": "none",
            "truncation_order": None,
        }

        if len(original_columns) > 5000:
            logger.warning(
                "feature_filter received %d features; no implicit truncation applied",
                len(original_columns),
            )

        if feature_filter is None:
            return features_df, metadata, info

        filter_data = feature_filter.model_dump(exclude_none=True)
        if not filter_data:
            return features_df, metadata, info

        info["feature_filter_applied"] = True

        include_features = set(feature_filter.include_features or [])
        if include_features:
            selected &= include_features

        if feature_filter.include_pattern:
            pattern = re.compile(feature_filter.include_pattern)
            selected &= {name for name in original_columns if pattern.search(str(name))}

        selected = self._apply_metadata_dimension_filter(
            selected,
            metadata,
            "category",
            feature_filter.include_categories,
        )
        selected = self._apply_metadata_dimension_filter(
            selected,
            metadata,
            "data_source",
            feature_filter.include_data_sources,
        )
        selected = self._apply_metadata_dimension_filter(
            selected,
            metadata,
            "family",
            feature_filter.include_families,
        )

        exclude_features = set(feature_filter.exclude_features or [])
        if exclude_features:
            selected -= exclude_features

        ordered = [name for name in original_columns if name in selected]
        if feature_filter.max_features is not None and len(ordered) > feature_filter.max_features:
            ordered = sorted(ordered)[: feature_filter.max_features]
            info["truncation_mode"] = "preview"
            info["truncation_order"] = "sorted_column_name"

        if not ordered:
            raise InvalidInputError("feature_filter selected zero features")

        filtered_metadata = self._filter_metadata_for_columns(metadata, set(ordered))
        info["feature_count_filtered"] = int(len(ordered))
        return features_df.loc[:, ordered], filtered_metadata, info

    @staticmethod
    def _apply_metadata_dimension_filter(
        selected: set[str],
        metadata: dict,
        dimension: str,
        allowed_values: Optional[list[str]],
    ) -> set[str]:
        if not allowed_values:
            return selected
        allowed = set(allowed_values)
        return {
            name
            for name in selected
            if isinstance(metadata.get(name), dict)
            and metadata.get(name, {}).get(dimension) in allowed
        }

    @staticmethod
    def _filter_metadata_for_columns(metadata: dict, selected_columns: set[str]) -> dict:
        if not metadata:
            return metadata
        filtered: dict[str, Any] = {}
        for key, value in metadata.items():
            if key in selected_columns:
                filtered[key] = value
            elif not isinstance(value, dict):
                filtered[key] = value
        return filtered

    def _stage4_ic_calculation(
        self,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
        split_context: Optional[dict] = None,
    ) -> dict:
        method = config.global_settings.default_method
        rolling_windows = config.ic_calculation.rolling_windows
        rolling_stride = config.ic_calculation.rolling_stride
        ic_decay_horizons = config.ic_calculation.ic_decay_horizons
        test_mask = split_context.get("test_mask") if split_context else None
        features_for_ic, label_for_ic = _slice_by_mask(
            features_df,
            label_series,
            test_mask,
        )

        if split_context is not None:
            adjusted_windows = self._ic_engine._adjust_rolling_windows(rolling_windows)
            min_required = max(adjusted_windows) + int(
                split_context.get("effective_horizon", 0)
            )
            if len(features_for_ic) < min_required:
                return {
                    "status": "skipped",
                    "module_name": "ic_train_test_split",
                    "reason": "test rows below rolling warmup minimum",
                    "error_type": "INSUFFICIENT_DATA",
                    "details": {
                        "train_rows": int(np.asarray(split_context.get("train_mask"), dtype=bool).sum()),
                        "test_rows": int(len(features_for_ic)),
                        "min_test_rows": int(min_required),
                    },
                }

        ic_values = self._ic_engine.compute_ic(features_for_ic, label_for_ic, method)
        rolling_features = features_df
        rolling_label = label_series
        rolling_test_mask = test_mask
        if split_context is not None:
            train_mask = np.asarray(split_context.get("train_mask"), dtype=bool)
            test_mask_arr = np.asarray(test_mask, dtype=bool)
            if train_mask.shape[0] != len(features_df) or test_mask_arr.shape[0] != len(features_df):
                raise ValueError("split mask length must match features length")
            allowed_mask = train_mask | test_mask_arr
            rolling_features, rolling_label = _slice_by_mask(
                features_df,
                label_series,
                allowed_mask,
            )
            rolling_test_mask = test_mask_arr[allowed_mask]
        rolling_ic_full = self._ic_engine.compute_rolling_ic(
            rolling_features, rolling_label, rolling_windows, rolling_stride, method
        )
        rolling_ic = (
            self._slice_rolling_ic_to_test(
                rolling_ic_full,
                rolling_features,
                rolling_label,
                rolling_windows,
                rolling_stride,
                rolling_test_mask,
            )
            if split_context is not None
            else rolling_ic_full
        )
        icir = self._ic_engine.compute_icir(rolling_ic)
        ic_autocorr = self._ic_engine.compute_ic_autocorrelation(rolling_ic)

        ic_decay = {}
        grouped_ic = {}
        raw_data = None
        raw_data_for_ic = None

        if kline_reader is not None and metadata:
            symbol = metadata.get("symbol")
            timeframe = metadata.get("timeframe")
            if symbol and timeframe:
                raw_data = kline_reader.read_klines(symbol, timeframe)
                if raw_data is not None:
                    raw_data_for_ic = _slice_raw_data_by_mask(
                        raw_data,
                        features_df,
                        features_for_ic,
                        test_mask,
                    )

        if config.report.include_decay_analysis and raw_data_for_ic is not None:
            close = raw_data_for_ic.get("close")
            if close is not None:
                ic_decay = self._ic_engine.compute_ic_decay(
                    features_for_ic,
                    close,
                    ic_decay_horizons,
                    method,
                    config.labels.return_type,
                )

        if raw_data_for_ic is not None and config.report.include_regime_analysis:
            grouped_ic = self._ic_engine.compute_grouped_ic(
                features_for_ic,
                label_for_ic,
                raw_data_for_ic,
                metadata,
                config.ic_calculation.grouped_analysis.model_dump(),
            )

        # LA-2 B3 close carrier：對齊 features_df index
        close_series_out: Optional[pd.Series] = None
        if raw_data_for_ic is not None and "close" in getattr(raw_data_for_ic, "columns", []):
            close_series_out = pd.to_numeric(raw_data_for_ic["close"], errors="coerce")
            close_series_out = close_series_out.reindex(features_df.index)
        elif raw_data is not None and "close" in getattr(raw_data, "columns", []):
            close_series_out = pd.to_numeric(raw_data["close"], errors="coerce")
            close_series_out = close_series_out.reindex(features_df.index)

        ic_results = {
            "label_series": label_series,
            "ic_values": ic_values,
            "rolling_ic": rolling_ic,
            "icir": icir,
            "ic_autocorr": ic_autocorr,
            "ic_decay": ic_decay,
            "grouped_ic": grouped_ic,
            "close_series": close_series_out,
            "scope": "test" if split_context is not None else "full",
        }

        return ic_results

    @staticmethod
    def _resolve_scope_symbol(
        split_context: Optional[dict],
        metadata: Optional[dict],
    ) -> str:
        """解析 SelectionScope 用的真實 symbol；缺則 raise，禁虛構 UNKNOWN。

        優先序：split_context.allowed_symbols → split_context.symbol → metadata.symbol。
        正規化走既有 `_normalize_symbol_value`（缺值/sentinel fail-closed）。
        """
        if split_context is not None:
            allowed = split_context.get("allowed_symbols")
            if allowed:
                first = (
                    allowed[0]
                    if isinstance(allowed, (list, tuple))
                    else next(iter(allowed))
                )
                return _normalize_symbol_value(first)
            if split_context.get("symbol") is not None:
                return _normalize_symbol_value(split_context["symbol"])
        if metadata is not None and metadata.get("symbol") is not None:
            return _normalize_symbol_value(metadata["symbol"])
        raise ValueError(
            "SelectionScope base_universe_hash requires authentic symbol "
            "(split_context.allowed_symbols/symbol or metadata.symbol); "
            "refusing fabricated identity"
        )

    def _stage5_statistical_validation(
        self,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        ic_results: dict,
        config: ICConfig,
        event_info: dict,
        split_context: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Stage5：HAC 顯著性 + FDR q 閘 + SelectionScope（Task 2.1–2.3）。

        rolling_ic 保留於 ic_results 供診斷，不再餵入 p-value 鏈。
        """
        icir = ic_results.get("icir", {})
        event_info = event_info or {}
        test_mask = split_context.get("test_mask") if split_context else None
        features_for_stats, label_for_stats = _slice_by_mask(
            features_df,
            label_series,
            test_mask,
        )

        # horizon：split_context 優先，否則 resolver（禁硬編 default）
        if split_context is not None and split_context.get("effective_horizon") is not None:
            horizon = int(split_context["effective_horizon"])
        else:
            horizon = int(_resolve_effective_label_horizon(config, None))

        ic_stats = compute_hac_ic_statistics(
            features_for_stats,
            label_for_stats,
            horizon=horizon,
            maxlags=_config_significance_maxlags(config),
        )

        alpha_effective, alpha_source, selection_mode = self._resolve_alpha_policy(
            config, event_info
        )
        fdr_enabled = self._resolve_fdr_enabled(config)
        fdr_method = self._resolve_fdr_method(config)

        # 全 evaluated 集合（stage5 進場全欄）先算 BH q，先於任何門檻（D-C）
        universe_features = [str(c) for c in features_for_stats.columns]
        p_values: dict[str, float] = {}
        for feature in universe_features:
            raw_p = (ic_stats.get(feature) or {}).get("p_value", np.nan)
            try:
                p_values[feature] = float(raw_p)
            except (TypeError, ValueError):
                p_values[feature] = float("nan")

        q_values, n_tests = apply_fdr(
            p_values, alpha_effective, method=fdr_method
        )
        for feature, q in q_values.items():
            item = dict(ic_stats.get(feature) or {})
            item.setdefault("p_value", p_values.get(feature, np.nan))
            item.setdefault("t_stat", np.nan)
            item["p_value_adj"] = q
            ic_stats[feature] = item

        evaluated_features = [
            feature
            for feature in universe_features
            if np.isfinite(p_values.get(feature, np.nan))
        ]
        if n_tests != len(evaluated_features):
            raise ValueError(
                f"n_tests ({n_tests}) must equal len(evaluated_features) "
                f"({len(evaluated_features)})"
            )

        split_label = "test" if split_context is not None else "full"
        symbol = self._resolve_scope_symbol(split_context, metadata)
        config_hash = self._hash_config(config)
        scope_id = f"{config_hash}:{split_label}"
        # D-G：method 恆=canonical fdr method；OFF 唯一表述=enabled=false
        selection_scope = SelectionScope(
            scope_id=scope_id,
            universe_features=universe_features,
            split_label=split_label,  # type: ignore[arg-type]
            evaluated_features=evaluated_features,
            n_tests=n_tests,
            method=fdr_method,
            base_universe_hash=_base_universe_hash(features_for_stats.index, symbol),
        )

        maxlags_values = [
            (ic_stats.get(f) or {}).get("maxlags")
            for f in evaluated_features
        ]
        finite_maxlags = [
            int(v)
            for v in maxlags_values
            if v is not None and np.isfinite(float(v))
        ]
        maxlags_meta: Optional[int] = max(finite_maxlags) if finite_maxlags else None

        significance_meta = {
            "fdr": {
                "enabled": bool(fdr_enabled),
                "method": fdr_method,
                "alpha_effective": float(alpha_effective),
            },
            "maxlags": maxlags_meta,
            "n_tests": int(n_tests),
            "scope_id": scope_id,
            "tested_estimator": TESTED_ESTIMATOR_BAR_LEVEL,
            "fdr_assumption_note": FDR_ASSUMPTION_NOTE,
        }

        quantile_results = self._monotonicity.compute_all(
            features_for_stats, label_for_stats
        )
        coverage_results = self._coverage.compute_all(features_for_stats)
        # ICHC Task 5.3（方案 A）：enabled=false → 真不算（省算力＋尊重 flag 語意）；
        # report 節輸出契約 status 物件；summary 端 turnover_rate 顯式缺席（空 dict）
        if config.turnover.enabled:
            turnover_results = self._turnover.compute_all(features_for_stats)
        else:
            from momentum.Analysis.ic_config_schema import contract_enum as _ce

            assert "disabled" in _ce("capability_status")
            turnover_results = {"status": "disabled", "reason": "turnover_disabled"}

        summary_table = self._build_summary_table(
            features_df.columns,
            icir,
            ic_stats,
            quantile_results,
            coverage_results,
            turnover_results,
            ic_results.get("ic_decay", {}),
        )

        passed_features, threshold_log = self._apply_thresholds(
            summary_table,
            config.thresholds,
            alpha_effective,
            fdr_enabled=fdr_enabled,
        )
        threshold_log = {
            **threshold_log,
            "alpha_effective": float(alpha_effective),
            "n_tests": int(n_tests),
            "fdr_enabled": bool(fdr_enabled),
            "alpha_source": alpha_source,
        }
        if selection_mode is not None:
            threshold_log["selection_mode"] = selection_mode

        return {
            "summary_table": summary_table,
            "ic_stats": ic_stats,
            "monotonicity": quantile_results,
            "coverage": coverage_results,
            "turnover": turnover_results,
            "passed_features": passed_features,
            "threshold_log": threshold_log,
            "label_series": label_for_stats,
            "scope": "test" if split_context is not None else "full",
            "selection_scope": selection_scope,
            "significance": significance_meta,
            "alpha_effective": float(alpha_effective),
            "alpha_source": alpha_source,
            "selection_mode": selection_mode,
            "fdr_enabled": bool(fdr_enabled),
            "n_tests": int(n_tests),
        }

    @staticmethod
    def _resolve_alpha_policy(
        config: ICConfig, event_info: dict
    ) -> tuple[float, str, Optional[str]]:
        """D-E α 政策：sufficient/marginal→p_value_max；low_confidence→max(p,0.10)。

        不再用 adjusted_p_threshold 直接覆蓋 p_value_max（舊幽靈語意廢除）。
        """
        p_value_max = float(config.thresholds.p_value_max)
        tier = str((event_info or {}).get("tier") or "sufficient")
        if tier == "low_confidence":
            return (
                float(max(p_value_max, 0.10)),
                "event_tier_low_confidence",
                "exploratory_low_confidence",
            )
        # sufficient / marginal / 其他 → threshold_default
        return p_value_max, "threshold_default", None

    def _resolve_fdr_enabled(self, config: ICConfig) -> bool:
        """FDR 預設 ON（D-G）。優先測試 override，否則讀 canonical significance.fdr.enabled。"""
        override = getattr(self, "_fdr_enabled_override", None)
        if override is not None:
            return bool(override)
        sig = getattr(config, "significance", None)
        if sig is None:
            return True
        fdr = sig.get("fdr") if isinstance(sig, dict) else getattr(sig, "fdr", None)
        if fdr is None:
            return True
        enabled = (
            fdr.get("enabled") if isinstance(fdr, dict) else getattr(fdr, "enabled", None)
        )
        if enabled is None:
            return True
        return bool(enabled)

    def _resolve_fdr_method(self, config: ICConfig) -> str:
        """讀 canonical significance.fdr.method 並傳給 apply_fdr（禁幽靈 config）。

        三層接受集合恆等 ``{"fdr_bh"}``（與 ``apply_fdr`` / ``SignificanceFdrSchema``
        一致；exact-whitelist，禁 strip/lower 正規化）。

        取值語意：
        - 經 schema 驗證的 config 物件：``Literal["fdr_bh"]`` 已保證合法，直接通過。
        - dict/raw 繞過 schema：**缺** ``method`` 鍵（或 object 無該屬性）→ 使用
          schema 預設 ``"fdr_bh"``（與 ``SignificanceFdrSchema.method`` 預設對齊，屬合法）。
        - **顯式** ``method`` 鍵存在且值非精確 ``"fdr_bh"``（含 ``None``、
          ``"FDR_BH"`` / ``" fdr_bh "`` / ``""`` / 未知字串）→ ``ValueError``
          （fail-closed；禁 ``raw or default``）。

        OFF 時 method 仍為 canonical 名稱；唯一 OFF 表述=enabled=false（D-G）。
        未來 fdr_by/romano_wolf 升級須同步擴張三處白名單，禁再走 raw-p 靜默降級。
        """
        # 與 apply_fdr._ALLOWED_FDR_METHODS / SignificanceFdrSchema Literal 恆等
        default = "fdr_bh"
        allowed = frozenset({"fdr_bh"})
        sig = getattr(config, "significance", None)
        if sig is None:
            return default
        fdr = sig.get("fdr") if isinstance(sig, dict) else getattr(sig, "fdr", None)
        if fdr is None:
            return default
        if isinstance(fdr, dict):
            if "method" not in fdr:
                return default  # 缺鍵 → schema 預設
            raw = fdr["method"]
        else:
            if not hasattr(fdr, "method"):
                return default  # 缺屬性 → schema 預設
            raw = fdr.method
        # 顯式 None 或非白名單值 → fail-closed（與缺鍵語意分離）
        if raw is None or raw not in allowed:
            raise ValueError(
                f"Unsupported significance.fdr.method={raw!r}; "
                "canonical only: exact 'fdr_bh' "
                "(fail-closed: no strip/lower/normalize; no silent raw-p fallback)"
            )
        return raw

    def _stage6_redundancy(
        self,
        features_df: pd.DataFrame,
        passed_features: list[str],
        ic_scores: dict,
        metadata: dict,
        split_context: Optional[dict] = None,
    ) -> dict:
        test_mask = split_context.get("test_mask") if split_context else None
        features_for_redundancy = features_df
        if test_mask is not None:
            mask_arr = np.asarray(test_mask, dtype=bool)
            if mask_arr.shape[0] != len(features_df):
                raise ValueError("split mask length must match features length")
            features_for_redundancy = features_df.loc[features_df.index[mask_arr]]

        if not passed_features:
            redundancy_log = {
                "method": "none",
                "input_features": 0,
                "output_features": 0,
                "removed_features": [],
            }
            if split_context is not None:
                redundancy_log["scope"] = "test"
            return {
                "filtered_df": pd.DataFrame(index=features_for_redundancy.index),
                "redundancy_log": redundancy_log,
                "correlation_matrix": pd.DataFrame(),
                "diversification_metrics": {},
                **({"scope": "test"} if split_context is not None else {}),
            }

        filtered_df, redundancy_log = self._redundancy.filter(
            features_for_redundancy[passed_features],
            ic_scores,
            method=self._config.redundancy.method,
        )
        corr_matrix = self._redundancy.compute_correlation_matrix(filtered_df)
        feature_metadata = self._filter_feature_metadata(metadata)
        diversification = self._redundancy.compute_diversification_metrics(
            list(filtered_df.columns), corr_matrix, feature_metadata
        )

        if split_context is not None:
            redundancy_log = {**redundancy_log, "scope": "test"}

        return {
            "filtered_df": filtered_df,
            "redundancy_log": redundancy_log,
            "correlation_matrix": corr_matrix,
            "diversification_metrics": diversification,
            **({"scope": "test"} if split_context is not None else {}),
        }

    def _stage7_report(
        self,
        features_df: pd.DataFrame,
        metadata: dict,
        ic_results: dict,
        stage5_results: dict,
        stage6_results: dict,
        stage0_log: dict,
        preproc_log: dict,
        event_info: dict,
        feature_filter_info: dict,
        split_context: Optional[dict] = None,
        stage6b_results: Optional[dict] = None,
    ) -> dict:
        filter_log = self._reporter.generate_filter_log(
            {
                "stage0_ingestion": stage0_log,
                "stage1_preprocessing": preproc_log,
                "stage3_event_filter": event_info,
                "feature_filter": feature_filter_info,
                "stage5_thresholds": stage5_results.get("threshold_log", {}),
                "stage6_redundancy": stage6_results.get("redundancy_log", {}),
            }
        )

        correlation_matrix = stage6_results.get("correlation_matrix")
        corr_payload = self._build_correlation_payload(correlation_matrix)

        analysis_results = {
            "filter_log": filter_log,
            "summary_table": stage5_results.get("summary_table", []),
            "ic_decay": ic_results.get("ic_decay", {}),
            "quantile_returns": stage5_results.get("monotonicity", {}),
            "grouped_ic": ic_results.get("grouped_ic", {}),
            "correlation_matrix": corr_payload,
            "diversification_metrics": stage6_results.get(
                "diversification_metrics", {}
            ),
            "rolling_ic_series": ic_results.get("rolling_ic", {}),
            "turnover_analysis": stage5_results.get("turnover", {}),
            "coverage_analysis": stage5_results.get("coverage", {}),
            # GAP-2 Task 4.1：新節恆為 status object（呼叫方未傳 ⇒ disabled 物件；裸 {} ⇒ 程式錯，fail-loud 不掩蓋）
            "marginal_ic": self._require_marginal_section(stage6b_results),
        }

        report_meta = self._build_report_metadata(
            features_df,
            stage6_results.get("filtered_df"),
            metadata,
            event_info,
            ic_results.get("ic_decay", {}),
            feature_filter_info,
            scope="test" if split_context is not None else None,
            selection_scope=stage5_results.get("selection_scope"),
            significance=stage5_results.get("significance"),
            selection_mode=stage5_results.get("selection_mode"),
            alpha_source=stage5_results.get("alpha_source"),
        )
        report = self._reporter.generate_json_report(analysis_results, report_meta)

        # LA-1 B3：root 紅標 + pass_class（正常路徑 ok_oos；full_sample → degraded）
        status, oos = self._resolve_root_status(report_meta)
        self._annotate_root_status_and_pass_class(
            report,
            analysis_status=status,
            oos_guarantees=oos,
        )
        # GAP-2 A1-3：邊際 IC 節 OOS 兩欄由 root 注入（單一來源；獨立可 patch helper）
        self._inject_root_oos(report.get("marginal_ic"), status, oos)

        # G-C：fallback 內層 skip；正常路徑寫出
        if not self._suppress_persist:
            self._persist_outputs(
                features_df,
                stage6_results.get("filtered_df"),
                report,
                report_meta,
                filter_log,
                stage6b_results=report.get("marginal_ic"),
                event_identity=self._event_identity,
                features_path=self._features_path,
                label_series=ic_results.get("label_series") if isinstance(ic_results, dict) else None,
                split_context=split_context,
            )
        else:
            # A1-1：suppress 時五鍵恆存在（wrapper 唯一寫出點會覆蓋為實值）
            report_meta_obj = report.get("metadata") if isinstance(report.get("metadata"), dict) else report_meta
            report_meta_obj["survivor_output"] = {
                "status": "not_computed",
                "reason": self._survivor_reason("persist_suppressed"),
                "path": None,
                "sha256": None,
                "case_id": self._resolve_case_id(metadata),
            }

        self._filtered_features_df = stage6_results.get("filtered_df")

        # LA-2 B3：close carrier 進 _ic_cache（index 對齊 features_df；factor proxy 用）
        close_series: Optional[pd.Series] = None
        if isinstance(ic_results, dict) and ic_results.get("close_series") is not None:
            close_series = pd.to_numeric(ic_results["close_series"], errors="coerce")
            if isinstance(close_series, pd.Series):
                close_series = close_series.reindex(features_df.index)

        self._ic_cache = {
            "features_df": features_df,
            "label_series": ic_results.get("label_series"),
            "close_series": close_series,
            "metadata": metadata,
            "icir": ic_results.get("icir", {}),
            "rolling_ic": ic_results.get("rolling_ic", {}),
            "ic_decay": ic_results.get("ic_decay", {}),
            "grouped_ic": ic_results.get("grouped_ic", {}),
            "event_info": event_info,
            "feature_filter_info": feature_filter_info,
            "stage0_log": stage0_log,
            "preproc_log": preproc_log,
            # refilter 必須與首跑同 HAC/FDR scope（OOS→test_mask；full→None）
            "split_context": split_context,
            # GAP-2 Task 4.1：persist 完成後才承接之 immutable snapshot（persist 只讀顯式 kwargs）
            "stage6b_results": deepcopy(report.get("marginal_ic")),
            "event_identity": deepcopy(self._event_identity),
        }
        self._monotonicity_cache = stage5_results.get("monotonicity", {})
        self._corr_cache = correlation_matrix
        self._config_hash = self._hash_config(self._config)

        return report

    def _validate_input(
        self,
        features_df: pd.DataFrame,
        labels_df: Optional[pd.DataFrame],
        metadata: dict,
    ) -> list[str]:
        if features_df is None or features_df.empty:
            raise InvalidInputError("features_df is empty")

        if len(features_df) < 100:
            raise InsufficientDataError("total samples < 100")

        if not self._is_float_dataframe(features_df):
            raise InvalidInputError("features_df must be float32/float64")

        if labels_df is not None and not labels_df.empty:
            if not self._is_float_dataframe(labels_df):
                raise InvalidInputError("labels_df must be float32/float64")

        if metadata:
            for feature in features_df.columns:
                meta = metadata.get(feature)
                if not meta:
                    raise InvalidInputError(f"missing metadata for {feature}")
                for key in ("name", "category", "layer"):
                    if key not in meta:
                        raise InvalidInputError(
                            f"metadata for {feature} missing {key}"
                        )

        nan_ratio = features_df.isna().mean()
        removed = nan_ratio[nan_ratio > 0.9].index.tolist()
        return removed

    def _select_label_series(
        self, labels_df: pd.DataFrame, config: ICConfig
    ) -> pd.Series:
        if labels_df.empty:
            raise InvalidInputError("labels_df is empty")
        if "label" in labels_df.columns:
            return labels_df["label"]
        if labels_df.shape[1] == 1:
            return labels_df.iloc[:, 0]

        default_horizon = config.global_settings.default_horizon
        for name in labels_df.columns:
            if str(default_horizon) in name:
                return labels_df[name]
        return labels_df.iloc[:, 0]

    def _slice_rolling_ic_to_test(
        self,
        rolling_ic: dict,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        windows: list[int],
        stride: int,
        test_mask: Optional[np.ndarray],
    ) -> dict:
        if test_mask is None:
            return rolling_ic

        label_name = label_series.name or "label"
        aligned = pd.concat(
            [features_df, label_series.rename(label_name)], axis=1
        ).dropna()
        if aligned.empty:
            return {name: {} for name in features_df.columns}

        test_index = set(features_df.index[np.asarray(test_mask, dtype=bool)])
        adjusted_windows = self._ic_engine._adjust_rolling_windows(windows)
        sliced: dict[str, dict] = {name: {} for name in features_df.columns}

        for window in adjusted_windows:
            key = f"window_{window}"
            end_positions = np.arange(window, len(aligned) + 1, stride)
            end_index = aligned.index[end_positions - 1]
            keep_positions = [
                idx for idx, timestamp in enumerate(end_index) if timestamp in test_index
            ]
            for feature in features_df.columns:
                values = list((rolling_ic.get(feature, {}) or {}).get(key, []))
                sliced[feature][key] = [
                    values[idx] for idx in keep_positions if idx < len(values)
                ]

        return sliced

    def _build_summary_table(
        self,
        feature_names: list[str],
        icir: dict,
        ic_stats: dict,
        quantile_results: dict,
        coverage_results: dict,
        turnover_results: dict,
        ic_decay: dict,
    ) -> list[dict]:
        table: list[dict] = []
        for feature in feature_names:
            icir_item = icir.get(feature, {})
            stats_item = ic_stats.get(feature, {})
            quantile_item = quantile_results.get(feature, {})
            coverage_item = coverage_results.get(feature, {})
            turnover_item = turnover_results.get(feature, {})
            decay_item = ic_decay.get(feature, {})

            table.append(
                {
                    "feature_name": feature,
                    "ic_mean": icir_item.get("ic_mean"),
                    "ic_std": icir_item.get("ic_std"),
                    "icir": icir_item.get("icir"),
                    "p_value": stats_item.get("p_value"),
                    "t_stat": stats_item.get("t_stat"),
                    "p_value_adj": stats_item.get("p_value_adj"),
                    "ic_hit_rate": icir_item.get("ic_hit_rate"),
                    "monotonicity_score": quantile_item.get(
                        "monotonicity_score"
                    ),
                    "long_short_spread": quantile_item.get("long_short", {}).get(
                        "spread"
                    ),
                    "coverage": coverage_item.get("coverage"),
                    "turnover_rate": turnover_item.get("quantile_turnover"),
                    "ic_half_life": decay_item.get("half_life"),
                    "regime_robust": None,
                }
            )
        # ICHC R6 修補（CODEX-R6）：turnover disabled → key 缺席（非 None 值）
        if (
            isinstance(turnover_results, dict)
            and turnover_results.get("status") == "disabled"
        ):
            for row in table:
                row.pop("turnover_rate", None)
        return table

    def _apply_thresholds(
        self,
        summary_table: list[dict],
        thresholds: Any,
        alpha_effective: float,
        *,
        fdr_enabled: bool = True,
    ) -> tuple[list[str], dict]:
        """門檻過濾；p 閘消費 p_value_adj（FDR on）或 p_value（FDR off）。"""
        passed: list[str] = []
        removed: dict[str, list[str]] = {
            "ic_mean": [],
            "icir": [],
            "p_value": [],
            "ic_hit_rate": [],
            "monotonicity": [],
            "coverage": [],
            "long_short_spread": [],
        }

        for row in summary_table:
            name = row.get("feature_name")
            if name is None:
                continue

            if not self._passes_threshold(row.get("ic_mean"), thresholds.ic_mean_min):
                removed["ic_mean"].append(name)
                continue
            if not self._passes_threshold(row.get("icir"), thresholds.icir_min):
                removed["icir"].append(name)
                continue
            p_field = "p_value_adj" if fdr_enabled else "p_value"
            if not self._passes_threshold(
                row.get(p_field), alpha_effective, inverse=True
            ):
                removed["p_value"].append(name)
                continue
            if not self._passes_threshold(
                row.get("ic_hit_rate"), thresholds.ic_hit_rate_min
            ):
                removed["ic_hit_rate"].append(name)
                continue
            if not self._passes_threshold(
                row.get("monotonicity_score"), thresholds.monotonicity_score_min
            ):
                removed["monotonicity"].append(name)
                continue
            if not self._passes_threshold(
                row.get("coverage"), thresholds.coverage_min
            ):
                removed["coverage"].append(name)
                continue

            if thresholds.long_short_spread.enabled:
                if not self._passes_threshold(
                    row.get("long_short_spread"),
                    thresholds.long_short_spread.min_spread,
                ):
                    removed["long_short_spread"].append(name)
                    continue

            passed.append(name)

        threshold_log = {
            "input_features": len(summary_table),
            "output_features": len(passed),
            "removed_features": removed,
        }

        return passed, threshold_log

    def _build_correlation_payload(
        self, corr_matrix: Optional[pd.DataFrame]
    ) -> dict:
        if corr_matrix is None or corr_matrix.empty:
            return {"features": [], "matrix": []}

        features = list(corr_matrix.columns)
        values = corr_matrix.fillna(0.0).to_numpy(dtype=float).tolist()
        return {"features": features, "matrix": values}

    def _build_report_metadata(
        self,
        features_df: pd.DataFrame,
        filtered_df: Optional[pd.DataFrame],
        metadata: dict,
        event_info: dict,
        ic_decay: dict,
        feature_filter_info: Optional[dict] = None,
        scope: Optional[str] = None,
        selection_scope: Optional[SelectionScope] = None,
        significance: Optional[dict] = None,
        selection_mode: Optional[str] = None,
        alpha_source: Optional[str] = None,
    ) -> dict:
        meta = dict(metadata) if metadata else {}
        warnings = []
        existing_warnings = meta.get("warnings")
        if isinstance(existing_warnings, list):
            warnings.extend(existing_warnings)

        warnings.extend(self._collect_ic_decay_warnings(ic_decay))
        meta.update(
            {
                "total_features_input": int(features_df.shape[1]),
                "total_features_output": int(filtered_df.shape[1])
                if filtered_df is not None
                else 0,
                "n_samples": int(len(features_df)),
                "event_filter": event_info,
                **(feature_filter_info or {}),
                "warnings": warnings,
            }
        )
        # ICHC Task 6.2：切分現狀誠實標示（枚舉住契約檔 split_method）——
        # IC 主路徑現況=holdout-only；full-sample fallback 由 fit_mode 判別
        meta["split_method"] = (
            "full_sample_fallback"
            if meta.get("fit_mode") == "full_sample"
            else "holdout"
        )
        if scope is not None:
            meta["scope"] = scope
        if selection_scope is not None:
            meta["selection_scope"] = {
                "scope_id": selection_scope.scope_id,
                "universe_features": list(selection_scope.universe_features),
                "split_label": selection_scope.split_label,
                "evaluated_features": list(selection_scope.evaluated_features),
                "n_tests": int(selection_scope.n_tests),
                "method": selection_scope.method,
                "base_universe_hash": selection_scope.base_universe_hash,
            }
        if significance is not None:
            meta["significance"] = significance
        if selection_mode is not None:
            meta["selection_mode"] = selection_mode
        if alpha_source is not None:
            meta["alpha_source"] = alpha_source
        return meta

    @staticmethod
    def _collect_ic_decay_warnings(ic_decay: dict) -> list[str]:
        if not ic_decay:
            return []

        reason_labels = {
            "insufficient_points": "點數不足",
            "low_variance": "變異過小",
            "low_r2": "R2過低",
            "fit_exception": "擬合失敗",
        }

        reason_counts: dict[str, int] = {}
        for result in ic_decay.values():
            if not isinstance(result, dict):
                continue
            if not result.get("fit_warning"):
                continue
            reason = result.get("fit_warning_reason") or "unknown"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if not reason_counts:
            return []

        details = []
        for reason, count in sorted(reason_counts.items()):
            label = reason_labels.get(reason, reason)
            details.append(f"{label}={count}")

        return [
            "IC Decay 擬合警示: " + ", ".join(details)
        ]

    @staticmethod
    def _filter_feature_metadata(metadata: dict) -> dict:
        if not metadata:
            return {}
        return {key: value for key, value in metadata.items() if isinstance(value, dict)}

    # ------------------------------------------------------------------ GAP-2 Task 4.1／4.2 helpers
    @staticmethod
    def _marginal_status_object(status: str, reason: Optional[str]) -> dict:
        """邊際 IC 節之 status object（reason 字面須 ∈ 契約 reasons.marginal_ic；不寫死於程式外）。"""
        pool = load_survivor_contract()["reasons"]["marginal_ic"]
        if reason is not None and reason not in pool:
            raise KeyError(f"marginal_ic reason {reason!r} not in contract")
        return {"status": status, "reason": reason}

    def _require_marginal_section(self, stage6b_results: Optional[dict]) -> dict:
        """None ⇒ disabled 物件；非 dict／裸 {}／缺 status ⇒ ValueError（禁把裸空節寫進報告——§V-14／wiring R3）。"""
        if stage6b_results is None:
            return self._marginal_status_object("disabled", "disabled_by_config")
        if not isinstance(stage6b_results, dict) or not stage6b_results or "status" not in stage6b_results:
            raise ValueError("stage6b returned a bare/invalid marginal_ic section (must be a status object)")
        return stage6b_results

    @staticmethod
    def _survivor_reason(name: str) -> str:
        pool = load_survivor_contract()["reasons"]["survivor_output"]
        if name not in pool:
            raise KeyError(f"survivor_output reason {name!r} not in contract")
        return name

    def _resolve_stage6b_fit_scope(self, split_context: Optional[dict]) -> Optional[str]:
        """fit_scope 唯一判定：fallback 遞迴 ⇒ full_sample；無 split ⇒ None（節 not_applicable）；否則 train。"""
        if self._in_fallback_rerun:
            return "full_sample"
        if split_context is None:
            return None
        return "train"

    @staticmethod
    def _inject_root_oos(section: Any, analysis_status: str, oos_guarantees: bool) -> None:
        """A1-3：對 status==ok 之邊際 IC 節注入 root 之 oos_guarantees／pass_class（含 composite）。獨立可 patch。"""
        if not isinstance(section, dict) or section.get("status") != "ok":
            return
        pass_class = "oos" if analysis_status == "ok_oos" else "full_sample_research_only"
        section["oos_guarantees"] = bool(oos_guarantees)
        section["pass_class"] = pass_class
        comp = section.get("composite")
        if isinstance(comp, dict) and "oos_guarantees" in comp:
            comp["oos_guarantees"] = bool(oos_guarantees)

    def _stage6b_marginal_ic(
        self,
        features_df: pd.DataFrame,
        label_series: Optional[pd.Series],
        stage5_results: dict,
        stage6_results: dict,
        split_context: Optional[dict],
        config: ICConfig,
        *,
        fit_scope: Optional[str],
    ) -> dict:
        """GAP-2 stage 6b：semi-partial 秩 IC（loo／sequential／removed）＋多因子組合 IC。

        - `enabled=False` ⇒ `{status:disabled, reason:disabled_by_config}`（非裸 {}）。
        - masks：holdout ⇒ split_context 之 train/test mask、fit_scope=train；fallback ⇒ 全 True、full_sample；
          無 split 且非 fallback ⇒ `not_applicable:no_holdout_split`。
        - `oos_guarantees`／`pass_class` 維持 None 佔位，由 `_stage7_report` 依 root 注入（A1-3）。
        """
        cfg = config.marginal_ic
        if not cfg.enabled:
            return self._marginal_status_object("disabled", "disabled_by_config")
        if label_series is None:
            return self._marginal_status_object("not_computed", "insufficient_test_rows")
        filtered_df = stage6_results.get("filtered_df")
        survivors = list(filtered_df.columns) if filtered_df is not None else []
        passed = list(stage5_results.get("passed_features") or [])
        extra = [f for f in passed if f not in set(survivors)] if cfg.include_removed_candidates else []
        n = int(len(features_df.index))
        if fit_scope == "full_sample":
            train_mask = np.ones(n, dtype=bool)
            test_mask = np.ones(n, dtype=bool)
        elif fit_scope == "train":
            train_mask = np.asarray(split_context["train_mask"], dtype=bool)
            test_mask = np.asarray(split_context["test_mask"], dtype=bool)
        else:
            return self._marginal_status_object("not_applicable", "no_holdout_split")
        n_test = int(test_mask.sum())
        horizon = 1
        if isinstance(split_context, dict) and split_context.get("effective_horizon") is not None:
            horizon = int(split_context["effective_horizon"])
        block_len = max(int(horizon), int(math.ceil(n_test ** (1.0 / 3.0))) if n_test > 0 else 1, 1)
        params = MarginalICParams(
            min_test_rows=int(cfg.min_test_rows),
            min_rows_per_regressor=int(cfg.min_rows_per_regressor),
            degenerate_threshold=float(cfg.degenerate_threshold),
            n_bootstrap=int(cfg.n_bootstrap),
            block_len=int(block_len),
            seed=int(cfg.bootstrap_seed),
            weights_method=str(cfg.weights_method),
            max_survivors_for_loo=int(cfg.max_survivors_for_loo),
            max_removed_candidates=int(cfg.max_removed_candidates),
        )
        label = label_series if isinstance(label_series, pd.Series) else pd.Series(label_series, index=features_df.index)
        if len(label) != n:
            label = label.reindex(features_df.index)
        res = compute_marginal_ic(
            features_df, label, train_mask=train_mask, test_mask=test_mask, survivors=survivors,
            extra_candidates=extra, params=params, fit_scope=fit_scope,
        )
        comp = combine_factors(
            features_df, label, train_mask=train_mask, test_mask=test_mask, survivors=survivors,
            params=params, fit_scope=fit_scope,
        )
        section = res.to_dict()
        section["composite"] = comp.to_dict()
        logger.info(
            "IC stage6b marginal_ic: status=%s reason=%s survivors=%d removed=%d n_regressions=%d fit_scope=%s",
            section["status"], section["reason"], len(survivors), len(extra), section["n_regressions"], fit_scope,
        )
        return section

    def _persist_outputs(
        self,
        features_df: pd.DataFrame,
        filtered_df: Optional[pd.DataFrame],
        report: dict,
        metadata: dict,
        filter_log: dict,
        *,
        stage6b_results: Optional[dict] = None,
        event_identity: Optional[dict] = None,
        features_path: Optional[str] = None,
        label_series: Optional[pd.Series] = None,
        split_context: Optional[dict] = None,
    ) -> dict:
        output_paths: dict[str, str] = {}
        analysis_status = None
        oos_guarantees = None
        source_generated_at = None
        if isinstance(report, dict):
            # B3-ENUM-01：persist 讀取點 fail-closed（非字面 ok_oos → degraded）
            from momentum.Analysis.ic_reporter import normalize_analysis_status

            analysis_status = normalize_analysis_status(report.get("analysis_status"))
            if "oos_guarantees" in report:
                oos_guarantees = bool(report.get("oos_guarantees"))
            else:
                oos_guarantees = analysis_status == "ok_oos"
            source_generated_at = report.get("generated_at")

        # B3-H5-01：當次 run 是否寫出 filtered 必記在 metadata，避免 export 讀到穩定路徑舊檔
        report_meta = report.setdefault("metadata", {}) if isinstance(report, dict) else {}
        if not isinstance(report_meta, dict):
            report_meta = {}
            if isinstance(report, dict):
                report["metadata"] = report_meta

        if filtered_df is not None and not filtered_df.empty:
            output_path = self._resolve_filtered_path(metadata)
            saved = self._reporter.save_filtered_features(
                filtered_df,
                list(filtered_df.columns),
                output_path,
                analysis_status=analysis_status,
                oos_guarantees=oos_guarantees,
                source_generated_at=str(source_generated_at)
                if source_generated_at is not None
                else None,
            )
            output_paths["filtered_features"] = saved
            report_meta["filtered_features_written"] = True
            report_meta["filtered_features_path"] = saved
            if source_generated_at is not None:
                report_meta["filtered_generated_at"] = str(source_generated_at)
        else:
            # 空 filtered：明確標記未寫出，export 必須拒穩定路徑舊檔
            report_meta["filtered_features_written"] = False
            report_meta.pop("filtered_features_path", None)
            report_meta.pop("filtered_generated_at", None)

        report_paths = self._reporter.save_report(
            report,
            output_dir="data_cache/reports",
            case_id=self._resolve_case_id(metadata),
        )
        output_paths.update(report_paths)
        output_paths["filter_log"] = self._reporter.save_filter_log(
            filter_log,
            output_dir="data_cache/reports",
            case_id=self._resolve_case_id(metadata),
        )

        # ---- GAP-2 Task 4.2：倖存者輸出檔（沿 report json 同 output_dir 解析；五鍵恆寫入 metadata.survivor_output）----
        report_meta["survivor_output"] = self._write_survivor_output(
            report=report,
            report_meta=report_meta,
            metadata=metadata,
            filtered_df=filtered_df,
            features_df=features_df,
            report_json_path=report_paths.get("json"),
            stage6b_results=stage6b_results,
            event_identity=event_identity,
            features_path=features_path,
            label_series=label_series,
            split_context=split_context,
        )
        if report_meta["survivor_output"].get("path"):
            output_paths["survivor_output"] = report_meta["survivor_output"]["path"]
        # R21 CODEX-R21-P1-01：五鍵注入發生在 save_report 之後 ⇒ 重存報告使落盤 ic_report_*.json 亦含 metadata.survivor_output（互指鏡像）
        report_paths = self._reporter.save_report(
            report,
            output_dir="data_cache/reports",
            case_id=self._resolve_case_id(metadata),
        )
        output_paths.update(report_paths)

        return output_paths

    def _write_survivor_output(
        self,
        *,
        report: dict,
        report_meta: dict,
        metadata: dict,
        filtered_df: Optional[pd.DataFrame],
        features_df: pd.DataFrame,
        report_json_path: Optional[str],
        stage6b_results: Optional[dict],
        event_identity: Optional[dict],
        features_path: Optional[str],
        label_series: Optional[pd.Series],
        split_context: Optional[dict],
    ) -> dict:
        """組裝＋驗證＋原子寫出 ic_survivors_{case_id}.json；回五鍵 status object（TODO Task 4.2 三形狀）。

        - 缺 symbol／timeframe ⇒ 不組裝不寫檔 ⇒ computation_failed:identity_missing。
        - 組裝／驗證之 ContractValidationError **上拋**（fail-closed；屬程式錯非 IO 錯）。
        - 寫檔 IO 例外 ⇒ computation_failed:write_failed（A1-6：reason 字面封閉，例外只進 log），報告照存。
        """
        case_id = self._resolve_case_id(metadata)
        symbol = metadata.get("symbol") if isinstance(metadata, dict) else None
        timeframe = metadata.get("timeframe") if isinstance(metadata, dict) else None
        if not symbol or not timeframe:
            return {
                "status": "computation_failed",
                "reason": self._survivor_reason("identity_missing"),
                "path": None,
                "sha256": None,
                "case_id": case_id,
            }
        summary_by_feature = {
            str(row.get("feature_name")): row
            for row in (report.get("summary_table") or [])
            if isinstance(row, dict) and row.get("feature_name") is not None
        }
        features_source_hash = ""
        if features_path and Path(features_path).is_file():
            h = hashlib.sha256()
            with open(features_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            features_source_hash = h.hexdigest()
        labels_content_hash = ""
        if isinstance(label_series, pd.Series):
            labels_content_hash = hashlib.sha256(
                pd.to_numeric(label_series, errors="coerce").to_numpy(dtype=float).tobytes()
            ).hexdigest()
        split_ctx = dict(split_context or {})
        split_ctx.setdefault("full_index", features_df.index)
        section = stage6b_results if isinstance(stage6b_results, dict) else None
        composite = section.get("composite") if isinstance(section, dict) else None
        marginal = None
        if isinstance(section, dict) and "views" in section:
            marginal = {k: v for k, v in section.items() if k != "composite"}
        report_ref = f"ic_report_{case_id}.json"
        payload = build_survivor_output(
            report_meta=report_meta,
            filtered_features=list(filtered_df.columns) if filtered_df is not None else [],
            marginal_ic_result=marginal,
            composite_result=composite,
            summary_by_feature=summary_by_feature,
            root_analysis_status=str(report.get("analysis_status")),
            event_identity=event_identity or compute_event_identity(None, None),
            event_context=getattr(self, "_event_context", None),
            split_context=split_ctx,
            config_hash=str(self._current_config_hash or self._hash_config(self._current_config or self._config)),
            features_source_hash=features_source_hash,
            features_path=str(features_path) if features_path else None,
            labels_content_hash=labels_content_hash,
            symbol=str(symbol),
            timeframe=str(timeframe),
            case_id=case_id,
            generated_at=str(report.get("generated_at")),
            fit_mode=str(report_meta.get("fit_mode") or metadata.get("fit_mode") or "unset"),
            pit_stats_version=str(report_meta.get("pit_stats_version") or PIT_STATS_VERSION),
            ic_method=str(((self._current_config or self._config).ic_calculation.methods or ["spearman"])[0]),
            label_horizon=int(split_ctx["effective_horizon"]) if split_ctx.get("effective_horizon") is not None else None,
            label_return_type=str((self._current_config or self._config).labels.return_type),
            report_ref=report_ref,
        )
        validate_survivor_output(payload, report_meta=report_meta, report_ref_path=report_json_path)
        output_dir = str(Path(report_json_path).parent) if report_json_path else "data_cache/reports"
        try:
            path = self._reporter.save_survivor_output(payload, output_dir=output_dir, case_id=case_id)
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except Exception as exc:  # noqa: BLE001 — IO 失敗只記 log（A1-6），報告照存
            logger.error("survivor output write failed: %s", exc, exc_info=True)
            return {
                "status": "computation_failed",
                "reason": self._survivor_reason("write_failed"),
                "path": None,
                "sha256": None,
                "case_id": case_id,
            }
        return {"status": "ok", "reason": None, "path": str(path), "sha256": digest, "case_id": case_id}

    def _resolve_case_id(self, metadata: dict) -> str:
        case_id = metadata.get("case_id") if metadata else None
        if case_id:
            return str(case_id)
        return "ic_gatekeeper"

    def _resolve_filtered_path(self, metadata: dict) -> str:
        symbol = metadata.get("symbol") if metadata else None
        timeframe = metadata.get("timeframe") if metadata else None
        if symbol and timeframe:
            name = f"{symbol}_{timeframe}_filtered.h5"
        else:
            name = "filtered_features.h5"
        return str(Path("data_cache/features") / name)

    def _load_features_hdf5(self, features_path: str) -> tuple[pd.DataFrame, dict]:
        if not Path(features_path).exists():
            raise FileNotFoundError(f"features_path not found: {features_path}")

        with h5py.File(features_path, "r") as file:
            group = self._select_first_group(file)
            if group is None:
                raise InvalidInputError("HDF5 has no groups")

            features = group.get("features")
            if features is None:
                raise InvalidInputError("features dataset missing")
            feature_matrix = features[:]

            timestamps = group.get("timestamps")
            if timestamps is not None:
                index = pd.Index(timestamps[:], name="timestamp")
            else:
                index = pd.RangeIndex(start=0, stop=feature_matrix.shape[0])

            feature_names = self._read_names(group, "feature_names")
            if not feature_names:
                feature_names = [f"feature_{i}" for i in range(feature_matrix.shape[1])]

            features_df = pd.DataFrame(feature_matrix, columns=feature_names, index=index)
            metadata = {}
            metadata_json = group.attrs.get("metadata_json")
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
            return features_df, metadata

    def _load_labels_hdf5(self, labels_path: str) -> Optional[pd.DataFrame]:
        if not labels_path:
            return None
        if not Path(labels_path).exists():
            raise FileNotFoundError(f"labels_path not found: {labels_path}")

        with h5py.File(labels_path, "r") as file:
            group = self._select_first_group(file)
            if group is None:
                raise InvalidInputError("labels HDF5 has no groups")
            labels = group.get("labels")
            if labels is None:
                raise InvalidInputError("labels dataset missing")
            label_matrix = labels[:]
            if label_matrix.ndim == 1:
                label_matrix = label_matrix.reshape(-1, 1)
            label_names = self._read_names(group, "label_names")
            if not label_names:
                label_names = ["label"]
            labels_df = pd.DataFrame(label_matrix, columns=label_names)
            if "timestamps" in group:
                labels_df.index = pd.Index(group["timestamps"][:], name="timestamp")
            return labels_df

    def _load_meta_json(self, meta_path: Optional[str]) -> dict:
        if not meta_path:
            return {}
        path = Path(meta_path)
        if not path.exists():
            raise FileNotFoundError(f"meta_path not found: {meta_path}")
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}

    def _select_first_group(self, file: h5py.File) -> Optional[h5py.Group]:
        if not file.keys():
            return None
        first_key = list(file.keys())[0]
        group = file[first_key]
        if isinstance(group, h5py.Group) and group.keys():
            inner_key = list(group.keys())[0]
            inner_group = group[inner_key]
            if isinstance(inner_group, h5py.Group):
                return inner_group
        if isinstance(group, h5py.Group):
            return group
        return None

    def _read_names(self, group: h5py.Group, key: str) -> list[str]:
        if key in group:
            raw = list(group[key][:])
        else:
            raw = list(group.attrs.get(key, []))
        names = []
        for item in raw:
            if isinstance(item, (bytes, np.bytes_)):
                names.append(item.decode("utf-8"))
            else:
                names.append(str(item))
        return names

    def _report_progress(
        self, stage: int, stage_name: str, progress: float, message: str
    ) -> None:
        if self._progress_callback is None:
            return
        payload = {
            "stage": stage,
            "stage_name": stage_name,
            "progress": progress,
            "message": message,
        }
        try:
            self._progress_callback(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Progress callback failed: %s", exc)

    def _apply_config_override(self, config_override: Optional[dict]) -> ICConfig:
        if not config_override:
            return self._config
        if not isinstance(config_override, dict):
            raise InvalidInputError("config_override must be a dict")
        base = self._config.model_dump(by_alias=True)
        merged = self._deep_merge(base, config_override)
        return ICConfig.model_validate(merged)

    def _hash_config(self, config: ICConfig) -> str:
        payload = json.dumps(config.model_dump(), sort_keys=True)
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    def _apply_tier_config(self, config: ICConfig) -> ICConfig:
        data = config.model_dump(by_alias=True)
        tier_cfg = (data.get("feature_tiers") or {})
        active_preset = str(tier_cfg.get("active_preset", "intermediate"))
        presets = tier_cfg.get("presets") or {}
        custom = tier_cfg.get("custom_overrides") or {}

        if active_preset == "custom":
            stage_overrides = custom.get("stage_overrides") or {}
            module_overrides = custom.get("module_overrides") or {}

            for key, enabled in stage_overrides.items():
                if key in LOCKED_STAGE_KEYS:
                    continue
                path = STAGE_OVERRIDE_PATHS.get(key)
                if path is None:
                    continue
                _set_nested_bool(data, path, bool(enabled))

            for key, enabled in module_overrides.items():
                path = MODULE_ENABLED_PATHS.get(key)
                if path is None:
                    continue
                _set_nested_bool(data, path, bool(enabled))
        else:
            preset = presets.get(active_preset) or presets.get("intermediate") or {}
            deep_enabled = bool(preset.get("deep_analysis", True))
            disabled_modules = preset.get("disabled_modules") or []

            if not deep_enabled:
                for section, field in MODULE_ENABLED_PATHS.values():
                    if isinstance(data.get(section), dict):
                        data[section][field] = False
            else:
                for section, field in MODULE_ENABLED_PATHS.values():
                    # F1.2 tier truth table(D13)：不強制覆寫 factor_return.enabled。
                    # foundation 走 deep_enabled=False 分支 → 全模組 False。
                    # intermediate/advanced：保留 schema/request 的 enabled 值
                    # （F1.2~F4 預設 False 仍 stopgap;F5.2 flip True 後自然入 run）。
                    # custom 走 module_overrides 分支。
                    if section == "factor_return":
                        continue
                    if isinstance(data.get(section), dict):
                        data[section][field] = True
                for module_name in disabled_modules:
                    path = MODULE_ENABLED_PATHS.get(module_name)
                    if path is None:
                        continue
                    section, field = path
                    if isinstance(data.get(section), dict):
                        data[section][field] = False

            # 具名 preset 同樣映射 fdr_correction→significance.fdr.enabled
            # （UI 三 preset 皆 fdr_correction=true；缺 stage_overrides 時強制 ON）
            stage_overrides = custom.get("stage_overrides") or {}
            fdr_path = STAGE_OVERRIDE_PATHS["fdr_correction"]
            if "fdr_correction" in stage_overrides:
                _set_nested_bool(
                    data, fdr_path, bool(stage_overrides["fdr_correction"])
                )
            else:
                _set_nested_bool(data, fdr_path, True)
            # GAP-2 Task 4.1／5.1：具名 preset 分支同樣消費 marginal_ic（純 mapping；缺則沿 config 預設開）
            if "marginal_ic" in stage_overrides:
                _set_nested_bool(
                    data, STAGE_OVERRIDE_PATHS["marginal_ic"], bool(stage_overrides["marginal_ic"])
                )

        return ICConfig.model_validate(data)

    @staticmethod
    def _is_deep_analysis_enabled(config: ICConfig) -> bool:
        tier = config.feature_tiers
        if tier.active_preset == "custom":
            return True
        preset = tier.presets.get(tier.active_preset)
        if preset is None:
            return True
        return bool(preset.deep_analysis)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _passes_threshold(
        value: Any, threshold: float, inverse: bool = False
    ) -> bool:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return False
        if inverse:
            return float(value) <= float(threshold)
        return float(value) >= float(threshold)

    @staticmethod
    def _is_float_dataframe(df: pd.DataFrame) -> bool:
        for dtype in df.dtypes:
            if dtype not in (np.float32, np.float64):
                return False
        return True
