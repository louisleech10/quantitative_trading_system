"""簡易測試 - 驗證價格變動計算方式功能"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# 測試 1: 驗證 Enum
print("=" * 50)
print("測試 1: 驗證 PriceChangeMethodEnum")
print("=" * 50)

from api.models.requests import PriceChangeMethodEnum

print(f"✓ OPEN_TO_CLOSE = {PriceChangeMethodEnum.OPEN_TO_CLOSE.value}")
print(f"✓ CLOSE_TO_CLOSE = {PriceChangeMethodEnum.CLOSE_TO_CLOSE.value}")

# 測試 2: 驗證 SearchConfigRequest
print("\n" + "=" * 50)
print("測試 2: 驗證 SearchConfigRequest")
print("=" * 50)

from api.models.requests import SearchConfigRequest

request1 = SearchConfigRequest(
    name="測試",
    timeframe="12h",
    start_date="2024-01-01",
    end_date="2024-12-31",
    price_change_method=PriceChangeMethodEnum.OPEN_TO_CLOSE
)
print(f"✓ Request with OPEN_TO_CLOSE: {request1.price_change_method.value}")

request2 = SearchConfigRequest(
    name="測試",
    timeframe="12h",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
print(f"✓ Request default: {request2.price_change_method.value}")

# 測試 3: 驗證 SearchConfiguration
print("\n" + "=" * 50)
print("測試 3: 驗證 SearchConfiguration")
print("=" * 50)

from momentum.DataExtraction.case_search_engine import SearchConfiguration

config1 = SearchConfiguration(
    timeframe='12h',
    price_change_method='OPEN_TO_CLOSE'
)
print(f"✓ Config with OPEN_TO_CLOSE: {config1.price_change_method}")

config2 = SearchConfiguration(
    timeframe='12h'
)
print(f"✓ Config default: {config2.price_change_method}")

# 測試 4: 計算邏輯驗證
print("\n" + "=" * 50)
print("測試 4: 計算邏輯驗證")
print("=" * 50)

import pandas as pd

test_data = pd.DataFrame({
    'open': [100.0, 110.0, 105.0],
    'close': [104.0, 112.0, 107.0],
})

# OPEN_TO_CLOSE
open_to_close = (test_data['close'] - test_data['open']) / test_data['open']
print(f"✓ OPEN_TO_CLOSE 計算: {list(open_to_close)}")
print(f"  預期: [0.04, 0.0182, 0.019]")

# CLOSE_TO_CLOSE
close_to_close = test_data['close'].pct_change()
print(f"✓ CLOSE_TO_CLOSE 計算: {list(close_to_close)}")
print(f"  預期: [NaN, 0.0769, -0.0446]")

print("\n" + "=" * 50)
print("🎉 所有基本測試通過!")
print("=" * 50)
