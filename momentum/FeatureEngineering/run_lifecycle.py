"""Safe lifecycle operations for persisted feature runs."""

from __future__ import annotations

import json
import os
import shutil
import stat
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from momentum.FeatureEngineering.feature_registry import FeatureRegistry, RegistryCorruptError
from momentum.FeatureEngineering.run_locks import RunBusyError, RunLease, is_run_active
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


@dataclass
class OrphanEntry:
    """單一孤兒條目（registry↔leaf 不一致）。"""

    kind: str
    symbol: str
    timeframe: str
    config_hash: str
    leaf_kind: Optional[str] = None


@dataclass
class OrphanReport:
    """孤兒掃描/清理摘要。"""

    orphans: List[OrphanEntry] = field(default_factory=list)
    cleaned_registry: int = 0
    cleaned_leaves: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = True


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
        """取得 lease 後安全刪除單一 run（統一 orchestration: mark→delete→remove/clear）。"""
        validate_config_hash(config_hash)
        lease = RunLease.acquire(self.locks_dir, symbol, timeframe, config_hash, timeout=0)
        try:
            return self._orchestrated_delete_locked(symbol, timeframe, config_hash, lease)
        finally:
            lease.release()

    def _orchestrated_delete_locked(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        lease: RunLease,
    ) -> DeleteResult:
        """在 caller-held lease 下執行 mark-deleting→delete→remove/clear。"""
        if not lease.active:
            raise RuntimeError("delete requires an active run lease")
        marked = False
        try:
            marked = self.registry.mark_deleting_for_delete(symbol, timeframe, config_hash)
            result = self._delete_run_locked(symbol, timeframe, config_hash, lease)
            if result.errors and marked:
                self.registry.clear_deleting(symbol, timeframe, config_hash)
            return result
        except Exception:
            if marked:
                self.registry.clear_deleting(symbol, timeframe, config_hash)
            raise

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
                    if not (entry.get("alias") or entry.get("batch_alias"))
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

    def scan_orphans(self) -> OrphanReport:
        """掃描 registry 與 features/CGSA leaf 不一致的孤兒條目。"""
        report = OrphanReport(dry_run=True)
        registry_keys = self._registry_key_set()
        seen_orphans: set[Tuple[str, str, str, str]] = set()

        for entry in self.registry.list_all():
            symbol = str(entry.get("symbol", ""))
            timeframe = str(entry.get("timeframe", ""))
            config_hash = str(entry.get("config_hash", ""))
            if not symbol or not timeframe or not config_hash:
                continue
            if self._is_protected_run(symbol, timeframe, config_hash, entry):
                continue
            feature_leaf = features_run_dir(self.features_root, symbol, timeframe, config_hash)
            cgsa_leaf = self._resolve_cgsa_leaf(symbol, timeframe, config_hash)
            features_exists = feature_leaf.exists() or feature_leaf.is_symlink()
            cgsa_exists = cgsa_leaf.exists() or cgsa_leaf.is_symlink()
            if features_exists or cgsa_exists:
                continue
            key = ("registry_without_leaf", symbol, timeframe, config_hash)
            if key not in seen_orphans:
                seen_orphans.add(key)
                report.orphans.append(OrphanEntry(
                    kind="registry_without_leaf",
                    symbol=symbol,
                    timeframe=timeframe,
                    config_hash=config_hash,
                ))

        for symbol, timeframe, config_hash, leaf_kind in self._iter_disk_leaves():
            identity = (symbol, timeframe, config_hash)
            if identity in registry_keys:
                continue
            entry = self.registry.get(symbol, timeframe, config_hash)
            if entry is not None and entry.get("deleting"):
                continue
            if is_run_active(self.locks_dir, symbol, timeframe, config_hash):
                continue
            key = ("leaf_without_registry", symbol, timeframe, config_hash, leaf_kind)
            if key not in seen_orphans:
                seen_orphans.add(key)
                report.orphans.append(OrphanEntry(
                    kind="leaf_without_registry",
                    symbol=symbol,
                    timeframe=timeframe,
                    config_hash=config_hash,
                    leaf_kind=leaf_kind,
                ))

        return report

    def clean_orphans(self, *, dry_run: bool = True) -> OrphanReport:
        """清理孤兒：registry 有 leaf 無→remove；(features|CGSA) leaf 有 registry 無→刪 leaf。"""
        report = self.scan_orphans()
        report.dry_run = dry_run
        if dry_run:
            return report

        for orphan in list(report.orphans):
            try:
                if orphan.kind == "registry_without_leaf":
                    lease = RunLease.acquire(
                        self.locks_dir,
                        orphan.symbol,
                        orphan.timeframe,
                        orphan.config_hash,
                        timeout=0,
                    )
                    try:
                        if self.registry.remove(orphan.symbol, orphan.timeframe, orphan.config_hash):
                            report.cleaned_registry += 1
                    finally:
                        lease.release()
                elif orphan.kind == "leaf_without_registry":
                    lease = RunLease.acquire(
                        self.locks_dir,
                        orphan.symbol,
                        orphan.timeframe,
                        orphan.config_hash,
                        timeout=0,
                    )
                    try:
                        stub = DeleteResult(orphan.symbol, orphan.timeframe, orphan.config_hash)
                        if orphan.leaf_kind in (None, "features", "both"):
                            feature_leaf = features_run_dir(
                                self.features_root,
                                orphan.symbol,
                                orphan.timeframe,
                                orphan.config_hash,
                            )
                            if feature_leaf.exists() or feature_leaf.is_symlink():
                                self._delete_leaf(feature_leaf, self.features_root, "features", stub)
                        if orphan.leaf_kind in ("cgsa", "both"):
                            cgsa_leaf = self._resolve_cgsa_leaf(
                                orphan.symbol,
                                orphan.timeframe,
                                orphan.config_hash,
                            )
                            if cgsa_leaf.exists() or cgsa_leaf.is_symlink():
                                if self._cgsa_owned_by_run(cgsa_leaf, orphan.config_hash):
                                    self._delete_leaf(cgsa_leaf, self.cgsa_root, "cgsa", stub)
                        if stub.features_deleted or stub.cgsa_deleted:
                            report.cleaned_leaves += 1
                        report.errors.extend(stub.errors)
                    finally:
                        lease.release()
            except RunBusyError:
                report.errors.append(
                    f"{orphan.symbol}/{orphan.timeframe}/{orphan.config_hash}: run_busy"
                )
            except Exception as exc:
                report.errors.append(
                    f"{orphan.symbol}/{orphan.timeframe}/{orphan.config_hash}: {exc}"
                )

        return report

    def _registry_key_set(self) -> set[Tuple[str, str, str]]:
        keys: set[Tuple[str, str, str]] = set()
        for entry in self.registry.list_all():
            symbol = str(entry.get("symbol", ""))
            timeframe = str(entry.get("timeframe", ""))
            config_hash = str(entry.get("config_hash", ""))
            if symbol and timeframe and config_hash:
                keys.add((symbol, timeframe, config_hash))
        return keys

    def _is_protected_run(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        entry: Dict[str, object],
    ) -> bool:
        """active lease 或 deleting 中的 run 不算孤兒。"""
        if entry.get("deleting"):
            return True
        return is_run_active(self.locks_dir, symbol, timeframe, config_hash)

    def _resolve_cgsa_leaf(self, symbol: str, timeframe: str, config_hash: str) -> Path:
        override = os.getenv("FFACT_CGSA_WORK_DIR", "").strip()
        root = Path(override) if override else self.cgsa_root
        return cgsa_work_dir(root, symbol, timeframe, config_hash)

    def _iter_disk_leaves(self) -> Iterator[Tuple[str, str, str, str]]:
        """列舉磁碟上 features 與 CGSA run leaf（含 CGSA-only）。"""
        yielded: set[Tuple[str, str, str]] = set()

        if self.features_root.exists():
            for symbol_dir in sorted(self.features_root.iterdir()):
                if not symbol_dir.is_dir() or symbol_dir.name.startswith("."):
                    continue
                if symbol_dir.name == "registry.json":
                    continue
                for tf_dir in sorted(symbol_dir.iterdir()):
                    if not tf_dir.is_dir():
                        continue
                    for hash_dir in sorted(tf_dir.iterdir()):
                        if not hash_dir.is_dir():
                            continue
                        try:
                            validate_config_hash(hash_dir.name)
                        except ValueError:
                            continue
                        identity = (symbol_dir.name, tf_dir.name, hash_dir.name)
                        if identity in yielded:
                            continue
                        yielded.add(identity)
                        cgsa_leaf = self._resolve_cgsa_leaf(*identity)
                        leaf_kind = "both" if cgsa_leaf.exists() or cgsa_leaf.is_symlink() else "features"
                        yield symbol_dir.name, tf_dir.name, hash_dir.name, leaf_kind

        cgsa_root = Path(os.getenv("FFACT_CGSA_WORK_DIR", "").strip() or self.cgsa_root)
        if cgsa_root.exists():
            for leaf in sorted(cgsa_root.iterdir()):
                if not leaf.is_dir():
                    continue
                identity = self._identity_from_cgsa_leaf(leaf)
                if identity is None:
                    continue
                symbol, timeframe, config_hash = identity
                key = (symbol, timeframe, config_hash)
                if key in yielded:
                    continue
                yielded.add(key)
                yield symbol, timeframe, config_hash, "cgsa"

    @staticmethod
    def _identity_from_cgsa_leaf(leaf: Path) -> Optional[Tuple[str, str, str]]:
        """從 CGSA work leaf 的 manifest 解析 run identity。"""
        manifest_path = leaf / "manifest.json"
        if not manifest_path.is_file() or manifest_path.stat().st_size == 0:
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        symbol = str(manifest.get("symbol") or "").strip()
        timeframe = str(manifest.get("timeframe") or manifest.get("primary_tf") or "").strip()
        config_hash = str(manifest.get("config_hash") or "").strip()
        if not symbol or not timeframe or not config_hash:
            return None
        try:
            validate_config_hash(config_hash)
        except ValueError:
            return None
        if not RunLifecycleManager._cgsa_owned_by_run(leaf, config_hash):
            return None
        return symbol, timeframe, config_hash

    @staticmethod
    def _cgsa_owned_by_run(leaf: Path, config_hash: str) -> bool:
        manifest_path = leaf / "manifest.json"
        if not manifest_path.is_file():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return manifest.get("config_hash") == config_hash

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
