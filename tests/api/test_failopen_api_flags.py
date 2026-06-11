"""Batch5 round2: API fail_open flag wiring end-to-end."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from api.models.feature_factory_models import FailOpenGateFlags, FeatureGenerateRequest
from api.services.feature_factory_service import FeatureFactoryService
from momentum.FeatureEngineering.config_manager import ConfigManager


def test_merge_fail_open_flags_into_config_override() -> None:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    flags = FailOpenGateFlags(allow_partial_layers=True, allow_partial_ic=True)
    merged = service._merge_fail_open_flags({"preset": "default"}, flags)
    assert merged is not None
    assert merged["allow_partial_layers"] is True
    assert merged["allow_partial_ic"] is True
    assert merged["preset"] == "default"


def test_resolve_config_override_includes_fail_open_flags() -> None:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._config_manager = ConfigManager()
    flags = FailOpenGateFlags(allow_partial_training=True)
    merged = service._merge_fail_open_flags(None, flags)
    resolved = service._resolve_config_override(merged)
    assert resolved is not None
    assert resolved["allow_partial_training"] is True


def _build_task_service(captured: dict[str, object]) -> FeatureFactoryService:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = MagicMock()
    service._callbacks = {}
    service._config_manager = ConfigManager()

    def fake_generate(
        task_id,
        symbol,
        timeframe,
        config_override,
        force_regenerate,
        progress_callback,
        start_date=None,
        end_date=None,
    ):
        captured["config_override"] = config_override
        from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult

        return FeatureGenerationResult(
            features_df=None,
            labels_df=None,
            metadata={"quality_status": "complete"},
            feature_count=0,
            generation_time=0.0,
            layer_counts={},
            config_used={},
            hdf5_path="/tmp/fake.h5",
        )

    service._generate_features_with_phase_d = fake_generate  # type: ignore[method-assign]
    service._summarize_result = lambda result: {"metadata": result.metadata, "hdf5_path": result.hdf5_path}  # type: ignore[method-assign]
    service._persist_task_record = lambda *args, **kwargs: None  # type: ignore[method-assign]
    service._notify_callbacks = lambda *args, **kwargs: None  # type: ignore[method-assign]
    service._start_stats_cache_warmup = lambda *args, **kwargs: None  # type: ignore[method-assign]
    service._start_cgsa_catalog_warmup = lambda *args, **kwargs: None  # type: ignore[method-assign]
    service._start_data_quality_warmup = lambda *args, **kwargs: None  # type: ignore[method-assign]
    return service


@pytest.mark.asyncio
async def test_start_generation_passes_fail_open_to_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    service = _build_task_service(captured)
    service._tasks = {"task-1": {"status": "running", "completed_stages": []}}

    loop = asyncio.get_running_loop()

    async def immediate_executor(_executor, func):
        return func()

    monkeypatch.setattr(loop, "run_in_executor", immediate_executor)

    request = FeatureGenerateRequest(
        symbol="BTCUSDT",
        timeframe="1h",
        fail_open=FailOpenGateFlags(allow_partial_layers=True),
    )

    await service._run_task("task-1", request)

    override = captured.get("config_override")
    assert isinstance(override, dict)
    assert override.get("allow_partial_layers") is True


@pytest.mark.asyncio
async def test_start_generation_without_fail_open_keeps_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    service = _build_task_service(captured)
    service._tasks = {"task-2": {"status": "running", "completed_stages": []}}

    loop = asyncio.get_running_loop()

    async def immediate_executor(_executor, func):
        return func()

    monkeypatch.setattr(loop, "run_in_executor", immediate_executor)

    request = FeatureGenerateRequest(symbol="BTCUSDT", timeframe="1h")
    await service._run_task("task-2", request)

    override = captured.get("config_override")
    assert override is None or override.get("allow_partial_layers") in (None, False)
