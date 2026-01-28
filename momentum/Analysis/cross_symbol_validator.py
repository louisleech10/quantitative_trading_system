"""
Cross Symbol Validator - 跨幣種泛化驗證

Author: AI Agent
Date: 2026-01-29
"""

from dataclasses import dataclass
from typing import Dict, Optional, List

import numpy as np
import xgboost as xgb
from sklearn.metrics import roc_auc_score

from api.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CrossSymbolValidationResult:
    """跨幣種驗證結果"""
    source_symbol: str
    target_symbol: str
    source_auc: float
    target_auc: float
    generalization_gap: float
    verdict: str

    def to_dict(self) -> Dict:
        return {
            "source_symbol": self.source_symbol,
            "target_symbol": self.target_symbol,
            "source_auc": self.source_auc,
            "target_auc": self.target_auc,
            "generalization_gap": self.generalization_gap,
            "verdict": self.verdict
        }


class CrossSymbolValidator:
    """跨幣種泛化驗證器"""

    def __init__(self, params: Optional[Dict] = None):
        self.default_params = {
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "max_depth": 5,
            "learning_rate": 0.05,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": 0
        }
        self.params = {**self.default_params, **(params or {})}

    def validate_cross_symbol(
        self,
        X_train_source: np.ndarray,
        y_train_source: np.ndarray,
        X_test_target: np.ndarray,
        y_test_target: np.ndarray,
        source_symbol: str,
        target_symbol: str
    ) -> CrossSymbolValidationResult:
        """
        用來源幣訓練，目標幣測試
        """
        if len(X_train_source) == 0 or len(X_test_target) == 0:
            raise ValueError("訓練或測試資料為空")
        if len(X_train_source) != len(y_train_source):
            raise ValueError("訓練資料長度不一致")
        if len(X_test_target) != len(y_test_target):
            raise ValueError("測試資料長度不一致")

        model = xgb.XGBClassifier(**self.params)
        model.fit(X_train_source, y_train_source, verbose=False)

        source_pred = model.predict_proba(X_train_source)[:, 1]
        target_pred = model.predict_proba(X_test_target)[:, 1]

        source_auc = self._safe_auc(y_train_source, source_pred)
        target_auc = self._safe_auc(y_test_target, target_pred)

        if np.isnan(source_auc) or np.isnan(target_auc):
            generalization_gap = float("nan")
        else:
            generalization_gap = float(source_auc - target_auc)

        verdict = self._get_verdict(generalization_gap)

        logger.info(
            f"跨幣種驗證完成 - {source_symbol}->{target_symbol}, "
            f"source_auc={source_auc:.4f}, target_auc={target_auc:.4f}, "
            f"gap={generalization_gap:.4f}, verdict={verdict}"
        )

        return CrossSymbolValidationResult(
            source_symbol=source_symbol,
            target_symbol=target_symbol,
            source_auc=float(source_auc) if not np.isnan(source_auc) else 0.0,
            target_auc=float(target_auc) if not np.isnan(target_auc) else 0.0,
            generalization_gap=float(generalization_gap) if not np.isnan(generalization_gap) else 0.0,
            verdict=verdict
        )

    def run_leave_one_symbol_out(
        self,
        symbols: List[str],
        X_by_symbol: Dict[str, np.ndarray],
        y_by_symbol: Dict[str, np.ndarray]
    ) -> List[CrossSymbolValidationResult]:
        """
        多幣種 Leave-One-Out 驗證
        """
        results: List[CrossSymbolValidationResult] = []

        for target_symbol in symbols:
            train_symbols = [s for s in symbols if s != target_symbol]
            if not train_symbols:
                continue

            X_train = np.vstack([X_by_symbol[s] for s in train_symbols])
            y_train = np.concatenate([y_by_symbol[s] for s in train_symbols])
            X_test = X_by_symbol[target_symbol]
            y_test = y_by_symbol[target_symbol]

            result = self.validate_cross_symbol(
                X_train_source=X_train,
                y_train_source=y_train,
                X_test_target=X_test,
                y_test_target=y_test,
                source_symbol="_".join(train_symbols),
                target_symbol=target_symbol
            )
            results.append(result)

        return results

    def _safe_auc(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        if len(np.unique(y_true)) < 2:
            logger.warning("AUC 計算失敗：只有單一類別")
            return float("nan")
        return float(roc_auc_score(y_true, y_pred_proba))

    def _get_verdict(self, gap: float) -> str:
        if np.isnan(gap):
            return "unknown"
        if gap < 0.05:
            return "good"
        if gap < 0.15:
            return "moderate"
        return "poor"
