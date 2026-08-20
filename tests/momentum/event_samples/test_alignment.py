"""Task B1.1 驗證：§G-2 真實 kline 手算對照（整數 ms exact）＋失敗枚舉＋記帳守恆＋W11。

手算依據：ETHUSDT kline 為連續網格（實測 2026-08-20：1h/4h/12h 首根 open＝2024-01-01
00:00 UTC＝1704067200s、間隔＝TF、無缺根），故 §G-2 之「手算」＝網格算術，
期望值以**字面整數**寫死（==，容差 0）。
"""

from __future__ import annotations

import pandas as pd
import pytest

from momentum.Analysis.event_samples import alignment as al
from momentum.Analysis.event_samples.alignment import align_events, n_dropped_by_reason
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.types import AlignmentConfig
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000  # 2024-01-01 00:00 UTC（ms）
H1 = 3600000
H12 = 43200000
T0_100 = BASE + 100 * H12          # 12h 第 100 根 open＝1708387200000
LAST_12H_OPEN = 1777291200000      # 12h 最末根 open（實測）
CFG3 = AlignmentConfig(timeframes=("1h", "4h", "12h"))


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("1h", "4h", "12h"))


def run(events, bars, cfg=CFG3):
    df = validate_event_import(events)
    return align_events(df, bars, cfg)


def two(ev0):
    """湊二元批（B1.0 missing_control_group 閘）；第二事件為對照正常事件。"""
    return [ev0, make_event(1, label=1 - ev0["label"], t0=T0_100 + 10 * H12)]


def test_g2_k0_integer_exact(bars):
    assert T0_100 == 1708387200000  # 手算字面
    rec, fail = run(two(make_event(0, t0=T0_100, label=1)), bars)
    assert fail.empty
    r = rec.event_level.set_index("event_id").loc["ev0"]
    assert int(r["decision_at_ms"]) == 1708387200000
    assert int(r["entry_at_ms"]) == 1708387200000                # trigger_open ⇒ bar open_time
    assert int(r["entry_price_source_bar_open_ms"]) == 1708387200000
    assert r["entry_price_source_field"] == "open"
    assert int(r["label_start_ms"]) == 1708387200000 + H12       # t0 close
    assert int(r["label_end_ms"]) == 1708387200000 + 3 * H12     # H=2 ⇒ close(idx+2)
    tf = rec.per_tf[rec.per_tf["event_id"] == "ev0"].set_index("timeframe")
    for t in ("1h", "4h", "12h"):  # 12h 整點 ⇒ 三 TF cutoff 皆恰為 decision_at
        assert int(tf.loc[t, "feature_cutoff_ms"]) == 1708387200000
        assert int(tf.loc[t, "last_bar_close_ms"]) == 1708387200000


def test_g2_k1_offset_exact(bars):
    """k>0 exact receipt oracle（M9 反面在 test_mutation_guard）。"""
    rec, fail = run(two(make_event(0, t0=T0_100, decision_offset_bars=1, label=1)), bars)
    assert fail.empty
    r = rec.event_level.set_index("event_id").loc["ev0"]
    assert int(r["decision_at_ms"]) == 1708387200000 - H12       # t0 往前 1 根 12h open
    assert int(r["label_start_ms"]) == 1708387200000 + H12       # label 錨不隨 decision 移動（D1-5）
    tf = rec.per_tf[rec.per_tf["event_id"] == "ev0"].set_index("timeframe")
    for t in ("1h", "4h", "12h"):
        assert int(tf.loc[t, "feature_cutoff_ms"]) == 1708387200000 - H12


def test_g2_nonboundary_1h_anchor_asof(bars):
    """非整點 TF 邊界 ⇒ as-of 取列非報錯；手算：day10 07:00 之 1h/4h/12h cutoff。"""
    t0 = BASE + 9 * 86400000 + 7 * H1  # 1704870000000
    assert t0 == 1704870000000
    ev = make_event(0, t0=t0, timeframe="1h", label=1)
    rec, fail = run([ev, make_event(1, label=0, t0=T0_100, timeframe="12h")], bars)
    assert fail.empty
    tf = rec.per_tf[rec.per_tf["event_id"] == "ev0"].set_index("timeframe")
    assert int(tf.loc["1h", "feature_cutoff_ms"]) == 1704870000000   # 07:00 close
    assert int(tf.loc["4h", "feature_cutoff_ms"]) == 1704859200000   # 04:00 close
    assert int(tf.loc["12h", "feature_cutoff_ms"]) == 1704844800000  # day10 00:00 close


def test_g2_data_end_label_window_incomplete(bars):
    rec, fail = run(two(make_event(0, t0=LAST_12H_OPEN, label=1)), bars)
    assert fail.set_index("event_id").loc["ev0", "reason"] == "label_window_incomplete"


def test_next_open_close_to_close_two_number_disclosure(bars):
    """SPEC D2-1／§G-2：next_open×close_to_close ⇒ entry_after_label_start=true 且三段鏈全過。"""
    rec, fail = run(two(make_event(0, t0=T0_100, entry_price_semantic="next_open", label=1)), bars)
    assert fail.empty
    r = rec.event_level.set_index("event_id").loc["ev0"]
    assert int(r["entry_at_ms"]) == 1708387200000 + H12
    assert bool(r["entry_after_label_start"]) is True
    assert int(r["decision_at_ms"]) <= int(r["entry_at_ms"])
    assert int(r["decision_at_ms"]) <= int(r["label_start_ms"]) < int(r["label_end_ms"])
    assert int(r["entry_at_ms"]) < int(r["label_end_ms"])


def test_label_modes_exact(bars):
    """各 label_return_mode 之 label_start/label_end exact 手算入案（§G-2）。"""
    ld = {"rule_id": "r", "canonical_digest": "c" * 64, "window": {"horizon_bars": 2}}
    cases = [
        ("open_to_close", "trigger_open", T0_100, T0_100 + H12),
        ("open_to_horizon_close", "trigger_open", T0_100, T0_100 + 3 * H12),
        ("open_to_horizon_close", "next_open", T0_100 + H12, T0_100 + 4 * H12),
    ]
    for mode, sem, exp_start, exp_end in cases:
        ev = make_event(0, t0=T0_100, entry_price_semantic=sem, label=1,
                        label_definition=dict(ld, label_return_mode=mode))
        rec, fail = run(two(ev), bars)
        assert fail.empty, (mode, sem, fail)
        r = rec.event_level.set_index("event_id").loc["ev0"]
        assert int(r["label_start_ms"]) == exp_start, (mode, sem)
        assert int(r["label_end_ms"]) == exp_end, (mode, sem)


def test_accounting_conservation_m1(bars):
    """M1 記帳守恆：n_input == n_receipts + n_failures，且逐失敗有 reason。"""
    events = [
        make_event(0, t0=T0_100, label=1),
        make_event(1, t0=LAST_12H_OPEN, label=0),           # label_window_incomplete
        make_event(2, t0=T0_100 + 7 * H12, label=1),
        make_event(3, t0=T0_100 + 1234, label=0),           # 非 bar open ⇒ no_boundary_match
    ]
    rec, fail = run(events, bars)
    assert len(events) == len(rec.event_level) + len(fail)
    summary = n_dropped_by_reason(fail)
    assert summary == {"label_window_incomplete": 1, "no_boundary_match": 1}
    assert sum(summary.values()) == len(fail)


def test_warmup_insufficient_before_data_start(bars):
    ev = make_event(0, t0=BASE, decision_offset_bars=1, label=1)  # 首根再往前 ⇒ 無 bar
    rec, fail = run(two(ev), bars)
    assert fail.set_index("event_id").loc["ev0", "reason"] == "warmup_insufficient_12h"


def test_missing_tf_and_corrupt_bars(bars):
    ev2 = two(make_event(0, t0=T0_100, label=1))
    df = validate_event_import(ev2)
    # 缺 TF
    only12 = {"ETHUSDT": {"12h": bars["ETHUSDT"]["12h"]}}
    rec, fail = align_events(df, only12, CFG3)
    assert set(fail["reason"]) == {"missing_bar"}
    # 亂序 bar
    shuffled = bars["ETHUSDT"]["12h"].iloc[::-1].reset_index(drop=True)
    rec, fail = align_events(df, {"ETHUSDT": {"1h": bars["ETHUSDT"]["1h"], "4h": bars["ETHUSDT"]["4h"], "12h": shuffled}}, CFG3)
    assert set(fail["reason"]) == {"unsorted_bar"}
    # 重複 bar
    dup = pd.concat([bars["ETHUSDT"]["12h"], bars["ETHUSDT"]["12h"].iloc[[100]]]).sort_values("open_time_ms").reset_index(drop=True)
    rec, fail = align_events(df, {"ETHUSDT": {"1h": bars["ETHUSDT"]["1h"], "4h": bars["ETHUSDT"]["4h"], "12h": dup}}, CFG3)
    assert set(fail["reason"]) == {"duplicate_bar"}


def test_corrupt_close_time_rejected(bars):
    """CODEX-R1-P1-04：close_time 亂序／close≤open 的 bar 表一律 fail-closed（cutoff searchsorted 依賴其排序）。"""
    ev2 = two(make_event(0, t0=T0_100, label=1))
    df = validate_event_import(ev2)
    b12 = bars["ETHUSDT"]["12h"].copy()
    b12["close_time_ms"] = b12["open_time_ms"]  # 全表 close == open（仍排序唯一）⇒ 邊界語意壞
    rec, fail = align_events(df, {"ETHUSDT": {"1h": bars["ETHUSDT"]["1h"], "4h": bars["ETHUSDT"]["4h"], "12h": b12}}, CFG3)
    assert len(rec.event_level) == 0 and set(fail["reason"]) == {"tf_boundary_ambiguous"}
    b12c = bars["ETHUSDT"]["12h"].copy()
    b12c.loc[100, "close_time_ms"] = b12c.loc[100, "open_time_ms"]  # 單列 close==open ⇒ 與前列 close 重複
    rec, fail = align_events(df, {"ETHUSDT": {"1h": bars["ETHUSDT"]["1h"], "4h": bars["ETHUSDT"]["4h"], "12h": b12c}}, CFG3)
    assert len(rec.event_level) == 0 and set(fail["reason"]) == {"duplicate_bar"}
    b12b = bars["ETHUSDT"]["12h"].copy()
    b12b.loc[[100, 101], "close_time_ms"] = b12b.loc[[101, 100], "close_time_ms"].to_numpy()  # close 亂序
    rec, fail = align_events(df, {"ETHUSDT": {"1h": bars["ETHUSDT"]["1h"], "4h": bars["ETHUSDT"]["4h"], "12h": b12b}}, CFG3)
    assert len(rec.event_level) == 0 and set(fail["reason"]) == {"unsorted_bar"}


def test_w11_decision_gt_t0_guard_falsifiable(bars, monkeypatch):
    """W11 負例：竄改推導使 decision_at > t0 ⇒ loud 拒（守衛真的在看）。"""
    monkeypatch.setattr(al, "_decision_idx", lambda t0_idx, k: t0_idx + 1)
    rec, fail = run(two(make_event(0, t0=T0_100, label=1)), bars)
    assert len(rec.event_level) == 0
    assert set(fail["reason"]) == {"no_boundary_match"}


def test_assert_cutoff_shift_one_bar_mutation_red(bars, monkeypatch):
    """ASSERT … WHEN mutation=cutoff_shift_one_bar THEN rc!=0（§G-3(ii)）：
    cutoff 後移一根 ⇒ feature_after_decision loud（正常跑則綠）。"""
    orig = al._select_cutoff_idx
    monkeypatch.setattr(al, "_select_cutoff_idx", lambda c, d: orig(c, d) + 1)
    rec, fail = run(two(make_event(0, t0=T0_100, label=1)), bars)
    assert len(rec.event_level) == 0
    assert set(fail["reason"]) == {"feature_after_decision"}
