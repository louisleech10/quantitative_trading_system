import numpy as np
import pandas as pd

from api.services.xgboost_batch_service import XGBoostBatchService


def test_flatten_sequence_features():
    """測試展平序列特徵輸出形狀與命名"""
    service = XGBoostBatchService()
    window_values = np.array([
        [1.0, 2.0],
        [3.0, 4.0],
        [5.0, 6.0]
    ])
    feature_names = ["a", "b"]

    values, names = service._flatten_sequence_features(
        window_values=window_values,
        feature_names=feature_names,
        window_size=3
    )

    assert values.shape == (6,)
    assert len(names) == 6
    assert names[0] == "a_w3_t-2"
    assert names[-1] == "b_w3_t0"


def test_aggregate_sequence_features_mean_last():
    """測試彙總序列特徵輸出形狀"""
    service = XGBoostBatchService()
    window_values = np.array([
        [1.0, 2.0],
        [3.0, 4.0]
    ])
    feature_names = ["a", "b"]

    values, names = service._aggregate_sequence_features(
        window_values=window_values,
        feature_names=feature_names,
        window_size=2,
        aggregation_methods=["mean", "last"]
    )

    assert values.shape == (4,)
    assert len(names) == 4
    assert "a_w2_mean" in names
    assert "b_w2_last" in names


def test_build_sequence_features_flatten():
    """測試 build_sequence_features 在展平模式"""
    service = XGBoostBatchService()
    df = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [5.0, 6.0, 7.0, 8.0],
        "timestamp_sec": [1, 2, 3, 4]
    })

    result = service._build_sequence_features(
        all_features=df,
        row_idx=3,
        feature_names=["x", "y"],
        sequence_length=2,
        sequence_feature_mode="flatten",
        sequence_stride=1,
        aggregation_methods=None,
        multi_scale_windows=None
    )

    assert result is not None
    values, names = result
    assert values.shape == (4,)
    assert len(names) == 4
