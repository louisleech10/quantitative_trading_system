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


GIT_PREFIX = ("git", "-c", "core.quotepath=off")  # 審查 r46：路徑輸出一律不跳脫（非 ASCII 路徑原樣）


def _git(*args: str, check: bool = True, repo: Path = REPO) -> bytes:
    proc = subprocess.run([*GIT_PREFIX, *args], cwd=repo, capture_output=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')}")
    return proc.stdout


class HeadReader:
    """HEAD 6e07e0ad 之檔內容讀取（`git cat-file`，結果快取）。`repo` 供 mutation 之暫存 git repo 使用（SPEC v22 D11）。"""

    def __init__(self, commit: str, repo: Path = REPO) -> None:
        self.commit = commit
        self.repo = repo
        self._cache: Dict[str, Optional[bytes]] = {}
        self._types: Dict[str, Optional[str]] = {}

    def obj_type(self, path: str) -> Optional[str]:
        if path not in self._types:
            proc = subprocess.run(["git", "cat-file", "-t", f"{self.commit}:{path}"], cwd=self.repo, capture_output=True)
            self._types[path] = proc.stdout.decode().strip() if proc.returncode == 0 else None
        return self._types[path]

    def read(self, path: str) -> Optional[bytes]:
        if path not in self._cache:
            if self.obj_type(path) != "blob":
                self._cache[path] = None
            else:
                self._cache[path] = _git("cat-file", "blob", f"{self.commit}:{path}", repo=self.repo)
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
# SPEC v22 D11.2：選填之重錨紀錄 {治理檔 path: {"base_commit": 40hex, "foreign_commits": [40hex, …]}}——該檔 ② 之期望
# 改以 base_commit 版位元組＋同一操作計算（操作之定位與摘錄仍對錨點 6e07e0ad 解析）；由產生器 --rebase 寫入
OPTIONAL_TOP_KEYS = {"rebase"}
REBASE_ENTRY_KEYS = {"base_commit", "foreign_commits"}
_SHA40_RE = re.compile(r"[0-9a-f]{40}")


def rebase_schema_errors(disp: Dict[str, Any]) -> List[str]:
    rb = disp.get("rebase")
    if rb is None:
        return []
    if not isinstance(rb, dict):
        return ["rebase 須為物件 {path: {base_commit, foreign_commits}}"]
    errs: List[str] = []
    governed = set(governed_files(disp))
    for path, ent in rb.items():
        if path not in governed:
            errs.append(f"rebase {path!r} 不在治理檔（母體 ∪ 操作表 path）")
        if not isinstance(ent, dict) or set(ent) != REBASE_ENTRY_KEYS:
            errs.append(f"rebase {path!r} 欄位須恰為 {sorted(REBASE_ENTRY_KEYS)}")
            continue
        if not (isinstance(ent["base_commit"], str) and _SHA40_RE.fullmatch(ent["base_commit"])):
            errs.append(f"rebase {path!r} base_commit 須為 40 位小寫十六進位")
        fc = ent["foreign_commits"]
        if not (isinstance(fc, list) and fc and all(isinstance(c, str) and _SHA40_RE.fullmatch(c) for c in fc)):
            errs.append(f"rebase {path!r} foreign_commits 須為非空之 40 位提交編號陣列")
    return errs


def schema_errors(disp: Dict[str, Any], spec_text: str) -> List[str]:
    """處置表封閉 schema（SPEC 驗證⑤⑥之三清單 schema 與 nodeid 表／操作表必填欄）。"""
    errs: List[str] = []
    if not TOP_KEYS <= set(disp) <= TOP_KEYS | OPTIONAL_TOP_KEYS:
        errs.append(f"頂層鍵不符：多 {sorted(set(disp) - TOP_KEYS - OPTIONAL_TOP_KEYS)} 缺 {sorted(TOP_KEYS - set(disp))}")
        return errs
    errs += rebase_schema_errors(disp)
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


# ---------------------------------------------------------------------------
# SPEC v22 D11.2：重錨（他票改過之治理檔以他票最近改動後版本為新基準）與衝突檢查
# ---------------------------------------------------------------------------

WHOLE_FILE_KINDS = ("replace-file", "delete-file")


def _top_key(stmt: ast.stmt) -> Tuple[str, str]:
    """模組層敘述之歸屬鍵：函式／類別＝名稱；其餘＝整句傾印（任何改動即成「刪一句＋增一句」）。"""
    if isinstance(stmt, _DEF_TYPES):
        return ("def", stmt.name)
    return ("stmt", ast_dump(stmt))


def _top_groups(tree: ast.Module) -> Dict[Tuple[str, str], List[str]]:
    groups: Dict[Tuple[str, str], List[str]] = {}
    for stmt in tree.body:
        groups.setdefault(_top_key(stmt), []).append(ast_dump(stmt))
    return groups


def touched_top_keys(anchor_tree: ast.Module, base_tree: ast.Module) -> Set[Tuple[str, str]]:
    """錨點→基準之間有改動之頂層定義（Python AST 節點）：同鍵之敘述傾印序列不同者（新增、刪除、改寫皆計）。"""
    a, b = _top_groups(anchor_tree), _top_groups(base_tree)
    return {k for k in set(a) | set(b) if a.get(k) != b.get(k)}


def _top_level_of(tree: ast.Module, node: ast.AST) -> ast.stmt:
    for stmt in tree.body:
        if any(n is node for n in ast.walk(stmt)):
            return stmt
    raise LocatorError("目標不在任一模組層敘述內")


def json_touched_pointers(a: Any, b: Any, prefix: Tuple[str, ...] = ()) -> List[Tuple[str, ...]]:
    """兩 JSON 文件之差異位置（token 序列）：dict 逐鍵下探；list 長度不同即整個 list 計為改動（索引位移保守處理）。"""
    if isinstance(a, dict) and isinstance(b, dict):
        out: List[Tuple[str, ...]] = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(prefix + (k,))
            else:
                out += json_touched_pointers(a[k], b[k], prefix + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += json_touched_pointers(x, y, prefix + (str(i),))
        return out
    return [] if canonical_json(a) == canonical_json(b) else [prefix]


def rebase_conflicts(path: str, anchor_b: Optional[bytes], base_b: Optional[bytes],
                     ops: Sequence[Dict[str, Any]]) -> List[str]:
    """衝突檢查：他票自錨點至新基準之改動所觸之頂層定義（Python）或 JSON pointer，與本票對該檔任一操作（不分 phase）之
    目標相交 ⇒ 列出（fail-closed，須重新處置並經審查；不得以「操作不變」放行）。整檔操作、檔於任一側不存在、無法解析
    皆視為相交。"""
    if anchor_b is None or base_b is None:
        return [f"{path}：錨點或基準不存在此檔"]
    if anchor_b == base_b:
        return []
    errs: List[str] = []
    for op in ops:
        if op["kind"] in WHOLE_FILE_KINDS:
            errs.append(f"{path}：{op['id']}（{op['kind']}）為整檔操作，他票已改此檔")
    ext = ext_of(path)
    if ext == ".py":
        py_ops = [op for op in ops if op["kind"] in PY_KINDS]
        if not py_ops:
            return errs
        try:
            a_tree, b_tree = ast.parse(anchor_b.decode("utf-8")), ast.parse(base_b.decode("utf-8"))
        except SyntaxError as exc:
            return errs + [f"{path}：無法解析（{exc}）"]
        touched = touched_top_keys(a_tree, b_tree)
        for op in py_ops:
            try:
                top = _top_level_of(a_tree, resolve_locator(a_tree, op["kind"], op["locator"]).node)
            except LocatorError as exc:
                errs.append(f"{path}：{op['id']} 於錨點無法定位（{exc}）")
                continue
            if _top_key(top) in touched:
                errs.append(f"{path}：他票改動之頂層定義 {_top_key(top)[1][:80]!r} 與 {op['id']}（{op['kind']}）之目標相交")
    elif ext == ".json":
        pointers = [op for op in ops if op["kind"] == "delete-json-path"]
        if not pointers:
            return errs
        try:
            touched_ptrs = json_touched_pointers(json.loads(anchor_b), json.loads(base_b))
        except ValueError as exc:
            return errs + [f"{path}：JSON 無法解析（{exc}）"]
        for op in pointers:
            tgt = tuple(_pointer_tokens(op["pointer"]))
            for t in touched_ptrs:
                if t[: len(tgt)] == tgt or tgt[: len(t)] == t:
                    errs.append(f"{path}：他票改動之 JSON pointer /{'/'.join(t)} 與 {op['id']} 之 {op['pointer']} 相交")
                    break
    return errs


def _node_path(root: ast.AST, target: ast.AST) -> Optional[List[Tuple[str, Optional[int]]]]:
    if root is target:
        return []
    for field, val in ast.iter_fields(root):
        items = [(i, x) for i, x in enumerate(val)] if isinstance(val, list) else [(None, val)]
        for i, child in items:
            if isinstance(child, ast.AST):
                sub = _node_path(child, target)
                if sub is not None:
                    return [(field, i)] + sub
    return None


def _follow(root: ast.AST, steps: Sequence[Tuple[str, Optional[int]]]) -> ast.AST:
    node = root
    for field, i in steps:
        val = getattr(node, field)
        node = val[i] if i is not None else val
    return node


def rebase_ops(anchor_src: str, base_src: str, ops: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把對錨點解析之 Python 操作轉成對基準之同一操作：目標所在頂層敘述於兩側傾印相同（衝突檢查保證），沿同一 AST
    結構路徑取基準之對應節點，行號類定位（stmt、import_alias）改用基準行號；轉換後於基準重新解析須得同一摘錄傾印，
    否則 LocatorError（fail-closed）。非 Python 操作原樣回傳。"""
    a_tree, b_tree = ast.parse(anchor_src), ast.parse(base_src)
    b_groups: Dict[Tuple[str, str], List[ast.stmt]] = {}
    for stmt in b_tree.body:
        b_groups.setdefault(_top_key(stmt), []).append(stmt)
    out: List[Dict[str, Any]] = []
    for op in ops:
        if op["kind"] not in PY_KINDS:
            out.append(op)
            continue
        t = resolve_locator(a_tree, op["kind"], op["locator"])
        top = _top_level_of(a_tree, t.node)
        key = _top_key(top)
        same = [s for s in a_tree.body if _top_key(s) == key]
        cands = b_groups.get(key, [])
        if len(cands) != len(same) or any(ast_dump(x) != ast_dump(y) for x, y in zip(same, cands)):
            raise LocatorError(f"{op['id']}：目標所在頂層定義於基準已改（應先過衝突檢查）")
        b_top = cands[[i for i, s in enumerate(same) if s is top][0]]
        anchor_node = t.container if t.action == "remove_alias" else t.node
        b_node = _follow(b_top, _node_path(top, anchor_node) or [])
        loc = dict(op["locator"])
        if loc.get("category") == "stmt":
            loc["lineno"], loc["end_lineno"] = b_node.lineno, b_node.end_lineno
        elif loc.get("category") == "import_alias":
            loc["lineno"] = b_node.lineno
        new_op = dict(op, locator=loc)
        if resolve_locator(b_tree, op["kind"], loc).excerpt_dump() != t.excerpt_dump():
            raise LocatorError(f"{op['id']}：於基準重新定位之摘錄與錨點不同")
        out.append(new_op)
    return out


def _foreign_hint(path: str, foreign_touched: Set[str]) -> str:
    return "（此檔錨點以來曾被他票改過：須以產生器 --rebase 重錨，見 SPEC v22 D11.2）" if path in foreign_touched else ""


def check_2(disp: Dict[str, Any], phase: int, head: HeadReader,
            current_reader=current_bytes, foreign_only: Optional[Iterable[str]] = None,
            read_at=None, foreign_touched: Optional[Iterable[str]] = None) -> List[str]:
    """②（SPEC v22 D11.2）：
    - 「只被他票提交改過、未被本票提交改過、且工作樹相對 HEAD 未改」（`foreign_only`，D11.1 定義）且本批 E 無該檔操作者
      不比對（E 有該檔操作者仍比對——本票之操作未執行不得因他票碰過該檔而放行）；
    - 處置表 `rebase` 有該檔者：先做衝突檢查（全部 phase 之操作），相交即紅；不相交 ⇒ 期望＝基準提交之位元組＋E 之同一
      操作（定位經 `rebase_ops` 轉換）；
    - 其餘：期望＝錨點位元組＋E 之操作（原規則）。
    `foreign_only`／`foreign_touched` 未給（None）⇒ 以本 repo 之 git 歷史計算（mutation 測試以暫存 repo 明給）。"""
    e_ops = ops_in(disp, phase)
    skip = set(foreign_only_paths() if foreign_only is None else foreign_only)
    touched = set(foreign_and_ticket_paths()[0] if foreign_touched is None else foreign_touched)
    rebase = disp.get("rebase") or {}
    read_at = read_at or _git_show_bytes
    errs = []
    for path in governed_files(disp):
        file_ops = [op for op in e_ops if op["path"] == path]
        if path in skip and not file_ops:
            continue
        cur = current_reader(path)
        ent = rebase.get(path)
        if ent is None:
            diff = expected_vs_current(path, head.read(path), cur, file_ops)
            if diff:
                errs.append(f"② {path}：{diff}{_foreign_hint(path, touched)}")
            continue
        anchor_b, base_b = head.read(path), read_at(ent["base_commit"], path)
        conflicts = rebase_conflicts(path, anchor_b, base_b, [op for op in disp["operations"] if op["path"] == path])
        if conflicts:
            errs += [f"② 重錨衝突（fail-closed）：{c}" for c in conflicts]
            continue
        try:
            ops = rebase_ops(anchor_b.decode("utf-8"), base_b.decode("utf-8"), file_ops) \
                if ext_of(path) == ".py" and any(op["kind"] in PY_KINDS for op in file_ops) else file_ops
        except (SyntaxError, LocatorError) as exc:
            errs.append(f"② {path}：重錨後無法定位操作（{exc}）")
            continue
        diff = expected_vs_current(path, base_b, cur, ops)
        if diff:
            errs.append(f"② {path}（基準 {ent['base_commit'][:8]}）：{diff}（若他票於基準後又改此檔，須再重錨）")
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


# SPEC v22 D11.1：本票提交＝`Ticket-Batch` 附註之 root（`/` 前）等於 TICKET_ROOT，或 `Governance-Scope` 附註值以空白
# 切分後第二個 token 等於 FRAMEPATH（第一個 token 恆為 `out-of-epic`）；標題與附註內文之子字串一律不計（取代 D10①）。
# 同一附註鍵有多值時以 \x1e 分隔（不用 `;`，免與附註內文混淆）。
TICKET_GS_TOKEN = "FRAMEPATH"
_LOG_FMT = ("%x00%H%x1f%s%x1f%(trailers:key=Ticket-Batch,valueonly,separator=%x1e)"
            "%x1f%(trailers:key=Governance-Scope,valueonly,separator=%x1e)")


def is_ticket_commit(ticket_batch: str, governance_scope: str) -> bool:
    """D11.1 之本票提交判定（只看兩個結構化附註之封閉 token）。"""
    if any(v.strip().split("/", 1)[0].strip() == TICKET_ROOT for v in ticket_batch.split("\x1e")):
        return True
    return any(len(v.split()) >= 2 and v.split()[1] == TICKET_GS_TOKEN for v in governance_scope.split("\x1e"))


def parse_commit_log(log_text: str) -> List[Tuple[str, bool, Set[str]]]:
    """`git log --format=_LOG_FMT --name-only` 之輸出 → 依輸出序之 (提交, 是否本票提交, 所改路徑)。"""
    out: List[Tuple[str, bool, Set[str]]] = []
    for block in log_text.split("\x00")[1:]:
        head, _, files = block.partition("\n")
        fields = (head.split("\x1f") + ["", "", "", ""])[:4]
        paths = {p for p in files.splitlines() if p.strip()}
        out.append((fields[0].strip(), is_ticket_commit(fields[2], fields[3]), paths))
    return out


def split_commit_paths(log_text: str) -> Tuple[Set[str], Set[str]]:
    """`git log --format=_LOG_FMT --name-only` 之輸出 → (本票提交所改路徑, 他票提交所改路徑)；本票提交依 D11.1。"""
    ticket: Set[str] = set()
    foreign: Set[str] = set()
    for _sha, mine, paths in parse_commit_log(log_text):
        (ticket if mine else foreign).update(paths)
    return ticket, foreign


def commit_log(repo: Path = REPO, rev_range: Optional[str] = None, *paths: str, reverse: bool = False) -> str:
    args = ["log", f"--format={_LOG_FMT}", "--name-only", *(["--reverse"] if reverse else []),
            rev_range or f"{HEAD_SHORT}..HEAD", "--", *paths]
    return _git(*args, repo=repo).decode("utf-8", "replace")


def foreign_and_ticket_paths(repo: Path = REPO, anchor: str = HEAD_SHORT) -> Tuple[Set[str], Set[str]]:
    """錨點至 HEAD 間 (他票提交所改路徑, 本票提交所改路徑)。"""
    ticket, foreign = split_commit_paths(commit_log(repo, f"{anchor}..HEAD"))
    return foreign, ticket


def foreign_only_paths(repo: Path = REPO, anchor: str = HEAD_SHORT) -> Set[str]:
    """實作期 b1（並行他票提交）：錨點 6e07e0ad 至 HEAD 間只被他票提交改過、未被本票提交改過、且工作樹相對 HEAD
    未改之路徑——他票之正常提交（如 Javis 信箱工具）不屬本票範圍，自 ⑤(a)／⑦ 之「錨點以來改動」中排除、② 不比對
    （SPEC v22 D11.2）；本票提交或工作樹（本批未提交改動）碰到者一律照常受檢。本票提交之辨識依 D11.1。"""
    foreign, ticket = foreign_and_ticket_paths(repo, anchor)
    wt = {p for p in _git("diff", "--name-only", "HEAD", repo=repo).decode().splitlines() if p}
    wt |= {p for p in _git("ls-files", "--others", "--exclude-standard", repo=repo).decode().splitlines() if p}
    return foreign - ticket - wt


def rebase_history_errors(disp: Dict[str, Any], repo: Path = REPO, anchor: str = HEAD_SHORT) -> List[str]:
    """處置表 `rebase` 每列（D11.2）須對得上 git 歷史：基準為錨點之後代；錨點至基準間改過該檔之提交恰為所記之
    foreign_commits（依時間序）且全為他票提交（D11.1）——重錨不得吸收本票自己之改動。"""
    errs: List[str] = []
    for path, ent in (disp.get("rebase") or {}).items():
        base = ent["base_commit"]
        if subprocess.run(["git", "merge-base", "--is-ancestor", anchor, base], cwd=repo,
                          capture_output=True).returncode != 0:
            errs.append(f"② rebase {path}：基準 {base[:8]} 非錨點 {anchor} 之後代")
            continue
        hist = [(sha, mine) for sha, mine, paths in parse_commit_log(commit_log(repo, f"{anchor}..{base}", path,
                                                                                  reverse=True)) if path in paths]
        mine = [sha[:8] for sha, m in hist if m]
        if mine:
            errs.append(f"② rebase {path}：錨點至基準間有本票提交改此檔 {mine}（重錨只准吸收他票改動）")
        if [sha for sha, _ in hist] != ent["foreign_commits"]:
            errs.append(f"② rebase {path}：所記 foreign_commits 與錨點至基準之改檔提交不符")
    return errs


def git_added_and_untracked() -> Set[str]:
    added = _git("diff", "--name-status", "--diff-filter=A", HEAD_SHORT, "--", *R_ROOTS).decode().splitlines()
    out = {line.split("\t", 1)[1] for line in added if "\t" in line} - foreign_only_paths()
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


# SPEC v22 D11.9：`plaindocs-index` 表無識別碼欄；本票提交（與工作樹）另准增刪「白話審閱文件路徑位於 白話說明/ 且檔名
# 以 FRAMEPATH 起首」之列（連結欄為 Markdown 連結，相對於該表 target〔白話說明/README.md〕所在目錄解析）；他列照舊。
PLAINDOCS_INDEX_KEY = "plaindocs-index"
PLAINDOCS_DIR = "白話說明"
PLAINDOCS_LINK_COL = "打開這份"
PLAINDOCS_TICKET_PREFIX = "FRAMEPATH"
_MD_LINK_RE = re.compile(r"\[[^\]\n]*\]\(([^()\s]+)\)")


def is_ticket_plaindoc_row(table: Dict[str, Any], row: Any) -> bool:
    import posixpath

    cols = table.get("columns")
    if not (isinstance(cols, list) and PLAINDOCS_LINK_COL in cols and isinstance(row, list)):
        return False
    ci = cols.index(PLAINDOCS_LINK_COL)
    cell = row[ci] if len(row) > ci else None
    m = _MD_LINK_RE.fullmatch(cell.strip()) if isinstance(cell, str) else None
    if m is None or m.group(1).startswith("/") or "\\" in m.group(1) or ":" in m.group(1):
        return False
    target = table.get("target")
    base = posixpath.dirname(target[0]) if isinstance(target, list) and len(target) == 1 and isinstance(target[0], str) \
        else PLAINDOCS_DIR
    full = posixpath.normpath(posixpath.join(base, m.group(1)))
    return full.startswith(PLAINDOCS_DIR + "/") and posixpath.basename(full).startswith(PLAINDOCS_TICKET_PREFIX)


def _without_ticket_plaindocs(doc: Dict[str, Any]) -> Dict[str, Any]:
    table = doc.get(PLAINDOCS_INDEX_KEY)
    if not (isinstance(table, dict) and isinstance(table.get("rows"), list)):
        return doc
    out = copy.deepcopy(doc)
    out[PLAINDOCS_INDEX_KEY]["rows"] = [r for r in table["rows"] if not is_ticket_plaindoc_row(table, r)]
    return out


def check_6(disp: Dict[str, Any], phase: int, head_doc: Dict[str, Any], cur_doc: Dict[str, Any],
            label: str = "HEAD→現行") -> List[str]:
    """單段改動（before＝head_doc、after＝cur_doc；⑥ 只餵本票提交與工作樹之段，D11.3）只得觸及 fact_key_rows（phase ≤
    本批）所列之列，及 D11.9 之本票白話審閱索引列。"""
    allowed = {item["row_id"] for item in disp["fact_key_rows"] if item["phase"] <= phase}
    head_doc, cur_doc = _without_ticket_plaindocs(head_doc), _without_ticket_plaindocs(cur_doc)
    if canonical_json(_fact_rows_without(head_doc, allowed)) != canonical_json(_fact_rows_without(cur_doc, allowed)):
        return [f"⑥ scripts/fact_keys.json 於 fact_key_rows（phase ≤ {phase}）以外之列有改動（{label}）"]
    return []


def _json_at(repo: Path, rev: str, rel: str) -> Dict[str, Any]:
    proc = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=repo, capture_output=True)
    return json.loads(proc.stdout) if proc.returncode == 0 else {}


def ticket_revisions(rel: str, repo: Path = REPO, anchor: str = HEAD_SHORT,
                     current_reader=None) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    """SPEC v22 D11.3 之逐提交歸屬（JSON 檔 `rel`）：每一本票提交（D11.1）改動該檔者取 `commit^→commit`，末項為
    `HEAD→工作樹`；他票提交之改動不計（不比錨點與現行之淨差——本票改越界列後被他票改回仍紅）。回傳 [(標籤, before, after)]。"""
    out: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    for sha, mine, paths in parse_commit_log(commit_log(repo, f"{anchor}..HEAD", reverse=True)):
        if mine and rel in paths:
            out.append((f"本票提交 {sha[:8]}：commit^→commit", _json_at(repo, f"{sha}^", rel), _json_at(repo, sha, rel)))
    cur = (current_reader or (lambda r: json.loads((repo / r).read_text(encoding="utf-8"))))(rel)
    out.append(("HEAD→工作樹", _json_at(repo, "HEAD", rel), cur))
    return out


def fact_key_revisions(repo: Path = REPO, anchor: str = HEAD_SHORT,
                       current_reader=None) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    """⑥（SPEC v22 D11.3）：scripts/fact_keys.json 之逐本票提交與工作樹改動段。"""
    return ticket_revisions(FACT_KEYS_REL, repo, anchor, current_reader)


def check_6_revisions(disp: Dict[str, Any], phase: int,
                      revisions: Sequence[Tuple[str, Dict[str, Any], Dict[str, Any]]]) -> List[str]:
    """SPEC v25 D17：本票提交段之越界改動，若其後某本票提交段恰為其逐字還原（後段 before＝前段 after、後段 after＝前段
    before，皆以「扣 fact_key_rows 與本票白話索引列」之越界視圖比），兩段合併為淨零不計；工作樹段不得作還原段；他票改回
    不在 revisions 內，仍紅（D11.3 不變）。"""
    allowed = {item["row_id"] for item in disp["fact_key_rows"] if item["phase"] <= phase}

    def view(doc: Dict[str, Any]) -> str:
        return canonical_json(_fact_rows_without(_without_ticket_plaindocs(doc), allowed))

    views = [(label, view(before), view(after)) for label, before, after in revisions]
    cleared: Set[int] = set()
    for i, (label_i, b_i, a_i) in enumerate(views):
        if b_i == a_i or i in cleared or label_i == "HEAD→工作樹":
            continue
        for j in range(i + 1, len(views)):
            label_j, b_j, a_j = views[j]
            if label_j != "HEAD→工作樹" and j not in cleared and b_j == a_i and a_j == b_i:
                cleared |= {i, j}
                break
    errs: List[str] = []
    for k, (label, before, after) in enumerate(revisions):
        if k not in cleared:
            errs += check_6(disp, phase, before, after, label)
    return errs


def git_changed_paths() -> Set[str]:
    out: Set[str] = set()
    for line in _git("diff", "--name-status", "-M", HEAD_SHORT, "--", *DIFF_ROOTS).decode().splitlines():
        parts = line.split("\t")
        out.update(p for p in parts[1:] if p)
    return out - foreign_only_paths()


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


def check_7_live_doc(head_doc: Dict[str, Any], cur_doc: Dict[str, Any], label: str = "HEAD→現行") -> List[str]:
    errs = _live_doc_ticket_row_errors(cur_doc)
    if canonical_json(_live_doc_without_ticket_rows(head_doc)) != canonical_json(_live_doc_without_ticket_rows(cur_doc)):
        errs.append(f"⑦ {LIVE_DOC_REGISTRY_REL} 於本票文件 exact 列以外有改動（{label}）")
    return errs


def check_7_live_doc_revisions(revisions: Sequence[Tuple[str, Dict[str, Any], Dict[str, Any]]]) -> List[str]:
    """活文件登記表之逐本票提交歸屬（SPEC v22 D11.1／D11.3 同構推及 ⑦：他票提交之改動〔他票登記自身 SPEC 列〕不計，
    本票提交與工作樹之改動只准本票文件 exact 列）。"""
    errs: List[str] = []
    for label, before, after in revisions:
        errs += check_7_live_doc(before, after, label)
    return errs


# SPEC v22 D11.7：collect-only 時 `tests/conftest.py`（pytest_collection_modifyitems → scripts/build_l65_golden.py
# write_test_inventory_from_nodeids）改寫之已追蹤清冊——與受影響測試閘 GENERATED_TRACKED（D10②）同一檔。⑦ 不無條件
# 豁免：改動之內容須等於以現行樹 collect 重產之結果（collect 副作用免報、手動竄改仍抓）。
GENERATED_INVENTORY_REL = "tests/golden/l65/test_inventory.txt"
INVENTORY_EMPTY = b"BLOCKER: no L6.5/preprocessing tests collected\n"  # 生成器於收集不到相關 nodeid 時之輸出
INVENTORY_COLLECT_TIMEOUT = 600


def regenerate_inventory(files: Sequence[str], repo: Path = REPO) -> bytes:
    """以現行樹 collect-only 收集 `files`（同 D10② 之生成規則：由 conftest 之 collection hook 寫出清冊）並回傳寫出之
    位元組；呼叫前之清冊位元組於結束時原樣寫回（不留副作用）。collect 失敗 ⇒ RuntimeError。"""
    inv = repo / GENERATED_INVENTORY_REL
    saved = inv.read_bytes() if inv.is_file() else None
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=--import-mode=importlib",
             "-p", "no:cacheprovider", *files], cwd=repo, capture_output=True, text=True,
            timeout=INVENTORY_COLLECT_TIMEOUT)
        if proc.returncode != 0:
            raise RuntimeError(f"collect rc={proc.returncode}：{proc.stdout[-800:]}{proc.stderr[-400:]}")
        return inv.read_bytes()
    finally:
        if saved is None:
            if inv.exists():
                inv.unlink()  # 呼叫前不存在 ⇒ 撤除本次 collect 寫出者
        else:
            inv.write_bytes(saved)


def inventory_integrity_errors(content: Optional[bytes], regenerate=regenerate_inventory,
                               head_content: Optional[bytes] = None) -> List[str]:
    """清冊生成物完整性（D11.7）：現行內容須等於「collect 其所列檔」重產之結果；每行須為 `檔::名` 之 nodeid（生成器之
    輸出形態）。全空收集之生成輸出（INVENTORY_EMPTY）只在「HEAD 版清冊亦為空標記（或不存在）」或「以 HEAD 版所列檔
    collect 重產確為空」時視為生成物（審查 r63 CODEX-R63-P1-01：非空清冊被換成空標記不得無條件放行）。"""
    if content is None:
        return [f"⑦ {GENERATED_INVENTORY_REL} 被刪除（生成物不得刪）"]
    if content == INVENTORY_EMPTY:
        if head_content is None or head_content == INVENTORY_EMPTY:
            return []
        head_files = sorted({ln.split("::", 1)[0] for ln in head_content.decode("utf-8", "replace").splitlines()
                             if "::" in ln})
        try:
            regenerated = regenerate(head_files)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            return [f"⑦ {GENERATED_INVENTORY_REL} 為空標記而 HEAD 版所列檔無法 collect 重產：{str(exc)[:300]}"]
        if regenerated != INVENTORY_EMPTY:
            return [f"⑦ {GENERATED_INVENTORY_REL} 被換成空集合標記，而以 HEAD 版所列檔 collect 重產非空（手動改動？）"]
        return []
    lines = content.decode("utf-8", "replace").splitlines()
    if not lines or any("::" not in ln or ln != ln.strip() for ln in lines):
        return [f"⑦ {GENERATED_INVENTORY_REL} 含非 nodeid 行（非生成器輸出形態）"]
    files = sorted({ln.split("::", 1)[0] for ln in lines})
    try:
        regenerated = regenerate(files)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        return [f"⑦ {GENERATED_INVENTORY_REL} 所列檔無法 collect 重產：{str(exc)[:300]}"]
    if regenerated != content:
        return [f"⑦ {GENERATED_INVENTORY_REL} 與以現行樹 collect 重產之結果不等（手動改動？）"]
    return []


def inventory_check_current(path: str) -> List[str]:
    return inventory_integrity_errors(current_bytes(path), head_content=_git_show_bytes("HEAD", path))


def check_7(disp: Dict[str, Any], changed: Set[str], inventory_check=inventory_check_current) -> List[str]:
    """⑦：既有檔改動須在母體 ∪ 操作表 ∪ new_files。collect 清冊（D11.7）於改動時改走 `inventory_check(path)`（回傳
    錯誤清單；預設＝現行內容之生成物完整性檢查）；明給 None ⇒ 照一般路徑計越界（不豁免）。"""
    allowed = set(governed_files(disp)) | {item["path"] for item in disp["new_files"]}
    exempt = {FACT_KEYS_REL, LIVE_DOC_REGISTRY_REL}  # 前者由⑥、後者由 check_7_live_doc 裁決
    errs: List[str] = []
    if inventory_check is not None and GENERATED_INVENTORY_REL in changed:
        exempt.add(GENERATED_INVENTORY_REL)
        errs += inventory_check(GENERATED_INVENTORY_REL)
    # 已追蹤之 numba／位元組碼快取（`__pycache__/`，任一測試執行即改寫；同⑤(b) 之過濾，SPEC v16 A5）
    bad = sorted(p for p in changed if p not in exempt and p not in allowed and "__pycache__/" not in p)
    return errs + ([f"⑦ 既有檔改動不在母體 ∪ 操作表 ∪ new_files：{bad}"] if bad else [])


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


# FRAMEPATH 收案（ec89a695）後退役（TESTREG SPEC v53 Task 4.4 子批①；遷移期驗證於遷移完成後移除）：
# 以錨點位元組／AST 約束治理檔與錨點以來歷史之真實 repo 檢查——test_check_0_disposition_view_bound_to_table、
# test_check_0_frozen_since_approval_anchor、test_check_0_history_freeze_order、test_check_1_collect_difference、
# test_check_2_per_file_expected、test_check_3_rewrite_keeps_assertions、test_check_0_frozen_acceptance_tests_unchanged
# （凍結驗收檔位元組）。收案時 check_2 綠之紀錄：handoffs/run_receipts/testreg_probes/b5/check2_head.log。
# 其判定函式與 mutation 測試保留。


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


def approval_permits(audit_lines: Iterable[str]) -> List[str]:
    """審計紀錄中本票（root 恰為 TICKET_ROOT）全部實作許可 `impl_token_issued` 之 round_start_head（依紀錄序）。"""
    out: List[str] = []
    for line in audit_lines:
        if '"impl_token_issued"' not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("event") == "impl_token_issued" and ev.get("root") == TICKET_ROOT \
                and re.fullmatch(r"[0-9a-f]{40}", str(ev.get("round_start_head", ""))):
            out.append(ev["round_start_head"])
    return out


def _audit_permits() -> List[str]:
    p = REPO / AUDIT_REL
    return approval_permits(p.read_text(encoding="utf-8", errors="replace").splitlines()) if p.is_file() else []


def git_is_ancestor(a: str, b: str, repo: Path = REPO) -> bool:
    """a 為 b 之祖先或相同（`git merge-base --is-ancestor`）；任一不存在 ⇒ False。"""
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=repo, capture_output=True).returncode == 0


def history_errors(commits_after_anchor: Sequence[Tuple[str, Set[str]]], frozen: Sequence[str],
                   baseline: str = BASELINE_REL, permits: Optional[Sequence[str]] = None,
                   is_ancestor=git_is_ancestor) -> List[str]:
    """git 歷史之凍結次序（審查 r23 CODEX-R23-P1-01／P1-02）。`commits_after_anchor`＝錨點之後依時間序之
    (commit, 該提交改動之路徑集合)。規則：①（SPEC v22 D11.8 核定期）首個改動生產碼（momentum／api／config）之提交之後
    （含該提交）改動 `frozen`（四支驗收測試與 manifest）之提交 c，須被其後之本票實作許可涵蓋——存在許可 P（`permits`＝
    審計紀錄 impl_token_issued 之 round_start_head）為 c 之後代（或相同），且 c 與 P 之間（不含 c、含 P）無生產碼提交
    （修訂未核定前不得實作下一批）；同一提交混改生產碼與凍結檔者一律紅（無從先核定）；②基準檔之每一次加入或改動皆須
    在首個生產碼提交之前（不得同一提交混改）。
    實作期 r43（SPEC v19 D2）：原 ②「加入後不得再改」使錨點碼態下之補格重凍（同碼態、無生產改動）亦恆紅；生產碼開始改動後
    仍一律禁改。`permits` 未給（None）⇒ 讀本 repo 之 `.claude/gate/audit.log`。"""
    errs: List[str] = []
    permits = _audit_permits() if permits is None else list(permits)
    is_prod = [any(_in_roots(p, PRODUCTION_ROOTS) for p in paths) for _, paths in commits_after_anchor]
    first_prod = next((i for i, prod in enumerate(is_prod) if prod), None)
    if first_prod is not None:
        for i in range(first_prod, len(commits_after_anchor)):
            c, paths = commits_after_anchor[i]
            touched = sorted(set(paths) & set(frozen))
            if not touched:
                continue
            if is_prod[i]:
                errs.append(f"⓪ 提交 {c[:8]} 同時改動生產碼與凍結檔：{touched}")
                continue
            later_prod = [commits_after_anchor[j][0] for j in range(i + 1, len(commits_after_anchor)) if is_prod[j]]
            covering = [p for p in permits if is_ancestor(c, p)
                        and not any(is_ancestor(q, p) for q in later_prod)]
            if not covering:
                errs.append(f"⓪ 生產碼改動開始後之提交 {c[:8]} 改動凍結檔 {touched}，未被其後之本票實作許可涵蓋"
                            f"（須許可之 round_start_head 為其後代、且其間無生產碼提交）")
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


# 審查 r43 CODEX-R43-P1-01：D2 准生產碼前重凍，但既有格之 fingerprint 與語意 receipt 不得被改寫（只准新增格）；
# receipt 中隨每次執行之暫存路徑不同之鍵不比
BASELINE_RUN_PATH_KEYS = frozenset({"kline_copy", "legacy_kline_dir", "child_env"})


FFNAME_RECEIPT_REL = "handoffs/run_receipts/ffname-refreeze.json"
# time_index_sha256 之輸入含 timestamps.parquet 之相對路徑（含 config hash 目錄，受命名世代鹽影響）⇒ 屬名／鹽衍生，
# 其時間值由 FF-NAME K2 收據之去路徑 time_values 比對證明不變（scripts/ffname_refreeze.py framepath recipe）
_FFNAME_FP_SCALARS = ("row_count", "run_status", "completeness", "failure_reasons")


def _ffname_path_receipt_norm(receipt: Any) -> Any:
    """path_receipt 之名／鹽衍生部分正規化：manifests 路徑之 config hash 段（受命名世代鹽影響）以佔位取代；
    dstar_cache_hits 之 sha256 為命中欄名清單之雜湊（名衍生）⇒ 只比 count。其餘鍵原樣比。"""
    if not isinstance(receipt, dict):
        return receipt
    out = dict(receipt)
    if isinstance(out.get("manifests"), list):
        out["manifests"] = ["/".join(p if i != 2 else "<config_hash>" for i, p in enumerate(str(m).split("/")))
                            for m in out["manifests"]]
    if isinstance(out.get("dstar_cache_hits"), dict):
        out["dstar_cache_hits"] = {"count": out["dstar_cache_hits"].get("count")}
    return out


def ffname_framepath_approvals() -> Dict[str, Dict[str, str]]:
    """FF-NAME SPEC v22：收據 framepath 段核可（決策 refrozen）之格 → 該格之改前→現行欄名映射（改前 worktree 紀錄器）。"""
    path = REPO / FFNAME_RECEIPT_REL
    if not path.is_file():
        return {}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    entry = next((e for e in receipt.get("files", []) if e.get("path") == BASELINE_REL), None) or {}
    out: Dict[str, Dict[str, str]] = {}
    for unit in entry.get("units") or []:
        if unit.get("decision") == "refrozen" and not unit.get("value_hash_mismatch"):
            out[str(unit["unit"])] = json.loads((REPO / unit["map"]).read_text(encoding="utf-8"))["mapping"]
    return out


def _ffname_rekeyed_cell_errors(cell: str, old_fp: Dict[str, Any], new_fp: Dict[str, Any],
                                mapping: Dict[str, str]) -> List[str]:
    """核可格之改寫只准「鍵名換名＋名衍生雜湊」：逐欄值紀錄（columns、result_columns.columns）經映射逐筆相等、
    多出之欄須為 FF-NAME §G ⑥ 新增 lag；其餘名無關項（列數、時間軸、完整性等）逐項相等。"""
    from tests.feature_engineering.ffname_helpers import is_g6_new_lag

    errs: List[str] = []
    for key in ("columns", "result_columns"):
        old_cols = (old_fp.get(key) or {}) if key == "columns" else ((old_fp.get(key) or {}).get("columns") or {})
        new_cols = (new_fp.get(key) or {}) if key == "columns" else ((new_fp.get(key) or {}).get("columns") or {})
        seen = set()
        for name, rec in old_cols.items():
            new = mapping.get(name)
            if new is None or new_cols.get(new) != rec:
                errs.append(f"⓪ 格 {cell} {key}／{name}：逐欄值經 FF-NAME 映射不等或查無")
            seen.add(new)
        errs += [f"⓪ 格 {cell} {key}／{n}：多出之欄非 ⑥ 新增 lag" for n in set(new_cols) - seen if not is_g6_new_lag(n)]
    errs += [f"⓪ 格 {cell} {k}：名無關項改變" for k in _FFNAME_FP_SCALARS if old_fp.get(k) != new_fp.get(k)]
    if _ffname_path_receipt_norm(old_fp.get("path_receipt")) != _ffname_path_receipt_norm(new_fp.get("path_receipt")):
        errs.append(f"⓪ 格 {cell} path_receipt：去除 config hash 段與命中欄名雜湊後仍改變")
    return errs


def baseline_lineage_errors(versions: Sequence[Tuple[str, Dict[str, Any]]],
                            approvals: Optional[Dict[str, Dict[str, str]]] = None) -> List[str]:
    """基準各版本（依時間序之 (版本名, 基準 JSON)）之承續：後版須含前版每一格，且該格 fingerprint 逐項相等、
    receipt 除 `BASELINE_RUN_PATH_KEYS` 外相等、`code_anchor` 不變；只准新增格（memory 屬量測值不比）。
    FF-NAME SPEC v22：既有格之逐欄值不變；鍵名與名衍生雜湊（column_names_sha256、manifest_sha256、
    stationarity_decisions_sha256、column_count、result_columns.names_sha256）只在收據 framepath 段核可之格可更新
    （`approvals`；預設讀收據）。"""
    approvals = ffname_framepath_approvals() if approvals is None else approvals
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
                if cell in approvals:
                    errs += _ffname_rekeyed_cell_errors(cell, old.get("fingerprint") or {}, new.get("fingerprint") or {},
                                                        approvals[cell])
                else:
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


def test_ffname_approved_rekey_lineage_rule():
    """FF-NAME SPEC v22 規則：核可格可換鍵與名衍生雜湊；逐欄值變更、非 ⑥ 多出欄、名無關項變更或未核可格之改寫仍紅。"""
    fp = {"run_status": "complete", "row_count": 3, "column_names_sha256": "a", "manifest_sha256": "m",
          "columns": {"close_trend_EMA_8_Kurt_W5": {"values": "v"}}}
    v1 = {"code_anchor": "a", "cells": {"C1": {"fingerprint": fp, "receipt": {}}}}
    renamed = {**fp, "column_names_sha256": "b", "manifest_sha256": "n",
               "columns": {"close_1h_trend_EMA_8_Kurt-W5": {"values": "v"}}}
    v2 = {"code_anchor": "a", "cells": {"C1": {"fingerprint": renamed, "receipt": {}}}}
    approval = {"C1": {"close_trend_EMA_8_Kurt_W5": "close_1h_trend_EMA_8_Kurt-W5"}}
    assert baseline_lineage_errors([("v1", v1), ("v2", v2)], approvals=approval) == []
    assert baseline_lineage_errors([("v1", v1), ("v2", v2)], approvals={}) != []          # 未核可
    bad_value = json.loads(json.dumps(v2))
    bad_value["cells"]["C1"]["fingerprint"]["columns"]["close_1h_trend_EMA_8_Kurt-W5"]["values"] = "w"
    assert baseline_lineage_errors([("v1", v1), ("v2", bad_value)], approvals=approval) != []
    extra = json.loads(json.dumps(v2))
    extra["cells"]["C1"]["fingerprint"]["columns"]["close_1h_trend_SMA_8"] = {"values": "x"}
    assert baseline_lineage_errors([("v1", v1), ("v2", extra)], approvals=approval) != []
    rows = json.loads(json.dumps(v2))
    rows["cells"]["C1"]["fingerprint"]["row_count"] = 4
    assert baseline_lineage_errors([("v1", v1), ("v2", rows)], approvals=approval) != []


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


def test_check_4_internal_consistency_and_excerpts(ctx):
    assert check_4(ctx["disp"], ctx["head"]) == []


NON_ASCII_TRACKED = "tests/3.2C- 雙窗口密度驗證.py"  # repo 內現存之非 ASCII 路徑（處置表母體成員）


def _affected_gate():
    import importlib.util

    spec = importlib.util.spec_from_file_location("framepath_affected_gate", REPO / "scripts/framepath_affected_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_JUNIT = """<testsuites><testsuite>
<testcase classname="tests.x.test_a" name="test_ok"/>
<testcase classname="tests.x.test_a" name="test_p[1h]"><failure type="AssertionError" message="assert 1 == 2">t</failure></testcase>
<testcase classname="tests.x.test_a.TestK" name="test_m"><error type="ValueError" message="bad /private/var/folders/zz/abc at 0x10ab">t</error></testcase>
<testcase classname="tests.x.test_a" name="test_s"><skipped type="pytest.skip" message="needs data"/></testcase>
<testcase classname="tests.x.other" name="test_z"/>
</testsuite></testsuites>"""


def test_affected_gate_junit_nodeid_and_identity():
    """審查 r46（CODEX-R46-P1-01／02、GROK-R46-P1-01）：junit → nodeid 重建（模組函式、參數化、類別方法；他檔略）
    與失敗身分（只遮暫存路徑與位址，數字不遮）。"""
    g = _affected_gate()
    res = g.junit_results(_JUNIT, "tests/x/test_a.py")
    assert set(res) == {"tests/x/test_a.py::test_ok", "tests/x/test_a.py::test_p[1h]",
                        "tests/x/test_a.py::TestK::test_m", "tests/x/test_a.py::test_s"}
    assert res["tests/x/test_a.py::test_ok"]["outcome"] == "passed"
    assert res["tests/x/test_a.py::test_s"]["outcome"] == "skipped"
    ident = g.failure_identity(res["tests/x/test_a.py::TestK::test_m"])
    assert ident == ("error", "ValueError", "bad <tmp> at <hex>")
    assert g.failure_identity({"outcome": "failed", "type": "AssertionError", "message": "assert 1 == 2"}) != \
        g.failure_identity({"outcome": "failed", "type": "AssertionError", "message": "assert 1 == 3"})


def test_mutation_affected_gate_classify_cannot_absorb_caused():
    """三類歸屬封閉：完整性缺漏 ⇒ missing；錨點同身分 ⇒ 既有紅；錨點綠／缺／身分或類別不同 ⇒ 本批造成；略過亦比身分。"""
    g = _affected_gate()
    f = lambda msg, outcome="failed", t="AssertionError": {"outcome": outcome, "type": t, "message": msg}  # noqa: E731
    exp = ["a::ok", "a::red", "a::changed", "a::anchor_green", "a::anchor_missing", "a::skip_same", "a::skip_new",
           "a::kind", "a::absent"]
    batch = {"a::ok": f("", "passed"), "a::red": f("x"), "a::changed": f("x 2"), "a::anchor_green": f("x"),
             "a::anchor_missing": f("x"), "a::skip_same": f("r", "skipped", "skip"),
             "a::skip_new": f("r", "skipped", "skip"), "a::kind": f("x", "error", "AssertionError"),
             "a::extra": f("", "passed")}
    anchor = {"a::red": f("x"), "a::changed": f("x 1"), "a::anchor_green": f("", "passed"),
              "a::skip_same": f("r", "skipped", "skip"), "a::kind": f("x")}
    out = g.classify(exp, batch, anchor)
    assert out["missing"] == ["a::absent"] and out["unexpected"] == ["a::extra"]
    assert out["head_red"] == ["a::red", "a::skip_same"]
    assert out["caused"] == ["a::changed", "a::anchor_green", "a::anchor_missing", "a::skip_new", "a::kind"]
    assert out["passed"] == ["a::ok"]


def test_mutation_affected_gate_verdict_every_condition_blocks():
    """審查 r47（CODEX-R47-P1-03／04）：通過條件逐項——A 組失敗、未完成檔（pytest rc 非 0／1 或結果不齊）、缺、多出、
    本批造成，任一非空即不通過；全空才通過。"""
    g = _affected_gate()
    ok = {"missing": [], "unexpected": [], "caused": [], "head_red": ["x"], "passed": ["y"]}
    assert g.verdict(ok, [], []) is True
    assert g.verdict(ok, ["a::t"], []) is False
    assert g.verdict(ok, [], ["tests/f.py"]) is False
    for key in ("missing", "unexpected", "caused"):
        assert g.verdict(dict(ok, **{key: ["n"]}), [], []) is False
    assert g.RUN_RC_OK == (0, 1)


def test_affected_gate_state_key_binds_tree_and_file(tmp_path):
    """審查 r47（CODEX-R47-P1-05）：結果檔沿用之狀態指紋隨工作樹 diff、未追蹤檔、測試檔內容、phase 改變而改變。"""
    g = _affected_gate()
    repo = tmp_path / "r"
    repo.mkdir()
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)  # noqa: E731
    run("init", "-q")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    (repo / "t.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    run("add", "t.py")
    run("commit", "-qm", "c")
    k0 = g.state_key(repo, "t.py", 1)
    assert g.state_key(repo, "t.py", 1) == k0
    assert g.state_key(repo, "t.py", 2) != k0
    (repo / "u.py").write_text("x = 1\n", encoding="utf-8")
    k1 = g.state_key(repo, "t.py", 1)
    assert k1 != k0
    (repo / "t.py").write_text("def test_a():\n    assert 1\n", encoding="utf-8")
    assert g.state_key(repo, "t.py", 1) not in (k0, k1)


def test_affected_gate_anchor_worktree_verification(tmp_path):
    """審查 r47（CODEX-R47-P1-02）：錨點工作樹須 HEAD＝本票最晚許可錨點、乾淨（封閉豁免僅 data_cache symlink 與
    __pycache__）；主工作樹（HEAD 非錨點或不乾淨）⇒ 拒。SPEC v23 D12.1：錨點碼態由許可錨點界定，不再比對寫死之
    6e07e0ad 生產碼（b2 起許可錨點含 b1 生產碼改動，該比對恆拒）。"""
    g = _affected_gate()
    assert g._benign_status("?? data_cache") and g._benign_status(" M momentum/x/__pycache__/a.nbi")
    assert not g._benign_status("?? data_cache_other") and not g._benign_status(" M tests/a.py")
    assert not g._benign_status("?? scripts/new.py")
    with pytest.raises(g.GateError):
        g.verify_anchor_worktree(REPO, "0" * 40)
    # SPEC v23 D12.1：寫死之碼態錨點常數與其生產碼等值比對已刪
    import inspect

    assert not hasattr(g, "CODE_ANCHOR")
    src = inspect.getsource(g.verify_anchor_worktree)
    assert "CODE_ANCHOR" not in src and "PRODUCTION_ROOTS" not in src


def test_mutation_affected_gate_r48_hardening(tmp_path, monkeypatch):
    """審查 r48（CODEX-R48-P1-02／03／04）：錨點重跑 rc 非 0／1 或結果不齊 ⇒ 不採（不得吸收為既有紅）；狀態指紋綁定
    有效環境；錨點工作樹之實體 data_cache 或被忽略檔 ⇒ 拒。"""
    g = _affected_gate()
    r = {"a::x": {"outcome": "failed", "type": "E", "message": "m"}}
    assert g.anchor_usable(0, r, ["a::x"]) == r and g.anchor_usable(1, r, ["a::x"]) == r
    assert g.anchor_usable(2, r, ["a::x"]) == {} and g.anchor_usable(1, r, ["a::x", "a::y"]) == {}
    out = g.classify(["a::x"], r, g.anchor_usable(3, r, ["a::x"]))
    assert out["caused"] == ["a::x"] and out["head_red"] == []
    assert g.env_fingerprint({"FFACT_X": "1"}) != g.env_fingerprint({"FFACT_X": "2"})
    assert g.env_fingerprint({"FFACT_X": "1", "HOME": "a"}) == g.env_fingerprint({"FFACT_X": "1", "HOME": "b"})
    assert g._benign_ignored("momentum/a/__pycache__/x.nbi") and not g._benign_ignored("data_cache/x.h5")
    assert g.BATCH_PHASE == {1: 1, 2: 2, 3: 3, 4: 3}


def test_mutation_affected_gate_anchor_worktree_real(tmp_path):
    """審查 r49（CODEX-R49-P1-01）：以真實錨點工作樹（本票最晚實作許可之提交，稀疏檢出只含 pytest.ini 以控秒級與磁碟）
    實跑 verify_anchor_worktree：合法狀態（無 data_cache 或指向主工作樹之 symlink）通過；實體 data_cache 目錄、
    指向他處之 symlink、被忽略之輸入檔（.env）、追蹤檔改動，各自拒絕。SPEC v23 D12.1：許可錨點之生產碼可異於
    6e07e0ad（b2 起含 b1 生產碼改動），合法錨點工作樹照常通過；錨點工作樹 HEAD 為真實他提交（如 6e07e0ad，當其非
    許可錨點時）⇒ 拒。"""
    g = _affected_gate()
    anchor = g.resolve_anchor()
    wt = tmp_path / "anchor_wt"
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, check=True, capture_output=True)  # noqa: E731
    git("worktree", "add", "--no-checkout", "--detach", str(wt), anchor)
    try:
        subprocess.run(["git", "-C", str(wt), "sparse-checkout", "set", "--no-cone", "/pytest.ini"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(wt), "checkout", "--quiet"], check=True, capture_output=True)
        g.verify_anchor_worktree(wt, anchor)  # 合法：無 data_cache
        (wt / "data_cache").symlink_to(REPO / "data_cache")
        g.verify_anchor_worktree(wt, anchor)  # 合法：指向主工作樹之 symlink
        (wt / "data_cache").unlink()
        (wt / "data_cache").mkdir()
        with pytest.raises(g.GateError):  # 實體 data_cache
            g.verify_anchor_worktree(wt, anchor)
        (wt / "data_cache").rmdir()
        (wt / "data_cache").symlink_to(tmp_path)
        with pytest.raises(g.GateError):  # 指向他處之 symlink
            g.verify_anchor_worktree(wt, anchor)
        (wt / "data_cache").unlink()
        (wt / ".env").write_text("X=1\n", encoding="utf-8")
        with pytest.raises(g.GateError):  # 被忽略之輸入檔
            g.verify_anchor_worktree(wt, anchor)
        (wt / ".env").unlink()
        (wt / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        with pytest.raises(g.GateError):  # 追蹤檔改動
            g.verify_anchor_worktree(wt, anchor)
        with pytest.raises(g.GateError):  # HEAD ≠ 錨點
            g.verify_anchor_worktree(wt, "0" * 40)
        # SPEC v23 D12.1：以真實他提交（碼態舊錨點 6e07e0ad）為錨點 ⇒ HEAD ≠ 錨點而拒（HEAD 條件為碼態界定之唯一來源）
        old = subprocess.run(["git", "rev-parse", "6e07e0ad^{commit}"], cwd=REPO, check=True, capture_output=True,
                             text=True).stdout.strip()
        if old != anchor:
            with pytest.raises(g.GateError):
                g.verify_anchor_worktree(wt, old)
    finally:
        git("worktree", "remove", "--force", str(wt))


def test_affected_gate_manifest_groups():
    """C 組須為 affected_tests 之子集；A 組（本票具名驗收）不入 B／C；缺 affected_groups 列 ⇒ 拒跑。"""
    g = _affected_gate()
    rows = ["affected_tests phase=1 tests/a.py tests/feature_engineering/test_framepath_invariance.py tests/c.py",
            "affected_groups phase=1 C=tests/c.py"]
    assert g.manifest_groups({"batch_card": {"risk_mitigation": rows}}, 1) == (["tests/a.py"], ["tests/c.py"])
    with pytest.raises(g.GateError):
        g.manifest_groups({"batch_card": {"risk_mitigation": rows[:1]}}, 1)
    with pytest.raises(g.GateError):
        g.manifest_groups({"batch_card": {"risk_mitigation": [rows[0], "affected_groups phase=1 C=tests/zz.py"]}}, 1)
    real = json.loads((REPO / MANIFEST_REL).read_text(encoding="utf-8"))
    b, c = g.manifest_groups(real, 1)
    assert c and set(b).isdisjoint(c) and not set(b + c) & set(g.A_GROUP)


def test_affected_gate_collect_real_nodeids():
    """諮詢 r5 CODEX-R5-P1-01：以真實 pytest collect（本專案 pytest.ini）取得 nodeid；mutation：collect 改回 `-q` ⇒
    輸出為表頭與 `<Function …>`、無 nodeid 行 ⇒ GateError（紅）。"""
    g = _affected_gate()
    env = dict(os.environ, PYTHONPATH=str(REPO))
    ids = g.collect("tests/test_cgsa_pipeline.py", REPO, env)
    assert ids and all(i.startswith("tests/test_cgsa_pipeline.py::") for i in ids)


_D8_HELPER = '''
def prepare_env(mp, **env):
    for k, v in env.items():
        mp.setenv(k, v)

def run_frame(mp):
    mp.setenv("FFACT_USE_CGSA", "0")

def generate_s2(factory):
    return factory.generate_features("X", "1h")
'''
_D8_CONFTEST = '''
import pytest

@pytest.fixture
def frame_env(monkeypatch):
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
'''
_D8_TEST = '''
from tests import d8help as h

_PATH_ENV = {"legacy": {"FFACT_USE_CGSA": "0"}, "cgsa": {}}

def test_dict_spread(path, monkeypatch):
    h.prepare_env(monkeypatch, **_PATH_ENV[path])

def test_condexp(use, monkeypatch):
    monkeypatch.setenv("FFACT_USE_CGSA", "1" if use else "0")

def test_truthy_only(monkeypatch):
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

def test_helper_module_call(monkeypatch):
    h.run_frame(monkeypatch)

def _local_env():
    return {"FFACT_USE_CGSA": "0"}

def test_local_helper_call():
    env = _local_env()

def test_conftest_fixture(frame_env):
    pass

def test_deleted_symbol_attr(factory):
    factory._cgsa_enabled()

def test_deleted_symbol_string(monkeypatch, factory):
    monkeypatch.setattr(factory, "_cgsa_enabled", lambda: False)

def test_kw_value_unknown(monkeypatch, v):
    h.prepare_env(monkeypatch, FFACT_USE_CGSA=v)

def test_untouched():
    assert 1 + 1 == 2
'''


def _d8_sources(test_src=_D8_TEST, helper_src=_D8_HELPER):
    src = {"tests/d8help.py": helper_src, "tests/conftest.py": _D8_CONFTEST, "tests/test_d8.py": test_src}
    return src.get


def test_mutation_affected_gate_s2_taint_transitive():
    """諮詢 r5 CODEX-R5-P1-02／COMPOSER-R5-P1-01／GROK-R5-P1-01：S2 以 AST 傳遞分析判「會走被刪／被改分支」——模組層
    dict 經 `**` 展開、CondExp 假值臂、tests/ 輔助模組呼叫、同模組 helper、conftest fixture、被刪符號（屬性或字串）、
    值不可決定之關鍵字引數皆選入；可證真值常數與無關測試不選入。mutation：關閉 ffact 與符號表 ⇒ 前述全數消失（紅）。"""
    g = _affected_gate()
    scan = g.file_scan("tests/test_d8.py", _d8_sources(), frozenset({"_cgsa_enabled"}))
    tainted = set(scan["taint"])
    must = {"test_dict_spread", "test_condexp", "test_helper_module_call", "test_local_helper_call",
            "test_conftest_fixture", "test_deleted_symbol_attr", "test_deleted_symbol_string", "test_kw_value_unknown"}
    assert must <= tainted, sorted(must - tainted)
    assert not {"test_truthy_only", "test_untouched"} & tainted
    assert "name:_PATH_ENV" in scan["taint"]["test_dict_spread"]
    assert any(r.startswith("call:tests/d8help.py:") for r in scan["taint"]["test_helper_module_call"])
    assert any(r.startswith("call:tests/conftest.py:") for r in scan["taint"]["test_conftest_fixture"])
    off = g.module_taint("tests/test_d8.py", _d8_sources(), frozenset(), ffact=False)
    assert not any(off.values())


def test_affected_gate_heavy_is_transitive():
    """S3 輕量判定須經輔助模組傳遞（諮詢 r5 實測：直接字面判定把經 helper 呼叫真實生成之檔誤判輕量）。"""
    g = _affected_gate()
    heavy_src = "from tests import d8help as h\n\ndef test_x(factory):\n    h.generate_s2(factory)\n"
    assert g.is_heavy("tests/test_d8.py", _d8_sources(test_src=heavy_src))
    assert g.is_heavy("tests/test_d8.py", _d8_sources(test_src="P = 'data_cache/feature_klines/kline_cache.h5'\n"))
    assert not g.is_heavy("tests/test_d8.py", _d8_sources(test_src="def test_y():\n    assert True\n"))
    # 審查 r51 GROK-R51-P1-01：helper 內只有 kline 路徑字面（函式內或模組層名稱），測試只呼叫該 helper ⇒ 重型
    helper = "def kline_frame():\n    return open('data_cache/feature_klines/kline_cache.h5')\n"
    caller = "from tests import d8help as h\n\ndef test_z():\n    h.kline_frame()\n"
    assert g.is_heavy("tests/test_d8.py", _d8_sources(test_src=caller, helper_src=helper))
    helper2 = "KLINE = 'data_cache/feature_klines/kline_cache.h5'\n\ndef load():\n    return KLINE\n"
    caller2 = "from tests import d8help as h\n\ndef test_z():\n    h.load()\n"
    assert g.is_heavy("tests/test_d8.py", _d8_sources(test_src=caller2, helper_src=helper2))


def test_affected_gate_s1_targets_locators():
    """S1：qualname locator 取該函式（含全部參數化）；target／import_alias 取引用該名之函式；顯式 nodeids；rename 取
    new_nodeid；phase>N 之操作不入。空 nodeids 不等於沒有測試。"""
    g = _affected_gate()
    disp = {"operations": [
        {"id": "OP-1", "phase": 1, "path": "tests/t.py", "kind": "rewrite", "nodeids": [],
         "locator": {"category": "def", "qualname": "test_a"}},
        {"id": "OP-2", "phase": 1, "path": "tests/t.py", "kind": "delete-node", "nodeids": [],
         "locator": {"category": "dict_item", "target": "_ENV", "path": ["legacy"]}},
        {"id": "OP-3", "phase": 1, "path": "tests/t.py", "kind": "delete-node", "nodeids": [],
         "locator": {"category": "import_alias", "lineno": 3, "name": "MagicMock"}},
        {"id": "OP-4", "phase": 1, "path": "tests/t.py", "kind": "delete-node",
         "nodeids": ["tests/t.py::test_p[legacy]"], "locator": {"category": "parametrize_elem", "qualname": "test_p"}},
        {"id": "OP-5", "phase": 2, "path": "tests/t.py", "kind": "rewrite", "nodeids": [],
         "locator": {"category": "def", "qualname": "test_late"}},
    ], "nodeids": [{"nodeid": "tests/t.py::C::test_old", "phase": 1, "disposition": "rename", "op": "OP-6",
                    "new_nodeid": "tests/t.py::C::test_new"}]}
    scans = {"tests/t.py": {"refs": {"test_b": {"_ENV"}, "test_c": {"MagicMock"}, "test_d": {"x"}}}}
    funcs, nodes = g.s1_targets(disp, 1, scans)
    assert set(funcs["tests/t.py"]) == {"test_a", "test_b", "test_c", "test_p", "C.test_new"}
    assert "tests/t.py::test_p[legacy]" in nodes and "tests/t.py::C::test_new" in nodes
    collected = {"tests/t.py": ["tests/t.py::test_a[1]", "tests/t.py::test_a[2]", "tests/t.py::test_p[cgsa]",
                                "tests/t.py::C::test_new", "tests/t.py::test_d", "tests/t.py::test_late"]}
    sel, skip = g.select_expected(collected, {"tests/t.py": {"refs": scans["tests/t.py"]["refs"], "taint": {},
                                                             "heavy": True}}, funcs, nodes, [], [], False)
    assert set(sel) == {"tests/t.py::test_a[1]", "tests/t.py::test_a[2]", "tests/t.py::test_p[cgsa]",
                        "tests/t.py::C::test_new"}
    assert skip == {"tests/t.py::test_d": "invariance_envelope", "tests/t.py::test_late": "invariance_envelope"}


def test_mutation_affected_gate_select_partition_and_align():
    """選入與未跑互斥且聯集＝collected；輕量檔整檔選入、釘扎重型不得整檔；必跑選入；引用對齊名者未觸發時理由為
    align_static_proof、觸發時選入（CODEX-R5-P2-03 條件觸發）。mutation：對齊觸發旗標失效 ⇒ 觸發案仍為 skipped（紅）。"""
    g = _affected_gate()
    collected = {"tests/light.py": ["tests/light.py::test_1", "tests/light.py::test_2"],
                 "tests/pinned.py": ["tests/pinned.py::test_3"],
                 "tests/heavy.py": ["tests/heavy.py::test_v6", "tests/heavy.py::test_must", "tests/heavy.py::test_x"]}
    scans = {"tests/light.py": {"refs": {}, "taint": {}, "heavy": False},
             "tests/pinned.py": {"refs": {}, "taint": {}, "heavy": False},
             "tests/heavy.py": {"refs": {"test_v6": {"TimeframeAligner"}}, "taint": {}, "heavy": True}}
    must = ["tests/heavy.py::test_must"]
    for trig in (False, True):
        sel, skip = g.select_expected(collected, scans, {}, {}, must, ["tests/pinned.py"], trig)
        allids = {n for ids in collected.values() for n in ids}
        assert set(sel) | set(skip) == allids and not set(sel) & set(skip)
        assert {"tests/light.py::test_1", "tests/light.py::test_2", "tests/heavy.py::test_must"} <= set(sel)
        assert skip["tests/pinned.py::test_3"] == "invariance_envelope"
        assert skip["tests/heavy.py::test_x"] == "invariance_envelope"
        assert set(skip.values()) <= set(g.SKIP_REASONS)
        if trig:
            assert sel["tests/heavy.py::test_v6"] == ["align_trigger"]
        else:
            assert skip["tests/heavy.py::test_v6"] == "align_static_proof"


_CGSA_OLD = '''
def gone():
    return 1

def _priv():
    return 1

def public():
    return 1

class K:
    def _meth(self):
        return 1

    def dispatch(self):
        use_cgsa = self._cgsa_enabled() and getattr(self, "_cgsa_registry", None) is not None
        if use_cgsa:
            return self._cgsa_path()
        return self._legacy_path()

    def gated(self, mode):
        if self._cgsa_enabled() and self._cgsa_registry is not None and mode == "s":
            return 1
        if not self._cgsa_enabled():
            raise RuntimeError("off")
        return 2
'''
_CGSA_NEW = '''
def _priv():
    return 2

def public():
    return 2

class K:
    def _meth(self):
        return 2

    def dispatch(self):
        """docstring 不影響。"""
        self._require_cgsa_registry("dispatch")
        return self._cgsa_path()

    def gated(self, mode):
        if mode == "s":
            self._require_cgsa_registry("gated")
            return 1
        return 2
'''


def _git_tmp_repo(tmp_path, files):
    repo = tmp_path / "r"

    def git(*a):
        return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True,
                              capture_output=True, text=True).stdout

    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    git("init", "-q")
    git("add", ".")
    git("commit", "-qm", "a")
    return repo, git("rev-parse", "HEAD").strip()


def test_mutation_affected_gate_cgsa_equivalence_and_dangling(tmp_path):
    """審查 r51 CODEX-R51-P1-01：S2 符號表＝被刪定義 ∪ CGSA 殘差（CGSA 開啟且 registry 已建立之假設下正規形仍不同者，
    不分公開私有）；只拿掉 `_cgsa_enabled()` 判斷、改加 registry 守衛之改動（dispatch、gated）判等價不入表。被刪且已無
    定義之名稱仍被引用 ⇒ GateError。mutation：正規化失效（等價判斷恆假）⇒ dispatch／gated 入殘差（紅）。"""
    g = _affected_gate()
    repo, anchor = _git_tmp_repo(tmp_path, {"momentum/m.py": _CGSA_OLD})
    (repo / "momentum" / "m.py").write_text(_CGSA_NEW, encoding="utf-8")
    deleted, residual, files, specs = g.production_changes(repo, anchor)
    assert deleted == {"gone"} and files == ["momentum/m.py"]
    assert residual == {"_priv", "public", "_meth"}
    assert specs == ["momentum.m:K._meth", "momentum.m:_priv", "momentum.m:public"]
    assert g.s2_symbols(deleted, residual) == frozenset({"gone", "_priv", "public", "_meth"})
    old_k = {n.name: n for n in ast.parse(_CGSA_OLD).body if isinstance(n, ast.ClassDef)}["K"]
    new_k = {n.name: n for n in ast.parse(_CGSA_NEW).body if isinstance(n, ast.ClassDef)}["K"]
    for name in ("dispatch", "gated"):
        o = next(m for m in old_k.body if getattr(m, "name", "") == name)
        n = next(m for m in new_k.body if getattr(m, "name", "") == name)
        assert ast.dump(o) != ast.dump(n) and g.cgsa_normal_form(o) == g.cgsa_normal_form(n)
    (repo / "momentum" / "user.py").write_text("def use():\n    return gone()\n", encoding="utf-8")
    with pytest.raises(g.GateError):
        g.production_changes(repo, anchor)


def test_affected_gate_cgsa_equivalence_rejects_real_change():
    """CGSA 開啟下行為確有不同者不得判等價：保留分支之值改變、白名單改拒絕、條件不涉 CGSA 之刪除。"""
    g = _affected_gate()

    def fn(src):
        return ast.parse(src).body[0]

    old = "def f(self, c):\n    if self._cgsa_enabled() and c in SKIP:\n        return None\n    return c\n"
    new = "def f(self, c):\n    if c not in OK:\n        raise ValueError(c)\n    return c\n"
    assert g.cgsa_normal_form(fn(old)) != g.cgsa_normal_form(fn(new))
    old2 = "def f(self):\n    if self._cgsa_enabled():\n        return 1\n    return 0\n"
    assert g.cgsa_normal_form(fn(old2)) == g.cgsa_normal_form(fn("def f(self):\n    return 1\n"))
    assert g.cgsa_normal_form(fn(old2)) != g.cgsa_normal_form(fn("def f(self):\n    return 0\n"))


def test_mutation_affected_gate_r52_value_semantics_and_bindings(tmp_path):
    """審查 r52：①and／or 只在只看真假之位置任意折疊，值位置只去開頭常數（`x and <CGSA 開>` ≠ `x`）②類別屬性與模組
    常數之值改變入殘差，且新碼中引用者入殘差規格 ③類別標頭或無法以名稱歸屬之模組層敘述改變 ⇒ 拒跑。"""
    g = _affected_gate()

    def fn(src):
        return ast.parse(src).body[0]

    nf = g.cgsa_normal_form
    assert nf(fn("def f(self, x):\n    return x and self._cgsa_enabled()\n")) != nf(fn("def f(self, x):\n    return x\n"))
    assert nf(fn("def f(self, x):\n    if x and self._cgsa_enabled():\n        return 1\n    return 0\n")) == \
        nf(fn("def f(self, x):\n    if x:\n        return 1\n    return 0\n"))
    assert nf(fn("def f(self, x):\n    y = self._cgsa_enabled() and x\n    return y\n")) == \
        nf(fn("def f(self, x):\n    y = x\n    return y\n"))
    assert nf(fn("def f(self, x):\n    return not (not self._cgsa_enabled() and x)\n")) == \
        nf(fn("def f(self, x):\n    return True\n"))
    # 審查 r53：吸收常數之前有運算元（x 仍被求值）⇒ 不得化為常數
    assert nf(fn("def f(self, x):\n    return not (x and not self._cgsa_enabled())\n")) != \
        nf(fn("def f(self, x):\n    return True\n"))

    old = "LIMIT = 1\n\nclass C:\n    MODE = 'old'\n\n    def value(self):\n        return self.MODE\n\n" \
          "    def other(self):\n        return 0\n\ndef use():\n    return LIMIT\n"
    new = old.replace("MODE = 'old'", "MODE = 'new'").replace("LIMIT = 1", "LIMIT = 2")
    repo, anchor = _git_tmp_repo(tmp_path / "a", {"momentum/m.py": old})
    (repo / "momentum" / "m.py").write_text(new, encoding="utf-8")
    deleted, residual, _files, specs = g.production_changes(repo, anchor)
    assert {"MODE", "LIMIT"} <= residual and not deleted
    assert specs == ["momentum.m:C.value", "momentum.m:use"]
    for bad in (old.replace("class C:", "class C(object):"), old + "\nif LIMIT:\n    print('x')\n"):
        repo2, anchor2 = _git_tmp_repo(tmp_path / f"b{len(bad)}", {"momentum/m.py": old})
        (repo2 / "momentum" / "m.py").write_text(bad, encoding="utf-8")
        with pytest.raises(g.GateError):
            g.production_changes(repo2, anchor2)


_CYCLE_SOURCES = {
    "tests/h1.py": "from tests import h2\n\ndef fn():\n    return Deleted\n\ndef other():\n    return h2.g()\n",
    "tests/h2.py": "from tests import h1\n\ndef g():\n    return h1.fn()\n",
    "tests/test_a.py": "from tests import h1\n\ndef test_a():\n    h1.other()\n",
    "tests/test_b.py": "from tests import h2\n\ndef test_b():\n    h2.g()\n",
}


def test_mutation_affected_gate_cycle_taint_order_independent():
    """審查 r52 CODEX-R52-P1-03／GROK-R52-P1-01：輔助模組循環匯入時，S2 taint 與掃描順序無關、共用快取不存不完整
    結果。mutation：遇循環回空並快取（原實作）⇒ 後掃之 test_b 無 taint（紅）。"""
    g = _affected_gate()
    src = _CYCLE_SOURCES.get
    sym = frozenset({"Deleted"})
    for order in (("tests/test_a.py", "tests/test_b.py"), ("tests/test_b.py", "tests/test_a.py")):
        cache: dict = {}
        got = {p: g.module_taint(p, src, sym, cache) for p in order}
        assert got["tests/test_a.py"]["test_a"] and got["tests/test_b.py"]["test_b"], order
    assert g.module_taint("tests/h2.py", src, sym)["g"] == {"call:tests/h1.py:fn"}


def test_affected_gate_probe_plugin_records_in_pytest(tmp_path):
    """殘差探針於 B／C 之 pytest 行程內亦記錄（`-p framepath_affected_gate`）。以子行程實跑 pytest。"""
    (tmp_path / "probe_mod2.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (tmp_path / "test_probe_use.py").write_text("import probe_mod2\n\ndef test_x():\n    assert probe_mod2.f() == 1\n",
                                                encoding="utf-8")
    out = tmp_path / "probe"
    g = _affected_gate()
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tmp_path), str(REPO), str(REPO / "scripts")]),
               FRAMEPATH_DEF_PROBE_DIR=str(out), FRAMEPATH_DEF_PROBE_DEFS="probe_mod2:f")
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *g.PROBE_PLUGIN_ARGS,
                           "-c", os.devnull, "--rootdir", str(tmp_path), str(tmp_path / "test_probe_use.py")],
                          env=env, cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-800:] + proc.stderr[-800:]
    assert g.probe_hits(out) == {"probe_mod2:f"}


def test_mutation_affected_gate_digest_and_timing_hardening(tmp_path):
    """審查 r52：①未追蹤檔內容改變 ⇒ inputs_digest 改變（本執行器自身收據除外）②junit 時間非有限／負值不採、
    admission 之 NaN 計為未知。mutation：digest 只雜湊路徑清單、admission 不檢有限 ⇒ 紅。"""
    g = _affected_gate()
    repo, anchor = _git_tmp_repo(tmp_path, {"README": "x\n"})
    (repo / "u.txt").write_text("one", encoding="utf-8")
    d1 = g.plan_inputs_digest(repo, anchor, 1)
    (repo / "u.txt").write_text("two", encoding="utf-8")
    d2 = g.plan_inputs_digest(repo, anchor, 1)
    assert d1 != d2
    own = repo / "handoffs" / "run_receipts" / "framepath-b1-affected-plan.json"
    own.parent.mkdir(parents=True)
    own.write_text("{}", encoding="utf-8")
    assert g.plan_inputs_digest(repo, anchor, 1) == d2
    xml = ('<testsuites><testsuite><testcase classname="tests.test_cgsa_pipeline" name="a" time="nan"/>'
           '<testcase classname="tests.test_cgsa_pipeline" name="b" time="-1"/>'
           '<testcase classname="tests.test_cgsa_pipeline" name="c" time="inf"/>'
           '<testcase classname="tests.test_cgsa_pipeline" name="d"/></testsuite></testsuites>')
    assert g.junit_times(xml, REPO) == {}
    adm = g.admission(["n"], {"n": float("nan")}, 10)
    assert adm["status"] == "unknown" and adm["unknown"] == ["n"]


def test_mutation_affected_gate_r53_hardening(tmp_path):
    """審查 r53：①條件位置之吸收常數不吞掉其前運算元之求值（`if x() and False` ≠ `if False`）②dict 中其後有
    `**展開` 之 FFACT 真值不算已證 ③經匯入類別再呼叫其方法之 taint 須傳遞（含別名匯入鏈）④--timings 估時來源綁入
    inputs_digest。mutation：任一修補撤回 ⇒ 對應斷言紅。"""
    g = _affected_gate()

    def fn(src):
        return ast.parse(src).body[0]

    nf = g.cgsa_normal_form
    assert nf(fn("def f(x):\n    if x() and False:\n        return 1\n    return 0\n")) != \
        nf(fn("def f(x):\n    if False:\n        return 1\n    return 0\n"))
    assert nf(fn("def f(x):\n    if False and x():\n        return 1\n    return 0\n")) == \
        nf(fn("def f(x):\n    return 0\n"))

    assert g.ffact_unproven(ast.parse('cfg = {"FFACT_USE_CGSA": "1", **extra}'))
    assert not g.ffact_unproven(ast.parse('cfg = {**extra, "FFACT_USE_CGSA": "1"}'))

    src = {"tests/h.py": "class C:\n    def g(self):\n        return Deleted\n",
           "tests/a.py": "from tests.h import C\n\ndef helper():\n    return C().g()\n",
           "tests/test_x.py": "from tests import a as aa\n\ndef test_x():\n    aa.helper()\n"}.get
    assert g.module_taint("tests/test_x.py", src, frozenset({"Deleted"}))["test_x"]

    # 審查 r54：分支內之單次賦值不支配後續讀取 ⇒ 不代入（原碼 cond 為假時 UnboundLocalError，不得判等價）
    old54 = "def f(self, cond):\n    if cond:\n        flag = True\n    return flag and self._cgsa_enabled()\n"
    new54 = "def f(self, cond):\n    if cond:\n        flag = True\n    return True\n"
    assert nf(fn(old54)) != nf(fn(new54))
    # 讀取先於最外層賦值（原碼 UnboundLocalError）⇒ 不代入
    old54b = "def f(self):\n    y = flag\n    flag = self._cgsa_enabled()\n    return y\n"
    assert nf(fn(old54b)) != nf(fn("def f(self):\n    y = True\n    return y\n"))
    # 最外層、先於全部讀取之單次賦值仍代入（b1 之 generate_multi_tf 形態）
    old_top = ("def f(self):\n    use = self._cgsa_enabled() and self._cgsa_registry is not None\n"
               "    if use:\n        return self._a()\n    return self._b()\n")
    assert nf(fn(old_top)) == nf(fn("def f(self):\n    self._require_cgsa_registry('f')\n    return self._a()\n"))

    # 審查 r55：`except … as 名`、函式內 import 別名、巢狀定義名皆計為綁定 ⇒ 不代入
    cases = (  # (原碼其餘本體, 誤代入後之本體)
        ("    try:\n        return flag / x\n    except ZeroDivisionError as flag:\n        return flag\n",
         "    try:\n        return True / x\n    except ZeroDivisionError as flag:\n        return True\n"),
        ("    import os as flag\n    return flag\n", "    import os as flag\n    return True\n"),
        ("    def flag():\n        return 0\n    return flag\n", "    def flag():\n        return 0\n    return True\n"),
    )
    for rest, wrongly_substituted in cases:
        old55 = "def f(self, x):\n    flag = self._cgsa_enabled()\n" + rest
        assert nf(fn(old55)) != nf(fn("def f(self, x):\n" + wrongly_substituted)), rest

    repo, anchor = _git_tmp_repo(tmp_path, {"README": "x\n"})
    e1 = g.plan_inputs_digest(repo, anchor, 1, (), {"PATH": "/bin"})
    assert g.plan_inputs_digest(repo, anchor, 1, (), {"PATH": "/bin", "PYTEST_ADDOPTS": "--deselect=x"}) != e1
    tdir = tmp_path / "timings"
    tdir.mkdir()
    xml = tdir / "a.xml"
    xml.write_text('<testsuites><testcase classname="tests.t" name="a" time="1"/></testsuites>', encoding="utf-8")
    d1 = g.plan_inputs_digest(repo, anchor, 1, [tdir])
    xml.write_text('<testsuites><testcase classname="tests.t" name="a" time="2"/></testsuites>', encoding="utf-8")
    assert g.plan_inputs_digest(repo, anchor, 1, [tdir]) != d1


def test_mutation_affected_gate_r59_anchor_restore_and_collect_progress(tmp_path, monkeypatch):
    """審查 r59：①Runner 呼叫前還原的是本次呼叫之工作樹（錨點呼叫還原錨點樹之清冊）②collect 前後寫 progress.json，
    逾時具名停下（collect-timeout）。mutation：還原寫死主 REPO、collect 無逾時 ⇒ 紅。"""
    g = _affected_gate()
    other, _ = _git_tmp_repo(tmp_path / "anchor", {"tests/golden/l65/test_inventory.txt": "anchor-head\n"})
    inv = other / "tests/golden/l65/test_inventory.txt"
    inv.write_text("regenerated\n", encoding="utf-8")
    seen = {}

    def fake_run_file(test_file, xml, cwd, env, nodeids=None, extra=()):
        seen["inv"] = inv.read_text(encoding="utf-8")
        return 0, {"t::x": {"outcome": "passed", "type": "", "message": ""}}

    monkeypatch.setattr(g, "run_file", fake_run_file)
    r = g.Runner(tmp_path / "out", None, 1)
    r.run("t", tmp_path / "out" / "j.xml", other, os.environ, ["t::x"], (), "K", ["t::x"], phase="anchor")
    assert seen["inv"] == "anchor-head\n"

    (tmp_path / "slow").mkdir()
    (tmp_path / "slow" / "test_slow_import.py").write_text("import time\ntime.sleep(30)\n\ndef test_a():\n    pass\n",
                                                          encoding="utf-8")
    monkeypatch.setattr(g, "COLLECT_TIMEOUT_SECONDS", 2)
    monkeypatch.setattr(g, "_RUNNER", g.Runner(tmp_path / "out2", None, 0))
    with pytest.raises(g.GateError):
        g.collect("test_slow_import.py", tmp_path / "slow", dict(os.environ, PYTHONPATH=str(REPO)))
    prog = json.loads((tmp_path / "out2" / "progress.json").read_text(encoding="utf-8"))
    assert prog["phase"] == "collect" and prog["state"] == "collect-timeout" and prog["file"] == "test_slow_import.py"


def test_mutation_split_commit_paths_foreign_vs_ticket():
    """實作期 b1：他票並行提交（如 Javis 信箱工具）之路徑不計入本票 ⑤(a)／⑦；本票提交（SPEC v22 D11.1：Ticket-Batch
    root＝20260928-FRAMEPATH，或 Governance-Scope 第二 token＝FRAMEPATH）之路徑照常受檢；同一路徑兩者皆改者屬本票。
    mutation：分類規則改成全部本票、或改回標題／附註子字串 ⇒ 他票路徑入本票（紅）。"""
    log = ("\x00a1\x1fdocs(framepath): SPEC v21\x1f\x1fout-of-epic FRAMEPATH TODO\n\ndocs/FRAMEPATH_SPEC.md\nshared.txt\n"
           "\x00b2\x1ffeat(javis): 信箱\x1f\x1fout-of-epic Javis 信箱工具\n\nscripts/javis_mail.sh\nshared.txt\n"
           "\x00c3\x1frefactor: 刪 frame\x1f20260928-FRAMEPATH/b1\x1f\n\nmomentum/x.py\n")
    ticket, foreign = split_commit_paths(log)
    assert ticket == {"docs/FRAMEPATH_SPEC.md", "shared.txt", "momentum/x.py"}
    assert foreign == {"scripts/javis_mail.sh", "shared.txt"}
    assert foreign - ticket == {"scripts/javis_mail.sh"}
    real_ticket, real_foreign = split_commit_paths(_git("log", f"--format={_LOG_FMT}", "--name-only",
                                                        f"{HEAD_SHORT}..HEAD", "--").decode("utf-8", "replace"))
    assert "scripts/javis_mail.sh" in real_foreign - real_ticket  # 本 repo 實況：Javis 信箱工具為他票
    assert "docs/FRAMEPATH_SPEC.md" in real_ticket
    # SPEC v22 D11.1：TESTREG 提交（標題含「FRAMEPATH 閘接線」、附註內文含「HP/RM-FRAMEPATH」）判他票
    testreg = ("\x00d4\x1ffeat(testreg): Task 2.3 FRAMEPATH 閘接線\x1f20261010-TESTREG/b2\x1fout-of-epic TESTREG 第 2 批"
               "\n\nscripts/testreg.py\n"
               "\x00e5\x1fdocs(testreg): 交接\x1f\x1fout-of-epic TESTREG 第 2 批（fact_keys HP/RM-FRAMEPATH 列）"
               "\n\ntests/registry/catalog.json\n")
    t2, f2 = split_commit_paths(log + testreg)
    assert t2 == ticket
    assert f2 == foreign | {"scripts/testreg.py", "tests/registry/catalog.json"}
    assert {"scripts/testreg.py", "tests/registry/catalog.json"} <= real_foreign - real_ticket  # 本 repo 實況


def test_mutation_d11_1_testreg_commit_is_foreign():
    """M-D11.1（SPEC v22）：本票提交只認結構化附註之封閉 token——Ticket-Batch root 恰為 20260928-FRAMEPATH，或
    Governance-Scope 第二 token 恰為 FRAMEPATH；標題、附註內文之子字串、同後綴他票 root 一律判他票。本 repo 之
    d57a9f3b／14452799（TESTREG）判他票、5584102d／f7d558aa／ed3f6533（FRAMEPATH）判本票。
    mutation：判定改回「標題或附註含 FRAMEPATH」⇒ TESTREG 兩例判本票（紅）。"""
    assert not is_ticket_commit("20261010-TESTREG/b2", "out-of-epic TESTREG 第 2 批 Task 2.3 與 SPEC v41–v43 實作")
    assert not is_ticket_commit("", "out-of-epic TESTREG 第 2 批進度與交接（fact_keys HP/RM-FRAMEPATH 列之 TESTREG 段）")
    assert not is_ticket_commit("20260927-FRAMEPATH/b1", "")          # 同後綴之他票 root
    assert not is_ticket_commit("", "out-of-epic FRAMEPATHX 文件")      # token 須恰等
    assert not is_ticket_commit("", "FRAMEPATH out-of-epic")             # 只認第二個 token
    assert is_ticket_commit("20260928-FRAMEPATH/b1", "out-of-epic FRAMEPATH b1 實作")
    assert is_ticket_commit("20260928-FRAMEPATH", "")
    assert is_ticket_commit("small", "out-of-epic FRAMEPATH TODO 審查 r39 修補")
    assert is_ticket_commit("20261010-TESTREG/b2\x1e20260928-FRAMEPATH/b2", "")  # 同鍵多值
    log = ("\x00d57a\x1ffeat(testreg): Task 2.3 FRAMEPATH 閘接線\x1f20261010-TESTREG/b2\x1fout-of-epic TESTREG 第 2 批"
           "（HP/RM-FRAMEPATH 列）\n\nscripts/testreg.py\n")
    assert split_commit_paths(log) == (set(), {"scripts/testreg.py"})
    real = {sha[:8]: mine for sha, mine, _paths in parse_commit_log(commit_log())}
    assert real["d57a9f3b"] is False and real["14452799"] is False
    assert real["5584102d"] is True and real["f7d558aa"] is True and real["ed3f6533"] is True


def _commit_tmp(repo: Path, subject: str, trailers: Sequence[str], files: Dict[str, str]) -> str:
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    base = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*base, "add", "-A"], check=True, capture_output=True)
    msg = subject + ("\n\n" + "\n".join(trailers) if trailers else "")
    subprocess.run([*base, "commit", "-qm", msg], check=True, capture_output=True)
    return subprocess.run([*base, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


_TB_FOREIGN = "Ticket-Batch: 20261010-TESTREG/b2"
_TB_TICKET = "Ticket-Batch: 20260928-FRAMEPATH/b2"


def _tmp_reader(repo: Path):
    return lambda p: (repo / p).read_bytes() if (repo / p).is_file() else None


def test_mutation_d11_2a_foreign_only_governed_file_not_compared(tmp_path):
    """M-D11.2a（SPEC v22）：治理檔只被他票提交改過（含標題提 FRAMEPATH 之 TESTREG 提交）、未被本票提交改過、工作樹未改
    ⇒ ② 不比對（綠）；工作樹改了該檔 ⇒ 照常比對（紅）；本批 E 有該檔操作而未執行 ⇒ 仍比對（紅，不因他票碰過放行）。
    重錨紀錄須對得上 git 歷史（錨點至基準間不得有本票提交改該檔）。mutation：② 撤回他票排除 ⇒ 第一個斷言紅。"""
    a0 = "def test_a():\n    assert 1\n"
    b0 = "def test_b():\n    assert 1\n\n\ndef test_frame():\n    assert 2\n"
    repo, anchor = _git_tmp_repo(tmp_path, {"tests/a.py": a0, "tests/b.py": b0})
    c_foreign = _commit_tmp(repo, "feat(testreg): FRAMEPATH 閘接線", [_TB_FOREIGN, "Governance-Scope: out-of-epic TESTREG x"],
                            {"tests/a.py": a0 + "\n\ndef test_a2():\n    assert 3\n"})
    c_ticket = _commit_tmp(repo, "refactor(framepath): b2", [_TB_TICKET],
                           {"tests/b.py": "def test_b():\n    assert 1\n"})
    op = _op("delete-node", {"category": "def", "qualname": "test_frame"}, id="OP-B", path="tests/b.py", phase=1)
    disp = {"population": {"files": ["tests/a.py", "tests/b.py"]}, "operations": [op]}
    head, cur = HeadReader(anchor, repo), _tmp_reader(repo)
    foreign, _ticket = foreign_and_ticket_paths(repo, anchor)
    fo = foreign_only_paths(repo, anchor)
    assert fo == {"tests/a.py"}
    assert check_2(disp, 1, head, cur, foreign_only=fo, foreign_touched=foreign) == []
    assert check_2(disp, 1, head, cur, foreign_only=set(), foreign_touched=foreign) != []  # 不排除 ⇒ 錨點比對必紅
    # 本批 E 有該檔之操作（未執行）⇒ 即使只被他票改過仍比對
    op_a = _op("delete-node", {"category": "def", "qualname": "test_a"}, id="OP-A", path="tests/a.py", phase=1)
    assert any("tests/a.py" in e for e in check_2(dict(disp, operations=[op, op_a]), 1, head, cur,
                                                     foreign_only=fo, foreign_touched=foreign))
    # 工作樹改該檔 ⇒ 不再屬只被他票改過 ⇒ 比對（紅）
    (repo / "tests/a.py").write_text(a0 + "\n\ndef test_a2():\n    assert 4\n", encoding="utf-8")
    fo_wt = foreign_only_paths(repo, anchor)
    assert "tests/a.py" not in fo_wt
    assert check_2(disp, 1, head, cur, foreign_only=fo_wt, foreign_touched=foreign) != []
    # 重錨紀錄之歷史核對
    ok = {"rebase": {"tests/a.py": {"base_commit": c_foreign, "foreign_commits": [c_foreign]}}}
    assert rebase_history_errors(dict(disp, **ok), repo, anchor) == []
    bad_ticket = {"rebase": {"tests/b.py": {"base_commit": c_ticket, "foreign_commits": [c_ticket]}}}
    assert rebase_history_errors(dict(disp, **bad_ticket), repo, anchor) != []
    bad_list = {"rebase": {"tests/a.py": {"base_commit": c_ticket, "foreign_commits": []}}}
    assert rebase_history_errors(dict(disp, **bad_list), repo, anchor) != []
    assert rebase_schema_errors(dict(disp, **bad_list)) != []  # foreign_commits 須非空
    assert rebase_schema_errors(dict(disp, rebase={"tests/zz.py": ok["rebase"]["tests/a.py"]})) != []  # 非治理檔


_RB_ANCHOR = '''import os


def test_target(monkeypatch):
    x = run()
    frame_only()
    assert x


def test_other():
    assert 1
'''


def test_mutation_d11_2b_rebase_conflict_on_operation_target_is_red():
    """M-D11.2b（SPEC v22）：重錨後 ② 以基準位元組＋同一操作計算期望（行號類定位隨基準轉換）；他票改到本票操作之目標
    函式（頂層定義）或 JSON pointer ⇒ 衝突檢查紅（fail-closed，不得以「操作不變」放行）；他票只改不相干之定義 ⇒ 綠。
    mutation：衝突檢查恆空 ⇒ JSON 目標被他票改仍綠、Python 案無「重錨衝突」（紅）。"""
    lines = _RB_ANCHOR.splitlines()
    ln = lines.index("    frame_only()") + 1
    ops = [_op("delete-node", {"category": "stmt", "qualname": "test_target", "lineno": ln, "end_lineno": ln},
               id="OP-S", path="tests/x.py", phase=2),
           _op("delete-node", {"category": "import_alias", "lineno": 1, "name": "os"}, id="OP-I", path="tests/x.py",
               phase=2)]
    base_ok = "import sys\n\n\ndef helper():\n    return 0\n\n\n" + _RB_ANCHOR.replace("    assert 1\n", "    assert 2\n")
    base_bad = _RB_ANCHOR.replace("    x = run()\n", "    x = run(fast=True)\n")
    sha = "b" * 40
    disp = {"population": {"files": ["tests/x.py"]}, "operations": ops,
            "rebase": {"tests/x.py": {"base_commit": sha, "foreign_commits": [sha]}}}

    def run2(base: str, current: str, with_rebase: bool = True) -> List[str]:
        d = disp if with_rebase else {k: v for k, v in disp.items() if k != "rebase"}
        return check_2(d, 2, _SrcHead(_RB_ANCHOR), lambda p: current.encode(), foreign_only=set(),
                       read_at=lambda c, p: base.encode(), foreign_touched={"tests/x.py"})

    done_ok = base_ok.replace("import os\n", "").replace("    frame_only()\n", "")
    assert rebase_conflicts("tests/x.py", _RB_ANCHOR.encode(), base_ok.encode(), ops) == []
    assert run2(base_ok, done_ok) == []                       # 重錨（行號位移）後照表執行 ⇒ 綠
    assert run2(base_ok, done_ok, with_rebase=False) != []    # 未重錨 ⇒ 錨點比對紅
    assert run2(base_ok, done_ok.replace("    assert x\n", "    assert True\n")) != []  # 重錨後仍抓表外改動
    done_bad = base_bad.replace("import os\n", "").replace("    frame_only()\n", "")
    assert rebase_conflicts("tests/x.py", _RB_ANCHOR.encode(), base_bad.encode(), ops) != []
    assert any("重錨衝突" in e and "OP-S" in e for e in run2(base_bad, done_bad))
    # JSON：他票改到本票 delete-json-path 之目標（或其所在 list 長度）⇒ 衝突；改不相干之鍵 ⇒ 不衝突且照表比對
    j_anchor = {"rows": [[1, "RM-FRAMEPATH", "a"], [2, "RM-X", "b"]], "other": {"k": 1}}
    jop = [{"id": "OP-J", "phase": 2, "path": "t.json", "kind": "delete-json-path", "pointer": "/rows/0"}]
    jdisp = {"population": {"files": ["t.json"]}, "operations": jop,
             "rebase": {"t.json": {"base_commit": sha, "foreign_commits": [sha]}}}

    def runj(base: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
        return check_2(jdisp, 2, _SrcHead(json.dumps(j_anchor)), lambda p: json.dumps(current).encode(),
                       foreign_only=set(), read_at=lambda c, p: json.dumps(base).encode(), foreign_touched=set())

    j_unrelated = dict(j_anchor, other={"k": 2})
    assert runj(j_unrelated, {"rows": [[2, "RM-X", "b"]], "other": {"k": 2}}) == []
    j_target = {"rows": [[1, "RM-FRAMEPATH", "CHANGED"], [2, "RM-X", "b"]], "other": {"k": 1}}
    assert any("重錨衝突" in e for e in runj(j_target, {"rows": [[2, "RM-X", "b"]], "other": {"k": 1}}))
    j_len = {"rows": [[0, "RM-NEW", "n"]] + j_anchor["rows"], "other": {"k": 1}}
    assert rebase_conflicts("t.json", json.dumps(j_anchor).encode(), json.dumps(j_len).encode(), jop) != []
    # 整檔操作：他票改過該檔即衝突
    rop = [{"id": "OP-R", "phase": 2, "path": "s.sh", "kind": "replace-file"}]
    assert rebase_conflicts("s.sh", b"echo a\n", b"echo b\n", rop) != []


_FK_ANCHOR = {"_schema": {}, "t": {"columns": ["序", "識別碼", "狀態"],
                                   "rows": [[1, "RM-FRAMEPATH", "a"], [2, "RM-X", "b"]]}}


def _fk(rm_framepath: str, rm_x: str) -> str:
    doc = copy.deepcopy(_FK_ANCHOR)
    doc["t"]["rows"][0][2], doc["t"]["rows"][1][2] = rm_framepath, rm_x
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


def test_mutation_d11_3_ticket_commit_out_of_scope_row_reverted_by_foreign_is_red(tmp_path):
    """M-D11.3（SPEC v22）：⑥ 逐本票提交歸屬——本票提交改越界列（RM-X）、其後他票改回 ⇒ 錨點對現行淨差為零，仍紅；
    他票改越界列、本票只改允許列 ⇒ 綠；工作樹改越界列 ⇒ 紅。mutation：⑥ 改回錨點對現行整份比對（或不分提交歸屬）⇒
    第一案綠（紅）。"""
    disp = {"fact_key_rows": [{"row_id": "RM-FRAMEPATH", "phase": 1}]}
    repo, anchor = _git_tmp_repo(tmp_path / "a", {FACT_KEYS_REL: _fk("a", "b")})
    _commit_tmp(repo, "docs(framepath): 交接", [_TB_TICKET], {FACT_KEYS_REL: _fk("a", "z")})
    _commit_tmp(repo, "docs(testreg): 交接", [_TB_FOREIGN], {FACT_KEYS_REL: _fk("a", "b")})
    assert check_6(disp, 1, json.loads(_fk("a", "b")), json.loads((repo / FACT_KEYS_REL).read_text())) == []  # 淨差零
    revs = fact_key_revisions(repo, anchor)
    assert any("本票提交" in e for e in check_6_revisions(disp, 1, revs))
    repo2, anchor2 = _git_tmp_repo(tmp_path / "b", {FACT_KEYS_REL: _fk("a", "b")})
    _commit_tmp(repo2, "docs(testreg): HP-TESTREG", [_TB_FOREIGN], {FACT_KEYS_REL: _fk("a", "y")})
    _commit_tmp(repo2, "docs(framepath): b2", ["Governance-Scope: out-of-epic FRAMEPATH b2 交接"],
                {FACT_KEYS_REL: _fk("c", "y")})
    assert check_6_revisions(disp, 1, fact_key_revisions(repo2, anchor2)) == []
    (repo2 / FACT_KEYS_REL).write_text(_fk("c", "w"), encoding="utf-8")
    assert any("HEAD→工作樹" in e for e in check_6_revisions(disp, 1, fact_key_revisions(repo2, anchor2)))


def test_mutation_d17_ticket_self_revert_pair_nets_zero(tmp_path):
    """SPEC v25 D17：本票提交改越界列、其後本票提交逐字改回 ⇒ 兩段合併淨零，綠；改回但非逐字（改成他值）⇒ 紅；只在工作樹
    改回 ⇒ 紅（工作樹段不得作還原段）。mutation：不做配對（D11.3 原樣）⇒ 第一案紅；配對不要求逐字 ⇒ 第二案綠。"""
    disp = {"fact_key_rows": [{"row_id": "RM-FRAMEPATH", "phase": 1}]}
    repo, anchor = _git_tmp_repo(tmp_path / "a", {FACT_KEYS_REL: _fk("a", "b")})
    _commit_tmp(repo, "docs(framepath): 交接", [_TB_TICKET], {FACT_KEYS_REL: _fk("a", "z")})
    _commit_tmp(repo, "docs(framepath): 撤回", [_TB_TICKET], {FACT_KEYS_REL: _fk("c", "b")})
    assert check_6_revisions(disp, 1, fact_key_revisions(repo, anchor)) == []
    repo2, anchor2 = _git_tmp_repo(tmp_path / "b", {FACT_KEYS_REL: _fk("a", "b")})
    _commit_tmp(repo2, "docs(framepath): 交接", [_TB_TICKET], {FACT_KEYS_REL: _fk("a", "z")})
    _commit_tmp(repo2, "docs(framepath): 撤回錯", [_TB_TICKET], {FACT_KEYS_REL: _fk("a", "w")})
    assert any("本票提交" in e for e in check_6_revisions(disp, 1, fact_key_revisions(repo2, anchor2)))
    repo3, anchor3 = _git_tmp_repo(tmp_path / "c", {FACT_KEYS_REL: _fk("a", "b")})
    _commit_tmp(repo3, "docs(framepath): 交接", [_TB_TICKET], {FACT_KEYS_REL: _fk("a", "z")})
    (repo3 / FACT_KEYS_REL).write_text(_fk("a", "b"), encoding="utf-8")
    assert any("本票提交" in e for e in check_6_revisions(disp, 1, fact_key_revisions(repo3, anchor3)))


def test_mutation_d11_live_doc_registry_per_commit(tmp_path):
    """活文件登記表（⑦）同 ⑥ 之逐提交歸屬：他票提交登記自身 SPEC 列 ⇒ 不計（綠）；本票提交登記他票列、其後他票刪回
    ⇒ 紅；工作樹登記他票列 ⇒ 紅。mutation：改回錨點對現行整份比對 ⇒ 第一案紅、第二案綠（紅）。"""
    def reg(*rows):
        return json.dumps({"exact": [list(r) for r in rows], "prefix": []}, ensure_ascii=False) + "\n"

    base_row = ("docs/A_SPEC.md", "LIVE-SPEC")
    repo, anchor = _git_tmp_repo(tmp_path / "a", {LIVE_DOC_REGISTRY_REL: reg(base_row)})
    _commit_tmp(repo, "docs(testreg): SPEC v1", [_TB_FOREIGN], {LIVE_DOC_REGISTRY_REL: reg(base_row, ("docs/T_SPEC.md",
                                                                                                    "LIVE-SPEC"))})
    _commit_tmp(repo, "docs(framepath): 登記", [_TB_TICKET],
                {LIVE_DOC_REGISTRY_REL: reg(base_row, ("docs/T_SPEC.md", "LIVE-SPEC"),
                                            ("docs/FRAMEPATH_SPEC.md", "LIVE-SPEC"))})
    assert check_7_live_doc_revisions(ticket_revisions(LIVE_DOC_REGISTRY_REL, repo, anchor)) == []
    assert check_7_live_doc(json.loads(reg(base_row)), json.loads((repo / LIVE_DOC_REGISTRY_REL).read_text())) != []
    repo2, anchor2 = _git_tmp_repo(tmp_path / "b", {LIVE_DOC_REGISTRY_REL: reg(base_row)})
    _commit_tmp(repo2, "docs(framepath): 誤登", [_TB_TICKET], {LIVE_DOC_REGISTRY_REL: reg(base_row, ("docs/X.md", "HIST"))})
    _commit_tmp(repo2, "docs(testreg): 刪回", [_TB_FOREIGN], {LIVE_DOC_REGISTRY_REL: reg(base_row)})
    assert any("本票提交" in e for e in check_7_live_doc_revisions(ticket_revisions(LIVE_DOC_REGISTRY_REL, repo2, anchor2)))
    (repo / LIVE_DOC_REGISTRY_REL).write_text(reg(base_row, ("docs/T_SPEC.md", "LIVE-SPEC"),
                                                  ("docs/FRAMEPATH_SPEC.md", "LIVE-SPEC"), ("docs/Y.md", "HIST")),
                                              encoding="utf-8")
    assert any("HEAD→工作樹" in e for e in check_7_live_doc_revisions(ticket_revisions(LIVE_DOC_REGISTRY_REL, repo, anchor)))


def test_mutation_d11_8_frozen_change_needs_later_permit(tmp_path):
    """M-D11.8（SPEC v22 核定期）：生產碼提交之後改動凍結檔之提交，須其後有本票實作許可（round_start_head 為其後代、
    且其間無生產碼提交）涵蓋 ⇒ 綠；無許可、許可早於改動、許可前已有下一批生產碼提交、同一提交混改 ⇒ 紅。另以暫存 git
    repo 實測祖先判定與審計紀錄解析。mutation：撤除涵蓋條件或其間無生產碼條件 ⇒ 對應紅案轉綠（紅）。"""
    t, m, prod = FROZEN_ACCEPTANCE_TESTS[0], MANIFEST_REL, "momentum/x.py"
    line = ["p1", "rev", "docs", "p2", "docs2"]
    sha = {k: (k + "0" * 40)[:40] for k in line}
    idx = {sha[k]: i for i, k in enumerate(line)}  # 線性歷史：a 為 b 之祖先 ⇔ 序號不大於
    anc = lambda a, b: a in idx and b in idx and idx[a] <= idx[b]  # noqa: E731
    hist = [(sha["p1"], {prod}), (sha["rev"], {t, m}), (sha["docs"], {"docs/a.md"}), (sha["p2"], {prod}),
            (sha["docs2"], {"docs/b.md"})]
    frozen = (t, m)
    assert history_errors(hist, frozen, permits=[sha["docs"]], is_ancestor=anc) == []       # 許可涵蓋 ⇒ 綠
    assert history_errors(hist, frozen, permits=[sha["rev"]], is_ancestor=anc) == []        # 許可即在改動提交上
    assert history_errors(hist, frozen, permits=[], is_ancestor=anc) != []                  # 無許可 ⇒ 紅
    assert history_errors(hist, frozen, permits=[sha["p1"]], is_ancestor=anc) != []         # 許可早於改動 ⇒ 紅
    assert history_errors(hist, frozen, permits=[sha["docs2"]], is_ancestor=anc) != []      # 許可前已實作下一批 ⇒ 紅
    mixed = [(sha["p1"], {prod}), (sha["rev"], {t, prod}), (sha["docs"], {"docs/a.md"})]
    assert history_errors(mixed, frozen, permits=[sha["docs"]], is_ancestor=anc) != []      # 同一提交混改 ⇒ 紅
    # 真實 git：祖先判定與審計紀錄
    repo, anchor = _git_tmp_repo(tmp_path, {"README": "x\n"})
    c_prod = _commit_tmp(repo, "b1", [_TB_TICKET], {prod: "a = 1\n"})
    c_rev = _commit_tmp(repo, "rev", ["Governance-Scope: out-of-epic FRAMEPATH TODO 修訂"], {t: "assert 1\n"})
    c_doc = _commit_tmp(repo, "doc", [], {"docs/a.md": "x\n"})
    real_hist = [(c_prod, {prod}), (c_rev, {t}), (c_doc, {"docs/a.md"})]
    ev = lambda h, root=TICKET_ROOT: json.dumps({"event": "impl_token_issued", "root": root,  # noqa: E731
                                                 "round_start_head": h})
    permits = approval_permits(["=== x ===", ev(c_prod), ev(c_doc, "20261010-TESTREG"), ev(c_doc)])
    assert permits == [c_prod, c_doc]
    ga = lambda a, b: git_is_ancestor(a, b, repo)  # noqa: E731
    assert history_errors(real_hist, frozen, permits=permits, is_ancestor=ga) == []
    assert history_errors(real_hist, frozen, permits=permits[:1], is_ancestor=ga) != []
    assert history_errors(real_hist, frozen, permits=approval_permits([ev(c_doc, "20261010-TESTREG")]),
                          is_ancestor=ga) != []                                              # 他票許可不算


def _plaindocs(*rows) -> Dict[str, Any]:
    return {"_schema": {}, "plaindocs-index": {"target": ["白話說明/README.md"], "render": "table",
                                               "columns": ["你想問", "打開這份", "維護規則"], "rows": [list(r) for r in rows]}}


def test_mutation_d11_9_plaindocs_index_ticket_rows_only():
    """M-D11.9（SPEC v22）：⑥ 另准本票段增刪 plaindocs-index 中「白話審閱文件路徑位於 白話說明/ 且檔名以 FRAMEPATH
    起首」之列；增他票列（TESTREG）、問句含 FRAMEPATH 而連結非 FRAMEPATH 檔、以 ../ 逃出 白話說明/、改他列 ⇒ 紅。
    本 repo 之 8 筆本票提交（e506a570 等）增刪本票審閱列 ⇒ 不紅。mutation：判定恆真或改看問句欄 ⇒ 紅案轉綠（紅）。"""
    disp = {"fact_key_rows": [{"row_id": "RM-FRAMEPATH", "phase": 1}]}
    now = ("現在在做什麼？", "[現在做到哪.md](現在做到哪.md)", "整段覆蓋")
    before = _plaindocs(now)
    ok_rows = [("FRAMEPATH 規格第 22 版要我核可什麼？", "[FRAMEPATH規格v22修正審閱.md](FRAMEPATH規格v22修正審閱.md)", "核可後封存"),
               ("FRAMEPATH 舊審閱", "[FRAMEPATH規格v16修正審閱.md](Archived/FRAMEPATH規格v16修正審閱.md)", "封存")]
    for r in ok_rows:
        assert check_6(disp, 1, before, _plaindocs(now, r)) == []        # 增本票列
        assert check_6(disp, 1, _plaindocs(now, r), before) == []        # 刪本票列
    bad_rows = [("TESTREG 規格要我核可什麼？", "[TESTREG規格審閱.md](TESTREG規格審閱.md)", "核可後封存"),
                ("FRAMEPATH 規格要我核可什麼？", "[規格審閱.md](規格審閱.md)", "核可後封存"),
                ("FRAMEPATH 越界", "[FRAMEPATH.md](../docs/FRAMEPATH.md)", "x"),
                ("FRAMEPATH 純文字", "FRAMEPATH規格v22修正審閱.md", "x")]
    for r in bad_rows:
        assert check_6(disp, 1, before, _plaindocs(now, r)) != [], r
    assert check_6(disp, 1, before, _plaindocs((now[0], now[1], "改了"))) != []           # 改他列 ⇒ 紅
    # 他列改成本票連結（借本票豁免刪他列）⇒ 紅
    assert check_6(disp, 1, before, _plaindocs(ok_rows[0])) != []
    real = {label.split()[1][:8]: (b, a) for label, b, a in fact_key_revisions() if label.startswith("本票提交")}
    for c in ("e506a570", "dc91faa4", "d252ca63", "6807e56a", "0eaddd11", "bfd683b0", "d0461057", "27d80c04"):
        b, a = real[c]
        assert canonical_json(b.get(PLAINDOCS_INDEX_KEY)) != canonical_json(a.get(PLAINDOCS_INDEX_KEY)), c
        assert check_6(load_json(DISPOSITION_REL), 1, b, a) == [], c


def test_mutation_d11_11c_text_apply_uses_rebase_base():
    """SPEC v22 D11.11(c)：text_apply 對有 rebase 紀錄之檔以 base_commit 位元組套用（他票改動保留、行號類定位隨基準
    轉換），結果過 ②；衝突 ⇒ 拒套。mutation：text_apply 忽略 rebase（用錨點位元組）⇒ 他票改動遺失、② 紅（紅）。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("framepath_text_apply",
                                                  REPO / "handoffs/run_receipts/framepath_probes/text_apply.py")
    ta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ta)
    lines = _RB_ANCHOR.splitlines()
    ln = lines.index("    frame_only()") + 1
    ops = [_op("delete-node", {"category": "stmt", "qualname": "test_target", "lineno": ln, "end_lineno": ln},
               id="OP-S", path="tests/x.py", phase=2)]
    base = "import sys\n\n\ndef helper():\n    return 0\n\n\n" + _RB_ANCHOR
    sha = "b" * 40
    disp = {"population": {"files": ["tests/x.py"]}, "operations": ops,
            "rebase": {"tests/x.py": {"base_commit": sha, "foreign_commits": [sha]}}}
    head = _SrcHead(_RB_ANCHOR)
    read_at = lambda c, p: base.encode()  # noqa: E731
    new, diff = ta.apply_file(disp, "tests/x.py", 2, head, read_at)
    assert diff is None
    text = new.decode("utf-8")
    assert "def helper():" in text and "import sys" in text and "frame_only()" not in text
    assert check_2(disp, 2, head, lambda p: new, foreign_only=set(), read_at=read_at, foreign_touched=set()) == []
    bad_base = _RB_ANCHOR.replace("    x = run()\n", "    x = run(fast=True)\n")
    with pytest.raises(SystemExit):
        ta.apply_file(disp, "tests/x.py", 2, head, lambda c, p: bad_base.encode())
    plain, _ = ta.apply_file({k: v for k, v in disp.items() if k != "rebase"}, "tests/x.py", 2, head)
    assert "def helper():" not in plain.decode("utf-8")  # 無 rebase 紀錄 ⇒ 錨點位元組（對照）


def test_mutation_affected_gate_d13_external_import_names_not_s2():
    """SPEC v24 D13：S2 不計自標準庫／第三方匯入之綁定名之刪改；自生產模組（momentum／api／config）匯入、相對匯入、同名
    另有非匯入綁定者照舊計入。mutation：外部匯入名入 S2（b2 實測選入 8,304 項）⇒ 第一斷言紅；生產匯入名被排除 ⇒ 第二斷言紅。"""
    g = _affected_gate()
    body = ast.parse("import numpy as np\nimport time\nfrom pathlib import Path\nfrom momentum.core import config\n"
                     "from . import sibling\nimport queue\nqueue = None\n").body
    ext = g._external_import_names(body)
    assert {"np", "time", "Path"} <= ext and "queue" not in ext
    assert not ({"config", "sibling"} & ext)


def test_mutation_affected_gate_d14_hardware_blocked():
    """SPEC v25 D14：登記於 tests/hardware_requirements.json 之大機器專用測試，機器實體記憶體低於需求即不選入、達標即選入。
    mutation：不比對記憶體（恆排除或恆選入）⇒ 第一或第二斷言紅；登記檔缺兩支 RM-FULLSCALE 完整版 ⇒ 第三斷言紅。"""
    g = _affected_gate()
    entries = g.load_hardware_requirements(REPO)
    gib = 1 << 30
    low = g.hardware_blocked(entries, 8 * gib)
    assert set(low) == {e["path"] for e in entries} and all(v["ticket"] == "RM-FULLSCALE" for v in low.values())
    assert g.hardware_blocked(entries, 64 * gib) == {}
    assert {"tests/feature_engineering/test_ff_fullchain_truncation_mr.py",
            "tests/feature_engineering/test_ff_multitf_truncation_mr.py"} <= set(low)


@pytest.mark.parametrize("bad", [
    {"path": "tests/feature_engineering/test_no_such_file.py", "ticket": "RM-FULLSCALE", "min_memory_gib": 24, "reason": "x"},
    {"path": "tests/feature_engineering/test_ff_fullchain_truncation_mr.py", "ticket": "OTHER", "min_memory_gib": 24,
     "reason": "x"},
    {"path": "tests/feature_engineering/test_ff_fullchain_truncation_mr.py", "ticket": "RM-FULLSCALE", "min_memory_gib": 0,
     "reason": "x"},
    {"path": "tests/feature_engineering/test_ff_fullchain_truncation_mr.py", "ticket": "RM-FULLSCALE",
     "min_memory_gib": True, "reason": "x"},
    {"path": "tests/feature_engineering/test_ff_fullchain_truncation_mr.py", "ticket": "RM-FULLSCALE", "min_memory_gib": 24,
     "reason": " "},
])
def test_mutation_affected_gate_d14_registry_fail_closed(tmp_path, bad):
    """SPEC v25 D14：登記檔條目不合格式（路徑不存在、ticket 非 RM-FULLSCALE、需求非正整數、無理由）⇒ GateError。"""
    g = _affected_gate()
    target = tmp_path / "tests/feature_engineering/test_ff_fullchain_truncation_mr.py"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    (tmp_path / g.HARDWARE_REQUIREMENTS_REL).write_text(json.dumps({"entries": [bad]}), encoding="utf-8")
    with pytest.raises(g.GateError):
        g.load_hardware_requirements(tmp_path)


def test_mutation_affected_gate_d14_plan_wiring():
    """SPEC v25 D14：plan 以本機記憶體套登記、把被擋檔之 nodeid 自 selected 移入 skipped 並記於收據 hardware_blocked，
    且 inputs_digest 綁機器記憶體。mutation：刪 plan 之套用（或不移出 selected、不記收據、digest 不綁記憶體）⇒ 紅。"""
    src = (REPO / "scripts/framepath_affected_gate.py").read_text(encoding="utf-8")
    fns = {n.name: ast.get_source_segment(src, n) for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    assert "hardware_blocked(load_hardware_requirements(repo), machine_memory_bytes())" in fns["plan"]
    assert "selected.pop(nid)" in fns["plan"] and '"hardware_blocked": blocked' in fns["plan"]
    assert "machine_memory_bytes()" in fns["plan_inputs_digest"]


def test_mutation_affected_gate_d14_registry_missing_or_duplicate(tmp_path):
    """SPEC v25 D14：登記檔不存在 ⇒ 空清單（不排除＝全照常選入）；路徑重複 ⇒ GateError。"""
    g = _affected_gate()
    assert g.load_hardware_requirements(tmp_path) == []
    target = tmp_path / "tests/test_x.py"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    row = {"path": "tests/test_x.py", "ticket": "RM-FULLSCALE", "min_memory_gib": 24, "reason": "x"}
    (tmp_path / g.HARDWARE_REQUIREMENTS_REL).write_text(json.dumps({"entries": [row, row]}), encoding="utf-8")
    with pytest.raises(g.GateError):
        g.load_hardware_requirements(tmp_path)


def _d16_traced_python(tmp_path, code: str, extra_env=None):
    """以受影響閘同法（PYTHONPATH 首位 framepath_trace_site、FRAMEPATH_TRACE_DIR）跑一段 Python，回 trace 目錄。"""
    g = _affected_gate()
    trace = tmp_path / "trace"
    env = dict(os.environ, PYTHONPATH=f"{g.TRACE_SITE_DIR}{os.pathsep}{REPO}", **{g.TRACE_DIR_ENV: str(trace)})
    env.update(extra_env or {})
    subprocess.run([sys.executable, "-c", code], cwd=str(tmp_path), env=env, check=True, capture_output=True)
    return g, trace


def test_mutation_affected_gate_d16_trace_records_reads_children_and_untraced(tmp_path):
    """SPEC v25 D16：讀取記錄器實跑——父行程讀檔、列目錄、spawn 之 multiprocessing 子行程讀檔皆入 trace；寫入不入；
    非 Python 子行程 ⇒ untraced ⇒ trace_record 回 None。mutation：記錄器漏子行程或漏 listdir ⇒ 對應斷言紅。"""
    repo = tmp_path / "repo"
    (repo / "d").mkdir(parents=True)
    (repo / "a.txt").write_text("A", encoding="utf-8")
    (repo / "b.txt").write_text("B", encoding="utf-8")
    code = textwrap.dedent(f"""
        import multiprocessing as mp, os
        def child(p):
            open(p).read()
        if __name__ == "__main__":
            open({str(repo / 'a.txt')!r}).read()
            os.listdir({str(repo / 'd')!r})
            open({str(repo / 'w.txt')!r}, "w").write("x")
            ctx = mp.get_context("spawn")
            pr = ctx.Process(target=child, args=({str(repo / 'b.txt')!r},)); pr.start(); pr.join()
    """)
    trace = tmp_path / "trace"
    script = tmp_path / "run_trace.py"
    script.write_text(code, encoding="utf-8")
    g = _affected_gate()
    env = dict(os.environ, PYTHONPATH=f"{g.TRACE_SITE_DIR}{os.pathsep}{REPO}", **{g.TRACE_DIR_ENV: str(trace)})
    subprocess.run([sys.executable, str(script)], cwd=str(tmp_path), env=env, check=True, capture_output=True)
    rec = g.trace_record(trace, repo)
    assert rec is not None and rec["processes"] >= 2
    assert {"a.txt", "b.txt"} <= set(rec["files"]) and "w.txt" not in rec["files"]
    assert "d" in rec["dirs"]
    (tmp_path / "x").mkdir()
    g2, trace2 = _d16_traced_python(tmp_path / "x", "import subprocess; subprocess.run(['true'])")
    assert g2.trace_record(trace2, repo) is None


def test_mutation_affected_gate_d16_trace_valid_only_on_read_inputs(tmp_path):
    """SPEC v25 D16：trace_valid——未讀之檔改動仍有效；讀過之檔改動、被列目錄新增項目、venv 套件變動皆失效；
    trace_record 於任一行程未完成或有錯誤時回 None。mutation：trace_valid 恆真／不比對目錄 ⇒ 紅。"""
    g = _affected_gate()
    repo = tmp_path / "repo"
    (repo / "d").mkdir(parents=True)
    (repo / "read.txt").write_text("1", encoding="utf-8")
    (repo / "other.txt").write_text("1", encoding="utf-8")
    trace = tmp_path / "trace"
    trace.mkdir()
    root = str(repo.resolve())
    row = {"pid": 1, "complete": True, "files": [f"{root}/read.txt", f"{root}/venv/x.py", f"{root}/m/__pycache__/a.pyc"],
           "dirs": [f"{root}/d"], "untraced": [], "errors": 0}
    (trace / "1.json").write_text(json.dumps(row), encoding="utf-8")
    rec = g.trace_record(trace, repo)
    assert set(rec["files"]) == {"read.txt"} and set(rec["dirs"]) == {"d"}
    assert g.trace_valid(rec, repo)
    (repo / "other.txt").write_text("2", encoding="utf-8")
    assert g.trace_valid(rec, repo)
    (repo / "read.txt").write_text("2", encoding="utf-8")
    assert not g.trace_valid(rec, repo)
    (repo / "read.txt").write_text("1", encoding="utf-8")
    (repo / "d" / "new").write_text("", encoding="utf-8")
    assert not g.trace_valid(rec, repo)
    for bad in ({"complete": False}, {"errors": 1}, {"untraced": [{"prog": "bash"}]}):
        (trace / "1.json").write_text(json.dumps({**row, **bad}), encoding="utf-8")
        assert g.trace_record(trace, repo) is None


def _d16_runner_fixture(tmp_path, monkeypatch):
    g = _affected_gate()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "in.txt").write_text("1", encoding="utf-8")
    (repo / "doc.md").write_text("1", encoding="utf-8")
    xml = tmp_path / "out" / "t.xml"
    xml.parent.mkdir()
    xml.write_text('<testsuites><testsuite><testcase classname="tests.t" name="test_a"/></testsuite></testsuites>',
                   encoding="utf-8")
    snap_of = lambda root: {p.name: g._path_state(p) for p in sorted(root.iterdir())}  # noqa: E731
    monkeypatch.setattr(g, "snapshot_map", snap_of)
    monkeypatch.setattr(g, "restore_generated", lambda cwd: None)
    calls = []
    monkeypatch.setattr(g, "run_file", lambda *a, **k: (calls.append(1), (0, {"tests/t.py::test_a": {"outcome": "passed"}}))[1])
    r = g.Runner(tmp_path / "out", None, 1)
    snap = json.dumps(snap_of(repo), sort_keys=True, ensure_ascii=False)
    ref = hashlib.sha256(snap.encode("utf-8")).hexdigest()
    r._snapshot_path(ref).parent.mkdir(parents=True)
    r._snapshot_path(ref).write_text(snap, encoding="utf-8")
    trace = {"files": {"in.txt": g._path_state(repo / "in.txt")}, "dirs": {}, "venv": g.venv_fingerprint(repo),
             "tool": g._trace_tool_hash(repo)}

    def write_meta(state_key="old"):
        xml.with_suffix(".meta.json").write_text(json.dumps({"state_key": state_key, "rc": 0, "file": "tests/t.py",
                                                             "call_id": "C", "snapshot": ref, "trace": trace}),
                                                 encoding="utf-8")

    def run(call_id="C", key="new"):
        r.run("tests/t.py", xml, repo, {}, None, (), key, ["tests/t.py::test_a"], call_id=call_id)
    return g, repo, calls, write_meta, run


def test_mutation_affected_gate_d16_runner_reuses_by_trace(tmp_path, monkeypatch):
    """SPEC v25 D16：Runner.run——state_key 不同但 call_id 相同且 trace 仍有效 ⇒ 沿用不呼叫 pytest；trace 失效或 call_id
    不同 ⇒ 重跑。mutation：沿用條件不看 trace 或不看 call_id ⇒ 紅。"""
    g = _affected_gate()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "in.txt").write_text("1", encoding="utf-8")
    xml = tmp_path / "out" / "t.xml"
    xml.parent.mkdir()
    xml.write_text('<testsuites><testsuite><testcase classname="tests.t" name="test_a"/></testsuite></testsuites>',
                   encoding="utf-8")
    trace = {"files": {"in.txt": g._path_state(repo / "in.txt")}, "dirs": {}, "venv": g.venv_fingerprint(repo),
             "tool": g._trace_tool_hash(repo)}
    # r69：call_id 枝另須呼叫開始時之快照（其後只改未讀文字檔方可沿用）；本案快照＝目前，改動為空
    snap_of = lambda root: {p.name: g._path_state(p) for p in sorted(root.iterdir())}  # noqa: E731
    monkeypatch.setattr(g, "snapshot_map", snap_of)
    snap = json.dumps(snap_of(repo), sort_keys=True, ensure_ascii=False)
    ref = hashlib.sha256(snap.encode("utf-8")).hexdigest()
    (tmp_path / "out" / "snapshots").mkdir()
    (tmp_path / "out" / "snapshots" / f"{ref}.json").write_text(snap, encoding="utf-8")
    trace_meta = {"call_id": "C", "trace": trace, "snapshot": ref}
    xml.with_suffix(".meta.json").write_text(json.dumps({"state_key": "old", "rc": 0, "file": "tests/t.py",
                                                         **trace_meta}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(g, "restore_generated", lambda cwd: None)
    monkeypatch.setattr(g, "run_file", lambda *a, **k: (calls.append(1), (0, {"tests/t.py::test_a": {"outcome": "passed"}}))[1])
    r = g.Runner(tmp_path / "out", None, 1)
    r.run("tests/t.py", xml, repo, {}, None, (), "new", ["tests/t.py::test_a"], call_id="C")
    assert calls == []
    r.run("tests/t.py", xml, repo, {}, None, (), "new", ["tests/t.py::test_a"], call_id="D")
    assert calls == [1]
    xml.with_suffix(".meta.json").write_text(json.dumps({"state_key": "old", "rc": 0, "file": "tests/t.py",
                                                         **trace_meta}), encoding="utf-8")
    (repo / "in.txt").write_text("2", encoding="utf-8")
    r.run("tests/t.py", xml, repo, {}, None, (), "new", ["tests/t.py::test_a"], call_id="C")
    assert calls == [1, 1]


def test_mutation_affected_gate_d16_r69_unread_text_change_reused(tmp_path, monkeypatch):
    """r69：call_id 相同、trace 有效、快照至今只改未讀之文字檔（doc.md）⇒ 沿用。mutation：任何改動皆失效 ⇒ 紅。"""
    g, repo, calls, write_meta, run = _d16_runner_fixture(tmp_path, monkeypatch)
    write_meta()
    (repo / "doc.md").write_text("2", encoding="utf-8")
    run()
    assert calls == []


def test_mutation_affected_gate_d16_r69_state_key_branch_requires_trace(tmp_path, monkeypatch):
    """r69 CODEX-R69-P1-01／GROK-R69-P1-02：meta 帶 trace 時，state_key 相同亦須 trace 仍有效（handoffs 不入 state_key，
    讀過之收據改動只由 trace 看見）。mutation：state_key 枝短路不檢 trace ⇒ 紅。"""
    g, repo, calls, write_meta, run = _d16_runner_fixture(tmp_path, monkeypatch)
    write_meta(state_key="SAME")
    (repo / "in.txt").write_text("2", encoding="utf-8")
    run(key="SAME")
    assert calls == [1]


@pytest.mark.parametrize("path, reusable", [
    ("docs/x.md", True),                       # 未讀之文字檔
    ("tests/other/test_y.py", True),           # 未讀之他測試檔內容改動
    ("data:data_cache/feature_klines/kline_cache.h5", False),  # GROK-R69-P0-01：DATA_INPUTS（h5py 之 C 層讀取不入 trace）
    ("tests/_golden/x/frame.h5", False),       # 資料類副檔名（C 層讀取可能）
    ("tests/_golden/x/frame.parquet", False),
    ("tests/feature_engineering/conftest.py", False),  # pytest 以存在檢查載入
    ("pytest.ini", False),
    ("read.json", False),                      # 讀過之檔
    ("ign:data_cache/kline_cache.h5", False),  # r70 CODEX-R70-P1-01：被忽略之資料類檔（h5py 讀取）
])
def test_mutation_affected_gate_d16_r69_changes_reusable(path, reusable):
    """r69：快照至今之改動逐類判定（changes_reusable）。mutation：不判資料類／DATA_INPUTS／設定類 ⇒ 對應案紅。"""
    g = _affected_gate()
    rec = {"files": {"read.json": "x"}, "dirs": {}}
    then = {"read.json": "x"}
    then[path] = "a"
    now = dict(then)
    now[path] = "b"
    assert g.changes_reusable(then, now, rec, "tests/feature_engineering/test_z.py") is reusable


def test_mutation_affected_gate_d16_r70_snapshot_includes_ignored_data(tmp_path):
    """r70 CODEX-R70-P1-01：snapshot_map 收被 git 忽略之資料類檔（鍵 ign:）並以內容 sha256 記；工具目錄（.codex 等）與
    非資料類被忽略檔不收；內容改動 ⇒ 快照不同。mutation：不收被忽略資料檔 ⇒ 第一斷言紅。"""
    g = _affected_gate()
    repo = tmp_path / "repo"
    (repo / "data_cache").mkdir(parents=True)
    (repo / ".codex").mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text("data_cache/\n.codex/\n*.log\n", encoding="utf-8")
    (repo / "data_cache" / "kline_cache.h5").write_bytes(b"v1")
    (repo / ".codex" / "state.json").write_text("{}", encoding="utf-8")
    (repo / "run.log").write_text("x", encoding="utf-8")
    snap = g.snapshot_map(repo)
    assert "ign:data_cache/kline_cache.h5" in snap
    assert not any(k.startswith("ign:.codex/") or k == "ign:run.log" for k in snap)
    (repo / "data_cache" / "kline_cache.h5").write_bytes(b"v2")
    assert g.snapshot_map(repo)["ign:data_cache/kline_cache.h5"] != snap["ign:data_cache/kline_cache.h5"]
    # 被忽略之 .json（Python 讀取、必入 trace）以原路徑為鍵：屬文字類，讀過才失效
    (repo / "data_cache" / "registry.json").write_text("{}", encoding="utf-8")
    snap2 = g.snapshot_map(repo)
    assert "data_cache/registry.json" in snap2 and "ign:data_cache/registry.json" not in snap2
    assert g.changes_reusable(snap2, {**snap2, "data_cache/registry.json": "changed"}, {"files": {}, "dirs": {}},
                              "tests/t/test_x.py") is True


def test_mutation_affected_gate_d16_r69_added_py_near_test_invalidates():
    """r69：測試檔所在目錄（及上層）或讀過檔之目錄新增／刪除 .py ⇒ 失效（套件探索靠存在檢查）；無關目錄新增 .py ⇒ 可沿用。"""
    g = _affected_gate()
    rec = {"files": {"momentum/a/mod.py": "x"}, "dirs": {}}
    base = {"momentum/a/mod.py": "x"}
    t = "tests/feature_engineering/test_z.py"
    assert g.changes_reusable(base, {**base, "tests/feature_engineering/helper_new.py": "n"}, rec, t) is False
    assert g.changes_reusable(base, {**base, "momentum/a/new.py": "n"}, rec, t) is False
    assert g.changes_reusable(base, {**base, "scripts/tool_new.py": "n"}, rec, t) is True


def test_mutation_affected_gate_d18_default_out_persistent():
    """SPEC v25 D18：結果目錄預設於 repo 內被 git 忽略之 .testreg/framepath_gate_b<N>（重開機不清）；main 以之為 --out 預設。
    mutation：預設改回系統暫存區（tempfile.gettempdir）⇒ 第一或第三斷言紅。"""
    g = _affected_gate()
    d = g.default_out_dir(REPO, 2)
    assert d.resolve().is_relative_to(REPO.resolve()) and d.parts[-2:] == (".testreg", "framepath_gate_b2")
    assert subprocess.run(["git", "check-ignore", "-q", str(d / "x")], cwd=REPO).returncode == 0
    src = (REPO / "scripts/framepath_affected_gate.py").read_text(encoding="utf-8")
    assert "Path(args.out or default_out_dir(REPO, batch))" in src and "tempfile.gettempdir()" not in src


def test_mutation_affected_gate_d18_junit_from_ledger_matches_pytest_identity(tmp_path):
    """D18（審查 r73）：junit_from_ledger 由紀錄器同式之紀錄（exception_type＋str(例外) 首行）重建之 junit，其
    failure_identity 與 pytest 實產 junit 逐項相同（call 斷言失敗、多行例外、setup 失敗）。mutation：寫 type 屬性或訊息
    只放首行 ⇒ 紅。"""
    g = _affected_gate()
    proj = tmp_path / "proj"
    (proj / "tests").mkdir(parents=True)
    (proj / "tests" / "test_x.py").write_text(textwrap.dedent("""
        import pytest
        @pytest.fixture
        def broken():
            raise RuntimeError("setup boom")
        def test_assert():
            assert 1 == 2
        def test_multiline():
            raise ValueError("bad value\\nsecond line")
        def test_setup(broken):
            pass
        def test_ok():
            pass
    """), encoding="utf-8")
    (proj / "tests" / "conftest.py").write_text(textwrap.dedent("""
        import json, pytest
        RECS = {}
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(item, call):
            out = yield
            rep = out.get_result()
            if call.excinfo is not None and rep.failed:
                v = call.excinfo.value
                head = str(v).strip().splitlines()[0][:300] if str(v).strip() else ""
                RECS[item.nodeid] = {"nodeid": item.nodeid, "outcome": "failed", "phase_failed": call.when,
                                     "exception_type": type(v).__name__, "exception_head": head}
            elif call.when == "call" and rep.passed:
                RECS.setdefault(item.nodeid, {"nodeid": item.nodeid, "outcome": "passed"})
        def pytest_sessionfinish(session):
            open("recs.json", "w").write(json.dumps(list(RECS.values())))
    """), encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml=real.xml",
                    "tests/test_x.py"], cwd=str(proj), capture_output=True)
    real = g.junit_results((proj / "real.xml").read_text(encoding="utf-8"), "tests/test_x.py")
    recs = json.loads((proj / "recs.json").read_text(encoding="utf-8"))
    rebuilt = g.junit_results(g.junit_from_ledger("tests/test_x.py", recs), "tests/test_x.py")
    assert set(real) == set(rebuilt) and len(real) == 4
    for nid in real:
        assert g.failure_identity(real[nid]) == g.failure_identity(rebuilt[nid]), nid


@pytest.mark.parametrize("outcome", ["skipped", "xfailed", "xpassed"])
def test_mutation_affected_gate_d18_junit_from_ledger_rejects_unreconstructable(outcome):
    """審查 r74 CODEX-R74-P1-01：紀錄器不存 skip／xfail 原因 ⇒ junit_from_ledger 對 skipped／xfailed／xpassed 拒絕（ValueError），
    還原程序據以不還原該檔、交閘重跑。mutation：以空訊息輸出 skipped ⇒ 不拋例外 ⇒ 紅。"""
    g = _affected_gate()
    with pytest.raises(ValueError):
        g.junit_from_ledger("tests/t.py", [{"nodeid": "tests/t.py::test_a", "outcome": outcome}])
    assert "<failure" not in g.junit_from_ledger("tests/t.py", [{"nodeid": "tests/t.py::test_a", "outcome": "passed"}])


def test_mutation_affected_gate_d18_untraced_reuse_requires_ignored_inputs_unchanged(tmp_path, monkeypatch):
    """D18（審查 r73 CODEX-R73-P1-02）：無 trace 之沿用／還原結果，state_key 相同仍須被忽略之資料（data:／ign:／ignt:）
    自寫入快照後未變；缺快照 ⇒ 不沿用；一般無 trace 結果（非沿用／還原）照舊只依 state_key。mutation：不檢快照 ⇒ 紅。"""
    g = _affected_gate()
    repo = tmp_path / "repo"
    repo.mkdir()
    xml = tmp_path / "out" / "t.xml"
    xml.parent.mkdir()
    xml.write_text('<testsuites><testsuite><testcase classname="tests.t" name="test_a"/></testsuite></testsuites>',
                   encoding="utf-8")
    state = {"ignt:data_cache/features/registry.json": "v1", "ign:data_cache/k.h5": "h1", "docs/x.md": "d1"}
    monkeypatch.setattr(g, "snapshot_map", lambda root: dict(state))
    monkeypatch.setattr(g, "restore_generated", lambda cwd: None)
    calls = []
    monkeypatch.setattr(g, "run_file", lambda *a, **k: (calls.append(1), (0, {"tests/t.py::test_a": {"outcome": "passed"}}))[1])
    r = g.Runner(tmp_path / "out", None, 1)
    snap = json.dumps(dict(state), sort_keys=True)
    ref = hashlib.sha256(snap.encode("utf-8")).hexdigest()
    r._snapshot_path(ref).parent.mkdir(parents=True)
    r._snapshot_path(ref).write_text(snap, encoding="utf-8")

    def meta(**extra):
        xml.with_suffix(".meta.json").write_text(json.dumps({"state_key": "K", "rc": 0, "file": "tests/t.py",
                                                             "trace": None, **extra}), encoding="utf-8")

    def run():
        r.run("tests/t.py", xml, repo, {}, None, (), "K", ["tests/t.py::test_a"])
    meta(recovered_from={"session_id": "s"}, snapshot=ref)
    state["docs/x.md"] = "d2"
    run()
    assert calls == []  # 只改已追蹤文字檔（由 state_key 綁）⇒ 沿用
    meta(recovered_from={"session_id": "s"}, snapshot=ref)
    state["ignt:data_cache/features/registry.json"] = "v2"
    run()
    assert calls == [1]  # 被忽略之 .json 改動 ⇒ 重跑
    meta(recovered_from={"session_id": "s"})
    state["ignt:data_cache/features/registry.json"] = "v1"
    run()
    assert calls == [1, 1]  # 缺快照 ⇒ 重跑
    meta()
    run()
    assert calls == [1, 1]  # 一般無 trace 結果 ⇒ 只依 state_key


def test_mutation_affected_gate_d11_12_empty_collect(tmp_path):
    """SPEC v22 D11.12：受影響閘 collect 對無測試函式之檔（pytest rc 5 且輸出含 no tests collected）於 plan 視為空集合
    （不選入、記 empty_collect）；A 組（未給 sink）、匯入錯誤（rc 2）、rc 5 但無該字樣 ⇒ 仍 GateError。以子行程實跑
    pytest（暫存目錄之 pytest.ini 同本 repo 之 addopts，`-v` 抵銷一個 `-q` 使摘要行輸出）。
    mutation：rc 5 一律放行（不看字樣）、或任何非 0 皆放行 ⇒ 對應紅案轉綠（紅）。"""
    g = _affected_gate()
    assert g.is_empty_collect(5, "\nno tests collected in 0.01s\n")
    assert not g.is_empty_collect(5, "")
    assert not g.is_empty_collect(2, "no tests collected")
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -v --tb=short --import-mode=importlib\n", encoding="utf-8")
    (tmp_path / "test_empty.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "test_broken.py").write_text("import framepath_no_such_module_xyz\n", encoding="utf-8")
    (tmp_path / "test_ok.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(REPO))
    sink: List[str] = []
    assert g.collect("test_empty.py", tmp_path, env, sink) == [] and sink == ["test_empty.py"]
    with pytest.raises(g.GateError):  # A 組：未給 sink ⇒ 照舊拒
        g.collect("test_empty.py", tmp_path, env)
    with pytest.raises(g.GateError):  # 匯入錯誤 rc≠5 ⇒ 給 sink 亦拒
        g.collect("test_broken.py", tmp_path, env, sink)
    assert sink == ["test_empty.py"]
    assert g.collect("test_ok.py", tmp_path, env, sink) == ["test_ok.py::test_a"]
    # 審查 r63：plan 經 collect_or_empty 以三參數呼叫 collect（TESTREG 凍結驗收以三參數替身替換 collect）
    sink2: List[str] = []
    assert g.collect_or_empty("test_empty.py", tmp_path, env, sink2) == [] and sink2 == ["test_empty.py"]
    with pytest.raises(g.GateError):
        g.collect_or_empty("test_broken.py", tmp_path, env, sink2)
    assert g.collect_or_empty("test_ok.py", tmp_path, env, sink2) == ["test_ok.py::test_a"]
    sel, skip = g.select_expected({"test_empty.py": [], "test_ok.py": ["test_ok.py::test_a"]},
                                  {"test_ok.py": {"refs": {}, "taint": {}, "heavy": False}}, {}, {}, [], [], False)
    assert set(sel) == {"test_ok.py::test_a"} and skip == {}


def test_mutation_d11_7_inventory_hand_edit_is_red():
    """M-D11.7（SPEC v22）：⑦ 對 collect 清冊做生成物完整性檢查——以現行樹 collect 重產之內容 ⇒ 不紅；手動改一行或刪
    一行 ⇒ 紅；未給 oracle ⇒ 照一般越界（不無條件豁免）。實跑 collect（單檔，秒級），結束後清冊位元組原樣寫回。
    mutation：清冊無條件豁免 ⇒ 手改一行仍綠（紅）。"""
    target = "tests/feature_engineering/test_ff_fullchain_truncation_mr.py"
    before = current_bytes(GENERATED_INVENTORY_REL)
    good = regenerate_inventory([target])
    assert current_bytes(GENERATED_INVENTORY_REL) == before  # 重產不留副作用
    assert good != INVENTORY_EMPTY and len(good.splitlines()) >= 2
    cache = {(target,): good}

    def regen(files):
        key = tuple(files)
        if key not in cache:
            cache[key] = regenerate_inventory(files)
        return cache[key]

    lines = good.decode("utf-8").splitlines()
    tampered = ("\n".join([lines[0] + "_x"] + lines[1:]) + "\n").encode("utf-8")
    dropped = ("\n".join(lines[1:]) + "\n").encode("utf-8")
    assert inventory_integrity_errors(good, regen) == []
    assert inventory_integrity_errors(tampered, regen) != []
    assert inventory_integrity_errors(dropped, regen) != []
    assert inventory_integrity_errors(b"not a nodeid\n", regen) != []
    disp = {"population": {"files": []}, "operations": [], "new_files": []}
    assert check_7(disp, {GENERATED_INVENTORY_REL}, lambda p: inventory_integrity_errors(good, regen)) == []
    assert check_7(disp, {GENERATED_INVENTORY_REL}, lambda p: inventory_integrity_errors(tampered, regen)) != []
    assert check_7(disp, {GENERATED_INVENTORY_REL}, None) != []


def test_mutation_d11_7_empty_sentinel_not_unconditional():
    """審查 r63 CODEX-R63-P1-01：非空清冊（HEAD 版）被換成空集合標記 ⇒ 以 HEAD 版所列檔重產非空 ⇒ 紅；HEAD 版亦為
    空標記或不存在 ⇒ 不紅；HEAD 版所列檔重產確為空 ⇒ 不紅。mutation：空標記無條件放行 ⇒ 第一案綠（紅）。"""
    head = b"tests/x/test_a.py::test_one\ntests/x/test_a.py::test_two\n"
    nonempty = {("tests/x/test_a.py",): head}
    assert inventory_integrity_errors(INVENTORY_EMPTY, lambda fs: nonempty[tuple(fs)], head_content=head) != []
    assert inventory_integrity_errors(INVENTORY_EMPTY, lambda fs: INVENTORY_EMPTY, head_content=head) == []
    assert inventory_integrity_errors(INVENTORY_EMPTY, lambda fs: head, head_content=INVENTORY_EMPTY) == []
    assert inventory_integrity_errors(INVENTORY_EMPTY, lambda fs: head, head_content=None) == []


def test_mutation_affected_gate_runner_resume_pause_progress(tmp_path):
    """實作期 b1（使用者 2026-10-10：不得被時間上限砍掉重來、卡住須可知）：同狀態指紋之結果檔沿用（不呼叫 pytest）；
    無可沿用結果且本段已逾預算 ⇒ Paused（停在呼叫之間）；progress.json 記狀態、已完成數與 pid。mutation：沿用條件或
    預算檢查撤回 ⇒ 紅。"""
    g = _affected_gate()
    out = tmp_path / "out"
    xml = out / "junit" / "t.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text('<testsuites><testcase classname="tests.test_cgsa_pipeline" name="test_x"/></testsuites>',
                   encoding="utf-8")
    xml.with_suffix(".meta.json").write_text(json.dumps({"state_key": "K", "rc": 0}), encoding="utf-8")
    r = g.Runner(out, 0.0, 2)
    rc, res = r.run("tests/test_cgsa_pipeline.py", xml, REPO, os.environ, None, (), "K",
                    ["tests/test_cgsa_pipeline.py::test_x"])
    assert rc == 0 and "tests/test_cgsa_pipeline.py::test_x" in res and r.done == 1
    with pytest.raises(g.Paused):
        r.run("tests/test_cgsa_pipeline.py", xml, REPO, os.environ, None, (), "OTHER",
              ["tests/test_cgsa_pipeline.py::test_x"])
    r.progress("paused", "", [], state="paused")
    prog = json.loads((out / "progress.json").read_text(encoding="utf-8"))
    assert prog["state"] == "paused" and prog["done"] == 1 and prog["total"] == 2 and prog["pid"] == os.getpid()
    # 審查 r57：meta 或結果檔損毀（中斷於寫入中）⇒ 視為未命中（此處逾預算故 Paused），不得 JSONDecodeError
    xml.with_suffix(".meta.json").write_text('{"state_key": "K", "rc"', encoding="utf-8")
    with pytest.raises(g.Paused):
        r.run("tests/test_cgsa_pipeline.py", xml, REPO, os.environ, None, (), "K",
              ["tests/test_cgsa_pipeline.py::test_x"])
    xml.with_suffix(".meta.json").write_text(json.dumps({"state_key": "K", "rc": 0}), encoding="utf-8")
    xml.write_text("<testsuites><testcase", encoding="utf-8")
    with pytest.raises(g.Paused):
        r.run("tests/test_cgsa_pipeline.py", xml, REPO, os.environ, None, (), "K",
              ["tests/test_cgsa_pipeline.py::test_x"])
    # 審查 r57：已追蹤之 handoffs 改動不影響 inputs_digest（未追蹤者亦然）；其他已追蹤檔改動則影響
    repo, anchor = _git_tmp_repo(tmp_path / "d", {"handoffs/a.md": "x\n", "src.py": "a = 1\n"})
    base = g.plan_inputs_digest(repo, anchor, 1, (), {"PATH": "/bin"})
    (repo / "handoffs" / "a.md").write_text("y\n", encoding="utf-8")
    (repo / "handoffs" / "new.md").write_text("z\n", encoding="utf-8")
    assert g.plan_inputs_digest(repo, anchor, 1, (), {"PATH": "/bin"}) == base
    (repo / "src.py").write_text("a = 2\n", encoding="utf-8")
    assert g.plan_inputs_digest(repo, anchor, 1, (), {"PATH": "/bin"}) != base
    # 審查 r58：只改排除路徑之提交（交接）與生成之已追蹤清冊不改 state_key／digest；輸入檔之提交則改；清冊可還原
    repo2, anchor2 = _git_tmp_repo(tmp_path / "e", {"handoffs/a.md": "x\n", "src.py": "a = 1\n",
                                                    "tests/golden/l65/test_inventory.txt": "inv\n"})

    def fps():
        return (g.state_key(repo2, "src.py", 1, {"PATH": "/bin"}),
                g.plan_inputs_digest(repo2, anchor2, 1, (), {"PATH": "/bin"}))

    def commit(rel, text):
        (repo2 / rel).write_text(text, encoding="utf-8")
        subprocess.run(["git", "-C", str(repo2), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "c"],
                       check=True, capture_output=True)

    before = fps()
    commit("handoffs/a.md", "y\n")
    (repo2 / "tests/golden/l65/test_inventory.txt").write_text("regenerated\n", encoding="utf-8")
    assert fps() == before
    g.restore_generated(repo2)
    assert (repo2 / "tests/golden/l65/test_inventory.txt").read_text(encoding="utf-8") == "inv\n"
    commit("src.py", "a = 3\n")
    assert fps()[0] != before[0] and fps()[1] != before[1]
    # 審查 r60：未追蹤檔與被忽略之資料輸入，同路徑內容改變即改 state_key／digest
    (repo2 / ".gitignore").write_text("data_cache/\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo2), "-c", "user.email=t@t", "-c", "user.name=t", "add", ".gitignore"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo2), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "gi"],
                   check=True, capture_output=True)
    (repo2 / "fixture.json").write_text("1", encoding="utf-8")
    kl = repo2 / "data_cache/feature_klines/kline_cache.h5"
    kl.parent.mkdir(parents=True)
    kl.write_bytes(b"A")
    s1 = fps()
    (repo2 / "fixture.json").write_text("2", encoding="utf-8")
    s2 = fps()
    kl.write_bytes(b"B")
    s3 = fps()
    assert s1[0] != s2[0] != s3[0] and s1[1] != s2[1] != s3[1]
    # 審查 r61：同大小換內容且回撥 mtime（metadata 全同）⇒ 仍改兩指紋（不以 metadata 快取）
    st = kl.stat()
    kl.write_bytes(b"C")
    os.utime(kl, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert fps() != s3


def test_affected_gate_def_probe_records_calls(tmp_path):
    """殘差定義執行探針：環境變數已設之行程內包裝模組函式、類別方法、staticmethod，呼叫後結束寫 `<pid>.json`；回傳值
    不變。未呼叫者不記。以子行程實跑。"""
    mod = tmp_path / "probe_mod.py"
    mod.write_text("def f(x):\n    return x + 1\n\nclass C:\n    def m(self):\n        return 2\n\n"
                   "    @staticmethod\n    def s():\n        return 3\n\n    def unused(self):\n        return 4\n",
                   encoding="utf-8")
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('g', {str(REPO / 'scripts/framepath_affected_gate.py')!r})\n"
        "g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)\n"
        "g.install_def_probe(); g.install_def_probe()\n"
        "import probe_mod\n"
        "assert probe_mod.f(1) == 2 and probe_mod.C().m() == 2 and probe_mod.C.s() == 3 and probe_mod.C().s() == 3\n",
        encoding="utf-8")
    out = tmp_path / "probe"
    env = dict(os.environ, PYTHONPATH=f"{tmp_path}{os.pathsep}{REPO}", FRAMEPATH_DEF_PROBE_DIR=str(out),
               FRAMEPATH_DEF_PROBE_DEFS="probe_mod:f,probe_mod:C.m,probe_mod:C.s,probe_mod:C.unused")
    proc = subprocess.run([sys.executable, str(driver)], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    hits = _affected_gate().probe_hits(out)
    assert hits == {"probe_mod:f", "probe_mod:C.m", "probe_mod:C.s"}


def test_mutation_affected_gate_admission_and_residual_verdict(tmp_path):
    """admission：全部已知且 ≤ 預算＝within、有未知＝unknown、已知逾預算＝over；junit 時間依 repo 內 .py 還原 nodeid。
    verdict：CGSA 殘差定義未被 A 組執行 ⇒ 不通過。mutation：verdict 忽略殘差未執行 ⇒ 紅。"""
    g = _affected_gate()
    assert g.admission(["a", "b"], {"a": 1.0, "b": 2.0}, 10)["status"] == "within"
    assert g.admission(["a", "b"], {"a": 1.0}, 10) == {"budget_seconds": 10, "known_seconds": 1.0, "unknown": ["b"],
                                                      "status": "unknown"}
    assert g.admission(["a", "b"], {"a": 11.0}, 10)["status"] == "over"
    xml = ('<testsuites><testsuite><testcase classname="tests.test_cgsa_pipeline" name="test_x" time="1.5"/>'
           '<testcase classname="tests.feature_engineering.test_framepath_disposition.K" name="t[1]" time="2"/>'
           '</testsuite></testsuites>')
    assert g.junit_times(xml, REPO) == {"tests/test_cgsa_pipeline.py::test_x": 1.5,
                                        "tests/feature_engineering/test_framepath_disposition.py::K::t[1]": 2.0}
    ok = {"missing": [], "unexpected": [], "caused": []}
    assert g.verdict(ok, [], []) and g.verdict(ok, [], [], [])
    assert not g.verdict(ok, [], [], ["momentum.m:K._meth"])


def test_git_path_output_not_escaped():
    """審查 r46（GROK-R46-P1-02、CODEX-R46-P1-03）：驗證器之 git 路徑輸出（ls-files、diff、log --name-only）對非 ASCII
    路徑原樣輸出，不得出現 git 引號／八進位逸出形態；處置表母體不得含逸出形態。mutation：拿掉 core.quotepath=off ⇒ 紅。"""
    listed = _git("ls-files", "--", NON_ASCII_TRACKED).decode("utf-8").splitlines()
    assert listed == [NON_ASCII_TRACKED]
    names = _git("log", "--format=", "--name-only", "-1", "--", NON_ASCII_TRACKED).decode("utf-8").splitlines()
    assert NON_ASCII_TRACKED in names
    escaped = subprocess.run(["git", "-c", "core.quotepath=on", "ls-files", "--", NON_ASCII_TRACKED], cwd=REPO,
                             capture_output=True).stdout.decode("utf-8").strip()
    assert escaped != NON_ASCII_TRACKED and escaped.startswith('"')  # 證 mutation 有效：預設會逸出
    disp = json.loads((REPO / DISPOSITION_REL).read_text(encoding="utf-8"))
    paths = list(disp["population"]["files"]) + [op["path"] for op in disp["operations"]]
    assert not [p for p in paths if p.startswith('"') or re.search(r"\\[0-7]{3}", p)]


# FRAMEPATH 收案後退役（TESTREG SPEC v53 Task 4.4 子批①）：⑤⑥⑦ 對真實 repo 工作樹與錨點以來改動之檢查——
# test_check_5_new_and_ignored_files、test_check_6_fact_keys_rows、test_check_7_changed_paths_in_scope
# （工作樹任一未提交改動即判為本票越界，收案後會擋所有他票之進行中工作）。判定函式與 mutation 測試保留。


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
