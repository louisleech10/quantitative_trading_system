# API 端點規範

## 文檔資訊
- **版本**: 3.0
- **最後更新**: 2026-02-08
- **Base URL**: `http://localhost:8000`（開發環境）
- **API Prefix**: `/api/v1`
- **變更記錄**:
  - v3.0 (2026-02-08): 同步 REFACTOR_ARCHITECTURE_V4；完整收錄 13 個路由模組、85+ 端點；新增 Feature Engineering / Pattern Analysis / Pattern Management / ML Pipeline / Two-Stage Search API；更新數據模型與錯誤碼
  - v2.0 (2026-01-09): 新增 Phase 3 API（Optuna 優化、信號分析、WebSocket）
  - v1.1 (2025-12-06): 新增 SignalDensityResponse 零值統計欄位
  - v1.0 (2025-09-30): 初始版本

---

## 目錄
1. [通用規範](#通用規範)
2. [Case Search API](#1-case-search-api)
3. [Case Management API](#2-case-management-api)
4. [Chart Data API](#3-chart-data-api)
5. [Chart Signals API](#4-chart-signals-api)
6. [Configuration API](#5-configuration-api)
7. [Signal Analysis API](#6-signal-analysis-api)
8. [Optimization API (Core)](#7-optimization-api-core)
9. [Optimization Analysis API](#8-optimization-analysis-api)
10. [Feature Engineering API](#9-feature-engineering-api)
11. [Pattern Analysis API (XGBoost)](#10-pattern-analysis-api-xgboost)
12. [Pattern Management API](#11-pattern-management-api)
13. [ML Pipeline API](#12-ml-pipeline-api)
14. [Two-Stage Search API](#13-two-stage-search-api)
15. [WebSocket API](#websocket-api)
16. [錯誤處理](#錯誤處理)
17. [數據模型](#數據模型)

---

## 通用規範

### 請求格式
```
Content-Type: application/json
Accept: application/json
```

### 響應格式
所有端點回傳 JSON。大部分遵循以下格式：
```json
{
  "success": true,
  "data": { },
  "error": null
}
```

### HTTP 狀態碼
| 狀態碼 | 說明 |
|--------|------|
| `200` | 請求成功 |
| `201` | 建立成功 |
| `202` | 已接受（非同步任務已啟動） |
| `400` | 請求參數錯誤 |
| `404` | 資源不存在 |
| `422` | 驗證失敗 |
| `500` | 伺服器內部錯誤 |

### Router 註冊對照表

| 路由模組 | Prefix | Tags |
|----------|--------|------|
| `case_search` | `/api/v1/search` | Case Search |
| `case` | `/api/v1` | Case Management |
| `chart` | `/api/v1/chart` | Chart Data |
| `chart_signals` | `/api/v1/chart` | Chart Signals |
| `config` | `/api/v1/config` | Configuration |
| `signal_analysis` | `/api/v1/signal-analysis` | Signal Analysis |
| `optimization` | `/api/v1/optimization` | Optimization |
| `optimization_analysis` | `/api/v1/optimization` | Optimization Analysis |
| `feature_engineering` | `/api/v1/features` | Feature Engineering |
| `pattern_analysis` | `/api/v1/pattern-analysis` | Pattern Analysis |
| `pattern_management` | `/api/v1/patterns` | Pattern Management |
| `ml_pipeline` | `/api/v1/ml-pipeline` | ML Pipeline |
| `two_stage_search` | `/api/v1/two-stage` | Two-Stage Search |

---

## 1. Case Search API

> **路由**: `api/routes/case_search.py` | **Prefix**: `/api/v1/search`

### 1.1 執行搜索
```http
POST /api/v1/search/execute
```

**Request Body** (`SearchConfigRequest`):
```json
{
  "timeframe": "12h",
  "startDate": "2024-01-01",
  "endDate": "2024-12-31",
  "timeRange": "2024-01-01_2024-12-31",
  "conditions": [
    {
      "parameter": "price_change",
      "operator": ">=",
      "value": 5.0,
      "condition_type": "trigger"
    }
  ],
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

**Response** (`TaskStartResponse`):
```json
{
  "task_id": "uuid",
  "status": "pending",
  "message": "搜索任務已建立"
}
```

### 1.2 預覽搜索
```http
POST /api/v1/search/preview
```
快速預覽搜索結果（限制筆數），回傳 `SearchPreviewResponse`。

### 1.3 查詢任務狀態
```http
GET /api/v1/search/task/{task_id}
```

**Response** (`TaskStatusResponse`):
```json
{
  "task_id": "uuid",
  "status": "running",
  "progress": {
    "current_step": 50,
    "total_steps": 200,
    "percentage": 0.25,
    "current_symbol": "BTCUSDT"
  }
}
```

### 1.4 取得任務結果
```http
GET /api/v1/search/task/{task_id}/result
```
回傳 `SearchResponse`，包含完整案例列表與統計摘要。

### 1.5 取消任務
```http
POST /api/v1/search/task/{task_id}/cancel
```

### 1.6 列出搜索任務
```http
GET /api/v1/search/tasks
```
回傳 `TaskListResponse`。

### 1.7 清理舊任務
```http
DELETE /api/v1/search/tasks/cleanup
```

### 1.8 健康檢查
```http
GET /api/v1/search/health
```

---

## 2. Case Management API

> **路由**: `api/routes/case.py` | **Prefix**: `/api/v1`

### 2.1 匯入案例
```http
POST /api/v1/case/import
Content-Type: multipart/form-data
```
上傳 CSV 或 Excel 檔案，回傳 `CaseImportResponse`。

### 2.2 案例列表
```http
GET /api/v1/case/list
```
回傳 `CaseListResponse`。

### 2.3 案例數量
```http
GET /api/v1/case/count
```

### 2.4 清除所有案例
```http
DELETE /api/v1/case/clear-all
```

### 2.5 批量 K 線下載
```http
POST /api/v1/kline/batch-download
```

**Request Body** (`BatchDownloadRequest`):
```json
{
  "case_ids": ["uuid1", "uuid2"],
  "timeframe": "12h",
  "warmup_bars": 240
}
```

### 2.6 查詢下載進度
```http
GET /api/v1/kline/download-status/{task_id}
```

**Response** (`DownloadProgress`):
```json
{
  "task_id": "uuid",
  "status": "running",
  "progress": 0.65,
  "downloaded": 130,
  "total": 200,
  "errors": []
}
```

---

## 3. Chart Data API

> **路由**: `api/routes/chart.py` | **Prefix**: `/api/v1/chart`

### 3.1 取得圖表數據
```http
GET /api/v1/chart/data
```

**Query Parameters**:
| 參數 | 類型 | 說明 |
|------|------|------|
| `symbol` | string | 交易對（必填） |
| `timeframe` | string | 時間框架（必填） |
| `center_index` | int | 中心索引（舊邏輯） |
| `case_timeframe` | string | 案例時間框架（TO/TC 新邏輯） |
| `indicator_type` | string | 指標類型 (可選) |
| `data_source` | string | 數據源 (可選) |
| `strategy_logic` | string | 策略邏輯 (可選) |
| `short_period` | int | 短週期 (可選) |
| `mid_period` | int | 中週期 (可選) |
| `long_period` | int | 長週期 (可選) |

**Response**: K 線數據 + 可選指標計算結果。

---

## 4. Chart Signals API

> **路由**: `api/routes/chart_signals.py` | **Prefix**: `/api/v1/chart`

### 4.1 計算圖表信號
```http
POST /api/v1/chart/signals
```

**Request Body** (`ChartSignalCalculationRequest`):
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "12h",
  "data_source": "close",
  "indicator_type": "ema",
  "strategy_logic": "short_long_cross",
  "params": {
    "short_period": 7,
    "long_period": 25
  }
}
```

**Response** (`ChartSignalCalculationResponse`):
```json
{
  "signals": [
    {
      "timestamp": 1704067200000,
      "type": "buy",
      "price": 42500.0,
      "indicator_values": {"ema_short": 42300, "ema_long": 42100}
    }
  ],
  "strategy_name": "close_ema_short_long_cross",
  "total_signals": 25
}
```

### 4.2 驗證策略配置
```http
POST /api/v1/chart/validate-strategy
```
回傳 `StrategyConfigValidationResponse`。

---

## 5. Configuration API

> **路由**: `api/routes/config.py` | **Prefix**: `/api/v1/config`

### 5.1 範本 CRUD
```http
GET    /api/v1/config/templates                    # 取得所有範本
GET    /api/v1/config/templates/{template_name}     # 取得指定範本
POST   /api/v1/config/templates                    # 建立新範本
PUT    /api/v1/config/templates/{template_name}     # 更新範本
DELETE /api/v1/config/templates/{template_name}     # 刪除範本
```

### 5.2 系統設定
```http
GET   /api/v1/config/system     # 取得系統設定
PATCH /api/v1/config/system     # 更新系統設定
```

### 5.3 驗證與統計
```http
GET /api/v1/config/validation/symbols   # 驗證標的列表
GET /api/v1/config/stats                # 系統統計
```

---

## 6. Signal Analysis API

> **路由**: `api/routes/signal_analysis.py` | **Prefix**: `/api/v1/signal-analysis`

### 6.1 計算信號密度
```http
POST /api/v1/signal-analysis/density
```

**Request Body** (`SignalDensityRequest`):
```json
{
  "case_id": "uuid",
  "strategy_config": {
    "data_source": "close",
    "indicator_type": "ema",
    "strategy_logic": "short_long_cross",
    "params": {"short_period": 7, "mid_period": 18, "long_period": 35}
  },
  "training_window": {
    "reference_point": "TO",
    "lookback_bars": 24,
    "lookforward_bars": 0,
    "far_lookback_bars": 48
  }
}
```

**Response** (`SignalDensityResponse`): 見[數據模型](#signaldensityresponse)章節。

### 6.2 預覽訓練視窗
```http
POST /api/v1/signal-analysis/preview-window
```
用於除錯的訓練視窗預覽。

---

## 7. Optimization API (Core)

> **路由**: `api/routes/optimization.py` | **Prefix**: `/api/v1/optimization`

### 7.1 建立優化任務
```http
POST /api/v1/optimization/tasks
```

**Request Body**: 包含參數空間、優化配置（sampler、n_trials、timeout）等。

### 7.2 啟動優化任務
```http
POST /api/v1/optimization/tasks/{task_id}/start
```

### 7.3 查詢任務狀態
```http
GET /api/v1/optimization/tasks/{task_id}
```

**Response**:
```json
{
  "task_id": "uuid",
  "status": "running",
  "progress": 0.75,
  "current_trial": 225,
  "total_trials": 300,
  "best_value": 0.35,
  "best_params": {"ema_short": 7, "ema_mid": 18, "ema_long": 35}
}
```

### 7.4 列出所有任務
```http
GET /api/v1/optimization/tasks
```

### 7.5 取消任務
```http
POST /api/v1/optimization/tasks/{task_id}/cancel
```

### 7.6 列出策略
```http
GET /api/v1/optimization/strategies
```

### 7.7 策略詳情
```http
GET /api/v1/optimization/strategies/{strategy_id}
```

### 7.8 試驗對比
```http
GET /api/v1/optimization/trials/compare
```

---

## 8. Optimization Analysis API

> **路由**: `api/routes/optimization_analysis.py` | **Prefix**: `/api/v1/optimization`

### 8.1 參數重要性 (FANOVA/MDI)
```http
GET /api/v1/optimization/tasks/{task_id}/analysis/importance
```

### 8.2 優化歷史曲線
```http
GET /api/v1/optimization/tasks/{task_id}/analysis/history
```

### 8.3 參數空間散佈圖
```http
GET /api/v1/optimization/tasks/{task_id}/analysis/param-space
```

### 8.4 2D 參數熱力圖
```http
GET /api/v1/optimization/tasks/{task_id}/analysis/heatmap
```

### 8.5 收斂偵測
```http
GET /api/v1/optimization/tasks/{task_id}/analysis/convergence
```

### 8.6 穩定性分析（按執行時間）
```http
GET /api/v1/optimization/tasks/{task_id}/analysis/stability
```

### 8.7 穩定性分析（按案例月份）
```http
GET /api/v1/optimization/tasks/{task_id}/analysis/stability-by-case-month
```

### 8.8 Top N Trials
```http
GET /api/v1/optimization/tasks/{task_id}/trials
```

### 8.9 完整優化結果
```http
GET /api/v1/optimization/tasks/{task_id}/result
```

---

## 9. Feature Engineering API

> **路由**: `api/routes/feature_engineering.py` | **Prefix**: `/api/v1/features`

### 9.1 啟動特徵擷取
```http
POST /api/v1/features/extract
```

**Request Body** (`FeatureExtractionRequest`):
```json
{
  "case_id": "uuid",
  "feature_config": {
    "indicator_features": ["ema", "rsi", "macd"],
    "multi_scale_windows": [6, 12, 24],
    "sequence_features": true
  }
}
```

**Response** (202 Accepted):
```json
{
  "task_id": "uuid",
  "status": "accepted"
}
```

### 9.2 查詢任務狀態
```http
GET /api/v1/features/task/{task_id}
```
回傳 `FeatureTaskStatusResponse`。

### 9.3 取得特徵統計
```http
GET /api/v1/features/summary/{case_id}
```
回傳 `FeatureSummaryResponse`（包含特徵統計、相關性對）。

### 9.4 健康檢查
```http
GET /api/v1/features/health
```

---

## 10. Pattern Analysis API (XGBoost)

> **路由**: `api/routes/pattern_analysis.py` | **Prefix**: `/api/v1/pattern-analysis`

### 10.1 啟動 XGBoost 分析（單案例）
```http
POST /api/v1/pattern-analysis/xgboost/start
```

**Request Body** (`XGBoostAnalysisRequest`):
```json
{
  "case_id": "uuid",
  "indicator_params": {
    "data_source": "close",
    "indicator_type": "ema",
    "strategy_logic": "short_long_cross"
  },
  "multi_scale_windows": [6, 12, 24],
  "sequence_features": true,
  "purged_cv_folds": 5
}
```

### 10.2 啟動批量 XGBoost 分析
```http
POST /api/v1/pattern-analysis/xgboost/batch/start
```

**Request Body** (`XGBoostBatchAnalysisRequest`):
```json
{
  "case_ids": ["uuid1", "uuid2", "uuid3"],
  "indicator_params": {},
  "multi_scale_windows": [6, 12, 24]
}
```

### 10.3 查詢任務狀態
```http
GET /api/v1/pattern-analysis/xgboost/task/{task_id}          # 單任務
GET /api/v1/pattern-analysis/xgboost/batch/task/{task_id}     # 批量任務
```

### 10.4 OOT 驗證
```http
POST /api/v1/pattern-analysis/xgboost/validate-oot
```

### 10.5 預測結果
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/predictions
```

### 10.6 特徵重要性
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/feature-importance
```

### 10.7 機率密度
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/probability-density
```

### 10.8 策略權益曲線
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/strategy-equity
```

### 10.9 Top 假陽性
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/top-false-positives
```

### 10.10 滾動 AUC
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/rolling-auc
```

### 10.11 校準曲線
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/calibration-curve
```

### 10.12 PR 曲線
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/pr-curve
```

### 10.13 SHAP 全域分析
```http
POST /api/v1/pattern-analysis/xgboost/{task_id}/shap
```

### 10.14 SHAP 單案例
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/shap/case/{case_id}
```

### 10.15 漂移報告 (PSI)
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/drift-report
```

### 10.16 市場情境分析
```http
GET /api/v1/pattern-analysis/xgboost/{task_id}/regime-analysis
```

### 10.17 案例摘要
```http
GET /api/v1/pattern-analysis/cases/summary
```

### 10.18 模型資訊
```http
GET /api/v1/pattern-analysis/model/info/{case_id}
GET /api/v1/pattern-analysis/model/list
GET /api/v1/pattern-analysis/model/exists/{case_id}
```

---

## 11. Pattern Management API

> **路由**: `api/routes/pattern_management.py` | **Prefix**: `/api/v1/patterns`

### 11.1 建立 Pattern
```http
POST /api/v1/patterns/define
```

**Request Body** (`CreatePatternRequest`):
```json
{
  "name": "EMA 金叉 + 成交量放大",
  "description": "短線金叉搭配量能突破",
  "rules": [
    {
      "indicator": "ema",
      "condition": "short > long",
      "params": {"short_period": 5, "long_period": 20}
    }
  ]
}
```

### 11.2 列出所有 Pattern
```http
GET /api/v1/patterns/list
```

### 11.3 Pattern 統計
```http
GET /api/v1/patterns/statistics
```

### 11.4 取得 Pattern 詳情
```http
GET /api/v1/patterns/{pattern_id}
```

### 11.5 取得 Pattern 摘要
```http
GET /api/v1/patterns/{pattern_id}/summary
```

### 11.6 更新 Pattern
```http
PUT /api/v1/patterns/{pattern_id}
```

### 11.7 刪除 Pattern
```http
DELETE /api/v1/patterns/{pattern_id}
```

### 11.8 刪除所有 Pattern
```http
DELETE /api/v1/patterns/batch/delete-all
```

---

## 12. ML Pipeline API

> **路由**: `api/routes/ml_pipeline.py` | **Prefix**: `/api/v1/ml-pipeline`

### 12.1 從 Optuna Trial 建立 Pipeline
```http
POST /api/v1/ml-pipeline/create
```

### 12.2 取得 Pipeline 詳情
```http
GET /api/v1/ml-pipeline/{pipeline_id}
```

### 12.3 列出所有 Pipeline
```http
GET /api/v1/ml-pipeline/list
```

### 12.4 刪除 Pipeline
```http
DELETE /api/v1/ml-pipeline/{pipeline_id}
```

---

## 13. Two-Stage Search API

> **路由**: `api/routes/two_stage_search.py` | **Prefix**: `/api/v1/two-stage`

### 13.1 啟動正例搜索（階段 1）
```http
POST /api/v1/two-stage/positive
```

### 13.2 啟動反例搜索（階段 2）
```http
POST /api/v1/two-stage/negative/{positive_task_id}
```
基於正例搜索結果，設定反例條件並執行搜索。

### 13.3 取得合併結果
```http
GET /api/v1/two-stage/combined/{positive_task_id}/{negative_task_id}
```

---

## WebSocket API

### 即時優化進度
```
ws://localhost:8000/ws/optimization/{task_id}?client_id={client_id}
```

**連線流程**:
1. Client 連線並傳入 task_id + client_id
2. Server accept，註冊至 `WebSocketConnectionManager`
3. 優化進行時透過 callback 推送 JSON 進度
4. 任務完成/失敗後發送最終狀態
5. 心跳機制（30s ping）防止連線超時

**推送格式**:
```json
{
  "type": "progress",
  "status": "running",
  "progress": 0.45,
  "current_trial": 135,
  "total_trials": 300,
  "best_value": 0.32,
  "best_params": {"ema_short": 7, "ema_mid": 18, "ema_long": 35},
  "milestone": "50%"
}
```

**最終狀態**:
```json
{
  "type": "completed",
  "status": "completed",
  "progress": 1.0,
  "best_value": 0.35,
  "best_params": {}
}
```

---

## 錯誤處理

### 錯誤響應格式
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "人類可讀的錯誤訊息",
    "details": {}
  }
}
```

### 錯誤碼

| 錯誤碼 | 說明 | HTTP 狀態碼 |
|--------|------|------------|
| `INVALID_PARAMS` | 請求參數錯誤 | 400 |
| `RESOURCE_NOT_FOUND` | 資源不存在 | 404 |
| `TASK_FAILED` | 任務執行失敗 | 500 |
| `TASK_NOT_FOUND` | 任務 ID 不存在 | 404 |
| `TASK_ALREADY_RUNNING` | 任務已在執行中 | 409 |
| `RATE_LIMIT_EXCEEDED` | 超過頻率限制 | 429 |
| `INTERNAL_ERROR` | 伺服器內部錯誤 | 500 |
| `DATA_NOT_READY` | 數據未準備好 | 400 |
| `DATA_CONTINUITY_ERROR` | K 線數據不連續 | 400 |
| `INSUFFICIENT_DATA` | 數據量不足 | 400 |
| `MODEL_NOT_FOUND` | 模型不存在 | 404 |
| `INVALID_SYMBOL` | 無效的交易對符號（不可重試） | 400 |
| `NETWORK_ERROR` | 網路錯誤（可重試） | 502 |
| `DOWNLOAD_FAILED` | K 線下載失敗 | 500 |

### 錯誤分類機制
```python
class FailureType(Enum):
    RATE_LIMIT = "rate_limit"    # 可重試（指數退避）
    NETWORK_ERROR = "network"    # 可重試
    INVALID_SYMBOL = "invalid"   # 不可重試
    DATA_ERROR = "data_error"    # 不可重試
```

---

## 數據模型

### CaseData
```typescript
interface CaseData {
  case_id: string;
  symbol: string;
  timestamp: string;            // ISO8601
  timeframe: string;
  label: 0 | 1;                // 0=反例, 1=正例

  // OHLCV
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;

  // 觸發條件
  price_change: number;
  closing_strength: number;
  volume_multiplier: number;
  taker_buy_ratio: number;

  // 未來表現
  future_1bar_return?: number;
  // ... future_2bar_return ~ future_12bar_return
  future_12bar_return?: number;
  future_1bar_max_drawdown?: number;
  // ... future_2bar_max_drawdown ~ future_12bar_max_drawdown
  future_12bar_max_drawdown?: number;

  // 環境
  market_classification?: string;
  hour_of_day?: number;
  day_of_week?: number;
}
```

### EnhancedCaseData
包含 33 個擴充參數（6 基本觸發 + 12 未來報酬 + 12 未來回撤 + 3 時間），用於完整搜索結果。

### SearchConfigRequest
```typescript
interface SearchConfigRequest {
  timeframe: '1h' | '4h' | '12h' | '1d';
  startDate?: string;
  endDate?: string;
  timeRange?: string;        // "YYYY-MM-DD_YYYY-MM-DD"
  conditions: FilterConditionRequest[];
  symbols?: string[];
  price_change_method?: 'close_to_close' | 'low_to_high';
}

interface FilterConditionRequest {
  parameter: string;
  operator: '>=' | '<=' | '>' | '<' | '==' | '!=';
  value: number;
  condition_type: 'trigger' | 'future_return' | 'future_drawdown';
}
```

### TrainingWindowConfig
```typescript
interface TrainingWindowConfig {
  reference_point: 'TO' | 'TC' | 'custom';
  lookback_bars: number;
  lookforward_bars: number;
  far_lookback_bars?: number;    // 雙密度模式
}
```

### StrategyConfig
```typescript
interface StrategyConfig {
  data_source: string;          // 'close' | 'volume' | 'taker_ratio' | ...
  indicator_type: string;       // 'ema' | 'rsi' | 'macd' | ...
  strategy_logic: string;       // 'short_long_cross' | 'mid_long_cross' | ...
  params: Record<string, number>;
}
```

### SignalDensityResponse
```typescript
interface SignalDensityResponse {
  // 核心統計
  positive_avg_density: number;
  negative_avg_density: number;
  separation: number;

  // 雙密度模式 (far_lookback_bars 配置時有效)
  positive_far_avg_density?: number;
  negative_far_avg_density?: number;
  positive_near_far_ratio?: number;
  negative_near_far_ratio?: number;
  ratio_separation?: number;

  // M-value Golden Formula v2.0
  m_value?: number;
  weighted_m_positive?: number;
  weighted_m_negative?: number;

  // 零值統計 (v1.1)
  positive_near_zero_count?: number;
  positive_near_zero_ratio?: number;
  positive_far_zero_count?: number;
  positive_far_zero_ratio?: number;
  negative_near_zero_count?: number;
  negative_near_zero_ratio?: number;
  negative_far_zero_count?: number;
  negative_far_zero_ratio?: number;

  // 統計檢驗
  p_value: number;
  cohens_d: number;
  stability_cv: number;

  // 詳細統計
  positive_std: number;
  negative_std: number;
  positive_sample_size: number;
  negative_sample_size: number;

  // 樣本警告
  sample_warnings?: string[];
}
```

### BatchDownloadRequest
```typescript
interface BatchDownloadRequest {
  case_ids: string[];
  timeframe: string;
  warmup_bars?: number;         // 預設 240
}
```

### XGBoostBatchAnalysisRequest
```typescript
interface XGBoostBatchAnalysisRequest {
  case_ids: string[];
  indicator_params: {
    data_source: string;
    indicator_type: string;
    strategy_logic: string;
    params: Record<string, number>;
  };
  multi_scale_windows?: number[];
  sequence_features?: boolean;
  purged_cv_folds?: number;
}
```

### FeatureExtractionRequest
```typescript
interface FeatureExtractionRequest {
  case_id: string;
  feature_config: {
    indicator_features: string[];
    multi_scale_windows?: number[];
    sequence_features?: boolean;
  };
}
```

### PatternRequest
```typescript
interface CreatePatternRequest {
  name: string;
  description?: string;
  rules: PatternRuleRequest[];
}

interface PatternRuleRequest {
  indicator: string;
  condition: string;
  params: Record<string, any>;
}
```

---

## 開發環境

### 啟動後端
```bash
# 從專案根目錄
python run_api.py
# -> http://localhost:8000

# 或使用 uvicorn
uvicorn api.main:app --reload --port 8000
```

### API 文檔（自動生成）
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 測試工具
```bash
# curl 範例
curl -X POST http://localhost:8000/api/v1/search/execute \
  -H "Content-Type: application/json" \
  -d '{"timeframe": "12h", "conditions": [...]}'

# Python 範例
import requests
resp = requests.post(
    'http://localhost:8000/api/v1/search/execute',
    json={'timeframe': '12h', 'conditions': [...]}
)
```

### 版本策略
- 當前版本：`v1`
- 路徑格式：`/api/v1/{resource}`
- 破壞性變更增加主版本號，新增功能向後相容

---

*文檔版本：3.0*
*最後更新：2026-02-08*
*狀態：REFACTOR_ARCHITECTURE_V4 同步完成*
