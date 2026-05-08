from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def test_precision_corr_002_matches_001() -> None:
    if not fp_mod.HAS_STATSMODELS:
        pytest.skip("statsmodels unavailable")

    rng = np.random.default_rng(7)
    series = pd.Series(np.cumsum(rng.normal(0.0, 1.0, size=360)))
    preprocessor = FeaturePreprocessor(
        {
            "fractional_differencing": {
                "enabled": True,
                "precision": 0.02,
                "weight_threshold": 1e-5,
                "cache_d_star": False,
            }
        }
    )

    d_001 = preprocessor._find_min_d(series, precision=0.01, max_lag=64)
    d_002 = preprocessor._find_min_d(series, precision=0.02, max_lag=64)
    frac_001 = preprocessor._frac_diff_ffd(series, d_001, max_width=64).dropna()
    frac_002 = preprocessor._frac_diff_ffd(series, d_002, max_width=64).dropna()
    aligned = pd.concat([frac_001, frac_002], axis=1).dropna()

    assert aligned.corr().iloc[0, 1] > 0.999


def test_precision_override_reaches_find_min_d(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = []

    def fake_find_min_d(
        self: FeaturePreprocessor,
        series: pd.Series,
        *,
        adf_threshold: float = 0.05,
        d_range: Tuple[float, float] = (0.0, 1.0),
        precision: Optional[float] = None,
        max_lag: int = 0,
    ) -> float:
        captured.append(precision)
        return 1.0

    monkeypatch.setenv("FFACT_FRACDIFF_PRECISION_OVERRIDE", "0.01")
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1")
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", fake_find_min_d)
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)

    frame = pd.DataFrame({"L1_alpha": np.arange(1.0, 81.0)})
    preprocessor = FeaturePreprocessor(
        {
            "fractional_differencing": {
                "enabled": True,
                "apply_to": ["L1_alpha"],
                "cache_d_star": False,
                "precision": 0.02,
                "max_lag": 8,
            },
            "mode": "append",
        }
    )

    preprocessor.transform(frame)

    assert captured == [0.01]


def test_precision_cache_version_v2_invalidates_legacy_and_mismatch(
    tmp_path: Path,
) -> None:
    context = PreprocessingContext(
        symbol="ETHUSDT",
        timeframe="1h",
        config_hash="e" * 32,
        data_fingerprint="fingerprint-precision",
        feature_schema_hash="schema-precision",
        time_range=(1, 100),
        row_count=100,
        source_data_version="test",
    )
    cache = DStarCache(
        context,
        tmp_path,
        adf_threshold=0.1,
        precision=0.02,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=500,
        nan_policy="dropna",
    )

    cache.set("L1_alpha", 0.5)
    cache.flush_atomic()
    payload = json.loads(cache.path.read_text(encoding="utf-8"))

    assert payload["cache_version"] == "v3"
    assert cache.get("L1_alpha") == 0.5
    assert DStarCache(
        context,
        tmp_path,
        adf_threshold=0.1,
        precision=0.01,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=500,
        nan_policy="dropna",
    ).get("L1_alpha") is None

    cache.path.write_text(json.dumps({"L1_alpha": 0.5}), encoding="utf-8")
    assert DStarCache(
        context,
        tmp_path,
        adf_threshold=0.1,
        precision=0.02,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=500,
        nan_policy="dropna",
    ).get("L1_alpha") is None
