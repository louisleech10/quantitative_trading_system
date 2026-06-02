"""Feature generation registry tracking generated feature datasets."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from momentum.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_REGISTRY_PATH = Path("data_cache/features/registry.json")


class FeatureRegistry:
    """Registry persisted as a JSON file with per-config upsert semantics."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or DEFAULT_REGISTRY_PATH
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._entries = []
            return

        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._entries = data if isinstance(data, list) else []
            logger.info("Loaded feature registry with %d entries", len(self._entries))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load feature registry, starting fresh: %s", exc)
            self._entries = []

    def add(self, entry: Dict[str, Any]) -> None:
        """Add or update one entry and persist the registry atomically."""
        required_keys = {"symbol", "timeframe", "config_hash"}
        missing = required_keys - set(entry.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")

        if "created_at" not in entry:
            entry["created_at"] = time.time()

        key = (
            str(entry["symbol"]),
            str(entry["timeframe"]),
            str(entry["config_hash"]),
        )
        for idx, existing in enumerate(self._entries):
            existing_key = (
                str(existing.get("symbol")),
                str(existing.get("timeframe")),
                str(existing.get("config_hash")),
            )
            if existing_key == key:
                self._entries[idx] = entry
                self._persist()
                return

        self._entries.append(entry)
        self._persist()

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def find(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        return [
            item
            for item in self._entries
            if item.get("symbol") == symbol and item.get("timeframe") == timeframe
        ]

    def find_latest(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        matches = self.find(symbol, timeframe)
        if not matches:
            return None
        return max(matches, key=lambda item: item.get("created_at", 0))

    def _persist(self) -> None:
        """Persist via tempfile then rename for atomic replacement."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2, default=str)
            os.rename(temp_path, str(self._path))
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
