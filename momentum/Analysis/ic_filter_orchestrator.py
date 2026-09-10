"""IC filter orchestrator for Gatekeeper pipeline."""

from __future__ import annotations

import functools
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
from momentum.Analysis.ic_reporter import ICReporter, _finite_or_neg_inf
from momentum.Analysis.marginal_ic import MarginalICParams, compute_marginal_ic
from momentum.Analysis.monotonicity_tester import MonotonicityTester
from momentum.Analysis.binary_discrimination import (
    BINARY_STATUS_OK,
    _permute_blocks,
    block_ids_for_events,
    block_permutation_oracle,
    mann_whitney_table,
    rank_biserial_stat,
)
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
    AnalysisCancelled,
    InsufficientDataError,
    InvalidInputError,
    ModuleUnavailableError,
)
from momentum.core.logging import get_logger
from momentum.core.contracts import (
    EventIsolationRows,
    ORACLE_RETURN_KINDS,
    AlignmentSpec,
    AlignmentViolationError,
    ExposurePayload,
    FactorModuleResult,
    OrthogonalizationPayload,
    SelectionScope,
    SplitPlan,
    TimestampDiscontinuityError,
    ValidatedBinaryLabel,
    binary_label_digest,
    deny_factor_in_ok_oos,
    is_event_label_consumed,
    _coerce_timestamp_array,
    _normalize_symbol_value,
    split_per_symbol,
    validate_alignment,
    validate_split_pair_integrity,
    LABEL_KIND_EVENT_GIVEN,
    AlignmentReport,
    derive_label_kind,
    validate_consumed_label,
)
from momentum.core.protocols import IKlineReader
from momentum.core.split_preview import (
    count_binary_classes_in_rows as _count_binary_classes_in_rows,
    holdout_split_point,
    holdout_test_row_index,
)
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


#: EVTLABEL Task 2.2：這些鍵**不得**經 `config_override` 傳（`ICConfig` 會靜默吞掉）。
_ISOLATION_CONTROL_KEYS: frozenset[str] = frozenset(
    {"event_isolation", "event_purge_rows", "label_window_rows", "lookahead_depth_rows"}
)


def _reject_isolation_in_config_override(config_override: Optional[dict]) -> None:
    """走錯通道 ⇒ 當場失敗（而不是靜默不生效）。"""
    if not isinstance(config_override, dict):
        return
    hit = sorted(_ISOLATION_CONTROL_KEYS.intersection(config_override))
    if hit:
        raise ValueError(
            f"event isolation must be passed as the `event_isolation` kwarg, not config_override（誤用鍵：{hit}）"
            "——ICConfig 對未知鍵是靜默忽略，走 config 通道會傳了不生效也不報錯"
        )


def _timed_stage(name: str):
    """FU-3（使用者 2026-09-10 併入 EVTLABEL P1）：逐 stage 計時，寫 `metadata.stage_timings`。

    出生理由：報告**完全沒有**分段耗時，導致「多 horizon 會多久」「哪一段該加速」只能用猜的
    ——主委 2026-09-10 就因此把事件 run 成本估錯一個量級（估幾分鐘、實際 39k 特徵跑不完）。
    🔴 秒數**本質非決定性** ⇒ `tests/momentum/helpers/ichc_run.canonical_sha` 之
    `_CLOCK_KEYS` 已納入 `stage_timings`（與 `generated_at` 同類），golden 不受影響。
    同名 stage 多次呼叫（fallback 路徑會重跑 stage5/6）⇒ **累加**，非覆蓋。
    """

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            started = time.perf_counter()
            try:
                return fn(self, *args, **kwargs)
            finally:
                elapsed = time.perf_counter() - started
                timings = getattr(self, "_stage_timings", None)
                if timings is None:
                    timings = {}
                    self._stage_timings = timings
                timings[name] = round(timings.get(name, 0.0) + elapsed, 3)

        return wrapper

    return deco


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


def _memory_snapshot() -> Optional[dict]:
    """EVTALIGN Task 4.1：{rss, phys_total, swap_used}（bytes）；取不到 ⇒ None（不擋、不猜）。"""
    try:
        import psutil  # 延遲載入：非 hot path，且缺套件時退化為不觀測

        proc = psutil.Process()
        return {
            "rss": int(proc.memory_info().rss),
            "phys_total": int(psutil.virtual_memory().total),
            "swap_used": int(psutil.swap_memory().used),
        }
    except Exception:  # noqa: BLE001
        return None


_SWAP_GROWTH_WARN_BYTES = 1 << 30  # swap 自 analyze 起增長 ≥ 1 GB ⇒ 視為 thrash 徵兆


def _memory_pressure(baseline: Optional[dict]) -> Optional[dict]:
    """RSS 超過實體記憶體，或 swap 自基線增長 ≥ 1 GB ⇒ 回傳觀測值（供 WARN）；否則 None。**不 raise。**

    實測依據（SPEC Task 4.1）：17 GB RSS／8 GB 實體、swap 15.6 GB、CPU 3.3% ＝ thrash。
    """
    now = _memory_snapshot()
    if now is None:
        return None
    rss_over = now["rss"] > now["phys_total"]
    swap_growth = now["swap_used"] - int((baseline or {}).get("swap_used", now["swap_used"]))
    if not rss_over and swap_growth < _SWAP_GROWTH_WARN_BYTES:
        return None
    return {
        "rss_bytes": now["rss"], "phys_total_bytes": now["phys_total"],
        "swap_used_bytes": now["swap_used"], "swap_growth_bytes": int(max(swap_growth, 0)),
        "reason": "rss_exceeds_physical" if rss_over else "swap_growth",
    }


def _intersect_features_with_kline_period(
    features_df: pd.DataFrame,
    meta: Optional[dict],
    kline_reader: Optional[IKlineReader],
    *,
    event_period_ms: Optional[tuple] = None,
) -> tuple[pd.DataFrame, Optional[dict]]:
    """EVTALIGN Task 3.1：分析區間＝feature 期間 ∩ K 線期間；裁掉的根數與採用區間**揭露**，禁靜默。

    使用者原話④：「還要手動重新生成特徵，手動K線對齊，這太蠢了，是缺陷吧」⇒ 期間不一致由系統處理。
    - feature 超出 K 線頭／尾的列**無法算 label**（沒有 close），裁掉並記 `trimmed_bars.head/tail`。
    - K 線超出 feature 的部分由 `_coterminalize_close`（Task 1.1）處理，不在此。
    - 交集為空 ⇒ fail-closed，訊息含 feature／K 線／（若知）事件三者期間。
    - 沒有 K 線來源（無 reader 或 meta 缺 symbol/timeframe）⇒ 不裁、回 None（預載 label 路徑各自判定）。
    回傳 `(features_df, period_alignment | None)`；`period_alignment` 之 `trimmed_bars` 皆 0 表示同尾同頭。
    """
    if kline_reader is None or not meta:
        return features_df, None
    symbol = meta.get("symbol")
    timeframe = meta.get("timeframe")
    if not symbol or not timeframe:
        return features_df, None
    raw = kline_reader.read_klines(symbol, timeframe)
    if raw is None or raw.empty:
        return features_df, None
    kline_index = _normalize_frame_time_index(raw, "raw_data")
    feature_index = _normalize_ic_time_index(features_df.index, "features_df")
    k_start, k_end = kline_index[0], kline_index[-1]
    keep = np.asarray((feature_index >= k_start) & (feature_index <= k_end))
    kept = np.flatnonzero(keep)
    feature_period = {"start": str(feature_index[0]), "end": str(feature_index[-1]), "bars": int(len(feature_index))}
    kline_period = {"start": str(k_start), "end": str(k_end), "bars": int(len(kline_index))}
    if kept.size == 0:
        ev = ""
        if event_period_ms:
            ev = (f"；事件期間 [{pd.Timestamp(int(event_period_ms[0]), unit='ms')}, "
                  f"{pd.Timestamp(int(event_period_ms[1]), unit='ms')}]")
        raise AlignmentViolationError(
            f"feature 期間 [{feature_period['start']}, {feature_period['end']}] 與 K 線期間 "
            f"[{kline_period['start']}, {kline_period['end']}] 無交集{ev}——系統無法對齊"
            "（請確認選到的 feature run 與 K 線快取是同一 symbol/timeframe；不是要你重生特徵）"
        )
    head = int(kept[0])
    tail = int(len(keep) - 1 - kept[-1])
    period_alignment = {
        "used": {"start": str(feature_index[kept[0]]), "end": str(feature_index[kept[-1]]), "bars": int(kept.size)},
        "trimmed_bars": {"head": head, "tail": tail},
        "feature_period": feature_period,
        "kline_period": kline_period,
    }
    if event_period_ms:
        period_alignment["event_period"] = {
            "start": str(pd.Timestamp(int(event_period_ms[0]), unit="ms")),
            "end": str(pd.Timestamp(int(event_period_ms[1]), unit="ms")),
        }
    if head or tail:
        features_df = features_df.iloc[kept]
    return features_df, period_alignment


def _coterminalize_close(close: pd.Series, feature_index: pd.Index) -> pd.Series:
    """EVTALIGN Task 1.1（B）：label 生成前把 close 裁到 feature 尾——守衛 `validate_alignment` 一字不改。

    K 線比特徵長（結尾多出 N 根）是正常情形（使用者：「K線比特徵多也很合理吧」），但 label 由
    **整條** close 生成再 reindex 到 feature index 時，feature 尾端 lag 列會有真值 ⇒
    守衛「尾端 NaN 必須＝lag」誤擋。裁切把截短情形**化約為同尾情形**：label 逐值相同
    （`handoffs/20260908-probe-option-b-trim.py` rc=0），少掉的 lag 列正是同尾本來就沒有的。
    裁切依據 `feature_index[-1]` 從既有參數**推導**（SPEC §C-7），不新增任何參數；
    stage0（預載 labels 之 oracle close）與 stage2（生成 close）**兩個呼叫點都接**，
    防「一點 derive、一點仍信參數」漂移。K 線尾早於 feature 尾 ⇒ 本式 no-op，交守衛照舊判定。
    """
    if len(feature_index) == 0:
        raise AlignmentViolationError("feature_index is empty; cannot coterminalize close")
    return close.loc[close.index <= feature_index[-1]]


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
        "No preloaded label file (labels_df=None): mainline label will be generated from kline with configured horizon (normal path, not an error)",
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
    split_point = holdout_split_point(n_rows, oos_test_size=float(config.oos_test_size))
    effective_purge = max(int(purge_gap), effective_horizon, 0)
    effective_embargo = int(config.embargo)
    train_rows = np.arange(0, split_point, dtype=int)
    # EVTLABEL Task 2.2（R3 `CODEX-R1-P1-04`）：test 段列計畫改由 `momentum/core/split_preview` 之
    # **單一純函式**產生——service 的顯式模式 fast-fail 預檢呼叫同一支，兩端不可能漂。
    test_rows = holdout_test_row_index(
        n_rows,
        oos_test_size=float(config.oos_test_size),
        purge_gap=effective_purge,
        embargo=effective_embargo,
    )
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


def _optional_row_count(value: Any) -> Optional[int]:
    """列數：有就轉 int，**沒有就是 `None`**——禁以 0 代表「不知道」。

    🔴 `CODEX-R2-P1-01`（2026-09-06 R2）：`oos_downgrade` 的三個列數會直接進畫面。
    以 0 當缺值 ⇒ 使用者看到「訓練 0 列、測試 0 列、需要 0 列」，
    這是**假的量化事實**（0 是一個合法且看起來像真的答案），
    而 `None` 會走前端 `ic-oos-downgrade-no-rows` 分支明講「沒有列數可報」。

    🔴 `_split_fallback_metadata` 的 `details` **也走本 helper**。原本想跳過它
    （legacy 欄位、無前端消費者），但實跑發現 `int(None)`／`int("n/a")` 會讓
    整條 fallback **拋例外**——那是潛伏的當機，不是「保守的 0」。
    既有測試只斷言該欄之**鍵集**，值改為 `None` 不動任何斷言。
    """
    if value is None:
        return None
    if isinstance(value, bool):  # bool 是 int 的子類，會靜默變 0/1
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _split_fallback_metadata(reason: str, details: dict[str, Any]) -> dict[str, Any]:
    """建立 default-ON 回退 metadata，避免 legacy 結果被誤標為 OOS。"""
    return {
        "requested": True,
        "applied": False,
        "scope": "full_sample_legacy",
        "oos_guarantees": False,
        "reason": reason,
        # 🔴 `CODEX-R2-P1-01` 之延伸：本欄無前端消費者（既有測試只斷言**鍵集**），
        #    但 `int(None)`／`int("n/a")` 會讓整條 fallback **拋例外**——
        #    那是潛伏的當機，不是「保守的 0」。改走同一個 helper，鍵集不變。
        "details": {
            "train_rows": _optional_row_count(details.get("train_rows")),
            "test_rows": _optional_row_count(details.get("test_rows")),
            "min_test_rows": _optional_row_count(details.get("min_test_rows")),
        },
    }


class ICFilterOrchestrator:
    """IC 篩選協調器 — 八階段流水線 + 快取策略 + 篩選日誌。"""

    def __init__(self, config: ICConfig):
        self._config = config
        # ── EVTLABEL Task 3.7：匯入標籤模式之置換自檢與負對照之產物 ──────────────
        #: 負對照失敗時為 `"negative_control_failed"`（Task 3.8 之倖存者輸出據此標 suppressed）。
        self._survivor_suppressed_reason: Optional[str] = None
        #: 置換收據（seed／n_perm／block_len／n_blocks／budget_floor_hit／negative_control）。
        self._binary_oracle_receipt: Optional[dict] = None
        #: label 視窗有幾根特徵 K 線（由 service 之 `event_isolation` 設定；決定區塊長度）。
        self._binary_label_window_bars: int = 0
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
        event_label_owners: Optional[dict] = None,
        event_context: Optional[dict] = None,
        event_isolation: Optional[EventIsolationRows] = None,
        # ── EVTLABEL Task 3.3：匯入標籤模式之入口 kwargs（皆顯式，禁走 config_override）──
        #: 與 `event_label_values` **同鍵**（feature_cutoff_ms）之 0/1 向量；None ⇒ 這批沒有可用 0/1。
        event_binary_labels: Optional[dict] = None,
        #: 使用者**請求**的模式（auto／return_rule／imported_binary）。effective mode 在 stage3 決定。
        label_mode_requested: str = "auto",
        #: staging 已看出「用不了 0/1」的原因（no_label_column／label_invalid_domain）；供報告揭露。
        label_mode_hint: Optional[str] = None,
    ) -> dict:
        """主入口：執行完整八階段流水線。

        event_isolation（EVTLABEL Task 2.2）：事件路徑之隔離區兩項（已換算成特徵列數）。
        `label_window_rows` 抬 **purge**、`lookahead_depth_rows` 由 service 抬 **embargo**。
        🔴 **只走這個顯式 kwarg**：`config_override` 對未知鍵是靜默忽略，走那條等於沒生效也不報錯。

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
        # EVTLABEL Task 2.2：隔離區列數**只走顯式 kwarg**。若有人把它塞進 config_override，
        # `ICConfig` 會靜默吞掉（Pydantic extra=ignore）⇒ 傳了不生效也不報錯，是最難查的一種錯。
        # 故在入口 fail-closed，把「走錯通道」變成當場失敗。
        _reject_isolation_in_config_override(config_override)
        # FU-3（R1 `CODEX-R1-P2-03`）：計時是 **analyze-scoped**。不在入口清空的話，重用同一個
        # analyzer 跑第二次（掃描格逐格重用、UI 連續分析）會把上一次的秒數疊進來 ⇒ 揭露變成假的。
        # 同一次 analyze 內 fallback 重跑 stage5/6 之累加是**刻意**的，兩者不衝突。
        self._stage_timings = {}
        self._clear_deep_analysis_cache()
        # GAP-2 Task 4.1：入口存路徑（供 refilter／persist provenance）＋當次 config hash
        self._features_path = str(features_path) if features_path else None
        self._labels_path = str(labels_path) if labels_path else None
        self._current_config_hash = self._hash_config(config)
        self._current_config = config  # 本次 effective config（provenance ic_method／label_return_type 取此，非建構時 config）
        self._event_context = dict(event_context) if event_context else None  # GAP-3 B2.4：survivor v2 六鍵來源
        # EVTALIGN Task 2.1：stage0／stage2 鷹架之 AlignmentViolationError 於 event_label_values 提供時延後，
        # 由 stage3 依「該序列是否真被消費」裁定 raise 或降為診斷（每次 analyze 重置；fallback 重跑亦重置）。
        self._deferred_scaffold_violation: Optional[AlignmentViolationError] = None
        self._period_alignment: Optional[dict] = None  # EVTALIGN Task 3.1：stage0 寫入
        self._memory_baseline = _memory_snapshot()  # EVTALIGN Task 4.1：WARN 之比較基線（swap 增長）
        self._memory_warned = False
        event_period_ms: Optional[tuple] = None
        if event_timestamps:
            _ev = np.asarray(list(event_timestamps))
            if np.issubdtype(_ev.dtype, np.number) and len(_ev):
                _mx = float(np.nanmax(np.abs(_ev.astype(float))))
                _scale = 1 if _mx >= 1e12 else 1000
                event_period_ms = (int(np.nanmin(_ev) * _scale), int(np.nanmax(_ev) * _scale))

        self._report_progress(0, "ingestion", 0.02, "loading inputs")
        features_df, labels_df, metadata, stage0_log = self._stage0_ingestion(
            features_path, labels_path, meta_path, config=config, kline_reader=kline_reader,
            defer_alignment_error=event_label_values is not None,
            event_period_ms=event_period_ms,
        )
        _pa = self._period_alignment
        if _pa and (int(_pa["trimmed_bars"]["head"]) or int(_pa["trimmed_bars"]["tail"])):
            # 🔴 只在真的裁了才寫鍵：零裁切之報告逐位元組不變（§G-1 golden）；裁了就必揭露（禁靜默）
            metadata = dict(metadata)
            metadata["period_alignment"] = dict(_pa)

        # ── TFWINDOW Task 3.1：rolling 視窗依 run 週期換算（reference_tf=12h）——由 metadata.timeframe 注入引擎；
        #    缺／非法 ⇒ 不換算並 fail-loud 揭露（不假換算）。全路徑寫 ic_window_disclosure（gap2 golden 已依 §G 重凍，diff 只含此鍵）。
        #    reference_tf 以 effective config（含 config_override）同步進引擎（R5 CODEX-R5-P2-03）。
        _tf_adjust = self._ic_engine.set_timeframe(
            metadata.get("timeframe") if isinstance(metadata, dict) else None,
            reference_tf=config.ic_calculation.icir.reference_tf,
        )
        metadata = dict(metadata)
        metadata["ic_window_disclosure"] = {
            "window_unit": "bars",
            "timeframe": metadata.get("timeframe"),
            "reference_tf": config.ic_calculation.icir.reference_tf,
            "timeframe_adjustment": _tf_adjust,
            "adjusted_windows": [int(w) for w in self._ic_engine._adjust_rolling_windows(list(config.ic_calculation.rolling_windows))],
            "icir_role": "threshold",
        }

        split_context: Optional[dict] = None
        if config.ic_train_test_split:
            expected_freq = _resolve_expected_freq(metadata)
            allowed_symbols = _resolve_metadata_symbol_allowlist(metadata)
            symbol = next(iter(allowed_symbols))
            effective_horizon = _resolve_effective_label_horizon(config, labels_df)
            # 🔴 EVTLABEL Task 2.2：purge 由**答案窗**決定，不再只吃主線 horizon。
            #    受理 run（12h 事件 h=1 配 1h 特徵）之前是 purge=5（主線 default_horizon，與 h 無關），
            #    12 根的答案窗被塞在 embargo 裡 ⇒ 不洩漏但標籤貼錯位置。
            #    取 max 是因為兩者都必須被擋住：主線 label 的 5 根、事件 label 的 12 根。
            event_window_rows = int(event_isolation.label_window_rows) if event_isolation else 0
            # EVTLABEL Task 3.7：答案窗有幾根 ⇒ 決定區塊置換之區塊長度（視窗跨過幾個事件，
            # 那幾個就得綁在一起洗）。與 purge 用的是**同一個**數字，不另建第二份。
            self._binary_label_window_bars = int(event_window_rows)
            effective_purge_gap = max(effective_horizon, event_window_rows)
            split_result = _build_holdout_split_plan(
                features_df,
                config,
                symbol,
                expected_freq,
                purge_gap=effective_purge_gap,
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
                    event_label_owners=event_label_owners,
                    event_context=event_context,
                    event_isolation=event_isolation,
                    # EVTLABEL Task 3.3：三個 fallback 呼叫點皆須透傳（漏一個＝該路徑靜默變報酬版）
                    event_binary_labels=event_binary_labels,
                    label_mode_requested=label_mode_requested,
                    label_mode_hint=label_mode_hint,
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
            # 🔴 B3 review R1（`CODEX-R1-P1-01`／`P1-02`、`COMPOSER-R1-P1-01`、`GROK-R1-P1-01`／
            #    `P1-02`／`P1-03`——五條 finding、三家全員命中同一處）：選樣預檢原本住在
            #    **service**，用 `create_ic_analyzer(None)._config` 與自行組的 purge/embargo
            #    重建一份「測試段」。三家實測指出那份重建**必然**與這裡分歧
            #    （config_override 未套用；`purge=label_window_rows` 而非 `max(H, W)`；
            #    `embargo=depth` 而非 `max(config_embargo, depth)`），且 `read_hdf(columns=[])`
            #    對本專案真實 h5（h5py CArray，非 pandas table）恆失敗 ⇒ 預檢從未真正跑過。
            #    ⇒ 改在**這裡**判：`test_plan.row_index` 就是實際測試段，沒有第二份算術可漂。
            #    仍在 preprocessing **之前**，所以「不必跑完才知道不足」的目的照樣達成。
            selection_counts = _count_binary_classes_in_rows(
                event_binary_labels, features_df.index, test_plan.row_index
            )
            if selection_counts is not None:
                split_context["selection_preview"] = dict(selection_counts)
                floor = int(config.event_filter.min_events_per_class)
                if str(label_mode_requested) == "imported_binary" and min(
                    selection_counts["n_pos"], selection_counts["n_neg"]
                ) < floor:
                    raise ValueError(
                        "class_below_min_selection: 驗證段內正例 "
                        f"{selection_counts['n_pos']}／反例 {selection_counts['n_neg']}，"
                        f"未達每類最少 {floor} 個——明示 imported_binary 模式不接受靜默降級"
                        "（改用 auto 會退回報酬版並在報告寫明原因）"
                    )
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
            if event_isolation is not None:
                # EVTLABEL Task 2.2：**只在事件路徑寫**這三鍵 ⇒ 全域報告逐位元組不變（G-1）。
                # `embargo_source` **不在此寫**（R1 C7 定死唯一寫入點＝service 之 `metadata.isolation`）：
                # orchestrator 看不到「service 抬高前的原 config embargo」，在此判會是第二份推論。
                metadata["ic_train_test_split"].update(
                    {
                        "purge_gap_source": (
                            "event_label_window" if event_window_rows > effective_horizon else "mainline_horizon"
                        ),
                        "event_label_window_rows": int(event_window_rows),
                        "lookahead_depth_rows": int(event_isolation.lookahead_depth_rows),
                    }
                )
            # UAT 2026-09-08（使用者：「為何要跑完才知道不足，要重跑第二次?」）：stage4 之 rolling warmup 檢查
            # 只依賴「測試段列數／視窗／horizon」，切分計畫做完就全部已知 ⇒ 在預處理**之前**先判，
            # 不足直接走全樣本，不再白跑一輪 39k 特徵的預處理。stage4 那條檢查保留為安全網（規則同一份）。
            precheck = self._precheck_rolling_warmup(
                features_df, config, split_context, event_timestamps,
                event_conditional=self._is_event_conditional_precheck(event_label_values, config),
            )
            if precheck is not None:
                return self._run_full_sample_fallback(
                    features_path,
                    labels_path,
                    meta_path,
                    config_override,
                    progress_callback,
                    kline_reader,
                    reason="rolling_warmup_insufficient",
                    details=precheck,
                    event_timestamps=event_timestamps,
                    event_label_values=event_label_values,
                    event_label_owners=event_label_owners,
                    event_context=event_context,
                    event_isolation=event_isolation,
                    # EVTLABEL Task 3.3：三個 fallback 呼叫點皆須透傳（漏一個＝該路徑靜默變報酬版）
                    event_binary_labels=event_binary_labels,
                    label_mode_requested=label_mode_requested,
                    label_mode_hint=label_mode_hint,
                    )

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
            labels_df, metadata, config, kline_reader, features_df=features_df,
            defer_alignment_error=event_label_values is not None,
        )

        self._report_progress(3, "event_filter", 0.35, "applying event filter")
        features_df, label_series, event_info = self._stage3_event_filter(
            features_df, label_series, metadata, config, kline_reader,
            event_timestamps=event_timestamps,
            event_label_values=event_label_values,
            event_label_owners=event_label_owners,
            # EVTLABEL Task 3.4：effective mode 之決策點。`split_context` 必須傳——
            # 「能不能用 0/1」取決於**切分後驗證段**每類還剩幾個，而不是整批的正反比例。
            event_binary_labels=event_binary_labels,
            label_mode_requested=label_mode_requested,
            label_mode_hint=label_mode_hint,
            split_context=split_context,
        )
        if event_info.get("label_mode"):
            metadata = dict(metadata)
            metadata["label_mode"] = dict(event_info["label_mode"])
        if event_info.get("conditional_ic_abandoned"):
            # CODEX-R2-P1-04（GROK-R1-P1-01 方案②之下游消費）：事件不足 ⇒ 條件 IC 明確 unavailable，
            # 後續 stage 之數值為主線 return_N 全樣本 IC，報告 metadata 機械標示、禁當條件 IC 消費。
            metadata = dict(metadata)
            metadata["conditional_ic"] = {
                "capability_status": "unavailable",
                "reason": "insufficient_events",
                "label_source": "mainline_return_N",
                "doc": "event_label_values 已提供但事件數 < min_events；下游不得把本報告 IC 當條件 IC",
            }
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
            # ── EVTWARMUP Task 1.2：min_test_events 統計地板（只在 stage3 之後、只認產生者標記；R2 GROK-R2-P0-01）
            if is_event_label_consumed(event_info):
                # stage3 後 features_df 只剩實際被消費之事件列 ⇒ 測試段事件數＝test_mask 命中數
                test_events = int(test_mask.sum())
                split_context["test_events"] = test_events
                min_test_events = int(config.event_filter.min_test_events)
                if test_events < min_test_events:
                    metadata = dict(metadata)
                    split_meta = dict(metadata.get("ic_train_test_split") or {})
                    split_meta["oos_guarantees"] = False
                    split_meta["test_events"] = test_events
                    split_meta["min_test_events"] = min_test_events
                    metadata["ic_train_test_split"] = split_meta
                    if "oos_downgrade" not in metadata:  # 第三寫出點；fallback 富版（若有）優先
                        metadata["oos_downgrade"] = {
                            "reason": "insufficient_test_events",
                            "test_events": test_events,
                            "min_test_events": min_test_events,
                            "train_rows": int(train_mask.sum()),
                            "test_rows": int(test_mask.sum()),
                            "min_test_rows": None,
                        }
                    logger.warning(
                        "IC holdout kept but test-segment events insufficient: test_events=%s min_test_events=%s "
                        "(oos_guarantees=false; no full-sample rerun)", test_events, min_test_events,
                    )
        # 事件路徑視窗尺度揭露——與切分無關（R4 CODEX-R4-P2-03：ic_train_test_split=False 亦須揭露）；
        # 只事件路徑寫；全域待 TFWINDOW 重凍 golden 時一併進
        if is_event_label_consumed(event_info):
            metadata = dict(metadata)
            metadata["ic_window_disclosure"] = {
                **dict(metadata.get("ic_window_disclosure") or {}),
                "icir_role": "diagnostic",   # 事件路徑：ICIR 只作診斷（EVTWARMUP Task 2.1）
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
            event_info=event_info,
        )
        if ic_results.get("status") == "skipped":
            # ICHC R5 one-shot guard：fallback 重跑內再觸發＝設計不變式被破壞
            # （holdout off 後 stage4 不應再 skip）——fail-closed 禁遞迴。
            #
            # 🔴 判別式必須是 `_in_fallback_rerun`，**不是** `_suppress_persist`
            #    （`SCANCUBE` UAT B26 實機打穿，2026-09-07）：
            #    這兩個旗標原本恰好同進同出（只有 fallback 重跑會 suppress），
            #    所以讀錯也看不出來——本函式 `:1198` 的註解甚至已經寫明該用前者。
            #    `SCANCUBE` Task 1.1 讓**掃描格**也 suppress（研究掃描不寫 survivor artifact）
            #    之後巧合被打破：每一格從第一次 warmup skip 就被誤判成「已在重跑內」而直接 raise
            #    ⇒ 使用者的 6 格掃描**全部 unavailable**，掃描等於白跑。
            #    教訓＝旗標一物二用；`_suppress_persist` 只該回答「要不要落檔」。
            if self._in_fallback_rerun:
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
                event_label_owners=event_label_owners,
                event_context=event_context,
                event_isolation=event_isolation,
                # EVTLABEL Task 3.3：三個 fallback 呼叫點皆須透傳（漏一個＝該路徑靜默變報酬版）
                event_binary_labels=event_binary_labels,
                label_mode_requested=label_mode_requested,
                label_mode_hint=label_mode_hint,
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
        # EVTWARMUP Task 2.1：事件路徑 ICIR 多為非有限（redundancy `_score_value` 會給 -inf）⇒ tiebreaker 改吃 ic_mean；
        # 全域路徑一字不改（redundancy_filter.py 不改，改呼叫端傳的分數字典）。
        redundancy_scores, tiebreaker_effective = self._redundancy_scores(event_info, stage5_results, ic_results["icir"])
        if tiebreaker_effective is not None:
            metadata = dict(metadata)
            metadata["tiebreaker_effective"] = tiebreaker_effective
        # UAT 2026-09-09：ic_mean 回退為 pooled point IC 時揭露（只在真的回退時寫鍵；全域 golden 不動）
        _src = dict(getattr(self, "_ic_mean_source", None) or {})
        if _src.get("pooled_point_ic", 0) > 0:
            metadata = dict(metadata)
            metadata["ic_window_disclosure"] = {**dict(metadata.get("ic_window_disclosure") or {}), "ic_mean_source": _src}
        stage6_results = self._stage6_redundancy(
            features_df,
            stage5_results["passed_features"],
            redundancy_scores,
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

        self._attach_stage_timings(report)
        self._report_progress(7, "report", 1.0, "completed")
        self._report = report
        return report

    def _attach_stage_timings(self, report: Any) -> None:
        """FU-3：把逐 stage 耗時（秒）寫進 `metadata.stage_timings`；空則不寫（不留空殼鍵）。"""
        timings = getattr(self, "_stage_timings", None)
        if not timings or not isinstance(report, dict):
            return
        metadata = report.get("metadata")
        if isinstance(metadata, dict):
            metadata["stage_timings"] = dict(sorted(timings.items()))

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
        event_label_owners: Optional[dict] = None,
        event_context: Optional[dict] = None,
        event_isolation: Optional[EventIsolationRows] = None,
        # ── EVTLABEL Task 3.3：匯入標籤模式之入口 kwargs（皆顯式，禁走 config_override）──
        #: 與 `event_label_values` **同鍵**（feature_cutoff_ms）之 0/1 向量；None ⇒ 這批沒有可用 0/1。
        event_binary_labels: Optional[dict] = None,
        #: 使用者**請求**的模式（auto／return_rule／imported_binary）。effective mode 在 stage3 決定。
        label_mode_requested: str = "auto",
        #: staging 已看出「用不了 0/1」的原因（no_label_column／label_invalid_domain）；供報告揭露。
        label_mode_hint: Optional[str] = None,
    ) -> dict:
        """以 flag-off 重跑 full-sample，並只追加 fallback metadata。

        🔴 `event_isolation`（B2 review R1 `CODEX-R1-P2-02`／`GROK-R1-P2-01`，兩家同判）：
        本函式**不用**它——full-sample 沒有切分，隔離區無處可套。收下並原樣透傳只為
        **簽名對稱**：`analyze` 有而 fallback 沒有時，下一個改這條路徑的人會誤以為
        「fallback 也套了隔離」，或依 TODO 傳入而 TypeError。內層 `analyze` 之
        `ic_train_test_split` 因 flag-off 不會建立，三鍵自然不寫。

        LA-0 RULING-3：呼叫前鎖 fit_mode=full_sample + oos_guarantees=False 紅標。
        LA-1 B3：logger.warning + 禁內層 persist + root 紅標後唯一寫出。
        """
        details = details or {}
        # 🔴 `CODEX-R2-P1-01`：走同一個 helper——log 與 metadata 用**同一組值**。
        #    舊版在此另做 `int(..., 0)`，於是 log 印 0、metadata 也是 0，
        #    而缺值與「真的 0 列」在兩處都分不出來；`None` 印成 `None` 才讀得懂。
        train_rows = _optional_row_count(details.get("train_rows"))
        test_rows = _optional_row_count(details.get("test_rows"))
        min_test_rows = _optional_row_count(details.get("min_test_rows"))
        logger.warning(
            "IC full-sample fallback triggered: reason=%s train_rows=%s "
            "test_rows=%s min_test_rows=%s fit_mode=full_sample",
            reason,
            train_rows,
            test_rows,
            min_test_rows,
        )
        # UAT 2026-09-08：降級原因原本只在最後寫進報告，重跑期間畫面只見「又一次 preprocessing」⇒ 即時推到進度通道
        self._report_progress(
            0, "fallback", 0.02,
            f"切分不足（{reason}）：改以全樣本重跑（無 OOS 保證）",
            extra={
                "fallback_reason": reason,
                "fallback_details": {"train_rows": train_rows, "test_rows": test_rows, "min_test_rows": min_test_rows},
            },
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
                event_label_owners=event_label_owners,
                event_context=event_context,
                event_isolation=event_isolation,  # 對稱透傳；full-sample 無切分 ⇒ 不影響結果
                # 🔴 EVTLABEL Task 3.3：0/1 與請求模式**必須**跟著透傳。
                #    退回全樣本改變的是「用哪些列」，不是「用哪一種 label」——
                #    在此丟掉 0/1 會讓 fallback 靜默變成報酬版，而報告仍寫著使用者選了匯入標籤。
                event_binary_labels=event_binary_labels,
                label_mode_requested=label_mode_requested,
                label_mode_hint=label_mode_hint,
            )
        finally:
            self._suppress_persist = prev_suppress
            self._in_fallback_rerun = False

        report_meta = dict(report.get("metadata") or {})
        report_meta.pop("scope", None)
        report_meta["ic_train_test_split"] = _split_fallback_metadata(reason, details)
        report_meta["fit_mode"] = "full_sample"
        # 🔴 UAT（2026-09-07）：`fit_mode=full_sample` 有**兩種**來源，語意完全相反——
        #    ①使用者／設定**主動要求**全樣本擬合（研究用途，合理）
        #    ②資料不足 ⇒ 系統**被迫**退回全樣本（不是誰要求的）
        #    只看 `fit_mode` 分不出來，於是畫面對②說了「這是請求的結果，不是資料不足」
        #    ——把**結果**當成**原因**講給使用者聽，方向剛好相反。
        #    ⇒ 留一個明確的來源標記，讓顯示層不必用猜的。
        report_meta["fit_mode_source"] = "fallback"
        report_meta["oos_guarantees"] = False
        report_meta["pit_stats_version"] = PIT_STATS_VERSION
        # 🔴 `GAP3_EVENT_DISCLOSURE` Task 1.3：把**降級的原因與門檻**帶到 report。
        #    出生事故（2026-09-06 UAT）：畫面只說「來自 full-sample fallback 或無 holdout 保證」，
        #    而 `reason`／`train_rows`／`test_rows`／`min_test_rows` 這四個數字**這裡全都有**、
        #    卻只進了 logger.warning ⇒ 使用者看得到降級、看不到為什麼，也無從判斷該加樣本還是改設定。
        #    本欄**純新增**：`_resolve_root_status` 讀的鍵集不變，既有判定一字未動。
        #    🔴 `CODEX-R2-P1-01`：缺鍵一律 `None`，**不得**以 0 填洞。
        #    R1 我自己立的契約是「未知＝null」，這裡卻還是 `int(details.get(..., 0))`
        #    ⇒ `details` 不完整時畫面印「訓練 0 列、測試 0 列、需要 0 列」，
        #    那是一個**看起來像真的假數字**（與 mutation D8 在防的是同一種病，只是換了進入路徑）。
        report_meta["oos_downgrade"] = {
            "reason": str(reason),
            "train_rows": train_rows,
            "test_rows": test_rows,
            "min_test_rows": min_test_rows,
        }
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
    def _specific_reason(meta: dict) -> Optional[str]:
        """在 metadata 裡找一個**比「沒有保證」更有用**的原因；找不到回 `None`。

        🔴 **只影響 reason 字串，不影響任何判定**——呼叫端已經決定要降級了，
        本函式只是替那個決定找一句使用者做得了事的說明。

        優先序＝**由具體到籠統**：切分自己記的 reason（如 `rolling_warmup_insufficient`，
        它連列數都有）> 事件樣本不足 > 設定直指全樣本 > 切分未套用。
        """
        split = meta.get("ic_train_test_split")
        if isinstance(split, dict):
            reason = split.get("reason")
            if isinstance(reason, str) and reason.strip():
                return reason.strip()
        event_meta = meta.get("event_filter")
        if isinstance(event_meta, dict) and event_meta.get("fallback") is True:
            return "event_filter_fallback"
        if meta.get("fit_mode") == "full_sample":
            # 🔴 分辨「誰要求的」：`fallback` ⇒ 是資料不足**被迫**退回，
            #    不是使用者的設定。兩者的下一步完全不同（加樣本 vs 改設定），
            #    講錯方向會讓使用者去改一個他根本沒設過的東西。
            if meta.get("fit_mode_source") == "fallback":
                return "fit_mode_full_sample_forced"
            return "fit_mode_full_sample"
        if isinstance(split, dict) and (
            split.get("applied") is False or split.get("oos_guarantees") is False
        ):
            return "split_not_applied"
        return None

    @staticmethod
    def _downgrade_branch(report_meta: dict) -> Optional[str]:
        """觸發降級的**分支代號**；`None` ⇒ 未降級（`ok_oos`）。

        🔴 本函式是 root 狀態判定之**唯一**實作，`_resolve_root_status` 只是它的薄包裝。
        分支順序與判準**逐字沿用**改寫前之 `_resolve_root_status`（行為不變，由
        `test_resolve_root_status_behaviour_is_baseline` 之參數化守住）。

        🔴 為什麼要回「分支代號」而不只回 bool（`CODEX-R1-P1-01`／`COMPOSER-R1-P2-02`）：
        揭露層要告訴使用者**為什麼**沒有 OOS 保證。原本只有 full-sample fallback 那條路
        會寫 `oos_downgrade`，其餘四條分支（含事件樣本不足）降級了卻沒有原因可顯示，
        畫面退回籠統警語——那正是本票要修的病，只是漏了四條路。
        ⇒ 分支代號由**同一份判定**產出，不另寫第二份條件。
        """
        meta = report_meta or {}
        if meta.get("oos_guarantees") is False:
            # 🔴 `meta_oos_guarantees_false` 是**循環理由**（「metadata 說沒有保證」＝把結論
            #    再講一次），使用者看了不知道該做什麼——`SCANCUBE` UAT B24 實機打穿：
            #    畫面只給這一句，而真正的原因（滾動 IC 暖身不足）就在同一份 metadata 裡。
            #
            # 🔴 **不可以只把本分支往後排**：那會讓
            #    `{oos_guarantees: False, ic_train_test_split: {applied: True, oos_guarantees: True}}`
            #    這組從 degraded 變成 ok_oos——判定被放寬，方向錯了。
            #    ⇒ **判定不動**（本分支仍然命中、仍然 degraded），只把 reason 挖深。
            return ICFilterOrchestrator._specific_reason(meta) or "meta_oos_guarantees_false"
        if meta.get("fit_mode") == "full_sample":
            # 與 `_specific_reason` 同一套判準（被迫 vs 主動要求，見該處註解）。
            # 兩處必須一致，否則同一份 metadata 走不同入口會得到不同說法。
            return (
                "fit_mode_full_sample_forced"
                if meta.get("fit_mode_source") == "fallback"
                else "fit_mode_full_sample"
            )
        # ICHC Task 4.1：事件樣本不足回退全樣本 → 即使 holdout 已 applied 仍判 degraded
        event_meta = meta.get("event_filter")
        if isinstance(event_meta, dict) and event_meta.get("fallback") is True:
            return "event_filter_fallback"
        split = meta.get("ic_train_test_split")
        if isinstance(split, dict):
            if split.get("oos_guarantees") is False or split.get("applied") is False:
                return "split_not_applied"
            if split.get("applied") is True and split.get("oos_guarantees") is not False:
                return None
        if meta.get("oos_guarantees") is True:
            return None
        return "no_holdout_evidence"

    @staticmethod
    def _resolve_root_status(report_meta: dict) -> tuple[str, bool]:
        """由 metadata 推 root analysis_status / oos_guarantees。

        OOS 宣稱 iff analysis_status=="ok_oos"（G-A2）。
        判定實作住 `_downgrade_branch`（單一來源）；本函式只做 branch → (status, bool)。
        """
        branch = ICFilterOrchestrator._downgrade_branch(report_meta)
        return ("ok_oos", True) if branch is None else ("degraded_full_sample", False)

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
        # 🔴 `CODEX-R1-P1-01`／`COMPOSER-R1-P2-02` 之閉合：**任何**降級都要有具名原因。
        #    原本只有 full-sample fallback 那條路寫 `oos_downgrade`，其餘四條分支
        #    （`event_filter.fallback`／`fit_mode=full_sample`／`split` 未套用／無 holdout 證據）
        #    降級了卻沒有原因，畫面退回籠統警語。
        #    🔴 **只在缺席時補**：fallback 路徑已寫入含四個數字的版本，不得覆蓋成無數字版。
        #    🔴 列數未知時填 `None`（**不是 0**）——0 會被讀成「訓練 0 列」這種假事實。
        if analysis_status != "ok_oos":
            meta = report.get("metadata")
            if isinstance(meta, dict) and not isinstance(meta.get("oos_downgrade"), dict):
                meta["oos_downgrade"] = {
                    "reason": ICFilterOrchestrator._downgrade_branch(meta) or "unknown",
                    "train_rows": None,
                    "test_rows": None,
                    "min_test_rows": None,
                }
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

        # EVTWARMUP（R4 CODEX-R4-P1-01）：refilter 與首跑同一 helper——事件路徑吃 ic_mean，全域吃 icir
        refilter_scores, _tb = self._redundancy_scores(
            self._ic_cache.get("event_info", {}), stage5_results, self._ic_cache["icir"]
        )
        stage6_results = self._stage6_redundancy(
            self._ic_cache["features_df"],
            stage5_results["passed_features"],
            refilter_scores,
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

        self._attach_stage_timings(report)
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
        # EVTWARMUP Task 2.1（R2 CODEX-R2-P1-01）：事件路徑 icir 可為 None ⇒ 排序 key 須 None／NaN 安全
        ordered = sorted(
            table,
            key=lambda item: _finite_or_neg_inf(item.get(sort_by)),
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

    @_timed_stage("stage0_ingestion")
    def _stage0_ingestion(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str],
        config: Optional[ICConfig] = None,
        kline_reader: Optional[IKlineReader] = None,
        *,
        defer_alignment_error: bool = False,
        event_period_ms: Optional[tuple] = None,
    ) -> tuple[pd.DataFrame, Optional[pd.DataFrame], dict, dict]:
        features_df, features_meta = self._load_features_hdf5(features_path)
        labels_df = self._load_labels_hdf5(labels_path)
        meta = self._load_meta_json(meta_path)
        if features_meta and not meta:
            meta = features_meta

        # EVTALIGN Task 3.1：feature ∩ K 線期間（系統自己對齊；裁掉的根數揭露）。
        # 在切分計畫之前做 ⇒ split／purge 都建立在實際分析區間上。
        features_df, period_alignment = _intersect_features_with_kline_period(
            features_df, meta, kline_reader, event_period_ms=event_period_ms
        )
        self._period_alignment = period_alignment

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
                        close = _coterminalize_close(close, feature_index)  # stage0
            _rk = active_config.labels.return_type
            report: Optional[AlignmentReport] = None
            try:
                report = validate_alignment(
                    normalized_features,
                    label_series,
                    _alignment_spec(meta, horizon),
                    close=close if _rk in ORACLE_RETURN_KINDS else None,
                    return_kind=_rk,
                )
            except AlignmentViolationError as exc:
                # EVTALIGN Task 2.1：同 stage2——預載 label 亦可能在 stage3 被覆寫丟棄；延後由 stage3 裁定。
                if not defer_alignment_error:
                    raise
                self._deferred_scaffold_violation = exc
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
        if labels_df is not None and not labels_df.empty and report is not None:
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

    @_timed_stage("stage1_preprocessing")
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
            progress=self._stage1_progress_hook,
        )

    # ── EVTALIGN Task 4.1：階段內進度 ＋ 記憶體 WARN（非阻擋）──────────────────────
    def _stage1_progress_hook(self, sub: dict) -> None:
        """preprocessing 之中間回報：`done/total`＋ETA（估不出 ⇒ `estimating`），並附記憶體壓力 WARN。

        🔴 §C-4／使用者原話①「可以跑的話，幹嘛擋?」：記憶體壓力**只 WARN、不 raise、不擋**；
        正常時**不發**（不製造噪音）；每次 analyze 至多發一次（`_memory_warned`）。
        """
        done, total = int(sub.get("done", 0)), max(int(sub.get("total", 1)), 1)
        frac = min(max(done / total, 0.0), 1.0)
        eta = sub.get("eta_seconds")
        eta_txt = "預估中" if sub.get("eta_state") == "estimating" else (
            f"約 {int(round(float(eta)))} 秒" if eta is not None else "預估中"
        )
        extra = {
            "sub_step": sub.get("sub_step"), "sub_done": done, "sub_total": total,
            "eta_seconds": eta, "eta_state": sub.get("eta_state"),
        }
        pressure = _memory_pressure(getattr(self, "_memory_baseline", None))
        if pressure is not None and not getattr(self, "_memory_warned", False):
            self._memory_warned = True
            extra["warning"] = "memory_pressure_observed"
            extra["warning_detail"] = pressure
        self._report_progress(
            1, "preprocessing", 0.05 + 0.15 * frac,
            f"preprocessing {sub.get('sub_step')} {done}/{total}（ETA {eta_txt}）", extra=extra,
        )

    @_timed_stage("stage2_label_generation")
    def _stage2_label_generation(
        self,
        labels_df: Optional[pd.DataFrame],
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
        features_df: Optional[pd.DataFrame] = None,
        *,
        defer_alignment_error: bool = False,
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
        if features_df is None:
            feature_index = close_index
            features_for_gate = pd.DataFrame(index=feature_index)
        else:
            feature_index = _normalize_ic_time_index(features_df.index, "features_df")
            features_for_gate = features_df.copy(deep=False)
            features_for_gate.index = feature_index
        # EVTALIGN Task 1.1（B）：生成 label **之前**裁到 feature 尾（見 _coterminalize_close）
        close = _coterminalize_close(close, feature_index)  # stage2
        labels_cfg = config.labels
        horizon = _resolve_effective_label_horizon(config, None)

        label_generator = create_label_generator()
        label_series = label_generator.generate_returns_by_type(
            close,
            horizon,
            labels_cfg.return_type,
        )
        labels_df = pd.DataFrame(
            {f"return_{horizon}": label_series}, index=close.index
        )

        labels_for_gate = labels_df.reindex(feature_index)
        label_series = labels_for_gate[f"return_{horizon}"]
        try:
            validate_alignment(
                features_for_gate,
                label_series,
                _alignment_spec(metadata, horizon),
                close=close if labels_cfg.return_type in ORACLE_RETURN_KINDS else None,
                return_kind=labels_cfg.return_type,
            )
        except AlignmentViolationError as exc:
            # EVTALIGN Task 2.1（R3 三家一致，D5 閉合）：這條序列**可能**在 stage3 被 event label 覆寫丟棄。
            # 「要不要當硬閘」不在此決定——延後到 stage3 得知它是否被消費時再裁：
            # 被覆寫 ⇒ 只作診斷（info 揭露）；未被覆寫（事件不足 fallback／filter 未啟用）⇒ 原樣 raise。
            # 判準是「資料是否將被替換」（event_label_values is not None），不是 mode 字串（§C-6）。
            if not defer_alignment_error:
                raise
            self._deferred_scaffold_violation = exc
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

    _STAGE4_SUBSTEPS = 5

    def _stage4_checkpoint(self, name: str, idx: int) -> None:
        """stage4 子計算邊界之進度回報（同時是協作式取消點）；ETA 不估（子步驟耗時差異大，不給假數字）。"""
        frac = (idx - 1) / self._STAGE4_SUBSTEPS
        self._report_progress(
            4, "ic_calculation", 0.55 + 0.15 * frac, f"ic_calculation {name} {idx}/{self._STAGE4_SUBSTEPS}",
            extra={"sub_step": name, "sub_done": idx, "sub_total": self._STAGE4_SUBSTEPS,
                   "eta_seconds": None, "eta_state": "estimating"},
        )

    # ── EVTWARMUP Task 1.1：事件條件 IC 之分流（兩段判；SPEC §C-3）──────────────────
    @staticmethod
    def _is_event_conditional_precheck(event_label_values: Optional[dict], config: ICConfig) -> bool:
        """stage3 之前（尚無 label_source）：`bool(values) and event_filter.enabled`；空 dict／filter 未啟用 ⇒ 主線。"""
        return bool(event_label_values) and bool(config.event_filter.enabled)

    @staticmethod
    def _is_event_conditional_consumed(event_info: Optional[dict]) -> bool:
        """🔴 已淘汰（EVTLABEL Task 3.1）：判準搬到 `momentum/core/contracts.py::is_event_label_consumed`。

        原本只認 `event_label_value`，加了 `imported_binary_label` 之後那個判準會把匯入標籤模式的 run
        誤判成全域路徑（門檻／冗餘分數／隔離都走錯分支）⇒ 集合定義收斂到 contracts 一處。
        本方法保留為薄包裝只為擋住外部殘留呼叫；orchestrator 內呼叫點應為 0
        （`tests/momentum/Analysis/test_evtlabel_label_predicate.py` 機械對證）。
        """
        return is_event_label_consumed(event_info)

    def _redundancy_scores(
        self, event_info: Optional[dict], stage5_results: dict, icir_scores: dict
    ) -> tuple[dict, Optional[str]]:
        """stage6 冗餘之分數字典（analyze／refilter **同一**入口，R4 `CODEX-R4-P1-01`）。

        事件條件 IC 路徑：ICIR 多為非有限（`redundancy_filter._score_value` 會給 -inf）⇒ 改吃 stage5 summary 之 `ic_mean`，
        回 `("ic_mean")` 供 `metadata.tiebreaker_effective`；全域路徑：原樣 `icir_scores`、回 None（不寫鍵）。
        """
        if not is_event_label_consumed(event_info):
            return icir_scores, None
        scores = {
            str(row.get("feature_name")): row.get("ic_mean")
            for row in ((stage5_results or {}).get("summary_table") or [])
            if isinstance(row, dict)
        }
        return scores, "ic_mean"

    def _rolling_warmup_min_rows(self, config: ICConfig, effective_horizon: int) -> int:
        """stage4 與預檢共用的**同一條**規則：max(依週期換算之 rolling 視窗) ＋ effective_horizon。"""
        adjusted = self._ic_engine._adjust_rolling_windows(config.ic_calculation.rolling_windows)
        return int(max(adjusted)) + int(effective_horizon)

    def _precheck_rolling_warmup(
        self,
        features_df: pd.DataFrame,
        config: ICConfig,
        split_context: dict,
        event_timestamps: Optional[list],
        *,
        event_conditional: bool = False,
    ) -> Optional[dict]:
        """切分後、預處理前的 rolling warmup 預檢；不足回 details（同 stage4 之三鍵），足夠回 None。

        事件模式下 stage4 實際拿到的是「落在測試段的事件列」，故此處以事件時間戳 ∩ 測試段計數
        （事件若在 stage3 對齊時被丟，stage4 安全網仍會擋——本預檢只會少擋、不會多擋）。
        EVTWARMUP Task 1.1：`event_conditional=True`（預檢分流真）⇒ **不以 bar-rolling warmup 擋**，只記
        `split_context["test_events"]` 供地板；規則本身（`_rolling_warmup_min_rows`）不動。
        """
        test_mask = np.asarray(split_context["test_mask"], dtype=bool)
        train_mask = np.asarray(split_context["train_mask"], dtype=bool)
        test_rows = int(test_mask.sum())
        # R4 CODEX-R4-P2-02：只有事件條件 IC 路徑才以「事件 ∩ 測試段」計數；主線（disabled／空值／棄條件）保留 bar 列數
        if event_timestamps and event_conditional:
            ts_arr = np.asarray(list(event_timestamps))
            if np.issubdtype(ts_arr.dtype, np.number):
                max_abs = float(np.nanmax(np.abs(ts_arr.astype(float)))) if len(ts_arr) else 0.0
                event_index = pd.to_datetime(ts_arr, unit="ms" if max_abs >= 1e12 else "s", errors="raise")
            else:
                event_index = pd.to_datetime(ts_arr, errors="raise")
            feature_index = _normalize_ic_time_index(features_df.index, "features_df")
            test_rows = int(np.isin(feature_index[test_mask].asi8, pd.DatetimeIndex(event_index).asi8).sum())
            split_context["test_events"] = test_rows
        else:
            split_context["test_events"] = None
        if event_conditional:
            return None
        min_required = self._rolling_warmup_min_rows(config, int(split_context.get("effective_horizon", 0)))
        if test_rows >= min_required:
            return None
        return {
            "train_rows": int(train_mask.sum()),
            "test_rows": test_rows,
            "min_test_rows": min_required,
            "decided_at": "precheck_before_preprocessing",
        }

    def _settle_deferred_scaffold(self, *, scaffold_consumed: bool, info: Optional[dict]) -> None:
        """EVTALIGN Task 2.1（R3 D5 閉合）：裁定 stage0／stage2 延後的鷹架 `AlignmentViolationError`。

        鷹架被消費（未被 event label 覆寫）⇒ 原樣 raise——它就是最終 label，保護不得因事件模式而少；
        鷹架被覆寫丟棄 ⇒ 不擋，但把訊息寫進 `info["scaffold_alignment_deferred"]` 揭露（驗的是被消費的那條，見
        `validate_consumed_label`）。每次呼叫後清空。
        """
        pending = getattr(self, "_deferred_scaffold_violation", None)
        self._deferred_scaffold_violation = None
        if pending is None:
            return
        if scaffold_consumed and pending is not None:
            raise pending
        if info is not None:
            info["scaffold_alignment_deferred"] = str(pending)

    @_timed_stage("stage3_event_filter")
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
        event_label_owners: Optional[dict] = None,
        # ── EVTLABEL Task 3.4：匯入標籤模式之決策輸入 ──────────────────────────
        event_binary_labels: Optional[dict] = None,
        label_mode_requested: str = "auto",
        label_mode_hint: Optional[str] = None,
        split_context: Optional[dict] = None,
    ) -> tuple[pd.DataFrame, pd.Series, dict]:
        event_cfg = config.event_filter
        # GAP-2 Task 4.1：事件身分於 pop timestamps **之前**以 request 原始輸入計算（不可變；refilter 沿用）
        self._event_identity = compute_event_identity(
            getattr(event_cfg, "query", None) if event_cfg.enabled else None,
            list(event_timestamps) if (event_cfg.enabled and event_timestamps is not None) else None,
        )
        if not event_cfg.enabled:
            # 鷹架未被覆寫 ⇒ 它就是被消費的序列 ⇒ 延後之違規在此原樣 raise
            self._settle_deferred_scaffold(scaffold_consumed=True, info=None)
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
            # 事件不足 ⇒ 全樣本續算用的正是鷹架序列 ⇒ 延後之違規在此原樣 raise（不得因事件模式而放行）
            self._settle_deferred_scaffold(scaffold_consumed=True, info=None)
            return features_df, label_series, info

        filtered_index = _normalize_ic_time_index(filtered_df.index, "filtered_events")
        selected_index = feature_index.intersection(filtered_index)
        if selected_index.empty:
            raise AlignmentViolationError("event filter produced no timestamps overlapping features")
        filtered_features = normalized_features.loc[selected_index]
        filtered_label = normalized_label.loc[selected_index]
        label_source: str
        if event_label_values is not None:
            # GAP-3 Task B2.3：條件 IC 只吃事件連續 label_value（SPEC D1-3）；選中之每一 timestamp
            # 必須有 label_value（缺 ⇒ loud，不回退主線 return_N——D1-5 禁以 decision 列 join）。
            # 不傳 ⇒ 本分支不執行，既有 stage 語意與報告鍵逐位元組不變（§G-1 golden 看住）。
            # EVTALIGN Task 2.1：缺值／非有限（CODEX-R1-P2-05）之檢查已**提升為契約**
            # `validate_event_given`，於覆寫**之後**對實際被消費的序列執行；這裡只做覆寫本身
            # （缺 key 先以 NaN 佔位，契約必先以「missing」loud，NaN 不會流出）。
            idx_ms = (selected_index.asi8 // 10**6).astype("int64")
            vals = np.asarray(
                [float(event_label_values[int(t)]) if int(t) in event_label_values else np.nan for t in idx_ms],
                dtype=float,
            )
            filtered_label = pd.Series(vals, index=filtered_label.index, name=filtered_label.name)
            info = dict(info)
            label_source = "event_label_value"
            info["label_source"] = label_source
            info["statistic_kind"] = "conditional_ic"
            info["sample_scope_kind"] = "event"
        else:
            # 未覆寫 ⇒ 被消費的是 stage0／stage2 已過 validate_alignment 之序列的 .loc 限制；
            # 產生者＝本函式（上方 .loc），故 label_source 在此由產生分支寫定，非預設。
            label_source = "mainline_return_N"
        # 延後之鷹架違規在此裁定：覆寫 ⇒ 鷹架被丟棄，只留診斷；未覆寫 ⇒ 鷹架被消費，原樣 raise
        self._settle_deferred_scaffold(scaffold_consumed=(label_source != "event_label_value"), info=info)
        # ── EVTALIGN Task 2.1（D）：驗**實際被消費**的那條（COMPOSER-R1-P0-02：舊碼三個呼叫點
        #    全在覆寫之前，覆寫後無再驗）。契約由 label_source 導出（§C-7 綁產生者；缺席 raise），
        #    分派依「資料是什麼」非依 mode（§C-6 判準），三種模式同一條路徑。
        #    forward_return 路徑不寫任何新報告鍵——§G-1 golden 逐位元組不變。
        label_kind = derive_label_kind(label_source)
        consumed = validate_consumed_label(
            filtered_features,
            filtered_label,
            label_kind=label_kind,
            expected_values=event_label_values,
            event_owners=event_label_owners,
            source_series=normalized_label,
        )
        if label_kind == LABEL_KIND_EVENT_GIVEN:
            info["label_kind"] = label_kind
            info["consumed_event_count"] = int(consumed["checked_samples"])
            # {event_id: label_value}——只有 producer 傳 owners 時才綁得出；service 端再對自己的
            # 逐事件 label 來源逐筆比對（三元組 (event_id, timestamp, label_value) 之最後一腿）。
            info["consumed_event_labels"] = dict(consumed["consumed_event_labels"])
        # ── EVTLABEL Task 3.4：effective mode 決策 ＋ 0/1 綁定與驗證 ────────────
        info = self._resolve_label_mode_and_bind_binary(
            info,
            filtered_features=filtered_features,
            event_binary_labels=event_binary_labels,
            label_mode_requested=label_mode_requested,
            label_mode_hint=label_mode_hint,
            split_context=split_context,
            event_label_owners=event_label_owners,
            config=config,
            label_source=label_source,
        )
        return filtered_features, filtered_label, info

    def _set_ic_cache(self, key: str, value: Any) -> None:
        """寫 `_ic_cache`；尚未建立時**先建**（stage3 可能在 analyze 之外被單獨呼叫／測試）。

        🔴 不用 `self._ic_cache[key] = value` 直寫：`_ic_cache` 預設是 `None`
        （`__init__`），直寫會 TypeError；而更糟的是——若改成 `if isinstance(dict)` 就靜默略過，
        驗過的 0/1 就會**無聲消失**，stage5 拿不到卻沒有任何訊號。建立而非略過。
        """
        if not isinstance(self._ic_cache, dict):
            self._ic_cache = {}
        self._ic_cache[key] = value

    def _resolve_label_mode_and_bind_binary(
        self,
        info: dict,
        *,
        filtered_features: pd.DataFrame,
        event_binary_labels: Optional[dict],
        label_mode_requested: str,
        label_mode_hint: Optional[str],
        split_context: Optional[dict],
        event_label_owners: Optional[dict],
        config: ICConfig,
        label_source: str,
    ) -> dict:
        """EVTLABEL Task 3.4：決定 `label_mode_effective`，並在 imported_binary 下綁定 0/1 向量。

        🔴 **決策點只有這裡**（R1 C2）。route 與 service 一律只透傳 `requested`——
        「能不能用 0/1」取決於**切分後驗證段**每類還剩幾個，那是切分之後才知道的事；
        在更早的地方判就得重建一份切分，那正是 B3 review 打掉的東西。

        🔴 **selection scope**（R1 C2）：計數的分母是**驗證段**（`split_context["test_mask"]`），
        不是整批。整批 136 正 / 29 反看起來很夠，但驗證段可能只剩 2 個反例——
        統計是在驗證段上做的，分母就必須是驗證段。無切分（fallback）⇒ 退回全樣本。

        明示 `imported_binary` 遇任何不足 ⇒ raise（non-retryable）；`auto` ⇒ 退回報酬版並記 reason。
        """
        requested = str(label_mode_requested or "auto")
        info = dict(info)
        # 事件不足已棄條件 IC ⇒ 0/1 更不可能可用；標 unavailable 而非假裝可用。
        abandoned = bool(info.get("conditional_ic_abandoned")) or label_source != "event_label_value"

        n_pos_batch = int(sum(1 for v in (event_binary_labels or {}).values() if int(v) == 1))
        n_neg_batch = int(sum(1 for v in (event_binary_labels or {}).values() if int(v) == 0))

        if split_context is not None and split_context.get("test_mask") is not None:
            sel_idx = filtered_features.index[np.asarray(split_context["test_mask"], dtype=bool)]
            selection_scope = "test"
        else:
            sel_idx = filtered_features.index
            selection_scope = "full_sample"
        sel_counts = _count_binary_classes_in_rows(
            event_binary_labels, sel_idx, np.arange(len(sel_idx), dtype=int)
        ) or {"n_pos": 0, "n_neg": 0}

        floor = int(config.event_filter.min_events_per_class)
        reason: Optional[str] = None
        if abandoned:
            effective, reason = "return_rule", "conditional_ic_abandoned"
        elif requested == "return_rule":
            effective = "return_rule"
        elif event_binary_labels is None:
            effective, reason = "return_rule", (label_mode_hint or "no_label_column")
        elif min(sel_counts["n_pos"], sel_counts["n_neg"]) == 0:
            effective, reason = "return_rule", "one_class"
        elif min(sel_counts["n_pos"], sel_counts["n_neg"]) < floor:
            effective, reason = "return_rule", "class_below_min_selection"
        else:
            effective = "imported_binary"

        if requested == "imported_binary" and effective != "imported_binary":
            raise ValueError(
                f"{reason}: 明示 imported_binary 模式無法套用（驗證段正例 {sel_counts['n_pos']}／"
                f"反例 {sel_counts['n_neg']}，每類最少 {floor}；scope={selection_scope}）"
                "——不接受靜默降級（改用 auto 會退回報酬版並在報告寫明原因）"
            )

        info["label_mode"] = {
            "requested": requested,
            "effective": effective,
            "reason": reason,
            "n_pos_batch": n_pos_batch,
            "n_neg_batch": n_neg_batch,
            "n_pos_selection": int(sel_counts["n_pos"]),
            "n_neg_selection": int(sel_counts["n_neg"]),
            "selection_scope": selection_scope,
        }
        if abandoned and label_source == "event_label_value":
            info["statistic_kind"] = "binary_discrimination_unavailable"
        if effective != "imported_binary":
            self._set_ic_cache("event_binary_label", None)
            return info

        # ── 綁定：0/1 向量必須過與報酬 label **同一條**契約，再封成 immutable ──
        idx_ms = (filtered_features.index.asi8 // 10**6).astype("int64")
        missing = [int(t) for t in idx_ms if int(t) not in event_binary_labels]
        if missing:
            raise AlignmentViolationError(
                f"event_binary_labels missing for {len(missing)} selected timestamps (first={missing[:3]})"
            )
        bseries = pd.Series(
            [float(event_binary_labels[int(t)]) for t in idx_ms],
            index=filtered_features.index, name="imported_binary_label",
        )
        bres = validate_consumed_label(
            filtered_features, bseries,
            label_kind=derive_label_kind("imported_binary_label"),
            expected_values={int(k): float(v) for k, v in event_binary_labels.items()},
            event_owners=event_label_owners,
        )
        rows = frozenset(
            (str(eid), int(ts), int(val)) for eid, (ts, val) in bres["consumed_event_rows"].items()
        )
        digest = binary_label_digest(rows)
        frozen = bseries.copy()
        # 🔴 之後任何 `iloc[...] = ` 會 ValueError ⇒ stage5 不可能就地改掉被驗過的那一份。
        frozen.to_numpy().flags.writeable = False
        self._set_ic_cache("event_binary_label", ValidatedBinaryLabel(
            series=frozen, digest=digest, rows_frozenset=rows,
            n_pos=int((bseries == 1.0).sum()), n_neg=int((bseries == 0.0).sum()),
        ))
        info["label_source"] = "imported_binary_label"
        info["statistic_kind"] = "binary_discrimination"
        info["secondary_statistic"] = "conditional_ic"
        info["binary_label_digest"] = digest
        info["consumed_event_binary_rows"] = {
            str(eid): (int(ts), int(val)) for eid, (ts, val) in bres["consumed_event_rows"].items()
        }
        return info

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

    @_timed_stage("stage4_ic_calculation")
    def _stage4_ic_calculation(
        self,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
        split_context: Optional[dict] = None,
        event_info: Optional[dict] = None,
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

        # EVTWARMUP Task 1.1：事件條件 IC（產生者標記 label_source=event_label_value）不以 bar-rolling warmup 擋
        if split_context is not None and not is_event_label_consumed(event_info):
            min_required = self._rolling_warmup_min_rows(config, int(split_context.get("effective_horizon", 0)))
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

        # UAT 2026-09-08：stage4 各子計算之間設回報點（進度可見＋協作式取消點）；39k 特徵時每段仍是分鐘級。
        self._stage4_checkpoint("ic", 1)
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
        self._stage4_checkpoint("rolling_ic", 2)
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
        self._stage4_checkpoint("icir_autocorr", 3)
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
                self._stage4_checkpoint("ic_decay", 4)
                ic_decay = self._ic_engine.compute_ic_decay(
                    features_for_ic,
                    close,
                    ic_decay_horizons,
                    method,
                    config.labels.return_type,
                )

        if raw_data_for_ic is not None and config.report.include_regime_analysis:
            self._stage4_checkpoint("grouped_ic", 5)
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

    @_timed_stage("stage5_statistical_validation")
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
            point_ic=ic_results.get("ic_values") or {},
        )

        # ── EVTLABEL Task 3.6：匯入標籤模式之主統計進表 ────────────────────────
        binary_mode = self._merge_binary_statistics(
            summary_table, features_for_stats, event_info, config,
            alpha_effective=alpha_effective, fdr_method=fdr_method,
        )

        passed_features, threshold_log = self._apply_thresholds(
            summary_table,
            config.thresholds,
            alpha_effective,
            fdr_enabled=fdr_enabled,
            # EVTWARMUP Task 2.1：事件路徑 ICIR 為診斷欄，不作硬門檻（全域 icir_gate=True 一字不改）
            icir_gate=not is_event_label_consumed(event_info),
            binary_mode=binary_mode,
        )
        if binary_mode:
            passed_features, self._binary_oracle_receipt = self._run_binary_permutation_and_negative_control(
                passed_features, threshold_log["removed_features"], features_for_stats,
                config, alpha_effective=alpha_effective, fdr_method=fdr_method,
            )
            threshold_log["output_features"] = len(passed_features)
            # 排序：主統計為 |rank_biserial|（NaN 置底）；名稱作 tiebreak 以求可重現。
            summary_table.sort(
                key=lambda row: (
                    -abs(row["rank_biserial"]) if np.isfinite(row.get("rank_biserial", np.nan)) else np.inf,
                    str(row.get("feature_name", "")),
                )
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

    @_timed_stage("stage6_redundancy")
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

    @_timed_stage("stage7_report")
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
        point_ic: Optional[dict] = None,
    ) -> list[dict]:
        """summary_table 組裝。

        🔴 UAT 2026-09-09（事件 run 165 事件、1h 視窗 252/756/1512 > 事件數）：rolling 序列全空 ⇒ `icir_item.ic_mean` 全 NaN
        ⇒ `_apply_thresholds` 之 `ic_mean_min` 把 **5909 個特徵全部砍光**（EVTWARMUP 只豁免了 ICIR，漏了 ic_mean）。
        修法：rolling 均值缺席時，`ic_mean` 回退為同一 stage4 之 pooled point IC（`ic_results["ic_values"]`，即 HAC t/p 所檢定的統計量），
        並於 `self._ic_mean_source` 計數供 metadata 揭露；rolling 有值時行為不變（全域 golden 逐位元組不動）。
        """
        table: list[dict] = []
        point_ic = point_ic or {}
        source_counts = {"rolling_mean": 0, "pooled_point_ic": 0, "unavailable": 0}
        for feature in feature_names:
            icir_item = icir.get(feature, {})
            ic_mean_val = icir_item.get("ic_mean")
            if isinstance(ic_mean_val, (int, float)) and not isinstance(ic_mean_val, bool) and np.isfinite(ic_mean_val):
                source_counts["rolling_mean"] += 1
            else:
                fallback = point_ic.get(feature)
                if isinstance(fallback, (int, float)) and not isinstance(fallback, bool) and np.isfinite(fallback):
                    ic_mean_val = float(fallback)
                    source_counts["pooled_point_ic"] += 1
                else:
                    source_counts["unavailable"] += 1
            stats_item = ic_stats.get(feature, {})
            quantile_item = quantile_results.get(feature, {})
            coverage_item = coverage_results.get(feature, {})
            turnover_item = turnover_results.get(feature, {})
            decay_item = ic_decay.get(feature, {})

            table.append(
                {
                    "feature_name": feature,
                    "ic_mean": ic_mean_val,
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
        self._ic_mean_source = source_counts  # 不放 _ic_cache（部分路徑為 None）
        return table

    def _run_binary_permutation_and_negative_control(
        self,
        passed: list,
        removed: dict,
        features_for_stats: "pd.DataFrame",
        config: ICConfig,
        *,
        alpha_effective: float,
        fdr_method: str,
    ) -> tuple:
        """EVTLABEL Task 3.7：倖存者逐一區塊置換重驗 ＋ 整批負對照。回 `(passed, receipt)`。

        兩道是**不同層級**的問題：

        (C) **逐特徵**：這個特徵的分辨力，會不會只是因為事件彼此重疊而看起來很強？
            把標籤以區塊為單位洗掉再算一次；觀測值落在置換帶內（跟隨機沒兩樣）⇒ 移出倖存者。
            這是特徵級 fail-closed。

        (B) **整批**：把標籤整批洗掉、重跑一次完整篩選，看**還能篩出幾個**。
            如果隨機也能篩出跟實測差不多的數量，那整批結果就與雜訊無法區分 ⇒
            倖存者標 suppressed（診斷表仍保留，但不當可消費的結論交出去）。

        🔴 `n_observed == 0` ⇒ **不跑負對照**（沒有倖存者就沒有「是不是雜訊」的問題），
        status 記 `skipped:no_survivors`——與「跑了而且失敗」是兩件事，不得混為同一個紅燈。
        """
        vb = (self._ic_cache or {}).get("event_binary_label")
        if vb is None:
            return passed, None
        sel_ms = (pd.Index(features_for_stats.index).asi8 // 10**6).astype("int64")
        bar_ms = self._binary_feature_bar_ms(sel_ms)
        window_bars = int(getattr(self, "_binary_label_window_bars", 0) or 0)
        block_ids, block_len, n_blocks = block_ids_for_events(sel_ms, window_bars, bar_ms)
        y = vb.series.reindex(features_for_stats.index).to_numpy(dtype="int64")

        cfg_ev = config.event_filter
        k = max(1, len(passed))
        n_perm = min(1000, max(200, int(cfg_ev.perm_budget_total) // k))
        budget_floor_hit = bool(int(cfg_ev.perm_budget_total) < 200 * len(passed))

        receipt = {
            "seed": int(cfg_ev.oracle_seed), "n_perm": int(n_perm),
            "block_len": int(block_len), "n_blocks": int(n_blocks),
            "budget_floor_hit": budget_floor_hit, "first_permutation_digest": None,
        }
        removed.setdefault("permutation_oracle_disagree", [])
        removed.setdefault("permutation_unavailable", [])

        survivors: list = []
        for name in list(passed):
            values = features_for_stats[name].to_numpy(dtype="float64")
            out = block_permutation_oracle(
                values, y, block_ids, rank_biserial_stat,
                seed=int(cfg_ev.oracle_seed), n_perm=int(n_perm),
            )
            if out.get("status") != BINARY_STATUS_OK:
                removed["permutation_unavailable"].append(name)
                continue
            if receipt["first_permutation_digest"] is None:
                receipt["first_permutation_digest"] = out["receipt"]["first_permutation_digest"]
            if out.get("in_band"):
                removed["permutation_oracle_disagree"].append(name)
                continue
            survivors.append(name)

        n_observed = len(survivors)
        if n_observed == 0:
            receipt["negative_control"] = {"status": "skipped:no_survivors"}
            self._survivor_suppressed_reason = None
            return survivors, receipt

        counts: list = []
        for i in range(int(cfg_ev.negative_control_n)):
            rng = np.random.default_rng(int(cfg_ev.oracle_seed) + i)
            y_sh = _permute_blocks(rng, y, block_ids)
            tbl_sh = mann_whitney_table(
                features_for_stats, y_sh, min_class_n=int(cfg_ev.min_events_per_class)
            )
            q_sh, _ = apply_fdr(
                {n: float(tbl_sh.loc[n, "p_value"]) for n in tbl_sh.index},
                alpha_effective, method=fdr_method,
            )
            hits = 0
            for n in tbl_sh.index:
                rb = float(tbl_sh.loc[n, "rank_biserial"])
                q = float(q_sh.get(n, np.nan))
                if (
                    str(tbl_sh.loc[n, "status"]) == BINARY_STATUS_OK
                    and np.isfinite(rb) and np.isfinite(q)
                    and q <= alpha_effective
                    and abs(rb) >= float(config.thresholds.rank_biserial_min)
                ):
                    hits += 1
            counts.append(int(hits))

        # 整數 order statistic（`method="higher"`），**禁插值**：計數是離散的，
        # 插出來的 12.4 不對應任何一次實驗。
        q95 = int(np.quantile(counts, 0.95, method="higher")) if counts else 0
        receipt["negative_control"] = {
            "n_observed": int(n_observed), "shuffled_counts": counts,
            "q95": int(q95), "seed_base": int(cfg_ev.oracle_seed), "block_len": int(block_len),
        }
        if n_observed <= q95:
            # 隨機也能篩出這麼多 ⇒ 與雜訊無法區分。診斷表保留，但不當結論交出去。
            self._survivor_suppressed_reason = "negative_control_failed"
        else:
            self._survivor_suppressed_reason = None
        return survivors, receipt

    @staticmethod
    def _binary_feature_bar_ms(sel_ms: "np.ndarray") -> int:
        """由被選中列之時間戳推特徵 K 線長度（毫秒）：取相鄰間距之**最小正值**。

        事件是稀疏的，所以間距是「幾根」的整數倍；最小正間距即一根。只有一列 ⇒ 回 1。
        """
        arr = np.asarray(sorted(int(v) for v in np.asarray(sel_ms).tolist()), dtype="int64")
        if len(arr) < 2:
            return 1
        gaps = np.diff(arr)
        gaps = gaps[gaps > 0]
        return int(np.min(gaps)) if len(gaps) else 1

    def _merge_binary_statistics(
        self,
        summary_table: list[dict],
        features_for_stats: pd.DataFrame,
        event_info: dict,
        config: ICConfig,
        *,
        alpha_effective: float,
        fdr_method: str,
    ) -> bool:
        """EVTLABEL Task 3.6：把 0/1 分辨力統計併進 summary_table；回傳「本次是否 binary 模式」。

        🔴 **消費前三守衛**（R2 D1；**刻意沒有** digest 相等比對）：
        ① `X.index` 與 selection index 逐值相等 ② `len(y) == len(X)`
        ③ 每一個 `(event_id, ts_ms, 0/1)` 都在 stage3 驗過的 `rows_frozenset` 裡。
        任一不成立 ⇒ raise。為什麼不用 digest 相等：digest 只能說「整份一樣或不一樣」，
        說不出**是哪幾列**被換掉；子集檢查會直接指出那一列。

        🔴 對證之後**直接**把 `X, y` 餵進 `mann_whitney_table`，中間不得重排、不得 `.iloc[perm]`
        ——中間任何重排都會讓「驗過的」與「用掉的」再度分家。
        """
        if str((event_info or {}).get("label_source")) != "imported_binary_label":
            return False
        vb = (self._ic_cache or {}).get("event_binary_label")
        if vb is None:
            raise AlignmentViolationError(
                "label_source=imported_binary_label 但 stage3 沒有交付 ValidatedBinaryLabel"
            )

        sel_idx = features_for_stats.index
        # ① index 對齊
        if not vb.series.index.equals(pd.Index(features_for_stats.index)):
            y_series = vb.series.reindex(sel_idx)
            if y_series.isna().any():
                raise AlignmentViolationError(
                    "binary label consumed != validated: selection 有列不在驗過的 0/1 向量裡"
                )
        else:
            y_series = vb.series
        y = y_series.to_numpy(dtype="int64")
        # ② 長度
        if len(y) != len(features_for_stats):
            raise AlignmentViolationError(
                f"binary label consumed != validated: 長度 {len(y)} != {len(features_for_stats)}"
            )
        # ③ 逐列在驗過的三元組集合內
        owners = {str(eid): (int(ts), int(val)) for eid, (ts, val) in
                  ((e, (t, v)) for e, t, v in vb.rows_frozenset)}
        by_row = {(int(ts), int(val)) for _, ts, val in vb.rows_frozenset}
        sel_ms = (pd.Index(sel_idx).asi8 // 10**6).astype("int64")
        for ts, y_i in zip(sel_ms, y):
            if (int(ts), int(y_i)) not in by_row:
                raise AlignmentViolationError(
                    f"binary label consumed != validated: 列 {int(ts)} 之值 {int(y_i)} 不在驗過的集合內"
                )
        assert owners is not None  # 保留 owners 供未來逐 event 診斷；不參與判定

        tbl = mann_whitney_table(
            features_for_stats, y, min_class_n=int(config.event_filter.min_events_per_class)
        )
        q_values, _ = apply_fdr(
            {name: float(tbl.loc[name, "p_value"]) for name in tbl.index},
            alpha_effective, method=fdr_method,
        )
        for row in summary_table:
            name = str(row.get("feature_name", ""))
            if name not in tbl.index:
                continue
            rec = tbl.loc[name]
            row["auc"] = float(rec["auc"])
            row["rank_biserial"] = float(rec["rank_biserial"])
            row["mw_u"] = float(rec["mw_u"])
            row["mw_p_value"] = float(rec["p_value"])
            row["mw_p_value_adj"] = float(q_values.get(name, np.nan))
            row["n_pos"] = int(rec["n_pos"])
            row["n_neg"] = int(rec["n_neg"])
            row["n_used_binary"] = int(rec["n_used"])
            row["binary_status"] = str(rec["status"])
        return True

    def _apply_thresholds(
        self,
        summary_table: list[dict],
        thresholds: Any,
        alpha_effective: float,
        *,
        fdr_enabled: bool = True,
        icir_gate: bool = True,
        binary_mode: bool = False,
    ) -> tuple[list[str], dict]:
        """門檻過濾；p 閘消費 p_value_adj（FDR on）或 p_value（FDR off）。

        `icir_gate=False`（EVTWARMUP Task 2.1，事件條件 IC 路徑）：ICIR 不作剔除門檻，只記錄到
        `removed["icir_skipped_event_path"]`（診斷）；全域路徑預設 True，行為不變。
        """
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
        if not icir_gate:
            removed["icir_skipped_event_path"] = []   # 事件路徑必有此鍵（診斷欄；即使無人走到 ICIR 檢查）

        if binary_mode:
            # 🔴 EVTLABEL Task 3.6：匯入標籤模式之門檻**與報酬版分開**。
            #    報酬版那幾道（ic_mean／icir／ic_hit_rate／monotonicity／coverage／long_short_spread）
            #    在這裡不適用 ⇒ 一律記錄到 `*_skipped_binary_mode` 而**不剔除**
            #    （報酬版 IC 仍算、留第二欄供對照）。
            for gate in ("ic_mean", "icir", "ic_hit_rate", "monotonicity", "coverage", "long_short_spread"):
                removed[f"{gate}_skipped_binary_mode"] = []
            removed["rank_biserial"] = []
            removed["binary_unavailable"] = []

        for row in summary_table:
            name = row.get("feature_name")
            if name is None:
                continue

            if binary_mode:
                if str(row.get("binary_status")) != BINARY_STATUS_OK:
                    removed["binary_unavailable"].append(name)
                    continue
                for gate in ("ic_mean", "icir", "ic_hit_rate", "monotonicity", "coverage", "long_short_spread"):
                    removed[f"{gate}_skipped_binary_mode"].append(name)
                # 🔴 效應量閘取**絕對值**且用**獨立門檻**（R1 C1 推翻共用 ic_mean_min）：
                #    rank-biserial 為負代表「反向但一樣能分」，不取絕對值會把強反向特徵誤殺。
                rb = row.get("rank_biserial")
                if not (isinstance(rb, (int, float)) and np.isfinite(rb)
                        and abs(row["rank_biserial"]) >= thresholds.rank_biserial_min):
                    removed["rank_biserial"].append(name)
                    continue
                # p 閘讀 **Mann-Whitney 的 q**，不是報酬版的 q。
                p_field = "mw_p_value_adj" if fdr_enabled else "mw_p_value"
                if not self._passes_threshold(row.get(p_field), alpha_effective, inverse=True):
                    removed["p_value"].append(name)
                    continue
                passed.append(name)
                continue

            if not self._passes_threshold(row.get("ic_mean"), thresholds.ic_mean_min):
                removed["ic_mean"].append(name)
                continue
            if not self._passes_threshold(row.get("icir"), thresholds.icir_min):
                if icir_gate:
                    removed["icir"].append(name)
                    continue
                removed.setdefault("icir_skipped_event_path", []).append(name)  # 記錄、不剔除
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

    @_timed_stage("stage6b_marginal_ic")
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
        self, stage: int, stage_name: str, progress: float, message: str,
        extra: Optional[dict] = None,
    ) -> None:
        # fallback 等路徑可能在未經 analyze() 設定 callback 前被直接呼叫（測試亦如此）⇒ 缺屬性視同 None
        if getattr(self, "_progress_callback", None) is None:
            return
        payload = {
            "stage": stage,
            "stage_name": stage_name,
            "progress": progress,
            "message": message,
        }
        if extra:
            payload.update(extra)
        try:
            self._progress_callback(payload)
        except AnalysisCancelled:
            # 呼叫端（service）要求協作式中止（例：伺服器已關閉）——**不吞**，讓分析在此回報點停下
            raise
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

            # 🔴 TIERTOGGLE（使用者 2026-09-10 裁定；票 TIERTOGGLE）：具名 preset 分支
            #    **全量**消費 `stage_overrides`，與 custom 分支同一迴圈語意。
            #    舊版只逐鍵映射 `fdr_correction`／`marginal_ic` 兩把鑰匙 ⇒ UI「基礎」preset 之
            #    `ic_decay:false`／`grouped_ic:false`／`turnover_analysis`／`event_filtering`
            #    在後端**被靜默丟掉**、照原 config 預設（True）跑＝幽靈開關（畫面關了、後端沒關）。
            #    實機證據：2026-09-09 事件 run 選「基礎」仍產出 `ic_decay`（5,909 特徵×7 horizon）
            #    與 `grouped_ic`，且 decay 逐 horizon 各算一次是該 run 跑不完的主要成本之一。
            #    前後端鍵集之機械對證見 `momentum/Analysis/contracts/ui_stage_toggles.json`
            #    （pytest `tests/momentum/test_tier_toggle_sync.py` ＋ vitest `icAnalysisStore.toggles.test.ts`）。
            stage_overrides = custom.get("stage_overrides") or {}
            for key, enabled in stage_overrides.items():
                if key in LOCKED_STAGE_KEYS:
                    continue
                path = STAGE_OVERRIDE_PATHS.get(key)
                if path is None:
                    continue
                _set_nested_bool(data, path, bool(enabled))
            # 缺 `fdr_correction` ⇒ 強制 ON（UI 三 preset 皆 true；非 UI 客戶端沿舊行為，不得因本次改動變 OFF）
            if "fdr_correction" not in stage_overrides:
                _set_nested_bool(data, STAGE_OVERRIDE_PATHS["fdr_correction"], True)

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
