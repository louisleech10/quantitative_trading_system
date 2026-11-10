"""防上限 checker（ICPERF SPEC v5.85 Task 0.6 (g)，L3）。

只檢產品路徑（momentum/、api/、frontend/src/、config/）之新增或修改行，高信心規則：Field／Query 無依據之上界、
逾欄列數即拒、依資料維度降低精度、資料切片直接入統計或持久結果。固定秒數中止計算由既有 NOCAP
`timeout_write_guard` 負責，本 checker 不重複。行內豁免 `# limit-lint: allow=<rule> reason=<理由>`。
兩態：`--mode warn`（只提示）與 `--mode block`（未豁免之 high 命中或 parse_error ⇒ rc 2）。

高信心規則只對 Python（AST）判；TS／TSX、YAML、JSON 以 L0 掃描器（`scripts/limit_scan.py`）之同一語法解析取候選，
只出提示（hint）；任一語言 parse 失敗回 `parse_error`（high），不得視為「無上限」。
block 模式只阻擋語料收據（`tests/_golden/icperf/limit_lint_corpus_receipt.json`）中 status＝block 之規則與 parse_error。

入口：
- `--mode warn|block [--receipt R] [--root ROOT] <檔>...`：逐檔全文檢查。
- `--staged`：檢 git 暫存區（相對 HEAD 之新增或修改行；pre-commit 經 `scripts/git_hooks/limit_lint_staged.sh`）。
- `--hook`：PostToolUse Edit／Write 事件（stdin JSON；經 `scripts/limit_lint_hook.sh`）；以 git HEAD 版為舊版，
  只檢新增或修改行；非產品路徑或無法解析之 payload 放行。
- `--corpus-receipt <out>`：以 L0 機讀表為標註語料，對現行碼全量跑各高信心規則，寫逐規則 precision／recall 與實例。
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import limit_scan  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = REPO / "tests" / "_golden" / "icperf" / "limit_lint_corpus_receipt.json"
DEFAULT_INVENTORY = REPO / "tests" / "_golden" / "icperf" / "limit_inventory.json"
PRODUCT_PREFIXES = ("momentum/", "api/", "frontend/src/", "config/")
HIGH_RULES = ("field_upper_bound", "count_gate", "dimension_reduces_precision", "slice_into_statistic")
RECEIPT_DOC = ("ICPERF SPEC v5.85 Task 0.6 (g)：防上限 checker 逐規則語料收據。量測欄由 "
               "`venv/bin/python scripts/limit_lint.py --corpus-receipt tests/_golden/icperf/limit_lint_corpus_receipt.json` "
               "以 tests/_golden/icperf/limit_inventory.json 為標註語料對現行全部產品 .py 全量重算（命中行 needs_fix＝true 為真陽性，"
               "其餘為誤報；recall 分母為該規則所宣稱語法族之 needs_fix 列）；status 與 accept_reason 為依實例之判定，重產時沿用。")
ALLOW_RE = re.compile(r"limit-lint:\s*allow=(\w+)\s+reason=(\S.*)")

BOUND_CALLS = {"Field", "Query", "Path", "Body", "Form", "Header", "Cookie"}
UPPER_NAME = re.compile(r"(^|_)(max|limit|cap)(_|$)", re.IGNORECASE)
PRECISION_NAME = re.compile(r"^(n_|num_)?(perm|perms|permutations|boot|bootstrap|bootstraps|samples?|resamples?|iter|"
                            r"iters|iterations|trials|paths|draws|b)$", re.IGNORECASE)
STAT_METHODS = {"corr", "cov", "mean", "std", "var", "median", "quantile", "rank", "sum", "describe", "corrwith",
                "skew", "kurt", "kurtosis", "sem", "agg", "aggregate", "spearmanr", "pearsonr", "kendalltau",
                "corrcoef", "average", "percentile", "nanmean", "nanstd", "nanmedian", "nanpercentile", "ols", "fit"}
PERSIST_CALLS = {"dump", "to_csv", "to_parquet", "to_hdf", "to_json", "to_pickle", "to_feather", "to_sql", "save",
                 "savez", "savez_compressed", "write", "put", "create_dataset", "write_text", "write_bytes"}


def is_product_path(rel: str) -> bool:
    """產品路徑判定（repo 相對路徑）；測試檔不檢。"""
    rel = rel.replace(os.sep, "/")
    if not rel.startswith(PRODUCT_PREFIXES):
        return False
    parts = set(rel.split("/"))
    name = rel.rsplit("/", 1)[-1]
    if parts & {"tests", "__tests__", "__fixtures__", "node_modules"}:
        return False
    if re.search(r"\.(test|spec)\.[jt]sx?$", name) or re.match(r"(test_.*|.*_test|conftest)\.py$", name):
        return False
    return rel.endswith((".py", ".ts", ".tsx", ".json", ".yaml", ".yml"))


def _finding(rule: str, line: int, symbol: str, confidence: str, detail: str = "") -> Dict[str, Any]:
    return {"rule": rule, "line": line, "symbol": symbol, "confidence": confidence, "detail": detail}


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _is_size_expr(node: ast.AST) -> bool:
    """`len(x)`、`x.shape[k]`、`x.shape`、`x.size`：資料列欄數。"""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
        return True
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "shape":
        return True
    return isinstance(node, ast.Attribute) and node.attr in ("shape", "size")


def _bound_value(node: ast.AST) -> Tuple[bool, str]:
    """比較另一側是否為上限：數字（≥2；0、1 為空／單元素之定義域檢查）或帶 max／limit／cap 之名稱。回 (是否, 符號)。
    個位數之結構檢查（如 `len(path.parents) >= 3`）亦為 high，屬准豁免者以行內豁免附理由（r153：不以數字大小推定語意）。"""
    v = limit_scan._num(node)
    if v is not None:
        return v >= 2, str(v)
    name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""
    return bool(name) and bool(UPPER_NAME.search(name)), name


def _parents(tree: ast.AST) -> Dict[ast.AST, ast.AST]:
    out: Dict[ast.AST, ast.AST] = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            out[c] = p
    return out


def _assigned_name(node: ast.AST, parents: Dict[ast.AST, ast.AST]) -> str:
    cur = node
    while cur in parents:
        p = parents[cur]
        if isinstance(p, ast.Assign):
            t = p.targets[0]
            return t.id if isinstance(t, ast.Name) else t.attr if isinstance(t, ast.Attribute) else ""
        if isinstance(p, (ast.AnnAssign, ast.AugAssign)):
            t = p.target
            return t.id if isinstance(t, ast.Name) else t.attr if isinstance(t, ast.Attribute) else ""
        if isinstance(p, ast.stmt):
            return ""
        cur = p
    return ""


def _slice_bounds(sl: ast.AST) -> List[float]:
    """切片之數字界（上界任意；下界只計負數，即取尾段）；|v|≥2 才計。"""
    out: List[float] = []
    items = sl.elts if isinstance(sl, ast.Tuple) else [sl]
    for it in items:
        if not isinstance(it, ast.Slice):
            continue
        up = limit_scan._num(it.upper) if it.upper is not None else None
        lo = limit_scan._num(it.lower) if it.lower is not None else None
        if up is not None and abs(up) >= 2:
            out.append(up)
        if lo is not None and lo <= -2:
            out.append(lo)
    return out


def _span(node: ast.AST) -> Set[int]:
    return set(range(node.lineno, (getattr(node, "end_lineno", None) or node.lineno) + 1))


def _enclosing_stmt(node: ast.AST, parents: Dict[ast.AST, ast.AST]) -> ast.AST:
    cur = node
    while cur in parents and not isinstance(cur, ast.stmt):
        cur = parents[cur]
    return cur


def _size_compare(term: ast.AST) -> Optional[Tuple[str, str]]:
    """`len(x) > N` 類比較之方向與符號：回 ("exceeds"｜"within", 符號)；`not (…)` 翻轉方向；非上限比較回 None。"""
    negate = False
    while isinstance(term, ast.UnaryOp) and isinstance(term.op, ast.Not):
        negate, term = not negate, term.operand
    if not (isinstance(term, ast.Compare) and len(term.ops) == 1):
        return None
    left, op, right = term.left, term.ops[0], term.comparators[0]
    if _is_size_expr(left) and isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)):
        direction, other = ("exceeds" if isinstance(op, (ast.Gt, ast.GtE)) else "within"), right
    elif _is_size_expr(right) and isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)):
        direction, other = ("exceeds" if isinstance(op, (ast.Lt, ast.LtE)) else "within"), left
    else:
        return None
    ok, sym = _bound_value(other)
    if not ok:
        return None
    if negate:
        direction = "within" if direction == "exceeds" else "exceeds"
    return direction, sym


def _measured(term: ast.AST) -> Set[str]:
    """比較式中被量長度之運算式（`len(xs)` ⇒ dump(xs)；`df.shape[0]`、`x.size` ⇒ dump(df)／dump(x)）。"""
    out: Set[str] = set()
    for n in ast.walk(term):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "len" and n.args:
            out.add(ast.dump(n.args[0]))
        elif isinstance(n, ast.Attribute) and n.attr in ("shape", "size", "ndim"):
            out.add(ast.dump(n.value))
    return out


def _index_guard(branch: List[ast.stmt], measured: Set[str]) -> bool:
    """長度檢查用以保護常數索引取值（`if len(p.parents) >= 3: return p.parents[2]`、`array[:, 1]`、`parts[0]`）：
    分支之 return 值以常數整數索引取用受量物件之元素 ⇒ 該檢查為索引合法性，不是上限。只有切片（`xs[:8]` 截斷）不算。"""
    for s in branch:
        if not isinstance(s, ast.Return) or s.value is None:
            continue
        for n in ast.walk(s.value):
            if isinstance(n, ast.Subscript) and ast.dump(n.value) in measured:
                idx = n.slice.elts if isinstance(n.slice, ast.Tuple) else [n.slice]
                if any(isinstance(i, ast.Constant) and isinstance(i.value, int) for i in idx):
                    return True
    return False


def _degenerate_return(s: Optional[ast.AST]) -> bool:
    """`return`、`return None`、回傳常數或空容器——資料不足時之退化回傳。"""
    if not isinstance(s, ast.Return):
        return False
    v = s.value
    return v is None or isinstance(v, ast.Constant) or (
        isinstance(v, (ast.List, ast.Tuple, ast.Set)) and not v.elts) or (isinstance(v, ast.Dict) and not v.keys)


def _next_stmt(node: ast.stmt, parents: Dict[ast.AST, ast.AST]) -> Optional[ast.stmt]:
    """同一區塊中緊接於 node 之後之敘述。"""
    p = parents.get(node)
    if p is None:
        return None
    for field in ("body", "orelse", "finalbody"):
        block = getattr(p, field, None)
        if isinstance(block, list) and node in block:
            i = block.index(node)
            return block[i + 1] if i + 1 < len(block) else None
    return None


def _rejects(stmts: List[ast.stmt], count_returns: bool) -> List[Tuple[ast.AST, Set[int]]]:
    """分支內之拒絕或跳過敘述與其可達路徑上之條件行：raise／continue／break／sys.exit，及（count_returns 時）任何 return
    ——逾量分支提早返回即與正常路徑分流（錯誤回應、哨兵、截斷後結果皆屬之）。往下看巢狀 if（條件行計入路徑）、
    with（全部 context 運算式計入路徑）、try（body 中之 raise 若有 except 承接則不計，因例外被吞；return／continue／
    break 仍計；except、else、finally 照常）；不進入迴圈（其 break／continue 屬內層迴圈）、函式與類別。"""
    out: List[Tuple[ast.AST, Set[int]]] = []
    stack: List[Tuple[ast.AST, Set[int], bool]] = [(s, set(), False) for s in stmts]
    while stack:
        s, path, swallowed = stack.pop()
        if isinstance(s, ast.If):
            cond = path | _span(s.test)
            stack.extend((c, cond, swallowed) for c in s.body)
            stack.extend((c, cond, swallowed) for c in s.orelse)
            continue
        if isinstance(s, (ast.With, ast.AsyncWith)):
            ctx: Set[int] = set()
            for item in s.items:
                ctx |= _span(item.context_expr)
            stack.extend((c, path | ctx, swallowed) for c in s.body)
            continue
        if isinstance(s, ast.Try):
            stack.extend((c, path, swallowed or bool(s.handlers)) for c in s.body)
            for block in (s.orelse, s.finalbody, *[h.body for h in s.handlers]):
                stack.extend((c, path, swallowed) for c in block)
            continue
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and _call_name(s.value.func) in ("exit", "_exit"):
            if not swallowed:
                out.append((s, path))
            continue
        if isinstance(s, ast.Raise):
            if not swallowed:
                out.append((s, path))
            continue
        if isinstance(s, (ast.Continue, ast.Break)) or (isinstance(s, ast.Return) and count_returns):
            out.append((s, path))
    return out


def _python_high(text: str) -> List[Dict[str, Any]]:
    """四條高信心規則。每筆另帶 `lines`（判定所依之全部行號；`lint_changed` 以其與修改行之交集判是否新增或修改）。"""
    tree = ast.parse(text)
    parents = _parents(tree)
    found: List[Dict[str, Any]] = []

    def add(rule: str, line: int, sym: str, detail: str, lines: Set[int]) -> None:
        f = _finding(rule, line, sym, "high", detail)
        f["lines"] = sorted(lines | {line})
        found.append(f)

    for node in ast.walk(tree):
        # field_upper_bound：Field／Query 等之 le／lt 上界
        if isinstance(node, ast.Call) and _call_name(node.func) in BOUND_CALLS:
            for kw in node.keywords:
                if kw.arg in ("le", "lt") and kw.value is not None:
                    sym = _assigned_name(node, parents)
                    p = parents.get(node)
                    if isinstance(p, ast.arguments):
                        for a, d in zip(p.args[len(p.args) - len(p.defaults):], p.defaults):
                            if d is node:
                                sym = a.arg
                    add("field_upper_bound", kw.value.lineno, sym or kw.arg, f"{_call_name(node.func)}({kw.arg}=…)",
                        _span(node))
        # count_gate：逾列欄數即拒絕或跳過——`if len(x) > N: <拒絕>`、`if len(x) <= N: … else: <拒絕>`、
        # `assert len(x) <= N`；拒絕可在巢狀區塊；條件可為合取項或 `not (…)`（析取項之各項獨立成立，亦逐項判）
        if isinstance(node, ast.If):
            terms = node.test.values if isinstance(node.test, ast.BoolOp) else [node.test]
            for term in terms:
                sc = _size_compare(term)
                if sc is None:
                    continue
                direction, sym = sc
                # 資料足量檢查（`if len(x) >= 2: return compute(x)` 後接 `return None`）：另一路徑立即退化回傳 ⇒
                # 本分支之 return 是正常結果而非拒絕；其餘情形逾量分支之任何 return 皆為分流。
                branch = node.body if direction == "exceeds" else node.orelse
                other = node.body if direction == "within" else (node.orelse or [])
                alt_first = other[0] if other else (_next_stmt(node, parents) if direction == "exceeds" else None)
                rej = _rejects(branch, count_returns=not (_degenerate_return(alt_first)
                                                          or _index_guard(branch, _measured(term))))
                if rej:
                    lines = _span(term)
                    for r, path in rej:
                        lines |= _span(r) | path
                    add("count_gate", term.lineno, sym, "逾列欄數即拒／跳過", lines)
        if isinstance(node, ast.Assert):
            sc = _size_compare(node.test)
            if sc is not None and sc[0] == "within":
                add("count_gate", node.lineno, sc[1], "assert 列欄數上限", _span(node))
        # dimension_reduces_precision：精度參數（置換次數、bootstrap、抽樣、迭代、路徑數）除以資料維度
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv)) and _is_size_expr(node.right):
            name = _assigned_name(node, parents)
            if name and PRECISION_NAME.match(name):
                add("dimension_reduces_precision", node.lineno, name, "依資料維度縮減精度參數",
                    _span(_enclosing_stmt(node, parents)))
        # slice_into_statistic：數字切片直接入統計或持久結果
        if isinstance(node, ast.Subscript) and _slice_bounds(node.slice):
            cur, hit = node, ""
            while cur in parents:
                p = parents[cur]
                if isinstance(p, ast.Attribute) and p.value is cur:
                    if p.attr in STAT_METHODS:
                        hit = p.attr
                        break
                    cur = p
                    continue
                if isinstance(p, ast.Call):
                    nm = _call_name(p.func)
                    if p.func is cur:
                        cur = p
                        continue
                    if nm in STAT_METHODS or nm in PERSIST_CALLS:
                        hit = nm
                    break
                break
            if hit:
                add("slice_into_statistic", node.lineno, hit, f"切片後直接入 {hit}", _span(_enclosing_stmt(node, parents)))
    return found


def _hints_via_scan(rel: str, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """以 L0 掃描器之同一語法解析取候選（hint）與 parse 錯誤。"""
    suffix = Path(rel).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="limit_lint_") as td:
        p = Path(td) / ("x" + suffix)
        p.write_text(text, encoding="utf-8")
        if suffix in (".ts", ".tsx"):
            try:
                out = limit_scan.scan([p])
            except FileNotFoundError:
                return [], [_finding("ts_unavailable", 1, "", "hint", "node 不可用，TS／TSX 未檢")]
        else:
            out = limit_scan.scan([p])
    errs = [_finding("parse_error", 1, "", "high", e.get("error", "")) for e in out["errors"]]
    hints = [_finding("limit_candidate", r["line"], str(r.get("name") or r.get("value")), "hint", r.get("kind", ""))
             for r in out["rows"]]
    return hints, errs


def _allowed(line_text: str, rule: str) -> bool:
    """豁免須指定被命中之規則，理由須含至少一個文字字元（`reason=.` 不算；理由之實質由審碼判，同 eslint 之 require-description）。"""
    m = ALLOW_RE.search(line_text)
    return bool(m) and m.group(1) == rule and bool(re.search(r"[^\W_]", m.group(2)))


def lint_text(path: str, text: str) -> List[Dict[str, Any]]:
    """回命中清單，每筆 `{"rule", "line", "symbol", "confidence"}`（confidence ∈ {"high", "hint"}）。"""
    rel = str(path).replace(os.sep, "/")
    if not is_product_path(rel):
        return []
    lines = text.splitlines()
    high: List[Dict[str, Any]] = []
    if rel.endswith(".py"):
        try:
            high = _python_high(text)
        except SyntaxError as exc:
            return [_finding("parse_error", exc.lineno or 1, "", "high", str(exc))]
    hints, errs = _hints_via_scan(rel, text)
    if errs:
        return errs
    high = [f for f in high if not (0 < f["line"] <= len(lines) and _allowed(lines[f["line"] - 1], f["rule"]))]
    seen: Set[Tuple[str, int]] = set()
    out: List[Dict[str, Any]] = []
    for f in high:
        k = (f["rule"], f["line"])
        if k not in seen:
            seen.add(k)
            out.append(f)
    high_lines = {f["line"] for f in out}
    out += [h for h in hints if h["line"] not in high_lines]
    return sorted(out, key=lambda f: (f["line"], f["rule"]))


def changed_lines(old_text: str, new_text: str) -> Set[int]:
    """新版中新增或修改之行號（1 起）。"""
    sm = difflib.SequenceMatcher(a=old_text.splitlines(), b=new_text.splitlines(), autojunk=False)
    out: Set[int] = set()
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert"):
            out.update(range(j1 + 1, j2 + 1))
    return out


def lint_changed(path: str, old_text: str, new_text: str) -> List[Dict[str, Any]]:
    """只回判定所依之任一行（`lines`：比較式、拒絕敘述、整個呼叫或敘述）為新增或修改之命中（含既有常數改值、
    只改分支內容使既有比較變成拒絕）；未修改之舊違例不回。parse_error 一律回。"""
    changed = changed_lines(old_text, new_text)
    return [f for f in lint_text(path, new_text)
            if f["rule"] == "parse_error" or changed.intersection(f.get("lines", [f["line"]]))]


def load_block_rules(receipt: Path) -> Optional[Set[str]]:
    """語料收據中 status＝block 之規則。收據缺檔、不可解析、`rules` 非非空陣列或缺 rule／status ⇒ None（block 模式據此
    fail-closed，不得因收據壞掉而放行）；收據合法而無 block 規則 ⇒ 空集合（全部只提示）。"""
    try:
        rec = json.loads(Path(receipt).read_text(encoding="utf-8"))
        rules = rec["rules"]
        if not isinstance(rules, list) or not rules:
            return None
        if not all(isinstance(r, dict) and isinstance(r.get("rule"), str) and r.get("status") in ("warn", "block")
                   for r in rules):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {r["rule"] for r in rules if r["status"] == "block"}


def _report(rel: str, findings: List[Dict[str, Any]], block_rules: Optional[Set[str]], mode: str) -> bool:
    """印出命中；回是否阻擋。block_rules 為 None（收據不可用）⇒ 全部高信心命中一律阻擋（fail-closed）。"""
    blocked = False
    for f in findings:
        blocking = mode == "block" and f["confidence"] == "high" and (
            f["rule"] == "parse_error" or block_rules is None or f["rule"] in block_rules)
        blocked |= blocking
        tag = "BLOCK" if blocking else ("HIGH" if f["confidence"] == "high" else "hint")
        print(f"limit_lint [{tag}] {f['rule']} {rel}:{f['line']} {f['symbol']} {f.get('detail', '')}".rstrip(),
              file=sys.stderr)
    if blocked:
        print("limit_lint：上限寫法依 ICPERF SPEC Task 0.6 (c) 修法矩陣處理；屬數學值域、外部協定分頁、可遍歷之頁容量、"
              "F-chunk、顯示摘要、求積未收斂回報者，於該行加 `# limit-lint: allow=<rule> reason=<理由>`",
              file=sys.stderr)
    return blocked


def _rel(p: Path, root: Path) -> Optional[str]:
    try:
        return str(p.resolve().relative_to(root.resolve())).replace(os.sep, "/")
    except ValueError:
        return None


def _git_show(root: Path, spec: str) -> Optional[str]:
    res = subprocess.run(["git", "-C", str(root), "show", spec], capture_output=True)
    if res.returncode != 0:
        return None
    return res.stdout.decode("utf-8", errors="replace")


def _run_hook(root: Path, block_rules: Optional[Set[str]], mode: str) -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        fp = Path(payload["tool_input"]["file_path"])
    except (ValueError, KeyError, TypeError):
        return 0
    rel = _rel(fp, root)
    if rel is None or not is_product_path(rel) or not fp.is_file():
        return 0
    new_text = fp.read_text(encoding="utf-8", errors="replace")
    old_text = _git_show(root, f"HEAD:{rel}") or ""
    return 2 if _report(rel, lint_changed(rel, old_text, new_text), block_rules, mode) else 0


def _run_staged(root: Path, block_rules: Optional[Set[str]], mode: str) -> int:
    res = subprocess.run(["git", "-C", str(root), "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
                         capture_output=True)
    if res.returncode != 0:
        print("limit_lint：無法讀取 git 暫存區", file=sys.stderr)
        return 2
    blocked = False
    for rel in [x for x in res.stdout.decode("utf-8").split("\0") if x]:
        if not is_product_path(rel):
            continue
        new_text = _git_show(root, f":{rel}")
        if new_text is None:
            continue
        old_text = _git_show(root, f"HEAD:{rel}") or ""
        blocked |= _report(rel, lint_changed(rel, old_text, new_text), block_rules, mode)
    return 2 if blocked else 0


def build_corpus_receipt(root: Path, inventory: Dict[str, Any]) -> Dict[str, Any]:
    """以 L0 機讀表為標註語料：對 DEFAULT_ROOTS 下全部 .py 全量跑高信心規則。

    命中行於機讀表為 needs_fix＝true ⇒ 真陽性；其餘（needs_fix＝false 或非盤點候選）⇒ 誤報。
    各規則之 recall 分母＝該規則所宣稱語法族中之 needs_fix 列（族判定以該列原始碼行之語法，不依規則實作）。
    """
    rows = [r for r in inventory["rows"] if r["file"].endswith(".py")]
    label = {(r["file"], r["line"]): r for r in rows}
    hits: Dict[str, List[Tuple[str, int, str]]] = {r: [] for r in HIGH_RULES}
    for p in limit_scan._iter_default_files(root):
        if p.suffix != ".py":
            continue
        rel = _rel(p, root)
        if rel is None or not is_product_path(rel):
            continue
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        try:
            for f in _python_high(text):
                hits[f["rule"]].append((rel, f["line"], lines[f["line"] - 1].strip()[:160]))
        except SyntaxError:
            continue
    def nxt(r: Dict[str, Any]) -> str:
        return r_code(root, {"file": r["file"], "line": r["line"] + 1})

    family = {
        # Field／Query 等之 le／lt（含多行呼叫中獨立成行之 `le=…`）
        "field_upper_bound": lambda r: re.search(r"\b(" + "|".join(BOUND_CALLS) + r")\(.*\b(le|lt)\s*=", r_code(root, r))
        or re.match(r"(le|lt)\s*=", r_code(root, r)),
        # 列欄數比較且下一行即拒絕／跳過（取樣分支不屬本規則）
        "count_gate": lambda r: re.match(r"(if|elif)\b.*(len\(|\.shape|\.size).*>", r_code(root, r))
        and re.match(r"(raise|return|continue|break)\b", nxt(r)),
        "dimension_reduces_precision": lambda r: re.search(r"/\s*(len\(|\w+\.shape|\w+\.size)", r_code(root, r)),
        "slice_into_statistic": lambda r: re.search(r"\[[^\]]*:\s*-?\d+\s*\]\s*\.\s*\w+|\[\s*-\d+\s*:\s*\]",
                                                    r_code(root, r)),
    }
    out_rules = []
    for rule in HIGH_RULES:
        tp = [h for h in hits[rule] if label.get((h[0], h[1]), {}).get("needs_fix") is True]
        fp = [h for h in hits[rule] if label.get((h[0], h[1]), {}).get("needs_fix") is not True]
        fam = [r for r in rows if r["needs_fix"] and family[rule](r)]
        hit_keys = {(h[0], h[1]) for h in hits[rule]}
        fn = [(r["file"], r["line"], r_code(root, r)[:160]) for r in fam if (r["file"], r["line"]) not in hit_keys]
        n_hit = len(hits[rule])
        out_rules.append({
            "rule": rule,
            "hits": n_hit,
            "true_positives": len(tp),
            "precision": round(len(tp) / n_hit, 4) if n_hit else None,
            "family_needs_fix": len(fam),
            "recall": round((len(fam) - len(fn)) / len(fam), 4) if fam else None,
            "false_positives": [f"{f}:{ln} {c}" for f, ln, c in fp],
            "false_negatives": [f"{f}:{ln} {c}" for f, ln, c in fn],
        })
    return {"rules": out_rules}


_CODE_CACHE: Dict[Tuple[str, str], List[str]] = {}


def r_code(root: Path, r: Dict[str, Any]) -> str:
    key = (str(root), r["file"])
    if key not in _CODE_CACHE:
        p = root / r["file"]
        _CODE_CACHE[key] = p.read_text(encoding="utf-8").splitlines() if p.is_file() else []
    lines = _CODE_CACHE[key]
    return lines[r["line"] - 1].strip() if 0 < r["line"] <= len(lines) else ""


def main(argv: Any = None) -> int:
    """CLI：`limit_lint.py --mode warn|block [--receipt <語料收據>] [--root <repo 根>] <檔>...`；`--staged` 檢 git 暫存區內容
    （pre-commit 用）。block 模式只阻擋收據（預設 tests/_golden/icperf/limit_lint_corpus_receipt.json）中 status＝block 之規則。"""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("warn", "block"), default="warn")
    ap.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    ap.add_argument("--root", default=os.environ.get("LIMIT_LINT_ROOT") or str(REPO))
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--hook", action="store_true")
    ap.add_argument("--corpus-receipt", metavar="OUT")
    ap.add_argument("files", nargs="*")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if args.corpus_receipt:
        out = Path(args.corpus_receipt)
        inv = json.loads(DEFAULT_INVENTORY.read_text(encoding="utf-8"))
        rec = build_corpus_receipt(root, inv)
        # 判定欄（status、accept_reason）為人工依實例所下之結論：重產時沿用既有收據之判定，量測欄一律重算；
        # 新規則預設 warn（未判定不得阻擋）。
        prev: Dict[str, Dict[str, Any]] = {}
        if out.is_file():
            prev = {r["rule"]: r for r in json.loads(out.read_text(encoding="utf-8")).get("rules", [])}
        for r in rec["rules"]:
            p = prev.get(r["rule"], {})
            r["status"] = p.get("status", "warn")
            r["accept_reason"] = p.get("accept_reason", "待判定")
        rec = {"_doc": RECEIPT_DOC, **rec}
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    block_rules = load_block_rules(Path(args.receipt))
    if block_rules is None and args.mode == "block":
        print(f"limit_lint：語料收據不可用（{args.receipt}：缺檔、不可解析或 rules 不合規）⇒ 高信心規則一律阻擋",
              file=sys.stderr)
    if args.hook:
        return _run_hook(root, block_rules, args.mode)
    if args.staged:
        return _run_staged(root, block_rules, args.mode)
    blocked = False
    for f in args.files:
        p = Path(f)
        rel = _rel(p, root) or str(p)
        if not is_product_path(rel):
            continue
        blocked |= _report(rel, lint_text(rel, p.read_text(encoding="utf-8")), block_rules, args.mode)
    return 2 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
