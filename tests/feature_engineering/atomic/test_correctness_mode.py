"""Task 1.0 — correctness mode：fail-open off 時已登錄指標失敗須 raise。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Type

import pytest

from momentum.FeatureEngineering.atomic.cycle_indicators import CycleIndicatorEngine
from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.momentum_indicators import MomentumIndicatorEngine
from momentum.FeatureEngineering.atomic.pattern_indicators import PatternIndicatorEngine
from momentum.FeatureEngineering.atomic.statistics_indicators import StatisticsIndicatorEngine
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine


_ENGINE_MUTATION_CASES: List[Tuple[Type[Any], str, str, Dict]] = [
    (
        MomentumIndicatorEngine,
        "MFI",
        "hlcv",
        {"indicators": [{"name": "MFI", "periods": [14]}]},
    ),
    (
        VolatilityIndicatorEngine,
        "ATR",
        "hlc",
        {"indicators": [{"name": "ATR", "periods": [14]}]},
    ),
    (
        VolumeIndicatorEngine,
        "OBV",
        "close_volume",
        {"indicators": [{"name": "OBV"}]},
    ),
    (
        StatisticsIndicatorEngine,
        "BETA",
        "hl",
        {"indicators": [{"name": "BETA", "periods": [5]}]},
    ),
    (
        TrendIndicatorEngine,
        "SAR",
        "hl",
        {"indicators": [{"name": "SAR"}]},
    ),
    (
        CycleIndicatorEngine,
        "CCI",
        "hlc",
        {"indicators": [{"name": "CCI", "periods": [14]}]},
    ),
    (
        PatternIndicatorEngine,
        "BOP",
        "ohlc",
        {"indicators": [{"name": "BOP"}]},
    ),
]


@pytest.fixture
def kline_df(requires_kline_data):
    return requires_kline_data("BTCUSDT", "12h", min_rows=200)


def _apply_map_deletion(map_key: str, indicator: str) -> set[str]:
    TALibWrapper.INDICATOR_REGISTRY.clear()
    TALibWrapper.initialize()
    original = set(TALibWrapper._INPUT_TYPE_MAP[map_key])
    mutated = set(original)
    mutated.discard(indicator)
    TALibWrapper._INPUT_TYPE_MAP[map_key] = mutated
    TALibWrapper.INDICATOR_REGISTRY.clear()
    TALibWrapper.initialize()
    return original


def _restore_map(map_key: str, original: set[str]) -> None:
    TALibWrapper._INPUT_TYPE_MAP[map_key] = original
    TALibWrapper.INDICATOR_REGISTRY.clear()
    TALibWrapper.initialize()


def test_correctness_mode_raises_on_registered_indicator_failure(
    kline_df, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation probe C1-0：刪 MFI from map → compute_all raise（非 warning）。"""
    monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
    try:
        original = _apply_map_deletion("hlcv", "MFI")
        engine = MomentumIndicatorEngine(
            {
                "indicators": [{"name": "MFI", "periods": [14]}],
                "fail_open_indicators": False,
            },
            ["close"],
        )
        with pytest.raises(Exception):
            engine.compute_all(kline_df)
    finally:
        _restore_map("hlcv", original)
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)


@pytest.mark.parametrize(
    "engine_cls,indicator,map_key,config",
    _ENGINE_MUTATION_CASES,
    ids=[case[1] for case in _ENGINE_MUTATION_CASES],
)
def test_correctness_mode_raises_across_engines_on_map_deletion(
    kline_df,
    monkeypatch: pytest.MonkeyPatch,
    engine_cls: Type[Any],
    indicator: str,
    map_key: str,
    config: Dict,
) -> None:
    """C1-0 跨 7 talib engine：刪已登錄指標 from _INPUT_TYPE_MAP → correctness mode 下 compute_all raise。"""
    monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
    try:
        original = _apply_map_deletion(map_key, indicator)
        engine = engine_cls({**config, "fail_open_indicators": False}, ["close"])
        with pytest.raises(Exception):
            engine.compute_all(kline_df)
    finally:
        _restore_map(map_key, original)
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)


def test_correctness_mode_raises_on_microstructure_failure(
    kline_df, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C1-0 第 8 engine（microstructure）：注入計算 fault → correctness mode raise。"""
    monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
    engine = MicrostructureIndicatorEngine(
        {"enabled_features": ["amihud"], "fail_open_indicators": False},
        ["close"],
    )

    def _broken_amihud(_data):
        raise RuntimeError("injected microstructure fault")

    monkeypatch.setattr(engine, "_compute_amihud", _broken_amihud)
    try:
        with pytest.raises(RuntimeError, match="injected microstructure fault"):
            engine.compute_all(kline_df)
    finally:
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)


def test_correctness_mode_raises_on_entropy_failure(
    kline_df, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C1-0 entropy engine：注入 shannon fault → correctness mode raise。"""
    monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
    engine = EntropyIndicatorEngine(
        {"apply_to": ["close_return"], "fail_open_indicators": False},
        ["close"],
    )

    def _broken_shannon(_series, _source_name):
        raise RuntimeError("injected entropy fault")

    monkeypatch.setattr(engine, "_compute_shannon_entropy", _broken_shannon)
    try:
        with pytest.raises(RuntimeError, match="injected entropy fault"):
            engine.compute_all(kline_df)
    finally:
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)


def test_correctness_mode_raises_on_tail_risk_failure(
    kline_df, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C1-0 tail_risk engine：注入 cvar fault → correctness mode raise。"""
    monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
    engine = TailRiskIndicatorEngine({"fail_open_indicators": False}, ["close"])

    def _broken_cvar(_returns):
        raise RuntimeError("injected tail_risk fault")

    monkeypatch.setattr(engine, "_compute_cvar", _broken_cvar)
    try:
        with pytest.raises(RuntimeError, match="injected tail_risk fault"):
            engine.compute_all(kline_df)
    finally:
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)


def test_fail_open_default_warns_not_raises(kline_df, monkeypatch: pytest.MonkeyPatch) -> None:
    """預設 fail-open：同 mutation 不 raise（行為不變）。"""
    monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)
    TALibWrapper.initialize()
    original = TALibWrapper._INPUT_TYPE_MAP["hlcv"].copy()
    try:
        hlcv = set(TALibWrapper._INPUT_TYPE_MAP["hlcv"])
        hlcv.discard("MFI")
        TALibWrapper._INPUT_TYPE_MAP["hlcv"] = hlcv
        engine = MomentumIndicatorEngine(
            {"indicators": [{"name": "MFI", "periods": [14]}]},
            ["close"],
        )
        result = engine.compute_all(kline_df)
        assert isinstance(result, type(kline_df))  # DataFrame
    finally:
        TALibWrapper._INPUT_TYPE_MAP["hlcv"] = original


def test_mutation_correctness_mode_off_vs_on(kline_df, monkeypatch: pytest.MonkeyPatch) -> None:
    """§B1.1 自證：correctness off→不 raise；on→同 mutation raise。"""
    map_key = "hlcv"
    indicator = "MFI"
    config_off = {"indicators": [{"name": "MFI", "periods": [14]}]}
    config_on = {
        "indicators": [{"name": "MFI", "periods": [14]}],
        "fail_open_indicators": False,
    }

    TALibWrapper.INDICATOR_REGISTRY.clear()
    TALibWrapper.initialize()
    true_original = set(TALibWrapper._INPUT_TYPE_MAP[map_key])

    monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)
    try:
        _apply_map_deletion(map_key, indicator)
        engine_off = MomentumIndicatorEngine(config_off, ["close"])
        result = engine_off.compute_all(kline_df)
        assert isinstance(result, type(kline_df))

        monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
        _apply_map_deletion(map_key, indicator)
        engine_on = MomentumIndicatorEngine(config_on, ["close"])
        with pytest.raises(Exception):
            engine_on.compute_all(kline_df)
    finally:
        _restore_map(map_key, true_original)
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)


def test_mutation_entropy_off_vs_on(kline_df, monkeypatch: pytest.MonkeyPatch) -> None:
    """§B1.1 自證：entropy off→不 raise；on→同 fault-injection raise。"""
    monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)
    engine_off = EntropyIndicatorEngine({"apply_to": ["close_return"]}, ["close"])

    def _broken_shannon(_series, _source_name):
        raise RuntimeError("injected entropy fault")

    monkeypatch.setattr(engine_off, "_compute_shannon_entropy", _broken_shannon)
    result = engine_off.compute_all(kline_df)
    assert isinstance(result, type(kline_df))

    monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
    engine_on = EntropyIndicatorEngine(
        {"apply_to": ["close_return"], "fail_open_indicators": False},
        ["close"],
    )
    monkeypatch.setattr(engine_on, "_compute_shannon_entropy", _broken_shannon)
    try:
        with pytest.raises(RuntimeError, match="injected entropy fault"):
            engine_on.compute_all(kline_df)
    finally:
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)


def test_mutation_tail_risk_off_vs_on(kline_df, monkeypatch: pytest.MonkeyPatch) -> None:
    """§B1.1 自證：tail_risk off→不 raise；on→同 fault-injection raise。"""
    monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)
    engine_off = TailRiskIndicatorEngine({}, ["close"])

    def _broken_cvar(_returns):
        raise RuntimeError("injected tail_risk fault")

    monkeypatch.setattr(engine_off, "_compute_cvar", _broken_cvar)
    result = engine_off.compute_all(kline_df)
    assert isinstance(result, type(kline_df))

    monkeypatch.setenv("FF_CORRECTNESS_MODE", "1")
    engine_on = TailRiskIndicatorEngine({"fail_open_indicators": False}, ["close"])
    monkeypatch.setattr(engine_on, "_compute_cvar", _broken_cvar)
    try:
        with pytest.raises(RuntimeError, match="injected tail_risk fault"):
            engine_on.compute_all(kline_df)
    finally:
        monkeypatch.delenv("FF_CORRECTNESS_MODE", raising=False)
