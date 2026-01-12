"""
Data Source Registry - 數據源註冊系統

解決問題：
1. 硬編碼數據源清單 → 動態註冊機制
2. 未來擴充（Glassnode, 台股, 美股）無需修改核心程式碼
3. 數據源驗證自動化

Author: AI Agent
Date: 2026-01-11
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class DataSourceCategory(Enum):
    """數據源類別"""
    PRICE = "price"  # 價格類（OHLC）
    VOLUME = "volume"  # 成交量類
    RATIO = "ratio"  # 比率類（0-1）
    ONCHAIN = "onchain"  # 鏈上數據（Glassnode）
    MARGIN = "margin"  # 融資融券（台股）
    OPTION = "option"  # 期權數據（美股）
    CUSTOM = "custom"  # 自訂數據


@dataclass
class DataSourceDefinition:
    """數據源定義"""
    name: str  # 數據源名稱（e.g., 'close', 'nvt_ratio'）
    category: DataSourceCategory  # 數據源類別
    description: str  # 數據源描述
    column_name: str  # DataFrame 欄位名稱
    value_range: Optional[tuple] = None  # 數值範圍（用於驗證）
    required: bool = False  # 是否為必須欄位
    validator: Optional[Callable] = None  # 自訂驗證函式


class DataSourceRegistry:
    """
    數據源註冊表
    
    特點：
    - 動態註冊：新增數據源無需修改核心程式碼
    - 自動驗證：檢查 DataFrame 是否包含所需欄位
    - 分類管理：按照數據類型分類（價格、成交量、鏈上等）
    
    使用範例：
    ```python
    # 註冊新數據源
    registry = DataSourceRegistry()
    registry.register(
        name='nvt_ratio',
        category=DataSourceCategory.ONCHAIN,
        description='Network Value to Transactions Ratio',
        column_name='nvt_ratio',
        value_range=(0, 100)
    )
    
    # 驗證數據源
    if registry.is_valid('nvt_ratio', df):
        # 使用該數據源
        ema = df['nvt_ratio'].ewm(span=20).mean()
    ```
    """
    
    _instance = None  # Singleton 實例
    
    def __new__(cls):
        """實作 Singleton 模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化註冊表（只執行一次）"""
        if self._initialized:
            return
        
        self._sources: Dict[str, DataSourceDefinition] = {}
        self._register_default_sources()
        self._initialized = True
    
    def _register_default_sources(self):
        """註冊預設數據源（當前系統支援的）"""
        # 價格數據
        self.register(
            name='close',
            category=DataSourceCategory.PRICE,
            description='收盤價',
            column_name='close',
            required=True
        )
        self.register(
            name='open',
            category=DataSourceCategory.PRICE,
            description='開盤價',
            column_name='open',
            required=True
        )
        self.register(
            name='high',
            category=DataSourceCategory.PRICE,
            description='最高價',
            column_name='high',
            required=True
        )
        self.register(
            name='low',
            category=DataSourceCategory.PRICE,
            description='最低價',
            column_name='low',
            required=True
        )
        
        # 成交量數據
        self.register(
            name='volume',
            category=DataSourceCategory.VOLUME,
            description='成交量',
            column_name='volume',
            required=True
        )
        self.register(
            name='taker_buy_volume',
            category=DataSourceCategory.VOLUME,
            description='主動買入成交量',
            column_name='taker_buy_volume',
            required=False
        )
        
        # 比率數據
        self.register(
            name='taker_ratio',
            category=DataSourceCategory.RATIO,
            description='主動買入比率',
            column_name='taker_ratio',
            value_range=(0, 1),
            required=False
        )
    
    def register(
        self,
        name: str,
        category: DataSourceCategory,
        description: str,
        column_name: str,
        value_range: Optional[tuple] = None,
        required: bool = False,
        validator: Optional[Callable] = None
    ):
        """
        註冊新數據源
        
        Args:
            name: 數據源名稱
            category: 數據源類別
            description: 數據源描述
            column_name: DataFrame 欄位名稱
            value_range: 數值範圍（用於驗證）
            required: 是否為必須欄位
            validator: 自訂驗證函式
        """
        if name in self._sources:
            raise ValueError(f"數據源 '{name}' 已經註冊")
        
        self._sources[name] = DataSourceDefinition(
            name=name,
            category=category,
            description=description,
            column_name=column_name,
            value_range=value_range,
            required=required,
            validator=validator
        )
    
    def get(self, name: str) -> Optional[DataSourceDefinition]:
        """獲取數據源定義"""
        return self._sources.get(name)
    
    def is_registered(self, name: str) -> bool:
        """檢查數據源是否已註冊"""
        return name in self._sources
    
    def list_sources(
        self,
        category: Optional[DataSourceCategory] = None,
        required_only: bool = False
    ) -> List[str]:
        """
        列出所有數據源
        
        Args:
            category: 篩選特定類別
            required_only: 只列出必須欄位
        
        Returns:
            數據源名稱列表
        """
        sources = []
        for name, definition in self._sources.items():
            if category and definition.category != category:
                continue
            if required_only and not definition.required:
                continue
            sources.append(name)
        return sources
    
    def validate_dataframe(
        self,
        df,
        data_source: str,
        raise_error: bool = True
    ) -> bool:
        """
        驗證 DataFrame 是否包含指定數據源
        
        Args:
            df: pandas DataFrame
            data_source: 數據源名稱
            raise_error: 是否拋出錯誤（False 則返回 bool）
        
        Returns:
            是否有效
        """
        if not self.is_registered(data_source):
            if raise_error:
                available = ', '.join(self.list_sources())
                raise ValueError(
                    f"未知的數據源: '{data_source}'\n"
                    f"可用的數據源: {available}\n"
                    f"提示：使用 DataSourceRegistry().register() 註冊新數據源"
                )
            return False
        
        definition = self.get(data_source)
        column_name = definition.column_name
        
        # 檢查欄位是否存在
        if column_name not in df.columns:
            if raise_error:
                raise ValueError(
                    f"DataFrame 缺少數據源欄位: '{column_name}'\n"
                    f"可用欄位: {list(df.columns)}"
                )
            return False
        
        # 檢查數值範圍
        if definition.value_range:
            min_val, max_val = definition.value_range
            actual_min = df[column_name].min()
            actual_max = df[column_name].max()
            
            if actual_min < min_val or actual_max > max_val:
                if raise_error:
                    raise ValueError(
                        f"數據源 '{data_source}' 數值超出範圍\n"
                        f"預期範圍: [{min_val}, {max_val}]\n"
                        f"實際範圍: [{actual_min:.4f}, {actual_max:.4f}]"
                    )
                return False
        
        # 自訂驗證
        if definition.validator:
            if not definition.validator(df[column_name]):
                if raise_error:
                    raise ValueError(f"數據源 '{data_source}' 自訂驗證失敗")
                return False
        
        return True
    
    def get_category_description(self, category: DataSourceCategory) -> str:
        """獲取類別描述"""
        descriptions = {
            DataSourceCategory.PRICE: "價格類數據（OHLC）",
            DataSourceCategory.VOLUME: "成交量類數據",
            DataSourceCategory.RATIO: "比率類數據（0-1）",
            DataSourceCategory.ONCHAIN: "鏈上數據（Glassnode）",
            DataSourceCategory.MARGIN: "融資融券數據（台股）",
            DataSourceCategory.OPTION: "期權數據（美股）",
            DataSourceCategory.CUSTOM: "自訂數據"
        }
        return descriptions.get(category, "未知類別")


# 全域實例（Singleton）
data_source_registry = DataSourceRegistry()


# ==================== 擴充範例 ====================

def register_glassnode_sources():
    """註冊 Glassnode 鏈上數據源（未來擴充）"""
    registry = DataSourceRegistry()
    
    # NVT Ratio
    registry.register(
        name='nvt_ratio',
        category=DataSourceCategory.ONCHAIN,
        description='Network Value to Transactions Ratio',
        column_name='nvt_ratio',
        value_range=(0, 200)
    )
    
    # MVRV Ratio
    registry.register(
        name='mvrv_ratio',
        category=DataSourceCategory.ONCHAIN,
        description='Market Value to Realized Value Ratio',
        column_name='mvrv_ratio',
        value_range=(0, 10)
    )
    
    # SOPR (Spent Output Profit Ratio)
    registry.register(
        name='sopr',
        category=DataSourceCategory.ONCHAIN,
        description='Spent Output Profit Ratio',
        column_name='sopr',
        value_range=(0, 2)
    )


def register_taiwan_stock_sources():
    """註冊台股專屬數據源（未來擴充）"""
    registry = DataSourceRegistry()
    
    # 融資餘額
    registry.register(
        name='margin_balance',
        category=DataSourceCategory.MARGIN,
        description='融資餘額',
        column_name='margin_balance',
        value_range=(0, None)
    )
    
    # 融券餘額
    registry.register(
        name='short_balance',
        category=DataSourceCategory.MARGIN,
        description='融券餘額',
        column_name='short_balance',
        value_range=(0, None)
    )
    
    # 融資使用率
    registry.register(
        name='margin_utilization',
        category=DataSourceCategory.MARGIN,
        description='融資使用率',
        column_name='margin_utilization',
        value_range=(0, 1)
    )


def register_us_stock_sources():
    """註冊美股專屬數據源（未來擴充）"""
    registry = DataSourceRegistry()
    
    # Put/Call Ratio
    registry.register(
        name='put_call_ratio',
        category=DataSourceCategory.OPTION,
        description='Put/Call Ratio',
        column_name='put_call_ratio',
        value_range=(0, 5)
    )
    
    # Implied Volatility
    registry.register(
        name='implied_volatility',
        category=DataSourceCategory.OPTION,
        description='Implied Volatility',
        column_name='implied_volatility',
        value_range=(0, 1)
    )


# 使用範例
if __name__ == '__main__':
    # 獲取註冊表
    registry = DataSourceRegistry()
    
    # 列出所有數據源
    print("所有數據源:", registry.list_sources())
    
    # 列出價格類數據源
    print("價格類數據源:", registry.list_sources(category=DataSourceCategory.PRICE))
    
    # 檢查數據源是否註冊
    print("close 是否註冊:", registry.is_registered('close'))
    print("nvt_ratio 是否註冊:", registry.is_registered('nvt_ratio'))
    
    # 註冊 Glassnode 數據源
    register_glassnode_sources()
    print("\n註冊 Glassnode 後:")
    print("nvt_ratio 是否註冊:", registry.is_registered('nvt_ratio'))
    print("鏈上數據源:", registry.list_sources(category=DataSourceCategory.ONCHAIN))
