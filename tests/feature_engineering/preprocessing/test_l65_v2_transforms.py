from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.preprocessing.feature_preprocessor import HAS_SCIPY, FeaturePreprocessor

try:
    from scipy.special import ndtri
except Exception:
    ndtri = None

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _rank_config(window: int = 3) -> dict:
    return {
        "mode": "replace",
        "rank_transform": {"enabled": True, "window": window, "apply_to": "all"},
    }


def _gaussian_config() -> dict:
    return {
        "mode": "replace",
        "causal_preprocessing": False,
        "gaussian_normalize": {
            "enabled": True,
            "clip_range": [0.001, 0.999],
            "apply_to": "all",
        },
    }


def _winsor_quantile_config(lower: float = 0.25, upper: float = 0.75) -> dict:
    return {
        "mode": "replace",
        "causal_preprocessing": False,
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [lower, upper],
            "apply_to": "all",
        },
    }


def _zscore_config(windows: list[int], mode: str = "replace") -> dict:
    return {
        "mode": mode,
        "adaptive_zscore": {
            "enabled": True,
            "windows": windows,
            "epsilon": 1e-8,
            "apply_to": "all",
        },
    }


def _single_copy_config() -> dict:
    return {
        "mode": "replace",
        "winsorization": {
            "method": "sigma",
            "sigma_k": 2.0,
            "apply_to": ["trend", "constant", "with_nan", "negative"],
        },
        "rank_transform": {
            "enabled": True,
            "window": 3,
            "apply_to": ["trend", "constant", "with_nan", "negative"],
        },
        "gaussian_normalize": {
            "enabled": True,
            "clip_range": [0.001, 0.999],
            "apply_to": ["trend", "constant", "with_nan", "negative"],
        },
        "adaptive_zscore": {
            "enabled": True,
            "windows": [3],
            "epsilon": 1e-8,
            "apply_to": ["trend", "constant", "with_nan", "negative"],
        },
    }


def _legacy_rank(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    selected = frame.astype(float)
    rolling = selected.rolling(window, min_periods=1)
    ranked = rolling.rank(method="average", pct=True)
    constant_mask = rolling.max() == rolling.min()
    ranked = ranked.mask(constant_mask, 0.5)
    ranked = ranked.where(~selected.isna(), np.nan)
    return ranked.astype(np.float32, copy=False)


def _expected_gaussian(frame: pd.DataFrame, lower: float = 0.001, upper: float = 0.999) -> pd.DataFrame:
    if ndtri is None:
        pytest.skip("scipy is required for gaussian comparison")

    payload = {}
    for column in frame.columns:
        series = frame[column].astype(float)
        if series.nunique(dropna=True) <= 1:
            ranked = pd.Series(np.nan, index=series.index, dtype=float)
            ranked.loc[series.notna()] = 0.5
        else:
            ranked = series.rank(pct=True)
        payload[column] = ndtri(ranked.clip(lower=lower, upper=upper).to_numpy(dtype=np.float64))
    return pd.DataFrame(payload, index=frame.index).astype(np.float32, copy=False)


def _expected_winsor_quantile(
    frame: pd.DataFrame,
    lower: float,
    upper: float,
) -> pd.DataFrame:
    selected = frame.astype(float)
    lowers = selected.quantile(lower)
    uppers = selected.quantile(upper)
    return selected.clip(lower=lowers, upper=uppers, axis=1).astype(np.float32, copy=False)


def _expected_zscore(frame: pd.DataFrame, window: int, epsilon: float = 1e-8) -> pd.DataFrame:
    selected = frame.astype(float)
    rolling = selected.rolling(window, min_periods=1)
    mean = rolling.mean()
    std = rolling.std()
    zscore = (selected - mean) / (std + epsilon)
    zscore = zscore.where(std > 0.0, 0.0)
    zscore = zscore.where(~selected.isna(), np.nan)
    return zscore.astype(np.float32, copy=False)


def test_single_copy_equivalence(monkeypatch: pytest.MonkeyPatch) -> None:
    if not HAS_SCIPY or ndtri is None:
        pytest.skip("scipy is required for full single-copy pipeline comparison")

    monkeypatch.delenv("FFACT_L65_OPTIMIZATION_PROFILE", raising=False)
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    frame = pd.DataFrame(
        {
            "trend": [1.0, 2.0, 3.0, 5.0, 8.0, 13.0],
            "constant": [7.0, 7.0, 7.0, 7.0, 7.0, 7.0],
            "with_nan": [1.0, np.nan, 2.0, 2.0, 5.0, np.nan],
            "negative": [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0],
            "label": ["a", "b", "c", "d", "e", "f"],
        }
    )
    original = frame.copy(deep=True)
    config = _single_copy_config()

    optimized = FeaturePreprocessor(config).transform(frame)
    legacy = FeaturePreprocessor(config)._transform_single_legacy(frame)

    assert list(optimized.columns) == list(legacy.columns)
    assert optimized.index.equals(legacy.index)
    assert optimized["label"].to_list() == legacy["label"].to_list()
    assert frame.equals(original)

    numeric_columns = [column for column in optimized.columns if column != "label"]
    assert optimized.loc[:, numeric_columns].isna().equals(legacy.loc[:, numeric_columns].isna())
    np.testing.assert_allclose(
        optimized.loc[:, numeric_columns].to_numpy(dtype=np.float32),
        legacy.loc[:, numeric_columns].to_numpy(dtype=np.float32),
        rtol=1e-5,
        atol=1e-8,
        equal_nan=True,
    )


def test_single_copy_legacy_profile_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_L65_OPTIMIZATION_PROFILE", "legacy")
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 4.0],
            "beta": [2.0, 2.0, np.nan, 5.0],
        }
    )
    config = {
        "mode": "replace",
        "winsorization": {"method": "sigma", "sigma_k": 2.0, "apply_to": "all"},
        "rank_transform": {"enabled": True, "window": 2, "apply_to": "all"},
    }

    preprocessor = FeaturePreprocessor(config)
    assert not preprocessor._can_use_optimized_dataframe_path()

    result = preprocessor.transform(frame)
    expected = FeaturePreprocessor(config)._transform_single_legacy(frame)

    np.testing.assert_allclose(
        result.to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    )


def test_single_copy_append_mode_preserves_legacy_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FFACT_L65_OPTIMIZATION_PROFILE", raising=False)
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 4.0],
            "beta": [2.0, 2.0, np.nan, 5.0],
        }
    )
    config = {
        "mode": "append",
        "winsorization": {"method": "sigma", "sigma_k": 2.0, "apply_to": "all"},
        "rank_transform": {"enabled": True, "window": 2, "apply_to": "all"},
    }

    preprocessor = FeaturePreprocessor(config)
    assert not preprocessor._can_use_optimized_dataframe_path()

    result = preprocessor.transform(frame)
    expected = FeaturePreprocessor(config)._transform_single_legacy(frame)

    assert list(result.columns) == list(expected.columns)
    np.testing.assert_allclose(
        result.to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    )


def test_l65_v2_benchmark_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/benchmark_l65_v2.py", "--help"],
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    help_text = result.stdout
    for flag in ("--phase", "--tier", "--ic-first", "--full-schema", "--streaming-checks"):
        assert flag in help_text


def test_l65_v2_golden_builder_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_l65_golden.py", "--mode=ic_first", "--help"],
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert "--mode" in result.stdout
    assert "ic_first" in result.stdout


def test_rank_constant_mask_removed() -> None:
    source = inspect.getsource(FeaturePreprocessor._apply_rank_transform)
    assert "rolling_max" not in source
    assert "rolling_min" not in source
    assert ".max()" not in source
    assert ".min()" not in source

    frame = pd.DataFrame(
        {
            "constant_then_trend": [1.0, 1.0, 1.0, 2.0, 3.0, np.nan, 3.0],
            "nan_then_constant": [np.nan, 5.0, 5.0, 5.0, 5.0, 6.0, 7.0],
        }
    )
    result = FeaturePreprocessor(_rank_config(window=3))._apply_rank_transform(frame)
    expected = _legacy_rank(frame, window=3)

    np.testing.assert_allclose(
        result.loc[:, expected.columns].to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    )


def test_rank_constant_window() -> None:
    frame = pd.DataFrame(
        {
            "constant": [4.0, 4.0, 4.0, 4.0, 4.0],
            "nan_prefixed_constant": [np.nan, 2.0, 2.0, 2.0, 2.0],
        }
    )
    result = FeaturePreprocessor(_rank_config(window=3))._apply_rank_transform(frame)

    assert result["constant"].eq(0.5).all()
    assert np.isnan(result["nan_prefixed_constant"].iloc[0])
    assert result["nan_prefixed_constant"].iloc[1:].eq(0.5).all()


def test_winsorize_numpy_equivalence() -> None:
    helper_source = inspect.getsource(FeaturePreprocessor._winsorize_2d_inplace)
    assert "np.nanquantile" in inspect.getsource(FeaturePreprocessor._nanquantile_linear)
    assert "np.clip" in helper_source
    assert "out=arr" in helper_source

    frame = pd.DataFrame(
        {
            "trend": [1.0, 2.0, 3.0, 4.0, 100.0],
            "with_nan": [np.nan, 2.0, 3.0, 4.0, 500.0],
            "negative": [-100.0, -3.0, -2.0, -1.0, 0.0],
            "constant": [7.0, 7.0, 7.0, 7.0, 7.0],
        }
    )
    result = FeaturePreprocessor(_winsor_quantile_config())._apply_winsorization(frame)
    expected = _expected_winsor_quantile(frame, lower=0.25, upper=0.75)

    assert result.isna().equals(expected.isna())
    np.testing.assert_allclose(
        result.to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=1e-5,
        atol=1e-8,
        equal_nan=True,
    )


def test_winsorize_all_nan_column() -> None:
    frame = pd.DataFrame(
        {
            "all_nan": [np.nan, np.nan, np.nan, np.nan],
            "mixed": [1.0, np.nan, 3.0, 100.0],
        }
    )
    result = FeaturePreprocessor(_winsor_quantile_config())._apply_winsorization(frame)

    assert result["all_nan"].isna().all()
    assert result["mixed"].isna().to_list() == [False, True, False, False]
    assert result["mixed"].iloc[-1] < frame["mixed"].iloc[-1]


def test_zscore_shared_rolling() -> None:
    helper_source = inspect.getsource(FeaturePreprocessor._rolling_zscore_2d)
    apply_source = inspect.getsource(FeaturePreprocessor._apply_adaptive_zscore)
    assert helper_source.count(".rolling(") == 1
    assert "_rolling_zscore_2d" in apply_source
    assert ".rolling(" not in apply_source

    frame = pd.DataFrame(
        {
            "trend": [1.0, 2.0, 4.0, 8.0, 16.0],
            "constant": [5.0, 5.0, 5.0, 5.0, 5.0],
            "with_nan": [1.0, np.nan, 2.0, 2.0, 5.0],
        }
    )
    result = FeaturePreprocessor(_zscore_config([3]))._apply_adaptive_zscore(frame)
    expected = _expected_zscore(frame, window=3)

    assert result.isna().equals(expected.isna())
    np.testing.assert_allclose(
        result.to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=1e-5,
        atol=1e-8,
        equal_nan=True,
    )


def test_zscore_empty_windows() -> None:
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, np.nan, 4.0],
            "beta": [3.0, 3.0, 3.0, 3.0],
        }
    )

    replace_result = FeaturePreprocessor(_zscore_config([]))._apply_adaptive_zscore(frame)
    append_result = FeaturePreprocessor(_zscore_config([], mode="append"))._apply_adaptive_zscore(frame)

    assert list(replace_result.columns) == list(frame.columns)
    assert list(append_result.columns) == list(frame.columns)
    np.testing.assert_allclose(
        replace_result.to_numpy(dtype=np.float32),
        frame.to_numpy(dtype=np.float32),
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    )
    np.testing.assert_allclose(
        append_result.to_numpy(dtype=np.float32),
        frame.to_numpy(dtype=np.float32),
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    )


def test_zscore_append_mode_preserves_legacy_suffix_order() -> None:
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 4.0, 8.0],
            "beta": [3.0, np.nan, 6.0, 9.0],
        }
    )
    windows = [2, 3]
    result = FeaturePreprocessor(_zscore_config(windows, mode="append"))._apply_adaptive_zscore(frame)

    expected = frame.copy()
    expected_frames = []
    for window in windows:
        expected_window = _expected_zscore(frame, window=window)
        expected_window = expected_window.rename(
            columns={column: f"{column}_zscore_{window}" for column in frame.columns}
        )
        expected_frames.append(expected_window)
    expected = pd.concat([expected] + expected_frames, axis=1)

    assert list(result.columns) == list(expected.columns)
    np.testing.assert_allclose(
        result.to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=1e-5,
        atol=1e-8,
        equal_nan=True,
    )


def test_zscore_constant_window_legacy_equivalence() -> None:
    frame = pd.DataFrame(
        {
            "constant": [7.0, 7.0, 7.0, 7.0],
            "single_then_trend": [1.0, 2.0, 3.0, 4.0],
            "nan_prefixed": [np.nan, 5.0, 5.0, 6.0],
        }
    )
    result = FeaturePreprocessor(_zscore_config([3]))._apply_adaptive_zscore(frame)
    expected = _expected_zscore(frame, window=3)

    assert result["constant"].eq(0.0).all()
    assert result["single_then_trend"].iloc[0] == 0.0
    assert np.isnan(result["nan_prefixed"].iloc[0])
    assert result["nan_prefixed"].iloc[1] == 0.0
    np.testing.assert_allclose(
        result.to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    )


def test_gaussian_batch_equivalence() -> None:
    if not HAS_SCIPY or ndtri is None:
        pytest.skip("scipy is required for gaussian normalization")

    frame = pd.DataFrame(
        {
            "trend": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "constant": [7.0, 7.0, 7.0, 7.0, 7.0, 7.0],
            "with_nan": [1.0, np.nan, 2.0, 2.0, 5.0, np.nan],
            "negative": [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0],
        }
    )
    result = FeaturePreprocessor(_gaussian_config())._apply_gaussian_normalize(frame)
    expected = _expected_gaussian(frame)

    np.testing.assert_allclose(
        result.loc[:, expected.columns].to_numpy(dtype=np.float32),
        expected.to_numpy(dtype=np.float32),
        rtol=1e-5,
        atol=1e-8,
        equal_nan=True,
    )


def test_gaussian_nan_column() -> None:
    if not HAS_SCIPY or ndtri is None:
        pytest.skip("scipy is required for gaussian normalization")

    frame = pd.DataFrame(
        {
            "all_nan": [np.nan, np.nan, np.nan, np.nan],
            "constant_with_nan": [3.0, np.nan, 3.0, np.nan],
            "mixed": [1.0, np.nan, 2.0, 3.0],
        }
    )
    result = FeaturePreprocessor(_gaussian_config())._apply_gaussian_normalize(frame)

    assert result["all_nan"].isna().all()
    assert result["constant_with_nan"].isna().to_list() == [False, True, False, True]
    assert result["mixed"].isna().to_list() == [False, True, False, False]
    assert result.loc[[0, 2], "constant_with_nan"].eq(0.0).all()
