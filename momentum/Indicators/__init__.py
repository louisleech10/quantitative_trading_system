"""
Indicators Module - 多數據源指標計算引擎

本模塊提供統一的技術指標計算框架，支援多種數據源和指標類型。

主要組件：
- DataSourceEnum: 8種數據源枚舉
- DataSourceManager: 數據源管理器
- BaseIndicator: 指標抽象基類
- EMAIndicator: EMA 指標實作（類裝飾器版本）
- register_functional_indicator: 函數式指標註冊（混合式架構）

架構支持：
- 類裝飾器模式：繼承 BaseIndicator + @register_indicator
- 函數式模式：純函數 + register_functional_indicator（推薦新指標使用）

使用範例（類裝飾器）：
    >>> from momentum.Indicators import EMAIndicator, DataSourceManager, DataSourceEnum
    >>> manager = DataSourceManager()
    >>> indicator = EMAIndicator()
    >>> close = manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)
    >>> ema = indicator.calculate(close, period=20)

使用範例（函數式 - 通過 IndicatorEngine）：
    >>> from momentum.Indicators import IndicatorEngine, DataSourceEnum
    >>> engine = IndicatorEngine()
    >>> result = engine.calculate_indicator("ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=20)

使用範例（函數式 - 直接調用）：
    >>> from momentum.Indicators.ema import ema
    >>> result = ema(close_data, period=20)
"""

__version__ = "0.1.0"

# 導出核心類型
from .types import (
    DataSourceEnum,
    IndicatorParams,
    IndicatorResult,
    IndicatorConfig,
    ParamRange
)

# 導出核心類
from .data_source_manager import DataSourceManager
from .base_indicator import BaseIndicator

# 導出指標
from .ema_indicator import EMAIndicator

# 導出引擎
from .indicator_engine import IndicatorEngine, register_indicator

# 導出功能包裝器（函數式架構）
from .functional_wrapper import register_functional_indicator, unregister_functional_indicator

# 導出配置載入器
from .config_loader import ConfigLoader, get_global_loader, load_indicator_config

# 導入函數式 EMA（觸發自動註冊）
# 注意：這會自動註冊 "ema" 到 IndicatorEngine
import momentum.Indicators.ema  # noqa: F401

__all__ = [
    # 類型
    "DataSourceEnum",
    "IndicatorParams",
    "IndicatorResult",
    "IndicatorConfig",
    "ParamRange",
    # 核心類
    "DataSourceManager",
    "BaseIndicator",
    # 引擎
    "IndicatorEngine",
    "register_indicator",
    # 函數式架構
    "register_functional_indicator",
    "unregister_functional_indicator",
    # 配置
    "ConfigLoader",
    "get_global_loader",
    "load_indicator_config",
    # 指標（類裝飾器版本）
    "EMAIndicator",
]
