#!/usr/bin/env python3
"""b9 R11 探針：複驗 `GROK-R11-P1-03`「M5 座標二擇一不窮盡」之四案真值表。

🔴 為什麼需要這支：grok 在 R11 交件中自陳實跑四案結果。依本專案之驗證保真度鐵律，
主委採納該結論前**須自行複跑**，不得只引用委員交件（同 R10 對 composer 探針之處置）。

四案（交錯批：全域 symbols = [A, B, A, B]，symbol A 之全域位置 = 0, 2）：
  case1 全域 row_index ＋ 全域宇宙（4 列）
  case2 全域 row_index ＋ 局部宇宙（2 列）   ← codex R10 的 IndexError 反例
  case3 局部 row_index ＋ 局部宇宙（2 列）   ← grok 稱 PASS；若成立則二擇一不窮盡
  case4 局部 row_index ＋ 全域宇宙（4 列）

判定：若 case3 PASS，則 SPEC `Task 9.2b` 步驟 0③ 現寫的二擇一
（(a) 傳 full-universe `row_index`／(b) local→global rebase adapter）**漏了第三條可行路徑**，
且未要求 `ts`／`symbols` 與 `row_index` 同一座標系。

用法：`venv/bin/python handoffs/20260912-splitunify-b9-probe-m5-coords.py`
"""

import numpy as np
import pandas as pd

from momentum.core.contracts import SplitPlan, validate_split_pair_integrity

TS_GLOBAL = pd.to_datetime(
    ["2026-01-01 00:00", "2026-01-01 01:00", "2026-01-01 02:00", "2026-01-01 03:00"]
)
SYM_GLOBAL = np.array(["A", "B", "A", "B"], dtype=object)

# 局部宇宙＝只留 symbol A 的兩列（全域位置 0 與 2）
TS_LOCAL = TS_GLOBAL[[0, 2]]
SYM_LOCAL = np.array(["A", "A"], dtype=object)

BASE_HASH = "probe-m5-base-universe"


def _plan(label, rows, ts_for_bounds):
    """建一個 symbol A 的 SplitPlan；time_bounds 取該 plan 自己的列範圍。"""
    idx = np.asarray(rows, dtype=int)
    return SplitPlan(
        split_label=label,
        index_kind="positional",
        row_index=idx,
        time_bounds=(ts_for_bounds[0], ts_for_bounds[-1]),
        purge_gap=0,
        embargo=0,
        purge_semantic="timedelta",
        base_universe_hash=BASE_HASH,
        symbol="A",
    )


def run_case(name, train_rows, test_rows, ts, symbols, train_bounds, test_bounds):
    try:
        train = _plan("train", train_rows, train_bounds)
        test = _plan("test", test_rows, test_bounds)
    except Exception as exc:  # 建構期就擋下也算結果
        print("%-38s 建構失敗 %s: %s" % (name, type(exc).__name__, exc))
        return type(exc).__name__

    try:
        validate_split_pair_integrity(train, test, ts, symbols)
    except Exception as exc:
        print("%-38s %s: %s" % (name, type(exc).__name__, str(exc)[:90]))
        return type(exc).__name__
    print("%-38s PASS" % name)
    return "PASS"


if __name__ == "__main__":
    print("=== M5 座標四案（train=A 第一列, test=A 第二列）===")
    r1 = run_case(
        "case1 全域索引 + 全域宇宙",
        [0], [2], TS_GLOBAL, SYM_GLOBAL, TS_GLOBAL[[0]], TS_GLOBAL[[2]],
    )
    r2 = run_case(
        "case2 全域索引 + 局部宇宙",
        [0], [2], TS_LOCAL, SYM_LOCAL, TS_GLOBAL[[0]], TS_GLOBAL[[2]],
    )
    r3 = run_case(
        "case3 局部索引 + 局部宇宙",
        [0], [1], TS_LOCAL, SYM_LOCAL, TS_LOCAL[[0]], TS_LOCAL[[1]],
    )
    r4 = run_case(
        "case4 局部索引 + 全域宇宙",
        [0], [1], TS_GLOBAL, SYM_GLOBAL, TS_LOCAL[[0]], TS_LOCAL[[1]],
    )

    print()
    print("判定：")
    print("  case3（局部索引+局部宇宙）＝%s" % r3)
    if r3 == "PASS":
        print("  ⇒ grok `GROK-R11-P1-03` **成立**：二擇一漏了第三條可行路徑；")
        print("    `Task 9.2b` 步驟 0③ 須改為『row_index 與 ts/symbols 同一座標系』三選一並禁混用。")
    else:
        print("  ⇒ 與 grok 所述不符，須逐案檢視（勿直接採納其結論）。")
    print("  四案結果：case1=%s case2=%s case3=%s case4=%s" % (r1, r2, r3, r4))
