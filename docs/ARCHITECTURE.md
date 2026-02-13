# 量化交易策略系統架構文檔

## 文檔版本
- **版本**: 3.1
- **最後更新**: 2026-02-13
- **狀態**: 生產中 + 持續開發（Phase 4 進行中）
- **更新內容**: 
  - v3.1 (2026-02-13): 添加回測系統架構規劃（Backtest Domain）；添加平行開發架構指南；添加架構合規檢查腳本
  - v3.0 (2026-02-08): 同步 REFACTOR_ARCHITECTURE_V4 架構變更（解耦架構、Protocol 注入、Factory 模式、KlineDataService 統一資料存取層）；更新模組清單與目錄結構；標記已完成功能
  - v2.0 (2026-01-09): 添加 Phase 3 完整架構（Optuna 優化系統、WebSocket 通訊、9 個視覺化組件）
  - v1.0 (2025-09-30): 初始版本

---

## 目錄
1. [系統概覽](#系統概覽)
2. [技術棧](#技術棧)
3. [解耦架構原則](#解耦架構原則)
4. [整體架構](#整體架構)
5. [目錄結構](#目錄結構)
6. [已實現功能](#已實現功能)
7. [待開發功能](#待開發功能)
8. [數據流設計](#數據流設計)
9. [模組詳細設計](#模組詳細設計)
10. [性能考慮](#性能考慮)
11. [安全性設計](#安全性設計)
12. [擴展性設計](#擴展性設計)

**相關文檔**:
- [平行開發架構指南](./PARALLEL_DEVELOPMENT_GUIDE.md) - 多團隊平行開發規範
- [回測系統架構設計](./BACKTEST_SYSTEM_DESIGN.md) - 回測系統完整設計文檔
- [產品願景與版本演進](./PRODUCT_VISION.md) - 系統長期演進方向
- [架構解耦規範](./REFACTOR_ARCHITECTURE_V4.md) - 7 條解耦規則詳細說明

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
- **ML 優化平台**: 使用機器學習（XGBoost）優化交易策略參數
- **研究工作流**: 支持完整的量化研究流程

### 系統目標
1. 降低策略發現門檻（無需編程知識）
2. 自動化 Pattern 識別過程
3. 提供完整的研究到實盤工作流
4. 支持多市場擴展（加密貨幣 → 台股 → 美股）

### 開發狀態總覽 (2026 Q1)
| Phase | 內容 | 狀態 |
|-------|------|------|
| Phase 1 | 案例搜索系統 + Web UI | ✅ 已完成 |
| Phase 2 | K 線下載 + 圖表系統 | ✅ 已完成 |
| Phase 3 | Optuna 優化 + 信號分析 + 視覺化 | ✅ 已完成 |
| Phase 3.5 | 特徵工程 + XGBoost + Pattern 管理 | ✅ 已完成 |
| REFACTOR V4 | 架構解耦（7 條規則、Protocol 注入、Factory 模式） | ✅ 已完成 |
| Phase 4 | Pattern 發現 + 進階分析 | 🔄 進行中 |

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
  - SHAP (模型可解釋性)
  - Optuna (參數優化)
```

### 數據存儲
```yaml
時序數據: HDF5 (K 線數據，gzip 壓縮)
結構化數據: CSV/JSON (搜索結果、案例數據)
模型存儲: Pickle (XGBoost 模型)
特徵存儲: HDF5 (特徵矩陣)
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

> 此節源自 REFACTOR_ARCHITECTURE_V4，定義系統的 7 條架構規則。

### 架構規則 (全部已通過驗證)

| 規則 | 描述 | 狀態 |
|------|------|------|
| Rule 1 | `momentum/` 不得依賴 `api/` | ✅ 0 violation |
| Rule 2 | `momentum/` 跨 Domain 不得直接 import（透過 Protocol 注入） | ✅ 0 violation |
| Rule 3 | `api/services/` 不得直接建構 `momentum/` 物件（使用 `factories.py`） | ✅ 0 violation |
| Rule 4 | `api/services/` 之間不得互相 import | ✅ 0 violation |
| Rule 5 | 不得有 Mutable global singleton | ✅ 已修復 |
| Rule 6 | 無 callback/closure bypass | ✅ 通過 |
| Rule 7 | `api/models` ↔ `momentum/core` 無互相依賴 | ✅ 通過 |

### Protocol 注入機制

`momentum/` 內跨 Domain 依賴透過 Protocol 介面解耦（`momentum/core/protocols.py`）：

```python
class IKlineReader(Protocol):
    """K 線讀取介面 — DataExtraction Domain 實作"""
    def read_klines(self, symbol, timeframe, start_time, end_time) -> pd.DataFrame: ...
    def read_klines_around_timestamp(self, symbol, timeframe, timestamp, ...) -> pd.DataFrame: ...
    def get_metadata(self, symbol, timeframe) -> dict: ...

class IIndicatorEngine(Protocol):
    """指標計算介面 — Indicators Domain 實作"""
    def calculate_indicators_from_dataframe(self, df, config) -> pd.DataFrame: ...

class IModelTrainer(Protocol):
    """模型訓練介面 — Analysis Domain 實作"""
    def train_model(self, X, y, config) -> Any: ...
```

### Factory 模式

所有 Domain 物件的建構集中在 `momentum/factories.py`：

```python
# momentum/factories.py — 涵蓋所有 Domain 的工廠函式

# ── Data ──
create_kline_storage_manager()
create_kline_download_service()
create_binance_provider()

# ── Search ──
create_momentum_data_loader()
create_case_search_engine()
create_search_configuration()
create_filter_condition()

# ── Market ──
create_market_config()

# ── Indicators ──
create_indicator_engine()

# ── Analysis ──
create_signal_density_analyzer()
create_xgboost_analyzer()
create_model_storage()
create_feature_storage()
create_feature_extractor()
create_feature_validator()
create_strategy_params()

# ── Statistics ──
create_expectancy_calculator()
create_bootstrap_estimator()
create_cross_symbol_validator()
create_regime_analyzer()

# ── Pattern ──
create_pattern_extractor()
create_pattern_storage()
create_pattern_validator()
create_pattern_rule()
create_pattern()

# ── Optimization ──
create_parameter_ranges()
create_optuna_optimizer()
create_optimization_result()

# ── Utility ──
get_data_source_values()
```

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
| Feature | K 線 HDF5 | 特徵矩陣 | HDF5 | `data_cache/features/{case_id}.h5` |
| Analysis | 特徵 HDF5 | 模型 | Pickle | `data_cache/models/{case_id}.pkl` |
| Optimization | 模型+搜尋空間 | Study/Checkpoint | SQLite+Pickle | `data/optuna_{study}.db` |

### 持續解耦要求

> **Authority**: 所有新功能開發、架構演進必須遵循本節要求，參見 [PRODUCT_VISION.md](./PRODUCT_VISION.md) 版本演進策略。

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

| 規則 | V1.0 | V2.0 擴展 | V3.0 擴展 |
|------|------|------------|------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | 必須保持 | 必須保持 |
| **Rule 2** | Domain 內用 Protocol | 擴展至 NLU Domain | 擴展至 Agent Domain |
| **Rule 3** | Service 用 Factory | 新增 `create_chat_service()` | 新增 `create_agent_orchestrator()` |
| **Rule 4** | Service 間禁止直接調用 | 必須保持 | 必須保持 |
| **Rule 5** | Config 單一來源 | 擴展至 Prompt Config | 擴展至 Policy Config |
| **Rule 6** | Test 配置隔離 | 必須保持 | 必須保持 |
| **Rule 7** | DTO 不跨層 | 必須保持 | 必須保持 |

#### 新模組開發檢查清單

**每個新 Task/Feature 開發前必須確認**：

- [ ] **依賴方向檢查**: 新模組是否依賴了不該依賴的層？
  - ❌ `momentum/` 內不可 `import api.*`
  - ❌ `api/routes/` 內不可直接 `import momentum.*.Engine()`
  - ✅ 透過 `momentum/factories.py` 建構物件
  
- [ ] **Protocol 介面設計**: 跨 Domain 依賴是否定義了 Protocol？
  - ❌ `from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer`
  - ✅ `from momentum.core.protocols import IModelTrainer`
  
- [ ] **Factory 註冊**: 新引擎是否加入 `momentum/factories.py`？
  ```python
  # ✅ 範例
  def create_new_engine(config: Optional[dict] = None) -> NewEngine:
      return NewEngine(config or {})
  ```
  
- [ ] **Config 管理**: 新配置是否加入 `momentum/core/config.py` 或 `api/core/config.py`？
  - ❌ 硬編碼在程式碼內
  - ✅ 從 Config 物件讀取
  
- [ ] **測試隔離**: 測試是否可以不啟動完整系統？
  - ❌ 測試需要 `run_api.py` 啟動後才能跑
  - ✅ 測試可直接 `pytest tests/momentum/` 執行
  
- [ ] **Artifact 契約**: 新資料格式是否記錄在 Artifact Contract Table？

#### 常見違規案例

**❌ 反模式 1: Service 直接建構引擎**
```python
# api/services/new_service.py
from momentum.Analysis.new_engine import NewEngine

class NewService:
    def __init__(self):
        self.engine = NewEngine()  # ❌ 違反 Rule 3
```

**✅ 正確做法**:
```python
# api/services/new_service.py
from momentum.core.protocols import INewEngine

class NewService:
    def __init__(self, engine: INewEngine):  # ✅ 注入 Protocol
        self.engine = engine

# api/main.py
from momentum.factories import create_new_engine
engine = create_new_engine()
service = NewService(engine=engine)
```

**❌ 反模式 2: momentum 依賴 api**
```python
# momentum/Analysis/analyzer.py
from api.core.logging import get_logger  # ❌ 違反 Rule 1

logger = get_logger(__name__)
```

**✅ 正確做法**:
```python
# momentum/Analysis/analyzer.py
from momentum.core.logging import get_logger  # ✅ 使用 momentum 內部 logging

logger = get_logger(__name__)
```

**❌ 反模式 3: 跨 Domain 直接 import**
```python
# momentum/Analysis/feature_engineer.py
from momentum.DataExtraction.kline_storage import KlineStorageManager  # ❌ 違反 Rule 2

class FeatureEngineer:
    def __init__(self):
        self.kline_storage = KlineStorageManager()
```

**✅ 正確做法**:
```python
# momentum/core/protocols.py
class IKlineReader(Protocol):
    def read_klines(...) -> pd.DataFrame: ...

# momentum/Analysis/feature_engineer.py
from momentum.core.protocols import IKlineReader

class FeatureEngineer:
    def __init__(self, kline_reader: IKlineReader):  # ✅ Protocol 注入
        self.kline_reader = kline_reader
```

#### 解耦驗證工具

**手動檢查命令**（開發過程中使用）:
```bash
# 檢查 momentum → api 的違規依賴
grep -r "from api\." momentum/
grep -r "import api\." momentum/

# 檢查 Service 直接建構違規
grep -r "= .*Engine()" api/services/
grep -r "= .*Analyzer()" api/services/

# 檢查跨 Domain 直接 import
grep -r "from momentum\.DataExtraction" momentum/Analysis/
grep -r "from momentum\.Indicators" momentum/Analysis/
```

**自動化檢查**（CI/CD 整合，未來實作）:
```bash
# 未來可加入 pre-commit hook
python scripts/check_architecture_rules.py
```

#### 文檔同步要求

**每次架構變更必須同步更新**：
1. [ARCHITECTURE.md](./ARCHITECTURE.md) - 更新 Domain 定義、Protocol 列表
2. [PRODUCT_VISION.md](./PRODUCT_VISION.md) - 如影響版本演進路徑
3. [*.PLAN.md](.) - 更新對應 Task 的 PLAN 文件
4. [.github/copilot-instructions.md](../.github/copilot-instructions.md) - 更新 AI Agent 快速參考

#### 實例：Task 1 (FeatureFactory) 解耦設計

**符合解耦原則的設計**：
- ✅ 7 層 Pipeline 每層獨立可測試（Rule 6）
- ✅ 透過 `create_feature_factory()` 建構（Rule 3）
- ✅ Config-driven，Preset 從 YAML 讀取（Rule 5）
- ✅ 不依賴 `api/` 層，純 `momentum/` 內邏輯（Rule 1）
- ✅ 跨 Domain 依賴（讀取 K 線）透過 `IKlineReader` Protocol（Rule 2）

**參見**: [Feature_Factory_PLAN.md](./Feature_Factory_PLAN.md) V7 的 decoupling 架構對齊章節

---

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
│  13 個路由模組, 85+ 端點                              │
│  case_search │ case │ chart │ chart_signals           │
│  config │ signal_analysis │ optimization              │
│  optimization_analysis │ feature_engineering          │
│  pattern_analysis │ pattern_management                │
│  ml_pipeline │ two_stage_search                       │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│             api/services/ (Business Logic)            │
│  20 個服務, 透過 factories.py 建構 Domain 物件        │
│  Services 之間不互相呼叫 (Rule 4)                     │
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
│  │Signal    │ │EMA, MACD...│  │Extractor     │      │
│  │Pattern   │ └────────────┘  │Storage       │      │
│  │SHAP      │ ┌────────────┐  │Validator     │      │
│  │Drift/PSI │ │Optimization│  └──────────────┘      │
│  │Bootstrap │ │Optuna      │                        │
│  │Regime    │ │Checkpoint  │                        │
│  └──────────┘ └────────────┘                        │
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

```
api/
├── __init__.py
├── main.py                              # FastAPI app、lifespan、router 註冊
├── core/
│   ├── config.py                        # Settings (pydantic-settings)
│   ├── logging.py                       # ColoredFormatter, get_logger()
│   └── middleware.py                    # CORS、全域例外處理
├── models/                              # Pydantic Request/Response Models
│   ├── requests.py                      # SearchConfigRequest, FilterConditionRequest
│   ├── responses.py                     # TaskStatusResponse, SearchResponse, CaseData
│   ├── response_models.py              # EnhancedCaseData (33 參數)
│   ├── case_models.py                  # CaseRecord, BatchDownloadRequest
│   ├── training_window_config.py       # TrainingWindowConfig, StrategyConfig, SignalDensityResponse
│   ├── strategy_test_models.py         # ChartSignalCalculationRequest/Response
│   ├── feature_engineering_models.py   # FeatureExtractionRequest/Response
│   ├── pattern_analysis_models.py      # XGBoost/SHAP/OOT/Drift/Regime 模型
│   └── pattern_management_models.py    # Pattern CRUD 模型
├── routes/                              # Thin Route Handlers (13 個)
│   ├── case_search.py                  # /search/* — 案例搜索 (8 endpoints)
│   ├── case.py                         # /api/v1/case/* + /api/v1/kline/* (6 endpoints)
│   ├── chart.py                        # /api/v1/chart/data (1 endpoint)
│   ├── chart_signals.py                # /api/v1/chart/signals + validate (2 endpoints)
│   ├── config.py                       # /config/* — 範本 + 系統設定 (9 endpoints)
│   ├── signal_analysis.py              # /api/v1/signal-analysis/* (2 endpoints)
│   ├── optimization.py                 # /api/v1/optimization/* — 優化核心 (8 endpoints)
│   ├── optimization_analysis.py        # /api/v1/optimization/* — 分析 (9 endpoints)
│   ├── feature_engineering.py          # /features/* (4 endpoints)
│   ├── pattern_analysis.py             # /pattern-analysis/* — XGBoost (21 endpoints)
│   ├── pattern_management.py           # /patterns/* — Pattern CRUD (8 endpoints)
│   ├── ml_pipeline.py                  # /api/v1/ml-pipeline/* (4 endpoints)
│   └── two_stage_search.py             # /two-stage/* (3 endpoints)
├── services/                            # Business Logic (20 個服務)
│   ├── kline_data_service.py           # ★ 統一 K 線資料存取層 (快取+下載)
│   ├── kline_storage_service.py        # HDF5 讀寫操作
│   ├── chart_data_service.py           # 圖表數據 + 指標計算
│   ├── chart_signal_service.py         # 策略信號計算
│   ├── batch_download_service.py       # 批量 K 線下載
│   ├── standalone_search_service.py    # 獨立搜索服務
│   ├── search_task_service.py          # 兩階段搜索任務管理
│   ├── optimization_task_service.py    # Optuna 優化任務 (Singleton)
│   ├── signal_analysis_service.py      # 信號密度分析 (Singleton)
│   ├── feature_task_service.py         # 特徵擷取任務
│   ├── xgboost_task_service.py         # XGBoost 分析任務
│   ├── xgboost_batch_service.py        # XGBoost 批量分析
│   ├── xgboost_task_cache.py           # XGBoost 結果快取
│   ├── shap_analysis_service.py        # SHAP 可解釋性分析
│   ├── case_import_service.py          # CSV/Excel 案例匯入
│   ├── case_storage.py                 # 案例記憶體存儲
│   ├── data_service.py                 # 範本 + 設定管理
│   ├── pattern_management_service.py   # Pattern CRUD 服務
│   └── task_manager.py                 # 通用任務狀態管理
├── websocket/
│   └── optimization_ws.py              # WebSocket 即時優化進度推送
└── utils/                               # 工具函式
```

### Core Engines (`momentum/`)

```
momentum/
├── __init__.py
├── factories.py                         # ★ 所有 Domain 物件工廠 (唯一建構入口)
├── core/                                # ★ 基礎設施層 (REFACTOR V4 新增)
│   ├── __init__.py
│   ├── config.py                        # MomentumConfig dataclass
│   ├── contracts.py                     # DTO/Enum (TrainingWindowConfig, StrategyConfig 等)
│   ├── logging.py                       # get_logger()
│   └── protocols.py                     # ★ IKlineReader, IIndicatorEngine, IModelTrainer
├── Analysis/                            # 分析引擎
│   ├── signal_density_analyzer.py       # SignalDensityAnalyzer
│   ├── xgboost_analyzer.py              # XGBoostAnalyzer
│   ├── shap_analyzer.py                 # SHAPAnalyzer
│   ├── prediction_analyzer.py           # PredictionAnalyzer
│   ├── model_storage.py                 # ModelStorage
│   ├── drift_analyzer.py               # DriftAnalyzer (PSI)
│   ├── regime_analyzer.py              # RegimeAnalyzer
│   ├── expectancy_calculator.py         # ExpectancyCalculator
│   ├── bootstrap_estimator.py           # BootstrapEstimator
│   ├── cross_symbol_validator.py        # CrossSymbolValidator
│   ├── calibration_analyzer.py          # CalibrationAnalyzer
│   ├── pareto_analyzer.py               # ParetoAnalyzer
│   ├── time_splitter.py                 # TimeSplitter (Train/Val/OOT)
│   ├── pattern_definition.py            # Pattern, PatternRule
│   ├── pattern_extractor.py             # PatternExtractor
│   ├── pattern_storage.py               # PatternStorage
│   ├── pattern_validator.py             # PatternValidator
│   ├── strategy_registry.py             # StrategyRegistry
│   ├── strategy_cache_registry.py       # StrategyCacheRegistry
│   ├── indicator_cache.py               # IndicatorCache
│   ├── kline_cache.py                   # KlineCache
│   └── strategies/                      # 策略子模組
│       ├── short_long_cross_strategy.py
│       ├── mid_long_cross_strategy.py
│       └── three_line_strategy.py
├── DataExtraction/                      # 數據擷取層
│   ├── case_search_engine.py            # CaseSearchEngine (30 參數框架)
│   ├── parallel_search_engine.py        # ParallelSearchEngine
│   ├── kline_storage.py                 # KlineStorageManager (HDF5)
│   ├── kline_download_service.py        # KlineDownloadService
│   ├── kline_provider_base.py           # Provider 抽象基類
│   ├── providers/
│   │   └── binance_provider.py          # BinanceProvider
│   ├── Momentum_Strategy_Data_Loader.py # MomentumDataLoader
│   ├── Market_Screener_Configuration.py # MarketConfig
│   ├── data_provider_base.py            # DataProvider 抽象基類
│   └── ...
├── FeatureEngineering/                  # 特徵工程
│   ├── feature_extractor.py             # FeatureExtractor
│   ├── feature_storage.py               # FeatureStorage (HDF5)
│   ├── feature_validator.py             # FeatureValidator
│   ├── feature_config.py
│   ├── data_source_registry.py
│   ├── ml_pipeline_config.py
│   ├── strategy_registry.py
│   └── indicators/
│       ├── ema_extractor.py
│       ├── macd_extractor.py
│       └── rsi_extractor.py
├── Indicator/                           # 純函式技術指標
│   ├── Base_Indicator_Reference.py
│   └── Advanced_MA_Reference.py
├── Indicators/                          # OOP 指標引擎
│   ├── indicator_engine.py              # IndicatorEngine (主引擎)
│   ├── base_indicator.py
│   ├── ema.py / ema_indicator.py
│   ├── config_loader.py
│   ├── data_source_manager.py
│   ├── functional_wrapper.py
│   └── types.py                         # DataSourceEnum
├── Optimization/                        # Optuna 優化系統
│   ├── optuna_optimizer.py              # OptunaOptimizer
│   ├── checkpoint_manager.py            # CheckpointManager
│   ├── progress_monitor.py              # ProgressMonitor
│   ├── result_analyzer.py               # ResultAnalyzer
│   ├── trial_comparison.py              # TrialComparison
│   ├── error_handler.py
│   └── strategy_metadata.py
└── Utils/
    └── data_validator.py                # DataValidator
```

### Frontend (`frontend/src/`)

```
frontend/src/
├── app/                                 # Next.js 15 App Router
│   ├── layout.tsx                       # 主佈局
│   ├── page.tsx                         # 首頁
│   ├── search/page.tsx                  # 案例搜索
│   ├── result/page.tsx                  # 搜索結果
│   └── optimization/page.tsx            # 優化系統
├── components/
│   ├── charts/                          # K 線圖表
│   │   ├── MultiPaneChartNew.tsx        # 多面板同步圖表 (Lightweight Charts)
│   │   └── TakerRatioChart.tsx          # Taker Ratio 圖表
│   ├── optimization/                    # 優化視覺化 (9 個組件)
│   │   ├── MetricsPanel.tsx
│   │   ├── DensityComparisonChart.tsx
│   │   ├── StabilityChart.tsx
│   │   ├── TrialHistoryTable.tsx
│   │   ├── ParameterImportanceChart.tsx
│   │   ├── ParameterDistributionChart.tsx
│   │   ├── ParallelCoordinatePlot.tsx
│   │   ├── OptimizationProgress.tsx
│   │   └── CompareTrialsTable.tsx
│   ├── search/                          # 搜索組件
│   ├── case/                            # 案例管理組件
│   └── layout/
│       └── MainLayout.tsx               # 主導航佈局
├── store/
│   ├── searchStore.ts                   # Zustand 搜索狀態
│   └── optimizationStore.ts             # Zustand 優化狀態
├── hooks/
│   └── useWebSocket.ts                  # WebSocket Hook
└── lib/
    └── types.ts                         # TypeScript 介面定義
```

### Data (`data_cache/`)
```
data_cache/
├── {SYMBOL}_{timeframe}.h5              # K 線數據 (e.g. BTCUSDT_12h.h5)
├── features/{case_id}.h5               # 特徵矩陣
└── models/{case_id}.pkl                # XGBoost 模型
```

---

## 已實現功能

### ✅ 1. Case Search 系統

#### 功能概述
完整的案例搜索系統，支持兩階段正反例搜索、多標的平行搜索。

#### 數據模型
```python
# 搜索參數（32 個）
基礎觸發條件 (6 個):
  - timeframe, price_change, closing_strength
  - price_position, volume_multiplier, taker_buy_ratio

未來表現驗證 (24 個):
  - future_1bar_return ~ future_12bar_return
  - future_1bar_max_drawdown ~ future_12bar_max_drawdown

反例專用 (2 個):
  - positive_negative_ratio, time_separation_days
```

#### 核心模組
- **搜索引擎**: `momentum/DataExtraction/case_search_engine.py`（CaseSearchEngine, SearchConfiguration, FilterCondition）
- **平行搜索**: `momentum/DataExtraction/parallel_search_engine.py`（非同步多標的併發搜索＋重試邏輯）
- **API 路由**: `api/routes/case_search.py`（8 個端點）
- **服務層**: `api/services/standalone_search_service.py`（StandaloneSearchService + TaskManager）
- **兩階段搜索**: `api/routes/two_stage_search.py`（正例搜索 → 反例搜索 → 合併結果）

#### 已實現的搜索策略
1. **條件反轉策略**: 設定與正例相反的市場條件
2. **時間分離策略**: 相同標的不同時間的隨機採樣
3. **標的內部採樣**: 確保正反例來自相同標的池
4. **兩階段搜索**: 先搜正例，再基於正例結果搜反例

---

### ✅ 2. K 線數據系統

#### KlineDataService — 統一資料存取層
> REFACTOR_ARCHITECTURE_V4 核心變更之一

`api/services/kline_data_service.py` 作為統一介面，協調快取與下載：

```python
class KlineDataService:
    def get_kline_data()          # 統一入口：先查快取，不足則下載
    def _check_cache_coverage()    # 檢查 HDF5 快取覆蓋率
    def _download_and_cache()      # 從 Binance 下載並寫入快取
    def _handle_partial_cache()    # 處理部分快取情境
    def _merge_kline_data()        # 合併快取與新下載數據
    def _validate_data_integrity() # 資料完整性驗證
```

#### KlineStorageService — HDF5 讀寫操作
```python
class KlineStorageService:
    def write_klines()                    # 寫入 K 線
    def append_klines()                   # 追加 K 線
    def read_klines()                     # 讀取指定範圍
    def read_klines_around_timestamp()    # 圍繞時間點讀取
    def check_data_integrity()            # 完整性檢查
    def get_data_quality_report()         # 品質報告
    def get_stats()                       # 統計資訊
```

#### 批量下載
- **服務**: `api/services/batch_download_service.py`
- **功能**: 平行批量 K 線下載、時間重疊偵測與合併、進度追蹤
- **API**: `POST /api/v1/kline/batch-download`、`GET /api/v1/kline/download-status/{task_id}`

---

### ✅ 3. 圖表分析系統

#### 多面板同步圖表
- **組件**: `MultiPaneChartNew.tsx`（Lightweight Charts）
- **功能**: Price / Volume / Taker Ratio 多面板、時間軸同步、CrossHair 同步

#### 策略信號標記
- **服務**: `api/services/chart_signal_service.py`（Singleton）
- **API**: `POST /api/v1/chart/signals`、`POST /api/v1/chart/validate-strategy`
- **功能**: 計算策略信號點、信號採樣、動態買入/賣出箭頭

#### 圖表數據
- **服務**: `api/services/chart_data_service.py`
- **API**: `GET /api/v1/chart/data`
- **功能**: K 線讀取、指標計算（含 warmup）、支持 TO/TC 邏輯與 center_index 舊邏輯

---

### ✅ 4. Optuna 參數優化系統

#### 優化目標函數（雙密度 v2.0 公式）
```python
Score = (μ_pos - μ_neg) - λ × (σ_pos + 0.5 × σ_neg)

其中:
- M_i = (Near_i - Far_i) / (Near_i + Far_i + ε)
- μ = Σ(w_i·M_i) / Σw_i
- σ = sqrt(Σw_i(M_i-μ)² / Σw_i)
- λ = 1.0
```

#### 支持 5 種優化器
TPESampler（預設）、CmaEsSampler、RandomSampler、GPSampler、NSGAIISampler

#### 容錯機制
- SQLite 存儲、Pickle 檢查點、3 層錯誤分類、自動重試（指數退避）

#### WebSocket 即時通訊
- **端點**: `ws://localhost:8000/ws/optimization/{task_id}?client_id=xxx`
- **管理器**: `WebSocketConnectionManager`（Singleton）
- **功能**: 即時進度推送、心跳檢測（30s ping）、按 task_id 訂閱

#### 核心模組
- **引擎**: `momentum/Optimization/optuna_optimizer.py`
- **服務**: `api/services/optimization_task_service.py`（Singleton）
- **WebSocket**: `api/websocket/optimization_ws.py`

#### API 端點（核心 + 分析共 17 個）
**核心** (`api/routes/optimization.py`):
- `POST /tasks` — 建立優化任務
- `POST /tasks/{id}/start` — 啟動任務
- `GET /tasks/{id}` — 查詢狀態
- `GET /tasks` — 列出所有任務
- `POST /tasks/{id}/cancel` — 取消
- `GET /strategies` — 列出策略
- `GET /strategies/{id}` — 策略詳情
- `GET /trials/compare` — 試驗對比

**分析** (`api/routes/optimization_analysis.py`):
- `GET /tasks/{id}/analysis/importance` — 參數重要性
- `GET /tasks/{id}/analysis/history` — 優化曲線
- `GET /tasks/{id}/analysis/param-space` — 參數空間
- `GET /tasks/{id}/analysis/heatmap` — 參數熱力圖
- `GET /tasks/{id}/analysis/convergence` — 收斂分析
- `GET /tasks/{id}/analysis/stability` — 穩定性分析
- `GET /tasks/{id}/analysis/stability-by-case-month` — 月份穩定性
- `GET /tasks/{id}/trials` — Top N trials
- `GET /tasks/{id}/result` — 完整結果

---

### ✅ 5. 優化結果視覺化系統

9 個專業圖表組件（`frontend/src/components/optimization/`）：

| 組件 | 功能 |
|------|------|
| **MetricsPanel** | 指標總覽（分數、μ 分離、σ 穩定性、p-value、Cohen's d） |
| **DensityComparisonChart** | 正反例密度對比＋月度分組 |
| **StabilityChart** | 月度分數變化＋變異係數（CV）＋趨勢線 |
| **TrialHistoryTable** | 所有試驗（排序、搜索、CSV 導出、Ctrl+A） |
| **ParameterImportanceChart** | FANOVA/MDI 參數重要性排名 |
| **ParameterDistributionChart** | 多參數散點圖＋分數顏色映射 |
| **ParallelCoordinatePlot** | 多維參數平行坐標＋高分突顯 |
| **OptimizationProgress** | 即時進度條＋WebSocket 狀態＋估計剩餘時間 |
| **CompareTrialsTable** | 多試驗並排對比＋差異高亮 |

---

### ✅ 6. 信號密度分析系統

#### 核心計算
- 雙窗口密度（Near/Far）、M-Metric v2.0
- 統計顯著性（t 檢驗、Cohen's d）
- 零值統計透明化（Far=0 排除比例）
- 樣本警告機制

#### 核心模組
- **引擎**: `momentum/Analysis/signal_density_analyzer.py`
- **服務**: `api/services/signal_analysis_service.py`（Singleton）
- **API**: `POST /api/v1/signal-analysis/density`、`POST /api/v1/signal-analysis/preview-window`

---

### ✅ 7. 多指標計算引擎

#### 數據源支持 (7 種)
close, open, high, low, volume, taker_volume, taker_ratio

#### 指標引擎
- **OOP 引擎**: `momentum/Indicators/indicator_engine.py`（IndicatorEngine — 主引擎）
- **純函式**: `momentum/Indicator/Base_Indicator_Reference.py`
- **支持指標**: EMA, SMA, DEMA, TEMA, RSI, MACD, ATR, Bollinger Bands 等
- **特性**: 向量化計算、YAML 配置、無未來函數驗證

---

### ✅ 8. 特徵工程系統

#### 功能概述
完整特徵擷取 → HDF5 存儲 → 品質驗證流程。

#### 核心模組
- **擷取**: `momentum/FeatureEngineering/feature_extractor.py`
- **存儲**: `momentum/FeatureEngineering/feature_storage.py`（HDF5）
- **驗證**: `momentum/FeatureEngineering/feature_validator.py`
- **服務**: `api/services/feature_task_service.py`
- **API**: `POST /features/extract`、`GET /features/task/{id}`、`GET /features/summary/{case_id}`、`GET /features/health`

#### 特徵指標
EMA, MACD, RSI 擷取器（`momentum/FeatureEngineering/indicators/`）— 支持多尺度窗口、序列特徵

---

### ✅ 9. XGBoost 分析系統

#### 核心能力
| 功能 | 模組 |
|------|------|
| 模型訓練（Purged CV, 多尺度窗口） | `xgboost_analyzer.py` |
| SHAP 全域/個案分析 | `shap_analyzer.py` |
| 機率密度、校準曲線、PR 曲線、滾動 AUC | `prediction_analyzer.py` |
| OOT (Out-of-Time) 驗證 | `time_splitter.py` |
| 特徵漂移 PSI | `drift_analyzer.py` |
| 市場情境分析 | `regime_analyzer.py` |
| 期望值計算 | `expectancy_calculator.py` |
| 信賴區間 | `bootstrap_estimator.py` |
| 跨標的驗證 | `cross_symbol_validator.py` |

#### 服務層
- `api/services/xgboost_task_service.py` — 單案例分析
- `api/services/xgboost_batch_service.py` — 批量分析
- `api/services/shap_analysis_service.py` — SHAP 分析

#### API 路由 (`api/routes/pattern_analysis.py` — 21 個端點)
主要端點：
- `POST /xgboost/start` — 啟動分析
- `POST /xgboost/batch/start` — 批量分析
- `POST /xgboost/validate-oot` — OOT 驗證
- `GET /xgboost/{id}/predictions` — 預測結果
- `GET /xgboost/{id}/feature-importance` — 特徵重要性
- `GET /xgboost/{id}/probability-density` — 機率密度
- `GET /xgboost/{id}/strategy-equity` — 策略權益曲線
- `GET /xgboost/{id}/rolling-auc` — 滾動 AUC
- `GET /xgboost/{id}/calibration-curve` — 校準曲線
- `GET /xgboost/{id}/pr-curve` — PR 曲線
- `POST /xgboost/{id}/shap` — SHAP 全域分析
- `GET /xgboost/{id}/shap/case/{case_id}` — 單案例 SHAP
- `GET /xgboost/{id}/drift-report` — 漂移報告
- `GET /xgboost/{id}/regime-analysis` — 情境分析

---

### ✅ 10. Pattern 管理系統

#### 功能概述
Pattern 的 CRUD 操作和統計分析。

#### 核心模組
- **定義**: `momentum/Analysis/pattern_definition.py`（Pattern, PatternRule）
- **擷取**: `momentum/Analysis/pattern_extractor.py`
- **存儲**: `momentum/Analysis/pattern_storage.py`
- **驗證**: `momentum/Analysis/pattern_validator.py`
- **服務**: `api/services/pattern_management_service.py`
- **API** (`api/routes/pattern_management.py` — 8 個端點):
  - `POST /patterns/define` — 建立 Pattern
  - `GET /patterns/list` — 列出所有
  - `GET /patterns/statistics` — 統計
  - `GET /patterns/{id}` — 詳情
  - `GET /patterns/{id}/summary` — 摘要
  - `PUT /patterns/{id}` — 更新
  - `DELETE /patterns/{id}` — 刪除
  - `DELETE /patterns/batch/delete-all` — 全部刪除

---

### ✅ 11. ML Pipeline 系統

- **API** (`api/routes/ml_pipeline.py`):
  - `POST /api/v1/ml-pipeline/create` — 從 Optuna trial 建立 pipeline
  - `GET /api/v1/ml-pipeline/{id}` — 取得詳情
  - `GET /api/v1/ml-pipeline/list` — 列出所有
  - `DELETE /api/v1/ml-pipeline/{id}` — 刪除

---

### ✅ 12. 配置管理系統

- **後端設定**: `api/core/config.py`（pydantic-settings, `.env` 載入）
- **範本管理**: `api/services/data_service.py`（TemplateManager + ConfigManager）
- **API** (`api/routes/config.py` — 9 個端點):
  - 範本: CRUD (templates)
  - 系統: `GET /config/system`、`PATCH /config/system`
  - 驗證: `GET /config/validation/symbols`
  - 統計: `GET /config/stats`

---

### ✅ 13. 案例匯入系統

- **服務**: `api/services/case_import_service.py`
- **功能**: CSV/Excel 匯入、欄位標準化、CSV Injection 防護、時間戳正規化
- **API** (`api/routes/case.py`):
  - `POST /api/v1/case/import` — 上傳匯入
  - `GET /api/v1/case/list` — 案例列表
  - `GET /api/v1/case/count` — 案例數量
  - `DELETE /api/v1/case/clear-all` — 清除全部

---

## 待開發功能

### ⏳ 1. 回測系統（優先級：🔥 高）

> **詳細設計**: 參見 [BACKTEST_SYSTEM_DESIGN.md](./BACKTEST_SYSTEM_DESIGN.md)

基於發現的 Pattern 或 ML 模型進行歷史回測驗證。

#### 架構設計（遵循解耦原則）

**模組結構**:
```
momentum/Backtest/                    # 新增 Domain（可獨立開發）
├── backtest_engine.py                # BacktestEngine（向量化回測）
├── position_manager.py               # PositionManager（部位管理）
├── trade_executor.py                 # TradeExecutor（交易執行）
├── performance_calculator.py         # PerformanceCalculator（績效計算）
├── risk_analyzer.py                  # RiskAnalyzer（風險分析）
├── report_generator.py               # ReportGenerator（報告生成）
└── types.py                          # Trade, Position, BacktestResult

api/services/
└── backtest_service.py               # BacktestService（任務管理）

api/routes/
└── backtest.py                       # REST API 路由

api/models/
└── backtest_models.py                # BacktestRequest, BacktestResponse
```

**Protocol 定義** (添加到 `momentum/core/protocols.py`):
```python
class IBacktestEngine(Protocol):
    def run_backtest(
        self, symbol, timeframe, start_date, end_date,
        strategy_params, initial_capital
    ) -> Dict: ...

class IPositionManager(Protocol):
    def open_position(...) -> Dict: ...
    def close_position(...) -> Dict: ...
    def check_stop_loss_take_profit(...) -> Optional[str]: ...

class IPerformanceCalculator(Protocol):
    def calculate_metrics(trades, equity_curve) -> Dict: ...
```

**Factory 函數** (添加到 `momentum/factories.py`):
```python
def create_backtest_engine() -> IBacktestEngine:
    kline_reader = create_kline_storage_manager()
    position_manager = create_position_manager()
    performance_calculator = create_performance_calculator()
    return BacktestEngine(
        kline_reader=kline_reader,
        position_manager=position_manager,
        performance_calculator=performance_calculator
    )
```

#### 核心功能

**1. 回測引擎**:
- 向量化交易執行（pandas/numpy）
- Numba JIT 優化關鍵路徑
- 支援多種策略類型（RSI, ML, Pattern）
- 性能目標：1年 12h 週期 < 1 秒（MacBook M1）

**2. 部位管理**:
- 開倉/平倉邏輯
- 止損止盈自動觸發
- 部位追蹤與歷史記錄

**3. 績效指標** (20+ 指標):
- **報酬**: 總報酬率、年化報酬、CAGR
- **風險**: 波動率、最大回撤、最大回撤持續期
- **風險調整**: 夏普比率、索提諾比率、卡瑪比率
- **交易**: 勝率、獲利因子、平均獲利/虧損、連續獲利/虧損

**4. 視覺化與報告**:
- 權益曲線圖表（Recharts）
- 交易記錄表格
- 績效指標面板
- PNG 匯出功能

#### 依賴關係（獨立開發）

```
回測系統依賴:
  ✅ IKlineReader (透過 Protocol) → DataExtraction
  ✅ 無其他業務邏輯依賴
  ✅ 可獨立測試: pytest tests/momentum/Backtest/
```

**與其他模組整合**:
```
[案例搜尋結果] → 策略參數 → [回測驗證]
[特徵工程] → XGBoost 預測 → [回測驗證]
[Optuna 優化] → 最佳參數 → [回測驗證]
```

#### REST API

```python
# POST /api/v1/backtest/run
{
  "symbol": "BTCUSDT",
  "timeframe": "12h",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "strategy_params": {"rsi_buy": 30, "rsi_sell": 70},
  "initial_capital": 100000.0
}

# Response
{
  "symbol": "BTCUSDT",
  "trades": [...],           # 交易記錄
  "equity_curve": [...],      # 權益曲線
  "metrics": {
    "total_return": 0.35,
    "sharpe_ratio": 1.8,
    "max_drawdown": -0.12,
    "win_rate": 0.65,
    ...
  }
}
```

#### 開發時程（可與項目1-2平行）

- Phase 1: 基礎架構（1-2天） — Protocol + Factory + 空類別
- Phase 2: 核心邏輯（3-5天） — Python 循環版本回測
- Phase 3: 性能優化（2-3天） — 向量化 + Numba JIT
- Phase 4: API 整合（2-3天） — REST API + Pydantic Models
- Phase 5: 前端整合（1-2週，待項目1-3完成後） — 圖表 + 報告

**總計**: 後端 8-13 天，前端 7-10 天（等 API 穩定後）

#### 平行開發可行性分析

✅ **可平行開發**，理由：
1. 新增模組，不修改現有程式碼
2. 遵循 Protocol 注入，無違規依賴
3. 使用 Factory 模式統一創建
4. 可獨立測試，無需完整系統啟動
5. API 合約可先定義，前端用 Mock 開發

---

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
- ✅ XGBoost
- ⏳ LightGBM, LSTM, Transformer（未來）

---

## 相關文檔

| 文檔 | 說明 |
|------|------|
| `docs/API_SPECIFICATION.md` | API 端點規格（85+ 端點） |
| `docs/DEVELOPMENT_GUIDE.md` | 開發規範（Ultra Think 3 步驟） |
| `docs/FEATURE_ROADMAP.md` | 功能路線圖 |
| `docs/REFACTOR_ARCHITECTURE_V4.md` | 架構重構記錄（10 個 Phase） |
| `docs/KLINE_DATA_SPECIFICATION.md` | HDF5 數據格式規範 |
| `.github/copilot-instructions.md` | AI Agent 指令 |

---

*文檔版本：3.0*  
*最後更新：2026-02-08*  
*狀態：REFACTOR_ARCHITECTURE_V4 同步完成*
