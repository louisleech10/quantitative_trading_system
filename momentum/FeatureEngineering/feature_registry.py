"""Feature generation registry tracking generated feature datasets."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

from momentum.FeatureEngineering.run_locks import RunBusyError
from momentum.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_REGISTRY_PATH = Path("data_cache/features/registry.json")
_T = TypeVar("_T")


class RegistryCorruptError(RuntimeError):
    """Registry 無法安全解析。"""


class RegistryLockTimeout(RuntimeError):
    """Registry transaction lock 逾時。"""


class FeatureRegistry:
    """Registry persisted as atomic, lock-serialized transactions."""

    LOCK_TIMEOUT_SECONDS = 30.0
    LOCK_INITIAL_BACKOFF_SECONDS = 0.01
    LOCK_MAX_BACKOFF_SECONDS = 0.5

    def __init__(self, path: Optional[Path] = None) -> None:
        env_path = os.getenv("FFACT_FEATURE_REGISTRY_PATH", "").strip()
        if path is not None:
            self._path = path
        elif env_path:
            self._path = Path(env_path).expanduser()
        else:
            self._path = DEFAULT_REGISTRY_PATH
        self._entries: List[Dict[str, Any]] = []
        self._corrupt = False
        self._corrupt_backup_created = False
        self._load()

    @property
    def corrupt(self) -> bool:
        """回傳 registry 是否處於 fail-closed 狀態。"""
        return self._corrupt

    def _load(self) -> None:
        if not self._path.exists():
            self._entries = []
            self._corrupt = False
            return
        try:
            with self._path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                raise ValueError("registry root must be a list")
            self._entries = data
            self._corrupt = False
            logger.info("Loaded feature registry with %d entries", len(self._entries))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to load feature registry: %s", exc)
            self._entries = []
            self._corrupt = True
            self._backup_corrupt_registry()

    def _backup_corrupt_registry(self) -> None:
        if self._corrupt_backup_created or not self._path.exists():
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = self._path.with_name(f"{self._path.name}.corrupt-{timestamp}")
        try:
            shutil.copy2(self._path, backup)
            self._corrupt_backup_created = True
        except OSError as exc:
            logger.error("Failed to back up corrupt registry: %s", exc, exc_info=True)

    def add(self, entry: Dict[str, Any]) -> None:
        """Add/upsert while preserving user-managed and historical fields."""
        required_keys = {"symbol", "timeframe", "config_hash"}
        missing = required_keys - set(entry.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")
        incoming = dict(entry)
        incoming.setdefault("created_at", time.time())
        incoming.setdefault("last_generated_at", incoming["created_at"])
        incoming_batch_id = incoming.get("batch_id")

        def mutate() -> None:
            key = self._key(incoming)
            for index, existing in enumerate(self._entries):
                if self._key(existing) != key:
                    continue
                merged = dict(incoming)
                for field in ("alias", "size_bytes", "created_at"):
                    if existing.get(field) not in (None, ""):
                        merged[field] = existing[field]
                self._apply_batch_id_merge(existing, merged, incoming_batch_id)
                self._entries[index] = merged
                return
            if incoming_batch_id is None:
                incoming.pop("batch_id", None)
                incoming.pop("batch_alias", None)
            self._entries.append(incoming)

        if self._corrupt:
            mutate()
            logger.error("Registry is corrupt; add retained in memory without persistence")
            return
        self._locked_mutate(mutate)

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
        return max(
            matches,
            key=lambda item: item.get("last_generated_at", item.get("created_at", 0)),
        )

    def get(self, symbol: str, timeframe: str, config_hash: str) -> Optional[Dict[str, Any]]:
        """讀取單一 entry；mutation 安全由 lease/deleting 協定保證。"""
        entry = self._find_entry(symbol, timeframe, config_hash)
        return dict(entry) if entry is not None else None

    def set_alias(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        alias: Optional[str],
    ) -> None:
        """設定或移除 run alias。"""
        normalized = alias.strip() if alias is not None else ""

        def mutate() -> None:
            target = self._require_entry(symbol, timeframe, config_hash)
            if target.get("deleting"):
                raise RunBusyError("Run is being deleted")
            if normalized and any(
                item is not target
                and item.get("symbol") == symbol
                and item.get("timeframe") == timeframe
                and item.get("alias") == normalized
                for item in self._entries
            ):
                raise ValueError(f"Alias already exists: {normalized}")
            if normalized:
                target["alias"] = normalized
            else:
                target.pop("alias", None)

        self._require_healthy()
        self._locked_mutate(mutate)

    def set_batch_alias(self, batch_id: str, batch_alias: Optional[str]) -> int:
        """更新同 batch_id 所有 entry 的 batch_alias；空字串視為清除。"""
        normalized = batch_alias.strip() if batch_alias is not None else ""
        affected = 0

        def mutate() -> None:
            nonlocal affected
            targets = [
                item
                for item in self._entries
                if str(item.get("batch_id") or "") == batch_id
            ]
            if not targets:
                raise KeyError(batch_id)
            for target in targets:
                if target.get("deleting"):
                    raise RunBusyError("Run is being deleted")
            for target in targets:
                if normalized:
                    target["batch_alias"] = normalized
                else:
                    target.pop("batch_alias", None)
                affected += 1

        self._require_healthy()
        self._locked_mutate(mutate)
        return affected

    def remove(self, symbol: str, timeframe: str, config_hash: str) -> bool:
        """移除單一 registry entry。"""
        removed = False

        def mutate() -> None:
            nonlocal removed
            key = (symbol, timeframe, config_hash)
            original = len(self._entries)
            self._entries = [item for item in self._entries if self._key(item) != key]
            removed = len(self._entries) != original

        self._require_healthy()
        self._locked_mutate(mutate)
        return removed

    def mark_deleting(self, symbol: str, timeframe: str, config_hash: str) -> bool:
        """在 transaction 內重新確認 alias/batch_alias 並標記刪除。"""
        marked = False

        def mutate() -> None:
            nonlocal marked
            target = self._require_entry(symbol, timeframe, config_hash)
            if target.get("alias") or target.get("batch_alias"):
                return
            target["deleting"] = True
            marked = True

        self._require_healthy()
        self._locked_mutate(mutate)
        return marked

    def mark_deleting_for_delete(self, symbol: str, timeframe: str, config_hash: str) -> bool:
        """明確刪除路徑標記 deleting；允許 alias/batch_alias run（override auto-cleanup 保護）。"""
        marked = False

        def mutate() -> None:
            nonlocal marked
            target = self._find_entry(symbol, timeframe, config_hash)
            if target is None:
                return
            target["deleting"] = True
            marked = True

        self._require_healthy()
        self._locked_mutate(mutate)
        return marked

    def clear_deleting(self, symbol: str, timeframe: str, config_hash: str) -> bool:
        """清除失敗 cleanup 留下的 deleting 標記。"""
        cleared = False

        def mutate() -> None:
            nonlocal cleared
            target = self._find_entry(symbol, timeframe, config_hash)
            if target is not None and target.pop("deleting", None) is not None:
                cleared = True

        self._require_healthy()
        self._locked_mutate(mutate)
        return cleared

    def _locked_mutate(self, fn: Callable[[], _T]) -> _T:
        """以 lockfile 序列化 reload/mutate/persist transaction。"""
        lock_path = self._path.with_name(f"{self._path.name}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.LOCK_TIMEOUT_SECONDS
        backoff = self.LOCK_INITIAL_BACKOFF_SECONDS
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                break
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise RegistryLockTimeout(f"Registry lock timed out: {lock_path}") from exc
                time.sleep(backoff)
                backoff = min(backoff * 2, self.LOCK_MAX_BACKOFF_SECONDS)
        try:
            self._load()
            self._require_healthy()
            result = fn()
            self._persist()
            return result
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _key(entry: Dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(entry.get("symbol")),
            str(entry.get("timeframe")),
            str(entry.get("config_hash")),
        )

    @staticmethod
    def _apply_batch_id_merge(
        existing: Dict[str, Any],
        merged: Dict[str, Any],
        incoming_batch_id: Any,
    ) -> None:
        """三態 batch_id overwrite：同批保留、換批 reset、None merge-preserve。"""
        existing_batch_id = existing.get("batch_id")
        incoming_has_concrete_batch_id = incoming_batch_id not in (None, "")

        if not incoming_has_concrete_batch_id:
            if existing_batch_id not in (None, ""):
                merged["batch_id"] = existing_batch_id
            else:
                merged.pop("batch_id", None)
            if existing.get("batch_alias") not in (None, ""):
                merged["batch_alias"] = existing["batch_alias"]
            else:
                merged.pop("batch_alias", None)
            return

        if str(incoming_batch_id) == str(existing_batch_id or ""):
            merged["batch_id"] = incoming_batch_id
            if existing.get("batch_alias") not in (None, ""):
                merged["batch_alias"] = existing["batch_alias"]
            else:
                merged.pop("batch_alias", None)
            return

        merged["batch_id"] = incoming_batch_id
        merged.pop("batch_alias", None)

    def _find_entry(self, symbol: str, timeframe: str, config_hash: str) -> Optional[Dict[str, Any]]:
        key = (symbol, timeframe, config_hash)
        return next((item for item in self._entries if self._key(item) == key), None)

    def _require_entry(self, symbol: str, timeframe: str, config_hash: str) -> Dict[str, Any]:
        entry = self._find_entry(symbol, timeframe, config_hash)
        if entry is None:
            raise KeyError((symbol, timeframe, config_hash))
        return entry

    def _require_healthy(self) -> None:
        if self._corrupt:
            raise RegistryCorruptError(f"Registry is corrupt: {self._path}")

    def _persist(self) -> None:
        """Persist via tempfile then atomic replacement."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            if self._path.exists():
                try:
                    shutil.copy2(self._path, self._path.with_name(f"{self._path.name}.bak"))
                except OSError as exc:
                    logger.error("Failed to back up registry: %s", exc, exc_info=True)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(self._entries, file, ensure_ascii=False, indent=2, default=str)
            os.replace(temp_path, str(self._path))
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
