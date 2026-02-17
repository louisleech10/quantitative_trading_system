from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine


def _make_data(n: int = 300) -> pd.DataFrame:
    np.random.seed(7)
    close = pd.Series(100 + np.cumsum(np.random.normal(0, 1, n)))
    return pd.DataFrame({"close": close})


def _engine(**override) -> TailRiskIndicatorEngine:
    cfg = {
        "windows": [21, 55, 100],
        "cvar_alphas": [0.01, 0.05],
        "rv_windows": [13, 21, 55],
        "mdd_windows": [21, 55, 100],
    }
    cfg.update(override)
    return TailRiskIndicatorEngine(cfg, ["close"])


def test_tail_risk_compute_all_feature_count_and_prefix() -> None:
    out = _engine().compute_all(_make_data())
    assert out.shape[1] == 26
    assert all(col.startswith("tr_") for col in out.columns)


def test_tail_risk_metadata_complete() -> None:
    metadata = _engine().get_feature_metadata()
    assert len(metadata) == 26
    assert "tr_mdd_100" in metadata


def test_tail_risk_insufficient_data() -> None:
    out = _engine().compute_all(_make_data(15))
    assert out["tr_cvar_1pct_100"].isna().all()


def test_tail_risk_zero_returns() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    assert (out.filter(like="tr_cvar_").fillna(0.0) == 0.0).all().all()
    assert (out.filter(like="tr_mdd_").fillna(0.0) == 0.0).all().all()


def test_tail_risk_one_sided() -> None:
    data = _make_data()
    data["close"] = np.arange(len(data), dtype=float) + 100.0
    out = _engine().compute_all(data)
    gpr = out.filter(like="tr_gpr_")
    assert (gpr.dropna() <= 100.0).all().all()


def test_tail_risk_rare_negative() -> None:
    data = _make_data()
    close = np.linspace(100, 120, len(data))
    close[150] = close[149] * 0.95
    data["close"] = close
    out = _engine().compute_all(data)
    assert out.filter(like="tr_cvar_5pct_").notna().any().any()


def test_udvr_zero_downside() -> None:
    data = _make_data()
    data["close"] = np.linspace(100, 130, len(data))
    out = _engine().compute_all(data)
    assert out.filter(like="tr_ud_vol_ratio_").isna().any().any()


def test_tail_risk_extreme() -> None:
    data = _make_data()
    data.loc[50:80, "close"] *= 1.5
    data.loc[120:150, "close"] *= 0.5
    out = _engine().compute_all(data)
    assert out.shape[1] == 26


def test_cvar_invalid_alpha() -> None:
    with pytest.raises(ValueError):
        _engine(cvar_alphas=[0.0, 0.05])


def test_tail_risk_many_nans() -> None:
    data = _make_data()
    data.loc[:220, "close"] = np.nan
    out = _engine().compute_all(data)
    assert out.shape[1] == 26


def test_mdd_monotonic_up() -> None:
    data = _make_data()
    data["close"] = np.linspace(100, 150, len(data))
    out = _engine().compute_all(data)
    assert (out.filter(like="tr_mdd_").fillna(0.0) == 0.0).all().all()


def test_mdd_monotonic_down() -> None:
    data = _make_data()
    data["close"] = np.linspace(150, 100, len(data))
    out = _engine().compute_all(data)
    assert out.filter(like="tr_mdd_").iloc[-1].max() > 0.0


def test_mdd_invalid_price() -> None:
    data = _make_data()
    data.loc[30, "close"] = 0.0
    out = _engine().compute_all(data)
    assert out.filter(like="tr_mdd_").isna().any().any()
