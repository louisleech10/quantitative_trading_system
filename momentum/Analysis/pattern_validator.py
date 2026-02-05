"""
Pattern Validator - 模式驗證器

驗證模式定義的正確性和合理性

Author: AI Agent
Date: 2026-01-10
"""

from typing import List, Dict, Optional, Tuple
import re
import logging

from momentum.Analysis.pattern_definition import Pattern, PatternRule
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class PatternValidator:
    """
    模式驗證器
    
    驗證模式定義的語法、特徵名稱、閾值合理性
    """
    
    # 支援的運算符
    VALID_OPERATORS = ['>', '<', '>=', '<=', '==', '!=']
    
    # 特徵名稱規則：字母、數字、底線、連字號
    FEATURE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_-]*$')
    
    def __init__(self, valid_feature_names: Optional[List[str]] = None):
        """
        Args:
            valid_feature_names: 有效的特徵名稱列表（可選）
        """
        self.valid_feature_names = set(valid_feature_names) if valid_feature_names else None
        self.logger = logger
    
    def validate_pattern(self, pattern: Pattern) -> Tuple[bool, List[str]]:
        """
        驗證完整模式
        
        Args:
            pattern: 模式物件
            
        Returns:
            (是否通過驗證, 錯誤訊息列表)
        """
        errors = []
        
        # 驗證 pattern_id
        if not pattern.pattern_id or not pattern.pattern_id.strip():
            errors.append("pattern_id 不能為空")
        
        # 驗證名稱
        if not pattern.name or not pattern.name.strip():
            errors.append("name 不能為空")
        
        # 驗證規則列表
        if not pattern.rules:
            errors.append("rules 不能為空（至少需要 1 條規則）")
        else:
            # 驗證每條規則
            for i, rule in enumerate(pattern.rules, 1):
                rule_errors = self.validate_rule(rule)
                if rule_errors:
                    errors.append(f"規則 {i}: {', '.join(rule_errors)}")
        
        # 驗證狀態
        if pattern.status not in ['active', 'archived', 'testing']:
            errors.append(f"無效的 status: {pattern.status}")
        
        # 驗證效能指標
        perf_errors = self.validate_performance_metrics(pattern.performance_metrics)
        if perf_errors:
            errors.extend(perf_errors)
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            self.logger.warning(
                f"模式驗證失敗 - ID: {pattern.pattern_id}, 錯誤數: {len(errors)}"
            )
        
        return is_valid, errors
    
    def validate_rule(self, rule: PatternRule) -> List[str]:
        """
        驗證單條規則
        
        Args:
            rule: 規則物件
            
        Returns:
            錯誤訊息列表
        """
        errors = []
        
        # 驗證特徵名稱語法
        if not self.FEATURE_NAME_PATTERN.match(rule.feature):
            errors.append(f"無效的特徵名稱: {rule.feature}")
        
        # 驗證特徵是否存在（如果提供了有效特徵列表）
        if self.valid_feature_names and rule.feature not in self.valid_feature_names:
            errors.append(f"特徵不存在: {rule.feature}")
        
        # 驗證運算符
        if rule.operator not in self.VALID_OPERATORS:
            errors.append(
                f"無效的運算符: {rule.operator}, "
                f"支援: {', '.join(self.VALID_OPERATORS)}"
            )
        
        # 驗證閾值
        if not isinstance(rule.threshold, (int, float)):
            errors.append(f"閾值必須是數字: {rule.threshold}")
        elif not (-1e6 < rule.threshold < 1e6):
            errors.append(f"閾值超出合理範圍: {rule.threshold}")
        
        # 驗證描述
        if not rule.description or not rule.description.strip():
            errors.append("description 不能為空")
        
        return errors
    
    def validate_performance_metrics(self, metrics: Dict[str, float]) -> List[str]:
        """
        驗證效能指標
        
        Args:
            metrics: 效能指標字典
            
        Returns:
            錯誤訊息列表
        """
        errors = []
        
        # 必須的指標（至少要有其中一組）
        # 組 1: 傳統 ML 指標
        has_traditional = all(k in metrics for k in ['precision', 'recall', 'f1_score'])
        # 組 2: XGBoost 指標
        has_xgboost = 'cv_auc_mean' in metrics or 'train_auc' in metrics
        
        if not has_traditional and not has_xgboost:
            errors.append("必須包含效能指標（precision/recall/f1_score 或 train_auc/cv_auc_mean）")
            return errors
        
        # 驗證存在的指標範圍
        range_check_metrics = ['precision', 'recall', 'f1_score', 'train_auc', 'cv_auc_mean', 'accuracy']
        
        for metric in range_check_metrics:
            if metric in metrics:
                if not isinstance(metrics[metric], (int, float)):
                    errors.append(f"{metric} 必須是數字")
                elif not (0 <= metrics[metric] <= 1):
                    errors.append(f"{metric} 必須在 [0, 1] 範圍內: {metrics[metric]}")
        
        # cv_auc_std 可以是任意非負數
        if 'cv_auc_std' in metrics:
            if not isinstance(metrics['cv_auc_std'], (int, float)):
                errors.append("cv_auc_std 必須是數字")
            elif metrics['cv_auc_std'] < 0:
                errors.append(f"cv_auc_std 必須是非負數: {metrics['cv_auc_std']}")
        
        return errors
    
    def validate_rule_syntax(self, rule_string: str) -> Tuple[bool, str]:
        """
        驗證規則語法字串
        
        Args:
            rule_string: 規則字串 (e.g., "ema_distance_5_20 > 0.02")
            
        Returns:
            (是否有效, 錯誤訊息)
        """
        try:
            # 解析規則字串
            parts = rule_string.split()
            
            if len(parts) != 3:
                return False, "規則格式錯誤，應為: feature operator threshold"
            
            feature, operator, threshold = parts
            
            # 驗證特徵名稱
            if not self.FEATURE_NAME_PATTERN.match(feature):
                return False, f"無效的特徵名稱: {feature}"
            
            # 驗證運算符
            if operator not in self.VALID_OPERATORS:
                return False, f"無效的運算符: {operator}"
            
            # 驗證閾值
            try:
                float(threshold)
            except ValueError:
                return False, f"無效的閾值: {threshold}"
            
            return True, ""
            
        except Exception as e:
            return False, f"解析錯誤: {str(e)}"
    
    def validate_thresholds(
        self,
        rules: List[PatternRule],
        threshold_ranges: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> List[str]:
        """
        驗證閾值合理性
        
        Args:
            rules: 規則列表
            threshold_ranges: 特徵的合理範圍字典 {feature: (min, max)}
            
        Returns:
            警告訊息列表
        """
        warnings = []
        
        if not threshold_ranges:
            return warnings
        
        for rule in rules:
            if rule.feature in threshold_ranges:
                min_val, max_val = threshold_ranges[rule.feature]
                
                if rule.threshold < min_val or rule.threshold > max_val:
                    warnings.append(
                        f"{rule.feature} 的閾值 {rule.threshold} 超出合理範圍 "
                        f"[{min_val}, {max_val}]"
                    )
        
        return warnings
    
    def validate_feature_names(
        self,
        pattern: Pattern,
        available_features: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        驗證模式中的特徵是否都存在
        
        Args:
            pattern: 模式物件
            available_features: 可用的特徵列表
            
        Returns:
            (是否全部存在, 不存在的特徵列表)
        """
        pattern_features = pattern.get_feature_list()
        available_set = set(available_features)
        
        missing_features = [
            f for f in pattern_features
            if f not in available_set
        ]
        
        all_exist = len(missing_features) == 0
        
        if not all_exist:
            self.logger.warning(
                f"模式 {pattern.pattern_id} 包含不存在的特徵: {missing_features}"
            )
        
        return all_exist, missing_features
    
    def check_rule_conflicts(self, rules: List[PatternRule]) -> List[str]:
        """
        檢查規則是否有衝突
        
        Args:
            rules: 規則列表
            
        Returns:
            衝突訊息列表
        """
        conflicts = []
        
        # 按特徵分組
        feature_rules: Dict[str, List[PatternRule]] = {}
        for rule in rules:
            if rule.feature not in feature_rules:
                feature_rules[rule.feature] = []
            feature_rules[rule.feature].append(rule)
        
        # 檢查同一特徵的多個規則是否衝突
        for feature, feature_rule_list in feature_rules.items():
            if len(feature_rule_list) > 1:
                # 檢查是否有互相矛盾的規則
                for i, rule1 in enumerate(feature_rule_list):
                    for rule2 in feature_rule_list[i+1:]:
                        if self._is_conflict(rule1, rule2):
                            conflicts.append(
                                f"{feature} 的規則衝突: "
                                f"{rule1.to_condition_string()} 與 "
                                f"{rule2.to_condition_string()}"
                            )
        
        return conflicts
    
    def _is_conflict(self, rule1: PatternRule, rule2: PatternRule) -> bool:
        """檢查兩條規則是否衝突"""
        # 簡單檢查：如果一個要求 > x，另一個要求 < y，且 x >= y，則衝突
        if rule1.operator == '>' and rule2.operator == '<':
            return rule1.threshold >= rule2.threshold
        if rule1.operator == '<' and rule2.operator == '>':
            return rule2.threshold >= rule1.threshold
        
        # 其他衝突情況可以擴展
        return False
