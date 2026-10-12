#!/usr/bin/env python3
"""testreg.py — TESTREG 測試清冊：契約驗證、bootstrap、標記、產出端檢查、複查訊號、受影響測試挑選、成效報告。

規格：docs/TESTREG_SPEC.md；契約單一真相源：tests/registry/testreg_schema.json（格式、枚舉、規則 V01–V22、挑選規則、
閘收據欄皆只讀該檔；本檔不存任何枚舉值副本——Task 1.1 驗收以字面計數機檢）。

TODO 凍結之介面（docs/manifests/TESTREG.json）：第 1 批實作 Phase 1（validate、bootstrap、markers、check）；Phase 2 起之
子命令（review、impact、run、effect）仍為簽章，函式體 `raise NotImplementedError("<Task>")`，由後續批次實作。簽章、具名縫
（供 tests/registry/ 之 mutation 置換者）與 CLI 契約不得於實作期更改；需改者回 TODO 重審。

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
import ast
import collections
import copy
import datetime as _dt
import functools
import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

REPO = Path(__file__).resolve().parents[1]
SCHEMA_REL = "tests/registry/testreg_schema.json"
CATALOG_REL = "tests/registry/catalog.json"
RULE_IDS: Tuple[str, ...] = tuple(f"V{i:02d}" for i in range(1, 23))

SignalValue = Union[bool, str]  # True／False／字面 "unknown"

_parse = functools.lru_cache(maxsize=512)(ast.parse)  # 唯讀用途之解析快取（呼叫端不得改寫回傳之樹）


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
    if src is None:
        return {}
    try:
        mod = _parse(src)
    except SyntaxError:
        return {}
    return _test_functions_of(mod, fpats, cpats)


def _test_functions_of(mod: ast.Module, fpats: Sequence[str] = ("test_*",),
                       cpats: Sequence[str] = ("Test*",)) -> Dict[str, ast.AST]:
    """`_test_functions` 之核心：已解析之模組 → {qualname: FunctionDef}（供已持有語法樹者免重解析）。"""
    out: Dict[str, ast.AST] = {}
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
    """conftest 之 `pytest_plugins` 字面所列模組之 repo 路徑（存在者）；依樹快取（`fixture_defs` 對每個測試檔之 conftest
    鏈逐一呼叫，未快取時真實規模每次 hook 重複解析 conftest 上千次）。"""
    cache = tree.__dict__.setdefault("_plugin_paths_cache", {})
    if conftest not in cache:
        cache[conftest] = _plugin_paths_uncached(tree, conftest)
    return list(cache[conftest])


def _plugin_paths_uncached(tree: "_Tree", conftest: str) -> List[str]:
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


def _is_usefixtures(x: ast.AST) -> bool:
    return isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == "usefixtures" \
        and isinstance(x.func.value, ast.Attribute) and x.func.value.attr == "mark"


def _usefixtures_in(nodes: Iterable[ast.AST]) -> List[str]:
    """裝飾器或 pytestmark 值中 usefixtures 標記之字串字面引數（依出現序；SPEC v35）。只認 pytest 實際套用者＝直接標記
    （裝飾器本身、pytestmark 值本身或其清單元素）；巢狀於其他標記之引數、本身作為參數值者不計（審查 r33 CODEX-R33-P2-02），
    掛在 `pytest.param(…, marks=…)` 者 pytest 8.4 收集時直接拒收（ValueError），亦不計（審查 r34 GROK-R34-P1-01）；
    非字串字面之引數無法靜態解析，不納入。"""
    out: List[str] = []
    for d in nodes:
        for x in (d.elts if isinstance(d, (ast.List, ast.Tuple)) else [d]):
            if _is_usefixtures(x):
                out.extend(a.value for a in x.args if isinstance(a, ast.Constant) and isinstance(a.value, str))
    return out


def _module_alias_at(eng: "_Engine", m: "_Mod", alias: str, before: Optional[int]) -> Optional[str]:
    """模組別名 → 其於 before 行之前最後一次綁定所指之 repo 內模組檔（`import a.b as h`、`import a`、`from a import b as h`
    而 b 為模組）；最後綁定為非匯入（本模組定義或賦值）或無法解析 ⇒ None（SPEC v39；審查 r38 CODEX-R38-P1-01：原以模組
    最終別名解析，別名於類別建立後重綁即取錯）。"""
    win: Optional[Tuple[Any, ...]] = None
    for ln, nm, info in m.order:
        if before is not None and ln >= before:
            break
        if nm == alias:
            win = info
    if win is None or win[0] != "import":
        return None
    kind, mod, attr = win[1]
    return eng.module_path(mod) if kind == "module" else eng.module_path(f"{mod}.{attr}")


def _base_names(eng: "_Engine", m: "_Mod", c: ast.ClassDef) -> set:
    """類別之基底名集合＝原始書寫名（名稱或屬性名）∪ 經 `_base_class` 還原之定義類別名（別名繼承、相對匯入；SPEC v35，
    審查 r34 CODEX-R34-P1-02）——供以類別名比對之預篩使用。"""
    out = {b.id if isinstance(b, ast.Name) else b.attr for b in c.bases if isinstance(b, (ast.Name, ast.Attribute))}
    for b in c.bases:
        hit = _base_class(eng, m, b)
        if hit is not None:
            out.add(hit[1].name)
    return out


def _base_class(eng: "_Engine", m: "_Mod", b: ast.AST) -> Optional[Tuple["_Mod", ast.ClassDef]]:
    """基底類別運算式 → (定義模組, ClassDef)，限 tests/ 下：名稱形式經本模組定義或 from-import 解析；模組屬性形式
    （`別名.類別`，別名綁定至 tests/ 下模組）經模組綁定解析（審查 r33 CODEX-R33-P1-01）。其他形式 ⇒ None。"""
    if isinstance(b, ast.Name):
        # v37：類別建立時之綁定；v38：取該綁定當時之類別節點（同名重定義不誤取後者；審查 r37 CODEX-R37-P1-01）
        r = eng.resolve_binding(m, b.id, {}, before=getattr(b, "lineno", None))
    elif isinstance(b, ast.Attribute) and isinstance(b.value, ast.Name):
        p = _module_alias_at(eng, m, b.value.id, getattr(b, "lineno", None))  # v39：別名取類別建立時之綁定
        m_ = eng.mod(p) if p else None
        r = eng.resolve_binding(m_, b.attr, {}) if m_ is not None else None  # 匯入之模組已執行完畢 ⇒ 其最終綁定
    else:
        r = None
    m2 = eng.mod(r[0]) if r and r[0].startswith("tests/") else None
    if m2 is None or not isinstance(r[2], ast.ClassDef):
        return None
    return m2, r[2]


def _pytestmark_values(body: Sequence[ast.stmt]) -> List[ast.AST]:
    return [s.value for s in body if isinstance(s, (ast.Assign, ast.AnnAssign)) and s.value is not None
            and any(isinstance(t, ast.Name) and t.id == "pytestmark"
                    for t in (s.targets if isinstance(s, ast.Assign) else [s.target]))]


def _requested_fixtures(eng: "_Engine", mi: "_Mod", qual: str, fn: ast.AST) -> List[str]:
    """測試函式所請求之 fixture 名（SPEC v33 契約 `assertion_nodes.inline_rule`）：參數（依序）＋ usefixtures 標記之字串
    字面——函式裝飾器、所在類別（含基底類別，遞移解析至 tests/ 外為止）之裝飾器與類別層 pytestmark、模組層 pytestmark。
    去重保序。"""
    names = [a.arg for a in [*getattr(fn.args, "posonlyargs", []), *fn.args.args, *fn.args.kwonlyargs]]
    names += _usefixtures_in(fn.decorator_list)
    if "::" in qual:
        cls = mi.classes.get(qual.split("::")[0])
        seen: set = set()

        def walk_cls(m: "_Mod", c: ast.ClassDef) -> None:
            key = (m.path, c.name)
            if key in seen:
                return
            seen.add(key)
            eng.touched.add(m.path)  # 基底類別所在模組屬此測試之依賴（helper_callers 據此反推）
            names.extend(_usefixtures_in(c.decorator_list))
            names.extend(_usefixtures_in(_pytestmark_values(c.body)))
            for b in c.bases:
                hit = _base_class(eng, m, b)
                if hit is not None:
                    walk_cls(*hit)

        if cls is not None:
            walk_cls(mi, cls)
    names += _usefixtures_in(_pytestmark_values(mi.tree.body))
    out: List[str] = []
    for n in names:
        if n not in out:
            out.append(n)
    return out


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


# (repo 相對路徑, 原始碼) → 解析結果：兩樹內容相同之檔共用一份（`_Mod` 只含由原始碼導出之唯讀資料，建立後不被改寫；
# 元素展開對語法樹節點一律先深複製）——HEAD 與受驗樹各解析全部測試檔時省一半解析（真實規模 autouse 判定實測）
_MOD_SHARED: Dict[Tuple[str, str], Optional["_Mod"]] = {}


class _Mod:
    def __init__(self, path: str, src: str):
        self.path = path
        self.tree = ast.parse(src)
        self.defs: Dict[str, ast.AST] = {}
        self.classes: Dict[str, ast.ClassDef] = {}
        self.fixtures: Dict[str, Tuple[ast.AST, bool]] = {}
        self.imports: Dict[str, Tuple[str, str, Optional[str]]] = {}
        self.stars: List[str] = []  # 模組層 `from M import *` 之 M（絕對模組名，依出現序；v36）
        # v37：模組層綁定敘述依出現序（行號, 名, 種類）——("local", 綁定當時之 def／class 節點或 None〔賦值〕；v38）／
        # ("import", 匯入登記)／("star", 模組)；名稱解析取最後一次
        # 綁定（Python 敘述順序語意；審查 r36 CODEX-R36-P1-01）。只看模組層敘述（if／try 區塊內之綁定不計，同既有）。
        self.order: List[Tuple[int, str, Tuple[Any, ...]]] = []
        self.assigns: Dict[str, List[ast.stmt]] = collections.defaultdict(list)
        for n in self.tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                isfx, auto = _fixture_info(n)
                if isfx:
                    self.fixtures[n.name] = (n, auto)
                self.defs[n.name] = n
                self.order.append((n.lineno, n.name, ("local", n)))
            elif isinstance(n, ast.ClassDef):
                self.classes[n.name] = n
                self.order.append((n.lineno, n.name, ("local", n)))
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                _note_imports(n, self.imports, path)
                one: Dict[str, Tuple[str, str, Optional[str]]] = {}
                _note_imports(n, one, path)
                self.order += [(n.lineno, k, ("import", v)) for k, v in one.items()]
                if isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names):
                    star = _from_module(n, path)
                    if star:
                        self.stars.append(star)
                        self.order.append((n.lineno, "*", ("star", star)))
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    for nm in ast.walk(t):
                        if isinstance(nm, ast.Name):
                            self.assigns[nm.id].append(n)
                            if isinstance(nm.ctx, ast.Store):
                                self.order.append((n.lineno, nm.id, ("local", None)))
        counts, rhs = _assign_counts(self.tree.body, deep=False)
        self.consts = {k: v for k, v in rhs.items() if counts.get(k) == 1 and _is_const_node(v)}


def _note_imports(n: ast.AST, out: Dict[str, Tuple[str, str, Optional[str]]], path: Optional[str] = None) -> None:
    """匯入敘述 → {本地名: ("module", 模組) | ("from", 模組, 名)}。相對匯入（`from .x import y`）依所在檔 path 還原為絕對
    模組名（SPEC v35；審查 r34 CODEX-R34-P1-01）；無 path 或層數超出 repo 根者不登記。"""
    if isinstance(n, ast.Import):
        for al in n.names:
            if al.asname:
                out[al.asname] = ("module", al.name, None)
            else:
                out[al.name.split(".")[0]] = ("module", al.name.split(".")[0], None)
    elif isinstance(n, ast.ImportFrom):
        module = _from_module(n, path)
        if not module:
            return
        for al in n.names:
            if al.name != "*":
                out[al.asname or al.name] = ("from", module, al.name)


def _star_exported(m: "_Mod", name: str) -> bool:
    """`from m import *` 是否匯出 name：m 有字面 `__all__`（字串之 list／tuple）⇒ name 在其中；否則 name 不以底線開頭
    （Python 語意；v36）。`__all__` 非字面者無法靜態判定，依無 `__all__` 處理。"""
    al = m.consts.get("__all__")
    if isinstance(al, (ast.List, ast.Tuple)) and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in al.elts):
        return name in {e.value for e in al.elts}
    return not name.startswith("_")


def _from_module(n: ast.ImportFrom, path: Optional[str]) -> Optional[str]:
    """from 匯入之絕對模組名：相對匯入依所在檔 path 還原（`from .a import b` 於 tests/x/t.py ⇒ tests.x.a）；無法還原 ⇒ None。"""
    if not n.level:
        return n.module
    pkg = path.split("/")[:-1] if path else None
    if pkg is None or n.level > len(pkg):  # 越過頂層套件（Python 拒收）不登記（v36，審查 r35 CODEX-R35-P2-03）
        return None
    parts = pkg[:len(pkg) - (n.level - 1)] + (n.module.split(".") if n.module else [])
    return ".".join(parts) or None


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
            if src is None:
                self._mods[path] = None
            else:
                key = (path, src)
                if key not in _MOD_SHARED:
                    try:
                        _MOD_SHARED[key] = _Mod(path, src)
                    except SyntaxError:
                        _MOD_SHARED[key] = None
                self._mods[path] = _MOD_SHARED[key]
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

    def resolve_name(self, mi: _Mod, name: str, local_imports, depth: int = 0,
                     before: Optional[int] = None) -> Optional[Tuple[str, str]]:
        """名稱 → (定義檔, 名稱)；語意見 `resolve_binding`。"""
        r = self.resolve_binding(mi, name, local_imports, depth, before)
        return (r[0], r[1]) if r is not None else None

    def resolve_binding(self, mi: _Mod, name: str, local_imports, depth: int = 0,
                        before: Optional[int] = None) -> Optional[Tuple[str, str, Optional[ast.AST]]]:
        """名稱 → (定義檔, 名稱, 獲勝綁定當時之 def／class 節點或 None)，限可解析至本 repo 之定義。函式內 import
        （local_imports）優先；否則依 Python 敘述順序語意（SPEC v37；審查 r36 CODEX-R36-P1-01）取模組層最後一次綁定——before
        給定時只看該行之前者（類別建立時之值），否則為模組最終綁定（呼叫時之值）：本模組定義／賦值 ⇒ 本檔（def／class 帶其
        綁定當時之節點——同名重定義時取當時者，v38；審查 r37 CODEX-R37-P1-01；賦值須為常數）；具名匯入 ⇒ 遞移解析其來源；
        星號匯入（v36）⇒ 來源模組確實綁定該名且匯出（`_star_exported`）時才算，遞移解析。"""
        if depth > 8:
            return None
        if name in local_imports:
            return self._resolve_import(local_imports[name], depth)
        win: Optional[Tuple[Any, ...]] = None
        for ln, nm, info in mi.order:
            if before is not None and ln >= before:
                break
            if info[0] == "star":
                p = self.module_path(info[1])
                m2 = self.mod(p) if p else None
                if m2 is not None and _star_exported(m2, name) and self._binds(m2, name, depth + 1):
                    win = ("star", m2)
            elif nm == name:
                win = info
        if win is None:
            return None
        if win[0] == "local":
            if win[1] is not None:
                return (mi.path, name, win[1])
            return (mi.path, name, None) if name in mi.consts else None
        if win[0] == "import":
            return self._resolve_import(win[1], depth)
        return self.resolve_binding(win[1], name, {}, depth + 1)  # 星號：於來源模組遞移解析（其最終綁定）

    def _resolve_import(self, entry: Tuple[str, str, Optional[str]], depth: int
                        ) -> Optional[Tuple[str, str, Optional[ast.AST]]]:
        kind, mod, attr = entry
        if kind != "from":
            return None
        p = self.module_path(mod)
        m2 = self.mod(p) if p else None
        return self.resolve_binding(m2, attr, {}, depth + 1) if m2 is not None else None

    def _binds(self, m: _Mod, name: str, depth: int) -> bool:
        """模組 m 是否於模組層綁定 name（任一綁定敘述，含經星號匯入自可解析之 repo 模組遞移帶入且匯出者）。"""
        if depth > 8:
            return False
        for _ln, nm, info in m.order:
            if nm == name:
                return True
            if info[0] == "star":
                p = self.module_path(info[1])
                m2 = self.mod(p) if p else None
                if m2 is not None and _star_exported(m2, name) and self._binds(m2, name, depth + 1):
                    return True
        return False

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
                _note_imports(n, imports, mi.path)
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

        def expand_calls_within(node: ast.AST) -> None:
            # 契約 inline_rule「每一呼叫 assertion_helpers 之節點」：斷言式子內（及 helper 呼叫之引數內）之 helper 呼叫亦展開
            # ——`assert x == h.f(...)` 之 f 刪斷言須使呼叫者減少（第 1 批審碼 r3 後主委自查：原整句只記一個元素，漏擋）
            for ch in ast.walk(node):
                if isinstance(ch, ast.Call):
                    tgt_ = self.resolve_callee(mi, ch.func, imps)
                    if tgt_ and self.is_helper(tgt_[0], tgt_[1]):
                        self.touched.add(tgt_[0])
                        out.extend(self.expand(mi, ch, tgt_, consts, imps, stack))

        def visit(node: ast.AST) -> None:
            if isinstance(node, ast.Assert):
                element(node, node.lineno, node.end_lineno)
                expand_calls_within(node)
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
                    for a in [*node.args, *(k.value for k in node.keywords)]:
                        expand_calls_within(a)  # 引數內之 helper 呼叫（如 `check(h.f(x))`）
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
        hbn = _bound_names(hfn)  # 一次算出（原於排序 key 內逐名重算，真實規模 28,696 次占 34 秒）
        local = {n for n in hbn if n not in binding}
        order = {n: i for i, n in enumerate(sorted(local, key=lambda n: hbn[n]))}
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
        requested = _requested_fixtures(self, mi, qual, fn)  # 參數在前（序號與 v32 相同）、usefixtures 字面其後
        queue = [(p, (fn.lineno, i)) for i, p in enumerate(requested) if p in fx]
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
            fbn = _bound_names(ffn)  # 一次算出（同上）
            local = set(fbn)
            order = {n: i for i, n in enumerate(sorted(local, key=lambda n: fbn[n]))}

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
    queue = [p for p in _requested_fixtures(eng, mi, qual, fn) if p in fx] + \
        sorted(n for n, (_, _, auto) in fx.items() if auto)
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
    if (mi.path, cls.name) in seen:
        return []
    seen.add((mi.path, cls.name))
    out = ["decorators:" + ast.dump(ast.List(elts=cls.decorator_list, ctx=ast.Load()), include_attributes=False)]
    for st in cls.body:
        if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in st.targets):
            out.append("cls-pytestmark:" + ast.dump(st, include_attributes=False))
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)) and st.name in _LIFECYCLE:
            out.append("lifecycle:" + ast.dump(st, include_attributes=False))
    for b in cls.bases:
        # v36：基底類別經同一解析入口（同模組、具名／別名／相對／星號匯入、模組屬性形式）遞移納入，限 tests/ 下
        # （審查 r35 CODEX-R35-P1-01：原只解析同模組，他模組基底之差異不改變 module_context）
        hit = _base_class(eng, mi, b)
        if hit is not None:
            out.append("base:" + ast.dump(hit[1], include_attributes=False))
            out.extend(_class_context(eng, hit[0], hit[1], seen))
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


_GIT_CTX_ENV = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_PREFIX", "GIT_OBJECT_DIRECTORY")


class _NoGitCtxEnv:
    """暫時移除 git hook 執行期注入之環境變數（pre-commit 中 `GIT_INDEX_FILE` 等會被暫存 worktree 之 git 子行程繼承，
    使 `worktree add`／`apply`／`diff` 作用於主倉索引而失敗）。"""

    def __enter__(self):
        self._saved = {k: os.environ.pop(k) for k in _GIT_CTX_ENV if k in os.environ}
        return self

    def __exit__(self, *exc):
        os.environ.update(self._saved)
        return False


def _digest_with(ctx: Context, head: str, patches: Sequence[str]) -> str:
    """於 head 乾淨樹依序套用 patches（取受驗之樹之補丁內容）後之 diff_digest（記錄器之單一實作）。"""
    key = (head, tuple(patches))
    cache = ctx.extra.setdefault("digests", {})
    if key in cache:
        return cache[key]
    texts = [_tree(ctx).read(rel) or "" for rel in patches]  # 受驗之樹（含暫存區）之內容先於移除環境前讀出
    tmp = Path(tempfile.mkdtemp(prefix="testreg-digest-"))
    wt = tmp / "wt"
    with _NoGitCtxEnv():
        _run_git(ctx.repo_root, "worktree", "add", "-q", "--detach", str(wt), head)
        try:
            for i, text in enumerate(texts):
                pf = tmp / f"p{i}.patch"
                pf.write_text(text, encoding="utf-8")
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
        text = _tree(ctx).read(patch_rel) or ""
        tmp = Path(tempfile.mkdtemp(prefix="testreg-cp-"))
        wt = tmp / "wt"
        with _NoGitCtxEnv():
            _run_git(ctx.repo_root, "worktree", "add", "-q", "--detach", str(wt), head)
            try:
                pf = tmp / "c.patch"
                pf.write_text(text, encoding="utf-8")
                ok = _run_git(wt, "apply", str(pf), check=False).returncode == 0
                for p in _patch_paths(text):
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
                elif isinstance(n, ast.ImportFrom):
                    mod_ = _from_module(n, path)  # v35：相對匯入依所在檔還原為絕對模組名
                    if mod_:
                        mods.add(mod_)
                        mods |= {f"{mod_}.{a.name}" for a in n.names}
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
    # v34：類別之 usefixtures 字面與基底（子類別之測試經此請求 fixture）；v39：依出現序涵蓋全部同名定義、各帶序號（重定義前
    # 建立之子類別經前一個定義請求 fixture；審查 r38 CODEX-R38-P1-02：原只看最後一個定義，改前一個之標記不判減少）
    nth: "collections.Counter[str]" = collections.Counter()
    for _ln, name, info in mi.order:
        if info[0] != "local" or not isinstance(info[1], ast.ClassDef):
            continue
        c, k = info[1], nth[name]
        nth[name] += 1
        if only is not None and name not in only:
            continue
        prof = out.setdefault(name, collections.Counter())
        for u in _usefixtures_in(c.decorator_list) + _usefixtures_in(_pytestmark_values(c.body)):
            prof[f"{k}:usefixtures:{u}"] += 1
        for b in c.bases:
            prof[f"{k}:base:{ast.dump(b)}"] += 1
    for name, v in mi.consts.items():
        plugins = _plugin_list(v) if name == "pytest_plugins" and path.endswith("conftest.py") else None
        if plugins is not None:
            # 外掛於 fixture 解析序最後（`fixture_defs` 以 setdefault 依序取）、不遮蔽既有名稱 ⇒ 輪廓＝依序之外掛元素：
            # 追加不減；移除或改序即減（實作期 b1：整值摺疊時追加一個外掛即判減而走完整反推，真實 conftest 175 秒）
            out[name] = collections.Counter(f"plugin:{i}:{p}" for i, p in enumerate(plugins))
        else:
            out[name] = collections.Counter({"const:" + ast.dump(v): 1})
    for n in mi.tree.body:  # 匯入名：解析目標（他模組 `from 本模組 import 名` 之使用者經此反推）
        if isinstance(n, ast.ImportFrom) and _from_module(n, path):
            mod_ = _from_module(n, path)  # v35：相對匯入依所在檔還原為絕對模組名
            for a in n.names:
                out.setdefault(a.asname or a.name, collections.Counter())[f"import:{mod_}.{a.name}"] += 1
        elif isinstance(n, ast.Import):
            for a in n.names:
                out.setdefault(a.asname or a.name.split(".")[0], collections.Counter())[f"import:{a.name}"] += 1
    return out


def _plugin_list(v: ast.AST) -> Optional[List[str]]:
    """`pytest_plugins` 之字面值 → 模組名清單（字串或字串之 list／tuple）；其他形態 ⇒ None（退回整值摺疊）。"""
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return [v.value]
    if isinstance(v, (ast.List, ast.Tuple)) and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in v.elts):
        return [e.value for e in v.elts]
    return None


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
        return loads | {a.arg for a in fn.args.args} | set(_usefixtures_in(fn.decorator_list))  # v33：usefixtures 字面
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
    # v33／v34：模組層 pytestmark 或任一類別（裝飾器、類別層 pytestmark）以 usefixtures 字面請求減少之名、或減少之名為本檔
    # 之類別（子類別經其請求 fixture）⇒ 全檔（保守超集）
    for m in (hm, cm):
        wide = _usefixtures_in(_pytestmark_values(m.body))
        for s in m.body:
            if isinstance(s, ast.ClassDef):
                wide += _usefixtures_in(s.decorator_list) + _usefixtures_in(_pytestmark_values(s.body)) + [s.name]
        if s_ & set(wide):
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


def _usefixtures_class_words(engs: Sequence["_Engine"], names: set) -> set:
    """names ∪（遞移）以 usefixtures 字面請求 names 之類別名及以之為基底之類別名（各引擎之樹之 tests/ 下 .py）。測試請求
    fixture 之字面——參數名、usefixtures 字串、基底類別名（基底可在他模組，其上之標記不出現在測試檔原文；審查 r33
    CODEX-R33-P1-01）——皆出現於測試檔原文 ⇒ 供文字預篩；同名誤中只多解析、不漏。"""
    words = set(names)
    pyfiles = sorted({p for e in engs for p in e.tree.files() if p.startswith("tests/") and p.endswith(".py")})
    for e in engs:
        e.tree.prefetch(pyfiles)
    grow = True
    while grow:
        grow = False
        wpat = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(words))) + r")\b")
        for eng in engs:
            for p in pyfiles:
                s = eng.tree.read(p) or ""
                if not any(w in s for w in words) or wpat.search(s) is None:
                    continue
                m = eng.mod(p)
                for c in (m.classes.values() if m else []):
                    if c.name in words:
                        continue
                    req = set(_usefixtures_in(c.decorator_list)) | set(_usefixtures_in(_pytestmark_values(c.body)))
                    if req & names or _base_names(eng, m, c) & words:
                        words.add(c.name)
                        grow = True
    return words


def _fixture_dependents(ctx: Context, eng: "_Engine", conftest: str, dec: set) -> set:
    """conftest 或其 `pytest_plugins` 外掛中自身輪廓減少之 fixture 集合 dec ⇒ 該 conftest 作用範圍內直接或經 fixture 傳遞
    （範圍內之 conftest 與其外掛、測試模組本身之 fixture）請求者之測試函式（參數與 usefixtures 字面含基底類別，SPEC v33；
    經 autouse 者為範圍內全部或該模組全部）。非 autouse 時以 fixture 名與遞移之類別名做文字預篩、只解析提及者（第 1 批
    審碼 r3：外掛 fixture 減少原走完整呼叫者反推，真實規模 157 秒）。受影響者之精確判定由呼叫端之逐一多重集合比較決定。"""
    base = conftest[: -len("conftest.py")]
    names = set(dec)
    files = [f for f in _tree(ctx).test_files(ctx.schema) if f.startswith(base)]
    conftests = [f for f in eng.tree.files() if f.startswith(base) and f.endswith("conftest.py")]
    holders = [*conftests, *(pl for c in conftests for pl in _plugin_paths(eng.tree, c))]
    eng.tree.prefetch(holders)
    changed = True
    while changed:
        changed = False
        for f in holders:
            m = eng.mod(f)
            for fname, (ffn, _) in (m.fixtures.items() if m else []):
                if fname not in names and {a.arg for a in ffn.args.args} & names:
                    names.add(fname)
                    changed = True
    autouse = any(auto for c in holders for n, (_, auto) in ((eng.mod(c).fixtures.items()) if eng.mod(c) else [])
                  if n in names)
    eng.tree.prefetch(files)
    if not autouse:
        words = _usefixtures_class_words((eng,), names)
        wpat = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(words))) + r")\b")
        files = [f for f in files if (lambda s: any(w in s for w in words) and wpat.search(s) is not None)(
            eng.tree.read(f) or "")]
    out = set()
    for f in files:
        mf = eng.mod(f)
        local, local_auto = set(names), autouse
        grow = mf is not None
        while grow:  # 測試模組本身之 fixture（只作用於本模組）遞移請求 names
            grow = False
            for fname, (ffn, a) in mf.fixtures.items():
                if fname not in local and {x.arg for x in ffn.args.args} & local:
                    local.add(fname)
                    grow = True
        if mf is not None:
            local_auto = local_auto or any(a for n, (_, a) in mf.fixtures.items() if n in local)
        for q, fn in (_test_functions_of(mf.tree) if mf is not None else {}).items():  # 不可解析之檔 ⇒ 無測試函式
            if local_auto or set(_requested_fixtures(eng, mf, q, fn)) & local:
                out.add(f"{f}::{q}")
    return out


def _fixture_closure(requested: Sequence[str], fx: Mapping[str, Tuple[str, ast.AST, bool]]) -> Dict[str, str]:
    """與 `_Engine.elements` 同一解析序（請求之 fixture——參數與 usefixtures 字面，見 `_requested_fixtures`——、可見之
    autouse fixture，再遞移 fixture 參數）⇒ {fixture 名: 定義檔}。"""
    queue = [p for p in requested if p in fx] + [n for n, (_, _, auto) in sorted(fx.items()) if auto]
    out: Dict[str, str] = {}
    while queue:
        n = queue.pop(0)
        if n in out or n not in fx:
            continue
        out[n] = fx[n][0]
        queue += [a.arg for a in fx[n][1].args.args if a.arg in fx]
    return out


def _plugin_change_dependents(ctx: Context, he: "_Engine", ce: "_Engine", conftest: str
                              ) -> Tuple[Dict[str, List[str]], set]:
    """conftest 之 `pytest_plugins` 移除或改序（審碼 r1 CODEX-R1-P1-02）。被移動之外掛＝HEAD 清單自首個與受驗樹不同之
    位置起之外掛（其前者解析優先序不變）。作用範圍內每一測試：HEAD 解析未經被移動外掛取得 fixture ⇒ 不受影響（新外掛只會
    增加元素）；兩樹解析（名→定義檔）相同 ⇒ 展開不變；純移除（受驗樹解析為 HEAD 之子集、測試檔與保留之 fixture 本體皆
    未變）⇒ 失去之 fixture 有任何斷言元素即必減（其元素整組消失、他處不變），皆無元素即不減；其餘 ⇒ 交逐一精確比較。
    回傳 ({必減 nodeid: 失去之有斷言 fixture 名}, 須精確比較之 nodeid)。不做完整呼叫者反推（真實規模分鐘級）。"""
    head, cur = he.tree, ce.tree  # 用引擎自身之樹：讀檔快取與 `he.mod`／`fixture_defs` 共用（批次預取才生效）
    confs = {t_: [c for c in t_.files() if c.endswith("conftest.py")] for t_ in (head, cur)}
    for t_ in (head, cur):
        t_.prefetch(confs[t_])
        t_.prefetch([pl for c in confs[t_] for pl in _plugin_paths(t_, c)])
    hp, cp = _plugin_paths(head, conftest), _plugin_paths(cur, conftest)
    i = 0
    while i < min(len(hp), len(cp)) and hp[i] == cp[i]:
        i += 1
    moved = set(hp[i:])
    decided: Dict[str, List[str]] = {}
    unsure: set = set()
    if not moved:
        return decided, unsure
    base = conftest[: -len("conftest.py")]
    dumps: Dict[Tuple[int, str, str], str] = {}

    def body(eng: "_Engine", path: str, name: str) -> str:
        key = (id(eng), path, name)
        if key not in dumps:
            m = eng.mod(path)
            fn_ = m.fixtures[name][0] if m and name in m.fixtures else None
            dumps[key] = ast.dump(fn_) if fn_ is not None else ""
        return dumps[key]

    # 文字預篩：測試只能以參數名請求 fixture（或經 autouse 套用）⇒ 被移動外掛提供之 fixture 名及遞移依賴它們之 fixture 名
    # （全部 conftest 與外掛模組，兩樹）皆未於測試檔出現、且其中無 autouse 者 ⇒ 該檔必不受影響，不必解析
    names: set = set()
    auto = False
    for pl in moved:
        m = he.mod(pl)
        for n, (_, a) in (m.fixtures.items() if m else []):
            names.add(n)
            auto = auto or a
    holders = []
    for eng in (he, ce):
        cs = confs[eng.tree]
        holders += [(eng, c) for c in cs] + [(eng, pl) for c in cs for pl in _plugin_paths(eng.tree, c)]
    grow = True
    while grow and not auto:
        grow = False
        for eng, p in holders:
            m = eng.mod(p)
            for n, (ffn, a) in (m.fixtures.items() if m else []):
                if n not in names and {x.arg for x in ffn.args.args} & names:
                    names.add(n)
                    auto = auto or a
                    grow = True
    # 候選字再納入（遞移）以 usefixtures 字面請求上列名稱之類別名（見 `_usefixtures_class_words`）
    words = _usefixtures_class_words((he, ce), names) if names and not auto else set(names)
    pat =re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(words))) + r")\b") if words else None

    def mentions(src: Optional[str]) -> bool:  # 子字串快篩後才以詞界正則確認
        s = src or ""
        return any(n in s for n in words) and pat.search(s) is not None

    # 每檔只解析一次（兩樹原始碼相同時共用）；conftest 鏈與其外掛之 fixture 依目錄快取（與 `_Engine.fixture_defs` 同序：
    # 本模組 → 由近而遠之 conftest.py → 各 conftest 之外掛）；失去之 fixture 有無斷言元素依定義快取。真實規模 autouse 外掛
    # 移除（8,563 個測試函式全數必減）時原逐檔多次解析＋逐 nodeid 重讀 pytest.ini 耗 18–30 秒。
    fp, cpp, files_pat, tps = _collect_patterns(cur)
    dir_defs: Dict[Tuple[int, str], Dict[str, Tuple[str, ast.AST, bool]]] = {}
    has_el: Dict[Tuple[str, str], bool] = {}

    def defs(eng: "_Engine", f: str, own: Optional["_Mod"]) -> Dict[str, Tuple[str, ast.AST, bool]]:
        parts = f.split("/")[:-1]
        key = (id(eng), "/".join(parts))
        if key not in dir_defs:
            chain = ["/".join(parts[:i] + ["conftest.py"]) for i in range(len(parts), -1, -1)]
            chain += [pl for c in chain for pl in _plugin_paths(eng.tree, c)]
            acc: Dict[str, Tuple[str, ast.AST, bool]] = {}
            for p in chain:
                m = eng.mod(p) if eng.tree.exists(p) else None
                for name, (fn_, a) in (m.fixtures.items() if m else []):
                    acc.setdefault(name, (p, fn_, a))
            dir_defs[key] = acc
        out = {name: (f, fn_, a) for name, (fn_, a) in (own.fixtures.items() if own else [])}
        for k, v in dir_defs[key].items():
            out.setdefault(k, v)
        return out

    def elements_nonempty(path: str, name: str, fn_: ast.AST) -> bool:
        if (path, name) not in has_el:
            has_el[(path, name)] = bool(he.collect(he.mod(path), fn_, "fixture", frozenset()))
        return has_el[(path, name)]

    tests = [f for f in head.test_files(ctx.schema) if f.startswith(base)
             and (not tps or any(f == tp or f.startswith(tp.rstrip("/") + "/") for tp in tps))
             and _name_ok(f.rsplit("/", 1)[-1], files_pat)]
    head.prefetch(tests)
    cur.prefetch(tests)
    for f in tests:
        hsrc, csrc = head.read(f), cur.read(f)
        if not auto and (pat is None or not (mentions(hsrc) or (csrc != hsrc and mentions(csrc)))):
            continue
        hm = he.mod(f)
        if hm is None:
            continue
        hfns = _test_functions_of(hm.tree, fp, cpp)
        if not hfns:
            continue
        hfx = defs(he, f, hm)
        if not moved & {p for p, _, _ in hfx.values()}:
            continue
        cm = hm if csrc == hsrc else ce.mod(f)
        cfx = defs(ce, f, cm)
        cfns = hfns if cm is hm else (_test_functions_of(cm.tree, fp, cpp) if cm else {})
        for q, fn in hfns.items():
            hb = _fixture_closure(_requested_fixtures(he, hm, q, fn), hfx)
            if not moved & set(hb.values()):
                continue
            cfn = cfns.get(q)
            if cfn is None:
                continue  # 函式已不在：V20 管
            cb = _fixture_closure(_requested_fixtures(ce, cm, q, cfn), cfx)
            if hb == cb:
                continue
            nid = f"{f}::{q}"
            pure = (hsrc == csrc and all(hb.get(n) == p for n, p in cb.items())
                    and all(p == f or body(he, p, n) == body(ce, p, n) for n, p in cb.items()))
            if not pure:
                unsure.add(nid)
                continue
            lost = sorted(n for n in hb if n not in cb and elements_nonempty(hb[n], n, hfx[n][1]))
            if lost:
                decided[nid] = lost  # nid 依受驗樹 pytest.ini 之收集規則存在（cfns 含 q、檔名與 testpaths 已篩）
    return decided, unsure


def _subclass_users(ctx: Context, he: "_Engine", ce: "_Engine", classes: set) -> set:
    """類別之 usefixtures 字面或基底減少（v34）：直接或遞移以之為基底之測試類別之全部方法（函式層 nodeid，兩樹聯集）。
    以類別名之文字預篩候選檔、只解析提及者（同名類別誤中只多比較、不漏）；不做完整呼叫者反推（真實規模實測 41 秒）。
    受影響者之精確判定由呼叫端之逐一多重集合比較決定。"""
    words = set(classes)
    files = sorted({p for t_ in (he.tree, ce.tree) for p in t_.files() if p.startswith("tests/") and p.endswith(".py")})
    he.tree.prefetch(files)
    ce.tree.prefetch(files)

    def mentions(s: str, pat_: "re.Pattern[str]") -> bool:
        return any(w in s for w in words) and pat_.search(s) is not None

    grow = True
    while grow:
        grow = False
        wpat = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(words))) + r")\b")
        for eng in (he, ce):
            for p in files:
                if not mentions(eng.tree.read(p) or "", wpat):
                    continue
                m = eng.mod(p)
                for c in (m.classes.values() if m else []):
                    if c.name not in words and _base_names(eng, m, c) & words:
                        words.add(c.name)
                        grow = True
    tpat = ctx.schema["formats"]["test_path"]
    wpat = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(words))) + r")\b")
    out: set = set()
    for eng in (he, ce):
        for p in files:
            s = eng.tree.read(p) or ""
            if not re.fullmatch(tpat, p) or not mentions(s, wpat):
                continue
            m = eng.mod(p)
            out |= {f"{p}::{q}" for q in (_test_functions_of(m.tree) if m else {})
                    if "::" in q and q.split("::")[0] in words}
    return out


def _star_reaches(engs: Sequence["_Engine"], pyfiles: Sequence[str], targets: set) -> bool:
    """tests/ 下模組之星號匯入鏈（遞移經 tests/ 以外之 repo 模組）是否觸及 targets 中任一檔（名稱解析之 `_binds` 經此改變）。"""
    for eng in engs:
        queue: List[str] = []
        for p in pyfiles:
            if "import *" in (eng.tree.read(p) or ""):
                m = eng.mod(p)
                queue += [info[1] for _ln, _nm, info in (m.order if m else []) if info[0] == "star"]
        seen: set = set()
        while queue:
            q = eng.module_path(queue.pop())
            if q is None or q in seen:
                continue
            seen.add(q)
            if q in targets:
                return True
            m = eng.mod(q)
            queue += [info[1] for _ln, _nm, info in (m.order if m else []) if info[0] == "star"]
    return False


def _module_deps(eng: "_Engine", path: str, cache: Dict[Tuple[int, str], set]) -> set:
    """模組（含函式內）之 import 所指之 tests/ 下模組檔（與 `helper_callers` 之匯入圖同規則；相對匯入依所在檔還原）。"""
    key = (id(eng), path)
    if key not in cache:
        m = eng.mod(path)
        mods: set = set()
        for n in (ast.walk(m.tree) if m else ()):
            if isinstance(n, ast.Import):
                mods |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mod_ = _from_module(n, path)
                if mod_:
                    mods.add(mod_)
                    mods |= {f"{mod_}.{a.name}" for a in n.names}
        cache[key] = {q for q in (eng.module_path(x) for x in mods) if q and q.startswith("tests/")}
    return cache[key]


def _reverse_importers(engs: Sequence["_Engine"], pyfiles: Sequence[str], targets: set,
                       cache: Dict[Tuple[int, str], set]) -> set:
    """tests/ 下模組中，其匯入（遞移、只經 tests/ 下模組）觸及 targets 者（含 targets 本身；各引擎之樹聯集）。匯入某模組
    之原文必含其模組名末段（套件為目錄名），以之做文字預篩後才解析。"""
    reached, frontier = set(targets), set(targets)
    while frontier:
        stems = {(p[: -len("/__init__.py")] if p.endswith("/__init__.py") else p[:-3]).rsplit("/", 1)[-1]
                 for p in frontier}
        pat = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(stems))) + r")\b")
        new: set = set()
        for eng in engs:
            for p in pyfiles:
                if p in reached or p in new:
                    continue
                s = eng.tree.read(p) or ""
                if any(st in s for st in stems) and pat.search(s) and _module_deps(eng, p, cache) & reached:
                    new.add(p)
        reached |= new
        frontier = new
    return reached


def _node_text(src: str, n: ast.AST) -> str:
    """模組層 def／class 之原文（含裝飾器）。"""
    lines = src.splitlines()
    lo = min([n.lineno, *(d.lineno for d in getattr(n, "decorator_list", []))])
    return "\n".join(lines[lo - 1:n.end_lineno])


def _import_route_tests(ctx: Context, he: "_Engine", ce: "_Engine", reach: set, seeds: set) -> set:
    """匯入途徑之候選測試：自 helper 輪廓減少之名稱（seeds）出發，於反向匯入閉包（reach）內之模組，遞移納入原文提及
    已納入名稱之模組層 def／class 名、`from … import 名 as 別名` 之別名與模組層賦值之目標名（靜態引用必於原文寫出名稱；
    動態取用屬 SPEC §N R6）；閉包內測試檔中，原文（含裝飾器；類別方法取整個類別）提及任一已納入名稱之測試函式為候選，
    模組層非 import 敘述（如 pytestmark）提及、或模組內 autouse fixture 已納入者 ⇒ 該檔全部測試（主委自查：原取匯入檔之
    全部測試，被 27 檔匯入之 helper 刪斷言 438 個測試逐一比較約 6–7 秒）。"""
    tpat = ctx.schema["formats"]["test_path"]
    names = set(seeds)
    grow = True
    while grow and names:
        grow = False
        wpat = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(names))) + r")\b")
        for p in sorted(reach):
            for eng in (he, ce):
                src, m = eng.tree.read(p) or "", eng.mod(p)
                if m is None or wpat.search(src) is None:
                    continue
                for n in m.tree.body:
                    new: set = set()
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if wpat.search(_node_text(src, n)):
                            new = {n.name}
                    elif isinstance(n, ast.ImportFrom):
                        new = {a.asname for a in n.names if a.asname and a.name in names}
                    elif isinstance(n, (ast.Assign, ast.AnnAssign)) and wpat.search(ast.get_source_segment(src, n) or ""):
                        tg = n.targets if isinstance(n, ast.Assign) else [n.target]
                        new = {x.id for t_ in tg for x in ast.walk(t_) if isinstance(x, ast.Name)}
                    if new - names:
                        names |= new
                        grow = True
    out: set = set()
    if not names:
        return out
    wpat = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(names))) + r")\b")
    for f in sorted(p for p in reach if re.fullmatch(tpat, p)):
        nids = _function_nodeids(ce.tree, f)
        if not nids:
            continue
        src, m = ce.tree.read(f) or "", ce.mod(f)
        if m is None:
            out |= set(nids)
            continue
        whole = any(not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))
                    and wpat.search(ast.get_source_segment(src, n) or "") for n in m.tree.body) \
            or any(a and nm in names for nm, (_, a) in m.fixtures.items())
        if whole:
            out |= set(nids)
            continue
        texts = {n.name: _node_text(src, n) for n in m.tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        for nid in nids:
            top = nid.split("::")[1]
            if wpat.search(texts.get(top, "")):
                out.add(nid)
    return out


def _fx_info(eng: "_Engine", m: Optional["_Mod"], n: str):
    """fixture 之 (形狀, 自身元素鍵多重集合)；形狀＝(參數列, autouse, 元素中局部名→序號, 元素中非局部名集合)。"""
    if m is None or n not in m.fixtures:
        return None
    ffn, auto = m.fixtures[n]
    inner = eng.collect(m, ffn, "fixture", frozenset())
    bn = _bound_names(ffn)
    order = {x: i for i, x in enumerate(sorted(bn, key=lambda x: bn[x]))}
    ids = {x.id for el in inner if el.get("node") is not None for x in ast.walk(el["node"]) if isinstance(x, ast.Name)}
    shape = ([a.arg for a in ffn.args.args], auto, {x: order[x] for x in ids if x in bn}, ids - set(bn))
    return shape, collections.Counter(e["key"] for e in eng.normalize(ffn, inner))


def _nontest_route(ctx: Context, he: "_Engine", ce: "_Engine", route: Mapping[str, set]) -> Tuple[Dict[str, List[str]], set]:
    """tests/ 下非測試檔（conftest、外掛、helper 模組）之差量減少（`route`：已扣除 pytest_plugins 與類別之處理）⇒ 受影響
    測試之路由，不做完整呼叫者反推（第 1 批審碼 r3：外掛 fixture 157 秒；主委自查：autouse fixture 120 秒、經 fixture 使用之
    helper 同型）。影響只經兩途：①fixture——各 conftest 與其外掛（holders）之 fixture 中，兩樹自身展開（`_fx_info`）不同者
    （其模組改變或其匯入閉包觸及改變之檔）；其請求者（依作用範圍、遞移、usefixtures 與 autouse）為候選；②匯入——自身
    匯入閉包觸及 route 之測試檔之全部測試，逐一精確比較。①之候選交 `_fixture_change_decide` 免展開判定。
    回傳 ({必減 nodeid: fixture 名}, 須精確比較之 nodeid)。"""
    changed = ctx.extra["changed"]
    tpat = ctx.schema["formats"]["test_path"]
    pyfiles = sorted({p for e in (he, ce) for p in e.tree.files() if p.startswith("tests/") and p.endswith(".py")})
    for e in (he, ce):
        e.tree.prefetch(pyfiles)  # 文字預篩讀全部檔：批次讀取（逐檔讀 HEAD／暫存區為每檔一個 git 子行程，實測 11–22 秒）
    dep_cache: Dict[Tuple[int, str], set] = {}
    changed_t ={p for p in changed if p.startswith("tests/") and p.endswith(".py")}
    reach_all = _reverse_importers((he, ce), pyfiles, changed_t, dep_cache)
    reach_route = _reverse_importers((he, ce), pyfiles, set(route), dep_cache)
    scopes_of: Dict[str, set] = {}  # holder → 其作用之 conftest（conftest 本身，或列它於 pytest_plugins 者）
    for e in (he, ce):
        for c in e.tree.files():
            if c.endswith("conftest.py"):
                scopes_of.setdefault(c, set()).add(c)
                for pl in _plugin_paths(e.tree, c):
                    scopes_of.setdefault(pl, set()).add(c)
    chg: Dict[Tuple[str, str], Tuple[bool, bool]] = {}  # (holder, fixture) → (形狀相同, 自身元素鍵減少)
    for p in sorted(scopes_of):
        if p not in reach_all:
            continue
        hm, cm = he.mod(p), ce.mod(p)
        for n in sorted(set(hm.fixtures if hm else ()) | set(cm.fixtures if cm else ())):
            a, b = _fx_info(he, hm, n), _fx_info(ce, cm, n)
            if a is not None and a == b:
                continue
            same = a is not None and b is not None and a[0] == b[0]
            chg[(p, n)] = (same, same and bool(multiset_decreased(a[1], b[1])))
    by_scope: Dict[str, set] = {}
    for (p, n) in chg:
        if p in reach_route:
            for c in scopes_of[p]:
                by_scope.setdefault(c, set()).add(n)
    cands: set = set()
    for c, names in sorted(by_scope.items()):
        cands |= _fixture_dependents(ctx, ce, c, names) | _fixture_dependents(ctx, he, c, names)
    exact = _import_route_tests(ctx, he, ce, reach_route, set().union(*route.values()))
    nt_changed = {p for p in changed if p.endswith(".py") and not p.startswith("tests/")}
    if "pytest.ini" in changed or (nt_changed and _star_reaches((he, ce), pyfiles, nt_changed)):
        return {}, cands | exact  # 免展開判定之前提不成立：全部逐一精確比較
    decided, unsure = _fixture_change_decide(ctx, he, ce, chg, reach_all, cands - exact)
    return decided, unsure | exact


def _fixture_change_decide(ctx: Context, he: "_Engine", ce: "_Engine", chg: Mapping[Tuple[str, str], Tuple[bool, bool]],
                           reach_all: set, cands: set) -> Tuple[Dict[str, List[str]], set]:
    """fixture 改變之候選測試之斷言多重集合是否減少之免逐一展開判定（主委自查：autouse fixture 刪斷言時候選＝範圍內全部
    8,592 個測試，逐一比較 120 秒）。元素鍵＝改名後語法樹之 dump（不含行號），全域序號依用名之位置元組排序（同元組依
    出現序）⇒ 下列前提成立時免展開即可判定；不成立者交逐一精確比較（呼叫端已確認 pytest.ini 未變、tests/ 以外之變更 .py
    不在星號匯入鏈上）：
    ①該測試檔兩版相同，且不在 `reach_all`（自身匯入閉包未觸及任何變更之 tests/ 下 .py）⇒ 本體與模組內 fixture 之展開不變；
    ②兩樹 fixture 展開順序（名、定義檔、位置）於留下者相同；chg 外之 holder fixture 兩樹展開相同——(a) 閉包相同，且其中
      改變者恰一個 f、f 之形狀（參數列、autouse、元素用名之局部名→序號、非局部名集合）兩版相同 ⇒ 其餘元素與全域序號
      不變、f 部分之鍵經同一單射改名 ⇒ 減少 ⟺ f 自身元素鍵多重集合減少；(b) 受驗樹閉包為 HEAD 閉包之真子集且留下者無
      改變 ⇒ 失去之 fixture 有任何元素即必減（元素總數減少），皆無元素即不減（其局部名不在任何元素中、序號不變）。
    回傳 ({必減 nodeid: fixture 名}, 須精確比較之 nodeid)。"""
    has_el: Dict[Tuple[str, str], bool] = {}

    def elements_nonempty(path: str, n: str) -> bool:
        if (path, n) not in has_el:
            m = he.mod(path)
            has_el[(path, n)] = bool(m and n in m.fixtures and he.collect(m, m.fixtures[n][0], "fixture", frozenset()))
        return has_el[(path, n)]

    cache: Dict[Tuple[int, str], Dict[str, Tuple[str, ast.AST, bool]]] = {}
    fp, cpp, files_pat, tps = _collect_patterns(ce.tree)
    fns: Dict[str, Dict[str, ast.AST]] = {}
    decided: Dict[str, List[str]] = {}
    unsure: set = set()
    for nid in sorted(cands):
        path, qual = _split_nodeid(nid)
        if path in reach_all or ce.tree.read(path) != he.tree.read(path):
            unsure.add(nid)
            continue
        hmod = he.mod(path)  # 兩版原始碼相同 ⇒ 同一解析結果（`_MOD_SHARED`）
        if path not in fns:  # 依受驗樹（pytest.ini 未變）之收集規則：檔名與 testpaths 不符者無 nodeid
            ok = (not tps or any(path == tp or path.startswith(tp.rstrip("/") + "/") for tp in tps)) \
                and _name_ok(path.rsplit("/", 1)[-1], files_pat)
            fns[path] = _test_functions_of(hmod.tree, fp, cpp) if hmod is not None and ok else {}
        fn = fns[path].get(qual)
        if fn is None:
            continue  # 依受驗樹收集規則不存在之 nodeid：精確比較路徑亦不報（存在性檢查）
        ho = _fixture_order(_requested_fixtures(he, hmod, qual, fn), _dir_fixture_defs(he, path, hmod, cache), fn.lineno)
        co = _fixture_order(_requested_fixtures(ce, hmod, qual, fn), _dir_fixture_defs(ce, path, hmod, cache), fn.lineno)
        if [x for x in ho if any(x[0] == y[0] for y in co)] != co:
            unsure.add(nid)  # 留下之 fixture 之展開順序、定義檔或位置改變：全域序號可能重排
            continue
        hb, cb = {n: p for n, p, _ in ho}, {n: p for n, p, _ in co}
        hs = {n for n, p in hb.items() if (p, n) in chg}
        if hb == cb:
            if not hs:
                continue  # 閉包不含改變之 fixture ⇒ 全部元素不變
            if len(hs) == 1 and chg[(hb[next(iter(hs))], next(iter(hs)))][0]:
                if chg[(hb[next(iter(hs))], next(iter(hs)))][1]:
                    decided[nid] = sorted(hs)
                continue
        elif not {n for n, p in cb.items() if (p, n) in chg}:
            lost = sorted(n for n in hb if n not in cb and elements_nonempty(hb[n], n))
            if lost:
                decided[nid] = lost
            continue
        unsure.add(nid)
    return decided, unsure


def _fixture_order(requested: Sequence[str], fx: Mapping[str, Tuple[str, ast.AST, bool]], lineno: int
                   ) -> List[Tuple[str, str, Tuple[int, int]]]:
    """與 `_Engine.elements` 同一佇列（請求者依序、可見之 autouse、再遞移 fixture 參數並承襲位置）⇒ 依展開順序之
    [(fixture 名, 定義檔, 位置)]；位置進入元素之局部名佔位、決定全域序號。"""
    queue = [(p, (lineno, i)) for i, p in enumerate(requested) if p in fx]
    queue += [(n, (lineno, -1)) for n, (_, _, auto) in sorted(fx.items()) if auto]
    seen: set = set()
    out: List[Tuple[str, str, Tuple[int, int]]] = []
    while queue:
        name, pos = queue.pop(0)
        if name in seen or name not in fx:
            continue
        seen.add(name)
        out.append((name, fx[name][0], pos))
        queue += [(a.arg, pos) for a in fx[name][1].args.args if a.arg in fx]
    return out


def _dir_fixture_defs(eng: "_Engine", f: str, own: Optional["_Mod"],
                      cache: Dict[Tuple[int, str], Dict[str, Tuple[str, ast.AST, bool]]]
                      ) -> Dict[str, Tuple[str, ast.AST, bool]]:
    """與 `_Engine.fixture_defs` 同序（本模組 → 由近而遠之 conftest.py → 各 conftest 之外掛），conftest 鏈部分依目錄快取。"""
    parts = f.split("/")[:-1]
    key = (id(eng), "/".join(parts))
    if key not in cache:
        chain = ["/".join(parts[:i] + ["conftest.py"]) for i in range(len(parts), -1, -1)]
        chain += [pl for c in chain for pl in _plugin_paths(eng.tree, c)]
        acc: Dict[str, Tuple[str, ast.AST, bool]] = {}
        for p in chain:
            m = eng.mod(p) if eng.tree.exists(p) else None
            for name, (fn_, a) in (m.fixtures.items() if m else []):
                acc.setdefault(name, (p, fn_, a))
        cache[key] = acc
    out = {name: (f, fn_, a) for name, (fn_, a) in (own.fixtures.items() if own else [])}
    for k, v in cache[key].items():
        out.setdefault(k, v)
    return out


def literal_fix_receipt_rel(schema: Mapping[str, Any], path: str) -> str:
    """契約 `receipts.literal_fix`：測試檔 path 之字面對映修正收據之 repo 相對路徑。"""
    return f"{schema['receipts']['literal_fix']['dir']}/{path.replace('/', '__')}.json"


def _string_spans(src: str) -> List[Tuple[int, int]]:
    """原始碼中字串 token（含 f-string）之 [起, 迄) 字元位置；不可 tokenize ⇒ []。"""
    import io
    import tokenize
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    spans = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.STRING:
                spans.append((starts[tok.start[0] - 1] + tok.start[1], starts[tok.end[0] - 1] + tok.end[1]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    return spans


def _literal_regex(keys: Iterable[str], boundary: str) -> "re.Pattern[str]":
    alt = "|".join(re.escape(k) for k in sorted(keys, key=lambda k: (-len(k), k)))
    return re.compile(f"(?<![{boundary}])(?:{alt})(?![{boundary}])")


def literal_fix_errors(ctx: Context, path: str) -> Optional[List[str]]:
    """契約 `receipts.literal_fix`（SPEC v41）：受驗之樹中測試檔 path 之字面對映修正收據。無收據 ⇒ None；有 ⇒ 不符之
    清單（空＝成立，該檔之 V19 一次性放行）。條件：形狀＝`types.receipt_literal_fix`；path 相符；head＝HEAD（一次性）；
    approval_ref 存在於受驗之樹；對映非空且雙射、鍵值不交；每鍵為假測試檔識別（路徑形合 `key_path_pattern` 而不合
    `formats.test_path`，或點號形合 `key_dotted_pattern` 且其路徑形如前），值為對應之合 `formats.test_path` 者
    （點號形之值之路徑形合之），同一識別之路徑形與點號形之值相對應；HEAD 版中鍵之每一出現、受驗版中值之每一出現皆
    位於字串 token 內，且值不出現於 HEAD 版；HEAD 版全文以識別字邊界之子字串代換（長鍵先、不重疊）後與受驗版逐位元
    相等（不得夾帶其他改動）；（v42）session_id 所指記錄器 session 綁定 head＋patch_path（patch 後之該檔＝受驗版），
    且該檔每一函式層 nodeid 於其中全為 passed。"""
    s = ctx.schema
    lf = s["receipts"]["literal_fix"]
    t = _tree(ctx)
    text = t.read(literal_fix_receipt_rel(s, path))
    if text is None:
        return None
    try:
        r = json.loads(text)
    except ValueError:
        return ["字面對映修正收據非 JSON"]
    errs = list(_seam("validate_shape")(r, {"type": "types.receipt_literal_fix"}, s))
    if errs:
        return errs
    if r["path"] != path:
        errs.append(f"收據 path {r['path']} ≠ {path}")
    if r["head"] != ctx.extra["head_sha"]:
        errs.append("收據 head ≠ HEAD（字面對映修正收據為一次性）")
    if not (ctx.repo_root / r["approval_ref"]).is_file():  # 收斂檔依慣例不進 git（.git/info/exclude 之 handoffs/*）
        errs.append(f"approval_ref {r['approval_ref']} 不存在")
    m: Dict[str, str] = r["map"]
    if not m or len(set(m.values())) != len(m) or set(m) & set(m.values()):
        return errs + ["對映須非空、雙射且鍵值不交"]
    tp = s["formats"]["test_path"]

    def as_path(x: str, dotted: bool) -> str:
        return x.replace(".", "/") + ".py" if dotted else x

    for k, v in m.items():
        dotted = re.fullmatch(lf["key_dotted_pattern"], k) is not None
        kp = as_path(k, dotted)
        if re.fullmatch(lf["key_path_pattern"], kp) is None or re.fullmatch(tp, kp) is not None:
            errs.append(f"鍵 {k!r} 非不合 formats.test_path 之假測試檔識別")
        if re.fullmatch(tp, as_path(v, dotted)) is None or (dotted and re.fullmatch(lf["key_dotted_pattern"], v) is None):
            errs.append(f"值 {v!r} 須為合 formats.test_path 之{'點號形' if dotted else '路徑'}")
        if dotted and kp in m and as_path(v, True) != m[kp]:
            errs.append(f"點號形 {k!r}→{v!r} 與路徑形 {kp!r}→{m[kp]!r} 不對應")
    old, new = ctx.extra["head_obj"].read(path), t.read(path)
    if old is None or new is None:
        return errs + ["HEAD 或受驗之樹缺該測試檔"]
    rx_k, rx_v = _literal_regex(m, lf["boundary_chars"]), _literal_regex(m.values(), lf["boundary_chars"])
    for src, rx, what in ((old, rx_k, "鍵（HEAD 版）"), (new, rx_v, "值（受驗版）")):
        spans = _string_spans(src)
        bad = [x.group(0) for x in rx.finditer(src) if not any(a <= x.start() and x.end() <= b for a, b in spans)]
        if bad:
            errs.append(f"{what}出現於字串 token 外：{sorted(set(bad))[:3]}")
    if rx_v.search(old):
        errs.append("值已出現於 HEAD 版（對映不可逆）")
    if rx_k.sub(lambda x: m[x.group(0)], old) != new:
        errs.append("HEAD 版套對映後與受驗版不相等（不得夾帶其他改動）")
    if errs:
        return errs
    # v42（修訂審查 r40 CODEX-R40-P1-01）：改名後全檔須實跑全過——依賴舊識別「不合格」之斷言改名後必紅，故不能靜默
    # 轉弱；收據綁定一次記錄器 session：head＝收據 head、diff_digest＝head 乾淨樹套 patch_path 之 diff_digest、patch 後
    # 之該檔＝受驗版，且該檔每一函式層 nodeid 於 session 皆有紀錄且全為 passed
    if not t.exists(r["patch_path"]):
        return [f"patch_path {r['patch_path']} 不存在"]
    # v43（修訂審查 r41 CODEX-R41-P1-01）：patch 所及之檔 ⊆ 契約 allowed_patch_paths ∪ {path}——不得夾帶改被測生產碼
    # 使改名後之負向斷言仍綠
    extra = sorted(set(_patch_paths(t.read(r["patch_path"]) or "")) - set(lf["allowed_patch_paths"]) - {path})
    if extra:
        return errs + [f"patch_path 含契約 allowed_patch_paths 以外之檔：{extra[:5]}"]
    if _PatchedTree(ctx, r["head"], r["patch_path"]).read(path) != new:
        errs.append("patch_path 套於 head 後之該檔 ≠ 受驗版")
    s = _ledger_session(ctx, r["session_id"])
    if s is None:
        return errs + [f"unverifiable：session {r['session_id']} 不在 ledger"]
    info = s["session"] or {}
    if info.get("head") != r["head"] or info.get("diff_digest") != _digest_with(ctx, r["head"], [r["patch_path"]]):
        errs.append("session 不綁定 head＋patch_path")
    for fn in _function_nodeids(t, path):
        recs = [x for n_, x in s["tests"].items() if re.sub(r"\[.*\]$", "", n_) == fn]
        if not recs or any(x.get("outcome") != "passed" for x in recs):
            errs.append(f"session 中 {fn} 未全為 passed（{sorted({x.get('outcome') for x in recs}) or '無紀錄'}）")
    return errs


def rule_v19(ctx: Context) -> List[Finding]:
    """V19（以 `assertion_multiset` 與 `multiset_decreased` 判定；測試檔有成立之字面對映修正收據〔`literal_fix_errors`
    為空〕⇒ 該檔之測試一次性放行）。"""
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
    he, ce = _engine_for(ctx, "HEAD"), _engine_for(ctx, ctx.tree)
    callers = _seam("helper_callers")
    for f in files:
        common = set(_function_nodeids(head, f)) & set(_function_nodeids(t, f))
        dec = _seam("decreased_defs")(ctx.repo_root, f, tree=ctx.tree)
        if dec is None:
            nids |= common
            continue
        dec_ = {d for d in dec if not d.startswith("test")}
        nids |= _affected_tests(head.read(f), t.read(f), f, common, dec_)
        if dec_:  # v34：經任何層級 usefixtures（含他模組基底類別）請求本檔減少之 fixture 者（審查 r33 CODEX-R33-P1-01）
            for eng_ in (he, ce):
                m_ = eng_.mod(f)
                for q, fn in (_test_functions(eng_.tree.read(f)).items() if m_ else []):
                    if f"{f}::{q}" in common and set(_requested_fixtures(eng_, m_, q, fn)) & dec_:
                        nids.add(f"{f}::{q}")
            cls_dec = {d for d in dec_ if any(m_ and d in m_.classes for m_ in (he.mod(f), ce.mod(f)))}
            if cls_dec:  # 本檔類別之 usefixtures 或基底減少：他檔之（遞移）子類別經此請求 fixture
                nids |= _subclass_users(ctx, he, ce, cls_dec)
    decided: Dict[str, List[str]] = {}
    decided_fx: Dict[str, List[str]] = {}  # fixture 改變之免展開判定（`_fixture_change_decide`；存在性已依受驗樹確認）
    route: Dict[str, set] = {}  # 非測試檔 → 其（扣除外掛清單與類別後之）輪廓減少名稱
    for h in helpers:
        dec = _seam("decreased_defs")(ctx.repo_root, h, tree=ctx.tree)
        dec = None if dec is None else set(dec)
        if dec is not None and not dec:
            continue  # 差量：本檔無任何定義之自身斷言輪廓減少 ⇒ 不可能有呼叫者減少
        if h.endswith("conftest.py") and dec is not None and "pytest_plugins" in dec:
            # 外掛移除／改序：外掛之 fixture 於展開時只記為觸及外掛檔（非 conftest），反推 conftest 本身會漏掉只經外掛取得
            # 斷言之測試（實作期 b1 test_07w 抓到）；改依兩樹之 fixture 解析逐測試判定（審碼 r1 CODEX-R1-P1-02：原對外掛做
            # 完整呼叫者反推，真實規模分鐘級）
            d_, u_ = _plugin_change_dependents(ctx, he, ce, h)
            for nid_, names_ in d_.items():
                decided[nid_] = sorted(set(decided.get(nid_, [])) | set(names_))
            nids |= u_
            dec = dec - {"pytest_plugins"}
            if not dec:
                continue
        if dec is not None:
            cls_dec = {d for d in dec if any(m_ and d in m_.classes for m_ in (he.mod(h), ce.mod(h)))}
            if cls_dec:  # v34：helper／conftest 中基底類別之 usefixtures 或基底減少 ⇒ （遞移）子類別之測試，不做完整反推
                nids |= _subclass_users(ctx, he, ce, cls_dec)
                dec = dec - cls_dec
                if not dec:
                    continue
        if dec is None:  # 不可解析：完整呼叫者反推
            nids |= set(callers(ctx.repo_root, h, tree=ctx.tree)) | set(callers(ctx.repo_root, h, tree="HEAD"))
        else:
            route[h] = set(dec)
    if route:  # 經 fixture 或匯入之影響（`_nontest_route`；不做完整呼叫者反推——審碼 r3 外掛 157 秒、autouse 120 秒）
        decided_fx, u_ = _nontest_route(ctx, he, ce, route)
        nids |= u_
    tombs, out = _tomb_ids(ctx), []
    present: Dict[str, set] = {}
    lit: Dict[str, Optional[List[str]]] = {}
    for nid in sorted(nids | set(decided) | set(decided_fx)):
        if nid in decided and nid not in nids:  # 存在性已於 `_plugin_change_dependents` 依受驗樹收集規則確認
            if nid not in tombs and not _rewrite_ok(ctx, nid):
                out.append(Finding("V19", nid, f"斷言多重集合減少（pytest_plugins 移除／改序使 fixture "
                                               f"{', '.join(decided[nid])} 之斷言不再套用；須同提交立碑或附 rewrite 收據）"))
            continue
        if nid in decided_fx and nid not in nids:
            if nid not in tombs and not _rewrite_ok(ctx, nid):
                out.append(Finding("V19", nid, f"斷言多重集合減少（fixture {', '.join(decided_fx[nid])} 之斷言減少或"
                                               f"不再套用；須同提交立碑或附 rewrite 收據）"))
            continue
        path_ = nid.split("::")[0]
        if path_ not in present:
            present[path_] = set(_function_nodeids(t, path_))
        if nid not in present[path_]:
            continue
        if path_ not in lit:
            lit[path_] = _seam("literal_fix_errors")(ctx, path_)
        if lit[path_] == []:
            continue  # 字面對映修正（SPEC v41）：HEAD 版全文套對映＝受驗版，斷言之改變只來自假測試檔識別之改名
        old = collections.Counter(e["key"] for e in he.elements(nid))
        new = collections.Counter(e["key"] for e in ce.elements(nid))
        if _skip_like(t, nid) and not _skip_like(head, nid):
            new = collections.Counter()  # 新增 skip／skipif／xfail（函式、類別、模組 pytestmark、本體 pytest.skip／xfail）⇒ 視為空
        dec = _seam("multiset_decreased")(old, new)
        if dec and nid not in tombs and not _rewrite_ok(ctx, nid):
            why = f"；字面對映修正收據不成立：{'；'.join(lit[path_][:3])}" if lit[path_] else ""
            out.append(Finding("V19", nid, f"斷言多重集合減少 {len(dec)} 項（須同提交立碑或附 rewrite 收據）{why}"))
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


ALLOWED_RED_REL = "tests/_golden/prered/allowed_red.json"
FACT_KEYS_REL = "scripts/fact_keys.json"


def review(repo_root: Path) -> Dict[str, Dict[str, SignalValue]]:
    """逐 catalog entry 逐訊號：{path: {訊號名: True|False|"unknown"}}；訊號名依 schema `enums.review_signal`，
    每訊號以 `signal_<名>`（呼叫當下以模組屬性取用）判定；不寫回 catalog。"""
    ctx = build_context(repo_root, "worktree")
    names = list(ctx.schema["enums"]["review_signal"])
    return {p: {s: _seam(f"signal_{s}")(ctx, p) for s in names} for p in sorted(_entries(ctx))}


def _file_of(nodeid: str) -> str:
    return nodeid.split("::")[0]


def _review_summary(ctx: Context) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """summary 依檔分組（{檔: [(nodeid, 紀錄)…]} 之扁平形：紀錄附 nodeid）；不存在或不合法（同記錄器 read_summary：
    JSON 不可解析、schema_version／k 不符、形狀不符）⇒ None。"""
    if "review_summary" not in ctx.extra:
        s = ctx.schema
        p = ctx.repo_root / s["summary"]["path"]
        by_file: Optional[Dict[str, List[Dict[str, Any]]]] = None
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            obj = None
        if isinstance(obj, dict) and obj.get("schema_version") == s["version"] and obj.get("k") == s["summary"]["k"] \
                and not _seam("validate_shape")(obj, s["summary"]["shape"], s):
            by_file = collections.defaultdict(list)
            for nid, recs in obj["nodes"].items():
                for r in recs:
                    by_file[_file_of(nid)].append(dict(r, nodeid=nid))
        ctx.extra["review_summary"] = by_file
    return ctx.extra["review_summary"]


def _review_ledger(ctx: Context) -> Optional[Dict[str, Tuple[str, str, bool]]]:
    """ledger 目錄不存在 ⇒ None；否則 {檔: (started, session_id, 該 session 有該檔之 collect_record)}，取收集過該檔
    （有該檔之 test 或 collect 紀錄）之 session 中 started 最晚者（同 started 以 session_id 定序）。"""
    if "review_ledger" not in ctx.extra:
        d = ctx.ledger_dir
        latest: Optional[Dict[str, Tuple[str, str, bool]]] = None
        if d.is_dir():
            latest = {}
            for f in sorted(d.glob("*.jsonl")):
                started, sid, seen, coll = None, f.name[:-len(".jsonl")], set(), set()
                try:
                    lines = f.read_text(encoding="utf-8").splitlines()
                except OSError:
                    continue
                for line in lines:
                    try:
                        rec = json.loads(line) if line.strip() else None
                    except ValueError:
                        continue
                    if not isinstance(rec, dict):
                        continue
                    kind = rec.get("kind")
                    if kind == "session":
                        started, sid = str(rec.get("started")), str(rec.get("session_id", sid))
                    elif kind == "test" and isinstance(rec.get("nodeid"), str):
                        seen.add(_file_of(rec["nodeid"]))
                    elif kind == "collect" and isinstance(rec.get("path"), str):
                        seen.add(rec["path"])
                        coll.add(rec["path"])
                if started is None:
                    continue
                for path in seen:
                    cand = (started, sid, path in coll)
                    if path not in latest or cand[:2] > latest[path][:2]:
                        latest[path] = cand
        ctx.extra["review_ledger"] = latest
    return ctx.extra["review_ledger"]


def _prod_module_file(head: "_Tree", dotted: str, roots: Tuple[str, ...]) -> Tuple[bool, Optional[str]]:
    """(是否屬 production_roots 之模組名, HEAD 中之檔)；非生產模組回 (False, None)。無 __init__.py 之套件目錄
    （namespace package）回目錄路徑加 "/"（無模組層綁定，只有子模組）。"""
    base = dotted.replace(".", "/")
    if not any((base + "/").startswith(r) if r.endswith("/") else base + ".py" == r for r in roots):
        return False, None
    for cand in (base + ".py", base + "/__init__.py"):
        if head.exists(cand):
            return True, cand
    if getattr(head, "_dirset", None) is None:
        head._dirset = {f.rsplit("/", 1)[0] for f in head.files() if "/" in f}
        head._dirset |= {d.rsplit("/", i)[0] for d in list(head._dirset) for i in range(1, d.count("/") + 1)}
    return (True, base + "/") if base in head._dirset else (True, None)


def _module_level_binds(src: Optional[str]) -> Tuple[set, bool]:
    """模組層（含模組層 if／try／with／for 區塊內）綁定之名稱，與是否有不可列舉之來源（星號匯入、模組層 __getattr__）。"""
    names: set = set()
    if src is None:
        return names, False
    try:
        mod = _parse(src)
    except SyntaxError:
        return names, True
    wildcard = False

    def targets(t: ast.AST) -> None:
        for n in ast.walk(t):
            if isinstance(n, ast.Name):
                names.add(n.id)

    def visit(body: Sequence[ast.stmt]) -> None:
        nonlocal wildcard
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(n.name)
                wildcard = wildcard or n.name == "__getattr__"
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    targets(t)
            elif isinstance(n, (ast.AnnAssign, ast.AugAssign)):
                targets(n.target)
            elif isinstance(n, ast.Import):
                names.update((al.asname or al.name).split(".")[0] for al in n.names)
            elif isinstance(n, ast.ImportFrom):
                for al in n.names:
                    if al.name == "*":
                        wildcard = True
                    else:
                        names.add(al.asname or al.name)
            elif isinstance(n, (ast.For, ast.AsyncFor)):
                targets(n.target)
                visit(n.body)
                visit(n.orelse)
            elif isinstance(n, (ast.With, ast.AsyncWith)):
                for it in n.items:
                    if it.optional_vars is not None:
                        targets(it.optional_vars)
                visit(n.body)
            elif isinstance(n, ast.If):
                visit(n.body)
                visit(n.orelse)
            elif isinstance(n, ast.Try):
                visit(n.body)
                visit(n.orelse)
                visit(n.finalbody)
                for h in n.handlers:
                    visit(h.body)

    visit(mod.body)
    return names, wildcard


def _prod_symbol_present(ctx: Context, dotted: str, sym: str) -> Optional[bool]:
    """sym 於 HEAD 之生產模組 dotted 是否存在（模組層綁定或子模組）；dotted 非生產模組 ⇒ None。"""
    cache = ctx.extra.setdefault("review_prod", {})
    key = (dotted, sym)
    if re.fullmatch(r"__\w+__", sym):  # 模組物件之內建屬性（__file__、__name__…）
        return True if _prod_module_file(ctx.extra["head_obj"], dotted, tuple(
            ctx.schema["receipts"]["E0"]["production_roots"]))[0] else None
    if key not in cache:
        head = ctx.extra["head_obj"]
        roots = tuple(ctx.schema["receipts"]["E0"]["production_roots"])
        is_prod, mf = _prod_module_file(head, dotted, roots)
        if not is_prod:
            cache[key] = None
        elif mf is None:
            cache[key] = False
        else:
            binds = ctx.extra.setdefault("review_binds", {})
            if mf not in binds:
                binds[mf] = _module_level_binds(head.read(mf))
            names, wildcard = binds[mf]
            sub = dotted.replace(".", "/") + "/" + sym
            cache[key] = wildcard or sym in names or head.exists(sub + ".py") or head.exists(sub + "/__init__.py")
    return cache[key]


def _dotted_chain(n: ast.AST) -> Optional[List[str]]:
    parts: List[str] = []
    while isinstance(n, ast.Attribute):
        parts.append(n.attr)
        n = n.value
    if not isinstance(n, ast.Name):
        return None
    parts.append(n.id)
    return parts[::-1]


def signal_prod_symbol_gone(ctx: Context, path: str) -> SignalValue:
    """測試檔 import 之生產符號於 HEAD AST 不存在。測試檔讀工作樹；生產模組（schema `receipts.E0.production_roots`）讀
    HEAD。計入：`from <生產模組> import <名>`（含函式內；名須為模組層綁定或子模組）、`import <生產模組>[ as 別名]` 後之
    屬性鏈 `<模組>.<名>`（Load）、及所 import 之生產模組本身於 HEAD 不存在；模組有星號匯入或模組層 __getattr__ ⇒ 不判
    缺。測試檔不可解析或不存在 ⇒ False。"""
    src = _tree(ctx).read(path)
    if src is None:
        return False
    try:
        mod = _parse(src)
    except SyntaxError:
        return False
    head = ctx.extra["head_obj"]
    roots = tuple(ctx.schema["receipts"]["E0"]["production_roots"])
    aliases: Dict[str, str] = {}
    modules: set = set()
    for n in ast.walk(mod):
        if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            is_prod, mf = _prod_module_file(head, n.module, roots)
            if not is_prod:
                continue
            for al in n.names:
                if al.name != "*" and _prod_symbol_present(ctx, n.module, al.name) is False:
                    return True
            if mf is None:
                return True
        elif isinstance(n, ast.Import):
            for al in n.names:
                is_prod, mf = _prod_module_file(head, al.name, roots)
                if not is_prod:
                    continue
                if mf is None:
                    return True
                if al.asname:
                    aliases[al.asname] = al.name
                else:
                    modules.add(al.name)
    if not aliases and not modules:
        return False
    for n in ast.walk(mod):
        if not (isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load)):
            continue
        chain = _dotted_chain(n)
        if chain is None:
            continue
        if chain[0] in aliases:
            chain = aliases[chain[0]].split(".") + chain[1:]
        elif not any(m.split(".")[0] == chain[0] for m in modules | set(aliases.values())):
            continue
        # 鏈之最長前綴為所 import 之生產模組者；其下一節須存在
        for i in range(len(chain) - 1, 0, -1):
            dotted = ".".join(chain[:i])
            if dotted in modules or dotted in aliases.values():
                if _prod_symbol_present(ctx, dotted, chain[i]) is False:
                    return True
                break
    return False


def _dur_triggered(recs: List[Dict[str, Any]], rule: Mapping[str, Any]) -> bool:
    passed = [r for r in recs if r.get("outcome") == "passed"]
    if not passed:
        return False
    latest = max(passed, key=lambda r: (r["started"], r["session_id"]))
    prior = [r for r in passed if r["session_id"] != latest["session_id"]
             and r["duration_class"] == latest["duration_class"] and r["duration_s"] > 0]
    prior.sort(key=lambda r: (r["started"], r["session_id"]))
    prior = prior[-int(rule["min_prior"]):]
    if len(prior) < int(rule["min_prior"]):
        return False
    vals = sorted(r["duration_s"] for r in prior)
    med = vals[len(vals) // 2]
    d = latest["duration_s"]
    return d >= float(rule["ratio_over_median"]) * med and d >= float(rule["min_seconds"])


def signal_duration_regression(ctx: Context, path: str) -> SignalValue:
    """依 schema `derived.duration_regression_rule`；summary 不存在 ⇒ "unknown"。"""
    summ = _review_summary(ctx)
    if summ is None:
        return "unknown"
    rule = ctx.schema["derived"]["duration_regression_rule"]
    by_node: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for r in summ.get(path, []):
        by_node[r["nodeid"]].append(r)
    return any(_dur_triggered(recs, rule) for recs in by_node.values())


def signal_outcome_flip_same_fingerprint(ctx: Context, path: str) -> SignalValue:
    """summary 中同 fingerprint 不同 outcome；summary 不存在 ⇒ "unknown"。"""
    summ = _review_summary(ctx)
    if summ is None:
        return "unknown"
    seen: Dict[Tuple[str, str], set] = collections.defaultdict(set)
    for r in summ.get(path, []):
        seen[(r["nodeid"], r["fingerprint"])].add(r["outcome"])
    return any(len(v) > 1 for v in seen.values())


def signal_collect_error(ctx: Context, path: str) -> SignalValue:
    """最近一個收集過該檔之 session 有該檔之 ledger collect_record；ledger 不存在 ⇒ "unknown"。"""
    led = _review_ledger(ctx)
    if led is None:
        return "unknown"
    hit = led.get(path)
    return bool(hit and hit[2])


def _owner_status(ctx: Context, owner: str) -> SignalValue:
    if "review_fact_keys" not in ctx.extra:
        try:
            fk = json.loads((ctx.repo_root / FACT_KEYS_REL).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            fk = {}
        ctx.extra["review_fact_keys"] = fk if isinstance(fk, dict) else {}
    fk = ctx.extra["review_fact_keys"]
    statuses: List[str] = []
    for blk, prefix in (("handoff-pending", "HP-"), ("roadmap-status", "RM-")):
        b = fk.get(blk)
        if not isinstance(b, dict):
            continue
        try:
            iid, ist = b["columns"].index("識別碼"), b["columns"].index("狀態")
        except (KeyError, ValueError):
            continue
        statuses += [r[ist] for r in b.get("rows", []) if isinstance(r, list) and len(r) > max(iid, ist)
                     and r[iid] == prefix + owner]
    if not statuses:
        return "unknown"
    return any(s == "已完成" for s in statuses)


def signal_allowed_red_owner_closed(ctx: Context, path: str) -> SignalValue:
    """該檔之 allowed_red.json 列之 owner_ticket 於 scripts/fact_keys.json 已完成（查表規則見 SPEC Task 2.1）。"""
    if "review_allowed_red" not in ctx.extra:
        try:
            rows = json.loads((ctx.repo_root / ALLOWED_RED_REL).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            rows = []
        ctx.extra["review_allowed_red"] = rows if isinstance(rows, list) else []
    owners = sorted({r.get("owner_ticket") for r in ctx.extra["review_allowed_red"] if isinstance(r, dict)
                     and isinstance(r.get("node"), str) and _file_of(r["node"]) == path
                     and isinstance(r.get("owner_ticket"), str)})
    if not owners:
        return False
    vals = [_owner_status(ctx, o) for o in owners]
    if any(v is True for v in vals):
        return True
    return "unknown" if any(v == "unknown" for v in vals) else False


def signal_quarantine_expired(ctx: Context, path: str) -> SignalValue:
    """該 entry 有 quarantine 之 expires 早於今日（V11 反例）。"""
    e = _entries(ctx).get(path)
    today = _today()
    return isinstance(e, dict) and any(isinstance(q, dict) and isinstance(q.get("expires"), str) and q["expires"] < today
                                       for q in e.get("quarantine") or [])


# ── Task 2.2：impact ─────────────────────────────────────────────────────────────────────────────────


class _ImportGraph:
    """受驗之樹（repo_root 之工作樹）內 .py 模組之匯入圖：每模組只解析一次，直接相依含函式內 import、星號匯入、
    `importlib.import_module`／`__import__` 之字串常值目標；套件之 `__init__.py` 依 Python 匯入語意一併納入。
    指向 repo 內頂層目錄而模組檔不存在者（例：已刪之生產模組）以其應有路徑（`a/b.py`）記為成員，使「已刪之變更檔」
    仍可由閉包找到匯入它之測試。"""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.tree = _Tree(self.root, "worktree")
        self.files = set(self.tree.files())
        self.top_dirs = {f.split("/", 1)[0] for f in self.files if "/" in f}
        self.dirs = {f.rsplit("/", 1)[0] for f in self.files if "/" in f}
        self.dirs |= {d.rsplit("/", i)[0] for d in list(self.dirs) for i in range(1, d.count("/") + 1)}
        self._deps: Dict[str, FrozenSet[str]] = {}
        self._closure: Dict[str, FrozenSet[str]] = {}
        self._parsed: Dict[str, Optional[ast.Module]] = {}

    def parsed(self, path: str) -> Optional[ast.Module]:
        if path not in self._parsed:
            src = self.tree.read(path)
            try:
                self._parsed[path] = _parse(src) if src is not None else None
            except SyntaxError:
                self._parsed[path] = None
        return self._parsed[path]

    def _module_targets(self, parts: Sequence[str], ghost: bool) -> List[str]:
        out: List[str] = []
        for i in range(1, len(parts) + 1):
            base = "/".join(parts[:i])
            if base + "/__init__.py" in self.files:
                out.append(base + "/__init__.py")
            elif base + ".py" in self.files:
                out.append(base + ".py")
            elif base in self.dirs:
                continue  # namespace package
            else:
                if ghost and i == len(parts) and parts[0] in self.top_dirs:
                    out.append(base + ".py")
                break
        return out

    def _abs_parts(self, here: str, module: Optional[str], level: int) -> Optional[List[str]]:
        if not level:
            return module.split(".") if module else None
        base = here.split("/")[:-1]
        if level - 1 > len(base):
            return None
        base = base[:len(base) - (level - 1)]
        return base + (module.split(".") if module else [])

    def deps(self, path: str) -> FrozenSet[str]:
        if path in self._deps:
            return self._deps[path]
        tree = self.parsed(path)
        out: set = set()
        for n in ast.walk(tree) if tree is not None else ():
            if isinstance(n, ast.Import):
                for al in n.names:
                    out.update(self._module_targets(al.name.split("."), ghost=True))
            elif isinstance(n, ast.ImportFrom):
                parts = self._abs_parts(path, n.module, n.level)
                if not parts:
                    continue
                out.update(self._module_targets(parts, ghost=bool(n.module)))
                for al in n.names:
                    if al.name != "*":
                        sub = "/".join([*parts, al.name])
                        for cand in (sub + "/__init__.py", sub + ".py"):
                            if cand in self.files:
                                out.add(cand)
                                break
            elif isinstance(n, ast.Call) and _last_name(n.func) in ("import_module", "__import__") and n.args \
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str) \
                    and not n.args[0].value.startswith("."):
                out.update(self._module_targets(n.args[0].value.split("."), ghost=False))
        out.discard(path)
        self._deps[path] = frozenset(out)
        return self._deps[path]

    def closure(self, start: str) -> FrozenSet[str]:
        if start not in self._closure:
            seen = {start}
            stack = [start]
            while stack:
                cur = stack.pop()
                for d in self.deps(cur):
                    if d not in seen:
                        seen.add(d)
                        stack.append(d)
            self._closure[start] = frozenset(seen)
        return self._closure[start]

    def is_dynamic(self, path: str) -> bool:
        """schema `impact.domain_rule` 之 dyn_modules：含 importlib.import_module 或 __import__ 且第一參數非字串常值。"""
        tree = self.parsed(path)
        if tree is None:
            return False
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and _last_name(n.func) in ("import_module", "__import__") and n.args \
                    and not (isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                return True
        return False


_IMPORT_GRAPHS: Dict[str, _ImportGraph] = {}


def _import_graph(root: Path) -> _ImportGraph:
    """impact 呼叫期間共用之匯入圖（impact 結束即丟棄；impact 以外之呼叫每次新建，不沿用舊樹內容）。"""
    key = str(Path(root).resolve())
    return _IMPORT_GRAPHS.get(key) or _ImportGraph(Path(root).resolve())


def _conftest_chain(files: set, test_path: str) -> List[str]:
    parts = test_path.split("/")[:-1]
    out = ["conftest.py"] if "conftest.py" in files else []
    for i in range(1, len(parts) + 1):
        cand = "/".join(parts[:i]) + "/conftest.py"
        if cand in files:
            out.append(cand)
    return out


def _name_refs(node: ast.AST) -> set:
    """節點引用之名稱：Name、Attribute 屬性名、參數名（fixture 請求）、字串常值（usefixtures 字面）。"""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.add(n.value)
    return out


def _import_node_targets(graph: _ImportGraph, path: str, n: ast.AST) -> List[str]:
    if isinstance(n, ast.Import):
        return [t for al in n.names for t in graph._module_targets(al.name.split("."), ghost=True)]
    parts = graph._abs_parts(path, n.module, n.level)
    if not parts:
        return []
    out = graph._module_targets(parts, ghost=bool(n.module))
    for al in n.names:
        sub = "/".join([*parts, al.name])
        out += [c for c in (sub + "/__init__.py", sub + ".py") if c in graph.files][:1]
    return out


def _module_def_reach(graph: _ImportGraph, path: str) -> Dict[str, Tuple[FrozenSet[str], set, bool]]:
    """conftest／外掛模組之頂層定義 → (可達 repo 模組, 引用名, autouse)。可達＝定義本體內之 import 目標、本體引用之
    模組層匯入名之目標、同模組被引用定義之可達（不動點），各取 import_closure（含函式內 import）；並含本模組。"""
    cache = graph.__dict__.setdefault("_def_reach", {})
    if path in cache:
        return cache[path]
    tree = graph.parsed(path)
    binds: Dict[str, List[str]] = collections.defaultdict(list)
    defs: Dict[str, ast.AST] = {}

    def visit(body: Sequence[ast.stmt]) -> None:
        for n in body:
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for al in n.names:
                    if al.name != "*":
                        local = al.asname or al.name.split(".")[0]
                        binds[local] += _import_node_targets(graph, path, n)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs[n.name] = n
            elif isinstance(n, (ast.If, ast.Try, ast.With)):
                for b in ("body", "orelse", "finalbody"):
                    visit(getattr(n, b, []) or [])
                for h in getattr(n, "handlers", []) or []:
                    visit(h.body)

    visit(tree.body if tree is not None else [])
    own: Dict[str, set] = {}
    refs: Dict[str, set] = {}
    for name, d in defs.items():
        refs[name] = _name_refs(d)
        mods = {path}
        for n in ast.walk(d):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                mods.update(_import_node_targets(graph, path, n))
        for r in refs[name] & set(binds):
            mods.update(binds[r])
        own[name] = mods
    changed = True
    while changed:
        changed = False
        for name in defs:
            for r in refs[name] & set(defs):
                if not own[r] <= own[name]:
                    own[name] |= own[r]
                    changed = True
    out = {}
    for name, d in defs.items():
        acc: set = set()
        for m in own[name]:
            acc |= graph.closure(m)
        out[name] = (frozenset(acc), refs[name], _fixture_info(d)[1])
    cache[path] = out
    return out


def _module_index(graph: _ImportGraph, path: str) -> Tuple[Dict[str, List[Tuple[str, Optional[str]]]],
                                                             Dict[str, List[ast.AST]]]:
    """模組層（含模組層 if／try／with 區塊）：匯入名 → [(被匯入之 repo 模組檔, 被匯入名；整個模組為 None)]；
    頂層 def／class 與模組層賦值目標名 → 其全部綁定節點。同名多次綁定（重綁、條件綁定）取全部之聯集（v42，修訂審查
    r40 CODEX-R40-P1-02：hook 執行時取最後綁定，聯集為其保守超集，不依敘述順序推斷）。"""
    cache = graph.__dict__.setdefault("_module_index", {})
    if path in cache:
        return cache[path]
    tree = graph.parsed(path)
    binds: Dict[str, List[Tuple[str, Optional[str]]]] = collections.defaultdict(list)
    defs: Dict[str, List[ast.AST]] = collections.defaultdict(list)

    def visit(body: Sequence[ast.stmt]) -> None:
        for n in body:
            if isinstance(n, ast.Import):
                for al in n.names:
                    tg = graph._module_targets(al.name.split("."), ghost=True)
                    # `import a.b as c` ⇒ c 指 a.b；`import a.b` ⇒ a 可經屬性取到 a 與 a.b（皆計）
                    binds[al.asname or al.name.split(".")[0]] += [(t, None) for t in (tg[-1:] if al.asname else tg)]
            elif isinstance(n, ast.ImportFrom):
                parts = graph._abs_parts(path, n.module, n.level)
                tg = graph._module_targets(parts, ghost=bool(n.module)) if parts else []
                for al in n.names:
                    if al.name == "*" or not parts:
                        continue
                    sub = "/".join([*parts, al.name])
                    sub_f = next((c for c in (sub + "/__init__.py", sub + ".py") if c in graph.files), None)
                    if sub_f:
                        binds[al.asname or al.name].append((sub_f, None))
                    elif tg:
                        binds[al.asname or al.name].append((tg[-1], al.name))
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs[n.name].append(n)
            elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    for x in ast.walk(t):
                        if isinstance(x, ast.Name):
                            defs[x.id].append(n)
            elif isinstance(n, (ast.If, ast.Try, ast.With, ast.For, ast.AsyncFor, ast.While)):
                for b in ("body", "orelse", "finalbody"):
                    visit(getattr(n, b, []) or [])
                for h in getattr(n, "handlers", []) or []:
                    visit(h.body)

    visit(tree.body if tree is not None else [])
    cache[path] = (binds, defs)
    return cache[path]


def _hook_reach(graph: _ImportGraph, path: str, name: str) -> FrozenSet[str]:
    """hook（及其引用之定義）之定義層可達：自 (path, name) 起，定義本體內之 import 目標取 import_closure；本體引用之
    同模組定義／模組層賦值遞移；引用之模組層匯入名——被匯入者為定義則遞移進該模組之該定義（只計其本體，不計該模組
    其他定義之函式內 import）、為整個模組則取其 import_closure。經過之定義所在檔皆計入。被匯入模組之模組層程式碼
    屬 import 期（失敗即全部測試失敗，任一被選測試即察覺），不另計。名稱解析不到（星號匯入、動態）⇒ 該模組之
    import_closure（保守）。"""
    seen: set = set()
    files: set = set()
    mods: set = set()
    stack: List[Tuple[str, str]] = [(path, name)]
    while stack:
        p, n = stack.pop()
        if (p, n) in seen:
            continue
        seen.add((p, n))
        files.add(p)
        binds, defs = _module_index(graph, p)
        nodes = defs.get(n, [])
        for tp, attr in binds.get(n, ()):  # 名稱亦（或只）由匯入綁定：一併追
            stack.append((tp, attr)) if attr else mods.add(tp)
        if not nodes and n not in binds:
            mods.add(p)
            continue
        for node in nodes:
            for x in ast.walk(node):
                if isinstance(x, (ast.Import, ast.ImportFrom)):
                    mods.update(_import_node_targets(graph, p, x))
            for r in _name_refs(node):
                if r in defs and r != n:
                    stack.append((p, r))
                for tp, attr in binds.get(r, ()):
                    stack.append((tp, attr)) if attr else mods.add(tp)
    out = set(files)
    for m in mods:
        out |= graph.closure(m)
    return frozenset(out)


def _reach_parts(root: Path, graph: _ImportGraph, test_path: str) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    """(測試檔與 fixture 可達, hook 可達)。前者＝自身之 import_closure（經具名縫）∪ 目錄鏈上 conftest.py（含 repo 根）
    與其 `pytest_plugins` 所列模組中，測試檔以名稱請求（參數、usefixtures 字面）或 autouse 之定義及其遞移依賴之可達；
    後者＝同一範圍內全部 `pytest_*` hook 之 `_hook_reach`（hook 套用於其作用範圍內全部測試）。未被請求之非 hook
    定義不計（不影響該測試之結果）。"""
    cache = graph.__dict__.setdefault("_reach", {})
    if test_path not in cache:
        acc = set(_seam("import_closure")(root, test_path))
        hooks: set = set()
        pool: Dict[str, List[Tuple[FrozenSet[str], set, bool]]] = collections.defaultdict(list)
        for cf in _conftest_chain(graph.files, test_path):
            for mod in [cf, *[p for p in _plugin_paths(graph.tree, cf) if p in graph.files]]:
                for name, info in _module_def_reach(graph, mod).items():
                    pool[name].append(info)
                    if name.startswith("pytest_"):
                        hooks |= _hook_reach(graph, mod, name)
        tree = graph.parsed(test_path)
        want = (_name_refs(tree) if tree is not None else set()) & set(pool)
        want |= {n for n, infos in pool.items() if any(i[2] for i in infos)}
        todo, seen = list(want), set()
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            for mods, refs, _ in pool[n]:
                acc |= mods
                todo += [r for r in refs & set(pool) if r not in seen]
        cache[test_path] = (frozenset(acc), frozenset(hooks))
    return cache[test_path]


def _reach(root: Path, graph: _ImportGraph, test_path: str) -> FrozenSet[str]:
    """`_reach_parts` 兩者之聯集（tests/ helper、domain 用）。"""
    tf, hk = _reach_parts(root, graph, test_path)
    return tf | hk


def _gate_module():
    """`scripts/framepath_affected_gate.py`（static_taint 之 `_TaintGraph`）；已載入者沿用。"""
    for name in ("scripts.framepath_affected_gate", "framepath_affected_gate"):
        if name in sys.modules:
            return sys.modules[name]
    p = Path(__file__).resolve().parent / "framepath_affected_gate.py"
    if not p.is_file():
        raise TestregError(f"USAGE impact: 缺 {p.name}（static_taint 之 _TaintGraph）")
    spec = importlib.util.spec_from_file_location("framepath_affected_gate", p)
    mod = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        sys.modules["framepath_affected_gate"] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = old
    return mod


def _string_taint(graph: _ImportGraph, tests: Sequence[str], substrings: Tuple[str, ...]) -> set:
    """`framepath_affected_gate._TaintGraph`（ffact 關閉、符號表空、字串子字串＝變更生產檔之模組名與路徑）：測試檔
    或其經 tests/ 輔助模組、conftest fixture 傳遞之定義含指名變更檔之字串（`mock.patch("momentum.x.f")`、以路徑讀原始
    碼、以子行程執行腳本等不經 import 之依賴），或測試檔模組層字串含之。"""
    if not substrings:
        return set()
    gate = _gate_module()

    def source_of(p: str) -> Optional[str]:
        return graph.tree.read(p) if graph.parsed(p) is not None else None

    tg = gate._TaintGraph(source_of, frozenset(), False, substrings)
    out = set()
    for t in tests:
        tree = graph.parsed(t)
        if tree is None:
            continue
        if any(s in r for r in gate.refs_of(tree) for s in substrings) or any(tg.reasons_of(t).values()):
            out.add(t)
            continue
        test_refs = gate.refs_of(tree)
        for cf in _conftest_chain(graph.files, t):
            if graph.parsed(cf) is not None and set(gate._tainted_names(tg.reasons_of(cf))) & test_refs:
                out.add(t)
                break
    return out


def _schema_scope_prefix(value: str, root_all: str) -> Optional[str]:
    """shared_test_infra 之值：「全部測試檔」⇒ ""（全部）；「X 下全部測試檔」⇒ X。"""
    if value == root_all:
        return ""
    if value.endswith(" 下" + root_all):
        return value[:-len(" 下" + root_all)]
    return None


def _tomb_index(tombstones: Iterable[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {t["nodeid"]: t for t in tombstones if isinstance(t, Mapping) and isinstance(t.get("nodeid"), str)}


def resolve_tomb_items(items: Sequence[str], tombstones: Iterable[Mapping[str, Any]],
                       exists=None) -> Tuple[List[str], List[Dict[str, Any]]]:
    """schema `impact.gate_feed` 第一步之碑解析（純函式）：items 為 nodeid 或測試檔路徑。nodeid（參數化以函式層比對）
    已立碑 ⇒ 以 `replaced_by` 遞迴取代（循環 ⇒ TestregError）、E0 無 replaced_by ⇒ 除去；路徑有碑而該檔已不存在
    （`exists(path)` 為假）⇒ 以其各碑 replaced_by 之所在檔取代、仍存在 ⇒ 保留並加上取代者所在檔。回傳
    (解析後之 items〔保序去重〕, 解析紀錄 [{"from", "to", "evidence_level"}]〔每碑一列〕)。"""
    idx = _tomb_index(tombstones)
    rows: Dict[str, Dict[str, Any]] = {}

    def node(n: str, stack: Tuple[str, ...]) -> List[str]:
        base = re.sub(r"\[.*\]$", "", n)
        tb = idx.get(base)
        if tb is None:
            return [n]
        if base in stack:
            raise TestregError(f"USAGE 碑循環：{' → '.join(stack + (base,))}")
        rows.setdefault(base, {"from": base, "to": list(tb.get("replaced_by") or []),
                               "evidence_level": tb.get("evidence_level")})
        out: List[str] = []
        for r in tb.get("replaced_by") or []:
            out += node(r, stack + (base,))
        return out

    resolved: List[str] = []
    for it in items:
        if "::" in it:
            resolved += node(it, ())
            continue
        tbs = sorted(b for b in idx if b.split("::")[0] == it)
        repl = [p.split("::")[0] for b in tbs for p in node(b, ())]
        alive = exists(it) if exists is not None else True
        resolved += ([it] if alive or not tbs else []) + repl
    return list(dict.fromkeys(resolved)), [rows[k] for k in sorted(rows)]


def previously_failed_from_summary(repo_root: Path) -> List[str]:
    """`previously_failed`：summary 中各 nodeid 依 started 最近一筆之 outcome∈{failed, error, xpassed} 者（排序）；
    summary 不存在或不合法（同記錄器 read_summary）⇒ []。"""
    s = load_schema(repo_root)
    try:
        obj = json.loads((Path(repo_root) / s["summary"]["path"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(obj, dict) or obj.get("schema_version") != s["version"] or obj.get("k") != s["summary"]["k"] \
            or _seam("validate_shape")(obj, s["summary"]["shape"], s):
        return []
    out = []
    for nid, recs in obj["nodes"].items():
        if recs and max(recs, key=lambda r: (r["started"], r["session_id"]))["outcome"] in ("failed", "error", "xpassed"):
            out.append(nid)
    return sorted(out)


def impact(repo_root: Path, changed_paths: List[str], must_resolved: List[str],
           previously_failed: List[str], production_taint: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """schema `impact`＋`gate_wiring` 之簽名：catalog、schema、AST 與測試檔集合一律自 repo_root 讀取；
    回傳 {"selected": [{"path", "reasons"}], "excluded": [{"path", "excluded_reason"}]}；schema `impact.precheck_rules`
    任一不符 ⇒ TestregError（不輸出；未登記之測試檔不拒跑而依 registry_unresolved 選入）；已立碑之檔依
    `impact.tombstoned_rule`；不存在使 selected 為空之分支。

    各來源（schema `enums.select_reason`）：must＝must_resolved 所在檔；changed_test＝變更之測試檔；static_taint＝變更之
    非測試 .py（tests/ 外）——測試檔與其 fixture 可達者（`_reach_parts` 前者）∪ `_TaintGraph` 字串傳遞命中者 ∪ hook
    可達者（`_reach_parts` 後者），及 tests/ 下 helper 模組（非 shared_test_infra）之變更——`_reach` 含該模組者；
    previously_failed＝其 nodeid 所在檔；registry_unresolved＝`impact.registry_unresolved_rule` 五條。
    `production_taint=False`（schema `impact.production_taint`；FRAMEPATH 閘之呼叫）⇒ 省略源自 tests/ 外 .py 變更之
    「測試檔與 fixture 可達」與字串傳遞兩者，hook 可達、domain、helper 與其餘來源照常。各來源皆空 ⇒ TestregError；
    來源非空而全部落在已刪或已立碑之檔 ⇒ 改選全部（未立碑之）測試檔、理由 registry_unresolved（不輸出空集合）。"""
    root = Path(repo_root).resolve()
    ctx = build_context(root, "worktree")
    s = ctx.schema
    precheck: List[Finding] = []
    for rid in s["impact"]["precheck_rules"]:
        precheck += _seam(f"rule_{rid.lower()}")(ctx)
    if precheck:
        raise TestregError(f"CATALOG impact 前置驗證不符（{len(precheck)} 項）：{precheck[0].render()}")
    key = str(root)
    _IMPORT_GRAPHS[key] = graph = _ImportGraph(root)
    try:
        return _impact_select(root, ctx, graph, changed_paths, must_resolved, previously_failed, production_taint)
    finally:
        _IMPORT_GRAPHS.pop(key, None)


def _impact_select(root: Path, ctx: Context, graph: _ImportGraph, changed_paths: Sequence[str],
                   must_resolved: Sequence[str], previously_failed: Sequence[str],
                   production_taint: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    s = ctx.schema
    pat = s["formats"]["test_path"]
    tests = sorted(f for f in graph.files if re.fullmatch(pat, f))
    entries = _entries(ctx)
    changed = sorted({p for p in changed_paths if isinstance(p, str) and p})
    src: Dict[str, set] = {r: set() for r in s["enums"]["select_reason"]}
    src["must"] |= {n.split("::")[0] for n in must_resolved}
    src["previously_failed"] |= {n.split("::")[0] for n in previously_failed}
    substrings: List[str] = []
    for p in changed:
        if re.fullmatch(pat, p):
            src["changed_test"].add(p)
            if p not in entries:
                src["registry_unresolved"].add(p)
            continue
        scope = _seam("shared_infra_scope")(root, p, tests)
        if scope is not None:
            src["registry_unresolved"] |= set(scope)
            continue
        if not p.endswith(".py") or p.split("/")[-1] == "conftest.py":  # conftest 只依 shared_test_infra
            continue
        if p.startswith("tests/"):
            src["static_taint"] |= {t for t in tests if p in _reach(root, graph, t)}
            continue
        src["static_taint"] |= {t for t in tests if p in _reach_parts(root, graph, t)[1]}  # hook 可達：恆計
        if production_taint:
            src["static_taint"] |= {t for t in tests if p in _reach_parts(root, graph, t)[0]}
            dotted = p[:-3].replace("/", ".")
            substrings += [p, dotted[:-len(".__init__")] if dotted.endswith(".__init__") else dotted]
        if p in graph.files and (graph.parsed(p) is None or graph.is_dynamic(p)):
            prefix = _seam("domain_prefix")(p)
            if "dyn_modules" not in ctx.extra:
                ctx.extra["dyn_modules"] = frozenset(f for f in graph.files if f.endswith(".py") and graph.is_dynamic(f))
            dyn = ctx.extra["dyn_modules"]
            dom = {t for t in tests if any(m.startswith(prefix + "/") or prefix == "" for m in _reach(root, graph, t))
                   or _reach(root, graph, t) & dyn}
            src["registry_unresolved"] |= dom if dom else set(tests)
    src["static_taint"] |= _string_taint(graph, tests, tuple(dict.fromkeys(substrings)))
    combined = _seam("combine_sources")({k: sorted(v) for k, v in src.items()})
    if not combined:
        raise TestregError("USAGE impact: 各來源皆空（must、變更、previously_failed 皆無），不輸出空集合")
    funcs = {t: _function_nodeids(graph.tree, t) for t in tests}
    tomb_paths = {tb["nodeid"].split("::")[0] for tb in _tombs(ctx) if isinstance(tb.get("nodeid"), str)}
    tomb_files = {t for t in tests if not funcs[t] and t in tomb_paths}
    selected = {f: r for f, r in combined.items() if f in set(tests) and f not in tomb_files}
    if not selected:
        selected = {t: ["registry_unresolved"] for t in tests if t not in tomb_files}
        if not selected:
            raise TestregError("USAGE impact: 受驗之樹無未立碑之測試檔，不輸出空集合")
    excluded = []
    for t in tests:
        if t not in selected:
            why = "tombstoned" if t in tomb_files else "not_collected" if not funcs[t] else "outside_changed_dependency"
            excluded.append({"path": t, "excluded_reason": why})
    return {"selected": [{"path": f, "reasons": list(selected[f])} for f in sorted(selected)], "excluded": excluded}


def combine_sources(sources: Mapping[str, Iterable[str]]) -> Dict[str, List[str]]:
    """{select_reason: 檔集合} → {檔: 排序後之理由清單}（聯集）。"""
    out: Dict[str, set] = collections.defaultdict(set)
    for reason, files in sources.items():
        for f in files:
            out[f].add(reason)
    return {f: sorted(r) for f, r in sorted(out.items())}


def domain_prefix(path: str) -> str:
    """schema `impact.domain_rule` 之 prefix(f)：f 所在目錄之前兩層目錄（層＝目錄層，不含檔名；不足兩層取一層；
    repo 根層之檔為空字串）。"""
    return "/".join(path.split("/")[:-1][:2])


def import_closure(repo_root: Path, test_path: str) -> FrozenSet[str]:
    """schema `impact.domain_rule` 之 import_closure(t)：repo 內模組之遞移閉包（含函式內 import、星號匯入、
    套件 __init__ 之 re-export），以 repo 相對 .py 路徑表示。"""
    return _import_graph(repo_root).closure(test_path)


def shared_infra_scope(repo_root: Path, changed_path: str, tests: Iterable[str]) -> Optional[FrozenSet[str]]:
    """schema `impact.shared_test_infra`：changed_path 屬共用基礎設施 ⇒ 其作用範圍內之測試檔集合；否則 None。
    鍵以 `/` 結尾者為前綴；含 `<dir>` 者為樣板（`<dir>` 對應一或多層目錄，值中同名代入）；值「全部測試檔」或
    「X 下全部測試檔」（皆讀自 schema）。"""
    table = load_schema(repo_root)["impact"]["shared_test_infra"]
    all_word = table.get("conftest.py") or next(iter(table.values()))
    tests = list(tests)
    for key, value in table.items():
        sub: Dict[str, str] = {}
        if "<dir>" in key:
            m = re.fullmatch(re.escape(key).replace(re.escape("<dir>"), r"(?P<dir>.+)"), changed_path)
            if not m:
                continue
            sub["<dir>"] = m.group("dir")
        elif key.endswith("/"):
            if not changed_path.startswith(key):
                continue
        elif changed_path != key:
            continue
        for k, v in sub.items():
            value = value.replace(k, v)
        prefix = _schema_scope_prefix(value, all_word)
        if prefix is None:
            raise TestregError(f"SCHEMA impact.shared_test_infra[{key}] 之值不可解析：{value}")
        return frozenset(t for t in tests if not prefix or t.startswith(prefix.rstrip("/") + "/"))
    return None


def _manifest_rows(manifest: Mapping[str, Any]) -> List[str]:
    rows = (manifest.get("batch_card") or {}).get("risk_mitigation") if isinstance(manifest, Mapping) else None
    return [r for r in rows if isinstance(r, str)] if isinstance(rows, list) else []


def must_from_manifest(repo_root: Path, manifest: Mapping[str, Any], phase: int) -> List[str]:
    """CLI impact 用：manifest 須含 `affected_tests phase=<phase> ` 列（否則 TestregError）；回傳 `affected_must
    phase=<phase> ` 列之 nodeid 經碑解析（schema `impact.gate_feed` 第一步）後之結果。"""
    rows = _manifest_rows(manifest)
    if not any(r.startswith(f"affected_tests phase={phase} ") for r in rows):
        raise TestregError(f"MANIFEST 缺 affected_tests phase={phase} 列")
    hits = [r for r in rows if r.startswith(f"affected_must phase={phase} ")]
    if len(hits) > 1:
        raise TestregError(f"MANIFEST 重複 affected_must phase={phase} 列")
    must = [p for p in hits[0][len(f"affected_must phase={phase} "):].split() if p] if hits else []
    cat = load_catalog(repo_root)
    return resolve_tomb_items(must, cat.get("tombstones", []))[0]


def _changed_from(root: Path, spec: str) -> List[str]:
    """CLI `--changed-from`：`worktree`＝相對 HEAD 之 diff ∪ 未追蹤檔；`A..B`＝兩提交之 diff；其餘＝該 rev 至工作樹之
    diff ∪ 未追蹤檔。"""
    out: set = set()
    if spec == "worktree":
        out |= set(_changed_paths(root, "worktree"))
    elif ".." in spec:
        a, b = spec.split("..", 1)
        out |= {p for p in _git_out(root, "diff", "--name-only", "--no-renames", a, b).splitlines() if p}
    else:
        out |= {p for p in _git_out(root, "diff", "--name-only", "--no-renames", spec).splitlines() if p}
        out |= {p for p in _git_out(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if p}
    return sorted(out)


def _cli_impact(root: Path, changed_from: str, manifest_rel: str, phase: int) -> Dict[str, Any]:
    try:
        manifest = json.loads((root / manifest_rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TestregError(f"MANIFEST {manifest_rel}: 不存在或不可解析") from exc
    must = _seam("must_from_manifest")(root, manifest, phase)
    return _seam("impact")(root, _changed_from(root, changed_from), must, previously_failed_from_summary(root))


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
        elif args.cmd == "review":
            sys.stdout.write(json.dumps(_seam("review")(root), ensure_ascii=False, sort_keys=True) + "\n")
        elif args.cmd == "impact":
            sys.stdout.write(json.dumps(_cli_impact(root, args.changed_from, args.manifest, args.phase),
                                        ensure_ascii=False, sort_keys=True) + "\n")
        else:
            raise TestregError(f"USAGE {args.cmd}: 第 2 批以後實作")
    except TestregError as exc:
        sys.stderr.write(str(exc).splitlines()[0] + "\n")
        return 2
    for f in findings:
        sys.stderr.write(f.render() + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    _rc = main(sys.argv[1:])
    sys.stdout.flush()
    sys.stderr.flush()
    # 略過直譯器拆解：大規模檢查持有之語法樹於正常結束時逐一釋放，真實規模 autouse 外掛移除（8,563 個測試函式）實測多耗
    # 約 2.6 秒（審碼 r1 CODEX-R1-P1-02 之計時）；輸出已 flush、檔案寫入皆於 with／write_text 內完成，無 atexit 收尾需求
    os._exit(_rc)
