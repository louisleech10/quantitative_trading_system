import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe import tf_aligner as tf_aligner_module
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


NS = 1_000_000_000


def _to_ms(series: pd.DatetimeIndex) -> pd.Series:
    return pd.Series((series.view("int64") // 1_000_000).astype(np.int64))


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


def _searchsorted_open_minus(
    source_values: pd.DataFrame,
    source_index: pd.DatetimeIndex,
    primary_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    return TimeframeAligner._searchsorted_align(
        source_values,
        source_index,
        primary_index,
        source_tf="1h",
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )


def _merge_open_minus(
    source_values: pd.DataFrame,
    source_index: pd.DatetimeIndex,
    primary_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    aligned = TimeframeAligner._merge_asof_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        source_tf="1h",
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )
    aligned.index = primary_index
    return aligned


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
    """T1.1: source close <= primary open 才可對齊。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 10, 20], dtype=np.int64)

    result = _build_map(primary, source, source_dur_s=10)

    # source_close=[10,20,30], decision=[5,15,25] -> [-1,0,1].
    np.testing.assert_array_equal(result, np.array([-1, 0, 1], dtype=np.int64))


def test_build_asof_index_map_source_close_boundary():
    """T1.2: source close 等於 decision time 時可用，不需 offset_ns。"""
    primary = np.array([10, 20], dtype=np.int64)
    source = np.array([0, 10], dtype=np.int64)

    result = _build_map(primary, source, source_dur_s=10)

    # source_close=[10,20], decision=[10,20] -> both exact closes are visible.
    np.testing.assert_array_equal(result, np.array([0, 1], dtype=np.int64))


def test_searchsorted_vs_merge_asof_numeric_equivalence():
    """T1.3: _searchsorted_align 與 merge_asof 路徑數值等價。"""
    source_index = pd.date_range("2026-01-01", periods=240, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=20, freq="12h")
    source_values = _make_source_values(source_index)

    expected = _merge_open_minus(source_values, source_index, primary_index)
    actual = _searchsorted_open_minus(source_values, source_index, primary_index)

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

    aligned = _searchsorted_open_minus(source_values, source_index, primary_index)

    assert list(aligned.columns) == list(source_values.columns)


def test_searchsorted_align_nan_pattern():
    """T1.5: 對齊後 NaN pattern 必須與 merge_asof 一致。"""
    source_index = pd.date_range("2026-01-01", periods=200, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=18, freq="12h")
    source_values = _make_source_values(source_index)

    expected = _merge_open_minus(source_values, source_index, primary_index)
    actual = _searchsorted_open_minus(source_values, source_index, primary_index)

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

    aligned = _searchsorted_open_minus(source_values, source_index, primary_index)

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

    expected = _merge_open_minus(source_values, source_index, primary_index)

    np.testing.assert_allclose(
        aligned.to_numpy(dtype=np.float64),
        expected.to_numpy(dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )


def test_build_asof_index_map_empty_source():
    """T1.B1: source 為空時應回傳全 -1。"""
    primary = np.array([1, 2, 3], dtype=np.int64)

    result = _build_map(primary, np.array([], dtype=np.int64))

    np.testing.assert_array_equal(result, np.array([-1, -1, -1], dtype=np.int64))


def test_build_asof_index_map_empty_primary():
    """T1.B2: primary 為空時應回傳空陣列。"""
    source = np.array([1, 2, 3], dtype=np.int64)

    result = _build_map(np.array([], dtype=np.int64), source)

    assert result.size == 0


def test_build_asof_index_map_single_row():
    """T1.B3: 單一 source row 的 mapping 行為。"""
    primary = np.array([90, 100, 110], dtype=np.int64)
    source = np.array([100], dtype=np.int64)

    result = _build_map(primary, source)

    np.testing.assert_array_equal(result, np.array([-1, 0, 0], dtype=np.int64))


def test_build_asof_index_map_primary_before_all():
    """T1.B4: primary 全早於 source 時應全 -1。"""
    primary = np.array([1, 50], dtype=np.int64)
    source = np.array([100, 200], dtype=np.int64)

    result = _build_map(primary, source)

    np.testing.assert_array_equal(result, np.array([-1, -1], dtype=np.int64))


def test_build_asof_index_map_primary_after_all():
    """T1.B5: primary 全晚於 source 時應指向最後一列。"""
    primary = np.array([250, 300], dtype=np.int64)
    source = np.array([100, 200], dtype=np.int64)

    result = _build_map(primary, source)

    np.testing.assert_array_equal(result, np.array([1, 1], dtype=np.int64))


def test_build_asof_index_map_duplicate_timestamps():
    """T1.B6: source 有重複 timestamp 時應取最後一個。"""
    primary = np.array([10, 11], dtype=np.int64)
    source = np.array([0, 10, 10, 20], dtype=np.int64)

    result = _build_map(primary, source)

    np.testing.assert_array_equal(result, np.array([2, 2], dtype=np.int64))


def test_build_asof_index_map_unsorted_source():
    """T1.B7: source 未排序時應拋 ValueError。"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 20, 10], dtype=np.int64)

    with pytest.raises(ValueError, match="source_ts must be sorted"):
        _build_map(primary, source)


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

    aligned = _searchsorted_open_minus(source_values, source_index, primary_index)

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

    aligned = _searchsorted_open_minus(source_values, source_index, primary_index)

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

    aligned = _searchsorted_open_minus(source_values, source_index, primary_index)

    assert called["memmap"]
    assert aligned.shape == (len(primary_index), n_cols)


def test_source_close_exact_boundary_inclusive():
    """T1.B14: exact boundary 依 source_close <= decision_time 手算。"""
    primary = np.array([100, 200], dtype=np.int64)
    source = np.array([0, 100, 200], dtype=np.int64)

    result = _build_map(primary, source, source_dur_s=100)

    # source_close=[100,200,300], decision=[100,200] -> [0,1].
    np.testing.assert_array_equal(result, np.array([0, 1], dtype=np.int64))


def test_build_asof_index_map_int_overflow():
    """T1.B15: 極大 timestamp 轉 ns 不應 overflow。"""
    max_s = np.int64(np.iinfo(np.int64).max // 1_000_000_000 - 4)
    source = np.array([max_s - 2, max_s], dtype=np.int64)
    primary = np.array([max_s], dtype=np.int64)

    result = _build_map(primary, source)
    result_with_one_ns_duration = TimeframeAligner.build_asof_index_map(
        primary,
        source,
        source_dur_ns=1,
        primary_dur_ns=0,
        mode="open_time",
    )

    np.testing.assert_array_equal(result, np.array([1], dtype=np.int64))
    np.testing.assert_array_equal(result_with_one_ns_duration, np.array([0], dtype=np.int64))
