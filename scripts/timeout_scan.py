"""NOCAP Task 0.2／0.2b③（docs/NOCAP_SPEC.md）：全庫逾時／期限樣式掃描——測試期（tests/registry/test_timeout_registry.py）
與 pre-commit（`--staged`，讀暫存區完整內容）共用之單一實作；Python／shell 樣式唯一來源 `scripts/timeout_patterns.json`、
白名單 `scripts/timeout_registry.json`。

用法：`python3 scripts/timeout_scan.py [--repo R] [--staged]`（rc 0＝全部命中皆已登記且非 A 類；1＝有未登記或登記為 A 類）。
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
PATTERNS = REPO / "scripts" / "timeout_patterns.json"
REGISTRY = REPO / "scripts" / "timeout_registry.json"
#: 掃描範圍（SPEC Task 0.2）：Python／shell 走 AST＋文字樣式，`config/` 走 YAML／JSON 鍵，`frontend/` 走 TS／JS 文字樣式。
SCAN_ROOTS = ("scripts", "momentum", "api", "tests", "handoffs/run_receipts", "config", "frontend")
EXCLUDED_DIRS = ("node_modules", ".next", "__pycache__", ".git", "playwright-report", "test-results")
CODE_SUFFIXES = (".py", ".sh")
CONFIG_SUFFIXES = (".yaml", ".yml", ".json")
FRONTEND_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
#: `config/` 之逾時鍵（YAML `key:`／JSON `"key":`）
CONFIG_KEY = re.compile(r"""^\s*["']?(\w*timeout\w*|deadline\w*|\w+_seconds)["']?\s*:""", re.I)
#: 前端之逾時／期限樣式（SPEC Task 0.2：請求逾時、AbortController、輪詢次數上限、期限比較、放棄分支）
FRONTEND_PATTERNS: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("fe_abort", re.compile(r"\bAbortController\b|\bAbortSignal\.timeout\b")),
    ("fe_timeout_key", re.compile(r"\b\w*[Tt]imeout\s*:")),
    ("fe_settimeout_abort", re.compile(r"setTimeout\([^)]*abort")),
    ("fe_poll_cap", re.compile(r"\bmax(Attempts|Polls|Retries|PollCount)\b|\bMAX_(ATTEMPTS|POLLS|RETRIES)\b")),
    ("fe_deadline_compare", re.compile(r"Date\.now\(\)\s*-")),
    ("fe_giveup", re.compile(r"took too long|did not complete within|Error\([^)]*[Tt]imeout")),
)
#: 呼叫之逾時參數名
TIMEOUT_KWARGS = ("timeout", "timeout_seconds", "max_seconds", "deadline")


@dataclass(frozen=True)
class Hit:
    """一處逾時／期限樣式命中：`function` 為所在函式全名（模組層 `<module>`；非 Python 為空字串）、
    `callee` 為被呼叫者（非呼叫之字串型命中為空字串）、`literal` 為逾時參數之字面值。"""
    path: str
    line: int
    pattern_id: str
    function: str
    callee: str
    literal: str
    text: str


_PATTERN_CACHE: Dict[Tuple[str, float], Tuple[Tuple[str, ...], List[Tuple[str, "re.Pattern[str]"]]]] = {}


def _load_patterns(path: Path = PATTERNS) -> Tuple[Tuple[str, ...], List[Tuple[str, "re.Pattern[str]"]]]:
    key = (str(path), path.stat().st_mtime)  # 同一行程內只讀一次（檔變更則重讀）
    if key not in _PATTERN_CACHE:
        raw = json.loads(path.read_text(encoding="utf-8"))
        _PATTERN_CACHE[key] = (tuple(raw["suffixes"]), [(p["id"], re.compile(p["regex"])) for p in raw["patterns"]])
    return _PATTERN_CACHE[key]


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _src(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001 — 舊版 Python 無 unparse
        return ""


class _Index(ast.NodeVisitor):
    """每一行之所在函式全名與覆蓋該行之呼叫（被呼叫者、逾時字面值）。"""

    def __init__(self) -> None:
        self.stack: List[str] = []
        self.func_of_line: Dict[int, str] = {}
        self.calls: List[Tuple[int, int, str, str]] = []  # (起行, 迄行, 被呼叫者, 逾時字面值)
        self.strings: Dict[int, List[Tuple[int, int]]] = {}  # 各行之字串字面區間（欄位；取自 AST，免另跑 tokenize）

    def _visit_scope(self, node: Any) -> None:
        self.stack.append(node.name)
        qual = ".".join(self.stack)
        for ln in range(node.lineno, (getattr(node, "end_lineno", None) or node.lineno) + 1):
            self.func_of_line[ln] = qual
        self.generic_visit(node)
        self.stack.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _visit_scope

    def _string_span(self, node: Any) -> None:
        end_l = getattr(node, "end_lineno", None) or node.lineno
        end_c = getattr(node, "end_col_offset", None)
        for r in range(node.lineno, end_l + 1):
            self.strings.setdefault(r, []).append((node.col_offset if r == node.lineno else 0,
                                                   end_c if (r == end_l and end_c is not None) else 10 ** 9))

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, (str, bytes)):
            self._string_span(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:  # f-string 整段視為字串
        self._string_span(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _dotted(node.func)
        literal = next((_src(kw.value) for kw in node.keywords if kw.arg in TIMEOUT_KWARGS and kw.value is not None), "")
        if not literal and node.args and name.split(".")[-1] in ("alarm", "wait_for"):
            literal = _src(node.args[-1] if name.endswith("wait_for") else node.args[0])
        self.calls.append((node.lineno, getattr(node, "end_lineno", None) or node.lineno, name, literal))
        self.generic_visit(node)


def _string_spans(text: str) -> Dict[int, List[Tuple[int, int]]]:
    """各行之字串字面區間（欄位）；tokenize 失敗 ⇒ 空。"""
    spans: Dict[int, List[Tuple[int, int]]] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.STRING:
                (sr, sc), (er, ec) = tok.start, tok.end
                for r in range(sr, er + 1):
                    spans.setdefault(r, []).append((sc if r == sr else 0, ec if r == er else 10 ** 9))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return {}
    return spans


def _scan_python(path: str, text: str, patterns: Sequence[Tuple[str, "re.Pattern[str]"]]) -> List[Hit]:
    try:
        tree: Optional[ast.AST] = ast.parse(text)
    except SyntaxError:
        tree = None
    index = _Index()
    if tree is not None:
        index.visit(tree)
        strings = index.strings  # AST 欄位為 UTF-8 位元組偏移
        byte_offsets = True
    else:  # 語法錯誤之檔：退回 tokenize 取字串區間（字元偏移）
        strings = _string_spans(text)
        byte_offsets = False
    hits: List[Hit] = []
    for n, line in enumerate(text.splitlines(), start=1):
        for pid, rx in patterns:
            m = rx.search(line)
            if not m:
                continue
            # AST 之欄位為 UTF-8 位元組偏移、正則為字元偏移：換算後比較（同行有非 ASCII 字串時兩者不同；b1 審碼 r4 P1-01）
            pos = len(line[:m.start()].encode("utf-8")) if byte_offsets else m.start()
            in_string = any(a <= pos < b for a, b in strings.get(n, []))
            callee, literal = "", ""
            if not in_string:
                covering = [c for c in index.calls if c[0] <= n <= c[1]]
                if covering:  # 最內層（範圍最小、起行最晚）之呼叫
                    c = min(covering, key=lambda c: (c[1] - c[0], -c[0]))
                    callee, literal = c[2], c[3]
            hits.append(Hit(path, n, pid, index.func_of_line.get(n, "<module>"), callee, literal, line))
            break
    if tree is not None:
        lines = text.splitlines()
        for ln in _bounded_polls(tree):
            line = lines[ln - 1] if 0 < ln <= len(lines) else ""
            hits.append(Hit(path, ln, "bounded_poll", index.func_of_line.get(ln, "<module>"), "", "", line))
    return hits


# ---- 「次數×睡眠」形之時間上限（bounded_poll；2026-11-13 TESTSEL I2 補洞：正則看不到不含時間字樣之上限）------------
#: 以呼叫此名之函式為「失敗」（pytest.fail、self.fail、fail）
_FAIL_CALLS = frozenset({"fail"})
_CONST_CALLS = frozenset({"int", "round", "ceil", "floor", "max", "min", "abs"})


def _int_consts(tree: ast.AST) -> set:
    """檔內綁定為數值字面（或常數運算式）之名、以及預設值為數值字面之參數名（迭代界改名／區域常數之繞過）。"""
    names: set = set()
    changed = True
    while changed:  # 常數間接（N = 5; M = N * 2）至不動點
        changed = False
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None:
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if _is_const_expr(n.value, names):
                    for t in targets:
                        if isinstance(t, ast.Name) and t.id not in names:
                            names.add(t.id)
                            changed = True
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = n.args.args + n.args.kwonlyargs
                defaults = ([None] * (len(n.args.args) - len(n.args.defaults)) + list(n.args.defaults)
                            + list(n.args.kw_defaults))
                for a, d in zip(args, defaults):
                    if d is not None and _is_const_expr(d, names) and a.arg not in names:
                        names.add(a.arg)
                        changed = True
    return names


def _is_const_expr(node: ast.AST, consts: set) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    if isinstance(node, ast.Name):
        return node.id in consts or (node.id.isupper() and len(node.id) > 1)
    if isinstance(node, ast.Attribute):
        return node.attr.isupper() and len(node.attr) > 1
    if isinstance(node, ast.UnaryOp):
        return _is_const_expr(node.operand, consts)
    if isinstance(node, ast.BinOp):
        return _is_const_expr(node.left, consts) and _is_const_expr(node.right, consts)
    if isinstance(node, ast.Call):
        name = _dotted(node.func).split(".")[-1]
        return name in _CONST_CALLS and bool(node.args) and all(_is_const_expr(a, consts) for a in node.args)
    return False


def _walk_local(nodes: Sequence[ast.AST]) -> Any:
    """走訪敘述（不進巢狀函式／類別／lambda）。"""
    stack = list(nodes)
    while stack:
        n = stack.pop()
        yield n
        for c in ast.iter_child_nodes(n):
            if not isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                stack.append(c)


def _has_sleep(body: Sequence[ast.AST]) -> bool:
    return any(isinstance(n, ast.Call) and _dotted(n.func).split(".")[-1] == "sleep" for n in _walk_local(body))


def _is_fail_stmt(st: ast.AST) -> bool:
    """迴圈耗盡後之失敗：raise、assert 恆假（False／0／None）、呼叫 fail（pytest.fail／self.fail）。"""
    if isinstance(st, ast.Raise):
        return True
    if isinstance(st, ast.Assert):
        return isinstance(st.test, ast.Constant) and not st.test.value
    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
        return _dotted(st.value.func).split(".")[-1] in _FAIL_CALLS
    return False


def _counter_while(st: ast.While, consts: set) -> bool:
    """`while n < N:`／`while n <= N:`／`while N > n:`／`while n > 0:`（倒數），本體改該計數名（+=／-=／重新賦值）。"""
    t = st.test
    if not (isinstance(t, ast.Compare) and len(t.ops) == 1 and len(t.comparators) == 1):
        return False
    left, op, right = t.left, t.ops[0], t.comparators[0]
    if isinstance(op, (ast.Lt, ast.LtE)) and isinstance(left, ast.Name) and _is_const_expr(right, consts):
        var = left.id
    elif isinstance(op, (ast.Gt, ast.GtE)) and isinstance(right, ast.Name) and _is_const_expr(left, consts):
        var = right.id
    elif isinstance(op, (ast.Gt, ast.GtE, ast.NotEq)) and isinstance(left, ast.Name) and _is_const_expr(right, consts):
        var = left.id  # 倒數：while n > 0
    else:
        return False
    for n in _walk_local(st.body):
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == var:
            return True
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == var for x in n.targets):
            return True
    return False


def _counter_names(loop: ast.AST) -> set:
    """迴圈之計數名：for 之目標名（任何可迭代，如 itertools.count／range／enumerate），及本體內 `n += c`／`n = n ± c` 者。"""
    names: set = set()
    if isinstance(loop, (ast.For, ast.AsyncFor)):
        for t in ast.walk(loop.target):
            if isinstance(t, ast.Name):
                names.add(t.id)
    for n in _walk_local(loop.body):
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            names.add(n.target.id)
        elif isinstance(n, ast.Assign) and isinstance(n.value, ast.BinOp):
            for t in n.targets:
                if isinstance(t, ast.Name) and any(isinstance(x, ast.Name) and x.id == t.id for x in ast.walk(n.value)):
                    names.add(t.id)
    return names


def _cmp_counter_const(test: ast.AST, counters: set, consts: set) -> bool:
    """條件式比較某計數名與常數（含 and／or、not 內之比較）。"""
    for n in ast.walk(test):
        if isinstance(n, ast.Compare):
            sides = [n.left, *n.comparators]
            if any(isinstance(s, ast.Name) and s.id in counters for s in sides) and \
                    any(_is_const_expr(s, consts) for s in sides if not (isinstance(s, ast.Name) and s.id in counters)):
                return True
    return False


def _fail_branch(st: ast.AST) -> bool:
    """失敗出口敘述：直接失敗，或 `if …:` 之本體（或 else）含直接失敗（例：迴圈後 `if not done: raise`）。"""
    if _is_fail_stmt(st):
        return True
    return isinstance(st, ast.If) and any(_is_fail_stmt(s) for s in [*st.body, *st.orelse])


def _loop_cap(st: ast.AST, consts: set) -> Tuple[bool, bool]:
    """（迭代界為常數或以計數與常數比較之條件退出, 迴圈本體內以計數條件直接失敗）。"""
    counters = _counter_names(st)
    bounded = False
    if isinstance(st, (ast.For, ast.AsyncFor)):
        it = st.iter
        bounded = (isinstance(it, ast.Call) and _dotted(it.func) == "range" and bool(it.args)
                   and all(_is_const_expr(a, consts) for a in it.args))
    elif isinstance(st, ast.While):
        bounded = _counter_while(st, consts) or _cmp_counter_const(st.test, counters, consts)
    inner_fail = False
    for n in _walk_local(st.body):
        if isinstance(n, ast.If) and _cmp_counter_const(n.test, counters, consts):
            exits = [*n.body, *n.orelse]
            if any(isinstance(s, (ast.Break, ast.Return)) for s in exits):
                bounded = True
            if any(_is_fail_stmt(s) for s in exits):
                bounded = inner_fail = True
    return bounded, inner_fail


def _recursive_polls(tree: ast.AST, consts: set) -> List[int]:
    """直接自遞迴之輪詢（codex r1 反例 D）：函式本體含 sleep、以「參數 ± 常數」呼叫自身、且有以該參數與常數比較之
    分支直接失敗（基底情形 raise／fail）⇒ 函式定義行。"""
    out: List[int] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or not _has_sleep(fn.body):
            continue
        params = {a.arg for a in [*fn.args.args, *fn.args.kwonlyargs]}
        stepped = set()
        for n in _walk_local(fn.body):
            if isinstance(n, ast.Call) and _dotted(n.func).split(".")[-1] == fn.name:
                for a in [*n.args, *(k.value for k in n.keywords)]:
                    if isinstance(a, ast.BinOp) and isinstance(a.left, ast.Name) and a.left.id in params \
                            and _is_const_expr(a.right, consts):
                        stepped.add(a.left.id)
        if not stepped:
            continue
        if any(isinstance(n, ast.If) and _cmp_counter_const(n.test, stepped, consts)
               and any(_is_fail_stmt(s) for s in [*n.body, *n.orelse]) for n in _walk_local(fn.body)):
            out.append(fn.lineno)
    return out


def _bounded_polls(tree: ast.AST) -> List[int]:
    """「次數×睡眠」形之時間上限之行號。迴圈（for 任何可迭代、while）：① 本體含 sleep（time.sleep／asyncio.sleep／
    sleep）；② 迭代界為常數（`range(常數式)`、計數式 `while n < 常數`、或本體內以計數與常數比較之 if 退出〔break／return〕
    ——涵蓋 `while True` 與 `itertools.count()`）；③ 失敗出口：迴圈 else、緊接迴圈後之敘述、或迴圈後之 `if` 本體為失敗
    （raise、assert 恆假、fail()），或本體內以計數條件直接失敗。另：直接自遞迴遞減參數＋sleep＋基底失敗之函式
    （`_recursive_polls`）。只 ①② 而無失敗出口（耗盡後靜默往下）不算。"""
    consts = _int_consts(tree)
    out: List[int] = []
    for parent in ast.walk(tree):
        for field in ("body", "orelse", "finalbody", "handlers"):
            block = getattr(parent, field, None)
            if not isinstance(block, list):
                continue
            for i, st in enumerate(block):
                if not isinstance(st, (ast.For, ast.AsyncFor, ast.While)) or not _has_sleep(st.body):
                    continue
                bounded, inner_fail = _loop_cap(st, consts)
                if not bounded:
                    continue
                after = block[i + 1] if i + 1 < len(block) else None
                if inner_fail or any(_is_fail_stmt(s) for s in st.orelse) or (after is not None and _fail_branch(after)):
                    out.append(st.lineno)
    out += _recursive_polls(tree, consts)
    return sorted(set(out))


def _scan_lines(path: str, text: str, patterns: Sequence[Tuple[str, "re.Pattern[str]"]]) -> List[Hit]:
    hits = []
    for n, line in enumerate(text.splitlines(), start=1):
        for pid, rx in patterns:
            if rx.search(line):
                hits.append(Hit(path, n, pid, "", "", "", line))
                break
    return hits


def scan_text(path: str, text: str) -> List[Hit]:
    """依副檔名與所在根目錄掃描單一檔內容（repo 相對路徑 `path`）。"""
    suffixes, patterns = _load_patterns()
    if path.startswith("config/") and path.endswith(CONFIG_SUFFIXES):
        return _scan_lines(path, text, [("config_timeout_key", CONFIG_KEY)])
    if path.startswith("frontend/") and path.endswith(FRONTEND_SUFFIXES):
        return _scan_lines(path, text, FRONTEND_PATTERNS)
    if path.endswith(".py"):
        return _scan_python(path, text, patterns)
    if path.endswith(tuple(s for s in suffixes if s != ".py")):
        return _scan_lines(path, text, patterns)
    return []


def _in_scope(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in EXCLUDED_DIRS for p in parts):
        return False
    if rel.startswith("config/"):
        return rel.endswith(CONFIG_SUFFIXES)
    if rel.startswith("frontend/"):
        return rel.endswith(FRONTEND_SUFFIXES)
    if rel.startswith("handoffs/run_receipts/"):  # 只掃探針目錄（`*_probes/`）之程式
        return rel.endswith(CODE_SUFFIXES) and len(parts) >= 4 and parts[2].endswith("_probes")
    return parts[0] in SCAN_ROOTS and rel.endswith(CODE_SUFFIXES)


def scan_repo(repo: Path = REPO, roots: Sequence[str] = SCAN_ROOTS) -> List[Hit]:
    """掃描 `roots` 下全部檔（排除 `EXCLUDED_DIRS`）。"""
    hits: List[Hit] = []
    for root in roots:
        base = repo / root
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            rel = p.relative_to(repo).as_posix()
            if not p.is_file() or not _in_scope(rel):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            hits.extend(scan_text(rel, text))
    return hits


def scan_staged(repo: Path = REPO) -> List[Hit]:
    """pre-commit：對每個暫存之受掃描檔讀暫存區內容（`git show :<path>`）跑 `scan_text`。"""
    names = subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                           capture_output=True, text=True, check=True).stdout.split()
    hits: List[Hit] = []
    for rel in names:
        if not _in_scope(rel):
            continue
        show = subprocess.run(["git", "-C", str(repo), "show", f":{rel}"], capture_output=True, text=True)
        if show.returncode == 0:
            hits.extend(scan_text(rel, show.stdout))
    return hits


def _binding_key(h: Hit) -> Tuple[str, str, str, str, str]:
    return (h.pattern_id, h.function, h.callee, h.literal, h.text.strip())


def new_vs_head(repo: Path, hits: Sequence[Hit]) -> List[Hit]:
    """相對 HEAD 之新命中：以綁定（樣式、所在函式、被呼叫者、字面值、整行）之多重集合差判定——同一行搬到另一函式
    或改綁亦算新（b1 審碼 r1 CODEX-R1-P1-02）。HEAD 無此檔 ⇒ 全部為新。"""
    by_path: Dict[str, List[Hit]] = {}
    for h in hits:
        by_path.setdefault(h.path, []).append(h)
    out: List[Hit] = []
    for rel, staged_hits in by_path.items():
        head = subprocess.run(["git", "-C", str(repo), "show", f"HEAD:{rel}"], capture_output=True, text=True)
        remaining: Dict[Tuple[str, str, str, str, str], int] = {}
        for h in (scan_text(rel, head.stdout) if head.returncode == 0 else []):
            remaining[_binding_key(h)] = remaining.get(_binding_key(h), 0) + 1
        for h in staged_hits:
            k = _binding_key(h)
            if remaining.get(k, 0) > 0:
                remaining[k] -= 1
            else:
                out.append(h)
    return out


ALLOWED_CLASSES = {"B", "C", "D"}
#: whole_file（整檔放行）只准守衛、掃描器本身與其測試
WHOLE_FILE_OK = {"scripts/timeout_write_guard.py", "tests/governance/test_timeout_write_guard.py",
                 "scripts/timeout_scan.py"}


def validate_registry(entries: Sequence[Mapping[str, Any]]) -> None:
    """任一列 class 不屬 B／C／D、缺理由或 path、綁定不恰為一種（whole_file／function＋callee＋literal／line）、或
    whole_file 而非守衛／掃描器本身 ⇒ ValueError（整份無效；守衛與 pre-commit 共用，b1 審碼 r1 CODEX-R1-P1-03）。"""
    for e in entries:
        if e.get("class") not in ALLOWED_CLASSES:
            raise ValueError(f"登記檔列 class={e.get('class')!r} 不允許（只准 B／C／D；長運算之時間上限＝A 類不可登記）：{e}")
        if not str(e.get("reason") or "").strip() or not e.get("path"):
            raise ValueError(f"登記檔列缺 path 或理由：{e}")
        kinds = [bool(e.get("whole_file")), all(k in e for k in ("function", "callee", "literal")), "line" in e]
        if sum(kinds) != 1:
            raise ValueError(f"登記檔列須恰一種綁定（whole_file／function＋callee＋literal／line）：{e}")
        if e.get("whole_file") and e.get("path") not in WHOLE_FILE_OK:
            raise ValueError(f"登記檔列 whole_file（整檔放行）只准守衛、掃描器本身與其測試：{e}")


def load_registry(path: Path = REGISTRY, text: Optional[str] = None) -> List[Dict[str, Any]]:
    """讀登記檔並驗證（`text` 給定時以之為內容，供 pre-commit 讀暫存版）。"""
    entries = list(json.loads(text if text is not None else path.read_text(encoding="utf-8"))["entries"])
    validate_registry(entries)
    return entries


def registered(hit: Hit, registry: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """白名單比對：Python 呼叫型命中須 path＋function＋callee＋literal 全等；其餘（shell、config、frontend、Python 字串型）
    須 path＋去頭尾空白整行相等；`whole_file` 列（守衛本身、掃描器與其測試）放行該檔全部命中。"""
    for e in registry:
        if e.get("path") != hit.path:
            continue
        if e.get("whole_file"):
            return dict(e)
        if hit.callee and "function" in e:
            if (e.get("function"), e.get("callee"), str(e.get("literal", ""))) == (hit.function, hit.callee, hit.literal):
                return dict(e)
        elif "line" in e and e["line"] == hit.text.strip():
            return dict(e)
    return None


def unregistered(hits: Sequence[Hit], registry: Sequence[Mapping[str, Any]]) -> List[Hit]:
    """未登記或登記為 A 類之命中。"""
    out = []
    for h in hits:
        e = registered(h, registry)
        if e is None or e.get("class") == "A":
            out.append(h)
    return out


PENDING = REPO / "scripts" / "timeout_pending_nocap.json"
PENDING_FIELDS = ("path", "pattern_id", "function", "callee", "literal", "text", "line_hint", "nocap_task", "category")
PENDING_CATEGORIES = ("產品碼", "腳本", "探針", "測試")


def load_pending(path: Path = PENDING, text: Optional[str] = None) -> List[Dict[str, Any]]:
    """NOCAP 未施工之既有命中棘輪清單（`scripts/timeout_pending_nocap.json`）：每列欄位恰為 `PENDING_FIELDS`、
    `nocap_task` 非空（docs/NOCAP_SPEC.md 之 Task 編號）、`category` 屬 `PENDING_CATEGORIES`；任一不符 ⇒ ValueError。"""
    entries = list(json.loads(text if text is not None else path.read_text(encoding="utf-8"))["entries"])
    for e in entries:
        if not isinstance(e, dict) or set(e) != set(PENDING_FIELDS):
            raise ValueError(f"pending 列欄位須恰為 {PENDING_FIELDS}：{e}")
        if not isinstance(e["nocap_task"], str) or not e["nocap_task"].strip():
            raise ValueError(f"pending 列缺 nocap_task（須指向 NOCAP 已定義之 Task）：{e}")
        if e["category"] not in PENDING_CATEGORIES:
            raise ValueError(f"pending 列 category 不屬 {PENDING_CATEGORIES}：{e}")
    return entries


def _pending_key(path: str, pattern_id: str, function: str, callee: str, literal: str, text: str) -> Tuple[str, ...]:
    return (path, pattern_id, function, callee, str(literal), text.strip())


def ratchet(hits: Sequence[Hit], registry: Sequence[Mapping[str, Any]],
            pending: Sequence[Mapping[str, Any]]) -> Tuple[List[Hit], List[Dict[str, Any]]]:
    """棘輪（業界 baseline 做法）：(未登記且不在 pending 之命中＝新增, pending 中已無對應命中之列＝已修好須移出)。
    比對以綁定（path、樣式、所在函式、被呼叫者、字面值、去頭尾空白整行）之多重集合，不用行號。"""
    left: Dict[Tuple[str, ...], List[Dict[str, Any]]] = {}
    for e in pending:
        k = _pending_key(e["path"], e["pattern_id"], e["function"], e["callee"], e["literal"], e["text"])
        left.setdefault(k, []).append(dict(e))
    new: List[Hit] = []
    for h in unregistered(hits, registry):
        k = _pending_key(h.path, h.pattern_id, h.function, h.callee, h.literal, h.text)
        if left.get(k):
            left[k].pop()
        else:
            new.append(h)
    stale = [e for rows in left.values() for e in rows]
    return new, stale


def stale_entries(registry: Sequence[Mapping[str, Any]], hits: Sequence[Hit],
                  repo: Path = REPO) -> List[Dict[str, Any]]:
    """登記檔中已無對應命中之列（防漂移）；`whole_file` 列以檔存在為準。"""
    out = []
    for e in registry:
        if e.get("whole_file"):
            if not (repo / str(e.get("path"))).is_file():
                out.append(dict(e))
            continue
        same_path = [h for h in hits if h.path == e.get("path")]
        if not any(registered(h, [e]) is not None for h in same_path):
            out.append(dict(e))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="NOCAP 逾時／期限樣式掃描")
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--staged", action="store_true", help="只掃暫存區（pre-commit）")
    ap.add_argument("--json", action="store_true", help="以 JSON 印未登記之命中（盤點用）")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    try:
        if args.staged:  # pre-commit 讀暫存版登記檔（同提交改登記檔亦須合格）
            show = subprocess.run(["git", "-C", str(repo), "show", ":scripts/timeout_registry.json"],
                                  capture_output=True, text=True)
            registry = load_registry(text=show.stdout) if show.returncode == 0 else load_registry()
        else:
            registry = load_registry(repo / "scripts" / "timeout_registry.json")
    except (OSError, ValueError, KeyError) as exc:
        print(f"🔴 timeout_scan（NOCAP）：登記檔無效 ⇒ 擋：{exc}", file=sys.stderr)
        return 1
    hits = scan_staged(repo) if args.staged else scan_repo(repo)
    stale: List[Dict[str, Any]] = []
    if args.staged:  # pre-commit：以完整內容判綁定、只對相對 HEAD 之新綁定報錯（既有寫法由全庫登記與測試期掃描管）
        hits = new_vs_head(repo, hits)
    else:
        stale = stale_entries(registry, hits, repo)
    missing = unregistered(hits, registry)
    for e in stale:
        print(f"過期登記（已無對應命中）：{json.dumps(e, ensure_ascii=False)}", file=sys.stderr)
    if args.json:
        print(json.dumps([h.__dict__ for h in missing], ensure_ascii=False, indent=1))
    else:
        for h in missing:
            print(f"{h.path}:{h.line}: [{h.pattern_id}] {h.text.strip()}", file=sys.stderr)
    if missing:
        print(f"🔴 timeout_scan（NOCAP）：{len(missing)} 處逾時／期限寫法未登記或屬 A 類（依牆鐘停止或縮減運算，"
              f"須改經共用監看）；等外部方或短輔助命令之保險於 scripts/timeout_registry.json 登記 B／C／D 並附理由",
              file=sys.stderr)
        return 1
    if stale:
        print(f"🔴 timeout_scan（NOCAP）：{len(stale)} 列過期登記（防漂移：刪除或改綁定）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
