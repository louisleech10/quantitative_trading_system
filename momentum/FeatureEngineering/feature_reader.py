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
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from momentum.FeatureEngineering.feature_storage import (
    GAUSSIAN_INT16_ENCODING,
    L7_ENCODING_REGISTRY_METADATA_KEY,
    RANK_UINT16_ENCODING,
    ZSCORE_INT16_ENCODING,
    decode_rank_from_uint16,
    decode_zscore_from_int16,
)
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class FeatureReader:
    """V7 unified feature read interface — Parquet-only, no HDF5."""

    V2_MANIFEST_NAME = "feature_manifest.json"

    def __init__(self, feature_base_path: str = "data_cache/features") -> None:
        self._base = Path(feature_base_path)

    def feature_run_dir(self, symbol: str, tf: str, config_hash: str) -> Path:
        """Return the canonical V2 run directory for one symbol/timeframe/config."""
        safe_symbol = self._safe_path_segment(symbol, "symbol")
        safe_tf = self._safe_path_segment(tf, "tf")
        safe_config_hash = self._safe_path_segment(config_hash, "config_hash")
        return self._base / safe_symbol / safe_tf / safe_config_hash

    def load_manifest_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
    ) -> dict:
        """Load a complete V2 manifest, falling back to V7 legacy metadata."""
        manifest, _base_dir, _is_legacy = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
        )
        return manifest

    def stream_groups_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
    ) -> Iterator[Tuple[str, pd.DataFrame]]:
        """Yield V2 groups one at a time from raw or processed canonical paths."""
        manifest, base_dir, is_legacy = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
        )
        if is_legacy:
            yield from self.stream_groups(symbol, config_hash)
            return

        artifact = self._get_v2_artifact(manifest, artifact_kind)
        for group_name, group_info in artifact.get("groups", {}).items():
            path = self._resolve_manifest_relative_path(base_dir, group_info.get("path") or group_info.get("file"))
            if not path.exists():
                raise FileNotFoundError(f"Parquet file missing: {path}")
            table = self._decode_l7_encoded_table(pq.read_table(str(path)))
            dataframe = table.to_pandas()
            yield group_name, dataframe
            del dataframe

    def load_columns_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        columns: List[str],
        artifact_kind: str = "raw",
    ) -> pd.DataFrame:
        """Column projection for V2 raw/processed artifacts with legacy fallback."""
        manifest, base_dir, is_legacy = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
        )
        if is_legacy:
            return self.load_columns(symbol, config_hash, columns)

        artifact = self._get_v2_artifact(manifest, artifact_kind)
        col_to_group: Dict[str, List[str]] = {}
        for group_name, group_info in artifact.get("groups", {}).items():
            group_cols = set(group_info.get("columns", []))
            needed = [column for column in columns if column in group_cols]
            if needed:
                col_to_group[group_name] = needed

        if not col_to_group:
            logger.warning("No V2 columns matched in any group: %s...", columns[:5])
            return pd.DataFrame()

        frames: List[pd.DataFrame] = []
        for group_name, needed_cols in col_to_group.items():
            group_info = artifact["groups"][group_name]
            path = self._resolve_manifest_relative_path(base_dir, group_info.get("path") or group_info.get("file"))
            if not path.exists():
                raise FileNotFoundError(f"Parquet file missing: {path}")
            table = pq.read_table(str(path), columns=needed_cols)
            table = self._decode_l7_encoded_table(table)
            frames.append(table.to_pandas())

        return pd.concat(frames, axis=1) if frames else pd.DataFrame()

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
            group_columns = [str(column) for column in group_info.get("columns", [])]
            table = pq.read_table(str(path), columns=group_columns or None)
            df = table.to_pandas()
            yield group_name, df
            del df, table

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

    def _resolve_manifest_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str,
    ) -> Tuple[dict, Path, bool]:
        run_dir = self.feature_run_dir(symbol, tf, config_hash)
        manifest_path = run_dir / self.V2_MANIFEST_NAME
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self._validate_manifest_v2(manifest, artifact_kind, manifest_path)
            return manifest, run_dir, False

        legacy_manifest = self.load_manifest(symbol, config_hash)
        legacy_dir = self._base / symbol / config_hash
        return (
            self._adapt_legacy_manifest_v2(
                manifest=legacy_manifest,
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                artifact_kind=artifact_kind,
            ),
            legacy_dir,
            True,
        )

    @staticmethod
    def _validate_manifest_v2(manifest: dict, artifact_kind: str, manifest_path: Path) -> None:
        if not isinstance(manifest, dict):
            raise ValueError(f"Invalid V2 manifest: {manifest_path}")
        if not manifest.get("complete"):
            raise ValueError(f"Incomplete V2 manifest is not readable: {manifest_path}")
        artifact = FeatureReader._get_v2_artifact(manifest, artifact_kind)
        if not artifact.get("complete"):
            raise ValueError(f"Incomplete V2 artifact is not readable: {artifact_kind}")

    @staticmethod
    def _get_v2_artifact(manifest: dict, artifact_kind: str) -> Dict[str, Any]:
        artifacts = manifest.get("artifacts", {})
        artifact = artifacts.get(artifact_kind)
        if not isinstance(artifact, dict):
            raise FileNotFoundError(f"V2 artifact not found: {artifact_kind}")
        return artifact

    @staticmethod
    def _adapt_legacy_manifest_v2(
        manifest: dict,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str,
    ) -> dict:
        groups = manifest.get("groups", {}) if isinstance(manifest, dict) else {}
        total_features = int(manifest.get("total_features", 0)) if isinstance(manifest, dict) else 0
        total_rows = int(manifest.get("total_rows", 0)) if isinstance(manifest, dict) else 0
        artifact = {
            "complete": True,
            "schema_version": "legacy_v7",
            "quality_status": "legacy",
            "path": ".",
            "feature_schema_hash": manifest.get("overall_sha", "legacy") if isinstance(manifest, dict) else "legacy",
            "row_count": total_rows,
            "time_range": {"start": None, "end": None},
            "total_features": total_features,
            "group_count": len(groups),
            "groups": groups,
        }
        return {
            "version": "l7_v2_legacy_adapter",
            "complete": True,
            "legacy_format": True,
            "symbol": symbol,
            "tf": tf,
            "config_hash": config_hash,
            "schema_version": "legacy_v7",
            "quality_status": "legacy",
            "feature_schema_hash": artifact["feature_schema_hash"],
            "row_count": total_rows,
            "time_range": artifact["time_range"],
            "total_features": total_features,
            "groups": groups,
            "artifacts": {artifact_kind: artifact},
        }

    @staticmethod
    def _resolve_manifest_relative_path(base_dir: Path, raw_path: Optional[str]) -> Path:
        if not raw_path:
            raise ValueError("Manifest group path is missing")
        relative_path = Path(str(raw_path))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"Unsafe manifest path: {raw_path}")
        return base_dir / relative_path

    @staticmethod
    def _decode_l7_encoded_table(table: pa.Table) -> pa.Table:
        metadata = table.schema.metadata or {}
        raw_registry = metadata.get(L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8"))
        if not raw_registry:
            return table

        try:
            registry = json.loads(raw_registry.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid l7_encoding_registry metadata") from exc

        arrays: List[Any] = []
        names: List[str] = []
        for column_name in table.column_names:
            column_registry = registry.get(column_name)
            if not column_registry:
                arrays.append(table[column_name])
                names.append(column_name)
                continue

            encoding_type = column_registry.get("encoding_type")
            column_values = table[column_name].to_pandas().to_numpy()
            if encoding_type == RANK_UINT16_ENCODING:
                window = int(column_registry.get("window") or 0)
                arrays.append(pa.array(decode_rank_from_uint16(column_values, window)))
            elif encoding_type in {ZSCORE_INT16_ENCODING, GAUSSIAN_INT16_ENCODING}:
                arrays.append(pa.array(decode_zscore_from_int16(column_values)))
            else:
                arrays.append(table[column_name])
            names.append(column_name)

        decoded_table = pa.Table.from_arrays(arrays, names=names)
        return decoded_table.replace_schema_metadata(metadata)

    @staticmethod
    def _safe_path_segment(value: str, field_name: str) -> str:
        segment = str(value).strip()
        if not segment or segment in {".", ".."} or "/" in segment or "\\" in segment:
            raise ValueError(f"Invalid {field_name}: {value!r}")
        return segment
