"""Task 1.1 驗證：年化頻率解析＋`available_years`（含 §V 反向測試）。

通過條件見 TODO Task 1.1「驗證」欄；mutation §V-8（未知回 730）與 §V-15（`available_years` 回 `n_bars`）
須使本檔轉紅。
"""

import pytest

from momentum.Analysis.strategy_validation.frequency import (
    UnknownTimeframeError,
    available_years,
    resolve_periods_per_year,
)


@pytest.mark.parametrize(
    "timeframe,expected",
    [("1h", 8760), ("4h", 2190), ("12h", 730), ("1d", 365)],
)
def test_resolve_known_timeframes(timeframe, expected):
    assert resolve_periods_per_year(timeframe) == expected


@pytest.mark.parametrize("bad", ["7m", "", None, "1H", 3600, [], "1 h"])
def test_resolve_unknown_raises(bad):
    """§V-8 mutation 鎖：未知 timeframe 回預設值（如 730）即轉紅。"""
    with pytest.raises(UnknownTimeframeError):
        resolve_periods_per_year(bad)


def test_available_years_zero_bars():
    assert available_years(n_bars=0, timeframe="1h") == 0.0


@pytest.mark.parametrize("bad_bars", [-1, 1.5, True, "100"])
def test_available_years_rejects_bad_n_bars(bad_bars):
    with pytest.raises(ValueError):
        available_years(n_bars=bad_bars, timeframe="1h")


def test_available_years_propagates_unknown_timeframe():
    with pytest.raises(UnknownTimeframeError):
        available_years(n_bars=100, timeframe="7m")


# §V 反向測試（A1-14）：真實 kline 長度（§A FACT-RECEIPT：1h=20352／4h=5088／12h=1696，同一期間）
# 三 timeframe 之 available_years 須互相相等；把 bar 數當年數（§V-15）即轉紅。
_REAL_KLINE_BARS = {"1h": 20352, "4h": 5088, "12h": 1696}
_EXPECTED_YEARS = 2.3232876712328765


@pytest.mark.parametrize("timeframe,n_bars", sorted(_REAL_KLINE_BARS.items()))
def test_available_years_matches_real_kline_receipt(timeframe, n_bars):
    assert available_years(n_bars=n_bars, timeframe=timeframe) == pytest.approx(
        _EXPECTED_YEARS, abs=1e-6
    )


def test_available_years_frequency_invariance():
    """同一期間、不同取樣頻率 ⇒ 年數相同（防「用頻率折抵年數」取巧）。"""
    years = [
        available_years(n_bars=n, timeframe=tf) for tf, n in sorted(_REAL_KLINE_BARS.items())
    ]
    assert max(years) - min(years) < 1e-6


# ============================================================================
# B1 code review K4 / GROK-R10-P2-01：兩個 import 路徑之防漂移
# canonical 實作住 momentum/core/frequency.py（A1-19）；本 package 之同名模組僅為 re-export。
# 新碼一律 import core；本斷言鎖住「re-export 不得長出第二套邏輯」。
# ============================================================================


def test_reexport_is_identical_object_to_core_implementation():
    from momentum.Analysis.strategy_validation import frequency as reexport
    from momentum.core import frequency as core

    assert reexport.resolve_periods_per_year is core.resolve_periods_per_year
    assert reexport.available_years is core.available_years
    assert reexport.UnknownTimeframeError is core.UnknownTimeframeError
