"""Task 1.4 驗證：canonical 報酬序列與 T 語意（真實 kline 跑一次回測，禁合成 fixture 冒充）。

mutation §V-9（DSR/資格閘接受 default_730 或 bar_count）須使本檔轉紅。
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.strategy_validation.returns_contract import (
    PeriodReturns,
    extract_period_returns,
)
from momentum.Strategy.vectorized_backtest import VectorizedBacktest

_KLINE = Path("data_cache/feature_klines/kline_cache.h5")
_PARAMS = {
    "entry_threshold": 0.7,
    "exit_threshold": 0.4,
    "stop_loss_atr": 2.0,
    "take_profit_ratio": 3.0,
    "position_sizing_method": "fixed",
    "position_size": 0.1,
    "kelly_fraction": 0.5,
    "max_position_size": 0.25,
    "cooldown_bars": 0,
    "trailing_stop_activation": 0.05,
}


def _real_backtest(timeframe="1h", n=1500):
    """用**真實 kline**（`data_cache/feature_klines/kline_cache.h5`）跑一次回測。

    禁合成 fixture 冒充真實資料（CLAUDE.md 資料真實性）；檔案不存在時 skip 而非造假。
    """
    h5py = pytest.importorskip("h5py")
    if not _KLINE.is_file():
        pytest.skip(f"真實 kline 不存在: {_KLINE}")
    with h5py.File(_KLINE, "r") as fh:
        symbol = sorted(fh.keys())[0]
        data = fh[f"{symbol}/{timeframe}/data"][:n]
    frame = pd.DataFrame(np.asarray(data.tolist(), dtype=object), columns=list(data.dtype.names))
    prices = pd.DataFrame(
        {
            "open": frame["open"].astype(float),
            "high": frame["high"].astype(float),
            "low": frame["low"].astype(float),
            "close": frame["close"].astype(float),
        }
    ).reset_index(drop=True)
    rng = np.random.default_rng(20260817)
    proba = pd.Series(rng.uniform(0.0, 1.0, size=len(prices)))
    atr = pd.Series((prices["high"] - prices["low"]).abs().clip(lower=1e-9).to_numpy())
    return prices, proba, atr


def _result(timeframe="1h", pass_timeframe=True):
    prices, proba, atr = _real_backtest(timeframe)
    return VectorizedBacktest().run_backtest(
        prices, proba, atr, _PARAMS, timeframe=timeframe if pass_timeframe else None
    )


def test_bar_count_has_more_obs_than_trade_level():
    """① 同一 BacktestResult 下 bar_count 之 n_obs 嚴格大於 trade_level（結構性 0 之存在證明）。"""
    result = _result()
    bar = extract_period_returns(result, timeframe="1h", t_semantics="bar_count")
    trade = extract_period_returns(result, timeframe="1h", t_semantics="trade_level")
    assert isinstance(bar, PeriodReturns)
    assert bar.n_obs > trade.n_obs


def test_bar_count_is_not_applicable_with_named_reason():
    """② bar_count ⇒ status 非 ok 且 reason 為契約字面（§V-9 mutation 鎖）。"""
    bar = extract_period_returns(_result(), timeframe="1h", t_semantics="bar_count")
    assert bar.status != "ok"
    assert bar.reason == "t_semantics_inflates_significance"
    assert bar.values.size > 0  # 值仍回傳供診斷


def test_default_730_is_rejected():
    """③ annualization_source=default_730 ⇒ status 非 ok（拒絕隱性 730）。"""
    result = _result(pass_timeframe=False)
    assert result.annualization["source"] == "default_730"
    got = extract_period_returns(result, timeframe="1h", t_semantics="trade_level")
    assert got.status != "ok"
    assert got.reason == "annualization_unresolved"


def test_missing_annualization_field_is_fail_closed():
    """⑤ 舊物件（無 annualization 欄）⇒ annualization_unresolved，禁假設 730。"""

    class _Legacy:
        equity_curve = pd.Series([1.0, 1.01, 1.02])
        trades = []

    got = extract_period_returns(_Legacy(), timeframe="1h", t_semantics="trade_level")
    assert got.status != "ok"
    assert got.reason == "annualization_unresolved"


def test_trade_level_periods_per_year_matches_trades_per_year():
    """④ trade_level 之 periods_per_year ＝ 交易數 / 可用年數（固定 fixture，atol=1e-9）。"""
    result = _result()
    trade = extract_period_returns(result, timeframe="1h", t_semantics="trade_level")
    n_bars = len(result.equity_curve)
    years = n_bars / 8760
    expected = trade.n_obs / years
    assert trade.periods_per_year == pytest.approx(expected, abs=1e-9)


def test_nonzero_return_bars_is_ok_and_drops_zeros():
    """nonzero_return_bars 為 DSR 合法輸入之一，且確實濾掉結構性 0。"""
    result = _result()
    bar = extract_period_returns(result, timeframe="1h", t_semantics="bar_count")
    nz = extract_period_returns(result, timeframe="1h", t_semantics="nonzero_return_bars")
    assert nz.status == "ok"
    assert nz.n_obs <= bar.n_obs
    assert not np.any(nz.values == 0.0)


def test_source_artifact_hash_is_stable_and_input_bound():
    """`source_artifact_hash` 同一結果重取相同；不同結果不同（供 DSR snapshot 綁定）。"""
    result = _result()
    a = extract_period_returns(result, timeframe="1h", t_semantics="trade_level")
    b = extract_period_returns(result, timeframe="1h", t_semantics="nonzero_return_bars")
    assert a.source_artifact_hash == b.source_artifact_hash
    assert len(a.source_artifact_hash) == 64

    other = _result(timeframe="4h")
    c = extract_period_returns(other, timeframe="4h", t_semantics="trade_level")
    assert c.source_artifact_hash != a.source_artifact_hash


def test_unknown_t_semantics_raises():
    with pytest.raises(ValueError):
        extract_period_returns(_result(), timeframe="1h", t_semantics="whatever")


def test_unknown_timeframe_propagates():
    from momentum.core.frequency import UnknownTimeframeError

    with pytest.raises(UnknownTimeframeError):
        extract_period_returns(_result(), timeframe="7m", t_semantics="trade_level")


def test_no_trades_yields_zero_obs_without_crash():
    """邊界①：無交易 ⇒ n_obs=0，不 crash、不回 NaN 汙染。"""

    class _NoTrades:
        equity_curve = pd.Series([1.0, 1.0, 1.0])
        trades = []
        annualization = {"source": "resolved", "periods_per_year": 8760, "timeframe": "1h"}

    got = extract_period_returns(_NoTrades(), timeframe="1h", t_semantics="trade_level")
    assert got.n_obs == 0
    assert got.status == "ok"
    assert math.isfinite(got.periods_per_year)
