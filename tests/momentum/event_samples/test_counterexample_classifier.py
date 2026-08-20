"""Task B1.5 驗證：三類手造 exact、boundary fixtures（每門檻 =/+1e-9/−1e-9 三點落位 exact）、
conflict 主鍵保留＋留痕、多類邊界 unclassifiable、答案窗不完整 unclassifiable、真實 kline 整合。"""

from __future__ import annotations

import pandas as pd
import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.counterexample_classifier import _classify_one, classify_counterexamples
from momentum.Analysis.event_samples.import_contract import load_event_import_contract, validate_event_import
from momentum.Analysis.event_samples.types import AlignmentConfig, AlignmentReceipts
from tests.momentum.event_samples.helpers import load_bars, make_event

CFG = load_event_import_contract()["counterexample_classifier_config"]
T0_100 = 1704067200000 + 100 * 43200000
EPS = 1e-9


# ---- boundary fixtures（回報純量，非價格；門檻預設 0.05/0.0/0.01/0.05＝example_default）----

@pytest.mark.parametrize(
    "r0,rw,expected",
    [
        (0.05, -0.01, "a_trigger_no_follow"),        # trigger_threshold 落位 =
        (0.05 + EPS, -0.01, "a_trigger_no_follow"),  # +1e-9
        (0.05 - EPS, -0.01, "unclassifiable"),       # −1e-9 ⇒ 零命中不猜
        (0.06, 0.0, "a_trigger_no_follow"),          # follow_threshold =
        (0.06, EPS, "unclassifiable"),               # +1e-9 ⇒ 續漲了，不是 a
        (0.06, -EPS, "a_trigger_no_follow"),         # −1e-9
        (0.01, 0.05, "b_range"),                     # range_threshold =
        (0.01 + EPS, 0.05, "unclassifiable"),        # +1e-9
        (0.01 - EPS, 0.05, "b_range"),               # −1e-9
        (-0.05, 0.0, "c_drop"),                      # drop_threshold =
        (-0.05 + EPS, 0.0, "unclassifiable"),        # +1e-9（跌不夠）
        (-0.05 - EPS, 0.0, "c_drop"),                # −1e-9
    ],
)
def test_boundary_fixture_exact(r0, rw, expected):
    assert _classify_one(r0, rw, CFG) == expected


def test_multi_hit_unclassifiable_not_guess():
    """M10 看住：同時滿足多類 ⇒ unclassifiable，不取 precedence 猜一類。"""
    override = {"thresholds": {"trigger_threshold": 0.005, "follow_threshold": 0.0,
                               "range_threshold": 0.01, "drop_threshold": 0.05}}  # runtime float 形
    assert _classify_one(0.005, -0.01, override) == "unclassifiable"  # a 與 b 同時命中


# ---- 端到端（真實 kline）----

@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def aligned(events, bars):
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    return df, rec, fail


def expected_suggestion(bars, t0_ms, label_end_ms, direction="long"):
    b = bars["ETHUSDT"]["12h"]
    i0 = int(b.index[b["open_time_ms"] == t0_ms][0])
    ie = int(b.index[b["close_time_ms"] == label_end_ms][0])
    sign = 1.0 if direction == "long" else -1.0
    r0 = sign * (b["close"].iloc[i0] - b["open"].iloc[i0]) / b["open"].iloc[i0]
    rw = sign * (b["close"].iloc[ie] - b["close"].iloc[i0]) / b["close"].iloc[i0]
    return _classify_one(float(r0), float(rw), CFG)


def test_real_kline_auto_classification(bars):
    events = [make_event(0, t0=T0_100, label=0), make_event(1, t0=T0_100 + 10 * 43200000, label=1)]
    df, rec, fail = aligned(events, bars)
    assert fail.empty
    out = classify_counterexamples(df, rec, bars, CFG)
    assert out["event_id"].tolist() == ["ev0"]                      # 僅 label=0 輸出
    r = rec.event_level.set_index("event_id").loc["ev0"]
    exp = expected_suggestion(bars, int(r["t0_ms"]), int(r["label_end_ms"]))
    row = out.iloc[0]
    assert row["counterexample_kind_effective"] == exp
    assert row["kind_source"] == "platform_auto"
    assert row["platform_suggested_kind"] is None


def test_user_label_kept_with_conflict_trace(bars):
    events = [make_event(0, t0=T0_100, label=0, counterexample_kind="b_range", kind_source="user"),
              make_event(1, t0=T0_100 + 10 * 43200000, label=1)]
    df, rec, fail = aligned(events, bars)
    out = classify_counterexamples(df, rec, bars, CFG).set_index("event_id")
    r = rec.event_level.set_index("event_id").loc["ev0"]
    exp = expected_suggestion(bars, int(r["t0_ms"]), int(r["label_end_ms"]))
    row = out.loc["ev0"]
    assert row["counterexample_kind_effective"] == "b_range"        # 主鍵保留 user，不回寫
    assert row["kind_source"] == "user"
    if exp != "b_range":
        assert row["platform_suggested_kind"] == exp                # 衝突留痕
    else:
        assert row["platform_suggested_kind"] is None


def test_window_incomplete_unclassifiable(bars):
    """答案窗不完整（對齊失敗、不在 receipts）⇒ unclassifiable 非亂填。"""
    last_open = 1777291200000
    events = [make_event(0, t0=last_open, label=0), make_event(1, t0=T0_100, label=1)]
    df, rec, fail = aligned(events, bars)
    assert not fail.empty
    out = classify_counterexamples(df, rec, bars, CFG).set_index("event_id")
    assert out.loc["ev0", "counterexample_kind_effective"] == "unclassifiable"
