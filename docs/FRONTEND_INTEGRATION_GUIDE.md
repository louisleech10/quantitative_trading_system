# 前端整合指南 - Phase 3-6 Frontend Integration

> **Date**: 2026-01-11  
> **Author**: Claude  
> **Status**: ✅ 完成實現，待整合測試

## 📋 目錄

1. [整合概述](#整合概述)
2. [後端 API](#後端-api)
3. [前端組件](#前端組件)
4. [完整工作流程](#完整工作流程)
5. [部署與測試](#部署與測試)
6. [故障排除](#故障排除)

---

## 整合概述

### 背景

Phase 3-6 實現了完整的動態指標系統（後端），包括：
- ✅ 動態特徵命名系統
- ✅ Trial 比較工具
- ✅ ML Pipeline 配置（單一/多指標模式）
- ✅ 端到端測試（13+ 測試全部通過）

**問題**：這些強大的後端功能沒有對應的 UI 界面，用戶需要：
- 編寫 Python 腳本調用 `compare_trials()`
- 手動調用 REST API
- 編輯 JSON 配置文件

### 解決方案

創建 4 個前端 React 組件 + 2 個後端 API endpoints，提供完整的視覺化工作流程。

### 架構概覽

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Next.js 15)                        │
├─────────────────────────────────────────────────────────────────┤
│  TrialComparisonPanel.tsx                                       │
│  → 視覺化比較 trials（表格 + 統計）                              │
│  → API: GET /api/v1/optimization/trials/compare                 │
│                                                                  │
│  TrialSelectionDialog.tsx                                       │
│  → 用戶選擇 trial 並填寫理由                                    │
│  → 必填: user_notes, 可選: pipeline_name                        │
│                                                                  │
│  MultiIndicatorConfig.tsx                                       │
│  → 視覺化配置多指標組合                                         │
│  → 支援 EMA + RSI + MACD                                        │
│  → 即時預覽特徵名稱                                             │
│                                                                  │
│  pipeline/page.tsx                                              │
│  → 整合以上 3 個組件的主頁面                                     │
│  → Tab 1: 選擇 Trial → Tab 2: 配置指標                          │
└─────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        後端 API (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  GET /api/v1/optimization/trials/compare                        │
│  → 調用 momentum/Optimization/trial_comparison.py               │
│  → 返回統計、推薦、trial 詳情                                   │
│                                                                  │
│  POST /api/v1/ml-pipeline/create                                │
│  → 調用 MLPipelineConfig.from_user_selection()                  │
│  → 支援單一/多指標模式                                          │
│  → 儲存為 JSON: data_cache/ml_pipelines/{id}.json              │
│                                                                  │
│  GET /api/v1/ml-pipeline/{id}                                   │
│  → 查詢 Pipeline 詳情                                           │
│                                                                  │
│  GET /api/v1/ml-pipeline/list                                   │
│  → 列出所有 Pipelines（分頁支援）                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 後端 API

### 1. Trial Comparison API

#### Endpoint
```
GET /api/v1/optimization/trials/compare
```

#### Query Parameters
| 參數 | 類型 | 必填 | 說明 | 範例 |
|------|------|------|------|------|
| `study_name` | string | ✅ | Optuna Study 名稱 | `momentum_optimization_001` |
| `trial_numbers` | string | ✅ | Trial 編號列表（逗號分隔） | `1,2,3,5,10` |

#### Response
```json
{
  "success": true,
  "data": {
    "best_trial_number": 5,
    "best_value": 0.8532,
    "value_mean": 0.7812,
    "value_std": 0.0521,
    "value_min": 0.6981,
    "value_max": 0.8532,
    "trials": [
      {
        "number": 1,
        "value": 0.7421,
        "state": "COMPLETE",
        "duration_seconds": 125.3,
        "params": {
          "short_period": 5,
          "mid_period": 20,
          "long_period": 60
        },
        "user_attrs": {}
      },
      // ... more trials
    ],
    "recommendation": "Trial #5 建議選擇，因為其分數最高 (0.8532) 且與平均值差距 1.38 個標準差，表現優異。"
  },
  "message": "Successfully compared 5 trials"
}
```

#### Error Responses
| Code | 說明 |
|------|------|
| 400 | `trial_numbers` 格式錯誤或少於 2 個 trials |
| 404 | Study 不存在 |
| 500 | 內部錯誤 |

#### 實現位置
- **路由**: `api/routes/optimization.py` (第 410+ 行)
- **核心邏輯**: `momentum/Optimization/trial_comparison.py::compare_trials()`

---

### 2. ML Pipeline Creation API

#### Endpoint
```
POST /api/v1/ml-pipeline/create
```

#### Request Body
```json
{
  "study_name": "momentum_optimization_001",
  "trial_number": 5,
  "strategy_type": "ema_three_line",
  "pipeline_name": "EMA Strategy v1",  // 可選
  "user_notes": "此 Trial 在回測中表現穩定，separation score 達 0.85，且參數組合合理。",  // 必填，至少 10 字
  "selected_by": "user",  // 預設 "user"
  "use_xgboost_tuning": true,
  "indicators": [  // null = 單一指標模式，有值 = 多指標模式
    {
      "indicator_type": "ema_three_line",
      "params": {
        "short_period": 5,
        "mid_period": 20,
        "long_period": 60,
        "volume_threshold": 1000000
      },
      "data_source": "close"
    },
    {
      "indicator_type": "rsi",
      "params": {
        "period": 14,
        "overbought": 70,
        "oversold": 30
      },
      "data_source": "close"
    }
  ]
}
```

#### Response
```json
{
  "success": true,
  "pipeline_id": "pipeline_momentum_optimization_001_trial5_20260111_143022",
  "message": "Pipeline created successfully in multi_indicator mode",
  "pipeline_summary": {
    "pipeline_id": "pipeline_momentum_optimization_001_trial5_20260111_143022",
    "mode": "multi_indicator",
    "study_name": "momentum_optimization_001",
    "trial_number": 5,
    "strategy_type": "ema_three_line",
    "user_notes": "此 Trial 在回測中表現穩定...",
    "selected_by": "user",
    "use_xgboost_tuning": true,
    "created_at": "20260111_143022",
    "feature_count": 42,
    "indicators": [
      {
        "type": "ema_three_line",
        "data_source": "close",
        "params": {"short_period": 5, "mid_period": 20, "long_period": 60}
      },
      {
        "type": "rsi",
        "data_source": "close",
        "params": {"period": 14, "overbought": 70, "oversold": 30}
      }
    ]
  }
}
```

#### 單一指標模式
如果 `indicators` 為 `null`，系統會：
1. 從 Optuna Trial 載入最佳參數
2. 使用 Trial 的指標類型和參數
3. 自動繼承所有配置

#### 多指標模式
如果 `indicators` 有值，系統會：
1. 忽略 Trial 的指標配置（僅保留 study 元數據）
2. 使用用戶自定義的指標組合
3. 生成動態特徵名稱（collision-free）

#### Error Responses
| Code | 說明 |
|------|------|
| 400 | `user_notes` 少於 10 字、參數錯誤 |
| 404 | Study 或 Trial 不存在 |
| 500 | Pipeline 創建失敗 |

#### 實現位置
- **路由**: `api/routes/ml_pipeline.py`
- **核心邏輯**: `momentum/FeatureEngineering/ml_pipeline_config.py::MLPipelineConfig.from_user_selection()`

---

### 3. Pipeline Detail API

#### Endpoint
```
GET /api/v1/ml-pipeline/{pipeline_id}
```

#### Response
完整的 Pipeline 配置 JSON（包含所有特徵工程、模型訓練設定）。

---

### 4. Pipeline List API

#### Endpoint
```
GET /api/v1/ml-pipeline/list?limit=50&offset=0
```

#### Response
```json
{
  "success": true,
  "data": [
    {
      "pipeline_id": "pipeline_momentum_001_trial5_20260111_143022",
      "study_name": "momentum_optimization_001",
      "trial_number": 5,
      "strategy_type": "ema_three_line",
      "user_notes": "此 Trial 在回測中表現穩定...",
      "selected_by": "user",
      "use_xgboost_tuning": true,
      "feature_count": 42,
      "created_at": "2026-01-11T14:30:22"
    }
    // ... more pipelines
  ],
  "total": 127
}
```

---

## 前端組件

### 1. TrialComparisonPanel

#### 位置
`frontend/src/components/optimization/TrialComparisonPanel.tsx` (320 行)

#### 功能
- ✅ 多選框選擇 trials（預設選中前 5 個）
- ✅ 「比較選中的 Trials」按鈕
- ✅ 統計資訊卡片：Best Trial, Mean, Std, Min, Max
- ✅ 推薦建議顯示（來自後端）
- ✅ Trial 詳情表格：編號、分數、狀態、執行時間、參數
- ✅ 每行有「選擇此 Trial」按鈕
- ✅ CSV 匯出功能

#### API 調用
```typescript
const response = await fetch(
  `/api/v1/optimization/trials/compare?study_name=${studyName}&trial_numbers=${selectedTrials.join(',')}`
);
```

#### Props
```typescript
interface Props {
  studyName: string;
  trials: TrialInfo[];  // 所有可用的 trials
  onTrialSelect: (trialNumber: number) => void;
}
```

#### 使用範例
```tsx
<TrialComparisonPanel
  studyName="momentum_optimization_001"
  trials={allTrials}
  onTrialSelect={(num) => {
    setSelectedTrial(num);
    openDialog();
  }}
/>
```

---

### 2. TrialSelectionDialog

#### 位置
`frontend/src/components/optimization/TrialSelectionDialog.tsx` (220 行)

#### 功能
- ✅ Dialog 顯示選中的 trial 資訊
- ✅ 必填欄位：`user_notes`（至少 10 字）
- ✅ 可選欄位：`pipeline_name`, `selected_by`
- ✅ Checkbox：`use_xgboost_tuning`
- ✅ 提交驗證（user_notes 不得為空）
- ✅ 提交後調用 ML Pipeline API

#### API 調用
```typescript
const response = await fetch('/api/v1/ml-pipeline/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    study_name: studyName,
    trial_number: selectedTrial.number,
    strategy_type: strategyType,
    pipeline_name: pipelineName,
    user_notes: userNotes,
    selected_by: selectedBy,
    use_xgboost_tuning: useXGBoost,
    indicators: null  // 單一指標模式
  })
});
```

#### Props
```typescript
interface Props {
  open: boolean;
  onClose: () => void;
  studyName: string;
  selectedTrial: TrialInfo | null;
  strategyType: string;
  onSuccess: (pipelineId: string) => void;
}
```

#### 使用範例
```tsx
<TrialSelectionDialog
  open={dialogOpen}
  onClose={() => setDialogOpen(false)}
  studyName="momentum_optimization_001"
  selectedTrial={selectedTrial}
  strategyType="ema_three_line"
  onSuccess={(pipelineId) => {
    router.push(`/ml-pipeline/${pipelineId}`);
  }}
/>
```

---

### 3. MultiIndicatorConfig

#### 位置
`frontend/src/components/optimization/MultiIndicatorConfig.tsx` (330 行)

#### 功能
- ✅ 動態新增/移除指標（Plus/Trash 按鈕）
- ✅ 指標類型下拉選單：EMA, RSI, MACD
- ✅ 資料來源下拉選單：close, open, high, low, volume, taker_ratio
- ✅ 參數輸入（根據指標類型動態顯示）
- ✅ 「預覽特徵名稱」按鈕
- ✅ 顯示 collision-free 特徵數量
- ✅ 返回配置供父組件使用

#### 指標配置範例

**EMA Three Line**:
```json
{
  "indicator_type": "ema_three_line",
  "params": {
    "short_period": 5,
    "mid_period": 20,
    "long_period": 60,
    "volume_threshold": 1000000
  },
  "data_source": "close"
}
```

**RSI**:
```json
{
  "indicator_type": "rsi",
  "params": {
    "period": 14,
    "overbought": 70,
    "oversold": 30
  },
  "data_source": "close"
}
```

**MACD**:
```json
{
  "indicator_type": "macd",
  "params": {
    "fast_period": 12,
    "slow_period": 26,
    "signal_period": 9
  },
  "data_source": "close"
}
```

#### 特徵名稱預覽
點擊「預覽特徵名稱」後顯示：
```
特徵名稱預覽 (collision-free):
  close_ema5_value
  close_ema20_value
  close_ema60_value
  close_rsi14_value
  close_rsi14_70_signal
  close_rsi14_30_signal
  close_macd12_26_9_macd
  close_macd12_26_9_signal
  ...
  
總計: 42 個特徵（無衝突）
```

#### Props
```typescript
interface Props {
  onChange: (indicators: IndicatorConfig[]) => void;
}
```

#### 使用範例
```tsx
<MultiIndicatorConfig
  onChange={(indicators) => {
    setConfiguredIndicators(indicators);
  }}
/>
```

---

### 4. Pipeline Configuration Page

#### 位置
`frontend/src/app/optimization-result/[taskId]/pipeline/page.tsx` (330 行)

#### 功能
- ✅ 麵包屑導航：首頁 > 優化任務 > Task #{taskId} > Pipeline 配置
- ✅ 優化結果摘要卡片
- ✅ 兩個 Tab:
  - **Tab 1: 選擇 Trial** - 整合 `TrialComparisonPanel`
  - **Tab 2: 配置指標** - 單一/多指標模式切換
- ✅ 單一指標模式：繼承 Trial 參數（顯示說明）
- ✅ 多指標模式：整合 `MultiIndicatorConfig`
- ✅ 提交後顯示成功訊息
- ✅ 3 秒後自動跳轉到 `/ml-pipeline/{pipeline_id}`

#### 完整工作流程

```
用戶進入頁面
    ↓
載入優化結果（study_name, trials）
    ↓
Tab 1: 選擇 Trial
    ↓
TrialComparisonPanel 顯示所有 trials
    ↓
用戶多選並點擊「比較」
    ↓
顯示統計資訊、推薦
    ↓
用戶點擊「選擇此 Trial」
    ↓
TrialSelectionDialog 彈出
    ↓
用戶填寫 user_notes（必填）
    ↓
【選項 A】直接提交（單一指標模式）
    ↓
    API: POST /ml-pipeline/create (indicators=null)
    ↓
    成功 → 跳轉到 Pipeline 詳情頁
    
【選項 B】切換到 Tab 2（多指標模式）
    ↓
    MultiIndicatorConfig 顯示
    ↓
    用戶新增指標（EMA, RSI, MACD）
    ↓
    配置參數、資料來源
    ↓
    預覽特徵名稱
    ↓
    提交
    ↓
    API: POST /ml-pipeline/create (indicators=[...])
    ↓
    成功 → 跳轉到 Pipeline 詳情頁
```

#### Route 路徑
```
/optimization-result/[taskId]/pipeline
```

#### URL 範例
```
http://localhost:3000/optimization-result/task_20260110_123456/pipeline
```

---

## 完整工作流程

### Scenario 1: 單一指標 Pipeline

```
1. 用戶完成優化任務 → 進入 /optimization-result/{taskId}
   
2. 點擊「配置 Pipeline」按鈕 → 跳轉到 /optimization-result/{taskId}/pipeline
   
3. Tab 1: 選擇 Trial
   - TrialComparisonPanel 顯示所有 trials
   - 用戶選中 trials 1, 2, 3, 5, 10
   - 點擊「比較選中的 Trials」
   
4. 後端 API 調用
   GET /api/v1/optimization/trials/compare?study_name=momentum_001&trial_numbers=1,2,3,5,10
   
5. 前端顯示統計資訊
   - Best Trial: #5 (score: 0.8532)
   - Mean: 0.7812, Std: 0.0521
   - Recommendation: "Trial #5 建議選擇..."
   
6. 用戶點擊 Trial #5 的「選擇此 Trial」按鈕
   
7. TrialSelectionDialog 彈出
   - 自動填入 pipeline_name: "EMA Strategy (Trial 5)"
   - 用戶填寫 user_notes: "穩定性高，參數合理，separation score 達 0.85"
   - 勾選 use_xgboost_tuning
   - 點擊「確認創建」
   
8. 後端 API 調用
   POST /api/v1/ml-pipeline/create
   {
     "study_name": "momentum_001",
     "trial_number": 5,
     "strategy_type": "ema_three_line",
     "user_notes": "穩定性高...",
     "indicators": null  // 單一指標模式
   }
   
9. 後端處理
   - 載入 Trial #5 的參數
   - 創建 MLPipelineConfig（單一指標）
   - 儲存為 JSON: data_cache/ml_pipelines/pipeline_momentum_001_trial5_20260111_143022.json
   
10. 前端接收響應
    - 顯示成功訊息
    - 3 秒後跳轉到 /ml-pipeline/pipeline_momentum_001_trial5_20260111_143022
```

### Scenario 2: 多指標 Pipeline

```
1-7. 同 Scenario 1（選擇 Trial）

8. 用戶在 TrialSelectionDialog 中點擊「取消」

9. 切換到 Tab 2: 配置指標
   - 選擇「多指標組合模式」
   
10. MultiIndicatorConfig 顯示
    - 點擊「+ 新增指標」
    - 選擇 EMA Three Line, data_source: close
    - 填入參數: short=5, mid=20, long=60
    
11. 再次點擊「+ 新增指標」
    - 選擇 RSI, data_source: close
    - 填入參數: period=14, overbought=70, oversold=30
    
12. 再次點擊「+ 新增指標」
    - 選擇 MACD, data_source: close
    - 填入參數: fast=12, slow=26, signal=9
    
13. 點擊「預覽特徵名稱」
    - 顯示 42 個 collision-free 特徵
    
14. 點擊「提交配置」
    
15. 後端 API 調用
    POST /api/v1/ml-pipeline/create
    {
      "study_name": "momentum_001",
      "trial_number": 5,
      "strategy_type": "ema_three_line",
      "user_notes": "多指標組合測試",
      "indicators": [
        {"indicator_type": "ema_three_line", "data_source": "close", "params": {...}},
        {"indicator_type": "rsi", "data_source": "close", "params": {...}},
        {"indicator_type": "macd", "data_source": "close", "params": {...}}
      ]
    }
    
16. 後端處理
    - 忽略 Trial #5 的指標配置
    - 使用用戶自定義的 3 個指標
    - 創建 FeatureEngineeringConfig（多指標）
    - 生成 42 個動態特徵名稱
    - 儲存 Pipeline
    
17. 前端接收響應
    - 顯示「Pipeline 創建成功（多指標模式，42 個特徵）」
    - 3 秒後跳轉到 Pipeline 詳情頁
```

---

## 部署與測試

### 1. 啟動後端 API

```bash
cd /Users/louis/Desktop/quantitative_trading_system
python run_api.py
```

啟動成功後應看到：
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000
```

### 2. 啟動前端

```bash
cd /Users/louis/Desktop/quantitative_trading_system/frontend
npm run dev
```

啟動成功後應看到：
```
▲ Next.js 15.x.x
- Local:        http://localhost:3000
- Environments: .env.local

✓ Ready in 2.3s
```

### 3. 檢查 API 文檔

訪問 `http://localhost:8000/api/v1/docs`，確認以下 endpoints 存在：

- ✅ `GET /api/v1/optimization/trials/compare`
- ✅ `POST /api/v1/ml-pipeline/create`
- ✅ `GET /api/v1/ml-pipeline/{pipeline_id}`
- ✅ `GET /api/v1/ml-pipeline/list`

### 4. 執行整合測試

```bash
cd /Users/louis/Desktop/quantitative_trading_system
python test_frontend_integration.py
```

測試項目：
1. ✅ Trial 比較 API
2. ✅ 創建單一指標 Pipeline
3. ✅ 創建多指標 Pipeline
4. ✅ 查詢 Pipeline 詳情
5. ✅ 列出所有 Pipelines

預期輸出：
```
✅ PASSED - trial_comparison
✅ PASSED - single_indicator_pipeline
✅ PASSED - multi_indicator_pipeline
✅ PASSED - pipeline_detail
✅ PASSED - pipeline_list

總計: 5/5 測試通過 (100.0%)
🎉 所有測試通過！前端整合功能正常運作。
```

### 5. 手動前端測試

1. 訪問 `http://localhost:3000`
2. 進入已完成的優化任務（例如 `http://localhost:3000/optimization-result/task_20260110_123456`）
3. 點擊右上角「配置 Pipeline」按鈕
4. 驗證以下功能：
   - ✅ TrialComparisonPanel 正常顯示
   - ✅ 多選 trials 並比較
   - ✅ 統計資訊正確顯示
   - ✅ 點擊「選擇此 Trial」彈出 Dialog
   - ✅ 填寫 user_notes 並提交
   - ✅ 切換到多指標模式
   - ✅ 新增/移除指標正常
   - ✅ 預覽特徵名稱正確
   - ✅ 提交成功並跳轉

---

## 故障排除

### 問題 1: API 調用 404 Not Found

**症狀**:
```
GET /api/v1/optimization/trials/compare → 404
```

**原因**: 路由未註冊或 API 服務未啟動

**解決方案**:
1. 確認 `api/main.py` 中已導入 `ml_pipeline` 模組
2. 檢查 `api/routes/optimization.py` 中是否有 `compare_optimization_trials` 函式
3. 重啟 API 服務: `python run_api.py`

---

### 問題 2: Study 不存在

**症狀**:
```json
{
  "detail": "Study 'momentum_optimization_001' not found"
}
```

**原因**: Study 檔案不存在於 `results/` 目錄

**解決方案**:
1. 確認 Study 名稱正確（大小寫敏感）
2. 檢查 `results/` 目錄下是否有對應的 `.db` 文件
3. 執行一次完整的優化任務創建 Study

---

### 問題 3: Trial 編號不存在

**症狀**:
```json
{
  "detail": "Trial #99 not found in study 'momentum_optimization_001'"
}
```

**原因**: 指定的 Trial 編號不存在

**解決方案**:
1. 使用 `GET /api/v1/optimization/tasks/{task_id}/result` 查詢可用的 trials
2. 確認 trial_numbers 在合法範圍內（從 0 或 1 開始）
3. 檢查 trials 是否為 COMPLETE 狀態

---

### 問題 4: user_notes 驗證失敗

**症狀**:
```json
{
  "detail": [
    {
      "loc": ["body", "user_notes"],
      "msg": "ensure this value has at least 10 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**原因**: `user_notes` 少於 10 個字符

**解決方案**:
- 在前端表單加入驗證：`user_notes.length >= 10`
- 提示用戶填寫詳細的選擇理由

---

### 問題 5: 多指標配置錯誤

**症狀**:
```json
{
  "detail": "Invalid indicator configuration: Missing required parameter 'period' for RSI"
}
```

**原因**: 指標參數不完整或錯誤

**解決方案**:
1. 檢查 `MultiIndicatorConfig` 的參數驗證邏輯
2. 確認所有必填參數都已填入
3. 參考 `momentum/Analysis/strategy_registry.py` 中的參數定義

---

### 問題 6: Pipeline 文件無法寫入

**症狀**:
```
PermissionError: [Errno 13] Permission denied: 'data_cache/ml_pipelines/pipeline_xxx.json'
```

**原因**: 權限不足或目錄不存在

**解決方案**:
```bash
mkdir -p data_cache/ml_pipelines
chmod 755 data_cache/ml_pipelines
```

---

### 問題 7: 前端組件未顯示

**症狀**: 頁面空白或 404

**原因**: Route 未註冊或組件導入失敗

**解決方案**:
1. 檢查 `frontend/src/app/optimization-result/[taskId]/pipeline/page.tsx` 是否存在
2. 確認所有組件已正確導入（沒有語法錯誤）
3. 檢查瀏覽器 Console 是否有錯誤訊息
4. 重啟 Next.js: `npm run dev`

---

## 下一步計劃

### 短期（1 週內）

1. **Pipeline 詳情頁**
   - 創建 `/ml-pipeline/{id}` 頁面
   - 顯示完整配置、特徵列表
   - 提供「開始訓練」按鈕

2. **Pipeline 列表頁**
   - 創建 `/ml-pipelines` 頁面
   - 表格顯示所有 Pipelines
   - 支援搜尋、過濾、分頁

3. **特徵重要性視覺化**
   - 訓練完成後顯示 SHAP values
   - 互動式特徵重要性圖表

### 中期（2-4 週）

4. **即時訓練進度**
   - WebSocket 連接顯示訓練進度
   - 即時 loss/accuracy 曲線

5. **模型比較頁面**
   - 並排比較多個 Pipelines
   - 性能指標對比表

6. **A/B 測試框架**
   - 創建對照組/實驗組
   - 統計顯著性檢驗

### 長期（1-2 個月）

7. **自動化推薦系統**
   - 基於歷史數據推薦最佳指標組合
   - 智能參數調優建議

8. **模板管理**
   - 保存常用配置為模板
   - 一鍵應用模板

---

## 文件更新記錄

| 日期 | 版本 | 變更內容 | 作者 |
|------|------|----------|------|
| 2026-01-11 | 1.0 | 初始版本，記錄 Phase 3-6 前端整合 | Claude |

---

## 相關文檔

- [DYNAMIC_INDICATOR_SYSTEM_GUIDE.md](./DYNAMIC_INDICATOR_SYSTEM_GUIDE.md) - 動態指標系統指南（後端）
- [PHASE3_6_COMPLETION_REPORT.md](./PHASE3_6_COMPLETION_REPORT.md) - Phase 3-6 完成報告
- [API_SPECIFICATION.md](./API_SPECIFICATION.md) - API 規格文檔
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系統架構文檔

---

## 總結

Phase 3-6 Frontend Integration 成功將後端的動態指標系統與前端 UI 整合，提供完整的視覺化工作流程。用戶現在可以：

- ✅ 視覺化比較 Optuna trials
- ✅ 基於數據做出 informed trial 選擇
- ✅ 配置單一或多指標組合
- ✅ 即時預覽特徵名稱
- ✅ 創建並管理 ML Pipelines

這標誌著系統從「開發者工具」演進為「用戶友好平台」的重要里程碑。

---

**維護者**: Claude  
**最後更新**: 2026-01-11  
**狀態**: ✅ 完成實現，待整合測試
