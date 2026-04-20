"""FeatureReader — V7 unified read-only interface for consuming per-group Parquet features.

Supports 4 loading modes:
  1. Metadata-Only  (zero data I/O)
  2. Column-Projected (read only requested columns)
  3. Per-Group Streaming (yield groups one at a time for bounded RAM)
  4. Cross-Symbol (load same columns across multiple symbols)

Design reference: FEATURE_STORAGE_ARCHITECTURE_V7.md §11
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

import pandas as pd
import pyarrow.parquet as pq

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class FeatureReader:
    """V7 unified feature read interface — Parquet-only, no HDF5."""

    def __init__(self, feature_base_path: str = "data_cache/features") -> None:
        self._base = Path(feature_base_path)

    # ------------------------------------------------------------------
    # Mode 1: Metadata-Only
    # ------------------------------------------------------------------

    def load_manifest(self, symbol: str, config_hash: str) -> dict:
        """Load manifest.json for a symbol/config_hash pair."""
        path = self._base / symbol / config_hash / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"manifest.json not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_features(self, symbol: str, config_hash: str) -> List[str]:
        """List all feature names without loading data.

        Reads from columns.json.gz when available; falls back to Parquet
        schema scanning if the compressed file is missing.
        """
        gz_path = self._base / symbol / config_hash / "columns.json.gz"
        if gz_path.exists():
            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        return self._list_features_from_parquet(symbol, config_hash)

    # ------------------------------------------------------------------
    # Mode 2: Column-Projected
    # ------------------------------------------------------------------

    def load_columns(
        self,
        symbol: str,
        config_hash: str,
        columns: List[str],
    ) -> pd.DataFrame:
        """Column projection — read only the requested columns."""
        manifest = self.load_manifest(symbol, config_hash)
        base_dir = self._base / symbol / config_hash

        # Build a reverse lookup: column_name → group_name for fast matching
        col_to_group: Dict[str, List[str]] = {}
        for group_name, group_info in manifest["groups"].items():
            group_cols = set(group_info.get("columns", []))
            needed = [c for c in columns if c in group_cols]
            if needed:
                col_to_group[group_name] = needed

        if not col_to_group:
            logger.warning(
                "No columns matched in any group: %s...",
                columns[:5],
            )
            return pd.DataFrame()

        frames: List[pd.DataFrame] = []
        for group_name, needed_cols in col_to_group.items():
            group_info = manifest["groups"][group_name]
            path = base_dir / group_info["file"]
            if not path.exists():
                raise FileNotFoundError(f"Parquet file missing: {path}")
            table = pq.read_table(str(path), columns=needed_cols)
            frames.append(table.to_pandas())

        return pd.concat(frames, axis=1) if frames else pd.DataFrame()

    # ------------------------------------------------------------------
    # Mode 3: Per-Group Streaming
    # ------------------------------------------------------------------

    def stream_groups(
        self,
        symbol: str,
        config_hash: str,
    ) -> Iterator[Tuple[str, pd.DataFrame]]:
        """Yield (group_name, DataFrame) one group at a time."""
        manifest = self.load_manifest(symbol, config_hash)
        base_dir = self._base / symbol / config_hash

        for group_name, group_info in manifest["groups"].items():
            path = base_dir / group_info["file"]
            if not path.exists():
                logger.warning("Parquet missing for group %s: %s", group_name, path)
                continue
            df = pq.read_table(str(path)).to_pandas()
            yield group_name, df
            del df

    # ------------------------------------------------------------------
    # Mode 4: Cross-Symbol
    # ------------------------------------------------------------------

    def load_cross_symbol(
        self,
        symbols: List[str],
        config_hash: str,
        columns: List[str],
    ) -> pd.DataFrame:
        """Load the same columns across multiple symbols → MultiIndex."""
        frames: List[pd.DataFrame] = []
        for sym in symbols:
            df = self.load_columns(sym, config_hash, columns)
            df["_symbol"] = sym
            frames.append(df)

        if not frames:
            return pd.DataFrame()
        result = pd.concat(frames)
        return result.set_index("_symbol", append=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _list_features_from_parquet(self, symbol: str, config_hash: str) -> List[str]:
        """Fallback: collect column names by scanning Parquet schemas."""
        manifest = self.load_manifest(symbol, config_hash)
        base_dir = self._base / symbol / config_hash
        all_columns: List[str] = []
        for group_name, group_info in manifest["groups"].items():
            path = base_dir / group_info["file"]
            if path.exists():
                schema = pq.read_schema(str(path))
                all_columns.extend(schema.names)
        return all_columns
