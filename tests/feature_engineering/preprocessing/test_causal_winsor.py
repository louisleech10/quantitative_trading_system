from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.preprocessing import _hurst_prior
from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext
from momentum.FeatureEngineering.preprocessing._non_stationary_cache import NonStationaryCache
from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
    scale_preprocessing_config_for_native,
)
from momentum.FeatureEngineering.preprocessing._numba_transforms import (
    rolling_quantile_2d,
    transform_array_fast,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import HAS_SCIPY, FeaturePreprocessor

try:
    from scipy.special import ndtri
except Exception:  # pragma: no cover
    ndtri = None


def _config(method: str, *, window: int = 20) -> dict:
    return {
        "mode": "replace",
        "causal_preprocessing": True,
        "winsorization": {
            "enabled": True,
            "method": method,
            "sigma_k": 1.0,
            "quantile_range": [0.25, 0.75],
            "window": window,
            "apply_to": "all",
        },
    }


def _rolling_quantile_oracle(frame: pd.DataFrame, window: int, lower_q: float, upper_q: float) -> pd.DataFrame:
    min_periods = max(20, window // 4)
    lower = frame.rolling(window, min_periods=min_periods).quantile(lower_q)
    upper = frame.rolling(window, min_periods=min_periods).quantile(upper_q)
    clipped = frame.copy()
    valid = lower.notna() & upper.notna()
    clipped = clipped.where(~valid, clipped.clip(lower=lower, upper=upper, axis=1))
    return clipped.astype(np.float32)


def test_rolling_bounds_pit() -> None:
    frame = pd.DataFrame(
        {
            "alpha": np.r_[np.linspace(1.0, 30.0, 30), 1000.0, 31.0, 32.0],
            "ties": [1.0] * 25 + [2.0, 2.0, 3.0, 100.0, 4.0, 5.0, 6.0, 7.0],
            "all_nan": [np.nan] * 33,
        }
    )
    window = 20

    result = FeaturePreprocessor(_config("quantile", window=window))._apply_winsorization(frame)
    expected = _rolling_quantile_oracle(frame.astype(float), window, 0.25, 0.75)

    np.testing.assert_allclose(result.to_numpy(np.float32), expected.to_numpy(np.float32), atol=1e-6, equal_nan=True)

    perturbed = frame.copy()
    perturbed.loc[31:, "alpha"] = [-9999.0, 9999.0]
    perturbed_result = FeaturePreprocessor(_config("quantile", window=window))._apply_winsorization(perturbed)
    np.testing.assert_allclose(
        result.loc[:30].to_numpy(np.float32),
        perturbed_result.loc[:30].to_numpy(np.float32),
        atol=1e-6,
        equal_nan=True,
    )

    lowers, uppers = rolling_quantile_2d(frame[["alpha"]].to_numpy(float), 0.25, 0.75, 1, 20)
    assert np.isnan(lowers).all()
    assert np.isnan(uppers).all()


def test_rolling_sigma_bounds_pit() -> None:
    frame = pd.DataFrame({"alpha": np.r_[np.linspace(1.0, 30.0, 30), 5000.0, 31.0]})
    window = 20
    min_periods = max(20, window // 4)
    result = FeaturePreprocessor(_config("sigma", window=window))._apply_winsorization(frame)

    rolling = frame.rolling(window, min_periods=min_periods)
    lower = rolling.mean() - rolling.std()
    upper = rolling.mean() + rolling.std()
    expected = frame.where(lower.isna() | upper.isna(), frame.clip(lower=lower, upper=upper, axis=1))
    np.testing.assert_allclose(result.to_numpy(np.float32), expected.to_numpy(np.float32), atol=1e-6)

    perturbed = frame.copy()
    perturbed.loc[31, "alpha"] = -5000.0
    perturbed_result = FeaturePreprocessor(_config("sigma", window=window))._apply_winsorization(perturbed)
    np.testing.assert_allclose(result.loc[:30].to_numpy(np.float32), perturbed_result.loc[:30].to_numpy(np.float32), atol=1e-6)


def test_gaussian_rolling_pit() -> None:
    if not HAS_SCIPY or ndtri is None:
        pytest.skip("scipy required")

    frame = pd.DataFrame({"alpha": np.r_[np.linspace(1.0, 30.0, 30), 1000.0, 31.0]})
    config = {
        "mode": "replace",
        "causal_preprocessing": True,
        "winsorization": {"enabled": False, "window": 20},
        "gaussian_normalize": {"enabled": True, "clip_range": [0.001, 0.999], "apply_to": "all"},
    }
    result = FeaturePreprocessor(config)._apply_gaussian_normalize(frame)

    window = 20
    min_periods = max(20, window // 4)
    ranked = frame.rolling(window, min_periods=min_periods).rank(method="average", pct=True)
    expected = pd.DataFrame(ndtri(ranked.clip(0.001, 0.999).to_numpy(float)), index=frame.index, columns=frame.columns)
    np.testing.assert_allclose(result.to_numpy(np.float32), expected.to_numpy(np.float32), atol=1e-6, equal_nan=True)

    perturbed = frame.copy()
    perturbed.loc[31, "alpha"] = -1000.0
    perturbed_result = FeaturePreprocessor(config)._apply_gaussian_normalize(perturbed)
    np.testing.assert_allclose(result.loc[:30].to_numpy(np.float32), perturbed_result.loc[:30].to_numpy(np.float32), atol=1e-6, equal_nan=True)


def test_fracdiff_warmup_freeze_no_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    prefix = np.linspace(1.0, 600.0, 600)
    tail_a = np.linspace(601.0, 900.0, 300)
    tail_b = np.linspace(5000.0, 9000.0, 300)
    s1 = pd.Series(np.r_[prefix, tail_a])
    s2 = pd.Series(np.r_[prefix, tail_b])
    seen_lengths: list[int] = []

    original_hurst = _hurst_prior.estimate_hurst_rs

    def _spy(values: np.ndarray) -> float:
        seen_lengths.append(len(values))
        return original_hurst(values)

    monkeypatch.setattr(_hurst_prior, "estimate_hurst_rs", _spy)
    pre = FeaturePreprocessor(
        {
            "causal_preprocessing": True,
            "calibration_bars": 500,
            "fractional_differencing": {"precision": 0.5, "adf_threshold": 0.1, "weight_threshold": 1e-5},
            "adf_differencing": {"sample_size": 500, "adf_threshold": 0.1},
        }
    )

    assert pre._find_min_d(s1, precision=0.5, max_lag=20) == pre._find_min_d(s2, precision=0.5, max_lag=20)
    assert seen_lengths
    assert max(seen_lengths) <= 500

    df1 = pd.DataFrame({"x": s1})
    df2 = pd.DataFrame({"x": s2})
    assert pre._get_non_stationary_columns(df1) == pre._get_non_stationary_columns(df2)


def test_flag_busts_hash_and_both_caches(tmp_path) -> None:
    adapter = Mock()
    adapter.get_last_timestamp.return_value = 123456
    factory = FeatureFactory(config_manager=Mock(), adapter_registry=adapter)
    cm = ConfigManager()
    causal = cm.get_merged_config(api_override={"preprocessing": {"causal_preprocessing": True}})
    legacy = cm.get_merged_config(api_override={"preprocessing": {"causal_preprocessing": False}})

    assert factory._compute_config_hash(causal, "BTCUSDT", "1h") != factory._compute_config_hash(legacy, "BTCUSDT", "1h")

    ctx = PreprocessingContext(symbol="BTCUSDT", timeframe="1h", row_count=10)
    old_cache = DStarCache(ctx, tmp_path, adf_threshold=0.1, precision=0.1, max_lag=20, weight_threshold=1e-5, sample_size=500, causal_preprocessing=False, calibration_bars=0)
    values = np.arange(10, dtype=np.float64)
    old_cache.set("alpha", 0.4, values)
    old_cache.flush_atomic()

    new_cache = DStarCache(ctx, tmp_path, adf_threshold=0.1, precision=0.1, max_lag=20, weight_threshold=1e-5, sample_size=500, causal_preprocessing=True, calibration_bars=500)
    assert new_cache.get("alpha", values[:10]) is None

    nonstat = NonStationaryCache()
    series = pd.Series(np.r_[np.arange(500, dtype=float), np.arange(500, 900, dtype=float)])
    old_key = nonstat.make_key("alpha", 0.1, 500, "dropna", series, causal_preprocessing=False, calibration_bars=0)
    nonstat.set(old_key, True)
    warmup_key = nonstat.make_key("alpha", 0.1, 500, "dropna", series.iloc[:500], causal_preprocessing=True, calibration_bars=500)
    assert nonstat.get(warmup_key) is None


def test_all_l65_entrypoints_causal(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame({"alpha": np.r_[np.linspace(1.0, 30.0, 30), 9999.0, 31.0]})
    config = {
        "mode": "replace",
        "causal_preprocessing": True,
        "winsorization": {"enabled": True, "method": "quantile", "quantile_range": [0.25, 0.75], "window": 20, "apply_to": "all"},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }

    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    monkeypatch.setenv("FFACT_L65_OPTIMIZATION_PROFILE", "legacy")
    legacy = FeaturePreprocessor(config).transform(frame)

    monkeypatch.setenv("FFACT_L65_OPTIMIZATION_PROFILE", "optimized")
    optimized = FeaturePreprocessor(config).transform(frame)
    np.testing.assert_allclose(legacy.to_numpy(np.float32), optimized.to_numpy(np.float32), atol=1e-6, equal_nan=True)

    if HAS_SCIPY:
        fast_config = {
            **config,
            "winsorization": {"enabled": False, "window": 20},
            "gaussian_normalize": {
                "enabled": True,
                "clip_range": [0.001, 0.999],
                "apply_to": "all",
            },
        }
        fast_pre = FeaturePreprocessor(fast_config)
        fast_context = fast_pre._build_registry_transform_context()

        def _run_fast(values: pd.DataFrame) -> np.ndarray:
            registry = Mock()
            registry.load_data.return_value = values.to_numpy(np.float32)
            captured: dict[str, np.ndarray] = {}
            registry.overwrite_data.side_effect = lambda _group_id, data: captured.setdefault("data", data.copy())
            group = SimpleNamespace(
                group_id="fast",
                columns=("alpha",),
                alignment=None,
                layer="L1",
            )
            fast_pre._transform_single_group(registry, group, fast_context)
            return captured["data"]

        fast = _run_fast(frame)
        perturbed = frame.copy()
        perturbed.iloc[-1, 0] = -9999.0
        fast_perturbed = _run_fast(perturbed)
        np.testing.assert_allclose(fast[:-1], fast_perturbed[:-1], atol=1e-6, equal_nan=True)

        rank_only = transform_array_fast(
            frame.to_numpy(np.float32),
            winsorize=False,
            rank=True,
            rank_window=20,
            zscore=False,
        )
        assert np.isnan(rank_only[:19]).all()
        assert np.isfinite(rank_only[19:]).all()

    try:
        import polars  # noqa: F401
    except Exception:
        polars = None

    if polars is not None:
        monkeypatch.setenv("FFACT_USE_POLARS", "1")
        polars_result = FeaturePreprocessor(config)._transform_single_polars(frame)
        np.testing.assert_allclose(legacy.to_numpy(np.float32), polars_result.to_numpy(np.float32), atol=1e-6, equal_nan=True)

        if HAS_SCIPY:
            gaussian_pre = FeaturePreprocessor(
                {
                    **config,
                    "winsorization": {"enabled": False, "window": 20},
                    "gaussian_normalize": {"enabled": True, "apply_to": "all"},
                }
            )
            original_gaussian = gaussian_pre._apply_gaussian_normalize
            gaussian_calls: list[bool] = []

            def _causal_gaussian(df: pd.DataFrame) -> pd.DataFrame:
                gaussian_calls.append(gaussian_pre.causal_preprocessing)
                return original_gaussian(df)

            monkeypatch.setattr(gaussian_pre, "_apply_gaussian_normalize", _causal_gaussian)
            gaussian_result = gaussian_pre._transform_single_polars(frame)
            gaussian_perturbed = gaussian_pre._transform_single_polars(perturbed)
            assert gaussian_calls == [True, True]
            np.testing.assert_allclose(
                gaussian_result.iloc[:-1].to_numpy(np.float32),
                gaussian_perturbed.iloc[:-1].to_numpy(np.float32),
                atol=1e-6,
                equal_nan=True,
            )

        fracdiff_pre = FeaturePreprocessor(
            {
                **config,
                "winsorization": {"enabled": False, "window": 20},
                "fractional_differencing": {
                    "enabled": True,
                    "apply_to": "all",
                    "precision": 0.5,
                },
            }
        )
        original_fracdiff = fracdiff_pre._apply_fractional_differencing
        fracdiff_calls: list[bool] = []

        def _causal_fracdiff(df: pd.DataFrame, source_layer=None) -> pd.DataFrame:
            fracdiff_calls.append(fracdiff_pre.causal_preprocessing)
            return original_fracdiff(df, source_layer=source_layer)

        monkeypatch.setattr(fracdiff_pre, "_apply_fractional_differencing", _causal_fracdiff)
        fracdiff_frame = pd.DataFrame(
            {"L1_alpha": np.r_[np.linspace(1.0, 600.0, 600), np.linspace(601.0, 620.0, 20)]}
        )
        fracdiff_result = fracdiff_pre.transform(fracdiff_frame)
        fracdiff_perturbed_frame = fracdiff_frame.copy()
        fracdiff_perturbed_frame.iloc[-1, 0] = -9999.0
        fracdiff_perturbed = fracdiff_pre.transform(fracdiff_perturbed_frame)
        assert fracdiff_calls == [True, True]
        np.testing.assert_allclose(
            fracdiff_result.iloc[:-1].to_numpy(np.float32),
            fracdiff_perturbed.iloc[:-1].to_numpy(np.float32),
            atol=1e-6,
            equal_nan=True,
        )

    native_config = {
        **config,
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.25, 0.75],
            "window": 240,
            "apply_to": "all",
        },
        "calibration_bars": 600,
    }
    scaled = scale_preprocessing_config_for_native(native_config, "12h", "1h")
    assert scaled["winsorization"]["window"] == 20
    assert scaled["calibration_bars"] == 50
    native_values = np.r_[np.linspace(1.0, 60.0, 60), 9999.0].astype(np.float32)[:, None]
    native_perturbed_values = native_values.copy()
    native_perturbed_values[-1, 0] = -9999.0
    idx_map = np.repeat(np.arange(len(native_values), dtype=np.int32), 12)
    group = SimpleNamespace(
        group_id="native",
        columns=("alpha",),
        layer="L1",
        alignment=SimpleNamespace(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=len(native_values),
            primary_n_rows=len(idx_map),
        ),
    )

    def _run_native(values: np.ndarray) -> np.ndarray:
        registry = Mock()
        registry.load_data_native.return_value = values
        registry.get_alignment_idx_map.return_value = idx_map
        captured: dict[str, np.ndarray] = {}
        registry.overwrite_data.side_effect = lambda _group_id, data: captured.setdefault("data", data.copy())
        assert FeaturePreprocessor(native_config)._maybe_run_native_l65_inplace(registry, group)
        return captured["data"]

    native = _run_native(native_values)
    native_perturbed = _run_native(native_perturbed_values)
    np.testing.assert_allclose(
        native[:-12],
        native_perturbed[:-12],
        atol=1e-6,
        equal_nan=True,
    )
