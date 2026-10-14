"""TESTREG Task 4.2：E1（完全重複）立碑——收據、catalog 碑、刪除測試函式（同一提交）。

用法：venv/bin/python handoffs/run_receipts/testreg_probes/b4/tomb_e1.py <final.tsv> <disposition_ref> [--apply]
- 讀 final.tsv 之 tombstones 欄（`nodeid:E1:replacement`，逗號分隔），只處理 E1。
- 每一碑：target 於 HEAD、replacement 於工作樹算 `testreg.e1_hashes`；三雜湊須全等，否則中止（rc 1，不寫任何檔）。
- --apply：寫收據 handoffs/run_receipts/testreg-retire/<nodeid 之 / 與 :: 換 __>.json、catalog.tombstones 加碑、
  以 AST 行範圍（含裝飾器）自測試檔刪除該函式；未給 --apply 只驗不寫。
"""
import json
import re
import subprocess
import sys
from pathlib import Path
import ast

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import testreg as tr  # noqa: E402

RDIR = "handoffs/run_receipts/testreg-retire"


def tombs_from(final_tsv: Path):
    out = []
    for ln in final_tsv.read_text(encoding="utf-8").splitlines()[1:]:
        c = ln.split("\t")
        if len(c) < 7 or c[6] in ("", "-"):
            continue
        for item in c[6].split(","):
            m = re.fullmatch(r"(.+?):(E[012]):(.+)", item)
            if not m:
                raise SystemExit(f"tombstones 欄格式不合：{item}")
            nodeid, lvl, rep = m.groups()
            if lvl == "E1":
                out.append((nodeid, rep))
    return out


def func_span(src: str, name: str):
    tree = ast.parse(src)
    hits = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(hits) != 1:
        raise SystemExit(f"頂層函式 {name} 出現 {len(hits)} 次（須恰 1）")
    n = hits[0]
    start = min([n.lineno] + [d.lineno for d in n.decorator_list])
    return start, n.end_lineno


def main(argv):
    final_tsv, dref = Path(argv[0]), argv[1]
    apply = "--apply" in argv
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    rows = []
    for nodeid, rep in tombs_from(final_tsv):
        t = tr.e1_hashes(REPO, nodeid, "HEAD")
        r = tr.e1_hashes(REPO, rep, "worktree")
        if t != r:
            raise SystemExit(f"E1 不成立 {nodeid} vs {rep}：{t} != {r}")
        rows.append((nodeid, rep, t))
        print(f"OK E1 {nodeid}")
    if not apply:
        return 0
    (REPO / RDIR).mkdir(parents=True, exist_ok=True)
    cpath = REPO / "tests/registry/catalog.json"
    cat = json.loads(cpath.read_text(encoding="utf-8"))
    have = {tb["nodeid"] for tb in cat.setdefault("tombstones", [])}
    by_file = {}
    for nodeid, rep, h in rows:
        rel = f"{RDIR}/{nodeid.replace('/', '__').replace('::', '__')}.json"
        rc = {"nodeid": nodeid, "head": head, "replacement_nodeid": rep, "target_ast_sha256": h["ast"],
              "replacement_ast_sha256": h["ast"], "fixture_closure_sha256": h["fixture_closure"],
              "module_context_sha256": h["module_context"]}
        (REPO / rel).write_text(json.dumps(rc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if nodeid not in have:
            cat["tombstones"].append({"nodeid": nodeid, "evidence_level": "E1", "evidence_receipt": rel,
                                      "replaced_by": [rep], "disposition_ref": dref})
        path, fn = nodeid.split("::", 1)
        if "::" in fn:
            raise SystemExit(f"類別方法不在本腳本範圍：{nodeid}")
        by_file.setdefault(path, []).append(fn)
    cat["tombstones"].sort(key=lambda x: x["nodeid"])
    cpath.write_text(json.dumps(cat, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for path, fns in by_file.items():
        p = REPO / path
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        spans = sorted((func_span("".join(lines), f) for f in fns), reverse=True)
        for s, e in spans:
            # 連同函式後之空行一併刪除（保留兩行空行分隔由前後文自然維持）
            j = e
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            del lines[s - 1:j]
        p.write_text("".join(lines), encoding="utf-8")
        print(f"deleted {len(fns)} functions from {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
