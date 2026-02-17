"""IC report generation utilities."""

from __future__ import annotations

import json
import csv
from io import StringIO
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

    def generate_summary_csv(self, report: dict, deep_report: dict | None = None) -> str:
        """生成 Summary CSV（UTF-8 with BOM）。"""

        summary_table = report.get("summary_table", []) if isinstance(report, dict) else []
        deep_payload = deep_report or self._resolve_deep_report(report)

        base_columns = [
            "rank",
            "feature_name",
            "ic_mean",
            "icir",
            "p_value",
            "ic_hit_rate",
            "monotonicity_score",
            "coverage",
            "turnover_rate",
            "half_life",
            "decay_rate",
            "decay_type",
            "long_short_spread",
            "max_correlation",
        ]
        deep_columns = [
            "factor_return_ls_mean",
            "factor_return_sharpe",
            "factor_return_max_drawdown",
            "centrality_score",
            "crowded",
            "trend_recommendation",
            "oos_mean_ic",
            "oos_assessment",
            "orthogonal_residual_ratio",
            "exposure_hhi",
            "quality_stationary",
            "net_ic",
        ]

        enable_deep = bool(deep_payload)
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=base_columns + (deep_columns if enable_deep else []),
            extrasaction="ignore",
        )
        writer.writeheader()

        for item in summary_table:
            feature_name = item.get("feature_name")
            row = {
                "rank": item.get("rank"),
                "feature_name": feature_name,
                "ic_mean": item.get("ic_mean"),
                "icir": item.get("icir"),
                "p_value": item.get("p_value"),
                "ic_hit_rate": item.get("ic_hit_rate"),
                "monotonicity_score": item.get("monotonicity_score"),
                "coverage": item.get("coverage"),
                "turnover_rate": item.get("turnover_rate"),
                "half_life": self._safe_nested(report.get("ic_decay"), feature_name, "half_life"),
                "decay_rate": self._safe_nested(report.get("ic_decay"), feature_name, "decay_rate"),
                "decay_type": self._safe_nested(report.get("ic_decay"), feature_name, "decay_type"),
                "long_short_spread": self._safe_nested(
                    report.get("quantile_returns"), feature_name, "long_short_spread"
                ),
                "max_correlation": self._max_correlation(report.get("correlation_matrix"), feature_name),
            }

            if enable_deep:
                row.update(self._build_deep_summary_columns(feature_name, deep_payload))

            writer.writerow(row)

        return f"\ufeff{output.getvalue()}"

    def generate_detailed_csv(self, report: dict, module_name: str) -> str:
        """生成指定模組的 Detailed CSV（UTF-8 with BOM）。"""

        if not module_name:
            raise ValueError("module_name is required")

        deep_payload = self._resolve_deep_report(report)
        module_alias = {
            "factor_return": "factor_returns",
            "factor_centrality": "factor_centrality",
            "trend": "trend_analysis",
            "rolling": "rolling_oos",
            "long_short": "long_short_analysis",
            "quality": "feature_quality_diagnostics",
            "net_ic": "net_ic_analysis",
        }
        resolved_module = module_alias.get(module_name, module_name)
        module_data = deep_payload.get(resolved_module)
        if module_data is None:
            raise ValueError(f"module not found: {module_name}")

        rows = self._flatten_module_rows(resolved_module, module_data)
        headers = sorted({key for row in rows for key in row.keys()})
        if not headers:
            headers = ["module", "message"]
            rows = [{"module": module_name, "message": "no_data"}]

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

        return f"\ufeff{output.getvalue()}"

    def generate_ai_json(self, report: dict, deep_report: dict | None = None) -> dict:
        """生成 AI 可讀 JSON。"""

        summary_table = report.get("summary_table", []) if isinstance(report, dict) else []
        top_n = int(self._config.get("ai_json_top_n", 30))
        top_features = sorted(
            summary_table,
            key=lambda item: item.get("icir", float("-inf")),
            reverse=True,
        )[:top_n]

        key_findings = self._generate_key_findings(top_features)
        risk_warnings = self._generate_risk_warnings(report, top_features)
        recommendations = self._generate_recommendations(risk_warnings)
        deep_payload = deep_report or self._resolve_deep_report(report)

        payload = {
            "version": report.get("version", "1.0"),
            "generated_at": report.get("generated_at", datetime.utcnow().isoformat()),
            "interpretation_guide": {
                "ic_mean": "IC 均值，越大代表預測能力越強",
                "icir": "IC 資訊比率，建議 > 0.5",
                "p_value": "統計顯著性，建議 < 0.05",
                "long_short_spread": "分位數多空價差，越大越好",
            },
            "top_features": [
                {
                    "rank": item.get("rank"),
                    "feature_name": item.get("feature_name"),
                    "ic_mean": item.get("ic_mean"),
                    "icir": item.get("icir"),
                    "p_value": item.get("p_value"),
                }
                for item in top_features
            ],
            "key_findings": key_findings,
            "risk_warnings": risk_warnings,
            "recommendations": recommendations,
            "module_summaries": self._build_module_summaries(deep_payload),
        }

        return payload

    def generate_enhanced_markdown(self, report: dict, deep_report: dict | None = None) -> str:
        """生成 Enhanced Markdown 報告。"""

        summary_table = report.get("summary_table", []) if isinstance(report, dict) else []
        top_features = sorted(
            summary_table,
            key=lambda item: item.get("icir", float("-inf")),
            reverse=True,
        )[:10]
        deep_payload = deep_report or self._resolve_deep_report(report)

        lines = [
            "# IC Gatekeep Enhanced Report",
            "",
            "## Top 10 Features",
            "",
            "| Rank | Feature | IC Mean | ICIR | P-Value |",
            "|---:|---|---:|---:|---:|",
        ]

        for item in top_features:
            lines.append(
                f"| {item.get('rank', '-') } | {item.get('feature_name', '-') } | "
                f"{self._fmt(item.get('ic_mean'))} | {self._fmt(item.get('icir'))} | {self._fmt(item.get('p_value'))} |"
            )

        lines.extend(["", "## 風險警告"])
        for warning in self._generate_risk_warnings(report, top_features):
            lines.append(f"- {warning}")

        lines.extend(["", "## 建議行動"])
        for suggestion in self._generate_recommendations(self._generate_risk_warnings(report, top_features)):
            lines.append(f"- {suggestion}")

        lines.extend(["", "## 深度分析摘要"])
        module_summaries = self._build_module_summaries(deep_payload)
        if not module_summaries:
            lines.append("- 未啟用深度分析")
        else:
            for key, value in module_summaries.items():
                lines.append(f"- {key}: {value}")

        lines.extend(["", "## 篩選漏斗"])
        for stage, stage_data in (report.get("filter_log") or {}).items():
            lines.append(
                f"- {stage}: input={stage_data.get('input', '-')}, output={stage_data.get('output', '-')}"
            )

        return "\n".join(lines)

    def export_all(self, report: dict, output_dir: str, case_id: str) -> dict[str, str]:
        """一次匯出 JSON / AI-JSON / CSV / Markdown。"""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        json_path = output_path / f"ic_report_{case_id}.json"
        ai_json_path = output_path / f"ic_ai_{case_id}.json"
        csv_summary_path = output_path / f"ic_summary_{case_id}.csv"
        markdown_path = output_path / f"ic_report_{case_id}.md"

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=True, separators=(",", ":"))

        with ai_json_path.open("w", encoding="utf-8") as file:
            json.dump(self.generate_ai_json(report), file, ensure_ascii=False, indent=2)

        csv_summary_path.write_text(self.generate_summary_csv(report), encoding="utf-8")
        markdown_path.write_text(self.generate_enhanced_markdown(report), encoding="utf-8")

        exports: dict[str, str] = {
            "json": str(json_path),
            "ai_json": str(ai_json_path),
            "csv_summary": str(csv_summary_path),
            "markdown": str(markdown_path),
        }

        deep_payload = self._resolve_deep_report(report)
        for module_name in deep_payload.keys():
            if module_name in {"deep_analysis_errors", "module_statuses", "deep_analysis_summary"}:
                continue
            detailed_path = output_path / f"ic_{module_name}_{case_id}.csv"
            detailed_path.write_text(
                self.generate_detailed_csv(report, module_name),
                encoding="utf-8",
            )
            exports[f"csv_detailed_{module_name}"] = str(detailed_path)

        return exports

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

    def _safe_nested(self, payload: Any, key: str | None, field: str) -> Any:
        if not isinstance(payload, dict):
            return None

        value = payload if key is None else payload.get(key)
        if not isinstance(value, dict):
            return None
        return value.get(field)

    def _max_correlation(self, correlation_matrix: Any, feature_name: str | None) -> float | None:
        if not feature_name or not isinstance(correlation_matrix, dict):
            return None
        features = correlation_matrix.get("features")
        matrix = correlation_matrix.get("matrix")
        if not isinstance(features, list) or not isinstance(matrix, list):
            return None

        try:
            index = features.index(feature_name)
        except ValueError:
            return None

        row = matrix[index] if index < len(matrix) else None
        if not isinstance(row, list):
            return None

        values = [abs(float(item)) for i, item in enumerate(row) if i != index]
        return max(values) if values else None

    def _resolve_deep_report(self, report: dict) -> dict:
        if not isinstance(report, dict):
            return {}

        deep_report = report.get("deep_analysis_report")
        if isinstance(deep_report, dict):
            results = deep_report.get("results")
            return results if isinstance(results, dict) else deep_report

        candidates = [
            "factor_returns",
            "factor_centrality",
            "trend_analysis",
            "parameter_sensitivity",
            "rolling_oos",
            "factor_orthogonalization",
            "factor_exposure",
            "long_short_analysis",
            "feature_quality_diagnostics",
            "net_ic_analysis",
        ]
        payload: dict[str, Any] = {}
        for key in candidates:
            if key in report:
                payload[key] = report[key]
        return payload

    def _build_deep_summary_columns(self, feature_name: str | None, deep_payload: dict) -> dict[str, Any]:
        return {
            "factor_return_ls_mean": self._safe_nested(deep_payload.get("factor_returns"), feature_name, "long_short_mean_return"),
            "factor_return_sharpe": self._safe_nested(
                self._safe_nested(deep_payload.get("factor_returns"), feature_name, "risk_metrics"),
                None,
                "sharpe",
            ),
            "factor_return_max_drawdown": self._safe_nested(
                self._safe_nested(deep_payload.get("factor_returns"), feature_name, "risk_metrics"),
                None,
                "max_drawdown",
            ),
            "centrality_score": self._safe_nested(
                self._safe_nested(deep_payload.get("factor_centrality"), "features", feature_name),
                None,
                "centrality",
            ),
            "crowded": self._safe_nested(
                self._safe_nested(deep_payload.get("factor_centrality"), "features", feature_name),
                None,
                "crowded",
            ),
            "trend_recommendation": self._safe_nested(
                self._safe_nested(deep_payload.get("trend_analysis"), feature_name, "combined_signal"),
                None,
                "recommendation",
            ),
            "oos_mean_ic": self._safe_nested(
                self._safe_nested(
                    self._safe_nested(deep_payload.get("rolling_oos"), "features", feature_name),
                    None,
                    "oos_stability",
                ),
                None,
                "mean_oos_ic",
            ),
            "oos_assessment": self._safe_nested(
                self._safe_nested(deep_payload.get("rolling_oos"), "features", feature_name),
                None,
                "assessment",
            ),
            "orthogonal_residual_ratio": self._safe_nested(
                deep_payload.get("factor_orthogonalization"),
                "residual_variance_ratio",
                feature_name or "",
            ),
            "exposure_hhi": self._safe_nested(deep_payload.get("factor_exposure"), "concentration", "hhi"),
            "quality_stationary": self._safe_nested(
                self._safe_nested(deep_payload.get("feature_quality_diagnostics"), "adf_results", feature_name),
                None,
                "is_stationary",
            ),
            "net_ic": self._safe_nested(
                self._safe_nested(deep_payload.get("net_ic_analysis"), "features", feature_name),
                None,
                "net_ic",
            ),
        }

    def _flatten_module_rows(self, module_name: str, module_data: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        def walk(prefix: dict[str, Any], data: Any) -> None:
            if isinstance(data, dict):
                simple_items = {key: value for key, value in data.items() if not isinstance(value, (dict, list))}
                nested_items = {key: value for key, value in data.items() if isinstance(value, (dict, list))}

                if simple_items:
                    rows.append({"module": module_name, **prefix, **simple_items})

                for key, value in nested_items.items():
                    walk({**prefix, "path": key}, value)
                return

            if isinstance(data, list):
                for idx, item in enumerate(data):
                    walk({**prefix, "index": idx}, item)
                return

            rows.append({"module": module_name, **prefix, "value": data})

        walk({}, module_data)
        return rows

    def _generate_key_findings(self, top_features: list[dict[str, Any]]) -> list[str]:
        if not top_features:
            return ["目前沒有通過篩選的因子。"]

        findings: list[str] = []
        best = top_features[0]
        findings.append(
            f"最佳因子 {best.get('feature_name')}，ICIR={self._fmt(best.get('icir'))}，IC Mean={self._fmt(best.get('ic_mean'))}。"
        )

        significant = [item for item in top_features if (item.get("p_value") is not None and item.get("p_value") < 0.05)]
        findings.append(f"前 {len(top_features)} 個因子中，顯著因子數量為 {len(significant)}。")
        return findings

    def _generate_risk_warnings(self, report: dict, top_features: list[dict[str, Any]]) -> list[str]:
        warnings: list[str] = []
        if not top_features:
            warnings.append("無可用因子，建議放寬門檻或檢查數據品質。")
            return warnings

        weak = [item for item in top_features if item.get("icir") is not None and item.get("icir") < 0.3]
        if weak:
            warnings.append("部分高排名因子 ICIR 偏低，可能存在穩定性風險。")

        high_corr = 0.0
        for item in top_features:
            corr = self._max_correlation(report.get("correlation_matrix"), item.get("feature_name"))
            if corr is not None:
                high_corr = max(high_corr, float(corr))
        if high_corr >= 0.9:
            warnings.append("因子之間相關性偏高，需注意冗餘風險。")

        return warnings or ["未檢測到顯著風險警示。"]

    def _generate_recommendations(self, warnings: list[str]) -> list[str]:
        recommendations = ["優先追蹤 Top 因子於 OOS 的穩定性。"]
        warning_text = " ".join(warnings)
        if "相關性" in warning_text:
            recommendations.append("可透過正交化或去冗餘策略降低共線性。")
        if "ICIR" in warning_text:
            recommendations.append("考慮提高 ICIR 門檻或調整特徵工程參數。")
        return recommendations

    def _build_module_summaries(self, deep_payload: dict) -> dict[str, Any]:
        if not deep_payload:
            return {}

        summaries: dict[str, Any] = {}
        for key, value in deep_payload.items():
            if not isinstance(value, dict):
                continue
            if "summary" in value and isinstance(value["summary"], dict):
                summaries[key] = value["summary"]
            else:
                summaries[key] = {"keys": list(value.keys())[:5], "size": len(value)}
        return summaries

    def _fmt(self, value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:.6f}"
        return str(value)

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
