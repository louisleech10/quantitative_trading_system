from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from momentum.FeatureEngineering.feature_factory import FeatureFactory


class _StubAdapterRegistry:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def fetch_aligned(self, symbol: str, timeframe: str, sources: list[str]) -> pd.DataFrame:
        return self._df.copy()


def _build_factory_with_df(df: pd.DataFrame) -> FeatureFactory:
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._adapter_registry = _StubAdapterRegistry(df)
    return factory


def test_layer0_date_filter_keeps_second_epoch_rows() -> None:
    dt_index = pd.date_range("2024-01-01", periods=5, freq="D")
    second_index = (dt_index.view("int64") // 1_000_000_000).astype("int64")
    df = pd.DataFrame({"open": [1, 2, 3, 4, 5]}, index=second_index)

    factory = _build_factory_with_df(df)
    config = SimpleNamespace(
        data_sources=SimpleNamespace(
            enabled_sources=["spot_klines"],
            synthetic_sources=[],
        )
    )

    filtered = factory._layer0_data_ingestion(
        symbol="ETHUSDT",
        timeframe="12h",
        config=config,
        start_date="2024-01-02",
        end_date="2024-01-03",
    )

    assert len(filtered) == 2
    assert filtered["open"].tolist() == [2, 3]


def test_data_range_uses_inferred_seconds_unit() -> None:
    dt_index = pd.date_range("2024-02-01", periods=2, freq="D")
    second_index = (dt_index.view("int64") // 1_000_000_000).astype("int64")
    df = pd.DataFrame({"open": [10, 11]}, index=second_index)

    data_range = FeatureFactory._data_range(df)

    assert len(data_range) == 2
    assert data_range[0].startswith("2024-02-01")
    assert data_range[1].startswith("2024-02-02")
