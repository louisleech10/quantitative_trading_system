import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
from momentum.core.protocols import IModelTrainer


def _make_binary_data(n_samples: int = 160, n_features: int = 8):
    rng = np.random.default_rng(42)
    X = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)),
        columns=[f"feature_{i}" for i in range(n_features)],
    )
    y = ((X["feature_0"] + 0.5 * X["feature_1"]) > 0).astype(int).to_numpy()
    return X, y, X.columns.tolist()


def test_lightgbm_protocol_and_train_predict():
    """LightGBMAnalyzer 應符合 IModelTrainer 並可完成基本訓練/預測。"""
    X, y, feature_names = _make_binary_data()
    analyzer = LightGBMAnalyzer(params={"n_estimators": 20, "num_leaves": 15})

    assert isinstance(analyzer, IModelTrainer)
    started = time.perf_counter()
    performance = analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)
    elapsed = time.perf_counter() - started

    proba = analyzer.predict_proba(X)

    assert analyzer.get_model_type() == "lightgbm"
    assert proba.shape == (len(X), 2)
    assert 0.0 <= performance.cv_auc_mean <= 1.0
    assert elapsed < 5.0


def test_lightgbm_required_errors_and_path_safety():
    """覆蓋 Task 3.2 關鍵錯誤路徑。"""
    analyzer = LightGBMAnalyzer()

    with pytest.raises(ValueError, match="模型尚未訓練"):
        analyzer.predict_proba(pd.DataFrame([[1.0, 2.0]]))

    with pytest.raises(ValueError, match="X 為空"):
        analyzer.train_model(pd.DataFrame(), np.array([]), feature_names=[])

    X, _, feature_names = _make_binary_data(n_samples=80)
    y_single = np.zeros(80, dtype=int)
    with pytest.raises(ValueError, match="標籤只有一個類別"):
        analyzer.train_model(X, y_single, feature_names=feature_names)

    with pytest.raises(ValueError, match="模型路徑必須在 data_cache/models/"):
        analyzer.load_model("/tmp/not-allowed.pkl")


def test_lightgbm_save_load_and_type_mismatch():
    """模型可儲存/載入，且可攔截引擎型別不匹配。"""
    from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

    X, y, feature_names = _make_binary_data()
    lgb = LightGBMAnalyzer(params={"n_estimators": 10, "num_leaves": 8})
    lgb.train_model(X, y, feature_names=feature_names, cv_folds=3)

    target_dir = Path("data_cache/models")
    target_dir.mkdir(parents=True, exist_ok=True)
    lgb_path = target_dir / "phase3_lgb_test.pkl"
    xgb_path = target_dir / "phase3_xgb_test.pkl"

    lgb.save_model(str(lgb_path))

    loaded = LightGBMAnalyzer()
    loaded.load_model(str(lgb_path))
    assert loaded.get_model_type() == "lightgbm"
    assert loaded.get_native_model() is not None

    xgb = XGBoostAnalyzer(params={"n_estimators": 10, "max_depth": 2})
    xgb.train_model(X, y, feature_names=feature_names, cv_folds=3)
    xgb.save_model(str(xgb_path))

    with pytest.raises(ValueError, match="模型類型不匹配"):
        loaded.load_model(str(xgb_path))

    if lgb_path.exists():
        lgb_path.unlink()
    if xgb_path.exists():
        xgb_path.unlink()
