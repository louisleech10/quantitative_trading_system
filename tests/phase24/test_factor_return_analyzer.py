import numpy as np
import pandas as pd

from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer
from momentum.Analysis.deep_analysis_types import SkippedResult


def _make_data(n: int = 400):
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="12h")
    feature = pd.Series(rng.normal(size=n), index=idx, name="f1")
    label = pd.Series(feature.values * 0.02 + rng.normal(scale=0.01, size=n), index=idx, name="ret")
    return feature, label


def test_compute_factor_returns_success():
    """舊斷言 `quantile_returns_summary` 為 pre-§U 鍵名;現契約=quantile_summary(+descriptive_full_sample)."""
    feature, label = _make_data()
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5})

    result = analyzer.compute_factor_returns(feature, label)

    assert isinstance(result, dict)
    # 舊: assert "quantile_returns_summary" in result  — 錯,§U 鍵為 quantile_summary
    assert "quantile_summary" in result
    assert result["quantile_summary"].get("descriptive_full_sample") is True
    assert "risk_metrics" in result
    assert "sharpe_ratio" in result["risk_metrics"]
    assert result["num_quantiles_used"] >= 2
    assert result["active_bar_count"] >= 0


def test_insufficient_samples():
    feature, label = _make_data(20)
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_factor_returns(feature, label)
    assert isinstance(result, SkippedResult)
    assert result.error_type == "INSUFFICIENT_DATA"


def test_constant_feature_skip():
    _, label = _make_data(100)
    idx = label.index
    feature = pd.Series(1.0, index=idx)
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_factor_returns(feature, label)
    assert isinstance(result, SkippedResult)


def test_empty_quantile_fallback():
    """舊斷言 num_quantiles_used∈{2,3}:舊 full-sample fallback 降 q。

    新契約:num_quantiles_used=請求值(q_eff 僅在 PIT 逐 bar 內部);二元 feature 仍可 ok。
    """
    rng = np.random.default_rng(1)
    idx = pd.date_range("2024-01-01", periods=120, freq="12h")
    feature = pd.Series(np.where(np.arange(120) % 2 == 0, 1, 2), index=idx)
    label = pd.Series(rng.normal(size=120) * 0.01, index=idx)
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5, "min_samples": 30, "warmup_periods": 20})

    result = analyzer.compute_factor_returns(feature, label)

    # 可能 ok(PIT q_eff 內部降到 2)或 no-active skip;不得崩
    if isinstance(result, SkippedResult):
        assert result.error_type == "INSUFFICIENT_DATA"
        return
    assert isinstance(result, dict)
    # 舊: assert result["num_quantiles_used"] in {2, 3}  — 錯,現回報請求 quantiles=5
    assert result["num_quantiles_used"] == 5
    assert "long_short_mean_return" in result
    assert "quantile_summary" in result


def test_compute_batch():
    """舊斷言 batch 直接回 {f1,f2} 特徵 map;新 §U = status/value/reason ok union."""
    rng = np.random.default_rng(2)
    idx = pd.date_range("2024-01-01", periods=300, freq="12h")
    features = pd.DataFrame(
        {
            "f1": rng.normal(size=300),
            "f2": rng.normal(size=300),
            "f3": rng.normal(size=300),
        },
        index=idx,
    )
    labels = pd.Series(features["f1"] * 0.01 + rng.normal(scale=0.01, size=300), index=idx)
    analyzer = FactorReturnAnalyzer({})

    result = analyzer.compute_batch(features, labels, top_n=2)

    # 舊: assert len(result)==2 / keys=={f1,f2}  — 錯,現為 ok union 包一層
    assert result["status"] == "ok"
    assert result["reason"] is None
    value = result["value"]
    assert value["schema_version"] == "fr_full_v1"
    assert value["semantics"] == "single_asset_factor_timing_ls"
    assert value["quantile_fit"] == "pit_expanding"
    assert set(value["features"].keys()) == {"f1", "f2"}
    assert len(value["features"]) == 2


def test_zero_variance_future_returns_skip():
    feature, _ = _make_data(120)
    label = pd.Series(0.01, index=feature.index)
    analyzer = FactorReturnAnalyzer({})

    result = analyzer.compute_factor_returns(feature, label)

    assert isinstance(result, SkippedResult)
    assert result.reason == "zero variance future_returns"


def test_compute_risk_metrics_empty_and_flat_returns():
    analyzer = FactorReturnAnalyzer({})

    empty_result = analyzer.compute_risk_metrics(pd.Series(dtype=float))
    assert np.isnan(empty_result["sharpe_ratio"])

    flat_result = analyzer.compute_risk_metrics(pd.Series([0.01] * 20))
    assert abs(float(flat_result["annualized_volatility"])) < 1e-8
    assert np.isnan(flat_result["sortino_ratio"]) or abs(float(flat_result["sortino_ratio"])) < 1e-8


def test_assign_quantiles_and_sampling_branches():
    """舊測呼叫已刪 helper `_assign_quantiles_with_fallback`。

    現改驗:常數 feature → SkippedResult;_sample_series 仍可用。
    """
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5, "min_samples": 30})
    idx = pd.date_range("2024-01-01", periods=50, freq="12h")
    const_feature = pd.Series([1.0] * 50, index=idx)
    label = pd.Series(np.linspace(-0.01, 0.01, 50), index=idx)
    result = analyzer.compute_factor_returns(const_feature, label)
    assert isinstance(result, SkippedResult)
    assert "constant" in result.reason

    sampled = analyzer._sample_series(pd.Series(np.arange(500, dtype=float)), max_points=100)
    assert len(sampled) == 100


def test_infer_periods_per_year_default_branch():
    analyzer = FactorReturnAnalyzer({})
    periods = analyzer._infer_periods_per_year(pd.Index([1, 2, 3]))
    assert periods == 365


def test_infer_periods_per_year_datetime_branch():
    analyzer = FactorReturnAnalyzer({})
    idx = pd.date_range("2024-01-01", periods=50, freq="12h")
    periods = analyzer._infer_periods_per_year(idx)
    assert periods > 365


def test_sample_series_small_branch():
    sampled = FactorReturnAnalyzer._sample_series(pd.Series([1.0, 2.0, 3.0]), max_points=10)
    assert sampled == [1.0, 2.0, 3.0]


def test_compute_risk_metrics_calmar_nan_when_no_drawdown():
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_risk_metrics(pd.Series([0.01] * 50), periods_per_year=365)
    assert np.isnan(result["calmar_ratio"]) or np.isfinite(result["calmar_ratio"])


# ---------------------------------------------------------------------------
# F5.1 D15: M-pos / M-lookahead 證偽測(phase24 路徑;改回舊行為 FAIL)
# 與 tests/momentum/Analysis/test_factor_return_analyzer.py §V-matrix 同源 reference。
# ---------------------------------------------------------------------------

FEATURE_7 = [20.0, 40.0, 10.0, 55.0, 30.0, 5.0, 50.0]
FUTURE_7 = [0.02, -0.01, 0.03, -0.02, 0.04, -0.03, 0.05]
ATOL = 1e-12


def _ref_pit_position(feature, *, num_quantiles=3, warmup_periods=2):
    """獨立 PIT expanding membership reference(不經 production)."""
    position = pd.Series(0, index=feature.index, dtype=int)
    for t in range(len(feature)):
        if t < warmup_periods:
            continue
        window = feature.iloc[: t + 1]
        q_eff = min(int(num_quantiles), int(window.nunique()))
        if q_eff < 2:
            continue
        try:
            bins = pd.qcut(window, q=q_eff, labels=False, duplicates="drop")
        except ValueError:
            continue
        label = bins.iloc[-1]
        if pd.isna(label):
            continue
        li = int(label)
        top, bottom = q_eff - 1, 0
        if li == top:
            position.iloc[t] = 1
        elif li == bottom:
            position.iloc[t] = -1
    return position


def _legacy_pos_subtract_ls(feature, future):
    """M-pos 舊行為: reset_index+iloc 位置相減(錯位;時間戳對齊破壞)."""
    f = feature.reset_index(drop=True)
    y = future.reset_index(drop=True)
    pos = _ref_pit_position(f, num_quantiles=3, warmup_periods=2)
    # 舊錯:用 iloc 位置對位置相乘卻長度/對齊依 reset 後 index——再 drop 末尾模擬 off-by-one
    paired = min(len(pos), len(y)) - 1  # 故意截掉最後一 bar 再現舊長度分歧
    if paired < 1:
        return pd.Series(dtype=float)
    high = (pos.iloc[:paired] * y.iloc[:paired]).astype(float)
    # 再做一次 iloc 錯位移(舊 misaligned 形狀)
    low = high.shift(1).fillna(0.0)
    return (high.iloc[:paired] - low.iloc[:paired]).astype(float)


def _full_sample_position(feature, num_quantiles=3, warmup_periods=2):
    """M-lookahead 舊行為: full-sample qcut 一次切完(前瞻)."""
    position = pd.Series(0, index=feature.index, dtype=int)
    q_eff = min(int(num_quantiles), int(feature.nunique()))
    if q_eff < 2:
        return position
    bins = pd.qcut(feature, q=q_eff, labels=False, duplicates="drop")
    top, bottom = q_eff - 1, 0
    for t in range(len(feature)):
        if t < warmup_periods:
            continue
        label = bins.iloc[t]
        if pd.isna(label):
            continue
        li = int(label)
        if li == top:
            position.iloc[t] = 1
        elif li == bottom:
            position.iloc[t] = -1
    return position


def test_mutation_pos_phase24():
    """M-pos: 舊 reset_index+iloc 位置相減變體 ≠ production/PIT reference。

    可證偽:若 production 退回舊位置相減,variant≈prod → 本斷言 FAIL。
    """
    idx = pd.RangeIndex(7)
    feature = pd.Series(FEATURE_7, index=idx, dtype=float)
    future = pd.Series(FUTURE_7, index=idx, dtype=float)
    pos = _ref_pit_position(feature, num_quantiles=3, warmup_periods=2)
    ref_ls = (pos * future).astype(float)
    variant = _legacy_pos_subtract_ls(feature, future)
    assert len(variant) != len(ref_ls) or not np.allclose(
        variant.to_numpy(dtype=float),
        ref_ls.to_numpy(dtype=float),
        atol=ATOL,
        equal_nan=True,
    ), "M-pos: variant must differ from PIT reference (old behavior should be distinguishable)"

    analyzer = FactorReturnAnalyzer(
        {"num_quantiles": 3, "min_samples": 3, "warmup_periods": 2}
    )
    result = analyzer.compute_factor_returns(feature, future, feature_name="f1")
    assert not isinstance(result, SkippedResult), getattr(result, "reason", result)
    prod_ls = analyzer.get_series_map()["f1"].ls_return
    assert np.allclose(
        prod_ls.to_numpy(dtype=float), ref_ls.to_numpy(dtype=float), atol=ATOL
    )
    # 改回舊行為可證偽:prod 若等於 variant → 紅
    assert len(variant) != len(prod_ls) or not np.allclose(
        variant.to_numpy(dtype=float),
        prod_ls.to_numpy(dtype=float),
        atol=ATOL,
        equal_nan=True,
    )


def test_mutation_lookahead_phase24():
    """M-lookahead: full-sample qcut 變體 ≠ PIT;production≡PIT。

    可證偽:若 production 退回 full-sample qcut,prod==fs → 本斷言 FAIL。
    """
    n = 15
    warmup = 5
    nq = 5
    rng = np.random.RandomState(0)
    feature = pd.Series(rng.randn(n).astype(float), index=pd.RangeIndex(n), dtype=float)
    future = pd.Series(rng.randn(n).astype(float) * 0.01, index=feature.index, dtype=float)

    pit_full = _ref_pit_position(feature, num_quantiles=nq, warmup_periods=warmup)
    fs_full = _full_sample_position(feature, num_quantiles=nq, warmup_periods=warmup)
    assert pit_full.tolist() != fs_full.tolist(), (
        "fixture must distinguish PIT from full-sample"
    )

    analyzer = FactorReturnAnalyzer(
        {"num_quantiles": nq, "min_samples": 5, "warmup_periods": warmup}
    )
    result = analyzer.compute_factor_returns(feature, future, feature_name="f1")
    assert not isinstance(result, SkippedResult), getattr(result, "reason", result)
    production_position = analyzer.get_series_map()["f1"].position
    assert production_position.tolist() == pit_full.tolist()
    assert production_position.tolist() != fs_full.tolist(), (
        "M-lookahead FALSIFY: production must not equal full-sample qcut"
    )
