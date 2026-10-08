"""試作：把處置表中 phase ≤ P 之操作以文字層套到 worktree 之 HEAD 版檔案，並以驗證器 ② 確認結果＝表定期望。
用法：text_apply.py <disp.json> <worktree> <P>
py：def／stmt 整段刪（含 decorator）；dict_item／seq_elem／parametrize_elem／import_alias 以欄位位移刪子字串與其逗號；
rename 改 def 名；rewrite 以新全文（依原縮排）取代。json：delete-json-path 後以 indent=2 寫回。replace-file／delete-file 照做。
FFACT_USE_CGSA 剝除另以正規化容許，不在此套用（試作測試照 HEAD 原樣留 env 設定，生產碼已不讀）。
"""
import ast
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.feature_engineering import test_framepath_disposition as V  # noqa: E402

disp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
W = Path(sys.argv[2])
P = int(sys.argv[3])
head = V.HeadReader(disp["head_commit"])


def offsets(src):
    starts, pos = [0], 0
    for line in src.splitlines(keepends=True):
        pos += len(line)
        starts.append(pos)
    return starts


def span(src, node, starts, whole_lines=False):
    if whole_lines:
        first = node.lineno
        if isinstance(node, V._DEF_TYPES) and node.decorator_list:
            first = min(d.lineno for d in node.decorator_list)
        return starts[first - 1], starts[node.end_lineno]
    return starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset


def widen_comma(src, a, b):
    # 刪序列元素：連同其後之逗號與空白；若為最後一個則連同其前之逗號
    j = b
    while j < len(src) and src[j] in " \t":
        j += 1
    if j < len(src) and src[j] == ",":
        j += 1
        while j < len(src) and src[j] in " \t":
            j += 1
        if j < len(src) and src[j] == "\n":
            k = a
            while k > 0 and src[k - 1] in " \t":
                k -= 1
            if k > 0 and src[k - 1] == "\n":
                return k, j + 1
        return a, j
    i = a
    while i > 0 and src[i - 1] in " \t\n":
        i -= 1
    if i > 0 and src[i - 1] == ",":
        return i - 1, b
    return a, b


def apply_py(src, ops):
    tree = ast.parse(src)
    starts = offsets(src)
    edits = []
    for op in ops:
        t = V.resolve_locator(tree, op["kind"], op["locator"])
        if t.action == "rename":
            node = t.node
            line = src[starts[node.lineno - 1]:starts[node.lineno]]
            idx = starts[node.lineno - 1] + line.index("def " + node.name) + 4
            edits.append((idx, idx + len(node.name), op["new_name"]))
        elif t.action == "replace":
            a, b = span(src, t.node, starts, whole_lines=True)
            indent = " " * t.node.col_offset
            new = textwrap.indent(textwrap.dedent(op["rewrite"]["new_source"]).rstrip("\n") + "\n", indent)
            edits.append((a, b, new))
        elif t.action == "remove_dict_item":
            key = t.container.keys[t.extra]
            a = starts[key.lineno - 1] + key.col_offset
            b = starts[t.node.end_lineno - 1] + t.node.end_col_offset
            a, b = widen_comma(src, a, b)
            edits.append((a, b, ""))
        elif t.action == "remove_alias":
            stmt = t.container
            if len(stmt.names) == 1:
                a, b = span(src, stmt, starts, whole_lines=True)
                edits.append((a, b, ""))
            else:
                seg = src[starts[stmt.lineno - 1]:starts[stmt.end_lineno]]
                name = t.node.name + (f" as {t.node.asname}" if t.node.asname else "")
                rel = seg.index(name)
                a = starts[stmt.lineno - 1] + rel
                a, b = widen_comma(src, a, a + len(name))
                edits.append((a, b, ""))
        else:
            node = t.node
            if isinstance(node, ast.stmt):
                a, b = span(src, node, starts, whole_lines=True)
                edits.append((a, b, ""))
            else:
                a, b = span(src, node, starts)
                a, b = widen_comma(src, a, b)
                edits.append((a, b, ""))
                if t.extra is not None:
                    a2, b2 = span(src, t.extra, starts)
                    edits.append(widen_comma(src, a2, b2) + ("",))
    for a, b, new in sorted(edits, key=lambda e: e[0], reverse=True):
        src = src[:a] + new + src[b:]
    # 刪敘述後留下之空 body ⇒ 補 pass（AST 期望側同規則）
    try:
        ast.parse(src)
    except SyntaxError as exc:
        raise SystemExit(f"套用後語法錯：{exc}")
    return src


paths = sorted({op["path"] for op in disp["operations"] if op["phase"] <= P})
bad = []
for path in paths:
    ops = [op for op in disp["operations"] if op["path"] == path and op["phase"] <= P]
    hb = head.read(path)
    dst = W / path
    if any(op["kind"] == "delete-file" for op in ops):
        if dst.exists():
            dst.unlink()
        continue
    if path.endswith(".py"):
        new = apply_py(hb.decode("utf-8"), [o for o in ops if o["kind"] in V.PY_KINDS]).encode("utf-8")
    elif path.endswith(".json"):
        doc = V.json_delete_paths(json.loads(hb), [o["pointer"] for o in ops if o["kind"] == "delete-json-path"])
        new = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    else:
        rep = [o for o in ops if o["kind"] == "replace-file"]
        new = rep[0]["new_content"].encode("utf-8") if rep else hb
    dst.write_bytes(new)
    diff = V.expected_vs_current(path, hb, new, ops)
    if diff:
        bad.append(f"{path}: {diff}")
print(f"files={len(paths)} mismatch={len(bad)}")
print("\n".join(bad))
