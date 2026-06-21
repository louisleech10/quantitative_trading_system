"""B2c: parity 5 RSS field contracts across REST/WS."""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from api.models.feature_factory_models import BatchTaskStatusResponse, FeatureTaskStatusResponse
from api.services.feature_factory_batch_service import FeatureFactoryBatchService
from api.services.feature_factory_service import FeatureFactoryService
from api.websocket.feature_factory_ws import map_batch_progress_ws_data
from momentum.FeatureEngineering.config_manager import ConfigManager


def test_parity_single_rest_process_rss_and_schema_version() -> None:
    """① 單 symbol REST 帶 process_rss_mb + schema_version(int)。"""
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = MagicMock()
    service._tasks = {
        "t1": {
            "task_id": "t1",
            "status": "running",
            "progress": 0.5,
            "current_stage": "layer_1",
            "completed_stages": [],
            "error": None,
            "result": None,
            "process_rss_mb": 600,
            "current_rss_mb": 600,
            "schema_version": 1,
        }
    }
    status = service.get_task_status("t1")
    assert status is not None
    model = FeatureTaskStatusResponse(**status)
    dumped = model.model_dump()
    assert dumped["process_rss_mb"] == 600
    assert dumped["schema_version"] == 1
    assert isinstance(dumped["schema_version"], int)


def test_parity_single_ws_process_rss_and_schema_version() -> None:
    """① 單 symbol WS notify payload（normalized）含 process_rss_mb + schema_version。"""
    from api.utils.ff_progress import normalize_progress_event

    ws_payload = normalize_progress_event(
        stage="layer_2",
        progress=0.3,
        message="go",
        process_rss_mb=700,
    )
    assert ws_payload["process_rss_mb"] == 700
    assert ws_payload["schema_version"] == 1
    assert ws_payload["current_rss_mb"] == 700


def test_parity_batch_rest_worker_rss_and_schema_version(batch_service_factory, tmp_path) -> None:
    """② 批次 REST 帶 worker_rss_mb + schema_version。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-parity-rest"
    layer_path = service._layer_metrics_path(task_id)
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    layer_path.write_text(
        json.dumps(
            {
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "stage": "layer_4",
                "progress": 0.6,
                "worker_rss_mb": 880,
                "current_rss_mb": 880,
                "schema_version": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
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
    status = service.get_status(task_id)
    assert status is not None
    model = BatchTaskStatusResponse(**status)
    dumped = model.model_dump()
    assert dumped["worker_rss_mb"] == 880
    assert dumped["schema_version"] == 1


def test_parity_batch_ws_worker_rss_and_schema_version() -> None:
    """② 批次 WS mapper 帶 worker_rss_mb + schema_version。"""
    payload = {
        "task_id": "batch-ws",
        "total": 2,
        "completed": 1,
        "failed": 0,
        "worker_rss_mb": 900,
        "current_rss_mb": 900,
        "schema_version": 1,
        "current_stage": "layer_3",
        "stage_progress": 0.4,
        "progress": 0.5,
        "status": "running",
    }
    mapped = map_batch_progress_ws_data(payload)
    assert mapped["worker_rss_mb"] == 900
    assert mapped["schema_version"] == 1


def test_parity_legacy_current_rss_mb_dual_write_both_paths() -> None:
    """③ legacy current_rss_mb 兩路徑仍存在（雙寫）。"""
    from api.utils.ff_progress import normalize_progress_event

    single = normalize_progress_event(stage="layer_0", progress=0.1, process_rss_mb=111)
    batch = normalize_progress_event(stage="layer_0", progress=0.1, worker_rss_mb=222)
    assert single["current_rss_mb"] == 111
    assert batch["current_rss_mb"] == 222


def test_parity_process_xor_worker_exclusive() -> None:
    """④ process_rss_mb XOR worker_rss_mb（同 event 互斥）。"""
    from api.utils.ff_progress import normalize_progress_event

    single = normalize_progress_event(stage="layer_1", progress=0.2, process_rss_mb=50)
    batch = normalize_progress_event(stage="layer_1", progress=0.2, worker_rss_mb=60)
    assert "process_rss_mb" in single and "worker_rss_mb" not in single
    assert "worker_rss_mb" in batch and "process_rss_mb" not in batch


def test_parity_concurrent_gt_one_no_fake_stage(batch_service_factory, tmp_path) -> None:
    """⑤ concurrent>1 不輸出假單一 current_stage。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-parity-coarse"
    layer_path = service._layer_metrics_path(task_id)
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    layer_path.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "stage": "layer_9",
                "progress": 0.9,
                "worker_rss_mb": 400,
                "current_rss_mb": 400,
                "schema_version": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    service._tasks[task_id] = {
        "task_id": task_id,
        "status": "running",
        "total": 2,
        "completed": 0,
        "failed": 0,
        "results": {},
        "errors": {},
        "concurrent_symbols": 2,
        "current_symbol": "BTCUSDT",
        "current_timeframe": "1h",
    }
    status = service.get_status(task_id)
    assert status is not None
    assert status.get("current_stage") is None
    assert status.get("worker_rss_mb") is None
    assert status.get("current_rss_mb") is None
