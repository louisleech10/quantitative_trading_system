"""TESTSEL I1a｜SPEC Task 1.1：正式資料根寫入偵測擴至整個 data_cache、測試時段內寫入 ⇒ session 非零。

每案於暫存專案（不在 repo 下）建 `data_cache` 與一個測試檔，以 `-p tests.fixtures.hermetic_guard_plugin` 子行程跑。
實作前（外掛為空殼）全部為紅。
"""
from __future__ import annotations

import os
import textwrap
import time
from pathlib import Path

import pytest

from tests.fixtures import hermetic_guard_plugin as guard
from tests.hermetic._harness import run_pytest


def _project(tmp_path: Path, test_body: str, conftest: str = "") -> Path:
    proj = tmp_path / "proj"
    (proj / "data_cache" / "patterns").mkdir(parents=True)
    (proj / "data_cache" / "patterns" / "_index.json").write_text("{}", encoding="utf-8")
    (proj / "data_cache" / "kline_cache.h5").write_bytes(b"\x00" * 64)
    (proj / "test_case.py").write_text(textwrap.dedent(test_body), encoding="utf-8")
    if conftest:
        (proj / "conftest.py").write_text(textwrap.dedent(conftest), encoding="utf-8")
    return proj


WRITE_NEW_FILE = """
    from pathlib import Path
    def test_writes():
        Path("data_cache/patterns/x.json").write_text("{}")
"""

READ_ONLY = """
    from pathlib import Path
    def test_reads():
        assert Path("data_cache/patterns/_index.json").read_text() == "{}"
"""


def test_accept_01_new_file_under_nested_dir_fails_session(tmp_path: Path) -> None:
    """① 寫 `data_cache/patterns/x.json`（現行兩頂層目錄範圍外）⇒ rc≠0 且輸出具名列出該路徑。"""
    res = run_pytest(_project(tmp_path, WRITE_NEW_FILE), ["test_case.py"])
    assert res.rc != 0, res.out
    assert "patterns/x.json" in res.out, res.out


def test_accept_02_inplace_rewrite_same_size_fails_session(tmp_path: Path) -> None:
    """② 就地改寫 `data_cache/kline_cache.h5`（同大小、mtime 變）⇒ rc≠0。"""
    body = """
        from pathlib import Path
        def test_rewrite():
            p = Path("data_cache/kline_cache.h5")
            p.write_bytes(b"\\x01" * 64)
    """
    res = run_pytest(_project(tmp_path, body), ["test_case.py"])
    assert res.rc != 0, res.out
    assert "kline_cache.h5" in res.out, res.out


def test_accept_03_read_only_session_passes(tmp_path: Path) -> None:
    """③ 只讀 ⇒ rc=0。"""
    res = run_pytest(_project(tmp_path, READ_ONLY), ["test_case.py"])
    assert res.rc == 0, res.out


def test_accept_04_internal_symlink_loop_not_followed(tmp_path: Path) -> None:
    """正式 data_cache 實有自指連結 `data_cache/data_cache -> data_cache`（I1a 實測）⇒ 快照不跟隨、session 正常結束 rc=0。"""
    proj = _project(tmp_path, READ_ONLY)
    os.symlink(proj / "data_cache", proj / "data_cache" / "data_cache")
    res = run_pytest(proj, ["test_case.py"])
    assert res.rc == 0, res.out


def test_accept_05_prod_service_running_marks_result_untrusted(tmp_path: Path) -> None:
    """執行前提：session 開始／結束查到正式服務行程 ⇒ 輸出標 PRECONDITION_MARK（結果不採計）。"""
    conftest = f"""
        import {guard.__name__} as g
        g.prod_services_running = lambda: ["4242 uvicorn api.main:app"]
    """
    res = run_pytest(_project(tmp_path, READ_ONLY, conftest), ["test_case.py"])
    assert guard.PRECONDITION_MARK in res.out, res.out


def test_accept_06_deletion_detected(tmp_path: Path) -> None:
    """刪除亦算寫入（SPEC Task 1.1「新增／修改／刪除」；審查 r1 codex／grok 必答 1 補）：刪 `_index.json` ⇒ rc≠0 且列出。"""
    body = """
        from pathlib import Path
        def test_deletes():
            Path("data_cache/patterns/_index.json").unlink()
    """
    res = run_pytest(_project(tmp_path, body), ["test_case.py"])
    assert res.rc != 0, res.out
    assert "patterns/_index.json" in res.out, res.out


def test_accept_07_relative_write_from_other_cwd_detected(tmp_path: Path) -> None:
    """cwd ≠ rootdir 時，相對 cwd 之 `data_cache` 寫入亦偵測（產品預設根相對 cwd；審查 r1 P1-02）。"""
    root = tmp_path / "root"
    root.mkdir()
    cwd = _project(tmp_path / "elsewhere", WRITE_NEW_FILE)
    res = run_pytest(cwd, [str(cwd / "test_case.py")], rootdir=root)
    assert res.rc != 0, res.out
    assert "patterns/x.json" in res.out, res.out
    assert [p.resolve() for p in guard.watched_roots(root, cwd)] == [
        (root / "data_cache").resolve(), (cwd / "data_cache").resolve()
    ]


def test_accept_08_repo_conftest_registers_guard_and_drops_old_detection() -> None:
    """接線：`tests/conftest.py` 之 `pytest_plugins` 註冊本外掛，且舊 `_PROD_WRITE_DIRS` 兩頂層目錄偵測已移除
    （審查 r1 codex／grok P1-02、composer P3-04）。"""
    import ast

    from tests.hermetic._harness import REPO

    tree = ast.parse((REPO / "tests" / "conftest.py").read_text(encoding="utf-8"))
    plugins = [
        elt.value for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in node.targets)
        for elt in node.value.elts if isinstance(elt, ast.Constant)
    ]
    assert guard.__name__ in plugins, plugins
    names = {t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets if isinstance(t, ast.Name)}
    funcs = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "_PROD_WRITE_DIRS" not in names and "prod_write_snapshot" not in funcs, (names, funcs)


def test_boundary_01_symlinked_data_cache_resolved(tmp_path: Path) -> None:
    """邊界①：`data_cache` 為符號連結（worktree 實況）⇒ 解析至實體再掃；經連結寫入 ⇒ rc≠0 且列出路徑。"""
    real = tmp_path / "real_data_cache"
    (real / "patterns").mkdir(parents=True)
    proj = tmp_path / "proj"
    proj.mkdir()
    os.symlink(real, proj / "data_cache")
    (proj / "test_case.py").write_text(textwrap.dedent(WRITE_NEW_FILE), encoding="utf-8")
    res = run_pytest(proj, ["test_case.py"])
    assert guard.resolve_prod_root(proj) == real.resolve()
    assert res.rc != 0, res.out
    assert "patterns/x.json" in res.out, res.out


def test_boundary_02_write_outside_test_window_labelled_nontest(tmp_path: Path) -> None:
    """邊界②：路徑 mtime 落在無測試執行之時段 ⇒ 歸「非測試寫入」，不計入測試時段清單。"""
    now = time.time_ns()
    windows = [(now - 10_000_000_000, now - 9_000_000_000)]
    after = {"patterns/in.json": (now - 9_500_000_000, 2), "patterns/out.json": (now - 1_000_000_000, 2)}
    in_test, non_test = guard.classify_prod_writes(["patterns/in.json", "patterns/out.json"], after, windows)
    assert in_test == ["patterns/in.json"]
    assert non_test == ["patterns/out.json"]


def test_boundary_02b_nontest_write_does_not_fail_session(tmp_path: Path) -> None:
    """邊界②（session 層）：只有非測試時段之寫入 ⇒ 標 NON_TEST_MARK、rc 不因此非零。"""
    conftest = """
        import pytest
        from pathlib import Path
        @pytest.hookimpl(tryfirst=True)
        def pytest_sessionfinish(session, exitstatus):
            Path("data_cache/patterns/late.json").write_text("{}")
    """
    res = run_pytest(_project(tmp_path, READ_ONLY, conftest), ["test_case.py"])
    assert res.rc == 0, res.out
    assert guard.NON_TEST_MARK in res.out and "patterns/late.json" in res.out, res.out


def test_mutation_scope_back_to_two_dirs_misses_nested_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞對照：範圍改回兩頂層目錄（features／cgsa_work）⇒ ① 之寫入（patterns/x.json）漏抓；正式範圍則抓到。"""
    root = tmp_path / "data_cache"
    (root / "patterns").mkdir(parents=True)
    (root / "features").mkdir()

    def _diff_after_nested_write() -> list:
        before = guard.prod_write_snapshot(root)
        target = root / "patterns" / "x.json"
        target.write_text("{}")
        after = guard.prod_write_snapshot(root)
        target.unlink()
        return guard.prod_write_diff(before, after)

    assert any("patterns/x.json" in p for p in _diff_after_nested_write())
    monkeypatch.setattr(guard, "PROD_SCAN_SUBDIRS", ("features", "cgsa_work"))
    assert not any("patterns/x.json" in p for p in _diff_after_nested_write())
