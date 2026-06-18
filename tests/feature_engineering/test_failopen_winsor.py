"""Phase4 validator winsor 因果性與單次套用測試。"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_validator import FeatureValidator


def _result(frame: pd.DataFrame, *, preprocessing: bool, winsor: bool):
    config = {
        "preprocessing": {
            "enabled": preprocessing,
            "winsorization": {"enabled": winsor},
        }
    }
    return SimpleNamespace(
        features_df=frame.copy(),
        feature_count=frame.shape[1],
        config_used=config,
    )


def test_validator_winsor_is_point_in_time() -> None:
    rng = np.random.default_rng(20260611)
    values = rng.normal(size=320).astype(np.float32)
    values[200] = 100.0
    frame = pd.DataFrame({"feature": values})
    validator = FeatureValidator()
    baseline = validator.winsorize(frame)

    for row in (0, 62, 63, 120, 200, 250):
        perturbed = frame.copy()
        perturbed.iloc[row + 1 :, 0] += np.float32(10_000.0)
        candidate = validator.winsorize(perturbed)
        np.testing.assert_allclose(
            candidate.iloc[row, 0],
            baseline.iloc[row, 0],
            atol=1e-6,
            rtol=0.0,
            equal_nan=True,
        )


@pytest.mark.parametrize("cgsa", [False, True])
@pytest.mark.parametrize("l65_winsor", [False, True])
def test_each_config_path_applies_at_most_one_winsor(
    cgsa: bool,
    l65_winsor: bool,
) -> None:
    del cgsa  # CGSA 不呼叫 frame validator；此矩陣仍驗證共同 config 決策。
    frame = pd.DataFrame({"feature": np.arange(320, dtype=np.float32)})
    result = _result(
        frame,
        preprocessing=l65_winsor,
        winsor=l65_winsor,
    )
    validator = FeatureValidator()

    validation = validator.validate_factory_output(result)

    assert validator._last_winsorization_count <= 1
    assert validator._last_winsorization_count == (0 if l65_winsor else 1)
    assert validation.has_inf is False


def test_winsor_rescans_nan_and_inf(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame({"feature": np.arange(320, dtype=np.float32)})
    result = _result(frame, preprocessing=False, winsor=False)
    validator = FeatureValidator()

    def _inject_invalid(_frame: pd.DataFrame) -> pd.DataFrame:
        invalid = _frame.copy()
        invalid.iloc[-1, 0] = np.inf
        invalid.iloc[-2, 0] = np.nan
        return invalid

    monkeypatch.setattr(validator, "winsorize", _inject_invalid)
    validation = validator.validate_factory_output(result)

    assert validation.has_inf is True
    assert validation.has_nan is True
