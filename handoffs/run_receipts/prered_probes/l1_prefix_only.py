"""PRE-RED：驗證 b 相對 a 之改變是否「只把每欄前段改為 NaN、其後數值逐位元組不變」。

用法：python l1_prefix_only.py <a.npz> <b.npz>
輸出：違規欄（b 有值之列與 a 不同、或 b 之 NaN 不是連續前綴擴張）之清單與計數。
"""

from __future__ import annotations

import json
import sys

import numpy as np


def main(a_path: str, b_path: str) -> None:
    a, b = np.load(a_path), np.load(b_path)
    assert sorted(a.files) == sorted(b.files)
    masked_more, violations, identical = 0, [], 0
    added_nan_total = 0
    for name in a.files:
        x, y = a[name], b[name]
        xn, yn = np.isnan(x), np.isnan(y)
        if np.array_equal(xn, yn) and np.array_equal(x[~xn].view(np.uint64), y[~yn].view(np.uint64)):
            identical += 1
            continue
        new_nan = yn & ~xn
        # 規則①：b 有值之列，a 亦有值且位元組相同
        keep = ~yn
        ok_values = (not (keep & xn).any()) and np.array_equal(x[keep].view(np.uint64), y[keep].view(np.uint64))
        # 規則②：新增 NaN 只出現在 b 首個有限值之前（連續前綴）
        fv = int(np.argmax(keep)) if keep.any() else len(y)
        ok_prefix = not new_nan[fv:].any()
        if ok_values and ok_prefix:
            masked_more += 1
            added_nan_total += int(new_nan.sum())
        else:
            violations.append({"name": name, "values_ok": bool(ok_values), "prefix_ok": bool(ok_prefix),
                               "new_nan_after_first_valid": int(new_nan[fv:].sum())})
    print(json.dumps({"columns": len(a.files), "identical": identical, "prefix_mask_only": masked_more,
                      "added_nan_total": added_nan_total, "violations": len(violations),
                      "violation_sample": violations[:20]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
