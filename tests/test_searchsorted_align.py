import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe import tf_aligner as tf_aligner_module
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


def _to_ms(series: pd.DatetimeIndex) -> pd.Series:
    return pd.Series((series.view("int64") // 1_000_000).astype(np.int64))


def _make_source_values(source_index: pd.DatetimeIndex) -> pd.DataFrame:
    values = np.arange(len(source_index), dtype=np.float32)
    return pd.DataFrame(
        {
            "f_close": values,
            "f_open": values * 0.5,
            "f_nan": np.where(values % 7 == 0, np.nan, values + 1.0),
        },
        index=source_index,
    )


def test_build_asof_index_map_basic():
    """T1.1: 基本 backward 對齊應回傳正確 index map。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 10, 20], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source)

    np.testing.assert_array_equal(result, np.array([0, 1, 2], dtype=np.int64))


def test_build_asof_index_map_with_offset():
    """T1.2: offset=-1ns 時，邊界點應取上一根。"""
    primary = np.array([10, 20], dtype=np.int64)
    source = np.array([10, 20], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source, offset_ns=-1)

    np.testing.assert_array_equal(result, np.array([-1, 0], dtype=np.int64))


def test_searchsorted_vs_merge_asof_numeric_equivalence():
    """T1.3: _searchsorted_align 與 merge_asof 路徑數值等價。"""
    source_index = pd.date_range("2026-01-01", periods=240, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=20, freq="12h")
    source_values = _make_source_values(source_index)

    expected = TimeframeAligner._merge_asof_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index - pd.Timedelta(nanoseconds=1),
    )
    expected.index = primary_index

    actual = TimeframeAligner._searchsorted_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        offset_ns=-1,
    )

    np.testing.assert_allclose(
        actual.to_numpy(dtype=np.float64),
        expected.to_numpy(dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )


def test_searchsorted_align_preserves_column_names():
    """T1.4: 對齊後欄位名順序與內容需完全一致。"""
    source_index = pd.date_range("2026-01-01", periods=48, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=6, freq="12h")
    source_values = _make_source_values(source_index)

    aligned = TimeframeAligner._searchsorted_align(source_values, source_index, primary_index, offset_ns=-1)

    assert list(aligned.columns) == list(source_values.columns)


def test_searchsorted_align_nan_pattern():
    """T1.5: 對齊後 NaN pattern 必須與 merge_asof 一致。"""
    source_index = pd.date_range("2026-01-01", periods=200, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=18, freq="12h")
    source_values = _make_source_values(source_index)

    expected = TimeframeAligner._merge_asof_align(
        source_values,
        source_index,
        primary_index - pd.Timedelta(nanoseconds=1),
    )
    expected.index = primary_index

    actual = TimeframeAligner._searchsorted_align(
        source_values,
        source_index,
        primary_index,
        offset_ns=-1,
    )

    assert np.array_equal(np.isnan(actual.to_numpy()), np.isnan(expected.to_numpy()))


def test_no_future_leak_after_searchsorted(monkeypatch):
    """T1.8: searchsorted 路徑需通過 future-leak 檢查。"""
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1")

    source_index = pd.date_range("2026-01-01", periods=72, freq="1h")
    source_df = pd.DataFrame({"feature": np.arange(72, dtype=np.float32)}, index=source_index)
    primary_index = pd.date_range("2026-01-01 12:00:00", periods=6, freq="12h")
    primary_ts = _to_ms(primary_index)

    aligned = TimeframeAligner.align_to_primary(
        source_df=source_df,
        source_tf="1h",
        primary_timestamps=primary_ts,
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )

    assert TimeframeAligner.validate_no_future_leak(aligned, primary_ts)


def test_searchsorted_align_preserves_source_timestamps_attr():
    """T1.9: 對齊輸出需保存 source_timestamps attrs。"""
    source_index = pd.date_range("2026-01-01", periods=36, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=5, freq="12h")
    source_values = _make_source_values(source_index)

    aligned = TimeframeAligner._searchsorted_align(source_values, source_index, primary_index, offset_ns=-1)

    assert "source_timestamps" in aligned.attrs
    assert isinstance(aligned.attrs["source_timestamps"], pd.DatetimeIndex)
    assert len(aligned.attrs["source_timestamps"]) == len(primary_index)


def test_env_var_fallback_to_merge_asof(monkeypatch):
    """T1.10: FFACT_USE_SEARCHSORTED=0 時應走 merge_asof fallback。"""
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "0")

    source_index = pd.date_range("2026-01-01", periods=96, freq="1h")
    source_values = _make_source_values(source_index)
    primary_index = pd.date_range("2026-01-01", periods=8, freq="12h")
    primary_ts = _to_ms(primary_index)

    source_df = source_values.copy()
    aligned = TimeframeAligner.align_to_primary(
        source_df=source_df,
        source_tf="1h",
        primary_timestamps=primary_ts,
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )

    expected = TimeframeAligner._merge_asof_align(
        source_values,
        source_index,
        primary_index - pd.Timedelta(nanoseconds=1),
    )
    expected.index = primary_index

    np.testing.assert_allclose(
        aligned.to_numpy(dtype=np.float64),
        expected.to_numpy(dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )


def test_build_asof_index_map_empty_source():
    """T1.B1: source 為空時應回傳全 -1。"""
    primary = np.array([1, 2, 3], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, np.array([], dtype=np.int64))

    np.testing.assert_array_equal(result, np.array([-1, -1, -1], dtype=np.int64))


def test_build_asof_index_map_empty_primary():
    """T1.B2: primary 為空時應回傳空陣列。"""
    source = np.array([1, 2, 3], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(np.array([], dtype=np.int64), source)

    assert result.size == 0


def test_build_asof_index_map_single_row():
    """T1.B3: 單一 source row 的 mapping 行為。"""
    primary = np.array([90, 100, 110], dtype=np.int64)
    source = np.array([100], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source)

    np.testing.assert_array_equal(result, np.array([-1, 0, 0], dtype=np.int64))


def test_build_asof_index_map_primary_before_all():
    """T1.B4: primary 全早於 source 時應全 -1。"""
    primary = np.array([1, 50], dtype=np.int64)
    source = np.array([100, 200], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source)

    np.testing.assert_array_equal(result, np.array([-1, -1], dtype=np.int64))


def test_build_asof_index_map_primary_after_all():
    """T1.B5: primary 全晚於 source 時應指向最後一列。"""
    primary = np.array([250, 300], dtype=np.int64)
    source = np.array([100, 200], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source)

    np.testing.assert_array_equal(result, np.array([1, 1], dtype=np.int64))


def test_build_asof_index_map_duplicate_timestamps():
    """T1.B6: source 有重複 timestamp 時應取最後一個。"""
    primary = np.array([10, 11], dtype=np.int64)
    source = np.array([0, 10, 10, 20], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source)

    np.testing.assert_array_equal(result, np.array([2, 2], dtype=np.int64))


def test_build_asof_index_map_unsorted_source():
    """T1.B7: source 未排序時應拋 ValueError。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 20, 10], dtype=np.int64)

    with pytest.raises(ValueError, match="source_ts must be sorted"):
        TimeframeAligner.build_asof_index_map(primary, source)


def test_searchsorted_align_all_nan_columns():
    """T1.B8: 全 NaN 欄位對齊後應維持全 NaN。"""
    source_index = pd.date_range("2026-01-01", periods=20, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=4, freq="12h")
    source_values = pd.DataFrame(
        {
            "nan_a": np.full(20, np.nan, dtype=np.float32),
            "nan_b": np.full(20, np.nan, dtype=np.float32),
        },
        index=source_index,
    )

    aligned = TimeframeAligner._searchsorted_align(source_values, source_index, primary_index, offset_ns=-1)

    assert aligned.isna().all().all()


def test_searchsorted_align_mixed_dtypes():
    """T1.B9: 混合 dtype 輸入後輸出應統一為 float32。"""
    source_index = pd.date_range("2026-01-01", periods=48, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=6, freq="12h")
    source_values = pd.DataFrame(
        {
            "f64": np.arange(48, dtype=np.float64),
            "f32": np.arange(48, dtype=np.float32),
            "int_col": np.arange(48, dtype=np.int64),
        },
        index=source_index,
    )

    aligned = TimeframeAligner._searchsorted_align(source_values, source_index, primary_index, offset_ns=-1)

    assert set(aligned.dtypes.unique()) == {np.dtype(np.float32)}


def test_searchsorted_align_very_wide_df(monkeypatch):
    """T1.B10: 寬表應走 memmap 路徑且完成對齊。"""
    source_index = pd.date_range("2026-01-01", periods=64, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=8, freq="12h")
    n_cols = 2048
    source_values = pd.DataFrame(
        np.random.RandomState(0).randn(len(source_index), n_cols).astype(np.float32),
        index=source_index,
        columns=[f"c_{i}" for i in range(n_cols)],
    )

    called = {"memmap": False}

    def _fake_memmap(shape, dtype=np.float32, prefix="ffact_"):
        del dtype, prefix
        called["memmap"] = True
        return np.empty(shape, dtype=np.float32)

    monkeypatch.setattr(tf_aligner_module, "MEMMAP_THRESHOLD_BYTES", 1)
    monkeypatch.setattr(tf_aligner_module, "create_temp_memmap", _fake_memmap)

    aligned = TimeframeAligner._searchsorted_align(source_values, source_index, primary_index, offset_ns=-1)

    assert called["memmap"]
    assert aligned.shape == (len(primary_index), n_cols)


def test_offset_ns_minus_one_at_exact_boundary():
    """T1.B14: exact boundary + offset=-1ns 需取上一根。"""
    primary = np.array([100, 200], dtype=np.int64)
    source = np.array([100, 200], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source, offset_ns=-1)

    np.testing.assert_array_equal(result, np.array([-1, 0], dtype=np.int64))


def test_build_asof_index_map_int_overflow():
    """T1.B15: 極大 timestamp 轉 ns 不應 overflow。"""
    max_ms = np.int64(np.iinfo(np.int64).max // 1_000_000 - 4)
    source = np.array([max_ms - 2, max_ms], dtype=np.int64)
    primary = np.array([max_ms], dtype=np.int64)

    result = TimeframeAligner.build_asof_index_map(primary, source, offset_ns=0)
    result_minus = TimeframeAligner.build_asof_index_map(primary, source, offset_ns=-1)

    np.testing.assert_array_equal(result, np.array([1], dtype=np.int64))
    np.testing.assert_array_equal(result_minus, np.array([0], dtype=np.int64))