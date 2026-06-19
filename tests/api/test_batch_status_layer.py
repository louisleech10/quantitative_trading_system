"""Batch status layer fields + WS mapper tests (T2 Task 2.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.models.feature_factory_models import BatchTaskStatusResponse
from api.services.feature_factory_batch_service import FeatureFactoryBatchService


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
    }
    service._apply_layer_metrics_to_task(task, task_id)
    assert "current_stage" not in task


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
    assert status["current_rss_mb"] == 640


def test_ws_mapper_whitelist_includes_layer_fields() -> None:
    """WS mapper 白名單含 layer 觀測欄位。"""
    import inspect
    import api.websocket.feature_factory_ws as ws_module

    source = inspect.getsource(ws_module.feature_factory_batch_websocket)
    assert "current_stage" in source
    assert "stage_progress" in source
    assert "current_rss_mb" in source
