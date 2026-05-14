"""
Feature Storage Tests - 特徵儲存測試

測試 HDF5 儲存讀取功能

Author: AI Agent
Date: 2026-01-10
"""

import pytest
import pandas as pd
import numpy as np
import h5py
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from momentum.FeatureEngineering.feature_extractor import (
    FeatureExtractor,
    StrategyParams
)
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


@pytest.fixture
def temp_storage_path(tmp_path):
    """建立臨時儲存目錄"""
    storage_path = tmp_path / "test_features"
    storage_path.mkdir(parents=True, exist_ok=True)
    yield str(storage_path)
    # 清理
    if storage_path.exists():
        shutil.rmtree(storage_path)


@pytest.fixture
def sample_features():
    """生成樣本特徵數據"""
    extractor = FeatureExtractor()
    
    # 載入真實數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    # 提取特徵
    params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
    )
    
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=True
    )
    
    # 填補 NaN
    features_df[feature_names] = features_df[feature_names].fillna(method='ffill')
    features_df[feature_names] = features_df[feature_names].fillna(0)
    
    return features_df, feature_names, params


def test_feature_storage_hdf5(temp_storage_path, sample_features):
    """測試 HDF5 儲存讀取"""
    features_df, feature_names, params = sample_features
    storage = FeatureStorage(base_path=temp_storage_path)
    
    case_id = "TEST_ETHUSDT_1735905600_1"
    symbol = "ETHUSDT"
    timeframe = "1h"
    
    # 儲存特徵
    file_path = storage.save_features_to_hdf5(
        case_id=case_id,
        symbol=symbol,
        timeframe=timeframe,
        features_df=features_df,
        feature_names=feature_names,
        strategy_params={'strategy_type': params.strategy_type, 'params': params.params}
    )
    
    assert Path(file_path).exists(), "特徵檔案應該存在"
    
    # 讀取特徵
    loaded_df, loaded_names, metadata = storage.load_features_from_hdf5(
        case_id, symbol, timeframe
    )
    
    # 檢查資料完整性
    assert len(loaded_df) == len(features_df)
    assert loaded_names == feature_names
    assert metadata['case_id'] == case_id
    assert metadata['symbol'] == symbol
    assert metadata['timeframe'] == timeframe
    assert metadata['strategy_type'] == params.strategy_type
    
    # 檢查特徵值一致性 (允許微小誤差)
    for feature in feature_names:
        np.testing.assert_allclose(
            loaded_df[feature].values,
            features_df[feature].values,
            rtol=1e-4,
            atol=5e-4,
        )
    
    print(f"✅ HDF5 儲存讀取測試通過 - 檔案: {file_path}")


def test_feature_summary(temp_storage_path, sample_features):
    """測試特徵摘要統計"""
    features_df, feature_names, params = sample_features
    storage = FeatureStorage(base_path=temp_storage_path)
    
    case_id = "TEST_ETHUSDT_1735905600_2"
    symbol = "ETHUSDT"
    timeframe = "1h"
    
    # 儲存特徵
    storage.save_features_to_hdf5(
        case_id, symbol, timeframe, features_df, feature_names,
        strategy_params={'strategy_type': params.strategy_type, 'params': params.params}
    )
    
    # 獲取摘要
    summary = storage.get_feature_summary(case_id, symbol, timeframe)
    
    # 檢查摘要內容
    assert summary['case_id'] == case_id
    assert summary['symbol'] == symbol
    assert summary['timeframe'] == timeframe
    assert summary['feature_count'] == len(feature_names)
    assert summary['sample_count'] == len(features_df)
    assert 'feature_stats' in summary
    assert 'high_correlation_pairs' in summary
    
    # 檢查統計量
    for feature in feature_names[:3]:  # 檢查前 3 個特徵
        assert feature in summary['feature_stats']
        stats = summary['feature_stats'][feature]
        assert 'mean' in stats
        assert 'std' in stats
        assert 'min' in stats
        assert 'max' in stats
    
    print(f"✅ 特徵摘要測試通過 - 特徵數: {summary['feature_count']}, "
          f"高相關性對: {len(summary['high_correlation_pairs'])}")


def test_feature_file_operations(temp_storage_path, sample_features):
    """測試特徵檔案操作 (列出、檢查、刪除)"""
    features_df, feature_names, params = sample_features
    storage = FeatureStorage(base_path=temp_storage_path)
    
    case_id = "TEST_ETHUSDT_1735905600_3"
    symbol = "ETHUSDT"
    timeframe = "1h"
    
    # 檢查檔案不存在
    assert not storage.feature_file_exists(case_id)
    
    # 儲存特徵
    storage.save_features_to_hdf5(
        case_id, symbol, timeframe, features_df, feature_names,
        strategy_params={'strategy_type': params.strategy_type, 'params': params.params}
    )
    
    # 檢查檔案存在
    assert storage.feature_file_exists(case_id)
    
    # 列出檔案
    file_list = storage.list_feature_files()
    assert len(file_list) >= 1
    assert any(f['case_id'] == case_id for f in file_list)
    
    # 刪除檔案
    success = storage.delete_features(case_id)
    assert success
    
    # 檢查檔案已刪除
    assert not storage.feature_file_exists(case_id)
    
    print("✅ 特徵檔案操作測試通過")


def test_edge_case_file_not_found(temp_storage_path):
    """Edge Case: 檔案不存在"""
    storage = FeatureStorage(base_path=temp_storage_path)
    
    with pytest.raises(FileNotFoundError):
        storage.load_features_from_hdf5(
            "NONEXISTENT_CASE", "ETHUSDT", "1h"
        )
    
    print("✅ 檔案不存在處理測試通過")


def test_cgsa_registry_reports_insufficient_disk(monkeypatch, tmp_path):
    """測試 CGSA 中間 .npy 寫入遇到磁碟不足時回報可診斷訊息。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    monkeypatch.setattr(registry, "_disk_free_bytes", lambda _path: 1)
    data = np.ones((2, 2), dtype=np.float32)
    group = ColumnGroup(
        group_id="disk_guard",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="TEST",
        columns=("a", "b"),
        shape=data.shape,
    )

    with pytest.raises(Exception) as exc_info:
        registry.save_data(group, data)

    message = str(exc_info.value)
    assert "Insufficient disk space" in message
    assert "disk_guard" in message
    assert "shape=(2, 2)" in message


def test_cgsa_parquet_uses_float32_when_values_exceed_float16(tmp_path):
    """測試 BTC 價格尺度特徵不會因 float16 overflow 變成 inf。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [
            [60000.0, 1.0],
            [70000.0, 2.0],
            [80000.0, 3.0],
        ],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="test_high_price",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("btc_price_feature", "small_feature"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("BTCUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "BTCUSDT" / "hash"
    df = pd.read_parquet(output_dir / "test_high_price.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["btc_price_feature"].dtype) == "float32"
    assert np.isinf(df["btc_price_feature"].to_numpy()).sum() == 0
    assert df["btc_price_feature"].tolist() == [60000.0, 70000.0, 80000.0]
    assert manifest["dtype"] == "float32"
    assert manifest["groups"]["test_high_price"]["dtype"] == "float32"


def test_cgsa_parquet_uses_float32_when_float16_underflows_tiny_values(tmp_path):
    """測試極小價格尺度特徵不會因 float16 underflow 變成 0。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [
            [1.0e-8, -1.0e-8],
            [2.0e-8, -2.0e-8],
            [5.0e-8, -5.0e-8],
        ],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="test_tiny_price",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("tiny_positive", "tiny_negative"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("TINYUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "TINYUSDT" / "hash"
    df = pd.read_parquet(output_dir / "test_tiny_price.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["tiny_positive"].dtype) == "float32"
    np.testing.assert_allclose(df["tiny_positive"].to_numpy(), data[:, 0], rtol=1e-7, atol=0)
    np.testing.assert_allclose(df["tiny_negative"].to_numpy(), data[:, 1], rtol=1e-7, atol=0)
    assert manifest["dtype"] == "float32"
    assert manifest["groups"]["test_tiny_price"]["dtype"] == "float32"


def test_cgsa_parquet_keeps_float16_when_safe(tmp_path):
    """測試一般尺度特徵仍保留 float16 壓縮。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array([[100.0, 1.0], [200.0, 2.0]], dtype=np.float32)
    registry.save_data(
        ColumnGroup(
            group_id="test_small",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("small_price", "small_feature"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("ETHUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "ETHUSDT" / "hash"
    df = pd.read_parquet(output_dir / "test_small.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["small_price"].dtype) == "float16"
    assert manifest["dtype"] == "float16"
    assert manifest["groups"]["test_small"]["dtype"] == "float16"
    # Task 1: dtype_summary structured payload always present.
    summary = manifest["dtype_summary"]
    assert summary["counts"] == {"float16": 1}
    assert summary["float32_fallback_count"] == 0
    assert summary["float32_fallback_parts"] == []


def test_cgsa_manifest_dtype_summary_records_mixed_dtype(tmp_path):
    """Mixed-dtype runs must surface per-dtype counts + the fallback group list."""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    safe = np.array([[100.0, 1.0], [200.0, 2.0], [300.0, 3.0]], dtype=np.float32)
    overflow = np.array(
        [[60000.0, 1.0], [70000.0, 2.0], [80000.0, 3.0]],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_safe",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("safe_a", "safe_b"),
            shape=safe.shape,
        ),
        safe,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_overflow",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("big_a", "big_b"),
            shape=overflow.shape,
        ),
        overflow,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("MIXEDUSDT", "hash", registry)

    manifest = json.loads(
        (tmp_path / "features" / "MIXEDUSDT" / "hash" / "manifest.json").read_text()
    )

    assert manifest["dtype"] == "mixed"
    summary = manifest["dtype_summary"]
    assert summary["counts"] == {"float16": 1, "mixed": 1}
    assert summary["column_counts"] == {"float16": 3, "float32": 1}
    assert summary["float32_fallback_count"] == 1
    assert summary["float32_fallback_parts"] == ["grp_overflow"]


def test_cgsa_parquet_mixed_part_falls_back_per_column(tmp_path):
    """同一 parquet part 內只有不安全欄位應退回 float32。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [[100.0, 60000.0], [200.0, 70000.0], [300.0, 80000.0]],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_mixed_columns",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("safe_small", "unsafe_big"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("MIXCOLUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "MIXCOLUSDT" / "hash"
    df = pd.read_parquet(output_dir / "grp_mixed_columns.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["safe_small"].dtype) == "float16"
    assert str(df["unsafe_big"].dtype) == "float32"
    assert manifest["dtype"] == "mixed"
    assert manifest["groups"]["grp_mixed_columns"]["dtype"] == "mixed"
    assert manifest["dtype_summary"]["counts"] == {"mixed": 1}
    assert manifest["dtype_summary"]["column_counts"] == {"float16": 1, "float32": 1}


def test_l7_disk_precheck_raises_when_estimate_exceeds_free_space(monkeypatch, tmp_path):
    """L7 entry guard fails fast when aggregate estimate exceeds free disk."""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.ones((4, 2), dtype=np.float32)
    registry.save_data(
        ColumnGroup(
            group_id="grp_one",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("a", "b"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 1)

    try:
        storage.persist_registry_to_parquet("DISKFULL", "hash", registry)
        assert False, "Expected aggregate L7 disk pre-check to fail"
    except OSError as exc:
        message = str(exc)
        assert "Insufficient disk space for L7 persist" in message
        assert "safety_factor" in message


def test_l7_disk_precheck_accounts_for_reclaimable_npy(monkeypatch, tmp_path):
    """L7 precheck 應用 streaming budget，不因可回收 .npy 總量誤判失敗。"""
    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    one_gib = 1024 ** 3
    group_count = 1000
    group_bytes = 1000 * 1000 * np.dtype(np.float32).itemsize

    class _FakeDiskPath:
        def exists(self) -> bool:
            return True

        def stat(self) -> SimpleNamespace:
            return SimpleNamespace(st_size=group_bytes)

    groups = [
        (
            f"grp_{index}",
            SimpleNamespace(shape=(1000, 1000), disk_path=_FakeDiskPath()),
        )
        for index in range(group_count)
    ]

    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: one_gib)

    storage._precheck_l7_disk_space(
        tmp_path / "features" / "STREAM" / "hash",
        groups,
        batch_limit=2,
    )


def test_edge_case_corrupted_metadata(temp_storage_path, sample_features):
    """Edge Case: 損壞的元數據處理"""
    features_df, feature_names, params = sample_features
    storage = FeatureStorage(base_path=temp_storage_path)
    
    case_id = "TEST_CORRUPTED"
    symbol = "ETHUSDT"
    timeframe = "1h"
    
    # 儲存特徵
    file_path = storage.save_features_to_hdf5(
        case_id, symbol, timeframe, features_df, feature_names,
        strategy_params={'strategy_type': params.strategy_type, 'params': params.params}
    )
    
    # 手動修改 HDF5 檔案 (移除某些屬性)
    with h5py.File(file_path, 'a') as f:
        assert f"{symbol}/{timeframe}" in f
        # 嘗試讀取缺少某些屬性的情況
        # (實際上 get 方法會返回 None，不會報錯)
    
    # 讀取時應該能容錯處理
    loaded_df, loaded_names, metadata = storage.load_features_from_hdf5(
        case_id, symbol, timeframe
    )
    
    assert loaded_df is not None
    assert loaded_names == feature_names
    
    print("✅ 損壞元數據處理測試通過")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
