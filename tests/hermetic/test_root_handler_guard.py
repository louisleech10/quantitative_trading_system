"""TESTSEL I1a｜SPEC Task 1.4：root logger handler 外洩。

根因（runs/testsel_mon/TESTSEL_REMAINING.md 11-16 20:02 列）：pagination 兩測試於主行程呼叫 `_process_chunk_worker`，
`_init_worker_file_logging`（parallel_search_engine.py）把 FileHandler 掛 root 不移除；`tmp_path_retention_policy = failed`
刪其暫存目錄後，其後凡寫 root log 之測試拋 FileNotFoundError（段 5 213 條假紅）。
重現須依段 5 實際順序（`data/seg5_pagination_order.txt`，取自段 5 進度紀錄 -67605-；檔內原序 45 passed 不重現）：
I1a 實測無守衛 ⇒ `11 failed, 33 passed`，錯誤 `FileNotFoundError: …/test_parallel_worker_outer_cat0/w.log`（產品 handler 帶
「同行程已掛即不再掛」標記，外洩後後續測試之新 log_path 不再建立）。
pagination 檔一律複製進暫存專案再跑：以外部絕對路徑給檔會載入其祖先目錄之 conftest.py（主 repo 根者把主 repo 插入 sys.path）。
暫存專案均設 `tmp_path_retention_policy = failed` 以重現同條件。實作前 boundary_01／02、accept_01 為紅。
"""
from __future__ import annotations

import logging
import re
import textwrap
from pathlib import Path

import pytest

from tests.fixtures import hermetic_guard_plugin as guard
from tests.hermetic._harness import REPO, run_pytest

INI = "[pytest]\ntmp_path_retention_policy = failed\n"
PAGINATION = REPO / "tests/momentum/DataExtraction/test_search_download_pagination.py"
# 施工時於兩測試之 finally 清理行尾加此標記，供 M3 機械移除（SPEC Task 1.4 mutation M3）
FINALLY_MARK = "# I1A-HANDLER-FINALLY"
SEG5_ORDER = [
    l.strip() for l in (Path(__file__).parent / "data" / "seg5_pagination_order.txt").read_text(encoding="utf-8").splitlines()
    if l.strip()
]


def _strip_finally(src: str) -> str:
    """把帶 FINALLY_MARK 之清理行換成 `pass`（還原為改前之外洩狀態；無標記時原樣）。"""
    return "\n".join(
        re.sub(r"^(\s*).*" + re.escape(FINALLY_MARK) + r".*$", r"\1pass", line) for line in src.splitlines()
    )


def _seg5_pagination_run(tmp_path: Path, source: str, plugins=None):  # type: ignore[no-untyped-def]
    """pagination 檔（source 內容）複製進暫存專案，依段 5 順序逐 nodeid 跑。"""
    proj = _proj(tmp_path, "def test_placeholder():\n    pass\n")
    (proj / "test_pagination_copy.py").write_text(source, encoding="utf-8")
    ids = [f"test_pagination_copy.py::{name}" for name in SEG5_ORDER]
    if plugins is None:
        return run_pytest(proj, ids)
    return run_pytest(proj, ids, plugins=plugins)

LEAK_THEN_LOG = """
    import logging
    def test_a_mounts_file_handler_without_cleanup(tmp_path):
        h = logging.FileHandler(tmp_path / "w.log")
        logging.getLogger().addHandler(h)
        logging.getLogger().warning("a")
    def test_b_root_handlers_clean_and_logging_works():
        root = logging.getLogger()
        # 只查測試 a 外洩之 w.log（pytest 自身另掛 `_FileHandler /dev/null`，亦為 FileHandler 子類）
        assert not any(str(getattr(h, "baseFilename", "")).endswith("w.log") for h in root.handlers), root.handlers
        root.warning("b")
"""

# 測試前既有之 root handler（代表 pytest 自身與 session 級設定所掛者；pytest 之 caplog handler 每階段重掛，
# 單看 caplog 分辨不出「全清」——故另於 conftest 匯入時預掛一個具名 handler 觀測）
PREEXISTING_CONFTEST = """
    import logging
    _H = logging.NullHandler()
    _H.set_name("session-preexisting")
    logging.getLogger().addHandler(_H)
"""

CAPLOG_AFTER_LEAK = """
    import logging
    def test_a_mounts_handler(tmp_path):
        logging.getLogger().addHandler(logging.FileHandler(tmp_path / "w.log"))
    def test_b_caplog_and_preexisting_handler_survive(caplog):
        names = [h.get_name() for h in logging.getLogger().handlers]
        assert "session-preexisting" in names, names
        with caplog.at_level(logging.INFO):
            logging.getLogger("x").info("hello-caplog")
        assert any(r.getMessage() == "hello-caplog" for r in caplog.records)
"""


def _failed_count(out: str) -> int:
    """pytest 摘要行之 failed 數（不以字串 " failed" 比對：log 內容如 `status to failed` 會誤中）。"""
    m = re.findall(r"(\d+) failed", out)
    return int(m[-1]) if m else 0


def _proj(tmp_path: Path, body: str, conftest: str = "") -> Path:
    proj = tmp_path / "proj"
    proj.mkdir(parents=True)
    (proj / "pytest.ini").write_text(INI, encoding="utf-8")
    (proj / "test_case.py").write_text(textwrap.dedent(body), encoding="utf-8")
    if conftest:
        (proj / "conftest.py").write_text(textwrap.dedent(conftest), encoding="utf-8")
    return proj


def test_boundary_01_mounted_handler_removed_after_test(tmp_path: Path) -> None:
    """邊界①：測試掛 root handler 未清 ⇒ 守衛於該測試後移除；下一測試 root 無該 handler 且寫 log 正常 ⇒ 2 passed。"""
    res = run_pytest(_proj(tmp_path, LEAK_THEN_LOG), ["test_case.py"])
    assert res.rc == 0 and "2 passed" in res.out, res.out


def test_boundary_02_pytest_own_handlers_preserved(tmp_path: Path) -> None:
    """邊界②：pytest 自身與測試前既有之 handler 不得被移除——清理後既有 handler 仍在、caplog 仍收到紀錄 ⇒ 2 passed。"""
    res = run_pytest(_proj(tmp_path, CAPLOG_AFTER_LEAK, PREEXISTING_CONFTEST), ["test_case.py"])
    assert res.rc == 0 and "2 passed" in res.out, res.out


def test_accept_01_seg5_order_pagination_passes_with_guard(tmp_path: Path) -> None:
    """SPEC Task 1.4 驗證：依段 5 順序跑 pagination 檔 44 條 ⇒ 全過（現況無守衛 11 failed，見 M1）。"""
    res = _seg5_pagination_run(tmp_path, PAGINATION.read_text(encoding="utf-8"))
    assert res.rc == 0, res.out
    assert _failed_count(res.out) == 0 and "FileNotFoundError" not in res.out, res.out


def test_mutation_m1_without_guard_downstream_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """M1：守衛不清理（等同移除 fixture）⇒ 段 5 順序之 pagination（兩測試 finally 清理剝除＝改前狀態）11 failed、
    邊界①之 test_b 1 failed；行程內另證清理函式被換成空操作時外洩之 handler 仍在。
    （審查 r1 codex／grok P1-01：改用剝除 finally 之來源，施工加 finally 後本斷言仍成立。）"""
    seg5 = _seg5_pagination_run(tmp_path / "seg5", _strip_finally(PAGINATION.read_text(encoding="utf-8")), plugins=())
    assert seg5.rc != 0 and _failed_count(seg5.out) == 11 and "test_parallel_worker_outer_cat0/w.log" in seg5.out, seg5.out
    res = run_pytest(_proj(tmp_path, LEAK_THEN_LOG), ["test_case.py"], plugins=())
    assert res.rc != 0 and _failed_count(res.out) == 1, res.out
    root = logging.getLogger()
    before = list(root.handlers)
    leaked = logging.FileHandler(tmp_path / "leak.log")
    root.addHandler(leaked)
    try:
        assert leaked in guard.cleanup_root_handlers(before) and leaked not in root.handlers
        root.addHandler(leaked)
        monkeypatch.setattr(guard, "cleanup_root_handlers", lambda b: [])
        guard.cleanup_root_handlers(before)
        assert leaked in root.handlers
    finally:
        if leaked in root.handlers:
            root.removeHandler(leaked)
        leaked.close()


def test_mutation_m2_clear_all_handlers_removes_preexisting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """M2：守衛改為清除全部 root handlers ⇒ 測試前既有之 handler（代表 pytest 自身 caplog／logging plugin）被移除；
    正式政策下保留。暫存專案層另證：預掛之 session 級 handler 被清 ⇒ 邊界②之 test_b 1 failed。"""
    root = logging.getLogger()
    orig = list(root.handlers)
    sentinel = logging.NullHandler()
    root.addHandler(sentinel)
    try:
        before = list(root.handlers)
        new = logging.FileHandler(tmp_path / "new.log")
        root.addHandler(new)
        guard.cleanup_root_handlers(before)
        assert sentinel in root.handlers and new not in root.handlers
        new2 = logging.FileHandler(tmp_path / "new2.log")
        root.addHandler(new2)
        monkeypatch.setattr(guard, "ROOT_HANDLER_POLICY", "all")
        guard.cleanup_root_handlers(before)
        assert sentinel not in root.handlers
    finally:
        for h in list(root.handlers):
            if h not in orig:
                root.removeHandler(h)
                h.close()
        root.handlers[:] = orig  # 還原本 session 自身 handler（M2 全清後）
    conftest = PREEXISTING_CONFTEST + f"""
    import {guard.__name__} as g
    g.ROOT_HANDLER_POLICY = "all"
"""
    res = run_pytest(_proj(tmp_path / "p2", CAPLOG_AFTER_LEAK, conftest), ["test_case.py"])
    assert res.rc != 0 and _failed_count(res.out) == 1, res.out


def test_accept_02_m3_fixture_alone_suffices_without_finally(tmp_path: Path) -> None:
    """M3：pagination 兩測試之 finally 清理移除、守衛保留 ⇒ 段 5 順序仍全過（證守衛單獨足夠）。"""
    src = PAGINATION.read_text(encoding="utf-8")
    assert src.count(FINALLY_MARK) >= 2, "施工須於兩測試 finally 清理行標記 FINALLY_MARK"
    res = _seg5_pagination_run(tmp_path, _strip_finally(src))
    assert res.rc == 0 and _failed_count(res.out) == 0, res.out
