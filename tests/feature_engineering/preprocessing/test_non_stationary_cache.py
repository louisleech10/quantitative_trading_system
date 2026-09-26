from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import EVENT_ADF_UNTESTED, FeaturePreprocessor
from tests.feature_engineering.ffstat_helpers import attach_unit_calibration


def test_non_stationary_cache_reuses_adf_result(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"adf": 0}

    def fake_adfuller(series: pd.Series, autolag: str = "AIC") -> Any:
        call_count["adf"] += 1
        return (None, 0.2)

    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)
    monkeypatch.setattr(fp_mod, "adfuller", fake_adfuller)
    # Force statsmodels path so fake_adfuller is actually called.
    # (fast-ADF numba path bypasses adfuller by default.)
    monkeypatch.setenv("FFACT_USE_FAST_ADF", "0")

    frame = pd.DataFrame({"L1_alpha": np.arange(80.0)})
    preprocessor = FeaturePreprocessor(
        # FFSTAT b3b：adf_differencing.sample_size 已刪（N＝calibration_bars）；封包只在平穩化開啟時交付 ⇒ 明設 enabled
        {"calibration_bars": 40, "adf_differencing": {"enabled": True, "adf_threshold": 0.05}}
    )

    attach_unit_calibration(preprocessor, frame)  # 封包以 fixture 本身建，僅驗同實例快取
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

    # FFSTAT b3b：原「公開序列高 NaN（60/100）⇒ 不做 ADF／d*」來自已刪之輸出範圍 NaN 率免檢閘（SPEC §C 逐欄檢定）；
    # 改驗唯一仍不檢定之情形：校準域（前 100 根）與公開序列（後 100 根）皆全無有效值
    values = np.full(200, np.nan)
    pre_history = pd.DataFrame({"L1_high_nan": values[:100]})
    frame = pd.DataFrame({"L1_high_nan": values[100:]})

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
            "calibration_bars": 40,
        },
        # FFSTAT Task 1.1：fracdiff 目標層只取自結構化層來源（不再由欄名 `L1_` 前綴推層）
        column_layer_map={"L1_high_nan": "L1"},
    )

    attach_unit_calibration(preprocessor, pre_history)
    output = preprocessor.transform(frame)

    assert "L1_high_nan_fracdiff" not in output.columns
    assert call_count["adf"] == 0
    record = next(r for (_, c), r in preprocessor.stationarity_decisions().items() if c == "L1_high_nan")
    assert record["adf_pvalue"] is None and EVENT_ADF_UNTESTED in record["events"]
