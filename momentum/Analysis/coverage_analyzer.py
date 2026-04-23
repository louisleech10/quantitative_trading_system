"""Coverage analysis utilities for IC analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import h5py
import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.protocols import IFeatureReader


logger = get_logger(__name__)


class CoverageAnalyzer:
    """因子覆蓋率分析 — 確保因子在大部分時間點有值。"""

    def __init__(
        self,
        feature_reader_factory: Optional[Callable[[str], IFeatureReader]] = None,
    ) -> None:
        self._feature_reader_factory = feature_reader_factory

    def compute_time_coverage(self, feature: pd.Series) -> float:
        """時間覆蓋率: count(非NaN) / total_bars。"""

        total = int(len(feature))
        if total == 0:
            return float("nan")
        return float(feature.notna().sum() / total)

    def compute_effective_start(self, feature: pd.Series) -> int:
        """有效起始點: 第一個非 NaN 的 index 位置。"""

        if feature.empty:
            return -1
        mask = feature.notna().to_numpy()
        if not mask.any():
            return -1
        return int(np.argmax(mask))

    def compute_all(self, features_df: pd.DataFrame) -> dict[str, dict]:
        """批次計算覆蓋率。"""

        results: dict[str, dict] = {}
        for feature_name in features_df.columns:
            series = features_df[feature_name]
            coverage = self.compute_time_coverage(series)
            effective_start = self.compute_effective_start(series)
            nan_count = int(series.isna().sum())
            results[feature_name] = {
                "coverage": coverage,
                "effective_start": effective_start,
                "nan_count": nan_count,
            }
        return results

    def flag_low_coverage(self, coverage_results: dict, threshold: float = 0.5) -> list[str]:
        """標記低覆蓋率特徵。"""

        low_features: list[str] = []
        for feature_name, metrics in (coverage_results or {}).items():
            coverage = metrics.get("coverage")
            if coverage is None or (isinstance(coverage, float) and np.isnan(coverage)):
                continue
            if coverage < threshold:
                low_features.append(feature_name)
        return low_features

    @staticmethod
    def _resolve_feature_file_path(symbol: str, timeframe: str, feature_base_path: str) -> Path:
        base_path = Path(feature_base_path).expanduser().resolve()
        return base_path / f"{symbol}_{timeframe}_factory.h5"

    def _load_symbol_features(
        self,
        symbol: str,
        timeframe: str,
        feature_base_path: str,
    ) -> pd.DataFrame | None:
        """Load features for a symbol, trying V7 FeatureReader first, then legacy HDF5."""
        # V7 path: scan for manifest.json in feature_base_path/{symbol}/*/
        base = Path(feature_base_path).expanduser().resolve()
        sym_dir = base / symbol
        if sym_dir.is_dir():
            for config_dir in sorted(sym_dir.iterdir(), reverse=True):
                manifest_path = config_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        reader = self._get_feature_reader(str(base))
                        config_hash = config_dir.name
                        columns = reader.list_features(symbol, config_hash)
                        if columns:
                            df = reader.load_columns(symbol, config_hash, columns)
                            if not df.empty:
                                logger.info(
                                    "Coverage: loaded %s via FeatureReader (%d cols)",
                                    symbol, len(df.columns),
                                )
                                return df
                    except Exception as exc:
                        logger.warning(
                            "Coverage: FeatureReader failed for %s: %s, falling back to HDF5",
                            symbol, exc,
                        )

        # Legacy HDF5 fallback
        file_path = self._resolve_feature_file_path(symbol, timeframe, feature_base_path)
        if not file_path.exists():
            logger.warning("Coverage matrix feature file not found: %s", file_path)
            return None
        try:
            return self._load_feature_dataframe(file_path)
        except Exception as exc:
            logger.warning("Coverage matrix failed to read %s: %s", file_path, exc)
            return None

    def _get_feature_reader(self, feature_base_path: str) -> IFeatureReader:
        if self._feature_reader_factory is None:
            from momentum.factories import create_feature_reader

            self._feature_reader_factory = create_feature_reader
        return self._feature_reader_factory(feature_base_path)

    @staticmethod
    def _decode_feature_names(raw_names: np.ndarray, feature_count: int) -> list[str]:
        names = [
            value.decode("utf-8") if isinstance(value, (bytes, bytearray, np.bytes_)) else str(value)
            for value in raw_names
        ]
        if len(names) != feature_count:
            return [f"feature_{idx}" for idx in range(feature_count)]
        return names

    @staticmethod
    def _find_dataset_group(h5_file: h5py.File) -> h5py.Group | None:
        if "data" in h5_file and isinstance(h5_file["data"], h5py.Group) and "features" in h5_file["data"]:
            return h5_file["data"]

        candidate_path: str | None = None

        def visitor(name: str, node: object) -> None:
            nonlocal candidate_path
            if candidate_path is not None:
                return
            if isinstance(node, h5py.Group) and "features" in node:
                candidate_path = name

        h5_file.visititems(visitor)
        if candidate_path is None:
            return None

        node = h5_file[candidate_path]
        if isinstance(node, h5py.Group):
            return node
        return None

    def _load_feature_dataframe(self, file_path: Path) -> pd.DataFrame:
        with h5py.File(file_path, "r") as h5_file:
            dataset_group = self._find_dataset_group(h5_file)
            if dataset_group is None:
                raise ValueError(f"Unable to locate features dataset in {file_path}")

            features = dataset_group["features"][:]
            if features.ndim != 2:
                raise ValueError(f"Invalid feature shape in {file_path}: {features.shape}")

            raw_names = dataset_group.get("feature_names")
            if raw_names is None:
                names = [f"feature_{idx}" for idx in range(features.shape[1])]
            else:
                names = self._decode_feature_names(raw_names[:], features.shape[1])

            return pd.DataFrame(features, columns=names)

    def compute_symbol_coverage_matrix(
        self,
        symbols: list[str],
        timeframe: str,
        feature_names: list[str],
        feature_base_path: str = "data_cache/features",
    ) -> dict[str, object]:
        """回傳 features × symbols 的 NaN 比率矩陣。"""

        normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]
        if len(normalized_symbols) == 0:
            raise ValueError("symbols cannot be empty")
        if not timeframe or not timeframe.strip():
            raise ValueError("timeframe cannot be empty")

        dedup_symbols = list(dict.fromkeys(normalized_symbols))

        normalized_features = [name.strip() for name in feature_names if name and name.strip()]
        dedup_features = list(dict.fromkeys(normalized_features))

        symbol_frames: dict[str, pd.DataFrame | None] = {}
        row_counts: dict[str, int] = {}
        discovered_features: set[str] = set()

        for symbol in dedup_symbols:
            frame = self._load_symbol_features(symbol, timeframe.strip(), feature_base_path)
            if frame is None:
                symbol_frames[symbol] = None
                row_counts[symbol] = 0
                continue

            symbol_frames[symbol] = frame
            row_counts[symbol] = int(frame.shape[0])
            if len(dedup_features) == 0:
                discovered_features.update(str(column) for column in frame.columns)

        if len(dedup_features) == 0:
            dedup_features = sorted(discovered_features)

        matrix: dict[str, dict[str, float | None]] = {}
        valid_counts: dict[str, dict[str, int]] = {}

        for feature_name in dedup_features:
            matrix[feature_name] = {}
            valid_counts[feature_name] = {}
            for symbol in dedup_symbols:
                frame = symbol_frames.get(symbol)
                if frame is None or frame.empty or feature_name not in frame.columns:
                    matrix[feature_name][symbol] = 1.0
                    valid_counts[feature_name][symbol] = 0
                    continue

                series = pd.to_numeric(frame[feature_name], errors="coerce")
                total = int(series.shape[0])
                if total <= 0:
                    matrix[feature_name][symbol] = None
                    valid_counts[feature_name][symbol] = 0
                    continue

                valid_count = int(series.notna().sum())
                nan_ratio = 1.0 - (valid_count / total)
                matrix[feature_name][symbol] = float(np.clip(nan_ratio, 0.0, 1.0))
                valid_counts[feature_name][symbol] = valid_count

        symbol_coverages: dict[str, float] = {}
        for symbol in dedup_symbols:
            coverage_values = [
                1.0 - nan_ratio
                for nan_ratio in (matrix.get(feature_name, {}).get(symbol) for feature_name in dedup_features)
                if isinstance(nan_ratio, float) and np.isfinite(nan_ratio)
            ]
            symbol_coverages[symbol] = float(np.mean(coverage_values)) if coverage_values else 0.0

        feature_coverages: dict[str, float] = {}
        for feature_name in dedup_features:
            coverage_values = [
                1.0 - nan_ratio
                for nan_ratio in matrix.get(feature_name, {}).values()
                if isinstance(nan_ratio, float) and np.isfinite(nan_ratio)
            ]
            feature_coverages[feature_name] = float(np.mean(coverage_values)) if coverage_values else 0.0

        all_coverages = [
            value
            for value in symbol_coverages.values()
            if np.isfinite(value)
        ]

        summary = {
            "avg_coverage": float(np.mean(all_coverages)) if all_coverages else 0.0,
            "worst_symbol": min(symbol_coverages, key=symbol_coverages.get) if symbol_coverages else None,
            "worst_feature": min(feature_coverages, key=feature_coverages.get) if feature_coverages else None,
        }

        return {
            "matrix": matrix,
            "valid_counts": valid_counts,
            "row_counts": row_counts,
            "symbols": dedup_symbols,
            "features": dedup_features,
            "summary": summary,
        }
