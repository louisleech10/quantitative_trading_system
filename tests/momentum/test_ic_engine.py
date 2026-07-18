import numpy as np
import pandas as pd
import pytest
from scipy import optimize, stats

from momentum.Analysis.ic_engine import ICEngine
from momentum.core.contracts import AlignmentViolationError


def _make_sample_data(n_samples: int = 50):
    rng = np.random.default_rng(42)
    base = np.linspace(0, 1, n_samples)
    data = pd.DataFrame(
        {
            "feature_pos": base + rng.normal(0, 0.01, n_samples),
            "feature_neg": -base + rng.normal(0, 0.01, n_samples),
            "feature_noise": rng.normal(0, 1, n_samples),
        }
    )
    label = pd.Series(base, name="label")
    return data, label


def test_compute_ic_matches_scipy():
    """Spearman/Pearson 與 scipy 驗算一致。"""
    features, label = _make_sample_data()
    engine = ICEngine({"methods": ["spearman", "pearson"]})

    spearman = engine.compute_ic(features, label, method="spearman")
    pearson = engine.compute_ic(features, label, method="pearson")

    for feature in features.columns:
        expected_s = stats.spearmanr(features[feature], label)[0]
        expected_p = stats.pearsonr(features[feature], label)[0]
        assert abs(spearman[feature] - expected_s) < 1e-9
        assert abs(pearson[feature] - expected_p) < 1e-9


def test_compute_rolling_ic_and_icir():
    """Rolling IC + ICIR 計算正確。"""
    features, label = _make_sample_data(n_samples=80)
    engine = ICEngine({"icir": {"window": 10}})

    rolling = engine.compute_rolling_ic(
        features, label, windows=[10], stride=1, method="spearman"
    )
    assert "feature_pos" in rolling
    assert "window_10" in rolling["feature_pos"]
    assert len(rolling["feature_pos"]["window_10"]) > 0

    icir = engine.compute_icir(rolling)
    assert icir["feature_pos"]["icir"] > 0
    assert icir["feature_pos"]["ic_hit_rate"] > 0.8


def test_rolling_window_adjustment_by_timeframe():
    """Rolling window 依 timeframe 自動調整。"""
    features, label = _make_sample_data(n_samples=40)
    engine = ICEngine(
        {
            "icir": {"window": 10, "reference_tf": "12h"},
            "timeframe": "4h",
        }
    )

    rolling = engine.compute_rolling_ic(
        features, label, windows=[10], stride=1, method="pearson"
    )

    assert "window_30" in rolling["feature_pos"]


def test_compute_ic_decay_outputs_peak_horizon():
    """IC Decay 回傳 peak horizon 與 half-life。"""
    features, label = _make_sample_data(n_samples=100)
    close = label.cumsum() + 10

    engine = ICEngine({})
    decay = engine.compute_ic_decay(
        features,
        close,
        horizons=[1, 2, 3],
        method="spearman",
        return_type="simple",
    )

    result = decay["feature_pos"]
    assert result["peak_horizon"] in [1, 2, 3]
    assert len(result["ic_values"]) == 3
    assert "half_life" in result


def test_fit_exponential_decay_identifies_exponential():
    """指數衰減擬合可辨識 decay_type。"""
    horizons = [1, 2, 3, 4, 5]
    ic_values = [0.5 * np.exp(-0.4 * h) + 0.01 for h in horizons]

    result = ICEngine._fit_exponential_decay(horizons, ic_values)

    assert result["decay_type"] == "exponential"
    assert result["half_life"] > 0


def test_grouped_ic_by_year_and_category():
    """分組 IC 可依年份與分類產出。"""
    features, label = _make_sample_data(n_samples=40)
    raw_data = pd.DataFrame(
        {
            "close": label.cumsum() + 10,
        },
        index=pd.date_range("2024-01-01", periods=40, freq="D"),
    )
    metadata = {
        "feature_pos": {"category": "trend"},
        "feature_neg": {"category": "trend"},
        "feature_noise": {"category": "noise"},
    }

    engine = ICEngine({})
    grouped = engine.compute_grouped_ic(
        features,
        label,
        raw_data,
        metadata,
        {
            "by_year": True,
            "by_quarter": False,
            "by_regime": False,
            "by_category": True,
            "by_data_source": False,
            "by_layer": False,
        },
    )

    assert "by_year" in grouped
    assert "2024" in grouped["by_year"]
    assert "by_category" in grouped
    assert "trend" in grouped["by_category"]


def test_grouped_ic_by_regime():
    """分組 IC 可依市場狀態產出。"""
    features, label = _make_sample_data(n_samples=60)
    raw_data = pd.DataFrame(
        {"close": np.linspace(1, 2, 60)},
        index=pd.date_range("2024-01-01", periods=60, freq="D"),
    )

    engine = ICEngine({})
    grouped = engine.compute_grouped_ic(
        features,
        label,
        raw_data,
        metadata={},
        config={
            "by_year": False,
            "by_quarter": False,
            "by_regime": True,
            "by_category": False,
            "by_data_source": False,
            "by_layer": False,
            "regime_definitions": {
                "high_vol_percentile": 80,
                "low_vol_percentile": 20,
            },
        },
    )

    assert "by_regime" in grouped
    assert "bull" in grouped["by_regime"]
    assert "bear" in grouped["by_regime"]


def test_align_label_to_group_rejects_equal_length_misalignment():
    """M2: 同長錯位不可靜默 positional 對齊。"""
    group_df = pd.DataFrame(
        {"feature": [1.0, 2.0, 3.0]},
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
    )
    label = pd.Series(
        [0.1, 0.2, 0.3],
        index=pd.date_range("2024-01-02", periods=3, freq="D"),
        name="return_1",
    )

    with pytest.raises(AlignmentViolationError, match="equal length"):
        ICEngine._align_label_to_group(label, group_df)


def test_align_label_to_group_reindexes_subset_labels():
    """不同長度時保留既有 reindex 語義。"""
    index = pd.date_range("2024-01-01", periods=3, freq="D")
    group_df = pd.DataFrame({"feature": [1.0, 2.0, 3.0]}, index=index)
    label = pd.Series([0.1, 0.3], index=index[[0, 2]], name="return_1")

    aligned = ICEngine._align_label_to_group(label, group_df)

    assert aligned.index.equals(group_df.index)
    assert np.isnan(aligned.iloc[1])
    assert aligned.name == "return_1"


def test_ic_autocorrelation_high_for_stable_series():
    """IC 自相關在穩定序列上偏高。"""
    rolling = {
        "feature_pos": {"window_10": [0.2, 0.25, 0.3, 0.35, 0.4]},
    }
    engine = ICEngine({"icir": {"window": 10}})
    autocorr = engine.compute_ic_autocorrelation(rolling, lag=1)

    assert autocorr["feature_pos"] > 0.3


def test_ic_autocorrelation_zero_std_branch():
    """std=0 時應回 NaN。"""
    engine = ICEngine({"icir": {"window": 5}})
    rolling = {"f1": {"window_5": [0.1, 0.1, 0.1, 0.1]}}

    autocorr = engine.compute_ic_autocorrelation(rolling, lag=1)

    assert np.isnan(autocorr["f1"])


def test_compute_ic_empty_and_short_inputs():
    """空資料與短資料回傳 NaN 或空 dict。"""
    engine = ICEngine({})

    empty = pd.DataFrame()
    assert engine.compute_ic(empty, pd.Series(dtype=float)) == {}

    short_features = pd.DataFrame({"f1": [1.0]})
    short_label = pd.Series([1.0])
    result = engine.compute_ic(short_features, short_label, method="spearman")
    assert np.isnan(result["f1"])


def test_compute_ic_kendall_and_unknown_method():
    """kendall 與未知方法分支。"""
    features, label = _make_sample_data(n_samples=10)
    engine = ICEngine({})

    kendall = engine.compute_ic(features, label, method="kendall")
    assert "feature_pos" in kendall

    unknown = engine.compute_ic(features, label, method="unknown")
    assert "feature_pos" in unknown


def test_compute_rolling_ic_empty_alignment():
    """對齊後空資料回空 dict。"""
    features = pd.DataFrame({"f1": [1.0, 2.0]})
    label = pd.Series([np.nan, np.nan])
    engine = ICEngine({})

    rolling = engine.compute_rolling_ic(features, label, windows=[5], stride=1, method="spearman")

    assert rolling["f1"] == {}


def test_compute_rolling_ic_pearson_short_window():
    """pearson 分支與短窗口返回空列表。"""
    features = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    label = pd.Series([1.0, 2.0, 3.0])
    engine = ICEngine({})

    rolling = engine.compute_rolling_ic(features, label, windows=[5], stride=1, method="pearson")

    assert rolling["f1"]["window_5"] == []


def test_compute_returns_fallback():
    """LA-2 B1：return_type 不支援時 fail-closed raise（禁 silent 回退 simple）。"""
    engine = ICEngine({})
    close = pd.Series([1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="Unsupported return_type"):
        engine._compute_returns(close, horizon=1, return_type="unknown")

    with pytest.raises(NotImplementedError, match="LOOKAHEAD_LABEL_UNSUPPORTED"):
        engine._compute_returns(close, horizon=1, return_type="winsorized")


def test_select_icir_series_fallbacks():
    """ICIR Series 選擇回退分支。"""
    engine = ICEngine({"icir": {"window": 99}})

    assert engine._select_icir_series({}) == []
    assert engine._select_icir_series({"window_5": [0.1]}) == [0.1]


def test_time_index_parsing_and_alignment():
    """時間索引解析與對齊分支。"""
    engine = ICEngine({})
    raw_data = pd.DataFrame({"open_time": [1704067200, 1704153600, 1704240000]})

    index = engine._get_time_index(raw_data)
    assert index is not None
    assert index.year.tolist() == [2024, 2024, 2024]

    features = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    label = pd.Series([1.0, 2.0, 3.0])
    aligned_features, aligned_label, aligned_raw = engine._align_with_raw_data(features, label, raw_data)
    assert len(aligned_features) == len(aligned_raw)
    assert aligned_label.index.equals(aligned_features.index)


def test_regime_groups_empty_and_missing_close():
    """Regime 分支空資料處理。"""
    engine = ICEngine({})
    features = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    label = pd.Series([0.1, 0.2, 0.3])

    assert engine._compute_regime_groups(features, label, pd.DataFrame(), {}) == {}


def test_metadata_groups_empty_metadata():
    """metadata 空時應回空 dict。"""
    engine = ICEngine({})
    features = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    label = pd.Series([0.1, 0.2, 0.3])

    assert engine._compute_metadata_groups(features, label, {}, "category", "spearman") == {}


def test_rolling_corr_matrix_edges():
    """rolling corr 的邊界條件。"""
    x = np.array([[1.0, 2.0], [2.0, 3.0]])
    y = np.array([1.0, 2.0])

    empty_short = ICEngine._rolling_corr_matrix(x, y, window=3, stride=1)
    assert empty_short.shape[0] == 0

    empty_window = ICEngine._rolling_corr_matrix(x, y, window=1, stride=1)
    assert empty_window.shape[0] == 0


def test_compute_icir_empty_values():
    """空 IC 序列應回 NaN。"""
    engine = ICEngine({"icir": {"window": 5}})

    result = engine.compute_icir({"f1": {"window_5": []}})
    assert np.isnan(result["f1"]["icir"])


def test_grouped_ic_quarter_and_metadata_groups():
    """分組 IC 支援季度與 metadata 群組。"""
    features, label = _make_sample_data(n_samples=40)
    raw_data = pd.DataFrame(
        {"close": label.cumsum() + 10},
        index=pd.date_range("2024-01-01", periods=40, freq="D"),
    )
    metadata = {
        "feature_pos": {"data_source": "close", "layer": 1},
        "feature_neg": {"data_source": "close", "layer": 1},
        "feature_noise": {"data_source": "volume", "layer": 2},
    }
    engine = ICEngine({})

    grouped = engine.compute_grouped_ic(
        features,
        label,
        raw_data,
        metadata,
        {
            "by_year": False,
            "by_quarter": True,
            "by_regime": False,
            "by_category": False,
            "by_data_source": True,
            "by_layer": True,
        },
    )

    assert "by_quarter" in grouped
    assert "by_data_source" in grouped
    assert "by_layer" in grouped


def test_ic_autocorrelation_edge_cases():
    """自相關在不足樣本或變異為零時回 NaN。"""
    engine = ICEngine({"icir": {"window": 10}})

    rolling = {"f1": {"window_10": [0.1]}}
    autocorr = engine.compute_ic_autocorrelation(rolling, lag=1)
    assert np.isnan(autocorr["f1"])

    rolling = {"f1": {"window_10": [0.1, 0.1, 0.1]}}
    autocorr = engine.compute_ic_autocorrelation(rolling, lag=1)
    assert np.isnan(autocorr["f1"])


def test_fit_exponential_decay_edge_cases(monkeypatch):
    """Decay fit 的不足點數與低變異分支。"""
    insufficient = ICEngine._fit_exponential_decay([1, 2], [0.1, 0.2])
    assert insufficient["fit_warning_reason"] == "insufficient_points"

    low_var = ICEngine._fit_exponential_decay([1, 2, 3], [0.1, 0.1, 0.1])
    assert low_var["fit_warning_reason"] == "low_variance"

    def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(optimize, "curve_fit", _raise)
    failed = ICEngine._fit_exponential_decay([1, 2, 3], [0.1, 0.2, 0.3])
    assert failed["fit_warning_reason"] == "fit_exception"


def test_pairwise_corr_edge_cases():
    """對齊空資料與 std=0 分支。"""
    engine = ICEngine({})
    series = pd.Series([np.nan, np.nan])
    label = pd.Series([np.nan, np.nan])

    assert np.isnan(engine._compute_pairwise_corr(series, label, "spearman"))

    series = pd.Series([1.0, 1.0, 1.0])
    label = pd.Series([2.0, 2.0, 2.0])
    assert np.isnan(engine._compute_pairwise_corr(series, label, "pearson"))


def test_timeframe_parsing_and_adjustment():
    """時間窗調整與解析分支。"""
    engine = ICEngine({"icir": {"window": 10, "reference_tf": "12h"}, "timeframe": "bad"})
    assert engine._adjust_rolling_windows([10]) == [10]

    assert engine._parse_timeframe_hours("1d") == 24
    assert engine._parse_timeframe_hours("1w") == 168
    assert engine._parse_timeframe_hours("") is None
    assert engine._parse_timeframe_hours("xh") is None


def test_iter_time_groups_quarter():
    """季度分組分支。"""
    engine = ICEngine({})
    raw_data = pd.DataFrame(index=pd.date_range("2024-01-01", periods=10, freq="D"))

    groups = engine._iter_time_groups(raw_data, "quarter")
    assert groups


def test_compute_vectorized_ic_single_feature():
    """單一特徵向量化 IC。"""
    engine = ICEngine({})
    df = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    label = pd.Series([1.0, 2.0, 3.0])

    result = engine._compute_vectorized_ic(df, label, "pearson")
    assert "f1" in result


def test_rolling_spearman_branches():
    """rolling_spearman 的 NaN 與 std=0 分支。"""
    engine = ICEngine({})
    series = pd.Series([1.0, 1.0, 1.0, 1.0])
    label = pd.Series([1.0, 1.0, 1.0, 1.0])

    results = engine._rolling_spearman(series, label, window=2, stride=1)
    assert all(np.isnan(value) for value in results)


def test_select_peak_horizon_all_nan():
    """全 NaN 時回第一個 horizon。"""
    engine = ICEngine({})
    assert engine._select_peak_horizon([1, 2, 3], [np.nan, np.nan, np.nan]) == 1


def test_compute_returns_log_branch():
    """log return 分支應正確輸出。"""
    engine = ICEngine({})
    close = pd.Series([1.0, 2.0, 4.0])

    values = engine._compute_returns(close, horizon=1, return_type="log")
    assert np.isclose(values.iloc[0], np.log(2.0))


def test_select_icir_series_weird_dict():
    """windows values 空時回空列表。"""
    engine = ICEngine({"icir": {"window": 5}})

    class _WeirdDict(dict):
        def __bool__(self):
            return True

        def values(self):
            return []

    assert engine._select_icir_series(_WeirdDict()) == []


def test_iter_time_groups_missing_time_index():
    """無時間索引時回空分組。"""
    engine = ICEngine({})
    raw_data = pd.DataFrame({"value": [1.0, 2.0, 3.0]})

    assert engine._iter_time_groups(raw_data, "year") == []


def test_get_time_index_non_numeric_column():
    """非數字時間欄位應轉為 datetime。"""
    engine = ICEngine({})
    raw_data = pd.DataFrame({"timestamp": ["2024-01-01", "2024-01-02"]})

    index = engine._get_time_index(raw_data)
    assert pd.api.types.is_datetime64_any_dtype(index)


def test_regime_groups_empty_vol_values():
    """波動率為空時回空 dict。"""
    engine = ICEngine({})
    features = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    label = pd.Series([0.1, 0.2, 0.3], index=features.index)
    raw_data = pd.DataFrame({"close": [np.nan, np.nan, np.nan]}, index=features.index)

    result = engine._compute_regime_groups(features, label, raw_data, {})
    assert result == {}


def test_metadata_groups_skip_none_values():
    """metadata value 為 None 時跳過。"""
    engine = ICEngine({})
    features = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [2.0, 3.0, 4.0]})
    label = pd.Series([0.1, 0.2, 0.3])
    metadata = {"f1": {"category": None}, "f2": {"category": "trend"}}

    grouped = engine._compute_metadata_groups(features, label, metadata, "category", "spearman")
    assert "trend" in grouped


def test_align_with_raw_data_empty_and_reindex():
    """raw_data 空與長度不一致分支。"""
    engine = ICEngine({})
    features = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    label = pd.Series([0.1, 0.2, 0.3])

    aligned_features, aligned_label, aligned_raw = engine._align_with_raw_data(
        features, label, pd.DataFrame()
    )
    assert aligned_raw.empty

    raw_data = pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0]})
    aligned_features, aligned_label, aligned_raw = engine._align_with_raw_data(
        features, label, raw_data
    )
    assert len(aligned_raw) == len(aligned_features)


def test_compute_vectorized_ic_short_rows():
    """樣本數不足應回 NaN。"""
    engine = ICEngine({})
    df = pd.DataFrame({"f1": [1.0]})
    label = pd.Series([1.0])

    result = engine._compute_vectorized_ic(df, label, "pearson")
    assert np.isnan(result["f1"])


def test_parse_timeframe_hours_unknown_unit():
    """未知單位應回 None。"""
    engine = ICEngine({})
    assert engine._parse_timeframe_hours("1m") is None


def test_rolling_spearman_nan_and_valid():
    """rolling_spearman 的 NaN skip 與正常路徑。"""
    engine = ICEngine({})
    series = pd.Series([1.0, np.nan])
    label = pd.Series([1.0, 2.0])

    results = engine._rolling_spearman(series, label, window=2, stride=1)
    assert results == []

    series = pd.Series([1.0, 2.0, 3.0, 4.0])
    label = pd.Series([1.0, 2.0, 3.0, 5.0])
    results = engine._rolling_spearman(series, label, window=2, stride=1)
    assert len(results) > 0


def test_rolling_spearman_nan_label_branch():
    """label 含 NaN 時應跳過該視窗。"""
    engine = ICEngine({})
    series = pd.Series([1.0, 2.0, 3.0])
    label = pd.Series([1.0, np.nan, 3.0])

    results = engine._rolling_spearman(series, label, window=2, stride=1)
    assert results == []


def test_fit_exponential_decay_low_r2_warning():
    """低 R2 應標記非指數衰減。"""
    horizons = [1, 2, 3, 4]
    ic_values = [0.1, -0.2, 0.15, -0.05]

    result = ICEngine._fit_exponential_decay(horizons, ic_values)
    assert result["fit_warning_reason"] == "low_r2"
