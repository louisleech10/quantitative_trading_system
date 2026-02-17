"""IC report generation utilities."""

from __future__ import annotations

import json
from datetime import datetime
import math
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class ICReporter:
    """Stage 7: 報告生成 — JSON + Markdown + HDF5 輸出。"""

    def __init__(self, config: dict):
        self._config = config or {}

    def generate_json_report(self, analysis_results: dict, metadata: dict) -> dict:
        """生成完整 JSON 報告。"""

        rolling_series = self._sample_rolling_series(
            analysis_results.get("rolling_ic_series", {})
        )

        report = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "filter_log": analysis_results.get("filter_log", {}),
            "summary_table": analysis_results.get("summary_table", []),
            "ic_decay": analysis_results.get("ic_decay", {}),
            "quantile_returns": analysis_results.get("quantile_returns", {}),
            "grouped_ic": analysis_results.get("grouped_ic", {}),
            "correlation_matrix": analysis_results.get("correlation_matrix", {}),
            "diversification_metrics": analysis_results.get(
                "diversification_metrics", {}
            ),
            "rolling_ic_series": rolling_series,
            "turnover_analysis": analysis_results.get("turnover_analysis", {}),
            "coverage_analysis": analysis_results.get("coverage_analysis", {}),
        }

        deep_report = analysis_results.get("deep_analysis_report")
        deep_enabled = bool(analysis_results.get("deep_analysis_enabled", False))
        if deep_enabled and deep_report is not None:
            self._append_deep_analysis_fields(report, deep_report)

        return report

    def inject_deep_analysis(self, report: dict, deep_report: Any) -> dict:
        """在既有 report 上注入深度分析欄位（保持向後相容）。"""

        base = dict(report or {})
        self._append_deep_analysis_fields(base, deep_report)
        return base

    def generate_ai_summary(self, report: dict) -> str:
        """生成 AI 可讀 Markdown 摘要。"""

        summary_table = report.get("summary_table", [])
        top_features = sorted(
            summary_table,
            key=lambda item: item.get("icir", float("-inf")),
            reverse=True,
        )[:5]

        lines = [
            "# IC Gatekeeper Summary",
            "",
            "## Key Findings",
        ]
        if top_features:
            for item in top_features:
                lines.append(
                    f"- {item.get('feature_name')}: ICIR={item.get('icir')}, IC Mean={item.get('ic_mean')}"
                )
        else:
            lines.append("- No features passed the filter.")

        lines.extend(
            [
                "",
                "## Regime Analysis",
                "- Regime statistics available in grouped_ic section.",
                "",
                "## Recommendations",
                "- Review thresholds if too few features passed.",
                "",
                "## Risk Warnings",
                "- Event sample size may reduce statistical confidence.",
            ]
        )
        return "\n".join(lines)

    def save_filtered_features(
        self,
        features_df: pd.DataFrame,
        selected_features: list[str],
        output_path: str,
    ) -> str:
        """儲存精選特徵矩陣至 HDF5。"""

        if features_df is None or features_df.empty:
            raise ValueError("features_df is empty")
        if not selected_features:
            raise ValueError("selected_features is empty")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = features_df[selected_features].to_numpy(dtype=np.float32)
        timestamps = self._extract_timestamps(features_df)

        with h5py.File(path, "w") as file:
            group = file.create_group("filtered")
            group.create_dataset("features", data=data, compression="gzip")
            group.create_dataset("timestamps", data=timestamps, compression="gzip")
            str_dtype = h5py.string_dtype(encoding="utf-8")
            group.create_dataset(
                "feature_names",
                data=np.array(selected_features, dtype=object),
                dtype=str_dtype,
            )
            group.attrs["feature_count"] = len(selected_features)

        logger.info("Filtered features saved: %s", path)
        return str(path)

    def save_report(self, report: dict, output_dir: str, case_id: str) -> dict[str, str]:
        """持久化所有報告產出。"""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        json_path = output_path / f"ic_report_{case_id}.json"
        markdown_path = output_path / f"ic_summary_{case_id}.md"

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=True, separators=(",", ":"))

        if self._config.get("ai_summary", True):
            summary = self.generate_ai_summary(report)
            with markdown_path.open("w", encoding="utf-8") as file:
                file.write(summary)

        logger.info("IC report saved: %s", json_path)
        return {"json": str(json_path), "markdown": str(markdown_path)}

    def save_filter_log(self, filter_log: dict, output_dir: str, case_id: str) -> str:
        """儲存篩選日誌 JSON。"""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        log_path = output_path / f"ic_filter_log_{case_id}.json"
        with log_path.open("w", encoding="utf-8") as file:
            json.dump(filter_log, file, ensure_ascii=True, indent=2)
        return str(log_path)

    def generate_filter_log(self, stage_results: dict) -> dict:
        """生成篩選日誌。"""

        log = {}
        for stage, result in (stage_results or {}).items():
            if result is None:
                continue
            log[stage] = result
        return log

    def _extract_timestamps(self, features_df: pd.DataFrame) -> np.ndarray:
        if isinstance(features_df.index, pd.DatetimeIndex):
            return features_df.index.view("int64")
        if features_df.index.name == "timestamp":
            return features_df.index.to_numpy(dtype=np.int64)
        if "timestamp" in features_df.columns:
            return features_df["timestamp"].to_numpy(dtype=np.int64)
        return np.arange(len(features_df), dtype=np.int64)

    def _sample_rolling_series(self, rolling_series: dict) -> dict:
        if not isinstance(rolling_series, dict):
            return rolling_series

        max_points = int(self._config.get("max_series_points", 1000))
        if max_points <= 0:
            return rolling_series

        sampled: dict = {}
        for feature, windows in rolling_series.items():
            if not isinstance(windows, dict):
                sampled[feature] = windows
                continue
            sampled_windows: dict = {}
            for window_key, values in windows.items():
                if not isinstance(values, list) or len(values) <= max_points:
                    sampled_windows[window_key] = values
                    continue
                step = max(1, int(math.ceil(len(values) / max_points)))
                sampled_windows[window_key] = values[::step]
            sampled[feature] = sampled_windows

        return sampled

    def _append_deep_analysis_fields(self, report: dict, deep_report: Any) -> None:
        serialized = self._serialize_deep_analysis(deep_report)
        report.update(serialized)

    def _serialize_deep_analysis(self, deep_report: Any) -> dict:
        data = deep_report
        if hasattr(deep_report, "__dict__"):
            data = deep_report.__dict__

        results = data.get("results", {}) if isinstance(data, dict) else {}
        errors = data.get("deep_analysis_errors", []) if isinstance(data, dict) else []
        summary = data.get("module_summary", {}) if isinstance(data, dict) else {}

        serialized_errors = []
        for item in errors:
            if isinstance(item, dict):
                serialized_errors.append(item)
            elif hasattr(item, "__dict__"):
                serialized_errors.append(dict(item.__dict__))

        output = {
            "deep_analysis_enabled": True,
            "deep_analysis_version": "0.1",
            "deep_analysis_errors": serialized_errors,
            "module_statuses": [
                {"module_name": module_name, "status": status}
                for module_name, status in summary.items()
            ],
            "deep_analysis_summary": {
                "total": int(data.get("total_modules", 10)) if isinstance(data, dict) else 10,
                "completed": int(data.get("completed_count", 0)) if isinstance(data, dict) else 0,
                "skipped": int(data.get("skipped_count", 0)) if isinstance(data, dict) else 0,
                "failed": int(data.get("failed_count", 0)) if isinstance(data, dict) else 0,
            },
        }

        module_to_report_key = {
            "factor_returns": "factor_returns",
            "factor_centrality": "factor_centrality",
            "trend_analysis": "trend_analysis",
            "parameter_sensitivity": "parameter_sensitivity",
            "rolling_oos": "rolling_oos",
            "factor_orthogonalization": "factor_orthogonalization",
            "factor_exposure": "factor_exposure",
            "long_short_analysis": "long_short_analysis",
            "feature_quality_diagnostics": "feature_quality_diagnostics",
            "net_ic_analysis": "net_ic_analysis",
        }
        for module_name, key in module_to_report_key.items():
            if isinstance(results, dict) and module_name in results:
                output[key] = results[module_name]

        return output
