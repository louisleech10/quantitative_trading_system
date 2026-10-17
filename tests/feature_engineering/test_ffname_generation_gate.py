"""FF-NAME Task 3.4 — 命名世代閘（docs/FFNAME_SPEC.md Task 3.4）。

共同邊界＝`feature_reader.py` 內單一私有 manifest 解析函式（全部 V2 讀取方法皆經它；缺鍵、舊版、無法解析即拒）；
特徵 run 之 parquet 只准經 `FeatureReader` 開啟；凡接受特徵檔路徑之入口先解析為 canonical run 再經 reader（移除任意
`.parquet`／`.h5` 退路）；多標的合併點（`feature_library.load_multi`、`cross_symbol_training_service`、
`xgboost_batch_service` 交集前）再驗版本一致。
邊界：①單標的缺鍵亦拒 ②非特徵矩陣之快取（統計 parquet）具名排除。
驗證：reader 每個 V2 讀取方法與各 direct 呼叫者各一例缺鍵／舊版／無法解析 ⇒ 拒（訊息含 manifest 鍵）、同版通過且回傳
== 無閘時；三個多標的合併點各一例兩標的版本不一 ⇒ 拒；`feature_factory_service` 瀏覽、選欄、相關矩陣路徑與
`ic_analysis_service` apply-transforms 路徑拒且不先回傳 DataFrame；`ic_filter_orchestrator` stage0 以非 canonical run 之
`.h5` 路徑 ⇒ 拒；靜態封閉（白名單 `tests/_golden/ffname/read_whitelist.json`）。
fixture：以正式 `FeatureStorage.write_raw` 寫 V2 run，欄值取真實 kline（API／讀取單元 fixture；非生成正確性證據）。
mutation：§V ⑧移除 reader 共同邊界或任一合併點之世代閘。
v13：拒收一律 `FeatureNamingVersionError(RuntimeError)`（呼叫端包裝時例外鏈須含之）；canonical run＝特徵根下
`<symbol>/<timeframe>/<config_hash>/`（或其 manifest）且 registry 有條目；xgboost 合併點以替身驅動之單元測試＋AST 並行；
靜態封閉 `scripts/tmp/` 具名排除。
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterator, List, Tuple

import h5py
import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.feature_library import FeatureLibrary
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering.ffname_helpers import (
    GATE_KEY,
    REPO,
    VALID,
    WHITELIST_PATH,
    chain_has,
    kline_symbols,
    patch_everywhere,
    real_slice,
)
from tests.feature_engineering.ffstat_helpers import PRIMARY_TF, SYMBOL

TF = PRIMARY_TF
CFG = "cfg_ffname_gate"
MODES = ("missing", "old", "unparsable")
COLS = [VALID["multi_output"], VALID["microstructure"]]


def _write_run(base: Path, symbol: str = SYMBOL, cfg: str = CFG) -> Path:
    storage = FeatureStorage(str(base))
    kline = real_slice(32, symbol=symbol)
    frame = pd.DataFrame({c: kline["close"].to_numpy(dtype=np.float32) for c in COLS}, index=kline.index)
    raw_dir = storage.write_raw(symbol, TF, cfg, {"g": frame}, row_index=pd.DatetimeIndex(kline.index))
    manifest = raw_dir.parent / "feature_manifest.json"
    assert json.loads(manifest.read_text(encoding="utf-8")).get(GATE_KEY) == fn.CURRENT_FEATURE_NAMING_VERSION
    return manifest


@contextlib.contextmanager
def tampered(manifest: Path, mode: str) -> Iterator[None]:
    original = manifest.read_bytes()
    data = json.loads(original)
    if mode == "missing":
        data.pop(GATE_KEY, None)
    elif mode == "old":
        data[GATE_KEY] = fn.CURRENT_FEATURE_NAMING_VERSION - 1
    elif mode == "unparsable":
        data[GATE_KEY] = "two"
    elif isinstance(mode, int):
        data[GATE_KEY] = mode
    manifest.write_text(json.dumps(data), encoding="utf-8")
    try:
        yield
    finally:
        manifest.write_bytes(original)


def _rejects(call: Callable[[], Any]) -> bool:
    """呼叫拋 `FeatureNamingVersionError`（或呼叫端包裝而其例外鏈含之）且訊息含 manifest 版本鍵 ⇒ True；
    回傳任何結果或拋其他例外 ⇒ False（SPEC v13 例外型別）。"""
    try:
        result = call()
        if hasattr(result, "__next__"):
            next(result)
    except Exception as exc:  # noqa: BLE001
        return chain_has(exc, fn.FeatureNamingVersionError) and GATE_KEY in str(exc)
    return False


def _reader_calls(reader: FeatureReader, symbol: str = SYMBOL) -> Dict[str, Callable[[], Any]]:
    return {
        "load_manifest_v2": lambda: reader.load_manifest_v2(symbol, TF, CFG),
        "load_columns_v2": lambda: reader.load_columns_v2(symbol, TF, CFG, COLS),
        "load_row_index_v2": lambda: reader.load_row_index_v2(symbol, TF, CFG),
        "stream_groups_v2": lambda: reader.stream_groups_v2(symbol, TF, CFG),
        "list_features_v2": lambda: reader.list_features_v2(symbol, TF, CFG),
    }


# ---------------------------------------------------------------- 邊界

def test_boundary_01_single_symbol_missing_key_rejected(tmp_path):
    manifest = _write_run(tmp_path / "features")
    reader = FeatureReader(str(tmp_path / "features"))
    with tampered(manifest, "missing"):
        assert _rejects(_reader_calls(reader)["load_columns_v2"])


def _scan_reads(roots) -> List[Tuple[str, str, str]]:
    wl = json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
    calls = {tuple(c.split(".")) for c in wl["calls"]}
    out: List[Tuple[str, str, str]] = []
    for root in roots:
        for p in sorted((REPO / root).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            def visit(node, qual):
                for ch in ast.iter_child_nodes(node):
                    if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        visit(ch, qual + [ch.name])
                        continue
                    if (isinstance(ch, ast.Call) and isinstance(ch.func, ast.Attribute)
                            and isinstance(ch.func.value, ast.Name) and (ch.func.value.id, ch.func.attr) in calls):
                        out.append((str(p.relative_to(REPO)), ".".join(qual) or "<module>", f"{ch.func.value.id}.{ch.func.attr}"))
                    visit(ch, qual)

            visit(tree, [])
    return out


def test_boundary_02_stats_parquet_cache_named_exclusion():
    wl = json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
    entries = {(e["path"], e["qualname"], e["call"]): e["purpose"] for e in wl["entries"]}
    stats_key = ("api/services/feature_factory_service.py", "FeatureFactoryService._load_cgsa_stats_mem", "pd.read_parquet")
    assert stats_key in entries and "統計" in entries[stats_key]
    live = set(_scan_reads(["api"]))
    assert stats_key in live  # 白名單項須對應實存呼叫（防過期白名單）


# ---------------------------------------------------------------- reader 共同邊界

@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("method", ["load_manifest_v2", "load_columns_v2", "load_row_index_v2", "stream_groups_v2", "list_features_v2"])
def test_reader_methods_reject(tmp_path, mode, method):
    manifest = _write_run(tmp_path / "features")
    reader = FeatureReader(str(tmp_path / "features"))
    with tampered(manifest, mode):
        assert _rejects(_reader_calls(reader)[method]), (method, mode)


def test_reader_same_version_passes_and_equals_ungated(tmp_path, monkeypatch):
    manifest = _write_run(tmp_path / "features")
    reader = FeatureReader(str(tmp_path / "features"))
    gated = reader.load_columns_v2(SYMBOL, TF, CFG, COLS)
    patch_everywhere(monkeypatch, fn.assert_feature_naming_version, lambda *a, **k: None)
    ungated = reader.load_columns_v2(SYMBOL, TF, CFG, COLS)
    pd.testing.assert_frame_equal(gated, ungated)


def test_gate_functions_contract():
    assert issubclass(fn.FeatureNamingVersionError, RuntimeError)
    fn.assert_feature_naming_version({GATE_KEY: fn.CURRENT_FEATURE_NAMING_VERSION})
    for bad in ({}, {GATE_KEY: fn.CURRENT_FEATURE_NAMING_VERSION - 1}, {GATE_KEY: "two"}):
        with pytest.raises(fn.FeatureNamingVersionError, match=GATE_KEY):
            fn.assert_feature_naming_version(bad)
    current = fn.CURRENT_FEATURE_NAMING_VERSION
    fn.assert_single_feature_naming_version({"A": {GATE_KEY: current}, "B": {GATE_KEY: current}})
    with pytest.raises(fn.FeatureNamingVersionError, match=GATE_KEY):
        fn.assert_single_feature_naming_version({"A": {GATE_KEY: current}, "B": {GATE_KEY: current + 1}})


# ---------------------------------------------------------------- direct 呼叫者

@pytest.mark.parametrize("mode", MODES)
def test_ic_engine_row_index_rejects(tmp_path, mode):
    from momentum.Analysis.ic_engine import ICEngine

    manifest = _write_run(tmp_path / "features")
    reader = FeatureReader(str(tmp_path / "features"))
    with tampered(manifest, mode):
        assert _rejects(lambda: ICEngine._load_raw_row_index(reader, SYMBOL, TF, CFG))


@pytest.mark.parametrize("mode", MODES)
def test_coverage_analyzer_does_not_load_rejected_run(tmp_path, mode):
    from momentum.Analysis.coverage_analyzer import CoverageAnalyzer

    base = tmp_path / "features"
    manifest = _write_run(base)
    analyzer = CoverageAnalyzer(feature_reader_factory=lambda path: FeatureReader(path))
    assert isinstance(analyzer._load_symbol_features(SYMBOL, TF, str(base)), pd.DataFrame)
    with tampered(manifest, mode):
        assert analyzer._load_symbol_features(SYMBOL, TF, str(base)) is None


@pytest.mark.parametrize("mode", MODES)
def test_event_materialization_rejects(tmp_path, monkeypatch, mode):
    import momentum.factories as factories
    from momentum.Analysis.event_samples.feature_materialization import materialize_features_at_decision

    base = tmp_path / "features"
    manifest = _write_run(base)
    fake_ff = SimpleNamespace(generate_features=lambda *a, **k: SimpleNamespace(metadata={"config_hash": CFG}))
    monkeypatch.setattr(factories, "create_feature_factory", lambda *a, **k: fake_ff)
    monkeypatch.setattr(factories, "create_feature_reader", lambda *a, **k: FeatureReader(str(base)))
    receipts = SimpleNamespace(per_tf=pd.DataFrame({"event_id": ["e1"], "timeframe": [TF]}))
    events = pd.DataFrame({"event_id": ["e1"], "symbol": [SYMBOL]})
    with tampered(manifest, mode):
        assert _rejects(lambda: materialize_features_at_decision(receipts, {}, {"config_override": {}}, events=events))


def _library(base: Path, entries: List[Tuple[str, Path]]) -> FeatureLibrary:
    registry = FeatureRegistry(base / "registry.json")
    for symbol, manifest in entries:
        registry.add({"symbol": symbol, "timeframe": TF, "config_hash": CFG, "hdf5_relative_path": str(manifest)})
    return FeatureLibrary(registry, FeatureStorage(str(base)), feature_reader=FeatureReader(str(base)))


@pytest.mark.parametrize("mode", MODES)
def test_feature_library_load_rejects(tmp_path, mode):
    base = tmp_path / "features"
    manifest = _write_run(base)
    library = _library(base, [(SYMBOL, manifest)])
    with tampered(manifest, mode):
        assert _rejects(lambda: library.load(SYMBOL, TF, config_hash=CFG))


@pytest.mark.parametrize("mode", MODES)
def test_ic_analysis_transforms_path_rejects(tmp_path, mode):
    from api.services.ic_analysis_service import ICAnalysisService

    base = tmp_path / "features"
    manifest = _write_run(base)
    service = ICAnalysisService()
    service._feature_library = _library(base, [(SYMBOL, manifest)])  # canonical run：特徵根下＋registry 有條目（v13）
    assert isinstance(service._load_features_for_transforms(None, None, str(manifest)), pd.DataFrame)
    with tampered(manifest, mode):
        assert _rejects(lambda: service._load_features_for_transforms(None, None, str(manifest)))


def _non_canonical_rejected(service, path: str) -> bool:
    """非 canonical run 路徑 ⇒ 產生任何 DataFrame 前拒收（不得回傳 DataFrame）。"""
    try:
        result = service._load_features_for_transforms(None, None, path)
    except Exception:  # noqa: BLE001
        return True
    return not isinstance(result, pd.DataFrame)


def test_ic_analysis_arbitrary_parquet_path_rejected_before_dataframe(tmp_path):
    from api.services.ic_analysis_service import ICAnalysisService

    base = tmp_path / "features"
    manifest = _write_run(base)
    loose = tmp_path / "loose.parquet"
    loose.write_bytes(next(manifest.parent.rglob("*.parquet")).read_bytes())
    service = ICAnalysisService()
    service._feature_library = _library(base, [(SYMBOL, manifest)])
    assert _non_canonical_rejected(service, str(loose))


def test_ic_analysis_canonical_layout_without_registry_entry_rejected(tmp_path):
    """v13 canonical run 判定：路徑形似 `<symbol>/<tf>/<config_hash>/feature_manifest.json` 但 registry 無對應條目 ⇒ 拒。"""
    from api.services.ic_analysis_service import ICAnalysisService

    base = tmp_path / "features"
    manifest = _write_run(base)
    service = ICAnalysisService()
    service._feature_library = _library(base, [])
    assert _non_canonical_rejected(service, str(manifest))


def test_orchestrator_stage0_non_canonical_h5_rejected(tmp_path, monkeypatch):
    import momentum.Analysis.ic_filter_orchestrator as orch_mod
    from momentum.Analysis.ic_config_schema import ICConfig

    kline = real_slice(32)
    h5 = tmp_path / "loose_features.h5"
    labels = tmp_path / "labels.h5"
    for path in (h5, labels):
        with h5py.File(path, "w") as f:
            f.create_dataset(f"{SYMBOL}/{TF}/close", data=kline["close"].to_numpy())
    opened: List[str] = []
    real_file = h5py.File

    def spy(path, *a, **k):
        opened.append(str(path))
        return real_file(path, *a, **k)

    monkeypatch.setattr(orch_mod.h5py, "File", spy)
    with pytest.raises(Exception):
        orch_mod.ICFilterOrchestrator(ICConfig())._stage0_ingestion(str(h5), str(labels), None)
    assert str(h5) not in opened


# ---------------------------------------------------------------- feature_factory_service

def _service(manifest: Path):
    from api.services.feature_factory_service import FeatureFactoryService

    service = FeatureFactoryService()
    with service._lock:
        service._tasks = {"t": {"status": "completed", "result": {
            "hdf5_path": str(manifest), "metadata": {"symbol": SYMBOL, "timeframe": TF, "config_hash": CFG},
            "generation_time": 1.0, "layer_counts": {}}}}
    return service


@pytest.mark.parametrize("mode", MODES)
def test_feature_factory_service_paths_reject(tmp_path, mode):
    manifest = _write_run(tmp_path / "features")
    service = _service(manifest)
    with tampered(manifest, mode):
        assert _rejects(lambda: service.browse_features("t", 0, 10, None, "asc", None, None, None, "names"))
        assert _rejects(lambda: service.browse_feature_data("t", [COLS[0]], 0, 10))
        assert _rejects(lambda: service.browse_correlation("t", COLS, "pearson"))


# ---------------------------------------------------------------- 多標的合併點

def _two_symbol_library(tmp_path) -> Tuple[FeatureLibrary, Path, str]:
    base = tmp_path / "features"
    other = next(s for s in kline_symbols() if s != SYMBOL)
    m_a = _write_run(base, SYMBOL)
    m_b = _write_run(base, other)
    return _library(base, [(SYMBOL, m_a), (other, m_b)]), m_b, other


def _mixed_rejected(call: Callable[[], Any], manifest_b: Path) -> bool:
    with tampered(manifest_b, fn.CURRENT_FEATURE_NAMING_VERSION + 1):
        return _rejects(call)


def test_load_multi_rejects_mixed_versions(tmp_path):
    library, m_b, other = _two_symbol_library(tmp_path)
    assert isinstance(library.load_multi([SYMBOL, other], TF, config_hashes={SYMBOL: CFG, other: CFG}), dict)
    assert _mixed_rejected(lambda: library.load_multi([SYMBOL, other], TF, config_hashes={SYMBOL: CFG, other: CFG}), m_b)


def test_cross_symbol_training_rejects_mixed_versions(tmp_path):
    from api.services.cross_symbol_training_service import CrossSymbolTrainingService

    library, m_b, other = _two_symbol_library(tmp_path)
    service = CrossSymbolTrainingService()
    service._feature_library = library
    call = lambda: asyncio.run(service.run_cross_symbol_validation([SYMBOL, other], TF))
    assert _mixed_rejected(call, m_b)


def _xgboost_task_after_run(library: FeatureLibrary, other: str) -> Dict[str, Any]:
    """以替身驅動 `_run_batch_analysis`（K 線服務與任務管理替身；K 線值取真實 kline），回傳任務狀態。"""
    import logging

    from api.services.xgboost_batch_service import BatchTaskManager, XGBoostBatchService

    service = XGBoostBatchService.__new__(XGBoostBatchService)  # 不建構 K 線下載等外部依賴
    service.task_manager = BatchTaskManager()
    service.task_manager.create_task("ffname-xgb", 1)
    service.logger = logging.getLogger("ffname.xgboost_stub")
    service._feature_library = library
    klines = {s: real_slice(64, symbol=s) for s in (SYMBOL, other)}
    service._get_kline_data = lambda symbol, timeframe, start_time, end_time: klines[symbol]
    ts = int(klines[SYMBOL].index[-10].timestamp())
    cases = [SimpleNamespace(case_id="c1", timestamp=ts, symbol=SYMBOL, positive_case=True)]
    asyncio.run(service._run_batch_analysis(
        "ffname-xgb", [SYMBOL, other], TF, cases, [], None, 10, None, "aggregate", 1, None, None,
        False, None, None, None, "xgboost", None, False, 2, 5, 1))
    return service.task_manager.get_task("ffname-xgb")


def test_xgboost_batch_rejects_mixed_versions_with_stubs(tmp_path):
    library, m_b, other = _two_symbol_library(tmp_path)
    clean = _xgboost_task_after_run(library, other)
    assert GATE_KEY not in str(clean.get("error") or "")
    with tampered(m_b, fn.CURRENT_FEATURE_NAMING_VERSION + 1):
        task = _xgboost_task_after_run(library, other)
    assert task["status"] == "failed"
    assert GATE_KEY in str(task.get("error") or "")


def test_xgboost_batch_checks_versions_before_intersection():
    tree = ast.parse((REPO / "api/services/xgboost_batch_service.py").read_text(encoding="utf-8"))
    fn_node = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_run_batch_analysis")
    lines = {"assert": [], "intersect": []}
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Call):
            name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
            if name == "assert_single_feature_naming_version":
                lines["assert"].append(n.lineno)
            if name == "intersect_columns_without_masking":
                lines["intersect"].append(n.lineno)
    assert lines["assert"] and lines["intersect"]
    assert min(lines["assert"]) < min(lines["intersect"])


# ---------------------------------------------------------------- 靜態封閉

def test_static_reads_only_reader_or_whitelist():
    wl = json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
    allowed = {(e["path"], e["qualname"], e["call"]) for e in wl["entries"]}
    excluded = tuple(wl["excluded_prefixes"])
    offenders = [hit for hit in _scan_reads(wl["scan_roots"])
                 if hit[0] != wl["reader_module"] and hit not in allowed and not hit[0].startswith(excluded)]
    assert offenders == [], offenders[:30]


def test_whitelist_entries_are_live_and_scripts_tmp_excluded():
    wl = json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
    assert wl["excluded_prefixes"] == ["scripts/tmp/"]
    live = set(_scan_reads(wl["scan_roots"]))
    stale = [e for e in wl["entries"] if (e["path"], e["qualname"], e["call"]) not in live]
    assert stale == []
    assert not any(e["path"].startswith("scripts/tmp/") for e in wl["entries"])


# ---------------------------------------------------------------- mutation

def test_mutation_reader_gate_removed_is_caught(tmp_path, monkeypatch):
    """§V mutation ⑧（reader 共同邊界）：世代閘改為 no-op ⇒ 舊版 manifest 被讀出。"""
    manifest = _write_run(tmp_path / "features")
    reader = FeatureReader(str(tmp_path / "features"))
    assert patch_everywhere(monkeypatch, fn.assert_feature_naming_version, lambda *a, **k: None) >= 1
    with tampered(manifest, "old"):
        assert _rejects(_reader_calls(reader)["load_columns_v2"]) is False


def test_mutation_merge_point_gate_removed_is_caught(tmp_path, monkeypatch):
    """§V mutation ⑧（合併點）：單標的閘與合併點閘皆 no-op ⇒ load_multi 接受混世代。"""
    library, m_b, other = _two_symbol_library(tmp_path)
    patch_everywhere(monkeypatch, fn.assert_feature_naming_version, lambda *a, **k: None)
    patch_everywhere(monkeypatch, fn.assert_single_feature_naming_version, lambda *a, **k: None)
    call = lambda: library.load_multi([SYMBOL, other], TF, config_hashes={SYMBOL: CFG, other: CFG})
    assert _mixed_rejected(call, m_b) is False
