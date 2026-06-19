"""Batch layer_metrics.jsonl observability tests (T2 Task 1.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from api.services.feature_factory_batch_service import FeatureFactoryBatchService


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def test_compute_single_writes_layer_metrics_jsonl(tmp_path, monkeypatch) -> None:
    """progress_callback 觸發時寫入 layer_metrics.jsonl，rss_mb 存在且非負。"""
    layer_metrics_path = tmp_path / "layer_metrics.jsonl"
    monkeypatch.setenv("FFACT_LAYER_METRICS_PATH", str(layer_metrics_path))

    stages = [
        ("layer_0", 0.0, "Starting layer_0..."),
        ("layer_0", 1.0, "layer_0 completed"),
        ("layer_1", 0.0, "Starting layer_1..."),
        ("layer_1", 1.0, "layer_1 completed"),
    ]

    def fake_generate(**kwargs):
        cb = kwargs.get("progress_callback")
        assert cb is not None
        for stage, progress, message in stages:
            cb({"stage": stage, "progress": progress, "message": message})
        result = MagicMock()
        result.hdf5_path = str(tmp_path / "BTCUSDT_1h.h5")
        return result

    factory_mock = MagicMock()
    factory_mock.generate_features.side_effect = fake_generate

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        path = FeatureFactoryBatchService._compute_single(
            "BTCUSDT",
            "1h",
            None,
            True,
            str(tmp_path),
        )

    assert path.endswith("BTCUSDT_1h.h5")
    rows = _read_jsonl(layer_metrics_path)
    assert len(rows) == len(stages)
    assert len(rows) <= 200
    rss_values = []
    for row in rows:
        assert row["symbol"] == "BTCUSDT"
        assert row["timeframe"] == "1h"
        assert row["schema_version"] == 1
        assert "stage" in row
        assert "progress" in row
        assert "elapsed" in row
        rss = row["rss_mb"]
        assert isinstance(rss, int)
        assert rss >= 0
        assert rss < 65536
        rss_values.append(rss)
    assert len(set(rss_values)) >= 1


def test_compute_single_layer_metrics_failopen_on_write_error(tmp_path, monkeypatch) -> None:
    """寫檔失敗時 generate_features 仍完成 (fail-open)。"""
    monkeypatch.setenv("FFACT_LAYER_METRICS_PATH", str(tmp_path / "layer_metrics.jsonl"))

    def fake_generate(**kwargs):
        cb = kwargs.get("progress_callback")
        if cb:
            cb({"stage": "layer_0", "progress": 0.0, "message": "start"})
            cb({"stage": "layer_0", "progress": 1.0, "message": "done"})
        result = MagicMock()
        result.hdf5_path = str(tmp_path / "out.h5")
        return result

    factory_mock = MagicMock()
    factory_mock.generate_features.side_effect = fake_generate

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        with patch.object(
            FeatureFactoryBatchService,
            "_append_child_metrics_jsonl",
            side_effect=OSError("disk full"),
        ):
            path = FeatureFactoryBatchService._compute_single("BTCUSDT", "1h", None, True, str(tmp_path))

    assert path.endswith("out.h5")


def test_compute_single_cache_hit_no_layer_events(tmp_path, monkeypatch) -> None:
    """cache-hit 路徑不強制 layer 事件，jsonl 可空。"""
    layer_metrics_path = tmp_path / "layer_metrics.jsonl"
    monkeypatch.setenv("FFACT_LAYER_METRICS_PATH", str(layer_metrics_path))

    result_mock = MagicMock()
    result_mock.hdf5_path = str(tmp_path / "cached.h5")
    factory_mock = MagicMock()
    factory_mock.generate_features.return_value = result_mock

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        path = FeatureFactoryBatchService._compute_single(
            "BTCUSDT",
            "1h",
            None,
            False,
            str(tmp_path),
        )

    assert path.endswith("cached.h5")
    assert _read_jsonl(layer_metrics_path) == []
    factory_mock.generate_features.assert_called_once()
    assert factory_mock.generate_features.call_args.kwargs.get("progress_callback") is not None
