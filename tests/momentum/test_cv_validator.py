"""CV Validator Tests - 交叉驗證器測試"""

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression

from momentum.Analysis.model_validation.cv_validator import CVValidator


def _build_data(n_samples: int = 500, random_state: int = 42):
    X, y = make_classification(
        n_samples=n_samples,
        n_features=6,
        n_informative=4,
        n_redundant=1,
        n_classes=2,
        random_state=random_state,
    )
    X_df = pd.DataFrame(X, columns=[f"f{i}" for i in range(X.shape[1])])
    y_series = pd.Series(y)
    return X_df, y_series


def test_time_series_split_order():
    """時間序列切分不洩漏未來資料"""
    X, y = _build_data()
    validator = CVValidator({"n_splits": 4, "oot_ratio": 0.2})

    splits = validator.time_series_split(X, y, n_splits=4)
    assert len(splits) == 4

    cv_end = int(len(X) * (1 - 0.2))
    for train_idx, val_idx in splits:
        assert train_idx.max() < val_idx.min()
        assert val_idx.max() < cv_end


def test_cv_validate_outputs():
    """驗證 CV 與 OOT 指標輸出"""
    X, y = _build_data()
    model = LogisticRegression(max_iter=1000)
    validator = CVValidator({"n_splits": 4, "oot_ratio": 0.2})

    result = validator.validate(model, X, y)

    assert "cv_auc_mean" in result
    assert "cv_auc_std" in result
    assert "fold_aucs" in result
    assert len(result["fold_aucs"]) == 4
    assert 0.0 <= result["oot_auc"] <= 1.0
    assert 0.0 <= result["oot_precision"] <= 1.0
    assert 0.0 <= result["oot_recall"] <= 1.0
    assert 0.0 <= result["oot_f1"] <= 1.0

    oot_result = validator.get_oot_result()
    assert "auc" in oot_result
    assert "precision" in oot_result


def test_cv_validator_input_errors():
    """輸入邊界條件"""
    validator = CVValidator()
    X = pd.DataFrame()
    y = pd.Series([], dtype=int)

    with pytest.raises(ValueError):
        validator._split_cv_oot(X, y, 0.2)

    X = pd.DataFrame({"f0": [1, 2, 3]})
    y = pd.Series([1, 0])
    with pytest.raises(ValueError):
        validator._split_cv_oot(X, y, 0.2)

    X = pd.DataFrame({"f0": [1, 2, 3, 4]})
    y = pd.Series([1, 0, 1, 0])
    with pytest.raises(ValueError):
        validator._split_cv_oot(X, y, 1.0)

    with pytest.raises(ValueError):
        validator._split_cv_oot(X, y, 0.99)


def test_time_series_split_errors():
    """切分錯誤分支"""
    X = pd.DataFrame({"f0": [1, 2, 3, 4]})
    y = pd.Series([1, 0, 1, 0])
    validator = CVValidator({"oot_ratio": 0.2})

    with pytest.raises(ValueError):
        validator.time_series_split(X, y, n_splits=1)

    X_small = pd.DataFrame({"f0": [1, 2, 3]})
    y_small = pd.Series([1, 0, 1])
    with pytest.raises(ValueError):
        validator.time_series_split(X_small, y_small, n_splits=3)

    with pytest.raises(ValueError):
        validator._time_series_split_on_cv(X_small, n_splits=1)

    with pytest.raises(ValueError):
        validator._time_series_split_on_cv(X_small, n_splits=3)


def test_sort_by_index_and_get_oot_result():
    """索引排序與 OOT 結果預設"""
    X = pd.DataFrame({"f0": [1, 2, 3]}, index=[2, 1, 3])
    y = pd.Series([1, 0, 1], index=[2, 1, 3])
    validator = CVValidator()

    X_sorted, y_sorted = validator._sort_by_index(X, y)
    assert X_sorted.index.is_monotonic_increasing
    assert list(y_sorted.index) == list(X_sorted.index)
    assert validator.get_oot_result() == {}

    X_sorted, y_sorted = validator._sort_by_index(X, [1, 0, 1])
    assert isinstance(y_sorted, pd.Series)


def test_predict_scores_and_auc_branches(monkeypatch):
    """_predict_scores 與 AUC 例外分支"""
    validator = CVValidator()
    X = pd.DataFrame({"f0": [1, 2, 3, 4]})
    y = pd.Series([1, 0, 1, 0])

    class DecisionModel:
        def decision_function(self, X):
            return np.zeros(len(X))

    class PredictModel:
        def predict(self, X):
            return np.ones(len(X))

    assert validator._predict_scores(DecisionModel(), X).shape[0] == len(X)
    assert validator._predict_scores(PredictModel(), X).shape[0] == len(X)

    def fake_auc(*args, **kwargs):
        raise ValueError("fail")

    monkeypatch.setattr(
        "momentum.Analysis.model_validation.cv_validator.roc_auc_score",
        fake_auc,
    )
    assert np.isnan(validator._compute_auc(DecisionModel(), X, y))


def test_validate_single_class_outputs():
    """單一類別時 AUC 為 NaN"""
    X = pd.DataFrame({"f0": [1, 2, 3, 4, 5, 6, 7, 8]})
    y = pd.Series([1] * len(X))
    model = DummyClassifier(strategy="most_frequent")
    validator = CVValidator({"n_splits": 2, "oot_ratio": 0.25})

    result = validator.validate(model, X, y)
    assert np.isnan(result["cv_auc_mean"])
    assert result["overfit_warning"] is False
