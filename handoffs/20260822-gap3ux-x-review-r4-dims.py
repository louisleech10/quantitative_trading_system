"""GAP-3 SPEC R4 — 六維度契約定位 receipt（可重跑）。

遞迴搜尋 `event_import_contract.json`，印出 Phase 7 六個維度的**完整 JSON 路徑**、
型別、enum、accepted 子集。不預設任何巢狀層級——路徑由資料本身導出。

用法：
    python3 handoffs/20260822-gap3ux-x-review-r4-dims.py            # 完整定義
    python3 handoffs/20260822-gap3ux-x-review-r4-dims.py --counts   # 只印元素數
"""

import json
import sys

CONTRACT = "momentum/Analysis/contracts/event_import_contract.json"
DIMS = (
    "scenario",
    "control_kind",
    "entry_price_semantic",
    "label_return_mode",
    "decision_offset_bars",
    "counterexample_kind",
)


def walk(node, path=""):
    """逐節點產出 (路徑, 值)。"""
    if isinstance(node, dict):
        for key, value in node.items():
            yield path + "/" + key, value
            yield from walk(value, path + "/" + key)
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            yield from walk(value, path + "[%d]" % idx)


def main() -> int:
    contract = json.load(open(CONTRACT, encoding="utf-8"))
    counts_only = "--counts" in sys.argv
    found = {}
    for path, value in walk(contract):
        name = path.rsplit("/", 1)[-1]
        if name in DIMS and isinstance(value, dict) and "type" in value:
            found.setdefault(name, (path, value))

    missing = [d for d in DIMS if d not in found]
    for dim in DIMS:
        if dim not in found:
            print("%-22s NOT_FOUND" % dim)
            continue
        path, value = found[dim]
        if counts_only:
            enum = value.get("enum") or []
            accepted = value.get("accepted")
            print(
                "%-22s enum_len=%d accepted_len=%s enum=%s"
                % (
                    dim,
                    len(enum),
                    "None" if accepted is None else len(accepted),
                    enum or None,
                )
            )
        else:
            print("%-22s path=%s" % (dim, path))
            print("%-22s def =%s" % ("", json.dumps(value, ensure_ascii=False)))
    if missing:
        print("MISSING:", missing)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
