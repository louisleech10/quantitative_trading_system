from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.feature_naming import build_identity, format_feature_name, parse_feature_name


def _name(indicator: str, source: str, *params: object) -> str:
    """FF-NAME 文法之 microstructure 欄名（未標記形；source＝輸出點輸入元組之 canonical 串接）。"""
    return format_feature_name(build_identity(source, "microstructure", indicator, params))


def _by_indicator(out: pd.DataFrame, *indicators: str) -> pd.DataFrame:
    """取 indicator 屬 `indicators` 之欄（取代改前之欄名前綴 `ms_<indicator>_` 篩選）。"""
    return out[[c for c in out.columns if parse_feature_name(c, tagged=False).indicator in indicators]]


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
    assert all(parse_feature_name(col, tagged=False).category == "microstructure" for col in df.columns)


def test_micro_feature_name_unique() -> None:
    engine = _engine()
    df = engine.compute_all(_make_data())
    assert len(df.columns) == len(set(df.columns))


def test_micro_metadata_complete() -> None:
    engine = _engine()
    metadata = engine.get_feature_metadata()
    assert len(metadata) == 25
    assert _name("ofi-raw", "taker-ratio") in metadata


def test_amihud_zero_volume() -> None:
    engine = _engine()
    data = _make_data()
    data["quote_volume"] = 0.0
    out = engine.compute_all(data)
    sub = _by_indicator(out, "amihud-illiq")
    assert sub.shape[1] > 0 and sub.isna().all().all()


def test_ltr_zero_trades() -> None:
    engine = _engine()
    data = _make_data()
    data["trades"] = 0.0
    out = engine.compute_all(data)
    sub = _by_indicator(out, "large-trade-ratio")
    assert sub.shape[1] > 0 and sub.isna().all().all()


def test_micro_insufficient_data() -> None:
    engine = _engine()
    data = _make_data(10)
    out = engine.compute_all(data)
    assert out[_name("amihud-illiq", "close-quote-volume", 55)].isna().all()


def _post_warmup(out: pd.DataFrame, indicator: str) -> pd.DataFrame:
    """取 indicator 欄之暖機後區段：因果 rolling 窗未滿之前段為 NaN 屬設計；
    NaN 只准出現在開頭連續暖機段（中段出現 NaN 即 FAIL），且暖機後須有值（防空集合恆真）。"""
    sub = _by_indicator(out, indicator)
    assert sub.shape[1] > 0, f"no columns with indicator {indicator}"
    for col in sub.columns:
        s = sub[col]
        first = s.first_valid_index()
        assert first is not None, f"{col} all NaN"
        assert s.loc[first:].notna().all(), f"{col} has NaN after warmup"
    start = max(sub[c].first_valid_index() for c in sub.columns)
    post = sub.loc[start:]
    assert len(post) > 0
    return post


def test_constant_price() -> None:
    engine = _engine()
    data = _make_data()
    data["close"] = 100.0
    data["high"] = 100.0
    data["low"] = 100.0
    out = engine.compute_all(data)
    assert (_post_warmup(out, "kyle-lambda") == 0.0).all().all()
    assert (_post_warmup(out, "roll-spread") == 0.0).all().all()


def test_ofi_fallback() -> None:
    engine = _engine()
    data = _make_data().drop(columns=["taker_ratio"])
    out = engine.compute_all(data)
    assert _name("ofi-raw", "taker-buy-volume-volume") in out.columns  # 退回分支：輸入 taker_buy_volume／volume


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
    assert (_post_warmup(out, "cs-spread") == 0.0).all().all()


def test_roll_positive_autocov() -> None:
    engine = _engine()
    data = _make_data()
    data["close"] = np.arange(len(data), dtype=float)
    out = engine.compute_all(data)
    assert (_post_warmup(out, "roll-spread") >= 0.0).all().all()


def test_vpin_zero_volume() -> None:
    engine = _engine()
    data = _make_data()
    data["volume"] = 0.0
    out = engine.compute_all(data)
    sub = _by_indicator(out, "vpin", "vpin-zscore")
    assert sub.shape[1] > 0 and sub.isna().all().all()


def test_vpin_zero_sigma() -> None:
    engine = _engine()
    data = _make_data()
    data["close"] = 100.0
    out = engine.compute_all(data)
    vpin = _by_indicator(out, "vpin", "vpin-zscore")
    assert (vpin.fillna(0.0) == 0.0).all().all()
