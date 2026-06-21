"""B2b: single-symbol progress RSS via normalize."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from api.models.feature_factory_models import FeatureGenerateRequest
from api.services.feature_factory_service import FeatureFactoryService
from momentum.FeatureEngineering.config_manager import ConfigManager


def _build_single_service(captured: Dict[str, List[Any]]) -> FeatureFactoryService:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = MagicMock()
    service._callbacks = {}
    service._config_manager = ConfigManager()
    service._tasks = {
        "task-single": {
            "task_id": "task-single",
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "completed_stages": [],
            "error": None,
            "result": None,
        }
    }

    def fake_generate(**kwargs):
        cb = kwargs.get("progress_callback")
        assert cb is not None
        captured.setdefault("callbacks", []).append(cb)
        cb({"stage": "layer_1", "progress": 0.5, "message": "half"})
        from momentum.core.contracts import FeatureGenerationResult

        return FeatureGenerationResult(
            features_df=None,
            labels_df=None,
            metadata={"quality_status": "complete", "symbol": "BTCUSDT", "timeframe": "1h", "config_hash": "abc"},
            feature_count=0,
            generation_time=0.0,
            layer_counts={},
            config_used={},
            hdf5_path="/tmp/fake.h5",
        )

    service._generate_features_with_phase_d = fake_generate  # type: ignore[method-assign]
    service._invoke_generation_with_lease_sink = lambda **kwargs: fake_generate(**kwargs)  # type: ignore[method-assign]
    service._summarize_result = lambda result: {"metadata": result.metadata, "hdf5_path": result.hdf5_path}  # type: ignore[method-assign]
    service._persist_task_record = lambda *args, **kwargs: None  # type: ignore[method-assign]

    def capture_notify(task_id: str, payload: Dict[str, Any]) -> None:
        captured.setdefault("notify", []).append(payload)

    service._notify_callbacks = capture_notify  # type: ignore[method-assign]
    service._start_stats_cache_warmup = lambda *args, **kwargs: None  # type: ignore[method-assign]
    service._start_cgsa_catalog_warmup = lambda *args, **kwargs: None  # type: ignore[method-assign]
    service._start_data_quality_warmup = lambda *args, **kwargs: None  # type: ignore[method-assign]
    return service


@pytest.mark.asyncio
async def test_single_progress_callback_includes_process_rss_and_schema_version() -> None:
    captured: Dict[str, List[Any]] = {}
    service = _build_single_service(captured)
    request = FeatureGenerateRequest(symbol="BTCUSDT", timeframe="1h")

    with patch("api.services.feature_factory_service.psutil.Process") as proc_mock:
        proc_mock.return_value.memory_info.return_value.rss = 512 * 1024 * 1024
        await service._run_task("task-single", request)

    progress_notifies = [n for n in captured["notify"] if n.get("stage") == "layer_1"]
    assert progress_notifies, captured["notify"]
    notify = progress_notifies[0]
    assert notify["process_rss_mb"] == 512
    assert notify.get("worker_rss_mb") is None
    assert notify["current_rss_mb"] == 512
    assert notify["schema_version"] == 1

    status = service.get_task_status("task-single")
    assert status is not None
    assert status["process_rss_mb"] == 512
    assert status["current_rss_mb"] == 512
    assert status["schema_version"] == 1


@pytest.mark.asyncio
async def test_single_progress_psutil_fail_open() -> None:
    captured: Dict[str, List[Any]] = {}
    service = _build_single_service(captured)
    request = FeatureGenerateRequest(symbol="BTCUSDT", timeframe="1h")

    with patch("api.services.feature_factory_service.psutil.Process", side_effect=OSError("no psutil")):
        await service._run_task("task-single", request)

    progress_notifies = [n for n in captured["notify"] if n.get("stage") == "layer_1"]
    assert progress_notifies
    notify = progress_notifies[0]
    assert "process_rss_mb" not in notify or notify.get("process_rss_mb") is None
    assert notify["stage"] == "layer_1"
