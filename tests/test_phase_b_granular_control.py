"""
Phase B 驗證測試 — Feature Factory Granular Control Plan

涵蓋項目：
- B1: Schema API
- B2: Batch Toggle API
- B3: Preset API expansion (4 new presets)
- B4: Preview accuracy optimization (per-indicator/aggregator/operator filter)
"""

import copy
import pytest

from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_config import (
    AggregatorConfig,
    CategoryConfig,
    CrossFeatureConfig,
    CrossSectionalConfig,
    FactoryConfig,
    IndicatorDef,
    MicrostructureConfig,
    AdvancedFeatureItemConfig,
    RollingAggConfig,
)


# ===========================================================
# Fixtures
# ===========================================================

@pytest.fixture
def config_manager():
    """Return a ConfigManager using the project default config."""
    return ConfigManager()


@pytest.fixture
def merged_config(config_manager):
    """Return the fully merged FactoryConfig."""
    return config_manager.get_merged_config()


# ===========================================================
# B1: Schema API — Service-level schema building
# ===========================================================

class TestB1SchemaAPI:
    """B1: Schema API 驗證"""

    def test_schema_structure(self, config_manager):
        """Schema 包含所有 7 個 layer key"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        assert "layers" in schema
        expected_layers = {"layer1", "layer2", "layer3", "layer4", "layer5", "layer6", "layer6_5"}
        assert set(schema["layers"].keys()) == expected_layers

    def test_layer1_categories(self, config_manager):
        """Layer 1 包含 10 個 category"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        categories = schema["layers"]["layer1"]["categories"]
        expected_cats = {
            "trend", "momentum", "volatility", "volume",
            "cycle", "pattern", "statistics",
            "microstructure", "entropy", "tail_risk",
        }
        assert set(categories.keys()) == expected_cats

    def test_layer1_special_categories_have_features(self, config_manager):
        """microstructure/entropy/tail_risk 在 schema 中不應為空"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        categories = schema["layers"]["layer1"]["categories"]
        for cat in ["microstructure", "entropy", "tail_risk"]:
            assert len(categories[cat]["features"]) > 0, f"{cat} features 不應為空"

    def test_layer1_indicator_has_enabled_field(self, config_manager):
        """每個指標都有 enabled 欄位"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        trend = schema["layers"]["layer1"]["categories"]["trend"]
        assert len(trend["indicators"]) > 0
        for ind in trend["indicators"]:
            assert "name" in ind
            assert "enabled" in ind
            assert isinstance(ind["enabled"], bool)

    def test_layer1_cdl_pattern_has_description(self, config_manager):
        """CDL 形態指標具有描述"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        pattern = schema["layers"]["layer1"]["categories"]["pattern"]
        cdl_indicators = [i for i in pattern["indicators"] if i["name"].startswith("CDL")]
        assert len(cdl_indicators) > 0
        for ind in cdl_indicators:
            assert ind["description"] != "", f"{ind['name']} 缺少描述"

    def test_layer1_known_indicator_description(self, config_manager):
        """已知指標如 EMA/RSI 應有正確描述"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        trend = schema["layers"]["layer1"]["categories"]["trend"]
        ema_list = [i for i in trend["indicators"] if i["name"] == "EMA"]
        assert len(ema_list) == 1
        assert ema_list[0]["description"] == "指數移動平均"

    def test_layer2_operators(self, config_manager):
        """Layer 2 包含 6 個 operator"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        operators = schema["layers"]["layer2"]["operators"]
        expected_ops = {"distance", "cross", "momentum", "ratio", "binary_signal", "worldquant"}
        assert set(operators.keys()) == expected_ops

    def test_layer3_aggregators(self, config_manager):
        """Layer 3 包含所有 aggregator 且有 enabled 欄位"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        aggs = schema["layers"]["layer3"]["aggregators"]
        expected_aggs = {"slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"}
        assert set(aggs.keys()) == expected_aggs
        for name, cfg in aggs.items():
            assert "enabled" in cfg, f"aggregator {name} 缺少 enabled"

    def test_layer6_sub_engines(self, config_manager):
        """Layer 6 包含 7 個 sub-engine"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        subs = schema["layers"]["layer6"]["sub_engines"]
        expected = {
            "consensus", "interaction", "time_features", "trend_consensus",
            "momentum_divergence", "volume_price_divergence", "volatility_regime",
        }
        assert set(subs.keys()) == expected

    def test_layer6_5_methods(self, config_manager):
        """Layer 6.5 包含 6 個 preprocessing 方法"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()
        schema = svc.get_schema()

        methods = schema["layers"]["layer6_5"]["methods"]
        expected = {
            "winsorization", "rank_transform", "adaptive_zscore",
            "gaussian_normalize", "adf_differencing", "fractional_differencing",
        }
        assert set(methods.keys()) == expected


# ===========================================================
# B2: Batch Toggle API
# ===========================================================

class TestB2BatchToggle:
    """B2: Batch Toggle API 驗證"""

    def test_toggle_indicator_enabled(self):
        """批量切換指標 enabled 狀態"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        result = svc.batch_toggle([
            {"path": "atomic_indicators.trend.indicators.SMA.enabled", "value": False},
        ])
        assert result["results"][0]["success"] is True

        # Verify SMA is disabled in returned config
        trend_indicators = result["config"]["atomic_indicators"]["trend"]["indicators"]
        sma = next(i for i in trend_indicators if i["name"] == "SMA")
        assert sma["enabled"] is False

    def test_toggle_aggregator_enabled(self):
        """批量切換 rolling aggregator enabled"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        result = svc.batch_toggle([
            {"path": "rolling_aggregation.aggregators.zscore.enabled", "value": False},
        ])
        assert result["results"][0]["success"] is True

        agg = result["config"]["rolling_aggregation"]["aggregators"]
        assert agg["zscore"]["enabled"] is False

    def test_toggle_invalid_path(self):
        """無效路徑應回傳 success=false"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        result = svc.batch_toggle([
            {"path": "nonexistent.path.here", "value": True},
        ])
        assert result["results"][0]["success"] is False

    def test_toggle_multiple_items(self):
        """多個批量切換同時運作"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        result = svc.batch_toggle([
            {"path": "atomic_indicators.trend.indicators.EMA.enabled", "value": False},
            {"path": "atomic_indicators.trend.indicators.SMA.enabled", "value": False},
            {"path": "rolling_aggregation.aggregators.zscore.enabled", "value": False},
        ])
        assert all(r["success"] for r in result["results"])
        assert "preview" in result
        assert "config" in result

    def test_toggle_returns_preview(self):
        """每次 batch toggle 都回傳 preview"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        result = svc.batch_toggle([
            {"path": "atomic_indicators.trend.indicators.EMA.enabled", "value": True},
        ])
        assert "preview" in result
        assert "total_features" in result["preview"]

    def test_toggle_operator_enabled(self):
        """切換 operator enabled"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        result = svc.batch_toggle([
            {"path": "operators.distance.enabled", "value": False},
        ])
        assert result["results"][0]["success"] is True
        assert result["config"]["operators"]["distance"]["enabled"] is False


# ===========================================================
# B3: Preset API expansion
# ===========================================================

class TestB3PresetExpansion:
    """B3: 新增 4 個 Preset 驗證"""

    @pytest.mark.parametrize("preset_name", [
        "trend_focused",
        "momentum_focused",
        "microstructure_focused",
        "lightweight_ml",
    ])
    def test_new_preset_valid(self, config_manager, preset_name):
        """新 preset 能正常生成合法的 FactoryConfig"""
        config = config_manager.apply_preset(preset_name)
        assert isinstance(config, FactoryConfig)

    def test_trend_focused_only_select_momentum(self, config_manager):
        """trend_focused: Momentum 只保留 RSI/MACD/ADX"""
        config = config_manager.apply_preset("trend_focused")
        cfg = config.model_dump(by_alias=True)

        # Trend should be enabled
        assert cfg["atomic_indicators"]["trend"]["enabled"] is True
        # Volatility should be enabled
        assert cfg["atomic_indicators"]["volatility"]["enabled"] is True
        # Momentum should be enabled but only 3 indicators active
        assert cfg["atomic_indicators"]["momentum"]["enabled"] is True
        mom_indicators = cfg["atomic_indicators"]["momentum"]["indicators"]
        enabled_mom = [i for i in mom_indicators if i.get("enabled", True)]
        enabled_names = {i["name"] for i in enabled_mom}
        assert enabled_names == {"RSI", "MACD", "ADX"}

    def test_momentum_focused_enables_volume(self, config_manager):
        """momentum_focused: Volume 啟用"""
        config = config_manager.apply_preset("momentum_focused")
        cfg = config.model_dump(by_alias=True)

        assert cfg["atomic_indicators"]["momentum"]["enabled"] is True
        assert cfg["atomic_indicators"]["volume"]["enabled"] is True

    def test_microstructure_focused_enables_correct(self, config_manager):
        """microstructure_focused: Microstructure + Volume + Entropy"""
        config = config_manager.apply_preset("microstructure_focused")
        cfg = config.model_dump(by_alias=True)

        assert cfg["atomic_indicators"]["microstructure"]["enabled"] is True
        assert cfg["atomic_indicators"]["volume"]["enabled"] is True
        assert cfg["atomic_indicators"]["entropy"]["enabled"] is True
        # Trend should be disabled
        assert cfg["atomic_indicators"]["trend"]["enabled"] is False

    def test_lightweight_ml_limited_indicators(self, config_manager):
        """lightweight_ml: 精選有限指標"""
        config = config_manager.apply_preset("lightweight_ml")
        cfg = config.model_dump(by_alias=True)

        # Count total enabled indicators across all categories
        total_enabled = 0
        for cat_key in ["trend", "momentum", "volatility", "volume"]:
            cat = cfg["atomic_indicators"].get(cat_key, {})
            if not cat.get("enabled", True):
                continue
            for ind in cat.get("indicators", []):
                if ind.get("enabled", True):
                    total_enabled += 1
        # Should be around 13 (3 trend + 6 mom + 2 vol + 2 vol_ind)
        assert total_enabled <= 20, f"Too many indicators: {total_enabled}"
        assert total_enabled >= 10, f"Too few indicators: {total_enabled}"

    def test_lightweight_ml_rolling_only_3_agg(self, config_manager):
        """lightweight_ml: Rolling 只用 mean/std/rank"""
        config = config_manager.apply_preset("lightweight_ml")
        cfg = config.model_dump(by_alias=True)

        agg = cfg["rolling_aggregation"]["aggregators"]
        enabled_aggs = {k for k, v in agg.items() if v.get("enabled", True)}
        assert enabled_aggs == {"mean", "std", "rank"}

    def test_preset_applied_via_service(self):
        """Service 層 apply_preset_config 正確運作"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        result = svc.apply_preset_config("trend_focused")
        assert "config" in result
        assert "preview" in result
        assert result["preview"]["total_features"] > 0

    def test_presets_list_includes_new_presets(self):
        """MCP get_presets 包含所有新 preset"""
        from api.services.feature_factory_service import FeatureFactoryService
        svc = FeatureFactoryService()

        presets = svc.get_presets()
        names = {p["name"] for p in presets}
        assert "trend_focused" in names
        assert "momentum_focused" in names
        assert "microstructure_focused" in names
        assert "lightweight_ml" in names

    def test_unknown_preset_raises_error(self, config_manager):
        """未知 preset 名稱拋出 ValueError"""
        with pytest.raises(ValueError, match="Unknown preset"):
            config_manager.apply_preset("nonexistent_preset")


# ===========================================================
# B4: Preview accuracy optimization
# ===========================================================

class TestB4PreviewAccuracy:
    """B4: Preview 精確度優化驗證"""

    def test_per_indicator_enabled_affects_count(self, config_manager):
        """關閉 indicator 應降低 atomic 計數"""
        full_config = config_manager.get_merged_config()
        full_preview = config_manager.preview_feature_count(full_config)
        full_total = full_preview.total_features

        # Disable most trend indicators
        override = {
            "atomic_indicators": {
                "trend": {
                    "enabled": True,
                    "indicators": [
                        {"name": "EMA", "enabled": True},
                        {"name": "SMA", "enabled": False},
                        {"name": "WMA", "enabled": False},
                        {"name": "DEMA", "enabled": False},
                        {"name": "TEMA", "enabled": False},
                    ],
                }
            }
        }
        partial_config = config_manager.get_merged_config(override)
        partial_preview = config_manager.preview_feature_count(partial_config)

        assert partial_preview.total_features < full_total, \
            f"Disabling indicators should reduce count: {partial_preview.total_features} vs {full_total}"

    def test_all_indicators_disabled_gives_zero_atomic(self, config_manager):
        """所有指標 disabled → atomic count = 0"""
        override = {"atomic_indicators": {}}
        # Disable all categories
        for cat in ["trend", "momentum", "volatility", "volume",
                     "cycle", "pattern", "statistics"]:
            override["atomic_indicators"][cat] = {"enabled": False}
        override["atomic_indicators"]["microstructure"] = {"enabled": False}
        override["atomic_indicators"]["entropy"] = {"enabled": False}
        override["atomic_indicators"]["tail_risk"] = {"enabled": False}

        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        assert preview.breakdown["atomic"] == 0

    def test_per_aggregator_enabled_affects_rolling(self, config_manager):
        """關閉部分 aggregator 應降低 rolling 計數"""
        # 全開 config
        full_config = config_manager.get_merged_config()
        full_preview = config_manager.preview_feature_count(full_config)

        # 只開 2 個 aggregator
        override = {
            "rolling_aggregation": {
                "enabled": True,
                "aggregators": {
                    "mean": {"enabled": True},
                    "std": {"enabled": True},
                    "slope": {"enabled": False},
                    "rank": {"enabled": False},
                    "zscore": {"enabled": False},
                    "skew": {"enabled": False},
                    "kurt": {"enabled": False},
                    "min": {"enabled": False},
                    "max": {"enabled": False},
                    "range": {"enabled": False},
                },
            }
        }
        partial_config = config_manager.get_merged_config(override)
        partial_preview = config_manager.preview_feature_count(partial_config)

        assert partial_preview.breakdown["rolling"] < full_preview.breakdown["rolling"], \
            "Disabling aggregators should reduce rolling count"

    def test_rolling_disabled_gives_zero(self, config_manager):
        """Rolling disabled → rolling count = 0"""
        override = {"rolling_aggregation": {"enabled": False}}
        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        assert preview.breakdown["rolling"] == 0

    def test_preview_breakdown_keys(self, config_manager):
        """Preview breakdown 包含所有必要 key"""
        config = config_manager.get_merged_config()
        preview = config_manager.preview_feature_count(config)

        expected_keys = {"atomic", "derived", "rolling", "lag", "cross_sectional", "meta", "labels"}
        assert expected_keys.issubset(set(preview.breakdown.keys()))

    def test_operators_disabled_affects_derived(self, config_manager):
        """關閉所有 operators → derived count = 0"""
        override = {
            "operators": {
                "distance": {"enabled": False},
                "cross": {"enabled": False},
                "momentum": {"enabled": False},
                "ratio": {"enabled": False},
                "binary_signal": {"enabled": False},
                "worldquant": {"enabled": False},
            }
        }
        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        assert preview.breakdown["derived"] == 0

    def test_cross_sectional_per_feature_count(self, config_manager):
        """Cross-sectional per-feature enabled 影響計數"""
        override = {
            "cross_sectional": {
                "enabled": True,
                "features": {
                    "relative_price": {"enabled": True},
                    "beta": {"enabled": False},
                    "idiosyncratic_momentum": {"enabled": False},
                },
            }
        }
        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        assert preview.breakdown["cross_sectional"] == 1

    def test_meta_per_subengine_count(self, config_manager):
        """Meta features per-subengine enabled 影響計數"""
        # Disable all meta sub-engines
        override = {
            "meta_features": {
                "enabled": True,
                "consensus": False,
                "interaction": False,
                "time_features": False,
                "trend_consensus": False,
                "momentum_divergence": False,
                "volume_price_divergence": False,
                "volatility_regime": False,
            }
        }
        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        assert preview.breakdown["meta"] == 0


# ===========================================================
# Config Migration (向後相容)
# ===========================================================

class TestConfigMigration:
    """Config migration 向後相容驗證"""

    def test_old_aggregators_list_migrated(self):
        """舊格式 aggregators: list[str] → dict[str, AggregatorConfig]"""
        raw = {
            "rolling_aggregation": {
                "aggregators": ["mean", "std", "rank"],
            }
        }
        result = ConfigManager.migrate_config(raw)
        agg = result["rolling_aggregation"]["aggregators"]
        assert isinstance(agg, dict)
        assert set(agg.keys()) == {"mean", "std", "rank"}
        for v in agg.values():
            assert v["enabled"] is True

    def test_old_cross_features_list_migrated(self):
        """舊格式 cross_sectional.features: list[str] → dict"""
        raw = {
            "cross_sectional": {
                "features": ["relative_price", "beta"],
            }
        }
        result = ConfigManager.migrate_config(raw)
        feats = result["cross_sectional"]["features"]
        assert isinstance(feats, dict)
        assert set(feats.keys()) == {"relative_price", "beta"}

    def test_old_microstructure_enabled_features_migrated(self):
        """舊格式 microstructure.enabled_features: list → features dict"""
        raw = {
            "atomic_indicators": {
                "microstructure": {
                    "enabled_features": ["amihud", "kyle_lambda"],
                }
            }
        }
        result = ConfigManager.migrate_config(raw)
        ms = result["atomic_indicators"]["microstructure"]
        assert "features" in ms
        assert set(ms["features"].keys()) == {"amihud", "kyle_lambda"}

    def test_indicator_without_enabled_defaults_true(self):
        """指標缺少 enabled 欄位 → 預設 True"""
        ind = IndicatorDef(name="EMA")
        assert ind.enabled is True
