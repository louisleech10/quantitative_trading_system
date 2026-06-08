from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def _base_df(n: int = 300) -> pd.DataFrame:
    np.random.seed(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="12h")
    return pd.DataFrame(
        {
            "f1": np.random.normal(0, 1, n),
            "f2": np.random.normal(0, 1, n).cumsum(),
            "ms_feature": np.random.normal(0, 1, n),
        },
        index=idx,
    )


def test_preprocess_empty_df() -> None:
    pre = FeaturePreprocessor({"rank_transform": {"enabled": True}})
    out = pre.transform(pd.DataFrame())
    assert out.empty


def test_preprocess_all_nan_column() -> None:
    df = pd.DataFrame({"f1": [np.nan] * 100})
    pre = FeaturePreprocessor(
        {
            "rank_transform": {"enabled": True, "window": 10, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [10], "apply_to": "all"},
            "mode": "append",
        }
    )
    out = pre.transform(df)
    assert out["f1_rank"].isna().all()
    assert out["f1_zscore_10"].isna().all()


def test_preprocess_constant_column() -> None:
    df = pd.DataFrame({"f1": [5.0] * 120})
    pre = FeaturePreprocessor(
        {
            "causal_preprocessing": False,
            "rank_transform": {"enabled": True, "window": 20, "apply_to": "all"},
            "gaussian_normalize": {"enabled": True, "apply_to": "all", "clip_range": [0.001, 0.999]},
            "adaptive_zscore": {"enabled": True, "windows": [20], "apply_to": "all", "epsilon": 1e-8},
            "mode": "append",
        }
    )
    out = pre.transform(df)
    assert np.isclose(out["f1_rank"].dropna().iloc[-1], 0.5)
    assert np.isclose(out["f1_gaussian"].dropna().iloc[-1], 0.0)
    assert np.isclose(out["f1_zscore_20"].dropna().iloc[-1], 0.0)


def test_adf_nan_heavy() -> None:
    if not fp_mod.HAS_STATSMODELS:
        pytest.skip("statsmodels unavailable")
    df = _base_df(120)
    df.loc[df.index[:80], "f1"] = np.nan
    pre = FeaturePreprocessor(
        {
            "causal_preprocessing": False,
            "adf_differencing": {"enabled": True, "apply_to": ["f1"], "max_diff": 2},
            "mode": "append",
        }
    )
    out = pre.transform(df)
    assert "f1_diff1" not in out.columns
    assert "f1_diff2" not in out.columns


def test_gaussian_boundary() -> None:
    df = pd.DataFrame({"f1": np.concatenate([np.zeros(50), np.ones(50)])})
    pre = FeaturePreprocessor(
        {
            "causal_preprocessing": False,
            "gaussian_normalize": {"enabled": True, "apply_to": "all", "clip_range": [0.001, 0.999]},
            "mode": "append",
        }
    )
    out = pre.transform(df)
    assert np.isfinite(out["f1_gaussian"].dropna().to_numpy()).all()


def test_winsor_then_zscore() -> None:
    df = pd.DataFrame({"f1": [1.0] * 100 + [1000.0]})
    pre = FeaturePreprocessor(
        {
            "causal_preprocessing": False,
            "winsorization": {"enabled": True, "method": "sigma", "sigma_k": 0.0, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [20], "apply_to": "all", "epsilon": 1e-8},
            "mode": "append",
        }
    )
    out = pre.transform(df)
    assert np.isfinite(out["f1_zscore_20"].fillna(0.0).to_numpy()).all()


def test_preprocess_replace_mode() -> None:
    df = _base_df(120)
    before_cols = df.shape[1]
    pre = FeaturePreprocessor(
        {
            "rank_transform": {"enabled": True, "window": 20, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [20], "apply_to": "all", "epsilon": 1e-8},
            "mode": "replace",
        }
    )
    out = pre.transform(df)
    assert out.shape[1] == before_cols


def test_preprocess_append_mode() -> None:
    df = _base_df(120)
    pre = FeaturePreprocessor(
        {
            "rank_transform": {"enabled": True, "window": 20, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [20], "apply_to": "all", "epsilon": 1e-8},
            "mode": "append",
        }
    )
    out = pre.transform(df)
    assert out.shape[1] > df.shape[1]
    assert any(col.endswith("_rank") for col in out.columns)
    assert any("_zscore_" in col for col in out.columns)


def test_preprocess_performance() -> None:
    np.random.seed(123)
    df = pd.DataFrame(np.random.normal(0, 1, (300, 1000)), columns=[f"f{i}" for i in range(1000)])
    pre = FeaturePreprocessor(
        {
            "winsorization": {"enabled": True, "method": "quantile", "quantile_range": [0.01, 0.99], "apply_to": "all"},
            "rank_transform": {"enabled": True, "window": 50, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [50], "apply_to": "all", "epsilon": 1e-8},
            "mode": "append",
        }
    )
    start = time.time()
    out = pre.transform(df)
    elapsed = time.time() - start
    assert not out.empty
    assert elapsed < 30


def test_fracdiff_convergence_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    if not fp_mod.HAS_STATSMODELS:
        pytest.skip("statsmodels unavailable")
    df = _base_df(160)
    df = df.rename(columns={"f2": "L1_f2"})
    pre = FeaturePreprocessor(
        {
            "causal_preprocessing": False,
            "fractional_differencing": {
                "enabled": True,
                "apply_to": ["L1_f2"],
                "d_range": [0.0, 1.0],
                "adf_threshold": 0.05,
                "weight_threshold": 1e-5,
                "precision": 0.01,
                "cache_d_star": False,
            },
            "mode": "append",
        }
    )

    def _raise(*_args, **_kwargs):
        raise RuntimeError("forced fail")

    monkeypatch.setattr(pre, "_find_min_d", _raise)
    out = pre.transform(df)
    assert "L1_f2_fracdiff" in out.columns


def test_fracdiff_short_data() -> None:
    series = pd.Series([1.0, 2.0, 3.0])
    out = FeaturePreprocessor._frac_diff_ffd(series, d=0.9, threshold=1e-8)
    assert out.isna().all()


def test_fracdiff_adf_coexist(monkeypatch: pytest.MonkeyPatch) -> None:
    if not fp_mod.HAS_STATSMODELS:
        pytest.skip("statsmodels unavailable")
    df = _base_df(180)
    df = df.rename(columns={"f2": "L1_f2"})
    pre = FeaturePreprocessor(
        {
            "causal_preprocessing": False,
            "fractional_differencing": {
                "enabled": True,
                "apply_to": ["L1_f2"],
                "cache_d_star": False,
            },
            "adf_differencing": {
                "enabled": True,
                "apply_to": ["L1_f2"],
                "max_diff": 2,
            },
            "mode": "append",
        }
    )

    monkeypatch.setattr(pre, "_find_min_d", lambda *_args, **_kwargs: 0.5)
    out = pre.transform(df)
    assert "L1_f2_fracdiff" in out.columns
    assert "L1_f2_diff1" not in out.columns
    assert "L1_f2_diff2" not in out.columns


def test_transform_fixed_order(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force pandas path so we can monkey-patch the _apply_* helpers and capture
    # call order. The polars path uses different (equivalent) helpers
    # (polars_l65_winsorization etc.) and the order is asserted by other
    # numerical-equivalence tests (e.g. test_winsor_then_zscore).
    monkeypatch.setenv("FFACT_USE_POLARS", "0")

    df = _base_df(60)
    pre = FeaturePreprocessor(
        {
            "winsorization": {"enabled": True},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "rank_transform": {"enabled": True, "window": 10},
            "gaussian_normalize": {"enabled": True},
            "adaptive_zscore": {"enabled": True, "windows": [10]},
            "mode": "append",
        }
    )

    call_order: list[str] = []

    def _wrap(name: str):
        original = getattr(pre, name)

        def _inner(arg):
            call_order.append(name)
            return original(arg)

        return _inner

    monkeypatch.setattr(pre, "_apply_winsorization", _wrap("_apply_winsorization"))
    monkeypatch.setattr(pre, "_apply_rank_transform", _wrap("_apply_rank_transform"))
    monkeypatch.setattr(pre, "_apply_gaussian_normalize", _wrap("_apply_gaussian_normalize"))
    monkeypatch.setattr(pre, "_apply_adaptive_zscore", _wrap("_apply_adaptive_zscore"))

    pre.transform(df)
    assert call_order == [
        "_apply_winsorization",
        "_apply_rank_transform",
        "_apply_gaussian_normalize",
        "_apply_adaptive_zscore",
    ]
