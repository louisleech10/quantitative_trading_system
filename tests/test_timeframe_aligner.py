import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


NS = 1_000_000_000
HOUR = 3600


def _build_map(
    primary: np.ndarray,
    source: np.ndarray,
    source_dur_s: int = 0,
    primary_dur_s: int = 0,
    mode: str = "open_time",
) -> np.ndarray:
    return TimeframeAligner.build_asof_index_map(
        primary,
        source,
        source_dur_ns=source_dur_s * NS,
        primary_dur_ns=primary_dur_s * NS,
        mode=mode,
    )


def test_build_asof_index_map_basic():
    """測試 source_close <= primary_open 的基本對齊行為。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 10, 20], dtype=np.int64)

    result = _build_map(primary, source, source_dur_s=10)

    # source_close=[10,20,30], decision=[5,15,25] -> [-1,0,1].
    np.testing.assert_array_equal(result, np.array([-1, 0, 1], dtype=np.int64))


def test_build_asof_index_map_source_close_boundary():
    """測試 source_close 等於 decision time 時可用，不需 offset_ns。"""
    primary = np.array([10, 20], dtype=np.int64)
    source = np.array([0, 10], dtype=np.int64)

    result = _build_map(primary, source, source_dur_s=10)

    # source_close=[10,20], decision=[10,20] -> [0,1].
    np.testing.assert_array_equal(result, np.array([0, 1], dtype=np.int64))


def test_build_asof_index_map_unsorted_source_raises_value_error():
    """測試 source timestamp 未排序時會拋出 ValueError。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 20, 10], dtype=np.int64)

    with pytest.raises(ValueError, match="source_ts must be sorted"):
        _build_map(primary, source)


def test_align_high_frequency_to_primary():
    source_ts = pd.Series([i * HOUR * 1000 for i in range(13)])
    source_df = pd.DataFrame({"value": list(range(13))}, index=source_ts)
    primary_ts = pd.Series([0, 12 * HOUR * 1000, 24 * HOUR * 1000])

    aligned = TimeframeAligner.align_to_primary(
        source_df,
        "1h",
        primary_ts,
        "12h",
        alignment_mode=AlignmentMode.CLOSE_TIME,
    )
    assert aligned.index.size == 3
    # close_time decisions=[12h,24h,36h]; 1h source closes=[1h..13h].
    # Old row-0 value 12 contained look-ahead because source open 12h closes at 13h.
    assert aligned["value"].iloc[0] == 11
    assert aligned["value"].iloc[1] == 12
    assert aligned["value"].iloc[2] == 12
    source_close = pd.DatetimeIndex(aligned.attrs["source_timestamps"])
    decision_time = pd.to_datetime(primary_ts, unit="ms") + pd.Timedelta(hours=12)
    assert (source_close <= decision_time).all()


def test_align_low_frequency_to_primary():
    source_ts = pd.Series([0, 24 * HOUR * 1000, 48 * HOUR * 1000])
    source_df = pd.DataFrame({"value": [1, 2, 3]}, index=source_ts)
    primary_ts = pd.Series([12 * HOUR * 1000, 36 * HOUR * 1000])

    aligned = TimeframeAligner.align_to_primary(source_df, "1d", primary_ts, "12h")
    assert aligned.index.size == 2
    # open_time decisions=[12h,36h]; 1d source closes=[24h,48h,72h].
    # Old values [1,2] contained look-ahead; only the first daily bar is closed by 36h.
    assert np.isnan(aligned["value"].iloc[0])
    assert aligned["value"].iloc[1] == 1


def test_validate_no_future_leak_detects_future():
    primary_ts = pd.Series([0, 12 * 3600 * 1000])
    aligned = pd.DataFrame({"value": [1.0, 2.0]})
    aligned.attrs["source_timestamps"] = pd.to_datetime(primary_ts + 3600 * 1000, unit="ms")
    assert not TimeframeAligner.validate_no_future_leak(aligned, primary_ts)
