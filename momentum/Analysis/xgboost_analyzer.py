"""
XGBoost Analyzer - 特徵重要性分析引擎

使用 XGBoost 分析特徵重要性，找出關鍵交易模式

Author: AI Agent
Date: 2026-01-10
Updated: 2026-01-28 - 新增 OOT 驗證功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
import logging

import xgboost as xgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
from sklearn.metrics import precision_recall_curve, auc

from api.core.logging import get_logger
from momentum.Analysis.calibration_analyzer import CalibrationAnalyzer, CalibrationMetrics, CalibrationCurveData
from momentum.Analysis.time_splitter import PurgedTimeSeriesSplit

logger = get_logger(__name__)


# ==================== OOT 驗證相關資料結構 ====================

@dataclass
class OOTValidationResult:
    """OOT 驗證結果"""
    oot_auc: float
    oot_precision: float
    oot_recall: float
    oot_f1: float
    oot_samples: int
    oot_positive_count: int
    oot_positive_rate: float
    cv_auc_mean: float
    cv_oot_gap: float
    gap_status: str  # 'good' (< 0.05), 'acceptable' (< 0.08), 'warning' (>= 0.08)
    oot_period_start: str
    oot_period_end: str
    
    def is_generalization_good(self, threshold: float = 0.08) -> bool:
        """模型是否有良好的泛化能力"""
        return self.cv_oot_gap < threshold
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "oot_auc": round(self.oot_auc, 4),
            "oot_precision": round(self.oot_precision, 4),
            "oot_recall": round(self.oot_recall, 4),
            "oot_f1": round(self.oot_f1, 4),
            "oot_samples": self.oot_samples,
            "oot_positive_count": self.oot_positive_count,
            "oot_positive_rate": round(self.oot_positive_rate, 4),
            "cv_auc_mean": round(self.cv_auc_mean, 4),
            "cv_oot_gap": round(self.cv_oot_gap, 4),
            "gap_status": self.gap_status,
            "oot_period_start": self.oot_period_start,
            "oot_period_end": self.oot_period_end,
            "is_generalization_good": self.is_generalization_good()
        }


@dataclass
class ModelPerformance:
    """模型效能指標"""
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float  # train_auc - cv_auc_mean
    brier_score: Optional[float] = None
    ece: Optional[float] = None
    calibration_quality: Optional[str] = None
    pr_auc: Optional[float] = None
    positive_rate: Optional[float] = None
    
    def is_overfitting(self, threshold: float = 0.15) -> bool:
        """是否過擬合"""
        return self.overfitting_score > threshold


@dataclass
class FeatureImportance:
    """特徵重要性"""
    feature: str
    importance: float
    rank: int
    method: str  # 'gain', 'weight', 'cover'


@dataclass
class CasePrediction:
    """單筆案例預測"""
    case_id: str
    y_true: Optional[int]
    predicted_proba: float

    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "y_true": self.y_true,
            "predicted_proba": self.predicted_proba
        }


@dataclass
class ProbabilitySummary:
    """機率摘要"""
    mean: float
    std: float
    bins: Dict[str, int]
    min: float
    max: float

    def to_dict(self) -> Dict:
        return {
            "mean": self.mean,
            "std": self.std,
            "bins": self.bins,
            "min": self.min,
            "max": self.max
        }


@dataclass
class PredictionOutput:
    """預測輸出"""
    predictions: List[CasePrediction]
    proba_summary: ProbabilitySummary

    def to_dict(self) -> Dict:
        return {
            "predictions": [p.to_dict() for p in self.predictions],
            "proba_summary": self.proba_summary.to_dict()
        }


@dataclass
class PRMetrics:
    """PR 指標"""
    pr_auc: float
    baseline: float
    positive_rate: float
    precision: List[float]
    recall: List[float]
    thresholds: List[float]

    def to_dict(self) -> Dict:
        return {
            "pr_auc": self.pr_auc,
            "baseline": self.baseline,
            "positive_rate": self.positive_rate,
            "precision": self.precision,
            "recall": self.recall,
            "thresholds": self.thresholds
        }


class XGBoostAnalyzer:
    """
    XGBoost 分析引擎
    
    使用 XGBoost 分析特徵重要性並發現交易模式
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Args:
            params: XGBoost 參數字典（可選，使用預設值）
        """
        self.logger = logger
        
        # XGBoost 預設參數
        self.default_params = {
            # Model parameters
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': 5,
            'learning_rate': 0.05,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 5,
            'gamma': 0.1,
            
            # Regularization
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            
            # Other
            'random_state': 42,
            'n_jobs': -1,
            'verbosity': 0
        }
        
        # 合併自訂參數
        self.params = {**self.default_params, **(params or {})}
        
        self.model = None
        self.feature_names = None
        self.calibration_analyzer = CalibrationAnalyzer()
        self.last_calibration_curve: Optional[CalibrationCurveData] = None
        self.last_pr_curve: Optional[Dict[str, List[float]]] = None
    
    def train_model(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        early_stopping_rounds: int = 10,
        eval_size: float = 0.2,
        xgboost_params: Optional[Dict] = None,
        cv_folds: int = 5,
        time_series_split: bool = False,
        timestamps: Optional[List[int]] = None,
        purge_gap: Optional[int] = None,
        embargo_pct: Optional[float] = None
    ) -> ModelPerformance:
        """
        訓練 XGBoost 模型
        
        Args:
            X: 特徵矩陣 (n_samples, n_features) - 可以是 DataFrame 或 numpy array
            y: 標籤數組 (n_samples,) - 1=盈利, 0=虧損
            feature_names: 特徵名稱列表（當 X 是 numpy array 時必須提供）
            early_stopping_rounds: Early stopping 輪數
            eval_size: 驗證集比例
            xgboost_params: 自訂 XGBoost 參數（可選）
            
        Returns:
            ModelPerformance 物件
        """
        # 儲存特徵名稱（支援 DataFrame 和 numpy array）
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
        elif feature_names is not None:
            self.feature_names = feature_names
        else:
            raise ValueError("當 X 是 numpy array 時，必須提供 feature_names 參數")
        
        self.logger.info(
            f"開始訓練 XGBoost 模型 - 樣本數: {len(X)}, 特徵數: {len(self.feature_names)}"
        )
        
        # 更新參數
        if xgboost_params:
            self.params = {**self.default_params, **xgboost_params}
        
        # 檢查標籤分佈
        unique, counts = np.unique(y, return_counts=True)
        label_dist = dict(zip(unique, counts))
        self.logger.info(f"標籤分佈: {label_dist}")
        
        if len(unique) < 2:
            raise ValueError(f"標籤只有一個類別: {unique}，無法訓練二分類模型")
        
        # 分割訓練集和驗證集
        if time_series_split:
            if timestamps is None:
                order = np.arange(len(y))
            else:
                order = np.argsort(np.array(timestamps))

            if isinstance(X, pd.DataFrame):
                X_sorted = X.iloc[order]
            else:
                X_sorted = X[order]
            y_sorted = y[order]

            split_idx = int(len(y_sorted) * (1 - eval_size))
            if split_idx < 1 or split_idx >= len(y_sorted):
                raise ValueError("時間序列切分比例不合理，請調整 eval_size")

            X_train = X_sorted[:split_idx]
            X_val = X_sorted[split_idx:]
            y_train = y_sorted[:split_idx]
            y_val = y_sorted[split_idx:]
        else:
            from sklearn.model_selection import train_test_split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=eval_size, random_state=42, stratify=y
            )
        
        self.logger.info(
            f"訓練集: {len(X_train)} 樣本, 驗證集: {len(X_val)} 樣本"
        )
        
        # 建立 XGBoost 模型（加入 early_stopping_rounds 參數）
        params_with_early_stop = {**self.params, 'early_stopping_rounds': early_stopping_rounds}
        self.model = xgb.XGBClassifier(**params_with_early_stop)
        
        # 訓練模型
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # 計算訓練集 AUC
        y_train_pred = self.model.predict_proba(X_train)[:, 1]
        train_auc = roc_auc_score(y_train, y_train_pred)
        
        # 驗證模型
        performance = self.validate_model(
            X, y, cv_folds=cv_folds,
            time_series_split=time_series_split,
            timestamps=timestamps,
            purge_gap=purge_gap,
            embargo_pct=embargo_pct
        )
        
        self.logger.info(
            f"訓練完成 - Train AUC: {train_auc:.4f}, "
            f"CV AUC: {performance.cv_auc_mean:.4f} ± {performance.cv_auc_std:.4f}"
        )
        
        return performance

    def train_with_purged_cv(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        early_stopping_rounds: int = 10,
        eval_size: float = 0.2,
        xgboost_params: Optional[Dict] = None,
        cv_folds: int = 5,
        timestamps: Optional[List[int]] = None,
        purge_gap: int = 5,
        embargo_pct: float = 0.01
    ) -> ModelPerformance:
        """
        使用 Purged K-Fold 交叉驗證訓練模型
        """
        return self.train_model(
            X=X,
            y=y,
            feature_names=feature_names,
            early_stopping_rounds=early_stopping_rounds,
            eval_size=eval_size,
            xgboost_params=xgboost_params,
            cv_folds=cv_folds,
            time_series_split=True,
            timestamps=timestamps,
            purge_gap=purge_gap,
            embargo_pct=embargo_pct
        )
    
    def calculate_feature_importance(
        self,
        feature_names: List[str],
        method: str = 'gain',
        top_n: Optional[int] = None
    ) -> List[FeatureImportance]:
        """
        計算特徵重要性
        
        Args:
            feature_names: 特徵名稱列表
            method: 'gain', 'weight', 'cover'
            top_n: 返回前 N 個特徵（None 表示全部）
            
        Returns:
            特徵重要性列表（按重要性排序）
        """
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 train_model()")
        
        # 獲取特徵重要性 (XGBoost 2.x API)
        importance_dict = self.model.get_booster().get_score(importance_type=method)
        
        # 轉換為列表格式
        importance_list = []
        for i, feature_name in enumerate(feature_names):
            # XGBoost 使用 f0, f1, ... 作為特徵名稱
            xgb_feature_name = f'f{i}'
            importance = importance_dict.get(xgb_feature_name, 0.0)
            importance_list.append((feature_name, importance))
        
        # 正規化重要性（總和為 1）
        total_importance = sum(imp for _, imp in importance_list)
        if total_importance == 0:
            # 回退：嘗試使用 sklearn 介面的 feature_importances_
            if hasattr(self.model, "feature_importances_"):
                fallback_importances = self.model.feature_importances_
                if fallback_importances is not None and len(fallback_importances) == len(feature_names):
                    importance_list = list(zip(feature_names, fallback_importances))
                    total_importance = float(np.sum(fallback_importances))
        
        if total_importance > 0:
            importance_list = [(name, imp / total_importance) for name, imp in importance_list]
        else:
            self.logger.warning("特徵重要性總和為 0，模型可能未產生分裂")
        
        # 排序（由高到低）
        importance_list.sort(key=lambda x: x[1], reverse=True)
        
        # 建立 FeatureImportance 物件
        result = [
            FeatureImportance(
                feature=name,
                importance=imp,
                rank=rank + 1,
                method=method
            )
            for rank, (name, imp) in enumerate(importance_list)
        ]
        
        # 返回前 N 個（如果指定）
        if top_n is not None:
            result = result[:top_n]
        
        self.logger.info(
            f"特徵重要性計算完成 - 方法: {method}, "
            f"前 3 名: {[r.feature for r in result[:3]]}"
        )
        
        return result

    def get_all_importance_types(
        self,
        feature_names: List[str],
        top_n: Optional[int] = None
    ) -> Dict[str, List[FeatureImportance]]:
        """
        取得三種特徵重要性指標（gain/cover/weight）
        """
        return {
            "gain": self.calculate_feature_importance(feature_names, method="gain", top_n=top_n),
            "cover": self.calculate_feature_importance(feature_names, method="cover", top_n=top_n),
            "weight": self.calculate_feature_importance(feature_names, method="weight", top_n=top_n)
        }

    def _build_proba_summary(self, y_pred_proba: np.ndarray, n_bins: int = 10) -> ProbabilitySummary:
        """建立預測機率摘要"""
        mean = float(np.mean(y_pred_proba))
        std = float(np.std(y_pred_proba))
        min_val = float(np.min(y_pred_proba))
        max_val = float(np.max(y_pred_proba))

        bins = np.linspace(0.0, 1.0, n_bins + 1)
        hist, edges = np.histogram(y_pred_proba, bins=bins)
        bin_map: Dict[str, int] = {}
        for i in range(len(hist)):
            left = edges[i]
            right = edges[i + 1]
            key = f"{left:.1f}-{right:.1f}"
            bin_map[key] = int(hist[i])

        return ProbabilitySummary(
            mean=mean,
            std=std,
            bins=bin_map,
            min=min_val,
            max=max_val
        )

    def get_predictions(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y_true: Optional[np.ndarray] = None,
        case_ids: Optional[List[str]] = None,
        batch_size: int = 10000
    ) -> PredictionOutput:
        """
        取得預測機率與摘要
        """
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 train_model()")

        if len(X) == 0:
            raise ValueError("X 為空，無法預測")

        if y_true is not None and len(X) != len(y_true):
            raise ValueError("X 與 y_true 長度不一致")

        if case_ids is not None and len(X) != len(case_ids):
            raise ValueError("X 與 case_ids 長度不一致")

        total_samples = len(X)
        if case_ids is None:
            case_ids = [f"case_{i}" for i in range(total_samples)]
        elif len(set(case_ids)) != len(case_ids):
            self.logger.warning("case_id 存在重複，請確認輸入是否正確")

        y_pred_proba_chunks = []
        for start in range(0, total_samples, batch_size):
            end = min(start + batch_size, total_samples)
            if isinstance(X, pd.DataFrame):
                X_batch = X.iloc[start:end]
            else:
                X_batch = X[start:end]
            proba_batch = self.model.predict_proba(X_batch)[:, 1]
            y_pred_proba_chunks.append(proba_batch)

        y_pred_proba = np.concatenate(y_pred_proba_chunks)
        min_prob = float(np.min(y_pred_proba))
        max_prob = float(np.max(y_pred_proba))
        if min_prob < 0.0 or max_prob > 1.0:
            self.logger.warning(
                f"預測機率超出 [0, 1] 範圍 (min={min_prob:.4f}, max={max_prob:.4f})"
            )

        predictions = []
        for i, proba in enumerate(y_pred_proba):
            label = int(y_true[i]) if y_true is not None else None
            predictions.append(
                CasePrediction(
                    case_id=case_ids[i],
                    y_true=label,
                    predicted_proba=float(proba)
                )
            )

        summary = self._build_proba_summary(y_pred_proba)
        return PredictionOutput(predictions=predictions, proba_summary=summary)

    def calculate_calibration_metrics(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        n_bins: int = 10
    ) -> CalibrationMetrics:
        """計算校準指標與曲線資料"""
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 train_model()")

        y_pred_proba = self.model.predict_proba(X)[:, 1]
        metrics = self.calibration_analyzer.calculate_metrics(y, y_pred_proba, n_bins=n_bins)
        self.last_calibration_curve = metrics.curve_data

        self.logger.info(
            f"校準指標 - Brier: {metrics.brier_score:.4f}, ECE: {metrics.ece:.4f}, "
            f"品質: {metrics.calibration_quality}"
        )
        if metrics.calibration_quality == "poor":
            self.logger.warning("校準品質偏低，建議重新調整模型或做機率校準")

        return metrics

    def calculate_pr_metrics(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray
    ) -> PRMetrics:
        """計算 PR AUC 與曲線資料"""
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 train_model()")

        y_pred_proba = self.model.predict_proba(X)[:, 1]
        precision, recall, thresholds = precision_recall_curve(y, y_pred_proba)
        pr_auc = float(auc(recall, precision))
        positive_rate = float(np.mean(y))
        baseline = positive_rate

        self.last_pr_curve = {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": thresholds.tolist()
        }

        if positive_rate < 0.2:
            self.logger.info(
                f"正樣本比例偏低 ({positive_rate:.2%})，建議參考 PR AUC"
            )

        return PRMetrics(
            pr_auc=pr_auc,
            baseline=baseline,
            positive_rate=positive_rate,
            precision=precision.tolist(),
            recall=recall.tolist(),
            thresholds=thresholds.tolist()
        )
    
    def validate_model(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        cv_folds: int = 5,
        time_series_split: bool = False,
        timestamps: Optional[List[int]] = None,
        purge_gap: Optional[int] = None,
        embargo_pct: Optional[float] = None
    ) -> ModelPerformance:
        """
        交叉驗證模型效能
        
        Args:
            X: 特徵矩陣
            y: 標籤數組
            cv_folds: 交叉驗證折數
            
        Returns:
            模型效能指標
        """
        self.logger.info(f"開始交叉驗證 - {cv_folds}-fold CV")
        
        # 建立交叉驗證分割
        if time_series_split:
            if timestamps is None:
                order = np.arange(len(y))
            else:
                order = np.argsort(np.array(timestamps))

            if isinstance(X, pd.DataFrame):
                X_ordered = X.iloc[order]
            else:
                X_ordered = X[order]
            y_ordered = y[order]

            if purge_gap is not None or embargo_pct is not None:
                split_iter = PurgedTimeSeriesSplit(
                    n_splits=cv_folds,
                    purge_gap=int(purge_gap or 0),
                    embargo_pct=float(embargo_pct or 0.0)
                ).split(X_ordered)
            else:
                from sklearn.model_selection import TimeSeriesSplit
                splitter = TimeSeriesSplit(n_splits=cv_folds)
                split_iter = splitter.split(X_ordered)
        else:
            if purge_gap is not None or embargo_pct is not None:
                self.logger.warning("非時間序列切分下忽略 purge/embargo 參數")
            skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
            X_ordered = X
            y_ordered = y
            split_iter = skf.split(X_ordered, y_ordered)
        
        cv_auc_scores = []
        cv_precision_scores = []
        cv_recall_scores = []
        cv_f1_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(split_iter):
            # 支援 DataFrame 和 numpy array
            if isinstance(X_ordered, pd.DataFrame):
                X_train_fold = X_ordered.iloc[train_idx]
                X_val_fold = X_ordered.iloc[val_idx]
            else:
                X_train_fold = X_ordered[train_idx]
                X_val_fold = X_ordered[val_idx]
            
            y_train_fold = y_ordered[train_idx]
            y_val_fold = y_ordered[val_idx]
            
            # 訓練模型
            model_fold = xgb.XGBClassifier(**self.params)
            model_fold.fit(X_train_fold, y_train_fold, verbose=False)
            
            # 預測
            y_pred_proba = model_fold.predict_proba(X_val_fold)[:, 1]
            y_pred = model_fold.predict(X_val_fold)
            
            # 計算指標
            if len(np.unique(y_val_fold)) < 2:
                auc = np.nan
                self.logger.warning(
                    f"Fold {fold + 1}/{cv_folds} - 驗證集只有單一類別，AUC 設為 NaN"
                )
            else:
                auc = roc_auc_score(y_val_fold, y_pred_proba)
            precision = precision_score(y_val_fold, y_pred, zero_division=0)
            recall = recall_score(y_val_fold, y_pred, zero_division=0)
            f1 = f1_score(y_val_fold, y_pred, zero_division=0)
            
            cv_auc_scores.append(auc)
            cv_precision_scores.append(precision)
            cv_recall_scores.append(recall)
            cv_f1_scores.append(f1)
            
            self.logger.info(
                f"Fold {fold + 1}/{cv_folds} - "
                f"AUC: {auc:.4f}, Precision: {precision:.4f}, "
                f"Recall: {recall:.4f}, F1: {f1:.4f}"
            )
        
        # 計算訓練集 AUC（使用完整模型）
        if self.model is None:
            raise ValueError("模型尚未訓練")
        
        y_train_pred = self.model.predict_proba(X_ordered)[:, 1]
        if len(np.unique(y_ordered)) < 2:
            train_auc = np.nan
            self.logger.warning("訓練集只有單一類別，Train AUC 設為 NaN")
        else:
            train_auc = roc_auc_score(y_ordered, y_train_pred)
        
        # 平均指標
        valid_auc_scores = [v for v in cv_auc_scores if not np.isnan(v)]
        if len(valid_auc_scores) == 0:
            cv_auc_mean = np.nan
            cv_auc_std = np.nan
        else:
            cv_auc_mean = float(np.mean(valid_auc_scores))
            cv_auc_std = float(np.std(valid_auc_scores))
        
        if np.isnan(train_auc) or np.isnan(cv_auc_mean):
            overfitting_score = np.nan
        else:
            overfitting_score = train_auc - cv_auc_mean

        # 校準指標與 PR AUC
        calibration_metrics = self.calculate_calibration_metrics(X_ordered, y_ordered)
        pr_metrics = self.calculate_pr_metrics(X_ordered, y_ordered)

        if not np.isnan(cv_auc_mean) and not np.isnan(pr_metrics.pr_auc):
            roc_pr_gap = cv_auc_mean - pr_metrics.pr_auc
            if roc_pr_gap > 0.15:
                self.logger.warning(
                    f"ROC AUC 與 PR AUC 差距較大 ({roc_pr_gap:.4f})，ROC AUC 可能過度樂觀"
                )
        
        # 建立效能物件
        performance = ModelPerformance(
            train_auc=train_auc,
            cv_auc_mean=cv_auc_mean,
            cv_auc_std=cv_auc_std,
            precision=np.mean(cv_precision_scores),
            recall=np.mean(cv_recall_scores),
            f1_score=np.mean(cv_f1_scores),
            overfitting_score=overfitting_score,
            brier_score=calibration_metrics.brier_score,
            ece=calibration_metrics.ece,
            calibration_quality=calibration_metrics.calibration_quality,
            pr_auc=pr_metrics.pr_auc,
            positive_rate=pr_metrics.positive_rate
        )
        
        self.logger.info(
            f"交叉驗證完成 - "
            f"Train AUC: {performance.train_auc:.4f}, "
            f"CV AUC: {performance.cv_auc_mean:.4f} ± {performance.cv_auc_std:.4f}, "
            f"Overfitting: {performance.overfitting_score:.4f}"
        )
        
        if performance.is_overfitting():
            self.logger.warning(
                f"檢測到過擬合 (overfitting score > 0.15): {performance.overfitting_score:.4f}"
            )
        
        return performance
    
    def get_top_features(
        self,
        n: int = 10,
        method: str = 'gain'
    ) -> List[str]:
        """
        獲取前 N 個重要特徵名稱
        
        Args:
            n: 前 N 個特徵
            method: 重要性計算方法
            
        Returns:
            特徵名稱列表
        """
        if self.feature_names is None:
            raise ValueError("特徵名稱尚未設定，請先訓練模型")

        importance_list = self.calculate_feature_importance(
            feature_names=self.feature_names,
            method=method,
            top_n=n
        )
        return [fi.feature for fi in importance_list]
    
    # ==================== OOT 驗證方法 ====================
    
    def validate_oot(
        self,
        X_oot: Union[pd.DataFrame, np.ndarray],
        y_oot: np.ndarray,
        cv_auc_mean: Optional[float] = None,
        oot_period_start: str = "",
        oot_period_end: str = "",
        threshold: float = 0.5
    ) -> OOTValidationResult:
        """
        Out-of-Time 驗證
        
        評估模型在完全未見過的未來時間段的表現
        
        Args:
            X_oot: OOT 特徵矩陣
            y_oot: OOT 標籤
            cv_auc_mean: CV AUC 平均值（用於計算 gap，None 時跳過 gap 計算）
            oot_period_start: OOT 期間開始時間
            oot_period_end: OOT 期間結束時間
            threshold: 分類閾值（預設 0.5）
            
        Returns:
            OOTValidationResult 物件
            
        Raises:
            ValueError: 模型未訓練或 OOT 樣本不足
        """
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 train_model()")
        
        # 驗證 OOT 資料
        if len(X_oot) == 0:
            raise ValueError("OOT 資料為空")
        
        if len(y_oot) == 0 or len(X_oot) != len(y_oot):
            raise ValueError(f"OOT 標籤長度不匹配: X={len(X_oot)}, y={len(y_oot)}")
        
        self.logger.info(
            f"開始 OOT 驗證 - 樣本數: {len(X_oot)}, "
            f"期間: {oot_period_start} ~ {oot_period_end}"
        )
        
        # 預測
        y_pred_proba = self.model.predict_proba(X_oot)[:, 1]
        y_pred = (y_pred_proba >= threshold).astype(int)
        
        # 計算指標
        unique_labels = np.unique(y_oot)
        if len(unique_labels) < 2:
            self.logger.warning(
                f"OOT 標籤只有單一類別 ({unique_labels})，AUC 設為 NaN"
            )
            oot_auc = np.nan
        else:
            oot_auc = roc_auc_score(y_oot, y_pred_proba)
        
        oot_precision = precision_score(y_oot, y_pred, zero_division=0)
        oot_recall = recall_score(y_oot, y_pred, zero_division=0)
        oot_f1 = f1_score(y_oot, y_pred, zero_division=0)
        
        # 計算樣本統計
        oot_samples = len(y_oot)
        oot_positive_count = int(np.sum(y_oot))
        oot_positive_rate = oot_positive_count / oot_samples if oot_samples > 0 else 0.0
        
        # 計算 CV-OOT Gap
        if cv_auc_mean is not None and not np.isnan(cv_auc_mean) and not np.isnan(oot_auc):
            cv_oot_gap = cv_auc_mean - oot_auc
        else:
            cv_oot_gap = np.nan
        
        # 判斷 Gap 狀態
        if np.isnan(cv_oot_gap):
            gap_status = "unknown"
        elif cv_oot_gap < 0.05:
            gap_status = "good"
        elif cv_oot_gap < 0.08:
            gap_status = "acceptable"
        else:
            gap_status = "warning"
        
        # 記錄結果
        self.logger.info(
            f"OOT 驗證完成 - AUC: {oot_auc:.4f}, "
            f"Precision: {oot_precision:.4f}, Recall: {oot_recall:.4f}, "
            f"正樣本率: {oot_positive_rate:.2%}"
        )
        
        if not np.isnan(cv_oot_gap):
            if gap_status == "warning":
                self.logger.warning(
                    f"CV-OOT Gap 較大 ({cv_oot_gap:.4f} >= 0.08)，"
                    f"模型可能在未來時間段表現較差"
                )
            else:
                self.logger.info(
                    f"CV-OOT Gap: {cv_oot_gap:.4f} - 狀態: {gap_status}"
                )
        
        return OOTValidationResult(
            oot_auc=float(oot_auc) if not np.isnan(oot_auc) else 0.0,
            oot_precision=float(oot_precision),
            oot_recall=float(oot_recall),
            oot_f1=float(oot_f1),
            oot_samples=oot_samples,
            oot_positive_count=oot_positive_count,
            oot_positive_rate=float(oot_positive_rate),
            cv_auc_mean=float(cv_auc_mean) if cv_auc_mean and not np.isnan(cv_auc_mean) else 0.0,
            cv_oot_gap=float(cv_oot_gap) if not np.isnan(cv_oot_gap) else 0.0,
            gap_status=gap_status,
            oot_period_start=oot_period_start,
            oot_period_end=oot_period_end
        )
    
    def get_cv_oot_gap(
        self,
        cv_auc_mean: float,
        oot_auc: float
    ) -> Tuple[float, str]:
        """
        計算 CV-OOT Gap 並判斷狀態
        
        Args:
            cv_auc_mean: CV AUC 平均值
            oot_auc: OOT AUC
            
        Returns:
            (gap 值, 狀態字串)
        """
        if np.isnan(cv_auc_mean) or np.isnan(oot_auc):
            return np.nan, "unknown"
        
        gap = cv_auc_mean - oot_auc
        
        if gap < 0.05:
            status = "good"
        elif gap < 0.08:
            status = "acceptable"
        else:
            status = "warning"
        
        return gap, status
