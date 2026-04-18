from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Optional

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


def _make_group(
    group_id: str,
    layer: LayerSource,
    timeframe: str,
    data_source: str,
    indicator: str,
    columns: tuple[str, ...],
    shape: tuple[int, int],
    disk_path: Optional[Path] = None,
) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=layer,
        timeframe=timeframe,
        data_source=data_source,
        indicator=indicator,
        columns=columns,
        shape=shape,
        dtype="float32",
        disk_path=disk_path,
    )


def test_column_group_immutable():
    """T2.1: ColumnGroup 為 frozen dataclass，不可修改屬性。"""
    group = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=("close_1h_trend_EMA_5",),
        shape=(10, 1),
    )

    with pytest.raises(FrozenInstanceError):
        group.group_id = "1h_L1_trend_RSI"


def test_column_group_est_bytes():
    """T2.2: est_bytes 應符合 n_rows * n_cols * element_size。"""
    group = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=("a", "b", "c"),
        shape=(100, 3),
    )

    assert group.est_bytes == 100 * 3 * 4


def test_registry_register_and_get(tmp_path: Path):
    """T2.3: register 後可透過 group_id 取回相同物件。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    group = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=("close_1h_trend_EMA_5",),
        shape=(10, 1),
    )

    registry.register(group)

    assert registry.get(group.group_id) == group


def test_registry_duplicate_raises(tmp_path: Path):
    """T2.4: 重複 group_id 註冊應拋 ValueError。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    group = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=("close_1h_trend_EMA_5",),
        shape=(10, 1),
    )

    registry.register(group)

    with pytest.raises(ValueError, match="Duplicate group_id"):
        registry.register(group)


def test_registry_save_and_load_roundtrip(tmp_path: Path):
    """T2.5: save_data 後 load_data 應與原數值一致（float32）。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    data = np.array([[1.0, 2.0], [3.5, np.nan], [7.0, 9.0]], dtype=np.float64)
    group = _make_group(
        group_id="1h_L1_momentum_RSI",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="RSI",
        columns=("close_1h_momentum_RSI_5", "close_1h_momentum_RSI_14"),
        shape=(0, 0),
    )

    updated = registry.save_data(group, data)
    loaded = np.asarray(registry.load_data(updated.group_id))

    assert updated.disk_path is not None
    assert updated.disk_path.exists()
    assert loaded.dtype == np.float32
    np.testing.assert_allclose(loaded, data.astype(np.float32), equal_nan=True)

    resumed = ColumnGroupRegistry.resume_from_manifest(tmp_path)
    resumed_loaded = np.asarray(resumed.load_data(updated.group_id))
    np.testing.assert_allclose(resumed_loaded, data.astype(np.float32), equal_nan=True)


def test_registry_list_by_layer(tmp_path: Path):
    """T2.6: list_by_layer 應只回傳指定 layer 的 groups。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    l1_group = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=("close_1h_trend_EMA_5",),
        shape=(10, 1),
    )
    l2_group = _make_group(
        group_id="1h_L2_cross",
        layer=LayerSource.L2,
        timeframe="1h",
        data_source="close",
        indicator="cross",
        columns=("close_1h_cross_EMA5_EMA21",),
        shape=(10, 1),
    )

    registry.register(l1_group)
    registry.register(l2_group)

    only_l1 = registry.list_by_layer(LayerSource.L1)

    assert [group.group_id for group in only_l1] == ["1h_L1_trend_EMA"]


def test_registry_list_by_timeframe(tmp_path: Path):
    """T2.7: list_by_timeframe 應只回傳指定 TF 的 groups。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    group_1h = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=("close_1h_trend_EMA_5",),
        shape=(10, 1),
    )
    group_12h = _make_group(
        group_id="12h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="close",
        indicator="EMA",
        columns=("close_12h_trend_EMA_5",),
        shape=(10, 1),
    )

    registry.register(group_12h)
    registry.register(group_1h)

    only_1h = registry.list_by_timeframe("1h")

    assert [group.group_id for group in only_1h] == ["1h_L1_trend_EMA"]


def test_registry_all_column_names_order(tmp_path: Path):
    """T2.8: all_column_names() 應符合 Canonical Column Order。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)

    group_l2_12h = _make_group(
        group_id="12h_L2_Ratio",
        layer=LayerSource.L2,
        timeframe="12h",
        data_source="close",
        indicator="RSI",
        columns=(
            "close_12h_momentum_RSI_21_ratio",
            "close_12h_momentum_RSI_5_ratio",
        ),
        shape=(10, 2),
    )
    group_l3_1h = _make_group(
        group_id="1h_L3_trend_EMA_close",
        layer=LayerSource.L3,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=(
            "close_1h_trend_EMA_21_std",
            "close_1h_trend_EMA_5_mean",
        ),
        shape=(10, 2),
    )
    group_l1_1h = _make_group(
        group_id="1h_L1_trend_ADX",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="ADX",
        columns=(
            "close_1h_trend_ADX_14",
            "label_next_1h",
        ),
        shape=(10, 2),
    )

    registry.register(group_l2_12h)
    registry.register(group_l3_1h)
    registry.register(group_l1_1h)

    assert registry.all_column_names() == [
        "close_1h_trend_ADX_14",
        "close_1h_trend_EMA_5_mean",
        "close_1h_trend_EMA_21_std",
        "close_12h_momentum_RSI_5_ratio",
        "close_12h_momentum_RSI_21_ratio",
        "label_next_1h",
    ]


def test_registry_cleanup_deletes_files(tmp_path: Path):
    """T2.9: cleanup 後應刪除全部 .npy 並清空 registry。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    data = np.ones((3, 1), dtype=np.float32)

    group_a = _make_group(
        group_id="1h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=("close_1h_trend_EMA_5",),
        shape=(0, 0),
    )
    group_b = _make_group(
        group_id="12h_L1_trend_EMA",
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="close",
        indicator="EMA",
        columns=("close_12h_trend_EMA_5",),
        shape=(0, 0),
    )

    registry.save_data(group_a, data)
    registry.save_data(group_b, data)

    assert len(list(tmp_path.glob("*.npy"))) == 2

    registry.cleanup()

    assert len(list(tmp_path.glob("*.npy"))) == 0
    assert registry.total_columns() == 0


def test_registry_total_columns(tmp_path: Path):
    """T2.10: total_columns 應等於所有 group 欄位數總和。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    registry.register(
        _make_group(
            group_id="1h_L1_trend_EMA",
            layer=LayerSource.L1,
            timeframe="1h",
            data_source="close",
            indicator="EMA",
            columns=("a", "b"),
            shape=(10, 2),
        )
    )
    registry.register(
        _make_group(
            group_id="12h_L1_momentum_RSI",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="RSI",
            columns=("c", "d", "e"),
            shape=(10, 3),
        )
    )

    assert registry.total_columns() == 5
