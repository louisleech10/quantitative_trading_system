# 架構擴充性 - 快速參考指南

> **3 個問題，3 個解決方案**  
> **版本**: 2.0 | **日期**: 2026-01-11

## ✅ 問題 1: 數據源擴充（Glassnode, 台股, 美股）

### 💡 答案：完全支援！

**使用 [`DataSourceRegistry`](momentum/FeatureEngineering/data_source_registry.py)**

```python
from momentum.FeatureEngineering.data_source_registry import DataSourceRegistry, DataSourceCategory

# 註冊新數據源（只需一次）
registry = DataSourceRegistry()

# 範例 1: Glassnode 鏈上數據
registry.register(
    name='nvt_ratio',
    category=DataSourceCategory.ONCHAIN,
    description='Network Value to Transactions Ratio',
    column_name='nvt_ratio',
    value_range=(0, 200)
)

# 範例 2: 台股融資融券
registry.register(
    name='margin_balance',
    category=DataSourceCategory.MARGIN,
    description='融資餘額',
    column_name='margin_balance'
)

# 範例 3: 美股期權數據
registry.register(
    name='put_call_ratio',
    category=DataSourceCategory.OPTION,
    description='Put/Call Ratio',
    column_name='put_call_ratio'
)
```

**之後直接使用**：
```python
# Optuna 優化
strategy_params = StrategyParams(
    strategy_type='ema_three_line',
    data_source='nvt_ratio',  # ✅ 自動支援
    params={...}
)

# Feature Engineering
features_df, feature_names = extractor.extract_features_from_strategy(
    df=kline_data,
    strategy_params=strategy_params
)
# ✅ 自動使用 'nvt_ratio' 計算 EMA
```

---

## ✅ 問題 2: 策略擴充（MACD, RSI, Bollinger Bands）

### 💡 答案：完全支援！

**使用 [`StrategyRegistry`](momentum/FeatureEngineering/strategy_registry.py)**

### Step 1: 實作策略提取器

```python
from momentum.FeatureEngineering.strategy_registry import BaseStrategyExtractor

class MACDExtractor(BaseStrategyExtractor):
    """MACD 策略特徵提取器"""
    
    def extract(self, df, params, data_source='close'):
        """提取 MACD 特徵"""
        features_df = df.copy()
        feature_names = []
        
        fast = params['fast_period']
        slow = params['slow_period']
        signal = params['signal_period']
        
        # 計算 MACD
        ema_fast = features_df[data_source].ewm(span=fast).mean()
        ema_slow = features_df[data_source].ewm(span=slow).mean()
        
        features_df['macd'] = ema_fast - ema_slow
        features_df['macd_signal'] = features_df['macd'].ewm(span=signal).mean()
        features_df['macd_histogram'] = features_df['macd'] - features_df['macd_signal']
        
        feature_names.extend(['macd', 'macd_signal', 'macd_histogram'])
        
        return features_df, feature_names
    
    def validate_params(self, params):
        """驗證參數"""
        if params['fast_period'] >= params['slow_period']:
            raise ValueError("fast_period 必須小於 slow_period")
```

### Step 2: 註冊策略

```python
from momentum.FeatureEngineering.strategy_registry import StrategyRegistry

registry = StrategyRegistry()

registry.register_strategy(
    name='macd',
    description='Moving Average Convergence Divergence',
    required_params=['fast_period', 'slow_period', 'signal_period'],
    extractor=MACDExtractor()
)
```

### Step 3: 使用新策略

```python
# Optuna 優化
strategy_params = StrategyParams(
    strategy_type='macd',  # ✅ 新策略自動支援
    data_source='close',
    params={
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9
    }
)

# Feature Engineering
features_df, feature_names = extractor.extract_features_from_strategy(
    df=kline_data,
    strategy_params=strategy_params
)
# ✅ 自動調用 MACDExtractor.extract()
```

---

## ✅ 問題 3: XGBoost 參數繼承

### 💡 答案：完全從 Optuna 繼承！

**使用 [`MLPipelineConfig`](momentum/FeatureEngineering/ml_pipeline_config.py)**

### 參數繼承鏈

```
Optuna Best Trial (data_source='close', ema_short=5, ...)
    ↓
StrategyConfig (完全繼承)
    ↓
FeatureEngineeringConfig (完全繼承)
    ↓
Feature Extraction (使用相同參數)
    ↓
XGBoost Training
```

### 完整流程

```python
from momentum.FeatureEngineering.ml_pipeline_config import MLPipelineConfig
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

# ==================== STEP 1: Optuna 優化完成 ====================
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=200)

best_trial = study.best_trial

# ==================== STEP 2: 建立 Pipeline 配置 ====================
pipeline_config = MLPipelineConfig.from_optuna_trial(
    trial=best_trial,
    strategy_type='ema_three_line',
    use_xgboost_tuning=False  # 模式 1: 使用預設參數
)

# 保存配置（完全可重現）
pipeline_config.to_json('data/pipeline_config.json')

# ==================== STEP 3: 提取特徵 ====================
feature_extractor = FeatureExtractor()

strategy_params = StrategyParams(
    strategy_type=pipeline_config.strategy_config.strategy_type,
    data_source=pipeline_config.strategy_config.data_source,  # ← 從 Optuna 繼承
    params=pipeline_config.strategy_config.strategy_params     # ← 從 Optuna 繼承
)

features_df, feature_names = feature_extractor.extract_features_from_strategy(
    df=kline_data,
    strategy_params=strategy_params
)

# ==================== STEP 4: 訓練 XGBoost ====================
xgb_analyzer = XGBoostAnalyzer(
    params=pipeline_config.xgboost_config.params  # ← 從 Pipeline 繼承
)

performance = xgb_analyzer.train_model(X=features_df[feature_names], y=labels)

print(f"✅ 訓練完成: AUC = {performance.cv_auc_mean:.4f}")
```

### XGBoost 兩種配置模式

#### 模式 1: 使用預設參數（快速迭代）

```python
pipeline_config = MLPipelineConfig.from_optuna_trial(
    trial=best_trial,
    strategy_type='ema_three_line',
    use_xgboost_tuning=False  # ← 快速模式
)
```

**優點**：快速訓練，無需二次優化  
**適用**：快速驗證策略有效性

#### 模式 2: 二次 Optuna 優化（最終模型）

```python
pipeline_config = MLPipelineConfig.from_optuna_trial(
    trial=best_trial,
    strategy_type='ema_three_line',
    use_xgboost_tuning=True,  # ← 精細模式
    optuna_n_trials=50
)

# 需要手動執行二次優化
def xgboost_objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        ...
    }
    xgb_analyzer = XGBoostAnalyzer(params=params)
    performance = xgb_analyzer.train_model(X, y)
    return performance.cv_auc_mean

xgb_study = optuna.create_study(direction='maximize')
xgb_study.optimize(xgboost_objective, n_trials=50)

# 更新配置
pipeline_config.xgboost_config.params = xgb_study.best_params
```

**優點**：針對當前策略/特徵優化，可能提升 AUC +0.02-0.05  
**適用**：最終生產模型

---

## 📦 新建檔案

1. **[`data_source_registry.py`](momentum/FeatureEngineering/data_source_registry.py)**  
   數據源註冊系統（支援 Glassnode、台股、美股擴充）

2. **[`strategy_registry.py`](momentum/FeatureEngineering/strategy_registry.py)**  
   策略註冊系統（支援 MACD、RSI、Bollinger Bands 擴充）

3. **[`ml_pipeline_config.py`](momentum/FeatureEngineering/ml_pipeline_config.py)**  
   ML Pipeline 配置系統（參數繼承鏈管理）

---

## 🔄 測試驗證

```bash
# 測試數據源註冊系統
python momentum/FeatureEngineering/data_source_registry.py
# ✅ 輸出: 所有數據源: ['close', 'open', ...], 註冊 Glassnode 後: ['nvt_ratio', ...]

# 測試策略註冊系統
python momentum/FeatureEngineering/strategy_registry.py
# ✅ 輸出: 預設策略: ['ema_three_line'], 註冊後: ['macd', 'rsi', ...]

# 測試 Pipeline 配置系統
python momentum/FeatureEngineering/ml_pipeline_config.py
# ✅ 輸出: Pipeline 配置、參數繼承鏈示意圖

# 測試修復後的 data_source
python test_data_source_simple.py
# ✅ 輸出: close EMA=3089.29, volume EMA=5864.46, taker_ratio EMA=0.5321
```

---

## 📚 完整文檔

詳細說明請參考: [`docs/ARCHITECTURE_EXTENSIBILITY_GUIDE.md`](docs/ARCHITECTURE_EXTENSIBILITY_GUIDE.md)

---

**最後更新**: 2026-01-11  
**版本**: 2.0  
**維護者**: AI Agent
