"""Feature browser service.

特徵瀏覽器頁面已併入 Feature Factory，本 service 僅保留跨 Symbol Coverage
Matrix 計算與其所需的特徵載入器（HDF5 / Parquet / FeatureLibrary）。原骨架
期未串接的 IC / SHAP / 重要度 / quality-scorecard 等占位方法已移除。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py
import numpy as np
import pandas as pd

from api.core.logging import get_logger
from momentum.factories import (
    create_coverage_analyzer,
    create_feature_library,
    create_feature_reader,
)


logger = get_logger("api.feature_browser_service")


class FeatureBrowserService:
    """Service layer for feature browser APIs（僅 Coverage Matrix）。"""

    def __init__(self) -> None:
        self._feature_library = create_feature_library()
        self._coverage_analyzer = create_coverage_analyzer()
        self._feature_reader = create_feature_reader()

    def get_coverage_matrix(
        self,
        symbols: List[str],
        timeframe: str,
        feature_names: Optional[List[str]] = None,
        feature_base_path: str = "data_cache/features",
    ) -> Dict[str, Any]:
        normalized_symbols = [item.strip().upper() for item in (symbols or []) if item and item.strip()]
        if len(normalized_symbols) < 2:
            raise ValueError("Coverage Matrix 需至少 2 個 Symbol")

        normalized_features = [item.strip() for item in (feature_names or []) if item and item.strip()]
        return self._coverage_analyzer.compute_symbol_coverage_matrix(
            symbols=normalized_symbols,
            timeframe=timeframe,
            feature_names=normalized_features,
            feature_base_path=feature_base_path,
        )

    def get_group_coverage(
        self,
        symbols: List[str],
        timeframe: str,
        feature_base_path: str = "data_cache/features",
    ) -> Dict[str, Any]:
        normalized_symbols = [item.strip().upper() for item in (symbols or []) if item and item.strip()]
        if len(normalized_symbols) < 2:
            raise ValueError("Coverage Matrix 需至少 2 個 Symbol")

        return self._coverage_analyzer.compute_group_coverage_matrix(
            symbols=normalized_symbols,
            timeframe=timeframe,
            feature_base_path=feature_base_path,
        )

    def get_group_feature_coverage(
        self,
        symbols: List[str],
        timeframe: str,
        group_name: str,
        feature_base_path: str = "data_cache/features",
        top_n: int = 100,
    ) -> Dict[str, Any]:
        normalized_symbols = [item.strip().upper() for item in (symbols or []) if item and item.strip()]
        if len(normalized_symbols) < 2:
            raise ValueError("Coverage Matrix 需至少 2 個 Symbol")

        return self._coverage_analyzer.compute_group_feature_coverage(
            symbols=normalized_symbols,
            timeframe=timeframe,
            group_name=group_name,
            feature_base_path=feature_base_path,
            top_n=top_n,
        )

    # ===== 特徵載入器 =====
    def _load_features_df(self, features_path: str) -> pd.DataFrame:
        if features_path.startswith("library:"):
            parts = features_path.split(":")
            if len(parts) == 3:
                _, symbol, timeframe = parts
                return self._normalize_df_index(self._feature_library.load(symbol, timeframe))
            raise ValueError("Invalid FeatureLibrary source format, expected library:{symbol}:{timeframe}")

        # V7 Parquet path: try FeatureReader when features_path refers to a
        # per-group Parquet directory (symbol/config_hash with manifest.json).
        if features_path.startswith("parquet:"):
            parts = features_path.split(":")
            if len(parts) == 3:
                _, symbol, config_hash = parts
                return self._load_via_reader(symbol, config_hash)
            raise ValueError("Invalid Parquet source format, expected parquet:{symbol}:{config_hash}")

        path = Path(features_path)
        if not path.exists():
            raise FileNotFoundError(f"features_path not found: {features_path}")

        suffix = path.suffix.lower()
        if suffix in {".csv"}:
            df = pd.read_csv(path)
            return self._normalize_df_index(df)

        if suffix in {".h5", ".hdf5"}:
            try:
                return self._load_hdf5_features(path)
            except Exception as exc:
                logger.error("Failed to load hdf5 features: %s", exc, exc_info=True)
                raise ValueError(f"Invalid HDF5 structure: {features_path}")

        raise ValueError(f"Unsupported features file format: {suffix}")

    def _load_via_reader(self, symbol: str, config_hash: str) -> pd.DataFrame:
        """Load features via V7 FeatureReader (Parquet per-group streaming)."""
        columns = self._feature_reader.list_features(symbol, config_hash)
        if not columns:
            raise FileNotFoundError(f"No features found for {symbol}/{config_hash}")
        df = self._feature_reader.load_columns(symbol, config_hash, columns)
        logger.info(
            "Loaded features via FeatureReader for %s/%s: %d rows x %d cols",
            symbol, config_hash, len(df), len(df.columns),
        )
        return self._normalize_df_index(df)

    def _load_hdf5_features(self, path: Path) -> pd.DataFrame:
        with h5py.File(path, "r") as h5_file:
            dataset_group = self._find_dataset_group(h5_file)
            if dataset_group is None:
                raise ValueError("Unable to locate features dataset")

            features = dataset_group["features"][:]
            raw_names = dataset_group.get("feature_names")
            if raw_names is not None:
                names = [
                    value.decode("utf-8") if isinstance(value, (bytes, bytearray, np.bytes_)) else str(value)
                    for value in raw_names[:]
                ]
            else:
                names = [f"feature_{idx}" for idx in range(features.shape[1])]

            if len(names) != features.shape[1]:
                names = [f"feature_{idx}" for idx in range(features.shape[1])]

            df = pd.DataFrame(features, columns=names)

            timestamps_ds = dataset_group.get("timestamps")
            if timestamps_ds is not None:
                ts_values = timestamps_ds[:]
                if np.issubdtype(ts_values.dtype, np.number):
                    # Auto-detect unit: Binance ms timestamps are ~1.7e12;
                    # feature factory stores Unix seconds (~1.7e9).
                    unit = "ms" if len(ts_values) > 0 and ts_values[0] > 1e12 else "s"
                    idx = pd.to_datetime(ts_values, unit=unit, errors="coerce")
                else:
                    idx = pd.to_datetime(ts_values, errors="coerce")
                df.index = idx

            return self._normalize_df_index(df)

    @staticmethod
    def _find_dataset_group(h5_file: h5py.File) -> Optional[h5py.Group]:
        if "data" in h5_file and isinstance(h5_file["data"], h5py.Group) and "features" in h5_file["data"]:
            return h5_file["data"]

        def visitor(name: str, node: Any) -> Optional[str]:
            if isinstance(node, h5py.Group) and "features" in node:
                return name
            return None

        group_name = h5_file.visititems(visitor)
        if group_name:
            node = h5_file[group_name]
            if isinstance(node, h5py.Group):
                return node
        return None

    @staticmethod
    def _normalize_df_index(df: pd.DataFrame) -> pd.DataFrame:
        if "timestamp" in df.columns:
            index = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.drop(columns=["timestamp"])
            df.index = index
            return df
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.RangeIndex(start=0, stop=len(df), step=1)
        return df


feature_browser_service = FeatureBrowserService()
