"""IC analysis service integration tests for run selector."""

from __future__ import annotations

import asyncio

import pytest

from api.models.ic_models import ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
HASH_A = "1c4b825498449860a639b0ac37f66d73"


def _require_run() -> None:
    service = ICAnalysisService()
    if service._feature_library._registry.get(SYMBOL, TIMEFRAME, HASH_A) is None:
        pytest.skip(f"missing registry run {HASH_A}")


@pytest.mark.asyncio
@pytest.mark.ic_run_selector
@pytest.mark.analyze_real_run
async def test_analyze_real_run_with_config_hash_completes() -> None:
    _require_run()
    service = ICAnalysisService()
    request = ICAnalyzeRequest(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        config_hash=HASH_A,
        config_override={
            "thresholds": {
                "ic_mean_min": -1.0,
                "icir_min": -1.0,
                "p_value_max": 1.0,
            },
            "report": {"include_regime_analysis": False, "include_decay_analysis": False},
        },
    )
    started = await service.start_analysis(request)
    task_id = started["task_id"]

    for _ in range(600):
        status = service.get_task_status(task_id)
        if status and status.get("status") in {"completed", "failed"}:
            break
        await asyncio.sleep(0.5)

    status = service.get_task_status(task_id)
    assert status is not None
    assert status["status"] == "completed", status.get("error")
    report = service.get_result(task_id)
    assert isinstance(report, dict)
    assert report.get("summary_table") is not None


@pytest.mark.ic_run_selector
def test_resolve_run_path_contains_config_hash() -> None:
    _require_run()
    service = ICAnalysisService()
    entry = service._feature_library._registry.get(SYMBOL, TIMEFRAME, HASH_A)
    assert entry is not None
    features_path, _meta_path = service._materialize_features_for_ic(SYMBOL, TIMEFRAME, HASH_A)
    assert HASH_A in entry["hdf5_relative_path"]
    assert features_path.endswith(".h5")
