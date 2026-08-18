"""GAP-1 Task 2.4 — 策略層 wiring 閘門（契約 ↔ `report.py`／`strategy_validation/*.py` 封閉集合比對；AST，不用 regex）。

規則（A1-11／A1-17；只做語法層「無條件路徑」判定，不做 CFG／可達性推導）：
  W1  契約 `report_sections` 節名集合 ⊆ `build_validation_section` **函式頂層**組裝之 dict 字面鍵（`assembled`）
  W2  契約 `reasons` 每值須出現於 `strategy_validation/*.py` 之某個 `ast.Constant`（死枚舉即紅）
  W3  三形之 reason 字面（`reason=<Const>` keyword／Assign／AnnAssign；`{"reason": <Const>}`；`<x含reason> == <Const>`）
      ⊆ 契約 `reasons`；非 Constant 之動態值 ⇒ `[unresolved]` 且 rc=1（fail-closed）
  W4  契約 `eligibility_keys` 九鍵 ⊆ `eligibility` 節之頂層組裝鍵集合
🔴 凡條件／迴圈／try／with 內之組裝一律不計入（`if False:` 內寫滿節名 ⇒ 不足 ⇒ rc=1）；註解／docstring／死分支不造成假綠。
exit：0 全綠／1 任一規則違反／2 缺契約、缺 report.py、語法錯、找不到目標函式。
用法：venv/bin/python scripts/strategy_wiring_check.py [--contract <json>] [--pkg <dir>]（旗標供測試覆寫，禁 env）。
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = REPO / "momentum" / "Analysis" / "contracts" / "strategy_validation_contract.json"
DEFAULT_PKG = REPO / "momentum" / "Analysis" / "strategy_validation"
TARGET_FUNC = "build_validation_section"

_CONDITIONAL = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncFor, ast.AsyncWith)


def _dict_literal_keys(node: ast.AST) -> Optional[Set[str]]:
    """`ast.Dict` 之字面鍵集合（任一鍵非 str Constant ⇒ None，視為不可判定）。"""
    if not isinstance(node, ast.Dict):
        return None
    keys: Set[str] = set()
    for k in node.keys:
        if k is None:  # {**x}
            return None
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            keys.add(k.value)
        else:
            return None
    return keys


def _top_level_statements(func: ast.FunctionDef) -> List[ast.stmt]:
    """函式頂層 statement（不深入 If／For／While／Try／With 之 body）。"""
    return list(func.body)


def collect_assembled(func: ast.FunctionDef) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """回 (頂層組裝之頂層鍵集合, {節名: 該節 dict 字面之鍵集合})。

    只認：① 頂層 `Return` 之 `ast.Dict` ② 頂層 `Assign` `name = {...}` 後 `return name`／`out["<lit>"] = …`
    ③ 頂層 `{**a, **b}` 且 a／b 皆頂層 dict 字面。巢狀節（值為 dict 字面）之鍵一併收集供 W4。
    """
    top = _top_level_statements(func)
    named_dicts: Dict[str, ast.Dict] = {}
    assembled: Set[str] = set()
    sections: Dict[str, Set[str]] = {}
    subscript_keys: Dict[str, Set[str]] = {}

    def _absorb(d: ast.Dict) -> None:
        for k, v in zip(d.keys, d.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                assembled.add(k.value)
                sub = _dict_literal_keys(v)
                if sub is not None:
                    sections.setdefault(k.value, set()).update(sub)
                elif isinstance(v, ast.Name) and v.id in named_dicts:
                    sub2 = _dict_literal_keys(named_dicts[v.id])
                    if sub2 is not None:
                        sections.setdefault(k.value, set()).update(sub2)
            elif k is None and isinstance(v, ast.Name) and v.id in named_dicts:  # {**a}
                _absorb(named_dicts[v.id])

    for stmt in top:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            tgt = stmt.targets[0]
            if isinstance(tgt, ast.Name) and isinstance(stmt.value, ast.Dict):
                named_dicts[tgt.id] = stmt.value
            elif (
                isinstance(tgt, ast.Subscript)
                and isinstance(tgt.value, ast.Name)
                and isinstance(tgt.slice, ast.Constant)
                and isinstance(tgt.slice.value, str)
            ):
                subscript_keys.setdefault(tgt.value.id, set()).add(tgt.slice.value)
                sub = _dict_literal_keys(stmt.value)
                if sub is not None:
                    sections.setdefault(tgt.slice.value, set()).update(sub)
        elif isinstance(stmt, ast.Return) and stmt.value is not None:
            if isinstance(stmt.value, ast.Dict):
                _absorb(stmt.value)
            elif isinstance(stmt.value, ast.Name):
                name = stmt.value.id
                if name in named_dicts:
                    _absorb(named_dicts[name])
                assembled.update(subscript_keys.get(name, set()))
    return assembled, sections


def _scope_assignments(scope: ast.AST) -> Dict[str, List[ast.AST]]:
    """某作用域（函式 body 或模組頂層）內每個 Name 之 Assign／AnnAssign 來源值（**不**深入巢狀函式）。"""
    out: Dict[str, List[ast.AST]] = {}

    def _visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue  # 巢狀作用域另計
            if isinstance(child, ast.Assign):
                for t in child.targets:
                    if isinstance(t, ast.Name):
                        out.setdefault(t.id, []).append(child.value)
            elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name) and child.value is not None:
                out.setdefault(child.target.id, []).append(child.value)
            _visit(child)

    _visit(scope)
    return out


class _Scope:
    """passthrough 判定用之作用域：函式參數集合＋函式內指派＋模組頂層 str 常數（函式內同名指派**遮蔽**模組常數）。"""

    def __init__(self, params: Set[str], local_assigns: Dict[str, List[ast.AST]], module_consts: Dict[str, str]):
        self.params = params
        self.local_assigns = local_assigns
        self.module_consts = module_consts


def _is_passthrough(node: ast.AST, scope: _Scope, depth: int = 0) -> bool:
    """「傳遞既有 reason 值」之**封閉白名單**（A1-24；B4 review N1 收窄）：
    ① `<x>.reason`（Attribute 且 attr=="reason"）② `<x>["reason"]`（Subscript 且 slice 為 Constant "reason"）
    ③ `<x>.get("reason", <合規>)`（首參數為 Constant "reason"）④ `A if c else B`（兩支皆合規）
    ⑤ `Name`：為該函式參數、或同**函式作用域**內所有指派來源皆合規、或（未在函式內指派時）為模組頂層 str 常數。
    其餘（任意 Attribute／Subscript／其他 Call／JoinedStr／BinOp／跨檔別名）⇒ 非 passthrough ⇒ `[unresolved]` rc=1。"""
    if depth > 8:
        return False
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) or node.value is None
    if isinstance(node, ast.Attribute):
        return node.attr == "reason"
    if isinstance(node, ast.Subscript):
        return isinstance(node.slice, ast.Constant) and node.slice.value == "reason"
    if isinstance(node, ast.IfExp):
        return _is_passthrough(node.body, scope, depth + 1) and _is_passthrough(node.orelse, scope, depth + 1)
    if isinstance(node, ast.Call):
        f = node.func
        if (
            isinstance(f, ast.Attribute)
            and f.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "reason"
        ):
            return all(_is_passthrough(a, scope, depth + 1) for a in node.args[1:])
        return False
    if isinstance(node, ast.Name):
        if node.id in scope.local_assigns:
            return all(_is_passthrough(s, scope, depth + 1) for s in scope.local_assigns[node.id])
        if node.id in scope.params:
            return True
        return node.id in scope.module_consts
    return False


def _module_str_consts(tree: ast.AST) -> Dict[str, str]:
    consts: Dict[str, str] = {}
    if isinstance(tree, ast.Module):
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    consts[stmt.targets[0].id] = stmt.value.value
    return consts


def _reason_literals(tree: ast.AST) -> Tuple[Set[str], List[str]]:
    """三形之 reason 字面（逐作用域解析）；非 Constant 且非 passthrough ⇒ unresolved 清單（fail-closed）。"""
    found: Set[str] = set()
    unresolved: List[str] = []
    module_consts = _module_str_consts(tree)
    scopes: List[Tuple[ast.AST, _Scope]] = [(tree, _Scope(set(), _scope_assignments(tree), module_consts))]
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
            if fn.args.vararg:
                params.add(fn.args.vararg.arg)
            if fn.args.kwarg:
                params.add(fn.args.kwarg.arg)
            scopes.append((fn, _Scope(params, _scope_assignments(fn), module_consts)))
    for scope_node, scope in scopes:
        _collect_reason_sites(scope_node, scope, found, unresolved)
    return found, unresolved


def _own_nodes(scope_node: ast.AST):
    """該作用域**自身**之節點（不含巢狀函式／類別內部）。"""
    stack = [scope_node]
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if child is not scope_node and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            stack.append(child)


def _resolve_name_literal(name: str, scope: _Scope) -> Optional[str]:
    """`Name` 可解析為單一 str 字面時回該字面（同函式內所有指派皆為同值 Constant；否則模組頂層常數且未被遮蔽／非參數）。"""
    if name in scope.local_assigns:
        vals = {s.value for s in scope.local_assigns[name] if isinstance(s, ast.Constant) and isinstance(s.value, str)}
        if len(vals) == 1 and len(scope.local_assigns[name]) == 1:
            return next(iter(vals))
        return None
    if name in scope.params:
        return None
    return scope.module_consts.get(name)


def _collect_reason_sites(scope_node: ast.AST, scope: _Scope, found: Set[str], unresolved: List[str]) -> None:
    def _take(node: ast.AST, where: str) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value:  # 空字串 = 無 reason，允許
                found.add(node.value)
        elif isinstance(node, ast.Constant):
            pass
        elif isinstance(node, ast.IfExp):
            _take(node.body, where)
            _take(node.orelse, where)
        elif isinstance(node, ast.Name) and _resolve_name_literal(node.id, scope) is not None:
            lit = _resolve_name_literal(node.id, scope)
            if lit:
                found.add(lit)
        elif _is_passthrough(node, scope):
            pass
        else:
            unresolved.append(f"{where}:L{getattr(node, 'lineno', '?')}:{type(node).__name__}")

    for node in _own_nodes(scope_node):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "reason":
                    _take(kw.value, "kw")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "reason" for t in targets):
                if getattr(node, "value", None) is not None:
                    _take(node.value, "assign")
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "reason":
                    _take(v, "dict")
        elif isinstance(node, ast.Compare):
            left_src = ast.dump(node.left)
            if "reason" in left_src and len(node.comparators) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                comp = node.comparators[0]
                if isinstance(comp, ast.Constant):
                    if isinstance(comp.value, str) and comp.value:
                        found.add(comp.value)
                # 非 Constant 之比較（如 reason in contract["reasons"]）不屬三形，不列 unresolved


def _used_module_const_values(tree: ast.AST) -> Set[str]:
    """W2 之「已接線」第二形：模組頂層 str 常數之值，且該常數名於同檔**被引用**（Name Load，非其指派本身）。
    只出現於 docstring／從未被引用之常數 ⇒ **不**算接線（B4 review N1／CODEX-R18-P2-06）。"""
    consts = _module_str_consts(tree)
    loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return {v for name, v in consts.items() if name in loaded}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    ap.add_argument("--pkg", default=str(DEFAULT_PKG))
    args = ap.parse_args(argv)
    contract_path = Path(args.contract)
    pkg = Path(args.pkg)

    if not contract_path.is_file():
        print(f"[strategy_wiring_check] rc=2 缺契約: {contract_path}", file=sys.stderr)
        return 2
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[strategy_wiring_check] rc=2 契約 JSON 語法錯: {exc}", file=sys.stderr)
        return 2
    report_py = pkg / "report.py"
    if not report_py.is_file():
        print(f"[strategy_wiring_check] rc=2 缺 report.py: {report_py}", file=sys.stderr)
        return 2
    py_files = sorted(p for p in pkg.glob("*.py") if p.name != "__init__.py")
    trees: Dict[Path, ast.AST] = {}
    for p in py_files:
        try:
            trees[p] = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as exc:
            print(f"[strategy_wiring_check] rc=2 語法錯: {p}: {exc}", file=sys.stderr)
            return 2
    func = next(
        (n for n in ast.walk(trees[report_py]) if isinstance(n, ast.FunctionDef) and n.name == TARGET_FUNC), None
    )
    if func is None:
        print(f"[strategy_wiring_check] rc=2 找不到 {TARGET_FUNC}: {report_py}", file=sys.stderr)
        return 2

    failures: List[str] = []
    sections_spec = contract.get("report_sections", {})
    section_names = {k for k in sections_spec if not k.startswith("_")}
    elig_keys = set((contract.get("eligibility_keys") or {}).keys())
    reasons = list(contract.get("reasons") or [])
    if not reasons:
        failures.append("W2: 契約 reasons 為空")

    assembled, sections = collect_assembled(func)
    # W1
    missing_sections = sorted(section_names - assembled)
    if missing_sections:
        failures.append(f"W1: report_sections 未於 {TARGET_FUNC} 頂層無條件組裝: {missing_sections}（assembled={sorted(assembled)}）")
    # W4
    elig_assembled = sections.get("eligibility", set())
    missing_elig = sorted(elig_keys - elig_assembled)
    if missing_elig:
        failures.append(f"W4: eligibility_keys 未於 eligibility 節頂層組裝: {missing_elig}（assembled={sorted(elig_assembled)}）")
    # W2 / W3
    wired: Set[str] = set()  # W2「已接線」＝出現於 reason 位置（三形，經作用域解析）或為被引用之模組常數值
    reason_found: Set[str] = set()
    unresolved_all: List[str] = []
    for p, tree in trees.items():
        found, unresolved = _reason_literals(tree)
        reason_found |= found
        wired |= found | _used_module_const_values(tree)
        unresolved_all += [f"{p.name}:{u}" for u in unresolved]
    dead = sorted(r for r in reasons if r not in wired)
    if dead:
        failures.append(
            f"W2: 契約 reasons 未於 {pkg.name}/*.py 之 reason 位置或被引用常數出現（死枚舉；docstring／未用常數不算）: {dead}"
        )
    invented = sorted(r for r in reason_found if r not in reasons)
    if invented:
        failures.append(f"W3: 自創 reason 字面（不在契約 reasons）: {invented}")
    if unresolved_all:
        failures.append(f"W3: [unresolved] 動態 reason 值（fail-closed）: {unresolved_all}")

    if failures:
        for f in failures:
            print(f"[strategy_wiring_check] ✗ {f}")
        print(f"[strategy_wiring_check] rc=1（{len(failures)} 條）")
        return 1
    print(f"[strategy_wiring_check] ✓ W1..W4（sections={sorted(section_names)}；reasons={len(reasons)}；files={len(trees)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
