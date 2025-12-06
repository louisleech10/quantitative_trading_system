# 策略擴展指南 (Strategy Extension Guide)

> **目標讀者**: AI Agent (Claude Code, GitHub Copilot 等)
> **最後更新**: 2025-12-04
> **系統版本**: Phase 2 完成 + 混合式架構 (Hybrid Architecture)

---

## 文檔目的

本文檔提供**完整的、可執行的指令**，讓 AI Agent 能夠獨立完成以下任務：
1. 新增技術指標 (Technical Indicators)
2. 新增交易策略 (Trading Strategies)
3. 整合到 Optuna 優化系統
4. 為未來的 XGBoost/LSTM 模型預留接口
5. 測試與驗證

---

## 目錄

1. [系統架構概覽](#1-系統架構概覽)
2. [新增指標 (Indicator)](#2-新增指標-indicator)
3. [新增策略 (Strategy)](#3-新增策略-strategy)
4. [Optuna 整合](#4-optuna-整合)
5. [XGBoost/LSTM 預留接口](#5-xgboostlstm-預留接口)
6. [測試與驗證](#6-測試與驗證)
7. [故障排除](#7-故障排除)
8. [完整範例：RSI 超買超賣策略](#8-完整範例rsi-超買超賣策略)

---

## 1. 系統架構概覽

### 1.1 核心組件

```
quantitative_trading_system/
├── momentum/
│   ├── Indicators/              # 指標引擎
│   │   ├── indicator_engine.py  # 核心引擎
│   │   └── indicators/          # 指標實現
│   │       ├── ema.py
│   │       ├── sma.py
│   │       └── rsi.py           # [AI 新增範例]
│   ├── Analysis/
│   │   ├── strategy_registry.py # 策略註冊表 (核心)
│   │   └── strategies/          # 策略實現
│   │       ├── three_line_strategy.py
│   │       └── rsi_strategy.py  # [AI 新增範例]
│   └── Optimization/
│       ├── strategy_metadata.py # 元數據定義
│       └── optuna_optimizer.py  # Optuna 優化器
├── config/
│   └── strategies.yaml          # 策略配置 (AI 修改此檔案)
└── api/
    └── routes/
        └── optimization.py      # REST API 端點
```

### 1.2 指標架構（混合式設計）

**系統支援兩種指標實作方式**：

| 模式 | 適用場景 | 代碼量 | AI 難度 |
|------|---------|-------|--------|
| **函數式（推薦）** | 新增指標 | ~40 行 | ⭐⭐⭐⭐⭐ 最簡單 |
| **類裝飾器** | 既有指標（如 EMA） | ~130 行 | ⭐⭐⭐ 中等 |

**函數式模式**（推薦）：
- AI 只需寫純函數（`calculate` + `validate`）
- 系統自動包裝成類並註冊
- 獲得完整的錯誤處理、性能監控、日誌記錄

**類裝飾器模式**：
- 繼承 `BaseIndicator` 基類
- 使用 `@register_indicator` 裝飾器
- 已存在的指標（如 EMA）使用此模式

**兩者可共存**：既有指標無需重構，新指標使用函數式。

### 1.3 數據流

```
1. YAML 配置 (config/strategies.yaml)
   ↓
2. StrategyRegistry 載入元數據
   ↓
3. OptunaOptimizer 動態採樣參數
   ↓
4. SignalDensityAnalyzer 計算策略信號
   ↓
5. 返回優化結果
```

### 1.4 關鍵類與方法

| 組件 | 檔案 | 關鍵方法 | 用途 |
|------|------|----------|------|
| **StrategyRegistry** | `momentum/Analysis/strategy_registry.py` | `get_strategy()`, `validate_parameters()` | 策略註冊與驗證 |
| **IndicatorEngine** | `momentum/Indicators/indicator_engine.py` | `calculate_indicators_from_dataframe()` | 批量計算指標 |
| **register_functional_indicator** | `momentum/Indicators/functional_wrapper.py` | 一行註冊函數式指標 | 函數式指標包裝器 |
| **OptunaOptimizer** | `momentum/Optimization/optuna_optimizer.py` | `_objective_function()` | 參數優化 |
| **SignalDensityAnalyzer** | `momentum/Analysis/signal_density_analyzer.py` | `calculate_strategy_signals()` | 計算策略信號 |

---

## 2. 新增指標 (Indicator)

### 2.1 指標命名規範

- **檔案名稱**: `{indicator_name}.py` (小寫，底線分隔)
- **函數名稱**: `calculate_{indicator_name}()` 和 `validate_{indicator_name}_params()`
- **範例**: RSI 指標 → `rsi.py` + `calculate_rsi()` + `validate_rsi_params()`

### 2.2 函數式指標模板（推薦）

**位置**: `momentum/Indicators/{indicator_name}.py`

**代碼量**: ~40 行（核心邏輯）

```python
"""
{指標全名} 指標實作 - 函數式版本

{指標詳細說明}

計算公式:
    {公式描述}

功能特性:
- 使用 pandas_ta 庫計算（如果可用）
- 回退到 pandas 原生方法
- 完整的參數驗證
- 邊界條件處理

Author: AI Agent ({你的名字})
Date: {當前日期}
"""

import pandas as pd
import logging
from typing import Dict, Any

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas_ta not available, using pandas native methods")

from .functional_wrapper import register_functional_indicator

logger = logging.getLogger(__name__)


def calculate_{indicator_name}(data: pd.Series, param1: int = default_value) -> pd.Series:
    """
    計算 {指標全名}

    {指標用途和特點說明}

    計算公式：
        {詳細公式}

    Args:
        data: 輸入數據序列（如 close price, volume 等）
        param1: 參數1說明（默認 {default_value}）
               - 短期: {建議值}
               - 中期: {建議值}
               - 長期: {建議值}

    Returns:
        pd.Series: {指標名} 計算結果（與輸入等長，前 N 個值可能為 NaN）

    Example:
        >>> import pandas as pd
        >>> data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        >>> result = calculate_{indicator_name}(data, param1=3)
        >>> print(result)

    Note:
        - 前 (param1-1) 個值可能為 NaN
        - 如果數據長度 < param1，返回全 NaN 序列
    """
    # 邊界檢查：數據長度不足
    if len(data) < param1:
        logger.warning(
            f"Data length ({len(data)}) < param1 ({param1}), "
            f"returning all NaN"
        )
        return pd.Series([float('nan')] * len(data), index=data.index)

    # 使用 pandas_ta（如果可用）
    if PANDAS_TA_AVAILABLE:
        try:
            # [AI 填入：使用 pandas_ta 的計算邏輯]
            result = ta.{indicator_name}(data, length=param1)
            logger.debug(f"Calculated {indicator_name} using pandas_ta: param1={param1}")
            return result
        except Exception as e:
            logger.warning(
                f"pandas_ta failed, falling back to pandas native: {e}"
            )

    # 回退到 pandas 原生方法
    # [AI 填入：使用 pandas 的計算邏輯]
    result = data.rolling(window=param1).mean()  # 示例：替換為實際邏輯
    logger.debug(f"Calculated {indicator_name} using pandas: param1={param1}")

    return result


def validate_{indicator_name}_params(param1: int = default_value) -> bool:
    """
    驗證 {指標名} 參數有效性

    參數約束：
    - param1 必須是整數
    - param1 範圍: [min_value, max_value]
      - 最小值: {最小值說明}
      - 最大值: {最大值說明}

    Args:
        param1: 參數1

    Returns:
        bool: 參數是否有效（總是返回 True，無效時拋出異常）

    Raises:
        ValueError: 參數無效時拋出詳細錯誤信息

    Example:
        >>> validate_{indicator_name}_params(param1=14)  # True
        >>> validate_{indicator_name}_params(param1=0)   # ValueError
    """
    # 檢查類型
    if not isinstance(param1, int):
        raise ValueError(
            f"param1 must be int, got {type(param1).__name__}"
        )

    # 檢查範圍
    if param1 < min_value:
        raise ValueError(
            f"param1 must be >= {min_value} (got {param1}). "
            f"{最小值原因說明}"
        )

    if param1 > max_value:
        raise ValueError(
            f"param1 must be <= {max_value} (got {param1}). "
            f"{最大值原因說明}"
        )

    return True


# 註冊到系統（一行代碼）
register_functional_indicator(
    name="{indicator_name}",
    calculate_fn=calculate_{indicator_name},
    validate_fn=validate_{indicator_name}_params,
    default_params={"param1": default_value},
    description=(
        "{指標中文全名} - "
        "{一句話描述指標特點}"
    )
)


# 可選：提供便利函數用於直接調用（測試用）
def {indicator_name}(data: pd.Series, param1: int = default_value) -> pd.Series:
    """
    {指標名} 便利函數（直接調用，無錯誤處理）

    此函數直接調用 calculate_{indicator_name}，不經過 IndicatorEngine。
    適用於測試和快速計算，但缺少 BaseIndicator 的錯誤處理。

    Args:
        data: 輸入數據序列
        param1: 參數1

    Returns:
        pd.Series: {指標名} 計算結果

    Example:
        >>> from momentum.Indicators.{indicator_name} import {indicator_name}
        >>> result = {indicator_name}(close_data, param1=14)
    """
    return calculate_{indicator_name}(data, param1=param1)
```

### 2.3 Warmup 需求（⚠️ 重要）

**所有指標都需要 warmup 數據才能計算出準確的初始值！**

**什麼是 Warmup？**
- 技術指標（如 EMA、RSI、MACD）需要歷史數據來「熱身」
- 沒有足夠的 warmup 數據，指標初始值會不準確
- 例如：EMA_30 需要約 135 根 K 線才能收斂到 99.5% 精度

**Warmup 計算公式**：
```python
# 對於 EMA 類指標
WARMUP_MULTIPLIER = 4.5
warmup_bars = int(max_period * WARMUP_MULTIPLIER)
# 例：EMA_30 需要 30 * 4.5 = 135 根 warmup K 線

# 對於其他指標（參考值）
# RSI: period * 2 (需要足夠的漲跌資料)
# MACD: slow_period + signal_period (複合指標)
# Bollinger Bands: period (與 SMA 相同)
```

**API 層已自動處理 Warmup**：
- `chart_data_service.py` 的 `_calculate_indicators_with_warmup()` 方法會：
  1. 根據指標參數計算所需 warmup 數量
  2. 從 HDF5 讀取額外的 warmup 數據
  3. 計算完整指標後，只返回顯示範圍的值

**AI Agent 實現新指標時需注意**：
1. **在指標文檔中說明** warmup 需求（前 N 個值為 NaN）
2. **如果指標有特殊 warmup 需求**（如比 `period * 4.5` 更多），需在 `chart_data_service.py` 中添加特殊處理
3. **測試時使用足夠長的數據**（至少 `period * 5` 根 K 線）

**範例：RSI 的 warmup 說明**：
```python
def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    ...
    Note:
        - 前 (period+1) 個值為 NaN（需要 diff + ewm 初始化）
        - 建議輸入數據長度 >= period * 3 以獲得穩定結果
        - API 層會自動處理 warmup，無需在此函數中處理
    """
```

---

### 2.4 註冊指標到系統

**重要**: 使用函數式模式時，指標會**自動註冊**！無需修改任何其他文件。

**AI 執行步驟**:

1. 創建指標文件 `momentum/Indicators/{indicator_name}.py`（如上模板）
2. 完成！系統會在導入時自動註冊。

**自動註冊原理**:
- `register_functional_indicator()` 會自動將函數包裝成類
- 包裝的類繼承 `BaseIndicator`，獲得完整的錯誤處理、性能監控
- 自動註冊到 `IndicatorEngine`

**驗證註冊成功**:
```python
from momentum.Indicators import IndicatorEngine

engine = IndicatorEngine()
print(engine.list_indicators())  # 應該包含你的指標名稱
```

### 2.5 驗證指標

**AI 執行命令**:
```bash
python3 -c "
from momentum.Indicators import IndicatorEngine, DataSourceEnum
import pandas as pd
import numpy as np

# 創建測試數據
engine = IndicatorEngine()
data = pd.DataFrame({'close': np.random.uniform(100, 200, 100)})

# 測試新指標（通過 IndicatorEngine）
config = {
    'indicator': '{indicator_name}',
    'data_source': 'close',
    'params': {'param1': value},
    'output_name': 'test_{indicator_name}'
}

result = engine.calculate_indicators_from_dataframe(data, [config])
print(f'✅ {indicator_name} 指標驗證成功')
print(result.describe())

# 測試直接調用
from momentum.Indicators.{indicator_name} import calculate_{indicator_name}
direct_result = calculate_{indicator_name}(data['close'], param1=value)
print(f'✅ 直接調用成功，計算 {len(direct_result)} 個值')
"
```

### 2.6 函數式 vs 類裝飾器對比

| 特性 | 函數式（推薦） | 類裝飾器 |
|------|--------------|---------|
| **代碼量** | ~40 行 | ~130 行 |
| **AI 難度** | ⭐⭐⭐⭐⭐ 最簡單 | ⭐⭐⭐ 中等 |
| **需要理解** | 函數、參數 | 類、繼承、裝飾器、self |
| **錯誤處理** | ✅ 自動提供 | ✅ 自動提供 |
| **性能監控** | ✅ 自動提供 | ✅ 自動提供 |
| **自動註冊** | ✅ 一行代碼 | ⚠️ 需裝飾器 |
| **適用場景** | **所有新指標** | 既有指標 |

**結論**: 所有新指標都應使用**函數式模式**。

---

## 3. 新增策略 (Strategy)

### 3.1 策略分類

| 分類 | 說明 | 範例 |
|------|------|------|
| **trend** | 趨勢追蹤 | 三線排列、均線交叉 |
| **momentum** | 動量指標 | RSI、MACD |
| **volatility** | 波動率 | Bollinger Bands |
| **volume** | 成交量 | OBV、Volume Profile |

### 3.2 策略實現模板

**位置**: `momentum/Analysis/strategies/{strategy_name}_strategy.py`

> ⚠️ **Warmup 注意事項**：
> - 策略調用 `IndicatorEngine.calculate_indicators_from_dataframe()` 時
> - **直接調用**：需自行確保輸入數據包含足夠的 warmup 數據
> - **透過 API**：`chart_data_service.py` 已自動處理 warmup
> - **透過 SignalDensityAnalyzer**：`_extract_full_density_window()` 已處理 warmup

```python
"""
{策略名稱}策略實現

策略邏輯: {詳細描述策略邏輯}

參數說明:
- param1: {說明}
- param2: {說明}

Warmup 需求:
    - 此策略使用的指標需要 {N} 根 K 線作為 warmup
    - API 層和 SignalDensityAnalyzer 已自動處理 warmup
    - 直接調用時需確保輸入數據足夠長

Author: AI Agent
Date: {當前日期}
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from momentum.Indicators.indicator_engine import IndicatorEngine
from api.core.logging import get_logger

logger = get_logger("{strategy_name}_strategy")


def calculate_signals(
    kline_data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> np.ndarray:
    """
    計算{策略名稱}策略信號

    這是策略的核心計算函數，由 SignalDensityAnalyzer 動態調用。

    Args:
        kline_data: K線數據DataFrame，包含 open, high, low, close, volume 列
        indicators: 預計算的指標字典（通常為空，策略自己計算）
        params: 參數字典，包含:
            - param1: {說明}
            - param2: {說明}
            - indicator_type: 指標類型 (ema/sma/...)
            - data_source: 數據源 (close/open/high/low)

    Returns:
        np.ndarray: boolean 數組，True 表示信號有效（持續條件）

    Raises:
        ValueError: 當參數缺失或無效時
        KeyError: 當必要參數不存在時

    策略邏輯:
        {詳細描述策略的數學邏輯和條件}

    Example:
        >>> params = {
        ...     'param1': 14,
        ...     'param2': 70,
        ...     'indicator_type': 'ema',
        ...     'data_source': 'close'
        ... }
        >>> signals = calculate_signals(kline_data, {}, params)
        >>> print(f"信號數量: {np.sum(signals)}/{len(signals)}")
    """
    try:
        # 步驟1: 提取參數
        param1 = params['param1']
        param2 = params['param2']
        indicator_type = params.get('indicator_type', 'ema')
        data_source = params.get('data_source', 'close')

        logger.debug(
            f"Calculating {strategy_name} signals with "
            f"param1={param1}, param2={param2}"
        )

        # 步驟2: 創建 IndicatorEngine 並配置指標
        indicator_engine = IndicatorEngine()

        indicator_configs = [
            {
                "indicator": "indicator_name",
                "data_source": data_source,
                "params": {"period": param1},
                "output_name": "indicator_output"
            },
            # [AI 添加更多指標配置]
        ]

        # 步驟3: 批量計算指標
        indicators_df = indicator_engine.calculate_indicators_from_dataframe(
            kline_data,
            indicator_configs
        )

        # 步驟4: 驗證指標計算結果
        required_cols = ["indicator_output"]  # [AI 列出所有需要的列]
        missing_cols = [col for col in required_cols if col not in indicators_df.columns]
        if missing_cols:
            error_msg = f"Indicator calculation missing columns: {missing_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 步驟5: 應用策略邏輯
        # [AI 實現策略邏輯]
        # 範例: RSI 超買超賣
        # signals = (
        #     (indicators_df["rsi"] < params['oversold_threshold']) |
        #     (indicators_df["rsi"] > params['overbought_threshold'])
        # )

        signals = np.zeros(len(kline_data), dtype=bool)  # [AI 替換為實際邏輯]

        logger.debug(
            f"Strategy signals calculated: {np.sum(signals)}/{len(signals)} bars"
        )

        return signals

    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        raise ValueError(f"Missing required parameter: {e}")
    except Exception as e:
        logger.error(
            f"Failed to calculate {strategy_name} signals: {e}",
            exc_info=True
        )
        raise


def validate_params(params: Dict[str, Any]) -> List[str]:
    """
    驗證策略參數（業務邏輯驗證）

    這是可選的驗證函數，用於檢查參數之間的業務邏輯關係。
    基礎驗證（類型、範圍）由 StrategyRegistry 自動處理。

    Args:
        params: 參數字典

    Returns:
        List[str]: 錯誤訊息列表（空列表表示驗證通過）

    Example:
        >>> params = {'period': 14, 'threshold': 70}
        >>> errors = validate_params(params)
        >>> if errors:
        ...     print("驗證失敗:", errors)
    """
    errors = []

    try:
        param1 = params['param1']
        param2 = params['param2']

        # [AI 添加業務邏輯驗證]
        # 範例: 檢查參數關係
        # if param1 >= param2:
        #     errors.append(f"param1 ({param1}) 必須小於 param2 ({param2})")

        # 範例: 檢查參數合理性
        # if param2 < 50 or param2 > 100:
        #     errors.append(
        #         f"param2 ({param2}) 超出合理範圍 [50, 100]，"
        #         f"可能導致過多或過少的信號"
        #     )

    except KeyError as e:
        errors.append(f"缺少必要參數: {e}")

    return errors
```

### 3.3 配置策略元數據

**位置**: `config/strategies.yaml`

**AI 執行步驟**: 在 `strategies:` 區塊下添加新策略

```yaml
strategies:
  {strategy_id}:  # 策略唯一標識符 (小寫，底線分隔)
    display_name: "{策略中文名稱}"
    description: "{策略詳細描述，包含核心邏輯}"
    category: "{trend|momentum|volatility|volume}"

    # 參數定義列表
    parameters:
      - name: "param1"
        display_name: "參數1名稱"
        type: "int"  # int | float | categorical
        default_value: 14
        min_value: 5
        max_value: 30
        step: 1
        description: "參數1的詳細說明"
        unit: "根K線"  # 可選
        constraints:  # 參數約束（可選）
          - type: "less_than"  # less_than | greater_than | less_than_or_equal | ...
            target: "param2"
            message: "param1 必須小於 param2"

      - name: "param2"
        display_name: "參數2名稱"
        type: "float"
        default_value: 70.0
        min_value: 50.0
        max_value: 100.0
        step: 0.5
        description: "參數2的詳細說明"
        unit: "%"

    # 支援的指標和數據源
    supported_indicators: ["ema", "sma", "{indicator_name}"]
    supported_data_sources: ["close", "open", "high", "low"]

    # 計算函數位置（動態導入）
    calculator_module: "momentum.Analysis.strategies.{strategy_name}_strategy"
    calculator_function: "calculate_signals"

    # 驗證函數位置（可選）
    validator_module: "momentum.Analysis.strategies.{strategy_name}_strategy"
    validator_function: "validate_params"

    # UI 相關
    icon: "📊"  # 策略圖標
    recommended_for: "{使用場景說明}"
    complexity: "simple"  # simple | medium | advanced

    # 標籤（用於搜索和分類）
    tags:
      - "{category}"
      - "{indicator_name}"
      - "{特性}"
```

### 3.4 參數類型說明

| 類型 | YAML type | 必要欄位 | 範例 |
|------|-----------|---------|------|
| **整數** | `int` | `min_value`, `max_value`, `step` | 週期、數量 |
| **浮點數** | `float` | `min_value`, `max_value`, `step` | 閾值、比率 |
| **分類** | `categorical` | `choices` | 指標類型、數據源 |

### 3.5 約束類型說明

| 約束類型 | 說明 | 範例 |
|---------|------|------|
| `less_than` | A < B | short_period < mid_period |
| `less_than_or_equal` | A ≤ B | threshold ≤ 100 |
| `greater_than` | A > B | oversold > 0 |
| `greater_than_or_equal` | A ≥ B | period ≥ 5 |

---

## 4. Optuna 整合

### 4.1 自動整合機制

**重要**: Optuna 優化器已經完全重構為**動態參數採樣系統**，無需修改任何代碼！

當你完成以下步驟後，Optuna 會自動整合新策略：
1. ✅ 創建策略實現檔案 (`{strategy_name}_strategy.py`)
2. ✅ 配置 YAML (`config/strategies.yaml`)

### 4.2 Optuna 如何使用新策略

**位置**: `momentum/Optimization/optuna_optimizer.py:613-660`

```python
# Optuna 優化器的動態採樣邏輯 (已實現，無需修改)

def _objective_function(self, trial: Trial) -> float:
    # 步驟1: 用戶選擇策略
    strategy_logic = self.strategy_logic  # 例如: "rsi_strategy"

    # 步驟2: 從註冊表獲取策略元數據
    from momentum.Analysis.strategy_registry import strategy_registry
    metadata = strategy_registry.get_strategy(strategy_logic)

    # 步驟3: 動態採樣所有參數
    params = {}
    for param_def in metadata.parameters:
        if param_def.type == ParameterType.INT:
            params[param_def.name] = trial.suggest_int(
                param_def.name,
                int(param_def.min_value),
                int(param_def.max_value),
                step=int(param_def.step) if param_def.step else 1
            )
        elif param_def.type == ParameterType.FLOAT:
            params[param_def.name] = trial.suggest_float(
                param_def.name,
                param_def.min_value,
                param_def.max_value,
                step=param_def.step
            )
        elif param_def.type == ParameterType.CATEGORICAL:
            params[param_def.name] = trial.suggest_categorical(
                param_def.name,
                param_def.choices
            )

    # 步驟4: 參數驗證
    validation_result = strategy_registry.validate_parameters(strategy_logic, params)
    if not validation_result.is_valid:
        raise optuna.TrialPruned()  # 跳過無效參數組合

    # 步驟5: 計算目標函數值
    return self._calculate_objective_value(params)
```

### 4.3 測試 Optuna 整合

**AI 執行命令**:
```python
from momentum.Optimization.optuna_optimizer import OptunaOptimizer
import optuna

# 創建優化器
optimizer = OptunaOptimizer(
    study_name="test_{strategy_name}",
    n_trials=10,
    strategy_logic="{strategy_id}"  # 你的策略 ID
)

# 執行優化（需要設置案例數據）
# optimizer.optimize(positive_cases, negative_cases, training_window)

print("✅ Optuna 整合測試成功")
```

---

## 5. XGBoost/LSTM 預留接口

### 5.1 設計理念

為了讓 XGBoost 和 LSTM 模型能夠使用策略系統的指標和參數，我們設計了**特徵提取接口**。

### 5.2 特徵提取器架構

**位置**: `momentum/ML/feature_extractor.py` (AI 需要創建)

```python
"""
機器學習特徵提取器

將策略系統的指標計算能力轉換為 ML 模型的特徵。

Author: AI Agent
Date: {當前日期}
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from momentum.Analysis.strategy_registry import strategy_registry
from momentum.Indicators.indicator_engine import IndicatorEngine


class FeatureExtractor:
    """
    為 XGBoost/LSTM 模型提取特徵

    使用策略系統的指標引擎，確保特徵計算與策略優化一致。
    """

    def __init__(self):
        self.indicator_engine = IndicatorEngine()
        self.strategy_registry = strategy_registry

    def extract_strategy_features(
        self,
        kline_data: pd.DataFrame,
        strategy_id: str,
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        從策略中提取特徵

        Args:
            kline_data: K線數據
            strategy_id: 策略ID
            params: 策略參數

        Returns:
            pd.DataFrame: 特徵矩陣
        """
        # 1. 獲取策略元數據
        metadata = self.strategy_registry.get_strategy(strategy_id)

        # 2. 計算策略信號（作為特徵）
        calculator = self.strategy_registry.get_calculator(strategy_id)
        signals = calculator(kline_data, {}, params)

        # 3. 提取指標值（作為額外特徵）
        features = pd.DataFrame(index=kline_data.index)
        features['strategy_signal'] = signals.astype(int)

        # 4. 添加原始指標值
        # [AI 實現：提取策略使用的所有指標值]

        return features

    def extract_indicator_features(
        self,
        kline_data: pd.DataFrame,
        indicator_configs: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        從指標配置中提取特徵

        Args:
            kline_data: K線數據
            indicator_configs: 指標配置列表

        Returns:
            pd.DataFrame: 特徵矩陣
        """
        return self.indicator_engine.calculate_indicators_from_dataframe(
            kline_data,
            indicator_configs
        )

    def extract_multiple_strategies(
        self,
        kline_data: pd.DataFrame,
        strategy_params: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        從多個策略中提取特徵（集成學習）

        Args:
            kline_data: K線數據
            strategy_params: 策略參數列表，每個元素包含:
                - strategy_id: 策略ID
                - params: 參數字典

        Returns:
            pd.DataFrame: 合併的特徵矩陣
        """
        all_features = []

        for config in strategy_params:
            features = self.extract_strategy_features(
                kline_data,
                config['strategy_id'],
                config['params']
            )
            features = features.add_prefix(f"{config['strategy_id']}_")
            all_features.append(features)

        return pd.concat(all_features, axis=1)
```

### 5.3 XGBoost 整合範例

**位置**: `momentum/ML/xgboost_model.py` (AI 需要創建)

```python
"""
XGBoost 模型整合範例

展示如何使用策略系統的特徵。

Author: AI Agent
Date: {當前日期}
"""

import xgboost as xgb
import pandas as pd
from typing import Dict, Any

from momentum.ML.feature_extractor import FeatureExtractor


class XGBoostStrategy:
    """
    基於 XGBoost 的策略模型
    """

    def __init__(self, feature_configs: List[Dict[str, Any]]):
        """
        Args:
            feature_configs: 特徵配置列表（策略+參數）
        """
        self.feature_extractor = FeatureExtractor()
        self.feature_configs = feature_configs
        self.model = None

    def extract_features(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        """提取訓練特徵"""
        return self.feature_extractor.extract_multiple_strategies(
            kline_data,
            self.feature_configs
        )

    def train(self, X: pd.DataFrame, y: pd.Series):
        """訓練 XGBoost 模型"""
        dtrain = xgb.DMatrix(X, label=y)

        params = {
            'max_depth': 6,
            'eta': 0.1,
            'objective': 'binary:logistic',
            'eval_metric': 'auc'
        }

        self.model = xgb.train(params, dtrain, num_boost_round=100)

    def predict(self, kline_data: pd.DataFrame) -> pd.Series:
        """預測信號"""
        features = self.extract_features(kline_data)
        dtest = xgb.DMatrix(features)
        predictions = self.model.predict(dtest)
        return pd.Series(predictions > 0.5, index=kline_data.index)
```

### 5.4 LSTM 整合範例

**位置**: `momentum/ML/lstm_model.py` (AI 需要創建)

```python
"""
LSTM 模型整合範例

展示如何使用策略系統的時序特徵。

Author: AI Agent
Date: {當前日期}
"""

import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

from momentum.ML.feature_extractor import FeatureExtractor


class LSTMStrategy(nn.Module):
    """
    基於 LSTM 的策略模型
    """

    def __init__(
        self,
        feature_configs: List[Dict[str, Any]],
        hidden_size: int = 64,
        num_layers: int = 2
    ):
        super().__init__()

        self.feature_extractor = FeatureExtractor()
        self.feature_configs = feature_configs

        # 計算特徵維度
        sample_data = pd.DataFrame({'close': [100]})
        sample_features = self.feature_extractor.extract_multiple_strategies(
            sample_data,
            feature_configs
        )
        input_size = sample_features.shape[1]

        # LSTM 層
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )

        # 輸出層
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向傳播"""
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]
        logits = self.fc(last_output)
        return self.sigmoid(logits)

    def extract_sequences(
        self,
        kline_data: pd.DataFrame,
        sequence_length: int = 60
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        提取時序特徵序列

        Args:
            kline_data: K線數據
            sequence_length: 序列長度

        Returns:
            (X, indices): 特徵序列和對應的索引
        """
        # 提取所有特徵
        features = self.feature_extractor.extract_multiple_strategies(
            kline_data,
            self.feature_configs
        )

        # 創建滑動窗口序列
        X = []
        indices = []

        for i in range(sequence_length, len(features)):
            X.append(features.iloc[i-sequence_length:i].values)
            indices.append(i)

        return np.array(X), np.array(indices)
```

### 5.5 使用範例

```python
# XGBoost 範例
feature_configs = [
    {'strategy_id': 'three_line', 'params': {'short_period': 7, 'mid_period': 21, 'long_period': 70}},
    {'strategy_id': 'rsi_strategy', 'params': {'period': 14, 'oversold': 30, 'overbought': 70}}
]

xgb_model = XGBoostStrategy(feature_configs)
features = xgb_model.extract_features(kline_data)
# xgb_model.train(features, labels)

# LSTM 範例
lstm_model = LSTMStrategy(feature_configs, hidden_size=64)
X, indices = lstm_model.extract_sequences(kline_data, sequence_length=60)
# 訓練 LSTM ...
```

---

## 6. 測試與驗證

### 6.1 單元測試模板

**位置**: `tests/test_{strategy_name}_strategy.py`

```python
"""
{策略名稱}策略測試

Author: AI Agent
Date: {當前日期}
"""

import pytest
import pandas as pd
import numpy as np

from momentum.Analysis.strategy_registry import strategy_registry
from momentum.Analysis.strategies.{strategy_name}_strategy import (
    calculate_signals,
    validate_params
)


class Test{StrategyName}Strategy:
    """測試 {策略名稱} 策略"""

    def test_strategy_registered(self):
        """測試策略已註冊"""
        metadata = strategy_registry.get_strategy("{strategy_id}")
        assert metadata.strategy_id == "{strategy_id}"
        assert metadata.display_name == "{策略中文名稱}"

    def test_calculate_signals_valid_params(self):
        """測試有效參數的信號計算"""
        # 創建測試數據
        kline_data = pd.DataFrame({
            'timestamp': range(100),
            'open': np.random.uniform(40000, 42000, 100),
            'high': np.random.uniform(41000, 43000, 100),
            'low': np.random.uniform(39000, 41000, 100),
            'close': np.random.uniform(40000, 42000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })

        params = {
            'param1': 14,
            'param2': 70,
            'indicator_type': 'ema',
            'data_source': 'close'
        }

        signals = calculate_signals(kline_data, {}, params)

        assert isinstance(signals, np.ndarray)
        assert len(signals) == len(kline_data)
        assert signals.dtype == bool
        print(f"✅ 信號計算成功: {np.sum(signals)}/{len(signals)} 個信號")

    def test_parameter_validation(self):
        """測試參數驗證"""
        # 有效參數
        valid_params = {
            'param1': 14,
            'param2': 70,
            'indicator_type': 'ema',
            'data_source': 'close'
        }

        result = strategy_registry.validate_parameters("{strategy_id}", valid_params)
        assert result.is_valid, f"有效參數被拒絕: {result.errors}"

        # 無效參數（根據你的約束）
        invalid_params = {
            'param1': 30,  # 超出範圍
            'param2': 70,
            'indicator_type': 'ema',
            'data_source': 'close'
        }

        result = strategy_registry.validate_parameters("{strategy_id}", invalid_params)
        assert not result.is_valid, "無效參數應該被拒絕"
        print(f"✅ 參數驗證正確: {result.errors}")

    def test_custom_validation(self):
        """測試自定義驗證函數"""
        # 測試業務邏輯驗證
        params = {
            'param1': 14,
            'param2': 70
        }

        errors = validate_params(params)
        assert isinstance(errors, list)
        print(f"✅ 自定義驗證通過: {len(errors)} 個錯誤")

    def test_signal_consistency(self):
        """測試信號一致性（同樣的輸入應產生同樣的輸出）"""
        kline_data = pd.DataFrame({
            'close': [100, 102, 101, 105, 103, 107, 106, 110, 108]
        })

        params = {
            'param1': 3,
            'param2': 70,
            'indicator_type': 'ema',
            'data_source': 'close'
        }

        signals1 = calculate_signals(kline_data, {}, params)
        signals2 = calculate_signals(kline_data, {}, params)

        assert np.array_equal(signals1, signals2), "信號計算不一致"
        print("✅ 信號計算一致性驗證通過")


if __name__ == "__main__":
    # 運行測試
    test = Test{StrategyName}Strategy()
    test.test_strategy_registered()
    test.test_calculate_signals_valid_params()
    test.test_parameter_validation()
    test.test_custom_validation()
    test.test_signal_consistency()

    print("\n" + "="*60)
    print("✅ 所有測試通過！")
    print("="*60)
```

### 6.2 運行測試

**AI 執行命令**:
```bash
# 運行單個策略測試
python3 tests/test_{strategy_name}_strategy.py

# 運行所有策略測試
python3 -m pytest tests/test_*_strategy.py -v

# 運行整合測試
python3 test_phase2_integration.py
```

### 6.3 驗證清單

**AI 執行此清單以確保策略正確整合**:

- [ ] 指標已實現並註冊到 IndicatorEngine
- [ ] 策略實現檔案已創建 (`{strategy_name}_strategy.py`)
- [ ] YAML 配置已添加 (`config/strategies.yaml`)
- [ ] 策略可從註冊表獲取: `strategy_registry.get_strategy("{strategy_id}")`
- [ ] 參數驗證通過: `strategy_registry.validate_parameters(...)`
- [ ] 信號計算函數可執行: `calculate_signals(...)`
- [ ] 單元測試通過
- [ ] API 端點返回新策略: `GET /api/v1/optimization/strategies`

---

## 7. 故障排除

### 7.1 常見錯誤

#### 錯誤 1: 策略未找到

**錯誤訊息**:
```
ValueError: Strategy 'xxx' not found in registry
```

**原因**: YAML 配置未正確載入或策略 ID 拼寫錯誤

**解決方案**:
```python
# 檢查已註冊的策略
from momentum.Analysis.strategy_registry import strategy_registry
strategies = strategy_registry.list_strategies()
print([s.strategy_id for s in strategies])

# 檢查 YAML 語法
import yaml
with open('config/strategies.yaml') as f:
    data = yaml.safe_load(f)
    print(data.keys())
```

#### 錯誤 2: 循環依賴

**錯誤訊息**:
```
ImportError: cannot import name 'strategy_registry' from partially initialized module
```

**原因**: 策略模組在頂層 import strategy_registry

**解決方案**: 使用 lazy import
```python
# ❌ 錯誤
from momentum.Analysis.strategy_registry import strategy_registry

def calculate_signals(...):
    metadata = strategy_registry.get_strategy(...)

# ✅ 正確
def calculate_signals(...):
    from momentum.Analysis.strategy_registry import strategy_registry
    metadata = strategy_registry.get_strategy(...)
```

#### 錯誤 3: 參數驗證失敗

**錯誤訊息**:
```
optuna.TrialPruned: Parameter validation failed
```

**原因**: 參數約束配置錯誤或過於嚴格

**解決方案**:
```python
# 測試參數驗證
params = {...}
result = strategy_registry.validate_parameters("strategy_id", params)
print(f"Valid: {result.is_valid}")
print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")
```

#### 錯誤 4: 指標計算失敗

**錯誤訊息**:
```
ValueError: Indicator calculation missing columns: ['xxx']
```

**原因**: 指標配置中的 `output_name` 與驗證代碼不匹配

**解決方案**:
```python
# 確保 output_name 與驗證代碼一致
indicator_configs = [
    {
        "indicator": "rsi",
        "data_source": "close",
        "params": {"period": 14},
        "output_name": "rsi_14"  # ← 這個名稱
    }
]

# 驗證代碼
required_cols = ["rsi_14"]  # ← 必須匹配
```

#### 錯誤 5: 指標值與交易所不一致

**錯誤訊息**:
```
Charts 頁面顯示 EMA_30 = 3442.04
Binance 顯示 EMA_30 = 3441.99
```

**原因**: Warmup 數據不足導致指標計算不準確

**解決方案**:
```python
# 問題診斷
# 1. 檢查輸入數據長度
print(f"Input data length: {len(kline_data)}")
print(f"Required warmup for EMA_30: {30 * 4.5} = 135 bars")

# 2. 確認 API 層是否使用了 warmup
# chart_data_service.py 中應該有:
WARMUP_MULTIPLIER = 4.5

async def _calculate_indicators_with_warmup(...):
    # 計算 warmup 需求
    warmup_bars = int(max_period * WARMUP_MULTIPLIER)
    # 讀取 display_bars + warmup_bars 的數據
    # 計算指標
    # 只返回 display_bars 範圍的指標值

# 3. 若是前端顯示問題，檢查是否使用了截斷（不是四捨五入）
# ✅ 正確: Math.floor(value * 100) / 100  → 3441.99
# ❌ 錯誤: value.toFixed(2)               → 3442.00
```

**參考**: API 層 warmup 實現見 [chart_data_service.py](../api/services/chart_data_service.py) 的 `_calculate_indicators_with_warmup()` 方法

---

### 7.2 調試技巧

**啟用詳細日誌**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**檢查中間結果**:
```python
# 在策略函數中添加調試輸出
print(f"指標計算結果: {indicators_df.head()}")
print(f"信號數量: {np.sum(signals)}")
print(f"非 NaN 值數量: {np.sum(~pd.isna(signals))}")
```

---

## 8. 完整範例：RSI 超買超賣策略

### 8.1 步驟概覽

我們將實現一個完整的 RSI 超買超賣策略，展示完整流程。

### 8.2 步驟 1: 實現 RSI 指標（函數式）

**檔案**: `momentum/Indicators/rsi.py`

**代碼量**: ~80 行（包含完整文檔）

```python
"""
RSI 指標實作 - 函數式版本

相對強弱指標（Relative Strength Index）

計算公式:
    RSI = 100 - (100 / (1 + RS))
    RS = 平均漲幅 / 平均跌幅

功能特性:
- 使用 pandas_ta 庫計算（如果可用）
- 回退到 pandas 原生 ewm
- 完整的參數驗證
- 邊界條件處理

Author: AI Agent
Date: 2025-12-04
"""

import pandas as pd
import numpy as np
import logging

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas_ta not available, using pandas native methods")

from .functional_wrapper import register_functional_indicator

logger = logging.getLogger(__name__)


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    計算 RSI（相對強弱指標）

    RSI 用於衡量價格變動的速度和幅度，識別超買超賣狀態。

    計算公式：
        RS = 平均漲幅 / 平均跌幅
        RSI = 100 - (100 / (1 + RS))

    Args:
        data: 輸入數據序列（通常是 close price）
        period: RSI 週期（默認 14）
               - 短期: 7, 9
               - 標準: 14
               - 長期: 21, 28

    Returns:
        pd.Series: RSI 值（0-100），前 period+1 個值為 NaN

    Example:
        >>> import pandas as pd
        >>> data = pd.Series([100, 102, 101, 105, 103, 107, 106, 110])
        >>> rsi = calculate_rsi(data, period=3)
        >>> print(rsi)

    Note:
        - 前 (period+1) 個值為 NaN（需要 diff + ewm 初始化）
        - RSI > 70: 超買區域
        - RSI < 30: 超賣區域
    """
    # 邊界檢查：數據長度不足
    if len(data) < period + 1:
        logger.warning(
            f"Data length ({len(data)}) < period+1 ({period+1}), "
            f"returning all NaN"
        )
        return pd.Series([float('nan')] * len(data), index=data.index)

    # 使用 pandas_ta（如果可用）
    if PANDAS_TA_AVAILABLE:
        try:
            result = ta.rsi(data, length=period)
            logger.debug(f"Calculated RSI using pandas_ta: period={period}")
            return result
        except Exception as e:
            logger.warning(
                f"pandas_ta failed, falling back to pandas native: {e}"
            )

    # 回退到 pandas 原生方法
    # 計算價格變化
    delta = data.diff()

    # 分離漲跌
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # 計算平均漲跌（使用 EMA）
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()

    # 計算 RS 和 RSI
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))

    logger.debug(f"Calculated RSI using pandas: period={period}")

    return rsi


def validate_rsi_params(period: int = 14) -> bool:
    """
    驗證 RSI 參數有效性

    參數約束：
    - period 必須是整數
    - period 範圍: [2, 50]
      - 最小 2: 技術上可計算的最小值
      - 最大 50: 超過此值 RSI 變化過於緩慢

    Args:
        period: RSI 週期

    Returns:
        bool: 參數是否有效（總是返回 True，無效時拋出異常）

    Raises:
        ValueError: 參數無效時拋出詳細錯誤信息

    Example:
        >>> validate_rsi_params(period=14)  # True
        >>> validate_rsi_params(period=1)   # ValueError
    """
    # 檢查類型
    if not isinstance(period, int):
        raise ValueError(
            f"period must be int, got {type(period).__name__}"
        )

    # 檢查範圍
    if period < 2:
        raise ValueError(
            f"period must be >= 2 (got {period}). "
            f"Period too small for meaningful RSI calculation."
        )

    if period > 50:
        raise ValueError(
            f"period must be <= 50 (got {period}). "
            f"Period too large, RSI will be too slow to react."
        )

    return True


# 註冊到系統（一行代碼）
register_functional_indicator(
    name="rsi",
    calculate_fn=calculate_rsi,
    validate_fn=validate_rsi_params,
    default_params={"period": 14},
    description=(
        "相對強弱指標（Relative Strength Index）- "
        "衡量價格變動速度和幅度，識別超買超賣狀態"
    )
)


# 可選：提供便利函數用於直接調用（測試用）
def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI 便利函數（直接調用，無錯誤處理）

    Example:
        >>> from momentum.Indicators.rsi import rsi
        >>> result = rsi(close_data, period=14)
    """
    return calculate_rsi(data, period=period)
```

### 8.3 步驟 2: 驗證 RSI 自動註冊

**重要**: 使用函數式模式，RSI 已自動註冊，無需修改其他文件！

**驗證命令**:
```python
from momentum.Indicators import IndicatorEngine

engine = IndicatorEngine()
print(engine.list_indicators())  # 應該包含 'rsi'
print(engine.get_indicator_info('rsi'))  # 查看 RSI 元信息
```

### 8.4 步驟 3: 實現 RSI 策略

**檔案**: `momentum/Analysis/strategies/rsi_strategy.py`

```python
"""
RSI 超買超賣策略實現

策略邏輯:
- RSI > overbought_threshold: 超買信號
- RSI < oversold_threshold: 超賣信號
- 兩者之一為 True 時產生信號

Author: AI Agent
Date: 2025-12-03
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from momentum.Indicators.indicator_engine import IndicatorEngine
from api.core.logging import get_logger

logger = get_logger("rsi_strategy")


def calculate_signals(
    kline_data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> np.ndarray:
    """
    計算 RSI 超買超賣策略信號

    Args:
        kline_data: K線數據
        indicators: 預計算指標（未使用）
        params: 參數字典
            - period: RSI 週期
            - overbought_threshold: 超買閾值
            - oversold_threshold: 超賣閾值
            - indicator_type: 指標類型（未使用，RSI 固定）
            - data_source: 數據源

    Returns:
        np.ndarray: boolean 陣列
    """
    try:
        # 提取參數
        period = params['period']
        overbought = params['overbought_threshold']
        oversold = params['oversold_threshold']
        data_source = params.get('data_source', 'close')

        logger.debug(
            f"Calculating RSI strategy: period={period}, "
            f"overbought={overbought}, oversold={oversold}"
        )

        # 創建指標引擎
        indicator_engine = IndicatorEngine()

        # 配置 RSI 指標
        indicator_configs = [
            {
                "indicator": "rsi",
                "data_source": data_source,
                "params": {"period": period},
                "output_name": "rsi"
            }
        ]

        # 計算 RSI
        indicators_df = indicator_engine.calculate_indicators_from_dataframe(
            kline_data,
            indicator_configs
        )

        # 驗證結果
        if "rsi" not in indicators_df.columns:
            raise ValueError("RSI calculation failed")

        # 應用策略邏輯
        signals = (
            (indicators_df["rsi"] > overbought) |
            (indicators_df["rsi"] < oversold)
        )

        logger.debug(
            f"RSI strategy signals: {np.sum(signals)}/{len(signals)} bars, "
            f"overbought={np.sum(indicators_df['rsi'] > overbought)}, "
            f"oversold={np.sum(indicators_df['rsi'] < oversold)}"
        )

        return signals.values

    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        raise ValueError(f"Missing required parameter: {e}")
    except Exception as e:
        logger.error(f"Failed to calculate RSI strategy: {e}", exc_info=True)
        raise


def validate_params(params: Dict[str, Any]) -> List[str]:
    """驗證 RSI 策略參數"""
    errors = []

    try:
        period = params['period']
        overbought = params['overbought_threshold']
        oversold = params['oversold_threshold']

        # 檢查閾值關係
        if oversold >= overbought:
            errors.append(
                f"oversold_threshold ({oversold}) 必須小於 "
                f"overbought_threshold ({overbought})"
            )

        # 檢查閾值合理性
        if oversold < 10:
            errors.append(
                f"oversold_threshold ({oversold}) 過低，可能產生過少信號"
            )

        if overbought > 90:
            errors.append(
                f"overbought_threshold ({overbought}) 過高，可能產生過少信號"
            )

        # 檢查週期合理性
        if period < 5:
            errors.append(
                f"RSI 週期 ({period}) 過短，可能產生過多假信號"
            )

    except KeyError as e:
        errors.append(f"缺少必要參數: {e}")

    return errors
```

### 8.5 步驟 4: 配置 YAML

**檔案**: `config/strategies.yaml`

```yaml
strategies:
  # ... 現有策略 ...

  rsi_strategy:
    display_name: "RSI 超買超賣"
    description: "使用 RSI 指標識別超買超賣區域。RSI > 70 為超買，RSI < 30 為超賣。"
    category: "momentum"

    parameters:
      - name: "period"
        display_name: "RSI 週期"
        type: "int"
        default_value: 14
        min_value: 5
        max_value: 30
        step: 1
        description: "RSI 計算週期"
        unit: "根K線"

      - name: "overbought_threshold"
        display_name: "超買閾值"
        type: "float"
        default_value: 70.0
        min_value: 60.0
        max_value: 90.0
        step: 1.0
        description: "RSI 超買閾值（高於此值視為超買）"
        unit: "%"
        constraints:
          - type: "greater_than"
            target: "oversold_threshold"
            message: "超買閾值必須大於超賣閾值"

      - name: "oversold_threshold"
        display_name: "超賣閾值"
        type: "float"
        default_value: 30.0
        min_value: 10.0
        max_value: 40.0
        step: 1.0
        description: "RSI 超賣閾值（低於此值視為超賣）"
        unit: "%"

    supported_indicators: ["rsi"]
    supported_data_sources: ["close"]

    calculator_module: "momentum.Analysis.strategies.rsi_strategy"
    calculator_function: "calculate_signals"

    validator_module: "momentum.Analysis.strategies.rsi_strategy"
    validator_function: "validate_params"

    icon: "📊"
    recommended_for: "適合震盪市場，識別超買超賣區域進行反轉交易"
    complexity: "simple"

    tags:
      - "momentum"
      - "rsi"
      - "overbought_oversold"
```

### 8.6 步驟 5: 測試

**AI 執行**:

```bash
# 測試指標
python3 -c "
from momentum.Indicators.indicator_engine import IndicatorEngine
import pandas as pd
import numpy as np

engine = IndicatorEngine()
data = pd.DataFrame({'close': np.random.uniform(40000, 42000, 100)})

config = {
    'indicator': 'rsi',
    'data_source': 'close',
    'params': {'period': 14},
    'output_name': 'rsi'
}

result = engine.calculate_indicators_from_dataframe(data, [config])
print('✅ RSI 指標測試成功')
print(result['rsi'].describe())
"

# 測試策略
python3 -c "
from momentum.Analysis.strategy_registry import strategy_registry
import pandas as pd
import numpy as np

# 檢查策略是否已註冊
metadata = strategy_registry.get_strategy('rsi_strategy')
print(f'✅ 策略已註冊: {metadata.display_name}')

# 測試參數驗證
params = {
    'period': 14,
    'overbought_threshold': 70.0,
    'oversold_threshold': 30.0,
    'data_source': 'close'
}

result = strategy_registry.validate_parameters('rsi_strategy', params)
print(f'✅ 參數驗證: {result.is_valid}')

# 測試信號計算
from momentum.Analysis.strategies.rsi_strategy import calculate_signals

kline_data = pd.DataFrame({
    'close': np.random.uniform(40000, 42000, 100)
})

signals = calculate_signals(kline_data, {}, params)
print(f'✅ 信號計算成功: {np.sum(signals)}/{len(signals)} 個信號')
"
```

### 8.7 步驟 6: API 驗證

**AI 執行**:

```python
from momentum.Analysis.strategy_registry import strategy_registry

# 檢查 API 返回
strategies = strategy_registry.list_strategies()
rsi_found = any(s.strategy_id == 'rsi_strategy' for s in strategies)

if rsi_found:
    print("✅ RSI 策略已出現在 API 端點中")

    # 獲取詳細信息
    metadata = strategy_registry.get_strategy('rsi_strategy')
    print(f"  - 顯示名稱: {metadata.display_name}")
    print(f"  - 參數數量: {len(metadata.parameters)}")
    print(f"  - 類別: {metadata.category}")
else:
    print("❌ RSI 策略未找到")
```

---

## 9. 快速參考

### 9.1 AI Agent 執行清單

**新增一個完整策略的標準流程**:

```bash
# 步驟 1: 創建指標（如果需要新指標）
touch momentum/Indicators/indicators/{indicator_name}.py
# [AI 實現指標計算函數]

# 步驟 2: 註冊指標
# [AI 編輯 momentum/Indicators/indicator_engine.py]

# 步驟 3: 創建策略
touch momentum/Analysis/strategies/{strategy_name}_strategy.py
# [AI 實現 calculate_signals 和 validate_params]

# 步驟 4: 配置 YAML
# [AI 編輯 config/strategies.yaml]

# 步驟 5: 測試
python3 -c "from momentum.Analysis.strategy_registry import strategy_registry; print(strategy_registry.get_strategy('{strategy_id}'))"

# 步驟 6: 運行完整測試
python3 test_phase2_integration.py
```

### 9.2 關鍵檔案位置速查

| 功能 | 檔案路徑 |
|------|---------|
| **新增指標** | `momentum/Indicators/indicators/{name}.py` |
| **註冊指標** | `momentum/Indicators/indicator_engine.py` |
| **新增策略** | `momentum/Analysis/strategies/{name}_strategy.py` |
| **配置策略** | `config/strategies.yaml` |
| **測試** | `tests/test_{name}_strategy.py` |
| **ML 特徵** | `momentum/ML/feature_extractor.py` |

### 9.3 必須遵循的規範

1. **命名規範**: 小寫 + 底線 (例: `rsi_strategy`, 不是 `RsiStrategy`)
2. **函數簽名**:
   - 指標: `calculate_{name}(data: pd.Series, params: Dict) -> pd.Series`
   - 策略: `calculate_signals(kline_data, indicators, params) -> np.ndarray`
   - 驗證: `validate_params(params: Dict) -> List[str]`
3. **返回類型**:
   - 指標返回 `pd.Series`
   - 策略信號返回 `np.ndarray[bool]`
4. **日誌記錄**: 使用 `logger.debug/info/warning/error`
5. **錯誤處理**: 捕獲並重新拋出異常，添加上下文信息
6. **⚠️ Warmup 處理**: 
   - 在指標文檔中說明前 N 個值為 NaN
   - 測試時使用足夠長的數據（至少 `period * 5`）
   - API 層和 SignalDensityAnalyzer 已自動處理 warmup
   - 若新增複合指標（如 MACD），需確認 `chart_data_service.py` 的 warmup 計算邏輯
7. **數值顯示**: 使用截斷（truncate）而非四捨五入，以符合交易所標準

---

## 10. 總結

### 10.1 系統優勢

✅ **完全動態**: 無需修改核心代碼即可添加策略
✅ **類型安全**: Pydantic 自動驗證參數
✅ **可測試**: 每個組件都可以獨立測試
✅ **可擴展**: 支援 Optuna、XGBoost、LSTM 等多種用途
✅ **AI 友好**: 清晰的模板和執行流程

### 10.2 下一步

完成策略擴展後，你可以：
1. 運行 Optuna 優化找到最佳參數
2. 使用 XGBoost/LSTM 模型組合多個策略
3. 通過 API 端點查詢策略信息
4. 在前端 UI 中動態選擇策略和參數

---

**文檔版本**: v2.0 (混合式架構)
**最後更新**: 2025-12-04
**維護者**: AI Agent System

---

## 附錄 A: 架構決策記錄

本系統採用**混合式架構 (Hybrid Architecture)**，詳細決策分析見：`~/.claude/plans/jolly-splashing-harbor.md`

**核心理念**：
- AI 寫簡單的純函數（~40 行）
- 系統自動包裝成完整的類（獲得錯誤處理、性能監控等）
- 既有指標（如 EMA）保留類裝飾器模式，無需重構
- 新指標使用函數式模式

**設計原則**：
1. **AI 友好**：降低實作難度，提高開發效率
2. **無重複代碼**：所有系統功能由 BaseIndicator 統一提供
3. **向後兼容**：兩種模式可共存，不破壞既有代碼
4. **統一接口**：對外表現一致，通過 IndicatorEngine 調用

**參考範例**：
- 函數式版本：[momentum/Indicators/ema.py](momentum/Indicators/ema.py)
- 類裝飾器版本：[momentum/Indicators/ema_indicator.py](momentum/Indicators/ema_indicator.py)
- 包裝器實作：[momentum/Indicators/functional_wrapper.py](momentum/Indicators/functional_wrapper.py)


未來新增指標/策略的標準流程
情境 1: 您想新增一個指標（例如 MACD）
您只需要告訴我：
"新增 MACD 指標，參數包括 fast_period (12), slow_period (26), signal_period (9)"
我會自動：
參照 STRATEGY_EXTENSION_GUIDE.md Section 2.2 的函數式模板
創建 momentum/Indicators/macd.py（~40 行核心邏輯）
實作 calculate_macd() 和 validate_macd_params()
一行註冊：register_functional_indicator(...)
✅ 完成！自動獲得錯誤處理、性能監控、日誌記錄
情境 2: 您想新增一個策略（例如 MACD 金叉死叉）
您只需要告訴我：
"新增 MACD 金叉死叉策略，當 MACD 線上穿信號線時產生買入信號"
我會自動：
參照 STRATEGY_EXTENSION_GUIDE.md Section 3.2 的策略模板
創建 momentum/Analysis/strategies/macd_cross_strategy.py
實作 calculate_signals() 和 validate_params()
更新 config/strategies.yaml 配置
✅ 完成！自動整合到 Optuna、API 端點
關鍵優勢
項目	傳統方式	使用文檔後
溝通成本	您需詳細說明技術細節	您只需說明業務需求
我的理解	需要多次確認架構	直接參照統一模板
代碼一致性	可能有差異	100% 統一標準
測試驗證	需手動設計	文檔內建測試範例
實際使用範例
範例對話 1: 新增 Bollinger Bands
您：
"新增 Bollinger Bands 指標，參數：period (20), std_dev (2)"
我會執行：
# 參照 Section 2.2 模板創建 momentum/Indicators/bollinger_bands.py

def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0):
    # [核心邏輯 ~15 行]
    sma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower  # 返回三條線

def validate_bollinger_bands_params(period: int = 20, std_dev: float = 2.0):
    # [驗證邏輯 ~10 行]
    if period < 5: raise ValueError("...")
    if std_dev < 0.5: raise ValueError("...")
    return True

# 一行註冊
register_functional_indicator(...)
範例對話 2: 新增參數
您：
"在 three_line 策略中新增一個參數 min_gap，要求 mid_period 至少比 short_period 大 min_gap"
我會執行：
更新 config/strategies.yaml 添加 min_gap 參數定義
在 parameters 中添加約束關係
更新 validate_params() 添加業務邏輯驗證
✅ Optuna 自動識別新參數並採樣
文檔的核心價值
這份文檔就像一本「AI Agent 操作手冊」：
統一標準：確保我每次實作的代碼風格一致
降低溝通成本：您不需要解釋技術細節
提高效率：我直接套用模板，不需要思考架構
保證質量：模板內建最佳實踐（錯誤處理、日誌、測試）
您需要做什麼？
幾乎什麼都不用做！ 您只需要：
告訴我業務需求（例如："我要一個 RSI 超買超賣策略"）
告訴我參數和邏輯（例如："RSI > 70 算超買，< 30 算超賣"）
（可選）檢查我生成的代碼是否符合預期
我會：
參照文檔自動選擇正確的模板
生成符合標準的代碼
運行測試驗證
提供完整的實作報告
總結：這份文檔是專門為 AI Agent（像我）設計的「操作指南」，讓未來您只需要用自然語言描述需求，我就能按照統一標準快速實作，無需您擔心技術細節。就像您有一位完全理解系統架構的技術助理一樣！🎯