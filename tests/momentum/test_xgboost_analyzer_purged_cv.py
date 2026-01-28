"""
XGBoostAnalyzer Purged CV 測試

測試 Task 1.5 的 Purged K-Fold 整合
"""

import numpy as np

from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer


def test_train_with_purged_cv():
    """測試 Purged K-Fold 訓練流程"""
    rng = np.random.default_rng(42)
    n_samples = 150
    n_features = 6

    X = rng.normal(size=(n_samples, n_features))
    y = ((X[:, 0] + X[:, 1]) > 0).astype(int)
    timestamps = np.arange(n_samples)

    analyzer = XGBoostAnalyzer()
    performance = analyzer.train_with_purged_cv(
        X=X,
        y=y,
        feature_names=[f"f{i}" for i in range(n_features)],
        early_stopping_rounds=5,
        eval_size=0.2,
        xgboost_params={
            "n_estimators": 20,
            "max_depth": 2,
            "learning_rate": 0.1,
            "subsample": 0.9,
            "colsample_bytree": 0.9
        },
        cv_folds=3,
        timestamps=timestamps,
        purge_gap=2,
        embargo_pct=0.1
    )

    assert 0.0 <= performance.train_auc <= 1.0
    assert 0.0 <= performance.cv_auc_mean <= 1.0
