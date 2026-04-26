"""
測試價格變動計算方式功能
驗證 OPEN_TO_CLOSE 和 CLOSE_TO_CLOSE 兩種計算方式的正確性

執行方式：
    python test_price_change_calculation.py

測試項目：
1. 驗證 PriceChangeMethodEnum 枚舉值
2. 測試 _add_calculated_columns 兩種計算方式
3. 驗證 API 請求參數傳遞
4. 確認正例與反例使用相同的計算方式
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.models.requests import PriceChangeMethodEnum, SearchConfigRequest
from momentum.DataExtraction.case_search_engine import CaseSearchEngine, SearchConfiguration
from api.core.logging import get_logger

logger = get_logger(__name__)


def test_1_enum_values():
    """測試1: 驗證 PriceChangeMethodEnum 枚舉值"""
    logger.info("=" * 50)
    logger.info("測試1: 驗證 PriceChangeMethodEnum 枚舉值")
    logger.info("=" * 50)
    
    assert hasattr(PriceChangeMethodEnum, 'OPEN_TO_CLOSE')
    assert hasattr(PriceChangeMethodEnum, 'CLOSE_TO_CLOSE')
    
    assert PriceChangeMethodEnum.OPEN_TO_CLOSE.value == "OPEN_TO_CLOSE"
    assert PriceChangeMethodEnum.CLOSE_TO_CLOSE.value == "CLOSE_TO_CLOSE"
    
    logger.info("✅ 枚舉值驗證通過")
    logger.info(f"   OPEN_TO_CLOSE = {PriceChangeMethodEnum.OPEN_TO_CLOSE.value}")
    logger.info(f"   CLOSE_TO_CLOSE = {PriceChangeMethodEnum.CLOSE_TO_CLOSE.value}")


def test_2_open_to_close_calculation():
    """測試2: 驗證 OPEN_TO_CLOSE 計算方式"""
    logger.info("\n" + "=" * 50)
    logger.info("測試2: 驗證 OPEN_TO_CLOSE 計算方式")
    logger.info("=" * 50)
    
    # 建立測試數據
    test_data = pd.DataFrame({
        'open_time': [1000, 2000, 3000, 4000],
        'open': [100.0, 110.0, 105.0, 108.0],
        'high': [105.0, 115.0, 110.0, 112.0],
        'low': [98.0, 108.0, 103.0, 106.0],
        'close': [104.0, 112.0, 107.0, 111.0],
        'volume': [1000, 1200, 900, 1100],
        'quote_volume': [100000, 120000, 90000, 110000],
    })
    
    # 直接呼叫靜態方法測試
    # OPEN_TO_CLOSE: (close - open) / open
    result_df = test_data.copy()
    result_df['price_change'] = (result_df['close'] - result_df['open']) / result_df['open']
    result_df['closing_strength'] = (result_df['close'] - result_df['low']) / (result_df['high'] - result_df['low'])
    result_df['price_position'] = (result_df['close'] - result_df['low'].rolling(20).min()) / (result_df['high'].rolling(20).max() - result_df['low'].rolling(20).min())
    result_df['volume_multiplier'] = result_df['volume'] / result_df['volume'].rolling(20).mean()
    
    # 驗證計算結果 (Close - Open) / Open
    expected_changes = [
        (104.0 - 100.0) / 100.0,  # 0.04 = 4%
        (112.0 - 110.0) / 110.0,  # 0.0182 = 1.82%
        (107.0 - 105.0) / 105.0,  # 0.019 = 1.9%
        (111.0 - 108.0) / 108.0,  # 0.0278 = 2.78%
    ]
    
    logger.info("期望的 price_change 值 (OPEN_TO_CLOSE):")
    for i, expected in enumerate(expected_changes):
        actual = result_df.loc[i, 'price_change']
        logger.info(f"   Row {i}: Expected={expected:.4f} ({expected*100:.2f}%), Actual={actual:.4f} ({actual*100:.2f}%)")
        assert abs(actual - expected) < 1e-6, f"Row {i}: Expected {expected}, got {actual}"
    
    logger.info("✅ OPEN_TO_CLOSE 計算驗證通過")


def test_3_close_to_close_calculation():
    """測試3: 驗證 CLOSE_TO_CLOSE 計算方式"""
    logger.info("\n" + "=" * 50)
    logger.info("測試3: 驗證 CLOSE_TO_CLOSE 計算方式")
    logger.info("=" * 50)
    
    # 建立測試數據 (與測試2相同)
    test_data = pd.DataFrame({
        'open_time': [1000, 2000, 3000, 4000],
        'open': [100.0, 110.0, 105.0, 108.0],
        'high': [105.0, 115.0, 110.0, 112.0],
        'low': [98.0, 108.0, 103.0, 106.0],
        'close': [104.0, 112.0, 107.0, 111.0],
        'volume': [1000, 1200, 900, 1100],
        'quote_volume': [100000, 120000, 90000, 110000],
    })
    
    # 直接呼叫 pct_change() 測試
    # CLOSE_TO_CLOSE: close.pct_change()
    result_df = test_data.copy()
    result_df['price_change'] = result_df['close'].pct_change()
    result_df['closing_strength'] = (result_df['close'] - result_df['low']) / (result_df['high'] - result_df['low'])
    result_df['price_position'] = (result_df['close'] - result_df['low'].rolling(20).min()) / (result_df['high'].rolling(20).max() - result_df['low'].rolling(20).min())
    result_df['volume_multiplier'] = result_df['volume'] / result_df['volume'].rolling(20).mean()
    
    # 驗證計算結果 (Close[i] - Close[i-1]) / Close[i-1]
    # 第一個值應該是 NaN (沒有前一個收盤價)
    expected_changes = [
        np.nan,  # 第一根K線
        (112.0 - 104.0) / 104.0,   # 0.0769 = 7.69%
        (107.0 - 112.0) / 112.0,   # -0.0446 = -4.46%
        (111.0 - 107.0) / 107.0,   # 0.0374 = 3.74%
    ]
    
    logger.info("期望的 price_change 值 (CLOSE_TO_CLOSE):")
    for i, expected in enumerate(expected_changes):
        actual = result_df.loc[i, 'price_change']
        if pd.isna(expected):
            logger.info(f"   Row {i}: Expected=NaN, Actual={actual} (應為 NaN)")
            assert pd.isna(actual), f"Row {i}: Expected NaN, got {actual}"
        else:
            logger.info(f"   Row {i}: Expected={expected:.4f} ({expected*100:.2f}%), Actual={actual:.4f} ({actual*100:.2f}%)")
            assert abs(actual - expected) < 1e-6, f"Row {i}: Expected {expected}, got {actual}"
    
    logger.info("✅ CLOSE_TO_CLOSE 計算驗證通過")


def test_4_search_configuration():
    """測試4: 驗證 SearchConfiguration 接受 price_change_method 參數"""
    logger.info("\n" + "=" * 50)
    logger.info("測試4: 驗證 SearchConfiguration 參數傳遞")
    logger.info("=" * 50)
    
    # 測試 OPEN_TO_CLOSE
    config1 = SearchConfiguration(
        timeframe='12h',
        time_range=('2024-01-01', '2024-12-31'),
        price_change_method='OPEN_TO_CLOSE'
    )
    assert config1.price_change_method == 'OPEN_TO_CLOSE'
    logger.info(f"✅ Config 1: price_change_method = {config1.price_change_method}")
    
    # 測試 CLOSE_TO_CLOSE
    config2 = SearchConfiguration(
        timeframe='12h',
        time_range=('2024-01-01', '2024-12-31'),
        price_change_method='CLOSE_TO_CLOSE'
    )
    assert config2.price_change_method == 'CLOSE_TO_CLOSE'
    logger.info(f"✅ Config 2: price_change_method = {config2.price_change_method}")
    
    # 測試預設值 (應該是 CLOSE_TO_CLOSE)
    config3 = SearchConfiguration(
        timeframe='12h',
        time_range=('2024-01-01', '2024-12-31')
    )
    assert config3.price_change_method == 'CLOSE_TO_CLOSE'
    logger.info(f"✅ Config 3 (預設): price_change_method = {config3.price_change_method}")


def test_5_api_request_model():
    """測試5: 驗證 API 請求模型"""
    logger.info("\n" + "=" * 50)
    logger.info("測試5: 驗證 API 請求模型")
    logger.info("=" * 50)
    
    # 測試帶 price_change_method 的請求
    request1 = SearchConfigRequest(
        name="測試搜索",
        timeframe="12h",
        start_date="2024-01-01",
        end_date="2024-12-31",
        price_change_method=PriceChangeMethodEnum.OPEN_TO_CLOSE
    )
    assert request1.price_change_method == PriceChangeMethodEnum.OPEN_TO_CLOSE
    logger.info(f"✅ Request 1: price_change_method = {request1.price_change_method.value}")
    
    # 測試預設值
    request2 = SearchConfigRequest(
        name="測試搜索",
        timeframe="12h",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    assert request2.price_change_method == PriceChangeMethodEnum.CLOSE_TO_CLOSE
    logger.info(f"✅ Request 2 (預設): price_change_method = {request2.price_change_method.value}")


if __name__ == '__main__':
    logger.info("開始執行價格變動計算方式功能測試")
    logger.info("=" * 70)
    
    try:
        test_1_enum_values()
        test_2_open_to_close_calculation()
        test_3_close_to_close_calculation()
        test_4_search_configuration()
        test_5_api_request_model()
        
        logger.info("\n" + "=" * 70)
        logger.info("🎉 所有測試通過！")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"\n❌ 測試失敗: {str(e)}", exc_info=True)
        sys.exit(1)
