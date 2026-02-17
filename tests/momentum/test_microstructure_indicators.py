from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine


def _make_data(n: int = 300) -> pd.DataFrame:
    np.random.seed(42)
    close = pd.Series(100 + np.cumsum(np.random.normal(0, 1, n)))
    high = close + np.abs(np.random.normal(0.5, 0.2, n))
    low = close - np.abs(np.random.normal(0.5, 0.2, n))
    volume = pd.Series(np.random.randint(100, 1000, n)).astype(float)
    quote_volume = close * volume
    taker_buy_volume = volume * np.random.uniform(0.4, 0.7, n)
    taker_ratio = taker_buy_volume / volume
    trades = pd.Series(np.random.randint(1, 50, n)).astype(float)

    return pd.DataFrame(
        {
            "close": close,
            "high": high,
            "low": low,
            "volume": volume,
            "quote_volume": quote_volume,
            "taker_buy_volume": taker_buy_volume,
            "taker_ratio": taker_ratio,
            "trades": trades,
        }
    )


def _engine() -> MicrostructureIndicatorEngine:
    config = {
        "windows": [5, 13, 21, 55],
        "cs_spread_smooth": [5, 13, 21],
        "kyle_lambda_windows": [13, 21, 55],
        "vpin_n_buckets": [30, 50],
        "vpin_zscore_windows": [21, 55],
    }
    return MicrostructureIndicatorEngine(config, ["close"])


def test_micro_compute_all_feature_count_and_prefix() -> None:
    engine = _engine()
    df = engine.compute_all(_make_data())
    assert df.shape[1] == 25
    assert all(col.startswith("ms_") for col in df.columns)


def test_micro_feature_name_unique() -> None:
    engine = _engine()
    df = engine.compute_all(_make_data())
    assert len(df.columns) == len(set(df.columns))


def test_micro_metadata_complete() -> None:
    engine = _engine()
    metadata = engine.get_feature_metadata()
    assert len(metadata) == 25
    assert "ms_ofi_raw" in metadata


def test_amihud_zero_volume() -> None:
    engine = _engine()
    data = _make_data()
    data["quote_volume"] = 0.0
    out = engine.compute_all(data)
    assert out.filter(like="ms_amihud_illiq_").isna().all().all()


def test_ltr_zero_trades() -> None:
    engine = _engine()
    data = _make_data()
    data["trades"] = 0.0
    out = engine.compute_all(data)
    assert out.filter(like="ms_large_trade_ratio_").isna().all().all()


def test_micro_insufficient_data() -> None:
    engine = _engine()
    data = _make_data(10)
    out = engine.compute_all(data)
    assert out["ms_amihud_illiq_55"].isna().all()


def test_constant_price() -> None:
    engine = _engine()
    data = _make_data()
    data["close"] = 100.0
    data["high"] = 100.0
    data["low"] = 100.0
    out = engine.compute_all(data)
    assert (out.filter(like="ms_kyle_lambda_") == 0.0).all().all()
    assert (out.filter(like="ms_roll_spread_") == 0.0).all().all()


def test_ofi_fallback() -> None:
    engine = _engine()
    data = _make_data().drop(columns=["taker_ratio"])
    out = engine.compute_all(data)
    assert "ms_ofi_raw" in out.columns


def test_volume_spike() -> None:
    engine = _engine()
    data = _make_data()
    data.loc[100, "volume"] = data.loc[100, "volume"] * 1000
    out = engine.compute_all(data)
    assert out.shape[1] == 25


def test_zero_range_bar() -> None:
    engine = _engine()
    data = _make_data()
    data["high"] = data["low"]
    out = engine.compute_all(data)
    assert (out.filter(like="ms_cs_spread_") == 0.0).all().all()


def test_roll_positive_autocov() -> None:
    engine = _engine()
    data = _make_data()
    data["close"] = np.arange(len(data), dtype=float)
    out = engine.compute_all(data)
    assert (out.filter(like="ms_roll_spread_") >= 0.0).all().all()


def test_vpin_zero_volume() -> None:
    engine = _engine()
    data = _make_data()
    data["volume"] = 0.0
    out = engine.compute_all(data)
    assert out.filter(like="ms_vpin_").isna().all().all()


def test_vpin_zero_sigma() -> None:
    engine = _engine()
    data = _make_data()
    data["close"] = 100.0
    out = engine.compute_all(data)
    vpin = out.filter(like="ms_vpin_")
    assert (vpin.fillna(0.0) == 0.0).all().all()
