#!/usr/bin/env python3
"""b9 研究探針：`feature_cutoff_ms`（bar close）與 `feature_index`（bar open）是否同刻度。

🔴 為什麼需要這支：`docs/SPLITUNIFY_SPEC.D-002.md` 之 `Task 9.2b` 要把側別判定由
`feature_cutoff_ms in train_ms` 改為以事件級 `decision_at_ms` 判定。但讀碼顯示三件事：

  · `alignment.py:206` `cutoff = int(sub_ct[idx])`，`sub_ct` 為 **close_time_ms** ⇒ cutoff 是 bar **close**
  · `alignment.py:157` `decision_at = int(ot[decision_idx])`，`ot` 為 **open_time_ms** ⇒ decision_at 是 bar **open**
  · `tests/momentum/event_samples/test_splitunify_wiring.py` 之 `_canonical()` 用 **open_time_ms**
    當 `feature_index`，而其斷言 `cut in train_ms` **通過**

若 cutoff（close）真的落在 open 刻度集合裡，代表該資料的 close 與**下一根**的 open 相等
（區間右開慣例）⇒ 現行判側其實是「以下一根 bar 的位置」定側，換成 decision_at（本根 open）
會**系統性位移一根**。若不相等，則 wiring 測試的通過另有原因，須再查。

讀碼到此無法再推進，只能實測。用法：
  `venv/bin/python handoffs/20260912-splitunify-b9-probe-clock-alignment.py`
"""
import sys

import numpy as np

sys.path.insert(0, "/Users/louis/Desktop/quantitative_trading_system")

from tests.momentum.event_samples.helpers import load_bars  # noqa: E402

SYM = "ETHUSDT"
TF = "12h"


def main() -> int:
    bars = load_bars(SYM, (TF,))
    df = bars[SYM][TF]
    ot = df["open_time_ms"].to_numpy(dtype=np.int64)
    ct = df["close_time_ms"].to_numpy(dtype=np.int64)

    print("bars n=%d" % len(df))
    print("open[0:3]  =", ot[:3].tolist())
    print("close[0:3] =", ct[:3].tolist())
    print("close[i] - open[i]      =", int(ct[0] - ot[0]))
    print("open[i+1] - close[i]    =", int(ot[1] - ct[0]))

    open_set = set(ot.tolist())
    hits = sum(1 for c in ct[:200].tolist() if c in open_set)
    print("close 落在 open 集合的比例（前 200 根）= %d/200" % hits)

    # 若 close == 下一根 open，則 close 命中 open 集合，且對應的是**後一根**
    shifted = int(np.sum(ct[:-1] == ot[1:]))
    print("close[i] == open[i+1] 的根數 = %d / %d" % (shifted, len(ct) - 1))

    print()
    print("判定：")
    if hits == 200 and shifted == len(ct) - 1:
        print("  ⇒ cutoff（close）恆等於下一根 open ⇒ 現行判側實際以**下一根**之位置定側；")
        print("    改用 decision_at（本根 open）會系統性位移一根，Task 9.2b 須明寫此位移之處置。")
    elif hits == 0:
        print("  ⇒ close 完全不在 open 集合 ⇒ wiring 測試之通過另有原因（須再查其 fixture）。")
    else:
        print("  ⇒ 部分命中（hits=%d, shifted=%d）——資料本身不連續，兩種刻度混用風險更高。" % (hits, shifted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
