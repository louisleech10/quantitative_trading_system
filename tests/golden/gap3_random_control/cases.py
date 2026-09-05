"""GAP-3 `G3-D2` D5.4 — 隨機對照抽樣 golden 之**案例登記處**。

🔴 觸發事件與 universe 邊界**不寫死 ms**：以具名 selector 從真實 bar 表導出索引，
並在導出時斷言前置條件（例如「universe 跨月」）。寫死時間戳會在 kline 增量更新後
指到別的 bar，而值仍合法 ⇒ 靜默失去覆蓋（`gap3_label` 之 `cases.py` 已為此付過代價）。

各 phase 於此**追加**案例，不改既有條目（既有條目之值已凍結）。
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Mapping, Tuple

SYMBOL = "ETHUSDT"
TF = "12h"
TFS: Tuple[str, ...] = (TF,)

#: 觸發事件之 bar index（真實網格上的固定位置；`--check` 以 selector 逐檔對證）。
_TRIGGER_IDX: Tuple[int, ...] = (200, 400, 700)
#: universe／period 之 bar index 邊界。
_UNIVERSE_LO, _UNIVERSE_HI = 100, 900
_HORIZON = 2


def _cols(bars, tf: str = TF):
    df = bars[SYMBOL][tf]
    return df["open_time_ms"].to_numpy(), df["close_time_ms"].to_numpy()


def _month(open_ms: int) -> str:
    return _dt.datetime.fromtimestamp(open_ms / 1000.0, tz=_dt.timezone.utc).strftime("%Y-%m")


def resolve_trigger_receipts(bars, tf: str = TF) -> List[Dict[str, Any]]:
    """觸發批之逐事件收據（`t0_ms`／`label_end_ms` 皆自真實網格導出）。"""
    ot, ct = _cols(bars, tf)
    return [
        {"event_id": f"{SYMBOL}:{tf}:{int(ot[i])}", "symbol": SYMBOL, "timeframe": tf,
         "t0_ms": int(ot[i]), "label_end_ms": int(ct[i + _HORIZON])}
        for i in _TRIGGER_IDX
    ]


def resolve_spec(bars, *, seed: int, tf: str = TF, n_requested: int = 40,
                 neighborhood: int = 2, embargo: int = 6,
                 threshold: float = 0.02, horizon: int = _HORIZON,
                 direction: str = "long") -> Dict[str, Any]:
    """抽樣契約之**輸入**部分（收據鍵由產生器填回）。

    🔴 導出時斷言 universe **跨月**（D-001 D5.4 邊界「universe 跨月分層」）——
    否則 `per_stratum` 只有一層，「分層」這件事在 golden 裡沒被凍到。
    """
    ot, _ = _cols(bars, tf)
    lo, hi = int(ot[_UNIVERSE_LO]), int(ot[_UNIVERSE_HI])
    months = {_month(int(t)) for t in ot if lo <= int(t) <= hi}
    if len(months) < 2:
        raise AssertionError(
            f"universe [{lo}, {hi}] 只跨 {sorted(months)} 一個月；本 golden 之覆蓋前提是跨月分層")
    return {
        "universe": {"symbol": SYMBOL, "timeframe": tf, "start_ms": lo, "end_ms": hi},
        "strata": {"symbol": SYMBOL, "timeframe": tf,
                   "period": {"start_ms": lo, "end_ms": hi}, "direction": direction},
        "allocation": "proportional_to_candidates",
        "exclusion": {"trigger_ids_digest": "", "neighborhood_bars": neighborhood,
                      "embargo_bars": embargo},
        "label_rule": {"threshold": threshold, "horizon_bars": horizon},
        "seed": seed, "n_requested": n_requested, "replacement": False,
    }


#: 登記處。`file_name` 為 `<seed>__<tf>.json`（`D-001` D5.4 字面）。
CASES: Tuple[Mapping[str, Any], ...] = (
    {"file_name": f"20260905__{TF}.json", "seed": 20260905, "scenario": "C"},
    {"file_name": f"7__{TF}.json", "seed": 7, "scenario": "C"},
)


def resolved_cases(bars) -> List[Dict[str, Any]]:
    """登記處 → 具體案例（含自真實 bar 導出之 spec 與觸發收據）。"""
    out: List[Dict[str, Any]] = []
    for c in CASES:
        out.append({
            "file_name": str(c["file_name"]),
            "meta": {
                "case_id": str(c["file_name"]).removesuffix(".json"),
                "symbol": SYMBOL,
                "timeframe": TF,
                "scenario": str(c["scenario"]),
                "seed": int(c["seed"]),
                "spec": resolve_spec(bars, seed=int(c["seed"])),
                "trigger_receipts": resolve_trigger_receipts(bars),
            },
        })
    return out
