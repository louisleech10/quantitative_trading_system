"""Batch status layer fields + WS mapper tests (T2 Task 2.1)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from api.models.feature_factory_models import BatchGenerateRequest, BatchTaskStatusResponse
from api.services.feature_factory_batch_service import FeatureFactoryBatchService
from api.websocket.feature_factory_ws import map_batch_progress_ws_data


def test_batch_task_status_response_accepts_layer_fields() -> None:
    """Pydantic model 接受 current_stage/stage_progress/current_rss_mb。"""
    model = BatchTaskStatusResponse(
        task_id="batch-1",
        status="running",
        total=2,
        completed=0,
        failed=0,
        progress=0.0,
        current_symbol="BTCUSDT",
        current_timeframe="1h",
        current_stage="layer_3",
        stage_progress=0.5,
        current_rss_mb=512,
    )
    dumped = model.model_dump()
    assert dumped["current_stage"] == "layer_3"
    assert dumped["stage_progress"] == 0.5
    assert dumped["current_rss_mb"] == 512


def test_tail_layer_metrics_jsonl_skips_partial_lines(tmp_path) -> None:
    """半行 JSONDecodeError 跳過不 crash。"""
    path = tmp_path / "layer_metrics.jsonl"
    path.write_text(
        '{"symbol":"BTCUSDT","stage":"layer_0"}\n'
        '{"broken"\n'
        '{"symbol":"BTCUSDT","timeframe":"1h","stage":"layer_1","progress":1.0,"rss_mb":128}\n',
        encoding="utf-8",
    )
    rows = FeatureFactoryBatchService._tail_layer_metrics_jsonl(path)
    assert len(rows) == 2
    assert rows[-1]["stage"] == "layer_1"


def test_apply_layer_metrics_to_task_concurrent_one(batch_service_factory, tmp_path) -> None:
    """concurrent=1 時 tail 最新 row 併入 task status。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-layer-1"
    layer_path = service._layer_metrics_path(task_id)
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "stage": "layer_0",
            "progress": 0.0,
            "rss_mb": 100,
            "schema_version": 1,
        },
        {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "stage": "layer_2",
            "progress": 0.75,
            "rss_mb": 256,
            "schema_version": 1,
        },
    ]
    with layer_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    task = {
        "task_id": task_id,
        "concurrent_symbols": 1,
        "current_symbol": "BTCUSDT",
        "current_timeframe": "1h",
    }
    service._apply_layer_metrics_to_task(task, task_id)
    assert task["current_stage"] == "layer_2"
    assert task["stage_progress"] == 0.75
    assert task["worker_rss_mb"] == 256
    assert task["current_rss_mb"] == 256


def test_apply_layer_metrics_skipped_when_concurrent_gt_one(batch_service_factory, tmp_path) -> None:
    """concurrent>1 不加 per-symbol layer 欄位。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-layer-2"
    task = {
        "task_id": task_id,
        "concurrent_symbols": 2,
        "current_symbol": "BTCUSDT",
        "current_timeframe": "1h",
        "current_stage": "layer_1",
        "stage_progress": 0.5,
        "current_rss_mb": 128,
    }
    service._apply_layer_metrics_to_task(task, task_id)
    assert "current_stage" not in task
    assert "stage_progress" not in task
    assert "current_rss_mb" not in task


def test_apply_layer_metrics_clears_on_symbol_handoff(batch_service_factory, tmp_path) -> None:
    """換手到下一 symbol 且尚無匹配 row 時不得殘留前一 symbol 的 layer。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-layer-handoff"
    layer_path = service._layer_metrics_path(task_id)
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    with layer_path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "stage": "layer_3",
                    "progress": 0.8,
                    "rss_mb": 300,
                    "schema_version": 1,
                }
            )
            + "\n"
        )

    task = {
        "task_id": task_id,
        "concurrent_symbols": 1,
        "current_symbol": "BTCUSDT",
        "current_timeframe": "1h",
    }
    service._apply_layer_metrics_to_task(task, task_id)
    assert task["current_stage"] == "layer_3"
    assert task["stage_progress"] == 0.8
    assert task["worker_rss_mb"] == 300
    assert task["current_rss_mb"] == 300

    task["current_symbol"] = "ETHUSDT"
    task["current_timeframe"] = "1h"
    service._apply_layer_metrics_to_task(task, task_id)
    assert "current_stage" not in task
    assert "stage_progress" not in task
    assert "current_rss_mb" not in task


def test_get_status_includes_layer_fields(batch_service_factory, tmp_path) -> None:
    """get_status 回傳 current_stage 等欄位。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-layer-3"
    service._tasks[task_id] = {
        "task_id": task_id,
        "status": "running",
        "total": 1,
        "completed": 0,
        "failed": 0,
        "results": {},
        "errors": {},
        "concurrent_symbols": 1,
        "current_symbol": "ETHUSDT",
        "current_timeframe": "4h",
    }
    layer_path = service._layer_metrics_path(task_id)
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    FeatureFactoryBatchService._append_child_metrics_jsonl(
        layer_path,
        {
            "symbol": "ETHUSDT",
            "timeframe": "4h",
            "stage": "layer_6_5",
            "progress": 0.25,
            "rss_mb": 640,
            "schema_version": 1,
        },
    )

    status = service.get_status(task_id)
    assert status is not None
    assert status["current_stage"] == "layer_6_5"
    assert status["stage_progress"] == 0.25
    assert status["worker_rss_mb"] == 640
    assert status["current_rss_mb"] == 640


def test_ws_mapper_emits_layer_fields() -> None:
    """WS mapper 輸出 JSON 含正確 layer 觀測值。"""
    payload = {
        "task_id": "batch-ws-1",
        "total": 2,
        "completed": 1,
        "failed": 0,
        "current_symbol": "BTCUSDT",
        "current_timeframe": "1h",
        "current_stage": "layer_4",
        "stage_progress": 0.42,
        "worker_rss_mb": 768,
        "current_rss_mb": 768,
        "schema_version": 1,
        "progress": 0.5,
        "status": "running",
        "queued": 1,
        "concurrent_symbols": 1,
        "memory_sanity_failed": False,
        "last_item_metrics": None,
    }

    mapped = map_batch_progress_ws_data(payload)
    assert mapped["current_stage"] == "layer_4"
    assert mapped["stage_progress"] == 0.42
    assert mapped["worker_rss_mb"] == 768
    assert mapped["current_rss_mb"] == 768
    assert mapped["schema_version"] == 1
    assert mapped["current_symbol"] == "BTCUSDT"
    assert mapped["current_timeframe"] == "1h"


@pytest.mark.asyncio
async def test_layer_metrics_tick_cancelled_on_wave_exception(
    monkeypatch,
    batch_service_factory,
    tmp_path,
) -> None:
    """tick 建立後 wave 拋錯時不得殘留 pending tick task。"""
    service = batch_service_factory(tmp_path)
    tick_tasks: List[asyncio.Task[Any]] = []
    real_create_task = asyncio.create_task

    def capture_create_task(coro, *args, **kwargs):
        task = real_create_task(coro, *args, **kwargs)
        qualname = getattr(coro, "__qualname__", "")
        if "_layer_metrics_tick" in qualname:
            tick_tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", capture_create_task)

    class ExplodingExecutor:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("executor setup failed")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ExplodingExecutor,
    )

    task = {
        "task_id": "batch-tick-cancel",
        "concurrent_symbols": 1,
        "total": 1,
        "completed": 0,
        "failed": 0,
        "results": {},
        "errors": {},
    }
    checkpoint = {
        "batch_id": "batch-tick-cancel",
        "queued_items": [{"symbol": "BTCUSDT", "timeframe": "1h"}],
    }
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h")

    with pytest.raises(RuntimeError, match="executor setup failed"):
        await service._process_item_wave(
            task,
            checkpoint,
            [{"symbol": "BTCUSDT", "timeframe": "1h"}],
            request,
            str(tmp_path),
        )

    await asyncio.sleep(0)
    assert tick_tasks, "expected layer metrics tick task to be created"
    assert all(tick_task.done() for tick_task in tick_tasks)
    pending_ticks = [
        pending
        for pending in asyncio.all_tasks()
        if pending is not asyncio.current_task()
        and not pending.done()
        and "_layer_metrics_tick" in getattr(pending.get_coro(), "__qualname__", "")
    ]
    assert pending_ticks == []
