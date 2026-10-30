import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.pit_stats import (
    MIN_SAMPLES,
    first_valid_index,
    pit_expanding_qcut_label,
    pit_expanding_qcut_top_mask,
    pit_expanding_rank,
)
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer


def _long_series(n: int = 200, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(size=n).cumsum())


def _ref_pit_top_mask(series: pd.Series, q: int) -> pd.Series:
    """獨立逐根參考：第 t 根以截至 t 之有限歷史求 q 分位邊界（去重），當根值落最高箱 ⇒ 1.0。

    有效根：截至 t 之有限值數（±inf 不計；ICPERF Task 0.4 ⑰ FR-10：分箱最少樣本只計有限值，舊版同 §MS
    effective_count 把 ±inf 計入，致有限值不足 MIN_SAMPLES 即分箱）≥ MIN_SAMPLES 且當根有限。
    pd.qcut 箱為右閉、首箱含最小值 ⇒ 最高箱＝(edges[-2], edges[-1]]；只剩一箱時恆為最高箱；
    有限歷史全相同（去重後只一個邊界、無箱）⇒ 無標籤 ⇒ NaN（SPEC Task 0.4 ①）。
    """
    values = series.to_numpy(dtype=float)
    out = np.full(values.shape[0], np.nan)
    seen = 0
    for t in range(values.shape[0]):
        seen += int(np.isfinite(values[t]))  # ICPERF Task 0.4 ⑰ FR-10：只計有限值
        if seen < MIN_SAMPLES or not np.isfinite(values[t]):
            continue
        hist = values[: t + 1]
        finite = hist[np.isfinite(hist)]
        edges = np.unique(np.quantile(finite, np.linspace(0.0, 1.0, q + 1)))
        if edges.size == 1:
            continue
        out[t] = 1.0 if edges.size == 2 or values[t] > edges[-2] else 0.0
    return pd.Series(out, index=series.index)


def _boundary_series(case: str) -> pd.Series:
    n = MIN_SAMPLES + 40
    if case == "all_identical":
        return pd.Series(np.ones(n))
    if case == "identical_then_new":
        vals = np.ones(n)
        vals[MIN_SAMPLES + 5 :] = np.arange(2.0, 2.0 + n - MIN_SAMPLES - 5)
        return pd.Series(vals)
    vals = _long_series(n, seed=11).to_numpy(copy=True)  # nan_inf_mixed
    vals[[3, 50, MIN_SAMPLES + 2, MIN_SAMPLES + 20]] = np.nan
    vals[[7, MIN_SAMPLES + 4]] = np.inf
    vals[[60, MIN_SAMPLES + 9]] = -np.inf
    return pd.Series(vals)


@pytest.mark.parametrize("case", ["all_identical", "identical_then_new", "nan_inf_mixed"])
def test_top_mask_and_turnover_boundaries_match_reference(case):
    """頂分位遮罩與單值換手率之邊界（CODEX-R34-P1-01）：全相同 ⇒ 無標籤 NaN、換手率 NaN；
    全相同後出現新值 ⇒ 新值起有標籤；NaN／±inf 混合 ⇒ 有效根依有限值計數（ICPERF Task 0.4 ⑰ FR-10；舊為非 NaN）。"""
    series = _boundary_series(case)
    ref = _ref_pit_top_mask(series, q=5)
    mask = pit_expanding_qcut_top_mask(series, q=5, min_samples=MIN_SAMPLES, duplicates="drop")
    turnover = TurnoverAnalyzer({"num_quantiles": 5}).compute_quantile_turnover(series, num_quantiles=5)
    expected = (
        float("nan") if ref.notna().sum() == 0
        else float(ref.diff().abs().replace([np.inf, -np.inf], np.nan).dropna().mean())
    )

    assert np.array_equal(mask.to_numpy(), ref.to_numpy(), equal_nan=True)
    assert (np.isnan(turnover) and np.isnan(expected)) or np.isclose(turnover, expected)
    assert (ref.notna().sum() == 0) == (case == "all_identical")


@pytest.mark.parametrize("seed", [1, 2])
def test_quantile_turnover_matches_expected(seed):
    """頂部分位變化比例＝逐根 PIT 參考之頂分位遮罩 |Δ| 均值（ICPERF Task 0.4 ①）。

    舊預期以整段最大標籤界定頂分位（讀 t 之後資料）：seed=1 序列一路下行、當根標籤只到 1，
    舊法把第 2 檔當頂分位而得 0.1667；逐根定義下從未進第 5 檔 ⇒ 0.0。
    """
    series = _long_series(220, seed=seed)
    analyzer = TurnoverAnalyzer({"num_quantiles": 5})

    turnover = analyzer.compute_quantile_turnover(series, num_quantiles=5)

    top_mask = _ref_pit_top_mask(series, q=5)
    expected = float(top_mask.diff().abs().replace([np.inf, -np.inf], np.nan).dropna().mean())
    assert np.isclose(turnover, expected)


def test_rank_change_rate_for_increasing_series():
    """遞增序列的 PIT rank change 均值應為 1（有效段）。"""
    # dense increasing: rank(t)=t+1 → |Δrank|=1 for t>=1 once both sides valid
    series = pd.Series(np.arange(1, MIN_SAMPLES + 50, dtype=float))
    analyzer = TurnoverAnalyzer({})

    rate = analyzer.compute_rank_change_rate(series)

    assert np.isclose(rate, 1.0)


def test_factor_autocorrelation_matches_pandas():
    """因子自相關應與 pandas.autocorr 一致。"""
    series = pd.Series([1, 2, 3, 4, 5, 6, 7])
    analyzer = TurnoverAnalyzer({})

    autocorr = analyzer.compute_factor_autocorrelation(series)

    assert np.isclose(autocorr, series.autocorr(lag=1))


def test_compute_all_outputs_metrics():
    """批次輸出包含必要欄位。"""
    df = pd.DataFrame(
        {
            "feature_a": _long_series(150, seed=2),
            "feature_b": _long_series(150, seed=3),
        }
    )
    analyzer = TurnoverAnalyzer({"num_quantiles": 3})

    results = analyzer.compute_all(df, num_quantiles=3)

    assert set(results.keys()) == {"feature_a", "feature_b"}
    assert "quantile_turnover" in results["feature_a"]
    assert "rank_change_rate" in results["feature_a"]
    assert "autocorrelation" in results["feature_a"]
    assert "time_series" in results["feature_a"]
    ts = results["feature_a"]["time_series"]
    assert len(ts["quantile_turnovers"]) == len(df["feature_a"])


def test_cost_drag_proxy_hand_calc():
    """成本拖累手算:(10/1e4)*1.5==0.0015(§T 無 ×2;舊 0.1-0.01×2=0.08 固化混量綱+四腿=錯)。"""
    analyzer = TurnoverAnalyzer({})

    drag = analyzer.compute_cost_drag_proxy(turnover_rate=1.5, cost_bps=10.0)

    assert np.isclose(drag, 0.0015)


def test_cost_drag_proxy_zero_turnover():
    """邊界:turnover=0 → 0.0。"""
    analyzer = TurnoverAnalyzer({})
    assert analyzer.compute_cost_drag_proxy(turnover_rate=0.0, cost_bps=10.0) == 0.0


def test_turnover_handles_empty_and_qcut_failure(monkeypatch):
    """空序列與 pit qcut 失敗應回 NaN。"""
    analyzer = TurnoverAnalyzer({})

    assert np.isnan(analyzer.compute_quantile_turnover(pd.Series([], dtype=float)))

    def _raise(*_args, **_kwargs):
        raise ValueError("qcut fail")

    monkeypatch.setattr(
        "momentum.Analysis.turnover_analyzer.pit_expanding_qcut_top_mask", _raise
    )
    series = pd.Series([1.0, 2.0, 3.0])
    assert np.isnan(analyzer.compute_quantile_turnover(series, num_quantiles=5))


def test_rank_change_and_autocorr_empty():
    """資料不足時回 NaN。"""
    analyzer = TurnoverAnalyzer({})
    series = pd.Series([1.0])

    assert np.isnan(analyzer.compute_rank_change_rate(series))
    assert np.isnan(analyzer.compute_factor_autocorrelation(series))


def test_rank_change_short_warmup_nan():
    """n < min_samples：無有效 PIT rank → NaN。"""
    analyzer = TurnoverAnalyzer({})
    series = pd.Series(np.arange(1, 20, dtype=float))
    assert np.isnan(analyzer.compute_rank_change_rate(series))


def test_cost_drag_proxy_nan_turnover_raises():
    """舊斷言為何錯:nan→nan 靜默;SPEC v1.1=負/非有限 turnover→raise ValueError(禁 clamp)。"""
    analyzer = TurnoverAnalyzer({})

    with pytest.raises(ValueError):
        analyzer.compute_cost_drag_proxy(turnover_rate=float("nan"), cost_bps=10.0)


def test_cost_drag_proxy_negative_turnover_raises():
    analyzer = TurnoverAnalyzer({})
    with pytest.raises(ValueError):
        analyzer.compute_cost_drag_proxy(turnover_rate=-0.2, cost_bps=10.0)


def test_mutation_m8_restore_proxy_subtraction(monkeypatch):
    """M8:恢復 proxy 混減(gross_ic - λ×turnover) → 手算紅。"""
    analyzer = TurnoverAnalyzer({})

    def mixed(self, turnover_rate, cost_bps=None, gross_ic=0.1, transaction_cost=0.01):  # type: ignore[no-untyped-def]
        # 舊混量綱:0.1 - 0.01*2 = 0.08 路徑
        return float(gross_ic - transaction_cost * float(turnover_rate))

    monkeypatch.setattr(TurnoverAnalyzer, "compute_cost_drag_proxy", mixed)
    with pytest.raises(AssertionError):
        drag = analyzer.compute_cost_drag_proxy(turnover_rate=1.5, cost_bps=10.0)
        assert np.isclose(drag, 0.0015)


def test_compute_all_defaults_num_quantiles():
    """compute_all 應使用預設分位數。"""
    analyzer = TurnoverAnalyzer({"num_quantiles": 3})
    df = pd.DataFrame(
        {
            "feature_a": _long_series(120, seed=4).tolist(),
            "feature_b": _long_series(120, seed=5).tolist(),
        }
    )

    results = analyzer.compute_all(df, num_quantiles=None)

    assert set(results.keys()) == {"feature_a", "feature_b"}


def test_quantile_turnover_empty_changes(monkeypatch):
    """changes 全非有限時回 0。"""
    analyzer = TurnoverAnalyzer({})
    series = _long_series(150, seed=6)

    def _all_nan(series, q, min_samples=MIN_SAMPLES, duplicates="drop"):  # noqa: ARG001
        return pd.Series(np.nan, index=series.index if hasattr(series, "index") else None)

    # Force quantiles valid but constant top mask with no finite diffs via all-nan quantiles
    # → compute path returns nan (no valid labels). Instead force top_mask diffs empty:
    def _const_top(series, q, min_samples=MIN_SAMPLES, duplicates="drop"):  # noqa: ARG001
        # single label at first_valid only → diff mostly nan; mean of empty → 0.0
        out = pd.Series(np.nan, index=series.index)
        fv = first_valid_index(series, min_samples=min_samples)
        if fv is not None:
            out.iloc[fv:] = 1.0  # always top, never change
        return out

    monkeypatch.setattr(
        "momentum.Analysis.turnover_analyzer.pit_expanding_qcut_top_mask", _const_top
    )
    assert analyzer.compute_quantile_turnover(series, num_quantiles=5) == 0.0


def test_rank_change_rate_empty_diffs(monkeypatch):
    """diffs 空時回 0。"""
    analyzer = TurnoverAnalyzer({})
    series = _long_series(150, seed=7)

    def _const_rank(series, min_samples=MIN_SAMPLES, ties="average"):  # noqa: ARG001
        out = pd.Series(np.nan, index=series.index)
        fv = first_valid_index(series, min_samples=min_samples)
        if fv is not None:
            out.iloc[fv:] = 1.0  # constant rank → |diff|=0
        return out

    monkeypatch.setattr(
        "momentum.Analysis.turnover_analyzer.pit_expanding_rank", _const_rank
    )
    assert analyzer.compute_rank_change_rate(series) == 0.0


def test_compute_turnover_time_series_structure():
    """Turnover 時序：長度=源 n、含 null warmup、timestamps 對齊。"""
    analyzer = TurnoverAnalyzer({"num_quantiles": 3})
    series = pd.Series(
        np.linspace(0, 1, 150),
        index=np.arange(100, 250),
    )

    result = analyzer.compute_turnover_time_series(series, num_quantiles=3)

    assert set(result.keys()) == {
        "quantile_turnovers",
        "rank_change_rates",
        "timestamps",
    }
    n = len(series)
    assert len(result["quantile_turnovers"]) == n
    assert len(result["rank_change_rates"]) == n
    assert len(result["timestamps"]) == n
    assert all(isinstance(ts, int) for ts in result["timestamps"])

    fv = first_valid_index(series, min_samples=MIN_SAMPLES)
    assert fv is not None
    # warmup [0, first_valid) = JSON null；t=first_valid 本身 == 0.0（RULING-5）
    assert all(v is None for v in result["quantile_turnovers"][:fv])
    assert all(v is None for v in result["rank_change_rates"][:fv])
    assert result["quantile_turnovers"][fv] == 0.0
    assert result["rank_change_rates"][fv] == 0.0
    # post-first_valid 允許 float（或偶發 non-finite→null）
    for v in result["quantile_turnovers"][fv:]:
        assert v is None or isinstance(v, float)


def test_compute_turnover_time_series_qcut_failure(monkeypatch):
    """pit qcut 失敗時仍對齊源 n 全 null，不拋例外。"""
    analyzer = TurnoverAnalyzer({})
    series = pd.Series([1.0, 2.0, 3.0, 4.0])

    def _raise(*_args, **_kwargs):
        raise ValueError("qcut fail")

    monkeypatch.setattr(
        "momentum.Analysis.turnover_analyzer.pit_expanding_qcut_top_mask", _raise
    )
    result = analyzer.compute_turnover_time_series(series, num_quantiles=4)
    assert len(result["quantile_turnovers"]) == len(series)
    assert len(result["rank_change_rates"]) == len(series)
    assert len(result["timestamps"]) == len(series)
    assert all(v is None for v in result["quantile_turnovers"])
    assert all(v is None for v in result["rank_change_rates"])


def test_quantile_turnover_hand_computed_top_entries_exits():
    """頂分位換手率之獨立手算 oracle（不重抄生產公式）。

    序列：前 MIN_SAMPLES 根為 1..MIN_SAMPLES 嚴格遞增（第 MIN_SAMPLES 根＝歷史最大 ⇒ 頂分位 label 4）；
    其後每根若為「新高」⇒ 頂分位 4、「新低」⇒ 底分位 0。狀態（自 t=MIN_SAMPLES-1）：
    T T T B T B B T T ⇒ 頂分位遮罩 1 1 1 0 1 0 0 1 1 ⇒ |Δ| 自 t=MIN_SAMPLES 起 0 0 1 1 1 0 1 0 ⇒ 均值 4/8＝0.5。
    """
    pattern = ["T", "T", "B", "T", "B", "B", "T", "T"]
    vals = list(np.arange(1, MIN_SAMPLES + 1, dtype=float))
    hi, lo = float(MIN_SAMPLES), 1.0
    for p in pattern:
        if p == "T":
            hi += 1000.0
            vals.append(hi)
        else:
            lo -= 1000.0
            vals.append(lo)
    series = pd.Series(vals)
    hand_labels = [np.nan] * (MIN_SAMPLES - 1) + [4.0] + [4.0 if p == "T" else 0.0 for p in pattern]

    labels = pit_expanding_qcut_label(series, q=5, min_samples=MIN_SAMPLES, duplicates="drop")
    turnover = TurnoverAnalyzer({"num_quantiles": 5}).compute_quantile_turnover(series, num_quantiles=5)

    assert np.isclose(turnover, 0.5) and np.array_equal(labels.to_numpy(), np.array(hand_labels), equal_nan=True), \
        f"turnover={turnover}"
