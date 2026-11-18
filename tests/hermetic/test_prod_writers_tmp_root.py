"""TESTSEL I1a｜SPEC Task 1.2：寫正式資料之測試改暫存根。

寫入者清單＝I1a 實測（runs/testsel_route/i1a/i1a_facts.md ②，沙盒實跑定案；推翻舊清單之
`test_cube_failure_does_not_kill_scan_results`、`test_gap3_scan_grid`）。驗法：以 repo 之 pytest.ini／rootdir 跑該 nodeid，
但 cwd＝暫存目錄——三寫入者之預設根皆相對 cwd，未改則落 `<scratch>/data_cache`，可觀測且不碰正式資料。
實作前 accept_01–03 為紅（實測已寫入）。
"""
from __future__ import annotations

import ast
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests.fixtures import hermetic_guard_plugin as guard
from tests.hermetic._harness import REPO, files_under, run_pytest, run_repo_nodeids_in_scratch_cwd

LA2_PROMOTION = "tests/momentum/test_la2_lookahead.py::test_pattern_promotion_guard"
MULTI_RANGE_APPEND = "tests/test_append_fix.py::test_multi_range_append"
SCAN_CUBE_WIRING = "tests/api/test_scan_cube.py::test_wiring_scan_grid_strips_report_before_returning"


def _assert_no_default_root_write(nodeid: str, tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    res = run_repo_nodeids_in_scratch_cwd([nodeid], scratch)
    assert res.rc == 0, res.out
    assert files_under(scratch / "data_cache") == [], (nodeid, files_under(scratch / "data_cache"))


def test_accept_01_la2_promotion_guard_no_default_root_write(tmp_path: Path) -> None:
    """實測：每跑一次於預設根 `data_cache/patterns` 寫 5 個 PAT_*.json＋_index.json ⇒ 改後 0 檔且通過。"""
    _assert_no_default_root_write(LA2_PROMOTION, tmp_path)


def test_accept_02_multi_range_append_no_default_root_write(tmp_path: Path) -> None:
    """實測：連 Binance 後 append 進預設 `./data_cache/kline_cache.h5` ⇒ 改用暫存 cache_dir（保留網路路徑覆蓋）後 0 檔且通過。"""
    _assert_no_default_root_write(MULTI_RANGE_APPEND, tmp_path)


def test_accept_03_scan_cube_wiring_no_default_root_write(tmp_path: Path) -> None:
    """實測：`DEFAULT_ROOT` monkeypatch 對已綁定之預設無效，寫 `data_cache/ic_scan_cubes/t1/` ⇒ 改後 0 檔且通過。"""
    _assert_no_default_root_write(SCAN_CUBE_WIRING, tmp_path)


def test_boundary_01_real_kline_read_only_not_flagged(tmp_path: Path) -> None:
    """邊界①：只讀真實 `data_cache/feature_klines/kline_cache.h5`（data_cache 符號連結至正式根）⇒ 偵測 rc=0。"""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "data_cache").symlink_to(REPO / "data_cache")
    (proj / "test_case.py").write_text(textwrap.dedent("""
        import h5py
        def test_read_real_kline():
            # 專案 K 線庫為 h5py 階層（非 pandas HDFStore 格式），唯讀開檔取群組
            with h5py.File("data_cache/feature_klines/kline_cache.h5", "r") as f:
                assert len(list(f.keys())) > 0
    """), encoding="utf-8")
    res = run_pytest(proj, ["test_case.py"])
    assert res.rc == 0, res.out


def test_boundary_02_network_failure_not_skipped(tmp_path: Path) -> None:
    """邊界②：網路不可用 ⇒ 維持原行為（失敗而非 skip），且仍不寫預設根。"""
    fn = next(
        n for n in ast.walk(ast.parse((REPO / "tests/test_append_fix.py").read_text(encoding="utf-8")))
        if isinstance(n, ast.FunctionDef) and n.name == "test_multi_range_append"
    )
    skip_calls = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Attribute) and n.attr in {"skip", "skipif", "importorskip", "xfail"}
    ]
    assert skip_calls == [], "網路失敗不得改為 skip／xfail 掩蓋"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    dead = "http://127.0.0.1:9"
    res = run_repo_nodeids_in_scratch_cwd(
        [MULTI_RANGE_APPEND], scratch,
        env_extra={"HTTPS_PROXY": dead, "HTTP_PROXY": dead, "https_proxy": dead, "http_proxy": dead, "NO_PROXY": ""},
    )
    assert res.rc != 0 and " skipped" not in res.out, res.out
    assert files_under(scratch / "data_cache") == [], files_under(scratch / "data_cache")


def test_mutation_harness_flags_default_root_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """觀測法前提：產品預設根確實相對 cwd（`PatternStorage()` 不給 base_path ⇒ `<cwd>/data_cache/patterns`），
    故 accept_01–03 之「cwd＝暫存目錄」觀測法非恆真。"""
    from momentum.Analysis.pattern_storage import PatternStorage

    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "data_cache").exists()
    storage = PatternStorage()
    assert (tmp_path / "data_cache" / "patterns").is_dir()
    assert Path(storage.base_path).resolve() == (tmp_path / "data_cache" / "patterns").resolve()
    assert guard.PROD_DATA_DIRNAME == "data_cache"


# 修前（寫入者仍用預設根）之版本釘選：I1a 施工前整合樹 HEAD（main 合入後之 merge commit）
PRE_FIX_COMMIT = "72258590"
WRITERS = [
    (LA2_PROMOTION, "patterns/"),
    (MULTI_RANGE_APPEND, "kline_cache.h5"),
    (SCAN_CUBE_WIRING, "ic_scan_cubes/"),
]


def _run_copy_via_repo_conftest(nodeid: str, source: str, scratch: Path):  # type: ignore[no-untyped-def]
    """把 nodeid 所在檔之 source 依原相對路徑放進 scratch，cwd＝rootdir＝scratch，經 `-p tests.conftest` 跑——
    守衛須由 repo conftest 之 `pytest_plugins` 自動註冊（不 `-p` 守衛本身）。"""
    rel, fn = nodeid.split("::", 1)
    dst = scratch / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(source, encoding="utf-8")
    return run_pytest(scratch, [f"{rel}::{fn}", "-p", "tests.conftest"], plugins=())


@pytest.mark.parametrize("nodeid,written", WRITERS, ids=["la2_promotion", "multi_range_append", "scan_cube_wiring"])
def test_mutation_reverted_writer_fails_session_via_repo_conftest(nodeid: str, written: str, tmp_path: Path) -> None:
    """SPEC Task 1.2 mutation：寫入者改回預設根（修前版本，釘選 PRE_FIX_COMMIT）⇒ 經 repo conftest 註冊之 Task 1.1 偵測
    使 session 非零並列出實際寫入路徑；修後版本同法 ⇒ rc=0 且 cwd 下無 data_cache 寫入（審查 r1 codex／grok P1-02）。"""
    from momentum.Analysis.pattern_storage import PatternStorage

    assert PatternStorage.__init__.__defaults__ == ("data_cache/patterns",), "前提：產品預設根相對 cwd（不得於本項改產品預設）"
    rel = nodeid.split("::", 1)[0]
    pre_fix = subprocess.run(["git", "-C", str(REPO), "show", f"{PRE_FIX_COMMIT}:{rel}"],
                             capture_output=True, text=True, check=True).stdout
    mutant = _run_copy_via_repo_conftest(nodeid, pre_fix, tmp_path / "mutant")
    assert mutant.rc != 0 and written in mutant.out, mutant.out
    fixed = _run_copy_via_repo_conftest(nodeid, (REPO / rel).read_text(encoding="utf-8"), tmp_path / "fixed")
    assert fixed.rc == 0, fixed.out
    assert files_under(tmp_path / "fixed" / "data_cache") == [], files_under(tmp_path / "fixed" / "data_cache")
