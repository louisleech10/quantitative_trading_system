"""TESTREG Task 4.2：以既成收據立碑（E2 等）——catalog.tombstones 加碑並刪除該頂層測試函式（同一提交）。

用法：venv/bin/python handoffs/run_receipts/testreg_probes/b4/tomb_add.py <nodeid> <E0|E1|E2> <receipt> <disposition_ref> [replaced_by …]
"""
import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def main(argv):
    nodeid, lvl, rcpt, dref, *rb = argv
    if not (REPO / rcpt).is_file():
        raise SystemExit(f"收據不存在：{rcpt}")
    path, fn = nodeid.split("::", 1)
    if "::" in fn:
        raise SystemExit(f"類別方法不在本腳本範圍：{nodeid}")
    p = REPO / path
    src = p.read_text(encoding="utf-8")
    hits = [n for n in ast.parse(src).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn]
    if len(hits) != 1:
        raise SystemExit(f"頂層函式 {fn} 出現 {len(hits)} 次（須恰 1）")
    n = hits[0]
    s, e = min([n.lineno] + [d.lineno for d in n.decorator_list]), n.end_lineno
    lines = src.splitlines(keepends=True)
    j = e
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    del lines[s - 1:j]
    cpath = REPO / "tests/registry/catalog.json"
    cat = json.loads(cpath.read_text(encoding="utf-8"))
    tombs = cat.setdefault("tombstones", [])
    if any(t["nodeid"] == nodeid for t in tombs):
        raise SystemExit(f"碑已存在：{nodeid}")
    tombs.append({"nodeid": nodeid, "evidence_level": lvl, "evidence_receipt": rcpt, "replaced_by": rb,
                  "disposition_ref": dref})
    tombs.sort(key=lambda x: x["nodeid"])
    cpath.write_text(json.dumps(cat, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    p.write_text("".join(lines), encoding="utf-8")
    print(f"tombstoned {nodeid} ({lvl})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
