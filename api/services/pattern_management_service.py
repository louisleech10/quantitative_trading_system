"""
Pattern Management Service - 模式管理服務

提供模式的建立、查詢、更新、刪除服務

Author: AI Agent
Date: 2026-01-10
"""

from typing import Dict, List, Optional
from datetime import datetime
import uuid
import logging

from momentum.factories import (
    create_pattern,
    create_pattern_rule,
    create_pattern_storage,
    create_pattern_validator,
)
from api.core.logging import get_logger

logger = get_logger(__name__)


class PatternManagementService:
    """模式管理服務"""
    
    def __init__(self):
        self.storage = create_pattern_storage()
        self.validator = create_pattern_validator()
        self.logger = logger
    
    def create_pattern(
        self,
        name: str,
        description: str,
        rules: List[Dict],
        case_id: str,
        xgboost_importance: Dict[str, float],
        performance_metrics: Dict[str, float],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        建立新模式
        
        Args:
            name: 模式名稱
            description: 模式描述
            rules: 規則列表（字典格式）
            case_id: 來源案例 ID
            xgboost_importance: XGBoost 特徵重要性
            performance_metrics: 效能指標
            tags: 標籤
            metadata: 元數據
            
        Returns:
            建立結果
        """
        # 生成 pattern_id
        pattern_id = f"PAT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        self.logger.info(f"開始建立模式 - ID: {pattern_id}, 名稱: {name}")
        
        try:
            # 轉換規則
            pattern_rules = [create_pattern_rule(**rule) for rule in rules]
            
            # 建立模式物件
            now = datetime.now().isoformat()
            pattern = create_pattern(
                pattern_id=pattern_id,
                name=name,
                description=description,
                rules=pattern_rules,
                case_id=case_id,
                xgboost_importance=xgboost_importance,
                performance_metrics=performance_metrics,
                created_at=now,
                updated_at=now,
                status='active',
                tags=tags or [],
                metadata=metadata or {}
            )
            
            # 驗證模式
            is_valid, errors = self.validator.validate_pattern(pattern)
            if not is_valid:
                self.logger.error(f"模式驗證失敗 - ID: {pattern_id}, 錯誤: {errors}")
                return {
                    'success': False,
                    'error': '模式驗證失敗',
                    'validation_errors': errors
                }
            
            # 儲存模式
            file_path = self.storage.save_pattern_to_json(pattern)
            
            self.logger.info(f"模式建立成功 - ID: {pattern_id}")
            
            return {
                'success': True,
                'pattern_id': pattern_id,
                'pattern': pattern.to_dict(),
                'file_path': file_path,
                'message': '模式建立成功'
            }
            
        except Exception as e:
            self.logger.error(f"建立模式失敗: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_pattern(self, pattern_id: str) -> Dict:
        """
        獲取模式
        
        Args:
            pattern_id: 模式 ID
            
        Returns:
            模式資料
        """
        try:
            if not self.storage.pattern_exists(pattern_id):
                return {
                    'success': False,
                    'error': f'模式不存在: {pattern_id}'
                }
            
            pattern = self.storage.load_pattern_from_json(pattern_id)
            
            return {
                'success': True,
                'pattern': pattern.to_dict()
            }
            
        except Exception as e:
            self.logger.error(f"獲取模式失敗: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_patterns(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        case_id: Optional[str] = None
    ) -> Dict:
        """
        列出模式
        
        Args:
            status: 狀態過濾
            tags: 標籤過濾
            case_id: 案例 ID 過濾
            
        Returns:
            模式列表
        """
        try:
            patterns = self.storage.query_patterns(
                status=status,
                tags=tags,
                case_id=case_id
            )
            
            # 轉換為字典格式
            pattern_list = [p.to_dict() for p in patterns]
            
            self.logger.info(f"列出模式 - 共 {len(pattern_list)} 個")
            
            return {
                'success': True,
                'count': len(pattern_list),
                'patterns': pattern_list
            }
            
        except Exception as e:
            self.logger.error(f"列出模式失敗: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_pattern(
        self,
        pattern_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        更新模式
        
        Args:
            pattern_id: 模式 ID
            name: 新名稱（可選）
            description: 新描述（可選）
            status: 新狀態（可選）
            tags: 新標籤（可選）
            metadata: 新元數據（可選）
            
        Returns:
            更新結果
        """
        try:
            # 載入現有模式
            if not self.storage.pattern_exists(pattern_id):
                return {
                    'success': False,
                    'error': f'模式不存在: {pattern_id}'
                }
            
            pattern = self.storage.load_pattern_from_json(pattern_id)
            
            # 更新欄位
            if name is not None:
                pattern.name = name
            if description is not None:
                pattern.description = description
            if status is not None:
                pattern.status = status
            if tags is not None:
                pattern.tags = tags
            if metadata is not None:
                pattern.metadata = metadata
            
            # 更新時間戳
            pattern.updated_at = datetime.now().isoformat()
            
            # 驗證更新後的模式
            is_valid, errors = self.validator.validate_pattern(pattern)
            if not is_valid:
                return {
                    'success': False,
                    'error': '模式驗證失敗',
                    'validation_errors': errors
                }
            
            # 儲存
            self.storage.save_pattern_to_json(pattern)
            
            self.logger.info(f"模式更新成功 - ID: {pattern_id}")
            
            return {
                'success': True,
                'pattern_id': pattern_id,
                'message': '模式更新成功'
            }
            
        except Exception as e:
            self.logger.error(f"更新模式失敗: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_pattern(self, pattern_id: str) -> Dict:
        """
        刪除模式
        
        Args:
            pattern_id: 模式 ID
            
        Returns:
            刪除結果
        """
        try:
            if not self.storage.pattern_exists(pattern_id):
                return {
                    'success': False,
                    'error': f'模式不存在: {pattern_id}'
                }
            
            success = self.storage.delete_pattern(pattern_id)
            
            if success:
                self.logger.info(f"模式刪除成功 - ID: {pattern_id}")
                return {
                    'success': True,
                    'message': '模式刪除成功'
                }
            else:
                return {
                    'success': False,
                    'error': '刪除失敗'
                }
            
        except Exception as e:
            self.logger.error(f"刪除模式失敗: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_all_patterns(self) -> Dict:
        """
        刪除所有模式
        
        Returns:
            刪除結果
        """
        try:
            patterns = self.storage.get_all_patterns()
            deleted_count = 0
            
            for pattern in patterns:
                if self.storage.delete_pattern(pattern.pattern_id):
                    deleted_count += 1
            
            self.logger.info(f"批量刪除完成 - 共刪除 {deleted_count} 個模式")
            return {
                'success': True,
                'message': f'已刪除 {deleted_count} 個模式',
                'deleted_count': deleted_count
            }
            
        except Exception as e:
            self.logger.error(f"批量刪除失敗: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_pattern_summary(self, pattern_id: str) -> Dict:
        """獲取模式摘要"""
        try:
            summary = self.storage.get_pattern_summary(pattern_id)
            return {
                'success': True,
                'summary': summary
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict:
        """獲取統計資訊"""
        try:
            library = self.storage.load_all_patterns()
            stats = library.get_statistics()
            
            return {
                'success': True,
                'statistics': stats
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
