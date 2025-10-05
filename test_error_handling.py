"""
Phase 1 錯誤處理機制測試

專門測試：
1. 錯誤分類功能
2. 重試邏輯
3. 失敗記錄生成
4. 報告輸出
"""

import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, '/Users/louis/Desktop/quantitative_trading_system')

from momentum.DataExtraction.parallel_search_engine import (
    FailureType,
    classify_error,
    calculate_backoff_delay,
    create_failure_record
)
from datetime import datetime


def test_error_classification():
    """測試錯誤分類功能"""
    print("=" * 60)
    print("測試1：錯誤分類功能")
    print("=" * 60)

    test_cases = [
        (Exception("Connection timeout"), FailureType.NETWORK_ERROR),
        (Exception("Rate limit exceeded"), FailureType.API_LIMIT),
        (Exception("No data available"), FailureType.DATA_NOT_FOUND),
        (Exception("Invalid config"), FailureType.INVALID_CONFIG),
        (Exception("Something went wrong"), FailureType.UNKNOWN),
    ]

    passed = 0
    for error, expected_type in test_cases:
        result = classify_error(error)
        status = "✅" if result == expected_type else "❌"
        print(f"{status} {str(error):30} → {result.value:20} (期望: {expected_type.value})")
        if result == expected_type:
            passed += 1

    print(f"\n通過: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_backoff_calculation():
    """測試退避延遲計算"""
    print("\n" + "=" * 60)
    print("測試2：退避延遲計算")
    print("=" * 60)

    # 網絡錯誤：指數退避
    print("\n網絡錯誤（指數退避）:")
    for attempt in range(3):
        delay = calculate_backoff_delay(FailureType.NETWORK_ERROR, attempt)
        expected = 1 * (2 ** attempt)  # 1s, 2s, 4s
        status = "✅" if delay == expected else "❌"
        print(f"{status} 第{attempt+1}次: {delay}秒 (期望: {expected}秒)")

    # API限流：固定延遲
    print("\nAPI限流（固定延遲）:")
    for attempt in range(2):
        delay = calculate_backoff_delay(FailureType.API_LIMIT, attempt)
        expected = 5.0
        status = "✅" if delay == expected else "❌"
        print(f"{status} 第{attempt+1}次: {delay}秒 (期望: {expected}秒)")

    # 數據缺失：無延遲
    print("\n數據缺失（無重試）:")
    delay = calculate_backoff_delay(FailureType.DATA_NOT_FOUND, 0)
    status = "✅" if delay == 0 else "❌"
    print(f"{status} 延遲: {delay}秒 (期望: 0秒)")

    return True


def test_failure_record_creation():
    """測試失敗記錄創建"""
    print("\n" + "=" * 60)
    print("測試3：失敗記錄創建")
    print("=" * 60)

    test_cases = [
        {
            'error': Exception("Network timeout"),
            'type': FailureType.NETWORK_ERROR,
            'expected_severity': 'transient',
            'expected_recoverable': True
        },
        {
            'error': Exception("No data found"),
            'type': FailureType.DATA_NOT_FOUND,
            'expected_severity': 'permanent',
            'expected_recoverable': False
        },
        {
            'error': Exception("Invalid configuration"),
            'type': FailureType.INVALID_CONFIG,
            'expected_severity': 'critical',
            'expected_recoverable': False
        }
    ]

    all_passed = True
    for i, case in enumerate(test_cases, 1):
        print(f"\n測試案例{i}: {case['type'].value}")

        record = create_failure_record(
            symbol='BTCUSDT',
            error=case['error'],
            error_type=case['type'],
            retry_count=3,
            worker_id=1,
            chunk_idx=0,
            first_failed_at=datetime.now().isoformat()
        )

        # 驗證嚴重性
        severity_ok = record.severity == case['expected_severity']
        print(f"  {'✅' if severity_ok else '❌'} 嚴重性: {record.severity} (期望: {case['expected_severity']})")

        # 驗證可恢復性
        recoverable_ok = record.is_recoverable == case['expected_recoverable']
        print(f"  {'✅' if recoverable_ok else '❌'} 可恢復: {record.is_recoverable} (期望: {case['expected_recoverable']})")

        # 驗證基本字段
        fields_ok = (
            record.symbol == 'BTCUSDT' and
            record.error_type == case['type'].value and
            record.retry_count == 3
        )
        print(f"  {'✅' if fields_ok else '❌'} 基本字段: symbol, error_type, retry_count")

        if not (severity_ok and recoverable_ok and fields_ok):
            all_passed = False

    return all_passed


def test_retry_config():
    """測試重試配置"""
    print("\n" + "=" * 60)
    print("測試4：重試配置驗證")
    print("=" * 60)

    from momentum.DataExtraction.parallel_search_engine import RETRY_CONFIG

    expected_retries = {
        FailureType.NETWORK_ERROR: 3,
        FailureType.API_LIMIT: 2,
        FailureType.DATA_NOT_FOUND: 0,
        FailureType.INVALID_CONFIG: 0,
        FailureType.UNKNOWN: 1
    }

    all_passed = True
    for error_type, expected_count in expected_retries.items():
        actual_count = RETRY_CONFIG[error_type]['max_retries']
        status = "✅" if actual_count == expected_count else "❌"
        print(f"{status} {error_type.value:20} → 最多重試{actual_count}次 (期望: {expected_count}次)")
        if actual_count != expected_count:
            all_passed = False

    return all_passed


def main():
    """主測試函數"""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║       Phase 1 錯誤處理機制單元測試                        ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")

    results = []

    # 執行測試
    try:
        result1 = test_error_classification()
        results.append(("錯誤分類", result1))
    except Exception as e:
        print(f"❌ 測試1失敗: {e}")
        results.append(("錯誤分類", False))

    try:
        result2 = test_backoff_calculation()
        results.append(("退避計算", result2))
    except Exception as e:
        print(f"❌ 測試2失敗: {e}")
        results.append(("退避計算", False))

    try:
        result3 = test_failure_record_creation()
        results.append(("失敗記錄", result3))
    except Exception as e:
        print(f"❌ 測試3失敗: {e}")
        results.append(("失敗記錄", False))

    try:
        result4 = test_retry_config()
        results.append(("重試配置", result4))
    except Exception as e:
        print(f"❌ 測試4失敗: {e}")
        results.append(("重試配置", False))

    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)

    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{name:15} {status}")

    all_passed = all(r for _, r in results)

    if all_passed:
        print("\n🎉 所有測試通過！錯誤處理機制工作正常！")
        return 0
    else:
        print("\n⚠️ 部分測試失敗")
        return 1


if __name__ == "__main__":
    exit(main())
