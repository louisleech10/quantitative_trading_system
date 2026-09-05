"""GAP-3 `G3-D2` **Task D4.2** — 三層 oracle 之第 (2)(3) 層。

`D-001` D4.2 把 label 之保證分成三層，**缺一即紅**：

1. **凍結層** ＝ `tests/golden/gap3_label/*.json`（有限案例，逐位元組）。
2. **獨立 raw-bar oracle**（本檔上半）：測試檔內以**期望表**寫死 D1-6 五語意之
   `(bar_offset, field)` 與三 mode 之 `(start_bar, end_bar)`，**自 raw bars 以 index 算**
   期望 `entry_at_ms`／`label_start_ms`／`label_end_ms`／`label_value`，再與 producer 逐欄 `==`。
   🔴 **不得引用收據之 `entry_price_ref`／時間戳當期望值**——那樣 alignment 與 ref
   協同錯誤時本層會跟著錯。期望值只能來自 raw bars ＋ 本檔寫死的表。
3. **property 層**（本檔下半 `label_differential_grid`）：固定網格 13 對 × k∈{0,1,2,4}
   × h∈{1,2,3,5,7} × {long, short}，**加** seeded 隨機抽樣（`seed=20260903`，40 組
   `(k,h)` 取自可行域），逐 event 以 (2) 之期望表比對（`atol=0`），
   NaN mask 與 failures reason 集合相等。

**誠實邊界**：可行域內未被 (1)(3) 覆蓋之 `(k,h)` 只有 (2) 之同型 oracle 保證，
無 exact 凍結——具名於 `D-001` §N（`needs-research`）。
"""

from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional, Tuple

import pytest

from momentum.Analysis.event_samples.label_value_from_case import (
    REJECTED_PAIRS,
    SUPPORTED_PAIRS,
    prepare_analysis_windows,
    resolve_label_value_at_analyze,
)
from tests.momentum.event_samples.helpers import load_bars, make_event

SYMBOL = "ETHUSDT"
TF = "12h"
TF_SECONDS = {TF: 43200}
DECLARED = {TF: 0}

#: 🔴 **本表是 oracle 的全部來源**（`D-001` D4.2 (2)）：D1-6 五語意 → `(offset_kind, offset, field)`。
#  `offset_kind`：`"fixed"` ⇒ `entry_idx = t0_idx + offset`；`"minus_k"` ⇒ `entry_idx = t0_idx − k`。
#  **寫死在測試裡**是刻意的：與 `alignment._entry_mapping` 各寫一份，兩邊同時錯才會漏。
ENTRY_EXPECT: Mapping[str, Tuple[str, int, str]] = {
    "trigger_open": ("fixed", 0, "open"),
    "trigger_close": ("fixed", 0, "close"),
    "next_open": ("fixed", +1, "open"),
    "decision_bar_open": ("minus_k", 0, "open"),
    "decision_bar_close": ("minus_k", 0, "close"),
}

#: 三 mode → `(start_anchor, end_anchor)`；同樣寫死，不讀 producer。
MODE_EXPECT: Mapping[str, Tuple[str, str]] = {
    "close_to_close": ("t0_close", "t0_plus_h_close"),
    "open_to_close": ("entry_at", "entry_close"),
    "open_to_horizon_close": ("entry_at", "entry_plus_h_close"),
}

#: 事件錨點之 bar index（挑資料中段：k 最大 8、h 最大 12 皆在界內）。
T0_IDXS: Tuple[int, ...] = (120, 180, 240)
#: `make_event(i, ...)` 之 `event_id`（＝`ev{i}`）；與 `T0_IDXS` 同序。
EVENT_IDS: Tuple[str, ...] = tuple(f"ev{i}" for i in range(len(T0_IDXS)))


@pytest.fixture(scope="module")
def bars():
    return load_bars(SYMBOL, (TF,))


def _cols(bars):
    df = bars[SYMBOL][TF]
    return (
        df["open_time_ms"].to_numpy(),
        df["close_time_ms"].to_numpy(),
        df["open"].to_numpy(),
        df["close"].to_numpy(),
    )


def _spec(entry: str, mode: str, k: int, h: int) -> Dict[str, object]:
    return {
        "horizon_bars": h,
        "entry_price_semantic": entry,
        "label_return_mode": mode,
        "decision_offset_bars": k,
    }


def _records(bars, direction: str, k: int, entry: str, mode: str, h: int):
    ot, _, _, _ = _cols(bars)
    recs = []
    for i, idx in enumerate(T0_IDXS):
        rec = dict(make_event(i, t0=int(ot[idx]), label=i % 2, direction=direction))
        rec["decision_offset_bars"] = k
        rec["entry_price_semantic"] = entry
        ld = dict(rec.get("label_definition") or {})
        ld["label_return_mode"] = mode
        ld["window"] = {**dict(ld.get("window") or {}), "horizon_bars": h}
        rec["label_definition"] = ld
        recs.append(rec)
    return recs


def expected_row(
    bars, *, t0_idx: int, entry: str, mode: str, k: int, h: int, direction: str,
) -> Optional[Dict[str, object]]:
    """**只用 raw bars ＋ 上方兩張表**算出期望值；幾何越界 ⇒ `None`（該事件不該出現在收據）。"""
    ot, ct, op, cl = _cols(bars)
    n = len(ot)
    kind, off, field = ENTRY_EXPECT[entry]
    entry_idx = t0_idx - k if kind == "minus_k" else t0_idx + off
    if entry_idx < 0 or entry_idx > n - 1 or t0_idx - k < 0:
        return None
    start_anchor, end_anchor = MODE_EXPECT[mode]
    end_idx = {
        "t0_plus_h_close": t0_idx + h,
        "entry_close": entry_idx,
        "entry_plus_h_close": entry_idx + h,
    }[end_anchor]
    if end_idx > n - 1:
        return None
    entry_at = int(ot[entry_idx]) if field == "open" else int(ct[entry_idx])
    label_start = int(ct[t0_idx]) if start_anchor == "t0_close" else entry_at
    label_end = int(ct[end_idx])
    if not (label_start < label_end):
        return None  # 幾何零窗（REJECTED_PAIRS）——alignment 會 no_boundary_match
    base = float(op[entry_idx]) if field == "open" else float(cl[entry_idx])
    if mode == "close_to_close":
        base = float(cl[t0_idx])
    end_price = float(cl[end_idx])
    sign = 1 if direction == "long" else -1
    return {
        "decision_at_ms": int(ot[t0_idx - k]),
        "entry_at_ms": entry_at,
        "label_start_ms": label_start,
        "label_end_ms": label_end,
        "entry_price_ref": {"bar_open_ms": int(ot[entry_idx]), "field": field},
        "label_value": sign * (end_price - base) / base,
    }


def actual_rows(bars, *, entry: str, mode: str, k: int, h: int, direction: str):
    """跑 producer 兩階段，回 `{event_id: {同 expected_row 之鍵}}`。"""
    sp = _spec(entry, mode, k, h)
    recs = _records(bars, direction, k, entry, mode, h)
    prepared = prepare_analysis_windows(
        recs, bars, event_label_spec=sp, event_import_id="oracle",
        lookahead_bars_declared=DECLARED, timeframe_seconds=TF_SECONDS,
    )
    result = resolve_label_value_at_analyze(prepared, bars, event_label_spec=sp)
    refs = {e.event_id: e for e in prepared.entry_price_refs}
    out: Dict[str, Dict[str, object]] = {}
    for w in prepared.windows:
        ref = refs[w.event_id]
        out[w.event_id] = {
            "decision_at_ms": int(w.decision_at_ms),
            "entry_at_ms": int(w.entry_at_ms),
            "label_start_ms": int(w.label_start_ms),
            "label_end_ms": int(w.label_end_ms),
            "entry_price_ref": {"bar_open_ms": int(ref.bar_open_ms), "field": ref.field},
            "label_value": result.label_values.get(w.event_id),
        }
    return out, prepared, result


# ── 第 (2) 層：獨立 raw-bar oracle ─────────────────────────────────────────

@pytest.mark.parametrize("entry,mode", sorted(SUPPORTED_PAIRS))
@pytest.mark.parametrize("direction", ["long", "short"])
def test_rawbar_oracle_matches_producer(bars, entry, mode, direction):
    """13 對 × 兩方向：producer 之五欄與**獨立期望表**逐欄 `==`（`atol=0`）。"""
    k, h = 2, 3
    rows, _, result = actual_rows(bars, entry=entry, mode=mode, k=k, h=h, direction=direction)
    assert result.supported is True
    seen = 0
    for i, t0_idx in enumerate(T0_IDXS):
        eid = EVENT_IDS[i]
        want = expected_row(bars, t0_idx=t0_idx, entry=entry, mode=mode, k=k, h=h,
                            direction=direction)
        if want is None:
            assert eid not in rows, f"{eid} 幾何越界卻仍出現在收據"
            continue
        assert eid in rows, f"{eid} 幾何可行卻不在收據（{entry}×{mode}）"
        got = rows[eid]
        for key in ("decision_at_ms", "entry_at_ms", "label_start_ms", "label_end_ms",
                    "entry_price_ref"):
            assert got[key] == want[key], f"{eid} {key}: got={got[key]} want={want[key]}"
        assert got["label_value"] == pytest.approx(want["label_value"], abs=0.0, rel=1e-15)
        seen += 1
    assert seen == len(T0_IDXS), "本組合應三個事件皆可行（否則 oracle 覆蓋縮水而不自知）"


def test_rawbar_oracle_rejected_pairs_produce_no_window(bars):
    """兩個幾何零窗對：期望表算出 `label_start == label_end` ⇒ 期望為 `None`，收據亦無該列。"""
    ot, ct, _, _ = _cols(bars)
    for mode, entries in REJECTED_PAIRS.items():
        for entry in entries:
            for k in (0, 2):
                want = expected_row(bars, t0_idx=T0_IDXS[0], entry=entry, mode=mode,
                                    k=k, h=3, direction="long")
                assert want is None, f"({entry}, {mode}, k={k}) 期望表應算出零窗"
    # 對照：非拒收對之同一 t0 有窗（否則上一句可能只是期望表整個壞了）
    ok = expected_row(bars, t0_idx=T0_IDXS[0], entry="trigger_open", mode="open_to_close",
                      k=0, h=3, direction="long")
    assert ok is not None and ok["label_end_ms"] == int(ct[T0_IDXS[0]])
    assert ok["entry_at_ms"] == int(ot[T0_IDXS[0]])


def test_rawbar_oracle_expected_table_is_falsifiable(bars):
    """🔴 **本層之可證偽性**：把期望表之 `next_open` 偏移改成 0 ⇒ 上面那條必紅。

    沒有這條，`ENTRY_EXPECT` 可以整張寫錯而測試照樣綠（因為它只跟自己比）。
    """
    rows, _, _ = actual_rows(bars, entry="next_open", mode="open_to_close", k=0, h=1,
                             direction="long")
    ot, _, _, _ = _cols(bars)
    eid = EVENT_IDS[0]
    good = expected_row(bars, t0_idx=T0_IDXS[0], entry="next_open", mode="open_to_close",
                        k=0, h=1, direction="long")
    assert rows[eid]["entry_at_ms"] == good["entry_at_ms"]
    original = ENTRY_EXPECT["next_open"]
    try:
        ENTRY_EXPECT.__class__  # noqa: B018  （Mapping 為 dict；下行就地改，finally 還原）
        dict.__setitem__(ENTRY_EXPECT, "next_open", ("fixed", 0, "open"))  # type: ignore[arg-type]
        bad = expected_row(bars, t0_idx=T0_IDXS[0], entry="next_open", mode="open_to_close",
                           k=0, h=1, direction="long")
        assert rows[eid]["entry_at_ms"] != bad["entry_at_ms"], "偏移改壞後仍相等 ⇒ 本層不可證偽"
    finally:
        dict.__setitem__(ENTRY_EXPECT, "next_open", original)  # type: ignore[arg-type]


# ── 第 (3) 層：property／differential grid ─────────────────────────────────

_FIXED_KS: Tuple[int, ...] = (0, 1, 2, 4)
_FIXED_HS: Tuple[int, ...] = (1, 2, 3, 5, 7)
_RANDOM_SEED = 20260903
_RANDOM_N = 40


def _grid_cells() -> List[Tuple[str, str, int, int, str]]:
    """固定網格 ＋ seeded 隨機抽樣（**可行域內**均勻取樣）之全部格。"""
    cells: List[Tuple[str, str, int, int, str]] = []
    for entry, mode in sorted(SUPPORTED_PAIRS):
        for k in _FIXED_KS:
            for h in _FIXED_HS:
                for direction in ("long", "short"):
                    cells.append((entry, mode, k, h, direction))
    rng = random.Random(_RANDOM_SEED)
    pairs = sorted(SUPPORTED_PAIRS)
    for _ in range(_RANDOM_N):
        entry, mode = pairs[rng.randrange(len(pairs))]
        # 可行域：k ≤ min(T0_IDXS)、h 使 end_idx 不越界（bar 表遠大於 t0_idx+h）
        k = rng.randint(0, 8)
        h = rng.randint(1, 12)
        cells.append((entry, mode, k, h, ("long", "short")[rng.randrange(2)]))
    return cells


_CELLS = _grid_cells()


def test_label_differential_grid_is_the_declared_size():
    """網格規模＝`13 × 4 × 5 × 2 + 40`；規模悄悄縮水就是覆蓋悄悄消失。"""
    assert len(SUPPORTED_PAIRS) == 13
    assert len(_CELLS) == 13 * len(_FIXED_KS) * len(_FIXED_HS) * 2 + _RANDOM_N == 560


def test_label_differential_grid(bars):
    """逐格以第 (2) 層之期望表比對；NaN mask 與 event 鍵集亦須相等。

    🔴 `atol=0`：報酬是純算術，沒有容差可言；容差會把「差一根 bar」藏起來。
    """
    ot, _, _, _ = _cols(bars)
    checked = 0
    for entry, mode, k, h, direction in _CELLS:
        rows, _, result = actual_rows(bars, entry=entry, mode=mode, k=k, h=h,
                                      direction=direction)
        assert result.supported is True
        want_ids = set()
        for t0_idx in T0_IDXS:
            eid = EVENT_IDS[T0_IDXS.index(t0_idx)]
            want = expected_row(bars, t0_idx=t0_idx, entry=entry, mode=mode, k=k, h=h,
                                direction=direction)
            if want is None:
                continue
            want_ids.add(eid)
            got = rows[eid]
            assert got["label_start_ms"] == want["label_start_ms"]
            assert got["label_end_ms"] == want["label_end_ms"]
            assert got["entry_price_ref"] == want["entry_price_ref"]
            assert got["label_value"] == pytest.approx(want["label_value"], abs=0.0, rel=1e-15)
            checked += 1
        # NaN mask：期望為 None 之事件不得有值；鍵集相等
        assert set(rows) == want_ids, f"({entry},{mode},k={k},h={h}) 鍵集不等"
        assert not [e for e, v in rows.items() if v["label_value"] is None], \
            f"({entry},{mode},k={k},h={h}) 可行域內不應有 None"
    assert checked >= len(_CELLS), "每格至少一個事件被實際比對過"


def test_label_differential_grid_mutation_end_bar_shift(bars, monkeypatch):
    """🔴 mutation 自證：`end_bar_index` 少算一根 ⇒ 上面那條必紅。

    改的是 producer 側之 `end_idx`（`alignment` 的 `end_idx` 由本函式之語意複製），
    期望表不動 ⇒ 兩邊分道揚鑣，值必不等。
    """
    import momentum.Analysis.event_samples.alignment as al

    real = al.align_events

    def mutated(events, bars_by_tf, config):
        rec, fail = real(events, bars_by_tf, config)
        if len(rec.event_level):
            ev = rec.event_level.copy()
            ev["label_end_ms"] = ev["label_end_ms"] - 43200000  # 少算一根 12h
            rec = type(rec)(event_level=ev, per_tf=rec.per_tf)
        return rec, fail

    monkeypatch.setattr(
        "momentum.Analysis.event_samples.label_value_from_case.align_events", mutated,
    )
    ot, _, _, _ = _cols(bars)
    rows, _, _ = actual_rows(bars, entry="trigger_open", mode="open_to_horizon_close",
                             k=0, h=3, direction="long")
    eid = EVENT_IDS[0]
    want = expected_row(bars, t0_idx=T0_IDXS[0], entry="trigger_open",
                        mode="open_to_horizon_close", k=0, h=3, direction="long")
    assert rows[eid]["label_end_ms"] != want["label_end_ms"], "mutation 未生效 ⇒ 本層不可證偽"
    assert rows[eid]["label_value"] != want["label_value"]
