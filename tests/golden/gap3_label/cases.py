"""GAP-3 `G3-D2` golden 之**案例登記處**（`--init` 由此建檔；`--check` 不讀本檔）。

🔴 t0 **不寫死索引**：以具名 selector 從真實 bar 表導出，並在導出時斷言前置條件
（例如 `gap_bars` 斷言 `open(t) != close(t−1)`）。寫死索引會在 kline 增量更新後
指到別的 bar，而值仍合法 ⇒ 靜默失效。

各 phase 於此**追加**案例，不改既有條目（既有條目之值已凍結）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

SYMBOL = "ETHUSDT"
TF = "12h"
TF_SECONDS = {"12h": 43200}
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


def _bars_cols(bars):
    df = bars[SYMBOL][TF]
    return (df["open_time_ms"].to_numpy(), df["open"].to_numpy(), df["close"].to_numpy())


def select_t0(selector: str, bars) -> Tuple[int, ...]:
    """具名 selector → t0 清單。未知 selector ⇒ raise（禁預設）。"""
    kind, _, arg = selector.partition(":")
    n = int(arg)
    ot, op, cl = _bars_cols(bars)
    if kind == "gap_bars":
        out: List[int] = []
        for i in range(95, min(400, len(ot) - 20)):
            if op[i] != cl[i - 1]:          # 前置：確為跳空 bar
                out.append(int(ot[i]))
            if len(out) == n:
                break
        if len(out) != n:
            raise AssertionError(f"gap_bars:{n} 於真實 kline 指定區間不足")
        return tuple(out)
    if kind == "plain":
        return tuple(int(ot[95 + 10 * i]) for i in range(n))
    raise AssertionError(f"未知 t0 selector: {selector!r}")


def _spec(h: int, entry: str, mode: str, k: int) -> Dict[str, Any]:
    return {
        "horizon_bars": h,
        "entry_price_semantic": entry,
        "label_return_mode": mode,
        "decision_offset_bars": k,
    }


def _case(entry: str, mode: str, k: int, direction: str, h: int, *,
          selector: str, pending: bool) -> Dict[str, Any]:
    case_id = f"{entry}__{mode}__k{k}__{direction}__{TF}__h{h}"
    out: Dict[str, Any] = {
        "case_id": case_id,
        "file_name": f"{case_id}.json",
        "symbol": SYMBOL,
        "timeframe": TF,
        "direction": direction,
        "event_import_id": f"golden-{case_id}",
        "event_label_spec": _spec(h, entry, mode, k),
        "t0_selector": selector,
        "lookahead_bars_declared": dict(DECLARED),
        "timeframe_seconds": dict(TF_SECONDS),
    }
    if pending:
        out["matrix_pending"] = True
        out["matrix_pending_reason"] = _D0_PENDING
    return out


#: ── Phase D0（Task D4.1）────────────────────────────────────────────────────
#  ①跳空 bar（§G 必含案例 ①）：`open_to_*` 之基準價與 `close_to_close` 必不同值
#  ⑤long／short 同價格序列（§G 必含案例 ⑤）：short == −long
#  k=2（`decision_bar_open`）：證明 entry bar 之 open 取自 t₀−k
CASES: Tuple[Mapping[str, Any], ...] = (
    # 既有支援組合（無 pending）——D4.1 之 hash 於本批合法重凍一次，值不變
    _case("trigger_close", "close_to_close", 0, "long", 3, selector="plain:4", pending=False),
    _case("trigger_close", "close_to_close", 0, "short", 3, selector="plain:4", pending=False),
    _case("trigger_close", "close_to_close", 0, "long", 1, selector="gap_bars:3", pending=False),
    # 跳空 bar × open 語意（D0 之主交付）
    _case("trigger_open", "open_to_close", 0, "long", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_close", 0, "short", 1, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_horizon_close", 0, "long", 3, selector="gap_bars:3", pending=False),
    _case("trigger_open", "open_to_horizon_close", 0, "short", 3, selector="gap_bars:3", pending=False),
    _case("decision_bar_open", "open_to_horizon_close", 2, "long", 3, selector="gap_bars:3", pending=True),
    _case("decision_bar_open", "open_to_horizon_close", 2, "short", 3, selector="gap_bars:3", pending=True),
)


def resolved_cases(bars) -> List[Dict[str, Any]]:
    """把 `t0_selector` 解成 `t0_ms`，回傳 `--init` 可直接凍結之骨架清單。"""
    out = []
    for c in CASES:
        meta = {k: v for k, v in c.items() if k not in ("t0_selector", "file_name")}
        meta["t0_ms"] = list(select_t0(str(c["t0_selector"]), bars))
        out.append({"file_name": str(c["file_name"]), "meta": meta})
    return out
