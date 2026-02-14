import pytest

from momentum.Analysis.model_config import ModelConfigManager


def test_from_natural_language_overfitting_and_validation():
    manager = ModelConfigManager()

    config = manager.from_natural_language("用 lightgbm，防止過擬合，嚴格驗證")

    assert config["engine"] == "lightgbm"
    assert config["boosting_type"] == "dart"
    assert config["cv_folds"] == 10
    assert config["early_stopping_rounds"] == 50


def test_from_natural_language_no_match_returns_empty_dict():
    manager = ModelConfigManager()
    assert manager.from_natural_language("完全不相關指令") == {}


def test_to_optuna_space_lightgbm_contains_10_parameters():
    manager = ModelConfigManager()

    space = manager.to_optuna_space("lightgbm")

    assert len(space) == 10
    assert "num_leaves" in space


def test_validate_config_boundary_and_combination_warning():
    manager = ModelConfigManager()

    messages = manager.validate_config(
        {"num_leaves": 300, "min_child_samples": 5},
        "lightgbm",
    )

    assert any("num_leaves 必須在 2-256 之間" in msg for msg in messages)
    assert any("WARNING:" in msg and "容易過擬合" in msg for msg in messages)


def test_validate_config_legal_params_returns_empty_errors():
    manager = ModelConfigManager()

    messages = manager.validate_config({"num_leaves": 31, "learning_rate": 0.05}, "lightgbm")

    assert messages == []


def test_from_dict_raises_value_error_for_invalid_config():
    manager = ModelConfigManager()

    with pytest.raises(ValueError, match="num_leaves 必須在 2-256 之間"):
        manager.from_dict({"engine": "lightgbm", "num_leaves": 300})