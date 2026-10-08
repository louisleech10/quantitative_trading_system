"""把 tests/_golden/framepath/test_disposition.json 轉成供審查逐項閱讀之 Markdown（衍生物；以 JSON sha256 綁定，JSON 為唯一權威）。
用法：PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/render_disposition.py <out.md>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "tests/_golden/framepath/test_disposition.json"


def main() -> int:
    raw = SRC.read_bytes()
    disp = json.loads(raw)
    rows = disp["nodeids"]
    by_op = {}
    for r in rows:
        if r["disposition"] != "keep":
            by_op.setdefault(r["op"], []).append(r)
    out = [
        "# FRAMEPATH 處置表審查視圖（衍生物，權威＝JSON）",
        "",
        f"- 來源：`tests/_golden/framepath/test_disposition.json` sha256 `{hashlib.sha256(raw).hexdigest()}`",
        f"- HEAD：`{disp['head_commit']}`；母體 {len(disp['population']['files'])} 檔；collect 檔 {len(disp['collect']['files'])}；"
        f"nodeid {len(rows)}（keep {sum(r['disposition'] == 'keep' for r in rows)}、delete {sum(r['disposition'] == 'delete' for r in rows)}、"
        f"rename {sum(r['disposition'] == 'rename' for r in rows)}）；操作 {len(disp['operations'])}",
        "- 每列附 HEAD 摘錄；rewrite 附改寫後全文與須保留之 HEAD 斷言行號；replace-file 附新檔全文。",
        "",
    ]
    for phase in (1, 2, 3):
        out += [f"## Phase {phase}", ""]
        for op in [o for o in disp["operations"] if o["phase"] == phase]:
            loc = op.get("locator") or {}
            target = loc.get("qualname") or loc.get("target") or op.get("pointer") or ""
            out += [f"### {op['id']} `{op['kind']}` `{op['path']}` {('`' + str(target) + '`') if target else ''}".rstrip(), ""]
            if loc:
                out += [f"- locator：`{json.dumps(loc, ensure_ascii=False)}`"]
            out += [f"- frame 依據：{op['frame_basis']}"]
            for r in by_op.get(op["id"], []):
                extra = f" → `{r['new_nodeid']}`" if r["disposition"] == "rename" else ""
                out += [f"- nodeid {r['disposition']}：`{r['nodeid']}`{extra}"]
            if op["kind"] == "rewrite":
                rw = op["rewrite"]
                out += [f"- 改寫理由：{rw['reason']}",
                        f"- 須保留之 HEAD 斷言行：{[p['lineno'] for p in rw['preserved_assertions']]}", "",
                        "改寫後全文：", "", "```python", rw["new_source"].rstrip("\n"), "```", ""]
            if op["kind"] == "replace-file":
                out += ["", "新檔全文：", "", "```", op["new_content"].rstrip("\n"), "```", ""]
            if op["kind"] not in ("delete-file", "replace-file"):
                fence = "json" if op["kind"] == "delete-json-path" else "python"
                out += ["", "HEAD 摘錄：", "", f"```{fence}", op["excerpt"].rstrip("\n"), "```", ""]
            out.append("")
    out += ["## new_files", ""] + [f"- `{n['path']}`（phase {n['phase']}，Task {n['task']}）" for n in disp["new_files"]]
    out += ["", "## fact_key_rows", ""] + [f"- `{n['row_id']}`（phase {n['phase']}）" for n in disp["fact_key_rows"]]
    out += ["", "## ignored_baseline", ""] + [f"- `{p}`" for p in disp["ignored_baseline"]]
    Path(sys.argv[1]).write_text("\n".join(out) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
