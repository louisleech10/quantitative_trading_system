"""TESTREG Task 3.1：依分類輪裁決表（G*_final.tsv）寫入 catalog 委員欄，或核對 catalog 與裁決表逐檔相等。

用法：
  python write_catalog.py write  <catalog.json> <G1_final.tsv>=<synth.md> [...]
  python write_catalog.py verify <catalog.json> <G1_final.tsv>=<synth.md> [...]

寫入欄位：guarantee、oracle、claim（逗號分隔 ⇒ 陣列，保留裁決表順序）、disposition、rewrite_targets（`-` ⇒ []）、
disposition_ref（＝該組收斂檔路徑）。其餘欄位不動；tombstones 欄不寫（碑於 Task 3.2 隨刪除同提交立）。
fail-closed：表頭不符、路徑不在 catalog、同一路徑出現於兩組、值為空或含 unclassified ⇒ rc 1。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

HEADER = ["path", "guarantee", "oracle", "claim", "disposition", "rewrite_targets", "tombstones", "basis"]
LIST_FIELDS = ("guarantee", "oracle", "claim")


def _rows(tsv: Path) -> List[Dict[str, str]]:
    with tsv.open(encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        head = next(rd, None)
        if head != HEADER:
            raise SystemExit(f"{tsv}: 表頭不符 {head}")
        out = []
        for i, row in enumerate(rd, start=2):
            if len(row) != len(HEADER):
                raise SystemExit(f"{tsv}:{i}: 欄數 {len(row)} ≠ {len(HEADER)}")
            out.append(dict(zip(HEADER, row)))
        return out


def _expected(pairs: List[str]) -> Dict[str, Dict[str, object]]:
    exp: Dict[str, Dict[str, object]] = {}
    for pair in pairs:
        tsv, _, synth = pair.partition("=")
        if not synth or not Path(synth).is_file():
            raise SystemExit(f"收斂檔不存在：{pair}")
        for r in _rows(Path(tsv)):
            p = r["path"]
            if p in exp:
                raise SystemExit(f"{p} 出現於兩組")
            v: Dict[str, object] = {}
            for f in LIST_FIELDS:
                items = [x for x in r[f].split(",") if x]
                if not items or "unclassified" in items:
                    raise SystemExit(f"{p}: {f} 為空或含 unclassified")
                v[f] = items
            if r["disposition"] not in ("keep", "rewrite"):
                raise SystemExit(f"{p}: disposition {r['disposition']!r}")
            # 分類規則：rewrite 之 `-` ＝整檔（契約 rewrite_targets 空＝整檔）；keep 一律 `-`
            tg = [] if r["rewrite_targets"] == "-" else r["rewrite_targets"].split(",")
            if r["disposition"] == "keep" and tg:
                raise SystemExit(f"{p}: keep 而有改寫目標")
            v["disposition"], v["rewrite_targets"], v["disposition_ref"] = r["disposition"], tg, synth
            exp[p] = v
    return exp


def main(argv: List[str]) -> int:
    if len(argv) < 3 or argv[0] not in ("write", "verify"):
        print(__doc__, file=sys.stderr)
        return 2
    mode, cat_path, pairs = argv[0], Path(argv[1]), argv[2:]
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    exp = _expected(pairs)
    missing = sorted(p for p in exp if p not in cat["entries"])
    if missing:
        print("不在 catalog：" + ", ".join(missing), file=sys.stderr)
        return 1
    if mode == "write":
        for p, v in exp.items():
            cat["entries"][p].update(v)
        cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {len(exp)} entries")
        return 0
    bad: List[Tuple[str, str]] = []
    for p, v in exp.items():
        for k, want in v.items():
            if cat["entries"][p].get(k) != want:
                bad.append((p, k))
    for p, k in bad:
        print(f"MISMATCH {p} {k}", file=sys.stderr)
    print(f"verified {len(exp)} entries, mismatches {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
