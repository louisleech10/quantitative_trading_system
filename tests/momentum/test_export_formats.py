from pathlib import Path

from momentum.Analysis.ic_reporter import ICReporter


def _sample_report(deep_enabled: bool = True) -> dict:
    report = {
        "version": "1.0",
        "generated_at": "2026-02-17T00:00:00",
        "summary_table": [
            {
                "rank": 1,
                "feature_name": "feature_a",
                "ic_mean": 0.08,
                "icir": 1.2,
                "p_value": 0.01,
                "ic_hit_rate": 0.68,
                "monotonicity_score": 0.71,
                "coverage": 0.99,
                "turnover_rate": 0.21,
            },
            {
                "rank": 2,
                "feature_name": "feature_b",
                "ic_mean": 0.03,
                "icir": 0.45,
                "p_value": 0.08,
                "ic_hit_rate": 0.52,
                "monotonicity_score": 0.4,
                "coverage": 0.95,
                "turnover_rate": 0.31,
            },
        ],
        "ic_decay": {
            "feature_a": {"half_life": 4, "decay_rate": 0.2, "decay_type": "exp"},
            "feature_b": {"half_life": 2, "decay_rate": 0.4, "decay_type": "exp"},
        },
        "quantile_returns": {
            "feature_a": {"long_short_spread": 0.12},
            "feature_b": {"long_short_spread": 0.03},
        },
        "correlation_matrix": {
            "features": ["feature_a", "feature_b"],
            "matrix": [[1.0, 0.35], [0.35, 1.0]],
        },
        "filter_log": {"stage_1": {"input": 100, "output": 20}},
    }

    if deep_enabled:
        report["deep_analysis_report"] = {
            "results": {
                "factor_returns": {
                    "feature_a": {
                        "long_short_mean_return": 0.11,
                        "risk_metrics": {"sharpe": 1.5, "max_drawdown": -0.08},
                    }
                },
                "trend_analysis": {
                    "feature_a": {"combined_signal": {"recommendation": "持有"}}
                },
                "factor_exposure": {"concentration": {"hhi": 0.22}},
                "rolling_oos": {
                    "features": {
                        "feature_a": {
                            "assessment": "robust",
                            "oos_stability": {"mean_oos_ic": 0.06},
                        }
                    }
                },
                "feature_quality_diagnostics": {
                    "adf_results": {"feature_a": {"is_stationary": True}}
                },
                "net_ic_analysis": {
                    "features": {"feature_a": {"net_ic": 0.04}}
                },
            }
        }

    return report


def test_summary_csv_columns_match_spec() -> None:
    reporter = ICReporter({})
    csv_text = reporter.generate_summary_csv(_sample_report())
    header = csv_text.splitlines()[0].replace("\ufeff", "")

    assert "rank" in header
    assert "feature_name" in header
    assert "ic_mean" in header
    assert "max_correlation" in header
    assert "trend_recommendation" in header


def test_summary_csv_utf8_bom() -> None:
    reporter = ICReporter({})
    csv_text = reporter.generate_summary_csv(_sample_report())
    assert csv_text.startswith("\ufeff")


def test_detailed_csv_factor_return_format() -> None:
    reporter = ICReporter({})
    csv_text = reporter.generate_detailed_csv(_sample_report(), "factor_returns")
    assert csv_text.startswith("\ufeff")
    assert "long_short_mean_return" in csv_text


def test_detailed_csv_all_modules() -> None:
    reporter = ICReporter({})
    report = _sample_report()
    modules = list(report["deep_analysis_report"]["results"].keys())
    for module in modules:
        csv_text = reporter.generate_detailed_csv(report, module)
        assert csv_text.startswith("\ufeff")
        assert len(csv_text.splitlines()) >= 2


def test_ai_json_has_interpretation_guide() -> None:
    reporter = ICReporter({})
    payload = reporter.generate_ai_json(_sample_report())
    assert "interpretation_guide" in payload
    assert "key_findings" in payload
    assert "recommendations" in payload


def test_ai_json_key_findings_auto_generated() -> None:
    reporter = ICReporter({})
    payload = reporter.generate_ai_json(_sample_report())
    assert payload["key_findings"]
    assert any("最佳因子" in item for item in payload["key_findings"])


def test_ai_json_token_count_under_4k() -> None:
    reporter = ICReporter({})
    large_report = _sample_report()
    large_report["summary_table"] = [
        {
            "rank": idx + 1,
            "feature_name": f"feature_{idx}",
            "ic_mean": 0.01,
            "icir": 0.5,
            "p_value": 0.04,
        }
        for idx in range(60)
    ]

    payload = reporter.generate_ai_json(large_report)
    text = str(payload)
    assert len(text.split()) < 4000


def test_enhanced_markdown_has_top10_table() -> None:
    reporter = ICReporter({})
    markdown = reporter.generate_enhanced_markdown(_sample_report())
    assert "| Rank | Feature | IC Mean | ICIR | P-Value |" in markdown


def test_enhanced_markdown_risk_warnings() -> None:
    reporter = ICReporter({})
    markdown = reporter.generate_enhanced_markdown(_sample_report())
    assert "## 風險警告" in markdown


def test_export_all_creates_all_files(tmp_path: Path) -> None:
    reporter = ICReporter({})
    exported = reporter.export_all(_sample_report(), str(tmp_path), "case_x")

    assert Path(exported["json"]).exists()
    assert Path(exported["ai_json"]).exists()
    assert Path(exported["csv_summary"]).exists()
    assert Path(exported["markdown"]).exists()


def test_deep_analysis_disabled_csv_basic_only() -> None:
    reporter = ICReporter({})
    csv_text = reporter.generate_summary_csv(_sample_report(deep_enabled=False))
    header = csv_text.splitlines()[0].replace("\ufeff", "")
    assert "feature_name" in header
    assert "trend_recommendation" not in header
