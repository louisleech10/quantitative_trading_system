"""
優化錯誤處理器 - 錯誤分類與重試機制

功能:
1. 錯誤分類（可重試/不可重試/致命）
2. 自動重試機制（exponential backoff）
3. 詳細錯誤日誌記錄
4. 錯誤統計分析

Author: Claude (Phase 3.5 Day 3)
Date: 2025-11-02
"""

import logging
import time
from typing import Optional, Tuple
from enum import Enum
import traceback


class ErrorType(Enum):
    """錯誤類型枚舉"""
    RETRYABLE = "retryable"  # 可重試錯誤
    NON_RETRYABLE = "non_retryable"  # 不可重試錯誤
    FATAL = "fatal"  # 致命錯誤


class OptimizationErrorHandler:
    """
    優化錯誤處理器

    負責優化過程中的錯誤分類、重試和日誌記錄。
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        初始化錯誤處理器

        Args:
            max_retries: 最大重試次數（default: 3）
            base_delay: 基礎延遲時間（秒，exponential backoff用）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)

        # 錯誤統計
        self.error_counts = {
            ErrorType.RETRYABLE: 0,
            ErrorType.NON_RETRYABLE: 0,
            ErrorType.FATAL: 0
        }

    def classify_error(self, exception: Exception) -> ErrorType:
        """
        分類錯誤類型

        Args:
            exception: 捕獲的異常

        Returns:
            ErrorType枚舉值
        """
        exception_type = type(exception).__name__
        exception_msg = str(exception).lower()

        # 可重試錯誤（網絡、暫時性問題）
        retryable_patterns = [
            'connection', 'timeout', 'network', 'temporary',
            'retry', 'unavailable', 'busy', 'lock'
        ]

        # 致命錯誤（系統級問題）
        fatal_patterns = [
            'memory', 'disk', 'permission', 'system', 'fatal'
        ]

        # 檢查致命錯誤
        if any(pattern in exception_msg for pattern in fatal_patterns):
            return ErrorType.FATAL

        # 檢查可重試錯誤（基於異常類型）
        if isinstance(exception, (ConnectionError, TimeoutError, OSError)):
            return ErrorType.RETRYABLE

        # 檢查可重試錯誤（基於異常訊息）
        if any(pattern in exception_msg for pattern in retryable_patterns):
            return ErrorType.RETRYABLE

        # 不可重試錯誤（參數錯誤、數據問題）
        if isinstance(exception, (ValueError, KeyError, TypeError, AttributeError)):
            return ErrorType.NON_RETRYABLE

        # 預設為可重試（保守策略）
        self.logger.warning(f"Unknown error type {exception_type}, treating as RETRYABLE")
        return ErrorType.RETRYABLE

    def should_retry(self, error_type_or_attempt, attempt: Optional[int] = None) -> bool:
        """
        判斷是否應該重試

        支援兩種呼叫方式:
        - should_retry(error_type, attempt)
        - should_retry(attempt)
        """
        if attempt is None and isinstance(error_type_or_attempt, int):
            error_type = ErrorType.RETRYABLE
            attempt = error_type_or_attempt
        else:
            error_type = error_type_or_attempt

        if error_type == ErrorType.RETRYABLE and attempt < self.max_retries:
            return True
        return False

    def calculate_backoff_delay(self, attempt: int) -> float:
        """
        計算exponential backoff延遲時間

        Args:
            attempt: 當前重試次數（從1開始）

        Returns:
            延遲時間（秒）
        """
        # Exponential backoff: base_delay * 2^(attempt-1)
        delay = self.base_delay * (2 ** (attempt - 1))
        # 最大延遲60秒
        return min(delay, 60.0)

    def calculate_delay(self, attempt: int) -> float:
        """兼容舊介面：指數退避延遲計算（attempt 從 0 開始）"""
        return min(self.base_delay * (2 ** attempt), 60.0)

    def handle_trial_error(
        self,
        trial_number: int,
        exception: Exception,
        attempt: int = 1
    ) -> Tuple[bool, Optional[float]]:
        """
        處理試驗錯誤

        Args:
            trial_number: 試驗編號
            exception: 捕獲的異常
            attempt: 當前重試次數

        Returns:
            (should_retry, delay) 元組
            - should_retry: 是否應該重試
            - delay: 重試前延遲時間（秒），若不重試則為None
        """
        # 分類錯誤
        error_type = self.classify_error(exception)

        # 更新統計
        self.error_counts[error_type] += 1

        # 記錄錯誤日誌
        self.log_error(
            trial_number=trial_number,
            error_type=error_type,
            exception=exception,
            attempt=attempt
        )

        # 判斷是否重試
        should_retry = self.should_retry(error_type, attempt)

        if should_retry:
            delay = self.calculate_backoff_delay(attempt)
            self.logger.info(
                f"Trial {trial_number} will retry (attempt {attempt}/{self.max_retries}) "
                f"after {delay:.1f}s delay"
            )
            return (True, delay)
        else:
            if error_type == ErrorType.FATAL:
                self.logger.critical(
                    f"Trial {trial_number} encountered FATAL error, "
                    f"optimization should be terminated"
                )
            else:
                self.logger.info(
                    f"Trial {trial_number} will not retry (error_type={error_type.value})"
                )
            return (False, None)

    def log_error(
        self,
        trial_number: int,
        error_type: ErrorType,
        exception: Exception,
        attempt: int
    ):
        """
        記錄詳細錯誤日誌

        Args:
            trial_number: 試驗編號
            error_type: 錯誤類型
            exception: 異常對象
            attempt: 重試次數
        """
        error_log = (
            f"\n{'='*60}\n"
            f"[ERROR] Trial {trial_number} Failed\n"
            f"{'='*60}\n"
            f"Error Type: {error_type.value.upper()}\n"
            f"Exception: {type(exception).__name__}\n"
            f"Message: {str(exception)}\n"
            f"Attempt: {attempt}/{self.max_retries}\n"
            f"Traceback:\n{traceback.format_exc()}"
            f"{'='*60}\n"
        )

        if error_type == ErrorType.FATAL:
            self.logger.critical(error_log)
        elif error_type == ErrorType.RETRYABLE:
            self.logger.warning(error_log)
        else:
            self.logger.error(error_log)

    def get_error_statistics(self) -> dict:
        """
        獲取錯誤統計信息

        Returns:
            錯誤統計字典
        """
        total_errors = sum(self.error_counts.values())

        return {
            'total_errors': total_errors,
            'retryable_errors': self.error_counts[ErrorType.RETRYABLE],
            'non_retryable_errors': self.error_counts[ErrorType.NON_RETRYABLE],
            'fatal_errors': self.error_counts[ErrorType.FATAL],
            'error_rate_by_type': {
                error_type.value: count / max(total_errors, 1)
                for error_type, count in self.error_counts.items()
            }
        }

    def reset_statistics(self):
        """重置錯誤統計"""
        self.error_counts = {
            ErrorType.RETRYABLE: 0,
            ErrorType.NON_RETRYABLE: 0,
            ErrorType.FATAL: 0
        }
        self.logger.info("Error statistics reset")
