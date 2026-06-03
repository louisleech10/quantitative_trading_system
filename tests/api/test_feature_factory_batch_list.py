"""批次發現 — list_recoverable_batches 與 GET /batch/list。"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app


def _write_checkpoint(
    checkpoint_dir,
    batch_id: str,
    *,
    completed_items: list,
    timeframe: str = "1h",
    last_updated_at: str,
) -> None:
    payload = {
        "batch_id": batch_id,
        "request_payload": {"timeframe": timeframe, "symbols": ["BTCUSDT"]},
        "completed_items": completed_items,
        "failed_items": [],
        "last_updated_at": last_updated_at,
    }
    path = checkpoint_dir / f"batch_state_{batch_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_list_recoverable_batches_excludes_empty_and_sorts_newest_first(
    tmp_path,
    batch_service_factory,
):
    service = batch_service_factory(tmp_path)

    _write_checkpoint(
        tmp_path,
        "batch-old",
        completed_items=[{"symbol": "BTCUSDT", "timeframe": "1h", "output_paths": ["/a"]}],
        timeframe="1h",
        last_updated_at="2026-06-01T10:00:00",
    )
    _write_checkpoint(
        tmp_path,
        "batch-new",
        completed_items=[
            {"symbol": "ETHUSDT", "timeframe": "4h", "output_paths": ["/b"]},
            {"symbol": "DOGEUSDT", "timeframe": "4h", "output_paths": ["/c"]},
        ],
        timeframe="4h",
        last_updated_at="2026-06-03T12:00:00",
    )
    _write_checkpoint(
        tmp_path,
        "batch-empty",
        completed_items=[],
        last_updated_at="2026-06-03T13:00:00",
    )
    (tmp_path / "batch_state_corrupt.json").write_text("{not json", encoding="utf-8")

    batches = service.list_recoverable_batches()

    assert len(batches) == 2
    assert batches[0]["batch_id"] == "batch-new"
    assert batches[1]["batch_id"] == "batch-old"
    assert batches[0]["symbols"] == ["ETHUSDT", "DOGEUSDT"]
    assert batches[0]["timeframe"] == "4h"
    assert batches[0]["completed_count"] == 2
    assert batches[1]["completed_count"] == 1


def test_list_recoverable_batches_returns_empty_when_no_checkpoints(
    tmp_path,
    batch_service_factory,
):
    service = batch_service_factory(tmp_path)
    assert service.list_recoverable_batches() == []


def test_get_batch_list_route_returns_recoverable_batches(
    tmp_path,
    batch_service_factory,
):
    from api.routes.feature_factory import get_batch_service

    service = batch_service_factory(tmp_path)
    _write_checkpoint(
        tmp_path,
        "route-batch-1",
        completed_items=[{"symbol": "BTCUSDT", "timeframe": "1h", "output_paths": ["/x"]}],
        last_updated_at="2026-06-02T08:00:00",
    )
    app.dependency_overrides[get_batch_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/features/batch/list")
        assert response.status_code == 200
        body = response.json()
        assert len(body["batches"]) == 1
        assert body["batches"][0]["batch_id"] == "route-batch-1"
    finally:
        app.dependency_overrides.pop(get_batch_service, None)
