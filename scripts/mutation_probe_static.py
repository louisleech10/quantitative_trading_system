#!/usr/bin/env python3
"""mutation_probe_static.py — AST 靜態檢查 test_mutation_* 探針非空心/非偽自證(章程 §B1.1)。

為何(2026-06-28,機制 review 兩家攻破):mutation_probe_check.sh 原只驗「探針有名、有跑、有綠」,
擋不住:① 空心 `assert True`;② 偽 raises(`with pytest.raises(ZeroDivisionError): 1/0`,與待測無關)。
本檢查用 AST 對每個 `test_mutation_*`:
  - 必含「注入/falsification」結構:pytest.raises / monkeypatch / setattr / mock.patch /
    .clear( / .initialize( / .discard( / assert ...(含 not 或比較或 np.testing.assert*);
    且不得只有 Pass / assert True / 常數運算式。
  - 偽 raises 啟發(WARN，非 FAIL):raises 區塊內僅 literal 運算(如 1/0)而無被測符號引用。
  - oracle 自指啟發(WARN):探針/檔內 oracle 區出現 list_indicators()/INDICATOR_REGISTRY/
    _*_MAP 同時當期望值;提示 adversarial 必審(機器不宣稱證獨立)。

退出:0=全部探針結構合格(WARN 不致命);1=有空心/偽自證(致命)。誠實邊界:靜態擋明顯空心,
真自指/真綁定底層斷言仍須 adversarial(§B1.2)。
"""
from __future__ import annotations

import ast
import sys

FALSIFY_CALL = {"raises", "fail", "monkeypatch", "setattr", "patch", "clear",
                "initialize", "discard", "pop", "assert_allclose", "assert_array_equal",
                "assert_array_almost_equal", "approx"}
# 「碰到待測系統」訊號:防偽 raises(如 `with pytest.raises(ZeroDivisionError): 1/0` 與待測無關)。
SYSTEM_TOUCH_CALL = {"monkeypatch", "setattr", "patch", "mock", "clear", "initialize", "discard"}
PROJECT_IMPORT_PREFIX = ("momentum", "api", "tests.references")
SELF_REF_TOKENS = ("list_indicators(", "INDICATOR_REGISTRY", "_INPUT_TYPE_MAP",
                   "_CATEGORY_MAP", "build_talib_input_semantics(")


def _calls(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                out.add(f.attr)
            elif isinstance(f, ast.Name):
                out.add(f.id)
        if isinstance(n, ast.With):
            for item in n.items:
                c = item.context_expr
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
                    out.add(c.func.attr)
    return out


def _has_real_assert(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Assert):
            t = n.test
            # 'assert True' / 'assert 1' = 空心,不算
            if isinstance(t, ast.Constant):
                continue
            return True
    return False


def _body_is_trivial(fn: ast.FunctionDef) -> bool:
    real = []
    for s in fn.body:
        if isinstance(s, ast.Pass):
            continue
        if isinstance(s, ast.Expr) and isinstance(s.value, (ast.Constant, ast.Str)):
            continue  # docstring / bare literal
        if isinstance(s, ast.Assert) and isinstance(s.test, ast.Constant):
            continue  # assert True
        real.append(s)
    return len(real) == 0


def _project_imported_names(tree: ast.AST) -> set[str]:
    """模組層級從 momentum/api/tests.references import 的名字(待測系統符號)。"""
    names: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith(PROJECT_IMPORT_PREFIX):
            for a in n.names:
                names.add(a.asname or a.name)
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith(PROJECT_IMPORT_PREFIX):
                    names.add((a.asname or a.name).split(".")[0])
    return names


def _refs_names(node: ast.AST, names: set[str]) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in names:
            return True
    return False


def check_file(path: str) -> tuple[list[str], list[str]]:
    fatal: list[str] = []
    warn: list[str] = []
    try:
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
    except Exception as exc:  # noqa: BLE001
        return [f"{path}: 無法解析 ({exc})"], []
    project_names = _project_imported_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_mutation_"):
            continue
        calls = _calls(node)
        has_falsify = bool(calls & FALSIFY_CALL) or _has_real_assert(node)
        if _body_is_trivial(node) or not has_falsify:
            fatal.append(
                f"{path}::{node.name} 空心/無 falsification 探針"
                f"(須 pytest.raises / monkeypatch / setattr / assert(非True) / clear()+initialize() 等)"
            )
            continue
        # 防偽 raises:探針須真碰到待測系統(monkeypatch/setattr/patch 或引用 momentum/api 符號)
        touches_system = bool(calls & SYSTEM_TOUCH_CALL) or _refs_names(node, project_names)
        if not touches_system:
            fatal.append(
                f"{path}::{node.name} 探針未碰到待測系統"
                f"(僅 falsify 與待測無關,如 `pytest.raises(ZeroDivisionError): 1/0`);"
                f"須 monkeypatch/setattr 待測碼 或 引用 momentum/api 被測符號"
            )
            continue
        seg = ast.get_source_segment(src, node) or ""
        if any(tok in seg for tok in SELF_REF_TOKENS):
            warn.append(f"{path}::{node.name} 可能自指 oracle(出現 {[t for t in SELF_REF_TOKENS if t in seg]});adversarial 必審獨立性")
    return fatal, warn


def main(argv: list[str]) -> int:
    fatal: list[str] = []
    warn: list[str] = []
    for path in argv:
        f, w = check_file(path)
        fatal += f
        warn += w
    for w in warn:
        print(f"ORACLE-SELF-REF WARN: {w}")
    if fatal:
        print("MUTATION-PROBE-STATIC FAIL:")
        for f in fatal:
            print(f"  · {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
