"""Phase A: Granular Control — 向後相容與新功能測試

Tests for FEATURE_FACTORY_GRANULAR_CONTROL_PLAN V1.2 Phase A:
- A1: IndicatorDef.enabled
- A2: AdvancedFeatureItemConfig + Micro/Entropy/TailRisk features dict
- A3: RollingAggConfig.aggregators list→dict
- A4: CrossSectionalConfig.features list→dict
- A5: BinarySignalRule + BinarySignalToggle
- A6: WorldQuantToggle + OperatorItemConfig
- A7: ConfigManager.migrate_config()
- A8: FeatureFactory filter helpers
- A9: Backward compatibility
"""

import copy

import pytest

from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_config import (
    AdvancedFeatureItemConfig,
    AggregatorConfig,
    BinarySignalRule,
    BinarySignalToggle,
    CategoryConfig,
    CrossFeatureConfig,
    CrossSectionalConfig,
    EntropyConfig,
    FactoryConfig,
    IndicatorDef,
    MicrostructureConfig,
    OperatorConfig,
    OperatorItemConfig,
    OperatorToggle,
    RollingAggConfig,
    TailRiskConfig,
    WorldQuantToggle,
)


# ═══════════════════════════════════════════════════════════════════
# A1: IndicatorDef.enabled
# ═══════════════════════════════════════════════════════════════════


class TestA1IndicatorDefEnabled:
    """IndicatorDef 新增 enabled 欄位"""

    def test_default_enabled_true(self):
        """新建 IndicatorDef 預設 enabled=True"""
        ind = IndicatorDef(name="EMA")
        assert ind.enabled is True

    def test_explicit_enabled_false(self):
        """明確設定 enabled=False"""
        ind = IndicatorDef(name="SMA", enabled=False)
        assert ind.enabled is False

    def test_old_format_without_enabled(self):
        """舊格式 dict（無 enabled 欄位）→ 預設 True"""
        ind = IndicatorDef.model_validate({"name": "RSI", "periods": [14]})
        assert ind.enabled is True
        assert ind.name == "RSI"

    def test_model_dump_includes_enabled(self):
        """model_dump() 輸出包含 enabled"""
        ind = IndicatorDef(name="MACD", enabled=False)
        d = ind.model_dump()
        assert d["enabled"] is False
        assert d["name"] == "MACD"

    def test_extra_fields_preserved(self):
        """extra fields 仍然通過 ConfigDict(extra='allow')"""
        ind = IndicatorDef(name="BBANDS", periods=[20], stddev=[2.0])
        assert ind.name == "BBANDS"
        assert ind.enabled is True


# ═══════════════════════════════════════════════════════════════════
# A2: AdvancedFeatureItemConfig + Micro/Entropy/TailRisk
# ═══════════════════════════════════════════════════════════════════


class TestA2AdvancedFeatures:
    """Microstructure/Entropy/TailRisk per-feature 控制"""

    def test_advanced_feature_item_default(self):
        cfg = AdvancedFeatureItemConfig()
        assert cfg.enabled is True

    def test_advanced_feature_item_extra_fields(self):
        cfg = AdvancedFeatureItemConfig(enabled=True, windows=[5, 13, 21])
        assert cfg.enabled is True
        # extra="allow" 允許 windows 等欄位

    def test_microstructure_features_dict_empty_default(self):
        cfg = MicrostructureConfig()
        assert cfg.features == {}
        assert cfg.enabled is False

    def test_microstructure_with_features(self):
        cfg = MicrostructureConfig(
            enabled=True,
            features={
                "amihud": AdvancedFeatureItemConfig(enabled=True),
                "kyle_lambda": AdvancedFeatureItemConfig(enabled=False),
            },
        )
        assert cfg.features["amihud"].enabled is True
        assert cfg.features["kyle_lambda"].enabled is False

    def test_microstructure_old_format_still_works(self):
        """舊格式 enabled_features 仍可使用"""
        cfg = MicrostructureConfig(enabled=True, enabled_features=["amihud", "vpin"])
        assert cfg.enabled_features == ["amihud", "vpin"]
        assert cfg.features == {}  # features 保持空（由 migrate_config 轉換）

    def test_entropy_features_dict_empty_default(self):
        cfg = EntropyConfig()
        assert cfg.features == {}

    def test_entropy_with_features(self):
        cfg = EntropyConfig(
            enabled=True,
            features={
                "shannon": AdvancedFeatureItemConfig(enabled=True),
                "hurst": AdvancedFeatureItemConfig(enabled=False),
            },
        )
        assert cfg.features["shannon"].enabled is True
        assert cfg.features["hurst"].enabled is False

    def test_tail_risk_features_dict_empty_default(self):
        cfg = TailRiskConfig()
        assert cfg.features == {}

    def test_tail_risk_with_features(self):
        cfg = TailRiskConfig(
            enabled=True,
            features={
                "cvar": AdvancedFeatureItemConfig(enabled=True),
                "max_drawdown": AdvancedFeatureItemConfig(enabled=False),
            },
        )
        assert cfg.features["cvar"].enabled is True
        assert cfg.features["max_drawdown"].enabled is False


# ═══════════════════════════════════════════════════════════════════
# A3: RollingAggConfig aggregators list → dict
# ═══════════════════════════════════════════════════════════════════


class TestA3RollingAggConfig:
    """RollingAggConfig.aggregators 向後相容轉換"""

    def test_default_aggregators_are_dict(self):
        cfg = RollingAggConfig()
        assert isinstance(cfg.aggregators, dict)
        assert "slope" in cfg.aggregators
        assert cfg.aggregators["slope"].enabled is True

    def test_list_input_converted_to_dict(self):
        """舊格式 list[str] → dict (向後相容)"""
        cfg = RollingAggConfig.model_validate({
            "enabled": True,
            "windows": [5, 13],
            "aggregators": ["mean", "std", "rank"],
        })
        assert isinstance(cfg.aggregators, dict)
        assert len(cfg.aggregators) == 3
        assert cfg.aggregators["mean"].enabled is True
        assert cfg.aggregators["rank"].enabled is True

    def test_dict_input_parsed_correctly(self):
        """新格式 dict[str, AggregatorConfig]"""
        cfg = RollingAggConfig.model_validate({
            "enabled": True,
            "windows": [5],
            "aggregators": {
                "mean": {"enabled": True},
                "zscore": {"enabled": False},
            },
        })
        assert cfg.aggregators["mean"].enabled is True
        assert cfg.aggregators["zscore"].enabled is False

    def test_model_dump_output(self):
        cfg = RollingAggConfig()
        d = cfg.model_dump()
        assert isinstance(d["aggregators"], dict)
        assert d["aggregators"]["slope"]["enabled"] is True


# ═══════════════════════════════════════════════════════════════════
# A4: CrossSectionalConfig features list → dict
# ═══════════════════════════════════════════════════════════════════


class TestA4CrossSectionalConfig:
    """CrossSectionalConfig.features 向後相容轉換"""

    def test_default_features_are_dict(self):
        cfg = CrossSectionalConfig()
        assert isinstance(cfg.features, dict)
        assert "relative_price" in cfg.features
        assert cfg.features["relative_price"].enabled is True

    def test_list_input_converted_to_dict(self):
        """舊格式 list[str] → dict"""
        cfg = CrossSectionalConfig.model_validate({
            "enabled": True,
            "reference_symbol": "BTCUSDT",
            "features": ["relative_price", "beta"],
        })
        assert isinstance(cfg.features, dict)
        assert len(cfg.features) == 2
        assert cfg.features["beta"].enabled is True

    def test_dict_input_parsed_correctly(self):
        """新格式 dict"""
        cfg = CrossSectionalConfig.model_validate({
            "enabled": True,
            "reference_symbol": "BTCUSDT",
            "features": {
                "relative_price": {"enabled": True},
                "beta": {"enabled": False},
                "idiosyncratic_momentum": {"enabled": True},
            },
        })
        assert cfg.features["beta"].enabled is False

    def test_in_operator_works_on_dict(self):
        """dict 的 'in' 運算子與 list 行為一致"""
        cfg = CrossSectionalConfig()
        assert "relative_price" in cfg.features
        assert "nonexistent" not in cfg.features


# ═══════════════════════════════════════════════════════════════════
# A5: BinarySignalRule + BinarySignalToggle
# ═══════════════════════════════════════════════════════════════════


class TestA5BinarySignalRule:
    """BinarySignalRule model + BinarySignalToggle"""

    def test_binary_signal_rule_default_enabled(self):
        rule = BinarySignalRule(
            indicator="RSI", condition="> 70", name_suffix="Overbought"
        )
        assert rule.enabled is True

    def test_binary_signal_rule_disabled(self):
        rule = BinarySignalRule(
            indicator="RSI", condition="< 30", name_suffix="Oversold", enabled=False
        )
        assert rule.enabled is False

    def test_binary_signal_toggle_inherits_operator_toggle(self):
        toggle = BinarySignalToggle()
        assert toggle.enabled is True
        assert toggle.rules == []
        assert toggle.apply_to == "all"

    def test_binary_signal_toggle_with_rules(self):
        toggle = BinarySignalToggle(
            enabled=True,
            rules=[
                BinarySignalRule(indicator="RSI", condition="> 70", name_suffix="OB"),
                BinarySignalRule(
                    indicator="RSI", condition="< 30", name_suffix="OS", enabled=False
                ),
            ],
        )
        assert len(toggle.rules) == 2
        assert toggle.rules[0].enabled is True
        assert toggle.rules[1].enabled is False

    def test_old_format_rules_without_enabled(self):
        """舊 YAML 格式的 rules（無 enabled 欄位）→ 預設 True"""
        toggle = BinarySignalToggle.model_validate({
            "enabled": True,
            "rules": [
                {"indicator": "RSI", "condition": "> 70", "name_suffix": "OB"},
                {"indicator": "ADX", "condition": "> 25", "name_suffix": "ST"},
            ],
        })
        assert all(r.enabled for r in toggle.rules)

    def test_operator_config_uses_binary_signal_toggle(self):
        cfg = OperatorConfig()
        assert isinstance(cfg.binary_signal, BinarySignalToggle)
        assert cfg.binary_signal.rules == []


# ═══════════════════════════════════════════════════════════════════
# A6: WorldQuantToggle + OperatorItemConfig
# ═══════════════════════════════════════════════════════════════════


class TestA6WorldQuantConfig:
    """WorldQuantToggle per-sub-operator 控制"""

    def test_operator_item_config_default(self):
        cfg = OperatorItemConfig()
        assert cfg.enabled is True

    def test_worldquant_toggle_default_operators_none(self):
        toggle = WorldQuantToggle()
        assert toggle.operators is None
        assert toggle.enabled is True

    def test_worldquant_toggle_with_operators(self):
        toggle = WorldQuantToggle.model_validate({
            "enabled": True,
            "operators": {
                "ts_argmax": {"enabled": True, "windows": [5, 13]},
                "ts_corr": {"enabled": False},
            },
        })
        assert toggle.operators["ts_argmax"].enabled is True
        assert toggle.operators["ts_corr"].enabled is False

    def test_operator_config_uses_worldquant_toggle(self):
        cfg = OperatorConfig()
        assert isinstance(cfg.worldquant, WorldQuantToggle)
        assert cfg.worldquant.operators is None

    def test_old_worldquant_format_no_operators(self):
        """舊格式只有 enabled + apply_to"""
        cfg = OperatorConfig.model_validate({
            "distance": {"enabled": True},
            "cross": {"enabled": True},
            "momentum": {"enabled": True},
            "ratio": {"enabled": True},
            "binary_signal": {"enabled": True},
            "worldquant": {"enabled": True},
        })
        assert cfg.worldquant.enabled is True
        assert cfg.worldquant.operators is None


# ═══════════════════════════════════════════════════════════════════
# A7: ConfigManager.migrate_config()
# ═══════════════════════════════════════════════════════════════════


class TestA7MigrateConfig:
    """ConfigManager.migrate_config() 舊格式遷移"""

    def test_migrate_aggregators_list_to_dict(self):
        raw = {
            "rolling_aggregation": {
                "aggregators": ["mean", "std", "rank"],
            }
        }
        result = ConfigManager.migrate_config(raw)
        agg = result["rolling_aggregation"]["aggregators"]
        assert isinstance(agg, dict)
        assert agg["mean"]["enabled"] is True
        assert len(agg) == 3

    def test_migrate_cross_sectional_features_list_to_dict(self):
        raw = {
            "cross_sectional": {
                "features": ["relative_price", "beta"],
            }
        }
        result = ConfigManager.migrate_config(raw)
        feats = result["cross_sectional"]["features"]
        assert isinstance(feats, dict)
        assert feats["relative_price"]["enabled"] is True

    def test_migrate_microstructure_enabled_features(self):
        raw = {
            "atomic_indicators": {
                "microstructure": {
                    "enabled": True,
                    "enabled_features": ["amihud", "vpin"],
                }
            }
        }
        result = ConfigManager.migrate_config(raw)
        ms = result["atomic_indicators"]["microstructure"]
        assert "features" in ms
        assert ms["features"]["amihud"]["enabled"] is True
        assert ms["features"]["vpin"]["enabled"] is True

    def test_migrate_preserves_new_format(self):
        """新格式不被二次轉換"""
        raw = {
            "rolling_aggregation": {
                "aggregators": {"mean": {"enabled": True}, "std": {"enabled": False}},
            },
            "cross_sectional": {
                "features": {"beta": {"enabled": True}},
            },
        }
        result = ConfigManager.migrate_config(raw)
        assert result["rolling_aggregation"]["aggregators"]["mean"]["enabled"] is True
        assert result["rolling_aggregation"]["aggregators"]["std"]["enabled"] is False

    def test_migrate_microstructure_enabled_features_all(self):
        """enabled_features='all' 且無 features dict → 不遷移，保持 'all'"""
        raw = {
            "atomic_indicators": {
                "microstructure": {
                    "enabled": True,
                    "enabled_features": "all",
                }
            }
        }
        result = ConfigManager.migrate_config(raw)
        ms = result["atomic_indicators"]["microstructure"]
        assert "features" not in ms

    def test_migrate_microstructure_features_already_present(self):
        """features dict 已存在 → 不覆蓋"""
        raw = {
            "atomic_indicators": {
                "microstructure": {
                    "enabled": True,
                    "enabled_features": ["amihud"],
                    "features": {"vpin": {"enabled": True}},
                }
            }
        }
        result = ConfigManager.migrate_config(raw)
        ms = result["atomic_indicators"]["microstructure"]
        # features 已存在，不會被 enabled_features 覆蓋
        assert ms["features"] == {"vpin": {"enabled": True}}


# ═══════════════════════════════════════════════════════════════════
# A8: FeatureFactory filter helpers (unit-level)
# ═══════════════════════════════════════════════════════════════════


class TestA8FilterHelpers:
    """FeatureFactory centralized filter helpers"""

    def test_filter_category_config_all_enabled(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        cat = CategoryConfig(
            enabled=True,
            indicators=[
                IndicatorDef(name="EMA", enabled=True),
                IndicatorDef(name="SMA", enabled=True),
            ],
        )
        result = FeatureFactory._filter_category_config(cat)
        assert result is not None
        assert len(result["indicators"]) == 2

    def test_filter_category_config_partial(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        cat = CategoryConfig(
            enabled=True,
            indicators=[
                IndicatorDef(name="EMA", enabled=True),
                IndicatorDef(name="SMA", enabled=False),
                IndicatorDef(name="WMA", enabled=True),
            ],
        )
        result = FeatureFactory._filter_category_config(cat)
        assert result is not None
        names = [i["name"] for i in result["indicators"]]
        assert names == ["EMA", "WMA"]

    def test_filter_category_config_all_disabled(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        cat = CategoryConfig(
            enabled=True,
            indicators=[
                IndicatorDef(name="EMA", enabled=False),
                IndicatorDef(name="SMA", enabled=False),
            ],
        )
        result = FeatureFactory._filter_category_config(cat)
        assert result is None

    def test_filter_advanced_config_with_features(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        ms = MicrostructureConfig(
            enabled=True,
            features={
                "amihud": AdvancedFeatureItemConfig(enabled=True),
                "kyle_lambda": AdvancedFeatureItemConfig(enabled=False),
                "vpin": AdvancedFeatureItemConfig(enabled=True),
            },
        )
        result = FeatureFactory._filter_advanced_config(ms)
        assert result["enabled_features"] == ["amihud", "vpin"]

    def test_filter_advanced_config_empty_features(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        ms = MicrostructureConfig(enabled=True)
        result = FeatureFactory._filter_advanced_config(ms)
        # features 為空時不覆蓋 enabled_features
        assert "enabled_features" in result
        assert result["enabled_features"] == "all"

    def test_filter_rolling_config_dict_aggregators(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        cfg = RollingAggConfig.model_validate({
            "enabled": True,
            "windows": [5],
            "aggregators": {
                "mean": {"enabled": True},
                "std": {"enabled": True},
                "zscore": {"enabled": False},
            },
        })
        result = FeatureFactory._filter_rolling_config(cfg)
        assert isinstance(result["aggregators"], list)
        assert "mean" in result["aggregators"]
        assert "std" in result["aggregators"]
        assert "zscore" not in result["aggregators"]

    def test_filter_operators_config_binary_rules(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        ops = OperatorConfig.model_validate({
            "distance": {"enabled": True},
            "cross": {"enabled": True},
            "momentum": {"enabled": True},
            "ratio": {"enabled": True},
            "binary_signal": {
                "enabled": True,
                "rules": [
                    {"indicator": "RSI", "condition": "> 70", "name_suffix": "OB", "enabled": True},
                    {"indicator": "RSI", "condition": "< 30", "name_suffix": "OS", "enabled": False},
                ],
            },
            "worldquant": {"enabled": True},
        })
        result = FeatureFactory._filter_operators_config(ops)
        bs_rules = result["binary_signal"]["rules"]
        assert len(bs_rules) == 1
        assert bs_rules[0]["name_suffix"] == "OB"

    def test_filter_operators_config_worldquant_operators(self):
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        ops = OperatorConfig.model_validate({
            "distance": {"enabled": True},
            "cross": {"enabled": True},
            "momentum": {"enabled": True},
            "ratio": {"enabled": True},
            "binary_signal": {"enabled": True},
            "worldquant": {
                "enabled": True,
                "operators": {
                    "ts_argmax": {"enabled": True},
                    "ts_corr": {"enabled": False},
                    "decay_linear": {"enabled": True},
                },
            },
        })
        result = FeatureFactory._filter_operators_config(ops)
        wq_ops = result["worldquant"]["operators"]
        assert isinstance(wq_ops, list)
        assert "ts_argmax" in wq_ops
        assert "decay_linear" in wq_ops
        assert "ts_corr" not in wq_ops

    def test_filter_operators_config_worldquant_none(self):
        """operators 為 None → 移除讓 Engine 用預設值"""
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        ops = OperatorConfig()
        result = FeatureFactory._filter_operators_config(ops)
        assert "operators" not in result.get("worldquant", {})


# ═══════════════════════════════════════════════════════════════════
# A9: End-to-end backward compatibility
# ═══════════════════════════════════════════════════════════════════


class TestA9BackwardCompatibility:
    """舊 config 格式不修改直接載入"""

    def test_old_yaml_loads_without_error(self):
        """既有 scan_config.yaml 可正常載入"""
        cm = ConfigManager()
        config = cm.get_merged_config()
        assert isinstance(config, FactoryConfig)

    def test_old_format_full_roundtrip(self):
        """舊格式 dict → FactoryConfig → model_dump → FactoryConfig"""
        old = {
            "version": "2.2",
            "global": {},
            "data_sources": {},
            "timeframes": {},
            "atomic_indicators": {
                "trend": {
                    "enabled": True,
                    "indicators": [{"name": "EMA", "periods": [21, 55]}],
                }
            },
            "operators": {
                "distance": {"enabled": True},
                "cross": {"enabled": True},
                "momentum": {"enabled": True},
                "ratio": {"enabled": True},
                "binary_signal": {"enabled": True},
                "worldquant": {"enabled": True},
            },
            "rolling_aggregation": {
                "enabled": True,
                "aggregators": ["mean", "std"],
            },
            "lag_features": {},
            "cross_sectional": {
                "features": ["relative_price", "beta"],
            },
            "meta_features": {},
            "labels": {},
        }
        config = FactoryConfig.model_validate(ConfigManager.migrate_config(copy.deepcopy(old)))
        assert config.atomic_indicators.trend.indicators[0].enabled is True
        assert config.rolling_aggregation.aggregators["mean"].enabled is True
        assert config.cross_sectional.features["relative_price"].enabled is True

        # Roundtrip
        dumped = config.model_dump(by_alias=True)
        config2 = FactoryConfig.model_validate(dumped)
        assert config2.atomic_indicators.trend.indicators[0].name == "EMA"

    def test_three_layer_merge_with_new_fields(self):
        """API override 可使用新 enabled 欄位"""
        cm = ConfigManager()
        config = cm.get_merged_config(api_override={
            "atomic_indicators": {
                "trend": {
                    "indicators": [
                        {"name": "EMA", "enabled": False},
                        {"name": "SMA", "enabled": True},
                    ]
                }
            },
            "rolling_aggregation": {
                "aggregators": {
                    "mean": {"enabled": True},
                    "std": {"enabled": False},
                }
            },
        })
        # trend indicators 的 enabled 設定生效
        trend = config.atomic_indicators.trend
        ema = next(i for i in trend.indicators if i.name == "EMA")
        sma = next(i for i in trend.indicators if i.name == "SMA")
        assert ema.enabled is False
        assert sma.enabled is True

        # Aggregators 的 enabled 設定生效
        assert config.rolling_aggregation.aggregators["mean"].enabled is True
        assert config.rolling_aggregation.aggregators["std"].enabled is False

    def test_edge_case_all_indicators_disabled(self):
        """Category enabled=true 但所有 indicator enabled=false → 等同 category disabled"""
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        cat = CategoryConfig(
            enabled=True,
            indicators=[
                IndicatorDef(name="EMA", enabled=False),
                IndicatorDef(name="SMA", enabled=False),
            ],
        )
        result = FeatureFactory._filter_category_config(cat)
        assert result is None  # 無 enabled 指標 → None，不建立 Engine

    def test_edge_case_empty_indicators_list(self):
        """indicators 為空 → 回傳 None"""
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        cat = CategoryConfig(enabled=True, indicators=[])
        result = FeatureFactory._filter_category_config(cat)
        assert result is None
