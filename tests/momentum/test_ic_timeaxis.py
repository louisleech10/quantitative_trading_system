from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_engine import ICEngine


def _load_kline_seconds_fixture() -> pd.DataFrame:
    return pd.read_csv(Path("tests/fixtures/ic_phase0/kline_seconds.csv"))


def test_get_time_index_parses_second_epoch_as_datetime_index() -> None:
    """真 kline 形狀：RangeIndex + 秒級 timestamp 欄。"""

    engine = ICEngine({})
    raw_data = _load_kline_seconds_fixture()

    time_index = engine._get_time_index(raw_data)

    assert isinstance(time_index, pd.DatetimeIndex)
    assert time_index.year.tolist() == [2024] * len(raw_data)


def test_iter_time_groups_handles_second_epoch_kline_shape() -> None:
    """秒級 timestamp fixture 走 year 分組不應回 Series 或崩潰。"""

    engine = ICEngine({})
    raw_data = _load_kline_seconds_fixture()

    groups = engine._iter_time_groups(raw_data, "year")

    assert [year for year, _ in groups] == [2024]
    assert list(groups[0][1]) == list(raw_data.index)


def test_get_time_index_rejects_implausible_numeric_timestamps() -> None:
    engine = ICEngine({})

    with pytest.raises(ValueError, match="timestamp"):
        engine._get_time_index(pd.DataFrame({"timestamp": [0, 1, 2]}))

    with pytest.raises(ValueError, match="timestamp"):
        engine._get_time_index(pd.DataFrame({"timestamp": [4102444800, 4102531200]}))

    with pytest.raises(ValueError, match="timestamp"):
        engine._get_time_index(pd.DataFrame({"timestamp": [10_000_000_000_000_000]}))


def test_get_time_index_parses_millisecond_epoch() -> None:
    engine = ICEngine({})

    time_index = engine._get_time_index(
        pd.DataFrame({"timestamp": [1704067200000, 1704153600000]})
    )

    assert isinstance(time_index, pd.DatetimeIndex)
    assert time_index.year.tolist() == [2024, 2024]


def test_get_time_index_rejects_nan_timestamp() -> None:
    engine = ICEngine({})

    with pytest.raises(ValueError, match="NaN"):
        engine._get_time_index(pd.DataFrame({"timestamp": [1704067200, np.nan]}))


def test_get_time_index_rejects_exact_unsupported_magnitude() -> None:
    engine = ICEngine({})

    with pytest.raises(ValueError, match="unsupported magnitude"):
        engine._get_time_index(pd.DataFrame({"timestamp": [1_000_000_000_000_000]}))


def test_compute_grouped_ic_rejects_explicit_by_volatility() -> None:
    engine = ICEngine({})
    features = pd.DataFrame({"feature": np.arange(6, dtype=float)})
    label = pd.Series(np.arange(6, dtype=float))
    raw_data = _load_kline_seconds_fixture()

    with pytest.raises(NotImplementedError, match="not supported"):
        engine.compute_grouped_ic(
            features,
            label,
            raw_data,
            metadata={},
            config={
                "method": "spearman",
                "by_year": False,
                "by_quarter": False,
                "by_regime": False,
                "by_category": False,
                "by_data_source": False,
                "by_layer": False,
                "by_volatility": True,
            },
        )
