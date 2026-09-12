#!/usr/bin/env python3
"""b9 偵察探針：現行多 feature TF 之 fail-closed 真實性與邊界。

🔴 本檔**必須留在 repo 內**：`docs/SPLITUNIFY_SPEC.D-002.md` §A 的 FACT-RECEIPT 引用它，
而 receipt 的意義在於**別人能重跑**。先前此檔只存在於 session 暫存目錄，
導致該 receipt 不可複驗（由 b9 R3 審查抓出）。

用法：`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py`

四種情形：
  A. 選定 feature TF 下每事件恰一列 ⇒ 應放行
  B. 同一 (event_id, feature_timeframe) 重複兩列 ⇒ 應 raise
  C. 同一事件同批存在多個 feature TF、但只選其中一個 ⇒ 另一個是否被**靜默丟棄**
  D. 事件只在別的 feature TF 有 cutoff ⇒ 應報「缺 cutoff」
"""
import sys

import pandas as pd

sys.path.insert(0, "/Users/louis/Desktop/quantitative_trading_system")

from momentum.Analysis.event_samples.split_projection import build_event_keys  # noqa: E402
from momentum.Analysis.event_samples.types import AlignmentReceipts  # noqa: E402

BASE = 1_700_000_000_000
H1 = 3_600_000


def _event_level(ids):
    return pd.DataFrame({
        "event_id": ids,
        "symbol": ["ETHUSDT"] * len(ids),
        "timeframe": ["1h"] * len(ids),
        "decision_at_ms": [BASE + i * H1 for i in range(len(ids))],
        "label_start_ms": [BASE + i * H1 for i in range(len(ids))],
        "label_end_ms": [BASE + (i + 1) * H1 for i in range(len(ids))],
    })


def _per_tf(rows):
    return pd.DataFrame(rows, columns=["event_id", "timeframe", "feature_cutoff_ms"])


def case(name, event_level, per_tf, selected):
    receipts = AlignmentReceipts(event_level=event_level, per_tf=per_tf)
    try:
        out = build_event_keys(receipts, selected_timeframe=selected)
    except Exception as exc:  # noqa: BLE001
        print("%-4s RAISED  %s: %s" % (name, type(exc).__name__, str(exc)[:95]))
        return "raised"
    print("%-4s NO_RAISE 產出 %d 列；event_id=%s"
          % (name, len(out), sorted(out["event_id"].tolist())))
    return "passed"


if __name__ == "__main__":
    ids = ["e1", "e2"]
    el = _event_level(ids)

    case("A", el, _per_tf([("e1", "1h", BASE), ("e2", "1h", BASE + H1)]), "1h")

    case("B", el,
         _per_tf([("e1", "1h", BASE), ("e1", "1h", BASE + H1), ("e2", "1h", BASE + H1)]),
         "1h")

    case("C", el,
         _per_tf([("e1", "1h", BASE), ("e2", "1h", BASE + H1),
                  ("e1", "4h", BASE), ("e2", "4h", BASE + H1)]),
         "1h")

    case("D", el,
         _per_tf([("e1", "1h", BASE), ("e2", "4h", BASE + H1)]),
         "1h")
