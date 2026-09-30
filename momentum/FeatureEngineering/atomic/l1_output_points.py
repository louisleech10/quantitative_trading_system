"""FF-STAT Task 2.3（SPEC v45 §C「L1 遮罩」「L1 輸出點契約」）：L1 輸出點之唯一遮罩入口。

每個 L1 輸出欄於交 L2（或同引擎衍生、跨引擎合併）前經 ``mask_output``：以產生該欄之已解析參數字典與
倍數表之 ``period_keys`` 建 ``OutputPointSpec``，經 ``stable_mask.instance_k`` 取 K（模組屬性呼叫，
測試得以 spy），再以 ``stable_mask.apply_l1_mask`` 將 origin 之前與 ``[origin, origin+K)`` 設 NaN。
遮罩只作用於輸出：指標一律於未遮罩之輸入上計算（v33）。
"""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.atomic import warmup_lookup
from momentum.FeatureEngineering.preprocessing import stable_mask as sm

# TA-Lib K 線形態（CDL＊）共用之倍數表具名條目（SPEC §C v39）
PATTERN_CATEGORY = "pattern"


def table_indicator(indicator: str, category: Optional[str] = None) -> str:
    """輸出點所查之倍數表條目名：CDL＊ ⇒ ``CDL_PATTERN``；其餘為指標名大寫。"""
    if category == PATTERN_CATEGORY or str(indicator).upper().startswith("CDL"):
        return warmup_lookup.PATTERN_ENTRY
    return str(indicator).upper()


def period_keys_for(indicator: str) -> Tuple[str, ...]:
    """倍數表對該條目登記之 ``period_keys``；查無條目回空（由 ``instance_k`` 以缺條目 fail-closed）。"""
    entry = warmup_lookup.warmup_table().get(indicator)
    return tuple(entry.get("period_keys") or ()) if entry else ()


def origin_of(inputs: Sequence[np.ndarray]) -> Optional[int]:
    """L1 遮罩 origin：該指標全部輸入欄皆為有限值之第一列。"""
    columns = [np.asarray(values, dtype=np.float64).reshape(-1) for values in inputs]
    return sm.l1_origin(np.column_stack(columns)) if columns else None


def mask_output(
    engine: str,
    indicator: str,
    column: str,
    values: Any,
    params: Mapping[str, Any],
    *,
    origin: Optional[int],
    upstream: Sequence[str] = (),
    window: Optional[int] = None,
    upstream_k: Optional[Mapping[str, int]] = None,
) -> Tuple[np.ndarray, int]:
    """回傳 (遮罩後之新陣列, K)；契約不成立（缺條目、缺鍵、缺上游 K）⇒ ``StableMaskError``（輸出前 fail-closed）。"""
    spec = sm.OutputPointSpec(
        engine=engine,
        indicator=indicator,
        column=column,
        params=dict(params or {}),
        period_keys=() if upstream else period_keys_for(indicator),
        upstream=tuple(upstream),
        window=window,
    )
    k = sm.instance_k(spec, warmup_lookup.warmup_table(), upstream_k)
    return sm.apply_l1_mask(np.asarray(values, dtype=np.float64), origin, k), k


def mask_frame(
    frame: Optional[pd.DataFrame],
    engine: str,
    indicator: str,
    params: Mapping[str, Any],
    data: pd.DataFrame,
    input_columns: Sequence[str],
) -> Optional[pd.DataFrame]:
    """自訂 L1 輸出點：``frame`` 之每欄皆由同一次計算（``params``、輸入欄 ``input_columns``）產生 ⇒ 逐欄遮罩。

    空 frame（輸入欄不齊時引擎回空）原樣回傳。"""
    if frame is None or frame.empty:
        return frame
    origin = origin_of([data[c].to_numpy(dtype=np.float64) for c in input_columns])
    masked = {
        column: mask_output(engine, indicator, str(column), frame[column].to_numpy(), params, origin=origin)[0]
        for column in frame.columns
    }
    return pd.DataFrame(masked, index=frame.index)


def point(indicator: str, params: Mapping[str, Any], inputs: Sequence[str],
          upstream: Sequence[str] = (), window: Optional[int] = None) -> Dict[str, Any]:
    """進階 atomic 引擎之單欄輸出點契約（倍數表條目、已解析參數、輸入欄、同引擎上游與窗長）。"""
    return {"indicator": indicator, "params": dict(params), "inputs": tuple(inputs),
            "upstream": tuple(upstream), "window": window}


def mask_engine_frame(engine: str, frame: pd.DataFrame, points: Mapping[str, Mapping[str, Any]],
                      data: pd.DataFrame) -> pd.DataFrame:
    """進階 atomic 引擎（microstructure、entropy、tail_risk）之 L1 輸出點：``frame`` 每欄須有 ``points`` 契約，
    缺者輸出前 fail-closed（SPEC §C v38：不得以欄名推週期）。衍生欄之上游 K 取本次已算出之上游 K。"""
    if frame is None or frame.empty:
        return frame
    lacking = [str(c) for c in frame.columns if c not in points]
    if lacking:
        raise sm.StableMaskError(f"L1 輸出點契約不成立：engine={engine}：輸出欄無參數契約 {lacking[:20]}")
    ks: Dict[str, int] = {}
    masked: Dict[str, np.ndarray] = {}
    pending = [str(c) for c in frame.columns]
    while pending:
        progressed = False
        for column in list(pending):
            spec = points[column]
            if any(u not in ks for u in spec["upstream"] if u in points):
                continue
            inputs = [data[c].to_numpy(dtype=np.float64) for c in spec["inputs"] if c in data.columns]
            values, k = mask_output(engine, spec["indicator"], column, frame[column].to_numpy(), spec["params"],
                                    origin=origin_of(inputs), upstream=spec["upstream"], window=spec["window"],
                                    upstream_k=ks)
            masked[column], ks[column] = values, k
            pending.remove(column)
            progressed = True
        if not progressed:
            raise sm.StableMaskError(f"L1 輸出點契約不成立：engine={engine}：上游 K 無法解析 {pending[:20]}")
    return pd.DataFrame({c: masked[str(c)] for c in frame.columns}, index=frame.index)


# 進階 atomic 引擎啟用時之倍數表條目（衍生欄 MS_OFI_ZSCORE／MS_VPIN_ZSCORE 依上游，不查表）
ADVANCED_ENTRIES = {
    "microstructure": ("MS_AMIHUD_ILLIQ", "MS_KYLE_LAMBDA", "MS_ROLL_SPREAD", "MS_CS_SPREAD", "MS_OFI_RAW",
                       "MS_LARGE_TRADE_RATIO", "MS_VPIN"),
    "entropy": ("ENT_SHANNON", "ENT_APEN", "ENT_SAMPEN", "ENT_FRACTAL_DIM", "ENT_HURST", "ENT_PERM"),
    "tail_risk": ("TR_CVAR", "TR_RV_UP", "TR_RV_DOWN", "TR_RSJ", "TR_UD_VOL_RATIO", "TR_GPR", "TR_JB", "TR_MDD"),
}
# 引擎於類別啟用時一律產出之自訂欄（不讀設定之指標清單）
ALWAYS_CUSTOM = {
    "volatility": ("KELTNER", "DONCHIAN", "PARKINSON_VOL", "GARMANKLASS_VOL"),
    "volume": ("VWAP", "VOLUME_MA_RATIO", "FORCE_INDEX", "KLINGER_VOLUME_OSC", "EASE_OF_MOVEMENT"),
}
_TALIB_CATEGORIES = ("trend", "momentum", "volatility", "volume", "cycle", "pattern", "statistics")


def check_config_coverage(config: Any) -> None:
    """FF-STAT Task 2.4（R5）：設定啟用之每個 L1 指標皆須在倍數表——於設定 hash 計算與快取查詢之前呼叫；
    缺者拋 ``WarmupTableError``，訊息列指標名與 max_period（不得套後備係數）。"""
    from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
    from momentum.FeatureEngineering.warmup_window import _resolve_indicator_max_period

    TALibWrapper.initialize()
    table = warmup_lookup.warmup_table()
    ai = config.atomic_indicators
    missing = []
    for cat in _TALIB_CATEGORIES:
        cat_cfg = getattr(ai, cat)
        if not cat_cfg.enabled:
            continue
        names = [(ind.name, ind.model_dump()) for ind in cat_cfg.indicators if ind.enabled]
        names += [(name, {}) for name in ALWAYS_CUSTOM.get(cat, ())]
        for name, raw in names:
            spec = TALibWrapper.INDICATOR_REGISTRY.get(name)
            entry = table_indicator(spec.talib_func, spec.category) if spec else str(name).upper()
            if spec is not None and spec.computed_in_adapter:
                continue
            if entry not in table:
                missing.append(f"{name}(max_period={_resolve_indicator_max_period(raw) if raw else 0})")
    for cat, entries in ADVANCED_ENTRIES.items():
        if getattr(ai, cat).enabled:
            missing += [f"{e}(advanced {cat})" for e in entries if e not in table]
    for item in getattr(config, "custom_indicators", None) or []:
        if str(item.name).upper() not in table:
            missing.append(f"{item.name}(custom)")
    if missing:
        raise warmup_lookup.WarmupTableError(
            f"倍數表缺以下 L1 指標，生成於設定 hash 與快取查詢前中止（FF-STAT R5，不套後備係數）：{missing}"
        )


# 引擎寫死之自訂欄參數（與 volatility／volume 引擎之 mask_frame 呼叫一致）
ALWAYS_CUSTOM_PARAMS = {
    "KELTNER": {"timeperiod": 20}, "DONCHIAN": {"timeperiod": 20}, "PARKINSON_VOL": {"timeperiod": 20},
    "GARMANKLASS_VOL": {"timeperiod": 20}, "VWAP": {"timeperiod": 20}, "VOLUME_MA_RATIO": {"timeperiod": 20},
    "FORCE_INDEX": {"timeperiod": 13}, "KLINGER_VOLUME_OSC": {},
    "EASE_OF_MOVEMENT": {"timeperiod": 14},
}
_PATTERN_FREQUENCY_MAX_WINDOW = 21  # PatternIndicatorEngine.compute_pattern_frequency 預設窗之最大者


def _k_from_table(indicator: str, params: Mapping[str, Any]) -> int:
    """與 ``stable_mask.instance_k`` 同一規則（不經其模組屬性，避免估算污染測試之 spy）。"""
    entry = warmup_lookup.get_entry(indicator)
    if entry.get("warmup_class") == "cumulative":
        return 0
    keys = tuple(entry.get("period_keys") or ())
    if not keys:
        sm.check_variant(entry, params, keys)  # r32 codex P2-02：與遮罩路徑同一變體檢查
        return int(entry["k"])
    return int(sm.k_for_params(entry, params, keys))


def max_l1_k(config: Any) -> int:
    """設定啟用之全部 L1 輸出點之 K 最大者（原生週期根數；同引擎衍生輸出含其窗）——公開域預熱初值之 L1 成分。"""
    from momentum.FeatureEngineering.atomic.cycle_indicators import CycleIndicatorEngine
    from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
    from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
    from momentum.FeatureEngineering.atomic.momentum_indicators import MomentumIndicatorEngine
    from momentum.FeatureEngineering.atomic.statistics_indicators import StatisticsIndicatorEngine
    from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
    from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
    from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
    from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
    from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine

    TALibWrapper.initialize()
    engines = {"trend": TrendIndicatorEngine, "momentum": MomentumIndicatorEngine,
               "volatility": VolatilityIndicatorEngine, "volume": VolumeIndicatorEngine,
               "cycle": CycleIndicatorEngine, "statistics": StatisticsIndicatorEngine}
    ai = config.atomic_indicators
    best = 0
    for cat, engine_cls in engines.items():
        cat_cfg = getattr(ai, cat)
        if not cat_cfg.enabled:
            continue
        engine = engine_cls(cat_cfg.model_dump(), [])
        for ind in cat_cfg.indicators:
            spec = TALibWrapper.INDICATOR_REGISTRY.get(ind.name) if ind.enabled else None
            if spec is None or spec.computed_in_adapter:
                continue
            for params in engine._resolve_params(ind.name, ind.model_dump()):
                best = max(best, _k_from_table(table_indicator(spec.talib_func, spec.category), params))
        for name in ALWAYS_CUSTOM.get(cat, ()):
            best = max(best, _k_from_table(name, ALWAYS_CUSTOM_PARAMS[name]))
    if ai.pattern.enabled:
        best = max(best, int(warmup_lookup.get_pattern_default_bars()) + _PATTERN_FREQUENCY_MAX_WINDOW - 1)
    advanced = (("microstructure", MicrostructureIndicatorEngine), ("entropy", EntropyIndicatorEngine),
                ("tail_risk", TailRiskIndicatorEngine))
    for cat, engine_cls in advanced:
        cat_cfg = getattr(ai, cat)
        if not cat_cfg.enabled:
            continue
        engine = engine_cls(cat_cfg.model_dump(), [])
        points = engine._output_points(pd.DataFrame()) if cat == "microstructure" else engine._output_points()
        ks: Dict[str, int] = {}
        for column, spec in points.items():
            if not spec["upstream"]:
                ks[column] = _k_from_table(spec["indicator"], spec["params"])
        for column, spec in points.items():
            if spec["upstream"]:
                ks[column] = max(ks.get(u, 0) for u in spec["upstream"]) + int(spec["window"] or 1) - 1
        best = max([best, *ks.values()])
    for item in getattr(config, "custom_indicators", None) or []:
        for decl in item.outputs.values():
            entry = warmup_lookup.get_entry(item.name)
            keys = tuple(decl.period_keys) or tuple(entry.get("period_keys") or ())
            k = int(entry["k"]) if not keys else int(sm.k_for_params(entry, decl.params, keys))
            best = max(best, k)
    return best


__all__ = ["PATTERN_CATEGORY", "table_indicator", "period_keys_for", "origin_of", "mask_output", "mask_frame",
           "point", "mask_engine_frame", "check_config_coverage", "max_l1_k", "ADVANCED_ENTRIES", "ALWAYS_CUSTOM",
           "ALWAYS_CUSTOM_PARAMS"]
