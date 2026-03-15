# API 端點規範

## 文檔資訊
- **版本**: 6.0
- **最後更新**: 2026-03-15
- **Base URL**: `http://localhost:8000`（開發環境）
- **API Prefix**: `/api/v1`
- **變更記錄**:
  - v6.0 (2026-03-15): 新增 Feature Factory MultiTF + Batch API（Section 20）- 單標的 generate（含 timeframe 驗證）、多標的 batch 啟動（BatchGenerateRequest）、批次任務查詢（BatchTaskStatusResponse）、WebSocket 批次進度推送；基於 Feature_Factory_MultiTF_MultiSymbol_TODO V7
  - v5.0 (2026-03-08): 新增 Feature Factory Granular Control API（Section 19）- Per-Indicator 細粒度控制 3 個端點（Schema / Batch Toggle / Preset）；基於 FEATURE_FACTORY_GRANULAR_CONTROL_PLAN V1.2
  - v4.0 (2026-02-18): 新增 Model Enhancement API（Section 16）- Phase 3.5 模型增強系統 8 個端點；新增 Hyperparameter Optimization API（Section 17）及 Execution Optimization API（Section 18）- Phase 4 回測系統優化；更新 Router 註冊對照表
  - v3.2 (2026-02-14): 新增 Dual-Engine ML API（Section 15）- Phase 3.7 雙引擎 ML 系統（LightGBM + XGBoost）7 個端點；通用模型訓練、LightGBM 專屬訓練、雙引擎對比報告、通用批量分析
  - v3.1 (2026-02-13): 新增 IC Analysis API（Section 14）- IC Gatekeeper 篩選系統 13 個端點，WebSocket 實時進度推送
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
15. [IC Analysis API](#14-ic-analysis-api)
16. [Dual-Engine ML API (Phase 3.7)](#15-dual-engine-ml-api-phase-37)
17. [Model Enhancement API (Phase 3.5)](#16-model-enhancement-api-phase-35)
18. [Hyperparameter Optimization API (Phase 4)](#17-hyperparameter-optimization-api-phase-4)
19. [Execution Optimization API (Phase 4)](#18-execution-optimization-api-phase-4)
20. [Feature Factory Granular Control API](#19-feature-factory-granular-control-api)
21. [Feature Factory MultiTF + Batch API](#20-feature-factory-multitf--batch-api)
22. [WebSocket API](#websocket-api)
23. [錯誤處理](#錯誤處理)
24. [數據模型](#數據模型)

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
| `pattern_analysis` | `/api/v1/pattern-analysis` | Pattern Analysis（含 Dual-Engine ML） |
| `pattern_management` | `/api/v1/patterns` | Pattern Management |
| `ml_pipeline` | `/api/v1/ml-pipeline` | ML Pipeline |
| `two_stage_search` | `/api/v1/two-stage` | Two-Stage Search |
| `model_enhancement` | `/api/v1/model-enhancement` | Model Enhancement (Phase 3.5) |
| `hyperparameter_optimization` | `/api/v1/hyperparameter-optimization` | Hyperparameter Optimization (Phase 4) |
| `feature_factory` | `/api/v1/features` | Feature Factory |
| `feature_browser` | `/api/v1` | Feature Browser |
| `feature_toggles` | `/api/v1/feature-toggles` | Feature Toggles |
| `export` | `/api/v1/export` | Export |
| `execution_optimization` | `/api/v1/execution-optimization` | Execution Optimization (Phase 4) |

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

## 10. Pattern Analysis API (XGBoost / LightGBM)

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

## 15. Dual-Engine ML API (Phase 3.7)

> **路由**: `api/routes/pattern_analysis.py` | **Prefix**: `/api/v1/pattern-analysis`
> 
> Phase 3.7 新增的雙引擎 ML API，支援 LightGBM 與 XGBoost 通用訓練、單引擎專屬訓練、雙引擎對比報告，以及通用批量分析（xgboost / lightgbm / both）。

### 15.1 通用模型訓練
```http
POST /api/v1/pattern-analysis/model/train
```

**Request Body** (`ModelTrainingRequest`):
```json
{
  "engine": "lightgbm",
  "features_source": "data_cache/features/BTCUSDT_12h_features.h5",
  "config": {
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": 6
  },
  "validation": {
    "cv_folds": 5,
    "purge_gap": 5,
    "oot_enabled": true,
    "oot_ratio": 0.2,
    "early_stopping_rounds": 50
  },
  "run_comparison": false
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `engine` | `"lightgbm"` \| `"xgboost"` | 否（預設 lightgbm） | 模型引擎 |
| `features_source` | `string` | 是 | 特徵數據來源路徑 |
| `config` | `object` | 否 | 引擎專屬模型參數 |
| `validation` | `ValidationConfig` | 否 | 驗證配置 |
| `run_comparison` | `boolean` | 否（預設 false） | 是否同時執行雙引擎對比 |

**Response** (`TaskStartResponse`):
```json
{
  "task_id": "model_task_20260214_103000_abc123",
  "status": "running",
  "engine": "lightgbm"
}
```

### 15.2 取得模型效能
```http
GET /api/v1/pattern-analysis/model/{task_id}/performance
```

**Response** (`ModelPerformanceResponse`):
```json
{
  "engine_type": "lightgbm",
  "train_auc": 0.92,
  "cv_auc_mean": 0.85,
  "cv_auc_std": 0.03,
  "precision": 0.78,
  "recall": 0.72,
  "f1_score": 0.75,
  "overfitting_score": 0.07,
  "brier_score": 0.15,
  "ece": 0.04,
  "calibration_quality": "good",
  "pr_auc": 0.81,
  "positive_rate": 0.35,
  "oot_auc": 0.83,
  "training_time_seconds": 12.5
}
```

### 15.3 取得雙引擎對比報告
```http
GET /api/v1/pattern-analysis/model/{task_id}/comparison
```

需要 `run_comparison=true` 才能取得結果。

**Response** (`ComparisonReportResponse`):
```json
{
  "engine_performances": {
    "xgboost": {
      "engine_type": "xgboost",
      "train_auc": 0.94,
      "cv_auc_mean": 0.86,
      "cv_auc_std": 0.02,
      "precision": 0.80,
      "recall": 0.70,
      "f1_score": 0.75,
      "overfitting_score": 0.08
    },
    "lightgbm": {
      "engine_type": "lightgbm",
      "train_auc": 0.91,
      "cv_auc_mean": 0.85,
      "cv_auc_std": 0.03,
      "precision": 0.78,
      "recall": 0.74,
      "f1_score": 0.76,
      "overfitting_score": 0.06
    }
  },
  "consensus_rate": 0.88,
  "feature_rank_correlation": 0.72,
  "recommended_engine": "lightgbm",
  "recommendation_reason": "CV AUC 相近但過擬合分數較低，泛化能力較佳"
}
```

### 15.4 LightGBM 專屬訓練
```http
POST /api/v1/pattern-analysis/lightgbm/train
```

**Request Body** (`LightGBMTrainingRequest`):
```json
{
  "features_source": "data_cache/features/BTCUSDT_12h_features.h5",
  "config": {
    "learning_rate": 0.05,
    "num_leaves": 31
  },
  "boosting_type": "gbdt",
  "categorical_features": ["market_regime", "day_of_week"],
  "validation": {
    "cv_folds": 5,
    "purge_gap": 5,
    "oot_enabled": true,
    "oot_ratio": 0.2,
    "early_stopping_rounds": 50
  }
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `features_source` | `string` | 是 | 特徵數據來源路徑 |
| `config` | `object` | 否 | LightGBM 參數 |
| `boosting_type` | `"gbdt"` \| `"dart"` \| `"goss"` | 否（預設 gbdt） | Boosting 策略 |
| `categorical_features` | `string[]` | 否 | 類別特徵列表（LightGBM 原生支援） |
| `validation` | `ValidationConfig` | 否 | 驗證配置 |

**Response**: 同 `TaskStartResponse`（engine 固定為 `"lightgbm"`）

### 15.5 取得 LightGBM 結果
```http
GET /api/v1/pattern-analysis/lightgbm/{task_id}/results
```

**Response** (`LightGBMResultsResponse`):
```json
{
  "task_id": "model_task_20260214_103000_abc123",
  "performance": {
    "engine_type": "lightgbm",
    "train_auc": 0.91,
    "cv_auc_mean": 0.85,
    "cv_auc_std": 0.03,
    "precision": 0.78,
    "recall": 0.74,
    "f1_score": 0.76,
    "overfitting_score": 0.06
  },
  "feature_importance": [
    {"feature": "ema_ratio_5_20", "importance": 0.35, "rank": 1},
    {"feature": "volume_ma_ratio", "importance": 0.22, "rank": 2}
  ],
  "predictions_summary": {
    "total_cases": 1200,
    "mean_proba": 0.42,
    "positive_rate": 0.35
  }
}
```

### 15.6 通用批量分析
```http
POST /api/v1/pattern-analysis/batch/start
```

支援 xgboost / lightgbm / both 三種引擎模式的批量分析。

**Request Body** (`BatchAnalysisRequest`，繼承 `XGBoostBatchAnalysisRequest`):
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "timeframe": "12h",
  "indicators": [
    {
      "indicator": "ema",
      "data_source": "close",
      "params": {"short_period": 5, "long_period": 20}
    }
  ],
  "engine": "both",
  "model_params": {"learning_rate": 0.05},
  "run_comparison": true,
  "lookback_bars": 200,
  "cv_folds": 5
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `engine` | `"xgboost"` \| `"lightgbm"` \| `"both"` | 否（預設 xgboost） | 模型引擎 |
| `run_comparison` | `boolean` | 否（預設 false） | 雙引擎模式下執行對比報告 |
| `model_params` | `object` | 否 | 通用模型參數 |
| 其餘欄位 | - | - | 同 `XGBoostBatchAnalysisRequest` |

### 15.7 取得通用批量任務狀態
```http
GET /api/v1/pattern-analysis/batch/task/{task_id}
```

回傳任務進度、狀態與結果，格式同批量 XGBoost 任務但包含引擎資訊。

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

## 14. IC Analysis API

> **路由**: `api/routes/ic_analysis.py` | **Prefix**: `/api/v1/ic`

IC Gatekeeper 分析 API，提供 Information Coefficient 特徵篩選、八階段管線執行、統計驗證、冗餘篩選、模型驗證等功能。

### 14.1 啟動 IC 分析
```http
POST /api/v1/ic/analyze
```

**Request Body**:
```json
{
  "feature_file_path": "data_cache/features/BTCUSDT_12h_features.h5",
  "label_file_path": "data_cache/labels/BTCUSDT_12h_labels.h5",
  "metadata_file_path": "data_cache/features/BTCUSDT_12h_metadata.json",
  "ic_method": "spearman",
  "min_periods": 20,
  "event_filter_mode": "query",
  "event_query": "market_regime == 'bull'",
  "statistical_test": {
    "enabled": true,
    "alpha": 0.05,
    "method": "fdr"
  },
  "monotonicity_test": {
    "enabled": true,
    "n_quantiles": 5,
    "min_score": 0.6
  },
  "redundancy_filter": {
    "enabled": true,
    "algorithm": "greedy",
    "correlation_threshold": 0.7
  },
  "model_validation": {
    "enabled": true,
    "cv_folds": 5,
    "oot_ratio": 0.2
  }
}
```

**Response**:
```json
{
  "task_id": "ic_task_20260213_143052_abc123",
  "status": "running",
  "message": "IC analysis started"
}
```

### 14.2 查詢任務狀態
```http
GET /api/v1/ic/task/{task_id}
```

**Response**:
```json
{
  "task_id": "ic_task_20260213_143052_abc123",
  "status": "running",
  "progress": {
    "current_stage": "Stage 5: 統計驗證",
    "stage_number": 5,
    "total_stages": 8,
    "percentage": 62.5,
    "elapsed_time": 12.8,
    "estimated_remaining": 7.2
  },
  "result": null
}
```

**狀態值**: `pending`, `running`, `completed`, `failed`

### 14.3 下載分析報告
```http
GET /api/v1/ic/export/{task_id}/{format}
```

**參數**:
- `format`: `json` | `markdown` | `hdf5` | `ai_summary`

**Response (JSON format)**:
```json
{
  "task_id": "ic_task_20260213_143052_abc123",
  "timestamp": "2026-02-13T14:32:15",
  "config": {
    "ic_method": "spearman",
    "min_periods": 20
  },
  "pipeline_summary": {
    "stage_0_ingestion": {"features_count": 200, "samples_count": 10000},
    "stage_1_preprocessing": {"removed_features": 5, "remaining": 195},
    "stage_4_ic_calculation": {"ic_computed": 195},
    "stage_5_statistical_test": {"passed": 120, "failed": 75},
    "stage_6_monotonicity_test": {"passed": 85, "failed": 35},
    "stage_7_redundancy_filter": {"final_features": 42}
  },
  "top_features": [
    {
      "feature_name": "rsi_14",
      "ic_mean": 0.082,
      "t_statistic": 4.56,
      "p_value": 0.0001,
      "monotonicity_score": 0.85,
      "correlation_cluster": "momentum_group_1"
    }
  ],
  "model_validation": {
    "cv_auc_mean": 0.68,
    "oot_auc": 0.65,
    "psi": 0.12
  }
}
```

### 14.4 下載完整資料（HDF5）
```http
GET /api/v1/ic/export/{task_id}/hdf5
```

**Response**: Binary HDF5 檔案  
**Content-Type**: `application/x-hdf5`  
**檔案內容**:
- `/ic_values` - IC 時間序列矩陣
- `/ic_statistics` - 統計指標表
- `/filtered_features` - 最終篩選特徵清單
- `/metadata` - 完整配置與執行資訊

### 14.5 Refilter 模式（快速重新篩選）
```http
POST /api/v1/ic/refilter
```

**Request Body**:
```json
{
  "new_ic_threshold": 0.05,
  "new_p_value_threshold": 0.01,
  "new_correlation_threshold": 0.65
}
```

**功能**: 不重新計算 IC，直接從快取讀取已計算 IC，套用新的篩選條件（10 倍加速）。

**Response**:
```json
{
  "refilter_task_id": "ic_refilter_20260213_143500_xyz789",
  "status": "completed",
  "execution_time_seconds": 0.8,
  "final_features_count": 38
}
```

### 14.6 取得 IC 衰減曲線
```http
GET /api/v1/ic/decay/{feature_name}
```

**Response**:
```json
{
  "feature_name": "rsi_14",
  "ic_decay": [
    {"period": 1, "ic": 0.082},
    {"period": 2, "ic": 0.074},
    {"period": 3, "ic": 0.061},
    {"period": 5, "ic": 0.042},
    {"period": 10, "ic": 0.018}
  ]
}
```

### 14.7 取得分組 IC（按市場狀態）
```http
GET /api/v1/ic/grouped?feature_name=rsi_14&group_by=market_regime
```

**Response**:
```json
{
  "feature_name": "rsi_14",
  "grouped_ic": {
    "bull": {"ic_mean": 0.095, "sample_size": 4200},
    "bear": {"ic_mean": 0.061, "sample_size": 3800},
    "sideways": {"ic_mean": 0.032, "sample_size": 2000}
  }
}
```

### 14.8 取得分位數報酬分析
```http
GET /api/v1/ic/quantile/{feature_name}
```

**Response**:
```json
{
  "feature_name": "rsi_14",
  "quantile_returns": [
    {"quantile": "Q1", "mean_return": -0.012, "std": 0.045},
    {"quantile": "Q2", "mean_return": -0.003, "std": 0.038},
    {"quantile": "Q3", "mean_return": 0.008, "std": 0.041},
    {"quantile": "Q4", "mean_return": 0.019, "std": 0.047},
    {"quantile": "Q5", "mean_return": 0.032, "std": 0.053}
  ],
  "long_short_spread": 0.044,
  "monotonicity_score": 0.85
}
```

### 14.9 取得相關性矩陣
```http
GET /api/v1/ic/correlation?features=rsi_14,macd,ema_cross
```

**Response**:
```json
{
  "correlation_matrix": [
    [1.0, 0.23, 0.15],
    [0.23, 1.0, 0.68],
    [0.15, 0.68, 1.0]
  ],
  "feature_names": ["rsi_14", "macd", "ema_cross"]
}
```

### 14.10 取得模型驗證結果
```http
GET /api/v1/ic/result/{task_id}
```

**Response**:
```json
{
  "cv_results": {
    "fold_1": {"auc": 0.67, "precision": 0.58, "recall": 0.62},
    "fold_2": {"auc": 0.69, "precision": 0.61, "recall": 0.64},
    "mean": {"auc": 0.68, "precision": 0.59, "recall": 0.63}
  },
  "oot_results": {
    "auc": 0.65,
    "precision": 0.56,
    "recall": 0.61
  },
  "psi_score": 0.12,
  "rolling_auc": [
    {"period": "2025-Q1", "auc": 0.67},
    {"period": "2025-Q2", "auc": 0.69},
    {"period": "2025-Q3", "auc": 0.66}
  ]
}
```

### 14.11 取得 SHAP 解釋
```http
POST /api/v1/ic/deep-analysis/{task_id}
```

**Request Body**:
```json
{
  "case_indices": [0, 10, 50, 100],
  "features": ["rsi_14", "macd", "ema_cross"]
}
```

**Response**:
```json
{
  "shap_values": {
    "case_0": {"rsi_14": 0.12, "macd": -0.05, "ema_cross": 0.08},
    "case_10": {"rsi_14": 0.08, "macd": -0.02, "ema_cross": 0.11}
  },
  "feature_importance": [
    {"feature": "ema_cross", "mean_abs_shap": 0.095},
    {"feature": "rsi_14", "mean_abs_shap": 0.087},
    {"feature": "macd", "mean_abs_shap": 0.042}
  ]
}
```

### 14.12 批次啟動多標的分析
```http
POST /api/v1/ic/full-analysis
```

**Request Body**:
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
  "feature_template": "data_cache/features/{symbol}_12h_features.h5",
  "label_template": "data_cache/labels/{symbol}_12h_labels.h5",
  "shared_config": {
    "ic_method": "spearman",
    "min_periods": 20
  }
}
```

**Response**:
```json
{
  "batch_id": "batch_20260213_144500",
  "task_ids": [
    "ic_task_BTCUSDT_144501",
    "ic_task_ETHUSDT_144502",
    "ic_task_BNBUSDT_144503"
  ]
}
```

### 14.13 WebSocket 實時進度
```
ws://localhost:8000/ws/ic-analysis/{task_id}
```

**推送格式**:
```json
{
  "type": "progress",
  "task_id": "ic_task_20260213_143052_abc123",
  "status": "running",
  "current_stage": "Stage 5: 統計驗證",
  "stage_number": 5,
  "total_stages": 8,
  "percentage": 62.5,
  "elapsed_time": 12.8,
  "estimated_remaining": 7.2,
  "stage_metrics": {
    "features_processed": 120,
    "features_passed": 85,
    "features_failed": 35
  }
}
```

**完成狀態**:
```json
{
  "type": "completed",
  "task_id": "ic_task_20260213_143052_abc123",
  "status": "completed",
  "execution_time": 20.5,
  "final_features_count": 42,
  "report_available": true
}
```

---

## 19. Feature Factory Granular Control API

> **路由**: `api/routes/feature_factory.py` | **Prefix**: `/api/v1/features`  
> **依據**: FEATURE_FACTORY_GRANULAR_CONTROL_PLAN V1.2  
> **新增於**: v5.0 (2026-03-08)

Per-Indicator 細粒度控制 — 支援 Layer 1~6.5 所有層級的指標/聚合器/運算子獨立啟用/關閉。

### 19.1 取得完整 Schema
```http
GET /api/v1/features/schema
```

回傳 7 層架構的完整 Schema，包含所有可用指標、描述與當前 enabled 狀態，供前端動態渲染 UI。

**Response** (200 OK):
```json
{
  "layers": {
    "layer1": {
      "name": "Atomic Indicators",
      "enabled": true,
      "categories": {
        "trend": {
          "enabled": true,
          "level": "L1",
          "description": "趨勢指標",
          "indicators": [
            {
              "name": "EMA",
              "enabled": true,
              "description": "指數移動平均",
              "params": { "periods": "fibonacci", "period_range": [5, 233] }
            }
          ]
        }
      }
    },
    "layer2": {
      "name": "Derived Operators",
      "enabled": true,
      "operators": {
        "distance": { "enabled": true, "description": "距離運算" },
        "cross": { "enabled": true, "description": "交叉運算" },
        "momentum": { "enabled": true, "description": "動量運算" },
        "ratio": { "enabled": true, "description": "比率運算" },
        "binary_signal": { "enabled": true, "description": "二元信號" },
        "worldquant": { "enabled": true, "description": "WorldQuant 算子" }
      }
    },
    "layer3": {
      "name": "Rolling Aggregation",
      "enabled": true,
      "aggregators": {
        "mean": { "enabled": true },
        "std": { "enabled": true },
        "rank": { "enabled": true }
      },
      "windows": [5, 13, 21, 34, 55]
    },
    "layer4": { "name": "Lag Features", "enabled": true },
    "layer5": {
      "name": "Cross-Sectional",
      "enabled": true,
      "features": {
        "relative_price": { "enabled": true },
        "beta": { "enabled": true },
        "idiosyncratic_momentum": { "enabled": true }
      }
    },
    "layer6": {
      "name": "Meta Features",
      "enabled": true,
      "sub_engines": {
        "consensus": { "enabled": true },
        "interaction": { "enabled": true },
        "time_features": { "enabled": true },
        "trend_consensus": { "enabled": true },
        "momentum_divergence": { "enabled": true },
        "volume_price_divergence": { "enabled": true },
        "volatility_regime": { "enabled": true }
      }
    },
    "layer6_5": {
      "name": "Preprocessing",
      "enabled": false,
      "methods": {
        "winsorization": { "enabled": true },
        "rank_transform": { "enabled": true },
        "adaptive_zscore": { "enabled": true },
        "gaussian_normalize": { "enabled": false },
        "adf_differencing": { "enabled": false },
        "fractional_differencing": { "enabled": false }
      }
    }
  }
}
```

### 19.2 批量切換啟用狀態
```http
PUT /api/v1/features/config/batch-toggle
```

批量切換指標/聚合器/運算子的 enabled 狀態。支援任意深度路徑。

**Request Body** (`BatchToggleRequest`):
```json
{
  "toggles": [
    { "path": "atomic_indicators.trend.indicators.EMA.enabled", "value": true },
    { "path": "atomic_indicators.trend.indicators.SMA.enabled", "value": false },
    { "path": "rolling_aggregation.aggregators.zscore.enabled", "value": false },
    { "path": "operators.distance.enabled", "value": false }
  ]
}
```

**Response** (200 OK):
```json
{
  "results": [
    { "path": "atomic_indicators.trend.indicators.EMA.enabled", "success": true },
    { "path": "atomic_indicators.trend.indicators.SMA.enabled", "success": true },
    { "path": "rolling_aggregation.aggregators.zscore.enabled", "success": true },
    { "path": "operators.distance.enabled", "success": true }
  ],
  "config": { },
  "preview": {
    "total_features": 2345,
    "estimated_time_seconds": 12.5,
    "memory_mb": 45.0,
    "breakdown": {
      "atomic": 800,
      "derived": 200,
      "rolling": 1000,
      "lag": 100,
      "cross_sectional": 3,
      "meta": 42,
      "labels": 200
    }
  }
}
```

**錯誤**：無效路徑時該項 `success: false`，其餘正常項仍執行。

### 19.3 套用預設配置
```http
POST /api/v1/features/config/presets/{preset_name}
```

套用具名預設配置，回傳更新後的 config 和 preview。

**Path Parameters**:
| 參數 | 類型 | 說明 |
|------|------|------|
| `preset_name` | string | 預設名稱（見下表） |

**可用預設**:
| 預設名 | 說明 |
|--------|------|
| `minimal` | 最小配置（Trend + Momentum） |
| `standard` | 標準配置（全部 TA-Lib） |
| `basic_essential` | 基礎精選（4 核心 + Winsor + Rank） |
| `intermediate_research` | 進階研究（+ Stats, Cycle, Pattern） |
| `professional_full` | 完整專業（+ Micro + Entropy） |
| `ml_optimized` | ML 專用 |
| `trend_focused` | 趨勢策略（Trend 全開 + Momentum 精選） |
| `momentum_focused` | 動量策略（Momentum + Volume 全開） |
| `microstructure_focused` | 微觀結構研究（Micro + Volume + Entropy） |
| `lightweight_ml` | 輕量 ML（~30 核心指標 + rank preprocessing） |

**Response** (200 OK):
```json
{
  "config": { },
  "preview": {
    "total_features": 1234,
    "estimated_time_seconds": 8.0,
    "memory_mb": 30.0,
    "breakdown": { }
  }
}
```

**Error** (400 Bad Request):
```json
{
  "detail": "Unknown preset: invalid_name"
}
```

---

## 20. Feature Factory MultiTF + Batch API

> **路由**: `api/routes/feature_factory.py` | **Prefix**: `/api/v1/features`  
> **新增於**: v6.0 (2026-03-15)

### 20.1 單標的特徵生成
```http
POST /api/v1/features/generate
```

啟動單一標的的特徵生成任務。`timeframe` 必須是 `SUPPORTED_TIMEFRAMES` 之一，否則回傳 422。

**Request Body** (`FeatureGenerateRequest`):
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "12h",
  "config_override": null,
  "force_regenerate": false
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `symbol` | string | ✅ | 交易標的（例如 `BTCUSDT`）|
| `timeframe` | string | ✅ | 主時間週期（需在 `SUPPORTED_TIMEFRAMES` 中）|
| `config_override` | object \| null | ❌ | 覆寫預設特徵工廠配置 |
| `force_regenerate` | boolean | ❌ | `true` 跳過快取，強制重算（預設 `false`）|

**SUPPORTED_TIMEFRAMES**：`["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]`

**Response** (202 Accepted):
```json
{
  "task_id": "3f4a1b2c-...",
  "status": "pending"
}
```

**錯誤**：
| 狀態碼 | 情境 |
|--------|------|
| `422` | `timeframe` 不在 `SUPPORTED_TIMEFRAMES` 中 |
| `400` | 請求參數語意錯誤（例如無效 config 路徑）|
| `500` | 伺服器內部錯誤 |

---

### 20.2 啟動批次特徵生成
```http
POST /api/v1/features/batch
```

啟動多標的並行特徵生成。後端使用 `FeatureFactoryBatchService`（`ProcessPoolExecutor`，`max_concurrent=2`）。

**Request Body** (`BatchGenerateRequest`):
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
  "timeframe": "12h",
  "config_override": null,
  "force_regenerate": false,
  "max_workers": 4
}
```

| 欄位 | 類型 | 必填 | 約束 | 說明 |
|------|------|------|------|------|
| `symbols` | array\<string\> | ✅ | 1–200 個；自動去重 | 目標標的清單 |
| `timeframe` | string | ❌ | 必須在 `SUPPORTED_TIMEFRAMES` 中 | 主時間週期（預設 `"12h"`）|
| `config_override` | object \| null | ❌ | — | 覆寫特徵工廠配置 |
| `force_regenerate` | boolean | ❌ | — | 是否跳過快取（預設 `false`）|
| `max_workers` | integer | ❌ | 1–8 | ProcessPool 工作行程數（預設 `4`）|

**Validators**:
- `symbols`：自動去重並保留順序；每個元素需符合 `^[A-Za-z0-9_]+$`
- `timeframe`：不在 `SUPPORTED_TIMEFRAMES` 列表則回傳 422

**Response** (202 Accepted):
```json
{
  "task_id": "a9b3c2d1-...",
  "status": "pending",
  "total": 3
}
```

**錯誤**：
| 狀態碼 | 情境 |
|--------|------|
| `422` | `timeframe` 不合法或 `symbols` 含非法字元 |
| `400` | 請求語意錯誤 |
| `500` | 伺服器內部錯誤 |

---

### 20.3 查詢批次任務狀態
```http
GET /api/v1/features/batch/{task_id}
```

輪詢批次任務當前進度。

**Path Parameters**:
| 參數 | 類型 | 說明 |
|------|------|------|
| `task_id` | string (UUID) | 由 `POST /batch` 回傳的任務 ID |

**Response** (`BatchTaskStatusResponse`):
```json
{
  "task_id": "a9b3c2d1-...",
  "status": "running",
  "total": 3,
  "completed": 1,
  "failed": 0,
  "progress": 0.33,
  "results": {
    "BTCUSDT": "task_id_btc"
  },
  "errors": {}
}
```

**`status` 可能值**:
| 狀態 | 說明 |
|------|------|
| `pending` | 等待排隊中 |
| `running` | 批次進行中 |
| `completed` | 全部標的完成 |
| `partial` | 部分標的失敗，其餘完成 |
| `failed` | 全部標的失敗或任務啟動失敗 |

**錯誤**：
| 狀態碼 | 情境 |
|--------|------|
| `404` | `task_id` 不存在或已 TTL 清理 |
| `500` | 伺服器內部錯誤 |

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

### IC Analysis 即時進度
```
ws://localhost:8000/ws/ic-analysis/{task_id}?client_id={client_id}
```
推送 IC Gatekeeper 八階段管線進度（stage_number, percentage, stage_metrics 等）。

### Feature Factory 即時進度
```
ws://localhost:8000/ws/features/{task_id}?client_id={client_id}
```
推送 Feature Factory 七層 pipeline 執行進度。

### Feature Factory 批次生成即時進度
```
ws://localhost:8000/ws/features/batch/{task_id}?client_id={client_id}
```

推送多標的批次特徵生成的逐標的完成進度。

**推送格式**（每完成一個標的）:
```json
{
  "type": "batch_progress",
  "task_id": "a9b3c2d1-...",
  "status": "running",
  "total": 10,
  "completed": 3,
  "failed": 0,
  "progress": 0.30,
  "latest_symbol": "ETHUSDT",
  "latest_result": "task_id_eth"
}
```

**最終狀態**:
```json
{
  "type": "batch_completed",
  "task_id": "a9b3c2d1-...",
  "status": "completed",
  "total": 10,
  "completed": 10,
  "failed": 0,
  "progress": 1.0,
  "results": {"BTCUSDT": "task_btc", "ETHUSDT": "task_eth"},
  "errors": {}
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

### ValidationConfig (Phase 3.7)
```typescript
interface ValidationConfig {
  cv_folds: number;                // 2-20, 預設 5
  purge_gap: number;               // 0-500, 預設 5
  oot_enabled: boolean;            // 預設 true
  oot_ratio: number;               // 0.0-1.0, 預設 0.2
  early_stopping_rounds: number;   // 1-500, 預設 50
}
```

### ModelTrainingRequest (Phase 3.7)
```typescript
interface ModelTrainingRequest {
  engine: 'lightgbm' | 'xgboost';         // 預設 lightgbm
  features_source: string;                  // 特徵數據路徑
  config?: Record<string, any>;            // 引擎專屬參數
  validation?: ValidationConfig;
  run_comparison: boolean;                  // 預設 false
}
```

### ModelPerformanceResponse (Phase 3.7)
```typescript
interface ModelPerformanceResponse {
  engine_type?: string;
  train_auc: number;
  cv_auc_mean: number;
  cv_auc_std: number;
  precision: number;
  recall: number;
  f1_score: number;
  overfitting_score: number;
  brier_score?: number;
  ece?: number;
  calibration_quality?: string;
  pr_auc?: number;
  positive_rate?: number;
  oot_auc?: number;
  training_time_seconds?: number;
}
```

### ComparisonReportResponse (Phase 3.7)
```typescript
interface ComparisonReportResponse {
  engine_performances: Record<string, ModelPerformanceResponse>;
  consensus_rate: number;
  feature_rank_correlation: number;
  recommended_engine: string;
  recommendation_reason: string;
}
```

### LightGBMTrainingRequest (Phase 3.7)
```typescript
interface LightGBMTrainingRequest {
  features_source: string;
  config?: Record<string, any>;
  boosting_type: 'gbdt' | 'dart' | 'goss';  // 預設 gbdt
  categorical_features?: string[];
  validation?: ValidationConfig;
}
```

### LightGBMResultsResponse (Phase 3.7)
```typescript
interface LightGBMResultsResponse {
  task_id: string;
  performance: ModelPerformanceResponse;
  feature_importance: Array<{ feature: string; importance: number; rank: number }>;
  predictions_summary?: Record<string, any>;
}
```

### BatchAnalysisRequest (Phase 3.7)
```typescript
interface BatchAnalysisRequest extends XGBoostBatchAnalysisRequest {
  engine: 'xgboost' | 'lightgbm' | 'both';  // 預設 xgboost
  run_comparison: boolean;                     // 預設 false
  model_params?: Record<string, any>;          // 通用模型參數
}
```

### TaskStartResponse (Phase 3.7)
```typescript
interface TaskStartResponse {
  task_id: string;
  status: string;    // "running"
  engine: string;    // "lightgbm" | "xgboost"
}
```

---

## 16. Model Enhancement API (Phase 3.5)

> **路由**: `api/routes/model_enhancement.py` | **Prefix**: `/api/v1/model-enhancement`

### 16.1 機率校準
```http
POST /api/v1/model-enhancement/calibrate
```
**功能**: 執行機率校準（Platt Scaling / Isotonic Regression / Beta Calibration / Venn-ABERS）

### 16.2 Walk-Forward 驗證
```http
POST /api/v1/model-enhancement/walk-forward
```
**功能**: 執行 Walk-Forward 驗證（Rolling / Expanding 窗口模式）

### 16.3 樣本加權計算
```http
POST /api/v1/model-enhancement/sample-weights
```
**功能**: 計算樣本權重（time_decay / class_balance / return_based / uniqueness）

### 16.4 對抗驗證
```http
POST /api/v1/model-enhancement/adversarial-validate
```
**功能**: 執行對抗驗證（分布測試 + feature-level KS/PSI + 洩漏偵測）

### 16.5 CPCV 驗證
```http
POST /api/v1/model-enhancement/cpcv
```
**功能**: 執行 Combinatorial Purged Cross-Validation（López de Prado 方法）

### 16.6 學習曲線
```http
POST /api/v1/model-enhancement/learning-curve
```
**功能**: 計算學習曲線（data curves + feature curves + bias-variance 診斷）

### 16.7 查詢任務
```http
GET /api/v1/model-enhancement/task/{task_id}
```
**功能**: 查詢模型增強任務狀態與結果

### 16.8 全量增強
```http
POST /api/v1/model-enhancement/full-enhancement
```
**功能**: 執行所有 6 個增強模組（平行執行，per-module timeout）

---

## 17. Hyperparameter Optimization API (Phase 4)

> **路由**: `api/routes/hyperparameter_optimization.py` | **Prefix**: `/api/v1/hyperparameter-optimization`

**功能**: 模型超參數優化端點（基於重構後的 Optuna 可插拔目標架構）

#### 端點概要
- 超參數優化任務建立（ModelHyperparamObjective + StrategyBacktestObjective）
- 任務狀態查詢
- 優化結果輸出（JSON/CSV/HTML/AI-readable 報告）
- 過擬合偵測結果

---

## 18. Execution Optimization API (Phase 4)

> **路由**: `api/routes/execution_optimization.py` | **Prefix**: `/api/v1/execution-optimization`

**功能**: 策略執行面優化端點（回測引擎 + 績效指標 + 部位管理）

#### 端點概要
- 回測任務建立（VectorizedBacktest + SL/TP/Trailing Stop 配置）
- 績效指標查詢（Sharpe / Sortino / Calmar / MaxDD / Expectancy / SQN / Win Rate / Profit Factor）
- 部位管理配置（Kelly / Fixed / ProbabilityScaled）
- 優化結果輸出

#### 新 WebSocket 事件
- `backtest_progress` — 回測進度更新
- `pareto_update` — Pareto 前沿更新（多目標優化）
- `overfitting_alert` — 過擬合警報

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

*文檔版本：6.0*
*最後更新：2026-03-15*
*狀態：Phase 1-4 + Feature Factory MultiTF/Batch 全部完成，API 同步更新*
