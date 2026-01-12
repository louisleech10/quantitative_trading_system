"""
XGBoost Analyzer - 特徵重要性分析引擎

使用 XGBoost 分析特徵重要性，找出關鍵交易模式

Author: AI Agent
Date: 2026-01-10
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

import xgboost as xgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

from api.core.logging import get_logger

logger = get_logger(__name__)


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
    
    def train_model(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        early_stopping_rounds: int = 10,
        eval_size: float = 0.2,
        xgboost_params: Optional[Dict] = None
    ) -> ModelPerformance:
        """
        訓練 XGBoost 模型
        
        Args:
            X: 特徵矩陣 (n_samples, n_features)
            y: 標籤數組 (n_samples,) - 1=盈利, 0=虧損
            early_stopping_rounds: Early stopping 輪數
            eval_size: 驗證集比例
            xgboost_params: 自訂 XGBoost 參數（可選）
            
        Returns:
            ModelPerformance 物件
        """
        # 儲存特徵名稱
        self.feature_names = X.columns.tolist()
        
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
        performance = self.validate_model(X, y, cv_folds=5)
        
        self.logger.info(
            f"訓練完成 - Train AUC: {train_auc:.4f}, "
            f"CV AUC: {performance.cv_auc_mean:.4f} ± {performance.cv_auc_std:.4f}"
        )
        
        return performance
    
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
        if total_importance > 0:
            importance_list = [
                (name, imp / total_importance)
                for name, imp in importance_list
            ]
        
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
        
        return result
    
    def validate_model(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        cv_folds: int = 5
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
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        cv_auc_scores = []
        cv_precision_scores = []
        cv_recall_scores = []
        cv_f1_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_val_fold = y[val_idx]
            
            # 訓練模型
            model_fold = xgb.XGBClassifier(**self.params)
            model_fold.fit(X_train_fold, y_train_fold, verbose=False)
            
            # 預測
            y_pred_proba = model_fold.predict_proba(X_val_fold)[:, 1]
            y_pred = model_fold.predict(X_val_fold)
            
            # 計算指標
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
        
        y_train_pred = self.model.predict_proba(X)[:, 1]
        train_auc = roc_auc_score(y, y_train_pred)
        
        # 平均指標
        cv_auc_mean = np.mean(cv_auc_scores)
        cv_auc_std = np.std(cv_auc_scores)
        
        # 建立效能物件
        performance = ModelPerformance(
            train_auc=train_auc,
            cv_auc_mean=cv_auc_mean,
            cv_auc_std=cv_auc_std,
            precision=np.mean(cv_precision_scores),
            recall=np.mean(cv_recall_scores),
            f1_score=np.mean(cv_f1_scores),
            overfitting_score=train_auc - cv_auc_mean
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
        importance_list = self.calculate_feature_importance(method=method, top_n=n)
        return [fi.feature for fi in importance_list]
