"""Phase 2 tests: registry persistence and restore."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def test_registry_add_and_list() -> None:
    """Add entries and verify list_all returns all of them."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = FeatureRegistry(Path(tmpdir) / "registry.json")
        registry.add({"symbol": "BTCUSDT", "timeframe": "1h", "config_hash": "hash-a"})
        registry.add({"symbol": "ETHUSDT", "timeframe": "4h", "config_hash": "hash-b"})

        entries = registry.list_all()
        assert len(entries) == 2


def test_registry_persist_and_reload() -> None:
    """Entries should persist to disk and be loaded by a new instance."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"

        registry_first = FeatureRegistry(registry_path)
        registry_first.add(
            {"symbol": "BTCUSDT", "timeframe": "1h", "config_hash": "persist-hash"}
        )

        registry_second = FeatureRegistry(registry_path)
        entries = registry_second.list_all()
        assert len(entries) == 1
        assert entries[0]["config_hash"] == "persist-hash"


def test_registry_find_latest() -> None:
    """find_latest should return the entry with the largest created_at."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = FeatureRegistry(Path(tmpdir) / "registry.json")
        registry.add(
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "config_hash": "old-hash",
                "created_at": 100,
            }
        )
        registry.add(
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "config_hash": "new-hash",
                "created_at": 200,
            }
        )

        latest = registry.find_latest("BTCUSDT", "1h")
        assert latest is not None
        assert latest["config_hash"] == "new-hash"


def test_registry_missing_keys_raises() -> None:
    """add should raise ValueError when required keys are missing."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = FeatureRegistry(Path(tmpdir) / "registry.json")
        with pytest.raises(ValueError, match="Missing required keys"):
            registry.add({"symbol": "BTCUSDT"})


def test_registry_corrupt_json_recovers() -> None:
    """Corrupt JSON should not crash loading and should recover as empty list."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"
        registry_path.write_text("{invalid json", encoding="utf-8")

        registry = FeatureRegistry(registry_path)
        assert registry.list_all() == []


def test_registry_atomic_write_creates_valid_json() -> None:
    """Persisted file should always be valid JSON after add."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"
        registry = FeatureRegistry(registry_path)
        registry.add({"symbol": "X", "timeframe": "1h", "config_hash": "h"})

        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        assert isinstance(payload, list)
        assert len(payload) == 1
