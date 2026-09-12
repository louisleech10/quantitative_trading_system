#!/usr/bin/env python3
"""b9 研究探針二：`decision_at_ms` 與各 feature TF 之 `feature_cutoff_ms` 的實際關係。

🔴 為什麼需要這支（修正探針一的過強結論）：探針一證實 bar 採右閉（`close[i] == open[i+1]`，
實測 1695/1695），我據此說「改用 `decision_at_ms` 判側會**系統性位移一根**」。但再讀一次
`alignment.py:87-93`：

    `_select_cutoff_idx(close_ms, decision_at) = searchsorted(close_ms, decision_at, "right") - 1`
    ⇒ `cutoff = max{close ≤ decision_at}`

而 `decision_at = ot[decision_idx]`（某根之 open ＝ 前一根之 close）⇒ 在**觸發 TF** 上
`cutoff` 很可能**恰等於** `decision_at`，根本不位移；位移只會出現在**其他 feature TF**
（4h 之 close 網格較密／較疏，`max{close ≤ decision_at}` 會落在更早的時刻）。

本探針直接印出實際數值，定案 `Task 9.2b` 該用「集合成員判定」還是「區間比較」：
  · 同 TF（trigger＝feature）時 cutoff 與 decision_at 差多少
  · 跨 TF 時差多少
  · decision_at 是否落在 feature_index（該 TF 之 open 網格）集合內

用法：`venv/bin/python handoffs/20260912-splitunify-b9-probe-decision-vs-cutoff.py`
"""
import sys

import numpy as np

sys.path.insert(0, "/Users/louis/Desktop/quantitative_trading_system")

from tests.momentum.event_samples.helpers import load_bars, make_event  # noqa: E402
from momentum.Analysis.event_samples.pipeline import EventPipelineConfig, EventSamplePipeline  # noqa: E402

SYM = "ETHUSDT"
TRIGGER_TF = "12h"
H12 = 43200000
BASE = 1704067200000


def main() -> int:
    tfs = (TRIGGER_TF, "4h")
    bars = load_bars(SYM, tfs)
    records = [make_event(i, t0=BASE + n * H12, label=i % 2) for i, n in enumerate((300, 600, 900, 1200))]

    res = EventSamplePipeline().run_event_study_only(
        records, bars, EventPipelineConfig(timeframes=tfs)
    )
    ev = res.receipts.event_level
    per_tf = res.receipts.per_tf

    open_12h = set(bars[SYM][TRIGGER_TF]["open_time_ms"].to_numpy(dtype=np.int64).tolist())
    open_4h = set(bars[SYM]["4h"]["open_time_ms"].to_numpy(dtype=np.int64).tolist())

    print("事件數 =", len(ev))
    print()
    print("%-12s %-16s %-10s %-16s %-10s %-16s" %
          ("event_id", "decision_at", "in12hOpen", "cutoff_12h", "delta_12h", "cutoff_4h"))
    for _, row in ev.iterrows():
        eid = row["event_id"]
        dec = int(row["decision_at_ms"])
        sub = per_tf[per_tf["event_id"] == eid]
        c12 = sub[sub["timeframe"] == TRIGGER_TF]["feature_cutoff_ms"]
        c4 = sub[sub["timeframe"] == "4h"]["feature_cutoff_ms"]
        c12v = int(c12.iloc[0]) if len(c12) else -1
        c4v = int(c4.iloc[0]) if len(c4) else -1
        print("%-12s %-16d %-10s %-16d %-10d %-16d" %
              (str(eid)[:12], dec, dec in open_12h, c12v, dec - c12v, c4v))

    print()
    print("decision_at 落在 12h open 網格的比例 = %d/%d" %
          (sum(1 for d in ev["decision_at_ms"] if int(d) in open_12h), len(ev)))
    print("decision_at 落在 4h  open 網格的比例 = %d/%d" %
          (sum(1 for d in ev["decision_at_ms"] if int(d) in open_4h), len(ev)))
    print()
    print("判定：")
    print("  · delta_12h 全為 0 ⇒ 觸發 TF 上 decision_at == cutoff，Task 9.2b 不位移；")
    print("    差異只出現在其他 feature TF（看 cutoff_4h），那正是本票要統一的對象。")
    print("  · decision_at 全在 12h open 網格 ⇒ 對以 12h 為 feature_index 之投影，")
    print("    集合成員判定可直接沿用；否則 Task 9.2b 須改為區間比較。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
