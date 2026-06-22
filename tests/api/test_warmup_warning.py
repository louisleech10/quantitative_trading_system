"""B6c: warmup_insufficient API contract tests."""

from __future__ import annotations

from typing import Any, Dict, Optional

from api.services.feature_factory_service import FeatureFactoryService
from api.utils.warmup_contract import (
    coerce_warmup_insufficient,
    extract_warmup_insufficient_from_result,
    warmup_insufficient_items_from_completed,
)


def test_coerce_warmup_insufficient_valid() -> None:
    raw = {"needed": 500, "available": 120, "affected_bars": 380}
    assert coerce_warmup_insufficient(raw) == raw


def test_coerce_warmup_insufficient_rejects_partial() -> None:
    assert coerce_warmup_insufficient({"needed": 1, "available": 0}) is None


def test_extract_from_result_metadata() -> None:
    result = {
        "metadata": {
            "symbol": "BTCUSDT",
            "warmup_insufficient": {"needed": 10, "available": 3, "affected_bars": 7},
        }
    }
    assert extract_warmup_insufficient_from_result(result) == {
        "needed": 10,
        "available": 3,
        "affected_bars": 7,
    }


def test_extract_from_result_absent_when_sufficient() -> None:
    assert extract_warmup_insufficient_from_result({"metadata": {"symbol": "ETHUSDT"}}) is None


def test_warmup_insufficient_items_from_completed_checkpoint() -> None:
    completed = [
        {
            "symbol": "BTCUSDT",
            "timeframe": "12h",
            "warmup_insufficient": {"needed": 500, "available": 50, "affected_bars": 450},
        },
        {"symbol": "ETHUSDT", "timeframe": "12h"},
    ]
    items = warmup_insufficient_items_from_completed(completed)
    assert len(items) == 1
    assert items[0]["symbol"] == "BTCUSDT"
    assert items[0]["warmup_insufficient"]["affected_bars"] == 450


def _seed_task(
    service: FeatureFactoryService,
    task_id: str,
    result: Optional[Dict[str, Any]],
    *,
    status: str = "completed",
) -> None:
    with service._lock:
        service._tasks[task_id] = {
            "task_id": task_id,
            "status": status,
            "progress": 1.0,
            "current_stage": "completed",
            "completed_stages": ["completed"],
            "error": None,
            "result": result,
            "schema_version": 1,
        }


def test_get_task_status_promotes_warmup_insufficient() -> None:
    service = FeatureFactoryService()
    task_id = "warmup-task-1"
    result = {
        "metadata": {
            "warmup_insufficient": {"needed": 200, "available": 80, "affected_bars": 120},
        }
    }
    _seed_task(service, task_id, result)

    status = service.get_task_status(task_id)
    assert status is not None
    assert status["warmup_insufficient"] == {
        "needed": 200,
        "available": 80,
        "affected_bars": 120,
    }


def test_get_task_status_omits_warmup_when_sufficient() -> None:
    service = FeatureFactoryService()
    task_id = "warmup-task-2"
    _seed_task(service, task_id, {"metadata": {"symbol": "SOLUSDT"}})

    status = service.get_task_status(task_id)
    assert status is not None
    assert status.get("warmup_insufficient") is None
