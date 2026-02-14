"""
Model Storage - 模型儲存管理

使用 Pickle 格式儲存和讀取模型（XGBoost/LightGBM）

Author: AI Agent
Date: 2026-01-10
"""

import pickle
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import logging

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class ModelStorage:
    """
    模型儲存管理器
    
    使用 Pickle 格式儲存模型和相關元數據
    """
    
    def __init__(self, base_path: str = "data_cache/models"):
        """
        Args:
            base_path: 模型儲存根目錄
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
    
    def save_model_to_pickle(
        self,
        case_id: str,
        model: Any,
        feature_names: list,
        performance: Dict,
        params: Dict,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        儲存模型至 Pickle
        
        Args:
            case_id: 案例 ID
            model: XGBoost 模型
            feature_names: 特徵名稱列表
            performance: 效能指標字典
            params: 模型參數
            metadata: 其他元數據
            
        Returns:
            檔案路徑
        """
        file_path = self.base_path / f"{case_id}.pkl"
        
        self.logger.info(f"開始儲存模型 - 案例: {case_id}, 檔案: {file_path}")
        
        # 準備儲存物件
        model_data = {
            'model': model,
            'feature_names': feature_names,
            'performance': performance,
            'params': params,
            'metadata': metadata or {},
            'saved_at': datetime.now().isoformat(),
            'case_id': case_id
        }
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(model_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            file_size_kb = file_path.stat().st_size / 1024
            
            self.logger.info(
                f"模型儲存完成 - 檔案大小: {file_size_kb:.2f} KB, "
                f"特徵數: {len(feature_names)}"
            )
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"模型儲存失敗: {str(e)}", exc_info=True)
            raise
    
    def load_model_from_pickle(self, case_id: str) -> Dict[str, Any]:
        """
        從 Pickle 讀取模型
        
        Args:
            case_id: 案例 ID
            
        Returns:
            模型數據字典，包含 model, feature_names, performance, params, metadata
        """
        file_path = self.base_path / f"{case_id}.pkl"
        
        if not file_path.exists():
            raise FileNotFoundError(f"模型檔案不存在: {file_path}")
        
        self.logger.info(f"開始讀取模型 - 案例: {case_id}, 檔案: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.logger.info(
                f"模型讀取完成 - 特徵數: {len(model_data['feature_names'])}"
            )
            
            return model_data
            
        except Exception as e:
            self.logger.error(f"模型讀取失敗: {str(e)}", exc_info=True)
            raise
    
    def model_file_exists(self, case_id: str) -> bool:
        """檢查模型檔案是否存在"""
        file_path = self.base_path / f"{case_id}.pkl"
        return file_path.exists()
    
    def delete_model(self, case_id: str) -> bool:
        """
        刪除模型檔案
        
        Args:
            case_id: 案例 ID
            
        Returns:
            是否成功刪除
        """
        file_path = self.base_path / f"{case_id}.pkl"
        
        if not file_path.exists():
            self.logger.warning(f"模型檔案不存在，無法刪除: {file_path}")
            return False
        
        try:
            file_path.unlink()
            self.logger.info(f"模型檔案已刪除: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"刪除模型檔案失敗: {str(e)}", exc_info=True)
            return False
    
    def list_model_files(self) -> list:
        """
        列出所有模型檔案
        
        Returns:
            模型檔案列表
        """
        model_files = []
        
        for file_path in self.base_path.glob("*.pkl"):
            case_id = file_path.stem
            
            model_files.append({
                'case_id': case_id,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'modified_time': datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat()
            })
        
        # 按修改時間排序
        model_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return model_files
    
    def get_model_info(self, case_id: str) -> Dict:
        """
        獲取模型資訊（不載入完整模型）
        
        Args:
            case_id: 案例 ID
            
        Returns:
            模型資訊字典
        """
        model_data = self.load_model_from_pickle(case_id)
        
        # 返回除了模型本身之外的所有資訊
        return {
            'case_id': model_data['case_id'],
            'feature_names': model_data['feature_names'],
            'feature_count': len(model_data['feature_names']),
            'performance': model_data['performance'],
            'params': model_data['params'],
            'metadata': model_data['metadata'],
            'saved_at': model_data['saved_at']
        }
