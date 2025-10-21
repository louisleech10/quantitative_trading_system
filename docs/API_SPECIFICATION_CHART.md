# 圖表系統API規格

## 文檔資訊
- **版本**: 1.0
- **最後更新**: 2025-10-20
- **適用範圍**: 階段1圖表系統API

---

## API設計原則

### RESTful風格

**資源導向**：
- 使用名詞而非動詞（/kline而非/getKline）
- 使用HTTP方法表達操作（GET, POST, PUT, DELETE）
- 使用複數形式（/cases而非/case）

**版本控制**：
- 所有端點以/api/v1為前綴
- 未來可擴展v2而不影響v1

### 統一響應格式

**成功響應**：
```json
{
  "success": true,
  "data": {
    // 實際數據
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": 1717329600,
    "version": "1.0"
  }
}
```

**錯誤響應**：
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "人類可讀的錯誤訊息",
    "details": {
      // 額外的錯誤細節
    }
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": 1717329600
  }
}
```

### 錯誤代碼規範

**格式**：`CATEGORY_SPECIFIC_ERROR`

**分類**：
- `DATA_*`：數據相關錯誤
- `VALIDATION_*`：驗證錯誤
- `DOWNLOAD_*`：下載錯誤
- `CALCULATION_*`：計算錯誤
- `SYSTEM_*`：系統錯誤

---

## 1. K線數據API

### 1.1 獲取圖表數據

**用途**：獲取用於圖表顯示的K線數據

**端點**：`GET /api/v1/chart/data`

**請求參數**（Query）：

| 參數 | 類型 | 必需 | 說明 | 範例 |
|------|------|------|------|------|
| symbol | string | ✅ | 交易對 | ETHUSDT |
| case_timestamp | int64 | ✅ | 案例時間點（Unix秒） | 1717329600 |
| timeframe | string | ✅ | 時間框架 | 1h |
| max_bars | int | ⭕ | 最大返回根數 | 200 |

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "case_timestamp": 1717329600,
    "klines": [
      {
        "timestamp": 1717240000,
        "open": 3500.5,
        "high": 3520.0,
        "low": 3495.0,
        "close": 3510.0,
        "volume": 1500.5,
        "taker_buy_volume": 825.3,
        "taker_ratio": 0.55,
        "quote_volume": 5265000.0,
        "number_of_trades": 1250
      }
      // ... 更多K線
    ],
    "center_index": 100,
    "metadata": {
      "symbol": "ETHUSDT",
      "timeframe": "1h",
      "total_bars": 200,
      "time_range": {
        "start": 1717240000,
        "end": 1717329600
      }
    }
  }
}
```

**錯誤響應**：

| HTTP狀態 | 錯誤代碼 | 說明 |
|---------|---------|------|
| 404 | DATA_NOT_FOUND | K線數據不存在 |
| 400 | VALIDATION_INVALID_SYMBOL | Symbol格式錯誤 |
| 400 | VALIDATION_INVALID_TIMEFRAME | 不支援的timeframe |
| 400 | VALIDATION_TIME_RANGE_TOO_LARGE | 請求範圍超過限制 |
| 500 | SYSTEM_CACHE_READ_ERROR | HDF5讀取失敗 |

**範例**：
```
GET /api/v1/chart/data?symbol=ETHUSDT&case_timestamp=1717329600&timeframe=1h&max_bars=200
```

---

### 1.2 查詢可用Timeframe

**用途**：查詢某symbol已緩存的timeframe列表

**端點**：`GET /api/v1/chart/timeframes`

**請求參數**（Query）：

| 參數 | 類型 | 必需 | 說明 | 範例 |
|------|------|------|------|------|
| symbol | string | ✅ | 交易對 | ETHUSDT |

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "symbol": "ETHUSDT",
    "available_timeframes": ["1h", "4h", "1d"],
    "cache_status": {
      "1h": {
        "time_range_start": 1609459200,
        "time_range_end": 1717329600,
        "total_bars": 5000,
        "last_updated": 1717500000
      },
      "4h": {
        "time_range_start": 1609459200,
        "time_range_end": 1717329600,
        "total_bars": 1250,
        "last_updated": 1717500000
      }
    }
  }
}
```

**用途場景**：前端顯示可用的timeframe選項

---

## 2. 批量下載API

### 2.1 批量下載K線

**用途**：批量下載多個案例的K線數據

**端點**：`POST /api/v1/kline/batch-download`

**請求體**（JSON）：
```json
{
  "cases": [
    {
      "symbol": "ETHUSDT",
      "timestamp": 1717329600,
      "timeframe": "1h"
    },
    {
      "symbol": "BTCUSDT",
      "timestamp": 1717416000,
      "timeframe": "4h"
    }
  ],
  "config": {
    "bars_before": 72,
    "bars_after": 24,
    "force_update": false
  }
}
```

**成功響應**（202 Accepted）：
```json
{
  "success": true,
  "data": {
    "task_id": "task-uuid-12345",
    "status": "queued",
    "total_cases": 2,
    "estimated_time": 30
  }
}
```

**說明**：
- 返回202表示任務已接受，異步執行
- 使用task_id查詢進度

---

### 2.2 查詢下載進度

**用途**：查詢批量下載任務的進度

**端點**：`GET /api/v1/kline/download-status/{task_id}`

**路徑參數**：

| 參數 | 類型 | 說明 | 範例 |
|------|------|------|------|
| task_id | string | 任務ID | task-uuid-12345 |

**成功響應**（200 OK）：

**進行中**：
```json
{
  "success": true,
  "data": {
    "task_id": "task-uuid-12345",
    "status": "running",
    "progress": {
      "completed": 5,
      "total": 10,
      "percentage": 50.0,
      "current_symbol": "ETHUSDT"
    },
    "started_at": 1717500000,
    "estimated_completion": 1717500030
  }
}
```

**已完成**：
```json
{
  "success": true,
  "data": {
    "task_id": "task-uuid-12345",
    "status": "completed",
    "progress": {
      "completed": 10,
      "total": 10,
      "percentage": 100.0
    },
    "results": {
      "succeeded": 9,
      "failed": 1,
      "failed_cases": [
        {
          "symbol": "INVALIDUSDT",
          "error": "Symbol not found"
        }
      ]
    },
    "started_at": 1717500000,
    "completed_at": 1717500025,
    "duration": 25
  }
}
```

**任務狀態值**：
- `queued`：排隊中
- `running`：執行中
- `completed`：已完成
- `failed`：失敗

---

## 3. 案例管理API

### 3.1 導入案例CSV

**用途**：上傳並解析案例CSV檔案

**端點**：`POST /api/v1/cases/import`

**請求格式**：multipart/form-data

**請求參數**：

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| file | file | ✅ | CSV或Excel檔案 |

**CSV格式要求**：
- 必須包含欄位：symbol, timeframe, datetime, Positive_case
- datetime格式：支援ISO 8601或Unix timestamp
- Positive_case值：0或1

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "import_id": "import-uuid-12345",
    "statistics": {
      "total_cases": 100,
      "positive_cases": 55,
      "negative_cases": 45,
      "unique_symbols": 10,
      "timeframes": ["1h", "4h"]
    },
    "validation": {
      "valid_cases": 98,
      "invalid_cases": 2,
      "errors": [
        {
          "row": 15,
          "error": "Invalid datetime format"
        },
        {
          "row": 42,
          "error": "Missing symbol"
        }
      ]
    }
  }
}
```

**錯誤響應**：

| HTTP狀態 | 錯誤代碼 | 說明 |
|---------|---------|------|
| 400 | VALIDATION_INVALID_FILE_FORMAT | 檔案格式不支援 |
| 400 | VALIDATION_MISSING_REQUIRED_COLUMNS | 缺少必要欄位 |
| 413 | VALIDATION_FILE_TOO_LARGE | 檔案過大 |

---

### 3.2 查詢案例列表

**用途**：獲取已導入的案例列表

**端點**：`GET /api/v1/cases`

**請求參數**（Query）：

| 參數 | 類型 | 必需 | 說明 | 範例 |
|------|------|------|------|------|
| import_id | string | ⭕ | 導入批次ID | import-uuid-12345 |
| symbol | string | ⭕ | 篩選symbol | ETHUSDT |
| timeframe | string | ⭕ | 篩選timeframe | 1h |
| label | int | ⭕ | 篩選標籤（0或1） | 1 |
| limit | int | ⭕ | 每頁數量 | 50 |
| offset | int | ⭕ | 偏移量 | 0 |

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "cases": [
      {
        "case_id": "case-uuid-1",
        "symbol": "ETHUSDT",
        "timestamp": 1717329600,
        "datetime": "2025-06-02T12:00:00Z",
        "timeframe": "4h",
        "label": 1,
        "kline_cached": true
      }
      // ... 更多案例
    ],
    "pagination": {
      "total": 100,
      "limit": 50,
      "offset": 0,
      "has_more": true
    }
  }
}
```

---

## 4. 策略信號API

### 4.1 計算策略信號

**用途**：計算指定策略的信號點

**端點**：`POST /api/v1/chart/signals`

**請求體**（JSON）：
```json
{
  "symbol": "ETHUSDT",
  "case_timestamp": 1717329600,
  "timeframe": "1h",
  "strategy": {
    "type": "ema_cross",
    "params": {
      "fast_period": 5,
      "slow_period": 20,
      "condition": "fast_above_slow"
    }
  },
  "calculation_range": {
    "bars_before": 72,
    "bars_after": 0
  }
}
```

**策略類型**：

| type | 說明 | 必要參數 |
|------|------|---------|
| ema_cross | EMA交叉 | fast_period, slow_period, condition |
| rsi_threshold | RSI閾值 | period, threshold, direction |
| macd_cross | MACD交叉 | fast, slow, signal |
| volume_spike | 成交量放量 | ma_period, multiplier |
| taker_ratio_threshold | Taker比例 | threshold, direction |

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "signals": [
      {
        "timestamp": 1717240000,
        "type": "buy",
        "position": "belowBar",
        "color": "#4caf50",
        "indicators": {
          "EMA5": 3505.2,
          "EMA20": 3500.1,
          "difference": 5.1,
          "difference_pct": 0.14
        }
      },
      {
        "timestamp": 1717250000,
        "type": "buy",
        "position": "belowBar",
        "color": "#4caf50",
        "indicators": {
          "EMA5": 3510.5,
          "EMA20": 3502.3,
          "difference": 8.2,
          "difference_pct": 0.23
        }
      }
      // ... 更多信號
    ],
    "calculation_range": {
      "start": 1717066800,
      "end": 1717329600
    },
    "statistics": {
      "total_bars_analyzed": 72,
      "signals_count": 15,
      "signal_rate": 0.208
    }
  }
}
```

**錯誤響應**：

| HTTP狀態 | 錯誤代碼 | 說明 |
|---------|---------|------|
| 400 | VALIDATION_INVALID_STRATEGY_TYPE | 不支援的策略類型 |
| 400 | VALIDATION_INVALID_STRATEGY_PARAMS | 策略參數錯誤 |
| 404 | DATA_NOT_FOUND | K線數據不存在 |
| 500 | CALCULATION_INDICATOR_ERROR | 指標計算失敗 |

---

### 4.2 查詢預設策略

**用途**：獲取系統預設策略列表

**端點**：`GET /api/v1/strategies/presets`

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "strategies": [
      {
        "id": "ema_5_20_cross",
        "name": "EMA5 > EMA20 (短期上升)",
        "type": "ema_cross",
        "params": {
          "fast_period": 5,
          "slow_period": 20,
          "condition": "fast_above_slow"
        },
        "description": "短期均線在長期均線上方，表示短期上升趨勢"
      },
      {
        "id": "rsi_oversold",
        "name": "RSI < 30 (超賣)",
        "type": "rsi_threshold",
        "params": {
          "period": 14,
          "threshold": 30,
          "direction": "below"
        },
        "description": "RSI低於30，可能出現反彈"
      }
      // ... 更多預設策略
    ]
  }
}
```

---

## 5. ML特徵提取API

### 5.1 提取特徵

**用途**：批量提取ML訓練特徵

**端點**：`POST /api/v1/ml/extract-features`

**請求體**（JSON）：
```json
{
  "import_id": "import-uuid-12345",
  "config": {
    "feature_timeframe": "1h",
    "bars_before": 72,
    "bars_after": 24,
    "features": {
      "use_raw_kline": true,
      "use_indicators": true,
      "use_taker_ratio": true,
      "indicators": ["EMA5", "EMA20", "EMA50", "RSI14", "MACD"]
    },
    "preprocessing": {
      "normalize": true,
      "handle_missing": "drop"
    }
  }
}
```

**成功響應**（202 Accepted）：
```json
{
  "success": true,
  "data": {
    "task_id": "feature-task-uuid-12345",
    "status": "queued",
    "total_cases": 100,
    "estimated_time": 120
  }
}
```

---

### 5.2 查詢特徵提取進度

**用途**：查詢特徵提取任務進度

**端點**：`GET /api/v1/ml/feature-status/{task_id}`

**路徑參數**：

| 參數 | 類型 | 說明 |
|------|------|------|
| task_id | string | 任務ID |

**成功響應**（200 OK）：

**進行中**：
```json
{
  "success": true,
  "data": {
    "task_id": "feature-task-uuid-12345",
    "status": "running",
    "progress": {
      "phase": "extracting_features",
      "completed": 45,
      "total": 100,
      "percentage": 45.0,
      "current_step": "計算技術指標"
    },
    "started_at": 1717500000
  }
}
```

**已完成**：
```json
{
  "success": true,
  "data": {
    "task_id": "feature-task-uuid-12345",
    "status": "completed",
    "progress": {
      "completed": 100,
      "total": 100,
      "percentage": 100.0
    },
    "results": {
      "feature_file": "path/to/ml_features.h5",
      "feature_id": "features-uuid-12345",
      "statistics": {
        "total_cases": 100,
        "valid_cases": 98,
        "invalid_cases": 2,
        "features_count": 450,
        "positive_ratio": 0.55,
        "data_quality": "good"
      },
      "splits": {
        "train": 70,
        "validation": 10,
        "test": 20
      }
    },
    "started_at": 1717500000,
    "completed_at": 1717500120,
    "duration": 120
  }
}
```

---

### 5.3 載入特徵數據

**用途**：載入已生成的Feature Matrix

**端點**：`GET /api/v1/ml/features/{feature_id}`

**路徑參數**：

| 參數 | 類型 | 說明 |
|------|------|------|
| feature_id | string | 特徵數據ID |

**請求參數**（Query）：

| 參數 | 類型 | 必需 | 說明 | 範例 |
|------|------|------|------|------|
| split | string | ⭕ | 數據集分割 | train |
| format | string | ⭕ | 返回格式 | json |

**split可選值**：
- `train`：訓練集
- `validation`：驗證集
- `test`：測試集
- `all`：全部數據

**format可選值**：
- `json`：JSON格式（預設，適合小數據）
- `hdf5_path`：返回HDF5檔案路徑（適合大數據）

**成功響應**（200 OK，format=json）：
```json
{
  "success": true,
  "data": {
    "feature_id": "features-uuid-12345",
    "split": "train",
    "features": [
      [0.55, 3500.5, 3510.0, ...],  // 案例1特徵向量
      [0.52, 3505.2, 3515.1, ...]   // 案例2特徵向量
      // ... 更多案例
    ],
    "labels": [1, 0, 1, ...],
    "metadata": {
      "feature_names": ["taker_ratio_t-1", "close_t-1", ...],
      "case_ids": ["case-uuid-1", "case-uuid-2", ...],
      "shape": [70, 450],
      "config": {
        "feature_timeframe": "1h",
        "bars_before": 72,
        "bars_after": 24
      }
    }
  }
}
```

**成功響應**（200 OK，format=hdf5_path）：
```json
{
  "success": true,
  "data": {
    "feature_id": "features-uuid-12345",
    "hdf5_path": "/path/to/ml_features.h5",
    "access_info": {
      "features_key": "/features/data",
      "labels_key": "/labels/data",
      "metadata_key": "/metadata"
    }
  }
}
```

---

## 6. ML配置API

### 6.1 查詢ML配置

**用途**：獲取當前ML配置

**端點**：`GET /api/v1/ml/config`

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "feature_extraction": {
      "timeframe": "1h",
      "bars_before": 72,
      "bars_after": 24
    },
    "features": {
      "use_raw_kline": true,
      "use_indicators": true,
      "use_taker_ratio": true,
      "indicators": ["EMA5", "EMA20", "EMA50", "RSI14", "MACD"]
    },
    "preprocessing": {
      "normalize": true,
      "handle_missing": "drop"
    },
    "training": {
      "test_size": 0.2,
      "validation_size": 0.1,
      "random_state": 42,
      "stratify": true
    }
  }
}
```

---

### 6.2 更新ML配置

**用途**：更新ML配置

**端點**：`PUT /api/v1/ml/config`

**請求體**（JSON）：
```json
{
  "feature_extraction": {
    "timeframe": "4h",
    "bars_before": 100,
    "bars_after": 20
  },
  "features": {
    "indicators": ["EMA5", "EMA20", "RSI14"]
  }
}
```

**成功響應**（200 OK）：
```json
{
  "success": true,
  "data": {
    "message": "配置已更新",
    "updated_config": {
      // ... 完整的新配置
    }
  }
}
```

**錯誤響應**：

| HTTP狀態 | 錯誤代碼 | 說明 |
|---------|---------|------|
| 400 | VALIDATION_INVALID_TIMEFRAME | timeframe不支援 |
| 400 | VALIDATION_BARS_OUT_OF_RANGE | bars數值超出範圍 |
| 400 | VALIDATION_INVALID_INDICATOR | 指標不存在 |

---

## 7. 通用錯誤處理

### 常見HTTP狀態碼

| 狀態碼 | 說明 | 使用場景 |
|-------|------|---------|
| 200 | OK | 請求成功 |
| 202 | Accepted | 異步任務已接受 |
| 400 | Bad Request | 請求參數錯誤 |
| 404 | Not Found | 資源不存在 |
| 413 | Payload Too Large | 請求體過大 |
| 429 | Too Many Requests | 速率限制 |
| 500 | Internal Server Error | 伺服器錯誤 |
| 503 | Service Unavailable | 服務暫時不可用 |

### 錯誤代碼完整列表

**數據錯誤（DATA_*）**：
- `DATA_NOT_FOUND`：數據不存在
- `DATA_INCOMPLETE`：數據不完整
- `DATA_CORRUPTED`：數據損壞

**驗證錯誤（VALIDATION_*）**：
- `VALIDATION_INVALID_SYMBOL`：Symbol格式錯誤
- `VALIDATION_INVALID_TIMEFRAME`：Timeframe不支援
- `VALIDATION_INVALID_TIMESTAMP`：時間戳格式錯誤
- `VALIDATION_MISSING_REQUIRED_FIELD`：缺少必要欄位
- `VALIDATION_INVALID_FILE_FORMAT`：檔案格式錯誤
- `VALIDATION_TIME_RANGE_TOO_LARGE`：時間範圍過大
- `VALIDATION_INVALID_STRATEGY_TYPE`：策略類型錯誤
- `VALIDATION_INVALID_STRATEGY_PARAMS`：策略參數錯誤

**下載錯誤（DOWNLOAD_*）**：
- `DOWNLOAD_API_RATE_LIMIT`：API速率限制
- `DOWNLOAD_API_ERROR`：API返回錯誤
- `DOWNLOAD_NETWORK_ERROR`：網路錯誤

**計算錯誤（CALCULATION_*）**：
- `CALCULATION_INDICATOR_ERROR`：指標計算失敗
- `CALCULATION_FEATURE_ERROR`：特徵計算失敗

**系統錯誤（SYSTEM_*）**：
- `SYSTEM_CACHE_READ_ERROR`：快取讀取失敗
- `SYSTEM_CACHE_WRITE_ERROR`：快取寫入失敗
- `SYSTEM_OUT_OF_MEMORY`：記憶體不足
- `SYSTEM_TASK_QUEUE_FULL`：任務佇列已滿

---

## 8. 速率限制

### 限制規則

**一般端點**：
- 每分鐘100次請求
- 超過限制返回429狀態碼

**批量操作端點**：
- 每分鐘10次請求
- 包括：batch-download, extract-features

**速率限制響應**：
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "請求過於頻繁，請稍後再試",
    "details": {
      "limit": 100,
      "window": 60,
      "retry_after": 30
    }
  }
}
```

**Headers**：
- `X-RateLimit-Limit`：限制數量
- `X-RateLimit-Remaining`：剩餘次數
- `X-RateLimit-Reset`：重置時間（Unix時間戳）

---

## 9. 認證與授權

### 當前版本

**本地開發**：無需認證

**說明**：
- 階段1僅本地使用
- 無需API Key或Token
- 未來擴展到雲端時再加入認證

### 未來擴展（規劃）

**API Key認證**：
- Header：`X-API-Key: your-api-key`
- 每個使用者唯一的API Key

**JWT Token**：
- Header：`Authorization: Bearer <token>`
- 支援使用者登入系統

---

## 10. 測試與除錯

### 測試端點

**健康檢查**：`GET /api/v1/health`

**響應**：
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": 1717500000,
    "services": {
      "database": "ok",
      "cache": "ok",
      "task_queue": "ok"
    }
  }
}
```

### 除錯模式

**開啟方式**：設定環境變數 `DEBUG=true`

**影響**：
- 錯誤響應包含詳細堆疊追蹤
- LOG級別提升到DEBUG
- 返回額外的除錯資訊

**範例**（除錯模式下的錯誤響應）：
```json
{
  "success": false,
  "error": {
    "code": "CALCULATION_INDICATOR_ERROR",
    "message": "RSI計算失敗",
    "details": {
      "indicator": "RSI14",
      "data_points": 10,
      "required_points": 14
    },
    "debug_info": {
      "traceback": "...",
      "function": "calculate_rsi",
      "line": 125
    }
  }
}
```

---

## 11. API版本演進

### 版本策略

**當前版本**：v1

**未來計劃**：
- v1保持穩定，不做破壞性變更
- 新功能優先加入v1（向後兼容）
- 重大變更時發布v2

### 廢棄通知

**流程**：
1. 提前3個月宣布廢棄
2. 響應Header添加 `X-API-Deprecated: true`
3. 文檔標註廢棄時間
4. 提供遷移指南

---

## 總結

本API規格定義了圖表系統的**完整API介面**，涵蓋K線數據、批量下載、案例管理、策略信號、ML特徵提取等所有功能。

**核心特點**：
- ✅ RESTful設計風格
- ✅ 統一的響應格式
- ✅ 完整的錯誤處理
- ✅ 清晰的錯誤代碼
- ✅ 速率限制保護
- ✅ 易於測試和除錯

**設計原則遵循**：
- ✅ 資源導向（名詞而非動詞）
- ✅ 語義化HTTP方法
- ✅ 版本控制
- ✅ 向後兼容
- ✅ 文檔完整

---

*文檔版本：1.0*  
*最後更新：2025-10-20*  
*維護者：開發團隊*