"""Case SHAP Tests - 單案例 SHAP 測試"""

import builtins
import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

from momentum.Analysis.model_validation.case_shap import CaseSHAPExplainer


def test_case_shap_explain_single_and_batch():
    """單筆與批次 SHAP 解釋"""
    shap = pytest.importorskip("shap")
    _ = shap

    X, y = make_classification(
        n_samples=200,
        n_features=4,
        n_informative=3,
        n_redundant=0,
        n_classes=2,
        random_state=11,
    )
    feature_names = [f"f{i}" for i in range(X.shape[1])]
    X_df = pd.DataFrame(X, columns=feature_names)
    y_series = pd.Series(y)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_df, y_series)

    explainer = CaseSHAPExplainer()
    single_result = explainer.explain_single(model, X_df.iloc[[0]], feature_names)

    assert "base_value" in single_result
    assert "shap_values" in single_result
    assert len(single_result["shap_values"]) == len(feature_names)

    series_result = explainer.explain_single(model, X_df.iloc[0], feature_names)
    assert len(series_result["shap_values"]) == len(feature_names)

    batch_result = explainer.explain_batch(model, X_df, feature_names, max_samples=50)
    assert "mean_abs_shap" in batch_result
    assert "feature_importance_rank" in batch_result
    assert len(batch_result["mean_abs_shap"]) == len(feature_names)


def test_case_shap_input_errors():
    """X_single 輸入檢查"""
    explainer = CaseSHAPExplainer()
    feature_names = ["f0", "f1"]

    with pytest.raises(ValueError):
        explainer.explain_single(None, pd.DataFrame([[1, 2], [3, 4]]), feature_names)

    with pytest.raises(ValueError):
        explainer.explain_single(None, pd.DataFrame([[1, 2]], columns=["f0", "f2"]), feature_names)

    empty_result = explainer.explain_batch(None, pd.DataFrame(), feature_names)
    assert empty_result == {"mean_abs_shap": {}, "feature_importance_rank": []}


def test_case_shap_predict_scores_branches():
    """_predict_scores 分支覆蓋"""
    explainer = CaseSHAPExplainer()
    X = pd.DataFrame([[1, 2], [3, 4]], columns=["f0", "f1"])

    class ProbaModel:
        def predict_proba(self, X):
            return np.tile([0.4, 0.6], (len(X), 1))

    class DecisionModel:
        def decision_function(self, X):
            return np.zeros(len(X))

    class PredictModel:
        def predict(self, X):
            return np.ones(len(X))

    assert explainer._predict_scores(ProbaModel(), X).shape[0] == len(X)
    assert explainer._predict_scores(DecisionModel(), X).shape[0] == len(X)
    assert explainer._predict_scores(PredictModel(), X).shape[0] == len(X)


def test_case_shap_load_shap_error(monkeypatch):
    """_load_shap 缺少相依套件"""
    explainer = CaseSHAPExplainer()

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "shap":
            raise ImportError("no shap")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError):
        explainer._load_shap()
