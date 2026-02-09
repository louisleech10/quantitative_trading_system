from momentum.FeatureEngineering.config_manager import ConfigManager


def test_three_layer_merge():
    cm = ConfigManager()
    config = cm.get_merged_config(
        api_override={"atomic_indicators": {"trend": {"enabled": False}}}
    )
    assert config.atomic_indicators.trend.enabled is False


def test_preset_standard():
    cm = ConfigManager()
    config = cm.apply_preset("standard")
    preview = cm.preview_feature_count(config)
    assert 500 <= preview.total_features <= 1200


def test_validate_rejects_invalid():
    cm = ConfigManager()
    result = cm.validate_config(
        {"atomic_indicators": {"trend": {"indicators": [{"name": "NONEXIST"}]}}}
    )
    assert result.is_valid is False
