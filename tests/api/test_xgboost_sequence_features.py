import numpy as np
import pandas as pd

from api.services.xgboost_batch_service import XGBoostBatchService


def test_flatten_sequence_features():
    """測試展平序列特徵輸出形狀與命名
    
    注意：現在特徵只用到 TO-1，所以命名從 t-3 到 t-1（沒有 t0）
    """
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
    # 修正：現在是 t-3, t-2, t-1 (沒有 t0)
    assert names[0] == "a_w3_t-3"
    assert names[1] == "a_w3_t-2"
    assert names[2] == "a_w3_t-1"
    assert names[3] == "b_w3_t-3"
    assert names[-1] == "b_w3_t-1"


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


def test_build_sequence_features_flatten_values_exclude_to_bar():
    """展平模式之值必須恰為 TO 前兩根（第 1、2 列），TO 當根（row_idx=3）不得入窗

    獨立 oracle：手算 row_idx=3、sequence_length=2、stride=1 ⇒ 視窗列 [1, 2]；
    x 第 1、2 列＝[2, 3]，y 第 1、2 列＝[6, 7]；轉置展平後依特徵連續排列。
    """
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

    assert result is not None and [float(v) for v in result[0]] == [2.0, 3.0, 6.0, 7.0] and 4.0 not in [float(v) for v in result[0]] and list(result[1]) == ["x_w2_t-2", "x_w2_t-1", "y_w2_t-2", "y_w2_t-1"], f"視窗值錯（含 TO 或順序錯）：{result}"


def test_flatten_sequence_features_values_match_names():
    """展平後之值須與名稱逐一對應：a 之 t-3..t-1 為 [1,3,5]、b 為 [2,4,6]

    獨立 oracle：window_values 第 j 欄即特徵 j 之時間序列（舊→新），手寫期望。
    """
    service = XGBoostBatchService()
    window_values = np.array([
        [1.0, 2.0],
        [3.0, 4.0],
        [5.0, 6.0]
    ])

    values, names = service._flatten_sequence_features(
        window_values=window_values,
        feature_names=["a", "b"],
        window_size=3
    )

    assert dict(zip(names, [float(v) for v in values])) == {"a_w3_t-3": 1.0, "a_w3_t-2": 3.0, "a_w3_t-1": 5.0, "b_w3_t-3": 2.0, "b_w3_t-2": 4.0, "b_w3_t-1": 6.0}, f"值與名稱錯配：{list(zip(names, values))}"


def test_aggregate_sequence_features_mean_last_values():
    """彙總模式 mean／last 之值須等於手算：mean=[2,3]、last=[3,4]"""
    service = XGBoostBatchService()
    window_values = np.array([
        [1.0, 2.0],
        [3.0, 4.0]
    ])

    values, names = service._aggregate_sequence_features(
        window_values=window_values,
        feature_names=["a", "b"],
        window_size=2,
        aggregation_methods=["mean", "last"]
    )

    assert dict(zip(names, [float(v) for v in values])) == {"a_w2_mean": 2.0, "b_w2_mean": 3.0, "a_w2_last": 3.0, "b_w2_last": 4.0}, f"彙總值錯：{list(zip(names, values))}"
