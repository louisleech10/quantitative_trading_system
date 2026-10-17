"""
測試 XGBoost Analyzer 對 numpy array 的支援

驗證 train_model 可以同時接受：
1. pandas DataFrame
2. numpy array + feature_names

TESTREG b5：原為模組層腳本（print，try/except 吞錯，pytest 收集 0 項），改寫為 pytest 函式，
保留原測試 1–3 之檢查；原只 print 之項改為斷言。
"""

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

_N_SAMPLES = 100
_N_FEATURES = 5
_FEATURE_NAMES = [f"feature_{i}" for i in range(_N_FEATURES)]


def _data() -> tuple:
    rng = np.random.default_rng(0)
    X_array = rng.standard_normal((_N_SAMPLES, _N_FEATURES))
    y = np.zeros(_N_SAMPLES, dtype=int)
    y[_N_SAMPLES // 2:] = 1  # 確保有兩個類別
    return X_array, y


def test_train_model_accepts_numpy_with_feature_names() -> None:
    """測試 1：numpy array + feature_names 可訓練，特徵名稱已儲存。"""
    X_array, y = _data()
    analyzer = XGBoostAnalyzer()
    perf = analyzer.train_model(
        X=X_array, y=y, feature_names=_FEATURE_NAMES, early_stopping_rounds=5, eval_size=0.2
    )
    assert list(analyzer.feature_names) == _FEATURE_NAMES
    assert np.isfinite(perf.in_sample_train_auc)
    assert np.isfinite(perf.cv_auc_mean)


def test_train_model_accepts_dataframe_equivalently() -> None:
    """測試 2：pandas DataFrame（向後相容）可訓練，結果與 numpy+feature_names 一致。"""
    X_array, y = _data()
    a_np = XGBoostAnalyzer()
    p_np = a_np.train_model(
        X=X_array, y=y, feature_names=_FEATURE_NAMES, early_stopping_rounds=5, eval_size=0.2
    )
    a_df = XGBoostAnalyzer()
    p_df = a_df.train_model(
        X=pd.DataFrame(X_array, columns=_FEATURE_NAMES), y=y, early_stopping_rounds=5, eval_size=0.2
    )
    assert list(a_df.feature_names) == _FEATURE_NAMES
    assert np.isclose(p_df.in_sample_train_auc, p_np.in_sample_train_auc)
    assert np.isclose(p_df.cv_auc_mean, p_np.cv_auc_mean)


def test_train_model_numpy_without_feature_names_raises() -> None:
    """測試 3：numpy array 未給 feature_names ⇒ ValueError。"""
    X_array, y = _data()
    with pytest.raises(ValueError, match="feature_names"):
        XGBoostAnalyzer().train_model(X=X_array, y=y, early_stopping_rounds=5, eval_size=0.2)
