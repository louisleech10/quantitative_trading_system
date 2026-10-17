"""FF-NAME Task 1.2／3.3 — 欄名描述向量與 API 描述（docs/FFNAME_SPEC.md Task 1.2、Task 3.3）。

Task 1.2：`scripts/export_feature_name_vectors.py --check` rc 0；向量含 §G reference 全部新名之解析結果與拒收案例
（未知 category、非法參數字元、custom slug 碰撞、TsCorr、label）；重產 sha256 相同。邊界：向量檔由腳本產生，手改即本檔紅。
Task 3.3：描述之唯一供給點＝瀏覽投影 `FeatureFactoryService._project_browse_rows`，`names` 與 `table` 兩種 detail_level
共用同一投影並一律帶描述；各回傳欄名之 API 之描述 == Task 1.2 向量（含拒收時之錯誤描述）；兩種 detail_level 逐欄相等。
描述鍵、row 鍵、錯誤鍵與向量版面取自 `tests/_golden/ffname/contract.json`。前端靜態封閉與 vitest 見
`frontend/src/lib/featureDescriptor.static.test.ts`、`frontend/src/lib/featureDescriptor.test.ts`。
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx
import numpy as np
import pandas as pd
import pytest
import pytest_asyncio
from fastapi import FastAPI

import api.routes.feature_factory as feature_factory_routes
from api.routes.feature_factory import router as feature_factory_router
from api.services.feature_factory_service import FeatureFactoryService
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering.ffname_helpers import CONTRACT, REPO, VALID, VECTORS_PATH, real_slice
from tests.feature_engineering.ffstat_helpers import PRIMARY_TF, SYMBOL

DESC = CONTRACT["descriptor"]
ROW_KEY = DESC["row_key"]
SCRIPT = REPO / "scripts" / "export_feature_name_vectors.py"


def _vectors() -> Dict[str, Any]:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def _descriptor(name: str, detail_level: str) -> Dict[str, Any]:
    rows = FeatureFactoryService._project_browse_rows([{"name": name, "category": "x", "nan_ratio": 0.0}], detail_level)
    return rows[0][ROW_KEY]


def _vector_mismatches(vectors: Dict[str, Any], detail_level: str = "names") -> List[str]:
    bad = []
    for entry in vectors["valid"] + vectors["rejected"]:
        if _descriptor(entry["name"], detail_level) != entry["descriptor"]:
            bad.append(entry["name"])
    return bad


# ---------------------------------------------------------------- Task 1.2

def test_export_script_check_rc0():
    proc = subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=str(REPO), capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_vectors_layout_and_coverage():
    vectors = _vectors()
    assert list(vectors) == DESC["vectors_layout"]["top_keys"]
    names_valid = {e["name"] for e in vectors["valid"]}
    names_rejected = {e["name"] for e in vectors["rejected"]}
    assert set(VALID.values()) <= names_valid
    assert any("TsCorr-" in n for n in names_valid)
    for entry in vectors["valid"]:
        assert set(entry) == set(DESC["vectors_layout"]["entry_keys"])
        assert set(entry["descriptor"]) == set(DESC["keys"])
    for entry in vectors["rejected"]:
        assert entry["descriptor"].get(DESC["error_key"])
    assert any(n.startswith("label_") for n in names_rejected)
    assert len(names_rejected) >= 5  # 未知 category、非法參數字元、custom slug 碰撞、TsCorr 缺 digest、label


def test_vectors_regeneration_is_deterministic(tmp_path):
    out = tmp_path / "vectors.json"
    proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out)], cwd=str(REPO), capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr
    assert hashlib.sha256(out.read_bytes()).hexdigest() == hashlib.sha256(VECTORS_PATH.read_bytes()).hexdigest()


def test_boundary_01_hand_edited_vector_is_detected():
    vectors = _vectors()
    assert _vector_mismatches(vectors) == []
    edited = copy.deepcopy(vectors)
    edited["valid"][0]["descriptor"]["indicator"] = str(edited["valid"][0]["descriptor"]["indicator"]) + "-handedit"
    assert _vector_mismatches(edited) == [edited["valid"][0]["name"]]


# ---------------------------------------------------------------- Task 3.3

def test_descriptor_equals_vectors_both_detail_levels():
    vectors = _vectors()
    assert _vector_mismatches(vectors, "names") == []
    assert _vector_mismatches(vectors, "table") == []


def test_detail_levels_share_projection():
    for name in VALID.values():
        assert _descriptor(name, "names") == _descriptor(name, "table")
        assert set(_descriptor(name, "names")) == set(DESC["keys"])


def _run_manifest(tmp_path: Path) -> Path:
    """API 讀取 fixture：以正式 write_raw 寫 V2 run；欄值取真實 kline，欄名為合法新名。"""
    storage = FeatureStorage(str(tmp_path / "features"))
    kline = real_slice(16)
    names = [VALID["multi_output"], VALID["microstructure"], VALID["xsec"]]
    groups = {"g": pd.DataFrame({n: kline["close"].to_numpy(dtype=np.float32) for n in names}, index=kline.index)}
    raw_dir = storage.write_raw(SYMBOL, PRIMARY_TF, "cfg_ffname", groups, row_index=pd.DatetimeIndex(kline.index))
    return raw_dir.parent / "feature_manifest.json"


def _service(manifest: Path) -> FeatureFactoryService:
    service = FeatureFactoryService()
    with service._lock:
        service._tasks = {"task-ffname": {"status": "completed", "result": {
            "hdf5_path": str(manifest),
            "metadata": {"symbol": SYMBOL, "timeframe": PRIMARY_TF, "config_hash": "cfg_ffname"},
            "generation_time": 1.0, "layer_counts": {}}}}
    return service


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(feature_factory_router)
    return test_app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_browse_route_returns_descriptors_for_both_levels(client, monkeypatch, tmp_path):
    manifest = _run_manifest(tmp_path)
    monkeypatch.setattr(feature_factory_routes, "feature_factory_service", _service(manifest))
    by_level = {}
    for level in ("names", "table"):
        resp = await client.get(f"/api/v1/features/browse/task-ffname/features?detail_level={level}")
        assert resp.status_code == 200, resp.text
        rows = resp.json()["features"]
        by_level[level] = {r["name"]: r[ROW_KEY] for r in rows}
        for name, desc in by_level[level].items():
            assert desc == _descriptor(name, level)
    assert by_level["names"] == by_level["table"]


def test_mutation_names_level_without_descriptor_is_caught(monkeypatch):
    """mutant：`names` 投影不帶描述（只回 name）⇒ 與向量比對失敗。"""
    vectors = _vectors()
    monkeypatch.setattr(FeatureFactoryService, "_project_browse_rows",
                        staticmethod(lambda rows, detail_level: [{"name": r.get("name"), ROW_KEY: {}} for r in rows]))
    assert _vector_mismatches(vectors, "names") != []
