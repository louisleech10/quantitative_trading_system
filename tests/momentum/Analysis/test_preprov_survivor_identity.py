"""PRE-PROV（docs/FFDSTAR_SPEC.md Task 2.4）：IC 輸出（報告 metadata、倖存者 provenance、API 結果）帶同一 run 身分物件。

驗證（SPEC Task 2.4）：真實短窗 IC 分析之報告與倖存者 `ff_run_identity` 等於 Task 2.1 身分；倖存者契約驗證器拒收
缺該鍵之新版本輸出（契約 `version` +1、`provenance_keys` 加 `ff_run_identity`）。
邊界（⇒ boundary_01–02）：①事件型路徑（`_run_event_label_stages`）同樣帶身分；②IC 選擇為空。
mutation：倖存者改寫入 ingest 快取檔之舊身分 ⇒ 身分相等案紅。

驅動：經服務入口 `ICAnalysisService._run_analysis`（與 `/analyze` 同一路徑：物化 ingest 快取 → orchestrator →
報告／倖存者落檔 → 結果寫回 task），以真實 kline 短窗 run（`preprov_helpers`，格 `h1_stat_on`，本模組生成一次）。
隔離：orchestrator 與服務之輸出寫死相對路徑（`data_cache/reports`、`data_cache/reports/ic_ingest_cache`、
`data_cache/features/<sym>_<tf>_filtered.h5`），IC 設定讀相對 `config/`，標籤 kline 讀相對 `data_cache/feature_klines`
（ic_analysis_service.py:500）⇒ 本模組 cwd 移到 tmp（`config` 以 symlink 指回 repo、kline 目錄常數改絕對路徑），
不寫入專案 data_cache。事件型邊界之事件紀錄以該 run 之真實時間軸為 t0（事件屬使用者輸入，非特徵矩陣）。
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pytest

from api.models.ic_models import ICAnalyzeRequest
from api.services import ic_analysis_service as svc_mod
from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis import survivor_contract as sc
from momentum.Analysis.event_samples.import_contract import canonical_event_id
from momentum.Analysis.ic_config_schema import ContractValidationError
from momentum.factories import create_ic_analyzer
from momentum.FeatureEngineering import run_provenance as rp
from momentum.FeatureEngineering.feature_library import FeatureLibrary
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.timeout(3600)

REPO = Path(__file__).resolve().parents[3]
CONTRACT: Dict[str, Any] = json.loads(rp.CONTRACT_PATH.read_text(encoding="utf-8"))
IDENTITY_KEYS: List[str] = list(CONTRACT["run_identity_keys"])
IDENTITY_KEY = "ff_run_identity"  # SPEC Task 2.4 之報告／倖存者鍵名
# 改前碼態之倖存者契約版本（momentum/Analysis/contracts/ic_survivor_contract.json，HEAD＝2）；SPEC D5：+1
PRE_CHANGE_SURVIVOR_CONTRACT_VERSION = 2
# SPEC Task 2.1「`load` 新增回傳身分之入口」未定名；同 tests/feature_engineering/test_preprov_identity.py
LOAD_WITH_IDENTITY = "load_with_identity"
CELL = "h1_stat_on"


def expected_identity(manifest: Dict[str, Any], artifact_kind: str = "raw") -> Dict[str, Any]:
    """測試端獨立 oracle：自 manifest 原文逐鍵取 run 身分（同 test_preprov_identity.py）。"""
    node = (manifest.get("artifacts") or {}).get(artifact_kind) or {}
    prov = node.get("provenance")
    out = {
        "symbol": manifest.get("symbol"),
        "tf": manifest.get("tf"),
        "config_hash": manifest.get("config_hash"),
        "feature_schema_hash": node.get("feature_schema_hash", manifest.get("feature_schema_hash")),
        "feature_naming_version": manifest.get("feature_naming_version"),
        "artifact_kind": artifact_kind,
        "content_sha256": node.get("content_sha256"),
        "provenance_sha256": prov.get("sha256") if isinstance(prov, dict) else None,
    }
    assert set(out) == set(IDENTITY_KEYS), "契約 run_identity_keys 改動須同步本 oracle"
    return out


def library_for(run: Any) -> FeatureLibrary:
    root = Path(run.features_root)
    registry_path = root / "registry.json"
    assert registry_path.is_file(), f"前提不成立：隔離特徵根無 registry（{registry_path}）"
    return FeatureLibrary(FeatureRegistry(registry_path), FeatureStorage(str(root)), feature_reader=FeatureReader(str(root)))


def run_analysis(run: Any, request: ICAnalyzeRequest, *, event_batch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """經服務入口跑一次真實 IC 分析；完成後立即讀出倖存者檔（各次分析同 case_id 會覆寫同一檔）。"""
    service = ICAnalysisService()
    service._feature_library = library_for(run)  # noqa: SLF001 — 服務特徵根換成該 run 之隔離根
    task_id = f"preprov-{uuid.uuid4().hex[:12]}"
    service._tasks[task_id] = {"task_id": task_id, "status": "running", "progress": 0.0, "error": None, "result": None}
    asyncio.run(service._run_analysis(task_id, create_ic_analyzer(), request,
                                      service._build_config_override(request), event_batch=event_batch))
    info = service._tasks[task_id]
    assert info["status"] == "completed", f"IC 分析未完成：{info.get('error')!r}"
    report = info["result"]
    status = (report.get("metadata") or {}).get("survivor_output") or {}
    survivor = json.loads(Path(status["path"]).read_text(encoding="utf-8")) if status.get("path") else None
    return {"report": report, "survivor_status": status, "survivor": survivor, "api": service.get_result(task_id)}


def survivor_identity(result: Dict[str, Any]) -> Any:
    assert result["survivor"] is not None, f"倖存者檔未寫出：{result['survivor_status']!r}"
    return result["survivor"]["provenance"].get(IDENTITY_KEY)


def identity_carried(result: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    """oracle：報告 metadata、API 結果、倖存者 provenance 三處之身分皆等於期望。"""
    report_id = (result["report"].get("metadata") or {}).get(IDENTITY_KEY)
    api_id = ((result["api"] or {}).get("metadata") or {}).get(IDENTITY_KEY)
    return report_id == expected and api_id == expected and survivor_identity(result) == expected


# ---------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Dict[str, Any]]:
    run = ph.generate_short_run(tmp_path_factory.mktemp("preprov_survivor_run"), CELL)
    work = tmp_path_factory.mktemp("preprov_survivor_cwd")
    (work / "config").symlink_to(REPO / "config")
    mp = pytest.MonkeyPatch()
    mp.chdir(work)
    mp.setattr(svc_mod, "FEATURE_KLINE_CACHE_DIR", str(REPO / "data_cache" / "feature_klines"))
    manifest = json.loads((Path(run.run_dir) / FeatureReader.V2_MANIFEST_NAME).read_text(encoding="utf-8"))
    try:
        yield {"run": run, "work": work, "manifest": manifest, "expected": expected_identity(manifest)}
    finally:
        mp.undo()


def _request(run: Any, **kwargs: Any) -> ICAnalyzeRequest:
    return ICAnalyzeRequest(symbol=run.symbol, timeframe=run.tf, config_hash=run.config_hash, **kwargs)


@pytest.fixture(scope="module")
def analysis(env: Dict[str, Any]) -> Dict[str, Any]:
    """全域（非事件）IC 分析一次。"""
    return run_analysis(env["run"], _request(env["run"]))


@pytest.fixture(scope="module")
def empty_analysis(env: Dict[str, Any]) -> Dict[str, Any]:
    """IC 選擇為空：IC 平均下限 1.0（|IC|≤1，無特徵可過）。"""
    return run_analysis(env["run"], _request(env["run"], config_override={"thresholds": {"ic_mean_min": 1.0}}))


def _event_batch(run: Any) -> Dict[str, Any]:
    """事件批：以該 run 真實時間軸上等距之 bar 為 t0（避開首尾各 15%，留答案窗），報酬規則 label。"""
    axis = FeatureReader(str(run.features_root)).load_row_index_v2(run.symbol, run.tf, run.config_hash)
    assert axis is not None and len(axis) >= 200, "前提不成立：run 時間軸過短，事件不足"
    lo, hi = int(len(axis) * 0.15), int(len(axis) * 0.85)
    step = max(1, (hi - lo) // 80)
    records = []
    for i, pos in enumerate(range(lo, hi, step)):
        t0 = int(axis[pos].value // 10**6)
        records.append({
            "event_id": canonical_event_id(run.symbol, run.tf, t0), "symbol": run.symbol, "timeframe": run.tf,
            "t0": t0, "decision_offset_bars": 0, "entry_price_semantic": "trigger_close", "direction": "long",
            "scenario": "C", "label": i % 2,
            "label_definition": {"rule_id": "preprov", "canonical_digest": "c" * 64, "window": {"horizon_bars": 2},
                                 "label_return_mode": "close_to_close"},
            "control_kind": "user_labeled_same_trigger", "source_file_digest": "a" * 64,
            "data_snapshot_digest": "b" * 64,
        })
    return {
        "records": tuple(records),
        "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                             "label_return_mode": "close_to_close", "decision_offset_bars": 0},
        "lookahead_bars_declared": {run.tf: 0},
    }


@pytest.fixture(scope="module")
def event_analysis(env: Dict[str, Any]) -> Dict[str, Any]:
    run = env["run"]
    request = _request(run, event_import_id="preprov-event-batch", event_label_mode="return_rule")
    return run_analysis(run, request, event_batch=_event_batch(run))


# ---------------------------------------------------------------- 驗證


def test_report_and_survivor_identity_equal_task21_identity(env: Dict[str, Any], analysis: Dict[str, Any]) -> None:
    """報告 metadata、API 結果、倖存者 provenance 之 `ff_run_identity` 等於 Task 2.1 身分（自 manifest 逐鍵、
    且等於 FeatureLibrary 回傳身分之入口所得）；倖存者 `config_hash`（IC 設定雜湊）語意不變。"""
    run, expected = env["run"], env["expected"]
    assert expected["content_sha256"], "前提不成立：manifest 無 content_sha256（Task 1.3 未落地）"
    _df, identity = getattr(library_for(run), LOAD_WITH_IDENTITY)(run.symbol, run.tf, config_hash=run.config_hash)
    assert identity.to_dict() == expected
    assert (analysis["report"].get("metadata") or {}).get(IDENTITY_KEY) == expected
    assert ((analysis["api"] or {}).get("metadata") or {}).get(IDENTITY_KEY) == expected
    assert survivor_identity(analysis) == expected
    assert identity_carried(analysis, expected)
    # 倖存者 config_hash 仍為 IC 設定雜湊，不得被特徵 run 之 config_hash 取代
    assert analysis["survivor"]["provenance"]["config_hash"] != run.config_hash


def test_survivor_contract_requires_ff_run_identity(analysis: Dict[str, Any]) -> None:
    """契約 `version` +1、`provenance_keys` 含必填之 `ff_run_identity`；驗證器收真實輸出、拒收缺該鍵之新版本輸出。"""
    contract = sc.load_survivor_contract()
    assert contract["version"] == PRE_CHANGE_SURVIVOR_CONTRACT_VERSION + 1
    spec = contract["provenance_keys"]["keys"].get(IDENTITY_KEY)
    assert spec is not None and spec.get("required", True) is True
    payload = analysis["survivor"]
    assert payload is not None and payload["schema_version"] == contract["version"]
    sc.validate_survivor_output(copy.deepcopy(payload))  # 基線：真實輸出可過
    missing = copy.deepcopy(payload)
    del missing["provenance"][IDENTITY_KEY]
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(missing)


# ---------------------------------------------------------------- 邊界


def test_boundary_01_event_path_carries_identity(env: Dict[str, Any], event_analysis: Dict[str, Any]) -> None:
    """邊界①：事件型路徑（`event_import_id` ⇒ `_run_event_label_stages` 五階段）之報告、API 結果、倖存者同樣帶身分。"""
    meta = event_analysis["report"].get("metadata") or {}
    assert (meta.get("event_filter") or {}).get("mode") not in (None, "none"), "前提不成立：未走事件分支"
    assert identity_carried(event_analysis, env["expected"])


def test_boundary_02_empty_selection_carries_identity(env: Dict[str, Any], empty_analysis: Dict[str, Any]) -> None:
    """邊界②：IC 選擇為空 ⇒ 倖存者檔仍寫出（no_survivors）且三處身分皆等於本 run。"""
    payload = empty_analysis["survivor"]
    assert payload is not None and payload["feature_names"] == [], "前提不成立：選擇非空"
    assert payload["status"] == "not_applicable"
    assert identity_carried(empty_analysis, env["expected"])


# ---------------------------------------------------------------- mutation


def test_mutation_survivor_takes_stale_ingest_identity(env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：倖存者改寫入 ingest 快取檔之舊身分（同 config_hash、先前 run 之內容身分）⇒ 身分相等案翻轉。"""
    expected = env["expected"]
    stale = dict(expected, content_sha256=hashlib.sha256(b"stale ingest cache run").hexdigest())
    real = orch_mod.build_survivor_output

    def stale_build(**kwargs: Any) -> Dict[str, Any]:
        payload = real(**kwargs)
        payload["provenance"][IDENTITY_KEY] = dict(stale)
        return payload

    monkeypatch.setattr(orch_mod, "build_survivor_output", stale_build)
    result = run_analysis(env["run"], _request(env["run"]))
    assert survivor_identity(result) == stale
    assert not identity_carried(result, expected)
