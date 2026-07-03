from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from momentum.FeatureEngineering.feature_config import FractionalDifferencingConfig
from momentum.FeatureEngineering.preprocessing._d_star_cache import (
    DStarCache,
    PreprocessingContext,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


BASE_CONTEXT = PreprocessingContext(
    symbol="BTCUSDT",
    timeframe="1h",
    config_hash="f" * 32,
    data_fingerprint="fingerprint-v1",
    feature_schema_hash="schema-v1",
    time_range=(1, 600),
    row_count=600,
    source_data_version="unit",
)


def _preprocessor(
    *,
    calibration_bars: int = 500,
    max_lag: int = 0,
    cache_d_star: bool = False,
) -> FeaturePreprocessor:
    return FeaturePreprocessor(
        {
            "calibration_bars": calibration_bars,
            "mode": "append",
            "adf_differencing": {"sample_size": calibration_bars},
            "fractional_differencing": {
                "enabled": True,
                "apply_to": "all",
                "cache_d_star": cache_d_star,
                "max_lag": max_lag,
            },
        }
    )


def _cache(
    cache_dir: Path,
    context: PreprocessingContext = BASE_CONTEXT,
    *,
    max_lag: int = 50,
    calibration_bars: int = 500,
) -> DStarCache:
    return DStarCache(
        context,
        cache_dir,
        adf_threshold=0.1,
        precision=0.01,
        max_lag=max_lag,
        weight_threshold=1e-5,
        sample_size=500,
        calibration_bars=calibration_bars,
    )


def test_fracdiff_auto_max_lag_is_calibration_derived_not_df_length() -> None:
    preprocessor = _preprocessor(calibration_bars=500)

    for row_count in (510, 590, 600, 5000):
        frame = pd.DataFrame({"x": np.arange(row_count, dtype=np.float64)})
        assert len(frame) == row_count
        assert preprocessor._resolve_fracdiff_max_lag() == 50


def test_fracdiff_explicit_max_lag_and_calibration_bounds() -> None:
    assert _preprocessor(max_lag=37)._resolve_fracdiff_max_lag() == 37
    assert _preprocessor(calibration_bars=800)._resolve_fracdiff_max_lag() == 80
    assert _preprocessor(calibration_bars=3000)._resolve_fracdiff_max_lag() == 252


def test_fractional_differencing_config_round_trip_and_validation() -> None:
    legacy = FractionalDifferencingConfig.model_validate({"enabled": True})
    assert legacy.max_lag == 0
    assert legacy.model_dump()["max_lag"] == 0

    pinned = FractionalDifferencingConfig.model_validate({"enabled": True, "max_lag": 37})
    assert pinned.max_lag == 37

    with pytest.raises(ValidationError):
        FractionalDifferencingConfig.model_validate({"enabled": True, "max_lag": -1})


def test_fracdiff_hash_is_independent_of_dataframe_row_count(tmp_path: Path) -> None:
    full_context = replace(BASE_CONTEXT, row_count=600, time_range=(1, 600))
    trunc_context = replace(BASE_CONTEXT, row_count=590, time_range=(1, 590))

    full = _cache(tmp_path / "full", full_context, max_lag=50, calibration_bars=500)
    trunc = _cache(tmp_path / "trunc", trunc_context, max_lag=50, calibration_bars=500)

    assert full._fracdiff_hash == trunc._fracdiff_hash


def test_pre_fix_auto_cache_misses_after_calibration_derived_max_lag(tmp_path: Path) -> None:
    values = np.linspace(1.0, 2.0, 600, dtype=np.float64)
    old_auto = _cache(tmp_path, max_lag=60, calibration_bars=500)
    old_auto.set("feature_fracdiff", 0.4, values)
    old_auto.flush_atomic()

    fixed_auto = _cache(tmp_path, max_lag=50, calibration_bars=500)

    assert old_auto.path != fixed_auto.path
    assert fixed_auto.get("feature_fracdiff", values) is None


def test_pre_fix_explicit_pin50_cache_can_legally_hit(tmp_path: Path) -> None:
    values = np.linspace(1.0, 2.0, 600, dtype=np.float64)
    pinned_before = _cache(tmp_path, max_lag=50, calibration_bars=500)
    pinned_before.set("feature_fracdiff", 0.4, values)
    pinned_before.flush_atomic()

    fixed_auto_same_width = _cache(tmp_path, max_lag=50, calibration_bars=500)

    assert fixed_auto_same_width.path == pinned_before.path
    assert fixed_auto_same_width.get("feature_fracdiff", values) == 0.4


def test_find_min_d_short_clean_series_returns_one() -> None:
    preprocessor = _preprocessor()
    short = pd.Series(np.arange(19, dtype=np.float64))

    assert preprocessor._find_min_d(short, max_lag=50) == 1.0


def test_short_dataframe_fracdiff_keeps_row_count(monkeypatch: pytest.MonkeyPatch) -> None:
    preprocessor = _preprocessor(calibration_bars=500, cache_d_star=False)
    frame = pd.DataFrame({"L1_close": np.linspace(1.0, 2.0, 300, dtype=np.float64)})
    resolved: list[int] = []

    def _spy_find_min_d(
        series: pd.Series,
        *,
        adf_threshold: float = 0.05,
        d_range: tuple[float, float] = (0.0, 1.0),
        precision: float | None = None,
        max_lag: int = 0,
    ) -> float:
        del series, adf_threshold, d_range, precision
        resolved.append(max_lag)
        return 1.0

    monkeypatch.setattr(preprocessor, "_find_min_d", _spy_find_min_d)
    result = preprocessor._apply_fractional_differencing(frame)

    assert len(result) == len(frame)
    assert resolved == [50]
    assert "L1_close_fracdiff" in result.columns
