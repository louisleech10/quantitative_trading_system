# 量化交易策略系統架構文檔

> ⚠️ 治理制度(協作/派工/gate)以 `CLAUDE.md` 與 `docs/MULTI_AGENT_ORCHESTRATION.md` 為準;本檔最後驗證 2026-07-05,其後細節可能過時。

## 文檔版本
- **版本**: 7.0
- **最後更新**: 2026-05-25
- **狀態**: 生產中 + 持續開發
- **更新內容**:
  - v7.0 (2026-05-25): 同步 Feature Factory Granular Control（per-indicator 細粒度控制、Preset API、Batch-Toggle API）；L6.5 優化系列（native-tf path -45.4%、d_star cache v3、Numba Fast ADF、joblib 並行化）；L7 storage 增強（sharded npy、hardware-adaptive 壓縮、IC-First raw/ cleanup）；IC engine cache hit path；Feature Browser CGSA 優化；per-indicator warmup lookup；FeatureTimeSeriesChart 重構
  - v6.1 (2026-05-07): 修正 Feature Storage artifact 描述（HDF5 legacy → V7 per-group parquet）；新增 L65 V2 IC-First canonical path（`{SYMBOL}/{TF}/{config_hash}/raw|processed`）；同步 Artifact Contract Table 與目錄樹
  - v6.0 (2026-03-15): 同步 Feature Factory MultiTF 整合 + 多標的批次計算 — MultiTF 路由策略、AlignmentMode paradigm、FeatureFactoryBatchService 架構（ProcessPoolExecutor + TTL 清理）
  - v5.0 (2026-02-18): 同步全部已完成 PLAN — Phase 1 Feature Factory（7 層 Pipeline）、Phase 1.5 Feature Factory 優化（微觀結構/資訊理論/尾部風險引擎 + Layer 6.5 前處理）、Phase 2.4-2.12 IC Deep Analysis（10 個深度分析模組 + 特徵難度分級 + 匯出系統 + 資料瀏覽器）、Phase 3.5 模型增強（6 個增強模組：校準/Walk-Forward/樣本加權/對抗驗證/CPCV/學習曲線）、Phase 4 Optuna 重構 + Strategy Domain（VectorizedBacktest + PerformanceMetrics + PositionSizing + RiskManager + IBacktestEngine/IPositionSizer Protocol）
  - v4.0 (2026-02-14): 新增 Phase 3.7 雙引擎 ML 系統架構（LightGBM + XGBoost、IModelTrainer Protocol 擴展、IOptimizationObjective、模型對比系統、四維參數系統、可插拔 Optuna 目標）
  - v3.0 (2026-02-08): 同步 REFACTOR_ARCHITECTURE_V4 架構變更（解耦架構、Protocol 注入、Factory 模式、KlineDataService 統一資料存取層）；更新模組清單與目錄結構；標記已完成功能
  - v2.0 (2026-01-09): 添加 Phase 3 完整架構（Optuna 優化系統、WebSocket 通訊、9 個視覺化組件）
  - v1.0 (2025-09-30): 初始版本

---

## 目錄
1. [系統概覽](#系統概覽)
2. [技術棧](#技術棧)
3. [解耦架構原則](#解耦架構原則)
4. [Feature Factory 架構](#feature-factory-架構)
5. [整體架構](#整體架構)
6. [目錄結構](#目錄結構)
7. [已實現功能](#已實現功能)
8. [待開發功能](#待開發功能)
9. [數據流設計](#數據流設計)
10. [模組詳細設計](#模組詳細設計)
11. [性能考慮](#性能考慮)
12. [安全性設計](#安全性設計)
13. [擴展性設計](#擴展性設計)

---

## 系統概覽

### 系統定位
**量化研究工作平台（Quantitative Research Platform）**

與傳統量化交易系統的差異：
```
傳統量化: 已知策略 → 優化參數 → 回測 → 實盤
本系統:   探索案例 → 發現Pattern → 驗證策略 → ML優化 → 回測 → (未來)實盤
```

### 核心價值
- **案例發現引擎**: 從歷史數據中找出符合特定模式的交易案例
- **Pattern 識別系統**: 自動發現起漲前的共通技術指標特徵
- **ML 優化平台**: 使用機器學習（XGBoost + LightGBM 雙引擎）優化交易策略參數
- **研究工作流**: 支持完整的量化研究流程

### 系統目標
1. 降低策略發現門檻（無需編程知識）
2. 自動化 Pattern 識別過程
3. 提供完整的研究到實盤工作流
4. 支持多市場擴展（加密貨幣 → 台股 → 美股）

### 開發狀態總覽（各 Phase 里程碑;最後校對 2026-07-12。近期進度以 `HANDOFF.md` / `docs/ROADMAP.md` 為準）
| Phase | 內容 | 狀態 |
|-------|------|------|
| Phase 1 | 案例搜索系統 + Web UI | ✅ 已完成 |
| Phase 2 (K線圖表) | K 線下載 + 圖表系統 | ✅ 已完成 |
| Phase 2 (IC Gatekeeper) | IC 特徵篩選 + 模型驗證 | ✅ 已完成 |
| Phase 3 | Optuna 優化 + 信號分析 + 視覺化 | ✅ 已完成 |
| Phase 3.5 | 特徵工程 + XGBoost + Pattern 管理 | ✅ 已完成 |
| Phase 3.5 | 模型增強系統（校準、Walk-Forward、對抗驗證、CPCV、學習曲線） | ✅ 已完成 |
| Phase 3.7 | 雙引擎 ML 系統 (LightGBM + XGBoost) | ✅ 已完成 |
| REFACTOR V4 | 架構解耦（7 條規則、Protocol 注入、Factory 模式） | ✅ 已完成 |
| Phase 4 | Optuna 重構 + Strategy Domain（回測引擎、績效指標、部位管理） | ✅ 已完成 |
| Phase 1 (Feature Factory) | 7 層特徵工程 Pipeline + Config 驅動 + 七段式命名 | ✅ 已完成 |
| Phase 1.5 (Feature Factory 優化) | 微觀結構/資訊理論/尾部風險引擎 + Layer 6.5 前處理 | ✅ 已完成 |
| Phase 2.4-2.12 (IC Deep Analysis) | 10 個深度分析模組 + 特徵難度分級 + 匯出系統 | ✅ 已完成 |
| Feature Factory MultiTF + Batch | MultiTF 路由、AlignmentMode、多標的批次計算服務 | ✅ 已完成 |
| Feature Factory Granular Control | Per-indicator 細粒度控制 + Preset + Batch-Toggle API + 前端元件 | ✅ 已完成 |
| L6.5 優化系列 | native-tf path（-45.4%）+ d_star cache v3 + Numba ADF + joblib 並行 | ✅ 已完成 |
| L7 Storage 增強 | Sharded npy + hardware-adaptive 壓縮 + IC-First raw/ cleanup | ✅ 已完成 |
| IC Engine | Cache hit path（raw/ 刪除後複用 IC scores） | ✅ 已完成 |
| Feature Browser | CGSA stats 優化（sampling quantile + parallel warmup） | ✅ 已完成 |

---

## 技術棧

### 前端技術
```yaml
框架: Next.js 15 (App Router)
語言: TypeScript 5.x
樣式: Tailwind CSS 3.x
狀態管理: Zustand
圖表庫:
  - Lightweight Charts (TradingView 開源) - K 線圖表
  - Recharts - Dashboard 統計圖表
組件庫: shadcn/ui
HTTP 客戶端: Fetch API
WebSocket: 原生 WebSocket API
```

### 後端技術
```yaml
框架: FastAPI 0.100+
語言: Python 3.11
數據處理:
  - pandas 2.0+ (數據分析)
  - numpy 1.24+ (數值計算)
技術指標:
  - pandas-ta (技術指標庫)
  - 自建 IndicatorEngine (OOP 指標引擎)
API 交互:
  - python-binance (幣安 API)
機器學習:
  - XGBoost (分類模型)
  - LightGBM 4.0+ (雙引擎訓練)
  - SHAP (模型可解釋性)
  - Optuna (參數優化、可插拔目標函式)
```

### 數據存儲
```yaml
時序數據: HDF5 (K 線數據，gzip 壓縮)
結構化數據: CSV/JSON (搜索結果、案例數據)
模型存儲: Pickle (XGBoost/LightGBM 模型)
特徵存儲: |
  V7 per-group Parquet (L7 特徵矩陣，AsyncParquetCompactor，IC-First 雙路徑)
    L7_raw:       data_cache/features/{SYMBOL}/{TF}/{config_hash}/raw/{group_id}.parquet
    L7_processed: data_cache/features/{SYMBOL}/{TF}/{config_hash}/processed/{group_id}.parquet
    IC 選擇清單:  data_cache/features/{SYMBOL}/{TF}/{config_hash}/ic_selected_features_{SYMBOL}_{TF}.json
    Manifest:     data_cache/features/{SYMBOL}/{TF}/{config_hash}/feature_manifest.json
  HDF5 legacy (FeatureStorage.save_factory_output，向後相容)
    legacy:       data_cache/features/{symbol}_{timeframe}_factory.h5
優化記錄: SQLite (Optuna Study)
緩存: 內存緩存 (搜索結果臨時存儲)
```

### 開發環境
```yaml
硬件: MacBook M1
Python 版本: 3.11+ (M1 原生支持)
Node 版本: 18+
包管理:
  - Python: pip + requirements.txt
  - Node: npm
版本控制: Git + GitHub
IDE: VS Code
```

---

## 解耦架構原則

> **規範權威**:7 條解耦規則的 canonical 定義**唯一住在 `CLAUDE.md` §The 7 Decoupling Rules**;本節僅為架構視角的重述與現況佐證,如與 CLAUDE.md 有出入,以 CLAUDE.md 為準。
> 此節源自 REFACTOR_ARCHITECTURE_V4。歷史上本表 Rule 5/6 曾誤寫為 singleton/callback(與 canonical 的 Config/Test 不符),已於 docdrift(2026-07-12)改正——singleton/callback 降為獨立 named invariant Rule 8/9(見下)。

### 架構規則(canonical,與 CLAUDE.md 同步)

| 規則 | 描述 | 現況 |
|------|------|------|
| Rule 1 | `momentum/` 不得依賴 `api/` | ✅ 0 violation(`grep "from api\." momentum/`==0) |
| Rule 2 | `momentum/` 跨 Domain 不得直接 import（透過 Protocol 注入） | ⚠️ **`check_decoupling.sh` 報 5 筆**:`momentum/Analysis/*` 直接 import `momentum/FeatureEngineering`(warmup_lookup/consumer_gate/feature_reader);phase4 窄查(僅 strategy_backtest)通過。是否屬真違規或該豁免共用工具,待 triage(見 ROADMAP P2) |
| Rule 3 | `api/services/` 不得直接建構 `momentum/` 物件（使用 `factories.py`） | ⚠️ **`check_decoupling.sh` 報 12 筆**:api/services、api/routes 直接 import `momentum/FeatureEngineering` 具體工具(run_locks/run_paths/hardware_utils/feature_reader…)未走 factory;待 triage(見 ROADMAP P2) |
| Rule 4 | `api/services/` 之間不得互相 import | ⚠️ **1 已知違規**:`feature_factory_batch_adapters.py:9` import `feature_factory_service`(feature-explorer 系列引入,`check_decoupling.sh` 紅;待修/另立債票) |
| Rule 5 | **Config 單一來源**（`momentum/core/config.py` 或 `api/core/config.py`；momentum 不得 import `api.core.config`） | ✅ scanner 綠 |
| Rule 6 | **測試不依賴 `run_api.py`**（`pytest tests/momentum/` 可獨立跑） | ✅ `check_decoupling_phase4.sh` 綠(**註**:phase4 僅實跑 `tests/momentum/Strategy/` 子集=135 passed,非全 `tests/momentum/`;full 覆蓋未機械強制) |
| Rule 7 | `api/models` ↔ `momentum/core` 無互相依賴 | ✅ 0 violation |

**具名不變式(named invariants;非「7 條」之一,獨立追蹤,詳見 CLAUDE.md)**:

| 不變式 | 描述 | 現況(誠實) |
|--------|------|-----------|
| Rule 8 | 不得有 Mutable global singleton | ⚠️ **仍有殘留**:`chart_signal_service.py`/`signal_analysis_service.py`/`data_source_registry.py` 等 `_instance` singleton 尚在,列技術債追蹤(勿宣稱「已修復」) |
| Rule 9 | 無跨界 callback/closure/lambda monkeypatch bypass | ✅ 由 `check_decoupling.sh` lambda 檢查強制(該腳本內部標「Rule 6」=此不變式) |

> **兩支 scanner 編號語意不同**:`check_decoupling.sh` 的「Rule 5」=Config(canonical R5)、「Rule 6」=callback bypass(=Rule 9);`check_decoupling_phase4.sh` 的「Rule 6」=獨立 pytest(canonical R6)。canonical 編號以 CLAUDE.md 為準。

### Protocol 注入機制

- **INV-B-ARCH-01 Protocol權威指向protocols.py**：跨 Domain 依賴以 `momentum/core/protocols.py` 的 Protocol 注入；介面清單與簽名只以該檔為準，可用 `rg -n '^class I.*\(Protocol\)' momentum/core/protocols.py` 重生。

### Factory 模式

- **INV-B-ARCH-02 Factory權威指向factories.py**：Domain 物件由 `momentum/factories.py` 集中建構；工廠清單與簽名只以該檔為準，可用 `rg -n '^def (create_|get_)' momentum/factories.py` 重生。

### 呼叫流程

```
API Route (thin handler)
    │
    ▼
api/services/ (business logic)
    │
    │ 透過 momentum/factories.py 建構物件
    ▼
momentum/ Domain 物件 (pure logic)
    │
    │ 跨 Domain 透過 Protocol 注入
    ▼
Data Layer (HDF5 / API / SQLite)
```

### Artifact Contract Table

| Domain | 輸入 | 輸出 | 格式 | 路徑 |
|--------|------|------|------|------|
| Data | Binance API | K 線資料 | HDF5 | `data_cache/{SYMBOL}_{timeframe}.h5` |
| Data | SearchConfig | 搜尋結果 | JSON | `search_results/{task_id}.json` |
| Feature (legacy) | K 線 HDF5 | 特徵矩陣 | HDF5 | `data_cache/features/{symbol}_{timeframe}_factory.h5` |
| Feature L7_raw (V7) | K 線 → L6.5_pre winsorize | 全量 winsorized 特徵 | Parquet per-group | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/raw/{group_id}.parquet` |
| Feature L7_processed (V7) | L7_raw → IC Gate → L6.5_post | IC 篩選後 rank/zscore 特徵 | Parquet per-group | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/processed/{group_id}.parquet` |
| Feature IC Selection (V7) | L7_raw IC 分析 | 選中特徵清單 + metadata | JSON | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/ic_selected_features_{SYMBOL}_{TF}.json` |
| Feature Manifest (V7) | 全 group 完成 | schema_hash + complete flag | JSON | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/feature_manifest.json` |
| Analysis | 特徵 Parquet/HDF5 | 模型 | Pickle | `data_cache/models/{case_id}.pkl` |
| Optimization | 模型+搜尋空間 | Study/Checkpoint | SQLite+Pickle | `data/optuna_{study}.db` |

### 持續解耦要求

- **INV-B-ARCH-09 持續解耦指向PRODUCT_VISION**：所有新功能與架構演進遵循 `CLAUDE.md` canonical 規則；版本演進理由與方向參見 [PRODUCT_VISION.md](./PRODUCT_VISION.md)。

#### 為何需要持續解耦？

**系統演進目標**（參見 [PRODUCT_VISION.md](./PRODUCT_VISION.md)）：
```
V1.0（當前）: 手動 UI 操作
V2.0（2026 Q3-Q4）: Chat 自然語言介面
V3.0（2027+）: 全自主 AI Agent
```

每個版本演進都需要：
- ✅ **不影響既有版本**（V2.0 不能破壞 V1.0 的 REST API）
- ✅ **可獨立測試**（新增 Chat 功能不應需要完整系統啟動）
- ✅ **可獨立部署**（未來可能分離 Agent 服務到獨立容器）

#### 解耦規則適用範圍

- **INV-B-ARCH-03 解耦規則適用所有版本**：`CLAUDE.md` 的 canonical Rule 1–7 同時約束 V1、V2 與 V3；新增 NLU／Agent Domain、Prompt／Policy Config 或 factory 時不得改變依賴方向。

#### 新模組開發檢查清單

- **INV-B-ARCH-04 新模組依canonical checklist**：依 `CLAUDE.md` 逐項確認依賴方向、Protocol、Factory、Config 單一來源、測試隔離與 DTO 邊界；新增資料格式另須更新本節 Artifact Contract Table。

#### 常見違規案例

- **INV-B-ARCH-05 違規案例保留一組**：反例是 service 直接建構 concrete engine；正例是 service 依賴 `momentum/core/protocols.py` 的 Protocol，並由 composition root 呼叫 `momentum/factories.py` 注入實作。

#### 解耦驗證工具

- **INV-B-ARCH-06 scanner命令可重生**：完整驗證入口為 `bash scripts/check_decoupling.sh` 與 `bash scripts/check_decoupling_phase4.sh`；兩支 scanner 的編號語意差以上方原樣留說明為準。

#### 文檔同步要求

- **INV-B-ARCH-07 架構變更同步canonical**：架構變更同步更新本檔與相關 PLAN；若影響版本演進則更新 `PRODUCT_VISION.md`，若影響治理規則則以 `CLAUDE.md` canonical 為唯一修改入口。

#### 實例：Task 1 (FeatureFactory) 解耦設計

- **INV-B-ARCH-08 FeatureFactory案例指向專節**：Feature Factory 的解耦與跨層契約見 [Feature Factory 架構](#feature-factory-架構)；canonical Rule 1–7 仍以 `CLAUDE.md` 為準。

---

## Feature Factory 架構

本節只定義跨層、跨時間框架與跨版本必須穩定的契約；具體模組 inventory 仍由原始碼重生。

### L6.5 與 artifact 契約

- `d_star` 快取鍵必須是每一欄實際數值的 fingerprint，不得以 index hash 代替；native-tf 路徑會讓非主時間框架 group 在 source TF 原生列上完成 L6.5（包含 fracdiff/ADF 與 per-column value fingerprint 的 `d_star`），其 cache 以 source TF 隔離、不與主 TF 共用鍵，再依 `idx_map` 對齊展開至主 TF；禁止先展開成 step-function 再做 ADF/fracdiff，以免估計偏置。
- 增量生成預設只補齊缺少或失效的 artifact；`force_regenerate` 明確要求忽略既有可用結果並重新生成，不得被當成一般 cache hit。
- 資料順序固定為 L6.5_pre winsorize → L7_raw → IC Gate → L6.5_post rank/zscore → L7_processed。原因是 IC 必須評估 winsorized、但尚未經 post-IC 轉換的完整候選集合，避免篩選結果受到後處理污染。格式、canonical path 與 manifest 細節以 [Artifact Contract Table](#artifact-contract-table) 為準。

### Schema 與相容性契約

- 完整層序固定為 Layer 0 數據標準化 → L1 原子指標 → L2 衍生特徵（Distance/Cross/Divergence）→ L3 Rolling 統計 → L4 Lag 延遲 → L5 多時間框架 → L6 元特徵（Trend Consensus/Volatility Regime）→ L6.5 前處理 → L7 Label；L6.5 的前後段位置另受上節 artifact 順序約束。
- 特徵名稱遵循七段式文法 `{source}_{timeframe}_{category}_{indicator}_{params}_{operator}_{window}`；欄位名稱同時是下游選取、cache 與既有 artifact 的 schema，因此擴充引擎只能依此文法加入穩定 prefix，不得任意改名破壞相容性。三個 Phase 1.5 引擎的 concrete prefix 是 Microstructure `ms_`、Entropy `ent_`、Tail Risk `tr_`，屬輸出 schema 相容契約。
- Granular Control 的 `IndicatorDef.enabled` 是 per-indicator 開關 schema；`migrate_config()` 必須把舊版 config 遷移成等價的新格式，維持既有設定語意。每個 indicator 依自己的 warmup period 計算有效起點，並保留 warmup 導致的 NaN 修復契約，不得用單一全域假設掩蓋不同指標需求。

### MultiTF 時間可得性契約

- 每個時間框架先在自己的 bar 序列獨立完成特徵計算，再對齊至主時間框架；不得先重採樣到主時間框架後計算，以免使用當時尚不可得的資料。
- `AlignmentMode.OPEN_MINUS` 以「下一根 bar 的 open」作為上一根已完成 bar 的可得邊界；`AlignmentMode.CLOSE_TIME` 只在低頻 bar 收盤後才允許高頻列取得該低頻特徵。兩種模式都必須維持 point-in-time 可得性，禁止 look-ahead。

### Optimization pointer

Optuna objective 的可調權重值只以 `momentum/Optimization/optuna_optimizer.py` 的實作為準；公式結構與量綱契約見 CAP-04。

## 整體架構

### 系統層級架構

```
┌──────────────────────────────────────────────────────┐
│                 Frontend (Next.js 15)                 │
│         Zustand Store + React Components             │
│  ┌──────────┐┌──────────┐┌──────────┐┌──────────┐   │
│  │案例搜索  ││圖表分析  ││優化系統  ││XGBoost   │   │
│  │界面      ││界面      ││界面      ││儀表板    │   │
│  └────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘   │
└───────┼───────────┼───────────┼───────────┼──────────┘
        │           │           │           │
    HTTP/WS     HTTP        HTTP/WS      HTTP
        │           │           │           │
┌───────▼───────────▼───────────▼───────────▼──────────┐
│              api/routes/ (Thin Handlers)              │
│  25 個路由模組, 130+ 端點                            │
│  case_search │ case │ chart │ chart_signals           │
│  config │ signal_analysis │ optimization              │
│  optimization_analysis │ feature_engineering          │
│  pattern_analysis │ pattern_management                │
│  ml_pipeline │ two_stage_search                       │
│  model_enhancement │ hyperparameter_optimization     │
│  execution_optimization                               │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│             api/services/ (Business Logic)            │
│  28+ 個服務, 透過 factories.py 建構 Domain 物件       │
│  Services 之間不互相呼叫 (Rule 4;現有 1 已知違規待修)  │
│                                                      │
│  KlineDataService ─── 統一 K 線存取 (快取+下載)       │
│  ChartDataService ─── 圖表數據 + 指標計算             │
│  OptimizationTaskService ── Optuna 優化管理           │
│  XGBoostTaskService ── XGBoost 分析管理               │
│  FeatureTaskService ── 特徵擷取管理                   │
│  SearchTaskService ── 兩階段搜索                      │
│  SignalAnalysisService ── 信號密度分析                 │
│  PatternManagementService ── Pattern CRUD             │
│  SHAPAnalysisService ── SHAP 可解釋性                 │
│  BatchDownloadService ── 批量 K 線下載                │
│  CaseImportService ── CSV/Excel 案例匯入              │
│  ...                                                 │
└───────────────────────┬──────────────────────────────┘
                        │ factories.py
┌───────────────────────▼──────────────────────────────┐
│           momentum/ (Core Domain Logic)              │
│  ┌─────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ core/   │ │factories.py  │ │DataExtraction│      │
│  │protocols│ │(唯一建構入口) │ │CaseSearch    │      │
│  │contracts│ │              │ │KlineStorage  │      │
│  │config   │ └──────────────┘ │ParallelSearch│      │
│  └─────────┘                  │Binance       │      │
│  ┌──────────┐ ┌────────────┐  └──────────────┘      │
│  │Analysis/ │ │Indicators/ │  ┌──────────────┐      │
│  │XGBoost   │ │Engine(OOP) │  │FeatureEng/   │      │
│  │LightGBM  │ │EMA, MACD...│  │Factory(7層)  │      │
│  │Signal    │ └────────────┘  │Extractor     │      │
│  │Pattern   │ ┌────────────┐  │Storage       │      │
│  │SHAP      │ │Optimization│  │Validator     │      │
│  │Drift/PSI │ │Optuna      │  └──────────────┘      │
│  │Bootstrap │ │Checkpoint  │  ┌──────────────┐      │
│  │DeepAnaly │ │Objectives/ │  │★ Strategy/   │      │
│  │ModelEnhc │ └────────────┘  │Backtest      │      │
│  │Regime    │                 │Metrics       │      │
│  └──────────┘                 └──────────────┘      │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                   Data Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ HDF5     │ │ Binance  │ │ SQLite   │             │
│  │(K線/特徵)│ │ API      │ │ (Optuna) │             │
│  └──────────┘ └──────────┘ └──────────┘             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ Pickle   │ │ JSON/CSV │ │ Memory   │             │
│  │ (模型)   │ │(搜索結果)│ │ (快取)   │             │
│  └──────────┘ └──────────┘ └──────────┘             │
└──────────────────────────────────────────────────────┘
```

---

## 目錄結構

### Backend (`api/`)

負責 FastAPI 邊界、request/response DTO、薄 route handler、業務服務與 WebSocket 協調。關鍵入口是 `api/main.py`；本地啟動入口是頂層 `run_api.py`。

### Core Engines (`momentum/`)

負責資料擷取、特徵工程、分析、優化與回測等 Domain Logic。跨域物件統一由 `momentum/factories.py` 建構，跨域介面定義於 `momentum/core/protocols.py`。

### Frontend (`frontend/src/`)

負責 Next.js App Router 頁面、視覺元件、Zustand 狀態、hooks 與 typed API client；頁面入口位於 `frontend/src/app/`，共用 API 型別位於 `frontend/src/lib/types.ts`。

### Data (`data_cache/`)

`data_cache/` 是本地市場數據與特徵 artifact 層，由對應的 storage/service 路徑管理生命週期。快取必須依 symbol/timeframe 隔離，禁止 fake data 與跨標的污染，且不得 commit。

完整目錄樹以 repo 為準，可在對應 domain 以 `find` 重新生成。

## 已實現功能

本節是能力與穩定契約索引，不是完成度快照。即時狀態只以 [HANDOFF](../HANDOFF.md) 與 [ROADMAP](./ROADMAP.md) 為準；端點與 schema 以 [API 規格](./API_SPECIFICATION.md) 為準。

| 能力 | 狀態(pointer→HANDOFF/ROADMAP) | 主要 module | API(→API_SPEC 穩定 H2) | 前端(→code) |
|---|---|---|---|---|
| **CAP-01 Case Search**<br>契約：正例、反例與未來表現 workflow；`SearchConfig` 保留 6 類觸發、24 類未來表現、2 類反例參數 taxonomy，並依時間切分防洩漏。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/DataExtraction/case_search_engine.py` | [Case Search](./API_SPECIFICATION.md#1-case-search-api) | `frontend/src/app/case-search/` |
| **CAP-02 K 線數據**<br>契約：cache-first、缺口下載、symbol/timeframe 隔離；HDF5 schema 相容、重疊 merge 與 failure 語意；批次平行並追蹤進度。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `api/services/kline_*_service.py` | [Case Management（Kline batch）](./API_SPECIFICATION.md#2-case-management-api) | `frontend/src/` |
| **CAP-03 圖表分析**<br>契約：信號服務負責動態買賣箭頭；圖表 response/schema 由 API 規格維護。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `api/services/chart_*_service.py` | [Signals](./API_SPECIFICATION.md#4-chart-signals-api)、[Data](./API_SPECIFICATION.md#3-chart-data-api) | `frontend/src/components/charts/` |
| **CAP-04 Optuna 優化**<br>契約：雙密度 `Score = (μ_pos - μ_neg) - λ×(σ_pos + 0.5×σ_neg)`，其中案例 i 的 `M_i = (Near_i - Far_i) / (Near_i + Far_i + ε)`，`Near_i`/`Far_i` 分別為近／遠期信號密度，μ/σ 為正反例各自的加權均值／離散度。密度比、M、μ、σ、λ 與 Score 均為無量綱，使正反例分離與穩定性懲罰可相減；λ 的調參值只以 `momentum/Optimization/optuna_optimizer.py` 為準。objective 方向、版本相容及 pruning/retry/exception 分類保留。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Optimization/` | [Core](./API_SPECIFICATION.md#7-optimization-api-core)、[Analysis](./API_SPECIFICATION.md#8-optimization-analysis-api)、[WS](./API_SPECIFICATION.md#websocket-api) | `frontend/src/components/optimization/` |
| **CAP-05 優化視覺化**<br>契約：參數重要性、歷史、平行座標、等高線、試驗與分布由 code inventory 實現。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `api/routes/optimization_analysis.py` | [Optimization Analysis](./API_SPECIFICATION.md#8-optimization-analysis-api) | `frontend/src/components/optimization/` |
| **CAP-06 信號密度**<br>契約：正反例密度定義、分數量綱及 engine/service ownership 保留。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/` | [Signal Analysis](./API_SPECIFICATION.md#6-signal-analysis-api) | `frontend/src/` |
| **CAP-07 多指標引擎**<br>契約：指標不得使用未來資料；來源 inventory 以 config/code 為準。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Indicators/` | — | `frontend/src/` |
| **CAP-08 特徵工程**<br>契約：IC-First 使用 `L7_raw + L7_processed`；V2 path 分離 `raw/processed`，legacy HDF5 向後相容。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/FeatureEngineering/` | [Feature Engineering](./API_SPECIFICATION.md#9-feature-engineering-api) | `frontend/src/components/feature-factory/` |
| **CAP-09 XGBoost**<br>契約：Purged CV、OOT、PSI 與跨標的驗證共同維持防洩漏及時間可得性。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/xgboost_analyzer.py` | [Pattern Analysis](./API_SPECIFICATION.md#10-pattern-analysis-api-xgboost--lightgbm) | `frontend/src/components/pattern/` |
| **CAP-10 Pattern 管理**<br>契約：definition→extract→validate→store lifecycle 留在 domain；CRUD schema 由 API 規格維護。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/pattern_*` | [Pattern Management](./API_SPECIFICATION.md#11-pattern-management-api) | `frontend/src/components/pattern/` |
| **CAP-11 ML Pipeline**<br>契約：訓練→時間序列驗證→報告順序固定，train/validation/test 不混用。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/` | [Pattern Analysis](./API_SPECIFICATION.md#10-pattern-analysis-api-xgboost--lightgbm) | `frontend/src/components/pattern/` |
| **CAP-12 配置管理**<br>契約：Config 單一來源與 precedence 以 [CLAUDE.md](../CLAUDE.md#the-7-decoupling-rules-zero-tolerance) Rule 5 為準。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/core/config.py`、`api/core/config.py` | — | `frontend/src/` |
| **CAP-13 案例匯入**<br>契約：匯入 schema、驗證與 retryable/non-retryable failure 分類保留；無效資料不得靜默寫入。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `api/services/case_import_service.py` | [Case Management](./API_SPECIFICATION.md#2-case-management-api) | `frontend/src/` |
| **CAP-14 IC Gatekeeper**<br>契約：Stage 0–7 固定為 ingestion→preprocessing→labels→events→IC→statistical（含 monotonicity）→redundancy→report；配置為 `Default < YAML < API Override`。Pearson/Spearman/robust、OOT/CV gap/PSI 的適用語意保留；redundancy 依配置選 Greedy/Hierarchical/VIF 與其 correlation/linkage/VIF threshold 語意，Diversification 是篩後互補性指標；refilter 不得污染資料邊界。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/ic_filter_orchestrator.py` | [IC Analysis](./API_SPECIFICATION.md#14-ic-analysis-api) | `frontend/src/{app,components}/ic-analysis/` |
| **CAP-15 雙引擎 ML**<br>契約：XGBoost/LightGBM 經 `IModelTrainer` 並維持相容；`IOptimizationObjective` 隔離目標，ModelComparison 負責 A/B 與共識 lifecycle。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/{xgboost_analyzer,lightgbm_analyzer,model_comparison}.py` | [Dual-Engine ML](./API_SPECIFICATION.md#15-dual-engine-ml-api-phase-37) | `frontend/src/components/pattern/` |
| **CAP-16 Feature Factory**<br>契約：七段式 schema、`IndicatorDef.enabled`、`migrate_config()`、per-indicator warmup/NaN、增量與 `force_regenerate` 見 [Feature Factory 架構](#feature-factory-架構)。native-tf 在 source TF 原生列完成 L6.5（含 fracdiff/ADF），`d_star` 用 per-column value fingerprint 且依 source TF 隔離，再對齊主 TF；不得沿用主 TF 的 `d_star`。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/FeatureEngineering/`、`momentum/factories.py` | [Granular Control](./API_SPECIFICATION.md#19-feature-factory-granular-control-api) | `frontend/src/components/feature-factory/` |
| **CAP-17 IC 深度分析**<br>契約：factor return、centrality、trend、sensitivity、rolling OOS、orthogonalization、exposure、long/short、quality diagnostics、Net IC 各有 ownership；skipped/failure 與輸出 schema 相容，成本/OOS 保持量綱及時間語意。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/` | [IC Analysis](./API_SPECIFICATION.md#14-ic-analysis-api) | `frontend/src/components/ic-analysis/` |
| **CAP-18 模型增強**<br>契約：校準、Walk-Forward、sample weighting、adversarial validation、CPCV、learning curve 共享 validation lifecycle；purge/embargo 與分布檢查不得洩漏。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/` | [Model Enhancement](./API_SPECIFICATION.md#16-model-enhancement-api-phase-35) | `frontend/src/` |
| **CAP-19 Strategy 回測與優化**<br>契約：signal→execution→metrics 固定；risk/position sizing 維持量綱；`IBacktestEngine`/`IPositionSizer` 是 domain 邊界，objective plug-in 向後相容。API_SPEC/runtime prefix 既有漂移不在此宣稱一致。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Strategy/`、`momentum/Optimization/objectives/` | [Hyperparameter](./API_SPECIFICATION.md#17-hyperparameter-optimization-api-phase-4)、[Execution](./API_SPECIFICATION.md#18-execution-optimization-api-phase-4)、[WS](./API_SPECIFICATION.md#websocket-api) | `frontend/src/components/optimization/` |
| **CAP-20 MultiTF + Batch**<br>契約：各 TF 先在自身 bar 計算，再依 `OPEN_MINUS`/`CLOSE_TIME` 可得時間對齊，禁止 look-ahead。Batch 管理 concurrency、TTL、per-symbol failure isolation；cache 不跨 symbol。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/FeatureEngineering/`、`api/services/feature_factory_batch_service.py` | [MultiTF + Batch](./API_SPECIFICATION.md#20-feature-factory-multitf--batch-api)、[WS](./API_SPECIFICATION.md#websocket-api) | `frontend/src/components/feature-factory/` |
| **CAP-21 L7 Storage**<br>契約：raw shard 串流、per-part 寫前磁碟檢查；tier 決定壓縮但維持跨 tier repeatability。IC 完成後才 cleanup，failure 隔離至 part。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/FeatureEngineering/` | — | `frontend/src/components/feature-factory/` |
| **CAP-22 IC Cache Hit**<br>契約：raw cleanup 後可複用 IC scores；cache miss 才重算，不得將缺 raw 當可用或跨 symbol 複用。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `momentum/Analysis/` | [IC Analysis](./API_SPECIFICATION.md#14-ic-analysis-api) | `frontend/src/components/ic-analysis/` |
| **CAP-23 Feature Browser CGSA**<br>契約：stats sampling quantile、冷快取 parallel warmup、首次同步上限 500；這些屬 CGSA/冷快取 lifecycle。 | [HANDOFF](../HANDOFF.md) / [ROADMAP](./ROADMAP.md) | `api/services/` | — | `frontend/src/components/feature-factory/` |

### Manifest disposition mapping

合併規則：每個 child ID 明列於其父能力；`K`=留（進該 CAP 列或 [Feature Factory 架構](#feature-factory-架構)）、`D`=刪（依 manifest 命令可重生）、`M`=外移（本表 API 欄保留目的章 pointer）。

<!-- A1.1-MAPPING
CAP-01 K:01,01-OV,01-MODEL,01-MODEL-CODE,01-STRAT D:01-MODULE
CAP-02 K:02,02-ACCESS,02-STORAGE,02-BATCH,02-BATCH-LIFECYCLE D:02-ACCESS-CODE,02-STORAGE-CODE M:02-BATCH-API
CAP-03 K:03,03-SIGNAL D:03-PANEL M:03-DATA
CAP-04 K:04,04-OBJ,04-OBJ-CODE,04-FAIL D:04-OPT,04-MOD M:04-WS,04-API
CAP-05 K:05 D:05-TABLE
CAP-06 K:06,06-CALC,06-MOD
CAP-07 K:07,07-ENGINE D:07-SOURCE
CAP-08 K:08,08-OV,08-MOD D:08-IND
CAP-09 K:09,09-CORE,09-CORE-TABLE D:09-SVC M:09-API
CAP-10 K:10,10-OV,10-MOD D:10-MOD-CORE M:10-MOD-API
CAP-11 K:11
CAP-12 K:12
CAP-13 K:13
CAP-14 K:14,14-OV,14-MOD,14-MOD-T1,14-MOD-T2,14-PIPE,14-PIPE-CODE,14-IC,14-IC-TABLE,14-RED,14-RED-TABLE,14-ARCH,14-ARCH-CODE2 D:14-MOD-T4,14-TEST,14-TEST-TABLE,14-ARCH-CODE1,14-PERF,14-TODO M:14-MOD-T3
CAP-15 K:15,15-ARCH,15-CORE,15-CORE-TABLE D:15-ARCH-CODE,15-FE,15-FE-TABLE,15-TEST M:15-API,15-API-TABLE
CAP-16 K:16,16-OV,16-LAYERS,16-LAYERS-TABLE,16-EXT,16-EXT-TABLE,16-L65,16-L65-TABLE,16-GRAN,16-GRAN-ENGINE,16-ARCH D:16-CORE,16-GRAN-FE,16-GRAN-TEST M:16-GRAN-API
CAP-17 K:17,17-OV,17-MOD,17-MOD-TABLE,17-OTHER
CAP-18 K:18,18-OV,18-CORE,18-CORE-TABLE D:18-FE M:18-API
CAP-19 K:19,19-OV,19-CORE,19-CORE-TABLE,19-PROTO,19-PROTO-CODE,19-OPTUNA M:19-API,19-WS
CAP-20 K:20,20-OV,20-ROUTE,20-ROUTE-CODE,20-ALIGN,20-ALIGN-TABLE,20-ALIGN-CODE,20-BATCH,20-BATCH-CODE D:20-TEST M:20-API,20-API-TABLE
CAP-21 K:21,21-SHARD,21-TIER,21-TIER-TABLE,21-CLEAN
CAP-22 K:22
CAP-23 K:23,23-CGSA D:23-CHART
-->

---

## 待開發功能

> ⚠️ 本清單為概略優先序,可能落後實際進度;個別功能真實狀態以 `HANDOFF.md` / `docs/ROADMAP.md` 與原始碼為準。

### ⏳ 1. 前端 UI 整合（優先級：🔥 高）

各系統前端視覺化頁面開發與整合：
- IC Deep Analysis 前端互動面板
- Model Enhancement 前端儀表板
- Strategy 回測結果視覺化
- Feature Factory 管理介面 / Feature Explorer(**部分已建**,feature-explorer 系列 commit;整合與品質彙整持續中)

### ⏳ 2. 實盤部署（優先級：🟡 低）

策略部署到雲端、實時監控、自動執行交易。

---

## 數據流設計

### 完整數據流向

```
1️⃣ 案例搜索
   搜索條件 → CaseSearchEngine → ParallelSearchEngine → 案例列表 (CSV/JSON)

2️⃣ 案例匯入
   CSV/Excel → CaseImportService → 案例記憶體存儲 → 批量 K 線下載

3️⃣ K 線下載
   案例列表 → KlineDataService (快取優先) → HDF5
   ※ 不足時透過 BinanceProvider 下載並寫入快取

4️⃣ 圖表分析
   HDF5 → ChartDataService → IndicatorEngine → 多面板圖表
   用戶選策略 → ChartSignalService → 信號箭頭標記

5️⃣ 信號密度分析
   策略配置 → SignalDensityAnalyzer → 密度統計 + M-Metric

6️⃣ 參數優化
   參數空間 → OptunaOptimizer → 最佳參數 + Trial 分析
   WebSocket → 即時進度推送 → 前端 9 個視覺化組件

7️⃣ 特徵工程
   K 線 HDF5 → FeatureExtractor → 特徵矩陣 HDF5

8️⃣ XGBoost 訓練與分析
   特徵矩陣 → XGBoostAnalyzer → 模型 (Pickle)
   → SHAP 可解釋性 / OOT 驗證 / 漂移分析 / 情境分析

9️⃣ Pattern 管理
   分析結果 → PatternStorage → CRUD → 統計與摘要

🔟 Feature Factory 特徵生成
   Config (scan_config.yaml) → FeatureFactory 7 層 Pipeline → 特徵矩陣 HDF5
   ※ 支持微觀結構/資訊理論/尾部風險三大擴充引擎

1️⃣1️⃣ MultiTF 特徵批次生成
   BatchGenerateRequest (1–200 標的) → FeatureFactoryBatchService (ProcessPoolExecutor)
   → 對每標的發出 FeatureFactory.generate_features()
   → MultiTFGenerator 計算外加 TF，依 AlignmentMode 對齊
   → 結果儲存至 HDF5，WebSocket 推送進度

1️⃣1️⃣ IC 深度分析
   IC Gatekeeper 結果 → 10 個深度分析模組 → 因子報酬/趨勢/OOS/正交化等報告

1️⃣2️⃣ 模型增強
   訓練完成模型 → 6 個增強模組 → 校準/Walk-Forward/對抗驗證/CPCV/學習曲線

1️⃣3️⃣ 策略回測
   信號 + K 線資料 → VectorizedBacktest → 績效指標 (Sharpe/Sortino/Calmar/MaxDD/SQN)
   → PositionSizer (Kelly/Fixed/機率加權)
   → RiskManager (SL/TP/Trailing Stop)
```

---

## 模組詳細設計

### 關鍵服務類別

#### KlineDataService — 統一 K 線存取
```python
# api/services/kline_data_service.py
class KlineDataService:
    """統一 K 線資料介面，協調快取（HDF5）與下載（Binance API）"""
    def get_kline_data(self, symbol, timeframe, start_time, end_time):
        # 1. 檢查快取覆蓋率
        # 2. 不足時下載並寫入快取
        # 3. 合併數據
        # 4. 驗證完整性
        pass
```

#### OptimizationTaskService — Optuna 任務管理
```python
# api/services/optimization_task_service.py (Singleton)
class OptimizationTaskService:
    def create_task(config) → task_id
    def start_task(task_id) → asyncio.Task
    def cancel_task(task_id)
    # 透過 WebSocket callback 推送進度
```

#### XGBoostTaskService — XGBoost 分析
```python
# api/services/xgboost_task_service.py
class XGBoostTaskService:
    def start_xgboost_analysis_task(request) → task_id
    # 背景執行：特徵載入 → 模型訓練 → 結果快取
```

---

## 性能考慮

### M1 優化策略

**優化層級** (從最佳到最差):
1. **向量化 pandas/numpy** — 優先使用 `df.rolling()`, `np.where()`, `pd.merge()`
2. **Numba JIT** — 無法避免的數值迴圈
3. **Async/multiprocessing** — I/O 密集或平行搜索
4. **Python 迴圈** — 最後手段，需先 profiling

### 數據緩存策略
- **HDF5 gzip 壓縮**: 減少磁碟 I/O
- **KlineDataService 快取優先**: 先查本地 HDF5，不足再下載
- **記憶體快取**: IndicatorCache, KlineCache, StrategyCacheRegistry

---

## 安全性設計

### API 密鑰管理
- `.env` 環境變量（`BINANCE_API_KEY`, `BINANCE_SECRET_KEY`）
- `pydantic-settings` 自動載入

### 資料安全
- CSV Import 防 Injection 攻擊（`_sanitize_csv_injection`）
- API 輸入驗證（全部透過 Pydantic Models）
- 錯誤分類避免洩漏內部堆疊資訊

---

## 擴展性設計

### 多市場支持
透過 `DataProvider` / `KlineProviderBase` 抽象基類：
- ✅ `BinanceProvider` — 幣安加密貨幣
- ⏳ 台股、美股 Provider（未來）

### 策略類型擴展
透過 `StrategyRegistry` 動態註冊：
- ✅ Short-Long Cross, Mid-Long Cross, Three-Line
- ⏳ 更多策略可透過 YAML 配置新增

### 機器學習模型擴展
透過 `IModelTrainer` Protocol：
- ✅ XGBoost（8 個 Protocol 方法、向後相容）
- ✅ LightGBM（8 個 Protocol 方法、Phase 3.7 完成）
- ✅ 雙引擎對比（ModelComparison、推薦引擎、共識率）
- ✅ 四維參數系統（YAML/Dict/NL/Optuna）
- ✅ 可插拔 Optuna 目標（IOptimizationObjective Protocol）
- ✅ 模型增強（6 個模組：校準/Walk-Forward/樣本加權/對抗驗證/CPCV/學習曲線）
- ⏳ LSTM, Transformer（未來）

### 回測系統擴展
透過 `IBacktestEngine` + `IPositionSizer` Protocol：
- ✅ VectorizedBacktest（向量化回測、SL/TP/Trailing Stop）
- ✅ PerformanceMetrics（12+ 指標）
- ✅ 3 種部位管理（Kelly/Fixed/機率加權）
- ⏳ Event-Driven Backtest（未來）

---

## 相關文檔

| 文檔 | 說明 |
|------|------|
| `docs/API_SPECIFICATION.md` | API 端點規格（100+ 端點） |
| `docs/DEVELOPMENT_GUIDE.md` | 開發規範 |
| `docs/REFACTOR_ARCHITECTURE_V4.md` | 架構重構記錄（10 個 Phase）— 歷史參考 |
| `docs/FRONTEND_INTEGRATION_GUIDE.md` | 前端整合指南（Phase 3-6 UI） |
| `docs/DYNAMIC_INDICATOR_SYSTEM_GUIDE.md` | 動態指標系統指南（Legacy，已被 Feature Factory 取代） |
| `CLAUDE.md` | Claude Code AI 協作指令 |

---

*文檔版本：7.0*  
*最後更新：2026-05-25*  
*狀態：Phase 1-4 + Feature Factory（MultiTF/Batch/Granular Control）+ L6.5/L7 優化系列全部完成*
