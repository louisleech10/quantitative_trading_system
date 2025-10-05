"""
Phase 0 錯誤處理測試套件

測試內容：
1. 錯誤分類正確性
2. 退避延遲計算
3. 失敗記錄創建
4. 重試配置驗證
"""

import logging
import sys
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent))

from momentum.DataExtraction.data_cache_manager import (
    CacheFailureType,
    classify_cache_error,
    calculate_cache_backoff_delay,
    CACHE_RETRY_CONFIG
)

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_error_classification():
    """測試1：錯誤分類正確性"""
    logger.info("="*60)
    logger.info("測試1：錯誤分類")
    logger.info("="*60)

    test_cases = [
        # (錯誤消息, 預期類型)
        ("Connection timeout", CacheFailureType.NETWORK_ERROR),
        ("network unreachable", CacheFailureType.NETWORK_ERROR),
        ("Rate limit exceeded", CacheFailureType.API_LIMIT),
        ("Too many requests (429)", CacheFailureType.API_LIMIT),
        ("No data found", CacheFailureType.DATA_NOT_FOUND),
        ("Data missing", CacheFailureType.DATA_NOT_FOUND),
        ("HDF5 file corrupt", CacheFailureType.HDF5_ERROR),
        ("Invalid HDF5 structure", CacheFailureType.HDF5_ERROR),
        ("Invalid symbol: ABC", CacheFailureType.INVALID_SYMBOL),
        ("Symbol not found", CacheFailureType.INVALID_SYMBOL),
        ("Some random error", CacheFailureType.UNKNOWN),
    ]

    passed = 0
    failed = 0

    for error_msg, expected_type in test_cases:
        error = Exception(error_msg)
        result_type = classify_cache_error(error)

        if result_type == expected_type:
            logger.info(f"✅ '{error_msg}' -> {result_type.value}")
            passed += 1
        else:
            logger.error(
                f"❌ '{error_msg}' -> {result_type.value} "
                f"(預期: {expected_type.value})"
            )
            failed += 1

    logger.info(f"\n錯誤分類測試: {passed}通過, {failed}失敗")
    return failed == 0


def test_backoff_calculation():
    """測試2：退避延遲計算"""
    logger.info("\n" + "="*60)
    logger.info("測試2：退避延遲計算")
    logger.info("="*60)

    test_cases = [
        # (錯誤類型, 嘗試次數, 預期延遲)
        (CacheFailureType.NETWORK_ERROR, 0, 1),    # base * 2^0 = 1
        (CacheFailureType.NETWORK_ERROR, 1, 2),    # base * 2^1 = 2
        (CacheFailureType.NETWORK_ERROR, 2, 4),    # base * 2^2 = 4
        (CacheFailureType.API_LIMIT, 0, 5),        # 固定延遲
        (CacheFailureType.API_LIMIT, 1, 5),        # 固定延遲
        (CacheFailureType.HDF5_ERROR, 0, 0.5),     # base * 2^0 = 0.5
        (CacheFailureType.HDF5_ERROR, 1, 1.0),     # base * 2^1 = 1.0
        (CacheFailureType.UNKNOWN, 0, 2),          # base * 2^0 = 2
        (CacheFailureType.UNKNOWN, 1, 4),          # base * 2^1 = 4
    ]

    passed = 0
    failed = 0

    for error_type, attempt, expected_delay in test_cases:
        result_delay = calculate_cache_backoff_delay(error_type, attempt)

        if result_delay == expected_delay:
            logger.info(
                f"✅ {error_type.value}, 嘗試{attempt} -> {result_delay}秒"
            )
            passed += 1
        else:
            logger.error(
                f"❌ {error_type.value}, 嘗試{attempt} -> {result_delay}秒 "
                f"(預期: {expected_delay}秒)"
            )
            failed += 1

    logger.info(f"\n退避計算測試: {passed}通過, {failed}失敗")
    return failed == 0


def test_retry_config():
    """測試3：重試配置驗證"""
    logger.info("\n" + "="*60)
    logger.info("測試3：重試配置驗證")
    logger.info("="*60)

    expected_configs = {
        CacheFailureType.NETWORK_ERROR: 3,
        CacheFailureType.API_LIMIT: 2,
        CacheFailureType.DATA_NOT_FOUND: 0,
        CacheFailureType.HDF5_ERROR: 1,
        CacheFailureType.INVALID_SYMBOL: 0,
        CacheFailureType.UNKNOWN: 1,
    }

    passed = 0
    failed = 0

    for error_type, expected_retries in expected_configs.items():
        config = CACHE_RETRY_CONFIG[error_type]
        max_retries = config.get('max_retries', 0)

        if max_retries == expected_retries:
            logger.info(
                f"✅ {error_type.value}: "
                f"最多重試{max_retries}次 - {config.get('description', '')}"
            )
            passed += 1
        else:
            logger.error(
                f"❌ {error_type.value}: "
                f"最多重試{max_retries}次 (預期: {expected_retries}次)"
            )
            failed += 1

    logger.info(f"\n重試配置測試: {passed}通過, {failed}失敗")
    return failed == 0


def test_failure_record_structure():
    """測試4：失敗記錄結構驗證"""
    logger.info("\n" + "="*60)
    logger.info("測試4：失敗記錄結構")
    logger.info("="*60)

    from momentum.DataExtraction.data_cache_manager import CacheFailureRecord

    # 創建測試記錄
    record = CacheFailureRecord(
        symbol="BTCUSDT",
        error_type=CacheFailureType.NETWORK_ERROR.value,
        error_message="Connection timeout",
        error_trace="Traceback...",
        severity="transient",
        retry_count=3,
        first_failed_at="2025-10-05T10:00:00",
        last_retry_at="2025-10-05T10:00:10",
        operation="download",
        is_recoverable=True
    )

    # 轉換為字典
    record_dict = record.to_dict()

    # 檢查必要字段
    required_fields = [
        'symbol', 'error_type', 'error_message', 'severity',
        'retry_count', 'operation', 'is_recoverable'
    ]

    passed = 0
    failed = 0

    for field in required_fields:
        if field in record_dict:
            logger.info(f"✅ 字段 '{field}': {record_dict[field]}")
            passed += 1
        else:
            logger.error(f"❌ 缺少字段: {field}")
            failed += 1

    logger.info(f"\n失敗記錄結構測試: {passed}通過, {failed}失敗")
    return failed == 0


def main():
    """運行所有測試"""
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║         Phase 0 錯誤處理測試套件                          ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝\n")

    results = {
        "錯誤分類": test_error_classification(),
        "退避計算": test_backoff_calculation(),
        "重試配置": test_retry_config(),
        "失敗記錄結構": test_failure_record_structure(),
    }

    # 總結
    logger.info("\n" + "="*60)
    logger.info("測試總結")
    logger.info("="*60)

    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        logger.info(f"{test_name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        logger.info("\n✅ 所有測試通過！Phase 0錯誤處理系統運作正常")
        return 0
    else:
        logger.error("\n❌ 部分測試失敗，請檢查日誌")
        return 1


if __name__ == "__main__":
    sys.exit(main())
