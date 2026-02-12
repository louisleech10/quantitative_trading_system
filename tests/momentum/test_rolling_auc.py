"""Rolling AUC Tests - 滾動 AUC 測試"""

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

from momentum.Analysis.model_validation.rolling_auc import RollingAUCTracker


def test_rolling_auc_compute():
    """滾動 AUC 計算"""
    X, y = make_classification(
        n_samples=400,
        n_features=5,
        n_informative=3,
        n_redundant=1,
        n_classes=2,
        random_state=0,
    )
    X_df = pd.DataFrame(X, columns=[f"f{i}" for i in range(X.shape[1])])
    y_series = pd.Series(y)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_df, y_series)

    tracker = RollingAUCTracker()
    result = tracker.compute(model, X_df, y_series, window=120, stride=60)

    assert len(result["timestamps"]) == len(result["auc_values"])
    assert result["trend"] in {"stable", "declining", "improving"}
    assert len(result["auc_values"]) > 0


def test_rolling_auc_input_errors():
    """參數與長度錯誤"""
    tracker = RollingAUCTracker()
    X = pd.DataFrame({"f0": [1, 2, 3]})
    y = pd.Series([1, 0, 1])

    with pytest.raises(ValueError):
        tracker.compute(None, X, y, window=1, stride=1)

    with pytest.raises(ValueError):
        tracker.compute(None, X, y, window=2, stride=0)

    with pytest.raises(ValueError):
        tracker.compute(None, X, y.iloc[:2], window=2, stride=1)


def test_rolling_auc_branches(monkeypatch):
    """單一類別與 AUC 例外分支"""
    tracker = RollingAUCTracker()
    X = pd.DataFrame({"f0": np.arange(10)})
    y = pd.Series([1] * 10)

    class PredictModel:
        def predict(self, X):
            return np.zeros(len(X))

    result = tracker.compute(PredictModel(), X, y, window=5, stride=5)
    assert all(np.isnan(val) for val in result["auc_values"])

    def fake_auc(*args, **kwargs):
        raise ValueError("fail")

    monkeypatch.setattr(
        "momentum.Analysis.model_validation.rolling_auc.roc_auc_score",
        fake_auc,
    )

    y = pd.Series([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
    result = tracker.compute(PredictModel(), X, y, window=5, stride=5)
    assert np.isnan(result["auc_values"][0])


def test_rolling_auc_helpers():
    """輔助函式覆蓋"""
    tracker = RollingAUCTracker()

    class DecisionModel:
        def decision_function(self, X):
            return np.zeros(len(X))

    class ProbaSingleClassModel:
        def predict_proba(self, X):
            return np.ones((len(X), 1))

    X = pd.DataFrame({"f0": [1, 2, 3]})
    assert tracker._predict_scores(DecisionModel(), X).shape[0] == len(X)
    assert tracker._predict_scores(ProbaSingleClassModel(), X).shape[0] == len(X)

    assert tracker._detect_trend([np.nan]) == "stable"
    assert tracker._detect_trend([0.5, 0.7]) == "improving"
    assert tracker._detect_trend([0.7, 0.5]) == "declining"
    assert tracker._detect_trend([0.5, 0.5005]) == "stable"

    X_dt = pd.DataFrame({"f0": [1, 2]}, index=pd.date_range("2024-01-01", periods=2))
    assert tracker._extract_timestamp(X_dt) == X_dt.index[-1]

    X_ts = pd.DataFrame({"timestamp": [10, 20], "f0": [1, 2]})
    assert tracker._extract_timestamp(X_ts) == 20

    X_idx = pd.DataFrame({"f0": [1, 2]}, index=[5, 6])
    assert tracker._extract_timestamp(X_idx) == 6
