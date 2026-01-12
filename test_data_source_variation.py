#!/usr/bin/env python3
"""
測試不同 data_source 的 EMA 特徵工程
驗證：Optuna 的 data_source 參數確實會影響 EMA 計算

Author: Louis
Date: 2026-01-10
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams
from api.core.logging import get_logger

logger = get_logger(__name__)

def load_test_data():
    """載入測試數據（使用 pandas HDF5 讀取）"""
    import os
    
    hdf5_path = os.path.join('data_cache', 'kline_cache.h5')
    
    # 使用 pandas 讀取
    df = pd.read_hdf(hdf5_path, key='ETHUSDT/1h')
    
    # 確保 timestamp 是 datetime 類型
    if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 取最近 100 根 K 線
    df = df.tail(100).reset_index(drop=True)
    
    return df

def test_data_source_variation():
    """測試不同 data_source 對 EMA 特徵的影響"""
    logger.info("="*60)
    logger.info("測試不同 data_source 的 EMA 特徵計算")
    logger.info("="*60)
    
    # 1. 載入數據
    df = load_test_data()
    logger.info(f"載入數據: {len(df)} 行")
    
    # 2. 準備策略參數（只有 data_source 不同）
    base_params = {
        'ema_short': 5,
        'ema_mid': 20,
        'ema_long': 60,
        'volume_threshold': 0.6
    }
    
    data_sources = ['close', 'volume', 'taker_ratio']
    results = {}
    
    # 3. 測試每個 data_source
    extractor = FeatureExtractor()
    
    for data_source in data_sources:
        logger.info(f"\n--- 測試 data_source='{data_source}' ---")
        
        strategy_params = StrategyParams(
            strategy_type='ema_three_line',
            data_source=data_source,
            params=base_params
        )
        
        try:
            features_df = extractor.extract_features_from_strategy(
                df.copy(),
                strategy_params
            )
            
            # 記錄 EMA 特徵值
            ema_columns = ['ema_5', 'ema_20', 'ema_60']
            last_row = features_df.iloc[-1]
            
            results[data_source] = {
                col: last_row[col] for col in ema_columns
            }
            
            logger.info(f"✅ 成功提取特徵")
            logger.info(f"   最後一根 K 線的 EMA 值:")
            for col in ema_columns:
                logger.info(f"     {col}: {last_row[col]:.6f}")
                
        except Exception as e:
            logger.error(f"❌ 失敗: {str(e)}")
            results[data_source] = {'error': str(e)}
    
    # 4. 比較結果
    logger.info("\n" + "="*60)
    logger.info("結果比較")
    logger.info("="*60)
    
    # 檢查是否有差異
    all_same = True
    if len(results) >= 2:
        first_source = list(results.keys())[0]
        first_values = results[first_source]
        
        for source in list(results.keys())[1:]:
            if 'error' in results[source]:
                continue
                
            for col in ['ema_5', 'ema_20', 'ema_60']:
                diff = abs(results[source][col] - first_values[col])
                if diff > 1e-6:  # 允許浮點誤差
                    all_same = False
                    logger.info(f"✅ {source} 的 {col} 與 {first_source} 不同")
                    logger.info(f"   差異: {diff:.6f}")
    
    if all_same:
        logger.warning("⚠️  所有 data_source 產生相同的 EMA 值（可能有問題）")
    else:
        logger.info("✅ 不同 data_source 產生不同的 EMA 值（正確行為）")
    
    # 5. 數值合理性檢查
    logger.info("\n" + "="*60)
    logger.info("數值合理性檢查")
    logger.info("="*60)
    
    for source, values in results.items():
        if 'error' in values:
            logger.error(f"❌ {source}: {values['error']}")
            continue
            
        logger.info(f"\n{source}:")
        
        # Close 應該在合理範圍（ETH 價格通常 1000-5000）
        if source == 'close':
            ema_5 = values['ema_5']
            if 100 < ema_5 < 10000:
                logger.info(f"  ✅ EMA_5 = {ema_5:.2f} (合理的 ETH 價格範圍)")
            else:
                logger.warning(f"  ⚠️  EMA_5 = {ema_5:.2f} (超出預期範圍)")
        
        # Volume 應該是大數值（通常數千到數萬）
        elif source == 'volume':
            ema_5 = values['ema_5']
            if ema_5 > 100:
                logger.info(f"  ✅ EMA_5 = {ema_5:.2f} (合理的成交量範圍)")
            else:
                logger.warning(f"  ⚠️  EMA_5 = {ema_5:.2f} (成交量似乎太小)")
        
        # Taker ratio 應該在 0-1 之間
        elif source == 'taker_ratio':
            ema_5 = values['ema_5']
            if 0 <= ema_5 <= 1:
                logger.info(f"  ✅ EMA_5 = {ema_5:.4f} (合理的比率範圍 0-1)")
            else:
                logger.warning(f"  ⚠️  EMA_5 = {ema_5:.4f} (超出 0-1 範圍)")

if __name__ == '__main__':
    try:
        test_data_source_variation()
        logger.info("\n" + "="*60)
        logger.info("✅ 測試完成")
        logger.info("="*60)
    except Exception as e:
        logger.error(f"\n❌ 測試失敗: {str(e)}", exc_info=True)
        sys.exit(1)
