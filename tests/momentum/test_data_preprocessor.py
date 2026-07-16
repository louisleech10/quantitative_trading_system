import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.data_preprocessor import DataPreprocessor


def test_preprocess_handles_winsorize_missing_and_constant():
    """測試 Winsorization、缺失值與常數特徵處理。

    LA-0 B4：顯式 fit_mode=full_sample 保留既有 full-sample 斷言（禁改 assert 過測）。
    """
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
    cleaned, log = preprocessor.preprocess(df, fit_mode="full_sample")

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
    assert log["fit_mode"] == "full_sample"
    assert log["oos_guarantees"] is False


def test_preprocess_empty_df_raises():
    """空 DataFrame 觸發錯誤。"""
    preprocessor = DataPreprocessor({})

    with pytest.raises(ValueError):
        preprocessor.preprocess(pd.DataFrame(), fit_mode="full_sample")


def test_preprocess_full_sample_escape():
    """full_sample 逃生口：全期 fit + oos_guarantees=False 紅標。"""
    rng = np.random.default_rng(0)
    n = 200
    values = rng.normal(size=n)
    values[-5:] = 1e6  # 尾端 outlier 應影響 full_sample 邊界
    df = pd.DataFrame({"x": values})
    preprocessor = DataPreprocessor(
        {
            "winsorization": {
                "enabled": True,
                "method": "percentile",
                "lower_percentile": 1.0,
                "upper_percentile": 99.0,
            },
            "missing_values": {"max_fill_forward": 0, "min_coverage": 0.0},
            "standardize": {"method": "none"},
        }
    )
    out, log = preprocessor.preprocess(df, fit_mode="full_sample")
    assert log["fit_mode"] == "full_sample"
    assert log["oos_guarantees"] is False
    # full_sample 邊界受尾端 outlier 影響 → max 被 clip 到 ~p99（含 outlier 的分位）
    p99 = float(pd.Series(values).quantile(0.99))
    assert float(out["x"].max()) <= p99 + 1e-9


def test_preprocess_unset_none_fail_closed():
    """unset + fit_mask=None → fail-closed raise。"""
    preprocessor = DataPreprocessor({})
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="fail-closed"):
        preprocessor.preprocess(df)
    with pytest.raises(ValueError, match="fail-closed"):
        preprocessor.preprocess(df, fit_mask=None, fit_mode="unset")


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

    clipped, log = preprocessor.winsorize(
        df, method="none", lower=1.0, upper=99.0, fit_mode="full_sample"
    )
    assert log["winsorized"] == []
    assert set(log["skipped"]) == set(df.columns)

    mad_df, _ = preprocessor.winsorize(
        df, method="mad", lower=1.0, upper=99.0, fit_mode="full_sample"
    )
    assert mad_df["feature_type"].tolist() == df["feature_type"].tolist()

    z_df, _ = preprocessor.winsorize(
        df, method="zscore", lower=1.0, upper=99.0, fit_mode="full_sample"
    )
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

    cross = preprocessor.standardize(
        df, method="cross_sectional_zscore", fit_mode="full_sample"
    )
    assert cross.shape == df.shape

    ts = preprocessor.standardize(
        df, method="time_series_zscore", fit_mode="full_sample"
    )
    assert ts.shape == df.shape

    ranked = preprocessor.standardize(
        df, method="rank_transform", fit_mode="full_sample"
    )
    assert ranked.max().max() <= 1.0

    with pytest.raises(ValueError):
        preprocessor.standardize(df, method="unknown", fit_mode="full_sample")


def test_clip_series_unknown_method_raises():
    """未知 winsorize 方法應拋出錯誤。"""
    preprocessor = DataPreprocessor({})

    with pytest.raises(ValueError):
        preprocessor._clip_series(
            pd.Series([1.0, 2.0]),
            method="unknown",
            lower=1.0,
            upper=99.0,
            fit_mode="full_sample",
        )


def test_is_type_feature_empty_false():
    """空序列不是型態特徵。"""
    preprocessor = DataPreprocessor({})

    assert preprocessor._is_type_feature(pd.Series([], dtype=float)) is False


def test_type_feature_pit_not_dependent_on_future():
    """#4 反例：pit_expanding type 判定不依未來序列翻轉（截尾 vs 加未來一致）。"""
    prefix = np.resize(np.array([-100.0, 0.0, 100.0], dtype=float), 120)
    future = np.linspace(-5.0, 5.0, 80)  # 非 type 值
    trunc = pd.DataFrame({"sig": prefix.copy()})
    full = pd.DataFrame({"sig": np.concatenate([prefix, future])})
    prep = DataPreprocessor(
        {
            "winsorization": {
                "enabled": True,
                "method": "percentile",
                "lower_percentile": 1.0,
                "upper_percentile": 99.0,
            },
            "missing_values": {"max_fill_forward": 0, "min_coverage": 0.0},
            "standardize": {"method": "none"},
        }
    )

    # 無 metadata：pit 禁 peek 全序列 → 兩邊皆非 type（一致，無 look-ahead 翻轉）
    t_trunc = prep._column_is_type_feature(
        "sig", trunc["sig"], metadata=None, fit_mask=None, fit_mode="pit_expanding"
    )
    t_full = prep._column_is_type_feature(
        "sig", full["sig"], metadata=None, fit_mask=None, fit_mode="pit_expanding"
    )
    assert t_trunc is False and t_full is False

    # metadata 靜態宣告：兩邊皆 type，與未來值無關
    meta = {"type_features": ["sig"]}
    assert prep._column_is_type_feature(
        "sig", trunc["sig"], metadata=meta, fit_mask=None, fit_mode="pit_expanding"
    )
    assert prep._column_is_type_feature(
        "sig", full["sig"], metadata=meta, fit_mask=None, fit_mode="pit_expanding"
    )

    # winsorize 分支：metadata type → 截尾/全長皆 skip，early 值 equal
    clip_full, log_full = prep.winsorize(
        full, method="percentile", lower=1.0, upper=99.0,
        metadata=meta, fit_mode="pit_expanding",
    )
    clip_trunc, log_trunc = prep.winsorize(
        trunc, method="percentile", lower=1.0, upper=99.0,
        metadata=meta, fit_mode="pit_expanding",
    )
    assert log_full["skipped"] == ["sig"]
    assert log_trunc["skipped"] == ["sig"]
    np.testing.assert_allclose(
        clip_full["sig"].iloc[: len(trunc)].to_numpy(),
        clip_trunc["sig"].to_numpy(),
        equal_nan=True,
    )

    # 舊病：full_sample value-set 仍可依未來翻轉（研究逃生，非 PIT 契約）
    assert prep._column_is_type_feature(
        "sig", trunc["sig"], None, None, "full_sample"
    ) is True
    assert prep._column_is_type_feature(
        "sig", full["sig"], None, None, "full_sample"
    ) is False


def test_pit_coverage_constant_first_valid_canonical():
    """#5：coverage+constant 對原序列各算一次再組合；final first-valid==§MS(99)。

    手動雙 warmup（先遮再 pit_valid_mask）必打紅 first==198。
    """
    from momentum.Analysis.pit_stats import MIN_SAMPLES, pit_valid_mask

    n = 220
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"f0": rng.normal(size=n)})
    prep = DataPreprocessor(
        {
            "winsorization": {"enabled": False},
            "missing_values": {"max_fill_forward": 0, "min_coverage": 0.0},
            "standardize": {"method": "none"},
        }
    )
    out, log = prep.preprocess(df, fit_mode="pit_expanding")
    const_valid = log["per_bar_validity"]["constant"]["f0"]
    first_true = next(i for i, v in enumerate(const_valid) if v)
    first_non_nan = int(out["f0"].notna().to_numpy().argmax())
    assert first_true == MIN_SAMPLES - 1  # dense → 99
    assert first_non_nan == MIN_SAMPLES - 1

    # 手動雙 warmup 打紅：coverage 先遮 → 再 pit_valid_mask → first=198
    series = df["f0"]
    pit_ok = pit_valid_mask(series, min_samples=MIN_SAMPLES).to_numpy()
    once_masked = series.copy()
    once_masked.loc[~pit_ok] = np.nan
    pit_ok2 = pit_valid_mask(once_masked, min_samples=MIN_SAMPLES).to_numpy()
    double_first = next(i for i, v in enumerate(pit_ok2) if v)
    assert double_first == 2 * (MIN_SAMPLES - 1) + 0  # 198 for m=100
    assert double_first != first_true  # 現碼不得等於雙 warmup
