# Optuna重構_SPEC V0.2 補充說明

> **版本**: V0.2 Addendum  
> **日期**: 2026-02-14  
> **目的**: 針對使用者提出的 7 個關鍵問題，補充 V0.1 未涵蓋的內容  
> **原文件**: `Optuna重構_SPEC.md` V0.1  
> **狀態**: 📝 補充文件 - 等待整合回主文件

---

## 📌 V0.2 主要變更摘要

### 變更1: 移除/封存指標參數優化模式
- **決策**: 封存 `optimization_mode='indicator'` 相關程式碼
- **影響**: 簡化為 2 種模式 (`hyperparameter` + `execution`)
- **封存位置**: `archived/momentum/Optimization/indicator_mode/`

### 變更2: 新增模型超參數優化維度
- **新增**: `HyperparameterObjective` 類
- **支援**: LightGBM 9 個參數 + XGBoost 8 個參數
- **前端**: 新增 `/optimization/hyperparameter` 頁面

### 變更3: 業界實踐澄清
- **結論**: Optuna 在完整回測**之前**使用是業界標準
- **流程**: 超參數優化 → 策略參數優化 (向量化回測) → 完整回測驗證

### 變更4: 前端UI參數配置需求
- **新增**: 超參數搜索空間配置 UI (可編輯表格)
- **新增**: 策略執行參數配置 UI (滑桿 + 預設範圍按鈕)
- **新增**: 優化目標選擇 (Expectancy/Sharpe/Sortino...)
- **新增**: 風險約束配置 (MaxDD上限, Win Rate下限)

### 變更5: LightGBM/XGBoost 超參數審查
- **發現**: Phase 3 未實作 Optuna 超參數優化
- **補齊**: 參數範圍驗證 + 過擬合檢測 + 雙引擎對比測試

### 變更6: 測試覆蓋率100%
- **提升**: 從 80-90% → 100%
- **新增**: 7 個單元測試文件 + 6 個整合測試文件
- **策略**: Mock外部依賴 + 邊界測試 + 異常測試

### 變更7: 前端獨立性設計
- **原則**: `/optimization/*` 完全獨立於 `/model/*`
- **重構**: 舊策略測試UI → 封存或重定向
- **資料遷移**: 提供遷移腳本 (可選)

---

## 🎯 Optuna 重構最終方案 (V0.2)

### 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                     Optuna 優化系統 (V0.2)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Mode 1: Hyperparameter Optimization (模型超參數優化)             │
│  ├─ 目標: 最大化 Validation AUC                                 │
│  ├─ 輸入: 訓練集特徵 + 驗證集特徵                                 │
│  ├─ 搜索空間: LightGBM 9參數 / XGBoost 8參數                    │
│  ├─ 約束: Train-Val Gap < 0.1 (防過擬合)                       │
│  └─ 輸出: best_hyperparameters.json                             │
│                                                                  │
│  Mode 2: Execution Optimization (策略執行參數優化)                │
│  ├─ 目標: 最大化 Expectancy / Sharpe / SQN                     │
│  ├─ 輸入: 模型預測機率 + 價格數據 + ATR                          │
│  ├─ 搜索空間: Entry/Exit Threshold, TP/SL, Position Sizing     │
│  ├─ 回測引擎: VectorizedBacktest (< 0.1s/1000 trades)          │
│  ├─ 約束: MaxDD < -30%, WinRate > 40%                          │
│  └─ 輸出: best_strategy_params.json + backtest_result.json     │
│                                                                  │
│  [Archived] Mode 3: Indicator Optimization (指標參數優化 - 已封存) │
│  └─ 移至: archived/momentum/Optimization/indicator_mode/        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 前端頁面結構

```
frontend/src/app/optimization/
├── hyperparameter/                    # 模型超參數優化 (新增)
│   ├── page.tsx                       # 配置頁面
│   │   ├─ 模型選擇器 (LightGBM/XGBoost)
│   │   ├─ 訓練/驗證集時間範圍
│   │   ├─ 超參數搜索空間配置表格
│   │   ├─ Optuna設定 (Sampler, Trials, Timeout)
│   │   └─ 約束條件 (Train-Val Gap上限)
│   │
│   └── result/[taskId]/page.tsx       # 結果展示
│       ├─ 最佳超參數卡片 (可複製JSON)
│       ├─ Parameter Importance圖表
│       ├─ Optimization History圖表
│       ├─ 過擬合檢查 (Train-Val Gap分佈)
│       └─ Trial比較表
│
├── execution/                         # 策略執行參數優化 (新增)
│   ├── page.tsx                       # 配置頁面
│   │   ├─ 數據源選擇 (選擇已完成的模型訓練)
│   │   ├─ 策略參數搜索空間配置表格
│   │   ├─ 倉位管理方法選擇
│   │   ├─ 優化目標選擇 (Expectancy/Sharpe...)
│   │   ├─ 風險約束配置 (MaxDD, Win Rate)
│   │   ├─ 回測成本設定 (手續費, 滑點)
│   │   └─ Optuna設定 + 多目標開關
│   │
│   └── result/[taskId]/page.tsx       # 結果展示
│       ├─ 最佳策略參數卡片
│       ├─ 績效指標總覽 (Sharpe, Expectancy, SQN, MaxDD...)
│       ├─ 權益曲線圖 (vs Buy & Hold)
│       ├─ 回撤曲線圖
│       ├─ 交易明細表
│       ├─ Pareto前沿圖 (若多目標)
│       └─ 導出功能 (JSON/CSV/PNG)
│
└── [Archived] indicator-tuning/       # 指標參數優化 (已封存)
    └── 移至: archived_frontend/optimization/indicator-tuning/
```

### 後端 API 端點

```
POST /api/v1/optimization/hyperparameter
  Request: {
    "model_type": "lightgbm",
    "feature_data_path": "features_filtered.csv",
    "train_time_range": {...},
    "val_time_range": {...},
    "search_space": {
      "learning_rate": [0.01, 0.3],
      "num_leaves": [20, 150],
      ...
    },
    "n_trials": 100,
    "sampler": "TPE",
    "constraints": {
      "train_val_gap": 0.1
    }
  }
  Response: {
    "task_id": "hyper_opt_20260214_001",
    "status": "running"
  }

POST /api/v1/optimization/execution
  Request: {
    "model_task_id": "model_train_20260213_005",  # 選擇已完成的模型訓練
    "search_space": {
      "entry_threshold": [0.5, 0.95],
      "stop_loss_atr": [1.0, 5.0],
      ...
    },
    "target_metric": "expectancy",
    "constraints": {
      "max_drawdown": -0.30,
      "win_rate": 0.40
    },
    "n_trials": 100
  }
  Response: {
    "task_id": "exec_opt_20260214_002",
    "status": "running"
  }

WebSocket /ws/optimization/{task_id}
  實時推送: {
    "trial_number": 45,
    "completion_percentage": 45,
    "current_best_value": 0.042,
    "eta_seconds": 180
  }

GET /api/v1/optimization/hyperparameter/{task_id}/result
  Response: {
    "task_id": "...",
    "status": "completed",
    "best_params": {...},
    "metrics": {
      "val_auc": 0.823,
      "train_auc": 0.897,
      "train_val_gap": 0.074
    },
    "trials": [...]
  }

GET /api/v1/optimization/execution/{task_id}/result
  Response: {
    "task_id": "...",
    "best_params": {...},
    "backtest_metrics": {
      "expectancy": 0.045,
      "sharpe_ratio": 1.85,
      "max_drawdown": -0.181,
      ...
    },
    "equity_curve": [...],
    "trades": [...]
  }
```

---

## 📋 新增檔案清單 (V0.2)

### 後端新增

| 檔案路徑 | 功能 | 程式碼行數 (估計) |
|---------|------|------------------|
| `momentum/Optimization/objectives/hyperparameter_objective.py` | 模型超參數優化目標 | ~300 |
| `momentum/Strategy/vectorized_backtest.py` | 向量化回測引擎 | ~600 |
| `momentum/Strategy/performance_metrics.py` | 策略績效指標計算 | ~400 |
| `momentum/Strategy/position_sizing.py` | 倉位管理 (Kelly, Fixed, Probability) | ~150 |
| `momentum/Strategy/risk_manager.py` | 風險管理 (TP/SL/Trailing Stop) | ~200 |
| `api/services/hyperparameter_optimization_service.py` | 超參數優化服務 | ~250 |
| `api/services/execution_optimization_service.py` | 策略執行優化服務 | ~250 |
| `api/routes/hyperparameter_optimization.py` | 超參數優化路由 | ~100 |
| `api/routes/execution_optimization.py` | 執行優化路由 | ~100 |

**總計**: ~2350 行新增程式碼

### 前端新增

| 檔案路徑 | 功能 | 元件數 (估計) |
|---------|------|--------------|
| `frontend/src/app/optimization/hyperparameter/page.tsx` | 超參數優化配置頁 | 1 |
| `frontend/src/app/optimization/hyperparameter/result/[id]/page.tsx` | 超參數優化結果頁 | 1 |
| `frontend/src/app/optimization/execution/page.tsx` | 執行優化配置頁 | 1 |
| `frontend/src/app/optimization/execution/result/[id]/page.tsx` | 執行優化結果頁 | 1 |
| `frontend/src/components/optimization/common/OptunaProgressBar.tsx` | Optuna進度條 | 1 |
| `frontend/src/components/optimization/common/ParameterRangeSlider.tsx` | 參數範圍滑桿 | 1 |
| `frontend/src/components/optimization/hyperparameter/HyperparameterConfigForm.tsx` | 超參數配置表單 | 1 |
| `frontend/src/components/optimization/hyperparameter/ParameterImportanceChart.tsx` | 參數重要性圖表 | 1 |
| `frontend/src/components/optimization/execution/ExecutionConfigForm.tsx` | 執行參數配置表單 | 1 |
| `frontend/src/components/optimization/execution/EquityCurveChart.tsx` | 權益曲線圖 | 1 |
| `frontend/src/components/optimization/execution/ParetoFrontChart.tsx` | Pareto前沿圖 | 1 |
| `frontend/src/store/optimizationStore.ts` | Optuna狀態管理 | 1 |
| `frontend/src/lib/api/optimizationApi.ts` | Optuna API調用 | 1 |

**總計**: ~13 個頁面/元件

### 測試新增 (100% 覆蓋率)

| 測試檔案 | 測試數量 (估計) |
|---------|---------------|
| `tests/momentum/Strategy/test_vectorized_backtest.py` | ~20 |
| `tests/momentum/Strategy/test_performance_metrics.py` | ~50 (12指標 × 4測試) |
| `tests/momentum/Strategy/test_position_sizing.py` | ~15 |
| `tests/momentum/Optimization/test_hyperparameter_objective.py` | ~25 |
| `tests/momentum/Optimization/test_execution_objective.py` | ~20 |
| `tests/integration/test_end_to_end_hyperparameter.py` | ~5 |
| `tests/integration/test_end_to_end_execution.py` | ~5 |

**總計**: ~140 個測試案例

---

## ⏱️ 工作量重新評估 (V0.2)

### V0.1 原始評估
- **總工作量**: 17-23 天
- **階段**: 6 個 Phase

### V0.2 修正評估

| Phase | 任務 | V0.1 估計 | V0.2 估計 | 差異 | 原因 |
|-------|------|----------|----------|------|------|
| **Phase 4.0** | 系統驗證與清理 | - | **1 天** | +1天 | 封存舊程式碼 + 資料遷移 |
| **Phase 4.1** | 模型超參數優化 | - | **3-4 天** | +3-4天 | V0.1 未涵蓋 (新增) |
| **Phase 4.2** | 向量化回測引擎 | 2-3 天 | **2-3 天** | 不變 | 保持 |
| **Phase 4.3** | 策略執行優化整合 | 1-2 天 | **2 天** | +0.5天 | 前端UI增多 |
| **Phase 4.4** | 前端UI完整實作 | 1 天 | **4-5 天** | +3-4天 | 兩套UI (超參數+執行) |
| **Phase 4.5** | 測試100%覆蓋率 | 1-2 天 | **3-4 天** | +2天 | 從90%提升至100% |
| **Total** | | **17-23 天** | **26-32 天** | **+9天** | |

**結論**: V0.2 更全面，但需額外 **9 天**工作量

**建議分期**:
- **Phase 4A (優先)**: Phase 4.1 模型超參數優化 (3-4天)
- **Phase 4B (次要)**: Phase 4.2-4.3 策略執行優化 (4-5天)
- **Phase 4C (收尾)**: Phase 4.4-4.5 前端+測試 (7-9天)

---

## 🎓 業界實踐補充說明 (回應問題3)

### Optuna 在量化金融工作流程中的位置

```
[數據準備階段]
1. 原始數據收集 (K線, Glassnode...)
2. 特徵工程 (Feature Generation)
3. IC 篩選 (Feature Selection)
   ↓
   
[模型訓練階段] ⬅️ **Optuna Hyperparameter Optimization (Phase 4.1)**
4a. LightGBM 訓練 (手動參數) ❌ 不推薦
4b. LightGBM 訓練 + **Optuna 超參數搜索** ✅ 業界標準
   - 搜索空間: learning_rate, num_leaves, max_depth, regularization
   - 目標: 最大化 OOT Validation AUC
   - 約束: Train-Val Gap < 0.1 (防過擬合)
   - 時間: 100 trials × 30秒 = 50分鐘
   ↓
   
[策略開發階段] ⬅️ **Optuna Execution Optimization (Phase 4.2)**
5. 策略參數搜索 (**快速向量化回測**)
   - 搜索空間: Entry Threshold, TP/SL, Position Sizing
   - 目標: 最大化 Expectancy / Sharpe
   - 回測: 向量化 (< 0.1s/trial)
   - 時間: 100 trials × 0.1秒 = 10秒
   ↓
   
[驗證階段] ⬅️ **Phase 5 完整回測系統 (後續)**
6. 完整回測驗證 (**事件驅動回測，高精度**)
   - 用途: 最終驗證 Phase 4 最佳策略
   - 工具: 事件驅動引擎 (模擬訂單簿、滑點、部分成交)
   - 頻率: 僅跑 1-3 次 (最佳策略 + 對照組)
   - 時間: 10-30秒/次
   ↓
   
7. Walk-Forward Analysis (Phase 5)
8. Monte Carlo 模擬 (Phase 5)
9. 壓力測試 (Phase 5)
   ↓
   
[實盤階段]
10. Paper Trading
11. Live Trading
```

### 為何不在完整回測中調參？

| 考量維度 | Optuna + 向量化回測 | 完整回測中調參 |
|---------|-------------------|--------------|
| **速度** | 100 trials < 5分鐘 | 100 trials > 30分鐘 |
| **記憶體** | < 2GB | > 8GB (需模擬訂單簿) |
| **開發效率** | 快速迭代 | 緩慢試錯 |
| **過擬合風險** | 中 (向量化簡化假設) | 高 (精確回測易過擬合參數) |
| **業界採用率** | 95%+ | < 5% |

**結論**: 
- ✅ **推薦**: Optuna 快速搜索 → 完整回測驗證
- ❌ **不推薦**: 跳過 Optuna，直接在完整回測調參

---

## 🔗 與主規格文件的關係

**本文件 (V0.2 補充說明)** 涵蓋:
1. 7 個關鍵問題的詳細回應
2. 新增功能清單
3. 工作量重新評估
4. 業界實踐補充

**主規格文件 (Optuna重構_SPEC.md V0.1)** 涵蓋:
1. 詳細技術規格 (VectorizedBacktest 程式碼)
2. 詳細 API 設計
3. 配置檔案範例
4. 業界參考資料

**下一步動作**:
1. ✅ 審查本補充說明
2. ⏳ 整合回主文件 (Optuna重構_SPEC.md V0.2 正式版)
3. ⏳ 生成 `Optuna重構_PLAN.md` (詳細 Task 清單)

---

**END OF ADDENDUM**
