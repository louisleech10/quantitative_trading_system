"""Watchlist persistence service (Phase D)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import List, Optional

from api.core.config import settings
from api.core.logging import get_logger
from api.models.watchlist_models import WatchlistEntryModel, WatchlistQueryResponse


logger = get_logger(__name__)

MAX_WATCHLIST_ENTRIES = 500


@dataclass
class _WatchlistFilePaths:
    base_dir: Path
    data_file: Path


class WatchlistService:
    """Persist watchlist entries to JSON for cross-session usage."""

    def __init__(self, data_cache_root: Optional[Path] = None) -> None:
        root = data_cache_root or settings.data_cache_path
        base_dir = Path(root) / "watchlists"
        data_file = base_dir / "watchlist_v1.json"
        self._paths = _WatchlistFilePaths(base_dir=base_dir, data_file=data_file)
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self._paths.base_dir.mkdir(parents=True, exist_ok=True)
        if self._paths.data_file.exists():
            return

        payload = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": [],
        }
        self._write_payload(payload)

    def _read_payload(self) -> dict:
        try:
            raw = self._paths.data_file.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except FileNotFoundError:
            self._ensure_storage()
            return self._read_payload()
        except json.JSONDecodeError:
            logger.warning("Watchlist JSON damaged, reset to empty payload")
            payload = {
                "version": "1.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "entries": [],
            }
            self._write_payload(payload)

        if not isinstance(payload, dict):
            raise ValueError("watchlist payload format invalid")
        if payload.get("version") != "1.0":
            raise ValueError("watchlist version 不支援")

        entries = payload.get("entries")
        if not isinstance(entries, list):
            raise ValueError("watchlist entries format invalid")

        return payload

    def _write_payload(self, payload: dict) -> None:
        self._paths.data_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _to_entry_list(raw_entries: list) -> List[WatchlistEntryModel]:
        parsed: List[WatchlistEntryModel] = []
        for item in raw_entries:
            try:
                parsed.append(WatchlistEntryModel.model_validate(item))
            except Exception:
                continue
        return parsed

    @staticmethod
    def _deduplicate_and_sort(entries: List[WatchlistEntryModel]) -> List[WatchlistEntryModel]:
        by_feature: dict[str, WatchlistEntryModel] = {}
        for entry in entries:
            existing = by_feature.get(entry.feature_name)
            if existing is None or entry.updated_at >= existing.updated_at:
                by_feature[entry.feature_name] = entry

        ordered = sorted(
            by_feature.values(),
            key=lambda item: item.updated_at,
            reverse=True,
        )
        return ordered[:MAX_WATCHLIST_ENTRIES]

    def get_entries(self, status: Optional[str] = None) -> WatchlistQueryResponse:
        with self._lock:
            payload = self._read_payload()

        entries = self._deduplicate_and_sort(self._to_entry_list(payload.get("entries", [])))
        if status:
            entries = [entry for entry in entries if entry.status == status]

        updated_at_raw = payload.get("updated_at")
        updated_at = datetime.now(timezone.utc)
        if isinstance(updated_at_raw, str):
            try:
                updated_at = datetime.fromisoformat(updated_at_raw)
            except ValueError:
                updated_at = datetime.now(timezone.utc)

        return WatchlistQueryResponse(
            version="1.0",
            updated_at=updated_at,
            entries=entries,
        )

    def replace_entries(self, entries: List[WatchlistEntryModel]) -> WatchlistQueryResponse:
        if len(entries) > MAX_WATCHLIST_ENTRIES:
            raise ValueError(f"Watchlist 容量上限為 {MAX_WATCHLIST_ENTRIES}")

        normalized = self._deduplicate_and_sort(entries)
        now = datetime.now(timezone.utc)
        payload = {
            "version": "1.0",
            "updated_at": now.isoformat(),
            "entries": [entry.model_dump(mode="json") for entry in normalized],
        }

        with self._lock:
            self._write_payload(payload)

        logger.info("Watchlist synced: entries=%s", len(normalized))
        return WatchlistQueryResponse(
            version="1.0",
            updated_at=now,
            entries=normalized,
        )


_watchlist_service: Optional[WatchlistService] = None


def get_watchlist_service() -> WatchlistService:
    global _watchlist_service
    if _watchlist_service is None:
        _watchlist_service = WatchlistService()
    return _watchlist_service
