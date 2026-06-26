from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.core.config import settings
from api.routes.ic_analysis import ic_analysis_service, router
from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis.ic_artifact_writer import read, write
from momentum.core.contracts import ICResult


BASELINE_PATH = (
    Path(__file__).resolve().parents[1]
    / "golden"
    / "ic_phase1_contract"
    / "baseline_btc_1h.json"
)
BASELINE_TASK_ID = "baseline-btc-1h"
test_app = FastAPI()
test_app.include_router(router)
CLIENT = TestClient(test_app)


def _strip_dynamic(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def _has_key_recursive(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        return key_name in value or any(
            _has_key_recursive(item, key_name) for item in value.values()
        )
    if isinstance(value, list):
        return any(_has_key_recursive(item, key_name) for item in value)
    return False


def _restore_first_summary_row_to_ic_result(payload: dict[str, Any]) -> None:
    summary_table = payload["summary_table"]
    first_row = summary_table[0]
    summary_table[0] = ICResult(
        feature_name=first_row["feature_name"],
        ic_mean=first_row["ic_mean"],
        ic_std=first_row["ic_std"],
        icir=first_row["icir"],
        p_value=first_row["p_value"],
        ic_hit_rate=first_row["ic_hit_rate"],
        monotonicity_score=first_row["monotonicity_score"],
        long_short_spread=first_row["long_short_spread"],
        coverage=first_row["coverage"],
        turnover_rate=first_row["turnover_rate"],
        ic_half_life=first_row["ic_half_life"],
        regime_robust=first_row["regime_robust"],
    )


def _load_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.fixture
def baseline_task(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    baseline = _load_baseline()
    original_tasks = dict(ic_analysis_service._tasks)
    original_last_task_id = ic_analysis_service._last_task_id
    original_flag = settings.ic_response_v2
    monkeypatch.setattr(settings, "ic_response_v2", False)

    ic_analysis_service._tasks = {
        BASELINE_TASK_ID: {
            "task_id": BASELINE_TASK_ID,
            "status": "completed",
            "progress": 1.0,
            "error": None,
            "result": copy.deepcopy(baseline),
            "deep_analysis_top_n": 3,
            "ic_artifact_dir": tmp_path,
        }
    }
    ic_analysis_service._last_task_id = BASELINE_TASK_ID

    try:
        yield baseline
    finally:
        ic_analysis_service._tasks = original_tasks
        ic_analysis_service._last_task_id = original_last_task_id
        monkeypatch.setattr(settings, "ic_response_v2", original_flag)


def _artifact_path(tmp_path: Path, baseline: dict[str, Any]) -> Path:
    config_hash = baseline["metadata"]["config_hash"]
    return tmp_path / f"{BASELINE_TASK_ID}_{config_hash}_v2.parquet"


def _write_ranked_artifact(path: Path) -> list[dict[str, Any]]:
    rows = [
        {
            "feature_name": "alpha_low",
            "horizon": 5,
            "ic_mean": 0.10,
            "ic_std": 0.20,
            "icir": 0.50,
            "p_value": 0.20,
            "ic_hit_rate": 0.51,
            "eval_status": "evaluated",
            "selection_scope_id": "scope-a",
            "schema_version": 1,
        },
        {
            "feature_name": "alpha_top",
            "horizon": 5,
            "ic_mean": 0.42,
            "ic_std": 0.10,
            "icir": 4.20,
            "p_value": 0.01,
            "ic_hit_rate": 0.63,
            "eval_status": "evaluated",
            "selection_scope_id": "scope-a",
            "schema_version": 1,
        },
        {
            "feature_name": "alpha_mid",
            "horizon": 5,
            "ic_mean": 0.31,
            "ic_std": 0.11,
            "icir": 2.80,
            "p_value": 0.03,
            "ic_hit_rate": 0.59,
            "eval_status": "evaluated",
            "selection_scope_id": "scope-a",
            "schema_version": 1,
        },
        {
            "feature_name": "alpha_fourth",
            "horizon": 5,
            "ic_mean": 0.21,
            "ic_std": 0.15,
            "icir": 1.10,
            "p_value": 0.08,
            "ic_hit_rate": 0.55,
            "eval_status": "evaluated",
            "selection_scope_id": "scope-a",
            "schema_version": 1,
        },
    ]
    write(rows, path)
    return rows


def test_flag_off_get_result_no_eval_status_key() -> None:
    baseline = _load_baseline()
    task_payload = copy.deepcopy(baseline)
    _restore_first_summary_row_to_ic_result(task_payload)

    service = ICAnalysisService()
    service._tasks["baseline-task"] = {
        "task_id": "baseline-task",
        "status": "completed",
        "progress": 1.0,
        "error": None,
        "result": task_payload,
    }

    result = service.get_result("baseline-task")

    assert isinstance(result, dict)
    assert not _has_key_recursive(result, "eval_status")
    assert _strip_dynamic(result) == _strip_dynamic(baseline)


def test_flag_off_deep_equal_baseline(baseline_task: dict[str, Any]) -> None:
    response = CLIENT.get(f"/api/v1/ic/result/{BASELINE_TASK_ID}")

    assert response.status_code == 200
    assert _strip_dynamic(response.json()) == _strip_dynamic(baseline_task)


def test_route_v2_negotiation(
    baseline_task: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact_path = _artifact_path(tmp_path, baseline_task)
    _write_ranked_artifact(artifact_path)

    monkeypatch.setattr(settings, "ic_response_v2", True)
    v2_response = CLIENT.get(f"/api/v1/ic/result/{BASELINE_TASK_ID}?schema_version=2")
    assert v2_response.status_code == 200
    v2_payload = v2_response.json()
    assert v2_payload["schema_version"] == 2
    assert v2_payload["artifact_uri"] == str(artifact_path)
    assert v2_payload["total_features"] == 4
    assert "summary_table" not in v2_payload

    v1_response = CLIENT.get(f"/api/v1/ic/result/{BASELINE_TASK_ID}")
    assert v1_response.status_code == 200
    assert _strip_dynamic(v1_response.json()) == _strip_dynamic(baseline_task)

    monkeypatch.setattr(settings, "ic_response_v2", False)
    forced_v2_response = CLIENT.get(f"/api/v1/ic/result/{BASELINE_TASK_ID}?schema_version=2")
    assert forced_v2_response.status_code == 200
    assert _strip_dynamic(forced_v2_response.json()) == _strip_dynamic(baseline_task)


def test_v2_top_n_derived_from_artifact(
    baseline_task: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact_path = _artifact_path(tmp_path, baseline_task)
    _write_ranked_artifact(artifact_path)
    monkeypatch.setattr(settings, "ic_response_v2", True)

    response = CLIENT.get(f"/api/v1/ic/result/{BASELINE_TASK_ID}?schema_version=2")

    assert response.status_code == 200
    payload = response.json()
    artifact_rows = read(artifact_path)
    expected_top_n = sorted(artifact_rows, key=lambda row: -float(row["icir"]))[:3]
    assert payload["top_n_summary"] == expected_top_n


def test_flag_off_subroutes_unchanged(baseline_task: dict[str, Any]) -> None:
    feature_name = next(iter(baseline_task["ic_decay"]))
    cases = [
        (
            f"/api/v1/ic/decay/{feature_name}?task_id={BASELINE_TASK_ID}",
            baseline_task["ic_decay"][feature_name],
        ),
        (
            f"/api/v1/ic/quantile/{feature_name}?task_id={BASELINE_TASK_ID}",
            baseline_task["quantile_returns"][feature_name],
        ),
        (
            f"/api/v1/ic/correlation?task_id={BASELINE_TASK_ID}",
            baseline_task["correlation_matrix"],
        ),
        (
            f"/api/v1/ic/grouped?task_id={BASELINE_TASK_ID}",
            baseline_task["grouped_ic"],
        ),
    ]

    for path, expected in cases:
        response = CLIENT.get(path)
        assert response.status_code == 200
        assert _hash_json(response.json()) == _hash_json(expected)

    # 直接驗 service 匯出輸出（避開 StreamingResponse 在 TestClient 下的 generator hang；
    # 仍對 export 子端點輸出做 flag-off 不變回歸，不弱化驗證）。
    export_result = ic_analysis_service.export_analysis(BASELINE_TASK_ID, "json")
    assert export_result["type"] != "file"
    content = export_result["content"]
    if isinstance(content, (str, bytes)):
        raw = content
    else:
        chunks = list(content)
        raw = b"".join(chunks) if chunks and isinstance(chunks[0], bytes) else "".join(chunks)
    exported = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    assert _strip_dynamic(exported) == _strip_dynamic(baseline_task)


def test_export_route_streaming(baseline_task: dict[str, Any]) -> None:
    deadline = time.monotonic() + 2.0
    chunks: list[bytes] = []
    byte_cap = 4096

    with CLIENT.stream("GET", f"/api/v1/ic/export/{BASELINE_TASK_ID}/json") as response:
        assert response.status_code == 200
        assert "content-disposition" in response.headers
        assert "ic_report_" in response.headers["content-disposition"]
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            if sum(len(item) for item in chunks) >= byte_cap:
                break
            assert time.monotonic() < deadline

    body_prefix = b"".join(chunks)
    assert body_prefix
    assert body_prefix.lstrip().startswith(b"{")


def test_no_artifact_uri_none(
    baseline_task: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ic_response_v2", True)

    response = CLIENT.get(f"/api/v1/ic/result/{BASELINE_TASK_ID}?schema_version=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "schema_version": 2,
        "top_n_summary": [],
        "artifact_uri": None,
        "total_features": 0,
    }
