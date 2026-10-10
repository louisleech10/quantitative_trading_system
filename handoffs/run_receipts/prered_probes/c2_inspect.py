"""PRE-RED Task 2.0：對 C2 判 U 之欄，以測試檔原版 _l3_oracle 重算並列出不符之格（新版值、原版 ref、向量化 ref）。

用法：python c2_inspect.py <new_prefix> <c2.json> [最多列數]
"""

import json
import re
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from ablation_c2 import STATS, _test_oracle, oracle_vec  # noqa: E402

new_p, c2_p = sys.argv[1:3]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 3
new = np.load(new_p + ".npz")
meta = json.load(open(new_p + ".json"))
rows = np.asarray(meta["public_rows"], dtype=np.int64)
orig = _test_oracle()
rx = re.compile(r"^(?P<up>.+)_(?P<stat>Mean|Std|ZScore|Skew|Kurt)_W(?P<w>\d+)$")
for c in json.load(open(c2_p))["U_reasons"]:
    m = rx.match(c)
    up = np.asarray(new[m["up"]], dtype=np.float64)
    k = STATS.index(m["stat"])
    w = int(m["w"])
    ro, rv = orig(up, w)[:, k], oracle_vec(up, w)[:, k]
    y = np.asarray(new[c], dtype=np.float64)
    bad = [int(i) for i in rows if np.isfinite(y[i]) and not np.isfinite(ro[i])]
    same_vec = np.array_equal(np.isfinite(ro), np.isfinite(rv))
    print(c, "orig_ref_nan_where_new_finite", len(bad), "vec==orig_mask", same_vec)
    for i in bad[:limit]:
        win = up[i - w + 1:i + 1]
        print("   row", i, "new", y[i], "orig_ref", ro[i], "vec_ref", rv[i], "window", np.round(win, 6).tolist())
