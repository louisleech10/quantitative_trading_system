"""GAP-3 `G3-D2` golden 之**案例登記處**（`--init` 由此建檔；`--check` 不讀本檔）。

🔴 t0 **不寫死索引**：以具名 selector 從真實 bar 表導出，並在導出時斷言前置條件
（例如 `gap_bars` 斷言 `open(t) != close(t−1)`）。寫死索引會在 kline 增量更新後
指到別的 bar，而值仍合法 ⇒ 靜默失效。

各 phase 於此**追加**案例，不改既有條目（既有條目之值已凍結）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

SYMBOL = "ETHUSDT"
#: 預設 TF（既有案例之 `case_id` 皆含此字串，改動會改檔名 ⇒ 不得更動）。
TF = "12h"
#: 本登記處用到的全部 TF（`--init`／`--check` 之 bar 載入清單）。
TFS: Tuple[str, ...] = ("1h", "12h")
TF_SECONDS = {"1h": 3600, "12h": 43200}
DECLARED = {"12h": 0}

#: `matrix_pending` 之理由字面。**現行使用者＝k>0 案例**（`decision_bar_open × k=2`）：
#: D1.3 之 `SUPPORTED_MATRIX` 四對皆 k=0，k>0 之開放留待 **Task D4.2**。
#: 🔴 loader 之**反向 fail-closed 已實測生效**：D1.3 開矩陣後，四個 k=0 之 `open_to_*` 案例
#: 仍留著本旗標 ⇒ `--check` 當場 `GoldenError`（4 檔紅），迫使移除並重凍。
#: 🔴 **移除本旗標時勿全域取代**（2026-09-04 踩過）：`pending=True` 曾被一次 sed 全改成 False，
#: 連 k=2 那兩檔一起改掉，於是它們被凍成「全 None」（`變動鍵=['events','nan_event_ids']` 即警訊）。
#: 重凍前後**必須**逐位元組比對備份。
_D0_PENDING = (
    "k>0 尚不在 SUPPORTED_MATRIX（D1.3 四對皆 k=0）；k>0 之開放為 D-001 Task D4.2 之交付"
)


def _cols(bars, tf: str):
    df = bars[SYMBOL][tf]
    return (df["open_time_ms"].to_numpy(), df["open"].to_numpy(), df["close"].to_numpy())


def select_t0(selector: str, bars, tf: str = TF) -> Tuple[int, ...]:
    """具名 selector → t0 清單。未知 selector ⇒ raise（禁預設、禁靜默回空）。

    每個 selector 都在**導出時**斷言它自己的前置條件——否則「這個案例覆蓋了什麼」
    只存在於檔名，資料一換就悄悄失去覆蓋。
    """
    kind, _, arg = selector.partition(":")
    n = int(arg)
    ot, op, cl = _cols(bars, tf)
    if kind == "gap_bars":
        # §G 必含①：跳空 bar（open(t) != close(t−1)）。open_to_* 與 close_to_close 才分得開。
        out: List[int] = []
        for i in range(95, min(400, len(ot) - 20)):
            if op[i] != cl[i - 1]:
                out.append(int(ot[i]))
            if len(out) == n:
                break
        if len(out) != n:
            raise AssertionError(f"gap_bars:{n}@{tf} 於真實 kline 指定區間不足")
        return tuple(out)
    if kind == "plain":
        return tuple(int(ot[95 + 10 * i]) for i in range(n))
    if kind == "tail_mixed":
        # §G 必含②：資料末端 ⇒ 答案窗超出 ⇒ `label_window_incomplete`。
        # 🔴 **混合批**（正常事件 ＋ 末端事件）而非全末端：全末端會凍出 `events={}`，
        #    那種 golden 分不出「末端被正確丟棄」與「整個 producer 壞掉」。
        #    混合之後，凍結值同時釘住「好的算得出來」與「壞的不在鍵集」。
        # 🔴 末端取**倒數第三根**而非最後一根：t0 落在最後一根時，三段鏈與
        #    `entry_at < label_end` 兩條額外不變式也會擋，主守衛之覆蓋就變成不可證偽
        #    （同 `test_analysis_label_producer_07` 之理由）。
        if len(ot) < 120:
            raise AssertionError(f"tail_mixed@{tf} bar 數不足")
        return (int(ot[100]), int(ot[len(ot) - 3]))
    if kind == "warmup_mixed":
        # §G 必含③：資料**起點** ⇒ k>0 時 `t0_idx − k < 0` ⇒ `warmup_insufficient_{tf}`。
        # 同上：混合批，`ot[0]`（暖身不足）＋ `ot[100]`（正常）。
        if len(ot) < 120:
            raise AssertionError(f"warmup_mixed@{tf} bar 數不足")
        return (int(ot[0]), int(ot[100]))
    raise AssertionError(f"未知 t0 selector: {selector!r}")


def _spec(h: int, entry: str, mode: str, k: int) -> Dict[str, Any]:
    return {
        "horizon_bars": h,
        "entry_price_semantic": entry,
        "label_return_mode": mode,
        "decision_offset_bars": k,
    }


def _case(entry: str, mode: str, k: int, direction: str, h: int, *,
          selector: str, pending: bool, tf: str = TF) -> Dict[str, Any]:
    case_id = f"{entry}__{mode}__k{k}__{direction}__{tf}__h{h}"
    out: Dict[str, Any] = {
        "case_id": case_id,
        "file_name": f"{case_id}.json",
        "symbol": SYMBOL,
        "timeframe": tf,
        "direction": direction,
        "event_import_id": f"golden-{case_id}",
        "event_label_spec": _spec(h, entry, mode, k),
        "t0_selector": selector,
        "lookahead_bars_declared": {tf: 0},
        "timeframe_seconds": {tf: TF_SECONDS[tf]},
    }
    if pending:
        out["matrix_pending"] = True
        out["matrix_pending_reason"] = _D0_PENDING
    return out


#: ── Phase D0（Task D4.1）＋ Phase D1（Task D1.4）之凍結案例 ─────────────────
#  §G「必含案例」對照（每條都要指得出是哪一個檔在守）：
#    ① 跳空 bar                     → 全部 `gap_bars:*` 之案例
#    ② 資料末端 label_window_incomplete → `trigger_close__close_to_close__k0__long__12h__h5`（NaN mask 非空）
#    ③ k>0 之 warmup_insufficient    → `decision_bar_open__open_to_horizon_close__k2__long__12h__h1`
#    ④ next_open 之 entry_after_label_start=true → `next_open__close_to_close__k0__long__12h__h1`
#    ⑤ long／short 同價格序列，short == −long → 每個 k=0 組合皆成對
CASES: Tuple[Mapping[str, Any], ...] = (
    # ── D0 既有（值已凍結，勿改 selector／spec）────────────────────────────
    _case("trigger_close", "close_to_close", 0, "long", 3, selector="plain:4", pending=False),
    _case("trigger_close", "close_to_close", 0, "short", 3, selector="plain:4", pending=False),
    _case("trigger_close", "close_to_close", 0, "long", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_close", 0, "long", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_close", 0, "short", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_horizon_close", 0, "long", 3, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_horizon_close", 0, "short", 3, selector="gap_bars:3", pending=False),
    _case("decision_bar_open", "open_to_horizon_close", 2, "long", 3, selector="gap_bars:3", pending=True),
    _case("decision_bar_open", "open_to_horizon_close", 2, "short", 3, selector="gap_bars:3", pending=True),

    # ── D1.4 追加：SUPPORTED_MATRIX 四對 × {long,short} × h∈{1,3} 之補齊 ────
    _case("trigger_close", "close_to_close", 0, "short", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "close_to_close", 0, "long", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "close_to_close", 0, "short", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "close_to_close", 0, "long", 3, selector="gap_bars:3", pending=False),
    _case("trigger_open", "close_to_close", 0, "short", 3, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_horizon_close", 0, "long", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_horizon_close", 0, "short", 1, selector="gap_bars:3", pending=False),
    # 🔴 `open_to_close` 之 h **不參與計算**（起訖皆為 entry bar）⇒ h=3 之值須與 h=1 **逐位元組相同**。
    #    這兩個檔的存在就是那條斷言的證據（測試 `…_h_invariance` 直接比對兩檔）。
    _case("trigger_open", "open_to_close", 0, "long", 3, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_close", 0, "short", 3, selector="gap_bars:3", pending=False),

    # ── D1.4 追加：§G 必含②③④ ────────────────────────────────────────────
    # ② 資料末端：h=5 之答案窗超出 ⇒ 部分事件 label_window_incomplete ⇒ NaN mask 非空
    _case("trigger_close", "close_to_close", 0, "long", 5, selector="tail_mixed:2", pending=False),
    # ③ k>0 之 warmup：t0 落在資料最前 ⇒ t0_idx − k < 0 ⇒ warmup_insufficient_12h（全批失敗）
    _case("decision_bar_open", "open_to_horizon_close", 2, "long", 1, selector="warmup_mixed:2", pending=True),
    # ④ next_open × close_to_close：entry_at == ct[t0] == label_start ⇒ entry_after_label_start=true
    #    🔴 本組合**不在** SUPPORTED_MATRIX（留 D4.2）⇒ 需 matrix_pending；
    #    它守的是**收據之時間戳與 entry_price_ref**，不是 label_value。
    _case("next_open", "close_to_close", 0, "long", 1, selector="gap_bars:3", pending=True),

    # ── D1.4 追加：一組 1h（跨 TF；證明 golden 機制不綁 12h）──────────────
    _case("trigger_open", "open_to_close", 0, "long", 1, selector="gap_bars:3", pending=False, tf="1h"),
    _case("trigger_open", "open_to_close", 0, "short", 1, selector="gap_bars:3", pending=False, tf="1h"),
)


def resolved_cases(bars) -> List[Dict[str, Any]]:
    """把 `t0_selector` 解成 `t0_ms`，回傳 `--init` 可直接凍結之骨架清單。"""
    out = []
    for c in CASES:
        meta = {k: v for k, v in c.items() if k not in ("t0_selector", "file_name")}
        meta["t0_ms"] = list(select_t0(str(c["t0_selector"]), bars, str(c["timeframe"])))
        out.append({"file_name": str(c["file_name"]), "meta": meta})
    return out
