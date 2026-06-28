"""Task 1.2 — C1-1 wrapper vs talib differential + BUG-1 雙 oracle。"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pytest
import talib

from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.atomic.custom_indicators import CustomIndicatorEngine

pytestmark = pytest.mark.requires_kline

_DIFF_CASES: List[Tuple[str, Dict, str]] = [
    ("RSI", {"timeperiod": 14}, "close"),
    ("ATR", {"timeperiod": 14}, "close"),
    ("EMA", {"timeperiod": 21}, "close"),
    ("MACD", {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}, "close"),
    (
        "STOCH",
        {"fastk_period": 5, "slowk_period": 3, "slowd_period": 3},
        "close",
    ),
    ("BOP", {}, "close"),
    ("OBV", {}, "close"),
    ("AD", {}, "close"),
    ("ADOSC", {"fastperiod": 3, "slowperiod": 10}, "close"),
    ("BETA", {"timeperiod": 5}, "close"),
    ("CORREL", {"timeperiod": 5}, "close"),
    ("Beta_CloseVolume", {"timeperiod": 5}, "close"),
    ("Correl_CloseVolume", {"timeperiod": 5}, "close"),
    ("HT_DCPERIOD", {}, "close"),
    ("STDDEV", {"timeperiod": 5, "nbdev": 1}, "close"),
]


@pytest.fixture
def ohlcv_df(requires_kline_data):
    return requires_kline_data("BTCUSDT", "12h", min_rows=400)


def _talib_direct(indicator: str, data, params: Dict) -> np.ndarray | Tuple[np.ndarray, ...]:
    func = getattr(talib, indicator if indicator not in ("Beta_CloseVolume", "Correl_CloseVolume") else (
        "BETA" if indicator == "Beta_CloseVolume" else "CORREL"
    ))
    high = data["high"].to_numpy(dtype=float)
    low = data["low"].to_numpy(dtype=float)
    close = data["close"].to_numpy(dtype=float)
    volume = data["volume"].to_numpy(dtype=float)
    open_ = data["open"].to_numpy(dtype=float)

    if indicator in ("BETA", "CORREL"):
        return func(high, low, **params)
    if indicator in ("Beta_CloseVolume", "Correl_CloseVolume"):
        return func(close, volume, **params)
    if indicator == "RSI":
        return func(close, **params)
    if indicator == "ATR":
        return func(high, low, close, **params)
    if indicator == "EMA":
        return func(close, **params)
    if indicator == "MACD":
        return func(close, **params)
    if indicator == "STOCH":
        return func(high, low, close, **params)
    if indicator == "BOP":
        return func(open_, high, low, close)
    if indicator == "OBV":
        return func(close, volume)
    if indicator == "AD":
        return func(high, low, close, volume)
    if indicator == "ADOSC":
        return func(high, low, close, volume, **params)
    if indicator == "HT_DCPERIOD":
        return func(close)
    if indicator == "STDDEV":
        return func(close, **params)
    raise ValueError(f"No direct oracle for {indicator}")


def _compare_outputs(
    wrapper_out: np.ndarray,
    oracle_out: np.ndarray,
) -> None:
    w_nan = np.isnan(wrapper_out)
    o_nan = np.isnan(oracle_out)
    np.testing.assert_array_equal(w_nan, o_nan)
    mask = ~w_nan
    if mask.any():
        np.testing.assert_allclose(wrapper_out[mask], oracle_out[mask], rtol=1e-10, atol=1e-10)


@pytest.mark.parametrize("indicator,params,source", _DIFF_CASES)
def test_wrapper_matches_talib_direct(ohlcv_df, indicator: str, params: Dict, source: str) -> None:
    TALibWrapper.initialize()
    wrapper_df = TALibWrapper.compute(indicator, ohlcv_df, params, source)
    oracle = _talib_direct(indicator, ohlcv_df, params)
    if not isinstance(oracle, tuple):
        oracle = (oracle,)
    assert len(wrapper_df.columns) == len(oracle)
    for col_idx in range(len(oracle)):
        wrapper_vals = wrapper_df.iloc[:, col_idx].to_numpy(dtype=float)
        _compare_outputs(wrapper_vals, oracle[col_idx])


def test_beta_correl_dual_oracle(ohlcv_df) -> None:
    """BUG-1：標準 BETA/CORREL == talib(high,low)；價量版 == talib(close,volume)。"""
    params = {"timeperiod": 5}
    high = ohlcv_df["high"].to_numpy(dtype=float)
    low = ohlcv_df["low"].to_numpy(dtype=float)
    close = ohlcv_df["close"].to_numpy(dtype=float)
    volume = ohlcv_df["volume"].to_numpy(dtype=float)

    beta_hl = TALibWrapper.compute("BETA", ohlcv_df, params).iloc[:, 0].to_numpy()
    correl_hl = TALibWrapper.compute("CORREL", ohlcv_df, params).iloc[:, 0].to_numpy()
    beta_cv = TALibWrapper.compute("Beta_CloseVolume", ohlcv_df, params).iloc[:, 0].to_numpy()
    correl_cv = TALibWrapper.compute("Correl_CloseVolume", ohlcv_df, params).iloc[:, 0].to_numpy()

    _compare_outputs(beta_hl, talib.BETA(high, low, timeperiod=5))
    _compare_outputs(correl_hl, talib.CORREL(high, low, timeperiod=5))
    _compare_outputs(beta_cv, talib.BETA(close, volume, timeperiod=5))
    _compare_outputs(correl_cv, talib.CORREL(close, volume, timeperiod=5))

    # 標準與價量語義不同（防假綠）
    valid = ~(np.isnan(beta_hl) | np.isnan(beta_cv))
    assert not np.allclose(beta_hl[valid], beta_cv[valid], rtol=1e-6, atol=1e-6)


def test_price_transform_adapter_policy(ohlcv_df) -> None:
    """price_transform：computed_in_adapter → compute 回空 DF（adapter 層負責）。"""
    for name in ("AVGPRICE", "MEDPRICE", "TYPPRICE", "WCLPRICE"):
        out = TALibWrapper.compute(name, ohlcv_df, {})
        assert out.empty or len(out.columns) == 0


def test_custom_indicator_smoke(ohlcv_df) -> None:
    """custom 模組抽樣：CustomIndicatorEngine 空定義不 crash。"""
    engine = CustomIndicatorEngine()
    out = engine.compute_all(ohlcv_df, [])
    assert out.empty


def test_mutation_wrapper_source_close_to_open_fails(ohlcv_df, monkeypatch) -> None:
    """Mutation C1-1：改 RSI source close→open 應與 talib(close) 不一致。"""
    TALibWrapper.initialize()
    original = TALibWrapper._prepare_inputs

    def _patched_prepare(spec, data, data_source, params):
        if spec.name == "RSI":
            data_source = "open"
        return original(spec, data, data_source, params)

    monkeypatch.setattr(TALibWrapper, "_prepare_inputs", staticmethod(_patched_prepare))
    wrapper_df = TALibWrapper.compute("RSI", ohlcv_df, {"timeperiod": 14}, "close")
    oracle = talib.RSI(ohlcv_df["close"].to_numpy(dtype=float), timeperiod=14)
    w = wrapper_df.iloc[:, 0].to_numpy()
    valid = ~(np.isnan(w) | np.isnan(oracle))
    assert not np.allclose(w[valid], oracle[valid], rtol=1e-8, atol=1e-8)
