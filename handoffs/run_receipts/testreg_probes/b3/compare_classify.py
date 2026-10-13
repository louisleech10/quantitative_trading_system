"""TESTREG b3 Task 3.1：逐檔比對主委與三家之分類機讀表（唯讀；不寫 catalog）。fail-closed。

每份交件檔內以 fenced block 標記 ```testreg-classify 開頭、``` 結尾；表頭固定為
path, guarantee, oracle, claim, disposition, rewrite_targets, tombstones, evidence, note（tab 分隔）。
多值欄以半形逗號分隔；空值寫 `-`。tombstones 每項 `nodeid:等級:replaced_by1|replaced_by2`（無 replaced_by 寫 `-`）。

用法：venv/bin/python compare_classify.py <scope.txt> <out.tsv> <名稱=交件檔> [<名稱=交件檔> ...]
驗證（任一違反 ⇒ 列出全部錯誤、不寫 out.tsv、rc 1；諮詢 r3 CODEX-R3-P1-04）：
- 每份表：恰一個 testreg-classify 表、表頭逐字、每列 9 欄、path 不重複、path 集合＝範圍（不缺不多）；
- guarantee／oracle／claim 每值 ∈ 契約 enums（不得含 unclassified）、至少一值；disposition ∈ file_disposition；
- rewrite_targets：disposition=keep ⇒ 須為 `-`；每項為函式層 nodeid（`path::[Class::]func`、不含參數化後綴），
  其 path＝該列 path，且函式（或類別方法）於該檔 AST 存在；
- tombstones：每項 `nodeid:E0|E1|E2:replaced_by…`，nodeid 同上規則；replaced_by 各項為函式層 nodeid 形；
- evidence：至少一項，每項 `repo 相對路徑:行號`，檔存在且行號在 1..行數內；
- note：非空（無則 `-`），不得含 tab（以欄數檢查涵蓋）。
輸出：每檔一列——各比較欄是否一致（agree_<欄>）與各家之值；stdout 印彙總計數。
比較欄：guarantee、oracle、claim、rewrite_targets、tombstones（集合）、disposition。
"""
import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
HEAD = ["path", "guarantee", "oracle", "claim", "disposition", "rewrite_targets", "tombstones", "evidence", "note"]
SET_COLS = {"guarantee", "oracle", "claim", "rewrite_targets", "tombstones"}
CMP_COLS = ["guarantee", "oracle", "claim", "disposition", "rewrite_targets", "tombstones"]
FENCE_OPEN = re.compile(r"^```testreg-classify\s*$")
NODEID = re.compile(r"^(tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+\.py)::((?:[A-Za-z_][A-Za-z0-9_]*::)?[A-Za-z_][A-Za-z0-9_]*)$")
EVIDENCE = re.compile(r"^([A-Za-z0-9_./-]+):([0-9]+)(?:-([0-9]+))?$")


def load_enums() -> dict:
    schema = json.loads((REPO / "tests/registry/testreg_schema.json").read_text(encoding="utf-8"))
    e = schema["enums"]
    return {
        "guarantee": set(e["charter_category"]) - {"unclassified"},
        "oracle": set(e["oracle"]) - {"unclassified"},
        "claim": set(e["claim"]) - {"unclassified"},
        "disposition": set(e["file_disposition"]),
        "level": set(e["retire_evidence_level"]),
    }


_DEFS: dict = {}


def defined_names(path: str) -> set:
    """檔內可作 nodeid 之函式層名：模組層函式、類別內函式（Class::func）。"""
    if path not in _DEFS:
        p = REPO / path
        names: set = set()
        if p.is_file():
            tree = ast.parse(p.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    for sub in node.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            names.add(f"{node.name}::{sub.name}")
        _DEFS[path] = names
    return _DEFS[path]


def parse(path: Path, errs: list) -> dict:
    rows, inside, header_seen, tables = {}, False, False, 0
    for lineno, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not inside:
            if FENCE_OPEN.match(ln):
                inside, tables = True, tables + 1
            continue
        if ln.strip() == "```":
            inside = False
            continue
        if not ln.strip():
            continue
        cells = ln.split("\t")
        if not header_seen:
            if cells != HEAD:
                errs.append(f"{path}:{lineno}: 表頭不符 {cells[:9]}")
            header_seen = True
            continue
        if len(cells) != len(HEAD):
            errs.append(f"{path}:{lineno}: 欄數 {len(cells)} ≠ 9")
            continue
        rec = dict(zip(HEAD, cells))
        if rec["path"] in rows:
            errs.append(f"{path}:{lineno}: 重複列 {rec['path']}")
            continue
        rec["_line"] = lineno
        rows[rec["path"]] = rec
    if tables != 1:
        errs.append(f"{path}: testreg-classify 表數 {tables} ≠ 1")
    if inside:
        errs.append(f"{path}: fenced 表未關閉")
    return rows


def split_vals(v: str) -> list:
    v = v.strip()
    return [] if v in ("", "-") else [x.strip() for x in v.split(",")]


def check_nodeid(nid: str, owner: str, where: str, errs: list, must_exist: bool) -> None:
    m = NODEID.match(nid)
    if not m:
        errs.append(f"{where}: nodeid 形不合 {nid!r}")
        return
    if m.group(1) != owner:
        errs.append(f"{where}: nodeid 之檔 {m.group(1)} ≠ 該列 {owner}")
        return
    if must_exist and m.group(2) not in defined_names(owner):
        errs.append(f"{where}: 函式不存在 {nid}")


def validate_row(rec: dict, enums: dict, where: str, errs: list) -> None:
    for col in ("guarantee", "oracle", "claim"):
        vals = split_vals(rec[col])
        if not vals:
            errs.append(f"{where}: {col} 為空")
        bad = [x for x in vals if x not in enums[col]]
        if bad:
            errs.append(f"{where}: {col} 值不在契約 enums：{bad}")
    disp = rec["disposition"].strip()
    if disp not in enums["disposition"]:
        errs.append(f"{where}: disposition 值不合 {disp!r}")
    targets = split_vals(rec["rewrite_targets"])
    if disp == "keep" and targets:
        errs.append(f"{where}: disposition=keep 而 rewrite_targets 非空")
    for t in targets:
        check_nodeid(t, rec["path"], where, errs, must_exist=True)
    for item in split_vals(rec["tombstones"]):
        # nodeid 本身含 `::`，等級與 replaced_by 以「:E<n>:」分隔
        m = re.match(r"^(.+?):(E[0-9]):(.+)$", item)
        if not m:
            errs.append(f"{where}: tombstones 項形不合 {item!r}")
            continue
        nid, level, repl = m.group(1), m.group(2), m.group(3)
        if level not in enums["level"]:
            errs.append(f"{where}: tombstones 等級不合 {level!r}")
        check_nodeid(nid, rec["path"], where, errs, must_exist=True)
        if repl != "-":
            for r in repl.split("|"):
                if not NODEID.match(r.strip()):
                    errs.append(f"{where}: replaced_by 形不合 {r!r}")
    ev = split_vals(rec["evidence"])
    if not ev:
        errs.append(f"{where}: evidence 為空")
    for e in ev:
        m = EVIDENCE.match(e)
        if not m:
            errs.append(f"{where}: evidence 形不合 {e!r}")
            continue
        p = REPO / m.group(1)
        if ".." in Path(m.group(1)).parts or not p.is_file():
            errs.append(f"{where}: evidence 檔不存在 {m.group(1)}")
            continue
        n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        lo = int(m.group(2))
        hi = int(m.group(3)) if m.group(3) else lo
        if not 1 <= lo <= hi <= n:
            errs.append(f"{where}: evidence 行號越界或倒置 {e}（檔 {n} 行）")
    if not rec["note"].strip():
        errs.append(f"{where}: note 為空（無則寫 -）")


def norm(col: str, val: str):
    return frozenset(split_vals(val)) if col in SET_COLS else val.strip()


def main(scope_p: str, out_p: str, *pairs: str) -> int:
    scope = [ln.strip() for ln in Path(scope_p).read_text().splitlines() if ln.strip()]
    scope_set = set(scope)
    if len(scope_set) != len(scope):
        print(f"FAIL: 範圍清單有重複 {scope_p}")
        return 1
    if not pairs:
        print("FAIL: 未給任何交件檔")
        return 1
    enums = load_enums()
    errs: list = []
    tables = {}
    for p in pairs:
        name, _, fp = p.partition("=")
        if not name or not fp or name in tables:
            errs.append(f"參數不合或名稱重複：{p!r}")
            continue
        rows = parse(Path(fp), errs)
        missing = sorted(scope_set - set(rows))
        extra = sorted(set(rows) - scope_set)
        if missing:
            errs.append(f"{name}: 缺列 {len(missing)}：{missing[:5]}")
        if extra:
            errs.append(f"{name}: 範圍外列 {len(extra)}：{extra[:5]}")
        for path, rec in rows.items():
            if path in scope_set:
                validate_row(rec, enums, f"{name}:{fp}:{rec['_line']}", errs)
        tables[name] = rows
    if errs:
        print(f"FAIL: {len(errs)} 個錯誤（未寫 {out_p}）")
        for e in errs:
            print(f"  {e}")
        return 1
    names = list(tables)
    out_head = ["path"] + [f"agree_{c}" for c in CMP_COLS]
    for n in names:
        out_head += [f"{n}.{c}" for c in CMP_COLS]
    agree_all = 0
    with open(out_p, "w", encoding="utf-8") as fh:
        fh.write("\t".join(out_head) + "\n")
        for path in scope:
            flags = ["Y" if len({norm(c, tables[n][path][c]) for n in names}) == 1 else "N" for c in CMP_COLS]
            agree_all += all(f == "Y" for f in flags)
            row = [path] + flags
            for n in names:
                row += [tables[n][path][c] for c in CMP_COLS]
            fh.write("\t".join(row) + "\n")
    print(f"PASS: files={len(scope)} sources={len(names)} all_agree={agree_all} → {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
