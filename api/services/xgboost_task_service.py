"""
XGBoost Task Service - XGBoost 分析任務服務

管理非同步的 XGBoost 分析任務

Author: AI Agent
Date: 2026-01-10
"""

import asyncio
import uuid
from typing import Dict, Optional
from datetime import datetime
import logging

import pandas as pd
import numpy as np

from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from momentum.Analysis.regime_analyzer import RegimeAnalyzer
from momentum.Analysis.pattern_extractor import PatternExtractor
from momentum.Analysis.model_storage import ModelStorage
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from api.core.logging import get_logger
from api.utils.json_serializer import sanitize_for_json

logger = get_logger(__name__)


class TaskManager:
    """任務狀態管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
    
    def create_task(self, task_id: str):
        """建立新任務"""
        self.tasks[task_id] = {
            'status': 'running',
            'created_at': datetime.now().isoformat(),
            'progress': 0,
            'message': '任務已啟動',
            'result': None,
            'error': None
        }
    
    def update_progress(self, task_id: str, progress: int, message: str):
        """更新進度"""
        if task_id in self.tasks:
            self.tasks[task_id]['progress'] = progress
            self.tasks[task_id]['message'] = message
    
    def update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """更新狀態"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = status
            if result:
                self.tasks[task_id]['result'] = result
            if error:
                self.tasks[task_id]['error'] = error
            self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """獲取任務狀態"""
        return self.tasks.get(task_id)


class XGBoostTaskService:
    """XGBoost 分析任務服務"""
    
    def __init__(self):
        self.task_manager = TaskManager()
        self.xgboost_analyzer = XGBoostAnalyzer()
        self.pattern_extractor = PatternExtractor()
        self.model_storage = ModelStorage()
        self.feature_storage = FeatureStorage()
        self.logger = logger
    
    async def start_xgboost_analysis_task(
        self,
        case_id: str,
        xgboost_params: Optional[Dict] = None,
        cv_folds: int = 5,
        top_n_rules: int = 10,
        min_support: int = 10
    ) -> Dict:
        """
        啟動 XGBoost 分析任務
        
        Args:
            case_id: 案例 ID
            xgboost_params: XGBoost 參數
            cv_folds: 交叉驗證折數
            top_n_rules: 提取前 N 條規則
            min_support: 最小支持度
            
        Returns:
            任務 ID 和狀態
        """
        task_id = str(uuid.uuid4())
        
        self.logger.info(
            f"啟動 XGBoost 分析任務 - task_id: {task_id}, case_id: {case_id}"
        )
        
        # 建立任務
        self.task_manager.create_task(task_id)
        
        # 在背景執行分析
        asyncio.create_task(
            self._run_xgboost_analysis(
                task_id, case_id, xgboost_params,
                cv_folds, top_n_rules, min_support
            )
        )
        
        return {
            'task_id': task_id,
            'message': 'XGBoost 分析任務已啟動',
            'status': 'running'
        }
    
    async def _run_xgboost_analysis(
        self,
        task_id: str,
        case_id: str,
        xgboost_params: Optional[Dict],
        cv_folds: int,
        top_n_rules: int,
        min_support: int
    ):
        """執行 XGBoost 分析（背景任務）"""
        try:
            # 1. 讀取特徵數據
            self.task_manager.update_progress(task_id, 10, '讀取特徵數據...')
            
            feature_data = self.feature_storage.load_features_from_hdf5(case_id)
            
            if 'features' not in feature_data:
                raise ValueError(f"案例 {case_id} 沒有特徵數據")
            
            df = feature_data['features']
            
            # 準備 X, y
            if 'label' not in df.columns:
                raise ValueError("特徵數據缺少 label 欄位")
            
            y = df['label'].values
            timestamps = df['timestamp'].values if 'timestamp' in df.columns else None
            X = df.drop(columns=['label', 'open_time'], errors='ignore')
            feature_names = X.columns.tolist()
            if 'case_id' in df.columns:
                case_ids = df['case_id'].astype(str).tolist()
            else:
                case_ids = [f"{case_id}_{i}" for i in range(len(X))]
            
            self.logger.info(
                f"特徵數據載入完成 - 樣本數: {len(X)}, 特徵數: {len(feature_names)}"
            )
            
            # 2. 訓練模型
            self.task_manager.update_progress(task_id, 30, '訓練 XGBoost 模型...')
            
            performance = await asyncio.to_thread(
                self.xgboost_analyzer.train_model,
                X, y,
                feature_names,
                10,
                0.2,
                xgboost_params,
                cv_folds,
                True,
                timestamps
            )
            
            self.logger.info(
                f"模型訓練完成 - Train AUC: {performance.train_auc:.4f}, "
                f"CV AUC: {performance.cv_auc_mean:.4f}"
            )
            
            # 3. 計算特徵重要性
            self.task_manager.update_progress(task_id, 50, '計算特徵重要性...')
            
            feature_importance = await asyncio.to_thread(
                self.xgboost_analyzer.calculate_feature_importance,
                feature_names
            )

            # 3.1 取得三種特徵重要性
            feature_importance_all = await asyncio.to_thread(
                self.xgboost_analyzer.get_all_importance_types,
                feature_names
            )
            
            # 4. 提取決策規則
            self.task_manager.update_progress(task_id, 70, '提取決策規則...')
            
            rules = await asyncio.to_thread(
                self.pattern_extractor.extract_decision_rules,
                self.xgboost_analyzer.model,
                X, y, feature_names,
                top_n_rules, min_support
            )

            # 4.1 取得預測機率與摘要
            predictions_output = await asyncio.to_thread(
                self.xgboost_analyzer.get_predictions,
                X, y, case_ids
            )

            # 4.2 建立 SHAP 取樣資料（供後續解釋使用）
            max_shap_samples = 200
            sample_size = min(len(X), max_shap_samples)
            rng = np.random.default_rng(42)
            sample_indices = rng.choice(len(X), size=sample_size, replace=False)
            if isinstance(X, pd.DataFrame):
                X_sample = X.iloc[sample_indices]
                sample_values = X_sample.values
            else:
                sample_values = X[sample_indices]

            shap_sample = {
                "sample_size": int(sample_size),
                "feature_names": feature_names,
                "case_ids": [case_ids[i] for i in sample_indices],
                "samples": sample_values.tolist()
            }

            # 4.3 市場體制分析（若可取得 Market_Phase）
            regime_analysis = None
            market_phases = self._resolve_market_phases(df)
            if market_phases:
                try:
                    analyzer = RegimeAnalyzer()
                    y_pred_proba = np.array([p.predicted_proba for p in predictions_output.predictions])
                    regime_report = analyzer.analyze_by_phase(
                        y_true=y,
                        y_pred_proba=y_pred_proba,
                        market_phases=market_phases
                    )
                    regime_analysis = regime_report.to_dict()
                    self.logger.info("發現 Market_Phase 欄位，啟用體制分析")
                except Exception as e:
                    self.logger.warning(f"市場體制分析失敗: {str(e)}")
            
            # 5. 儲存模型
            self.task_manager.update_progress(task_id, 90, '儲存模型...')
            
            model_path = await asyncio.to_thread(
                self.model_storage.save_model_to_pickle,
                case_id,
                self.xgboost_analyzer.model,
                feature_names,
                performance.__dict__,
                xgboost_params or {},
                {
                    'task_id': task_id,
                    'cv_folds': cv_folds,
                    'top_n_rules': top_n_rules,
                    'min_support': min_support
                }
            )
            
            # 6. 完成
            result = {
                'case_id': case_id,
                'model_performance': performance.__dict__,
                'feature_importance': [fi.__dict__ for fi in feature_importance],
                'feature_importance_all': {
                    key: [fi.__dict__ for fi in values]
                    for key, values in feature_importance_all.items()
                },
                'decision_rules': [rule.to_dict() for rule in rules],
                'predictions': predictions_output.to_dict(),
                'shap_sample': shap_sample,
                'calibration_curve': (
                    self.xgboost_analyzer.last_calibration_curve.to_dict()
                    if self.xgboost_analyzer.last_calibration_curve else None
                ),
                'pr_curve': self.xgboost_analyzer.last_pr_curve,
                'regime_analysis': regime_analysis,
                'model_saved': True,
                'model_path': model_path
            }

            result = sanitize_for_json(result)
            
            self.task_manager.update_status(task_id, 'completed', result=result)
            self.task_manager.update_progress(task_id, 100, '分析完成')
            
            self.logger.info(f"XGBoost 分析完成 - task_id: {task_id}, case_id: {case_id}")
            
        except Exception as e:
            error_msg = f"XGBoost 分析失敗: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.task_manager.update_status(task_id, 'failed', error=error_msg)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """獲取任務狀態"""
        return self.task_manager.get_task(task_id)
    
    def get_model_info(self, case_id: str) -> Dict:
        """獲取模型資訊"""
        return self.model_storage.get_model_info(case_id)
    
    def list_models(self) -> list:
        """列出所有模型"""
        return self.model_storage.list_model_files()
    
    def model_exists(self, case_id: str) -> bool:
        """檢查模型是否存在"""
        return self.model_storage.model_file_exists(case_id)

    def _resolve_market_phases(self, df: pd.DataFrame) -> Optional[list]:
        """解析 Market_Phase 欄位，若缺失則以時間戳推導"""
        phase_columns = ["Market_Phase", "market_phase", "marketPhase"]
        for col in phase_columns:
            if col in df.columns:
                phases = df[col].astype(str).tolist()
                if any(phases):
                    return phases

        if "timestamp" not in df.columns:
            return None

        try:
            from datetime import datetime
            from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig

            timestamps = df["timestamp"].values
            phases = []
            for ts in timestamps:
                ts_int = int(ts)
                if ts_int > 10 ** 12:
                    ts_int = ts_int // 1000
                phase = MarketConfig.get_market_phase(datetime.utcfromtimestamp(ts_int))
                phases.append(phase)
            return phases
        except Exception as e:
            self.logger.warning(f"市場體制推導失敗: {str(e)}")
            return None
