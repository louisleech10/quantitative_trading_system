"""Phase 3 tests: FeatureLibrary abstraction layer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from momentum.core.contracts import FeatureLibraryEntry, FeatureNotFoundError


def test_feature_library_entry_frozen() -> None:
    """FeatureLibraryEntry should be immutable."""
    entry = FeatureLibraryEntry(
        symbol="BTC",
        timeframe="1h",
        config_hash="abc",
        feature_count=10,
        row_count=100,
        created_at=1.0,
        hdf5_relative_path="a/b.h5",
    )
    with pytest.raises(AttributeError):
        entry.symbol = "ETH"  # type: ignore[misc]


def test_feature_not_found_error_attributes() -> None:
    """FeatureNotFoundError should carry symbol/timeframe and readable message."""
    err = FeatureNotFoundError("BTCUSDT", "1h", "test detail")
    assert err.symbol == "BTCUSDT"
    assert err.timeframe == "1h"
    assert "BTCUSDT" in str(err)
    assert "test detail" in str(err)


def test_feature_library_list_available() -> None:
    """list_available should support symbol/timeframe filtering."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.list_all.return_value = [
        {
            "symbol": "BTC",
            "timeframe": "1h",
            "config_hash": "a",
            "feature_count": 5,
            "row_count": 10,
            "created_at": 1.0,
            "hdf5_relative_path": "p",
        },
        {
            "symbol": "ETH",
            "timeframe": "1h",
            "config_hash": "b",
            "feature_count": 3,
            "row_count": 8,
            "created_at": 2.0,
            "hdf5_relative_path": "q",
        },
    ]
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    all_entries = lib.list_available()
    assert len(all_entries) == 2

    btc_entries = lib.list_available(symbol="BTC")
    assert len(btc_entries) == 1
    assert btc_entries[0].symbol == "BTC"


def test_feature_library_load_success() -> None:
    """load should return DataFrame when registry/storage both have data."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {
        "symbol": "BTC",
        "timeframe": "1h",
        "config_hash": "h",
    }

    mock_result = MagicMock()
    mock_result.features_df = pd.DataFrame({"feat_a": [1.0, 2.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    lib = FeatureLibrary(mock_registry, mock_storage)
    df = lib.load("BTC", "1h")
    assert len(df) == 2


def test_feature_library_load_raises_on_missing() -> None:
    """load should raise FeatureNotFoundError when no registry entry exists."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = None
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    with pytest.raises(FeatureNotFoundError):
        lib.load("NONEXIST", "1h")


def test_feature_library_load_multi_raises_on_any_missing() -> None:
    """load_multi should raise FeatureNotFoundError if any symbol is missing."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()

    def fake_find(symbol: str, timeframe: str):
        if symbol == "BTC":
            return {"symbol": "BTC", "timeframe": "1h", "config_hash": "h"}
        return None

    mock_registry.find_latest.side_effect = fake_find

    mock_result = MagicMock()
    mock_result.features_df = pd.DataFrame({"f": [1.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    lib = FeatureLibrary(mock_registry, mock_storage)
    with pytest.raises(FeatureNotFoundError):
        lib.load_multi(["BTC", "ETH"], "1h")


def test_feature_library_ensure_fresh_true() -> None:
    """ensure_fresh should return True when config hash matches."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {"config_hash": "target_hash"}
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    assert lib.ensure_fresh("BTC", "1h", "target_hash") is True


def test_feature_library_ensure_fresh_false_when_stale() -> None:
    """ensure_fresh should return False when config hash differs."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {"config_hash": "old_hash"}
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    assert lib.ensure_fresh("BTC", "1h", "new_hash") is False
