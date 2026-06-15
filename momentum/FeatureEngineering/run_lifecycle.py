"""Safe lifecycle operations for persisted feature runs."""

from __future__ import annotations

import json
import os
import shutil
import stat
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from momentum.FeatureEngineering.feature_registry import FeatureRegistry, RegistryCorruptError
from momentum.FeatureEngineering.run_locks import RunBusyError, RunLease
from momentum.FeatureEngineering.run_paths import cgsa_work_dir, features_run_dir, validate_config_hash


@dataclass
class DeleteResult:
    """單一 run 刪除結果。"""

    symbol: str
    timeframe: str
    config_hash: str
    features_deleted: bool = False
    cgsa_deleted: bool = False
    registry_removed: bool = False
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    features_bytes: int = 0
    cgsa_bytes: int = 0

    @property
    def total_bytes(self) -> int:
        return self.features_bytes + self.cgsa_bytes


@dataclass
class CleanupReport:
    """自動保留策略執行摘要。"""

    symbol: str
    timeframe: str
    keep_latest: int
    deleted: List[DeleteResult] = field(default_factory=list)
    skipped_busy: List[str] = field(default_factory=list)
    skipped_named: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RunLifecycleManager:
    """Coordinate leases, safe deletion, registry state, and retention."""

    _singleflight_guard = threading.Lock()
    _singleflight: Dict[Tuple[str, str], threading.Lock] = {}

    def __init__(
        self,
        features_root: Path,
        cgsa_root: Path,
        locks_dir: Path,
        registry: FeatureRegistry,
    ) -> None:
        self.features_root = Path(features_root)
        self.cgsa_root = Path(cgsa_root)
        self.locks_dir = Path(locks_dir)
        self.registry = registry

    def delete_run(self, symbol: str, timeframe: str, config_hash: str) -> DeleteResult:
        """取得 lease 後安全刪除單一 run。"""
        validate_config_hash(config_hash)
        lease = RunLease.acquire(self.locks_dir, symbol, timeframe, config_hash, timeout=0)
        try:
            return self._delete_run_locked(symbol, timeframe, config_hash, lease)
        finally:
            lease.release()

    def _delete_run_locked(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        lease: RunLease,
    ) -> DeleteResult:
        """在 caller-held lease 下執行刪除，不自行取鎖。"""
        if not lease.active:
            raise RuntimeError("delete requires an active run lease")
        result = DeleteResult(symbol, timeframe, config_hash)
        feature_leaf = features_run_dir(self.features_root, symbol, timeframe, config_hash)
        self._delete_leaf(feature_leaf, self.features_root, "features", result)

        override = os.getenv("FFACT_CGSA_WORK_DIR", "").strip()
        if override:
            result.skipped.append("work_dir_override")
        else:
            cgsa_leaf = cgsa_work_dir(self.cgsa_root, symbol, timeframe, config_hash)
            if cgsa_leaf.exists() or cgsa_leaf.is_symlink():
                manifest_path = cgsa_leaf / "manifest.json"
                if not manifest_path.is_file() or manifest_path.stat().st_size == 0:
                    result.skipped.append("no_manifest")
                else:
                    try:
                        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        result.errors.append(f"cgsa manifest: {exc}")
                    else:
                        if manifest.get("config_hash") != config_hash:
                            result.skipped.append("ownership_mismatch")
                        else:
                            self._delete_leaf(cgsa_leaf, self.cgsa_root, "cgsa", result)

        if not result.errors:
            result.registry_removed = self.registry.remove(symbol, timeframe, config_hash)
        return result

    def set_run_alias(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        alias: Optional[str],
    ) -> None:
        """以 run lease 將 alias mutation 與刪除互斥。"""
        validate_config_hash(config_hash)
        lease = RunLease.acquire(self.locks_dir, symbol, timeframe, config_hash, timeout=0)
        try:
            self.registry.set_alias(symbol, timeframe, config_hash, alias)
        finally:
            lease.release()

    def auto_cleanup(self, symbol: str, timeframe: str, keep_latest: int = 5) -> CleanupReport:
        """保留最新未命名 runs，命名 runs 永不自動清除。"""
        if keep_latest < 0:
            raise ValueError("keep_latest must be non-negative")
        if self.registry.corrupt:
            raise RegistryCorruptError("Cannot clean a corrupt registry")
        lock = self._singleflight_lock(symbol, timeframe)
        with lock:
            report = CleanupReport(symbol, timeframe, keep_latest)
            entries = sorted(
                (
                    entry
                    for entry in self.registry.find(symbol, timeframe)
                    if not entry.get("alias")
                ),
                key=lambda entry: entry.get(
                    "last_generated_at", entry.get("created_at", 0)
                ),
                reverse=True,
            )
            for entry in entries[keep_latest:]:
                config_hash = str(entry.get("config_hash", ""))
                try:
                    lease = RunLease.acquire(
                        self.locks_dir, symbol, timeframe, config_hash, timeout=0
                    )
                except RunBusyError:
                    report.skipped_busy.append(config_hash)
                    continue
                marked = False
                try:
                    marked = self.registry.mark_deleting(symbol, timeframe, config_hash)
                    if not marked:
                        report.skipped_named.append(config_hash)
                        continue
                    result = self._delete_run_locked(symbol, timeframe, config_hash, lease)
                    report.deleted.append(result)
                    report.errors.extend(result.errors)
                    if result.errors:
                        self.registry.clear_deleting(symbol, timeframe, config_hash)
                except Exception as exc:
                    report.errors.append(f"{config_hash}: {exc}")
                    if marked:
                        self.registry.clear_deleting(symbol, timeframe, config_hash)
                finally:
                    lease.release()
            return report

    @classmethod
    def _singleflight_lock(cls, symbol: str, timeframe: str) -> threading.Lock:
        key = (symbol, timeframe)
        with cls._singleflight_guard:
            return cls._singleflight.setdefault(key, threading.Lock())

    def _delete_leaf(
        self,
        leaf: Path,
        root: Path,
        kind: str,
        result: DeleteResult,
    ) -> None:
        if not leaf.exists() and not leaf.is_symlink():
            return
        try:
            expected_depth = 3 if kind == "features" else 1
            self._validate_leaf(leaf, root, expected_depth)
            size = self._directory_size(leaf)
            shutil.rmtree(leaf)
        except OSError as exc:
            result.errors.append(f"{kind}: {exc}")
            return
        if kind == "features":
            result.features_deleted = True
            result.features_bytes = size
        else:
            result.cgsa_deleted = True
            result.cgsa_bytes = size

    @staticmethod
    def _validate_leaf(leaf: Path, root: Path, expected_depth: int) -> None:
        resolved_root = root.resolve()
        relative = leaf.relative_to(root)
        current = root
        for component in relative.parts:
            current = current / component
            mode = os.lstat(current).st_mode
            if stat.S_ISLNK(mode):
                raise OSError(f"symlink component rejected: {current}")
        resolved_leaf = leaf.resolve()
        if not resolved_leaf.is_relative_to(resolved_root):
            raise OSError(f"path escapes allowed root: {leaf}")
        if len(relative.parts) != expected_depth or resolved_leaf == resolved_root:
            raise OSError(f"path is not a run leaf: {leaf}")

    @staticmethod
    def _directory_size(path: Path) -> int:
        total = 0
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        return total
