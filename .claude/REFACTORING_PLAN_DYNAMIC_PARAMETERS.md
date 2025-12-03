# 動態參數系統重構計劃

**Author**: Claude
**Date**: 2025-12-03
**目標**: 消除硬編碼，支援任意指標和策略的動態配置
**預計工作量**: 2-3 天（分 4 個 Phase）

---

## 1. 問題分析總結

### 1.1 硬編碼問題清單（按嚴重度）

| 位置 | 問題描述 | 嚴重度 | 影響 |
|------|---------|--------|------|
| `optuna_optimizer.py:615,625,829,839` | `if strategy_logic == 'three_line'` 硬編碼判斷 | 🔴 高 | 每新增策略需修改 4 處 |
| `signal_density_analyzer.py:163-168` | 策略邏輯硬編碼分支 | 🔴 高 | 新策略需添加方法 |
| `OptunaConfigPanel.tsx:44-66` | EMA 三參數硬編碼在 UI | 🔴 高 | 無法支援其他指標 |
| `strategy-test/page.tsx:109-173` | 選項列表硬編碼 | 🔴 高 | 新指標/策略需修改前端 |
| `StrategyLogicSelector.tsx:42-70` | 策略選項硬編碼 | 🟡 中 | UI 需手動更新 |
| `charts/page.tsx` | 策略判斷邏輯 | 🟡 中 | 圖表頁面也有硬編碼 |
| `ParameterRanges:136-149` | 默認值硬編碼 | 🟢 低 | 支援覆蓋，問題較小 |

**總計**: 需修改 **8+ 個文件**，**20+ 個位置**

---

## 2. 設計目標

### 2.1 功能目標
- ✅ **支援任意指標組合**: EMA, SMA, RSI, MACD, Bollinger Bands, ATR 等
- ✅ **支援任意策略邏輯**: 三線排列、雙線交叉、閾值突破、通道突破等
- ✅ **配置驅動**: 新增指標/策略只需修改配置文件，不需改代碼
- ✅ **動態 UI 生成**: 前端根據後端元數據自動生成參數輸入表單

### 2.2 技術目標
- ✅ **向後兼容**: 不破壞現有 `three_line` 策略
- ✅ **類型安全**: 使用 Pydantic (後端) 和 TypeScript (前端) 確保類型安全
- ✅ **高性能**: 優化邏輯不能變慢
- ✅ **易測試**: 每個策略可獨立測試

---

## 3. 核心設計

### 3.1 策略元數據系統

#### 後端數據結構

```python
# momentum/Optimization/strategy_metadata.py

from typing import List, Dict, Any, Callable, Optional
from pydantic import BaseModel
from enum import Enum

class ParameterType(str, Enum):
    INT = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"

class ParameterConstraint(BaseModel):
    """參數約束定義"""
    type: str  # 'less_than', 'greater_than', 'range_overlap', etc.
    target: str  # 目標參數名稱
    message: str  # 錯誤訊息

class ParameterDefinition(BaseModel):
    """參數定義"""
    name: str
    display_name: str  # UI 顯示名稱
    type: ParameterType
    default_value: Any
    # For int/float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    # For categorical
    choices: Optional[List[str]] = None
    # Validation
    constraints: List[ParameterConstraint] = []
    description: Optional[str] = None

class StrategyMetadata(BaseModel):
    """策略元數據"""
    strategy_id: str  # 'three_line', 'rsi_overbought', etc.
    display_name: str
    description: str
    category: str  # 'trend', 'momentum', 'volatility'

    # 需要的參數定義
    parameters: List[ParameterDefinition]

    # 支援的指標類型
    supported_indicators: List[str]  # ['ema', 'sma']

    # 支援的數據源
    supported_data_sources: List[str]  # ['close', 'volume']

    # 驗證函數（可選）
    validator_module: Optional[str] = None
    validator_function: Optional[str] = None

    # 計算函數
    calculator_module: str
    calculator_function: str

    # UI 相關
    icon: Optional[str] = "📈"
    recommended_for: Optional[str] = None
```

#### YAML 配置範例

```yaml
# config/strategies.yaml

strategies:
  three_line:
    display_name: "三線排列"
    description: "短期EMA > 中期EMA > 長期EMA，順勢交易"
    category: "trend"
    icon: "📈"

    supported_indicators: ["ema", "sma"]
    supported_data_sources: ["close", "open", "high", "low"]

    parameters:
      - name: "short_period"
        display_name: "短期週期"
        type: "int"
        default_value: 7
        min_value: 5
        max_value: 15
        step: 1
        description: "短期移動平均週期"
        constraints:
          - type: "less_than"
            target: "mid_period"
            message: "短期週期必須小於中期週期"

      - name: "mid_period"
        display_name: "中期週期"
        type: "int"
        default_value: 25
        min_value: 20
        max_value: 40
        step: 1
        constraints:
          - type: "less_than"
            target: "long_period"
            message: "中期週期必須小於長期週期"

      - name: "long_period"
        display_name: "長期週期"
        type: "int"
        default_value: 70
        min_value: 50
        max_value: 100
        step: 1

    calculator_module: "momentum.Analysis.strategies.three_line_strategy"
    calculator_function: "calculate_signals"

    validator_module: "momentum.Analysis.strategies.three_line_strategy"
    validator_function: "validate_params"

  rsi_overbought:
    display_name: "RSI 超買超賣"
    description: "RSI 指標判斷超買超賣區域"
    category: "momentum"
    icon: "📊"

    supported_indicators: ["rsi"]
    supported_data_sources: ["close"]

    parameters:
      - name: "rsi_period"
        display_name: "RSI 週期"
        type: "int"
        default_value: 14
        min_value: 7
        max_value: 21
        step: 1

      - name: "overbought_threshold"
        display_name: "超買閾值"
        type: "float"
        default_value: 70.0
        min_value: 65.0
        max_value: 85.0
        step: 0.5
        constraints:
          - type: "greater_than"
            target: "oversold_threshold"
            message: "超買閾值必須大於超賣閾值"

      - name: "oversold_threshold"
        display_name: "超賣閾值"
        type: "float"
        default_value: 30.0
        min_value: 15.0
        max_value: 35.0
        step: 0.5

    calculator_module: "momentum.Analysis.strategies.rsi_strategy"
    calculator_function: "calculate_signals"
```

---

### 3.2 策略註冊系統

```python
# momentum/Analysis/strategy_registry.py

from typing import Dict, Type, Callable
import yaml
from pathlib import Path

class StrategyRegistry:
    """策略註冊中心（單例模式）"""

    _instance = None
    _strategies: Dict[str, StrategyMetadata] = {}
    _calculators: Dict[str, Callable] = {}
    _validators: Dict[str, Callable] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._strategies:
            self._load_from_yaml()

    def _load_from_yaml(self):
        """從 YAML 載入策略定義"""
        config_path = Path(__file__).parent.parent.parent / "config" / "strategies.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        for strategy_id, config in data['strategies'].items():
            metadata = StrategyMetadata(strategy_id=strategy_id, **config)
            self._strategies[strategy_id] = metadata

            # 動態載入 calculator 函數
            calculator = self._import_function(
                metadata.calculator_module,
                metadata.calculator_function
            )
            self._calculators[strategy_id] = calculator

            # 動態載入 validator 函數（如果有）
            if metadata.validator_module:
                validator = self._import_function(
                    metadata.validator_module,
                    metadata.validator_function
                )
                self._validators[strategy_id] = validator

    def _import_function(self, module_path: str, function_name: str) -> Callable:
        """動態導入函數"""
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, function_name)

    def get_strategy(self, strategy_id: str) -> StrategyMetadata:
        """獲取策略元數據"""
        if strategy_id not in self._strategies:
            raise ValueError(f"Strategy '{strategy_id}' not found")
        return self._strategies[strategy_id]

    def list_strategies(self) -> List[StrategyMetadata]:
        """列出所有策略"""
        return list(self._strategies.values())

    def get_calculator(self, strategy_id: str) -> Callable:
        """獲取策略計算函數"""
        return self._calculators[strategy_id]

    def get_validator(self, strategy_id: str) -> Optional[Callable]:
        """獲取策略驗證函數"""
        return self._validators.get(strategy_id)

    def validate_parameters(self, strategy_id: str, params: Dict[str, Any]) -> List[str]:
        """驗證參數（返回錯誤訊息列表）"""
        metadata = self.get_strategy(strategy_id)
        errors = []

        # 1. 基礎驗證（類型、範圍）
        for param_def in metadata.parameters:
            if param_def.name not in params:
                errors.append(f"缺少必要參數: {param_def.display_name}")
                continue

            value = params[param_def.name]

            # 類型驗證
            if param_def.type == ParameterType.INT and not isinstance(value, int):
                errors.append(f"{param_def.display_name} 必須是整數")
            elif param_def.type == ParameterType.FLOAT and not isinstance(value, (int, float)):
                errors.append(f"{param_def.display_name} 必須是數字")

            # 範圍驗證
            if param_def.min_value is not None and value < param_def.min_value:
                errors.append(f"{param_def.display_name} 不能小於 {param_def.min_value}")
            if param_def.max_value is not None and value > param_def.max_value:
                errors.append(f"{param_def.display_name} 不能大於 {param_def.max_value}")

        # 2. 約束驗證（參數間關係）
        for param_def in metadata.parameters:
            if param_def.name not in params:
                continue

            for constraint in param_def.constraints:
                if not self._check_constraint(params, param_def.name, constraint):
                    errors.append(constraint.message)

        # 3. 自定義驗證函數
        validator = self.get_validator(strategy_id)
        if validator:
            custom_errors = validator(params)
            if custom_errors:
                errors.extend(custom_errors)

        return errors

    def _check_constraint(self, params: Dict, param_name: str, constraint: ParameterConstraint) -> bool:
        """檢查單個約束"""
        value = params[param_name]
        target_value = params.get(constraint.target)

        if target_value is None:
            return True

        if constraint.type == "less_than":
            return value < target_value
        elif constraint.type == "greater_than":
            return value > target_value
        elif constraint.type == "less_than_or_equal":
            return value <= target_value
        # ... 更多約束類型

        return True

# 單例實例
strategy_registry = StrategyRegistry()
```

---

### 3.3 重構後的 OptunaOptimizer

```python
# momentum/Optimization/optuna_optimizer.py (重構後)

class OptunaOptimizer:
    def __init__(self, parameter_ranges: ParameterRanges = None):
        self.parameter_ranges = parameter_ranges or ParameterRanges()
        self.strategy_registry = strategy_registry

    def _objective_function(self, trial: optuna.Trial) -> float:
        """目標函數（完全動態化）"""

        # 1. 採樣固定參數
        data_source = trial.suggest_categorical(
            'data_source',
            self.parameter_ranges.data_sources
        )
        strategy_logic = trial.suggest_categorical(
            'strategy_logic',
            self.parameter_ranges.strategy_logics
        )
        indicator_type = trial.suggest_categorical(
            'indicator_type',
            ['ema', 'sma']  # 可從配置讀取
        )

        # 2. 動態採樣策略參數
        metadata = self.strategy_registry.get_strategy(strategy_logic)
        params = {}

        for param_def in metadata.parameters:
            if param_def.type == ParameterType.INT:
                params[param_def.name] = trial.suggest_int(
                    param_def.name,
                    param_def.min_value,
                    param_def.max_value,
                    step=param_def.step or 1
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

        # 3. 參數驗證
        validation_errors = self.strategy_registry.validate_parameters(
            strategy_logic,
            params
        )
        if validation_errors:
            logger.warning(f"Trial {trial.number} 參數驗證失敗: {validation_errors}")
            raise optuna.TrialPruned()

        # 4. 構建 StrategyConfig
        strategy_config = StrategyConfig(
            data_source=data_source,
            indicator_type=indicator_type,
            strategy_logic=strategy_logic,
            params=params
        )

        # 5. 計算目標值（與之前相同）
        try:
            response = self.signal_analyzer.calculate_signal_density(
                positive_cases=self.positive_cases,
                negative_cases=self.negative_cases,
                training_window=self.training_window,
                strategy_config=strategy_config
            )

            return response.separation
        except Exception as e:
            logger.error(f"Trial {trial.number} 執行失敗: {e}")
            raise optuna.TrialPruned()
```

**關鍵改進**:
- ❌ 移除硬編碼的 `if strategy_logic == 'three_line'`
- ✅ 根據策略元數據動態採樣參數
- ✅ 使用統一的驗證框架
- ✅ 支援任意策略，無需修改代碼

---

### 3.4 重構後的 SignalDensityAnalyzer

```python
# momentum/Analysis/signal_density_analyzer.py (重構後)

class SignalDensityAnalyzer:
    def __init__(self):
        self.strategy_registry = strategy_registry
        self.indicator_engine = IndicatorEngine()

    def calculate_strategy_signals(
        self,
        kline_data: pd.DataFrame,
        strategy_config: StrategyConfig
    ) -> np.ndarray:
        """計算策略信號（完全動態化）"""

        # 1. 獲取策略計算函數
        calculator = self.strategy_registry.get_calculator(
            strategy_config.strategy_logic
        )

        # 2. 計算指標值（根據策略需要的參數）
        metadata = self.strategy_registry.get_strategy(
            strategy_config.strategy_logic
        )

        indicators = {}
        for param_def in metadata.parameters:
            param_name = param_def.name
            param_value = strategy_config.params[param_name]

            # 如果是週期參數，計算指標
            if 'period' in param_name.lower():
                indicator_key = param_name  # e.g., 'short_period'
                indicators[indicator_key] = self.indicator_engine.calculate(
                    indicator_type=strategy_config.indicator_type,
                    data_source=kline_data[strategy_config.data_source],
                    period=param_value
                )

        # 3. 調用策略計算函數
        signals = calculator(
            kline_data=kline_data,
            indicators=indicators,
            params=strategy_config.params
        )

        return signals
```

**策略實現範例**:

```python
# momentum/Analysis/strategies/three_line_strategy.py

def calculate_signals(
    kline_data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> np.ndarray:
    """三線排列策略信號計算"""

    short_ema = indicators['short_period']
    mid_ema = indicators['mid_period']
    long_ema = indicators['long_period']

    # 三線排列: short > mid > long
    signals = (short_ema > mid_ema) & (mid_ema > long_ema)

    return signals.values

def validate_params(params: Dict[str, Any]) -> List[str]:
    """自定義參數驗證"""
    errors = []

    # 可選：額外的業務邏輯驗證
    # 例如：short_period 與 mid_period 的差距不能太小
    if params['mid_period'] - params['short_period'] < 5:
        errors.append("中期與短期週期差距至少需要 5")

    return errors
```

---

## 4. 前端動態化

### 4.1 API 端點：獲取策略元數據

```python
# api/routes/optimization.py

@router.get("/strategies", response_model=List[StrategyMetadata])
async def list_strategies():
    """列出所有可用的策略"""
    strategies = strategy_registry.list_strategies()
    return strategies

@router.get("/strategies/{strategy_id}", response_model=StrategyMetadata)
async def get_strategy_metadata(strategy_id: str):
    """獲取單個策略的元數據"""
    try:
        return strategy_registry.get_strategy(strategy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### 4.2 前端類型定義

```typescript
// frontend/src/types/strategy-metadata.ts

export enum ParameterType {
  INT = 'int',
  FLOAT = 'float',
  CATEGORICAL = 'categorical'
}

export interface ParameterConstraint {
  type: string
  target: string
  message: string
}

export interface ParameterDefinition {
  name: string
  display_name: string
  type: ParameterType
  default_value: any
  min_value?: number
  max_value?: number
  step?: number
  choices?: string[]
  constraints: ParameterConstraint[]
  description?: string
}

export interface StrategyMetadata {
  strategy_id: string
  display_name: string
  description: string
  category: string
  parameters: ParameterDefinition[]
  supported_indicators: string[]
  supported_data_sources: string[]
  icon?: string
  recommended_for?: string
}
```

### 4.3 動態參數面板組件

```typescript
// frontend/src/components/strategy-test/DynamicParameterPanel.tsx

import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface DynamicParameterPanelProps {
  strategyId: string
  values: Record<string, any>
  onChange: (values: Record<string, any>) => void
  disabled?: boolean
}

export function DynamicParameterPanel({
  strategyId,
  values,
  onChange,
  disabled = false
}: DynamicParameterPanelProps) {
  const [metadata, setMetadata] = useState<StrategyMetadata | null>(null)
  const [errors, setErrors] = useState<string[]>([])

  // 1. 載入策略元數據
  useEffect(() => {
    fetch(`/api/v1/optimization/strategies/${strategyId}`)
      .then(res => res.json())
      .then(data => setMetadata(data))
      .catch(err => console.error('Failed to load strategy metadata:', err))
  }, [strategyId])

  // 2. 驗證參數
  useEffect(() => {
    if (!metadata) return

    const newErrors: string[] = []

    for (const paramDef of metadata.parameters) {
      const value = values[paramDef.name]

      // 範圍驗證
      if (paramDef.min_value !== undefined && value < paramDef.min_value) {
        newErrors.push(`${paramDef.display_name} 不能小於 ${paramDef.min_value}`)
      }
      if (paramDef.max_value !== undefined && value > paramDef.max_value) {
        newErrors.push(`${paramDef.display_name} 不能大於 ${paramDef.max_value}`)
      }

      // 約束驗證
      for (const constraint of paramDef.constraints) {
        const targetValue = values[constraint.target]
        if (targetValue === undefined) continue

        if (constraint.type === 'less_than' && value >= targetValue) {
          newErrors.push(constraint.message)
        } else if (constraint.type === 'greater_than' && value <= targetValue) {
          newErrors.push(constraint.message)
        }
      }
    }

    setErrors(newErrors)
  }, [metadata, values])

  if (!metadata) {
    return <div>Loading...</div>
  }

  return (
    <div className="space-y-4">
      {/* 參數輸入 */}
      <div className="grid grid-cols-2 gap-4">
        {metadata.parameters.map(paramDef => (
          <div key={paramDef.name} className="space-y-2">
            <Label htmlFor={paramDef.name}>
              {paramDef.display_name}
              {paramDef.description && (
                <span className="text-xs text-gray-500 ml-2">
                  ({paramDef.description})
                </span>
              )}
            </Label>

            {paramDef.type === ParameterType.INT || paramDef.type === ParameterType.FLOAT ? (
              <Input
                id={paramDef.name}
                type="number"
                value={values[paramDef.name] ?? paramDef.default_value}
                onChange={e => {
                  const value = paramDef.type === ParameterType.INT
                    ? parseInt(e.target.value)
                    : parseFloat(e.target.value)
                  onChange({ ...values, [paramDef.name]: value })
                }}
                min={paramDef.min_value}
                max={paramDef.max_value}
                step={paramDef.step || 1}
                disabled={disabled}
              />
            ) : null}

            {/* TODO: 支援 categorical 類型 */}
          </div>
        ))}
      </div>

      {/* 驗證錯誤 */}
      {errors.length > 0 && (
        <Alert variant="destructive">
          <AlertDescription>
            <ul className="list-disc pl-4 space-y-1">
              {errors.map((error, idx) => (
                <li key={idx}>{error}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
```

### 4.4 更新 OptunaConfigPanel

```typescript
// frontend/src/components/strategy-test/OptunaConfigPanel.tsx (重構後)

import { DynamicParameterPanel } from './DynamicParameterPanel'

export interface OptunaConfig {
  enabled: boolean
  n_trials: number
  timeout: number
  random_seed: number
  enable_pruning: boolean
  strategy_id: string  // 替代硬編碼的 EMA 參數
  parameters: Record<string, any>  // 動態參數
}

export function OptunaConfigPanel({
  config,
  onChange,
  disabled = false
}: OptunaConfigPanelProps) {
  // ... 基礎設定 UI (n_trials, timeout, etc.)

  return (
    <div className="space-y-6">
      {/* 基礎設定區塊 */}
      <div>
        <h3>基礎設定</h3>
        {/* Switch, NumberInput 等 */}
      </div>

      {/* 動態參數配置區塊 */}
      <div>
        <h3>參數搜索空間</h3>
        <DynamicParameterPanel
          strategyId={config.strategy_id}
          values={config.parameters}
          onChange={newParams => {
            onChange({ ...config, parameters: newParams })
          }}
          disabled={disabled}
        />
      </div>
    </div>
  )
}
```

---

## 5. 實施計劃

### Phase 1: 後端基礎設施（優先級最高）

**時間**: 4-6 小時

**任務清單**:
- [ ] 創建 `momentum/Optimization/strategy_metadata.py`
  - 定義 `ParameterType`, `ParameterConstraint`, `ParameterDefinition`, `StrategyMetadata`
- [ ] 創建 `momentum/Analysis/strategy_registry.py`
  - 實現 `StrategyRegistry` 單例類
  - 實現 YAML 載入邏輯
  - 實現參數驗證框架
- [ ] 創建 `config/strategies.yaml`
  - 定義 `three_line` 策略元數據（遷移現有邏輯）
- [ ] 創建 `momentum/Analysis/strategies/three_line_strategy.py`
  - 提取現有三線排列計算邏輯到獨立函數
  - 實現 `calculate_signals()` 和 `validate_params()`
- [ ] 測試策略註冊系統
  ```bash
  pytest tests/optimization/test_strategy_registry.py -v
  ```

**驗收標準**:
- ✅ `strategy_registry.list_strategies()` 返回 `three_line` 元數據
- ✅ `strategy_registry.validate_parameters()` 正確驗證參數
- ✅ `strategy_registry.get_calculator()` 返回可執行的函數

---

### Phase 2: 後端重構（核心邏輯改動）

**時間**: 6-8 小時

**任務清單**:
- [ ] 重構 `momentum/Optimization/optuna_optimizer.py`
  - 修改 `_objective_function()` 使用動態參數採樣
  - 移除 4 處硬編碼 `if strategy_logic == 'three_line'`
  - 修改多目標函數 `_objective_function_multi()`
- [ ] 重構 `momentum/Analysis/signal_density_analyzer.py`
  - 修改 `calculate_strategy_signals()` 使用策略註冊系統
  - 移除硬編碼的策略分支判斷
- [ ] 添加 API 端點 `api/routes/optimization.py`
  - `GET /api/v1/optimization/strategies` - 列出所有策略
  - `GET /api/v1/optimization/strategies/{id}` - 獲取策略元數據
- [ ] 更新 `api/routes/optimization.py` 的 `CreateOptimizationTaskRequest`
  - 確保 `parameter_ranges` 可以接收動態參數
- [ ] 向後兼容測試
  ```bash
  pytest tests/optimization/ -v -k "three_line"
  ```

**驗收標準**:
- ✅ Optuna 優化可以運行（使用 three_line 策略）
- ✅ 結果與重構前一致
- ✅ 無硬編碼策略判斷邏輯
- ✅ 所有現有測試通過

---

### Phase 3: 前端動態化

**時間**: 4-6 小時

**任務清單**:
- [ ] 創建 `frontend/src/types/strategy-metadata.ts`
  - 定義 TypeScript 類型（與後端對應）
- [ ] 創建 `frontend/src/components/strategy-test/DynamicParameterPanel.tsx`
  - 實現動態參數輸入 UI
  - 實現前端驗證邏輯
- [ ] 重構 `frontend/src/components/strategy-test/OptunaConfigPanel.tsx`
  - 移除硬編碼的 EMA 參數
  - 整合 `DynamicParameterPanel`
- [ ] 更新 `frontend/src/app/strategy-test/page.tsx`
  - 從 API 載入策略列表（替代硬編碼的 `STRATEGY_OPTIONS`）
  - 動態渲染策略選擇器
- [ ] 可選：重構 `frontend/src/components/strategy/StrategyLogicSelector.tsx`
  - 從 API 載入策略選項

**驗收標準**:
- ✅ 策略測試頁面可以正常運行
- ✅ 參數面板根據選擇的策略動態生成
- ✅ 驗證邏輯正常工作
- ✅ 可以成功創建優化任務

---

### Phase 4: 擴展與測試

**時間**: 4-6 小時

**任務清單**:
- [ ] 添加第二個策略範例（如 `rsi_overbought`）
  - 創建 `config/strategies.yaml` 定義
  - 創建 `momentum/Analysis/strategies/rsi_strategy.py`
  - 確保系統支援非 EMA 指標
- [ ] 創建完整的測試套件
  - 策略註冊測試
  - 參數驗證測試
  - 前端動態 UI 測試
- [ ] 性能測試
  - 對比重構前後的 Optuna 優化速度
  - 確保無性能退化
- [ ] 文檔更新
  - 更新開發者文檔（如何添加新策略）
  - 更新用戶文檔（如何使用動態參數）

**驗收標準**:
- ✅ 至少支援 2 種完全不同的策略（EMA + RSI）
- ✅ 新增策略無需修改核心代碼
- ✅ 測試覆蓋率 > 80%
- ✅ 性能無明顯退化（< 5%）

---

## 6. 遷移策略

### 6.1 向後兼容性保證

**策略**:
1. 保留 `ParameterRanges` 的默認值（兼容舊 API）
2. 舊的 `three_line` 策略 ID 不變
3. API 端點保持向後兼容（`parameter_ranges` 繼續支援）

**遷移路徑**:
```python
# 舊代碼（仍然可以工作）
parameter_ranges = ParameterRanges(
    ema_short_range=(5, 15),
    ema_mid_range=(20, 40),
    ema_long_range=(50, 100)
)

# 新代碼（推薦）
# 自動從 strategies.yaml 讀取，無需指定範圍
```

### 6.2 數據遷移

**不需要**數據遷移！因為：
- 策略 ID (`three_line`) 不變
- 參數名稱可以保持兼容（`ema_short` → `short_period` 透過映射層）

---

## 7. 測試策略

### 7.1 單元測試

```bash
# 測試策略註冊系統
pytest tests/optimization/test_strategy_registry.py -v

# 測試參數驗證
pytest tests/optimization/test_parameter_validation.py -v

# 測試動態採樣
pytest tests/optimization/test_optuna_dynamic.py -v
```

### 7.2 集成測試

```bash
# 端到端測試（使用真實數據）
pytest tests/optimization/test_optimization_integration.py -v -k "three_line"

# 測試新策略（RSI）
pytest tests/optimization/test_optimization_integration.py -v -k "rsi"
```

### 7.3 回歸測試

```bash
# 確保 three_line 結果與重構前一致
pytest tests/optimization/test_regression.py -v
```

### 7.4 手動驗證

**前端測試**:
1. 訪問 `http://localhost:3000/strategy-test`
2. 選擇策略 → 參數面板應動態生成
3. 輸入無效參數 → 應顯示驗證錯誤
4. 創建優化任務 → 應成功啟動
5. 查看結果頁面 → 應正常顯示

---

## 8. 風險評估與緩解

| 風險 | 嚴重度 | 緩解措施 |
|------|--------|---------|
| 重構破壞現有功能 | 🔴 高 | 保留完整的回歸測試套件 |
| 性能退化 | 🟡 中 | 性能基準測試，動態導入緩存 |
| 配置文件維護複雜 | 🟡 中 | 提供 schema 驗證和文檔 |
| 前端動態 UI 複雜度 | 🟡 中 | 分階段實現，先簡單後複雜 |
| 向後兼容性問題 | 🟢 低 | 保留舊 API，提供適配層 |

---

## 9. 關鍵文件清單

### 需要創建的文件

**後端** (7 個文件):
1. `momentum/Optimization/strategy_metadata.py` (新增)
2. `momentum/Analysis/strategy_registry.py` (新增)
3. `config/strategies.yaml` (新增)
4. `momentum/Analysis/strategies/__init__.py` (新增)
5. `momentum/Analysis/strategies/three_line_strategy.py` (新增)
6. `momentum/Analysis/strategies/rsi_strategy.py` (新增，Phase 4)
7. `tests/optimization/test_strategy_registry.py` (新增)

**前端** (3 個文件):
1. `frontend/src/types/strategy-metadata.ts` (新增)
2. `frontend/src/components/strategy-test/DynamicParameterPanel.tsx` (新增)
3. `frontend/src/hooks/useStrategyMetadata.ts` (新增，可選)

### 需要修改的文件

**後端** (3 個文件):
1. `momentum/Optimization/optuna_optimizer.py` (重構)
2. `momentum/Analysis/signal_density_analyzer.py` (重構)
3. `api/routes/optimization.py` (新增 API 端點)

**前端** (2 個文件):
1. `frontend/src/components/strategy-test/OptunaConfigPanel.tsx` (重構)
2. `frontend/src/app/strategy-test/page.tsx` (移除硬編碼選項)

**總計**: 創建 10 個新文件，修改 5 個現有文件

---

## 10. 成功標準

### 功能標準
- ✅ 支援至少 2 種完全不同的策略（EMA + RSI）
- ✅ 新增策略只需修改配置文件和策略實現，無需改核心代碼
- ✅ 前端參數面板根據策略動態生成
- ✅ 向後兼容，現有 three_line 策略正常工作

### 質量標準
- ✅ 測試覆蓋率 > 80%
- ✅ 所有回歸測試通過
- ✅ 性能退化 < 5%
- ✅ 無 ESLint/TypeScript 錯誤

### 文檔標準
- ✅ 開發者文檔：如何添加新策略
- ✅ 配置文件有完整的 schema 和範例
- ✅ API 文檔更新

---

## 11. 下一步行動

**立即開始** (推薦順序):

1. ✅ **創建這份計劃文檔** ← 你在這裡
2. 🚀 **Phase 1: 後端基礎設施** (4-6 小時)
   - 創建 `strategy_metadata.py`
   - 創建 `strategy_registry.py`
   - 創建 `config/strategies.yaml`
3. 🚀 **Phase 2: 後端重構** (6-8 小時)
   - 重構 `optuna_optimizer.py`
   - 重構 `signal_density_analyzer.py`
4. 🚀 **Phase 3: 前端動態化** (4-6 小時)
   - 創建 `DynamicParameterPanel`
5. 🚀 **Phase 4: 擴展與測試** (4-6 小時)
   - 添加 RSI 策略範例

**預計總時間**: 2-3 天

---

## 附錄 A: 策略添加範例

假設要添加「MACD 交叉策略」，步驟如下：

### 步驟 1: 定義策略元數據

```yaml
# config/strategies.yaml

strategies:
  # ... 現有策略 ...

  macd_cross:
    display_name: "MACD 交叉"
    description: "MACD 線與信號線交叉判斷買賣點"
    category: "momentum"
    icon: "📊"

    supported_indicators: ["macd"]
    supported_data_sources: ["close"]

    parameters:
      - name: "fast_period"
        display_name: "快線週期"
        type: "int"
        default_value: 12
        min_value: 8
        max_value: 20
        step: 1

      - name: "slow_period"
        display_name: "慢線週期"
        type: "int"
        default_value: 26
        min_value: 20
        max_value: 40
        step: 1
        constraints:
          - type: "greater_than"
            target: "fast_period"
            message: "慢線週期必須大於快線週期"

      - name: "signal_period"
        display_name: "信號線週期"
        type: "int"
        default_value: 9
        min_value: 5
        max_value: 15
        step: 1

    calculator_module: "momentum.Analysis.strategies.macd_strategy"
    calculator_function: "calculate_signals"
```

### 步驟 2: 實現策略邏輯

```python
# momentum/Analysis/strategies/macd_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_signals(
    kline_data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> np.ndarray:
    """MACD 交叉策略信號計算"""

    # 計算 MACD
    close = kline_data['close']

    fast_ema = close.ewm(span=params['fast_period'], adjust=False).mean()
    slow_ema = close.ewm(span=params['slow_period'], adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=params['signal_period'], adjust=False).mean()

    # 金叉：MACD 線上穿信號線
    golden_cross = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))

    return golden_cross.values

def validate_params(params: Dict[str, Any]) -> List[str]:
    """自定義參數驗證"""
    errors = []

    # 可選：業務邏輯驗證
    if params['slow_period'] - params['fast_period'] < 8:
        errors.append("慢線與快線週期差距至少需要 8")

    return errors
```

### 步驟 3: 測試

```bash
# 重啟服務，自動載入新策略
python -m uvicorn api.main:app --reload

# 測試 API
curl http://localhost:8000/api/v1/optimization/strategies/macd_cross

# 前端測試
# 訪問 http://localhost:3000/strategy-test
# 選擇 "MACD 交叉" 策略
# 應該看到三個參數輸入框：快線週期、慢線週期、信號線週期
```

**完成！無需修改任何核心代碼。**

---

## 結論

這個重構計劃將徹底消除硬編碼問題，使系統支援任意指標和策略的動態配置。通過分 4 個 Phase 實施，可以保證向後兼容性，並逐步驗證每個階段的正確性。

**關鍵優勢**:
- 🚀 **可擴展性**: 新增策略只需配置文件 + 策略實現函數
- 🔒 **類型安全**: Pydantic + TypeScript 確保類型正確
- 🧪 **可測試性**: 每個策略可獨立測試
- 📚 **可維護性**: 配置與代碼分離，易於理解和修改
- ⚡ **高性能**: 動態導入緩存，性能不受影響

**預計收益**:
- 新增策略時間：從 **2-3 小時** 降低到 **15-30 分鐘**
- 代碼耦合度：從 **高耦合** 降低到 **低耦合**
- 測試複雜度：從 **集成測試** 改為 **單元測試優先**
