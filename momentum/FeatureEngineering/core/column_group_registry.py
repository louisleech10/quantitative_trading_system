from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional

import numpy as np
import pandas as pd

try:
    from typing_extensions import deprecated
except ImportError:
    def deprecated(_reason: str):  # type: ignore[misc]
        def _decorator(func):
            return func

        return _decorator

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class FailureType(str, Enum):
    """Failure category for registry I/O and validation operations."""

    IO_ERROR = "io_error"
    OOM = "oom"
    VALIDATION = "validation"
    CONFIG = "config"


class ColumnGroupRegistryError(RuntimeError):
    """Registry-level exception with explicit failure classification."""

    def __init__(self, message: str, failure_type: FailureType) -> None:
        super().__init__(message)
        self.failure_type = failure_type


class ColumnGroupRegistry:
    """In-memory registry tracking all column groups for a single symbol run."""

    _LAYER_ORDER = {
        LayerSource.L1: 0,
        LayerSource.L2: 1,
        LayerSource.L3: 2,
        LayerSource.L4: 3,
        LayerSource.L5: 4,
        LayerSource.L6: 5,
        LayerSource.L65: 6,
    }
    _CATEGORY_ORDER = {
        "entropy": 0,
        "microstructure": 1,
        "momentum": 2,
        "tail_risk": 3,
        "trend": 4,
        "volatility": 5,
        "volume": 6,
    }
    _AGGREGATOR_ORDER = {
        "kurt": 0,
        "max": 1,
        "mean": 2,
        "min": 3,
        "range": 4,
        "rank": 5,
        "skew": 6,
        "slope": 7,
        "std": 8,
        "zscore": 9,
    }
    _TIMEFRAME_REGEX = re.compile(r"^(\d+)([mhdw])$")
    _NUMBER_REGEX = re.compile(r"(?<!\d)(\d+)(?!\d)")

    def __init__(self, work_dir: Path, memory_buffer_groups: int = 0):
        self._groups: dict[str, ColumnGroup] = {}
        self._work_dir = Path(work_dir)
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_context: dict[str, Any] = {}
        self._group_parquet_paths: dict[str, str] = {}
        self._memory_buffer: dict[str, np.ndarray] = {}
        self._memory_buffer_limit = max(0, int(memory_buffer_groups))
        self._buffer_lock = threading.Lock()
        self._manifest_lock = threading.Lock()
        self._manifest_defer_depth = 0
        self._manifest_dirty = False
        self._io_stats: Dict[str, float] = {
            "persist_count": 0.0,
            "persist_bytes": 0.0,
            "persist_seconds": 0.0,
            "overwrite_count": 0.0,
            "overwrite_bytes": 0.0,
            "overwrite_seconds": 0.0,
            "manifest_write_count": 0.0,
            "manifest_write_seconds": 0.0,
            "manifest_deferred_count": 0.0,
        }

    @property
    def work_dir(self) -> Path:
        """Registry working directory containing persisted intermediate files."""
        return self._work_dir

    @property
    def manifest_path(self) -> Path:
        """Absolute path of registry manifest file."""
        return self._work_dir / "manifest.json"

    def save_state(
        self,
        symbol: str,
        primary_tf: str,
        training_tfs: Iterable[str],
        config_hash: str,
        config_snapshot: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Persist manifest context metadata and rewrite manifest atomically."""
        self._manifest_context = {
            "symbol": symbol,
            "primary_tf": primary_tf,
            "training_tfs": list(training_tfs),
            "config_hash": config_hash,
            "config_snapshot": self._to_json_safe(dict(config_snapshot or {})),
            "created_at": self._manifest_context.get("created_at", datetime.utcnow().isoformat()),
        }
        self._write_manifest()

    def set_group_parquet_paths(
        self,
        parquet_paths: Mapping[str, str],
        write_manifest: bool = True,
    ) -> None:
        """Attach parquet output paths to tracked groups for manifest/materialization."""
        for group_id, parquet_path in parquet_paths.items():
            if group_id not in self._groups:
                raise ColumnGroupRegistryError(
                    f"Cannot bind parquet path for unknown group_id: {group_id}",
                    failure_type=FailureType.VALIDATION,
                )
            self._group_parquet_paths[group_id] = str(parquet_path)

        if write_manifest:
            self._write_manifest()

    def register(self, group: ColumnGroup) -> None:
        """Register a column group. Raises if group_id already exists."""
        if group.group_id in self._groups:
            raise ValueError(f"Duplicate group_id: {group.group_id}")
        self._groups[group.group_id] = group

    def get(self, group_id: str) -> ColumnGroup:
        """Get a column group by ID."""
        return self._groups[group_id]

    def list_by_layer(self, layer: LayerSource) -> list[ColumnGroup]:
        """List all groups from a specific layer."""
        return sorted(
            [group for group in self._groups.values() if group.layer == layer],
            key=lambda item: item.group_id,
        )

    def list_by_timeframe(self, tf: str) -> list[ColumnGroup]:
        """List all groups from a specific timeframe."""
        return sorted(
            [group for group in self._groups.values() if group.timeframe == tf],
            key=lambda item: item.group_id,
        )

    def has_layers_for_timeframe(self, tf: str, layers: Iterable[LayerSource]) -> bool:
        """Return True iff every layer in ``layers`` has at least one group for ``tf``.

        Used by Multi-TF resume logic to decide whether a TF can be skipped
        when re-running a pipeline against an existing manifest. Caller is
        responsible for passing the canonical layer set (typically L1..L6).
        """
        required = {layer for layer in layers}
        if not required:
            return False
        seen: set[LayerSource] = set()
        for group in self._groups.values():
            if group.timeframe != tf:
                continue
            seen.add(group.layer)
            if required.issubset(seen):
                return True
        return required.issubset(seen)

    def write_manifest(self) -> None:
        """Public façade for persisting manifest atomically (thread-safe).

        Resume support: callers that register groups via :meth:`register`
        (rather than :meth:`save_data`) must invoke this to flush the
        in-memory mapping to ``manifest.json`` so a subsequent process can
        pick up where the previous one left off. ``save_data`` already
        writes the manifest internally.
        """
        self._write_manifest_thread_safe()

    @contextmanager
    def defer_manifest_writes(self, reason: str = "") -> Iterator[None]:
        """Batch manifest writes until the protected mutation block exits."""
        with self._manifest_lock:
            self._manifest_defer_depth += 1

        started_at = time.perf_counter()
        try:
            yield
        finally:
            should_flush = False
            deferred_count = 0.0
            with self._manifest_lock:
                self._manifest_defer_depth = max(0, self._manifest_defer_depth - 1)
                if self._manifest_defer_depth == 0 and self._manifest_dirty:
                    self._manifest_dirty = False
                    should_flush = True
                    deferred_count = self._io_stats.get("manifest_deferred_count", 0.0)

            if should_flush:
                self._write_manifest_thread_safe()
                elapsed = time.perf_counter() - started_at
                logger.info(
                    "[registry] Deferred manifest writes flushed: reason=%s deferred=%.0f elapsed=%.2fs",
                    reason or "unspecified",
                    deferred_count,
                    elapsed,
                )

    def io_stats(self) -> Dict[str, float]:
        """Return cumulative registry I/O counters for coarse performance diagnostics."""
        return dict(self._io_stats)

    def reset_io_stats(self) -> None:
        """Reset cumulative registry I/O counters."""
        for key in self._io_stats:
            self._io_stats[key] = 0.0

    def iter_all(self) -> Iterable[tuple[str, ColumnGroup]]:
        """Iterate all groups in deterministic group_id order."""
        for group_id in sorted(self._groups.keys()):
            yield group_id, self._groups[group_id]

    def load_data(self, group_id: str) -> np.ndarray:
        """Load column group data from disk with memory-mapped read-only mode."""
        with self._buffer_lock:
            buffered = self._memory_buffer.get(group_id)
        if buffered is not None:
            return np.asarray(buffered, dtype=np.float32)

        group = self.get(group_id)
        if group.disk_path is None:
            raise ColumnGroupRegistryError(
                f"Group {group_id} has no disk_path; cannot load persisted data.",
                failure_type=FailureType.VALIDATION,
            )

        if not group.disk_path.exists():
            raise ColumnGroupRegistryError(
                f"Persisted group data missing: {group.disk_path}",
                failure_type=FailureType.IO_ERROR,
            )

        try:
            return np.load(group.disk_path, mmap_mode="r", allow_pickle=False)
        except OSError as exc:
            raise ColumnGroupRegistryError(
                f"Failed to load group data for {group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc

    def save_data(self, group: ColumnGroup, data: np.ndarray) -> ColumnGroup:
        """Save group data to .npy, register it, and update manifest atomically."""
        if data.ndim != 2:
            raise ColumnGroupRegistryError(
                f"Group {group.group_id} data must be 2D, got shape={data.shape}",
                failure_type=FailureType.VALIDATION,
            )

        if group.group_id in self._groups:
            raise ValueError(f"Duplicate group_id: {group.group_id}")

        data_fp32 = np.asarray(data, dtype=np.float32)
        path = self._work_dir / f"{group.group_id}.npy"

        updated_group = ColumnGroup(
            group_id=group.group_id,
            layer=group.layer,
            timeframe=group.timeframe,
            data_source=group.data_source,
            indicator=group.indicator,
            columns=group.columns,
            shape=(int(data_fp32.shape[0]), int(data_fp32.shape[1])),
            dtype="float32",
            disk_path=path,
        )

        self._groups[updated_group.group_id] = updated_group

        if self._memory_buffer_limit > 0:
            with self._buffer_lock:
                self._memory_buffer[group.group_id] = data_fp32
                should_flush = len(self._memory_buffer) >= self._memory_buffer_limit

            if should_flush:
                self._flush_buffer()

            return updated_group

        self._persist_group_array(updated_group.group_id, path, data_fp32, action="persist")

        try:
            self._write_manifest_thread_safe()
        except OSError as exc:
            self._groups.pop(updated_group.group_id, None)
            if path.exists():
                path.unlink()
            raise ColumnGroupRegistryError(
                f"Failed to write manifest after persisting {group.group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc

        return updated_group

    def overwrite_data(self, group_id: str, data: np.ndarray) -> ColumnGroup:
        """Overwrite existing persisted .npy for a group and refresh manifest."""
        if data.ndim != 2:
            raise ColumnGroupRegistryError(
                f"Group {group_id} data must be 2D, got shape={data.shape}",
                failure_type=FailureType.VALIDATION,
            )

        group = self.get(group_id)
        if data.shape[1] != group.n_cols:
            raise ColumnGroupRegistryError(
                f"Group {group_id} column count mismatch: expected {group.n_cols}, got {data.shape[1]}",
                failure_type=FailureType.VALIDATION,
            )

        target_path = group.disk_path or (self._work_dir / f"{group.group_id}.npy")
        temp_path = target_path.with_suffix(".npy.tmp")
        data_fp32 = np.asarray(data, dtype=np.float32)

        with self._buffer_lock:
            self._memory_buffer.pop(group_id, None)

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            started_at = time.perf_counter()
            with temp_path.open("wb") as handle:
                np.save(handle, data_fp32, allow_pickle=False)
            os.replace(temp_path, target_path)
            elapsed = time.perf_counter() - started_at
            self._io_stats["overwrite_count"] += 1.0
            self._io_stats["overwrite_bytes"] += float(data_fp32.nbytes)
            self._io_stats["overwrite_seconds"] += elapsed
        except MemoryError as exc:
            if temp_path.exists():
                temp_path.unlink()
            raise ColumnGroupRegistryError(
                f"OOM while overwriting group {group_id} to {target_path}",
                failure_type=FailureType.OOM,
            ) from exc
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink()
            raise ColumnGroupRegistryError(
                f"Failed to overwrite group {group_id} to {target_path}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc

        updated_group = ColumnGroup(
            group_id=group.group_id,
            layer=group.layer,
            timeframe=group.timeframe,
            data_source=group.data_source,
            indicator=group.indicator,
            columns=group.columns,
            shape=(int(data_fp32.shape[0]), int(data_fp32.shape[1])),
            dtype="float32",
            disk_path=target_path,
        )
        self._groups[group_id] = updated_group

        try:
            self._write_manifest_thread_safe()
        except OSError as exc:
            raise ColumnGroupRegistryError(
                f"Failed to write manifest after overwriting {group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc

        return updated_group

    def total_columns(self) -> int:
        """Total number of columns tracked by this registry."""
        return sum(group.n_cols for group in self._groups.values())

    def all_column_names(self) -> list[str]:
        """Return all feature column names using canonical column ordering."""
        flattened: list[tuple[tuple[Any, ...], str]] = []
        for group in self._groups.values():
            for column in group.columns:
                flattened.append((self._column_sort_key(group, column), column))

        flattened.sort(key=lambda item: item[0])
        return [column for _, column in flattened]

    def cleanup(self) -> None:
        """Delete persisted .npy files and clear the in-memory registry."""
        with self._buffer_lock:
            self._memory_buffer.clear()

        for group in self._groups.values():
            if group.disk_path and group.disk_path.exists():
                try:
                    group.disk_path.unlink()
                except OSError as exc:
                    raise ColumnGroupRegistryError(
                        f"Failed to delete persisted group file {group.disk_path}: {exc}",
                        failure_type=FailureType.IO_ERROR,
                    ) from exc

        manifest_path = self._work_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest_path.unlink()
            except OSError as exc:
                raise ColumnGroupRegistryError(
                    f"Failed to delete manifest file {manifest_path}: {exc}",
                    failure_type=FailureType.IO_ERROR,
                ) from exc

        self._groups.clear()

    @classmethod
    def resume_from_manifest(cls, work_dir: Path) -> "ColumnGroupRegistry":
        """Resume registry state from manifest.json and existing .npy files."""
        work_dir = Path(work_dir)
        manifest_path = work_dir / "manifest.json"
        if not manifest_path.exists():
            raise ColumnGroupRegistryError(
                f"manifest.json not found under {work_dir}",
                failure_type=FailureType.CONFIG,
            )

        try:
            with manifest_path.open("r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ColumnGroupRegistryError(
                f"Invalid manifest JSON under {manifest_path}: {exc}",
                failure_type=FailureType.CONFIG,
            ) from exc

        registry = cls(work_dir=work_dir)
        registry._manifest_context = {
            "symbol": manifest.get("symbol"),
            "primary_tf": manifest.get("primary_tf"),
            "training_tfs": manifest.get("training_tfs") or [],
            "config_hash": manifest.get("config_hash"),
            "config_snapshot": manifest.get("config_snapshot") or {},
            "created_at": manifest.get("created_at") or datetime.utcnow().isoformat(),
        }

        for group_meta in manifest.get("groups", []):
            npy_path: Optional[Path] = None
            parquet_path: Optional[Path] = None

            npy_path_value = group_meta.get("npy_path")
            if npy_path_value:
                npy_candidate = work_dir / str(npy_path_value)
                if npy_candidate.exists():
                    npy_path = npy_candidate

            parquet_path_value = group_meta.get("parquet_path")
            if parquet_path_value:
                parquet_candidate = Path(str(parquet_path_value))
                if not parquet_candidate.is_absolute():
                    parquet_candidate = work_dir / parquet_candidate
                if parquet_candidate.exists():
                    parquet_path = parquet_candidate

            if npy_path is None:
                # Cannot resume without the intermediate .npy data.  When only
                # parquet is present the previous run completed successfully and
                # its .npy intermediates were already cleaned up; registering
                # the group with disk_path=None would crash load_data later.
                # Skip it so the new run recomputes from scratch with the
                # original group IDs (no "_2" suffix collisions).
                if parquet_path is not None:
                    logger.debug(
                        "[registry] Group %s has parquet output but no npy intermediate;"
                        " not restoring (previous run already completed for this group)",
                        group_meta.get("group_id"),
                    )
                else:
                    logger.warning(
                        "[registry] Missing npy/parquet file for group %s; skipped",
                        group_meta.get("group_id"),
                    )
                continue

            try:
                shape = cls._parse_shape(group_meta.get("shape"))
                group = ColumnGroup(
                    group_id=str(group_meta["group_id"]),
                    layer=LayerSource(str(group_meta["layer"])),
                    timeframe=str(group_meta["timeframe"]),
                    data_source=str(group_meta["data_source"]),
                    indicator=str(group_meta["indicator"]),
                    columns=tuple(group_meta.get("columns", [])),
                    shape=shape,
                    dtype=str(group_meta.get("dtype", "float32")),
                    disk_path=npy_path,
                )
            except (KeyError, ValueError, TypeError) as exc:
                raise ColumnGroupRegistryError(
                    f"Invalid group metadata in manifest for {group_meta}: {exc}",
                    failure_type=FailureType.CONFIG,
                ) from exc

            registry.register(group)

            if parquet_path is not None:
                registry._group_parquet_paths[group.group_id] = str(parquet_path)

        return registry

    @staticmethod
    def compute_config_hash(
        config: Mapping[str, Any],
        ignored_keys: Optional[Iterable[str]] = None,
    ) -> str:
        """Compute deterministic config hash from canonical JSON payload."""
        normalized = ColumnGroupRegistry._normalize_config_for_hash(
            config=config,
            ignored_keys=set(ignored_keys or {"log_level", "n_jobs"}),
        )
        canonical_json = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _normalize_config_for_hash(
        config: Any,
        ignored_keys: set[str],
    ) -> Any:
        if isinstance(config, Mapping):
            return {
                str(key): ColumnGroupRegistry._normalize_config_for_hash(value, ignored_keys)
                for key, value in sorted(config.items(), key=lambda item: str(item[0]))
                if str(key) not in ignored_keys
            }

        if isinstance(config, (list, tuple)):
            return [ColumnGroupRegistry._normalize_config_for_hash(item, ignored_keys) for item in config]

        return config

    @staticmethod
    def _parse_shape(shape_value: Any) -> tuple[int, int]:
        if not isinstance(shape_value, (list, tuple)) or len(shape_value) != 2:
            return 0, 0

        return int(shape_value[0]), int(shape_value[1])

    def _write_manifest(self) -> None:
        """Write manifest.json using atomic temp-file replacement."""
        self._work_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.manifest_path

        default_created_at = self._manifest_context.get("created_at")
        if not default_created_at:
            default_created_at = datetime.utcnow().isoformat()

        training_tfs = self._manifest_context.get("training_tfs")
        if not isinstance(training_tfs, list):
            training_tfs = []

        groups_payload = self._manifest_groups_payload()
        total_features = sum(len(group_meta["columns"]) for group_meta in groups_payload)

        payload = {
            "symbol": self._manifest_context.get("symbol"),
            "primary_tf": self._manifest_context.get("primary_tf"),
            "training_tfs": training_tfs,
            "config_hash": self._manifest_context.get("config_hash"),
            "config_snapshot": self._manifest_context.get("config_snapshot") or {},
            "total_features": total_features,
            "total_groups": len(groups_payload),
            "created_at": default_created_at,
            "groups": groups_payload,
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._work_dir,
            prefix="manifest.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            temp_path = Path(handle.name)

        try:
            os.replace(temp_path, manifest_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _manifest_groups_payload(self) -> list[dict[str, Any]]:
        with self._buffer_lock:
            buffered_group_ids = set(self._memory_buffer.keys())

        payload: list[dict[str, Any]] = []
        for group in sorted(self._groups.values(), key=lambda item: item.group_id):
            if group.group_id in buffered_group_ids:
                continue
            payload.append(
                {
                    "group_id": group.group_id,
                    "layer": group.layer.value,
                    "timeframe": group.timeframe,
                    "data_source": group.data_source,
                    "indicator": group.indicator,
                    "columns": list(group.columns),
                    "shape": [group.n_rows, group.n_cols],
                    "dtype": group.dtype,
                    "npy_path": group.disk_path.name if group.disk_path else None,
                    "parquet_path": self._group_parquet_paths.get(group.group_id),
                }
            )
        return payload

    def _persist_group_array(
        self,
        group_id: str,
        path: Path,
        data_fp32: np.ndarray,
        action: str,
    ) -> None:
        """Persist one group array to disk with explicit failure classification."""

        expected_bytes = int(data_fp32.nbytes)
        free_before = self._disk_free_bytes(path.parent)
        if free_before is not None and free_before < expected_bytes:
            raise ColumnGroupRegistryError(
                f"Insufficient disk space while {action} group {group_id} to {path}: "
                f"need {self._format_bytes(expected_bytes)}, available {self._format_bytes(free_before)}, "
                f"shape={tuple(data_fp32.shape)}",
                failure_type=FailureType.IO_ERROR,
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            started_at = time.perf_counter()
            np.save(path, data_fp32, allow_pickle=False)
            elapsed = time.perf_counter() - started_at
            self._io_stats["persist_count"] += 1.0
            self._io_stats["persist_bytes"] += float(expected_bytes)
            self._io_stats["persist_seconds"] += elapsed
        except MemoryError as exc:
            raise ColumnGroupRegistryError(
                f"OOM while {action} group {group_id} to {path}",
                failure_type=FailureType.OOM,
            ) from exc
        except OSError as exc:
            free_after = self._disk_free_bytes(path.parent)
            raise ColumnGroupRegistryError(
                f"Failed to {action} group {group_id} to {path}: {exc}; "
                f"shape={tuple(data_fp32.shape)}, bytes={self._format_bytes(expected_bytes)}, "
                f"free_before={self._format_bytes(free_before)}, free_after={self._format_bytes(free_after)}",
                failure_type=FailureType.IO_ERROR,
            ) from exc

    @staticmethod
    def _disk_free_bytes(path: Path) -> Optional[int]:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return int(shutil.disk_usage(path).free)
        except OSError:
            return None

    @staticmethod
    def _format_bytes(num_bytes: Optional[int]) -> str:
        if num_bytes is None:
            return "unknown"
        return f"{num_bytes / (1024 ** 3):.2f} GiB"

    def _write_manifest_thread_safe(self) -> None:
        """Serialize manifest writes to avoid parallel temp-file races."""

        with self._manifest_lock:
            if self._manifest_defer_depth > 0:
                self._manifest_dirty = True
                self._io_stats["manifest_deferred_count"] += 1.0
                return
            started_at = time.perf_counter()
            self._write_manifest()
            elapsed = time.perf_counter() - started_at
            self._io_stats["manifest_write_count"] += 1.0
            self._io_stats["manifest_write_seconds"] += elapsed

    def _flush_buffer(self) -> None:
        """Flush buffered group arrays to disk and refresh manifest once."""

        with self._buffer_lock:
            if not self._memory_buffer:
                return
            buffered_items = list(self._memory_buffer.items())
            self._memory_buffer.clear()

        for group_id, data_fp32 in buffered_items:
            group = self.get(group_id)
            target_path = group.disk_path or (self._work_dir / f"{group_id}.npy")
            self._persist_group_array(group_id, target_path, np.asarray(data_fp32, dtype=np.float32), action="flush")

        self._write_manifest_thread_safe()

    def finalize(self) -> None:
        """Flush any remaining buffered arrays to disk."""

        self._flush_buffer()

    @deprecated("Use iter_all()/load_data() instead; materialize_wide_df may consume large RAM.")
    def materialize_wide_df(self) -> pd.DataFrame:
        """Rebuild a wide DataFrame from per-group parquet (fallback to .npy) in canonical column order."""
        if not self._groups:
            return pd.DataFrame()

        estimated_gb = sum(group.est_bytes for group in self._groups.values()) / (1024**3)
        logger.warning(
            "[registry] materialize_wide_df() is deprecated and may consume %.2f GB RAM",
            estimated_gb,
        )

        frames: list[pd.DataFrame] = []
        expected_rows: Optional[int] = None

        for group in self._sorted_groups_for_materialize():
            frame = self._load_group_frame_for_materialize(group)
            if expected_rows is None:
                expected_rows = len(frame)
            elif len(frame) != expected_rows:
                raise ColumnGroupRegistryError(
                    (
                        f"Group {group.group_id} row mismatch during materialization: "
                        f"expected {expected_rows}, got {len(frame)}"
                    ),
                    failure_type=FailureType.VALIDATION,
                )
            frames.append(frame)

        combined = pd.concat(frames, axis=1, copy=False) if frames else pd.DataFrame()
        ordered_columns = self.all_column_names()
        if ordered_columns:
            combined = combined.loc[:, ordered_columns]
        return combined

    def _sorted_groups_for_materialize(self) -> list[ColumnGroup]:
        return sorted(
            self._groups.values(),
            key=lambda group: self._column_sort_key(
                group,
                group.columns[0] if group.columns else group.group_id,
            ),
        )

    def _load_group_frame_for_materialize(self, group: ColumnGroup) -> pd.DataFrame:
        parquet_path_value = self._group_parquet_paths.get(group.group_id)
        if parquet_path_value:
            parquet_path = Path(parquet_path_value)
            if not parquet_path.is_absolute():
                parquet_path = self._work_dir / parquet_path
            if parquet_path.exists():
                frame = pd.read_parquet(parquet_path)
                if list(frame.columns) != list(group.columns):
                    frame = frame.loc[:, list(group.columns)]
                return frame.astype(np.float32, copy=False)

        data = np.asarray(self.load_data(group.group_id), dtype=np.float32)
        return pd.DataFrame(data, columns=list(group.columns), copy=False)

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): ColumnGroupRegistry._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [ColumnGroupRegistry._to_json_safe(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _column_sort_key(self, group: ColumnGroup, column: str) -> tuple[Any, ...]:
        timeframe_key = self._timeframe_sort_key(group.timeframe)
        layer_key = self._LAYER_ORDER.get(group.layer, 999)
        category_key, category_value = self._extract_category(group, column)
        indicator_value = group.indicator.lower()
        source_value = group.data_source.lower()
        window_value = self._extract_window(column)
        aggregator_key, aggregator_value = self._extract_aggregator(column)
        label_last = 1 if column.startswith("label_") else 0

        return (
            label_last,
            timeframe_key,
            layer_key,
            category_key,
            category_value,
            indicator_value,
            source_value,
            window_value,
            aggregator_key,
            aggregator_value,
            column,
        )

    def _extract_category(self, group: ColumnGroup, column: str) -> tuple[int, str]:
        tokens = [token.lower() for token in column.split("_")]
        group_tokens = [token.lower() for token in group.group_id.split("_")]

        for token in tokens + group_tokens:
            if token in self._CATEGORY_ORDER:
                return self._CATEGORY_ORDER[token], token

        return len(self._CATEGORY_ORDER) + 1, ""

    def _extract_aggregator(self, column: str) -> tuple[int, str]:
        tokens = [token.lower() for token in column.split("_")]
        for token in tokens:
            if token in self._AGGREGATOR_ORDER:
                return self._AGGREGATOR_ORDER[token], token

        return len(self._AGGREGATOR_ORDER) + 1, ""

    def _extract_window(self, column: str) -> int:
        matches = self._NUMBER_REGEX.findall(column)
        if not matches:
            return 10**9

        try:
            return int(matches[-1])
        except ValueError:
            return 10**9

    def _timeframe_sort_key(self, timeframe: str) -> tuple[int, str]:
        match = self._TIMEFRAME_REGEX.match(timeframe)
        if not match:
            return 10**9, timeframe

        value = int(match.group(1))
        unit = match.group(2)
        multiplier = {
            "m": 1,
            "h": 60,
            "d": 60 * 24,
            "w": 60 * 24 * 7,
        }[unit]
        return value * multiplier, timeframe
