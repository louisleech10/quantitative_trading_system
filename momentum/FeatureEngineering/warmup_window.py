"""B6 warmup-then-trim：OutputWindow 解析與 max_warmup 估算。

選項 1：載入 [ingest_start, end] 因果計算，公開輸出 trim 到 [output_start, end]。
flag ``FFACT_WARMUP_TRIM`` 預設關閉（= B5 strict-window）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.atomic.warmup_lookup import (
    get_max_warmup_bars,
    get_pattern_default_bars,
)
from momentum.FeatureEngineering.preprocessing._native_tf_helpers import scale_window_for_native

if TYPE_CHECKING:
    from momentum.FeatureEngineering.feature_config import FactoryConfig

# L5 beta 預設 rolling window（relative_strength.py）
_BETA_ROLLING_WINDOW = 60
# validator winsor fallback（feature_validator.py L6.5 winsor off 時）
_VALIDATOR_WINSOR_FALLBACK = 252
# L6 volatility_regime 隱含 ATR 長窗
_L6_META_ATR_LONG_WINDOW = 55


@dataclass(frozen=True)
class OutputWindow:
    """單次 generate 的載入與輸出視窗。"""

    ingest_start: Optional[str]
    output_start: Optional[str]
    output_end: Optional[str]
    max_warmup_bars: int
    warmup_enabled: bool

    @property
    def ingest_start_ts(self) -> Optional[pd.Timestamp]:
        if self.ingest_start is None:
            return None
        return pd.Timestamp(self.ingest_start)

    @property
    def output_start_ts(self) -> Optional[pd.Timestamp]:
        if self.output_start is None:
            return None
        return pd.Timestamp(self.output_start)

    @property
    def output_end_ts(self) -> Optional[pd.Timestamp]:
        if self.output_end is None:
            return None
        return pd.Timestamp(self.output_end)


@dataclass(frozen=True)
class WarmupInsufficient:
    """warmup 不足 metadata（凍結欄位）。"""

    needed: int
    available: int
    affected_bars: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "needed": int(self.needed),
            "available": int(self.available),
            "affected_bars": int(self.affected_bars),
        }


def is_warmup_trim_enabled() -> bool:
    """``FFACT_WARMUP_TRIM`` 環境變數；預設 ``0`` = strict-window (B5)。"""
    raw = os.getenv("FFACT_WARMUP_TRIM", "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _max_positive(*values: int) -> int:
    positives = [int(v) for v in values if v and int(v) > 0]
    return max(positives) if positives else 0


def _max_from_lists(*lists: Sequence[int]) -> int:
    values: List[int] = []
    for seq in lists:
        if not seq:
            continue
        values.extend(int(v) for v in seq if v and int(v) > 0)
    return max(values) if values else 0


def _resolve_indicator_max_period(indicator: Mapping[str, Any]) -> int:
    """從單一 indicator config 條目解析最大 lookback period。"""
    combos = indicator.get("combos")
    if isinstance(combos, list) and combos:
        max_p = 0
        for combo in combos:
            if not isinstance(combo, dict):
                continue
            for key in (
                "timeperiod",
                "slowperiod",
                "fastperiod",
                "signalperiod",
                "fastk_period",
                "slowk_period",
                "slowd_period",
                "fastd_period",
            ):
                val = combo.get(key)
                if val is not None:
                    max_p = max(max_p, int(val))
        return max_p if max_p > 0 else 26

    ema_periods = indicator.get("ema_periods")
    if isinstance(ema_periods, list) and ema_periods:
        return max(int(p) for p in ema_periods)

    periods = indicator.get("periods")
    period_range = indicator.get("period_range")
    industry_standard = indicator.get("industry_standard")
    range_min, range_max = 5, 233
    if isinstance(period_range, list) and len(period_range) >= 2:
        range_min = int(period_range[0])
        range_max = int(period_range[1])

    if isinstance(periods, str):
        values = ParameterGenerator.generate(
            periods,
            range_min=range_min,
            range_max=range_max,
            industry_standard=industry_standard if isinstance(industry_standard, list) else None,
        )
        return max(values) if values else range_max
    if isinstance(periods, list):
        merged = {int(p) for p in periods}
        if isinstance(industry_standard, list):
            merged.update(int(p) for p in industry_standard)
        return max(merged) if merged else 1
    return 1


def _collect_l1_warmup_bars(config: "FactoryConfig") -> int:
    """L1：get_max_warmup_bars + CDL pattern + advanced atomic 獨立窗。"""
    indicator_periods: Dict[str, int] = {}
    ai = config.atomic_indicators
    category_models = [
        ai.trend,
        ai.momentum,
        ai.volatility,
        ai.volume,
        ai.cycle,
        ai.statistics,
    ]

    for cat in category_models:
        if not cat.enabled:
            continue
        for ind in cat.indicators:
            if not ind.enabled:
                continue
            name = str(ind.name).upper()
            period = _resolve_indicator_max_period(ind.model_dump())
            indicator_periods[name] = max(indicator_periods.get(name, 0), period)

    l1_talib = get_max_warmup_bars(indicator_periods) if indicator_periods else 0

    pattern_bars = 0
    if ai.pattern.enabled:
        pattern_bars = get_pattern_default_bars()

    advanced_windows: List[int] = []
    if ai.microstructure.enabled:
        ms = ai.microstructure
        advanced_windows.extend(ms.windows)
        advanced_windows.extend(ms.cs_spread_smooth)
        advanced_windows.extend(ms.kyle_lambda_windows)
        advanced_windows.extend(ms.vpin_zscore_windows)
        advanced_windows.extend(ms.vpin_n_buckets)
    if ai.entropy.enabled:
        ent = ai.entropy
        advanced_windows.extend(ent.windows)
        advanced_windows.extend(ent.hurst_windows)
        advanced_windows.extend(ent.perm_windows)
        advanced_windows.extend(ent.shannon_windows)
        advanced_windows.append(ent.perm_m)
        advanced_windows.append(ent.apen_m)
        advanced_windows.append(ent.fractal_kmax)
    if ai.tail_risk.enabled:
        tr = ai.tail_risk
        advanced_windows.extend(tr.windows)
        advanced_windows.extend(tr.rv_windows)
        advanced_windows.extend(tr.mdd_windows)

    return _max_positive(l1_talib, pattern_bars, _max_from_lists(advanced_windows))


def _collect_l2_warmup_bars(config: "FactoryConfig") -> int:
    """L2：momentum lags、WQ windows、decay_linear。"""
    if not config.operators.enabled:
        return 0
    ops = config.operators.model_dump(by_alias=True)
    max_val = 0

    momentum_cfg = ops.get("momentum", {}) or ops.get("momentum_change", {})
    if momentum_cfg.get("enabled", False):
        lags = momentum_cfg.get("lags", [3, 5, 8])
        if isinstance(lags, list):
            max_val = max(max_val, _max_from_lists(lags))

    wq = ops.get("worldquant", {})
    if wq.get("enabled", False):
        windows = wq.get("windows", [5, 13, 21])
        if isinstance(windows, list):
            max_val = max(max_val, _max_from_lists(windows))

    return max_val


def _collect_l3_warmup_bars(config: "FactoryConfig") -> int:
    if not config.rolling_aggregation.enabled:
        return 0
    return _max_from_lists(config.rolling_aggregation.windows)


def _collect_l4_warmup_bars(config: "FactoryConfig") -> int:
    if not config.lag_features.enabled:
        return 0
    gs = config.global_settings
    lags = ParameterGenerator.generate_lag_sequence(
        gs.sequence_length,
        gs.max_lag_ratio,
        strategy=gs.lag_strategy,
        custom_lags=gs.custom_lags,
    )
    return max(lags) if lags else 0


def _collect_l5_warmup_bars(config: "FactoryConfig") -> int:
    """L5 cross-sectional：compute_beta rolling + reference symbol 同 warmup。"""
    if not config.cross_sectional.enabled:
        return 0
    features = config.cross_sectional.features
    needs_beta = False
    for name in ("beta", "idiosyncratic_momentum"):
        feat = features.get(name)
        if feat is not None and feat.enabled:
            needs_beta = True
            break
    if not needs_beta:
        return 0
    return _BETA_ROLLING_WINDOW


def _collect_l6_warmup_bars(config: "FactoryConfig") -> int:
    """L6 meta 顯式 rolling 窗（volatility_regime ATR 比值）。"""
    if not config.meta_features.enabled:
        return 0
    if config.meta_features.volatility_regime:
        return _L6_META_ATR_LONG_WINDOW
    return 0


def _collect_l65_warmup_bars(
    config: "FactoryConfig",
    primary_tf: str,
    training_tfs: Sequence[str],
) -> int:
    """L6.5 + native-tf 放大 + validator winsor fallback。"""
    pp = config.preprocessing
    base_windows: List[int] = []

    if pp.enabled:
        if pp.winsorization.enabled:
            base_windows.append(int(pp.winsorization.window))
        else:
            base_windows.append(_VALIDATOR_WINSOR_FALLBACK)
        if pp.rank_transform.enabled:
            base_windows.append(int(pp.rank_transform.window))
        if pp.adaptive_zscore.enabled:
            base_windows.extend(int(w) for w in pp.adaptive_zscore.windows)
        base_windows.append(int(pp.calibration_bars))
        if pp.fractional_differencing.enabled:
            max_lag = int(pp.fractional_differencing.model_dump().get("max_lag", 0) or 0)
            if max_lag <= 0:
                # docs/FRACDIFF_MAXLAG_SPEC.md: value path auto max_lag is
                # calibration-derived; warmup keeps the conservative 252
                # fallback because it only extends preheat, not feature values.
                max_lag = 252
            base_windows.append(max_lag)
        if pp.adf_differencing.enabled:
            base_windows.append(int(pp.adf_differencing.sample_size))

    if not base_windows:
        return 0

    max_primary = max(base_windows)
    max_scaled = max_primary
    for tf in training_tfs:
        if tf == primary_tf:
            continue
        for window in base_windows:
            scaled = scale_window_for_native(int(window), tf, primary_tf)
            max_scaled = max(max_scaled, scaled)
    return max_scaled


def estimate_max_warmup_bars(
    config: "FactoryConfig",
    primary_tf: str,
    training_tfs: Optional[Sequence[str]] = None,
) -> int:
    """primary TF bars：各層 warmup 來源取 max（排除 cumulative/fracdiff d*/ADF order/post-IC/labels）。"""
    tfs = list(training_tfs) if training_tfs else list(config.timeframes.training)
    if primary_tf not in tfs:
        tfs = [primary_tf, *tfs]

    sources = [
        _collect_l1_warmup_bars(config),
        _collect_l2_warmup_bars(config),
        _collect_l3_warmup_bars(config),
        _collect_l4_warmup_bars(config),
        _collect_l5_warmup_bars(config),
        _collect_l6_warmup_bars(config),
        _collect_l65_warmup_bars(config, primary_tf, tfs),
    ]
    return _max_positive(*sources)


def _estimate_ingest_start_iso(
    output_start: str,
    max_warmup_bars: int,
    timeframe: str,
) -> str:
    """以 bar 時長估算 ingest_start（載入前保守下界）。"""
    ts = pd.Timestamp(output_start)
    bar_sec = TIMEFRAME_SECONDS.get(timeframe, TIMEFRAME_SECONDS["12h"])
    buffer = 1.1
    delta = pd.Timedelta(seconds=int(max_warmup_bars * bar_sec * buffer))
    return (ts - delta).isoformat()


def resolve_output_window(
    config: "FactoryConfig",
    timeframe: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> OutputWindow:
    """generate 入口算一次 OutputWindow。"""
    if not is_warmup_trim_enabled() or start_date is None:
        return OutputWindow(
            ingest_start=start_date,
            output_start=start_date,
            output_end=end_date,
            max_warmup_bars=0,
            warmup_enabled=False,
        )

    primary_tf = config.timeframes.primary if timeframe in config.timeframes.training else timeframe
    training_tfs = list(dict.fromkeys(config.timeframes.training))
    max_warmup = estimate_max_warmup_bars(config, primary_tf, training_tfs)
    ingest_start = _estimate_ingest_start_iso(start_date, max_warmup, primary_tf)

    return OutputWindow(
        ingest_start=ingest_start,
        output_start=start_date,
        output_end=end_date,
        max_warmup_bars=max_warmup,
        warmup_enabled=True,
    )


def coerce_index_to_datetime(index: pd.Index) -> pd.Series:
    """與 FeatureFactory._coerce_index_to_datetime 對齊的 epoch 單位推斷。"""
    if index is None:
        return pd.Series(dtype="datetime64[ns]")

    index_series = pd.Series(index)
    if pd.api.types.is_numeric_dtype(index_series):
        numeric = pd.to_numeric(index_series, errors="coerce")
        max_abs = numeric.abs().max(skipna=True)
        if pd.notna(max_abs):
            if max_abs >= 1_000_000_000_000_000_000:
                unit = "ns"
            elif max_abs >= 1_000_000_000_000_000:
                unit = "us"
            elif max_abs >= 1_000_000_000_000:
                unit = "ms"
            else:
                unit = "s"
            parsed = pd.to_datetime(numeric, unit=unit, errors="coerce")
            fallback = pd.to_datetime(index_series, errors="coerce")
            return parsed.where(parsed.notna(), fallback)
    return pd.to_datetime(index_series, errors="coerce")


def compute_row_bounds(
    index: pd.Index,
    window: OutputWindow,
) -> Tuple[int, int]:
    """回傳 [start_idx, end_idx_exclusive) 對應 output 視窗。"""
    if not window.warmup_enabled or window.output_start is None:
        return 0, len(index)

    dt_index = coerce_index_to_datetime(index)
    start_ts = window.output_start_ts
    end_ts = window.output_end_ts

    mask = dt_index >= start_ts
    if end_ts is not None:
        mask &= dt_index <= end_ts

    if not mask.any():
        return 0, 0

    positions = np.flatnonzero(mask.to_numpy())
    return int(positions[0]), int(positions[-1]) + 1


def compute_warmup_insufficient(
    raw_data: pd.DataFrame,
    window: OutputWindow,
) -> Optional[WarmupInsufficient]:
    """needed vs available（ingest_start 前實得 bar）。"""
    if not window.warmup_enabled or window.output_start is None:
        return None

    needed = int(window.max_warmup_bars)
    if needed <= 0:
        return None

    dt_index = coerce_index_to_datetime(raw_data.index)
    start_ts = window.output_start_ts
    before_mask = dt_index < start_ts
    available = int(before_mask.sum())

    if available >= needed:
        return None

    affected = max(0, needed - available)
    return WarmupInsufficient(needed=needed, available=available, affected_bars=affected)


def build_warmup_metadata(
    config: "FactoryConfig",
    raw_data: pd.DataFrame,
    window: OutputWindow,
) -> Dict[str, Any]:
    """warmup_insufficient、label_tail_nan_bars、cumulative_anchor。"""
    meta: Dict[str, Any] = {}
    if not window.warmup_enabled:
        return meta

    insufficient = compute_warmup_insufficient(raw_data, window)
    if insufficient is not None:
        meta["warmup_insufficient"] = insufficient.to_dict()

    binary_h = config.labels.binary.horizons
    reg_h = config.labels.regression.horizons
    all_h = list(binary_h) + list(reg_h)
    if all_h:
        meta["label_tail_nan_bars"] = int(max(all_h))

    if window.ingest_start is not None:
        meta["cumulative_anchor"] = window.ingest_start

    return meta


def trim_dataframe_to_output_window(
    frame: pd.DataFrame,
    window: OutputWindow,
) -> pd.DataFrame:
    """依 output 視窗裁切 DataFrame（不改值）。"""
    if frame is None or frame.empty or not window.warmup_enabled:
        return frame

    start_idx, end_idx = compute_row_bounds(frame.index, window)
    if start_idx >= end_idx:
        return frame.iloc[0:0]
    return frame.iloc[start_idx:end_idx]


def trim_series_to_output_window(
    series: pd.Series,
    window: OutputWindow,
) -> pd.Series:
    if series is None or series.empty or not window.warmup_enabled:
        return series
    start_idx, end_idx = compute_row_bounds(series.index, window)
    if start_idx >= end_idx:
        return series.iloc[0:0]
    return series.iloc[start_idx:end_idx]


def output_time_range_dict(window: OutputWindow) -> Dict[str, Optional[str]]:
    """manifest / sidecar time_range。"""
    return {
        "start": window.output_start,
        "end": window.output_end,
    }


def output_row_count(index: pd.Index, window: OutputWindow) -> int:
    """公開輸出列數 = |[output_start, output_end]|。"""
    start_idx, end_idx = compute_row_bounds(index, window)
    return max(0, end_idx - start_idx)


def ingest_layer0_start_date(
    window: OutputWindow,
    timeframe: str,
    primary_tf: str,
) -> Optional[str]:
    """各 TF _layer0 載入起點：primary 用 ingest_start；次 TF 用 primary ingest_start 時間跨度。"""
    if not window.warmup_enabled:
        return window.output_start
    return window.ingest_start


def max_ingest_index_before_output_start(
    raw_data: pd.DataFrame,
    window: OutputWindow,
) -> Optional[pd.Timestamp]:
    """因果檢查：max(ingest_index) < output_start。"""
    if not window.warmup_enabled or window.output_start is None:
        return None
    dt_index = coerce_index_to_datetime(raw_data.index)
    start_ts = window.output_start_ts
    before = dt_index[dt_index < start_ts]
    if before.empty:
        return None
    return before.max()


__all__ = [
    "OutputWindow",
    "WarmupInsufficient",
    "build_warmup_metadata",
    "coerce_index_to_datetime",
    "compute_row_bounds",
    "compute_warmup_insufficient",
    "estimate_max_warmup_bars",
    "ingest_layer0_start_date",
    "is_warmup_trim_enabled",
    "max_ingest_index_before_output_start",
    "output_row_count",
    "output_time_range_dict",
    "resolve_output_window",
    "trim_dataframe_to_output_window",
    "trim_series_to_output_window",
]
