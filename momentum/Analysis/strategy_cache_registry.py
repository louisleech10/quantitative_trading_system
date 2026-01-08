"""
策略快取計算器註冊表

提供裝飾器模式讓策略註冊自己的快取信號計算函式，
使 IndicatorCache 可以透過策略名稱動態呼叫對應的計算邏輯，
無需在核心程式碼中硬編碼策略類型判斷。

設計原則:
- 開放封閉原則: 新增策略只需新增裝飾器函式，無需修改核心程式碼
- 單一職責: 每個策略計算器只負責自己的信號邏輯
- 類型安全: 使用 TypedDict 定義參數結構

使用方式:
```python
from momentum.Analysis.strategy_cache_registry import (
    register_strategy_cache,
    strategy_cache_registry
)

@register_strategy_cache("my_strategy")
def calc_my_strategy(indicator_values: Dict[str, np.ndarray]) -> np.ndarray:
    '''
    Args:
        indicator_values: {param_name: indicator_array}
            例如: {"short_period": ema_short, "long_period": ema_long}
    
    Returns:
        np.ndarray: boolean 信號陣列
    '''
    short = indicator_values["short_period"]
    long = indicator_values["long_period"]
    return short > long

# 在 IndicatorCache 中使用
calculator = strategy_cache_registry.get_calculator("my_strategy")
signals = calculator(indicator_values)
```

Author: Claude (Optuna Cache Optimization Phase)
Date: 2026-01-08
"""

import logging
from typing import Callable, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


# 策略快取計算函式的類型定義
# 輸入: {param_name: np.ndarray} → 輸出: np.ndarray (boolean)
StrategyCacheCalculator = Callable[[Dict[str, np.ndarray]], np.ndarray]


class StrategyCacheRegistry:
    """
    策略快取計算器註冊表
    
    管理所有策略的快取信號計算函式，提供：
    - 註冊: 透過裝飾器或手動註冊
    - 查詢: 根據策略名稱獲取計算函式
    - 檢查: 判斷策略是否已註冊
    """
    
    def __init__(self):
        self._calculators: Dict[str, StrategyCacheCalculator] = {}
        self._descriptions: Dict[str, str] = {}
    
    def register(
        self,
        strategy_name: str,
        calculator: StrategyCacheCalculator,
        description: str = ""
    ) -> None:
        """
        註冊策略快取計算器
        
        Args:
            strategy_name: 策略名稱 (必須與 strategies.yaml 中的 key 一致)
            calculator: 計算函式 (Dict[str, np.ndarray] -> np.ndarray)
            description: 策略描述 (可選)
        """
        if strategy_name in self._calculators:
            logger.warning(
                f"策略 '{strategy_name}' 已註冊，將被覆蓋"
            )
        
        self._calculators[strategy_name] = calculator
        self._descriptions[strategy_name] = description
        
        logger.debug(f"已註冊策略快取計算器: {strategy_name}")
    
    def get_calculator(self, strategy_name: str) -> Optional[StrategyCacheCalculator]:
        """
        獲取策略的快取計算函式
        
        Args:
            strategy_name: 策略名稱
            
        Returns:
            計算函式，或 None (未註冊時)
        """
        return self._calculators.get(strategy_name)
    
    def has_strategy(self, strategy_name: str) -> bool:
        """
        檢查策略是否已註冊
        
        Args:
            strategy_name: 策略名稱
            
        Returns:
            bool: 是否已註冊
        """
        return strategy_name in self._calculators
    
    def list_strategies(self) -> list:
        """
        列出所有已註冊的策略
        
        Returns:
            策略名稱列表
        """
        return list(self._calculators.keys())
    
    def get_description(self, strategy_name: str) -> str:
        """
        獲取策略描述
        
        Args:
            strategy_name: 策略名稱
            
        Returns:
            描述字串
        """
        return self._descriptions.get(strategy_name, "")


# 全域單例註冊表
strategy_cache_registry = StrategyCacheRegistry()


def register_strategy_cache(
    strategy_name: str,
    description: str = ""
) -> Callable[[StrategyCacheCalculator], StrategyCacheCalculator]:
    """
    裝飾器: 註冊策略快取計算器
    
    使用方式:
    ```python
    @register_strategy_cache("three_line", "三線排列策略")
    def calc_three_line(values: Dict[str, np.ndarray]) -> np.ndarray:
        short = values["short_period"]
        mid = values["mid_period"]
        long = values["long_period"]
        return (short > mid) & (mid > long)
    ```
    
    Args:
        strategy_name: 策略名稱 (必須與 strategies.yaml 中的 key 一致)
        description: 策略描述 (可選)
        
    Returns:
        裝飾器函式
    """
    def decorator(func: StrategyCacheCalculator) -> StrategyCacheCalculator:
        strategy_cache_registry.register(strategy_name, func, description)
        return func
    
    return decorator


# ============================================================
# 內建策略快取計算器
# ============================================================

@register_strategy_cache(
    "three_line",
    "三線排列策略: short > mid > long"
)
def calc_three_line_signals(indicator_values: Dict[str, np.ndarray]) -> np.ndarray:
    """
    計算三線排列信號
    
    策略邏輯: short_period EMA > mid_period EMA > long_period EMA
    
    Args:
        indicator_values: {
            "short_period": np.ndarray,  # 短期指標值
            "mid_period": np.ndarray,    # 中期指標值
            "long_period": np.ndarray    # 長期指標值
        }
    
    Returns:
        np.ndarray: boolean 信號陣列
    """
    short = indicator_values["short_period"]
    mid = indicator_values["mid_period"]
    long = indicator_values["long_period"]
    
    return (short > mid) & (mid > long)


@register_strategy_cache(
    "short_long_cross",
    "短長交叉策略: short > long"
)
def calc_short_long_cross_signals(indicator_values: Dict[str, np.ndarray]) -> np.ndarray:
    """
    計算短長交叉信號
    
    策略邏輯: short_period EMA > long_period EMA (金叉持續狀態)
    
    Args:
        indicator_values: {
            "short_period": np.ndarray,  # 短期指標值
            "long_period": np.ndarray    # 長期指標值
        }
    
    Returns:
        np.ndarray: boolean 信號陣列
    """
    short = indicator_values["short_period"]
    long = indicator_values["long_period"]
    
    return short > long


@register_strategy_cache(
    "mid_long_cross",
    "中長交叉策略: mid > long"
)
def calc_mid_long_cross_signals(indicator_values: Dict[str, np.ndarray]) -> np.ndarray:
    """
    計算中長交叉信號
    
    策略邏輯: mid_period EMA > long_period EMA
    
    Args:
        indicator_values: {
            "mid_period": np.ndarray,    # 中期指標值
            "long_period": np.ndarray    # 長期指標值
        }
    
    Returns:
        np.ndarray: boolean 信號陣列
    """
    mid = indicator_values["mid_period"]
    long = indicator_values["long_period"]
    
    return mid > long


# 模組載入時自動註冊內建策略
logger.info(
    f"策略快取計算器已載入: {strategy_cache_registry.list_strategies()}"
)
