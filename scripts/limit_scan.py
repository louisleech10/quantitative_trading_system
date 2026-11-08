"""上限盤點掃描器（ICPERF SPEC v5.85 Task 0.6 (a)(b)，L0）。

以語法解析掃 Python（AST）、JSON、TS／TSX（`scripts/limit_scan_ts.js`，TypeScript 編譯器 API）、YAML（`yaml.compose`）
中可能構成上限之數字字面量與符號常數，並以受版控之裁定（`tests/_golden/icperf/limit_rulings.json`）產生現行需修機讀表
`tests/_golden/icperf/limit_inventory.json`。parse 失敗入 errors，不得視為「無上限」。取代
`runs/limit_audit/scan_py_literals.py`（2026-11-03 一次性腳本）。

候選規則：0 一律不列；1、-1 不列，但切片界（`[:1]`、`.slice(…, 1)`）列入；負數以 UnaryOp 還原（`iloc[-500:]` ⇒ -500）；
Python 之比較、切片、函式預設值、呼叫之數字關鍵字參數與 min／max／clip／head／tail／nlargest／nsmallest／islice／range
之位置參數、數字賦值，以及切片界、比較、函式預設值與關鍵字參數中之模組層符號常數（追一層宣告，值記於使用處之行）；
行內無數字之上限判定點（比較式、切片界、head／tail／nlargest／nsmallest／islice 引數之一側為帶上限語意之名稱，如
`if total_rows > max_rows:`、`xs[:top_n]`）列為具名候選（`value` 為 None、`name` 為該名稱）。
有解析錯誤時拒產機讀表（`build_inventory` 拋 ValueError、`--inventory` 回 2 且不寫檔）。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = ("momentum", "api", "frontend/src", "config")
SUFFIXES = {".py", ".json", ".ts", ".tsx", ".yaml", ".yml"}
SKIP_PARTS = {"__pycache__", "node_modules", "tests", ".next", "__fixtures__"}
#: 上限語意名稱（YAML／JSON 鍵路徑、TS 屬性／變數名；TS 子程序經環境變數取同一字面）。
LIMIT_NAME_PATTERN = (r"(limit|max|min|top|cap|budget|timeout|window|period|horizon|lag|sample|threshold|depth|paths|"
                      r"perm|bootstrap|count|rows|cols|batch|chunk|worker|retr|ttl|quantile|bins|alpha|pct|ratio|frac|"
                      r"size|len|n_)")
_LIMIT_NAME = re.compile(LIMIT_NAME_PATTERN, re.IGNORECASE)
CALL_ARG_FUNCS = {"min", "max", "clip", "head", "tail", "nlargest", "nsmallest", "islice", "range"}
TS_HELPER = REPO / "scripts" / "limit_scan_ts.js"


def code_sha256(code: str) -> str:
    """機讀表之行身分：去首尾空白之原始碼行之 sha256。"""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def _num(node: Optional[ast.AST]) -> Optional[float]:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _num(node.operand)
        if v is not None:
            return -v if isinstance(node.op, ast.USub) else v
    return None


def _keep(value: float, *, slice_bound: bool = False) -> bool:
    if value == 0:
        return False
    if value in (1, -1):
        return slice_bound
    return True


def _scan_python(path: Path, text: str) -> List[Dict[str, Any]]:
    tree = ast.parse(text)
    lines = text.splitlines()
    consts: Dict[str, float] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            v = _num(node.value) if node.value is not None else None
            if v is not None:
                for t in targets:
                    if isinstance(t, ast.Name):
                        consts[t.id] = v
    rows: List[Dict[str, Any]] = []
    seen = set()

    def emit(at: ast.AST, kind: str, value: float) -> None:
        ln = at.lineno
        key = (ln, kind, value)
        if key in seen:
            return
        seen.add(key)
        rows.append({"file": str(path), "line": ln, "kind": kind, "value": value,
                     "code": lines[ln - 1].strip()[:200]})

    def value_of(node: Optional[ast.AST]) -> Optional[float]:
        v = _num(node)
        if v is None and isinstance(node, ast.Name) and node.id in consts:
            return consts[node.id]
        return v

    def limit_name(node: Optional[ast.AST]) -> Optional[str]:
        """非數字之上限語意名稱（`max_rows`、`self.top_n`）；模組層數字常數已由 value_of 解析，不重列。"""
        if isinstance(node, ast.Name) and node.id not in consts and _LIMIT_NAME.search(node.id):
            return node.id
        if isinstance(node, ast.Attribute) and _LIMIT_NAME.search(node.attr):
            return node.attr
        return None

    def emit_named(at: ast.AST, kind: str, name: str) -> None:
        ln = at.lineno
        key = (ln, kind, name)
        if key in seen:
            return
        seen.add(key)
        rows.append({"file": str(path), "line": ln, "kind": kind, "value": None, "name": name,
                     "code": lines[ln - 1].strip()[:200]})

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for c in operands:
                v = value_of(c)
                if v is not None and _keep(v):
                    emit(c, "compare", v)
            # 行內無數字之上限判定點（`if total_rows > max_rows:`）：任一運算元帶上限語意名稱且無數字運算元
            if all(value_of(c) is None for c in operands) and \
                    all(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in node.ops):
                for c in operands:
                    name = limit_name(c)
                    if name:
                        emit_named(c, "named_compare", name)
        elif isinstance(node, ast.Slice):
            for c in (node.lower, node.upper, node.step):
                v = value_of(c)
                if c is not None and v is not None and _keep(v, slice_bound=True):
                    emit(c, "slice", v)
                elif c is not None and v is None and limit_name(c):
                    emit_named(c, "named_slice", limit_name(c) or "")
        elif isinstance(node, ast.arguments):
            for c in [*node.defaults, *[d for d in node.kw_defaults if d is not None]]:
                v = value_of(c)
                if v is not None and _keep(v):
                    emit(c, "default", v)
        elif isinstance(node, ast.Call):
            fname = getattr(node.func, "id", getattr(node.func, "attr", ""))
            for kw in node.keywords:
                v = value_of(kw.value)
                if kw.arg and v is not None and _keep(v):
                    emit(kw.value, f"call_kw:{fname}.{kw.arg}", v)
            if fname in CALL_ARG_FUNCS:
                for a in node.args:
                    v = value_of(a)
                    if v is not None and _keep(v):
                        emit(a, f"call_arg:{fname}", v)
                    elif v is None and fname in ("head", "tail", "nlargest", "nsmallest", "islice") and limit_name(a):
                        emit_named(a, f"named_call_arg:{fname}", limit_name(a) or "")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            v = _num(node.value) if node.value is not None else None
            if v is not None and _keep(v):
                for t in targets:
                    name = getattr(t, "id", getattr(t, "attr", ""))
                    if name:
                        emit(node.value, f"assign:{name}", v)
    return rows


def _scan_json(path: Path, text: str) -> List[Dict[str, Any]]:
    """JSON：先完整解析（不可解析 ⇒ 例外 ⇒ errors），再以詞法走訪記每個數字之行號與所在鍵路徑；鍵路徑中任一鍵帶上限
    語意名稱者才列為候選。"""
    json.loads(text)
    rows: List[Dict[str, Any]] = []
    lines = text.splitlines()
    line, i, n = 1, 0, len(text)
    stack: List[Optional[str]] = []      # 每層容器目前之鍵（陣列層為 None）
    pending_key: Optional[str] = None
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            s = text[i + 1:j]
            k = j + 1
            while k < n and text[k] in " \t\r\n":
                k += 1
            if k < n and text[k] == ":":
                pending_key = s
            line += text[i:j + 1].count("\n")
            i = j + 1
            continue
        if ch == "\n":
            line += 1
        elif ch in "{[":
            stack.append(pending_key)
            pending_key = None
        elif ch in "}]":
            if stack:
                stack.pop()
            pending_key = None
        elif ch == ",":
            pending_key = None
        elif ch == "-" or ch.isdigit():
            j = i + 1
            while j < n and (text[j].isdigit() or text[j] in ".eE+-"):
                j += 1
            tok = text[i:j]
            try:
                v = float(tok) if any(c in tok for c in ".eE") else int(tok)
            except ValueError:
                v = None
            keys = [k for k in [*stack, pending_key] if k]
            if v is not None and _keep(v) and any(_LIMIT_NAME.search(k) for k in keys):
                rows.append({"file": str(path), "line": line, "kind": "json_number", "value": v,
                             "code": lines[line - 1].strip()[:200]})
            pending_key = None
            i = j
            continue
        i += 1
    return rows


def _scan_yaml(path: Path, text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    lines = text.splitlines()
    """YAML：以 compose 取節點與行號；鍵路徑中任一鍵帶上限語意名稱之數字純量才列為候選。"""
    for doc in yaml.compose_all(text, Loader=yaml.SafeLoader):
        stack: List[Tuple[Any, Tuple[str, ...]]] = [(doc, ())] if doc is not None else []
        while stack:
            node, keys = stack.pop()
            if isinstance(node, yaml.ScalarNode):
                if node.tag in ("tag:yaml.org,2002:int", "tag:yaml.org,2002:float") \
                        and any(_LIMIT_NAME.search(k) for k in keys):
                    v = yaml.safe_load(node.value)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and _keep(v):
                        ln = node.start_mark.line + 1
                        rows.append({"file": str(path), "line": ln, "kind": "yaml_number", "value": v,
                                     "code": lines[ln - 1].strip()[:200]})
            elif isinstance(node, yaml.SequenceNode):
                stack.extend((child, keys) for child in node.value)
            elif isinstance(node, yaml.MappingNode):
                for k, v in node.value:
                    stack.append((v, keys + (str(getattr(k, "value", "")),)))
    return rows


def _scan_ts(paths: List[Path]) -> Dict[str, Any]:
    if not paths:
        return {"rows": [], "errors": []}
    env = {**os.environ, "LIMIT_NAME_PATTERN": LIMIT_NAME_PATTERN}
    res = subprocess.run(["node", str(TS_HELPER), *[str(p) for p in paths]], capture_output=True, text=True, env=env)
    if res.returncode != 0:
        return {"rows": [], "errors": [{"file": str(p), "error": f"TS 子程序失敗：{res.stderr.strip()[:200]}"}
                                      for p in paths]}
    return json.loads(res.stdout)


def scan(paths: Iterable[Path]) -> Dict[str, Any]:
    """掃描路徑集合，回 `{"rows": [{"file", "line", "kind", "value", "code"}...], "errors": [{"file", "error"}...]}`。"""
    rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    ts_paths: List[Path] = []
    for p in map(Path, paths):
        suffix = p.suffix.lower()
        if suffix in (".ts", ".tsx"):
            ts_paths.append(p)
            continue
        try:
            text = p.read_text(encoding="utf-8")
            if suffix == ".py":
                rows += _scan_python(p, text)
            elif suffix == ".json":
                rows += _scan_json(p, text)
            elif suffix in (".yaml", ".yml"):
                rows += _scan_yaml(p, text)
        except (SyntaxError, ValueError, UnicodeDecodeError, yaml.YAMLError) as exc:
            errors.append({"file": str(p), "error": f"{type(exc).__name__}: {exc}"[:300]})
    ts_out = _scan_ts(ts_paths)
    rows += ts_out["rows"]
    errors += ts_out["errors"]
    return {"rows": rows, "errors": errors}


def _iter_default_files(root: Path) -> List[Path]:
    out: List[Path] = []
    for base in DEFAULT_ROOTS:
        d = root / base
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in SUFFIXES and not (SKIP_PARTS & set(p.relative_to(root).parts)) \
                    and not re.search(r"\.(test|spec)\.[jt]sx?$", p.name):
                out.append(p)
    return out


def scan_default_roots(root: Path) -> Dict[str, Any]:
    """遞迴掃 `root` 下 DEFAULT_ROOTS 之全部 .py／.json／.ts／.tsx／.yaml／.yml 檔（同 `scan` 之輸出形狀；路徑為 root 相對）。"""
    root = Path(root).resolve()
    out = scan(_iter_default_files(root))

    def rel(f: str) -> str:
        try:
            return str(Path(f).resolve().relative_to(root))
        except ValueError:
            return f

    for r in out["rows"]:
        r["file"] = rel(r["file"])
    for e in out["errors"]:
        e["file"] = rel(e["file"])
    out["rows"].sort(key=lambda r: (r["file"], r["line"], str(r["value"])))
    out["errors"].sort(key=lambda e: e["file"])
    return out


RULING_FIELDS = ("category", "semantic_type", "needs_fix", "batch", "reason", "g_impact")


def build_inventory(scan_out: Dict[str, Any], rulings: Dict[str, Any], root: Path) -> Dict[str, Any]:
    """候選＋裁定（`tests/_golden/icperf/limit_rulings.json`，以 file＋code_sha256 為鍵）⇒ 機讀表
    `{"rows": [...], "unruled": [...]}`；無裁定之候選列入 unruled，不得靜默丟棄；裁定指向已不存在之候選列入 unruled。
    裁定帶 `"site": "manual"` 者為手動登記點（行內無數字之上限判定點），依碼 sha 於現行檔定位；列帶 `site`（scan／manual）。"""
    if scan_out.get("errors"):
        # parse 失敗之檔不得視為「無上限」：拒產機讀表，呼叫端須先修好來源或掃描器
        raise ValueError(f"掃描有 {len(scan_out['errors'])} 個解析錯誤，拒產機讀表："
                         + "; ".join(f"{e['file']}: {e['error']}" for e in scan_out["errors"][:5]))
    lines_by_cand: Dict[Tuple[str, str], List[int]] = {}
    code_by_line: Dict[Tuple[str, int], str] = {}
    for r in scan_out["rows"]:
        sha = code_sha256(r["code"]) if len(r["code"]) < 200 else None
        if sha is None:
            full = (Path(root) / r["file"]).read_text(encoding="utf-8").splitlines()[r["line"] - 1]
            sha = code_sha256(full)
        key = (r["file"], sha)
        lines_by_cand.setdefault(key, [])
        if r["line"] not in lines_by_cand[key]:
            lines_by_cand[key].append(r["line"])
        code_by_line[(r["file"], r["line"])] = r["code"]
    ruled: Dict[Tuple[str, str], Dict[str, Any]] = {}
    unruled: List[Dict[str, Any]] = []
    manual_lines: Dict[Tuple[str, str], List[int]] = {}
    for rule in rulings.get("rulings", []):
        key = (rule["file"], rule["code_sha256"])
        if key in lines_by_cand:
            ruled[key] = rule
            continue
        if rule.get("site") == "manual":
            # 手動登記點：行內無數字字面量之上限判定點（如 `if total_rows > max_rows:`），掃描器不列為候選；
            # 以現行檔內去首尾空白後 sha256 相等之行定位，碼已改或刪即列 unruled（同候選之漂移偵測）。
            p = Path(root) / rule["file"]
            text = p.read_text(encoding="utf-8").splitlines() if p.is_file() else []
            hits = [i + 1 for i, ln in enumerate(text) if code_sha256(ln) == rule["code_sha256"]]
            if hits:
                ruled[key] = rule
                manual_lines[key] = hits
                continue
        unruled.append({"file": rule["file"], "code_sha256": rule["code_sha256"], "reason": "裁定之候選已不存在"})
    rows: List[Dict[str, Any]] = []
    for key, lines in sorted({**lines_by_cand, **manual_lines}.items()):
        rule = ruled.get(key)
        site = "manual" if key in manual_lines else "scan"
        for ln in sorted(lines):
            if rule is None:
                unruled.append({"file": key[0], "line": ln, "code": code_by_line[(key[0], ln)],
                                "reason": "候選無裁定"})
                continue
            rows.append({"file": key[0], "line": ln, "code_sha256": key[1], "site": site,
                         **{f: rule[f] for f in RULING_FIELDS}})
    rows.sort(key=lambda r: (r["file"], r["line"]))
    return {"rows": rows, "unruled": unruled}


def rows_json(doc: str, key: str, rows: List[Dict[str, Any]]) -> str:
    """每列一行之 JSON 文件（`{"_doc": ..., key: [ {...},\\n ... ]}`）：仍為合法 JSON，diff 以列為單位、檔案較 indent 版小。"""
    body = ",\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
    return "{" + f'"_doc": {json.dumps(doc, ensure_ascii=False)},\n"{key}": [\n{body}\n]' + "}\n"


def main(argv: Any = None) -> int:
    """CLI：`limit_scan.py [路徑...]` 輸出候選 JSON；`limit_scan.py --inventory --rulings <檔> --out <檔>` 重產機讀表。"""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--inventory", action="store_true")
    ap.add_argument("--rulings", type=Path, default=REPO / "tests" / "_golden" / "icperf" / "limit_rulings.json")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--root", type=Path, default=REPO)
    args = ap.parse_args(argv)
    if args.inventory:
        scan_out = scan_default_roots(args.root)
        if scan_out["errors"]:
            for e in scan_out["errors"]:
                print(f"PARSE ERROR {e['file']}: {e['error']}", file=sys.stderr)
            print("拒產機讀表：有解析錯誤之檔不得視為無上限（未寫出）", file=sys.stderr)
            return 2
        inv = build_inventory(scan_out, json.loads(args.rulings.read_text(encoding="utf-8")), args.root)
        doc_line = "ICPERF SPEC v5.85 Task 0.6 (a)：現行需修機讀表（scripts/limit_scan.py --inventory 產生，勿手改）。" \
                   "semantic_type 為修法矩陣分類（SPEC (c)），reason 為逐列施工指示；兩者所指修法不一致時以 reason 為準" \
                   "（如須保留之程序級串行列）。"
        text = rows_json(doc_line, "rows", inv["rows"])
        if args.out is not None:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        print(json.dumps({"rows": len(inv["rows"]), "unruled": len(inv["unruled"])}, ensure_ascii=False),
              file=sys.stderr)
        return 0 if not inv["unruled"] else 1
    out = scan_default_roots(args.root) if not args.paths else scan([Path(p) for p in args.paths])
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    return 0 if not out["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
