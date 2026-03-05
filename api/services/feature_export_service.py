"""Feature export service for structured JSON and Markdown reports."""

from __future__ import annotations

from html import escape
from itertools import combinations
from math import isfinite
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from api.core.logging import get_logger


logger = get_logger("api.feature_export_service")


class FeatureExportService:
    """Build AI-friendly export payloads from feature DataFrame."""

    LEVEL_CATEGORY_MAP = {
        "L1_basic": ["trend", "momentum", "volatility", "volume"],
        "L2_intermediate": ["statistics", "cycle", "pattern", "tail_risk"],
        "L3_advanced": ["microstructure", "entropy"],
    }

    def build_json_report(
        self,
        task_id: str,
        features_df: pd.DataFrame,
        export_meta: Dict[str, Any],
        include_sample_data: bool,
        sample_rows: int,
        include_statistics: bool,
        include_correlation_top_k: int,
    ) -> Dict[str, Any]:
        metadata = self._build_metadata(task_id, features_df, export_meta)
        catalog = self._build_feature_catalog(features_df, export_meta)
        statistics = self._build_statistics(features_df, include_statistics)
        sample_data = self._build_sample_data(features_df, sample_rows) if include_sample_data else {
            "columns": [],
            "rows": [],
        }
        quality_alerts = self._build_quality_alerts(features_df)
        hotspots = self._build_correlation_hotspots(features_df, include_correlation_top_k)

        return {
            "version": "1.0",
            "type": "feature_factory_report",
            "metadata": metadata,
            "feature_catalog": catalog,
            "statistics": statistics,
            "sample_data": sample_data,
            "quality_alerts": quality_alerts,
            "correlation_hotspots": hotspots,
        }

    def build_markdown_report(
        self,
        task_id: str,
        features_df: pd.DataFrame,
        export_meta: Dict[str, Any],
        max_token_budget: int,
        sections: Optional[List[str]],
        language: str,
    ) -> str:
        report_data = self.build_json_report(
            task_id=task_id,
            features_df=features_df,
            export_meta=export_meta,
            include_sample_data=True,
            sample_rows=5,
            include_statistics=True,
            include_correlation_top_k=10,
        )

        selected_sections = self._normalize_sections(sections)
        markdown = self._build_markdown(
            report_data=report_data,
            max_tokens=max_token_budget,
            sections=selected_sections,
            language=language,
        )
        return markdown

    def _build_metadata(self, task_id: str, features_df: pd.DataFrame, export_meta: Dict[str, Any]) -> Dict[str, Any]:
        metadata = export_meta.get("metadata") or {}
        config_used = metadata.get("config_used") or {}
        atomic = config_used.get("atomic_indicators") or {}
        preprocessing = config_used.get("preprocessing") or {}

        engines_enabled = [name for name, cfg in atomic.items() if isinstance(cfg, dict) and cfg.get("enabled")]

        return {
            "task_id": task_id,
            "symbol": export_meta.get("symbol"),
            "timeframe": export_meta.get("timeframe"),
            "generated_at": export_meta.get("generated_at"),
            "total_features": int(features_df.shape[1]),
            "total_rows": int(features_df.shape[0]),
            "generation_time_seconds": float(export_meta.get("generation_time") or 0.0),
            "config_hash": metadata.get("config_hash"),
            "engines_enabled": engines_enabled,
            "preprocessing_enabled": bool(preprocessing.get("enabled", False)),
            "preprocessing_mode": preprocessing.get("mode", "append"),
        }

    def _build_feature_catalog(self, features_df: pd.DataFrame, export_meta: Dict[str, Any]) -> Dict[str, Any]:
        categories: Dict[str, List[str]] = {}
        for column in features_df.columns:
            category = self._infer_category(column)
            categories.setdefault(category, []).append(column)

        by_category = {
            category: {"count": len(features), "features": features}
            for category, features in categories.items()
        }

        by_level = {}
        for level, level_categories in self.LEVEL_CATEGORY_MAP.items():
            count = sum(len(categories.get(category, [])) for category in level_categories)
            by_level[level] = {
                "count": count,
                "categories": level_categories,
            }

        metadata = export_meta.get("metadata") or {}
        layer_counts = metadata.get("layer_counts") or export_meta.get("layer_counts") or {}
        by_layer = {
            "layer1_atomic": int(layer_counts.get("layer1", 0)),
            "layer2_derived": int(layer_counts.get("layer2", 0)),
            "layer3_rolling": int(layer_counts.get("layer3", 0)),
            "layer4_lag": int(layer_counts.get("layer4", 0)),
            "layer5_cross_sectional": int(layer_counts.get("layer5", 0)),
            "layer6_meta": int(layer_counts.get("layer6", 0)),
            "layer6_5_preprocessing": int(layer_counts.get("layer6_5", 0)),
        }

        return {
            "by_category": by_category,
            "by_level": by_level,
            "by_layer": by_layer,
        }

    def _build_statistics(self, features_df: pd.DataFrame, include_statistics: bool) -> Dict[str, Any]:
        _EMPTY_SUMMARY = {
            "summary": {
                "nan_ratio_mean": 0.0,
                "nan_ratio_max": 0.0,
                "inf_count": 0,
                "constant_features": 0,
                "high_correlation_pairs": 0,
            },
            "per_feature": [],
        }
        if not include_statistics or features_df.empty:
            return _EMPTY_SUMMARY

        import warnings
        nan_ratios = features_df.isna().mean()
        numeric_df = features_df.select_dtypes(include=[np.number])
        inf_count = int(np.isinf(numeric_df.to_numpy()).sum()) if not numeric_df.empty else 0
        constant_features = int((numeric_df.nunique(dropna=True) <= 1).sum()) if not numeric_df.empty else 0

        # Skip full correlation matrix for large datasets (O(N²) memory + time).
        # Returns None when skipped so callers can show "not computed" instead of misleading 0.
        HIGH_CORR_COL_LIMIT = 500
        high_corr_pairs: Optional[int] = None
        if numeric_df.shape[1] >= 2 and numeric_df.shape[1] <= HIGH_CORR_COL_LIMIT:
            corr_df = numeric_df.corr().abs()
            upper = corr_df.where(np.triu(np.ones(corr_df.shape), k=1).astype(bool))
            high_corr_pairs = int((upper > 0.95).sum().sum())

        # Vectorized per-feature stats — one pass per operation instead of per-column loop.
        # describe/skew/kurt are C-level vectorized; the subsequent loop only builds dicts.
        per_feature: List[Dict[str, Any]] = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            desc = features_df.describe(percentiles=[]).T  # count/mean/std/min/max
            skewness_s = features_df.skew()
            kurtosis_s = features_df.kurt()
        for column in features_df.columns:
            category = self._infer_category(column)
            level = self._infer_level(category)
            col_desc = desc.loc[column] if column in desc.index else {}
            per_feature.append({
                "name": column,
                "category": category,
                "level": level,
                "layer": self._infer_layer(column),
                "dtype": str(features_df[column].dtype),
                "nan_ratio": self._safe_float(nan_ratios.get(column, 0.0)),
                "mean": self._safe_float(col_desc.get("mean")),
                "std": self._safe_float(col_desc.get("std")),
                "min": self._safe_float(col_desc.get("min")),
                "max": self._safe_float(col_desc.get("max")),
                "skewness": self._safe_float(skewness_s.get(column)),
                "kurtosis": self._safe_float(kurtosis_s.get(column)),
                "description": f"{category} feature: {column}",
            })

        return {
            "summary": {
                "nan_ratio_mean": float(nan_ratios.mean()) if len(nan_ratios) else 0.0,
                "nan_ratio_max": float(nan_ratios.max()) if len(nan_ratios) else 0.0,
                "inf_count": inf_count,
                "constant_features": constant_features,
                "high_correlation_pairs": high_corr_pairs,
            },
            "per_feature": per_feature,
        }

    def _build_sample_data(self, features_df: pd.DataFrame, sample_rows: int) -> Dict[str, Any]:
        sampled = features_df.head(sample_rows)
        sampled = sampled.reset_index()

        columns = [str(column) for column in sampled.columns]
        rows: List[List[Any]] = []
        for _, row in sampled.iterrows():
            values: List[Any] = []
            for value in row.tolist():
                if isinstance(value, pd.Timestamp):
                    values.append(value.isoformat())
                elif isinstance(value, np.generic):
                    values.append(value.item())
                elif isinstance(value, float):
                    values.append(None if not isfinite(value) else value)
                else:
                    values.append(value)
            rows.append(values)

        return {
            "columns": columns,
            "rows": rows,
        }

    def _build_quality_alerts(self, features_df: pd.DataFrame) -> List[Dict[str, Any]]:
        MAX_ALERTS = 100
        alerts: List[Dict[str, Any]] = []

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            nan_ratios = features_df.isna().mean()
            unique_counts = features_df.nunique(dropna=True)

        # NaN ratio alerts — vectorized, capped
        for col, ratio in nan_ratios[nan_ratios > 0.1].head(MAX_ALERTS).items():
            alerts.append({
                "severity": "warning",
                "feature": col,
                "message": f"NaN ratio {float(ratio):.2%} exceeds 10% threshold",
            })

        # Constant feature alerts — vectorized, capped
        for col in unique_counts[unique_counts <= 1].head(MAX_ALERTS).index:
            alerts.append({
                "severity": "warning",
                "feature": col,
                "message": "Constant feature detected",
            })

        # Warmup detection — only columns with any NaN, capped at 50 to avoid large loops
        for col in nan_ratios[nan_ratios > 0].index[:50]:
            warmup_rows = int(features_df[col].isna().cumprod().sum())
            if warmup_rows > 0:
                alerts.append({
                    "severity": "info",
                    "feature": col,
                    "message": f"Warmup detected: first {warmup_rows} rows are NaN",
                })

        return alerts[:MAX_ALERTS]

    def _build_correlation_hotspots(self, features_df: pd.DataFrame, top_k: int) -> List[Dict[str, Any]]:
        if top_k <= 0:
            return []

        numeric_df = features_df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return []

        limit_cols = min(numeric_df.shape[1], 200)
        if numeric_df.shape[1] > limit_cols:
            variances = numeric_df.var().sort_values(ascending=False)
            selected_columns = list(variances.index[:limit_cols])
            numeric_df = numeric_df[selected_columns]
            logger.info(
                "Correlation hotspot columns limited from %s to %s for performance",
                features_df.shape[1],
                limit_cols,
            )

        corr_df = numeric_df.corr()
        pairs = []
        for left, right in combinations(corr_df.columns, 2):
            corr = corr_df.loc[left, right]
            if pd.isna(corr):
                continue
            pairs.append((left, right, float(corr)))

        pairs.sort(key=lambda item: abs(item[2]), reverse=True)

        hotspots = []
        for left, right, corr in pairs[:top_k]:
            hotspots.append(
                {
                    "feature_a": left,
                    "feature_b": right,
                    "correlation": corr,
                }
            )
        return hotspots

    @staticmethod
    def _normalize_sections(sections: Optional[List[str]]) -> Optional[set[str]]:
        if not sections:
            return None
        normalized = {section.strip().lower() for section in sections if section and section.strip()}
        return normalized or None

    def _build_markdown(
        self,
        report_data: Dict[str, Any],
        max_tokens: int,
        sections: Optional[set[str]],
        language: str,
    ) -> str:
        blocks: List[str] = []
        remaining = max_tokens

        all_sections = [
            ("header", self._md_header),
            ("catalog", self._md_catalog),
            ("quality", self._md_quality),
            ("top_features", self._md_top_features),
            ("sample", self._md_sample),
        ]

        for key, builder in all_sections:
            if sections and key not in sections:
                continue
            text = builder(report_data, language)
            tokens = self._estimate_tokens(text)
            if key in {"header", "catalog", "quality"}:
                if remaining - tokens < 0:
                    continue
                blocks.append(text)
                remaining -= tokens
                continue

            if remaining <= 0:
                continue
            if tokens <= remaining:
                blocks.append(text)
                remaining -= tokens

        if not blocks:
            blocks.append(self._md_header(report_data, language))

        return "\n\n".join(blocks)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        ascii_chars = sum(1 for ch in text if ord(ch) < 128)
        non_ascii = len(text) - ascii_chars
        return (ascii_chars // 4) + (non_ascii // 2)

    def _md_header(self, report_data: Dict[str, Any], language: str) -> str:
        metadata = report_data.get("metadata", {})
        title = (
            f"# Feature Factory Report: {escape(str(metadata.get('symbol', 'N/A')))} {escape(str(metadata.get('timeframe', 'N/A')))}"
            if language.lower() == "en"
            else f"# Feature Factory 報告：{escape(str(metadata.get('symbol', 'N/A')))} {escape(str(metadata.get('timeframe', 'N/A')))}"
        )
        summary = (
            f"> Generated: {escape(str(metadata.get('generated_at', 'N/A')))} | Features: {metadata.get('total_features', 0)} | Rows: {metadata.get('total_rows', 0)}"
        )
        return f"{title}\n\n{summary}"

    def _md_catalog(self, report_data: Dict[str, Any], language: str) -> str:
        catalog = report_data.get("feature_catalog", {}).get("by_category", {})
        header = "## Feature Catalog" if language.lower() == "en" else "## 特徵目錄"
        lines = [header, "", "| Category | Count |", "|---|---:|"]
        for category, detail in catalog.items():
            lines.append(f"| {escape(str(category))} | {int(detail.get('count', 0))} |")
        return "\n".join(lines)

    def _md_quality(self, report_data: Dict[str, Any], language: str) -> str:
        summary = report_data.get("statistics", {}).get("summary", {})
        header = "## Quality Summary" if language.lower() == "en" else "## 品質摘要"
        lines = [
            header,
            "",
            f"- NaN 平均比例: {summary.get('nan_ratio_mean', 0.0):.2%}",
            f"- 常量特徵: {summary.get('constant_features', 0)}",
            "- 高相關特徵對: " + (
                str(summary['high_correlation_pairs'])
                if summary.get('high_correlation_pairs') is not None
                else "未計算（特徵數 > 500 時跳過，避免 O(N²) 記憶體消耗）"
            ),
        ]
        return "\n".join(lines)

    def _md_top_features(self, report_data: Dict[str, Any], language: str) -> str:
        features = report_data.get("statistics", {}).get("per_feature", [])
        features_sorted = sorted(features, key=lambda item: abs(item.get("std") or 0.0), reverse=True)[:20]
        header = "## Top Features by Variation" if language.lower() == "en" else "## 變異度最高特徵"
        lines = [header, "", "| Feature | Category | Std | Skew | Kurt |", "|---|---|---:|---:|---:|"]
        for feature in features_sorted:
            lines.append(
                "| {name} | {category} | {std:.6f} | {skew:.6f} | {kurt:.6f} |".format(
                    name=escape(str(feature.get("name", ""))),
                    category=escape(str(feature.get("category", ""))),
                    std=float(feature.get("std") or 0.0),
                    skew=float(feature.get("skewness") or 0.0),
                    kurt=float(feature.get("kurtosis") or 0.0),
                )
            )
        return "\n".join(lines)

    def _md_sample(self, report_data: Dict[str, Any], language: str) -> str:
        sample = report_data.get("sample_data", {})
        columns = sample.get("columns", [])
        rows = sample.get("rows", [])
        if not columns:
            return "## Sample Data\n\nN/A"

        header = "## Sample Data" if language.lower() == "en" else "## 樣本數據"
        lines = [header, "", "| " + " | ".join(escape(str(col)) for col in columns[:8]) + " |"]
        lines.append("|" + "---|" * min(len(columns), 8))
        for row in rows[:5]:
            lines.append("| " + " | ".join(escape(str(item)) for item in row[:8]) + " |")
        return "\n".join(lines)

    def _infer_category(self, feature_name: str) -> str:
        if feature_name.startswith("ms_"):
            return "microstructure"
        if feature_name.startswith("ent_"):
            return "entropy"
        if feature_name.startswith("tr_"):
            return "tail_risk"
        if feature_name.startswith("close_trend_") or feature_name.startswith("volume_trend_"):
            return "trend"
        if "_momentum_" in feature_name:
            return "momentum"
        if "_volatility_" in feature_name:
            return "volatility"
        if "_volume_" in feature_name:
            return "volume"
        if "_cycle_" in feature_name:
            return "cycle"
        if "_pattern_" in feature_name:
            return "pattern"
        if "_stats_" in feature_name or "_stat_" in feature_name:
            return "statistics"
        if feature_name.startswith("meta_"):
            return "meta"
        return "other"

    def _infer_level(self, category: str) -> str:
        for level, categories in self.LEVEL_CATEGORY_MAP.items():
            if category in categories:
                return level
        return "L1_basic"

    @staticmethod
    def _infer_layer(feature_name: str) -> str:
        if feature_name.endswith("_rank") or "_zscore_" in feature_name or feature_name.endswith("_gaussian"):
            return "layer6_5"
        if feature_name.startswith("meta_"):
            return "layer6"
        if "_lag" in feature_name:
            return "layer4"
        return "layer1"

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(number):
            return None
        return number
