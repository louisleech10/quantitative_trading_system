import pandas as pd
import pytest

from momentum.Analysis.data_preprocessor import DataPreprocessor


def test_preprocess_handles_winsorize_missing_and_constant():
    """測試 Winsorization、缺失值與常數特徵處理。"""
    df = pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 3.0, 1000.0],
            "feature_b": [1.0, None, None, None],
            "feature_c": [5.0, 5.0, 5.0, 5.0],
            "feature_type": [-100.0, 0.0, 100.0, -100.0],
        }
    )

    config = {
        "winsorization": {
            "enabled": True,
            "method": "percentile",
            "lower_percentile": 1.0,
            "upper_percentile": 99.0,
        },
        "missing_values": {"max_fill_forward": 1, "min_coverage": 0.8},
    }

    preprocessor = DataPreprocessor(config)
    cleaned, log = preprocessor.preprocess(df)

    assert "feature_b" not in cleaned.columns
    assert "feature_c" not in cleaned.columns
    assert set(cleaned.columns) == {"feature_a", "feature_type"}

    lower_q = df["feature_a"].quantile(0.01)
    upper_q = df["feature_a"].quantile(0.99)
    assert cleaned["feature_a"].max() <= upper_q + 1e-9
    assert cleaned["feature_a"].min() >= lower_q - 1e-9
    assert cleaned["feature_type"].tolist() == df["feature_type"].tolist()

    assert "removed_features" in log
    assert "low_coverage" in log["removed_features"]
    assert "constant" in log["removed_features"]


def test_preprocess_empty_df_raises():
    """空 DataFrame 觸發錯誤。"""
    preprocessor = DataPreprocessor({})

    with pytest.raises(ValueError):
        preprocessor.preprocess(pd.DataFrame())


def test_winsorize_methods_and_type_feature_skip():
    """覆蓋 winsorize 方法分支與型態特徵跳過。"""
    df = pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 100.0, 3.0],
            "feature_b": [5.0, 5.0, 5.0, 5.0],
            "feature_type": [-100.0, 0.0, 100.0, -100.0],
        }
    )
    preprocessor = DataPreprocessor({})

    clipped, log = preprocessor.winsorize(df, method="none", lower=1.0, upper=99.0)
    assert log["winsorized"] == []
    assert set(log["skipped"]) == set(df.columns)

    mad_df, _ = preprocessor.winsorize(df, method="mad", lower=1.0, upper=99.0)
    assert mad_df["feature_type"].tolist() == df["feature_type"].tolist()

    z_df, _ = preprocessor.winsorize(df, method="zscore", lower=1.0, upper=99.0)
    assert z_df["feature_type"].tolist() == df["feature_type"].tolist()


def test_standardize_methods_and_unknown():
    """覆蓋標準化各分支與未知方法。"""
    df = pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 3.0],
            "feature_b": [2.0, 3.0, 4.0],
        }
    )
    preprocessor = DataPreprocessor({})

    cross = preprocessor.standardize(df, method="cross_sectional_zscore")
    assert cross.shape == df.shape

    ts = preprocessor.standardize(df, method="time_series_zscore")
    assert ts.shape == df.shape

    ranked = preprocessor.standardize(df, method="rank_transform")
    assert ranked.max().max() <= 1.0

    with pytest.raises(ValueError):
        preprocessor.standardize(df, method="unknown")


def test_clip_series_unknown_method_raises():
    """未知 winsorize 方法應拋出錯誤。"""
    preprocessor = DataPreprocessor({})

    with pytest.raises(ValueError):
        preprocessor._clip_series(pd.Series([1.0, 2.0]), method="unknown", lower=1.0, upper=99.0)


def test_is_type_feature_empty_false():
    """空序列不是型態特徵。"""
    preprocessor = DataPreprocessor({})

    assert preprocessor._is_type_feature(pd.Series([], dtype=float)) is False
