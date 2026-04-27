from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def test_non_stationary_cache_reuses_adf_result(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"adf": 0}

    def fake_adfuller(series: pd.Series, autolag: str = "AIC") -> Any:
        call_count["adf"] += 1
        return (None, 0.2)

    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)
    monkeypatch.setattr(fp_mod, "adfuller", fake_adfuller)

    frame = pd.DataFrame({"L1_alpha": np.arange(80.0)})
    preprocessor = FeaturePreprocessor(
        {"adf_differencing": {"adf_threshold": 0.05, "sample_size": 40}}
    )

    assert preprocessor._get_non_stationary_columns(frame) == ["L1_alpha"]
    assert preprocessor._get_non_stationary_columns(frame) == ["L1_alpha"]
    assert call_count["adf"] == 1


def test_high_nan_no_adf_for_non_stationary_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"adf": 0}

    def fake_adfuller(series: pd.Series, autolag: str = "AIC") -> Any:
        call_count["adf"] += 1
        return (None, 0.2)

    def fail_find_min_d(*args: Any, **kwargs: Any) -> float:
        raise AssertionError("high-NaN column should not reach FracDiff d* search")

    values = np.arange(100.0)
    values[:60] = np.nan
    frame = pd.DataFrame({"L1_high_nan": values})

    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1")
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)
    monkeypatch.setattr(fp_mod, "adfuller", fake_adfuller)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", fail_find_min_d)

    preprocessor = FeaturePreprocessor(
        {
            "fractional_differencing": {
                "enabled": True,
                "apply_to": "non_stationary",
                "cache_d_star": False,
                "precision": 0.02,
            },
            "mode": "append",
        }
    )

    output = preprocessor.transform(frame)

    assert "L1_high_nan_fracdiff" not in output.columns
    assert call_count["adf"] == 0
