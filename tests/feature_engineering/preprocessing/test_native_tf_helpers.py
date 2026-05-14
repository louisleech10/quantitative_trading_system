"""Unit tests for momentum.FeatureEngineering.preprocessing._native_tf_helpers."""

from __future__ import annotations

import numpy as np
import pytest

from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
    apply_idx_map_to_array,
    native_tf_enabled,
    scale_preprocessing_config_for_native,
    scale_window_for_native,
    should_use_native_path,
)


# ---------------------------------------------------------------------------
# scale_window_for_native
# ---------------------------------------------------------------------------
class TestScaleWindow:
    def test_same_tf_returns_unchanged(self):
        assert scale_window_for_native(252, "1h", "1h") == 252

    def test_primary_window_scales_to_source_long(self):
        # source=12h, primary=1h: 360 primary 1h-bars → 360*3600/43200 = 30 12h bars
        assert scale_window_for_native(360, "12h", "1h") == 30

    def test_primary_window_scales_to_source_short(self):
        # source=1h, primary=12h: 60 primary 12h-bars → 60*43200/3600 = 720 1h bars
        assert scale_window_for_native(60, "1h", "12h") == 720

    def test_minimum_one_when_collapses_to_zero(self):
        # source=12h, primary=1h, window=1 → round(1*3600/43200)=0 → clamp 1
        assert scale_window_for_native(1, "12h", "1h") == 1

    def test_zero_window_returns_zero(self):
        assert scale_window_for_native(0, "1h", "12h") == 0

    def test_negative_window_returns_zero(self):
        assert scale_window_for_native(-5, "1h", "12h") == 0

    def test_unknown_tf_raises(self):
        with pytest.raises(ValueError):
            scale_window_for_native(100, "unknown", "1h")
        with pytest.raises(ValueError):
            scale_window_for_native(100, "1h", "unknown")

    def test_empty_tf_raises(self):
        with pytest.raises(ValueError):
            scale_window_for_native(100, "", "1h")


# ---------------------------------------------------------------------------
# scale_preprocessing_config_for_native
# ---------------------------------------------------------------------------
class TestScaleConfig:
    def test_same_tf_deep_copy_unchanged(self):
        cfg = {
            "rank_transform": {"window": 252},
            "adaptive_zscore": {"window": 100, "windows": [50, 100, 200]},
        }
        scaled = scale_preprocessing_config_for_native(cfg, "1h", "1h")
        assert scaled is not cfg
        assert scaled["rank_transform"]["window"] == 252
        assert scaled["adaptive_zscore"]["window"] == 100
        assert scaled["adaptive_zscore"]["windows"] == [50, 100, 200]

    def test_native_long_tf_scales_windows(self):
        cfg = {
            "rank_transform": {"window": 360, "enabled": True},
            "adaptive_zscore": {
                "window": 240,
                "windows": [60, 120, 240],
                "enabled": True,
            },
        }
        scaled = scale_preprocessing_config_for_native(cfg, "12h", "1h")
        # 360 / 12 = 30
        assert scaled["rank_transform"]["window"] == 30
        # 240 / 12 = 20
        assert scaled["adaptive_zscore"]["window"] == 20
        # [60/12, 120/12, 240/12] = [5, 10, 20]
        assert scaled["adaptive_zscore"]["windows"] == [5, 10, 20]
        # enabled flags preserved
        assert scaled["rank_transform"]["enabled"] is True
        assert scaled["adaptive_zscore"]["enabled"] is True

    def test_min_clamp_for_small_windows(self):
        cfg = {
            "rank_transform": {"window": 6},
            "adaptive_zscore": {"windows": [6, 12]},
        }
        # 6 / 12 = 0.5 → round = 0 → clamp = 1; 12 / 12 = 1
        scaled = scale_preprocessing_config_for_native(cfg, "12h", "1h")
        assert scaled["rank_transform"]["window"] == 1
        assert scaled["adaptive_zscore"]["windows"] == [1, 1]

    def test_preserves_non_window_fields(self):
        cfg = {
            "fractional_differencing": {
                "sample_size": 5000,
                "max_lag": 50,
                "enabled": True,
            },
            "winsorization": {"lower_q": 0.01, "upper_q": 0.99},
        }
        scaled = scale_preprocessing_config_for_native(cfg, "12h", "1h")
        # Non-window fields untouched
        assert scaled["fractional_differencing"]["sample_size"] == 5000
        assert scaled["fractional_differencing"]["max_lag"] == 50
        assert scaled["winsorization"]["lower_q"] == 0.01

    def test_missing_keys_no_error(self):
        cfg = {"winsorization": {"lower_q": 0.01}}
        scaled = scale_preprocessing_config_for_native(cfg, "12h", "1h")
        assert scaled == cfg
        assert scaled is not cfg

    def test_deep_copy_isolation(self):
        cfg = {"adaptive_zscore": {"windows": [60, 120]}}
        scaled = scale_preprocessing_config_for_native(cfg, "12h", "1h")
        # Mutating scaled does not affect original
        scaled["adaptive_zscore"]["windows"].append(999)
        assert cfg["adaptive_zscore"]["windows"] == [60, 120]


# ---------------------------------------------------------------------------
# apply_idx_map_to_array
# ---------------------------------------------------------------------------
class TestApplyIdxMap:
    def test_basic_expansion_2d(self):
        native = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)
        # primary rows: [0, 0, 1, 1, 2, 2]  (each native row repeated twice)
        idx_map = np.array([0, 0, 1, 1, 2, 2], dtype=np.int64)
        result = apply_idx_map_to_array(native, idx_map, primary_n_rows=6)
        assert result.shape == (6, 2)
        assert result.dtype == np.float32
        np.testing.assert_array_equal(
            result, np.array([[1, 2], [1, 2], [3, 4], [3, 4], [5, 6], [5, 6]],
                             dtype=np.float32))

    def test_unfilled_gaps_become_nan(self):
        native = np.array([[10.0]], dtype=np.float32)
        idx_map = np.array([-1, 0, -1], dtype=np.int64)
        result = apply_idx_map_to_array(native, idx_map, primary_n_rows=3)
        assert np.isnan(result[0, 0])
        assert result[1, 0] == 10.0
        assert np.isnan(result[2, 0])

    def test_all_negative_returns_all_nan(self):
        native = np.array([[1.0]], dtype=np.float32)
        idx_map = np.array([-1, -1, -1], dtype=np.int64)
        result = apply_idx_map_to_array(native, idx_map, primary_n_rows=3)
        assert np.all(np.isnan(result))

    def test_1d_native_raises(self):
        native = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        idx_map = np.array([0, 1, 2, 2], dtype=np.int64)
        with pytest.raises(ValueError):
            apply_idx_map_to_array(native, idx_map, primary_n_rows=4)

    def test_zero_primary_rows(self):
        native = np.array([[1.0]], dtype=np.float32)
        idx_map = np.array([], dtype=np.int64)
        result = apply_idx_map_to_array(native, idx_map, primary_n_rows=0)
        assert result.shape == (0, 1)

    def test_invalid_native_ndim_raises(self):
        native = np.zeros((2, 2, 2), dtype=np.float32)
        idx_map = np.array([0], dtype=np.int64)
        with pytest.raises(ValueError):
            apply_idx_map_to_array(native, idx_map, 1)

    def test_idx_out_of_range_raises(self):
        native = np.array([[1.0]], dtype=np.float32)
        idx_map = np.array([0, 5], dtype=np.int64)  # 5 >= source_n_rows (1)
        with pytest.raises(ValueError):
            apply_idx_map_to_array(native, idx_map, primary_n_rows=2)

    def test_negative_idx_other_than_minus_one_treated_as_gap(self):
        native = np.array([[1.0]], dtype=np.float32)
        idx_map = np.array([0, -2], dtype=np.int64)
        result = apply_idx_map_to_array(native, idx_map, primary_n_rows=2)
        assert result[0, 0] == 1.0
        assert np.isnan(result[1, 0])

    def test_large_block_copy(self):
        # Exceeds _ROW_BLOCK=1024 to validate block-iterate logic.
        n_native = 10
        n_cols = 3
        native = np.arange(n_native * n_cols, dtype=np.float32).reshape(n_native, n_cols)
        n_primary = 3000
        idx_map = (np.arange(n_primary) // (n_primary // n_native)).clip(0, n_native - 1).astype(np.int64)
        result = apply_idx_map_to_array(native, idx_map, primary_n_rows=n_primary)
        assert result.shape == (n_primary, n_cols)
        # Sample check: rows mapping to native index 0 must equal native[0]
        zero_rows = np.where(idx_map == 0)[0]
        np.testing.assert_array_equal(result[zero_rows[0]], native[0])

    def test_preserves_float32_dtype(self):
        native = np.array([[1.0]], dtype=np.float64)
        idx_map = np.array([0], dtype=np.int64)
        result = apply_idx_map_to_array(native, idx_map, primary_n_rows=1)
        assert result.dtype == np.float32


# ---------------------------------------------------------------------------
# should_use_native_path
# ---------------------------------------------------------------------------
class TestShouldUseNativePath:
    def _config_with_fracdiff(self):
        return {"fractional_differencing": {"enabled": True}}

    def test_happy_path(self):
        ok, reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=1696,
            scaled_config=self._config_with_fracdiff(),
            flag_enabled=True,
        )
        assert ok is True
        assert reason == "ok"

    def test_not_compact(self):
        ok, reason = should_use_native_path(
            is_compact_aligned=False,
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=1696,
            scaled_config=self._config_with_fracdiff(),
            flag_enabled=True,
        )
        assert ok is False
        assert "not_compact" in reason

    def test_flag_disabled(self):
        ok, reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=1696,
            scaled_config=self._config_with_fracdiff(),
            flag_enabled=False,
        )
        assert ok is False
        assert "flag" in reason.lower()

    def test_same_tf_no_benefit(self):
        ok, reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe="1h",
            primary_timeframe="1h",
            source_n_rows=10000,
            scaled_config=self._config_with_fracdiff(),
            flag_enabled=True,
        )
        assert ok is False
        assert "same_tf" in reason or "no_benefit" in reason

    def test_too_few_native_rows(self):
        ok, reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe="1d",
            primary_timeframe="1h",
            source_n_rows=10,  # below _MIN_NATIVE_ROWS=50
            scaled_config=self._config_with_fracdiff(),
            flag_enabled=True,
        )
        assert ok is False
        assert "native_rows" in reason

    def test_missing_tf_falls_back(self):
        ok, reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe=None,
            primary_timeframe="1h",
            source_n_rows=1696,
            scaled_config=self._config_with_fracdiff(),
            flag_enabled=True,
        )
        assert ok is False
        assert "missing_tf" in reason


# ---------------------------------------------------------------------------
# native_tf_enabled flag
# ---------------------------------------------------------------------------
class TestNativeTfEnabled:
    def test_default_enabled(self, monkeypatch):
        monkeypatch.delenv("FFACT_L65_NATIVE_TF", raising=False)
        assert native_tf_enabled() is True

    def test_disabled_by_zero(self, monkeypatch):
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "0")
        assert native_tf_enabled() is False

    def test_disabled_by_false(self, monkeypatch):
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "false")
        assert native_tf_enabled() is False

    def test_enabled_by_one(self, monkeypatch):
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        assert native_tf_enabled() is True
