"""FF-STAT Task 3.1：d* 讀／搜尋／寫三出口 fail-closed（docs/FFSTAT_SPEC.md §C「d* 三出口」）。

整合測試以輕量真實 run（append 模式；平穩化結果為衍生欄 `<欄>_fracdiff`／`<欄>_diffK`）驗；
d* 快取目錄一律隔離於 tmp。實作前應為紅。
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pyarrow.parquet as pq
import pytest

from momentum.FeatureEngineering import feature_storage as fs_module
from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as spp
from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as h

EV = h.EVENTS
API = h.CONTRACT["dstar_cache_api"]


def _derived(root: Path) -> List[str]:
    return [n for p in root.rglob("*_L65.parquet") for n in pq.ParquetFile(p).schema_arrow.names]


def _failed_columns(result: Any, event: str) -> List[str]:
    return [c for c, d in h.decisions(result).items() if event in d["events"]]


def _assert_search_failed_one(root: Path, result: Any, dstar_dir: Path) -> None:
    failed = _failed_columns(result, EV["search_failed"])
    assert len(failed) == 1, failed
    col = failed[0]
    derived = set(_derived(root))
    assert not any(n.startswith(col + "_fracdiff") or n.startswith(col + "_diff") for n in derived), col
    dec = h.decisions(result)[col]
    assert dec["fracdiff"] is False and dec["d"] is None and dec["adf_differenced"] is False
    entries = {k for f in dstar_dir.glob("*.json") for k in json.loads(f.read_text(encoding="utf-8"))["entries"]}
    fracdiffed = [c for c, d in h.decisions(result).items() if d["fracdiff"]]
    assert len(entries) == len(fracdiffed)
    meta = result.metadata
    manifest = json.loads(Path(meta["manifest_path"]).read_text(encoding="utf-8"))
    for src in (meta, manifest):
        assert f"{EV['search_failed']}:1" in src["failure_reasons"]
        assert src["quality_status"] == "partial"


def _fail_first_serial_search(monkeypatch: pytest.MonkeyPatch) -> None:
    real = FeaturePreprocessor._find_min_d
    calls = {"n": 0}

    def _mutant(self, series, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("injected d* search failure")
        return real(self, series, **kw)

    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", _mutant)


def _inline_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    """平行路徑改在主程序內逐項執行（loky 子程序看不到 monkeypatch），並強制 n_jobs=2 走平行分支之結果處理。"""
    monkeypatch.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self, *a, **k: 2)
    monkeypatch.setattr(spp.ParallelSlowPath, "map",
                        lambda self, items, worker_function: [worker_function(np.asarray(v, dtype=np.float64), dict(m))
                                                              for v, m in items])


def _fail_first_parallel_search(monkeypatch: pytest.MonkeyPatch) -> None:
    real = spp.find_min_d_with_prior
    calls = {"n": 0}

    def _mutant(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("injected worker d* search failure")
        return real(*a, **k)

    _inline_parallel(monkeypatch)
    monkeypatch.setattr(spp, "find_min_d_with_prior", _mutant)


@pytest.mark.parametrize("path", ["serial", "parallel", "frame"])
def test_search_failure_keeps_original_and_degrades(path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 驗證：注入 d* 搜尋例外（ADF 差分同時開啟）⇒ 該欄無衍生欄、快取無該欄、manifest 與
    result.metadata 之 failure_reasons 皆含 `fracdiff_search_failed:1`、quality_status == partial。"""
    env = {"FFACT_USE_CGSA": "0"} if path == "frame" else {"FFACT_USE_CGSA": "1"}
    dstar = h.prepare_stat_env(monkeypatch, tmp_path, **env)
    if path == "parallel":
        _fail_first_parallel_search(monkeypatch)
    else:
        _fail_first_serial_search(monkeypatch)
    root, _, result = h.run_stat(tmp_path, h.stat_payload())
    _assert_search_failed_one(root, result, dstar)


# ---------------------------------------------------------------- 邊界①：讀取失敗

@pytest.fixture(scope="module")
def warm_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """先以冷快取跑一次，留下 d* 快取檔（邊界①之損壞對象）。"""
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("ffstat_warm")
    try:
        dstar = h.prepare_stat_env(mp, tmp)
        h.run_stat(tmp, h.stat_payload())
        assert list(dstar.glob("*.json"))
        return dstar
    finally:
        mp.undo()


_CORRUPT = {
    "not_json": lambda text: "{",
    "top_level_array": lambda text: "[]",
    "entries_not_object": lambda text: json.dumps({**json.loads(text), "entries": []}),
}


@pytest.mark.parametrize("shape", sorted(_CORRUPT) + ["load_oserror", "get_raises"])
def test_boundary_14_cache_read_failure_event_and_search(shape: str, warm_cache: Path, tmp_path: Path,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 邊界①：快取三種壞檔形狀、載入 OSError、單欄 cache.get 例外 ⇒ 事件 dstar_cache_read_failed、
    該欄照常搜尋套用（有 `_fracdiff` 衍生欄或決策明確）、quality_status == partial。"""
    dstar = h.prepare_stat_env(monkeypatch, tmp_path)
    for f in warm_cache.glob("*.json"):
        shutil.copy2(f, dstar / f.name)
    files = list(dstar.glob("*.json"))
    if shape in _CORRUPT:
        for f in files:
            f.write_text(_CORRUPT[shape](f.read_text(encoding="utf-8")), encoding="utf-8")
    elif shape == "load_oserror":
        real_read = Path.read_text
        targets = {str(f) for f in files}

        def _read(self, *a, **k):
            if str(self) in targets:
                raise OSError("injected load failure")
            return real_read(self, *a, **k)

        monkeypatch.setattr(Path, "read_text", _read)
    else:
        real_get = DStarCache.get
        calls = {"n": 0}

        def _get(self, column, col_values=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("injected cache.get failure")
            return real_get(self, column, col_values)

        monkeypatch.setattr(DStarCache, "get", _get)
    root, _, result = h.run_stat(tmp_path, h.stat_payload())
    affected = _failed_columns(result, EV["cache_read_failed"])
    assert affected
    dec = h.decisions(result)
    assert all(dec[c]["d"] is not None or dec[c]["fracdiff"] is False for c in affected)
    assert result.metadata["quality_status"] == "partial"
    assert any(r.startswith(EV["cache_read_failed"] + ":") for r in result.metadata["failure_reasons"])


def test_boundary_14b_missing_cache_file_no_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 邊界①：快取檔不存在（冷快取）⇒ 無 dstar_cache_read_failed 事件。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    _, _, result = h.run_stat(tmp_path, h.stat_payload())
    assert not _failed_columns(result, EV["cache_read_failed"])
    assert not any(r.startswith(EV["cache_read_failed"]) for r in result.metadata["failure_reasons"])


def test_cache_load_error_distinguished_from_missing(tmp_path: Path) -> None:
    """Task 3.1：`DStarCache` 載入失敗與檔案不存在分開回報（契約 `dstar_cache_api.load_error_attr`）。"""
    ctx = PreprocessingContext(symbol=h.SYMBOL, timeframe=h.PRIMARY_TF, config_hash="cfg")
    missing = DStarCache(ctx, tmp_path / "a")
    assert getattr(missing, API["load_error_attr"]) is None
    first = DStarCache(ctx, tmp_path / "b")
    first.set("close_trend_EMA_10", 0.45, h.kline_frame()["close"].to_numpy()[:500])
    assert first.flush_atomic() is True
    for f in (tmp_path / "b").glob("*.json"):
        f.write_text("{", encoding="utf-8")
    broken = DStarCache(ctx, tmp_path / "b")
    assert getattr(broken, API["load_error_attr"])


# ---------------------------------------------------------------- 邊界①′：交錯 flush

def test_boundary_15_interleaved_flush_last_writer_wins(tmp_path: Path) -> None:
    """Task 3.1 邊界①′：同路徑兩個 DStarCache 實例交錯 flush_atomic ⇒ 後寫者勝出、先寫之項下次為未命中、無事件。"""
    ctx = PreprocessingContext(symbol=h.SYMBOL, timeframe=h.PRIMARY_TF, config_hash="cfg")
    values = h.kline_frame()["close"].to_numpy()
    a, b = DStarCache(ctx, tmp_path), DStarCache(ctx, tmp_path)
    b.set("col_b", 0.4, values[:500])
    assert b.flush_atomic() is True
    a.set("col_a", 0.2, values[500:1000])
    assert a.flush_atomic() is True
    reread = DStarCache(ctx, tmp_path)
    assert reread.get("col_a", values[500:1000]) == pytest.approx(0.2)
    assert reread.get("col_b", values[:500]) is None
    assert getattr(reread, API["load_error_attr"]) is None


# ---------------------------------------------------------------- 邊界②：寫入失敗

@pytest.mark.parametrize("where", ["set", "os_replace"])
def test_boundary_16_cache_write_failure_applies_and_degrades(where: str, tmp_path: Path,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 邊界②：單欄 cache.set 例外與 flush_atomic 之 os.replace 失敗各一 ⇒ 值照常套用、
    事件 `dstar_cache_write_failed:<欄數>`、quality_status == partial。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    if where == "set":
        real_set = DStarCache.set
        calls = {"n": 0}

        def _set(self, column, d_star, col_values=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("injected cache.set failure")
            return real_set(self, column, d_star, col_values)

        monkeypatch.setattr(DStarCache, "set", _set)
    else:
        from momentum.FeatureEngineering.preprocessing import _d_star_cache as dmod

        monkeypatch.setattr(dmod.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("injected replace")))
    root, _, result = h.run_stat(tmp_path, h.stat_payload())
    reasons = [r for r in result.metadata["failure_reasons"] if r.startswith(EV["cache_write_failed"] + ":")]
    assert len(reasons) == 1 and int(reasons[0].split(":")[1]) >= 1
    assert result.metadata["quality_status"] == "partial"
    fracdiffed = [c for c, d in h.decisions(result).items() if d["fracdiff"]]
    assert fracdiffed and {c + "_fracdiff" for c in fracdiffed} <= set(_derived(root))


def test_flush_atomic_reports_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1：flush_atomic 之 os.replace 失敗 ⇒ 回報 False（不再只記 warning）。"""
    from momentum.FeatureEngineering.preprocessing import _d_star_cache as dmod

    ctx = PreprocessingContext(symbol=h.SYMBOL, timeframe=h.PRIMARY_TF, config_hash="cfg")
    cache = DStarCache(ctx, tmp_path)
    cache.set("col", 0.3, h.kline_frame()["close"].to_numpy()[:500])
    monkeypatch.setattr(dmod.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("injected replace")))
    assert cache.flush_atomic() is False


# ---------------------------------------------------------------- 邊界③④⑤

def test_boundary_17_parallel_worker_failure_not_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 邊界③：parallel worker 搜尋失敗 ⇒ 快取無該欄（主程序先判 status 再寫快取）。"""
    dstar = h.prepare_stat_env(monkeypatch, tmp_path)
    _fail_first_parallel_search(monkeypatch)
    root, _, result = h.run_stat(tmp_path, h.stat_payload())
    _assert_search_failed_one(root, result, dstar)


def test_boundary_18_all_columns_fail_run_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 邊界④：全部欄 d* 搜尋皆例外 ⇒ run quality_status == partial，無任何 `_fracdiff` 衍生欄。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d",
                        lambda self, series, **kw: (_ for _ in ()).throw(RuntimeError("all fail")))
    root, _, result = h.run_stat(tmp_path, h.stat_payload(adf=False))
    assert result.metadata["quality_status"] == "partial"
    assert not any(n.endswith("_fracdiff") for n in _derived(root))


_META_CASES = [
    {"quality_status": "complete", "run_status": "complete", "failure_reasons": []},
    {"quality_status": "partial", "run_status": "complete", "failure_reasons": ["L2:12h:dependency_failed"]},
]


@pytest.mark.parametrize("meta", _META_CASES)
def test_boundary_19_no_events_identical_to_fftfmeta(meta: Dict[str, Any]) -> None:
    """Task 3.1 邊界⑤：無事件 ⇒ apply_quality_degradation 輸出與 FF-TFMETA 現行（不帶新參數）逐位元組相同。"""
    kw = dict(inf_ratio=0.0, nan_ratio=0.01, max_inf_ratio=0.0, max_nan_ratio=1.0, preprocessing_applied=True)
    legacy = fs_module.apply_quality_degradation(dict(meta), **kw)
    new = fs_module.apply_quality_degradation(dict(meta), **kw, extra_failure_reasons=())
    assert json.dumps(new, sort_keys=True) == json.dumps(legacy, sort_keys=True)


def test_extra_failure_reasons_degrade_to_partial() -> None:
    """Task 3.1：`extra_failure_reasons` 非空 ⇒ 併入 failure_reasons 並降為 partial。"""
    kw = dict(inf_ratio=0.0, nan_ratio=0.0, max_inf_ratio=0.0, max_nan_ratio=1.0, preprocessing_applied=True)
    out = fs_module.apply_quality_degradation(dict(_META_CASES[0]), **kw,
                                              extra_failure_reasons=(f"{EV['search_failed']}:2",))
    assert f"{EV['search_failed']}:2" in out["failure_reasons"] and out["quality_status"] == "partial"


# ---------------------------------------------------------------- mutation

def test_mutation_degradation_ignores_events_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V：品質降級忽略欄級事件 ⇒ 併入測試必紅。"""
    real = fs_module.apply_quality_degradation

    def _mutant(meta, *, extra_failure_reasons=(), **kw):
        return real(meta, **kw)

    monkeypatch.setattr(fs_module, "apply_quality_degradation", _mutant)
    with pytest.raises(AssertionError):
        test_extra_failure_reasons_degrade_to_partial()


def test_mutation_flush_swallows_error_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑫：flush_atomic 失敗改回只記 warning（回傳 None）⇒ 回報測試必紅。"""
    monkeypatch.setattr(DStarCache, "flush_atomic", lambda self: None)
    with pytest.raises(AssertionError):
        test_flush_atomic_reports_failure(tmp_path, monkeypatch)
