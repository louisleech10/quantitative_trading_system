"""
Indicators Module - 多數據源指標計算引擎

本模塊提供統一的技術指標計算框架，支援多種數據源和指標類型。

主要組件：
- DataSourceEnum: 8種數據源枚舉
- DataSourceManager: 數據源管理器
- BaseIndicator: 指標抽象基類
- EMAIndicator: EMA 指標實作

使用範例：
    >>> from momentum.Indicators import EMAIndicator, DataSourceManager, DataSourceEnum
    >>> manager = DataSourceManager()
    >>> indicator = EMAIndicator()
    >>> close = manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)
    >>> ema = indicator.calculate(close, period=20)
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

# 導出配置載入器
from .config_loader import ConfigLoader, get_global_loader, load_indicator_config

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
    # 配置
    "ConfigLoader",
    "get_global_loader",
    "load_indicator_config",
    # 指標
    "EMAIndicator",
]
