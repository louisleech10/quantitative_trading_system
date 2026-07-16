from pathlib import Path
from typing import Optional

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.data_preprocessor import DataPreprocessor


KLINE_CACHE_PATH = Path("data_cache/feature_klines/kline_cache.h5")


def _real_btc_1h_features(limit: int = 300) -> pd.DataFrame:
    with h5py.File(KLINE_CACHE_PATH, "r") as file:
        data = file["BTCUSDT/1h/data"][:limit]
    return pd.DataFrame(
        {
            "open": data["open"].astype("float64"),
            "high": data["high"].astype("float64"),
            "low": data["low"].astype("float64"),
            "close": data["close"].astype("float64"),
            "volume": data["volume"].astype("float64"),
        },
        index=pd.Index(data["timestamp"].astype("int64"), name="timestamp"),
    )


def _train_mask(length: int, train_fraction: float = 0.8) -> np.ndarray:
    split = int(length * train_fraction)
    mask = np.zeros(length, dtype=bool)
    mask[:split] = True
    return mask


def _preprocessor(extra_config: Optional[dict] = None) -> DataPreprocessor:
    config = {
        "winsorization": {
            "enabled": True,
            "method": "percentile",
            "lower_percentile": 1.0,
            "upper_percentile": 99.0,
        },
        "missing_values": {"max_fill_forward": 3, "min_coverage": 0.5},
        "standardize": {"method": "none"},
    }
    if extra_config:
        config.update(extra_config)
    return DataPreprocessor(config)


def test_winsor_bounds_from_train_only() -> None:
    features = _real_btc_1h_features()
    fit_mask = _train_mask(len(features))
    dirty = features.copy()
    dirty.loc[~fit_mask, "close"] = dirty["close"].max() * 100.0
    preprocessor = _preprocessor()

    clean_clipped, _ = preprocessor.winsorize(
        features[["close"]],
        method="percentile",
        lower=1.0,
        upper=99.0,
        fit_mask=fit_mask,
    )
    dirty_clipped, _ = preprocessor.winsorize(
        dirty[["close"]],
        method="percentile",
        lower=1.0,
        upper=99.0,
        fit_mask=fit_mask,
    )

    pd.testing.assert_series_equal(
        dirty_clipped.loc[fit_mask, "close"],
        clean_clipped.loc[fit_mask, "close"],
    )
    assert dirty_clipped.loc[~fit_mask, "close"].max() == clean_clipped.loc[fit_mask, "close"].max()


def test_standardize_params_from_train_only() -> None:
    features = _real_btc_1h_features()
    fit_mask = _train_mask(len(features))
    dirty = features.copy()
    dirty.loc[~fit_mask, "volume"] = dirty["volume"].max() * 100.0
    preprocessor = _preprocessor({"standardize": {"method": "time_series_zscore"}})

    clean = preprocessor.standardize(features[["volume"]], "time_series_zscore", fit_mask=fit_mask)
    dirty_standardized = preprocessor.standardize(
        dirty[["volume"]],
        "time_series_zscore",
        fit_mask=fit_mask,
    )

    pd.testing.assert_series_equal(
        dirty_standardized.loc[fit_mask, "volume"],
        clean.loc[fit_mask, "volume"],
    )


def test_coverage_from_train_only() -> None:
    features = _real_btc_1h_features()[["close", "volume"]]
    fit_mask = _train_mask(len(features))
    dirty = features.copy()
    dirty.loc[~fit_mask, "close"] = np.nan
    preprocessor = _preprocessor()

    _, clean_removed = preprocessor.handle_missing(
        features,
        max_fill_forward=3,
        min_coverage=0.9,
        fit_mask=fit_mask,
    )
    _, dirty_removed = preprocessor.handle_missing(
        dirty,
        max_fill_forward=3,
        min_coverage=0.9,
        fit_mask=fit_mask,
    )

    assert dirty_removed == clean_removed


def test_constant_from_train_only() -> None:
    features = _real_btc_1h_features()[["close", "volume"]]
    fit_mask = _train_mask(len(features))
    dirty = features.copy()
    dirty.loc[~fit_mask, "close"] = 1.0
    preprocessor = _preprocessor()

    _, clean_removed = preprocessor.remove_constant_features(features, fit_mask=fit_mask)
    _, dirty_removed = preprocessor.remove_constant_features(dirty, fit_mask=fit_mask)

    assert dirty_removed == clean_removed


def test_preprocess_legacy_no_mask_unchanged() -> None:
    """LA-0 B4：legacy unset+None 由「不變」強化為 fail-closed raise。"""
    features = _real_btc_1h_features()
    preprocessor = _preprocessor({"standardize": {"method": "time_series_zscore"}})

    with pytest.raises(ValueError, match="fail-closed"):
        preprocessor.preprocess(features)
    with pytest.raises(ValueError, match="fail-closed"):
        preprocessor.preprocess(features, fit_mask=None)
    with pytest.raises(ValueError, match="fail-closed"):
        preprocessor.preprocess(features, fit_mask=None, fit_mode="unset")
