#!/usr/bin/env python3
"""governance_families_loader.py — 治理家族 SoT 的 python 讀取(與 governance_families.sh 讀同檔同 key)。

scripts 非 package(無 __init__.py),故以 __file__ 相對定位 JSON;禁 `import scripts`。
fail-closed: 檔缺/JSON 壞/key 缺或非非空 list → raise(caller 不得放行)。
"""
from __future__ import annotations

import json
import os
import sys

_JSON = os.path.join(os.path.dirname(os.path.realpath(__file__)), "governance_families.json")


def load(key: str) -> list[str]:
    with open(_JSON, encoding="utf-8") as fh:
        d = json.load(fh)
    v = d.get(key)
    if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v):
        raise ValueError(f"governance_families: key 缺/非非空字串list: {key}")
    return list(v)


def load_upper(key: str) -> list[str]:
    return [x.upper() for x in load(key)]


if __name__ == "__main__":
    # CLI: python3 governance_families_loader.py <key> [sep]  → 印出 sep 連接
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    sep = sys.argv[2] if len(sys.argv) > 2 else ","
    try:
        print(sep.join(load(key)))
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"{e}\n")
        sys.exit(1)
