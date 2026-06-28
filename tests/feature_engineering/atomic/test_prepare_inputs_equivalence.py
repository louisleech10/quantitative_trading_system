"""Task 1.1 — C1-2 prepare_inputs equivalence vs TALIB_INPUT_SEMANTICS + talib 直呼。"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pytest
import talib

from momentum.FeatureEngineering.atomic.talib_input_semantics import (
    C12_EXCLUDED_INDICATORS,
    C12_MAVP_ALLOWLIST,
    arrays_from_dataframe,
    build_talib_input_semantics,
)
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper

pytestmark = pytest.mark.requires_kline

_SAMPLE_CASES: List[Tuple[str, Dict]] = [
    ("RSI", {"timeperiod": 14}),
    ("ATR", {"timeperiod": 14}),
    ("EMA", {"timeperiod": 21}),
    ("MACD", {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}),
    ("STOCH", {"fastk_period": 5, "slowk_period": 3, "slowd_period": 3}),
    ("BOP", {}),
    ("OBV", {}),
    ("AD", {}),
    ("ADOSC", {"fastperiod": 3, "slowperiod": 10}),
    ("BETA", {"timeperiod": 5}),
    ("CORREL", {"timeperiod": 5}),
    ("Beta_CloseVolume", {"timeperiod": 5}),
    ("Correl_CloseVolume", {"timeperiod": 5}),
    ("HT_DCPERIOD", {}),
    ("STDDEV", {"timeperiod": 5, "nbdev": 1}),
]


@pytest.fixture
def ohlcv_df(requires_kline_data):
    df = requires_kline_data("BTCUSDT", "12h", min_rows=300)
    for col in ("open", "high", "low", "close", "volume"):
        assert col in df.columns
    return df


def _wrapper_arrays(spec_name: str, data, params: Dict, source: str = "close") -> List[np.ndarray]:
    spec = TALibWrapper.get_indicator_spec(spec_name)
    params_copy = dict(params)
    inputs, _ = TALibWrapper._prepare_inputs(spec, data, source, params_copy)
    return inputs


@pytest.mark.parametrize("indicator,params", _SAMPLE_CASES)
def test_prepare_inputs_byte_equal_to_semantics_table(
    ohlcv_df, indicator: str, params: Dict
) -> None:
    if indicator in C12_EXCLUDED_INDICATORS:
        pytest.skip("price_transform excluded from C1-2")
    if indicator in C12_MAVP_ALLOWLIST:
        pytest.skip("MAVP special periods excluded")

    semantic_arrays = arrays_from_dataframe(indicator, ohlcv_df)
    wrapper_arrays = _wrapper_arrays(indicator, ohlcv_df, params)

    assert len(wrapper_arrays) == len(semantic_arrays)
    for wa, sa in zip(wrapper_arrays, semantic_arrays):
        np.testing.assert_array_equal(wa, sa)


def test_registry_coverage_excludes_adapter_and_mavp(ohlcv_df) -> None:
    """registry 每指標皆有語義表條目（adapter/MAVP 除外）。"""
    TALibWrapper.initialize()
    semantics = build_talib_input_semantics([])
    for spec in TALibWrapper.list_indicators():
        if spec.computed_in_adapter or spec.name in C12_MAVP_ALLOWLIST:
            continue
        assert spec.name in semantics, f"missing semantics for {spec.name}"


def test_mutation_delete_atr_from_map_fails_equivalence(ohlcv_df) -> None:
    """Mutation C1-2：刪 ATR from _INPUT_TYPE_MAP → 本測試必 FAIL。"""
    TALibWrapper.initialize()
    original_hlc = set(TALibWrapper._INPUT_TYPE_MAP["hlc"])
    try:
        hlc = set(original_hlc)
        hlc.discard("ATR")
        TALibWrapper._INPUT_TYPE_MAP["hlc"] = hlc
        TALibWrapper.INDICATOR_REGISTRY.clear()
        TALibWrapper.initialize()
        wrapper_arrays = _wrapper_arrays("ATR", ohlcv_df, {"timeperiod": 14})
        semantic_arrays = arrays_from_dataframe("ATR", ohlcv_df)
        with pytest.raises(AssertionError):
            np.testing.assert_array_equal(wrapper_arrays[0], semantic_arrays[0])
    finally:
        TALibWrapper._INPUT_TYPE_MAP["hlc"] = original_hlc
        TALibWrapper.INDICATOR_REGISTRY.clear()
        TALibWrapper.initialize()
