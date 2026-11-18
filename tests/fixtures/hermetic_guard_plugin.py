"""測試隔離守衛外掛（TESTSEL I1a；docs/TESTSEL_I1_REDS_SPEC.md Task 1.1、Task 1.4）。

由 `tests/conftest.py` 之 `pytest_plugins` 註冊（取代原 `_PROD_WRITE_DIRS`／`prod_write_snapshot`／`pytest_sessionfinish`
只報兩頂層目錄之偵測）。驗收：`tests/hermetic/`。抽成獨立模組之理由：可於暫存專案以 `-p tests.fixtures.hermetic_guard_plugin` 單獨載入，驗 session 結束碼與 handler
清理（`tests/hermetic/`），不需載入整個 `tests/conftest.py`；I3 移植至 main 時原樣帶入。

Task 1.1——正式資料根寫入偵測：
- 範圍＝`<rootpath>/data_cache` 與「session 開始時 cwd 下之 `data_cache`」兩棵全樹（解析後相同則只掃一次；根為符號連結時
  解析至實體；樹內符號連結不跟隨，只記其本身 lstat）。掃 cwd 者之理由：產品預設根多為「相對 cwd 之 data_cache」
  （PatternStorage、build_cube、KlineStorageManager；I1a 實測），pytest 自他處起跑時寫入落在 cwd 下（審查 r1 P1-02）。
- 新增、修改、刪除皆算（刪除無 mtime ⇒ 保守歸測試時段）。
- 經 `tests/conftest.py` 之 `pytest_plugins` 註冊（舊 `_PROD_WRITE_DIRS`／`prod_write_snapshot`／`pytest_sessionfinish` 同批移除）。
- session 開始／結束各快照一次 {相對路徑: (mtime_ns, size)}（含目錄）；有新增／修改／刪除且落在任一測試執行時段
  （`pytest_runtest_logstart`～`pytest_runtest_logfinish`）⇒ `session.exitstatus` 設為 `PROD_WRITE_EXIT_CODE`，終端具名列出
  每個路徑與其 mtime；落在無測試執行之時段者標「非測試寫入」只報不改結束碼（SPEC Task 1.1 邊界②）。
- session 開始與結束各查一次正式服務行程（`PROD_SERVICE_PATTERN`）；任一非空 ⇒ 終端標 `PRECONDITION_MARK`
  （該次結果不採計，前提滿足後重跑；SPEC Task 1.1「執行前提」）。

Task 1.4——root logger handler 外洩：autouse function 範圍 fixture，測試結束後關閉並移除「該測試期間新增至 root
logger」之 handler；pytest 自身 handler（caplog／logging plugin）與測試前既有者不動。
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pytest

PROD_DATA_DIRNAME = "data_cache"
# None＝data_cache 全樹；只為改壞對照（test_mutation_*）可設為子目錄元組，正式不得設定。
PROD_SCAN_SUBDIRS: Optional[Tuple[str, ...]] = None
PROD_WRITE_EXIT_CODE = 1
PROD_SERVICE_PATTERN = "run_api.py|uvicorn|next dev|next start"
PRECONDITION_MARK = "[HERMETIC-PRECONDITION] 正式服務行程存在，本次結果不採計"
NON_TEST_MARK = "非測試寫入"
# "new_only"＝只移除測試期間新增者（正式）；"all" 只為改壞對照。
ROOT_HANDLER_POLICY = "new_only"

Snapshot = Dict[str, Tuple[int, int]]


def resolve_prod_root(rootpath: Path) -> Path:
    """`<rootpath>/data_cache` 解析符號連結後之實體路徑（SPEC Task 1.1 邊界①）。"""
    return (Path(rootpath) / PROD_DATA_DIRNAME).resolve()


def watched_roots(rootpath: Path, cwd: Path) -> List[Path]:
    """要快照之根：`resolve_prod_root(rootpath)` 與 `cwd/data_cache`（解析後去重；不存在者仍列入以偵測新建）。"""
    roots: List[Path] = []
    for cand in (resolve_prod_root(rootpath), (Path(cwd) / PROD_DATA_DIRNAME).resolve()):
        if cand not in roots:
            roots.append(cand)
    return roots


def _walk(base: Path, rel_prefix: str, out: Snapshot) -> None:
    try:
        entries = list(os.scandir(base))
    except OSError:
        return
    for entry in entries:
        rel = f"{rel_prefix}{entry.name}"
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        out[rel] = (st.st_mtime_ns, st.st_size)
        if entry.is_dir(follow_symlinks=False):
            _walk(Path(entry.path), rel + "/", out)


def prod_write_snapshot(prod_root: Path) -> Snapshot:
    """遞迴快照 {相對 posix 路徑: (mtime_ns, size)}，含目錄；樹內符號連結以 lstat 記錄、不跟隨（防自指迴圈）。"""
    snap: Snapshot = {}
    root = Path(prod_root)
    if not root.is_dir():
        return snap
    if PROD_SCAN_SUBDIRS is None:
        _walk(root, "", snap)
        return snap
    for sub in PROD_SCAN_SUBDIRS:
        base = root / sub
        if base.is_dir():
            _walk(base, f"{sub}/", snap)
    return snap


def prod_write_diff(before: Snapshot, after: Snapshot) -> List[str]:
    """新增、變動、消失之路徑（排序）。"""
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def classify_prod_writes(
    changed: Sequence[str], after: Snapshot, windows: Sequence[Tuple[int, int]]
) -> Tuple[List[str], List[str]]:
    """依 mtime 歸因：回 (測試時段內, 非測試時段)；已消失之路徑無 mtime ⇒ 保守歸測試時段。"""
    in_test: List[str] = []
    non_test: List[str] = []
    for path in changed:
        stat = after.get(path)
        if stat is None or any(start <= stat[0] <= end for start, end in windows):
            in_test.append(path)
        else:
            non_test.append(path)
    return in_test, non_test


def prod_services_running() -> List[str]:
    """`pgrep -ifl PROD_SERVICE_PATTERN` 之結果行（無則空；排除本行程）。"""
    try:
        proc = subprocess.run(
            ["pgrep", "-ifl", PROD_SERVICE_PATTERN], capture_output=True, text=True, errors="replace",
            env={**os.environ, "LC_ALL": "C"},
        )
    except OSError:
        return []
    own = str(os.getpid())
    return [line for line in proc.stdout.splitlines() if line.strip() and line.split()[0] != own]


class _State:
    roots: List[Path] = []
    before: Dict[Path, Snapshot] = {}
    services_at_start: List[str] = []
    windows: List[Tuple[int, int]] = []
    current_start: Optional[int] = None


def pytest_sessionstart(session) -> None:  # type: ignore[no-untyped-def]
    """記 session 開始快照與正式服務行程。"""
    _State.roots = watched_roots(Path(str(session.config.rootpath)), Path.cwd())
    _State.before = {root: prod_write_snapshot(root) for root in _State.roots}
    _State.services_at_start = prod_services_running()
    _State.windows = []
    _State.current_start = None


def pytest_runtest_logstart(nodeid: str, location) -> None:  # type: ignore[no-untyped-def]
    """記測試起點（ns）。"""
    _State.current_start = time.time_ns()


def pytest_runtest_logfinish(nodeid: str, location) -> None:  # type: ignore[no-untyped-def]
    """記測試終點（ns）。"""
    if _State.current_start is not None:
        _State.windows.append((_State.current_start, time.time_ns()))
        _State.current_start = None


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus) -> None:  # type: ignore[no-untyped-def]
    """比對快照、歸因、列出路徑；測試時段內有寫入 ⇒ `session.exitstatus = PROD_WRITE_EXIT_CODE`。"""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")

    def say(msg: str, red: bool = True) -> None:
        if reporter is not None:
            reporter.write_line(msg, red=red)

    in_test_all: List[str] = []
    for root in _State.roots:
        after = prod_write_snapshot(root)
        changed = prod_write_diff(_State.before.get(root, {}), after)
        if not changed:
            continue
        in_test, non_test = classify_prod_writes(changed, after, _State.windows)
        for rel in in_test:
            stat = after.get(rel)
            in_test_all.append(f"{root}/{rel}")
            say(f"[HERMETIC] 測試寫入正式資料根：{root}/{rel}（mtime_ns={stat[0] if stat else '已刪除'}）")
        for rel in non_test:
            say(f"[HERMETIC] {NON_TEST_MARK}：{root}/{rel}（mtime_ns={after[rel][0]}）", red=False)
    services = sorted(set(_State.services_at_start) | set(prod_services_running()))
    if services:
        say(f"{PRECONDITION_MARK}：{'; '.join(services)}")
    if in_test_all:
        say(f"[HERMETIC] 共 {len(in_test_all)} 項測試時段內之寫入 ⇒ session 結束狀態 {PROD_WRITE_EXIT_CODE}")
        session.exitstatus = PROD_WRITE_EXIT_CODE


def cleanup_root_handlers(before: Sequence[object]) -> List[object]:
    """關閉並移除 root logger 上「不在 before 內」之 handler（`ROOT_HANDLER_POLICY="new_only"`）；回傳被移除者。
    pytest 自身 handler 於測試開始前已掛上（在 before 內）⇒ 不動（SPEC Task 1.4 邊界②）。"""
    root = logging.getLogger()
    keep = {id(h) for h in before}
    if ROOT_HANDLER_POLICY == "all":
        removed = list(root.handlers)
    else:
        removed = [h for h in root.handlers if id(h) not in keep]
    for handler in removed:
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001 —— 關閉失敗不影響移除
            pass
    return removed


@pytest.fixture(autouse=True)
def _root_handler_guard():  # type: ignore[no-untyped-def]
    """測試後移除該測試期間新增之 root handler（SPEC Task 1.4）。"""
    before = list(logging.getLogger().handlers)
    yield
    cleanup_root_handlers(before)
