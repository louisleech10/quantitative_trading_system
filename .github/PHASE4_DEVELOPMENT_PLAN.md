# Phase 4 Development Plan - Pattern Discovery System
> **ML-first Pattern Discovery** | Not Prediction, but Pattern Recognition  
> **Version**: 1.0 | **Created**: 2026-01-10 | **Status**: 📋 Planning

---

## 🎯 Phase 4 Core Objective

**First Principle**: 從歷史數據中自動發現有效的交易模式，而非預測未來價格

**System Goal**: 
- 輸入：Optuna 優化後的策略參數 + HDF5 歷史數據
- 處理：自動特徵工程（25-32 features）→ XGBoost 分析 → 特徵重要性排序
- 輸出：可解釋的交易模式規則（前 5-10 個關鍵特徵組合）

**NOT in Scope**:
- ❌ 價格預測模型
- ❌ 實時交易執行
- ❌ 複雜的深度學習模型
- ❌ 多策略組合優化

---

## 📋 Task Breakdown

### Task 4.1: Feature Engineering System (Week 17-18, ~4,000 lines)

**Objective**: 根據 Optuna 優化後的策略參數，動態生成對應的交易特徵

**⚠️ 重要設計原則**:
- **動態特徵生成**：不是固定 32 個特徵，而是根據策略參數動態計算
- **策略依賴性**：目前僅支持 EMA 三線策略，未來可擴展其他策略
- **參數化特徵**：例如 Optuna 優化出 ema_short=5, ema_mid=20, ema_long=60 → 生成對應 EMA 特徵
- **Timeframe 可選**：支援多時間週期（1h, 4h, 12h, 1d），與指標策略測試和 Optuna 保持一致

**📊 測試數據規格** (data_cache/kline_cache.h5 + cases.json):
- **標的**: ETHUSDT（165 個案例：55 正例 + 110 反例）
- **可用時間週期**:
  - `1h`: 20,401 筆數據（指標策略測試和 Optuna 使用）
  - `4h`: 151 筆數據
  - `12h`: 197 筆數據（案例搜尋使用）
  - `1d`: 148 筆數據
- **備註**: BTCUSDT 早期測試數據已於 2026-01-10 刪除，避免誤用

#### Technical Specifications

**Backend Components**:
```
momentum/FeatureEngineering/
├── feature_extractor.py          # 核心特徵提取引擎
│   ├── extract_features_from_strategy()  # 根據策略參數提取特徵
│   ├── extract_price_features()   # 價格特徵（通用）
│   ├── extract_volume_features()  # 成交量特徵（通用）
│   ├── extract_ema_features()     # EMA 指標特徵（參數化）
│   └── extract_signal_features()  # 信號特徵（基於策略邏輯）
├── feature_validator.py          # 特徵驗證器
│   ├── validate_no_future_leak() # 確保無未來函數
│   ├── validate_no_nan()         # 檢查 NaN 值
│   └── validate_correlation()    # 檢查高相關性 (>0.95)
└── feature_storage.py            # 特徵儲存管理
    ├── save_features_to_hdf5()   # 儲存至 HDF5
    └── load_features_from_hdf5() # 從 HDF5 讀取

api/services/
└── feature_task_service.py       # 非同步特徵提取服務
    ├── start_feature_extraction_task()
    ├── get_task_status()
    └── get_feature_summary()

api/routes/
└── feature_engineering.py        # REST API 路由
    ├── POST /api/v1/features/extract
    ├── GET /api/v1/features/task/{id}
    └── GET /api/v1/features/summary/{case_id}
```

**動態特徵生成架構**:

**Stage 1: 通用價格特徵** (不依賴策略參數，~8 個):
1. `price_change_pct` - 價格變化百分比 (close/open - 1)
2. `high_low_range_pct` - 高低價範圍百分比 ((high-low)/open)
3. `close_position_in_range` - 收盤價在高低範圍的位置 ((close-low)/(high-low))
4. `price_volatility_5` - 5 期價格波動率 (std(close)/mean(close))
5. `price_momentum_3` - 3 期價格動量 (close - close.shift(3))
6. `upper_shadow_pct` - 上影線百分比 ((high-max(open,close))/open)
7. `lower_shadow_pct` - 下影線百分比 ((min(open,close)-low)/open)
8. `body_pct` - K線實體百分比 (abs(close-open)/open)

**Stage 2: 通用成交量特徵** (不依賴策略參數，~6 個):
9. `volume_change_pct` - 成交量變化百分比 (volume/volume.shift(1) - 1)
10. `volume_ma_ratio_5` - 成交量與 5 期均量比 (volume/volume.rolling(5).mean())
11. `taker_buy_ratio` - 主動買入比例 (taker_buy_volume/volume)
12. `taker_buy_value_ratio` - 主動買入金額比例 (taker_buy_quote_volume/quote_volume)
13. `volume_price_correlation_5` - 5 期量價相關性 (corr(volume, close))
14. `abnormal_volume_flag` - 異常成交量標記 (volume > 2 * volume.rolling(20).mean())

**Stage 3: 策略參數化特徵** (依賴 Optuna 優化參數，動態生成):

**Example: EMA 三線策略** (ema_short=5, ema_mid=20, ema_long=60)
15. `ema_{short}` - EMA(5) 值
16. `ema_{mid}` - EMA(20) 值
17. `ema_{long}` - EMA(60) 值
18. `ema_distance_{short}_{mid}` - EMA(5) 與 EMA(20) 距離 ((ema5-ema20)/ema20)
19. `ema_distance_{mid}_{long}` - EMA(20) 與 EMA(60) 距離 ((ema20-ema60)/ema60)
20. `ema_trend_aligned` - EMA 趨勢對齊 (ema5 > ema20 > ema60)
21. `ema_cross_signal_{short}_{mid}` - EMA(5) 穿越 EMA(20) 信號

**Example: Volume Threshold 特徵** (volume_threshold=0.6)
22. `volume_spike_{threshold}` - 成交量激增 (taker_ratio > 0.6)
23. `taker_ratio_distance_{threshold}` - 主動買入比例與閾值距離 (taker_ratio - 0.6)

**Stage 4: 信號組合特徵** (基於策略邏輯):
24. `entry_signal_score` - 進場信號分數（組合 EMA 趨勢 + 成交量條件）
25. `trend_consistency_5` - 5 期趨勢一致性（連續 5 期同方向）
26. `signal_strength` - 信號強度（基於多個條件的加權）

**⚠️ 特徵數量說明**:
- 不是固定 25-32 個，而是根據策略參數動態生成
- EMA 三線策略：預計 20-26 個特徵
- 未來擴展其他策略時，特徵數量會增加
- 避免過度工程化，先實現 EMA 三線策略的特徵提取

**Data Storage Format** (HDF5):
```python
# Path: data_cache/features/{case_id}.h5
# Structure:
/{symbol}/{timeframe}/  # 例如：/ETHUSDT/1h/ 或 /ETHUSDT/12h/
    /features          # Dataset: (n_samples, n_features) float32, 動態列數
    /feature_names     # Attribute: List[str] 動態生成的特徵名稱
    /labels            # Dataset: (n_samples,) int32, 1=盈利, 0=虧損
    /timestamps        # Dataset: (n_samples,) int64, Unix timestamp
    /metadata          # Attributes: extraction_time, strategy_type, strategy_params, timeframe
    /generation_info   # Attributes: feature_count, generation_method="dynamic"

# Timeframe 說明（ETHUSDT 可用數據）：
# - 1h: 20,401 筆（指標策略測試、Optuna 使用）
# - 4h: 151 筆
# - 12h: 197 筆（案例搜尋使用）
# - 1d: 148 筆
# XGBoost 可選擇任意 timeframe，建議使用 1h（數據量最大）
```

**API Endpoints**:

```python
# POST /api/v1/features/extract
Request:
{
    "case_id": "ETHUSDT_1735905600_1",      # 案例 ID（格式：symbol_timestamp_index）
    "symbol": "ETHUSDT",                    # 交易標的
    "timeframe": "1h",                      # 時間週期（可選：1h, 4h, 12h, 1d）
    "strategy_type": "ema_three_line",      # 策略類型（目前僅支持 ema_three_line）
    "strategy_params": {  # Optuna 優化後的參數
        "ema_short": 5,
        "ema_mid": 20,
        "ema_long": 60,
        "volume_threshold": 0.6
    },
    "include_basic_features": true,  # 是否包含通用價格/成交量特徵
    "validate": true                  # 是否執行驗證
}

Response:
{
    "task_id": "feat_123abc",
    "status": "running",
    "estimated_time": 30  # seconds
}

# GET /api/v1/features/task/{task_id}
Response:
{
    "task_id": "feat_123abc",
    "status": "completed",  # "running" | "completed" | "failed"
    "progress": 100,
    "result": {
        "case_id": "ETHUSDT_1735905600_1",
        "symbol": "ETHUSDT",
        "timeframe": "1h",  # 使用的時間週期
        "strategy_type": "ema_three_line",
        "n_samples": 480,  # 實際 K 線數量（取決於 case 時間範圍）
        "n_features": 26,  # 動態生成的特徵數量
        "feature_names": ["price_change_pct", "ema_distance_5_20", ...],
        "storage_path": "data_cache/features/ETHUSDT_1735905600_1.h5",
        "validation": {
            "has_nan": false,
            "has_inf": false,
            "max_correlation": 0.87,
            "warnings": []
        }
    },
    "error": null
}

# GET /api/v1/features/summary/{case_id}
Response:
{
    "case_id": "ETHUSDT_1735905600_1",
    "symbol": "ETHUSDT",
    "timeframe": "1h",
    "feature_count": 26,  # 動態生成，取決於策略參數（EMA 三線約 26 個）
    "sample_count": 480,  # 實際 K 線數量
    "feature_stats": {
        "price_change_pct": {"mean": 0.002, "std": 0.015, "min": -0.08, "max": 0.12},
        "volume_change_pct": {"mean": 0.05, "std": 0.3, "min": -0.7, "max": 2.5},
        // ... 其他特徵統計
    },
    "correlation_matrix": [...],  # 32x32 相關性矩陣
    "high_correlation_pairs": [
        {"feature1": "ema_distance_5_20", "feature2": "ema_trend_aligned", "corr": 0.92}
    ]
}
```

#### Acceptance Criteria

**Auto-Tests** (pytest) - ⚠️ 必須使用真實數據，不能有硬編碼或假設:
- ✅ `test_feature_extraction_ema_strategy()` - EMA 三線策略特徵提取（使用真實 Case）
- ✅ `test_feature_no_future_leak()` - 確保無未來函數（檢查時間序列依賴）
- ✅ `test_feature_no_nan_inf()` - 無 NaN/Inf 值（使用真實 Case 測試）
- ✅ `test_feature_correlation_threshold()` - 高相關性檢測 (>0.95)
- ✅ `test_feature_storage_hdf5()` - HDF5 儲存讀取（使用真實 Case）
- ✅ `test_feature_api_endpoints()` - API 端點測試（使用真實 Case ID）
- ✅ `test_dynamic_feature_generation()` - 動態特徵生成測試（不同參數組合）

**Edge Case Tests** (pytest) - ⚠️ 必須考慮邊緣情況:
- ✅ `test_edge_case_empty_data()` - 空數據處理
- ✅ `test_edge_case_single_sample()` - 單一樣本處理
- ✅ `test_edge_case_missing_columns()` - 缺失欄位處理（例如 taker_volume）
- ✅ `test_edge_case_zero_volume()` - 零成交量處理（避免除零錯誤）
- ✅ `test_edge_case_extreme_values()` - 極端價格值處理（價格暴漲/暴跌）
- ✅ `test_edge_case_invalid_strategy_params()` - 無效策略參數處理
- ✅ `test_edge_case_unsupported_strategy()` - 不支持的策略類型處理

**Human Validation** (需人工確認):
- 🔍 特徵工程邏輯合理性（例如：ema_distance_5_20 計算是否正確）
- 🔍 特徵統計分佈是否符合預期（使用真實 Case 的統計結果）
- 🔍 高相關性特徵對是否需要移除（基於真實數據的相關性矩陣）
- 🔍 Optuna 參數是否正確傳遞到特徵計算（比對 strategy_params）

---

### Task 4.2: XGBoost Analysis Engine (Week 19, ~2,500 lines)

**Objective**: 使用 XGBoost 分析特徵重要性，找出關鍵交易模式

#### Technical Specifications

**Backend Components**:
```
momentum/Analysis/
├── xgboost_analyzer.py           # XGBoost 分析引擎
│   ├── train_model()             # 訓練 XGBoost 模型
│   ├── calculate_feature_importance() # 計算特徵重要性
│   ├── extract_top_patterns()    # 提取前 N 個模式
│   └── validate_model()          # 模型驗證 (交叉驗證)
├── pattern_extractor.py          # 模式提取器
│   ├── extract_decision_rules()  # 從決策樹提取規則
│   ├── simplify_rules()          # 簡化規則
│   └── rank_rules_by_importance() # 規則重要性排序
└── model_storage.py              # 模型儲存管理
    ├── save_model_to_pickle()
    └── load_model_from_pickle()

api/services/
└── xgboost_task_service.py       # 非同步 XGBoost 分析服務
    ├── start_xgboost_analysis_task()
    ├── get_analysis_result()
    └── get_feature_importance()

api/routes/
└── pattern_analysis.py           # REST API 路由
    ├── POST /api/v1/patterns/analyze
    ├── GET /api/v1/patterns/task/{id}
    └── GET /api/v1/patterns/importance/{case_id}
```

**XGBoost Configuration**:
```python
xgboost_params = {
    # Model parameters
    "objective": "binary:logistic",  # 盈利 vs 虧損二分類
    "eval_metric": "auc",            # AUC-ROC 評估
    "max_depth": 5,                  # 決策樹深度 (避免過擬合)
    "learning_rate": 0.05,           # 學習率
    "n_estimators": 100,             # 樹的數量
    "subsample": 0.8,                # 樣本採樣比例
    "colsample_bytree": 0.8,         # 特徵採樣比例
    "min_child_weight": 5,           # 最小葉子節點樣本數
    "gamma": 0.1,                    # 分裂最小損失減少
    
    # Regularization
    "reg_alpha": 0.1,                # L1 正則化
    "reg_lambda": 1.0,               # L2 正則化
    
    # Other
    "random_state": 42,
    "n_jobs": -1,                    # 使用所有 CPU 核心
    "verbosity": 0
}

# Cross-validation
cv_params = {
    "n_splits": 5,                   # 5-fold 交叉驗證
    "shuffle": True,
    "random_state": 42
}
```

**Feature Importance Methods**:
1. **Gain** (default): 該特徵對模型的平均貢獻
2. **Weight**: 該特徵在所有樹中被使用的次數
3. **Cover**: 該特徵影響的樣本數量

**API Endpoints**:

```python
# POST /api/v1/patterns/analyze
Request:
{
    "case_id": "ETHUSDT_1735905600_1",      # 案例 ID（格式：symbol_timestamp_index）
    "symbol": "ETHUSDT",                    # 交易標的
    "timeframe": "1h",                      # 時間週期（可選：1h, 4h, 12h, 1d）
    "model_params": {  # 可選，使用預設值
        "max_depth": 5,
        "n_estimators": 100
    },
    "cv_folds": 5,
    "top_n_features": 10  # 提取前 N 個重要特徵
}

Response:
{
    "task_id": "xgb_456def",
    "status": "running",
    "estimated_time": 60  # seconds
}

# GET /api/v1/patterns/task/{task_id}
Response:
{
    "task_id": "xgb_456def",
    "status": "completed",
    "result": {
        "case_id": "ETHUSDT_1735905600_1",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "model_performance": {
            "train_auc": 0.85,
            "cv_auc_mean": 0.78,
            "cv_auc_std": 0.03,
            "overfitting_score": 0.07  # train_auc - cv_auc_mean
        },
        "feature_importance": {
            "top_10_features": [
                {"rank": 1, "feature": "ema_distance_5_20", "importance": 0.25, "method": "gain"},
                {"rank": 2, "feature": "taker_buy_ratio", "importance": 0.18, "method": "gain"},
                {"rank": 3, "feature": "rsi_14", "importance": 0.12, "method": "gain"},
                // ... 前 10 個特徵
            ],
            "all_features": [...]  # 所有 32 個特徵的重要性
        },
        "decision_rules": [
            {
                "rule_id": 1,
                "condition": "ema_distance_5_20 > 0.02 AND taker_buy_ratio > 0.6",
                "support": 250,      # 符合此規則的樣本數
                "confidence": 0.82,  # 盈利概率
                "lift": 1.5          # 相對於基準的提升
            },
            // ... 前 5-10 條規則
        ],
        "model_path": "data_cache/models/ETHUSDT_1735905600_1.pkl"
    }
}

# GET /api/v1/patterns/importance/{case_id}
Response:
{
    "case_id": "ETHUSDT_1735905600_1",
    "symbol": "ETHUSDT",
    "timeframe": "1h",
    "feature_importance": [...],  # 同上
    "importance_chart_data": {
        "labels": ["ema_distance_5_20", "taker_buy_ratio", ...],
        "values": [0.25, 0.18, ...]
    }
}
```

#### Acceptance Criteria

**Auto-Tests** (pytest) - ⚠️ 必須使用真實數據:
- ✅ `test_xgboost_training()` - XGBoost 訓練測試（使用真實 Case 特徵）
- ✅ `test_feature_importance_calculation()` - 特徵重要性計算（驗證 gain/weight/cover）
- ✅ `test_cross_validation()` - 交叉驗證測試（5-fold CV）
- ✅ `test_overfitting_detection()` - 過擬合檢測 (train_auc - cv_auc > 0.15)
- ✅ `test_decision_rule_extraction()` - 決策規則提取（驗證規則數量 3-10 條）
- ✅ `test_model_persistence()` - 模型儲存與載入（Pickle 格式）

**Edge Case Tests** (pytest) - ⚠️ 必須考慮邊緣情況:
- ✅ `test_edge_case_imbalanced_labels()` - 不平衡標籤處理（盈利/虧損比例極端）
- ✅ `test_edge_case_insufficient_samples()` - 樣本數不足處理（< 100 樣本）
- ✅ `test_edge_case_single_class()` - 單一類別處理（全部盈利或全部虧損）
- ✅ `test_edge_case_constant_features()` - 常數特徵處理（特徵值全部相同）
- ✅ `test_edge_case_high_correlation_features()` - 高相關性特徵處理（>0.95）
- ✅ `test_edge_case_cv_fold_too_small()` - CV fold 樣本數過少處理

**Human Validation** (需人工確認):
- 🔍 模型效能合理性（CV AUC, precision, recall）
- 🔍 Overfitting 檢查（train vs CV performance）
- 🔍 Top 10 特徵重要性分佈合理（前 3 名不應佔 >70%）
- 🔍 決策規則可解釋性（例如：ema_distance_5_20 > 0.02 在交易上合理嗎？）
- 🔍 規則的 support 和 confidence 是否符合預期

---

### Task 4.3: Pattern Definition & Storage (Week 20, ~2,000 lines)

**Objective**: 將 XGBoost 發現的模式轉換為可儲存、可查詢的結構化定義

#### Technical Specifications

**Backend Components**:
```
momentum/Analysis/
├── pattern_definition.py         # 模式定義
│   ├── PatternRule (dataclass)   # 單條規則定義
│   ├── Pattern (dataclass)       # 完整模式定義
│   └── PatternLibrary (class)    # 模式庫管理
├── pattern_storage.py            # 模式儲存
│   ├── save_pattern_to_json()    # 儲存為 JSON
│   ├── load_pattern_from_json()  # 從 JSON 載入
│   └── query_patterns()          # 查詢模式
└── pattern_validator.py          # 模式驗證器
    ├── validate_rule_syntax()    # 規則語法驗證
    ├── validate_feature_names()  # 特徵名稱驗證
    └── validate_thresholds()     # 閾值合理性驗證

api/services/
└── pattern_management_service.py # 模式管理服務
    ├── create_pattern()
    ├── get_pattern()
    ├── list_patterns()
    ├── update_pattern()
    └── delete_pattern()

api/routes/
└── pattern_management.py         # REST API 路由
    ├── POST /api/v1/patterns/define
    ├── GET /api/v1/patterns/{pattern_id}
    ├── GET /api/v1/patterns/list
    ├── PUT /api/v1/patterns/{pattern_id}
    └── DELETE /api/v1/patterns/{pattern_id}
```

**Pattern Data Structure**:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class PatternRule:
    """單條模式規則"""
    feature: str           # 特徵名稱 (e.g., "ema_distance_5_20")
    operator: str          # 運算符 (">" | "<" | ">=" | "<=" | "==" | "!=")
    threshold: float       # 閾值
    description: str       # 中文描述 (e.g., "EMA5 高於 EMA20 2%以上")

@dataclass
class Pattern:
    """完整模式定義"""
    pattern_id: str                    # 唯一 ID (e.g., "PAT_001")
    name: str                          # 模式名稱 (e.g., "強勢突破模式")
    description: str                   # 模式描述
    rules: List[PatternRule]           # 規則列表 (AND 關係)
    case_id: str                       # 來源案例 ID
    xgboost_importance: Dict[str, float]  # XGBoost 特徵重要性
    performance_metrics: Dict[str, float] # 模式表現指標
    created_at: datetime
    updated_at: datetime
    status: str                        # "active" | "archived" | "testing"
    tags: List[str]                    # 標籤 (e.g., ["趨勢", "成交量"])
    metadata: Dict                     # 其他元數據

# Example:
pattern_example = Pattern(
    pattern_id="PAT_001",
    name="EMA順勢+成交量確認模式",
    description="EMA三線順勢排列，且主動買入比例超過60%，顯示強勢上漲動能",
    rules=[
        PatternRule(
            feature="ema_distance_5_20",
            operator=">",
            threshold=0.02,
            description="EMA5 高於 EMA20 2%以上"
        ),
        PatternRule(
            feature="ema_distance_20_60",
            operator=">",
            threshold=0.01,
            description="EMA20 高於 EMA60 1%以上"
        ),
        PatternRule(
            feature="taker_buy_ratio",
            operator=">",
            threshold=0.6,
            description="主動買入比例超過60%"
        ),
        PatternRule(
            feature="volume_ma_ratio_5",
            operator=">",
            threshold=1.2,
            description="成交量為5期均量1.2倍以上"
        )
    ],
    case_id="ETHUSDT_1735905600_1",
    xgboost_importance={
        "ema_distance_5_20": 0.25,
        "ema_distance_20_60": 0.15,
        "taker_buy_ratio": 0.18,
        "volume_ma_ratio_5": 0.12
    },
    performance_metrics={
        "support": 250,       # 符合此模式的樣本數
        "confidence": 0.82,   # 盈利概率
        "lift": 1.5,          # 相對基準的提升
        "cv_auc": 0.78        # 交叉驗證 AUC
    },
    created_at=datetime.now(),
    updated_at=datetime.now(),
    status="active",
    tags=["趨勢", "成交量", "EMA"],
    metadata={
        "strategy": "momentum",
        "symbol": "ETHUSDT",
        "timeframe": "1h",  # 可選：1h, 4h, 12h, 1d
        "data_source": "kline_cache.h5"
    }
)
```

**Storage Format** (JSON):
```json
// Path: data_cache/patterns/PAT_001.json
{
    "pattern_id": "PAT_001",
    "name": "EMA順勢+成交量確認模式",
    "description": "EMA三線順勢排列，且主動買入比例超過60%，顯示強勢上漲動能",
    "rules": [
        {
            "feature": "ema_distance_5_20",
            "operator": ">",
            "threshold": 0.02,
            "description": "EMA5 高於 EMA20 2%以上"
        },
        // ... 其他規則
    ],
    "case_id": "ETHUSDT_1735905600_1",
    "xgboost_importance": {...},
    "performance_metrics": {...},
    "created_at": "2026-01-10T10:00:00Z",
    "updated_at": "2026-01-10T10:00:00Z",
    "status": "active",
    "tags": ["趨勢", "成交量", "EMA"],
    "metadata": {...}
}

// Path: data_cache/patterns/pattern_index.json
{
    "patterns": [
        {
            "pattern_id": "PAT_001",
            "name": "EMA順勢+成交量確認模式",
            "status": "active",
            "created_at": "2026-01-10T10:00:00Z",
            "file_path": "data_cache/patterns/PAT_001.json"
        },
        // ... 其他模式
    ],
    "last_updated": "2026-01-10T10:00:00Z"
}
```

**API Endpoints**:

```python
# POST /api/v1/patterns/define
Request:
{
    "name": "EMA順勢+成交量確認模式",
    "description": "...",
    "rules": [...],  # List[PatternRule]
    "case_id": "ETHUSDT_1735905600_1",
    "xgboost_importance": {...},
    "performance_metrics": {...},
    "tags": ["趨勢", "成交量"]
}

Response:
{
    "pattern_id": "PAT_001",
    "status": "created",
    "file_path": "data_cache/patterns/PAT_001.json"
}

# GET /api/v1/patterns/{pattern_id}
Response:
{
    "pattern": {
        "pattern_id": "PAT_001",
        "name": "...",
        "case_id": "ETHUSDT_1735905600_1",
        // ... 完整 Pattern 物件
    }
}

# GET /api/v1/patterns/list?status=active&tag=趨勢
Response:
{
    "patterns": [
        {
            "pattern_id": "PAT_001",
            "name": "...",
            "status": "active",
            "tags": ["趨勢", "成交量"],
            "created_at": "2026-01-10T10:00:00Z"
        },
        // ... 其他模式
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
}

# PUT /api/v1/patterns/{pattern_id}
Request:
{
    "status": "archived",  # 或更新其他欄位
    "tags": ["趨勢", "成交量", "已驗證"]
}

Response:
{
    "pattern_id": "PAT_001",
    "status": "updated"
}

# DELETE /api/v1/patterns/{pattern_id}
Response:
{
    "pattern_id": "PAT_001",
    "status": "deleted"
}
```

#### Acceptance Criteria

**Auto-Tests** (pytest) - ⚠️ 必須使用真實數據:
- ✅ `test_pattern_creation()` - 模式建立測試（使用真實 XGBoost 結果）
- ✅ `test_pattern_validation()` - 模式驗證（語法、特徵名稱、閾值）
- ✅ `test_pattern_storage_json()` - JSON 儲存與載入
- ✅ `test_pattern_query()` - 模式查詢（by status, tags, case_id）
- ✅ `test_pattern_crud_operations()` - CRUD 操作測試
- ✅ `test_pattern_index_consistency()` - pattern_index.json 一致性

**Edge Case Tests** (pytest):
- ✅ `test_edge_case_empty_rules()` - 空規則處理
- ✅ `test_edge_case_duplicate_pattern_id()` - 重複 pattern_id 處理
- ✅ `test_edge_case_invalid_operator()` - 無效運算符處理（例如："~="）
- ✅ `test_edge_case_extreme_threshold()` - 極端閾值處理（例如：1e10）
- ✅ `test_edge_case_missing_metadata()` - 缺失 metadata 處理
- ✅ `test_edge_case_corrupted_json()` - 損壞的 JSON 檔案處理
- ✅ `test_edge_case_pattern_index_out_of_sync()` - pattern_index 不同步處理

**Human Validation** (需人工確認):
- 🔍 規則可解釋性（交易邏輯合理嗎？）
- 🔍 規則數量合理（建議 3-7 條，不要太多或太少）
- 🔍 閾值設定合理（例如：taker_buy_ratio > 0.6 太高或太低？）
- 🔍 模式名稱和描述清晰易懂

---

### Task 4.4: Pattern Evaluation UI (Week 21, ~3,000 lines)

**Objective**: 前端視覺化介面，展示模式發現結果並支持人工評估

#### Technical Specifications

**Frontend Components**:
```
frontend/src/app/patterns/
├── page.tsx                      # 模式列表頁面
├── [patternId]/
│   └── page.tsx                  # 模式詳情頁面
└── evaluate/
    └── page.tsx                  # 模式評估頁面

frontend/src/components/patterns/
├── PatternList.tsx               # 模式列表組件
├── PatternCard.tsx               # 模式卡片組件
├── PatternDetailView.tsx         # 模式詳情視圖
├── FeatureImportanceChart.tsx    # 特徵重要性圖表 (橫向條形圖)
├── DecisionRuleTable.tsx         # 決策規則表格
├── PatternPerformancePanel.tsx   # 模式表現指標面板
├── PatternFilterPanel.tsx        # 模式篩選面板
├── PatternComparisonView.tsx     # 模式比較視圖 (多個模式對比)
└── PatternEvaluationForm.tsx     # 模式評估表單 (人工評分)

frontend/src/store/
└── patternStore.ts               # Zustand 狀態管理
    ├── patterns: Pattern[]
    ├── selectedPattern: Pattern | null
    ├── filterOptions: {...}
    └── actions: {...}
```

**UI Components Design**:

**1. PatternList.tsx** (模式列表):
- 顯示所有模式的卡片列表
- 支持篩選 (by status, tags, confidence, created_at)
- 支持排序 (by confidence, support, created_at)
- 支持搜尋 (by name, description)
- 每張卡片顯示：模式名稱、描述、tags、performance_metrics、狀態

**2. FeatureImportanceChart.tsx** (特徵重要性圖表):
```typescript
// 使用 recharts 橫向條形圖
<ResponsiveContainer width="100%" height={400}>
  <BarChart data={featureImportanceData} layout="vertical">
    <XAxis type="number" domain={[0, 1]} />
    <YAxis type="category" dataKey="feature" width={150} />
    <Tooltip content={<CustomTooltip />} />
    <Bar dataKey="importance" fill="#3b82f6">
      {/* 根據重要性動態調整顏色 */}
      {data.map((entry, index) => (
        <Cell key={`cell-${index}`} fill={getImportanceColor(entry.importance)} />
      ))}
    </Bar>
  </BarChart>
</ResponsiveContainer>

// Color mapping:
// importance > 0.2: green-600
// importance 0.1-0.2: blue-500
// importance < 0.1: gray-400
```

**3. DecisionRuleTable.tsx** (決策規則表格):
```typescript
// 顯示所有決策規則
interface Rule {
  rule_id: number;
  condition: string;  // "ema_distance_5_20 > 0.02 AND taker_buy_ratio > 0.6"
  support: number;
  confidence: number;
  lift: number;
}

// Table columns:
// - Rule ID
// - Condition (可展開顯示詳細邏輯)
// - Support (樣本數 + 百分比)
// - Confidence (盈利概率 + 顏色標記)
// - Lift (相對提升 + 顏色標記)
// - Actions (編輯、刪除、加入模式庫)
```

**4. PatternPerformancePanel.tsx** (模式表現指標面板):
```typescript
// 顯示模式的關鍵表現指標
interface PerformanceMetrics {
  support: number;        // 符合樣本數
  confidence: number;     // 盈利概率
  lift: number;           // 相對提升
  cv_auc: number;         // 交叉驗證 AUC
  precision: number;      // 精確率
  recall: number;         // 召回率
  f1_score: number;       // F1 分數
}

// 4x2 網格顯示，每個指標卡片包含：
// - 指標名稱
// - 指標值 (大字體)
// - 顏色標記 (green/yellow/red)
// - 簡短說明
// - 趨勢圖 (如有歷史數據)
```

**5. PatternComparisonView.tsx** (模式比較視圖):
```typescript
// 支持選擇 2-4 個模式進行並排比較
// 比較維度：
// - Feature importance (重疊條形圖)
// - Performance metrics (雷達圖)
// - Decision rules (表格對比)
// - Support/Confidence (散點圖)

// 使用 recharts RadarChart
<RadarChart data={comparisonData}>
  <PolarGrid />
  <PolarAngleAxis dataKey="metric" />
  <PolarRadiusAxis domain={[0, 1]} />
  <Radar name="Pattern 1" dataKey="PAT_001" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
  <Radar name="Pattern 2" dataKey="PAT_002" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
  <Legend />
</RadarChart>
```

**6. PatternEvaluationForm.tsx** (模式評估表單):
```typescript
// 人工評估模式質量
interface EvaluationForm {
  pattern_id: string;
  evaluator: string;          // 評估者
  rating: number;             // 1-5 星評分
  interpretability: number;   // 可解釋性 (1-5)
  practicality: number;       // 實用性 (1-5)
  confidence_level: number;   // 信心水平 (1-5)
  comments: string;           // 評論
  decision: "approve" | "reject" | "revise";  // 決策
}

// Form fields:
// - Star rating (1-5 stars, interactive)
// - Interpretability slider (1-5)
// - Practicality slider (1-5)
// - Confidence level slider (1-5)
// - Comments textarea
// - Decision buttons (Approve/Reject/Request Revision)
```

**API Integration**:

```typescript
// frontend/src/lib/api/patternApi.ts

export const patternApi = {
  // List patterns
  listPatterns: async (filters?: PatternFilters) => {
    const params = new URLSearchParams(filters as any);
    const response = await fetch(`${API_BASE_URL}/api/v1/patterns/list?${params}`);
    return response.json();
  },

  // Get pattern detail
  getPattern: async (patternId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/patterns/${patternId}`);
    return response.json();
  },

  // Create pattern
  createPattern: async (patternData: CreatePatternRequest) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/patterns/define`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patternData),
    });
    return response.json();
  },

  // Update pattern
  updatePattern: async (patternId: string, updates: Partial<Pattern>) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/patterns/${patternId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    return response.json();
  },

  // Delete pattern
  deletePattern: async (patternId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/patterns/${patternId}`, {
      method: 'DELETE',
    });
    return response.json();
  },
};
```

**State Management** (Zustand):

```typescript
// frontend/src/store/patternStore.ts

interface PatternState {
  // State
  patterns: Pattern[];
  selectedPattern: Pattern | null;
  comparisonPatterns: Pattern[];
  filterOptions: PatternFilters;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchPatterns: () => Promise<void>;
  selectPattern: (patternId: string) => void;
  addToComparison: (patternId: string) => void;
  removeFromComparison: (patternId: string) => void;
  setFilters: (filters: PatternFilters) => void;
  updatePattern: (patternId: string, updates: Partial<Pattern>) => Promise<void>;
  deletePattern: (patternId: string) => Promise<void>;
}

export const usePatternStore = create<PatternState>((set, get) => ({
  patterns: [],
  selectedPattern: null,
  comparisonPatterns: [],
  filterOptions: { status: 'active', tags: [], minConfidence: 0.7 },
  isLoading: false,
  error: null,

  fetchPatterns: async () => {
    set({ isLoading: true, error: null });
    try {
      const filters = get().filterOptions;
      const data = await patternApi.listPatterns(filters);
      set({ patterns: data.patterns, isLoading: false });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  selectPattern: (patternId: string) => {
    const pattern = get().patterns.find(p => p.pattern_id === patternId);
    set({ selectedPattern: pattern || null });
  },

  addToComparison: (patternId: string) => {
    const pattern = get().patterns.find(p => p.pattern_id === patternId);
    if (pattern && get().comparisonPatterns.length < 4) {
      set({ comparisonPatterns: [...get().comparisonPatterns, pattern] });
    }
  },

  removeFromComparison: (patternId: string) => {
    set({
      comparisonPatterns: get().comparisonPatterns.filter(p => p.pattern_id !== patternId)
    });
  },

  setFilters: (filters: PatternFilters) => {
    set({ filterOptions: filters });
    get().fetchPatterns();  // Auto-refetch
  },

  updatePattern: async (patternId: string, updates: Partial<Pattern>) => {
    set({ isLoading: true, error: null });
    try {
      await patternApi.updatePattern(patternId, updates);
      await get().fetchPatterns();  // Refresh list
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  deletePattern: async (patternId: string) => {
    set({ isLoading: true, error: null });
    try {
      await patternApi.deletePattern(patternId);
      await get().fetchPatterns();  // Refresh list
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },
}));
```

#### Acceptance Criteria

**Auto-Tests** (Jest + React Testing Library) - ⚠️ 使用真實數據結構:
- ✅ `PatternList.test.tsx` - 模式列表渲染測試（使用真實 Pattern 結構）
- ✅ `FeatureImportanceChart.test.tsx` - 圖表渲染測試（使用真實特徵數據）
- ✅ `DecisionRuleTable.test.tsx` - 表格渲染測試（使用真實決策規則）
- ✅ `patternStore.test.ts` - Zustand store 測試（驗證狀態更新邏輯）
- ✅ `patternApi.test.ts` - API 呼叫測試（mock 但使用真實 API 結構）

**Edge Case Tests** (Jest + React Testing Library):
- ✅ `test_edge_case_empty_pattern_list()` - 空模式列表處理
- ✅ `test_edge_case_zero_importance()` - 特徵重要性為 0 處理
- ✅ `test_edge_case_api_timeout()` - API 超時處理
- ✅ `test_edge_case_malformed_pattern()` - 格式錯誤的模式處理
- ✅ `test_edge_case_large_feature_count()` - 大量特徵（>100）處理
- ✅ `test_edge_case_missing_chart_data()` - 缺失圖表數據處理
- ✅ `test_edge_case_concurrent_filter_updates()` - 並發篩選更新處理

**Human Validation** (需人工測試):
- 🔍 UI 響應式設計測試（桌面、平板、手機）
- 🔍 圖表互動性測試（hover, click, export PNG）
- 🔍 篩選和排序功能測試
- 🔍 模式比較視圖顯示正確性
- 🔍 評估表單提交流程測試
- 🔍 空狀態處理（無模式、無數據）
- 🔍 錯誤狀態處理（API 失敗、網路錯誤）

---

## 🔍 Risk Mitigation Strategies

**⚠️ 簡化策略**：Optuna score 和案例數據質量先不管，系統能運作就好

### Risk 1: XGBoost 過擬合

**Problem**: 訓練 AUC 很高但 CV AUC 很低

**Mitigation**:
1. **Early Stopping**:
   ```python
   xgb_model.fit(
       X_train, y_train,
       eval_set=[(X_val, y_val)],
       early_stopping_rounds=10,  # 10 輪無改善則停止
       verbose=False
   )
   ```

2. **增強正則化**:
   - 增加 `reg_alpha` (L1) 和 `reg_lambda` (L2)
   - 減少 `max_depth` (從 5 → 3)
   - 增加 `min_child_weight` (從 5 → 10)

3. **交叉驗證**:
   - 使用 5-fold CV 評估模型穩定性
   - 如 CV std > 0.05，表示模型不穩定

4. **人工介入點**:
   - 在 Task 4.2 完成後，人工檢查 overfitting_score
   - 如 overfitting_score > 0.15，需調整超參數

### Risk 4: 特徵重要性解釋性不足

**Problem**: XGBoost 找出的 top features 在交易上難以解釋

**Mitigation**:
1. **SHAP 值分析** (Phase 4 後續任務):
   ```python
   import shap
   explainer = shap.TreeExplainer(xgb_model)
   shap_values = explainer.shap_values(X_test)
   shap.summary_plot(shap_values, X_test)
   ```

2. **特徵工程審查**:
   - 每個特徵都有清晰的金融意義
   - 特徵計算邏輯經過人工審查

3. **決策規則簡化**:
   - 限制規則數量 (3-7 條)
   - 合併高度相關的特徵

4. **人工介入點**:
   - 在 Task 4.3 定義模式時，由交易專家審查規則合理性

### Risk 5: 前端渲染效能問題

**Problem**: 大量模式或複雜圖表導致前端卡頓

**Mitigation**:
1. **虛擬化列表**:
   ```typescript
   import { useVirtualizer } from '@tanstack/react-virtual';
   
   // 僅渲染可見的模式卡片
   const virtualizer = useVirtualizer({
     count: patterns.length,
     getScrollElement: () => parentRef.current,
     estimateSize: () => 200,  // 每張卡片高度
   });
   ```

2. **圖表數據限制**:
   - 特徵重要性圖表最多顯示前 20 個特徵
   - 決策規則表格最多顯示前 10 條規則
   - 使用分頁避免一次性載入所有數據

3. **React.memo 優化**:
   ```typescript
   export const PatternCard = React.memo(({ pattern }: Props) => {
     // ...
   }, (prevProps, nextProps) => {
     return prevProps.pattern.pattern_id === nextProps.pattern.pattern_id;
   });
   ```

4. **人工介入點**:
   - 在 Task 4.4 完成後，使用 Chrome DevTools 檢查渲染效能
   - 目標：首次渲染 < 1 秒，互動響應 < 100ms

---

## ✅ Development Workflow

### Step 1: 啟動開發任務

```bash
# 1. 建立 Git branch
git checkout -b feature/phase4-pattern-discovery

# 2. 設定 Python 環境
source venv/bin/activate
pip install -r requirements.txt

# 3. 設定前端環境
cd frontend
npm install

# 4. 確認 HDF5 數據可用（ETHUSDT 多時間週期）
python3 -c "import h5py; f = h5py.File('data_cache/kline_cache.h5', 'r'); print('Available data:'); print('  ETHUSDT/1h:', f['ETHUSDT/1h/data'].shape[0], 'rows'); print('  ETHUSDT/4h:', f['ETHUSDT/4h/data'].shape[0], 'rows'); print('  ETHUSDT/12h:', f['ETHUSDT/12h/data'].shape[0], 'rows'); print('  ETHUSDT/1d:', f['ETHUSDT/1d/data'].shape[0], 'rows')"

# 5. 確認案例數據（165 個案例：55 正例 + 110 反例）
python3 -c "import json; data = json.load(open('data_cache/cases.json')); pos = sum(1 for c in data['cases'] if c.get('positive_case')); neg = sum(1 for c in data['cases'] if not c.get('positive_case')); print(f'Total: {len(data[\"cases\"])} cases ({pos} positive + {neg} negative)')"
```

### Step 2: 開發流程 (Ultra Think 3-Step) - **連續開發模式**

**⚠️ 重要調整**: 因為使用者不會寫程式碼，無法在每個 TASK 完成後驗證，因此採用**連續開發模式**：
- Agent 連續完成 Task 4.1 → 4.2 → 4.3 → 4.4
- 每個 TASK 完成後執行**自動測試**（pytest）
- 全部完成後執行**整合測試**（end-to-end）
- 最後由使用者進行**驗收測試**（UAT）

**For each task (4.1, 4.2, 4.3, 4.4):**

**STEP 1 - THINK (Initial Generation)**:
- 閱讀 PHASE4_DEVELOPMENT_PLAN.md 的 Technical Specifications
- 生成初始程式碼框架 (包含基本功能、錯誤處理、logging)
- 確保程式碼可執行 (no syntax errors)

**STEP 2 - REVIEW (Self Review)**:
- 檢查清單：
  - ❌ 是否有 hardcoded data? (違反 Data Truth Principle)
  - ❌ 是否有缺失的錯誤處理?
  - ❌ 是否有缺失的 logging?
  - ❌ 是否有命名不清晰的變數? (no `df1`, `temp`, `x`)
  - ❌ 是否有重複程式碼?
  - ❌ 是否有效能問題? (使用 vectorized operations)
  - ❌ 是否有安全問題?
- 輸出 To-do List (不修改程式碼)

**STEP 3 - OPTIMIZE (Refactor)**:
- 根據 Step 2 的 To-do List 逐項修改
- 加入註解說明複雜邏輯
- 生成最終的 production-ready 程式碼

**STEP 4 - AUTO TEST (每個 TASK 完成後立即執行)**:
- 執行 pytest 自動測試（包含 edge case）
- 確認所有測試通過
- 如測試失敗，返回 STEP 1 修正
- **不等待人工驗證，直接進入下一個 TASK**

### Step 3: 自動測試（每個 TASK 完成後立即執行）

```bash
# Task 4.1 完成後
pytest tests/momentum/test_feature_extractor.py -v --tb=short
pytest tests/api/test_feature_api.py -v --tb=short

# Task 4.2 完成後
pytest tests/momentum/test_xgboost_analyzer.py -v --tb=short
pytest tests/momentum/test_pattern_extractor.py -v --tb=short

# Task 4.3 完成後
pytest tests/momentum/test_pattern_definition.py -v --tb=short
pytest tests/api/test_pattern_management_api.py -v --tb=short

# Task 4.4 完成後
cd frontend
npm test -- --coverage --watchAll=false

# 所有 TASK 完成後：整合測試
pytest tests/integration/test_phase4_end_to_end.py -v --tb=short
```

### Step 4: 整合測試（全部 TASK 完成後）

**Integration Test Scenarios**:
```bash
# Scenario 1: 完整流程測試（Feature → XGBoost → Pattern → UI）
pytest tests/integration/test_full_pattern_discovery_flow.py -v

# Scenario 2: 多時間週期測試（1h, 4h, 12h, 1d）
pytest tests/integration/test_multi_timeframe_support.py -v

# Scenario 3: ETHUSDT 真實案例測試（165 案例）
pytest tests/integration/test_ethusdt_real_cases.py -v
```

**Expected Results**:
- ✅ 所有自動測試通過（pytest + Jest）
- ✅ 特徵提取成功（ETHUSDT/1h, 20,401 rows）
- ✅ XGBoost 訓練完成（CV AUC > 0.7, overfitting < 0.15）
- ✅ 模式定義生成（3-10 條規則）
- ✅ 前端 UI 正常渲染（無 console errors）

### Step 5: 使用者驗收測試（UAT）- **最後統一驗收**

**⚠️ 這是唯一需要人工驗證的階段**

**驗收清單**:

**1. 功能驗收**:
- 🔍 啟動後端: `python run_api.py` → 確認無錯誤
- 🔍 啟動前端: `cd frontend && npm run dev` → 確認無錯誤
- 🔍 測試特徵提取 API: `POST /api/v1/features/extract` → 檢查 Response
- 🔍 測試 XGBoost 分析 API: `POST /api/v1/patterns/analyze` → 檢查 Response
- 🔍 測試模式管理 API: `GET /api/v1/patterns/list` → 檢查 Response
- 🔍 瀏覽前端 UI: `http://localhost:3000/patterns` → 確認顯示正常

**2. 數據驗收**:
- 🔍 檢查 3-5 個案例的特徵提取結果（使用真實 ETHUSDT Case）
- 🔍 確認特徵統計分佈合理（無 NaN/Inf，合理範圍）
- 🔍 檢查 XGBoost 模型效能（CV AUC, precision, recall）
- 🔍 檢查 top 10 features 是否合理（基於交易邏輯）
- 🔍 檢查模式規則可解釋性（3-7 條規則，閾值合理）

**3. UI/UX 驗收**:
- 🔍 圖表互動性測試（hover, click, export PNG）
- 🔍 篩選和排序功能測試
- 🔍 空狀態處理（無模式、無數據）
- 🔍 錯誤狀態處理（API 失敗、網路錯誤）

**4. 效能驗收**:
- 🔍 特徵提取時間 < 30 秒（1h timeframe, 20,401 rows）
- 🔍 XGBoost 訓練時間 < 60 秒
- 🔍 前端首次渲染 < 1 秒
- 🔍 互動響應 < 100ms

**驗收後行動**:
- ✅ 全部通過 → 進入除錯和優化階段
- ❌ 部分失敗 → Agent 回到對應 TASK 修正
- ❓ 不確定 → 參考 XGBoost 教學文檔（見 Step 6）

### Step 6: XGBoost 教學文檔（驗收階段參考）

**⚠️ Agent 需在所有 TASK 完成後生成此文檔**

**文檔位置**: `docs/XGBOOST_PATTERN_DISCOVERY_GUIDE.md`

**內容大綱**:

**1. XGBoost 基礎原理**:
- 什麼是 XGBoost？（決策樹集成學習）
- 為什麼用於模式發現？（特徵重要性排序）
- 與深度學習的差異（可解釋性 vs 預測準確度）

**2. 關鍵參數說明**:
```python
# 模型複雜度參數
max_depth: 決策樹最大深度（預設 5，範圍 3-10）
  - 太小: 模型過於簡單，無法捕捉複雜模式
  - 太大: 容易過擬合
  - 建議: 從 3 開始，逐步增加到 5-7

n_estimators: 樹的數量（預設 100，範圍 50-300）
  - 太小: 模型欠擬合
  - 太大: 訓練時間長，可能過擬合
  - 建議: 100-200，使用 early_stopping

learning_rate: 學習率（預設 0.05，範圍 0.01-0.3）
  - 太小: 訓練慢，需要更多樹
  - 太大: 容易過擬合或不收斂
  - 建議: 0.05-0.1

# 正則化參數
reg_alpha: L1 正則化（預設 0.1，範圍 0-1）
  - 控制特徵稀疏性（移除不重要特徵）
  
reg_lambda: L2 正則化（預設 1.0，範圍 0-10）
  - 控制權重大小（避免過擬合）

min_child_weight: 最小葉子節點樣本數（預設 5，範圍 1-10）
  - 太小: 容易過擬合
  - 太大: 模型過於保守
```

**3. 特徵重要性解讀**:
```python
# 三種重要性指標
Gain (default): 該特徵對模型的平均貢獻
  - 數值越高，特徵越重要
  - 適合理解「哪些特徵最有用」

Weight: 該特徵在所有樹中被使用的次數
  - 數值越高，特徵越常被用到
  - 適合理解「哪些特徵最穩定」

Cover: 該特徵影響的樣本數量
  - 數值越高，特徵影響範圍越廣
  - 適合理解「哪些特徵最普遍」

# 實際範例（基於 ETHUSDT 數據）
Top 5 Features:
1. ema_distance_5_20 (gain: 0.25)  → EMA 短期動量最重要
2. taker_buy_ratio (gain: 0.18)    → 主動買盤壓力關鍵
3. rsi_14 (gain: 0.12)              → 超買超賣信號有效
4. volume_ma_ratio_5 (gain: 0.10)  → 成交量激增重要
5. price_momentum_3 (gain: 0.08)   → 短期價格動量次要

# 解讀建議
- 前 3 名特徵貢獻 > 50%: 模式集中明確（好）
- 前 3 名特徵貢獻 > 70%: 可能過度依賴單一信號（需檢查）
- 前 10 名特徵貢獻 < 80%: 模式過於分散（需簡化）
```

**4. 過擬合檢測與緩解**:
```python
# 過擬合指標
Overfitting Score = train_auc - cv_auc_mean

# 評估標準
< 0.05: 無過擬合（理想）
0.05-0.10: 輕微過擬合（可接受）
0.10-0.15: 中度過擬合（需調整參數）
> 0.15: 嚴重過擬合（需大幅調整）

# 緩解策略（優先順序）
1. 增加 min_child_weight (5 → 10)
2. 減少 max_depth (5 → 3)
3. 增加 reg_alpha 和 reg_lambda
4. 使用 early_stopping_rounds=10
5. 減少 n_estimators
```

**5. 實際調整範例**:
```python
# Case 1: CV AUC 過低 (< 0.7)
問題: 模型效能不足
調整:
- 增加 max_depth (5 → 7)
- 增加 n_estimators (100 → 200)
- 減少 min_child_weight (5 → 3)

# Case 2: 過擬合嚴重 (overfitting > 0.15)
問題: 訓練效果好但驗證差
調整:
- 減少 max_depth (5 → 3)
- 增加 reg_alpha (0.1 → 0.5)
- 增加 min_child_weight (5 → 10)

# Case 3: 特徵重要性過於集中
問題: 前 3 名佔 80% 重要性
調整:
- 檢查是否有資料洩漏（future leak）
- 移除高相關性特徵（corr > 0.95）
- 增加 colsample_bytree (0.8 → 0.6)
```

**6. 常見問題與解決方法**:
| 問題 | 可能原因 | 解決方法 |
|------|---------|---------|
| AUC 一直是 0.5 | 標籤錯誤或特徵無效 | 檢查 labels (1=盈利, 0=虧損) |
| 訓練時間過長 | n_estimators 太大 | 減少到 100，使用 early_stopping |
| 所有特徵重要性都很低 | 特徵與標籤無關 | 檢查特徵工程邏輯 |
| CV AUC 波動很大 | 樣本數不足或不平衡 | 增加 cv_folds，檢查標籤分佈 |

### Step 7: 提交與文檔

```bash
# 1. Git commit (所有 TASK 完成後一次性提交)
git add .
git commit -m "feat: Implement Phase 4 Pattern Discovery System (Task 4.1-4.4)

- Task 4.1: Feature Engineering System (動態特徵生成)
- Task 4.2: XGBoost Analysis Engine (特徵重要性分析)
- Task 4.3: Pattern Definition & Storage (模式定義與儲存)
- Task 4.4: Pattern Evaluation UI (9+ 前端組件)
- Integration Tests: End-to-end pattern discovery flow
- Documentation: XGBoost 教學文檔"

# 2. 更新文檔（Agent 自動完成）
# - docs/ARCHITECTURE.md (新增 Phase 4 章節)
# - docs/API_SPECIFICATION.md (新增 Phase 4 API)
# - docs/XGBOOST_PATTERN_DISCOVERY_GUIDE.md (新增 XGBoost 教學)
# - .github/PATTERN_DISCOVERY_ROADMAP.md (更新 Phase 4 狀態 → 100%)

# 3. 建立 PR
git push origin feature/phase4-pattern-discovery
# 在 GitHub 建立 Pull Request

# 4. 通知使用者進行 UAT
# Agent 輸出驗收清單和 XGBoost 教學文檔位置
```

---

## 📊 Success Metrics

### Task 4.1 Success Metrics
- ✅ 成功提取動態特徵（數量基於策略參數，EMA 三線約 20-26 個）
- ✅ 無 NaN/Inf 值
- ✅ 無高相關性特徵對 (corr > 0.95)
- ✅ HDF5 儲存與載入成功
- ✅ API 端點正常運作
- ✅ 支援多時間週期（1h, 4h, 12h, 1d）
- ✅ 特徵提取時間 < 30 秒 (per case, 1h timeframe with 20,401 rows)
- ✅ 使用 ETHUSDT 真實數據測試（165 個案例：55 正例 + 110 反例）

### Task 4.2 Success Metrics
- ✅ CV AUC > 0.7
- ✅ Overfitting score < 0.15
- ✅ 成功提取 top 10 features
- ✅ 成功提取 5-10 條決策規則
- ✅ 模型儲存與載入成功
- ✅ XGBoost 訓練時間 < 60 秒

### Task 4.3 Success Metrics
- ✅ 模式定義結構完整
- ✅ 模式儲存為 JSON 格式
- ✅ 模式查詢功能正常
- ✅ CRUD 操作正常
- ✅ pattern_index.json 保持一致性

### Task 4.4 Success Metrics
- ✅ 所有 9 個組件正常渲染
- ✅ 圖表互動性正常 (hover, click, export)
- ✅ 篩選和排序功能正常
- ✅ 模式比較視圖正常
- ✅ 首次渲染時間 < 1 秒
- ✅ 互動響應時間 < 100ms
- ✅ 支持響應式設計 (桌面、平板、手機)

---

## 📚 Reference Documents

- [PATTERN_DISCOVERY_ROADMAP.md](.github/PATTERN_DISCOVERY_ROADMAP.md) - Phase 4 總覽
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - 系統架構
- [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) - Ultra Think 開發流程
- [copilot-instructions.md](.github/copilot-instructions.md) - AI Agent 指引
- [OPTIMIZATION_FORMULA_SPEC.md](docs/OPTIMIZATION_FORMULA_SPEC.md) - Optuna 公式說明
- [API_SPECIFICATION.md](docs/API_SPECIFICATION.md) - API 文檔

---

## 🚀 Next Steps

**Immediate Actions**:
1. ✅ 此 PLAN 已完成 → 進入新 Thread 開始開發
2. 📋 使用 Sonnet 4.5 模型執行 Phase 4 開發
3. 📋 從 Task 4.1 開始，遵循 Ultra Think 3-step 流程

**Development Order**:
```
Task 4.1 (Week 17-18) → Task 4.2 (Week 19) → Task 4.3 (Week 20) → Task 4.4 (Week 21)
```

**Agent Autonomy** (連續開發模式):
- 🤖 **Full Auto**: 
  - 程式碼生成（Task 4.1 → 4.2 → 4.3 → 4.4）
  - 單元測試（pytest + Jest，每個 TASK 完成後立即執行）
  - 整合測試（end-to-end，全部完成後執行）
  - 錯誤處理、logging、文檔生成
  - XGBoost 教學文檔生成
- 🔍 **Human Only** (最後 UAT 階段):
  - 功能驗收（啟動系統，測試 API）
  - 數據驗收（檢查特徵、模型效能、模式規則）
  - UI/UX 驗收（圖表互動、篩選排序）
  - 效能驗收（提取時間、訓練時間、渲染時間）

**Communication** (新模式):
- Agent **只在全部完成後**向使用者報告：
  - ✅ **完成內容**:
    - Task 4.1-4.4 實作完成
    - 所有自動測試通過（pytest + Jest）
    - 整合測試通過（end-to-end）
    - 文檔更新完成（ARCHITECTURE, API_SPEC, XGBoost 教學）
  - 📋 **驗收清單**:
    - 功能驗收步驟（啟動、API 測試）
    - 數據驗收標準（AUC > 0.7, overfitting < 0.15）
    - UI/UX 驗收項目（圖表、篩選）
  - 📚 **參考文檔**:
    - `docs/XGBOOST_PATTERN_DISCOVERY_GUIDE.md` - XGBoost 運作原理、參數說明、調整方法
    - `docs/ARCHITECTURE.md` - Phase 4 架構說明
    - `docs/API_SPECIFICATION.md` - Phase 4 API 文檔
  - ❓ **已知問題** (如有):
    - 需要調整的參數
    - 需要優化的效能瓶頸

---

**Ready to start Phase 4 development! 🚀**
