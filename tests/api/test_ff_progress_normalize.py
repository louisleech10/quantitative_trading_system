"""B2a: normalize_progress_event unit tests."""

from __future__ import annotations

import pytest

from api.utils.ff_progress import (
    ProgressErrorClass,
    legacy_absent_schema_version,
    normalize_progress_event,
)


def test_normalize_single_process_rss_dual_writes_legacy() -> None:
    event = normalize_progress_event(
        stage="layer_1",
        progress=0.5,
        message="half",
        process_rss_mb=420,
        schema_version=1,
    )
    assert event["process_rss_mb"] == 420
    assert event.get("worker_rss_mb") is None
    assert event["current_rss_mb"] == 420
    assert event["schema_version"] == 1
    assert event["error_class"] == ProgressErrorClass.NONE.value


def test_normalize_batch_worker_rss_dual_writes_legacy() -> None:
    event = normalize_progress_event(
        stage="layer_3",
        progress=0.25,
        worker_rss_mb=512,
        symbol="BTCUSDT",
        timeframe="1h",
        schema_version=1,
    )
    assert event["worker_rss_mb"] == 512
    assert event.get("process_rss_mb") is None
    assert event["current_rss_mb"] == 512
    assert event["schema_version"] == 1


def test_normalize_process_xor_worker_mutually_exclusive() -> None:
    event = normalize_progress_event(
        stage="layer_0",
        progress=0.0,
        process_rss_mb=100,
        worker_rss_mb=200,
    )
    assert event["process_rss_mb"] == 100
    assert event.get("worker_rss_mb") is None
    assert event["current_rss_mb"] == 100
    assert event["error_class"] == ProgressErrorClass.BOTH_RSS_FIELDS.value


def test_normalize_legacy_jsonl_rss_mb_alias() -> None:
    event = normalize_progress_event(
        stage="layer_2",
        progress=1.0,
        rss_mb=333,
    )
    assert event["worker_rss_mb"] == 333
    assert event["current_rss_mb"] == 333
    assert event["schema_version"] == 0


def test_normalize_invalid_stage_fail_open() -> None:
    event = normalize_progress_event(stage="not_a_real_stage", progress=0.1)
    assert event["stage"] == "not_a_real_stage"
    assert event["error_class"] == ProgressErrorClass.INVALID_STAGE.value


def test_normalize_missing_rss_fields_none() -> None:
    event = normalize_progress_event(stage="complete", progress=1.0, schema_version=1)
    assert "process_rss_mb" not in event
    assert "worker_rss_mb" not in event
    assert "current_rss_mb" not in event
    assert event["schema_version"] == 1


def test_normalize_legacy_absent_schema_version_defaults_zero() -> None:
    event = normalize_progress_event(stage="layer_0", progress=0.1)
    assert event["schema_version"] == 0


def test_legacy_absent_schema_version_is_zero() -> None:
    assert legacy_absent_schema_version({}) == 0
    assert legacy_absent_schema_version({"schema_version": 1}) == 1


def test_normalize_same_input_stable_output() -> None:
    fields = dict(stage="layer_6_5", progress=0.75, worker_rss_mb=1024, message="x")
    first = normalize_progress_event(**fields)
    second = normalize_progress_event(**fields)
    assert first == second
