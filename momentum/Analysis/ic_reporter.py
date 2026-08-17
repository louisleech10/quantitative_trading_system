"""IC report generation utilities."""

from __future__ import annotations

import json
import csv
from io import StringIO
from datetime import datetime
import math
from pathlib import Path
from typing import Any, Mapping, Optional

import h5py
import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)

# OOS 宣稱關鍵字（degraded 出口禁出現未降級文案）
_OOS_CLAIM_MARKERS = (
    "oos-passed",
    "oos_passed",
    "oos guarantee",
    "out-of-sample passed",
    "out_of_sample_passed",
    "ok_oos",
)


class DegradedOOSViolation(Exception):
    """degraded 報表被當 OOS 消費、或缺少 research-only 標記時 raise。

    LA-1 B3：全 8 gate 共用此唯一 exception（禁 return-False 雙軌）。
    """


def _is_degraded(report: Mapping[str, Any] | None) -> bool:
    """兩值 fail-closed：僅字面 ``ok_oos`` 視為 OOS；缺失/未知/其餘一律 degraded。

    LA-1 B3-ENUM-01：禁 default ok_oos。
    """
    if not isinstance(report, Mapping):
        return True
    return report.get("analysis_status") != "ok_oos"


def normalize_analysis_status(raw: Any) -> str:
    """將任意 status 正規化為兩值契約（fail-closed）。

    僅字面 ``ok_oos`` 保留；``None``/空/未知 → ``degraded_full_sample``。
    """
    if raw == "ok_oos":
        return "ok_oos"
    if raw == "degraded_full_sample":
        return "degraded_full_sample"
    # research_only 等別名、未知字串、None → degraded
    if raw in {"research_only", "degraded", "full_sample"}:
        return "degraded_full_sample"
    if isinstance(raw, str) and raw.strip() and raw != "ok_oos":
        # 未知非空字串仍不當 OOS；統一 degraded 契約值
        return "degraded_full_sample"
    return "degraded_full_sample"


def gate_summary_table_pass_class(report: Mapping[str, Any]) -> None:
    """Oracle ①：degraded 時 summary_table 每列 pass_class != \"oos\"。"""
    if not _is_degraded(report):
        return
    rows = report.get("summary_table") or []
    if not isinstance(rows, list):
        raise DegradedOOSViolation("summary_table missing under degraded")
    if not rows:
        return
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise DegradedOOSViolation(f"summary_table[{i}] not object")
        pc = row.get("pass_class")
        if pc is None or pc == "oos":
            raise DegradedOOSViolation(
                f"summary_table[{i}] pass_class={pc!r} (need research-only marker)"
            )


def gate_filter_log_output_features(report: Mapping[str, Any]) -> None:
    """Oracle ②：degraded 時 filter_log.stage5_thresholds.output_features 附 pass_class。"""
    if not _is_degraded(report):
        return
    fl = report.get("filter_log") or {}
    if not isinstance(fl, dict):
        raise DegradedOOSViolation("filter_log missing under degraded")
    s5 = fl.get("stage5_thresholds") or {}
    if not isinstance(s5, dict):
        raise DegradedOOSViolation("stage5_thresholds missing under degraded")
    of = s5.get("output_features")
    marker = None
    if isinstance(of, dict):
        marker = of.get("pass_class")
    elif of is None:
        marker = s5.get("pass_class")
    if marker is None or marker == "oos":
        raise DegradedOOSViolation(
            f"stage5_thresholds.output_features pass_class={marker!r}"
        )


def gate_hdf5_analysis_status_attr(
    path: str | Path,
    *,
    expect_degraded: bool = True,
) -> None:
    """Oracle ③：filtered HDF5 必須有 analysis_status attr。"""
    p = Path(path)
    if not p.is_file():
        raise DegradedOOSViolation(f"HDF5 missing: {p}")
    with h5py.File(p, "r") as handle:
        status = None
        if "analysis_status" in handle.attrs:
            status = handle.attrs["analysis_status"]
        elif "filtered" in handle and "analysis_status" in handle["filtered"].attrs:
            status = handle["filtered"].attrs["analysis_status"]
        else:
            # 掃 group attrs
            for key in handle.keys():
                grp = handle[key]
                if hasattr(grp, "attrs") and "analysis_status" in grp.attrs:
                    status = grp.attrs["analysis_status"]
                    break
    if status is None:
        raise DegradedOOSViolation(f"HDF5 missing analysis_status attr: {p}")
    status_s = status.decode() if isinstance(status, (bytes, bytearray)) else str(status)
    if expect_degraded and status_s == "ok_oos":
        raise DegradedOOSViolation(
            f"HDF5 analysis_status claims ok_oos under degraded: {status_s}"
        )
    if expect_degraded and status_s not in {"degraded_full_sample", "research_only"}:
        # 允許 research-only 別名；主契約 = degraded_full_sample
        if status_s != "degraded_full_sample":
            raise DegradedOOSViolation(
                f"HDF5 analysis_status unexpected under degraded: {status_s!r}"
            )


def gate_ai_json_oos_text(
    ai_payload: Mapping[str, Any],
    report: Mapping[str, Any] | None = None,
) -> None:
    """Oracle ④：degraded 時 AI JSON 禁 OOS 宣稱、必 research-only 標。"""
    degraded = _is_degraded(report) if report is not None else (
        ai_payload.get("analysis_status") == "degraded_full_sample"
        or ai_payload.get("oos_guarantees") is False
        or ai_payload.get("research_only") is True
    )
    # 呼叫端在 degraded report 上必須驗
    if report is not None and not _is_degraded(report):
        return
    if report is not None and _is_degraded(report):
        degraded = True
    if not degraded:
        return

    if ai_payload.get("research_only") is not True and ai_payload.get(
        "analysis_status"
    ) not in {"degraded_full_sample", "research_only"}:
        raise DegradedOOSViolation("ai_json missing research-only / degraded marker")

    top = ai_payload.get("top_features") or []
    if isinstance(top, list):
        for i, item in enumerate(top):
            if not isinstance(item, dict):
                continue
            pc = item.get("pass_class")
            if pc == "oos":
                raise DegradedOOSViolation(f"ai_json top_features[{i}] pass_class=oos")
            # degraded 時若有 features 應標 research-only
            if pc is None and top:
                raise DegradedOOSViolation(
                    f"ai_json top_features[{i}] missing pass_class under degraded"
                )

    blob = json.dumps(ai_payload, ensure_ascii=False).lower()
    for marker in _OOS_CLAIM_MARKERS:
        if marker in blob and "research" not in blob:
            raise DegradedOOSViolation(f"ai_json OOS claim without research-only: {marker}")
    # 明確 ok_oos 字樣在 degraded 下禁止
    if '"analysis_status": "ok_oos"' in blob or '"analysis_status":"ok_oos"' in blob:
        raise DegradedOOSViolation("ai_json claims analysis_status=ok_oos under degraded")


def gate_api_csv_carrier(
    *,
    headers: Mapping[str, str] | None,
    body: str,
    report: Mapping[str, Any] | None = None,
    expect_degraded: bool = True,
) -> None:
    """Oracle ⑤ CSV：HTTP header X-Analysis-Status + 檔首註解行。"""
    if report is not None and not _is_degraded(report) and not expect_degraded:
        return
    if not expect_degraded and report is not None and not _is_degraded(report):
        return
    headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    status_hdr = headers.get("x-analysis-status")
    if not status_hdr:
        raise DegradedOOSViolation("CSV missing X-Analysis-Status header")
    if expect_degraded and status_hdr == "ok_oos":
        raise DegradedOOSViolation("CSV header claims ok_oos under degraded")
    first_line = (body or "").splitlines()[0] if body else ""
    if not first_line.lstrip().startswith("#"):
        raise DegradedOOSViolation("CSV missing leading comment marker line")
    if "analysis_status" not in first_line and status_hdr not in first_line:
        raise DegradedOOSViolation("CSV comment line missing analysis_status")


def gate_api_transforms_carrier(
    response: Mapping[str, Any],
    *,
    hdf5_path: str | Path | None = None,
    expect_degraded: bool = True,
) -> None:
    """Oracle ⑤ transforms：response.analysis_status + 輸出 HDF5 attr。"""
    status = response.get("analysis_status") if isinstance(response, Mapping) else None
    if status is None:
        raise DegradedOOSViolation("ApplyTransformsResponse missing analysis_status")
    if expect_degraded and status == "ok_oos":
        raise DegradedOOSViolation("transforms response claims ok_oos under degraded")
    path = hdf5_path or (response.get("output_path") if isinstance(response, Mapping) else None)
    if path:
        gate_hdf5_analysis_status_attr(path, expect_degraded=expect_degraded)


def gate_task_payload_status(payload: Mapping[str, Any]) -> None:
    """task completion / result payload 必含 root 紅標。"""
    if not isinstance(payload, Mapping):
        raise DegradedOOSViolation("task payload not object")
    # payload 可能是 report 本體或包一層 result
    report = payload.get("result") if "result" in payload and isinstance(
        payload.get("result"), Mapping
    ) else payload
    if not isinstance(report, Mapping):
        raise DegradedOOSViolation("task payload missing report")
    # completion callback 可能把紅標放在 payload 根（B3-TASK-01）
    if "analysis_status" not in report and "analysis_status" in payload:
        report = payload
    if "analysis_status" not in report:
        raise DegradedOOSViolation("task payload missing analysis_status")
    if "oos_guarantees" not in report and "oos_guarantees" not in payload:
        raise DegradedOOSViolation("task payload missing oos_guarantees")


def assert_filtered_export_fresh(
    result: Mapping[str, Any] | None,
    export_path: str | Path,
) -> Path:
    """B3-H5-01：export 前驗當次 run freshness；stale / 空 filtered → raise FileNotFoundError。

    當次 run 未寫出 filtered（空結果）或 HDF5 的 source_generated_at 與 report
    對不上時，拒絕回傳 stable-path 上可能殘留的上一輪檔案。
    """
    path = Path(export_path)
    if not isinstance(result, Mapping):
        raise FileNotFoundError("Filtered features not found: missing result")
    meta = result.get("metadata") if isinstance(result.get("metadata"), Mapping) else {}
    written = meta.get("filtered_features_written")
    if written is False:
        raise FileNotFoundError(
            "Filtered features empty for this run; refuse stale stable-path export"
        )
    expected_gen = meta.get("filtered_generated_at") or result.get("generated_at")
    if not expected_gen:
        raise FileNotFoundError(
            "Filtered features provenance missing; refuse unstamped export"
        )
    if not path.is_file():
        raise FileNotFoundError(f"Filtered features not found: {path}")
    with h5py.File(path, "r") as handle:
        file_gen = None
        if "source_generated_at" in handle.attrs:
            file_gen = handle.attrs["source_generated_at"]
        elif "filtered" in handle and "source_generated_at" in handle["filtered"].attrs:
            file_gen = handle["filtered"].attrs["source_generated_at"]
    if isinstance(file_gen, (bytes, bytearray)):
        file_gen = file_gen.decode()
    if file_gen is None or str(file_gen) != str(expected_gen):
        raise FileNotFoundError(
            "Filtered features stale relative to this run "
            f"(file={file_gen!r} expected={expected_gen!r})"
        )
    expected_task = meta.get("filtered_source_task_id")
    if expected_task is not None:
        with h5py.File(path, "r") as handle:
            file_tid = None
            if "source_task_id" in handle.attrs:
                file_tid = handle.attrs["source_task_id"]
            elif "filtered" in handle and "source_task_id" in handle["filtered"].attrs:
                file_tid = handle["filtered"].attrs["source_task_id"]
        if isinstance(file_tid, (bytes, bytearray)):
            file_tid = file_tid.decode()
        if file_tid is None or str(file_tid) != str(expected_task):
            raise FileNotFoundError(
                "Filtered features task_id mismatch "
                f"(file={file_tid!r} expected={expected_task!r})"
            )
    return path


class ICReporter:
    """Stage 7: 報告生成 — JSON + Markdown + HDF5 輸出。"""

    def __init__(self, config: dict):
        self._config = config or {}

    def generate_json_report(self, analysis_results: dict, metadata: dict) -> dict:
        """生成完整 JSON 報告。"""

        rolling_series = self._sample_rolling_series(
            analysis_results.get("rolling_ic_series", {})
        )

        meta = self._sanitize_metadata_for_json(metadata or {})
        summary_table = self._sanitize_summary_table_for_json(
            analysis_results.get("summary_table", [])
        )

        report = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "metadata": meta,
            "filter_log": analysis_results.get("filter_log", {}),
            "summary_table": summary_table,
            "ic_decay": analysis_results.get("ic_decay", {}),
            "quantile_returns": self._flatten_quantile_returns(
                analysis_results.get("quantile_returns", {})
            ),
            "grouped_ic": analysis_results.get("grouped_ic", {}),
            "correlation_matrix": analysis_results.get("correlation_matrix", {}),
            "diversification_metrics": analysis_results.get(
                "diversification_metrics", {}
            ),
            "rolling_ic_series": rolling_series,
            "turnover_analysis": analysis_results.get("turnover_analysis", {}),
            "coverage_analysis": analysis_results.get("coverage_analysis", {}),
            "cross_sectional_symbol_ic": analysis_results.get("cross_sectional_symbol_ic", {}),
            "cross_symbol_validation": analysis_results.get("cross_symbol_validation", {}),
        }

        deep_report = analysis_results.get("deep_analysis_report")
        deep_enabled = bool(analysis_results.get("deep_analysis_enabled", False))
        if deep_enabled and deep_report is not None:
            self._append_deep_analysis_fields(report, deep_report)

        # ICHC Task 2.1：契約 validator 唯一邊界（下游出口讀已驗證 report，不各自再驗）
        from momentum.Analysis.ic_config_schema import (
            validate_report_against_contract,
        )

        validate_report_against_contract(report)
        return report

    @staticmethod
    def _flatten_quantile_returns(qr_tree: Any) -> dict:
        """ICHC Task 2.1：per-feature 巢狀 payload 攤平為契約形狀（數值不變）。

        映射（SPEC 定死）：內層 quantile_returns.* 全鍵上提 feature 根層；
        long_short.spread→long_short_spread（內層已有同名鍵者以內層為準）；
        monotonicity_score 留根層；不丟鍵。status 物件與已扁平 payload 原樣通過。
        """
        if not isinstance(qr_tree, dict):
            return {}
        flat: dict = {}
        for feature, node in qr_tree.items():
            if not isinstance(node, dict):
                flat[feature] = node
                continue
            inner = node.get("quantile_returns")
            if not isinstance(inner, dict):
                flat[feature] = node  # 已扁平（或 status 物件）：原樣
                continue
            payload = dict(inner)
            if "monotonicity_score" in node:
                payload["monotonicity_score"] = node["monotonicity_score"]
            long_short = node.get("long_short")
            if isinstance(long_short, dict):
                payload.setdefault("long_short_spread", long_short.get("spread"))
                payload.setdefault("long_short_tstat", long_short.get("tstat"))
            flat[feature] = payload
        return flat

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
        # F2: envelope unwrap + sanitizer + flat module map(讀 results.factor_returns)
        deep_payload = self._prepare_deep_payload(report, deep_report)

        # 既有欄名/順序 byte 不變；t_stat / p_value_adj 僅追加於末尾（Task 2.4）
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
            "t_stat",
            "p_value_adj",
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
            "cost_drag_return",
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
                # 舊欄 p_value：保留 raw float（含 NaN→csv 寫成 "nan"），
                # 禁經 _jsonable_scalar 以免 byte 從 "nan" 變空欄（Task 2.4 硬規格）
                "p_value": item.get("p_value"),
                # 新欄：JSON/下游可 null；CSV 允許 None→空欄（舊 baseline 無此欄）
                "t_stat": self._jsonable_scalar(item.get("t_stat")),
                "p_value_adj": self._jsonable_scalar(item.get("p_value_adj")),
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

        # F2: envelope unwrap + sanitizer;factor_returns detailed 經 unwrap features
        deep_payload = self._prepare_deep_payload(report, None)
        module_alias = {
            "factor_return": "factor_returns",
            "factor_centrality": "factor_centrality",
            "trend": "trend_analysis",
            "rolling": "rolling_oos",
            "long_short": "long_short_analysis",
            "quality": "feature_quality_diagnostics",
            # 短名 net_ic 已廢(B-strict);僅允許完整模組鍵 net_ic_analysis
            "net_ic_analysis": "net_ic_analysis",
        }
        resolved_module = module_alias.get(module_name, module_name)
        module_data = deep_payload.get(resolved_module) if isinstance(deep_payload, dict) else None
        if module_data is None:
            raise ValueError(f"module not found: {module_name}")

        # ok §U → flatten features map;unavailable 仍 flatten union 佔位
        if resolved_module == "factor_returns":
            unwrapped = self._unwrap_factor_returns(module_data)
            if unwrapped is not None:
                module_data = unwrapped

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
        """生成 AI 可讀 JSON。

        LA-1 B3：degraded 時 OOS 文案 fail-closed（research-only 標，禁冒充 OOS）。
        """

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
        # F2: envelope unwrap + sanitizer(ok 放行 / legacy 擋)
        deep_payload = self._prepare_deep_payload(report, deep_report)

        # B3-ENUM-01：讀取點 fail-closed — 非字面 ok_oos 一律 degraded
        if isinstance(report, dict):
            analysis_status = normalize_analysis_status(report.get("analysis_status"))
            oos_guarantees = report.get("oos_guarantees")
            degraded = _is_degraded(report)
        else:
            analysis_status = "degraded_full_sample"
            oos_guarantees = False
            degraded = True
        pass_class = (
            "full_sample_research_only" if degraded else "oos"
        )
        if degraded:
            risk_warnings = list(risk_warnings or [])
            risk_warnings.insert(
                0,
                "RESEARCH-ONLY: full-sample fallback — not OOS-validated; "
                "do not treat top_features as out-of-sample passed.",
            )

        payload = {
            "version": report.get("version", "1.0") if isinstance(report, dict) else "1.0",
            "generated_at": (
                report.get("generated_at", datetime.utcnow().isoformat())
                if isinstance(report, dict)
                else datetime.utcnow().isoformat()
            ),
            "analysis_status": analysis_status,
            "oos_guarantees": (
                bool(oos_guarantees) if oos_guarantees is not None else (not degraded)
            ),
            "research_only": bool(degraded),
            "interpretation_guide": {
                "ic_mean": "IC 均值，越大代表預測能力越強",
                "icir": "IC 資訊比率，建議 > 0.5",
                "p_value": "統計顯著性，建議 < 0.05",
                "long_short_spread": "分位數多空價差，越大越好",
                **(
                    {
                        "pass_class": "full_sample_research_only 表示非 OOS 保證，僅研究用途",
                    }
                    if degraded
                    else {}
                ),
            },
            "top_features": [
                {
                    "rank": item.get("rank"),
                    "feature_name": item.get("feature_name"),
                    "ic_mean": item.get("ic_mean"),
                    "icir": item.get("icir"),
                    "p_value": item.get("p_value"),
                    "pass_class": item.get("pass_class") or pass_class,
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
        # F2: envelope unwrap + sanitizer(ok 放行 / legacy 擋)
        deep_payload = self._prepare_deep_payload(report, deep_report)

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

        # LA-2 B3：root ok_oos + factor loud → fail-closed deny
        if isinstance(report, dict):
            from momentum.core.contracts import deny_factor_in_ok_oos

            deny_factor_in_ok_oos(report)

        # F2: export_all raw dump sanitizer(ok 放行 / legacy 擋)
        from momentum.Analysis.factor_return_sanitizer import sanitize_factor_returns

        safe_report = (
            sanitize_factor_returns(report) if isinstance(report, dict) else report
        )

        json_path = output_path / f"ic_report_{case_id}.json"
        ai_json_path = output_path / f"ic_ai_{case_id}.json"
        csv_summary_path = output_path / f"ic_summary_{case_id}.csv"
        markdown_path = output_path / f"ic_report_{case_id}.md"

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(safe_report, file, ensure_ascii=True, separators=(",", ":"))

        with ai_json_path.open("w", encoding="utf-8") as file:
            json.dump(self.generate_ai_json(safe_report), file, ensure_ascii=False, indent=2)

        csv_summary_path.write_text(self.generate_summary_csv(safe_report), encoding="utf-8")
        markdown_path.write_text(self.generate_enhanced_markdown(safe_report), encoding="utf-8")

        exports: dict[str, str] = {
            "json": str(json_path),
            "ai_json": str(ai_json_path),
            "csv_summary": str(csv_summary_path),
            "markdown": str(markdown_path),
        }

        deep_payload = self._resolve_deep_report(safe_report)
        for module_name in deep_payload.keys():
            if module_name in {"deep_analysis_errors", "module_statuses", "deep_analysis_summary"}:
                continue
            detailed_path = output_path / f"ic_{module_name}_{case_id}.csv"
            detailed_path.write_text(
                self.generate_detailed_csv(safe_report, module_name),
                encoding="utf-8",
            )
            exports[f"csv_detailed_{module_name}"] = str(detailed_path)

        return exports

    def save_filtered_features(
        self,
        features_df: pd.DataFrame,
        selected_features: list[str],
        output_path: str,
        analysis_status: Optional[str] = None,
        oos_guarantees: Optional[bool] = None,
        source_generated_at: Optional[str] = None,
        source_task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """儲存精選特徵矩陣至 HDF5。

        LA-1 B3：寫 analysis_status / oos_guarantees attr（oracle ③ carrier）。
        B3-H5-01：寫 source_generated_at / source_task_id 供 export freshness 對帳。
        """

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
            if analysis_status is not None:
                status_s = str(analysis_status)
                group.attrs["analysis_status"] = status_s
                file.attrs["analysis_status"] = status_s
            if oos_guarantees is not None:
                group.attrs["oos_guarantees"] = bool(oos_guarantees)
                file.attrs["oos_guarantees"] = bool(oos_guarantees)
            if source_generated_at is not None:
                gen_s = str(source_generated_at)
                group.attrs["source_generated_at"] = gen_s
                file.attrs["source_generated_at"] = gen_s
            if source_task_id is not None:
                tid_s = str(source_task_id)
                group.attrs["source_task_id"] = tid_s
                file.attrs["source_task_id"] = tid_s

        logger.info("Filtered features saved: %s", path)
        return str(path)

    def save_report(self, report: dict, output_dir: str, case_id: str) -> dict[str, str]:
        """持久化所有報告產出。

        F2: 落檔前 sanitizer(ok §U 放行;legacy 裸 map 擋)。
        LA-2 B3：root ok_oos + factor loud → deny。
        """

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if isinstance(report, dict):
            from momentum.core.contracts import deny_factor_in_ok_oos

            deny_factor_in_ok_oos(report)

        from momentum.Analysis.factor_return_sanitizer import sanitize_factor_returns

        safe_report = (
            sanitize_factor_returns(report) if isinstance(report, dict) else report
        )

        json_path = output_path / f"ic_report_{case_id}.json"
        markdown_path = output_path / f"ic_summary_{case_id}.md"

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(safe_report, file, ensure_ascii=True, separators=(",", ":"))

        if self._config.get("ai_summary", True):
            summary = self.generate_ai_summary(safe_report)
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

    @staticmethod
    def _jsonable_scalar(value: Any) -> Any:
        """非有限 float（NaN/inf）→ None（JSON null）。"""
        if value is None:
            return None
        try:
            if isinstance(value, (float, np.floating, int, np.integer)):
                fv = float(value)
                if not math.isfinite(fv):
                    return None
                return fv
        except (TypeError, ValueError):
            return value
        return value

    def _sanitize_summary_table_for_json(self, summary_table: Any) -> list:
        """summary 列中 t_stat/p_value/p_value_adj 的 NaN → null。"""
        if not isinstance(summary_table, list):
            return []
        sanitized: list = []
        for item in summary_table:
            if not isinstance(item, dict):
                sanitized.append(item)
                continue
            row = dict(item)
            for key in ("p_value", "t_stat", "p_value_adj"):
                if key in row:
                    row[key] = self._jsonable_scalar(row.get(key))
            sanitized.append(row)
        return sanitized

    def _sanitize_metadata_for_json(self, metadata: dict) -> dict:
        """確保 significance 節存在時結構完整；scalar NaN → null。"""
        meta = dict(metadata or {})
        significance = meta.get("significance")
        if isinstance(significance, dict):
            sig = dict(significance)
            fdr = sig.get("fdr")
            if isinstance(fdr, dict):
                fdr_clean = dict(fdr)
                if "alpha_effective" in fdr_clean:
                    fdr_clean["alpha_effective"] = self._jsonable_scalar(
                        fdr_clean.get("alpha_effective")
                    )
                sig["fdr"] = fdr_clean
            if "maxlags" in sig:
                sig["maxlags"] = self._jsonable_scalar(sig.get("maxlags"))
            if "n_tests" in sig:
                n_tests = sig.get("n_tests")
                sig["n_tests"] = int(n_tests) if n_tests is not None else 0
            meta["significance"] = sig
        return meta

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

    def _unwrap_factor_returns(self, payload: Any) -> dict[str, Any] | None:
        """§U ok union → ``value.features``;reporter 全出口統一 unwrap。

        M-unwrap:若不呼叫此法而直接讀頂層,summary 三欄必 null。
        """
        from momentum.Analysis.factor_return_sanitizer import unwrap_factor_returns_features

        return unwrap_factor_returns_features(payload)

    def _flatten_deep_envelope(self, deep_payload: Any) -> dict[str, Any]:
        """API/service envelope ``{results, module_summary}`` → flat module map.

        export 常傳 envelope 作 deep_report;消費者(summary/AI/MD)讀頂層
        ``factor_returns``,必須先定位 ``results.factor_returns``。
        已是 flat(頂層含 module 鍵)則原樣回傳。
        """
        if not isinstance(deep_payload, dict):
            return {}
        results = deep_payload.get("results")
        if not isinstance(results, dict):
            return deep_payload
        # envelope: 有 module_summary / counts,或頂層尚無 module 鍵
        is_envelope = (
            "module_summary" in deep_payload
            or "completed_count" in deep_payload
            or "module_statuses" in deep_payload
            or (
                "factor_returns" not in deep_payload
                and any(
                    k in results
                    for k in (
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
                    )
                )
            )
        )
        if is_envelope:
            return dict(results)
        return deep_payload

    def _prepare_deep_payload(
        self, report: dict | None, deep_report: dict | None = None
    ) -> dict[str, Any]:
        """統一 deep 出口前處理:sanitize → envelope flatten。

        順序:先 sanitize(對齊 module_summary/statuses)再 flatten
        (消費者只讀 flat module map)。
        """
        from momentum.Analysis.factor_return_sanitizer import sanitize_factor_returns

        if deep_report is not None:
            deep_payload: Any = deep_report
        else:
            deep_payload = self._resolve_deep_report(report if isinstance(report, dict) else {})
        if not isinstance(deep_payload, dict):
            return {}
        cleaned = sanitize_factor_returns(deep_payload)
        if not isinstance(cleaned, dict):
            return {}
        return self._flatten_deep_envelope(cleaned)

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
        # F2: 必經 _unwrap_factor_returns 讀 .value.features(M-unwrap 護網)
        fr_features = self._unwrap_factor_returns(deep_payload.get("factor_returns"))
        return {
            "factor_return_ls_mean": self._safe_nested(
                fr_features, feature_name, "long_short_mean_return"
            ),
            "factor_return_sharpe": self._safe_nested(
                self._safe_nested(fr_features, feature_name, "risk_metrics"),
                None,
                "sharpe_ratio",
            ),
            "factor_return_max_drawdown": self._safe_nested(
                self._safe_nested(fr_features, feature_name, "risk_metrics"),
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
            "cost_drag_return": self._safe_nested(
                self._safe_nested(deep_payload.get("net_ic_analysis"), "features", feature_name),
                None,
                "cost_drag_return",
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
            # F2: factor_returns unavailable → 無有限 meta;ok → unwrap features 摘要
            if key == "factor_returns" and value.get("status") == "unavailable":
                summaries[key] = {
                    "status": "unavailable",
                    "reason": value.get("reason"),
                }
                continue
            if key == "factor_returns" and value.get("status") == "ok":
                features = self._unwrap_factor_returns(value) or {}
                summaries[key] = {
                    "status": "ok",
                    "keys": list(features.keys())[:5],
                    "size": len(features),
                }
                continue
            if "summary" in value and isinstance(value["summary"], dict):
                summaries[key] = value["summary"]
            else:
                summaries[key] = {"keys": list(value.keys())[:5], "size": len(value)}
            # D-4：factor_exposure 附帶 factor_attribution 子狀態（可讀）
            if key == "factor_exposure":
                fa = value.get("factor_attribution")
                if not isinstance(fa, dict):
                    payload = value.get("payload")
                    summary_node = None
                    if isinstance(payload, dict):
                        summary_node = payload.get("summary")
                    elif payload is not None and hasattr(payload, "summary"):
                        summary_node = getattr(payload, "summary", None)
                    if isinstance(summary_node, dict):
                        fa = summary_node.get("factor_attribution")
                if isinstance(fa, dict) and "status" in fa:
                    base = summaries[key]
                    if not isinstance(base, dict):
                        base = {"value": base}
                        summaries[key] = base
                    else:
                        base = dict(base)
                        summaries[key] = base
                    base["factor_attribution"] = {
                        "status": fa.get("status"),
                        "value": fa.get("value"),
                        "reason": fa.get("reason"),
                    }
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

        # F2: inject/serialize 出口 sanitizer(ok 放行 / legacy 擋)
        from momentum.Analysis.factor_return_sanitizer import sanitize_factor_returns

        return sanitize_factor_returns(output)
