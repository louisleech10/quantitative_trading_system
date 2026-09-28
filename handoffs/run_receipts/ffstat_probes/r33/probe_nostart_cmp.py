"""探針：比對改前與改後無起始日全史輸出，逐欄於改後首個有限值之後之最大絕對差與相對差（依欄名後綴分類）。"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


def load(root: Path):
    cols = {}
    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet") or p.name == "timestamps.parquet":
            continue
        t = pq.read_table(p)
        for n in t.column_names:
            if n not in ("timestamp", "__index_level_0__", "index"):
                cols[n] = np.asarray(t.column(n).to_numpy(zero_copy_only=False), dtype=np.float64)
    return cols


old, new = load(Path(sys.argv[1])), load(Path(sys.argv[2]))
common = sorted(set(old) & set(new))
by_kind = defaultdict(lambda: {"n": 0, "differ": 0, "max_rel": 0.0, "nan_mismatch": 0})
worst = []
for c in common:
    a, b = old[c], new[c]
    if len(a) != len(b):
        print("LEN", c, len(a), len(b))
        continue
    fb = np.isfinite(b)
    if not fb.any():
        continue
    start = int(np.argmax(fb))
    a2, b2 = a[start:], b[start:]
    m = re.search(r"_(Mean|Std|Min|Max|Range|ZScore|Skew|Kurt|Rank|Slope)_W\d+$", c)
    kind = m.group(1) if m else ("L2" if re.search(r"_(Ratio|Cross)$", c) else "L1")
    k = by_kind[kind]
    k["n"] += 1
    nan_mis = int((np.isfinite(a2) != np.isfinite(b2)).sum())
    k["nan_mismatch"] += int(nan_mis > 0)
    both = np.isfinite(a2) & np.isfinite(b2)
    if both.any():
        d = np.abs(a2[both] - b2[both])
        scale = np.maximum(np.abs(a2[both]), 1e-12)
        rel = float(np.max(d / scale))
        if float(d.max()) > 0:
            k["differ"] += 1
        k["max_rel"] = max(k["max_rel"], rel)
        worst.append((rel, float(d.max()), c))
worst.sort(reverse=True)
print("COMMON", len(common), "ONLY_OLD", len(set(old) - set(new)), "ONLY_NEW", len(set(new) - set(old)))
print("BY_KIND", json.dumps(by_kind, indent=0))
print("WORST", json.dumps(worst[:12]))
