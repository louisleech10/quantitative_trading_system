from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class LayerSource(str, Enum):
    """Feature layer source for column group metadata."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L65 = "L6.5"


@dataclass(frozen=True)
class ShardMeta:
    """Per-shard metadata for a sharded ColumnGroup persisted to disk.

    A shard is a contiguous column slice [col_start, col_end) of the parent
    group's float32 ndarray, persisted as one ``.shard{NN}.npy`` file. Sharding
    bounds peak in-flight bytes during L6.5 raw-sink streaming so multi-symbol
    runs do not blow past the cgsa_work disk budget.
    """

    shard_idx: int
    col_start: int
    col_end: int
    n_rows: int
    disk_path: Path
    nbytes: int

    @property
    def n_cols(self) -> int:
        return self.col_end - self.col_start


@dataclass(frozen=True)
class AlignmentMeta:
    """Logical alignment metadata for compact non-primary timeframe groups.

    Compact-aligned groups keep the source timeframe rows on disk and carry an
    ``idx_map`` that expands them to the primary timeframe rows at read/stream
    time. ``ColumnGroup.shape`` remains the logical shape expected by downstream
    L6.5/L7 code.
    """

    source_timeframe: str
    primary_timeframe: str
    source_n_rows: int
    primary_n_rows: int
    idx_map_path: Path
    alignment_mode: str
    offset_ns: int = 0
    source_dur_ns: int = 0
    primary_dur_ns: int = 0
    mode: str = "close_time"
    align_algo_version: int = 1


@dataclass(frozen=True)
class ColumnGroup:
    """Immutable metadata for a group of related feature columns.

    Sharding model (Phase B Phase 1):
    - ``shards`` empty + ``disk_path`` set: legacy single-file group (back-compat).
    - ``shards`` populated: shard-aware group; ``disk_path`` may also be set
      to ``shards[0].disk_path`` when len(shards)==1 for transparent fast path.
    """

    group_id: str
    layer: LayerSource
    timeframe: str
    data_source: str
    indicator: str
    columns: tuple[str, ...]
    shape: tuple[int, int]
    dtype: str = "float32"
    disk_path: Optional[Path] = None
    shards: Tuple[ShardMeta, ...] = field(default_factory=tuple)
    alignment: Optional[AlignmentMeta] = None

    @property
    def n_rows(self) -> int:
        return self.shape[0]

    @property
    def n_cols(self) -> int:
        return self.shape[1]

    @property
    def est_bytes(self) -> int:
        elem_size = 4 if self.dtype == "float32" else 8
        return self.n_rows * self.n_cols * elem_size

    @property
    def is_sharded(self) -> bool:
        """True if this group is persisted as 2+ shard files."""
        return len(self.shards) > 1

    @property
    def is_compact_aligned(self) -> bool:
        """True when physical storage is source-TF rows plus an idx_map."""
        return self.alignment is not None

    @property
    def logical_n_rows(self) -> int:
        """Logical row count exposed to downstream consumers."""
        return self.n_rows

    @property
    def physical_n_rows(self) -> int:
        """Physical row count stored on disk before logical alignment."""
        if self.alignment is not None:
            return int(self.alignment.source_n_rows)
        if self.shards:
            return int(self.shards[0].n_rows)
        return self.n_rows

    @property
    def total_shard_bytes(self) -> int:
        """Physical persisted bytes; falls back to logical estimate if absent."""
        if self.shards:
            return sum(int(shard.nbytes) for shard in self.shards)
        if self.disk_path is not None:
            try:
                if self.disk_path.exists():
                    return int(self.disk_path.stat().st_size)
            except OSError:
                pass
        return self.est_bytes

    @property
    def max_shard_bytes(self) -> int:
        """Largest physical shard/file bytes; falls back to logical estimate."""
        if self.shards:
            return max(int(shard.nbytes) for shard in self.shards)
        if self.disk_path is not None:
            try:
                if self.disk_path.exists():
                    return int(self.disk_path.stat().st_size)
            except OSError:
                pass
        return self.est_bytes
