"""GAP-3 `G3-D2` **Task D4.2** — 逐事件成對可行域 `feasible(e,k,h)` 與兩個條件上界。

`D-001` D4.2 之驗收（逐條對應本檔測試）：
- 真實 kline 取**三事件手算**兩上界 `==`；
- mutation：`end_idx` 少算一根 ⇒ **兩上界皆變**；
- `decision_bar_open × open_to_horizon_close` 取 `(k_max_at_h, h)` 通過、
  `(k_max_at_h + 1, h)` 該事件入 failures；
- **誠實邊界**：`≤ 上界` **不保證**零 failures（`align_events` 之 `missing_bar` 等
  loud 拒收不納入閉式）。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.types import AlignmentConfig
from momentum.Analysis.event_samples.label_value_from_case import (
    end_bar_index,
    entry_bar_index,
    event_geometries,
    feasible,
    feasible_bounds,
    prepare_analysis_windows,
)
from tests.momentum.event_samples.helpers import load_bars, make_event

SYMBOL = "ETHUSDT"
TF = "12h"
TF_SECONDS = {TF: 43200}
DECLARED = {TF: 0}
T0_IDXS: Tuple[int, ...] = (120, 180, 240)
EVENT_IDS: Tuple[str, ...] = tuple(f"ev{i}" for i in range(len(T0_IDXS)))


@pytest.fixture(scope="module")
def bars():
    return load_bars(SYMBOL, (TF,))


def _spec(entry: str, mode: str, k: int, h: int) -> Dict[str, object]:
    return {"horizon_bars": h, "entry_price_semantic": entry,
            "label_return_mode": mode, "decision_offset_bars": k}


def _records(bars, *, entry: str, mode: str, k: int, h: int,
             t0_idxs: Tuple[int, ...] = T0_IDXS, direction: str = "long"):
    ot = bars[SYMBOL][TF]["open_time_ms"].to_numpy()
    recs = []
    for i, idx in enumerate(t0_idxs):
        rec = dict(make_event(i, t0=int(ot[idx]), label=i % 2, direction=direction))
        rec["decision_offset_bars"] = k
        rec["entry_price_semantic"] = entry
        ld = dict(rec.get("label_definition") or {})
        ld["label_return_mode"] = mode
        ld["window"] = {**dict(ld.get("window") or {}), "horizon_bars": h}
        rec["label_definition"] = ld
        recs.append(rec)
    return recs


# ── `feasible` 純函式之閉式（手算，不呼叫 producer）─────────────────────────

def test_feasible_is_pure_closed_form():
    """三條約束逐條可證偽：暖機、末端、coverage。"""
    common = dict(mode="close_to_close", entry="trigger_close", t0_idx=100, n_bars=1000)
    assert feasible("e", 0, 1, coverage_ok=True, **common) is True
    # ① t0_idx − k < 0
    assert feasible("e", 101, 1, coverage_ok=True, **common) is False
    assert feasible("e", 100, 1, coverage_ok=True, **common) is True
    # ② end_idx > n_bars − 1（close_to_close ⇒ end = t0_idx + h）
    assert feasible("e", 0, 899, coverage_ok=True, **common) is True
    assert feasible("e", 0, 900, coverage_ok=True, **common) is False
    # ③ coverage
    assert feasible("e", 0, 1, coverage_ok=False, **common) is False


def test_feasible_k_and_h_are_coupled_for_decision_bar_horizon():
    """🔴 `decision_bar_* × open_to_horizon_close`：k 變大反而讓 end 條件變鬆。

    這條就是「支援域不是兩個獨立區間」的可證偽證據——若把 `feasible` 寫成
    `k ≤ K ∧ h ≤ H` 兩個獨立區間，本條必紅。
    """
    kw = dict(mode="open_to_horizon_close", entry="decision_bar_open",
              t0_idx=100, n_bars=102, coverage_ok=True)
    # h=5：end = 100 − k + 5 ≤ 101 ⇒ k ≥ 4
    assert feasible("e", 0, 5, **kw) is False
    assert feasible("e", 3, 5, **kw) is False
    assert feasible("e", 4, 5, **kw) is True
    assert feasible("e", 10, 5, **kw) is True
    # 對照：非 decision_bar entry 之 end 與 k 無關 ⇒ 全部 False
    kw2 = {**kw, "entry": "trigger_open"}
    assert [feasible("e", k, 5, **kw2) for k in (0, 4, 10)] == [False, False, False]


def test_entry_and_end_index_tables_match_alignment(bars):
    """`entry_bar_index`／`end_bar_index` 與 `align_events` 實跑之收據逐事件相符。

    🔴 這條把「純函式那份 index 算術」與「對齊層那份」釘在一起——兩份實作是刻意的
    （一份要能不跑對齊就算），但**不得**漂移。
    """
    df = bars[SYMBOL][TF]
    ot, ct = df["open_time_ms"].to_numpy(), df["close_time_ms"].to_numpy()
    for entry in ("trigger_open", "trigger_close", "next_open",
                  "decision_bar_open", "decision_bar_close"):
        for mode in ("close_to_close", "open_to_horizon_close"):
            k, h = 2, 3
            recs = _records(bars, entry=entry, mode=mode, k=k, h=h)
            receipts, failures = align_events(
                __import__("pandas").DataFrame(recs), bars, AlignmentConfig(timeframes=(TF,)),
            )
            assert len(failures) == 0, f"{entry}×{mode} 本組不該有 failures"
            for row in receipts.event_level.to_dict("records"):
                t0_idx = int((ot == int(row["t0_ms"])).nonzero()[0][0])
                e_idx = entry_bar_index(entry, t0_idx=t0_idx, k=k)
                nd_idx = end_bar_index(mode, t0_idx=t0_idx, entry_idx=e_idx, h=h)
                assert int(row["entry_price_source_bar_open_ms"]) == int(ot[e_idx])
                assert int(row["label_end_ms"]) == int(ct[nd_idx])


# ── 兩個條件上界：三事件手算 `==` ──────────────────────────────────────────

def _hand_bounds(bars, *, entry: str, mode: str, k: int, h: int) -> Tuple[int, int]:
    """**測試側手算**（不呼叫 `feasible_bounds`）：逐事件閉式後取 min。"""
    df = bars[SYMBOL][TF]
    n = len(df)
    ct0 = int(df["close_time_ms"].to_numpy()[0])
    ot = df["open_time_ms"].to_numpy()
    cov_min_idx = int(ot.searchsorted(ct0, side="left"))
    k_maxes: List[int] = []
    h_maxes: List[int] = []
    for t0_idx in T0_IDXS:
        k_maxes.append(min(t0_idx, t0_idx - cov_min_idx))
        e_idx = entry_bar_index(entry, t0_idx=t0_idx, k=k)
        e1 = end_bar_index(mode, t0_idx=t0_idx, entry_idx=e_idx, h=1)
        h_maxes.append(n - 1 - e1 + 1)
    return min(k_maxes), min(h_maxes)


@pytest.mark.parametrize("entry,mode", [
    ("trigger_close", "close_to_close"),
    ("trigger_open", "open_to_horizon_close"),
    ("decision_bar_open", "open_to_horizon_close"),
    ("decision_bar_close", "open_to_horizon_close"),
    ("next_open", "close_to_close"),
])
def test_feasible_bounds_matches_hand_computation(bars, entry, mode):
    """真實 kline 三事件：兩上界與手算 `==`。"""
    k, h = 2, 3
    got = feasible_bounds(
        _records(bars, entry=entry, mode=mode, k=k, h=h), bars,
        event_label_spec=_spec(entry, mode, k, h), timeframes=(TF,),
    )
    want_k, want_h = _hand_bounds(bars, entry=entry, mode=mode, k=k, h=h)
    assert got.k_status == "bounded" and got.h_status == "bounded"
    assert got.k_max_feasible_at_h == want_k
    assert got.h_max_feasible_at_k == want_h


def test_feasible_bounds_open_to_close_h_is_inert(bars):
    """`open_to_close` 之 `end_idx` 與 h 無關 ⇒ h **無幾何上界**，狀態具名而非用 `None` 混充。"""
    got = feasible_bounds(
        _records(bars, entry="trigger_open", mode="open_to_close", k=0, h=1), bars,
        event_label_spec=_spec("trigger_open", "open_to_close", 0, 1), timeframes=(TF,),
    )
    assert got.h_status == "h_inert_for_mode"
    assert got.h_max_feasible_at_k is None
    assert got.k_status == "bounded" and isinstance(got.k_max_feasible_at_h, int)


def test_feasible_bounds_no_feasible_k_when_tail_event_blocks(bars):
    """末端事件使該 h 下無任何可行 k ⇒ `k_status == "no_feasible_k"`（不是回 0 假裝可行）。"""
    n = len(bars[SYMBOL][TF])
    tail = (120, n - 3)
    h = 10  # end = t0_idx + 10 > n − 1（末端事件）
    got = feasible_bounds(
        _records(bars, entry="trigger_close", mode="close_to_close", k=0, h=h, t0_idxs=tail),
        bars, event_label_spec=_spec("trigger_close", "close_to_close", 0, h), timeframes=(TF,),
    )
    assert got.k_status == "no_feasible_k" and got.k_max_feasible_at_h is None


def test_feasible_bounds_mutation_end_index_shifts_both_bounds(bars, monkeypatch):
    """🔴 mutation：`end_bar_index` **少算一根** ⇒ **兩個上界皆變**（`D-001` D4.2 驗收）。

    批次刻意含一個末端事件：未 mutate 時它使 `k_max` 為 `None`（該 h 下無可行 k），
    mutate 後 end 變小 ⇒ 它變可行 ⇒ `k_max` 由 `None` 變成數字、`h_max` 加一。
    """
    import momentum.Analysis.event_samples.label_value_from_case as m

    n = len(bars[SYMBOL][TF])
    tail_idx = n - 10          # end = t0_idx + h = n ⇒ 恰好越界一根
    tail = (120, tail_idx)
    h = 10
    recs = _records(bars, entry="trigger_close", mode="close_to_close", k=0, h=h, t0_idxs=tail)
    spec = _spec("trigger_close", "close_to_close", 0, h)
    before = feasible_bounds(recs, bars, event_label_spec=spec, timeframes=(TF,))
    # 未 mutate：末端事件之 end 越界 ⇒ 該 h 下無可行 k；h 上界＝`n − t0_idx − 1`
    assert before.k_status == "no_feasible_k" and before.k_max_feasible_at_h is None
    assert before.h_max_feasible_at_k == n - tail_idx - 1 == 9

    real = m.end_bar_index
    monkeypatch.setattr(m, "end_bar_index",
                        lambda mode, *, t0_idx, entry_idx, h: real(
                            mode, t0_idx=t0_idx, entry_idx=entry_idx, h=h) - 1)
    after = feasible_bounds(recs, bars, event_label_spec=spec, timeframes=(TF,))
    assert after.k_status == "bounded" and after.k_max_feasible_at_h is not None
    assert after.h_max_feasible_at_k == n - tail_idx == 10
    assert (before.k_max_feasible_at_h, before.h_max_feasible_at_k) != \
           (after.k_max_feasible_at_h, after.h_max_feasible_at_k)


def test_feasible_bounds_k_max_plus_one_puts_event_in_failures(bars):
    """`decision_bar_open × open_to_horizon_close`：`(k_max, h)` 全綠、`(k_max+1, h)` 入 failures。

    🔴 上界是**建議**不是輸入鎖 ⇒ 超界不是 400，而是該事件逐條 loud 進 failures。
    """
    import pandas as pd

    entry, mode, h = "decision_bar_open", "open_to_horizon_close", 3
    # 取一個 t0_idx 小的事件，讓 k_max 由暖機決定且數字夠小可實跑
    small = (5,)
    recs = _records(bars, entry=entry, mode=mode, k=0, h=h, t0_idxs=small)
    b = feasible_bounds(recs, bars, event_label_spec=_spec(entry, mode, 0, h), timeframes=(TF,))
    k_max = b.k_max_feasible_at_h
    assert isinstance(k_max, int) and k_max >= 1, f"本 fixture 之 k_max 應為小正整數，得 {k_max}"

    ok = _records(bars, entry=entry, mode=mode, k=k_max, h=h, t0_idxs=small)
    rec_ok, fail_ok = align_events(pd.DataFrame(ok), bars, AlignmentConfig(timeframes=(TF,)))
    assert len(fail_ok) == 0 and len(rec_ok.event_level) == 1

    over = _records(bars, entry=entry, mode=mode, k=k_max + 1, h=h, t0_idxs=small)
    rec_bad, fail_bad = align_events(pd.DataFrame(over), bars, AlignmentConfig(timeframes=(TF,)))
    assert len(rec_bad.event_level) == 0 and len(fail_bad) == 1
    assert str(fail_bad.iloc[0]["reason"]).startswith("warmup_insufficient")


def test_feasible_bounds_honest_boundary_not_a_success_guarantee(bars):
    """🔴 **誠實邊界**：`≤ 上界` 之事件仍可能因 `align_events` 之 loud 拒收落入 failures。

    以真實 bar 表之**副本**把一格 close 改成 0（＝mutation，非合成 fixture）：
    `feasible` 仍回 `True`（它不看價格），而對齊層以 `nonpositive_reference_price` 拒收。
    ⇒ 證明兩者的責任邊界確實不同，UI 文案不得把「≤ 上界」寫成全批成功保證。
    """
    import pandas as pd

    df = bars[SYMBOL][TF]
    ot = df["open_time_ms"].to_numpy()
    t0_idx = 120
    broken = df.copy()
    broken.loc[t0_idx, "close"] = 0.0          # 只改一格；其餘皆真實值
    bars_broken = {SYMBOL: {TF: broken}}

    geoms = event_geometries(
        _records(bars, entry="trigger_close", mode="close_to_close", k=0, h=3,
                 t0_idxs=(t0_idx,)),
        bars_broken, timeframes=(TF,),
    )
    assert len(geoms) == 1
    g = geoms[0]
    assert feasible(g.event_id, 0, 3, mode="close_to_close", entry="trigger_close",
                    t0_idx=g.t0_idx, n_bars=g.n_bars, coverage_ok=True) is True

    recs = _records(bars, entry="trigger_close", mode="close_to_close", k=0, h=3,
                    t0_idxs=(t0_idx,))
    _, failures = align_events(pd.DataFrame(recs), bars_broken,
                               AlignmentConfig(timeframes=(TF,)))
    assert len(failures) == 1
    assert str(failures.iloc[0]["reason"]) == "nonpositive_reference_price"
    _ = ot


def test_feasible_bounds_survives_prepare_without_realignment(bars):
    """`feasible_bounds` 之結果與 `prepare_analysis_windows` 之收據一致，且**不重跑對齊**。"""
    entry, mode, k, h = "decision_bar_open", "open_to_horizon_close", 2, 3
    recs = _records(bars, entry=entry, mode=mode, k=k, h=h)
    calls: List[int] = []
    import momentum.Analysis.event_samples.label_value_from_case as m

    real = m.align_events
    try:
        m.align_events = lambda *a, **kw: (calls.append(1), real(*a, **kw))[1]
        b = feasible_bounds(recs, bars, event_label_spec=_spec(entry, mode, k, h),
                            timeframes=(TF,))
        assert calls == [], "feasible_bounds 不得呼叫 align_events"
        prepared = prepare_analysis_windows(
            recs, bars, event_label_spec=_spec(entry, mode, k, h),
            event_import_id="fb", lookahead_bars_declared=DECLARED,
            timeframe_seconds=TF_SECONDS,
        )
        assert len(calls) == 1
    finally:
        m.align_events = real
    assert len(prepared.windows) == len(T0_IDXS)
    assert b.k_status == "bounded" and b.h_status == "bounded"
