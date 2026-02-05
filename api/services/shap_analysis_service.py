"""
SHAP Analysis Service - SHAP 解釋服務

提供 XGBoost 模型的全局與單案例 SHAP 解釋

Author: AI Agent
Date: 2026-01-28
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from api.core.logging import get_logger
from momentum.factories import (
    create_feature_storage,
    create_model_storage,
    create_xgboost_analyzer,
)

logger = get_logger(__name__)


class SHAPAnalysisService:
    """SHAP 解釋服務"""

    def __init__(self):
        self.model_storage = create_model_storage()
        self.feature_storage = create_feature_storage()
        self.logger = logger

    def _load_model_data(self, task_result: Dict) -> Dict:
        model_path = task_result.get("model_path")
        if not model_path:
            raise ValueError("任務結果缺少 model_path")

        model_id = Path(model_path).stem
        return self.model_storage.load_model_from_pickle(model_id)

    def _build_sample_from_task(
        self,
        task_result: Dict,
        sample_size: int
    ) -> Tuple[pd.DataFrame, List[str], List[str]]:
        shap_sample = task_result.get("shap_sample")
        if shap_sample:
            feature_names = shap_sample.get("feature_names", [])
            case_ids = shap_sample.get("case_ids", [])
            samples = shap_sample.get("samples", [])
            if not feature_names or not samples:
                raise ValueError("shap_sample 資料不完整")

            X_all = pd.DataFrame(samples, columns=feature_names)
            if sample_size < len(X_all):
                rng = np.random.default_rng(42)
                indices = rng.choice(len(X_all), size=sample_size, replace=False)
                X_sample = X_all.iloc[indices]
                case_ids_sample = [case_ids[i] for i in indices]
            else:
                X_sample = X_all
                case_ids_sample = case_ids

            return X_sample, feature_names, case_ids_sample

        task_case_id = task_result.get("case_id")
        if task_case_id:
            features_df, feature_names, _ = self.feature_storage.load_features_from_hdf5(task_case_id)
            if len(features_df) == 0:
                raise ValueError("特徵資料為空")
            rng = np.random.default_rng(42)
            sample_size = min(sample_size, len(features_df))
            indices = rng.choice(len(features_df), size=sample_size, replace=False)
            X_sample = features_df.iloc[indices][feature_names]
            case_ids_sample = [f"{task_case_id}_{i}" for i in indices]
            return X_sample, feature_names, case_ids_sample

        raise ValueError("無法取得 SHAP 取樣資料，請重新執行分析任務")

    def analyze_global(
        self,
        task_result: Dict,
        sample_size: int,
        include_summary_points: bool,
        feature_pairs: Optional[List[Tuple[str, str]]] = None
    ):
        model_data = self._load_model_data(task_result)
        model = model_data["model"]

        X_sample, feature_names, _ = self._build_sample_from_task(task_result, sample_size)

        analyzer = create_xgboost_analyzer()
        analyzer.model = model
        analyzer.feature_names = feature_names

        global_result = analyzer.analyze_shap_global(
            X=X_sample,
            sample_size=sample_size,
            include_summary_points=include_summary_points
        )

        interaction_effects = None
        if feature_pairs:
            interaction_effects = analyzer.get_shap_interaction_effects(
                X=X_sample,
                feature_pairs=feature_pairs
            )

        return global_result, interaction_effects

    def explain_single_case(
        self,
        task_result: Dict,
        case_id: str
    ):
        model_data = self._load_model_data(task_result)
        model = model_data["model"]

        X_sample, feature_names, case_ids = self._build_sample_from_task(task_result, sample_size=200)

        if case_id in case_ids:
            row_idx = case_ids.index(case_id)
            case_features = X_sample.iloc[row_idx]
        else:
            task_case_id = task_result.get("case_id")
            if task_case_id and case_id.startswith(f"{task_case_id}_"):
                suffix = case_id.replace(f"{task_case_id}_", "", 1)
                if suffix.isdigit():
                    row_idx = int(suffix)
                    features_df, feature_names, _ = self.feature_storage.load_features_from_hdf5(task_case_id)
                    if row_idx >= len(features_df):
                        raise ValueError("case_id 超出特徵資料範圍")
                    case_features = features_df.loc[row_idx, feature_names]
                else:
                    raise ValueError("case_id 格式無法解析")
            else:
                raise ValueError("case_id 不在 SHAP 取樣資料中")

        analyzer = create_xgboost_analyzer()
        analyzer.model = model
        analyzer.feature_names = feature_names

        return analyzer.explain_shap_single_case(case_features, feature_names=feature_names)
