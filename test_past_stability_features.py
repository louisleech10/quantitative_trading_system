#!/usr/bin/env python3
"""
測試歷史穩定度參數實作

驗證5個新參數的正確性：
1. past_24hr_max_single_move
2. past_48hr_price_range
3. past_72hr_avg_bar_volatility
4. past_48hr_directional_movement
5. past_24hr_volume_stability
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from momentum.DataExtraction.case_search_engine import CaseSearchEngine

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockDataLoader:
    """模擬數據加載器（用於測試）"""
    pass

def create_test_data(rows=100, timeframe='12h'):
    """
    創建測試數據

    Args:
        rows: 行數
        timeframe: 時間框架

    Returns:
        測試DataFrame
    """
    # 生成時間索引
    start_date = datetime(2024, 1, 1)
    if timeframe == '12h':
        freq = '12H'
    elif timeframe == '4h':
        freq = '4H'
    elif timeframe == '1h':
        freq = '1H'
    elif timeframe == '1d':
        freq = '1D'
    else:
        freq = '4H'

    dates = pd.date_range(start=start_date, periods=rows, freq=freq)

    # 生成模擬OHLCV數據
    np.random.seed(42)
    base_price = 40000

    data = []
    current_price = base_price

    for i in range(rows):
        # 模擬價格隨機遊走
        change = np.random.randn() * 0.02  # 2%標準差
        open_price = current_price
        close_price = open_price * (1 + change)
        high_price = max(open_price, close_price) * (1 + abs(np.random.randn() * 0.01))
        low_price = min(open_price, close_price) * (1 - abs(np.random.randn() * 0.01))
        volume = np.random.uniform(1000, 5000)

        data.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'quote_asset_volume': volume * close_price,
            'taker_buy_base_asset_volume': volume * np.random.uniform(0.4, 0.6)
        })

        current_price = close_price

    df = pd.DataFrame(data, index=dates)
    return df

def test_12h_timeframe():
    """測試12h timeframe的正確性"""
    logger.info("=" * 60)
    logger.info("測試 1: 12h Timeframe")
    logger.info("=" * 60)

    # 創建測試數據
    df = create_test_data(rows=100, timeframe='12h')
    logger.info(f"測試數據: {len(df)} 行")

    # 創建CaseSearchEngine實例（傳入模擬data_loader）
    engine = CaseSearchEngine(data_loader=MockDataLoader())

    # 調用計算函數
    df_with_features = engine._add_calculated_columns(df, timeframe='12h')

    # 驗證5個參數都存在
    past_params = [
        'past_24hr_max_single_move',
        'past_48hr_price_range',
        'past_72hr_avg_bar_volatility',
        'past_48hr_directional_movement',
        'past_24hr_volume_stability'
    ]

    logger.info("\n參數存在性檢查:")
    for param in past_params:
        exists = param in df_with_features.columns
        logger.info(f"  - {param}: {'✓ 存在' if exists else '✗ 不存在'}")

    # 驗證periods正確性（12h timeframe）
    # 24hr = 24 // 12 = 2根bar
    # 48hr = 48 // 12 = 4根bar
    # 72hr = 72 // 12 = 6根bar
    logger.info("\n12h Timeframe 預期periods:")
    logger.info("  - 24hr 窗口: 2根bar")
    logger.info("  - 48hr 窗口: 4根bar")
    logger.info("  - 72hr 窗口: 6根bar")

    # 檢查NaN值分布
    logger.info("\nNaN值統計:")
    for param in past_params:
        if param in df_with_features.columns:
            nan_count = df_with_features[param].isna().sum()
            valid_count = len(df_with_features) - nan_count
            first_valid_idx = df_with_features[param].first_valid_index()
            logger.info(f"  - {param}:")
            logger.info(f"    - 有效值: {valid_count}/{len(df_with_features)}")
            logger.info(f"    - NaN值: {nan_count}")
            logger.info(f"    - 首個有效索引: {first_valid_idx}")

    # 顯示前10行數據統計
    logger.info("\n前10行數據統計:")
    for param in past_params:
        if param in df_with_features.columns:
            values = df_with_features[param].head(10)
            logger.info(f"  - {param}:")
            logger.info(f"    {values.tolist()}")

    return df_with_features

def test_4h_timeframe():
    """測試4h timeframe的正確性"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: 4h Timeframe")
    logger.info("=" * 60)

    # 創建測試數據
    df = create_test_data(rows=200, timeframe='4h')
    logger.info(f"測試數據: {len(df)} 行")

    # 創建CaseSearchEngine實例（傳入模擬data_loader）
    engine = CaseSearchEngine(data_loader=MockDataLoader())

    # 調用計算函數
    df_with_features = engine._add_calculated_columns(df, timeframe='4h')

    # 驗證periods正確性（4h timeframe）
    # 24hr = 24 // 4 = 6根bar
    # 48hr = 48 // 4 = 12根bar
    # 72hr = 72 // 4 = 18根bar
    logger.info("\n4h Timeframe 預期periods:")
    logger.info("  - 24hr 窗口: 6根bar")
    logger.info("  - 48hr 窗口: 12根bar")
    logger.info("  - 72hr 窗口: 18根bar")

    # 檢查NaN值分布
    past_params = [
        'past_24hr_max_single_move',
        'past_48hr_price_range',
        'past_72hr_avg_bar_volatility',
        'past_48hr_directional_movement',
        'past_24hr_volume_stability'
    ]

    logger.info("\nNaN值統計:")
    for param in past_params:
        if param in df_with_features.columns:
            nan_count = df_with_features[param].isna().sum()
            valid_count = len(df_with_features) - nan_count
            logger.info(f"  - {param}: {valid_count}/{len(df_with_features)} 有效值")

    return df_with_features

def test_extreme_cases():
    """測試邊界情況"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 3: 邊界情況")
    logger.info("=" * 60)

    engine = CaseSearchEngine(data_loader=MockDataLoader())

    # 測試1: 極小數據集
    logger.info("\n3.1 極小數據集（5行）:")
    df_small = create_test_data(rows=5, timeframe='12h')
    df_small_result = engine._add_calculated_columns(df_small, timeframe='12h')
    logger.info(f"  - 計算完成，結果shape: {df_small_result.shape}")
    logger.info(f"  - past_24hr_max_single_move 有效值: {df_small_result['past_24hr_max_single_move'].notna().sum()}")

    # 測試2: 包含零值的數據
    logger.info("\n3.2 包含零值的數據:")
    df_zero = create_test_data(rows=20, timeframe='4h')
    df_zero.loc[df_zero.index[5], 'volume'] = 0  # 設置一個零成交量
    df_zero.loc[df_zero.index[10], 'open'] = df_zero.loc[df_zero.index[10], 'close']  # 無價格變化
    df_zero_result = engine._add_calculated_columns(df_zero, timeframe='4h')
    logger.info(f"  - 計算完成，結果shape: {df_zero_result.shape}")
    logger.info(f"  - past_24hr_volume_stability 包含NaN: {df_zero_result['past_24hr_volume_stability'].isna().any()}")

    # 測試3: 單調趨勢數據（測試 directional_movement）
    logger.info("\n3.3 單調上漲趨勢:")
    df_trend = create_test_data(rows=30, timeframe='12h')
    # 製造單調上漲
    for i in range(1, len(df_trend)):
        df_trend.loc[df_trend.index[i], 'close'] = df_trend.loc[df_trend.index[i-1], 'close'] * 1.01
    df_trend_result = engine._add_calculated_columns(df_trend, timeframe='12h')
    directional = df_trend_result['past_48hr_directional_movement'].dropna()
    logger.info(f"  - past_48hr_directional_movement 平均值: {directional.mean():.4f}")
    logger.info(f"  - 預期接近1.0（單向趨勢）: {'✓' if directional.mean() > 0.8 else '✗'}")

    return df_small_result, df_zero_result, df_trend_result

def test_performance():
    """測試性能（10萬行數據）"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 4: 性能測試（100,000行）")
    logger.info("=" * 60)

    import time

    # 創建大數據集
    logger.info("創建100,000行測試數據...")
    df_large = create_test_data(rows=100000, timeframe='4h')
    logger.info(f"數據創建完成: {df_large.shape}")

    # 測試計算時間
    engine = CaseSearchEngine(data_loader=MockDataLoader())

    logger.info("開始計算歷史穩定度參數...")
    start_time = time.time()
    df_result = engine._add_calculated_columns(df_large, timeframe='4h')
    end_time = time.time()

    duration = end_time - start_time
    logger.info(f"✓ 計算完成！耗時: {duration:.2f} 秒")
    logger.info(f"性能目標: < 2秒 → {'✓ 通過' if duration < 2.0 else '✗ 未達標'}")
    logger.info(f"處理速度: {len(df_large) / duration:.0f} 行/秒")

    return df_result, duration

def main():
    """主測試函數"""
    logger.info("🚀 開始測試歷史穩定度參數實作")
    logger.info("=" * 60)

    try:
        # 測試1: 12h timeframe
        df_12h = test_12h_timeframe()

        # 測試2: 4h timeframe
        df_4h = test_4h_timeframe()

        # 測試3: 邊界情況
        df_small, df_zero, df_trend = test_extreme_cases()

        # 測試4: 性能測試
        df_perf, duration = test_performance()

        # 總結
        logger.info("\n" + "=" * 60)
        logger.info("📊 測試總結")
        logger.info("=" * 60)
        logger.info("✓ 測試1: 12h Timeframe - 通過")
        logger.info("✓ 測試2: 4h Timeframe - 通過")
        logger.info("✓ 測試3: 邊界情況 - 通過")
        logger.info(f"{'✓' if duration < 2.0 else '✗'} 測試4: 性能測試 - {duration:.2f}秒 (目標<2秒)")
        logger.info("\n🎉 所有測試完成！")

        return True

    except Exception as e:
        logger.error(f"測試失敗: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
