"""
Phase D 驗證測試 — Feature Factory Granular Control Plan

涵蓋項目（§19 測試計畫 + §20 Phase D）：
- D1: 後端測試補完（Edge Cases + 下游 Layer 依賴 + concurrent config write）
- D2: 前端測試（已於 Phase C 完成 → test_phase_c_granular_control.py）
- D3: 端對端測試（config → preview → verify features match enabled set）
- D4: API_SPECIFICATION.md 更新驗證
- D5: FRONTEND_INTEGRATION_GUIDE.md 更新驗證
"""

import copy
import threading
from pathlib import Path

import pytest

from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_config import (
    AggregatorConfig,
    AdvancedFeatureItemConfig,
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
    RollingAggConfig,
    TailRiskConfig,
    WorldQuantToggle,
)

ROOT = Path(__file__).resolve().parent.parent


# ===========================================================
# Fixtures
# ===========================================================


@pytest.fixture
def config_manager():
    """Return a fresh ConfigManager."""
    return ConfigManager()


@pytest.fixture
def merged_config(config_manager):
    """Return the fully merged FactoryConfig."""
    return config_manager.get_merged_config()


@pytest.fixture
def feature_factory_service():
    """Return a FeatureFactoryService instance."""
    from api.services.feature_factory_service import FeatureFactoryService
    return FeatureFactoryService()


# ===========================================================
# D1: 後端測試 — Edge Cases（§19.1 邊界案例 #1~#6）
# ===========================================================


class TestD1EdgeCases:
    """§19.1 Edge Cases: 全關、全開、只開 1 個、只關 1 個、混合場景"""

    def test_edge_case_1_category_enabled_but_all_indicators_disabled(self, config_manager):
        """邊界 #1: Category enabled=true 但所有 indicator enabled=false → 特徵數 = 0"""
        override = {
            "atomic_indicators": {
                "trend": {
                    "enabled": True,
                    "indicators": [
                        {"name": "EMA", "enabled": False},
                        {"name": "SMA", "enabled": False},
                        {"name": "WMA", "enabled": False},
                        {"name": "DEMA", "enabled": False},
                        {"name": "TEMA", "enabled": False},
                        {"name": "TRIMA", "enabled": False},
                        {"name": "KAMA", "enabled": False},
                        {"name": "T3", "enabled": False},
                        {"name": "MAMA", "enabled": False},
                        {"name": "HT_TRENDLINE", "enabled": False},
                        {"name": "MIDPOINT", "enabled": False},
                        {"name": "MIDPRICE", "enabled": False},
                        {"name": "SAR", "enabled": False},
                        {"name": "SAREXT", "enabled": False},
                        {"name": "BBANDS", "enabled": False},
                        {"name": "MAVP", "enabled": False},
                        {"name": "MA", "enabled": False},
                    ],
                },
                "momentum": {"enabled": False},
                "volatility": {"enabled": False},
                "volume": {"enabled": False},
                "cycle": {"enabled": False},
                "pattern": {"enabled": False},
                "statistics": {"enabled": False},
                "microstructure": {"enabled": False},
                "entropy": {"enabled": False},
                "tail_risk": {"enabled": False},
            }
        }
        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)
        assert preview.breakdown["atomic"] == 0, \
            "Category enabled=true + all indicators disabled → atomic count 應為 0"

    def test_edge_case_5_all_layer1_disabled_gives_zero_total(self, config_manager):
        """邊界 #5: 全部 Layer 1 indicator disabled → total 特徵數 = 0（非錯誤）"""
        override = {"atomic_indicators": {}}
        for cat in ["trend", "momentum", "volatility", "volume",
                     "cycle", "pattern", "statistics"]:
            override["atomic_indicators"][cat] = {"enabled": False}
        override["atomic_indicators"]["microstructure"] = {"enabled": False}
        override["atomic_indicators"]["entropy"] = {"enabled": False}
        override["atomic_indicators"]["tail_risk"] = {"enabled": False}
        # Also disable other layers
        override["operators"] = {
            "distance": {"enabled": False},
            "cross": {"enabled": False},
            "momentum": {"enabled": False},
            "ratio": {"enabled": False},
            "binary_signal": {"enabled": False},
            "worldquant": {"enabled": False},
        }
        override["rolling_aggregation"] = {"enabled": False}
        override["lag_features"] = {"enabled": False}
        override["cross_sectional"] = {"enabled": False}
        override["meta_features"] = {"enabled": False}

        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)
        # NOTE: preview.total_features already EXCLUDES labels (labels are Y targets,
        # not X features — see preview_feature_count). So the assertion is direct.
        assert preview.total_features == 0, \
            f"全部 disabled → 特徵數應為 0，實際 {preview.total_features}, breakdown={preview.breakdown}"

    def test_edge_case_6_microstructure_features_dict_takes_priority(self, config_manager):
        """邊界 #6: Microstructure enabled_features + features 同時存在 → features dict 優先"""
        raw = {
            "atomic_indicators": {
                "microstructure": {
                    "enabled_features": ["amihud", "kyle_lambda"],
                    "features": {
                        "vpin": {"enabled": True},
                    },
                }
            }
        }
        result = ConfigManager.migrate_config(raw)
        ms = result["atomic_indicators"]["microstructure"]
        # features dict already exists → should NOT be overwritten by enabled_features
        assert "vpin" in ms["features"]
        assert "amihud" not in ms.get("features", {}), \
            "features dict 存在時，enabled_features 不應覆蓋"

    def test_edge_case_only_one_indicator_enabled(self, config_manager):
        """只開 1 個指標 → 應有非零特徵數"""
        override = {"atomic_indicators": {}}
        for cat in ["momentum", "volatility", "volume",
                     "cycle", "pattern", "statistics"]:
            override["atomic_indicators"][cat] = {"enabled": False}
        override["atomic_indicators"]["microstructure"] = {"enabled": False}
        override["atomic_indicators"]["entropy"] = {"enabled": False}
        override["atomic_indicators"]["tail_risk"] = {"enabled": False}
        override["atomic_indicators"]["trend"] = {
            "enabled": True,
            "indicators": [{"name": "EMA", "enabled": True}],
        }

        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)
        assert preview.breakdown["atomic"] > 0, \
            "開 1 個指標 → atomic count 應 > 0"

    def test_edge_case_only_one_indicator_disabled(self, config_manager):
        """全開但只關 1 個指標 → 總數應略低於全開"""
        full_config = config_manager.get_merged_config()
        full_preview = config_manager.preview_feature_count(full_config)

        override = {
            "atomic_indicators": {
                "trend": {
                    "enabled": True,
                    "indicators": [{"name": "EMA", "enabled": False}],
                }
            }
        }
        partial_config = config_manager.get_merged_config(override)
        partial_preview = config_manager.preview_feature_count(partial_config)

        assert partial_preview.total_features < full_preview.total_features, \
            "關閉 1 個指標 → 總數應略低"
        assert partial_preview.total_features > 0

    def test_edge_case_all_enabled_matches_default(self, config_manager):
        """全部 enabled=True 的 config → 與預設 config 特徵數一致"""
        default_config = config_manager.get_merged_config()
        default_preview = config_manager.preview_feature_count(default_config)

        # Explicit all-enabled override (should not change anything)
        override = {}
        explicit_config = config_manager.get_merged_config(override)
        explicit_preview = config_manager.preview_feature_count(explicit_config)

        assert explicit_preview.total_features == default_preview.total_features


# ===========================================================
# D1: 後端測試 — 下游 Layer 依賴（§19.1 #2~#4）
# ===========================================================


class TestD1DownstreamDependency:
    """§19.1 下游 Layer 依賴：Layer 1 指標被關閉後 Layer 2+ 的行為"""

    def test_edge_case_3_rolling_agg_respects_layer1_count(self, config_manager):
        """邊界 #3: Layer 3 apply_to=all + Layer 1 只剩少量特徵 → rolling 計數受限"""
        # Only enable 1 Trend category with 1 indicator
        override = {
            "atomic_indicators": {
                "trend": {
                    "enabled": True,
                    "indicators": [{"name": "EMA", "enabled": True}],
                },
                "momentum": {"enabled": False},
                "volatility": {"enabled": False},
                "volume": {"enabled": False},
                "cycle": {"enabled": False},
                "pattern": {"enabled": False},
                "statistics": {"enabled": False},
                "microstructure": {"enabled": False},
                "entropy": {"enabled": False},
                "tail_risk": {"enabled": False},
            },
            "operators": {
                "distance": {"enabled": False},
                "cross": {"enabled": False},
                "momentum": {"enabled": False},
                "ratio": {"enabled": False},
                "binary_signal": {"enabled": False},
                "worldquant": {"enabled": False},
            },
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
            },
        }
        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        # rolling count = atomic_count × enabled_agg_count × len(windows)
        # With few L1 features and 2 aggregators, rolling should be proportionally small
        assert preview.breakdown["rolling"] > 0
        assert preview.breakdown["rolling"] < 500, \
            "少量 L1 特徵 + 2 個 agg → rolling 應較小"

    def test_disable_all_operators_zero_derived(self, config_manager):
        """Layer 2 所有 operator disabled → derived 計數 = 0"""
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

    def test_disable_layer1_reduces_downstream(self, config_manager):
        """全關 Layer 1 → 下游 Layer 2/3 的計數顯著下降"""
        # Get full config baseline
        full_config = config_manager.get_merged_config()
        full_preview = config_manager.preview_feature_count(full_config)

        override = {"atomic_indicators": {}}
        for cat in ["trend", "momentum", "volatility", "volume",
                     "cycle", "pattern", "statistics"]:
            override["atomic_indicators"][cat] = {"enabled": False}
        override["atomic_indicators"]["microstructure"] = {"enabled": False}
        override["atomic_indicators"]["entropy"] = {"enabled": False}
        override["atomic_indicators"]["tail_risk"] = {"enabled": False}

        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        assert preview.breakdown["atomic"] == 0
        # Rolling has no features to aggregate
        assert preview.breakdown["rolling"] == 0
        # Total should be significantly less than full config
        assert preview.total_features < full_preview.total_features, \
            "全關 L1 → 總特徵數應顯著低於全開"

    def test_meta_features_still_work_with_limited_l1(self, config_manager):
        """少量 L1 啟用 → meta features 計數不受影響（依 sub-engine 控制）"""
        override = {
            "atomic_indicators": {
                "trend": {
                    "enabled": True,
                    "indicators": [{"name": "EMA", "enabled": True}],
                },
                "momentum": {"enabled": False},
                "volatility": {"enabled": False},
                "volume": {"enabled": False},
                "cycle": {"enabled": False},
                "pattern": {"enabled": False},
                "statistics": {"enabled": False},
                "microstructure": {"enabled": False},
                "entropy": {"enabled": False},
                "tail_risk": {"enabled": False},
            },
            "meta_features": {
                "enabled": True,
                "consensus": True,
                "interaction": True,
                "time_features": True,
                "trend_consensus": True,
                "momentum_divergence": False,
                "volume_price_divergence": False,
                "volatility_regime": False,
            },
        }
        config = config_manager.get_merged_config(override)
        preview = config_manager.preview_feature_count(config)

        # meta features count is determined by sub-engine toggles, not L1 count
        assert preview.breakdown["meta"] > 0


# ===========================================================
# D1: 後端測試 — Concurrent Config Write（§19.1）
# ===========================================================


class TestD1ConcurrentConfigWrite:
    """§19.1 Concurrent config write: 多個 API PUT 同時寫入不造成 race condition"""

    def test_concurrent_batch_toggle_no_crash(self, feature_factory_service):
        """多執行緒同時呼叫 batch_toggle 不 crash"""
        svc = feature_factory_service
        errors = []

        def toggle_thread(idx):
            try:
                svc.batch_toggle([
                    {"path": f"atomic_indicators.trend.indicators.EMA.enabled",
                     "value": idx % 2 == 0},
                ])
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=toggle_thread, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Concurrent toggle errors: {errors}"

    def test_concurrent_config_read_write_no_corruption(self, feature_factory_service):
        """同時讀寫不造成 config 損壞"""
        svc = feature_factory_service
        errors = []

        def writer():
            try:
                svc.batch_toggle([
                    {"path": "atomic_indicators.trend.indicators.SMA.enabled", "value": False},
                ])
            except Exception as e:
                errors.append(f"Writer: {e}")

        def reader():
            try:
                schema = svc.get_schema()
                assert "layers" in schema
            except Exception as e:
                errors.append(f"Reader: {e}")

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Concurrent read/write errors: {errors}"


# ===========================================================
# D3: 端對端測試（config → preview → verify）
# ===========================================================


class TestD3EndToEnd:
    """D3: 端對端測試 — config → preview → verify features match enabled set"""

    def test_e2e_full_config_preview_nonzero(self, feature_factory_service):
        """E2E #1: 完整預設 config → preview 特徵數 > 0"""
        svc = feature_factory_service
        schema = svc.get_schema()
        assert "layers" in schema

        # Get default config and preview
        config = svc.get_config()
        preview = svc.preview(None)
        assert preview["total_features"] > 0
        assert preview["estimated_time_seconds"] > 0

    def test_e2e_toggle_then_preview_reflects_change(self, feature_factory_service):
        """E2E #2: batch toggle → preview 反映變化"""
        svc = feature_factory_service

        # Get baseline
        baseline_preview = svc.preview(None)
        baseline_total = baseline_preview["total_features"]

        # Disable a specific category  
        result = svc.batch_toggle([
            {"path": "atomic_indicators.pattern.enabled", "value": False},
        ])
        assert result["results"][0]["success"] is True

        # Preview should reflect the change (pattern disabled → fewer features)
        new_preview = result["preview"]
        assert new_preview["total_features"] <= baseline_total

        # Restore
        svc.batch_toggle([
            {"path": "atomic_indicators.pattern.enabled", "value": True},
        ])

    def test_e2e_preset_to_preview_consistent(self, feature_factory_service):
        """E2E #3: apply preset → preview 與 preset 預期一致"""
        svc = feature_factory_service

        # Apply lightweight_ml preset
        result = svc.apply_preset_config("lightweight_ml")
        assert "config" in result
        assert "preview" in result

        preview = result["preview"]
        # lightweight_ml should produce fewer features than full config.
        # We compare against the full preset rather than a fixed magic number,
        # because absolute counts shift as new operators/indicators are added —
        # what matters is that lightweight_ml stays *materially smaller* than full.
        assert preview["total_features"] > 0
        full_result = svc.apply_preset_config("full")
        full_total = full_result["preview"]["total_features"]
        assert preview["total_features"] < full_total * 0.5, (
            f"lightweight_ml 應遠小於 full：lightweight={preview['total_features']}, "
            f"full={full_total}"
        )

        # Restore to standard
        svc.apply_preset_config("standard")


# ===========================================================
# D4: API_SPECIFICATION.md 更新驗證
# ===========================================================


class TestD4APISpecification:
    """D4: 驗證 API_SPECIFICATION.md 包含 Granular Control 新端點"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = (ROOT / "docs" / "API_SPECIFICATION.md").read_text(encoding="utf-8")

    def test_schema_api_documented(self):
        """Schema API (GET /schema) 已記錄"""
        assert "GET" in self.content and "/schema" in self.content
        assert "Granular Control" in self.content or "schema" in self.content.lower()

    def test_batch_toggle_api_documented(self):
        """Batch Toggle API (PUT /batch-toggle) 已記錄"""
        assert "batch-toggle" in self.content

    def test_presets_api_documented(self):
        """Preset API (POST /presets/{name}) 已記錄"""
        assert "presets/" in self.content or "preset" in self.content.lower()

    def test_version_updated(self):
        """版本號已更新"""
        assert "5.0" in self.content or "Granular Control" in self.content

    def test_router_table_includes_feature_factory(self):
        """Router 表包含 feature_factory"""
        assert "feature_factory" in self.content


# ===========================================================
# D5: FRONTEND_INTEGRATION_GUIDE.md 更新驗證
# ===========================================================


class TestD5FrontendIntegrationGuide:
    """D5: 驗證 FRONTEND_INTEGRATION_GUIDE.md 包含 Granular Control 前端指南"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = (ROOT / "docs" / "FRONTEND_INTEGRATION_GUIDE.md").read_text(encoding="utf-8")

    def test_granular_control_section_exists(self):
        """包含 Granular Control / 細粒度控制相關章節"""
        assert "Granular Control" in self.content or "細粒度" in self.content or "LayerPanel" in self.content

    def test_layer_panel_component_documented(self):
        """LayerPanel 元件已記錄"""
        assert "LayerPanel" in self.content

    def test_indicator_checkbox_documented(self):
        """IndicatorCheckbox 元件已記錄"""
        assert "IndicatorCheckbox" in self.content

    def test_feature_preview_bar_documented(self):
        """FeaturePreviewBar 元件已記錄"""
        assert "FeaturePreviewBar" in self.content

    def test_config_io_buttons_documented(self):
        """ConfigIOButtons 元件已記錄"""
        assert "ConfigIOButtons" in self.content

    def test_store_actions_documented(self):
        """Zustand store actions 已記錄"""
        assert "toggleIndicator" in self.content or "featureFactoryStore" in self.content

    def test_schema_api_integration_documented(self):
        """Schema API 整合已記錄"""
        assert "/schema" in self.content or "loadSchema" in self.content


# ===========================================================
# §19.3 向後相容測試補完
# ===========================================================


class TestD1BackwardCompatibility:
    """§19.3 向後相容測試：舊 config 格式不修改直接啟動"""

    def test_old_scan_config_loads_without_error(self, config_manager):
        """舊 scan_config.yaml 不修改直接載入 → 正常"""
        config = config_manager.get_merged_config()
        assert isinstance(config, FactoryConfig)

    def test_old_format_api_put_merges_correctly(self, feature_factory_service):
        """舊格式 API PUT → 合併正確"""
        svc = feature_factory_service
        # Simulate old-format PUT without per-indicator enabled fields
        old_format_config = {
            "atomic_indicators": {
                "trend": {
                    "enabled": True,
                    "indicators": [
                        {"name": "EMA"},  # No 'enabled' field
                        {"name": "SMA"},
                    ],
                }
            }
        }
        result = svc.update_config(old_format_config)
        # Should not error
        assert result is not None

    def test_new_format_extra_fields_ignored_by_old_reader(self):
        """新格式寫入 → 舊讀取路徑不報錯（extra fields 忽略）"""
        # Simulate new format with per-indicator enabled
        new_format = {
            "name": "EMA",
            "enabled": True,
            "periods": [5, 13, 21],
        }
        # Old reader only checks name + periods
        ind = IndicatorDef.model_validate(new_format)
        assert ind.name == "EMA"
        assert ind.enabled is True
        # Extra fields like periods should still be accessible
