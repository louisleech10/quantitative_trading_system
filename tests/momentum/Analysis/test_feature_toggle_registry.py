from __future__ import annotations

from pathlib import Path

import pytest

from momentum.Analysis.feature_toggle_registry import DifficultyLevel, FeatureToggle, FeatureToggleRegistry


@pytest.fixture
def registry() -> FeatureToggleRegistry:
    return FeatureToggleRegistry()


def test_registry_default_counts(registry: FeatureToggleRegistry):
    assert len(registry.get_by_difficulty(DifficultyLevel.ESSENTIAL)) == 4
    assert len(registry.get_by_difficulty(DifficultyLevel.INTERMEDIATE)) >= 8
    assert len(registry.get_by_difficulty(DifficultyLevel.ADVANCED)) >= 8


def test_T1_locked_feature_cannot_disable(registry: FeatureToggleRegistry):
    with pytest.raises(ValueError, match="不可關閉"):
        registry.set_enabled("F-001", False)


def test_T2_disable_upstream_cascade(registry: FeatureToggleRegistry):
    # 先將 F-001 解鎖，模擬上游被關閉場景
    registry._toggles["F-001"].is_locked = False

    cascaded = registry.set_enabled("F-001", False)

    assert "F-002" in cascaded
    assert registry._toggles["F-001"].is_enabled is False
    assert registry._toggles["F-002"].is_enabled is False
    assert registry._toggles["F-101"].is_enabled is False


def test_T3_enable_dependency_not_satisfied(registry: FeatureToggleRegistry):
    registry._toggles["F-001"].is_locked = False
    registry.set_enabled("F-001", False)

    with pytest.raises(ValueError, match="需先啟用"):
        registry.set_enabled("F-108", True)


def test_T4_apply_essential_only(registry: FeatureToggleRegistry):
    registry.apply_preset("essential-only")

    for toggle in registry.get_all_features():
        if toggle.difficulty == DifficultyLevel.ESSENTIAL:
            assert toggle.is_enabled is True
        else:
            assert toggle.is_enabled is False


def test_T5_apply_full(registry: FeatureToggleRegistry):
    registry.apply_preset("full")

    assert all(item.is_enabled for item in registry.get_all_features())


def test_T6_unknown_feature_id(registry: FeatureToggleRegistry):
    with pytest.raises(ValueError, match="未知功能 ID"):
        registry.set_enabled("UNKNOWN", True)


def test_T7_invalid_yaml_fallback_to_recommended(tmp_path: Path):
    broken_yaml = tmp_path / "broken.yaml"
    broken_yaml.write_text("feature_toggles: [", encoding="utf-8")

    registry = FeatureToggleRegistry(yaml_path=str(broken_yaml))

    assert registry._toggles["F-001"].is_enabled is True
    assert registry._toggles["F-005"].is_enabled is True
    assert registry._toggles["F-011"].is_enabled is False


def test_T8_detect_cycle_dependency():
    registry = FeatureToggleRegistry()
    registry._toggles.clear()
    registry.register(
        FeatureToggle(
            feature_id="A",
            name="A",
            description="A",
            difficulty=DifficultyLevel.INTERMEDIATE,
            dependencies=["B"],
        )
    )
    registry.register(
        FeatureToggle(
            feature_id="B",
            name="B",
            description="B",
            difficulty=DifficultyLevel.INTERMEDIATE,
            dependencies=["A"],
        )
    )

    with pytest.raises(ValueError, match="循環依賴"):
        registry._ensure_no_cycles()


def test_register_duplicate_feature_id(registry: FeatureToggleRegistry):
    with pytest.raises(ValueError, match="重複 feature_id"):
        registry.register(
            FeatureToggle(
                feature_id="F-001",
                name="dup",
                description="dup",
                difficulty=DifficultyLevel.ESSENTIAL,
            )
        )


def test_validate_dependencies_returns_error_when_dependency_disabled(registry: FeatureToggleRegistry):
    registry._toggles["F-001"].is_locked = False
    registry._toggles["F-001"].is_enabled = False
    registry._toggles["F-101"].is_enabled = True

    errors = registry.validate_dependencies()

    assert any("F-101" in item for item in errors)


def test_to_config_dict_contains_presets_and_toggles(registry: FeatureToggleRegistry):
    payload = registry.to_config_dict()

    assert "presets" in payload
    assert "feature_toggles" in payload
    assert "F-001" in payload["feature_toggles"]
