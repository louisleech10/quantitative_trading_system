"""PRE-RED Task 2.0：對 C3 之 U 欄（無 dead_reasons 之 Skew／Kurt），檢查其上游於新版之非 NaN 相異值數
是否 ≤ skip_higher_moments_max_cardinality（預設 2；rolling_aggregator._compute_low_cardinality_cols 之條件）。

用法：python c3_lowcard.py <new_prefix> <c3.json> [threshold]
"""

import json
import re
import sys
from collections import Counter

import numpy as np

new_p, c3_p = sys.argv[1:3]
th = int(sys.argv[3]) if len(sys.argv) > 3 else 2
new = np.load(new_p + ".npz")
c3 = json.load(open(c3_p))
rx = re.compile(r"^(?P<up>.+)_(Skew|Kurt)_W\d+$")
ok, bad, card = [], [], Counter()
for c in c3["U"]:
    m = rx.match(c)
    if not m or m["up"] not in new.files:
        bad.append((c, "not skew/kurt or upstream missing"))
        continue
    v = np.asarray(new[m["up"]], dtype=np.float64)
    n = len(np.unique(v[~np.isnan(v)]))
    card[n] += 1
    (ok if n <= th else bad).append((c, n))
print(json.dumps({"U_in": len(c3["U"]), "explained_low_cardinality": len(ok), "unexplained": len(bad),
                  "upstream_nunique_hist": dict(card), "unexplained_sample": bad[:8]}, ensure_ascii=False, indent=1))
