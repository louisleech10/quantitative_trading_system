"""
數據驗證器 - Optuna 優化數據驗證

功能:
1. 優化前驗證：檢查案例數量、時間重疊、案例 ID 有效性
2. 運行時驗證：檢查 trial 結果的合法性（密度比率、統計指標）
3. 數據質量警告：識別潛在的數據質量問題

設計理念:
- 數據真實性原則：確保所有輸入數據真實有效
- 早期失敗：優化前發現問題，避免浪費計算資源
- 詳細報告：提供清晰的驗證錯誤信息

Author: Claude (Optuna 優化系統 Phase 2)
Date: 2025-12-01
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from momentum.core.contracts import SignalDensityResponse


class ValidationSeverity(str, Enum):
    """驗證結果嚴重程度"""
    ERROR = "error"      # 錯誤：必須修復才能繼續
    WARNING = "warning"  # 警告：可以繼續但建議修復
    INFO = "info"        # 信息：僅供參考


@dataclass
class ValidationIssue:
    """驗證問題"""
    severity: ValidationSeverity
    code: str           # 問題代碼（如 "INSUFFICIENT_CASES"）
    message: str        # 問題描述
    details: Dict[str, Any] = field(default_factory=dict)  # 詳細信息


@dataclass
class ValidationResult:
    """驗證結果"""
    is_valid: bool                              # 是否通過驗證
    issues: List[ValidationIssue] = field(default_factory=list)  # 問題列表

    @property
    def errors(self) -> List[ValidationIssue]:
        """獲取所有錯誤"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """獲取所有警告"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]

    @property
    def has_errors(self) -> bool:
        """是否有錯誤"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def add_error(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        """添加錯誤"""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code=code,
            message=message,
            details=details or {}
        ))
        self.is_valid = False

    def add_warning(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        """添加警告"""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code=code,
            message=message,
            details=details or {}
        ))

    def add_info(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        """添加信息"""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            code=code,
            message=message,
            details=details or {}
        ))


class DataValidator:
    """
    數據驗證器

    負責驗證 Optuna 優化過程中的數據質量和合法性。
    """

    def __init__(
        self,
        min_cases_per_group: int = 10,
        max_time_overlap_ratio: float = 0.1,
        valid_ratio_range: tuple = (0.5, 3.0),
        valid_pvalue_range: tuple = (0.0, 1.0)
    ):
        """
        初始化數據驗證器

        Args:
            min_cases_per_group: 每組最小案例數量（默認 10）
            max_time_overlap_ratio: 最大時間重疊比例（默認 0.1 = 10%）
            valid_ratio_range: 有效密度比率範圍（默認 0.5-3.0）
            valid_pvalue_range: 有效 p-value 範圍（默認 0.0-1.0）
        """
        self.min_cases_per_group = min_cases_per_group
        self.max_time_overlap_ratio = max_time_overlap_ratio
        self.valid_ratio_range = valid_ratio_range
        self.valid_pvalue_range = valid_pvalue_range
        self.logger = logging.getLogger(__name__)

        self.logger.info(
            f"DataValidator initialized: min_cases={min_cases_per_group}, "
            f"max_overlap={max_time_overlap_ratio}, "
            f"valid_ratio_range={valid_ratio_range}"
        )

    async def validate_pre_optimization(
        self,
        positive_case_ids: List[str],
        negative_case_ids: List[str],
        case_storage = None  # CaseStorage 實例（可選）
    ) -> ValidationResult:
        """
        優化前驗證

        檢查：
        1. 案例數量是否足夠（>= min_cases_per_group）
        2. 正例和反例是否有重疊
        3. 案例 ID 是否有效（如果提供 case_storage）

        Args:
            positive_case_ids: 正例案例 ID 列表
            negative_case_ids: 反例案例 ID 列表
            case_storage: 案例存儲管理器（可選）

        Returns:
            ValidationResult: 驗證結果
        """
        result = ValidationResult(is_valid=True)

        # 1. 檢查案例數量
        self._validate_case_count(positive_case_ids, negative_case_ids, result)

        # 2. 檢查案例重疊
        self._validate_case_overlap(positive_case_ids, negative_case_ids, result)

        # 3. 檢查案例 ID 有效性（如果提供 case_storage）
        if case_storage is not None:
            await self._validate_case_ids(positive_case_ids, negative_case_ids, case_storage, result)

        # 記錄驗證結果
        if result.has_errors:
            self.logger.error(
                f"Pre-optimization validation failed with {len(result.errors)} errors"
            )
        elif result.has_warnings:
            self.logger.warning(
                f"Pre-optimization validation passed with {len(result.warnings)} warnings"
            )
        else:
            self.logger.info("Pre-optimization validation passed")

        return result

    def _validate_case_count(
        self,
        positive_case_ids: List[str],
        negative_case_ids: List[str],
        result: ValidationResult
    ):
        """驗證案例數量"""
        pos_count = len(positive_case_ids)
        neg_count = len(negative_case_ids)

        if pos_count < self.min_cases_per_group:
            result.add_error(
                code="INSUFFICIENT_POSITIVE_CASES",
                message=f"正例案例數量不足：需要至少 {self.min_cases_per_group} 個，實際 {pos_count} 個",
                details={
                    "required": self.min_cases_per_group,
                    "actual": pos_count,
                    "missing": self.min_cases_per_group - pos_count
                }
            )

        if neg_count < self.min_cases_per_group:
            result.add_error(
                code="INSUFFICIENT_NEGATIVE_CASES",
                message=f"反例案例數量不足：需要至少 {self.min_cases_per_group} 個，實際 {neg_count} 個",
                details={
                    "required": self.min_cases_per_group,
                    "actual": neg_count,
                    "missing": self.min_cases_per_group - neg_count
                }
            )

        # 警告：樣本不平衡
        if pos_count > 0 and neg_count > 0:
            ratio = max(pos_count, neg_count) / min(pos_count, neg_count)
            if ratio > 3.0:
                result.add_warning(
                    code="IMBALANCED_SAMPLES",
                    message=f"正反例樣本不平衡：比例 {ratio:.2f}:1 (建議 <3:1)",
                    details={
                        "positive_count": pos_count,
                        "negative_count": neg_count,
                        "ratio": ratio
                    }
                )

    def _validate_case_overlap(
        self,
        positive_case_ids: List[str],
        negative_case_ids: List[str],
        result: ValidationResult
    ):
        """驗證案例重疊"""
        # 轉換為集合以檢查重疊
        pos_set = set(positive_case_ids)
        neg_set = set(negative_case_ids)

        overlap = pos_set & neg_set

        if overlap:
            result.add_error(
                code="CASE_OVERLAP",
                message=f"正例和反例有重疊：{len(overlap)} 個案例同時出現在兩組中",
                details={
                    "overlap_count": len(overlap),
                    "overlap_ids": list(overlap)[:10]  # 最多顯示 10 個
                }
            )

    async def _validate_case_ids(
        self,
        positive_case_ids: List[str],
        negative_case_ids: List[str],
        case_storage,
        result: ValidationResult
    ):
        """驗證案例 ID 有效性"""
        # 檢查 case_storage 是否有 case_exists 方法
        if not hasattr(case_storage, 'case_exists'):
            result.add_warning(
                code="CASE_STORAGE_NO_VALIDATION",
                message="CaseStorage 未實作 case_exists() 方法，無法驗證案例 ID",
                details={"case_storage_type": type(case_storage).__name__}
            )
            return

        # 驗證正例案例 ID
        invalid_positive = []
        for case_id in positive_case_ids:
            try:
                if not case_storage.case_exists(case_id):
                    invalid_positive.append(case_id)
            except Exception as e:
                self.logger.warning(f"Error checking positive case {case_id}: {e}")

        if invalid_positive:
            result.add_error(
                code="INVALID_POSITIVE_CASE_IDS",
                message=f"發現 {len(invalid_positive)} 個無效的正例案例 ID",
                details={
                    "invalid_count": len(invalid_positive),
                    "invalid_ids": invalid_positive[:10]  # 最多顯示 10 個
                }
            )

        # 驗證反例案例 ID
        invalid_negative = []
        for case_id in negative_case_ids:
            try:
                if not case_storage.case_exists(case_id):
                    invalid_negative.append(case_id)
            except Exception as e:
                self.logger.warning(f"Error checking negative case {case_id}: {e}")

        if invalid_negative:
            result.add_error(
                code="INVALID_NEGATIVE_CASE_IDS",
                message=f"發現 {len(invalid_negative)} 個無效的反例案例 ID",
                details={
                    "invalid_count": len(invalid_negative),
                    "invalid_ids": invalid_negative[:10]  # 最多顯示 10 個
                }
            )

    def validate_trial_result(
        self,
        result_response: SignalDensityResponse
    ) -> ValidationResult:
        """
        驗證單次 trial 結果

        檢查：
        1. 密度比率是否在有效範圍內
        2. p-value 是否在有效範圍內
        3. 統計指標是否有效（非 NaN）

        Args:
            result_response: SignalDensityResponse 實例

        Returns:
            ValidationResult: 驗證結果
        """
        result = ValidationResult(is_valid=True)

        # 1. 驗證密度比率範圍
        self._validate_density_ratios(result_response, result)

        # 2. 驗證 p-value 範圍
        self._validate_pvalue(result_response, result)

        # 3. 驗證統計指標
        self._validate_statistics(result_response, result)

        return result

    def _validate_density_ratios(
        self,
        response: SignalDensityResponse,
        result: ValidationResult
    ):
        """驗證密度比率範圍"""
        min_ratio, max_ratio = self.valid_ratio_range

        # 檢查 positive_near_far_ratio
        if hasattr(response, 'positive_near_far_ratio') and response.positive_near_far_ratio is not None:
            if response.positive_near_far_ratio < min_ratio or response.positive_near_far_ratio > max_ratio:
                result.add_warning(
                    code="RATIO_OUT_OF_RANGE",
                    message=f"正例 near/far ratio 超出建議範圍 [{min_ratio}, {max_ratio}]: {response.positive_near_far_ratio:.3f}",
                    details={
                        "ratio_type": "positive_near_far_ratio",
                        "value": response.positive_near_far_ratio,
                        "valid_range": self.valid_ratio_range
                    }
                )

        # 檢查 negative_near_far_ratio
        if hasattr(response, 'negative_near_far_ratio') and response.negative_near_far_ratio is not None:
            if response.negative_near_far_ratio < min_ratio or response.negative_near_far_ratio > max_ratio:
                result.add_warning(
                    code="RATIO_OUT_OF_RANGE",
                    message=f"反例 near/far ratio 超出建議範圍 [{min_ratio}, {max_ratio}]: {response.negative_near_far_ratio:.3f}",
                    details={
                        "ratio_type": "negative_near_far_ratio",
                        "value": response.negative_near_far_ratio,
                        "valid_range": self.valid_ratio_range
                    }
                )

    def _validate_pvalue(
        self,
        response: SignalDensityResponse,
        result: ValidationResult
    ):
        """驗證 p-value 範圍"""
        if not hasattr(response, 'p_value') or response.p_value is None:
            return

        import math
        if math.isnan(response.p_value):
            result.add_warning(
                code="PVALUE_NAN",
                message="p-value 為 NaN，可能表示數據不足或計算錯誤",
                details={"p_value": "NaN"}
            )
            return

        min_p, max_p = self.valid_pvalue_range
        if response.p_value < min_p or response.p_value > max_p:
            result.add_error(
                code="INVALID_PVALUE",
                message=f"p-value 超出有效範圍 [{min_p}, {max_p}]: {response.p_value}",
                details={
                    "p_value": response.p_value,
                    "valid_range": self.valid_pvalue_range
                }
            )

    def _validate_statistics(
        self,
        response: SignalDensityResponse,
        result: ValidationResult
    ):
        """驗證統計指標"""
        import math

        # 檢查關鍵統計指標是否為 NaN
        checks = [
            ('positive_avg_density', response.positive_avg_density if hasattr(response, 'positive_avg_density') else None),
            ('negative_avg_density', response.negative_avg_density if hasattr(response, 'negative_avg_density') else None),
            ('separation', response.separation if hasattr(response, 'separation') else None),
            ('cohens_d', response.cohens_d if hasattr(response, 'cohens_d') else None),
        ]

        for name, value in checks:
            if value is not None and math.isnan(value):
                result.add_warning(
                    code="STATISTIC_NAN",
                    message=f"統計指標 {name} 為 NaN，可能表示數據質量問題",
                    details={"statistic_name": name}
                )

        # 檢查 separation 是否為負數（通常表示優化方向錯誤）
        if hasattr(response, 'separation') and response.separation is not None:
            if not math.isnan(response.separation) and response.separation < -1.0:
                result.add_warning(
                    code="NEGATIVE_SEPARATION",
                    message=f"Separation 為負數 ({response.separation:.4f})，反例密度高於正例",
                    details={"separation": response.separation}
                )
