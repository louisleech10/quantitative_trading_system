#!/usr/bin/env python3
"""LA-1 歸因 allowlist 產生器（ICPERF SPEC v5.43 Task 0.5 (d)）。

以 `test_b4_golden_rebaseline.py`／`tests/momentum/test_la1_lookahead.py` 同一組 builder 產生 live diffs
（BTC 五路徑 recursive diff＋P1-3-obs、ETH 跨 symbol、kmeans PIT 之 xgboost_phases／regime_kmeans），
列＝(path, index, old, new, class)；old 不等於 B0 葉值即 fail。輸出依 class 之列數增減與 (path, index)
集合之新增／消失，供重錄審查。

施工狀態：空殼（Task 0.5 規格審查後實作）。
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("ICPERF Task 0.5 (d)：la1 allowlist 產生器尚未實作")


if __name__ == "__main__":
    raise SystemExit(main())
