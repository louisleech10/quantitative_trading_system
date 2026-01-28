"""
SHAP Analyzer - 特徵貢獻解釋引擎

提供 XGBoost 模型的 SHAP 全局與單案例解釋

Author: AI Agent
Date: 2026-01-28
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from api.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GlobalSHAPFeatureImportance:
    """全局 SHAP 特徵重要性"""
    feature: str
    mean_abs_shap: float
    mean_shap: float
    rank: int


@dataclass
class SHAPSummaryPoint:
    """Beeswarm 點資料"""
    feature: str
    value: float
    shap_value: float


@dataclass
class GlobalSHAPResult:
    """全局 SHAP 結果"""
    expected_value: float
    feature_importance_shap: List[GlobalSHAPFeatureImportance]
    top_positive_features: List[str]
    top_negative_features: List[str]
    sample_size: int
    summary_points: Optional[List[SHAPSummaryPoint]] = None


@dataclass
class SingleCaseContribution:
    """單案例 SHAP 貢獻"""
    feature: str
    value: float
    shap_value: float
    contribution_pct: float


@dataclass
class SingleCaseSHAPResult:
    """單案例 SHAP 結果"""
    predicted_proba: float
    expected_value: float
    contributions: List[SingleCaseContribution]


@dataclass
class InteractionEffect:
    """特徵交互效應"""
    feature_pair: Tuple[str, str]
    mean_abs_interaction: float


class SHAPAnalyzer:
    """
    SHAP 分析器

    提供全局特徵重要性、單案例解釋與交互效應分析
    """

    def __init__(self):
        self.logger = logger

    def _load_shap(self):
        try:
            import shap  # type: ignore
            return shap
        except Exception as e:
            raise ImportError(
                "缺少相依套件 shap，請先安裝：pip install shap"
            ) from e

    def build_explainer(self, model):
        """建立並返回 SHAP TreeExplainer"""
        shap = self._load_shap()
        return shap.TreeExplainer(model)

    def analyze_global(
        self,
        model,
        X: Union[pd.DataFrame, np.ndarray],
        sample_size: int = 100,
        explainer=None,
        include_summary_points: bool = True
    ) -> GlobalSHAPResult:
        """計算全局 SHAP 重要性"""
        if len(X) == 0:
            raise ValueError("X 為空，無法進行 SHAP 分析")

        if isinstance(X, pd.DataFrame):
            feature_names = X.columns.tolist()
            X_values = X
        else:
            if hasattr(model, "feature_names_in_"):
                feature_names = list(model.feature_names_in_)
            else:
                raise ValueError("X 為 numpy array 時必須提供特徵名稱")
            X_values = pd.DataFrame(X, columns=feature_names)

        if sample_size < 1:
            raise ValueError("sample_size 必須大於 0")

        if len(X_values) > sample_size:
            X_sample = X_values.sample(sample_size, random_state=42)
        else:
            X_sample = X_values

        explainer = explainer or self.build_explainer(model)
        shap_values = explainer.shap_values(X_sample)
        expected_value = explainer.expected_value

        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        if isinstance(expected_value, (list, tuple, np.ndarray)):
            expected_value = float(expected_value[1] if len(expected_value) > 1 else expected_value[0])
        else:
            expected_value = float(expected_value)

        shap_array = np.array(shap_values)
        mean_abs = np.mean(np.abs(shap_array), axis=0)
        mean_shap = np.mean(shap_array, axis=0)

        importance_list = []
        for idx, feature in enumerate(feature_names):
            importance_list.append((feature, float(mean_abs[idx]), float(mean_shap[idx])))

        importance_list.sort(key=lambda x: x[1], reverse=True)

        feature_importance = [
            GlobalSHAPFeatureImportance(
                feature=feature,
                mean_abs_shap=mean_abs_shap,
                mean_shap=mean_shap_val,
                rank=rank + 1
            )
            for rank, (feature, mean_abs_shap, mean_shap_val) in enumerate(importance_list)
        ]

        top_positive = [f for f in feature_importance if f.mean_shap > 0]
        top_negative = [f for f in feature_importance if f.mean_shap < 0]

        top_positive_features = [f.feature for f in top_positive[:5]]
        top_negative_features = [f.feature for f in top_negative[:5]]

        summary_points = None
        if include_summary_points:
            summary_points = []
            for row_idx in range(shap_array.shape[0]):
                for col_idx, feature in enumerate(feature_names):
                    summary_points.append(
                        SHAPSummaryPoint(
                            feature=feature,
                            value=float(X_sample.iloc[row_idx, col_idx]),
                            shap_value=float(shap_array[row_idx, col_idx])
                        )
                    )

        self.logger.info(
            f"SHAP 全局分析完成 - 樣本數: {len(X_sample)}, 特徵數: {len(feature_names)}"
        )

        return GlobalSHAPResult(
            expected_value=expected_value,
            feature_importance_shap=feature_importance,
            top_positive_features=top_positive_features,
            top_negative_features=top_negative_features,
            sample_size=len(X_sample),
            summary_points=summary_points
        )

    def explain_single_case(
        self,
        model,
        case_features: Union[pd.Series, pd.DataFrame, np.ndarray, List[float]],
        feature_names: Optional[List[str]] = None,
        explainer=None
    ) -> SingleCaseSHAPResult:
        """單筆案例解釋"""
        if isinstance(case_features, pd.DataFrame):
            if len(case_features) != 1:
                raise ValueError("case_features DataFrame 必須只有一列")
            case_row = case_features.iloc[0]
        elif isinstance(case_features, pd.Series):
            case_row = case_features
        else:
            if feature_names is None:
                raise ValueError("使用 numpy 或 list 時必須提供 feature_names")
            case_row = pd.Series(case_features, index=feature_names)

        if feature_names is None:
            feature_names = list(case_row.index)

        case_row = case_row.reindex(feature_names)
        if case_row.isna().any():
            missing = case_row.index[case_row.isna()].tolist()
            raise ValueError(f"case_features 缺少特徵: {missing}")

        case_df = case_row.to_frame().T

        explainer = explainer or self.build_explainer(model)
        shap_values = explainer.shap_values(case_df)
        expected_value = explainer.expected_value

        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        if isinstance(expected_value, (list, tuple, np.ndarray)):
            expected_value = float(expected_value[1] if len(expected_value) > 1 else expected_value[0])
        else:
            expected_value = float(expected_value)

        shap_array = np.array(shap_values)[0]
        abs_sum = float(np.sum(np.abs(shap_array)))

        contributions = []
        for idx, feature in enumerate(feature_names):
            shap_val = float(shap_array[idx])
            contribution_pct = (abs(shap_val) / abs_sum * 100.0) if abs_sum > 0 else 0.0
            contributions.append(
                SingleCaseContribution(
                    feature=feature,
                    value=float(case_row.iloc[idx]),
                    shap_value=shap_val,
                    contribution_pct=float(contribution_pct)
                )
            )

        contributions.sort(key=lambda x: abs(x.shap_value), reverse=True)

        predicted_proba = float(model.predict_proba(case_df)[:, 1][0])

        self.logger.info("SHAP 單案例分析完成")

        return SingleCaseSHAPResult(
            predicted_proba=predicted_proba,
            expected_value=expected_value,
            contributions=contributions
        )

    def get_interaction_effects(
        self,
        model,
        X: Union[pd.DataFrame, np.ndarray],
        feature_pairs: Sequence[Tuple[str, str]],
        explainer=None
    ) -> List[InteractionEffect]:
        """計算指定特徵對的交互效應"""
        if len(feature_pairs) == 0:
            return []

        if isinstance(X, pd.DataFrame):
            feature_names = X.columns.tolist()
            X_values = X
        else:
            if hasattr(model, "feature_names_in_"):
                feature_names = list(model.feature_names_in_)
            else:
                raise ValueError("X 為 numpy array 時必須提供特徵名稱")
            X_values = pd.DataFrame(X, columns=feature_names)

        explainer = explainer or self.build_explainer(model)

        try:
            shap_interactions = explainer.shap_interaction_values(X_values)
        except Exception as e:
            raise ValueError(f"無法計算交互效應: {str(e)}") from e

        if isinstance(shap_interactions, list):
            shap_interactions = shap_interactions[1] if len(shap_interactions) > 1 else shap_interactions[0]

        interaction_array = np.array(shap_interactions)

        effects: List[InteractionEffect] = []
        for feature_a, feature_b in feature_pairs:
            if feature_a not in feature_names or feature_b not in feature_names:
                raise ValueError(f"交互特徵不存在: {feature_a}, {feature_b}")
            idx_a = feature_names.index(feature_a)
            idx_b = feature_names.index(feature_b)
            mean_abs_interaction = float(np.mean(np.abs(interaction_array[:, idx_a, idx_b])))
            effects.append(
                InteractionEffect(
                    feature_pair=(feature_a, feature_b),
                    mean_abs_interaction=mean_abs_interaction
                )
            )

        return effects
