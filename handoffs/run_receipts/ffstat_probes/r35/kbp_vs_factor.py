"""倍數表：k_by_params（逐實例單點量測）與 ceil(max(period_keys 值) × recommended_factor) 之比較。"""
import math
import re

import yaml

t = yaml.safe_load(open("/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/atomic/warmup_table.yaml"))
rows, below = 0, []
for name, e in t["indicators"].items():
    f = e.get("recommended_factor")
    kbp = e.get("k_by_params") or {}
    if not f or not kbp:
        continue
    for params, k in kbp.items():
        vals = [float(v) for v in re.findall(r"=([0-9.]+)", params)]
        keys = re.findall(r"([A-Za-z_]+)=", params)
        pk = e.get("period_keys") or []
        pv = [float(v) for kk, v in zip(keys, vals) if kk in pk] or vals
        if not pv:
            continue
        kf = math.ceil(max(pv) * float(f))
        rows += 1
        if int(k) < kf:
            below.append((name, params, int(k), kf, round(kf / max(int(k), 1), 2)))
print("instances", rows, "k_by_params < factor-K", len(below))
for b in sorted(below, key=lambda x: -x[4])[:25]:
    print(" ", b)
