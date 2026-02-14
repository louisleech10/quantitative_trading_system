# Phase 3 前端 UI 升級 PLAN — 雙引擎 ML 分析介面

> **版本**: V1  
> **建立日期**: 2026-02-13  
> **依據**: `Phase3_LightGBM_XGBoost_PLAN.md` V4 (Frozen) + 現有前端 codebase 盤點  
> **目標**: 讓使用者透過 UI 完整操作 Phase 3 雙引擎功能，包含引擎選擇、訓練、對比、深度分析  
> **設計原則**: 最小改動、分頁分類、避免頁面跳轉、重用現有元件

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
| `POST /model/train` | 通用模型訓練（engine=lightgbm/xgboost, run_comparison） |
| `GET /model/{task_id}/performance` | 通用效能查詢 |
| `GET /model/{task_id}/comparison` | 雙引擎 A/B 對比報告 |
| `POST /lightgbm/train` | LightGBM 專用訓練（boosting_type, categorical） |
| `GET /lightgbm/{task_id}/results` | LightGBM 專用結果 |
| Optimization `task_type=model_hyperparam` | Optuna 模型超參數優化 |

### 缺口總結

1. **引擎選擇 UI** — 無法選 LightGBM 或雙引擎模式
2. **LightGBM 專屬參數** — 無 num_leaves / boosting_type / categorical 配置
3. **雙引擎對比視覺化** — 無並排 metrics 對比
4. **API 接線** — patternApi.ts 只有 `/xgboost/*` 調用
5. **TypeScript 型別** — 缺少 engine_type、ComparisonReport 等型別
6. **深度分析通用化** — details 頁面硬綁 XGBoost

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

### 2.3 分類清晰

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

### Task F.1：TypeScript 型別擴展

**優先級**: P0 | **預估**: 0.5h | **依賴**: 無

**檔案**: `frontend/src/lib/patternTypes.ts` (修改)

**新增型別**：

```typescript
// === Phase 3 雙引擎型別 ===

type EngineType = 'lightgbm' | 'xgboost';

interface ModelTrainingRequest {
  engine: EngineType;
  features_source: string;
  config?: Record<string, any>;
  validation?: ValidationConfig;
  run_comparison: boolean;
  // 以下為批量分析整合欄位（與現有 batch start 合併）
  symbols?: string[];
  timeframe?: string;
  indicators?: IndicatorConfig[];
  lookback_bars?: number;
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

// LightGBM 專用參數
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

// XGBoost 參數（已部分存在，補齊）
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
```

**修改 `AnalysisResult`**：新增 `engine_type?: EngineType` 欄位

**Checklist**：
- [ ] `EngineType` 型別
- [ ] `ModelTrainingRequest` 與 `ValidationConfig`
- [ ] `ModelPerformanceResponse` 與 `ComparisonReportResponse`
- [ ] `TaskStartResponse`
- [ ] `LightGBMConfig` 與 `XGBoostConfig`
- [ ] `AnalysisResult` 加 `engine_type` 欄位

---

### Task F.2：API 客戶端擴展

**優先級**: P0 | **預估**: 0.5h | **依賴**: Task F.1

**檔案**: `frontend/src/lib/api/patternApi.ts` (修改)

**新增函式**：

```typescript
// === Phase 3 通用模型 API ===

// 通用模型訓練（支援引擎選擇 + 雙引擎對比）
export async function startModelTraining(request: ModelTrainingRequest): Promise<TaskStartResponse> { ... }

// 取得模型效能
export async function getModelPerformance(taskId: string): Promise<ModelPerformanceResponse> { ... }

// 取得雙引擎對比報告
export async function getModelComparison(taskId: string): Promise<ComparisonReportResponse> { ... }

// LightGBM 專用訓練
export async function startLightGBMTraining(request: LightGBMTrainingRequest): Promise<TaskStartResponse> { ... }

// LightGBM 專用結果
export async function getLightGBMResults(taskId: string): Promise<LightGBMResultsResponse> { ... }

// === 深度分析 API 通用化 ===
// 將現有 /xgboost/{taskId}/xxx 抽成參數化函式，支援 engine 路徑動態切換
export async function getDeepAnalysis(engine: EngineType, taskId: string, analysisType: string): Promise<any> {
  return fetchAPI(`/pattern-analysis/${engine}/${taskId}/${analysisType}`);
}
```

**修改現有函式**：
- `startBatchAnalysis()` 加 `engine?: EngineType` 參數（預設 `'xgboost'`，向後相容）
- 深度分析 12 個函式改為接受 `engine` 參數（預設 `'xgboost'`，向後相容）

**Checklist**：
- [ ] `startModelTraining()` 
- [ ] `getModelPerformance()`
- [ ] `getModelComparison()`
- [ ] `startLightGBMTraining()`
- [ ] `getLightGBMResults()`
- [ ] 現有 `startBatchAnalysis()` 加 engine 參數
- [ ] 深度分析函式通用化（engine 參數）

---

### Task F.3：Store 擴展

**優先級**: P0 | **預估**: 0.5h | **依賴**: Task F.1

**檔案**: `frontend/src/store/patternStore.ts` (修改)

**新增 State**：

```typescript
// 新增到 PatternState
selectedEngine: EngineType;           // 當前選擇的引擎
comparisonReport: ComparisonReportResponse | null;  // 雙引擎對比結果
comparisonLoading: boolean;
runComparison: boolean;               // 是否執行雙引擎對比

// 新增 Actions
setSelectedEngine: (engine: EngineType) => void;
setComparisonReport: (report: ComparisonReportResponse | null) => void;
setRunComparison: (run: boolean) => void;
loadComparisonReport: (taskId: string) => Promise<void>;
```

**修改 `loadDeepAnalysis()`**：
- 動態使用 `selectedEngine` 決定 API 路徑（`/xgboost/` 或 `/lightgbm/`）
- 若 LightGBM 深度分析 endpoint 尚未實作，fallback 到通用 `/model/` endpoint

**Checklist**：
- [ ] `selectedEngine` state + setter
- [ ] `comparisonReport` state + setter + loader
- [ ] `runComparison` state + setter
- [ ] `loadDeepAnalysis()` 支援動態引擎路徑

---

### Task F.4：引擎選擇 & 模型參數配置元件

**優先級**: P0 | **預估**: 1h | **依賴**: Task F.1

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
- **雙引擎對比模式**：簡化介面，使用預設參數，重點是對比分析
- **驗證配置**：摺疊式面板，含 CV/OOT/Early Stopping（所有引擎共用）

**Props**：
```typescript
interface EngineConfigPanelProps {
  onEngineChange: (engine: EngineType | 'both') => void;
  onConfigChange: (config: Record<string, any>) => void;
  onValidationChange: (validation: ValidationConfig) => void;
}
```

**Checklist**：
- [ ] 三選一引擎切換（XGBoost / LightGBM / 雙引擎對比）
- [ ] XGBoost 參數面板
- [ ] LightGBM 參數面板（boosting_type 下拉 + num_leaves + min_child_samples 等）
- [ ] 雙引擎模式說明
- [ ] 驗證配置摺疊面板（CV + OOT + Early Stopping）
- [ ] 參數變更回呼

---

### Task F.5：雙引擎對比面板元件

**優先級**: P1 | **預估**: 1.5h | **依賴**: Task F.1, F.2

**檔案**: `frontend/src/components/pattern/ComparisonPanel.tsx` (🆕 新建)

**UI 設計**（放置於結果區 Tab 2）：

```
┌─────────────────────────────────────────────────────────────────┐
│ 🆚 雙引擎 A/B 對比報告                                          │
│                                                                 │
│ 💡 推薦引擎: LightGBM                                           │
│    原因: "LightGBM AUC 較高且過擬合分數較低"                       │
│                                                                 │
│ ┌─────────────────────────┬─────────────────────────┐           │
│ │ 📊 指標並排對比                                                │
│ │                                                               │
│ │ 指標          XGBoost    LightGBM     差異        勝方         │
│ │ ─────────────────────────────────────────────────             │
│ │ CV AUC        0.723      0.741       +0.018    ✅ LightGBM    │
│ │ Precision     0.680      0.695       +0.015    ✅ LightGBM    │
│ │ Recall        0.610      0.602       -0.008    ✅ XGBoost     │
│ │ F1 Score      0.643      0.645       +0.002    ≈ 相當         │
│ │ Overfitting   0.085      0.062       -0.023    ✅ LightGBM    │
│ │ Brier Score   0.190      0.185       -0.005    ✅ LightGBM    │
│ │ Train Time    3.2s       1.8s        -1.4s     ✅ LightGBM    │
│ └─────────────────────────┴─────────────────────────┘           │
│                                                                 │
│ ┌────────────────────────────────────────┐                      │
│ │ 🔄 預測共識率: 87.3%                    │                      │
│ │ 📈 特徵排名相關性 (Spearman): 0.82      │                      │
│ └────────────────────────────────────────┘                      │
│                                                                 │
│ ┌────────────────────────────────────────────────────┐          │
│ │ Top-10 特徵重要性對比（並排長條圖）                              │
│ │                                                                │
│ │ feature_A  ████████████ (LGB)                                 │
│ │            ██████████   (XGB)                                 │
│ │ feature_B  ██████████   (LGB)                                 │
│ │            ████████████ (XGB)                                 │
│ │ ...                                                           │
│ └────────────────────────────────────────────────────┘          │
│                                                                 │
│ [匯出 PNG]  [匯出 CSV]                                           │
└─────────────────────────────────────────────────────────────────┘
```

**子元件拆分**：

| 子元件 | 用途 |
|--------|------|
| `ComparisonMetricsTable` | 指標並排表格（7 行 × 5 列，含色彩標記勝方） |
| `ComparisonFeatureChart` | Top-10 特徵重要性並排長條圖（Recharts GroupedBarChart） |
| `ConsensusCard` | 共識率 + Spearman 相關性指標卡片 |
| `RecommendationBanner` | 推薦引擎 Banner（含原因說明） |

**Checklist**：
- [ ] `ComparisonPanel` 主容器
- [ ] `RecommendationBanner` — 推薦引擎 + 原因
- [ ] `ComparisonMetricsTable` — 指標並排（色彩標記差異方向）
- [ ] `ConsensusCard` — 共識率 + Spearman
- [ ] `ComparisonFeatureChart` — 並排特徵重要性
- [ ] PNG / CSV 匯出
- [ ] 空狀態處理（未執行對比時）

---

### Task F.6：批量分析主頁整合改造

**優先級**: P0 | **預估**: 2h | **依賴**: Task F.2, F.3, F.4, F.5

**檔案**: `frontend/src/app/patterns/xgboost-analysis/page.tsx` (🔄 修改)

**改造重點**：

#### 6a. 左面板：加入「引擎配置」區塊

- 在現有 Step 2（指標配置）下方插入 Step 3：`<EngineConfigPanel />`
- 現有的 XGBoost 參數欄位（max_depth、learning_rate 等）搬移到 `EngineConfigPanel` 內
- 新增「雙引擎對比」開關

#### 6b. 右面板：改為 Tabs 分頁制

**現有右面板**是一個長滾動結果面板。改為 Tabs：

```
┌─────────────────────────────────────────┐
│  📊 訓練結果  │  🆚 引擎對比  │  🔍 深度分析  │
├─────────────────────────────────────────┤
│                                         │
│  （Tab 內容，不跳頁）                     │
│                                         │
└─────────────────────────────────────────┘
```

| Tab | 內容 | 條件 |
|-----|------|------|
| **訓練結果** | 現有的進度卡 + 模型效能 + 特徵重要性 + 決策規則 + 進階指標 | 永遠顯示 |
| **引擎對比** | `<ComparisonPanel />` | 只在「雙引擎對比」模式時顯示 |
| **深度分析** | 內嵌現有 4 分頁（驗證/特徵/監控/診斷） | 訓練完成後顯示 |

#### 6c. 訓練流程分支

```typescript
const handleStartAnalysis = async () => {
  if (selectedEngine === 'both') {
    // 使用 /model/train with run_comparison=true
    const response = await startModelTraining({
      engine: 'lightgbm', // 主引擎
      features_source: buildFeaturesSource(),
      config: lightgbmConfig,
      validation: validationConfig,
      run_comparison: true,
      symbols, timeframe, indicators, lookback_bars
    });
    setTaskId(response.task_id);
  } else {
    // 使用現有 batch/start（XGBoost）或新增（LightGBM）
    const response = await startBatchAnalysis({
      ...currentConfig,
      engine: selectedEngine, // 新增參數
    });
    setTaskId(response.task_id);
  }
};
```

#### 6d. 結果面板引擎標籤

- 在結果標題旁顯示引擎 Badge（如 `🟢 LightGBM` 或 `🔵 XGBoost`）
- `ModelPerformance` 顯示時加 `engine_type` 標註

#### 6e. 深度分析內嵌

- **不跳頁到 `/patterns/xgboost-analysis/[task_id]/details`**
- 在 Tab 3「深度分析」內嵌 4 個子 Tab（驗證/特徵/監控/診斷）
- 重用現有 `ValidationTab`、`FeaturesTab`、`MonitoringTab`、`DiagnosisTab` 元件
- 保留舊的 details 路由作為獨立頁面（可由「在新頁面開啟」按鈕觸發）

**Checklist**：
- [ ] 左面板加入 `<EngineConfigPanel />` 作為 Step 3
- [ ] 現有 XGBoost 參數欄位搬移到 EngineConfigPanel
- [ ] 右面板改為 Tabs（訓練結果 / 引擎對比 / 深度分析）
- [ ] 訓練邏輯分支（單引擎 vs 雙引擎）
- [ ] 結果面板加引擎 Badge
- [ ] Tab 2 放 `<ComparisonPanel />`（雙引擎模式才顯示）
- [ ] Tab 3 內嵌深度分析 4 子 Tab
- [ ] 保留「在新頁面開啟深度分析」按鈕
- [ ] 進度追蹤邏輯更新（支援 /model/ 端點 polling）

---

### Task F.7：深度分析通用化

**優先級**: P1 | **預估**: 1h | **依賴**: Task F.2, F.3

**檔案**:
- `frontend/src/store/patternStore.ts` (修改 `loadDeepAnalysis`)
- `frontend/src/components/pattern/details/DetailsHeader.tsx` (修改)
- `frontend/src/components/pattern/details/tabs/*.tsx` (微調)

**改造內容**：

1. **`loadDeepAnalysis(taskId, engine)`** — 新增 `engine` 參數
   - 根據 `engine` 決定 API 路徑前綴（`/xgboost/` 或 `/lightgbm/`）
   - LightGBM 的深度分析 endpoint 如果尚未後端實作，先 fallback 到 `/model/{taskId}/performance`

2. **`DetailsHeader`** — 顯示引擎類型 Badge

3. **各 Tab 元件** — 確認 props 不硬編碼 `/xgboost/` 路徑（以 store 中的 engine 為準）

**Checklist**：
- [ ] `loadDeepAnalysis` 支援 engine 參數
- [ ] DetailsHeader 顯示引擎 Badge
- [ ] 各 Tab 確認不硬編碼引擎路徑

---

### Task F.8：導覽列更新

**優先級**: P2 | **預估**: 0.25h | **依賴**: 無

**檔案**: `frontend/src/components/layout/MainLayout.tsx` (修改)

**改動**：

```typescript
// 將「模式發現」的描述更新
{
  name: '模式發現',
  href: '/patterns',
  icon: Target,
  description: 'LightGBM/XGBoost 雙引擎 ML 分析（Phase 3+4）'  // ← 更新描述
}
```

- 不新增導覽項目（所有功能在現有路由下操作）

**Checklist**：
- [ ] 導覽描述更新

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
│   • 驗證配置（摺疊）      │  │  • 推薦引擎 Banner             │           │
│                         │  │  • 指標並排表格                  │           │
│ [🚀 開始訓練]            │  │  • 共識率 + Spearman            │           │
│                         │  │  • 特徵重要性對比圖              │           │
│                         │  │                                │           │
│                         │  │ [Tab 3: 深度分析]               │           │
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

### 新增檔案（2 個）

| 檔案路徑 | 用途 | Task |
|---------|------|:----:|
| `frontend/src/components/pattern/EngineConfigPanel.tsx` | 引擎選擇 + 模型參數配置 | F.4 |
| `frontend/src/components/pattern/ComparisonPanel.tsx` | 雙引擎 A/B 對比面板 | F.5 |

### 修改檔案（6 個）

| 檔案路徑 | 修改內容 | Task |
|---------|---------|:----:|
| `frontend/src/lib/patternTypes.ts` | 新增 8 個 TypeScript 型別 | F.1 |
| `frontend/src/lib/api/patternApi.ts` | 新增 5 個 API 函式 + 通用化深度分析 | F.2 |
| `frontend/src/store/patternStore.ts` | 新增 engine/comparison state + actions | F.3 |
| `frontend/src/app/patterns/xgboost-analysis/page.tsx` | 加入引擎配置 + 改右面板為 Tabs + 內嵌深度分析 | F.6 |
| `frontend/src/components/pattern/details/DetailsHeader.tsx` | 顯示引擎 Badge | F.7 |
| `frontend/src/components/layout/MainLayout.tsx` | 導覽描述更新 | F.8 |

---

## 六、執行順序

```
F.1 (型別)     ──→ F.2 (API 客戶端) ──→ F.3 (Store)
                         │                    │
                         └────────┬───────────┘
                                  ↓
F.4 (引擎配置元件) ──→ F.6 (主頁整合)
F.5 (對比面板元件) ──↗         │
                               ↓
                    F.7 (深度分析通用化)
                               │
F.8 (導覽更新)     ←── 無依賴，可隨時

推薦實作順序：
  Step 1: F.1 + F.8         (0.75h)    — 型別 + 導覽
  Step 2: F.2 + F.3         (1h)       — API + Store
  Step 3: F.4 + F.5         (2.5h)     — 兩個新元件
  Step 4: F.6               (2h)       — 主頁整合
  Step 5: F.7               (1h)       — 深度分析通用化
```

---

## 七、設計決策說明

### Q1: 為什麼不新增 `/patterns/lightgbm-analysis` 路由？

> **答案**：避免程式碼重複。XGBoost 和 LightGBM 的分析流程 90% 相同（選數據 → 配指標 → 訓練 → 看結果 → 深度分析），只差引擎參數。  
> 在同一頁面內用引擎選擇器切換，比維護兩套幾乎相同的頁面更合理。

### Q2: 為什麼深度分析要內嵌而不是跳頁？

> **答案**：使用者需求是「盡量不跳頁」。內嵌深度分析到 Tab 3 後，使用者可以在同一頁面完成「配置 → 訓練 → 看結果 → 深度分析 → 對比」全流程。  
> 同時保留舊的 details 獨立頁面（可從「在新頁面開啟」按鈕進入），適合需要全螢幕查看圖表的場景。

### Q3: 為什麼 ComparisonPanel 是獨立元件而非內嵌在結果面板？

> **答案**：ComparisonPanel 的資料結構（`ComparisonReportResponse`）與訓練結果（`AnalysisResult`）不同，且只在雙引擎模式出現。獨立元件更好維護。

### Q4: 現有 12 個深度分析圖表元件需要改嗎？

> **答案**：**不需要**。這些圖表都是引擎無關的（接收 y_true + y_pred_proba 或統計數據），只需要確保 API 呼叫路徑通用化（Task F.7），圖表元件本身零改動。

---

## 八、後端配合事項

Phase 3 後端已實作完成的能力基本足夠，但以下項目需確認/補充：

| 項目 | 狀態 | 說明 |
|------|------|------|
| `/model/train` 整合批量分析 | ⚠️ 需確認 | 目前 `/model/train` 的 `features_source` 是 HDF5 key，需確認能否與批量分析（多 symbols）整合 |
| LightGBM 深度分析 endpoints | ⚠️ 需確認 | 現有深度分析 12 個 endpoint 只在 `/xgboost/` 路徑下，LightGBM 任務是否能共用？ |
| 雙引擎批量分析 | ⚠️ 需確認 | `ModelTaskService._run_task()` 是否支援多 symbols 批量+ 雙引擎？或需要包一層？ |
| `/model/train` 進度輪詢 | ✅ 已有 | `ModelTaskService.get_task_status()` 回傳 running/completed/failed |

> **建議**：前端先實作 UI，對接現有 API；後端如有缺口再逐步補齊（前端用 fallback + 空狀態處理）。

---

## 九、驗收標準

| # | 驗收項 | 標準 |
|---|--------|------|
| 1 | 引擎可選 | 使用者可在頁面上選 XGBoost / LightGBM / 雙引擎三種模式 |
| 2 | LightGBM 可訓練 | 選 LightGBM 後可配置參數、送出訓練、看到結果 |
| 3 | 雙引擎可對比 | 選「雙引擎對比」後，Tab 2 顯示 ComparisonPanel |
| 4 | 不跳頁 | 配置 → 訓練 → 結果 → 深度分析全在 `/patterns/xgboost-analysis` 完成 |
| 5 | 向後相容 | 現有純 XGBoost 流程操作完全不受影響 |
| 6 | 深度分析可用 | Tab 3 內嵌 4 子 Tab 的 12 個圖表均可正常載入 |
| 7 | 響應式 | 左右面板在不同螢幕寬度正常顯示 |
| 8 | 匯出 | 對比報告支援 PNG + CSV 匯出 |
| 9 | 空/錯誤狀態 | 所有新增面板均有 EmptyState + ErrorState 處理 |

---

**文件維護者**: Quantitative Trading System Team  
**建立日期**: 2026-02-13
