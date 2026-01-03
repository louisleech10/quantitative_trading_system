# 指標擴展指南 - 如何添加新指標

> **目標讀者**: 需要添加新技術指標的開發者
> **前置知識**: Python、pandas 基礎、技術分析概念
> **預計時間**: 30-60 分鐘（含測試）

本指南將帶你一步步實作一個新的技術指標，並整合到指標計算引擎中。

---

## 📋 目錄

1. [快速開始](#快速開始)
2. [指標實作步驟](#指標實作步驟)
3. [完整範例：SMA 指標](#完整範例sma-指標)
4. [測試與驗證](#測試與驗證)
5. [最佳實踐](#最佳實踐)
6. [常見問題](#常見問題)

---

## 快速開始

添加新指標只需 **5 個步驟**：

```
1. 創建指標類（繼承 BaseIndicator）
2. 實作 calculate() 方法
3. 實作 validate_params() 方法
4. 註冊到引擎
5. 更新 YAML 配置
```

**最快範例**（假設已有計算邏輯）：
```python
from momentum.Indicators import BaseIndicator, register_indicator
import pandas as pd

@register_indicator("my_indicator")
class MyIndicator(BaseIndicator):
    def calculate(self, data: pd.Series, period: int = 20, **kwargs) -> pd.Series:
        # 你的計算邏輯
        return data.rolling(window=period).mean()

    def validate_params(self, period: int = 20, **kwargs) -> bool:
        if not isinstance(period, int) or period < 2:
            raise ValueError(f"Invalid period: {period}")
        return True
```

完成！你的指標已經可以使用了。

---

## 指標實作步驟

### 步驟 1: 創建指標類文件

在 [momentum/Indicators/](../momentum/Indicators/) 目錄下創建新文件，命名規則：`<indicator_name>_indicator.py`

**範例**：創建 `sma_indicator.py`（Simple Moving Average）

```python
# momentum/Indicators/sma_indicator.py
"""
SMA (簡單移動平均線) 指標

公式：SMA = sum(price[i-n+1:i+1]) / n
說明：計算過去 n 期的算術平均值
"""

from typing import Any, Dict
import pandas as pd
import logging

from .base_indicator import BaseIndicator

logger = logging.getLogger(__name__)
```

### 步驟 2: 定義指標類

繼承 `BaseIndicator` 並實作必要方法：

```python
class SMAIndicator(BaseIndicator):
    """
    SMA (簡單移動平均線) 指標

    計算過去 N 期數據的算術平均值。

    參數：
        period (int): 計算週期，默認 20

    Example:
        >>> indicator = SMAIndicator()
        >>> sma = indicator.calculate(close_prices, period=20)
    """

    @classmethod
    def get_indicator_name(cls) -> str:
        """返回指標名稱（用於註冊和識別）"""
        return "sma"

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """返回默認參數"""
        return {"period": 20}
```

### 步驟 3: 實作 calculate() 方法

這是核心計算邏輯：

```python
    def calculate(self, data: pd.Series, period: int = 20, **kwargs) -> pd.Series:
        """
        計算 SMA

        Args:
            data: 輸入數據（pandas Series）
            period: 計算週期
            **kwargs: 其他參數（向前兼容）

        Returns:
            pd.Series: SMA 結果（前 N-1 個值為 NaN）

        Raises:
            ValueError: 參數驗證失敗
        """
        # 1. 驗證參數
        if not self.validate_params(period=period):
            raise ValueError(f"Invalid parameters: period={period}")

        # 2. 邊界情況處理
        if len(data) < period:
            logger.warning(
                f"Data length ({len(data)}) < period ({period}), "
                f"all values will be NaN"
            )
            return pd.Series([float('nan')] * len(data), index=data.index)

        # 3. 計算 SMA
        result = data.rolling(window=period).mean()

        logger.debug(
            f"SMA calculated: period={period}, "
            f"valid_values={result.notna().sum()}/{len(result)}"
        )

        return result
```

**關鍵要點**：
- ✅ **參數驗證**：確保調用 `validate_params()`
- ✅ **邊界處理**：數據長度不足時返回 NaN，而非報錯
- ✅ **保持索引**：返回的 Series 必須保持原始索引
- ✅ **日誌記錄**：記錄關鍵信息方便調試

### 步驟 4: 實作 validate_params() 方法

參數驗證邏輯：

```python
    def validate_params(self, period: int = 20, **kwargs) -> bool:
        """
        驗證參數有效性

        Args:
            period: 週期參數
            **kwargs: 其他參數

        Returns:
            bool: 參數是否有效

        Raises:
            ValueError: 參數無效時拋出異常
        """
        # 類型檢查
        if not isinstance(period, int):
            raise ValueError(
                f"period must be int, got {type(period).__name__}"
            )

        # 範圍檢查
        if period < 2:
            raise ValueError(
                f"period must be >= 2 (got {period})"
            )

        if period > 500:
            raise ValueError(
                f"period must be <= 500 (got {period}), "
                f"larger values may not be meaningful"
            )

        return True
```

**驗證原則**：
- ✅ **明確的錯誤信息**：告訴用戶什麼錯了
- ✅ **合理的範圍**：根據指標特性設定上下限
- ✅ **類型安全**：檢查參數類型

### 步驟 5: 註冊指標到引擎

有兩種註冊方式：

**方式 1: 裝飾器（推薦）**
```python
from momentum.Indicators import register_indicator

@register_indicator("sma")
class SMAIndicator(BaseIndicator):
    # ... 類定義
```

**方式 2: 手動註冊**
```python
from momentum.Indicators import IndicatorEngine
from momentum.Indicators.sma_indicator import SMAIndicator

# 在初始化代碼中註冊
IndicatorEngine.register("sma", SMAIndicator)
```

### 步驟 6: 更新 YAML 配置（傳統方式，向後兼容）

> **注意**：此方式仍然有效，但推薦使用「步驟 7」的 StrategyMetadata 方式，更適合 Optuna 優化系統。

編輯 [config/indicators.yaml](../config/indicators.yaml)，添加新指標配置：

```yaml
indicators:
  sma:
    # 基本信息
    class_name: SMAIndicator
    module: momentum.Indicators.sma_indicator
    description: "簡單移動平均線 (Simple Moving Average) - 所有數據點權重相同"
    category: trend

    # 默認參數
    default_params:
      period: 20

    # 參數範圍 (用於 Optuna 優化)
    param_ranges:
      period:
        type: int
        min: 2
        max: 200
        step: 1
        description: "SMA 週期"

    # 支援的數據源
    supported_data_sources:
      - close
      - open
      - high
      - low
      - volume

    # 計算要求
    requirements:
      min_periods: "period"
      data_constraints:
        - "no_nan"

    # 性能配置
    performance:
      cache_result: true
      estimated_time_ms: 3
```

### 步驟 7: 整合到策略系統（推薦方式）⭐

**為什麼推薦這種方式？**
- ✅ 自動整合到 Optuna 優化系統
- ✅ 動態參數採樣，無需硬編碼
- ✅ 類型安全，編譯時檢查
- ✅ 更好的文檔化和可維護性

#### 定義策略元數據

```python
# momentum/Analysis/strategies/sma_strategy.py
"""
SMA 策略定義

基於簡單移動平均線的趨勢跟蹤策略
"""

from momentum.Analysis.strategy_registry import (
    strategy_registry,
    StrategyMetadata,
    ParameterDefinition,
    ParameterType
)

# 定義策略元數據
sma_strategy = StrategyMetadata(
    name="sma_trend",
    display_name="SMA 趨勢策略",
    description="使用單一 SMA 作為趨勢判斷指標",
    category="trend",

    # 參數定義（Optuna 會自動識別這些範圍）
    parameters=[
        ParameterDefinition(
            name="period",
            display_name="SMA 週期",
            type=ParameterType.INT,
            min_value=5,
            max_value=200,
            default_value=20,
            step=1,
            description="計算 SMA 的回看週期"
        )
    ],

    # 需要的指標
    required_indicators=["sma"],

    # 支援的數據源
    supported_data_sources=["close", "open", "high", "low"],

    # 實作函數（可選，用於信號生成）
    implementation_module="momentum.Analysis.strategies.sma_strategy",
    implementation_function="generate_sma_signals"
)

# 註冊到全局策略註冊表
strategy_registry.register(sma_strategy)


def generate_sma_signals(klines_df, strategy_config):
    """
    生成 SMA 策略信號

    Args:
        klines_df: K 線數據（包含價格、成交量等）
        strategy_config: 策略配置（包含 period 參數）

    Returns:
        信號序列（1=多頭, -1=空頭, 0=無信號）
    """
    from momentum.Indicators import IndicatorEngine, DataSourceEnum

    # 計算 SMA
    engine = IndicatorEngine()
    sma = engine.calculate_indicator(
        "sma",
        DataSourceEnum(strategy_config.data_source),
        klines_df['symbol'].iloc[0],
        klines_df['timeframe'].iloc[0],
        period=strategy_config.params['period']
    )

    # 生成信號：價格 > SMA 為多頭
    signals = (klines_df['close'] > sma).astype(int)
    signals[signals == 0] = -1  # 空頭

    return signals
```

#### 在 Optuna 優化中使用

```python
from momentum.Optimization import OptunaOptimizer
from momentum.Analysis.strategy_registry import strategy_registry

# 1. 獲取策略元數據
metadata = strategy_registry.get_strategy("sma_trend")
print(f"Strategy: {metadata.display_name}")
print(f"Parameters: {[p.name for p in metadata.parameters]}")

# 2. Optuna 會自動使用 ParameterDefinition 進行採樣
optimizer = OptunaOptimizer(
    study_name="sma_optimization",
    positive_cases=positive_cases,
    negative_cases=negative_cases,
    training_window=window_config,
    n_trials=50,
    n_jobs=4  # 多核並行
)

# 3. 運行優化（參數範圍自動從 metadata 讀取）
result = await optimizer.optimize()

# 4. 獲取最佳參數
print(f"Best period: {result.best_params['period']}")
```

#### YAML 配置 vs StrategyMetadata 對比

| 特性 | YAML 配置 | StrategyMetadata（推薦）|
|------|-----------|------------------------|
| **類型安全** | ❌ 執行時檢查 | ✅ 編譯時檢查 |
| **Optuna 整合** | ⚠️ 需手動解析 | ✅ 自動整合 |
| **動態擴展** | ❌ 需修改文件 | ✅ 代碼即配置 |
| **文檔化** | ⚠️ 需同步維護 | ✅ Docstring 即文檔 |
| **版本控制** | ✅ 易於追蹤 | ✅ 與代碼一起管理 |
| **適用場景** | 簡單指標配置 | 複雜策略系統 |

**建議**：
- 新策略使用 StrategyMetadata
- 舊配置保留 YAML（向後兼容）
- 兩種方式可以共存

---

## 完整範例：SMA 指標

這是一個完整的 SMA 指標實作，可以直接複製使用：

```python
# momentum/Indicators/sma_indicator.py
"""
SMA (簡單移動平均線) 指標

公式：SMA[t] = (price[t] + price[t-1] + ... + price[t-n+1]) / n
特點：所有數據點權重相同，是最基礎的移動平均線
用途：識別趨勢方向、支撐壓力位、交叉信號
"""

from typing import Any, Dict
import pandas as pd
import logging

from .base_indicator import BaseIndicator
from .indicator_engine import register_indicator

logger = logging.getLogger(__name__)


@register_indicator("sma")
class SMAIndicator(BaseIndicator):
    """
    SMA (簡單移動平均線) 指標

    Example:
        >>> from momentum.Indicators import SMAIndicator
        >>> indicator = SMAIndicator()
        >>> sma = indicator.calculate(close_prices, period=20)
        >>> print(f"Latest SMA: {sma.iloc[-1]}")
    """

    @classmethod
    def get_indicator_name(cls) -> str:
        return "sma"

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {"period": 20}

    def calculate(self, data: pd.Series, period: int = 20, **kwargs) -> pd.Series:
        """
        計算 SMA

        Args:
            data: 價格序列
            period: 計算週期（默認 20）

        Returns:
            pd.Series: SMA 序列
        """
        # 驗證參數
        if not self.validate_params(period=period):
            raise ValueError(f"Invalid period: {period}")

        # 邊界情況
        if len(data) < period:
            logger.warning(
                f"Data length ({len(data)}) < period ({period})"
            )
            return pd.Series([float('nan')] * len(data), index=data.index)

        # 計算 SMA
        result = data.rolling(window=period).mean()

        logger.debug(
            f"SMA calculated: period={period}, "
            f"data_length={len(data)}, "
            f"valid_count={result.notna().sum()}"
        )

        return result

    def validate_params(self, period: int = 20, **kwargs) -> bool:
        """驗證參數"""
        if not isinstance(period, int):
            raise ValueError(f"period must be int, got {type(period).__name__}")

        if period < 2:
            raise ValueError(f"period must be >= 2 (got {period})")

        if period > 500:
            raise ValueError(f"period too large: {period}")

        return True
```

---

## 測試與驗證

### 1. 單元測試

創建測試文件 `tests/indicators/test_sma_indicator.py`：

```python
import pytest
import pandas as pd
import numpy as np
from momentum.Indicators import SMAIndicator

def test_sma_basic():
    """測試基本 SMA 計算"""
    indicator = SMAIndicator()

    # 簡單測試數據
    data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    result = indicator.calculate(data, period=3)

    # 驗證結果
    assert len(result) == 10
    assert pd.isna(result.iloc[0])  # 前兩個為 NaN
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == 2.0    # (1+2+3)/3 = 2
    assert result.iloc[3] == 3.0    # (2+3+4)/3 = 3

def test_sma_validation():
    """測試參數驗證"""
    indicator = SMAIndicator()
    data = pd.Series([1, 2, 3])

    # 無效參數應該拋出異常
    with pytest.raises(ValueError):
        indicator.calculate(data, period=1)  # 太小

    with pytest.raises(ValueError):
        indicator.calculate(data, period=1000)  # 太大
```

### 2. 對比驗證

與已知正確的實作對比（如 TA-Lib）：

```python
import talib

def test_sma_vs_talib():
    """與 TA-Lib 對比"""
    indicator = SMAIndicator()

    # 真實數據
    data = pd.Series([...])  # 從 HDF5 載入

    # 計算
    my_sma = indicator.calculate(data, period=20)
    talib_sma = talib.SMA(data.values, timeperiod=20)

    # 比較（忽略 NaN）
    diff = np.abs(my_sma.dropna() - talib_sma[~np.isnan(talib_sma)])
    assert diff.max() < 1e-6  # 誤差小於 1e-6
```

### 3. 端到端測試

```python
def test_sma_with_engine():
    """測試整合到引擎"""
    from momentum.Indicators import IndicatorEngine, DataSourceEnum

    engine = IndicatorEngine()

    # 計算真實案例的 SMA
    result = engine.calculate_indicator(
        "sma",
        DataSourceEnum.CLOSE,
        "ETHUSDT",
        "1h",
        period=20
    )

    assert isinstance(result, pd.Series)
    assert len(result) > 0
    assert result.notna().sum() > 0
```

---

## 最佳實踐

### ✅ DO（應該做的）

1. **完整的 docstring**
   ```python
   def calculate(self, data: pd.Series, **params) -> pd.Series:
       """
       計算指標

       Args:
           data: 輸入數據
           **params: 參數

       Returns:
           pd.Series: 計算結果

       Raises:
           ValueError: 參數無效
       """
   ```

2. **明確的參數驗證**
   ```python
   if not isinstance(period, int):
       raise ValueError(f"Expected int, got {type(period)}")
   ```

3. **邊界情況處理**
   ```python
   if len(data) < period:
       return pd.Series([float('nan')] * len(data), index=data.index)
   ```

4. **保持索引一致**
   ```python
   result = data.rolling(period).mean()  # ✅ 保持原索引
   return result
   ```

5. **日誌記錄**
   ```python
   logger.debug(f"Calculated {name}: {len(result)} values")
   ```

### ❌ DON'T（不應該做的）

1. ❌ **不要修改輸入數據**
   ```python
   # 錯誤
   data = data.fillna(0)  # 修改了原始數據

   # 正確
   clean_data = data.fillna(0)  # 創建副本
   ```

2. ❌ **不要假設數據完整**
   ```python
   # 錯誤
   return data.rolling(period).mean()  # 沒有檢查長度

   # 正確
   if len(data) < period:
       return pd.Series([nan] * len(data), index=data.index)
   ```

3. ❌ **不要硬編碼參數**
   ```python
   # 錯誤
   def calculate(self, data):
       return data.rolling(20).mean()  # 硬編碼 20

   # 正確
   def calculate(self, data, period=20):
       return data.rolling(period).mean()
   ```

4. ❌ **不要忽略異常**
   ```python
   # 錯誤
   try:
       result = complex_calculation()
   except:
       pass  # 忽略所有錯誤

   # 正確
   try:
       result = complex_calculation()
   except ValueError as e:
       logger.error(f"Calculation failed: {e}")
       raise
   ```

---

## 常見問題

### Q1: 指標需要多個數據源怎麼辦？

**A**: 在 `calculate()` 中添加額外參數，或使用 `**kwargs` 傳遞：

```python
def calculate(
    self,
    data: pd.Series,  # 主數據源
    volume: Optional[pd.Series] = None,  # 額外數據源
    **kwargs
) -> pd.Series:
    if volume is None:
        raise ValueError("Volume data is required for this indicator")

    # 使用兩個數據源計算
    result = some_calculation(data, volume)
    return result
```

### Q2: 指標計算很慢怎麼優化？

**A**: 幾個優化方向：
1. 使用 `pandas_ta` 或 `TA-Lib` 的 C 語言實現
2. 使用 `numba` JIT 編譯
3. 啟用緩存機制
4. 批量計算而非逐點計算

### Q3: 如何處理前 N 個值？

**A**: 返回 NaN，這是標準做法：

```python
# 前 period-1 個值為 NaN
result = data.rolling(period).mean()
```

用戶可以根據需要用 `dropna()` 移除。

### Q4: 指標結果需要歸一化怎麼辦？

**A**: 在 `calculate()` 中添加可選的歸一化邏輯：

```python
def calculate(
    self,
    data: pd.Series,
    period: int = 20,
    normalize: bool = False,
    **kwargs
) -> pd.Series:
    result = data.rolling(period).mean()

    if normalize:
        result = (result - result.min()) / (result.max() - result.min())

    return result
```

---

## 整合到 Optuna 優化系統 🚀

完成指標實作後，您可以將其整合到 Optuna 參數優化系統中，自動尋找最佳參數組合。

### 完整優化流程範例

```python
"""
完整的指標 → 策略 → Optuna 優化流程範例

此範例展示如何從零開始定義一個新指標並整合到 Optuna 優化系統中。
"""

# ==================== 1. 定義並註冊指標 ====================
from momentum.Indicators import BaseIndicator, register_indicator
import pandas as pd

@register_indicator("my_sma")
class MySMAIndicator(BaseIndicator):
    """簡單移動平均線指標"""

    def calculate(self, data: pd.Series, period: int = 20, **kwargs) -> pd.Series:
        return data.rolling(window=period).mean()

    def validate_params(self, period: int = 20, **kwargs) -> bool:
        if not isinstance(period, int) or period < 2:
            raise ValueError(f"Invalid period: {period}")
        return True


# ==================== 2. 定義策略元數據 ====================
from momentum.Analysis.strategy_registry import (
    strategy_registry,
    StrategyMetadata,
    ParameterDefinition,
    ParameterType
)

# 定義策略元數據（Optuna 會自動讀取參數範圍）
sma_strategy = StrategyMetadata(
    name="my_sma_strategy",
    display_name="我的 SMA 策略",
    description="基於雙 SMA 的趨勢跟蹤策略",
    category="trend",

    # 參數定義（Optuna 會自動使用這些範圍進行採樣）
    parameters=[
        ParameterDefinition(
            name="short_period",
            display_name="短週期",
            type=ParameterType.INT,
            min_value=5,
            max_value=50,
            default_value=20,
            step=1,
            description="短期 SMA 週期"
        ),
        ParameterDefinition(
            name="long_period",
            display_name="長週期",
            type=ParameterType.INT,
            min_value=20,
            max_value=200,
            default_value=50,
            step=1,
            description="長期 SMA 週期"
        )
    ],

    required_indicators=["my_sma"],
    supported_data_sources=["close", "volume"]
)

# 註冊策略到全局註冊表
strategy_registry.register(sma_strategy)


# ==================== 3. 運行 Optuna 優化 ====================
import asyncio
from momentum.Optimization import OptunaOptimizer, ParameterRanges
from api.models.training_window_config import TrainingWindowConfig

async def run_optimization():
    """執行 Optuna 參數優化"""

    # 定義案例數據（正例和反例）
    positive_cases = ["case1", "case2", "case3"]  # 替換為實際 case IDs
    negative_cases = ["case4", "case5", "case6"]

    # 定義訓練窗口
    window_config = TrainingWindowConfig(
        lookback_bars=100,
        reference_point="peak"
    )

    # 創建 Optuna 優化器
    optimizer = OptunaOptimizer(
        study_name="my_sma_optimization",
        positive_cases=positive_cases,
        negative_cases=negative_cases,
        training_window=window_config,

        # Optuna 配置
        sampler_type="TPE",  # Tree-structured Parzen Estimator
        n_trials=100,        # 運行 100 次試驗
        n_jobs=4,            # 使用 4 核並行（4.3x 加速）⚡
        random_seed=42,

        # 參數範圍（可選：覆蓋策略元數據中的範圍）
        parameter_ranges=ParameterRanges(
            data_sources=["close", "volume"],
            strategy_logics=["my_sma_strategy"],
            indicator_types=["my_sma"]
        )
    )

    # 執行優化
    result = await optimizer.optimize()

    # 輸出結果
    print(f"✅ 最佳參數: {result.best_params}")
    print(f"✅ 最佳得分 (Golden Formula): {result.best_value:.4f}")
    print(f"✅ 優化耗時: {result.optimization_time:.1f} 秒")

    # 獲取所有試驗結果
    trials_df = optimizer.get_trials_dataframe()
    print(f"\n📊 前 10 名結果:")
    print(trials_df.head(10))

    return result

# 執行優化
if __name__ == "__main__":
    result = asyncio.run(run_optimization())
```

### Golden Formula v2.0 得分計算

Optuna 優化使用 **Golden Formula v2.0** 作為目標函數：

```
Score = (μ_pos - μ_neg) - λ × (σ_pos + 0.5 × σ_neg)
```

**符號說明**：
- **μ_pos**: 正例加權平均 M 值（範圍 [-1, 1]）
- **μ_neg**: 反例加權平均 M 值（範圍 [-1, 1]）
- **σ_pos**: 正例 M 值標準差（穩定性指標）
- **σ_neg**: 反例 M 值標準差
- **λ**: 穩定性懲罰係數（默認 1.0）

**M 值定義**：
```
M = (Near - Far) / (Near + Far)
```
- **Near**: 近期信號密度（lookback_bars 範圍內）
- **Far**: 遠期信號密度（far_lookback_bars 範圍內）

**優化目標**：
- ✅ **最大化 μ_pos**：正例在近期有高信號密度
- ✅ **最小化 μ_neg**：反例在近期信號密度低
- ✅ **最小化 σ_pos**：正例表現穩定（不同月份一致）

### 多核並行優化（2026-01 更新）⚡

系統支援真正的多核並行加速：

```python
optimizer = OptunaOptimizer(
    # ... 其他參數 ...
    n_jobs=4,  # 使用 4 個 CPU 核心並行
)
```

**性能提升實測**：
```
1 核:  ~2.5 分鐘 (100 trials)
4 核:  ~58 秒    (4.3x 加速) ⚡
8 核:  ~35 秒    (預估)      ⚡
```

**配置建議**：
- 推薦設為 CPU 核心數的 **50-75%**
- 超過 8 核後收益遞減（I/O 瓶頸）
- 記憶體使用會線性增長（每核心獨立載入案例數據）

**前端配置**（NEW）：
```typescript
// 現在可以在前端直接配置並行核心數
const optunaConfig = {
  enabled: true,
  n_trials: 100,
  n_jobs: 4,  // ← 用戶可自行調整
}
```

### 參數去重機制（NEW）

系統會自動剪枝重複的參數組合，確保：

```
n_trials=50  →  50 組不同的參數（而非 50 次嘗試）
```

**工作原理**：
1. 每個 trial 採樣參數後，檢查是否已經測試過
2. 如果重複，剪枝並採樣新參數
3. 如果試驗不足，自動補充試驗直到達到目標數量

**範例**：
```python
# 用戶設定 50 trials
optimizer = OptunaOptimizer(n_trials=50, ...)

# 實際執行
- 初始運行: 40 個 COMPLETE + 10 個 PRUNED (重複)
- 自動補充: 額外運行 10 個 trials
- 最終結果: 50 個 COMPLETE trials（每個參數組合唯一）
```

### CSV 導出與統計欄位（NEW）

優化完成後，CSV 會包含 **20+ 個統計欄位**：

```csv
Rank,Trial #,Value,State,data_source,strategy_logic,indicator_type,
short_period,mid_period,long_period,
p_value,cohens_d,stability_cv,                    # 統計檢驗
positive_avg_density,negative_avg_density,        # 密度指標
separation,m_separation,                          # 分離度
positive_weighted_mean_m,negative_weighted_mean_m,# M 值
positive_m_std,negative_m_std,                    # M 值穩定性
positive_total_weight,negative_total_weight,      # 權重統計
positive_active_cases,negative_active_cases,      # 案例統計
...
```

### 最佳實踐

#### 1. 合理設定參數範圍

```python
# ✅ 推薦：基於領域知識設定範圍
ParameterDefinition(
    name="period",
    min_value=5,    # 太小會過擬合
    max_value=200,  # 太大會失去響應性
    step=1
)

# ❌ 避免：範圍過大導致搜索低效
ParameterDefinition(
    name="period",
    min_value=1,
    max_value=1000  # 範圍過大
)
```

#### 2. 選擇適當的試驗次數

```python
# 快速測試：20-50 trials
optimizer = OptunaOptimizer(n_trials=20, n_jobs=4)

# 正式優化：100-200 trials（推薦）
optimizer = OptunaOptimizer(n_trials=100, n_jobs=4)

# 精細調優：500+ trials
optimizer = OptunaOptimizer(n_trials=500, n_jobs=8)
```

#### 3. 啟用進度監控

```python
optimizer = OptunaOptimizer(
    # ... 其他參數 ...
    enable_progress_monitor=True,  # 顯示進度條
    checkpoint_interval=50,        # 每 50 trials 保存檢查點
    checkpoint_dir="data/checkpoints"
)
```

#### 4. 處理優化結果

```python
# 執行優化
result = await optimizer.optimize()

# 分析最佳參數
best_params = result.best_params
print(f"最佳短週期: {best_params['short_period']}")
print(f"最佳長週期: {best_params['long_period']}")

# 獲取收斂歷史
convergence = result.convergence_history
print(f"優化路徑: {convergence}")

# 導出完整結果
trials_df = optimizer.get_trials_dataframe()
trials_df.to_csv("optimization_results.csv")
```

---

## 下一步

完成指標實作後：

1. ✅ **運行測試**：確保所有測試通過
2. ✅ **定義策略元數據**：使用 StrategyMetadata（推薦）
3. ✅ **整合到 Optuna**：運行參數優化找到最佳配置
4. ✅ **編寫文檔**：在 docstring 中說明用法
5. ✅ **性能測試**：確保計算效率符合預期
6. ✅ **提交代碼**：創建 Pull Request

**參考資源**：
- [EMA 指標實作](../momentum/Indicators/ema_indicator.py) - 完整範例
- [Three Line 策略](../momentum/Analysis/strategies/three_line_strategy.py) - 策略元數據範例
- [BaseIndicator 文檔](../momentum/Indicators/base_indicator.py) - 基類說明
- [API 使用文檔](./indicator_api_usage.md) - 如何使用指標
- [Optuna 優化系統](../momentum/Optimization/README.md) - 深入了解優化系統

---

**有問題？** 查看 [常見問題](./faq.md) 或提交 Issue。
