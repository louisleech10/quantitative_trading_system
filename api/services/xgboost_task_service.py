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
from momentum.Analysis.pattern_extractor import PatternExtractor
from momentum.Analysis.model_storage import ModelStorage
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from api.core.logging import get_logger

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
            
            # 4. 提取決策規則
            self.task_manager.update_progress(task_id, 70, '提取決策規則...')
            
            rules = await asyncio.to_thread(
                self.pattern_extractor.extract_decision_rules,
                self.xgboost_analyzer.model,
                X, y, feature_names,
                top_n_rules, min_support
            )
            
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
                'decision_rules': [rule.to_dict() for rule in rules],
                'model_saved': True,
                'model_path': model_path
            }
            
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
