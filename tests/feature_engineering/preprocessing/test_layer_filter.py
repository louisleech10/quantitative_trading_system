from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def _frame() -> pd.DataFrame:
    values = np.arange(1.0, 81.0, dtype=np.float64)
    return pd.DataFrame(
        {
            "L1_alpha": values,
            "L2_beta": values + 1.0,
            "L3_gamma": values + 2.0,
            "L4_delta": values + 3.0,
            "raw_unknown": values + 4.0,
        }
    )


def _config() -> dict:
    columns = ["L1_alpha", "L2_beta", "L3_gamma", "L4_delta", "raw_unknown"]
    return {
        "fractional_differencing": {
            "enabled": True,
            "apply_to": columns,
            "cache_d_star": False,
            "precision": 0.02,
            "weight_threshold": 1e-5,
            "max_lag": 8,
        },
        "mode": "append",
    }


def _stub_find_min_d(
    self: FeaturePreprocessor,
    series: pd.Series,
    *,
    adf_threshold: float = 0.05,
    d_range: Tuple[float, float] = (0.0, 1.0),
    precision: Optional[float] = None,
    max_lag: int = 0,
) -> float:
    return 1.0


def test_layer_filter_optimized_profile_processes_only_l1_l2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FFACT_L65_OPTIMIZATION_PROFILE", raising=False)
    monkeypatch.delenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", raising=False)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", _stub_find_min_d)
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)

    output = FeaturePreprocessor(_config()).transform(_frame())

    assert "L1_alpha_fracdiff" in output.columns
    assert "L2_beta_fracdiff" in output.columns
    assert "L3_gamma_fracdiff" not in output.columns
    assert "L4_delta_fracdiff" not in output.columns
    assert "raw_unknown_fracdiff" not in output.columns


def test_layer_filter_legacy_profile_restores_l1_to_l4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_L65_OPTIMIZATION_PROFILE", "legacy")
    monkeypatch.delenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", raising=False)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", _stub_find_min_d)
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)

    output = FeaturePreprocessor(_config()).transform(_frame())

    for column in ("L1_alpha", "L2_beta", "L3_gamma", "L4_delta"):
        assert f"{column}_fracdiff" in output.columns
    assert "raw_unknown_fracdiff" not in output.columns


def test_unknown_layer_warning_and_skip(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.delenv("FFACT_L65_OPTIMIZATION_PROFILE", raising=False)
    monkeypatch.delenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", raising=False)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", _stub_find_min_d)
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)

    FeaturePreprocessor(_config()).transform(_frame())

    assert "Layer parse failed col=raw_unknown" in caplog.text


def test_layer_filter_runs_non_stationary_adf_only_for_target_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = {"adf": 0}

    def fake_adfuller(series: pd.Series, autolag: str = "AIC"):
        call_count["adf"] += 1
        return (None, 0.2)

    monkeypatch.delenv("FFACT_L65_OPTIMIZATION_PROFILE", raising=False)
    monkeypatch.delenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", raising=False)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", _stub_find_min_d)
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)
    monkeypatch.setattr(fp_mod, "adfuller", fake_adfuller)

    frame = pd.DataFrame(
        {
            "L1_alpha": np.arange(1.0, 81.0),
            "L3_gamma": np.arange(2.0, 82.0),
        }
    )
    preprocessor = FeaturePreprocessor(
        {
            "fractional_differencing": {
                "enabled": True,
                "apply_to": "non_stationary",
                "cache_d_star": False,
                "precision": 0.02,
                "max_lag": 8,
            },
            "mode": "append",
        }
    )

    output = preprocessor.transform(frame)

    assert call_count["adf"] == 1
    assert "L1_alpha_fracdiff" in output.columns
    assert "L3_gamma_fracdiff" not in output.columns
