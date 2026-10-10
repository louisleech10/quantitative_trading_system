"""PRE-RED：比較兩份 l1_components 輸出之逐欄差異。用法：python l1_coldiff.py <a.json> <b.json>"""

from __future__ import annotations

import json
import sys


def main(a_path: str, b_path: str) -> None:
    a = {c["name"]: c for c in json.load(open(a_path))["per_column"]}
    b = {c["name"]: c for c in json.load(open(b_path))["per_column"]}
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    common = [n for n in a if n in b]
    val_only = [n for n in common if a[n]["values"] != b[n]["values"] and a[n]["mask"] == b[n]["mask"]]
    mask_changed = [n for n in common if a[n]["mask"] != b[n]["mask"]]
    same = [n for n in common if a[n]["values"] == b[n]["values"] and a[n]["mask"] == b[n]["mask"]]
    order_a = [n for n in a if n in b]
    order_b = [n for n in b if n in a]
    print(json.dumps({
        "only_in_a": only_a, "only_in_b": only_b,
        "common": len(common), "identical": len(same),
        "values_changed_mask_same": val_only,
        "mask_changed_count": len(mask_changed),
        "mask_changed_first_valid_shift_sample": [
            (n, a[n]["first_valid"], b[n]["first_valid"]) for n in mask_changed[:15]
        ],
        "mask_changed_later_first_valid": sum(1 for n in mask_changed if b[n]["first_valid"] > a[n]["first_valid"] or b[n]["first_valid"] == -1),
        "common_order_identical": order_a == order_b,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
