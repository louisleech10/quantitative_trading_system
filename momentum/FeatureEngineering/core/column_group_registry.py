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
from dataclasses import replace
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

from momentum.FeatureEngineering.core.column_group import AlignmentMeta, ColumnGroup, LayerSource, ShardMeta
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
        """Load column group data; transparently concatenates shards if sharded."""
        with self._buffer_lock:
            buffered = self._memory_buffer.get(group_id)
        if buffered is not None:
            return np.asarray(buffered, dtype=np.float32)

        group = self.get(group_id)

        if group.alignment is not None:
            return self._load_compact_aligned_group(group)

        # Sharded path: concat per-shard mmaps. We allocate one ndarray and
        # memcpy each shard slice in to avoid mmap-lifetime issues with the
        # caller (np.concatenate on mmap views can keep file handles alive
        # arbitrarily long, blocking unlink on Windows / multi-process).
        if group.shards:
            for shard in group.shards:
                if not shard.disk_path.exists():
                    raise ColumnGroupRegistryError(
                        f"Persisted shard data missing: {shard.disk_path} (group={group_id} shard={shard.shard_idx})",
                        failure_type=FailureType.IO_ERROR,
                    )
            try:
                out = np.empty((group.n_rows, group.n_cols), dtype=np.float32)
                for shard in group.shards:
                    arr = np.load(shard.disk_path, mmap_mode="r", allow_pickle=False)
                    out[:, shard.col_start:shard.col_end] = arr
                    del arr
                return out
            except OSError as exc:
                raise ColumnGroupRegistryError(
                    f"Failed to load sharded group data for {group_id}: {exc}",
                    failure_type=FailureType.IO_ERROR,
                ) from exc

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

    def iter_shards(self, group_id: str) -> Iterator[tuple[ShardMeta, np.ndarray, tuple[str, ...]]]:
        """Yield ``(shard_meta, mmap_array, shard_columns)`` for each shard.

        For non-sharded legacy groups, yields a single synthesized shard view
        backed by ``disk_path``. The ``mmap_array`` is read-only mmap; caller
        must NOT mutate. Drop reference between iterations to release mmap.

        Compact-aligned groups yield logical primary-timeframe rows. Their
        physical source arrays are expanded with the group's ``idx_map`` one
        shard at a time, so existing L6.5/L7 streaming callers keep the same
        interface without storing dense aligned ``.npy`` files.
        """
        group = self.get(group_id)

        if group.alignment is not None:
            idx_map = self._load_alignment_index_map(group)
            yield from self._iter_compact_aligned_shards(group, idx_map)
            return

        # Memory-buffer fast path: synthesize as one virtual shard.
        with self._buffer_lock:
            buffered = self._memory_buffer.get(group_id)
        if buffered is not None:
            arr = np.asarray(buffered, dtype=np.float32)
            virtual = ShardMeta(
                shard_idx=0,
                col_start=0,
                col_end=group.n_cols,
                n_rows=group.n_rows,
                disk_path=group.disk_path or (self._work_dir / f"{group_id}.npy"),
                nbytes=int(arr.nbytes),
            )
            yield virtual, arr, tuple(group.columns)
            return

        if group.shards:
            for shard in group.shards:
                if not shard.disk_path.exists():
                    raise ColumnGroupRegistryError(
                        f"Persisted shard data missing: {shard.disk_path} (group={group_id} shard={shard.shard_idx})",
                        failure_type=FailureType.IO_ERROR,
                    )
                try:
                    arr = np.load(shard.disk_path, mmap_mode="r", allow_pickle=False)
                except OSError as exc:
                    raise ColumnGroupRegistryError(
                        f"Failed to mmap shard {shard.shard_idx} for {group_id}: {exc}",
                        failure_type=FailureType.IO_ERROR,
                    ) from exc
                shard_columns = tuple(group.columns[shard.col_start:shard.col_end])
                yield shard, arr, shard_columns
                del arr
            return

        # Legacy single-file fallback: synthesize one shard.
        if group.disk_path is None or not group.disk_path.exists():
            raise ColumnGroupRegistryError(
                f"Group {group_id} has no readable disk_path or shards.",
                failure_type=FailureType.VALIDATION,
            )
        try:
            arr = np.load(group.disk_path, mmap_mode="r", allow_pickle=False)
        except OSError as exc:
            raise ColumnGroupRegistryError(
                f"Failed to mmap legacy single-file group {group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc
        virtual = ShardMeta(
            shard_idx=0,
            col_start=0,
            col_end=group.n_cols,
            n_rows=group.n_rows,
            disk_path=group.disk_path,
            nbytes=int(arr.nbytes),
        )
        yield virtual, arr, tuple(group.columns)
        del arr

    def _load_compact_aligned_group(self, group: ColumnGroup) -> np.ndarray:
        """Materialize a compact-aligned group to its logical dense matrix."""
        out = np.empty((group.n_rows, group.n_cols), dtype=np.float32)
        for shard_meta, aligned_shard, _columns in self.iter_shards(group.group_id):
            out[:, shard_meta.col_start:shard_meta.col_end] = aligned_shard
            del aligned_shard
        return out

    # ------------------------------------------------------------------
    # Native (source-resolution) read API
    # ------------------------------------------------------------------
    # These methods return data at the source timeframe row count for
    # compact-aligned groups, skipping the idx_map expansion. They power
    # the native-resolution L6.5 path that runs preprocessing on native
    # rows and forward-fills results to primary rows post-transform.
    # For non-compact groups the behavior is identical to load_data /
    # iter_shards (no alignment to bypass).
    def load_data_native(self, group_id: str) -> np.ndarray:
        """Load source-resolution data without idx_map expansion.

        For compact-aligned groups, returns shape (source_n_rows, n_cols).
        For non-compact groups, returns shape (n_rows, n_cols) — identical
        to ``load_data``.
        """
        group = self.get(group_id)

        with self._buffer_lock:
            buffered = self._memory_buffer.get(group_id)
        if buffered is not None:
            return np.asarray(buffered, dtype=np.float32)

        if group.alignment is None:
            return self.load_data(group_id)

        # Compact-aligned: read physical source rows directly.
        if group.shards:
            for shard in group.shards:
                if not shard.disk_path.exists():
                    raise ColumnGroupRegistryError(
                        f"Persisted shard data missing: {shard.disk_path} (group={group_id} shard={shard.shard_idx})",
                        failure_type=FailureType.IO_ERROR,
                    )
            try:
                source_n_rows = int(group.alignment.source_n_rows)
                out = np.empty((source_n_rows, group.n_cols), dtype=np.float32)
                for shard in group.shards:
                    arr = np.load(shard.disk_path, mmap_mode="r", allow_pickle=False)
                    if arr.shape[0] != source_n_rows:
                        raise ColumnGroupRegistryError(
                            f"Compact shard row mismatch for {group_id} shard {shard.shard_idx}: "
                            f"expected {source_n_rows}, got {arr.shape[0]}",
                            failure_type=FailureType.VALIDATION,
                        )
                    out[:, shard.col_start:shard.col_end] = arr
                    del arr
                return out
            except OSError as exc:
                raise ColumnGroupRegistryError(
                    f"Failed to load native sharded group data for {group_id}: {exc}",
                    failure_type=FailureType.IO_ERROR,
                ) from exc

        if group.disk_path is None or not group.disk_path.exists():
            raise ColumnGroupRegistryError(
                f"Compact-aligned group {group_id} has no readable disk_path or shards.",
                failure_type=FailureType.VALIDATION,
            )
        try:
            arr = np.load(group.disk_path, mmap_mode="r", allow_pickle=False)
        except OSError as exc:
            raise ColumnGroupRegistryError(
                f"Failed to mmap native compact group {group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc
        return np.asarray(arr, dtype=np.float32)

    def iter_shards_native(
        self, group_id: str
    ) -> Iterator[tuple[ShardMeta, np.ndarray, tuple[str, ...]]]:
        """Yield shards at source resolution without idx_map expansion.

        ShardMeta.n_rows reflects source rows for compact-aligned groups.
        For non-compact groups, behavior matches ``iter_shards``.
        """
        group = self.get(group_id)

        if group.alignment is None:
            yield from self.iter_shards(group_id)
            return

        source_n_rows = int(group.alignment.source_n_rows)

        with self._buffer_lock:
            buffered = self._memory_buffer.get(group_id)
        if buffered is not None:
            arr = np.asarray(buffered, dtype=np.float32)
            virtual = ShardMeta(
                shard_idx=0,
                col_start=0,
                col_end=group.n_cols,
                n_rows=source_n_rows,
                disk_path=group.disk_path or (self._work_dir / f"{group_id}.npy"),
                nbytes=int(arr.nbytes),
            )
            yield virtual, arr, tuple(group.columns)
            return

        if group.shards:
            for shard in group.shards:
                if not shard.disk_path.exists():
                    raise ColumnGroupRegistryError(
                        f"Persisted shard data missing: {shard.disk_path} (group={group_id} shard={shard.shard_idx})",
                        failure_type=FailureType.IO_ERROR,
                    )
                try:
                    arr = np.load(shard.disk_path, mmap_mode="r", allow_pickle=False)
                except OSError as exc:
                    raise ColumnGroupRegistryError(
                        f"Failed to mmap native shard {shard.shard_idx} for {group_id}: {exc}",
                        failure_type=FailureType.IO_ERROR,
                    ) from exc
                native_meta = ShardMeta(
                    shard_idx=shard.shard_idx,
                    col_start=shard.col_start,
                    col_end=shard.col_end,
                    n_rows=source_n_rows,
                    disk_path=shard.disk_path,
                    nbytes=shard.nbytes,
                )
                shard_columns = tuple(group.columns[shard.col_start:shard.col_end])
                yield native_meta, arr, shard_columns
                del arr
            return

        if group.disk_path is None or not group.disk_path.exists():
            raise ColumnGroupRegistryError(
                f"Compact-aligned group {group_id} has no readable disk_path or shards.",
                failure_type=FailureType.VALIDATION,
            )
        try:
            arr = np.load(group.disk_path, mmap_mode="r", allow_pickle=False)
        except OSError as exc:
            raise ColumnGroupRegistryError(
                f"Failed to mmap native compact single-file group {group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc
        try:
            source_nbytes = int(group.disk_path.stat().st_size)
        except OSError:
            source_nbytes = int(arr.nbytes)
        virtual = ShardMeta(
            shard_idx=0,
            col_start=0,
            col_end=group.n_cols,
            n_rows=source_n_rows,
            disk_path=group.disk_path,
            nbytes=source_nbytes,
        )
        yield virtual, arr, tuple(group.columns)
        del arr

    def get_alignment_idx_map(self, group_id: str) -> Optional[np.ndarray]:
        """Return idx_map (int64 array) for a compact-aligned group, else None.

        The returned array has length ``alignment.primary_n_rows``. Values >= 0
        index into the source-resolution data; -1 marks rows with no valid
        source row available (output should be NaN).
        """
        group = self.get(group_id)
        if group.alignment is None:
            return None
        return self._load_alignment_index_map(group)

    def _iter_compact_aligned_shards(
        self,
        group: ColumnGroup,
        idx_map: np.ndarray,
    ) -> Iterator[tuple[ShardMeta, np.ndarray, tuple[str, ...]]]:
        """Yield logical aligned shard arrays for a compact-aligned group."""
        group_id = group.group_id

        with self._buffer_lock:
            buffered = self._memory_buffer.get(group_id)
        if buffered is not None:
            physical = np.asarray(buffered, dtype=np.float32)
            aligned = self._align_physical_array(
                physical,
                idx_map,
                n_primary=group.n_rows,
                group_id=group_id,
            )
            virtual = ShardMeta(
                shard_idx=0,
                col_start=0,
                col_end=group.n_cols,
                n_rows=group.n_rows,
                disk_path=group.disk_path or (self._work_dir / f"{group_id}.npy"),
                nbytes=int(physical.nbytes),
            )
            yield virtual, aligned, tuple(group.columns)
            return

        if group.shards:
            for shard in group.shards:
                if not shard.disk_path.exists():
                    raise ColumnGroupRegistryError(
                        f"Persisted shard data missing: {shard.disk_path} (group={group_id} shard={shard.shard_idx})",
                        failure_type=FailureType.IO_ERROR,
                    )
                try:
                    physical = np.load(shard.disk_path, mmap_mode="r", allow_pickle=False)
                except OSError as exc:
                    raise ColumnGroupRegistryError(
                        f"Failed to mmap compact shard {shard.shard_idx} for {group_id}: {exc}",
                        failure_type=FailureType.IO_ERROR,
                    ) from exc
                aligned = self._align_physical_array(
                    physical,
                    idx_map,
                    n_primary=group.n_rows,
                    group_id=group_id,
                )
                logical_meta = ShardMeta(
                    shard_idx=shard.shard_idx,
                    col_start=shard.col_start,
                    col_end=shard.col_end,
                    n_rows=group.n_rows,
                    disk_path=shard.disk_path,
                    nbytes=shard.nbytes,
                )
                shard_columns = tuple(group.columns[shard.col_start:shard.col_end])
                yield logical_meta, aligned, shard_columns
                del physical, aligned
            return

        if group.disk_path is None or not group.disk_path.exists():
            raise ColumnGroupRegistryError(
                f"Compact-aligned group {group_id} has no readable disk_path or shards.",
                failure_type=FailureType.VALIDATION,
            )
        try:
            physical = np.load(group.disk_path, mmap_mode="r", allow_pickle=False)
        except OSError as exc:
            raise ColumnGroupRegistryError(
                f"Failed to mmap compact single-file group {group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc
        aligned = self._align_physical_array(
            physical,
            idx_map,
            n_primary=group.n_rows,
            group_id=group_id,
        )
        try:
            source_nbytes = int(group.disk_path.stat().st_size)
        except OSError:
            source_nbytes = int(physical.nbytes)
        virtual = ShardMeta(
            shard_idx=0,
            col_start=0,
            col_end=group.n_cols,
            n_rows=group.n_rows,
            disk_path=group.disk_path,
            nbytes=source_nbytes,
        )
        yield virtual, aligned, tuple(group.columns)
        del physical, aligned

    def _load_alignment_index_map(self, group: ColumnGroup) -> np.ndarray:
        alignment = group.alignment
        if alignment is None:
            raise ColumnGroupRegistryError(
                f"Group {group.group_id} is not compact-aligned",
                failure_type=FailureType.VALIDATION,
            )
        idx_map_path = Path(alignment.idx_map_path)
        if not idx_map_path.exists():
            raise ColumnGroupRegistryError(
                f"Alignment idx_map missing for group {group.group_id}: {idx_map_path}",
                failure_type=FailureType.IO_ERROR,
            )
        try:
            idx_map = np.load(idx_map_path, mmap_mode="r", allow_pickle=False)
        except OSError as exc:
            raise ColumnGroupRegistryError(
                f"Failed to load alignment idx_map for {group.group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc
        if int(idx_map.shape[0]) != group.n_rows:
            raise ColumnGroupRegistryError(
                f"Alignment idx_map row mismatch for {group.group_id}: "
                f"expected {group.n_rows}, got {idx_map.shape[0]}",
                failure_type=FailureType.VALIDATION,
            )
        return np.asarray(idx_map, dtype=np.int64)

    @staticmethod
    def _align_physical_array(
        physical: np.ndarray,
        idx_map: np.ndarray,
        *,
        n_primary: int,
        group_id: str,
    ) -> np.ndarray:
        source = np.asarray(physical, dtype=np.float32)
        if source.ndim != 2:
            raise ColumnGroupRegistryError(
                f"Compact source group {group_id} must be 2D, got shape={source.shape}",
                failure_type=FailureType.VALIDATION,
            )
        out = np.full((int(n_primary), int(source.shape[1])), np.nan, dtype=np.float32)
        if idx_map.size == 0:
            return out
        valid = idx_map >= 0
        if bool(np.any(valid & (idx_map >= source.shape[0]))):
            raise ColumnGroupRegistryError(
                f"Alignment idx_map for {group_id} references source row beyond {source.shape[0]}",
                failure_type=FailureType.VALIDATION,
            )
        if bool(np.any(valid)):
            out[valid] = source[idx_map[valid]]
        return out

    def save_data(self, group: ColumnGroup, data: np.ndarray) -> ColumnGroup:
        """Save group data sharded across one or more .npy files; updates manifest.

        Sharding is automatic based on ``get_cgsa_shard_bytes()`` tier target.
        Small groups whose total bytes fit in one shard fall through the fast
        single-file path (legacy behavior, ``disk_path`` set, ``shards`` empty).
        """
        if data.ndim != 2:
            raise ColumnGroupRegistryError(
                f"Group {group.group_id} data must be 2D, got shape={data.shape}",
                failure_type=FailureType.VALIDATION,
            )

        if group.group_id in self._groups:
            raise ValueError(f"Duplicate group_id: {group.group_id}")

        data_fp32 = np.asarray(data, dtype=np.float32)
        n_rows, n_cols = int(data_fp32.shape[0]), int(data_fp32.shape[1])

        # Memory-buffer fast path bypasses sharding (small in-flight cache).
        if self._memory_buffer_limit > 0:
            single_path = self._work_dir / f"{group.group_id}.npy"
            updated_group = ColumnGroup(
                group_id=group.group_id,
                layer=group.layer,
                timeframe=group.timeframe,
                data_source=group.data_source,
                indicator=group.indicator,
                columns=group.columns,
                shape=(n_rows, n_cols),
                dtype="float32",
                disk_path=single_path,
            )
            self._groups[updated_group.group_id] = updated_group
            with self._buffer_lock:
                self._memory_buffer[group.group_id] = data_fp32
                should_flush = len(self._memory_buffer) >= self._memory_buffer_limit
            if should_flush:
                self._flush_buffer()
            return updated_group

        slices = self._compute_shard_slices(n_rows, n_cols, dtype_size=4)

        if len(slices) <= 1:
            # Single-shard fast path (legacy on-disk shape).
            single_path = self._work_dir / f"{group.group_id}.npy"
            updated_group = ColumnGroup(
                group_id=group.group_id,
                layer=group.layer,
                timeframe=group.timeframe,
                data_source=group.data_source,
                indicator=group.indicator,
                columns=group.columns,
                shape=(n_rows, n_cols),
                dtype="float32",
                disk_path=single_path,
            )
            self._groups[updated_group.group_id] = updated_group
            self._persist_group_array(updated_group.group_id, single_path, data_fp32, action="persist")
            try:
                self._write_manifest_thread_safe()
            except OSError as exc:
                self._groups.pop(updated_group.group_id, None)
                if single_path.exists():
                    single_path.unlink()
                raise ColumnGroupRegistryError(
                    f"Failed to write manifest after persisting {group.group_id}: {exc}",
                    failure_type=FailureType.IO_ERROR,
                ) from exc
            return updated_group

        # Multi-shard path.
        shard_metas: list[ShardMeta] = []
        written_paths: list[Path] = []
        width = max(2, len(str(len(slices) - 1)))
        try:
            for idx, (col_start, col_end) in enumerate(slices):
                shard_path = self._work_dir / f"{group.group_id}.shard{idx:0{width}d}.npy"
                shard_arr = np.ascontiguousarray(data_fp32[:, col_start:col_end])
                self._persist_group_array(
                    f"{group.group_id}#shard{idx}",
                    shard_path,
                    shard_arr,
                    action="persist-shard",
                )
                shard_metas.append(
                    ShardMeta(
                        shard_idx=idx,
                        col_start=col_start,
                        col_end=col_end,
                        n_rows=n_rows,
                        disk_path=shard_path,
                        nbytes=int(shard_arr.nbytes),
                    )
                )
                written_paths.append(shard_path)
                del shard_arr
        except Exception:
            for path in written_paths:
                try:
                    if path.exists():
                        path.unlink()
                except OSError:
                    pass
            for tmp in self._work_dir.glob(f"{group.group_id}.shard*.npy.tmp"):
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise

        updated_group = ColumnGroup(
            group_id=group.group_id,
            layer=group.layer,
            timeframe=group.timeframe,
            data_source=group.data_source,
            indicator=group.indicator,
            columns=group.columns,
            shape=(n_rows, n_cols),
            dtype="float32",
            disk_path=None,
            shards=tuple(shard_metas),
        )
        self._groups[updated_group.group_id] = updated_group

        try:
            self._write_manifest_thread_safe()
        except OSError as exc:
            self._groups.pop(updated_group.group_id, None)
            for path in written_paths:
                try:
                    if path.exists():
                        path.unlink()
                except OSError:
                    pass
            raise ColumnGroupRegistryError(
                f"Failed to write manifest after persisting sharded {group.group_id}: {exc}",
                failure_type=FailureType.IO_ERROR,
            ) from exc

        logger.debug(
            "[registry] Persisted sharded group %s: shards=%d, total_bytes=%.2f MiB, max_shard=%.2f MiB",
            group.group_id,
            len(shard_metas),
            updated_group.total_shard_bytes / (1024 ** 2),
            updated_group.max_shard_bytes / (1024 ** 2),
        )
        return updated_group

    def _compute_shard_slices(
        self,
        n_rows: int,
        n_cols: int,
        dtype_size: int,
    ) -> list[tuple[int, int]]:
        """Return list of (col_start, col_end) shard slices.

        Floor: at least 1 column per shard (warns if single-column row exceeds
        target). Single-shard fast path returned when total bytes <= target.
        """
        if n_cols <= 0 or n_rows <= 0:
            return [(0, n_cols)]

        try:
            from momentum.FeatureEngineering.utils.hardware_utils import get_cgsa_shard_bytes
            target_bytes = int(get_cgsa_shard_bytes())
        except Exception:
            target_bytes = 256 * 1024 * 1024

        bytes_per_col = n_rows * dtype_size
        if bytes_per_col <= 0:
            return [(0, n_cols)]

        total_bytes = bytes_per_col * n_cols
        if total_bytes <= target_bytes:
            return [(0, n_cols)]

        cols_per_shard = max(1, target_bytes // bytes_per_col)
        if cols_per_shard < 1:
            cols_per_shard = 1
            logger.warning(
                "[registry] Single column (n_rows=%d, %.2f MiB) exceeds shard target %.2f MiB; "
                "falling back to 1 column per shard",
                n_rows,
                bytes_per_col / (1024 ** 2),
                target_bytes / (1024 ** 2),
            )

        slices: list[tuple[int, int]] = []
        start = 0
        while start < n_cols:
            end = min(start + int(cols_per_shard), n_cols)
            slices.append((start, end))
            start = end
        return slices

    def unlink_shard(self, group_id: str, shard_idx: int) -> None:
        """Delete one persisted shard file. No-op if file already absent.

        Used by raw-sink cleanup hook to release shard bytes immediately after
        the corresponding parquet part is durably written.
        """
        if group_id not in self._groups:
            return
        group = self._groups[group_id]
        for shard in group.shards:
            if shard.shard_idx == shard_idx:
                if shard.disk_path.exists():
                    try:
                        shard.disk_path.unlink()
                    except OSError as exc:
                        raise ColumnGroupRegistryError(
                            f"Failed to unlink shard {shard.disk_path}: {exc}",
                            failure_type=FailureType.IO_ERROR,
                        ) from exc
                return

    def unregister_group(self, group_id: str) -> None:
        """Remove group from registry and delete any remaining shard / single files.

        Used by raw-sink to release manifest entries after a group's parts are
        all durably written. Manifest is rewritten atomically.
        """
        with self._buffer_lock:
            self._memory_buffer.pop(group_id, None)
        group = self._groups.pop(group_id, None)
        if group is None:
            return
        for shard in group.shards:
            if shard.disk_path.exists():
                try:
                    shard.disk_path.unlink()
                except OSError:
                    pass
        if group.disk_path and group.disk_path.exists():
            try:
                group.disk_path.unlink()
            except OSError:
                pass
        self._group_parquet_paths.pop(group_id, None)
        try:
            self._write_manifest_thread_safe()
        except OSError:
            pass

    def release_storage(self, group_id: str) -> int:
        """Release on-disk storage for a group while keeping the registry entry.

        Symmetric to a legacy single-file ``Path.unlink()`` cleanup but works
        for sharded groups too. After this call the group still exists in the
        registry (so parquet path binding via :meth:`set_group_parquet_paths`
        still works), but ``shards`` is empty and ``disk_path`` is cleared so
        downstream code does not try to read a deleted file. Returns the total
        bytes attributed to this group's prior on-disk footprint (using the
        recorded ``ShardMeta.nbytes`` so callers get the full original size
        even when individual shards were already incrementally unlinked by
        the raw-sink path).
        """
        if group_id not in self._groups:
            return 0
        group = self._groups[group_id]
        freed = 0
        for shard in group.shards:
            # Use recorded nbytes so the count is accurate even if the file
            # was already unlinked by a prior per-shard cleanup hook.
            freed += int(getattr(shard, "nbytes", 0))
            try:
                if shard.disk_path.exists():
                    shard.disk_path.unlink()
            except OSError:
                pass
        if group.disk_path is not None:
            try:
                if group.disk_path.exists():
                    freed += int(group.disk_path.stat().st_size)
                    group.disk_path.unlink()
            except OSError:
                pass
        # Replace with a stripped ColumnGroup so .shards / .disk_path reflect reality.
        self._groups[group_id] = replace(
            group,
            shards=(),
            disk_path=None,
        )
        with self._buffer_lock:
            self._memory_buffer.pop(group_id, None)
        try:
            self._write_manifest_thread_safe()
        except OSError:
            pass
        return freed

    def overwrite_data(self, group_id: str, data: np.ndarray) -> ColumnGroup:
        """Overwrite an existing group with new data (legacy single-file API).

        Re-persists via the same shard-aware ``save_data`` policy. Existing
        shard / single files are removed first to avoid stale slices when the
        new shard layout differs from the previous one.
        """
        if data.ndim != 2:
            raise ColumnGroupRegistryError(
                f"Group {group_id} data must be 2D, got shape={data.shape}",
                failure_type=FailureType.VALIDATION,
            )

        existing = self.get(group_id)
        if data.shape[1] != existing.n_cols:
            raise ColumnGroupRegistryError(
                f"Group {group_id} column count mismatch: expected {existing.n_cols}, got {data.shape[1]}",
                failure_type=FailureType.VALIDATION,
            )

        with self._buffer_lock:
            self._memory_buffer.pop(group_id, None)

        # Remove old persisted artifacts before re-persisting.
        for shard in existing.shards:
            if shard.disk_path.exists():
                try:
                    shard.disk_path.unlink()
                except OSError:
                    pass
        if existing.disk_path and existing.disk_path.exists():
            try:
                existing.disk_path.unlink()
            except OSError:
                pass

        # Pop and re-save through the shard-aware path.
        self._groups.pop(group_id, None)
        try:
            updated = self.save_data(existing, data)
        except Exception:
            # Best-effort restore registry entry to avoid leaving group_id
            # missing; caller should treat overwrite as failed regardless.
            self._groups[group_id] = existing
            raise

        self._io_stats["overwrite_count"] += 1.0
        self._io_stats["overwrite_bytes"] += float(np.asarray(data, dtype=np.float32).nbytes)
        return updated

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
        """Delete persisted .npy / shard files and clear the in-memory registry."""
        with self._buffer_lock:
            self._memory_buffer.clear()

        alignment_paths: set[Path] = set()
        for group in self._groups.values():
            if group.alignment is not None:
                alignment_paths.add(Path(group.alignment.idx_map_path))
            for shard in group.shards:
                if shard.disk_path.exists():
                    try:
                        shard.disk_path.unlink()
                    except OSError as exc:
                        raise ColumnGroupRegistryError(
                            f"Failed to delete persisted shard file {shard.disk_path}: {exc}",
                            failure_type=FailureType.IO_ERROR,
                        ) from exc
            if group.disk_path and group.disk_path.exists():
                try:
                    group.disk_path.unlink()
                except OSError as exc:
                    raise ColumnGroupRegistryError(
                        f"Failed to delete persisted group file {group.disk_path}: {exc}",
                        failure_type=FailureType.IO_ERROR,
                    ) from exc

        for alignment_path in alignment_paths:
            if alignment_path.exists():
                try:
                    alignment_path.unlink()
                except OSError as exc:
                    raise ColumnGroupRegistryError(
                        f"Failed to delete alignment idx_map file {alignment_path}: {exc}",
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

        # Belt-and-suspenders: clean any stray .tmp from interrupted runs.
        for tmp in self._work_dir.glob("*.tmp"):
            try:
                tmp.unlink()
            except OSError:
                pass

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

        manifest_schema = int(manifest.get("schema_version", 1))
        if manifest_schema not in (1, 2):
            logger.warning(
                "[registry] Unknown manifest schema_version=%s under %s; attempting schema 2 read",
                manifest_schema, work_dir,
            )

        # Belt-and-suspenders: clean any stray *.tmp left from interrupted runs
        # so resumed pipelines don't trip on partial writes.
        for tmp in work_dir.glob("*.tmp"):
            try:
                tmp.unlink()
            except OSError:
                pass

        for group_meta in manifest.get("groups", []):
            npy_path: Optional[Path] = None
            parquet_path: Optional[Path] = None
            shard_metas: list[ShardMeta] = []

            # ---- Schema 2 path: read shards list if present and non-empty.
            shards_raw = group_meta.get("shards") or []
            if shards_raw:
                missing_shard = False
                tmp_metas: list[ShardMeta] = []
                for shard_meta_raw in shards_raw:
                    shard_file = shard_meta_raw.get("file")
                    if not shard_file:
                        missing_shard = True
                        break
                    shard_path = work_dir / str(shard_file)
                    if not shard_path.exists():
                        logger.warning(
                            "[registry] Missing shard file %s for group %s; skipping group",
                            shard_path, group_meta.get("group_id"),
                        )
                        missing_shard = True
                        break
                    tmp_metas.append(
                        ShardMeta(
                            shard_idx=int(shard_meta_raw.get("shard_idx", 0)),
                            col_start=int(shard_meta_raw.get("col_start", 0)),
                            col_end=int(shard_meta_raw.get("col_end", 0)),
                            n_rows=int(shard_meta_raw.get("n_rows", 0)),
                            disk_path=shard_path,
                            nbytes=int(shard_meta_raw.get("nbytes", 0)),
                        )
                    )
                if missing_shard:
                    continue
                shard_metas = sorted(tmp_metas, key=lambda s: s.shard_idx)

            # ---- Schema 1 / single-file fallback (treated as 1-shard group).
            npy_path_value = group_meta.get("npy_path")
            if not shard_metas and npy_path_value:
                npy_candidate = work_dir / str(npy_path_value)
                if npy_candidate.exists():
                    npy_path = npy_candidate
                    if manifest_schema == 1:
                        logger.debug(
                            "[registry] Restoring legacy single-file group %s as 1-shard view "
                            "(migrating manifest schema 1 -> 2 lazily on next persist)",
                            group_meta.get("group_id"),
                        )

            parquet_path_value = group_meta.get("parquet_path")
            if parquet_path_value:
                parquet_candidate = Path(str(parquet_path_value))
                if not parquet_candidate.is_absolute():
                    parquet_candidate = work_dir / parquet_candidate
                if parquet_candidate.exists():
                    parquet_path = parquet_candidate

            alignment_meta: Optional[AlignmentMeta] = None
            alignment_raw = group_meta.get("alignment")
            if isinstance(alignment_raw, Mapping):
                idx_map_value = alignment_raw.get("idx_map_path")
                if not idx_map_value:
                    logger.warning(
                        "[registry] Compact alignment for group %s has no idx_map_path; skipping group",
                        group_meta.get("group_id"),
                    )
                    continue
                idx_map_path = Path(str(idx_map_value))
                if not idx_map_path.is_absolute():
                    idx_map_path = work_dir / idx_map_path
                if not idx_map_path.exists():
                    if parquet_path is not None and not shard_metas and npy_path is None:
                        logger.debug(
                            "[registry] Compact group %s already has parquet output but no idx_map; not restoring",
                            group_meta.get("group_id"),
                        )
                        continue
                    logger.warning(
                        "[registry] Missing alignment idx_map %s for group %s; skipping group",
                        idx_map_path,
                        group_meta.get("group_id"),
                    )
                    continue
                alignment_meta = AlignmentMeta(
                    source_timeframe=str(alignment_raw.get("source_timeframe", group_meta.get("timeframe", ""))),
                    primary_timeframe=str(alignment_raw.get("primary_timeframe", manifest.get("primary_tf") or "")),
                    source_n_rows=int(alignment_raw.get("source_n_rows", group_meta.get("shape", [0, 0])[0])),
                    primary_n_rows=int(alignment_raw.get("primary_n_rows", group_meta.get("shape", [0, 0])[0])),
                    idx_map_path=idx_map_path,
                    alignment_mode=str(alignment_raw.get("alignment_mode", "close_time")),
                    offset_ns=int(alignment_raw.get("offset_ns", 0)),
                    source_dur_ns=int(alignment_raw.get("source_dur_ns", 0)),
                    primary_dur_ns=int(alignment_raw.get("primary_dur_ns", 0)),
                    mode=str(alignment_raw.get("mode", alignment_raw.get("alignment_mode", "close_time"))),
                    align_algo_version=int(alignment_raw.get("align_algo_version", 1)),
                )

            if not shard_metas and npy_path is None:
                # Cannot resume without intermediate data. Parquet-only entries
                # mean the previous run completed; skip silently.
                if parquet_path is not None:
                    logger.debug(
                        "[registry] Group %s has parquet output but no npy/shard intermediate;"
                        " not restoring (previous run already completed for this group)",
                        group_meta.get("group_id"),
                    )
                else:
                    logger.warning(
                        "[registry] Missing npy/shard/parquet file for group %s; skipped",
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
                    shards=tuple(shard_metas),
                    alignment=alignment_meta,
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
            "schema_version": 2,
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
            shards_payload: list[dict[str, Any]] = [
                {
                    "shard_idx": shard.shard_idx,
                    "col_start": shard.col_start,
                    "col_end": shard.col_end,
                    "n_rows": shard.n_rows,
                    "nbytes": shard.nbytes,
                    "file": shard.disk_path.name,
                }
                for shard in group.shards
            ]
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
                    "shards": shards_payload,
                    "alignment": self._alignment_payload(group),
                    "parquet_path": self._group_parquet_paths.get(group.group_id),
                }
            )
        return payload

    @staticmethod
    def _alignment_payload(group: ColumnGroup) -> Optional[dict[str, Any]]:
        alignment = group.alignment
        if alignment is None:
            return None
        return {
            "source_timeframe": alignment.source_timeframe,
            "primary_timeframe": alignment.primary_timeframe,
            "source_n_rows": int(alignment.source_n_rows),
            "primary_n_rows": int(alignment.primary_n_rows),
            "idx_map_path": alignment.idx_map_path.name,
            "alignment_mode": alignment.alignment_mode,
            "offset_ns": int(alignment.offset_ns),
            "source_dur_ns": int(alignment.source_dur_ns),
            "primary_dur_ns": int(alignment.primary_dur_ns),
            "mode": alignment.mode,
            "align_algo_version": int(alignment.align_algo_version),
        }

    def _persist_group_array(
        self,
        group_id: str,
        path: Path,
        data_fp32: np.ndarray,
        action: str,
    ) -> None:
        """Persist one group array atomically (.tmp + os.replace) with disk pre-check."""

        expected_bytes = int(data_fp32.nbytes)
        free_before = self._disk_free_bytes(path.parent)
        if free_before is not None and free_before < expected_bytes:
            raise ColumnGroupRegistryError(
                f"Insufficient disk space while {action} group {group_id} to {path}: "
                f"need {self._format_bytes(expected_bytes)}, available {self._format_bytes(free_before)}, "
                f"shape={tuple(data_fp32.shape)}",
                failure_type=FailureType.IO_ERROR,
            )

        # Atomic write: ``.npy.tmp`` first, then os.replace. Avoids partial
        # files visible to a peer process / SIGKILL leaving half-written shards.
        temp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            started_at = time.perf_counter()
            with temp_path.open("wb") as handle:
                np.save(handle, data_fp32, allow_pickle=False)
            os.replace(temp_path, path)
            elapsed = time.perf_counter() - started_at
            self._io_stats["persist_count"] += 1.0
            self._io_stats["persist_bytes"] += float(expected_bytes)
            self._io_stats["persist_seconds"] += elapsed
        except MemoryError as exc:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise ColumnGroupRegistryError(
                f"OOM while {action} group {group_id} to {path}",
                failure_type=FailureType.OOM,
            ) from exc
        except OSError as exc:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
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
