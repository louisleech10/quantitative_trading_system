"""IC analysis service integration tests for run selector."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pandas as pd
import pytest

from api.models.ic_models import ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
HASH_A = "1c4b825498449860a639b0ac37f66d73"


class _SleepingAnalyzer:
    def analyze(self, **_kwargs):
        time.sleep(0.2)
        return {"summary_table": []}

    def analyze_cross_sectional(self, **_kwargs):
        time.sleep(0.2)
        return {"summary_table": []}


class _ProgressAnalyzer:
    def analyze(self, **kwargs):
        progress_callback = kwargs["progress_callback"]
        progress_callback({"stage": "ic_calculation", "progress": 0.5, "message": "worker tick"})
        return {"summary_table": []}


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


@pytest.mark.asyncio
async def test_run_analysis_does_not_block_event_loop(monkeypatch) -> None:
    service = ICAnalysisService()
    analyzer = _SleepingAnalyzer()

    async def run_and_probe(task_id: str, request: ICAnalyzeRequest) -> None:
        service._tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "error": None,
            "result": None,
        }
        started = time.perf_counter()
        task = asyncio.create_task(service._run_analysis(task_id, analyzer, request, {}))
        await asyncio.sleep(0.02)
        elapsed = time.perf_counter() - started
        await task

        assert elapsed < 0.1
        assert service.get_task_status(task_id)["status"] == "completed"

    await run_and_probe(
        "longitudinal-task",
        ICAnalyzeRequest(features_path="features.h5", labels_path="labels.h5"),
    )

    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0],
            "label": [0.1, 0.2],
        },
        index=pd.Index([1, 2], name="timestamp"),
    )
    monkeypatch.setattr(
        service,
        "_feature_library",
        SimpleNamespace(load_multi=lambda *_args, **_kwargs: {"BTC": frame, "ETH": frame}),
    )

    await run_and_probe(
        "cross-sectional-task",
        ICAnalyzeRequest(
            mode="cross_sectional",
            symbols=["BTC", "ETH"],
            timeframe="12h",
            labels_path="labels.h5",
        ),
    )


@pytest.mark.asyncio
async def test_progress_callback_from_to_thread_schedules_on_event_loop() -> None:
    service = ICAnalysisService()
    task_id = "progress-task"
    scheduled: list[asyncio.Task] = []
    callback_errors: list[str] = []

    async def noop() -> None:
        return None

    def notification_callback(payload):
        if payload.get("status") != "running":
            return
        try:
            scheduled.append(asyncio.create_task(noop()))
        except RuntimeError as exc:
            callback_errors.append(str(exc))
            raise

    service._tasks[task_id] = {
        "task_id": task_id,
        "status": "running",
        "progress": 0.0,
        "error": None,
        "result": None,
    }
    service.register_notification_callback(task_id, notification_callback)

    await service._run_analysis(
        task_id,
        _ProgressAnalyzer(),
        ICAnalyzeRequest(features_path="features.h5", labels_path="labels.h5"),
        {},
    )
    await asyncio.sleep(0)

    assert callback_errors == []
    assert len(scheduled) == 1
    await scheduled[0]
    assert service.get_task_status(task_id)["status"] == "completed"
