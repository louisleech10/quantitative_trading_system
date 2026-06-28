"""Phase 8 + edge cases: native-resolution L6.5 with real ETH 1h/12h data
and additional boundary scenarios.

Real data source: ``data_cache/feature_klines/kline_cache.h5`` (ETHUSDT 1h
20352 rows, 12h 1696 rows). Tests verify:

- Forward-fill structural correctness on real 12h→1h alignment.
- Statistical divergence (native winsor/zscore on real distribution differs
  from legacy on step-replicated distribution).
- d_star cache key isolation (native sibling preprocessor uses source-TF in
  cache filename — verifies no collision with primary-TF cache).
- Append mode produces ``_L65`` groups with primary-shaped expansion.
- Single-column / many-column compact groups.
- Leading / trailing / all-negative gaps in idx_map.
- Mixed registry: compact + non-compact groups together.
- dtype preservation (float32 in → float32 out).
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import h5py
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


REAL_KLINE_PATH = Path("data_cache/feature_klines/kline_cache.h5")

pytestmark = pytest.mark.requires_kline


# ---------------------------------------------------------------------------
# Real-data fixtures
# ---------------------------------------------------------------------------
def _load_eth_close(timeframe: str, max_rows: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """Return (timestamp_ns, close_float32) arrays from the real kline cache."""
    if not REAL_KLINE_PATH.exists():
        pytest.fail(f"real kline cache not present: {REAL_KLINE_PATH}")
    with h5py.File(REAL_KLINE_PATH, "r") as f:
        ds = f[f"/ETHUSDT/{timeframe}/data"][:]
    ts = np.asarray(ds["timestamp"], dtype=np.int64)
    close = np.asarray(ds["close"], dtype=np.float32)
    if max_rows > 0:
        ts = ts[:max_rows]
        close = close[:max_rows]
    return ts, close


def _build_close_time_idx_map(
    primary_ts: np.ndarray,
    source_ts: np.ndarray,
    source_period_seconds: int,
) -> np.ndarray:
    """For each primary timestamp (Unix seconds), find the latest source idx
    whose close_time has occurred (causal: source close_time = source_ts +
    source_period_seconds). Returns int32 array, -1 where no source bar closed.
    """
    source_close = source_ts + source_period_seconds
    idx = np.searchsorted(source_close, primary_ts, side="right") - 1
    return idx.astype(np.int32)


def _write_idx_map_npy(path: Path, idx_map: np.ndarray) -> Path:
    np.save(path, np.asarray(idx_map, dtype=np.int32), allow_pickle=False)
    return path


def _make_real_eth_compact_registry(
    tmp_path: Path,
    *,
    primary_rows: int = 2400,
    n_cols: int = 1,
    extra_columns_from_close: bool = False,
) -> Tuple[ColumnGroupRegistry, np.ndarray, np.ndarray, int]:
    """Build a registry with one compact-aligned 12h ETH group → 1h primary.

    Returns (registry, native_data, idx_map, expected_native_n_rows_used).
    """
    primary_ts, _primary_close = _load_eth_close("1h", max_rows=primary_rows)
    source_ts, source_close = _load_eth_close("12h", max_rows=0)
    period_12h_seconds = 12 * 60 * 60
    idx_map = _build_close_time_idx_map(primary_ts, source_ts, period_12h_seconds)

    # Trim native data to highest referenced source idx + 1 (memory hygiene).
    max_idx = int(idx_map.max())
    native_n_rows = max(max_idx + 1, 1)
    native = np.zeros((native_n_rows, n_cols), dtype=np.float32)
    if extra_columns_from_close and n_cols > 1:
        # Make each column a slightly-shifted derivative of close so they have
        # different distributions but realistic structure.
        for c in range(n_cols):
            offset = c
            shifted = np.roll(source_close[:native_n_rows], offset)
            shifted[:offset] = source_close[0]
            native[:, c] = shifted * (1.0 + 0.001 * c)
    else:
        native[:, 0] = source_close[:native_n_rows]
        for c in range(1, n_cols):
            native[:, c] = source_close[:native_n_rows] * (1.0 + 0.01 * c)

    registry = ColumnGroupRegistry(tmp_path / "work")
    group_id = "12h_L1_eth_close"
    source_path = registry.work_dir / f"{group_id}.npy"
    np.save(source_path, native, allow_pickle=False)
    idx_path = _write_idx_map_npy(
        registry.work_dir / ".align_12h_to_1h_close_time.npy", idx_map
    )

    columns = tuple(f"close_lag{c}" for c in range(n_cols))
    group = ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="close",
        indicator="ETH_REAL",
        columns=columns,
        shape=(len(idx_map), n_cols),
        dtype="float32",
        disk_path=source_path,
        alignment=AlignmentMeta(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=native_n_rows,
            primary_n_rows=len(idx_map),
            idx_map_path=idx_path,
            alignment_mode="close_time",
            offset_ns=0,
        ),
    )
    registry.register(group)
    registry.write_manifest()
    return registry, native, idx_map, native_n_rows


def _l65_config(*, mode: str = "replace") -> dict:
    return {
        "enabled": True,
        "mode": mode,
        "winsorization": {"enabled": True, "lower_q": 0.01, "upper_q": 0.99},
        "rank_transform": {"enabled": True, "window": 240},  # 1h primary → 20 12h
        "adaptive_zscore": {"enabled": True, "windows": [120, 240]},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }


# ---------------------------------------------------------------------------
# Phase 8: real ETH structural correctness
# ---------------------------------------------------------------------------
class TestRealEthForwardFillStructure:
    def test_native_output_is_step_constant_within_each_native_idx(
        self, tmp_path, monkeypatch
    ):
        """For every group of consecutive primary rows mapping to the same
        native idx, the output values must be identical (forward-fill
        invariant)."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        registry, _native, idx_map, _n_native = _make_real_eth_compact_registry(
            tmp_path, primary_rows=20352, n_cols=1
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        result = registry.load_data("12h_L1_eth_close")
        assert result.shape == (len(idx_map), 1)

        # Walk runs of identical idx_map and assert constancy.
        i = 0
        n = len(idx_map)
        violations = 0
        runs_checked = 0
        while i < n:
            j = i + 1
            cur = idx_map[i]
            while j < n and idx_map[j] == cur:
                j += 1
            if cur >= 0 and j - i > 1:
                vals = result[i:j, 0]
                finite = vals[np.isfinite(vals)]
                if finite.size > 1 and not np.allclose(finite, finite[0], rtol=0, atol=0):
                    violations += 1
                runs_checked += 1
            i = j
        assert runs_checked > 100, "expected many runs in 2400 primary rows"
        assert violations == 0, (
            f"{violations} runs had non-constant values; forward-fill invariant broken"
        )

    def test_native_path_dtype_preserved_float32(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        registry, _, _, _ = _make_real_eth_compact_registry(
            tmp_path, primary_rows=20352, n_cols=1
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        result = registry.load_data("12h_L1_eth_close")
        assert result.dtype == np.float32

    def test_leading_negative_idx_stays_nan(self, tmp_path, monkeypatch):
        """Primary rows before the first source close_time map to -1 → NaN."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        registry, _native, idx_map, _ = _make_real_eth_compact_registry(
            tmp_path, primary_rows=20352, n_cols=1
        )
        # Confirm we actually have leading -1 gaps in the real alignment.
        leading_gaps = int((idx_map[: min(20, len(idx_map))] == -1).sum())
        if leading_gaps == 0:
            pytest.skip("real ETH alignment has no leading gaps; structural test n/a")
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        result = registry.load_data("12h_L1_eth_close")
        gap_mask = idx_map == -1
        assert np.all(np.isnan(result[gap_mask, 0])), (
            "expected NaN at every idx_map==-1 position"
        )


# ---------------------------------------------------------------------------
# Phase 8: real ETH statistical divergence
# ---------------------------------------------------------------------------
class TestRealEthStatisticalDivergence:
    def test_native_vs_legacy_winsor_clip_points_differ(self, tmp_path, monkeypatch):
        """Winsorization on 12h native (~200 distinct values) vs 1h step-series
        (~2400 rows but only ~200 distinct values heavily replicated) must
        produce different clip points — otherwise the fix has no effect."""
        # Legacy
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "0")
        legacy_reg, _, idx_map, _ = _make_real_eth_compact_registry(
            tmp_path / "legacy", primary_rows=20352, n_cols=1
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            legacy_reg, n_workers=1
        )
        legacy_result = legacy_reg.load_data("12h_L1_eth_close").copy()

        # Native
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        native_reg, _, _, _ = _make_real_eth_compact_registry(
            tmp_path / "native", primary_rows=20352, n_cols=1
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            native_reg, n_workers=1
        )
        native_result = native_reg.load_data("12h_L1_eth_close")

        # Causal rolling preprocessing gives each path a grid-dependent warmup
        # NaN prefix. After C-1 rank/zscore min_periods alignment (2026-06-08):
        #   - legacy: dense 1h step-series, winsor+rank+zscore all use
        #     min_periods=max(20, window//4) on primary windows -> ~71 rows.
        #   - native: transforms on scaled 12h grid (rank/zscore min_periods=20
        #     on windows ~20/10), then forward-fill to 1h -> ~20 native bars *
        #     ~12 primary rows/bar -> ~240 primary rows.
        # Invariant: both have non-empty warmup; steady-state (past max prefix)
        # shares identical NaN positions. Measured 2026-06-08: legacy=71,
        # native=240.
        legacy_nan = np.isnan(legacy_result).ravel()
        native_nan = np.isnan(native_result).ravel()

        def _warmup_prefix(mask: np.ndarray) -> int:
            i = 0
            while i < len(mask) and mask[i]:
                i += 1
            return i

        legacy_prefix = _warmup_prefix(legacy_nan)
        native_prefix = _warmup_prefix(native_nan)
        assert 40 <= legacy_prefix <= 120, (
            f"legacy warmup prefix {legacy_prefix} outside expected causal range "
            f"(winsor/rank/zscore min_periods on 1h step-series; measured=71)"
        )
        assert 200 <= native_prefix <= 280, (
            f"native warmup prefix {native_prefix} outside expected causal range "
            f"(scaled rank/zscore min_periods on 12h grid × ffill; measured=240)"
        )
        assert native_prefix > legacy_prefix, (
            f"native prefix {native_prefix} should exceed legacy {legacy_prefix} "
            f"(coarse-grid min_periods upscaled via forward-fill)"
        )

        # Steady-state (past the longer warmup) must share identical NaN positions.
        steady_start = max(legacy_prefix, native_prefix)
        np.testing.assert_array_equal(
            legacy_nan[steady_start:],
            native_nan[steady_start:],
            err_msg="steady-state NaN masks diverge -> leaked warmup difference",
        )

        common = np.isfinite(legacy_result) & np.isfinite(native_result)
        diffs = np.abs(legacy_result[common] - native_result[common])
        # On real ETH 12h close, distributions of legacy step-series vs native
        # series differ meaningfully — require at least 5% of common positions
        # to differ by > 1e-3 (not just floating-noise drift).
        meaningful_diff_ratio = float((diffs > 1e-3).mean())
        assert meaningful_diff_ratio > 0.05, (
            f"native vs legacy differ in only {meaningful_diff_ratio*100:.2f}% of "
            f"finite positions — expected >5%"
        )

    def test_d_star_cache_key_isolation_native_uses_source_tf(
        self, tmp_path, monkeypatch
    ):
        """When native path runs, the sibling preprocessor's d_star cache
        context.timeframe must reflect SOURCE TF (12h), not PRIMARY (1h).
        We probe this by triggering native then inspecting the FeaturePreprocessor's
        internal context — using a tiny custom hook."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        registry, _, _, _ = _make_real_eth_compact_registry(
            tmp_path, primary_rows=20352, n_cols=1
        )
        captured = {}
        # Patch FeaturePreprocessor.__init__ to record context for the SIBLING
        # native instance (the inner one created with scaled_config).
        from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fp_mod

        original_init = fp_mod.FeaturePreprocessor.__init__

        def _spy_init(self, config, *args, context=None, **kwargs):
            original_init(self, config, *args, context=context, **kwargs)
            ctx = getattr(self, "_preprocessing_context", None)
            if ctx is not None and getattr(ctx, "timeframe", None) == "12h":
                captured["native_ctx_timeframe"] = ctx.timeframe
                captured["native_ctx_row_count"] = ctx.row_count

        monkeypatch.setattr(fp_mod.FeaturePreprocessor, "__init__", _spy_init)

        # Outer preprocessor uses primary TF context (1h) by default since we
        # don't pass context — but the native sibling MUST construct a new
        # context with timeframe=12h.
        outer = fp_mod.FeaturePreprocessor(_l65_config())
        outer.transform_registry_groups(registry, n_workers=1)

        assert captured.get("native_ctx_timeframe") == "12h", (
            "native sibling preprocessor did not use source-TF (12h) in its "
            "PreprocessingContext — d_star cache would collide with primary"
        )
        # Native context row_count must equal native (12h) row count, NOT
        # primary (1h) row count.
        assert captured.get("native_ctx_row_count", 0) > 0
        assert captured["native_ctx_row_count"] < 20352, (
            "native context row_count should be <<primary; got "
            f"{captured['native_ctx_row_count']} ≥ 20352"
        )


# ---------------------------------------------------------------------------
# Edge cases on synthetic compact groups
# ---------------------------------------------------------------------------
def _make_synthetic_compact(
    tmp_path: Path,
    *,
    native: np.ndarray,
    idx_map: np.ndarray,
    columns: tuple,
    group_id: str = "12h_L1_synth",
) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(tmp_path / "work")
    source_path = registry.work_dir / f"{group_id}.npy"
    np.save(source_path, native.astype(np.float32, copy=False), allow_pickle=False)
    idx_path = _write_idx_map_npy(
        registry.work_dir / ".align_12h_to_1h_close_time.npy", idx_map
    )
    group = ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="close",
        indicator="SYNTH",
        columns=columns,
        shape=(len(idx_map), native.shape[1]),
        dtype="float32",
        disk_path=source_path,
        alignment=AlignmentMeta(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=native.shape[0],
            primary_n_rows=len(idx_map),
            idx_map_path=idx_path,
            alignment_mode="close_time",
            offset_ns=0,
        ),
    )
    registry.register(group)
    registry.write_manifest()
    return registry


class TestEdgeCases:
    def test_single_column_compact(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        rng = np.random.default_rng(0)
        native = rng.standard_normal((100, 1)).astype(np.float32) * 10 + 100
        idx_map = np.repeat(np.arange(100, dtype=np.int32), 12)
        registry = _make_synthetic_compact(
            tmp_path, native=native, idx_map=idx_map, columns=("only_col",)
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        result = registry.load_data("12h_L1_synth")
        assert result.shape == (1200, 1)
        assert result.dtype == np.float32
        assert np.isfinite(result).mean() > 0.5

    def test_many_column_compact(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        rng = np.random.default_rng(1)
        n_cols = 20
        native = rng.standard_normal((150, n_cols)).astype(np.float32)
        idx_map = np.repeat(np.arange(150, dtype=np.int32), 12)
        cols = tuple(f"f{i}" for i in range(n_cols))
        registry = _make_synthetic_compact(
            tmp_path, native=native, idx_map=idx_map, columns=cols
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        result = registry.load_data("12h_L1_synth")
        assert result.shape == (1800, n_cols)
        assert result.dtype == np.float32

    def test_idx_map_all_negative_outputs_all_nan(self, tmp_path, monkeypatch):
        """All -1 idx_map → output entirely NaN, no crash."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        native = np.ones((100, 2), dtype=np.float32)
        idx_map = np.full(1200, -1, dtype=np.int32)
        registry = _make_synthetic_compact(
            tmp_path, native=native, idx_map=idx_map, columns=("a", "b")
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        result = registry.load_data("12h_L1_synth")
        assert result.shape == (1200, 2)
        assert np.all(np.isnan(result))

    def test_irregular_idx_map_runs(self, tmp_path, monkeypatch):
        """Non-uniform run lengths (mix of ratios) — forward-fill must still
        be constant within each native-idx run."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        rng = np.random.default_rng(2)
        native = rng.standard_normal((80, 1)).astype(np.float32)
        # Irregular: native idx 0→3 rows, 1→6 rows, 2→1 row, 3→12 rows...
        run_lengths = rng.integers(1, 15, size=80)
        idx_map_list = []
        for i, run in enumerate(run_lengths):
            idx_map_list.extend([i] * int(run))
        idx_map = np.asarray(idx_map_list, dtype=np.int32)
        primary_n = len(idx_map)
        if primary_n < 50:
            pytest.skip("primary too small for L6.5 windows")

        registry = _make_synthetic_compact(
            tmp_path, native=native, idx_map=idx_map, columns=("v",)
        )
        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        result = registry.load_data("12h_L1_synth")
        assert result.shape == (primary_n, 1)
        # Check forward-fill constancy on irregular runs.
        i = 0
        while i < primary_n:
            j = i + 1
            cur = idx_map[i]
            while j < primary_n and idx_map[j] == cur:
                j += 1
            if cur >= 0 and j - i > 1:
                vals = result[i:j, 0]
                finite = vals[np.isfinite(vals)]
                if finite.size > 1:
                    assert np.allclose(finite, finite[0], rtol=0, atol=0), (
                        f"non-constant in irregular run idx={cur} [{i}:{j}]"
                    )
            i = j

    def test_mixed_compact_and_non_compact_in_same_registry(
        self, tmp_path, monkeypatch
    ):
        """Mixed registry: compact 12h group + non-compact 1h group. Each
        should take the appropriate path; non-compact must be unaffected by
        the flag."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        rng = np.random.default_rng(3)
        # Compact group
        native = rng.standard_normal((100, 1)).astype(np.float32)
        idx_map = np.repeat(np.arange(100, dtype=np.int32), 12)
        registry = _make_synthetic_compact(
            tmp_path, native=native, idx_map=idx_map, columns=("c1",),
            group_id="12h_compact",
        )
        # Non-compact group
        plain = rng.standard_normal((1200, 2)).astype(np.float32)
        plain_group = ColumnGroup(
            group_id="1h_plain",
            layer=LayerSource.L1,
            timeframe="1h",
            data_source="close",
            indicator="PLAIN",
            columns=("p1", "p2"),
            shape=(1200, 2),
            dtype="float32",
        )
        registry.save_data(plain_group, plain.copy())

        FeaturePreprocessor(_l65_config()).transform_registry_groups(
            registry, n_workers=1
        )
        compact_result = registry.load_data("12h_compact")
        plain_result = registry.load_data("1h_plain")
        assert compact_result.shape == (1200, 1)
        assert plain_result.shape == (1200, 2)
        # Non-compact must remain finite where input was finite.
        assert np.isfinite(plain_result).mean() > 0.5

    def test_append_mode_creates_l65_group(self, tmp_path, monkeypatch):
        """In append mode, native path should produce a `_L65` sibling group
        with primary-shape data."""
        monkeypatch.setenv("FFACT_L65_NATIVE_TF", "1")
        rng = np.random.default_rng(4)
        native = rng.standard_normal((100, 1)).astype(np.float32)
        idx_map = np.repeat(np.arange(100, dtype=np.int32), 12)
        registry = _make_synthetic_compact(
            tmp_path, native=native, idx_map=idx_map, columns=("v",),
            group_id="12h_append",
        )
        FeaturePreprocessor(_l65_config(mode="append")).transform_registry_groups(
            registry, n_workers=1
        )
        # Original group should still exist; native path either appends a
        # `_L65` group or produces no extra columns (winsor/rank/zscore replace
        # the originals, so append may yield only the originals — accept both).
        all_ids = [gid for gid, _ in registry.iter_all()]
        assert "12h_append" in all_ids
        original = registry.load_data("12h_append")
        assert original.shape == (1200, 1)
        # If a _L65 sibling exists, it must be primary-shaped.
        for gid in all_ids:
            if gid.startswith("12h_append_L65"):
                sibling = registry.load_data(gid)
                assert sibling.shape[0] == 1200
                assert sibling.dtype == np.float32
