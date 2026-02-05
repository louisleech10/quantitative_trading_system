"""
Pattern Extractor - 模式提取器

從 XGBoost 決策樹中提取可解釋的交易規則

Author: AI Agent
Date: 2026-01-10
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import logging

import xgboost as xgb

from momentum.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DecisionRule:
    """決策規則"""
    rule_id: int
    condition: str  # 例如: "ema_distance_5_20 > 0.02 AND taker_buy_ratio > 0.6"
    support: int  # 符合此規則的樣本數
    confidence: float  # 盈利概率
    lift: float  # 相對於基準的提升
    feature_conditions: List[Tuple[str, str, float]]  # [(feature, operator, threshold), ...]
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'rule_id': self.rule_id,
            'condition': self.condition,
            'support': self.support,
            'confidence': self.confidence,
            'lift': self.lift,
            'feature_conditions': [
                {'feature': f, 'operator': op, 'threshold': t}
                for f, op, t in self.feature_conditions
            ]
        }


class PatternExtractor:
    """
    模式提取器
    
    從 XGBoost 模型中提取決策規則
    """
    
    def __init__(self):
        self.logger = logger
    
    def extract_decision_rules(
        self,
        model: xgb.XGBClassifier,
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        top_n: int = 10,
        min_support: int = 10
    ) -> List[DecisionRule]:
        """
        從 XGBoost 模型提取決策規則
        
        Args:
            model: 訓練好的 XGBoost 模型
            X: 特徵矩陣
            y: 標籤數組
            feature_names: 特徵名稱列表
            top_n: 返回前 N 條規則
            min_support: 最小支持度（樣本數）
            
        Returns:
            決策規則列表
        """
        self.logger.info(f"開始提取決策規則 - 最多 {top_n} 條")
        
        # 使用樹結構提取規則
        rules = self._extract_rules_from_trees(
            model, X, y, feature_names, min_support
        )
        
        # 簡化規則（合併相似規則）
        rules = self._simplify_rules(rules)
        
        # 按 confidence * lift 排序
        rules.sort(key=lambda r: r.confidence * r.lift, reverse=True)
        
        # 返回前 N 條
        result = rules[:top_n]
        
        self.logger.info(
            f"提取完成 - 共 {len(result)} 條規則, "
            f"平均 confidence: {np.mean([r.confidence for r in result]):.4f}"
        )
        
        return result
    
    def _extract_rules_from_trees(
        self,
        model: xgb.XGBClassifier,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: List[str],
        min_support: int
    ) -> List[DecisionRule]:
        """從樹中提取規則"""
        rules = []
        
        # 獲取所有樹
        booster = model.get_booster()
        
        # 基準盈利概率
        base_prob = y.mean()
        
        # 對於每棵樹的葉子節點，提取規則
        # 這裡簡化實現：使用特徵重要性和分位數生成規則
        importance_dict = booster.get_score(importance_type='gain')
        
        # 獲取最重要的前 5 個特徵
        top_features = sorted(
            [(f"f{i}", importance_dict.get(f"f{i}", 0), feature_names[i])
             for i in range(len(feature_names))],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        rule_id = 1
        
        # 為每個重要特徵生成規則
        for xgb_fname, importance, fname in top_features:
            if importance == 0:
                continue
            
            # 獲取特徵值（支援 DataFrame 和 numpy array）
            if isinstance(X, pd.DataFrame):
                feature_values = X[fname]
            else:
                # numpy array: 找到特徵索引
                feature_idx = feature_names.index(fname)
                feature_values = pd.Series(X[:, feature_idx])
            
            # 計算該特徵的四分位數
            q25, q50, q75 = feature_values.quantile([0.25, 0.5, 0.75])
            
            # 生成 3 條規則（> q25, > q50, > q75）
            for threshold, quantile_name in [(q25, 'Q25'), (q50, 'Q50'), (q75, 'Q75')]:
                # 找出符合條件的樣本
                mask = feature_values > threshold
                support = mask.sum()
                
                if support < min_support:
                    continue
                
                # 計算盈利概率
                y_subset = y[mask]
                if len(y_subset) == 0:
                    continue
                
                confidence = y_subset.mean()
                lift = confidence / base_prob if base_prob > 0 else 1.0
                
                # 建立規則
                condition = f"{fname} > {threshold:.4f}"
                rule = DecisionRule(
                    rule_id=rule_id,
                    condition=condition,
                    support=support,
                    confidence=confidence,
                    lift=lift,
                    feature_conditions=[(fname, '>', threshold)]
                )
                rules.append(rule)
                rule_id += 1
        
        # 生成組合規則（兩個特徵的 AND 組合）
        if len(top_features) >= 2:
            for i in range(min(3, len(top_features))):
                for j in range(i + 1, min(3, len(top_features))):
                    _, _, fname1 = top_features[i]
                    _, _, fname2 = top_features[j]
                    
                    # 獲取特徵值（支援 DataFrame 和 numpy array）
                    if isinstance(X, pd.DataFrame):
                        feature1_values = X[fname1]
                        feature2_values = X[fname2]
                    else:
                        feature1_idx = feature_names.index(fname1)
                        feature2_idx = feature_names.index(fname2)
                        feature1_values = pd.Series(X[:, feature1_idx])
                        feature2_values = pd.Series(X[:, feature2_idx])
                    
                    # 使用中位數
                    threshold1 = feature1_values.quantile(0.5)
                    threshold2 = feature2_values.quantile(0.5)
                    
                    # 組合條件
                    mask = (feature1_values > threshold1) & (feature2_values > threshold2)
                    support = mask.sum()
                    
                    if support < min_support:
                        continue
                    
                    y_subset = y[mask]
                    if len(y_subset) == 0:
                        continue
                    
                    confidence = y_subset.mean()
                    lift = confidence / base_prob if base_prob > 0 else 1.0
                    
                    condition = f"{fname1} > {threshold1:.4f} AND {fname2} > {threshold2:.4f}"
                    rule = DecisionRule(
                        rule_id=rule_id,
                        condition=condition,
                        support=support,
                        confidence=confidence,
                        lift=lift,
                        feature_conditions=[
                            (fname1, '>', threshold1),
                            (fname2, '>', threshold2)
                        ]
                    )
                    rules.append(rule)
                    rule_id += 1
        
        return rules
    
    def _simplify_rules(self, rules: List[DecisionRule]) -> List[DecisionRule]:
        """
        簡化規則（移除重複或高度相似的規則）
        
        Args:
            rules: 規則列表
            
        Returns:
            簡化後的規則列表
        """
        if len(rules) <= 1:
            return rules
        
        # 按 confidence * lift 排序
        rules.sort(key=lambda r: r.confidence * r.lift, reverse=True)
        
        simplified = []
        used_features = set()
        
        for rule in rules:
            # 檢查是否已經有相似的規則
            rule_features = set(f for f, _, _ in rule.feature_conditions)
            
            # 如果特徵組合已經使用過，跳過
            if rule_features.issubset(used_features) and len(rule_features) == 1:
                continue
            
            simplified.append(rule)
            used_features.update(rule_features)
            
            # 限制最多 20 條規則
            if len(simplified) >= 20:
                break
        
        return simplified
    
    def rank_rules_by_importance(
        self,
        rules: List[DecisionRule],
        importance_weights: Optional[Dict[str, float]] = None
    ) -> List[DecisionRule]:
        """
        根據重要性排序規則
        
        Args:
            rules: 規則列表
            importance_weights: 特徵重要性權重（可選）
            
        Returns:
            排序後的規則列表
        """
        if importance_weights is None:
            # 使用 confidence * lift 排序
            rules.sort(key=lambda r: r.confidence * r.lift, reverse=True)
        else:
            # 使用特徵重要性加權排序
            def rule_score(rule: DecisionRule) -> float:
                # 基礎分數：confidence * lift
                base_score = rule.confidence * rule.lift
                
                # 特徵重要性加權
                feature_weight = sum(
                    importance_weights.get(f, 0)
                    for f, _, _ in rule.feature_conditions
                ) / len(rule.feature_conditions)
                
                return base_score * (1 + feature_weight)
            
            rules.sort(key=rule_score, reverse=True)
        
        return rules
