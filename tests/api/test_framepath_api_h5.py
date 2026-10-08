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
                                  call_attr: str = "register_hdf5_for_browse",
                                  receiver: str = "feature_factory_service") -> bool:
    """route 函式本體之頂層 `try`（不得被其他 try 包住；審查 r28 CODEX-R28-P1-02）其本體含 service 呼叫
    `<x>.<call_attr>(...)`，且其 handlers 中 `except ValueError` 之本體 raise HTTPException(status_code=400)，
    並排在任何 `except Exception` 之前（否則 broad handler 先吞成 500）。巢狀 try 內之 ValueError 分支不算。"""
    import ast

    def has_call(stmts: list) -> bool:
        # 審查 r30／r31：service 呼叫須為頂層 try 本體之「直接敘述」（Assign／AnnAssign／Return／Expr，不下探任何
        # 複合敘述如巢狀 try／if／with／for 及函式／lambda），且呼叫目標恰為 `<receiver>.<call_attr>`（receiver 為
        # 名稱 feature_factory_service；CODEX-R31-P1-03：他物件同名方法不算）
        def direct_calls(expr: ast.AST):
            stack = [expr]
            while stack:
                n = stack.pop()
                if isinstance(n, ast.Lambda):
                    continue
                if isinstance(n, ast.Call):
                    yield n
                stack.extend(ast.iter_child_nodes(n))

        for s in stmts:
            if not isinstance(s, (ast.Assign, ast.AnnAssign, ast.Return, ast.Expr)) or s.value is None:
                continue
            for c in direct_calls(s.value):
                if isinstance(c.func, ast.Attribute) and c.func.attr == call_attr \
                        and isinstance(c.func.value, ast.Name) and c.func.value.id == receiver:
                    return True
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
    # 審查 r31 CODEX-R31-P1-03：try 內為他物件之同名方法、或 service 呼叫藏於 if／with 複合敘述內 ⇒ 不算
    service_call = "feature_factory_service.register_hdf5_for_browse(request)"
    wrong_receiver = (
        "async def register_hdf5_for_browse(request):\n"
        "    task_id = feature_factory_service.register_hdf5_for_browse(request)\n"
        "    try:\n        return other.register_hdf5_for_browse(request)\n"
        "    except ValueError as exc:\n        raise HTTPException(status_code=400, detail=str(exc))\n"
    )
    in_if_false = good.replace(f"        return {service_call}\n",
                               f"        if False:\n            return {service_call}\n        return None\n")
    in_with = good.replace(f"        return {service_call}\n",
                           f"        with ctx():\n            return {service_call}\n")
    assert route_maps_value_error_to_400(good.replace(f"return {service_call}", f"task_id = {service_call}"))
    for bad in (nested, not_400, call_outside, handler_nested, handler_cond, inner_500, wrong_receiver, in_if_false,
                in_with):
        assert not route_maps_value_error_to_400(bad)


# ---------------------------------------------------------------- Task 2.5–2.7（SPEC v17：V1 版面與已無用舊格式）

V1_REMOVED_SYMBOLS = (
    "persist_registry_to_parquet", "AsyncParquetCompactor", "_write_v7_manifest", "_write_columns_json_gz",
    "FFACT_L7_WORKERS", "FFACT_L7_COMPACTOR", "_adapt_legacy_manifest_v2", "_list_features_from_parquet",
    "legacy_v7", "FFACT_HDF5_CHUNK", "FFACT_HDF5_GZIP", "_build_2d_chunks", "_build_1d_chunks",
    "feature_file_exists", "list_feature_files", "export_for_ml", "FFACT_DSTAR_CACHE_MIGRATE_LEGACY",
    "migrate_d_star_cache", "l7_workers", "hdf5_cache_compression",
    # 審查 r34 CODEX-R34-P1-01：V1 寫入專用 helper、save_factory_output 殘留 helper、只由 V1 寫入讀取之 chunk_bars
    "_persist_parts_parallel", "_precheck_l7_disk_space", "_classify_persist_failure", "_resolve_bounded_env",
    "chunk_bars",
)
# 只由已刪 save_factory_output 讀取之 FeatureStorage 實例屬性（以 `self.` 前綴精確比對，避免誤中 tf_aligner 之 n_chunk_cols）
V1_REMOVED_ATTR_RE = r"self\.(_chunk_rows|_chunk_cols|_gzip_level)\b"
V1_READER_CALLS = ("load_manifest", "list_features", "load_columns", "stream_groups", "load_cross_symbol")


V1_READER_CLASSES = (("momentum/FeatureEngineering/feature_reader.py", "FeatureReader"),
                     ("momentum/core/protocols.py", "IFeatureReader"))


def v1_symbol_hits(sources) -> list:
    """Task 2.5–2.7 刪除之符號殘留（字面）。V1 讀取方法另由 `v1_reader_methods` 以 AST 判（同名之他類 API——如 IC
    cube store 之 `load_manifest`、IC 服務三元組 `list_features`——不在刪除範圍，不以字面判）。"""
    import re

    hits = []
    for path, src in sources:
        hits += [(path, s) for s in V1_REMOVED_SYMBOLS if s in src]
        hits += [(path, m.group(0)) for m in re.finditer(V1_REMOVED_ATTR_RE, src)]
    return hits


def v1_reader_methods(class_sources) -> list:
    """`FeatureReader`／`IFeatureReader` 類別本體內定義之 V1 讀取方法（`*_v2` 不計）。"""
    import ast

    hits = []
    for (path, cls), src in class_sources:
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ClassDef) and node.name == cls:
                hits += [(path, n.name) for n in node.body
                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in V1_READER_CALLS]
    return hits


def test_boundary_13_v1_and_dead_format_symbols_absent():
    """SPEC v17 Task 2.5／2.7 驗證之符號清零（momentum／api／scripts）；`frontend/src` 另驗 `l7_workers`。"""
    assert v1_symbol_hits(_py_sources(("momentum", "api", "scripts"))) == []
    assert v1_reader_methods([(pc, (REPO / pc[0]).read_text(encoding="utf-8")) for pc in V1_READER_CLASSES]) == []
    tsx = [p for p in (REPO / "frontend" / "src").rglob("*.ts*")
           if any(s in p.read_text(encoding="utf-8") for s in ("l7_workers", "chunk_bars", "Compactor=ON"))]
    assert tsx == []


def test_mutation_v1_symbol_scan_detects_residue():
    """符號清零檢查可證偽：殘留已刪符號 ⇒ 命中；FeatureReader／IFeatureReader 留 V1 讀取方法 ⇒ 命中；`*_v2` 方法、
    他類同名 API（IC cube store `load_manifest`）不命中。"""
    assert v1_symbol_hits([("m.py", "x = 'persist_registry_to_parquet'\n")]) != []
    assert v1_symbol_hits([("m.py", "store.load_manifest(root, tid)\n")]) == []
    # 審查 r34：主入口已刪而專用 helper／屬性殘留 ⇒ 各自命中；V2 同族名與他模組之 n_chunk_cols 不命中
    for residue in ("def _persist_parts_parallel(self):\n", "def _precheck_l7_disk_space(self):\n",
                    "def _classify_persist_failure(e):\n", "def _resolve_bounded_env(n):\n",
                    "cfg = {'chunk_bars': 1}\n", "self._chunk_rows = 1\n", "self._chunk_cols = 1\n",
                    "x = self._gzip_level\n"):
        assert v1_symbol_hits([("m.py", residue)]) != [], residue
    assert v1_symbol_hits([("m.py", "def _precheck_l7_raw_stream_disk_space(self):\n    n_chunk_cols = 2\n")]) == []
    key = ("momentum/FeatureEngineering/feature_reader.py", "FeatureReader")
    residue = "class FeatureReader:\n    def stream_groups(self, s, h):\n        pass\n"
    clean = "class FeatureReader:\n    def stream_groups_v2(self, s, t, h):\n        pass\n"
    other = "class CubeStore:\n    def load_manifest(self, r, t):\n        pass\n"
    assert v1_reader_methods([(key, residue)]) == [(key[0], "stream_groups")]
    assert v1_reader_methods([(key, clean)]) == [] and v1_reader_methods([(key, other)]) == []


V1_FIXTURE = REPO / "tests" / "_golden" / "framepath" / "v1_layout"
V1_SYMBOL, V1_HASH, V1_TF = "FPV1USDT", "cfgv1fixture", "1h"


def _v1_only_root(tmp_path: Path) -> Path:
    """只有 V1 版面之 base_path：複製錨點碼態 V1 寫入器產出之真 fixture（handoffs/run_receipts/framepath_probes/
    make_v1_fixture.py）；錨點碼態下 V2 讀者會退回讀出它、coverage V7 枝會讀出它 ⇒ 下列驗收於錨點紅、實作後綠。"""
    import shutil

    root = tmp_path / "v1only"
    shutil.copytree(V1_FIXTURE, root)
    return root


def test_boundary_14_v2_reader_does_not_fall_back_to_v1(tmp_path):
    """Task 2.5：V2 manifest 缺而同目錄有 V1 版面 ⇒ `load_manifest_v2` 拋 `FileNotFoundError`（訊息含 V2
    `feature_manifest.json` 路徑），FeatureLibrary 同情境拋 `FeatureNotFoundError`；不讀 V1。"""
    root = _v1_only_root(tmp_path)
    with pytest.raises(FileNotFoundError) as exc:
        FeatureReader(str(root)).load_manifest_v2(V1_SYMBOL, V1_TF, V1_HASH)
    assert "feature_manifest.json" in str(exc.value)
    lib = _library(root, tmp_path / "v1only_registry.json")
    with pytest.raises(FeatureNotFoundError):
        lib.load(V1_SYMBOL, V1_TF, config_hash=V1_HASH)


def test_boundary_15_coverage_ignores_v1_layout(tmp_path):
    """Task 2.6：只有 V1 目錄之 symbol ⇒ coverage 回無資料（V7 掃描枝已刪）。"""
    root = _v1_only_root(tmp_path)
    assert create_coverage_analyzer()._load_symbol_features(V1_SYMBOL, V1_TF, str(root)) is None


@pytest.fixture
def ic_app() -> FastAPI:
    from api.routes.ic_analysis import router as ic_router

    test_app = FastAPI()
    test_app.include_router(ic_router)
    return test_app


async def _ic_list_old_address_rejected(app: FastAPI, features_path: str) -> bool:
    """IC `/features/list` 帶舊位址 ⇒ HTTP 400、訊息含該位址並指向 symbol／timeframe／config_hash。"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/ic/features/list", params={"features_path": features_path})
    return resp.status_code == 400 and features_path in resp.text and all(
        token in resp.text for token in ("symbol", "timeframe", "config_hash"))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["parquet_key", "real_legacy_h5"])
async def test_boundary_16_ic_feature_list_old_address_is_400(ic_app, tmp_path, kind):
    """Task 2.6：IC `/features/list` 帶 `features_path`——舊 `parquet:` 位址，或**實際存在**之 `data/` group 舊 h5
    （錨點碼態會讀出 `framepath_a`／`framepath_b` 回 200）——一律 HTTP 400；審查 r33 CODEX-R33-P1-01。"""
    if kind == "parquet_key":
        features_path = "parquet:BTCUSDT:abc123"
    else:
        features_path = str(_write_factory_h5(tmp_path / "legacy_features.h5"))
    assert await _ic_list_old_address_rejected(ic_app, features_path)


@pytest.mark.asyncio
async def test_mutation_ic_list_old_h5_branch_restored_is_detected(ic_app, monkeypatch, tmp_path):
    """還原舊 h5 讀取枝（實檔回清單、200）⇒ 驗收判定翻轉為 False；以 route 實際呼叫之服務實例置換其方法。"""
    import api.routes.ic_analysis as ic_routes

    h5 = _write_factory_h5(tmp_path / "legacy_features.h5")
    monkeypatch.setattr(ic_routes.ic_analysis_service, "list_features",
                        lambda features_path=None, meta_path=None, **kw: [{"name": "framepath_a"}])
    assert not await _ic_list_old_address_rejected(ic_app, str(h5))


# ---------------------------------------------------------------- Task 2.6 舊 cgsa_work 瀏覽格式（審查 r33 CODEX-R33-P1-02）

CGSA_WORK_REJECT = "舊 cgsa_work 瀏覽格式已不支援"
BROWSE_ROUTES = (  # 審查 r34 CODEX-R34-P1-02：全部 browse／export 讀者（含 summary 與其 fast path）
    "/api/v1/features/browse/{tid}/features",
    "/api/v1/features/browse/{tid}/data?features=legacy_a",
    "/api/v1/features/browse/{tid}/correlation?features=legacy_a,legacy_b",
    "/api/v1/features/browse/{tid}/vif?features=legacy_a,legacy_b",
    "/api/v1/features/browse/{tid}/distribution?feature=legacy_a",
    "/api/v1/features/browse/{tid}/nan-pattern",
    "/api/v1/features/browse/{tid}/data-quality",
    "/api/v1/features/browse/{tid}/summary",
    "/api/v1/features/export/{tid}/csv",
    "/api/v1/features/export/{tid}/json",
    "/api/v1/features/export/{tid}/markdown",
)


def _cgsa_work_list_manifest(tmp_path: Path) -> Path:
    """舊 CGSA registry 列表格式（`groups` 為串列、各組以絕對 `parquet_path` 指檔；無 version）；產生者
    `_layer7_validate_and_persist_cgsa` 已由 v16 A1 刪除。錨點碼態會經 `parquet_path` 讀出 `legacy_a`。"""
    import json

    import pyarrow as pa
    import pyarrow.parquet as pq

    work = tmp_path / "cgsa_work" / f"{SYMBOL}_{PRIMARY_TF}_deadbeef"
    work.mkdir(parents=True)
    parquet = work / "g.parquet"
    pq.write_table(pa.table({"legacy_a": [1.0, 2.0, 3.0, 4.0], "legacy_b": [2.0, 1.0, 4.0, 3.0]}), str(parquet))
    manifest = work / "manifest.json"
    manifest.write_text(json.dumps({"symbol": SYMBOL, "timeframe": PRIMARY_TF, "groups": [
        {"group_id": "g", "parquet_path": str(parquet), "columns": ["legacy_a", "legacy_b"]}]}), encoding="utf-8")
    return manifest


async def _route_results(client, tid: str, routes) -> dict:
    """逐路由累積 (status, text)（審查 r35：不在第一個不符處提早返回，逐路由皆可判）。"""
    out = {}
    for route in routes:
        resp = await client.get(route.format(tid=tid))
        out[route] = (resp.status_code, resp.text)
    return out


async def _cgsa_work_routes_rejected(client, tid: str) -> bool:
    results = await _route_results(client, tid, BROWSE_ROUTES)
    return all(code == 400 and CGSA_WORK_REJECT in text for code, text in results.values())


V2_BROWSE_ROUTES = (  # 審查 r35 CODEX-R35-P1-04：同 11 個讀者對有效 V2 run 皆 200（錨點與試作實測皆 200）
    "/api/v1/features/browse/{tid}/features",
    "/api/v1/features/browse/{tid}/data?features=feat_a",
    "/api/v1/features/browse/{tid}/correlation?features=feat_a,feat_b",
    "/api/v1/features/browse/{tid}/vif?features=feat_a,feat_b",
    "/api/v1/features/browse/{tid}/distribution?feature=feat_a",
    "/api/v1/features/browse/{tid}/nan-pattern",
    "/api/v1/features/browse/{tid}/data-quality",
    "/api/v1/features/browse/{tid}/summary",
    "/api/v1/features/export/{tid}/csv",
    "/api/v1/features/export/{tid}/json",
    "/api/v1/features/export/{tid}/markdown",
)


def v2_routes_all_served(results: dict) -> list:
    """不合格之路由（非 200、或回應含舊格式／舊 h5 拒絕字樣）；空＝全部照常服務。"""
    return [route for route, (code, text) in results.items()
            if code != 200 or CGSA_WORK_REJECT in text or H5_REJECT in text]


@pytest.mark.asyncio
async def test_boundary_19_v2_manifest_served_by_all_browse_routes(client, monkeypatch, tmp_path):
    """Task 2.6 底線：有效 V2 run 之 task 於全部 11 個 browse／export 讀者照常 200（舊格式拒絕不得誤傷 V2）。"""
    service = _service_with_tasks({"task-v2": _task(str(_cgsa_run(tmp_path)))})
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", service)
    assert v2_routes_all_served(await _route_results(client, "task-v2", V2_BROWSE_ROUTES)) == []


def test_mutation_v2_route_single_wrong_rejection_is_detected():
    """單一路由（如 summary）對 V2 誤拒 ⇒ 判定逐路由命中該路由。"""
    ok = {route: (200, "{}") for route in V2_BROWSE_ROUTES}
    summary = "/api/v1/features/browse/{tid}/summary"
    bad = {**ok, summary: (400, CGSA_WORK_REJECT)}
    assert v2_routes_all_served(ok) == [] and v2_routes_all_served(bad) == [summary]


@pytest.mark.asyncio
async def test_boundary_17_cgsa_work_list_format_routes_are_400(client, monkeypatch, tmp_path):
    """Task 2.6：task 指向舊 cgsa_work 列表格式 manifest ⇒ 全部 browse／export 讀者（features、data、correlation、vif、
    distribution、nan-pattern、data-quality、summary、csv／json／markdown 匯出）皆 400 且含訊息。"""
    service = _service_with_tasks({"task-cgsa-work": _task(str(_cgsa_work_list_manifest(tmp_path)))})
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", service)
    assert await _cgsa_work_routes_rejected(client, "task-cgsa-work")


@pytest.mark.asyncio
async def test_mutation_cgsa_work_list_format_branch_restored_is_detected(client, monkeypatch, tmp_path):
    """還原列表格式讀取（舊 manifest 之 task 照讀出資料、不拒絕；以導向一個可讀 V2 run 模擬錨點碼態讀出資料）
    ⇒ 驗收判定翻轉為 False。"""
    service = _service_with_tasks({"task-cgsa-work": _task(str(_cgsa_work_list_manifest(tmp_path))),
                                   "task-v2": _task(str(_cgsa_run(tmp_path)))})
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", service)
    original = service._load_task_context
    monkeypatch.setattr(service, "_load_task_context",
                        lambda task_id: original("task-v2" if task_id == "task-cgsa-work" else task_id))
    assert not await _cgsa_work_routes_rejected(client, "task-cgsa-work")


# ---------------------------------------------------------------- Task 2.7 定義級殘留（審查 r33 CODEX-R33-P2-03）

DEAD_CLASS_MEMBERS = (
    ("momentum/FeatureEngineering/feature_storage.py", "FeatureStorage",
     ("delete_features", "feature_file_exists", "list_feature_files")),
    ("api/core/config.py", "Settings", ("enable_hdf5_cache", "hdf5_cache_dir", "hdf5_cache_compression")),
    # 審查 r35 CODEX-R35-P1-01：瀏覽服務之舊讀取方法（Task 2.3／2.6）
    ("api/services/feature_browser_service.py", "FeatureBrowserService",
     ("_load_features_df", "_load_via_reader", "_load_hdf5_features", "_find_dataset_group")),
)
# 審查 r35 CODEX-R35-P1-01／P2-03：舊格式之字串契約殘留（以 AST 字串常數判，註解不計）
DEAD_STRING_CONTRACTS = (
    ("api/services/feature_browser_service.py", ("library:", "parquet:")),
    ("momentum/Analysis/ic_engine.py", ("legacy_format",)),
    ("api/services/ic_analysis_service.py", ("parquet:",)),
)


def dead_string_constants(file_sources) -> list:
    """檔內字串常數以禁用前綴起首（`library:`、`parquet:`）或等於禁用鍵（`legacy_format`）者。"""
    import ast

    hits = []
    for (path, tokens), src in file_sources:
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                hits += [(path, t) for t in tokens if node.value == t or (t.endswith(":") and node.value.startswith(t))]
    return hits


def legacy_quality_statuses(src: str) -> list:
    """`QUALITY_STATUS_PRECEDENCE` 字面中之 V1 專屬狀態 `legacy`。"""
    import ast

    for node in ast.walk(ast.parse(src)):
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == "QUALITY_STATUS_PRECEDENCE" and node.value is not None:
            return [e.value for e in ast.walk(node.value) if isinstance(e, ast.Constant) and e.value == "legacy"]
    return []


def test_boundary_20_old_format_string_contracts_and_legacy_status_absent():
    """Task 2.5 ④／2.6：瀏覽服務無 `library:`／`parquet:` 位址字串、ic_engine 無 `legacy_format`、IC 服務無 `parquet:`
    位址字串；`QUALITY_STATUS_PRECEDENCE` 不含 V1 專屬 `legacy`。"""
    srcs = [(spec, (REPO / spec[0]).read_text(encoding="utf-8")) for spec in DEAD_STRING_CONTRACTS]
    assert dead_string_constants(srcs) == []
    storage = (REPO / "momentum/FeatureEngineering/feature_storage.py").read_text(encoding="utf-8")
    assert legacy_quality_statuses(storage) == []


def test_mutation_old_format_contract_scans_detect_residue():
    spec = ("m.py", ("library:", "legacy_format"))
    assert dead_string_constants([(spec, "if p.startswith('library:'):\n    pass\n")]) == [("m.py", "library:")]
    assert dead_string_constants([(spec, "if manifest.get('legacy_format'):\n    pass\n")]) == [("m.py", "legacy_format")]
    assert dead_string_constants([(spec, "# library: 舊位址已刪\nx = 'libraryX'\n")]) == []
    assert legacy_quality_statuses("QUALITY_STATUS_PRECEDENCE: Tuple[str, ...] = ('legacy', 'partial')\n") == ["legacy"]
    assert legacy_quality_statuses("QUALITY_STATUS_PRECEDENCE = ('failed', 'partial', 'complete')\n") == []


def dead_class_members(class_sources) -> list:
    """類別本體內仍定義之已刪成員（方法或類別層欄位指派）。"""
    import ast

    hits = []
    for (path, cls, names), src in class_sources:
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ClassDef) and node.name == cls:
                for n in node.body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names:
                        hits.append((path, cls, n.name))
                    targets = [n.target] if isinstance(n, ast.AnnAssign) else n.targets if isinstance(n, ast.Assign) else []
                    hits += [(path, cls, t.id) for t in targets if isinstance(t, ast.Name) and t.id in names]
    return hits


def test_boundary_18_dead_class_members_absent_dataloader_param_kept():
    """Task 2.7：`FeatureStorage.delete_features`／`feature_file_exists`／`list_feature_files` 與 api `Settings` 三個 HDF5
    設定欄不存在；`DataLoader(enable_hdf5_cache=…)` 建構參數保留（快取本身現役）。"""
    import inspect

    from momentum.DataExtraction.data_loader_momentum import DataLoader

    srcs = [(spec, (REPO / spec[0]).read_text(encoding="utf-8")) for spec in DEAD_CLASS_MEMBERS]
    assert dead_class_members(srcs) == []
    assert "enable_hdf5_cache" in inspect.signature(DataLoader.__init__).parameters


def test_mutation_dead_class_member_scan_detects_residue():
    spec = ("api/core/config.py", "Settings", ("enable_hdf5_cache",))
    residue = "class Settings:\n    enable_hdf5_cache: bool = True\n"
    method = ("x.py", "FeatureStorage", ("delete_features",))
    assert dead_class_members([(spec, residue)]) == [("api/core/config.py", "Settings", "enable_hdf5_cache")]
    assert dead_class_members([(method, "class FeatureStorage:\n    def delete_features(self):\n        pass\n")]) != []
    assert dead_class_members([(spec, "class Other:\n    enable_hdf5_cache = 1\n")]) == []


# ---------------------------------------------------------------- Task 2.3／2.5／2.6 舊分支結構性殘留（審查 r36）
# 只驗收行為（400／無資料）不足：正常實作可在舊分支前加早退而留下後方死碼（CODEX-R36-P1-01）。以下以 AST 判
# 指名之舊讀取結構確實不存在；V2 合法讀取（如 `fast.get("total_rows")`、kline_cache.h5 之 h5py 讀取）不誤中。

def _func_nodes(tree, name: str):
    import ast

    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]


def _bound_names(tree, module: str) -> set:
    """模組 `module` 於本檔綁定之全部名稱（審查 r37 CODEX-R37-P1-01：含別名）：`import m`→m、`import m as x`→x、
    `import m.sub`→m、`from m import a`／`from m import a as b`／`from m.sub import a`→a／b。"""
    import ast

    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == module or a.name.startswith(module + "."):
                    out.add(a.asname or a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.module and (n.module == module or n.module.startswith(module + ".")):
            out |= {a.asname or a.name for a in n.names}
    return out


def _module_uses(node, tree, module: str) -> list:
    """node 範圍內對 `module` 之匯入與名稱使用（行號；名稱集合取自整檔之綁定）。"""
    import ast

    bound = _bound_names(tree, module)
    imports = [n.lineno for n in ast.walk(node) if isinstance(n, ast.Import)
               for a in n.names if a.name == module or a.name.startswith(module + ".")]
    imports += [n.lineno for n in ast.walk(node) if isinstance(n, ast.ImportFrom) and n.module
                and (n.module == module or n.module.startswith(module + "."))]
    uses = [n.lineno for n in ast.walk(node) if isinstance(n, ast.Name) and n.id in bound]
    return imports + uses


def _str_consts(node) -> list:
    import ast

    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def structural_residues(sources: dict) -> list:
    """sources＝{repo 相對路徑: 原始碼}；回傳殘留描述（空＝合格）。"""
    import ast

    hits = []
    cov = ast.parse(sources["momentum/Analysis/coverage_analyzer.py"])
    if _module_uses(cov, cov, "h5py") or "manifest.json" in _str_consts(cov):
        hits.append("coverage_analyzer：仍有 h5py 或 V1 `manifest.json` 掃描")
    ic = ast.parse(sources["api/services/ic_analysis_service.py"])
    for fn in _func_nodes(ic, "list_features"):
        consts = _str_consts(fn)
        if _module_uses(fn, ic, "h5py") or "data" in consts or any(c.startswith("parquet:") for c in consts):
            hits.append("ic_analysis_service.list_features：仍有舊 h5／parquet: 讀取枝")
    ffs = ast.parse(sources["api/services/feature_factory_service.py"])
    consts = _str_consts(ffs)
    if "parquet_path" in consts or "7.0" in consts:
        hits.append("feature_factory_service：仍有舊 cgsa_work 列表格式（parquet_path）或 V7 轉向（7.0）")
    for n in ast.walk(ffs):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" \
                and isinstance(n.func.value, ast.Name) and n.func.value.id in {"manifest", "raw_manifest"} \
                and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "total_rows":
            hits.append(f"feature_factory_service：L{n.lineno} 仍有舊格式 total_rows 退回")
    for gone in ("_load_hdf5_features_df", "_csv_chunk_generator_from_hdf5"):
        if _func_nodes(ffs, gone):
            hits.append(f"feature_factory_service：仍定義 {gone}")
    allowed = {id(x) for fn in _func_nodes(ffs, "_load_cgsa_kline_timestamps") for x in ast.walk(fn)}
    bound = _bound_names(ffs, "h5py")
    stray = [n.lineno for n in ast.walk(ffs) if isinstance(n, ast.Name) and n.id in bound and id(n) not in allowed]
    stray += [n.lineno for n in ast.walk(ffs) if isinstance(n, ast.ImportFrom) and n.module == "h5py"]
    if stray:
        hits.append(f"feature_factory_service：kline 讀取以外仍用 h5py（L{stray}）")
    fbs = ast.parse(sources["api/services/feature_browser_service.py"])
    attrs = [n.attr for n in ast.walk(fbs) if isinstance(n, ast.Attribute) and n.attr in {"_feature_library", "_feature_reader"}]
    imports = [a.name for n in ast.walk(fbs) if isinstance(n, ast.ImportFrom) for a in n.names
               if a.name in {"create_feature_library", "create_feature_reader"}]
    if attrs or imports:
        hits.append(f"feature_browser_service：仍有無用屬性或工廠匯入 {sorted(set(attrs + imports))}")
    return hits


STRUCTURAL_FILES = ("momentum/Analysis/coverage_analyzer.py", "api/services/ic_analysis_service.py",
                    "api/services/feature_factory_service.py", "api/services/feature_browser_service.py")


def test_boundary_21_old_branches_structurally_absent():
    """Task 2.3／2.5／2.6：coverage 無 h5py／V1 manifest 掃描；IC list_features 無舊 h5／parquet: 枝；瀏覽服務無舊 cgsa_work
    列表格式、V7 轉向、舊格式 total_rows 退回、factory h5 讀取（h5py 只准於 kline 讀取）；瀏覽器服務無無用屬性與工廠匯入
    （審查 r36 CODEX-R36-P1-01／P2-03）。"""
    assert structural_residues({p: (REPO / p).read_text(encoding="utf-8") for p in STRUCTURAL_FILES}) == []


def test_mutation_structural_residue_scan_detects_early_guard_leftovers():
    """在舊枝前加早退而保留後方死碼 ⇒ 命中；V2 合法寫法不命中。"""
    clean = {
        "momentum/Analysis/coverage_analyzer.py": "def f():\n    return reader.list_features_v2(a, b, c)\n",
        "api/services/ic_analysis_service.py": (
            "def list_features(self, features_path=None, *, symbol=None):\n"
            "    if features_path:\n        raise ValueError('use symbol, timeframe and config_hash')\n"
            "    return reader.list_features_v2(symbol)\n"),
        "api/services/feature_factory_service.py": (
            "import h5py\n"
            "def _load_cgsa_kline_timestamps(self):\n    with h5py.File(p) as f:\n        return f\n"
            "def summary(self, fast):\n    return fast.get('total_rows')\n"),
        "api/services/feature_browser_service.py": (
            "from momentum.factories import create_coverage_analyzer\n"
            "class FeatureBrowserService:\n    def __init__(self):\n        self._coverage_analyzer = create_coverage_analyzer()\n"),
    }
    assert structural_residues(clean) == []
    leftovers = {
        "momentum/Analysis/coverage_analyzer.py": "import h5py\n",
        "api/services/ic_analysis_service.py": (
            "def list_features(self, features_path=None):\n"
            "    if features_path:\n        raise ValueError('x')\n"
            "    with h5py.File(features_path) as f:\n        return f['data']\n"),
        "api/services/feature_factory_service.py": "def g(manifest):\n    return manifest.get('total_rows')\n",
        "api/services/feature_browser_service.py": "class S:\n    def __init__(self):\n        self._feature_reader = 1\n",
    }
    for path, src in leftovers.items():
        assert structural_residues({**clean, path: src}) != [], path
    assert structural_residues({**clean, "api/services/feature_factory_service.py":
                                "def _load_hdf5_features_df(self):\n    pass\n"}) != []
    assert structural_residues({**clean, "api/services/feature_factory_service.py":
                                "x = {'parquet_path': 1}\n"}) != []
    # 審查 r37 CODEX-R37-P1-01：別名匯入與別名使用
    for path, src in (
        ("momentum/Analysis/coverage_analyzer.py", "import h5py as hp\ndef f(p):\n    return hp.File(p)\n"),
        ("momentum/Analysis/coverage_analyzer.py", "from h5py import File as H5File\ndef f(p):\n    return H5File(p)\n"),
        ("api/services/feature_factory_service.py",
         "import h5py as hp\ndef _load_cgsa_kline_timestamps(self):\n    return hp.File(k)\n"
         "def _load_old(self, p):\n    return hp.File(p)\n"),
        ("api/services/ic_analysis_service.py",
         "import h5py as hp\ndef list_features(self, features_path=None):\n    return hp.File(features_path)\n"),
    ):
        assert structural_residues({**clean, path: src}) != [], (path, src)
    # 別名之 kline 讀取仍屬合法
    assert structural_residues({**clean, "api/services/feature_factory_service.py":
                                "import h5py as hp\ndef _load_cgsa_kline_timestamps(self):\n    return hp.File(k)\n"}) == []
