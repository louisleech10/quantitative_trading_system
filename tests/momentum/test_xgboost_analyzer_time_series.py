import numpy as np

from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer


def test_train_model_time_series_split():
    """測試時間序列切分訓練是否可正常執行"""
    rng = np.random.default_rng(42)
    X = rng.normal(size=(120, 6))
    y = np.array([0, 1] * 60)
    timestamps = np.arange(len(y))

    analyzer = XGBoostAnalyzer()
    performance = analyzer.train_model(
        X,
        y,
        feature_names=[f"f{i}" for i in range(X.shape[1])],
        early_stopping_rounds=5,
        eval_size=0.2,
        xgboost_params={
            "n_estimators": 10,
            "max_depth": 2,
            "learning_rate": 0.1,
            "subsample": 0.9,
            "colsample_bytree": 0.9
        },
        cv_folds=3,
        time_series_split=True,
        timestamps=timestamps
    )

    assert 0.0 <= performance.train_auc <= 1.0
    assert 0.0 <= performance.cv_auc_mean <= 1.0
