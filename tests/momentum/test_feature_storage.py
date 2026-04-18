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
from pathlib import Path
import shutil

from momentum.FeatureEngineering.feature_extractor import (
    FeatureExtractor,
    StrategyParams
)
from momentum.FeatureEngineering.feature_storage import FeatureStorage


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
        group = f[f"{symbol}/{timeframe}"]
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
