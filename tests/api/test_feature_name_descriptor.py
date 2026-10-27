"""FF-NAME Task 1.2／3.3 — 欄名描述向量與 API 描述（docs/FFNAME_SPEC.md Task 1.2、Task 3.3）。

Task 1.2：`scripts/export_feature_name_vectors.py --check` rc 0；向量含 §G reference 全部新名之解析結果與拒收案例
（未知 category、非法參數字元、custom slug、TsCorr、label）；重產 sha256 相同。邊界：向量檔由腳本產生，手改即本檔紅。
審查 r12：向量檔每筆以 `parse_feature_name` 重新計算後逐筆相等（拒收以例外類別），契約 `rejection_cases` 每類至少一筆；
custom slug 類於欄名層以「indicator 不合 slug 字母表」表達（兩定義同 slug 之碰撞屬設定驗證，見 Task 2.2 測試）。
Task 3.3：描述之唯一供給點＝瀏覽投影 `FeatureFactoryService._project_browse_rows`，`names` 與 `table` 兩種 detail_level
共用同一投影並一律帶描述；各回傳欄名之 API 之描述 == Task 1.2 向量（含拒收時之錯誤描述）；兩種 detail_level 逐欄相等。
描述鍵、row 鍵、錯誤鍵與向量版面取自 `tests/_golden/ffname/contract.json`。前端靜態封閉與 vitest 見
`frontend/src/lib/featureDescriptor.static.test.ts`、`frontend/src/lib/featureDescriptor.test.ts`。
"""

from __future__ import annotations

import builtins
import copy
import dataclasses
import hashlib
import importlib.util
import json
import subprocess
import sys

from tests._nocap_subprocess import run_watched_subprocess
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
import momentum.FeatureEngineering.feature_naming as fn
from tests.feature_engineering.ffname_helpers import (
    CONTRACT,
    REPO,
    VALID,
    VECTORS_PATH,
    iter_new_names_from_baseline,
    patch_everywhere,
    real_slice,
)
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


def expected_valid_descriptor_fields(name: str) -> Dict[str, Any]:
    """由 `parse_feature_name` 重新計算之描述欄位（編碼依契約 `descriptor.encoding`；display 另驗非空）。"""
    ident = fn.parse_feature_name(name)
    return {"version": fn.CURRENT_FEATURE_NAMING_VERSION, "kind": ident.kind, "source": ident.source, "tf": ident.tf,
            "category": ident.category, "indicator": ident.indicator,
            "params": [list(member) for member in ident.params], "ops": list(ident.ops)}


def recompute_mismatches(vectors: Dict[str, Any]) -> List[str]:
    """向量檔逐筆重新計算後之不符項（審查 r12 CODEX-R12-P1-02：不得只比 hash 或數量）：
    合法名＝描述欄位逐一等於 parser 之身分；拒收名＝parser 實拋例外類別名等於描述之錯誤鍵，且等於該 case 之契約類別；
    契約 `rejection_cases` 每一類至少一筆。"""
    bad: List[str] = []
    for entry in vectors["valid"]:
        desc = entry["descriptor"]
        try:
            expected = expected_valid_descriptor_fields(entry["name"])
        except fn.FeatureNameParseError as exc:
            bad.append(f"valid_rejected_by_parser:{entry['name']}:{type(exc).__name__}")
            continue
        if {k: desc.get(k) for k in expected} != expected or not str(desc.get("display") or ""):
            bad.append(f"valid_mismatch:{entry['name']}")
    cases = DESC["rejection_cases"]
    seen = set()
    for entry in vectors["rejected"]:
        case = entry.get("case")
        if case not in cases:
            bad.append(f"unknown_case:{entry['name']}:{case}")
            continue
        try:
            fn.parse_feature_name(entry["name"])
            bad.append(f"not_rejected:{entry['name']}")
            continue
        except fn.FeatureNameParseError as exc:
            raised = type(exc).__name__
        if raised != cases[case]["exception"] or entry["descriptor"].get(DESC["error_key"]) != raised:
            bad.append(f"rejection_class_mismatch:{entry['name']}:{raised}")
        seen.add(case)
    bad += [f"missing_case:{c}" for c in sorted(set(cases) - seen)]
    return bad


# ---------------------------------------------------------------- Task 1.2

def test_export_script_check_rc0():
    proc = run_watched_subprocess([sys.executable, str(SCRIPT), "--check"], cwd=str(REPO))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_vectors_layout_and_coverage():
    vectors = _vectors()
    assert list(vectors) == DESC["vectors_layout"]["top_keys"]
    assert vectors["version"] == fn.CURRENT_FEATURE_NAMING_VERSION
    names_valid = {e["name"] for e in vectors["valid"]}
    names_rejected = {e["name"] for e in vectors["rejected"]}
    assert set(VALID.values()) <= names_valid
    assert set(iter_new_names_from_baseline()) <= names_valid  # §G reference 全部新名
    assert any("TsCorr-" in n for n in names_valid)
    for entry in vectors["valid"]:
        assert set(entry) == set(DESC["vectors_layout"]["entry_keys"])
        assert set(entry["descriptor"]) == set(DESC["keys"])
    for entry in vectors["rejected"]:
        assert entry["descriptor"].get(DESC["error_key"])
        assert set(entry) == set(DESC["vectors_layout"]["rejected_entry_keys"])
    assert any(n.startswith("label_") for n in names_rejected)
    assert len(names_rejected) >= 5  # 數量只作下限；逐類涵蓋由 test_vectors_recomputed_entry_by_entry 判定


def test_vectors_recomputed_entry_by_entry():
    assert recompute_mismatches(_vectors()) == []


def test_mutation_missing_rejection_class_or_copied_descriptor_is_caught():
    """mutant：刪除某一拒收類別之全部項，或把某合法項之描述換成另一名之描述（複製檔可過 hash 者）⇒ 重算比對翻紅。"""
    vectors = _vectors()
    assert recompute_mismatches(vectors) == [] and vectors["version"] == fn.CURRENT_FEATURE_NAMING_VERSION
    dropped = copy.deepcopy(vectors)
    victim_case = sorted(DESC["rejection_cases"])[0]
    dropped["rejected"] = [e for e in dropped["rejected"] if e.get("case") != victim_case]
    assert f"missing_case:{victim_case}" in recompute_mismatches(dropped)
    swapped = copy.deepcopy(vectors)
    if len(swapped["valid"]) >= 2:
        swapped["valid"][0]["descriptor"] = copy.deepcopy(swapped["valid"][1]["descriptor"])
        assert f"valid_mismatch:{swapped['valid'][0]['name']}" in recompute_mismatches(swapped)
    lenient = copy.deepcopy(vectors)
    lenient["rejected"][0]["descriptor"][DESC["error_key"]] = "Exception"
    assert any(b.startswith("rejection_class_mismatch:") for b in recompute_mismatches(lenient))


def _load_exporter():
    """以檔案路徑載入匯出腳本（模組名 ffname_export_vectors，供 patch_everywhere 一併替換其綁名）。"""
    spec = importlib.util.spec_from_file_location("ffname_export_vectors", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ffname_export_vectors"] = module
    spec.loader.exec_module(module)
    return module


def test_exporter_output_reflects_parser(monkeypatch, tmp_path):
    """審查 r13 CODEX-R13-P1-01：匯出器須由 parser 產生——把 `parse_feature_name` 換成對某合法名回傳可辨識身分之替身，
    `build_vectors()` 與 `--out` 產物皆須反映替身結果（讀回既有檔之實作必紅）。"""
    exporter = _load_exporter()
    probe = VALID["multi_output"]
    real = fn.parse_feature_name

    def probe_parse(name, *a, **k):
        ident = real(name, *a, **k)
        return dataclasses.replace(ident, indicator="FfnameProbe") if name == probe else ident

    replaced = patch_everywhere(monkeypatch, real, probe_parse, prefixes=("momentum", "api", "ffname_export_vectors"))
    assert replaced >= 1
    built = exporter.build_vectors()
    entry = next(e for e in built["valid"] if e["name"] == probe)
    assert entry["descriptor"]["indicator"] == "FfnameProbe"
    out = tmp_path / "vectors.json"
    assert exporter.write_vectors(out) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert next(e for e in written["valid"] if e["name"] == probe)["descriptor"]["indicator"] == "FfnameProbe"


def test_exporter_does_not_read_committed_vectors(monkeypatch, tmp_path):
    """審查 r13：匯出器不得讀回已提交向量檔——指向竄改之向量檔時輸出不變，且讀取正式向量檔即拋錯。"""
    exporter = _load_exporter()
    clean = exporter.build_vectors()
    tampered_path = tmp_path / "name_vectors.json"
    tampered_path.write_text(json.dumps({"version": 0, "valid": [], "rejected": []}), encoding="utf-8")
    monkeypatch.setattr(exporter, "VECTORS_PATH", tampered_path)
    real_vectors = VECTORS_PATH.resolve()
    real_read_text = Path.read_text
    real_open = builtins.open

    def guarded_read_text(self, *a, **k):
        if Path(self).resolve() == real_vectors:
            raise AssertionError("匯出器讀回已提交向量檔")
        return real_read_text(self, *a, **k)

    def guarded_open(file, *a, **k):
        if isinstance(file, (str, Path)) and Path(file).resolve() == real_vectors:
            raise AssertionError("匯出器讀回已提交向量檔")
        return real_open(file, *a, **k)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(builtins, "open", guarded_open)
    assert exporter.build_vectors() == clean
    out = tmp_path / "out.json"
    assert exporter.write_vectors(out) == 0
    assert json.loads(real_read_text(out, encoding="utf-8")) == clean


def test_vectors_regeneration_is_deterministic(tmp_path):
    out = tmp_path / "vectors.json"
    proc = run_watched_subprocess([sys.executable, str(SCRIPT), "--out", str(out)], cwd=str(REPO))
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
    manifest = raw_dir.parent / "feature_manifest.json"
    # FF-NAME Task 3.4（v19）：canonical run＝設定特徵根下且 registry 有條目 ⇒ 登記於 <root>/registry.json
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    FeatureRegistry(tmp_path / "features" / "registry.json").add(
        {"symbol": SYMBOL, "timeframe": PRIMARY_TF, "config_hash": "cfg_ffname", "hdf5_relative_path": str(manifest)})
    return manifest


def _service(manifest: Path) -> FeatureFactoryService:
    service = FeatureFactoryService()
    feature_root = manifest.parents[3]  # 測試之設定特徵根（＝_run_manifest 之 FeatureStorage 根；正式值為 settings）
    service._browse_feature_root = lambda: feature_root
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
