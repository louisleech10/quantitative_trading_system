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


def _name_assignments(tree: ast.AST) -> Dict[str, List[ast.AST]]:
    """同檔內每個 Name 之所有 Assign／AnnAssign 來源值（供 passthrough 判定）。"""
    out: Dict[str, List[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            out.setdefault(node.target.id, []).append(node.value)
    return out


def _is_passthrough(node: ast.AST, assigns: Dict[str, List[ast.AST]], depth: int = 0) -> bool:
    """「傳遞既有 reason 值」之封閉形態（不產生新字面）：
    `x.reason`／`x["reason"]`（Attribute／Subscript）、`x.get("reason", <passthrough|Constant>)`、
    `A if c else B`（兩支皆 passthrough／Constant）、`Name`（同檔所有指派來源皆 passthrough／Constant，或未被指派＝參數）。
    JoinedStr（f-string）／BinOp／其他 Call／跨檔別名 ⇒ **非** passthrough ⇒ unresolved。"""
    if depth > 8:
        return False
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Attribute):
        return True
    if isinstance(node, ast.Subscript):
        return isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)
    if isinstance(node, ast.IfExp):
        return _is_passthrough(node.body, assigns, depth + 1) and _is_passthrough(node.orelse, assigns, depth + 1)
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "get" and node.args:
            return all(_is_passthrough(a, assigns, depth + 1) for a in node.args)
        return False
    if isinstance(node, ast.Name):
        sources = assigns.get(node.id, [])
        return all(_is_passthrough(s, assigns, depth + 1) for s in sources)  # 無指派＝參數 ⇒ True
    return False


def _reason_literals(tree: ast.AST) -> Tuple[Set[str], List[str]]:
    """三形之 reason 字面；非 Constant 且非 passthrough ⇒ unresolved 清單（fail-closed）。"""
    found: Set[str] = set()
    unresolved: List[str] = []
    assigns = _name_assignments(tree)

    def _take(node: ast.AST, where: str) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value:  # 空字串 = 無 reason，允許
                found.add(node.value)
        elif isinstance(node, ast.Constant):
            pass
        elif isinstance(node, ast.IfExp):
            _take(node.body, where)
            _take(node.orelse, where)
        elif _is_passthrough(node, assigns):
            pass
        else:
            unresolved.append(f"{where}:L{getattr(node, 'lineno', '?')}:{type(node).__name__}")

    for node in ast.walk(tree):
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
    return found, unresolved


def _all_constants(tree: ast.AST) -> Set[str]:
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _cross_file_reason_names(tree: ast.AST, module_consts: Dict[str, str]) -> None:
    """同檔 `_REASON_X = "literal"` 之常數名對映（供 `reason=_REASON_X` 解析為 Constant）。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                module_consts[node.targets[0].id] = node.value.value


def _resolve_same_file_names(tree: ast.AST) -> ast.AST:
    """把 `Name` 指向同檔頂層 str 常數者改寫成 `Constant`（只追同檔頂層；跨檔別名一律 unresolved）。"""
    consts: Dict[str, str] = {}
    if isinstance(tree, ast.Module):
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    consts[stmt.targets[0].id] = stmt.value.value

    class _Rewriter(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name):  # type: ignore[override]
            if isinstance(node.ctx, ast.Load) and node.id in consts:
                return ast.copy_location(ast.Constant(value=consts[node.id]), node)
            return node

    return _Rewriter().visit(tree)


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
    all_consts: Set[str] = set()
    reason_found: Set[str] = set()
    unresolved_all: List[str] = []
    for p, tree in trees.items():
        all_consts |= _all_constants(tree)
        resolved = _resolve_same_file_names(tree)
        found, unresolved = _reason_literals(resolved)
        reason_found |= found
        unresolved_all += [f"{p.name}:{u}" for u in unresolved]
    dead = sorted(r for r in reasons if r not in all_consts)
    if dead:
        failures.append(f"W2: 契約 reasons 未出現於 {pkg.name}/*.py 任何 Constant（死枚舉）: {dead}")
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
