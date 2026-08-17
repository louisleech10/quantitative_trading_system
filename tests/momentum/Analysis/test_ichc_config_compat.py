"""ICHC Task 6.3 — 死配置移除相容測試（REMOVED_KEYS warning＋回歸）。"""

import logging

import pytest

from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config


class TestRemovedKeys:
    def test_schema_no_longer_has_dead_fields(self):
        config = ICConfig()
        assert not hasattr(config.performance, "max_features_for_correlation")
        assert not hasattr(config, "shapley")

    def test_old_config_with_removed_keys_loads_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            config = load_ic_config(
                api_override={
                    "performance": {"max_features_for_correlation": 200},
                    "shapley": {"enabled": False},
                }
            )
        assert isinstance(config, ICConfig)
        removed_warnings = [
            r for r in caplog.records if "ICHC-REMOVED-KEY" in r.getMessage()
        ]
        assert len(removed_warnings) == 2  # 兩個移除鍵各一則
        joined = "\n".join(r.getMessage() for r in removed_warnings)
        assert "performance.max_features_for_correlation" in joined
        assert "shapley" in joined

    def test_unknown_non_removed_key_still_ignored_silently(self, caplog):
        """回歸：非 REMOVED_KEYS 的未知鍵維持現狀 ignore（不爆、不誤警）。"""
        with caplog.at_level(logging.WARNING):
            config = load_ic_config(
                api_override={"totally_unknown_key_zzz": {"x": 1}}
            )
        assert isinstance(config, ICConfig)
        assert not [
            r for r in caplog.records if "ICHC-REMOVED-KEY" in r.getMessage()
        ]

    def test_clean_config_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            load_ic_config()
        assert not [
            r for r in caplog.records if "ICHC-REMOVED-KEY" in r.getMessage()
        ]
