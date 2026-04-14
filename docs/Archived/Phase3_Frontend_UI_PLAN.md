# Phase 3 前端 UI 升級 PLAN — 雙引擎 ML 分析介面

> **版本**: V4 (Frozen)
> **建立日期**: 2026-02-13  
> **依據**: `Phase3_LightGBM_XGBoost_PLAN.md` V4 (Frozen) + 現有前端 codebase 盤點  
> **目標**: 讓使用者透過 UI 完整操作 Phase 3 雙引擎功能，包含引擎選擇、訓練、對比、深度分析  
> **設計原則**: 最小改動、分頁分類、避免頁面跳轉、重用現有元件  
> **Changelog**:  
> - V1→V2：修正 9 項自審問題（3 嚴重/4 中等/2 輕微）— 見「附錄 A」  
> - V2→V3：交叉驗證審查修正 8 項問題（1 嚴重/3 中等/4 輕微）— 見「附錄 B」  
> - V3→V4(Frozen)：最終審查修正 5 項問題（0 嚴重/2 中等/3 輕微）— 見「附錄 C」

---

## 一、現狀盤點摘要

### 已有 UI（可重用）

| 頁面/元件 | 路徑 | 能力 |
|-----------|------|------|
| XGBoost 批量分析主頁 | `/patterns/xgboost-analysis/page.tsx` | 多選交易對、K 線設定、指標配置、XGBoost 參數、啟動訓練、進度追蹤、結果展示 |
| 深度分析儀表板 | `/patterns/xgboost-analysis/[task_id]/details/page.tsx` | 4 分頁（驗證/特徵/監控/診斷）、12 個圖表元件 |
| 共用圖表元件 | `components/pattern/details/charts/` | 10 個圖表（SHAP、PR、Calibration、PSI、Rolling AUC 等） |
| 共用 UI 元件 | `components/pattern/details/shared/` | MetricCard、EmptyState、ErrorState、LoadingState、ChartExportButton |
| 特徵重要性圖 | `FeatureImportanceChart.tsx` | Recharts 長條圖（gain/weight/cover 切換） |
| 決策規則表 | `DecisionRuleTable.tsx` | 排序 + CSV 匯出 |
| 指標配置器 | `MultiIndicatorConfig.tsx` | 動態新增/刪除指標，已被 XGBoost 頁面使用 |

### 已有後端 API（Phase 3 新增，前端尚未接上）

| 端點 | 用途 |
|------|------|
| `POST /model/train` | 通用訓練（需預生成特徵 HDF5，精簡流程） |
| `GET /model/{task_id}/performance` | 通用效能查詢 |
| `GET /model/{task_id}/comparison` | 雙引擎 A/B 對比報告 |
| `POST /lightgbm/train` | LightGBM 專用訓練（需預生成特徵 HDF5） |
| `GET /lightgbm/{task_id}/results` | LightGBM 專用結果 |
| Optimization `task_type=model_hyperparam` | Optuna 模型超參數優化 |

### ⚠️ 關鍵架構事實（V2 新增 — V1 遺漏的核心問題）

**後端存在兩套完全不同的訓練管線**：

| 面向 | Batch 管線 (`/xgboost/batch/start`) | Model 管線 (`/model/train`) |
|------|--------------------------------------|---------------------------|
| **服務** | `XGBoostBatchService` (~750 行) | `ModelTaskService` (~100 行) |
| **輸入** | `symbols + timeframe + indicators`（原始配置） | `features_source`（預生成 HDF5 路徑） |
| **流程** | 端到端：案例載入→K 線讀取→特徵工程→訓練→20+ 項後處理 | 精簡：讀 HDF5→訓練→回傳 performance |
| **支援引擎** | 僅 XGBoost（硬編碼 `create_xgboost_analyzer()`） | LightGBM / XGBoost（`create_model_trainer(engine)`） |
| **深度分析** | ✅ 完整 12 個端點 | ❌ 無 |
| **雙引擎對比** | ❌ | ✅ `run_comparison=True` |

**結論**：要讓 LightGBM 擁有與 XGBoost 等價的完整批量分析體驗（含深度分析圖表），**必須擴展 Batch Service 支援多引擎**，而非僅對接 `/model/train`。

### 缺口總結（V2 修訂）

1. **引擎選擇 UI** — 無法選 LightGBM 或雙引擎模式
2. **LightGBM 專屬參數** — 無 num_leaves / boosting_type / categorical 配置
3. **雙引擎對比視覺化** — 無並排 metrics 對比
4. **API 接線** — patternApi.ts 只有 `/xgboost/*` 調用
5. **TypeScript 型別** — 缺少 engine_type、ComparisonReport 等型別
6. **深度分析通用化** — details 頁面硬綁 XGBoost
7. **🆕 後端 Batch Service 需擴展** — 支援 LightGBM 引擎（前置 Task）
8. **🆕 Optuna model_hyperparam 無 UI 入口** — Phase 3.9 功能無法從前端觸發
9. **🆕 兩套管線整合** — 前端需統一調度 Batch 管線 vs Model 管線

---

## 二、設計原則

### 2.1 最小改動、最大重用

- **不新增頁面路由**，在現有頁面內加分頁/切換
- **保留所有現有 XGBoost UI**，只擴展不替換
- **12 個深度分析圖表元件 100% 重用**（引擎無關，吃 y_true + y_pred_proba）

### 2.2 操作流程不跳頁

```
使用者完整操作路徑（單一頁面內完成）：

/patterns/xgboost-analysis
├── [左面板] 配置區（現有 + 新增引擎選擇）
│   ├── Step 1: 案例&數據配置（現有）
│   ├── Step 2: 指標配置（現有）
│   └── Step 3: 引擎&模型配置（新增 ← 唯一新增的配置區）
│
├── [右面板] 結果區（分頁制）
│   ├── Tab 1: 訓練結果（現有 XGBoost 結果面板，擴展顯示引擎標籤）
│   ├── Tab 2: 雙引擎對比（新增 ← 只在 run_comparison=true 時出現）
│   └── Tab 3: 深度分析（新增 ← 內嵌深度分析儀表板，不跳頁）
│
唯一需要跳頁的情況：「儲存為樣式」→ 跳到 /patterns 查看
```

### 2.3 訓練管線調度策略（V2 新增）

前端根據使用者選擇，自動路由到正確的後端管線：

| 使用者選擇 | 調用管線 | API 端點 | 說明 |
|-----------|---------|---------|------|
| **XGBoost（預設）** | Batch 管線 | `POST /xgboost/batch/start` | 現有流程不動，100% 相容 |
| **LightGBM** | Batch 管線（擴展後） | `POST /batch/start` + `engine=lightgbm` | 需後端 Task B.0 完成 |
| **雙引擎對比** | Batch 管線（擴展後） | `POST /batch/start` + `engine=both` | 後端同時訓練兩引擎 + 對比 |
| **Optuna 自動調參** | Optimization 管線 | `POST /optimization/start` + `task_type=model_hyperparam` | 新增 UI 入口 |

### 2.4 分類清晰

| 分類 | 放哪裡 | 備註 |
|------|--------|------|
| 數據選擇 | 左面板 Step 1 | 現有不動 |
| 指標配置 | 左面板 Step 2 | 現有不動 |
| 引擎選擇 & 模型參數 | 左面板 Step 3 | 新增區塊 |
| 訓練進度 & 結果 | 右面板 Tab 1 | 輕微擴展 |
| 雙引擎對比 | 右面板 Tab 2 | 全新 |
| 深度分析 | 右面板 Tab 3 | 內嵌現有 4 分頁 |

---

## 三、改動清單（按 Task 編號）

---

### 群組 0：後端前置任務

### Task B.0：XGBoostBatchService 擴展為多引擎 Batch Service

**優先級**: P0（前端所有功能的前置條件） | **依賴**: Phase 3 核心引擎已完成

> **為什麼需要這個 Task**：現有 `XGBoostBatchService` 硬編碼了 `create_xgboost_analyzer()`。
> 如果不擴展，LightGBM 選項只能走精簡的 `/model/train`（沒有特徵工程、沒有深度分析、沒有決策規則），
> 使用者體驗會嚴重不對等。85% 的 batch service 程式碼已經是引擎無關的，只需改動 15%。

**檔案**：
- `api/services/xgboost_batch_service.py` (🔄 修改)
- `api/routes/pattern_analysis.py` (🔄 修改 — 新增通用 batch 路由)
- `momentum/Analysis/lightgbm_analyzer.py` (🔄 微調 — 補 `last_calibration_curve` / `last_pr_curve` 屬性)

**改動要點**：

> **V3 關鍵修正：Singleton 架構保留**
> `get_xgboost_batch_service()` 是 **singleton**（全域唯一實例），`task_manager` 和 `task_cache` 都綁在該實例上。
> 若改為 `__init__(engine)` 每次建新實例，會導致任務查詢失敗（task_id 存在 A 實例但從 B 實例查）。
> 正確做法：**singleton 不動，engine 作為參數傳入 `start_batch_analysis()`，動態建立 analyzer**。

```python
# api/services/xgboost_batch_service.py — 核心改動（V3 修訂方案）

class XGBoostBatchService:  # 保留類別名 + singleton 模式不動
    def __init__(self):
        # __init__ 完全不動，保留向後相容
        ...
        self.xgboost_analyzer = create_xgboost_analyzer()  # 保留（XGBoost 預設用）
        ...

    async def start_batch_analysis(
        self,
        symbols, timeframe, indicators, ...,
        engine: str = "xgboost",       # V3 新增
        model_params: Optional[Dict] = None,  # V3 新增：取代 xgboost_params（通用命名）
        run_comparison: bool = False,   # V3 新增
        **kwargs
    ):
        # 保留原有參數簽名的所有欄位，新增 engine / model_params / run_comparison
        ...

    async def _run_batch_analysis(self, ..., engine: str = "xgboost", model_params=None, run_comparison=False):
        # V3 修正：動態建立 analyzer（不修改 self.xgboost_analyzer）
        from momentum.factories import create_model_trainer
        analyzer = create_model_trainer(engine=engine, config=model_params)
        # 後續所有 self.xgboost_analyzer.xxx → analyzer.xxx（使用局部變數，不修改 self）
        # task_cache.store_result() 仍用 self.task_cache（singleton 共享）
        ...
        # 讀取 calibration / pr_curve
        calibration_curve = analyzer.last_calibration_curve  # LightGBM 需先補齊此屬性
        pr_curve = analyzer.last_pr_curve
        ...
```

> **注意**：`_run_batch_analysis` 內有 **13 處** `self.xgboost_analyzer` 引用（排除 `__init__` 中的 1 處定義）+ `xgboost_params` 參數名。
> 改動量約 40-50 行（V2 低估為 20-30 行，V3 低估引用數為 ~6 處）。

```python
# api/routes/pattern_analysis.py — 新增通用 batch 路由（V3 修正）
@router.post("/batch/start")  # 通用 batch 入口
async def start_batch_analysis(request: BatchAnalysisRequest):
    engine = request.engine or "xgboost"
    batch_service = get_xgboost_batch_service()  # V3: 使用 singleton，不建新實例
    return await batch_service.start_batch_analysis(
        symbols=request.symbols,
        timeframe=request.timeframe,
        indicators=[ind.model_dump() for ind in request.indicators],
        lookback_bars=request.lookback_bars,
        engine=engine,                        # V3 新增
        model_params=request.model_params,    # V3 新增
        run_comparison=request.run_comparison, # V3 新增
        # ... 其他欄位同 XGBoostBatchAnalysisRequest
    )
```

```python
# api/models/pattern_analysis_models.py — V3 新增 BatchAnalysisRequest Pydantic 模型
class BatchAnalysisRequest(XGBoostBatchAnalysisRequest):
    """通用批量分析請求（繼承 XGBoost 版本，新增引擎選擇）"""
    engine: Optional[str] = Field(default="xgboost", description="引擎：xgboost / lightgbm")
    model_params: Optional[Dict[str, Any]] = Field(default=None, description="引擎模型參數（替代 xgboost_params）")
    run_comparison: bool = Field(default=False, description="是否同時訓練雙引擎並產生對比報告")
    # 注意：繼承的 xgboost_params 仍可用（向後相容），model_params 優先
```

```python
# momentum/Analysis/lightgbm_analyzer.py — 補齊屬性
# 在 train_model() 中增加：
self.last_calibration_curve = {...}  # 與 XGBoost 同格式（CalibrationCurveData）
self.last_pr_curve = {...}           # Dict: {precision, recall, thresholds}
```

> **V3 新增：`pattern_extractor` 決策規則適配**
> 現有 `self.pattern_extractor.extract_rules()` 依賴 XGBoost Booster 的樹結構（`get_dump()`）。
> LightGBM 的樹結構格式不同（`model.booster_.dump_model()`）。
> **方案**：在 `_run_batch_analysis` 中判斷 engine，LightGBM 暫時跳過 `extract_decision_rules()`，
> 改為返回空規則 `[]` + 在結果中標註 `"decision_rules_note": "LightGBM 暫不支援決策規則提取"`。
> 未來可另建 `LightGBMPatternExtractor` 適配 LightGBM 樹格式。

**深度分析端點通用化**（V3 補充說明）：
- 現有 12 個 `/xgboost/{task_id}/xxx` 端點透過 `_get_task_from_services()` 查詢任務
- `_get_task_from_services` 先查 `batch_service.get_task_status()`，再查 `xgboost_service.get_task_status()`
- 因為 singleton 方案下 LightGBM 任務也存入同一個 `task_manager`，所以 LightGBM task_id **可以**通過現有 `/xgboost/` 路徑查詢
- `_XGBoostTaskCache` 同理，singleton 共享 cache 不分引擎
- 結論：**深度分析端點不需任何修改**，LightGBM 任務自動可查

**驗收條件**（V3 修訂）：
- [x] `start_batch_analysis(..., engine="lightgbm")` 可以完成完整批量分析
- [x] `get_xgboost_batch_service()` singleton 行為完全不變
- [x] 現有 `/xgboost/batch/start` 端點行為完全不變（向後相容）
- [x] 新增 `/batch/start` 端點接受 `engine` 參數
- [x] 新增 `BatchAnalysisRequest` Pydantic 模型（繼承 `XGBoostBatchAnalysisRequest`）
- [x] LightGBM 任務的深度分析端點可通（12 個端點，走 singleton cache）
- [x] `LightGBMAnalyzer` 補齊 `last_calibration_curve` / `last_pr_curve`
- [x] LightGBM 跳過 `extract_decision_rules()`，返回空規則 + 備註

**Checklist**（V3 修訂）：
- [x] `start_batch_analysis()` 新增 `engine` / `model_params` / `run_comparison` 參數
- [x] `_run_batch_analysis()` 用局部 `analyzer` 變數（不修改 `self.xgboost_analyzer`）
- [x] `_run_batch_analysis()` 內 13 處 `self.xgboost_analyzer` → `analyzer`（含 train_model, calculate_feature_importance, get_all_importance_types, model, get_predictions, calculate_precision_at_k, recommend_k, calculate_permutation_importance, calculate_fold_importance_stability, model (regime), last_calibration_curve ×2, last_pr_curve）
- [x] `_run_batch_analysis()` 內 `xgboost_params` → 支援 `model_params` 傳入
- [x] `extract_decision_rules()` 加引擎判斷（LightGBM → 空規則 + 備註）
- [x] 新增 `/batch/start` 通用路由（使用 `get_xgboost_batch_service()` singleton）
- [x] 後端 `BatchAnalysisRequest` Pydantic 模型（繼承方式）
- [x] `LightGBMAnalyzer` 補齊 `last_calibration_curve` / `last_pr_curve`
- [x] 深度分析端點不需改動（singleton cache 自動包含 LightGBM 任務）
- [x] 所有現有測試通過（回歸驗證）

---

### 群組 A：TypeScript 型別與 API 接線

### Task F.1：TypeScript 型別擴展

**優先級**: P0 | **依賴**: 無

**檔案**: `frontend/src/lib/patternTypes.ts` (修改)

**新增型別**：

```typescript
// === Phase 3 雙引擎型別 ===

type EngineType = 'lightgbm' | 'xgboost';

// V2 修正：引擎選擇模式（含 'both'）獨立於 EngineType
type EngineMode = EngineType | 'both';

// V2 修正：精確匹配後端 ModelTrainingRequest（僅 features_source 模式）
interface ModelTrainingRequest {
  engine: EngineType;
  features_source: string;
  config?: Record<string, any>;
  validation?: ValidationConfig;
  run_comparison: boolean;
}

// V2 新增：批量分析請求的引擎擴展（匹配後端 BatchAnalysisRequest）
interface BatchAnalysisRequest {
  engine?: EngineType;          // V2 新增：引擎選擇
  symbols: string[];
  timeframe: string;
  indicators: IndicatorConfig[];
  lookback_bars: number;
  sequence_length?: number | null;
  sequence_feature_mode?: 'aggregate' | 'flatten';
  sequence_stride?: number;
  aggregation_methods?: string[] | null;
  multi_scale_windows?: number[] | null;
  time_series_split?: boolean;
  model_params?: Record<string, any>;  // V3 說明：對應後端 BatchAnalysisRequest.model_params；若為 XGBoost 引擎，後端同時接受 xgboost_params（向後相容）
  cv_folds: number;
  run_comparison?: boolean;     // V2 新增：雙引擎對比
}

interface ValidationConfig {
  cv_folds: number;
  purge_gap: number;
  oot_enabled: boolean;
  oot_ratio: number;
  early_stopping_rounds: number;
}

interface ModelPerformanceResponse {
  engine_type?: string;
  train_auc: number;
  cv_auc_mean: number;
  cv_auc_std: number;
  precision: number;
  recall: number;
  f1_score: number;
  overfitting_score: number;
  oot_auc?: number | null;
  brier_score?: number | null;
  ece?: number | null;
  calibration_quality?: string | null;
  pr_auc?: number | null;
  positive_rate?: number | null;
  training_time_seconds?: number | null;
}

interface ComparisonReportResponse {
  engine_performances: Record<string, ModelPerformanceResponse>;
  consensus_rate: number;
  feature_rank_correlation: number;
  recommended_engine: string;
  recommendation_reason: string;
}

interface TaskStartResponse {
  task_id: string;
  status: string;
  engine: string;
}

// V2 新增：補齊 LightGBM 專用型別
interface LightGBMTrainingRequest {
  features_source: string;
  config?: Record<string, any>;
  boosting_type: 'gbdt' | 'dart' | 'goss';
  categorical_features?: string[];
  validation?: ValidationConfig;
}

interface LightGBMResultsResponse {
  task_id: string;
  performance: ModelPerformanceResponse;
  feature_importance: Array<{ feature: string; importance: number; rank: number }>;
  predictions_summary?: Record<string, any>;
}

// LightGBM 專用配置（UI 表單用）
interface LightGBMConfig {
  boosting_type: 'gbdt' | 'dart' | 'goss';
  num_leaves: number;
  max_depth: number;
  learning_rate: number;
  n_estimators: number;
  subsample: number;
  colsample_bytree: number;
  min_child_samples: number;
  reg_alpha: number;
  reg_lambda: number;
  min_gain_to_split: number;
  categorical_features?: string[];
}

// XGBoost 配置（UI 表單用）
interface XGBoostConfig {
  max_depth: number;
  learning_rate: number;
  n_estimators: number;
  subsample: number;
  colsample_bytree: number;
  min_child_weight: number;
  gamma: number;
  reg_alpha: number;
  reg_lambda: number;
}

// V2 新增：Optuna model_hyperparam 請求型別
interface ModelHyperparamOptimizationRequest {
  task_type: 'model_hyperparam';
  engine: EngineType;
  n_trials: number;
  objective_config: {
    engine: EngineType;
    features_source?: string;
    cv_folds?: number;
    base_model_params?: Record<string, any>;
  };
}
```

**修改 `AnalysisResult`**：新增 `engine_type?: EngineType` 欄位

**Checklist**：
- [x] `EngineType` 型別
- [x] `EngineMode` 型別（含 `'both'`）— V2 新增
- [x] `BatchAnalysisRequest` 加 `engine` + `run_comparison` + `model_params` — V2 修正
- [x] `ModelTrainingRequest` 精確匹配後端（不含 symbols 等批量欄位）— V2 修正
- [x] `ValidationConfig`
- [x] `ModelPerformanceResponse` 與 `ComparisonReportResponse`
- [x] `TaskStartResponse`
- [x] `LightGBMTrainingRequest` 與 `LightGBMResultsResponse` — V2 新增
- [x] `LightGBMConfig` 與 `XGBoostConfig`
- [x] `ModelHyperparamOptimizationRequest` — V2 新增
- [x] `AnalysisResult` 加 `engine_type` 欄位
- [x] 📌 V3 新增：清除 `page.tsx` 內的 ~120 行重複 inline 型別定義（ModelPerformance, FeatureImportance, DecisionRule 等），改為從 `patternTypes.ts` import（與 Task F.6 配合）

---

### Task F.2：API 客戶端擴展

**優先級**: P0 | **依賴**: Task F.1

**檔案**: `frontend/src/lib/api/patternApi.ts` (修改)

**新增函式**：

```typescript
// === 批量分析擴展（V2 修正：走 Batch 管線而非 Model 管線）===

// V2 核心修正：LightGBM 批量分析走 /batch/start（而非 /model/train）
export async function startBatchAnalysis(config: BatchAnalysisRequest): Promise<{ task_id: string }> {
  // V2: engine 決定路由
  const endpoint = config.engine === 'lightgbm' || config.run_comparison
    ? '/pattern-analysis/batch/start'          // 新增通用 batch 端點
    : '/pattern-analysis/xgboost/batch/start'; // 現有端點（向後相容）

  return fetchAPI(endpoint, {
    method: 'POST',
    body: JSON.stringify(config)
  });
}

// === Phase 3 通用模型 API（精簡管線，用於 features_source 模式）===
export async function startModelTraining(request: ModelTrainingRequest): Promise<TaskStartResponse> { ... }
export async function getModelPerformance(taskId: string): Promise<ModelPerformanceResponse> { ... }
export async function getModelComparison(taskId: string): Promise<ComparisonReportResponse> { ... }

// === 深度分析 API（V2 修正：統一使用 /xgboost/ 路徑，因 task_id 是唯一的）===
// 保持現有 12 個函式不變，LightGBM 任務也用 /xgboost/{taskId}/xxx 路徑
// （後端 Task B.0 確保 LightGBM task_id 也能通過 /xgboost/ 路徑查詢）
// 如果後端改為 /analysis/{taskId}/xxx，此處同步更新

// V2 新增：Optuna 模型超參數優化
export async function startModelHyperparamOptimization(
  request: ModelHyperparamOptimizationRequest
): Promise<{ task_id: string }> {
  return fetchAPI('/optimization/start', {
    method: 'POST',
    body: JSON.stringify(request)
  });
}
```

**修改現有函式**：
- `startBatchAnalysis()` 加 `engine` 參數（預設不傳 = XGBoost，向後相容）

**Checklist**：
- [x] `startBatchAnalysis()` 加 engine 路由邏輯 — V2 修正
- [x] `startModelTraining()`（精簡管線，進階使用者）
- [x] `getModelPerformance()`
- [x] `getModelComparison()`
- [x] `startModelHyperparamOptimization()` — V2 新增
- [x] 深度分析 12 個函式保持不變（依賴 Task B.0 的後端通用化）— V2 修正
- [x] 📌 V3 新增：`page.tsx` 內的 inline `startBatchAnalysis()` / `getTaskStatus()` / `getCaseSummary()` 函式需搬移至此檔案，統一 API 出口（與 Task F.6 配合）

---

### Task F.3：Store 擴展

**優先級**: P0 | **依賴**: Task F.1

**檔案**: `frontend/src/store/patternStore.ts` (修改)

**新增 State**：

```typescript
// 新增到 PatternState

// V2 修正：使用 EngineMode 而非 EngineType（支援 'both'）
selectedEngine: EngineMode;            // 'xgboost' | 'lightgbm' | 'both'
comparisonReport: ComparisonReportResponse | null;
comparisonLoading: boolean;

// 新增 Actions
setSelectedEngine: (engine: EngineMode) => void;
setComparisonReport: (report: ComparisonReportResponse | null) => void;
loadComparisonReport: (taskId: string) => Promise<void>;
```

**`loadDeepAnalysis()`**：
- V2 修正：**不需要動態切換路徑**。後端 Task B.0 確保所有 task_id（無論引擎）都可通過相同深度分析端點查詢。保持現有 `/xgboost/{taskId}/xxx` 路徑不變。

**Checklist**：
- [x] `selectedEngine: EngineMode` state + setter — V2 修正型別
- [x] `comparisonReport` state + setter + loader
- [x] `loadDeepAnalysis` 保持不變 — V2 修正（不需動態路徑）

---

### 群組 B：新增元件

### Task F.4：引擎選擇 & 模型參數配置元件

**優先級**: P0 | **依賴**: Task F.1

**檔案**: `frontend/src/components/pattern/EngineConfigPanel.tsx` (🆕 新建)

**UI 設計**（放置於現有 XGBoost 分析頁面左側面板的 Step 3）：

```
┌─────────────────────────────────────────┐
│ 🔧 引擎 & 模型配置                       │
│                                         │
│ 引擎選擇:                                │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│ │ XGBoost  │ │ LightGBM │ │ 雙引擎對比 │  │
│ └──────────┘ └──────────┘ └──────────┘  │
│                                         │
│ ── XGBoost 參數（現有欄位搬移至此）──     │
│ max_depth: [6]    learning_rate: [0.05]  │
│ n_estimators: [100]  CV 折數: [5]        │
│                                         │
│ ── 或 LightGBM 參數 ──                  │
│ Boosting: [GBDT ▼]  (GBDT/DART/GOSS)    │
│ num_leaves: [31]     learning_rate: [0.05]│
│ n_estimators: [200]  min_child: [20]     │
│ reg_alpha: [0.1]     reg_lambda: [1.0]   │
│ □ 啟用類別特徵                            │
│                                         │
│ ── 或 雙引擎模式 ──                      │
│ ✅ 使用預設參數分別訓練 XGBoost + LightGBM │
│ ✅ 產生對比報告 + 引擎推薦                  │
│ (可展開自訂兩引擎各自參數)                  │
│                                         │
│ ── Optuna 自動調參（可選）──              │
│ □ 啟用 Optuna 自動調參                    │
│   Trial 數: [100]                        │
│   最佳化目標: CV AUC (最大化)              │
│                                         │
│ [驗證配置] (可展開)                        │
│ CV 折數: [5]  Purge Gap: [5]             │
│ □ OOT 驗證  比例: [0.2]                  │
│ Early Stopping: [50]                     │
└─────────────────────────────────────────┘
```

**功能說明**：
- **三個引擎選項**以 SegmentedControl（類似 Tab）展示，點選後顯示對應參數區
- **XGBoost 模式**：顯示現有的 XGBoost 參數欄位（從原位置搬移到此統一面板）
- **LightGBM 模式**：顯示 LightGBM 專屬參數（boosting_type 下拉、num_leaves 等）
- **雙引擎對比模式**：簡化介面，使用預設參數，重點是對比分析。可展開自訂各引擎參數
- **Optuna 自動調參**：V2 新增，勾選後顯示 trial 數設定（走 Optimization 管線）
  > ⚠️ V4 補充：後端 `model_hyperparam` objective 需要 `features`（numpy/DataFrame）和 `labels`（numpy）作為輸入，
  > 無法直接從前端傳送。**Optuna 調參的前置條件是已完成至少一次 Batch 分析**（用其產生的特徵矩陣），
  > 或另建一個後端端點自動從 HDF5 載入特徵。此版本 Optuna UI 入口先以「顯示提示 + 跳轉到優化頁」方式實作，
  > 完整整合留待後續 sprint。
- **驗證配置**：摺疊式面板，含 CV/OOT/Early Stopping（所有引擎共用）

**Props**：
```typescript
interface EngineConfigPanelProps {
  onEngineChange: (engine: EngineMode) => void;  // V2: EngineMode 包含 'both'
  onConfigChange: (config: Record<string, any>) => void;
  onValidationChange: (validation: ValidationConfig) => void;
  onOptunaToggle: (enabled: boolean, nTrials: number) => void;  // V2 新增
}
```

**Checklist**：
- [x] 三選一引擎切換（XGBoost / LightGBM / 雙引擎對比）
- [x] XGBoost 參數面板
- [x] LightGBM 參數面板（boosting_type 下拉 + num_leaves + min_child_samples 等）
- [x] 雙引擎模式說明 + 可展開自訂參數
- [x] Optuna 自動調參核取方塊 + trial 數設定 — V2 新增
- [x] 驗證配置摺疊面板（CV + OOT + Early Stopping）
- [x] 參數變更回呼

---

### Task F.5：雙引擎對比面板元件

**優先級**: P1 | **依賴**: Task F.1, F.2

**檔案**（V2 修正：子元件獨立檔案，遵循專案慣例 `details/charts/` 每圖一檔）：
- `frontend/src/components/pattern/ComparisonPanel.tsx` (🆕 主容器)
- `frontend/src/components/pattern/comparison/RecommendationBanner.tsx` (🆕)
- `frontend/src/components/pattern/comparison/ComparisonMetricsTable.tsx` (🆕)
- `frontend/src/components/pattern/comparison/ConsensusCard.tsx` (🆕)
- `frontend/src/components/pattern/comparison/ComparisonFeatureChart.tsx` (🆕)

**UI 設計**（放置於結果區 Tab 2）：

```
┌─────────────────────────────────────────────────────────────────┐
│ 🆚 雙引擎 A/B 對比報告                                          │
│                                                                 │
│ ┌─────────────────────────────────────────────────┐             │
│ │ 💡 推薦引擎: LightGBM                             │             │
│ │    原因: "LightGBM AUC 較高且過擬合分數較低"        │             │
│ └─────────────────────────────────────────────────┘             │
│                                                                 │
│ ┌───────────────────────────────────────────────────┐           │
│ │ 📊 指標並排對比                                     │           │
│ │                                                     │           │
│ │ 指標          XGBoost    LightGBM     差異    勝方   │           │
│ │ ────────────────────────────────────────────────── │           │
│ │ CV AUC        0.723      0.741     +0.018  ✅ LGB  │           │
│ │ Precision     0.680      0.695     +0.015  ✅ LGB  │           │
│ │ Recall        0.610      0.602     -0.008  ✅ XGB  │           │
│ │ F1 Score      0.643      0.645     +0.002  ≈ 相當  │           │
│ │ Overfitting   0.085      0.062     -0.023  ✅ LGB  │           │
│ │ Brier Score   0.190      0.185     -0.005  ✅ LGB  │           │
│ │ Train Time    3.2s       1.8s      -1.4s   ✅ LGB  │           │
│ └───────────────────────────────────────────────────┘           │
│                                                                 │
│ ┌──────────────────────┐ ┌──────────────────────┐               │
│ │ 🔄 預測共識率: 87.3%  │ │ 📈 Spearman: 0.82    │               │
│ └──────────────────────┘ └──────────────────────┘               │
│                                                                 │
│ ┌───────────────────────────────────────────────────┐           │
│ │ Top-10 特徵重要性對比（並排長條圖）                   │           │
│ │                                                     │           │
│ │ feature_A  ████████████ (LGB)                       │           │
│ │            ██████████   (XGB)                       │           │
│ │ feature_B  ██████████   (LGB)                       │           │
│ │            ████████████ (XGB)                       │           │
│ └───────────────────────────────────────────────────┘           │
│                                                                 │
│ [匯出 PNG]  [匯出 CSV]                                           │
└─────────────────────────────────────────────────────────────────┘
```

**Checklist**：
- [x] `ComparisonPanel.tsx` 主容器
- [x] `RecommendationBanner.tsx` — 推薦引擎 + 原因
- [x] `ComparisonMetricsTable.tsx` — 指標並排（色彩標記差異方向）
- [x] `ConsensusCard.tsx` — 共識率 + Spearman
- [x] `ComparisonFeatureChart.tsx` — 並排特徵重要性（Recharts `GroupedBarChart`）
- [x] PNG / CSV 匯出（重用 `ChartExportButton`）
- [x] 空狀態處理（未執行對比時）

---

### 群組 C：頁面整合

### Task F.6：批量分析主頁整合改造

**優先級**: P0 | **依賴**: Task F.2, F.3, F.4, F.5, **B.0**

**檔案**: `frontend/src/app/patterns/xgboost-analysis/page.tsx` (🔄 修改)

**改造重點**：

#### 6a. 左面板：加入「引擎配置」區塊

- 在現有 Step 2（指標配置）下方插入 Step 3：`<EngineConfigPanel />`
- 現有的 XGBoost 參數欄位（max_depth、learning_rate 等）**搬移**到 `EngineConfigPanel` 內
- 新增「雙引擎對比」開關

#### 6b. 右面板：改為 Tabs 分頁制

**現有右面板**是一個長滾動結果面板。改為 Tabs：

```
┌──────────────────────────────────────────────┐
│  📊 訓練結果  │  🆚 引擎對比  │  🔍 深度分析  │
├──────────────────────────────────────────────┤
│  （Tab 內容，不跳頁）                          │
└──────────────────────────────────────────────┘
```

| Tab | 內容 | 條件 |
|-----|------|------|
| **訓練結果** | 現有的進度卡 + 模型效能 + 特徵重要性 + 決策規則 + 進階指標 | 永遠顯示 |
| **引擎對比** | `<ComparisonPanel />` | 只在「雙引擎對比」模式時顯示 Tab |
| **深度分析** | 內嵌現有 4 分頁（驗證/特徵/監控/診斷） | 訓練完成後顯示 |

#### 6c. 訓練流程分支（V2 修正：統一走 Batch 管線）

```typescript
const handleStartAnalysis = async () => {
  // V2 修正：所有引擎都走 Batch 管線（而非 /model/train）
  // 確保完整的特徵工程 + 深度分析能力

  if (optunaEnabled) {
    // Optuna 自動調參模式（V2 新增）
    const response = await startModelHyperparamOptimization({
      task_type: 'model_hyperparam',
      engine: selectedEngine === 'both' ? 'lightgbm' : selectedEngine,
      n_trials: optunaTrials,
      objective_config: {
        engine: selectedEngine === 'both' ? 'lightgbm' : selectedEngine,
        cv_folds: validationConfig.cv_folds
      }
    });
    // 跳轉到優化結果頁 or 內嵌進度
    return;
  }

  // 標準訓練模式
  const response = await startBatchAnalysis({
    symbols,
    timeframe,
    indicators,
    lookback_bars,
    engine: selectedEngine === 'both' ? 'lightgbm' : selectedEngine,  // 主引擎
    model_params: engineConfig,
    cv_folds: validationConfig.cv_folds,
    run_comparison: selectedEngine === 'both',  // 雙引擎對比
    // ... 其他不變
  });
  setTaskId(response.task_id);
};
```

#### 6d. 結果面板引擎標籤

- 在結果標題旁顯示引擎 Badge（如 `🟢 LightGBM` 或 `🔵 XGBoost`）
- `ModelPerformance` 顯示時加 `engine_type` 標註

#### 6e. 深度分析內嵌（V2 修正：不需引擎路徑切換）

- **不跳頁到 `/patterns/xgboost-analysis/[task_id]/details`**
- 在 Tab 3「深度分析」內嵌 4 個子 Tab（驗證/特徵/監控/診斷）
- 重用現有 `ValidationTab`、`FeaturesTab`、`MonitoringTab`、`DiagnosisTab` 元件
  > V4 補充：`MonitoringTab` 和 `DiagnosisTab` 需要 `taskId` prop（見 details/page.tsx 原始碼），
  > 內嵌時需從 page state 傳入。`ValidationTab` 和 `FeaturesTab` 從 store 讀取，無需額外 props。
- V2 修正：深度分析 API 路徑不變（Task B.0 負責後端通用化，前端無需切換路徑）
- 保留舊的 details 路由作為獨立頁面（可由「在新頁面開啟」按鈕觸發）

#### 6f. 雙引擎深度分析切換（V2 新增）

在 Tab 3（深度分析）頂部加一個引擎子切換器，僅在雙引擎模式時顯示：

```
┌─────────────────────────────────────────────┐
│ 🔍 深度分析                                  │
│                                             │
│ 查看引擎: [XGBoost ▼] / [LightGBM ▼]         │  ← 僅雙引擎模式顯示
│                                             │
│  ┌─────┬─────┬─────┬─────┐                  │
│  │驗證  │特徵  │監控  │診斷  │                  │
│  ├─────┴─────┴─────┴─────┤                  │
│  │ (該引擎對應的分析)      │                  │
│  └────────────────────────┘                  │
└─────────────────────────────────────────────┘
```

**Checklist**：
- [x] 左面板加入 `<EngineConfigPanel />` 作為 Step 3
- [x] 現有 XGBoost 參數欄位搬移到 EngineConfigPanel
- [x] 右面板改為 Tabs（訓練結果 / 引擎對比 / 深度分析）
- [x] 訓練邏輯分支 — V2 修正：統一走 Batch 管線
- [x] Optuna 自動調參流程 — V2 新增
- [x] 結果面板加引擎 Badge
- [x] Tab 2 放 `<ComparisonPanel />`（雙引擎模式才顯示 Tab）
- [x] Tab 3 內嵌深度分析 4 子 Tab
- [x] Tab 3 雙引擎模式的引擎子切換器 — V2 新增
- [x] 保留「在新頁面開啟深度分析」按鈕
- [x] 進度追蹤邏輯更新（支援通用 batch 端點 polling）

---

### 群組 D：通用化 & 收尾

### Task F.7：深度分析通用化

**優先級**: P1 | **依賴**: Task B.0

**檔案**:
- `frontend/src/components/pattern/details/DetailsHeader.tsx` (修改)

**改造內容**（V2 簡化）：

1. ~~`loadDeepAnalysis(taskId, engine)`~~ → V2：**`loadDeepAnalysis` 不需修改**
   - Task B.0 確保所有 task_id 可通過相同 API 路徑查詢
   - 前端不需要動態切換路徑

2. **`DetailsHeader`** — 顯示引擎類型 Badge（從 task 結果中取 `engine_type`）

3. ~~各 Tab 元件~~ → V2：**不需修改**。Tab 元件消費 store 中的數據，不直接呼叫 API。

**Checklist**：
- [x] DetailsHeader 顯示引擎 Badge
- [x] 確認獨立 details 頁面在 LightGBM task 下可正常運作

---

### Task F.8：導覽列更新

**優先級**: P2 | **依賴**: 無

**檔案**: `frontend/src/components/layout/MainLayout.tsx` (修改)

**改動**：

```typescript
{
  name: '模式發現',
  href: '/patterns',
  icon: Target,
  description: 'LightGBM/XGBoost 雙引擎 ML 分析（Phase 3+4）'
}
```

**Checklist**：
- [x] 導覽描述更新

---

## 四、頁面結構最終狀態

### 改造後的 `/patterns/xgboost-analysis` 頁面結構

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🧠 ML 模型分析                                                          │
│ LightGBM / XGBoost 雙引擎訓練與分析                                       │
├─────────────────────────┬────────────────────────────────────────────────┤
│                         │                                                │
│ 📋 配置面板 (左側)       │  📊 結果面板 (右側，Tabs)                        │
│                         │                                                │
│ ▶ Step 1: 數據選擇      │  ┌──────────┬──────────┬──────────┐           │
│   • 交易對多選           │  │ 訓練結果  │ 引擎對比  │ 深度分析  │           │
│   • K 線週期             │  ├──────────┴──────────┴──────────┤           │
│   • 回看 K 線數          │  │                                │           │
│                         │  │ [Tab 1: 訓練結果]               │           │
│ ▶ Step 2: 指標配置      │  │  • 進度追蹤                     │           │
│   • MultiIndicatorConfig │  │  • 模型效能（含引擎 Badge）     │           │
│                         │  │  • 特徵重要性 Top15             │           │
│ ▶ Step 3: 引擎&模型     │  │  • 決策規則 Top10               │           │
│   • XGBoost / LightGBM  │  │  • 進階指標（Precision@K 等）   │           │
│     / 雙引擎對比 三選一   │  │                                │           │
│   • 引擎專屬參數          │  │ [Tab 2: 引擎對比] ※雙引擎模式   │           │
│   • □ Optuna 自動調參    │  │  • 推薦引擎 Banner             │           │
│   • 驗證配置（摺疊）      │  │  • 指標並排表格                  │           │
│                         │  │  • 共識率 + Spearman            │           │
│ [🚀 開始訓練]            │  │  • 特徵重要性對比圖              │           │
│                         │  │                                │           │
│                         │  │ [Tab 3: 深度分析]               │           │
│                         │  │  查看引擎: [XGB▼/LGB▼] ※雙引擎  │           │
│                         │  │  ┌─────┬─────┬─────┬─────┐    │           │
│                         │  │  │驗證  │特徵  │監控  │診斷  │    │           │
│                         │  │  ├─────┴─────┴─────┴─────┤    │           │
│                         │  │  │ (內嵌現有深度分析元件)   │    │           │
│                         │  │  │  OOT / SHAP / PR 等    │    │           │
│                         │  │  └────────────────────────┘    │           │
│                         │  │                                │           │
│                         │  │ [💾 儲存為樣式] [📤 匯出]       │           │
│                         │  └────────────────────────────────┘           │
├─────────────────────────┴────────────────────────────────────────────────┤
│                              ⓘ 系統狀態列                                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 五、新增/修改檔案清單

### 新增檔案（6 個）

| 檔案路徑 | 用途 | Task |
|---------|------|:----:|
| `frontend/src/components/pattern/EngineConfigPanel.tsx` | 引擎選擇 + 模型參數 + Optuna 開關 | F.4 |
| `frontend/src/components/pattern/ComparisonPanel.tsx` | 雙引擎對比主容器 | F.5 |
| `frontend/src/components/pattern/comparison/RecommendationBanner.tsx` | 推薦引擎 Banner | F.5 |
| `frontend/src/components/pattern/comparison/ComparisonMetricsTable.tsx` | 指標並排表格 | F.5 |
| `frontend/src/components/pattern/comparison/ConsensusCard.tsx` | 共識率卡片 | F.5 |
| `frontend/src/components/pattern/comparison/ComparisonFeatureChart.tsx` | 特徵對比長條圖 | F.5 |

### 修改檔案（6 + 後端 3 + 模型 1 個）

| 檔案路徑 | 修改內容 | Task |
|---------|---------|:----:|
| `frontend/src/lib/patternTypes.ts` | 新增 12+ 個 TypeScript 型別 | F.1 |
| `frontend/src/lib/api/patternApi.ts` | 新增 4 個 API 函式 + 修改 batch 路由 + 搬入 page.tsx inline API | F.2 |
| `frontend/src/store/patternStore.ts` | 新增 engine/comparison state | F.3 |
| `frontend/src/app/patterns/xgboost-analysis/page.tsx` | 引擎配置 + Tabs + 內嵌深度分析 + 清除 inline 型別與 API 重複 | F.6 |
| `frontend/src/components/pattern/details/DetailsHeader.tsx` | 引擎 Badge | F.7 |
| `frontend/src/components/layout/MainLayout.tsx` | 導覽描述 | F.8 |
| **`api/services/xgboost_batch_service.py`** | **多引擎支援（方法層級，singleton 不動）** | **B.0** |
| **`api/routes/pattern_analysis.py`** | **通用 batch 路由** | **B.0** |
| **`api/models/pattern_analysis_models.py`** | **新增 `BatchAnalysisRequest` Pydantic 模型** | **B.0** |
| **`momentum/Analysis/lightgbm_analyzer.py`** | **補 `last_calibration_curve` / `last_pr_curve` 屬性** | **B.0** |

---

## 六、執行順序

```
B.0 (後端擴展) ←── 前置條件，必須先完成
      │
      ↓
F.1 (型別)     ──→ F.2 (API 客戶端) ──→ F.3 (Store)
                         │                    │
                         └────────┬───────────┘
                                  ↓
F.4 (引擎配置元件) ──→ F.6 (主頁整合)
F.5 (對比面板元件) ──↗         │
                               ↓
                    F.7 (深度分析通用化)

F.8 (導覽更新)     ←── 無依賴，可隨時

推薦實作順序：
  Step 0: B.0               — 後端 Batch Service 多引擎擴展
  Step 1: F.1 + F.8         — 型別 + 導覽
  Step 2: F.2 + F.3         — API + Store
  Step 3: F.4 + F.5         — 兩個新元件
  Step 4: F.6               — 主頁整合
  Step 5: F.7               — 深度分析通用化
```

---

## 七、設計決策說明

### Q1: 為什麼不新增 `/patterns/lightgbm-analysis` 路由？

> XGBoost 和 LightGBM 的分析流程 90% 相同（選數據 → 配指標 → 訓練 → 看結果 → 深度分析），只差引擎參數。
> 在同一頁面內用引擎選擇器切換，比維護兩套幾乎相同的頁面更合理。

### Q2: 為什麼深度分析要內嵌而不是跳頁？

> 使用者需求是「盡量不跳頁」。內嵌深度分析到 Tab 3 後，使用者可以在同一頁面完成「配置 → 訓練 → 看結果 → 深度分析 → 對比」全流程。
> 同時保留舊的 details 獨立頁面（可從「在新頁面開啟」按鈕進入），適合需要全螢幕查看圖表的場景。

### Q3: 為什麼 ComparisonPanel 是獨立元件而非內嵌在結果面板？

> ComparisonPanel 的資料結構（`ComparisonReportResponse`）與訓練結果（`AnalysisResult`）不同，且只在雙引擎模式出現。獨立元件更好維護。

### Q4: 現有 12 個深度分析圖表元件需要改嗎？

> **不需要**。這些圖表都是引擎無關的（接收 y_true + y_pred_proba 或統計數據）。後端 Task B.0 確保 LightGBM task 也能通過相同 API 端點查詢。圖表元件本身零改動。

### Q5:（V2 新增）為什麼 LightGBM 要走 Batch 管線而非 `/model/train`？

> `/model/train` 是精簡管線（需預生成特徵 HDF5，無深度分析），而 `/xgboost/batch/start` 是完整管線（案例→特徵工程→訓練→20+ 項分析）。
> 使用者在 UI 配置的是「symbols + indicators」而非 HDF5 路徑，所以必須走完整管線。
> Batch Service 85% 的程式碼已是引擎無關的，改動量約 40-50 行（含 13 處 analyzer 引用替換）。

### Q6:（V2 新增）為什麼深度分析路徑用 `/xgboost/` 而不是 `/analysis/`？

> 深度分析 12 個端點以 `task_id` 為 key。Task B.0 確保 LightGBM 任務的結果也存入相同 cache，因此 LightGBM task_id 也能通過 `/xgboost/` 路徑查詢。
> 未來可重新命名為 `/analysis/`（後端加 alias），但此階段優先不動，避免破壞現有功能。

### Q7:（V2 新增）雙引擎模式下深度分析怎麼切換？

> Tab 3 頂部加一個引擎下拉切換器（僅在雙引擎模式顯示），切換時重新呼叫 `loadDeepAnalysis(otherTaskId)`。
> 雙引擎模式訓練會產生 2 個 task_id（或 1 個主 task_id + comparison 結構），切換器切的是 task_id 而非 API 路徑。

### Q8:（V3 新增）為什麼不改 `XGBoostBatchService.__init__()` 接受 engine？

> `get_xgboost_batch_service()` 是 singleton 模式，全域唯一實例。其 `task_manager` 和 `task_cache` 都綁在該實例上，
> 是所有任務查詢（`get_task_status`、深度分析端點的 `_get_task_from_services`）的唯一資料來源。
> 若改為 `__init__(engine)` 並在路由中建新實例，新實例的 task_manager 是空的，查不到任何先前任務。
> 正確做法：singleton 保留，`engine` 作為參數傳入 `start_batch_analysis()` 和 `_run_batch_analysis()`，
> 在方法內部用局部變數 `analyzer = create_model_trainer(engine)` 動態建立分析器。

---

## 八、後端配合事項（V3 修訂）

| 項目 | 狀態 | 說明 | 解決方案 |
|------|:----:|------|---------|
| Batch Service 多引擎支援 | ❌ 需新做 | `XGBoostBatchService` 硬編碼 XGBoost | **Task B.0**：方法層級傳入 `engine`，singleton 不動 |
| Singleton 架構保留 | ✅ V3 確認 | `get_xgboost_batch_service()` singleton 必須保留 | **Task B.0**：`_run_batch_analysis` 用局部 `analyzer` 變數 |
| `BatchAnalysisRequest` Pydantic 模型 | ❌ 需新增 | 前端需要含 `engine` 的請求模型 | **Task B.0**：繼承 `XGBoostBatchAnalysisRequest`，新增 `engine`/`model_params`/`run_comparison` |
| LightGBM 補齊 `last_calibration_curve` / `last_pr_curve` | ❌ 需補 | Batch Service 依賴這兩個屬性 | **Task B.0**：在 `LightGBMAnalyzer.train_model()` 內補齊 |
| `extract_decision_rules()` LightGBM 支援 | ⚠️ V3 明確方案 | `pattern_extractor` 依賴 XGBoost Booster 樹結構 | **Task B.0**：LightGBM 暫跳過，回傳空規則 + 備註欄位 |
| LightGBM 深度分析端點 | ✅ V3 確認可行 | singleton cache 自動包含 LightGBM 任務 | **不需改動**：`_get_task_from_services()` 自動查到 |
| 通用 `/batch/start` 路由 | ❌ 需新增 | 目前只有 `/xgboost/batch/start` | **Task B.0**：新增路由 |
| 雙引擎批量對比 | ❌ 需新增 | Batch Service 不支援 `run_comparison` | **Task B.0**：在 batch service 完成訓練後呼叫 `ModelComparison` |
| Optuna `model_hyperparam` UI 整合 | ✅ 後端已有 | 路由 + 服務均已實作 | 前端 Task F.4 加 UI 入口即可 |

---

## 九、驗收標準（V2 更新）

| # | 驗收項 | 標準 |
|---|--------|------|
| 1 | 引擎可選 | 使用者可在頁面上選 XGBoost / LightGBM / 雙引擎三種模式 |
| 2 | LightGBM 可訓練 | 選 LightGBM 後可配置參數、送出訓練、看到**完整結果**（含特徵重要性、進階指標；決策規則因 LightGBM 樹結構不同暫為空 + 備註） |
| 3 | 雙引擎可對比 | 選「雙引擎對比」後，Tab 2 顯示 ComparisonPanel（指標並排 + 推薦引擎） |
| 4 | 不跳頁 | 配置 → 訓練 → 結果 → 深度分析全在 `/patterns/xgboost-analysis` 完成 |
| 5 | 向後相容 | 現有純 XGBoost 流程操作完全不受影響 |
| 6 | 深度分析可用 | Tab 3 內嵌 4 子 Tab 的 12 個圖表均可正常載入（XGBoost + LightGBM） |
| 7 | 雙引擎深度分析切換 | 雙引擎模式下可在 Tab 3 切換顯示兩引擎各自的深度分析 — V2 新增 |
| 8 | Optuna 自動調參 | 可從 UI 啟動模型超參數優化任務 — V2 新增 |
| 9 | 響應式 | 左右面板在不同螢幕寬度正常顯示 |
| 10 | 匯出 | 對比報告支援 PNG + CSV 匯出 |
| 11 | 空/錯誤狀態 | 所有新增面板均有 EmptyState + ErrorState 處理 |

---

## 附錄 A：V1→V2 審查修正記錄

### Ultra Think 自審過程

#### Step 2：審查 To-Do（9 項問題）

| 嚴重度 | # | 問題 | V2 修正方式 |
|:------:|---|------|------------|
| 🔴 | S1 | 訓練流程不對齊：`/model/train` 是精簡管線，無法替代 Batch 管線的完整功能 | 新增 **Task B.0**（後端 Batch Service 擴展），前端統一走 Batch 管線 |
| 🔴 | S2 | 深度分析端點只有 `/xgboost/`，LightGBM 無對應端點 | Task B.0 解決：cache key 統一用 task_id，LightGBM 也可通過 `/xgboost/` 路徑查 |
| 🔴 | S3 | TypeScript `ModelTrainingRequest` 加了後端不存在的欄位 | 分離 `ModelTrainingRequest`（精簡管線）和 `BatchAnalysisRequest`（批量管線）兩個型別 |
| 🟡 | M1 | Optuna `model_hyperparam` 無 UI 入口 | Task F.4 新增 Optuna 核取方塊 + Trial 數設定 |
| 🟡 | M2 | 雙引擎模式需要 `features_source`（缺特徵生成步驟） | 改走 Batch 管線（自帶特徵工程），不走 `/model/train` |
| 🟡 | M3 | `LightGBMTrainingRequest` / `LightGBMResultsResponse` 未定義 | Task F.1 補齊型別定義 |
| 🟡 | M4 | 雙引擎深度分析切換邏輯缺失 | Task F.6-6f 新增引擎子切換器 |
| 🟢 | L1 | `EngineType` 不含 `'both'` | 新增 `EngineMode = EngineType \| 'both'` 型別 |
| 🟢 | L2 | ComparisonPanel 子元件位置不明確 | 獨立到 `comparison/` 子目錄 |

#### Step 3：最佳化執行

所有修正均已整合至 V2 各 Task 中。

---

**文件維護者**: Quantitative Trading System Team  
**建立日期**: 2026-02-13  
**版本歷程**:  
- V1 (2026-02-13): 初版 PLAN，基於前端 codebase 盤點產生
- V2 (2026-02-13): Ultra Think 審查修訂 — 修正 9 項問題（3 嚴重/4 中等/2 輕微），新增 Task B.0 後端前置任務、Optuna UI 入口、雙引擎深度分析切換、TypeScript 型別對齊後端
- V3 (2026-02-14): 交叉驗證審查修訂 — 修正 8 項問題（1 嚴重/3 中等/4 輕微），修正 singleton 架構衝突、補齊後端 Pydantic 模型、明確 pattern_extractor 方案、修正 API 改動量估算、page.tsx 去重提醒
- V4 Frozen (2026-02-14): 最終審查修訂 — 修正 5 項問題（0 嚴重/2 中等/3 輕微），修正 analyzer 引用數、Optuna 前置條件、改動量估算同步、LightGBM 決策規則備註、Tab props 文件

---

## 附錄 B：V2→V3 交叉驗證審查修正記錄

### 審查方法

以 V2 PLAN 為基準，對照實際 codebase 逐項驗證：
1. 後端檔案路徑、類別簽名、方法參數是否與 PLAN 描述一致
2. 前端檔案存在性、型別定義、inline 程式碼重複
3. Singleton 架構、資料流路徑、cache 共享機制

### Step 2：審查 To-Do（8 項問題）

| 嚴重度 | # | 問題 | V3 修正方式 |
|:------:|---|------|------------|
| 🔴 | S1 | `get_xgboost_batch_service()` 是 singleton，B.0 的 `__init__(engine)` 方案會導致 task_manager/task_cache 隔離，後續查不到任務 | 改為方法層級 `engine` 參數：`start_batch_analysis(..., engine="lightgbm")`，`_run_batch_analysis` 用局部 `analyzer` 變數 |
| 🟡 | M1 | 後端 `BatchAnalysisRequest` Pydantic 模型未定義，前端 TypeScript 有但後端沒寫 | Task B.0 新增 `BatchAnalysisRequest(XGBoostBatchAnalysisRequest)` 繼承方式，加 `engine`/`model_params`/`run_comparison` |
| 🟡 | M2 | `pattern_extractor` 依賴 XGBoost Booster 樹結構（`get_dump()`），LightGBM 格式不同，PLAN 只說「判斷引擎類型」無具體方案 | 明確方案：LightGBM 暫跳過 `extract_decision_rules()`，返回空規則 `[]` + `decision_rules_note` 欄位 |
| 🟡 | M3 | `start_batch_analysis()` 方法簽名是散開參數，PLAN 路由範例寫成傳 request 物件 | 修正路由程式碼範例：使用 `get_xgboost_batch_service()` + 展開請求欄位傳入 |
| 🟢 | L1 | TypeScript `model_params` 與後端 `xgboost_params` 欄位名不一致，缺明確映射 | model_params 型別定義加註：後端 `BatchAnalysisRequest.model_params` 優先；向後相容允許 `xgboost_params` |
| 🟢 | L2 | `page.tsx` 有 ~120 行 inline 重複型別（ModelPerformance, FeatureImportance 等），新增型別後未提及去重 | Task F.1 checklist 新增：清除 page.tsx inline 型別，改為 import |
| 🟢 | L3 | `page.tsx` 有 inline `startBatchAnalysis()` / `getTaskStatus()` / `getCaseSummary()`，Task F.6 未提及替換 | Task F.2 checklist 新增：搬移 page.tsx inline API 至 patternApi.ts |
| 🟢 | L4 | `_run_batch_analysis` 有 ~6 處 `self.xgboost_analyzer` + `xgboost_params` 參數，B.0 改動量 V2 低估為 20-30 行 | 修正為 40-50 行，checklist 逐項列出 |

### Step 3：最佳化執行

所有修正均已整合至 V3 各 Task 中。核心改動：
- Task B.0：完全重寫改動方案（singleton 保留 → 方法層級 engine）+ 補齊 Pydantic 模型 + 明確 pattern_extractor 方案
- Task F.1 checklist：新增 page.tsx inline 型別去重項
- Task F.2 checklist：新增 page.tsx inline API 搬移項
- 第七節：新增 Q8 設計決策說明
- 第八節：後端配合事項表格全面更新（9→9 項，多項狀態從 ⚠️ 改為 ✅ 已確認）

---

## 附錄 C：V3→V4(Frozen) 最終審查修正記錄

### 審查方法

以 V3 PLAN 為基準，針對先前審查發現的可疑項進行精確 codebase 驗證：
1. `grep self.xgboost_analyzer` 精確計數（`xgboost_batch_service.py`）
2. `read_file optimization_task_service.py` 驗證 `model_hyperparam` 介面
3. `read_file details/page.tsx` 確認 Tab 元件 props 簽名
4. 交叉比對 PLAN 內部數值一致性（Q5 vs B.0 改動量）

### Step 2：審查 To-Do（5 項問題）

| 嚴重度 | # | 問題 | V4 修正方式 |
|:------:|---|------|------------|
| 🟡 | M1 | `self.xgboost_analyzer` 引用數寫「~6 處」，`grep` 實測為 **13 處**（排除 `__init__`），嚴重低估會導致實作遺漏 | 修正為「**13 處**」並列出所有方法呼叫點，改動量維持 40-50 行 |
| 🟡 | M2 | Optuna `model_hyperparam` 後端需要 `features`（numpy/DataFrame）+ `labels`（numpy）實際數據，前端無法直接傳送特徵矩陣。PLAN 的 `features_source?: string` 不匹配 | 增加 ⚠️ 備註：Optuna 調參前置條件 = 已完成 Batch 分析。此版本 Optuna UI 入口先以「提示 + 跳轉」實作，完整整合留待後續 sprint |
| 🟢 | L1 | Q5 寫「~30 行」但 B.0 checklist 已修正為 40-50 行，數值不同步 | Q5 同步更新為「40-50 行（含 13 處 analyzer 引用替換）」 |
| 🟢 | L2 | 驗收標準 #2 寫「含特徵重要性、決策規則、進階指標」，但 LightGBM 決策規則 B.0 已明確返回空 | 加備註：「決策規則因 LightGBM 樹結構不同暫為空 + 備註」 |
| 🟢 | L3 | Task F.6 重用 Tab 元件未說明 props 差異：`MonitoringTab`/`DiagnosisTab` 需 `taskId` prop，`ValidationTab`/`FeaturesTab` 從 store 讀取 | 加 V4 補充說明 props 傳入方式 |

### Step 3：最佳化執行

所有修正均已整合至 V4 各 Task 中。核心改動：
- B.0 checklist：`self.xgboost_analyzer` 引用數從 ~6 修正為 13，列出所有方法呼叫點
- F.3 Optuna 區塊：增加前置條件警告與設計限制說明
- F.6 Tab 重用：補充 props 差異文件，明確哪些 Tab 需要 `taskId`
- Q5 改動量：同步為 40-50 行
- 驗收標準 #2：LightGBM 決策規則備註

### Frozen 判定

V4 經以下多輪驗證後無結構性問題，標記為 **Frozen**：
- ✅ Round 1 (V1→V2): Ultra Think 自審 — 9 項修正
- ✅ Round 2 (V2→V3): 後端交叉驗證 — 8 項修正（含 1 嚴重 singleton 衝突）
- ✅ Round 3 (V3→V4): 精確 codebase grep 驗證 — 5 項修正（0 嚴重）
- ✅ 所有後端介面（API 路徑、Pydantic 模型、方法簽名）已確認匹配
- ✅ 所有前端元件（Tab props、型別定義、store 結構）已確認匹配
- ✅ 已知限制已文件化（Optuna 前置條件、LightGBM 決策規則）
