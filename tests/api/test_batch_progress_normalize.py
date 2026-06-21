"""B2b: batch progress via normalize_progress_event."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from api.services.feature_factory_batch_service import FeatureFactoryBatchService


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def test_compute_single_writes_normalized_layer_metrics_jsonl(tmp_path, monkeypatch) -> None:
    """jsonl row 為 normalized event（worker_rss_mb + legacy 雙寫）。"""
    layer_metrics_path = tmp_path / "layer_metrics.jsonl"
    monkeypatch.setenv("FFACT_LAYER_METRICS_PATH", str(layer_metrics_path))

    def fake_generate(**kwargs):
        cb = kwargs.get("progress_callback")
        assert cb is not None
        cb({"stage": "layer_0", "progress": 0.5, "message": "half"})
        result = MagicMock()
        result.hdf5_path = str(tmp_path / "BTCUSDT_1h.h5")
        return result

    factory_mock = MagicMock()
    factory_mock.generate_features.side_effect = fake_generate

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        FeatureFactoryBatchService._compute_single("BTCUSDT", "1h", None, True, str(tmp_path))

    rows = _read_jsonl(layer_metrics_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == 1
    assert row["worker_rss_mb"] >= 0
    assert row["current_rss_mb"] == row["worker_rss_mb"]
    assert "process_rss_mb" not in row or row.get("process_rss_mb") is None


def test_apply_layer_metrics_reads_legacy_rss_mb_jsonl(batch_service_factory, tmp_path) -> None:
    """舊 jsonl rss_mb 仍可經 normalize 映射為 worker_rss_mb + legacy。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-legacy-rss"
    layer_path = service._layer_metrics_path(task_id)
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    with layer_path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "stage": "layer_1",
                    "progress": 0.5,
                    "rss_mb": 199,
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
    assert task["worker_rss_mb"] == 199
    assert task["current_rss_mb"] == 199
    assert task["schema_version"] == 1


def test_apply_layer_metrics_concurrent_gt_one_coarse(batch_service_factory, tmp_path) -> None:
    """concurrent>1 不輸出假單一 current_stage / RSS。"""
    service = batch_service_factory(tmp_path)
    task_id = "batch-coarse"
    task = {
        "task_id": task_id,
        "concurrent_symbols": 2,
        "current_symbol": "BTCUSDT",
        "current_timeframe": "1h",
        "current_stage": "layer_1",
        "stage_progress": 0.5,
        "worker_rss_mb": 128,
        "current_rss_mb": 128,
    }
    service._apply_layer_metrics_to_task(task, task_id)
    assert "current_stage" not in task
    assert "worker_rss_mb" not in task
    assert "current_rss_mb" not in task
