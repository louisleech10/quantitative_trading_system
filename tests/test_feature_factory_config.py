import pytest
import yaml

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_config import (
    AlignmentMode,
    AtomicIndicatorConfig,
    EntropyConfig,
    FactoryConfig,
    MicrostructureConfig,
    PreprocessingConfig,
    SUPPORTED_TIMEFRAMES,
    TailRiskConfig,
    TimeframeConfig,
)


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
    # 2026-04 feature space expanded (microstructure/entropy/tail-risk + registry growth).
    # Keep this guard broad enough to detect regressions while allowing expected expansion.
    assert 60000 <= preview.total_features <= 100000


def test_validate_rejects_invalid():
    cm = ConfigManager()
    result = cm.validate_config(
        {"atomic_indicators": {"trend": {"indicators": [{"name": "NONEXIST"}]}}}
    )
    assert result.is_valid is False


def test_microstructure_config_defaults():
    config = MicrostructureConfig()
    assert config.enabled is False
    assert config.windows == [5, 13, 21, 55]
    assert config.epsilon == 1e-10


def test_entropy_config_perm_m_validation():
    with pytest.raises(ValueError):
        EntropyConfig(perm_m=1)


def test_tail_risk_config_alpha_validation():
    with pytest.raises(ValueError):
        TailRiskConfig(cvar_alphas=[0.0])


def test_preprocessing_config_has_all_subconfigs():
    config = PreprocessingConfig()
    assert config.winsorization.enabled is True
    assert config.adf_differencing.enabled is False
    assert config.fractional_differencing.enabled is False
    assert config.rank_transform.enabled is True
    assert config.gaussian_normalize.enabled is False
    assert config.adaptive_zscore.enabled is True


def test_atomic_indicator_config_has_new_sections():
    config = AtomicIndicatorConfig()
    assert config.microstructure.enabled is False
    assert config.entropy.enabled is False
    assert config.tail_risk.enabled is False


def test_factory_config_backward_compat_defaults():
    old_yaml_like = {
        "version": "2.2",
        "global": {},
        "data_sources": {},
        "timeframes": {},
        "atomic_indicators": {},
        "operators": {},
        "rolling_aggregation": {},
        "lag_features": {},
        "cross_sectional": {},
        "meta_features": {},
        "labels": {},
    }
    config = FactoryConfig.model_validate(old_yaml_like)
    assert config.preprocessing.enabled is False
    assert config.atomic_indicators.microstructure.enabled is False
    assert config.timeframes.alignment_mode == AlignmentMode.OPEN_MINUS


def test_timeframe_config_supported_timeframes():
    assert SUPPORTED_TIMEFRAMES == ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]


def test_timeframe_config_rejects_unsupported_values():
    with pytest.raises(ValueError):
        TimeframeConfig(primary="2h", training=["12h"])

    with pytest.raises(ValueError):
        TimeframeConfig(primary="12h", training=["2h"])


def test_migrate_config_adds_alignment_mode_default():
    migrated = ConfigManager.migrate_config({"timeframes": {"primary": "12h", "training": ["12h"]}})
    assert migrated["timeframes"]["alignment_mode"] == "open_minus"


def test_migrate_config_fallback_on_unknown_alignment_mode():
    migrated = ConfigManager.migrate_config(
        {"timeframes": {"primary": "12h", "training": ["12h"], "alignment_mode": "unknown"}}
    )
    assert migrated["timeframes"]["alignment_mode"] == "open_minus"


def test_config_hash_changes_when_alignment_mode_changes():
    factory = create_feature_factory()
    config_open = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": ["12h", "1h"], "alignment_mode": "open_minus"}}
    )
    config_close = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": ["12h", "1h"], "alignment_mode": "close_time"}}
    )

    hash_open = factory._compute_config_hash(config_open, symbol="ETHUSDT", timeframe="12h")
    hash_close = factory._compute_config_hash(config_close, symbol="ETHUSDT", timeframe="12h")
    assert hash_open != hash_close


def test_config_hash_same_for_reordered_training_timeframes():
    factory = create_feature_factory()
    config_a = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": ["12h", "1h"], "alignment_mode": "open_minus"}}
    )
    config_b = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": ["1h", "12h"], "alignment_mode": "open_minus"}}
    )

    hash_a = factory._compute_config_hash(config_a, symbol="ETHUSDT", timeframe="12h")
    hash_b = factory._compute_config_hash(config_b, symbol="ETHUSDT", timeframe="12h")
    assert hash_a == hash_b


def test_config_hash_changes_when_training_timeframes_change():
    factory = create_feature_factory()
    config_a = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": ["12h", "1h"], "alignment_mode": "open_minus"}}
    )
    config_b = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": ["12h", "4h"], "alignment_mode": "open_minus"}}
    )

    hash_a = factory._compute_config_hash(config_a, symbol="ETHUSDT", timeframe="12h")
    hash_b = factory._compute_config_hash(config_b, symbol="ETHUSDT", timeframe="12h")
    assert hash_a != hash_b


def test_yaml_with_new_sections_defaults():
    cm = ConfigManager()
    config = cm.get_merged_config()
    assert config.atomic_indicators.microstructure.enabled is False
    assert config.atomic_indicators.entropy.enabled is False
    assert config.atomic_indicators.tail_risk.enabled is False
    assert config.preprocessing.enabled is False


def test_yaml_enable_microstructure():
    cm = ConfigManager()
    config = cm.get_merged_config(
        api_override={"atomic_indicators": {"microstructure": {"enabled": True}}}
    )
    assert config.atomic_indicators.microstructure.enabled is True
    assert config.atomic_indicators.microstructure.windows == [5, 13, 21, 55]


def test_preview_with_new_engines():
    cm = ConfigManager()
    config = cm.get_merged_config(
        api_override={
            "atomic_indicators": {
                "microstructure": {"enabled": True},
                "entropy": {"enabled": True},
                "tail_risk": {"enabled": True},
            }
        }
    )
    preview = cm.preview_feature_count(config)
    assert preview.breakdown.get("microstructure", 0) == 25
    assert preview.breakdown.get("entropy", 0) == 21
    assert preview.breakdown.get("tail_risk", 0) == 26


def test_preview_with_preprocessing_added():
    cm = ConfigManager()
    config = cm.get_merged_config(
        api_override={
            "preprocessing": {
                "enabled": True,
                "mode": "append",
                "rank_transform": {"enabled": True},
                "gaussian_normalize": {"enabled": True},
                "adaptive_zscore": {"enabled": True, "windows": [100, 252]},
            }
        }
    )
    preview = cm.preview_feature_count(config)
    assert preview.breakdown.get("preprocessing_added", 0) > 0


def test_preview_new_engines_add_72_features():
    cm = ConfigManager()
    base = cm.get_merged_config()
    base_preview = cm.preview_feature_count(base)

    enhanced = cm.get_merged_config(
        api_override={
            "atomic_indicators": {
                "microstructure": {"enabled": True},
                "entropy": {"enabled": True},
                "tail_risk": {"enabled": True},
            }
        }
    )
    enhanced_preview = cm.preview_feature_count(enhanced)

    assert enhanced_preview.total_features - base_preview.total_features == 72
    assert enhanced_preview.breakdown["microstructure"] == 25
    assert enhanced_preview.breakdown["entropy"] == 21
    assert enhanced_preview.breakdown["tail_risk"] == 26


def test_scan_config_contains_new_sections():
    with open("config/scan_config.yaml", "r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    assert "atomic_indicators" in raw
    assert "microstructure" in raw["atomic_indicators"]
    assert "entropy" in raw["atomic_indicators"]
    assert "tail_risk" in raw["atomic_indicators"]
    assert "preprocessing" in raw
    assert raw["timeframes"]["alignment_mode"] == "open_minus"
