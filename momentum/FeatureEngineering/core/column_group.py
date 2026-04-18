from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


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
class ColumnGroup:
    """Immutable metadata for a group of related feature columns."""

    group_id: str
    layer: LayerSource
    timeframe: str
    data_source: str
    indicator: str
    columns: tuple[str, ...]
    shape: tuple[int, int]
    dtype: str = "float32"
    disk_path: Optional[Path] = None

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
