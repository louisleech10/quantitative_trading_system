"""T-C: CGSA L3 累積磁碟預檢（增量制，mirror L7 模型）。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import (
    ColumnGroupRegistry,
    ColumnGroupRegistryError,
)
from momentum.factories import create_feature_factory
from tests._helpers.stub_layer_execute import stub_execute_layer1_6, stub_layer_data, stub_spill_to_memmap


def _group(group_id: str, n_rows: int, n_cols: int, timeframe: str = "12h") -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L2,
        timeframe=timeframe,
        data_source="derived",
        indicator="mock",
        columns=tuple(f"{group_id}_c{i}" for i in range(n_cols)),
        shape=(n_rows, n_cols),
        dtype="float32",
    )


def _layer_df(n_rows: int, n_cols: int) -> pd.DataFrame:
    return pd.DataFrame(
        np.zeros((n_rows, n_cols), dtype=np.float32),
        columns=[f"c{i}" for i in range(n_cols)],
    )


def _needed_for_frame(
    registry: ColumnGroupRegistry,
    frame: pd.DataFrame,
    *,
    chunk_cols: int = 5000,
) -> int:
    planned, max_shard = registry._estimate_chunk_shard_planned_bytes(
        int(frame.shape[0]),
        int(frame.shape[1]),
        chunk_cols=chunk_cols,
    )
    reserve = registry._resolve_cgsa_disk_reserve_bytes()
    return int(planned) + int(max_shard) * 2 + reserve


# --- Unit tests (cgsa_disk_precheck) ---


def test_cgsa_disk_precheck_raises_when_free_below_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    monkeypatch.setenv("FFACT_CGSA_DISK_RESERVE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    frame = _layer_df(4096, 2048)
    needed = _needed_for_frame(registry, frame)
    monkeypatch.setattr(registry, "_disk_free_bytes", lambda _path: needed - 1)

    with pytest.raises(ColumnGroupRegistryError) as exc:
        registry._precheck_cgsa_cumulative_disk(
            frame,
            layer_label="L3_rolling",
            symbol="ETHUSDT",
            timeframe="12h",
        )
    msg = str(exc.value)
    assert "ETHUSDT" in msg
    assert "12h" in msg
    assert "L3_rolling" in msg
    assert "need" in msg.lower() or "Need" in msg
    assert "available" in msg.lower() or "GiB" in msg


def test_cgsa_disk_precheck_passes_when_free_equals_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    monkeypatch.setenv("FFACT_CGSA_DISK_RESERVE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    frame = _layer_df(2048, 1024)
    needed = _needed_for_frame(registry, frame)
    monkeypatch.setattr(registry, "_disk_free_bytes", lambda _path: needed)

    registry._precheck_cgsa_cumulative_disk(
        frame,
        layer_label="L3_rolling",
        symbol="BTCUSDT",
        timeframe="1h",
    )


def test_cgsa_disk_precheck_no_false_abort_with_large_registry_occupancy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """adv#1: registry 已大量佔用 + 本次增量小 + free 足夠增量 → 不 abort。"""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    monkeypatch.setenv("FFACT_CGSA_DISK_RESERVE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    # 佔滿 registry（真實寫入磁碟；free 已扣除這些檔案）。
    registry.save_data(
        _group("existing_big", 8192, 4096),
        np.zeros((8192, 4096), dtype=np.float32),
    )
    assert sum(s.nbytes for s in registry.get("existing_big").shards) > 32 * 1024 * 1024

    small_frame = _layer_df(128, 256)
    needed = _needed_for_frame(registry, small_frame)
    monkeypatch.setattr(registry, "_disk_free_bytes", lambda _path: needed + 4096)

    registry._precheck_cgsa_cumulative_disk(
        small_frame,
        layer_label="L3_rolling",
        symbol="ETHUSDT",
        timeframe="12h",
    )


def test_cgsa_disk_precheck_non_dataframe_returns_without_raise(
    tmp_path: Path,
) -> None:
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    registry._precheck_cgsa_cumulative_disk(
        {"not": "a dataframe"},
        layer_label="L3_rolling",
        symbol="ETHUSDT",
        timeframe="12h",
    )


def test_cgsa_disk_precheck_reserve_env_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FFACT_CGSA_DISK_RESERVE_GIB", raising=False)
    assert ColumnGroupRegistry._resolve_cgsa_disk_reserve_bytes() == int(2.0 * 1024 ** 3)


def test_cgsa_disk_precheck_env_disable_skips_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_CGSA_DISK_PRECHECK", "0")
    factory = create_feature_factory(validate_continuity=False)
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    factory._cgsa_registry = registry
    factory._current_symbol = "ETHUSDT"
    factory._current_timeframe = "12h"

    calls: list[int] = []

    def _spy_precheck(*args, **kwargs) -> None:
        del args, kwargs
        calls.append(1)

    monkeypatch.setattr(registry, "_precheck_cgsa_cumulative_disk", _spy_precheck)

    frame = _layer_df(128, 64)
    factory._persist_layer_output_groups(frame, LayerSource.L3, "L3_rolling")
    assert calls == []
    assert len(registry._groups) > 0


# --- Integration tests (cgsa_disk_precheck_integration) ---


class _MtFTimeframes:
    primary = "12h"
    training = ["12h", "1h"]
    alignment_mode = "open_minus"


class _MtFConfig:
    def __init__(self, *, allow_partial_timeframes: bool = True) -> None:
        self.timeframes = _MtFTimeframes()
        self.allow_partial_timeframes = allow_partial_timeframes
        self.preprocessing = SimpleNamespace(enabled=False)


class _CgsaIntegrationFactory:
    """最小 CGSA factory：真實 _persist_layer_output_groups + stub L1-L6。"""

    def __init__(self, data_by_tf: dict[str, pd.DataFrame], registry: ColumnGroupRegistry) -> None:
        self._data_by_tf = data_by_tf
        self._cgsa_registry = registry
        self._current_symbol: str | None = None
        self._current_timeframe: str | None = None
        self._real = create_feature_factory(validate_continuity=False)
        self._real._cgsa_registry = registry

    def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
        del symbol, config, start_date, end_date
        return self._data_by_tf[timeframe]

    def _execute_layer1_6(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    def _execute_layer1_6_preserve_dtype(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    _spill_to_memmap = staticmethod(stub_spill_to_memmap)
    layer_data = stub_layer_data

    def _layer1_atomic_indicators(self, data, config):
        del config
        tf = str(self._current_timeframe)
        return pd.DataFrame({f"x_{tf}": data["value"].values}, index=data["timestamp"])

    def _layer2_derived_features(self, layer1, data, config):
        del layer1, data, config
        return pd.DataFrame()

    def _layer3_rolling_aggregation(self, layer1, layer2, config):
        del layer1, layer2, config
        return _layer_df(8, 64)

    def _layer4_lag_features(self, layer1, layer2, layer3, data, config):
        del layer1, layer2, layer3, data, config
        return pd.DataFrame()

    def _layer5_cross_sectional(self, layer1, layer2, config):
        del layer1, layer2, config
        return pd.DataFrame()

    def _layer6_meta_features(self, layer1, layer2, data, config):
        del layer1, layer2, data, config
        return pd.DataFrame()

    def _persist_layer_output_groups(self, frame, layer, label) -> None:
        self._real._current_symbol = self._current_symbol
        self._real._current_timeframe = self._current_timeframe
        self._real._cgsa_registry = self._cgsa_registry
        self._real._persist_layer_output_groups(frame, layer, label)


def _primary_frames() -> pd.DataFrame:
    return pd.DataFrame({"timestamp": [0, 12 * 3600 * 1000], "value": [10.0, 11.0]})


def _abort_before_persist(
    factory: _CgsaIntegrationFactory,
    registry: ColumnGroupRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _layer_df(4096, 2048)
    needed = _needed_for_frame(registry, frame)
    monkeypatch.setattr(registry, "_disk_free_bytes", lambda _path: needed - 1)
    factory._current_symbol = "ETHUSDT"
    factory._current_timeframe = "12h"
    with pytest.raises(ColumnGroupRegistryError):
        factory._persist_layer_output_groups(frame, LayerSource.L3, "L3_rolling")


def test_cgsa_disk_precheck_integration_single_tf_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_CGSA_DISK_PRECHECK", "1")
    monkeypatch.setenv("FFACT_CGSA_DISK_RESERVE_GIB", "0")
    registry = ColumnGroupRegistry(tmp_path / "single_tf", memory_buffer_groups=0)
    factory = create_feature_factory(validate_continuity=False)
    factory._cgsa_registry = registry
    factory._current_symbol = "ETHUSDT"
    factory._current_timeframe = "12h"

    frame = _layer_df(4096, 2048)
    needed = _needed_for_frame(registry, frame)
    monkeypatch.setattr(registry, "_disk_free_bytes", lambda _path: needed - 1)

    with pytest.raises(ColumnGroupRegistryError):
        factory._persist_single_tf_l3_l6_to_cgsa(frame, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert len(registry._groups) == 0


def test_cgsa_disk_precheck_integration_serial_multi_tf_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
    monkeypatch.setenv("FFACT_CGSA_DISK_PRECHECK", "1")
    monkeypatch.setenv("FFACT_CGSA_DISK_RESERVE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "serial", memory_buffer_groups=0)
    factory = _CgsaIntegrationFactory({"12h": _primary_frames()}, registry)
    _abort_before_persist(factory, registry, monkeypatch)


def test_cgsa_disk_precheck_integration_parallel_primary_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "1")
    monkeypatch.setenv("FFACT_CGSA_DISK_PRECHECK", "1")
    monkeypatch.setenv("FFACT_CGSA_DISK_RESERVE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "parallel", memory_buffer_groups=0)
    factory = _CgsaIntegrationFactory({"12h": _primary_frames()}, registry)
    _abort_before_persist(factory, registry, monkeypatch)


def test_cgsa_disk_precheck_integration_serial_runs_when_free_sufficient(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
    monkeypatch.setenv("FFACT_CGSA_DISK_PRECHECK", "1")
    monkeypatch.setenv("FFACT_CGSA_DISK_RESERVE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "serial_ok", memory_buffer_groups=0)
    factory = _CgsaIntegrationFactory({"12h": _primary_frames()}, registry)
    frame = _layer_df(128, 64)
    needed = _needed_for_frame(registry, frame)
    monkeypatch.setattr(registry, "_disk_free_bytes", lambda _path: needed + 1024 * 1024)
    factory._current_symbol = "ETHUSDT"
    factory._current_timeframe = "12h"
    factory._persist_layer_output_groups(frame, LayerSource.L3, "L3_rolling")
    assert len(registry._groups) > 0
