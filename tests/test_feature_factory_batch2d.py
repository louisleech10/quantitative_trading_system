"""Batch 2d tests for Task 2.9~2.11."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict
from unittest.mock import Mock

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import FeatureFactory


class _DummyLabelsConfig:
    def model_dump(self) -> Dict[str, Dict[str, object]]:
        return {
            "binary": {"horizons": [1], "threshold": 0.0},
            "regression": {"horizons": [1]},
        }


class _DummyConfig:
    def __init__(self) -> None:
        self.labels = _DummyLabelsConfig()

    def model_dump(self, by_alias: bool = True) -> Dict[str, object]:
        del by_alias
        return {
            "labels": self.labels.model_dump(),
            "timeframes": {"training": ["1h", "12h"]},
            "operators": {"enabled": True},
        }


def _make_group(
    group_id: str,
    layer: LayerSource,
    timeframe: str,
    columns: tuple[str, ...],
    indicator: str,
) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=layer,
        timeframe=timeframe,
        data_source="close",
        indicator=indicator,
        columns=columns,
        shape=(0, 0),
        dtype="float32",
        disk_path=None,
    )


def test_t214_manifest_contains_required_fields(tmp_path: Path):
    """T2.14: manifest.json 應包含 Batch 2d 規範要求欄位。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")

    group_a = _make_group(
        group_id="1h_L1_trend_ADX",
        layer=LayerSource.L1,
        timeframe="1h",
        columns=("close_1h_trend_ADX_14",),
        indicator="ADX",
    )
    group_b = _make_group(
        group_id="12h_L2_Ratio",
        layer=LayerSource.L2,
        timeframe="12h",
        columns=("close_12h_momentum_RSI_5_ratio",),
        indicator="Ratio",
    )

    registry.save_data(group_a, np.array([[1.0], [2.0], [3.0]], dtype=np.float32))
    registry.save_data(group_b, np.array([[4.0], [5.0], [6.0]], dtype=np.float32))

    config_snapshot = {"b": {"x": 1}, "a": [1, 2], "n_jobs": 8}
    config_hash = ColumnGroupRegistry.compute_config_hash(config_snapshot)
    registry.save_state(
        symbol="ETHUSDT",
        primary_tf="1h",
        training_tfs=["1h", "12h"],
        config_hash=config_hash,
        config_snapshot=config_snapshot,
    )

    manifest = json.loads(registry.manifest_path.read_text(encoding="utf-8"))

    assert manifest["symbol"] == "ETHUSDT"
    assert manifest["primary_tf"] == "1h"
    assert manifest["training_tfs"] == ["1h", "12h"]
    assert manifest["config_hash"] == config_hash
    assert manifest["total_features"] == 2
    assert manifest["total_groups"] == 2
    assert isinstance(manifest["groups"], list)
    assert len(manifest["groups"]) == 2
    assert "created_at" in manifest

    group_ids = [item["group_id"] for item in manifest["groups"]]
    assert group_ids == sorted(group_ids)


def test_task210_layer7_cgsa_per_group_validate_without_materialize(tmp_path: Path, monkeypatch):
    """Task 2.10（FRAMEPATH：改走唯一 CGSA L7 入口 `_layer7_raw_from_cgsa_pipeline`）：per-group validate，且不在 validate 階段 materialize、persist=False 不落盤（V1 版面寫入 persist_registry_to_parquet 已刪，落盤探針改掛 V2 串流寫入）。"""
    from types import SimpleNamespace

    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    factory._cgsa_registry = registry

    group_nan = _make_group(
        group_id="1h_L3_nan_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_mean",),
        indicator="EMA",
    )
    group_inf = _make_group(
        group_id="1h_L3_inf_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_std",),
        indicator="EMA",
    )

    registry.save_data(group_nan, np.array([[np.nan], [np.nan], [np.nan]], dtype=np.float32))
    registry.save_data(group_inf, np.array([[1.0], [np.inf], [2.0]], dtype=np.float32))

    # Task 2.10（validate 階段不應 materialize）：寬表組裝已於 FFPROD Task 1.1 刪除（生產無呼叫者），結構上不可呼叫。

    persist_called = {"value": False}

    def _fake_write_raw_from_registry_stream(*args, **kwargs):
        del args, kwargs
        persist_called["value"] = True
        raise AssertionError("persist=False 不得呼叫 write_raw_from_registry_stream")

    monkeypatch.setattr(factory._storage, "write_raw_from_registry_stream", _fake_write_raw_from_registry_stream)

    config = _DummyConfig()
    config.preprocessing = SimpleNamespace(enabled=False)
    raw_data = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
    result = factory._layer7_raw_from_cgsa_pipeline(
        symbol="ETHUSDT",
        timeframe="1h",
        raw_data=raw_data,
        config=config,
        elapsed=1.23,
        config_hash="cfg_batch2d",
        compute_warnings=["pre-existing warning"],
        persist=False,
    )

    assert persist_called["value"] is False
    assert result.features_df.empty
    assert result.feature_count == registry.total_columns()
    assert result.hdf5_path == ""

    validation = result.metadata["validation"]
    assert validation["has_inf"] is True
    assert validation["has_nan"] is True
    assert any("NaN ratio" in warning for warning in validation["warnings"])
    assert Path(result.metadata["manifest_path"]).exists()
