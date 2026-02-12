"""OOT Validator Tests - OOT 驗證器測試"""

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

from momentum.Analysis.model_validation.oot_validator import OOTValidator


def _build_data(n_samples: int = 400, random_state: int = 7):
    X, y = make_classification(
        n_samples=n_samples,
        n_features=5,
        n_informative=3,
        n_redundant=1,
        n_classes=2,
        random_state=random_state,
    )
    X_df = pd.DataFrame(X, columns=[f"f{i}" for i in range(X.shape[1])])
    y_series = pd.Series(y)
    return X_df, y_series


def test_split_and_evaluate():
    """OOT 切分與評估"""
    X, y = _build_data()
    validator = OOTValidator(oot_ratio=0.2)

    X_train, X_oot, y_train, y_oot = validator.split_oot(X, y)
    assert len(X_train) + len(X_oot) == len(X)
    assert len(X_oot) == len(y_oot)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    result = validator.evaluate(model, X_oot, y_oot)
    assert 0.0 <= result["auc"] <= 1.0
    assert 0.0 <= result["precision"] <= 1.0
    assert 0.0 <= result["recall"] <= 1.0
    assert 0.0 <= result["f1"] <= 1.0


def test_gap_severity():
    """CV-OOT Gap 嚴重度判斷"""
    validator = OOTValidator()
    gap_info = validator.compute_gap(0.9, 0.6)
    assert gap_info["overfit_warning"] is True
    assert gap_info["severity"] == "severe"

    gap_info = validator.compute_gap(0.95, 0.8)
    assert gap_info["severity"] == "warning"

    gap_info = validator.compute_gap(0.9, 0.85)
    assert gap_info["severity"] == "normal"


def test_oot_split_errors_and_sorting():
    """OOT 切分錯誤與排序"""
    X = pd.DataFrame({"f0": [1, 2, 3]}, index=[2, 1, 3])
    y = pd.Series([1, 0, 1], index=[2, 1, 3])

    with pytest.raises(ValueError):
        OOTValidator(oot_ratio=1.0).split_oot(X, y)

    with pytest.raises(ValueError):
        OOTValidator(oot_ratio=0.99).split_oot(X, y)

    validator = OOTValidator(oot_ratio=0.34)
    X_train, X_oot, y_train, y_oot = validator.split_oot(X, y)
    assert X_train.index.is_monotonic_increasing
    assert y_train.index.is_monotonic_increasing
    assert len(X_oot) > 0

    X_sorted, y_sorted = validator._sort_by_index(X, [1, 0, 1])
    assert isinstance(y_sorted, pd.Series)


def test_predict_scores_and_auc_branches(monkeypatch):
    """predict 分支與 AUC 例外"""
    validator = OOTValidator()
    X = pd.DataFrame({"f0": [1, 2, 3, 4]})

    class DecisionModel:
        def decision_function(self, X):
            return np.zeros(len(X))

    class PredictModel:
        def predict(self, X):
            return np.ones(len(X))

    class ProbaSingleClassModel:
        def predict_proba(self, X):
            return np.ones((len(X), 1))

    scores = validator._predict_scores(DecisionModel(), X)
    assert scores.shape[0] == len(X)

    scores = validator._predict_scores(PredictModel(), X)
    assert scores.shape[0] == len(X)

    scores = validator._predict_scores(ProbaSingleClassModel(), X)
    assert scores.shape[0] == len(X)

    def fake_auc(*args, **kwargs):
        raise ValueError("fail")

    monkeypatch.setattr(
        "momentum.Analysis.model_validation.oot_validator.roc_auc_score",
        fake_auc,
    )
    y = pd.Series([1, 0, 1, 0])
    assert np.isnan(validator._compute_auc(y, np.zeros(len(y))))


def test_auc_single_class():
    """單一類別時 AUC 為 NaN"""
    validator = OOTValidator()
    y = pd.Series([1, 1, 1])
    assert np.isnan(validator._compute_auc(y, np.zeros(len(y))))
