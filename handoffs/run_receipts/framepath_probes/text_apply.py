"""試作：把處置表中 phase ≤ P 之操作以文字層套到 worktree 之 HEAD 版檔案，並以驗證器 ② 確認結果＝表定期望。
用法：text_apply.py <disp.json> <worktree> <P>
py：def／stmt 整段刪（含 decorator）；dict_item／seq_elem／parametrize_elem／import_alias 以欄位位移刪子字串與其逗號；
rename 改 def 名；rewrite 以新全文（依原縮排）取代。json：delete-json-path 後以 indent=2 寫回。replace-file／delete-file 照做。
FFACT_USE_CGSA 剝除另以正規化容許，不在此套用（試作測試照 HEAD 原樣留 env 設定，生產碼已不讀）。
SPEC v22 D11.11(c)：處置表 `rebase` 有紀錄之檔，改以其 base_commit 之位元組套用（Python 操作之定位經驗證器
`rebase_ops` 轉成基準行號）；先過驗證器同一衝突檢查，相交即拒（不套用）。驗證亦以基準位元組＋轉換後之操作比對。
"""
import ast
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.feature_engineering import test_framepath_disposition as V  # noqa: E402


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


def source_and_ops(disp, path, ops, head, read_at=V._git_show_bytes):
    """回傳 (套用來源位元組, 對該來源之操作)：有 rebase 紀錄 ⇒ base_commit 位元組＋經 rebase_ops 轉換之操作（衝突檢查
    相交 ⇒ SystemExit）；否則錨點位元組＋原操作。"""
    ent = (disp.get("rebase") or {}).get(path)
    anchor_b = head.read(path)
    if ent is None:
        return anchor_b, ops
    base_b = read_at(ent["base_commit"], path)
    conflicts = V.rebase_conflicts(path, anchor_b, base_b, [op for op in disp["operations"] if op["path"] == path])
    if conflicts:
        raise SystemExit("重錨衝突（不套用）：\n  " + "\n  ".join(conflicts))
    if path.endswith(".py") and any(op["kind"] in V.PY_KINDS for op in ops):
        ops = V.rebase_ops(anchor_b.decode("utf-8"), base_b.decode("utf-8"), ops)
    return base_b, ops


def apply_file(disp, path, phase, head, read_at=V._git_show_bytes):
    """單檔：回傳 (新位元組〔None＝刪檔〕, 與期望之差異說明或 None)。"""
    ops = [op for op in disp["operations"] if op["path"] == path and op["phase"] <= phase]
    if any(op["kind"] == "delete-file" for op in ops):
        return None, None
    src_b, ops = source_and_ops(disp, path, ops, head, read_at)
    if path.endswith(".py"):
        new = apply_py(src_b.decode("utf-8"), [o for o in ops if o["kind"] in V.PY_KINDS]).encode("utf-8")
    elif path.endswith(".json"):
        doc = V.json_delete_paths(json.loads(src_b), [o["pointer"] for o in ops if o["kind"] == "delete-json-path"])
        new = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    else:
        rep = [o for o in ops if o["kind"] == "replace-file"]
        new = rep[0]["new_content"].encode("utf-8") if rep else src_b
    return new, V.expected_vs_current(path, src_b, new, ops)


def main() -> int:
    disp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    w = Path(sys.argv[2])
    phase = int(sys.argv[3])
    head = V.HeadReader(disp["head_commit"])
    paths = sorted({op["path"] for op in disp["operations"] if op["phase"] <= phase})
    bad = []
    for path in paths:
        new, diff = apply_file(disp, path, phase, head)
        dst = w / path
        if new is None:
            if dst.exists():
                dst.unlink()
            continue
        dst.write_bytes(new)
        if diff:
            bad.append(f"{path}: {diff}")
    print(f"files={len(paths)} mismatch={len(bad)}")
    print("\n".join(bad))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
