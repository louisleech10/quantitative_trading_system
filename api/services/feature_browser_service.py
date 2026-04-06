"""Feature browser service for Phase 8 (M9)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py
import numpy as np
import pandas as pd
from scipy import stats

from api.core.logging import get_logger
from momentum.factories import (
    create_coverage_analyzer,
    create_feature_library,
    create_feature_quality_diagnostics,
)


logger = get_logger("api.feature_browser_service")


class FeatureBrowserService:
    """Service layer for feature browser APIs."""

    def __init__(self) -> None:
        self._quality_diagnostics = create_feature_quality_diagnostics(config={})
        self._feature_library = create_feature_library()
        self._coverage_analyzer = create_coverage_analyzer()

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

    def get_overview(self, features_path: str) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        if df.empty:
            return {
                "total_rows": 0,
                "total_features": 0,
                "numeric_features": 0,
                "mean_nan_pct": 0.0,
                "items": [],
            }

        numeric_df = df.select_dtypes(include=[np.number])
        items: List[Dict[str, Any]] = []
        for column in df.columns:
            series = pd.to_numeric(df[column], errors="coerce")
            items.append(
                {
                    "feature_name": column,
                    "data_type": str(df[column].dtype),
                    "mean": self._safe_float(series.mean()),
                    "std": self._safe_float(series.std()),
                    "min": self._safe_float(series.min()),
                    "max": self._safe_float(series.max()),
                    "nan_pct": float(series.isna().mean()) * 100.0,
                }
            )

        return {
            "total_rows": int(df.shape[0]),
            "total_features": int(df.shape[1]),
            "numeric_features": int(numeric_df.shape[1]),
            "mean_nan_pct": float(pd.isna(df).mean().mean() * 100.0),
            "items": items,
        }

    def get_ic_dashboard(self, features_path: str, top_k: int = 50) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if numeric_df.shape[1] < 2 or numeric_df.shape[0] < 100:
            return {
                "available": False,
                "message": "IC 資料不可用，請先確認特徵資料筆數與欄位數。",
                "entries": [],
            }

        target = numeric_df.iloc[:, 0].shift(-1)
        entries: List[Dict[str, Any]] = []
        for feature in numeric_df.columns:
            aligned = pd.DataFrame({"x": numeric_df[feature], "y": target}).dropna()
            if len(aligned) < 30:
                continue

            corr, pvalue = stats.spearmanr(aligned["x"].to_numpy(), aligned["y"].to_numpy())
            if np.isnan(corr):
                continue

            window = min(63, max(10, len(aligned) // 4))
            rolling_ic = (
                aligned["x"].rolling(window=window, min_periods=max(10, window // 2)).corr(aligned["y"]).dropna()
            )
            rolling_values = rolling_ic.tail(20).to_numpy(dtype=float)
            ic_std = float(np.std(rolling_values)) if rolling_values.size > 0 else 0.0
            ir = float(corr / (ic_std + 1e-8))
            t_stat = float(corr * np.sqrt(len(aligned)) / (ic_std + 1e-8))

            if pvalue < 0.01:
                significance = "***"
            elif pvalue < 0.05:
                significance = "**"
            elif pvalue < 0.1:
                significance = "*"
            else:
                significance = ""

            entries.append(
                {
                    "feature_name": feature,
                    "ic_mean": float(corr),
                    "ic_std": ic_std,
                    "ir": ir,
                    "t_stat": t_stat,
                    "significance": significance,
                    "sparkline": [float(v) for v in rolling_values.tolist()],
                }
            )

        entries.sort(key=lambda item: abs(item["ic_mean"]), reverse=True)
        return {
            "available": True,
            "message": None,
            "entries": entries[:top_k],
        }

    def get_rolling_ic(self, features_path: str, feature_name: str, window: int = 63) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if feature_name not in numeric_df.columns:
            raise FileNotFoundError(f"Feature not found: {feature_name}")
        if numeric_df.shape[1] < 2:
            return {"feature_name": feature_name, "window": window, "points": []}

        target = numeric_df.iloc[:, 0].shift(-1)
        aligned = pd.DataFrame({"x": numeric_df[feature_name], "y": target}).dropna()
        if aligned.empty:
            return {"feature_name": feature_name, "window": window, "points": []}

        rolling_ic = aligned["x"].rolling(window=window, min_periods=max(20, window // 2)).corr(aligned["y"])
        rolling_std = rolling_ic.rolling(window=max(10, window // 3), min_periods=5).std()
        points: List[Dict[str, Any]] = []
        for idx, value in rolling_ic.dropna().items():
            std = rolling_std.loc[idx] if idx in rolling_std.index else np.nan
            ir = float(value / std) if pd.notna(std) and std != 0 else None
            points.append(
                {
                    "timestamp": str(idx),
                    "ic": float(value),
                    "ir": ir,
                }
            )

        return {
            "feature_name": feature_name,
            "window": window,
            "points": points,
        }

    def get_quality_scorecard(self, features_path: str, top_k: int = 200) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        if df.empty:
            return {
                "items": [],
                "funnel": {
                    "raw": 0,
                    "after_ic": 0,
                    "after_vif": 0,
                    "final": 0,
                },
            }

        diagnostics = self._quality_diagnostics.run_full_diagnostics(df)
        adf_results = diagnostics.get("adf_results", {})
        coverage_stats = diagnostics.get("coverage_stats", {})
        redundancy_pairs = diagnostics.get("redundancy_scan", {}).get("high_correlation_pairs", [])

        redundant_features = set()
        for left, right, _ in redundancy_pairs:
            redundant_features.add(left)
            redundant_features.add(right)

        items: List[Dict[str, Any]] = []
        for feature in df.columns[:top_k]:
            adf = adf_results.get(feature, {})
            coverage = float(coverage_stats.get(feature, {}).get("coverage", 0.0))
            stationarity_score = 1.0 if bool(adf.get("is_stationary", False)) else 0.4
            coverage_score = float(np.clip(coverage, 0.0, 1.0))
            drift_score = 1.0 if coverage > 0.8 else 0.6
            redundancy_score = 0.5 if feature in redundant_features else 1.0

            total = float(np.clip((stationarity_score + coverage_score + drift_score + redundancy_score) / 4.0, 0.0, 1.0))
            if total >= 0.9:
                grade = "A"
            elif total >= 0.8:
                grade = "B"
            elif total >= 0.7:
                grade = "C"
            elif total >= 0.6:
                grade = "D"
            else:
                grade = "F"

            items.append(
                {
                    "feature_name": feature,
                    "stationarity_score": stationarity_score,
                    "coverage_score": coverage_score,
                    "drift_score": drift_score,
                    "redundancy_score": redundancy_score,
                    "total_score": total,
                    "grade": grade,
                }
            )

        filtered_ic = sum(1 for item in items if item["total_score"] >= 0.6)
        filtered_vif = sum(1 for item in items if item["redundancy_score"] >= 1.0 and item["total_score"] >= 0.6)
        final_count = sum(1 for item in items if item["grade"] in {"A", "B", "C"})

        return {
            "items": items,
            "funnel": {
                "raw": len(items),
                "after_ic": filtered_ic,
                "after_vif": filtered_vif,
                "final": final_count,
            },
        }

    def get_correlation_matrix(
        self,
        features_path: str,
        method: str = "spearman",
        max_features: int = 200,
    ) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        original_feature_count = int(numeric_df.shape[1])
        if original_feature_count == 0:
            return {
                "method": method,
                "features": [],
                "matrix": [],
                "truncated": False,
                "original_feature_count": 0,
            }

        truncated = original_feature_count > max_features
        selected = numeric_df.columns[:max_features]
        corr = numeric_df[selected].corr(method=method).fillna(0.0)

        return {
            "method": method,
            "features": list(corr.columns),
            "matrix": corr.to_numpy(dtype=float).tolist(),
            "truncated": truncated,
            "original_feature_count": original_feature_count,
        }

    def get_vif(self, features_path: str, max_features: int = 200) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if numeric_df.empty:
            return {"items": []}

        selected = list(numeric_df.columns[:max_features])
        matrix = numeric_df[selected].corr(method="pearson").fillna(0.0).to_numpy(dtype=float)
        matrix = matrix + np.eye(matrix.shape[0]) * 1e-6
        inv_corr = np.linalg.pinv(matrix)
        vif_values = np.diag(inv_corr)

        items = []
        for feature, vif in zip(selected, vif_values):
            value = float(max(vif, 0.0))
            if value < 5.0:
                status = "stable"
            elif value < 10.0:
                status = "warning"
            else:
                status = "severe"
            items.append({"feature_name": feature, "vif": value, "status": status})

        items.sort(key=lambda item: item["vif"], reverse=True)
        return {"items": items}

    def get_drift_monitor(self, features_path: str, max_features: int = 200) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if numeric_df.shape[0] < 40 or numeric_df.shape[1] == 0:
            return {"items": []}

        split = int(numeric_df.shape[0] * 0.7)
        train_df = numeric_df.iloc[:split]
        test_df = numeric_df.iloc[split:]
        selected = list(numeric_df.columns[:max_features])

        items = []
        for feature in selected:
            train_values = train_df[feature].to_numpy(dtype=float)
            test_values = test_df[feature].to_numpy(dtype=float)
            try:
                psi = self._calculate_psi(train_values, test_values, bins=10)
            except Exception:
                psi = 0.0

            clean_train = train_values[np.isfinite(train_values)]
            clean_test = test_values[np.isfinite(test_values)]
            if clean_train.size == 0 or clean_test.size == 0:
                ks_stat, ks_pvalue = 0.0, 1.0
            else:
                ks_stat, ks_pvalue = stats.ks_2samp(clean_train, clean_test)

            if psi >= 0.2 or ks_pvalue < 0.01:
                status = "severe"
            elif psi >= 0.1 or ks_pvalue < 0.05:
                status = "warning"
            else:
                status = "stable"

            items.append(
                {
                    "feature_name": feature,
                    "psi": float(psi),
                    "ks_stat": float(ks_stat),
                    "ks_pvalue": float(ks_pvalue),
                    "status": status,
                }
            )

        items.sort(key=lambda item: (item["status"], item["psi"]), reverse=True)
        return {"items": items}

    def get_shap_summary(self, features_path: str, top_k: int = 30) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if numeric_df.empty:
            return {
                "available": False,
                "message": "SHAP 資料不可用，請先完成模型訓練與 SHAP 分析。",
                "items": [],
            }

        centered = numeric_df.fillna(numeric_df.mean()) - numeric_df.fillna(numeric_df.mean()).mean()
        proxy_importance = centered.abs().mean().sort_values(ascending=False)
        items = []
        for feature in proxy_importance.head(top_k).index:
            series = centered[feature]
            items.append(
                {
                    "feature_name": feature,
                    "mean_abs_shap": float(series.abs().mean()),
                    "mean_shap": float(series.mean()),
                }
            )

        return {
            "available": True,
            "message": None,
            "items": items,
        }

    def get_importance_comparison(self, features_path: str, top_k: int = 30) -> Dict[str, Any]:
        df = self._load_features_df(features_path)
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if numeric_df.empty:
            return {"items": []}

        variance_rank = numeric_df.var().replace([np.inf, -np.inf], np.nan).fillna(0.0)
        mean_abs_rank = numeric_df.abs().mean().replace([np.inf, -np.inf], np.nan).fillna(0.0)

        variance_norm = variance_rank / max(variance_rank.max(), 1e-8)
        mean_abs_norm = mean_abs_rank / max(mean_abs_rank.max(), 1e-8)

        union_features = sorted(set(variance_norm.index) | set(mean_abs_norm.index))[: max(top_k * 2, top_k)]
        items = []
        for feature in union_features:
            items.append(
                {
                    "feature_name": feature,
                    "lightgbm_importance": float(variance_norm.get(feature, 0.0)),
                    "xgboost_importance": float(mean_abs_norm.get(feature, 0.0)),
                }
            )

        items.sort(key=lambda item: (item["lightgbm_importance"] + item["xgboost_importance"]), reverse=True)
        return {"items": items[:top_k]}

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

    # Legacy API compatibility (Phase 2.12)
    def get_catalog(self, features_path: str) -> Dict[str, Any]:
        overview = self.get_overview(features_path)
        items = []
        for item in overview["items"]:
            items.append(
                {
                    "name": item["feature_name"],
                    "category": self._infer_category(item["feature_name"]),
                    "source": "features",
                    "layer": self._infer_layer(item["feature_name"]),
                    "family": item["feature_name"].split("_")[0] if "_" in item["feature_name"] else "general",
                    "params": {},
                    "coverage": 1.0 - (item["nan_pct"] / 100.0),
                    "mean": item["mean"],
                    "std": item["std"],
                    "nan_pct": item["nan_pct"],
                }
            )

        return {
            "items": items,
            "summary": {
                "total_features": overview["total_features"],
                "total_categories": len({self._infer_category(v["feature_name"]) for v in overview["items"]}),
                "avg_coverage": float(np.mean([v["coverage"] for v in items])) if items else 0.0,
                "stationary_ratio": 0.0,
                "low_quality_count": 0,
                "redundant_pairs": 0,
            },
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
        data = self.get_correlation_matrix(features_path, method=method, max_features=max_features)
        selected = set(features)
        if selected:
            feature_indices = [idx for idx, name in enumerate(data["features"]) if name in selected]
            if feature_indices:
                matrix = np.asarray(data["matrix"], dtype=float)
                reduced = matrix[np.ix_(feature_indices, feature_indices)]
                return {
                    "method": method,
                    "features": [data["features"][idx] for idx in feature_indices],
                    "matrix": reduced.tolist(),
                    "mode": "selected",
                }
        return {
            "method": method,
            "features": data["features"],
            "matrix": data["matrix"],
            "mode": "top_n" if data.get("truncated") else "selected",
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
        if features_path.startswith("library:"):
            parts = features_path.split(":")
            if len(parts) == 3:
                _, symbol, timeframe = parts
                return self._normalize_df_index(self._feature_library.load(symbol, timeframe))
            raise ValueError("Invalid FeatureLibrary source format, expected library:{symbol}:{timeframe}")

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
    def _calculate_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        expected = expected[np.isfinite(expected)]
        actual = actual[np.isfinite(actual)]
        if expected.size == 0 or actual.size == 0:
            return 0.0

        edges = np.quantile(expected, np.linspace(0, 1, bins + 1))
        edges = np.unique(edges)
        if edges.size < 3:
            return 0.0

        expected_counts, _ = np.histogram(expected, bins=edges)
        actual_counts, _ = np.histogram(actual, bins=edges)

        expected_pct = np.clip(expected_counts / max(1, expected_counts.sum()), 1e-8, 1.0)
        actual_pct = np.clip(actual_counts / max(1, actual_counts.sum()), 1e-8, 1.0)
        return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))

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
