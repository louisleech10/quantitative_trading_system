import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


def test_build_asof_index_map_basic():
    """測試 build_asof_index_map 基本對齊行為。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 10, 20], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source)

    np.testing.assert_array_equal(result, np.array([0, 1, 2], dtype=np.int64))


def test_build_asof_index_map_with_offset():
    """測試 OPEN_MINUS offset=-1ns 時，邊界點會取上一根。"""
    primary = np.array([10, 20], dtype=np.int64)
    source = np.array([10, 20], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source, offset_ns=-1)

    np.testing.assert_array_equal(result, np.array([-1, 0], dtype=np.int64))


def test_build_asof_index_map_unsorted_source_raises_value_error():
    """測試 source timestamp 未排序時會拋出 ValueError。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 20, 10], dtype=np.int64)

    with pytest.raises(ValueError, match="source_ts must be sorted"):
        TimeframeAligner.build_asof_index_map(primary, source)


def test_align_high_frequency_to_primary():
    source_ts = pd.Series([i * 3600 * 1000 for i in range(13)])
    source_df = pd.DataFrame({"value": list(range(13))}, index=source_ts)
    primary_ts = pd.Series([0, 12 * 3600 * 1000, 24 * 3600 * 1000])

    aligned = TimeframeAligner.align_to_primary(
        source_df,
        "1h",
        primary_ts,
        "12h",
        alignment_mode=AlignmentMode.CLOSE_TIME,
    )
    assert aligned.index.size == 3
    assert aligned["value"].iloc[1] == 12
    assert aligned["value"].iloc[2] == 12
    assert TimeframeAligner.validate_no_future_leak(aligned, primary_ts)


def test_align_low_frequency_to_primary():
    source_ts = pd.Series([0, 24 * 3600 * 1000, 48 * 3600 * 1000])
    source_df = pd.DataFrame({"value": [1, 2, 3]}, index=source_ts)
    primary_ts = pd.Series([12 * 3600 * 1000, 36 * 3600 * 1000])

    aligned = TimeframeAligner.align_to_primary(source_df, "1d", primary_ts, "12h")
    assert aligned.index.size == 2
    assert aligned["value"].iloc[0] == 1
    assert aligned["value"].iloc[1] == 2


def test_validate_no_future_leak_detects_future():
    primary_ts = pd.Series([0, 12 * 3600 * 1000])
    aligned = pd.DataFrame({"value": [1.0, 2.0]})
    aligned.attrs["source_timestamps"] = pd.to_datetime(primary_ts + 3600 * 1000, unit="ms")
    assert not TimeframeAligner.validate_no_future_leak(aligned, primary_ts)
