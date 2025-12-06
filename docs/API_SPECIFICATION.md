# API接口規範

## 文檔信息
- **版本**: 1.1
- **最後更新**: 2025-12-06
- **Base URL**: `http://localhost:8000` (開發環境)
- **變更記錄**:
  - v1.1 (2025-12-06): 新增 SignalDensityResponse 零值統計欄位，修復 Far=0 統計偏差

---

## 目錄
1. [通用規範](#通用規範)
2. [已實現API](#已實現api)
3. [待開發API](#待開發api)
4. [錯誤處理](#錯誤處理)
5. [數據模型](#數據模型)

---

## 通用規範

### 請求格式
```
Content-Type: application/json
Accept: application/json
```

### 響應格式
```json
{
  "success": boolean,
  "data": object | array | null,
  "error": {
    "code": string,
    "message": string,
    "details": object
  } | null
}
```

### 狀態碼
- `200` - 請求成功
- `201` - 創建成功
- `400` - 請求參數錯誤
- `404` - 資源不存在
- `500` - 服務器錯誤

---

## 已實現API

### 1. Case Search API

#### 執行搜索
```http
POST /api/v1/search/execute
```

**Request Body:**
```json
{
  "template_id": "string (optional)",
  "config": {
    "timeframe": "1h|4h|12h|1d",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "price_change": number,
    "volume_multiplier": number,
    "taker_buy_ratio": number,
    // ... 其他20個參數
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid",
    "status": "pending"
  }
}
```

---

#### 查詢任務狀態
```http
GET /api/v1/search/task/{task_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid",
    "status": "pending|running|completed|failed",
    "progress": 0.0-1.0,
    "result": {
      "cases": [],
      "statistics": {}
    }
  }
}
```

---

#### 獲取搜索模板
```http
GET /api/v1/search/templates
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "config": {}
    }
  ]
}
```

---

### 2. Config API

#### 獲取系統配置
```http
GET /api/v1/config
```

**Response:**
```json
{
  "success": true,
  "data": {
    "storage_path": "string",
    "max_concurrent_tasks": number,
    "cache_enabled": boolean
  }
}
```

---

#### 更新系統配置
```http
PATCH /api/v1/config
```

**Request Body:**
```json
{
  "storage_path": "string (optional)",
  "max_concurrent_tasks": number
}
```

---

## 待開發API

### 3. Chart Data API

#### 獲取K線數據
```http
GET /api/v1/chart/kline/{symbol}/{case_id}
```

**Query Parameters:**
- `lookback`: number (default: 240)
- `forward`: number (default: 96)

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "case_id": "uuid",
    "case_timestamp": "ISO8601",
    "klines": {
      "timestamp": [number],
      "open": [number],
      "high": [number],
      "low": [number],
      "close": [number],
      "volume": [number],
      "taker_volume": [number],
      "taker_ratio": [number]
    }
  }
}
```

---

#### 獲取信號標記
```http
GET /api/v1/chart/signals/{case_id}
```

**Query Parameters:**
- `strategy`: string (required)
- `data_sources`: string[] (default: ['price', 'volume', 'taker_ratio'])

**Response:**
```json
{
  "success": true,
  "data": {
    "price_signals": [
      {
        "time": number,
        "position": "aboveBar|belowBar",
        "color": "string",
        "shape": "arrowUp|arrowDown",
        "text": "string",
        "strategy": "string"
      }
    ],
    "volume_signals": [],
    "taker_ratio_signals": []
  }
}
```

---

### 4. K線下載API

#### 批量下載K線
```http
POST /api/v1/kline/batch-download
```

**Request Body (multipart/form-data):**
- `csv_file`: File (CSV with columns: symbol, timestamp, label)
- `lookback_bars`: number (default: 240)
- `forward_bars`: number (default: 96)

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid",
    "total_cases": number,
    "estimated_time": "string"
  }
}
```

---

#### 查詢下載進度
```http
GET /api/v1/kline/download-progress/{task_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "pending|running|completed|failed",
    "progress": number,
    "downloaded": number,
    "total": number,
    "current_symbol": "string",
    "errors": ["string"]
  }
}
```

---

### 5. Indicator Testing API

#### 計算指標
```http
POST /api/v1/indicator/calculate
```

**Request Body:**
```json
{
  "case_ids": ["uuid"],
  "indicators": [
    {
      "type": "EMA|RSI|MACD|...",
      "data_sources": ["close", "volume", "taker_ratio"],
      "params": {
        "period": number
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid"
  }
}
```

---

#### 優化指標參數
```http
POST /api/v1/indicator/optimize
```

**Request Body:**
```json
{
  "case_ids": ["uuid"],
  "indicator": "EMA|RSI|...",
  "data_source": "close|volume|...",
  "optimization": {
    "method": "optuna|grid_search",
    "n_trials": number,
    "param_space": {
      "period": {"min": 5, "max": 200}
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid"
  }
}
```

---

#### 獲取指標評分
```http
GET /api/v1/indicator/scores
```

**Query Parameters:**
- `sort_by`: "score|accuracy|frequency"
- `limit`: number (default: 50)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "indicator": "close_ema_20",
      "score": 0.85,
      "accuracy": 0.78,
      "frequency": 0.12,
      "stability": 0.82,
      "efficiency": 0.95,
      "best_params": {"period": 20},
      "rank": 1
    }
  ]
}
```

---

### 6. ML Training API

#### 準備訓練數據
```http
POST /api/v1/ml/prepare-data
```

**Request Body:**
```json
{
  "positive_case_ids": ["uuid"],
  "negative_case_ids": ["uuid"],
  "feature_config": {
    "price_features": true,
    "volume_features": true,
    "taker_features": true,
    "indicator_features": ["close_ema_20", "rsi_14", "..."]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dataset_id": "uuid",
    "total_samples": number,
    "feature_count": number
  }
}
```

---

#### 訓練模型
```http
POST /api/v1/ml/train
```

**Request Body:**
```json
{
  "dataset_id": "uuid",
  "model_type": "xgboost|lightgbm|lstm",
  "config": {
    "test_size": 0.2,
    "use_optuna": boolean,
    "n_trials": number,
    "cv_folds": 5
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid",
    "estimated_time": "string"
  }
}
```

---

#### 查詢訓練進度
```http
GET /api/v1/ml/training-progress/{task_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "pending|running|completed|failed",
    "progress": number,
    "current_trial": number,
    "total_trials": number,
    "best_score": number,
    "elapsed_time": number
  }
}
```

---

#### 獲取模型評估
```http
GET /api/v1/ml/model/{model_id}/evaluation
```

**Response:**
```json
{
  "success": true,
  "data": {
    "model_id": "uuid",
    "model_type": "xgboost",
    "metrics": {
      "accuracy": 0.78,
      "precision": 0.76,
      "recall": 0.81,
      "f1": 0.78,
      "auc": 0.85
    },
    "risk_reward": {
      "avg_profit": 0.085,
      "avg_loss": 0.034,
      "risk_reward_ratio": 2.5,
      "win_rate": 0.68
    },
    "feature_importance": [
      {"feature": "close_ema_20", "importance": 0.15},
      {"feature": "volume_spike", "importance": 0.12}
    ]
  }
}
```

---

#### 預測
```http
POST /api/v1/ml/predict
```

**Request Body:**
```json
{
  "model_id": "uuid",
  "case_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "prediction": 0|1,
    "probability": number,
    "confidence": "high|medium|low",
    "expected_return": number,
    "risk_reward_ratio": number,
    "top_features": [
      {"feature": "string", "contribution": number}
    ]
  }
}
```

---

### 7. Pattern Discovery API

#### 發現Pattern
```http
POST /api/v1/pattern/discover
```

**Request Body:**
```json
{
  "indicator_ids": ["string"],
  "min_accuracy": number,
  "max_combination_size": number
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid"
  }
}
```

---

#### 獲取Pattern列表
```http
GET /api/v1/pattern/list
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "pattern_id": "uuid",
      "name": "EMA金叉+成交量放大",
      "conditions": [
        "close_ema_5 > close_ema_20",
        "volume > volume_ma_20 * 1.5"
      ],
      "accuracy": 0.75,
      "sample_size": 150,
      "avg_return": 0.08,
      "win_rate": 0.68
    }
  ]
}
```

---

### 8. Backtest API

#### 執行回測
```http
POST /api/v1/backtest/run
```

**Request Body:**
```json
{
  "strategy_type": "pattern|ml_model",
  "strategy_id": "uuid",
  "config": {
    "initial_capital": number,
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "commission": number,
    "slippage": number
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid"
  }
}
```

---

#### 獲取回測結果
```http
GET /api/v1/backtest/result/{task_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "metrics": {
      "total_return": 0.25,
      "annual_return": 0.15,
      "sharpe_ratio": 1.8,
      "sortino_ratio": 2.2,
      "max_drawdown": -0.15,
      "calmar_ratio": 1.0,
      "win_rate": 0.68,
      "profit_factor": 2.5,
      "total_trades": 150
    },
    "equity_curve": [
      {"timestamp": number, "equity": number}
    ],
    "trades": [
      {
        "entry_time": "ISO8601",
        "exit_time": "ISO8601",
        "type": "long|short",
        "entry_price": number,
        "exit_price": number,
        "pnl": number,
        "pnl_pct": number
      }
    ]
  }
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
    "message": "Human readable error message",
    "details": {
      "field": "specific error details"
    }
  }
}
```

### 常見錯誤碼
```
INVALID_PARAMS - 請求參數錯誤
RESOURCE_NOT_FOUND - 資源不存在
TASK_FAILED - 任務執行失敗
RATE_LIMIT_EXCEEDED - 超過頻率限制
INTERNAL_ERROR - 服務器內部錯誤
DATA_NOT_READY - 數據未準備好
MODEL_NOT_TRAINED - 模型未訓練
INSUFFICIENT_DATA - 數據不足
```

### 錯誤處理示例
```javascript
try {
  const response = await fetch('/api/v1/search/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(searchConfig)
  });
  
  const result = await response.json();
  
  if (!result.success) {
    console.error(`Error: ${result.error.code} - ${result.error.message}`);
    // Handle specific error codes
    switch(result.error.code) {
      case 'INVALID_PARAMS':
        // Show validation errors
        break;
      case 'RATE_LIMIT_EXCEEDED':
        // Retry after delay
        break;
      default:
        // Generic error handling
    }
  }
} catch (error) {
  console.error('Network error:', error);
}
```

---

## 數據模型

### CaseData
```typescript
interface CaseData {
  case_id: string;
  symbol: string;
  timestamp: string; // ISO8601
  timeframe: string;
  label: 0 | 1; // 0=反例, 1=正例
  
  // OHLCV數據
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
  future_6bar_return?: number;
  future_12bar_return?: number;
  future_max_return?: number;
  future_max_drawdown?: number;
  
  // 環境信息
  market_phase: string;
  hour_of_day: number;
  day_of_week: number;
}
```

### SearchConfig
```typescript
interface SearchConfig {
  name: string;
  description: string;
  timeframe: '1h' | '4h' | '12h' | '1d';
  start_date: string;
  end_date: string;
  
  // 觸發條件
  price_change?: { operator: string; value: number };
  closing_strength?: { operator: string; value: number };
  volume_multiplier?: { operator: string; value: number };
  taker_buy_ratio?: { operator: string; value: number };
  
  // 未來表現要求
  future_return_requirements?: {
    bars: number;
    operator: string;
    value: number;
  }[];
  
  // 反例設定
  negative_config?: {
    enabled: boolean;
    ratio: number;
    time_separation_days: number;
  };
}
```

### SignalDensityResponse (v1.1 更新)
```typescript
/**
 * 信號密度分析響應模型
 * 
 * 計算策略在正反例中的信號密度差異，評估策略有效性。
 * v1.1 更新：新增零值統計欄位，透明化顯示 Far=0 被排除的案例比例。
 */
interface SignalDensityResponse {
  // === 核心統計指標 ===
  positive_avg_density: number;      // 正例平均信號密度 (0.0~1.0)
  negative_avg_density: number;      // 反例平均信號密度 (0.0~1.0)
  separation: number;                // 密度差異 (正例 - 反例)，優化目標
  
  // === 雙密度模式額外指標 (當 far_lookback_bars 配置時有效) ===
  positive_far_avg_density?: number; // 正例遠期平均密度
  negative_far_avg_density?: number; // 反例遠期平均密度
  positive_near_far_ratio?: number;  // 正例 Near/Far Ratio 平均值 (可能為 null)
  negative_near_far_ratio?: number;  // 反例 Near/Far Ratio 平均值 (可能為 null)
  ratio_separation?: number;         // Ratio 差異 (正例 - 反例)，雙密度優化目標
  
  // === 零值統計 (v1.1 新增) ===
  // 透明化顯示策略信號未觸發或 Far=0 被排除的案例比例
  // Far density = 0 的案例會被排除於 ratio 統計，避免除以零產生無意義數值
  positive_near_zero_count?: number;  // 正例中 Near=0 的案例數（策略信號完全未觸發）
  positive_near_zero_ratio?: number;  // 正例中 Near=0 的比例 (0.0~1.0)
  positive_far_zero_count?: number;   // 正例中 Far=0 的案例數（被排除於 ratio 統計）
  positive_far_zero_ratio?: number;   // 正例中 Far=0 的比例 (0.0~1.0)
  negative_near_zero_count?: number;  // 反例中 Near=0 的案例數（策略信號完全未觸發）
  negative_near_zero_ratio?: number;  // 反例中 Near=0 的比例 (0.0~1.0)
  negative_far_zero_count?: number;   // 反例中 Far=0 的案例數（被排除於 ratio 統計）
  negative_far_zero_ratio?: number;   // 反例中 Far=0 的比例 (0.0~1.0)
  
  // === 統計檢驗指標 ===
  p_value: number;                   // 統計顯著性 (<0.05 為顯著)
  cohens_d: number;                  // Cohen's d 效果量 (>0.5 中效果, >0.8 大效果)
  stability_cv: number;              // 穩定性係數 (<0.3 穩定)
  
  // === 詳細統計 ===
  positive_std: number;
  negative_std: number;
  positive_sample_size: number;
  negative_sample_size: number;
  case_level_densities: Record<string, number>;
}
```

### IndicatorConfig
```typescript
interface IndicatorConfig {
  type: 'EMA' | 'RSI' | 'MACD' | 'ATR' | 'BB' | ...;
  data_source: 'close' | 'open' | 'high' | 'low' | 'volume' | 'taker_volume' | 'taker_ratio';
  params: Record<string, number>;
}
```

### MLModelConfig
```typescript
interface MLModelConfig {
  model_id: string;
  model_type: 'xgboost' | 'lightgbm' | 'lstm';
  version: string;
  created_at: string;
  
  training_config: {
    test_size: number;
    cv_folds: number;
    optuna_trials?: number;
  };
  
  performance: {
    accuracy: number;
    precision: number;
    recall: number;
    f1: number;
    auc: number;
  };
  
  feature_importance: Array<{
    feature: string;
    importance: number;
  }>;
}
```

---

## WebSocket API（未來）

### 實時進度更新
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/progress/{task_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // { progress: 0.5, status: 'running', message: '...' }
};
```

---

## 版本控制

### API版本
當前版本：`v1`

路徑格式：`/api/v{version}/{resource}`

### 版本更新策略
- **破壞性變更**：增加主版本號（v1 → v2）
- **新增功能**：維持版本號，向後兼容
- **Bug修復**：維持版本號

---

## 速率限制

### 限制規則
- 搜索API：10請求/分鐘
- 下載API：5請求/小時
- 訓練API：3請求/小時
- 其他API：60請求/分鐘

### 響應頭
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642089600
```

---

## 開發環境

### 啟動後端
```bash
cd api
python run_api.py

# 或使用uvicorn
uvicorn api.main:app --reload --port 8000
```

### API文檔
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 測試工具
```bash
# 使用curl測試
curl -X POST http://localhost:8000/api/v1/search/execute \
  -H "Content-Type: application/json" \
  -d '{"config": {...}}'

# 使用Python requests
import requests
response = requests.post(
  'http://localhost:8000/api/v1/search/execute',
  json={'config': {...}}
)
```

---

*文檔版本：1.0*  
*最後更新：2025-09-30*  
*維護者：開發團隊*