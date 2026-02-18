from __future__ import annotations

import json

import numpy as np

from momentum.Analysis.analysis_exporter import AnalysisExporter, ExportFormat


def _sample_payload() -> dict:
    return {
        "engine": "lightgbm",
        "performance": {
            "auc": 0.62,
            "accuracy": 0.59,
            "nan_metric": np.nan,
        },
        "feature_importance": [
            {"feature_name": "f1", "importance": 0.9, "rank": 1},
            {"feature_name": "f2", "importance": 0.7, "rank": 2},
        ],
        "enhancement": {
            "calibration": {"status": "completed", "ece_before": 0.08, "ece_after": 0.03},
            "walk_forward": {"status": "skipped", "reason": "insufficient_data"},
        },
        "comparison": {"winner": "lightgbm"},
        "optimization": {"best_value": 0.35, "best_params": {"learning_rate": 0.03}},
    }


def test_export_model_performance_json_envelope():
    exporter = AnalysisExporter()
    output = exporter.export_model_performance(_sample_payload(), ExportFormat.JSON, "task-1")

    assert isinstance(output, dict)
    assert output["schema_version"] == "1.0"
    assert output["scope"] == "performance"
    assert output["model_id"] == "task-1"


def test_export_feature_importance_csv_contains_header_and_rows():
    exporter = AnalysisExporter()
    output = exporter.export_feature_importance(_sample_payload(), ExportFormat.CSV, "task-1")

    assert isinstance(output, str)
    assert "feature_name" in output
    assert "importance" in output
    assert "f1" in output


def test_export_enhancement_markdown_contains_scope_and_sections():
    exporter = AnalysisExporter()
    output = exporter.export_enhancement_results(_sample_payload(), ExportFormat.MARKDOWN, "task-1")

    assert isinstance(output, str)
    assert "Export Report" in output
    assert "enhancement" in output.lower()


def test_export_full_report_json_contains_all_sections():
    exporter = AnalysisExporter()
    output = exporter.export_full_research_report(_sample_payload(), ExportFormat.JSON, "task-1")

    assert isinstance(output, dict)
    assert output["scope"] == "full"
    assert "performance" in output
    assert "feature_importance" in output
    assert "enhancement" in output


def test_export_by_scope_supports_calibration():
    exporter = AnalysisExporter()
    output = exporter.export_by_scope(_sample_payload(), "calibration", ExportFormat.JSON, "task-1")

    assert isinstance(output, dict)
    assert output["scope"] == "calibration"
    assert output["records"][0]["status"] == "completed"


def test_sanitize_nan_and_numpy_types_to_json_serializable():
    exporter = AnalysisExporter()
    output = exporter.export_model_performance(_sample_payload(), ExportFormat.JSON, "task-1")

    text = json.dumps(output, ensure_ascii=False)
    assert "nan_metric" in text
    assert '"nan_metric": null' in text


def test_export_by_scope_accepts_string_format_json():
    exporter = AnalysisExporter()
    output = exporter.export_by_scope(_sample_payload(), "performance", "json", "task-1")

    assert isinstance(output, dict)
    assert output["scope"] == "performance"
