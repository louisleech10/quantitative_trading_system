"""FRAMEPATH Task 1.5：由主委整併之決策檔產出 `tests/_golden/framepath/test_disposition.json`。

輸入 `--decisions`（JSON）：{"operations": [...], "nodeid_reasons": {nodeid: 理由}, "new_files": [...],
"fact_key_rows": [...], "collect_extra": [...]}；每個操作：
  {"phase", "path", "kind", "frame_basis", "deleted_nodeids": [...], "renamed_nodeids": {舊: 新},
   + 種類專屬欄：locator／new_name／rewrite{reason, preserved_assertion_lines, new_source}／pointer／new_content}
本工具只做機械衍生（不做處置判斷）：
- 母體＝HEAD 6e07e0ad 中 SPEC Task 1.5 所列字面任一命中之 tests／frontend/src／scripts 檔 ＋ extra，排除 fact_keys；
- collect 檔集合＝母體與操作表 path 中位於 tests/ 之 .py；nodeid 表＝其於 HEAD 碼態之 `pytest --collect-only`
  （主工作樹之 .py 與 6e07e0ad 相同，收據記錄核對）；
- 摘錄、摘錄雜湊、保留斷言雜湊、改寫後全文雜湊、replace-file 新檔雜湊：一律呼叫驗證器同一函式；
- ignored_baseline：主工作樹以 SPEC ⑤(b) 同一命令與過濾凍結。
用法：PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/build_disposition.py --decisions <檔> --out <檔>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tests.feature_engineering import test_framepath_disposition as V  # noqa: E402

LITERALS = [
    "FFACT_USE_CGSA", "_cgsa_enabled", "_generate_multi_tf_legacy", "_legacy_native_row_maps", "load_factory_output",
    "save_factory_output", "_factory.h5", "_factory_meta.json", "_try_load_cache", "_load_hdf5_features",
    "register_hdf5_for_browse", "multi_tf_legacy_merged", "multi_tf_layers", "multi_symbol_c3", "batch2d/control",
    "hdf5_path", "hdf5_relative_path", ".h5",
]
ROOTS = ["tests", "frontend/src", "scripts"]
EXTRA = ["tests/governance/test_prered_allowed_red.py"]
EXCLUDED = ["scripts/fact_keys.json"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def population(head: str) -> list:
    cmd = ["grep", "-l", "-F"] + [x for lit in LITERALS for x in ("-e", lit)] + [head, "--", *ROOTS]
    out = subprocess.run(["git", *cmd], cwd=REPO, capture_output=True, text=True)
    files = {line.split(":", 1)[1] for line in out.stdout.splitlines() if line}
    files |= set(EXTRA)
    return sorted(files - set(EXCLUDED))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    dec = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    head = git("rev-parse", V.HEAD_SHORT).strip()
    reader = V.HeadReader(head)
    pop = population(head)

    # 核對：主工作樹 .py 與 HEAD 相同（collect 於主工作樹執行之前提）
    drift = [p for p in git("diff", "--name-only", head, "--", "*.py").split() if not p.startswith("handoffs/")]
    new_paths = {item["path"] for item in dec["new_files"]}
    drift = [p for p in drift if p not in new_paths]
    if drift:
        raise SystemExit(f"主工作樹 .py 與 HEAD 不同：{drift}")

    ops = []
    for i, d in enumerate(dec["operations"], 1):
        op = {"id": f"OP-{i:03d}", "phase": d["phase"], "path": d["path"], "kind": d["kind"],
              "excerpt_sha256": "", "excerpt": "", "frame_basis": d["frame_basis"],
              "nodeids": sorted(set(d.get("deleted_nodeids", [])) | set(d.get("renamed_nodeids", {})))}
        hb = reader.read(d["path"])
        if hb is None:
            raise SystemExit(f"{op['id']} {d['path']} 於 HEAD 不存在")
        if d["kind"] in V.PY_KINDS:
            op["locator"] = d["locator"]
            src = hb.decode("utf-8")
            if d["kind"] == "rename":
                op["new_name"] = d["new_name"]
            if d["kind"] == "rewrite":
                rw = d["rewrite"]
                new_def = V.parse_rewrite_source(rw["new_source"])
                pres = V.preserved_assertion_dumps(src, [{"lineno": n} for n in rw["preserved_assertion_lines"]])
                op["rewrite"] = {
                    "reason": rw["reason"],
                    "preserved_assertions": [{"lineno": n, "ast_sha256": V.sha256_text(dump)} for n, dump in pres],
                    "new_source": rw["new_source"],
                    "new_source_ast_sha256": V.sha256_text(V.ast_dump(new_def)),
                }
            op["excerpt"] = V.excerpt_text_py(src, op)
            op["excerpt_sha256"] = V.excerpt_hash_py(src, op)
        elif d["kind"] == "delete-json-path":
            op["pointer"] = d["pointer"]
            op["excerpt"] = V.canonical_json(V.json_resolve(json.loads(hb), d["pointer"])).decode("utf-8")
            op["excerpt_sha256"] = V.excerpt_hash_json(hb, d["pointer"])
        elif d["kind"] == "replace-file":
            op["new_content"] = d["new_content"]
            op["new_sha256"] = V.sha256_text(d["new_content"])
            op["excerpt"] = "（整檔，見 HEAD）"
            op["excerpt_sha256"] = V.sha256_bytes(hb)
        else:
            op["excerpt"] = "（整檔，見 HEAD）"
            op["excerpt_sha256"] = V.sha256_bytes(hb)
        ops.append(op)

    collect_files = sorted({p for p in set(pop) | {o["path"] for o in ops} | set(dec.get("collect_extra", []))
                            if p.startswith("tests/") and p.endswith(".py") and reader.read(p) is not None})
    head_nodeids = sorted(V.collect_nodeids(collect_files))
    by_nodeid = {}
    for op in ops:
        d = dec["operations"][int(op["id"][3:]) - 1]
        for nid in d.get("deleted_nodeids", []):
            by_nodeid[nid] = {"disposition": "delete", "op": op["id"], "phase": op["phase"]}
        for old, new in d.get("renamed_nodeids", {}).items():
            by_nodeid[old] = {"disposition": "rename", "op": op["id"], "phase": op["phase"], "new_nodeid": new}
    unknown = sorted(set(by_nodeid) - set(head_nodeids))
    if unknown:
        raise SystemExit(f"決策列之 nodeid 不在 HEAD collect：{unknown[:20]}")
    rows = []
    for nid in head_nodeids:
        if nid in by_nodeid:
            b = by_nodeid[nid]
            row = {"nodeid": nid, "phase": b["phase"], "disposition": b["disposition"], "op": b["op"]}
            if b["disposition"] == "delete":
                row["reason"] = dec["nodeid_reasons"].get(nid) or next(
                    o["frame_basis"] for o in ops if o["id"] == b["op"])
            else:
                row["new_nodeid"] = b["new_nodeid"]
            rows.append(row)
        else:
            rows.append({"nodeid": nid, "phase": 1, "disposition": "keep"})

    disp = {
        "schema": "framepath-test-disposition/1",
        "head_commit": head,
        "python": "%d.%d" % sys.version_info[:2],
        "spec": "docs/FRAMEPATH_SPEC.md v15 Task 1.5",
        "population": {"roots": ROOTS, "literals": LITERALS, "extra": EXTRA, "excluded": EXCLUDED,
                       "command": "git grep -l -F <literals> 6e07e0ad -- tests frontend/src scripts", "files": pop},
        "collect": {"command": "python -m pytest --collect-only -q -o addopts=--import-mode=importlib -p no:cacheprovider <files>",
                    "files": collect_files},
        "hash_algorithms": {
            "py": "ast.dump(node, annotate_fields=True, include_attributes=False) 之 utf-8 sha256；dict 項以 Dict(keys=[k], values=[v]) 傾印；定位一律對 HEAD 版",
            "json": "目標子樹之 json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False) utf-8 sha256",
            "file": "HEAD 整檔位元組 sha256",
            "module_compare": "兩側經 strip_ffact（SPEC Task 1.5 驗證末段 (a)–(d)）後之 ast.dump 逐字相等",
            "definition": "tests/feature_engineering/test_framepath_disposition.py",
        },
        "nodeids": rows,
        "operations": ops,
        "new_files": dec["new_files"],
        "fact_key_rows": dec["fact_key_rows"],
        "ignored_baseline": V.git_ignored(),
    }
    Path(args.out).write_text(json.dumps(disp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"population={len(pop)} collect_files={len(collect_files)} nodeids={len(rows)} ops={len(ops)} "
          f"delete={sum(r['disposition']=='delete' for r in rows)} rename={sum(r['disposition']=='rename' for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
