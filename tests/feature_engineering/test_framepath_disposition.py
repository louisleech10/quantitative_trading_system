"""FRAMEPATH Task 1.5：測試／腳本處置表照表執行之機械檢查（docs/FRAMEPATH_SPEC.md Task 1.5 驗證⓪–⑦）。

處置表＝`tests/_golden/framepath/test_disposition.json`（TODO 階段於 HEAD 6e07e0ad 凍結、三家審查戳記、sha256 記入
`docs/manifests/FRAMEPATH.json`）。本檔秒級、不跑被測測試；只比對「現行工作樹」與「HEAD 版套用處置表中本批已執行之列」。

本批 Phase 由環境變數 `FRAMEPATH_PHASE`（1／2／3）給定；未設 ⇒ 3（收案後之常態＝全表已執行）。
E＝處置表中 `phase` ≤ 本批 Phase 之列。
`new_files[].phase`＝「自哪一批起允許存在」（⑤(a)）；TODO 落點（具名驗收測試、契約 JSON）依 TODOFMT 於 TODO
提交即已存在 ⇒ 一律 phase 1，與其所屬 SPEC Task 之 Phase 無關；某批是否「執行」該測由 manifest gate_cmd 決定。

雜湊與正規化之唯一定義在本檔（產生器 `handoffs/run_receipts/framepath_probes/build_disposition.py` 匯入本檔之函式），
處置表 `hash_algorithms` 段為其文字說明：
- AST 傾印＝`ast.dump(node, annotate_fields=True, include_attributes=False)`（不含行列位置，不做 FFACT 剝除）；
  摘錄雜湊＝該傾印之 utf-8 sha256；dict 項以 `Dict(keys=[k], values=[v])` 之傾印計。
- 整模組比對：兩側皆經 `strip_ffact`（SPEC 驗證⑦後段 (a)–(d) 之封閉形態）後之傾印逐字相等。
- JSON canonical＝`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` 之 utf-8。
- 整檔雜湊＝原始位元組之 sha256。
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple  # noqa: F401

import pytest

REPO = Path(__file__).resolve().parents[2]
DISPOSITION_REL = "tests/_golden/framepath/test_disposition.json"
COMPARE_DOMAIN_REL = "tests/_golden/framepath/compare_domain.json"
MANIFEST_REL = "docs/manifests/FRAMEPATH.json"
FACT_KEYS_REL = "scripts/fact_keys.json"
HEAD_SHORT = "6e07e0ad"
R_ROOTS = ("momentum", "api", "scripts", "tests", "frontend/src")
DIFF_ROOTS = ("tests", "scripts", "frontend/src")
IGNORED_EXTS = (".py", ".json", ".ts", ".tsx", ".sh")
FFACT_KEY = "FFACT_USE_CGSA"
PHASES = (1, 2, 3)
KINDS = ("delete-node", "rename", "rewrite", "delete-json-path", "replace-file", "delete-file")
PY_KINDS = ("delete-node", "rename", "rewrite")
LOCATOR_CATEGORIES = ("def", "dict_item", "seq_elem", "import_alias", "parametrize_elem", "stmt")
# SPEC §N 第 2 項所建之欄名殘留列（hdf5_path／hdf5_relative_path 改名）之識別碼；Task 4.1 建於 roadmap-status
RESIDUAL_ROW_ID = "RM-HDF5PATHNAME"
# SPEC v16 ⑥：另准 §N 第 1 項之登記處既有列 RM-FFSTORE（只追加 manifest 型快取命中殘留之登記）
SECTION_N_REGISTRY_ROW_IDS = ("RM-FFSTORE",)
FACT_KEY_ROW_IDS = ("RM-FRAMEPATH", "HP-FRAMEPATH", RESIDUAL_ROW_ID) + SECTION_N_REGISTRY_ROW_IDS
MANIFEST_SHA_RE = re.compile(r"^contract_sha256 (\S+) ([0-9a-f]{64})$")


# ---------------------------------------------------------------------------
# 基本工具
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def ast_dump(node: ast.AST) -> str:
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _git(*args: str, check: bool = True) -> bytes:
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')}")
    return proc.stdout


class HeadReader:
    """HEAD 6e07e0ad 之檔內容讀取（`git cat-file`，結果快取）。"""

    def __init__(self, commit: str) -> None:
        self.commit = commit
        self._cache: Dict[str, Optional[bytes]] = {}
        self._types: Dict[str, Optional[str]] = {}

    def obj_type(self, path: str) -> Optional[str]:
        if path not in self._types:
            proc = subprocess.run(["git", "cat-file", "-t", f"{self.commit}:{path}"], cwd=REPO, capture_output=True)
            self._types[path] = proc.stdout.decode().strip() if proc.returncode == 0 else None
        return self._types[path]

    def read(self, path: str) -> Optional[bytes]:
        if path not in self._cache:
            if self.obj_type(path) != "blob":
                self._cache[path] = None
            else:
                self._cache[path] = _git("cat-file", "blob", f"{self.commit}:{path}")
        return self._cache[path]


def current_bytes(path: str) -> Optional[bytes]:
    p = REPO / path
    return p.read_bytes() if p.is_file() else None


def ext_of(path: str) -> str:
    return Path(path).suffix


# ---------------------------------------------------------------------------
# FFACT_USE_CGSA 剝除正規化（SPEC Task 1.5 驗證末段 (a)–(d)；鍵一律限字面 "FFACT_USE_CGSA"）
# ---------------------------------------------------------------------------

def _is_key(node: Optional[ast.AST]) -> bool:
    return isinstance(node, ast.Constant) and node.value == FFACT_KEY


def _is_os_environ(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "environ"
            and isinstance(node.value, ast.Name) and node.value.id == "os")


def _subscript_key(node: ast.Subscript) -> Optional[ast.AST]:
    sl = node.slice
    if isinstance(sl, ast.Index):  # pragma: no cover - python<3.9
        sl = sl.value  # type: ignore[attr-defined]
    return sl


def _strip_stmt(stmt: ast.stmt) -> bool:
    """True ⇒ 該敘述屬 (a)／(b) 之封閉形態，整句剝除。"""
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        func = call.func
        # (a) monkeypatch.setenv("FFACT_USE_CGSA", …)／monkeypatch.delenv("FFACT_USE_CGSA", …)（receiver 限名稱
        # `monkeypatch`；HEAD 母體實測全為此形，其他 receiver 之同鍵敘述一律判不等——審查 r16 GROK-R16-P1-01）
        if (isinstance(func, ast.Attribute) and func.attr in {"setenv", "delenv"}
                and isinstance(func.value, ast.Name) and func.value.id == "monkeypatch"
                and call.args and _is_key(call.args[0])):
            return True
        # (b) os.environ.pop("FFACT_USE_CGSA", …)
        if (isinstance(func, ast.Attribute) and func.attr == "pop" and _is_os_environ(func.value)
                and call.args and _is_key(call.args[0])):
            return True
    # (b) os.environ["FFACT_USE_CGSA"] = …
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
        tgt = stmt.targets[0]
        if isinstance(tgt, ast.Subscript) and _is_os_environ(tgt.value) and _is_key(_subscript_key(tgt)):
            return True
    # (b) del os.environ["FFACT_USE_CGSA"]
    if isinstance(stmt, ast.Delete) and len(stmt.targets) == 1:
        tgt = stmt.targets[0]
        if isinstance(tgt, ast.Subscript) and _is_os_environ(tgt.value) and _is_key(_subscript_key(tgt)):
            return True
    return False


class _FfactStripper(ast.NodeTransformer):
    def generic_visit(self, node: ast.AST) -> ast.AST:
        for field, old in ast.iter_fields(node):
            if isinstance(old, list):
                new_list: List[Any] = []
                for item in old:
                    if isinstance(item, ast.stmt) and _strip_stmt(item):
                        continue
                    if isinstance(item, ast.AST):
                        item = self.visit(item)
                        if item is None:
                            continue
                    new_list.append(item)
                if old and not new_list and field in {"body", "orelse", "finalbody"} and isinstance(old[0], ast.stmt):
                    new_list = [ast.Pass()]
                setattr(node, field, new_list)
            elif isinstance(old, ast.AST):
                new_node = self.visit(old)
                setattr(node, field, new_node)
        return node

    def visit_Dict(self, node: ast.Dict) -> ast.AST:
        # (c) 任一 dict 字面中該鍵之項
        pairs = [(k, v) for k, v in zip(node.keys, node.values) if not _is_key(k)]
        node.keys = [k for k, _ in pairs]
        node.values = [v for _, v in pairs]
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> ast.AST:
        # (d) 任一呼叫之關鍵字引數 FFACT_USE_CGSA=…
        node.keywords = [kw for kw in node.keywords if kw.arg != FFACT_KEY]
        return self.generic_visit(node)


def _normalize_pass_bodies(tree: ast.AST) -> ast.AST:
    """任一敘述串列若只剩 `pass`（含剝除／刪除後補入者）視為同一形態；不改其他敘述。"""
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            val = getattr(node, field, None)
            if isinstance(val, list) and val and all(isinstance(s, ast.Pass) for s in val):
                setattr(node, field, [ast.Pass()])
    return tree


def strip_ffact(tree: ast.AST) -> ast.AST:
    out = _FfactStripper().visit(copy.deepcopy(tree))
    return _normalize_pass_bodies(out)


def module_dump_normalized(tree: ast.AST) -> str:
    return ast_dump(strip_ffact(tree))


# ---------------------------------------------------------------------------
# 定位器（全部對 HEAD 版 AST 解析；一檔之全部操作先解析成節點身分再一次套用）
# ---------------------------------------------------------------------------

class LocatorError(ValueError):
    pass


_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _children_lists(node: ast.AST) -> Iterable[Tuple[ast.AST, str, list]]:
    for field, val in ast.iter_fields(node):
        if isinstance(val, list):
            yield node, field, val


def _parent_map(tree: ast.AST) -> Dict[int, Tuple[ast.AST, str, list]]:
    parents: Dict[int, Tuple[ast.AST, str, list]] = {}
    for node in ast.walk(tree):
        for owner, field, lst in _children_lists(node):
            for item in lst:
                if isinstance(item, ast.AST):
                    parents[id(item)] = (owner, field, lst)
    return parents


def resolve_def(tree: ast.Module, qualname: str) -> ast.AST:
    scope: ast.AST = tree
    for part in qualname.split("."):
        matches = [n for n in getattr(scope, "body", []) if isinstance(n, _DEF_TYPES) and n.name == part]
        if len(matches) != 1:
            raise LocatorError(f"def {qualname!r}：於 {part!r} 找到 {len(matches)} 個（須恰 1）")
        scope = matches[0]
    return scope


def _resolve_scope(tree: ast.Module, qualname: str) -> ast.AST:
    return tree if qualname == "<module>" else resolve_def(tree, qualname)


def _module_assign_value(tree: ast.Module, target: str) -> ast.AST:
    hits = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) \
                and stmt.targets[0].id == target:
            hits.append(stmt.value)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == target \
                and stmt.value is not None:
            hits.append(stmt.value)
    if len(hits) != 1:
        raise LocatorError(f"模組層賦值 {target!r}：找到 {len(hits)} 個（須恰 1）")
    return hits[0]


def _walk_literal(value: ast.AST, path: Sequence[Any]) -> Tuple[ast.AST, Any]:
    """沿 path 走到最後一步之容器；回傳 (容器, 最後一步)。str 步＝dict 鍵（字串常數），int 步＝序列索引。"""
    node = value
    for step in path[:-1]:
        node = _literal_child(node, step)
    return node, path[-1]


def _literal_child(node: ast.AST, step: Any) -> ast.AST:
    if isinstance(step, str):
        if not isinstance(node, ast.Dict):
            raise LocatorError(f"鍵 {step!r} 之容器非 dict 字面")
        idx = [i for i, k in enumerate(node.keys) if isinstance(k, ast.Constant) and k.value == step]
        if len(idx) != 1:
            raise LocatorError(f"dict 鍵 {step!r}：找到 {len(idx)} 個")
        return node.values[idx[0]]
    if isinstance(step, int) and not isinstance(step, bool):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            raise LocatorError(f"索引 {step} 之容器非 list／tuple／set 字面")
        if not 0 <= step < len(node.elts):
            raise LocatorError(f"索引 {step} 越界（{len(node.elts)}）")
        return node.elts[step]
    raise LocatorError(f"路徑步 {step!r} 型別不合法")


def _parametrize_parts(dec: ast.AST) -> Tuple[ast.AST, Optional[ast.AST]]:
    if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "parametrize"):
        raise LocatorError("decorator 非 *.parametrize(...) 呼叫")
    values = dec.args[1] if len(dec.args) >= 2 else next((k.value for k in dec.keywords if k.arg == "argvalues"), None)
    if not isinstance(values, (ast.List, ast.Tuple)):
        raise LocatorError("parametrize 之 argvalues 非 list／tuple 字面")
    ids = next((k.value for k in dec.keywords if k.arg == "ids"), None)
    if ids is not None and not (isinstance(ids, (ast.List, ast.Tuple)) and len(ids.elts) == len(values.elts)):
        ids = None
    return values, ids


class Target:
    """一個操作在 HEAD 樹上解析出之目標。action ∈ remove_item／remove_dict_item／remove_alias／rename／replace。"""

    def __init__(self, action: str, node: ast.AST, container: Any = None, extra: Any = None) -> None:
        self.action = action
        self.node = node
        self.container = container
        self.extra = extra

    def excerpt_dump(self) -> str:
        if self.action == "remove_dict_item":
            key = self.container.keys[self.extra]
            return ast_dump(ast.Dict(keys=[key], values=[self.node]))
        return ast_dump(self.node)


def resolve_locator(tree: ast.Module, kind: str, loc: Dict[str, Any]) -> Target:
    cat = loc.get("category")
    if cat not in LOCATOR_CATEGORIES:
        raise LocatorError(f"locator.category 不合法：{cat!r}")
    if kind in {"rename", "rewrite"} and cat != "def":
        raise LocatorError(f"{kind} 之 locator.category 須為 def")
    if kind == "rewrite":
        node = resolve_def(tree, loc["qualname"])
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise LocatorError("rewrite 限函式")
        return Target("replace", node)
    if kind == "rename":
        node = resolve_def(tree, loc["qualname"])
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise LocatorError("rename 限函式")
        return Target("rename", node)
    if cat == "def":
        return Target("remove_item", resolve_def(tree, loc["qualname"]))
    if cat in {"dict_item", "seq_elem"}:
        path = loc.get("path")
        if not isinstance(path, list) or not path:
            raise LocatorError("path 須為非空陣列")
        last = path[-1]
        if cat == "dict_item" and not isinstance(last, str):
            raise LocatorError("dict_item 之最後一步須為字串鍵")
        if cat == "seq_elem" and not (isinstance(last, int) and not isinstance(last, bool)):
            raise LocatorError("seq_elem 之最後一步須為整數索引")
        container, step = _walk_literal(_module_assign_value(tree, loc["target"]), path)
        node = _literal_child(container, step)
        if cat == "dict_item":
            idx = [i for i, v in enumerate(container.values) if v is node][0]
            return Target("remove_dict_item", node, container, idx)
        return Target("remove_item", node)
    if cat == "import_alias":
        stmts = [s for s in ast.walk(tree) if isinstance(s, (ast.Import, ast.ImportFrom)) and s.lineno == loc["lineno"]]
        if len(stmts) != 1:
            raise LocatorError(f"import @L{loc['lineno']}：找到 {len(stmts)} 個")
        aliases = [a for a in stmts[0].names if (a.asname or a.name) == loc["name"]]
        if len(aliases) != 1:
            raise LocatorError(f"import 別名 {loc['name']!r}：找到 {len(aliases)} 個")
        return Target("remove_alias", aliases[0], stmts[0])
    if cat == "parametrize_elem":
        fn = resolve_def(tree, loc["qualname"])
        decs = getattr(fn, "decorator_list", [])
        k = loc["decorator_index"]
        if not (isinstance(k, int) and 0 <= k < len(decs)):
            raise LocatorError(f"decorator_index {k} 越界")
        values, ids = _parametrize_parts(decs[k])
        i = loc["index"]
        if not (isinstance(i, int) and 0 <= i < len(values.elts)):
            raise LocatorError(f"parametrize 索引 {i} 越界")
        return Target("remove_item", values.elts[i], extra=(ids.elts[i] if ids is not None else None))
    # stmt
    scope = _resolve_scope(tree, loc["qualname"])
    hits = [n for n in ast.walk(scope) if isinstance(n, ast.stmt) and n is not scope
            and n.lineno == loc["lineno"] and getattr(n, "end_lineno", None) == loc["end_lineno"]]
    if len(hits) != 1:
        raise LocatorError(f"stmt L{loc['lineno']}-{loc['end_lineno']} 於 {loc['qualname']}：找到 {len(hits)} 個")
    return Target("remove_item", hits[0])


def parse_rewrite_source(src: str) -> ast.AST:
    mod = ast.parse(textwrap.dedent(src))
    if len(mod.body) != 1 or not isinstance(mod.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise LocatorError("rewrite.new_source 須恰為一個函式定義")
    return mod.body[0]


def _descendant_ids(node: ast.AST) -> Set[int]:
    return {id(n) for n in ast.walk(node)}


def apply_py_ops(head_src: str, ops: Sequence[Dict[str, Any]]) -> ast.Module:
    """HEAD 版套用 E 中本檔之 delete-node／rename／rewrite；回傳未經 FFACT 剝除之樹。"""
    tree = ast.parse(head_src)
    targets: List[Tuple[Dict[str, Any], Target]] = [(op, resolve_locator(tree, op["kind"], op["locator"])) for op in ops]
    for i, (_, a) in enumerate(targets):
        for j, (_, b) in enumerate(targets):
            if i != j and a.node is not b.node and id(b.node) in _descendant_ids(a.node):
                raise LocatorError(f"操作 {targets[i][0]['id']} 與 {targets[j][0]['id']} 目標巢狀重疊")
            if i < j and a.node is b.node:
                raise LocatorError(f"操作 {targets[i][0]['id']} 與 {targets[j][0]['id']} 指向同一節點")
    parents = _parent_map(tree)
    for op, t in targets:
        if t.action == "rename":
            t.node.name = op["new_name"]  # type: ignore[attr-defined]
        elif t.action == "replace":
            owner, field, lst = parents[id(t.node)]
            lst[[k for k, x in enumerate(lst) if x is t.node][0]] = parse_rewrite_source(op["rewrite"]["new_source"])
        elif t.action == "remove_dict_item":
            idx = [k for k, v in enumerate(t.container.values) if v is t.node][0]
            del t.container.keys[idx]
            del t.container.values[idx]
        elif t.action == "remove_alias":
            t.container.names = [a for a in t.container.names if a is not t.node]
        else:
            owner, field, lst = parents[id(t.node)]
            lst[:] = [x for x in lst if x is not t.node]
            if t.extra is not None:
                o2, f2, l2 = parents[id(t.extra)]
                l2[:] = [x for x in l2 if x is not t.extra]
    # 清空之 import 敘述整句移除；清空之敘述串列補 pass
    for node in ast.walk(tree):
        for owner, field, lst in list(_children_lists(node)):
            if any(isinstance(x, (ast.Import, ast.ImportFrom)) and not x.names for x in lst):
                lst[:] = [x for x in lst if not (isinstance(x, (ast.Import, ast.ImportFrom)) and not x.names)]
            if field == "body" and not lst and isinstance(owner, (ast.stmt, ast.excepthandler)):
                lst.append(ast.Pass())
    return tree


def excerpt_hash_py(head_src: str, op: Dict[str, Any]) -> str:
    tree = ast.parse(head_src)
    return sha256_text(resolve_locator(tree, op["kind"], op["locator"]).excerpt_dump())


def excerpt_text_py(head_src: str, op: Dict[str, Any]) -> str:
    tree = ast.parse(head_src)
    t = resolve_locator(tree, op["kind"], op["locator"])
    seg_node = t.node
    if t.action == "remove_dict_item":
        key = t.container.keys[t.extra]
        return f"{ast.get_source_segment(head_src, key)}: {ast.get_source_segment(head_src, t.node)}"
    if t.action == "remove_alias":
        return ast.get_source_segment(head_src, t.container) or ""
    if isinstance(seg_node, _DEF_TYPES) and seg_node.decorator_list:
        lines = head_src.splitlines()
        start = min(d.lineno for d in seg_node.decorator_list)
        return "\n".join(lines[start - 1: seg_node.end_lineno])
    return ast.get_source_segment(head_src, seg_node) or ""


def preserved_assertion_dumps(head_src: str, items: Sequence[Dict[str, Any]]) -> List[Tuple[int, str]]:
    """「須保留之原斷言」：HEAD 中起於該行之敘述（唯一）之傾印。"""
    tree = ast.parse(head_src)
    out = []
    for item in items:
        hits = [n for n in ast.walk(tree) if isinstance(n, ast.stmt) and n.lineno == item["lineno"]
                and not isinstance(n, _DEF_TYPES)]
        if len(hits) != 1:
            raise LocatorError(f"保留斷言 L{item['lineno']}：找到 {len(hits)} 個敘述")
        out.append((item["lineno"], ast_dump(hits[0])))
    return out


# ---------------------------------------------------------------------------
# JSON 操作
# ---------------------------------------------------------------------------

def _pointer_tokens(pointer: str) -> List[str]:
    if not pointer.startswith("/"):
        raise LocatorError(f"JSON Pointer 須以 / 開頭：{pointer!r}")
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer[1:].split("/")]


def json_resolve(doc: Any, pointer: str) -> Any:
    node = doc
    for tok in _pointer_tokens(pointer):
        if isinstance(node, dict):
            if tok not in node:
                raise LocatorError(f"JSON Pointer {pointer}：鍵 {tok!r} 不存在")
            node = node[tok]
        elif isinstance(node, list):
            if not tok.isdigit() or int(tok) >= len(node):
                raise LocatorError(f"JSON Pointer {pointer}：索引 {tok!r} 不合法")
            node = node[int(tok)]
        else:
            raise LocatorError(f"JSON Pointer {pointer}：穿過純量")
    return node


def json_delete_paths(doc: Any, pointers: Sequence[str]) -> Any:
    """全部 pointer 對 HEAD 文件解析後一次刪除（互為前綴者拒收）。"""
    toks = [tuple(_pointer_tokens(p)) for p in pointers]
    for i, a in enumerate(toks):
        for j, b in enumerate(toks):
            if i != j and b[: len(a)] == a:
                raise LocatorError(f"JSON Pointer 互為前綴：{pointers[i]} ／ {pointers[j]}")
    for p in pointers:
        json_resolve(doc, p)
    targets = set(toks)

    def rec(node: Any, prefix: Tuple[str, ...]) -> Any:
        if isinstance(node, dict):
            return {k: rec(v, prefix + (k,)) for k, v in node.items() if prefix + (k,) not in targets}
        if isinstance(node, list):
            return [rec(v, prefix + (str(i),)) for i, v in enumerate(node) if prefix + (str(i),) not in targets]
        return node

    return rec(doc, ())


def excerpt_hash_json(head_bytes: bytes, pointer: str) -> str:
    return sha256_bytes(canonical_json(json_resolve(json.loads(head_bytes), pointer)))


# ---------------------------------------------------------------------------
# 處置表載入與 schema
# ---------------------------------------------------------------------------

def load_json(rel: str) -> Any:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def batch_phase() -> int:
    raw = os.environ.get("FRAMEPATH_PHASE", "3").strip()
    if raw not in {"1", "2", "3"}:
        raise ValueError(f"FRAMEPATH_PHASE 須為 1／2／3：{raw!r}")
    return int(raw)


def _is_repo_rel(path: Any) -> bool:
    return (isinstance(path, str) and path and not path.startswith("/") and ".." not in Path(path).parts
            and "\\" not in path and not any(ord(c) < 32 for c in path))


def _in_roots(path: str, roots: Sequence[str]) -> bool:
    return any(path == r or path.startswith(r + "/") for r in roots)


def kind_ext_ok(kind: str, path: str) -> bool:
    ext = ext_of(path)
    if kind in PY_KINDS:
        return ext == ".py"
    if kind == "delete-json-path":
        return ext == ".json"
    if kind == "replace-file":
        return ext not in {".py", ".json"}
    return kind == "delete-file"


NODEID_KEYS = {"nodeid", "phase", "disposition", "op", "new_nodeid", "reason"}
OP_COMMON = {"id", "phase", "path", "kind", "excerpt_sha256", "excerpt", "frame_basis", "nodeids"}
OP_EXTRA = {
    "delete-node": {"locator"},
    "rename": {"locator", "new_name"},
    "rewrite": {"locator", "rewrite"},
    "delete-json-path": {"pointer"},
    "replace-file": {"new_content", "new_sha256"},
    "delete-file": set(),
}
REWRITE_KEYS = {"reason", "preserved_assertions", "removed_assertions", "new_source", "new_source_ast_sha256"}
REMOVED_ASSERTION_KEYS = {"lineno", "ast_sha256", "reason"}
NEW_FILE_KEYS = {"path", "phase", "task"}
FACT_ROW_KEYS = {"row_id", "phase"}
TOP_KEYS = {"schema", "head_commit", "python", "spec", "population", "collect", "hash_algorithms", "nodeids",
            "operations", "new_files", "fact_key_rows", "ignored_baseline"}


def schema_errors(disp: Dict[str, Any], spec_text: str) -> List[str]:
    """處置表封閉 schema（SPEC 驗證⑤⑥之三清單 schema 與 nodeid 表／操作表必填欄）。"""
    errs: List[str] = []
    if set(disp) != TOP_KEYS:
        errs.append(f"頂層鍵不符：多 {sorted(set(disp) - TOP_KEYS)} 缺 {sorted(TOP_KEYS - set(disp))}")
        return errs
    for row in disp["nodeids"]:
        if not isinstance(row, dict) or not set(row) <= NODEID_KEYS:
            errs.append(f"nodeid 列未知欄位：{row}")
            continue
        if row.get("phase") not in PHASES:
            errs.append(f"nodeid 列 phase 不合法：{row.get('nodeid')}")
        d = row.get("disposition")
        if d == "keep":
            if set(row) - {"nodeid", "phase", "disposition"}:
                errs.append(f"keep 列不得帶 op／new_nodeid／reason：{row['nodeid']}")
        elif d == "delete":
            if not isinstance(row.get("op"), str) or not isinstance(row.get("reason"), str) or not row["reason"]:
                errs.append(f"delete 列須有 op 與 reason：{row['nodeid']}")
            if "new_nodeid" in row:
                errs.append(f"delete 列不得帶 new_nodeid：{row['nodeid']}")
        elif d == "rename":
            if not isinstance(row.get("op"), str) or not isinstance(row.get("new_nodeid"), str):
                errs.append(f"rename 列須有 op 與 new_nodeid：{row['nodeid']}")
        else:
            errs.append(f"disposition 不合法：{row.get('nodeid')} {d!r}")
    seen_ids: Set[str] = set()
    for op in disp["operations"]:
        kind = op.get("kind")
        if kind not in KINDS:
            errs.append(f"操作種類不合法：{op.get('id')} {kind!r}")
            continue
        want = OP_COMMON | OP_EXTRA[kind]
        if set(op) != want:
            errs.append(f"操作 {op.get('id')} 欄位不符：多 {sorted(set(op) - want)} 缺 {sorted(want - set(op))}")
            continue
        if op["id"] in seen_ids:
            errs.append(f"操作 id 重複：{op['id']}")
        seen_ids.add(op["id"])
        if op["phase"] not in PHASES:
            errs.append(f"操作 {op['id']} phase 不合法")
        if not _is_repo_rel(op["path"]):
            errs.append(f"操作 {op['id']} path 非 repo 相對：{op['path']!r}")
        if not isinstance(op["frame_basis"], str) or not op["frame_basis"].strip():
            errs.append(f"操作 {op['id']} 缺 frame 依據說明")
        if not isinstance(op["nodeids"], list) or not all(isinstance(x, str) for x in op["nodeids"]):
            errs.append(f"操作 {op['id']} nodeids 須為字串陣列")
        if kind == "rewrite":
            rw = op["rewrite"]
            if set(rw) != REWRITE_KEYS or not str(rw.get("reason", "")).strip():
                errs.append(f"操作 {op['id']} rewrite 欄位不符或缺理由")
            elif not isinstance(rw["removed_assertions"], list) or not all(
                    isinstance(r, dict) and set(r) == REMOVED_ASSERTION_KEYS and isinstance(r["lineno"], int)
                    and str(r["reason"]).strip() for r in rw["removed_assertions"]):
                errs.append(f"操作 {op['id']} removed_assertions 每項須為 {{lineno, ast_sha256, reason}} 且理由非空")
    # new_files
    paths_seen: Set[str] = set()
    for item in disp["new_files"]:
        if not isinstance(item, dict) or set(item) != NEW_FILE_KEYS:
            errs.append(f"new_files 項欄位不符：{item}")
            continue
        p, ph, task = item["path"], item["phase"], item["task"]
        if not _is_repo_rel(p) or not _in_roots(p, R_ROOTS):
            errs.append(f"new_files path 不在 R：{p!r}")
        if p in paths_seen:
            errs.append(f"new_files path 重複：{p}")
        paths_seen.add(p)
        if ph not in PHASES:
            errs.append(f"new_files phase 越界：{p}")
        if not isinstance(task, str) or not task_lists_new_path(spec_text, task, p, disp):
            errs.append(f"new_files {p} 之 task {task!r} 未以「（新）」或「新測」列出該 path")
    # fact_key_rows
    rid_seen: Set[str] = set()
    for item in disp["fact_key_rows"]:
        if not isinstance(item, dict) or set(item) != FACT_ROW_KEYS:
            errs.append(f"fact_key_rows 項欄位不符：{item}")
            continue
        if item["row_id"] not in FACT_KEY_ROW_IDS:
            errs.append(f"fact_key_rows row_id 不在允許之三種：{item['row_id']!r}")
        if item["row_id"] in rid_seen:
            errs.append(f"fact_key_rows row_id 重複：{item['row_id']}")
        rid_seen.add(item["row_id"])
        if item["phase"] not in PHASES:
            errs.append(f"fact_key_rows phase 越界：{item['row_id']}")
    ib = disp["ignored_baseline"]
    if not (isinstance(ib, list) and all(isinstance(x, str) for x in ib) and ib == sorted(set(ib))):
        errs.append("ignored_baseline 須為排序後不重複之字串陣列")
    return errs


def spec_task_block(spec_text: str, task: str) -> str:
    m = re.search(rf"\*\*Task {re.escape(task)} — .*?(?=\n\*\*Task |\n### |\n## |\Z)", spec_text, re.S)
    return m.group(0) if m else ""


def task_lists_new_path(spec_text: str, task: str, path: str, disp: Dict[str, Any]) -> bool:
    block = spec_task_block(spec_text, task)
    if not block:
        return False
    # SPEC 之新檔標記三形：「`path`（新）」「`path`，新）」（Task 1.5 處置表）「新測 `path`」
    if re.search(rf"`{re.escape(path)}`(（新）|，新）)", block) or re.search(rf"新測 `{re.escape(path)}`", block):
        return True
    # 或為該 Task 處置表 rename 新函式所在之新檔
    for row in disp.get("nodeids", []):
        if row.get("disposition") == "rename" and str(row.get("new_nodeid", "")).split("::")[0] == path:
            return True
    return False


def ops_in(disp: Dict[str, Any], phase: int) -> List[Dict[str, Any]]:
    return [op for op in disp["operations"] if op["phase"] <= phase]


def rows_in(disp: Dict[str, Any], phase: int) -> List[Dict[str, Any]]:
    return [r for r in disp["nodeids"] if r["phase"] <= phase]


def governed_files(disp: Dict[str, Any]) -> List[str]:
    return sorted(set(disp["population"]["files"]) | {op["path"] for op in disp["operations"]})


def manifest_contract_shas() -> Dict[str, str]:
    man = load_json(MANIFEST_REL)
    out = {}
    for line in man["batch_card"]["risk_mitigation"]:
        m = MANIFEST_SHA_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


# ---------------------------------------------------------------------------
# 檢查本體（純函式，供正式檢查與 mutation 共用）
# ---------------------------------------------------------------------------

def check_0(disp: Dict[str, Any], disp_bytes: bytes, recorded_sha: Optional[str], head: HeadReader,
            spec_text: str) -> List[str]:
    errs = []
    if recorded_sha != sha256_bytes(disp_bytes):
        errs.append(f"⓪ 處置表 sha256 {sha256_bytes(disp_bytes)} ≠ manifest 戳記值 {recorded_sha}")
    errs += [f"⓪ schema：{e}" for e in schema_errors(disp, spec_text)]
    if FACT_KEYS_REL in disp["population"]["files"] or any(op["path"] == FACT_KEYS_REL for op in disp["operations"]):
        errs.append("⓪ scripts/fact_keys.json 出現於母體或操作表")
    for op in disp["operations"]:
        if head.obj_type(op["path"]) == "tree":
            errs.append(f"⓪ 操作 {op['id']} 之 path 於 HEAD 為目錄：{op['path']}")
        if op.get("kind") in KINDS and not kind_ext_ok(op["kind"], op["path"]):
            errs.append(f"⓪ 操作 {op['id']} 種類 {op['kind']} 與副檔名 {ext_of(op['path'])!r} 不相容")
    return errs


def check_1(disp: Dict[str, Any], phase: int, current_nodeids: Set[str]) -> List[str]:
    head_set = {r["nodeid"] for r in disp["nodeids"]}
    e_rows = rows_in(disp, phase)
    expect_gone = {r["nodeid"] for r in e_rows if r["disposition"] in {"delete", "rename"}}
    expect_new = {r["new_nodeid"] for r in e_rows if r["disposition"] == "rename"}
    errs = []
    gone = head_set - current_nodeids
    if gone != expect_gone:
        errs.append(f"① HEAD 母體 − 現行 collect 與 E 之 delete／rename 不等：多 {sorted(gone - expect_gone)[:20]} "
                    f"缺 {sorted(expect_gone - gone)[:20]}")
    extra = current_nodeids - head_set
    if extra != expect_new:
        errs.append(f"① 現行 collect − HEAD 母體 與 E 之 rename 新 nodeid 不等：多 {sorted(extra - expect_new)[:20]} "
                    f"缺 {sorted(expect_new - extra)[:20]}")
    return errs


def expected_vs_current(path: str, head_b: Optional[bytes], cur_b: Optional[bytes],
                        file_ops: Sequence[Dict[str, Any]]) -> Optional[str]:
    """②：單一逐檔期望值規則（不分副檔名）。回傳 None＝相等，否則差異說明。"""
    if any(op["kind"] == "delete-file" for op in file_ops):
        return None if cur_b is None else "期望已刪除（delete-file）而現行仍存在"
    if cur_b is None:
        return "現行不存在（無 delete-file）"
    if head_b is None:
        return "HEAD 不存在此檔"
    ext = ext_of(path)
    if ext == ".py":
        py_ops = [op for op in file_ops if op["kind"] in PY_KINDS]
        try:
            expected = apply_py_ops(head_b.decode("utf-8"), py_ops)
            current = ast.parse(cur_b.decode("utf-8"))
        except (SyntaxError, LocatorError) as exc:
            return f"無法建立期望或解析現行：{exc}"
        if module_dump_normalized(expected) != module_dump_normalized(current):
            return "整模組 AST（經 FFACT 剝除正規化）與期望不等"
        return None
    if ext == ".json":
        pointers = [op["pointer"] for op in file_ops if op["kind"] == "delete-json-path"]
        if not pointers:
            return None if cur_b == head_b else "JSON 無操作而位元組與 HEAD 不等"
        try:
            exp = json_delete_paths(json.loads(head_b), pointers)
            cur = json.loads(cur_b)
        except (ValueError, LocatorError) as exc:
            return f"JSON 期望建立失敗：{exc}"
        return None if canonical_json(exp) == canonical_json(cur) else "JSON canonical 與期望不等"
    rep = [op for op in file_ops if op["kind"] == "replace-file"]
    if rep:
        return None if sha256_bytes(cur_b) == rep[0]["new_sha256"] else "replace-file：現行 sha256 ≠ 凍結值"
    return None if cur_b == head_b else "無操作而位元組與 HEAD 不等"


def check_2(disp: Dict[str, Any], phase: int, head: HeadReader,
            current_reader=current_bytes) -> List[str]:
    e_ops = ops_in(disp, phase)
    errs = []
    for path in governed_files(disp):
        file_ops = [op for op in e_ops if op["path"] == path]
        diff = expected_vs_current(path, head.read(path), current_reader(path), file_ops)
        if diff:
            errs.append(f"② {path}：{diff}")
    return errs


# 審查 r25 CODEX-R25-P1-01：保留斷言須「位置等價」，不只語法存在。封閉規則（白名單）：
# (i) 改寫後該斷言之祖先鏈（函式內各層複合節點之標頭傾印＋下一層所在欄位）須為 HEAD 祖先鏈之子序列——
#     只准拿掉外層（如刪 frame 分支後縮排上移），不准新增任何外層（`if False`、try、with、內層 def 等皆紅）；
# (ii) 沿途每一層區塊中，位於其前之兄弟敘述不得為終止敘述（return／raise／continue／break，或呼叫名為
#     skip／xfail／exit／_exit 之運算式敘述）；
# (iii) 改寫後函式不得新增 HEAD 所無之 skip／skipif／xfail 裝飾器。
_TERMINAL_CALL_NAMES = frozenset({"skip", "xfail", "exit", "_exit"})
_SKIP_MARKER_NAMES = frozenset({"skip", "skipif", "xfail"})
_BODY_FIELDS = ("body", "orelse", "finalbody", "handlers", "cases")


def _header_node(node: ast.AST) -> ast.AST:
    shallow = copy.copy(node)
    for field in _BODY_FIELDS:
        if isinstance(getattr(shallow, field, None), list):
            setattr(shallow, field, [])
    return shallow


def _call_name(node: ast.AST) -> Optional[str]:
    func = node.func if isinstance(node, ast.Call) else node
    if isinstance(func, ast.Call):
        func = func.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_terminal(stmt: ast.stmt) -> bool:
    if isinstance(stmt, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
        return True
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) \
        and _call_name(stmt.value) in _TERMINAL_CALL_NAMES


Link = Tuple[ast.AST, str]  # (祖先節點之標頭〔區塊欄位清空〕, 下一層所在欄位)


def _stmt_paths(func: ast.AST) -> List[Tuple[str, List[Link], bool, int]]:
    """func 內每個敘述 → (傾印, 祖先鏈〔不含 func 本身〕, 沿途是否位於前置終止敘述之後, 行號)。"""
    out: List[Tuple[str, List[Link], bool, int]] = []

    def walk(owner: ast.AST, chain: List[Link], blocked: bool) -> None:
        for field, val in ast.iter_fields(owner):
            if field not in _BODY_FIELDS or not isinstance(val, list):
                continue
            here = chain if owner is func else chain + [(_header_node(owner), field)]
            seen_terminal = blocked
            for child in val:
                if not isinstance(child, ast.AST):
                    continue
                if isinstance(child, ast.stmt):
                    out.append((ast_dump(child), here, seen_terminal, child.lineno))
                walk(child, here, seen_terminal)
                if isinstance(child, ast.stmt) and _is_terminal(child):
                    seen_terminal = True

    walk(func, [], False)
    return out


def _literal_elts(node: ast.AST) -> Optional[List[str]]:
    return [ast_dump(e) for e in node.elts] if isinstance(node, (ast.Tuple, ast.List)) else None


def _link_matches(new: Link, head: Link) -> bool:
    """同種類、同欄位且標頭傾印相等；唯一放寬：for 迴圈之 iter 為 tuple／list 字面且新元素為 HEAD 元素之非空子集
    （刪 frame 迭代元素），target 須相等。"""
    (nn, nf), (hn, hf) = new, head
    if type(nn) is not type(hn) or nf != hf:
        return False
    if ast_dump(nn) == ast_dump(hn):
        return True
    if isinstance(nn, (ast.For, ast.AsyncFor)) and ast_dump(nn.target) == ast_dump(hn.target):
        ne, he = _literal_elts(nn.iter), _literal_elts(hn.iter)
        if ne is not None and he is not None and ne and set(ne) <= set(he):
            rest_n, rest_h = copy.copy(nn), copy.copy(hn)
            rest_n.iter = rest_h.iter = ast.Tuple(elts=[], ctx=ast.Load())
            return ast_dump(rest_n) == ast_dump(rest_h)
    return False


def _is_subsequence(sub: Sequence[Link], seq: Sequence[Link]) -> bool:
    it = iter(seq)
    return all(any(_link_matches(x, y) for y in it) for x in sub)


def _skip_markers(func: ast.AST) -> Set[str]:
    return {ast_dump(d) for d in getattr(func, "decorator_list", []) if _call_name(d) in _SKIP_MARKER_NAMES}


def preserved_position_errors(head_func: ast.AST, new_def: ast.AST,
                              rows: Sequence[Tuple[int, str]]) -> Dict[int, str]:
    """保留斷言列（HEAD 行號, 傾印）於改寫後函式之位置等價判定；回傳 {列序: 不合格理由}（空＝全合格）。
    每列以其 HEAD 行號之敘述定祖先鏈；改寫後候選＝同傾印、不在終止敘述後、祖先鏈為該列 HEAD 鏈子序列之敘述；
    列與候選須一對一配對（審查 r26 CODEX-R26-P1-01：兩個相同斷言只留一個 ⇒ 紅），以增廣路徑求最大配對。"""
    head_paths = {(ln, d): c for d, c, _b, ln in _stmt_paths(head_func)}
    new_paths = _stmt_paths(new_def)
    errs: Dict[int, str] = {}
    cands: Dict[int, List[int]] = {}
    for i, (lineno, dump) in enumerate(rows):
        head_chain = head_paths.get((lineno, dump))
        if head_chain is None:
            errs[i] = "不在 HEAD 被改寫函式內"
            continue
        cands[i] = [j for j, (d, c, b, _ln) in enumerate(new_paths)
                    if d == dump and not b and _is_subsequence(c, head_chain)]
        if not cands[i]:
            errs[i] = ("未出現於改寫後全文" if not any(d == dump for d, _c, _b, _ln in new_paths)
                       else "改寫後位置不等價（新增外層控制結構或位於終止敘述之後）")
    owner: Dict[int, int] = {}

    def augment(i: int, seen: Set[int]) -> bool:
        for j in cands.get(i, []):
            if j in seen:
                continue
            seen.add(j)
            if j not in owner or augment(owner[j], seen):
                owner[j] = i
                return True
        return False

    for i in cands:
        if cands[i] and not augment(i, set()):
            errs[i] = "無一對一可配之改寫後敘述（重複斷言數量少於保留列）"
    return errs


def multiline_str_lines(node: ast.AST) -> List[int]:
    return [n.lineno for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and "\n" in n.value]


def check_3(disp: Dict[str, Any], phase: int, head: HeadReader) -> List[str]:
    errs = []
    for op in ops_in(disp, phase):
        if op["kind"] != "rewrite":
            continue
        rw = op["rewrite"]
        try:
            new_def = parse_rewrite_source(rw["new_source"])
        except (SyntaxError, LocatorError) as exc:
            errs.append(f"③ {op['id']} 改寫後全文無法解析：{exc}")
            continue
        if sha256_text(ast_dump(new_def)) != rw["new_source_ast_sha256"]:
            errs.append(f"③ {op['id']} 改寫後全文 AST 雜湊不符")
        if "." in op["locator"].get("qualname", "") and multiline_str_lines(new_def):
            # v17 試作實證：類別方法之凍結全文縮排自 0 起，實作時須縮排入類別，多行字串（docstring 等）之內容隨之
            # 改變 ⇒ ② 之整模組 AST 必不等；凍結全文不得含多行字串常數
            errs.append(f"③ {op['id']} 類別方法改寫全文含多行字串常數（L{multiline_str_lines(new_def)}），縮排後值會變")
        head_src = (head.read(op["path"]) or b"").decode("utf-8")
        try:
            pres = preserved_assertion_dumps(head_src, rw["preserved_assertions"])
            head_func = resolve_locator(ast.parse(head_src), "rewrite", op["locator"]).node
        except (SyntaxError, LocatorError) as exc:
            errs.append(f"③ {op['id']}：{exc}")
            continue
        if _skip_markers(new_def) - _skip_markers(head_func):
            errs.append(f"③ {op['id']} 改寫後函式新增 skip／skipif／xfail 裝飾器")
        for (lineno, dump), item in zip(pres, rw["preserved_assertions"]):
            if sha256_text(dump) != item["ast_sha256"]:
                errs.append(f"③ {op['id']} 保留斷言 L{lineno} 之 HEAD 雜湊不符")
        for i, why in sorted(preserved_position_errors(head_func, new_def, pres).items()):
            errs.append(f"③ {op['id']} 保留斷言 L{pres[i][0]}：{why}")
        errs.extend(f"③ {op['id']} {e}" for e in assertion_coverage_errors(head_func, new_def, rw))
    return errs


def _is_assertion_stmt(node: ast.AST) -> bool:
    """斷言敘述（封閉）：`assert` 或呼叫名以 assert 起首之運算式敘述（如 assert_frame_equal、自訂 assert_* helper）。"""
    if isinstance(node, ast.Assert):
        return True
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
        and (_call_name(node.value) or "").startswith("assert")


def assertion_coverage_errors(head_func: ast.AST, new_def: ast.AST, rw: Dict[str, Any]) -> List[str]:
    """審查 r30 CODEX-R30-P1-01：HEAD 被改寫函式內每個斷言敘述須被「保留列之敘述（含其內部）」涵蓋，或列於
    removed_assertions（行號＋正規化 AST 雜湊＋理由）；刪除列須確為該函式內之斷言、雜湊相符、且不與保留列重疊。
    審查 r31：同一行有兩個以上斷言敘述 ⇒ 無法以行號唯一定位，fail-closed（CODEX-R31-P1-01）；列為刪除之斷言不得
    殘留於改寫後函式——其傾印於改寫後之出現次數不得超過 HEAD 中同傾印且未列刪除者之個數（CODEX-R31-P1-02）。"""
    errs: List[str] = []
    pres_lines = {p["lineno"] for p in rw["preserved_assertions"]}
    covered: Set[int] = set()
    for node in ast.walk(head_func):
        if isinstance(node, ast.stmt) and not isinstance(node, _DEF_TYPES) and node.lineno in pres_lines:
            covered |= {id(x) for x in ast.walk(node)}
    by_line: Dict[int, List[ast.AST]] = {}
    for n in ast.walk(head_func):
        if _is_assertion_stmt(n):
            by_line.setdefault(n.lineno, []).append(n)
    for lineno, nodes in sorted(by_line.items()):
        if len(nodes) > 1:
            errs.append(f"HEAD L{lineno} 有 {len(nodes)} 個斷言敘述，無法以行號唯一定位（fail-closed）")
    asserts = {ln: nodes[0] for ln, nodes in by_line.items() if len(nodes) == 1}
    removed: Set[int] = set()
    for r in rw["removed_assertions"]:
        node = asserts.get(r["lineno"])
        if node is None:
            errs.append(f"刪除斷言 L{r['lineno']} 不是被改寫函式內可唯一定位之斷言敘述")
        elif sha256_text(ast_dump(node)) != r["ast_sha256"]:
            errs.append(f"刪除斷言 L{r['lineno']} 之 HEAD 雜湊不符")
        elif id(node) in covered:
            errs.append(f"刪除斷言 L{r['lineno']} 同時落在保留列內")
        else:
            removed.add(r["lineno"])
    for lineno, node in sorted(asserts.items()):
        if id(node) not in covered and lineno not in removed:
            errs.append(f"HEAD 斷言 L{lineno} 既未列保留亦未列刪除（含理由）")
    new_counts: Dict[str, int] = {}
    for n in ast.walk(new_def):
        if isinstance(n, ast.stmt):
            new_counts[ast_dump(n)] = new_counts.get(ast_dump(n), 0) + 1
    head_kept: Dict[str, int] = {}
    for n in ast.walk(head_func):
        if isinstance(n, ast.stmt) and not (_is_assertion_stmt(n) and n.lineno in removed):
            head_kept[ast_dump(n)] = head_kept.get(ast_dump(n), 0) + 1
    for lineno in sorted(removed):
        dump = ast_dump(asserts[lineno])
        if new_counts.get(dump, 0) > head_kept.get(dump, 0):
            errs.append(f"刪除斷言 L{lineno} 仍殘留於改寫後函式")
    return errs


def check_4(disp: Dict[str, Any], head: HeadReader) -> List[str]:
    errs = []
    ops = {op["id"]: op for op in disp["operations"]}
    table = {r["nodeid"]: r for r in disp["nodeids"]}
    for r in disp["nodeids"]:
        if r["disposition"] in {"delete", "rename"}:
            op = ops.get(r.get("op"))
            if op is None:
                errs.append(f"④ {r['nodeid']} 所指操作 {r.get('op')} 不存在")
            elif r["nodeid"] not in op["nodeids"]:
                errs.append(f"④ {r['nodeid']} 所指操作 {op['id']} 之 nodeid 集合不含之")
            elif op["phase"] != r["phase"]:
                errs.append(f"④ {r['nodeid']} 與其操作 {op['id']} 之 phase 不同")
    for op in disp["operations"]:
        for nid in op["nodeids"]:
            r = table.get(nid)
            if r is None or r["disposition"] not in {"delete", "rename"} or r.get("op") != op["id"]:
                errs.append(f"④ 操作 {op['id']} 之 nodeid {nid} 於 nodeid 表未標 delete／rename 指回本列")
        if op["kind"] == "delete-file":
            file_ids = {r["nodeid"] for r in disp["nodeids"] if r["nodeid"].split("::")[0] == op["path"]}
            if not file_ids <= set(op["nodeids"]):
                errs.append(f"④ delete-file {op['id']} 未涵蓋該檔全部 HEAD nodeid")
        hb = head.read(op["path"])
        if hb is None:
            errs.append(f"④ 操作 {op['id']} 之 path 於 HEAD 不存在：{op['path']}")
            continue
        try:
            if op["kind"] in PY_KINDS:
                got = excerpt_hash_py(hb.decode("utf-8"), op)
            elif op["kind"] == "delete-json-path":
                got = excerpt_hash_json(hb, op["pointer"])
            else:
                got = sha256_bytes(hb)
        except (SyntaxError, LocatorError, ValueError, KeyError) as exc:
            errs.append(f"④ 操作 {op['id']} 摘錄雜湊算不出：{exc}")
            continue
        if got != op["excerpt_sha256"]:
            errs.append(f"④ 操作 {op['id']} 摘錄雜湊 {got} ≠ 表列 {op['excerpt_sha256']}")
        if op["kind"] == "replace-file" and sha256_text(op["new_content"]) != op["new_sha256"]:
            errs.append(f"④ replace-file {op['id']} 新檔全文與 new_sha256 不符")
    return errs


def _filter_ignored(paths: Iterable[str]) -> List[str]:
    return sorted({p for p in paths if p.endswith(IGNORED_EXTS) and "__pycache__/" not in p})


def git_added_and_untracked() -> Set[str]:
    added = _git("diff", "--name-status", "--diff-filter=A", HEAD_SHORT, "--", *R_ROOTS).decode().splitlines()
    out = {line.split("\t", 1)[1] for line in added if "\t" in line}
    out |= {p for p in _git("ls-files", "--others", "--exclude-standard", "--", *R_ROOTS).decode().splitlines() if p}
    return out


def anchor_commit_time() -> int:
    return int(_git("show", "-s", "--format=%ct", HEAD_SHORT).decode().strip())


def ignored_since_anchor(paths: Iterable[str], anchor_ct: int,
                         mtime=lambda p: (REPO / p).stat().st_mtime) -> List[str]:
    """⑤(b) 之計入集合（SPEC v16 A11；審查 r25 GROK-R25-P1-01）：過濾後之被忽略檔中，mtime 不早於錨點 6e07e0ad
    提交時間者。錨點之前即存在之本機被忽略檔（非本票產物，乾淨 worktree 不存在）不計，使⑤(b) 於主工作樹與乾淨
    worktree 同義；以保留舊 mtime 之複製或 `touch` 回撥時間屬蓄意繞過，不在本閘防範範圍。"""
    return sorted(p for p in _filter_ignored(paths) if mtime(p) >= anchor_ct)


def git_ignored() -> List[str]:
    return ignored_since_anchor(_git("ls-files", "--others", "--ignored", "--exclude-standard", "--", *R_ROOTS)
                                .decode().splitlines(), anchor_commit_time())


def check_5(disp: Dict[str, Any], phase: int, added: Set[str], ignored: List[str],
            exists=lambda p: (REPO / p).is_file()) -> List[str]:
    errs = []
    allowed = {item["path"] for item in disp["new_files"] if item["phase"] <= phase}
    extra = sorted(added - allowed)
    if extra:
        errs.append(f"⑤(a) 新增檔不在 new_files（phase ≤ {phase}）：{extra}")
    # 審查 r24 CODEX-R24-P2-01：phase ≤ 本批之 new_files 須實際存在（如 b1 之凍結腳本與 CGSA 指紋基準）
    missing = sorted(p for p in allowed if not exists(p))
    if missing:
        errs.append(f"⑤(a) new_files（phase ≤ {phase}）應存在而缺：{missing}")
    if ignored != disp["ignored_baseline"]:
        errs.append(f"⑤(b) 被忽略檔集合與凍結基線不等：多 {sorted(set(ignored) - set(disp['ignored_baseline']))} "
                    f"缺 {sorted(set(disp['ignored_baseline']) - set(ignored))}")
    return errs


def _fact_rows_without(doc: Dict[str, Any], drop_ids: Set[str]) -> Dict[str, Any]:
    out = copy.deepcopy(doc)
    for key, val in out.items():
        if key == "_schema" or not isinstance(val, dict):
            continue
        cols = val.get("columns")
        rows = val.get("rows")
        if isinstance(cols, list) and "識別碼" in cols and isinstance(rows, list):
            ci = cols.index("識別碼")
            val["rows"] = [r for r in rows if not (isinstance(r, list) and len(r) > ci and r[ci] in drop_ids)]
    return out


def check_6(disp: Dict[str, Any], phase: int, head_doc: Dict[str, Any], cur_doc: Dict[str, Any]) -> List[str]:
    allowed = {item["row_id"] for item in disp["fact_key_rows"] if item["phase"] <= phase}
    if canonical_json(_fact_rows_without(head_doc, allowed)) != canonical_json(_fact_rows_without(cur_doc, allowed)):
        return [f"⑥ scripts/fact_keys.json 於 fact_key_rows（phase ≤ {phase}）以外之列與 HEAD 不等"]
    return []


def git_changed_paths() -> Set[str]:
    out: Set[str] = set()
    for line in _git("diff", "--name-status", "-M", HEAD_SHORT, "--", *DIFF_ROOTS).decode().splitlines():
        parts = line.split("\t")
        out.update(p for p in parts[1:] if p)
    return out


LIVE_DOC_REGISTRY_REL = "scripts/live_doc_registry.json"
# SPEC v16 ⑦：活文件登記表只准本票文件之 `exact` 列增刪（SPEC／TODO manifest 之生命週期登記）
# 只准本票之 SPEC 與 TODO manifest 兩路徑（審查 r16 CODEX-R16-P1-03），且每路徑至多一列、列形恰為
# [路徑, 類別]、類別屬封閉集合（審查 r17 CODEX-R17-P1-04：類別錯、重複、多欄皆不得藏於豁免）
LIVE_DOC_TICKET_ROWS: Dict[str, Tuple[str, ...]] = {
    "docs/FRAMEPATH_SPEC.md": ("LIVE-SPEC", "HIST"),          # 收案時 SPEC 可轉 HIST
    "docs/manifests/FRAMEPATH.json": ("LIVE-CONTRACT", "HIST"),
}


def _live_doc_ticket_row_errors(doc: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    seen: Dict[str, int] = {}
    for r in doc.get("exact") or []:
        if not (isinstance(r, list) and r and r[0] in LIVE_DOC_TICKET_ROWS):
            continue
        seen[r[0]] = seen.get(r[0], 0) + 1
        if len(r) != 2 or r[1] not in LIVE_DOC_TICKET_ROWS[r[0]]:
            errs.append(f"⑦ {LIVE_DOC_REGISTRY_REL} 本票列形或類別不合：{r}")
    errs += [f"⑦ {LIVE_DOC_REGISTRY_REL} 本票列重複：{p}×{n}" for p, n in seen.items() if n > 1]
    return errs


def _live_doc_without_ticket_rows(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(doc)
    rows = out.get("exact")
    if isinstance(rows, list):
        out["exact"] = [r for r in rows if not (isinstance(r, list) and r and r[0] in LIVE_DOC_TICKET_ROWS)]
    return out


def check_7_live_doc(head_doc: Dict[str, Any], cur_doc: Dict[str, Any]) -> List[str]:
    errs = _live_doc_ticket_row_errors(cur_doc)
    if canonical_json(_live_doc_without_ticket_rows(head_doc)) != canonical_json(_live_doc_without_ticket_rows(cur_doc)):
        errs.append(f"⑦ {LIVE_DOC_REGISTRY_REL} 於本票文件 exact 列以外與 HEAD 不等")
    return errs


def check_7(disp: Dict[str, Any], changed: Set[str]) -> List[str]:
    allowed = set(governed_files(disp)) | {item["path"] for item in disp["new_files"]}
    exempt = {FACT_KEYS_REL, LIVE_DOC_REGISTRY_REL}  # 前者由⑥、後者由 check_7_live_doc 裁決
    # 已追蹤之 numba／位元組碼快取（`__pycache__/`，任一測試執行即改寫；同⑤(b) 之過濾，SPEC v16 A5）
    bad = sorted(p for p in changed if p not in exempt and p not in allowed and "__pycache__/" not in p)
    return [f"⑦ 既有檔改動不在母體 ∪ 操作表 ∪ new_files：{bad}"] if bad else []


def collect_nodeids(files: Sequence[str]) -> Set[str]:
    existing = [f for f in files if (REPO / f).is_file()]
    if not existing:
        return set()
    proc = subprocess.run(
        # pytest.ini 之 addopts 含 -v（會抵銷 -q 而印樹狀）；覆寫為只留 import-mode，與 HEAD 凍結時同一命令
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=--import-mode=importlib",
         "-p", "no:cacheprovider", *existing],
        cwd=REPO, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"collect rc={proc.returncode}\n{proc.stdout[-3000:]}\n{proc.stderr[-2000:]}")
    return {line.strip() for line in proc.stdout.splitlines() if "::" in line and not line.startswith(" ")}


def check_table_vs_head(disp: Dict[str, Any], head_nodeids: Set[str]) -> List[str]:
    """nodeid 表須恰等於 HEAD 於 `collect.files` 之實際收集（審查 r18 CODEX-R18-P1-03：表本身漏列／多列時，①④ 以表
    為 HEAD 母體將無從察覺，delete-file 之「涵蓋該檔全部 HEAD nodeid」亦失準）。"""
    table = {r["nodeid"] for r in disp["nodeids"]}
    if table == head_nodeids:
        return []
    return [f"nodeid 表與 HEAD 實際收集不等：表缺 {sorted(head_nodeids - table)[:20]} 表多 {sorted(table - head_nodeids)[:20]}"]


def collect_at_commit(commit: str, files: Sequence[str]) -> Set[str]:
    """於暫存 worktree（detach 於 commit）收集；`data_cache` 以 symlink 指回主工作樹（部分測試模組匯入即讀資料）。"""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="framepath_head_collect_") as tmp:
        wt = Path(tmp) / "wt"
        _git("worktree", "add", "--detach", str(wt), commit)
        try:
            if (REPO / "data_cache").exists():
                (wt / "data_cache").symlink_to(REPO / "data_cache")
            existing = [f for f in files if (wt / f).is_file()]
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=--import-mode=importlib",
                 "-p", "no:cacheprovider", *existing], cwd=wt, capture_output=True, text=True,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"HEAD collect rc={proc.returncode}\n{proc.stdout[-3000:]}")
            return {line.strip() for line in proc.stdout.splitlines() if "::" in line and not line.startswith(" ")}
        finally:
            _git("worktree", "remove", "--force", str(wt), check=False)


def collect_files(disp: Dict[str, Any]) -> List[str]:
    files = set(disp["collect"]["files"])
    files |= {r["new_nodeid"].split("::")[0] for r in disp["nodeids"] if r["disposition"] == "rename"}
    return sorted(files)


# ---------------------------------------------------------------------------
# 正式檢查（現行工作樹）
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ctx() -> Dict[str, Any]:
    disp_bytes = (REPO / DISPOSITION_REL).read_bytes()
    disp = json.loads(disp_bytes)
    return {
        "disp": disp,
        "disp_bytes": disp_bytes,
        "head": HeadReader(disp["head_commit"]),
        "phase": batch_phase(),
        "spec": (REPO / "docs/FRAMEPATH_SPEC.md").read_text(encoding="utf-8"),
    }


def test_head_commit_and_python_pinned(ctx):
    disp = ctx["disp"]
    assert disp["head_commit"].startswith(HEAD_SHORT)
    assert disp["python"] == "%d.%d" % sys.version_info[:2], "AST 傾印格式依 Python 版本；須以凍結時之版本執行"


def test_check_0_sha_schema_and_kinds(ctx):
    recorded = manifest_contract_shas().get(DISPOSITION_REL)
    assert check_0(ctx["disp"], ctx["disp_bytes"], recorded, ctx["head"], ctx["spec"]) == []


FROZEN_ACCEPTANCE_TESTS = (
    "tests/feature_engineering/test_framepath_invariance.py",
    "tests/feature_engineering/test_framepath_cgsa_only.py",
    "tests/feature_engineering/test_framepath_disposition.py",
    "tests/api/test_framepath_api_h5.py",
)
# 審查 r39 CODEX-R39-P1-01：V1 版面 fixture（boundary_14／15 之反向 oracle）與驗收測試同等凍結——manifest 記 sha256、
# 實作許可錨點後不得改、首個生產碼提交後不得改
V1_FIXTURE_FILES = (
    "tests/_golden/framepath/v1_layout/FPV1USDT/cfgv1fixture/manifest.json",
    "tests/_golden/framepath/v1_layout/FPV1USDT/cfgv1fixture/columns.json.gz",
    "tests/_golden/framepath/v1_layout/FPV1USDT/cfgv1fixture/g1.parquet",
)
FROZEN_CONTRACT_FILES = FROZEN_ACCEPTANCE_TESTS + V1_FIXTURE_FILES


def frozen_file_errors(recorded: Dict[str, str], paths: Sequence[str], reader=current_bytes) -> List[str]:
    """TODO 凍結之具名驗收測試：現行位元組 sha256 須等於 manifest 所記（審查 r22 CODEX-R22-P1-01：實作期不得以
    弱化新增驗收檔過閘；需改者回 TODO 重審並更新 manifest）。"""
    errs = []
    for p in paths:
        data = reader(p)
        if p not in recorded:
            errs.append(f"⓪ manifest 未記 {p} 之 contract_sha256")
        elif data is None or sha256_bytes(data) != recorded[p]:
            errs.append(f"⓪ {p} 與 TODO 凍結之 sha256 不等")
    return errs


DISPOSITION_VIEW_REL = "handoffs/run_receipts/20261008-framepath-disposition-view.md"


def test_check_0_disposition_view_bound_to_table():
    """審查 r30 CODEX-R30-P1-03：逐項閱讀視圖（衍生物）入版控、其 sha256 記於 manifest，且首段所記來源 JSON
    sha256 等於現行處置表（視圖與權威表不同步 ⇒ 紅）。"""
    view = current_bytes(DISPOSITION_VIEW_REL)
    assert view is not None
    assert manifest_contract_shas().get(DISPOSITION_VIEW_REL) == sha256_bytes(view)
    table_sha = sha256_bytes(current_bytes(DISPOSITION_REL) or b"")
    assert f"sha256 `{table_sha}`" in view.decode("utf-8").split("\n", 4)[2]


def test_check_0_frozen_acceptance_tests_unchanged():
    assert frozen_file_errors(manifest_contract_shas(), FROZEN_CONTRACT_FILES) == []


# 審查 r28 CODEX-R28-P1-01：manifest 之 contract_sha256 由 manifest 自我宣告，首個生產碼提交前可整批同步改寫
# 而自洽。外部錨點＝gate 於核可後發 FRAMEPATH 實作許可時寫入已提交審計紀錄之 `round_start_head`（gate.sh
# impl_token_issued；manifest 無從改寫）：自該提交起，下列核定檔之位元組不得再變。
AUDIT_REL = ".claude/gate/audit.log"
APPROVAL_FROZEN = FROZEN_CONTRACT_FILES + (MANIFEST_REL, DISPOSITION_REL, COMPARE_DOMAIN_REL)
TICKET_ROOT = "20260928-FRAMEPATH"  # 本票 task-id 根（同票跨日沿用首日前綴）；exact match（審查 r29）


def approval_anchor(audit_lines: Iterable[str]) -> Optional[str]:
    """審計紀錄中最晚一筆本票（root 恰為 TICKET_ROOT；審查 r29 CODEX-R29-P1-01／COMPOSER-R29-P1-01：不以後綴比對，
    他票同後綴之事件不算）`impl_token_issued` 之 round_start_head；無則 None。
    實作期 r41：原取最早一筆 ⇒ 實作期發現凍結驗收之缺陷時，經 TODO 重審＋戳記後亦永無法再核定（錨點恆停在首張許可）。
    改取最晚一筆：工作樹內之改動恆對最新許可時之提交比對（意外漂移照擋）；生產碼開始改動後之凍結檔提交另由
    `history_errors` ①擋；許可之重領須過 gate（戳記、TODOFMT），屬重新核定。"""
    anchor: Optional[str] = None
    for line in audit_lines:
        if '"impl_token_issued"' not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("event") == "impl_token_issued" and ev.get("root") == TICKET_ROOT \
                and re.fullmatch(r"[0-9a-f]{40}", str(ev.get("round_start_head", ""))):
            anchor = ev["round_start_head"]
    return anchor


def approval_errors(anchor: Optional[str], production_changed: bool, paths: Sequence[str],
                    read_at, reader=current_bytes) -> List[str]:
    """有錨點 ⇒ 每個核定檔之現行位元組須等於錨點提交之版本；無錨點而生產碼已改動（提交或工作樹）⇒ 紅
    （實作須先經 gate 領許可）；無錨點且生產碼未動（TODO 階段）⇒ 不判。"""
    if anchor is None:
        return ["⓪ 生產碼已改動但審計無本票實作許可（impl_token_issued）之 round_start_head"] if production_changed else []
    return [f"⓪ {p} 與實作許可時（{anchor[:8]}）核定之版本不等" for p in paths if reader(p) != read_at(anchor, p)]


def _git_show_bytes(commit: str, path: str) -> Optional[bytes]:
    proc = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO, capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def test_check_0_frozen_since_approval_anchor():
    lines = (REPO / AUDIT_REL).read_text(encoding="utf-8", errors="replace").splitlines()
    prod_changed = any("__pycache__/" not in p for p in
                       _git("diff", "--name-only", HEAD_SHORT, "--", *PRODUCTION_ROOTS).decode().splitlines() if p)
    assert approval_errors(approval_anchor(lines), prod_changed, APPROVAL_FROZEN, _git_show_bytes) == []


def test_mutation_self_consistent_rewrite_after_approval_is_red():
    """manifest 與驗收測試於許可後同步改寫（自洽之 sha256）⇒ 紅；生產碼已改而無許可紀錄 ⇒ 紅；TODO 階段不判。"""
    p = "tests/feature_engineering/test_framepath_invariance.py"
    approved = {p: b"assert real()\n", MANIFEST_REL: b'{"sha": "A"}'}
    weakened = {p: b"assert True\n", MANIFEST_REL: b'{"sha": "B"}'}
    anchor = "a" * 40
    ev = json.dumps({"event": "impl_token_issued", "root": "20260928-FRAMEPATH", "round_start_head": anchor})
    other = json.dumps({"event": "impl_token_issued", "root": "20261004-OTHER", "round_start_head": "b" * 40})
    assert approval_anchor(["=== text ===", other, ev]) == anchor
    assert approval_anchor([other]) is None
    # 審查 r29：他票同後綴（-FRAMEPATH）之較早事件不得被選中
    sibling = json.dumps({"event": "impl_token_issued", "root": "20260927-FRAMEPATH", "round_start_head": "c" * 40})
    assert approval_anchor([sibling, ev]) == anchor and approval_anchor([sibling]) is None
    # 實作期 r41：本票多筆許可取最晚一筆；其後之他票事件不改變錨點
    later = json.dumps({"event": "impl_token_issued", "root": "20260928-FRAMEPATH", "round_start_head": "d" * 40})
    assert approval_anchor([ev, later, other, sibling]) == "d" * 40
    assert approval_anchor([later, ev]) == anchor
    read_at = lambda c, path: approved[path]  # noqa: E731
    assert approval_errors(anchor, True, list(approved), read_at, reader=approved.get) == []
    assert approval_errors(anchor, True, list(approved), read_at, reader=weakened.get) != []
    assert approval_errors(None, True, list(approved), read_at, reader=weakened.get) != []
    assert approval_errors(None, False, list(approved), read_at, reader=weakened.get) == []


PRODUCTION_ROOTS = ("momentum", "api", "config")
BASELINE_REL = "tests/_golden/framepath/cgsa_fingerprint.json"


def history_errors(commits_after_anchor: Sequence[Tuple[str, Set[str]]], frozen: Sequence[str],
                   baseline: str = BASELINE_REL) -> List[str]:
    """git 歷史之凍結次序（審查 r23 CODEX-R23-P1-01／P1-02）。`commits_after_anchor`＝錨點之後依時間序之
    (commit, 該提交改動之路徑集合)。規則：①首個改動生產碼（momentum／api／config）之提交之後，不得再有改動
    `frozen`（四支驗收測試與 manifest）之提交；②基準檔之每一次加入或改動皆須在首個生產碼提交之前（不得同一提交混改）。
    實作期 r43（SPEC v19 D2）：原 ②「加入後不得再改」使錨點碼態下之補格重凍（同碼態、無生產改動）亦恆紅；生產碼開始改動後
    仍一律禁改。"""
    errs: List[str] = []
    first_prod = next((i for i, (_, paths) in enumerate(commits_after_anchor)
                       if any(_in_roots(p, PRODUCTION_ROOTS) for p in paths)), None)
    if first_prod is not None:
        for c, paths in commits_after_anchor[first_prod + 1:] + commits_after_anchor[first_prod:first_prod + 1]:
            touched = sorted(set(paths) & set(frozen))
            if touched:
                errs.append(f"⓪ 生產碼改動開始後之提交 {c[:8]} 仍改動凍結檔：{touched}")
    base_idx = [i for i, (_, paths) in enumerate(commits_after_anchor) if baseline in paths]
    if first_prod is not None:
        late = [commits_after_anchor[i][0][:8] for i in base_idx if i >= first_prod]
        if late:
            errs.append(f"⓪ 基準 {baseline} 於生產碼改動開始後（含同一提交）被加入或改動：{late}")
    return errs


def git_commits_after_anchor() -> List[Tuple[str, Set[str]]]:
    out = _git("log", "--reverse", "--format=@%H", "--name-only", f"{HEAD_SHORT}..HEAD").decode().splitlines()
    commits: List[Tuple[str, Set[str]]] = []
    for line in out:
        if line.startswith("@"):
            commits.append((line[1:], set()))
        elif line.strip() and commits:
            commits[-1][1].add(line.strip())
    return commits


def test_check_0_history_freeze_order():
    assert history_errors(git_commits_after_anchor(), (*FROZEN_CONTRACT_FILES, MANIFEST_REL)) == []


# 審查 r43 CODEX-R43-P1-01：D2 准生產碼前重凍，但既有格之 fingerprint 與語意 receipt 不得被改寫（只准新增格）；
# receipt 中隨每次執行之暫存路徑不同之鍵不比
BASELINE_RUN_PATH_KEYS = frozenset({"kline_copy", "legacy_kline_dir", "child_env"})


def baseline_lineage_errors(versions: Sequence[Tuple[str, Dict[str, Any]]]) -> List[str]:
    """基準各版本（依時間序之 (版本名, 基準 JSON)）之承續：後版須含前版每一格，且該格 fingerprint 逐項相等、
    receipt 除 `BASELINE_RUN_PATH_KEYS` 外相等、`code_anchor` 不變；只准新增格（memory 屬量測值不比）。"""
    errs: List[str] = []
    for (prev_name, prev), (name, cur) in zip(versions, versions[1:]):
        if prev.get("code_anchor") != cur.get("code_anchor"):
            errs.append(f"⓪ 基準 {name} 之 code_anchor 與 {prev_name} 不同")
        for cell, old in (prev.get("cells") or {}).items():
            new = (cur.get("cells") or {}).get(cell)
            if new is None:
                errs.append(f"⓪ 基準 {name} 刪除了既有格 {cell}")
                continue
            if new.get("fingerprint") != old.get("fingerprint"):
                errs.append(f"⓪ 基準 {name} 改寫了既有格 {cell} 之 fingerprint")
            strip = lambda r: {k: v for k, v in (r or {}).items() if k not in BASELINE_RUN_PATH_KEYS}  # noqa: E731
            if strip(new.get("receipt")) != strip(old.get("receipt")):
                errs.append(f"⓪ 基準 {name} 改寫了既有格 {cell} 之 receipt")
    return errs


def git_baseline_versions() -> List[Tuple[str, Dict[str, Any]]]:
    """錨點後每個改動基準之提交之版本，加上工作樹現行版本（依時間序）。"""
    out = _git("log", "--reverse", "--format=%H", f"{HEAD_SHORT}..HEAD", "--", BASELINE_REL).decode().split()
    versions = [(c[:8], json.loads(_git_show_bytes(c, BASELINE_REL) or b"{}")) for c in out]
    current = REPO / BASELINE_REL
    if current.is_file():
        versions.append(("worktree", json.loads(current.read_text(encoding="utf-8"))))
    return versions


def test_check_0_baseline_existing_cells_preserved():
    assert baseline_lineage_errors(git_baseline_versions()) == []


def test_mutation_baseline_lineage_rewrites_are_red():
    fp = {"run_status": "complete", "columns": {"x": {"values": "v"}}}
    rc = {"resume_entered": False, "kline_copy": "/tmp/a"}
    v1 = {"code_anchor": "a", "cells": {"C1": {"fingerprint": fp, "receipt": rc, "memory": {"peak_bytes": 1}}}}
    added = {"code_anchor": "a", "cells": {"C1": {"fingerprint": fp, "receipt": dict(rc, kline_copy="/tmp/b"),
                                                   "memory": {"peak_bytes": 2}},
                                           "C10": {"fingerprint": fp, "receipt": {}}}}
    assert baseline_lineage_errors([("v1", v1), ("v2", added)]) == []
    rewritten = json.loads(json.dumps(added))
    rewritten["cells"]["C1"]["fingerprint"]["columns"]["x"]["values"] = "w"
    assert baseline_lineage_errors([("v1", v1), ("v2", rewritten)]) != []
    dropped = {"code_anchor": "a", "cells": {"C10": added["cells"]["C10"]}}
    assert baseline_lineage_errors([("v1", v1), ("v2", dropped)]) != []
    semantic = json.loads(json.dumps(added))
    semantic["cells"]["C1"]["receipt"]["resume_entered"] = True
    assert baseline_lineage_errors([("v1", v1), ("v2", semantic)]) != []
    moved = dict(added, code_anchor="b")
    assert baseline_lineage_errors([("v1", v1), ("v2", moved)]) != []


def test_mutation_history_freeze_order_violations_are_red():
    t, m, b, prod = FROZEN_ACCEPTANCE_TESTS[0], MANIFEST_REL, BASELINE_REL, "momentum/x.py"
    ok = [("a" * 40, {t, m}), ("b" * 40, {b}), ("c" * 40, {prod})]
    assert history_errors(ok, (t, m)) == []
    assert history_errors(ok + [("d" * 40, {t})], (t, m)) != []            # 生產碼後改驗收測試
    assert history_errors(ok + [("d" * 40, {m})], (t, m)) != []            # 生產碼後改 manifest
    assert history_errors([("c" * 40, {prod, t})], (t, m)) != []           # 同一提交混改
    assert history_errors([("c" * 40, {prod}), ("d" * 40, {b})], (t, m)) != []  # 基準於生產碼後加入
    assert history_errors(ok + [("d" * 40, {b})], (t, m)) != []            # 基準於生產碼後被改寫
    # 實作期 r43（SPEC v19 D2）：生產碼改動前之重凍（同碼態補格）允許；同一提交混改生產碼與基準 ⇒ 紅
    refrozen = [("a" * 40, {t, m}), ("b" * 40, {b}), ("e" * 40, {b, t, m}), ("c" * 40, {prod})]
    assert history_errors(refrozen, (t, m)) == []
    assert history_errors([("a" * 40, {t, m}), ("c" * 40, {prod, b})], (t, m)) != []


def test_mutation_weakened_acceptance_test_is_red():
    recorded = {"t.py": sha256_bytes(b"assert x == 1\n")}
    assert frozen_file_errors(recorded, ["t.py"], lambda p: b"assert x == 1\n") == []
    assert frozen_file_errors(recorded, ["t.py"], lambda p: b"assert True\n") != []
    assert frozen_file_errors({}, ["t.py"], lambda p: b"assert x == 1\n") != []


def test_mutation_hollowed_v1_fixture_is_red():
    """審查 r39 CODEX-R39-P1-01：V1 fixture 列入凍結契約；改成仍可解壓之空 columns 等任一位元組變動 ⇒ ⓪紅。"""
    import gzip

    assert set(V1_FIXTURE_FILES) <= set(FROZEN_CONTRACT_FILES) and set(V1_FIXTURE_FILES) <= set(APPROVAL_FROZEN)
    path = V1_FIXTURE_FILES[1]
    real = current_bytes(path)
    recorded = {path: sha256_bytes(real)}
    assert frozen_file_errors(recorded, [path], lambda p: real) == []
    assert frozen_file_errors(recorded, [path], lambda p: gzip.compress(b"[]")) != []


def test_check_1_collect_difference(ctx):
    current = collect_nodeids(collect_files(ctx["disp"]))
    assert check_1(ctx["disp"], ctx["phase"], current) == []


def test_nodeid_table_equals_head_collect(ctx):
    disp = ctx["disp"]
    assert check_table_vs_head(disp, collect_at_commit(disp["head_commit"], disp["collect"]["files"])) == []


def test_mutation_nodeid_table_row_dropped_with_op_ids_is_red():
    """同時自表與 delete-file 之 nodeids 移除某檔全部列（CODEX-R18-P1-03 之繞法）⇒ 表與 HEAD 收集不等。"""
    head = {"t.py::a", "t.py::b", "u.py::c"}
    full = {"nodeids": [{"nodeid": n, "phase": 1, "disposition": "keep"} for n in sorted(head)]}
    dropped = {"nodeids": [r for r in full["nodeids"] if not r["nodeid"].startswith("u.py")]}
    assert check_table_vs_head(full, head) == []
    assert check_table_vs_head(dropped, head) != []


def test_check_2_per_file_expected(ctx):
    assert check_2(ctx["disp"], ctx["phase"], ctx["head"]) == []


def test_check_3_rewrite_keeps_assertions(ctx):
    assert check_3(ctx["disp"], 3, ctx["head"]) == []


def test_check_4_internal_consistency_and_excerpts(ctx):
    assert check_4(ctx["disp"], ctx["head"]) == []


def test_check_5_new_and_ignored_files(ctx):
    assert check_5(ctx["disp"], ctx["phase"], git_added_and_untracked(), git_ignored()) == []


def test_check_6_fact_keys_rows(ctx):
    head_doc = json.loads(ctx["head"].read(FACT_KEYS_REL))
    assert check_6(ctx["disp"], ctx["phase"], head_doc, load_json(FACT_KEYS_REL)) == []


def test_check_7_changed_paths_in_scope(ctx):
    assert check_7(ctx["disp"], git_changed_paths()) == []
    head_doc = json.loads(ctx["head"].read(LIVE_DOC_REGISTRY_REL))
    assert check_7_live_doc(head_doc, load_json(LIVE_DOC_REGISTRY_REL)) == []


def test_mutation_live_doc_registry_foreign_row_is_red():
    head = {"exact": [["docs/A_SPEC.md", "LIVE-SPEC"]], "prefix": []}
    ok = {"exact": [["docs/A_SPEC.md", "LIVE-SPEC"], ["docs/FRAMEPATH_SPEC.md", "LIVE-SPEC"],
                    ["docs/manifests/FRAMEPATH.json", "LIVE-CONTRACT"]], "prefix": []}
    for rows in ([["docs/FRAMEPATH_SPEC.md", "FOREIGN"]],                                   # 類別錯
                 [["docs/FRAMEPATH_SPEC.md", "LIVE-SPEC"], ["docs/FRAMEPATH_SPEC.md", "LIVE-SPEC"]],  # 重複
                 [["docs/FRAMEPATH_SPEC.md", "LIVE-SPEC", "FOREIGN"]]):                     # 多欄
        assert check_7_live_doc(head, {"exact": [["docs/A_SPEC.md", "LIVE-SPEC"], *rows], "prefix": []}) != []
    bad = {"exact": [["docs/A_SPEC.md", "ARCHIVED"]], "prefix": []}
    other = {"exact": [["docs/A_SPEC.md", "LIVE-SPEC"], ["docs/FRAMEPATH_OTHER.md", "FOREIGN"]], "prefix": []}
    assert check_7_live_doc(head, ok) == []
    assert check_7_live_doc(head, bad) != []
    assert check_7_live_doc(head, other) != []


def test_compare_domain_sha_recorded():
    recorded = manifest_contract_shas().get(COMPARE_DOMAIN_REL)
    assert recorded == sha256_bytes((REPO / COMPARE_DOMAIN_REL).read_bytes())


# ---------------------------------------------------------------------------
# 邊界與 mutation（不碰工作樹；以 HEAD 內容與合成輸入餵純函式）
# ---------------------------------------------------------------------------

_SAMPLE = '''
import os
import pytest
from x import a, b as bee

_PATH_ENV = {"cgsa": {"FFACT_MULTI_TF_PARALLEL": "0"}, "legacy": {"FFACT_USE_CGSA": "0"}}
FIXED_ENV = {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0"}
EXPECTED = {("n1", "FRAMEPATH"), ("n2", "FFSTORE")}


@pytest.mark.parametrize("env", [{"FFACT_USE_CGSA": "0", "FFACT_MULTI_TF_PARALLEL": "0"}, {"FFACT_MULTI_TF_PARALLEL": "0"}], ids=["frame", "cgsa"])
def test_arms(monkeypatch, env):
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    os.environ["FFACT_USE_CGSA"] = "1"
    run(env, FFACT_USE_CGSA="1")
    assert compare(1) == 1


def test_frame_only():
    assert frame() == 2


def test_mixed(monkeypatch):
    cg = run_cgsa()
    fr = run_frame()
    assert cg.ok
    assert cg == fr
'''


def _op(kind: str, locator: Optional[Dict[str, Any]] = None, **kw: Any) -> Dict[str, Any]:
    op = {"id": kw.pop("id", "OP-T"), "phase": kw.pop("phase", 1), "path": kw.pop("path", "tests/x.py"), "kind": kind,
          "excerpt_sha256": "", "excerpt": "", "frame_basis": "t", "nodeids": kw.pop("nodeids", [])}
    if locator is not None:
        op["locator"] = locator
    op.update(kw)
    return op


def _eq(head_src: str, cur_src: str, ops: Sequence[Dict[str, Any]]) -> bool:
    return expected_vs_current("tests/x.py", head_src.encode(), cur_src.encode(), ops) is None


def test_boundary_01_strip_only_ffact_is_equal():
    cur = _SAMPLE.replace('    monkeypatch.setenv("FFACT_USE_CGSA", "1")\n', "") \
        .replace('    os.environ["FFACT_USE_CGSA"] = "1"\n', "") \
        .replace('run(env, FFACT_USE_CGSA="1")', "run(env)") \
        .replace('FIXED_ENV = {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0"}', 'FIXED_ENV = {"FFACT_MULTI_TF_PARALLEL": "0"}')
    assert _eq(_SAMPLE, cur, [])


def test_mutation_keep_assertion_to_assert_true_is_red():
    cur = _SAMPLE.replace("assert frame() == 2", "assert True")
    assert not _eq(_SAMPLE, cur, [])


def test_mutation_other_env_key_value_change_is_red():
    cur = _SAMPLE.replace('{"FFACT_MULTI_TF_PARALLEL": "0"}], ids', '{"FFACT_MULTI_TF_PARALLEL": "1"}], ids')
    assert not _eq(_SAMPLE, cur, [])


def test_mutation_path_registry_value_or_unlisted_key_is_red():
    cur1 = _SAMPLE.replace('"cgsa": {"FFACT_MULTI_TF_PARALLEL": "0"}', '"cgsa": {"FFACT_MULTI_TF_PARALLEL": "1"}')
    cur2 = _SAMPLE.replace('"cgsa": {"FFACT_MULTI_TF_PARALLEL": "0"}, ', "")
    assert not _eq(_SAMPLE, cur1, [])
    assert not _eq(_SAMPLE, cur2, [])


def test_boundary_02_listed_dict_item_and_def_and_import_deletion_is_green():
    ops = [
        _op("delete-node", {"category": "dict_item", "target": "_PATH_ENV", "path": ["legacy"]}, id="A"),
        _op("delete-node", {"category": "def", "qualname": "test_frame_only"}, id="B"),
        _op("delete-node", {"category": "import_alias", "lineno": 4, "name": "bee"}, id="C"),
    ]
    cur = _SAMPLE.replace(', "legacy": {"FFACT_USE_CGSA": "0"}', "") \
        .replace("from x import a, b as bee", "from x import a") \
        .replace("\n\ndef test_frame_only():\n    assert frame() == 2\n", "\n")
    assert _eq(_SAMPLE, cur, ops)


def test_boundary_03_parametrize_elem_removes_matching_id():
    ops = [_op("delete-node", {"category": "parametrize_elem", "qualname": "test_arms", "decorator_index": 0, "index": 0})]
    cur = _SAMPLE.replace('[{"FFACT_USE_CGSA": "0", "FFACT_MULTI_TF_PARALLEL": "0"}, ', "[") \
        .replace('ids=["frame", "cgsa"]', 'ids=["cgsa"]')
    assert _eq(_SAMPLE, cur, ops)


def test_boundary_04_seq_elem_in_set_literal():
    ops = [_op("delete-node", {"category": "seq_elem", "target": "EXPECTED", "path": [0]})]
    cur = _SAMPLE.replace('EXPECTED = {("n1", "FRAMEPATH"), ("n2", "FFSTORE")}', 'EXPECTED = {("n2", "FFSTORE")}')
    assert _eq(_SAMPLE, cur, ops)


def test_boundary_05_stmt_deletion_in_function():
    lines = _SAMPLE.splitlines()
    l_fr = lines.index("    fr = run_frame()") + 1
    l_eq = lines.index("    assert cg == fr") + 1
    ops = [_op("delete-node", {"category": "stmt", "qualname": "test_mixed", "lineno": l_fr, "end_lineno": l_fr}, id="S1"),
           _op("delete-node", {"category": "stmt", "qualname": "test_mixed", "lineno": l_eq, "end_lineno": l_eq}, id="S2")]
    cur = _SAMPLE.replace("    fr = run_frame()\n", "").replace("    assert cg == fr\n", "")
    assert _eq(_SAMPLE, cur, ops)


def test_mutation_rewrite_differs_from_frozen_text_is_red():
    new_src = "def test_mixed(monkeypatch):\n    cg = run_cgsa()\n    assert cg.ok\n"
    ops = [_op("rewrite", {"category": "def", "qualname": "test_mixed"},
               rewrite={"reason": "r", "preserved_assertions": [], "new_source": new_src, "new_source_ast_sha256": ""})]
    good = _SAMPLE.replace("    fr = run_frame()\n", "").replace("    assert cg == fr\n", "")
    bad = good.replace("    assert cg.ok\n", "    assert True\n")
    assert _eq(_SAMPLE, good, ops)
    assert not _eq(_SAMPLE, bad, ops)


class _SrcHead:
    def __init__(self, src: str) -> None:
        self.src = src

    def read(self, path: str) -> bytes:
        return self.src.encode("utf-8")


_POS_HEAD = (
    "def test_p():\n"
    "    for name in ('frame', 'cgsa'):\n"
    "        if name == 'frame':\n"
    "            run_frame()\n"
    "        else:\n"
    "            assert ok(name)\n"
    "    assert done()\n"
)


def _pos_errs(new_src: str) -> List[str]:
    tree = ast.parse(_POS_HEAD)
    items = [{"lineno": n.lineno, "ast_sha256": sha256_text(ast_dump(n))}
             for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    rw = {"reason": "r", "preserved_assertions": items, "removed_assertions": [], "new_source": new_src,
          "new_source_ast_sha256": sha256_text(ast_dump(parse_rewrite_source(new_src)))}
    op = {"id": "OP-X", "phase": 1, "kind": "rewrite", "path": "t.py",
          "locator": {"category": "def", "qualname": "test_p"}, "rewrite": rw}
    return check_3({"operations": [op]}, 1, _SrcHead(_POS_HEAD))


def test_mutation_check_3_preserved_assertion_position():
    """審查 r25 CODEX-R25-P1-01：保留斷言移入永不執行之分支、終止敘述之後、新外層或新 skip 裝飾器 ⇒ ③紅；
    只拿掉 frame 外層（縮排上移）或刪 for 字面中之 frame 元素 ⇒ ③綠。"""
    ok = "def test_p():\n    for name in ('cgsa',):\n        assert ok(name)\n    assert done()\n"
    assert _pos_errs(ok) == []
    kept_if = ("def test_p():\n    for name in ('cgsa',):\n        if name == 'frame':\n            pass\n"
               "        else:\n            assert ok(name)\n    assert done()\n")
    assert _pos_errs(kept_if) == []
    bad = {
        "if False": "def test_p():\n    for name in ('cgsa',):\n        assert ok(name)\n"
                    "    if False:\n        assert done()\n",
        "after return": "def test_p():\n    for name in ('cgsa',):\n        assert ok(name)\n"
                        "    return\n    assert done()\n",
        "after skip": "def test_p():\n    pytest.skip('x')\n    for name in ('cgsa',):\n        assert ok(name)\n"
                      "    assert done()\n",
        "new try": "def test_p():\n    for name in ('cgsa',):\n        assert ok(name)\n"
                    "    try:\n        assert done()\n    except AssertionError:\n        pass\n",
        "empty loop": "def test_p():\n    for name in ():\n        assert ok(name)\n    assert done()\n",
        "foreign loop item": "def test_p():\n    for name in ('other',):\n        assert ok(name)\n"
                             "    assert done()\n",
        "while False": "def test_p():\n    while False:\n        for name in ('cgsa',):\n            assert ok(name)\n"
                       "    assert done()\n",
        "inner def": "def test_p():\n    def _never():\n        for name in ('cgsa',):\n            assert ok(name)\n"
                     "    assert done()\n",
        "else to body": ("def test_p():\n    for name in ('cgsa',):\n        if name == 'frame':\n"
                         "            assert ok(name)\n    assert done()\n"),
        "skip marker": "@pytest.mark.skip\ndef test_p():\n    for name in ('cgsa',):\n        assert ok(name)\n"
                       "    assert done()\n",
    }
    for label, src in bad.items():
        assert _pos_errs(src) != [], label


def test_mutation_check_3_unlisted_removed_assertion_is_red():
    """審查 r30 CODEX-R30-P1-01：HEAD 兩個斷言、只列一個保留、改寫刪掉另一個而未列刪除 ⇒ ③紅；列入
    removed_assertions（行號、雜湊、理由）⇒ ③綠；刪除列雜湊錯、理由空、指向非斷言、與保留列重疊 ⇒ 紅。"""
    head = "def test_u():\n    x = run()\n    assert a(x)\n    assert_frame_equal(x, y)\n"
    tree = ast.parse(head)
    nodes = {n.lineno: n for n in ast.walk(tree) if isinstance(n, ast.stmt) and n.lineno in (2, 3, 4)}
    sha = {ln: sha256_text(ast_dump(n)) for ln, n in nodes.items()}
    new_src = "def test_u():\n    x = run()\n    assert a(x)\n"

    def errs(removed, preserved=(3,)):
        rw = {"reason": "r", "preserved_assertions": [{"lineno": ln, "ast_sha256": sha[ln]} for ln in preserved],
              "removed_assertions": removed, "new_source": new_src,
              "new_source_ast_sha256": sha256_text(ast_dump(parse_rewrite_source(new_src)))}
        op = {"id": "OP-U", "phase": 1, "kind": "rewrite", "path": "t.py",
              "locator": {"category": "def", "qualname": "test_u"}, "rewrite": rw}
        return check_3({"operations": [op]}, 1, _SrcHead(head))

    assert errs([]) != []
    assert errs([{"lineno": 4, "ast_sha256": sha[4], "reason": "frame 對照臂"}]) == []
    assert errs([{"lineno": 4, "ast_sha256": "0" * 64, "reason": "frame 對照臂"}]) != []
    assert errs([{"lineno": 2, "ast_sha256": sha[2], "reason": "非斷言"}]) != []
    assert errs([{"lineno": 3, "ast_sha256": sha[3], "reason": "重疊"},
                 {"lineno": 4, "ast_sha256": sha[4], "reason": "frame"}]) != []


def test_mutation_check_3_removed_assertion_residue_and_same_line_are_red():
    """審查 r31：同一行兩個斷言 ⇒ fail-closed（CODEX-R31-P1-01）；列為刪除之斷言殘留於改寫後（如 return 之後）
    ⇒ 紅（CODEX-R31-P1-02）。"""
    def run(head: str, new_src: str, preserved, removed) -> List[str]:
        tree = ast.parse(head)
        stmts = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.stmt) and not isinstance(n, ast.FunctionDef):
                stmts.setdefault(n.lineno, n)
        rw = {"reason": "r",
              "preserved_assertions": [{"lineno": ln, "ast_sha256": sha256_text(ast_dump(stmts[ln]))} for ln in preserved],
              "removed_assertions": [{"lineno": ln, "ast_sha256": sha256_text(ast_dump(stmts[ln])), "reason": "frame"}
                                     for ln in removed],
              "new_source": new_src, "new_source_ast_sha256": sha256_text(ast_dump(parse_rewrite_source(new_src)))}
        op = {"id": "OP-R", "phase": 1, "kind": "rewrite", "path": "t.py",
              "locator": {"category": "def", "qualname": "test_r"}, "rewrite": rw}
        return check_3({"operations": [op]}, 1, _SrcHead(head))

    same_line = "def test_r():\n    x = 1\n    assert a(); assert b()\n"
    assert run(same_line, "def test_r():\n    x = 1\n", [], [3]) != []
    two = "def test_r():\n    assert a()\n    assert b()\n"
    assert run(two, "def test_r():\n    assert a()\n", [2], [3]) == []
    assert run(two, "def test_r():\n    assert a()\n    return\n    assert b()\n", [2], [3]) != []
    assert run(two, "def test_r():\n    assert a()\n    assert b()\n", [2], [3]) != []


def test_mutation_check_3_method_rewrite_multiline_string_is_red():
    """v17 試作：類別方法改寫全文含多行 docstring ⇒ ③紅（縮排入類別後字串值改變，② 必不等）；單行 ⇒ 綠。"""
    head = "class TestK:\n    def test_m(self):\n        assert a()\n"
    item = [{"lineno": 3, "ast_sha256": sha256_text(ast_dump(ast.parse("assert a()").body[0]))}]

    def errs(new_src: str) -> List[str]:
        rw = {"reason": "r", "preserved_assertions": item, "removed_assertions": [], "new_source": new_src,
              "new_source_ast_sha256": sha256_text(ast_dump(parse_rewrite_source(new_src)))}
        op = {"id": "OP-K", "phase": 1, "kind": "rewrite", "path": "t.py",
              "locator": {"category": "def", "qualname": "TestK.test_m"}, "rewrite": rw}
        return check_3({"operations": [op]}, 1, _SrcHead(head))

    assert errs('def test_m(self):\n    """one line."""\n    assert a()\n') == []
    assert errs('def test_m(self):\n    """two\n    lines."""\n    assert a()\n') != []


def test_mutation_check_3_duplicate_preserved_assertions_need_one_to_one_match():
    """審查 r26 CODEX-R26-P1-01：HEAD 有兩個相同斷言且皆列保留，改寫只留一個 ⇒ ③紅；兩個都留 ⇒ ③綠。"""
    head = "def test_d():\n    value = run()\n    assert value\n    rerun()\n    assert value\n"
    tree = ast.parse(head)
    items = [{"lineno": n.lineno, "ast_sha256": sha256_text(ast_dump(n))}
             for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    assert len(items) == 2

    def errs(new_src: str) -> List[str]:
        rw = {"reason": "r", "preserved_assertions": items, "removed_assertions": [], "new_source": new_src,
              "new_source_ast_sha256": sha256_text(ast_dump(parse_rewrite_source(new_src)))}
        op = {"id": "OP-D", "phase": 1, "kind": "rewrite", "path": "t.py",
              "locator": {"category": "def", "qualname": "test_d"}, "rewrite": rw}
        return check_3({"operations": [op]}, 1, _SrcHead(head))

    assert errs("def test_d():\n    value = run()\n    assert value\n    rerun()\n    assert value\n") == []
    assert errs("def test_d():\n    value = run()\n    assert value\n    rerun()\n") != []


def test_mutation_rename_with_changed_fixture_is_red():
    ops = [_op("rename", {"category": "def", "qualname": "test_frame_only"}, new_name="test_cgsa_only")]
    good = _SAMPLE.replace("def test_frame_only():", "def test_cgsa_only():")
    bad = good.replace("assert frame() == 2", "assert frame(1) == 2")
    assert _eq(_SAMPLE, good, ops)
    assert not _eq(_SAMPLE, bad, ops)


def test_boundary_06_json_pointer_deletion_and_table_outside_edit():
    head = json.dumps([{"node": "a", "owner": "FRAMEPATH"}, {"node": "b", "owner": "X"}]).encode()
    ops = [{"kind": "delete-json-path", "pointer": "/0", "path": "t.json"}]
    good = json.dumps([{"node": "b", "owner": "X"}], indent=2).encode()
    bad = json.dumps([{"node": "b", "owner": "Y"}]).encode()
    assert expected_vs_current("t.json", head, good, ops) is None
    assert expected_vs_current("t.json", head, bad, ops) is not None
    assert expected_vs_current("t.json", head, good, []) is not None  # 表外刪一列 ⇒ 紅


def test_boundary_07_non_py_json_requires_replace_file():
    head = b"echo a\n"
    new = b"echo b\n"
    assert expected_vs_current("s.sh", head, new, []) is not None
    assert expected_vs_current("s.sh", head, new, [{"kind": "replace-file", "new_sha256": sha256_bytes(new)}]) is None


def test_boundary_08_delete_file_listed_but_not_deleted_is_red():
    assert expected_vs_current("g.json", b"{}", b"{}", [{"kind": "delete-file"}]) is not None
    assert expected_vs_current("g.json", b"{}", None, [{"kind": "delete-file"}]) is None


def test_mutation_unregistered_deletion_is_red_in_check_1():
    disp = {"nodeids": [{"nodeid": "t.py::a", "phase": 1, "disposition": "keep"},
                        {"nodeid": "t.py::b", "phase": 1, "disposition": "delete", "op": "O", "reason": "r"}]}
    assert check_1(disp, 1, {"t.py::a"}) == []
    assert check_1(disp, 1, set()) != []           # 刪一條未登記測試
    assert check_1(disp, 1, {"t.py::a", "t.py::b"}) != []  # 該刪未刪


def test_mutation_phase2_row_executed_in_phase1_is_red():
    disp = {"nodeids": [{"nodeid": "t.py::b", "phase": 2, "disposition": "delete", "op": "O", "reason": "r"}]}
    assert check_1(disp, 1, set()) != []
    assert check_1(disp, 2, set()) == []


def test_mutation_disposition_byte_change_is_red_in_check_0(ctx):
    recorded = manifest_contract_shas().get(DISPOSITION_REL)
    mutated = ctx["disp_bytes"] + b" "
    assert any("sha256" in e for e in check_0(ctx["disp"], mutated, recorded, ctx["head"], ctx["spec"]))


def test_mutation_kind_extension_mismatch_is_red():
    assert not kind_ext_ok("delete-node", "a.json")
    assert not kind_ext_ok("delete-node", "a.sh")
    assert not kind_ext_ok("replace-file", "a.py")
    assert kind_ext_ok("delete-file", "a.parquet")


def test_mutation_excerpt_hash_wrong_is_red_in_check_4(ctx):
    disp = copy.deepcopy(ctx["disp"])
    target = next((op for op in disp["operations"] if op["kind"] == "delete-json-path"), None)
    assert target is not None, "處置表須至少一筆 delete-json-path（allowed_red FRAMEPATH 列）"
    target["excerpt_sha256"] = "0" * 64
    assert any(target["id"] in e for e in check_4(disp, ctx["head"]))


def test_mutation_nodeid_marked_delete_without_op_cover_is_red():
    disp = {"nodeids": [{"nodeid": "t.py::a", "phase": 1, "disposition": "delete", "op": "O1", "reason": "r"}],
            "operations": [{"id": "O1", "phase": 1, "path": "t.py", "kind": "delete-file", "nodeids": [],
                            "excerpt_sha256": ""}]}

    class _H:
        def read(self, p):
            return None

    assert any("不含之" in e for e in check_4(disp, _H()))


def test_mutation_new_file_outside_list_is_red_in_check_5():
    disp = {"new_files": [{"path": "tests/feature_engineering/test_framepath_disposition.py", "phase": 1, "task": "1.5"}],
            "ignored_baseline": ["a.py"]}
    assert check_5(disp, 1, {"tests/feature_engineering/unlisted_probe.py"}, ["a.py"]) != []
    assert check_5(disp, 1, set(), ["a.py", "tests/x/ignored_new.py"]) != []
    assert check_5(disp, 1, {"tests/feature_engineering/test_framepath_disposition.py"}, ["a.py"]) == []
    # 列於 new_files（phase ≤ 本批）而缺檔 ⇒ 紅（審查 r24 CODEX-R24-P2-01）
    assert check_5(disp, 1, set(), ["a.py"], exists=lambda p: False) != []


def test_mutation_ignored_set_counts_only_files_since_anchor():
    """審查 r25 GROK-R25-P1-01（SPEC v16 A11）：錨點前即存在之本機被忽略檔不計；錨點後新增之被忽略 .py 計入
    ⇒ 與凍結基線（乾淨 worktree＝[]）不等即紅；*.bak 與 __pycache__ 仍不判。"""
    anchor = 1_000
    mt = {"frontend/src/components/results/Old.tsx": 10, "tests/x/ignored_new.py": 2_000,
          "tests/x/new.bak": 2_000, "tests/x/__pycache__/m.py": 2_000, "tests/x/at_anchor.json": anchor}
    got = ignored_since_anchor(mt, anchor, mtime=mt.__getitem__)
    assert got == ["tests/x/at_anchor.json", "tests/x/ignored_new.py"]
    disp = {"new_files": [], "ignored_baseline": []}
    assert check_5(disp, 1, set(), got) != []
    assert check_5(disp, 1, set(), ignored_since_anchor(["frontend/src/components/results/Old.tsx"], anchor,
                                                         mtime=mt.__getitem__)) == []


def test_ignored_baseline_frozen_from_clean_worktree():
    """乾淨 HEAD worktree 之過濾後被忽略集合為空 ⇒ 凍結基線須為 []（GROK-R25-P1-01）。"""
    assert load_json(DISPOSITION_REL)["ignored_baseline"] == []


def test_mutation_fact_keys_other_row_change_is_red_in_check_6():
    head = {"_schema": {}, "t": {"columns": ["序", "識別碼", "狀態"], "rows": [[1, "RM-FRAMEPATH", "a"], [2, "RM-X", "b"]]}}
    ok = copy.deepcopy(head)
    ok["t"]["rows"][0][2] = "z"
    bad = copy.deepcopy(head)
    bad["t"]["rows"][1][2] = "z"
    disp = {"fact_key_rows": [{"row_id": "RM-FRAMEPATH", "phase": 1}]}
    assert check_6(disp, 1, head, ok) == []
    assert check_6(disp, 1, head, bad) != []


def test_mutation_out_of_scope_rename_is_red_in_check_7():
    disp = {"population": {"files": ["tests/a.py"]}, "operations": [{"path": "tests/_golden/batch2d/control.json"}],
            "new_files": []}
    assert check_7(disp, {"tests/_fixtures/x.json", "tests/_fixtures/y.json"}) != []
    assert check_7(disp, {"tests/_golden/batch2d/control.json"}) == []
    assert check_7(disp, {FACT_KEYS_REL}) == []
    assert check_7(disp, {"tests/_fixtures/__pycache__/rolling_quantile_legacy.f-1.py39.nbi"}) == []
    assert check_7(disp, {"tests/_fixtures/pycache_lookalike.py"}) != []


def test_mutation_schema_rejects_unlisted_new_file_task_and_foreign_row(ctx):
    disp = copy.deepcopy(ctx["disp"])
    disp["new_files"].append({"path": "tests/feature_engineering/unlisted_probe.py", "phase": 1, "task": "1.2"})
    disp["fact_key_rows"].append({"row_id": "RM-FFNAME", "phase": 3})
    errs = schema_errors(disp, ctx["spec"])
    assert any("unlisted_probe" in e for e in errs)
    assert any("RM-FFNAME" in e for e in errs)


def test_mutation_non_monkeypatch_receiver_setenv_is_not_stripped():
    """SPEC (a) 只限 `monkeypatch.setenv／delenv`：其他 receiver（helper、mp 別名）之同鍵敘述不得被正規化吃掉。"""
    base = "def t(monkeypatch, other):\n    x = 1\n"
    for added in ('    other.setenv("FFACT_USE_CGSA", "1")\n', '    mp.delenv("FFACT_USE_CGSA")\n'):
        assert not _eq(base, base + added, [])
    assert _eq(base, base + '    monkeypatch.setenv("FFACT_USE_CGSA", "1")\n', [])


def test_mutation_strip_does_not_touch_other_keys():
    src = 'monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")\n'
    assert module_dump_normalized(ast.parse(src)) == ast_dump(ast.parse(src))
