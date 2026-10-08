"""整併 G1–G6 分析輸出為 build_disposition 之決策檔；並以驗證器函式預檢每個操作（定位、改寫解析、保留斷言）。
用法：PYTHONPATH=<repo> venv/bin/python merge_agents.py <agents_dir> <overrides.json|-> <out decisions.json>
overrides：{"drop": [[path, 第幾個op(0起)], ...], "replace": {"path#i": op}, "add": [op（含 path）...]}
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.feature_engineering import test_framepath_disposition as V  # noqa: E402

agents = Path(sys.argv[1])
ov = json.loads(Path(sys.argv[2]).read_text()) if sys.argv[2] != "-" else {}
out = Path(sys.argv[3])
drop = {tuple(x) for x in ov.get("drop", [])}
rep = ov.get("replace", {})
reader = V.HeadReader("6e07e0ad")
ops, problems = [], []
for g in sorted(agents.glob("G*.json")):
    data = json.loads(g.read_text())
    for f in data["files"]:
        for i, op in enumerate(f.get("ops", [])):
            if (f["path"], i) in drop:
                continue
            op = dict(rep.get(f"{f['path']}#{i}", op))
            op["path"] = f["path"]
            note = op.pop("coverage_note", None)
            if note and note.strip().lower() not in {"n/a", "na", ""}:
                op["frame_basis"] = f"{op['frame_basis']}｜承接：{note}"
            op["_src"] = f"{g.stem}:{f['path']}#{i}"
            ops.append(op)
for op in ov.get("add", []):
    op = dict(op)
    op["_src"] = "override-add"
    ops.append(op)
for op in ops:
    try:
        hb = reader.read(op["path"])
        if hb is None:
            raise ValueError("HEAD 無此檔")
        if op["kind"] in V.PY_KINDS:
            src = hb.decode()
            V.excerpt_hash_py(src, op)
            if op["kind"] == "rewrite":
                d = V.parse_rewrite_source(op["rewrite"]["new_source"])
                new_dumps = {V.ast_dump(n) for n in V.ast.walk(d) if isinstance(n, V.ast.stmt)}
                pres = V.preserved_assertion_dumps(src, [{"lineno": n} for n in op["rewrite"]["preserved_assertion_lines"]])
                for n, dump in pres:
                    if dump not in new_dumps:
                        problems.append(f"{op['_src']} 保留斷言 L{n} 不在新全文")
        elif op["kind"] == "delete-json-path":
            V.excerpt_hash_json(hb, op["pointer"])
        if not V.kind_ext_ok(op["kind"], op["path"]):
            problems.append(f"{op['_src']} 種類與副檔名不相容")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"{op['_src']} {op['kind']}: {exc}")
# 同檔 py 操作合併套用預檢
by_path = {}
for op in ops:
    by_path.setdefault(op["path"], []).append(op)
for path, lst in by_path.items():
    py = [o for o in lst if o["kind"] in V.PY_KINDS]
    if py:
        try:
            V.apply_py_ops(reader.read(path).decode(), [dict(o, id=o["_src"]) for o in py])
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{path} 合併套用失敗：{exc}")
dec = {"operations": [{k: v for k, v in o.items() if k != "_src"} for o in ops],
       "nodeid_reasons": {}, "new_files": ov.get("new_files", []), "fact_key_rows": ov.get("fact_key_rows", []),
       "collect_extra": ov.get("collect_extra", [])}
out.write_text(json.dumps(dec, ensure_ascii=False, indent=1))
print(f"ops={len(ops)} problems={len(problems)}")
print("\n".join(problems))
