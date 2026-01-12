"""
Pattern Definition - 模式定義

定義交易模式的資料結構

Author: AI Agent
Date: 2026-01-10
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class PatternRule:
    """單條模式規則"""
    feature: str  # 特徵名稱 (e.g., "ema_distance_5_20")
    operator: str  # 運算符 (">" | "<" | ">=" | "<=" | "==" | "!=")
    threshold: float  # 閾值
    description: str  # 中文描述 (e.g., "EMA5 高於 EMA20 2%以上")
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PatternRule':
        """從字典建立"""
        return cls(**data)
    
    def to_condition_string(self) -> str:
        """轉換為條件字串"""
        return f"{self.feature} {self.operator} {self.threshold}"
    
    def evaluate(self, feature_value: float) -> bool:
        """評估規則是否滿足"""
        if self.operator == '>':
            return feature_value > self.threshold
        elif self.operator == '<':
            return feature_value < self.threshold
        elif self.operator == '>=':
            return feature_value >= self.threshold
        elif self.operator == '<=':
            return feature_value <= self.threshold
        elif self.operator == '==':
            return abs(feature_value - self.threshold) < 1e-6
        elif self.operator == '!=':
            return abs(feature_value - self.threshold) >= 1e-6
        else:
            raise ValueError(f"不支援的運算符: {self.operator}")


@dataclass
class Pattern:
    """完整模式定義"""
    pattern_id: str  # 唯一 ID (e.g., "PAT_001")
    name: str  # 模式名稱 (e.g., "強勢突破模式")
    description: str  # 模式描述
    rules: List[PatternRule]  # 規則列表 (AND 關係)
    case_id: str  # 來源案例 ID
    xgboost_importance: Dict[str, float]  # XGBoost 特徵重要性
    performance_metrics: Dict[str, float]  # 模式表現指標
    created_at: str  # ISO 格式時間
    updated_at: str  # ISO 格式時間
    status: str = "active"  # "active" | "archived" | "testing"
    tags: List[str] = field(default_factory=list)  # 標籤 (e.g., ["趨勢", "成交量"])
    metadata: Dict = field(default_factory=dict)  # 其他元數據
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'pattern_id': self.pattern_id,
            'name': self.name,
            'description': self.description,
            'rules': [rule.to_dict() for rule in self.rules],
            'case_id': self.case_id,
            'xgboost_importance': self.xgboost_importance,
            'performance_metrics': self.performance_metrics,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'status': self.status,
            'tags': self.tags,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Pattern':
        """從字典建立"""
        # 轉換規則列表
        rules = [PatternRule.from_dict(rule) for rule in data['rules']]
        
        return cls(
            pattern_id=data['pattern_id'],
            name=data['name'],
            description=data['description'],
            rules=rules,
            case_id=data['case_id'],
            xgboost_importance=data['xgboost_importance'],
            performance_metrics=data['performance_metrics'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            status=data.get('status', 'active'),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {})
        )
    
    def to_json(self) -> str:
        """轉換為 JSON 字串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Pattern':
        """從 JSON 字串建立"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_rule_condition_string(self) -> str:
        """獲取所有規則的條件字串（AND 組合）"""
        conditions = [rule.to_condition_string() for rule in self.rules]
        return " AND ".join(conditions)
    
    def evaluate_all_rules(self, feature_values: Dict[str, float]) -> bool:
        """評估所有規則是否滿足（AND 關係）"""
        for rule in self.rules:
            if rule.feature not in feature_values:
                return False
            if not rule.evaluate(feature_values[rule.feature]):
                return False
        return True
    
    def get_feature_list(self) -> List[str]:
        """獲取所有使用的特徵列表"""
        return [rule.feature for rule in self.rules]


class PatternLibrary:
    """模式庫管理器"""
    
    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}
    
    def add_pattern(self, pattern: Pattern):
        """新增模式"""
        self.patterns[pattern.pattern_id] = pattern
    
    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """獲取模式"""
        return self.patterns.get(pattern_id)
    
    def remove_pattern(self, pattern_id: str) -> bool:
        """移除模式"""
        if pattern_id in self.patterns:
            del self.patterns[pattern_id]
            return True
        return False
    
    def list_patterns(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Pattern]:
        """列出模式（可依狀態和標籤過濾）"""
        result = list(self.patterns.values())
        
        # 依狀態過濾
        if status:
            result = [p for p in result if p.status == status]
        
        # 依標籤過濾
        if tags:
            result = [
                p for p in result
                if any(tag in p.tags for tag in tags)
            ]
        
        return result
    
    def search_patterns(self, keyword: str) -> List[Pattern]:
        """搜尋模式（依名稱或描述）"""
        keyword_lower = keyword.lower()
        return [
            p for p in self.patterns.values()
            if keyword_lower in p.name.lower() or keyword_lower in p.description.lower()
        ]
    
    def get_patterns_by_case(self, case_id: str) -> List[Pattern]:
        """獲取指定案例的所有模式"""
        return [
            p for p in self.patterns.values()
            if p.case_id == case_id
        ]
    
    def get_pattern_count(self) -> int:
        """獲取模式總數"""
        return len(self.patterns)
    
    def get_statistics(self) -> Dict:
        """獲取統計資訊"""
        patterns = list(self.patterns.values())
        
        if not patterns:
            return {
                'total': 0,
                'active': 0,
                'archived': 0,
                'testing': 0,
                'avg_rules_per_pattern': 0,
                'top_tags': []
            }
        
        # 統計狀態
        status_count = {
            'active': sum(1 for p in patterns if p.status == 'active'),
            'archived': sum(1 for p in patterns if p.status == 'archived'),
            'testing': sum(1 for p in patterns if p.status == 'testing')
        }
        
        # 統計規則數量
        total_rules = sum(len(p.rules) for p in patterns)
        avg_rules = total_rules / len(patterns) if patterns else 0
        
        # 統計標籤
        tag_count = {}
        for p in patterns:
            for tag in p.tags:
                tag_count[tag] = tag_count.get(tag, 0) + 1
        
        top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total': len(patterns),
            'active': status_count['active'],
            'archived': status_count['archived'],
            'testing': status_count['testing'],
            'avg_rules_per_pattern': avg_rules,
            'top_tags': top_tags
        }
