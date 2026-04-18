"""Disk-backed memory utilities for large feature matrices.

On 8 GB M1 Mac, feature matrices can exceed physical RAM (e.g. 227K cols ×
12,888 rows × float32 = 11.7 GB).  ``np.empty`` forces all pages into
anonymous swap; ``np.memmap`` uses file-backed pages that the OS can evict
cheaply (dirty → write-back to file, clean → discard).  This keeps the
resident set small and avoids macOS OOM-killer.

Usage::

    arr = create_temp_memmap((12888, 168300))   # 8.66 GB on disk, ~0 in RAM
    arr[:, 0:100] = some_data                   # only 100 col pages loaded
    del arr                                     # file auto-deleted (Unix)

All public helpers return ``np.memmap`` arrays in **C (row-major) order**
so that writing C-order source arrays (the default from pandas/numpy) is
a fast row-by-row memcpy instead of a slow element-level transpose.
"""

from __future__ import annotations

import gc
import os
import tempfile
import time
from typing import List, Optional

import numpy as np
import pandas as pd

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None

from momentum.core.logging import get_logger

logger = get_logger(__name__)

# DataFrames smaller than this threshold use normal pd.concat (faster for
# small/medium workloads).  500 MB is well within 8 GB RAM budget.
MEMMAP_THRESHOLD_BYTES: int = 500_000_000
HEARTBEAT_INTERVAL_SECONDS: float = 30.0


def _resolve_copy_block_rows() -> int:
    """Rows per block when copying into memmap (0 = single-shot)."""
    raw = os.getenv("FFACT_MEMMAP_COPY_BLOCK_ROWS", "1024").strip()
    try:
        rows = int(raw)
    except ValueError:
        rows = 1024
    return max(rows, 0)


def _get_process_rss_mb() -> Optional[float]:
    """Return current process RSS in MB, or None when unavailable."""
    if psutil is None:
        return None
    try:
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def create_temp_memmap(
    shape: tuple,
    dtype: np.dtype = np.float32,
    prefix: str = "ff_",
) -> np.memmap:
    """Create a temporary file-backed memmap array (C-order).

    On Unix/macOS the temp file is ``os.unlink``-ed immediately after
    creation.  The file stays alive through the memmap's open file
    descriptor and is truly deleted once all references are garbage
    collected.  This avoids leaking temp files on crashes.

    C-order (row-major) is chosen because source arrays from pandas
    DataFrames are C-order by default.  Writing C-order source into
    C-order dest is a fast row-by-row memcpy; writing into F-order
    requires element-level transposition (10-100× slower for large
    arrays — the old 2-minute concat_with_memmap was caused by this).

    Parameters
    ----------
    shape : tuple
        Array shape, e.g. ``(n_rows, n_cols)``.
    dtype : numpy dtype, default ``np.float32``
        Element data type.
    prefix : str
        Temp-file name prefix (for debug ``lsof``).

    Returns
    -------
    np.memmap
        Writable C-order memmap.
    """
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".dat", prefix=prefix)
    os.close(tmp_fd)

    arr = np.memmap(tmp_path, dtype=dtype, mode="w+", shape=shape, order="C")
    os.unlink(tmp_path)  # Unix: kept alive by memmap fd

    est_gb = np.prod(shape) * np.dtype(dtype).itemsize / 1e9
    logger.info(
        "[memmap] created: shape=%s, dtype=%s, est=%.2f GB  (file auto-unlinked)",
        shape,
        dtype,
        est_gb,
    )
    return arr


def concat_with_memmap(
    dfs: List[pd.DataFrame],
    index: Optional[pd.Index] = None,
    threshold_bytes: int = MEMMAP_THRESHOLD_BYTES,
) -> pd.DataFrame:
    """Concatenate DataFrames along axis=1, using memmap for large results.

    For small results (< *threshold_bytes*), delegates to ``pd.concat``
    for maximum speed.  For large results, allocates a C-order
    memmap and copies each source DF's columns into it, so peak RAM
    stays at roughly one source DF at a time.

    Parameters
    ----------
    dfs : list of DataFrame
        Source frames to concatenate horizontally.
    index : pd.Index, optional
        Override index for the result.  If ``None``, uses the first DF's
        index.
    threshold_bytes : int
        Byte threshold below which plain ``pd.concat`` is used.

    Returns
    -------
    pd.DataFrame
        Combined frame.  If memmap was used, the underlying data is
        file-backed — only accessed pages reside in physical RAM.
    """
    valid_dfs = [df for df in dfs if df is not None and not df.empty]
    if not valid_dfs:
        return pd.DataFrame(index=index)

    # Fast path: single DF → return directly, no copy
    if len(valid_dfs) == 1:
        result = valid_dfs[0]
        if index is not None:
            result = result.set_axis(index)
        return result

    total_cols = sum(df.shape[1] for df in valid_dfs)
    n_rows = valid_dfs[0].shape[0]
    est_bytes = n_rows * total_cols * 4  # assume float32

    if est_bytes < threshold_bytes:
        result = pd.concat(valid_dfs, axis=1, copy=False)
        if index is not None:
            result.index = index
        return result

    logger.info(
        "[memmap concat] %d DFs → %d cols × %d rows ≈ %.2f GB → disk-backed",
        len(valid_dfs),
        total_cols,
        n_rows,
        est_bytes / 1e9,
    )

    out_arr = create_temp_memmap((n_rows, total_cols), prefix="concat_")
    col_names: List[str] = []
    col_offset = 0
    block_rows = _resolve_copy_block_rows()
    if block_rows <= 0:
        block_rows = 1024  # always use block copy to cap peak memory

    result_index = index if index is not None else valid_dfs[0].index

    for idx in range(len(valid_dfs)):
        df = valid_dfs[idx]
        n = df.shape[1]

        logger.info(
            "[memmap concat] copying DF %d/%d (%d cols)",
            idx + 1,
            len(valid_dfs),
            n,
        )

        # Collect column names BEFORE releasing df reference
        col_names.extend(df.columns.tolist())

        # Materialise the underlying numpy array ONCE (zero-copy if already
        # float32 C-order, one-pass copy otherwise).  Then slice rows from
        # the numpy array — avoids the extreme overhead of df.iloc[slice]
        # on wide DataFrames (156K cols → iloc rebuilds DF per block).
        src_arr = df.to_numpy(dtype=np.float32, copy=False)
        if not src_arr.flags["C_CONTIGUOUS"]:
            src_arr = np.ascontiguousarray(src_arr, dtype=np.float32)

        # Release the pandas DF immediately — we only need src_arr now.
        valid_dfs[idx] = None
        del df
        gc.collect()

        last_heartbeat = time.perf_counter()
        for row_start in range(0, n_rows, block_rows):
            row_end = min(row_start + block_rows, n_rows)
            out_arr[row_start:row_end, col_offset : col_offset + n] = src_arr[row_start:row_end]
            now = time.perf_counter()
            if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                rss_mb = _get_process_rss_mb()
                if rss_mb is not None:
                    logger.info(
                        "[concat_memmap] DF %d/%d: %d/%d rows copied, RSS=%.0f MB",
                        idx + 1,
                        len(valid_dfs),
                        row_end,
                        n_rows,
                        rss_mb,
                    )
                else:
                    logger.info(
                        "[concat_memmap] DF %d/%d: %d/%d rows copied",
                        idx + 1,
                        len(valid_dfs),
                        row_end,
                        n_rows,
                    )
                last_heartbeat = now

        col_offset += n
        del src_arr
        gc.collect()

    return pd.DataFrame(data=out_arr, index=result_index, columns=col_names, copy=False)
