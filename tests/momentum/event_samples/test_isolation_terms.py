"""EVTLABEL Task 2.1：隔離區兩項分開換算成特徵週期列數。

受理批（2026-09-09）：165 事件、12h 事件 × 1h 特徵、h=1 close_to_close、宣告深度 12 根 12h
⇒ 答案窗 12 根 1h、深度 144 根 1h。改前 purge=5（主線 default_horizon，與 h 無關）、
答案窗被塞在 embargo 裡；本 Task 把兩者分開，purge 才會跟著 h 走。
"""

from __future__ import annotations

import pytest

from momentum.Analysis.event_samples.label_value_from_case import (
    LabelProducerError,
    WindowRow,
    isolation_terms_rows,
    purge_lower_bound_rows,
)

TF = {"1h": 3600, "4h": 14400, "12h": 43200}
H12 = 43_200_000
H4 = 14_400_000


def _w(event_id: str, tf: str, start: int, span_ms: int) -> WindowRow:
    return WindowRow(
        event_id=event_id, symbol="ETHUSDT", timeframe=tf,
        decision_at_ms=start, entry_at_ms=start,
        label_start_ms=start, label_end_ms=start + span_ms,
    )


def test_receipt_batch_shape_h1_close_to_close():
    """h=1 c2c：答案窗 1 根 12h ＝ 12 根 1h；深度宣告 12 根 12h ＝ 144 根 1h。"""
    wins = [_w(f"e{i}", "12h", i * 2 * H12, H12) for i in range(165)]
    out = isolation_terms_rows(
        wins, lookahead_bars_declared={"12h": 12}, timeframe_seconds=TF, feature_timeframe="1h",
    )
    assert out.label_window_rows == 12
    assert out.lookahead_depth_rows == 144


def test_open_to_horizon_close_window_is_h_plus_one_bars():
    """o2hc h=12：收據視窗 13 根 12h ⇒ 156 根 1h（比深度 144 大 ⇒ purge 會由視窗決定）。"""
    wins = [_w("e0", "12h", 0, 13 * H12)]
    out = isolation_terms_rows(
        wins, lookahead_bars_declared={"12h": 12}, timeframe_seconds=TF, feature_timeframe="1h",
    )
    assert out.label_window_rows == 156
    assert out.lookahead_depth_rows == 144


def test_4h_events_on_1h_features():
    wins = [_w("e0", "4h", 0, 3 * H4)]
    out = isolation_terms_rows(
        wins, lookahead_bars_declared={"4h": 3}, timeframe_seconds=TF, feature_timeframe="1h",
    )
    assert out.label_window_rows == 12
    assert out.lookahead_depth_rows == 12


def test_zero_depth_declaration():
    """深度宣告 0（沒有用未來資訊挑樣本）⇒ embargo 不被抬高。"""
    wins = [_w("e0", "12h", 0, H12)]
    out = isolation_terms_rows(
        wins, lookahead_bars_declared={"12h": 0}, timeframe_seconds=TF, feature_timeframe="1h",
    )
    assert out.label_window_rows == 12
    assert out.lookahead_depth_rows == 0


def test_empty_windows_is_zero_not_error():
    out = isolation_terms_rows([], lookahead_bars_declared={}, timeframe_seconds=TF, feature_timeframe="1h")
    assert (out.label_window_rows, out.lookahead_depth_rows) == (0, 0)


def test_finer_event_than_feature_rounds_up_to_one_row():
    """細事件配粗特徵：不足一列也要整列擋住（無條件進位，不得回 0）。"""
    wins = [_w("e0", "1h", 0, 3600 * 1000)]
    out = isolation_terms_rows(
        wins, lookahead_bars_declared={"1h": 1}, timeframe_seconds=TF, feature_timeframe="4h",
    )
    assert out.label_window_rows == 1
    assert out.lookahead_depth_rows == 1


def test_missing_timeframe_is_fail_closed():
    wins = [_w("e0", "12h", 0, H12)]
    with pytest.raises(LabelProducerError, match="lookahead_bars_declared 缺"):
        isolation_terms_rows(wins, lookahead_bars_declared={}, timeframe_seconds=TF, feature_timeframe="1h")
    with pytest.raises(LabelProducerError, match="缺分析用 timeframe"):
        isolation_terms_rows(
            wins, lookahead_bars_declared={"12h": 1}, timeframe_seconds=TF, feature_timeframe="30m",
        )


@pytest.mark.parametrize(
    "span_ms,depth_bars",
    [(H12, 12), (13 * H12, 12), (H12, 0), (3 * H12, 1)],
)
def test_max_of_two_terms_equals_legacy_purge_rows(span_ms: int, depth_bars: int):
    """不變式：max(答案窗, 深度) 必須等於舊的 `purge_rows`（＝舊 embargo 抬升值）。

    這條保證「拆開」沒有改變總量、只改變歸屬——舊行為＝新兩項取 max。
    """
    wins = [_w("e0", "12h", 0, span_ms)]
    terms = isolation_terms_rows(
        wins, lookahead_bars_declared={"12h": depth_bars}, timeframe_seconds=TF, feature_timeframe="1h",
    )
    legacy = purge_lower_bound_rows(
        wins, lookahead_bars_declared={"12h": depth_bars}, timeframe_seconds=TF, symbols=["ETHUSDT"],
    )
    legacy_rows = -(-int(legacy[0].purge_lower_bound_ms) // (TF["1h"] * 1000))
    assert max(terms.label_window_rows, terms.lookahead_depth_rows) == legacy_rows
