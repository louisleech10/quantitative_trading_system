from __future__ import annotations

from api.services.xgboost_task_cache import ModelTaskCache, XGBoostTaskCache


def test_model_task_cache_store_and_get_result():
    cache = ModelTaskCache()
    cache.store_result(
        task_id="task-1",
        engine="lightgbm",
        predictions_df=None,
        calibration_curve={"x": [0.1]},
        pr_curve={"precision": [0.8]},
    )

    cached = cache.get_result("task-1")
    assert cached is not None
    assert cached.engine == "lightgbm"


def test_xgboost_task_cache_backward_compatible_store_result():
    cache = XGBoostTaskCache()
    cache.store_result(
        task_id="task-xgb-1",
        predictions_df=None,
        calibration_curve=None,
        pr_curve=None,
    )

    cached = cache.get_result("task-xgb-1")
    assert cached is not None
    assert cached.engine == "xgboost"
