import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.labels.label_generator import LabelGenerator


def test_generate_log_return():
    """測試對數收益率與預期一致。"""
    close = pd.Series([1.0, 2.0, 4.0, 8.0])
    generator = LabelGenerator({})

    result = generator.generate_log_return(close, horizon=1)

    expected = pd.Series(
        [np.log(2.0 / 1.0), np.log(4.0 / 2.0), np.log(8.0 / 4.0), np.nan],
        index=close.index,
    )
    assert np.isclose(result.iloc[0], expected.iloc[0])
    assert np.isclose(result.iloc[1], expected.iloc[1])
    assert np.isclose(result.iloc[2], expected.iloc[2])
    assert np.isnan(result.iloc[3])


def test_generate_excess_return():
    """測試超額收益率計算。"""
    close = pd.Series([1.0, 2.0, 3.0, 4.0])
    benchmark = pd.Series([1.0, 1.5, 2.0, 2.5])
    generator = LabelGenerator({})

    result = generator.generate_excess_return(close, benchmark, horizon=1)

    asset_ret = close.shift(-1) / close - 1
    bench_ret = benchmark.shift(-1) / benchmark - 1
    expected = asset_ret - bench_ret
    pd.testing.assert_series_equal(result, expected)


def test_generate_risk_adjusted_return_handles_zero_vol():
    """測試風險調整收益率避免除以零。"""
    close = pd.Series([1.0, 1.0, 1.0, 1.0])
    generator = LabelGenerator({})

    result = generator.generate_risk_adjusted_return(close, horizon=1, vol_window=2)

    assert result.isna().all()


def test_generate_winsorized_return():
    """測試截尾收益率限制在分位區間內。"""
    close = pd.Series([1.0, 2.0, 100.0, 2.0, 1.0])
    generator = LabelGenerator({})

    result = generator.generate_winsorized_return(close, horizon=1, lower=0.1, upper=0.9)
    ret = close.shift(-1) / close - 1
    lo, hi = ret.quantile(0.1), ret.quantile(0.9)

    assert result.max() <= hi or np.isnan(result.max())
    assert result.min() >= lo or np.isnan(result.min())


def test_generate_returns_by_type_dispatch():
    """測試回傳類型分派與錯誤處理。"""
    close = pd.Series([1.0, 2.0, 4.0])
    generator = LabelGenerator({})

    simple = generator.generate_returns_by_type(close, horizon=1, return_type="simple")
    log_ret = generator.generate_returns_by_type(close, horizon=1, return_type="log")

    assert np.isclose(simple.iloc[0], 1.0)
    assert np.isclose(log_ret.iloc[0], np.log(2.0))
    assert np.isnan(simple.iloc[-1])

    with pytest.raises(ValueError):
        generator.generate_returns_by_type(close, horizon=1, return_type="unknown")


def test_horizon_to_bars():
    """測試時間語義轉換為 bars。"""
    generator = LabelGenerator({})

    assert generator.horizon_to_bars("24h", "12h") == 2
    assert generator.horizon_to_bars("1w", "12h") == 14
    assert generator.horizon_to_bars("24h", "1h") == 24
    assert generator.horizon_to_bars("24h", "4h") == 6

    with pytest.raises(ValueError):
        generator.horizon_to_bars("10h", "12h")
