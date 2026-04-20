"""Arrow IPC utilities for column-group intermediate data sharing.

Used by Phase 5 multi-symbol parallel execution to share reference data
(e.g., BTCUSDT) across worker processes via memory-mapped Arrow IPC files.

Design reference: FEATURE_FACTORY_OPTIMIZATION_SPEC.md §7.1
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc

from momentum.core.logging import get_logger

logger = get_logger(__name__)


def write_arrow_ipc(
    data: pd.DataFrame,
    path: Path,
) -> None:
    """Write a DataFrame to Arrow IPC file format.

    Uses the IPC file format (not stream) to support random-access mmap reads.
    """
    path = Path(path)
    table = pa.Table.from_pandas(data, preserve_index=False)
    with pa.OSFile(str(path), "wb") as sink:
        writer = ipc.new_file(sink, table.schema)
        writer.write_table(table)
        writer.close()
    logger.info("[arrow_ipc] Written %d rows x %d cols to %s", len(data), len(data.columns), path.name)


def read_arrow_ipc(path: Path) -> pd.DataFrame:
    """Read an Arrow IPC file via memory-mapped I/O (zero-copy where possible)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arrow IPC file not found: {path}")

    with pa.memory_map(str(path), "r") as mmap:
        reader = ipc.open_file(mmap)
        table = reader.read_all()
    return table.to_pandas()


def write_reference_data_ipc(
    reference_df: pd.DataFrame,
    work_dir: Path,
    symbol: str = "BTCUSDT",
) -> Path:
    """Serialize reference data to Arrow IPC for sharing with worker processes."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    ipc_path = work_dir / f"shared_ref_{symbol}.arrow"
    write_arrow_ipc(reference_df, ipc_path)
    return ipc_path


def read_reference_data_ipc(ipc_path: Path) -> pd.DataFrame:
    """Read reference data from Arrow IPC in a worker process."""
    return read_arrow_ipc(ipc_path)
