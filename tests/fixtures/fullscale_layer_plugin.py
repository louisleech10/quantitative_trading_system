"""TESTSEL I4f 全規模層（docs/TESTSEL_I4F_SPEC.md）：pytest 官方範例〈Control skipping of tests according to command line
option〉之寫法——測試函式上直接加 `@pytest.mark.fullscale`，`--run-fullscale` 開關控制，收集期處理。

與官方範例唯一差異：不加 skip，改以 pytest 標準 deselect 延後。testmon 會把 skip 當已跑並記下依賴，之後加 `--run-fullscale`
也不再選中被延後者；deselect 不被記錄（`runs/testsel_route/i4f/i4f_facts.md` 原型③）。延後於其他選取（`-k`／`-m`／testmon）
之後（wrapper，`yield` 後），終端具名列出（屬「未驗」非「通過」）。`--collect-only` 不延後（nodeid 清單不隨分層而異）。
不經 `addopts -m`：帶 `-m` 使 testmon 停用選取。與手寫 `slow`（模組內偏慢；重型守衛與既有 gate_cmd 依 `-m "not slow"`）
為不同概念。marker 於 `pytest.ini` 宣告。
"""
from __future__ import annotations

from typing import Any, Dict, Generator, List

import pytest

OPTION = "--run-fullscale"
_DEFERRED = pytest.StashKey[Dict[str, int]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(OPTION, action="store_true", default=False,
                     help="執行全規模層（@pytest.mark.fullscale 之測試）；預設延後")


@pytest.hookimpl(wrapper=True)
def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config,
                                  items: List[pytest.Item]) -> Generator[None, None, None]:
    res = yield
    if config.getoption(OPTION) or config.option.collectonly:
        return res
    drop = [it for it in items if it.get_closest_marker("fullscale") is not None]
    if drop:
        gone = {id(it) for it in drop}
        items[:] = [it for it in items if id(it) not in gone]
        config.hook.pytest_deselected(items=drop)
        deferred: Dict[str, int] = {}
        for it in drop:
            f = it.nodeid.split("::", 1)[0]
            deferred[f] = deferred.get(f, 0) + 1
        config.stash[_DEFERRED] = deferred
    return res


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    deferred = config.stash.get(_DEFERRED, {})
    if not deferred:
        return
    terminalreporter.write_sep("-", f"全規模層：已延後之全規模測試（未驗，非通過；加 {OPTION} 執行）")
    for path in sorted(deferred):
        terminalreporter.write_line(f"{path}  延後 {deferred[path]} 條（加 {OPTION} 執行）")
