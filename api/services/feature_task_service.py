"""
Feature Task Service - 非同步特徵提取服務

提供非同步任務管理，支持長時間運行的特徵提取操作

Author: AI Agent
Date: 2026-01-10
"""

import asyncio
import uuid
from typing import Dict, Optional
from datetime import datetime
import logging
import traceback

import pandas as pd
import h5py

from momentum.FeatureEngineering.feature_extractor import (
    FeatureExtractor, StrategyParams
)
from momentum.FeatureEngineering.feature_validator import FeatureValidator
from momentum.FeatureEngineering.feature_storage import FeatureStorage

from api.core.logging import get_logger

logger = get_logger(__name__)


class TaskManager:
    """簡單的任務管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
    
    def create_task(self, task_id: str) -> None:
        """建立新任務"""
        self.tasks[task_id] = {
            'status': 'running',
            'progress': 0,
            'result': None,
            'error': None,
            'start_time': datetime.now().isoformat()
        }
    
    def update_progress(self, task_id: str, progress: int) -> None:
        """更新任務進度"""
        if task_id in self.tasks:
            self.tasks[task_id]['progress'] = progress
    
    def update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """更新任務狀態"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = status
            if result:
                self.tasks[task_id]['result'] = result
            if error:
                self.tasks[task_id]['error'] = error
            self.tasks[task_id]['end_time'] = datetime.now().isoformat()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """獲取任務資訊"""
        return self.tasks.get(task_id)


class FeatureTaskService:
    """
    特徵提取任務服務
    
    支持非同步特徵提取，適用於大量數據處理
    """
    
    def __init__(self):
        self.extractor = FeatureExtractor()
        self.validator = FeatureValidator()
        self.storage = FeatureStorage()
        self.task_manager = TaskManager()
        self.logger = logger
    
    async def start_feature_extraction_task(
        self,
        case_id: str,
        symbol: str,
        timeframe: str,
        strategy_type: str,
        strategy_params: Dict,
        include_basic_features: bool = True,
        validate: bool = True
    ) -> Dict:
        """
        啟動特徵提取任務
        
        Args:
            case_id: 案例 ID
            symbol: 交易標的
            timeframe: 時間週期
            strategy_type: 策略類型 ('ema_three_line')
            strategy_params: 策略參數
            include_basic_features: 是否包含通用特徵
            validate: 是否執行驗證
            
        Returns:
            {'task_id': str, 'status': str, 'estimated_time': int}
        """
        # 先做基本參數驗證（避免無效任務進入佇列）
        strategy_config = StrategyParams(
            strategy_type=strategy_type,
            params=strategy_params
        )
        strategy_config.validate()

        task_id = f"feat_{uuid.uuid4().hex[:8]}"
        
        self.logger.info(f"啟動特徵提取任務 - task_id: {task_id}, case_id: {case_id}")
        
        # 建立任務
        self.task_manager.create_task(task_id)
        
        # 非同步執行
        asyncio.create_task(
            self._run_feature_extraction(
                task_id, case_id, symbol, timeframe,
                strategy_type, strategy_params,
                include_basic_features, validate
            )
        )
        
        return {
            'task_id': task_id,
            'status': 'running',
            'estimated_time': 30  # 預估 30 秒
        }
    
    async def _run_feature_extraction(
        self,
        task_id: str,
        case_id: str,
        symbol: str,
        timeframe: str,
        strategy_type: str,
        strategy_params: Dict,
        include_basic_features: bool,
        validate: bool
    ) -> None:
        """執行特徵提取任務 (背景執行)"""
        try:
            self.logger.info(f"開始執行特徵提取 - task_id: {task_id}")
            
            # Step 1: 載入 K線數據 (20%)
            self.task_manager.update_progress(task_id, 20)
            df = await self._load_kline_data(symbol, timeframe)
            
            if len(df) == 0:
                raise ValueError(f"K線數據為空 - {symbol}/{timeframe}")
            
            self.logger.info(f"K線數據載入完成 - 行數: {len(df)}")
            
            # Step 2: 提取特徵 (60%)
            self.task_manager.update_progress(task_id, 40)
            
            strategy_config = StrategyParams(
                strategy_type=strategy_type,
                params=strategy_params
            )
            
            features_df, feature_names = self.extractor.extract_features_from_strategy(
                df, strategy_config, include_basic_features
            )
            
            self.logger.info(f"特徵提取完成 - 特徵數: {len(feature_names)}")
            
            # Step 3: 驗證特徵 (80%)
            self.task_manager.update_progress(task_id, 80)
            
            validation_result = None
            if validate:
                validation_result = self.validator.validate(features_df, feature_names)
                
                # 如果有 NaN 值，嘗試填補
                if validation_result.has_nan:
                    self.logger.warning("發現 NaN 值，執行前向填補")
                    features_df = self.validator.fill_nan_values(
                        features_df, feature_names, method='forward'
                    )
            
            # Step 4: 儲存特徵 (100%)
            self.task_manager.update_progress(task_id, 90)
            
            storage_path = self.storage.save_features_to_hdf5(
                case_id=case_id,
                symbol=symbol,
                timeframe=timeframe,
                features_df=features_df,
                feature_names=feature_names,
                strategy_params={'strategy_type': strategy_type, 'params': strategy_params}
            )
            
            # 完成任務
            result = {
                'case_id': case_id,
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy_type': strategy_type,
                'n_samples': len(features_df),
                'n_features': len(feature_names),
                'feature_names': feature_names,
                'storage_path': storage_path,
                'validation': {
                    'has_nan': validation_result.has_nan if validation_result else False,
                    'has_inf': validation_result.has_inf if validation_result else False,
                    'max_correlation': validation_result.max_correlation if validation_result else 0.0,
                    'warnings': validation_result.warnings if validation_result else []
                } if validate else None
            }
            
            self.task_manager.update_status(task_id, 'completed', result=result)
            self.task_manager.update_progress(task_id, 100)
            
            self.logger.info(f"特徵提取任務完成 - task_id: {task_id}")
            
        except Exception as e:
            error_msg = f"特徵提取失敗: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            self.task_manager.update_status(task_id, 'failed', error=error_msg)
    
    async def _load_kline_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        從 HDF5 載入 K線數據
        
        Args:
            symbol: 交易標的
            timeframe: 時間週期
            
        Returns:
            K線 DataFrame
        """
        hdf5_path = "data_cache/kline_cache.h5"
        
        try:
            with h5py.File(hdf5_path, 'r') as f:
                group_path = f"{symbol}/{timeframe}"
                
                if group_path not in f:
                    raise KeyError(f"數據不存在: {group_path}")
                
                # 讀取數據
                data = f[f"{group_path}/data"][:]
                
                # 轉換為 DataFrame
                df = pd.DataFrame(data)
                
                # 確保時間戳遞增排序
                df = df.sort_values('timestamp')
                
                return df
                
        except Exception as e:
            self.logger.error(f"載入 K線數據失敗: {str(e)}", exc_info=True)
            raise
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        獲取任務狀態
        
        Args:
            task_id: 任務 ID
            
        Returns:
            任務資訊或 None
        """
        task = self.task_manager.get_task(task_id)
        
        if task is None:
            return None
        
        return {
            'task_id': task_id,
            'status': task['status'],
            'progress': task['progress'],
            'result': task.get('result'),
            'error': task.get('error')
        }
    
    def get_feature_summary(
        self,
        case_id: str,
        symbol: str,
        timeframe: str
    ) -> Dict:
        """
        獲取特徵摘要
        
        Args:
            case_id: 案例 ID
            symbol: 交易標的
            timeframe: 時間週期
            
        Returns:
            特徵摘要統計
        """
        return self.storage.get_feature_summary(case_id, symbol, timeframe)
