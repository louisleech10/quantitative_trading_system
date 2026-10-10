"""PRE-RED：比較兩份 full_record 輸出之逐層逐欄差異。

用法：python full_coldiff.py <a.json> <b.json> [欄名須含之樣式（regex），檢查改變欄是否全命中]
"""

from __future__ import annotations

import json
import re
import sys


def main(a_path: str, b_path: str, pattern: str | None = None) -> None:
    a, b = json.load(open(a_path)), json.load(open(b_path))
    rx = re.compile(pattern) if pattern else None
    report = {"config_hash": [a["config_hash"], b["config_hash"]],
              "feature_count": [a["feature_count"], b["feature_count"]]}
    for layer in a["per_column"]:
        ca = {n: (v, m) for n, v, m in a["per_column"][layer]}
        cb = {n: (v, m) for n, v, m in b["per_column"].get(layer, [])}
        only_a, only_b = sorted(set(ca) - set(cb)), sorted(set(cb) - set(ca))
        common = [n for n in ca if n in cb]
        val = [n for n in common if ca[n][0] != cb[n][0] and ca[n][1] == cb[n][1]]
        mask = [n for n in common if ca[n][1] != cb[n][1]]
        changed = only_a + only_b + val + mask
        entry = {"cols": [len(ca), len(cb)], "only_a": len(only_a), "only_b": len(only_b),
                 "values_only_changed": len(val), "mask_changed": len(mask),
                 "unchanged": len(common) - len(val) - len(mask),
                 "order_same": [n for n in ca if n in cb] == [n for n in cb if n in ca]}
        if rx is not None:
            miss = [n for n in changed if not rx.search(n)]
            entry["changed_not_matching_pattern"] = len(miss)
            entry["miss_sample"] = miss[:10]
        entry["only_a_sample"] = only_a[:4]
        entry["only_b_sample"] = only_b[:4]
        report[layer] = entry
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
