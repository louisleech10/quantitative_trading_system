"""SPEC v17（Task 2.5–2.8）：把 G7–G9 分析輸出併入既有決策檔 decisions.json。

- 帶 `replaces: OP-NNN` 之操作取代該既有操作（OP 編號＝decisions.json operations 之 1 起序號，保持不變）；
- 其餘操作附加於尾（新 OP 編號接續）；
- 每個操作以驗證器同一函式預檢（HEAD 定位、改寫解析、保留／刪除斷言行）；任何問題 ⇒ 不寫檔、列出問題。
用法：PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/add_v17_ops.py <decisions.json> <G7.json> [<G8.json> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.feature_engineering import test_framepath_disposition as V  # noqa: E402

KEYS = ("phase", "path", "kind", "frame_basis", "deleted_nodeids", "renamed_nodeids", "locator", "new_name",
        "rewrite", "pointer", "new_content")


def normalize(path: str, op: dict) -> dict:
    out = {k: op[k] for k in KEYS if k in op}
    out["path"] = path
    note = op.get("coverage_note")
    if note and note.strip().lower() not in {"n/a", "na", ""}:
        out["frame_basis"] = f"{out['frame_basis']}｜承接：{note}"
    out.setdefault("deleted_nodeids", [])
    if out["kind"] == "rewrite":
        rw = dict(out["rewrite"])
        rw.setdefault("removed_assertion_lines", {})
        out["rewrite"] = rw
    return out


def precheck(reader: V.HeadReader, op: dict) -> str | None:
    hb = reader.read(op["path"])
    if op["kind"] in V.PY_KINDS:
        if hb is None:
            return "HEAD 無此檔"
        src = hb.decode("utf-8")
        tree = V.ast.parse(src)
        V.resolve_locator(tree, op["kind"], op["locator"])
        if op["kind"] == "rewrite":
            rw = op["rewrite"]
            V.parse_rewrite_source(rw["new_source"])
            V.preserved_assertion_dumps(src, [{"lineno": n} for n in rw["preserved_assertion_lines"]])
            V.preserved_assertion_dumps(src, [{"lineno": int(k)} for k in rw["removed_assertion_lines"]])
    elif op["kind"] in {"delete-file", "replace-file", "delete-json-path"} and hb is None:
        return "HEAD 無此檔"
    return None


def main() -> int:
    dec_path = Path(sys.argv[1])
    dec = json.loads(dec_path.read_text(encoding="utf-8"))
    reader = V.HeadReader(V.HEAD_SHORT)
    problems, n_rep, n_add = [], 0, 0
    for g in sys.argv[2:]:
        data = json.loads(Path(g).read_text(encoding="utf-8"))
        for f in data["files"]:
            for i, raw in enumerate(f.get("ops", [])):
                op = normalize(f["path"], raw)
                try:
                    why = precheck(reader, op)
                except Exception as exc:  # noqa: BLE001 — 預檢彙整所有問題
                    why = f"{type(exc).__name__}: {exc}"
                if why:
                    problems.append(f"{Path(g).stem}:{f['path']}#{i}: {why}")
                    continue
                rep = raw.get("replaces")
                if rep:
                    idx = int(rep.split("-")[1]) - 1
                    if dec["operations"][idx]["path"] != op["path"]:
                        problems.append(f"{f['path']}#{i}: replaces {rep} 之 path 不同")
                        continue
                    dec["operations"][idx] = op
                    n_rep += 1
                else:
                    dec["operations"].append(op)
                    n_add += 1
    if problems:
        print("\n".join(problems))
        return 1
    dec_path.write_text(json.dumps(dec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"replaced={n_rep} added={n_add} total_ops={len(dec['operations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
