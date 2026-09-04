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
    # 🔴 **刻意取「倒數第三根」而不是最後一根**：t0 落在最後一根時，
    #    `label_start == label_end` 會讓三段鏈與 `entry_at < label_end` **兩條額外的不變式**
    #    也一起擋住它 ⇒ 針對主守衛的 mutation 會錄到空紅集合（重複守衛使 mutation 失明）。
    #    往內移兩根之後，h=5 仍然不足（只剩 2 根），但**只有主守衛擋得住**——
    #    這樣「尾端不足要丟棄」這條保護才有可證偽性。實測：M5 由空紅變為紅。
    recs = [
        make_event(0, t0=T0_100, label=1, direction="long"),
        make_event(1, t0=last_open - 2 * H12, label=0, direction="long"),  # 尾端：答案窗必不足
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


# ══════════════════════════════════════════════════════════════════════════
# `D-001` Phase D0（Task D4.1）— `entry_price_refs` 側載＋`open_to_*` 取價
#
# 選擇器：`pytest tests/momentum/event_samples/ -q -k "open_to or entry_price_ref"`
#
# 🔴 **為什麼這一段要 `replace(supported=True)`**：`SUPPORTED_MATRIX` 之開放是
#    `D-001` Task D1.3 的交付（「D0 過 gate 後四對即 D1 唯一矩陣」），D0 只交付**取價路徑**。
#    ⇒ 本段以 `dataclasses.replace` 把 `supported` 旗標打開，其餘（windows／refs／hash／
#    normalized_spec_bytes）**全部是 `prepare_analysis_windows` 對真實 kline 跑出來的真值**，
#    測到的是 `resolve_label_value_at_analyze` 的**生產路徑**，不是替身。
#    D1.3 開矩陣後須加一條「移除本旗標覆寫、值逐位元組相同」——見 `docs/GAP3D2_IMPL_HANDOFF.md` §5。
# ══════════════════════════════════════════════════════════════════════════

from dataclasses import replace  # noqa: E402  （本段專用；置頂會與上方既有 import 區混淆來源）

from momentum.Analysis.event_samples.label_value_from_case import (  # noqa: E402
    EntryPriceRef,
    _price_at,
)


def _open_series(bars):
    df = bars["ETHUSDT"]["12h"]
    return (df["open_time_ms"].to_numpy(), df["open"].to_numpy(), df["close"].to_numpy())


def gap_bar_t0s(bars, n: int = 2, lo: int = 95, hi: int = 200):
    """回傳 `n` 個**跳空 bar**（`open(t) != close(t−1)`）之 t0（bar open ms）。

    🔴 跳空是**前置條件**而非結論：呼叫端須先斷言不等式成立，否則
    `open_to_close` 與 `close_to_close` 兩式在連續網格上恰好同值，(i) 失去鑑別力。
    """
    ot, op, cl = _open_series(bars)
    out = []
    for i in range(max(lo, 3), min(hi, len(ot) - 20)):
        if op[i] != cl[i - 1]:
            out.append((i, int(ot[i])))
        if len(out) == n:
            break
    assert len(out) == n, "真實 kline 於指定區間找不到足夠的跳空 bar"
    return out


def d0_records(bars, *, direction: str = "long", n: int = 2):
    """跳空 bar 上的二元批（label 含 0 與 1）。"""
    return [
        make_event(i, t0=t0, label=i % 2, direction=direction)
        for i, (_idx, t0) in enumerate(gap_bar_t0s(bars, n=n))
    ]


def force_supported(p):
    """D0 專用：只翻 `supported` 旗標，其餘欄位為真實 prepare 之產物（見本段檔頭）。"""
    return replace(p, supported=True, reason=None)


# ── (i) 跳空 bar：`trigger_open × open_to_close` 手算 ───────────────────────

def test_analysis_label_producer_d0_gap_bar_open_to_close_exact(bars):
    """(i) `trigger_open × open_to_close` 之值 == `(close[t0]−open[t0])/open[t0]`，
    且 **!=** `(close[t0]−close[t0−1])/close[t0−1]`（＝修法前會靜默取到的別名值）。"""
    ot, op, cl = _open_series(bars)
    sp = spec(h=1, entry="trigger_open", mode="open_to_close")
    recs = d0_records(bars)
    p = force_supported(prep(bars, recs, sp))
    r = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)
    assert r.supported is True and r.label_values

    by_id = {w.event_id: w for w in p.windows}
    checked = 0
    for rec in recs:
        w = by_id.get(rec["event_id"])
        if w is None:
            continue
        i = int((ot == int(rec["t0"])).nonzero()[0][0])
        # 前置：本根確為跳空 bar（不成立則下面兩式同值，本條不可證偽）
        assert op[i] != cl[i - 1], f"idx={i} 非跳空 bar"
        expect_open = (float(cl[i]) - float(op[i])) / float(op[i])
        alias_close = (float(cl[i]) - float(cl[i - 1])) / float(cl[i - 1])
        assert r.label_values[w.event_id] == expect_open       # atol=0
        assert r.label_values[w.event_id] != alias_close       # 修法前之別名錯價
        checked += 1
    assert checked >= 1


# ── (ii) `decision_bar_open × open_to_horizon_close, k=2` 基準＝open[t0−2] ──

def test_analysis_label_producer_d0_decision_bar_open_to_horizon_close_k2(bars):
    """(ii) k=2 之 `decision_bar_open × open_to_horizon_close`：基準價＝`open[t0−2]`、
    終點＝`close[t0−2+h]`（entry bar 之 open，**不是** t₀ 的任何價）。"""
    ot, op, cl = _open_series(bars)
    h = 3
    sp = spec(h=h, entry="decision_bar_open", mode="open_to_horizon_close", k=2)
    recs = d0_records(bars)
    p = force_supported(prep(bars, recs, sp))
    r = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)
    assert r.supported is True and r.label_values

    refs = {e.event_id: e for e in p.entry_price_refs}
    by_id = {w.event_id: w for w in p.windows}
    checked = 0
    for rec in recs:
        w = by_id.get(rec["event_id"])
        if w is None:
            continue
        i = int((ot == int(rec["t0"])).nonzero()[0][0])
        assert refs[w.event_id].bar_open_ms == int(ot[i - 2])
        assert refs[w.event_id].field == "open"
        expect = (float(cl[i - 2 + h]) - float(op[i - 2])) / float(op[i - 2])
        assert r.label_values[w.event_id] == expect            # atol=0
        # 對照：若誤用 t₀ 之任一價當基準，值不同（證明上式不是恆真）
        assert expect != (float(cl[i - 2 + h]) - float(op[i])) / float(op[i])
        checked += 1
    assert checked >= 1


# ── (iii) mutation：ref.field open↔close 對調 ⇒ 值變 ────────────────────────

def test_analysis_label_producer_d0_entry_price_ref_field_swapped_changes_value(bars):
    """(iii) 把 `entry_price_ref.field` 由 `open` 換成 `close` ⇒ `label_value` 必變。

    這是「取價真的讀了 ref.field」之可證偽性：若實作把 field 寫死成 `open`，本條變恆等而紅。
    """
    sp = spec(h=1, entry="trigger_open", mode="open_to_close")
    p = force_supported(prep(bars, d0_records(bars), sp))
    ok = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)

    swapped = replace(p, entry_price_refs=tuple(
        EntryPriceRef(event_id=e.event_id, bar_open_ms=e.bar_open_ms,
                      field="close" if e.field == "open" else "open")
        for e in p.entry_price_refs
    ))
    bad = resolve_label_value_at_analyze(swapped, bars, event_label_spec=sp)
    assert set(ok.label_values) == set(bad.label_values) and ok.label_values
    assert any(ok.label_values[e] != bad.label_values[e] for e in ok.label_values), \
        "field 對調後值不變 ⇒ 取價未讀 ref.field（寫死欄位）"


# ── (iv) mutation：刪 refs ⇒ None ＋ reason 非空（禁回落 close） ─────────────

def test_analysis_label_producer_d0_entry_price_refs_dropped_is_none(bars):
    """(iv) refs 被清空 ⇒ open 語意之 `label_value is None` 且 `reason` 非空。

    🔴 **禁回落**：回落 `_close_at(label_start_ms)` 會取到 t₀−1 之 close（連續網格別名），
    那是一個**合法數字**，於是「refs 沒串進來」永遠不會紅。本條把它釘成 loud。
    """
    sp = spec(h=1, entry="trigger_open", mode="open_to_close")
    p = force_supported(prep(bars, d0_records(bars), sp))
    dropped = replace(p, entry_price_refs=())
    r = resolve_label_value_at_analyze(dropped, bars, event_label_spec=sp)
    assert r.label_values, "鍵集不得為空（否則 None 斷言恆真）"
    assert all(v is None for v in r.label_values.values())
    assert r.reason == UNSUPPORTED_REASON
    # 對照：refs 在時同一批算得出非 None（證明上面不是恆 None）
    good = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)
    assert good.reason is None
    assert any(v is not None for v in good.label_values.values())


# ── (v) 改任一 ref 值 ⇒ hash 必變 ──────────────────────────────────────────

def test_analysis_label_producer_d0_entry_price_ref_value_changed_changes_hash(bars):
    """(v) `entry_price_refs` 進 `_receipt_hash` payload：改一個 ref ⇒ hash 必變。"""
    from momentum.Analysis.event_samples.label_value_from_case import _receipt_hash

    sp = spec(h=1, entry="trigger_open", mode="open_to_close")
    p = prep(bars, d0_records(bars), sp)
    args = dict(event_import_id="imp-1", normalized_spec_bytes=p.normalized_spec_bytes,
                windows=p.windows, per_tf=p.per_tf, direction_sign=p.direction_sign)
    base_hash = _receipt_hash(**args, entry_price_refs=p.entry_price_refs)
    assert base_hash == p.analysis_alignment_receipt_hash    # 生產路徑就是這個 payload

    bumped = (replace(p.entry_price_refs[0], bar_open_ms=p.entry_price_refs[0].bar_open_ms + 1),
              ) + p.entry_price_refs[1:]
    assert _receipt_hash(**args, entry_price_refs=bumped) != base_hash
    swapped_field = (replace(p.entry_price_refs[0], field="close"),) + p.entry_price_refs[1:]
    assert _receipt_hash(**args, entry_price_refs=swapped_field) != base_hash


# ── (v′) 同一批不同 entry 語意 ⇒ hash 不等（refs 進 hash 之語意價值） ────────

def test_analysis_label_producer_d0_entry_price_ref_distinguishes_entry_semantics(bars):
    """`trigger_open` 與 `trigger_close`（同為 `close_to_close`、同 h）之 hash **不等**。

    兩者之 `windows` 只差 `entry_at_ms`；本條連同 (v) 一起釘住「refs 真的進了 payload」。
    """
    recs = d0_records(bars)
    a = prep(bars, recs, spec(h=2, entry="trigger_open"))
    b = prep(bars, recs, spec(h=2, entry="trigger_close"))
    assert a.analysis_alignment_receipt_hash != b.analysis_alignment_receipt_hash
    assert {e.field for e in a.entry_price_refs} == {"open"}
    assert {e.field for e in b.entry_price_refs} == {"close"}


# ── (vi) 既有 `close_to_close` 值不變（hash 合法變一次） ────────────────────

def test_analysis_label_producer_d0_close_to_close_values_unchanged_by_entry_price_ref(bars):
    """(vi) `close_to_close` 之基準價**仍**取 `label_start_ms` 之 close，與 refs 無關。

    以「把 refs 換成明顯錯的座標」證明 `close_to_close` 路徑根本沒讀 refs
    ⇒ 既有值逐位元組不變（獨立手算 oracle 見上方 ①，未改）。
    """
    sp = spec()  # trigger_close × close_to_close × k=0（既有支援組合）
    p = prep(bars, records("long"), sp)
    r0 = resolve_label_value_at_analyze(p, bars, event_label_spec=sp)
    tampered = replace(p, entry_price_refs=tuple(
        EntryPriceRef(event_id=e.event_id, bar_open_ms=e.bar_open_ms + 7 * H12, field="open")
        for e in p.entry_price_refs
    ))
    r1 = resolve_label_value_at_analyze(tampered, bars, event_label_spec=sp)
    assert r0.label_values == r1.label_values and r0.label_values
    for w in p.windows:
        assert r0.label_values[w.event_id] == hand_return(bars, w)   # atol=0


# ── refs 之形狀不變式 ＋ `_price_at` 之 under/over 向 ───────────────────────

def test_analysis_label_producer_d0_entry_price_refs_same_order_and_length(bars):
    """`entry_price_refs` 與 `windows` **同序同長**（排序鍵相同 ⇒ 逐位置對應）。"""
    p = prep(bars, records("long"), spec())
    assert len(p.entry_price_refs) == len(p.windows)
    assert [e.event_id for e in p.entry_price_refs] == [w.event_id for w in p.windows]


def test_analysis_label_producer_d0_open_to_star_mismatched_label_start_raises(bars):
    """`open_to_*` 之 `label_start_ms != entry_at_ms` ⇒ `LabelProducerError`（fail-closed）。"""
    sp = spec(h=1, entry="trigger_open", mode="open_to_close")
    p = force_supported(prep(bars, d0_records(bars), sp))
    broken = replace(p, windows=tuple(
        replace(w, label_start_ms=w.label_start_ms + 1) for w in p.windows
    ))
    with pytest.raises(LabelProducerError, match="entry_at_ms"):
        resolve_label_value_at_analyze(broken, bars, event_label_spec=sp)


def test_analysis_label_producer_d0_entry_price_ref_price_at_lookup(bars):
    """`_price_at`：命中唯一列回該欄值；找不到／欄位不存在 ⇒ `None`（不猜最近的一根）。"""
    df = bars["ETHUSDT"]["12h"]
    ot = df["open_time_ms"].to_numpy()
    i = 100
    assert _price_at(df, int(ot[i]), "open") == float(df["open"].to_numpy()[i])
    assert _price_at(df, int(ot[i]), "close") == float(df["close"].to_numpy()[i])
    assert _price_at(df, int(ot[i]) + 1, "open") is None          # 不存在之 open_time
    assert _price_at(df, int(ot[i]), "high") is None              # 欄位不存在


# ── golden 掛載（`D-001` D1.4 之 parametrize；D0 先掛，避免凍結檔沒有任何執行者） ──

def _golden_paths():
    import glob as _glob
    from pathlib import Path as _Path
    root = _Path(__file__).resolve().parents[3] / "tests" / "golden" / "gap3_label"
    return sorted(_Path(p) for p in _glob.glob(str(root / "*.json")))


@pytest.fixture(scope="module")
def golden_bars():
    """golden 專用 bar 表：TF 清單取自**登記處**（`cases.TFS`），不是本檔的 12h fixture。

    🔴 D1.4 起 golden 含 1h 案例；沿用 12h-only 之 `bars` fixture 會讓那些案例以 KeyError
    炸開，而 `scripts/gap3_label_golden.py --check` 卻是綠的——兩條路徑載入不同資料，
    就是「CLI 綠、pytest 紅」這種最難查的不一致。TF 清單只有登記處一份。
    """
    from tests.golden.gap3_label import cases as case_registry
    return load_bars(case_registry.SYMBOL, case_registry.TFS)


@pytest.mark.parametrize("golden_path", _golden_paths(), ids=lambda p: p.stem)
def test_analysis_label_producer_d0_entry_price_ref_golden(golden_path, golden_bars):
    """每個凍結檔逐項 `==`（值／時間戳／`entry_price_ref`／NaN mask／hash／purge）。

    🔴 `_golden_paths()` 為空即視為錯誤：glob 打空會讓本條靜默零執行（假綠）。
    """
    from tests.golden.gap3_label.loader import check_golden, load_golden

    report = check_golden(load_golden(golden_path), golden_bars)
    assert report.ok, "\n".join(report.diffs)


def test_analysis_label_producer_d0_entry_price_ref_golden_set_nonempty():
    """golden 集合非空（釘住上一條之 parametrize 不會被 glob 打空成 0 個 case）。"""
    paths = _golden_paths()
    assert len(paths) >= 9, f"golden 檔數不足：{[p.name for p in paths]}"
    names = {p.stem for p in paths}
    assert any("open_to_close" in n for n in names)          # 跳空案例（§G 必含 ①）
    assert any(n.startswith("decision_bar_open") for n in names)   # k>0 之 entry bar


# ══════════════════════════════════════════════════════════════════════════
# `D-001` Task D1.3／D1.4 — 支援矩陣擴充與 golden 覆蓋
# ══════════════════════════════════════════════════════════════════════════

def _load_golden_json(stem: str) -> dict:
    import json
    from pathlib import Path as _Path
    root = _Path(__file__).resolve().parents[3] / "tests" / "golden" / "gap3_label"
    return json.loads((root / f"{stem}.json").read_text(encoding="utf-8"))


# ── D1.3：四對支援矩陣之語意 ───────────────────────────────────────────────

def test_analysis_label_producer_d13_trigger_open_close_to_close_equals_trigger_close(bars):
    """(i) `close_to_close` 之值與 entry 語意**無關**（D1-5：錨是 t₀ 的 close，不是 entry）。

    同一批、同 h，`trigger_open` 與 `trigger_close` 之 `label_values` 逐 event `==`（`atol=0`）。
    """
    recs = d0_records(bars)
    a_sp = spec(h=2, entry="trigger_open", mode="close_to_close")
    b_sp = spec(h=2, entry="trigger_close", mode="close_to_close")
    pa, pb = prep(bars, recs, a_sp), prep(bars, recs, b_sp)
    assert pa.supported is True and pb.supported is True, "D1.3 後兩者皆須在矩陣內"
    ra = resolve_label_value_at_analyze(pa, bars, event_label_spec=a_sp)
    rb = resolve_label_value_at_analyze(pb, bars, event_label_spec=b_sp)
    assert set(ra.label_values) == set(rb.label_values) and ra.label_values
    for eid, v in ra.label_values.items():
        assert rb.label_values[eid] == v          # atol=0


def test_analysis_label_producer_d13_trigger_open_entry_at_and_hash_differ(bars):
    """(ii) 但兩者之 `entry_at_ms` **不等**、`analysis_alignment_receipt_hash` **不等**。

    值相等而身分不等——沒有這條，上一條就可能是「兩邊其實跑了同一個 spec」。
    """
    recs = d0_records(bars)
    pa = prep(bars, recs, spec(h=2, entry="trigger_open", mode="close_to_close"))
    pb = prep(bars, recs, spec(h=2, entry="trigger_close", mode="close_to_close"))
    ea = {w.event_id: w.entry_at_ms for w in pa.windows}
    eb = {w.event_id: w.entry_at_ms for w in pb.windows}
    assert ea and all(ea[e] != eb[e] for e in ea), "trigger_open 之 entry_at 須為 bar open，與 close 不同"
    assert pa.analysis_alignment_receipt_hash != pb.analysis_alignment_receipt_hash


def test_analysis_label_producer_d13_matrix_membership_under_and_over(bars):
    """`SUPPORTED_MATRIX` 之 under／over 兩向：四對在內、鄰近組合在外。

    🔴 **over 向不可省**：只驗「四對為 True」時，把矩陣改成「全部回 True」也會綠。
    """
    from momentum.Analysis.event_samples.label_value_from_case import (
        SUPPORTED_MATRIX, normalize_event_label_spec, spec_is_supported,
    )
    assert SUPPORTED_MATRIX == frozenset({
        ("trigger_close", "close_to_close", 0),
        ("trigger_open", "close_to_close", 0),
        ("trigger_open", "open_to_close", 0),
        ("trigger_open", "open_to_horizon_close", 0),
    })
    for entry, mode in [("trigger_close", "close_to_close"), ("trigger_open", "close_to_close"),
                        ("trigger_open", "open_to_close"), ("trigger_open", "open_to_horizon_close")]:
        assert spec_is_supported(normalize_event_label_spec(spec(entry=entry, mode=mode))) is True
    # over 向：矩陣外之鄰近組合須為 False（D1.3 邊界①②）
    for entry, mode, k in [("trigger_close", "open_to_close", 0),        # 幾何零窗，D4.2 才處理
                           ("trigger_close", "open_to_horizon_close", 0),
                           ("next_open", "close_to_close", 0),
                           ("decision_bar_open", "open_to_horizon_close", 0),
                           ("trigger_open", "close_to_close", 1)]:       # k>0 留 D4
        assert spec_is_supported(
            normalize_event_label_spec(spec(entry=entry, mode=mode, k=k))
        ) is False, f"({entry}, {mode}, {k}) 不應在 D1 矩陣內"


# ── D1.4：golden 覆蓋之可證偽性 ────────────────────────────────────────────

def test_analysis_label_producer_d14_open_to_close_value_invariant_to_h():
    """`open_to_close` 之起訖皆為 entry bar ⇒ 值**不隨 h 變**：h=1 與 h=3 之 golden 逐位元組相同。

    這條把「h 被誤用進 open_to_close 的窗」釘死——那種錯會算出合法數字。
    """
    for direction in ("long", "short"):
        a = _load_golden_json(f"trigger_open__open_to_close__k0__{direction}__12h__h1")
        b = _load_golden_json(f"trigger_open__open_to_close__k0__{direction}__12h__h3")
        assert a["t0_ms"] == b["t0_ms"], "兩檔須為同一組 t0，否則比對無意義"
        assert set(a["events"]) == set(b["events"]) and a["events"]
        for eid in a["events"]:
            assert b["events"][eid]["label_value"] == a["events"][eid]["label_value"]
            assert b["events"][eid]["label_end_ms"] == a["events"][eid]["label_end_ms"]
        # 🔴 對照：hash **須不等**（h 進 normalized_spec_bytes ⇒ 身分不同），
        #    否則本條會與「兩檔其實是同一個 spec」無法區分。
        assert a["analysis_alignment_receipt_hash"] != b["analysis_alignment_receipt_hash"]


def test_analysis_label_producer_d14_golden_covers_required_boundary_cases():
    """§G「必含案例」逐條指得出守門的檔——缺任一即紅（防止 golden 集合悄悄失去覆蓋）。"""
    names = {p.stem for p in _golden_paths()}
    # ① 跳空 bar：至少一個 open_to_close 案例（其 t0 由 gap_bars selector 逐根斷言過）
    assert "trigger_open__open_to_close__k0__long__12h__h1" in names
    # ② 資料末端：混合批 ⇒ 2 個 t0 但只有 1 個 event（壞的不在鍵集，非填 0）
    tail = _load_golden_json("trigger_close__close_to_close__k0__long__12h__h5")
    assert len(tail["t0_ms"]) == 2 and len(tail["events"]) == 1, "末端案例須為混合批"
    # ③ k>0 之 warmup：同為混合批
    warm = _load_golden_json("decision_bar_open__open_to_horizon_close__k2__long__12h__h1")
    assert len(warm["t0_ms"]) == 2 and len(warm["events"]) == 1, "warmup 案例須為混合批"
    # ④ next_open：entry_at == label_start（＝收據之 entry_after_label_start 為 true 之機械內容）
    nxt = _load_golden_json("next_open__close_to_close__k0__long__12h__h1")
    assert nxt["events"]
    for v in nxt["events"].values():
        assert v["entry_at_ms"] == v["label_start_ms"]
        assert v["entry_price_ref"]["field"] == "open"
    # ⑤ long／short 成對，且 short == −long
    for stem in [n for n in names if "__long__" in n]:
        s = stem.replace("__long__", "__short__")
        if s not in names:
            continue
        a, b = _load_golden_json(stem), _load_golden_json(s)
        for eid in a["events"]:
            va, vb = a["events"][eid]["label_value"], b["events"][eid]["label_value"]
            if va is None or vb is None:
                continue
            assert vb == -va, f"{stem}: short 須為 long 之相反數"
    # 跨 TF：至少一個 1h 案例（證明 golden 機制不綁 12h）
    assert any(n.endswith("__1h__h1") for n in names), "須有 1h 案例"


def test_analysis_label_producer_d14_next_open_receipt_entry_after_label_start(bars):
    """§G 必含④之**收據側**對證：`next_open × close_to_close` ⇒ `entry_after_label_start` 為 True。

    golden 只凍時間戳；本條直接讀 `align_events` 收據那一欄，兩邊都守才不會有一邊悄悄變。
    """
    import pandas as pd
    from momentum.Analysis.event_samples.alignment import align_events
    from momentum.Analysis.event_samples.types import AlignmentConfig

    recs = [dict(r) for r in d0_records(bars)]
    for r in recs:
        r["entry_price_semantic"] = "next_open"
        r["label_definition"] = {**r["label_definition"], "label_return_mode": "close_to_close"}
    receipts, _ = align_events(pd.DataFrame(recs), bars, AlignmentConfig(timeframes=("12h",)))
    rows = receipts.event_level.to_dict("records")
    assert rows, "收據不得為空（否則下面的斷言恆真）"
    for row in rows:
        assert bool(row["entry_after_label_start"]) is True
        assert int(row["entry_at_ms"]) == int(row["label_start_ms"])
        assert row["entry_price_source_field"] == "open"


# ── D1.2：`event_known_at_decision` ───────────────────────────────────────

def test_alignment_event_known_at_decision_is_false_for_k0_and_k2(bars):
    """(i) 真實 kline、k∈{0,2} 兩事件之 `event_known_at_decision` 皆 `False`（D2-2 之等式）。"""
    from momentum.Analysis.event_samples.alignment import align_events
    import pandas as pd
    from momentum.Analysis.event_samples.types import AlignmentConfig

    df = bars["ETHUSDT"]["12h"]
    ct = df["close_time_ms"].to_numpy()
    ot = df["open_time_ms"].to_numpy()
    for k in (0, 2):
        recs = [dict(r) for r in d0_records(bars)]
        for r in recs:
            r["decision_offset_bars"] = k
        receipts, _ = align_events(pd.DataFrame(recs), bars, AlignmentConfig(timeframes=("12h",)))
        rows = receipts.event_level.to_dict("records")
        assert rows, f"k={k} 之收據不得為空"
        for row in rows:
            assert bool(row["event_known_at_decision"]) is False
            # 🔴 **不是恆 False 的斷言**：同時釘住它的定義式，這樣改壞定義才會紅
            i = int((ot == int(row["t0_ms"])).nonzero()[0][0])
            assert row["event_known_at_decision"] == bool(int(row["decision_at_ms"]) >= int(ct[i]))


def test_alignment_event_known_at_decision_column_registered_in_contract():
    """契約 `receipt_schema.event_level` 須含本欄且型別為 `bool`；`_EVENT_COLS` 順序前綴不變。"""
    from momentum.Analysis.event_samples.alignment import _EVENT_COLS
    from momentum.Analysis.event_samples.import_contract import load_event_import_contract

    schema = load_event_import_contract()["receipt_schema"]["event_level"]
    assert schema.get("event_known_at_decision") == "bool"
    assert _EVENT_COLS[-1] == "event_known_at_decision", "須追加於末位（前綴保留）"
    assert list(schema)[:len(_EVENT_COLS) - 1] == _EVENT_COLS[:-1], "契約與收據欄序須一致"
