from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine


def _make_data(n: int = 300) -> pd.DataFrame:
    np.random.seed(123)
    close = pd.Series(100 + np.cumsum(np.random.normal(0, 1, n)))
    volume = pd.Series(np.random.randint(100, 2000, n)).astype(float)
    taker_ratio = pd.Series(np.random.uniform(0.35, 0.75, n)).astype(float)
    return pd.DataFrame({"close": close, "volume": volume, "taker_ratio": taker_ratio})


def _engine(**override) -> EntropyIndicatorEngine:
    cfg = {
        "windows": [55, 100],
        "n_bins": 10,
        "apen_m": 2,
        "apen_r_ratio": 0.2,
        "shannon_windows": [21, 55, 100],
        "hurst_windows": [55, 100, 200],
        "fractal_kmax": 10,
        "perm_m": 3,
        "perm_windows": [21, 55, 100],
        "apply_to": ["close_return"],
    }
    cfg.update(override)
    return EntropyIndicatorEngine(cfg, ["close"])


def test_entropy_compute_all_feature_count_and_prefix() -> None:
    out = _engine().compute_all(_make_data())
    assert out.shape[1] == 15
    assert all(col.startswith("ent_") for col in out.columns)


def test_entropy_metadata_complete() -> None:
    metadata = _engine().get_feature_metadata()
    assert len(metadata) == 15
    assert "ent_perm_100" in metadata


def test_entropy_insufficient_data() -> None:
    out = _engine().compute_all(_make_data(30))
    assert out["ent_hurst_200"].isna().all()


def test_entropy_constant_returns() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    shannon = out.filter(like="ent_shannon_").dropna()
    assert not shannon.empty
    assert (shannon == 0.0).all().all()


def test_entropy_zero_variance() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    assert out.filter(like="ent_apen_").notna().any().any()


def test_entropy_many_nans() -> None:
    data = _make_data()
    data.loc[:200, "close"] = np.nan
    out = _engine().compute_all(data)
    assert out.shape[1] == 15


def test_entropy_extreme_returns() -> None:
    data = _make_data()
    data.loc[20:40, "close"] *= 1.5
    data.loc[80:100, "close"] *= 0.5
    out = _engine().compute_all(data)
    assert out.shape[1] == 15


def test_hurst_low_r_squared() -> None:
    data = _make_data()
    data["close"] = np.random.uniform(99.9, 100.1, len(data))
    out = _engine().compute_all(data)
    assert out["ent_hurst_55"].isna().any()


def test_entropy_missing_column() -> None:
    out = _engine(apply_to=["not_exist"]).compute_all(_make_data())
    assert out.empty


def test_perm_entropy_m_exceeds_window() -> None:
    out = _engine(perm_m=10, perm_windows=[5]).compute_all(_make_data())
    assert out["ent_perm_5"].isna().all()


def test_perm_entropy_constant_values() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    perm = out.filter(like="ent_perm_").dropna()
    assert not perm.empty
    assert (perm == 0.0).all().all()


def test_perm_entropy_invalid_m() -> None:
    with pytest.raises(ValueError):
        _engine(perm_m=1)
