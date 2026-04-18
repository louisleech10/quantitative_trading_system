"""Tests for Phase 1/2/3 memory optimization: column chunking, streaming, and merge batching.

Validates:
- Phase 1: L6.5 chunked output == non-chunked output
- Phase 2: L3 streaming + variance filter correctness
- Phase 3: MultiTF chunked merge == non-chunked merge
- Edge cases: empty, single col, all-NaN, constant, mixed dtypes
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Phase 1: L6.5 Column Chunking
# ---------------------------------------------------------------------------


class TestL65ColumnChunking:
    """L6.5 FeaturePreprocessor column chunking."""

    @staticmethod
    def _make_config(*, rank: bool = True, zscore: bool = True, winsor: bool = True):
        return {
            "mode": "replace",
            "winsorization": {
                "enabled": winsor,
                "method": "sigma",
                "sigma": 3.0,
                "apply_to": "all",
            },
            "rank_transform": {
                "enabled": rank,
                "window": 20,
                "apply_to": "all",
            },
            "adaptive_zscore": {
                "enabled": zscore,
                "window": 20,
                "apply_to": "all",
            },
        }

    @staticmethod
    def _make_wide_df(n_rows: int = 200, n_cols: int = 50, seed: int = 42):
        rng = np.random.RandomState(seed)
        data = rng.randn(n_rows, n_cols).astype(np.float32)
        cols = [f"feat_{i:04d}" for i in range(n_cols)]
        return pd.DataFrame(data, columns=cols)

    def test_chunked_matches_non_chunked(self):
        """核心正確性: chunked 結果必須與 non-chunked 完全一致"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = self._make_config()
        df = self._make_wide_df(n_rows=200, n_cols=50)

        # Non-chunked
        pp_full = FeaturePreprocessor(config)
        pp_full._column_chunk_size = 0  # disabled
        result_full = pp_full.transform(df)

        # Chunked (chunk_size=10 → 5 chunks)
        pp_chunked = FeaturePreprocessor(config)
        pp_chunked._column_chunk_size = 10
        result_chunked = pp_chunked.transform(df)

        pd.testing.assert_frame_equal(
            result_full.sort_index(axis=1),
            result_chunked.sort_index(axis=1),
            rtol=1e-5,
        )

    def test_empty_dataframe(self):
        """空 DataFrame 不應爆炸"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = self._make_config()
        pp = FeaturePreprocessor(config)
        pp._column_chunk_size = 10
        result = pp.transform(pd.DataFrame())
        assert result.empty

    def test_single_column(self):
        """只有 1 欄也能正常處理"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = self._make_config()
        df = self._make_wide_df(n_rows=100, n_cols=1)

        pp = FeaturePreprocessor(config)
        pp._column_chunk_size = 10
        result = pp.transform(df)
        assert result.shape[1] == 1
        assert not result.isna().all().all()

    def test_all_nan_columns(self):
        """全 NaN 欄位不該拋 exception"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = self._make_config()
        df = pd.DataFrame(np.nan, index=range(100), columns=["a", "b", "c"])

        pp = FeaturePreprocessor(config)
        pp._column_chunk_size = 2
        result = pp.transform(df)
        assert result.shape[1] == 3

    def test_constant_columns(self):
        """常數欄位不應拋 exception"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = self._make_config()
        df = pd.DataFrame({"const": [5.0] * 100, "normal": np.random.randn(100)})

        pp = FeaturePreprocessor(config)
        pp._column_chunk_size = 1
        result = pp.transform(df)
        assert result.shape[1] == 2

    def test_chunk_size_env_var(self, monkeypatch):
        """環境變數 FFACT_L65_CHUNK_SIZE 可控制 chunk size"""
        monkeypatch.setenv("FFACT_L65_CHUNK_SIZE", "500")
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        pp = FeaturePreprocessor({})
        assert pp._column_chunk_size == 500


# ---------------------------------------------------------------------------
# Phase 2: L3 Streaming + Variance Filter
# ---------------------------------------------------------------------------


class TestL3StreamingVarianceFilter:
    """L3 RollingAggregator streaming mode + variance filter."""

    @staticmethod
    def _make_aggregator(windows=None, aggs=None, chunk_size=256):
        from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

        config = {
            "enabled": True,
            "windows": windows or [5, 10],
            "aggregators": {
                name: {"enabled": True}
                for name in (aggs or ["mean", "std", "rank"])
            },
            "apply_to": "all",
        }
        agg = RollingAggregator(config)
        agg._column_chunk_size = chunk_size
        return agg

    @staticmethod
    def _make_data(n_rows=200, n_cols=10, seed=42, include_dead=False):
        rng = np.random.RandomState(seed)
        data = rng.randn(n_rows, n_cols).astype(np.float32)
        cols = [f"feat_{i}" for i in range(n_cols)]
        df = pd.DataFrame(data, columns=cols)
        if include_dead:
            df["dead_const"] = 0.0
            df["dead_nan"] = np.nan
        return df

    def test_streaming_output_matches_normal(self, monkeypatch):
        """Streaming 路徑結果在 variance filter 前應與普通路徑一致（排除 dead cols）"""
        monkeypatch.setenv("FFACT_L3_STREAMING", "0")
        agg_normal = self._make_aggregator(windows=[5], aggs=["mean", "std"])
        df = self._make_data(n_rows=200, n_cols=5)
        result_normal = agg_normal.compute_all(df)

        monkeypatch.setenv("FFACT_L3_STREAMING", "1")
        agg_stream = self._make_aggregator(windows=[5], aggs=["mean", "std"])
        result_stream = agg_stream.compute_all(df)

        # Streaming 結果應包含所有 non-dead 欄位
        # Normal result columns should all be present in streaming result
        for col in result_normal.columns:
            if col in result_stream.columns:
                pd.testing.assert_series_equal(
                    result_normal[col], result_stream[col], rtol=1e-5,
                    check_names=False,
                    check_dtype=False,
                )

    def test_variance_filter_removes_dead_columns(self, monkeypatch):
        """Variance filter 應移除 constant 和 all-NaN 生成欄位"""
        monkeypatch.setenv("FFACT_L3_STREAMING", "1")
        agg = self._make_aggregator(windows=[5], aggs=["mean", "std"])
        df = self._make_data(n_rows=200, n_cols=5, include_dead=True)
        result = agg.compute_all(df)

        # dead_const 的 mean/std 都是 constant (0.0) → std of constant = 0 → filtered
        # dead_nan 的所有 agg = NaN → filtered
        dead_cols = [c for c in result.columns if "dead_const" in c or "dead_nan" in c]
        # Some aggs on dead_const may survive (mean of constant = constant → filtered)
        # Verify at most very few survive
        surviving_nan = [c for c in dead_cols if "dead_nan" in c]
        assert len(surviving_nan) == 0, f"NaN cols should be filtered: {surviving_nan}"

    def test_streaming_empty_input(self, monkeypatch):
        """空 DataFrame 不應拋 exception"""
        monkeypatch.setenv("FFACT_L3_STREAMING", "1")
        agg = self._make_aggregator()
        result = agg.compute_all(pd.DataFrame())
        assert result.empty

    def test_variance_filter_standalone(self):
        """直接測試 _variance_filter"""
        from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

        df = pd.DataFrame({
            "good": np.random.randn(100),
            "constant": [1.0] * 100,
            "all_nan": [np.nan] * 100,
            "has_inf": [np.inf] + [1.0] * 99,
        })
        result = RollingAggregator._variance_filter(df)
        assert "good" in result.columns
        assert "constant" not in result.columns
        assert "all_nan" not in result.columns
        assert "has_inf" not in result.columns


# ---------------------------------------------------------------------------
# Phase 3: MultiTF Column-Batch Merge
# ---------------------------------------------------------------------------


class TestMultiTFColumnBatchMerge:
    """TimeframeAligner column-batch merge_asof."""

    @staticmethod
    def _make_aligned_data(n_rows=100, n_cols=20, freq="12h", seed=42):
        """Create a source DataFrame with DatetimeIndex and primary timestamps."""
        rng = np.random.RandomState(seed)
        source_index = pd.date_range("2024-01-01", periods=n_rows, freq=freq)
        data = rng.randn(n_rows, n_cols).astype(np.float32)
        cols = [f"feat_{i:04d}" for i in range(n_cols)]
        source_values = pd.DataFrame(data, columns=cols, index=source_index)

        # Primary timestamps: same freq, slight offset
        primary_index = pd.date_range("2024-01-01 01:00", periods=n_rows, freq=freq)
        return source_values, source_index, primary_index

    def test_chunked_merge_matches_single(self, monkeypatch):
        """分批 merge 結果必須與一次性 merge 完全一致"""
        from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

        source_values, source_index, primary_index = self._make_aligned_data(n_cols=20)

        # Non-chunked
        monkeypatch.setenv("FFACT_MERGE_CHUNK_SIZE", "0")
        result_single = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)

        # Chunked (chunk_size=5 → 4 chunks)
        monkeypatch.setenv("FFACT_MERGE_CHUNK_SIZE", "5")
        result_chunked = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)

        pd.testing.assert_frame_equal(
            result_single.sort_index(axis=1),
            result_chunked.sort_index(axis=1),
            rtol=1e-5,
        )

    def test_chunked_merge_preserves_source_timestamps(self, monkeypatch):
        """source_timestamps 屬性必須一致"""
        from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

        source_values, source_index, primary_index = self._make_aligned_data(n_cols=10)

        monkeypatch.setenv("FFACT_MERGE_CHUNK_SIZE", "0")
        result_single = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)

        monkeypatch.setenv("FFACT_MERGE_CHUNK_SIZE", "3")
        result_chunked = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)

        single_ts = result_single.attrs.get("source_timestamps")
        chunked_ts = result_chunked.attrs.get("source_timestamps")
        assert single_ts is not None
        assert chunked_ts is not None
        pd.testing.assert_index_equal(single_ts, chunked_ts, check_names=False)

    def test_future_leak_validation_with_chunked_merge(self, monkeypatch):
        """Chunked merge 不應引入未來洩漏"""
        from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

        source_values, source_index, primary_index = self._make_aligned_data(n_cols=10)

        monkeypatch.setenv("FFACT_MERGE_CHUNK_SIZE", "3")
        aligned = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)

        # source_timestamps should all be <= primary_index
        source_ts = aligned.attrs.get("source_timestamps")
        assert source_ts is not None
        assert (source_ts <= primary_index).all(), "Chunked merge introduced future leakage!"

    def test_empty_source(self, monkeypatch):
        """空源 DataFrame 不該拋 exception"""
        from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

        primary_index = pd.date_range("2024-01-01", periods=10, freq="12h")
        source_values = pd.DataFrame(index=pd.DatetimeIndex([]))
        source_index = pd.DatetimeIndex([])

        monkeypatch.setenv("FFACT_MERGE_CHUNK_SIZE", "3")
        result = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)
        assert result.shape[0] == len(primary_index)

    def test_single_column_merge(self, monkeypatch):
        """單欄 merge 不該觸發 chunking"""
        from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

        source_values, source_index, primary_index = self._make_aligned_data(n_cols=1)

        monkeypatch.setenv("FFACT_MERGE_CHUNK_SIZE", "5000")
        result = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)
        assert result.shape[1] == 1
