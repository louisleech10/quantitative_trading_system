# 量化交易策略系統架構文檔

## 文檔版本
- **版本**: 6.0
- **最後更新**: 2026-03-15
- **狀態**: 生產中 + 持續開發
- **更新內容**: 
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
4. [整體架構](#整體架構)
5. [目錄結構](#目錄結構)
6. [已實現功能](#已實現功能)
7. [待開發功能](#待開發功能)
8. [數據流設計](#數據流設計)
9. [模組詳細設計](#模組詳細設計)
10. [性能考慮](#性能考慮)
11. [安全性設計](#安全性設計)
12. [擴展性設計](#擴展性設計)

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

### 開發狀態總覽 (2026 Q1)
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
    """模型訓練介面 — Analysis Domain 實作（XGBoost + LightGBM）"""
    def train_model(self, X, y, config) -> Any: ...
    def predict_proba(self, features) -> Any: ...
    def get_feature_importance(self, method, top_n) -> Any: ...
    def save_model(self, path) -> None: ...
    def load_model(self, path) -> None: ...
    def get_model_type(self) -> str: ...
    def get_model_params(self) -> Dict[str, Any]: ...
    def get_native_model(self) -> Any: ...

class IOptimizationObjective(Protocol):
    """可插拔優化目標介面 — Optimization Domain 實作"""
    @property
    def name(self) -> str: ...
    @property
    def direction(self) -> str: ...
    def create_search_space(self, trial) -> Dict[str, Any]: ...
    def evaluate(self, params) -> float: ...

class IBacktestEngine(Protocol):
    """回測引擎介面 — Strategy Domain 實作（Phase 4）"""
    def run_backtest(self, signals, kline_data, config) -> Any: ...
    def get_performance_metrics(self) -> Dict[str, float]: ...

class IPositionSizer(Protocol):
    """部位管理介面 — Strategy Domain 實作（Phase 4）"""
    def calculate_position_size(self, signal, equity, risk_params) -> float: ...
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
create_lightgbm_analyzer()       # Phase 3.7 新增
create_model_trainer()           # Phase 3.7 新增（通用引擎建構）
create_model_comparison()        # Phase 3.7 新增
create_model_config_manager()    # Phase 3.7 新增

# ── IC Gatekeeper ──
create_ic_analyzer()             # Phase 2

# ── IC Deep Analysis（Phase 2.4-2.12）──
create_factor_return_analyzer()
create_factor_centrality_analyzer()
create_trend_analyzer()
create_parameter_sensitivity_analyzer()
create_rolling_oos_validator()
create_factor_orthogonalizer()
create_factor_exposure_analyzer()
create_long_short_analyzer()
create_feature_quality_diagnostics()
create_net_ic_analyzer()

# ── Model Enhancement（Phase 3.5）──
create_probability_calibrator()
create_walk_forward_validator()
create_sample_weight_calculator()
create_adversarial_validator()
create_combinatorial_purged_cv()
create_learning_curve_analyzer()

# ── Feature Factory（Phase 1）──
create_feature_factory()

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

# ── Strategy（Phase 4）──
create_backtest_engine()
create_position_sizer()

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
│   ├── ★ feature_factory_models.py      # ★ Feature Factory 模型（Phase 1）
│   ├── ★ feature_browser_models.py      # ★ Feature Browser 模型
│   ├── ★ feature_toggle_models.py       # ★ Feature Toggle 模型
│   ├── ★ export_models.py               # ★ 匯出模型
│   ├── pattern_analysis_models.py      # XGBoost/SHAP/OOT/Drift/Regime 模型
│   ├── pattern_management_models.py    # Pattern CRUD 模型
│   ├── ★ ic_models.py                  # ★ ICAnalysisRequest/Response（IC 配置 + 結果）
│   ├── ★ model_enhancement.py          # ★ Model Enhancement Request/Response（Phase 3.5）
│   └── ★ optimization_models.py        # ★ Hyperparameter/Execution Optimization 模型（Phase 4）
├── routes/                              # Thin Route Handlers (25 個)
│   ├── case_search.py                  # /search/* — 案例搜索 (8 endpoints)
│   ├── case.py                         # /api/v1/case/* + /api/v1/kline/* (6 endpoints)
│   ├── chart.py                        # /api/v1/chart/data (1 endpoint)
│   ├── chart_signals.py                # /api/v1/chart/signals + validate (2 endpoints)
│   ├── config.py                       # /config/* — 範本 + 系統設定 (9 endpoints)
│   ├── cross_symbol.py                 # /api/v1/cross-symbol/* — 跨標的訓練
│   ├── signal_analysis.py              # /api/v1/signal-analysis/* (2 endpoints)
│   ├── optimization.py                 # /api/v1/optimization/* — 優化核心 (8 endpoints)
│   ├── optimization_analysis.py        # /api/v1/optimization/* — 分析 (9 endpoints)
│   ├── feature_engineering.py          # /features/* (4 endpoints)
│   ├── ★ feature_factory.py             # ★ /api/v1/feature-factory/* （Phase 1）
│   ├── ★ feature_browser.py             # ★ /api/v1/feature-browser/* （Phase 2.12）
│   ├── feature_data.py                 # /api/v1/feature-data/* — 特徵數據
│   ├── feature_registry.py             # /api/v1/feature-registry/* — 特徵註冊
│   ├── ★ feature_toggles.py             # ★ /api/v1/feature-toggles/*
│   ├── ★ export.py                      # ★ /api/v1/export/*
│   ├── pattern_analysis.py             # /pattern-analysis/* — XGBoost (21 endpoints)
│   ├── pattern_management.py           # /patterns/* — Pattern CRUD (8 endpoints)
│   ├── ml_pipeline.py                  # /api/v1/ml-pipeline/* (4 endpoints)
│   ├── two_stage_search.py             # /two-stage/* (3 endpoints)
│   ├── watchlist.py                    # /api/v1/watchlist/* — 自選清單
│   ├── ★ ic_analysis.py                # ★ /api/v1/ic-analysis/* — IC Gatekeeper (13 endpoints)
│   ├── ★ model_enhancement.py          # ★ /api/v1/model-enhancement/* — 模型增強（Phase 3.5, 8 endpoints）
│   ├── ★ hyperparameter_optimization.py # ★ 超參數優化（Phase 4）
│   └── ★ execution_optimization.py      # ★ 執行優化（Phase 4）
├── services/                            # Business Logic (33 個服務)
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
│   ├── ★ feature_factory_service.py    # ★ Feature Factory 服務（Phase 1）
│   ├── ★ feature_browser_service.py    # ★ 特徵瀏覽服務（Phase 2.12）
│   ├── ★ feature_export_service.py     # ★ 特徵匯出服務
│   ├── ★ feature_toggle_service.py     # ★ Feature Toggle 服務
│   ├── ★ export_service.py             # ★ 通用匯出服務
│   ├── xgboost_task_service.py         # XGBoost 分析任務
│   ├── xgboost_batch_service.py        # XGBoost 批量分析
│   ├── xgboost_task_cache.py           # XGBoost 結果快取
│   ├── shap_analysis_service.py        # SHAP 可解釋性分析
│   ├── case_import_service.py          # CSV/Excel 案例匯入
│   ├── case_storage.py                 # 案例記憶體存儲
│   ├── data_service.py                 # 範本 + 設定管理
│   ├── pattern_management_service.py   # Pattern CRUD 服務
│   ├── task_manager.py                 # 通用任務狀態管理
│   ├── ★ ic_analysis_service.py        # ★ IC 分析任務服務（使用 Factory 建構）
│   ├── ★ model_enhancement_service.py  # ★ 模型增強服務（Phase 3.5, 6 模組平行執行）
│   ├── ★ model_task_service.py         # ★ 模型任務服務
│   ├── ★ optimization_output_service.py # ★ 優化輸出服務（Phase 4, JSON/CSV/HTML/AI 報告）
│   ├── cross_symbol_training_service.py # 跨標的 ML 訓練
│   ├── feature_factory_batch_service.py # Feature Factory 批次處理
│   ├── feature_kline_service.py        # 特徵 K 線數據服務
│   ├── lstm_task_service.py            # LSTM 模型訓練任務
│   └── watchlist_service.py            # 自選清單管理
├── websocket/
│   ├── optimization_ws.py              # WebSocket 即時優化進度推送
│   ├── ★ ic_analysis_ws.py             # ★ IC 分析實時進度推送（八階段狀態）
│   └── ★ feature_factory_ws.py         # ★ Feature Factory 實時進度推送
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
│   └── protocols.py                     # ★ IKlineReader, IIndicatorEngine, IModelTrainer, IBacktestEngine, IPositionSizer
├── Analysis/                            # 分析引擎
│   ├── signal_density_analyzer.py       # SignalDensityAnalyzer
│   ├── xgboost_analyzer.py              # XGBoostAnalyzer
│   ├── lightgbm_analyzer.py             # LightGBMAnalyzer (Phase 3.7)
│   ├── model_comparison.py              # ModelComparison 雙引擎對比 (Phase 3.7)
│   ├── model_config.py                  # ModelConfigManager 四維參數 (Phase 3.7)
│   ├── model_types.py                   # 共用 dataclass (Phase 3.7)
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
│   ├── strategies/                      # 策略子模組
│   │   ├── short_long_cross_strategy.py
│   │   ├── mid_long_cross_strategy.py
│   │   └── three_line_strategy.py
│   │
│   ├── ★ IC Gatekeeper 系統（Phase 2）  # ★ 12 個核心模組 + 5 個驗證模組
│   ├── data_preprocessor.py            # Winsorization + 缺失值填補 + 標準化 (265 行)
│   ├── ic_engine.py                    # Rolling IC + ICIR + IC Decay + Grouped IC (720 行)
│   ├── ic_filter_orchestrator.py       # 八階段管線協調器 (1,087 行)
│   ├── event_filter.py                 # Query/Timestamp 事件篩選 + 樣本分層 (289 行)
│   ├── statistical_validator.py        # t-test + p-value + 信賴區間 + FDR (166 行)
│   ├── monotonicity_tester.py          # 分位數報酬 + 單調性分數 (244 行)
│   ├── redundancy_filter.py            # Greedy/Hierarchical/VIF/Diversification (410 行)
│   ├── turnover_analyzer.py            # 換手率 + 排名變化率 + 自相關 (92 行)
│   ├── coverage_analyzer.py            # 時間覆蓋率 + 有效起點偵測 (92 行)
│   ├── ic_config_schema.py             # Pydantic 配置模型 + 三層合併 (349 行)
│   ├── ic_reporter.py                  # JSON/Markdown/HDF5/AI 摘要 (364 行)
│   ├── exceptions.py                   # InsufficientDataError 等錯誤定義 (13 行)
│   ├── ★ IC Deep Analysis（Phase 2.4-2.12）# ★ 10 個深度分析模組
│   ├── factor_return_analyzer.py       # 因子報酬分析
│   ├── factor_centrality_analyzer.py   # PCA 因子中心性
│   ├── trend_analyzer.py               # 趨勢分析（IC/Centrality/FactorReturn/LS-Spread）
│   ├── parameter_sensitivity_analyzer.py # 參數敏感度分析
│   ├── rolling_oos_validator.py        # 滾動 OOS 驗證
│   ├── factor_orthogonalizer.py        # 因子正交化（Gram-Schmidt/PCA）
│   ├── factor_exposure_analyzer.py     # 因子曝露與歸因
│   ├── long_short_analyzer.py          # 多空分離分析
│   ├── feature_quality_diagnostics.py  # ADF/Ljung-Box/CUSUM/PSI/Coverage 診斷
│   ├── net_ic_analyzer.py              # Net IC / 交易成本分析
│   ├── deep_analysis_types.py          # 共用型別（SkippedResult, DeepAnalysisReport）
│   ├── ★ Model Enhancement（Phase 3.5）  # ★ 6 個模型增強模組
│   ├── probability_calibrator.py       # 機率校準（Platt/Isotonic/Beta/Venn-ABERS）
│   ├── sample_weight_calculator.py     # 樣本加權（time_decay/class_balance/return_based/uniqueness）
│   ├── adversarial_validator.py        # 對抗驗證（分布測試 + KS/PSI + 洩漏偵測）
│   ├── learning_curve_analyzer.py      # 學習曲線（data/feature curves + bias-variance）
│   └── model_validation/               # ★ 模型驗證子系統（5 個 + 2 個新增模組）
│       ├── cv_validator.py             # 時間序列交叉驗證 + OOT 切分 (255 行)
│       ├── oot_validator.py            # Out-of-Time 驗證 + Gap 評估 (156 行)
│       ├── psi_calculator.py           # PSI 漂移監控 + 穩定性分類 (121 行)
│       ├── rolling_auc.py              # 滾動 AUC 追蹤 + 趨勢偵測 (148 行)
│       ├── case_shap.py                # 單案例 SHAP 解釋 + 批次分析 (115 行)
│       ├── walk_forward_validator.py   # Walk-Forward 驗證（Rolling/Expanding）（Phase 3.5）
│       └── combinatorial_purged_cv.py  # CPCV（López de Prado）（Phase 3.5）
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
│   ├── ★ feature_factory.py             # ★ FeatureFactory 7 層 Pipeline（Phase 1）
│   ├── ★ config_manager.py              # ★ ConfigManager YAML 讀取（Phase 1）
│   ├── atomic/                          # ★ Layer 1 原子引擎（Phase 1 + 1.5）
│   │   ├── ta_lib_engine.py             # TA-Lib 指標引擎
│   │   ├── microstructure_engine.py     # ★ 微觀結構引擎（Phase 1.5）
│   │   ├── entropy_engine.py            # ★ 資訊理論引擎（Phase 1.5）
│   │   └── tail_risk_engine.py          # ★ 尾部風險引擎（Phase 1.5）
│   ├── preprocessing/                   # ★ Layer 6.5 前處理層（Phase 1.5）
│   │   └── feature_preprocessor.py      # rank/gaussian/zscore/diff/fracdiff
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
│   ├── optuna_optimizer.py              # OptunaOptimizer (可插拔目標)
│   ├── checkpoint_manager.py            # CheckpointManager
│   ├── progress_monitor.py              # ProgressMonitor
│   ├── result_analyzer.py               # ResultAnalyzer
│   ├── trial_comparison.py              # TrialComparison
│   ├── error_handler.py
│   ├── strategy_metadata.py
│   └── objectives/                      # Phase 3.7 可插拔目標函式
│       ├── __init__.py
│       ├── model_hyperparam.py          # 模型超參數優化目標（Phase 4 增強：過擬合偵測）
│       ├── signal_density.py            # 信號密度目標（從主優化器抽取）
│       └── strategy_backtest.py         # 策略回測目標（Phase 4 增強：9 參數搜索空間 + 約束剪枝）
├── ★ Strategy/                          # ★ 策略回測 Domain（Phase 4 新增）
│   ├── vectorized_backtest.py           # VectorizedBacktest（信號生成 + 交易執行 + SL/TP/Trailing Stop）
│   ├── performance_metrics.py           # PerformanceMetrics（12+ 指標：Sharpe/Sortino/Calmar/MaxDD/SQN 等）
│   ├── position_sizing.py              # KellyPositionSizer / FixedPositionSizer / ProbabilityScaledSizer
│   └── risk_manager.py                 # RiskManager（SL/TP/Trailing 計算）
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
│   ├── chart/page.tsx                   # 圖表分析
│   ├── ic-analysis/page.tsx             # IC 深度分析
│   ├── feature-factory/page.tsx         # Feature Factory
│   ├── feature-browser/page.tsx         # 特徵瀏覽器
│   ├── optimization-execution/page.tsx  # 執行優化
│   ├── optimization-hyperparameter/page.tsx # 超參數優化
│   ├── optimization-result/page.tsx     # 優化結果
│   ├── patterns/page.tsx                # Pattern 管理
│   ├── strategy-test/page.tsx           # 策略測試
│   ├── strategy-demo/page.tsx           # 策略展示
│   └── data-preparation/page.tsx        # 資料準備
├── components/
│   ├── charts/                          # 圖表組件
│   │   ├── PriceChart.tsx               # K 線價格圖表
│   │   ├── TakerRatioChart.tsx          # Taker Ratio 圖表
│   │   ├── TradingChartWithSignals.tsx  # 信號標記交易圖表
│   │   ├── DensityDistributionChart.tsx # 密度分布圖
│   │   ├── StrategySignalChart.tsx      # 策略信號圖
│   │   ├── VolumeChart.tsx              # 成交量圖表
│   │   └── CombinedDensityBoxplot.tsx   # 密度箱型圖
│   ├── optimization/                    # Optuna 優化 UI
│   │   ├── TrialComparisonPanel.tsx     # 試驗對比面板
│   │   ├── CalibrationPlot.tsx          # 校準圖
│   │   ├── WalkForwardTimeline.tsx      # Walk-Forward 時間線
│   │   ├── CPCVPathChart.tsx            # CPCV 路徑圖
│   │   ├── LearningCurveChart.tsx       # 學習曲線圖
│   │   ├── AdversarialFeatureChart.tsx  # 對抗驗證圖
│   │   ├── MultiIndicatorConfig.tsx     # 多指標配置
│   │   ├── common/                      # 共用（OptunaProgressBar, SamplerSelector 等）
│   │   ├── execution/                   # 執行優化（EquityCurveChart, ParetoFrontChart 等）
│   │   └── hyperparameter/              # 超參數（OverfittingCheckChart, ParameterImportanceChart 等）
│   ├── results/                         # 優化結果展示
│   │   ├── MetricsPanel.tsx             # 指標總覽
│   │   ├── DensityComparisonChart.tsx   # 密度對比
│   │   ├── StabilityChart.tsx           # 穩定性分析
│   │   ├── TrialHistoryTable.tsx        # 試驗歷史表
│   │   ├── ParameterImportanceChart.tsx # 參數重要性
│   │   └── ExportButton.tsx             # 匯出按鈕
│   ├── optimization-results/            # 最佳結果展示
│   │   ├── BestResultCard.tsx           # 最佳結果卡
│   │   ├── ConvergencePlot.tsx          # 收斂圖
│   │   ├── ParamHeatmap.tsx             # 參數熱力圖
│   │   └── StabilityChart.tsx           # 穩定性圖
│   ├── ic-analysis/                     # IC 深度分析（25 個元件）
│   │   ├── RollingICChart.tsx           # 滾動 IC 時序圖
│   │   ├── CorrelationHeatmap.tsx       # 相關性矩陣
│   │   ├── FactorReturnChart.tsx        # 因子報酬圖
│   │   ├── FactorCentralityChart.tsx    # 因子中心性
│   │   ├── FeatureQualityDashboard.tsx  # 品質儀表板
│   │   ├── DeepAnalysisConfigPanel.tsx  # 配置面板
│   │   └── ...                          # 20+ 其他元件
│   ├── feature-factory/                 # Feature Factory UI（23 個元件）
│   │   ├── ConfigPanel.tsx              # 配置面板
│   │   ├── FeatureExplorer.tsx          # 特徵瀏覽器
│   │   ├── PreprocessingPanel.tsx       # 前處理面板
│   │   ├── OverviewDashboard.tsx        # 總覽儀表板
│   │   └── ...                          # 19+ 其他元件
│   ├── feature-browser/                 # 特徵瀏覽器（14 個元件）
│   │   ├── FeatureCatalogTable.tsx      # 特徵目錄表
│   │   ├── DriftMonitor.tsx             # 漂移監控
│   │   ├── QualityScorecard.tsx         # 品質計分卡
│   │   └── ...                          # 11+ 其他元件
│   ├── pattern/                         # Pattern 分析（11 個元件）
│   │   ├── PatternList.tsx              # Pattern 列表
│   │   ├── PatternDetail.tsx            # Pattern 詳情
│   │   ├── XGBoostAnalysisPanel.tsx     # XGBoost 面板
│   │   └── FeatureImportanceChart.tsx   # 特徵重要性
│   ├── strategy/                        # 策略配置（8 個元件）
│   ├── strategy-test/                   # 策略測試
│   ├── case/                            # 案例管理
│   ├── common/                          # 共用元件
│   ├── layout/                          # 佈局元件
│   ├── providers/                       # Context Providers
│   ├── settings/                        # 設定面板
│   └── ui/                              # shadcn/ui 基礎元件
├── store/
│   ├── searchStore.ts                   # 搜索狀態
│   ├── optimizationStore.ts             # 優化狀態
│   ├── icAnalysisStore.ts               # IC 分析狀態
│   ├── modelEnhancementStore.ts         # 模型增強狀態
│   ├── featureFactoryStore.ts           # Feature Factory 狀態
│   ├── featureBrowserStore.ts           # 特徵瀏覽狀態
│   ├── featureToggleStore.ts            # Feature Toggle 狀態
│   ├── patternStore.ts                  # Pattern 管理狀態
│   └── strategyTestStore.ts             # 策略測試狀態
├── hooks/
│   ├── useICAnalysis.ts                 # IC 分析 Hook
│   ├── useOptimization.ts               # 優化 Hook
│   ├── useFeatureFactory.ts             # Feature Factory Hook
│   ├── useChart.ts                      # 圖表 Hook
│   ├── useChartSync.ts                  # 圖表同步 Hook
│   ├── useAutoResearch.ts               # 自動研究 Hook
│   ├── useAvailableSymbols.ts           # 可用標的 Hook
│   └── useStrategyConfig.ts             # 策略配置 Hook
└── lib/
    ├── types.ts                         # TypeScript 介面定義
    ├── api.ts                           # API 客戶端
    ├── utils.ts                         # 工具函式
    ├── exportUtils.ts                   # 匯出工具
    └── errorHandler.ts                  # 錯誤處理
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
- **組件**: `PriceChart.tsx` / `TradingChartWithSignals.tsx`（Lightweight Charts）
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
完整特徵擷取 → HDF5 存儲 → 品質驗證流程。新增 FeatureFactory 7 層 Pipeline（Phase 1）與三大擴充引擎（Phase 1.5）。

#### 核心模組
- **7 層 Pipeline**: `momentum/FeatureEngineering/feature_factory.py`（FeatureFactory — Phase 1）
- **擷取**: `momentum/FeatureEngineering/feature_extractor.py`（Legacy）
- **存儲**: `momentum/FeatureEngineering/feature_storage.py`（HDF5）
- **驗證**: `momentum/FeatureEngineering/feature_validator.py`
- **配置**: `momentum/FeatureEngineering/config_manager.py` + `config/scan_config.yaml`
- **服務**: `api/services/feature_task_service.py`
- **API**: `POST /features/extract`、`POST /features/generate`、`GET /features/task/{id}`、`GET /features/summary/{case_id}`、`GET /features/health`

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

### ✅ 14. IC 特徵篩選系統（Phase 2 IC Gatekeeper）

#### 系統概述
**Information Coefficient 驅動的特徵選擇框架**，透過八階段管線自動識別預測力強的技術指標，並進行統計驗證與冗餘篩選。

#### 核心模組（18 個）

**IC 分析核心（12 個）**：

| 模組 | 位置 | 行數 | 功能 |
|------|------|------|------|
| data_preprocessor | `momentum/Analysis/` | 265 | Winsorization（異常值處理）、缺失值填補、標準化、常數特徵移除 |
| ic_engine | `momentum/Analysis/` | 720 | Rolling IC 計算、ICIR、IC Decay、Grouped IC（按年/季/市場狀態） |
| ic_filter_orchestrator | `momentum/Analysis/` | 1,087 | 八階段管線協調器（Stage 0-7）、統一入口 |
| event_filter | `momentum/Analysis/` | 289 | Query/Timestamp 事件篩選、樣本數分層（tier_1/2/3） |
| statistical_validator | `momentum/Analysis/` | 166 | t-test、p-value、信賴區間、Bonferroni/FDR 多重比較修正 |
| monotonicity_tester | `momentum/Analysis/` | 244 | 分位數報酬分析、單調性分數、Long-Short 價差 |
| redundancy_filter | `momentum/Analysis/` | 410 | Greedy 去重、Hierarchical Clustering、VIF、Diversification |
| turnover_analyzer | `momentum/Analysis/` | 92 | 分位數換手率、排名變化率、自相關分析 |
| coverage_analyzer | `momentum/Analysis/` | 92 | 時間覆蓋率、有效起點偵測、低覆蓋標記 |
| ic_config_schema | `momentum/Analysis/` | 349 | Pydantic 配置模型、三層合併（Default < YAML < API） |
| ic_reporter | `momentum/Analysis/` | 364 | JSON/Markdown/HDF5/AI 摘要四種報告格式 |
| exceptions | `momentum/core/` | 13 | InsufficientDataError、InvalidQueryError、InvalidInputError |

**模型驗證子系統（5 個）**：

| 模組 | 位置 | 行數 | 功能 |
|------|------|------|------|
| cv_validator | `momentum/Analysis/model_validation/` | 255 | 時間序列交叉驗證、OOT 切分、AUC/Precision/Recall/F1 |
| oot_validator | `momentum/Analysis/model_validation/` | 156 | Out-of-Time 驗證、CV-OOT Gap 評估 |
| psi_calculator | `momentum/Analysis/model_validation/` | 121 | PSI 漂移監控、穩定性分類（穩定/輕微/中度/嚴重） |
| rolling_auc | `momentum/Analysis/model_validation/` | 148 | 滾動 AUC 追蹤、趨勢偵測（上升/下降/穩定） |
| case_shap | `momentum/Analysis/model_validation/` | 115 | 單案例 SHAP 解釋、批次特徵重要性分析 |

**API 層（4 個）**：

| 模組 | 位置 | 功能 |
|------|------|------|
| ic_models | `api/models/ic_models.py` | Pydantic Request/Response 模型（ICAnalysisRequest、ICAnalysisResponse） |
| ic_analysis | `api/routes/ic_analysis.py` | 13 個 REST 端點（啟動分析、查詢狀態、下載報告、refilter） |
| ic_analysis_service | `api/services/ic_analysis_service.py` | 業務邏輯層、使用 `create_ic_analyzer()` Factory 建構 |
| ic_analysis_ws | `api/websocket/ic_analysis_ws.py` | WebSocket 實時進度推送（階段狀態、進度百分比） |

**前端（25+ 元件）**：

| 類別 | 元件數量 | 位置 |
|------|----------|------|
| 頁面 | 2 | `frontend/src/app/ic-analysis/` (page.tsx, layout.tsx) |
| 視覺化元件 | 25 | `frontend/src/components/ic-analysis/` |
| Hooks | 1 | `frontend/src/hooks/useICAnalysis.ts` |
| Store | 1 | `frontend/src/store/icAnalysisStore.ts` |

**視覺化元件清單**（主要元件）：
- `RollingICChart` - 滾動 IC 時序圖
- `CorrelationHeatmap` - 相關性矩陣熱力圖
- `FactorReturnChart` - 因子報酬圖
- `FactorCentralityChart` - 因子中心性
- `FactorExposureRadar` - 因子曝露雷達圖
- `LongShortComparisonChart` - 多空對比
- `FeatureQualityDashboard` - 品質儀表板
- `TrendDashboard` - 趨勢儀表板
- `ParameterSensitivityHeatmap` - 參數敏感度
- `DeepAnalysisConfigPanel` - 深度分析配置面板
- `NetICChart` - Net IC 分析圖
- …及其他 14 個元件

**配置檔案**：
- `config/ic_config.yaml` - IC 配置檔案（方法、閾值、篩選器參數）

#### 八階段篩選管線

```
Stage 0: 資料攝入
   ↓ 讀取 HDF5 特徵檔案 + 標籤檔案 + Metadata JSON
Stage 1: 數據前處理
   ↓ Winsorization (1%-99%) + 缺失值填補 + 標準化 + 常數特徵移除
Stage 2: 標籤生成
   ↓ 收益率計算 (forward_N_return) + 時間跨度轉換
Stage 3: 事件篩選
   ↓ Query/Timestamp 模式篩選 + 樣本數分層 (tier_1/2/3)
Stage 4: IC 計算
   ↓ Rolling IC + ICIR + IC Decay + Grouped IC (按年/季/狀態)
Stage 5: 統計驗證
   ↓ t-test + p-value + 信賴區間 + Bonferroni/FDR 修正
Stage 6: 單調性測試
   ↓ 分位數報酬 (5 分位) + 單調性分數 + Long-Short 價差
Stage 7: 冗餘篩選
   ↓ 相關矩陣分析 + Greedy/Hierarchical/VIF/Diversification
Stage 8: 報告生成
   ↓ JSON + Markdown + HDF5 + AI 摘要（四種格式同步生成）
```

#### 三種 IC 方法

| 方法 | 適用場景 | 優點 | 缺點 |
|------|---------|------|------|
| **Spearman** | 非線性關係、有離群值 | 對離群值穩健、適合單調關係 | 無法量化線性程度 |
| **Pearson** | 線性關係、連續變數 | 最大解釋力、統計特性最好 | 對離群值敏感 |
| **Kendall** | 小樣本、序數資料 | 樣本數小時穩定、適合排序 | 計算較慢 |

#### 四種冗餘篩選演算法

| 演算法 | 原理 | 適用場景 | 參數 |
|--------|------|---------|------|
| **Greedy** | 迭代保留高 IC、剔除相關特徵 | 快速去重 | `correlation_threshold` (預設 0.7) |
| **Hierarchical** | 樹狀結構分組、每組選代表 | 視覺化特徵關係 | `distance_threshold` (預設 0.5) |
| **VIF** | 方差膨脹因子、多重共線性 | 回歸模型必備 | `vif_threshold` (預設 5.0) |
| **Diversification** | 多樣化評估、確保特徵互補 | 降低模型風險 | `max_correlation` (預設 0.6) |

#### 測試套件（26 個測試檔案）

| 類別 | 檔案 | 行數（預估） | 測試內容 |
|------|------|-------------|----------|
| API 測試 | `test_ic_analysis_api.py` | ~200 | 13 個端點完整測試 |
| E2E 測試 | `test_ic_e2e.py` | ~300 | 端到端管線、refilter 快取、效能 |
| 引擎測試 | `test_ic_engine.py` | ~600 | IC 計算引擎完整覆蓋 |
| 效能測試 | `test_ic_engine_performance.py` | ~80 | 200×10K < 2s 基準 |
| 協調器測試 | `test_ic_filter_orchestrator.py` | ~700 | 八階段管線測試 |
| 報告測試 | `test_ic_reporter.py` | ~150 | JSON/Markdown/HDF5 生成 |
| 模組測試 | 20 個其他測試檔案 | ~2,500 | 各模組單元測試 |
| **總計** | **26 個檔案** | **~4,530** | **159 tests, 100% coverage** |

**測試統計**：
- ✅ 159 tests passed
- ⚠️ 2 warnings（非關鍵問題）
- ✅ 100% coverage (1,563/1,563 statements)
- ✅ 效能基準達標（200 features × 10K samples < 2s，超標 4 倍）

#### 架構特色

**Rule 1-7 完全遵守**：
- ✅ Rule 1: `momentum/` 不依賴 `api/`（0 violation，grep 驗證通過）
- ✅ Rule 2: 跨 Domain 使用 Protocol 注入（IICAnalyzer、ILabelGenerator、ICVValidator）
- ✅ Rule 3: API Service 使用 Factory 建構（`create_ic_analyzer()` 來自 `momentum/factories.py`）
- ✅ Rule 4: Service 之間無互相 import（0 violation）
- ✅ Rule 5: 無 Mutable global singleton
- ✅ Rule 6: 無 callback/closure bypass
- ✅ Rule 7: `api/models` ↔ `momentum/core` 無互相依賴

**Protocol 擴展**：
```python
# momentum/core/protocols.py
class IICAnalyzer(Protocol):
    """IC 分析器介面"""
    def analyze(...) -> ICAnalysisResult: ...

class ILabelGenerator(Protocol):
    """標籤生成器介面"""
    def generate_labels(...) -> pd.DataFrame: ...

class ICVValidator(Protocol):
    """交叉驗證器介面"""
    def validate(...) -> ValidationResult: ...
```

**三層配置系統**：
```
1. Default（程式碼內建預設值）
2. YAML（config/ic_config.yaml）
3. API Override（REST 請求參數）
優先級：Default < YAML < API Override
```

**事務性報告生成**：
所有報告格式（JSON/Markdown/HDF5/AI 摘要）在同一事務中生成，確保一致性。

#### 效能表現

- **計算效能**: 200 features × 10K samples < 2s（超標 4 倍）
- **Refilter 快取**: 讀取已計算 IC，重新套用篩選條件（10 倍加速）
- **向量化計算**: 使用 Pandas/NumPy 優化，避免 Python 循環
- **HDF5 壓縮**: gzip 壓縮，減少磁碟空間佔用

#### 待開發（前端 UI）

- ⏳ IC 分析結果視覺化頁面
- ⏳ 互動篩選控制面板（即時調整閾值）
- ⏳ 報告下載功能（JSON/Markdown/HDF5）
- ⏳ 相關性矩陣熱力圖互動視覺化
- ⏳ 特徵對比圖表（多特徵 IC 比較）

---

### ✅ 15. 雙引擎 ML 系統（Phase 3.7）

#### 架構概觀

```
              IModelTrainer Protocol (8 個方法)
                       |
      +───────────────+───────────────+
      |                               |
XGBoostAnalyzer                LightGBMAnalyzer
(8 methods, 向後相容)         (8 methods, 新引擎)
      |                               |
      +───────────────+───────────────+
                       |
              ModelComparison
          (A/B 對比 + 共識率 + 推薦)
```

#### 核心元件

| 元件 | 檔案 | 功能 |
|------|------|------|
| **IModelTrainer** | `momentum/core/protocols.py` | 8 個方法（train_model、predict_proba、get_feature_importance、save/load_model、get_model_type/params/native_model） |
| **IOptimizationObjective** | `momentum/core/protocols.py` | 6 個方法（name、direction、directions、create_search_space、evaluate、get_pruning_callback） |
| **LightGBMAnalyzer** | `momentum/Analysis/lightgbm_analyzer.py` | LightGBM 引擎，實作 IModelTrainer Protocol |
| **XGBoostAnalyzer** | `momentum/Analysis/xgboost_analyzer.py` | XGBoost 引擎，擴展 7 個新 Protocol 方法（向後相容） |
| **ModelComparison** | `momentum/Analysis/model_comparison.py` | 雙引擎並行訓練 + A/B 對比 + 共識率分析 |
| **ModelConfigManager** | `momentum/Analysis/model_config.py` | 四維參數系統（YAML → Dict → NL → Optuna） |
| **model_types** | `momentum/Analysis/model_types.py` | 13 個共用 dataclass（ModelPerformance、FeatureImportance、ComparisonReport 等） |
| **objectives/** | `momentum/Optimization/objectives/` | 3 個可插拔目標函式（ModelHyperparam、SignalDensity、StrategyBacktest） |

#### API 層

| 模組 | 位置 | 功能 |
|------|------|------|
| ModelTaskService | `api/services/model_task_service.py` | 通用模型任務調度（支援 XGBoost/LightGBM/雙引擎對比） |
| ModelTaskCache | `api/services/xgboost_task_cache.py` | 擴展為多引擎任務快取 |
| pattern_analysis routes | `api/routes/pattern_analysis.py` | 新增 /model/* 和 /lightgbm/* 端點 |
| pattern_analysis_models | `api/models/pattern_analysis_models.py` | 新增 7 個 API Model |

#### 前端元件

| 元件 | 位置 | 功能 |
|------|------|------|
| EngineConfigPanel | `frontend/src/components/pattern/EngineConfigPanel.tsx` | 引擎選擇 + 模型參數 + Optuna 開關 |
| ComparisonPanel | `frontend/src/components/pattern/ComparisonPanel.tsx` | 雙引擎對比主容器 |
| RecommendationBanner | `frontend/src/components/pattern/comparison/` | 推薦引擎 Banner |
| ComparisonMetricsTable | `frontend/src/components/pattern/comparison/` | 指標並排表格 |
| ConsensusCard | `frontend/src/components/pattern/comparison/` | 共識率卡片 |
| ComparisonFeatureChart | `frontend/src/components/pattern/comparison/` | 特徵對比長條圖 |

#### 測試覆蓋
- 10 個測試檔案，160+ 測試案例
- 邊界條件：100% 覆蓋
- Protocol 合規性：100% 通過
- 架構合規：REFACTOR_ARCHITECTURE_V4 Rule 1-7 全部通過

---

### ✅ 16. Feature Factory 特徵工程系統（Phase 1 + 1.5）

#### 系統概述
**7 層 Feature Pipeline** — Config-Driven 特徵生成工廠，支持七段式命名規範與增量生成。

#### 7 層 Pipeline 架構

| Layer | 名稱 | 功能 |
|-------|------|------|
| Layer 0 | 數據標準化 | HDF5 欄位映射、Adapter 轉換 |
| Layer 1 | 原子指標 | TA-Lib 引擎 + 微觀結構 + 資訊理論 + 尾部風險 |
| Layer 2 | 衍生特徵 | Distance / Cross / Divergence 算子 |
| Layer 3 | Rolling 統計 | Slope / ZScore / RollingAgg 窗口特徵 |
| Layer 4 | Lag 延遲 | 時間序列延遲特徵 |
| Layer 5 | 多時間框架 | MTF 對齊（1h/4h → 主 TF） |
| Layer 6 | 元特徵 | Trend Consensus / Volatility Regime |
| Layer 6.5 | 前處理 | rank/gaussian/zscore/diff/fracdiff（Phase 1.5） |
| Layer 7 | Label | binary/regression 標籤生成 |

#### 核心模組
- **工廠**: `momentum/FeatureEngineering/feature_factory.py`（FeatureFactory — 7 層 Pipeline 協調）
- **配置**: `momentum/FeatureEngineering/config_manager.py`（ConfigManager — YAML Preset 管理）
- **原子引擎**: `momentum/FeatureEngineering/atomic/`（TA-Lib + 微觀結構 + 資訊理論 + 尾部風險）
- **前處理**: `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- **工廠函式**: `momentum/factories.py` → `create_feature_factory()`
- **Config**: `config/scan_config.yaml`

#### Phase 1.5 擴充引擎

| 引擎 | Prefix | 功能 |
|------|--------|------|
| MicrostructureIndicatorEngine | `ms_` | Amihud 流動性、Kyle Lambda、VPIN 等 |
| EntropyIndicatorEngine | `ent_` | Shannon/Permutation Entropy、Hurst 指數、ApEn/SampEn |
| TailRiskIndicatorEngine | `tr_` | CVaR、上下行波動率、最大回撤、極值統計 |
| FeaturePreprocessor (Layer 6.5) | `_rank/_zscore/...` | 排名轉換、Gaussian 轉換、Z-Score、差分、分數差分 |

#### 架構特色
- ✅ Rule 1-7 完全遵守（Protocol 注入 `IKlineReader`、Factory 建構）
- ✅ Config-Driven（所有特徵由 `scan_config.yaml` 控制）
- ✅ 七段式命名規範（`{source}_{timeframe}_{category}_{indicator}_{params}_{operator}_{window}`）
- ✅ 增量生成機制（`force_regenerate` 控制）

---

### ✅ 17. IC 深度分析系統（Phase 2.4-2.12）

#### 系統概述
**10 個深度分析模組**擴展 IC Gatekeeper 系統，提供因子報酬、中心性、趨勢、敏感度、OOS 等進階分析。

#### 10 個深度分析模組

| # | 模組 | 功能 |
|---|------|------|
| 1 | factor_return_analyzer | 因子報酬分析（多空價差、IC 加權報酬） |
| 2 | factor_centrality_analyzer | PCA 因子中心性（主成分解釋力） |
| 3 | trend_analyzer | 趨勢分析（IC/Centrality/FactorReturn/LS-Spread 時序） |
| 4 | parameter_sensitivity_analyzer | 參數敏感度（窗口/閾值/分位數影響） |
| 5 | rolling_oos_validator | 滾動 OOS 驗證（樣本外穩定性） |
| 6 | factor_orthogonalizer | 因子正交化（Gram-Schmidt / PCA 去冗餘） |
| 7 | factor_exposure_analyzer | 因子曝露與歸因（因子載荷分析） |
| 8 | long_short_analyzer | 多空分離分析（獨立 IC/報酬分析） |
| 9 | feature_quality_diagnostics | ADF/Ljung-Box/CUSUM/PSI/Coverage 診斷 |
| 10 | net_ic_analyzer | Net IC / 交易成本分析（考慮換手率的淨 IC） |

#### 其他擴展功能
- **Phase 2.10**: 特徵難度分級系統（自動標記特徵品質等級）
- **Phase 2.11**: 全格式匯出系統（JSON/CSV/Markdown/HDF5/AI-readable）
- **Phase 2.12**: 特徵工程資料瀏覽器（前端互動探索）
- **前端元件**: 10 個新圖表元件（C13-C22）

---

### ✅ 18. 模型增強系統（Phase 3.5）

#### 系統概述
**6 個模型增強模組**（M1-M6），為 ML 模型（XGBoost/LightGBM）提供機率校準、Walk-Forward 驗證、樣本加權等進階功能。

#### 核心模組

| # | 模組 | 功能 |
|---|------|------|
| M1 | ProbabilityCalibrator | 機率校準（Platt Scaling / Isotonic Regression / Beta Calibration / Venn-ABERS） |
| M2 | WalkForwardValidator | Walk-Forward 驗證（Rolling / Expanding 窗口） |
| M3 | SampleWeightCalculator | 樣本加權（time_decay / class_balance / return_based / uniqueness） |
| M4 | AdversarialValidator | 對抗驗證（分布測試 + feature-level KS/PSI + 洩漏偵測） |
| M5 | CombinatorialPurgedCV | CPCV（López de Prado 組合式 Purged 交叉驗證） |
| M6 | LearningCurveAnalyzer | 學習曲線（data/feature curves + bias-variance 診斷） |

#### API 端點
- `POST /api/v1/model-enhancement/calibrate` — 機率校準
- `POST /api/v1/model-enhancement/walk-forward` — Walk-Forward 驗證
- `POST /api/v1/model-enhancement/sample-weights` — 樣本加權計算
- `POST /api/v1/model-enhancement/adversarial-validate` — 對抗驗證
- `POST /api/v1/model-enhancement/cpcv` — CPCV 驗證
- `POST /api/v1/model-enhancement/learning-curve` — 學習曲線
- `GET /api/v1/model-enhancement/task/{task_id}` — 查詢任務
- `POST /api/v1/model-enhancement/full-enhancement` — 全量增強

#### 前端元件
- CalibrationPlot (C23) — 校準曲線圖
- WalkForwardTimeline (C24) — Walk-Forward 時間線
- AdversarialFeatureChart (C25) — 對抗驗證特徵圖
- CPCVPathChart (C26) — CPCV 路徑圖
- LearningCurveChart (C27) — 學習曲線圖

---

### ✅ 19. Strategy 回測與優化系統（Phase 4）

#### 系統概述
**新 Domain `momentum/Strategy/`** — 提供向量化回測引擎、12+ 績效指標、部位管理、風險管理功能。同時重構 Optuna 優化系統為可插拔架構。

#### 核心模組

| 模組 | 功能 |
|------|------|
| VectorizedBacktest | 向量化回測引擎（信號生成 + 交易執行 + SL/TP/Trailing Stop） |
| PerformanceMetrics | 12+ 績效指標（Sharpe / Sortino / Calmar / MaxDD / Expectancy / SQN / Win Rate / Profit Factor） |
| KellyPositionSizer | Kelly 公式部位管理 |
| FixedPositionSizer | 固定比例部位管理 |
| ProbabilityScaledSizer | 機率加權部位管理 |
| RiskManager | 風險管理（SL/TP/Trailing Stop 計算） |

#### 新 Protocol
```python
class IBacktestEngine(Protocol):
    def run_backtest(self, signals, kline_data, config) -> Any: ...
    def get_performance_metrics(self) -> Dict[str, float]: ...

class IPositionSizer(Protocol):
    def calculate_position_size(self, signal, equity, risk_params) -> float: ...
```

#### Optuna 重構
- **StrategyBacktestObjective**: 增強（新建構子 + 9 參數搜索空間 + 約束剪枝）
- **ModelHyperparamObjective**: 增強（過擬合偵測、搜索空間驗證）
- **SignalDensityObjective**: 歸檔至 `archived/momentum/Optimization/objectives/`
- **optimization_config.yaml**: 新配置檔案（execution + hyperparameter + archived 區段）

#### API 端點
- `api/routes/hyperparameter_optimization.py` — 超參數優化端點
- `api/routes/execution_optimization.py` — 執行優化端點
- `api/services/optimization_output_service.py` — 輸出服務（JSON/CSV/HTML/AI-readable 報告）

#### WebSocket 新事件
- `backtest_progress` — 回測進度
- `pareto_update` — Pareto 前沿更新
- `overfitting_alert` — 過擬合警報

---

### ✅ 20. Feature Factory MultiTF 整合 + 多標的批次計算

#### 系統概述
本系統解決兩個核心缺口：
1. **MultiTF 路由**：`generate_features()` 對 `config.timeframes.training` 中列出的外加時幅計算對齊特徵
2. **多標的批次**：`FeatureFactoryBatchService` 將單標的任務並行化，支持 100+ 標的

#### MultiTF 路由策略

```python
# momentum/FeatureEngineering/feature_factory.py
def generate_features(self, symbol: str, timeframe: str) -> pd.DataFrame:
    # 主 TF：第一輪 Kline 讀取 + 7 層 Pipeline
    base_df = self._run_pipeline(symbol, timeframe)

    # 委託 MultiTFGenerator 計算訓練 TF
    training_tfs = self.config.timeframes.training
    if len(training_tfs) > 1:
        for tf in training_tfs:
            if tf != timeframe:
                extra_df = multi_tf_gen.generate(symbol, tf)  # 各自 7 層
                aligned_df = aligner.align(extra_df, base_df)  # OPEN_MINUS / CLOSE_TIME
                base_df = pd.concat([base_df, aligned_df], axis=1)
    return base_df
```

#### AlignmentMode Paradigm

| 模式 | 定義 | 適用情境 |
|------|------|----------|
| `OPEN_MINUS` | 現標時幅屬於 `open_time[i]（下一標的 open_time）` 的 bar | 預設，防起 look-ahead bias |
| `CLOSE_TIME` | 現標時幅以 `close_time` 對齊 | 高頻對齊至低頻，當低頻 K 線收盤就可知 |

```python
# momentum/FeatureEngineering/feature_config.py
class AlignmentMode(str, Enum):
    OPEN_MINUS = "open_minus"   # 預設：第 i+1 根 bar 的 open
    CLOSE_TIME = "close_time"   # 高頻時幅特徵修正
```

#### FeatureFactoryBatchService 架構

```python
# api/services/feature_factory_batch_service.py
class FeatureFactoryBatchService:
    """ProcessPoolExecutor 並行發出庫所有標的的特徵計算任務。"""

    MAX_CONCURRENT = 2          # 同時執行批次任務上限
    TASK_TTL_SECONDS = 3600     # TTL 清理已完成任務

    async def start_batch(self, request: BatchGenerateRequest) -> str:
        task_id = str(uuid.uuid4())
        asyncio.create_task(self._run_batch(task_id, request))
        return task_id

    async def _run_batch(self, task_id: str, request: BatchGenerateRequest):
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=request.max_workers) as pool:
            futures = [
                loop.run_in_executor(pool, _generate_one, sym, request)
                for sym in request.symbols
            ]
            for sym, future in zip(request.symbols, asyncio.as_completed(futures)):
                try:
                    result_task_id = await future
                    self._update_status(task_id, sym, success=True, result=result_task_id)
                except Exception as exc:
                    self._update_status(task_id, sym, success=False, error=str(exc))

    def get_status(self, task_id: str) -> BatchTaskStatusResponse | None:
        return self._tasks.get(task_id)
```

#### 已實作 API 端點
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/features/generate` | 單標的生成（8 種 TF 驗證）|
| POST | `/api/v1/features/batch` | 啟動批次生成 |
| GET | `/api/v1/features/batch/{task_id}` | 查詢批次狀態 |
| WS | `ws/features/batch/{task_id}` | 批次進度推送 |

#### Tests
- `tests/feature_factory/` 下 54 個測試全部通過（Phase 0 ~ Phase 4）
- `tests/feature_factory/test_batch_generation.py` — BatchService 單元測試
- `tests/feature_factory/test_multi_tf_alignment.py` — AlignmentMode 測試

---

## 待開發功能

### ⏳ 1. 前端 UI 整合（優先級：🔥 高）

各系統前端視覺化頁面開發與整合：
- IC Deep Analysis 前端互動面板
- Model Enhancement 前端儀表板
- Strategy 回測結果視覺化
- Feature Factory 管理介面

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
| `docs/DEVELOPMENT_GUIDE.md` | 開發規範（Ultra Think 3 步驟） |
| `docs/REFACTOR_ARCHITECTURE_V4.md` | 架構重構記錄（10 個 Phase）— 歷史參考 |
| `docs/FRONTEND_INTEGRATION_GUIDE.md` | 前端整合指南（Phase 3-6 UI） |
| `docs/DYNAMIC_INDICATOR_SYSTEM_GUIDE.md` | 動態指標系統指南（Legacy，已被 Feature Factory 取代） |
| `.github/copilot-instructions.md` | AI Agent 指令 |

---

*文檔版本：6.1*  
*最後更新：2026-04-14*  
*狀態：Phase 1-4 + Feature Factory MultiTF/Batch 全部完成，前端 UI 整合進行中*
