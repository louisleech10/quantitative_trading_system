from __future__ import annotations

import pytest

from momentum.factories import (
    create_model_comparison,
    create_model_config_manager,
    create_model_trainer,
)


def test_create_model_trainer_supports_lightgbm_and_xgboost():
    lightgbm_trainer = create_model_trainer("lightgbm")
    xgboost_trainer = create_model_trainer("xgboost")

    assert lightgbm_trainer.get_model_type() == "lightgbm"
    assert xgboost_trainer.get_model_type() == "xgboost"


def test_create_model_trainer_unknown_engine_raises_error():
    with pytest.raises(ValueError, match="不支援的引擎"):
        create_model_trainer("unknown")


def test_create_model_comparison_uses_default_dual_engines():
    comparison = create_model_comparison()
    trainer_names = set(comparison.trainers.keys())

    assert trainer_names == {"lightgbm", "xgboost"}


def test_create_model_config_manager_returns_instance():
    manager = create_model_config_manager()

    assert manager is not None
    assert hasattr(manager, "to_optuna_space")
