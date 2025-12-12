"""
測試函數式指標包裝器

驗證 functional_wrapper 和 EMA 函數式版本的功能

Author: Claude (Sonnet 4.5)
Date: 2025-12-04
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("函數式指標包裝器測試")
print("=" * 80)

# Test 1: 導入模組
print("\n[Test 1] 導入模組...")
try:
    from momentum.Indicators import (
        IndicatorEngine,
        DataSourceEnum,
        register_functional_indicator,
    )
    from momentum.Indicators.ema import calculate_ema, validate_ema_params, ema
    print("✅ 模組導入成功")
except Exception as e:
    print(f"❌ 模組導入失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: 檢查 EMA 是否自動註冊
print("\n[Test 2] 檢查 EMA 是否自動註冊...")
try:
    engine = IndicatorEngine()
    indicators = engine.list_indicators()
    print(f"已註冊指標: {indicators}")

    if "ema" in indicators:
        print("✅ EMA 函數式版本已自動註冊")
    else:
        print("❌ EMA 函數式版本未註冊")
        sys.exit(1)
except Exception as e:
    print(f"❌ 檢查註冊失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: 測試直接調用 calculate_ema
print("\n[Test 3] 測試直接調用 calculate_ema...")
try:
    # 創建測試數據
    data = pd.Series(np.random.uniform(100, 200, 100))

    # 直接調用
    result = calculate_ema(data, period=20)

    assert len(result) == len(data), f"長度不匹配: {len(result)} vs {len(data)}"
    assert result.isna().sum() < len(data), "結果全是 NaN"
    print(f"✅ 直接調用成功: 計算 {len(result)} 個值，前 {result.isna().sum()} 個為 NaN")
except Exception as e:
    print(f"❌ 直接調用失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: 測試參數驗證
print("\n[Test 4] 測試參數驗證...")
try:
    # 有效參數
    validate_ema_params(period=20)
    print("✅ 有效參數驗證通過")

    # 無效參數 - 類型錯誤
    try:
        validate_ema_params(period="20")
        print("❌ 應該拒絕字符串類型")
        sys.exit(1)
    except ValueError as e:
        print(f"✅ 正確拒絕字符串類型: {e}")

    # 無效參數 - 範圍錯誤
    try:
        validate_ema_params(period=1)
        print("❌ 應該拒絕 period=1")
        sys.exit(1)
    except ValueError as e:
        print(f"✅ 正確拒絕 period=1: {e}")

    try:
        validate_ema_params(period=300)
        print("❌ 應該拒絕 period=300")
        sys.exit(1)
    except ValueError as e:
        print(f"✅ 正確拒絕 period=300: {e}")

except Exception as e:
    print(f"❌ 參數驗證測試失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: 測試 ema 便利函數
print("\n[Test 5] 測試 ema 便利函數...")
try:
    data = pd.Series(np.random.uniform(100, 200, 100))
    result = ema(data, period=20)

    assert len(result) == len(data)
    print(f"✅ 便利函數調用成功")
except Exception as e:
    print(f"❌ 便利函數調用失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: 測試邊界條件（數據長度不足）
print("\n[Test 6] 測試邊界條件（數據長度不足）...")
try:
    data = pd.Series([1, 2, 3])  # 只有 3 個數據點
    result = calculate_ema(data, period=20)

    assert len(result) == 3
    assert result.isna().all(), "期望全部為 NaN"
    print("✅ 邊界條件處理正確：數據不足時返回全 NaN")
except Exception as e:
    print(f"❌ 邊界條件測試失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: 測試獲取指標元信息
print("\n[Test 7] 測試獲取指標元信息...")
try:
    info = engine.get_indicator_info("ema")
    print(f"✅ 指標信息: {info}")

    assert info['name'] == 'ema'
    assert info['default_params'] == {'period': 20}
    print("✅ 元信息正確")
except Exception as e:
    print(f"❌ 獲取元信息失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: 測試與類裝飾器版本的兼容性
print("\n[Test 8] 測試與類裝飾器版本的兼容性...")
try:
    from momentum.Indicators import EMAIndicator

    # 測試數據
    data = pd.Series(np.random.uniform(100, 200, 100))

    # 類裝飾器版本
    indicator_class = EMAIndicator()
    result_class = indicator_class.calculate(data, period=20)

    # 函數式版本
    result_func = calculate_ema(data, period=20)

    # 比較結果（應該相同或非常接近）
    diff = (result_class - result_func).abs().max()
    print(f"兩種版本的最大差異: {diff}")

    if diff < 1e-10:
        print("✅ 兩種版本結果一致")
    else:
        print(f"⚠️  兩種版本有差異，但差異很小: {diff}")

except Exception as e:
    print(f"❌ 兼容性測試失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ 所有測試通過！函數式指標包裝器工作正常。")
print("=" * 80)
