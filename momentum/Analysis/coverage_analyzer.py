"""Coverage analysis utilities for IC analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Tuple

import h5py
import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.protocols import IFeatureReader
from momentum.FeatureEngineering.feature_reader import FeatureReader


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

    def _find_latest_v2_config_hash(
        self,
        symbol: str,
        timeframe: str,
        feature_base_path: str,
    ) -> str | None:
        """掃描 V2 佈局 {symbol}/{tf}/{hash}/feature_manifest.json，取最新 config_hash。"""
        base = Path(feature_base_path).expanduser().resolve()
        tf_dir = base / symbol / timeframe.strip()
        if not tf_dir.is_dir():
            return None

        candidates: list[str] = []
        for config_dir in tf_dir.iterdir():
            if not config_dir.is_dir():
                continue
            manifest_path = config_dir / FeatureReader.V2_MANIFEST_NAME
            if manifest_path.exists():
                candidates.append(config_dir.name)

        if not candidates:
            return None
        return sorted(candidates, reverse=True)[0]

    def _load_v2_manifest_for_symbol(
        self,
        symbol: str,
        timeframe: str,
        feature_base_path: str,
        config_hash: str | None = None,
    ) -> Tuple[dict, str] | None:
        """載入單一 symbol 的 V2 manifest；失敗回 None。"""
        resolved_hash = config_hash or self._find_latest_v2_config_hash(symbol, timeframe, feature_base_path)
        if resolved_hash is None:
            return None

        try:
            reader = self._get_feature_reader(feature_base_path)
            manifest = reader.load_manifest_v2(
                symbol,
                timeframe.strip(),
                resolved_hash,
                artifact_kind="raw",
            )
            return manifest, resolved_hash
        except Exception as exc:
            logger.warning(
                "Coverage: V2 manifest load failed for %s/%s: %s",
                symbol,
                timeframe,
                exc,
            )
            return None

    @staticmethod
    def _collect_v2_columns(manifest: dict) -> list[str]:
        artifact = FeatureReader._get_v2_artifact(manifest, "raw")
        columns: list[str] = []
        for group_info in artifact.get("groups", {}).values():
            if not isinstance(group_info, dict):
                continue
            columns.extend(str(column) for column in group_info.get("columns", []))
        return list(dict.fromkeys(columns))

    def _load_symbol_features(
        self,
        symbol: str,
        timeframe: str,
        feature_base_path: str,
    ) -> pd.DataFrame | None:
        """Load features for a symbol: V2 → V7 → legacy HDF5。"""
        base = Path(feature_base_path).expanduser().resolve()
        tf = timeframe.strip()

        # V2 path: {symbol}/{timeframe}/{config_hash}/feature_manifest.json
        v2_manifest_bundle = self._load_v2_manifest_for_symbol(symbol, tf, feature_base_path)
        if v2_manifest_bundle is not None:
            manifest, config_hash = v2_manifest_bundle
            try:
                reader = self._get_feature_reader(str(base))
                columns = self._collect_v2_columns(manifest)
                if columns:
                    df = reader.load_columns_v2(symbol, tf, config_hash, columns, artifact_kind="raw")
                    if not df.empty:
                        logger.info(
                            "Coverage: loaded %s via V2 FeatureReader (%d cols)",
                            symbol,
                            len(df.columns),
                        )
                        return df
            except Exception as exc:
                logger.warning(
                    "Coverage: V2 FeatureReader failed for %s: %s, falling back",
                    symbol,
                    exc,
                )

        # V7 path: scan for manifest.json in feature_base_path/{symbol}/*/
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

    def compute_group_coverage_matrix(
        self,
        symbols: list[str],
        timeframe: str,
        feature_base_path: str = "data_cache/features",
    ) -> dict[str, object]:
        """group × symbol 平均 coverage（純 manifest nan_ratio，零 parquet 載入）。"""

        normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]
        if len(normalized_symbols) == 0:
            raise ValueError("symbols cannot be empty")
        if not timeframe or not timeframe.strip():
            raise ValueError("timeframe cannot be empty")

        dedup_symbols = list(dict.fromkeys(normalized_symbols))
        tf = timeframe.strip()

        symbol_manifests: dict[str, dict | None] = {}
        missing_symbols: list[str] = []
        all_groups: set[str] = set()

        for symbol in dedup_symbols:
            bundle = self._load_v2_manifest_for_symbol(symbol, tf, feature_base_path)
            if bundle is None:
                symbol_manifests[symbol] = None
                missing_symbols.append(symbol)
                continue

            manifest, _config_hash = bundle
            symbol_manifests[symbol] = manifest
            artifact = FeatureReader._get_v2_artifact(manifest, "raw")
            all_groups.update(str(name) for name in artifact.get("groups", {}).keys())

        matrix: dict[str, dict[str, float | None]] = {
            group_name: {symbol: None for symbol in dedup_symbols} for group_name in all_groups
        }

        for symbol in dedup_symbols:
            manifest = symbol_manifests.get(symbol)
            if manifest is None:
                continue

            artifact = FeatureReader._get_v2_artifact(manifest, "raw")
            for group_name, group_info in artifact.get("groups", {}).items():
                if not isinstance(group_info, dict):
                    continue
                nan_ratio = group_info.get("nan_ratio")
                if nan_ratio is None:
                    continue
                coverage = float(np.clip(1.0 - float(nan_ratio), 0.0, 1.0))
                matrix.setdefault(str(group_name), {item: None for item in dedup_symbols})
                matrix[str(group_name)][symbol] = coverage

        divergence: dict[str, float] = {}
        for group_name, symbol_values in matrix.items():
            coverages = [
                value
                for value in symbol_values.values()
                if isinstance(value, float) and np.isfinite(value)
            ]
            if len(coverages) >= 2:
                divergence[group_name] = float(max(coverages) - min(coverages))

        sorted_groups = sorted(
            all_groups,
            key=lambda name: divergence.get(name, -1.0),
            reverse=True,
        )

        symbol_coverages: dict[str, float] = {}
        for symbol in dedup_symbols:
            values = [
                matrix[group_name].get(symbol)
                for group_name in sorted_groups
                if isinstance(matrix.get(group_name, {}).get(symbol), float)
            ]
            symbol_coverages[symbol] = float(np.mean(values)) if values else 0.0

        all_coverages = [value for value in symbol_coverages.values() if np.isfinite(value)]
        summary = {
            "avg_coverage": float(np.mean(all_coverages)) if all_coverages else 0.0,
            "worst_symbol": min(symbol_coverages, key=symbol_coverages.get) if symbol_coverages else None,
            "worst_group": max(divergence, key=divergence.get) if divergence else None,
            "missing_symbols": missing_symbols,
        }

        return {
            "groups": sorted_groups,
            "symbols": dedup_symbols,
            "matrix": matrix,
            "divergence": divergence,
            "summary": summary,
        }

    def compute_group_feature_coverage(
        self,
        symbols: list[str],
        timeframe: str,
        group_name: str,
        feature_base_path: str = "data_cache/features",
        top_n: int = 100,
    ) -> dict[str, object]:
        """單一 group 的 per-feature coverage（僅載入該 group 欄位）。"""

        normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]
        if len(normalized_symbols) == 0:
            raise ValueError("symbols cannot be empty")
        if not timeframe or not timeframe.strip():
            raise ValueError("timeframe cannot be empty")
        if not group_name or not group_name.strip():
            raise ValueError("group_name cannot be empty")

        dedup_symbols = list(dict.fromkeys(normalized_symbols))
        tf = timeframe.strip()
        target_group = group_name.strip()

        feature_names: set[str] = set()
        matrix: dict[str, dict[str, float | None]] = {}
        row_counts: dict[str, int] = {}

        for symbol in dedup_symbols:
            bundle = self._load_v2_manifest_for_symbol(symbol, tf, feature_base_path)
            if bundle is None:
                row_counts[symbol] = 0
                continue

            manifest, config_hash = bundle
            artifact = FeatureReader._get_v2_artifact(manifest, "raw")
            groups = artifact.get("groups", {})
            group_info = groups.get(target_group)
            if not isinstance(group_info, dict):
                raise ValueError(f"group not found: {target_group}")

            columns = [str(column) for column in group_info.get("columns", [])]
            if not columns:
                row_counts[symbol] = 0
                continue

            reader = self._get_feature_reader(feature_base_path)
            frame = reader.load_columns_v2(symbol, tf, config_hash, columns, artifact_kind="raw")
            total = int(frame.shape[0])
            row_counts[symbol] = total

            for column in columns:
                feature_names.add(column)
                matrix.setdefault(column, {item: None for item in dedup_symbols})
                if column not in frame.columns or total <= 0:
                    matrix[column][symbol] = None
                    continue

                series = pd.to_numeric(frame[column], errors="coerce")
                valid_count = int(series.notna().sum())
                coverage = float(valid_count / total)
                matrix[column][symbol] = float(np.clip(coverage, 0.0, 1.0))

        dedup_features = sorted(feature_names)
        divergence: dict[str, float] = {}
        for feature_name in dedup_features:
            coverages = [
                value
                for value in matrix.get(feature_name, {}).values()
                if isinstance(value, float) and np.isfinite(value)
            ]
            if len(coverages) >= 2:
                divergence[feature_name] = float(max(coverages) - min(coverages))

        sorted_features = sorted(
            dedup_features,
            key=lambda name: divergence.get(name, -1.0),
            reverse=True,
        )
        limit = max(1, int(top_n))
        if len(sorted_features) > limit:
            sorted_features = sorted_features[:limit]

        return {
            "features": sorted_features,
            "symbols": dedup_symbols,
            "matrix": {name: matrix.get(name, {}) for name in sorted_features},
            "divergence": {name: divergence.get(name, 0.0) for name in sorted_features},
            "row_counts": row_counts,
            "group_name": target_group,
        }
