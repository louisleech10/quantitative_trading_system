"""Integration tests for native-resolution L6.5 path on compact-aligned groups.

Validates:
- Native path produces expanded primary-shape output identical in shape to legacy.
- Native path stats differ from legacy when source TF != primary TF (because
  L6.5 is computed on source rows, not the step-replicated primary rows).
- Backward compatibility: flag=0 disables the native path bit-for-bit.
- Fallback when native rows < threshold or alignment is missing.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import (
    AlignmentMeta,
    ColumnGroup,
    LayerSource,
)
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
    FeaturePreprocessor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _write_idx_map(path: Path, idx_map: np.ndarray) -> Path:
    np.save(path, np.asarray(idx_map, dtype=np.int32), allow_pickle=False)
    return path


def _make_compact_registry(
    tmp_path: Path,
    *,
    source: np.ndarray,
    idx_map: np.ndarray,
    columns: tuple[str, ...] = ("a", "b"),
    group_id: str = "12h_L1_compact",
) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(tmp_path / "work")
    source_path = registry.work_dir / f"{group_id}.npy"
    np.save(source_path, source.astype(np.float32, copy=False), allow_pickle=False)
    idx_map_path = _write_idx_map(
        registry.work_dir / ".align_12h_to_1h_close_time.npy", idx_map
    )
    group = ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="close",
        indicator="TEST",
        columns=columns,
        shape=(len(idx_map), source.shape[1]),
        dtype="float32",
        disk_path=source_path,
        alignment=AlignmentMeta(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=source.shape[0],
            primary_n_rows=len(idx_map),
            idx_map_path=idx_map_path,
            alignment_mode="close_time",
            offset_ns=0,
        ),
    )
    registry.register(group)
    registry.write_manifest()
    return registry


def _make_synthetic_native_data(n_native: int, n_cols: int, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # AR(1) series so winsorization / zscore have realistic distribution.
    eps = rng.standard_normal((n_native, n_cols)).astype(np.float32)
    out = np.empty_like(eps)
    out[0] = eps[0]
    for t in range(1, n_native):
        out[t] = 0.85 * out[t - 1] + 0.15 * eps[t]
    return out


def _make_idx_map_uniform(n_native: int, ratio: int) -> np.ndarray:
    """Each native row maps to exactly `ratio` consecutive primary rows."""
    n_primary = n_native * ratio
    return np.repeat(np.arange(n_native, dtype=np.int32), ratio)


def _basic_l65_config() -> dict:
    """Config with rank + zscore enabled (no fracdiff/ADF — keep test fast)."""
    return {
        "enabled": True,
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "lower_q": 0.01,
            "upper_q": 0.99,
        },
        "rank_transform": {
            "enabled": True,
            "window": 240,  # primary 1h units → scaled to 20 in 12h source
        },
        "adaptive_zscore": {
            "enabled": True,
            "windows": [120, 240],  # primary → [10, 20]
        },
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestNativePathInPlace:
    def test_native_path_runs_and_writes_primary_shape(self, tmp_path, monkeypatch):
        """Native path should produce primary-shape (n_primary, n_cols) output."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        n_native = 200
        n_cols = 3
        ratio = 12
        source = _make_synthetic_native_data(n_native, n_cols)
        idx_map = _make_idx_map_uniform(n_native, ratio)

        registry = _make_compact_registry(
            tmp_path,
            source=source,
            idx_map=idx_map,
            columns=tuple(f"col_{i}" for i in range(n_cols)),
        )
        n_primary = n_native * ratio

        config = _basic_l65_config()
        preprocessor = FeaturePreprocessor(config)
        completed = preprocessor.transform_registry_groups(registry, n_workers=1)

        assert completed == 1
        result = registry.load_data("12h_L1_compact")
        assert result.shape == (n_primary, n_cols)
        # Should not be all NaN — rank/zscore on real data must produce values.
        finite_ratio = np.isfinite(result).mean()
        assert finite_ratio > 0.5

    def test_flag_off_uses_legacy_path(self, tmp_path, monkeypatch):
        """With FFACT_L65_NATIVE_TF=0 the legacy expand-then-transform runs."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "0")
        n_native = 200
        n_cols = 2
        ratio = 12
        source = _make_synthetic_native_data(n_native, n_cols)
        idx_map = _make_idx_map_uniform(n_native, ratio)

        registry = _make_compact_registry(
            tmp_path, source=source, idx_map=idx_map
        )

        config = _basic_l65_config()
        preprocessor = FeaturePreprocessor(config)
        completed = preprocessor.transform_registry_groups(registry, n_workers=1)
        assert completed == 1
        result = registry.load_data("12h_L1_compact")
        assert result.shape == (n_native * ratio, n_cols)

    def test_native_vs_legacy_differ_for_compact_groups(self, tmp_path, monkeypatch):
        """The whole point: native and legacy paths SHOULD produce different stats."""
        n_native = 200
        n_cols = 2
        ratio = 12
        source = _make_synthetic_native_data(n_native, n_cols)
        idx_map = _make_idx_map_uniform(n_native, ratio)

        # Run with flag=0 (legacy)
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "0")
        legacy_reg = _make_compact_registry(
            tmp_path / "legacy", source=source, idx_map=idx_map
        )
        FeaturePreprocessor(_basic_l65_config()).transform_registry_groups(
            legacy_reg, n_workers=1
        )
        legacy_result = legacy_reg.load_data("12h_L1_compact").copy()

        # Run with flag=1 (native)
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        native_reg = _make_compact_registry(
            tmp_path / "native", source=source, idx_map=idx_map
        )
        FeaturePreprocessor(_basic_l65_config()).transform_registry_groups(
            native_reg, n_workers=1
        )
        native_result = native_reg.load_data("12h_L1_compact")

        assert legacy_result.shape == native_result.shape
        # Both should have finite values
        legacy_finite = np.isfinite(legacy_result)
        native_finite = np.isfinite(native_result)
        common_mask = legacy_finite & native_finite
        assert common_mask.sum() > 0
        # Statistics differ because rank/zscore on step-series vs native series
        # produce different results — at least one column must show meaningful diff.
        diffs = np.abs(legacy_result[common_mask] - native_result[common_mask])
        max_diff = float(np.nanmax(diffs)) if diffs.size > 0 else 0.0
        assert max_diff > 1e-3, (
            f"Expected native vs legacy to differ for compact groups, "
            f"max_diff={max_diff}"
        )

    def test_too_few_native_rows_fallback(self, tmp_path, monkeypatch):
        """Native rows < 50 → falls back to legacy path (no error)."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        n_native = 10  # below _MIN_NATIVE_ROWS=50
        n_cols = 2
        ratio = 12
        source = _make_synthetic_native_data(n_native, n_cols)
        idx_map = _make_idx_map_uniform(n_native, ratio)

        registry = _make_compact_registry(
            tmp_path, source=source, idx_map=idx_map
        )

        config = _basic_l65_config()
        preprocessor = FeaturePreprocessor(config)
        completed = preprocessor.transform_registry_groups(registry, n_workers=1)
        assert completed == 1
        result = registry.load_data("12h_L1_compact")
        # Falls back to legacy expand path; output stays primary-shape.
        assert result.shape == (n_native * ratio, n_cols)


class TestNonCompactGroupUnaffected:
    def test_non_compact_group_flag_independent(self, tmp_path, monkeypatch):
        """Non-compact (no alignment) groups must behave identically with flag on/off."""
        n_rows = 300
        n_cols = 2
        rng = np.random.default_rng(123)
        data = rng.standard_normal((n_rows, n_cols)).astype(np.float32)

        def _build_and_run(flag_value: str) -> np.ndarray:
            monkeypatch.setenv("FFACT_L65_NATIVE_TF", flag_value)
            registry = ColumnGroupRegistry(tmp_path / f"work_{flag_value}")
            group = ColumnGroup(
                group_id="g1",
                layer=LayerSource.L1,
                timeframe="1h",
                data_source="close",
                indicator="TEST",
                columns=("a", "b"),
                shape=(n_rows, n_cols),
                dtype="float32",
            )
            registry.save_data(group, data.copy())
            FeaturePreprocessor(_basic_l65_config()).transform_registry_groups(
                registry, n_workers=1
            )
            return registry.load_data("g1")

        out_off = _build_and_run("0")
        out_on = _build_and_run("1")

        assert out_off.shape == out_on.shape == (n_rows, n_cols)
        # Non-compact: no native-path eligibility → bit-for-bit equivalent.
        np.testing.assert_array_equal(out_off, out_on)


class TestRawSinkPath:
    def test_native_path_via_to_sink(self, tmp_path, monkeypatch):
        """Native path also works when called via transform_registry_groups_to_sink."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        n_native = 200
        n_cols = 2
        ratio = 12
        source = _make_synthetic_native_data(n_native, n_cols)
        idx_map = _make_idx_map_uniform(n_native, ratio)

        registry = _make_compact_registry(
            tmp_path, source=source, idx_map=idx_map
        )
        n_primary = n_native * ratio

        captured: dict = {}

        def _sink(out_group_id, out_columns, out_data, source_group_id,
                  source_disk_path, finalize):
            captured.setdefault(out_group_id, []).append(
                (list(out_columns), np.asarray(out_data).shape, finalize)
            )

        config = _basic_l65_config()
        preprocessor = FeaturePreprocessor(config)
        n_groups = preprocessor.transform_registry_groups_to_sink(
            registry, _sink, n_workers=1
        )

        assert n_groups == 1
        assert "12h_L1_compact" in captured
        outs = captured["12h_L1_compact"]
        assert len(outs) >= 1
        cols, shape, finalize = outs[0]
        assert shape == (n_primary, n_cols)
        assert finalize is True
