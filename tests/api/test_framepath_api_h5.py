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
Task 2.1／2.2 之生成案例用真實 kline（`ffstat_helpers` 輕量設定，單組串行）。Task 2.3 之 API 路由案例所讀 manifest 由
`_cgsa_run` 以正式 `FeatureStorage.write_raw` 寫入合成小表（同 `tests/api/test_feature_export.py`）——屬 API 讀取／schema
單元 fixture，不作 CGSA 生成正確性之證據（生成正確性由 Task 1.1 不變基準與 Task 2.1／2.2 真實 kline 案例承擔；審查 r28
CODEX-R28-P2-02）。
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
    """API 讀取／schema 單元 fixture：以正式 write_raw 寫合成小表之 V2 run（非 CGSA 生成正確性證據）。"""
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


@pytest.mark.asyncio
async def test_boundary_11_uppercase_json_suffix_treated_as_manifest(client, monkeypatch, tmp_path):
    """`.JSON` 大寫副檔名與現行判定一致（視為 CGSA manifest）：登錄成功、task context 走 manifest、features 路由 200
    （審查 r19 CODEX-R19-P1-05：不只驗 task id）。"""
    manifest = _cgsa_run(tmp_path)
    upper = manifest.with_name("feature_manifest.JSON")
    upper.write_bytes(manifest.read_bytes())
    service = _service_with_tasks({})
    task_id = service.register_hdf5_for_browse(SYMBOL, PRIMARY_TF, str(upper))
    assert task_id.startswith(f"browse_{SYMBOL}_{PRIMARY_TF}_")
    context = service._load_task_context(task_id)
    assert context.get("is_cgsa") is True
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", service)
    feats = await client.get(f"/api/v1/features/browse/{task_id}/features?detail_level=names")
    assert feats.status_code == 200 and "feat_a" in feats.text


ROUTES_PATH = REPO / "api" / "routes" / "feature_factory.py"


def route_maps_value_error_to_400(src: str, route: str = "register_hdf5_for_browse",
                                  call_attr: str = "register_hdf5_for_browse") -> bool:
    """route 函式本體之頂層 `try`（不得被其他 try 包住；審查 r28 CODEX-R28-P1-02）其本體含 service 呼叫
    `<x>.<call_attr>(...)`，且其 handlers 中 `except ValueError` 之本體 raise HTTPException(status_code=400)，
    並排在任何 `except Exception` 之前（否則 broad handler 先吞成 500）。巢狀 try 內之 ValueError 分支不算。"""
    import ast

    def has_call(stmts: list) -> bool:
        # 審查 r30 CODEX-R30-P1-02：service 呼叫須位於頂層 try 本體之直接路徑——不下探巢狀 try（其 handler 可先把
        # ValueError 轉成 500）與巢狀函式／lambda
        stack = list(stmts)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == call_attr:
                return True
            stack.extend(ast.iter_child_nodes(n))
        return False

    def raises_400(handler: ast.ExceptHandler) -> bool:
        # 審查 r29 CODEX-R29-P1-02／COMPOSER-R29-P1-02：只看 handler 本體之頂層敘述——其中第一個 raise／return
        # 須為 raise HTTPException(status_code=400)；巢狀 try／if 內之 400 不算（可被同 handler 內 broad catch 轉 500）
        for stmt in handler.body:
            if isinstance(stmt, ast.Raise):
                return isinstance(stmt.exc, ast.Call) and getattr(stmt.exc.func, "id", None) == "HTTPException" \
                    and any(kw.arg == "status_code" and getattr(kw.value, "value", None) == 400
                            for kw in stmt.exc.keywords)
            if isinstance(stmt, (ast.Return, ast.Try, ast.If, ast.With, ast.For, ast.While)):
                return False
        return False

    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == route):
            continue
        for tr in node.body:
            if not (isinstance(tr, ast.Try) and has_call(tr.body)):
                continue
            for handler in tr.handlers:
                name = getattr(handler.type, "id", None)
                if name in {"Exception", "BaseException"} or handler.type is None:
                    break
                if name == "ValueError":
                    return raises_400(handler)
    return False


def test_boundary_12_register_route_maps_value_error_to_400():
    assert route_maps_value_error_to_400(ROUTES_PATH.read_text(encoding="utf-8"))


def test_mutation_register_route_without_value_error_handler_is_detected():
    """刪 route 之 `except ValueError` 分支（SPEC Task 2.3 mutation）⇒ 檢查翻轉；另驗 handler 排在 broad
    `except Exception` 之後亦判失敗（broad 先吞成 500）。"""
    good = (
        "async def register_hdf5_for_browse(request):\n"
        "    try:\n        return feature_factory_service.register_hdf5_for_browse(request)\n"
        "    except FileNotFoundError as exc:\n        raise HTTPException(status_code=404, detail=str(exc))\n"
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n"
        "    except Exception as exc:\n        raise HTTPException(status_code=500, detail=str(exc))\n"
    )
    removed = good.replace(
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n", "")
    reordered = good.replace(
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n"
        "    except Exception as exc:\n        raise HTTPException(status_code=500, detail=str(exc))\n",
        "    except Exception as exc:\n        raise HTTPException(status_code=500, detail=str(exc))\n"
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n")
    assert route_maps_value_error_to_400(good)
    assert not route_maps_value_error_to_400(removed)
    assert not route_maps_value_error_to_400(reordered)
    # 審查 r28 CODEX-R28-P1-02：巢狀 try 之 ValueError→400 被外層 broad→500 包住、ValueError 分支不回 400、
    # service 呼叫不在該 try 內 ⇒ 皆判失敗
    nested = (
        "async def register_hdf5_for_browse(request):\n"
        "    try:\n"
        "        try:\n            return feature_factory_service.register_hdf5_for_browse(request)\n"
        "        except ValueError:\n            raise HTTPException(status_code=400)\n"
        "    except Exception:\n        raise HTTPException(status_code=500)\n"
    )
    not_400 = good.replace("raise HTTPException(status_code=400, detail=str(exc))",
                           "raise HTTPException(status_code=500, detail=str(exc))")
    call_outside = (
        "async def register_hdf5_for_browse(request):\n"
        "    task_id = feature_factory_service.register_hdf5_for_browse(request)\n"
        "    try:\n        return respond(task_id)\n"
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n"
    )
    # 審查 r29：handler 內層 try 之 400 被同 handler 之 broad catch 轉 500、或 400 位於條件分支內 ⇒ 皆判失敗
    handler_nested = (
        "async def register_hdf5_for_browse(request):\n"
        "    try:\n        return feature_factory_service.register_hdf5_for_browse(request)\n"
        "    except ValueError:\n"
        "        try:\n            raise HTTPException(status_code=400)\n"
        "        except Exception:\n            raise HTTPException(status_code=500)\n"
        "    except Exception:\n        raise HTTPException(status_code=500)\n"
    )
    handler_cond = good.replace(
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n",
        "    except ValueError as exc:\n        if flag:\n            raise HTTPException(status_code=400, detail=str(exc))\n"
        "        raise HTTPException(status_code=500, detail=str(exc))\n")
    logged = good.replace(
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n",
        "    except ValueError as exc:\n        logger.warning(str(exc))\n        raise HTTPException(status_code=400, detail=str(exc))\n")
    assert route_maps_value_error_to_400(logged)
    # 審查 r30：service 呼叫位於頂層 try 內之巢狀 try、其 ValueError 先轉 500 ⇒ 外層 400 handler 不算
    inner_500 = (
        "async def register_hdf5_for_browse(request):\n"
        "    try:\n"
        "        try:\n            return feature_factory_service.register_hdf5_for_browse(request)\n"
        "        except ValueError:\n            raise HTTPException(status_code=500)\n"
        "    except ValueError:\n        raise HTTPException(status_code=400)\n"
        "    except Exception:\n        raise HTTPException(status_code=500)\n"
    )
    for bad in (nested, not_400, call_outside, handler_nested, handler_cond, inner_500):
        assert not route_maps_value_error_to_400(bad)
