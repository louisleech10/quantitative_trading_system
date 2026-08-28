"""GAP-3 UX **Task 7.0b** 驗收 ①–⑦（SPEC L2665–2677）＋ `D-005` A-023 之四條。

選擇器：`pytest tests/momentum/event_samples/ -q -k analysis_label_producer`。

🔴 **真實 kline，禁合成價格**（CLAUDE.md 資料鐵律）：本檔全部用
`data_cache/feature_klines/kline_cache.h5` 之 ETHUSDT 連續網格。
「手算」＝直接從同一份 bar 表取兩根的 close 相除，**不是**另寫一份報酬公式
——那樣只會測到「兩份實作是否一致」，而不是「值對不對」。

🔴 **①② 共用同一組價格序列，只改 `direction`**。兩組不同 fixture 各自手算的話，
「short 是 long 的相反數」這件事就無從證偽（那正是 R2 consult 裡被否決的 `丁` 選項的錯法）。
"""

from __future__ import annotations

import pytest

from momentum.Analysis.event_samples.keys import EventKeyError, event_direction_sign
from momentum.Analysis.event_samples.label_value_from_case import (
    UNSUPPORTED_REASON,
    LabelProducerError,
    apply_event_coverage,
    prepare_analysis_windows,
    resolve_label_value_at_analyze,
)
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000  # 2024-01-01 00:00 UTC（ms）
H12 = 43200000
T0_100 = BASE + 100 * H12  # 12h 第 100 根 open
TF_SECONDS = {"12h": 43200}
DECLARED = {"12h": 0}


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def spec(h: int = 2, *, entry: str = "trigger_close", mode: str = "close_to_close", k: int = 0) -> dict:
    """`event_label_spec` 之四鍵（恰四鍵；多一鍵少一鍵皆 fail-closed）。"""
    return {
        "horizon_bars": h,
        "entry_price_semantic": entry,
        "label_return_mode": mode,
        "decision_offset_bars": k,
    }


def records(direction: str = "long", *, n: int = 2):
    """二元批（`label` 須含 0 與 1，否則匯入層之 `missing_control_group` 會擋）。"""
    return [
        make_event(i, t0=T0_100 + i * 10 * H12, label=i % 2, direction=direction)
        for i in range(n)
    ]


def prep(bars, recs, sp, *, import_id="imp-1"):
    return prepare_analysis_windows(
        recs, bars,
        event_label_spec=sp,
        event_import_id=import_id,
        lookahead_bars_declared=DECLARED,
        timeframe_seconds=TF_SECONDS,
    )


def hand_return(bars, w) -> float:
    """手算：直接從**同一份 bar 表**取 `label_start_ms`／`label_end_ms` 兩根的 close。

    這兩個時間戳來自 `align_events` 的收據，本函式不推導「是哪一根」——
    推導第二次就變成在測兩份實作是否一致。
    """
    df = bars["ETHUSDT"]["12h"]
    ct = df["close_time_ms"].to_numpy()
    close = df["close"].to_numpy()
    base = float(close[(ct == w.label_start_ms).nonzero()[0][0]])
    end = float(close[(ct == w.label_end_ms).nonzero()[0][0]])
    return (end - base) / base


# ── ①② signed（同一組價格序列，只改 direction） ─────────────────────────────

def test_analysis_label_producer_01_long_exact(bars):
    """① F-1′ 內 ⇒ `supported is True` 且值 == 手算（long，`atol=0`）。"""
    p = prep(bars, records("long"), spec())
    assert p.supported is True and p.reason is None
    r = resolve_label_value_at_analyze(p, bars, event_label_spec=spec())
    assert r.supported is True
    assert set(r.label_values) == {w.event_id for w in p.windows}
    for w in p.windows:
        assert r.label_values[w.event_id] == hand_return(bars, w)  # atol=0


def test_analysis_label_producer_02_short_is_exact_negation(bars):
    """② 同上 short ⇒ 值為①之**相反數**（`== -x`，`atol=0`）。`D-005` A-023 之主驗收。"""
    long_p = prep(bars, records("long"), spec())
    short_p = prep(bars, records("short"), spec())
    long_r = resolve_label_value_at_analyze(long_p, bars, event_label_spec=spec())
    short_r = resolve_label_value_at_analyze(short_p, bars, event_label_spec=spec())
    assert set(long_r.label_values) == set(short_r.label_values)
    assert long_r.label_values  # 防「兩個空 dict 也相等」之恆真
    for eid, x in long_r.label_values.items():
        assert short_r.label_values[eid] == -x  # atol=0


# ── ③④⑤ 非 F-1′ 三元組 ────────────────────────────────────────────────────

def test_analysis_label_producer_03_next_open_unsupported(bars):
    """③ `entry_price_semantic='next_open'` ⇒ `supported is False`、`label_values == {}`。"""
    sp = spec(entry="next_open")
    p = prep(bars, records("long"), sp)
    r = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)
    assert r.supported is False
    assert r.label_values == {}
    assert r.reason == UNSUPPORTED_REASON


def test_analysis_label_producer_04_k3_unsupported_but_decision_before_t0(bars):
    """④ `decision_offset_bars=3` ⇒ 同③；**且**該 eid 之 `WindowRow.decision_at_ms < t0`。

    🔴 後半是重點：它證明 **k 的映射真的生效了**，不是被忽略。
    所以 prepare 在不支援時**仍然對齊、仍然產窗**，只有值被扣住。
    🔴 `windows` 是 tuple ⇒ **禁** `windows[eid][...]` 之 dict API（R15）。
    """
    sp = spec(k=3)
    p = prep(bars, records("long"), sp)
    r = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)
    assert r.supported is False and r.label_values == {}
    assert p.windows, "k=3 之批次仍須產出 windows（否則本條的後半無從斷言）"
    by_id = {w.event_id: w for w in p.windows}          # 先建 map，不用 id 下標
    for rec in records("long"):
        w = by_id.get(rec["event_id"])
        if w is not None:
            assert w.decision_at_ms < rec["t0"]


def test_analysis_label_producer_05_open_to_close_unsupported(bars):
    """⑤ `label_return_mode='open_to_close'` ⇒ 同③。"""
    sp = spec(mode="open_to_close")
    p = prep(bars, records("long"), sp)
    r = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)
    assert r.supported is False and r.label_values == {}


# ── ⑥ 同批不同 h ───────────────────────────────────────────────────────────

def test_analysis_label_producer_06_h3_vs_h7(bars):
    """⑥ 同一批以 `h=3`／`h=7` 各跑一次 ⇒ event id 集合**相同**、值**不相同**、
    各 `WindowRow.label_end_ms` 各自對應自己的 h。

    🔴 fixture 必須是**非退化**價格序列（`CODEX-R1-P2-06`）：flat-close 序列下
    兩個 h 都算出 `0.0`，正確實作照樣紅。真實 ETHUSDT 網格非平坦，並在下方顯式斷言。
    """
    p3 = prep(bars, records("long"), spec(h=3))
    p7 = prep(bars, records("long"), spec(h=7))
    r3 = resolve_label_value_at_analyze(p3, bars, event_label_spec=spec(h=3))
    r7 = resolve_label_value_at_analyze(p7, bars, event_label_spec=spec(h=7))
    assert set(r3.label_values) == set(r7.label_values)
    assert r3.label_values
    # 非退化前置：至少有一個 eid 之兩值不等（若全等代表 fixture 平坦，本條失去鑑別力）
    assert any(r3.label_values[e] != r7.label_values[e] for e in r3.label_values), \
        "fixture 為退化（平坦）序列——本條在這種 fixture 下不可證偽"
    w3 = {w.event_id: w.label_end_ms for w in p3.windows}
    w7 = {w.event_id: w.label_end_ms for w in p7.windows}
    for eid in w3:
        assert w7[eid] > w3[eid], "h=7 之 label_end 須晚於 h=3（各自對應自己的 h）"


# ── ⑦ 尾端不足 ────────────────────────────────────────────────────────────

def test_analysis_label_producer_07_tail_insufficient_absent_not_zero(bars):
    """⑦ 尾端不足 ⇒ 該 eid **不出現**於餵給下游之鍵集（**非**填 0）。

    尾端事件之答案窗超出資料末端 ⇒ `align_events` 判 `label_window_incomplete`
    ⇒ 根本不會有 `WindowRow` ⇒ 鍵集自然不含它。這裡把「不含」釘住，
    因為「填 0」是這條最常見的壞法，而 0 是一個合法的報酬值、看不出異常。
    """
    df = bars["ETHUSDT"]["12h"]
    last_open = int(df["open_time_ms"].to_numpy()[-1])
    recs = [
        make_event(0, t0=T0_100, label=1, direction="long"),
        make_event(1, t0=last_open, label=0, direction="long"),  # 尾端：答案窗必不足
    ]
    p = prep(bars, recs, spec(h=5))
    r = resolve_label_value_at_analyze(p, bars, event_label_spec=spec(h=5))
    assert r.supported is True
    assert "ev1" not in r.label_values, "尾端不足之 eid 不得出現於鍵集"
    assert "ev1" not in {w.event_id for w in p.windows}
    assert r.label_values.get("ev0") is not None  # 對照：正常事件仍算得出來


# ── `D-005` A-023 之四條 ───────────────────────────────────────────────────

def test_analysis_label_producer_a023_direction_sign_in_hash(bars):
    """A-023 第 5 條：long 與 short 兩次 prepare 之 `analysis_alignment_receipt_hash` **不相等**。

    否則兩者 `label_values` 正負相反卻共用同一個 hash ⇒ 驗收 ⑩「三處讀到同一 hash」
    會在錯誤的前提下全綠。
    """
    long_p = prep(bars, records("long"), spec())
    short_p = prep(bars, records("short"), spec())
    assert long_p.direction_sign == 1 and short_p.direction_sign == -1
    assert long_p.analysis_alignment_receipt_hash != short_p.analysis_alignment_receipt_hash
    # 對照：同方向兩次 prepare ⇒ hash **相等**（決定性），證明上一條不是「hash 恆不等」
    assert (prep(bars, records("long"), spec()).analysis_alignment_receipt_hash
            == long_p.analysis_alignment_receipt_hash)


def test_analysis_label_producer_a023_mixed_direction_rejected(bars):
    """A-023 第 3 條：批內混方向 ⇒ `prepare_analysis_windows` raise（第二道，不只信匯入層）。"""
    recs = [
        make_event(0, t0=T0_100, label=1, direction="long"),
        make_event(1, t0=T0_100 + 10 * H12, label=0, direction="short"),
    ]
    with pytest.raises(LabelProducerError, match="direction"):
        prep(bars, recs, spec())


@pytest.mark.parametrize("bad", [None, "Long", "LONG", "", "buy", 1])
def test_analysis_label_producer_a023_direction_bad_values_rejected(bad):
    """A-023 第 2 條（**under 向**）：缺鍵／`None`／大小寫變體／非枚舉值一律 raise。"""
    with pytest.raises(EventKeyError):
        event_direction_sign({"direction": bad})


@pytest.mark.parametrize("good,sign", [("long", 1), ("short", -1)])
def test_analysis_label_producer_a023_direction_good_values_accepted(good, sign):
    """A-023 第 2 條（🔴 **over 向對照**）：兩個合法值須成功——證明上一條不是恆 raise。"""
    assert event_direction_sign({"direction": good}) == sign


# ── spec 綁定（R12 `CODEX-R12-P1-05`） ─────────────────────────────────────

def test_analysis_label_producer_spec_binding_h7_prepare_h3_resolve(bars):
    """以 `h=7` prepare、再以 `h=3` resolve ⇒ **fail-closed**（逐位元組比對）。

    沒有這條就能用 h=7 prepare 拿 hash／token、用 h=3 resolve，兩者回同一 hash／token
    而驗收全綠——那就是 purge 用 h=7、label 用 h=3。
    """
    p7 = prep(bars, records("long"), spec(h=7))
    bad = resolve_label_value_at_analyze(p7, bars, event_label_spec=spec(h=3))
    assert bad.supported is False and bad.label_values == {}
    assert bad.reason == UNSUPPORTED_REASON
    # 🔴 **over 向對照**：h=7 prepare ＋ h=7 resolve 須通過（證明不是恆 fail）
    good = resolve_label_value_at_analyze(p7, bars, event_label_spec=spec(h=7))
    assert good.supported is True and good.label_values


# ── coverage（⑭ (e)：初值＝全集；replace 不重算 token／hash） ──────────────

def test_analysis_label_producer_coverage_replace_keeps_identity(bars):
    """`apply_event_coverage` ⇒ 新身分、**同** token 同 hash；初值為全集。"""
    p0 = prep(bars, records("long"), spec())
    assert p0.allowed_event_ids == frozenset(w.event_id for w in p0.windows)
    keep = frozenset(list(p0.allowed_event_ids)[:1])
    p1 = apply_event_coverage(p0, keep)
    assert p1 is not p0                                   # 走 replace，非原地突變
    assert p1.prepared_token == p0.prepared_token
    assert p1.analysis_alignment_receipt_hash == p0.analysis_alignment_receipt_hash
    assert p1.allowed_event_ids == keep
    # 🔴 **over 向**：未剔除任何列時 ⇒ 兩者 allowed 集合相等
    assert apply_event_coverage(p0, p0.allowed_event_ids).allowed_event_ids == p0.allowed_event_ids
    # 🔴 只能縮不能擴
    with pytest.raises(LabelProducerError, match="不得擴張"):
        apply_event_coverage(p0, p0.allowed_event_ids | {"ev-not-there"})
