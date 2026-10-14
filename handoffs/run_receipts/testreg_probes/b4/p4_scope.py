"""TESTREG Phase 4 範圍與目錄排序（唯讀）：catalog 中三欄任一含 unclassified 之條目，依 docs/manifests/*.json 之
affected_tests 列引用次數，目錄由高到低。輸出 tsv：dir、dir_refs、path、file_refs。"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

repo = Path(sys.argv[1])
cat = json.loads((repo / "tests/registry/catalog.json").read_text(encoding="utf-8"))


def uncls(e):
    return any("unclassified" in json.dumps(e.get(k)) for k in ("guarantee", "oracle", "claim", "disposition"))


scope = sorted(e["path"] for e in (cat["entries"].values() if isinstance(cat["entries"], dict) else cat["entries"]) if uncls(e))
refs = Counter()
for m in sorted((repo / "docs/manifests").glob("*.json")):
    for line in re.findall(r"affected_tests phase=\d+ ([^\"]+)", m.read_text(encoding="utf-8")):
        for p in line.split():
            if p.startswith("tests/"):
                refs[p] += 1
by_dir = defaultdict(list)
for p in scope:
    by_dir[str(Path(p).parent)].append(p)
order = sorted(by_dir, key=lambda d: (-sum(refs[p] for p in by_dir[d]), d))
out = []
for d in order:
    dr = sum(refs[p] for p in by_dir[d])
    for p in sorted(by_dir[d], key=lambda p: (-refs[p], p)):
        out.append(f"{d}\t{dr}\t{p}\t{refs[p]}")
Path(sys.argv[2]).write_text("\n".join(out) + "\n", encoding="utf-8")
print(len(scope), "files;", len(order), "dirs")
for d in order:
    print(f"{sum(refs[p] for p in by_dir[d]):4d} {len(by_dir[d]):4d}  {d}")
