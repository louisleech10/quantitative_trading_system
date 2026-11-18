"""TESTSEL I4e 硬體閘（docs/TESTSEL_I4E_SPEC.md Task 1.2）：收集期依 `tests/hardware_requirements.json` 具名排除大機器測試。

本機實體記憶體低於登記之 `min_memory_gib` 之檔，其全部測試於收集後以 pytest 標準 deselect 排除（不 skip、不 xfail），
終端摘要逐檔具名列出（路徑、ticket、item、需求、本機記憶體、被排除條數）；被排除者屬「未驗」非「通過」，大機器驗收由
RM-FULLSCALE 承接。讀表與記憶體判斷之唯一實作＝`scripts/hardware_requirements.py`（以檔案路徑載入；framepath 閘同此）。
排除於其他選取（`-k`／`-m`／testmon）之後執行（wrapper，`yield` 後），摘要只計本會執行而被硬體閘排除者。
`--collect-only` 不執行測試 ⇒ 不排除（nodeid 清單不隨本機記憶體而異；登記表仍驗格式）。
登記表不存在 ⇒ 不排除；格式錯 ⇒ `pytest.UsageError`（收集前即失敗，fail-closed）。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import pytest

_BLOCKED_KEY = pytest.StashKey[Dict[str, Dict[str, Any]]]()
_DROPPED_KEY = pytest.StashKey[Dict[str, List[str]]]()


#: 本外掛所屬 repo 之根（`tests/fixtures/` 上兩層）。共用模組與登記表皆取自此處，不取 `config.rootpath`——有測試以暫存目錄為
#: rootdir、經 `-p tests.conftest` 載入本 repo 之外掛（如 tests/hermetic/test_prod_writers_tmp_root.py），暫存根下無共用模組
#: （施工時原 session 回報 INTERNALERROR FileNotFoundError）。驗收之暫存 repo 複製本外掛，故此根即該暫存 repo。
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _hw_module(root: Path):
    """以檔案路徑載入 `root` 下之共用模組（暫存 repo 驗收時載入其副本）。"""
    p = root / "scripts" / "hardware_requirements.py"
    spec = importlib.util.spec_from_file_location("_hardware_requirements_gate_plugin", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def pytest_configure(config: pytest.Config) -> None:
    root = _REPO_ROOT
    hw = _hw_module(root)
    try:
        entries = hw.load_hardware_requirements(root)
    except hw.HardwareTableError as exc:
        raise pytest.UsageError(f"硬體閘：{exc}") from exc
    config.stash[_DROPPED_KEY] = {}
    if config.option.collectonly:
        # 只收集不執行 ⇒ 無記憶體風險；不排除，使 nodeid 清單（golden inventory、framepath 閘 nodeid 表、ledger 估時等）
        # 不隨本機記憶體而異（施工時 test_mutation_d11_7_inventory_hand_edit_is_red 實測轉紅）
        config.stash[_BLOCKED_KEY] = {}
        return
    config.stash[_BLOCKED_KEY] = dict(hw.hardware_blocked(entries, hw.machine_memory_bytes()))


def _repo_rel_paths(items: List[pytest.Item]) -> Dict[int, Optional[str]]:
    """item → 其檔案相對 `_REPO_ROOT` 之 POSIX 路徑（repo 外 ⇒ None）。不用 nodeid：nodeid 相對 rootdir，`--rootdir tests`
    等合法用法下與登記表之 repo 相對鍵不同而漏排（審碼 b1 r1）。同檔只解析一次。"""
    cache: Dict[Path, Optional[str]] = {}
    out: Dict[int, Optional[str]] = {}
    for it in items:
        p = Path(it.path)
        if p not in cache:
            try:
                cache[p] = p.resolve().relative_to(_REPO_ROOT).as_posix()
            except ValueError:
                cache[p] = None
        out[id(it)] = cache[p]
    return out


@pytest.hookimpl(wrapper=True)
def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config,
                                  items: List[pytest.Item]) -> Generator[None, None, None]:
    res = yield
    blocked = config.stash.get(_BLOCKED_KEY, {})
    if not blocked:
        return res
    rel = _repo_rel_paths(items)
    drop = [it for it in items if rel[id(it)] in blocked]
    if drop:
        gone = {id(it) for it in drop}
        items[:] = [it for it in items if id(it) not in gone]
        config.hook.pytest_deselected(items=drop)
        dropped = config.stash[_DROPPED_KEY]
        for it in drop:
            dropped.setdefault(str(rel[id(it)]), []).append(it.nodeid)
    return res


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    dropped = config.stash.get(_DROPPED_KEY, {})
    if not dropped:
        return
    blocked = config.stash.get(_BLOCKED_KEY, {})
    terminalreporter.write_sep("-", "硬體閘：本機記憶體不足之大機器專用測試已具名排除（未驗，非通過）")
    for path in sorted(dropped):
        info = blocked[path]
        terminalreporter.write_line(
            f"{path}  {info['ticket']} {info.get('item') or ''}  需 {info['min_memory_gib']} GiB／本機 "
            f"{info['machine_memory_gib']} GiB  排除 {len(dropped[path])} 條")
