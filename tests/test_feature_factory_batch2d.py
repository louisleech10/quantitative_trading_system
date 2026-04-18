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


def test_task211_materialize_wide_df_prefers_parquet(tmp_path: Path):
    """Task 2.11: materialize_wide_df 應優先從 parquet 重組 wide DataFrame。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")

    group_adx = _make_group(
        group_id="1h_L1_trend_ADX",
        layer=LayerSource.L1,
        timeframe="1h",
        columns=("close_1h_trend_ADX_14",),
        indicator="ADX",
    )
    group_ratio = _make_group(
        group_id="12h_L2_Ratio",
        layer=LayerSource.L2,
        timeframe="12h",
        columns=("close_12h_momentum_RSI_5_ratio",),
        indicator="Ratio",
    )

    saved_adx = registry.save_data(group_adx, np.array([[10.0], [20.0], [30.0]], dtype=np.float32))
    saved_ratio = registry.save_data(group_ratio, np.array([[1.0], [2.0], [3.0]], dtype=np.float32))

    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir(parents=True, exist_ok=True)

    parquet_adx = parquet_dir / "1h_L1_trend_ADX.parquet"
    parquet_ratio = parquet_dir / "12h_L2_Ratio.parquet"

    pd.DataFrame({"close_1h_trend_ADX_14": [100.0, 200.0, 300.0]}).to_parquet(parquet_adx, index=False)
    pd.DataFrame({"close_12h_momentum_RSI_5_ratio": [7.0, 8.0, 9.0]}).to_parquet(parquet_ratio, index=False)

    registry.set_group_parquet_paths(
        {
            saved_adx.group_id: str(parquet_adx.resolve()),
            saved_ratio.group_id: str(parquet_ratio.resolve()),
        },
        write_manifest=False,
    )

    # 強制驗證 materialize 走 parquet 路徑，而不是 fallback npy。
    if saved_adx.disk_path is not None:
        saved_adx.disk_path.unlink()
    if saved_ratio.disk_path is not None:
        saved_ratio.disk_path.unlink()

    wide_df = registry.materialize_wide_df()

    assert wide_df.columns.tolist() == registry.all_column_names()
    np.testing.assert_allclose(
        wide_df["close_1h_trend_ADX_14"].to_numpy(dtype=np.float64),
        np.array([100.0, 200.0, 300.0], dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )
    np.testing.assert_allclose(
        wide_df["close_12h_momentum_RSI_5_ratio"].to_numpy(dtype=np.float64),
        np.array([7.0, 8.0, 9.0], dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )


def test_task210_layer7_cgsa_per_group_validate_without_materialize(tmp_path: Path, monkeypatch):
    """Task 2.10: CGSA Layer 7 應做 per-group validate，且不在 validate 階段 materialize。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

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

    # 若被呼叫代表違反 Task 2.10（validate 階段不應 materialize）。
    monkeypatch.setattr(
        registry,
        "materialize_wide_df",
        lambda: (_ for _ in ()).throw(AssertionError("materialize_wide_df should not be called")),
    )

    persist_called = {"value": False}

    def _fake_persist_registry_to_parquet(*args, **kwargs):
        del args, kwargs
        persist_called["value"] = True
        return []

    monkeypatch.setattr(factory._storage, "persist_registry_to_parquet", _fake_persist_registry_to_parquet)

    raw_data = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
    result = factory._layer7_validate_and_persist(
        symbol="ETHUSDT",
        timeframe="1h",
        raw_data=raw_data,
        layers=[],
        config=_DummyConfig(),
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
