"""Phase 1 tests: float32, get_last_timestamp, config_hash, log_volume."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pandas as pd


# ── T1-01: save_features_to_hdf5 writes float32 ──

def test_save_features_to_hdf5_writes_float32() -> None:
    """save_features_to_hdf5 should write float32, not float64."""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    storage = FeatureStorage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage.base_path = Path(tmpdir)
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10, freq="h"),
                "feat_a": np.random.randn(10).astype(np.float64),
                "feat_b": np.random.randn(10).astype(np.float64),
            }
        )
        path = storage.save_features_to_hdf5(
            case_id="test_case",
            symbol="BTCUSDT",
            timeframe="1h",
            features_df=df,
            feature_names=["feat_a", "feat_b"],
        )
        with h5py.File(path, "r") as f:
            ds = f["BTCUSDT/1h/features"]
            assert ds.dtype == np.float32, f"Expected float32, got {ds.dtype}"


# ── T1-02: load_factory_output returns float32 ──

def test_load_factory_output_returns_float32() -> None:
    """load_factory_output should return float32 even if stored as float64."""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    storage = FeatureStorage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage.base_path = Path(tmpdir)
        hdf5_file = Path(tmpdir) / "TESTUSDT_1h_factory.h5"

        with h5py.File(hdf5_file, "w") as f:
            group = f.create_group("TESTUSDT/1h")
            group.create_dataset(
                "features",
                data=np.array([[1.0], [2.0], [3.0]], dtype=np.float64),
            )
            group.create_dataset(
                "timestamps",
                data=np.array([1, 2, 3], dtype=np.int64),
            )
            str_dtype = h5py.string_dtype(encoding="utf-8")
            group.create_dataset(
                "feature_names",
                data=np.array(["feat_a"], dtype=object),
                dtype=str_dtype,
            )
            group.attrs["metadata_json"] = "{}"

        result = storage.load_factory_output("TESTUSDT", "1h")
        assert result is not None
        assert result.features_df["feat_a"].dtype == np.float32


# ── T1-03: KlineStorageManager.get_last_timestamp returns None for non-existent ──

def test_kline_storage_get_last_timestamp_nonexistent() -> None:
    """get_last_timestamp should return None when storage file does not exist."""
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    mgr = KlineStorageManager()
    result = mgr.get_last_timestamp("NONEXISTUSDT", "1h")
    assert result is None


# ── T1-04: get_last_timestamp returns None for empty dataset ──

def test_get_last_timestamp_empty_dataset() -> None:
    """get_last_timestamp should return None when HDF5 dataset is empty."""
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    mgr = KlineStorageManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        hdf5_path = Path(tmpdir) / "EMPTYUSDT_1h.h5"
        dt = np.dtype([("timestamp", "<i8"), ("close", "<f4")])
        with h5py.File(hdf5_path, "w") as f:
            f.create_dataset("EMPTYUSDT/1h/data", shape=(0,), dtype=dt)

        with patch.object(mgr, "_get_hdf5_path", return_value=hdf5_path):
            result = mgr.get_last_timestamp("EMPTYUSDT", "1h")
            assert result is None


# ── T1-05: get_last_timestamp returns int from non-empty dataset ──

def test_get_last_timestamp_non_empty_dataset() -> None:
    """get_last_timestamp should return last timestamp for non-empty dataset."""
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    mgr = KlineStorageManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        hdf5_path = Path(tmpdir) / "BTCUSDT_1h.h5"
        dt = np.dtype([("timestamp", "<i8"), ("close", "<f4")])
        data = np.array([(1000, 1.0), (2000, 2.0), (3000, 3.0)], dtype=dt)
        with h5py.File(hdf5_path, "w") as f:
            f.create_dataset("BTCUSDT/1h/data", data=data)

        with patch.object(mgr, "_get_hdf5_path", return_value=hdf5_path):
            result = mgr.get_last_timestamp("BTCUSDT", "1h")
            assert result == 3000


# ── T1-06: CryptoSpotAdapter.get_last_timestamp delegates ──

def test_crypto_spot_adapter_get_last_timestamp() -> None:
    """CryptoSpotAdapter should delegate to KlineStorageManager."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    mock_storage = MagicMock()
    mock_storage.get_last_timestamp.return_value = 1700000000000
    adapter = CryptoSpotAdapter(mock_storage)

    result = adapter.get_last_timestamp("BTCUSDT", "1h")
    assert result == 1700000000000
    mock_storage.get_last_timestamp.assert_called_once_with("BTCUSDT", "1h")


# ── T1-07: AdapterRegistry.get_last_timestamp picks max ──

def test_adapter_registry_get_last_timestamp_picks_max() -> None:
    """AdapterRegistry should return latest timestamp across adapters."""
    from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry

    registry = AdapterRegistry()

    adapter1 = MagicMock()
    adapter1.name = "source_a"
    adapter1.get_last_timestamp.return_value = 1000

    adapter2 = MagicMock()
    adapter2.name = "source_b"
    adapter2.get_last_timestamp.return_value = 2000

    registry.register(adapter1)
    registry.register(adapter2)

    result = registry.get_last_timestamp("BTCUSDT", "1h")
    assert result == 2000


# ── T1-08: AdapterRegistry.get_last_timestamp all None ──

def test_adapter_registry_get_last_timestamp_all_none() -> None:
    """When all adapters return None, registry should return None."""
    from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry

    registry = AdapterRegistry()
    adapter = MagicMock()
    adapter.name = "src"
    adapter.get_last_timestamp.return_value = None
    registry.register(adapter)

    assert registry.get_last_timestamp("X", "1h") is None


# ── T1-09: config_hash changes when kline timestamp changes ──

def test_config_hash_changes_with_kline_update() -> None:
    """config_hash should differ when kline_last_ts changes."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = MagicMock()
    factory._adapter_registry = MagicMock()

    mock_config = MagicMock()
    mock_config.model_dump.return_value = {"a": 1, "timeframes": {"training": ["1h"]}}

    factory._adapter_registry.get_last_timestamp.return_value = 1000
    hash1 = factory._compute_config_hash(mock_config, "BTC", "1h")

    factory._adapter_registry.get_last_timestamp.return_value = 2000
    hash2 = factory._compute_config_hash(mock_config, "BTC", "1h")

    assert hash1 != hash2


# ── T1-10: config_hash stable when unchanged ──

def test_config_hash_stable_when_unchanged() -> None:
    """config_hash should be deterministic for same inputs."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = MagicMock()
    factory._adapter_registry = MagicMock()

    mock_config = MagicMock()
    mock_config.model_dump.return_value = {"a": 1, "timeframes": {"training": ["1h"]}}

    factory._adapter_registry.get_last_timestamp.return_value = 1000
    hash1 = factory._compute_config_hash(mock_config, "BTC", "1h")
    hash2 = factory._compute_config_hash(mock_config, "BTC", "1h")

    assert hash1 == hash2


# ── T1-11: log-volume in available_fields ──

def test_log_volume_in_available_fields() -> None:
    """CryptoSpotAdapter.available_fields should include log-volume fields."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    adapter = CryptoSpotAdapter(MagicMock())
    assert "log-volume" in adapter.available_fields
    assert "log-quote-volume" in adapter.available_fields


# ── T1-12: log-volume non-negative ──

def test_log_volume_non_negative() -> None:
    """log-volume should be non-negative for non-negative volume inputs."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    adapter = CryptoSpotAdapter(MagicMock())

    df = pd.DataFrame(
        {
            "open": [1.0, 2.0],
            "high": [2.0, 3.0],
            "low": [0.5, 1.5],
            "close": [1.5, 2.5],
            "volume": [0.0, 100.0],
            "quote_volume": [0.0, 1000.0],
        }
    )

    result = adapter._add_synthetic_fields(df.copy())
    assert (result["log-volume"] >= 0).all()
    assert (result["log-quote-volume"] >= 0).all()


# ── T1-13: log-volume dtype float32 ──

def test_log_volume_dtype_float32() -> None:
    """log-volume and log-quote-volume should be float32."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    adapter = CryptoSpotAdapter(MagicMock())

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [2.0],
            "low": [0.5],
            "close": [1.5],
            "volume": [10.0],
            "quote_volume": [100.0],
        }
    )

    result = adapter._add_synthetic_fields(df.copy())
    assert result["log-volume"].dtype == np.float32
    assert result["log-quote-volume"].dtype == np.float32


# ── T1-14: log-quote-volume fallback when quote_volume missing ──

def test_log_quote_volume_fallback_when_missing() -> None:
    """log-quote-volume should fallback to 0.0 when quote_volume is missing."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    adapter = CryptoSpotAdapter(MagicMock())

    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [2.0],
            "low": [0.5],
            "close": [1.5],
            "volume": [0.0],
        }
    )

    result = adapter._add_synthetic_fields(df.copy())
    assert float(result["log-quote-volume"].iloc[0]) == 0.0
    assert result["log-quote-volume"].dtype == np.float32
