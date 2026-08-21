"""GAP-3 條件引擎純函式（docs/GAP3_EVENT_TODO.md Task B3.1；SPEC D3 欄位角色隔離＝規格全文）。

typed safe-subset AST＋canonical digest＋欄位角色清單＋max lookback。核心**不是** `df.eval`：
表達式由 Python `ast` 解析後逐 node 對契約白名單（`condition_engine_contract.json`）驗證，
再由本檔的 evaluator 遞迴求值。

角色隔離（D3-1/D3-3）：
- `expression_role='feature'`：引用 `trigger_outcome`／`future_outcome` 或 `future_*` 命名欄 ⇒ 拒。
- `expression_role='selection_predicate'`：放行未來欄，但 `column_roles` 全記錄、只進抽樣 provenance。
- `expression_role='label'`：須至少引用一個結果欄。
mutation M6 seam＝`_role_violation`（允許 future 欄過 feature 角色 ⇒ 測試必紅）。
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

try:  # Python 3.8+ 皆有 Literal；3.9.6 為 venv 實測版本
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal  # type: ignore

ExpressionRole = Literal["feature", "selection_predicate", "label"]

_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "condition_engine_contract.json"
_CONTRACT_CACHE: Optional[dict] = None


def load_condition_engine_contract() -> dict:
    """讀引擎契約（字面 SoT）；module 級快取，唯讀。"""
    global _CONTRACT_CACHE
    if _CONTRACT_CACHE is None:
        with _CONTRACT_PATH.open("r", encoding="utf-8") as f:
            _CONTRACT_CACHE = json.load(f)
    return _CONTRACT_CACHE


class ConditionError(ValueError):
    """條件式拒收（reason 字面住契約檔 failure_reasons）。"""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True)
class ConditionSpec:
    """已驗證之條件式。

    ast：canonical 巢狀 tuple（可雜湊、決定性）；canonical_digest＝其 JSON 之 sha256（同式異白／
    And-Or 運算元排序 ⇒ 同 digest；digest 不含 expression_role——角色是使用面不是規則身分）。
    column_roles：引用欄 → 角色（契約 column_roles 三值）。
    max_lookback：`lag(col, n)` 之最大 n（無 lag ⇒ 0）。
    label_ids：多組 label 之 manifest 識別（非布林覆寫；由產生器填）。
    """

    expression: str
    ast: Tuple[Any, ...]
    canonical_digest: str
    column_roles: Mapping[str, str]
    max_lookback: int
    label_ids: Tuple[str, ...]
    expression_role: str


# --------------------------------------------------------------------------- parse
_CMP_NAMES = {ast.Lt: "Lt", ast.LtE: "LtE", ast.Gt: "Gt", ast.GtE: "GtE", ast.Eq: "Eq", ast.NotEq: "NotEq"}
_CMP_FLIP = {"Lt": "Gt", "LtE": "GtE", "Gt": "Lt", "GtE": "LtE", "Eq": "Eq", "NotEq": "NotEq"}


def _role_violation(expression_role: str, column: str, column_role: str, contract: dict) -> Optional[str]:
    """角色隔離判定（M6 seam）。回 None＝合法，否則 reason。"""
    if expression_role == "feature":
        if column_role != "pit_feature" or column.startswith(contract["future_column_prefix"]):
            return "role_isolation_violation"
    return None


def _canon_const(v: Any) -> Tuple[str, Any]:
    if isinstance(v, bool):
        return ("const", v)
    if isinstance(v, (int, float)):
        return ("const", float(v))
    raise ConditionError("disallowed_node", f"constant of type {type(v).__name__}")


def _walk(node: ast.AST, registry: Mapping[str, str], contract: dict, cols: Dict[str, str], lags: List[int]) -> Tuple[Any, ...]:
    """遞迴驗證並產 canonical tuple。任何白名單外 node ⇒ ConditionError。"""
    allowed = contract["allowed_ast_nodes"]
    name = type(node).__name__
    if name not in allowed:
        raise ConditionError("disallowed_node", name)

    if isinstance(node, ast.Expression):
        return _walk(node.body, registry, contract, cols, lags)

    if isinstance(node, ast.BoolOp):
        op = "and" if isinstance(node.op, ast.And) else "or"
        parts = [_walk(v, registry, contract, cols, lags) for v in node.values]
        parts_sorted = tuple(sorted(parts, key=lambda p: json.dumps(p, sort_keys=True, default=str)))
        return (op,) + parts_sorted

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return ("not", _walk(node.operand, registry, contract, cols, lags))
        if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            c = _canon_const(node.operand.value)
            if isinstance(c[1], bool):
                raise ConditionError("disallowed_node", "USub on bool")
            return ("const", -c[1])
        raise ConditionError("disallowed_node", type(node.op).__name__)

    if isinstance(node, ast.Compare):
        operands = [_walk(node.left, registry, contract, cols, lags)] + [
            _walk(c, registry, contract, cols, lags) for c in node.comparators
        ]
        ops = []
        for o in node.ops:
            if type(o) not in _CMP_NAMES:
                raise ConditionError("disallowed_node", type(o).__name__)
            ops.append(_CMP_NAMES[type(o)])
        # 區間（鏈式比較）展開為 and 之兩兩比較，與顯式 `a<x and x<b` 同 digest
        pairs = []
        for i, op in enumerate(ops):
            left, right = operands[i], operands[i + 1]
            # canonical：常數放右側（`5 < x` ⇒ `x > 5`）
            if left[0] == "const" and right[0] != "const":
                left, right, op = right, left, _CMP_FLIP[op]
            pairs.append(("cmp", op, left, right))
        if len(pairs) == 1:
            return pairs[0]
        return ("and",) + tuple(sorted(pairs, key=lambda p: json.dumps(p, sort_keys=True, default=str)))

    if isinstance(node, ast.Name):
        col = node.id
        if col not in registry:
            raise ConditionError("unregistered_column", col)
        role = registry[col]
        if role not in contract["column_roles"]:
            raise ConditionError("unknown_column_role", f"{col}:{role}")
        cols[col] = role
        return ("col", col)

    if isinstance(node, ast.Constant):
        return _canon_const(node.value)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise ConditionError("disallowed_function", ast.dump(node.func))
        fname = node.func.id
        funcs = contract["allowed_functions"]
        if fname not in funcs:
            raise ConditionError("disallowed_function", fname)
        if len(node.args) != int(funcs[fname]["arity"]):
            raise ConditionError("disallowed_function", f"{fname} arity")
        if fname == "lag":
            target = _walk(node.args[0], registry, contract, cols, lags)
            n_node = node.args[1]
            if not (isinstance(n_node, ast.Constant) and isinstance(n_node.value, int)
                    and not isinstance(n_node.value, bool) and n_node.value >= 1):
                raise ConditionError("invalid_lag", "lag n 須為正整數常數（只往過去）")
            if target[0] != "col":
                raise ConditionError("invalid_lag", "lag 第一參數須為欄位")
            lags.append(int(n_node.value))
            return ("lag", target, int(n_node.value))
        arg = _walk(node.args[0], registry, contract, cols, lags)
        return (fname, arg)

    raise ConditionError("disallowed_node", name)  # pragma: no cover —— 白名單內但未處理者


def _is_constant_tree(t: Tuple[Any, ...]) -> bool:
    if t[0] == "col":
        return False
    if t[0] == "const":
        return True
    if t[0] == "cmp":
        return _is_constant_tree(t[2]) and _is_constant_tree(t[3])
    if t[0] == "lag":
        return False
    return all(_is_constant_tree(x) for x in t[1:] if isinstance(x, tuple))


def _is_trivial_compare(t: Tuple[Any, ...]) -> bool:
    """`x == x`／`x <= x` 類恆真／恆假比較。"""
    if t[0] == "cmp" and t[2] == t[3]:
        return True
    if t[0] in ("and", "or", "not"):
        return any(_is_trivial_compare(x) for x in t[1:])
    return False


def parse_condition(
    expression: str,
    column_registry: Mapping[str, str],
    expression_role: ExpressionRole,
    *,
    label_ids: Tuple[str, ...] = (),
) -> ConditionSpec:
    """解析並驗證條件式；任何不合法 ⇒ ConditionError（reason 字面住契約檔）。

    column_registry：欄位 → 角色（`pit_feature|trigger_outcome|future_outcome`）；未註冊欄 ⇒ 拒。
    """
    contract = load_condition_engine_contract()
    if expression_role not in contract["expression_roles"]:
        raise ConditionError("unknown_expression_role", str(expression_role))
    if expression is None or not str(expression).strip():
        raise ConditionError("empty_expression")
    try:
        tree = ast.parse(str(expression).strip(), mode="eval")
    except SyntaxError as exc:
        raise ConditionError("syntax_error", str(exc)) from exc

    cols: Dict[str, str] = {}
    lags: List[int] = []
    canon = _walk(tree, column_registry, contract, cols, lags)

    if _is_constant_tree(canon) or _is_trivial_compare(canon):
        raise ConditionError("constant_expression", "表達式不引用欄位或恆真／恆假")

    for col, role in sorted(cols.items()):
        r = _role_violation(expression_role, col, role, contract)
        if r is not None:
            raise ConditionError(r, f"{col} ({role}) under expression_role={expression_role}")
    if expression_role == "label" and not any(r in ("trigger_outcome", "future_outcome") for r in cols.values()):
        raise ConditionError("label_without_outcome_column")

    digest = hashlib.sha256(json.dumps(canon, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return ConditionSpec(
        expression=str(expression),
        ast=canon,
        canonical_digest=digest,
        column_roles=dict(sorted(cols.items())),
        max_lookback=max(lags) if lags else 0,
        label_ids=tuple(label_ids),
        expression_role=str(expression_role),
    )


# --------------------------------------------------------------------------- evaluate
def _eval(t: Tuple[Any, ...], df: pd.DataFrame) -> Any:
    kind = t[0]
    if kind == "col":
        return df[t[1]]
    if kind == "const":
        return t[1]
    if kind == "lag":
        return df[t[1][1]].shift(int(t[2]))  # 只往過去
    if kind == "cmp":
        left, right = _eval(t[2], df), _eval(t[3], df)
        op = t[1]
        if op == "Lt":
            return left < right
        if op == "LtE":
            return left <= right
        if op == "Gt":
            return left > right
        if op == "GtE":
            return left >= right
        if op == "Eq":
            return left == right
        return left != right
    if kind == "and":
        out = None
        for x in t[1:]:
            v = _eval(x, df)
            out = v if out is None else (out & v)
        return out
    if kind == "or":
        out = None
        for x in t[1:]:
            v = _eval(x, df)
            out = v if out is None else (out | v)
        return out
    if kind == "not":
        return ~_eval(t[1], df)
    if kind == "isnull":
        return _eval(t[1], df).isna()
    if kind == "notnull":
        return _eval(t[1], df).notna()
    if kind == "abs":
        return _eval(t[1], df).abs()
    raise ConditionError("disallowed_node", kind)  # pragma: no cover


def evaluate_condition(spec: ConditionSpec, df: pd.DataFrame) -> pd.Series:
    """對 df 求布林遮罩（index 同 df）。引用欄缺 ⇒ KeyError loud；NaN 比較依 numpy 語意為 False。"""
    missing = [c for c in spec.column_roles if c not in df.columns]
    if missing:
        raise KeyError(f"evaluate_condition: df 缺欄 {missing}")
    out = _eval(spec.ast, df)
    if not isinstance(out, pd.Series):
        raise ConditionError("non_boolean_result", type(out).__name__)
    if out.dtype != bool:
        if pd.api.types.is_bool_dtype(out):
            out = out.fillna(False).astype(bool)
        else:
            raise ConditionError("non_boolean_result", str(out.dtype))
    return out.astype(bool)


def assert_no_outcome_columns(columns: Mapping[str, str] | List[str], column_registry: Mapping[str, str]) -> None:
    """D3-4：匯出 ML 特徵表前斷言無 trigger_outcome／future_outcome 角色欄（selection_predicate 欄不得流入特徵表）。"""
    contract = load_condition_engine_contract()
    bad = []
    for c in list(columns):
        role = column_registry.get(c)
        if role in ("trigger_outcome", "future_outcome") or str(c).startswith(contract["future_column_prefix"]):
            bad.append(c)
    if bad:
        raise ConditionError("role_isolation_violation", f"特徵表含結果欄 {sorted(bad)}")


def allowed_filtering_params() -> frozenset:
    """D3-3：legacy `/search` 篩選參數允許清單之契約化出口（原 `requests.py` 寫死 {'price_change'}）。"""
    return frozenset(load_condition_engine_contract()["allowed_filtering_params"])


__all__ = [
    "ConditionError",
    "ConditionSpec",
    "ExpressionRole",
    "allowed_filtering_params",
    "assert_no_outcome_columns",
    "evaluate_condition",
    "load_condition_engine_contract",
    "parse_condition",
]
