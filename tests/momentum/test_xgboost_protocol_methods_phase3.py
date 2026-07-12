from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from momentum.core.protocols import IModelTrainer

pytestmark = [
    pytest.mark.ic_persist_redirect,
    pytest.mark.usefixtures("ic_persist_redirect"),
]


def _make_binary_data(n_samples: int = 180, n_features: int = 8):
    rng = np.random.default_rng(7)
    X = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)),
        columns=[f"feature_{i}" for i in range(n_features)],
    )
    y = ((X["feature_0"] - X["feature_1"] + 0.2 * X["feature_2"]) > 0).astype(int).to_numpy()
    return X, y, X.columns.tolist()


def test_xgboost_protocol_methods_added():
    """Task 3.3: 新增 7 個方法後應符合 IModelTrainer。"""
    analyzer = XGBoostAnalyzer(params={"n_estimators": 10, "max_depth": 2})
    assert isinstance(analyzer, IModelTrainer)

    X, y, feature_names = _make_binary_data()
    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    proba = analyzer.predict_proba(X)
    fi = analyzer.get_feature_importance(method="gain", top_n=3)

    assert proba.shape == (len(X), 2)
    assert len(fi) == 3
    assert analyzer.get_model_type() == "xgboost"
    assert isinstance(analyzer.get_model_params(), dict)
    assert analyzer.get_native_model() is not None


def test_xgboost_model_path_safety_and_type_mismatch():
    """Task 3.3: 路徑安全與模型類型檢查。"""
    X, y, feature_names = _make_binary_data()
    analyzer = XGBoostAnalyzer(params={"n_estimators": 10, "max_depth": 2})
    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)

    with pytest.raises(ValueError, match="模型路徑必須在 data_cache/models/"):
        analyzer.save_model("/tmp/xgb.pkl")

    target_dir = Path("data_cache/models")
    target_dir.mkdir(parents=True, exist_ok=True)
    xgb_path = target_dir / "phase3_xgb_protocol.pkl"
    analyzer.save_model(str(xgb_path))

    from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer

    lgb = LightGBMAnalyzer()
    with pytest.raises(ValueError, match="模型類型不匹配"):
        lgb.load_model(str(xgb_path))

    if xgb_path.exists():
        xgb_path.unlink()
