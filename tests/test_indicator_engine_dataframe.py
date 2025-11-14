"""Unit tests for IndicatorEngine.calculate_indicators_from_dataframe."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pandas.testing as pdt

# Ensure project root is on sys.path for direct execution
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.Indicators.indicator_engine import IndicatorEngine
from momentum.Indicators.ema_indicator import EMAIndicator


def _build_dummy_klines(rows: int = 20) -> pd.DataFrame:
    """Construct a minimal-yet-valid Kline DataFrame for unit tests."""
    timestamps = pd.date_range("2025-01-01", periods=rows, freq="h")
    base = pd.Series(range(1, rows + 1), dtype=float)

    return pd.DataFrame(
        {
            "timestamp": timestamps.astype("int64") // 10**9,
            "open": base + 0.1,
            "high": base + 0.5,
            "low": base - 0.5,
            "close": base,
            "volume": base * 10,
            "taker_buy_volume": base * 5,
            "taker_ratio": 0.5,
            "quote_volume": base * 20,
        }
    )


def test_calculate_indicators_from_dataframe_success():
    df = _build_dummy_klines()
    engine = IndicatorEngine()

    configs = [
        {
            "indicator": "ema",
            "data_source": "close",
            "params": {"period": 3},
            "output_name": "ema_short",
        },
        {
            "indicator": "ema",
            "data_source": "close",
            "params": {"period": 5},
            "output_name": "ema_long",
        },
    ]

    indicators = engine.calculate_indicators_from_dataframe(df, configs)

    assert set(["ema_short", "ema_long"]).issubset(indicators.columns)

    expected_short = EMAIndicator().calculate(df["close"], period=3)
    pdt.assert_series_equal(indicators["ema_short"], expected_short, check_names=False)


def test_calculate_indicators_from_dataframe_missing_column():
    df = _build_dummy_klines().drop(columns=["close"])
    engine = IndicatorEngine()

    configs = [
        {
            "indicator": "ema",
            "data_source": "close",
            "params": {"period": 3},
            "output_name": "ema_short",
        }
    ]

    try:
        engine.calculate_indicators_from_dataframe(df, configs)
    except ValueError as exc:
        assert "close" in str(exc)
    else:
        raise AssertionError("Expected ValueError when close column is missing")


if __name__ == "__main__":
    test_calculate_indicators_from_dataframe_success()
    test_calculate_indicators_from_dataframe_missing_column()
    print("All indicator engine dataframe tests passed.")
