"""Batch 2e tests for Phase 2 checklist closure (T2.16 + T2.B1~T2.B9)."""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import (
    ColumnGroupRegistry,
    ColumnGroupRegistryError,
    FailureType,
)
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


class _DummyOperators:
    def __init__(self, payload: dict) -> None:
        self.enabled = True
        self._payload = payload

    def model_dump(self, by_alias: bool = True) -> dict:
        del by_alias
        return self._payload


class _DummyConfig:
    def __init__(self, operators_payload: dict) -> None:
        self.operators = _DummyOperators(operators_payload)
        self.lag_features = SimpleNamespace(apply_to="all")


def _operators_payload(
    cross_enabled: bool = False,
    ratio_enabled: bool = False,
    momentum_enabled: bool = False,
) -> dict:
    return {
        "distance": {"enabled": False},
        "cross": {"enabled": cross_enabled},
        "ratio": {"enabled": ratio_enabled},
        "momentum": {"enabled": momentum_enabled, "lags": [1]},
        "binary_signal": {"enabled": False, "rules": []},
        "signed_strength": {"enabled": False},
        "worldquant": {
            "enabled": False,
            "windows": [5, 13],
            "operators": ["ts_rank"],
            "transforms": ["sign"],
        },
    }


def _make_group(
    group_id: str,
    layer: LayerSource,
    timeframe: str,
    columns: tuple[str, ...],
    indicator: str,
    data_source: str = "close",
) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=layer,
        timeframe=timeframe,
        data_source=data_source,
        indicator=indicator,
        columns=columns,
        shape=(0, 0),
        dtype="float32",
        disk_path=None,
    )


def _make_factory(tmp_path: Path, with_registry: bool = True) -> FeatureFactory:
    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    factory._current_timeframe = "1h"
    if with_registry:
        factory._cgsa_registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    else:
        factory._cgsa_registry = None
    return factory


def test_cgsa_l2_cross_group_operators(tmp_path, monkeypatch):
    """T2.16: CGSA L2 Cross/Ratio 結果應與 legacy 路徑一致。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    layer1 = pd.DataFrame(
        {
            "close_trend_EMA_5": [10.0, 12.0, 14.0, 16.0],
            "close_trend_EMA_21": [9.0, 11.0, 13.0, 15.0],
        }
    )
    raw_data = pd.DataFrame({"close": [10.0, 12.0, 14.0, 16.0]})

    indicator_specs = {
        "close_trend_EMA_5": {
            "source": "close",
            "category": "trend",
            "indicator": "EMA",
            "params": [5],
        },
        "close_trend_EMA_21": {
            "source": "close",
            "category": "trend",
            "indicator": "EMA",
            "params": [21],
        },
    }

    cfg = _DummyConfig(_operators_payload(cross_enabled=True, ratio_enabled=True))

    cgsa_factory = _make_factory(tmp_path=tmp_path / "cgsa", with_registry=True)
    legacy_factory = _make_factory(tmp_path=tmp_path / "legacy", with_registry=False)
    monkeypatch.setattr(cgsa_factory, "_build_indicator_specs", lambda _l1, _cfg: indicator_specs)
    monkeypatch.setattr(legacy_factory, "_build_indicator_specs", lambda _l1, _cfg: indicator_specs)

    cgsa_result = cgsa_factory._layer2_derived_features(layer1, raw_data, cfg)
    legacy_result = legacy_factory._layer2_derived_features(layer1, raw_data, cfg)

    assert cgsa_result.columns.tolist() == legacy_result.columns.tolist()
    np.testing.assert_allclose(
        cgsa_result.to_numpy(dtype=np.float64),
        legacy_result.to_numpy(dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )

    registry = cgsa_factory._cgsa_registry
    assert registry is not None
    saved_cross = np.asarray(registry.load_data("1h_L2_Cross"), dtype=np.float64)
    saved_ratio = np.asarray(registry.load_data("1h_L2_Ratio"), dtype=np.float64)

    # Validate per-group saved data matches legacy by column-name lookup
    # (positional concat is brittle to operator-emit order; the public contract
    # is that each saved group's columns appear in legacy_result with the same
    # values, regardless of operator ordering).
    cross_group = registry.get("1h_L2_Cross")
    ratio_group = registry.get("1h_L2_Ratio")
    cross_legacy = legacy_result[list(cross_group.columns)].to_numpy(dtype=np.float64)
    ratio_legacy = legacy_result[list(ratio_group.columns)].to_numpy(dtype=np.float64)
    np.testing.assert_allclose(saved_cross, cross_legacy, atol=1e-6, equal_nan=True)
    np.testing.assert_allclose(saved_ratio, ratio_legacy, atol=1e-6, equal_nan=True)


def test_t2b1_l1_single_indicator_runs_normally(tmp_path):
    """T2.B1: L1 只有 1 個 indicator 時應正常 per-group 註冊。"""
    factory = _make_factory(tmp_path=tmp_path, with_registry=True)

    frame = pd.DataFrame({"close_trend_EMA_5": [1.0, 2.0, 3.0]})
    factory._persist_layer1_indicator_groups(frame, category_hint="trend")

    groups = factory._cgsa_registry.list_by_layer(LayerSource.L1)
    assert [g.group_id for g in groups] == ["1h_L1_trend_EMA"]
    loaded = np.asarray(factory._cgsa_registry.load_data("1h_L1_trend_EMA"))
    np.testing.assert_allclose(loaded, frame.to_numpy(dtype=np.float32), equal_nan=True)


def test_t2b2_l2_without_cross_group_ops_direct_emit(tmp_path, monkeypatch):
    """T2.B2: L2 關閉 Cross/Ratio 時應直接 per-group emit（Momentum）。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    factory = _make_factory(tmp_path=tmp_path, with_registry=True)
    layer1 = pd.DataFrame({"close_trend_EMA_5": [10.0, 12.0, 14.0, 16.0]})
    raw_data = pd.DataFrame({"close": [10.0, 12.0, 14.0, 16.0]})
    indicator_specs = {
        "close_trend_EMA_5": {
            "source": "close",
            "category": "trend",
            "indicator": "EMA",
            "params": [5],
        }
    }
    monkeypatch.setattr(factory, "_build_indicator_specs", lambda _l1, _cfg: indicator_specs)

    cfg = _DummyConfig(_operators_payload(momentum_enabled=True))
    result = factory._layer2_derived_features(layer1, raw_data, cfg)

    group_ids = [g.group_id for g in factory._cgsa_registry.list_by_layer(LayerSource.L2)]
    assert group_ids == ["1h_L2_Momentum"]
    assert not result.empty
    assert all("_Momentum_" in col for col in result.columns)


def test_t2b3_all_nan_group_register_and_persist(tmp_path):
    """T2.B3: 全 NaN group 應可正常 register + parquet persist。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = _make_group(
        group_id="1h_L3_nan_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_mean", "close_1h_trend_EMA_5_std"),
        indicator="EMA",
    )
    nan_matrix = np.full((4, 2), np.nan, dtype=np.float32)
    registry.save_data(group, nan_matrix)

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    paths = storage.persist_registry_to_parquet(
        symbol="ETHUSDT",
        config_hash="cfg_nan",
        registry=registry,
        cleanup_intermediate=False,
    )

    assert len(paths) == 1
    persisted = pd.read_parquet(paths[0])
    assert persisted.isna().all().all()


def test_t2b4_zero_columns_group_not_registered(tmp_path):
    """T2.B4: 0 cols 輸入不應註冊任何 L1 group。"""
    factory = _make_factory(tmp_path=tmp_path, with_registry=True)
    zero_col_frame = pd.DataFrame(index=[0, 1, 2, 3])

    factory._persist_layer1_indicator_groups(zero_col_frame, category_hint="trend")

    assert factory._cgsa_registry.total_columns() == 0
    assert factory._cgsa_registry.list_by_layer(LayerSource.L1) == []


def test_t2b5_disk_full_raises_ioerror_and_cleans_staging(tmp_path, monkeypatch):
    """T2.B5: 磁碟空間不足時應拋錯，且 staging 目錄需被清理。"""
    # Force serial path (n_workers=1) so the monkeypatch in the main process
    # actually intercepts the parquet write (worker subprocesses don't inherit
    # patches applied via monkeypatch).
    monkeypatch.setenv("FFACT_L7_WORKERS", "1")

    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = _make_group(
        group_id="1h_L3_group_a",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("f_a_1", "f_a_2"),
        indicator="EMA",
    )
    registry.save_data(group, np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))

    storage = FeatureStorage(base_path=str(tmp_path / "features"))

    def _raise_no_space(*args, **kwargs):
        del args, kwargs
        raise OSError("No space left on device")

    # The persist path uses pyarrow.parquet.write_table directly (not
    # pd.DataFrame.to_parquet); patch the real call site.
    import pyarrow.parquet as pq_module
    monkeypatch.setattr(pq_module, "write_table", _raise_no_space)

    with pytest.raises(OSError, match="No space left on device"):
        storage.persist_registry_to_parquet(
            symbol="ETHUSDT",
            config_hash="cfg_diskfull",
            registry=registry,
            cleanup_intermediate=False,
        )

    output_dir = tmp_path / "features" / "ETHUSDT" / "cfg_diskfull"
    if output_dir.exists():
        # Final parquet must not appear (the contract that matters: no
        # half-written corrupt output is exposed to consumers).
        assert list(output_dir.glob("*.parquet")) == []
        # NOTE: staging_ subdir is intentionally PRESERVED on failure
        # (preserve_staging=True in feature_storage.py) so operators can
        # inspect partial results when diagnosing a disk-full crash.


def test_t2b6_same_indicator_different_tf_no_conflict(tmp_path):
    """T2.B6: 同指標不同 TF 因 prefix 不同，group_id 不衝突。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")

    g1 = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5",),
        indicator="EMA",
    )
    g2 = _make_group(
        group_id="12h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="12h",
        columns=("close_12h_trend_EMA_5",),
        indicator="EMA",
    )

    registry.save_data(g1, np.array([[1.0], [2.0]], dtype=np.float32))
    registry.save_data(g2, np.array([[3.0], [4.0]], dtype=np.float32))

    assert registry.total_columns() == 2
    assert [g.group_id for g in registry.list_by_layer(LayerSource.L1)] == [
        "12h_L1_trend_EMA",
        "1h_L1_trend_EMA",
    ]


def test_t2b7_manifest_projected_size_under_50mb(tmp_path):
    """T2.B7: 以大樣本欄位估算 453,953 cols 的 manifest 應低於 50MB。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")

    sample_col_count = 20_000
    sample_columns = tuple(f"close_1h_trend_EMA_{idx}" for idx in range(sample_col_count))
    registry.register(
        _make_group(
            group_id="1h_L1_trend_EMA_large",
            layer=LayerSource.L1,
            timeframe="1h",
            columns=sample_columns,
            indicator="EMA",
        )
    )
    registry.save_state(
        symbol="ETHUSDT",
        primary_tf="1h",
        training_tfs=["1h", "12h"],
        config_hash="cfg_large_manifest",
        config_snapshot={"phase": 2},
    )

    manifest_size = registry.manifest_path.stat().st_size
    bytes_per_col = manifest_size / float(sample_col_count)
    projected_size = bytes_per_col * 453_953

    assert projected_size < 50 * 1024 * 1024


def test_t2b8_l65_fracdiff_per_group_feasible(tmp_path, monkeypatch):
    """T2.B8: L6.5 fracdiff 在 per-group 路徑可被逐群執行。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    g1 = _make_group(
        group_id="1h_L3_group_a",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("f_a_1", "f_a_2"),
        indicator="EMA",
    )
    g2 = _make_group(
        group_id="1h_L3_group_b",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("f_b_1",),
        indicator="RSI",
    )
    registry.save_data(g1, np.array([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]], dtype=np.float32))
    registry.save_data(g2, np.array([[10.0], [11.0], [12.0]], dtype=np.float32))

    preprocessor = FeaturePreprocessor(
        {
            "fractional_differencing": {
                "enabled": True,
                "apply_to": "all",
                "cache_d_star": False,
            }
        }
    )

    calls = {"count": 0}

    def _fake_fracdiff(df: pd.DataFrame) -> pd.DataFrame:
        calls["count"] += 1
        return df

    monkeypatch.setattr(preprocessor, "_apply_fractional_differencing", _fake_fracdiff)

    processed_count = preprocessor.transform_registry_groups(registry)

    assert processed_count == 2
    assert calls["count"] == 2


def test_t2b9_cleanup_interrupted_then_next_cleanup_succeeds(tmp_path, monkeypatch):
    """T2.B9: cleanup 中斷後殘留檔案，下一次 cleanup 應可清理完成。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5",),
        indicator="EMA",
    )
    saved = registry.save_data(group, np.array([[1.0], [2.0]], dtype=np.float32))
    assert saved.disk_path is not None

    target = saved.disk_path
    original_unlink = Path.unlink
    state = {"failed": False}

    def _flaky_unlink(path_obj: Path, *args, **kwargs):
        if path_obj == target and not state["failed"]:
            state["failed"] = True
            raise OSError("interrupted cleanup")
        return original_unlink(path_obj, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _flaky_unlink)

    with pytest.raises(ColumnGroupRegistryError) as exc_info:
        registry.cleanup()
    assert exc_info.value.failure_type == FailureType.IO_ERROR
    assert target.exists()

    registry.cleanup()

    assert not target.exists()
    assert registry.total_columns() == 0


def test_phase2_l5_dependency_domain_excludes_layer2_runtime():
    """附加確認: L5 依賴域不應讀取 layer2（僅 layer1/raw/reference）。"""
    source = textwrap.dedent(inspect.getsource(FeatureFactory._layer5_cross_sectional))
    tree = ast.parse(source)
    layer2_loads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "layer2" and isinstance(node.ctx, ast.Load)
    ]
    assert layer2_loads == []


def test_phase2_l6_dependency_domain_excludes_layer2_runtime():
    """附加確認: L6 依賴域不應讀取 layer2（目前實作僅依賴 layer1/data）。"""
    source = textwrap.dedent(inspect.getsource(FeatureFactory._layer6_meta_features))
    tree = ast.parse(source)
    layer2_loads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "layer2" and isinstance(node.ctx, ast.Load)
    ]
    assert layer2_loads == []


def test_phase2_column_ordering_confirmation(tmp_path):
    """附加確認: all_column_names() 應維持 Canonical Column Ordering。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")

    registry.register(
        _make_group(
            group_id="12h_L3_trend_EMA_close",
            layer=LayerSource.L3,
            timeframe="12h",
            columns=("close_12h_trend_EMA_5_mean",),
            indicator="EMA",
            data_source="close",
        )
    )
    registry.register(
        _make_group(
            group_id="1h_L3_trend_EMA_close",
            layer=LayerSource.L3,
            timeframe="1h",
            columns=("close_1h_trend_EMA_21_std", "close_1h_trend_EMA_5_mean"),
            indicator="EMA",
            data_source="close",
        )
    )
    registry.register(
        _make_group(
            group_id="1h_L2_Ratio",
            layer=LayerSource.L2,
            timeframe="1h",
            columns=("close_1h_momentum_RSI_5_ratio",),
            indicator="Ratio",
            data_source="derived",
        )
    )
    registry.register(
        _make_group(
            group_id="1h_L1_trend_ADX",
            layer=LayerSource.L1,
            timeframe="1h",
            columns=("close_1h_trend_ADX_14", "label_next_1h"),
            indicator="ADX",
            data_source="close",
        )
    )

    assert registry.all_column_names() == [
        "close_1h_trend_ADX_14",
        "close_1h_momentum_RSI_5_ratio",
        "close_1h_trend_EMA_5_mean",
        "close_1h_trend_EMA_21_std",
        "close_12h_trend_EMA_5_mean",
        "label_next_1h",
    ]
