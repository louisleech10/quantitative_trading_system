from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering.ffstat_helpers import attach_unit_calibration


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


def _layer_map() -> dict:
    """FFSTAT Task 1.1：fracdiff 目標層只取自結構化層來源（不再由欄名 `L<k>_` 前綴推層）；層值與舊欄名前綴同。"""
    return {"L1_alpha": "L1", "L2_beta": "L2", "L3_gamma": "L3", "L4_delta": "L4", "raw_unknown": "L0"}


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
        "calibration_bars": 40,  # FFSTAT b3b：fixture 80 列，N 取 40（封包以 fixture 本身建，僅驗層篩選）
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

    pre = FeaturePreprocessor(_config(), column_layer_map=_layer_map())
    attach_unit_calibration(pre, _frame())
    output = pre.transform(_frame())

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

    pre = FeaturePreprocessor(_config(), column_layer_map=_layer_map())
    attach_unit_calibration(pre, _frame())
    output = pre.transform(_frame())

    for column in ("L1_alpha", "L2_beta", "L3_gamma", "L4_delta"):
        assert f"{column}_fracdiff" in output.columns
    assert "raw_unknown_fracdiff" not in output.columns


def test_unknown_layer_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """FFSTAT Task 1.1（取代已退役之 `test_unknown_layer_warning_and_skip`：該測試驗欄名解析失敗時記警告並
    當非目標，此退路依 SPEC §C「目標層」刪除）：層對照缺欄 ⇒ fail-closed，訊息含缺漏欄數與欄名。"""
    monkeypatch.delenv("FFACT_L65_OPTIMIZATION_PROFILE", raising=False)
    monkeypatch.delenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", raising=False)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", _stub_find_min_d)
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)
    layer_map = {k: v for k, v in _layer_map().items() if k != "raw_unknown"}

    with pytest.raises(ValueError) as err:
        pre = FeaturePreprocessor(_config(), column_layer_map=layer_map)
        attach_unit_calibration(pre, _frame())
        pre.transform(_frame())
    assert "缺 1/5" in str(err.value) and "raw_unknown" in str(err.value)


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
    # Force statsmodels path so fake_adfuller is actually called.
    # (fast-ADF numba path bypasses adfuller by default.)
    monkeypatch.setenv("FFACT_USE_FAST_ADF", "0")

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
            "calibration_bars": 40,
        },
        column_layer_map={"L1_alpha": "L1", "L3_gamma": "L3"},
    )

    attach_unit_calibration(preprocessor, frame)
    output = preprocessor.transform(frame)

    assert call_count["adf"] == 1
    assert "L1_alpha_fracdiff" in output.columns
    assert "L3_gamma_fracdiff" not in output.columns
