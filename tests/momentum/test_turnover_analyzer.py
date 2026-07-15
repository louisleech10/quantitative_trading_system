import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.pit_stats import (
    MIN_SAMPLES,
    first_valid_index,
    pit_expanding_qcut_label,
    pit_expanding_rank,
)
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer


def _long_series(n: int = 200, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(size=n).cumsum())


def test_quantile_turnover_matches_expected():
    """頂部分位變化比例計算正確（PIT qcut）。"""
    series = _long_series(220, seed=1)
    analyzer = TurnoverAnalyzer({"num_quantiles": 5})

    turnover = analyzer.compute_quantile_turnover(series, num_quantiles=5)

    quantiles = pit_expanding_qcut_label(
        series, q=5, min_samples=MIN_SAMPLES, duplicates="drop"
    )
    max_label = quantiles.max(skipna=True)
    top_mask = (quantiles == max_label).astype(float).where(quantiles.notna(), np.nan)
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
        "momentum.Analysis.turnover_analyzer.pit_expanding_qcut_label", _raise
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
            out.iloc[fv:] = 0.0  # always top, never change
        return out

    monkeypatch.setattr(
        "momentum.Analysis.turnover_analyzer.pit_expanding_qcut_label", _const_top
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
        "momentum.Analysis.turnover_analyzer.pit_expanding_qcut_label", _raise
    )
    result = analyzer.compute_turnover_time_series(series, num_quantiles=4)
    assert len(result["quantile_turnovers"]) == len(series)
    assert len(result["rank_change_rates"]) == len(series)
    assert len(result["timestamps"]) == len(series)
    assert all(v is None for v in result["quantile_turnovers"])
    assert all(v is None for v in result["rank_change_rates"])
