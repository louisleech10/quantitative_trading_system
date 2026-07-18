import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.model_comparison import ModelComparison
from momentum.Analysis.model_types import FeatureImportance, ModelPerformance


class DummyTrainer:
    def __init__(self, model_type: str, probabilities: np.ndarray, cv_auc: float):
        self._model_type = model_type
        self._probabilities = probabilities
        self._cv_auc = cv_auc

    def train_model(self, features, labels, feature_names, *args, **kwargs):
        return ModelPerformance(
            in_sample_train_auc=min(1.0, self._cv_auc + 0.03),
            cv_auc_mean=self._cv_auc,
            cv_auc_std=0.01,
            precision=0.7,
            recall=0.6,
            f1_score=0.65,
            overfitting_score=0.03,
            engine_type=self._model_type,
        )

    def predict_proba(self, features):
        return np.column_stack([1.0 - self._probabilities, self._probabilities])

    def get_feature_importance(self, method="gain", top_n=None):
        base = [
            FeatureImportance(feature_name="f0", importance=0.5, rank=1),
            FeatureImportance(feature_name="f1", importance=0.3, rank=2),
            FeatureImportance(feature_name="f2", importance=0.2, rank=3),
        ]
        return base[:top_n] if top_n is not None else base

    def save_model(self, path: str) -> None:
        return None

    def load_model(self, path: str) -> None:
        return None

    def get_model_type(self) -> str:
        return self._model_type

    def get_model_params(self):
        return {"name": self._model_type}

    def get_native_model(self):
        return self


def _sample_xy():
    X = pd.DataFrame({"f0": [1, 2, 3], "f1": [3, 2, 1], "f2": [0, 1, 0]})
    y = np.array([1, 0, 1])
    return X, y, X.columns.tolist()


def test_model_comparison_train_all_and_compare_report():
    X, y, feature_names = _sample_xy()
    trainers = {
        "lightgbm": DummyTrainer("lightgbm", np.array([0.9, 0.4, 0.55]), 0.82),
        "xgboost": DummyTrainer("xgboost", np.array([0.8, 0.3, 0.45]), 0.79),
    }
    comparison = ModelComparison(trainers)

    performances = comparison.train_all(X, y, feature_names)
    report = comparison.compare()

    assert set(performances.keys()) == {"lightgbm", "xgboost"}
    assert report.recommended_engine == "lightgbm"
    assert 0.0 <= report.consensus_rate <= 1.0
    assert isinstance(report.auc_comparison, dict)


def test_model_comparison_single_engine_report_still_valid():
    X, y, feature_names = _sample_xy()
    comparison = ModelComparison({"lightgbm": DummyTrainer("lightgbm", np.array([0.7, 0.2, 0.8]), 0.8)})

    comparison.train_all(X, y, feature_names)
    report = comparison.compare()

    assert report.consensus_rate == 1.0
    assert report.recommended_engine == "lightgbm"


def test_consensus_predictions_min_confidence_filters_conflicts():
    X, y, feature_names = _sample_xy()
    trainers = {
        "lightgbm": DummyTrainer("lightgbm", np.array([0.9, 0.4, 0.55]), 0.82),
        "xgboost": DummyTrainer("xgboost", np.array([0.8, 0.3, 0.45]), 0.79),
    }
    comparison = ModelComparison(trainers)
    comparison.train_all(X, y, feature_names)

    preds = comparison.consensus_predictions(X, method="min_confidence", threshold=0.5)

    assert preds.tolist() == [1, 0, -1]


def test_consensus_predictions_soft_and_hard_voting():
    X, y, feature_names = _sample_xy()
    trainers = {
        "lightgbm": DummyTrainer("lightgbm", np.array([0.9, 0.4, 0.55]), 0.82),
        "xgboost": DummyTrainer("xgboost", np.array([0.8, 0.3, 0.45]), 0.79),
    }
    comparison = ModelComparison(trainers)
    comparison.train_all(X, y, feature_names)

    soft = comparison.consensus_predictions(X, method="soft_voting", threshold=0.5)
    hard = comparison.consensus_predictions(X, method="hard_voting", threshold=0.5)

    assert soft.tolist() == [1, 0, 1]
    assert hard.tolist() == [1, 0, 1]


def test_consensus_predictions_invalid_method_raises():
    X, y, feature_names = _sample_xy()
    trainers = {
        "lightgbm": DummyTrainer("lightgbm", np.array([0.9, 0.4, 0.55]), 0.82),
        "xgboost": DummyTrainer("xgboost", np.array([0.8, 0.3, 0.45]), 0.79),
    }
    comparison = ModelComparison(trainers)
    comparison.train_all(X, y, feature_names)

    with pytest.raises(ValueError, match="method 僅支援"):
        comparison.consensus_predictions(X, method="unknown")


def test_model_comparison_requires_trainers():
    with pytest.raises(ValueError, match="至少需要一個 trainer"):
        ModelComparison({})