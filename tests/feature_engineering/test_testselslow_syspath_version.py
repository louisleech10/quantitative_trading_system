"""TESTSELSLOW 根因一（2026-11-15）之回歸測試。

根因：`scripts/ffname_refreeze.py` 逐欄呼叫之輔助函式內無條件 `sys.path.insert(0, MAIN_REPO)`，同一 pytest 行程之
sys.path 由 42 項增至 3,684 項；`numeric_view.library_version` 每次直呼 `importlib.metadata.version`（Python 3.9 逐項列
sys.path 目錄、無快取），每次 0.004 s → 0.54 s，全量後段每條走特徵生成之測試多十餘秒。

驗：① 重複呼叫各入口後 sys.path 長度不變、MAIN_REPO 恰一項且在首位（absent／already-first／present-later 三情境，
保留原「置首」語意）；② `library_version` 之值＝`importlib.metadata.version`（契約全部套件；未安裝＝`absent`），
同 name 第二次起不再呼叫 `importlib.metadata.version`，`cache_clear()` 後重讀。
"""
from __future__ import annotations

import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load(rel: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture
def isolated_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試內 sys.path 改動於結束時還原。"""
    monkeypatch.setattr(sys, "path", list(sys.path))


@pytest.fixture(scope="module")
def refreeze() -> Any:
    return _load("scripts/ffname_refreeze.py", "ffname_refreeze_testselslow")


@pytest.mark.parametrize("state", ["absent", "already_first", "present_later"])
def test_ffname_refreeze_main_repo_first_no_growth(refreeze: Any, isolated_path: None, state: str) -> None:
    main = str(refreeze.MAIN_REPO)
    others = [p for p in sys.path if p != main]
    if state == "absent":
        sys.path[:] = others
    elif state == "already_first":
        sys.path[:] = [main] + others
    else:
        sys.path[:] = others[:1] + [main] + others[1:]
    for _ in range(50):
        refreeze.framepath_new_group_id("1h_L1_trend_BBANDS-Lower", "close_trend_BBANDS-Lower_13")
        refreeze.tagged_column_of_key("1h_L4_lag/ohlc_pattern_BullishCount_5_Lag-1")
    assert sys.path[0] == main
    assert sys.path.count(main) == 1
    assert len(sys.path) == len(others) + 1
    assert sys.path[1:] == others  # 其餘路徑之相對順序不變


def test_ffname_refreeze_no_raw_unguarded_insert() -> None:
    """同類全部實例：工具內不得再有無條件 `sys.path.insert(0, str(MAIN_REPO))`（一律經 `_main_repo_first`）。"""
    text = (REPO / "scripts" / "ffname_refreeze.py").read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(MAIN_REPO))" not in text
    assert text.count("_main_repo_first()") >= 7


def test_framepath_refreeze_path_first_no_growth(isolated_path: None) -> None:
    rp = _load("scripts/framepath_refreeze_provenance_v2.py", "framepath_refreeze_provenance_v2_testselslow")
    target = str(REPO)
    others = [p for p in sys.path if p != target]
    sys.path[:] = others[:1] + [target] + others[1:]
    for _ in range(50):
        rp._path_first(target)
    assert sys.path[0] == target and sys.path.count(target) == 1 and sys.path[1:] == others


def test_library_version_cached_equals_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    from momentum.FeatureEngineering import numeric_view as nv

    names = list(nv.load_contract()["library_versions"]["values"])
    assert names, "契約 library_versions 為空"
    nv.library_version.cache_clear()
    calls: list = []
    real = importlib.metadata.version

    def counting(name: str) -> str:
        calls.append(name)
        return real(name)

    monkeypatch.setattr(importlib.metadata, "version", counting)
    for name in names:
        try:
            expect = real(name)
        except importlib.metadata.PackageNotFoundError:
            expect = "absent"
        assert nv.library_version(name) == expect
    first = len(calls)
    assert first == len(names)
    for _ in range(5):
        for name in names:
            nv.library_version(name)
    assert len(calls) == first, "同 name 第二次起不得再讀 importlib.metadata"
    nv.library_version.cache_clear()
    nv.library_version(names[0])
    assert len(calls) == first + 1, "cache_clear 後須重讀"
    nv.library_version.cache_clear()


def test_library_version_absent_package() -> None:
    from momentum.FeatureEngineering import numeric_view as nv

    nv.library_version.cache_clear()
    assert nv.library_version("testselslow-no-such-distribution") == "absent"
    nv.library_version.cache_clear()
