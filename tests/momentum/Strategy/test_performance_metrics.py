import numpy as np
import pandas as pd
import pytest

from momentum.Strategy.performance_metrics import PerformanceMetrics
from momentum.Strategy.performance_metrics import _safe_float
from momentum.Strategy.vectorized_backtest import Trade


@pytest.fixture
def sample_equity_curve():
    return pd.Series([1.0, 1.02, 1.01, 1.05, 1.08, 1.06, 1.10])


@pytest.fixture
def sample_trades():
    base_time = pd.Timestamp("2025-01-01")
    return [
        Trade(base_time, 100, base_time, 105, 0.1, "long", 0.005, 0.05, "take_profit", -0.01, 0.05),
        Trade(base_time, 105, base_time, 100, 0.1, "long", -0.004, -0.04, "stop_loss", -0.04, 0.01),
        Trade(base_time, 100, base_time, 110, 0.1, "long", 0.008, 0.08, "signal_exit", -0.01, 0.08),
    ]


def _get_metric_instance(sample_equity_curve, sample_trades):
    return PerformanceMetrics(sample_equity_curve, sample_trades)


@pytest.mark.parametrize(
    "method_name",
    [
        "total_return",
        "cagr",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "max_drawdown",
        "max_drawdown_duration",
        "expectancy",
        "system_quality_number",
        "win_rate",
        "profit_factor",
        "avg_win",
        "avg_loss",
    ],
)
def test_all_metrics_return_numeric(method_name, sample_equity_curve, sample_trades):
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    value = getattr(metrics, method_name)()
    assert isinstance(value, (int, float, np.floating))


@pytest.mark.parametrize(
    "method_name,expected",
    [
        ("total_return", 0.0),
        ("cagr", 0.0),
        ("sharpe_ratio", 0.0),
        ("sortino_ratio", 0.0),
        ("calmar_ratio", 0.0),
        ("max_drawdown", 0.0),
        ("max_drawdown_duration", 0),
        ("expectancy", 0.0),
        ("system_quality_number", 0.0),
        ("win_rate", 0.0),
        ("profit_factor", 0.0),
        ("avg_win", 0.0),
        ("avg_loss", 0.0),
    ],
)
def test_empty_inputs_return_default_zero(method_name, expected):
    metrics = PerformanceMetrics(pd.Series(dtype=float), [])
    value = getattr(metrics, method_name)()
    assert value == expected


@pytest.mark.parametrize("periods_per_year", [0, -1, -730])
def test_invalid_periods_per_year_raise(periods_per_year):
    with pytest.raises(ValueError):
        PerformanceMetrics(pd.Series([1.0, 1.1]), [], periods_per_year=periods_per_year)


@pytest.mark.parametrize(
    "equity_curve,expected_total_return",
    [
        ([1.0, 1.1], 0.1),
        ([1.0, 0.9], -0.1),
        ([1.0, 1.0], 0.0),
    ],
)
def test_total_return(equity_curve, expected_total_return):
    metrics = PerformanceMetrics(pd.Series(equity_curve), [])
    assert metrics.total_return() == pytest.approx(expected_total_return, rel=1e-6)


def test_max_drawdown_negative_value(sample_equity_curve, sample_trades):
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    assert metrics.max_drawdown() <= 0.0


def test_max_drawdown_duration_non_negative(sample_equity_curve, sample_trades):
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    assert metrics.max_drawdown_duration() >= 0


@pytest.mark.parametrize(
    "trade_pnls,expected_win_rate",
    [
        ([1, -1, 2, -2], 0.5),
        ([1, 2, 3], 1.0),
        ([-1, -2], 0.0),
    ],
)
def test_win_rate_calculation(trade_pnls, expected_win_rate):
    now = pd.Timestamp("2025-01-01")
    trades = [
        Trade(now, 100, now, 100, 0.1, "long", float(v), float(v) / 100.0, "signal_exit", 0, 0)
        for v in trade_pnls
    ]
    metrics = PerformanceMetrics(pd.Series([1.0, 1.1]), trades)
    assert metrics.win_rate() == pytest.approx(expected_win_rate, rel=1e-6)


@pytest.mark.parametrize(
    "trade_pnls,expected",
    [
        ([2, -1], 2.0),
        ([4, -2, -2], 1.0),
        ([1, 2], 0.0),
        ([-1, -2], 0.0),
    ],
)
def test_profit_factor(trade_pnls, expected):
    now = pd.Timestamp("2025-01-01")
    trades = [
        Trade(now, 100, now, 100, 0.1, "long", float(v), float(v) / 100.0, "signal_exit", 0, 0)
        for v in trade_pnls
    ]
    metrics = PerformanceMetrics(pd.Series([1.0, 1.1]), trades)
    assert metrics.profit_factor() == pytest.approx(expected, rel=1e-6)


def test_calculate_all_contains_required_keys(sample_equity_curve, sample_trades):
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    result = metrics.calculate_all()
    required = {
        "total_return",
        "cagr",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "max_drawdown",
        "max_drawdown_duration",
        "expectancy",
        "sqn",
        "win_rate",
        "profit_factor",
        "avg_win",
        "avg_loss",
        "total_trades",
    }
    assert required.issubset(set(result.keys()))


@pytest.mark.parametrize(
    "equity_curve",
    [
        [1.0, 1.0, 1.0, 1.0],
        [1.0, np.nan, 1.1, np.nan, 1.2],
        [1.0, np.inf, 1.1, -np.inf, 1.2],
    ],
)
def test_ratio_metrics_handle_boundary_data(equity_curve):
    metrics = PerformanceMetrics(pd.Series(equity_curve), [])
    for method_name in ["sharpe_ratio", "sortino_ratio", "calmar_ratio"]:
        value = getattr(metrics, method_name)()
        assert np.isfinite(value)


def test_sqn_denominator_zero_returns_zero():
    now = pd.Timestamp("2025-01-01")
    trades = [
        Trade(now, 100, now, 101, 0.1, "long", 0.01, 0.01, "signal_exit", 0, 0),
        Trade(now, 100, now, 101, 0.1, "long", 0.01, 0.01, "signal_exit", 0, 0),
    ]
    metrics = PerformanceMetrics(pd.Series([1.0, 1.1, 1.2]), trades)
    assert metrics.system_quality_number() == 0.0


def test_expectancy_with_mixed_trades(sample_equity_curve, sample_trades):
    metrics = PerformanceMetrics(sample_equity_curve, sample_trades)
    value = metrics.expectancy()
    assert isinstance(value, float)


def test_avg_win_and_avg_loss_sign(sample_equity_curve, sample_trades):
    metrics = PerformanceMetrics(sample_equity_curve, sample_trades)
    assert metrics.avg_win() >= 0
    assert metrics.avg_loss() <= 0


def test_cagr_on_short_series_returns_zero():
    metrics = PerformanceMetrics(pd.Series([1.0]), [])
    assert metrics.cagr() == 0.0


def test_total_return_start_non_positive_returns_zero():
    metrics = PerformanceMetrics(pd.Series([0.0, 1.0]), [])
    assert metrics.total_return() == 0.0


def test_max_drawdown_no_drawdown_returns_zero():
    metrics = PerformanceMetrics(pd.Series([1.0, 1.1, 1.2, 1.3]), [])
    assert metrics.max_drawdown() == pytest.approx(0.0)


def test_max_drawdown_duration_no_drawdown_returns_zero():
    metrics = PerformanceMetrics(pd.Series([1.0, 1.1, 1.2, 1.3]), [])
    assert metrics.max_drawdown_duration() == 0


def test_safe_float_type_error_returns_default():
    assert _safe_float(object(), 7.0) == 7.0


def test_init_with_none_equity_curve():
    metrics = PerformanceMetrics(None, [])
    assert metrics.total_return() == 0.0


def test_trade_dict_fields_path_covered():
    trades = [{"pnl": 1.5, "pnl_pct": 0.1}, {"pnl": -1.0, "pnl_pct": -0.05}]
    metrics = PerformanceMetrics(pd.Series([1.0, 1.02, 1.01]), trades)
    assert metrics.win_rate() == pytest.approx(0.5)
    assert metrics.system_quality_number() != 0.0


def test_cagr_end_non_positive_returns_zero():
    metrics = PerformanceMetrics(pd.Series([1.0, 0.0]), [])
    assert metrics.cagr() == 0.0


def test_max_drawdown_exact_hand_value(sample_equity_curve, sample_trades):
    """MDD 手算：曲線峰值 1.08 後跌至 1.06 為最深回撤 ⇒ 1.06/1.08 − 1（另一回撤 1.01/1.02 − 1 較淺）"""
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    assert metrics.max_drawdown() == pytest.approx(1.06 / 1.08 - 1.0, rel=1e-9, abs=1e-12) and metrics.max_drawdown() < 1.01 / 1.02 - 1.0, f"MDD={metrics.max_drawdown()}"


def test_expectancy_exact_hand_value(sample_equity_curve, sample_trades):
    """expectancy 手算：pnl=[0.005, −0.004, 0.008]；勝率 2/3、均贏 0.0065、均虧 0.004
    ⇒ 2/3×0.0065 − 1/3×0.004 = 0.003"""
    metrics = PerformanceMetrics(sample_equity_curve, sample_trades)
    assert metrics.expectancy() == pytest.approx(0.003, rel=1e-9, abs=1e-15), f"expectancy={metrics.expectancy()}"


def test_sharpe_ratio_matches_independent_oracle(sample_equity_curve, sample_trades):
    """Sharpe 獨立 oracle：純 Python 逐期報酬、母體標準差（ddof=0）、rf=0.02/730、×sqrt(730)"""
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    eq = [1.0, 1.02, 1.01, 1.05, 1.08, 1.06, 1.10]
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq))]
    mean_r = sum(rets) / len(rets)
    pstd = (sum((r - mean_r) ** 2 for r in rets) / len(rets)) ** 0.5
    oracle = (mean_r - 0.02 / 730) / pstd * 730 ** 0.5
    assert metrics.sharpe_ratio() == pytest.approx(oracle, rel=1e-9), f"sharpe={metrics.sharpe_ratio()} oracle={oracle}"


def test_sortino_ratio_matches_independent_oracle(sample_equity_curve, sample_trades):
    """Sortino 獨立 oracle：分母只取負報酬之母體標準差（兩筆負報酬：1.01/1.02−1、1.06/1.08−1）"""
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    eq = [1.0, 1.02, 1.01, 1.05, 1.08, 1.06, 1.10]
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq))]
    mean_r = sum(rets) / len(rets)
    downs = [r for r in rets if r < 0]
    d_mean = sum(downs) / len(downs)
    d_std = (sum((r - d_mean) ** 2 for r in downs) / len(downs)) ** 0.5
    oracle = (mean_r - 0.02 / 730) / d_std * 730 ** 0.5
    assert len(downs) == 2 and metrics.sortino_ratio() == pytest.approx(oracle, rel=1e-9), f"sortino={metrics.sortino_ratio()} oracle={oracle}"


def test_cagr_matches_independent_oracle(sample_equity_curve, sample_trades):
    """CAGR 獨立 oracle：7 點曲線＝6 期，年數＝6/730 ⇒ 1.10 ** (730/6) − 1"""
    metrics = _get_metric_instance(sample_equity_curve, sample_trades)
    oracle = 1.10 ** (730.0 / 6.0) - 1.0
    assert metrics.cagr() == pytest.approx(oracle, rel=1e-9), f"cagr={metrics.cagr()} oracle={oracle}"
