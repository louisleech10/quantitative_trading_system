"""SPLITUNIFY consult 之自我驗證：統一後多 symbol 批是否等價。

否證觀測：同一批多 symbol 事件，事件切分與「時間切分交集」給出**不同**的驗證段成員。
"""
import sys
sys.path.insert(0, ".")
import numpy as np, pandas as pd
from momentum.core.split_preview import holdout_test_row_index

H12 = 12 * 3_600_000
BASE = 1_700_000_000_000

# 兩個 symbol，時間交錯：ETH 每 12h、BTC 偏移 6h
eth = [BASE + i * H12 for i in range(40)]
btc = [BASE + i * H12 + H12 // 2 for i in range(40)]
rows = [("ETHUSDT", t) for t in eth] + [("BTCUSDT", t) for t in btc]
rows.sort(key=lambda r: r[1])
all_ms = [t for _, t in rows]

# ① 時間切分：全域 scalar，對**合併後的列序**切
n = len(all_ms)
test_rows = holdout_test_row_index(n, oos_test_size=0.2, purge_gap=2, embargo=2)
global_test = {all_ms[i] for i in test_rows}

# ② 事件切分：**每 symbol 各自**按時間切
per_symbol_test = set()
for sym in ("ETHUSDT", "BTCUSDT"):
    ms = sorted(t for s, t in rows if s == sym)
    k = len(ms)
    r = holdout_test_row_index(k, oos_test_size=0.2, purge_gap=2, embargo=2)
    per_symbol_test |= {ms[i] for i in r}

only_global = sorted(global_test - per_symbol_test)
only_per_sym = sorted(per_symbol_test - global_test)
print(f"合併列數={n}　全域切法之測試段={len(global_test)}　per-symbol 切法之測試段={len(per_symbol_test)}")
print(f"只在全域={len(only_global)}　只在 per-symbol={len(only_per_sym)}")
if only_global or only_per_sym:
    print("DISPROVED：兩種切法在多 symbol 批上**不等價** ⇒ 統一必須明確處理 per-symbol")
    print(f"  例：只在 per-symbol 的前三個 ts={only_per_sym[:3]}")
    sys.exit(1)
print("等價")
