# 完全動態指標系統 - 使用指南

## 系統概述

這是一個**完全動態、可無限擴展**的技術指標系統，讓您可以：

- ✅ 添加任何新指標，無需修改核心代碼
- ✅ 混合使用多種指標，自動避免特徵名稱衝突
- ✅ 參數動態變化，自動生成唯一特徵名稱
- ✅ 支援配置文件驅動的指標管理

**Date**: 2026-01-11  
**Author**: AI Agent

---

## 快速開始

### 1. 使用已註冊的指標（EMA）

```python
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams

# 建立提取器
extractor = FeatureExtractor()

# 配置 EMA 策略（系統已自動註冊）
params = StrategyParams(
    strategy_type='ema_three_line',
    params={
        'ema_short': 5,
        'ema_mid': 20,
        'ema_long': 60,
        'volume_threshold': 0.6
    },
    data_source='close'
)

# 提取特徵
features_df, feature_names = extractor.extract_features_from_strategy(df, params)

# 生成的特徵名稱：
# close_ema5_value, close_ema20_value, close_ema60_value
# close_ema5_20_distance, close_ema20_60_distance
# close_ema_trend_aligned, close_ema5_20_cross_signal
# volume_spike_60, taker_ratio_distance_60
# close_ema_entry_signal_score, close_ema_trend_consistency_5, close_ema_signal_strength
```

### 2. 註冊並使用新指標（RSI）

```python
from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
from momentum.FeatureEngineering.indicators import RSIExtractor

# 註冊 RSI 策略
registry = StrategyRegistry()
registry.register_strategy(
    name='rsi',
    description='Relative Strength Index',
    required_params=['period'],
    optional_params={'overbought': 70, 'oversold': 30},
    extractor=RSIExtractor()
)

# 使用 RSI 策略
params = StrategyParams(
    strategy_type='rsi',
    params={'period': 14, 'overbought': 70, 'oversold': 30},
    data_source='close'
)

features_df, feature_names = extractor.extract_features_from_strategy(df, params)

# 生成的特徵名稱：
# close_rsi14_value, close_rsi14_70_signal, close_rsi14_30_signal, close_rsi14_momentum
```

### 3. 混合多種指標

```python
# 註冊所有需要的指標
from momentum.FeatureEngineering.indicators import MACDExtractor

registry.register_strategy(
    name='macd',
    description='Moving Average Convergence Divergence',
    required_params=['fast', 'slow', 'signal'],
    extractor=MACDExtractor()
)

# 提取 EMA 特徵
params_ema = StrategyParams(
    strategy_type='ema_three_line',
    params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
    data_source='close'
)
df_ema, names_ema = extractor.extract_features_from_strategy(df.copy(), params_ema, include_basic_features=False)

# 提取 RSI 特徵
params_rsi = StrategyParams(
    strategy_type='rsi',
    params={'period': 14},
    data_source='close'
)
df_rsi, names_rsi = extractor.extract_features_from_strategy(df.copy(), params_rsi, include_basic_features=False)

# 提取 MACD 特徵
params_macd = StrategyParams(
    strategy_type='macd',
    params={'fast': 12, 'slow': 26, 'signal': 9},
    data_source='close'
)
df_macd, names_macd = extractor.extract_features_from_strategy(df.copy(), params_macd, include_basic_features=False)

# 合併所有特徵（無衝突！）
all_features = pd.concat([df_ema, df_rsi, df_macd], axis=1)
all_feature_names = names_ema + names_rsi + names_macd  # 20 個唯一特徵
```

---

## 如何添加新指標

### 步驟 1：建立提取器類別

建立文件：`momentum/FeatureEngineering/indicators/your_indicator_extractor.py`

```python
"""
Your Custom Indicator Extractor
"""

import pandas as pd
from typing import Dict, List, Tuple
from momentum.FeatureEngineering.strategy_registry import BaseStrategyExtractor
from api.core.logging import get_logger

logger = get_logger(__name__)


class YourIndicatorExtractor(BaseStrategyExtractor):
    """您的自定義指標提取器"""
    
    def validate_params(self, params: Dict) -> None:
        """驗證參數"""
        required = ['param1', 'param2']
        missing = [p for p in required if p not in params]
        
        if missing:
            raise ValueError(f"缺少必要參數: {missing}")
        
        # 添加您的驗證邏輯
        if params['param1'] < 0:
            raise ValueError("param1 必須 >= 0")
    
    def extract(
        self,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """提取特徵"""
        feature_names = []
        
        # 驗證數據源
        if data_source not in df.columns:
            raise ValueError(f"數據源 '{data_source}' 不存在")
        
        # 計算您的指標
        param1 = params['param1']
        param2 = params['param2']
        
        # 動態命名（重要！）
        feature_col = f"{data_source}_yourindicator{param1}_{param2}_value"
        df[feature_col] = self._calculate_indicator(df[data_source], param1, param2)
        feature_names.append(feature_col)
        
        # 添加更多特徵...
        
        return df, feature_names
    
    def _calculate_indicator(self, series, param1, param2):
        """您的指標計算邏輯"""
        # 實作您的算法
        return series.rolling(window=param1).mean() * param2
```

### 步驟 2：註冊到系統

```python
from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
from your_module import YourIndicatorExtractor

registry = StrategyRegistry()
registry.register_strategy(
    name='your_indicator',
    description='您的指標描述',
    required_params=['param1', 'param2'],
    extractor=YourIndicatorExtractor()
)
```

### 步驟 3：立即可用

```python
params = StrategyParams(
    strategy_type='your_indicator',
    params={'param1': 10, 'param2': 2},
    data_source='close'
)

features_df, feature_names = extractor.extract_features_from_strategy(df, params)
# 自動生成：close_yourindicator10_2_value
```

---

## 進階功能

### 1. 使用不同數據源

```python
# 使用 VOLUME 計算 EMA
params = StrategyParams(
    strategy_type='ema_three_line',
    params={'ema_short': 6, 'ema_mid': 15, 'ema_long': 28, 'volume_threshold': 0.7},
    data_source='volume'  # ← 改用 volume
)

# 生成特徵：volume_ema6_value, volume_ema15_value, volume_ema28_value
```

### 2. 相同指標不同參數

```python
# EMA(5,20,60)
params1 = StrategyParams(
    strategy_type='ema_three_line',
    params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
    data_source='close'
)

# EMA(10,30,90)
params2 = StrategyParams(
    strategy_type='ema_three_line',
    params={'ema_short': 10, 'ema_mid': 30, 'ema_long': 90, 'volume_threshold': 0.7},
    data_source='close'
)

# 兩組特徵完全不同，無衝突！
# 組1: close_ema5_value, close_ema20_value, close_ema60_value, ...
# 組2: close_ema10_value, close_ema30_value, close_ema90_value, ...
```

### 3. 查看已註冊策略

```python
registry = StrategyRegistry()

# 列出所有策略
strategies = registry.list_strategies()
print(strategies)  # ['ema_three_line', 'rsi', 'macd']

# 獲取策略詳情
strategy = registry.get_strategy('rsi')
print(strategy.description)        # 'Relative Strength Index'
print(strategy.required_params)    # ['period']
print(strategy.optional_params)    # {'overbought': 70, 'oversold': 30}
```

### 4. 配置文件驅動（未來擴展）

建立 `config/indicators_config.yaml`：

```yaml
strategies:
  - name: bollinger_bands
    extractor_class: momentum.FeatureEngineering.indicators.BollingerBandsExtractor
    required_params: [period, std_dev]
    
  - name: atr
    extractor_class: momentum.FeatureEngineering.indicators.ATRExtractor
    required_params: [period]
    
  # 無限添加...
```

啟動時自動載入（範例代碼）：

```python
import yaml
from importlib import import_module

def auto_register_from_config(config_path='config/indicators_config.yaml'):
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    registry = StrategyRegistry()
    
    for strategy in config['strategies']:
        module_path, class_name = strategy['extractor_class'].rsplit('.', 1)
        module = import_module(module_path)
        extractor_class = getattr(module, class_name)
        
        registry.register_strategy(
            name=strategy['name'],
            required_params=strategy['required_params'],
            extractor=extractor_class()
        )
    
    print(f"✅ 自動註冊了 {len(config['strategies'])} 個策略")

# 應用啟動時調用
auto_register_from_config()
```

---

## 已實作的指標

### 1. EMA (Exponential Moving Average)
- **文件**: `momentum/FeatureEngineering/indicators/ema_extractor.py`
- **策略名稱**: `ema_three_line`
- **必要參數**: `ema_short`, `ema_mid`, `ema_long`, `volume_threshold`
- **特徵數量**: 12 個（含信號特徵）
- **狀態**: ✅ 已註冊（自動）

### 2. RSI (Relative Strength Index)
- **文件**: `momentum/FeatureEngineering/indicators/rsi_extractor.py`
- **策略名稱**: `rsi`
- **必要參數**: `period`
- **可選參數**: `overbought=70`, `oversold=30`
- **特徵數量**: 4 個
- **狀態**: ⚠️ 需手動註冊

### 3. MACD (Moving Average Convergence Divergence)
- **文件**: `momentum/FeatureEngineering/indicators/macd_extractor.py`
- **策略名稱**: `macd`
- **必要參數**: `fast`, `slow`, `signal`
- **特徵數量**: 4 個
- **狀態**: ⚠️ 需手動註冊

---

## 常見問題

### Q1: 如何確保特徵名稱唯一？

**A**: 使用 `FeatureNamingConfig` 的動態命名方法，格式為 `{data_source}_{indicator}{params}_{feature_type}`。

範例：
- `close_ema5_value` - CLOSE 數據的 EMA(5) 值
- `volume_ema6_value` - VOLUME 數據的 EMA(6) 值
- `close_rsi14_value` - CLOSE 數據的 RSI(14) 值

### Q2: 可以添加幾十種指標嗎？

**A**: 可以！系統設計為無限擴展：
1. 實作 `BaseStrategyExtractor` 子類別
2. 註冊到 `StrategyRegistry`
3. 立即可用

無需修改 `feature_extractor.py` 或其他核心代碼。

### Q3: 如何處理不同指標的參數結構？

**A**: 每個提取器自己定義參數結構：
- EMA: `{'ema_short', 'ema_mid', 'ema_long', 'volume_threshold'}`
- RSI: `{'period', 'overbought', 'oversold'}`
- MACD: `{'fast', 'slow', 'signal'}`

系統通過 `validate_params()` 方法確保參數正確。

### Q4: 舊代碼需要修改嗎？

**A**: 不需要！`extract_ema_features()` 仍然存在於 `feature_extractor.py` 中作為向後相容。新代碼應使用動態系統：

```python
# 舊方式（仍可用）
features_df, names = extractor.extract_ema_features(df, ema_params, 'close')

# 新方式（推薦）
params = StrategyParams(strategy_type='ema_three_line', params=ema_params, data_source='close')
features_df, names = extractor.extract_features_from_strategy(df, params)
```

---

## 測試驗證

執行完整測試：

```bash
python test_dynamic_indicator_system.py
```

測試覆蓋：
- ✅ EMA 動態提取
- ✅ RSI 動態提取
- ✅ MACD 動態提取
- ✅ 混合多種指標無衝突
- ✅ 策略列表查詢

---

## 下一步

1. **Phase 3-6**: 繼續實作測試檔案更新、Trial 比較工具、Pipeline 配置修正、整合測試
2. **添加更多指標**: Bollinger Bands, ATR, Ichimoku Cloud, Stochastic Oscillator 等
3. **配置文件驅動**: 實作 YAML 配置自動註冊機制
4. **前端整合**: API 路由支援動態指標選擇

---

**系統已完成核心架構，可無限擴展！**
