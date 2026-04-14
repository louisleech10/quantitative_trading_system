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

# ==================== 用於 Optuna 優化（2026-01 更新）====================
# 推薦方式：使用 strategy_registry 獲取策略元數據
from momentum.Analysis.strategy_registry import strategy_registry

# 獲取策略元數據
metadata = strategy_registry.get_strategy("three_line")

# 查看所有參數定義
for param_def in metadata.parameters:
    print(f"{param_def.display_name} ({param_def.name}):")
    print(f"  範圍: {param_def.min_value} - {param_def.max_value}")
    print(f"  默認值: {param_def.default_value}")
    print(f"  步長: {param_def.step}")

# Optuna 會自動使用這些參數範圍進行優化

# ==================== 快取加速系統（2026-01-08 更新）====================
# 新增 strategy_cache_registry 用於 Optuna 快取加速
from momentum.Analysis.strategy_cache_registry import strategy_cache_registry

# 列出支援快取加速的策略
print(strategy_cache_registry.list_strategies())
# ['three_line', 'short_long_cross', 'mid_long_cross']

# 檢查策略是否支援快取
if strategy_cache_registry.has_strategy("three_line"):
    print("three_line 策略支援快取加速 (15x 效能提升)")

# 在 strategies.yaml 中，使用 is_cacheable: true 標記週期參數
# 系統會自動預計算這些參數的所有可能值，加速 Optuna 優化
```

---

## 與信號密度分析整合（2026-01 更新）

指標引擎可與 **SignalDensityAnalyzer** 結合使用，實現 Golden Formula v2.0 評分系統。

### 完整工作流程

```python
from momentum.Indicators import IndicatorEngine, DataSourceEnum
from momentum.Analysis import SignalDensityAnalyzer
from momentum.DataExtraction import KlineStorageManager
from api.models.strategy_config import StrategyConfig
from api.models.training_window_config import TrainingWindowConfig

# ==================== 1. 準備數據 ====================
# 載入 K 線數據
kline_storage = KlineStorageManager()

# 載入案例數據（正例和反例）
positive_cases = [...]  # 正例 Case 對象列表
negative_cases = [...]  # 反例 Case 對象列表

# ==================== 2. 配置策略 ====================
strategy_config = StrategyConfig(
    data_source="volume",
    strategy_logic="three_line",
    indicator_type="ema",
    params={
        "short_period": 5,
        "mid_period": 15,
        "long_period": 33
    }
)

# ==================== 3. 配置訓練窗口 ====================
window_config = TrainingWindowConfig(
    lookback_bars=100,          # 近期窗口（Near）
    far_lookback_bars=200,      # 遠期窗口（Far，可選）
    reference_point="peak",     # 參考點：peak/bottom/center
    mode="dual_density"         # 雙密度模式
)

# ==================== 4. 創建分析器 ====================
# 指標引擎會自動被 SignalDensityAnalyzer 使用
indicator_engine = IndicatorEngine()

analyzer = SignalDensityAnalyzer(
    kline_storage=kline_storage,
    indicator_engine=indicator_engine
)

# ==================== 5. 執行信號密度分析 ====================
result = analyzer.analyze_signal_density(
    positive_cases=positive_cases,
    negative_cases=negative_cases,
    strategy_config=strategy_config,
    window_config=window_config
)

# ==================== 6. 查看分析結果 ====================
print("信號密度分析結果:")
print(f"  正例加權平均 M 值: {result.positive_weighted_mean_m:.4f}")
print(f"  反例加權平均 M 值: {result.negative_weighted_mean_m:.4f}")
print(f"  M 分離度: {result.m_separation:.4f}")
print(f"  Golden Formula 得分: {result.optuna_golden_score:.4f}")
print(f"\n統計檢驗:")
print(f"  p-value: {result.p_value:.4f}")
print(f"  Cohen's d: {result.cohens_d:.4f}")
print(f"  穩定性 CV: {result.stability_cv:.4f}")
```

### Golden Formula v2.0 解讀

**目標函數**：
```
Score = (μ_pos - μ_neg) - λ × (σ_pos + 0.5 × σ_neg)
```

**M 值計算**（每個案例）：
```
M = (Near - Far) / (Near + Far)
```
- **Near**: 近期信號密度（lookback_bars 範圍內）
- **Far**: 遠期信號密度（far_lookback_bars 範圍內）
- **M 值範圍**: [-1, 1]
  - M > 0: 近期密度高於遠期（理想狀態）
  - M < 0: 遠期密度高於近期（不理想）
  - M ≈ 1: 幾乎所有信號都在近期
  - M ≈ -1: 幾乎所有信號都在遠期

**加權平均**：
```
μ_pos = Σ(w_i × M_i) / Σw_i
```
- 權重 w_i = Near_i（信號越多權重越大）
- 確保有足夠信號的案例有更大影響力

**優化目標**：
- ✅ 最大化 μ_pos（正例近期信號密集）
- ✅ 最小化 μ_neg（反例近期信號稀疏）
- ✅ 最小化 σ_pos（正例表現穩定）

### 與 Optuna 優化整合

```python
from momentum.Optimization import OptunaOptimizer

# 創建優化器（會自動使用 SignalDensityAnalyzer）
optimizer = OptunaOptimizer(
    study_name="ema_optimization",
    positive_cases=positive_cases,
    negative_cases=negative_cases,
    training_window=window_config,
    n_trials=100,
    n_jobs=4  # 多核並行
)

# 執行優化（自動計算 Golden Formula 得分）
result = await optimizer.optimize()

print(f"最佳參數: {result.best_params}")
print(f"最佳得分: {result.best_value:.4f}")
```

### 實用技巧

#### 1. 調試信號生成

```python
# 獲取單個案例的信號密度
case = positive_cases[0]

# 提取訓練窗口
klines = analyzer.extract_training_window(case, window_config)

# 計算指標
engine = IndicatorEngine()
ema = engine.calculate_indicator(
    "ema",
    DataSourceEnum.VOLUME,
    case.symbol,
    "1h",  # 使用固定 timeframe
    period=15
)

# 生成信號
from momentum.Analysis.strategies.three_line_strategy import check_three_line_signal
signals = check_three_line_signal(klines, strategy_config)

print(f"總 K 線數: {len(klines)}")
print(f"信號數: {signals.sum()}")
print(f"信號密度: {signals.sum() / len(klines):.4f}")
```

#### 2. 批量分析不同參數

```python
# 測試多組參數
param_sets = [
    {"short_period": 5, "mid_period": 15, "long_period": 30},
    {"short_period": 8, "mid_period": 20, "long_period": 50},
    {"short_period": 13, "mid_period": 25, "long_period": 100},
]

results = []
for params in param_sets:
    strategy_config.params = params
    result = analyzer.analyze_signal_density(
        positive_cases, negative_cases,
        strategy_config, window_config
    )
    results.append({
        "params": params,
        "score": result.optuna_golden_score,
        "m_separation": result.m_separation
    })

# 排序找最佳
best = sorted(results, key=lambda x: x['score'], reverse=True)[0]
print(f"最佳參數: {best['params']}")
print(f"最佳得分: {best['score']:.4f}")
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

**指標開發**：
- [指標擴展指南](./indicator_extension_guide.md) - 如何添加新指標（含 Optuna 整合）
- [EMA 指標源碼](../momentum/Indicators/ema_indicator.py) - 完整實作範例
- [配置文件說明](../config/indicators.yaml) - 配置格式詳解

**策略系統**：
- [策略註冊表文檔](../momentum/Analysis/strategy_registry.py) - StrategyMetadata 使用說明
- [Three Line 策略](../momentum/Analysis/strategies/three_line_strategy.py) - 完整策略範例

**優化系統（2026-01 更新）**：
- [Optuna 優化器文檔](../momentum/Optimization/README.md) - Golden Formula v2.0
- [SignalDensityAnalyzer](../momentum/Analysis/signal_density_analyzer.py) - 信號密度分析核心
- [多核並行優化指南](../docs/optimization_guide.md) - n_jobs 配置與性能調優

**有問題？** 查看代碼中的 docstring 或提交 Issue。
