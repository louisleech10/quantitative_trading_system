# Phase 3: LightGBM/XGBoost 雙引擎模型訓練系統 — 規格計畫書 V2(Frozen)

> **版本**: V2(Frozen)  
> **建立日期**: 2026-02-09  
> **最後更新**: 2026-02-09 — V2(Frozen) 三輪審查通過，凍結  
> **定位**: Phase 3 — 雙引擎 ML 模型訓練系統之詳細設計規格  
> **前置文件**: `docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` (Phase 0-2 已完成)  
> **前置交付物**: Phase 1 Feature Factory (✅), Phase 2 IC Gatekeeper (✅)  
> **對應 Phase**: Phase 3 — Model Training Engine (預估 7-9 天)

---

## 📋 目錄

- [🗺️ SPEC→PLAN 轉換指南](#️-specplan-轉換指南)
- [1. 專案願景與目標](#1-專案願景與目標)
- [2. 現有 Codebase 盤點與保留策略](#2-現有-codebase-盤點與保留策略)
- [3. 系統架構設計](#3-系統架構設計)
- [4. IModelTrainer Protocol 擴展設計](#4-imodeltrainer-protocol-擴展設計)
- [5. LightGBM 引擎實作規格](#5-lightgbm-引擎實作規格)
- [6. XGBoost 引擎重構規格](#6-xgboost-引擎重構規格)
- [7. 共享分析與視覺化架構](#7-共享分析與視覺化架構)
- [8. 四維參數調整系統](#8-四維參數調整系統)
- [9. 量化金融業界實務研究](#9-量化金融業界實務研究)
- [10. ML 演算法擴展性設計](#10-ml-演算法擴展性設計)
- [11. Factory 與 Service 整合](#11-factory-與-service-整合)
- [12. 邊界條件與驗證覆蓋](#12-邊界條件與驗證覆蓋)
- [13. 資料契約定義](#13-資料契約定義)
- [14. 實作計畫與依賴關係](#14-實作計畫與依賴關係)
- [15. 驗收標準](#15-驗收標準)

---

## 🗺️ SPEC→PLAN 轉換指南

> **本節說明如何將此規格書自動轉換為可執行的 PLAN/TODO 文件。**
> AI Agent 在閱讀本規格書後，應能根據以下規則產生結構化 PLAN。

### 轉換流程

```
1. 閱讀本指南 → 理解標注格式與章節類型
2. 遍歷所有「📋 PLAN 轉換標注」區塊 → 提取 Task 資訊
3. 參照 §14 Task 分解表 → 確認依賴關係與優先級
4. 對每個 IMPLEMENTATION Task 產生：
   a. Task 標題 + 描述（從章節標題與內容提取）
   b. 具體子步驟（從章節內程式碼規格提取，每 Task ≤ 10 步）
   c. 交付物清單（具體檔案路徑，見附錄 A）
   d. 驗收條件（從 §15 + 標注中提取）
5. 每個子步驟遵守 Ultra Think 三步驟：Generate → Review → Optimize
6. 輸出格式為 Markdown TODO 清單，含 checkbox
```

### 標注格式說明

本文件在關鍵章節末尾設有 `📋 PLAN 轉換標注` 區塊，格式如下：

```markdown
> 📋 **PLAN 轉換標注**
> - **章節類型**: CONTEXT | IMPLEMENTATION | TESTING | META
> - **對應 Task**: 3.X [任務名稱]
> - **交付物**: 具體檔案路徑
> - **前置條件**: 需先完成的其他 Task
> - **驗收條件**: 可測試的量化驗收條件
> - **實作要點**: AI Agent 實作時的關鍵提示
> - **預估工作量**: X 天
```

### 章節類型定義

| 類型 | 說明 | PLAN 轉換方式 |
|------|------|-------------|
| **CONTEXT** | 背景、研究、願景 | 不直接產生 Task，作為所有 Task 的參考資訊與設計依據 |
| **IMPLEMENTATION** | 具體程式碼實作規格 | 直接轉為 1+ 個 Task，每個 Task 有明確交付物與程式碼規格 |
| **TESTING** | 測試規格與邊界條件 | 轉為測試 Task，以對應 IMPLEMENTATION Task 為前置依賴 |
| **META** | 計畫排程、驗收標準 | 作為 PLAN 的骨架、排程約束和最終驗收清單 |

### 章節 → Task 對照總表

| 章節 | 類型 | 對應 Task ID | 說明 |
|------|:----:|:------------:|------|
| §1 專案願景 | CONTEXT | — | 提供設計決策背景，所有 Task 參考 |
| §2 Codebase 盤點 | CONTEXT | — | 列出保留/修改/新增清單，指導實作範圍 |
| §3 系統架構 | CONTEXT | — | 架構圖、解耦規則、Protocol 位置，指導 3.1 |
| §4 IModelTrainer Protocol | IMPLEMENTATION | **3.1** | Protocol 介面定義，Phase 3 第一步 |
| §5 LightGBM 規格 | IMPLEMENTATION | **3.2** | 最大工作量，核心引擎完整實作 |
| §6 XGBoost 重構 | IMPLEMENTATION | **3.3** | 新增 Protocol 方法（不改現有邏輯） |
| §7 共享分析架構 | IMPLEMENTATION | **3.2**, **3.5** | SHAPAnalyzer/CalibrationAnalyzer 等共享組件 |
| §8 四維參數系統 | IMPLEMENTATION | **3.4**, **3.9**, **3.10** | Config Manager + Optuna 重構 |
| §9 業界研究 | CONTEXT | — | 業界最佳實踐，指導設計決策 |
| §10 擴展性設計 | CONTEXT | — | 未來引擎擴展考量，指導 Protocol 設計 |
| §11 Factory/Service | IMPLEMENTATION | **3.6**, **3.7** | 工廠函式 + API 端點 |
| §12 邊界條件 | TESTING | **3.8** | 測試矩陣與邊界場景 |
| §13 資料契約 | IMPLEMENTATION | **3.1**, **3.2**, **3.3** | 共用 dataclass 定義 |
| §14 實作計畫 | META | — | Task 排程、依賴圖、推薦順序 |
| §15 驗收標準 | META | — | 最終驗收清單（功能/品質/效能） |
| 附錄 A | META | — | 新增/修改檔案完整清單 |
| 附錄 B | META | — | requirements.txt 更新 + M1 安裝指南 |

### Task ID 規則

- **3.X**: Phase 3 主任務（定義於 §14，共 10 個：3.1 ~ 3.10）
- **3.X.Y**: 子任務（AI Agent 可自行細分，例如 3.2.1 = train_model 方法實作）
- 子任務數量 ≤ 10 個/主任務

### 特殊標記說明

| 標記 | 含義 | PLAN 轉換影響 |
|------|------|-------------|
| `⚠️ 不改現有程式碼` | 只新增，不修改現有邏輯 | 子步驟中不含修改既有函式的動作 |
| `🔄 重構` | 需修改現有程式碼 | 子步驟須含向後相容驗證 |
| `🆕 全新` | 從零建立的模組 | 子步驟含建檔 + 實作 + 測試 |
| `📐 Protocol` | 定義介面契約 | 必須排在所有 IMPLEMENTATION Task 之前 |

---

## 1. 專案願景與目標

### 1.1 核心目標

建立一個**雙引擎 ML 模型訓練系統**，以 **LightGBM 為主引擎**、**XGBoost 為輔引擎**，兩者**完全獨立可調用**，但**最大化共享**分析管線（Analysis Pipeline）與視覺化組件。參數系統需支援四種調整介面：手動 UI、LLM 自然語言、AI Agent 自動研究、Optuna 最佳化。

### 1.2 為什麼 LightGBM 為主引擎？

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 量化交易特徵矩陣通常數千列特徵、數萬行樣本，LightGBM 的 Histogram-based 分割在速度與記憶體上具備決定性優勢 |
| **What** | LightGBM 使用 GOSS (Gradient-based One-Side Sampling) + EFB (Exclusive Feature Bundling)，可在保持精度的同時大幅降低計算量 |
| **Challenge** | XGBoost 不行嗎？→ XGBoost 精度不遜色，但量化研究需頻繁實驗調參，LightGBM 的訓練速度是 XGBoost 的 3-10 倍 |
| **Root Cause** | 研究平台的核心瓶頸是「實驗迭代速度」，而非「單次最高精度」 |

#### LightGBM vs XGBoost 業界對比

| 維度 | LightGBM | XGBoost | 對研究平台的影響 |
|------|----------|---------|-----------------|
| **訓練速度** | 快 3-10x（Histogram-based） | 較慢（Exact/Approx Greedy） | 🟢 更快的實驗迭代 |
| **記憶體** | 低（Histogram 壓縮） | 高（儲存每個分割候選） | 🟢 M1 Mac 16GB 更友善 |
| **類別特徵** | **原生支援**（最大優勢） | 需手動 One-Hot/Label Encoding | 🟢 市場體制指標可直接使用 |
| **過擬合防護** | 內建 DART、Min-Data-in-Leaf | 正則化 + Max Depth | 🟡 兩者接近 |
| **SHAP 支援** | ✅ TreeExplainer 完整支援 | ✅ TreeExplainer 完整支援 | 🟡 兩者相同 |
| **Optuna 整合** | ✅ 內建 Pruner callback | ✅ 內建 Pruner callback | 🟡 兩者相同 |
| **M1 Mac 加速** | ✅ OpenMP 原生支援 | ✅ OpenMP 原生支援 | 🟡 兩者相同 |
| **業界使用率** | Kaggle 金融賽事 60%+ 為主力 | 傳統穩定，新趨勢往 LightGBM 移動 | 🟢 與業界對齊 |

**結論**：LightGBM 作為主引擎，XGBoost 作為驗證引擎（Model Consensus），兩者結果一致時信心更高。

### 1.3 關鍵需求 (Key Requirements)

| # | 需求 | 優先級 | 說明 |
|---|------|:------:|------|
| R1 | **保留現有 XGBoost 全部功能** | P0 | xgboost_analyzer.py 所有方法、輸出格式、API 端點必須保留，可優化/增強但不可移除 |
| R2 | **LightGBM 全新主引擎** | P0 | 具備與 XGBoost 等價的所有分析能力（OOT、SHAP、PSI、Calibration、PR、Precision@K 等） |
| R3 | **雙引擎獨立呼叫** | P0 | `create_model_trainer('lightgbm')` 或 `create_model_trainer('xgboost')` 各自獨立運作 |
| R4 | **共享分析管線** | P0 | CalibrationAnalyzer、SHAPAnalyzer、DriftAnalyzer 等不依賴引擎類型 |
| R5 | **四維參數介面** | P1 | 手動 UI / LLM 自然語言 / AI Agent / Optuna 四種參數調整方式 |
| R6 | **IModelTrainer Protocol 擴展** | P0 | 新增 `predict_proba`, `get_feature_importance`, `save_model`, `load_model`, `get_model_type`, `get_model_params`, `get_native_model`（共 7 個方法） |
| R7 | **雙引擎結果對比** | P1 | ModelComparison 機制，自動化 A/B 比較產出報告 |
| R8 | **ML 演算法可擴展** | P1 | 架構預留 CatBoost、TabNet、線性模型等未來接入 |
| R9 | **100% 邊界條件覆蓋** | P0 | 所有函式的邊界狀態（空輸入、單類別、極端值等）必須有對應驗證規格 |
| R10 | **REFACTOR_ARCHITECTURE_V4 合規** | P0 | 嚴格遵守 7 條解耦規則，momentum/ 不依賴 api/ |

### 1.4 與 V1→V2→V3 產品演進的關係

| 版本 | 調用路徑 | Phase 3 貢獻 |
|------|---------|-------------|
| **V1.0** (UI) | `api/routes/` → `api/services/` → `momentum/Analysis/` | 手動選擇 LightGBM/XGBoost，UI 調參 |
| **V2.0** (Chat) | `api/chat/` → `api/services/` → `momentum/Analysis/` | LLM 自然語言選引擎、設參數 |
| **V3.0** (Agent) | `api/agent/` → `momentum/Agent/` → `momentum/Analysis/` | AI Agent 自動選引擎、研究最佳參數組合 |

**向後相容承諾**：
- V1.0 所有 REST API 端點在 V2.0/V3.0 不變
- `XGBoostAnalyzer` 公開方法簽名不變（可新增但不可刪改）
- 新功能通過 `IModelTrainer` Protocol 抽象，舊程式碼無需修改

---

## 2. 現有 Codebase 盤點與保留策略

### 2.1 現有 XGBoost 模組完整清單

#### momentum/Analysis/ 核心模組

| 檔案 | 類別 | 行數 | 方法數 | 保留策略 |
|------|------|:----:|:------:|---------|
| `xgboost_analyzer.py` | XGBoostAnalyzer | ~1387 | 20+ | ✅ **保留**：所有 public 方法原樣保留；重構使其符合 IModelTrainer；新增 LightGBM 等價方法 |
| `shap_analyzer.py` | SHAPAnalyzer | ~300 | 3 | ✅ **共享**：已使用 TreeExplainer，可直接用於 LightGBM |
| `calibration_analyzer.py` | CalibrationAnalyzer | ~200 | 4 | ✅ **共享**：純 sklearn 計算，不依賴引擎類型 |
| `time_splitter.py` | PurgedTimeSeriesSplit | ~150 | 3 | ✅ **共享**：純時間切分邏輯，與引擎無關 |
| `drift_analyzer.py` | DriftAnalyzer | ~200 | 4 | ✅ **共享**：PSI 計算不依賴引擎 |
| `regime_analyzer.py` | RegimeAnalyzer | ~250 | 3 | ✅ **共享**：Market Phase 分析不依賴引擎 |
| `prediction_analyzer.py` | PredictionAnalyzer | ~300 | 5 | ✅ **共享**：Rolling AUC、Equity Curve 等不依賴引擎 |
| `expectancy_calculator.py` | ExpectancyCalculator | ~100 | 2 | ✅ **共享**：期望值計算不依賴引擎 |
| `bootstrap_estimator.py` | BootstrapEstimator | ~150 | 2 | ✅ **共享**：Bootstrap CI 不依賴引擎 |
| `cross_symbol_validator.py` | CrossSymbolValidator | ~200 | 2 | ✅ **共享**：跨幣種驗證邏輯，接收 IModelTrainer |
| `model_storage.py` | ModelStorage | ~100 | 3 | 🔄 **擴展**：新增 LightGBM 模型序列化支援 |

#### api/services/ 服務層

| 檔案 | 類別 | 保留策略 |
|------|------|---------|
| `xgboost_task_service.py` | XGBoostTaskService | ✅ **保留**：現有 API 不變；新增 ModelTaskService 通用抽象 |
| `xgboost_batch_service.py` | XGBoostBatchService | ✅ **保留**：現有 batch 流程不變 |
| `xgboost_task_cache.py` | XGBoostTaskCache | 🔄 **擴展**：重命名為 ModelTaskCache，支援多引擎快取 |
| `shap_analysis_service.py` | SHAPAnalysisService | ✅ **共享**：已引擎無關 |

#### api/routes/ API 端點

| 檔案 | 端點數量 | 保留策略 |
|------|:--------:|---------|
| `pattern_analysis.py` | 21 | ✅ **保留所有端點**；新增 `/lightgbm/` 對等端點 + `/model/` 通用端點 |

### 2.2 保留策略原則

```
1. 【不刪除】任何 XGBoostAnalyzer 的 public 方法
2. 【不修改】任何已有端點的 URL 或回應格式
3. 【可新增】新的方法、參數、回應欄位（向後相容新增）
4. 【可重構】內部實作，但 public 介面不變
5. 【可抽取】共用邏輯到共享 Analyzer，但 XGBoost 仍可獨立使用
```

### 2.3 XGBoostAnalyzer 已有方法清單（必須保留）

```python
class XGBoostAnalyzer:
    # 核心訓練
    train_model(X, y, feature_names, ...) -> ModelPerformance      # ✅ 保留
    train_with_purged_cv(X, y, ...) -> ModelPerformance             # ✅ 保留
    validate_model(X, y, cv_folds, ...) -> ModelPerformance         # ✅ 保留
    validate_oot(X_oot, y_oot, ...) -> OOTValidationResult          # ✅ 保留
    
    # 預測與機率
    get_predictions(X, y_true, case_ids) -> PredictionOutput        # ✅ 保留
    
    # 特徵重要性
    calculate_feature_importance(feature_names, method) -> List[FI]  # ✅ 保留
    get_all_importance_types(feature_names) -> Dict[str, List[FI]]   # ✅ 保留
    calculate_permutation_importance(X, y) -> PermutationResult      # ✅ 保留
    calculate_fold_importance_stability(X, y) -> StabilityResult     # ✅ 保留
    
    # 進階分析
    calculate_precision_at_k(X, y, k_values) -> PrecisionAtKResult  # ✅ 保留
    recommend_k(y_true, y_pred_proba) -> Dict                       # ✅ 保留
    calculate_pr_metrics(X, y) -> PRMetrics                         # ✅ 保留
    
    # SHAP（委託 SHAPAnalyzer）
    analyze_shap_global(X, sample_size) -> GlobalSHAPResult         # ✅ 保留
    explain_single_case(case_features) -> SingleCaseSHAPResult      # ✅ 保留
```

---

## 3. 系統架構設計

### 3.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API Layer (api/)                              │
│                                                                      │
│  api/routes/pattern_analysis.py                                      │
│  ├─ /xgboost/*   (21 端點 — 保留不變)                                │
│  ├─ /lightgbm/*  (新增 — 與 XGBoost 對等的端點)                      │
│  └─ /model/*     (新增 — 引擎無關的通用端點)                          │
│                                                                      │
│  api/services/                                                       │
│  ├─ model_task_service.py      (新增 — 通用模型任務調度)              │
│  ├─ xgboost_task_service.py    (保留 — XGBoost 專用)                 │
│  ├─ lightgbm_task_service.py   (新增 — LightGBM 專用)               │
│  ├─ model_comparison_service.py (新增 — 雙引擎 A/B 對比)             │
│  └─ model_task_cache.py        (擴展 — 多引擎快取)                   │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  momentum/factories.py  (擴展)                                       │
│  ├─ create_model_trainer('lightgbm', config)  → LightGBMAnalyzer    │
│  ├─ create_model_trainer('xgboost', config)   → XGBoostAnalyzer     │
│  └─ create_model_comparison(engines=['lightgbm', 'xgboost'])        │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                  Momentum Domain (momentum/Analysis/)                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ momentum/core/protocols.py                                       ││
│  │  └─ IModelTrainer (Protocol — 擴展版)                            ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │
│  │ LightGBM     │   │ XGBoost      │   │ (未來引擎)    │             │
│  │ Analyzer     │   │ Analyzer     │   │ CatBoost/   │             │
│  │ (新建)        │   │ (保留/重構)   │   │ TabNet/...  │             │
│  │              │   │              │   │              │             │
│  │ Implements   │   │ Implements   │   │ Implements   │             │
│  │ IModelTrainer│   │ IModelTrainer│   │ IModelTrainer│             │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘             │
│         │                  │                  │                      │
│         └──────────────────┼──────────────────┘                      │
│                            │                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │           Shared Analyzers (引擎無關 — 共享層)                   ││
│  │                                                                  ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ││
│  │  │ SHAPAnalyzer    │  │ CalibrationAnal │  │ DriftAnalyzer   │  ││
│  │  │ (TreeExplainer) │  │ (Brier/ECE)     │  │ (PSI)           │  ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ││
│  │  │ RegimeAnalyzer  │  │ PredictionAnal  │  │ TimeSplitter    │  ││
│  │  │ (Market Phase)  │  │ (Rolling AUC)   │  │ (Purged CV)     │  ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ││
│  │  │ ExpectancyCalc  │  │ BootstrapEst    │  │ CrossSymbolVal  │  ││
│  │  │ (E[R])          │  │ (CI)            │  │ (Generalization)│  ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │           Model Comparison Engine (新建模組)                     ││
│  │  ModelComparison: 雙引擎 A/B 比較 + Consensus 機制              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │           Parameter System (四維參數)                            ││
│  │  ModelConfigManager: YAML/JSON ↔ 自然語言 ↔ Optuna Space       ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 模組依賴圖

```
momentum/core/protocols.py   (IModelTrainer — 定義)
        │
        ├─── momentum/Analysis/lightgbm_analyzer.py (實作)
        ├─── momentum/Analysis/xgboost_analyzer.py  (實作 — 保留)
        └─── momentum/Analysis/model_comparison.py  (消費 — 接收任意 IModelTrainer)
                │
                └── 共享 Analyzers (接收 y_true, y_pred_proba — 引擎無關)
                    ├── shap_analyzer.py (接收 tree model — LGB/XGB 通用)
                    ├── calibration_analyzer.py (接收 y_true, y_pred)
                    ├── drift_analyzer.py (接收 X_train, X_test)
                    ├── regime_analyzer.py (接收 y_true, y_pred, phases)
                    ├── prediction_analyzer.py (接收 predictions DataFrame)
                    ├── time_splitter.py (接收 DataFrame + timestamp)
                    ├── expectancy_calculator.py (接收 y_true, returns)
                    ├── bootstrap_estimator.py (接收 y_true, y_pred)
                    └── cross_symbol_validator.py (接收 IModelTrainer)

momentum/factories.py  (工廠函式)
        │
        └── create_model_trainer(engine, config) → IModelTrainer
```

### 3.3 解耦合規性驗證

| 規則 | 檢查項 | 合規方式 |
|------|--------|---------|
| **Rule 1** | `momentum/` 不 import `api/` | LightGBMAnalyzer 使用 `momentum.core.logging`，不引用 api 層 |
| **Rule 2** | 跨 Domain 使用 Protocol 注入 | ModelComparison 接收 `IModelTrainer`，不直接 import LightGBMAnalyzer |
| **Rule 3** | Service 使用 Factory 建構物件 | `model_task_service.py` 使用 `create_model_trainer()` |
| **Rule 4** | Service 互不引用 | `lightgbm_task_service.py` 不 import `xgboost_task_service.py` |
| **Rule 5** | Config 單一來源 | 模型參數統一在 `momentum/Analysis/model_config.py` |
| **Rule 6** | 測試獨立執行 | `pytest tests/momentum/` 不需啟動 API Server |
| **Rule 7** | DTO 不跨層 | 分析結果使用 `@dataclass`；API 回應使用 `Pydantic BaseModel` |

---

## 4. IModelTrainer Protocol 擴展設計

### 4.1 現有 Protocol（需保留）

```python
# momentum/core/protocols.py — 現有定義
@runtime_checkable
class IModelTrainer(Protocol):
    def train_model(
        self,
        features: Any,
        labels: Any,
        feature_names: Iterable[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        ...
```

### 4.2 擴展 Protocol（新增方法）

```python
# momentum/core/protocols.py — 擴展版
@runtime_checkable
class IModelTrainer(Protocol):
    """
    模型訓練協議（引擎無關）
    
    所有 ML 引擎（LightGBM, XGBoost, CatBoost, ...）必須實作此介面。
    下游消費者（ModelComparison, CrossSymbolValidator, Service 層）
    只依賴此 Protocol，不依賴具體引擎類別。
    """
    
    # === 核心訓練 ===
    def train_model(
        self,
        features: Any,
        labels: Any,
        feature_names: Iterable[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """訓練模型，回傳 ModelPerformance"""
        ...
    
    # === 預測 ===
    def predict_proba(
        self,
        features: Any,
    ) -> Any:
        """回傳預測機率 ndarray shape (n_samples, 2)"""
        ...
    
    # === 特徵重要性 ===
    def get_feature_importance(
        self,
        method: str = 'gain',
        top_n: Optional[int] = None,
    ) -> Any:
        """回傳特徵重要性列表"""
        ...
    
    # === 模型持久化 ===
    def save_model(self, path: str) -> None:
        """儲存模型到指定路徑"""
        ...
    
    def load_model(self, path: str) -> None:
        """從路徑載入模型"""
        ...
    
    # === 引擎 Metadata ===
    def get_model_type(self) -> str:
        """回傳引擎類型字串，如 'lightgbm', 'xgboost'"""
        ...
    
    def get_model_params(self) -> Dict[str, Any]:
        """回傳當前模型參數"""
        ...
    
    def get_native_model(self) -> Any:
        """回傳底層原生模型物件（供 SHAP TreeExplainer 使用）"""
        ...
```

### 4.3 Protocol 擴展向後相容策略

**問題**：擴展 Protocol 會不會破壞現有 XGBoostAnalyzer？

**策略**：
1. XGBoostAnalyzer 已有 `train_model()` → ✅ 相容
2. 新增方法在 XGBoostAnalyzer 中已有等價實現 → 只需 **添加方法別名或 wrapper**
3. `@runtime_checkable` 允許鴨子型別（只要方法存在即可）

**XGBoostAnalyzer 適配映射**：

| Protocol 方法 | XGBoostAnalyzer 現有方法 | 適配方式 |
|---------------|------------------------|---------|
| `train_model()` | `train_model()` ✅ | 已存在 |
| `predict_proba()` | `self.model.predict_proba()` | 新增 wrapper |
| `get_feature_importance()` | `calculate_feature_importance()` | 新增別名 wrapper |
| `save_model()` | 未有 | 新增（使用 pickle/joblib） |
| `load_model()` | 未有 | 新增（使用 pickle/joblib） |
| `get_model_type()` | 未有 | 新增（回傳 `'xgboost'`） |
| `get_model_params()` | `self.params` | 新增 getter |
| `get_native_model()` | `self.model` | 新增 getter |

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Task**: **3.1** IModelTrainer Protocol 擴展
> - **交付物**: `momentum/core/protocols.py`（修改）、`momentum/Analysis/model_types.py`（新增）
> - **前置條件**: 無（Phase 3 第一步）
> - **驗收條件**: (1) `IModelTrainer` 定義 8 個方法 (2) 新增 `IOptimizationObjective` Protocol (3) `isinstance(lgb, IModelTrainer)` → True (4) `isinstance(xgb, IModelTrainer)` → True
> - **實作要點**: 📐 Protocol 定義必須先於所有引擎實作。`IOptimizationObjective` 是 §8 維度 4 Optuna 重構的基礎。共用 dataclass（ModelPerformance 等）定義在 `model_types.py`，從 §13 提取。
> - **預估工作量**: 0.5 天

---

## 5. LightGBM 引擎實作規格

### 5.1 LightGBMAnalyzer 類別設計

**檔案**：`momentum/Analysis/lightgbm_analyzer.py` (新建)

```python
"""
LightGBM Analyzer - 主引擎模型訓練與分析

LightGBM 是本系統的主要 ML 引擎，具備：
- 原生類別特徵支援（Market_Phase, Symbol 等無需 encoding）
- Histogram-based 分割（快速訓練，低記憶體）
- GOSS + EFB（自動樣本抽樣與特徵打包）
- DART 正則化（Dropout 正則化防過擬合）

Author: AI Agent
Date: 2026-02-09
"""

import lightgbm as lgb
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import pickle
from pathlib import Path

from momentum.core.logging import get_logger
from momentum.Analysis.model_types import (
    ModelPerformance, FeatureImportance, OOTValidationResult
)
from momentum.Analysis.calibration_analyzer import CalibrationAnalyzer
from momentum.Analysis.time_splitter import PurgedTimeSeriesSplit
from momentum.Analysis.shap_analyzer import SHAPAnalyzer

logger = get_logger(__name__)


class LightGBMAnalyzer:
    """
    LightGBM 分析引擎
    
    符合 IModelTrainer Protocol。
    與 XGBoostAnalyzer 具有完全等價的分析能力，
    但利用 LightGBM 的原生優勢（速度、類別特徵、記憶體效率）。
    """
    
    def __init__(self, params: Optional[Dict] = None):
        self.logger = logger
        
        # LightGBM 預設參數（量化交易最佳化）
        self.default_params = {
            # Core
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',       # 可切換 'dart' 防過擬合
            'num_leaves': 31,
            'max_depth': -1,               # 不限深度，由 num_leaves 控制
            'learning_rate': 0.05,
            'n_estimators': 200,
            
            # Sampling
            'subsample': 0.8,              # bagging_fraction
            'colsample_bytree': 0.8,       # feature_fraction
            'subsample_freq': 5,           # bagging_freq
            
            # Regularization
            'min_child_samples': 20,       # min_data_in_leaf
            'reg_alpha': 0.1,              # L1
            'reg_lambda': 1.0,             # L2
            'min_gain_to_split': 0.01,
            
            # Category
            'categorical_feature': 'auto', # 自動偵測類別特徵
            
            # System
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1,
            'force_col_wise': True,        # M1 Mac 最佳化
        }
        
        self.params = {**self.default_params, **(params or {})}
        
        self.model: Optional[lgb.LGBMClassifier] = None
        self.feature_names: Optional[List[str]] = None
        self.categorical_features: Optional[List[str]] = None
        self.calibration_analyzer = CalibrationAnalyzer()
        self.shap_analyzer = SHAPAnalyzer()
        self._shap_explainer = None
    
    # ==================== IModelTrainer Protocol 方法 ====================
    
    def get_model_type(self) -> str:
        """回傳引擎類型"""
        return 'lightgbm'
    
    def get_model_params(self) -> Dict[str, Any]:
        """回傳當前模型參數"""
        return dict(self.params)
    
    def get_native_model(self) -> Any:
        """回傳底層 LightGBM 模型物件"""
        return self.model
    
    def predict_proba(self, features: Any) -> np.ndarray:
        """預測機率"""
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 train_model()")
        return self.model.predict_proba(features)
    
    def get_feature_importance(
        self, 
        method: str = 'gain', 
        top_n: Optional[int] = None
    ) -> List:
        """取得特徵重要性（IModelTrainer Protocol 方法）"""
        if self.feature_names is None:
            raise ValueError("特徵名稱尚未設定")
        return self.calculate_feature_importance(
            self.feature_names, method=method, top_n=top_n
        )
    
    def save_model(self, path: str) -> None:
        """儲存模型"""
        if self.model is None:
            raise ValueError("無模型可儲存")
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'categorical_features': self.categorical_features,
            'params': self.params,
            'model_type': 'lightgbm',
        }
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        self.logger.info(f"LightGBM 模型已儲存至 {save_path}")
    
    def load_model(self, path: str) -> None:
        """
        載入模型
        
        ⚠️ 安全注意：pickle.load 會執行任意程式碼。
        只載入來自受信任路徑的模型檔案（data_cache/models/ 目錄內）。
        不接受使用者上傳的 .pkl 檔案。
        未來可改用 LightGBM 原生 save_model/load_model（純文字格式，更安全）。
        """
        load_path = Path(path)
        if not load_path.exists():
            raise FileNotFoundError(f"模型檔案不存在: {load_path}")
        
        # 安全檢查：限制載入路徑
        allowed_base = Path('data_cache/models').resolve()
        resolved_path = load_path.resolve()
        if not str(resolved_path).startswith(str(allowed_base)):
            raise ValueError(f"安全限制：只允許從 {allowed_base} 載入模型")
        
        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)
        
        if model_data.get('model_type') != 'lightgbm':
            raise ValueError(f"模型類型不匹配: 預期 lightgbm，得到 {model_data.get('model_type')}")
        
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.categorical_features = model_data.get('categorical_features')
        self.params = model_data.get('params', self.default_params)
        self.logger.info(f"LightGBM 模型已從 {load_path} 載入")
    
    # ==================== 核心訓練方法 ====================
    
    def train_model(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        early_stopping_rounds: int = 20,
        eval_size: float = 0.2,
        lightgbm_params: Optional[Dict] = None,
        cv_folds: int = 5,
        time_series_split: bool = False,
        timestamps: Optional[List[int]] = None,
        purge_gap: Optional[int] = None,
        embargo_pct: Optional[float] = None,
        categorical_features: Optional[List[str]] = None,
    ) -> 'ModelPerformance':
        """
        訓練 LightGBM 模型
        
        與 XGBoostAnalyzer.train_model() 具有完全等價的介面，
        額外支援 categorical_features 參數（LightGBM 原生類別特徵）。
        
        Args:
            X: 特徵矩陣 (n_samples, n_features)
            y: 標籤數組 (n_samples,) — 1=盈利, 0=虧損
            feature_names: 特徵名稱列表
            early_stopping_rounds: Early stopping 輪數
            eval_size: 驗證集比例
            lightgbm_params: 自訂 LightGBM 參數
            cv_folds: 交叉驗證折數
            time_series_split: 是否使用時間序列切分
            timestamps: 時間戳（用於 time_series_split）
            purge_gap: Purged CV 的 look-ahead 間隔
            embargo_pct: Embargo 比例
            categorical_features: 類別特徵名稱列表（LightGBM 原生支援）
            
        Returns:
            ModelPerformance 物件
        """
        # 處理特徵名稱
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
        elif feature_names is not None:
            self.feature_names = feature_names
        else:
            raise ValueError("當 X 是 numpy array 時，必須提供 feature_names 參數")
        
        self.categorical_features = categorical_features
        
        self.logger.info(
            f"開始訓練 LightGBM 模型 — 樣本數: {len(X)}, 特徵數: {len(self.feature_names)}"
            + (f", 類別特徵: {len(categorical_features)}" if categorical_features else "")
        )
        
        # 更新參數
        if lightgbm_params:
            self.params = {**self.default_params, **lightgbm_params}
        
        # 標籤分佈檢查
        unique, counts = np.unique(y, return_counts=True)
        label_dist = dict(zip(unique.astype(int), counts.astype(int)))
        self.logger.info(f"標籤分佈: {label_dist}")
        
        if len(unique) < 2:
            raise ValueError(f"標籤只有一個類別: {unique}，無法訓練二分類模型")
        
        # 資料切分（與 XGBoostAnalyzer 相同邏輯）
        if time_series_split:
            X_train, X_val, y_train, y_val = self._time_series_split(
                X, y, eval_size, timestamps
            )
        else:
            from sklearn.model_selection import train_test_split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=eval_size, random_state=42, stratify=y
            )
        
        self.logger.info(f"訓練集: {len(X_train)} 樣本, 驗證集: {len(X_val)} 樣本")
        
        # 建立 LightGBM 模型
        fit_params = {**self.params}
        if early_stopping_rounds:
            fit_params['n_estimators'] = fit_params.get('n_estimators', 200)
        
        self.model = lgb.LGBMClassifier(**fit_params)
        
        # 建構 fit 參數
        fit_kwargs = {
            'eval_set': [(X_val, y_val)],
        }
        
        # LightGBM 的 categorical_feature 需在 fit 時傳入
        if categorical_features and isinstance(X_train, pd.DataFrame):
            cat_indices = [
                X_train.columns.get_loc(col) 
                for col in categorical_features 
                if col in X_train.columns
            ]
            if cat_indices:
                fit_kwargs['categorical_feature'] = cat_indices
        
        # 建立 callbacks
        callbacks = [lgb.log_evaluation(period=0)]  # 隱藏訓練日誌
        if early_stopping_rounds:
            callbacks.append(lgb.early_stopping(early_stopping_rounds, verbose=False))
        fit_kwargs['callbacks'] = callbacks
        
        self.model.fit(X_train, y_train, **fit_kwargs)
        
        # 重置 SHAP explainer
        self._shap_explainer = None
        
        # 驗證模型
        performance = self.validate_model(
            X, y, cv_folds=cv_folds,
            time_series_split=time_series_split,
            timestamps=timestamps,
            purge_gap=purge_gap,
            embargo_pct=embargo_pct
        )
        
        self.logger.info(
            f"LightGBM 訓練完成 — "
            f"CV AUC: {performance.cv_auc_mean:.4f} ± {performance.cv_auc_std:.4f}"
        )
        
        return performance
    
    def _time_series_split(self, X, y, eval_size, timestamps):
        """時間序列切分（與 XGBoostAnalyzer 邏輯相同，避免重複）"""
        if timestamps is None:
            order = np.arange(len(y))
        else:
            order = np.argsort(np.array(timestamps))
        
        if isinstance(X, pd.DataFrame):
            X_sorted = X.iloc[order]
        else:
            X_sorted = X[order]
        y_sorted = y[order]
        
        split_idx = int(len(y_sorted) * (1 - eval_size))
        if split_idx < 1 or split_idx >= len(y_sorted):
            raise ValueError("時間序列切分比例不合理，請調整 eval_size")
        
        return X_sorted[:split_idx], X_sorted[split_idx:], y_sorted[:split_idx], y_sorted[split_idx:]
    
    # ==================== 驗證方法（與 XGBoost 等價） ====================
    
    def validate_model(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        cv_folds: int = 5,
        time_series_split: bool = False,
        timestamps: Optional[List[int]] = None,
        purge_gap: Optional[int] = None,
        embargo_pct: Optional[float] = None,
    ) -> 'ModelPerformance':
        """
        交叉驗證模型表現（與 XGBoostAnalyzer.validate_model 等價）
        
        支援 StratifiedKFold 和 PurgedTimeSeriesSplit 兩種模式。
        
        演算法流程:
        1. 依 time_series_split 選擇切分策略（StratifiedKFold 或 PurgedTimeSeriesSplit）
        2. 逐 fold 訓練 LGBMClassifier + 驗證集 AUC
        3. 收集每 fold 的 AUC、feature importance
        4. 計算 CV 平均 AUC、標準差
        5. 回傳 ModelPerformance（不會修改 self.model）
        """
        # 實作與 XGBoostAnalyzer.validate_model 平行
        # 使用相同的 TimeSplitter、相同的指標計算
        ...
    
    def train_with_purged_cv(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        n_splits: int = 5,
        purge_gap: int = 5,
        embargo_pct: float = 0.01,
        lightgbm_params: Optional[Dict] = None,
        early_stopping_rounds: int = 20,
        categorical_features: Optional[List[str]] = None,
    ) -> 'ModelPerformance':
        """
        使用 Purged K-Fold 交叉驗證訓練
        
        與 XGBoostAnalyzer.train_with_purged_cv 等價介面:
        1. 使用 PurgedTimeSeriesSplit 切分資料
        2. 逐 fold 訓練 LightGBM 模型
        3. 最後用全部資料訓練最終模型
        4. 回傳含 CV 統計的 ModelPerformance
        
        Args:
            n_splits: Purged CV 折數
            purge_gap: 去汙染間隔（K-lines 數量）
            embargo_pct: Embargo 比例（防止 look-ahead bias）
            categorical_features: LightGBM 原生類別特徵
        """
        splitter = PurgedTimeSeriesSplit(
            n_splits=n_splits,
            purge_gap=purge_gap,
            embargo_pct=embargo_pct,
        )
        # fold-level 訓練 → 收集 AUC → 最終全量訓練
        ...
    
    def validate_oot(
        self,
        X_oot: Union[pd.DataFrame, np.ndarray],
        y_oot: np.ndarray,
        cv_auc_mean: Optional[float] = None,
    ) -> 'OOTValidationResult':
        """
        OOT 驗證（與 XGBoostAnalyzer.validate_oot 等價）
        
        演算法流程:
        1. 檢查 self.model 已訓練，否則 raise ValueError
        2. 若 len(y_oot) < 50 → 回傳警告 + insufficient_samples 標記
        3. 若 y_oot 只有單一類別 → 回傳 AUC=None + 警告
        4. 計算 OOT AUC = roc_auc_score(y_oot, model.predict_proba(X_oot)[:, 1])
        5. 計算 CV-OOT Gap = cv_auc_mean - oot_auc（若 cv_auc_mean 已提供）
        6. Gap 分級: < 0.05 → 'good', 0.05-0.10 → 'warning', > 0.10 → 'severe'
        7. 回傳 OOTValidationResult
        """
        ...
    
    # ==================== 特徵重要性（與 XGBoost 等價 + LightGBM 增強） ====================
    
    def calculate_feature_importance(
        self,
        feature_names: List[str],
        method: str = 'gain',
        top_n: Optional[int] = None,
    ) -> List['FeatureImportance']:
        """
        計算特徵重要性
        
        LightGBM 支援的 method:
        - 'gain': 該特徵帶來的預測改善（與 XGBoost gain 等價）
        - 'split': 該特徵被使用的次數（與 XGBoost weight 等價）
        
        注意：LightGBM 沒有 'cover'，使用 'split' 作為替代方案。
        """
        ...
    
    def get_all_importance_types(
        self,
        feature_names: List[str],
        top_n: Optional[int] = None,
    ) -> Dict[str, List['FeatureImportance']]:
        """
        取得所有重要性類型
        
        LightGBM 映射：
        - gain → gain
        - cover → N/A（以 split 替代，並標記）
        - weight → split
        """
        return {
            "gain": self.calculate_feature_importance(feature_names, method="gain", top_n=top_n),
            "split": self.calculate_feature_importance(feature_names, method="split", top_n=top_n),
        }
    
    # ==================== 其他分析方法（與 XGBoost 等價） ====================
    
    def calculate_precision_at_k(self, X, y, k_values=None) -> 'PrecisionAtKResult':
        """Precision@K（與 XGBoostAnalyzer 等價）"""
        ...
    
    def calculate_pr_metrics(self, X, y) -> 'PRMetrics':
        """PR 指標（與 XGBoostAnalyzer 等價）"""
        ...
    
    def get_predictions(self, X, y_true=None, case_ids=None) -> 'PredictionOutput':
        """取得預測結果（與 XGBoostAnalyzer 等價）"""
        ...
    
    def calculate_permutation_importance(self, X, y, **kwargs) -> 'PermutationImportanceResult':
        """Permutation Importance（與 XGBoostAnalyzer 等價）"""
        ...
    
    def calculate_fold_importance_stability(self, X, y, **kwargs) -> 'FoldImportanceStabilityResult':
        """Fold 穩定性（與 XGBoostAnalyzer 等價）"""
        ...
    
    def recommend_k(self, y_true, y_pred_proba, **kwargs) -> Dict:
        """推薦 K 值（與 XGBoostAnalyzer 等價）"""
        ...
    
    # ==================== SHAP 分析（共享 SHAPAnalyzer） ====================
    
    def analyze_shap_global(self, X, sample_size=100) -> 'GlobalSHAPResult':
        """全局 SHAP 分析（使用共享 SHAPAnalyzer + TreeExplainer）"""
        if self.model is None:
            raise ValueError("模型尚未訓練")
        return self.shap_analyzer.analyze_global(self.model, X, sample_size=sample_size)
    
    def explain_single_case(self, case_features) -> 'SingleCaseSHAPResult':
        """單案例 SHAP 分析"""
        if self.model is None:
            raise ValueError("模型尚未訓練")
        return self.shap_analyzer.explain_single_case(self.model, case_features)
```

### 5.2 LightGBM 特有能力（XGBoost 沒有的）

#### 5.2.1 原生類別特徵支援

```python
# LightGBM 可以直接使用類別欄位，無需 encoding
categorical_features = ['Market_Phase', 'Symbol_Category']

# XGBoost 需要先 Label Encoding 或 One-Hot
# LightGBM 只需在 fit() 時指定
model.fit(X, y, categorical_feature=cat_indices)
```

**對研究平台的意義**：
- `Market_Phase`（EXTREME_FEAR, FEAR, NEUTRAL, GREED, EXTREME_GREED）可直接作為特徵
- `Symbol` 類別（大盤幣/山寨幣/MEME幣）可直接使用
- 減少特徵工程步驟，提高實驗效率

**Feature Factory 可直接作為 categorical 的特徵清單**（Phase 1 已產出）：

| 特徵層級 | 特徵名稱範例 | 類型 | LightGBM 處理 | XGBoost 處理 |
|---------|------------|------|:----------:|:----------:|
| Layer 7 | `Market_Phase` | 離散：5 值 | ✅ 原生 categorical | Label Encoding |
| Layer 7 | `Regime_Label` | 離散：3-5 值 | ✅ 原生 categorical | Label Encoding |
| 自訂 | `Symbol_Category` | 離散：3-10 值 | ✅ 原生 categorical | Label Encoding |
| Layer 5 | `Day_of_Week` | 週期：7 值 | ✅ 原生 categorical | One-Hot / Cyclic |
| Layer 5 | `Hour_of_Day` | 週期：24 值 | ✅ 原生 categorical | One-Hot / Cyclic |

> 注意：數值型特徵（RSI、MACD 等）不應設為 categorical，保持連續值。

#### 5.2.2 DART Boosting（防過擬合增強）

```python
# DART = Dropouts meet Multiple Additive Regression Trees
lightgbm_params = {
    'boosting_type': 'dart',
    'drop_rate': 0.1,           # 每輪丟棄 10% 的樹
    'max_drop': 50,              # 最多丟棄 50 棵
    'skip_drop': 0.5,           # 50% 機率跳過 dropout
}
```

**適用場景**：當 CV AUC 與 Train AUC 差距 > 0.1 時，自動建議切換 DART。

#### 5.2.3 LightGBM 預設參數對比

| 參數 | LightGBM 預設 | XGBoost 等價 | 差異說明 |
|------|:-------------|:-------------|---------|
| `num_leaves` | 31 | `max_depth=5` (約 32 葉) | LightGBM 用葉數控制，更靈活 |
| `min_child_samples` | 20 | `min_child_weight=5` | LightGBM 用樣本數，更直觀 |
| `subsample_freq` | 5 | N/A | LightGBM 可控制 bagging 頻率 |
| `force_col_wise` | True | N/A | M1 Mac OpenMP 最佳化 |
| `categorical_feature` | 'auto' | N/A | 原生類別支援 |
| `boosting_type` | 'gbdt'/'dart' | N/A | DART 防過擬合 |

### 5.3 LightGBM 方法對照表（與 XGBoost 100% 等價覆蓋）

| 類別 | LightGBMAnalyzer 方法 | XGBoostAnalyzer 對應 | 實作狀態 |
|------|----------------------|---------------------|:--------:|
| **訓練** | `train_model()` | `train_model()` | 🔲 新建 |
| **訓練** | `train_with_purged_cv()` | `train_with_purged_cv()` | 🔲 新建 |
| **驗證** | `validate_model()` | `validate_model()` | 🔲 新建 |
| **驗證** | `validate_oot()` | `validate_oot()` | 🔲 新建 |
| **預測** | `predict_proba()` | `model.predict_proba()` | 🔲 新建 |
| **預測** | `get_predictions()` | `get_predictions()` | 🔲 新建 |
| **重要性** | `calculate_feature_importance()` | `calculate_feature_importance()` | 🔲 新建 |
| **重要性** | `get_all_importance_types()` | `get_all_importance_types()` | 🔲 新建 |
| **重要性** | `calculate_permutation_importance()` | `calculate_permutation_importance()` | 🔲 新建 |
| **重要性** | `calculate_fold_importance_stability()` | `calculate_fold_importance_stability()` | 🔲 新建 |
| **進階** | `calculate_precision_at_k()` | `calculate_precision_at_k()` | 🔲 新建 |
| **進階** | `recommend_k()` | `recommend_k()` | 🔲 新建 |
| **進階** | `calculate_pr_metrics()` | `calculate_pr_metrics()` | 🔲 新建 |
| **SHAP** | `analyze_shap_global()` | `analyze_shap_global()` | 🔲 新建 |
| **SHAP** | `explain_single_case()` | `explain_single_case()` | 🔲 新建 |
| **持久化** | `save_model()` | 新增至 XGBoost | 🔲 新建 |
| **持久化** | `load_model()` | 新增至 XGBoost | 🔲 新建 |
| **Protocol** | `get_model_type()` | 新增至 XGBoost | 🔲 新建 |
| **Protocol** | `get_model_params()` | 新增至 XGBoost | 🔲 新建 |
| **Protocol** | `get_native_model()` | 新增至 XGBoost | 🔲 新建 |

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Task**: **3.2** LightGBMAnalyzer 核心實作
> - **交付物**: `momentum/Analysis/lightgbm_analyzer.py`（🆕 全新）、`momentum/Analysis/model_storage.py`（🔄 修改 — 支援 LightGBM 序列化）
> - **前置條件**: Task 3.1 (Protocol 定義)
> - **驗收條件**: (1) 實作 IModelTrainer 全部 8 個方法 (2) Purged CV + OOT 驗證通過 (3) DART 防過擬合模式支援 (4) 1000 樣本 × 100 特徵訓練 < 5 秒 (M1 Mac) (5) 測試覆蓋率 ≥ 95%
> - **實作要點**: 本章包含 `train_model`、`validate_model`、`validate_oot`、`get_feature_importance`、`predict_proba`、`save_model`/`load_model` 的完整規格與程式碼範本。特別注意 GOSS+EFB 提速、類別特徵原生支援、early stopping 整合。子步驟建議：3.2.1 骨架建立 → 3.2.2 train_model → 3.2.3 validate → 3.2.4 feature importance → 3.2.5 predict → 3.2.6 save/load → 3.2.7 DART 模式。
> - **預估工作量**: 2 天（Phase 3 最大工作量）

---

## 6. XGBoost 引擎重構規格

### 6.1 重構原則

```
1. 【零破壞】：所有 public 方法簽名不變、回傳類型不變
2. 【新增 Protocol 方法】：添加 IModelTrainer 要求的新方法
3. 【抽取共用邏輯】：將引擎無關的程式碼移至共享 Analyzer（可選，Phase 3 不強制）
4. 【保留 import】：`from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer` 路徑不變
```

### 6.2 XGBoostAnalyzer 新增方法

```python
# 在 xgboost_analyzer.py 底部新增
class XGBoostAnalyzer:
    # ... 所有現有方法保留 ...
    
    # ===== IModelTrainer Protocol 新增方法 =====
    
    def predict_proba(self, features: Any) -> np.ndarray:
        """IModelTrainer Protocol — 預測機率"""
        if self.model is None:
            raise ValueError("模型尚未訓練")
        return self.model.predict_proba(features)
    
    def get_feature_importance(
        self, method: str = 'gain', top_n: Optional[int] = None
    ) -> List[FeatureImportance]:
        """IModelTrainer Protocol — 特徵重要性"""
        if self.feature_names is None:
            raise ValueError("特徵名稱尚未設定")
        return self.calculate_feature_importance(
            self.feature_names, method=method, top_n=top_n
        )
    
    def save_model(self, path: str) -> None:
        """IModelTrainer Protocol — 儲存模型"""
        if self.model is None:
            raise ValueError("無模型可儲存")
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'params': self.params,
            'model_type': 'xgboost',
        }
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        self.logger.info(f"XGBoost 模型已儲存至 {save_path}")
    
    def load_model(self, path: str) -> None:
        """IModelTrainer Protocol — 載入模型"""
        load_path = Path(path)
        if not load_path.exists():
            raise FileNotFoundError(f"模型檔案不存在: {load_path}")
        
        # 安全檢查：限制載入路徑（與 LightGBM 一致）
        allowed_base = Path('data_cache/models').resolve()
        resolved_path = load_path.resolve()
        if not str(resolved_path).startswith(str(allowed_base)):
            raise ValueError(f"安全限制：只允許從 {allowed_base} 載入模型")
        
        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)
        if model_data.get('model_type') != 'xgboost':
            raise ValueError(f"模型類型不匹配")
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.params = model_data.get('params', self.default_params)
        self.logger.info(f"XGBoost 模型已從 {load_path} 載入")
    
    def get_model_type(self) -> str:
        return 'xgboost'
    
    def get_model_params(self) -> Dict[str, Any]:
        return dict(self.params)
    
    def get_native_model(self) -> Any:
        return self.model
```

### 6.3 共用 Dataclass 統一位置

**問題**：LightGBMAnalyzer 和 XGBoostAnalyzer 使用相同的 dataclass（ModelPerformance, FeatureImportance, OOTValidationResult 等），目前這些 dataclass 定義在 xgboost_analyzer.py 內部。

**Phase 3 解法**：

> ⚠️ 注意：此處為 `model_types.py` 的**摘要定義**。完整欄位定義見 §13.1。以 §13.1 為權威版本。

```python
# momentum/Analysis/model_types.py (新建 — 共用型別定義)
"""ML 模型共用型別定義，LightGBM 和 XGBoost 共享"""

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ModelPerformance:
    """模型效能指標（引擎無關）"""
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float
    brier_score: Optional[float] = None
    ece: Optional[float] = None
    calibration_quality: Optional[str] = None
    pr_auc: Optional[float] = None
    positive_rate: Optional[float] = None
    engine_type: Optional[str] = None
    training_time_seconds: Optional[float] = None
    n_estimators_actual: Optional[int] = None

@dataclass
class FeatureImportance:
    feature_name: str
    importance: float
    rank: int

@dataclass
class OOTValidationResult:
    oot_auc: Optional[float]
    cv_oot_gap: Optional[float]
    gap_status: str  # 'good' / 'warning' / 'severe'
    n_samples: int

# ... 其他共用 dataclass (PRMetrics, PrecisionAtKResult, etc.)
```

**遷移策略**：
1. 新建 `model_types.py`，定義所有共用 dataclass
2. XGBoostAnalyzer 改為 `from momentum.Analysis.model_types import *`（向後相容 re-export）
3. LightGBMAnalyzer 直接 import `model_types`
4. xgboost_analyzer.py 保留原有 import 路徑（新增 re-export 以不破壞下游）

### 6.4 需從 XGBoostAnalyzer 抽取的共用邏輯（Phase 3 可選，Phase 4 執行）

以下邏輯在 LightGBMAnalyzer 和 XGBoostAnalyzer 中完全相同，**Phase 3 先複製、Phase 4 再重構抽取**：

| 共用邏輯 | 涉及方法 | 抽取目標 |
|---------|---------|---------|
| 時間序列切分 | `_time_series_split()` | `time_splitter.py` |
| 機率摘要計算 | `_build_proba_summary()` | `prediction_utils.py` |
| Precision@K 計算 | `calculate_precision_at_k()` | `metric_calculator.py` |
| Permutation Importance | `calculate_permutation_importance()` | 保留在各 Analyzer（需 self.model） |
| Fold 穩定性 | `calculate_fold_importance_stability()` | 保留在各 Analyzer（需 self.model） |
| K 推薦 | `recommend_k()` | `metric_calculator.py` |

**Phase 3 策略**：「先讓兩個引擎都能跑」→「Phase 4 DRY 重構」

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Task**: **3.3** XGBoostAnalyzer Protocol 適配
> - **交付物**: `momentum/Analysis/xgboost_analyzer.py`（🔄 修改 — 新增方法，不改現有邏輯）
> - **前置條件**: Task 3.1 (Protocol 定義)
> - **驗收條件**: (1) 新增 7 個 Protocol 方法（`predict_proba`、`get_feature_importance` wrapper、`save_model`、`load_model`、`get_model_type`、`get_model_params`、`get_native_model`）(2) ⚠️ 所有現有 21 個 API 端點回歸測試通過 (3) `isinstance(xgb, IModelTrainer)` → True (4) 現有測試全部不受影響
> - **實作要點**: 新增 7 個 IModelTrainer Protocol 方法。`train_model` 已有（不改）。`get_feature_importance` 新增為 wrapper 呼叫已有的 `calculate_feature_importance`。`save_model`/`load_model` 為全新方法（含路徑安全驗證）。`validate_model`/`validate_oot` 已存在於 XGBoostAnalyzer，不屬於 Protocol 擴展範圍。本章 §6.4 有完整重構對照表。
> - **預估工作量**: 0.5 天

---

## 7. 共享分析與視覺化架構

### 7.1 共享 Analyzer 設計原則

**核心要求**：共享 Analyzer **只接收通用型別**（`np.ndarray`, `pd.DataFrame`, `dict`），**不 import** 任何引擎類別。

```python
# ✅ 正確：引擎無關的輸入
class CalibrationAnalyzer:
    def calculate_brier_score(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        ...

# ✅ 正確：接收 Protocol 而非具體類別
class CrossSymbolValidator:
    def validate(self, model: IModelTrainer, X_source, X_target) -> Dict:
        ...

# ❌ 錯誤：依賴特定引擎
class SHAPAnalyzer:
    def analyze(self, model: XGBClassifier) -> Dict:  # 不應綁死 XGBClassifier
        ...
```

### 7.2 SHAP 共享策略

**現狀分析**：`shap.TreeExplainer` 同時支援 XGBoost 和 LightGBM：

```python
import shap

# XGBoost
explainer = shap.TreeExplainer(xgb_model)  # ✅ 支援

# LightGBM
explainer = shap.TreeExplainer(lgb_model)  # ✅ 支援

# 兩者使用完全相同的 API
shap_values = explainer.shap_values(X)
```

**SHAPAnalyzer 修改**：

```python
class SHAPAnalyzer:
    def analyze_global(
        self, 
        model: Any,  # 接收任意 tree model（XGBoost 或 LightGBM）
        X: pd.DataFrame, 
        sample_size: int = 100
    ) -> GlobalSHAPResult:
        """
        全局 SHAP 分析 — 引擎無關
        
        shap.TreeExplainer 自動偵測模型類型（XGBoost/LightGBM/CatBoost）。
        """
        explainer = shap.TreeExplainer(model)  # 自動識別
        ...
```

### 7.3 共享 Analyzer 完整清單

| Analyzer | 輸入型別 | 是否依賴引擎 | 共享方式 |
|---------|---------|:----------:|---------|
| **SHAPAnalyzer** | `model: Any` + `X: DataFrame` | 否（TreeExplainer 自動識別） | ✅ 直接共享 |
| **CalibrationAnalyzer** | `y_true: ndarray` + `y_pred: ndarray` | 否 | ✅ 直接共享 |
| **DriftAnalyzer** | `X_train: ndarray` + `X_test: ndarray` | 否 | ✅ 直接共享 |
| **RegimeAnalyzer** | `y_true, y_pred, phases: ndarray` | 否 | ✅ 直接共享 |
| **PredictionAnalyzer** | `predictions: DataFrame` | 否 | ✅ 直接共享 |
| **TimeSplitter** | `df: DataFrame` + `timestamp_col: str` | 否 | ✅ 直接共享 |
| **ExpectancyCalculator** | `y_true: ndarray` + `returns: ndarray` | 否 | ✅ 直接共享 |
| **BootstrapEstimator** | `y_true: ndarray` + `y_pred: ndarray` | 否 | ✅ 直接共享 |
| **CrossSymbolValidator** | `model: IModelTrainer` + `X, y` | 透過 Protocol | ✅ Protocol 注入 |

### 7.4 前端視覺化共享

所有前端圖表組件**已經是引擎無關的**（接收 JSON 數據而非模型物件），因此：

```
前端組件          ← 接收 JSON Data ← API Response ← Service 呼叫 Analyzer
                                                         │
                                    ┌─────────────────────┼────────────────────┐
                                    │                     │                    │
                                    ▼                     ▼                    ▼
                            LightGBMAnalyzer      XGBoostAnalyzer     (未來引擎)
                                    │                     │                    │
                                    └─────────────────────┼────────────────────┘
                                                          │
                                                   Shared Analyzers
                                                   (同一組計算邏輯)
```

**結論**：前端 11 個圖表組件（Task 4.4）**完全不需修改**，只需後端回傳相同格式的 JSON。

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Task**: **3.2**（LightGBM 整合共享 Analyzer）、**3.5**（ModelComparison）
> - **交付物**: `momentum/Analysis/model_comparison.py`（🆕 全新）、共享 Analyzer 整合（SHAPAnalyzer、CalibrationAnalyzer、MetricCalculator）
> - **前置條件**: Task 3.2 (LightGBM)、Task 3.3 (XGBoost)
> - **驗收條件**: (1) LGB 和 XGB 使用同一 SHAPAnalyzer (2) ComparisonReport 含 AUC 對比 + 特徵排名相關性 (3) 前端 11 個圖表組件無需修改
> - **實作要點**: §7.1 列出 5 個共享 Analyzer 的接入方式。§7.3 說明 ModelComparison 的 A/B 對比邏輯（AUC Gap、Feature Rank 相關性、Consensus Rate）。前端相容性的關鍵是後端回傳相同結構的 JSON。
> - **預估工作量**: 3.2 已含共享整合（2 天內），3.5 = 1 天

---

## 8. 四維參數調整系統

### 8.1 參數層級架構

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Model Parameter Space                             │
│                                                                      │
│  Level 1: Engine Selection (引擎選擇)                                │
│    engine: 'lightgbm' | 'xgboost'                                   │
│                                                                      │
│  Level 2: Training Params (訓練參數)                                 │
│    共通: cv_folds, eval_size, early_stopping_rounds, purge_gap      │
│    LightGBM: num_leaves, min_child_samples, boosting_type, dart_*   │
│    XGBoost:  max_depth, min_child_weight, gamma                     │
│                                                                      │
│  Level 3: Regularization (正則化)                                    │
│    共通: learning_rate, subsample, colsample_bytree, reg_alpha/lambda│
│    LightGBM: min_gain_to_split, drop_rate (DART)                    │
│    XGBoost:  gamma                                                   │
│                                                                      │
│  Level 4: Analysis Params (分析參數)                                 │
│    共通: shap_sample_size, psi_bins, bootstrap_n, precision_k_values │
│    oot_ratio, regime_min_samples, rolling_auc_window                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.2 四維參數介面設計

#### 維度 1：手動 UI 調整

```yaml
# config/model_config.yaml — 使用者手動編輯或 UI 表單
model_training:
  engine: "lightgbm"          # UI 下拉選單
  
  lightgbm:
    num_leaves: 31             # UI 滑桿 [8, 128]
    learning_rate: 0.05        # UI 滑桿 [0.001, 0.3]
    n_estimators: 200          # UI 數字輸入
    min_child_samples: 20      # UI 滑桿 [5, 100]
    subsample: 0.8             # UI 滑桿 [0.5, 1.0]
    colsample_bytree: 0.8     # UI 滑桿 [0.3, 1.0]
    boosting_type: "gbdt"      # UI 下拉: gbdt / dart
    reg_alpha: 0.1             # UI 滑桿 [0, 10]
    reg_lambda: 1.0            # UI 滑桿 [0, 10]
  
  xgboost:
    max_depth: 5               # UI 滑桿 [3, 12]
    learning_rate: 0.05
    n_estimators: 100
    min_child_weight: 5
    subsample: 0.8
    colsample_bytree: 0.8
    gamma: 0.1
    reg_alpha: 0.1
    reg_lambda: 1.0
  
  validation:
    cv_folds: 5                # UI 數字 [3, 10]
    eval_size: 0.2             # UI 滑桿 [0.1, 0.3]
    time_series_split: true    # UI 開關
    purge_gap: 5               # UI 滑桿 [0, 20]
    embargo_pct: 0.01          # UI 滑桿 [0, 0.05]
    oot_ratio: 0.2             # UI 滑桿 [0.1, 0.3]
  
  analysis:
    shap_sample_size: 100      # UI 數字
    psi_bins: 10               # UI 數字
    bootstrap_n: 1000          # UI 數字
    precision_k_values: [1, 5, 10, 20]  # UI 多選
```

#### 維度 2：LLM 自然語言映射

```python
# momentum/Analysis/model_config.py

class ModelConfigManager:
    """
    四維參數管理器
    
    支援：
    1. YAML/JSON 結構化配置（手動 UI）
    2. 自然語言指令解析（LLM V2.0）
    3. Python Dict API（AI Agent V3.0）
    4. Optuna Search Space 定義（自動調參）
    """
    
    # 自然語言 → 參數映射表
    NL_PARAMETER_MAP = {
        # 引擎選擇
        "用 lightgbm": {"engine": "lightgbm"},
        "用 xgboost": {"engine": "xgboost"},
        "用比較快的引擎": {"engine": "lightgbm"},
        "用穩定的引擎": {"engine": "xgboost"},
        
        # 複雜度控制
        "簡單模型": {"lightgbm.num_leaves": 15, "xgboost.max_depth": 3},
        "複雜模型": {"lightgbm.num_leaves": 63, "xgboost.max_depth": 8},
        "預設模型": {"lightgbm.num_leaves": 31, "xgboost.max_depth": 5},
        
        # 過擬合處理
        "防止過擬合": {
            "lightgbm.boosting_type": "dart",
            "lightgbm.min_child_samples": 50,
            "lightgbm.reg_alpha": 1.0,
            "lightgbm.reg_lambda": 5.0,
            "xgboost.gamma": 0.3,
            "xgboost.min_child_weight": 10,
        },
        "寬鬆正則化": {
            "lightgbm.min_child_samples": 10,
            "lightgbm.reg_alpha": 0.0,
            "xgboost.gamma": 0.0,
        },
        
        # 速度/精度權衡
        "快速訓練": {
            "lightgbm.n_estimators": 50,
            "xgboost.n_estimators": 50,
            "lightgbm.learning_rate": 0.1,
            "xgboost.learning_rate": 0.1,
        },
        "精確訓練": {
            "lightgbm.n_estimators": 500,
            "xgboost.n_estimators": 300,
            "lightgbm.learning_rate": 0.01,
            "xgboost.learning_rate": 0.01,
        },
        
        # 驗證設定
        "嚴格驗證": {
            "validation.cv_folds": 10,
            "validation.purge_gap": 10,
            "validation.oot_ratio": 0.25,
        },
        "快速驗證": {
            "validation.cv_folds": 3,
            "validation.purge_gap": 3,
            "validation.oot_ratio": 0.15,
        },
    }
    
    def from_natural_language(self, instruction: str) -> Dict[str, Any]:
        """
        自然語言 → 結構化參數
        
        V1.0: 關鍵字匹配
        V2.0: LLM 語義解析
        
        範例:
            "用 lightgbm，防止過擬合，嚴格驗證"
            → {engine: lightgbm, boosting_type: dart, cv_folds: 10, ...}
        """
        config = {}
        for key, mapping in self.NL_PARAMETER_MAP.items():
            if key in instruction:
                config.update(mapping)
        return config
    
    def to_optuna_space(self, engine: str = 'lightgbm') -> Dict[str, Any]:
        """
        產生 Optuna 搜索空間定義
        
        Returns:
            Dict 適用於 Optuna trial.suggest_* 系列函式
        """
        if engine == 'lightgbm':
            return {
                'num_leaves': ('int', 15, 127),
                'learning_rate': ('float_log', 0.005, 0.3),
                'n_estimators': ('int', 50, 500),
                'min_child_samples': ('int', 5, 100),
                'subsample': ('float', 0.5, 1.0),
                'colsample_bytree': ('float', 0.3, 1.0),
                'reg_alpha': ('float_log', 1e-3, 10.0),
                'reg_lambda': ('float_log', 1e-3, 10.0),
                'min_gain_to_split': ('float', 0.0, 1.0),
                'boosting_type': ('categorical', ['gbdt', 'dart']),
            }
        elif engine == 'xgboost':
            return {
                'max_depth': ('int', 3, 12),
                'learning_rate': ('float_log', 0.005, 0.3),
                'n_estimators': ('int', 50, 300),
                'min_child_weight': ('int', 1, 30),
                'subsample': ('float', 0.5, 1.0),
                'colsample_bytree': ('float', 0.3, 1.0),
                'gamma': ('float', 0.0, 5.0),
                'reg_alpha': ('float_log', 1e-3, 10.0),
                'reg_lambda': ('float_log', 1e-3, 10.0),
            }
        else:
            raise ValueError(f"不支援的引擎: {engine}")
    
    def from_yaml(self, path: str) -> Dict[str, Any]:
        """從 YAML 讀取配置"""
        ...
    
    def from_dict(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """從 Python Dict 建構（AI Agent 直接調用）"""
        ...
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """驗證參數合法性，回傳錯誤列表"""
        ...
```

#### 維度 3：AI Agent 程式化介面

```python
# V3.0 AI Agent 使用方式
from momentum.factories import create_model_trainer

# AI Agent 直接 dict 調參
config = {
    'num_leaves': 63,
    'learning_rate': 0.02,
    'n_estimators': 300,
    'min_child_samples': 30,
    'boosting_type': 'dart',
    'drop_rate': 0.15,
}

trainer = create_model_trainer('lightgbm', config=config)
performance = trainer.train_model(X, y, feature_names=feature_names)

# AI Agent 可讀取並修改參數
current_params = trainer.get_model_params()
current_params['learning_rate'] *= 0.5  # 降低學習率
trainer_v2 = create_model_trainer('lightgbm', config=current_params)
```

#### 維度 4：Optuna 自動調參整合（整體重構設計）

> ⚠️ **架構層級變更**：現有 Optuna 系統已有完整基礎設施（CheckpointManager、ErrorHandler、ProgressMonitor、WebSocket、SQLite）。
> Phase 3 **不是從零建構**，而是**重構 OptunaOptimizer 的目標函式系統**，使其支援多種優化場景。

##### 4a. 現有 Optuna 基礎設施盤點

| 模組 | 檔案 | 現狀 | Phase 3 處置 |
|------|------|------|:----------:|
| `OptunaOptimizer` | `momentum/Optimization/optuna_optimizer.py` | 硬編碼 SignalDensityAnalyzer 目標 | 🔄 重構為可插拔目標 |
| `CheckpointManager` | `momentum/Optimization/checkpoint_manager.py` | 通用 — 定期存/讀 Study | ✅ 保留不動 |
| `ErrorHandler` | `momentum/Optimization/error_handler.py` | 通用 — 錯誤分類 + 重試 | ✅ 保留不動 |
| `ProgressMonitor` | `momentum/Optimization/progress_monitor.py` | 通用 — 里程碑通知 + ETA | ✅ 保留不動 |
| `ResultAnalyzer` | `momentum/Optimization/result_analyzer.py` | 通用 — fANOVA 參數重要性 | ✅ 保留不動 |
| `UniqueSampler` | `momentum/Optimization/optuna_optimizer.py` 內 | 通用 — 去重包裝器 | ✅ 保留（抽出為獨立類別） |
| WebSocket 推送 | `api/websocket/optimization_ws.py` | 通用 — 即時進度推送 | ✅ 保留不動 |
| REST API | `api/routes/optimization.py` | 任務 CRUD + 啟動/取消 | 🔄 擴展 `task_type` 欄位 |
| Task Service | `api/services/optimization_task_service.py` | 任務生命週期管理 | 🔄 擴展 `task_type` 欄位 |
| SQLite Storage | Optuna 內建 `RDBStorage` | Study 持久化 | ✅ 保留不動 |

##### 4b. 重構核心：IOptimizationObjective Protocol

```python
# momentum/core/protocols.py — 新增

class IOptimizationObjective(Protocol):
    """
    可插拔優化目標介面
    
    解耦 OptunaOptimizer 與具體目標函式，
    讓同一個 OptunaOptimizer 引擎可驅動不同優化場景：
    
    Phase 2 原有:
      SignalDensityObjective     → 信號密度分離度最佳化
    
    Phase 3 新增:
      ModelHyperparamObjective   → ML 模型超參數最佳化
      StrategyBacktestObjective  → 進出場策略回測參數最佳化
    
    ⚠️ 設計原則：Protocol 檔案 (protocols.py) 不 import 第三方套件。
    trial 參數型別使用 Any，實作類別自行 import optuna.Trial 並轉型。
    這確保 protocols.py 保持輕量級，僅依賴 stdlib + typing。
    """
    
    @property
    def name(self) -> str:
        """目標名稱（用於 Study 命名與日誌）"""
        ...
    
    @property
    def direction(self) -> str:
        """'maximize' 或 'minimize'"""
        ...
    
    @property
    def directions(self) -> Optional[List[str]]:
        """多目標方向列表（NSGA-II 使用），None 表示單目標"""
        ...
    
    def create_search_space(self, trial: Any) -> Dict[str, Any]:
        """
        定義搜索空間並從 trial 中取樣參數
        
        Args:
            trial: optuna.Trial 實例（型別為 Any 以避免 protocols.py import optuna）
        
        Returns:
            取樣後的參數 dict
        """
        ...
    
    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, ...]]:
        """
        評估一組參數的效能
        
        Args:
            params: 由 create_search_space 產生的參數
            
        Returns:
            單目標: float（越高/低越好，依 direction）
            多目標: Tuple[float, ...]（依 directions 順序）
        """
        ...
    
    def get_pruning_callback(self, trial: Any) -> Optional[Any]:
        """
        回傳 Pruning callback（可選，LightGBM/XGBoost 有原生支援）
        
        Args:
            trial: optuna.Trial 實例
        """
        ...
```

##### 4c. 重構後的 OptunaOptimizer

```python
# momentum/Optimization/optuna_optimizer.py — 重構

# ErrorAction 定義（已存在於 error_handler.py，此處補充明確定義）
from enum import Enum

class ErrorAction(Enum):
    """錯誤處理動作 — OptimizationErrorHandler.handle() 回傳值"""
    RETRY = "retry"    # 重試（將 Trial 標記為 Pruned，Optuna 自動跳過）
    SKIP = "skip"      # 跳過（回傳極差值，不中斷 Study）
    ABORT = "abort"    # 終止（re-raise 異常，停止整個 Study）

class OptunaOptimizer:
    """
    通用 Optuna 優化引擎（重構版）
    
    重構前 (Phase 2):
        OptunaOptimizer → 硬編碼 SignalDensityAnalyzer._objective_function()
    
    重構後 (Phase 3):
        OptunaOptimizer → IOptimizationObjective (可插拔)
        ├── SignalDensityObjective     (Phase 2 原有，保留向後相容)
        ├── ModelHyperparamObjective   (Phase 3 新增 — 模型調參)
        └── StrategyBacktestObjective  (Phase 3 新增 — 策略回測調參)
    
    基礎設施完全保留:
        - CheckpointManager (checkpoint_manager.py)
        - ErrorHandler (error_handler.py)
        - ProgressMonitor (progress_monitor.py)
        - ResultAnalyzer (result_analyzer.py)
        - UniqueSampler (抽出為獨立類別)
    """
    
    def __init__(
        self,
        objective: IOptimizationObjective,  # ← 關鍵變化：注入可插拔目標
        sampler_type: str = 'tpe',
        checkpoint_manager: Optional[CheckpointManager] = None,
        error_handler: Optional[OptimizationErrorHandler] = None,
        progress_monitor: Optional[ProgressMonitor] = None,
    ):
        self.objective = objective
        self.sampler_type = sampler_type
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.error_handler = error_handler or OptimizationErrorHandler()
        self.progress_monitor = progress_monitor or ProgressMonitor()
    
    def create_study(self, study_name: Optional[str] = None) -> optuna.Study:
        """
        建立 Optuna Study
        
        多目標時自動使用 NSGAIISampler
        """
        directions = self.objective.directions
        if directions:
            return optuna.create_study(
                study_name=study_name or f"{self.objective.name}_multi",
                directions=directions,
                sampler=optuna.samplers.NSGAIISampler(),
            )
        else:
            return optuna.create_study(
                study_name=study_name or self.objective.name,
                direction=self.objective.direction,
                sampler=self._create_sampler(),
            )
    
    def optimize(self, n_trials: int = 100, **kwargs) -> optuna.Study:
        """
        執行優化（統一入口）
        
        內部流程:
        1. 建立 Study
        2. 定義 _wrapped_objective（整合 checkpoint + error handling + progress）
        3. 呼叫 study.optimize()
        4. 回傳完成的 Study
        """
        study = self.create_study()
        
        def _wrapped_objective(trial: optuna.Trial) -> Union[float, Tuple[float, ...]]:
            try:
                params = self.objective.create_search_space(trial)
                score = self.objective.evaluate(params)
                self.progress_monitor.on_trial_complete(trial, score)
                self.checkpoint_manager.maybe_save(study)
                return score
            except Exception as e:
                action = self.error_handler.handle(e)
                if action == ErrorAction.RETRY:
                    raise optuna.TrialPruned()
                elif action == ErrorAction.SKIP:
                    return float('-inf') if self.objective.direction == 'maximize' else float('inf')
                else:
                    raise
        
        study.optimize(_wrapped_objective, n_trials=n_trials, **kwargs)
        return study
```

##### 4d. 優化目標 A：模型超參數調整 (ModelHyperparamObjective)

```python
# momentum/Optimization/objectives/model_hyperparam.py — 新增

class ModelHyperparamObjective:
    """
    模型超參數優化目標
    
    目標: 最大化 Purged CV AUC
    參數空間: LightGBM/XGBoost 模型超參數
    使用場景: 尋找最佳模型配置
    
    implements IOptimizationObjective
    """
    
    def __init__(
        self,
        engine: str,  # 'lightgbm' 或 'xgboost'
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        config_manager: ModelConfigManager,
        cv_folds: int = 5,
        purge_gap: int = 5,
    ):
        self.engine = engine
        self.X = X
        self.y = y
        self.feature_names = feature_names
        self.config_manager = config_manager
        self.cv_folds = cv_folds
        self.purge_gap = purge_gap
    
    @property
    def name(self) -> str:
        return f"model_hyperparam_{self.engine}"
    
    @property
    def direction(self) -> str:
        return 'maximize'  # 最大化 CV AUC
    
    @property
    def directions(self) -> Optional[List[str]]:
        return None  # 單目標
    
    def create_search_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """從 ModelConfigManager 產生搜索空間"""
        space = self.config_manager.to_optuna_space(self.engine)
        
        params = {}
        for param_name, (param_type, *bounds) in space.items():
            if param_type == 'int':
                params[param_name] = trial.suggest_int(param_name, bounds[0], bounds[1])
            elif param_type == 'float':
                params[param_name] = trial.suggest_float(param_name, bounds[0], bounds[1])
            elif param_type == 'float_log':
                params[param_name] = trial.suggest_float(
                    param_name, bounds[0], bounds[1], log=True
                )
            elif param_type == 'categorical':
                params[param_name] = trial.suggest_categorical(param_name, bounds[0])
        return params
    
    def evaluate(self, params: Dict[str, Any]) -> float:
        """訓練模型並回傳 CV AUC"""
        trainer = create_model_trainer(self.engine, config=params)
        performance = trainer.train_model(
            self.X, self.y,
            feature_names=self.feature_names,
            cv_folds=self.cv_folds,
            purge_gap=self.purge_gap,
        )
        return performance.cv_auc_mean
    
    def get_pruning_callback(self, trial: optuna.Trial) -> Optional[Any]:
        """LightGBM/XGBoost 原生 Pruning 支援"""
        if self.engine == 'lightgbm':
            return optuna.integration.LightGBMPruningCallback(trial, 'auc')
        elif self.engine == 'xgboost':
            return optuna.integration.XGBoostPruningCallback(trial, 'auc')
        return None
```

##### 4e. 優化目標 B：策略回測參數調整 (StrategyBacktestObjective)

```python
# momentum/Optimization/objectives/strategy_backtest.py — 新增

class StrategyBacktestObjective:
    """
    進出場策略回測參數優化目標
    
    目標: 最大化 Sharpe Ratio（或多目標 Sharpe ↑ + MaxDD ↓）
    參數空間: 進出場策略參數（機率閾值、停損停利、部位大小等）
    使用場景: 已有訓練好的 ML 模型預測值，最佳化如何將預測轉為交易動作
    
    implements IOptimizationObjective
    
    ⚠️ 前置條件: 需先有訓練好的模型 (predict_proba → 機率值)
    """
    
    def __init__(
        self,
        model_predictions: np.ndarray,  # 已訓練模型的預測機率
        price_data: pd.DataFrame,       # 含 OHLCV 的行情資料
        multi_objective: bool = False,   # 是否多目標 (NSGA-II)
    ):
        self.model_predictions = model_predictions
        self.price_data = price_data
        self.multi_objective = multi_objective
    
    @property
    def name(self) -> str:
        return "strategy_backtest"
    
    @property
    def direction(self) -> str:
        return 'maximize'  # 最大化 Sharpe
    
    @property
    def directions(self) -> Optional[List[str]]:
        if self.multi_objective:
            return ['maximize', 'minimize']  # Sharpe ↑, MaxDD ↓
        return None
    
    def create_search_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """進出場策略參數空間"""
        return {
            # === 進場信號 ===
            'entry_probability_threshold': trial.suggest_float(
                'entry_probability_threshold', 0.5, 0.9
            ),
            'entry_confirmation_window': trial.suggest_int(
                'entry_confirmation_window', 1, 5
            ),
            
            # === 出場信號 ===
            'exit_probability_threshold': trial.suggest_float(
                'exit_probability_threshold', 0.3, 0.6
            ),
            'take_profit_pct': trial.suggest_float(
                'take_profit_pct', 0.02, 0.15
            ),
            'stop_loss_pct': trial.suggest_float(
                'stop_loss_pct', 0.01, 0.08
            ),
            'trailing_stop_pct': trial.suggest_float(
                'trailing_stop_pct', 0.005, 0.05
            ),
            
            # === 部位管理 ===
            'position_size_pct': trial.suggest_float(
                'position_size_pct', 0.05, 0.3
            ),
            'max_concurrent_positions': trial.suggest_int(
                'max_concurrent_positions', 1, 5
            ),
            
            # === 風控 ===
            'max_daily_loss_pct': trial.suggest_float(
                'max_daily_loss_pct', 0.02, 0.10
            ),
        }
    
    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, float]]:
        """
        執行回測並回傳效能指標
        
        流程:
        1. 用 model_predictions + 進場閾值 → 產生進出場信號
        2. 根據參數執行向量化模擬回測
        3. 計算 Sharpe Ratio / MaxDD
        """
        signals = self._generate_signals(params)
        backtest_result = self._run_backtest(signals, params)
        
        if self.multi_objective:
            return (backtest_result.sharpe_ratio, backtest_result.max_drawdown)
        return backtest_result.sharpe_ratio
    
    def _generate_signals(self, params: Dict[str, Any]) -> pd.Series:
        """根據模型預測 + 閾值參數產生交易信號"""
        entry_mask = self.model_predictions >= params['entry_probability_threshold']
        exit_mask = self.model_predictions <= params['exit_probability_threshold']
        
        signals = pd.Series(0, index=range(len(self.model_predictions)))
        signals[entry_mask] = 1   # 進場
        signals[exit_mask] = -1   # 出場
        return signals
    
    def _run_backtest(self, signals: pd.Series, params: Dict[str, Any]):
        """
        向量化回測引擎
        
        ⚠️ Phase 3 範圍: 基礎向量化回測（足以作為 Optuna 目標函式）
        ⚠️ Phase 4 延伸: 完整 Event-Driven 回測引擎
        """
        # ... 向量化回測實作（見 §9.1.3 業界實務）
        ...
    
    def get_pruning_callback(self, trial: optuna.Trial) -> Optional[Any]:
        return None  # 回測無內建 Pruning
```

##### 4f. 保留向後相容：SignalDensityObjective

```python
# momentum/Optimization/objectives/signal_density.py — 從原 optuna_optimizer.py 抽取

class SignalDensityObjective:
    """
    信號密度優化目標（Phase 2 原有功能，保留向後相容）
    
    implements IOptimizationObjective
    
    將原 optuna_optimizer.py 中的 _objective_function / _multi_objective_function
    重構為獨立的 Objective 類別，保持所有現有 API 行為與結果不變。
    
    現有前端 WebSocket 推送、分析端點完全不受影響。
    """
    
    @property
    def name(self) -> str:
        return "signal_density"
    
    @property
    def direction(self) -> str:
        return 'maximize'  # 最大化密度分離度
    
    @property
    def directions(self) -> Optional[List[str]]:
        return None  # Phase 2 現有為單目標（dual-density 模式也是加權單值）
    
    def create_search_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """EMA 策略參數空間（與原有 _objective_function 相同）"""
        return {
            'short_period': trial.suggest_int('short_period', 3, 20),
            'mid_period': trial.suggest_int('mid_period', 10, 50),
            'long_period': trial.suggest_int('long_period', 30, 200),
            'data_source': trial.suggest_categorical('data_source', [...]),
            'strategy_logic': trial.suggest_categorical('strategy_logic', [...]),
        }
    
    def evaluate(self, params: Dict[str, Any]) -> float:
        """計算信號密度分離度（與原有邏輯相同，搬遷至此）"""
        # ... 原有 SignalDensityAnalyzer._objective_function 邏輯搬遷至此
        ...
    
    def get_pruning_callback(self, trial: optuna.Trial) -> Optional[Any]:
        return None
```

##### 4g. 端對端優化流水線架構

```
Phase 3 架構（兩階段獨立優化）:

┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│  Stage 1: 模型超參數優化                                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ ModelHyperparamObjective                                     │ │
│  │   └── OptunaOptimizer.optimize(n_trials=100)                │ │
│  │       ├── 目標: 最大化 Purged CV AUC                         │ │
│  │       ├── 輸出: best_model_params                           │ │
│  │       └── 基礎設施: CheckpointManager + ErrorHandler +      │ │
│  │           ProgressMonitor + WebSocket 即時推送               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                          │                                        │
│                          ▼                                        │
│               best_model = train(best_params)                     │
│               predictions = best_model.predict_proba(X)           │
│                          │                                        │
│                          ▼                                        │
│  Stage 2: 策略回測參數優化                                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ StrategyBacktestObjective(predictions)                       │ │
│  │   └── OptunaOptimizer.optimize(n_trials=200)                │ │
│  │       ├── 目標: 最大化 Sharpe Ratio (或多目標 + MaxDD)       │ │
│  │       ├── 輸出: best_strategy_params                        │ │
│  │       └── 同樣享有完整基礎設施                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                          │                                        │
│                          ▼                                        │
│              📊 最終產出: best_model + best_strategy              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

Phase 4 延伸（Joint Optimization — 聯合優化）:

┌──────────────────────────────────────────────────────────────────┐
│  JointOptimizationObjective                                       │
│    └── 單一 Trial 同時調整:                                       │
│        ├── 模型超參數 (num_leaves, learning_rate, ...)            │
│        └── 策略參數 (threshold, stop_loss, ...)                   │
│    └── 目標: 最終回測 Sharpe Ratio                                │
│    └── ⚠️ 計算成本極高（每 Trial = 完整訓練 + 完整回測）          │
│    └── 💡 建議: 先 Stage 1+2 獨立收斂 → 再 Joint Fine-Tune      │
└──────────────────────────────────────────────────────────────────┘
```

##### 4h. 使用範例：完整端對端流程

```python
# 完整使用流程（V1.0 API 呼叫方式）

from momentum.factories import create_optuna_optimizer, create_model_trainer
from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective
from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective

# === Stage 1: 模型超參數優化 ===
model_objective = ModelHyperparamObjective(
    engine='lightgbm',
    X=X_train, y=y_train,
    feature_names=feature_names,
    config_manager=config_manager,
)

model_optimizer = create_optuna_optimizer(
    objective=model_objective,
    sampler_type='tpe',
)
model_study = model_optimizer.optimize(n_trials=100)
best_model_params = model_study.best_params
logger.info(f"最佳模型參數: CV AUC = {model_study.best_value:.4f}")

# === 用最佳參數訓練最終模型 ===
best_trainer = create_model_trainer('lightgbm', config=best_model_params)
best_trainer.train_model(X_train, y_train, feature_names=feature_names)
predictions = best_trainer.predict_proba(X_all)[:, 1]

# === Stage 2: 策略回測參數優化 ===
strategy_objective = StrategyBacktestObjective(
    model_predictions=predictions,
    price_data=price_df,
    multi_objective=True,  # Sharpe + MaxDD 雙目標
)

strategy_optimizer = create_optuna_optimizer(
    objective=strategy_objective,
    sampler_type='nsga2',  # 多目標自動使用 NSGA-II
)
strategy_study = strategy_optimizer.optimize(n_trials=200)

# 多目標: 從 Pareto 前沿選擇最佳策略
pareto_trials = strategy_study.best_trials
logger.info(f"Pareto 前沿包含 {len(pareto_trials)} 組策略")
```

##### 4i. Factory 整合（更新 create_optuna_optimizer）

```python
# momentum/factories.py — 更新

def create_optuna_optimizer(
    objective: 'IOptimizationObjective',
    sampler_type: str = 'tpe',
    checkpoint_dir: Optional[str] = None,
    enable_progress: bool = True,
) -> 'OptunaOptimizer':
    """
    建立 Optuna 優化器（重構版 — 可插拔目標）
    
    Args:
        objective: 優化目標實例
            - ModelHyperparamObjective  → ML 模型超參數調參
            - StrategyBacktestObjective → 進出場策略回測調參
            - SignalDensityObjective    → 信號密度調參（Phase 2 向後相容）
        sampler_type: 取樣器 ('tpe', 'cmaes', 'random', 'gp', 'nsga2')
        checkpoint_dir: Checkpoint 儲存目錄
        enable_progress: 是否啟用 ProgressMonitor
    """
    from momentum.Optimization.optuna_optimizer import OptunaOptimizer
    from momentum.Optimization.checkpoint_manager import CheckpointManager
    from momentum.Optimization.error_handler import OptimizationErrorHandler
    from momentum.Optimization.progress_monitor import ProgressMonitor
    
    return OptunaOptimizer(
        objective=objective,
        sampler_type=sampler_type,
        checkpoint_manager=CheckpointManager(checkpoint_dir=checkpoint_dir),
        error_handler=OptimizationErrorHandler(),
        progress_monitor=ProgressMonitor() if enable_progress else None,
    )
```

### 8.3 參數驗證與安全護欄

```python
class ModelConfigManager:
    """參數安全護欄 — 防止不合理的參數組合"""
    
    SAFETY_RULES = {
        'lightgbm': {
            'num_leaves': {'min': 2, 'max': 256, 'warning_max': 128},
            'learning_rate': {'min': 0.001, 'max': 1.0, 'warning_max': 0.3},
            'n_estimators': {'min': 10, 'max': 2000, 'warning_max': 1000},
            'min_child_samples': {'min': 1, 'max': 500},
            'subsample': {'min': 0.1, 'max': 1.0},
            'colsample_bytree': {'min': 0.1, 'max': 1.0},
        },
        'xgboost': {
            'max_depth': {'min': 1, 'max': 20, 'warning_max': 12},
            'learning_rate': {'min': 0.001, 'max': 1.0, 'warning_max': 0.3},
            'n_estimators': {'min': 10, 'max': 1000, 'warning_max': 500},
            'gamma': {'min': 0.0, 'max': 10.0},
        },
    }
    
    def validate_config(self, config: Dict, engine: str) -> List[str]:
        """
        驗證參數合法性
        
        Returns:
            錯誤訊息列表（空 = 通過）
        """
        errors = []
        rules = self.SAFETY_RULES.get(engine, {})
        
        for param, value in config.items():
            if param in rules:
                rule = rules[param]
                if value < rule.get('min', float('-inf')):
                    errors.append(f"{param}={value} 低於最小值 {rule['min']}")
                if value > rule.get('max', float('inf')):
                    errors.append(f"{param}={value} 高於最大值 {rule['max']}")
                if value > rule.get('warning_max', float('inf')):
                    logger.warning(f"⚠️ {param}={value} 偏高，可能導致過擬合")
        
        # 組合規則
        if engine == 'lightgbm':
            num_leaves = config.get('num_leaves', 31)
            min_child_samples = config.get('min_child_samples', 20)
            if num_leaves > 64 and min_child_samples < 10:
                errors.append(
                    f"num_leaves={num_leaves} 且 min_child_samples={min_child_samples}，"
                    "高複雜度 + 低正則化，過擬合風險極高"
                )
        
        return errors
```

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Task**:
>   - **3.4** ModelConfigManager 四維參數（維度 1-3 + 安全護欄）
>   - **3.9** Optuna 重構 — IOptimizationObjective + ModelHyperparamObjective
>   - **3.10** StrategyBacktestObjective + End-to-End Pipeline
> - **交付物**:
>   - 3.4: `momentum/Analysis/model_config.py`（🆕 全新）、`config/model_config.yaml`（🆕 全新）
>   - 3.9: `momentum/Optimization/optuna_optimizer.py`（🔄 重構）、`momentum/Optimization/objectives/model_hyperparam.py`（🆕）、`momentum/Optimization/objectives/signal_density.py`（🆕 從原始碼抽取）、`api/services/optimization_task_service.py`（🔄 擴展 task_type）、`api/routes/optimization.py`（🔄 擴展 task_type）
>   - 3.10: `momentum/Optimization/objectives/strategy_backtest.py`（🆕）
> - **前置條件**: 3.4 無依賴；3.9 依賴 3.1 (IOptimizationObjective Protocol) + 3.2 (LightGBM) + 3.4 (ConfigManager)；3.10 依賴 3.9
> - **驗收條件**:
>   - 3.4: YAML/Dict/NL/Optuna 四維均能產生合法 config；安全護欄捕獲組合規則違規
>   - 3.9: `create_optuna_optimizer(objective=ModelHyperparamObjective(...))` 可執行 100 trials；現有 SignalDensity 功能不受影響（向後相容）
>   - 3.10: Stage 1 (model) → Stage 2 (strategy) 端對端流程可執行；多目標 NSGA-II 產生 Pareto 前沿
> - **實作要點**: §8.2 維度 4 含完整架構設計（§4a-4i）。重構核心是將 OptunaOptimizer 從硬編碼 SignalDensityAnalyzer 變為注入 IOptimizationObjective。CheckpointManager/ErrorHandler/ProgressMonitor/WebSocket **全部保留不動**。
> - **預估工作量**: 3.4 = 1 天；3.9 = 1 天；3.10 = 1 天

---

## 9. 量化金融業界實務研究

### 9.1 業界 LightGBM/XGBoost 調參與回饋迴路

#### 9.1.1 Two Sigma / Citadel / DE Shaw 的 ML Pipeline 最佳實踐

```
業界標準 ML 迭代迴路:

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  1. Feature Engineering (IC Screening)                               │
│     ├── IC > 0.02 + t-stat > 2.0 → 保留                             │
│     └── 注意：IC 在不同市場體制下可能截然不同                          │
│                                                                      │
│  2. Model Training (Purged CV + OOT)                                 │
│     ├── Primary: LightGBM DART (防過擬合)                            │
│     ├── Validation: XGBoost (交叉驗證)                               │
│     └── Consensus: 兩者 AUC 差距 < 0.03 → 高信心                    │
│                                                                      │
│  3. Model Selection (Pareto Frontier)                                │
│     ├── X 軸: OOT AUC (泛化能力)                                     │
│     ├── Y 軸: CV-OOT Gap (穩定性)                                    │
│     └── 選擇 Pareto 前沿的模型                                       │
│                                                                      │
│  4. Post-Training Analysis                                           │
│     ├── SHAP → 理解「為什麼預測漲」                                  │
│     ├── PSI → 偵測特徵飄移（Data Drift）                             │
│     ├── Rolling AUC → 偵測模型退化（Concept Drift）                  │
│     └── Regime Analysis → 不同市場相位的策略差異化                    │
│                                                                      │
│  5. Feedback Loop (回饋迴路)                                         │
│     ├── Rolling AUC 連續 3 個月 < 0.55 → 觸發重訓練                 │
│     ├── PSI Top-5 特徵 > 0.25 → 觸發特徵工程重新篩選                │
│     ├── Regime 切換 → 動態調整 threshold + position size             │
│     └── 新數據可用 → 增量更新模型（Online Learning / Retrain）        │
│                                                                      │
│  6. Ensemble Strategy (集成策略)                                     │
│     ├── Soft Voting: (LGB_proba + XGB_proba) / 2                    │
│     ├── Stacking: Level-2 Logistic Regression                        │
│     ├── Conditional: Market Phase = FEAR → LGB; 其他 → XGB          │
│     └── Consensus Filter: 雙引擎 > 0.7 才交易                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

#### 9.1.2 量化基金常見的模型退化偵測策略

| 策略 | 偵測指標 | 觸發條件 | 行動 |
|------|---------|---------|------|
| **滾動效能監控** | Rolling AUC (30d window) | 連續 3 期 < 0.55 | 暫停交易 + 重訓練 |
| **特徵飄移警報** | PSI (Top-20 特徵) | 任一 PSI > 0.25 | 重新特徵篩選 + 重訓練 |
| **體制轉換偵測** | Market Phase 切換 | GREED → FEAR 轉換 | 動態調整 threshold |
| **Cross-Asset 泛化** | 跨幣種 AUC Gap | Gap > 0.15 | 加入更多幣種訓練 |
| **校準偏移** | ECE 趨勢 | ECE 連續上升 | 重新校準 (Platt/Isotonic) |

#### 9.1.3 Kaggle 金融賽事的頂級方案經驗

```
業界共識 (Top-5 Solutions, 2023-2025):

1. 【特徵為王】Feature Engineering 貢獻 60%+ 的改進
   → 本系統 Phase 1 Feature Factory 已完成 6514 特徵

2. 【LightGBM DART 是防過擬合的首選】
   → 在不平衡資料 + 時間序列場景，DART 優於 vanilla GBDT

3. 【Purged CV 是基本功】
   → 金融數據必須 Purge + Embargo，否則 CV AUC 虛高

4. 【雙引擎 Consensus > 單引擎】
   → LGB + XGB 雙引擎確認，信心度提升 15-25%

5. 【Optuna 不只調模型參數】
   → 也調整特徵篩選閾值 (IC cutoff)、交易閾值 (probability cutoff)
   → 形成「全鏈路最佳化」(End-to-End Optimization)

6. 【Post-Training 分析 = 超參數調整的方向指引】
   → SHAP 發現 RSI 最重要 → 增加 RSI 衍生特徵
   → PSI 發現 Volume 飄移 → 切換至 相對 Volume 特徵
   → Regime Analysis 發現 FEAR 表現好 → 放大 FEAR 時段權重
```

### 9.2 本系統的回饋迴路設計

```python
# momentum/Analysis/model_feedback.py (Phase 4 延伸)

from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class Suggestion:
    """模型回饋建議（ModelFeedbackLoop 產出）"""
    category: str          # 'overfitting' | 'feature_drift' | 'model_degradation' | 'class_imbalance'
    severity: str          # 'info' | 'warning' | 'critical'
    message: str           # 人類可讀的建議訊息
    suggested_params: Optional[Dict] = None   # 建議調整的參數（None = 無法自動建議）
    action: Optional[str] = None              # 建議動作 ('retrain_with_feature_selection', 'full_retrain', etc.)
    confidence: float = 0.5                   # 建議信心度 [0, 1]

class ModelFeedbackLoop:
    """
    模型回饋迴路引擎
    
    ⚠️ 範圍邊界說明：
    ┌──────────────────────────────────────────────────────────────┐
    │ Phase 3 範圍（本規格）:                                     │
    │   - analyze_and_suggest() 的規則框架（只定義規則結構）       │
    │   - 不包含自動執行能力                                      │
    │   - 回傳 Suggestion 物件供前端 UI 顯示                     │
    │                                                             │
    │ Phase 4 延伸（未來）:                                       │
    │   - 半自動建議 → 人工一鍵確認 → 自動調參重訓                │
    │   - Rolling AUC 自動監控 + 警報通知                         │
    │                                                             │
    │ Phase 5 延伸（V3.0 Agent）:                                 │
    │   - 全自動執行 → 人工審計日誌                               │
    │   - 自主決定重訓練 + 特徵篩選 + 參數調整                    │
    └──────────────────────────────────────────────────────────────┘
    
    Phase 3: 手動分析 → 人工決策
    Phase 4: 半自動建議 → 人工確認
    Phase 5: 全自動執行 → 人工審計
    """
    
    def analyze_and_suggest(
        self, 
        model_result: Dict,
        historical_results: List[Dict],
    ) -> List[Suggestion]:
        """
        分析模型結果並產生調參建議
        
        Phase 3 輸出示例:
        [
            Suggestion(
                category="overfitting",
                severity="warning",
                message="CV-OOT Gap = 0.12，建議啟用 DART 或增加正則化",
                suggested_params={"boosting_type": "dart", "reg_lambda": 5.0},
                confidence=0.85,
            ),
            Suggestion(
                category="feature_drift",
                severity="info",
                message="RSI_14 PSI = 0.18，分佈輕微偏移，暫不需調整",
                suggested_params=None,
                confidence=0.70,
            ),
        ]
        """
        suggestions = []
        
        # 規則 1：過擬合偵測
        cv_oot_gap = model_result.get('cv_oot_gap', 0)
        if cv_oot_gap > 0.10:
            suggestions.append(Suggestion(
                category="overfitting",
                severity="warning",
                message=f"CV-OOT Gap = {cv_oot_gap:.2f}，建議啟用 DART 或增加正則化",
                suggested_params={
                    "boosting_type": "dart",
                    "reg_lambda": max(5.0, model_result.get('reg_lambda', 1.0) * 3),
                    "min_child_samples": max(30, model_result.get('min_child_samples', 20)),
                },
            ))
        
        # 規則 2：特徵飄移
        drift_report = model_result.get('drift_report', {})
        severe_features = drift_report.get('severe_features', [])
        if severe_features:
            suggestions.append(Suggestion(
                category="feature_drift",
                severity="warning",
                message=f"{len(severe_features)} 個特徵嚴重飄移: {severe_features[:3]}",
                suggested_params=None,  # 需要重新特徵篩選
                action="retrain_with_feature_selection",
            ))
        
        # 規則 3：模型退化
        rolling_auc = model_result.get('rolling_auc_latest', None)
        if rolling_auc is not None and rolling_auc < 0.55:
            suggestions.append(Suggestion(
                category="model_degradation",
                severity="critical",
                message=f"最近 Rolling AUC = {rolling_auc:.3f}，模型可能已退化",
                suggested_params=None,
                action="full_retrain",
            ))
        
        # 規則 4：類別不平衡
        positive_rate = model_result.get('positive_rate', 0.5)
        if positive_rate < 0.15:
            suggestions.append(Suggestion(
                category="class_imbalance",
                severity="info",
                message=f"正例比例 = {positive_rate:.1%}，建議使用 PR AUC 而非 ROC AUC",
                suggested_params={"metric": "binary_logloss"},
            ))
        
        return suggestions
```

---

## 10. ML 演算法擴展性設計

### 10.1 擴展架構

```
IModelTrainer (Protocol)
├── LightGBMAnalyzer       ✅ Phase 3
├── XGBoostAnalyzer        ✅ Phase 3 (重構)
├── CatBoostAnalyzer       🔲 Phase 5+ (原生類別 + GPU，適合大規模幣種)
├── TabNetAnalyzer         🔲 Phase 6+ (注意力機制，適合高維稀疏特徵)
├── LinearModelAnalyzer    🔲 Phase 5+ (Logistic/Ridge，作為 Baseline)
├── StackingEnsemble       🔲 Phase 5+ (Level-2 組合多引擎)
└── AutoMLAnalyzer         🔲 Phase 7+ (自動選引擎 + 自動調參)
```

### 10.2 新增引擎的標準流程

```markdown
## 新增 ML 引擎 Checklist（以 CatBoost 為範例）

### 前置條件
- [ ] pip install catboost → 更新 requirements.txt
- [ ] 確認 M1 Mac 相容性

### 實作步驟
1. [ ] 建立 `momentum/Analysis/catboost_analyzer.py`
2. [ ] 實作 IModelTrainer Protocol 所有方法:
   - [ ] train_model()
   - [ ] predict_proba()
   - [ ] get_feature_importance()
   - [ ] save_model() / load_model()
   - [ ] get_model_type() → 'catboost'
   - [ ] get_model_params()
   - [ ] get_native_model()
3. [ ] 確認 SHAP TreeExplainer 支援 CatBoost ✅
4. [ ] 在 `momentum/factories.py` 新增:
   ```python
   def create_model_trainer(engine: str, config: Dict = None):
       if engine == 'catboost':
           from momentum.Analysis.catboost_analyzer import CatBoostAnalyzer
           return CatBoostAnalyzer(params=config)
   ```
5. [ ] 在 `ModelConfigManager` 新增 CatBoost 參數空間
6. [ ] 在 `ModelComparison` 中加入 CatBoost 支援
7. [ ] 新增 API 路由 `/catboost/*`（或使用 `/model/*` 通用路由）
8. [ ] 測試:
   - [ ] 單元測試（train/predict/importance/save/load）
   - [ ] 共享 Analyzer 相容性（SHAP/PSI/Calibration）
   - [ ] 整合測試（API 端到端）

### 驗收
- [ ] `isinstance(catboost_analyzer, IModelTrainer)` → True
- [ ] 所有共享 Analyzer 可正常調用
- [ ] 前端圖表無需修改即可顯示
```

### 10.3 Model Comparison Engine

```python
# momentum/Analysis/model_comparison.py (新建)

class ModelComparison:
    """
    雙引擎（或多引擎）A/B 對比引擎
    
    接收任意數量的 IModelTrainer 實例，產出對比報告。
    """
    
    def __init__(self, trainers: Dict[str, 'IModelTrainer']):
        """
        Args:
            trainers: {engine_name: IModelTrainer} 字典
                      e.g., {'lightgbm': lgb_analyzer, 'xgboost': xgb_analyzer}
        """
        self.trainers = trainers
        self.results: Dict[str, Dict] = {}
    
    def train_all(
        self,
        X: Any,
        y: np.ndarray,
        feature_names: List[str],
        **kwargs,
    ) -> Dict[str, 'ModelPerformance']:
        """訓練所有引擎，回傳各自 ModelPerformance"""
        performances = {}
        for name, trainer in self.trainers.items():
            logger.info(f"開始訓練 {name} 引擎")
            perf = trainer.train_model(X, y, feature_names=feature_names, **kwargs)
            performances[name] = perf
            self.results[name] = {'performance': perf}
        return performances
    
    def compare(self) -> 'ComparisonReport':
        """
        產生對比報告
        
        Returns:
            ComparisonReport 包含:
            - 各引擎 AUC/PR-AUC 對比
            - Consensus Score (兩者都預測正例的比例)
            - 特徵重要性排名相關性 (Spearman)
            - 推薦引擎 + 理由
        """
        ...
    
    def consensus_predictions(
        self,
        X: Any,
        method: str = 'soft_voting',  # 'soft_voting' | 'hard_voting' | 'min_confidence'
        threshold: float = 0.5,
    ) -> np.ndarray:
        """
        共識預測 — 多引擎聚合
        
        soft_voting: (proba_lgb + proba_xgb) / 2
        hard_voting: 多數決
        min_confidence: 所有引擎都 > threshold 才為正
        """
        ...


@dataclass
class ComparisonReport:
    """雙引擎對比報告"""
    engine_performances: Dict[str, 'ModelPerformance']
    auc_comparison: Dict[str, float]
    consensus_rate: float  # 兩引擎預測一致的比例
    feature_rank_correlation: float  # Spearman 相關 (Top-20 特徵排名)
    recommended_engine: str
    recommendation_reason: str
    
    def to_dict(self) -> Dict:
        ...
```

---

## 11. Factory 與 Service 整合

### 11.1 momentum/factories.py 新增函式

```python
# momentum/factories.py — 新增

def create_model_trainer(
    engine: str = 'lightgbm',
    config: Optional[Dict[str, Any]] = None,
) -> 'IModelTrainer':
    """
    建立模型訓練器（引擎無關的工廠函式）
    
    Args:
        engine: 'lightgbm' | 'xgboost'
        config: 自訂參數字典
    
    Returns:
        IModelTrainer 實例
    
    Raises:
        ValueError: 不支援的引擎類型
    """
    if engine == 'lightgbm':
        from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
        return LightGBMAnalyzer(params=config)
    elif engine == 'xgboost':
        from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
        return XGBoostAnalyzer(params=config)
    else:
        raise ValueError(
            f"不支援的引擎: {engine}。"
            f"可用引擎: lightgbm, xgboost"
        )


def create_model_comparison(
    engines: Optional[List[str]] = None,
    configs: Optional[Dict[str, Dict]] = None,
) -> 'ModelComparison':
    """
    建立雙引擎（或多引擎）對比器
    
    Args:
        engines: 引擎列表，預設 ['lightgbm', 'xgboost']
        configs: 各引擎參數 {engine_name: config_dict}
    """
    from momentum.Analysis.model_comparison import ModelComparison
    
    engines = engines or ['lightgbm', 'xgboost']
    configs = configs or {}
    
    trainers = {}
    for engine in engines:
        trainers[engine] = create_model_trainer(engine, configs.get(engine))
    
    return ModelComparison(trainers=trainers)


def create_model_config_manager() -> 'ModelConfigManager':
    """建立參數管理器"""
    from momentum.Analysis.model_config import ModelConfigManager
    return ModelConfigManager()
```

### 11.2 api/services/ 新增服務

#### model_task_service.py (新增 — 通用模型任務調度)

```python
# api/services/model_task_service.py

class ModelTaskService:
    """
    通用模型任務調度服務
    
    接收引擎名稱 + 參數，委託 Factory 建構 IModelTrainer，
    執行訓練 + 分析 + 快取結果。
    """
    
    def __init__(self):
        self.task_cache = ModelTaskCache()
    
    async def start_training_task(
        self,
        engine: str,
        config: Dict,
        data_source: str,  # CSV path or case search result ID
    ) -> str:
        """
        啟動非同步訓練任務
        
        Returns:
            task_id
        """
        task_id = str(uuid.uuid4())
        asyncio.create_task(self._run_task(task_id, engine, config, data_source))
        return task_id
    
    async def _run_task(self, task_id, engine, config, data_source):
        try:
            # 1. 建立 trainer
            trainer = create_model_trainer(engine, config)
            
            # 2. 載入數據
            X, y, feature_names = await self._load_data(data_source)
            
            # 3. 訓練
            performance = trainer.train_model(X, y, feature_names=feature_names, **config)
            
            # 4. 共享分析（引擎無關）
            y_pred_proba = trainer.predict_proba(X)[:, 1]
            
            calibration = self.calibration_analyzer.calculate_metrics(y, y_pred_proba)
            shap_result = self.shap_analyzer.analyze_global(
                trainer.get_native_model(), X
            )
            
            # 5. 快取結果
            self.task_cache.store(task_id, {
                'engine': engine,
                'performance': performance,
                'calibration': calibration,
                'shap': shap_result,
                # ...
            })
            
        except Exception as e:
            logger.error(f"Task {task_id} 失敗", exc_info=True)
            self.task_cache.store(task_id, {'status': 'failed', 'error': str(e)})
```

### 11.3 api/routes/ 新增端點

```python
# api/routes/pattern_analysis.py — 新增（保留所有現有端點）

# ===== 通用模型端點（引擎無關） =====

@router.post("/model/train", response_model=TaskStartResponse)
async def start_model_training(request: ModelTrainingRequest):
    """
    啟動模型訓練任務（通用端點）
    
    可選擇 engine='lightgbm' 或 'xgboost'
    """
    task_id = await model_task_service.start_training_task(
        engine=request.engine,
        config=request.params,
        data_source=request.data_source,
    )
    return TaskStartResponse(task_id=task_id)

@router.get("/model/{task_id}/performance", response_model=ModelPerformanceResponse)
async def get_model_performance(task_id: str):
    """取得模型效能（引擎無關）"""
    ...

@router.get("/model/{task_id}/comparison", response_model=ComparisonReportResponse)
async def get_model_comparison(task_id: str):
    """取得雙引擎對比報告"""
    ...

# ===== LightGBM 專用端點（與 XGBoost 對等） =====

@router.post("/lightgbm/train", response_model=TaskStartResponse)
async def start_lightgbm_training(request: LightGBMTrainingRequest):
    """啟動 LightGBM 訓練"""
    ...

@router.get("/lightgbm/{task_id}/results", response_model=LightGBMResultsResponse)
async def get_lightgbm_results(task_id: str):
    """取得 LightGBM 分析結果"""
    ...

# ... 與 /xgboost/* 端點完全對等的 /lightgbm/* 端點 ...
```

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Task**:
>   - **3.6** Factory 函式 + Service 整合
>   - **3.7** API 端點擴展
> - **交付物**:
>   - 3.6: `momentum/factories.py`（🔄 修改 — 新增 `create_model_trainer`、`create_model_comparison`、更新 `create_optuna_optimizer`）、`api/services/model_task_service.py`（🆕）、`api/services/xgboost_task_cache.py`（🔄 擴展為 ModelTaskCache）
>   - 3.7: `api/routes/pattern_analysis.py`（🔄 修改 — 新增 `/model/*` 和 `/lightgbm/*` 端點）
> - **前置條件**: 3.6 依賴 3.2 + 3.3；3.7 依賴 3.6
> - **驗收條件**: (1) `create_model_trainer('lightgbm')` / `create_model_trainer('xgboost')` 成功 (2) `/xgboost/*` 現有 21 端點不受影響 (3) 新增 `/lightgbm/*` 對等端點 (4) 通用 `/model/train` 端點可選擇引擎
> - **實作要點**: §11.1 定義 Factory 函式簽名。§11.2 定義 ModelTaskService 的非同步任務調度模式。§11.3 定義 API 端點路由。注意解耦規則: api/services 不直接 import Engine，喜用 Factory。
> - **預估工作量**: 3.6 = 0.5 天；3.7 = 0.5 天

---

## 12. 邊界條件與驗證覆蓋

### 12.1 輸入驗證矩陣

#### 資料輸入邊界

| 邊界條件 | 預期行為 | 測試方法 | 覆蓋引擎 |
|---------|---------|---------|:-------:|
| `X` 為空 DataFrame | `ValueError("X 為空")` | `X = pd.DataFrame()` | LGB + XGB |
| `y` 全為 0 | `ValueError("標籤只有一個類別")` | `y = np.zeros(100)` | LGB + XGB |
| `y` 全為 1 | `ValueError("標籤只有一個類別")` | `y = np.ones(100)` | LGB + XGB |
| `len(X) != len(y)` | `ValueError("X 與 y 長度不一致")` | 長度不等 | LGB + XGB |
| `X` 含 NaN | 引擎自動處理（Tree-based 支援 NaN） | 插入 NaN | LGB + XGB |
| `X` 含 Inf | `ValueError("X 含無限值")` | 插入 Inf | LGB + XGB |
| `X` 只有 1 個特徵 | 正常訓練（但 SHAP 可能單調） | 單欄 X | LGB + XGB |
| `X` 有 10000 個特徵 | 正常訓練（但警告特徵過多） | 大 X | LGB + XGB |
| `feature_names` 為 None 且 X 是 ndarray | `ValueError("必須提供 feature_names")` | | LGB + XGB |
| `feature_names` 與 X 欄數不符 | `ValueError("特徵數量不匹配")` | | LGB + XGB |

#### 參數邊界

| 邊界條件 | 預期行為 | 測試方法 | 覆蓋引擎 |
|---------|---------|---------|:-------:|
| `cv_folds = 1` | `ValueError("交叉驗證至少 2 折")` | | LGB + XGB |
| `cv_folds = 100`（超過樣本數） | `ValueError("折數超過樣本數")` | | LGB + XGB |
| `eval_size = 0`（無驗證集） | `ValueError("eval_size 必須 > 0")` | | LGB + XGB |
| `eval_size = 1`（無訓練集） | `ValueError("eval_size 必須 < 1")` | | LGB + XGB |
| `purge_gap` 大於資料筆數 | `ValueError("purge_gap 過大")` | | LGB + XGB |
| `learning_rate = 0` | `ValueError("learning_rate 必須 > 0")` | | LGB + XGB |
| `num_leaves = 1` (LGB) | `ValueError("num_leaves 必須 >= 2")` | | LGB |
| `max_depth = 0` (XGB) | `ValueError("max_depth 必須 >= 1")` | | XGB |
| `engine = 'unknown'` | `ValueError("不支援的引擎")` | Factory | N/A |

#### 模型狀態邊界

| 邊界條件 | 預期行為 | 測試方法 | 覆蓋引擎 |
|---------|---------|---------|:-------:|
| 未訓練即呼叫 `predict_proba` | `ValueError("模型尚未訓練")` | | LGB + XGB |
| 未訓練即呼叫 `get_feature_importance` | `ValueError("模型尚未訓練")` | | LGB + XGB |
| 未訓練即呼叫 `save_model` | `ValueError("無模型可儲存")` | | LGB + XGB |
| `load_model` 路徑不存在 | `FileNotFoundError` | | LGB + XGB |
| `load_model` 類型不匹配 | `ValueError("模型類型不匹配")` | 載入 XGB 模型到 LGB | LGB + XGB |
| 載入後再訓練（覆蓋） | 正常覆蓋舊模型 | | LGB + XGB |

#### OOT 驗證邊界

| 邊界條件 | 預期行為 | 測試方法 | 覆蓋引擎 |
|---------|---------|---------|:-------:|
| OOT 樣本 < 50 | 警告 + 標記 "insufficient_samples" | 小 OOT 集 | LGB + XGB |
| OOT 只有單一類別 | 警告 + AUC 設為 None | | LGB + XGB |
| OOT 時間範圍與訓練重疊 | `ValueError("時間範圍重疊")` | | LGB + XGB |

#### 不平衡標籤場景

| 邊界條件 | 預期行為 | 測試方法 | 覆蓋引擎 |
|---------|---------|---------|:-------:|
| 正例比例 < 5%（極度不平衡） | 警告 + 自動切換 metric 為 `binary_logloss` | `y = np.array([1]*5 + [0]*95)` | LGB + XGB |
| 正例比例 = 50%（完美平衡） | 正常訓練，不調整 | `y = np.array([1]*50 + [0]*50)` | LGB + XGB |
| 正例比例 > 95%（反向不平衡） | 警告 + 建議 label 可能反轉 | `y = np.array([1]*96 + [0]*4)` | LGB + XGB |
| 正例比例 < 1%（接近無正例） | `ValueError("正例比例過低，無法有效訓練")` | `y = np.array([1] + [0]*199)` | LGB + XGB |

#### SHAP 邊界

| 邊界條件 | 預期行為 | 測試方法 | 覆蓋引擎 |
|---------|---------|---------|:-------:|
| `sample_size > len(X)` | 使用全部樣本（不抽樣） | | LGB + XGB |
| `sample_size = 0` | `ValueError("sample_size 必須 > 0")` | | LGB + XGB |
| 單案例 SHAP case_id 不存在 | `ValueError("case_id 不存在")` | | LGB + XGB |

### 12.2 測試覆蓋目標

| 測試層級 | 目標覆蓋率 | 測試數量估算 |
|---------|:---------:|:-----------:|
| **LightGBMAnalyzer 單元測試** | ≥ 95% | 45-55 |
| **XGBoost 新增方法單元測試** | ≥ 95% | 15-20 |
| **ModelComparison 單元測試** | ≥ 90% | 15-20 |
| **ModelConfigManager 單元測試** | ≥ 90% | 20-25 |
| **共享 Analyzer 與 LGB 整合測試** | ≥ 85% | 15-20 |
| **API 端點整合測試** | ≥ 80% | 10-15 |
| **邊界條件測試** | 100% | 40-50 (上表所有項) |
| **合計** | | **~160-205** |

### 12.3 測試檔案結構

```
tests/
├── momentum/
│   ├── Analysis/
│   │   ├── test_lightgbm_analyzer.py           # LightGBM 核心測試
│   │   ├── test_lightgbm_edge_cases.py         # LightGBM 邊界條件
│   │   ├── test_xgboost_protocol_methods.py    # XGBoost 新增 Protocol 方法
│   │   ├── test_model_comparison.py            # 雙引擎對比測試
│   │   ├── test_model_config_manager.py        # 參數系統測試
│   │   ├── test_shared_analyzers_lightgbm.py   # 共享 Analyzer + LightGBM 整合
│   │   └── test_model_trainer_protocol.py      # Protocol 合規性測試
│   └── Optimization/
│       └── test_optuna_objectives.py           # Optuna 目標函式測試（3 種 Objective）
├── api/
│   └── test_model_api_endpoints.py             # API 端點測試
└── conftest.py                                  # 共用 fixtures
```

> 📋 **PLAN 轉換標注**
> - **章節類型**: TESTING
> - **對應 Task**: **3.8** 測試套件（160+ 測試）
> - **交付物**: `tests/momentum/Analysis/` 目錄下 7 個測試檔案 + `tests/momentum/Optimization/test_optuna_objectives.py` + `tests/api/test_model_api_endpoints.py` + `tests/conftest.py`
> - **前置條件**: Task 3.2 (LightGBM)、Task 3.3 (XGBoost)、Task 3.5 (Comparison)
> - **驗收條件**: (1) 總測試數 ≥ 160 (2) §12.1 邊界條件矩陣全部覆蓋 (3) LightGBM 覆蓋率 ≥ 95% (4) 邊界條件覆蓋率 100% (5) 所有測試可獨立執行（不需 run_api.py）
> - **實作要點**: §12.1 提供完整邊界條件矩陣（資料輸入 / 參數 / 模型狀態 / OOT / 不平衡標籤 / SHAP 共 6 類別）。§12.2 定義各層級目標覆蓋率。§12.3 定義測試檔案結構。建議子步驟：先寫 conftest + LGB 核心 → 邊界 → XGB Protocol → Comparison → Config → API。
> - **預估工作量**: 1-2 天

---

## 13. 資料契約定義

### 13.1 ModelPerformance（共用 — 引擎無關）

```python
@dataclass
class ModelPerformance:
    """模型效能指標（LightGBM 和 XGBoost 共用）"""
    
    # 核心指標
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float  # train_auc - cv_auc_mean
    
    # 校準指標
    brier_score: Optional[float] = None
    ece: Optional[float] = None
    calibration_quality: Optional[str] = None  # 'good'/'fair'/'poor'
    
    # PR 指標
    pr_auc: Optional[float] = None
    positive_rate: Optional[float] = None
    
    # 引擎 Metadata
    engine_type: Optional[str] = None  # 'lightgbm' / 'xgboost'
    training_time_seconds: Optional[float] = None
    n_estimators_actual: Optional[int] = None  # early stopping 後的實際輪數
```

### 13.2 API Request/Response（新增）

```python
# api/models/pattern_analysis_models.py — 新增

class ModelTrainingRequest(BaseModel):
    """通用模型訓練請求"""
    engine: str = Field(
        default='lightgbm',
        description="ML 引擎類型",
        pattern='^(lightgbm|xgboost)$'
    )
    data_source: str = Field(description="資料來源（CSV path 或 case search ID）")
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="引擎參數（覆蓋預設值）"
    )
    validation: Optional[ValidationConfig] = Field(
        default=None,
        description="驗證設定"
    )
    natural_language_instruction: Optional[str] = Field(
        default=None,
        description="自然語言指令（V2.0 LLM 解析）"
    )

class ValidationConfig(BaseModel):
    """驗證設定"""
    cv_folds: int = Field(default=5, ge=2, le=20)
    eval_size: float = Field(default=0.2, gt=0.0, lt=1.0)
    time_series_split: bool = True
    purge_gap: Optional[int] = Field(default=None, ge=0)
    embargo_pct: Optional[float] = Field(default=None, ge=0.0, le=0.1)
    oot_ratio: float = Field(default=0.2, gt=0.0, lt=0.5)

class ModelPerformanceResponse(BaseModel):
    """模型效能回應"""
    task_id: str
    engine: str
    performance: Dict[str, Any]
    training_time_seconds: float

class ComparisonReportResponse(BaseModel):
    """雙引擎對比報告回應"""
    task_id: str
    engines: List[str]
    performances: Dict[str, Dict[str, Any]]
    consensus_rate: float
    feature_rank_correlation: float
    recommended_engine: str
    recommendation_reason: str

class TaskStartResponse(BaseModel):
    """通用任務啟動回應（所有非同步任務共用）"""
    task_id: str
    status: str = "running"

class LightGBMTrainingRequest(BaseModel):
    """LightGBM 專用訓練請求（繼承通用欄位 + LightGBM 特有參數）"""
    data_source: str
    params: Optional[Dict[str, Any]] = None
    categorical_features: Optional[List[str]] = None  # LightGBM 原生類別特徵
    boosting_type: str = Field(default='gbdt', pattern='^(gbdt|dart)$')
    validation: Optional[ValidationConfig] = None

class LightGBMResultsResponse(BaseModel):
    """LightGBM 分析結果回應"""
    task_id: str
    engine: str = 'lightgbm'
    performance: Dict[str, Any]
    feature_importance: Optional[List[Dict[str, Any]]] = None
    shap_summary: Optional[Dict[str, Any]] = None
    calibration: Optional[Dict[str, Any]] = None
```

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Task**: **3.1**（ModelPerformance / OOTValidationResult 等共用 dataclass）、**3.7**（API Request/Response models）
> - **交付物**:
>   - 3.1: `momentum/Analysis/model_types.py`（🆕 全新 — ModelPerformance, FeatureImportance, OOTValidationResult 等核心 dataclass）
>   - 3.7: `api/models/pattern_analysis_models.py`（🔄 修改 — 新增 ModelTrainingRequest, ValidationConfig, ModelPerformanceResponse, ComparisonReportResponse, TaskStartResponse, LightGBMTrainingRequest, LightGBMResultsResponse 共 7 個 API Model）
> - **前置條件**: 無（dataclass 定義是最底層的依賴）
> - **驗收條件**: (1) ModelPerformance 可被 LGB 和 XGB 共用 (2) API Models 通過 Pydantic validation (3) DTO 不跨域（momentum 用 dataclass；api 用 BaseModel）
> - **實作要點**: §13.1 定義了 ModelPerformance 的完整欄位（核心指標 + 校準指標 + PR 指標 + 引擎 Metadata）。§13.2 定義 API Request/Response 包含 ValidationConfig 子模型。注意 Rule 7（DTO 不跨域）。

---

## 14. 實作計畫與依賴關係

### 14.1 Task 分解

| Task | 名稱 | 優先級 | 預估 | 依賴 |
|------|------|:------:|:----:|------|
| **3.1** | IModelTrainer + IOptimizationObjective Protocol 擴展 | P0 | 0.5 天 | 無 |
| **3.2** | LightGBMAnalyzer 核心實作 | P0 | 2 天 | 3.1 |
| **3.3** | XGBoostAnalyzer Protocol 適配 | P0 | 0.5 天 | 3.1 |
| **3.4** | ModelConfigManager 四維參數 | P1 | 1 天 | 無 |
| **3.5** | ModelComparison 雙引擎對比 | P1 | 1 天 | 3.2, 3.3 |
| **3.6** | Factory 函式 + Service 整合 | P0 | 0.5 天 | 3.2, 3.3 |
| **3.7** | API 端點擴展 | P1 | 0.5 天 | 3.6 |
| **3.8** | 測試套件（160+ 測試） | P0 | 1-2 天 | 3.2, 3.3, 3.5, 3.9 |
| **3.9** | Optuna 重構 — OptunaOptimizer 可插拔目標 + ModelHyperparamObjective | P1 | 1 天 | 3.1, 3.2, 3.4 |
| **3.10** | StrategyBacktestObjective + End-to-End Pipeline | P2 | 1 天 | 3.9 |

### 14.2 依賴關係圖

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 3 Task 依賴關係                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Task 3.1 (Protocol)  ─────────┬──────────── Task 3.4 (Config) │
│       │                        │                   │            │
│       ├──→ Task 3.2 (LightGBM) │                   │            │
│       │         │               │                   │            │
│       └──→ Task 3.3 (XGBoost)  │                   │            │
│                 │               │                   │            │
│       ┌─────────┤               │                   │            │
│       │         │               │                   │            │
│       ▼         ▼               │                   │            │
│  Task 3.5    Task 3.6           │                   │            │
│  (Comparison) (Factory)         │                   │            │
│       │         │               │                   │            │
│       └────┬────┘               │                   │            │
│            │                    │                   │            │
│            ▼                    │                   │            │
│       Task 3.7 (API)           │                   │            │
│                                │                   │            │
│       Task 3.9 (Optuna 重構) ←─┴───────────────────┘            │
│            │                                                    │
│            ▼                                                    │
│       Task 3.10 (策略回測)                                      │
│                                                                 │
│       Task 3.8 (Tests) ← 依賴 3.2, 3.3, 3.5, 3.9              │
│                                                                 │
│  圖例: A ──→ B 表示 B 依賴 A                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 14.3 推薦實作順序

```
Day 1:
  ├── Task 3.1: IModelTrainer + IOptimizationObjective Protocol 擴展（0.5 天）
  └── Task 3.3: XGBoostAnalyzer 新增 Protocol 方法（0.5 天）

Day 2-3:
  └── Task 3.2: LightGBMAnalyzer 完整實作（2 天）
      ├── 核心 train_model / validate_model / validate_oot
      ├── 特徵重要性（gain/split）
      ├── Precision@K / PR Metrics / Predictions
      ├── SHAP 整合（共享 SHAPAnalyzer）
      └── save_model / load_model

Day 4:
  ├── Task 3.4: ModelConfigManager 四維參數（0.5 天）
  └── Task 3.5: ModelComparison 雙引擎（0.5 天）

Day 5:
  ├── Task 3.6: Factory 函式更新（0.25 天）
  ├── Task 3.7: API 端點擴展（0.25 天）
  └── Task 3.8: 基礎測試套件（0.5 天）

Day 6-7:
  └── Task 3.8 續: 完整測試套件 + 邊界條件（1-2 天）

Day 8:
  └── Task 3.9: Optuna 重構（1 天）
      ├── IOptimizationObjective Protocol（已在 Day 1 定義）
      ├── OptunaOptimizer 重構為可插拔目標（保留所有基礎設施）
      ├── SignalDensityObjective（從原有程式碼抽取，向後相容）
      └── ModelHyperparamObjective（新增）

Day 9:
  └── Task 3.10: Strategy Backtest（1 天）
      ├── StrategyBacktestObjective（含向量化回測）
      ├── End-to-End Pipeline（Stage 1 model → Stage 2 strategy）
      └── 多目標 NSGA-II 支援
```

> 📋 **PLAN 轉換標注**
> - **章節類型**: META
> - **用途**: 此節為 PLAN 的骨架。AI Agent 應直接將 14.1 表格轉為 PLAN 的 Task 列表，14.2 轉為依賴關係，14.3 轉為排程建議。每個 Task 的詳細子步驟從對應的 IMPLEMENTATION 章節（§4-§8, §11）提取。

---

## 15. 驗收標準

### 15.1 功能驗收

| # | 驗收項 | 量化標準 | 測試方式 |
|---|---------|---------|---------|
| 1 | LightGBM 可獨立訓練 | `create_model_trainer('lightgbm')` 成功 | 單元測試 |
| 2 | XGBoost 仍可獨立訓練 | 所有現有測試仍通過 | 回歸測試 |
| 3 | 雙引擎可對比 | ComparisonReport 含 AUC 對比 | 整合測試 |
| 4 | Protocol 合規 | `isinstance(lgb, IModelTrainer)` → True | 型別測試 |
| 5 | SHAP 共享 | LGB 和 XGB 使用同一 SHAPAnalyzer | 整合測試 |
| 6 | 四維參數系統 | YAML → Dict → NL → Optuna 都能產生合法 config | 單元測試 |
| 7 | API 向後相容 | `/xgboost/*` 所有 21 端點回應不變 | 回歸測試 |
| 8 | 前端圖表不變 | LightGBM 結果可用現有 11 個圖表顯示 | 手動測試 |
| 9 | Optuna 模型調參 | `ModelHyperparamObjective` 執行 100 trials 並回傳最佳參數 | 整合測試 |
| 10 | Optuna 策略調參 | `StrategyBacktestObjective` 執行 200 trials 並產出回測結果 | 整合測試 |
| 11 | Optuna 向後相容 | `SignalDensityObjective` 產生與重構前相同的結果 | 回歸測試 |
| 12 | Optuna 端對端 | Stage 1 (model) → Stage 2 (strategy) 流水線完整執行 | 整合測試 |
| 13 | Optuna 基礎設施不受影響 | CheckpointManager / ErrorHandler / ProgressMonitor / WebSocket 在重構後依然正常運作 | 回歸測試 |

### 15.2 品質驗收

| # | 驗收項 | 量化標準 |
|---|---------|---------|
| 1 | 測試覆蓋率 | ≥ 90% (momentum/Analysis/lightgbm_analyzer.py) |
| 2 | 邊界條件覆蓋 | 100% (上述 12.1 所有項) |
| 3 | 型別提示 | 所有 public 函式有 type hints |
| 4 | 日誌標準 | INFO 關鍵步驟 + ERROR with traceback |
| 5 | 向量化 | 無 Python 迴圈處理大資料 |
| 6 | 解耦合規 | 7 條規則全部通過 (`grep -r "from api\." momentum/` → 0) |

### 15.3 效能驗收

| # | 驗收項 | 量化標準 | 環境 |
|---|---------|---------|------|
| 1 | LightGBM 訓練速度 | 1000 樣本 × 100 特徵 < 5 秒 | M1 Mac |
| 2 | XGBoost 訓練速度 | 不劣於現有（不退步） | M1 Mac |
| 3 | SHAP 計算 | 100 樣本 < 30 秒 | M1 Mac |
| 4 | 記憶體峰值 | < 4GB（16GB 機器的 25%） | M1 Mac |
| 5 | save/load 往返 | < 2 秒 | M1 Mac |

---

## 附錄 A：新增/修改檔案清單

### 新增檔案

| 檔案路徑 | 用途 | 對應 Task |
|---------|------|:---------:|
| `momentum/Analysis/lightgbm_analyzer.py` | LightGBM 主引擎 | 3.2 |
| `momentum/Analysis/model_comparison.py` | 雙引擎 A/B 對比 | 3.5 |
| `momentum/Analysis/model_config.py` | 四維參數管理 | 3.4 |
| `momentum/Analysis/model_types.py` | 共用 dataclass 定義（ModelPerformance 等） | 3.1 |
| `momentum/Optimization/objectives/__init__.py` | Optuna 目標函式套件 | 3.9 |
| `momentum/Optimization/objectives/model_hyperparam.py` | 模型超參數優化目標 | 3.9 |
| `momentum/Optimization/objectives/strategy_backtest.py` | 策略回測參數優化目標 | 3.10 |
| `momentum/Optimization/objectives/signal_density.py` | 信號密度目標（從原始碼抽取，向後相容） | 3.9 |
| `api/services/model_task_service.py` | 通用模型任務調度 | 3.6 |
| `api/services/lightgbm_task_service.py` | LightGBM 專用服務 | 3.6 |
| `config/model_config.yaml` | 模型參數配置檔 | 3.4 |
| `tests/momentum/Analysis/test_lightgbm_analyzer.py` | LightGBM 核心測試 | 3.8 |
| `tests/momentum/Analysis/test_lightgbm_edge_cases.py` | LightGBM 邊界測試 | 3.8 |
| `tests/momentum/Analysis/test_xgboost_protocol_methods.py` | XGBoost Protocol 測試 | 3.8 |
| `tests/momentum/Analysis/test_model_comparison.py` | 對比測試 | 3.8 |
| `tests/momentum/Analysis/test_model_config_manager.py` | 參數系統測試 | 3.8 |
| `tests/momentum/Analysis/test_shared_analyzers_lightgbm.py` | 共享 Analyzer 整合 | 3.8 |
| `tests/momentum/Analysis/test_model_trainer_protocol.py` | Protocol 合規性 | 3.8 |
| `tests/momentum/Optimization/test_optuna_objectives.py` | Optuna 目標函式測試 | 3.8 |
| `tests/api/test_model_api_endpoints.py` | API 端點整合測試 | 3.8 |

### 修改檔案

| 檔案路徑 | 修改內容 | 對應 Task |
|---------|---------|:---------:|
| `momentum/core/protocols.py` | 擴展 IModelTrainer（新增 6 個方法）+ 新增 IOptimizationObjective | 3.1 |
| `momentum/Analysis/xgboost_analyzer.py` | 新增 Protocol 方法（不改現有） | 3.3 |
| `momentum/Analysis/model_storage.py` | 支援 LightGBM 序列化 | 3.2 |
| `momentum/Optimization/optuna_optimizer.py` | 🔄 重構為可插拔 IOptimizationObjective 目標 | 3.9 |
| `momentum/factories.py` | 新增 `create_model_trainer()`, `create_model_comparison()`；更新 `create_optuna_optimizer()` | 3.6, 3.9 |
| `api/routes/pattern_analysis.py` | 新增 `/model/*` 和 `/lightgbm/*` 端點 | 3.7 |
| `api/services/xgboost_task_cache.py` | 擴展為 ModelTaskCache | 3.6 |
| `api/services/optimization_task_service.py` | 擴展 `task_type` 欄位支援多種優化目標 | 3.9 |
| `api/routes/optimization.py` | 擴展 `task_type` 欄位 | 3.9 |
| `api/models/pattern_analysis_models.py` | 新增 7 個 API Model（ModelTrainingRequest 等） | 3.7 |
| `requirements.txt` | 新增 `lightgbm` | 3.2 |

---

## 附錄 B：requirements.txt 更新

### M1 Mac 安裝注意事項

```bash
# LightGBM 在 M1 Mac 需要 OpenMP 支援
brew install libomp

# 然後用 pip 安裝
pip install lightgbm>=4.0.0

# 驗證安裝
python -c "import lightgbm; print(lightgbm.__version__)"

# 若遇到 OpenMP 問題，嘗試:
export LDFLAGS="-L/opt/homebrew/opt/libomp/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libomp/include"
pip install lightgbm --no-cache-dir
```

```
# 新增
lightgbm>=4.0.0            # LightGBM 主引擎

# 已有（確認版本相容）
xgboost>=2.0.0             # XGBoost 輔助引擎
shap>=0.43.0               # SHAP 解釋（同時支援 LGB + XGB）
optuna>=3.0.0              # 超參數最佳化
scikit-learn>=1.3.0        # CV, Metrics, Calibration
pandas>=2.0.0              # 資料框架
numpy>=1.24.0              # 數值計算
```

---

## 附錄 C：名詞對照表

| 英文術語 | 繁體中文 | 說明 |
|---------|---------|------|
| IModelTrainer | 模型訓練協議 | Protocol interface |
| LightGBMAnalyzer | LightGBM 分析引擎 | 主引擎實作 |
| XGBoostAnalyzer | XGBoost 分析引擎 | 輔助引擎（保留） |
| ModelComparison | 模型對比引擎 | 雙引擎 A/B |
| ModelConfigManager | 模型參數管理器 | 四維參數 |
| Purged CV | 去汙染交叉驗證 | 金融時序 CV |
| OOT | 時間外驗證 | Out-of-Time |
| PSI | 族群穩定性指數 | Population Stability Index |
| DART | Dropout 正則化 | LightGBM 防過擬合 |
| GOSS | 梯度單側抽樣 | Gradient-based One-Side Sampling |
| EFB | 互斥特徵打包 | Exclusive Feature Bundling |
| Consensus | 共識機制 | 多引擎一致預測 |
| IOptimizationObjective | 優化目標協議 | 可插拔目標函式介面 |
| ModelHyperparamObjective | 模型超參數優化目標 | 調整 LightGBM/XGBoost 超參數 |
| StrategyBacktestObjective | 策略回測優化目標 | 調整進出場策略參數 |
| SignalDensityObjective | 信號密度優化目標 | Phase 2 原有功能（向後相容） |
| Sharpe Ratio | 夏普比率 | 風險調整後報酬指標 |
| MaxDD | 最大回撤 | Maximum Drawdown |
| Pareto Frontier | 帕雷托前沿 | 多目標優化的非支配解集 |

---

**文件維護者**: Quantitative Trading System Team  
**建立日期**: 2026-02-09  
**版本歷程**:
- V1.0 (2026-02-09): 初始規格書，15 章 + 3 附錄
- V1.1 (2026-02-09): Optuna 重構設計 + SPEC→PLAN 轉換標注
- V2 (2026-02-09): 全文審查修正 — 第一輪 11 項 + 第二輪 10 項問題修復（Protocol 型別安全、ErrorAction 定義、XGBoost 路徑安全、Suggestion dataclass、§6 PLAN 方法清單修正、R6 方法列表補全、依賴圖重繪、PLAN 標注補全、§13 PLAN 新增、API Models 補定義等）

**對應主文件**: `docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` Phase 3
