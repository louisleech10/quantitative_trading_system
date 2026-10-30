import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis.monotonicity_tester import MonotonicityTester
from momentum.Analysis.pit_stats import MIN_SAMPLES, pit_expanding_qcut_label


def test_quantile_returns_and_spread():
    """分位數收益與 Long-Short Spread 計算正確（PIT pit_pool）。"""
    # n 需 ≥ MIN_SAMPLES 才有有效 bin（§MS）
    # 非單調特徵：PIT 下單調 linspace 的當前 bar 永遠落最高分位 → Q1 空
    n = 300
    rng = np.random.default_rng(0)
    feature = pd.Series(rng.normal(size=n), name="feature")
    # label 與 feature 正相關 → Q_high mean > Q_low mean
    label = pd.Series(feature.to_numpy() + rng.normal(scale=0.1, size=n), name="label")
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 10})

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    q_returns = result["quantile_mean_returns"]

    assert len(q_returns) == 5
    assert np.isfinite(q_returns["Q1"]) and np.isfinite(q_returns["Q5"])
    assert q_returns["Q5"] > q_returns["Q1"]

    data = tester._prepare_data(feature, label)
    bins = tester._assign_quantiles(data, 5)
    assert bins is not None
    valid = bins.dropna()
    low_mask = bins == valid.min()
    high_mask = bins == valid.max()
    expected_spread = float(
        data.loc[high_mask, "label"].mean() - data.loc[low_mask, "label"].mean()
    )

    assert np.isclose(result["long_short_spread"], expected_spread, atol=1e-6)


@pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
def test_nonfinite_label_excluded_from_aggregation(bad):
    """code review r48 CODEX-P1-02：標籤 ±inf／NaN 之列不進分位均值與多空價差（聚合只取標籤有限列）；oracle＝同分箱下
    以 np.isfinite(label) 遮罩後之 numpy 均值；分箱仍依特徵全時序（壞標籤之列之分箱不變）。"""
    n = 300
    rng = np.random.default_rng(7)
    feature = pd.Series(rng.normal(size=n), name="feature")
    label = pd.Series(feature.to_numpy() + rng.normal(scale=0.1, size=n), name="label")
    label.iloc[[150, 260]] = bad
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 10})
    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    data = tester._prepare_data(feature, label)
    bins = tester._assign_quantiles(data, 5)
    finite = np.isfinite(data["label"].to_numpy(dtype=float))
    for q in range(5):
        sel = (bins.to_numpy() == q) & finite
        expected = float(np.mean(data["label"].to_numpy(dtype=float)[sel])) if sel.any() else np.nan
        got = result["quantile_mean_returns"][f"Q{q + 1}"]
        assert np.isfinite(got) and np.isclose(got, expected, rtol=0, atol=1e-12), (q, got, expected)
    assert np.isfinite(result["long_short_spread"])


@pytest.mark.parametrize("q", [3, 5, 10, 20])
@pytest.mark.parametrize("direction", [1, -1])
def test_monotonicity_score_numeric_quantile_order(q, direction):
    """code review r48 CODEX-P1-03：Q 鍵依數值序（Q10 不排在 Q1 與 Q2 之間）；嚴格單調輸入 ⇒ 遞增 1.0、遞減 0.0
    （產品與方向對齊版 `_aligned_monotonicity` 皆為數值序；oracle＝依整數 bin 序之相鄰差比例）。"""
    from momentum.Analysis.ic_filter_orchestrator import _aligned_monotonicity

    means = {f"Q{i}": float(direction * i) for i in range(1, q + 1)}
    score = MonotonicityTester({}).compute_monotonicity_score({"quantile_mean_returns": means})
    assert score == (1.0 if direction > 0 else 0.0)
    assert _aligned_monotonicity(means, direction) == 1.0
    assert _aligned_monotonicity(means, -direction) == 0.0


def test_monotonicity_score_perfect():
    """完美單調時分數為 1.0。"""
    tester = MonotonicityTester({})
    quantile_returns = {
        "quantile_mean_returns": {"Q1": 0.1, "Q2": 0.2, "Q3": 0.3}
    }
    score = tester.compute_monotonicity_score(quantile_returns)
    assert score == 1.0


def test_quantile_downgrade_to_three():
    """樣本不足時自動降級到 3 分位。"""
    # 仍需 ≥ MIN_SAMPLES 才有 PIT 有效 bin；min_group_size 觸發 5→3
    feature = pd.Series(np.linspace(0, 1, 120), name="feature")
    label = pd.Series(np.linspace(0, 1, 120), name="label")
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 25})

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    assert len(result["quantile_mean_returns"]) == 3


def test_long_short_tstat_matches_scipy():
    """Long-Short t-stat 與 scipy 驗算一致（PIT bins）。"""
    n = 300
    feature = pd.Series(np.linspace(0, 1, n), name="feature")
    label = pd.Series(np.linspace(0, 1, n), name="label")
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 10})

    result = tester.compute_long_short_spread(feature, label, num_quantiles=5)

    data = tester._prepare_data(feature, label)
    quantiles = tester._assign_quantiles(data, 5)
    assert quantiles is not None
    valid = quantiles.dropna()
    low_values = data.loc[quantiles == valid.min(), "label"]
    high_values = data.loc[quantiles == valid.max(), "label"]
    expected = stats.ttest_ind(high_values, low_values, nan_policy="omit")

    assert np.isclose(result["tstat"], expected.statistic)
    assert np.isclose(result["pvalue"], expected.pvalue)
    assert "sharpe" in result


def test_empty_data_returns_nan_results():
    """空資料應回傳 NaN 結果。"""
    tester = MonotonicityTester({})
    feature = pd.Series([], dtype=float)
    label = pd.Series([], dtype=float)

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    assert all(np.isnan(value) for value in result["quantile_mean_returns"].values())

    long_short = tester.compute_long_short_spread(feature, label, num_quantiles=5)
    assert np.isnan(long_short["spread"])


def test_quantile_assign_failure_fallbacks():
    """全同值 / 無法形成有效分位時應回傳空結果。"""
    tester = MonotonicityTester({"min_group_size": 1})
    # n < MIN_SAMPLES → 全 bin=NA → empty
    feature = pd.Series([1.0] * 10)
    label = pd.Series(np.linspace(0, 1, 10))

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    assert all(np.isnan(value) for value in result["quantile_mean_returns"].values())


def test_pooled_sharpe_edge_cases():
    """樣本不足或變異為零時 Sharpe 回 NaN。"""
    tester = MonotonicityTester({})
    low_values = pd.Series([1.0])
    high_values = pd.Series([1.0])
    spread = 0.0

    sharpe = tester._compute_pooled_sharpe(low_values, high_values, spread)
    assert np.isnan(sharpe)


def test_monotonicity_score_empty_and_single():
    """空或單一分位數時回 0。"""
    tester = MonotonicityTester({})

    assert tester.compute_monotonicity_score({}) == 0.0
    assert tester.compute_monotonicity_score({"quantile_mean_returns": {"Q1": 0.1}}) == 0.0


def test_monotonicity_score_skips_missing_bins():
    """§P0-2-AGG：缺 bin 的 diff 不計。"""
    tester = MonotonicityTester({})
    # Q2 缺 → 只計 Q1→Q3 的 diff（若直接 nan 相減會誤計）
    score = tester.compute_monotonicity_score(
        {"quantile_mean_returns": {"Q1": 0.1, "Q2": np.nan, "Q3": 0.3}}
    )
    # 僅 Q1→Q3 可形成有限 pair？Q1-Q2 與 Q2-Q3 皆因 Q2 nan 不計 → 0.0
    assert score == 0.0
    # 連續有限：Q1<Q2 缺 Q3 有限 pair 1 個且 >0 → 1.0
    score2 = tester.compute_monotonicity_score(
        {"quantile_mean_returns": {"Q1": 0.1, "Q2": 0.2, "Q3": np.nan}}
    )
    assert score2 == 1.0


def test_quantile_returns_handles_empty_bin(monkeypatch):
    """空分位數應輸出 NaN 與空序列。"""
    tester = MonotonicityTester({})
    feature = pd.Series([1.0, 2.0], name="feature")
    label = pd.Series([0.1, 0.2], name="label")

    def _nan_bins(_data, _num_quantiles):
        return pd.Series([np.nan, np.nan], index=_data.index)

    monkeypatch.setattr(tester, "_assign_quantiles", _nan_bins)
    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)

    assert all(np.isnan(value) for value in result["quantile_mean_returns"].values())
    assert all(values == [] for values in result["cumulative_returns"].values())


def test_long_short_spread_quantile_bins_none(monkeypatch):
    """quantile_bins 為 None 時回 NaN。"""
    tester = MonotonicityTester({})
    feature = pd.Series([1.0, 2.0, 3.0], name="feature")
    label = pd.Series([0.1, 0.2, 0.3], name="label")

    monkeypatch.setattr(tester, "_assign_quantiles", lambda *_args, **_kwargs: None)
    result = tester.compute_long_short_spread(feature, label, num_quantiles=5)
    assert np.isnan(result["spread"])


def test_long_short_spread_empty_groups(monkeypatch):
    """空分組時回 NaN。"""
    tester = MonotonicityTester({})
    feature = pd.Series([1.0, 2.0], name="feature")
    label = pd.Series([0.1, 0.2], name="label")

    def _nan_bins(_data, _num_quantiles):
        return pd.Series([np.nan, np.nan], index=_data.index)

    monkeypatch.setattr(tester, "_assign_quantiles", _nan_bins)
    result = tester.compute_long_short_spread(feature, label, num_quantiles=5)
    assert np.isnan(result["spread"])


def test_assign_quantiles_error_paths(monkeypatch):
    """pit_expanding_qcut_label 例外時回退或 None。"""
    tester = MonotonicityTester({})
    data = pd.DataFrame({"feature": [1.0, 2.0, 3.0], "label": [0.1, 0.2, 0.3]})

    def _raise(*_args, **_kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(
        "momentum.Analysis.monotonicity_tester.pit_expanding_qcut_label", _raise
    )
    assert tester._assign_quantiles(data, 5) is None


def test_assign_quantiles_actual_bins_less():
    """實際分位數少於要求時降級到 3（長序列、少量 unique）。"""
    tester = MonotonicityTester({"min_group_size": 1})
    # 兩個 level 重複 ≥ MIN_SAMPLES，duplicates=drop 使 actual bins < 5 → 降 3
    feature = pd.Series(
        [0.0] * (MIN_SAMPLES // 2) + [1.0] * (MIN_SAMPLES // 2 + 50), name="feature"
    )
    label = pd.Series(np.linspace(0, 1, len(feature)), name="label")
    data = pd.concat([feature, label], axis=1)

    bins = tester._assign_quantiles(data, 5)
    assert bins is not None
    # 降級後仍有有效 label
    assert bins.notna().any()


def test_pooled_sharpe_zero_variance():
    """pooled 變異為 0 時回 NaN。"""
    tester = MonotonicityTester({})
    low_values = pd.Series([1.0, 1.0])
    high_values = pd.Series([1.0, 1.0])
    spread = 0.0

    assert np.isnan(tester._compute_pooled_sharpe(low_values, high_values, spread))


def test_assign_quantiles_pit_matches_helper():
    """_assign_quantiles 與 pit_expanding_qcut_label 一致。"""
    n = 150
    feature = pd.Series(np.linspace(0, 1, n), name="feature")
    label = pd.Series(np.linspace(0, 1, n), name="label")
    tester = MonotonicityTester({"min_group_size": 1})
    data = tester._prepare_data(feature, label)
    bins = tester._assign_quantiles(data, 5)
    expected = pit_expanding_qcut_label(data["feature"], q=5, min_samples=MIN_SAMPLES)
    # 若 actual bins < 5 會降級；此 linspace 應保持 5
    pd.testing.assert_series_equal(
        bins.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_long_short_tstat_matches_scipy_nondegenerate_independent_bins():
    """Long-Short t-stat／p 值／spread 對獨立 oracle（非退化）。

    非單調常態特徵＋正相關 label；分組不用產線 _assign_quantiles，而於測試內以
    np.quantile 獨立重算 PIT expanding 5 分位（t≥99 起、當根與歷史共同分位、右閉區間）：
    bin(t) = #{內部分位點 < x_t}。先確認低／高兩組不同且 5 個 bin 皆出現，再與 scipy 比對。
    """
    n = 300
    rng = np.random.default_rng(0)
    f = rng.normal(size=n)
    y = f + rng.normal(scale=0.1, size=n)
    feature = pd.Series(f, name="feature")
    label = pd.Series(y, name="label")
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 10, "min_samples": 100})

    result = tester.compute_long_short_spread(feature, label, num_quantiles=5)

    oracle_bins = np.full(n, -1)
    for t in range(99, n):
        edges = np.quantile(f[: t + 1], [0.2, 0.4, 0.6, 0.8])
        oracle_bins[t] = int(np.sum(edges < f[t]))
    low_y = y[oracle_bins == 0]
    high_y = y[oracle_bins == 4]
    expected = stats.ttest_ind(high_y, low_y)
    assert sorted(set(oracle_bins[oracle_bins >= 0].tolist())) == [0, 1, 2, 3, 4] and len(low_y) > 5 and len(high_y) > 5 and np.isclose(result["tstat"], expected.statistic) and expected.statistic > 5 and np.isclose(result["pvalue"], expected.pvalue) and np.isclose(result["spread"], high_y.mean() - low_y.mean()), f"result={result} expected_t={expected.statistic}"
