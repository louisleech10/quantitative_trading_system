# 指標計算引擎 API 使用文檔

> **面向用戶**: Phase 3.2+ 任務開發者、量化策略研究員
> **更新時間**: 2025-11-01
> **API 版本**: v0.1.0

本文檔介紹如何使用指標計算引擎進行技術指標計算。

---

## 📋 目錄

1. [快速開始](#快速開始)
2. [核心 API](#核心-api)
3. [常見場景](#常見場景)
4. [配置驅動計算](#配置驅動計算)
5. [性能優化](#性能優化)
6. [錯誤處理](#錯誤處理)

---

## 快速開始

### 最簡單的使用

```python
from momentum.Indicators import IndicatorEngine, EMAIndicator, DataSourceEnum

# 1. 註冊指標
IndicatorEngine.register("ema", EMAIndicator)

# 2. 創建引擎
engine = IndicatorEngine()

# 3. 計算指標
ema = engine.calculate_indicator(
    indicator_name="ema",
    data_source=DataSourceEnum.CLOSE,
    symbol="ETHUSDT",
    timeframe="1h",
    period=20
)

# 4. 使用結果
print(f"Latest EMA: {ema.iloc[-1]}")
print(f"Valid values: {ema.notna().sum()}")
```

### 使用裝飾器註冊（推薦）

```python
from momentum.Indicators import register_indicator, BaseIndicator

@register_indicator("ema")  # 自動註冊到引擎
class EMAIndicator(BaseIndicator):
    # ... 指標實作
    pass

# 無需手動註冊，直接使用
engine = IndicatorEngine()
result = engine.calculate_indicator("ema", ...)
```

---

## 核心 API

### 1. IndicatorEngine 初始化

```python
from momentum.Indicators import IndicatorEngine, DataSourceManager

# 方式 1: 使用默認配置
engine = IndicatorEngine()

# 方式 2: 自定義數據管理器
from momentum.DataExtraction import KlineStorageManager

storage = KlineStorageManager()
data_manager = DataSourceManager(storage)
engine = IndicatorEngine(data_manager)
```

### 2. 指標註冊

#### 方式 A: 裝飾器註冊（推薦）

```python
from momentum.Indicators import register_indicator, BaseIndicator

@register_indicator("my_indicator")
class MyIndicator(BaseIndicator):
    # ... 實作
    pass
```

#### 方式 B: 手動註冊

```python
from momentum.Indicators import IndicatorEngine
from momentum.Indicators.ema_indicator import EMAIndicator

IndicatorEngine.register("ema", EMAIndicator)
```

#### 查看已註冊指標

```python
# 列出所有指標
indicators = IndicatorEngine.list_indicators()
print(f"Available indicators: {indicators}")

# 獲取指標信息
info = IndicatorEngine.get_indicator_info("ema")
print(f"Default params: {info['default_params']}")
print(f"Class: {info['class_name']}")
```

### 3. 單指標計算

```python
# 基本用法
result = engine.calculate_indicator(
    indicator_name="ema",           # 指標名稱
    data_source=DataSourceEnum.CLOSE,  # 數據源
    symbol="ETHUSDT",                # 交易對
    timeframe="1h",                  # 時間框架
    period=20                        # 指標參數
)

# 結果是 pandas Series
print(type(result))  # <class 'pandas.core.series.Series'>
print(len(result))   # 數據長度
```

#### 支援的數據源

```python
from momentum.Indicators import DataSourceEnum

# 8 種數據源
DataSourceEnum.CLOSE           # 收盤價
DataSourceEnum.OPEN            # 開盤價
DataSourceEnum.HIGH            # 最高價
DataSourceEnum.LOW             # 最低價
DataSourceEnum.VOLUME          # 成交量
DataSourceEnum.TAKER_VOLUME    # 主動買入量
DataSourceEnum.TAKER_RATIO     # 主動買入比例
DataSourceEnum.QUOTE_VOLUME    # 報價成交量
```

### 4. 批量計算

```python
# 定義配置列表
configs = [
    {
        "indicator": "ema",
        "data_source": "close",
        "params": {"period": 20},
        "output_name": "ema_20"  # 可選：自定義列名
    },
    {
        "indicator": "ema",
        "data_source": "close",
        "params": {"period": 50},
        "output_name": "ema_50"
    },
    {
        "indicator": "ema",
        "data_source": "volume",
        "params": {"period": 20},
        "output_name": "ema_volume_20"
    }
]

# 批量計算
results = engine.calculate_indicators(
    symbol="ETHUSDT",
    timeframe="1h",
    configs=configs
)

# 結果是 DataFrame
print(type(results))  # <class 'pandas.core.frame.DataFrame'>
print(results.columns)  # ['ema_20', 'ema_50', 'ema_volume_20']
print(results.head())
```

---

## 常見場景

### 場景 1: 計算多週期 EMA

```python
from momentum.Indicators import IndicatorEngine, EMAIndicator, DataSourceEnum

# 註冊 EMA
IndicatorEngine.register("ema", EMAIndicator)
engine = IndicatorEngine()

# 計算 20/50/100 週期 EMA
periods = [20, 50, 100]
emas = {}

for period in periods:
    ema = engine.calculate_indicator(
        "ema",
        DataSourceEnum.CLOSE,
        "ETHUSDT",
        "1h",
        period=period
    )
    emas[f"ema_{period}"] = ema

# 合併為 DataFrame
import pandas as pd
df_emas = pd.DataFrame(emas)
print(df_emas.tail())
```

### 場景 2: EMA 在不同數據源上的表現

```python
# 數據源列表
sources = [
    DataSourceEnum.CLOSE,
    DataSourceEnum.VOLUME,
    DataSourceEnum.TAKER_RATIO
]

# 計算每個數據源的 EMA
results = {}
for source in sources:
    ema = engine.calculate_indicator(
        "ema",
        source,
        "ETHUSDT",
        "1h",
        period=20
    )
    results[f"ema_{source.value}"] = ema

df_results = pd.DataFrame(results)
```

### 場景 3: 使用配置文件批量計算

```python
from momentum.Indicators import ConfigLoader

# 載入配置
loader = ConfigLoader()
loader.load_config()

# 使用預設配置
preset_configs = loader.get_calculation_preset("ema_multi_period")

# 批量計算
results = engine.calculate_indicators(
    "ETHUSDT",
    "1h",
    preset_configs
)

print(results.columns)  # ['ema_20', 'ema_50', 'ema_100']
```

### 場景 4: 與案例數據結合（用於 Phase 3.2）

```python
from momentum.DataExtraction import KlineStorageManager

# 讀取案例 K 線數據
storage = KlineStorageManager()
df_klines = storage.read_klines("ETHUSDT", "1h")

# 計算指標
ema_20 = engine.calculate_indicator(
    "ema",
    DataSourceEnum.CLOSE,
    "ETHUSDT",
    "1h",
    period=20
)

# 合併到 K 線數據
df_klines['ema_20'] = ema_20

# 用於信號密度分析
print(df_klines[['timestamp', 'close', 'ema_20']].tail())
```

### 場景 5: 批量計算所有交易對

```python
symbols = ["ETHUSDT", "BTCUSDT", "BNBUSDT"]
timeframe = "1h"

all_results = {}

for symbol in symbols:
    try:
        ema = engine.calculate_indicator(
            "ema",
            DataSourceEnum.CLOSE,
            symbol,
            timeframe,
            period=20
        )
        all_results[symbol] = ema
        print(f"✅ {symbol}: {ema.notna().sum()} valid values")
    except Exception as e:
        print(f"❌ {symbol}: {e}")

# 合併結果
df_all = pd.DataFrame(all_results)
```

---

## 配置驅動計算

### 使用 YAML 配置

#### 1. 定義配置文件

編輯 `config/indicators.yaml`：

```yaml
calculation_presets:
  my_strategy:
    description: "我的策略指標集"
    configs:
      - indicator: ema
        data_source: close
        params:
          period: 20
        output_name: ema_fast

      - indicator: ema
        data_source: close
        params:
          period: 50
        output_name: ema_slow

      - indicator: ema
        data_source: volume
        params:
          period: 20
        output_name: volume_trend
```

#### 2. 載入並使用

```python
from momentum.Indicators import ConfigLoader, IndicatorEngine

# 載入配置
loader = ConfigLoader()
loader.load_config()

# 獲取預設配置
configs = loader.get_calculation_preset("my_strategy")

# 批量計算
engine = IndicatorEngine()
results = engine.calculate_indicators("ETHUSDT", "1h", configs)

print(results.columns)  # ['ema_fast', 'ema_slow', 'volume_trend']
```

### 動態配置

```python
# 根據條件動態生成配置
def generate_configs(periods: list) -> list:
    configs = []
    for period in periods:
        configs.append({
            "indicator": "ema",
            "data_source": "close",
            "params": {"period": period},
            "output_name": f"ema_{period}"
        })
    return configs

# 使用
configs = generate_configs([10, 20, 30, 50, 100])
results = engine.calculate_indicators("ETHUSDT", "1h", configs)
```

---

## 性能優化

### 1. 使用緩存

```python
from momentum.Indicators import DataSourceManager

# 啟用緩存（默認已啟用）
data_manager = DataSourceManager()

# 多次計算同一交易對時會自動使用緩存
engine = IndicatorEngine(data_manager)

# 第一次：從 HDF5 讀取
ema1 = engine.calculate_indicator("ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=20)

# 第二次：使用緩存（更快）
ema2 = engine.calculate_indicator("ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=50)
```

### 2. 批量計算（推薦）

```python
# ❌ 不推薦：逐個計算
results = {}
for period in [20, 50, 100]:
    results[f"ema_{period}"] = engine.calculate_indicator(
        "ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=period
    )

# ✅ 推薦：批量計算
configs = [
    {"indicator": "ema", "data_source": "close", "params": {"period": p}}
    for p in [20, 50, 100]
]
results = engine.calculate_indicators("ETHUSDT", "1h", configs)
```

### 3. 查看性能統計

```python
# 獲取引擎統計信息
stats = engine.get_stats()
print(f"Registered indicators: {stats['registered_indicators']}")
print(f"Cache size: {stats['cache_size']}")
print(f"Indicators: {stats['indicator_names']}")
```

---

## 錯誤處理

### 1. 捕獲計算錯誤

```python
from momentum.Indicators import IndicatorEngine, DataSourceEnum

engine = IndicatorEngine()

try:
    result = engine.calculate_indicator(
        "ema",
        DataSourceEnum.CLOSE,
        "INVALID_SYMBOL",  # 不存在的交易對
        "1h",
        period=20
    )
except ValueError as e:
    print(f"計算失敗: {e}")
except FileNotFoundError as e:
    print(f"數據文件不存在: {e}")
```

### 2. 批量計算的降級策略

```python
# 批量計算時，單個指標失敗不影響其他指標
configs = [
    {"indicator": "ema", "data_source": "close", "params": {"period": 20}},
    {"indicator": "invalid", "data_source": "close", "params": {}},  # 會失敗
    {"indicator": "ema", "data_source": "volume", "params": {"period": 10}},
]

results = engine.calculate_indicators("ETHUSDT", "1h", configs)

# 只返回成功計算的指標
print(results.columns)  # 只有 'ema_close_period20' 和 'ema_volume_period10'
```

### 3. 參數驗證

```python
# 無效參數會拋出 ValueError
try:
    result = engine.calculate_indicator(
        "ema",
        DataSourceEnum.CLOSE,
        "ETHUSDT",
        "1h",
        period=1  # 無效：period < 2
    )
except ValueError as e:
    print(f"參數錯誤: {e}")
```

---

## 進階用法

### 1. 直接使用指標類

```python
from momentum.Indicators import EMAIndicator, DataSourceManager, DataSourceEnum

# 創建指標實例
indicator = EMAIndicator()

# 獲取數據
data_manager = DataSourceManager()
close_prices = data_manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)

# 直接計算
ema = indicator.calculate(close_prices, period=20)

# 或使用安全計算（含錯誤處理）
result = indicator.safe_calculate(close_prices, period=20)
if result is not None:
    print(f"Calculation time: {result['metadata']['calc_time_ms']}ms")
    print(f"Valid from: {result['valid_from']}")
    ema_series = result['data']
```

### 2. 自定義數據源

```python
import pandas as pd
from momentum.Indicators import EMAIndicator

# 使用自己的數據
my_data = pd.Series([100, 102, 101, 105, 103, 107, 110])

indicator = EMAIndicator()
ema = indicator.calculate(my_data, period=3)

print(ema)
```

### 3. 獲取指標元信息

```python
# 從配置載入器獲取
from momentum.Indicators import ConfigLoader

loader = ConfigLoader()
loader.load_config()

# 獲取 EMA 信息
info = loader.get_indicator_info("ema")
print(f"Class: {info['class_name']}")
print(f"Module: {info['module']}")
print(f"Default params: {info['default_params']}")
print(f"Param ranges: {info['param_ranges']}")

# 用於 Optuna 優化（Phase 3.5）
param_range = info['param_ranges']['period']
print(f"Period range: {param_range['min']} - {param_range['max']}")
```

---

## 與 Phase 3.2 任務的銜接

Phase 3.2 需要使用指標引擎進行信號密度分析。範例：

```python
from momentum.Indicators import IndicatorEngine, ConfigLoader, DataSourceEnum

# 1. 載入配置
loader = ConfigLoader()
loader.load_config()

# 2. 獲取完整指標集
configs = loader.get_calculation_preset("full_indicator_set")

# 3. 批量計算所有指標
engine = IndicatorEngine()
indicators_df = engine.calculate_indicators("ETHUSDT", "1h", configs)

# 4. 進行信號密度分析
# indicators_df 包含所有計算好的指標，可以直接用於後續分析
print(f"Calculated {len(indicators_df.columns)} indicators")
print(f"Data length: {len(indicators_df)} rows")
```

---

## API 參考

### IndicatorEngine

| 方法 | 描述 |
|------|------|
| `register(name, class)` | 註冊指標（類方法） |
| `unregister(name)` | 取消註冊 |
| `list_indicators()` | 列出所有已註冊指標 |
| `get_indicator_info(name)` | 獲取指標元信息 |
| `calculate_indicator(...)` | 計算單個指標 |
| `calculate_indicators(...)` | 批量計算指標 |
| `get_stats()` | 獲取引擎統計信息 |

### ConfigLoader

| 方法 | 描述 |
|------|------|
| `load_config(force_reload)` | 載入配置文件 |
| `get_indicator_info(name)` | 獲取指標信息 |
| `get_default_params(name)` | 獲取默認參數 |
| `get_param_ranges(name)` | 獲取參數範圍 |
| `list_indicators()` | 列出所有指標 |
| `get_calculation_preset(name)` | 獲取預設配置 |
| `list_calculation_presets()` | 列出所有預設 |
| `get_global_config()` | 獲取全局配置 |
| `get_version()` | 獲取配置版本 |

---

## 更多資源

- [指標擴展指南](./indicator_extension_guide.md) - 如何添加新指標
- [EMA 指標源碼](../momentum/Indicators/ema_indicator.py) - 完整實作範例
- [配置文件說明](../config/indicators.yaml) - 配置格式詳解

**有問題？** 查看代碼中的 docstring 或提交 Issue。
