from momentum.Analysis.deep_analysis_types import DeepAnalysisReport, SkippedResult
from momentum.Analysis.ic_reporter import ICReporter


def test_generate_json_report_without_deep_analysis_keeps_backward_compatibility():
    reporter = ICReporter(config={})
    report = reporter.generate_json_report(analysis_results={}, metadata={})

    assert "summary_table" in report
    assert "deep_analysis_enabled" not in report
    assert "factor_returns" not in report


def test_inject_deep_analysis_serializes_required_keys():
    reporter = ICReporter(config={})
    base_report = reporter.generate_json_report(analysis_results={}, metadata={})

    deep_report = DeepAnalysisReport(
        results={
            # 舊斷言為何錯: 有限 factor_returns 節固化錯位輸出;
            # inject 出口經 sanitizer → §U 佔位 + summary unavailable + completed 重算。
            "factor_returns": {"feat_1": {"long_short_mean_return": 0.01}},
            "trend_analysis": {"feat_1": {"combined_signal": {"recommendation": "正常"}}},
        },
        deep_analysis_errors=[
            SkippedResult(module_name="rolling_oos", reason="insufficient", error_type="INSUFFICIENT_DATA")
        ],
        module_summary={
            "factor_returns": "completed",
            "trend_analysis": "completed",
            "rolling_oos": "skipped",
        },
        completed_count=2,
        skipped_count=1,
    )

    enriched = reporter.inject_deep_analysis(base_report, deep_report)

    assert enriched["deep_analysis_enabled"] is True
    assert enriched["deep_analysis_version"] == "0.1"
    assert "factor_returns" in enriched
    assert enriched["factor_returns"].get("status") == "unavailable"
    assert enriched["factor_returns"].get("value") is None
    assert "feat_1" not in enriched["factor_returns"]
    assert "trend_analysis" in enriched
    assert isinstance(enriched["deep_analysis_errors"], list)
    # FR 下架後 completed 僅計 trend_analysis(1);legacy completed==2 矛盾已修
    assert enriched["deep_analysis_summary"]["completed"] == 1
    fr_status_entries = [
        item for item in enriched["module_statuses"]
        if item.get("module_name") == "factor_returns"
    ]
    assert fr_status_entries and fr_status_entries[0].get("status") == "unavailable"
    assert any(item["module_name"] == "rolling_oos" for item in enriched["module_statuses"])
