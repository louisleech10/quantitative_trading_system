# Optuna 優化系統 - 輸出與視覺化規範

> **版本**: V1.0  
> **建立日期**: 2026-02-14  
> **目的**: 定義 Optuna 優化結果的輸出格式、視覺化標準、Dashboard 設計  
> **依據**: 業界標準 (QuantConnect, Quantopian, WorldQuant, Two Sigma)  
> **重要性**: ⭐⭐⭐⭐⭐ (V1.0 → V2.0 橋樑，AI Agent 需可讀格式)  
> **相關文件**: 
> - `Optuna重構_SPEC.md` (主規格)
> - `PRODUCT_VISION.md` (V1/V2/V3 演進)
> - `IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` (系統架構)

---

## 📋 目錄

1. [業界標準研究](#1-業界標準研究)
2. [輸出檔案格式規範](#2-輸出檔案格式規範)
3. [視覺化圖表規範](#3-視覺化圖表規範)
4. [Dashboard 設計](#4-dashboard-設計)
5. [AI 可讀格式設計](#5-ai-可讀格式設計)
6. [匯出功能設計](#6-匯出功能設計)
7. [實作優先順序](#7-實作優先順序)

---

## 1. 業界標準研究

### 1.1 QuantConnect 輸出規範

**QuantConnect** 是領先的量化平台，其優化結果輸出包含：

#### 檔案結構
```
/project/backtests/2024-02-14_optimization_001/
├── optimization_summary.json          # 最佳參數 + 統計摘要
├── trial_results.csv                  # 所有 Trial 明細
├── equity_curve.csv                   # 權益曲線時間序列
├── trades.csv                         # 所有交易明細
├── performance_metrics.json           # 績效指標 (Sharpe, MaxDD...)
├── charts/                            # 圖表 PNG
│   ├── equity_curve.png
│   ├── drawdown_curve.png
│   ├── parameter_importance.png
│   └── optimization_history.png
└── report.html                        # 完整 HTML 報告
```

#### 關鍵指標 (QuantConnect Standard)
```json
{
  "performance_metrics": {
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.31,
    "calmar_ratio": 1.42,
    "omega_ratio": 1.65,
    "max_drawdown": -0.181,
    "max_drawdown_duration_days": 45,
    "total_return": 0.523,
    "annual_return": 0.287,
    "annual_volatility": 0.155,
    "win_rate": 0.582,
    "profit_factor": 1.85,
    "expectancy": 0.042,
    "sqn": 2.15,
    "beta": 0.35,
    "alpha": 0.12,
    "information_ratio": 0.95,
    "tracking_error": 0.08
  },
  "trade_statistics": {
    "total_trades": 287,
    "winning_trades": 167,
    "losing_trades": 120,
    "average_win": 0.035,
    "average_loss": -0.018,
    "largest_win": 0.152,
    "largest_loss": -0.087,
    "average_trade_duration_hours": 36,
    "average_bars_held": 3
  }
}
```

---

### 1.2 Quantopian (Archive) 輸出規範

**Quantopian** (已關閉，但標準仍被業界引用) 特色：

#### Pyfolio 整合
- 使用 **Pyfolio** 庫生成標準報告
- Tear Sheet 格式 (4 頁標準報告)
- 風險分解分析 (Risk Attribution)

#### 輸出範例
```python
# Quantopian 風格輸出
{
  "returns_analysis": {
    "cumulative_returns": 0.523,
    "annual_return": 0.287,
    "annual_volatility": 0.155,
    "sharpe_ratio": 1.85,
    "max_drawdown": -0.181,
    "stability": 0.92,  # 權益曲線 R²
    "tail_ratio": 1.15  # 95 百分位 / 5 百分位
  },
  "rolling_statistics": {
    "rolling_sharpe_6m": [1.2, 1.5, 1.8, 2.1, 1.9],
    "rolling_volatility_6m": [0.12, 0.14, 0.13, 0.15, 0.14]
  },
  "worst_drawdown_periods": [
    {
      "start_date": "2025-06-15",
      "end_date": "2025-08-02",
      "peak_to_valley": -0.181,
      "recovery_date": "2025-09-10",
      "duration_days": 87
    }
  ]
}
```

---

### 1.3 WorldQuant 輸出規範

**WorldQuant** 特色：**Alpha 因子評分系統**

#### 核心指標 (WebSim 平台)
```json
{
  "alpha_metrics": {
    "sharpe": 1.85,
    "fitness": 2.34,       # 綜合評分 (考慮 Sharpe + Turnover + Correlation)
    "returns": 0.287,
    "drawdown": -0.181,
    "turnover": 0.45,      # 換手率 (越低越好)
    "margin": 0.65,        # 利潤率
    "decay": 5,            # Alpha 衰減天數
    "long_count": 25,      # 多頭持倉數
    "short_count": 25,     # 空頭持倉數
    "region_performance": {
      "USA": 0.032,
      "EUR": 0.028,
      "ASIA": 0.041
    }
  }
}
```

---

### 1.4 業界標準總結

| 平台 | 核心輸出格式 | 視覺化風格 | 特色功能 |
|------|------------|-----------|---------|
| **QuantConnect** | JSON + CSV | Interactive Plotly | HTML 報告 + 可下載圖表 |
| **Quantopian** | Pyfolio Tear Sheet | Matplotlib | 風險歸因分析 |
| **WorldQuant** | Alpha Metrics JSON | D3.js | Alpha 因子評分 |
| **Two Sigma** | 內部格式 | Bokeh | Monte Carlo 模擬 |
| **AQR** | PDF Report | LaTeX + R | 學術級報告 |

**共同標準**:
1. ✅ **JSON 為主要格式** (機器可讀)
2. ✅ **CSV 作為數據備份** (Excel 可開)
3. ✅ **PNG 圖表導出** (簡報用)
4. ✅ **HTML 完整報告** (分享用)
5. ✅ **核心指標統一**: Sharpe, MaxDD, Win Rate, Expectancy

---

## 2. 輸出檔案格式規範

### 2.1 檔案架構設計

#### 目錄結構
```
{PROJECT_ROOT}/optimization_results/
├── hyperparameter/                           # 模型超參數優化
│   └── {task_id}/                            # 例: hyper_20260214_001
│       ├── summary.json                      # ⭐ 最佳參數 + 核心指標
│       ├── trials.csv                        # 所有 Trial 明細
│       ├── trials_detailed.json              # Trial 詳細資訊 (含參數)
│       ├── parameter_importance.json         # 參數重要性 (Optuna 分析)
│       ├── optimization_history.json         # 優化過程時間序列
│       ├── model_comparison.json             # LightGBM vs XGBoost 對比
│       ├── overfitting_check.json            # 過擬合檢查結果
│       ├── ai_readable_report.md             # ⭐ AI Agent 可讀報告
│       └── charts/                           # 圖表 PNG
│           ├── parameter_importance.png
│           ├── optimization_history.png
│           ├── hyperparameter_distribution.png
│           └── overfitting_check.png
│
├── execution/                                # 策略執行參數優化
│   └── {task_id}/                            # 例: exec_20260214_002
│       ├── summary.json                      # ⭐ 最佳策略參數 + 績效
│       ├── trials.csv                        # 所有 Trial 明細
│       ├── trials_detailed.json              # Trial 詳細資訊
│       ├── backtest_result.json              # 回測完整結果
│       ├── equity_curve.csv                  # 權益曲線時間序列
│       ├── trades.csv                        # 所有交易明細
│       ├── trade_analysis.json               # 交易分析統計
│       ├── risk_metrics.json                 # 風險指標詳細分析
│       ├── pareto_front.json                 # Pareto 前沿 (若多目標)
│       ├── ai_readable_report.md             # ⭐ AI Agent 可讀報告
│       ├── full_report.html                  # 完整 HTML 報告
│       └── charts/                           # 圖表 PNG
│           ├── equity_curve.png
│           ├── drawdown_curve.png
│           ├── monthly_returns_heatmap.png
│           ├── trade_distribution.png
│           ├── parameter_importance.png
│           ├── optimization_history.png
│           ├── pareto_front.png              # (若多目標)
│           └── rolling_sharpe.png
│
└── metadata.json                             # 索引檔案 (所有任務清單)
```

---

### 2.2 JSON 格式詳細規範

#### 2.2.1 Hyperparameter Optimization - summary.json

```json
{
  "meta": {
    "task_id": "hyper_20260214_001",
    "task_type": "hyperparameter_optimization",
    "created_at": "2026-02-14T15:30:00Z",
    "completed_at": "2026-02-14T16:15:00Z",
    "duration_seconds": 2700,
    "study_name": "lightgbm_btcusdt_12h",
    "n_trials": 100,
    "n_completed_trials": 98,
    "n_failed_trials": 2,
    "sampler": "TPESampler",
    "optimization_direction": "maximize",
    "target_metric": "val_auc",
    "system_version": "v0.2.0"
  },
  
  "best_trial": {
    "trial_number": 67,
    "trial_id": "trial_67",
    "value": 0.8234,
    "datetime_complete": "2026-02-14T16:05:12Z",
    "params": {
      "learning_rate": 0.0532,
      "num_leaves": 87,
      "max_depth": 12,
      "min_child_samples": 45,
      "subsample": 0.82,
      "colsample_bytree": 0.75,
      "reg_alpha": 0.012,
      "reg_lambda": 0.085,
      "min_split_gain": 0.005
    },
    "user_attrs": {
      "train_auc": 0.8973,
      "val_auc": 0.8234,
      "train_val_gap": 0.0739,
      "training_time_seconds": 28.5,
      "n_features": 6514,
      "n_train_samples": 12580,
      "n_val_samples": 3145
    }
  },
  
  "performance_summary": {
    "validation_metrics": {
      "auc": 0.8234,
      "accuracy": 0.7823,
      "precision": 0.7654,
      "recall": 0.7912,
      "f1_score": 0.7781,
      "logloss": 0.4852
    },
    "overfitting_check": {
      "train_val_gap": 0.0739,
      "gap_threshold": 0.1,
      "is_overfitting": false,
      "recommendation": "Safe to deploy"
    },
    "model_stability": {
      "best_value_std": 0.0123,  # 前10名 Trial 標準差
      "best_value_range": 0.0287, # 前10名 Trial 範圍
      "stability_score": 0.92     # 穩定性評分 (0-1)
    }
  },
  
  "parameter_importance": {
    "learning_rate": 0.3452,
    "num_leaves": 0.2734,
    "max_depth": 0.1823,
    "subsample": 0.0987,
    "colsample_bytree": 0.0654,
    "min_child_samples": 0.0234,
    "reg_alpha": 0.0087,
    "reg_lambda": 0.0023,
    "min_split_gain": 0.0006
  },
  
  "optimization_insights": [
    "learning_rate 在 0.04-0.07 範圍內表現最佳",
    "num_leaves 過高 (>120) 會導致過擬合",
    "subsample 和 colsample_bytree 相互作用強",
    "regularization 參數影響較小"
  ],
  
  "next_steps": {
    "recommended_action": "Deploy to execution optimization",
    "confidence_level": "high",
    "warnings": [],
    "export_path": "/api/v1/models/export/hyper_20260214_001"
  }
}
```

---

#### 2.2.2 Execution Optimization - summary.json

```json
{
  "meta": {
    "task_id": "exec_20260214_002",
    "task_type": "execution_optimization",
    "created_at": "2026-02-14T16:30:00Z",
    "completed_at": "2026-02-14T16:35:00Z",
    "duration_seconds": 300,
    "study_name": "strategy_btcusdt_12h",
    "n_trials": 100,
    "n_completed_trials": 100,
    "n_failed_trials": 0,
    "sampler": "TPESampler",
    "optimization_direction": "maximize",
    "target_metric": "expectancy",
    "model_task_id": "hyper_20260214_001",  # 使用的模型
    "backtest_period": {
      "start_date": "2024-01-01",
      "end_date": "2026-01-01",
      "n_candles": 3650,
      "timeframe": "12h"
    },
    "system_version": "v0.2.0"
  },
  
  "best_trial": {
    "trial_number": 42,
    "trial_id": "trial_42",
    "value": 0.0452,  # Expectancy
    "datetime_complete": "2026-02-14T16:34:05Z",
    "params": {
      "entry_threshold": 0.72,
      "exit_threshold": 0.45,
      "stop_loss_atr_multiplier": 2.5,
      "take_profit_atr_multiplier": 4.0,
      "trailing_stop_atr_multiplier": 1.8,
      "position_sizing_method": "kelly_fraction",
      "kelly_fraction": 0.25,
      "max_position_size": 0.15,
      "min_holding_periods": 1,
      "max_holding_periods": 20
    },
    "user_attrs": {
      "sharpe_ratio": 1.85,
      "sortino_ratio": 2.34,
      "calmar_ratio": 1.42,
      "max_drawdown": -0.181,
      "win_rate": 0.582,
      "profit_factor": 1.85,
      "expectancy": 0.0452,
      "sqn": 2.15,
      "total_trades": 287,
      "avg_trade_duration_hours": 36
    }
  },
  
  "performance_metrics": {
    "returns": {
      "total_return": 0.523,
      "annual_return": 0.287,
      "monthly_return": 0.0214,
      "daily_return": 0.00068,
      "cumulative_return": 0.523,
      "buy_hold_return": 0.312,
      "excess_return": 0.211
    },
    "risk_adjusted": {
      "sharpe_ratio": 1.85,
      "sortino_ratio": 2.34,
      "calmar_ratio": 1.42,
      "omega_ratio": 1.65,
      "information_ratio": 0.95,
      "annual_volatility": 0.155,
      "downside_deviation": 0.087
    },
    "drawdown": {
      "max_drawdown": -0.181,
      "max_drawdown_duration_days": 45,
      "avg_drawdown": -0.053,
      "avg_drawdown_duration_days": 12,
      "recovery_factor": 2.89,  # Total Return / Max DD
      "ulcer_index": 0.042
    },
    "trade_statistics": {
      "total_trades": 287,
      "winning_trades": 167,
      "losing_trades": 120,
      "win_rate": 0.582,
      "profit_factor": 1.85,
      "expectancy": 0.0452,
      "sqn": 2.15,
      "average_win": 0.035,
      "average_loss": -0.018,
      "win_loss_ratio": 1.94,
      "largest_win": 0.152,
      "largest_loss": -0.087,
      "avg_trade_duration_hours": 36,
      "avg_bars_held": 3
    },
    "van_tharp_metrics": {
      "expectancy": 0.0452,
      "sqn": 2.15,
      "sqn_rating": "Above Average",  # <1.6: Poor, 1.6-1.9: Below Avg, 2.0-2.4: Above Avg, 2.5-2.9: Good, 3.0-5.0: Excellent, >7.0: Holy Grail
      "r_multiple_mean": 0.85,
      "r_multiple_std": 1.23,
      "opportunity": 287  # Total trades
    }
  },
  
  "risk_analysis": {
    "var_95": -0.032,  # Value at Risk (95%)
    "cvar_95": -0.045, # Conditional VaR
    "tail_ratio": 1.15,
    "worst_day": -0.087,
    "best_day": 0.152,
    "positive_days": 425,
    "negative_days": 305,
    "max_consecutive_wins": 12,
    "max_consecutive_losses": 8
  },
  
  "constraint_satisfaction": {
    "max_drawdown_constraint": {
      "limit": -0.30,
      "actual": -0.181,
      "satisfied": true
    },
    "win_rate_constraint": {
      "limit": 0.40,
      "actual": 0.582,
      "satisfied": true
    },
    "min_trades_constraint": {
      "limit": 100,
      "actual": 287,
      "satisfied": true
    }
  },
  
  "parameter_importance": {
    "entry_threshold": 0.4523,
    "stop_loss_atr_multiplier": 0.2834,
    "take_profit_atr_multiplier": 0.1623,
    "position_sizing_method": 0.0534,
    "kelly_fraction": 0.0287,
    "trailing_stop_atr_multiplier": 0.0123,
    "exit_threshold": 0.0076
  },
  
  "benchmark_comparison": {
    "strategy_return": 0.523,
    "buy_hold_return": 0.312,
    "outperformance": 0.211,
    "strategy_sharpe": 1.85,
    "buy_hold_sharpe": 0.92,
    "strategy_max_dd": -0.181,
    "buy_hold_max_dd": -0.456
  },
  
  "optimization_insights": [
    "Entry Threshold 0.7-0.75 表現最佳",
    "Stop Loss 2-3 ATR 平衡風險與報酬",
    "Kelly Fraction 0.2-0.3 最佳 (避免過度槓桿)",
    "持倉時間 24-48 小時最優"
  ],
  
  "next_steps": {
    "recommended_action": "Proceed to full backtest validation (Phase 5)",
    "confidence_level": "high",
    "warnings": [
      "樣本數 287 筆，建議增加測試期間",
      "回撤期間集中在 2025 Q3，需檢查該時期特殊事件"
    ],
    "export_path": "/api/v1/strategies/export/exec_20260214_002"
  }
}
```

---

### 2.3 CSV 格式規範

#### 2.3.1 trials.csv (通用格式)

```csv
trial_number,trial_id,value,state,datetime_start,datetime_complete,duration_seconds,learning_rate,num_leaves,max_depth,subsample,colsample_bytree,train_auc,val_auc,train_val_gap
1,trial_001,0.7823,COMPLETE,2026-02-14T15:30:05Z,2026-02-14T15:30:32Z,27,0.05,50,10,0.8,0.8,0.8534,0.7823,0.0711
2,trial_002,0.7912,COMPLETE,2026-02-14T15:30:35Z,2026-02-14T15:31:03Z,28,0.08,80,12,0.85,0.75,0.8765,0.7912,0.0853
...
```

**欄位說明**:
- `trial_number`: Trial 編號 (1-N)
- `trial_id`: 唯一識別碼
- `value`: 目標函數值 (Validation AUC / Expectancy 等)
- `state`: COMPLETE / PRUNED / FAIL
- 動態參數欄位 (依優化任務不同)
- 動態 user_attrs 欄位 (額外指標)

---

#### 2.3.2 equity_curve.csv (執行優化專用)

```csv
datetime,equity,returns,drawdown,cumulative_return,benchmark_equity,benchmark_returns
2024-01-01T00:00:00Z,100000.00,0.000000,0.000000,0.000000,100000.00,0.000000
2024-01-01T12:00:00Z,100350.00,0.003500,-0.000000,0.003500,100120.00,0.001200
2024-01-02T00:00:00Z,100280.00,-0.000698,-0.000698,0.002800,100250.00,0.002500
2024-01-02T12:00:00Z,101200.00,0.009177,0.000000,0.012000,100400.00,0.004000
...
```

**欄位說明**:
- `datetime`: 時間戳記 (ISO 8601)
- `equity`: 當前權益
- `returns`: 單期報酬率
- `drawdown`: 當前回撤 (負值)
- `cumulative_return`: 累積報酬率
- `benchmark_equity`: 基準 (Buy & Hold) 權益
- `benchmark_returns`: 基準報酬率

---

#### 2.3.3 trades.csv (執行優化專用)

```csv
trade_id,entry_datetime,exit_datetime,direction,entry_price,exit_price,position_size,pnl,pnl_pct,mae,mfe,r_multiple,holding_periods,exit_reason,commission,slippage
1,2024-01-05T12:00:00Z,2024-01-07T00:00:00Z,LONG,42500.00,43200.00,0.05,35.00,0.0165,-50.00,80.00,1.2,3,TAKE_PROFIT,2.50,5.00
2,2024-01-10T00:00:00Z,2024-01-11T12:00:00Z,LONG,43800.00,43500.00,0.05,-15.00,-0.0068,-30.00,10.00,-0.5,3,STOP_LOSS,2.50,5.00
...
```

**欄位說明** (Van Tharp 風格):
- `r_multiple`: R-倍數 (PnL / 初始風險)
- `mae`: Maximum Adverse Excursion (最大不利偏移)
- `mfe`: Maximum Favorable Excursion (最大有利偏移)
- `exit_reason`: TAKE_PROFIT / STOP_LOSS / TRAILING_STOP / SIGNAL_EXIT / TIME_EXIT

---

### 2.4 AI 可讀格式 (ai_readable_report.md)

> **關鍵需求**: V1.0 → V2.0 演進橋樑，讓 AI Agent 可理解優化結果

#### 範例: Hyperparameter Optimization Report

```markdown
# Hyperparameter Optimization Report

## Task Summary
- **Task ID**: hyper_20260214_001
- **Model**: LightGBM
- **Symbol**: BTCUSDT
- **Timeframe**: 12h
- **Optimization Duration**: 45 minutes
- **Trials Completed**: 98/100
- **Best Trial**: #67
- **Best Validation AUC**: 0.8234

## Best Parameters
```json
{
  "learning_rate": 0.0532,
  "num_leaves": 87,
  "max_depth": 12,
  "min_child_samples": 45,
  "subsample": 0.82,
  "colsample_bytree": 0.75
}
```

## Performance Analysis
- ✅ **Validation AUC**: 0.8234 (Target: >0.80)
- ✅ **Train-Val Gap**: 0.0739 (Threshold: <0.10)
- ✅ **No Overfitting Detected**
- ⚠️ **Stability**: 0.92 (Good, but top trials have 0.0123 std)

## Key Insights
1. **learning_rate** is the most important parameter (34.5% importance)
2. Optimal range: 0.04-0.07
3. **num_leaves** >120 causes overfitting
4. Regularization has minimal impact (<1% importance)

## Recommendations
1. ✅ **Deploy to Execution Optimization**: Model quality is sufficient
2. 📊 **Expected Performance**: 58% win rate, 1.8+ Sharpe ratio
3. ⚠️ **Monitor**: Watch for concept drift after 3 months

## Next Steps for AI Agent
```python
# Code to load this model
from momentum.Model import load_trained_model
model = load_trained_model("hyper_20260214_001")

# Use in execution optimization
POST /api/v1/optimization/execution
{
  "model_task_id": "hyper_20260214_001",
  "search_space": {...}
}
```

## Files Generated
- `summary.json` - Full results
- `trials.csv` - All trial data
- `charts/parameter_importance.png` - Visualization
```

---

## 3. 視覺化圖表規範

### 3.1 Hyperparameter Optimization 圖表

#### 3.1.1 Parameter Importance (參數重要性)
```typescript
// 圖表類型: Horizontal Bar Chart
// 庫: Recharts <BarChart layout="vertical">

interface ParameterImportance {
  parameter_name: string;
  importance: number;  // 0-1
  color: string;       // 依重要性: >0.2紅色, 0.1-0.2黃色, <0.1灰色
}

// 視覺設計
export function ParameterImportanceChart() {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data} layout="vertical">
        <XAxis type="number" domain={[0, 1]} />
        <YAxis type="category" dataKey="parameter_name" width={150} />
        <Tooltip />
        <Bar dataKey="importance" fill="#3b82f6">
          <LabelList dataKey="importance" position="right" formatter={(v) => `${(v*100).toFixed(1)}%`} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

**業界標準參考**: Optuna Dashboard, QuantConnect

---

#### 3.1.2 Optimization History (優化歷史)
```typescript
// 圖表類型: Line Chart with Scatter
// 顯示: 每個 Trial 的 Value + Best Value 累積曲線

interface OptimizationHistory {
  trial_number: number;
  value: number;
  best_value_so_far: number;
  is_best: boolean;
}

export function OptimizationHistoryChart() {
  return (
    <ComposedChart data={data}>
      <Line 
        type="stepAfter" 
        dataKey="best_value_so_far" 
        stroke="#10b981" 
        strokeWidth={2}
        name="Best Value"
      />
      <Scatter 
        dataKey="value" 
        fill="#3b82f6" 
        name="Trial Value"
      />
      {/* 標記最佳 Trial */}
      <ReferenceLine 
        x={bestTrialNumber} 
        stroke="#ef4444" 
        label="Best" 
      />
    </ComposedChart>
  );
}
```

---

#### 3.1.3 Hyperparameter Distribution (超參數分佈)
```typescript
// 圖表類型: Parallel Coordinates
// 顯示: 前 20 名 Trial 的參數組合

export function HyperparameterDistributionChart() {
  // 使用 Recharts RadarChart 或 D3.js Parallel Coordinates
  // 每條線代表一個 Trial
  // 顏色深淺表示性能 (深色=好)
}
```

---

#### 3.1.4 Overfitting Check (過擬合檢查)
```typescript
// 圖表類型: Scatter Plot (Train AUC vs Val AUC)

export function OverfittingCheckChart() {
  return (
    <ScatterChart>
      <Scatter data={trials} fill="#3b82f6" />
      {/* 對角線 (Train=Val) */}
      <ReferenceLine 
        segment={[{x: 0, y: 0}, {x: 1, y: 1}]} 
        stroke="#10b981" 
        label="Perfect (No Overfit)"
      />
      {/* 過擬合警戒線 (Train-Val Gap = 0.1) */}
      <ReferenceLine 
        segment={[{x: 0.1, y: 0}, {x: 1, y: 0.9}]} 
        stroke="#ef4444" 
        strokeDasharray="5 5"
        label="Overfit Threshold"
      />
    </ScatterChart>
  );
}
```

---

### 3.2 Execution Optimization 圖表

#### 3.2.1 Equity Curve (權益曲線)
```typescript
// 圖表類型: Area Chart with Comparison Line
// 顯示: 策略權益 vs Buy & Hold

interface EquityPoint {
  datetime: string;
  strategy_equity: number;
  benchmark_equity: number;
  drawdown: number;
}

export function EquityCurveChart() {
  return (
    <ComposedChart data={data}>
      <Area 
        type="monotone" 
        dataKey="strategy_equity" 
        fill="#3b82f6" 
        fillOpacity={0.3}
        stroke="#3b82f6"
        strokeWidth={2}
        name="Strategy"
      />
      <Line 
        type="monotone" 
        dataKey="benchmark_equity" 
        stroke="#6b7280" 
        strokeWidth={1}
        strokeDasharray="5 5"
        name="Buy & Hold"
      />
      <Tooltip 
        formatter={(value: number) => `$${value.toFixed(2)}`}
      />
      <Legend />
    </ComposedChart>
  );
}
```

**業界標準**: QuantConnect, TradingView

---

#### 3.2.2 Drawdown Curve (回撤曲線)
```typescript
// 圖表類型: Area Chart (下沉)
// 顯示: 從高點的回撤百分比

export function DrawdownCurveChart() {
  return (
    <AreaChart data={data}>
      <Area 
        type="monotone" 
        dataKey="drawdown" 
        fill="#ef4444" 
        fillOpacity={0.5}
        stroke="#ef4444"
        strokeWidth={2}
      />
      <ReferenceLine y={-0.30} stroke="#f59e0b" label="Constraint (-30%)" />
      <YAxis 
        domain={[-1, 0]} 
        tickFormatter={(v) => `${(v*100).toFixed(0)}%`}
      />
    </AreaChart>
  );
}
```

---

#### 3.2.3 Monthly Returns Heatmap (月度報酬熱力圖)
```typescript
// 圖表類型: Heatmap
// 顯示: 每月報酬 (X軸=月份, Y軸=年份)

interface MonthlyReturn {
  year: number;
  month: number;  // 1-12
  return_pct: number;
}

export function MonthlyReturnsHeatmap() {
  // 使用 Recharts 或自定義 SVG
  // 顏色: 綠色(正報酬) 紅色(負報酬)
  // 業界標準: Quantopian Pyfolio
}
```

---

#### 3.2.4 Trade Distribution (交易分佈)
```typescript
// 圖表類型: Histogram
// 顯示: PnL% 分佈 + Win/Loss 分離

export function TradeDistributionChart() {
  return (
    <BarChart data={pnlBins}>
      <Bar dataKey="count" fill={(entry) => entry.pnl > 0 ? '#10b981' : '#ef4444'} />
      <XAxis dataKey="pnl_bin" label="PnL %" />
      <YAxis label="Trade Count" />
      {/* 標記平均盈虧 */}
      <ReferenceLine x={avgWin} stroke="#10b981" label="Avg Win" />
      <ReferenceLine x={avgLoss} stroke="#ef4444" label="Avg Loss" />
    </BarChart>
  );
}
```

---

#### 3.2.5 Pareto Front (Pareto 前沿) - 多目標優化
```typescript
// 圖表類型: Scatter Plot
// 顯示: Sharpe Ratio (X) vs Max Drawdown (Y)

interface ParetoPoint {
  trial_number: number;
  sharpe_ratio: number;
  max_drawdown: number;
  is_pareto_optimal: boolean;
}

export function ParetoFrontChart() {
  return (
    <ScatterChart>
      <Scatter 
        data={paretoPoints.filter(p => p.is_pareto_optimal)} 
        fill="#10b981" 
        name="Pareto Optimal"
      />
      <Scatter 
        data={paretoPoints.filter(p => !p.is_pareto_optimal)} 
        fill="#9ca3af" 
        name="Dominated"
      />
      <XAxis dataKey="sharpe_ratio" label="Sharpe Ratio" />
      <YAxis dataKey="max_drawdown" label="Max Drawdown" />
    </ScatterChart>
  );
}
```

**業界標準**: Optuna (Multi-Objective Visualization)

---

#### 3.2.6 Rolling Sharpe Ratio (滾動夏普比率)
```typescript
// 圖表類型: Line Chart
// 顯示: 6 個月滾動 Sharpe Ratio

export function RollingSharpeChart() {
  return (
    <LineChart data={data}>
      <Line 
        type="monotone" 
        dataKey="rolling_sharpe_6m" 
        stroke="#3b82f6" 
        strokeWidth={2}
      />
      <ReferenceLine y={1.0} stroke="#10b981" label="Good (>1.0)" />
      <ReferenceLine y={2.0} stroke="#f59e0b" label="Excellent (>2.0)" />
    </LineChart>
  );
}
```

---

### 3.3 圖表導出規範

#### PNG 導出設定
```typescript
import html2canvas from 'html2canvas';

export async function exportChartAsPNG(
  chartRef: RefObject<HTMLDivElement>,
  filename: string
) {
  const canvas = await html2canvas(chartRef.current!, {
    backgroundColor: '#ffffff',
    scale: 2,  // 2x 解析度 (適合簡報)
    logging: false,
    useCORS: true
  });
  
  const link = document.createElement('a');
  link.download = `${filename}_${Date.now()}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

// 批量導出所有圖表
export async function exportAllCharts(taskId: string) {
  const charts = [
    'equity_curve',
    'drawdown_curve',
    'trade_distribution',
    'parameter_importance',
    'optimization_history'
  ];
  
  for (const chart of charts) {
    await exportChartAsPNG(chartRefs[chart], `${taskId}_${chart}`);
    await delay(500);  // 避免 Canvas 衝突
  }
}
```

---

## 4. Dashboard 設計

### 4.1 Hyperparameter Optimization Dashboard

#### 頁面結構
```
/optimization/hyperparameter/result/{taskId}

┌────────────────────────────────────────────────────────────────┐
│ [< Back] Hyperparameter Optimization Result                    │
│ Task ID: hyper_20260214_001 | Duration: 45 min | Status: ✅    │
└────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 📊 Best Model Performance                                     │
├───────────────┬───────────────┬───────────────┬──────────────┤
│ Val AUC       │ Train-Val Gap │ Trials        │ Best Trial   │
│ 0.8234        │ 0.0739        │ 98/100        │ #67          │
│ ✅ Target: 0.80│ ✅ < 0.10     │ 2 Failed      │              │
└───────────────┴───────────────┴───────────────┴──────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ⚙️ Best Hyperparameters                    [Copy JSON] [Export]│
├─────────────────────────────────────────────────────────────┤
│ {                                                            │
│   "learning_rate": 0.0532,                                   │
│   "num_leaves": 87,                                          │
│   "max_depth": 12,                                           │
│   ...                                                        │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────┬─────────────────────────────────┐
│ Parameter Importance     │ Optimization History             │
│                          │                                  │
│ [Bar Chart]              │ [Line Chart]                     │
│                          │                                  │
└──────────────────────────┴─────────────────────────────────┘

┌──────────────────────────┬─────────────────────────────────┐
│ Overfitting Check        │ Hyperparameter Distribution      │
│                          │                                  │
│ [Scatter Plot]           │ [Parallel Coordinates]           │
│                          │                                  │
└──────────────────────────┴─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📋 Trial Comparison Table                 [Export CSV]       │
├────┬─────┬──────────┬───────────┬──────────┬──────┬────────┤
│ #  │ Val │ Train-Val│ LR        │ Leaves   │ Depth│ Time   │
├────┼─────┼──────────┼───────────┼──────────┼──────┼────────┤
│ 67 │0.823│ 0.074    │ 0.0532    │ 87       │ 12   │ 28s    │
│ 23 │0.820│ 0.069    │ 0.0487    │ 92       │ 11   │ 27s    │
│ ...│     │          │           │          │      │        │
└────┴─────┴──────────┴───────────┴──────────┴──────┴────────┘

┌─────────────────────────────────────────────────────────────┐
│ 💡 Insights & Recommendations                                │
│ ✅ Model quality sufficient for deployment                   │
│ ⚠️ Monitor for concept drift after 3 months                  │
│ 📊 Optimal learning_rate range: 0.04-0.07                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🎯 Next Steps                                                │
│ [Deploy to Execution Optimization] [Download Full Report]    │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.2 Execution Optimization Dashboard

#### 頁面結構
```
/optimization/execution/result/{taskId}

┌────────────────────────────────────────────────────────────────┐
│ [< Back] Execution Optimization Result                         │
│ Task ID: exec_20260214_002 | Duration: 5 min | Status: ✅      │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📊 Strategy Performance Summary                              │
├──────────┬──────────┬──────────┬──────────┬─────────┬───────┤
│ Sharpe   │ Expectancy│ Max DD  │ Win Rate │ Trades  │ SQN   │
│ 1.85     │ 0.0452   │ -18.1%  │ 58.2%    │ 287     │ 2.15  │
│ ✅ >1.5  │ ✅ >0.03  │ ✅ >-30%│ ✅ >40%  │ ✅ >100 │ Above Avg│
└──────────┴──────────┴──────────┴──────────┴─────────┴───────┘

┌─────────────────────────────────────────────────────────────┐
│ ⚙️ Best Strategy Parameters                [Copy JSON] [Export]│
├─────────────────────────────────────────────────────────────┤
│ {                                                            │
│   "entry_threshold": 0.72,                                   │
│   "stop_loss_atr": 2.5,                                      │
│   "take_profit_atr": 4.0,                                    │
│   "kelly_fraction": 0.25,                                    │
│   ...                                                        │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 📈 Equity Curve                                [Export PNG]  │
│                                                               │
│ [Area Chart - Strategy vs Buy & Hold]                        │
│                                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────┬──────────────────────────────────┐
│ Drawdown Curve           │ Rolling Sharpe Ratio             │
│                          │                                  │
│ [Area Chart]             │ [Line Chart]                     │
│                          │                                  │
└──────────────────────────┴──────────────────────────────────┘

┌──────────────────────────┬──────────────────────────────────┐
│ Monthly Returns Heatmap  │ Trade Distribution               │
│                          │                                  │
│ [Heatmap]                │ [Histogram]                      │
│                          │                                  │
└──────────────────────────┴──────────────────────────────────┘

┌──────────────────────────┬──────────────────────────────────┐
│ Parameter Importance     │ Pareto Front (Multi-Objective)   │
│                          │                                  │
│ [Bar Chart]              │ [Scatter Plot]                   │
│                          │                                  │
└──────────────────────────┴──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📋 Trade Details                          [Export CSV]       │
├────┬────────────┬───────┬──────┬─────┬─────┬────┬──────────┤
│ #  │ Entry Time │ Dir   │ PnL% │ R   │ MAE │ MFE│ Exit     │
├────┼────────────┼───────┼──────┼─────┼─────┼────┼──────────┤
│ 1  │ 2024-01-05 │ LONG  │ 1.65%│ 1.2 │-0.5%│8.0%│ TP       │
│ 2  │ 2024-01-10 │ LONG  │-0.68%│-0.5 │-3.0%│1.0%│ SL       │
│ ...│            │       │      │     │     │    │          │
└────┴────────────┴───────┴──────┴─────┴─────┴────┴──────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🎯 Benchmark Comparison                                      │
├─────────────────┬──────────────┬──────────────┬─────────────┤
│ Metric          │ Strategy     │ Buy & Hold   │ Difference  │
├─────────────────┼──────────────┼──────────────┼─────────────┤
│ Total Return    │ 52.3%        │ 31.2%        │ +21.1%      │
│ Sharpe Ratio    │ 1.85         │ 0.92         │ +0.93       │
│ Max Drawdown    │ -18.1%       │ -45.6%       │ +27.5%      │
└─────────────────┴──────────────┴──────────────┴─────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 💡 Insights & Recommendations                                │
│ ✅ Strategy outperforms Buy & Hold by 21.1%                  │
│ ⚠️ Trade count moderate (287), consider longer test period   │
│ 📊 Entry Threshold 0.7-0.75 optimal                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🎯 Next Steps                                                │
│ [Proceed to Full Backtest] [Download Full Report] [Export]  │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. AI 可讀格式設計

### 5.1 設計原則

**目標**: 讓 V2.0 AI Agent 能理解和操作 V1.0 的輸出

**設計原則**:
1. ✅ **結構化**: JSON 為主，Markdown 為輔
2. ✅ **語義化**: 欄位名稱明確 (不用縮寫)
3. ✅ **可操作**: 提供下一步 API 端點
4. ✅ **上下文**: 包含決策依據和警告
5. ✅ **可驗證**: 所有數值附帶單位和閾值

---

### 5.2 AI Agent 使用範例

#### 範例 1: AI Agent 讀取優化結果

```python
# AI Agent 程式碼 (V2.0)
import json

# 1. 讀取優化結果
with open('optimization_results/execution/exec_20260214_002/summary.json') as f:
    result = json.load(f)

# 2. 解析性能
sharpe = result['performance_metrics']['risk_adjusted']['sharpe_ratio']
max_dd = result['performance_metrics']['drawdown']['max_drawdown']
win_rate = result['performance_metrics']['trade_statistics']['win_rate']

# 3. 決策邏輯
if sharpe > 1.5 and max_dd > -0.30 and win_rate > 0.50:
    decision = "APPROVE"
    confidence = "HIGH"
else:
    decision = "REJECT"
    confidence = "LOW"

# 4. 回應給用戶
response = f"""
根據優化結果分析:
- Sharpe Ratio: {sharpe} {'✅' if sharpe > 1.5 else '❌'}
- Max Drawdown: {max_dd*100:.1f}% {'✅' if max_dd > -0.30 else '❌'}
- Win Rate: {win_rate*100:.1f}% {'✅' if win_rate > 0.50 else '❌'}

**決策**: {decision} (信心度: {confidence})
**建議**: {'繼續進行完整回測' if decision == 'APPROVE' else '重新優化參數'}
"""

print(response)
```

---

#### 範例 2: AI Agent 生成對話式報告

```python
# AI Agent (V2.0) 讀取 ai_readable_report.md
with open('optimization_results/execution/exec_20260214_002/ai_readable_report.md') as f:
    report = f.read()

# 使用 LLM 生成對話式回應
prompt = f"""
你是量化交易助手。根據以下優化報告，用對話方式向用戶解釋結果。

{report}

用戶問題: "這個策略表現如何？能實盤嗎？"
"""

response = llm.generate(prompt)
# AI: "這個策略表現相當不錯！Sharpe Ratio 達到 1.85，屬於「優秀」級別。
#      最大回撤控制在 -18.1%，遠低於您設定的 -30% 限制。
#      勝率 58.2%，Expectancy 為正 (0.0452)，表示長期有盈利潛力。
#      
#      不過我建議先進行完整回測驗證，因為樣本數 287 筆偏少，
#      且回撤期間集中在 2025 Q3，需要檢查那段時間是否有特殊事件。"
```

---

### 5.3 AI 可讀報告模板

```markdown
# AI-Readable Optimization Report

## Metadata
- Task ID: {task_id}
- Task Type: {hyperparameter|execution}
- Created: {iso_datetime}
- Status: {completed|failed}

## Performance Summary
**Key Metrics**:
- PRIMARY_METRIC: {value} ({unit}) {'✅' if pass else '❌'} Target: {target}
- SECONDARY_METRIC_1: {value} ({unit}) {'✅' if pass else '❌'} Target: {target}
- SECONDARY_METRIC_2: {value} ({unit}) {'⚠️' if warning else '✅'} Target: {target}

## Best Parameters
```json
{best_params}
```

## Constraint Satisfaction
- Constraint 1: {name} {actual} / {limit} {'✅' if satisfied else '❌'}
- Constraint 2: {name} {actual} / {limit} {'✅' if satisfied else '❌'}

## Decision Logic
IF {condition_1} AND {condition_2} THEN {action}

RECOMMENDED_ACTION: {action}
CONFIDENCE_LEVEL: {high|medium|low}
REASONING: {explanation}

## Warnings & Risks
- ⚠️ {warning_1}
- ⚠️ {warning_2}

## Next API Call
```python
POST {api_endpoint}
BODY: {json_body}
```

## Files
- JSON: {summary_json_path}
- CSV: {trials_csv_path}  
- Charts: {charts_directory}
```

---

## 6. 匯出功能設計

### 6.1 匯出按鈕設計

#### 前端元件
```typescript
// frontend/src/components/optimization/ExportPanel.tsx

interface ExportPanelProps {
  taskId: string;
  taskType: 'hyperparameter' | 'execution';
}

export function ExportPanel({ taskId, taskType }: ExportPanelProps) {
  const handleExport = async (format: string) => {
    const response = await fetch(`/api/v1/optimization/${taskType}/${taskId}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format })
    });
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${taskId}_${format}_${Date.now()}.${format}`;
    a.click();
  };

  return (
    <div className="export-panel">
      <h3>Export Results</h3>
      <div className="button-group">
        <button onClick={() => handleExport('json')}>
          📄 JSON (Machine Readable)
        </button>
        <button onClick={() => handleExport('csv')}>
          📊 CSV (Excel)
        </button>
        <button onClick={() => handleExport('html')}>
          🌐 HTML Report
        </button>
        <button onClick={() => handleExport('pdf')}>
          📕 PDF Report
        </button>
        <button onClick={() => handleExport('charts')}>
          🖼️ All Charts (ZIP)
        </button>
        <button onClick={() => handleExport('full')}>
          📦 Full Package (ZIP)
        </button>
      </div>
    </div>
  );
}
```

---

### 6.2 後端匯出 API

```python
# api/routes/optimization_export.py

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import zipfile
import io

router = APIRouter()

@router.post("/api/v1/optimization/{task_type}/{task_id}/export")
async def export_optimization_result(
    task_type: str,  # hyperparameter | execution
    task_id: str,
    request: ExportRequest,
    background_tasks: BackgroundTasks
):
    """
    匯出優化結果
    
    支援格式:
    - json: summary.json
    - csv: trials.csv + trades.csv (若 execution)
    - html: 完整 HTML 報告
    - pdf: PDF 報告 (使用 WeasyPrint)
    - charts: 所有圖表 PNG (ZIP)
    - full: 完整套件 (JSON + CSV + Charts + HTML)
    """
    
    base_path = f"optimization_results/{task_type}/{task_id}"
    
    if request.format == "json":
        return FileResponse(
            f"{base_path}/summary.json",
            media_type="application/json",
            filename=f"{task_id}_summary.json"
        )
    
    elif request.format == "csv":
        # 多檔案 ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(f"{base_path}/trials.csv", "trials.csv")
            if task_type == "execution":
                zip_file.write(f"{base_path}/equity_curve.csv", "equity_curve.csv")
                zip_file.write(f"{base_path}/trades.csv", "trades.csv")
        
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={task_id}_csv.zip"}
        )
    
    elif request.format == "html":
        # 生成 HTML 報告
        html_content = await generate_html_report(task_id, task_type)
        return StreamingResponse(
            io.BytesIO(html_content.encode()),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename={task_id}_report.html"}
        )
    
    elif request.format == "pdf":
        # 使用 WeasyPrint 將 HTML 轉 PDF
        html_content = await generate_html_report(task_id, task_type)
        pdf_buffer = HTML(string=html_content).write_pdf()
        return StreamingResponse(
            io.BytesIO(pdf_buffer),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={task_id}_report.pdf"}
        )
    
    elif request.format == "charts":
        # 所有圖表 PNG
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipzip.ZIP_DEFLATED) as zip_file:
            chart_dir = f"{base_path}/charts"
            for chart_file in os.listdir(chart_dir):
                zip_file.write(f"{chart_dir}/{chart_file}", chart_file)
        
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={task_id}_charts.zip"}
        )
    
    elif request.format == "full":
        # 完整套件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 遞迴加入所有檔案
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = file_path.replace(base_path, task_id)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={task_id}_full.zip"}
        )
```

---

### 6.3 HTML 報告生成器

```python
# momentum/Reporting/html_report_generator.py

from jinja2 import Template
import json

class HTMLReportGenerator:
    """
    生成專業 HTML 報告 (QuantConnect 風格)
    """
    
    def __init__(self, task_id: str, task_type: str):
        self.task_id = task_id
        self.task_type = task_type
        self.base_path = f"optimization_results/{task_type}/{task_id}"
    
    async def generate(self) -> str:
        """生成完整 HTML 報告"""
        
        # 1. 讀取數據
        with open(f"{self.base_path}/summary.json") as f:
            summary = json.load(f)
        
        # 2. 準備圖表 (Base64 嵌入)
        charts = self._embed_charts()
        
        # 3. 使用 Jinja2 模板
        template = Template(self._get_template())
        
        html = template.render(
            task_id=self.task_id,
            task_type=self.task_type,
            summary=summary,
            charts=charts,
            generated_at=datetime.now().isoformat()
        )
        
        return html
    
    def _embed_charts(self) -> dict:
        """將圖表轉為 Base64 嵌入 HTML"""
        import base64
        
        charts = {}
        chart_dir = f"{self.base_path}/charts"
        
        for chart_file in os.listdir(chart_dir):
            with open(f"{chart_dir}/{chart_file}", 'rb') as f:
                encoded = base64.b64encode(f.read()).decode()
                charts[chart_file.replace('.png', '')] = f"data:image/png;base64,{encoded}"
        
        return charts
    
    def _get_template(self) -> str:
        """Jinja2 HTML 模板"""
        return """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>Optimization Report - {{ task_id }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1f2937;
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 10px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        .metric-card {
            background: #f9fafb;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            color: #1f2937;
        }
        .metric-label {
            font-size: 14px;
            color: #6b7280;
            margin-top: 5px;
        }
        .chart-section {
            margin: 40px 0;
        }
        .chart-section img {
            width: 100%;
            max-width: 800px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        .parameters {
            background: #1f2937;
            color: #f9fafb;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Optimization Report</h1>
        <p><strong>Task ID:</strong> {{ task_id }}</p>
        <p><strong>Task Type:</strong> {{ task_type }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
        
        {% if task_type == 'execution' %}
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{{ (summary.performance_metrics.risk_adjusted.sharpe_ratio * 100) | round(2) }}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ (summary.performance_metrics.trade_statistics.expectancy * 100) | round(3) }}%</div>
                <div class="metric-label">Expectancy</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ (summary.performance_metrics.drawdown.max_drawdown * 100) | round(1) }}%</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ (summary.performance_metrics.trade_statistics.win_rate * 100) | round(1) }}%</div>
                <div class="metric-label">Win Rate</div>
            </div>
        </div>
        
        <h2>📈 Equity Curve</h2>
        <div class="chart-section">
            <img src="{{ charts.equity_curve }}" alt="Equity Curve" />
        </div>
        
        <h2>📉 Drawdown Curve</h2>
        <div class="chart-section">
            <img src="{{ charts.drawdown_curve }}" alt="Drawdown Curve" />
        </div>
        {% endif %}
        
        <h2>⚙️ Best Parameters</h2>
        <div class="parameters">
            <pre>{{ summary.best_trial.params | tojson(indent=2) }}</pre>
        </div>
        
        <h2>📊 Parameter Importance</h2>
        <div class="chart-section">
            <img src="{{ charts.parameter_importance }}" alt="Parameter Importance" />
        </div>
        
        <h2>📈 Optimization History</h2>
        <div class="chart-section">
            <img src="{{ charts.optimization_history }}" alt="Optimization History" />
        </div>
    </div>
</body>
</html>
        """
```

---

## 7. 實作優先順序

### Phase 1 - 核心輸出 (Week 1-2)
- [x] 定義 JSON 格式規範
- [ ] 實作 summary.json 生成
- [ ] 實作 trials.csv 生成
- [ ] 實作 equity_curve.csv 生成 (execution)
- [ ] 實作 trades.csv 生成 (execution)
- [ ] 實作目錄結構創建

### Phase 2 - 視覺化基礎 (Week 3-4)
- [ ] Parameter Importance Chart
- [ ] Optimization History Chart
- [ ] Equity Curve Chart
- [ ] Drawdown Curve Chart
- [ ] PNG 導出功能

### Phase 3 - Dashboard (Week 5-6)
- [ ] Hyperparameter Result Page
- [ ] Execution Result Page
- [ ] Metrics Cards
- [ ] Trial Comparison Table
- [ ] Insights & Recommendations Panel

### Phase 4 - AI 可讀格式 (Week 7)
- [ ] ai_readable_report.md 生成
- [ ] 標準化決策邏輯格式
- [ ] API 端點建議
- [ ] 警告與風險標記

### Phase 5 - 進階功能 (Week 8-10)
- [ ] HTML 報告生成器
- [ ] PDF 導出 (WeasyPrint)
- [ ] 完整 ZIP 打包
- [ ] Monthly Returns Heatmap
- [ ] Pareto Front Chart (多目標)
- [ ] Rolling Sharpe Chart

### Phase 6 - 業界對標 (Week 11-12)
- [ ] Pyfolio 風格 Tear Sheet
- [ ] QuantConnect 風格報告
- [ ] WorldQuant Alpha Metrics
- [ ] Van Tharp R-Multiple 分析

---

## 📚 參考資料

### 業界平台
1. **QuantConnect**: https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/results
2. **Quantopian Pyfolio**: https://github.com/quantopian/pyfolio
3. **WorldQuant WebSim**: https://www.worldquantvrc.com/en/cms/wqc/websim/
4. **Optuna Dashboard**: https://optuna.readthedocs.io/en/stable/reference/visualization/index.html

### 技術標準
1. **JSON Schema**: Optimization Result Schema (自定義)
2. **Van Tharp Metrics**: System Quality Number, R-Multiple, Expectancy
3. **Sharpe Ratio Family**: Sharpe, Sortino, Calmar, Omega
4. **Pyfolio Metrics**: https://quantopian.github.io/pyfolio/

### 圖表庫
1. **Recharts**: https://recharts.org/ (React)
2. **Plotly**: https://plotly.com/python/ (Python)
3. **D3.js**: https://d3js.org/ (進階視覺化)
4. **html2canvas**: https://html2canvas.hertzen.com/ (PNG 導出)

---

**END OF DOCUMENT**
