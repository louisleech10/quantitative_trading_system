"""探針：以原始輸入欄直接計算之滾動標準差（真值）核對改前／改後之 L3 Std 欄。"""
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


def col(root: Path, name: str) -> np.ndarray:
    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet") or p.name == "timestamps.parquet":
            continue
        s = pq.read_schema(p)
        if name in s.names:
            return np.asarray(pq.read_table(p, columns=[name]).column(name).to_numpy(zero_copy_only=False), dtype=np.float64)
    raise KeyError(name)


old, new = Path(sys.argv[1]), Path(sys.argv[2])
for std_col, base_col, w in (("close_1h_trend_MIDPOINT_21_Std_W5", "close_1h_trend_MIDPOINT_21", 5),
                            ("hl_1h_trend_MIDPRICE_21_Std_W5", "hl_1h_trend_MIDPRICE_21", 5),
                            ("close_1h_trend_MIDPOINT_21_Std_W13", "close_1h_trend_MIDPOINT_21", 13)):
    a, b = col(old, std_col), col(new, std_col)
    x = col(new, base_col)
    both = np.isfinite(a) & np.isfinite(b)
    i = int(np.argmax(np.where(both, np.abs(a - b), -1)))
    window = x[i - w + 1:i + 1]
    true = float(np.std(window, ddof=1)) if np.isfinite(window).all() else float("nan")
    print(std_col, "row", i, "old", a[i], "new", b[i], "true(ddof=1, direct)", true, "window", window.tolist())
    # 全欄對真值之最大絕對誤差（兩版各自）
    xs = np.lib.stride_tricks.sliding_window_view(x, w)
    tv = np.full(len(x), np.nan)
    ok = np.isfinite(xs).all(axis=1)
    tv[w - 1:][ok] = xs[ok].std(axis=1, ddof=1)
    for label, arr in (("old", a), ("new", b)):
        m = np.isfinite(arr) & np.isfinite(tv)
        print("   ", label, "max |err| vs true", float(np.max(np.abs(arr[m] - tv[m]))), "n", int(m.sum()))
