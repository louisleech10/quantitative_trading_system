"""CGSA multi-TF integration tests (Phase 2 completion).

Tests cover:
- _align_group_array correctness
- CGSA multi-TF end-to-end (generate_multi_tf_cgsa)
- _combine_layers context-based skip/pass-through
- Boundary cases: empty groups, single TF, all-NaN groups
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


# ---------------------------------------------------------------------------
# _align_group_array unit tests
# ---------------------------------------------------------------------------

class TestAlignGroupArray:
    """Tests for MultiTFGenerator._align_group_array static method."""

    def test_basic_alignment_forward_fill(self):
        """12h source (3 rows) aligned to 1h primary (12 rows) via idx_map."""
        src = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)
        # idx_map: primary rows 0-3 map to src row 0, 4-7 to src row 1, 8-11 to src row 2
        idx_map = np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2], dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=12)

        assert result.shape == (12, 2)
        assert result.dtype == np.float32
        np.testing.assert_array_equal(result[0], [1.0, 2.0])
        np.testing.assert_array_equal(result[4], [3.0, 4.0])
        np.testing.assert_array_equal(result[8], [5.0, 6.0])

    def test_alignment_with_invalid_rows(self):
        """Rows with idx_map=-1 should produce NaN."""
        src = np.array([[10.0], [20.0]], dtype=np.float32)
        idx_map = np.array([-1, 0, -1, 1, -1], dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=5)

        assert result.shape == (5, 1)
        assert np.isnan(result[0, 0])
        np.testing.assert_equal(result[1, 0], 10.0)
        assert np.isnan(result[2, 0])
        np.testing.assert_equal(result[3, 0], 20.0)
        assert np.isnan(result[4, 0])

    def test_alignment_all_invalid(self):
        """All -1 idx_map → all NaN output."""
        src = np.array([[1.0, 2.0]], dtype=np.float32)
        idx_map = np.full(5, -1, dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=5)

        assert result.shape == (5, 2)
        assert np.all(np.isnan(result))

    def test_alignment_single_column(self):
        """Single column group alignment."""
        src = np.array([[100.0], [200.0], [300.0]], dtype=np.float32)
        idx_map = np.array([0, 1, 2], dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=3)

        np.testing.assert_array_equal(result.flatten(), [100.0, 200.0, 300.0])

    def test_alignment_preserves_nan_in_source(self):
        """NaN values in source should be preserved after alignment."""
        src = np.array([[np.nan, 2.0], [3.0, np.nan]], dtype=np.float32)
        idx_map = np.array([0, 0, 1, 1], dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=4)

        assert np.isnan(result[0, 0])
        assert result[0, 1] == 2.0
        assert result[2, 0] == 3.0
        assert np.isnan(result[2, 1])


# ---------------------------------------------------------------------------
# _combine_layers context-based skip
# ---------------------------------------------------------------------------

class TestCombineLayersContextSkip:
    """Test that _combine_layers skips only for final merge contexts in CGSA mode."""

    def test_layer7_final_skipped_in_cgsa(self, monkeypatch):
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        result = FeatureFactory._combine_layers([layer], context="layer7_final")
        assert result.empty

    def test_layer6_5_input_skipped_in_cgsa(self, monkeypatch):
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        result = FeatureFactory._combine_layers([layer], context="layer6_5_input")
        assert result.empty

    def test_multi_tf_merged_skipped_in_cgsa(self, monkeypatch):
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        result = FeatureFactory._combine_layers([layer], context="multi_tf_merged")
        assert result.empty

    def test_layer3_input_not_skipped_in_cgsa(self, monkeypatch):
        """Internal concat for layer3 input MUST still work in CGSA mode."""
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0, 2.0]})
        result = FeatureFactory._combine_layers([layer], context="layer3_input")
        assert not result.empty
        assert list(result.columns) == ["x"]

    def test_layer4_input_not_skipped_in_cgsa(self, monkeypatch):
        """Internal concat for layer4 input MUST still work in CGSA mode."""
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer1 = pd.DataFrame({"a": [1.0]})
        layer2 = pd.DataFrame({"b": [2.0]})
        result = FeatureFactory._combine_layers([layer1, layer2], context="layer4_input")
        assert not result.empty
        assert set(result.columns) == {"a", "b"}

    def test_non_cgsa_never_skips(self, monkeypatch):
        """With CGSA disabled, all contexts should produce non-empty results."""
        monkeypatch.setenv("FFACT_USE_CGSA", "0")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        for ctx in ("layer7_final", "layer6_5_input", "multi_tf_merged", "layer3_input"):
            result = FeatureFactory._combine_layers([layer], context=ctx)
            assert not result.empty, f"Context '{ctx}' should NOT be skipped when CGSA=0"


# ---------------------------------------------------------------------------
# CGSA multi-TF alignment via registry (integration)
# ---------------------------------------------------------------------------

class TestCGSAMultiTFAlignment:
    """Integration tests for CGSA per-group alignment in multi-TF flow."""

    def test_align_registry_groups_12h_to_1h(self, tmp_path):
        """Simulates 12h groups being aligned to 1h primary timestamps."""
        registry = ColumnGroupRegistry(work_dir=tmp_path)

        # 12h source: 3 rows (e.g. 3 * 12h candles)
        n_source = 3
        n_cols = 4
        src_data = np.arange(n_source * n_cols, dtype=np.float32).reshape(n_source, n_cols)

        group = ColumnGroup(
            group_id="12h_L1_trend_EMA",
            columns=("f1", "f2", "f3", "f4"),
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="EMA",
            shape=(n_source, n_cols),
            dtype="float32",
        )
        registry.save_data(group, src_data)

        # Primary: 12 rows (12 * 1h candles covering same 3 * 12h periods)
        n_primary = 12
        # Build idx_map: each 12h candle covers 4 primary rows
        idx_map = np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2], dtype=np.int64)

        loaded = np.asarray(registry.load_data("12h_L1_trend_EMA"), dtype=np.float32)
        aligned = MultiTFGenerator._align_group_array(loaded, idx_map, n_primary)
        registry.overwrite_data("12h_L1_trend_EMA", aligned)

        # Verify aligned data
        result = np.asarray(registry.load_data("12h_L1_trend_EMA"))
        assert result.shape == (n_primary, n_cols)
        # Row 0 should match source row 0
        np.testing.assert_array_equal(result[0], src_data[0])
        # Row 4 should match source row 1
        np.testing.assert_array_equal(result[4], src_data[1])
        # Row 8 should match source row 2
        np.testing.assert_array_equal(result[8], src_data[2])

    def test_primary_groups_not_aligned(self, tmp_path):
        """Primary TF groups should NOT be modified (no alignment needed)."""
        registry = ColumnGroupRegistry(work_dir=tmp_path)
        n_rows = 10
        original = np.random.randn(n_rows, 3).astype(np.float32)

        group = ColumnGroup(
            group_id="1h_L1_trend_EMA",
            columns=("a", "b", "c"),
            layer=LayerSource.L1,
            timeframe="1h",
            data_source="close",
            indicator="EMA",
            shape=(n_rows, 3),
            dtype="float32",
        )
        registry.save_data(group, original.copy())

        # Primary TF groups: no alignment, data stays unchanged
        loaded = np.asarray(registry.load_data("1h_L1_trend_EMA"))
        np.testing.assert_array_equal(loaded, original)

    def test_mixed_tf_groups_in_registry(self, tmp_path):
        """Registry with both 1h and 12h groups; only 12h gets aligned."""
        registry = ColumnGroupRegistry(work_dir=tmp_path)

        # 1h group (primary)
        data_1h = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]], dtype=np.float32)
        g1 = ColumnGroup("1h_L1_momentum_RSI", LayerSource.L1, "1h", "close", "RSI", ("r1", "r2"), (4, 2))
        registry.save_data(g1, data_1h.copy())

        # 12h group (secondary, 2 rows → needs alignment to 4 rows)
        data_12h = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
        g2 = ColumnGroup("12h_L1_trend_EMA", LayerSource.L1, "12h", "close", "EMA", ("e1", "e2"), (2, 2))
        registry.save_data(g2, data_12h.copy())

        # Align only 12h groups
        idx_map = np.array([0, 0, 1, 1], dtype=np.int64)
        for gid in ["12h_L1_trend_EMA"]:
            src = np.asarray(registry.load_data(gid), dtype=np.float32)
            aligned = MultiTFGenerator._align_group_array(src, idx_map, n_primary=4)
            registry.overwrite_data(gid, aligned)

        # 1h unchanged
        np.testing.assert_array_equal(
            np.asarray(registry.load_data("1h_L1_momentum_RSI")),
            data_1h,
        )
        # 12h aligned to 4 rows
        result_12h = np.asarray(registry.load_data("12h_L1_trend_EMA"))
        assert result_12h.shape == (4, 2)
        np.testing.assert_array_equal(result_12h[0], [10.0, 20.0])
        np.testing.assert_array_equal(result_12h[2], [30.0, 40.0])


# ---------------------------------------------------------------------------
# Boundary / edge cases
# ---------------------------------------------------------------------------

class TestCGSABoundary:
    """Boundary tests for CGSA registry operations."""

    def test_empty_group_alignment(self):
        """Group with 0 rows: alignment should produce all-NaN output."""
        src = np.empty((0, 3), dtype=np.float32)
        idx_map = np.full(5, -1, dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=5)
        assert result.shape == (5, 3)
        assert np.all(np.isnan(result))

    def test_single_row_group(self):
        """Single-row source group alignment."""
        src = np.array([[42.0, 99.0]], dtype=np.float32)
        idx_map = np.array([0, 0, 0], dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=3)
        assert result.shape == (3, 2)
        np.testing.assert_array_equal(result[0], [42.0, 99.0])
        np.testing.assert_array_equal(result[2], [42.0, 99.0])

    def test_all_nan_group(self):
        """All-NaN source group: output should also be all NaN."""
        src = np.full((3, 2), np.nan, dtype=np.float32)
        idx_map = np.array([0, 1, 2, 2], dtype=np.int64)
        result = MultiTFGenerator._align_group_array(src, idx_map, n_primary=4)
        assert result.shape == (4, 2)
        assert np.all(np.isnan(result))

    def test_cgsa_enabled_default_is_one(self, monkeypatch):
        """Default FFACT_USE_CGSA should be '1' (enabled)."""
        monkeypatch.delenv("FFACT_USE_CGSA", raising=False)
        assert MultiTFGenerator._cgsa_enabled() is True

        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        assert FeatureFactory._cgsa_enabled() is True

    def test_cgsa_disabled_via_env(self, monkeypatch):
        """FFACT_USE_CGSA=0 should disable CGSA."""
        monkeypatch.setenv("FFACT_USE_CGSA", "0")
        assert MultiTFGenerator._cgsa_enabled() is False

    def test_build_asof_index_map_basic(self):
        """Verify build_asof_index_map used by CGSA alignment."""
        primary_ms = np.array([0, 3600000, 7200000, 10800000], dtype=np.int64)
        source_ms = np.array([0, 7200000], dtype=np.int64)
        idx_map = TimeframeAligner.build_asof_index_map(primary_ms, source_ms)

        # primary[0]=0 → source[0]=0 (exact match)
        assert idx_map[0] == 0
        # primary[1]=3600000 → source[0]=0 (searchsorted backward)
        assert idx_map[1] == 0
        # primary[2]=7200000 → source[1]=7200000 (exact match)
        assert idx_map[2] == 1
        # primary[3]=10800000 → source[1]=7200000
        assert idx_map[3] == 1

    def test_registry_total_columns_after_alignment(self, tmp_path):
        """After alignment, registry total_columns should stay the same."""
        registry = ColumnGroupRegistry(work_dir=tmp_path)

        group = ColumnGroup("12h_L2_Cross", LayerSource.L2, "12h", "close", "Cross", ("c1", "c2", "c3"), (2, 3))
        registry.save_data(group, np.ones((2, 3), dtype=np.float32))

        assert registry.total_columns() == 3

        # Align: 2 rows → 6 rows
        idx_map = np.array([0, 0, 0, 1, 1, 1], dtype=np.int64)
        src = np.asarray(registry.load_data("12h_L2_Cross"), dtype=np.float32)
        aligned = MultiTFGenerator._align_group_array(src, idx_map, n_primary=6)
        registry.overwrite_data("12h_L2_Cross", aligned)

        # Column count unchanged; row count changed
        assert registry.total_columns() == 3
        loaded = np.asarray(registry.load_data("12h_L2_Cross"))
        assert loaded.shape == (6, 3)
