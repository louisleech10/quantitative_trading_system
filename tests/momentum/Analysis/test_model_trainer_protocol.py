from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from momentum.core.protocols import IModelTrainer


def _make_data(n_samples: int = 120, n_features: int = 10):
    rng = np.random.default_rng(123)
    X = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)),
        columns=[f"feature_{i}" for i in range(n_features)],
    )
    y = ((X["feature_0"] + X["feature_1"] * 0.2 - X["feature_2"] * 0.1) > 0).astype(int).to_numpy()
    return X, y, X.columns.tolist()


def test_lightgbm_and_xgboost_are_model_trainer_protocol():
    assert isinstance(LightGBMAnalyzer(), IModelTrainer)
    assert isinstance(XGBoostAnalyzer(), IModelTrainer)


def test_lightgbm_protocol_methods_smoke():
    X, y, feature_names = _make_data()
    trainer = LightGBMAnalyzer(params={"n_estimators": 20, "num_leaves": 15})

    trainer.train_model(X, y, feature_names=feature_names, cv_folds=3)
    proba = trainer.predict_proba(X)
    fi = trainer.get_feature_importance(top_n=5)

    assert proba.shape == (len(X), 2)
    assert len(fi) == 5
    assert trainer.get_model_type() == "lightgbm"
    assert isinstance(trainer.get_model_params(), dict)


def test_xgboost_protocol_methods_smoke():
    X, y, feature_names = _make_data()
    trainer = XGBoostAnalyzer(params={"n_estimators": 20, "max_depth": 3})

    trainer.train_model(X, y, feature_names=feature_names, cv_folds=3)
    proba = trainer.predict_proba(X)
    fi = trainer.get_feature_importance(top_n=5)

    assert proba.shape == (len(X), 2)
    assert len(fi) == 5
    assert trainer.get_model_type() == "xgboost"
    assert isinstance(trainer.get_model_params(), dict)
