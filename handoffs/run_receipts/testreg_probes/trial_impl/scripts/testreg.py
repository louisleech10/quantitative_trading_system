#!/usr/bin/env python3
"""testreg.py — TESTREG 測試清冊：契約驗證、bootstrap、標記、產出端檢查、複查訊號、受影響測試挑選、成效報告。

規格：docs/TESTREG_SPEC.md；契約單一真相源：tests/registry/testreg_schema.json（格式、枚舉、規則 V01–V22、挑選規則、
閘收據欄皆只讀該檔；本檔不存任何枚舉值副本——Task 1.1 驗收以字面計數機檢）。

TODO 凍結之介面（docs/manifests/TESTREG.json）：本檔目前只含簽章，函式體一律 `raise NotImplementedError("<Task>")`，
由各批實作。簽章、具名縫（供 tests/registry/ 之 mutation 置換者）與 CLI 契約不得於實作期更改；需改者回 TODO 重審。

用法（`--repo` 預設＝本檔所在 repo 根；路徑一律 repo 相對 POSIX）：
  testreg.py [--repo R] validate [--require-executed]
  testreg.py [--repo R] bootstrap [--receipt P]
  testreg.py [--repo R] markers
  testreg.py [--repo R] check (--paths P [P ...] | --manifest M | --helpers H [H ...] | --staged)
  testreg.py [--repo R] review
  testreg.py [--repo R] impact --changed-from <git-range|worktree> --manifest M --phase N
  testreg.py [--repo R] effect (--out P [--scope PREFIX ...] | --recompute P)
  testreg.py [--repo R] run --manifest M --phase N --base <rev> --receipt P [--out D] [--max-seconds S]

結束碼：0＝通過；非 0＝不通過或無法判定。不通過之每一項於 stderr 單列輸出，列首為規則 id（`V01`…`V22`）或
`MARKER`／`CATALOG`／`SCHEMA`／`MANIFEST`／`EFFECT`，格式 `<ID> <主體>: <訊息>`；ledger 不在本機而無法驗證者訊息含
`unverifiable`。review／impact 之結果以 JSON 寫 stdout。

具名縫（呼叫端一律於呼叫當下以模組屬性取用，使 `monkeypatch.setattr(testreg, <名>, …)` 生效）：
  - 規則：`rule_v01`…`rule_v22`；`rule_v07` 由 `rule_v07_receipt_valid` 與 `rule_v07_change_requires_receipt` 組成。
  - 斷言多重集合比較：`multiset_decreased`；暫存區變更清單：`staged_changes`；形狀驗證（V17 共用實作）：`validate_shape`。
  - bootstrap 之票代號：`ticket_of`；產出端呼叫者反推：`helper_callers`。
  - 複查訊號：`signal_<名>`，名＝schema `enums.review_signal` 之各值。
  - 挑選：`combine_sources`、`domain_prefix`、`import_closure`、`shared_infra_scope`。
"""
from __future__ import annotations

import argparse
import collections
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import argparse
import collections
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

REPO = Path(__file__).resolve().parents[1]
SCHEMA_REL = "tests/registry/testreg_schema.json"
CATALOG_REL = "tests/registry/catalog.json"
RULE_IDS: Tuple[str, ...] = tuple(f"V{i:02d}" for i in range(1, 23))

SignalValue = Union[bool, str]  # True／False／字面 "unknown"

import ast
import functools

_parse = functools.lru_cache(maxsize=512)(ast.parse)  # 唯讀用途之解析快取（呼叫端不得改寫回傳之樹）
import copy
import datetime as _dt
import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import subprocess
import tempfile


def _globals() -> Dict[str, Any]:
    return globals()


def _seam(name: str):
    """具名縫：於呼叫當下以模組屬性取用（monkeypatch 生效）。"""
    return _globals()[name]


def _run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(root), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise TestregError(f"git {' '.join(args[:3])} rc={proc.returncode}: {proc.stderr.strip()[:200]}")
    return proc


def _git_out(root: Path, *args: str) -> str:
    return _run_git(root, *args).stdout


_HEAD_CACHE: Dict[str, Optional[str]] = {}


def _head_sha(root: Path) -> Optional[str]:
    key = str(Path(root).resolve())
    if key not in _HEAD_CACHE:  # 單一行程內 HEAD 不變（hook／pre-commit 皆短命行程）
        proc = _run_git(root, "rev-parse", "--verify", "-q", "HEAD", check=False)
        _HEAD_CACHE[key] = proc.stdout.strip() or None if proc.returncode == 0 else None
    return _HEAD_CACHE[key]


def _is_ancestor(root: Path, a: str, b: str) -> bool:
    return _run_git(root, "merge-base", "--is-ancestor", a, b, check=False).returncode == 0


class _Tree:
    """受驗之樹：HEAD／staged（index）／worktree，或 rev:<sha>。"""

    def __init__(self, root: Path, kind: str):
        self.root, self.kind = Path(root), kind
        self._files: Optional[List[str]] = None
        self._cache: Dict[str, Optional[str]] = {}

    def _rev(self) -> Optional[str]:
        if self.kind == "HEAD":
            return "HEAD" if _head_sha(self.root) else None
        if self.kind.startswith("rev:"):
            return self.kind[4:]
        return None

    def read(self, rel: str) -> Optional[str]:
        if rel in self._cache:
            return self._cache[rel]
        text: Optional[str] = None
        if self.kind == "worktree":
            p = self.root / rel
            text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None
        elif self.kind == "staged":
            proc = _run_git(self.root, "show", f":{rel}", check=False)
            text = proc.stdout if proc.returncode == 0 else None
        else:
            rev = self._rev()
            if rev:
                proc = _run_git(self.root, "show", f"{rev}:{rel}", check=False)
                text = proc.stdout if proc.returncode == 0 else None
        self._cache[rel] = text
        return text

    def prefetch(self, rels: Sequence[str]) -> None:
        """非工作樹之樹：以單一 `git cat-file --batch` 批次讀入快取（避免逐檔 git show）。"""
        todo = [r for r in rels if r not in self._cache]
        if not todo or self.kind == "worktree":
            return
        pre = ":" if self.kind == "staged" else f"{self._rev()}:"
        proc = subprocess.run(["git", "-C", str(self.root), "cat-file", "--batch"],
                              input="".join(pre + r + "\n" for r in todo).encode(), capture_output=True)
        out, pos = proc.stdout, 0
        for r in todo:
            nl = out.index(b"\n", pos)
            header = out[pos:nl].decode()
            pos = nl + 1
            if header.endswith(" missing"):
                self._cache[r] = None
                continue
            size = int(header.split()[2])
            self._cache[r] = out[pos:pos + size].decode("utf-8", "replace")
            pos += size + 1

    def files(self) -> List[str]:
        if self._files is None:
            if self.kind == "worktree":
                out = _git_out(self.root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
                self._files = sorted({p for p in out.split("\0") if p and (self.root / p).is_file()})
            elif self.kind == "staged":
                out = _git_out(self.root, "ls-files", "-z", "--cached")
                self._files = sorted({p for p in out.split("\0") if p})
            else:
                rev = self._rev()
                out = _git_out(self.root, "ls-tree", "-r", "-z", "--name-only", rev) if rev else ""
                self._files = sorted({p for p in out.split("\0") if p})
        return self._files

    def exists(self, rel: str) -> bool:
        if self.kind == "worktree":
            return (self.root / rel).is_file()
        if getattr(self, "_fileset", None) is None:
            self._fileset = set(self.files())
        return rel in self._fileset

    def test_files(self, schema: Mapping[str, Any]) -> List[str]:
        pat = schema["formats"]["test_path"]
        return [f for f in self.files() if re.fullmatch(pat, f)]


def _split_nodeid(nodeid: str) -> Tuple[str, str]:
    path, _, rest = nodeid.partition("::")
    return path, re.sub(r"\[.*\]$", "", rest)


def _name_ok(name: str, pats: Sequence[str]) -> bool:
    import fnmatch
    return any(fnmatch.fnmatchcase(name, p) if any(c in p for c in "*?[") else name.startswith(p) for p in pats)


def _test_functions(src: Optional[str], fpats: Sequence[str] = ("test_*",),
                    cpats: Sequence[str] = ("Test*",)) -> Dict[str, ast.AST]:
    """{qualname（`f` 或 `Cls::f`）: FunctionDef}；依 pytest.ini 之 python_functions／python_classes。"""
    out: Dict[str, ast.AST] = {}
    if src is None:
        return out
    try:
        mod = _parse(src)
    except SyntaxError:
        return out
    for n in mod.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and _name_ok(n.name, fpats):
            out[n.name] = n
        elif isinstance(n, ast.ClassDef) and _name_ok(n.name, cpats):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and _name_ok(m.name, fpats):
                    out[f"{n.name}::{m.name}"] = m
    return out


def _collect_patterns(tree: "_Tree") -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    import configparser
    cp = configparser.ConfigParser()
    try:
        cp.read_string(tree.read("pytest.ini") or "")
        sec = cp["pytest"] if cp.has_section("pytest") else {}
    except configparser.Error:
        sec = {}
    return (tuple(sec.get("python_functions", "test").split()), tuple(sec.get("python_classes", "Test").split()),
            tuple(sec.get("python_files", "test_*.py *_test.py").split()), tuple(sec.get("testpaths", "").split()))


def _plugin_paths(tree: "_Tree", conftest: str) -> List[str]:
    """conftest 之 `pytest_plugins` 字面所列模組之 repo 路徑（存在者）。"""
    if not tree.exists(conftest):
        return []
    try:
        mod = ast.parse(tree.read(conftest) or "")
    except SyntaxError:
        return []
    names: List[str] = []
    for n in mod.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in n.targets):
            v = n.value
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                names.append(v.value)
            elif isinstance(v, (ast.List, ast.Tuple)):
                names += [e.value for e in v.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    out = []
    for nm in names:
        for p in (nm.replace(".", "/") + ".py", nm.replace(".", "/") + "/__init__.py"):
            if tree.exists(p):
                out.append(p)
                break
    return out


def _function_nodeids(tree: _Tree, path: str) -> List[str]:
    fp, cp_, files_, tps = _collect_patterns(tree)
    if tps and not any(path == tp or path.startswith(tp.rstrip("/") + "/") for tp in tps):
        return []
    if not _name_ok(path.rsplit("/", 1)[-1], files_):
        return []
    return sorted(f"{path}::{q}" for q in _test_functions(tree.read(path), fp, cp_))


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "surrogateescape")).hexdigest()


def _sha256_file(p: Path) -> Optional[str]:
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _today() -> str:
    return _dt.date.today().isoformat()


def _plugin_module():
    """記錄器模組（diff_digest 單一實作）：以檔案路徑載入。"""
    key = "_testreg_recorder_for_validate"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, REPO / "tests/fixtures/testreg_recorder_plugin.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


_SPECIAL = frozenset({"raises", "warns", "deprecated_call", "fail", "approx", "xfail", "skip"})
_CHECK_RE = re.compile(r"^(check|verify|validate|expect)_")
_PLACE = "\x00L"


def _last_name(func: ast.AST) -> Optional[str]:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_const_node(n: ast.AST) -> bool:
    if isinstance(n, ast.Constant):
        return True
    if isinstance(n, (ast.Tuple, ast.List)):
        return all(_is_const_node(e) for e in n.elts)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)) and isinstance(n.operand, ast.Constant):
        return True
    return False


def _fixture_info(fn: ast.AST) -> Tuple[bool, bool]:
    for d in getattr(fn, "decorator_list", []):
        target = d.func if isinstance(d, ast.Call) else d
        if _last_name(target) == "fixture":
            autouse = isinstance(d, ast.Call) and any(
                k.arg == "autouse" and isinstance(k.value, ast.Constant) and k.value.value is True for k in d.keywords)
            return True, autouse
    return False, False


def _bound_names(fn: ast.AST) -> Dict[str, Tuple[int, int]]:
    """函式內綁定之名 → 首次綁定位置（參數、Store、for／with／except as、comprehension、函式內 import）。"""
    pos: Dict[str, Tuple[int, int]] = {}

    def note(name: str, node: ast.AST) -> None:
        p = (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
        if name not in pos or p < pos[name]:
            pos[name] = p

    a = fn.args
    for arg in [*getattr(a, "posonlyargs", []), *a.args, *a.kwonlyargs, *(x for x in (a.vararg, a.kwarg) if x)]:
        note(arg.arg, arg)
    for n in ast.walk(fn):
        if n is fn:
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            note(n.id, n)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            note(n.name, n)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names:
                note((al.asname or al.name).split(".")[0], n)
    return pos


def _assign_counts(body: Sequence[ast.stmt], deep: bool) -> Tuple[Dict[str, int], Dict[str, ast.AST]]:
    counts: Dict[str, int] = collections.Counter()
    rhs: Dict[str, ast.AST] = {}
    nodes = ast.walk(ast.Module(body=list(body), type_ignores=[])) if deep else iter(body)
    for n in nodes:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                for nm in ast.walk(t):
                    if isinstance(nm, ast.Name) and isinstance(nm.ctx, ast.Store):
                        counts[nm.id] += 1
                        rhs[nm.id] = n.value if isinstance(t, ast.Name) else ast.Name(id="__nonconst__")
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and isinstance(n.target, ast.Name):
            counts[n.target.id] += 2 if isinstance(n, ast.AugAssign) else 1
            rhs[n.target.id] = n.value if isinstance(n, ast.AnnAssign) and n.value is not None else ast.Name(id="__nc__")
        elif isinstance(n, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.comprehension)):
            for nm in ast.walk(n.target if hasattr(n, "target") else n):
                if isinstance(nm, ast.Name) and isinstance(nm.ctx, ast.Store):
                    counts[nm.id] += 2
    return counts, rhs


class _Mod:
    def __init__(self, path: str, src: str):
        self.path = path
        self.tree = ast.parse(src)
        self.defs: Dict[str, ast.AST] = {}
        self.classes: Dict[str, ast.ClassDef] = {}
        self.fixtures: Dict[str, Tuple[ast.AST, bool]] = {}
        self.imports: Dict[str, Tuple[str, str, Optional[str]]] = {}
        self.assigns: Dict[str, List[ast.stmt]] = collections.defaultdict(list)
        for n in self.tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                isfx, auto = _fixture_info(n)
                if isfx:
                    self.fixtures[n.name] = (n, auto)
                self.defs[n.name] = n
            elif isinstance(n, ast.ClassDef):
                self.classes[n.name] = n
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                _note_imports(n, self.imports)
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    for nm in ast.walk(t):
                        if isinstance(nm, ast.Name):
                            self.assigns[nm.id].append(n)
        counts, rhs = _assign_counts(self.tree.body, deep=False)
        self.consts = {k: v for k, v in rhs.items() if counts.get(k) == 1 and _is_const_node(v)}


def _note_imports(n: ast.AST, out: Dict[str, Tuple[str, str, Optional[str]]]) -> None:
    if isinstance(n, ast.Import):
        for al in n.names:
            if al.asname:
                out[al.asname] = ("module", al.name, None)
            else:
                out[al.name.split(".")[0]] = ("module", al.name.split(".")[0], None)
    elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
        for al in n.names:
            out[al.asname or al.name] = ("from", n.module, al.name)


class _Engine:
    """一棵樹上之斷言多重集合計算（schema assertion_nodes 之 kinds／assertion_helpers／helper_precedence／
    inline_rule／normalize）。元素＝(dump 字串, provenance (path, lineno, end_lineno), owner (path, lineno, end_lineno, kind))。"""

    def __init__(self, tree: "_Tree"):
        self.tree = tree
        self._mods: Dict[str, Optional[_Mod]] = {}
        self._helper: Dict[Tuple[str, str], bool] = {}
        self._own: Dict[Tuple[str, str], str] = {}
        self._inst = 0
        self.touched: set = set()

    # 模組與解析
    def mod(self, path: str) -> Optional[_Mod]:
        if path not in self._mods:
            src = self.tree.read(path)
            try:
                self._mods[path] = _Mod(path, src) if src is not None else None
            except SyntaxError:
                self._mods[path] = None
        return self._mods[path]

    def module_path(self, dotted: str) -> Optional[str]:
        base = dotted.replace(".", "/")
        for cand in (base + ".py", base + "/__init__.py"):
            if self.tree.exists(cand):
                return cand
        return None

    def binding_module(self, mi: _Mod, name: str, local_imports: Mapping[str, Tuple[str, str, Optional[str]]]
                       ) -> Optional[str]:
        """名稱 → 其綁定之模組檔（`import a.b as X`、`import X`、`from a import X` 而 X 為模組）。"""
        b = local_imports.get(name) or mi.imports.get(name)
        if not b:
            return None
        kind, mod, attr = b
        if kind == "module":
            return self.module_path(mod)
        return self.module_path(f"{mod}.{attr}")

    def resolve_name(self, mi: _Mod, name: str, local_imports, depth: int = 0) -> Optional[Tuple[str, str]]:
        """名稱 → (定義檔, 名稱)：本模組定義或 from-import（遞移 re-export）。"""
        if depth > 8:
            return None
        if name in local_imports or name in mi.imports:
            kind, mod, attr = local_imports.get(name) or mi.imports[name]
            if kind != "from":
                return None
            p = self.module_path(mod)
            m2 = self.mod(p) if p else None
            if m2 is None:
                return None
            if attr in m2.defs or attr in m2.consts or attr in m2.classes:
                return (p, attr)
            return self.resolve_name(m2, attr, {}, depth + 1)
        if name in mi.defs or name in mi.consts or name in mi.classes:
            return (mi.path, name)
        return None

    def resolve_callee(self, mi: _Mod, func: ast.AST, local_imports) -> Optional[Tuple[str, ast.AST]]:
        if isinstance(func, ast.Name):
            r = self.resolve_name(mi, func.id, local_imports)
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            p = self.binding_module(mi, func.value.id, local_imports)
            r = (p, func.attr) if p else None
        else:
            r = None
        if not r or not r[0].startswith("tests/"):
            return None
        m2 = self.mod(r[0])
        fn = m2.defs.get(r[1]) if m2 else None
        if fn is None or _fixture_info(fn)[0]:
            return None
        return (r[0], fn)

    def const_of(self, mi: _Mod, node: ast.AST, local_consts, local_imports) -> Optional[ast.AST]:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in local_consts:
                return local_consts[node.id]
            if node.id in local_imports or node.id in mi.imports:
                r = self.resolve_name(mi, node.id, local_imports)
                if r and r[0].startswith("tests/"):
                    m2 = self.mod(r[0])
                    if m2 and r[1] in m2.consts:
                        self.touched.add(r[0])
                        return m2.consts[r[1]]
                return None
            if node.id in mi.consts:
                return mi.consts[node.id]
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and isinstance(node.ctx, ast.Load):
            p = self.binding_module(mi, node.value.id, local_imports)
            if p and p.startswith("tests/"):
                m2 = self.mod(p)
                if m2 and node.attr in m2.consts:
                    self.touched.add(p)
                    return m2.consts[node.attr]
        return None

    def fold(self, mi: _Mod, node: ast.AST, local_consts, local_imports) -> ast.AST:
        eng = self

        class F(ast.NodeTransformer):
            def visit_Name(self, n):
                c = eng.const_of(mi, n, local_consts, local_imports)
                return copy.deepcopy(c) if c is not None else n

            def visit_Attribute(self, n):
                c = eng.const_of(mi, n, local_consts, local_imports)
                if c is not None:
                    return copy.deepcopy(c)
                self.generic_visit(n)
                return n

        return F().visit(copy.deepcopy(node))

    def scope(self, mi: _Mod, fn: ast.AST) -> Tuple[Dict[str, ast.AST], Dict[str, Tuple[str, str, Optional[str]]]]:
        params = {a.arg for a in [*getattr(fn.args, "posonlyargs", []), *fn.args.args, *fn.args.kwonlyargs]}
        counts, rhs = _assign_counts(fn.body, deep=True)
        consts = {k: v for k, v in rhs.items() if counts.get(k) == 1 and k not in params and _is_const_node(v)}
        imports: Dict[str, Tuple[str, str, Optional[str]]] = {}
        for n in ast.walk(fn):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                _note_imports(n, imports)
        return consts, imports

    # helper 判定
    def is_helper(self, path: str, fn: ast.AST, stack: frozenset = frozenset()) -> bool:
        key = (path, fn.name)
        if key in self._helper:
            return self._helper[key]
        if key in stack:
            return False
        mi = self.mod(path)
        _, imps = self.scope(mi, fn)
        found = False
        for n in ast.walk(fn):
            if isinstance(n, ast.Assert):
                found = True
            elif isinstance(n, ast.Call):
                nm = _last_name(n.func)
                if nm and (nm.startswith("assert") or nm in _SPECIAL):
                    found = True
                else:
                    tgt = self.resolve_callee(mi, n.func, imps)
                    if tgt and self.is_helper(tgt[0], tgt[1], stack | {key}):
                        found = True
                    elif nm and _CHECK_RE.match(nm):
                        found = True
            if found:
                break
        self._helper[key] = found
        return found

    # 收集
    def collect(self, mi: _Mod, fn: ast.AST, kind: str, stack: frozenset) -> List[Dict[str, Any]]:
        """fn 本體之斷言元素（已於 fn 之範圍做常數摺疊；helper 已展開並代入；名稱未序號化）。"""
        consts, imps = self.scope(mi, fn)
        owner = (mi.path, fn.lineno, fn.end_lineno, kind)
        out: List[Dict[str, Any]] = []

        def element(node: ast.AST, lo: int, hi: int) -> None:
            out.append({"node": self.fold(mi, node, consts, imps), "prov": (mi.path, lo, hi), "owner": owner})

        def visit(node: ast.AST) -> None:
            if isinstance(node, ast.Assert):
                element(node, node.lineno, node.end_lineno)
                return
            if isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    c = item.context_expr
                    if isinstance(c, ast.Call) and _last_name(c.func) in _SPECIAL:
                        element(c, node.lineno, node.end_lineno)
                    else:
                        visit(c)
                for st in node.body:
                    visit(st)
                return
            if isinstance(node, ast.Call):
                tgt = self.resolve_callee(mi, node.func, imps)
                if tgt and self.is_helper(tgt[0], tgt[1]):
                    self.touched.add(tgt[0])
                    out.extend(self.expand(mi, node, tgt, consts, imps, stack))
                    return
                nm = _last_name(node.func)
                if nm and (nm.startswith("assert") or nm in _SPECIAL or _CHECK_RE.match(nm)):
                    element(node, node.lineno, node.end_lineno)
                    return
            for ch in ast.iter_child_nodes(node):
                visit(ch)

        for st in fn.body:
            visit(st)
        return out

    def expand(self, mi: _Mod, call: ast.Call, tgt: Tuple[str, ast.AST], consts, imps, stack: frozenset
               ) -> List[Dict[str, Any]]:
        hpath, hfn = tgt
        key = (hpath, hfn.name)
        if key in stack:
            return []
        hmi = self.mod(hpath)
        a = hfn.args
        starred = any(isinstance(x, ast.Starred) for x in call.args) or any(k.arg is None for k in call.keywords)
        if a.vararg or a.kwarg or starred:
            args = [ast.dump(self.fold(mi, x, consts, imps)) for x in call.args]
            kws = sorted((k.arg or "**", ast.dump(self.fold(mi, k.value, consts, imps))) for k in call.keywords)
            el = {"node": None, "opaque": json.dumps(["opaque", f"{hpath}::{hfn.name}", args, kws, self.own_sha(hpath, hfn)],
                                                       ensure_ascii=False),
                  "prov": (mi.path, call.lineno, call.end_lineno), "owner": None}
            return [el]
        params = [*getattr(a, "posonlyargs", []), *a.args]
        hconsts, himps = self.scope(hmi, hfn)
        binding: Dict[str, ast.AST] = {}
        defaults = list(a.defaults)
        for i, p in enumerate(params):
            di = i - (len(params) - len(defaults))
            if i < len(call.args):
                binding[p.arg] = self.fold(mi, call.args[i], consts, imps)
            elif di >= 0:
                binding[p.arg] = self.fold(hmi, defaults[di], hconsts, himps)
        for p, d in zip(a.kwonlyargs, a.kw_defaults):
            if d is not None:
                binding[p.arg] = self.fold(hmi, d, hconsts, himps)
        for k in call.keywords:
            binding[k.arg] = self.fold(mi, k.value, consts, imps)
        inner = self.collect(hmi, hfn, "helper", stack | {key})
        self._inst += 1
        inst = self._inst
        local = {n for n in _bound_names(hfn) if n not in binding}
        order = {n: i for i, n in enumerate(sorted(local, key=lambda n: _bound_names(hfn)[n]))}
        pos = (call.lineno, call.col_offset)

        class Sub(ast.NodeTransformer):
            def visit_Name(self, n):
                if n.id in binding and isinstance(n.ctx, ast.Load):
                    return copy.deepcopy(binding[n.id])
                if n.id in local:
                    return ast.copy_location(ast.Name(id=f"{_PLACE}{inst}|{pos[0]:08d}|{pos[1]:04d}|{order[n.id]:04d}|{n.id}",
                                                      ctx=n.ctx), n)
                return n

        for el in inner:
            if el.get("node") is not None and not el.get("subst_done_for", set()) & {inst}:
                el["node"] = Sub().visit(el["node"])
        return inner

    def own_sha(self, path: str, fn: ast.AST) -> str:
        key = (path, fn.name)
        if key not in self._own:
            self._own[key] = "pending"
            els = self.normalize(fn, self.collect(self.mod(path), fn, "helper", frozenset({key})))
            self._own[key] = _sha256_text(json.dumps(sorted(collections.Counter(e["key"] for e in els).items()),
                                                     ensure_ascii=False))
        return self._own[key]

    def fixture_defs(self, test_path: str) -> Dict[str, Tuple[str, ast.AST, bool]]:
        """test_path 可見之 fixture：同模組優先，其次由近而遠之 conftest.py（含 repo 根）。"""
        out: Dict[str, Tuple[str, ast.AST, bool]] = {}
        parts = test_path.split("/")[:-1]
        chain = [test_path] + ["/".join(parts[:i] + ["conftest.py"]) for i in range(len(parts), -1, -1)]
        chain += [pl for c in chain[1:] for pl in _plugin_paths(self.tree, c)]
        for p in chain:
            m = self.mod(p) if self.tree.exists(p) else None
            if m is None:
                continue
            for name, (fn, auto) in m.fixtures.items():
                out.setdefault(name, (p, fn, auto))
        return out

    def elements(self, nodeid: str) -> List[Dict[str, Any]]:
        """某測試函式之完整斷言元素（含 fixture 與 autouse 之 inline、helper 展開、normalize）。"""
        path, qual = _split_nodeid(nodeid)
        mi = self.mod(path)
        if mi is None:
            return []
        fn = _test_functions(self.tree.read(path)).get(qual)
        if fn is None:
            return []
        els = self.collect(mi, fn, "test", frozenset())
        fx = self.fixture_defs(path)
        params = [x.arg for x in [*getattr(fn.args, "posonlyargs", []), *fn.args.args, *fn.args.kwonlyargs]]
        queue = [(p, (fn.lineno, i)) for i, p in enumerate(params) if p in fx]
        queue += [(n, (fn.lineno, -1)) for n, (_, _, auto) in sorted(fx.items()) if auto]
        seen: set = set()
        while queue:
            name, pos = queue.pop(0)
            if name in seen or name not in fx:
                continue
            seen.add(name)
            fpath, ffn, _ = fx[name]
            self.touched.add(fpath)
            fmi = self.mod(fpath)
            inner = self.collect(fmi, ffn, "fixture", frozenset())
            self._inst += 1
            inst = self._inst
            local = set(_bound_names(ffn))
            order = {n: i for i, n in enumerate(sorted(local, key=lambda n: _bound_names(ffn)[n]))}

            class Ren(ast.NodeTransformer):
                def visit_Name(self, n):
                    if n.id in local:
                        return ast.copy_location(ast.Name(
                            id=f"{_PLACE}{inst}|{pos[0]:08d}|{pos[1] + 1:04d}|{order[n.id]:04d}|{n.id}", ctx=n.ctx), n)
                    return n

            for el in inner:
                if el.get("node") is not None:
                    el["node"] = Ren().visit(el["node"])
            els.extend(inner)
            fparams = [x.arg for x in ffn.args.args]
            queue += [(p, pos) for p in fparams if p in fx]
        return self.normalize(fn, els)

    def normalize(self, fn: ast.AST, els: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        bound = _bound_names(fn)
        used: Dict[str, Tuple] = {}
        for el in els:
            if el.get("node") is None:
                continue
            for n in ast.walk(el["node"]):
                if isinstance(n, ast.Name):
                    if n.id.startswith(_PLACE):
                        _, line, col, idx, _ = n.id[len(_PLACE):].split("|", 4)
                        used.setdefault(n.id, (int(line), int(col), 1, int(idx)))
                    elif n.id in bound:
                        used.setdefault(n.id, (*bound[n.id], 0, 0))
        ordinal = {name: f"_{i}" for i, name in enumerate(sorted(used, key=lambda k: used[k]))}

        class R(ast.NodeTransformer):
            def visit_Name(self, n):
                if n.id in ordinal:
                    return ast.Name(id=ordinal[n.id], ctx=n.ctx)
                return n

        out = []
        for el in els:
            e = dict(el)
            if el.get("node") is None:
                e["key"] = el["opaque"]
            else:
                e["key"] = ast.dump(R().visit(copy.deepcopy(el["node"])), annotate_fields=True, include_attributes=False)
            out.append(e)
        return out

class TestregError(RuntimeError):
    """無法判定（catalog／schema 不存在或不可解析、用法錯誤等）；訊息具名原因與路徑。"""

    __test__ = False  # 名稱以 Test 開頭，防 pytest 誤收集


@dataclass(frozen=True)
class Finding:
    """一項不符。`rule` 為規則 id 或類別字（見模組說明）；`subject` 為 entry 路徑、nodeid、收據或 manifest 路徑。"""

    rule: str
    subject: str
    message: str
    unverifiable: bool = False

    def render(self) -> str:
        """stderr 單列：`<rule> <subject>: <message>`（unverifiable 者訊息含該字）。"""
        msg = " ".join(self.message.split())
        if self.unverifiable and "unverifiable" not in msg:
            msg = f"unverifiable：{msg}"
        return f"{self.rule} {self.subject}: {msg}"


@dataclass
class Context:
    """一次驗證之受驗之樹與輸入。`tree`＝"worktree"（hook、手動 validate）或 "staged"（pre-commit）；
    `head_catalog` 為 `git show HEAD:tests/registry/catalog.json`（HEAD 無此檔為 None）；`scope_paths` 為 check
    之受檢範圍（None＝全部）。其餘內部欄位由實作自訂。"""

    repo_root: Path
    tree: str
    schema: Dict[str, Any]
    catalog: Dict[str, Any]
    head_catalog: Optional[Dict[str, Any]]
    ledger_dir: Path
    require_executed: bool = False
    scope_paths: Optional[FrozenSet[str]] = None
    extra: Dict[str, Any] = field(default_factory=dict)


# ── Task 1.1：契約與 validate ─────────────────────────────────────────────────────────────────────────


def load_schema(repo_root: Path) -> Dict[str, Any]:
    """讀 `<repo_root>/tests/registry/testreg_schema.json`；不存在或不可解析 ⇒ TestregError。"""
    p = Path(repo_root) / SCHEMA_REL
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TestregError(f"SCHEMA {SCHEMA_REL}: 不存在或不可解析（{type(exc).__name__}）") from exc


def load_catalog(repo_root: Path, tree: str = "worktree") -> Dict[str, Any]:
    """讀受驗之樹之 catalog（worktree＝檔案；staged＝`git show :tests/registry/catalog.json`）；不存在 ⇒ TestregError。"""
    text = _Tree(Path(repo_root), tree).read(CATALOG_REL)
    if text is None:
        raise TestregError(f"CATALOG {CATALOG_REL}: 不存在")
    try:
        return json.loads(text)
    except ValueError as exc:
        raise TestregError(f"CATALOG {CATALOG_REL}: JSON 不可解析") from exc


def build_context(repo_root: Path, tree: str = "worktree", *, require_executed: bool = False,
                  scope_paths: Optional[Iterable[str]] = None) -> Context:
    """組 Context；ledger 目錄依 schema `ledger.dir`（相對 repo_root）。"""
    root = Path(repo_root).resolve()
    schema = load_schema(root)
    catalog = load_catalog(root, tree)
    head = _Tree(root, "HEAD")
    head_text = head.read(CATALOG_REL)
    try:
        head_catalog = json.loads(head_text) if head_text else None
    except ValueError:
        head_catalog = None
    t = _Tree(root, tree)
    ctx = Context(root, tree, schema, catalog, head_catalog, root / schema["ledger"]["dir"], require_executed,
                  frozenset(scope_paths) if scope_paths is not None else None)
    ctx.extra.update(tree_obj=t, head_obj=head, head_sha=_head_sha(root), engines={}, ledger={})
    ctx.extra["changed"] = _changed_paths(root, tree)
    return ctx


def _changed_paths(root: Path, tree: str) -> Dict[str, str]:
    if tree == "staged":
        return _seam("staged_changes")(root)
    if not _head_sha(root):
        return {p: "A" for p in _Tree(root, "worktree").files()}
    out: Dict[str, str] = {}
    for line in _git_out(root, "diff", "--name-status", "--no-renames", "HEAD").splitlines():
        if line.strip():
            st, _, p = line.partition("\t")
            out[p] = st[0]
    for p in _git_out(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
        if p:
            out.setdefault(p, "A")
    return out


def _tree(ctx: Context) -> "_Tree":
    return ctx.extra["tree_obj"]


_ENGINES: Dict[Tuple[str, str], "_Engine"] = {}


def _shared_engine(root: Path, kind: str) -> "_Engine":
    """同一短命行程內同一 (repo, 樹) 共用引擎與其解析快取（hook／pre-commit 行程中樹內容不變）。"""
    key = (str(Path(root).resolve()), kind)
    if key not in _ENGINES:
        _ENGINES[key] = _Engine(_Tree(Path(root), kind))
    return _ENGINES[key]


def _engine_for(ctx: Context, kind: str) -> "_Engine":
    engines = ctx.extra["engines"]
    if kind not in engines:
        engines[kind] = _shared_engine(ctx.repo_root, kind)
    return engines[kind]


def validate(repo_root: Path, *, tree: str = "worktree", require_executed: bool = False) -> List[Finding]:
    """依 schema `validation_rules` 逐條呼叫 `rule_<id>`（呼叫當下以模組屬性取用）；V21 只於 require_executed=True 時
    執行。回傳全部不符（空＝通過）。"""
    ctx = build_context(repo_root, tree, require_executed=require_executed)
    out: List[Finding] = []
    for rule in ctx.schema["validation_rules"]:
        rid = rule["id"]
        if rid == "V21" and not require_executed:
            continue
        out.extend(_seam(f"rule_{rid.lower()}")(ctx))
    return out


def validate_shape(value: Any, type_spec: Mapping[str, Any], schema: Mapping[str, Any], where: str = "") -> List[str]:
    """V17 之單一實作：依 type／format／items／items_format／items_enum／min_items／max_items_ref／min／finite／const／
    key_format／additional_properties／allow_unknown（數值欄另許字面 "unknown"）與 types.* 遞迴驗形；catalog、summary、
    收據、閘收據、子批收據、成效報告與 V-6 收據共用。回傳錯誤訊息清單。"""
    errs: List[str] = []
    _shape(value, type_spec, schema, where or "$", errs)
    return errs


def _resolve(schema: Mapping[str, Any], ref: str) -> Any:
    node: Any = schema
    for part in ref.split("."):
        node = node[part]
    return node


def _enum_values(schema: Mapping[str, Any], ref: str) -> List[Any]:
    vals = _resolve(schema, ref)
    return list(vals) if isinstance(vals, list) else []


def _is_ref(t: Any) -> bool:
    return isinstance(t, str) and (t.startswith("types.") or t.startswith("catalog."))


def _shape(v: Any, spec: Mapping[str, Any], schema: Mapping[str, Any], where: str, errs: List[str]) -> None:
    t = spec.get("type")
    if _is_ref(t):
        _shape(v, _resolve(schema, t), schema, where, errs)
        return
    nullable = isinstance(t, str) and t.endswith("|null")
    base = t[:-5] if nullable else t
    if v is None:
        if not nullable:
            errs.append(f"{where}: 不得為 null")
        return
    fmts = schema["formats"]
    if base == "string":
        if not isinstance(v, str):
            errs.append(f"{where}: 須為字串")
            return
        if spec.get("format") and re.fullmatch(fmts[spec["format"]], v) is None:
            errs.append(f"{where}: 不符格式 {spec['format']}")
        if "const" in spec and v != spec["const"]:
            errs.append(f"{where}: 須為 {spec['const']!r}")
    elif base == "int":
        if not isinstance(v, int) or isinstance(v, bool):
            errs.append(f"{where}: 須為整數")
    elif base == "number":
        if spec.get("allow_unknown") and v == "unknown":
            return
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errs.append(f"{where}: 須為數值")
            return
        if spec.get("finite") and not math.isfinite(v):
            errs.append(f"{where}: 須為有限數值")
            return
        if "min" in spec and v < spec["min"]:
            errs.append(f"{where}: 須 ≥ {spec['min']}")
    elif base == "bool":
        if not isinstance(v, bool):
            errs.append(f"{where}: 須為布林")
    elif base == "enum":
        if v not in _enum_values(schema, spec["values"]):
            errs.append(f"{where}: 不屬 {spec['values']}")
    elif base == "array":
        if not isinstance(v, list):
            errs.append(f"{where}: 須為陣列")
            return
        if len(v) < spec.get("min_items", 0):
            errs.append(f"{where}: 元素數須 ≥ {spec['min_items']}")
        if "max_items_ref" in spec and len(v) > int(_resolve(schema, spec["max_items_ref"])):
            errs.append(f"{where}: 元素數超過 {spec['max_items_ref']}")
        item = spec.get("items")
        for i, x in enumerate(v):
            w = f"{where}[{i}]"
            if "items_enum" in spec:
                if x not in _enum_values(schema, spec["items_enum"]):
                    errs.append(f"{w}: 不屬 {spec['items_enum']}")
            elif _is_ref(item):
                _shape(x, {"type": item}, schema, w, errs)
            elif item == "string":
                _shape(x, {"type": "string", **({"format": spec["items_format"]} if "items_format" in spec else {})},
                       schema, w, errs)
    elif base == "map":
        if not isinstance(v, dict):
            errs.append(f"{where}: 須為物件（map）")
            return
        for k, x in v.items():
            if spec.get("key_format") and (not isinstance(k, str) or re.fullmatch(fmts[spec["key_format"]], k) is None):
                errs.append(f"{where}: 鍵 {k!r} 不符格式 {spec['key_format']}")
            if isinstance(spec.get("values"), Mapping):
                _shape(x, spec["values"], schema, f"{where}[{k!r}]", errs)
    elif base == "object":
        if not isinstance(v, dict):
            errs.append(f"{where}: 須為物件")
            return
        fields = spec.get("fields", {})
        required = {k for k, f in fields.items() if f.get("required")}
        if spec.get("additional_properties") is False:
            extra, missing = set(v) - set(fields), required - set(v)
            if extra:
                errs.append(f"{where}: 多出欄位 {sorted(extra)}")
            if missing:
                errs.append(f"{where}: 缺欄位 {sorted(missing)}")
        for k, f in fields.items():
            if k in v:
                _shape(v[k], f, schema, f"{where}.{k}", errs)
    else:
        errs.append(f"{where}: 未知型別 {t!r}")


def multiset_decreased(old: "collections.Counter[str]", new: "collections.Counter[str]") -> List[str]:
    """V19：回傳 old 中計數大於 new 之元素（多重集合減少；非僅比總數）。"""
    return sorted(k for k, n in old.items() if n > new.get(k, 0))


def _tree_kind(tree: str) -> str:
    return tree


def assertion_multiset(repo_root: Path, nodeid: str, tree: str = "worktree") -> "collections.Counter[str]":
    """某測試函式（函式層 nodeid）於受驗之樹（"HEAD"／"staged"／"worktree"）之斷言多重集合：依 schema
    `assertion_nodes`（kinds、assertion_helpers、inline_rule、normalize）由 AST 導出；元素帶 provenance 另由實作保存。"""
    t = _Tree(Path(repo_root), tree)
    if _skip_like(t, nodeid):
        return collections.Counter()  # schema assertion_nodes.skip_rule
    return collections.Counter(e["key"] for e in _Engine(t).elements(nodeid))


def _engine_elements(eng: "_Engine", nodeid: str) -> List[Dict[str, Any]]:
    return eng.elements(nodeid)


def _e1_parts(eng: "_Engine", nodeid: str) -> Optional[Dict[str, str]]:
    path, qual = _split_nodeid(nodeid)
    src = eng.tree.read(path)
    fn = _test_functions(src).get(qual)
    mi = eng.mod(path)
    if fn is None or mi is None:
        return None
    anon = copy.deepcopy(fn)
    anon.name = ""
    ast_sha = _sha256_text(ast.dump(anon, annotate_fields=True, include_attributes=False))
    fx = eng.fixture_defs(path)
    params = [a.arg for a in [*getattr(fn.args, "posonlyargs", []), *fn.args.args, *fn.args.kwonlyargs]]
    queue = [p for p in params if p in fx] + sorted(n for n, (_, _, auto) in fx.items() if auto)
    seen: Dict[str, str] = {}
    while queue:
        name = queue.pop(0)
        if name in seen or name not in fx:
            continue
        fpath, ffn, _ = fx[name]
        seen[name] = _sha256_text(ast.dump(ffn, annotate_fields=True, include_attributes=False))
        queue += [a.arg for a in ffn.args.args if a.arg in fx]
    fixture_sha = _sha256_text(json.dumps(sorted(seen.items())))
    ctx_parts: List[str] = []
    refs = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for name in sorted(refs):
        for st in mi.assigns.get(name, []):
            ctx_parts.append(ast.dump(st, include_attributes=False))
        if name in mi.defs and name not in fx:
            ctx_parts.append(ast.dump(mi.defs[name], include_attributes=False))
        if name in mi.classes:
            ctx_parts.append(ast.dump(mi.classes[name], include_attributes=False))
        for n in mi.tree.body:
            if isinstance(n, (ast.Import, ast.ImportFrom)) and any((al.asname or al.name).split(".")[0] == name for al in n.names):
                ctx_parts.append(ast.dump(n, include_attributes=False))
    for st in mi.assigns.get("pytestmark", []):
        ctx_parts.append("pytestmark:" + ast.dump(st, include_attributes=False))
    if "::" in qual:
        cls = mi.classes.get(qual.split("::")[0])
        if cls is not None:
            ctx_parts.extend(_class_context(eng, mi, cls, set()))
    return {"ast": ast_sha, "fixture_closure": fixture_sha, "module_context": _sha256_text(json.dumps(ctx_parts))}


_LIFECYCLE = ("setup_method", "teardown_method", "setup_class", "teardown_class", "setup_module", "teardown_module",
              "setup_function", "teardown_function")


def _class_context(eng: "_Engine", mi: "_Mod", cls: ast.ClassDef, seen: set) -> List[str]:
    if cls.name in seen:
        return []
    seen.add(cls.name)
    out = ["decorators:" + ast.dump(ast.List(elts=cls.decorator_list, ctx=ast.Load()), include_attributes=False)]
    for st in cls.body:
        if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in st.targets):
            out.append("cls-pytestmark:" + ast.dump(st, include_attributes=False))
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)) and st.name in _LIFECYCLE:
            out.append("lifecycle:" + ast.dump(st, include_attributes=False))
    for b in cls.bases:
        if isinstance(b, ast.Name) and b.id in mi.classes:
            out.append("base:" + ast.dump(mi.classes[b.id], include_attributes=False))
            out.extend(_class_context(eng, mi, mi.classes[b.id], seen))
        else:
            out.append("base-ext:" + ast.dump(b, include_attributes=False))
    return out


def e1_hashes(repo_root: Path, nodeid: str, tree: str = "worktree") -> Dict[str, str]:
    """E1 收據三雜湊之單一實作（validate 重算同用）：{"ast": FunctionDef 去名去屬性後 ast.dump 之 sha256,
    "fixture_closure": ..., "module_context": ...}，定義見 schema `receipts.E1.rule`；tree＝"HEAD"／"staged"／"worktree"。"""
    parts = _e1_parts(_Engine(_Tree(Path(repo_root), tree)), nodeid)
    if parts is None:
        raise TestregError(f"V08 {nodeid}: 於 {tree} 找不到函式")
    return parts


def assertion_lines(repo_root: Path, nodeid: str, tree: str = "worktree") -> List[str]:
    """`assertion_multiset` 之 provenance 位置清單（file:line，排序；mutation 收據之 target_assertion_lines 由此導出）。"""
    els = _Engine(_Tree(Path(repo_root), tree)).elements(nodeid)
    return sorted({f"{e['prov'][0]}:{e['prov'][1]}" for e in els})


def staged_changes(repo_root: Path) -> Dict[str, str]:
    """暫存區相對 HEAD 之變更：{repo 相對路徑: 狀態字（A／M／D；改名拆為 D＋A）}；pre-commit 之 V07／V19／V20 以此定範圍。"""
    root = Path(repo_root)
    if not _head_sha(root):
        return {p: "A" for p in _Tree(root, "staged").files()}
    out: Dict[str, str] = {}
    for line in _git_out(root, "diff", "--cached", "--name-status", "--no-renames", "HEAD").splitlines():
        if line.strip():
            st, _, p = line.partition("\t")
            out[p] = st[0]
    return out

def _entries(ctx: Context) -> Dict[str, Any]:
    e = ctx.catalog.get("entries") if isinstance(ctx.catalog, dict) else None
    return e if isinstance(e, dict) else {}


def _tombs(ctx: Context) -> List[Dict[str, Any]]:
    t = ctx.catalog.get("tombstones") if isinstance(ctx.catalog, dict) else None
    return [x for x in t if isinstance(x, dict)] if isinstance(t, list) else []


def _tomb_ids(ctx: Context) -> set:
    return {t.get("nodeid") for t in _tombs(ctx)}


def _scoped(ctx: Context, path: str) -> bool:
    return ctx.scope_paths is None or path in ctx.scope_paths


def _req_fields(spec: Mapping[str, Any]) -> set:
    return {k for k, f in spec.get("fields", {}).items() if f.get("required")}


def rule_v01(ctx: Context) -> List[Finding]:
    """V01（規則本文見 schema validation_rules）。"""
    out: List[Finding] = []
    t, head, tombs = _tree(ctx), ctx.extra["head_obj"], _tomb_ids(ctx)
    for path in sorted(_entries(ctx)):
        if not _scoped(ctx, path) or t.exists(path):
            continue
        head_fns = _function_nodeids(head, path)
        if head_fns:
            miss = [n for n in head_fns if n not in tombs]
            if miss:
                out.append(Finding("V01", path, f"檔不存在而函式未全數立碑：{', '.join(miss[:3])}"))
        elif not any(str(n).split("::")[0] == path for n in tombs):
            out.append(Finding("V01", path, "entry 所指檔不存在且無任何碑"))
    return out


def rule_v02(ctx: Context) -> List[Finding]:
    """V02。"""
    ent = _entries(ctx)
    return [Finding("V02", f, "測試檔無 catalog entry") for f in _tree(ctx).test_files(ctx.schema)
            if _scoped(ctx, f) and f not in ent]


def rule_v03(ctx: Context) -> List[Finding]:
    """V03。"""
    out: List[Finding] = []
    cs = ctx.schema["catalog"]
    req, forbidden = _req_fields(cs["entries"]), set(cs["entries"]["forbidden_fields"])
    for path, e in sorted(_entries(ctx).items()):
        if not _scoped(ctx, path):
            continue
        if not isinstance(e, dict):
            out.append(Finding("V03", path, "entry 須為物件"))
            continue
        if set(e) != req:
            out.append(Finding("V03", path, f"欄位集合不符：多 {sorted(set(e) - req)} 缺 {sorted(req - set(e))}"))
        if set(e) & forbidden:
            out.append(Finding("V03", path, f"含禁存欄位 {sorted(set(e) & forbidden)}"))
        if e.get("path") != path:
            out.append(Finding("V03", path, f"path 欄 {e.get('path')!r} 與鍵不同"))
        for q in e.get("quarantine", []) if isinstance(e.get("quarantine"), list) else []:
            if isinstance(q, dict) and set(q) != _req_fields(cs["quarantine_record"]):
                out.append(Finding("V03", path, "quarantine 紀錄欄位集合不符"))
    if ctx.scope_paths is None:
        treq = _req_fields(cs["tombstones"])
        for tb in _tombs(ctx):
            if set(tb) != treq:
                out.append(Finding("V03", str(tb.get("nodeid")), "碑欄位集合不符"))
    return out


def rule_v04(ctx: Context) -> List[Finding]:
    """V04。"""
    if not ctx.head_catalog:
        return []
    wo = [k for k, f in ctx.schema["catalog"]["entries"]["fields"].items() if f.get("write_once")]
    head = ctx.head_catalog.get("entries", {})
    out = []
    for path, e in sorted(_entries(ctx).items()):
        if _scoped(ctx, path) and path in head and isinstance(e, dict):
            for k in wo:
                if k in head[path] and e.get(k) != head[path].get(k):
                    out.append(Finding("V04", path, f"write_once 欄 {k} 與 HEAD 不同"))
    return out


def rule_v05(ctx: Context) -> List[Finding]:
    """V05。"""
    out = []
    fields = ctx.schema["catalog"]["entries"]["fields"]
    for path, e in sorted(_entries(ctx).items()):
        if not _scoped(ctx, path) or not isinstance(e, dict):
            continue
        for k, f in fields.items():
            v = e.get(k)
            if f.get("type") == "enum" and v not in _enum_values(ctx.schema, f["values"]):
                out.append(Finding("V05", path, f"{k}={v!r} 不屬 {f['values']}"))
            if "items_enum" in f and isinstance(v, list):
                bad = [x for x in v if x not in _enum_values(ctx.schema, f["items_enum"])]
                if bad:
                    out.append(Finding("V05", path, f"{k} 含非枚舉值 {bad}"))
            if "min_items" in f and isinstance(v, list) and len(v) < f["min_items"]:
                out.append(Finding("V05", path, f"{k} 元素數 < {f['min_items']}"))
    return out


def rule_v06(ctx: Context) -> List[Finding]:
    """V06。"""
    return [Finding("V06", p, "disposition=rewrite 而 disposition_ref 為 null") for p, e in sorted(_entries(ctx).items())
            if _scoped(ctx, p) and isinstance(e, dict) and e.get("disposition") == "rewrite" and e.get("disposition_ref") is None]


def _ledger_session(ctx: Context, sid: str) -> Optional[Dict[str, Any]]:
    cache = ctx.extra["ledger"]
    if sid not in cache:
        p = ctx.ledger_dir / f"{sid}.jsonl"
        if not p.is_file():
            cache[sid] = None
        else:
            recs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
            sess = next((r for r in recs if r.get("kind") == "session"), None)
            cache[sid] = {"session": sess, "tests": {r["nodeid"]: r for r in recs if r.get("kind") == "test"}}
    return cache[sid]


def _fn_record(sess: Mapping[str, Any], nodeid: str) -> Optional[Dict[str, Any]]:
    """函式層比對：參數化取任一案例失敗即視為失敗。"""
    hits = [r for n, r in sess["tests"].items() if re.sub(r"\[.*\]$", "", n) == nodeid]
    if not hits:
        return None
    bad = [r for r in hits if r["outcome"] in ("failed", "error")]
    return bad[0] if bad else hits[0]


def _receipt_head_problem(ctx: Context, rel: str, head: str) -> Optional[str]:
    hs = ctx.extra["head_sha"]
    is_new = ctx.extra["head_obj"].read(rel) != _tree(ctx).read(rel)
    if is_new:
        return None if head == hs else f"新增或變更之收據 head {head[:8]} ≠ HEAD"
    return None if hs and _is_ancestor(ctx.repo_root, head, hs) else "既有收據之 head 非 HEAD 之祖先"


def _load_receipt(ctx: Context, rel: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not rel:
        return None, "收據路徑為 null"
    text = _tree(ctx).read(rel)
    if text is None:
        return None, f"收據 {rel} 不存在"
    try:
        return json.loads(text), None
    except ValueError:
        return None, f"收據 {rel} 非 JSON"


def _digest_with(ctx: Context, head: str, patches: Sequence[str]) -> str:
    """於 head 乾淨樹依序套用 patches（取受驗之樹之補丁內容）後之 diff_digest（記錄器之單一實作）。"""
    key = (head, tuple(patches))
    cache = ctx.extra.setdefault("digests", {})
    if key in cache:
        return cache[key]
    tmp = Path(tempfile.mkdtemp(prefix="testreg-digest-"))
    wt = tmp / "wt"
    _run_git(ctx.repo_root, "worktree", "add", "-q", "--detach", str(wt), head)
    try:
        for rel in patches:
            pf = tmp / f"p{len(list(tmp.iterdir()))}.patch"
            pf.write_text(_tree(ctx).read(rel) or "", encoding="utf-8")
            _run_git(wt, "apply", str(pf))
        cache[key] = _plugin_module().diff_digest(wt)
    finally:
        _run_git(ctx.repo_root, "worktree", "remove", "--force", str(wt), check=False)
    return cache[key]


def _patch_paths(text: str) -> List[str]:
    return sorted({m.group(2) for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)$", text, re.M)})


def _check_mutation(ctx: Context, rcpt: Mapping[str, Any], rel: str, target: str, compare: Iterable[str]) -> List[str]:
    errs = validate_shape(rcpt, {"type": "types.receipt_mutation"}, ctx.schema)
    if errs:
        return errs
    root, schema = ctx.repo_root, ctx.schema
    if rcpt["target_nodeid"] != target:
        errs.append(f"target_nodeid {rcpt['target_nodeid']} ≠ {target}")
    hp = _receipt_head_problem(ctx, rel, rcpt["head"])
    if hp:
        errs.append(hp)
    comp = set(compare)
    if set(rcpt["compare_nodeids"]) != comp:
        errs.append(f"compare_nodeids ≠ {sorted(comp)}")
    head_eng = _engine_for(ctx, f"rev:{rcpt['head']}")
    els = head_eng.elements(target)
    lines = sorted({f"{e['prov'][0]}:{e['prov'][1]}" for e in els if e.get("prov")})
    if sorted(set(rcpt["target_assertion_lines"])) != lines:
        errs.append(f"target_assertion_lines 與重算 {lines} 不同")
    roots = tuple(schema["receipts"]["E0"]["production_roots"])
    tpath, tqual = _split_nodeid(target)
    tfn = _test_functions(head_eng.tree.read(tpath)).get(tqual)
    files = {l.rsplit(":", 1)[0] for l in lines} or {tpath}
    kills = []
    sessions_dc = set()
    cpatch = rcpt["compare_patch_path"]
    if cpatch:
        ptext = _tree(ctx).read(cpatch)
        if ptext is None or hashlib.sha256(ptext.encode("utf-8")).hexdigest() != rcpt["compare_patch_sha256"]:
            errs.append("compare_patch 不存在或 sha256 不符")
        else:
            touched = set(_patch_paths(ptext))
            if not touched <= {c.split("::")[0] for c in comp}:
                errs.append("compare_patch 修改了 compare 所在以外之檔")
            cmp_eng_tree = _tree(ctx)
            tmp_tree = _PatchedTree(ctx, rcpt["head"], cpatch)
            for c in comp:
                cp, cq = _split_nodeid(c)
                a = _test_functions(tmp_tree.read(cp)).get(cq)
                b = _test_functions(cmp_eng_tree.read(cp)).get(cq)
                if a is None or b is None or ast.dump(a) != ast.dump(b):
                    errs.append(f"compare_patch 套用後之 {c} 與受驗之樹不同")
    for m in rcpt["mutants"]:
        ptext = _tree(ctx).read(m["patch_path"])
        if ptext is None or hashlib.sha256(ptext.encode("utf-8")).hexdigest() != m["patch_sha256"]:
            errs.append(f"mutant {m['id']} 補丁不存在或 sha256 不符")
            continue
        if any(not (p.startswith(roots) or p in roots) for p in _patch_paths(ptext)):
            errs.append(f"mutant {m['id']} 修改 production_roots 以外之檔")
        if set(m["compare_outcomes"]) != comp:
            errs.append(f"mutant {m['id']} compare_outcomes 鍵集合 ≠ compare_nodeids")
        if not cpatch and m["compare_session_id"] != m["session_id"]:
            errs.append(f"mutant {m['id']} 無 compare_patch 而 compare_session_id ≠ session_id")
        s = _ledger_session(ctx, m["session_id"])
        cs = _ledger_session(ctx, m["compare_session_id"])
        if s is None or cs is None:
            errs.append(f"unverifiable：mutant {m['id']} 之 session 不在 ledger")
            continue
        for sess, patches in ((s, [m["patch_path"]]), (cs, ([cpatch] if cpatch else []) + [m["patch_path"]])):
            info = sess["session"] or {}
            sessions_dc.add(info.get("duration_class"))
            if info.get("head") != rcpt["head"] or info.get("diff_digest") != _digest_with(ctx, rcpt["head"], patches):
                errs.append(f"mutant {m['id']} 之 session 不綁定 head＋補丁")
        tr = _fn_record(s, target)
        if tr is None:
            errs.append(f"mutant {m['id']} 之 session 無 target 紀錄")
            continue
        loc = next((f for f in tr.get("fail_frames", []) if f.rsplit(":", 1)[0] in files), None)
        if tr["outcome"] != m["target_outcome"] or loc != m["target_fail_loc"]:
            errs.append(f"mutant {m['id']} 之 target 結果與紀錄不符")
        for c in comp:
            cr = _fn_record(cs, c)
            if cr is None or cr["outcome"] != m["compare_outcomes"].get(c):
                errs.append(f"mutant {m['id']} 之 {c} 結果與紀錄不符")
        if tr["outcome"] in ("failed", "error"):
            kills.append((m, tr))
            if not any(v in ("failed", "error") for v in m["compare_outcomes"].values()):
                errs.append(f"mutant {m['id']} 殺 target 而無 compare 被殺")
    if None in sessions_dc or len(sessions_dc) > 1 or (sessions_dc and rcpt["fingerprint"] not in sessions_dc):
        errs.append("各 session 之 duration_class 不一或不等於 fingerprint")
    if not kills:
        errs.append("無任何殺 target 之 mutant")

    def frame_in(tr, lo, hi, f):
        return any(fr.rsplit(":", 1)[0] == f and lo <= int(fr.rsplit(":", 1)[1]) <= hi for fr in tr.get("fail_frames", []))

    for e in els:
        f, lo, hi = e["prov"]
        owner = e.get("owner") or (f, lo, hi, "helper")
        ok = False
        for m, tr in kills:
            loc = m["target_fail_loc"]
            if not loc or loc.rsplit(":", 1)[0] != f or not lo <= int(loc.rsplit(":", 1)[1]) <= hi:
                continue
            if owner[3] == "fixture":
                ok = tr["phase_failed"] in ("setup", "teardown") and frame_in(tr, owner[1], owner[2], owner[0])
            else:
                ok = tr["phase_failed"] == "call" and frame_in(tr, owner[1], owner[2], owner[0])
            if ok:
                break
        if not ok:
            errs.append(f"斷言 {f}:{lo} 無對應之殺 mutant")
    if not els and tfn is not None:
        if not any(tr["phase_failed"] == "call" and frame_in(tr, tfn.lineno, tfn.end_lineno, tpath) for _, tr in kills):
            errs.append("無斷言 target 之殺 mutant 未於 call 期在 target 函式內失敗")
    return errs


class _PatchedTree:
    """head 之樹套用一個補丁後之唯讀視圖（只供 compare_patch 之函式比對）。"""

    def __init__(self, ctx: Context, head: str, patch_rel: str):
        self._files: Dict[str, Optional[str]] = {}
        tmp = Path(tempfile.mkdtemp(prefix="testreg-cp-"))
        wt = tmp / "wt"
        _run_git(ctx.repo_root, "worktree", "add", "-q", "--detach", str(wt), head)
        try:
            pf = tmp / "c.patch"
            pf.write_text(_tree(ctx).read(patch_rel) or "", encoding="utf-8")
            ok = _run_git(wt, "apply", str(pf), check=False).returncode == 0
            for p in _patch_paths(pf.read_text(encoding="utf-8")):
                self._files[p] = (wt / p).read_text(encoding="utf-8") if ok and (wt / p).is_file() else None
        finally:
            _run_git(ctx.repo_root, "worktree", "remove", "--force", str(wt), check=False)

    def read(self, rel: str) -> Optional[str]:
        return self._files.get(rel)


def _covered(ctx: Context, entry: Mapping[str, Any]) -> List[str]:
    targets = entry.get("rewrite_targets") or []
    if targets:
        return sorted({re.sub(r"\[.*\]$", "", t) for t in targets})
    return _function_nodeids(_tree(ctx), entry["path"])


def _rewrite_receipt_errors(ctx: Context, entry: Mapping[str, Any]) -> List[str]:
    key = ("rw", entry["path"], entry.get("rewrite_receipt"))
    cache = ctx.extra.setdefault("rw_cache", {})
    if key in cache:
        return cache[key]
    rcpt, err = _load_receipt(ctx, entry.get("rewrite_receipt"))
    if err:
        cache[key] = [err]
        return cache[key]
    shape = validate_shape(rcpt, {"type": "types.receipt_mutation"}, ctx.schema)
    if shape:
        cache[key] = shape
        return shape
    cov = _covered(ctx, entry)
    errs = [] if rcpt["target_nodeid"] in cov else [f"rewrite 收據之 target 不屬 rewrite_targets"]
    errs += _check_mutation(ctx, rcpt, entry["rewrite_receipt"], rcpt["target_nodeid"], cov)
    cache[key] = errs
    return errs


def rule_v07_receipt_valid(ctx: Context) -> List[Finding]:
    """V07 前半：rewrite_receipt 非 null ⇒ 依 receipts.mutation 全部 rule 與 binding_rule 驗過。"""
    out = []
    for p, e in sorted(_entries(ctx).items()):
        if _scoped(ctx, p) and isinstance(e, dict) and e.get("rewrite_receipt"):
            for err in _rewrite_receipt_errors(ctx, e):
                out.append(Finding("V07", p, err, unverifiable="unverifiable" in err))
    return out


def rule_v07_change_requires_receipt(ctx: Context) -> List[Finding]:
    """V07 後半：暫存區中 disposition=rewrite 之檔有內容變更 ⇒ 同提交之 rewrite_receipt 非 null 且驗過。"""
    if ctx.tree != "staged":
        return []
    out = []
    changed = ctx.extra["changed"]
    for p, e in sorted(_entries(ctx).items()):
        if isinstance(e, dict) and e.get("disposition") == "rewrite" and changed.get(p) in ("M", "A"):
            if not e.get("rewrite_receipt"):
                out.append(Finding("V07", p, "待改寫檔有暫存變更而無 rewrite_receipt"))
            else:
                out.extend(Finding("V07", p, err) for err in _rewrite_receipt_errors(ctx, e))
    return out


def rule_v07(ctx: Context) -> List[Finding]:
    """V07＝`rule_v07_receipt_valid` ∪ `rule_v07_change_requires_receipt`（兩者皆於呼叫當下以模組屬性取用）。"""
    seen, out = set(), []
    for f in [*_seam("rule_v07_receipt_valid")(ctx), *_seam("rule_v07_change_requires_receipt")(ctx)]:
        if (f.subject, f.message) not in seen:
            seen.add((f.subject, f.message))
            out.append(f)
    return out


def _module_defines(src: Optional[str], symbol: str) -> bool:
    if src is None:
        return False
    try:
        mod = ast.parse(src)
    except SyntaxError:
        return False
    for n in mod.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == symbol:
            return True
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == symbol for t in n.targets):
            return True
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == symbol:
            return True
    return False


def _module_file(tree: "_Tree", dotted: str) -> Optional[str]:
    base = dotted.replace(".", "/")
    for cand in (base + ".py", base + "/__init__.py"):
        if tree.read(cand) is not None:
            return cand
    return None


def _check_e0(ctx: Context, tomb: Mapping[str, Any], rcpt: Mapping[str, Any], rel: str) -> List[str]:
    errs = validate_shape(rcpt, {"type": "types.receipt_E0"}, ctx.schema)
    if errs:
        return errs
    if rcpt["nodeid"] != tomb["nodeid"] or rcpt["ledger_ref"]["nodeid"] != tomb["nodeid"]:
        errs.append("收據之 nodeid／ledger_ref 與碑不符")
    hp = _receipt_head_problem(ctx, rel, rcpt["head"])
    if hp:
        errs.append(hp)
    s = _ledger_session(ctx, rcpt["ledger_ref"]["session_id"])
    if s is None:
        return errs + ["unverifiable：ledger_ref 之 session 不在 ledger"]
    rec = s["tests"].get(rcpt["ledger_ref"]["nodeid"])
    info = s["session"] or {}
    if rec is None:
        return errs + ["ledger_ref 之紀錄不存在"]
    if info.get("head") != rcpt["head"] or info.get("diff_digest") != "clean":
        errs.append("紀錄之 session 非於收據 head 之乾淨樹")
    if rec["outcome"] not in ("failed", "error"):
        errs.append(f"目標於 head 之結果為 {rec['outcome']}（須 failed／error）")
    e0_types = ctx.schema["enums"]["e0_exception_types"]
    if rec.get("exception_type") not in e0_types or rec.get("exception_type") != rcpt["exception_type"]:
        errs.append("例外型別不符 E0")
    if rec.get("exception_origin") != rcpt["exception_origin"]:
        errs.append("exception_origin 與紀錄不符")
    sym, modname = rcpt["deleted_symbol"], rcpt["deleted_module"]
    if sym not in (rec.get("exception_head") or ""):
        errs.append("exception_head 不含 deleted_symbol")
    tpath = tomb["nodeid"].split("::")[0]
    opath, _, oline = rcpt["exception_origin"].rpartition(":")
    head_tree = _Tree(ctx.repo_root, f"rev:{rcpt['head']}")
    src = head_tree.read(tpath)
    if opath != tpath or src is None:
        errs.append("失敗行不在目標測試檔")
    else:
        mod = ast.parse(src)
        line = int(oline)
        aliases = {}
        for n in mod.body:
            if isinstance(n, ast.Import):
                for al in n.names:
                    if al.name == modname:
                        aliases[al.asname or al.name] = modname
        ok = False
        for n in ast.walk(mod):
            if getattr(n, "lineno", None) != line:
                continue
            if isinstance(n, ast.ImportFrom) and n.module == modname and any(al.name == sym for al in n.names) \
                    and rcpt["exception_type"] in ("ImportError", "ModuleNotFoundError"):
                ok = True
            if isinstance(n, ast.Attribute) and n.attr == sym and isinstance(n.value, ast.Name) \
                    and aliases.get(n.value.id) == modname and rcpt["exception_type"] == "AttributeError":
                ok = True
        if not ok:
            errs.append("失敗行非以模組綁定 import／屬性存取 deleted_symbol")
    roots = tuple(ctx.schema["receipts"]["E0"]["production_roots"])
    dc = rcpt["deleting_commit"]
    before = _Tree(ctx.repo_root, f"rev:{dc}^")
    mf = _module_file(before, modname)
    if mf is None or not (mf.startswith(roots) or mf in roots) or not _module_defines(before.read(mf), sym):
        errs.append("deleted_symbol 未於 deleting_commit^ 之 production_roots 模組層定義")
    for rev in (dc, rcpt["head"]):
        tr = _Tree(ctx.repo_root, f"rev:{rev}")
        mf2 = _module_file(tr, modname)
        if mf2 is not None and _module_defines(tr.read(mf2), sym):
            errs.append(f"deleted_symbol 於 {rev[:8]} 仍定義")
    if not _is_ancestor(ctx.repo_root, dc, rcpt["head"]):
        errs.append("deleting_commit 非 head 之祖先")
    scan = [tpath] + [f for f in head_tree.files() if f.startswith("tests/") and f.endswith(".py")
                      and (f.endswith("conftest.py") or "/fixtures/" in f)]
    for f in scan:
        s2 = head_tree.read(f)
        if s2 is None:
            continue
        for n in ast.walk(ast.parse(s2)):
            if isinstance(n, ast.Attribute) and n.attr == sym and isinstance(n.ctx, (ast.Store, ast.Del)):
                errs.append(f"{f} 寫入或刪除 {sym} 屬性")
            if isinstance(n, ast.Call) and _last_name(n.func) in ("setattr", "delattr") and len(n.args) >= 2 \
                    and isinstance(n.args[1], ast.Constant) and n.args[1].value == sym:
                errs.append(f"{f} 以 setattr／delattr 操作 {sym}")
            if isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store) and isinstance(n.value, ast.Attribute) \
                    and n.value.attr == "modules":
                errs.append(f"{f} 寫入 sys.modules")
    return errs


def _check_e1(ctx: Context, tomb: Mapping[str, Any], rcpt: Mapping[str, Any], rel: str) -> List[str]:
    errs = validate_shape(rcpt, {"type": "types.receipt_E1"}, ctx.schema)
    if errs:
        return errs
    if rcpt["nodeid"] != tomb["nodeid"]:
        errs.append("收據 nodeid 與碑不符")
    hp = _receipt_head_problem(ctx, rel, rcpt["head"])
    if hp:
        errs.append(hp)
    if rcpt["replacement_nodeid"] not in tomb.get("replaced_by", []):
        errs.append("replacement 不在 replaced_by")
    tgt = _e1_parts(_engine_for(ctx, f"rev:{rcpt['head']}"), rcpt["nodeid"])
    rep = _e1_parts(_engine_for(ctx, ctx.tree), rcpt["replacement_nodeid"])
    if tgt is None or rep is None:
        return errs + ["target 或 replacement 函式不存在"]
    if not (tgt["ast"] == rep["ast"] == rcpt["target_ast_sha256"] == rcpt["replacement_ast_sha256"]):
        errs.append("函式 AST 非完全相同或與收據不符")
    if not (tgt["fixture_closure"] == rep["fixture_closure"] == rcpt["fixture_closure_sha256"]):
        errs.append("fixture 閉包不同或與收據不符")
    if not (tgt["module_context"] == rep["module_context"] == rcpt["module_context_sha256"]):
        errs.append("模組情境不同或與收據不符")
    return errs


def rule_v08(ctx: Context) -> List[Finding]:
    """V08。"""
    out = []
    for tb in _tombs(ctx):
        if not _scoped(ctx, str(tb.get("nodeid", "")).split("::")[0]) and ctx.scope_paths is not None:
            continue
        rel = tb.get("evidence_receipt")
        rcpt, err = _load_receipt(ctx, rel)
        if err:
            out.append(Finding("V08", str(tb.get("nodeid")), err))
            continue
        lvl = tb.get("evidence_level")
        if lvl == "E0":
            errs = _check_e0(ctx, tb, rcpt, rel)
        elif lvl == "E1":
            errs = _check_e1(ctx, tb, rcpt, rel)
        else:
            errs = _check_mutation(ctx, rcpt, rel, tb.get("nodeid"), tb.get("replaced_by", []))
        out.extend(Finding("V08", str(tb.get("nodeid")), e, unverifiable="unverifiable" in e) for e in errs)
    return out


def rule_v09(ctx: Context) -> List[Finding]:
    """V09。"""
    out, t = [], _tree(ctx)
    for tb in _tombs(ctx):
        lvl, rb = tb.get("evidence_level"), tb.get("replaced_by") or []
        if lvl == "E0" and rb:
            out.append(Finding("V09", str(tb.get("nodeid")), "E0 之 replaced_by 須為空"))
        if lvl in ("E1", "E2"):
            if not rb:
                out.append(Finding("V09", str(tb.get("nodeid")), "E1／E2 之 replaced_by 不得為空"))
            for r in rb:
                if r not in _function_nodeids(t, r.split("::")[0]):
                    out.append(Finding("V09", str(tb.get("nodeid")), f"replaced_by {r} 於受驗之樹不存在"))
    return out


def rule_v10(ctx: Context) -> List[Finding]:
    """V10。"""
    t = _tree(ctx)
    return [Finding("V10", tb["nodeid"], "碑之函式仍存在") for tb in _tombs(ctx)
            if isinstance(tb.get("nodeid"), str) and tb["nodeid"] in _function_nodeids(t, tb["nodeid"].split("::")[0])]


def rule_v11(ctx: Context) -> List[Finding]:
    """V11。"""
    out, today = [], _today()
    for p, e in sorted(_entries(ctx).items()):
        if _scoped(ctx, p) and isinstance(e, dict):
            for q in e.get("quarantine") or []:
                if isinstance(q, dict) and isinstance(q.get("expires"), str) and q["expires"] < today:
                    out.append(Finding("V11", p, f"quarantine {q.get('nodeid')} 已逾期（{q['expires']}）"))
    return out


def rule_v12(ctx: Context) -> List[Finding]:
    """V12。"""
    out = []
    for p, e in sorted(_entries(ctx).items()):
        if not _scoped(ctx, p) or not isinstance(e, dict):
            continue
        for q in e.get("quarantine") or []:
            if not isinstance(q, dict):
                continue
            ev = [x for x in q.get("evidence") or [] if isinstance(x, dict)]
            fps, outcomes = set(), set()
            for x in ev:
                if re.sub(r"\[.*\]$", "", str(x.get("nodeid"))) != q.get("nodeid"):
                    out.append(Finding("V12", p, f"evidence 引用他 nodeid {x.get('nodeid')}"))
                    continue
                s = _ledger_session(ctx, str(x.get("session_id")))
                if s is None:
                    out.append(Finding("V12", p, f"evidence session {x.get('session_id')} 不在 ledger", unverifiable=True))
                    continue
                rec = s["tests"].get(x.get("nodeid"))
                if rec is None:
                    out.append(Finding("V12", p, "evidence 紀錄不存在"))
                    continue
                fps.add((s["session"] or {}).get("fingerprint"))
                outcomes.add(rec["outcome"])
            if len(fps) > 1:
                out.append(Finding("V12", p, "evidence 之 fingerprint 不同"))
            if ev and not ({"passed"} <= outcomes and outcomes & {"failed", "error"}):
                out.append(Finding("V12", p, "evidence 未含同 fingerprint 之 passed 與 failed／error"))
    return out


def rule_v13(ctx: Context) -> List[Finding]:
    """V13。"""
    want = set(ctx.schema["catalog"]["top_level_keys"])
    have = set(ctx.catalog) if isinstance(ctx.catalog, dict) else set()
    return [] if have == want else [Finding("V13", CATALOG_REL, f"頂層鍵 {sorted(have)} ≠ {sorted(want)}")]


def _manifests(tree: "_Tree") -> Dict[str, Dict[str, Any]]:
    out = {}
    mf = [f for f in tree.files() if re.fullmatch(r"docs/manifests/[^/]+\.json", f)]
    tree.prefetch(mf)
    for f in mf:
        if True:
            try:
                out[f] = json.loads(tree.read(f) or "")
            except ValueError:
                continue
    return out


def _walk_strings(obj: Any, key: Optional[str] = None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v, key)
    elif isinstance(obj, str):
        yield key, obj


def manifest_selection_strings(manifest: Mapping[str, Any], schema: Mapping[str, Any]) -> List[str]:
    """schema `manifest_selection_keys`：keys 所列鍵下之全部字串（gate_cmd 取 shlex token）＋ prefixed_strings 所定之列
    中之 token；其他欄位之字串不計。"""
    keys = set(schema["manifest_selection_keys"]["keys"])
    out: List[str] = []
    for k, s in _walk_strings(manifest):
        if k == "gate_cmd":
            try:
                out += shlex.split(s)
            except ValueError:
                out += s.split()
        elif k in keys:
            out.append(s)
        toks = s.split()
        if toks and toks[0] in ("affected_tests", "affected_must", "affected_groups"):
            out += [t.split("=", 1)[1] if "=" in t else t for t in toks[1:]]
    return out


def manifest_closed(repo_root: Path, manifest: Mapping[str, Any]) -> bool:
    """schema `manifest_status.manifest_closed`。"""
    try:
        fk = json.loads((Path(repo_root) / "scripts/fact_keys.json").read_text(encoding="utf-8"))
        blk = fk["handoff-pending"]
        ip, ist = blk["columns"].index("權威路徑"), blk["columns"].index("狀態")
    except (OSError, ValueError, KeyError):
        return False
    return any(r[ip] == manifest.get("spec_path") and r[ist] == "已完成" for r in blk.get("rows", []))


def manifest_tombstone_aware(manifest: Mapping[str, Any], schema: Mapping[str, Any]) -> bool:
    """schema `manifest_status.manifest_tombstone_aware`（含 gate_cmd_allowed_env／gate_cmd_allowed_options／gate_cmd_parse）。"""
    ms = schema["manifest_status"]
    cmds = [s for k, s in _walk_strings(manifest) if k == "gate_cmd"]
    if not cmds:
        return False
    for cmd in cmds:
        try:
            toks = shlex.split(cmd)
        except ValueError:
            return False
        if any(not re.fullmatch(r"[A-Za-z0-9_./=:,+-]+", t) for t in toks):
            return False
        while toks and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", toks[0]):
            if toks[0] not in ms["gate_cmd_allowed_env"]:
                return False
            toks = toks[1:]
        if len(toks) < 2 or toks[0] not in ("venv/bin/python", "python", "python3") or \
                toks[1] != "scripts/framepath_affected_gate.py":
            return False
        rest, seen, opts = toks[2:], collections.Counter(), ms["gate_cmd_allowed_options"]
        i = 0
        while i < len(rest):
            o = rest[i]
            if o not in opts or i + 1 >= len(rest) or rest[i + 1].startswith("-"):
                return False
            seen[o] += 1
            if not opts[o]["repeat"] and seen[o] > 1:
                return False
            i += 2
    return True


def _hits(manifest: Mapping[str, Any], schema: Mapping[str, Any], nodeid: str) -> bool:
    path = nodeid.split("::")[0]
    for tok in manifest_selection_strings(manifest, schema):
        base = re.sub(r"\[.*\]$", "", tok)
        if base == nodeid or base == path or base.split("::")[0] == path:
            return True
    return False


def _unsafe(ctx: Context, manifest: Mapping[str, Any]) -> bool:
    return not (manifest_closed(ctx.repo_root, manifest) or manifest_tombstone_aware(manifest, ctx.schema))


def rule_v14(ctx: Context) -> List[Finding]:
    """V14。"""
    head = {t.get("nodeid"): t for t in (ctx.head_catalog or {}).get("tombstones", []) if isinstance(t, dict)}
    mans = _manifests(_tree(ctx))
    out = []
    for tb in _tombs(ctx):
        nid = tb.get("nodeid")
        if not isinstance(nid, str) or head.get(nid) == tb:
            continue
        for mp, m in sorted(mans.items()):
            if _hits(m, ctx.schema, nid) and _unsafe(ctx, m):
                out.append(Finding("V14", nid, f"出現在未收案且閘不解析碑之 manifest {mp}"))
    return out


def rule_v15(ctx: Context) -> List[Finding]:
    """V15。"""
    out, t = [], _tree(ctx)
    for p, e in sorted(_entries(ctx).items()):
        if _scoped(ctx, p) and isinstance(e, dict) and e.get("rewrite_targets"):
            fns = set(_function_nodeids(t, p))
            for n in e.get("rewrite_targets") or []:
                if str(n).split("::")[0] != p or re.sub(r"\[.*\]$", "", str(n)) not in fns:
                    out.append(Finding("V15", p, f"rewrite_targets {n} 不屬本檔或函式不存在"))
    return out


def rule_v16(ctx: Context) -> List[Finding]:
    """V16。"""
    out = []
    boot = set((_tree(ctx).read(ctx.schema["bootstrap"]["paths_file"]) or "").splitlines())
    head = (ctx.head_catalog or {}).get("entries", {})
    for p, e in sorted(_entries(ctx).items()):
        if not _scoped(ctx, p) or not isinstance(e, dict):
            continue
        for col in ("guarantee", "oracle", "claim"):
            v = e.get(col)
            if isinstance(v, list) and "unclassified" in v:
                if v != ["unclassified"]:
                    out.append(Finding("V16", p, f"{col} 混用 unclassified"))
                if p not in boot:
                    out.append(Finding("V16", p, f"{col} 為 unclassified 而路徑不在 bootstrap 清單"))
                hv = head.get(p, {}).get(col)
                if isinstance(hv, list) and any(x != "unclassified" for x in hv):
                    out.append(Finding("V16", p, f"{col} 由已分類改回 unclassified"))
    return out


def _catalog_spec(schema: Mapping[str, Any]) -> Dict[str, Any]:
    cs = schema["catalog"]
    return {"type": "object", "additional_properties": False, "fields": {
        "entries": {"type": "map", "key_format": "test_path", "required": True,
                    "values": {"type": "object", "additional_properties": False, "fields": cs["entries"]["fields"]}},
        "tombstones": {"type": "array", "items": "catalog.tombstones", "required": True}}}


def rule_v17(ctx: Context) -> List[Finding]:
    """V17（以 `validate_shape` 對 catalog 全樹與 ledger 紀錄驗形）。"""
    cat = ctx.catalog
    if ctx.scope_paths is not None and isinstance(cat, dict):
        cat = dict(cat, entries={k: v for k, v in _entries(ctx).items() if k in ctx.scope_paths})
    return [Finding("V17", CATALOG_REL, e) for e in validate_shape(cat, _catalog_spec(ctx.schema), ctx.schema, "catalog")]


def rule_v18(ctx: Context) -> List[Finding]:
    """V18。"""
    pf = ctx.schema["bootstrap"]["paths_file"]
    h = ctx.extra["head_obj"].read(pf)
    return [] if h is None or h == _tree(ctx).read(pf) else [Finding("V18", pf, "bootstrap 清單與 HEAD 不同（不可變）")]


def _rewrite_ok(ctx: Context, nodeid: str) -> bool:
    e = _entries(ctx).get(nodeid.split("::")[0])
    if not isinstance(e, dict) or e.get("disposition") != "rewrite" or not e.get("rewrite_receipt"):
        return False
    return nodeid in _covered(ctx, e) and not _rewrite_receipt_errors(ctx, e)


def helper_callers(repo_root: Path, helper_path: str, tree: str = "worktree") -> List[str]:
    """tests/ 下非測試檔（conftest、fixtures、helper 模組）變更時，依 `assertion_nodes.inline_rule` 受影響之全部呼叫者
    測試函式（函式層 nodeid，排序）。"""
    t = _Tree(Path(repo_root), tree)
    schema = load_schema(Path(repo_root))
    eng = _Engine(t)
    if helper_path.endswith("conftest.py"):
        base = helper_path[: -len("conftest.py")]
        cands = [f for f in t.test_files(schema) if f.startswith(base)]
    else:
        files = set(t.files())

        def deps(path: str) -> set:
            try:
                tree_ = ast.parse(t.read(path) or "")
            except SyntaxError:
                return set()
            mods = set()
            for n in ast.walk(tree_):
                if isinstance(n, ast.Import):
                    mods |= {a.name for a in n.names}
                elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
                    mods.add(n.module)
                    mods |= {f"{n.module}.{a.name}" for a in n.names}
            out_ = set()
            for m in mods:
                base_ = m.replace(".", "/")
                out_ |= {p for p in (base_ + ".py", base_ + "/__init__.py") if p in files}
            return out_

        cands = []
        for f in t.test_files(schema):
            d_ = f.rsplit("/", 1)[0]
            chain = []
            while d_:
                chain.append(d_ + "/conftest.py")
                d_ = d_.rsplit("/", 1)[0] if "/" in d_ else ""
            starts = [c for c in chain + ["conftest.py"] if c in files]
            seen, todo = set(), [f, *starts, *[pl for c in starts for pl in _plugin_paths(t, c)]]
            while todo:
                cur = todo.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                todo += [d for d in deps(cur) if d.startswith("tests/")]
            if helper_path in seen:
                cands.append(f)
    out = []
    for f in cands:
        for nid in _function_nodeids(t, f):
            eng.touched = set()
            eng.elements(nid)
            if helper_path in eng.touched:
                out.append(nid)
    return sorted(out)


def _def_profiles(eng: "_Engine", path: str, only: Optional[set] = None) -> Optional[Dict[str, "collections.Counter[str]"]]:
    """helper 檔每一頂層定義之自身斷言輪廓（本體元素＋預設值＋常數值）；非定義之頂層敘述以 "__module__" 輪廓表示。"""
    mi = eng.mod(path)
    if mi is None:
        return None
    out: Dict[str, collections.Counter] = {}
    for name, fn in mi.defs.items():
        if only is not None and name not in only:
            continue
        kind = "fixture" if name in mi.fixtures else "helper"
        keys = collections.Counter(e["key"] for e in eng.normalize(fn, eng.collect(mi, fn, kind, frozenset({(path, name)}))))
        for d in [*fn.args.defaults, *(x for x in fn.args.kw_defaults if x is not None)]:
            keys["default:" + ast.dump(eng.fold(mi, d, {}, {}))] += 1
        if name in mi.fixtures and mi.fixtures[name][1]:
            keys["fixture:autouse"] += 1
        out[name] = keys
    for name, v in mi.consts.items():
        out[name] = collections.Counter({"const:" + ast.dump(v): 1})
    for n in mi.tree.body:  # 匯入名：解析目標（他模組 `from 本模組 import 名` 之使用者經此反推）
        if isinstance(n, ast.ImportFrom) and n.module and not n.level:
            for a in n.names:
                out.setdefault(a.asname or a.name, collections.Counter())[f"import:{n.module}.{a.name}"] += 1
        elif isinstance(n, ast.Import):
            for a in n.names:
                out.setdefault(a.asname or a.name.split(".")[0], collections.Counter())[f"import:{a.name}"] += 1
    return out


def _decreased_defs(he: "_Engine", ce: "_Engine", path: str) -> Optional[set]:
    """差量：模組層名稱之完整展開輪廓（定義內聯展開、預設值與常數摺疊、匯入名之解析目標）減少者；不可解析 ⇒ None。"""
    cand = _changed_names(he.tree.read(path), ce.tree.read(path))
    if cand is None:
        return None
    if not cand:
        return set()  # 模組層敘述語法樹皆未變 ⇒ 本檔無名稱可減（他檔之改動由其自身路由反推）
    hp, cp = _def_profiles(he, path, cand), _def_profiles(ce, path, cand)
    if hp is None or cp is None:
        return None
    return {n for n in hp if n in cand and multiset_decreased(hp[n], cp.get(n, collections.Counter()))}


_SKIP_MARKS = {"skip", "skipif", "xfail"}


def _skip_like(tree: "_Tree", nodeid: str) -> bool:
    """該測試函式是否帶 skip／skipif／xfail（函式或類別裝飾器、模組 pytestmark）或本體頂層呼叫 pytest.skip／xfail。"""
    path, qual = _split_nodeid(nodeid)
    try:
        mod = _parse(tree.read(path) or "")
    except SyntaxError:
        return False

    def has_mark(nodes) -> bool:
        for d in nodes:
            for x in ast.walk(d):
                if isinstance(x, ast.Attribute) and x.attr in _SKIP_MARKS and isinstance(x.value, ast.Attribute) \
                        and x.value.attr == "mark":
                    return True
        return False
    for s in mod.body:
        if isinstance(s, ast.Assign) and any(isinstance(t_, ast.Name) and t_.id == "pytestmark" for t_ in s.targets) \
                and has_mark([s.value]):
            return True
    cls, _, fname = qual.rpartition("::")
    for s in mod.body:
        if cls and isinstance(s, ast.ClassDef) and s.name == cls:
            if has_mark(s.decorator_list):
                return True
            body = s.body
        elif not cls:
            body = [s]
        else:
            continue
        for fn in body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == fname:
                if has_mark(fn.decorator_list):
                    return True
                for st in fn.body:
                    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute) \
                            and st.value.func.attr in ("skip", "xfail") and getattr(st.value.func.value, "id", "") == "pytest":
                        return True
    return False


def _affected_tests(hsrc: Optional[str], csrc: Optional[str], path: str, common: set, dec: set) -> set:
    """測試檔差量：本體（含裝飾器、所在類別）語法樹有變者 ∪ 本體引用或以 fixture 參數請求 dec（經模組內遞移擴張）者；
    dec 含 autouse fixture、或模組層 pytestmark 有變 ⇒ 全檔。"""
    def parse(src):
        try:
            return _parse(src or "")
        except SyntaxError:
            return None
    hm, cm = parse(hsrc), parse(csrc)
    if hm is None or cm is None:
        return set(common)
    def pm(m):
        return [ast.dump(s) for s in m.body if isinstance(s, ast.Assign)
                and any(isinstance(x, ast.Name) and x.id == "pytestmark" for x in s.targets)]
    if pm(hm) != pm(cm):
        return set(common)
    def units(m):
        out = {}
        for s in m.body:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[s.name] = (ast.dump(s), s)
            elif isinstance(s, ast.ClassDef):
                for x in s.body:
                    if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out[f"{s.name}::{x.name}"] = (ast.dump(s.decorator_list and ast.Tuple(s.decorator_list, ast.Load()) or ast.Pass()) + ast.dump(x), x)
        return out
    hu, cu = units(hm), units(cm)
    out = {n for n in common if hu.get(n.split("::", 1)[1], ("",))[0] != cu.get(n.split("::", 1)[1], ("",))[0]}
    if not dec:
        return out
    def deps(fn):
        loads = {x.id for x in ast.walk(fn) if isinstance(x, ast.Name)}
        return loads | {a.arg for a in fn.args.args}
    auto = set()
    for m in (hm, cm):
        for s in m.body:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and any("autouse" in ast.dump(d) for d in s.decorator_list):
                auto.add(s.name)
    s_ = set(dec)
    grow = True
    while grow:
        grow = False
        for m in (hm, cm):
            for s in m.body:
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and s.name not in s_ and deps(s) & s_:
                    s_.add(s.name)
                    grow = True
    if s_ & auto:
        return set(common)
    for n in common:
        q = n.split("::", 1)[1]
        for u in (hu, cu):
            if q in u and deps(u[q][1]) & s_:
                out.add(n)
    return out


def _changed_names(hsrc: Optional[str], csrc: Optional[str]) -> Optional[set]:
    """模組層名稱中，其綁定敘述之語法樹於兩版不同、或（模組內遞移）引用此等名稱者；不可解析 ⇒ None。"""
    def binds(src: Optional[str]):
        try:
            mod = _parse(src or "")
        except SyntaxError:
            return None
        out: Dict[str, List[str]] = {}
        refs: Dict[str, set] = {}
        for st in mod.body:
            names = set()
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(st.name)
            elif isinstance(st, (ast.Import, ast.ImportFrom)):
                names |= {a.asname or a.name.split(".")[0] for a in st.names}
            else:
                names |= {n.id for n in ast.walk(st) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            d = ast.dump(st)
            loads = {n.id for n in ast.walk(st) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            for nm in names:
                out.setdefault(nm, []).append(d)
                refs.setdefault(nm, set()).update(loads)
        return out, refs
    h, c = binds(hsrc), binds(csrc)
    if h is None or c is None:
        return None
    changed = {n for n in set(h[0]) | set(c[0]) if h[0].get(n) != c[0].get(n)}
    grow = True
    while grow:
        grow = False
        for n, ls in list(h[1].items()) + list(c[1].items()):
            if n not in changed and ls & changed:
                changed.add(n)
                grow = True
    return changed


def decreased_defs(repo_root: Path, helper_path: str, tree: str = "worktree") -> Optional[List[str]]:
    """具名縫：HEAD 與受驗之樹間自身斷言輪廓減少之定義名（排序）；模組層非定義敘述改變 ⇒ None。"""
    he, ce = _shared_engine(Path(repo_root), "HEAD"), _shared_engine(Path(repo_root), tree)
    d = _decreased_defs(he, ce, helper_path)
    return None if d is None else sorted(d)


def _fixture_dependents(ctx: Context, eng: "_Engine", conftest: str, dec: set) -> set:
    """conftest 中自身輪廓減少之 fixture 集合 dec ⇒ 其作用範圍內直接或經 fixture 傳遞使用者之測試函式（含 autouse）。"""
    base = conftest[: -len("conftest.py")]
    names = set(dec)
    files = [f for f in _tree(ctx).test_files(ctx.schema) if f.startswith(base)]
    conftests = [f for f in _tree(ctx).files() if f.startswith(base) and f.endswith("conftest.py")]
    changed = True
    while changed:
        changed = False
        for f in [*conftests, *files]:
            m = eng.mod(f)
            for fname, (ffn, _) in (m.fixtures.items() if m else []):
                if fname not in names and {a.arg for a in ffn.args.args} & names:
                    names.add(fname)
                    changed = True
    autouse = any(auto for c in conftests for n, (_, auto) in ((eng.mod(c).fixtures.items()) if eng.mod(c) else [])
                  if n in names)
    out = set()
    for f in files:
        for q, fn in _test_functions(_tree(ctx).read(f)).items():
            params = {a.arg for a in fn.args.args}
            if autouse or params & names:
                out.add(f"{f}::{q}")
    return out


def rule_v19(ctx: Context) -> List[Finding]:
    """V19（以 `assertion_multiset` 與 `multiset_decreased` 判定）。"""
    pat = ctx.schema["formats"]["test_path"]
    t, head = _tree(ctx), ctx.extra["head_obj"]
    files, helpers = set(), set(ctx.extra.get("helper_paths", []))
    for p in ctx.extra["changed"]:
        if p.startswith("tests/") and p.endswith(".py"):
            (files if re.fullmatch(pat, p) else helpers).add(p)
    if ctx.scope_paths is not None:
        files &= set(ctx.scope_paths)
        helpers &= set(ctx.extra.get("helper_paths", []))
    nids = set()
    for f in files:
        common = set(_function_nodeids(head, f)) & set(_function_nodeids(t, f))
        dec = _seam("decreased_defs")(ctx.repo_root, f, tree=ctx.tree)
        if dec is None:
            nids |= common
            continue
        nids |= _affected_tests(head.read(f), t.read(f), f, common, {d for d in dec if not d.startswith("test")})
    callers = _seam("helper_callers")
    he, ce = _engine_for(ctx, "HEAD"), _engine_for(ctx, ctx.tree)
    for h in helpers:
        dec = _seam("decreased_defs")(ctx.repo_root, h, tree=ctx.tree)
        dec = None if dec is None else set(dec)
        if dec is not None and not dec:
            continue  # 差量：本檔無任何定義之自身斷言輪廓減少 ⇒ 不可能有呼叫者減少
        if h.endswith("conftest.py") and dec is not None and dec <= set((ce.mod(h) or he.mod(h)).fixtures if (ce.mod(h) or he.mod(h)) else []):
            nids |= _fixture_dependents(ctx, ce, h, dec) | _fixture_dependents(ctx, he, h, dec)
            continue
        nids |= set(callers(ctx.repo_root, h, tree=ctx.tree)) | set(callers(ctx.repo_root, h, tree="HEAD"))
    tombs, out = _tomb_ids(ctx), []
    for nid in sorted(nids):
        if nid not in _function_nodeids(t, nid.split("::")[0]):
            continue
        old = collections.Counter(e["key"] for e in he.elements(nid))
        new = collections.Counter(e["key"] for e in ce.elements(nid))
        if _skip_like(t, nid) and not _skip_like(head, nid):
            new = collections.Counter()  # 新增 skip／skipif／xfail（函式、類別、模組 pytestmark、本體 pytest.skip／xfail）⇒ 視為空
        dec = _seam("multiset_decreased")(old, new)
        if dec and nid not in tombs and not _rewrite_ok(ctx, nid):
            out.append(Finding("V19", nid, f"斷言多重集合減少 {len(dec)} 項（須同提交立碑或附 rewrite 收據）"))
    return out


def rule_v20(ctx: Context) -> List[Finding]:
    """V20。"""
    pat = ctx.schema["formats"]["test_path"]
    t, head, tombs = _tree(ctx), ctx.extra["head_obj"], _tomb_ids(ctx)
    out = []
    files = {p for p in ctx.extra["changed"] if re.fullmatch(pat, p) and _scoped(ctx, p)}
    if "pytest.ini" in ctx.extra["changed"] and _scoped(ctx, "pytest.ini"):
        hp_, tp_ = _collect_patterns(head), _collect_patterns(t)
        if any(set(a) - set(b) for a, b in zip(hp_, tp_)):  # 四項皆只增（超集）⇒ 不可能少收，不檢
            allf = [p for p in head.files() if re.fullmatch(pat, p)]
            head.prefetch(allf)
            t.prefetch(allf)
            files |= set(allf)
    for p in sorted(files):
        gone = set(_function_nodeids(head, p)) - set(_function_nodeids(t, p))
        out += [Finding("V20", n, "測試函式刪除或改名而未立碑") for n in sorted(gone) if n not in tombs]
    return out


def rule_v21(ctx: Context) -> List[Finding]:
    """V21（只於 require_executed=True）。"""
    if not ctx.require_executed:
        return []
    out = []
    for p, e in sorted(_entries(ctx).items()):
        if isinstance(e, dict) and e.get("disposition") == "rewrite":
            if not e.get("rewrite_receipt"):
                out.append(Finding("V21", p, "rewrite 未執行（rewrite_receipt 為 null）"))
            else:
                out += [Finding("V21", p, err) for err in _rewrite_receipt_errors(ctx, e)]
    return out


def rule_v22(ctx: Context) -> List[Finding]:
    """V22。"""
    t, head = _tree(ctx), ctx.extra["head_obj"]
    only = ctx.extra.get("only_manifest")
    out = []
    for mp, m in sorted(_manifests(t).items()):
        if only and mp != only:
            continue
        if head.read(mp) == t.read(mp):
            continue
        for tb in _tombs(ctx):
            nid = tb.get("nodeid")
            if isinstance(nid, str) and _hits(m, ctx.schema, nid) and _unsafe(ctx, m):
                out.append(Finding("V22", mp, f"變更之 manifest（未收案且閘不解析碑）含既有碑 {nid}"))
    return out

# ── Task 1.2：bootstrap ──────────────────────────────────────────────────────────────────────────────


def ticket_of(repo_root: Path, path: str) -> str:
    """schema `bootstrap.ticket_rule`：以 `git log --follow --diff-filter=A` 取最早加入之提交導出票代號；導不出 ⇒ unknown。"""
    root = Path(repo_root)
    shas = _git_out(root, "log", "--follow", "--diff-filter=A", "--format=%H", "--", path).split()
    if not shas:
        return "unknown"
    sha = shas[-1]
    trailers = _git_out(root, "show", "-s", "--format=%(trailers:key=Ticket-Batch,valueonly)", sha).split()
    for tr in trailers:
        m = re.fullmatch(r"(.+)/b\d+", tr.strip())
        if m:
            return re.sub(r"^\d{8}-", "", m.group(1))
    subj = _git_out(root, "show", "-s", "--format=%s", sha).strip()
    m = re.match(r"^[a-z]+\(([A-Za-z0-9-]+)\):", subj)
    return m.group(1).upper() if m else "unknown"


def _dump_catalog(cat: Mapping[str, Any]) -> str:
    return json.dumps(cat, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def bootstrap(repo_root: Path, receipt: Optional[Path] = None) -> Dict[str, Any]:
    """寫 catalog（全部 git 追蹤之測試檔一筆 entry，其餘欄依 `bootstrap.defaults`）與 `bootstrap.paths_file`；冪等。
    回傳 {"entries": int, "unknown": int}；receipt 非 None 時另寫該 JSON（含 unknown 筆數與路徑清單）。"""
    root = Path(repo_root)
    schema = load_schema(root)
    pat = schema["formats"]["test_path"]
    tracked = sorted(p for p in _git_out(root, "ls-files", "-z").split("\0") if p and re.fullmatch(pat, p))
    cpath = root / CATALOG_REL
    cat = json.loads(cpath.read_text(encoding="utf-8")) if cpath.is_file() else {"entries": {}, "tombstones": []}
    ticket = _seam("ticket_of")
    defaults = schema["bootstrap"]["defaults"]
    for p in tracked:
        if p not in cat["entries"]:
            cat["entries"][p] = {"path": p, "ticket": ticket(root, p), **json.loads(json.dumps(defaults))}
    cpath.parent.mkdir(parents=True, exist_ok=True)
    cpath.write_text(_dump_catalog(cat), encoding="utf-8")
    pf = root / schema["bootstrap"]["paths_file"]
    if not pf.is_file():
        pf.write_text("".join(p + "\n" for p in tracked), encoding="utf-8")
    unknown = sorted(p for p in tracked if cat["entries"][p].get("ticket") == "unknown")
    res = {"entries": len(tracked), "unknown": len(unknown)}
    if receipt is not None:
        rp = Path(receipt) if Path(receipt).is_absolute() else root / receipt
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps({"schema_version": 1, "command": "scripts/testreg.py bootstrap", "exit_code": 0, **res,
                                  "unknown_paths": unknown}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return res


# ── Task 1.4：標記 ───────────────────────────────────────────────────────────────────────────────────

_BUILTIN_MARKS = frozenset({"parametrize", "skip", "skipif", "xfail", "usefixtures", "filterwarnings"})


def _ini_markers(root: Path) -> set:
    import configparser
    cp = configparser.ConfigParser(interpolation=None)
    try:
        cp.read_string((root / "pytest.ini").read_text(encoding="utf-8"))
        raw = cp["pytest"].get("markers", "")
    except (OSError, KeyError, configparser.Error):
        return set()
    return {re.split(r"[:(]", l.strip(), 1)[0].strip() for l in raw.splitlines() if l.strip()}


def _plugin_registered(root: Path, files: Sequence[str]) -> set:
    """conftest.py 與其 pytest_plugins 所列外掛中之 `config.addinivalue_line("markers", "<名>: …")` 字面。"""
    def module_file(dotted: str) -> Optional[str]:
        for cand in (dotted.replace(".", "/") + ".py", dotted.replace(".", "/") + "/__init__.py"):
            if (root / cand).is_file():
                return cand
        return None

    todo = [f for f in files if f.endswith("conftest.py")] + (["conftest.py"] if (root / "conftest.py").is_file() else [])
    seen, names = set(), set()
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        try:
            tree = ast.parse((root / f).read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in n.targets):
                vals = n.value.elts if isinstance(n.value, (ast.List, ast.Tuple)) else [n.value]
                for v in vals:
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        mf = module_file(v.value)
                        if mf:
                            todo.append(mf)
            if isinstance(n, ast.Call) and _last_name(n.func) == "addinivalue_line" and len(n.args) >= 2 \
                    and isinstance(n.args[0], ast.Constant) and n.args[0].value == "markers" \
                    and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str):
                names.add(re.split(r"[:(]", n.args[1].value, 1)[0].strip())
    return names


def unregistered_markers(repo_root: Path) -> List[Tuple[str, int, str]]:
    """AST 掃描 tests/ 下 `pytest.mark.<name>` 屬性存取（含清單形式 pytestmark；註解與字串不計），對照 pytest.ini
    註冊集合、tests/ 與 repo 根 conftest／外掛中 `config.addinivalue_line("markers", "<name>: …")` 字面註冊者與 pytest
    內建集合；回傳未註冊者 (路徑, 行號, 名稱)。"""
    root = Path(repo_root)
    files = sorted(p for p in _git_out(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
                   if p.startswith("tests/") and p.endswith(".py") and (root / p).is_file())
    reg = _ini_markers(root) | _plugin_registered(root, files) | _BUILTIN_MARKS
    out = []
    for f in files:
        try:
            tree = ast.parse((root / f).read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute) and n.value.attr == "mark" \
                    and isinstance(n.value.value, ast.Name) and n.value.value.id == "pytest" and n.attr not in reg:
                out.append((f, n.lineno, n.attr))
    return sorted(out)


# ── Task 1.5：產出端檢查 ─────────────────────────────────────────────────────────────────────────────

_ENTRY_RULES = ("V03", "V05", "V06", "V11", "V15", "V16", "V17")


def check(repo_root: Path, *, paths: Sequence[str] = (), manifest: Optional[str] = None,
          helpers: Sequence[str] = (), staged: bool = False) -> List[Finding]:
    """產出端檢查（SPEC Task 1.5 改法之規則子集）；只讀 catalog、schema、變更檔清單與其 AST，不呼叫 pytest、不讀 git 全史。"""
    root = Path(repo_root)
    out: List[Finding] = []
    if staged:
        ctx = build_context(root, "staged")
        for i in range(1, 23):
            if i != 21:
                out += _seam(f"rule_v{i:02d}")(ctx)
        return out
    if manifest:
        ctx = build_context(root, "worktree")
        ctx.extra["only_manifest"] = manifest
        return _seam("rule_v22")(ctx)
    if helpers:
        ctx = build_context(root, "worktree", scope_paths=[])
        ctx.extra["helper_paths"] = list(helpers)
        return _seam("rule_v19")(ctx)
    for p in paths:
        if p == "pytest.ini":
            out += _seam("rule_v20")(build_context(root, "worktree", scope_paths=[p]))
            continue
        if p == CATALOG_REL:
            ctx = build_context(root, "worktree")
            for rid in (*_ENTRY_RULES, "V13"):
                out += _seam(f"rule_{rid.lower()}")(ctx)
        else:
            ctx = build_context(root, "worktree", scope_paths=[p])
            for rid in ("V02", *_ENTRY_RULES, "V19", "V20"):
                out += _seam(f"rule_{rid.lower()}")(ctx)
    return out


# ── Task 2.1：複查訊號 ───────────────────────────────────────────────────────────────────────────────


def review(repo_root: Path) -> Dict[str, Dict[str, SignalValue]]:
    """逐 catalog entry 逐訊號：{path: {訊號名: True|False|"unknown"}}；訊號名依 schema `enums.review_signal`，
    每訊號以 `signal_<名>`（呼叫當下以模組屬性取用）判定；不寫回 catalog。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_prod_symbol_gone(ctx: Context, path: str) -> SignalValue:
    """測試檔 import 之生產符號於 HEAD AST 不存在。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_duration_regression(ctx: Context, path: str) -> SignalValue:
    """依 schema `derived.duration_regression_rule`；summary 不存在 ⇒ "unknown"。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_outcome_flip_same_fingerprint(ctx: Context, path: str) -> SignalValue:
    """summary 中同 fingerprint 不同 outcome；summary 不存在 ⇒ "unknown"。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_collect_error(ctx: Context, path: str) -> SignalValue:
    """最近一個收集過該檔之 session 有該檔之 ledger collect_record；ledger 不存在 ⇒ "unknown"。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_allowed_red_owner_closed(ctx: Context, path: str) -> SignalValue:
    """該檔之 allowed_red.json 列之 owner_ticket 於 scripts/fact_keys.json 已完成（查表規則見 SPEC Task 2.1）。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_quarantine_expired(ctx: Context, path: str) -> SignalValue:
    """該 entry 有 quarantine 之 expires 早於今日（V11 反例）。"""
    raise NotImplementedError("TESTREG Task 2.1")


# ── Task 2.2：impact ─────────────────────────────────────────────────────────────────────────────────


def impact(repo_root: Path, changed_paths: List[str], must_resolved: List[str],
           previously_failed: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """schema `impact`＋`gate_wiring` 之簽名：catalog、schema、AST 與測試檔集合一律自 repo_root 讀取；
    回傳 {"selected": [{"path", "reasons"}], "excluded": [{"path", "excluded_reason"}]}；schema `impact.precheck_rules`
    任一不符 ⇒ TestregError（不輸出；未登記之測試檔不拒跑而依 registry_unresolved 選入）；已立碑之檔依
    `impact.tombstoned_rule`；不存在使 selected 為空之分支。"""
    raise NotImplementedError("TESTREG Task 2.2")


def combine_sources(sources: Mapping[str, Iterable[str]]) -> Dict[str, List[str]]:
    """{select_reason: 檔集合} → {檔: 排序後之理由清單}（聯集）。"""
    raise NotImplementedError("TESTREG Task 2.2")


def domain_prefix(path: str) -> str:
    """schema `impact.domain_rule` 之 prefix(f)：f 所在目錄之前兩層目錄（層＝目錄層，不含檔名；不足兩層取一層；
    repo 根層之檔為空字串）。"""
    raise NotImplementedError("TESTREG Task 2.2")


def import_closure(repo_root: Path, test_path: str) -> FrozenSet[str]:
    """schema `impact.domain_rule` 之 import_closure(t)：repo 內模組之遞移閉包（含函式內 import、星號匯入、
    套件 __init__ 之 re-export），以 repo 相對 .py 路徑表示。"""
    raise NotImplementedError("TESTREG Task 2.2")


def shared_infra_scope(repo_root: Path, changed_path: str, tests: Iterable[str]) -> Optional[FrozenSet[str]]:
    """schema `impact.shared_test_infra`：changed_path 屬共用基礎設施 ⇒ 其作用範圍內之測試檔集合；否則 None。"""
    raise NotImplementedError("TESTREG Task 2.2")


def must_from_manifest(repo_root: Path, manifest: Mapping[str, Any], phase: int) -> List[str]:
    """CLI impact 用：manifest 須含 `affected_tests phase=<phase> ` 列（否則 TestregError）；回傳 `affected_must
    phase=<phase> ` 列之 nodeid 經碑解析（schema `impact.gate_feed` 第一步）後之結果。"""
    raise NotImplementedError("TESTREG Task 2.2")


# ── Task 3.2／4.2：子批閘（SPEC v17 C3）──────────────────────────────────────────────────────────────


def run_subbatch(repo_root: Path, manifest_path: str, phase: int, base: str, *, out: Path, receipt: Path,
                 max_seconds: float = 3600.0) -> int:
    """子批閘：changed_paths＝`git diff --name-only <base>` ∪ 相對 HEAD 之 diff ∪ 未追蹤檔（扣閘之 FP_EXCLUDES）；
    選測＝`impact`（must＝`must_from_manifest`；previously_failed 取自 summary）之 selected，整檔執行；執行器＝
    `framepath_affected_gate.Runner`（分段、`max_seconds` 用盡於呼叫之間停下回 3、同指紋沿用、progress.json）；非綠
    nodeid 於 base 之 detached worktree 重跑同 nodeid，以 `framepath_affected_gate.classify` 歸屬（模組屬性取用）；
    收據形狀＝schema `types.subbatch_receipt`，寫入前驗形並驗 `subbatch_gate` 所列欄間關係；回傳 0＝本子批造成＝0
    且無缺且無未完成檔、1＝否、3＝暫停（progress.json state＝paused）。"""
    raise NotImplementedError("TESTREG Task 3.2")


# ── Task 3.3／4.3：成效報告 ──────────────────────────────────────────────────────────────────────────


def effect_report(repo_root: Path, scope: Sequence[str] = ()) -> Dict[str, Any]:
    """由 catalog 碑與 summary 重算（形狀＝schema `types.effect_report`；欄位語意見 schema `effect_report`）：retired_functions（碑數）、retired_files（工作樹已不存在
    且其 entry 之函式皆有碑之檔數）、evidence_levels（各等級碑數）、saved_seconds_per_full_run（每一被淘汰函式層 nodeid
    之全部參數化 nodeid 於 summary 中 outcome=passed 紀錄之 duration_s 中位數之和；任一被淘汰 nodeid 無此紀錄 ⇒ 字面
    "unknown"，不寫 0、不外插）；scope 為碑 nodeid 之路徑前綴（空＝全部），記於報告 scope 欄。"""
    raise NotImplementedError("TESTREG Task 3.3")


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 入口；回傳結束碼（見模組說明）。"""
    ap = argparse.ArgumentParser(prog="testreg.py")
    ap.add_argument("--repo", default=str(REPO))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--require-executed", action="store_true")
    p = sub.add_parser("bootstrap")
    p.add_argument("--receipt")
    sub.add_parser("markers")
    p = sub.add_parser("check")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--paths", nargs="+")
    g.add_argument("--manifest")
    g.add_argument("--helpers", nargs="+")
    g.add_argument("--staged", action="store_true")
    sub.add_parser("review")
    p = sub.add_parser("impact")
    p.add_argument("--changed-from", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--phase", type=int, required=True)
    p = sub.add_parser("effect")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--out")
    g.add_argument("--recompute")
    p.add_argument("--scope", nargs="*", default=[])
    p = sub.add_parser("run")
    for a in ("--manifest", "--base", "--receipt"):
        p.add_argument(a, required=True)
    p.add_argument("--phase", type=int, required=True)
    p.add_argument("--out")
    p.add_argument("--max-seconds", type=float, default=3600.0)
    args = ap.parse_args(list(argv) if argv is not None else None)
    root = Path(args.repo).resolve()
    findings: List[Finding] = []
    try:
        if args.cmd == "validate":
            findings = _seam("validate")(root, require_executed=args.require_executed)
        elif args.cmd == "bootstrap":
            _seam("bootstrap")(root, Path(args.receipt) if args.receipt else None)
        elif args.cmd == "markers":
            findings = [Finding("MARKER", f"{p}:{ln}", f"未註冊之標記 {name}") for p, ln, name in _seam("unregistered_markers")(root)]
        elif args.cmd == "check":
            findings = _seam("check")(root, paths=args.paths or (), manifest=args.manifest, helpers=args.helpers or (),
                                      staged=args.staged)
        else:
            raise TestregError(f"USAGE {args.cmd}: 第 2 批以後實作")
    except TestregError as exc:
        sys.stderr.write(str(exc).splitlines()[0] + "\n")
        return 2
    for f in findings:
        sys.stderr.write(f.render() + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
