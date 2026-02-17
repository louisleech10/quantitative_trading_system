"""Feature browser service for Phase 2.12."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py
import numpy as np
import pandas as pd

from api.core.logging import get_logger
from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics


logger = get_logger("api.feature_browser_service")


class FeatureBrowserService:
    """Service layer for feature browser APIs."""

    def __init__(self) -> None:
        self._quality_diagnostics = FeatureQualityDiagnostics(config={})

    def get_catalog(self, features_path: str) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        if df.empty:
            return {
                "items": [],
                "summary": {
                    "total_features": 0,
                    "total_categories": 0,
                    "avg_coverage": 0.0,
                    "stationary_ratio": 0.0,
                    "low_quality_count": 0,
                    "redundant_pairs": 0,
                },
            }

        adf_results = self._quality_diagnostics.run_batch_adf_test(df)
        corr = df.corr(method="spearman")
        redundant_pairs = 0
        for row_idx in range(corr.shape[0]):
            for col_idx in range(row_idx + 1, corr.shape[1]):
                value = corr.iat[row_idx, col_idx]
                if pd.notna(value) and abs(float(value)) >= 0.9:
                    redundant_pairs += 1

        items: List[Dict[str, Any]] = []
        stationary_count = 0
        low_quality_count = 0
        categories = set()

        for column in df.columns:
            series = df[column]
            category = self._infer_category(column)
            categories.add(category)
            coverage = float(series.notna().mean())
            nan_pct = float(series.isna().mean()) * 100.0
            adf_result = adf_results.get(column, {})
            is_stationary = bool(adf_result.get("is_stationary", False))
            if is_stationary:
                stationary_count += 1
            if (not is_stationary) or nan_pct > 20.0:
                low_quality_count += 1

            items.append(
                {
                    "name": column,
                    "category": category,
                    "source": "features",
                    "layer": self._infer_layer(column),
                    "family": column.split("_")[0] if "_" in column else "general",
                    "params": {},
                    "coverage": coverage,
                    "mean": self._safe_float(series.mean()),
                    "std": self._safe_float(series.std()),
                    "nan_pct": nan_pct,
                }
            )

        summary = {
            "total_features": int(df.shape[1]),
            "total_categories": len(categories),
            "avg_coverage": float(df.notna().mean().mean()),
            "stationary_ratio": float(stationary_count / max(1, df.shape[1])),
            "low_quality_count": low_quality_count,
            "redundant_pairs": redundant_pairs,
        }
        return {"items": items, "summary": summary}

    def get_distribution(self, features_path: str, feature_name: str, bins: int) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        if feature_name not in df.columns:
            raise FileNotFoundError(f"Feature not found: {feature_name}")

        series = df[feature_name]
        clean = series.replace([np.inf, -np.inf], np.nan).dropna()
        if clean.empty:
            histogram_payload: List[Dict[str, Any]] = []
            kde_x: List[float] = []
            kde_y: List[float] = []
        else:
            counts, edges = np.histogram(clean.values, bins=bins, density=False)
            total = max(1, int(counts.sum()))
            histogram_payload = []
            for idx, count in enumerate(counts):
                left = float(edges[idx])
                right = float(edges[idx + 1])
                width = max(right - left, 1e-12)
                density = float((count / total) / width)
                histogram_payload.append(
                    {
                        "left": left,
                        "right": right,
                        "count": int(count),
                        "density": density,
                    }
                )

            kde_x, kde_y = self._estimate_kde(clean.values)

        jb_stat, jb_pvalue = self._jarque_bera(clean)
        stats = {
            "mean": self._safe_float(clean.mean()) if not clean.empty else None,
            "std": self._safe_float(clean.std()) if not clean.empty else None,
            "skew": self._safe_float(clean.skew()) if not clean.empty else None,
            "kurtosis": self._safe_float(clean.kurt()) if not clean.empty else None,
            "min": self._safe_float(clean.min()) if not clean.empty else None,
            "max": self._safe_float(clean.max()) if not clean.empty else None,
            "median": self._safe_float(clean.median()) if not clean.empty else None,
            "q25": self._safe_float(clean.quantile(0.25)) if not clean.empty else None,
            "q75": self._safe_float(clean.quantile(0.75)) if not clean.empty else None,
            "nan_pct": float(series.isna().mean()) * 100.0,
            "unique_count": int(clean.nunique()),
            "zero_count": int((clean == 0).sum()),
            "jb_stat": jb_stat,
            "jb_pvalue": jb_pvalue,
        }

        return {
            "feature_name": feature_name,
            "bins": bins,
            "histogram": histogram_payload,
            "kde_x": kde_x,
            "kde_y": kde_y,
            "statistics": stats,
        }

    def get_time_series(
        self,
        features_path: str,
        features: List[str],
        sample_rate: int,
    ) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        selected = self._resolve_selected_features(df, features, max_features=5)
        sampled = df[selected].iloc[:: max(1, sample_rate)]

        points = []
        for idx, row in sampled.iterrows():
            values = {feature: self._safe_float(row[feature]) for feature in selected}
            points.append({"timestamp": str(idx), "values": values})

        acf_payload: Dict[str, List[Dict[str, Any]]] = {}
        fft_payload: Dict[str, List[Dict[str, Any]]] = {}
        for feature in selected:
            acf_payload[feature] = self._compute_acf(sampled[feature])
            fft_payload[feature] = self._compute_fft(sampled[feature])

        return {
            "features": selected,
            "sample_rate": sample_rate,
            "points": points,
            "acf": acf_payload,
            "periodicity": fft_payload,
        }

    def get_correlation(
        self,
        features_path: str,
        features: List[str],
        method: str,
        max_features: int,
    ) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        resolved_features = self._resolve_selected_features(df, features, max_features=max_features)
        mode = "selected"
        if len(resolved_features) > 100:
            mode = "top_n"
            resolved_features = resolved_features[:100]

        corr = df[resolved_features].corr(method=method).fillna(0.0)
        return {
            "method": method,
            "features": list(corr.columns),
            "matrix": corr.to_numpy().tolist(),
            "mode": mode,
        }

    def run_quality_check(self, features_path: str, selected_features: Optional[List[str]]) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        if selected_features:
            selected = self._resolve_selected_features(df, selected_features, max_features=300)
            df = df[selected]

        diagnostics = self._quality_diagnostics.run_full_diagnostics(df)
        adf_results = diagnostics.get("adf_results", {})
        coverage_stats = diagnostics.get("coverage_stats", {})

        items: List[Dict[str, Any]] = []
        for feature in df.columns:
            adf = adf_results.get(feature, {})
            coverage = coverage_stats.get(feature, {})
            nan_pct = float(1.0 - float(coverage.get("coverage", 0.0))) * 100.0
            items.append(
                {
                    "feature": feature,
                    "adf_pvalue": self._safe_float(adf.get("p_value")),
                    "is_stationary": bool(adf.get("is_stationary", False)),
                    "coverage": float(coverage.get("coverage", 0.0)),
                    "nan_pct": nan_pct,
                }
            )

        return {"results": items}

    def get_data_table(
        self,
        features_path: str,
        page: int,
        page_size: int,
        columns: Optional[List[str]],
    ) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        selected_columns = self._resolve_selected_features(df, columns or [], max_features=1000) if columns else list(df.columns)

        start = max(0, (page - 1) * page_size)
        end = min(start + page_size, len(df))
        sliced = df[selected_columns].iloc[start:end]

        rows: List[Dict[str, Any]] = []
        for idx, row in sliced.iterrows():
            payload: Dict[str, Any] = {"timestamp": str(idx)}
            for column in selected_columns:
                payload[column] = self._safe_float(row[column])
            rows.append(payload)

        return {
            "total_rows": int(len(df)),
            "page": page,
            "page_size": page_size,
            "columns": ["timestamp", *selected_columns],
            "rows": rows,
        }

    def _load_features_df(self, features_path: str) -> pd.DataFrame:
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
                    idx = pd.to_datetime(ts_values, unit="ms", errors="coerce")
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

    @staticmethod
    def _resolve_selected_features(df: pd.DataFrame, requested: List[str], max_features: int) -> List[str]:
        if not requested:
            return list(df.columns[:max_features])

        missing = [feature for feature in requested if feature not in df.columns]
        if missing:
            raise FileNotFoundError(f"Feature not found: {missing[0]}")

        return requested[:max_features]

    @staticmethod
    def _compute_acf(series: pd.Series, max_lag: int = 20) -> List[Dict[str, Any]]:
        clean = series.replace([np.inf, -np.inf], np.nan).dropna().values
        if len(clean) < 3:
            return []

        mean = clean.mean()
        denom = np.sum((clean - mean) ** 2)
        if denom <= 0:
            return []

        result = []
        for lag in range(1, min(max_lag, len(clean) - 1) + 1):
            num = np.sum((clean[:-lag] - mean) * (clean[lag:] - mean))
            result.append({"lag": lag, "value": float(num / denom)})
        return result

    @staticmethod
    def _compute_fft(series: pd.Series, top_k: int = 5) -> List[Dict[str, Any]]:
        clean = series.replace([np.inf, -np.inf], np.nan).dropna().values
        if len(clean) < 8:
            return []

        centered = clean - clean.mean()
        fft_values = np.fft.rfft(centered)
        amplitudes = np.abs(fft_values)
        freqs = np.fft.rfftfreq(len(centered), d=1.0)

        if len(amplitudes) <= 1:
            return []

        pairs = [(float(freqs[i]), float(amplitudes[i])) for i in range(1, len(amplitudes))]
        pairs.sort(key=lambda item: item[1], reverse=True)
        return [{"frequency": pair[0], "amplitude": pair[1]} for pair in pairs[:top_k]]

    @staticmethod
    def _estimate_kde(values: np.ndarray, points: int = 80) -> tuple[List[float], List[float]]:
        if values.size < 2:
            return [], []
        min_value = float(np.min(values))
        max_value = float(np.max(values))
        if min_value == max_value:
            return [min_value], [1.0]

        x = np.linspace(min_value, max_value, points)
        std = float(np.std(values))
        bandwidth = max(1e-6, 1.06 * std * (values.size ** (-1 / 5)))
        densities = []
        for target in x:
            z = (target - values) / bandwidth
            kernel = np.exp(-0.5 * (z ** 2)) / np.sqrt(2 * np.pi)
            densities.append(float(np.mean(kernel) / bandwidth))
        return x.tolist(), densities

    @staticmethod
    def _jarque_bera(series: pd.Series) -> tuple[Optional[float], Optional[float]]:
        n = int(series.shape[0])
        if n < 4:
            return None, None
        skew = float(series.skew())
        kurtosis = float(series.kurt())
        jb = (n / 6.0) * ((skew ** 2) + ((kurtosis ** 2) / 4.0))
        pvalue = float(np.exp(-jb / 2.0))
        return jb, pvalue

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None
        if np.isfinite(converted):
            return converted
        return None

    @staticmethod
    def _infer_category(name: str) -> str:
        name_lower = name.lower()
        if "rsi" in name_lower:
            return "momentum"
        if "ema" in name_lower or "sma" in name_lower:
            return "trend"
        if "vol" in name_lower:
            return "volatility"
        if "ratio" in name_lower:
            return "ratio"
        return "general"

    @staticmethod
    def _infer_layer(name: str) -> str:
        if "lag" in name.lower():
            return "L3"
        if "rolling" in name.lower() or "cross" in name.lower():
            return "L2"
        return "L1"


feature_browser_service = FeatureBrowserService()
