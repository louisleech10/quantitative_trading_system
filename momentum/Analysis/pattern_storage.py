"""
Pattern Storage - 模式儲存管理

使用 JSON 格式儲存和讀取模式

Author: AI Agent
Date: 2026-01-10
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

from momentum.Analysis.pattern_definition import Pattern, PatternLibrary
from api.core.logging import get_logger

logger = get_logger(__name__)


class PatternStorage:
    """
    模式儲存管理器
    
    使用 JSON 格式儲存模式至檔案系統
    """
    
    def __init__(self, base_path: str = "data_cache/patterns"):
        """
        Args:
            base_path: 模式儲存根目錄
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        
        # 索引檔案路徑
        self.index_path = self.base_path / "_index.json"
    
    def save_pattern_to_json(self, pattern: Pattern) -> str:
        """
        儲存模式至 JSON 檔案
        
        Args:
            pattern: 模式物件
            
        Returns:
            檔案路徑
        """
        file_path = self.base_path / f"{pattern.pattern_id}.json"
        
        self.logger.info(f"開始儲存模式 - ID: {pattern.pattern_id}, 檔案: {file_path}")
        
        try:
            # 儲存模式
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(pattern.to_json())
            
            # 更新索引
            self._update_index(pattern)
            
            file_size_kb = file_path.stat().st_size / 1024
            
            self.logger.info(
                f"模式儲存完成 - 檔案大小: {file_size_kb:.2f} KB, "
                f"規則數: {len(pattern.rules)}"
            )
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"模式儲存失敗: {str(e)}", exc_info=True)
            raise
    
    def load_pattern_from_json(self, pattern_id: str) -> Pattern:
        """
        從 JSON 檔案讀取模式
        
        Args:
            pattern_id: 模式 ID
            
        Returns:
            模式物件
        """
        file_path = self.base_path / f"{pattern_id}.json"
        
        if not file_path.exists():
            raise FileNotFoundError(f"模式檔案不存在: {file_path}")
        
        self.logger.info(f"開始讀取模式 - ID: {pattern_id}, 檔案: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            pattern = Pattern.from_json(json_str)
            
            self.logger.info(
                f"模式讀取完成 - 規則數: {len(pattern.rules)}"
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"模式讀取失敗: {str(e)}", exc_info=True)
            raise
    
    def pattern_exists(self, pattern_id: str) -> bool:
        """檢查模式檔案是否存在"""
        file_path = self.base_path / f"{pattern_id}.json"
        return file_path.exists()
    
    def delete_pattern(self, pattern_id: str) -> bool:
        """
        刪除模式檔案
        
        Args:
            pattern_id: 模式 ID
            
        Returns:
            是否成功刪除
        """
        file_path = self.base_path / f"{pattern_id}.json"
        
        if not file_path.exists():
            self.logger.warning(f"模式檔案不存在，無法刪除: {file_path}")
            return False
        
        try:
            file_path.unlink()
            
            # 更新索引
            self._remove_from_index(pattern_id)
            
            self.logger.info(f"模式檔案已刪除: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"刪除模式檔案失敗: {str(e)}", exc_info=True)
            return False
    
    def list_pattern_files(self) -> List[Dict]:
        """
        列出所有模式檔案
        
        Returns:
            模式檔案列表
        """
        pattern_files = []
        
        for file_path in self.base_path.glob("*.json"):
            # 跳過索引檔案
            if file_path.name == "_index.json":
                continue
            
            pattern_id = file_path.stem
            
            pattern_files.append({
                'pattern_id': pattern_id,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'modified_time': datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat()
            })
        
        # 按修改時間排序
        pattern_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return pattern_files
    
    def load_all_patterns(self) -> PatternLibrary:
        """
        載入所有模式至 PatternLibrary
        
        Returns:
            PatternLibrary 物件
        """
        library = PatternLibrary()
        
        for file_info in self.list_pattern_files():
            try:
                pattern = self.load_pattern_from_json(file_info['pattern_id'])
                library.add_pattern(pattern)
            except Exception as e:
                self.logger.error(
                    f"載入模式失敗 - ID: {file_info['pattern_id']}, 錯誤: {str(e)}"
                )
        
        self.logger.info(f"載入完成 - 共 {library.get_pattern_count()} 個模式")
        
        return library
    
    def query_patterns(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        case_id: Optional[str] = None,
        min_performance: Optional[float] = None
    ) -> List[Pattern]:
        """
        查詢模式（依條件過濾）
        
        Args:
            status: 狀態過濾 ("active" | "archived" | "testing")
            tags: 標籤過濾
            case_id: 案例 ID 過濾
            min_performance: 最小效能指標（precision）
            
        Returns:
            符合條件的模式列表
        """
        # 載入所有模式
        library = self.load_all_patterns()
        patterns = library.list_patterns(status=status, tags=tags)
        
        # 依案例 ID 過濾
        if case_id:
            patterns = [p for p in patterns if p.case_id == case_id]
        
        # 依效能過濾
        if min_performance is not None:
            patterns = [
                p for p in patterns
                if p.performance_metrics.get('precision', 0) >= min_performance
            ]
        
        return patterns
    
    def get_pattern_summary(self, pattern_id: str) -> Dict:
        """
        獲取模式摘要資訊（不載入完整模式）
        
        Args:
            pattern_id: 模式 ID
            
        Returns:
            模式摘要字典
        """
        pattern = self.load_pattern_from_json(pattern_id)
        
        return {
            'pattern_id': pattern.pattern_id,
            'name': pattern.name,
            'description': pattern.description,
            'rule_count': len(pattern.rules),
            'rule_condition': pattern.get_rule_condition_string(),
            'case_id': pattern.case_id,
            'performance_metrics': pattern.performance_metrics,
            'status': pattern.status,
            'tags': pattern.tags,
            'created_at': pattern.created_at,
            'updated_at': pattern.updated_at
        }
    
    def _update_index(self, pattern: Pattern):
        """更新索引檔案"""
        try:
            # 讀取現有索引
            index = self._load_index()
            
            # 更新索引
            index[pattern.pattern_id] = {
                'name': pattern.name,
                'status': pattern.status,
                'tags': pattern.tags,
                'case_id': pattern.case_id,
                'updated_at': pattern.updated_at
            }
            
            # 儲存索引
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.warning(f"更新索引失敗: {str(e)}")
    
    def _remove_from_index(self, pattern_id: str):
        """從索引中移除"""
        try:
            index = self._load_index()
            
            if pattern_id in index:
                del index[pattern_id]
            
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.warning(f"從索引移除失敗: {str(e)}")
    
    def _load_index(self) -> Dict:
        """載入索引"""
        if not self.index_path.exists():
            return {}
        
        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
