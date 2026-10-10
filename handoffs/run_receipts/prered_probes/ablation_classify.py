"""PRE-RED Task 2.0：比較新版與舊版消融之全 ingest 窗值，逐欄分類（SPEC v4）。

用法：python ablation_classify.py <new_prefix> <old_prefix> <out.json>
前置：兩版 meta 之 ingest_ts 逐元素相等、public_rows 相等，否則拋錯。
類別（本檔只做機械比對；C2 由 ablation_c2.py 以獨立 reference 判定後回填）：
  C1-full    全 ingest 窗：新版有限之格消融值逐位元組相同，新版多出之 NaN 只在其首個有限值之前
  C1-public  只公開窗成立 C1（全窗不成立）
  D          其餘共同欄（待 C2 判定；未判定者計入 U）
  only_new／only_old  單側欄（C3 候選，待附剔除原因）
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter

import numpy as np


def _op(name: str) -> str:
    toks = name.split("_")
    tail = [t for t in toks[2:] if not re.fullmatch(r"W?\d+([.-]\d+)*", t)]
    return "_".join(tail[-2:]) if len(tail) >= 2 else ("_".join(tail) or name)


def _c1(x: np.ndarray, y: np.ndarray) -> bool:
    fin = ~np.isnan(y)
    if np.isnan(x[fin]).any() or not np.array_equal(x[fin], y[fin]):
        return False
    fv = int(np.argmax(fin)) if fin.any() else len(y)
    extra = np.isnan(y) & ~np.isnan(x)
    return not extra[fv:].any()


def main(new_p: str, old_p: str, out: str) -> None:
    new, old = np.load(new_p + ".npz"), np.load(old_p + ".npz")
    nm, om = json.load(open(new_p + ".json")), json.load(open(old_p + ".json"))
    if nm["ingest_ts"] != om["ingest_ts"]:
        raise RuntimeError("兩版 ingest 時間戳不等")
    if nm["public_rows"] != om["public_rows"]:
        raise RuntimeError("兩版公開列位置不等")
    rows = np.asarray(nm["public_rows"], dtype=np.int64)
    layer_of = {c: layer for layer, cols in nm["layer_cols"].items() for c in cols}
    for layer, cols in om["layer_cols"].items():
        for c in cols:
            layer_of.setdefault(c, layer)
    names_new, names_old = set(new.files), set(old.files)
    res = {"C1-full": [], "C1-public": [], "D": [],
           "only_new": sorted(names_new - names_old), "only_old": sorted(names_old - names_new)}
    detail = {}
    for c in sorted(names_new & names_old):
        y = np.asarray(new[c], dtype=np.float64)
        x = np.asarray(old[c], dtype=np.float64)
        if _c1(x, y):
            res["C1-full"].append(c)
        elif _c1(x[rows], y[rows]):
            res["C1-public"].append(c)
        else:
            yp, xp = y[rows], x[rows]
            both = ~np.isnan(yp) & ~np.isnan(xp)
            rel = float(np.max(np.abs(xp[both] - yp[both]) / np.maximum(np.abs(yp[both]), 1e-12))) if both.any() else None
            res["D"].append(c)
            detail[c] = {"layer": layer_of.get(c), "op": _op(c), "max_rel_public": rel}
    summary = {k: len(v) for k, v in res.items()}
    summary["U_before_C2"] = summary["D"]
    report = {"summary": summary,
              "by_layer": {k: dict(Counter(layer_of.get(c) for c in v)) for k, v in res.items()},
              "D_by_op": dict(Counter(d["op"] for d in detail.values()).most_common()),
              "classes": res, "D_detail": detail}
    json.dump(report, open(out, "w"), ensure_ascii=False)
    print(json.dumps({"summary": summary, "by_layer": report["by_layer"],
                      "D_by_op_top": dict(Counter(d["op"] for d in detail.values()).most_common(30))},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
