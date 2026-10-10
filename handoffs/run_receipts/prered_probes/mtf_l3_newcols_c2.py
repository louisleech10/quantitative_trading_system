"""以測試原版 _l3_oracle 驗算只出現在新版之 Skew_W3 欄（判準同 _l3_exact_checks：有限值位置全等、|差| ≤ 1e-5×max(|ref|,1)）。
用法：python mtf_l3_newcols_c2.py <probe.json>"""

import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from ablation_c2 import _test_oracle  # noqa: E402

oracle = _test_oracle()
for c, d in json.load(open(sys.argv[1])).items():
    got, up = np.asarray(d["value"]), np.asarray(d["upstream"])
    want = oracle(up, 3)[:, 3]
    mask_ok = np.array_equal(np.isfinite(got), np.isfinite(want))
    both = np.isfinite(got) & np.isfinite(want)
    val_ok = bool(np.all(np.abs(got[both] - want[both]) <= 1e-5 * np.maximum(np.abs(want[both]), 1.0)))
    print(c, "finite", int(np.isfinite(got).sum()), "mask_equal", mask_ok, "values_within_1e-5", val_ok)
