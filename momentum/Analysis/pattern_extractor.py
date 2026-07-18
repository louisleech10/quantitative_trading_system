"""
Pattern Extractor - 模式提取器

從 XGBoost 決策樹中提取可解釋的交易規則

LA-2 B3：門檻 / base_prob / confidence / lift 一律 train-mask + train-y-only；
必填 SplitPlan(split_label='train')，缺或非 train → fail-closed。

Author: AI Agent
Date: 2026-01-10
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import xgboost as xgb

from momentum.core.contracts import SplitPlan, canonical_split_plan_hash
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class PatternSplitRequiredError(ValueError):
    """extract_decision_rules 缺 SplitPlan 或 split_label≠train。"""


class PatternPlanIdentityError(ValueError):
    """pattern/model plan_hash 不一致（fail-closed）。"""


@dataclass
class DecisionRule:
    """決策規則"""
    rule_id: int
    condition: str  # 例如: "ema_distance_5_20 > 0.02 AND taker_buy_ratio > 0.6"
    support: int  # 符合此規則的樣本數（train 內）
    confidence: float  # 盈利概率（train-y-only）
    lift: float  # 相對於 train base_prob 的提升
    feature_conditions: List[Tuple[str, str, float]]  # [(feature, operator, threshold), ...]
    # train 門檻（分位值）；晉升時 OOT lift 可另計
    oot_lift: Optional[float] = None

    def to_dict(self) -> Dict:
        """轉換為字典"""
        out = {
            "rule_id": self.rule_id,
            "condition": self.condition,
            "support": self.support,
            "confidence": self.confidence,
            "lift": self.lift,
            "feature_conditions": [
                {"feature": f, "operator": op, "threshold": t}
                for f, op, t in self.feature_conditions
            ],
        }
        if self.oot_lift is not None:
            out["oot_lift"] = self.oot_lift
        return out


class PatternExtractor:
    """
    模式提取器

    從 XGBoost 模型中提取決策規則（C-2 promotion-train-mask）。
    """

    def __init__(self) -> None:
        self.logger = logger
        self._last_split_plan_hash: Optional[str] = None

    def extract_decision_rules(
        self,
        model: xgb.XGBClassifier,
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        top_n: int = 10,
        min_support: int = 10,
        *,
        split: Optional[SplitPlan] = None,
        expected_plan_hash: Optional[str] = None,
        oot_split: Optional[SplitPlan] = None,
    ) -> List[DecisionRule]:
        """
        從 XGBoost 模型提取決策規則。

        Args:
            model: 訓練好的 XGBoost 模型
            X: 特徵矩陣（全樣本；內部以 train-mask 切片）
            y: 標籤數組
            feature_names: 特徵名稱列表
            top_n: 返回前 N 條規則
            min_support: 最小支持度（train 樣本數）
            split: 必填 SplitPlan，且 split_label 必須為 'train'
            expected_plan_hash: 若提供，與 split hash 比對（plan identity）
            oot_split: 可選 OOT plan；若提供則另算 oot_lift（晉升用）

        Returns:
            決策規則列表
        """
        if split is None:
            raise PatternSplitRequiredError(
                "extract_decision_rules requires split: SplitPlan (fail-closed)"
            )
        if not isinstance(split, SplitPlan):
            raise PatternSplitRequiredError(
                f"split must be SplitPlan, got {type(split).__name__}"
            )
        if str(split.split_label) != "train":
            raise PatternSplitRequiredError(
                f"split_label must be 'train', got {split.split_label!r}"
            )

        plan_hash = canonical_split_plan_hash(split)
        if expected_plan_hash is not None and plan_hash != expected_plan_hash:
            raise PatternPlanIdentityError(
                f"plan identity mismatch: got {plan_hash[:16]}… "
                f"expected {expected_plan_hash[:16]}…"
            )
        self._last_split_plan_hash = plan_hash

        n = len(y) if not isinstance(y, pd.Series) else len(y)
        train_idx = np.asarray(split.row_index, dtype=int)
        if train_idx.size == 0:
            raise PatternSplitRequiredError("train split.row_index is empty")
        if train_idx.min() < 0 or train_idx.max() >= n:
            raise PatternSplitRequiredError(
                f"train row_index out of bounds for n={n}"
            )

        # train-mask 切片（固定絕對 cutoff 的 row_index，禁 random/比例重切）
        if isinstance(X, pd.DataFrame):
            X_train = X.iloc[train_idx]
        else:
            X_train = np.asarray(X)[train_idx]
        y_train = np.asarray(y)[train_idx]

        self.logger.info(
            "開始提取決策規則 - train_n=%d top_n=%d plan_hash=%s…",
            len(y_train),
            top_n,
            plan_hash[:12],
        )

        rules = self._extract_rules_from_trees(
            model, X_train, y_train, feature_names, min_support
        )

        # 可選：OOT lift（晉升用；不影響 train-y confidence）
        if oot_split is not None and str(oot_split.split_label) in {"test", "val"}:
            oot_idx = np.asarray(oot_split.row_index, dtype=int)
            if oot_idx.size > 0 and oot_idx.max() < n:
                if isinstance(X, pd.DataFrame):
                    X_oot = X.iloc[oot_idx]
                else:
                    X_oot = np.asarray(X)[oot_idx]
                y_oot = np.asarray(y)[oot_idx]
                base_oot = float(np.mean(y_oot)) if len(y_oot) else 0.0
                for rule in rules:
                    mask = self._apply_conditions(X_oot, feature_names, rule.feature_conditions)
                    if mask.sum() == 0:
                        rule.oot_lift = 0.0
                        continue
                    conf_oot = float(np.mean(np.asarray(y_oot)[mask]))
                    rule.oot_lift = (
                        conf_oot / base_oot if base_oot > 0 else 1.0
                    )

        rules = self._simplify_rules(rules)
        rules.sort(key=lambda r: r.confidence * r.lift, reverse=True)
        result = rules[:top_n]

        self.logger.info(
            "提取完成 - 共 %d 條規則, 平均 confidence: %.4f",
            len(result),
            float(np.mean([r.confidence for r in result])) if result else 0.0,
        )
        return result

    def _apply_conditions(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        feature_names: List[str],
        conditions: List[Tuple[str, str, float]],
    ) -> np.ndarray:
        """AND 連結合 feature_conditions；空集 → 全 False。"""
        if not conditions:
            n = len(X) if not isinstance(X, np.ndarray) else X.shape[0]
            return np.zeros(n, dtype=bool)
        mask = np.ones(
            len(X) if isinstance(X, pd.DataFrame) else X.shape[0], dtype=bool
        )
        for fname, op, thr in conditions:
            if isinstance(X, pd.DataFrame):
                vals = X[fname].to_numpy(dtype=float)
            else:
                idx = feature_names.index(fname)
                vals = np.asarray(X[:, idx], dtype=float)
            if op == ">":
                mask &= vals > thr
            elif op == ">=":
                mask &= vals >= thr
            elif op == "<":
                mask &= vals < thr
            elif op == "<=":
                mask &= vals <= thr
            else:
                raise ValueError(f"unsupported operator: {op}")
        return mask

    def _extract_rules_from_trees(
        self,
        model: xgb.XGBClassifier,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: List[str],
        min_support: int,
    ) -> List[DecisionRule]:
        """從樹中提取規則（X/y 已是 train-only）。"""
        rules: List[DecisionRule] = []
        booster = model.get_booster()

        # train-y-only base_prob
        base_prob = float(np.mean(y)) if len(y) else 0.0

        importance_dict = booster.get_score(importance_type="gain")
        top_features = sorted(
            [
                (f"f{i}", importance_dict.get(f"f{i}", 0), feature_names[i])
                for i in range(len(feature_names))
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        rule_id = 1
        for _xgb_fname, importance, fname in top_features:
            if importance == 0:
                continue
            if isinstance(X, pd.DataFrame):
                feature_values = X[fname]
            else:
                feature_idx = feature_names.index(fname)
                feature_values = pd.Series(X[:, feature_idx])

            # train-mask 分位門檻
            q25, q50, q75 = feature_values.quantile([0.25, 0.5, 0.75])
            for threshold, _qname in [(q25, "Q25"), (q50, "Q50"), (q75, "Q75")]:
                mask = feature_values > threshold
                support = int(mask.sum())
                if support < min_support:
                    continue
                y_subset = y[mask.to_numpy() if hasattr(mask, "to_numpy") else mask]
                if len(y_subset) == 0:
                    continue
                confidence = float(np.mean(y_subset))
                lift = confidence / base_prob if base_prob > 0 else 1.0
                thr = float(threshold)
                condition = f"{fname} > {thr:.4f}"
                rules.append(
                    DecisionRule(
                        rule_id=rule_id,
                        condition=condition,
                        support=support,
                        confidence=confidence,
                        lift=lift,
                        feature_conditions=[(fname, ">", thr)],
                    )
                )
                rule_id += 1

        if len(top_features) >= 2:
            for i in range(min(3, len(top_features))):
                for j in range(i + 1, min(3, len(top_features))):
                    _, _, fname1 = top_features[i]
                    _, _, fname2 = top_features[j]
                    if isinstance(X, pd.DataFrame):
                        feature1_values = X[fname1]
                        feature2_values = X[fname2]
                    else:
                        feature1_values = pd.Series(X[:, feature_names.index(fname1)])
                        feature2_values = pd.Series(X[:, feature_names.index(fname2)])
                    threshold1 = float(feature1_values.quantile(0.5))
                    threshold2 = float(feature2_values.quantile(0.5))
                    mask = (feature1_values > threshold1) & (
                        feature2_values > threshold2
                    )
                    support = int(mask.sum())
                    if support < min_support:
                        continue
                    y_subset = y[mask.to_numpy() if hasattr(mask, "to_numpy") else mask]
                    if len(y_subset) == 0:
                        continue
                    confidence = float(np.mean(y_subset))
                    lift = confidence / base_prob if base_prob > 0 else 1.0
                    condition = (
                        f"{fname1} > {threshold1:.4f} AND "
                        f"{fname2} > {threshold2:.4f}"
                    )
                    rules.append(
                        DecisionRule(
                            rule_id=rule_id,
                            condition=condition,
                            support=support,
                            confidence=confidence,
                            lift=lift,
                            feature_conditions=[
                                (fname1, ">", threshold1),
                                (fname2, ">", threshold2),
                            ],
                        )
                    )
                    rule_id += 1

        return rules

    def _simplify_rules(self, rules: List[DecisionRule]) -> List[DecisionRule]:
        """簡化規則（移除重複或高度相似的規則）。"""
        if len(rules) <= 1:
            return rules
        rules.sort(key=lambda r: r.confidence * r.lift, reverse=True)
        simplified: List[DecisionRule] = []
        used_features: set = set()
        for rule in rules:
            rule_features = set(f for f, _, _ in rule.feature_conditions)
            if rule_features.issubset(used_features) and len(rule_features) == 1:
                continue
            simplified.append(rule)
            used_features.update(rule_features)
            if len(simplified) >= 20:
                break
        return simplified

    def rank_rules_by_importance(
        self,
        rules: List[DecisionRule],
        importance_weights: Optional[Dict[str, float]] = None,
    ) -> List[DecisionRule]:
        """根據重要性排序規則。"""
        if importance_weights is None:
            rules.sort(key=lambda r: r.confidence * r.lift, reverse=True)
        else:

            def rule_score(rule: DecisionRule) -> float:
                base_score = rule.confidence * rule.lift
                feature_weight = sum(
                    importance_weights.get(f, 0)
                    for f, _, _ in rule.feature_conditions
                ) / max(1, len(rule.feature_conditions))
                return base_score * (1 + feature_weight)

            rules.sort(key=rule_score, reverse=True)
        return rules
