import pytest

from momentum.Analysis.deep_analysis_types import DeepAnalysisReport, SkippedResult
from momentum.Analysis.ic_config_schema import ICConfig, LongShortAnalysisConfig, load_ic_config


def test_deep_analysis_types_instantiation():
    skipped = SkippedResult(module_name="test", reason="r", error_type="INSUFFICIENT_DATA")
    report = DeepAnalysisReport()

    assert skipped.module_name == "test"
    assert report.total_modules == 10
    assert report.completed_count == 0


def test_ic_config_contains_deep_analysis_sections():
    config = ICConfig()
    assert config.factor_return.enabled is True
    assert config.factor_centrality.enabled is True
    assert config.trend_analysis.enabled is True
    assert config.parameter_sensitivity.enabled is True
    assert config.rolling_oos.enabled is True
    assert config.net_ic_analysis.default_cost_bps == 5


def test_long_short_quantile_overlap_rejected():
    with pytest.raises(ValueError):
        LongShortAnalysisConfig(
            num_quantiles=5,
            long_quantiles=[4, 5],
            short_quantiles=[5],
        )


def test_long_short_quantile_non_overlap_ok():
    config = LongShortAnalysisConfig(
        num_quantiles=5,
        long_quantiles=[4, 5],
        short_quantiles=[1, 2],
    )
    assert config.num_quantiles == 5


def test_load_ic_config_three_layer_merge_deep_analysis(tmp_path):
    default_path = tmp_path / "ic_config.yaml"
    user_path = tmp_path / "user_ic_config.yaml"

    default_path.write_text(
        """
version: '1.0'
factor_return:
  enabled: true
  num_quantiles: 5
net_ic_analysis:
  default_cost_bps: 5
""".strip(),
        encoding="utf-8",
    )
    user_path.write_text(
        """
factor_return:
  num_quantiles: 3
""".strip(),
        encoding="utf-8",
    )

    config = load_ic_config(
        default_path=str(default_path),
        user_path=str(user_path),
        api_override={"net_ic_analysis": {"default_cost_bps": 10}},
    )

    assert config.factor_return.num_quantiles == 3
    assert config.net_ic_analysis.default_cost_bps == 10
