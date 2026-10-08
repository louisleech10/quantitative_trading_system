"""FRAMEPATH Phase 2（Task 2.1–2.3）：舊特徵 `*_factory.h5` 讀寫鏈刪除後之具名驗收（docs/FRAMEPATH_SPEC.md）。

本檔承載 Phase 2 全部新斷言（SPEC Task 2.3 列本檔為新測；Task 2.1／2.2 未列新檔，其新斷言同置於此以免改動
處置表凍結之既有測試檔）：
- Task 2.1：生成忽略手放之 `*_factory.h5`、`force_regenerate` 兩值 fingerprint 相等；寫讀端與生成快取之符號
  於 momentum／api 零出現。
- Task 2.2：只有 `*_factory.h5` 之 base_path ⇒ `FeatureLibrary.load` 拋 `FeatureNotFoundError`（訊息不提 HDF5）、
  coverage 該 symbol 無資料；V2 run 與 h5 並存 ⇒ 只讀 V2；`config_hash` 明給但缺 artifacts ⇒ 既有訊息不變。
- Task 2.3：register／task context／schema（features 列表）／selected rows／CSV 對 `.h5` 皆 HTTP 400，body 含
  「舊 factory h5 已不支援」與路徑；CGSA manifest 路徑之 feature list、selected rows、CSV 匯出 200；
  `hdf5_path` 空字串之既有行為與 `.JSON` 大寫副檔名之判定不變。
生成案例用真實 kline（`ffstat_helpers` 輕量設定，單組串行）；API 讀取路徑沿用 `tests/api/test_feature_export.py`
之 `FeatureStorage.write_raw` V2 run 建法。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import h5py
import httpx
import numpy as np
import pandas as pd
import pytest
import pytest_asyncio
from fastapi import FastAPI

import api.routes.feature_factory as feature_factory_routes
from api.routes.feature_factory import router as feature_factory_router
from api.services.feature_factory_service import FeatureFactoryService
from momentum.core.contracts import FeatureNotFoundError
from momentum.factories import create_coverage_analyzer
from momentum.FeatureEngineering.feature_library import FeatureLibrary
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering.ffstat_helpers import (
    PRIMARY_TF,
    SYMBOL,
    base_fingerprints,
    prepare_stat_env,
    run_stat,
    stat_payload,
)

REPO = Path(__file__).resolve().parents[2]
H5_REJECT = "舊 factory h5 已不支援"
REMOVED_SYMBOLS = ("load_factory_output", "save_factory_output", "save_metadata_json", "_try_load_cache",
                   "_last_generation_from_cache")


def _write_factory_h5(path: Path) -> Path:
    """舊 frame 產物之形狀（`data/features` ＋ `data/feature_names`）；內容僅供「被忽略／被拒」之對象。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=np.array([[1.0, 2.0], [3.0, 4.0]]))
        group.create_dataset("feature_names", data=np.array(["framepath_a", "framepath_b"], dtype=object),
                             dtype=h5py.string_dtype(encoding="utf-8"))
    return path


def _library(root: Path, registry_path: Path) -> FeatureLibrary:
    return FeatureLibrary(FeatureRegistry(registry_path), FeatureStorage(str(root)), feature_reader=FeatureReader(str(root)))


def _py_sources(roots):
    for root in roots:
        for p in sorted((REPO / root).rglob("*.py")):
            if "__pycache__" not in p.parts:
                yield str(p.relative_to(REPO)), p.read_text(encoding="utf-8")


# ---------------------------------------------------------------- Task 2.1

def test_boundary_01_generation_ignores_hand_placed_factory_h5_and_force_flag(monkeypatch, tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    prepare_stat_env(monkeypatch, a)
    _write_factory_h5(a / "features" / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    root_a, _f, result_a = run_stat(a, stat_payload(), force_regenerate=False)
    prepare_stat_env(monkeypatch, b)
    root_b, _f, result_b = run_stat(b, stat_payload(), force_regenerate=True)
    assert str(result_a.metadata.get("manifest_path", "")).endswith(".json")
    assert "framepath_a" not in set(result_a.features_df.columns)
    fa, fb = base_fingerprints(root_a), base_fingerprints(root_b)
    assert fa and fa == fb


def test_boundary_02_factory_h5_chain_symbols_absent():
    hits = [(p, s) for p, src in _py_sources(("momentum", "api")) for s in REMOVED_SYMBOLS if s in src]
    assert hits == []


# ---------------------------------------------------------------- Task 2.2

def _library_rejects_h5_only(tmp_path: Path) -> bool:
    root = tmp_path / "h5only"
    _write_factory_h5(root / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    lib = _library(root, tmp_path / "h5only_registry.json")
    try:
        lib.load(SYMBOL, PRIMARY_TF)
    except FeatureNotFoundError as exc:
        return "hdf5" not in str(exc).lower() and "h5" not in str(exc).lower()
    return False


def test_boundary_03_library_h5_only_raises_feature_not_found(tmp_path):
    assert _library_rejects_h5_only(tmp_path)


def test_boundary_04_coverage_h5_only_has_no_data(tmp_path):
    root = tmp_path / "cov"
    _write_factory_h5(root / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    analyzer = create_coverage_analyzer()
    assert analyzer._load_symbol_features(SYMBOL, PRIMARY_TF, str(root)) is None


def _v2_raw_columns(root: Path, config_hash: str) -> set:
    manifest = FeatureReader(str(root)).load_manifest_v2(SYMBOL, PRIMARY_TF, config_hash, allow_partial=True)
    return {c for group in manifest["artifacts"]["raw"]["groups"].values() for c in group.get("columns", [])}


def test_boundary_05_library_and_coverage_read_v2_when_h5_coexists(monkeypatch, tmp_path):
    prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = run_stat(tmp_path, stat_payload())
    _write_factory_h5(root / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    expected = _v2_raw_columns(root, str(result.metadata["config_hash"]))
    lib = _library(root, root / "registry.json")
    loaded = lib.load(SYMBOL, PRIMARY_TF)
    assert "framepath_a" not in loaded.columns
    assert set(loaded.columns) == expected and len(expected) > 0
    cov = create_coverage_analyzer()._load_symbol_features(SYMBOL, PRIMARY_TF, str(root))
    assert cov is not None and "framepath_a" not in cov.columns


def test_boundary_06_explicit_config_hash_missing_artifacts_message_unchanged(monkeypatch, tmp_path):
    """`config_hash` 明給、registry 有列但 V2 artifacts 已不在 ⇒ 既有「artifacts missing for config_hash」訊息不變
    （不落到任何 h5 後備）。"""
    import shutil

    prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = run_stat(tmp_path, stat_payload())
    config_hash = str(result.metadata["config_hash"])
    _write_factory_h5(root / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    for raw_dir in root.rglob("raw"):
        if raw_dir.is_dir() and config_hash in str(raw_dir):
            shutil.rmtree(raw_dir)
    lib = _library(root, root / "registry.json")
    with pytest.raises(FeatureNotFoundError) as exc:
        lib.load(SYMBOL, PRIMARY_TF, config_hash=config_hash)
    assert f"artifacts missing for config_hash: {config_hash}" in str(exc.value)


def test_mutation_library_h5_fallback_restored_is_detected(monkeypatch, tmp_path):
    """還原 h5 後備（只有 h5 時讀出資料）⇒ `_library_rejects_h5_only` 為 False（驗收轉紅）。"""
    frame = pd.DataFrame({"framepath_a": [1.0, 3.0], "framepath_b": [2.0, 4.0]})
    monkeypatch.setattr(FeatureLibrary, "load", lambda self, symbol, timeframe, **kw: frame)
    assert not _library_rejects_h5_only(tmp_path)


# ---------------------------------------------------------------- Task 2.3

def _service_with_tasks(tasks: Dict[str, Dict[str, Any]]) -> FeatureFactoryService:
    """正式建構子（browse 路由依賴之各快取屬性齊備），只替換任務表。"""
    service = FeatureFactoryService()
    with service._lock:
        service._tasks = tasks
    return service


def _task(hdf5_path: str, config_hash: str = "cfg_framepath") -> Dict[str, Any]:
    return {"status": "completed", "result": {
        "hdf5_path": hdf5_path,
        "metadata": {"symbol": SYMBOL, "timeframe": PRIMARY_TF, "config_hash": config_hash},
        "generation_time": 1.0, "layer_counts": {}}}


def _cgsa_run(tmp_path: Path) -> Path:
    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2026-04-01", periods=4, freq="h")
    groups = {"g": pd.DataFrame({"feat_a": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
                                 "feat_b": np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)}, index=row_index)}
    raw_dir = storage.write_raw(SYMBOL, PRIMARY_TF, "cfg_framepath", groups, row_index=row_index)
    return raw_dir.parent / "feature_manifest.json"


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(feature_factory_router)
    return test_app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _is_h5_rejection(resp: httpx.Response, path: Path) -> bool:
    return resp.status_code == 400 and H5_REJECT in resp.text and str(path) in resp.text


@pytest.mark.asyncio
async def test_boundary_07_register_h5_is_400(client, monkeypatch, tmp_path):
    h5 = _write_factory_h5(tmp_path / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", _service_with_tasks({}))
    resp = await client.post("/api/v1/features/browse/register",
                             json={"symbol": SYMBOL, "timeframe": PRIMARY_TF, "hdf5_path": str(h5)})
    assert _is_h5_rejection(resp, h5)


@pytest.mark.asyncio
@pytest.mark.parametrize("route", [
    "/api/v1/features/browse/{tid}/features",
    "/api/v1/features/browse/{tid}/data?features=framepath_a",
    "/api/v1/features/export/{tid}/csv",
])
async def test_boundary_08_task_context_h5_routes_are_400(client, monkeypatch, tmp_path, route):
    h5 = _write_factory_h5(tmp_path / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    service = _service_with_tasks({"task-h5": _task(str(h5))})
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", service)
    resp = await client.get(route.format(tid="task-h5"))
    assert _is_h5_rejection(resp, h5)


@pytest.mark.asyncio
async def test_boundary_09_cgsa_manifest_routes_are_200(client, monkeypatch, tmp_path):
    manifest = _cgsa_run(tmp_path)
    service = _service_with_tasks({"task-v2": _task(str(manifest))})
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", service)
    feats = await client.get("/api/v1/features/browse/task-v2/features?detail_level=names")
    assert feats.status_code == 200 and "feat_a" in feats.text
    rows = await client.get("/api/v1/features/browse/task-v2/data?features=feat_a")
    assert rows.status_code == 200 and "feat_a" in rows.text
    csv = await client.get("/api/v1/features/export/task-v2/csv?columns=feat_a&include_metadata_header=false")
    assert csv.status_code == 200 and csv.text.splitlines()[0] == "timestamp,feat_a"


def test_boundary_10_empty_hdf5_path_behavior_unchanged():
    service = _service_with_tasks({"task-empty": _task("")})
    with pytest.raises(FileNotFoundError) as exc:
        service._load_task_context("task-empty")
    assert "HDF5 path not found for task: task-empty" in str(exc.value)


def test_boundary_11_uppercase_json_suffix_treated_as_manifest(tmp_path):
    manifest = _cgsa_run(tmp_path)
    upper = manifest.with_name("feature_manifest.JSON")
    upper.write_bytes(manifest.read_bytes())
    service = _service_with_tasks({})
    task_id = service.register_hdf5_for_browse(SYMBOL, PRIMARY_TF, str(upper))
    assert task_id.startswith(f"browse_{SYMBOL}_{PRIMARY_TF}_")


@pytest.mark.asyncio
async def test_mutation_register_unhandled_error_is_not_400(client, monkeypatch, tmp_path):
    """route 未把 service 之 ValueError 轉 400（如刪 `except ValueError`）時會落到 500 ⇒ `_is_h5_rejection` 為 False。"""
    h5 = _write_factory_h5(tmp_path / f"{SYMBOL}_{PRIMARY_TF}_factory.h5")
    service = _service_with_tasks({})

    def _boom(symbol, timeframe, hdf5_path):
        raise RuntimeError(f"{H5_REJECT}: {hdf5_path}")

    monkeypatch.setattr(service, "register_hdf5_for_browse", _boom)
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", service)
    resp = await client.post("/api/v1/features/browse/register",
                             json={"symbol": SYMBOL, "timeframe": PRIMARY_TF, "hdf5_path": str(h5)})
    assert resp.status_code == 500
    assert not _is_h5_rejection(resp, h5)
