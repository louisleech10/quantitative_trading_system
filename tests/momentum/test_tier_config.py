import pytest

from momentum.Analysis.ic_config_schema import ICConfig, FeatureTierConfig, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator


def test_default_tier_is_intermediate():
    config = ICConfig()
    assert config.feature_tiers.active_preset == "intermediate"


def test_foundation_preset_content():
    config = ICConfig()
    preset = config.feature_tiers.presets["foundation"]
    assert preset.deep_analysis is False


def test_intermediate_preset_disabled_modules():
    config = ICConfig()
    preset = config.feature_tiers.presets["intermediate"]
    assert "factor_orthogonalization" in preset.disabled_modules
    assert "factor_exposure" in preset.disabled_modules


def test_advanced_preset_enables_all():
    config = ICConfig()
    config.feature_tiers.active_preset = "advanced"
    orchestrator = ICFilterOrchestrator(config)

    applied = orchestrator._apply_tier_config(config)
    # 舊斷言為何錯: tier 後 `factor_return.enabled is True` 固化 tier 強制開啟錯位模組;
    # IC1C-FR-STOPGAP 從 tier 強制清單排除 factor_return → 保持 default-off False。
    assert applied.factor_return.enabled is False
    assert applied.factor_orthogonalization.enabled is True
    assert applied.factor_exposure.enabled is True


def test_custom_overrides_merge():
    config = ICConfig()
    config.feature_tiers.active_preset = "custom"
    config.feature_tiers.custom_overrides = {
        "stage_overrides": {"event_filtering": True},
        "module_overrides": {"factor_orthogonalization": True},
    }
    orchestrator = ICFilterOrchestrator(config)

    applied = orchestrator._apply_tier_config(config)
    assert applied.event_filter.enabled is True
    assert applied.factor_orthogonalization.enabled is True


def test_locked_features_cannot_disable():
    config = ICConfig()
    config.feature_tiers.active_preset = "custom"
    config.feature_tiers.custom_overrides = {
        "stage_overrides": {"ai_summary": False},
        "module_overrides": {},
    }
    orchestrator = ICFilterOrchestrator(config)

    applied = orchestrator._apply_tier_config(config)
    assert applied.report.ai_summary is True


def test_apply_tier_foundation_skips_deep():
    config = ICConfig()
    config.feature_tiers.active_preset = "foundation"
    orchestrator = ICFilterOrchestrator(config)

    applied = orchestrator._apply_tier_config(config)
    assert orchestrator._is_deep_analysis_enabled(applied) is False


def test_apply_tier_intermediate():
    config = ICConfig()
    config.feature_tiers.active_preset = "intermediate"
    orchestrator = ICFilterOrchestrator(config)

    applied = orchestrator._apply_tier_config(config)
    assert orchestrator._is_deep_analysis_enabled(applied) is True
    assert applied.factor_orthogonalization.enabled is False
    assert applied.factor_exposure.enabled is False


def test_invalid_preset_rejected():
    with pytest.raises(Exception):
        FeatureTierConfig(active_preset="invalid")


def test_yaml_tier_config_merge():
    config = load_ic_config(api_override={"feature_tiers": {"active_preset": "foundation"}})
    assert config.feature_tiers.active_preset == "foundation"
