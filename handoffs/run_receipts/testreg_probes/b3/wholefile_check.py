"""查：某版 rewrite 且目標 `-`（整檔），而裁決後目標為具名子集且未涵蓋該檔全部測試函式者。
用法：python wholefile_check.py <cmp.tsv> <final.tsv> [...成對]"""
import ast
import csv
import sys
from pathlib import Path


def funcs(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    out = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
            out.add(f"{path}::{n.name}")
        elif isinstance(n, ast.ClassDef) and n.name.startswith("Test"):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test"):
                    out.add(f"{path}::{n.name}::{m.name}")
    return out


def rows(p):
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))


args = sys.argv[1:]
hits = 0
for cmp_p, fin_p in zip(args[::2], args[1::2]):
    fin = {r["path"]: r for r in rows(fin_p)}
    for r in rows(cmp_p):
        p = r["path"]
        f = fin[p]
        if f["disposition"] != "rewrite" or f["rewrite_targets"] == "-":
            continue
        whole = [k.split(".")[0] for k in r if k.endswith(".disposition") and r[k] == "rewrite"
                 and r[k.replace(".disposition", ".rewrite_targets")] == "-"]
        if not whole:
            continue
        tg = set(f["rewrite_targets"].split(","))
        allf = funcs(p)
        missing = sorted(allf - tg)
        hits += bool(missing)
        print(f"{p}\twhole-file by {','.join(whole)}\tfinal {len(tg)}/{len(allf)}\tmissing {len(missing)}")
print(f"files with whole-file intent dropped: {hits}")
