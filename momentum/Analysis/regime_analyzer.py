"""
Regime Analyzer - 市場體制分析

分析模型在不同 Market Phase 下的表現

Author: AI Agent
Date: 2026-01-28
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import roc_auc_score

from api.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PhaseMetrics:
    """單一市場體制指標"""
    phase: str
    support: int
    auc: Optional[float]
    precision_at_10: Optional[float]
    avg_pred_proba: Optional[float]
    recommendation: str
    note: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "phase": self.phase,
            "support": int(self.support),
            "auc": None if self.auc is None else float(self.auc),
            "precision_at_10": None if self.precision_at_10 is None else float(self.precision_at_10),
            "avg_pred_proba": None if self.avg_pred_proba is None else float(self.avg_pred_proba),
            "recommendation": self.recommendation,
            "note": self.note
        }


@dataclass
class RegimeReport:
    """市場體制分析報告"""
    overall_auc: Optional[float]
    phase_metrics: List[PhaseMetrics]
    trading_rules: Dict[str, Dict[str, Optional[float]]]

    def to_dict(self) -> Dict:
        return {
            "overall_auc": None if self.overall_auc is None else float(self.overall_auc),
            "phase_metrics": [m.to_dict() for m in self.phase_metrics],
            "trading_rules": self.trading_rules
        }


class RegimeAnalyzer:
    """市場體制分析器"""

    DEFAULT_PHASES = [
        "EXTREME_FEAR",
        "FEAR",
        "NEUTRAL",
        "GREED",
        "EXTREME_GREED"
    ]

    def __init__(self, min_samples: int = 50):
        self.min_samples = min_samples
        self.logger = logger

    def analyze_by_phase(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        market_phases: List[str],
        phase_order: Optional[List[str]] = None,
        precision_k: int = 10,
        target_precision: float = 0.75
    ) -> RegimeReport:
        """依市場體制分析模型表現"""
        y_true = np.asarray(y_true)
        y_pred_proba = np.asarray(y_pred_proba)

        if len(y_true) != len(y_pred_proba) or len(y_true) != len(market_phases):
            raise ValueError("y_true、y_pred_proba、market_phases 長度不一致")

        phases = self._resolve_phases(market_phases, phase_order)
        overall_auc = self._safe_auc(y_true, y_pred_proba)

        phase_metrics: List[PhaseMetrics] = []
        for phase in phases:
            mask = np.array([p == phase for p in market_phases])
            support = int(mask.sum())

            if support < self.min_samples:
                phase_metrics.append(
                    PhaseMetrics(
                        phase=phase,
                        support=support,
                        auc=None,
                        precision_at_10=None,
                        avg_pred_proba=None,
                        recommendation="不建議交易（樣本不足）",
                        note="樣本不足"
                    )
                )
                continue

            y_phase = y_true[mask]
            proba_phase = y_pred_proba[mask]
            auc = self._safe_auc(y_phase, proba_phase)
            precision_at_10 = self._precision_at_k(y_phase, proba_phase, precision_k)
            avg_pred_proba = float(np.mean(proba_phase)) if proba_phase.size > 0 else None

            recommendation = self._build_recommendation(
                auc=auc,
                precision_at_10=precision_at_10,
                target_precision=target_precision
            )

            phase_metrics.append(
                PhaseMetrics(
                    phase=phase,
                    support=support,
                    auc=auc,
                    precision_at_10=precision_at_10,
                    avg_pred_proba=avg_pred_proba,
                    recommendation=recommendation
                )
            )

        trading_rules = self.get_phase_thresholds(
            y_true=y_true,
            y_pred_proba=y_pred_proba,
            market_phases=market_phases,
            phase_order=phases,
            target_precision=target_precision
        )

        return RegimeReport(
            overall_auc=overall_auc,
            phase_metrics=phase_metrics,
            trading_rules=trading_rules
        )

    def get_phase_thresholds(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        market_phases: List[str],
        phase_order: Optional[List[str]] = None,
        target_precision: float = 0.75
    ) -> Dict[str, Dict[str, Optional[float]]]:
        """取得各體制的建議閾值"""
        phases = self._resolve_phases(market_phases, phase_order)
        thresholds: Dict[str, Dict[str, Optional[float]]] = {}

        for phase in phases:
            mask = np.array([p == phase for p in market_phases])
            support = int(mask.sum())
            if support < self.min_samples:
                thresholds[phase] = {
                    "threshold": None,
                    "position_size": "skip"
                }
                continue

            y_phase = y_true[mask]
            proba_phase = y_pred_proba[mask]
            threshold = self._find_threshold_for_precision(
                y_phase,
                proba_phase,
                target_precision
            )

            position_size = self._position_size_from_threshold(threshold, target_precision)
            thresholds[phase] = {
                "threshold": threshold,
                "position_size": position_size
            }

        return thresholds

    def _resolve_phases(self, market_phases: List[str], phase_order: Optional[List[str]]) -> List[str]:
        if phase_order:
            return phase_order

        if market_phases:
            # 使用輸入順序去重，確保實際出現的 phase 排在前面
            ordered = list(dict.fromkeys(market_phases))
            return ordered

        return list(self.DEFAULT_PHASES)

    def _safe_auc(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> Optional[float]:
        if np.unique(y_true).size < 2:
            return None
        return float(roc_auc_score(y_true, y_pred_proba))

    def _precision_at_k(self, y_true: np.ndarray, y_pred_proba: np.ndarray, k_pct: int) -> Optional[float]:
        if y_true.size == 0:
            return None

        n_top = max(1, int(len(y_true) * k_pct / 100))
        order = np.argsort(y_pred_proba)[-n_top:]
        precision = float(np.mean(y_true[order])) if n_top > 0 else None
        return precision

    def _find_threshold_for_precision(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        target_precision: float
    ) -> Optional[float]:
        if y_true.size == 0:
            return None

        order = np.argsort(y_pred_proba)[::-1]
        y_sorted = y_true[order]
        proba_sorted = y_pred_proba[order]

        positives = 0
        total = 0
        candidate_threshold = None

        for idx, label in enumerate(y_sorted):
            total += 1
            positives += int(label)
            precision = positives / total if total > 0 else 0.0
            if precision >= target_precision:
                candidate_threshold = float(proba_sorted[idx])

        return candidate_threshold

    def _position_size_from_threshold(self, threshold: Optional[float], target_precision: float) -> str:
        if threshold is None:
            return "skip"
        if target_precision >= 0.8:
            return "large"
        if target_precision >= 0.7:
            return "medium"
        return "small"

    def _build_recommendation(
        self,
        auc: Optional[float],
        precision_at_10: Optional[float],
        target_precision: float
    ) -> str:
        if auc is None or precision_at_10 is None:
            return "不建議交易"

        if precision_at_10 >= target_precision and auc >= 0.6:
            return "優先交易"
        if auc >= 0.55:
            return "小量交易"
        return "不建議交易"
