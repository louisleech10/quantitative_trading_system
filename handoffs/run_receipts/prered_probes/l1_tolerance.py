"""PRE-RED：新版（預熱）與舊版（冷啟動）L1 之相對差，按輸出窗位置分段。

用法：python l1_tolerance.py <old.npz> <new.npz>
新版 registry 含預熱列 ⇒ 輸出窗＝新版末 len(old) 列（rows 對齊之前提另以時間軸驗）。
只比兩邊皆有限之格；相對差＝|old−new| / max(|new|, 欄內 new 有限值絕對值中位數, 1e-12)。
分段：輸出窗前 1/4、中 1/2、末 1/4；逐欄取該段最大相對差，報各段分位數與 > 0.005 之欄數。
"""

from __future__ import annotations

import json
import sys

import numpy as np


def main(old_path: str, new_path: str) -> None:
    old, new = np.load(old_path), np.load(new_path)
    n = None
    seg_max: dict[str, list[float]] = {"first_quarter": [], "middle_half": [], "last_quarter": []}
    worst: dict[str, list[tuple[str, float]]] = {k: [] for k in seg_max}
    for name in new.files:
        if name not in old.files:
            continue
        x = old[name]
        y = new[name][-len(x):]
        n = len(x)
        both = ~np.isnan(x) & ~np.isnan(y)
        if not both.any():
            continue
        fin = y[~np.isnan(y)]
        scale = max(float(np.median(np.abs(fin))), 1e-12)
        rel = np.where(both, np.abs(x - y) / np.maximum(np.abs(y), scale), np.nan)
        bounds = {"first_quarter": (0, n // 4), "middle_half": (n // 4, 3 * n // 4), "last_quarter": (3 * n // 4, n)}
        for seg, (lo, hi) in bounds.items():
            part = rel[lo:hi]
            if np.isfinite(part).any():
                m = float(np.nanmax(part))
                seg_max[seg].append(m)
                worst[seg].append((name, m))
    out = {"rows": n}
    for seg, vals in seg_max.items():
        arr = np.array(vals)
        w = sorted(worst[seg], key=lambda r: -r[1])
        out[seg] = {"columns": len(vals), "p50_p90_p99_max": np.quantile(arr, [0.5, 0.9, 0.99, 1.0]).tolist(),
                    "over_0.005": int((arr > 0.005).sum()), "worst": w[:12]}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
