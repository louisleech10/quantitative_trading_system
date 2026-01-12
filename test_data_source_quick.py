#!/usr/bin/env python3
"""
快速測試不同 data_source 的 EMA 計算
使用簡單的 mock 數據
"""

import pandas as pd
import numpy as np
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams
from api.core.logging import get_logger

logger = get_logger(__name__)

def create_mock_data(n=100):
    """建立 mock K線數據"""
    np.random.seed(42)
    
    # 模擬價格數據（ETH價格範圍 2000-4000）
    close_price = 3000 + np.cumsum(np.random.randn(n) * 50)
    
    # 模擬成交量數據（range 1000-50000）
    volume = 5000 + np.abs(np.random.randn(n) * 10000)
    
    # 模擬 taker_ratio（range 0-1）
    taker_ratio = 0.5 + np.random.randn(n) * 0.15
    taker_ratio = np.clip(taker_ratio, 0, 1)
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='1H'),
        'open': close_price * (1 + np.random.randn(n) * 0.01),
        'high': close_price * (1 + abs(np.random.randn(n)) * 0.02),
        'low': close_price * (1 - abs(np.random.randn(n)) * 0.02),
        'close': close_price,
        'volume': volume,
        'taker_buy_volume': volume * taker_ratio,
        'taker_ratio': taker_ratio,
        'quote_volume': volume * close_price,
        'number_of_trades': np.random.randint(100, 1000, n)
    })
    
    return df

def test_data_source_impact():
    """測試不同 data_source 對 EMA 的影響"""
    logger.info("="*60)
    logger.info("測試不同 data_source 的 EMA 特徵計算")
    logger.info("="*60)
    
    # 1. 建立 mock 數據
    df = create_mock_data(100)
    logger.info(f"建立 mock 數據: {len(df)} 行")
    logger.info(f"  Close 價格範圍: {df['close'].min():.2f} - {df['close'].max():.2f}")
    logger.info(f"  Volume 範圍: {df['volume'].min():.2f} - {df['volume'].max():.2f}")
    logger.info(f"  Taker ratio 範圍: {df['taker_ratio'].min():.4f} - {df['taker_ratio'].max():.4f}")
    
    # 2. 準備策略參數
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
        logger.info(f"\n{'─'*60}")
        logger.info(f"測試 data_source='{data_source}'")
        logger.info('─'*60)
        
        strategy_params = StrategyParams(
            strategy_type='ema_three_line',
            data_source=data_source,
            params=base_params
        )
        
        try:
            features_df, feature_names = extractor.extract_features_from_strategy(
                df.copy(),
                strategy_params
            )
            
            # 記錄 EMA 特徵值（最後一根 K 線）
            ema_columns = ['ema_5', 'ema_20', 'ema_60']
            last_row = features_df.iloc[-1]
            
            results[data_source] = {
                col: last_row[col] for col in ema_columns
            }
            
            logger.info("✅ 特徵提取成功")
            logger.info("最後一根 K 線的 EMA 值:")
            for col in ema_columns:
                logger.info(f"  {col:10s}: {last_row[col]:12.4f}")
                
            # 驗證數值合理性
            if data_source == 'close':
                assert 1000 < last_row['ema_5'] < 10000, "Close EMA 超出合理範圍"
            elif data_source == 'volume':
                assert last_row['ema_5'] > 100, "Volume EMA 太小"
            elif data_source == 'taker_ratio':
                assert 0 <= last_row['ema_5'] <= 1, "Taker ratio EMA 超出 0-1 範圍"
            
            logger.info("✅ 數值合理性檢查通過")
                
        except Exception as e:
            logger.error(f"❌ 失敗: {str(e)}", exc_info=True)
            results[data_source] = {'error': str(e)}
            return False
    
    # 4. 比較結果
    logger.info("\n" + "="*60)
    logger.info("結果比較與驗證")
    logger.info("="*60)
    
    # 檢查不同 data_source 的 EMA 是否不同
    all_same = True
    first_source = 'close'
    
    for source in ['volume', 'taker_ratio']:
        if 'error' in results[source]:
            continue
        
        logger.info(f"\n{first_source} vs {source}:")
        for col in ['ema_5', 'ema_20', 'ema_60']:
            val1 = results[first_source][col]
            val2 = results[source][col]
            diff_pct = abs(val1 - val2) / val1 * 100
            
            logger.info(f"  {col:10s}: {val1:12.4f} vs {val2:12.4f} (差異 {diff_pct:6.2f}%)")
            
            if diff_pct > 0.01:  # 差異超過 0.01%
                all_same = False
    
    logger.info("\n" + "="*60)
    if all_same:
        logger.error("❌ 失敗：所有 data_source 產生相同的 EMA 值")
        logger.error("   這表示 data_source 參數沒有生效")
        return False
    else:
        logger.info("✅ 成功：不同 data_source 產生不同的 EMA 值")
        logger.info("   data_source 參數正確生效")
        return True

if __name__ == '__main__':
    try:
        success = test_data_source_impact()
        
        if success:
            logger.info("\n" + "="*60)
            logger.info("✅✅✅ 所有測試通過 ✅✅✅")
            logger.info("="*60)
            exit(0)
        else:
            logger.error("\n" + "="*60)
            logger.error("❌ 測試失敗")
            logger.error("="*60)
            exit(1)
            
    except Exception as e:
        logger.error(f"\n❌ 測試異常: {str(e)}", exc_info=True)
        exit(1)
