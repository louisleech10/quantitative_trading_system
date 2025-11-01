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

### 步驟 6: 更新 YAML 配置

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

## 下一步

完成指標實作後：

1. ✅ **運行測試**：確保所有測試通過
2. ✅ **更新配置**：添加到 `config/indicators.yaml`
3. ✅ **編寫文檔**：在 docstring 中說明用法
4. ✅ **性能測試**：確保計算效率符合預期
5. ✅ **提交代碼**：創建 Pull Request

**參考資源**：
- [EMA 指標實作](../momentum/Indicators/ema_indicator.py) - 完整範例
- [BaseIndicator 文檔](../momentum/Indicators/base_indicator.py) - 基類說明
- [API 使用文檔](./indicator_api_usage.md) - 如何使用指標

---

**有問題？** 查看 [常見問題](./faq.md) 或提交 Issue。
