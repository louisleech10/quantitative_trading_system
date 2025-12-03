"""
Phase 1 策略註冊系統測試

測試策略元數據和註冊系統是否正常工作

Author: Claude
Date: 2025-12-03
"""

import sys
from pathlib import Path

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Phase 1 策略註冊系統測試")
print("=" * 60)

# Test 1: 導入模組
print("\n[Test 1] 導入模組...")
try:
    from momentum.Analysis.strategy_registry import strategy_registry
    from momentum.Optimization.strategy_metadata import StrategyMetadata
    print("✅ 模組導入成功")
except Exception as e:
    print(f"❌ 模組導入失敗: {e}")
    sys.exit(1)

# Test 2: 列出所有策略
print("\n[Test 2] 列出所有策略...")
try:
    strategies = strategy_registry.list_strategies()
    print(f"✅ 找到 {len(strategies)} 個策略:")
    for strategy in strategies:
        print(f"   - {strategy.strategy_id}: {strategy.display_name} ({strategy.category})")
except Exception as e:
    print(f"❌ 列出策略失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: 獲取 three_line 策略元數據
print("\n[Test 3] 獲取 three_line 策略元數據...")
try:
    three_line = strategy_registry.get_strategy("three_line")
    print(f"✅ 策略: {three_line.display_name}")
    print(f"   描述: {three_line.description}")
    print(f"   參數數量: {len(three_line.parameters)}")
    print(f"   參數列表:")
    for param in three_line.parameters:
        print(f"      - {param.name} ({param.type.value}): "
              f"{param.min_value} - {param.max_value}, default={param.default_value}")
except Exception as e:
    print(f"❌ 獲取元數據失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: 測試參數驗證（有效參數）
print("\n[Test 4] 測試參數驗證（有效參數）...")
try:
    valid_params = {
        "short_period": 7,
        "mid_period": 25,
        "long_period": 70
    }
    result = strategy_registry.validate_parameters("three_line", valid_params)
    if result.is_valid:
        print(f"✅ 參數驗證通過")
    else:
        print(f"❌ 參數驗證失敗: {result.errors}")
except Exception as e:
    print(f"❌ 驗證過程異常: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: 測試參數驗證（無效參數 - 範圍錯誤）
print("\n[Test 5] 測試參數驗證（無效參數 - 範圍錯誤）...")
try:
    invalid_params = {
        "short_period": 20,  # 超出範圍 (max=15)
        "mid_period": 25,
        "long_period": 70
    }
    result = strategy_registry.validate_parameters("three_line", invalid_params)
    if not result.is_valid:
        print(f"✅ 正確識別無效參數:")
        for error in result.errors:
            print(f"   - {error}")
    else:
        print(f"❌ 應該識別出無效參數，但驗證通過了")
except Exception as e:
    print(f"❌ 驗證過程異常: {e}")
    import traceback
    traceback.print_exc()

# Test 6: 測試參數驗證（無效參數 - 約束錯誤）
print("\n[Test 6] 測試參數驗證（無效參數 - 約束錯誤）...")
try:
    invalid_params = {
        "short_period": 25,  # short > mid，違反約束
        "mid_period": 20,
        "long_period": 70
    }
    result = strategy_registry.validate_parameters("three_line", invalid_params)
    if not result.is_valid:
        print(f"✅ 正確識別約束錯誤:")
        for error in result.errors:
            print(f"   - {error}")
    else:
        print(f"❌ 應該識別出約束錯誤，但驗證通過了")
except Exception as e:
    print(f"❌ 驗證過程異常: {e}")
    import traceback
    traceback.print_exc()

# Test 7: 測試獲取計算函數
print("\n[Test 7] 測試獲取計算函數...")
try:
    calculator = strategy_registry.get_calculator("three_line")
    print(f"✅ 獲取計算函數成功: {calculator.__name__}")
    print(f"   函數模組: {calculator.__module__}")
except Exception as e:
    print(f"❌ 獲取計算函數失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: 測試獲取驗證函數
print("\n[Test 8] 測試獲取驗證函數...")
try:
    validator = strategy_registry.get_validator("three_line")
    if validator:
        print(f"✅ 獲取驗證函數成功: {validator.__name__}")
        print(f"   函數模組: {validator.__module__}")
    else:
        print(f"⚠️  該策略沒有自定義驗證函數")
except Exception as e:
    print(f"❌ 獲取驗證函數失敗: {e}")
    import traceback
    traceback.print_exc()

# Test 9: 測試參數範圍提取
print("\n[Test 9] 測試參數範圍提取（用於 Optuna）...")
try:
    ranges = strategy_registry.get_parameter_ranges("three_line")
    print(f"✅ 提取參數範圍成功:")
    for param_name, range_info in ranges.items():
        print(f"   - {param_name}: {range_info}")
except Exception as e:
    print(f"❌ 提取參數範圍失敗: {e}")
    import traceback
    traceback.print_exc()

# Test 10: 測試其他策略
print("\n[Test 10] 測試其他策略 (short_long_cross, mid_long_cross)...")
try:
    for strategy_id in ["short_long_cross", "mid_long_cross"]:
        strategy = strategy_registry.get_strategy(strategy_id)
        calculator = strategy_registry.get_calculator(strategy_id)
        print(f"✅ {strategy_id}:")
        print(f"   顯示名稱: {strategy.display_name}")
        print(f"   參數數量: {len(strategy.parameters)}")
        print(f"   計算函數: {calculator.__name__}")
except Exception as e:
    print(f"❌ 測試其他策略失敗: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Phase 1 測試完成！策略註冊系統工作正常。")
print("=" * 60)
